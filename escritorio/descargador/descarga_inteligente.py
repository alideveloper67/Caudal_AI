# -*- coding: utf-8 -*-
"""Descarga inteligente: tus me gusta y lo que mas escuchas, bajados solos.

Trabaja en segundo plano y sin molestar:
  - una cancion cada vez, en un hilo de prioridad minima y con la velocidad
    limitada, para que lo que suena por internet no se corte;
  - espera si estas viendo un video por internet, si lo que suena se esta
    cargando o si tienes descargas tuyas en marcha (y pausa la suya si hace falta);
  - baja solo el sonido, sin recomprimir (el formato original de YouTube), en
    una subcarpeta propia de tu carpeta de descargas, hasta el tope de GB.

Lo bajado entra en el historial de descargas como cualquier otra cancion, asi
que suena desde el disco y sin internet.

Ajustes (compartidos con la app movil): 'descarga_inteligente' (bool) y
'descarga_inteligente_gb' (int).
"""

import os
import time

from PySide6.QtCore import QObject, QThread, QThreadPool, QTimer, Signal

CARPETA = "Descarga inteligente"
LIMITE_KBS = 768                 # velocidad maxima de estas descargas (KB/s)
BYTES_POR_SEGUNDO = 20_000       # ~160 kbps: para estimar lo que ocupara una cancion
TAMANO_SIN_DURACION = 6_000_000
DURACION_MAXIMA = 15 * 60        # mezclas de una hora no: solo canciones
INTERVALO_MS = 20_000            # cada cuanto mira si puede seguir
ESPERA_INICIAL_MS = 45_000       # deja arrancar Caudal tranquilo
GB = 1024 ** 3


# ---------------------------------------------------------------- logica pura

def ordenar_candidatos(me_gusta, escuchadas, ya_descargada=None, descartadas=()):
    """Mezcla me gusta y lo mas escuchado (uno y uno, sin repetir) y quita lo
    que no sirve: sin id de YouTube, demasiado largo, ya en el disco o que ya
    fallo. Devuelve la lista de pistas en el orden en que se bajaran."""
    descartadas = set(descartadas or ())
    salida, vistos = [], set()
    a, b = list(me_gusta or []), list(escuchadas or [])
    mezcla = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            mezcla.append(a[i])
        if i < len(b):
            mezcla.append(b[i])
    for p in mezcla:
        vid = (p or {}).get("video_id") or ""
        if not vid or vid in vistos or vid in descartadas:
            continue
        vistos.add(vid)
        dur = int(p.get("duracion") or 0)
        if dur > DURACION_MAXIMA:
            continue
        if ya_descargada is not None and ya_descargada(p):
            continue
        salida.append(p)
    return salida


def tamano_estimado(pista):
    dur = int((pista or {}).get("duracion") or 0)
    return dur * BYTES_POR_SEGUNDO if dur > 0 else TAMANO_SIN_DURACION


def cabe(usado, limite_gb, estimado):
    """¿Entra otra cancion sin pasarse del tope?"""
    try:
        limite = max(0.0, float(limite_gb)) * GB
    except (TypeError, ValueError):
        return False
    return limite > 0 and usado + estimado <= limite


def uso_en_disco(carpeta):
    """Bytes que ocupa la carpeta de la descarga inteligente."""
    total = 0
    if not carpeta or not os.path.isdir(carpeta):
        return 0
    pila = [carpeta]
    while pila:
        actual = pila.pop()
        try:
            with os.scandir(actual) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            pila.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


class _AjustesSuaves:
    """Los ajustes del usuario con lo que esta descarga necesita encima:
    solo audio sin recomprimir, sin pasos pesados y con la velocidad limitada."""

    def __init__(self, ajustes, carpeta):
        self._a = ajustes
        limite = int(ajustes["limite_velocidad"] or 0)
        self._extra = {
            "carpeta": carpeta,
            "tipo_descarga": "audio",
            "formato_audio": "original",
            "modo_musica": False,          # nivelar el audio gasta procesador
            "subtitulos": False,
            "miniatura": False,            # la portada va aparte, al historial
            "metadatos": True,
            "subcarpeta_por_red": False,
            "reintentos": 3,
            "limite_velocidad": min(limite, LIMITE_KBS) if limite else LIMITE_KBS,
        }

    def __getitem__(self, clave):
        if clave in self._extra:
            return self._extra[clave]
        return self._a[clave]

    def get(self, clave, defecto=None):
        try:
            return self[clave]
        except KeyError:
            return defecto


# ---------------------------------------------------------------- el trabajador

class DescargaInteligente(QObject):
    cambio = Signal()               # hay datos nuevos para la pantalla de Ajustes
    descargada = Signal(object)     # una pista mas que ya suena sin internet

    def __init__(self, ajustes, coleccion, reproductor=None, gestor=None, historial=None,
                 padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.coleccion = coleccion
        self.reproductor = reproductor
        self.gestor = gestor            # lo pone quien lo tenga (main o la ventana)
        self.historial = historial
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        try:
            self._pool.setThreadPriority(QThread.LowestPriority)
        except AttributeError:      # Qt anterior a 6.2
            pass
        self._trabajo = None
        self._tarea = None
        self._pista = None
        self._fallos = {}
        self._seguidos = 0
        self._esperar_hasta = 0.0
        self._hechas = 0
        self._motivo = ""
        self._uso_cache = (0.0, 0)
        self._reloj = QTimer(self)
        self._reloj.setInterval(INTERVALO_MS)
        self._reloj.timeout.connect(self.revisar)

    # ------------------------------------------------------------ control

    def iniciar(self):
        self._reloj.start()
        QTimer.singleShot(ESPERA_INICIAL_MS, self.revisar)

    def ajustes_cambiaron(self):
        """La pantalla de Ajustes llama aqui al tocar el interruptor o el tope."""
        self._uso_cache = (0.0, 0)
        if not self.activa() and self._tarea is not None:
            self._tarea.cancelar = True
        QTimer.singleShot(1500, self.revisar)
        self.cambio.emit()

    def activa(self):
        return bool(self.ajustes["descarga_inteligente"])

    def carpeta(self):
        return os.path.join(self.ajustes["carpeta"] or "", CARPETA)

    def usado(self, fresco=False):
        momento, valor = self._uso_cache
        if fresco or time.time() - momento > 60:
            valor = uso_en_disco(self.carpeta())
            self._uso_cache = (time.time(), valor)
        return valor

    def estado(self):
        """Resumen para la pantalla de Ajustes."""
        return {
            "activa": self.activa(),
            "usado": self.usado(),
            "limite_gb": int(self.ajustes["descarga_inteligente_gb"] or 0),
            "bajando": (self._pista or {}).get("titulo", "") if self._tarea else "",
            "hechas": self._hechas,
            "motivo": self._motivo,
            "carpeta": self.carpeta(),
        }

    # ------------------------------------------------------------ cortesia

    def _molesta(self):
        """Motivo para no bajar ahora (texto para la pantalla), o '' si se puede."""
        r = self.reproductor
        if r is not None:
            local = bool((getattr(r, "_fuente", None) or {}).get("local"))
            if r.modo == "video" and r.estado in ("sonando", "cargando") and not local:
                return "Esperando: estás viendo un video por internet."
            if r.estado == "cargando" and r.actual is not None and not local:
                return "Esperando a que cargue lo que suena."
        g = self.gestor
        if g is not None:
            try:
                if g.hay_actividad():
                    return "Esperando a que terminen tus descargas."
            except Exception:  # noqa: BLE001
                pass
        return ""

    # ------------------------------------------------------------ bucle

    def revisar(self):
        if not self.activa():
            self._motivo = ""
            return
        motivo = self._molesta()
        if self._tarea is not None:
            if motivo and not self._tarea.pausar:
                # deja paso: se retoma donde iba (el archivo a medias se conserva)
                self._tarea.pausar = True
                self._motivo = motivo
                self.cambio.emit()
            return
        if motivo:
            self._motivo = motivo
            return
        if time.time() < self._esperar_hasta:
            return
        from .config import ruta_ffmpeg
        if not ruta_ffmpeg():
            self._motivo = "Falta ffmpeg: no se puede guardar el audio."
            return
        siguiente = self._elegir()
        if siguiente is None:
            return
        self._lanzar(siguiente)

    def _elegir(self):
        try:
            gusta = self.coleccion.lista_me_gusta()
            escuchadas = self.coleccion.mas_escuchadas(150, 120)
        except Exception:  # noqa: BLE001
            return None
        en_gestor = set()
        if self.gestor is not None:
            try:
                en_gestor = {t.url for t in self.gestor.lista()}
            except Exception:  # noqa: BLE001
                en_gestor = set()
        descartadas = {v for v, n in self._fallos.items() if n >= 2}
        candidatas = ordenar_candidatos(
            gusta, escuchadas,
            ya_descargada=lambda p: (self.coleccion.copia_local(p.get("video_id")) is not None
                                     or any(p["video_id"] in u for u in en_gestor)),
            descartadas=descartadas)
        if not candidatas:
            self._motivo = "Al día: ya tienes en el disco todo lo que más escuchas."
            self.cambio.emit()
            return None
        p = candidatas[0]
        if not cabe(self.usado(), self.ajustes["descarga_inteligente_gb"], tamano_estimado(p)):
            self._motivo = "Lleno: se alcanzó el espacio que elegiste."
            self.cambio.emit()
            return None
        return p

    def _lanzar(self, pista):
        from .motor import Tarea, TrabajoDescarga
        vid = pista["video_id"]
        url = f"https://music.youtube.com/watch?v={vid}"
        carpeta = self.carpeta()
        try:
            os.makedirs(carpeta, exist_ok=True)
        except OSError:
            self._motivo = "No se pudo crear la carpeta en tus descargas."
            return
        tarea = Tarea(url=url, tipo_pedido="audio",
                      meta={"titulo": pista.get("titulo"), "artista": pista.get("artista"),
                            "duracion": pista.get("duracion")})
        tarea.titulo = pista.get("titulo") or url
        tarea.autor = pista.get("artista") or ""
        tarea.duracion = int(pista.get("duracion") or 0)
        trabajo = TrabajoDescarga(tarea, _AjustesSuaves(self.ajustes, carpeta))
        trabajo.senales.terminada.connect(self._terminada)
        self._trabajo, self._tarea, self._pista = trabajo, tarea, pista
        self._motivo = ""
        self._pool.start(trabajo)
        self.cambio.emit()

    def _terminada(self, _ident, ok, archivo, mensaje):
        tarea, pista = self._tarea, self._pista
        self._trabajo = self._tarea = self._pista = None
        if tarea is None or pista is None:
            return
        vid = pista.get("video_id")
        if ok and archivo and os.path.exists(archivo):
            self._seguidos = 0
            self._fallos.pop(vid, None)
            self._registrar(tarea, pista, archivo)
        elif mensaje == "__cancelada__":
            # pausada para no molestar, o apagada: se retoma en la proxima vuelta
            pass
        else:
            self._fallos[vid] = self._fallos.get(vid, 0) + 1
            self._seguidos += 1
            # sin internet o YouTube protestando: se espera cada vez mas
            espera = 120 if self._seguidos < 5 else 900
            self._esperar_hasta = time.time() + espera
            if self._seguidos >= 5:
                self._fallos.clear()
        self._uso_cache = (0.0, 0)
        self.cambio.emit()
        QTimer.singleShot(3000, self.revisar)

    def _registrar(self, tarea, pista, archivo):
        from .hilos import en_segundo_plano
        from .motor import bajar_miniatura

        def guardar(datos):
            caratula = ""
            if datos:
                try:
                    from .config import carpeta_caratulas
                    destino = carpeta_caratulas() / f"auto-{pista['video_id']}.img"
                    destino.write_bytes(datos)
                    caratula = str(destino)
                except OSError:
                    caratula = ""
            try:
                if self.historial is None:
                    from .historial import Historial
                    self.historial = Historial()
                tamano = os.path.getsize(archivo) if os.path.exists(archivo) else 0
                self.historial.agregar(
                    tarea.url, pista.get("titulo") or tarea.titulo,
                    tarea.plataforma.nombre, archivo, tamano,
                    int(pista.get("duracion") or tarea.duracion or 0),
                    tarea.calidad or "Audio", caratula=caratula, es_audio=True,
                    autor=pista.get("artista") or tarea.autor)
            except Exception:  # noqa: BLE001
                return
            try:
                self.coleccion.invalidar_indice()
            except Exception:  # noqa: BLE001
                pass
            self._hechas += 1
            self.descargada.emit(pista)
            self.cambio.emit()

        url = pista.get("miniatura") or ""
        if "://" in url:
            en_segundo_plano(bajar_miniatura, url, ok=guardar, error=lambda _e: guardar(b""),
                             dueno=self)
        else:
            guardar(b"")
