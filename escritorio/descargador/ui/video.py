# -*- coding: utf-8 -*-
"""Video: la vista grande (con pantalla completa) y el mini reproductor flotante.

mpv dibuja directamente en una ventana nativa de Windows (QWidget con
WA_NativeWindow); por eso los controles van debajo de la imagen y no encima.
"""

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QPushButton, QSizeGrip, QVBoxLayout,
                               QWidget)

from . import iconos, imagenes
from .componentes import BotonIcono, BotonPlay, Deslizador, Portada, formato_tiempo, fuente
from .estilos import C

VELOCIDADES = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]


class PantallaNativa(QWidget):
    """Donde pinta mpv. Negra mientras no hay imagen."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setStyleSheet("background:#000000;")
        self.setMinimumSize(160, 90)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))


class VistaVideo(QWidget):
    volver = Signal()
    pidio_mini = Signal()
    pidio_completa = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.titulo = "Video"
        self.motor = None
        self._pendiente = None
        self._dur = 0.0
        self._arrastrando = False
        self._info = {}
        self._caidos_previos = None
        self._avisos_tirones = 0
        self.en_completa = False

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # cabecera
        self.cab = QWidget()
        hc = QHBoxLayout(self.cab)
        hc.setContentsMargins(14, 10, 14, 10)
        hc.setSpacing(10)
        bt_volver = BotonIcono("atras", 18, "Volver", 34)
        bt_volver.clicked.connect(self.volver.emit)
        hc.addWidget(bt_volver)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        self.et_titulo = QLabel("")
        self.et_titulo.setStyleSheet("font-size:16px;font-weight:800;")
        textos.addWidget(self.et_titulo)
        self.et_autor = QLabel("")
        self.et_autor.setObjectName("secundario")
        textos.addWidget(self.et_autor)
        hc.addLayout(textos, 1)
        self.et_calidad = QLabel("")
        self.et_calidad.setObjectName("insignia")
        hc.addWidget(self.et_calidad)
        v.addWidget(self.cab)

        self.pantalla = PantallaNativa()
        v.addWidget(self.pantalla, 1)

        # controles
        self.controles = QWidget()
        self.controles.setStyleSheet(f"background:{C['panel']};")
        vc = QVBoxLayout(self.controles)
        vc.setContentsMargins(16, 6, 16, 10)
        vc.setSpacing(2)
        tiempo = QHBoxLayout()
        self.et_actual = QLabel("0:00")
        self.et_actual.setObjectName("ayuda")
        tiempo.addWidget(self.et_actual)
        self.barra = Deslizador(18)
        self.barra.movido.connect(self._moviendo)
        self.barra.soltado.connect(self._soltar)
        tiempo.addWidget(self.barra, 1)
        self.et_total = QLabel("0:00")
        self.et_total.setObjectName("ayuda")
        tiempo.addWidget(self.et_total)
        vc.addLayout(tiempo)
        fila = QHBoxLayout()
        fila.setSpacing(4)
        self.bt_play = BotonPlay(40, claro=True)
        self.bt_play.clicked.connect(self.r.alternar)
        b_ant = BotonIcono("anterior", 18, "Anterior", 34)
        b_ant.clicked.connect(self.r.anterior)
        b_atr = BotonIcono("retroceder10", 22, "Atrasar 10 s  (←)", 34)
        b_atr.clicked.connect(lambda: self.r.avanzar(-10))
        b_ade = BotonIcono("adelantar10", 22, "Adelantar 10 s  (→)", 34)
        b_ade.clicked.connect(lambda: self.r.avanzar(10))
        b_sig = BotonIcono("siguiente", 18, "Siguiente", 34)
        b_sig.clicked.connect(self.r.siguiente)
        for w in (b_ant, b_atr, self.bt_play, b_ade, b_sig):
            fila.addWidget(w)
        fila.addSpacing(12)
        self.bt_vol = BotonIcono("altavoz_fuerte", 18, "Volumen", 34)
        self.bt_vol.clicked.connect(lambda: self.ctx.ventana.barra.bt_volumen.click())
        fila.addWidget(self.bt_vol)
        self.volumen = Deslizador(16, rueda=True)
        self.volumen.setFixedWidth(90)
        self.volumen.set_valor(self.r.volumen / 100)
        self.volumen.movido.connect(lambda val: self.r.fijar_volumen(int(val * 100)))
        self.volumen.soltado.connect(lambda val: (self.r.fijar_volumen(int(val * 100)),
                                                  self.ctx.ajustes.guardar()))
        fila.addWidget(self.volumen)
        fila.addStretch(1)
        self.bt_audio = QPushButton("  Solo audio")
        self.bt_audio.setObjectName("contorno")
        self.bt_audio.setIcon(iconos.icono("musica", 15, C["texto"]))
        self.bt_audio.setToolTip("Seguir escuchando sin la imagen (en segundo plano)")
        self.bt_audio.setCursor(Qt.PointingHandCursor)
        self.bt_audio.clicked.connect(self._solo_audio)
        fila.addWidget(self.bt_audio)
        fila.addSpacing(6)
        self.bt_capitulos = BotonIcono("lista", 18, "Capítulos", 34)
        self.bt_capitulos.clicked.connect(self._menu_capitulos)
        self.bt_subs = BotonIcono("subtitulos", 19, "Subtítulos", 34)
        self.bt_subs.clicked.connect(self._menu_subtitulos)
        self.bt_vel = BotonIcono("velocidad", 19, "Velocidad", 34)
        self.bt_vel.clicked.connect(self._menu_velocidad)
        self.bt_calidad = BotonIcono("engranaje", 19, "Calidad", 34)
        self.bt_calidad.clicked.connect(self._menu_calidad)
        self.bt_mini = BotonIcono("mini", 19, "Mini reproductor  (I)", 34)
        self.bt_mini.clicked.connect(self.pidio_mini.emit)
        self.bt_completa = BotonIcono("pantalla_completa", 19, "Pantalla completa  (F)", 34)
        self.bt_completa.clicked.connect(self.pidio_completa.emit)
        for w in (self.bt_capitulos, self.bt_subs, self.bt_vel, self.bt_calidad, self.bt_mini,
                  self.bt_completa):
            fila.addWidget(w)
        vc.addLayout(fila)
        v.addWidget(self.controles)

        self.r.pista_cambio.connect(self._pista)
        self.r.estado_cambio.connect(lambda e: (self.bt_play.set_sonando(e == "sonando"),
                                                self.bt_play.set_cargando(e == "cargando")))
        self.r.posicion_cambio.connect(self._posicion)
        self.r.duracion_cambio.connect(self._duracion)
        self.r.calidad_cambio.connect(self._calidad)
        self.r.video_listo.connect(self._video_listo)
        self._pista(self.r.actual)

        # vigilancia de cuadros perdidos y de la pantalla completa
        self.reloj = QTimer(self)
        self.reloj.setInterval(2000)
        self.reloj.timeout.connect(self._vigilar)
        self.reloj.start()
        self._ultimo_raton = QCursor.pos()
        self._quieto = 0
        self.reloj_raton = QTimer(self)
        self.reloj_raton.setInterval(250)
        self.reloj_raton.timeout.connect(self._raton)

    # ------------------------------------------------------------ motor

    def asegurar_motor(self):
        if self.motor is None and self.r.disponible:
            self.motor = self.r.registrar_video("principal", int(self.pantalla.winId()))
        return self.motor

    def showEvent(self, e):
        super().showEvent(e)
        self.asegurar_motor()
        if self._pendiente is not None:
            datos, self._pendiente = self._pendiente, None
            QTimer.singleShot(0, lambda: self.r.arrancar_video_pendiente(datos))

    def _video_listo(self, datos):
        if self.r.destino_video != "principal":
            return
        if self.motor is None:
            # la vista aun no se ha mostrado: se arranca al mostrarla
            self._pendiente = datos
            if self.isVisible():
                self.asegurar_motor()
                pend, self._pendiente = self._pendiente, None
                QTimer.singleShot(0, lambda: self.r.arrancar_video_pendiente(pend))

    # ------------------------------------------------------------ pintado

    def _pista(self, p):
        if not p:
            self.et_titulo.setText("")
            self.et_autor.setText("")
            return
        self.et_titulo.setText(p.get("titulo") or "")
        self.et_autor.setText(p.get("artista") or "")
        self.titulo = p.get("titulo") or "Video"
        self._caidos_previos = None
        self._avisos_tirones = 0
        self.r._calidad_forzada = None

    def _posicion(self, pos):
        if self._arrastrando:
            return
        self.et_actual.setText(formato_tiempo(pos) or "0:00")
        if self._dur > 0:
            self.barra.set_valor(pos / self._dur)

    def _duracion(self, d):
        self._dur = float(d or 0)
        self.et_total.setText(formato_tiempo(self._dur) or "0:00")
        self._marcas()

    def _calidad(self, info):
        self._info = info or {}
        alto = info.get("alto")
        if info.get("local"):
            self.et_calidad.setText("EN EL DISCO")
        elif alto:
            fps = int(info.get("fps") or 0)
            nombre = {4320: "8K", 2160: "4K", 1440: "2K"}.get(int(alto), f"{alto}p")
            self.et_calidad.setText(f"{nombre}{fps if fps > 30 else ''}"
                                    + (" HDR" if info.get("hdr") else ""))
        else:
            self.et_calidad.setText("")
        self.et_calidad.setVisible(bool(self.et_calidad.text()))
        self.bt_subs.setEnabled(bool(info.get("subtitulos")))
        self.bt_capitulos.setEnabled(bool(info.get("capitulos")))
        self.bt_calidad.setEnabled(bool(info.get("alturas")))
        self._marcas()

    def _marcas(self):
        caps = self._info.get("capitulos") or []
        if self._dur > 0 and caps:
            self.barra.set_marcas([c[0] / self._dur for c in caps])
        else:
            self.barra.set_marcas([])

    def _moviendo(self, val):
        self._arrastrando = True
        self.et_actual.setText(formato_tiempo(val * self._dur) or "0:00")

    def _soltar(self, val):
        self._arrastrando = False
        if self._dur > 0:
            self.r.buscar(val * self._dur)

    # ------------------------------------------------------------ menus

    def _menu_calidad(self):
        menu = QMenu(self)
        actual = str(self.ctx.ajustes["calidad_video"])
        alto_real = self._info.get("alto")
        nombres = {4320: "8K · 4320p", 2160: "4K · 2160p", 1440: "2K · 1440p",
                   1080: "Full HD · 1080p", 720: "HD · 720p"}
        a = menu.addAction("Máxima disponible", lambda: self.r.cambiar_calidad_video("maxima"))
        a.setCheckable(True)
        a.setChecked(actual == "maxima")
        menu.addSeparator()
        for h in self._info.get("alturas") or []:
            etiqueta = nombres.get(h, f"{h}p")
            if h == alto_real:
                etiqueta += "   (ahora)"
            ac = menu.addAction(etiqueta, lambda h=h: self.r.cambiar_calidad_video(str(h)))
            ac.setCheckable(True)
            ac.setChecked(actual == str(h))
        menu.addSeparator()
        codec = self.ctx.ajustes["codec_video"]
        sub = menu.addMenu("Códec")
        for clave, texto in (("auto", "La mejor imagen (AV1/VP9)"),
                             ("sin_av1", "Evitar AV1 (más ligero)"),
                             ("compatible", "Solo H.264 (el más ligero)")):
            ac = sub.addAction(texto, lambda c=clave: self._codec(c))
            ac.setCheckable(True)
            ac.setChecked(codec == clave)
        info = self.motor.info_video() if self.motor else {}
        if info.get("ancho"):
            menu.addSeparator()
            d = menu.addAction(f"Se ve a {info['ancho']}×{info['alto']} · "
                               f"{'aceleración ' + info['hwdec'] if info.get('hwdec') not in ('no', None) else 'sin aceleración'}"
                               f" · {info.get('caidos', 0)} cuadros perdidos")
            d.setEnabled(False)
        menu.exec(self.bt_calidad.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6)))

    def _codec(self, c):
        self.ctx.ajustes["codec_video"] = c
        self.ctx.ajustes.guardar()
        self.r.cambiar_calidad_video(self.ctx.ajustes["calidad_video"])

    def _menu_subtitulos(self):
        menu = QMenu(self)
        subs = self._info.get("subtitulos") or {}
        menu.addAction("Desactivados", lambda: self.motor and self.motor.poner_subtitulo(""))
        if subs:
            menu.addSeparator()
        orden = sorted(subs.items(), key=lambda kv: ("automáticos" in kv[0],
                                                     not kv[0].lower().startswith(("es", "spa")),
                                                     kv[0]))
        for nombre, url in orden:
            menu.addAction(nombre, lambda u=url: self.motor and self.motor.poner_subtitulo(u))
        menu.exec(self.bt_subs.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6)))

    def _menu_velocidad(self):
        menu = QMenu(self)
        for v in VELOCIDADES:
            a = menu.addAction("Normal" if v == 1.0 else f"{v:g}×",
                               lambda v=v: self.r.fijar_velocidad(v))
            a.setCheckable(True)
            a.setChecked(abs(self.r.velocidad - v) < 0.01)
        menu.exec(self.bt_vel.mapToGlobal(QPoint(0, -menu.sizeHint().height() - 6)))

    def _menu_capitulos(self):
        menu = QMenu(self)
        for ini, titulo in self._info.get("capitulos") or []:
            menu.addAction(f"{formato_tiempo(ini) or '0:00'}   {titulo}",
                           lambda s=ini: self.r.buscar(s))
        menu.exec(self.bt_capitulos.mapToGlobal(QPoint(0, -min(menu.sizeHint().height(), 500) - 6)))

    def _solo_audio(self):
        self.r.cambiar_modo("audio")
        self.volver.emit()
        self.ctx.aviso.emit("Sigue sonando sin la imagen")

    # ------------------------------------------------------------ vigilancia

    def _vigilar(self):
        if (self.r.modo != "video" or self.r.estado != "sonando" or self.motor is None
                or self.r.destino_video != "principal"):
            self._caidos_previos = None
            return
        info = self.motor.info_video()
        caidos = info.get("caidos") or 0
        fps = info.get("fps") or 30
        if self._caidos_previos is None:
            self._caidos_previos = caidos
            return
        nuevos = caidos - self._caidos_previos
        self._caidos_previos = caidos
        if nuevos > fps * 2 * 0.2:          # mas de un 20 % de cuadros perdidos
            self._avisos_tirones += 1
        else:
            self._avisos_tirones = max(0, self._avisos_tirones - 1)
        if self._avisos_tirones >= 2 and self.ctx.ajustes["calidad_adaptable"]:
            self._avisos_tirones = 0
            alturas = [h for h in (self._info.get("alturas") or []) if h < (self._info.get("alto") or 0)]
            if alturas:
                nueva = max(alturas)
                self.r._calidad_forzada = str(nueva)
                self.r.cambiar_calidad_video(str(nueva), guardar=False)
                self.ctx.aviso.emit(f"Tu equipo no daba abasto: bajé a {nueva}p para que vaya "
                                    "fluido. Cámbialo en ⚙.")

    # ------------------------------------------------------------ pantalla completa

    def modo_completa(self, activo):
        self.en_completa = activo
        self.cab.setVisible(not activo)
        self.bt_completa.set_icono("salir_pantalla" if activo else "pantalla_completa")
        self.bt_completa.setToolTip("Salir de pantalla completa  (Esc)" if activo
                                    else "Pantalla completa  (F)")
        if activo:
            self._quieto = 0
            self.reloj_raton.start()
        else:
            self.reloj_raton.stop()
            self.controles.show()
            self.setCursor(Qt.ArrowCursor)

    def _raton(self):
        pos = QCursor.pos()
        if pos != self._ultimo_raton:
            self._ultimo_raton = pos
            self._quieto = 0
            if not self.controles.isVisible():
                self.controles.show()
        else:
            self._quieto += 1
            sobre_controles = self.controles.isVisible() and self.controles.rect().contains(
                self.controles.mapFromGlobal(pos))
            if self._quieto >= 10 and not sobre_controles and self.r.estado == "sonando":
                self.controles.hide()


class MiniReproductor(QWidget):
    """Ventanita flotante: el video (o la portada) con lo justo para controlar."""

    expandir = Signal()
    cerrado = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre, Qt.Window | Qt.FramelessWindowHint | Qt.Tool)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.setWindowTitle("Caudal · mini")
        self.setStyleSheet(f"background:{C['panel']};")
        self.resize(400, 286)
        self.setMinimumSize(280, 220)
        self.motor = None
        self._arrastre = None
        self._dur = 0.0
        self._aplicar_encima()

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        from PySide6.QtWidgets import QStackedWidget
        self.pila = QStackedWidget()
        self.pantalla = PantallaNativa()
        self.pila.addWidget(self.pantalla)
        self.portada = _PortadaMini()
        self.pila.addWidget(self.portada)
        v.addWidget(self.pila, 1)

        barra = QWidget()
        barra.setFixedHeight(66)
        vb = QVBoxLayout(barra)
        vb.setContentsMargins(10, 2, 8, 6)
        vb.setSpacing(0)
        self.progreso = Deslizador(12)
        self.progreso.soltado.connect(lambda val: self._dur and self.r.buscar(val * self._dur))
        vb.addWidget(self.progreso)
        h = QHBoxLayout()
        h.setSpacing(2)
        self.et = QLabel("")
        self.et.setStyleSheet("font-size:12.5px;font-weight:600;")
        h.addWidget(self.et, 1)
        b_ant = BotonIcono("anterior", 16, "Anterior", 30)
        b_ant.clicked.connect(self.r.anterior)
        self.bt_play = BotonPlay(32, claro=True)
        self.bt_play.clicked.connect(self.r.alternar)
        b_sig = BotonIcono("siguiente", 16, "Siguiente", 30)
        b_sig.clicked.connect(self.r.siguiente)
        b_exp = BotonIcono("abrir", 16, "Volver a la ventana grande", 30)
        b_exp.clicked.connect(self.expandir.emit)
        b_cerrar = BotonIcono("cerrar", 15, "Cerrar el mini reproductor", 30)
        b_cerrar.clicked.connect(self.close)
        for w in (b_ant, self.bt_play, b_sig, b_exp, b_cerrar):
            h.addWidget(w)
        vb.addLayout(h)
        v.addWidget(barra)
        agarre = QSizeGrip(self)
        agarre.setFixedSize(14, 14)
        self._agarre = agarre

        self.r.pista_cambio.connect(self._pista)
        self.r.estado_cambio.connect(lambda e: (self.bt_play.set_sonando(e == "sonando"),
                                                self.bt_play.set_cargando(e == "cargando")))
        self.r.posicion_cambio.connect(self._pos)
        self.r.duracion_cambio.connect(lambda d: setattr(self, "_dur", float(d or 0)))
        self.r.modo_cambio.connect(self._modo)
        self.r.video_listo.connect(self._video_listo)
        self._pista(self.r.actual)

    def _aplicar_encima(self):
        flags = Qt.Window | Qt.FramelessWindowHint | Qt.Tool
        if self.ctx.ajustes["mini_encima"]:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._agarre.move(self.width() - 14, self.height() - 14)

    def abrir(self):
        self._aplicar_encima()
        pantalla = self.screen().availableGeometry() if self.screen() else None
        if pantalla is not None and not self.isVisible():
            self.move(pantalla.right() - self.width() - 24, pantalla.bottom() - self.height() - 24)
        self.show()
        self.raise_()
        if self.motor is None and self.r.disponible:
            self.motor = self.r.registrar_video("mini", int(self.pantalla.winId()))
        self._modo(self.r.modo)
        if self.r.modo == "video":
            self.r.mover_video("mini")

    def closeEvent(self, e):
        if (not getattr(self, "_cerrando", False) and self.r.modo == "video"
                and self.r.destino_video == "mini"):
            # la ventanita sigue visible (y el video en ella) hasta que la grande
            # tiene la imagen en el mismo punto: asi no hay corte
            e.ignore()
            self._cerrando = True
            self.r.mover_video("principal")
            self._esperas = 0
            self._esperar_traspaso()
            return
        self._cerrando = False
        self.cerrado.emit()
        super().closeEvent(e)

    def _esperar_traspaso(self):
        self._esperas += 1
        if self.r._traspaso is None or self._esperas > 120:
            self.close()
            return
        QTimer.singleShot(50, self._esperar_traspaso)

    def _video_listo(self, _datos):
        pass

    def _modo(self, modo):
        self.pila.setCurrentIndex(0 if modo == "video" else 1)

    def _pista(self, p):
        if not p:
            self.et.setText("")
            self.portada.poner("")
            return
        fm = QFontMetrics(self.et.font())
        self.et.setText(fm.elidedText(f"{p.get('titulo', '')} · {p.get('artista', '')}",
                                      Qt.ElideRight, max(80, self.width() - 190)))
        self.portada.poner(p.get("miniatura") or "")

    def _pos(self, pos):
        if self._dur > 0:
            self.progreso.set_valor(pos / self._dur)

    # arrastrar la ventana desde cualquier parte
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._arrastre is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._arrastre)

    def mouseReleaseEvent(self, e):
        self._arrastre = None

    def mouseDoubleClickEvent(self, e):
        self.expandir.emit()


class _PortadaMini(QWidget):
    def __init__(self, padre=None):
        super().__init__(padre)
        self.img = None
        self.url = ""

    def poner(self, url):
        self.url = url
        self.img = None
        if url:
            imagenes.imagen(url, self._llego)
        self.update()

    def _llego(self, img):
        try:
            self.img = img
            self.update()
        except RuntimeError:
            pass

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        color = imagenes.color_dominante(self.img) if self.img is not None else QColor(C["superficie2"])
        p.fillRect(self.rect(), color)
        if self.img is not None and not self.img.isNull():
            lado = min(self.width(), self.height()) - 24
            esc = self.img.scaled(lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (self.width() - lado) // 2
            y = (self.height() - lado) // 2
            p.drawImage(QRectF(x, y, lado, lado), esc,
                        QRectF((esc.width() - lado) / 2, (esc.height() - lado) / 2, lado, lado))
        else:
            p.drawPixmap(self.width() // 2 - 24, self.height() // 2 - 24,
                         iconos.pixmap("musica", 48, C["texto3"]))


def _sin_usar():  # pragma: no cover
    return QFont, fuente, Portada
