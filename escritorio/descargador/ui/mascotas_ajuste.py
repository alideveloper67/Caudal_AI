# -*- coding: utf-8 -*-
"""Ajustes › «Mascotita del reproductor»: elegir quién camina sobre la barra de progreso.

Arriba, una vista previa con la mascota elegida caminando; debajo, una rejilla compacta con todas.
Exclusiva de donadores y fundadores; para el resto se ve bloqueada con un mensaje amable."""

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from .. import mascotas as M
from .donar import boton_donar
from .estilos import C

COLUMNAS = 6


class VistaPrevia(QWidget):
    """Una barra de ejemplo por la que camina la mascota elegida (no depende de la música)."""

    def __init__(self, gestor, padre=None):
        super().__init__(padre)
        self.gestor = gestor
        self.setFixedHeight(84)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._pos = 0.0
        self._cuadro = 0
        self._fase = 0.0
        self._t = QTimer(self)
        self._t.setInterval(90)
        self._t.timeout.connect(self._paso)
        self._n = 0
        gestor.cambiada.connect(self.update)

    def showEvent(self, e):
        self._t.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._t.stop()
        super().hideEvent(e)

    def _paso(self):
        self._n += 1
        self._pos = (self._pos + 0.006) % 1.0
        if self._n % 2 == 0:
            self._cuadro = (self._cuadro + 1) % M.num_cuadros(self.gestor.datos())
            self._fase += 0.9
        if self.isVisible():
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        margen = 20
        ancho = self.width() - 2 * margen
        y = self.height() - 18
        p.setBrush(QColor(255, 255, 255, 46))
        p.drawRoundedRect(QRectF(margen, y - 2, ancho, 4), 2, 2)
        datos = M.por_clave(self.gestor.clave) if self.gestor.clave else None
        if datos is None:
            p.setPen(QColor(C["texto"]))
            p.drawText(self.rect().adjusted(0, 0, 0, -18), Qt.AlignCenter, "Elige una mascotita para verla caminar aquí")
            return
        x = margen + ancho * self._pos
        p.setBrush(QColor(C["texto"]))
        p.drawRoundedRect(QRectF(margen, y - 2, ancho * self._pos, 4), 2, 2)
        M.pintar(p, datos, x, y, margen, self.width(), self._cuadro, self._fase, 1)


class SeccionMascotas(QFrame):
    def __init__(self, gestor, padre=None):
        super().__init__(padre)
        self.gestor = gestor
        self.setObjectName("caja")
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(12)
        cab = QHBoxLayout()
        t = QLabel("Mascotita del reproductor")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.nombre = QLabel("")
        self.nombre.setObjectName("secundario")
        cab.addWidget(self.nombre)
        v.addLayout(cab)
        self.ayuda = QLabel("Un personajito tierno que camina por la barra de la canción mientras suena.")
        self.ayuda.setObjectName("secundario")
        self.ayuda.setWordWrap(True)
        v.addWidget(self.ayuda)
        self.aviso = QLabel("Exclusiva para donadores y fundadores de Caudal.")
        self.aviso.setObjectName("ayuda")
        self.aviso.setWordWrap(True)
        v.addWidget(self.aviso)
        self.bt_donar = boton_donar(texto="Donar aquí")
        v.addWidget(self.bt_donar, 0, Qt.AlignLeft)

        self.vista = VistaPrevia(gestor)
        v.addWidget(self.vista)

        self.rejilla = QGridLayout()
        self.rejilla.setSpacing(8)
        v.addLayout(self.rejilla)
        self.botones = {}
        self._poner("", "Ninguna", None, 0)
        for i, m in enumerate(M.catalogo_de(gestor.ctx), start=1):
            self._poner(m["clave"], m["nombre"], None, i, m.get("origen", ""))
        # los dibujos, de a pocos: leerlos todos seguidos paraba la ventana
        self._sin_dibujo = [m["clave"] for m in M.catalogo_de(gestor.ctx)]
        self._t_dibujos = QTimer(self)
        self._t_dibujos.setInterval(0)
        self._t_dibujos.timeout.connect(self._mas_dibujos)
        self._t_dibujos.start()
        for c in range(COLUMNAS):
            self.rejilla.setColumnStretch(c, 1)
        gestor.cambiada.connect(self.refrescar)
        self.refrescar()

    def _mas_dibujos(self):
        tanda, self._sin_dibujo = self._sin_dibujo[:1], self._sin_dibujo[1:]       # de uno en uno: cada dibujo se lee del disco
        for clave in tanda:
            cuadros = M.cuadros(clave)
            if cuadros and clave in self.botones:
                self.botones[clave].setIcon(QIcon(cuadros[0]))
        if not self._sin_dibujo:
            self._t_dibujos.stop()

    def _poner(self, clave, nombre, pm, i, origen=""):
        b = QToolButton()
        b.setCheckable(True)
        b.setAutoRaise(False)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        fm = b.fontMetrics()
        b.setText(fm.elidedText(nombre, Qt.ElideRight, 84))
        b.setToolTip(f"{nombre} · {origen}" if origen else nombre)
        b.setAccessibleName(nombre)
        b.setMinimumSize(88, 84)
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b.setIconSize(QSize(50, 46))
        if pm is not None:
            b.setIcon(QIcon(pm))
        b.setStyleSheet(
            f"QToolButton{{background:rgba(255,255,255,0.05);border:2px solid transparent;border-radius:12px;"
            f"color:{C['texto']};font-size:11px;padding:4px 2px;}}"
            f"QToolButton:hover{{background:rgba(255,255,255,0.10);}}"
            f"QToolButton:checked{{border:2px solid {C['acento']};background:rgba(255,255,255,0.12);}}"
            f"QToolButton:disabled{{color:{C['texto']};}}")
        b.clicked.connect(lambda _=False, c=clave: self._elegir(c))
        self.botones[clave] = b
        self.rejilla.addWidget(b, i // COLUMNAS, i % COLUMNAS)

    def _elegir(self, clave):
        self.gestor.elegir(clave)
        self.refrescar()

    def refrescar(self):
        puede = self.gestor.puede
        suyas = self.gestor.tiene_exclusivas
        self.aviso.setVisible(not puede)
        self.bt_donar.setVisible(not puede)
        self.aviso.setText("Las demás son para donadores y fundadores de Caudal; la tuya es solo tuya."
                           if suyas else "Exclusiva para donadores y fundadores de Caudal.")
        for clave, b in self.botones.items():
            b.setEnabled(self.gestor.puede_elegir(clave) if clave else (puede or suyas))
            b.setChecked(clave == self.gestor.clave)
        m = M.por_clave(self.gestor.clave) if self.gestor.clave else None
        self.nombre.setText(f"{m['nombre']} · {m['origen']}" if m else "")
