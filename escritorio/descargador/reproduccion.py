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

from . import catalogo, mezcla_dj, mpv_carga
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

# super volumen: sonoridad objetivo en LUFS (Spotify normal = -14)
NIVELES_SUPER_VOLUMEN = {1: -11, 2: -9, 3: -7, 4: -5}
# subida fija (dB) de cada nivel del super volumen
GANANCIA_SUPER_VOLUMEN = {1: 3, 2: 5, 3: 7, 4: 9}
NOMBRES_SUPER_VOLUMEN = {0: "Apagado", 1: "Fuerte", 2: "Muy fuerte", 3: "Fiesta", 4: "Máximo"}

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


# ---------------------------------------------------------------- transiciones DJ
# Al pasar de una cancion a otra se recorta el silencio del final de la que
# acaba y el del principio de la que entra. Primero manda SponsorBlock
# ("music_offtopic": intros habladas y finales sin musica); si no hay datos, se
# escucha el principio y el final con el silencedetect de ffmpeg.

UMBRAL_SILENCIO = "-45dB"
SILENCIO_MINIMO = 0.35       # segundos seguidos bajo el umbral para contar
TRAMO_INICIO = 15.0          # cuanto se escucha del principio
TRAMO_FINAL = 30.0           # y del final
RECORTE_MAX_INICIO = 15.0    # nunca se salta mas que esto al entrar
RECORTE_MINIMO = 0.4         # por debajo de esto no merece la pena recortar
FUNDIDO_DJ_CORTO = 1.2       # fundido minimo al saltar un silencio sin crossfade
APAGADO_SUAVE_SEG = 30.0     # el temporizador baja el volumen estos ultimos segundos


def analizar_silencedetect(texto, desplazamiento=0.0, tramo=None):
    """Lee la salida de `silencedetect` y devuelve [(inicio, fin o None), ...]
    en segundos de la cancion. `desplazamiento` es donde empezo a escucharse;
    si ffmpeg ya dio tiempos absolutos (mayores que el tramo) no se suma."""
    import re
    silencios = []
    abierto = None
    for linea in (texto or "").splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", linea)
        if m:
            abierto = max(0.0, float(m.group(1)))
            continue
        m = re.search(r"silence_end:\s*(-?[\d.]+)", linea)
        if m:
            fin = float(m.group(1))
            silencios.append((abierto if abierto is not None else 0.0, fin))
            abierto = None
    if abierto is not None:
        silencios.append((abierto, None))     # el silencio llega hasta el final
    if not desplazamiento:
        return silencios
    absolutos = tramo is not None and any(
        (f or i) > tramo + 2 for i, f in silencios)
    if absolutos:
        return silencios
    return [(i + desplazamiento, None if f is None else f + desplazamiento)
            for i, f in silencios]


def bordes_de_musica(duracion, segmentos=(), silencios_inicio=(), silencios_final=()):
    """Donde empieza y donde acaba de verdad la musica: (inicio, fin).

    Sin datos (o si el recorte dejaria la cancion en casi nada) devuelve
    (0, duracion), que es no recortar."""
    dur = float(duracion or 0)
    if dur <= 0:
        return 0.0, 0.0
    inicio, fin = 0.0, dur
    for ini, fi, cat in segmentos or ():
        if cat and cat != "music_offtopic":
            continue
        if ini <= 1.5 and fi < dur * 0.5:
            inicio = max(inicio, float(fi))
        if fi >= dur - 2.0 and ini > dur * 0.5:
            fin = min(fin, float(ini))
    for ini, fi in silencios_inicio or ():
        if ini <= 0.3 and fi is not None:
            inicio = max(inicio, float(fi))
            break
    for ini, fi in silencios_final or ():
        if ini > dur * 0.5 and (fi is None or fi >= dur - 0.5):
            fin = min(fin, float(ini))
            break
    inicio = min(inicio, RECORTE_MAX_INICIO)
    if inicio < RECORTE_MINIMO:
        inicio = 0.0
    if dur - fin < RECORTE_MINIMO:
        fin = dur
    if fin - inicio < max(20.0, dur * 0.4):
        return 0.0, dur
    return round(inicio, 2), round(fin, 2)


def _ffmpeg_exe():
    from .config import ruta_ffmpeg
    carpeta = ruta_ffmpeg()
    if not carpeta:
        return ""
    for nombre in ("ffmpeg.exe", "ffmpeg"):
        ruta = os.path.join(carpeta, nombre)
        if os.path.exists(ruta):
            return ruta
    return ""


def sondear_silencios(fuente, desde, tramo, exe=None):
    """Escucha un tramo de la cancion con ffmpeg (sin ventana y con la prioridad
    mas baja del sistema) y devuelve sus silencios."""
    import subprocess
    exe = exe or _ffmpeg_exe()
    if not exe or not fuente:
        return []
    origen = fuente.get("archivo") or fuente.get("audio_url") or fuente.get("url")
    if not origen:
        return []
    cmd = [exe, "-hide_banner", "-nostats", "-nostdin", "-loglevel", "info"]
    if not fuente.get("archivo"):
        cab = fuente.get("cabeceras") or {}
        if cab.get("User-Agent"):
            cmd += ["-user_agent", cab["User-Agent"]]
        otras = "".join(f"{k}: {v}\r\n" for k, v in cab.items()
                        if v and k.lower() not in ("user-agent", "accept-encoding"))
        if otras:
            cmd += ["-headers", otras]
        cmd += ["-rw_timeout", "15000000"]
    if desde > 0:
        cmd += ["-ss", f"{desde:.2f}"]
    cmd += ["-t", f"{tramo:.2f}", "-i", origen, "-vn", "-sn", "-dn",
            "-af", f"silencedetect=n={UMBRAL_SILENCIO}:d={SILENCIO_MINIMO}",
            "-f", "null", "-"]
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    banderas |= getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=40, creationflags=banderas)
    except (OSError, subprocess.SubprocessError):
        return []
    return analizar_silencedetect(r.stderr, desde, tramo)


def calcular_bordes(fuente, duracion, video_id="", segmentos=None):
    """Trabajo de fondo: (inicio, fin) de la musica de una pista."""
    dur = float(duracion or 0)
    if dur <= 20:
        return 0.0, dur
    if segmentos is None:
        segmentos = catalogo.segmentos_a_saltar(video_id, CATEGORIAS_MUSICA) if video_id else []
    inicio, fin = bordes_de_musica(dur, segmentos)
    exe = _ffmpeg_exe()
    s_ini, s_fin = [], []
    if exe:
        if inicio == 0:
            s_ini = sondear_silencios(fuente, 0.0, TRAMO_INICIO, exe)
        if fin >= dur:
            desde = max(0.0, dur - TRAMO_FINAL + 2)
            s_fin = sondear_silencios(fuente, desde, TRAMO_FINAL, exe)
    return bordes_de_musica(dur, segmentos, s_ini, s_fin)


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
            audio_pitch_correction="yes",
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

        self._cerrado = False
        self._ignorar_fin = 0
        self._cargando = False
        self.fuente = None

        self.mpv.observe_property("time-pos", lambda _n, v: self._emitir(self.posicion, v))
        self.mpv.observe_property("duration", lambda _n, v: self._emitir(self.duracion, v))
        self.mpv.observe_property("pause", lambda _n, v: self._emitir(self.pausa, bool(v)))
        self.mpv.observe_property("paused-for-cache",
                                  lambda _n, v: self._emitir(self.esperando, bool(v)))
        if self.es_video:
            self.mpv.observe_property("video-params",
                                      lambda _n, v: self._emitir(self.params_video, v or {}))

        @self.mpv.event_callback("end-file")
        def _fin(evento):
            datos = evento.as_dict() if hasattr(evento, "as_dict") else {}
            razon = datos.get("reason", b"")
            razon = razon.decode() if isinstance(razon, bytes) else str(razon)
            if razon == "eof":
                self._emitir(self.termino, "eof", "")
            elif razon == "error":
                detalle = datos.get("file_error", b"")
                detalle = detalle.decode() if isinstance(detalle, bytes) else str(detalle)
                self._emitir(self.termino, "error", detalle)

        @self.mpv.event_callback("file-loaded")
        def _cargado(_evento):
            self._emitir(self.cargado)

        # teclas multimedia que llegan por los controles de Windows (SMTC) y
        # clics sobre el video
        for t in ("PLAY", "PAUSE", "PLAYPAUSE", "STOP", "NEXT", "PREV",
                  "MBTN_LEFT", "MBTN_LEFT_DBL", "WHEEL_UP", "WHEEL_DOWN",
                  "MBTN_RIGHT"):
            try:
                self.mpv.register_key_binding(t, self._hacer_tecla(t))
            except Exception:
                pass

    def _emitir(self, senal, *args):
        """Los avisos de mpv llegan desde su hilo; si Caudal ya se esta
        cerrando y el objeto no existe, se descartan en silencio."""
        if self._cerrado:
            return
        try:
            senal.emit(*args)
        except RuntimeError:
            self._cerrado = True

    def _hacer_tecla(self, nombre):
        def manejar(estado, _nombre, _char=None, _escalado=None, _arg=None):
            # estado: "d-" pulsada, "u-" soltada, "p-" pulsacion completa
            if estado and estado[0] in ("d", "p"):
                self._emitir(self.tecla, nombre)
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
        """Apaga mpv sin colgar la salida: si tarda mas de 1,5 s se deja atras
        (el proceso termina igual)."""
        self._cerrado = True
        import threading

        def apagar():
            try:
                self.mpv.command("stop")
            except Exception:
                pass
            try:
                self.mpv.terminate()
            except Exception:
                pass
        hilo = threading.Thread(target=apagar, daemon=True)
        hilo.start()
        hilo.join(1.5)


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
        self._traspaso = None
        self._est_carga = 1.5           # segundos que suele tardar en abrir un video

        self.volumen = int(ajustes["volumen"])
        self.velocidad = float(ajustes["velocidad"] or 1.0)
        self.aleatorio = bool(ajustes["aleatorio"])
        self.repetir = ajustes["repetir"] or "no"

        self._temporizador = QTimer(self)
        self._temporizador.setInterval(1000)
        self._temporizador.timeout.connect(self._tic_temporizador)
        self._apagar_en = None            # time.time() objetivo
        self._apagar_al_final = False
        self._factor_suave = 1.0          # 1 = volumen normal; baja al final del temporizador

        self._bordes = {}                 # clave de pista -> (inicio, fin) de la musica
        self._salto_dj = -1               # gen en la que ya se salto el silencio final
        self.plan_mezcla = {}             # clave de pista -> paso del Mezclador hacia la siguiente
        self.plan_marcas = {}             # clave -> {"entrada","salida","eq"} del Mezclador
        self.plan_analisis = {}           # clave -> análisis (BPM, compás) que trae el Mezclador
        self._an_cache = {}               # análisis leídos de la caché (None = no hay)
        self._af = {}                     # filtros que lleva puestos cada motor
        self._prueba = None               # prueba de un paso del Mezclador en marcha

        self._pasos_fundido = QTimer(self)
        self._pasos_fundido.setInterval(50)
        self._pasos_fundido.timeout.connect(self._paso_fundido)

        if self.disponible:
            try:
                self._crear_audio()
            except Exception as e:  # noqa: BLE001
                self.disponible = False
                self.motivo_no_disponible = str(e)

        # descarga inteligente: tus me gusta y lo mas escuchado, sin molestar
        self.descarga_inteligente = None
        try:
            from .descarga_inteligente import DescargaInteligente
            self.descarga_inteligente = DescargaInteligente(ajustes, coleccion, self, padre=self)
            self.descarga_inteligente.iniciar()
        except Exception:  # noqa: BLE001 - nunca debe impedir que suene la musica
            self.descarga_inteligente = None

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
        if self.modo == "video":
            # sin pantalla todavia no hay motor: la vista lo crea y arranca el video
            return self.videos.get(self.destino_video)
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
        nivel = int(self.ajustes["super_volumen"] or 0)
        # Igualar el volumen entre canciones SIN tocar el de dentro de cada una.
        # Antes iba con loudnorm, que corrige cada pocos segundos: subia las
        # partes suaves y bajaba las fuertes, y se oia como si el volumen
        # bajara y volviera a subir. dynaudnorm con una ventana de ~30 segundos
        # pone una ganancia casi fija por cancion (medido: conserva los 15,6 dB
        # entre estrofa y estribillo; loudnorm los dejaba en 6,9).
        if self.ajustes["normalizar"] or nivel > 0:
            partes.append("dynaudnorm=f=500:g=61:p=0.9:m=4")
        if nivel > 0:
            # mas fuerte de forma fija y un limitador rapido para los picos
            partes.append(f"volume={GANANCIA_SUPER_VOLUMEN.get(nivel, 5)}dB")
            partes.append("alimiter=limit=0.95:attack=5:release=80:level=disabled")
        if not partes:
            return ""
        return "lavfi=[" + ",".join(partes) + "]"

    def aplicar_sonido(self):
        af = self.cadena_filtros()
        for m in self._todos():
            m.fijar_filtros(af)
            self._af[id(m)] = af
            m.fijar_velocidad(self.velocidad)
        self._aplicar_volumen()

    def _vol(self):
        """Volumen que de verdad llega a mpv (el temporizador lo va bajando)."""
        return self.volumen * self._factor_suave

    def _aplicar_volumen(self):
        if self._fundido:
            return
        actual = self.motor_actual()
        for m in self._todos():
            m.fijar_volumen(self._vol() if m is actual else 0)

    def _poner_factor_suave(self, factor):
        factor = max(0.0, min(1.0, float(factor)))
        if abs(factor - self._factor_suave) < 0.004 and factor not in (0.0, 1.0):
            return
        if factor == self._factor_suave:
            return
        self._factor_suave = factor
        self._aplicar_volumen()

    def fijar_volumen(self, v):
        self.volumen = max(0, min(100, int(v)))
        self.ajustes["volumen"] = self.volumen
        self._aplicar_volumen()

    def fijar_velocidad(self, v, guardar=True):
        self.velocidad = max(0.25, min(3.0, float(v)))
        for m in self._todos():
            m.fijar_velocidad(self.velocidad)
        if guardar:
            self.ajustes["velocidad"] = self.velocidad
            self.ajustes.guardar()
            self.aviso.emit(f"Velocidad {self.velocidad:g}×")

    # ------------------------------------------------------------ cola

    def reproducir_lista(self, pistas, inicio=0, contexto=None, aleatorio=None, modo=None,
                         plan=None, marcas=None, analisis=None):
        pistas = [p for p in pistas if p]
        if not pistas:
            return
        self.plan_mezcla = dict(plan or {})
        self.plan_marcas = dict(marcas or {})
        self.plan_analisis = dict(analisis or {})
        self._prueba = None
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

    def reproducir_set(self, pistas, pasos, nombre="Mezcla", marcas=None, analisis=None):
        """Suena un set del Mezclador: en el orden dado y con los pasos a medida.
        `marcas` ({clave: entrada/salida/eq}) y `analisis` ({clave: BPM y compás})
        son opcionales: sin ellos suena como los sets de antes."""
        pistas = [p for p in pistas if p]
        if not pistas:
            return
        plan = mezcla_dj.plan_de_set(pistas, mezcla_dj.pasos_para(pistas, pasos))
        self.reproducir_lista(pistas, 0, {"tipo": "mezcla", "id": nombre, "titulo": nombre,
                                          "miniatura": pistas[0].get("miniatura") or ""},
                              aleatorio=False, modo="audio", plan=plan, marcas=marcas,
                              analisis=analisis)

    def probar_paso(self, a, b, paso, marcas=None, analisis=None):
        """Suena solo la unión de dos canciones: arranca poco antes de que empiece a
        entrar la segunda y se calla unos segundos después de que haya entrado."""
        if not a or not b:
            return
        paso = mezcla_dj.normalizar_paso(paso, a.get("duracion") or 0)
        clave = str(a.get("clave") or a.get("video_id") or "")
        self.plan_mezcla = {clave: paso} if clave else {}
        self.plan_marcas = dict(marcas or {})
        self.plan_analisis = dict(analisis or {})
        self._prueba = {"b": b, "paso": paso}
        self.aleatorio = False
        self.original = [a, b]
        self.secuencia = [a, b]
        self.pos = 0
        self.contexto = {"tipo": "mezcla", "id": "prueba", "titulo": "Prueba de mezcla"}
        self._poner_modo("audio")
        dur = float(a.get("duracion") or 0)
        marca = (self.plan_marcas.get(clave) or {}).get("salida")
        fin = float(marca) if marca else dur
        arranque = max(0.0, fin - paso["entra"] - 10.0)
        self._cargar(a, inicio=arranque)
        self.cola_cambio.emit()

    def probar_tramo(self, pista, inicio, segundos=12.0):
        """Suena `segundos` de una canción desde `inicio` (para probar un punto de
        entrada o de salida) y se calla."""
        if not pista:
            return
        self.plan_mezcla, self.plan_marcas, self.plan_analisis = {}, {}, {}
        prueba = {"tramo": True}
        self._prueba = prueba
        self.aleatorio = False
        self.original = [pista]
        self.secuencia = [pista]
        self.pos = 0
        self.contexto = {"tipo": "mezcla", "id": "prueba", "titulo": "Prueba de mezcla"}
        self._poner_modo("audio")
        self._cargar(pista, inicio=max(0.0, float(inicio or 0)))
        self.cola_cambio.emit()
        QTimer.singleShot(int(max(2.0, segundos) * 1000), lambda: self._fin_de_prueba(prueba))

    def _fin_de_prueba(self, prueba):
        if self._prueba is not prueba:
            return
        self._prueba = None
        self.plan_mezcla, self.plan_marcas, self.plan_analisis = {}, {}, {}
        if self.estado == "sonando":
            self.pausar()
            self.aviso.emit("Fin de la prueba de la mezcla")

    def reproducir_pista(self, pista, contexto=None, modo=None, con_radio=True):
        """Una cancion suelta: suena y detras viene su radio, como en YouTube Music."""
        if not pista:
            return
        self.plan_mezcla = {}
        self.plan_marcas = {}
        self.plan_analisis = {}
        self._prueba = None
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
        if self._traspaso:
            self._terminar_traspaso(True)
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
        self._traspaso = None
        self._cortar_fundido()
        for m in self._todos():
            m.detener()
        self._fijar_estado("parado")

    def buscar(self, segundos):
        if self._traspaso:
            self._terminar_traspaso(True)
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
        # saltar antes de que cuente como escuchada: el recomendador lo aprende
        if (not automatico and not self._escucha_registrada and self._posicion < 30
                and self.actual.get("video_id") and not self.actual.get("archivo")):
            try:
                from . import recomendador
                recomendador.anotar_salto(self.coleccion, self.actual)
                self._gusto = None
            except Exception:  # noqa: BLE001
                pass
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
        # al pasar sola, la siguiente entra donde empieza su musica
        self._cargar(objetivo, inicio=self._entrada_de(objetivo, False) if automatico else 0.0)
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
            candidatas = datos.get("pistas") or []
            # sin lo que sueles saltar ni lo que ya sonó estos días
            try:
                from . import recomendador
                self._gusto = recomendador.gusto(self.coleccion)     # al día: lo saltado hoy cuenta
                candidatas = recomendador.limpiar_radio(candidatas, self._gusto)
            except Exception:  # noqa: BLE001
                pass
            for p in candidatas:
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

        def pedir(video_id):
            # las «siguientes» de YouTube Music + artista, parecidos, historial y gustos
            from . import recomendador
            return recomendador.radio_inteligente(self.coleccion, pista)

        en_segundo_plano(pedir, pista.get("video_id"), ok=listo, error=fallo, dueno=self)

    # ------------------------------------------------------------ modo

    def _poner_modo(self, modo):
        if modo not in ("audio", "video") or modo == self.modo:
            return False
        self.modo = modo
        self.modo_cambio.emit(modo)
        return True

    def cambiar_modo(self, modo):
        """Pasar de cancion a video (o al reves) sin perder el punto.

        Al pasar a video la cancion sigue sonando hasta que el video tiene
        imagen en ese mismo punto: no hay silencio mientras carga."""
        if modo == self.modo:
            return
        posicion = self._posicion
        pausado = self.estado == "pausa"
        anterior = self.motor_actual()
        sonando = self.estado == "sonando" and anterior is not None and not anterior.es_video
        self._terminar_traspaso(False)
        self._poner_modo(modo)
        if modo == "video" and sonando and self.actual:
            self._traspaso = {"saliente": anterior, "objetivo": None}
            self._vigilar_traspaso()
        elif anterior:
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
        self._terminar_traspaso(True)
        self.destino_video = destino
        if viejo and self.estado == "sonando":
            # la pantalla vieja sigue hasta que la nueva la alcanza: sin corte
            self._traspaso = {"saliente": viejo, "objetivo": None}
            self._vigilar_traspaso()
        elif viejo:
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
            self._reintentos = 0
            self._escucha_registrada = False
            self._segmentos = []
            self._duracion = float(pista.get("duracion") or 0)
            self._posicion = float(inicio or 0)
            self.pista_cambio.emit(pista)
            self.duracion_cambio.emit(self._duracion)
            self.posicion_cambio.emit(self._posicion)
        if not self._traspaso:
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
        calidad = self.calidad_video_efectiva() if querer_video else self.ajustes["calidad_audio"]
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
            if self._traspaso:
                # el video no se pudo abrir: la cancion sigue como estaba
                self._terminar_traspaso(False, volver_a_audio=True)
                self.error.emit(f"No se pudo abrir el video: {e}")
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
        saliente = (self._traspaso or {}).get("saliente")
        for m in self._todos():
            if m is not motor and m is not saliente:
                m.detener()
        motor.fijar_velocidad(self.velocidad)
        if self.modo == "audio":
            self._poner_af(motor, self.cadena_para(self.actual))
        if saliente is not None:
            # el nuevo carga EN PAUSA un poco por delante; cuando lo que suena
            # llega a ese punto, arranca el nuevo y se apaga el viejo a la vez
            objetivo = saliente.posicion_actual() + self._est_carga + 0.6
            self._traspaso.update(objetivo=objetivo, listo=False, desde=time.time(),
                                  fuente=fuente)
            motor.fijar_volumen(0)
            motor.cargar(fuente, inicio=objetivo, pausado=True)
        else:
            motor.fijar_volumen(self._vol())
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
        # transicion DJ: donde acaba de verdad la musica de esta (audio solamente)
        if self.modo == "audio" and self.ajustes["transicion_dj"]:
            QTimer.singleShot(2500, lambda: gen == self._gen and self._analizar_bordes(
                pista, self._fuente))
        # precargar la siguiente para que empiece al instante
        QTimer.singleShot(4000, lambda: gen == self._gen and self._precargar())
        # y dejar listo el video de esta, por si pulsas "Ver el video"
        if self.modo == "audio" and vid and not pista.get("archivo"):
            QTimer.singleShot(2500, lambda: gen == self._gen and self._preparar_video(vid))

    def _preparar_video(self, vid):
        en_segundo_plano(catalogo.resolver, vid, "video", self.calidad_video_efectiva(),
                         self.ajustes["codec_video"], self.ajustes,
                         ok=lambda _d: None, error=lambda _e: None, dueno=self)

    def calidad_video_efectiva(self):
        """'Maxima' es la mayor que tu pantalla puede mostrar: en un monitor
        1080p, un 4K solo gasta red y procesador sin verse mejor."""
        calidad = self._calidad_forzada or self.ajustes["calidad_video"]
        if calidad != "maxima":
            return calidad
        try:
            from PySide6.QtGui import QGuiApplication
            alto = max(int(p.size().height() * p.devicePixelRatio())
                       for p in QGuiApplication.screens())
        except Exception:
            return calidad
        for escalon in (4320, 2160, 1440, 1080, 720):
            if alto >= escalon * 0.9:
                return str(escalon)
        return "720"

    def _vigilar_traspaso(self):
        """Seguro: un traspaso que se alarga mas de 5 s se completa igual."""
        t = self._traspaso
        if not t:
            return
        if time.time() - t.setdefault("inicio", time.time()) > 5.0:
            entrante = self.motor_actual()
            if entrante is not None and t.get("objetivo") is not None:
                entrante.buscar(max(t["saliente"].posicion_actual(), t["objetivo"]))
            self._terminar_traspaso(True)
            return
        QTimer.singleShot(250, self._vigilar_traspaso)

    def _terminar_traspaso(self, completar=True, volver_a_audio=False):
        t = self._traspaso
        if not t:
            return
        self._traspaso = None
        saliente = t["saliente"]
        if completar:
            entrante = self.motor_actual()
            if entrante is not None:
                entrante.fijar_volumen(self._vol())
                entrante.pausar(False)
            saliente.detener()
            if t.get("desde") and t.get("listo_en"):
                # se aprende cuanto tarda en cargar este equipo / esta conexion
                tardo = t["listo_en"] - t["desde"]
                self._est_carga = max(0.4, min(6.0, self._est_carga * 0.6 + tardo * 0.4))
            self._fijar_estado("sonando")
        elif volver_a_audio:
            self._poner_modo("audio")
            self._fijar_estado("sonando")

    def _precargar(self):
        sig = self._mirar_siguiente()
        if not sig or sig is self.actual:
            return
        dj = self.modo == "audio" and self.ajustes["transicion_dj"]
        if sig.get("archivo") and os.path.exists(sig["archivo"]):
            if dj:
                self._analizar_bordes(sig, {"archivo": sig["archivo"]})
            return
        copia = self.coleccion.copia_local(sig.get("video_id"), self.modo == "video") \
            if self.ajustes["preferir_descargado"] else None
        if copia:
            if dj:
                self._analizar_bordes(sig, {"archivo": copia[0]})
            return
        objetivo = sig.get("video_id") or sig.get("url")
        if not objetivo:
            return
        modo = self.modo
        calidad = self.ajustes["calidad_video"] if modo == "video" else self.ajustes["calidad_audio"]

        def resuelta(datos):
            if dj:
                self._analizar_bordes(sig, datos)
        en_segundo_plano(catalogo.resolver, objetivo, modo, calidad, self.ajustes["codec_video"],
                         self.ajustes, ok=resuelta, error=lambda _e: None, dueno=self)
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
        t = self._traspaso
        if t:
            if m is t["saliente"]:
                # mientras el nuevo carga, la barra sigue a lo que suena
                self._posicion = float(valor)
                self.posicion_cambio.emit(self._posicion)
                objetivo = t.get("objetivo")
                if objetivo is None:
                    return
                if t.get("listo") and float(valor) >= objetivo - 0.04:
                    self._terminar_traspaso(True)
                elif not t.get("listo") and float(valor) > objetivo + 0.3:
                    # tardo mas de lo previsto: se recoloca un poco mas adelante
                    entrante = self.motor_actual()
                    nuevo = float(valor) + self._est_carga + 1.0
                    t["objetivo"] = nuevo
                    if entrante is not None:
                        entrante.buscar(nuevo)
                return
            if m is self.motor_actual():
                return
        if self._fundido and m is self._fundido["entrante"]:
            pass
        elif not self._es_actual(m):
            return
        self._posicion = float(valor)
        self.posicion_cambio.emit(self._posicion)
        # si ya suena bien un rato tras un reintento, el contador vuelve a cero
        if getattr(self, "_reintentos", 0) and self._posicion > getattr(self, "_reintento_desde", 0) + 20:
            self._reintentos = 0
        # saltar lo que no es musica
        dj = self.ajustes["transicion_dj"] and self.modo == "audio"
        for ini, fin, cat in self._segmentos:
            if dj and cat == "music_offtopic" and fin >= (self._duracion or 0) - 2.0 \
                    and ini > (self._duracion or 0) * 0.5:
                continue        # el final sin musica lo resuelve la transicion DJ
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
                try:
                    from . import recomendador
                    recomendador.perdonar(self.coleccion, self.actual)
                except Exception:  # noqa: BLE001
                    pass
        # temporizador "al terminar esta cancion": baja poco a poco al final
        if self._apagar_al_final and self.ajustes["apagado_suave"] and self._duracion > 0:
            quedan = (self._fin_musica() or self._duracion) - self._posicion
            self._poner_factor_suave(min(1.0, quedan / APAGADO_SUAVE_SEG))
        # fundido con la siguiente (con la transicion DJ, antes del silencio final)
        if dj:
            self._vigilar_final_dj(m)
        elif (self.modo == "audio" and not self._fundido and not self._apagar_al_final
                and self._duracion > 20 and self.repetir != "una"
                and self.estado == "sonando"
                and self._debe_fundir_ya()):
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
        t = self._traspaso
        if t:
            if m is self.motor_actual():
                t["listo"] = True
                t["listo_en"] = time.time()
                if t["saliente"].posicion_actual() >= (t.get("objetivo") or 0) - 0.04:
                    # el viejo ya paso el punto: se recoloca un poco por delante
                    nuevo = t["saliente"].posicion_actual() + 0.8
                    t["objetivo"] = nuevo
                    m.buscar(nuevo)
            return
        if self._fundido and m is self._fundido.get("entrante"):
            self._fijar_estado("sonando")
            return
        if not self._es_actual(m):
            return
        self._fijar_estado("pausa" if m.en_pausa() else "sonando")

    def _al_pausa(self, m, pausado):
        if self._traspaso or not self._es_actual(m) or self.estado in ("parado", "cargando"):
            return
        self._fijar_estado("pausa" if pausado else "sonando")

    def _al_esperar(self, m, esperando):
        if self._traspaso or not self._es_actual(m):
            return
        if esperando:
            self._fijar_estado("cargando")
        else:
            self._fijar_estado("pausa" if m.en_pausa() else "sonando")

    def _al_terminar(self, m, razon, detalle):
        t = self._traspaso
        if t:
            if m is t["saliente"] and razon == "eof":
                self._terminar_traspaso(True)
                return
            if m is self.motor_actual() and razon == "error":
                self._terminar_traspaso(False, volver_a_audio=True)
                self.error.emit("No se pudo abrir el video; sigue sonando la canción.")
                return
            if m is t["saliente"]:
                return
        if self._fundido and m is self._fundido.get("saliente"):
            return
        if not self._es_actual(m):
            return
        if razon == "eof":
            if self._apagar_al_final:
                self._apagar_al_final = False
                self.temporizador_cambio.emit(None)
                self.detener()
                self._poner_factor_suave(1.0)
                self.aviso.emit("Temporizador: música detenida")
                return
            self.siguiente(automatico=True)
        elif razon == "error":
            # el enlace de YouTube caduca o la red parpadea: se pide otro y se sigue
            # donde iba, hasta 3 veces, antes de rendirse con la canción
            pista = self.actual
            if (pista and not (self._fuente or {}).get("local")
                    and getattr(self, "_reintentos", 0) < 3
                    and (pista.get("video_id") or pista.get("url"))):
                self._reintentos = getattr(self, "_reintentos", 0) + 1
                self._reintento_desde = self._posicion
                try:
                    catalogo.olvidar(pista.get("video_id") or pista.get("url"))
                except Exception:  # noqa: BLE001
                    pass
                gen = self._gen
                pausado = self.estado == "pausa"
                inicio = self._posicion
                self._fijar_estado("cargando")
                QTimer.singleShot(
                    700 * self._reintentos,
                    lambda: gen == self._gen and self._cargar(
                        pista, inicio=inicio, pausado=pausado, mismo=True, forzar_stream=True))
                return
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

    # ------------------------------------------------------------ transicion DJ

    @staticmethod
    def _clave_bordes(pista):
        if not pista:
            return ""
        return pista.get("video_id") or pista.get("archivo") or pista.get("url") or ""

    def _analizar_bordes(self, pista, fuente):
        """Calcula en segundo plano donde empieza y acaba la musica de la pista."""
        clave = self._clave_bordes(pista)
        if not clave or not fuente or clave in self._bordes:
            return
        duracion = float(pista.get("duracion") or (fuente.get("info") or {}).get("duracion") or 0)
        if pista is self.actual and self._duracion:
            duracion = self._duracion
        if duracion <= 20:
            return
        self._bordes[clave] = None              # en camino: no se pide dos veces
        if len(self._bordes) > 400:
            for k in list(self._bordes)[:200]:
                self._bordes.pop(k, None)

        def listo(res):
            self._bordes[clave] = tuple(res) if res else (0.0, duracion)

        def fallo(_e):
            self._bordes.pop(clave, None)
        en_segundo_plano(calcular_bordes, dict(fuente), duracion, pista.get("video_id") or "",
                         ok=listo, error=fallo, dueno=self)

    def _inicio_dj(self, pista):
        """Segundo en el que entra la musica (0 si no hay nada que recortar)."""
        if not self.ajustes["transicion_dj"] or self.modo != "audio":
            return 0.0
        b = self._bordes.get(self._clave_bordes(pista))
        return float(b[0]) if b else 0.0

    def _fin_musica(self):
        """Segundo en el que acaba de verdad la musica de lo que suena (o el punto de
        salida que se eligió en el Mezclador, si es antes)."""
        fin = self._fin_musica_base()
        salida = self._marcas_de(self.actual).get("salida")
        if salida and 5.0 < float(salida) < fin:
            return float(salida)
        return fin

    def _fin_musica_base(self):
        dur = self._duracion or 0.0
        if not self.ajustes["transicion_dj"] or dur <= 20:
            return dur
        fin = dur
        b = self._bordes.get(self._clave_bordes(self.actual))
        if b and b[1] and b[1] < dur:
            fin = float(b[1])
        for ini, fi, cat in self._segmentos:
            if cat == "music_offtopic" and fi >= dur - 2.0 and ini > dur * 0.5:
                fin = min(fin, float(ini))
        return fin

    def _vigilar_final_dj(self, m):
        """Fundido (o salto) a la siguiente antes de que llegue el silencio."""
        if self.modo != "audio" or self.estado != "sonando" or self._fundido:
            return
        if self.repetir == "una" or self._duracion <= 20 or self._salto_dj == self._gen:
            return
        fin = self._fin_musica()
        crossfade = self.config_fundido()[0]
        recorta = fin < self._duracion - RECORTE_MINIMO
        if self._apagar_al_final:
            # el temporizador "al terminar esta cancion" para donde acaba la musica
            if recorta and self._posicion >= fin:
                self._salto_dj = self._gen
                self._apagar_al_final = False
                self.temporizador_cambio.emit(None)
                self.detener()
                self._poner_factor_suave(1.0)
                self.aviso.emit("Temporizador: música detenida")
            return
        if crossfade > 0:
            if self._posicion >= self._t_disparo(fin, crossfade):
                # si la siguiente aun no esta lista se reintenta en el proximo aviso
                if not self._empezar_fundido() and recorta and self._posicion >= fin:
                    self._salto_dj = self._gen
                    self.siguiente(automatico=True)
            return
        if recorta and self._posicion >= fin:
            # sin fundido elegido: se salta el silencio con un fundido muy corto
            self._salto_dj = self._gen
            if not self._empezar_fundido(FUNDIDO_DJ_CORTO):
                self.siguiente(automatico=True)

    # ------------------------------------------------------------ fundido

    def paso_actual(self, pista=None):
        """El paso completo (tipo, curva, tempo…) de esta canción hacia la siguiente: el
        del Mezclador si lo hay, si no la «Mezcla DJ», si no el fundido de siempre.
        None si no hay ninguno."""
        pista = pista if pista is not None else self.actual
        clave = mezcla_dj._clave_de(pista or {})
        paso = self.plan_mezcla.get(clave) if clave else None
        return mezcla_dj.configuracion_paso(
            paso, self.ajustes["mezcla_dj"], self.ajustes["mezcla_dj_seg"],
            self.ajustes["mezcla_dj_graves"], self.ajustes["crossfade"], self._duracion)

    def config_fundido(self, pista=None):
        """(disparo, dur, graves) del fundido de esta canción hacia la siguiente."""
        p = self.paso_actual(pista)
        if p is None:
            return 0, 0, False
        return p["entra"], p["dur"], p["graves"]

    # ---- lo que se sabe de cada canción (análisis y marcas del Mezclador)

    def _analisis_de(self, pista):
        clave = mezcla_dj._clave_de(pista or {})
        if not clave:
            return None
        a = self.plan_analisis.get(clave)
        if a:
            return a
        if clave not in self._an_cache:
            if len(self._an_cache) > 400:
                self._an_cache.clear()
            try:
                from . import analisis_audio
                self._an_cache[clave] = analisis_audio.analisis_guardado(self.coleccion, pista)
            except Exception:  # noqa: BLE001
                self._an_cache[clave] = None
        return self._an_cache[clave]

    def olvidar_analisis(self):
        """Cuando el Mezclador analiza o corrige el tempo de una canción."""
        self._an_cache.clear()

    def _marcas_de(self, pista):
        clave = mezcla_dj._clave_de(pista or {})
        return (self.plan_marcas.get(clave) or {}) if clave else {}

    def cadena_para(self, pista):
        """Los filtros de sonido de siempre más el ecualizador de 3 bandas que se
        eligió para esta canción en el Mezclador (si lo hay)."""
        base = self.cadena_filtros()
        partes = mezcla_dj.filtros_eq(self._marcas_de(pista).get("eq"))
        return mezcla_dj.combinar_filtros(base, (), partes) if partes else base

    def _poner_af(self, m, cadena):
        """Cambia los filtros de un motor solo si de verdad son otros (cada cambio
        reinicia su cadena de audio)."""
        if self._af.get(id(m)) == cadena:
            return
        m.fijar_filtros(cadena)
        self._af[id(m)] = cadena

    def _entrada_de(self, pista, alinear):
        """Segundo en el que entra la canción: el punto de entrada elegido o donde
        empieza su música; con `alinear` y su tempo conocido, en un inicio de compás."""
        base = self._inicio_dj(pista)
        marca = self._marcas_de(pista).get("entrada")
        minimo = float(marca) if marca is not None else float(base or 0.0)
        if alinear:
            an = self._analisis_de(pista)
            if an and an.get("bpm"):
                return mezcla_dj.entrada_alineada(minimo, an, float(pista.get("duracion") or 0))
        return minimo

    def _t_disparo(self, fin, disparo):
        """Segundo de la canción que suena en el que empieza la transición: `disparo`
        segundos antes del final y, si se iguala el tempo o es un corte, en un inicio
        de compás."""
        t = fin - disparo
        p = self.paso_actual()
        if p and (p["tempo"] or p["tipo"] == "corte"):
            an = self._analisis_de(self.actual)
            if an and an.get("bpm"):
                t = mezcla_dj.disparo_alineado(t, an)
        return t

    def _debe_fundir_ya(self):
        d = self.config_fundido()[0]
        return d > 0 and self._posicion >= self._t_disparo(self._fin_musica(), d)

    def _empezar_fundido(self, duracion=None):
        sig = self._mirar_siguiente()
        if sig is None or len(self.audio) < 2:
            return
        paso = self.paso_actual()
        _disparo, dur_cfg, _g = self.config_fundido()
        tipo = paso["tipo"] if paso else "fundido"
        curva = paso["curva"] if paso else "suave"
        tempo = bool(paso and paso["tempo"])
        if duracion:            # saltar un silencio sin fundido elegido: corto y sencillo
            tipo, curva, tempo = "fundido", "suave", False
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
        pista_sale = self.actual
        objetivo_pista = self._avanzar()
        if objetivo_pista is None:
            return
        # a tempo: la que entra se acerca (hasta ±8 %) al tempo de la que sale
        ratio = 1.0
        if tempo:
            a_s, a_e = self._analisis_de(pista_sale), self._analisis_de(objetivo_pista)
            r = mezcla_dj.razon_tempo(mezcla_dj._bpm(a_s), mezcla_dj._bpm(a_e))
            if r:
                ratio = r
        self._gen += 1
        self.activo = 1 - self.activo
        self._fundido = {"saliente": saliente, "entrante": entrante,
                         "inicio": time.time(),
                         "dur": float(duracion or (mezcla_dj.DURACION_CORTE if tipo == "corte"
                                                   else dur_cfg)
                                      or self.ajustes["crossfade"] or FUNDIDO_DJ_CORTO),
                         "tipo": tipo, "curva": "corte" if tipo == "corte" else curva,
                         "graves": tipo == "graves", "ratio": ratio, "estado_filtros": None,
                         "base_sal": self.cadena_para(pista_sale),
                         "base_ent": self.cadena_para(objetivo_pista)}
        # la que entra empieza donde empieza su musica (o en su punto de entrada), y
        # alineada con el compás si se mezcla a tempo
        entrada = self._entrada_de(objetivo_pista, tempo or tipo == "corte")
        entrante.fijar_volumen(0)
        entrante.fijar_velocidad(self.velocidad * ratio)
        self._poner_af(entrante, self._fundido["base_ent"])
        self._cambiar_filtros(0.0)          # p. ej. la que entra llega sin graves
        entrante.cargar(fuente, inicio=entrada)
        self._fuente = fuente
        self.actual = objetivo_pista
        self._escucha_registrada = False
        self._segmentos = []
        self._duracion = float(objetivo_pista.get("duracion") or 0)
        self._posicion = entrada
        self.pista_cambio.emit(objetivo_pista)
        self.duracion_cambio.emit(self._duracion)
        info = dict(fuente.get("info") or {})
        info["local"] = bool(fuente.get("local"))
        self.calidad_cambio.emit(info)
        self.cola_cambio.emit()
        self._pasos_fundido.start()
        self._preparar_extras(self._gen)
        return True

    def _paso_fundido(self):
        f = self._fundido
        if not f:
            self._pasos_fundido.stop()
            return
        avance = min(1.0, (time.time() - f["inicio"]) / max(0.05, f["dur"]))
        v_ent, v_sal = mezcla_dj.curva_volumenes(f.get("curva", "suave"), avance)
        f["entrante"].fijar_volumen(self._vol() * v_ent)
        f["saliente"].fijar_volumen(self._vol() * v_sal)
        self._cambiar_filtros(avance)
        if avance >= 1.0:
            self._cerrar_fundido(completo=True)
            if self._prueba:
                prueba = self._prueba
                QTimer.singleShot(7000, lambda: self._fin_de_prueba(prueba))

    def _cambiar_filtros(self, avance):
        """Filtros de la transición (cambio de graves, filtro, eco): cambian por
        escalones según el avance del fundido."""
        f = self._fundido
        if not f:
            return
        sal, ent = mezcla_dj.partes_transicion(f.get("tipo", "fundido"), avance)
        if (sal, ent) == f.get("estado_filtros"):
            return
        f["estado_filtros"] = (sal, ent)
        self._poner_af(f["saliente"], mezcla_dj.combinar_filtros(f["base_sal"], sal))
        self._poner_af(f["entrante"], mezcla_dj.combinar_filtros(f["base_ent"], ent))

    def _cerrar_fundido(self, completo):
        """Acaba el fundido: la que salía se detiene y los dos motores vuelven a su sonido
        (la que sigue con el ecualizador de su canción, si lo tiene)."""
        f = self._fundido
        if not f:
            return
        f["saliente"].detener()
        self._fundido = None
        self._pasos_fundido.stop()
        self._poner_af(f["saliente"], self.cadena_filtros())
        self._poner_af(f["entrante"], f["base_ent"] if completo else self.cadena_filtros())
        self._aplicar_volumen()
        ratio = f.get("ratio", 1.0)
        if completo and abs(ratio - 1.0) > 0.001:
            self._devolver_tempo(f["entrante"], ratio)
        elif abs(ratio - 1.0) > 0.001:
            f["entrante"].fijar_velocidad(self.velocidad)

    def _devolver_tempo(self, m, ratio):
        """Tras mezclar a tempo, la canción vuelve poco a poco a su velocidad."""
        pasos = 6

        def paso(i):
            if self._fundido or self.motor_actual() is not m:
                return
            m.fijar_velocidad(self.velocidad * (ratio + (1.0 - ratio) * i / pasos))
        for i in range(1, pasos + 1):
            QTimer.singleShot(int(700 * i), lambda i=i: paso(i))

    def _cortar_fundido(self):
        if self._fundido:
            self._cerrar_fundido(completo=False)

    # ------------------------------------------------------------ temporizador

    def programar_apagado(self, minutos=None, al_terminar=False):
        self._apagar_al_final = bool(al_terminar)
        self._temporizador.setInterval(1000)
        self._poner_factor_suave(1.0)
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
            self._temporizador.setInterval(1000)
            self.temporizador_cambio.emit(None)
            self.pausar()
            # en pausa ya no se oye: el volumen vuelve a su sitio para la proxima vez
            self._poner_factor_suave(1.0)
            self.aviso.emit("Temporizador: música en pausa. ¡Buenas noches!")
            return
        if self.ajustes["apagado_suave"] and quedan <= APAGADO_SUAVE_SEG:
            # los ultimos 30 s el volumen baja poco a poco (a pasos de 0,2 s)
            if self._temporizador.interval() != 200:
                self._temporizador.setInterval(200)
            self._poner_factor_suave(quedan / APAGADO_SUAVE_SEG)
        elif self._factor_suave != 1.0:
            self._poner_factor_suave(1.0)
        segundos = int(quedan + 0.999)
        if segundos != getattr(self, "_ultimo_aviso_tempo", None):
            self._ultimo_aviso_tempo = segundos
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
