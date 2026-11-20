# -*- coding: utf-8 -*-
"""Base de los escenarios animados de la escena de escritorio (cyberpunk, samurái, gótico…).

Cada escenario solo dibuja dos cosas:

* `pintar_estatico(p, w, h)`: lo que no se mueve (cielo, degradados, siluetas). Se pinta UNA vez en un
  QPixmap al cambiar de tamaño o de acento y luego se copia en cada cuadro: barato.
* `pintar_animado(p, w, h, t)`: lo que se mueve, cada cuadro (30 FPS). `t` = segundos desde que se creó.

La base pone el reloj (solo corre con el escenario a la vista), el espectro del audio ya suavizado
(`self.bandas`, 0..1, ataque rápido y caída lenta), el color de acento con transición (`self.acento()`),
y ayudas para que todo se vea fino: `ondas()` (frecuencias como curvas suaves, nunca barras toscas),
`brillo()` (resplandor radial) y `velo()` (degradado vertical).
"""
import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

FPS = 30
N_BANDAS = 32
ATAQUE, CAIDA = 0.45, 0.08
TRANSICION_ACENTO = 0.8     # s


def mezclar(a, b, f):
    """Color entre `a` y `b` (f de 0 a 1)."""
    f = max(0.0, min(1.0, f))
    return QColor(round(a.red() + (b.red() - a.red()) * f), round(a.green() + (b.green() - a.green()) * f),
                  round(a.blue() + (b.blue() - a.blue()) * f), round(a.alpha() + (b.alpha() - a.alpha()) * f))


def con_alfa(color, alfa):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alfa))))
    return c


class EscenarioBase(QWidget):
    NOMBRE = "Escenario"
    ACENTO = "#FF4FD8"          # color propio del escenario (la carátula puede teñirlo)
    SEMILLA = 7

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self._t0 = time.monotonic()
        self._ahora = self._t0
        self.rnd = random.Random(self.SEMILLA)
        self.bandas = [0.0] * N_BANDAS
        self._objetivo = [0.0] * N_BANDAS
        self._acento_de = QColor(self.ACENTO)
        self._acento_a = QColor(self.ACENTO)
        self._acento_t = -10.0
        self._cache = None
        self._cache_clave = None
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / FPS))
        self._timer.timeout.connect(self._cuadro)
        self.preparar()

    # ------------------------------------------------------------ para los escenarios

    def preparar(self):
        """Se llama una vez al crear: generar partículas, estrellas… con `self.rnd` (repetible)."""

    def pintar_estatico(self, p, w, h):
        p.fillRect(0, 0, w, h, QColor("#000000"))

    def pintar_animado(self, p, w, h, t):
        """Cada cuadro, encima de lo estático."""

    # ------------------------------------------------------------ API pública

    def fijar_espectro(self, valores):
        """Valores 0..1 de cualquier longitud (vacío = en reposo: una respiración suave)."""
        v = [max(0.0, min(1.0, float(x))) for x in (valores or []) if x == x]
        if not v:
            self._objetivo = [0.0] * N_BANDAS
            return
        n = len(v)
        self._objetivo = [v[min(n - 1, int(i * n / N_BANDAS))] for i in range(N_BANDAS)]

    def poner_acento(self, color):
        c = QColor(color)
        if not c.isValid() or c == self._acento_a:
            return
        self._acento_de = self.acento()
        self._acento_a = c
        self._acento_t = time.monotonic()

    def acento(self):
        f = (time.monotonic() - self._acento_t) / TRANSICION_ACENTO
        return QColor(self._acento_a) if f >= 1 else mezclar(self._acento_de, self._acento_a, f)

    def energia(self):
        """Nivel general 0..1 (media de las bandas)."""
        return sum(self.bandas) / len(self.bandas)

    # ------------------------------------------------------------ ayudas de dibujo

    def ondas(self, p, base_y, ancho, alto_max, color, x0=0.0, espejo=True, reflejo=True, grosor=1.5):
        """Las frecuencias como una línea de ondas suave (curvas, simétrica si `espejo`), con relleno que se
        desvanece hacia abajo y, si `reflejo`, su reflejo tenue debajo de `base_y`."""
        vals = list(self.bandas)
        if espejo:
            vals = vals[::-1] + vals
        t = self._ahora - self._t0
        n = len(vals)
        pts = []
        for i, v in enumerate(vals):
            x = x0 + ancho * i / (n - 1)
            reposo = 0.04 + 0.025 * math.sin(t * 1.3 + i * 0.45)
            borde = math.sin(math.pi * i / (n - 1)) ** 0.6       # baja hacia los extremos
            pts.append(QPointF(x, base_y - alto_max * max(reposo, v) * borde))
        camino = QPainterPath(QPointF(x0, base_y))
        camino.lineTo(pts[0])
        for a, b in zip(pts, pts[1:]):
            medio = (a.x() + b.x()) / 2
            camino.cubicTo(QPointF(medio, a.y()), QPointF(medio, b.y()), b)
        camino.lineTo(QPointF(x0 + ancho, base_y))
        g = QLinearGradient(0, base_y - alto_max, 0, base_y)
        g.setColorAt(0, con_alfa(color, 110))
        g.setColorAt(1, con_alfa(color, 0))
        p.save()                     # sin heredar pincel ni pluma de quien llama
        p.setBrush(Qt.NoBrush)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillPath(camino, g)
        linea = QPainterPath(pts[0])
        for a, b in zip(pts, pts[1:]):
            medio = (a.x() + b.x()) / 2
            linea.cubicTo(QPointF(medio, a.y()), QPointF(medio, b.y()), b)
        p.setPen(QPen(con_alfa(color, 70), grosor * 4, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(linea)
        p.setPen(QPen(con_alfa(mezclar(color, QColor("white"), 0.55), 230), grosor, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(linea)
        if reflejo:
            p.save()
            p.translate(0, 2 * base_y)
            p.scale(1, -1)
            p.setOpacity(0.22)
            p.fillPath(camino, g)
            p.restore()
        p.restore()

    def brillo(self, p, cx, cy, radio, color, alfa=160):
        g = QRadialGradient(QPointF(cx, cy), max(1.0, radio))
        g.setColorAt(0, con_alfa(color, alfa))
        g.setColorAt(1, con_alfa(color, 0))
        p.fillRect(QRectF(cx - radio, cy - radio, 2 * radio, 2 * radio), g)

    def velo(self, p, rect, arriba, abajo):
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        g.setColorAt(0, QColor(arriba))
        g.setColorAt(1, QColor(abajo))
        p.fillRect(rect, g)

    # ------------------------------------------------------------ reloj y pintado

    def _cuadro(self):
        self._ahora = time.monotonic()
        for i in range(N_BANDAS):
            o, v = self._objetivo[i], self.bandas[i]
            self.bandas[i] = v + (o - v) * (ATAQUE if o > v else CAIDA)
        self.update()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._timer.start()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._timer.stop()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._cache = None

    def paintEvent(self, _ev):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        acento = self.acento()
        clave = (w, h, acento.rgba() if time.monotonic() - self._acento_t > TRANSICION_ACENTO else None)
        if self._cache is None or self._cache_clave != clave:
            pm = QPixmap(w, h)
            pc = QPainter(pm)
            try:
                pc.setRenderHint(QPainter.Antialiasing, True)
                self.pintar_estatico(pc, w, h)
            finally:
                pc.end()
            self._cache, self._cache_clave = pm, clave
        p = QPainter(self)
        try:
            p.drawPixmap(0, 0, self._cache)
            p.setRenderHint(QPainter.Antialiasing, True)
            self.pintar_animado(p, w, h, self._ahora - self._t0)
        finally:
            p.end()
