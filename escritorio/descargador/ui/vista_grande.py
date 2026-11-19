# -*- coding: utf-8 -*-
"""Base de las vistas grandes para donadores (visualizador y karaoke): lo que tienen en común.

- una cabecera con «Pantalla completa» y «Cerrar (Esc)» (más lo que añada cada vista) y un pie con la canción
  y los controles; los dos se esconden solos a los pocos segundos sin mover el ratón (y el cursor con ellos);
- si la cuenta deja de ser de donador (se acabó la prueba), la vista se cierra sola;
- ayudas para gastar poco: `ahorrando()` (modo gamer en ahorro) y `a_la_vista` (minimizada u oculta).
"""

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .componentes import BotonIcono, BotonPlay

BOTON = ("QPushButton{border:none;border-radius:14px;padding:6px 14px;font-size:13px;"
         "font-weight:800;color:#FFFFFF;background:rgba(255,255,255,0.16);}"
         "QPushButton:hover{background:rgba(255,255,255,0.26);}"
         "QPushButton:checked{background:#FFFFFF;color:#06070A;}")
MS_ESCONDER = 3500
ALTO_CABECERA = 64
ALTO_PIE = 112


def ahorrando(ctx):
    """True si el modo gamer está en ahorro (hay un juego a pantalla completa): no hay que animar nada."""
    g = getattr(ctx, "gamer", None)
    return bool(g is not None and getattr(g, "ahorrando", False))


def es_donador(ctx):
    g = getattr(ctx, "premium", None)
    return bool(g is not None and g.premium)


class _Elidida(QLabel):
    def __init__(self, estilo, padre=None):
        super().__init__("", padre)
        self._texto = ""
        self.setStyleSheet(estilo)
        self.setMinimumWidth(10)

    def poner(self, texto):
        self._texto = texto or ""
        self._repintar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._repintar()

    def _repintar(self):
        self.setText(self.fontMetrics().elidedText(self._texto, Qt.ElideRight, max(20, self.width() - 4)))


class VistaGrande(QWidget):
    """Una pantalla grande con controles que se esconden. Las vistas la heredan y pintan su fondo."""

    volver = Signal()
    titulo = "Vista"

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoFillBackground(False)
        self._controles_a_la_vista = True

        # ---- cabecera
        self.cabecera = QWidget(self)
        self.cabecera.setAttribute(Qt.WA_TranslucentBackground)
        self.fila_cab = QHBoxLayout(self.cabecera)
        self.fila_cab.setContentsMargins(24, 16, 22, 0)
        self.fila_cab.setSpacing(10)
        self.fila_cab.addStretch(1)
        self.bt_completa = QPushButton("Pantalla completa")
        self.bt_completa.setToolTip("Ocupar toda la pantalla (Esc para salir)")
        self.bt_completa.clicked.connect(self.alternar_pantalla_completa)
        self.bt_cerrar = QPushButton("Cerrar  (Esc)")
        self.bt_cerrar.clicked.connect(self.volver.emit)
        for b in (self.bt_completa, self.bt_cerrar):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(BOTON)
            b.setFocusPolicy(Qt.NoFocus)
            self.fila_cab.addWidget(b, 0, Qt.AlignVCenter)

        # ---- pie: lo que suena y los controles
        self.pie = QWidget(self)
        self.pie.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(self.pie)
        h.setContentsMargins(28, 0, 28, 18)
        h.setSpacing(16)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addStretch(1)
        self.et_titulo = _Elidida("color:#FFFFFF;font-size:20px;font-weight:800;background:transparent;")
        self.et_artista = _Elidida("color:rgba(255,255,255,0.72);font-size:14px;font-weight:600;"
                                   "background:transparent;")
        textos.addWidget(self.et_titulo)
        textos.addWidget(self.et_artista)
        h.addLayout(textos, 1)
        self.bt_anterior = BotonIcono("anterior", 22, "Anterior", 40, color="#E4E7EE", color_hover="#FFFFFF")
        self.bt_anterior.clicked.connect(self.r.anterior)
        self.bt_play = BotonPlay(52, claro=True)
        self.bt_play.setToolTip("Reproducir / pausar")
        self.bt_play.clicked.connect(self.r.alternar)
        self.bt_siguiente = BotonIcono("siguiente", 22, "Siguiente", 40, color="#E4E7EE", color_hover="#FFFFFF")
        self.bt_siguiente.clicked.connect(self.r.siguiente)
        for w in (self.bt_anterior, self.bt_play, self.bt_siguiente):
            h.addWidget(w, 0, Qt.AlignVCenter)
        h.addStretch(1)
        h.addSpacing(0)
        self.bt_play.set_sonando(self.suena())

        for w in (self.cabecera, self.pie):
            w.setMouseTracking(True)
            w.installEventFilter(self)
        self._t_esconder = QTimer(self)
        self._t_esconder.setSingleShot(True)             # (de un solo disparo: el modo gamer no lo toca)
        self._t_esconder.setInterval(MS_ESCONDER)
        self._t_esconder.timeout.connect(self._esconder)

        self.r.pista_cambio.connect(self._poner_textos)
        self.r.estado_cambio.connect(self._al_estado_base)
        g = getattr(ctx, "premium", None)
        if g is not None:
            g.cambiado.connect(self._vigilar_donador)
        self._poner_textos(self.r.actual)

    # ------------------------------------------------------------ estado
    def suena(self):
        return getattr(self.r, "estado", "") == "sonando"

    def _al_estado_base(self, estado):
        self.bt_play.set_sonando(estado == "sonando")

    def _poner_textos(self, p):
        p = p or {}
        self.et_titulo.poner(p.get("titulo") or "")
        artistas = ", ".join(a.get("nombre", "") for a in p.get("artistas") or [] if a.get("nombre"))
        self.et_artista.poner(artistas or p.get("artista") or "")

    def _vigilar_donador(self):
        if not es_donador(self.ctx) and self.isVisible():
            self.volver.emit()

    # ------------------------------------------------------------ controles que se esconden
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.cabecera.setGeometry(0, 0, self.width(), ALTO_CABECERA)
        self.pie.setGeometry(0, self.height() - ALTO_PIE, self.width(), ALTO_PIE)
        self.cabecera.raise_()
        self.pie.raise_()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.MouseMove, QEvent.Enter):
            self.mostrar_controles()
        return False

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self.mostrar_controles()

    def mostrar_controles(self):
        if not self._controles_a_la_vista:
            self._controles_a_la_vista = True
            self.cabecera.show()
            self.pie.show()
            self.unsetCursor()
        self._t_esconder.start()

    def _esconder(self):
        # con el ratón encima de los controles no se esconden
        if self.cabecera.underMouse() or self.pie.underMouse():
            self._t_esconder.start()
            return
        self._controles_a_la_vista = False
        self.cabecera.hide()
        self.pie.hide()
        self.setCursor(Qt.BlankCursor)

    def showEvent(self, e):
        super().showEvent(e)
        self._controles_a_la_vista = False
        self.mostrar_controles()
        self.setFocus()
        self._poner_textos(self.r.actual)
        self.bt_play.set_sonando(self.suena())

    def hideEvent(self, e):
        super().hideEvent(e)
        self._t_esconder.stop()
        self.unsetCursor()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.volver.emit()
            return
        if e.key() in (Qt.Key_F, Qt.Key_F11):
            self.alternar_pantalla_completa()
            return
        super().keyPressEvent(e)

    def alternar_pantalla_completa(self):
        v = getattr(self.ctx, "ventana", None)
        f = getattr(v, "alternar_completa", None)
        if f is not None:
            f()
