# -*- coding: utf-8 -*-
"""«Escuchando en Caudal» en tu perfil de Discord (Rich Presence).

Habla con la app de Discord del propio equipo por su canal local (IPC): en Windows la tubería
`\\\\.\\pipe\\discord-ipc-N`, en Linux/macOS el socket `discord-ipc-N`. No usa internet ni
librerías externas: el protocolo es corto (cabecera de 8 bytes + JSON) y va escrito aquí.

- Todo pasa en un hilo propio: la interfaz nunca espera a Discord.
- Si Discord no está abierto (o ni instalado) no pasa nada; se vuelve a probar cada pocos
  segundos, así que si lo abres después, aparece solo.
- Al pausar se ve «En pausa» (y tras un rato en pausa se quita); al parar o cerrar Caudal se
  borra del perfil.
- Hace falta el ID de una aplicación de Discord en ID_APLICACION_DISCORD (abajo). Mientras esté
  vacío, todo esto queda apagado sin errores.
"""

import json
import os
import struct
import sys
import threading
import time
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# EL ÚNICO SITIO DE CONFIGURACIÓN. Pega aquí el «Application ID» de la aplicación «Caudal» del
# portal de desarrolladores de Discord (discord.com/developers/applications). Vacío = apagado.
ID_APLICACION_DISCORD = ""
# ---------------------------------------------------------------------------------------------

WEB_CAUDAL = "https://caudal-musica.netlify.app"
IMAGEN_LOGO = "logo"            # nombre del «Rich Presence Asset» que se sube en el portal
REINTENTO_S = 15.0              # cada cuánto se vuelve a buscar Discord si no está
ENTRE_ENVIOS_S = 4.0            # Discord admite 5 cambios cada 20 s: se agrupan
PAUSA_MAX_S = 15 * 60           # en pausa más de esto: se quita del perfil

OP_SALUDO, OP_MARCO, OP_CIERRE, OP_PING, OP_PONG = 0, 1, 2, 3, 4
TIPO_ESCUCHANDO = 2
CODIGO_ID_INVALIDO = 4000


class ErrorIPC(Exception):
    """Discord no está, se cerró o respondió con un error."""


class IdInvalido(ErrorIPC):
    """Discord dice que ese ID de aplicación no existe: no sirve reintentar."""


# ============================================================================ el canal local


def _rutas_unix():
    bases = [os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP")] + ["/tmp"]
    for base in [b for b in bases if b]:
        for sub in ("", "app/com.discordapp.Discord", "snap.discord", ".flatpak/com.discordapp.Discord/xdg-run"):
            for i in range(10):
                yield os.path.join(base, sub, f"discord-ipc-{i}")


class ConexionIPC:
    """La conexión de verdad con la app de Discord de este equipo."""

    def __init__(self):
        self._f = None        # Windows: archivo de la tubería
        self._s = None        # Linux/macOS: socket

    def conectar(self):
        if sys.platform == "win32":
            for i in range(10):
                try:
                    self._f = open(rf"\\.\pipe\discord-ipc-{i}", "r+b", buffering=0)
                    return
                except OSError:
                    continue
            raise ErrorIPC("Discord no está abierto.")
        import socket
        for ruta in _rutas_unix():
            if not os.path.exists(ruta):
                continue
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                s.settimeout(5)
                s.connect(ruta)
                self._s = s
                return
            except OSError:
                s.close()
        raise ErrorIPC("Discord no está abierto.")

    def _escribir(self, datos):
        if self._f is not None:
            self._f.write(datos)
            self._f.flush()
        elif self._s is not None:
            self._s.sendall(datos)
        else:
            raise ErrorIPC("Sin conexión con Discord.")

    def _leer(self, n):
        trozos, falta = [], n
        while falta > 0:
            if self._f is not None:
                b = self._f.read(falta)
            elif self._s is not None:
                b = self._s.recv(falta)
            else:
                raise ErrorIPC("Sin conexión con Discord.")
            if not b:
                raise ErrorIPC("Discord cerró la conexión.")
            trozos.append(b)
            falta -= len(b)
        return b"".join(trozos)

    def enviar(self, op, carga):
        cuerpo = json.dumps(carga, ensure_ascii=False).encode("utf-8")
        try:
            self._escribir(struct.pack("<II", op, len(cuerpo)) + cuerpo)
        except OSError as e:
            raise ErrorIPC(str(e)) from e

    def recibir(self):
        try:
            op, largo = struct.unpack("<II", self._leer(8))
            cuerpo = self._leer(largo) if largo else b"{}"
        except OSError as e:
            raise ErrorIPC(str(e)) from e
        try:
            return op, json.loads(cuerpo.decode("utf-8"))
        except ValueError:
            return op, {}

    def cerrar(self):
        for c in (self._f, self._s):
            try:
                if c is not None:
                    c.close()
            except OSError:
                pass
        self._f = self._s = None


class ClienteDiscord:
    """Saludo, poner/quitar la actividad y responder a los pings. `fabrica` crea la conexión
    (las pruebas pasan una de mentira)."""

    def __init__(self, id_app, fabrica=ConexionIPC):
        self.id_app = str(id_app)
        self.fabrica = fabrica
        self.con = None
        self.con_tipo = True      # mandar «type: Escuchando» (los Discord viejos no lo aceptan)

    @property
    def conectado(self):
        return self.con is not None

    def conectar(self):
        con = self.fabrica()
        con.conectar()
        try:
            con.enviar(OP_SALUDO, {"v": 1, "client_id": self.id_app})
            op, datos = con.recibir()
        except ErrorIPC:
            con.cerrar()
            raise
        if op == OP_CIERRE:
            con.cerrar()
            if int(datos.get("code") or 0) == CODIGO_ID_INVALIDO:
                raise IdInvalido(datos.get("message") or "ID de aplicación no válido.")
            raise ErrorIPC(datos.get("message") or "Discord rechazó la conexión.")
        if datos.get("evt") == "ERROR":
            con.cerrar()
            raise ErrorIPC((datos.get("data") or {}).get("message") or "Discord rechazó la conexión.")
        self.con = con

    def _orden(self, args):
        carga = {"cmd": "SET_ACTIVITY", "args": args, "nonce": str(uuid.uuid4())}
        self.con.enviar(OP_MARCO, carga)
        while True:
            op, datos = self.con.recibir()
            if op == OP_PING:
                self.con.enviar(OP_PONG, datos)
                continue
            if op == OP_CIERRE:
                self.cerrar()
                raise ErrorIPC(datos.get("message") or "Discord cerró la conexión.")
            if datos.get("nonce") in (None, carga["nonce"]):
                return datos

    def poner_actividad(self, actividad):
        """`actividad` None la quita del perfil."""
        if self.con is None:
            raise ErrorIPC("Sin conexión con Discord.")
        args = {"pid": os.getpid()}
        if actividad is not None:
            act = dict(actividad)
            if not self.con_tipo:
                act.pop("type", None)
            args["activity"] = act
        try:
            r = self._orden(args)
        except ErrorIPC:
            self.cerrar()
            raise
        if r.get("evt") == "ERROR" and actividad is not None and self.con_tipo and "type" in actividad:
            # un Discord que aún no conoce «Escuchando»: se repite sin el tipo y se recuerda
            self.con_tipo = False
            return self.poner_actividad(actividad)
        if r.get("evt") == "ERROR":
            raise ErrorIPC((r.get("data") or {}).get("message") or "Discord no aceptó la actividad.")
        return r

    def cerrar(self):
        if self.con is not None:
            self.con.cerrar()
        self.con = None


# ============================================================================ qué se muestra


def _texto(t, minimo=2, maximo=128):
    """Discord pide textos de 2 a 128 caracteres."""
    t = " ".join(str(t or "").split())
    if len(t) > maximo:
        t = t[: maximo - 1] + "…"
    return t.ljust(minimo) if t else ""


def _artista(pista):
    if pista.get("artista"):
        return str(pista["artista"])
    nombres = [a.get("nombre") for a in pista.get("artistas") or [] if isinstance(a, dict) and a.get("nombre")]
    return ", ".join(nombres)


def _caratula(pista):
    """Solo una dirección pública (https) sirve: Discord la descarga él mismo."""
    url = str(pista.get("miniatura") or "")
    return url if url.startswith("https://") and len(url) <= 256 else ""


def actividad_de(pista, estado, posicion=0.0, duracion=0.0, ahora=None, con_boton=True,
                 en_pausa_desde=None):
    """El dict de actividad para Discord, o None si no hay que mostrar nada."""
    if not pista or estado not in ("sonando", "cargando", "pausa"):
        return None
    ahora = time.time() if ahora is None else ahora
    if estado == "pausa" and en_pausa_desde is not None and ahora - en_pausa_desde > PAUSA_MAX_S:
        return None
    titulo = _texto(pista.get("titulo") or "Sin título")
    artista = _artista(pista)
    album = (pista.get("album") or {}).get("nombre") if isinstance(pista.get("album"), dict) else ""
    act = {"type": TIPO_ESCUCHANDO, "details": titulo, "instance": False}
    if estado == "pausa":
        act["state"] = _texto(f"En pausa · {artista}" if artista else "En pausa")
    else:
        act["state"] = _texto(artista or "Caudal")
        dur = float(duracion or pista.get("duracion") or 0)
        pos = max(0.0, float(posicion or 0))
        inicio = ahora - pos
        act["timestamps"] = {"start": int(inicio * 1000)}
        if dur > 0 and pos <= dur:
            act["timestamps"]["end"] = int((inicio + dur) * 1000)
    caratula = _caratula(pista)
    act["assets"] = {"large_image": caratula or IMAGEN_LOGO,
                     "large_text": _texto(album or pista.get("titulo") or "Caudal")}
    if caratula:
        act["assets"].update({"small_image": IMAGEN_LOGO, "small_text": "Caudal"})
    if con_boton:
        act["buttons"] = [{"label": "Escuchar en Caudal", "url": WEB_CAUDAL}]
    return act


# ============================================================================ el hilo


class PresenciaDiscord:
    """Mantiene el perfil de Discord al día desde un hilo propio. Se le pasa el estado del
    reproductor con `actualizar` (no bloquea) y él se encarga de conectar, reintentar y enviar."""

    def __init__(self, id_app=None, fabrica=ConexionIPC, reintento=REINTENTO_S, entre_envios=ENTRE_ENVIOS_S,
                 reloj=time.time):
        self.id_app = ID_APLICACION_DISCORD if id_app is None else str(id_app or "")
        self.cliente = ClienteDiscord(self.id_app, fabrica) if self.id_app else None
        self.reintento = reintento
        self.entre_envios = entre_envios
        self.reloj = reloj
        self.con_boton = True
        self.activa = True              # el ajuste de la persona
        self.id_invalido = False
        self._estado = None             # (pista, estado, posicion, duracion, cuando)
        self._pausa_desde = None
        self._enviado = "nada"          # lo último que vio Discord (para no repetir)
        self._ultimo_envio = 0.0
        self._cv = threading.Condition()
        self._parar = False
        self._hilo = None

    # ---- lo que llama la interfaz (no bloquea nunca)
    @property
    def disponible(self):
        """Hay ID de aplicación: la función existe."""
        return self.cliente is not None

    @property
    def conectada(self):
        return bool(self.cliente and self.cliente.conectado)

    def actualizar(self, pista, estado, posicion=0.0, duracion=0.0):
        if not self.disponible:
            return
        with self._cv:
            if estado == "pausa":
                if self._pausa_desde is None:
                    self._pausa_desde = self.reloj()
            else:
                self._pausa_desde = None
            self._estado = (pista, estado, float(posicion or 0), float(duracion or 0), self.reloj())
            self._cv.notify()
        self._arrancar()

    def limpiar(self):
        self.actualizar(None, "parado")

    def poner_activa(self, si):
        if not self.disponible:
            return
        with self._cv:
            self.activa = bool(si)
            self._cv.notify()
        self._arrancar()

    def poner_boton(self, si):
        with self._cv:
            self.con_boton = bool(si)
            self._enviado = "cambio"        # que se vuelva a mandar
            self._cv.notify()

    def detener(self, espera=2.0):
        """Al cerrar Caudal: quita la actividad (si se puede en `espera` s) y cierra."""
        hilo = self._hilo
        with self._cv:
            self._estado = None
            self._parar = True
            self._cv.notify()
        if hilo is not None:
            hilo.join(espera)

    # ---- el hilo
    def _arrancar(self):
        if self._hilo is None or not self._hilo.is_alive():
            self._parar = False
            self._hilo = threading.Thread(target=self._bucle, name="discord-presencia", daemon=True)
            self._hilo.start()

    def _deseada(self):
        if not self.activa or self._estado is None:
            return None
        pista, estado, pos, dur, cuando = self._estado
        ahora = self.reloj()
        if estado in ("sonando", "cargando"):
            pos += ahora - cuando        # lo que avanzó desde que se anotó
        return actividad_de(pista, estado, pos, dur, ahora, self.con_boton, self._pausa_desde)

    @staticmethod
    def _firma(act):
        """Para no repetir lo mismo: se ignoran unos segundos de diferencia en los tiempos."""
        if act is None:
            return None
        a = dict(act)
        t = a.pop("timestamps", None) or {}
        return json.dumps(a, sort_keys=True), round(t.get("start", 0) / 3000), round(t.get("end", 0) / 3000)

    def _bucle(self):
        while True:
            with self._cv:
                if self._parar and self._estado is None:
                    break
                deseada = self._deseada()
                firma = self._firma(deseada)
                hace_falta = firma != self._enviado
                if not hace_falta:
                    # nada nuevo: se espera a un cambio (o a que una pausa larga caduque)
                    self._cv.wait(self.reintento if self._pausa_desde else None)
                    continue
                espera = self._ultimo_envio + self.entre_envios - self.reloj()
                if espera > 0 and not self._parar:
                    self._cv.wait(espera)
                    continue
            if self.id_invalido:
                with self._cv:
                    self._enviado = firma
                continue
            try:
                if not self.cliente.conectado:
                    if deseada is None:
                        with self._cv:
                            self._enviado = None      # sin Discord y sin nada que mostrar: listo
                        continue
                    self.cliente.conectar()
                self.cliente.poner_actividad(deseada)
                self._ultimo_envio = self.reloj()
                with self._cv:
                    self._enviado = firma
            except IdInvalido:
                self.id_invalido = True
            except ErrorIPC:
                # Discord no está (o se cerró): se prueba más tarde, sin molestar
                with self._cv:
                    if self._parar:
                        break
                    self._enviado = "reintentar"
                    self._cv.wait(self.reintento)
            except Exception:  # noqa: BLE001 - nunca tumbar Caudal por Discord
                with self._cv:
                    self._enviado = "reintentar"
                    self._cv.wait(self.reintento)
        if self.cliente is not None:
            try:
                if self.cliente.conectado:
                    self.cliente.poner_actividad(None)
            except Exception:  # noqa: BLE001
                pass
            self.cliente.cerrar()


# ============================================================================ ajuste guardado


def _ruta_ajuste(carpeta=None):
    if carpeta is None:
        from .config import carpeta_perfil
        carpeta = carpeta_perfil()
    return Path(carpeta) / "discord.json"


def leer_ajuste(carpeta=None):
    """{"activo": True, "boton": True} por defecto: solo se nota si Discord está abierto."""
    d = {"activo": True, "boton": True}
    try:
        guardado = json.loads(_ruta_ajuste(carpeta).read_text(encoding="utf-8"))
        if isinstance(guardado, dict):
            d.update({k: bool(guardado[k]) for k in d if k in guardado})
    except (OSError, ValueError):
        pass
    return d


def guardar_ajuste(datos, carpeta=None):
    try:
        _ruta_ajuste(carpeta).write_text(json.dumps(datos), encoding="utf-8")
    except OSError:
        pass


# ============================================================================ con el reproductor


def enganchar(reproductor, presencia=None, carpeta=None):
    """Conecta el reproductor de Caudal Escritorio con Discord. Devuelve el enganche (guárdalo
    en ctx.discord para que Ajustes lo encuentre)."""
    from PySide6.QtCore import QCoreApplication, QObject

    class Enganche(QObject):
        def __init__(self):
            super().__init__(reproductor)
            self.r = reproductor
            self.p = presencia or PresenciaDiscord()
            self.carpeta = carpeta
            aj = leer_ajuste(carpeta)
            self.p.activa = aj["activo"]
            self.p.con_boton = aj["boton"]
            self._pos = 0.0
            self._pos_t = time.monotonic()
            if not self.p.disponible:
                return            # sin ID de aplicación: ni se escucha al reproductor
            reproductor.pista_cambio.connect(lambda _p: self._enviar())
            reproductor.estado_cambio.connect(lambda _e: self._enviar())
            reproductor.duracion_cambio.connect(lambda _d: self._enviar())
            reproductor.posicion_cambio.connect(self._posicion)
            app = QCoreApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(lambda: self.p.detener(1.5))
            self._enviar()

        @property
        def disponible(self):
            return self.p.disponible

        @property
        def activa(self):
            return self.p.activa

        @property
        def con_boton(self):
            return self.p.con_boton

        def _posicion(self, s):
            # un salto (adelantar, volver atrás) cambia los tiempos que ve Discord
            ahora = time.monotonic()
            esperada = self._pos + (ahora - self._pos_t) if getattr(self.r, "estado", "") == "sonando" else self._pos
            self._pos, self._pos_t = float(s or 0), ahora
            if abs(self._pos - esperada) > 3:
                self._enviar()

        def _enviar(self):
            r = self.r
            self.p.actualizar(getattr(r, "actual", None), getattr(r, "estado", "parado"),
                              getattr(r, "_posicion", self._pos), getattr(r, "_duracion", 0.0))

        def poner_activa(self, si):
            self.p.poner_activa(si)
            guardar_ajuste({"activo": bool(si), "boton": self.p.con_boton}, self.carpeta)
            self._enviar()

        def poner_boton(self, si):
            self.p.poner_boton(si)
            guardar_ajuste({"activo": self.p.activa, "boton": bool(si)}, self.carpeta)
            self._enviar()

    return Enganche()
