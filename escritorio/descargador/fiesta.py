# -*- coding: utf-8 -*-
"""«Fiesta» por QR (anfitrión en Windows).

El anfitrión abre la fiesta y enseña un QR; los invitados entran desde la web
(/fiesta/<CODIGO>, sin instalar nada), piden canciones y votan. Esta PC pone la
cola de la fiesta en su reproductor y dice qué suena.

Las reglas viven en la base de datos (supabase/fiesta.sql): aquí solo se llaman
sus funciones con la clave pública. El anfitrión se identifica con la `clave`
secreta que devuelve fiesta_crear (solo en memoria: al cerrar Caudal la fiesta
sigue abierta para los invitados, pero esta PC deja de poner su música).

La parte de arriba no usa Qt (se prueba sola); `ControlFiesta` ata la fiesta al
Reproductor y al hilo de la interfaz.
"""

import random
import time

from . import nube

SITIO = "https://caudal-musica.netlify.app"
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
UMBRAL_S = 25            # con tan poco por delante se pide la siguiente de la fiesta
CONSULTA_MS = 20000      # además del tiempo real, se pregunta cada 20 s
LIMITE_DEFECTO = 5


class ErrorFiesta(Exception):
    """Algo que se le puede contar tal cual al usuario."""


# ================================================================ sin Qt

def normalizar_codigo(texto):
    t = "".join(str(texto or "").upper().split()).replace("-", "")
    return t if len(t) == 6 and all(c in ALFABETO for c in t) else ""


def enlace(codigo):
    return f"{SITIO}/fiesta/{codigo}"


def mensaje_de_error(estado, cuerpo):
    """La frase para la persona a partir de la respuesta de la base."""
    d = cuerpo
    if isinstance(cuerpo, (str, bytes)):
        try:
            import json
            d = json.loads(cuerpo)
        except ValueError:
            d = None
    msg = str(d.get("message") or "") if isinstance(d, dict) else ""
    codigo = str(d.get("code") or "") if isinstance(d, dict) else ""
    if codigo == "P0001" and msg:
        return msg
    if codigo == "PGRST202" or "could not find the function" in msg.lower():
        return "La fiesta todavía no está activa en el servidor de Caudal."
    if estado == 429:
        return "Demasiados intentos seguidos. Espera un momento."
    if estado >= 500 or estado == 0:
        return "No pudimos hablar con Caudal. Revisa tu internet y vuelve a probar."
    return "Algo falló. Vuelve a intentarlo."


def llamar(nombre, **parametros):
    """POST /rest/v1/rpc/<nombre>. Devuelve el JSON; lanza ErrorFiesta con una frase."""
    try:
        r = nube._peticion("POST", f"/rest/v1/rpc/{nombre}", json=parametros)
    except nube.ErrorNube as e:
        raise ErrorFiesta(str(e) or mensaje_de_error(0, None)) from e
    if r.status_code >= 400:
        raise ErrorFiesta(mensaje_de_error(r.status_code, r.text))
    if not (r.text or "").strip():
        return None
    try:
        return r.json()
    except ValueError:
        return None


def _n(v, defecto=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return defecto


def _https(u):
    u = u if isinstance(u, str) else ""
    return u if u.startswith("https://") and len(u) <= 500 and not any(c in u for c in ' "\'<>') else ""


def leer_cancion(c):
    return {
        "id": _n(c.get("id")), "video_id": str(c.get("video_id") or ""),
        "titulo": str(c.get("titulo") or "Sin título"), "artista": str(c.get("artista") or ""),
        "miniatura": _https(c.get("miniatura")), "duracion": _n(c.get("duracion")),
        "nombre": str(c.get("nombre") or ""), "votos": _n(c.get("votos")),
        "estado": str(c.get("estado") or "cola"), "de_anfitrion": c.get("de_anfitrion") is True,
    }


def ordenar_cola(cola):
    """Como sonarán: más votos primero; a igualdad, la que llegó antes."""
    return sorted(cola, key=lambda c: (-c["votos"], c["id"]))


def leer_fiesta(d):
    """Lo que devuelve fiesta_ver, limpio. None si la fiesta no existe."""
    if not isinstance(d, dict):
        return None
    lista = lambda v: [leer_cancion(c) for c in (v if isinstance(v, list) else []) if isinstance(c, dict)]  # noqa: E731
    s = d.get("sonando") if isinstance(d.get("sonando"), dict) else None
    return {
        "codigo": str(d.get("codigo") or ""), "nombre": str(d.get("nombre") or "Fiesta"),
        "abierta": d.get("abierta") is not False, "limite": _n(d.get("limite")),
        "version": _n(d.get("version")), "invitados": _n(d.get("invitados")),
        "sonando": None if s is None else {
            "video_id": str(s.get("video_id") or ""), "titulo": str(s.get("titulo") or ""),
            "artista": str(s.get("artista") or ""), "miniatura": _https(s.get("miniatura")),
            "duracion": _n(s.get("duracion")), "pausa": s.get("pausa") is True,
            "fiesta_id": None if s.get("fiesta_id") is None else _n(s.get("fiesta_id")),
            "nombre": str(s.get("nombre") or ""),
        },
        "cola": ordenar_cola(lista(d.get("cola"))),
        "sonadas": [c for c in lista(d.get("sonadas")) if c["estado"] == "sonada"],
    }


def pista_de_cancion(c):
    """Una canción de la fiesta como pista del reproductor (con su fiesta_id)."""
    from .catalogo import nueva_pista
    artistas = [{"nombre": c.get("artista"), "id": ""}] if c.get("artista") else []
    p = nueva_pista(c["video_id"], titulo=c.get("titulo") or "", artistas=artistas,
                    duracion=c.get("duracion") or 0, miniatura=c.get("miniatura") or "")
    p["fiesta_id"] = c.get("id")
    if c.get("nombre"):
        p["fiesta_nombre"] = c["nombre"]
    return p


def pista_para_sonando(pista, pos_ms=0, pausa=False):
    """Lo que se manda a fiesta_sonando (None = no suena nada)."""
    if not pista:
        return None
    d = {
        "video_id": str(pista.get("video_id") or ""),
        "titulo": str(pista.get("titulo") or "")[:200],
        "artista": str(pista.get("artista") or "")[:200],
        "miniatura": _https(pista.get("miniatura")),
        "duracion": max(0, _n(pista.get("duracion"))),
        "pos_ms": max(0, int(pos_ms or 0)),
        "pausa": bool(pausa),
    }
    if pista.get("fiesta_id") is not None:
        d["fiesta_id"] = pista.get("fiesta_id")
    return d


def hay_pendiente(proximas):
    """¿Ya hay una canción de la fiesta esperando en la cola del reproductor?"""
    return any(isinstance(p, dict) and p.get("fiesta_id") is not None for p in (proximas or []))


def debe_tomar(hay_actual, estado, restante_s, pendiente):
    """¿Toca pedir la siguiente canción de la fiesta?

    Sí cuando no suena nada, o cuando a la canción actual le quedan UMBRAL_S
    segundos o menos; nunca si ya hay una de la fiesta esperando, ni en pausa."""
    if pendiente:
        return False
    if not hay_actual or estado == "parado":
        return True
    if estado == "pausa":
        return False
    return restante_s is not None and restante_s <= UMBRAL_S


def nuevo_id():
    return "".join(random.SystemRandom().choice(ALFABETO) for _ in range(12))


# las llamadas de la base, una por una
def crear(nombre="", limite=LIMITE_DEFECTO):
    d = llamar("fiesta_crear", p_nombre=nombre or None, p_limite=int(limite))
    if not isinstance(d, dict) or not d.get("codigo") or not d.get("clave"):
        raise ErrorFiesta("No se pudo crear la fiesta. Vuelve a intentarlo.")
    return str(d["codigo"]), str(d["clave"])


def ver(codigo):
    return leer_fiesta(llamar("fiesta_ver", p_codigo=codigo))


def quitar(codigo, clave, cancion_id):
    return leer_fiesta(llamar("fiesta_quitar", p_codigo=codigo, p_clave=clave, p_cancion=int(cancion_id)))


def poner_limite(codigo, clave, limite):
    return leer_fiesta(llamar("fiesta_limite", p_codigo=codigo, p_clave=clave, p_limite=int(limite)))


def cerrar(codigo, clave):
    return leer_fiesta(llamar("fiesta_cerrar", p_codigo=codigo, p_clave=clave))


def tomar(codigo, clave):
    d = llamar("fiesta_tomar", p_codigo=codigo, p_clave=clave)
    return leer_cancion(d) if isinstance(d, dict) else None


def sonando(codigo, clave, datos):
    return leer_fiesta(llamar("fiesta_sonando", p_codigo=codigo, p_clave=clave, p_pista=datos))


# ================================================================ con Qt

try:
    from PySide6.QtCore import QObject, QTimer, Signal, Slot
except ImportError:  # pragma: no cover
    QObject = object


if QObject is not object:

    class _Puente(QObject):
        """Lleva funciones del hilo del websocket al de la interfaz."""
        llega = Signal(object)

        def __init__(self, padre=None):
            super().__init__(padre)
            self.llega.connect(self._ejecutar)

        @Slot(object)
        def _ejecutar(self, f):
            try:
                f()
            except Exception:  # noqa: BLE001
                import traceback
                traceback.print_exc()

    class ControlFiesta(QObject):
        """La fiesta abierta en esta PC (una a la vez) atada al reproductor."""
        cambio = Signal()          # llegó un estado nuevo de la fiesta (o se abrió/cerró)
        error = Signal(str)
        aviso = Signal(str)

        def __init__(self, ctx, padre=None, api=None, en_fondo=None):
            super().__init__(padre)
            self.ctx = ctx
            self.r = getattr(ctx, "reproductor", None)
            # `api` y `en_fondo` se cambian en las pruebas
            self.api = api or {"crear": crear, "ver": ver, "quitar": quitar, "limite": poner_limite,
                               "cerrar": cerrar, "tomar": tomar, "sonando": sonando}
            if en_fondo is None:
                from .hilos import en_segundo_plano
                en_fondo = lambda f, *a, ok=None, error=None: en_segundo_plano(  # noqa: E731
                    f, *a, ok=ok, error=error, dueno=self, urgente=True)
            self._en_fondo = en_fondo
            self.codigo = None
            self.clave = None
            self.fiesta = None
            self.auto = True
            self.creando = False
            self._tomando = False
            self._ultimo_tomar = 0.0
            self._posicion = 0.0
            self._duracion = 0.0
            self._canal = None
            self._puente = _Puente(self)
            self._consulta = QTimer(self)
            self._consulta.setInterval(CONSULTA_MS)
            self._consulta.timeout.connect(self.refrescar)
            self._tic = QTimer(self)
            self._tic.setInterval(1000)
            self._tic.timeout.connect(self.revisar)
            self._aviso_sonando = QTimer(self)
            self._aviso_sonando.setSingleShot(True)
            self._aviso_sonando.setInterval(400)
            self._aviso_sonando.timeout.connect(self._mandar_sonando)
            self._atado = False

        # ------------------------------------------------------------ estado
        @property
        def abierta(self):
            return bool(self.codigo and self.fiesta and self.fiesta["abierta"])

        @property
        def enlace(self):
            return enlace(self.codigo) if self.codigo else ""

        def _llamar(self, que, *args, ok=None, avisar_error=True):
            def bien(res):
                if ok:
                    ok(res)

            def mal(e):
                if avisar_error:
                    self.error.emit(str(e) if isinstance(e, ErrorFiesta) else
                                    "No pudimos hablar con Caudal. Revisa tu internet y vuelve a probar.")
            self._en_fondo(self.api[que], *args, ok=bien, error=mal)

        def _aplicar(self, f):
            if f is None:
                return
            if self.fiesta and f["version"] < self.fiesta["version"] and f["abierta"]:
                return                       # respuesta vieja
            self.fiesta = f
            if not f["abierta"]:
                self._parar()
            self.cambio.emit()
            self.revisar()

        # ------------------------------------------------------------ abrir y cerrar
        def crear(self, nombre="", limite=LIMITE_DEFECTO):
            if self.creando:
                return
            self.creando = True
            self.cambio.emit()

            def listo(res):
                self.creando = False
                self.codigo, self.clave = res
                self.fiesta = {"codigo": self.codigo, "nombre": (nombre or "").strip() or "Fiesta",
                               "abierta": True, "limite": int(limite), "version": 0, "invitados": 0,
                               "sonando": None, "cola": [], "sonadas": []}
                self._empezar()
                self.cambio.emit()
                self.refrescar()

            def fallo(e):
                self.creando = False
                self.cambio.emit()
                self.error.emit(str(e) if isinstance(e, ErrorFiesta) else "No se pudo crear la fiesta.")
            self._en_fondo(self.api["crear"], nombre, int(limite), ok=listo, error=fallo)

        def _empezar(self):
            self._consulta.start()
            self._tic.start()
            if self.r is not None and not self._atado:
                self._atado = True
                for senal, f in self._senales():
                    senal.connect(f)
            self._abrir_canal()
            self._avisar_sonando()

        def _senales(self):
            r = self.r
            lista = []
            for nombre, f in (("pista_cambio", self._al_pista), ("estado_cambio", self._al_estado),
                              ("posicion_cambio", self._al_posicion), ("duracion_cambio", self._al_duracion)):
                s = getattr(r, nombre, None)
                if s is not None:
                    lista.append((s, f))
            return lista

        def _abrir_canal(self):
            try:
                from .juntos import CanalRealtime
            except Exception:  # noqa: BLE001 - sin tiempo real sigue la consulta cada 20 s
                return
            try:
                self._canal = CanalRealtime(f"realtime:fiesta-{self.codigo}", nuevo_id(),
                                            al_mensaje=self._al_mensaje,
                                            despachar=self._puente.llega.emit)
                self._canal.abrir()
            except Exception:  # noqa: BLE001
                self._canal = None

        def _al_mensaje(self, evento, datos):
            if evento != "cambio":
                return
            v = _n((datos or {}).get("version"))
            if not self.fiesta or v > self.fiesta["version"]:
                self.refrescar()

        def _parar(self):
            self._consulta.stop()
            self._tic.stop()
            if self._canal is not None:
                try:
                    self._canal.cerrar()
                except Exception:  # noqa: BLE001
                    pass
                self._canal = None
            if self._atado:
                self._atado = False
                for senal, f in self._senales():
                    try:
                        senal.disconnect(f)
                    except (RuntimeError, TypeError):
                        pass

        def cerrar(self):
            if not self.codigo:
                return
            self._llamar("cerrar", self.codigo, self.clave, ok=self._aplicar)

        def olvidar(self):
            """Deja la fiesta (ya cerrada) para poder abrir otra."""
            self._parar()
            self.codigo = self.clave = self.fiesta = None
            self.cambio.emit()

        # ------------------------------------------------------------ anfitrión
        def refrescar(self):
            if self.codigo:
                self._llamar("ver", self.codigo, ok=self._aplicar, avisar_error=False)

        def quitar(self, cancion_id):
            if self.fiesta:
                self.fiesta = dict(self.fiesta, cola=[c for c in self.fiesta["cola"] if c["id"] != cancion_id])
                self.cambio.emit()
            self._llamar("quitar", self.codigo, self.clave, cancion_id, ok=self._aplicar)

        def poner_limite(self, limite):
            if self.fiesta and self.fiesta["limite"] == int(limite):
                return
            self._llamar("limite", self.codigo, self.clave, int(limite), ok=self._aplicar)

        def poner_auto(self, si):
            self.auto = bool(si)
            self.revisar()

        def poner_ahora(self, cancion):
            """Suena ya esta canción de la cola (sale de la cola al avisar qué suena)."""
            if self.r is None:
                return
            self.r.reproducir_pista(pista_de_cancion(cancion), con_radio=False)

        # ------------------------------------------------------------ reproductor
        def _al_pista(self, *_):
            self._posicion = 0.0
            self._avisar_sonando()

        def _al_estado(self, *_):
            self._avisar_sonando()
            self.revisar()

        def _al_posicion(self, s):
            self._posicion = float(s or 0)

        def _al_duracion(self, s):
            self._duracion = float(s or 0)

        def _avisar_sonando(self):
            if self.abierta:
                self._aviso_sonando.start()

        def _mandar_sonando(self):
            if not self.abierta or self.r is None:
                return
            p = getattr(self.r, "actual", None)
            estado = getattr(self.r, "estado", "parado")
            datos = None if (p is None or estado == "parado") else pista_para_sonando(
                p, int(self._posicion * 1000), estado == "pausa")
            self._llamar("sonando", self.codigo, self.clave, datos, ok=self._aplicar, avisar_error=False)

        def restante(self):
            dur = self._duracion or float((getattr(self.r, "actual", None) or {}).get("duracion") or 0)
            if dur <= 0:
                return None
            return max(0.0, dur - self._posicion)

        def revisar(self):
            """Cada segundo (y en cada cambio): ¿hay que poner la siguiente de la fiesta?"""
            if not (self.auto and self.abierta and self.r is not None) or self._tomando:
                return
            if not self.fiesta["cola"] or time.monotonic() - self._ultimo_tomar < 3:
                return
            if not debe_tomar(getattr(self.r, "actual", None) is not None, getattr(self.r, "estado", "parado"),
                              self.restante(), hay_pendiente(getattr(self.r, "proximas", []))):
                return
            self._tomando = True
            self._ultimo_tomar = time.monotonic()

            def listo(c):
                self._tomando = False
                if c and c.get("video_id"):
                    self._poner(c)
                self.refrescar()

            def fallo(_e):
                self._tomando = False
            self._en_fondo(self.api["tomar"], self.codigo, self.clave, ok=listo, error=fallo)

        def _poner(self, c):
            pista = pista_de_cancion(c)
            if getattr(self.r, "actual", None) is None or getattr(self.r, "estado", "parado") == "parado":
                self.r.reproducir_lista([pista], 0, {"tipo": "cola", "id": "", "titulo": "Fiesta"})
            else:
                self.r.reproducir_despues([pista])
            quien = f" (la pidió {c['nombre']})" if c.get("nombre") else ""
            self.aviso.emit(f"De la fiesta: «{c['titulo']}»{quien}")

    def control(ctx):
        """El ControlFiesta de la app (uno solo)."""
        c = getattr(ctx, "_control_fiesta", None)
        if c is None:
            c = ControlFiesta(ctx, ctx if isinstance(ctx, QObject) else None)
            ctx._control_fiesta = c
            aviso = getattr(ctx, "aviso", None)
            if aviso is not None:
                c.aviso.connect(aviso.emit)
        return c
