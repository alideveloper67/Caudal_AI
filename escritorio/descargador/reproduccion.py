# -*- coding: utf-8 -*-
"""Motor de reproduccion de Caudal (libmpv).

Dos motores de audio (para el fundido entre canciones) y los motores de video
que crean las pantallas que muestran imagen (la vista grande y el mini
reproductor). Todo pasa por `Reproductor`, que lleva la cola como Spotify:

  - la secuencia del contexto (album, lista, radio...) con su orden aleatorio,
  - "Siguiente en tu cola": lo que anadiste a mano, que suena antes,
  - reproduccion automatica: al acabarse, sigue con canciones parecidas.

Lo ya descargado suena desde el disco (sin internet); lo demas se pide a
YouTube en la mejor calidad, sin anuncios y en segundo plano.
"""

import os
import random
import time

from PySide6.QtCore import QObject, QTimer, Signal

from . import catalogo, mpv_carga
from .hilos import en_segundo_plano

FRECUENCIAS_EQ = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
PRESETS_EQ = {
    "Plano":          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Graves potentes": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
    "Agudos claros":  [0, 0, 0, 0, 0, 1, 2, 4, 5, 6],
    "Voces":          [-2, -1, 0, 2, 4, 4, 3, 1, 0, -1],
    "Pop":            [-1, 1, 3, 4, 2, 0, -1, -1, 1, 2],
    "Rock":           [4, 3, 2, 0, -1, -1, 1, 3, 4, 4],
    "Electrónica":    [5, 4, 1, 0, -2, 1, 0, 2, 4, 5],
    "Reguetón":       [6, 5, 3, 1, 0, -1, 0, 2, 3, 3],
    "Hip hop":        [5, 4, 2, 3, -1, -1, 1, 0, 2, 3],
    "Clásica":        [3, 2, 1, 0, 0, 0, -1, -1, 1, 2],
    "Jazz":           [3, 2, 1, 2, -1, -1, 0, 1, 2, 3],
    "Acústica":       [3, 2, 1, 1, 2, 2, 3, 3, 2, 1],
    "Noche (suave)":  [-3, -2, -1, 0, 1, 1, 0, -1, -2, -3],
    "Altavoz pequeño": [-6, -4, 0, 3, 4, 3, 2, 1, 0, -2],
}

CATEGORIAS_MUSICA = ["music_offtopic"]
CATEGORIAS_VIDEO = ["sponsor", "selfpromo", "interaction", "music_offtopic"]

NOMBRES_SALTO = {
    "music_offtopic": "parte sin música",
    "sponsor": "patrocinio",
    "selfpromo": "autopromoción",
    "interaction": "recordatorio de suscripción",
    "intro": "intro",
    "outro": "final",
}


def _edl(video_url, audio_url):
    """Une la pista de imagen y la de sonido en una sola fuente, como hace mpv
    con YouTube: es lo que permite 4K/8K (YouTube los sirve por separado)."""
    def esc(u):
        return f"%{len(u.encode('utf-8'))}%{u}"
    return ("edl://!new_stream;!no_clip;!no_chapters;" + esc(video_url)
            + ";!new_stream;!no_clip;!no_chapters;" + esc(audio_url))


class Motor(QObject):
    """Una instancia de mpv con sus avisos convertidos en senales de Qt."""

    posicion = Signal(object)
    duracion = Signal(object)
    pausa = Signal(bool)
    esperando = Signal(bool)
    termino = Signal(str, str)        # (eof|error, detalle)
    cargado = Signal()
    params_video = Signal(object)
    tecla = Signal(str)

    def __init__(self, ajustes, wid=None, nombre="audio", padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.nombre = nombre
        self.es_video = wid is not None
        mpv = mpv_carga.modulo()
        if mpv is None:
            raise RuntimeError(mpv_carga.error() or "Falta el motor de reproducción (libmpv).")
        opciones = dict(
            ytdl=False, idle="yes", keep_open="no",
            input_default_bindings=False, input_vo_keyboard=False, osc=False,
            cache="yes", demuxer_max_bytes="200MiB", demuxer_max_back_bytes="60MiB",
            demuxer_readahead_secs=40, audio_client_name="Caudal",
            volume_max=100, msg_level="all=no", network_timeout=25,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        )
        if self.es_video:
            opciones.update(
                wid=str(int(wid)), vo="gpu", force_window="yes",
                hwdec="auto-safe" if ajustes["aceleracion"] else "no",
                keepaspect="yes", background="color", background_color="#000000",
                audio_display="no", input_cursor="yes", cursor_autohide=1500,
                sub_auto="no", sub_font_size=44, sub_border_size=2.5,
                hr_seek="yes", video_sync="audio",
            )
        else:
            opciones.update(vo="null", video="no", audio_display="no")
        # mpv exige el formato numerico de C, y Qt lo cambia al del sistema
        # (coma decimal en espanol): sin esto mpv_create devuelve nulo
        import locale
        try:
            locale.setlocale(locale.LC_NUMERIC, "C")
        except locale.Error:
            pass
        # las teclas multimedia las atiende la ventana (una sola vez para todos
        # los motores); si cada mpv se anunciara a Windows habria varias sesiones
        try:
            opciones["media_controls"] = "no"
            self.mpv = mpv.MPV(**opciones)
        except Exception:
            opciones.pop("media_controls", None)
            self.mpv = mpv.MPV(**opciones)

        self._ignorar_fin = 0
        self._cargando = False
        self.fuente = None

        self.mpv.observe_property("time-pos", lambda _n, v: self.posicion.emit(v))
        self.mpv.observe_property("duration", lambda _n, v: self.duracion.emit(v))
        self.mpv.observe_property("pause", lambda _n, v: self.pausa.emit(bool(v)))
        self.mpv.observe_property("paused-for-cache",
                                  lambda _n, v: self.esperando.emit(bool(v)))
        if self.es_video:
            self.mpv.observe_property("video-params",
                                      lambda _n, v: self.params_video.emit(v or {}))

        @self.mpv.event_callback("end-file")
        def _fin(evento):
            datos = evento.as_dict() if hasattr(evento, "as_dict") else {}
            razon = datos.get("reason", b"")
            razon = razon.decode() if isinstance(razon, bytes) else str(razon)
            if razon == "eof":
                self.termino.emit("eof", "")
            elif razon == "error":
                detalle = datos.get("file_error", b"")
                detalle = detalle.decode() if isinstance(detalle, bytes) else str(detalle)
                self.termino.emit("error", detalle)

        @self.mpv.event_callback("file-loaded")
        def _cargado(_evento):
            self.cargado.emit()

        # teclas multimedia que llegan por los controles de Windows (SMTC) y
        # clics sobre el video
        for t in ("PLAY", "PAUSE", "PLAYPAUSE", "STOP", "NEXT", "PREV",
                  "MBTN_LEFT", "MBTN_LEFT_DBL", "WHEEL_UP", "WHEEL_DOWN",
                  "MBTN_RIGHT"):
            try:
                self.mpv.register_key_binding(t, self._hacer_tecla(t))
            except Exception:
                pass

    def _hacer_tecla(self, nombre):
        def manejar(estado, _nombre, _char=None, _escalado=None, _arg=None):
            # estado: "d-" pulsada, "u-" soltada, "p-" pulsacion completa
            if estado and estado[0] in ("d", "p"):
                self.tecla.emit(nombre)
        return manejar

    # ------------------------------------------------------------ control

    def cargar(self, fuente, inicio=0.0, pausado=False):
        """fuente: {"archivo"} o {"url", "audio_url", "cabeceras", "titulo"}."""
        self.fuente = fuente
        opciones = {}
        if inicio and inicio > 1:
            opciones["start"] = f"{inicio:.2f}"
        # el titulo va como propiedad y no como opcion de loadfile: las opciones
        # viajan separadas por comas y "KAROL G, Nicki Minaj" las rompia
        try:
            self.mpv["force-media-title"] = fuente.get("titulo") or ""
        except Exception:
            pass
        try:
            self.mpv.pause = bool(pausado)
        except Exception:
            pass
        if fuente.get("archivo"):
            destino = fuente["archivo"]
        else:
            cab = fuente.get("cabeceras") or {}
            campos = [f"{k}: {v}" for k, v in cab.items()
                      if k.lower() not in ("user-agent", "accept-encoding") and v]
            try:
                self.mpv["http-header-fields"] = campos
            except Exception:
                pass
            if cab.get("User-Agent"):
                try:
                    self.mpv["user-agent"] = cab["User-Agent"]
                except Exception:
                    pass
            if fuente.get("audio_url") and self.es_video:
                destino = _edl(fuente["url"], fuente["audio_url"])
            else:
                destino = fuente["url"]
        if opciones:
            self.mpv.loadfile(destino, "replace", **opciones)
        else:
            self.mpv.loadfile(destino, "replace")
        if fuente.get("subtitulo_url") and self.es_video:
            QTimer.singleShot(800, lambda: self.poner_subtitulo(fuente.get("subtitulo_url")))

    def poner_subtitulo(self, url):
        try:
            if url:
                self.mpv.command("sub-add", url, "select")
            else:
                self.mpv["sid"] = "no"
        except Exception:
            pass

    def detener(self):
        try:
            self.mpv.command("stop")
        except Exception:
            pass
        self.fuente = None

    def pausar(self, si=True):
        try:
            self.mpv.pause = bool(si)
        except Exception:
            pass

    def en_pausa(self):
        try:
            return bool(self.mpv.pause)
        except Exception:
            return True

    def buscar(self, segundos):
        try:
            self.mpv.command("seek", max(0.0, float(segundos)), "absolute+exact")
        except Exception:
            pass

    def posicion_actual(self):
        try:
            return float(self.mpv.time_pos or 0.0)
        except Exception:
            return 0.0

    def duracion_actual(self):
        try:
            return float(self.mpv.duration or 0.0)
        except Exception:
            return 0.0

    def fijar_volumen(self, v):
        try:
            self.mpv.volume = max(0.0, min(100.0, float(v)))
        except Exception:
            pass

    def fijar_velocidad(self, v):
        try:
            self.mpv.speed = float(v)
        except Exception:
            pass

    def fijar_filtros(self, af):
        try:
            self.mpv.af = af
        except Exception:
            try:
                self.mpv.af = ""
            except Exception:
                pass

    def fijar_aceleracion(self, si):
        if self.es_video:
            try:
                self.mpv["hwdec"] = "auto-safe" if si else "no"
            except Exception:
                pass

    def info_video(self):
        if not self.es_video:
            return {}
        try:
            vp = self.mpv.video_params or {}
            return {"ancho": vp.get("w"), "alto": vp.get("h"),
                    "hwdec": self.mpv.hwdec_current or "no",
                    "fps": self.mpv.container_fps or 0,
                    "caidos": self.mpv.frame_drop_count or 0}
        except Exception:
            return {}

    def cerrar(self):
        try:
            self.mpv.terminate()
        except Exception:
            pass


class Reproductor(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)            # cargando | sonando | pausa | parado
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)
    cola_cambio = Signal()
    modo_cambio = Signal(str)              # audio | video
    calidad_cambio = Signal(object)        # datos del stream que suena
    aviso = Signal(str)
    error = Signal(str)
    temporizador_cambio = Signal(object)   # segundos restantes o None
    video_listo = Signal(object)           # fuente lista para la vista de video

    def __init__(self, ajustes, coleccion, padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.coleccion = coleccion
        self.disponible = mpv_carga.modulo() is not None
        self.motivo_no_disponible = mpv_carga.error()

        self.audio = []                   # dos motores de audio
        self.activo = 0
        self.videos = {}                  # nombre -> Motor de video
        self.destino_video = "principal"

        self.modo = "audio"
        self.actual = None
        self.secuencia = []
        self.original = []
        self.pos = -1
        self.proximas = []
        self.contexto = None
        self.estado = "parado"
        self._duracion = 0.0
        self._posicion = 0.0
        self._gen = 0
        self._fuente = None
        self._segmentos = []
        self._escucha_registrada = False
        self._buscando_radio = False
        self._fundido = None
        self._ultimo_guardado = 0.0
        self._calidad_forzada = None

        self.volumen = int(ajustes["volumen"])
        self.velocidad = float(ajustes["velocidad"] or 1.0)
        self.aleatorio = bool(ajustes["aleatorio"])
        self.repetir = ajustes["repetir"] or "no"

        self._temporizador = QTimer(self)
        self._temporizador.setInterval(1000)
        self._temporizador.timeout.connect(self._tic_temporizador)
        self._apagar_en = None            # time.time() objetivo
        self._apagar_al_final = False

        self._pasos_fundido = QTimer(self)
        self._pasos_fundido.setInterval(50)
        self._pasos_fundido.timeout.connect(self._paso_fundido)

        if self.disponible:
            try:
                self._crear_audio()
            except Exception as e:  # noqa: BLE001
                self.disponible = False
                self.motivo_no_disponible = str(e)

    # ------------------------------------------------------------ motores

    def _crear_audio(self):
        for i in range(2):
            m = Motor(self.ajustes, None, f"audio{i}", self)
            self._conectar_motor(m)
            self.audio.append(m)
        self.aplicar_sonido()

    def _conectar_motor(self, m):
        m.posicion.connect(lambda v, m=m: self._al_posicion(m, v))
        m.duracion.connect(lambda v, m=m: self._al_duracion(m, v))
        m.pausa.connect(lambda p, m=m: self._al_pausa(m, p))
        m.esperando.connect(lambda e, m=m: self._al_esperar(m, e))
        m.termino.connect(lambda r, d, m=m: self._al_terminar(m, r, d))
        m.cargado.connect(lambda m=m: self._al_cargar(m))
        m.tecla.connect(self._al_tecla)

    def registrar_video(self, nombre, wid):
        """Las pantallas de video se presentan aqui con su ventana nativa."""
        if not self.disponible:
            return None
        if nombre in self.videos:
            return self.videos[nombre]
        m = Motor(self.ajustes, wid, f"video-{nombre}", self)
        self._conectar_motor(m)
        self.videos[nombre] = m
        self.aplicar_sonido()
        return m

    def motor_actual(self):
        if self.modo == "video" and self.destino_video in self.videos:
            return self.videos[self.destino_video]
        if self.audio:
            return self.audio[self.activo]
        return None

    def _todos(self):
        return list(self.audio) + list(self.videos.values())

    # ------------------------------------------------------------ sonido

    def cadena_filtros(self):
        partes = []
        if self.ajustes["ecualizador"]:
            bandas = list(self.ajustes["eq_bandas"] or [])[:10]
            for f, g in zip(FRECUENCIAS_EQ, bandas):
                if g:
                    partes.append(f"equalizer=f={f}:t=o:w=1:g={float(g):.1f}")
            if any(g > 0 for g in bandas):
                # margen para que al subir bandas no sature
                partes.insert(0, f"volume={-max(bandas) * 0.6:.1f}dB")
        if self.ajustes["normalizar"]:
            partes.append("loudnorm=I=-14:TP=-1.5:LRA=11")
        if not partes:
            return ""
        return "lavfi=[" + ",".join(partes) + "]"

    def aplicar_sonido(self):
        af = self.cadena_filtros()
        for m in self._todos():
            m.fijar_filtros(af)
            m.fijar_velocidad(self.velocidad)
        self._aplicar_volumen()

    def _aplicar_volumen(self):
        if self._fundido:
            return
        actual = self.motor_actual()
        for m in self._todos():
            m.fijar_volumen(self.volumen if m is actual else 0)

    def fijar_volumen(self, v):
        self.volumen = max(0, min(100, int(v)))
        self.ajustes["volumen"] = self.volumen
        self._aplicar_volumen()

    def fijar_velocidad(self, v):
        self.velocidad = max(0.25, min(3.0, float(v)))
        self.ajustes["velocidad"] = self.velocidad
        self.ajustes.guardar()
        for m in self._todos():
            m.fijar_velocidad(self.velocidad)
        self.aviso.emit(f"Velocidad {self.velocidad:g}×")

    # ------------------------------------------------------------ cola

    def reproducir_lista(self, pistas, inicio=0, contexto=None, aleatorio=None, modo=None):
        pistas = [p for p in pistas if p]
        if not pistas:
            return
        if aleatorio is not None:
            self.aleatorio = bool(aleatorio)
            self.ajustes["aleatorio"] = self.aleatorio
        inicio = max(0, min(inicio, len(pistas) - 1))
        self.original = list(pistas)
        self.contexto = contexto
        if self.aleatorio:
            primera = pistas[inicio] if (aleatorio is None or inicio) else random.choice(pistas)
            resto = [p for p in pistas if p is not primera]
            random.shuffle(resto)
            self.secuencia = [primera] + resto
            self.pos = 0
        else:
            self.secuencia = list(pistas)
            self.pos = inicio
        if modo:
            self._poner_modo(modo)
        self._cargar(self.secuencia[self.pos])
        self.cola_cambio.emit()

    def reproducir_pista(self, pista, contexto=None, modo=None, con_radio=True):
        """Una cancion suelta: suena y detras viene su radio, como en YouTube Music."""
        if not pista:
            return
        ctx = contexto or {"tipo": "radio", "id": pista.get("video_id") or pista.get("clave"),
                           "titulo": f"Radio de {pista.get('titulo', '')}"}
        self.original = [pista]
        self.secuencia = [pista]
        self.pos = 0
        self.contexto = ctx
        if modo:
            self._poner_modo(modo)
        self._cargar(pista)
        self.cola_cambio.emit()
        if con_radio and pista.get("video_id") and self.ajustes["autoplay"]:
            self._pedir_radio(pista, reemplazar_contexto=False)

    def iniciar_radio(self, pista):
        self.reproducir_pista(pista, {"tipo": "radio", "id": pista.get("video_id"),
                                      "titulo": f"Radio de {pista.get('titulo', '')}"})

    def reproducir_radio_id(self, playlist_id, titulo="Radio"):
        def listo(datos):
            pistas = datos.get("pistas") or []
            if pistas:
                self.reproducir_lista(pistas, 0, {"tipo": "radio", "id": playlist_id,
                                                  "titulo": titulo})
            else:
                self.error.emit("Esa radio no tiene canciones ahora mismo.")
        self.aviso.emit("Preparando la radio…")
        en_segundo_plano(catalogo.radio, None, playlist_id, ok=listo,
                         error=lambda e: self.error.emit(str(e)), dueno=self)

    def agregar_a_cola(self, pistas):
        if isinstance(pistas, dict):
            pistas = [pistas]
        pistas = [p for p in pistas if p]
        if not pistas:
            return
        if self.actual is None:
            self.reproducir_lista(pistas, 0, {"tipo": "cola", "id": "", "titulo": "Tu cola"})
            return
        self.proximas.extend(pistas)
        self.cola_cambio.emit()
        self.aviso.emit("Añadido a la cola" if len(pistas) == 1
                        else f"{len(pistas)} canciones añadidas a la cola")

    def reproducir_despues(self, pistas):
        if isinstance(pistas, dict):
            pistas = [pistas]
        pistas = [p for p in pistas if p]
        if not pistas:
            return
        if self.actual is None:
            self.reproducir_lista(pistas, 0)
            return
        self.proximas[0:0] = pistas
        self.cola_cambio.emit()
        self.aviso.emit("Sonará a continuación")

    def quitar_proxima(self, indice):
        if 0 <= indice < len(self.proximas):
            self.proximas.pop(indice)
            self.cola_cambio.emit()

    def quitar_de_secuencia(self, indice_absoluto):
        if self.pos < indice_absoluto < len(self.secuencia):
            p = self.secuencia.pop(indice_absoluto)
            if p in self.original:
                self.original.remove(p)
            self.cola_cambio.emit()

    def mover_proxima(self, origen, destino):
        if 0 <= origen < len(self.proximas) and 0 <= destino < len(self.proximas):
            p = self.proximas.pop(origen)
            self.proximas.insert(destino, p)
            self.cola_cambio.emit()

    def vaciar_proximas(self):
        self.proximas.clear()
        self.cola_cambio.emit()

    def saltar_a_proxima(self, indice):
        if 0 <= indice < len(self.proximas):
            p = self.proximas.pop(indice)
            del self.proximas[:indice]
            self.secuencia.insert(self.pos + 1, p)
            self.pos += 1
            self._cargar(p)
            self.cola_cambio.emit()

    def saltar_a(self, indice_absoluto):
        if 0 <= indice_absoluto < len(self.secuencia):
            self.pos = indice_absoluto
            self._cargar(self.secuencia[self.pos])
            self.cola_cambio.emit()

    def siguientes_de_contexto(self, n=80):
        return self.secuencia[self.pos + 1:self.pos + 1 + n]

    def alternar_aleatorio(self):
        self.aleatorio = not self.aleatorio
        self.ajustes["aleatorio"] = self.aleatorio
        self.ajustes.guardar()
        if self.secuencia and self.pos >= 0:
            hechas = self.secuencia[:self.pos + 1]
            if self.aleatorio:
                resto = self.secuencia[self.pos + 1:]
                random.shuffle(resto)
                self.secuencia = hechas + resto
            else:
                actual = self.secuencia[self.pos]
                pendientes = self.secuencia[self.pos + 1:]
                ids_original = {id(p) for p in self.original}
                ids_hechas = {id(p) for p in hechas}
                # lo que anadiste a mano (no esta en el contexto) se queda delante
                manuales = [p for p in pendientes if id(p) not in ids_original]
                ids_pendientes = {id(p) for p in pendientes}
                try:
                    i = next(i for i, p in enumerate(self.original) if p is actual)
                    resto = [p for p in self.original[i + 1:] if id(p) in ids_pendientes]
                    # y lo que en el orden original iba antes pero aun no sono
                    resto += [p for p in self.original[:i + 1]
                              if id(p) in ids_pendientes and id(p) not in ids_hechas]
                except StopIteration:
                    resto = [p for p in self.original if id(p) in ids_pendientes]
                self.secuencia = hechas + manuales + resto
        self.cola_cambio.emit()
        return self.aleatorio

    def ciclar_repetir(self):
        orden = ["no", "todo", "una"]
        self.repetir = orden[(orden.index(self.repetir) + 1) % 3] if self.repetir in orden else "no"
        self.ajustes["repetir"] = self.repetir
        self.ajustes.guardar()
        return self.repetir

    # ------------------------------------------------------------ transporte

    def alternar(self):
        m = self.motor_actual()
        if self.actual is None or m is None:
            return
        if self.estado == "parado":
            self._cargar(self.actual, inicio=self._posicion)
            return
        m.pausar(not m.en_pausa())

    def pausar(self):
        m = self.motor_actual()
        if m:
            m.pausar(True)

    def reanudar(self):
        m = self.motor_actual()
        if m and self.actual:
            if self.estado == "parado":
                self._cargar(self.actual, inicio=self._posicion)
            else:
                m.pausar(False)

    def detener(self):
        self._cortar_fundido()
        for m in self._todos():
            m.detener()
        self._fijar_estado("parado")

    def buscar(self, segundos):
        m = self.motor_actual()
        if m:
            m.buscar(segundos)
            self._posicion = float(segundos)
            self.posicion_cambio.emit(self._posicion)

    def avanzar(self, delta):
        self.buscar(max(0.0, self._posicion + delta))

    def siguiente(self, automatico=False):
        if self.actual is None:
            return
        if automatico and self.repetir == "una":
            self._cargar(self.actual)
            return
        objetivo = self._avanzar()
        if objetivo is None:
            if self.ajustes["autoplay"] and self.actual.get("video_id"):
                self._pedir_radio(self.actual, reemplazar_contexto=False, y_seguir=True)
            else:
                self.detener()
                self.buscar(0)
            return
        self._cargar(objetivo)
        self.cola_cambio.emit()

    def anterior(self):
        if self.actual is None:
            return
        if self._posicion > 4 or self.pos <= 0:
            self.buscar(0)
            return
        self.pos -= 1
        self._cargar(self.secuencia[self.pos])
        self.cola_cambio.emit()

    def _mirar_siguiente(self):
        """La siguiente pista sin moverse (para precargar y fundir)."""
        if self.repetir == "una" and self.actual:
            return self.actual
        if self.proximas:
            return self.proximas[0]
        if self.pos + 1 < len(self.secuencia):
            return self.secuencia[self.pos + 1]
        if self.repetir == "todo" and self.secuencia:
            return self.secuencia[0]
        return None

    def _avanzar(self):
        if self.proximas:
            p = self.proximas.pop(0)
            self.secuencia.insert(self.pos + 1, p)
            self.pos += 1
            return p
        if self.pos + 1 < len(self.secuencia):
            self.pos += 1
            return self.secuencia[self.pos]
        if self.repetir == "todo" and self.secuencia:
            if self.aleatorio:
                random.shuffle(self.secuencia)
            self.pos = 0
            return self.secuencia[0]
        return None

    def _pedir_radio(self, pista, reemplazar_contexto=False, y_seguir=False):
        if self._buscando_radio:
            return
        self._buscando_radio = True
        gen = self._gen

        def listo(datos):
            self._buscando_radio = False
            nuevas = []
            vistos = {p.get("video_id") for p in self.secuencia}
            for p in datos.get("pistas") or []:
                if p.get("video_id") and p["video_id"] not in vistos:
                    p["_auto"] = True
                    nuevas.append(p)
                    vistos.add(p["video_id"])
            if not nuevas:
                if y_seguir:
                    self.detener()
                return
            self.secuencia.extend(nuevas)
            self.original.extend(nuevas)
            self.cola_cambio.emit()
            if y_seguir and gen == self._gen:
                self.siguiente()

        def fallo(_e):
            self._buscando_radio = False
            if y_seguir:
                self.detener()

        en_segundo_plano(catalogo.radio, pista.get("video_id"), ok=listo, error=fallo,
                         dueno=self)

    # ------------------------------------------------------------ modo

    def _poner_modo(self, modo):
        if modo not in ("audio", "video") or modo == self.modo:
            return False
        self.modo = modo
        self.modo_cambio.emit(modo)
        return True

    def cambiar_modo(self, modo):
        """Pasar de cancion a video (o al reves) sin perder el punto."""
        if modo == self.modo:
            return
        posicion = self._posicion
        pausado = self.estado == "pausa"
        anterior = self.motor_actual()
        self._poner_modo(modo)
        if anterior:
            anterior.detener()
        if self.actual:
            self._cargar(self.actual, inicio=posicion, pausado=pausado, mismo=True)

    def mover_video(self, destino):
        """Llevar el video a otra pantalla (grande <-> mini) sin cortar."""
        if destino not in self.videos or destino == self.destino_video:
            self.destino_video = destino if destino in self.videos else self.destino_video
            return
        if self.modo != "video" or not self.actual:
            self.destino_video = destino
            return
        posicion = self._posicion
        pausado = self.estado == "pausa"
        viejo = self.videos.get(self.destino_video)
        self.destino_video = destino
        if viejo:
            viejo.detener()
        self._cargar(self.actual, inicio=posicion, pausado=pausado, mismo=True)

    def cambiar_calidad_video(self, alto, guardar=True):
        if guardar:
            self.ajustes["calidad_video"] = str(alto)
            self.ajustes.guardar()
            self._calidad_forzada = None
        else:
            self._calidad_forzada = str(alto)
        if self.modo == "video" and self.actual:
            self._cargar(self.actual, inicio=self._posicion,
                         pausado=self.estado == "pausa", mismo=True, forzar_stream=True)

    # ------------------------------------------------------------ carga

    def _cargar(self, pista, inicio=0.0, pausado=False, mismo=False, forzar_stream=False):
        if not self.disponible:
            self.error.emit("No se puede reproducir: " + (self.motivo_no_disponible
                                                          or "falta libmpv"))
            return
        self._cortar_fundido()
        self._gen += 1
        gen = self._gen
        cambio = pista is not self.actual or not mismo
        self.actual = pista
        if cambio:
            self._escucha_registrada = False
            self._segmentos = []
            self._duracion = float(pista.get("duracion") or 0)
            self._posicion = float(inicio or 0)
            self.pista_cambio.emit(pista)
            self.duracion_cambio.emit(self._duracion)
            self.posicion_cambio.emit(self._posicion)
        self._fijar_estado("cargando")
        self._apagar_si_toca_al_cambiar(cambio)

        querer_video = self.modo == "video"
        local = None
        if not forzar_stream:
            if pista.get("archivo") and os.path.exists(pista["archivo"]):
                if querer_video and pista.get("es_audio"):
                    local = None    # solo hay sonido en el disco: se pide el video
                else:
                    local = pista["archivo"]
            elif self.ajustes["preferir_descargado"] and pista.get("video_id"):
                copia = self.coleccion.copia_local(pista["video_id"], querer_video)
                if copia:
                    local = copia[0]

        if local:
            fuente = {"archivo": local, "titulo": self._titulo_medio(pista),
                      "local": True}
            self._arrancar(gen, fuente, inicio, pausado)
            return

        objetivo = pista.get("video_id") or pista.get("url") or ""
        if not objetivo:
            if pista.get("archivo"):
                self.error.emit("Ese archivo ya no está en el disco.")
            else:
                self.error.emit("No hay de dónde reproducir esta pista.")
            self._fijar_estado("parado")
            return

        modo = "video" if querer_video else "audio"
        if cambio:
            self._calidad_forzada = None
        calidad = (self._calidad_forzada or self.ajustes["calidad_video"]) if querer_video \
            else self.ajustes["calidad_audio"]
        codec = self.ajustes["codec_video"]

        def listo(datos):
            if gen != self._gen:
                return
            fuente = dict(datos)
            fuente["titulo"] = self._titulo_medio(pista)
            self._completar_pista(pista, datos.get("info") or {})
            self._arrancar(gen, fuente, inicio, pausado)

        def fallo(e):
            if gen != self._gen:
                return
            self._fijar_estado("parado")
            self.error.emit(str(e))
            # una pista rota no debe parar la musica
            if self.proximas or self.pos + 1 < len(self.secuencia):
                QTimer.singleShot(1500, lambda: gen == self._gen and self.siguiente())

        en_segundo_plano(catalogo.resolver, objetivo, modo, calidad, codec, self.ajustes,
                         ok=listo, error=fallo, dueno=self)

    def _titulo_medio(self, pista):
        t = pista.get("titulo") or ""
        if pista.get("artista"):
            t = f"{t} — {pista['artista']}"
        return t

    def _completar_pista(self, pista, info):
        """Lo que el stream sabe y el catalogo no traia (duracion, autor...)."""
        if not pista.get("duracion") and info.get("duracion"):
            pista["duracion"] = info["duracion"]
        if not pista.get("artista") and info.get("autor"):
            pista["artista"] = info["autor"]
            pista["artistas"] = [{"nombre": info["autor"], "id": ""}]
        if (not pista.get("titulo") or pista.get("titulo") == pista.get("url")) and info.get("titulo"):
            pista["titulo"] = info["titulo"]
        if not pista.get("video_id") and info.get("video_id"):
            pista["video_id"] = info["video_id"]

    def _arrancar(self, gen, fuente, inicio, pausado):
        if gen != self._gen:
            return
        self._fuente = fuente
        motor = self.motor_actual()
        if motor is None:
            if self.modo == "video":
                # la pantalla de video aun no existe: se avisa y ella lo arranca
                self.video_listo.emit({"fuente": fuente, "inicio": inicio, "pausado": pausado})
                return
            self.error.emit("No hay motor de reproducción.")
            return
        for m in self._todos():
            if m is not motor:
                m.detener()
        motor.fijar_volumen(self.volumen)
        motor.fijar_velocidad(self.velocidad)
        motor.cargar(fuente, inicio=inicio, pausado=pausado)
        info = dict((fuente.get("info") or {}))
        info["local"] = bool(fuente.get("local"))
        info["archivo"] = fuente.get("archivo", "")
        info["alturas"] = fuente.get("alturas") or []
        info["subtitulos"] = fuente.get("subtitulos") or {}
        self.calidad_cambio.emit(info)
        if self.modo == "video":
            self.video_listo.emit({"fuente": fuente, "inicio": inicio, "pausado": pausado})
        self._preparar_extras(gen)
        self._guardar_sesion_pronto()

    def arrancar_video_pendiente(self, datos):
        """La vista de video llama a esto cuando ya creo su motor."""
        if self.modo == "video" and datos:
            self._arrancar(self._gen, datos["fuente"], datos["inicio"], datos["pausado"])

    def _preparar_extras(self, gen):
        pista = self.actual
        if not pista:
            return
        vid = pista.get("video_id")
        if vid and self.ajustes["sponsorblock"]:
            categorias = list(CATEGORIAS_MUSICA)
            if self.modo == "video" and self.ajustes["sponsorblock_videos"]:
                categorias = CATEGORIAS_VIDEO

            def segmentos(lista):
                if gen == self._gen:
                    # no saltar si el tramo es casi toda la cancion
                    dur = self._duracion or 0
                    self._segmentos = [s for s in lista
                                       if not dur or (s[1] - s[0]) < dur * 0.6]
            en_segundo_plano(catalogo.segmentos_a_saltar, vid, categorias,
                             ok=segmentos, dueno=self)
        # precargar la siguiente para que empiece al instante
        QTimer.singleShot(4000, lambda: gen == self._gen and self._precargar())

    def _precargar(self):
        sig = self._mirar_siguiente()
        if not sig or sig is self.actual:
            return
        if sig.get("archivo") and os.path.exists(sig["archivo"]):
            return
        if self.ajustes["preferir_descargado"] and self.coleccion.copia_local(
                sig.get("video_id"), self.modo == "video"):
            return
        objetivo = sig.get("video_id") or sig.get("url")
        if not objetivo:
            return
        modo = self.modo
        calidad = self.ajustes["calidad_video"] if modo == "video" else self.ajustes["calidad_audio"]
        en_segundo_plano(catalogo.resolver, objetivo, modo, calidad, self.ajustes["codec_video"],
                         self.ajustes, ok=lambda _d: None, error=lambda _e: None, dueno=self)
        # si quedan pocas, pedir mas canciones parecidas por adelantado
        if (self.ajustes["autoplay"] and self.repetir == "no"
                and len(self.secuencia) - self.pos <= 3 and not self.proximas
                and self.actual and self.actual.get("video_id")):
            self._pedir_radio(self.actual)

    # ------------------------------------------------------------ avisos de mpv

    def _es_actual(self, m):
        return m is self.motor_actual()

    def _al_posicion(self, m, valor):
        if valor is None:
            return
        if self._fundido and m is self._fundido["entrante"]:
            pass
        elif not self._es_actual(m):
            return
        self._posicion = float(valor)
        self.posicion_cambio.emit(self._posicion)
        # saltar lo que no es musica
        for ini, fin, cat in self._segmentos:
            if ini <= self._posicion < fin - 0.5:
                m.buscar(fin)
                self.aviso.emit("Saltado: " + NOMBRES_SALTO.get(cat, "segmento"))
                self._segmentos = [s for s in self._segmentos if s[0] != ini]
                break
        # contar la escucha (30 s, o la mitad si es corta)
        if not self._escucha_registrada and self.actual:
            umbral = min(30.0, (self._duracion or 60) / 2)
            if self._posicion >= umbral:
                self._escucha_registrada = True
                self.coleccion.registrar_escucha(self.actual, self.contexto)
        # fundido con la siguiente
        if (self.modo == "audio" and not self._fundido
                and int(self.ajustes["crossfade"] or 0) > 0
                and self._duracion > 20 and self.repetir != "una"
                and self._duracion - self._posicion <= int(self.ajustes["crossfade"])
                and self.estado == "sonando"):
            self._empezar_fundido()
        if time.time() - self._ultimo_guardado > 15:
            self._guardar_sesion_pronto()

    def _al_duracion(self, m, valor):
        if not self._es_actual(m) or not valor:
            return
        self._duracion = float(valor)
        if self.actual and not self.actual.get("duracion"):
            self.actual["duracion"] = int(self._duracion)
        self.duracion_cambio.emit(self._duracion)

    def _al_cargar(self, m):
        if self._fundido and m is self._fundido.get("entrante"):
            self._fijar_estado("sonando")
            return
        if not self._es_actual(m):
            return
        self._fijar_estado("pausa" if m.en_pausa() else "sonando")

    def _al_pausa(self, m, pausado):
        if not self._es_actual(m) or self.estado in ("parado", "cargando"):
            return
        self._fijar_estado("pausa" if pausado else "sonando")

    def _al_esperar(self, m, esperando):
        if not self._es_actual(m):
            return
        if esperando:
            self._fijar_estado("cargando")
        else:
            self._fijar_estado("pausa" if m.en_pausa() else "sonando")

    def _al_terminar(self, m, razon, detalle):
        if self._fundido and m is self._fundido.get("saliente"):
            return
        if not self._es_actual(m):
            return
        if razon == "eof":
            if self._apagar_al_final:
                self._apagar_al_final = False
                self.temporizador_cambio.emit(None)
                self.detener()
                self.aviso.emit("Temporizador: música detenida")
                return
            self.siguiente(automatico=True)
        elif razon == "error":
            self.error.emit("No se pudo reproducir" + (f" ({detalle})" if detalle else "")
                            + ". Pasando a la siguiente.")
            self._fijar_estado("parado")
            if self.proximas or self.pos + 1 < len(self.secuencia):
                QTimer.singleShot(1200, self.siguiente)

    def _al_tecla(self, tecla):
        if tecla in ("PLAYPAUSE", "PLAY", "PAUSE", "MBTN_LEFT"):
            if tecla == "PLAY":
                self.reanudar()
            elif tecla == "PAUSE":
                self.pausar()
            else:
                self.alternar()
        elif tecla == "NEXT":
            self.siguiente()
        elif tecla == "PREV":
            self.anterior()
        elif tecla == "STOP":
            self.detener()
        elif tecla == "WHEEL_UP":
            self.fijar_volumen(self.volumen + 5)
        elif tecla == "WHEEL_DOWN":
            self.fijar_volumen(self.volumen - 5)
        elif tecla == "MBTN_LEFT_DBL":
            self.pidio_pantalla_completa()

    def pidio_pantalla_completa(self):
        """Lo redefine la ventana; aqui solo existe para que la tecla tenga destino."""

    def _fijar_estado(self, estado):
        if estado != self.estado:
            self.estado = estado
            self.estado_cambio.emit(estado)
            if estado in ("pausa", "parado"):
                self._guardar_sesion_pronto()

    # ------------------------------------------------------------ fundido

    def _empezar_fundido(self):
        sig = self._mirar_siguiente()
        if sig is None or len(self.audio) < 2:
            return
        # solo si la siguiente ya esta lista (en disco o precargada)
        local = sig.get("archivo") if sig.get("archivo") and os.path.exists(sig["archivo"]) else None
        if not local and self.ajustes["preferir_descargado"]:
            copia = self.coleccion.copia_local(sig.get("video_id"))
            local = copia[0] if copia else None
        fuente = None
        if local:
            fuente = {"archivo": local, "titulo": self._titulo_medio(sig), "local": True}
        else:
            objetivo = sig.get("video_id")
            clave = (f"https://www.youtube.com/watch?v={objetivo}", "audio",
                     str(self.ajustes["calidad_audio"]), self.ajustes["codec_video"])
            guardado = catalogo._cache_streams.get(clave) if objetivo else None
            if guardado:
                fuente = dict(guardado[1])
                fuente["titulo"] = self._titulo_medio(sig)
        if fuente is None:
            return

        saliente = self.audio[self.activo]
        entrante = self.audio[1 - self.activo]
        objetivo_pista = self._avanzar()
        if objetivo_pista is None:
            return
        self._gen += 1
        self.activo = 1 - self.activo
        self._fundido = {"saliente": saliente, "entrante": entrante,
                         "inicio": time.time(),
                         "dur": float(self.ajustes["crossfade"])}
        entrante.fijar_volumen(0)
        entrante.fijar_velocidad(self.velocidad)
        entrante.cargar(fuente)
        self._fuente = fuente
        self.actual = objetivo_pista
        self._escucha_registrada = False
        self._segmentos = []
        self._duracion = float(objetivo_pista.get("duracion") or 0)
        self._posicion = 0.0
        self.pista_cambio.emit(objetivo_pista)
        self.duracion_cambio.emit(self._duracion)
        info = dict(fuente.get("info") or {})
        info["local"] = bool(fuente.get("local"))
        self.calidad_cambio.emit(info)
        self.cola_cambio.emit()
        self._pasos_fundido.start()
        self._preparar_extras(self._gen)

    def _paso_fundido(self):
        f = self._fundido
        if not f:
            self._pasos_fundido.stop()
            return
        avance = min(1.0, (time.time() - f["inicio"]) / max(0.5, f["dur"]))
        # curva de igual potencia: no hay bajon a mitad del fundido
        import math
        f["entrante"].fijar_volumen(self.volumen * math.sin(avance * math.pi / 2))
        f["saliente"].fijar_volumen(self.volumen * math.cos(avance * math.pi / 2))
        if avance >= 1.0:
            f["saliente"].detener()
            self._fundido = None
            self._pasos_fundido.stop()
            self._aplicar_volumen()

    def _cortar_fundido(self):
        if self._fundido:
            self._fundido["saliente"].detener()
            self._fundido = None
            self._pasos_fundido.stop()
            self._aplicar_volumen()

    # ------------------------------------------------------------ temporizador

    def programar_apagado(self, minutos=None, al_terminar=False):
        self._apagar_al_final = bool(al_terminar)
        if minutos:
            self._apagar_en = time.time() + minutos * 60
            self._temporizador.start()
            self.temporizador_cambio.emit(minutos * 60)
            self.aviso.emit(f"La música se detendrá en {minutos} min")
        elif al_terminar:
            self._apagar_en = None
            self._temporizador.stop()
            self.temporizador_cambio.emit(-1)
            self.aviso.emit("La música se detendrá al terminar esta canción")
        else:
            self._apagar_en = None
            self._temporizador.stop()
            self.temporizador_cambio.emit(None)
            self.aviso.emit("Temporizador desactivado")

    def restante_apagado(self):
        if self._apagar_al_final:
            return -1
        if self._apagar_en:
            return max(0, int(self._apagar_en - time.time()))
        return None

    def _tic_temporizador(self):
        if not self._apagar_en:
            self._temporizador.stop()
            return
        quedan = self._apagar_en - time.time()
        if quedan <= 0:
            self._apagar_en = None
            self._temporizador.stop()
            self.temporizador_cambio.emit(None)
            self.pausar()
            self.aviso.emit("Temporizador: música en pausa. ¡Buenas noches!")
        else:
            self.temporizador_cambio.emit(int(quedan))

    def _apagar_si_toca_al_cambiar(self, cambio):
        pass

    # ------------------------------------------------------------ sesion

    def _guardar_sesion_pronto(self):
        self._ultimo_guardado = time.time()
        try:
            self.guardar_sesion()
        except Exception:
            pass

    def guardar_sesion(self):
        if not self.actual:
            return
        limpiar = lambda p: {k: v for k, v in p.items() if not k.startswith("_") or k == "_auto"}
        inicio = max(0, self.pos - 30)
        datos = {
            "secuencia": [limpiar(p) for p in self.secuencia[inicio:self.pos + 120]],
            "pos": self.pos - inicio,
            "proximas": [limpiar(p) for p in self.proximas[:100]],
            "contexto": self.contexto,
            "posicion": self._posicion,
            "modo": self.modo,
        }
        self.coleccion.guardar_estado("sesion", datos)

    def restaurar_sesion(self):
        datos = self.coleccion.estado("sesion")
        if not datos or not datos.get("secuencia"):
            return False
        self.secuencia = datos["secuencia"]
        self.original = list(self.secuencia)
        self.pos = max(0, min(int(datos.get("pos", 0)), len(self.secuencia) - 1))
        self.proximas = datos.get("proximas") or []
        self.contexto = datos.get("contexto")
        self.actual = self.secuencia[self.pos]
        self._posicion = float(datos.get("posicion") or 0)
        self._duracion = float(self.actual.get("duracion") or 0)
        self.estado = "parado"
        self.pista_cambio.emit(self.actual)
        self.duracion_cambio.emit(self._duracion)
        self.posicion_cambio.emit(self._posicion)
        self.estado_cambio.emit("parado")
        self.cola_cambio.emit()
        return True

    def cerrar(self):
        try:
            self.guardar_sesion()
        except Exception:
            pass
        for m in self._todos():
            m.cerrar()
