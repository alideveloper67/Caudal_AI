# -*- coding: utf-8 -*-
"""Enviar la música de Caudal Escritorio a un Chromecast, una tele o un altavoz
con Google Cast (lo mismo que el botón de Cast del teléfono).

Mientras hay conexión, el reproductor de Caudal sigue mandando (cola, radio,
siguiente...) pero no suena en la PC: cada canción que iba a abrir se la pasa a
``ControlCast.enviar`` y los botones (play/pausa, barra, volumen) llaman a
``pausar``, ``reanudar``, ``ir_a`` y ``fijar_volumen``. La tele avisa cuando
acaba y se pide la siguiente. Al desconectar, la música vuelve a la PC en el
mismo punto.

Qué se le manda a la tele:

* Canciones de YouTube / YouTube Music: el enlace de audio que ya resolvió
  yt-dlp (webm/opus o m4a/aac, que Chromecast entiende). Va atado a la IP
  pública de casa y la tele sale por la misma, así que lo abre ella sola. Si no
  puede, se repite a través de la PC (``ServidorCast``).
* Descargas y archivos del disco: los sirve la propia PC por la red de casa, con
  saltos (cabecera Range) para poder mover la barra.

Usa pychromecast (y zeroconf para descubrir los aparatos). Si no está instalado,
``disponible()`` es False y el botón no aparece.
"""

import ipaddress
import os
import re
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QObject, QTimer, Signal

# estados de la conexión
DESCONECTADO, CONECTANDO, CONECTADO = "desconectado", "conectando", "conectado"
# lo que dice la tele de lo que suena
NADA, CARGANDO, SONANDO, PAUSA, TERMINADO, ERROR, CORTADO = (
    "nada", "cargando", "sonando", "pausa", "terminado", "error", "cortado")


def disponible():
    """¿Está pychromecast? (va en requirements.txt)."""
    try:
        import pychromecast  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


# ------------------------------------------------------------------ utilidades

def rango_pedido(cabecera, largo):
    """El trozo (primero, último) que pide ``Range: bytes=...`` de un archivo de
    ``largo`` bytes. Sin cabecera: todo. None si el trozo no existe (416)."""
    if not cabecera or not cabecera.strip():
        return (0, max(0, largo - 1))
    m = re.match(r"^\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)", cabecera)
    if not m:
        return (0, max(0, largo - 1))
    a, b = m.group(1), m.group(2)
    if not a and not b:
        return None
    if largo == 0:
        return None
    if not a:
        n = int(b)
        if n == 0:
            return None
        return (max(0, largo - n), largo - 1)
    desde = int(a)
    if desde >= largo:
        return None
    hasta = largo - 1 if not b else min(int(b), largo - 1)
    if hasta < desde:
        return None
    return (desde, hasta)


_TIPOS = {
    "mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/mp4", "opus": "audio/ogg",
    "ogg": "audio/ogg", "oga": "audio/ogg", "webm": "audio/webm", "weba": "audio/webm",
    "flac": "audio/flac", "wav": "audio/wav", "mp4": "video/mp4", "m4v": "video/mp4",
    "mkv": "video/x-matroska", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif",
}


def tipo_por_extension(ruta):
    return _TIPOS.get(os.path.splitext(ruta or "")[1].lower().lstrip("."), "application/octet-stream")


def direccion_de(fuente):
    """La dirección que va a la tele. En modo video, solo el sonido."""
    if not fuente:
        return None
    if fuente.get("archivo"):
        return fuente["archivo"]
    u = fuente.get("audio_url") or fuente.get("url") or ""
    return u if u.startswith("http") else None


def tipo_de_fuente(fuente):
    """Por el ``mime=`` de los enlaces de YouTube, por la extensión o por el formato."""
    if fuente.get("archivo"):
        return tipo_por_extension(fuente["archivo"])
    u = fuente.get("audio_url") or fuente.get("url") or ""
    mime = urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("mime")
    if mime and "/" in mime[0]:
        return mime[0]
    info = fuente.get("info") or {}
    ext = str(info.get("ext") or info.get("formato") or "").lower()
    if ext in _TIPOS:
        return _TIPOS[ext]
    if not fuente.get("audio_url") and (info.get("alto") or 0) > 0:
        return "video/mp4"
    return "audio/mp4"


def caratula_grande(url):
    """Las miniaturas de YouTube Music vienen pequeñas: para la tele, grandes."""
    if not url:
        return url
    m = re.search(r"=w\d+-h\d+", url)
    if m and "googleusercontent" in url:
        return url.replace(m.group(0), "=w720-h720", 1)
    return re.sub(r"/(default|mqdefault|sddefault)\.jpg", "/hqdefault.jpg", url, count=1)


def es_privada(ip):
    try:
        d = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return d.version == 4 and d.is_private and not d.is_loopback and not d.is_link_local


def ip_local():
    """La dirección IPv4 de la PC en la red de casa, o None. (El socket UDP no
    manda nada: solo pregunta por qué tarjeta saldría.)"""
    for destino in ("192.168.1.1", "10.255.255.255", "8.8.8.8"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect((destino, 9))
                ip = s.getsockname()[0]
            finally:
                s.close()
            if es_privada(ip):
                return ip
        except OSError:
            continue
    return None


# ------------------------------------------------------------------ servidor de la PC

class ServidorCast:
    """Servidor http pequeño para la tele.

    * ``/a/<clave>``: un archivo publicado (la clave es al azar: no deja leer
      nada más del disco).
    * ``/p/<clave>``: repite un stream remoto a través de la PC.
    """

    def __init__(self, ip=None):
        self.ip = ip
        self._srv = None
        self._hilo = None
        self._archivos = {}   # clave -> (ruta, tipo)
        self._remotos = {}    # clave -> (url, tipo, cabeceras)
        self._cerrojo = threading.Lock()

    @property
    def puerto(self):
        return self._srv.server_address[1] if self._srv else 0

    def _abrir(self):
        with self._cerrojo:
            if self._srv:
                return
            servidor = self

            class Manejador(BaseHTTPRequestHandler):
                protocol_version = "HTTP/1.1"

                def log_message(self, *_a):
                    pass

                def do_HEAD(self):
                    servidor._atender(self, cuerpo=False)

                def do_GET(self):
                    servidor._atender(self, cuerpo=True)

                def do_OPTIONS(self):
                    self.send_response(204)
                    servidor._cors(self)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

            self._srv = ThreadingHTTPServer(("0.0.0.0", 0), Manejador)
            self._srv.daemon_threads = True
            self._hilo = threading.Thread(target=self._srv.serve_forever, name="caudal-cast-http",
                                          daemon=True)
            self._hilo.start()

    def _base(self):
        ip = self.ip or ip_local()
        if not ip:
            return None
        self._abrir()
        return f"http://{ip}:{self.puerto}"

    def publicar_archivo(self, ruta, tipo=None):
        if not ruta or not os.path.isfile(ruta):
            return None
        base = self._base()
        if not base:
            return None
        with self._cerrojo:
            clave = next((k for k, v in self._archivos.items() if v[0] == ruta), None) or secrets.token_hex(16)
            if len(self._archivos) >= 300:
                self._archivos.pop(next(iter(self._archivos)))
            self._archivos[clave] = (ruta, tipo or tipo_por_extension(ruta))
        ext = os.path.splitext(ruta)[1].lower()
        ext = ext if re.match(r"^\.[a-z0-9]{1,5}$", ext) else ""
        return f"{base}/a/{clave}{ext}"

    def publicar_remoto(self, url, tipo=None, cabeceras=None):
        base = self._base()
        if not base:
            return None
        with self._cerrojo:
            clave = next((k for k, v in self._remotos.items() if v[0] == url), None) or secrets.token_hex(16)
            if len(self._remotos) >= 300:
                self._remotos.pop(next(iter(self._remotos)))
            self._remotos[clave] = (url, tipo or "", dict(cabeceras or {}))
        return f"{base}/p/{clave}"

    @staticmethod
    def _cors(h):
        h.send_header("Access-Control-Allow-Origin", "*")
        h.send_header("Access-Control-Allow-Headers", "Range")
        h.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range, Accept-Ranges")

    def _atender(self, h, cuerpo):
        partes = [p for p in urllib.parse.urlparse(h.path).path.split("/") if p]
        try:
            if len(partes) == 2 and partes[0] == "a":
                a = self._archivos.get(partes[1].split(".")[0])
                if a:
                    return self._servir_archivo(h, a[0], a[1], cuerpo)
            elif len(partes) == 2 and partes[0] == "p":
                r = self._remotos.get(partes[1])
                if r:
                    return self._repetir(h, r[0], r[1], r[2], cuerpo)
            h.send_response(404)
            self._cors(h)
            h.send_header("Content-Length", "0")
            h.end_headers()
        except (ConnectionError, OSError):
            pass  # la tele cerró la conexión (es normal al saltar)

    def _servir_archivo(self, h, ruta, tipo, cuerpo):
        if not os.path.isfile(ruta):
            h.send_response(404)
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        largo = os.path.getsize(ruta)
        cab = h.headers.get("Range")
        rango = rango_pedido(cab, largo)
        if rango is None:
            h.send_response(416)
            self._cors(h)
            h.send_header("Content-Range", f"bytes */{largo}")
            h.send_header("Content-Length", "0")
            h.end_headers()
            return
        desde, hasta = rango
        parcial = bool(cab and cab.strip())
        h.send_response(206 if parcial else 200)
        self._cors(h)
        h.send_header("Content-Type", tipo)
        h.send_header("Accept-Ranges", "bytes")
        if parcial:
            h.send_header("Content-Range", f"bytes {desde}-{hasta}/{largo}")
        n = 0 if largo == 0 else hasta - desde + 1
        h.send_header("Content-Length", str(n))
        h.end_headers()
        if not cuerpo or n == 0:
            return
        with open(ruta, "rb") as f:
            f.seek(desde)
            queda = n
            while queda > 0:
                trozo = f.read(min(256 * 1024, queda))
                if not trozo:
                    break
                h.wfile.write(trozo)
                queda -= len(trozo)

    def _repetir(self, h, url, tipo, cabeceras, cuerpo):
        pedir = {k: v for k, v in cabeceras.items() if k.lower() not in ("accept-encoding", "range")}
        if h.headers.get("Range"):
            pedir["Range"] = h.headers["Range"]
        req = urllib.request.Request(url, headers=pedir, method="GET" if cuerpo else "HEAD")
        try:
            resp = urllib.request.urlopen(req, timeout=30)  # noqa: S310 (enlace que resolvió Caudal)
        except urllib.error.HTTPError as e:
            resp = e
        with resp:
            h.send_response(resp.status if hasattr(resp, "status") else resp.code)
            self._cors(h)
            for c in ("Content-Range", "Accept-Ranges", "Content-Length"):
                v = resp.headers.get(c)
                if v:
                    h.send_header(c, v)
            h.send_header("Content-Type", tipo or resp.headers.get("Content-Type") or "application/octet-stream")
            h.end_headers()
            if not cuerpo:
                return
            while True:
                trozo = resp.read(256 * 1024)
                if not trozo:
                    break
                h.wfile.write(trozo)

    def cerrar(self):
        with self._cerrojo:
            srv, self._srv = self._srv, None
            self._archivos.clear()
            self._remotos.clear()
        if srv:
            srv.shutdown()
            srv.server_close()


# ------------------------------------------------------------------ puente con pychromecast

class Dispositivo:
    def __init__(self, id, nombre, modelo="", info=None):  # noqa: A002
        self.id = str(id)
        self.nombre = nombre or "Chromecast"
        self.modelo = modelo or ""
        self.info = info

    @property
    def es_altavoz(self):
        m = self.modelo.lower()
        return any(x in m for x in ("audio", "speaker", "home", "nest mini", "group", "grupo"))

    def __eq__(self, otro):
        return isinstance(otro, Dispositivo) and otro.id == self.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Dispositivo({self.nombre})"


class PuenteChromecast:
    """Lo que el control necesita de la tele, con pychromecast. Los avisos llegan
    desde hilos de pychromecast: el control los pasa al hilo de la interfaz."""

    def __init__(self):
        self.al_dispositivos = lambda lista: None
        self.al_sesion = lambda dispositivo: None
        self.al_medio = lambda estado, duracion, url, posicion: None
        self.al_volumen = lambda v: None
        self._zconf = None
        self._browser = None
        self._cc = None
        self._dispositivo = None
        self._cerrojo = threading.Lock()

    @property
    def disponible(self):
        return disponible()

    # -- buscar
    def buscar(self):
        import zeroconf
        from pychromecast.discovery import CastBrowser, SimpleCastListener
        with self._cerrojo:
            if self._browser:
                self._avisar_lista()
                return
            self._zconf = self._zconf or zeroconf.Zeroconf()

            def cambio(*_a):
                self._avisar_lista()

            self._browser = CastBrowser(SimpleCastListener(cambio, cambio, cambio), self._zconf)
            self._browser.start_discovery()

    def _avisar_lista(self):
        b = self._browser
        if not b:
            return
        lista = [Dispositivo(i.uuid, i.friendly_name, i.model_name, i) for i in list(b.devices.values())]
        lista.sort(key=lambda d: d.nombre.lower())
        self.al_dispositivos(lista)

    def dejar_de_buscar(self):
        with self._cerrojo:
            b, self._browser = self._browser, None
        if b:
            try:
                b.stop_discovery()
            except Exception:  # noqa: BLE001
                pass

    # -- conectar
    def conectar(self, d):
        """Conecta en otro hilo; la conexión llega por ``al_sesion``."""
        threading.Thread(target=self._conectar, args=(d,), name="caudal-cast-conectar", daemon=True).start()
        return True

    def _conectar(self, d):
        import pychromecast
        from pychromecast.controllers.media import MediaStatusListener
        from pychromecast.socket_client import ConnectionStatusListener
        puente = self

        class Medio(MediaStatusListener):
            def new_media_status(self, s):
                puente._estado_medio(s)

            def load_media_failed(self, _item, _codigo):
                puente.al_medio(ERROR, None, None, None)

        class Conexion(ConnectionStatusListener):
            def new_connection_status(self, s):
                if s.status in ("LOST", "FAILED", "DISCONNECTED") and puente._cc is not None:
                    puente._cc = None
                    puente._dispositivo = None
                    puente.al_sesion(None)

        try:
            from pychromecast.controllers.receiver import CastStatusListener as BaseEstado
        except ImportError:  # versiones viejas
            BaseEstado = object

        class Estado(BaseEstado):
            def new_cast_status(self, s):
                if s is not None and s.volume_level is not None:
                    puente.al_volumen(float(s.volume_level))

        try:
            cc = pychromecast.get_chromecast_from_cast_info(d.info, self._zconf, tries=2, timeout=10)
            cc.wait(timeout=15)
            cc.media_controller.register_status_listener(Medio())
            cc.register_connection_listener(Conexion())
            cc.register_status_listener(Estado())
        except Exception:  # noqa: BLE001
            self.al_sesion(None)
            return
        self._cc = cc
        self._dispositivo = d
        self.al_sesion(d)
        try:
            self.al_volumen(float(cc.status.volume_level))
        except Exception:  # noqa: BLE001
            pass

    def _estado_medio(self, s):
        estado = {"PLAYING": SONANDO, "PAUSED": PAUSA, "BUFFERING": CARGANDO,
                  "LOADING": CARGANDO}.get(s.player_state)
        if estado is None:
            estado = {"FINISHED": TERMINADO, "ERROR": ERROR, "CANCELLED": CORTADO,
                      "INTERRUPTED": CORTADO}.get(s.idle_reason or "", NADA) \
                if s.player_state == "IDLE" else NADA
        self.al_medio(estado, s.duration, s.content_id, s.current_time)

    def desconectar(self):
        cc, self._cc = self._cc, None
        self._dispositivo = None
        if cc:
            def cortar():
                try:
                    cc.quit_app()
                except Exception:  # noqa: BLE001
                    pass
                try:
                    cc.disconnect(timeout=5)
                except Exception:  # noqa: BLE001
                    pass
            threading.Thread(target=cortar, daemon=True).start()

    # -- órdenes (pychromecast las manda sin bloquear la interfaz)
    def _mc(self):
        return self._cc.media_controller if self._cc else None

    def cargar(self, medio, desde=0.0, sonar=True):
        mc = self._mc()
        if not mc:
            return
        metadata = {"metadataType": 3, "title": medio["titulo"], "artist": medio["artista"]}
        if medio.get("album"):
            metadata["albumName"] = medio["album"]
        if medio.get("caratula"):
            metadata["images"] = [{"url": medio["caratula"]}]
        mc.play_media(medio["url"], medio["tipo"], title=medio["titulo"], thumb=medio.get("caratula"),
                      current_time=float(desde or 0), autoplay=bool(sonar), stream_type="BUFFERED",
                      metadata=metadata)

    def sonar(self):
        mc = self._mc()
        if mc:
            mc.play()

    def pausar(self):
        mc = self._mc()
        if mc:
            mc.pause()

    def ir_a(self, segundos):
        mc = self._mc()
        if mc:
            mc.seek(float(segundos))

    def fijar_volumen(self, v):
        if self._cc:
            self._cc.set_volume(max(0.0, min(1.0, float(v))))

    def parar(self):
        mc = self._mc()
        if mc:
            mc.stop()

    def cerrar(self):
        self.dejar_de_buscar()
        self.desconectar()
        z, self._zconf = self._zconf, None
        if z:
            threading.Thread(target=z.close, daemon=True).start()


# ------------------------------------------------------------------ el control

class AnfitrionCast:
    """Lo que el control necesita del reproductor (todo funciones, para poder probarlo)."""

    def __init__(self, pista, fuente, posicion, poner_posicion, duracion, poner_duracion,
                 sonando_local, fijar_estado, callar_local, volver_local, siguiente, aviso):
        self.pista = pista
        self.fuente = fuente
        self.posicion = posicion
        self.poner_posicion = poner_posicion
        self.duracion = duracion
        self.poner_duracion = poner_duracion
        self.sonando_local = sonando_local
        self.fijar_estado = fijar_estado
        self.callar_local = callar_local
        self.volver_local = volver_local
        self.siguiente = siguiente
        self.aviso = aviso


def anfitrion_de(r):
    """El anfitrión para el ``Reproductor`` de reproduccion.py."""

    def poner_posicion(seg):
        r._posicion = float(seg)
        r._emitir_posicion(forzar=True)

    def poner_duracion(seg):
        r._duracion = float(seg)
        r.duracion_cambio.emit(r._duracion)

    def callar_local():
        r._traspaso = None
        r._cortar_fundido()
        for m in r._todos():
            m.detener()

    def volver_local(seg, sonar):
        r._fijar_estado("parado")
        poner_posicion(seg)
        if sonar and r.actual is not None:
            r._cargar(r.actual, inicio=seg, mismo=True)

    return AnfitrionCast(
        pista=lambda: r.actual,
        fuente=lambda: getattr(r, "_fuente", None),
        posicion=lambda: float(r._posicion or 0),
        poner_posicion=poner_posicion,
        duracion=lambda: float(r._duracion or 0),
        poner_duracion=poner_duracion,
        sonando_local=lambda: r.estado in ("sonando", "cargando"),
        fijar_estado=r._fijar_estado,
        callar_local=callar_local,
        volver_local=volver_local,
        siguiente=lambda: r.siguiente(automatico=True),
        aviso=r.aviso.emit,
    )


class ControlCast(QObject):
    """El control de Cast de la PC (ver el docstring del módulo)."""

    cambio = Signal()
    # los avisos de los hilos de pychromecast pasan por aquí al hilo de la interfaz
    _ev_dispositivos = Signal(object)
    _ev_sesion = Signal(object)
    _ev_medio = Signal(object)
    _ev_volumen = Signal(float)

    def __init__(self, anfitrion, puente=None, servidor=None, padre=None):
        super().__init__(padre)
        self.anfitrion = anfitrion
        self.puente = puente if puente is not None else PuenteChromecast()
        self.servidor = servidor if servidor is not None else ServidorCast()
        self.conexion = DESCONECTADO
        self.dispositivo = None
        self.dispositivos = []
        self.buscando = False
        self.volumen = 0.5
        self.estado_medio = NADA
        self._pista = None
        self._url = None
        self._url_original = None
        self._tipo = "audio/mp4"
        self._cabeceras = {}
        self._por_pc = False
        self._empezo = False
        self._gen = 0
        self._base = 0.0
        self._base_en = time.monotonic()
        self._saliendo = False
        # se puede cambiar en las pruebas (para no esperar)
        self.despues = lambda ms, fn: QTimer.singleShot(ms, fn)

        self._ev_dispositivos.connect(self._al_dispositivos)
        self._ev_sesion.connect(self._al_sesion)
        # métodos (no lambdas): así Qt los llama en el hilo de la interfaz
        self._ev_medio.connect(self._al_medio_tupla)
        self._ev_volumen.connect(self._al_volumen)
        self.puente.al_dispositivos = self._ev_dispositivos.emit
        self.puente.al_sesion = self._ev_sesion.emit
        self.puente.al_medio = lambda *t: self._ev_medio.emit(t)
        self.puente.al_volumen = self._ev_volumen.emit

        self._reloj = QTimer(self)
        self._reloj.setInterval(500)
        self._reloj.timeout.connect(self._tic)
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(20000)
        self._espera.timeout.connect(self._tarda_conexion)

    # -- estado
    @property
    def soportado(self):
        return bool(self.puente.disponible)

    @property
    def activo(self):
        return self.conexion == CONECTADO

    # -- buscar y conectar
    def buscar_dispositivos(self):
        if not self.soportado:
            return
        self.buscando = True
        self.cambio.emit()
        try:
            self.puente.buscar()
        except Exception:  # noqa: BLE001
            self.buscando = False
            self.cambio.emit()

    def dejar_de_buscar(self):
        if not self.buscando:
            return
        self.buscando = False
        self.cambio.emit()
        try:
            self.puente.dejar_de_buscar()
        except Exception:  # noqa: BLE001
            pass

    def _al_dispositivos(self, lista):
        self.dispositivos = list(lista)
        self.cambio.emit()

    def conectar(self, d):
        if not self.soportado:
            return
        if self.activo and self.dispositivo == d:
            return
        if self.activo:
            self.desconectar(volver=False)
        self.conexion = CONECTANDO
        self.dispositivo = d
        self.cambio.emit()
        ok = False
        try:
            ok = self.puente.conectar(d)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            self._falla_conexion(d)
            return
        self._espera.start()

    def _tarda_conexion(self):
        if self.conexion == CONECTANDO and self.dispositivo:
            self._falla_conexion(self.dispositivo)

    def _falla_conexion(self, d):
        if self.conexion == CONECTADO:
            return
        self._espera.stop()
        self.conexion = DESCONECTADO
        self.dispositivo = None
        self.cambio.emit()
        self.anfitrion.aviso(f"No pude conectar con «{d.nombre}». Revisa que esté encendido y en la misma red.")
        try:
            self.puente.desconectar()
        except Exception:  # noqa: BLE001
            pass

    def _al_sesion(self, d):
        if d is not None:
            if self.conexion != CONECTADO:
                self._al_conectar(d)
        else:
            self._al_desconectar()

    def _al_conectar(self, d):
        self._espera.stop()
        self._saliendo = False
        self.conexion = CONECTADO
        self.dispositivo = d
        self.estado_medio = NADA
        self._url = None
        self.cambio.emit()
        self.dejar_de_buscar()
        pista, fuente = self.anfitrion.pista(), self.anfitrion.fuente()
        if pista is None or not fuente:
            return
        sonaba = self.anfitrion.sonando_local()
        desde = self.anfitrion.posicion()
        self.anfitrion.callar_local()
        self.enviar(pista, fuente, desde, not sonaba)

    def desconectar(self, volver=True):
        if self.conexion == DESCONECTADO:
            return
        if self.conexion == CONECTANDO:
            self._espera.stop()
            self.conexion = DESCONECTADO
            self.dispositivo = None
            self.cambio.emit()
            self.puente.desconectar()
            return
        punto = self.posicion_ahora()
        sonaba = self.estado_medio in (SONANDO, CARGANDO)
        self._saliendo = True
        self._soltar()
        try:
            self.puente.desconectar()
        except Exception:  # noqa: BLE001
            pass
        if volver:
            self._devolver(punto, sonaba)

    def _al_desconectar(self):
        if self.conexion == CONECTANDO:
            if self.dispositivo:
                self._falla_conexion(self.dispositivo)
            return
        if self.conexion != CONECTADO:
            return
        punto = self.posicion_ahora()
        sonaba = self.estado_medio in (SONANDO, CARGANDO)
        self._soltar()
        self.anfitrion.aviso("Se cortó la conexión con la tele. Sigue sonando en la PC.")
        self._devolver(punto, sonaba)

    def _soltar(self):
        self.conexion = DESCONECTADO
        self.dispositivo = None
        self.estado_medio = NADA
        self._url = None
        self._url_original = None
        self._reloj.stop()
        self._gen += 1
        self.cambio.emit()
        try:
            self.servidor.cerrar()
        except Exception:  # noqa: BLE001
            pass

    def _devolver(self, punto, sonaba):
        pista, self._pista = self._pista, None
        if pista is None or pista is not self.anfitrion.pista():
            return
        self.anfitrion.volver_local(punto, sonaba)

    # -- mandar canciones
    def enviar(self, pista, fuente, inicio=0.0, pausado=False):
        """Manda ``pista`` a la tele (la llama el reproductor en vez de abrirla él)."""
        if not self.activo:
            return
        self._gen += 1
        gen = self._gen
        directa = direccion_de(fuente)
        if not directa:
            self.anfitrion.fijar_estado("parado")
            self.anfitrion.aviso("Esta canción no se puede enviar a la tele.")
            return
        inicio = float(inicio or 0)
        if (pista is self._pista and directa == self._url_original and self._url
                and self.estado_medio not in (TERMINADO, ERROR, NADA)):
            if abs(inicio - self.posicion_ahora()) > 3:
                self.ir_a(inicio)
            return
        self._pista = pista
        self._url_original = directa
        self._por_pc = False
        self._empezo = False
        self._tipo = tipo_de_fuente(fuente)
        self._cabeceras = dict(fuente.get("cabeceras") or {})
        url = directa
        if fuente.get("archivo"):
            url = self.servidor.publicar_archivo(fuente["archivo"], self._tipo)
            if not url:
                self.anfitrion.fijar_estado("parado")
                self.anfitrion.aviso("Para enviar tus descargas, la PC tiene que estar en la misma red que la tele.")
                return
            self._por_pc = True
        self._cargar(gen, pista, url, inicio, pausado)

    def _cargar(self, gen, pista, url, inicio, pausado):
        self._url = url
        self.estado_medio = CARGANDO
        self.anfitrion.fijar_estado("cargando")
        self._fijar_base(inicio)
        self.anfitrion.poner_posicion(inicio)
        medio = {
            "url": url, "tipo": self._tipo,
            "titulo": str(pista.get("titulo") or ""),
            "artista": str(pista.get("artista") or ""),
            "album": str((pista.get("album") or {}).get("nombre") or "") if isinstance(pista.get("album"), dict) else "",
            "caratula": self._caratula(pista),
        }
        if gen != self._gen:
            return
        try:
            self.puente.cargar(medio, inicio, not pausado)
        except Exception:  # noqa: BLE001
            if gen == self._gen:
                self._fallo(gen)

    def _caratula(self, pista):
        m = str(pista.get("miniatura") or pista.get("caratula") or "")
        if not m:
            return None
        if m.startswith("http"):
            return caratula_grande(m)
        try:
            return self.servidor.publicar_archivo(m)
        except Exception:  # noqa: BLE001
            return None

    def _fallo(self, gen):
        pista, original = self._pista, self._url_original
        if pista is None or not original:
            return
        if not self._por_pc and original.startswith("http"):
            self._por_pc = True
            otra = self.servidor.publicar_remoto(original, self._tipo, self._cabeceras)
            if otra and gen == self._gen:
                self._cargar(gen, pista, otra, self.posicion_ahora(), False)
                return
        self.estado_medio = ERROR
        self.anfitrion.fijar_estado("parado")
        self.anfitrion.aviso("La tele no pudo reproducir esta canción. Pasamos a la siguiente.")
        self.despues(1200, lambda: gen == self._gen and self.activo and self.anfitrion.siguiente())

    # -- botones
    def pausar(self):
        if not self.activo:
            return
        self._fijar_base(self.posicion_ahora())
        self.estado_medio = PAUSA
        self.anfitrion.fijar_estado("pausa")
        self._reloj.stop()
        self.puente.pausar()

    def reanudar(self):
        if not self.activo:
            return
        pista = self._pista or self.anfitrion.pista()
        if not self._url or self.estado_medio in (TERMINADO, NADA, CORTADO, ERROR):
            fuente = self.anfitrion.fuente()
            if pista is not None and fuente:
                self._url = None
                self.enviar(pista, fuente, self.anfitrion.posicion())
            return
        self._fijar_base(self.posicion_ahora())
        self.estado_medio = SONANDO
        self.anfitrion.fijar_estado("sonando")
        self._reloj.start()
        self.puente.sonar()

    def alternar(self):
        if self.estado_medio in (SONANDO, CARGANDO):
            self.pausar()
        else:
            self.reanudar()

    def ir_a(self, segundos):
        if not self.activo:
            return
        self._fijar_base(float(segundos))
        self.anfitrion.poner_posicion(float(segundos))
        self.puente.ir_a(float(segundos))

    def parar(self):
        if not self.activo:
            return
        self._gen += 1
        self._fijar_base(self.posicion_ahora())
        self._url = None
        self.estado_medio = NADA
        self._reloj.stop()
        self.puente.parar()

    def fijar_volumen(self, v):
        self.volumen = max(0.0, min(1.0, float(v)))
        self.cambio.emit()
        if self.activo:
            self.puente.fijar_volumen(self.volumen)

    def _al_volumen(self, v):
        self.volumen = max(0.0, min(1.0, float(v)))
        self.cambio.emit()

    # -- lo que dice la tele
    def _al_medio_tupla(self, t):
        self._al_medio(*t)

    def _al_medio(self, estado, duracion=None, url=None, posicion=None):
        if not self.activo or self._saliendo:
            return
        if url and self._url and url != self._url:
            return  # aviso de lo anterior
        if estado == SONANDO:
            self._empezo = True
            if posicion is not None:
                self._fijar_base(float(posicion))
            elif self.estado_medio != SONANDO:
                self._fijar_base(self.posicion_ahora())
            self.estado_medio = SONANDO
            self.anfitrion.fijar_estado("sonando")
            self._reloj.start()
        elif estado == PAUSA:
            self._empezo = True
            self._fijar_base(float(posicion) if posicion is not None else self.posicion_ahora())
            self.estado_medio = PAUSA
            self.anfitrion.fijar_estado("pausa")
            self._reloj.stop()
            self.anfitrion.poner_posicion(self._base)
        elif estado == CARGANDO:
            if self.estado_medio == PAUSA and self._empezo:
                return
            self.estado_medio = CARGANDO
            self.anfitrion.fijar_estado("cargando")
        elif estado == TERMINADO:
            if not self._empezo or not self._url:
                return
            self.estado_medio = TERMINADO
            self._reloj.stop()
            self._url = None
            self.anfitrion.siguiente()
        elif estado == ERROR:
            if self._url:
                self._fallo(self._gen)
            return
        elif estado == CORTADO:
            if self.estado_medio == CARGANDO:
                return
            self.estado_medio = CORTADO
            self._reloj.stop()
            self.anfitrion.fijar_estado("pausa")
        if duracion and duracion > 0 and not self.anfitrion.duracion():
            self.anfitrion.poner_duracion(float(duracion))
        self.cambio.emit()

    # -- posición
    def posicion_ahora(self):
        if self.estado_medio != SONANDO:
            return self._base
        p = self._base + (time.monotonic() - self._base_en)
        d = self.anfitrion.duracion()
        return min(p, d) if d else p

    def _fijar_base(self, p):
        self._base = float(p)
        self._base_en = time.monotonic()

    def _tic(self):
        if self.activo and self.estado_medio == SONANDO:
            self.anfitrion.poner_posicion(self.posicion_ahora())

    def cerrar(self):
        self._reloj.stop()
        try:
            self.puente.cerrar()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.servidor.cerrar()
        except Exception:  # noqa: BLE001
            pass
