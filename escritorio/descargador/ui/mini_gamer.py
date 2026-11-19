# -*- coding: utf-8 -*-
"""Mini reproductor flotante del Modo gamer.

Una tarjeta sin bordes, siempre encima, semitransparente y que no le quita el foco al juego.
Se arrastra desde cualquier parte, recuerda su sitio y, si se pide, deja pasar los clics
(WS_EX_TRANSPARENT): entonces solo se maneja con los atajos. Muestra la caratula, el titulo,
reproducir/pausa, siguiente y el volumen.
"""

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

from .. import modo_gamer as MG
from . import iconos, imagenes
from .componentes import BotonIcono, BotonPlay, Deslizador
from .estilos import C
from .neon_gamer import _Neonable, dibujar_borde, reloj_neon

ANCHO, ALTO = 352, 100
LADO_CARATULA = 72


class _Caratula(QWidget):
    def __init__(self, padre=None):
        super().__init__(padre)
        self.setFixedSize(LADO_CARATULA, LADO_CARATULA)
        self.pm = None
        self.url = ""

    def poner(self, url):
        self.url = url or ""
        self.pm = None
        if self.url:
            esperado = self.url

            def listo(pm, esperado=esperado):
                try:
                    if self.url == esperado:
                        self.pm = pm
                        self.update()
                except RuntimeError:
                    pass
            self.pm = imagenes.pedir(self.url, LADO_CARATULA, LADO_CARATULA, "cuadrada", 12, listo)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self.pm is not None and not self.pm.isNull():
            p.drawPixmap(0, 0, self.pm)
            return
        g = QLinearGradient(0, 0, self.width(), self.height())
        g.setColorAt(0, QColor(C["superficie3"]))
        g.setColorAt(1, QColor(C["superficie2"]))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(self.rect()), 12, 12)
        p.drawPixmap((self.width() - 30) // 2, (self.height() - 30) // 2,
                     iconos.pixmap("musica", 30, C["texto3"]))


class MiniGamer(_Neonable, QWidget):
    def __init__(self, ctx, gestor, padre=None):
        flags = (Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                 | Qt.WindowDoesNotAcceptFocus)
        super().__init__(padre, flags)
        self.ctx = ctx
        self.g = gestor
        self.r = ctx.reproductor
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle("Caudal · modo gamer")
        self.setFixedSize(ANCHO, ALTO)
        self._arrastre = None
        self._pista = None

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(12)
        self.caratula = _Caratula()
        raiz.addWidget(self.caratula, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        cab = QHBoxLayout()
        cab.setContentsMargins(0, 0, 0, 0)
        self.et_titulo = QLabel("Nada sonando")
        self.et_titulo.setStyleSheet(f"background:transparent;color:{C['texto']};"
                                     "font-size:13.5px;font-weight:700;")
        cab.addWidget(self.et_titulo, 1)
        self.bt_cerrar = BotonIcono("cerrar", 13, "Ocultar (Ctrl+Alt+M)", 22)
        self.bt_cerrar.clicked.connect(lambda: self.g.mostrar_mini(False))
        cab.addWidget(self.bt_cerrar)
        col.addLayout(cab)
        self.et_artista = QLabel("")
        self.et_artista.setStyleSheet(f"background:transparent;color:{C['texto2']};font-size:11.5px;")
        col.addWidget(self.et_artista)
        col.addStretch(1)

        self.controles = QWidget()
        self.controles.setStyleSheet("background:transparent;")
        h = QHBoxLayout(self.controles)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        self.bt_play = BotonPlay(34, claro=True)
        self.bt_play.clicked.connect(self.r.alternar)
        h.addWidget(self.bt_play)
        self.bt_sig = BotonIcono("siguiente", 17, "Siguiente", 30)
        self.bt_sig.clicked.connect(self.r.siguiente)
        h.addWidget(self.bt_sig)
        h.addSpacing(6)
        self.ic_vol = QLabel()
        self.ic_vol.setStyleSheet("background:transparent;")
        h.addWidget(self.ic_vol)
        self.volumen = Deslizador(16, rueda=True)
        self.volumen.movido.connect(self._mover_volumen)
        self.volumen.soltado.connect(self._mover_volumen)
        h.addWidget(self.volumen, 1)
        col.addWidget(self.controles)
        # con los clics pasando, en vez de controles inutiles se dice como volver a tocarlo
        self.et_pasan = QLabel("")
        self.et_pasan.setStyleSheet(f"background:transparent;color:{C['texto3']};font-size:11px;")
        col.addWidget(self.et_pasan)
        raiz.addLayout(col, 1)

        self._t_pos = QTimer(self)
        self._t_pos.setSingleShot(True)
        self._t_pos.setInterval(400)
        self._t_pos.timeout.connect(self.guardar_posicion)

        self.r.estado_cambio.connect(self._estado)
        self._estado(self.r.estado)
        self.poner_pista(self.r.actual)
        self.sincronizar_volumen()
        self.setWindowOpacity(self.g.cfg["mini_opacidad"] / 100.0)
        self._modo_clics()

    # ------------------------------------------------------------ contenido

    def poner_pista(self, p):
        self._pista = p
        if not p:
            self.et_titulo.setText("Nada sonando")
            self.et_titulo.setToolTip("")
            self.et_artista.setText("")
            self.caratula.poner("")
            return
        ancho = ANCHO - 14 * 2 - LADO_CARATULA - 12 - 30
        fm = QFontMetrics(self.et_titulo.font())
        self.et_titulo.setText(fm.elidedText(p.get("titulo", ""), Qt.ElideRight, ancho))
        self.et_titulo.setToolTip(MG.texto_ahora_suena(p))
        fm2 = QFontMetrics(self.et_artista.font())
        self.et_artista.setText(fm2.elidedText(p.get("artista", ""), Qt.ElideRight, ancho + 24))
        self.caratula.poner(p.get("miniatura") or "")

    def _estado(self, e):
        self.bt_play.set_sonando(e == "sonando")
        self.bt_play.set_cargando(e == "cargando")

    def sincronizar_volumen(self):
        v = int(self.r.volumen)
        self.volumen.set_valor(v / 100.0)
        self.ic_vol.setPixmap(iconos.pixmap("altavoz_mute" if v == 0 else ("altavoz" if v < 50 else "altavoz_fuerte"),
                                            16, C["texto2"]))

    def _mover_volumen(self, v):
        self.r.fijar_volumen(int(round(v * 100)))
        self.sincronizar_volumen()

    # ------------------------------------------------------------ ventana

    def abrir(self):
        self.setWindowOpacity(self.g.cfg["mini_opacidad"] / 100.0)
        self._colocar()
        self.show()
        self.raise_()
        self._modo_clics()
        self.aplicar_clics()

    def _colocar(self):
        from PySide6.QtGui import QGuiApplication
        pos = self.g.cfg["mini_pos"]
        pantallas = QGuiApplication.screens()
        if pos:
            punto = QPoint(int(pos[0]), int(pos[1]))
            for s in pantallas:
                if s.availableGeometry().contains(punto + QPoint(20, 20)):
                    self.move(punto)
                    return
        s = QGuiApplication.primaryScreen()
        if s is not None:
            g = s.availableGeometry()
            self.move(g.right() - ANCHO - 24, g.bottom() - ALTO - 24)

    def guardar_posicion(self):
        self.g.cfg["mini_pos"] = [self.x(), self.y()]
        self.g.cfg.guardar()

    def poner_opacidad(self, pct):
        pct = max(35, min(100, int(pct)))
        self.g.cfg["mini_opacidad"] = pct
        self.setWindowOpacity(pct / 100.0)
        self.g.cfg.guardar()

    # ------------------------------------------------------------ dejar pasar los clics

    def _modo_clics(self):
        pasan = bool(self.g.cfg["mini_clics"])
        self.controles.setVisible(not pasan)
        self.bt_cerrar.setVisible(not pasan)
        self.et_pasan.setVisible(pasan)
        self.et_pasan.setText(f"Los clics pasan · {self.g.cfg['atajos'].get('clics', '')} para tocarla")
        self.setCursor(Qt.ArrowCursor if pasan else Qt.SizeAllCursor)

    def aplicar_clics(self):
        """WS_EX_TRANSPARENT sobre la ventana real: el raton la atraviesa y llega al juego."""
        pasan = bool(self.g.cfg["mini_clics"])
        self._modo_clics()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, pasan)
        if self.isVisible() or self.testAttribute(Qt.WA_WState_Created):
            MG.fijar_clics_pasan(int(self.winId()), pasan)

    # ------------------------------------------------------------ arrastrar y menu

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.RightButton:
            self._menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._arrastre is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._arrastre)

    def mouseReleaseEvent(self, e):
        self._arrastre = None

    def moveEvent(self, e):
        super().moveEvent(e)
        if self.isVisible():
            self._t_pos.start()

    def _menu(self, punto):
        m = QMenu(self)
        a = m.addAction("Dejar pasar los clics")
        a.setCheckable(True)
        a.setChecked(bool(self.g.cfg["mini_clics"]))
        a.triggered.connect(lambda si: self.g.fijar_clics(si))
        n = m.addAction("Borde RGB neón")
        n.setCheckable(True)
        n.setChecked(bool(self.g.cfg["neon"]))
        n.triggered.connect(lambda si: self.g.fijar_neon(si))
        m.addSeparator()
        m.addAction("Ocultar").triggered.connect(lambda: self.g.mostrar_mini(False))
        m.exec(punto)

    # ------------------------------------------------------------ pintura

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        fondo = QColor(C["panel"])
        fondo.setAlpha(238)
        p.setBrush(fondo)
        p.drawRoundedRect(r, 18, 18)
        if self.g.cfg["neon"] and reloj_neon().encendido:
            dibujar_borde(p, QRectF(self.rect()), 18, reloj_neon().fase, 2.0, brillo=not self.g.ahorrando)
        else:
            c = QColor(C["borde_claro"])
            p.setPen(c)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 18, 18)
