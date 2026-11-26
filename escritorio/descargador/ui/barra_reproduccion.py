# -*- coding: utf-8 -*-
"""La barra de abajo: lo que suena, los controles y el volumen."""

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget,
                               QFrame)

from . import iconos
from .componentes import BotonIcono, BotonPlay, Deslizador, Portada, formato_tiempo
from .estilos import C
from .cast_boton import BotonCast
from .panel_mas import FichaMas, PanelMas


ALTO = 92


def _t(seg):
    return formato_tiempo(seg) or "0:00"


class EnlaceTexto(QPushButton):
    def __init__(self, texto="", tam=13.5, negrita=False, color=None, padre=None):
        super().__init__(texto, padre)
        self._entero, self._tope = "", 0
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        color = color or C["texto"]
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;padding:0;text-align:left;"
            f"font-size:{tam}px;{'font-weight:600;' if negrita else ''}color:{color};}}"
            f"QPushButton:hover{{text-decoration:underline;color:{C['texto']};}}")

    def poner(self, texto, ancho=230):
        self._entero, self._tope = texto or "", ancho
        self._recortar(ancho)
        self.updateGeometry()

    def _recortar(self, ancho):
        fm = QFontMetrics(self.font())
        corto = fm.elidedText(self._entero, Qt.ElideRight, ancho)
        if corto != self.text():
            self.setText(corto)
        self.setToolTip(self._entero if corto != self._entero else "")

    def sizeHint(self):
        h = super().sizeHint()
        if self._tope:                     # lo que ocuparía entero: con sitio, se vuelve a ver entero
            h.setWidth(min(self._tope, QFontMetrics(self.font()).horizontalAdvance(self._entero)) + 4)
        return h

    def minimumSizeHint(self):
        h = super().minimumSizeHint()
        if self._tope:
            h.setWidth(60)
        return h

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._tope:                     # en ventanas estrechas termina en «…», no cortado a media letra
            self._recortar(min(self._tope, max(30, self.width() - 2)))


class BarraReproduccion(QFrame):
    pidio_panel = Signal(str)         # sonando | cola | letras
    pidio_sonando = Signal()          # el reproductor en grande
    pidio_letra = Signal()            # la letra a pantalla completa
    pidio_video = Signal()
    pidio_vinilo = Signal()           # el modo vinilo a pantalla completa
    pidio_mini = Signal()
    pidio_escritorio = Signal()       # la escena de escritorio a pantalla completa
    pidio_ecualizador = Signal()
    pidio_visualizador = Signal(str)  # ondas | particulas | barras (a pantalla completa, donadores)
    pidio_karaoke = Signal()          # karaoke y letras a pantalla completa (donadores)
    pidio_escena = Signal()           # la letra a pantalla completa con efectos (donadores)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.setObjectName("reproductor")
        self.setFixedHeight(ALTO)
        self._dur = 0.0
        self._arrastrando = False

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(10, 8, 14, 8)
        raiz.setSpacing(10)

        # ---- izquierda: lo que suena
        izq = QWidget()
        izq.setMinimumWidth(240)
        hi = QHBoxLayout(izq)
        hi.setContentsMargins(0, 0, 0, 0)
        hi.setSpacing(12)
        self.portada = Portada(56, 56, "cuadrada", 5)
        self.portada.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.portada.setCursor(Qt.PointingHandCursor)
        self.portada.setToolTip("Ver el reproductor en grande")
        self.portada.mousePressEvent = lambda _e: self._al_portada()
        hi.addWidget(self.portada)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        textos.addStretch(1)
        self.et_titulo = EnlaceTexto("", 14, True)
        self.et_titulo.clicked.connect(self._ir_contexto)
        textos.addWidget(self.et_titulo)
        self.et_artista = EnlaceTexto("", 12, False, C["texto2"])
        self.et_artista.clicked.connect(self._ir_artista)
        textos.addWidget(self.et_artista)
        # debajo del artista: entre los botones, al aparecer corría los de en medio
        self.et_calidad = QLabel("")
        self.et_calidad.setObjectName("insignia")
        self.et_calidad.hide()
        self.et_calidad.setFixedHeight(18)
        textos.addSpacing(2)
        textos.addWidget(self.et_calidad, 0, Qt.AlignLeft)
        textos.addStretch(1)
        hi.addLayout(textos)
        self.bt_gusta = BotonIcono("corazon", 20, "Guardar en Tus me gusta", 40)
        self.bt_gusta.clicked.connect(self._alternar_gusta)
        hi.addWidget(self.bt_gusta)
        self.et_descargado = QLabel()
        self.et_descargado.setPixmap(iconos.pixmap("descargado", 15, C["acento"]))
        self.et_descargado.setToolTip("Suena desde tu disco (sin internet)")
        self.et_descargado.hide()
        hi.addWidget(self.et_descargado)
        hi.addStretch(1)
        raiz.addWidget(izq, 30)

        # ---- centro: controles y progreso
        centro = QVBoxLayout()
        centro.setSpacing(2)
        botones = QHBoxLayout()
        botones.setSpacing(10)
        botones.addStretch(1)
        self.bt_aleatorio = BotonIcono("aleatorio", 19, "Aleatorio", 38)
        self.bt_aleatorio.clicked.connect(self._aleatorio)
        botones.addWidget(self.bt_aleatorio)
        self.bt_anterior = BotonIcono("anterior", 20, "Anterior", 40)
        self.bt_anterior.clicked.connect(self.r.anterior)
        botones.addWidget(self.bt_anterior)
        self.bt_play = BotonPlay(42, claro=True)
        self.bt_play.setToolTip("Reproducir / pausar  (Espacio)")
        self.bt_play.clicked.connect(self.r.alternar)
        botones.addWidget(self.bt_play)
        self.bt_siguiente = BotonIcono("siguiente", 20, "Siguiente", 40)
        self.bt_siguiente.clicked.connect(self.r.siguiente)
        botones.addWidget(self.bt_siguiente)
        self.bt_repetir = BotonIcono("repetir", 19, "Repetir", 38)
        self.bt_repetir.clicked.connect(self._repetir)
        botones.addWidget(self.bt_repetir)
        botones.addStretch(1)
        centro.addLayout(botones)
        tiempo = QHBoxLayout()
        tiempo.setSpacing(6)
        self.et_actual = QLabel("0:00")
        self.et_actual.setObjectName("ayuda")
        self.et_actual.setFixedWidth(42)
        self.et_actual.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        tiempo.addWidget(self.et_actual, 0, Qt.AlignBottom)     # al lado de la línea, también con mascota encima
        self.barra = Deslizador(16)
        self.barra.movido.connect(self._moviendo)
        self.barra.soltado.connect(self._soltar)
        gm = getattr(ctx, "mascota", None)
        if gm is not None:
            self.barra.alto_cambiado = self._ajustar_alto
            self.barra.poner_mascota(gm, self.r)
        tiempo.addWidget(self.barra, 1)
        self.et_total = QLabel("0:00")
        self.et_total.setObjectName("ayuda")
        self.et_total.setFixedWidth(42)
        tiempo.addWidget(self.et_total, 0, Qt.AlignBottom)
        centro.addLayout(tiempo)
        caja_centro = QWidget()
        caja_centro.setLayout(centro)
        caja_centro.setMaximumWidth(720)
        raiz.addWidget(caja_centro, 40)

        # ---- derecha
        der = QHBoxLayout()
        der.setSpacing(2)
        der.addStretch(1)
        # a la vista, lo de todos los días; lo demás, con su nombre, en «Más»
        self.bt_video = BotonIcono("video", 20, "Ver el video", 40)
        self.bt_video.clicked.connect(self._video)
        self.bt_video.installEventFilter(self)          # con el ratón encima ya se va pidiendo el video
        der.addWidget(self.bt_video)
        self.bt_letras = BotonIcono("letras", 20, "Letra  (Ctrl+Mayús+L)", 40)
        self.bt_letras.clicked.connect(self.pidio_letra.emit)
        der.addWidget(self.bt_letras)
        self.bt_cola = BotonIcono("cola", 20, "Cola", 40)
        self.bt_cola.clicked.connect(lambda: self.pidio_panel.emit("cola"))
        der.addWidget(self.bt_cola)
        self.bt_escritorio = BotonIcono("escritorio", 20, "Escena de escritorio (Ctrl+Shift+D)", 40)
        self.bt_escritorio.clicked.connect(self.pidio_escritorio.emit)
        der.addWidget(self.bt_escritorio)
        self.panel_mas = PanelMas(self)
        mas = self.panel_mas.agregar
        self.bt_visual = mas(FichaMas("visualizador", "Visualizador", "Visualizador y karaoke", cierra=False))
        self.bt_visual.clicked.connect(self._menu_visual)
        self.bt_karaoke = mas(FichaMas("letras", "Karaoke", "Karaoke a pantalla completa"))
        self.bt_karaoke.clicked.connect(self.pidio_karaoke.emit)
        self.bt_vinilo = mas(FichaMas("disco", "Modo vinilo"))
        self.bt_vinilo.clicked.connect(self.pidio_vinilo.emit)
        self.bt_mini = mas(FichaMas("mini", "Mini reproductor", "Mini reproductor (siempre encima)"))
        self.bt_mini.clicked.connect(self.pidio_mini.emit)
        self.bt_eq = mas(FichaMas("ecualizador", "Ecualizador", "Ecualizador y sonido"))
        self.bt_eq.clicked.connect(self.pidio_ecualizador.emit)
        self.bt_super = mas(FichaMas("altavoz_fuerte", "Volumen máximo", cierra=False))
        self.bt_super.clicked.connect(self._menu_super)
        self.bt_temporizador = mas(FichaMas("temporizador", "Apagar en…", "Temporizador para dormir", cierra=False))
        self.bt_temporizador.clicked.connect(self._menu_temporizador)
        self.bt_juntos = mas(FichaMas("usuario", "Escuchar juntos"))
        self.bt_juntos.clicked.connect(self._abrir_juntos)
        self.bt_que_suena = mas(FichaMas("musica", "¿Qué suena?", "Reconocer la canción que se oye en la PC"))
        self.bt_que_suena.clicked.connect(lambda: self.ctx.ventana.abrir_que_suena())
        self.bt_cast = BotonCast(self.r.cast, 40)      # Chromecast (oculto si no hay)
        der.addWidget(self.bt_cast)
        self.bt_mas = BotonIcono("puntos", 20, "Más: vinilo, ecualizador, apagar en…, mini reproductor", 40)
        self.bt_mas.clicked.connect(self.abrir_mas)
        der.addWidget(self.bt_mas)
        der.addSpacing(4)
        self.bt_volumen = BotonIcono("altavoz_fuerte", 20, "Silenciar", 40)
        self.bt_volumen.clicked.connect(self._silenciar)
        der.addWidget(self.bt_volumen)
        self.volumen = Deslizador(16, rueda=True)
        self.volumen.setFixedWidth(110)
        self.volumen.set_valor(self.r.volumen / 100)
        self.volumen.movido.connect(lambda v: self.r.fijar_volumen(int(v * 100)))
        self.volumen.soltado.connect(self._soltar_volumen)
        der.addWidget(self.volumen)
        caja_der = QWidget()
        caja_der.setLayout(der)
        raiz.addWidget(caja_der, 30)
        self._antes_mudo = 0

        # ---- senales
        self.r.pista_cambio.connect(self._pista)
        self.r.estado_cambio.connect(self._estado)
        self.r.posicion_cambio.connect(self._posicion)
        self.r.duracion_cambio.connect(self._duracion)
        self.r.calidad_cambio.connect(self._calidad)
        self.r.modo_cambio.connect(self._modo)
        self.r.temporizador_cambio.connect(self._temporizador)
        ctx.me_gusta_cambio.connect(lambda *_: self._pintar_gusta())
        self._pintar_modos()
        self._pintar_super()
        ctx.sonido_cambio.connect(self._pintar_super)
        # colores que siguen la carátula (donadores), insignia de calidad real y sonidos de interfaz
        from ..paleta_caratula import colores_de
        from ..sonidos_ui import instalar
        self._colores = colores_de(ctx)
        self._colores.cambio.connect(self._pintar_colores)
        if hasattr(self.r, "audio_real_cambio"):     # un reproductor sin ese aviso (simulado) no rompe la barra
            self.r.audio_real_cambio.connect(self._audio_real)
        instalar(ctx)
        self._pista(None)

    # ------------------------------------------------------------ eventos del motor

    def _pista(self, pista):
        vacia = pista is None
        for w in (self.bt_gusta, self.bt_letras, self.bt_video, self.bt_vinilo):
            w.setEnabled(not vacia)
        if vacia:
            self.portada.set_url("")
            self.et_titulo.poner("")
            self.et_artista.poner("")
            self.et_calidad.hide()
            self.et_descargado.hide()
            return
        self.portada.set_url(pista.get("miniatura") or "")
        self.et_titulo.poner(pista.get("titulo") or "", 210)
        self.et_artista.poner(pista.get("artista") or "", 210)
        self.bt_video.setEnabled(bool(pista.get("video_id"))
                                 or (bool(pista.get("archivo")) and not pista.get("es_audio")))
        self._pintar_gusta()

    def _pintar_gusta(self):
        p = self.r.actual
        gusta = bool(p and self.ctx.coleccion.me_gusta(p.get("clave")))
        self.bt_gusta.set_icono("corazon_lleno" if gusta else "corazon")
        self.bt_gusta.set_activo(gusta, punto=False)
        self.bt_gusta.setToolTip("Quitar de Tus me gusta" if gusta else "Guardar en Tus me gusta")

    def _ajustar_alto(self):
        """La barra de progreso crece cuando hay una mascotita encima: el reproductor también."""
        self.setFixedHeight(ALTO + max(0, self.barra.height() - 16))

    def _estado(self, estado):
        self.bt_play.set_sonando(estado in ("sonando",))
        self.bt_play.set_cargando(estado == "cargando")

    def _posicion(self, pos):
        if self._arrastrando:
            return
        self.et_actual.setText(_t(pos))
        if self._dur > 0:
            self.barra.set_valor(pos / self._dur)

    def _duracion(self, dur):
        self._dur = float(dur or 0)
        self.et_total.setText(_t(self._dur))

    def _calidad(self, info):
        texto = ""
        ayuda = ""
        if info.get("local"):
            texto = "EN EL DISCO"
            ayuda = info.get("archivo", "")
        elif info.get("alto"):
            fps = int(info.get("fps") or 0)
            alto = int(info["alto"])
            nombre = {4320: "8K", 2160: "4K", 1440: "2K"}.get(alto, f"{alto}p")
            texto = f"{nombre}{fps if fps > 30 else ''}"
            if info.get("hdr"):
                texto += " HDR"
            ayuda = (f"Video {info['alto']}p {fps} fps · {info.get('vcodec', '').split('.')[0]}\n"
                     f"Audio {info.get('acodec', '')} {info.get('abr', '')} kbps")
        elif info.get("acodec"):
            codec = (info.get("acodec") or "").split(".")[0].upper()
            codec = {"MP4A": "AAC"}.get(codec, codec)
            texto = f"{codec} {info.get('abr') or ''}".strip()
            ayuda = f"Audio {codec} a {info.get('abr')} kbps, {info.get('asr') or 48000} Hz"
        self.et_calidad.setText(texto)
        self.et_calidad.setToolTip(ayuda)
        self.et_calidad.setVisible(bool(texto))
        self.et_descargado.setVisible(bool(info.get("local")))
        if not info.get("alto"):
            self._pedir_audio_real()

    def _audio_real(self, datos):
        """Códec y tasa del audio que el motor decodifica de verdad (reemplaza lo que decía la plataforma)."""
        from .. import calidad_real
        if self.r.modo != "audio" or self.r.actual is None:
            return
        texto = calidad_real.etiqueta(datos)
        if texto:
            self.et_calidad.setText(texto)
            self.et_calidad.setToolTip(calidad_real.ayuda(datos))
            self.et_calidad.show()

    def _pedir_audio_real(self):
        m = getattr(self.r, "motor_actual", lambda: None)()
        f = getattr(m, "info_audio", None)
        if f is not None:
            self._audio_real(f())

    def _modo(self, modo):
        self.bt_video.set_activo(modo == "video", punto=True)
        self.bt_video.setToolTip("Volver a solo audio" if modo == "video" else "Ver el video")

    def _temporizador(self, restante):
        activo = restante is not None
        self.bt_temporizador.set_activo(activo)
        self._pintar_mas()
        if restante == -1:
            self.bt_temporizador.setToolTip("Se detiene al terminar la canción")
        elif activo:
            self.bt_temporizador.setToolTip(f"Se detiene en {int(restante) // 60 + 1} min")
        else:
            self.bt_temporizador.setToolTip("Temporizador para dormir")

    # ------------------------------------------------------------ acciones

    def _moviendo(self, v):
        self._arrastrando = True
        self.et_actual.setText(_t(v * self._dur))

    def _soltar(self, v):
        self._arrastrando = False
        if self._dur > 0:
            self.r.buscar(v * self._dur)

    def _soltar_volumen(self, v):
        self.r.fijar_volumen(int(v * 100))
        self.ctx.ajustes.guardar()
        self._pintar_volumen()

    def _pintar_volumen(self):
        v = self.r.volumen
        self.bt_volumen.set_icono("altavoz_mute" if v == 0 else ("altavoz" if v < 50 else "altavoz_fuerte"))
        self.volumen.set_valor(v / 100)

    def _silenciar(self):
        if self.r.volumen > 0:
            self._antes_mudo = self.r.volumen
            self.r.fijar_volumen(0)
        else:
            self.r.fijar_volumen(self._antes_mudo or 70)
        self._pintar_volumen()

    def subir_volumen(self, delta):
        self.r.fijar_volumen(self.r.volumen + delta)
        self._pintar_volumen()

    def _aleatorio(self):
        activo = self.r.alternar_aleatorio()
        self.ctx.aviso.emit("Aleatorio activado" if activo else "Aleatorio desactivado")
        self._pintar_modos()

    def _repetir(self):
        modo = self.r.ciclar_repetir()
        self.ctx.aviso.emit({"no": "Repetir desactivado", "todo": "Repetir toda la cola",
                             "una": "Repetir esta canción"}[modo])
        self._pintar_modos()

    def _pintar_modos(self):
        self.bt_aleatorio.set_activo(self.r.aleatorio)
        self.bt_repetir.set_icono("repetir_una" if self.r.repetir == "una" else "repetir")
        self.bt_repetir.set_activo(self.r.repetir != "no")
        self._pintar_volumen()

    def _video(self):
        if self.r.modo == "video":
            self.r.cambiar_modo("audio")
        else:
            self.pidio_video.emit()

    def _al_portada(self):
        if self.r.modo == "video":
            self.pidio_video.emit()
        elif self.r.actual is not None:
            self.pidio_sonando.emit()

    def _alternar_gusta(self):
        if self.r.actual:
            self.ctx.alternar_me_gusta(self.r.actual)

    def _ir_artista(self):
        p = self.r.actual
        if not p:
            return
        artistas = [a for a in p.get("artistas") or [] if a.get("id")]
        if artistas:
            self.ctx.navegar({"pagina": "artista", "id": artistas[0]["id"]})

    def _ir_contexto(self):
        p = self.r.actual
        if not p:
            return
        alb = p.get("album") or {}
        ctx = self.r.contexto or {}
        if ctx.get("tipo") in ("album", "lista", "mi_lista", "me_gusta") and ctx.get("id"):
            destino = {"album": "album", "lista": "lista", "mi_lista": "mi_lista",
                       "me_gusta": "me_gusta"}[ctx["tipo"]]
            self.ctx.navegar({"pagina": destino, "id": ctx["id"]})
        elif alb.get("id"):
            self.ctx.navegar({"pagina": "album", "id": alb["id"]})
        elif self.r.modo == "video":
            self.pidio_video.emit()

    def eventFilter(self, obj, ev):
        if obj is self.bt_video and ev.type() == QEvent.Enter:
            f = getattr(self.r, "adelantar_video", None)
            if f is not None:
                f()
        return super().eventFilter(obj, ev)

    def abrir_mas(self):
        self.panel_mas.alternar(self.bt_mas)

    def _pintar_mas(self):
        """Un puntito en «Más» si dentro hay algo en marcha (temporizador, escuchar juntos, volumen máximo)."""
        en_marcha = [f.texto for f in (self.bt_temporizador, self.bt_juntos, self.bt_super) if f._activo]
        self.bt_mas.set_activo(bool(en_marcha), punto=True)
        self.bt_mas.setToolTip("Más · en marcha: " + ", ".join(en_marcha) if en_marcha else
                               "Más: vinilo, ecualizador, apagar en…, mini reproductor")

    def _menu_temporizador(self):
        menu = QMenu(self)
        restante = self.r.restante_apagado()
        if restante is not None:
            texto = ("Activo: al terminar la canción" if restante == -1
                     else f"Activo: quedan {restante // 60} min {restante % 60} s")
            a = menu.addAction(texto)
            a.setEnabled(False)
            menu.addAction("Desactivar", lambda: self.r.programar_apagado(None))
            menu.addSeparator()
        for m in (5, 10, 15, 30, 45, 60, 90):
            menu.addAction(f"Detener en {m} minutos", lambda m=m: self.r.programar_apagado(m))
        menu.addAction("Al terminar esta canción", lambda: self.r.programar_apagado(None, True))
        self._menu_de(menu, self.bt_temporizador)

    def _menu_super(self):
        from ..reproduccion import NOMBRES_VOLUMEN_MAXIMO
        menu = QMenu(self)
        titulo = menu.addAction("Volumen máximo: lo más alto sin que se rompa")
        titulo.setEnabled(False)
        menu.addSeparator()
        actual = self.ctx.ajustes.get("volumen_maximo")
        for nivel, nombre in NOMBRES_VOLUMEN_MAXIMO.items():
            a = menu.addAction(nombre, lambda n=nivel: self._poner_super(n))
            a.setCheckable(True)
            a.setChecked(nivel == actual)
        menu.addSeparator()
        menu.addAction("Ecualizador y más…", self.pidio_ecualizador.emit)
        self._menu_de(menu, self.bt_super)

    def _menu_de(self, menu, ficha):
        """El menú de una ficha de «Más»: en su sitio; al elegir algo, el panel se cierra."""
        ancla = ficha if ficha.isVisible() else self.bt_mas
        if menu.exec(ancla.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6))) is not None:
            self.panel_mas.hide()

    def _poner_super(self, nivel):
        from .. import sonoridad
        from ..reproduccion import NOMBRES_VOLUMEN_MAXIMO
        sonoridad.poner_nivel(self.ctx.ajustes, nivel)
        self.ctx.ajustes.guardar()
        self.r.aplicar_sonido()
        self._pintar_super()
        self.ctx.aviso.emit("Volumen máximo apagado" if nivel not in sonoridad.NIVELES
                            else f"Volumen máximo: {NOMBRES_VOLUMEN_MAXIMO[nivel].lower()}")

    def _pintar_super(self):
        from .. import sonoridad
        from ..reproduccion import NOMBRES_VOLUMEN_MAXIMO
        nivel = self.ctx.ajustes.get("volumen_maximo")
        self.bt_super.set_activo(nivel in sonoridad.NIVELES)
        self._pintar_mas()
        self.bt_super.setToolTip("Volumen máximo: "
                                 + NOMBRES_VOLUMEN_MAXIMO.get(nivel, "Apagado").lower())

    def _abrir_juntos(self):
        from .paginas import juntos
        g = juntos.gestor(self.ctx)
        if not getattr(self, "_juntos_atado", False):
            self._juntos_atado = True
            g.cambio.connect(lambda: self._pintar_juntos(g))
        juntos.abrir_ventana(self.ctx, self.window())

    def _pintar_juntos(self, g):
        s = g.sala
        self.bt_juntos.set_activo(s is not None)
        self._pintar_mas()
        self.bt_juntos.setToolTip(f"Escuchar juntos · sala {s.codigo}" if s else "Escuchar juntos")

    def _menu_visual(self):
        from .visualizador import ESTILOS
        g = getattr(self.ctx, "premium", None)
        candado = "" if g is not None and g.premium else "🔒 "
        menu = QMenu(self)
        for clave, nombre in ESTILOS.items():
            menu.addAction(f"{candado}Visualizador · {nombre}", lambda k=clave: self.pidio_visualizador.emit(k))
        menu.addSeparator()
        menu.addAction(f"{candado}Karaoke a pantalla completa", self.pidio_karaoke.emit)
        menu.addAction(f"{candado}Letra con efectos a pantalla completa", self.pidio_escena.emit)
        if candado:
            menu.addSeparator()
            aviso = menu.addAction("Exclusivo para donadores")
            aviso.setEnabled(False)
        self._menu_de(menu, self.bt_visual)

    # ------------------------------------------------------------ colores de la carátula

    def _pintar_colores(self):
        """Un paso de la transición: el relleno del progreso y el tinte de la barra siguen a la carátula."""
        f = self._colores.fuerza
        if f > 0.02:
            c = self._colores.colores()[2]
            self.barra.color_relleno = QColor(c).lighter(115)
        else:
            self.barra.color_relleno = None
        self.barra.update()
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        f = self._colores.fuerza
        if f <= 0.02:
            return
        a, b, c = [QColor(h) for h in self._colores.hex_actuales()]
        g = QLinearGradient(0, 0, self.width(), 0)
        for pos, col in ((0.0, a), (0.55, b), (1.0, c)):
            col.setAlphaF(0.30 * f)
            g.setColorAt(pos, col)
        p = QPainter(self)
        p.fillRect(self.rect(), g)
        p.end()

    def marcar_panel(self, nombre):
        self.bt_letras.set_activo(nombre == "letras")
        self.bt_cola.set_activo(nombre == "cola")


def _no_usado():  # pragma: no cover
    return QTimer
