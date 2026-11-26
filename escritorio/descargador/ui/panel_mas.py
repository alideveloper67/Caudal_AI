# -*- coding: utf-8 -*-
"""El panel «Más» de la barra de reproducción: lo que se usa de vez en cuando, en fichas grandes y con su
nombre (antes eran trece iconos seguidos, sin texto, y había que adivinar cuál era cuál)."""

import time

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from . import iconos
from .componentes import BotonIcono, fuente
from .estilos import C

COLUMNAS = 3


class FichaMas(BotonIcono):
    """Icono arriba y su nombre debajo. Se comporta como BotonIcono (set_activo, set_icono, clicked)."""

    ANCHO, ALTO = 112, 84

    def __init__(self, icono, texto, ayuda="", cierra=True, padre=None):
        super().__init__(icono, 24, ayuda or texto, self.ANCHO, padre)
        self.setFixedSize(self.ANCHO, self.ALTO)
        self.texto = texto
        self.cierra = cierra                    # tocarla cierra el panel (las que abren un menú, no)
        self.setFocusPolicy(Qt.TabFocus)
        self.setAccessibleName(texto)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        marcada = self._encima or self.hasFocus() or self.isDown()
        fondo = QColor(C["acento"]) if self._activo else QColor(255, 255, 255)
        fondo.setAlpha((46 if marcada else 30) if self._activo else (34 if self.isDown() else 22 if marcada else 10))
        p.setBrush(fondo)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        color = C["texto3"] if not self.isEnabled() else C["acento"] if self._activo else C["texto"]
        p.drawPixmap((self.width() - self._tam) // 2, 14, iconos.pixmap(self._icono, self._tam, color))
        p.setFont(fuente(12.5, QFont.DemiBold))
        p.setPen(QColor(color if not self.isEnabled() or self._activo else C["texto2"]))
        p.drawText(QRect(4, 44, self.width() - 8, 36), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.texto)
        p.end()


class PanelMas(QFrame):
    """Ventanita que sale encima del botón «Más» (o a su derecha, en el menú lateral). Se cierra al tocar fuera,
    con Escape o al elegir."""

    def __init__(self, padre=None, titulo="Más controles", lado="arriba"):
        super().__init__(padre, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.fichas = []
        self._cerrado = 0.0
        self.lado = lado
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 16)
        v.setSpacing(12)
        t = QLabel(titulo)
        t.setStyleSheet(f"background:transparent;color:{C['texto']};font-size:15px;font-weight:800;")
        v.addWidget(t)
        self.rejilla = QGridLayout()
        self.rejilla.setSpacing(8)
        v.addLayout(self.rejilla)

    def agregar(self, ficha):
        n = len(self.fichas)
        self.fichas.append(ficha)
        self.rejilla.addWidget(ficha, n // COLUMNAS, n % COLUMNAS)
        if ficha.cierra:
            ficha.clicked.connect(self.hide)     # antes que lo suyo: lo que abre no queda debajo del panel
        return ficha

    def alternar(self, boton):
        if self.isVisible():
            self.hide()
            return
        if time.monotonic() - self._cerrado < 0.25:
            return                       # el mismo clic que lo cerró (tocar fuera) no lo vuelve a abrir
        self.adjustSize()
        esquina = boton.mapToGlobal(QPoint(boton.width() // 2, 0))
        x, y = esquina.x() - self.width() // 2, esquina.y() - self.height() - 10
        if self.lado == "derecha":
            esquina = boton.mapToGlobal(QPoint(boton.width(), 0))
            x, y = esquina.x() + 8, esquina.y() - 12
        pantalla = boton.screen()
        if pantalla is not None:
            a = pantalla.availableGeometry()
            x = max(a.left() + 8, min(x, a.right() - self.width() - 8))
            y = max(a.top() + 8, min(y, a.bottom() - self.height() - 8))
        self.move(x, y)
        self.show()

    def hideEvent(self, e):
        self._cerrado = time.monotonic()
        super().hideEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QColor(C["borde_claro"]))
        p.setBrush(QColor(C["superficie2"]))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 18, 18)
        p.end()
