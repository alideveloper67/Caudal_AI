# -*- coding: utf-8 -*-
"""Borde RGB neon del Modo gamer: un solo reloj ligero para todo lo que brilla.

Un unico QTimer (20 cuadros por segundo) mueve el tono; solo corre mientras haya algo
visible con el neon encendido, y se detiene solo en el ahorro al jugar o con el neon apagado.
"""

import weakref

from PySide6.QtCore import QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame

from .estilos import C

CUADRO_MS = 50
VUELTA_S = 6.0           # segundos por vuelta completa de colores


def color_neon(fase, desfase=0.0, s=0.85, v=1.0, alfa=255):
    c = QColor.fromHsvF((fase + desfase) % 1.0, s, v)
    c.setAlpha(alfa)
    return c


def _gradiente(centro, fase):
    g = QConicalGradient(centro, -fase * 360.0)
    for i in range(7):
        g.setColorAt(i / 6.0, color_neon(i / 6.0))
    return g


def dibujar_borde(p, rect, radio, fase, grosor=2.0, brillo=True):
    """Borde de colores que giran, con un resplandor suave por fuera."""
    rect = QRectF(rect)
    g = _gradiente(rect.center(), fase)
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(Qt.NoBrush)
    if brillo:
        for extra, alfa in ((6.0, 18), (3.5, 34)):
            p.setPen(QPen(_con_alfa(g, alfa), grosor + extra))
            p.drawRoundedRect(rect.adjusted(grosor, grosor, -grosor, -grosor), radio, radio)
    p.setPen(QPen(QBrush(g), grosor))
    p.drawRoundedRect(rect.adjusted(grosor / 2, grosor / 2, -grosor / 2, -grosor / 2), radio, radio)
    p.restore()


def _con_alfa(grad, alfa):
    g = QConicalGradient(grad.center(), grad.angle())
    for pos, col in grad.stops():
        c = QColor(col)
        c.setAlpha(alfa)
        g.setColorAt(pos, c)
    return QBrush(g)


class RelojNeon(QObject):
    """Mueve el tono y repinta los widgets registrados (solo los visibles)."""

    def __init__(self):
        super().__init__()
        self.fase = 0.0
        self.pausado = False
        self.encendido = True
        self._widgets = weakref.WeakSet()
        self._t = QTimer(self)
        self._t.setInterval(CUADRO_MS)
        self._t.timeout.connect(self._tic)

    def registrar(self, w):
        self._widgets.add(w)
        self.refrescar()

    def quitar(self, w):
        self._widgets.discard(w)
        self.refrescar()

    def pausar(self, si):
        self.pausado = bool(si)
        self.refrescar()

    def activar(self, si):
        self.encendido = bool(si)
        self.refrescar()

    def hay_trabajo(self):
        return self.encendido and not self.pausado and any(self._visible(w) for w in list(self._widgets))

    @staticmethod
    def _visible(w):
        try:
            return w.isVisible()
        except RuntimeError:
            return False

    def refrescar(self):
        """Arranca o detiene el reloj segun haya algo que animar."""
        if self.hay_trabajo():
            if not self._t.isActive():
                self._t.start()
        else:
            self._t.stop()
        for w in list(self._widgets):
            try:
                w.update()
            except RuntimeError:
                pass

    def _tic(self):
        self.fase = (self.fase + CUADRO_MS / 1000.0 / VUELTA_S) % 1.0
        vivos = 0
        for w in list(self._widgets):
            if self._visible(w):
                vivos += 1
                w.update()
        if not vivos:
            self._t.stop()

    @property
    def activo(self):
        return self._t.isActive()


_RELOJ = {}


def reloj_neon():
    if "r" not in _RELOJ:
        _RELOJ["r"] = RelojNeon()
    return _RELOJ["r"]


class _Neonable:
    """Mezcla: el widget se anota en el reloj al mostrarse y se quita al ocultarse."""

    neon_activo = True

    def _neon_on(self):
        return self.neon_activo and reloj_neon().encendido

    def showEvent(self, e):
        reloj_neon().registrar(self)
        super().showEvent(e)

    def hideEvent(self, e):
        super().hideEvent(e)
        reloj_neon().refrescar()


class MarcoNeon(_Neonable, QFrame):
    """Tarjeta con fondo de panel y borde RGB (o un borde sencillo si el neon esta apagado)."""

    def __init__(self, radio=18, grosor=2.0, padre=None):
        super().__init__(padre)
        self.radio = radio
        self.grosor = grosor
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie"]))
        p.drawRoundedRect(r, self.radio, self.radio)
        if self._neon_on():
            dibujar_borde(p, QRectF(self.rect()), self.radio, reloj_neon().fase, self.grosor)
        else:
            p.setPen(QPen(QColor(C["borde_claro"]), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, self.radio, self.radio)
