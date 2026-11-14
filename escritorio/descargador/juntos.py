# -*- coding: utf-8 -*-
"""«Escuchar juntos»: salas sin tablas sobre Supabase Realtime (Broadcast +
Presence) por websocket, con el protocolo de Phoenix.

Es el mismo protocolo que la app movil (app/lib/nucleo/juntos.dart), descrito
en supabase/JUNTOS.md: la PC y el telefono pueden estar en la misma sala.

- Presence dice quien esta en la sala (cada aparato es un miembro).
- El anfitrion manda por Broadcast lo que suena (pista, posicion, pausa) cada
  2,5 s y al instante si cambia algo; los demas lo siguen.
- Cada invitado mide la diferencia entre su reloj y el del anfitrion con
  ping/pong y salta a su posicion si se aleja mas de 1,5 s.
- Si el anfitrion se va, lo es el miembro que lleva mas tiempo en la sala.

Hilos: el websocket vive en un hilo propio. Todo lo que llega se entrega con
`despachar(funcion)`, que debe ejecutarla en el hilo del dueno (en la app, el
hilo de la interfaz: ver `SalaQt`). La sala (`SalaJuntos`) solo se toca desde
ese hilo y nunca bloquea: abrir, mandar y salir vuelven al instante.
"""

import itertools
import json
import queue
import random
import re
import threading
import time
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from . import nube

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover - se avisa al abrir una sala
    websocket = None

DESFASE_MAXIMO_MS = 1500
EMOJIS = ["❤️", "🔥", "😂", "😍", "👏", "🎉", "😮", "🕺"]

# El chat de la sala: mensajes cortos que no se guardan en ningun sitio.
# Quien pone la musica guarda los ultimos y se los pasa a quien entra.
LARGO_CHAT = 500
HISTORIAL_CHAT = 40


def mensaje_chat_valido(d):
    """{'de', 'nombre', 'texto', 't'} limpio, o None si no sirve."""
    if not isinstance(d, dict):
        return None
    texto = str(d.get("texto") or "").strip()[:LARGO_CHAT]
    if not texto:
        return None
    return {"de": str(d.get("de") or ""), "nombre": str(d.get("nombre") or "Alguien")[:40],
            "texto": texto, "t": _entero(d.get("t"), ahora_ms())}
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I
_azar = random.SystemRandom()

TIC_MS = 500
PING_MS = 4000
ESTADO_MS = 2500
ESPERA_ANFITRION_MS = 5000
LATIDO_S = 25
ESPERA_UNION_S = 12


def ahora_ms():
    return int(time.time() * 1000)


def nuevo_codigo():
    """Codigo corto de sala: 6 caracteres faciles de dictar."""
    return "".join(_azar.choice(ALFABETO) for _ in range(6))


def nuevo_id():
    return "".join(_azar.choice(ALFABETO) for _ in range(12))


def enlace_sala(codigo):
    return f"caudal://juntos?sala={codigo}"


def codigo_de_texto(texto):
    """Saca el codigo de un enlace (caudal://juntos?sala=…, https://…?sala=…)
    o de lo que se escribio a mano. None si no parece un codigo."""
    t = (texto or "").strip()
    try:
        sala = parse_qs(urlparse(t).query).get("sala")
    except ValueError:
        sala = None
    if sala:
        t = sala[0]
    t = re.sub(r"[\s-]", "", t.upper())
    return t if re.fullmatch(f"[{ALFABETO}]{{6}}", t) else None


def pista_para_compartir(p):
    """Solo datos sencillos y nunca rutas de archivos de este aparato."""
    return {k: v for k, v in (p or {}).items()
            if k != "archivo" and isinstance(v, (str, int, float, bool))}


def clave_pista(p):
    if not p:
        return ""
    v = str(p.get("video_id") or "")
    if v:
        return "v:" + v
    c = str(p.get("clave") or "")
    if c:
        return "c:" + c
    return f"t:{p.get('titulo') or ''}|{p.get('artista') or ''}"


def posicion_esperada(pos_ms, sonando, enviado_ms, diferencia, ahora_local=None, velocidad=1.0):
    """Donde deberia ir la cancion del anfitrion AHORA en este aparato (ms).
    `diferencia` = reloj del anfitrion - reloj local (ms)."""
    if not sonando:
        return int(pos_ms)
    local = ahora_ms() if ahora_local is None else ahora_local
    transcurrido = max(0, local + diferencia - enviado_ms)
    return int(pos_ms + round(transcurrido * velocidad))


def _entero(v, defecto=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return defecto


class ErrorJuntos(Exception):
    """Algo que se le puede contar tal cual al usuario."""


# ====================================================================== canal

class CanalRealtime:
    """Un canal de Supabase Realtime (Phoenix vsn 1.0.0) con latido y
    reconexion. Sin tablas: solo Broadcast y Presence.

    Las funciones `al_*` se llaman a traves de `despachar`, en el hilo del dueno.
    `presentes` (clave -> ultima meta) solo cambia en ese hilo.
    """

    def __init__(self, tema, clave_presencia, al_mensaje=None, al_presencia=None,
                 al_estado_conexion=None, al_abierto=None, despachar=None,
                 url_base=None, clave=None):
        self.tema = tema
        self.clave_presencia = clave_presencia
        self.al_mensaje = al_mensaje
        self.al_presencia = al_presencia
        self.al_estado_conexion = al_estado_conexion
        self.al_abierto = al_abierto          # (error o None) una sola vez
        self.despachar = despachar or (lambda f: f())
        self._url_base = url_base or nube.URL
        self._clave = clave or nube.CLAVE_PUBLICA
        self.presentes = {}
        self.unido = False
        self._ws = None
        self._refs = itertools.count(1)
        self._ref_union = None
        self._latido_pendiente = None
        self._mi_presencia = None
        self._cerrado = threading.Event()
        self._envio = threading.Lock()
        self._abierto_avisado = False
        self._hilo = None

    @property
    def url(self):
        u = urlparse(self._url_base)
        esquema = "ws" if u.scheme == "http" else "wss"
        return f"{esquema}://{u.netloc}/realtime/v1/websocket?apikey={self._clave}&vsn=1.0.0"

    # ---------------------------------------------------------------- abrir
    def abrir(self):
        """Conecta en segundo plano; `al_abierto(None)` al entrar, o con el error."""
        if websocket is None:
            self._avisar_abierto(ErrorJuntos(
                "Falta el componente websocket-client: reinstala Caudal."))
            return
        self._cerrado.clear()
        self._hilo = threading.Thread(target=self._bucle, name=f"juntos-{self.tema}", daemon=True)
        self._hilo.start()

    def _siguiente_ref(self):
        return str(next(self._refs))

    def _avisar_abierto(self, error):
        if self._abierto_avisado:
            return
        self._abierto_avisado = True
        if self.al_abierto:
            self.despachar(lambda: self.al_abierto(error))

    def _bucle(self):
        intentos = 0
        while not self._cerrado.is_set():
            try:
                ws = websocket.create_connection(self.url, timeout=10, enable_multithread=True)
            except Exception as e:  # noqa: BLE001
                texto = str(e)
                if not self._abierto_avisado:
                    if "404" in texto or "403" in texto:
                        self._avisar_abierto(ErrorJuntos(
                            "El servicio de salas (Supabase Realtime) no está habilitado."))
                    else:
                        self._avisar_abierto(ErrorJuntos(
                            "Sin conexión con el servicio de salas. Revisa tu internet."))
                    return
                espera = [1, 2, 4, 8, 15][min(intentos, 4)]
                intentos += 1
                if self._cerrado.wait(espera):
                    return
                continue
            if self._cerrado.is_set():
                self._cerrar_ws(ws)
                return
            intentos = 0
            self._ws = ws
            fin_conexion = threading.Event()
            latido = threading.Thread(target=self._latir, args=(ws, fin_conexion), daemon=True)
            try:
                ws.settimeout(None)
                self._ref_union = self._siguiente_ref()
                self._enviar_crudo("phx_join", {"config": {
                    "broadcast": {"self": False, "ack": False},
                    "presence": {"key": self.clave_presencia, "enabled": True},
                    "postgres_changes": [], "private": False}}, ref=self._ref_union)
                latido.start()
                while not self._cerrado.is_set():
                    crudo = ws.recv()
                    if not crudo:
                        break
                    self._recibir(crudo)
            except Exception:  # noqa: BLE001 - conexion caida
                pass
            fin_conexion.set()
            self._ws = None
            self._cerrar_ws(ws)
            if self.unido:
                self.unido = False
                if self.al_estado_conexion:
                    self.despachar(lambda: self.al_estado_conexion(False))
            if self._cerrado.is_set():
                return
            if not self._abierto_avisado:
                self._avisar_abierto(ErrorJuntos("Se cortó la conexión con la sala."))
                return
            espera = [1, 2, 4, 8, 15][min(intentos, 4)]
            intentos += 1
            if self._cerrado.wait(espera):
                return

    def _latir(self, ws, fin):
        self._latido_pendiente = None
        inicio = ultimo = time.monotonic()
        while not fin.wait(1):
            ahora = time.monotonic()
            if not self._abierto_avisado and ahora - inicio > ESPERA_UNION_S:
                self._avisar_abierto(ErrorJuntos(
                    "La sala no respondió. Revisa tu conexión a internet."))
                self._cerrado.set()
                self._cerrar_ws(ws)
                return
            if ahora - ultimo < LATIDO_S:
                continue
            ultimo = ahora
            if self._latido_pendiente is not None:
                # el anterior no volvio: la conexion esta muerta aunque no lo parezca
                self._cerrar_ws(ws)
                return
            self._latido_pendiente = self._siguiente_ref()
            self._mandar(ws, {"topic": "phoenix", "event": "heartbeat", "payload": {},
                              "ref": self._latido_pendiente})

    def _mandar(self, ws, mensaje):
        if ws is None:
            return False
        try:
            with self._envio:
                ws.send(json.dumps(mensaje, ensure_ascii=False))
            return True
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _cerrar_ws(ws):
        try:
            ws.abort()
        except Exception:  # noqa: BLE001
            pass
        try:
            ws.close(timeout=0.5)
        except Exception:  # noqa: BLE001
            pass

    def _enviar_crudo(self, evento, datos, ref=None):
        return self._mandar(self._ws, {"topic": self.tema, "event": evento, "payload": datos,
                                       "ref": ref or self._siguiente_ref(),
                                       "join_ref": self._ref_union})

    # ---------------------------------------------------------------- enviar
    def difundir(self, evento, datos):
        """Manda un aviso a todos los demas de la sala (no vuelve a uno mismo)."""
        if not self.unido:
            return
        self._enviar_crudo("broadcast", {"type": "broadcast", "event": evento, "payload": datos})

    def presentarme(self, datos):
        """Anuncia (o actualiza) quien soy en la lista de la sala."""
        self._mi_presencia = datos
        if self.unido:
            self._enviar_crudo("presence", {"type": "presence", "event": "track",
                                            "payload": datos})

    # ---------------------------------------------------------------- recibir
    def _recibir(self, crudo):
        try:
            m = json.loads(crudo)
        except ValueError:
            return
        if not isinstance(m, dict):
            return
        evento = str(m.get("event"))
        datos = m.get("payload") if isinstance(m.get("payload"), dict) else {}
        if m.get("topic") == "phoenix":
            if evento == "phx_reply" and m.get("ref") == self._latido_pendiente:
                self._latido_pendiente = None
            return
        if m.get("topic") != self.tema:
            return
        if evento == "phx_reply":
            if m.get("ref") != self._ref_union:
                return
            if datos.get("status") == "ok":
                self.unido = True
                if self._mi_presencia is not None:
                    self.presentarme(self._mi_presencia)
                if self.al_estado_conexion:
                    self.despachar(lambda: self.al_estado_conexion(True))
                self._avisar_abierto(None)
            else:
                resp = datos.get("response")
                r = str((resp.get("reason") if isinstance(resp, dict) else resp) or "")
                if not self._abierto_avisado:
                    self._cerrado.set()
                self._avisar_abierto(ErrorJuntos(
                    "La sala rechazó la entrada" + (f": {r}." if r else ".")))
                raise ConnectionError("union rechazada")
        elif evento == "presence_state":
            self.despachar(lambda: self._estado_presencia(datos))
        elif evento == "presence_diff":
            self.despachar(lambda: self._diferencia_presencia(datos))
        elif evento == "broadcast":
            ev = str(datos.get("event") or "")
            p = datos.get("payload") if isinstance(datos.get("payload"), dict) else {}
            if self.al_mensaje:
                self.despachar(lambda: self.al_mensaje(ev, p))
        elif evento in ("phx_error", "phx_close"):
            if not self._cerrado.is_set():
                raise ConnectionError(evento)
        elif evento == "system" and datos.get("status") == "error":
            self._avisar_abierto(ErrorJuntos(
                f"El servicio de salas falló: {datos.get('message') or ''}"))

    # --- en el hilo del dueno
    def _sumar(self, entradas):
        for clave, v in (entradas or {}).items():
            metas = v.get("metas") if isinstance(v, dict) else None
            if metas and isinstance(metas[-1], dict):
                self.presentes[clave] = metas[-1]

    def _estado_presencia(self, datos):
        self.presentes.clear()
        self._sumar(datos)
        if self.al_presencia:
            self.al_presencia()

    def _diferencia_presencia(self, datos):
        for k in (datos.get("leaves") or {}):
            self.presentes.pop(k, None)
        self._sumar(datos.get("joins") or {})
        if self.al_presencia:
            self.al_presencia()

    # ---------------------------------------------------------------- cerrar
    def cerrar(self):
        """Sale de la sala sin esperar a la red."""
        if self._cerrado.is_set():
            return
        ws = self._ws
        if ws is not None and self.unido:
            self._enviar_crudo("phx_leave", {})
        self._cerrado.set()
        self.unido = False
        if ws is not None:
            threading.Thread(target=self._cerrar_ws, args=(ws,), daemon=True).start()


# ================================================================ reproductor

class Control:
    """Lo que la sala necesita del reproductor (asi se prueba sin libmpv).
    Posiciones en milisegundos."""

    pista = None          # dict o None
    posicion_ms = 0
    sonando = False
    cargando = False      # cargando una pista: no se corrige la posicion

    def cargar(self, pista, inicio_ms=0, pausado=False):
        raise NotImplementedError

    def buscar(self, ms):
        raise NotImplementedError

    def pausar(self):
        raise NotImplementedError

    def reanudar(self):
        raise NotImplementedError


class ControlReproductor(Control):
    """El Reproductor de la app visto como Control (hilo de la interfaz)."""

    def __init__(self, r, titulo="Escuchar juntos"):
        self.r = r
        self.titulo = titulo

    @property
    def pista(self):
        return self.r.actual

    @property
    def posicion_ms(self):
        return int(float(self.r._posicion or 0) * 1000)

    @property
    def sonando(self):
        return self.r.estado == "sonando"

    @property
    def cargando(self):
        return self.r.estado == "cargando"

    def cargar(self, pista, inicio_ms=0, pausado=False):
        from .catalogo import nueva_pista
        vid = str(pista.get("video_id") or "")
        artista = str(pista.get("artista") or "")
        p = nueva_pista(vid, str(pista.get("titulo") or ""),
                        [{"nombre": a.strip(), "id": ""} for a in artista.split(",") if a.strip()],
                        duracion=_entero(pista.get("duracion")),
                        miniatura=str(pista.get("miniatura") or ""),
                        es_video=bool(pista.get("es_video")))
        r = self.r
        r.original = [p]
        r.secuencia = [p]
        r.pos = 0
        r.contexto = {"tipo": "juntos", "id": "", "titulo": self.titulo}
        inicio = max(0.0, inicio_ms / 1000.0)
        r._cargar(p, inicio=inicio if inicio > 1 else 0.0, pausado=pausado)
        r.cola_cambio.emit()

    def buscar(self, ms):
        self.r.buscar(max(0.0, ms / 1000.0))

    def pausar(self):
        self.r.pausar()

    def reanudar(self):
        self.r.reanudar()


# ======================================================================= sala

class Miembro:
    __slots__ = ("id", "nombre", "usuario", "entro")

    def __init__(self, id, nombre, usuario, entro):  # noqa: A002
        self.id, self.nombre, self.usuario, self.entro = id, nombre, usuario, entro

    @classmethod
    def desde(cls, clave, d):
        return cls(clave, str(d.get("nombre") or "Alguien"), str(d.get("usuario") or ""),
                   _entero(d.get("entro")))

    def orden(self):
        return (self.entro, self.id)

    def __repr__(self):
        return f"Miembro({self.nombre!r})"


class SalaJuntos:
    """Una sala de «Escuchar juntos». Se usa siempre desde un mismo hilo (el del
    dueno), que debe llamar a `tic()` cada 0,5 s y a `al_cambiar_reproductor()`
    cuando cambie la pista o la pausa.

    Avisos al dueno (todos en su hilo):
      al_abierta(error|None)        una vez: ya se esta dentro, o por que no
      al_cambio()                   cambio la lista, el anfitrion, la conexion…
      al_reaccion(emoji, nombre, de_mi)
    """

    def __init__(self, codigo, control, nombre, usuario="", anfitrion=False, despachar=None,
                 url_base=None, clave=None, al_abierta=None, al_cambio=None, al_reaccion=None,
                 al_chat=None):
        self.codigo = codigo
        self.control = control
        self.nombre = nombre or "Alguien"
        self.usuario = usuario or ""
        self.mi_id = nuevo_id()
        self._anfitrion_inicial = anfitrion
        self.al_abierta = al_abierta
        self.al_cambio = al_cambio
        self.al_reaccion = al_reaccion
        self.al_chat = al_chat
        self.chat = []
        self.canal = CanalRealtime(f"realtime:juntos-{codigo}", self.mi_id,
                                   al_mensaje=self._al_mensaje, al_presencia=self._al_presencia,
                                   al_estado_conexion=self._al_conexion,
                                   al_abierto=self._al_abierto, despachar=despachar,
                                   url_base=url_base, clave=clave)
        self.conectado = False
        self.abierta = False
        self.cerrada = False
        self.anfitrion_id = None
        self._rango_anfitrion = 0
        self._entro = 0
        self.diferencia_reloj = 0
        self._mejor_ida = None
        self._medidas = []
        self.ultimo_estado = None
        self._recibido_en = 0
        self.aviso = None
        self._seq = 0
        self._ultimo_salto = 0
        self._cargando_clave = ""
        self._cargando_desde = 0
        self._env_clave = ""
        self._env_sonando = False
        self._env_pos = 0
        self._env_en = 0
        self._env_forzado = 0
        self._proximo_ping = 0
        self._espera_anfitrion = 0

    # ------------------------------------------------------------ datos
    @property
    def enlace(self):
        return enlace_sala(self.codigo)

    @property
    def soy_anfitrion(self):
        return self.anfitrion_id == self.mi_id

    @property
    def miembros(self):
        return sorted((Miembro.desde(k, v) for k, v in self.canal.presentes.items()),
                      key=Miembro.orden)

    @property
    def anfitrion(self):
        for m in self.miembros:
            if m.id == self.anfitrion_id:
                return m
        return None

    @property
    def pista_sala(self):
        if self.soy_anfitrion:
            return self.control.pista
        p = (self.ultimo_estado or {}).get("pista")
        return p if isinstance(p, dict) else None

    def _avisar(self):
        if self.al_cambio:
            self.al_cambio()

    # ------------------------------------------------------------ abrir
    def abrir(self):
        self._entro = ahora_ms()
        if self._anfitrion_inicial:
            self.anfitrion_id = self.mi_id
            self._rango_anfitrion = self._entro
        self.canal.presentarme(self._mi_presencia())
        self.canal.abrir()

    def _mi_presencia(self):
        return {"nombre": self.nombre, "usuario": self.usuario, "entro": self._entro}

    def _al_abierto(self, error):
        if self.cerrada:
            return
        if error is not None:
            self.cerrada = True
            self.canal.cerrar()
            if self.al_abierta:
                self.al_abierta(error)
            return
        self.abierta = True
        self.conectado = True
        ahora = ahora_ms()
        self._proximo_ping = ahora + PING_MS
        if self.soy_anfitrion:
            self._mandar_estado()
        else:
            self.canal.difundir("hola", {"de": self.mi_id})
            self._medir_reloj()
            # si nadie responde (sala vacia), uno mismo pasa a ser el anfitrion
            self._espera_anfitrion = ahora + ESPERA_ANFITRION_MS
        if self.al_abierta:
            self.al_abierta(None)
        self._avisar()

    def _al_conexion(self, conectado):
        if self.cerrada:
            return
        self.conectado = conectado
        if conectado and self.abierta:
            if self.soy_anfitrion:
                self._mandar_estado()
            else:
                self.canal.difundir("hola", {"de": self.mi_id})
        self._avisar()

    # ------------------------------------------------------------ anfitrion
    def _al_presencia(self):
        if self.cerrada:
            return
        if (self.anfitrion_id is not None and self.anfitrion_id != self.mi_id
                and self.anfitrion_id not in self.canal.presentes):
            # el anfitrion se fue: le toca al que lleva mas tiempo
            self.anfitrion_id = None
            self._elegir_anfitrion()
        self._avisar()

    def _elegir_anfitrion(self):
        ms = self.miembros
        if not any(m.id == self.mi_id for m in ms):
            ms.append(Miembro(self.mi_id, self.nombre, self.usuario, self._entro))
        ms.sort(key=Miembro.orden)
        nuevo = ms[0]
        self.anfitrion_id = nuevo.id
        self._rango_anfitrion = nuevo.entro
        self._reiniciar_reloj()
        if nuevo.id == self.mi_id:
            self.aviso = "Ahora eres quien pone la música."
            self._mandar_estado()
        self._avisar()

    def _reiniciar_reloj(self):
        self._medidas.clear()
        self._mejor_ida = None
        self.diferencia_reloj = 0

    def ceder_anfitrion(self, id_):
        """El anfitrion le pasa el mando a otro miembro."""
        if not self.soy_anfitrion or id_ == self.mi_id or id_ not in self.canal.presentes:
            return
        self.canal.difundir("ceder", {"a": id_, "de": self.mi_id})
        self.anfitrion_id = id_
        self._rango_anfitrion = Miembro.desde(id_, self.canal.presentes[id_]).entro
        self._reiniciar_reloj()
        self.aviso = None
        self._avisar()

    def al_cambiar_reproductor(self):
        if not self.abierta or self.cerrada or not self.soy_anfitrion:
            return
        if (clave_pista(self.control.pista) != self._env_clave
                or self.control.sonando != self._env_sonando):
            self._mandar_estado()

    def _mandar_estado(self):
        if not self.soy_anfitrion or self.cerrada:
            return
        p = self.control.pista
        ahora = ahora_ms()
        self._env_clave = clave_pista(p)
        self._env_sonando = bool(self.control.sonando)
        self._env_pos = int(self.control.posicion_ms)
        self._env_en = ahora
        self._seq += 1
        self.canal.difundir("estado", {
            "de": self.mi_id, "rango": self._rango_anfitrion, "seq": self._seq,
            "pista": pista_para_compartir(p) if p else None,
            "pos": self._env_pos, "sonando": self._env_sonando, "t": ahora})

    def tic(self):
        """Cada 0,5 s desde el hilo del dueno."""
        if self.cerrada or not self.abierta:
            return
        ahora = ahora_ms()
        if self._espera_anfitrion and ahora >= self._espera_anfitrion:
            self._espera_anfitrion = 0
            if self.anfitrion_id is None:
                self._elegir_anfitrion()
        if ahora >= self._proximo_ping:
            self._proximo_ping = ahora + PING_MS
            self._medir_reloj()
        if self.soy_anfitrion:
            esperada = self._env_pos + (ahora - self._env_en) if self._env_sonando else self._env_pos
            salto = abs(self.control.posicion_ms - esperada) > DESFASE_MAXIMO_MS
            if ((salto and not self.control.cargando) or ahora - self._env_en > ESTADO_MS
                    or (self._env_forzado and ahora > self._env_forzado)):
                self._env_forzado = 0
                self._mandar_estado()
        else:
            self._seguir()

    # ------------------------------------------------------------ invitados
    def _al_mensaje(self, ev, d):
        if self.cerrada:
            return
        if ev == "estado":
            self._al_estado(d)
        elif ev == "hola":
            # alguien entro: que reciba ya lo que suena (y lo ultimo del chat)
            if self.soy_anfitrion:
                self._env_forzado = ahora_ms() + 150
                if self.chat:
                    self.canal.difundir("chat_historial", {"para": d.get("de"),
                                                           "mensajes": self.chat[-HISTORIAL_CHAT:]})
        elif ev == "chat":
            m = mensaje_chat_valido(d)
            if m and m["de"] != self.mi_id:
                self._sumar_chat(m)
        elif ev == "chat_historial":
            if d.get("para") == self.mi_id and not self.chat:
                for m in d.get("mensajes") or []:
                    m = mensaje_chat_valido(m)
                    if m:
                        self._sumar_chat(m)
        elif ev == "ping":
            if self.soy_anfitrion and d.get("a") == self.mi_id:
                self.canal.difundir("pong", {"para": d.get("de"), "t0": d.get("t0"),
                                             "th": ahora_ms()})
        elif ev == "pong":
            if d.get("para") == self.mi_id:
                self._al_pong(d)
        elif ev == "ceder":
            self.anfitrion_id = str(d.get("a") or "")
            m = self.canal.presentes.get(self.anfitrion_id)
            if m is not None:
                self._rango_anfitrion = Miembro.desde(self.anfitrion_id, m).entro
            self._reiniciar_reloj()
            if self.soy_anfitrion:
                self.aviso = "Te pasaron el mando: ahora pones la música."
                self._mandar_estado()
            self._avisar()
        elif ev == "reaccion":
            e = str(d.get("emoji") or "")
            if e and len(e) <= 8 and self.al_reaccion:
                self.al_reaccion(e, str(d.get("nombre") or ""), False)

    def _al_estado(self, d):
        de = str(d.get("de") or "")
        rango = _entero(d.get("rango"))
        if self.soy_anfitrion and de != self.mi_id:
            # dos anfitriones a la vez (p. ej. tras un corte): se queda el mas antiguo
            gana_el = (rango, de) < (self._rango_anfitrion, self.mi_id)
            if not gana_el:
                self._mandar_estado()
                return
        if self.anfitrion_id != de:
            self.anfitrion_id = de
            self._rango_anfitrion = rango
            self._reiniciar_reloj()
            self._medir_reloj()
        self._espera_anfitrion = 0
        self.ultimo_estado = d
        self._recibido_en = ahora_ms()
        self._seguir()
        self._avisar()

    def _medir_reloj(self):
        if self.soy_anfitrion or self.anfitrion_id is None or self.cerrada:
            return
        self.canal.difundir("ping", {"de": self.mi_id, "a": self.anfitrion_id, "t0": ahora_ms()})

    def _al_pong(self, d):
        t0 = d.get("t0")
        th = d.get("th")
        if not isinstance(t0, (int, float)) or not isinstance(th, (int, float)):
            return
        t0, th = int(t0), int(th)
        t1 = ahora_ms()
        ida = t1 - t0
        if ida < 0 or ida > 10000:
            return
        self._medidas.append((ida, th - (t0 + t1) // 2))
        if len(self._medidas) > 10:
            self._medidas.pop(0)
        # la medida con menos demora es la mas fiable
        mejor = min(self._medidas, key=lambda x: x[0])
        self._mejor_ida, self.diferencia_reloj = mejor

    def _seguir(self):
        """Lleva el reproductor local a lo que dice el anfitrion."""
        e = self.ultimo_estado
        if e is None or self.soy_anfitrion or self.cerrada:
            return
        c = self.control
        try:
            pista = e.get("pista") if isinstance(e.get("pista"), dict) else None
            sonando = e.get("sonando") is True
            t = _entero(e.get("t"), self._recibido_en)
            esperada = posicion_esperada(
                _entero(e.get("pos")), sonando, t,
                # sin medida del reloj todavia: se asume que el aviso tardo poco
                t - self._recibido_en if self._mejor_ida is None else self.diferencia_reloj)
            if pista is None:
                if c.sonando:
                    c.pausar()
                return
            clave = clave_pista(pista)
            if clave_pista(c.pista) != clave:
                if self._cargando_clave == clave and ahora_ms() - self._cargando_desde < 20000:
                    return
                if not str(pista.get("video_id") or ""):
                    texto = ("Quien pone la música está oyendo un archivo suyo "
                             "que no está en internet.")
                    if self.aviso != texto:
                        self.aviso = texto
                        self._avisar()
                    return
                self._cargando_clave = clave
                self._cargando_desde = ahora_ms()
                c.cargar(dict(pista), inicio_ms=esperada, pausado=not sonando)
                self._ultimo_salto = 0
                return
            self._cargando_clave = ""
            if c.cargando:
                return
            if sonando and not c.sonando:
                c.reanudar()
            elif not sonando and c.sonando:
                c.pausar()
            desfase = abs(c.posicion_ms - esperada)
            ahora = ahora_ms()
            if desfase > DESFASE_MAXIMO_MS and ahora - self._ultimo_salto > 2000:
                self._ultimo_salto = ahora
                # un poco por delante: el salto tarda en hacerse
                c.buscar(esperada + (150 if sonando else 0))
        except Exception:  # noqa: BLE001 - un fallo del reproductor no tumba la sala
            self._cargando_clave = ""

    # ------------------------------------------------------------ reacciones
    def reaccionar(self, emoji):
        if self.cerrada:
            return
        self.canal.difundir("reaccion", {"emoji": emoji, "nombre": self.nombre,
                                         "de": self.mi_id})
        if self.al_reaccion:
            self.al_reaccion(emoji, self.nombre, True)

    def enviar_chat(self, texto):
        texto = (texto or "").strip()[:LARGO_CHAT]
        if self.cerrada or not texto:
            return False
        m = {"de": self.mi_id, "nombre": self.nombre, "texto": texto, "t": ahora_ms()}
        self.canal.difundir("chat", m)
        self._sumar_chat(m)
        return True

    def _sumar_chat(self, m):
        self.chat.append(m)
        del self.chat[:-HISTORIAL_CHAT * 3]
        if self.al_chat:
            self.al_chat(m)

    def salir(self):
        if self.cerrada:
            return
        self.cerrada = True
        self.abierta = False
        self.conectado = False
        self.canal.cerrar()
        self._avisar()


# ============================================================= bucle simple

class BucleSimple:
    """Hilo dueno sin Qt (pruebas y guiones): ejecuta lo despachado y llama a
    `tic()` de las salas cada 0,5 s."""

    def __init__(self):
        self._cola = queue.Queue()
        self.salas = []
        self._fin = threading.Event()
        self._hilo = threading.Thread(target=self._correr, daemon=True)
        self._hilo.start()

    def despachar(self, f):
        self._cola.put(f)

    def llamar(self, f, espera=10):
        """Ejecuta `f` en el bucle y devuelve su resultado."""
        listo = threading.Event()
        caja = {}

        def envoltura():
            try:
                caja["r"] = f()
            except Exception as e:  # noqa: BLE001
                caja["e"] = e
            listo.set()

        self._cola.put(envoltura)
        if not listo.wait(espera):
            raise TimeoutError("el bucle no respondió")
        if "e" in caja:
            raise caja["e"]
        return caja.get("r")

    def _correr(self):
        siguiente = time.monotonic() + TIC_MS / 1000
        while not self._fin.is_set():
            try:
                f = self._cola.get(timeout=max(0.0, min(0.05, siguiente - time.monotonic())))
                f()
            except queue.Empty:
                pass
            except Exception:  # noqa: BLE001
                import traceback
                traceback.print_exc()
            if time.monotonic() >= siguiente:
                siguiente = time.monotonic() + TIC_MS / 1000
                for s in list(self.salas):
                    try:
                        s.tic()
                    except Exception:  # noqa: BLE001
                        import traceback
                        traceback.print_exc()

    def parar(self):
        self._fin.set()


# ================================================================== con Qt

class _Puente(QObject):
    """Lleva funciones del hilo del websocket al hilo de la interfaz."""
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


class SalaQt(QObject):
    """Una SalaJuntos atada al Reproductor y al hilo de la interfaz."""
    abierta = Signal(object)            # None o el texto del error
    cambio = Signal()
    reaccion = Signal(str, str, bool)   # emoji, nombre, de_mi
    chat = Signal(dict)                 # un mensaje del chat de la sala

    def __init__(self, reproductor, nombre, usuario="", codigo=None, padre=None, control=None):
        super().__init__(padre)
        self._puente = _Puente(self)
        self.r = reproductor
        self.control = control or ControlReproductor(reproductor)
        self.sala = SalaJuntos(codigo or nuevo_codigo(), self.control, nombre, usuario,
                               anfitrion=codigo is None, despachar=self._puente.llega.emit,
                               al_abierta=self._al_abierta, al_cambio=self.cambio.emit,
                               al_reaccion=self.reaccion.emit, al_chat=self.chat.emit)
        self._tic = QTimer(self)
        self._tic.setInterval(TIC_MS)
        self._tic.timeout.connect(self.sala.tic)
        if reproductor is not None:
            reproductor.pista_cambio.connect(self._al_reproductor)
            reproductor.estado_cambio.connect(self._al_reproductor)

    def abrir(self):
        self.sala.abrir()

    def _al_reproductor(self, *_):
        self.sala.al_cambiar_reproductor()

    def _al_abierta(self, error):
        if error is None:
            self._tic.start()
            self.abierta.emit(None)
        else:
            self._soltar_reproductor()
            self.abierta.emit(str(error))

    def _soltar_reproductor(self):
        self._tic.stop()
        if self.r is not None:
            for s in (self.r.pista_cambio, self.r.estado_cambio):
                try:
                    s.disconnect(self._al_reproductor)
                except (RuntimeError, TypeError):
                    pass

    def salir(self):
        self._soltar_reproductor()
        self.sala.salir()
