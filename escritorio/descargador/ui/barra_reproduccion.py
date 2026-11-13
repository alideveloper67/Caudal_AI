# -*- coding: utf-8 -*-
"""La barra de abajo: lo que suena, los controles y el volumen."""

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget,
                               QFrame)

from . import iconos
from .componentes import BotonIcono, BotonPlay, Deslizador, Portada, formato_tiempo
from .estilos import C


def _t(seg):
    return formato_tiempo(seg) or "0:00"


class EnlaceTexto(QPushButton):
    def __init__(self, texto="", tam=13.5, negrita=False, color=None, padre=None):
        super().__init__(texto, padre)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        color = color or C["texto"]
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;padding:0;text-align:left;"
            f"font-size:{tam}px;{'font-weight:600;' if negrita else ''}color:{color};}}"
            f"QPushButton:hover{{text-decoration:underline;color:{C['texto']};}}")

    def poner(self, texto, ancho=230):
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.font())
        self.setText(fm.elidedText(texto or "", Qt.ElideRight, ancho))
        self.setToolTip(texto if fm.horizontalAdvance(texto or "") > ancho else "")


class BarraReproduccion(QFrame):
    pidio_panel = Signal(str)         # sonando | cola | letras
    pidio_video = Signal()
    pidio_mini = Signal()
    pidio_ecualizador = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.setObjectName("reproductor")
        self.setFixedHeight(88)
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
        textos.addStretch(1)
        hi.addLayout(textos)
        self.bt_gusta = BotonIcono("corazon", 18, "Guardar en Tus me gusta", 32)
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
        self.bt_aleatorio = BotonIcono("aleatorio", 18, "Aleatorio", 32)
        self.bt_aleatorio.clicked.connect(self._aleatorio)
        botones.addWidget(self.bt_aleatorio)
        self.bt_anterior = BotonIcono("anterior", 18, "Anterior", 32)
        self.bt_anterior.clicked.connect(self.r.anterior)
        botones.addWidget(self.bt_anterior)
        self.bt_play = BotonPlay(36, claro=True)
        self.bt_play.setToolTip("Reproducir / pausar  (Espacio)")
        self.bt_play.clicked.connect(self.r.alternar)
        botones.addWidget(self.bt_play)
        self.bt_siguiente = BotonIcono("siguiente", 18, "Siguiente", 32)
        self.bt_siguiente.clicked.connect(self.r.siguiente)
        botones.addWidget(self.bt_siguiente)
        self.bt_repetir = BotonIcono("repetir", 18, "Repetir", 32)
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
        tiempo.addWidget(self.et_actual)
        self.barra = Deslizador(16)
        self.barra.movido.connect(self._moviendo)
        self.barra.soltado.connect(self._soltar)
        tiempo.addWidget(self.barra, 1)
        self.et_total = QLabel("0:00")
        self.et_total.setObjectName("ayuda")
        self.et_total.setFixedWidth(42)
        tiempo.addWidget(self.et_total)
        centro.addLayout(tiempo)
        caja_centro = QWidget()
        caja_centro.setLayout(centro)
        caja_centro.setMaximumWidth(720)
        raiz.addWidget(caja_centro, 40)

        # ---- derecha
        der = QHBoxLayout()
        der.setSpacing(2)
        der.addStretch(1)
        self.et_calidad = QLabel("")
        self.et_calidad.setObjectName("insignia")
        self.et_calidad.hide()
        self.et_calidad.setFixedHeight(20)
        der.addWidget(self.et_calidad, 0, Qt.AlignVCenter)
        der.addSpacing(4)
        self.bt_video = BotonIcono("video", 18, "Ver el video", 32)
        self.bt_video.clicked.connect(self._video)
        der.addWidget(self.bt_video)
        self.bt_letras = BotonIcono("letras", 18, "Letra", 32)
        self.bt_letras.clicked.connect(lambda: self.pidio_panel.emit("letras"))
        der.addWidget(self.bt_letras)
        self.bt_cola = BotonIcono("cola", 18, "Cola", 32)
        self.bt_cola.clicked.connect(lambda: self.pidio_panel.emit("cola"))
        der.addWidget(self.bt_cola)
        self.bt_temporizador = BotonIcono("temporizador", 17, "Temporizador para dormir", 32)
        self.bt_temporizador.clicked.connect(self._menu_temporizador)
        der.addWidget(self.bt_temporizador)
        self.bt_eq = BotonIcono("ecualizador", 17, "Ecualizador y sonido", 32)
        self.bt_eq.clicked.connect(self.pidio_ecualizador.emit)
        der.addWidget(self.bt_eq)
        self.bt_mini = BotonIcono("mini", 18, "Mini reproductor (siempre encima)", 32)
        self.bt_mini.clicked.connect(self.pidio_mini.emit)
        der.addWidget(self.bt_mini)
        self.bt_volumen = BotonIcono("altavoz_fuerte", 18, "Silenciar", 32)
        self.bt_volumen.clicked.connect(self._silenciar)
        der.addWidget(self.bt_volumen)
        self.volumen = Deslizador(16, rueda=True)
        self.volumen.setFixedWidth(100)
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
        self._pista(None)

    # ------------------------------------------------------------ eventos del motor

    def _pista(self, pista):
        vacia = pista is None
        for w in (self.bt_gusta, self.bt_letras, self.bt_video):
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

    def _modo(self, modo):
        self.bt_video.set_activo(modo == "video", punto=True)
        self.bt_video.setToolTip("Volver a solo audio" if modo == "video" else "Ver el video")

    def _temporizador(self, restante):
        activo = restante is not None
        self.bt_temporizador.set_activo(activo)
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
        else:
            self.pidio_panel.emit("sonando")

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
        menu.exec(self.bt_temporizador.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6)))

    def marcar_panel(self, nombre):
        self.bt_letras.set_activo(nombre == "letras")
        self.bt_cola.set_activo(nombre == "cola")


def _no_usado():  # pragma: no cover
    return QTimer
