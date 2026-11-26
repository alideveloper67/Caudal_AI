# -*- coding: utf-8 -*-
"""Motor de los escenarios hechos con una ilustración: la imagen a pantalla completa (sin tocarla) y, encima,
efectos ligeros declarados por cada escenario con coordenadas de la propia imagen.

Qué da el motor:

* La ilustración solo se desplaza un poco siguiendo el ratón; si no, está quieta (lo que se mueve son los
  efectos de encima). Se pinta con un margen extra para que nunca se vean los bordes.
* Interacción: al mover el ratón sobre el fondo salen partículas propias del escenario; un clic suelta una ráfaga.
* Golpe de bajo (escenarios ÉPICOS): con cada golpe fuerte de graves (o un clic) la imagen da una sacudida corta
  y un destello.
* Imágenes que no son 16:9 (p. ej. cuadradas): la ilustración se ve entera, centrada, y los lados se rellenan con
  una copia desenfocada y oscurecida de la misma imagen.

Los efectos (lluvia, humo, partículas que caen o suben, agua, brillos, destellos, rayos, aura, nubes, mariposas,
murciélagos, flashes de cámaras, vehículos…) son clases pequeñas con `pintar(p, t, dt, e)`; todos sus sprites se
pintan una vez por tamaño de pantalla y luego solo se copian (barato a 30 FPS).
"""
import math
import os
import random

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QCursor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication

from .base import TRANSICION_ACENTO, EscenarioBase, con_alfa, mezclar

CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                       "escenarios_img")
MARGEN = 0.015            # margen para el desplazamiento con el ratón (y la sacudida de los épicos)
MAX_TRAZO = 70            # partículas de la interacción a la vez


# ilustraciones ya decodificadas en un hilo, esperando a su escenario (decodificar una cuesta 60 ms: un tirón)
_LISTAS = {}


def adelantar(nombre):
    """Decodifica la ilustración (se llama en un hilo: QImage(ruta) suelta el intérprete)."""
    img = QImage(os.path.join(CARPETA, nombre))
    _LISTAS.clear()                  # solo la última: las demás ya no se quieren
    _LISTAS[nombre] = img


def ilustracion(nombre):
    """La ilustración, ya decodificada si se adelantó; si no, se lee ahora."""
    img = _LISTAS.pop(nombre, None)
    return QImage(os.path.join(CARPETA, nombre)) if img is None or img.isNull() else img


# ---------------------------------------------------------------- sprites

def _halo(color, radio, dureza=0.5):
    radio = max(2, int(radio))
    pm = QPixmap(2 * radio, 2 * radio)
    pm.fill(Qt.transparent)
    pc = QPainter(pm)
    try:
        g = QRadialGradient(QPointF(radio, radio), radio)
        c = QColor(color)
        g.setColorAt(0, con_alfa(c, 255))
        g.setColorAt(dureza, con_alfa(c, 95))
        g.setColorAt(1, con_alfa(c, 0))
        pc.fillRect(QRectF(0, 0, 2 * radio, 2 * radio), QBrush(g))
    finally:
        pc.end()
    return pm


def _forma(tipo, color, lado):
    """Sprite de una partícula (lado en px): pétalo, hoja, corazón, estrella de 4 puntas, chispa, gota, flor."""
    lado = max(4, int(lado))
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    pc = QPainter(pm)
    try:
        pc.setRenderHint(QPainter.Antialiasing, True)
        pc.translate(lado / 2, lado / 2)
        pc.scale(lado, lado)
        c = QColor(color)
        pc.setPen(Qt.NoPen)
        if tipo == "petalo":
            g = QLinearGradient(0, -0.5, 0, 0.5)
            g.setColorAt(0, mezclar(c, QColor("white"), 0.45))
            g.setColorAt(1, c)
            pc.setBrush(QBrush(g))
            f = QPainterPath(QPointF(0, 0.45))
            f.cubicTo(QPointF(0.5, 0.2), QPointF(0.45, -0.4), QPointF(0.1, -0.48))
            f.cubicTo(QPointF(0.04, -0.3), QPointF(-0.04, -0.3), QPointF(-0.1, -0.48))
            f.cubicTo(QPointF(-0.45, -0.4), QPointF(-0.5, 0.2), QPointF(0, 0.45))
            pc.drawPath(f)
        elif tipo == "hoja":
            pc.setBrush(c)
            f = QPainterPath(QPointF(0, -0.48))
            f.quadTo(QPointF(0.42, 0), QPointF(0, 0.48))
            f.quadTo(QPointF(-0.42, 0), QPointF(0, -0.48))
            pc.drawPath(f)
            pc.setPen(QPen(mezclar(c, QColor("black"), 0.35), 0.05))
            pc.drawLine(QPointF(0, -0.42), QPointF(0, 0.42))
        elif tipo == "corazon":
            pc.setBrush(c)
            f = QPainterPath(QPointF(0, 0.42))
            f.cubicTo(QPointF(-0.6, 0.0), QPointF(-0.35, -0.55), QPointF(0, -0.18))
            f.cubicTo(QPointF(0.35, -0.55), QPointF(0.6, 0.0), QPointF(0, 0.42))
            pc.drawPath(f)
            pc.setBrush(QColor(255, 255, 255, 150))
            pc.drawEllipse(QPointF(-0.18, -0.12), 0.08, 0.06)
        elif tipo == "estrella":
            g = QRadialGradient(QPointF(0, 0), 0.5)
            g.setColorAt(0, QColor(255, 255, 255, 255))
            g.setColorAt(0.25, con_alfa(c, 200))
            g.setColorAt(1, con_alfa(c, 0))
            pc.setBrush(QBrush(g))
            pc.drawEllipse(QPointF(0, 0), 0.5, 0.5)
            pc.setBrush(QColor(255, 255, 255, 235))
            f = QPainterPath(QPointF(0, -0.5))
            for a, b in ((0.07, 0.07), (0.5, 0.0), (0.07, -0.07), (0.0, 0.5), (-0.07, -0.07), (-0.5, 0.0),
                         (-0.07, 0.07), (0.0, -0.5)):
                f.lineTo(QPointF(a, -b) if (a, b) != (0.0, -0.5) else QPointF(0, -0.5))
            pc.drawPath(f)
        elif tipo == "gota":
            g = QLinearGradient(0, -0.5, 0, 0.5)
            g.setColorAt(0, con_alfa(c, 60))
            g.setColorAt(1, con_alfa(c, 230))
            pc.setBrush(QBrush(g))
            f = QPainterPath(QPointF(0, -0.5))
            f.quadTo(QPointF(0.22, 0.15), QPointF(0, 0.45))
            f.quadTo(QPointF(-0.22, 0.15), QPointF(0, -0.5))
            pc.drawPath(f)
        elif tipo == "flor":
            pc.setBrush(c)
            for k in range(5):
                pc.drawEllipse(QPointF(0, -0.24), 0.16, 0.24)
                pc.rotate(72)
            pc.setBrush(QColor("#FFE08A"))
            pc.drawEllipse(QPointF(0, 0), 0.12, 0.12)
        else:                                     # chispa: punto brillante con halo
            g = QRadialGradient(QPointF(0, 0), 0.5)
            g.setColorAt(0, QColor(255, 255, 255, 255))
            g.setColorAt(0.3, con_alfa(c, 220))
            g.setColorAt(1, con_alfa(c, 0))
            pc.setBrush(QBrush(g))
            pc.drawEllipse(QPointF(0, 0), 0.5, 0.5)
    finally:
        pc.end()
    return pm


# ---------------------------------------------------------------- efectos

class Efecto:
    """Base: guarda el escenario (para su geometría) y un azar propio repetible. ADITIVO: se suma como luz
    (modo Screen) en vez de taparse."""

    ADITIVO = False

    def __init__(self, semilla=0, **kw):
        self.kw = kw
        self.r = random.Random(semilla)
        self.esc = None

    def unir(self, esc):
        self.esc = esc
        self.iniciar()

    def iniciar(self):
        """Una vez: estado propio (partículas…)."""

    def redimensionar(self):
        """Al cambiar el tamaño: rehacer sprites."""

    def pintar(self, p, t, dt, e):
        pass

    # atajos de geometría (coordenadas de la imagen -> lienzo)
    def P(self, x, y):
        return self.esc.P(x, y)

    def R(self, rect):
        return self.esc.R(QRectF(*rect))

    @property
    def s(self):
        return self.esc.escala


class Lluvia(Efecto):
    """Lluvia en diagonal en dos capas (lejos fina y lenta, cerca más larga y rápida), todo en un solo trazo."""

    def iniciar(self):
        r = self.r
        n = self.kw.get("n", 220)
        self.gotas = [(r.random(), r.random(), r.uniform(0.6, 1.0), r.random() < 0.35) for _ in range(n)]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        ang = math.radians(self.kw.get("angulo", 12))
        col = QColor(self.kw.get("color", "#B9D8FF"))
        vel = self.kw.get("vel", 0.9)                 # pantallas por segundo
        largo = self.kw.get("largo", 0.035) * rect.height()
        lejos, cerca = [], []
        dx, dy = math.sin(ang), math.cos(ang)
        for x0, y0, v, cer in self.gotas:
            f = (y0 + t * vel * v * (1.35 if cer else 1.0)) % 1.0
            y = rect.top() + f * rect.height()
            x = rect.left() + ((x0 + f * dx * 0.12) % 1.0) * rect.width()
            L = largo * (1.5 if cer else 0.9) * v
            (cerca if cer else lejos).append(QLineF(x, y, x + dx * L, y + dy * L))
        p.setPen(QPen(con_alfa(col, self.kw.get("alfa", 70)), max(1.0, 0.9 * self.s), Qt.SolidLine, Qt.RoundCap))
        p.drawLines(lejos)
        p.setPen(QPen(con_alfa(col, int(self.kw.get("alfa", 70) * 1.6)), max(1.0, 1.4 * self.s), Qt.SolidLine,
                      Qt.RoundCap))
        p.drawLines(cerca)


class Salpicaduras(Efecto):
    """Anillos que se abren en el suelo mojado donde cae la lluvia."""

    def iniciar(self):
        n = self.kw.get("n", 18)
        self.puntos = [(self.r.random(), self.r.random(), self.r.random(), self.r.uniform(0.7, 1.3)) for _ in range(n)]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        col = QColor(self.kw.get("color", "#CFE6FF"))
        rmax = self.kw.get("radio", 14) * self.s
        p.setBrush(Qt.NoBrush)
        for x0, y0, fase, vel in self.puntos:
            u = (t * 1.4 * vel + fase) % 1.0
            # cada vuelta el anillo nace en otro sitio
            k = int(t * 1.4 * vel + fase)
            x = rect.left() + ((x0 + k * 0.618) % 1.0) * rect.width()
            y = rect.top() + ((y0 + k * 0.381) % 1.0) * rect.height()
            prof = 0.6 + 0.8 * (y - rect.top()) / max(1.0, rect.height())     # más grandes cerca
            rr = rmax * u * prof
            p.setPen(QPen(con_alfa(col, int(150 * (1 - u))), max(1.0, 1.1 * self.s)))
            p.drawEllipse(QPointF(x, y), rr, rr * 0.32)


class Reflejos(Efecto):
    """Destellos horizontales sobre suelo mojado o agua: rayitas de luz que respiran y se deslizan despacio."""

    ADITIVO = True

    def iniciar(self):
        n = self.kw.get("n", 60)
        self.rayas = [(self.r.random(), self.r.random(), self.r.uniform(0.3, 1.0), self.r.uniform(0, 6.28),
                       self.r.uniform(0.6, 1.8), self.r.randrange(4)) for _ in range(n)]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        colores = [QColor(c) for c in self.kw.get("colores", ("#FFFFFF",))]
        largo = self.kw.get("largo", 28) * self.s
        for x0, y0, L, fase, frec, ci in self.rayas:
            a = (0.5 + 0.5 * math.sin(t * frec + fase)) ** 2 * self.kw.get("alfa", 90) * (0.8 + 0.5 * e)
            if a < 6:
                continue
            x = rect.left() + ((x0 + math.sin(t * 0.15 + fase) * 0.01) % 1.0) * rect.width()
            y = rect.top() + y0 * rect.height()
            l = largo * L * (0.6 + 0.8 * y0)
            p.setPen(QPen(con_alfa(colores[ci % len(colores)], int(a)), max(1.0, 1.4 * self.s), Qt.SolidLine,
                          Qt.RoundCap))
            p.drawLine(QPointF(x - l / 2, y), QPointF(x + l / 2, y))


class Agua(Efecto):
    """Agua en calma: ondas concéntricas aplastadas que se abren y se desvanecen en puntos que cambian."""

    def iniciar(self):
        n = self.kw.get("n", 6)
        self.ondas = [(self.r.random(), self.r.random(), self.r.random(), self.r.uniform(0.6, 1.1)) for _ in range(n)]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        col = QColor(self.kw.get("color", "#FFFFFF"))
        rmax = self.kw.get("radio", 40) * self.s
        p.setBrush(Qt.NoBrush)
        for x0, y0, fase, vel in self.ondas:
            ciclo = t * 0.18 * vel + fase
            u = ciclo % 1.0
            k = int(ciclo)
            x = rect.left() + ((x0 + k * 0.618) % 1.0) * rect.width()
            y = rect.top() + ((y0 + k * 0.381) % 1.0) * rect.height()
            for j in (0.0, 0.33):
                uu = u - j
                if uu <= 0:
                    continue
                p.setPen(QPen(con_alfa(col, int(70 * (1 - uu))), max(1.0, 1.2 * self.s)))
                p.drawEllipse(QPointF(x, y), rmax * uu, rmax * uu * 0.28)


class Humo(Efecto):
    """Humo o vapor que sube desde un punto: bocanadas suaves que crecen, se ladean y se desvanecen."""

    def iniciar(self):
        n = self.kw.get("n", 10)
        self.bocanadas = [(k / n, self.r.uniform(0, 6.28), self.r.uniform(0.8, 1.2)) for k in range(n)]
        self._pm, self._clave = None, None

    def pintar(self, p, t, dt, e):
        x, y = self.kw["punto"]
        base = self.P(x, y)
        alto = self.kw.get("alto", 120) * self.s
        ancho = self.kw.get("ancho", 30) * self.s
        tam = self.kw.get("tam", 26) * self.s
        clave = int(tam)
        if self._clave != clave:
            self._pm = _halo(self.kw.get("color", "#FFFFFF"), tam, 0.35)
            self._clave = clave
        vel = self.kw.get("vel", 0.16)
        alfa = self.kw.get("alfa", 0.45)
        for off, fase, v in self.bocanadas:
            u = (t * vel * v + off) % 1.0
            px = base.x() + math.sin(u * 3.2 + fase) * ancho * u + self.kw.get("viento", 0.4) * ancho * u * u
            py = base.y() - u * alto
            esc = 0.25 + 0.95 * u
            p.setOpacity(alfa * math.sin(math.pi * u) ** 1.3)
            w = self._pm.width() * esc
            p.drawPixmap(QRectF(px - w / 2, py - w / 2, w, w), self._pm, QRectF(self._pm.rect()))
        p.setOpacity(1.0)


class Caida(Efecto):
    """Partículas que caen (o suben con vel < 0): pétalos, hojas, corazones, estrellas, chispas, gotas, flores;
    se balancean, giran y se voltean."""

    def iniciar(self):
        r = self.r
        n = self.kw.get("n", 30)
        ncol = len(self.kw.get("colores", ("#F7B9CF",)))
        self.parts = [(r.random(), r.random(), r.uniform(0.7, 1.3), r.uniform(0.01, 0.04), r.uniform(0.6, 1.6),
                       r.uniform(0, 6.28), r.uniform(-1.2, 1.2), r.uniform(0.8, 2.0), r.randrange(ncol),
                       r.uniform(0.6, 1.0)) for _ in range(n)]
        self._sprites, self._clave = [], None

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        tam = self.kw.get("tam", 16) * self.s
        if self._clave != int(tam):
            self._sprites = [_forma(self.kw.get("tipo", "petalo"), c, tam) for c in self.kw.get("colores", ("#F7B9CF",))]
            self._clave = int(tam)
        vel = self.kw.get("vel", 0.06)
        deriva = self.kw.get("deriva", 0.02)
        voltea = self.kw.get("voltea", True)
        alfa = self.kw.get("alfa", 1.0)
        if self.kw.get("recortar"):
            p.save()
            p.setClipRect(rect)
        for x0, y0, v, amp, frec, fase, giro, fv, ci, esc in self.parts:
            yf = (y0 + t * vel * v) % 1.0
            xf = (x0 + t * deriva * v + amp * math.sin(frec * t + fase)) % 1.0
            x, y = rect.left() + xf * rect.width(), rect.top() + yf * rect.height()
            pm = self._sprites[ci]
            borde = min(1.0, yf / 0.08, (1 - yf) / 0.08)        # aparecen y se van sin cortes
            p.setOpacity(max(0.0, borde) * alfa)
            p.save()
            p.translate(x, y)
            p.rotate(math.degrees(giro * t + fase))
            p.scale(esc * (max(0.15, abs(math.cos(fv * t + fase))) if voltea else 1.0), esc)
            p.drawPixmap(QPointF(-pm.width() / 2, -pm.height() / 2), pm)
            p.restore()
        p.setOpacity(1.0)
        if self.kw.get("recortar"):
            p.restore()


class Brillo(Efecto):
    """Resplandor en un punto (farol, letrero, ojo…). modos: respira, musica, neon (casi siempre encendido con
    algún parpadeo), latido (golpes cortos con los graves)."""

    ADITIVO = True

    def iniciar(self):
        self._pm, self._clave = None, None
        self.fase = self.r.uniform(0, 6.28)

    def pintar(self, p, t, dt, e):
        x, y = self.kw["punto"]
        c = self.P(x, y)
        rad = self.kw.get("radio", 60) * self.s
        if self._clave != int(rad):
            self._pm = _halo(self.kw.get("color", "#FFC080"), rad, self.kw.get("dureza", 0.4))
            self._clave = int(rad)
        modo = self.kw.get("modo", "respira")
        base = self.kw.get("alfa", 0.6)
        if modo == "musica":
            b = self.esc.banda(self.kw.get("banda"))
            a = base * (0.35 + 0.9 * b)
        elif modo == "latido":
            a = base * min(1.0, 0.15 + 1.4 * self.esc.graves())
        elif modo == "neon":
            ruido = math.sin(t * 13.1 + self.fase) + math.sin(t * 7.3 + 2 * self.fase)
            apagon = (t * 0.21 + self.fase) % 1.0 < 0.025
            a = base * (0.15 if apagon else (0.85 + 0.08 * ruido / 2)) * (0.9 + 0.25 * e)
        else:
            a = base * (0.7 + 0.3 * math.sin(t * self.kw.get("frec", 1.1) + self.fase)) * (0.9 + 0.3 * e)
        p.setOpacity(max(0.0, min(1.0, a)))
        p.drawPixmap(QPointF(c.x() - self._pm.width() / 2, c.y() - self._pm.height() / 2), self._pm)
        p.setOpacity(1.0)


class Destellos(Efecto):
    """Estrellitas de cuatro puntas que titilan (cielo, cristales, purpurina)."""

    ADITIVO = True

    def iniciar(self):
        n = self.kw.get("n", 15)
        self.pts = [(self.r.random(), self.r.random(), self.r.uniform(0, 6.28), self.r.uniform(0.5, 1.4),
                     self.r.uniform(0.5, 1.0)) for _ in range(n)]
        self._pm, self._clave = None, None

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        tam = self.kw.get("tam", 18) * self.s
        if self._clave != int(tam):
            self._pm = _forma("estrella", self.kw.get("color", "#FFFFFF"), tam)
            self._clave = int(tam)
        for x0, y0, fase, frec, esc in self.pts:
            a = max(0.0, math.sin(t * frec + fase)) ** 4
            if a < 0.04:
                continue
            x, y = rect.left() + x0 * rect.width(), rect.top() + y0 * rect.height()
            w = self._pm.width() * esc * (0.6 + 0.4 * a)
            p.setOpacity(min(1.0, a * (0.9 + 0.3 * e)))
            p.drawPixmap(QRectF(x - w / 2, y - w / 2, w, w), self._pm, QRectF(self._pm.rect()))
        p.setOpacity(1.0)


class Luciernagas(Efecto):
    """Puntos de luz que flotan con deriva lenta y se encienden y apagan (luciérnagas, polvo en un rayo)."""

    ADITIVO = True

    def iniciar(self):
        n = self.kw.get("n", 16)
        self.pts = [(self.r.random(), self.r.random(), self.r.uniform(0.01, 0.05), self.r.uniform(0.1, 0.35),
                     self.r.uniform(0, 6.28), self.r.uniform(0.3, 0.9)) for _ in range(n)]
        self._pm, self._clave = None, None

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        rad = self.kw.get("radio", 7) * self.s
        if self._clave != int(rad):
            self._pm = _halo(self.kw.get("color", "#D6FF96"), rad, 0.3)
            self._clave = int(rad)
        sube = self.kw.get("sube", 0.0)
        for x0, y0, dr, vel, fase, frec in self.pts:
            x = rect.left() + ((x0 + math.sin(t * vel + fase) * dr) % 1.0) * rect.width()
            y = rect.top() + ((y0 - t * sube * vel + math.sin(t * vel * 1.3 + 2 * fase) * dr * 0.6) % 1.0) * rect.height()
            b = max(0.0, math.sin(t * frec + fase)) ** (self.kw.get("parpadeo", 3))
            if b < 0.03:
                continue
            p.setOpacity(min(1.0, b * self.kw.get("alfa", 0.9) * (0.8 + 0.4 * e)))
            p.drawPixmap(QPointF(x - self._pm.width() / 2, y - self._pm.height() / 2), self._pm)
        p.setOpacity(1.0)


class Rayos(Efecto):
    """Rayos eléctricos que nacen en una zona, quebrados y ramificados; duran un instante y salen más con los
    graves. Se dibujan con halo ancho y núcleo blanco."""

    ADITIVO = True

    def iniciar(self):
        self.slots = [{"fin": -1.0, "prox": self.r.uniform(0, 1.5), "camino": None, "col": 0}
                      for _ in range(self.kw.get("n", 3))]

    def _nuevo(self, rect):
        r = self.r
        x = rect.left() + r.random() * rect.width()
        y = rect.top() + r.uniform(0, 0.3) * rect.height()
        largo = rect.height() * r.uniform(0.35, 0.8)
        puntos = [QPointF(x, y)]
        pasos = 10
        for k in range(pasos):
            x += r.uniform(-0.06, 0.06) * rect.width()
            y += largo / pasos
            puntos.append(QPointF(x, y))
        camino = QPainterPath(puntos[0])
        for q in puntos[1:]:
            camino.lineTo(q)
        # una rama
        i = r.randrange(2, pasos - 2)
        rama = QPainterPath(puntos[i])
        bx, by = puntos[i].x(), puntos[i].y()
        for _ in range(4):
            bx += r.uniform(-0.07, 0.07) * rect.width()
            by += largo / pasos * 0.8
            rama.lineTo(QPointF(bx, by))
        camino.addPath(rama)
        return camino

    def pintar(self, p, t, dt, e):
        rects = [self.R(rc) for rc in self.kw.get("rects")]
        colores = [QColor(c) for c in self.kw.get("colores", ("#7FD8FF", "#C38BFF"))]
        g = self.esc.graves()
        p.setBrush(Qt.NoBrush)
        for k, sl in enumerate(self.slots):
            if t >= sl["prox"]:
                sl["camino"] = self._nuevo(rects[k % len(rects)])
                sl["fin"] = t + self.r.uniform(0.08, 0.18)
                sl["prox"] = t + self.r.uniform(0.6, 2.0) / (1 + 2.5 * g)
                sl["col"] = self.r.randrange(len(colores))
            if t < sl["fin"] and sl["camino"] is not None:
                c = colores[sl["col"]]
                vida = (sl["fin"] - t) / 0.18
                p.setPen(QPen(con_alfa(c, int(70 * vida + 20)), 9 * self.s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(sl["camino"])
                p.setPen(QPen(con_alfa(c, int(180 * vida + 60)), 3 * self.s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.drawPath(sl["camino"])
                p.setPen(QPen(QColor(255, 255, 255, int(200 * vida + 40)), 1.2 * self.s, Qt.SolidLine, Qt.RoundCap,
                              Qt.RoundJoin))
                p.drawPath(sl["camino"])


class Aura(Efecto):
    """Aura de energía: chispas alargadas que suben rápido desde una zona, más intensas con la música."""

    ADITIVO = True

    def iniciar(self):
        n = self.kw.get("n", 40)
        self.pts = [(self.r.random(), self.r.random(), self.r.uniform(0.6, 1.4), self.r.randrange(3),
                     self.r.uniform(0, 6.28)) for _ in range(n)]
        self._sprites, self._clave = [], None

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        tam = self.kw.get("tam", 22) * self.s
        colores = self.kw.get("colores", ("#9CE8FF", "#C79BFF", "#FFFFFF"))
        if self._clave != int(tam):
            self._sprites = [_halo(c, tam / 2, 0.25) for c in colores]
            self._clave = int(tam)
        vel = self.kw.get("vel", 0.45) * (1 + 0.8 * e)
        for x0, y0, v, ci, fase in self.pts:
            u = (y0 + t * vel * v) % 1.0
            x = rect.left() + (x0 + 0.01 * math.sin(t * 3 + fase)) * rect.width()
            y = rect.bottom() - u * rect.height()
            pm = self._sprites[ci % len(self._sprites)]
            p.setOpacity(min(1.0, math.sin(math.pi * u) * (0.45 + 0.7 * e)))
            w = pm.width()
            p.drawPixmap(QRectF(x - w * 0.18, y - w, w * 0.36, w * 2.0), pm, QRectF(pm.rect()))
        p.setOpacity(1.0)


class Nubes(Efecto):
    """Bancos de bruma o nube muy suaves que se desplazan despacio de lado a lado."""

    def iniciar(self):
        n = self.kw.get("n", 3)
        self.nubes = [(self.r.random(), self.r.random(), self.r.uniform(0.6, 1.0), self.r.uniform(0.5, 1.0))
                      for _ in range(n)]
        self._pm, self._clave = None, None

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        tam = self.kw.get("tam", 260) * self.s
        if self._clave != int(tam):
            self._pm = _halo(self.kw.get("color", "#FFFFFF"), tam / 2, 0.45)
            self._clave = int(tam)
        vel = self.kw.get("vel", 0.006)
        for x0, y0, esc, v in self.nubes:
            xf = (x0 + t * vel * v) % 1.2 - 0.1
            x, y = rect.left() + xf * rect.width(), rect.top() + y0 * rect.height()
            w = self._pm.width() * esc
            p.setOpacity(self.kw.get("alfa", 0.25) * min(1.0, (xf + 0.1) / 0.15, (1.1 - xf) / 0.15))
            p.drawPixmap(QRectF(x - w, y - w * 0.22, w * 2, w * 0.44), self._pm, QRectF(self._pm.rect()))
        p.setOpacity(1.0)


class Voladores(Efecto):
    """Mariposas o murciélagos que cruzan siguiendo una curva suave y aletean."""

    def iniciar(self):
        n = self.kw.get("n", 2)
        self.v = [(self.r.random(), self.r.uniform(0.04, 0.08), self.r.uniform(0, 6.28), self.r.uniform(0.7, 1.2))
                  for _ in range(n)]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        tipo = self.kw.get("tipo", "mariposa")
        col = QColor(self.kw.get("color", "#FFD1E8"))
        tam = self.kw.get("tam", 16) * self.s
        for x0, vel, fase, esc in self.v:
            u = (x0 + t * vel) % 1.0
            x = rect.left() + u * rect.width()
            y = rect.top() + (0.5 + 0.35 * math.sin(u * 9 + fase)) * rect.height()
            ala = math.sin(t * (14 if tipo == "murcielago" else 9) + fase)
            s = tam * esc
            p.setOpacity(min(1.0, u / 0.06, (1 - u) / 0.06))
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            if tipo == "murcielago":
                for lado in (-1, 1):
                    f = QPainterPath(QPointF(x, y))
                    f.quadTo(QPointF(x + lado * s * 0.5, y - s * 0.5 * ala), QPointF(x + lado * s, y - s * 0.15 * ala))
                    f.quadTo(QPointF(x + lado * s * 0.6, y + s * 0.15), QPointF(x, y + s * 0.12))
                    p.drawPath(f)
                p.drawEllipse(QPointF(x, y), s * 0.14, s * 0.18)
            else:
                abre = 0.25 + 0.75 * abs(ala)
                for lado in (-1, 1):
                    p.drawEllipse(QPointF(x + lado * s * 0.32 * abre, y - s * 0.12), s * 0.34 * abre, s * 0.30)
                    p.drawEllipse(QPointF(x + lado * s * 0.22 * abre, y + s * 0.18), s * 0.22 * abre, s * 0.20)
                p.setBrush(mezclar(col, QColor("black"), 0.5))
                p.drawRoundedRect(QRectF(x - s * 0.04, y - s * 0.25, s * 0.08, s * 0.5), s * 0.04, s * 0.04)
        p.setOpacity(1.0)


class Flashes(Efecto):
    """Flashes de cámaras entre el público: destellos blancos cortísimos en puntos al azar (más con la música)."""

    ADITIVO = True

    def iniciar(self):
        self.activos = []
        self._pm, self._clave = None, None
        self._acum = 0.0

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        rad = self.kw.get("radio", 22) * self.s
        if self._clave != int(rad):
            self._pm = _halo("#FFFFFF", rad, 0.2)
            self._clave = int(rad)
        self._acum += dt * self.kw.get("frec", 2.0) * (1 + 3 * self.esc.graves())
        while self._acum >= 1.0:
            self._acum -= 1.0
            self.activos.append((rect.left() + self.r.random() * rect.width(),
                                 rect.top() + self.r.random() * rect.height(), t))
        vivos = []
        for x, y, t0 in self.activos:
            u = (t - t0) / 0.16
            if u >= 1:
                continue
            vivos.append((x, y, t0))
            p.setOpacity(1 - u)
            p.drawPixmap(QPointF(x - self._pm.width() / 2, y - self._pm.height() / 2), self._pm)
        self.activos = vivos[-20:]
        p.setOpacity(1.0)


class Vehiculo(Efecto):
    """Luz que cruza el cielo (coche volador, dron) con su estela, cada cierto tiempo."""

    ADITIVO = True

    def pintar(self, p, t, dt, e):
        x0, x1, y = self.kw["de"][0], self.kw["a"][0], self.kw["de"][1]
        y1 = self.kw["a"][1]
        periodo = self.kw.get("periodo", 16)
        dur = self.kw.get("dur", 7)
        u = ((t + self.kw.get("desfase", 0)) % periodo) / dur
        if u >= 1:
            return
        a = self.P(x0 + (x1 - x0) * u, y + (y1 - y) * u)
        b = self.P(x0 + (x1 - x0) * max(0.0, u - 0.06), y + (y1 - y) * max(0.0, u - 0.06))
        col = QColor(self.kw.get("color", "#7FF5FF"))
        g = QLinearGradient(b, a)
        g.setColorAt(0, con_alfa(col, 0))
        g.setColorAt(1, con_alfa(col, 200))
        p.setPen(QPen(QBrush(g), 3 * self.s, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(b, a)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawEllipse(a, 2.2 * self.s, 2.2 * self.s)


class Cascada(Efecto):
    """Agua que cae: rayitas verticales claras que bajan dentro de una franja estrecha."""

    def iniciar(self):
        self.rayas = [(self.r.random(), self.r.random(), self.r.uniform(0.6, 1.2)) for _ in range(self.kw.get("n", 8))]

    def pintar(self, p, t, dt, e):
        rect = self.R(self.kw.get("rect"))
        p.setPen(QPen(QColor(255, 255, 255, 150), max(1.0, 1.2 * self.s), Qt.SolidLine, Qt.RoundCap))
        for x0, y0, v in self.rayas:
            f = (y0 + t * 0.8 * v) % 1.0
            x = rect.left() + x0 * rect.width()
            y = rect.top() + f * rect.height()
            p.drawLine(QPointF(x, y), QPointF(x, min(rect.bottom(), y + rect.height() * 0.22)))


class Ondas(Efecto):
    """Las frecuencias de la música como línea de ondas suave en un sitio de la ilustración."""

    def pintar(self, p, t, dt, e):
        x0, y = self.P(self.kw["x0"], self.kw["y"]).x(), self.P(self.kw["x0"], self.kw["y"]).y()
        ancho = self.kw["ancho"] * self.s
        alto = self.kw.get("alto", 70) * self.s
        col = QColor(self.kw["color"]) if self.kw.get("color") else self.esc.acento()
        self.esc.ondas(p, y, ancho, alto, col, x0=x0, reflejo=self.kw.get("reflejo", False),
                       grosor=1.4 * max(1.0, self.s))


# ---------------------------------------------------------------- el escenario

class EscenarioImagen(EscenarioBase):
    """Escenario con ilustración. Subclases: IMAGEN (archivo en escenarios_img), EFECTOS (lista de efectos),
    INTERACCION (tipo y colores de las partículas del ratón), EPICO (sacudida y destello con los graves)."""

    IMAGEN = ""
    EFECTOS = ()
    INTERACCION = ("chispa", ("#FFFFFF",))
    EPICO = False
    SUPER = 2                  # las ilustraciones se guardan al doble de resolución (más nítidas en pantalla);
                               # las coordenadas de los efectos siguen siendo las de la imagen original
    FONDO = "#0B0A12"
    VINETA = 70

    def preparar(self):
        self._img = ilustracion(self.IMAGEN) if self.IMAGEN else QImage()
        self.iw = max(1, self._img.width() // self.SUPER)
        self.ih = max(1, self._img.height() // self.SUPER)
        self.efectos = list(self.crear_efectos())
        for ef in self.efectos:
            ef.unir(self)
        self.escala, self._ox, self._oy = 1.0, 0.0, 0.0
        self._cache_img, self._cache_img_clave = None, None
        self._px = self._py = 0.0
        self._t_prev = None
        self._sacudida = 0.0
        self._sac_dir = (0.0, 0.0)
        self._graves_media = 0.0
        self._ult_golpe = -10.0
        self._flash = 0.0
        self._margen = 0
        self._trazo = []                       # partículas del ratón: [x, y, vx, vy, t0, vida, sprite]
        self._cursor_prev = None
        self._sprites_inter, self._clave_inter = [], None
        self.setMouseTracking(True)

    def crear_efectos(self):
        return self.EFECTOS

    # ------------------------------------------------------------ audio
    def banda(self, i=None):
        if i is None:
            return self.energia()
        return max(0.0, min(1.0, self.bandas[int(i) % len(self.bandas)]))

    def graves(self):
        return sum(self.bandas[:4]) / 4.0

    # ------------------------------------------------------------ geometría
    def _geometria(self, W, H):
        aspecto_img, aspecto = self.iw / self.ih, W / H
        self.contener = abs(aspecto_img - aspecto) / aspecto > 0.12
        s = (min if self.contener else max)(W / self.iw, H / self.ih)
        self.escala = s
        self._ox, self._oy = (W - self.iw * s) / 2, (H - self.ih * s) / 2

    def P(self, x, y):
        return QPointF(self._ox + x * self.escala, self._oy + y * self.escala)

    def R(self, rect):
        return QRectF(self._ox + rect.x() * self.escala, self._oy + rect.y() * self.escala,
                      rect.width() * self.escala, rect.height() * self.escala)

    # ------------------------------------------------------------ pintado
    def pintar_estatico(self, p, W, H):
        self._geometria(W, H)
        p.fillRect(QRectF(0, 0, W, H), QColor(self.FONDO))
        if self._img.isNull():
            return
        if self.contener:
            # relleno de los lados: la misma imagen, muy desenfocada y oscura
            peque = self._img.scaled(max(8, self.iw // 24), max(8, self.ih // 24), Qt.IgnoreAspectRatio,
                                     Qt.SmoothTransformation)
            s2 = max(W / peque.width(), H / peque.height())
            fondo = peque.scaled(int(peque.width() * s2) + 2, int(peque.height() * s2) + 2, Qt.IgnoreAspectRatio,
                                 Qt.SmoothTransformation)
            p.drawImage(QPointF((W - fondo.width()) / 2, (H - fondo.height()) / 2), fondo)
            p.fillRect(QRectF(0, 0, W, H), QColor(0, 0, 0, 120))
        img = self._img.scaled(round(self.iw * self.escala), round(self.ih * self.escala), Qt.IgnoreAspectRatio,
                               Qt.SmoothTransformation)
        p.drawImage(QPointF(self._ox, self._oy), img)
        if self.contener:
            # bordes fundidos con el relleno
            fx = img.width() * 0.06
            for x0, x1 in ((self._ox, self._ox + fx), (self._ox + img.width(), self._ox + img.width() - fx)):
                g = QLinearGradient(x0, 0, x1, 0)
                g.setColorAt(0, QColor(0, 0, 0, 160))
                g.setColorAt(1, QColor(0, 0, 0, 0))
                p.fillRect(QRectF(min(x0, x1), 0, fx, H), QBrush(g))
        # viñeta suave
        v = QRadialGradient(QPointF(W / 2, H / 2), math.hypot(W, H) / 2)
        v.setColorAt(0.6, QColor(0, 0, 0, 0))
        v.setColorAt(1.0, QColor(0, 0, 0, self.VINETA))
        p.fillRect(QRectF(0, 0, W, H), QBrush(v))

    def pintar_animado(self, p, W, H, t):
        dt = 0.033 if self._t_prev is None else max(0.0, min(0.1, t - self._t_prev))
        self._t_prev = t
        e = self.energia()
        for ef in self.efectos:
            p.save()
            p.setCompositionMode(QPainter.CompositionMode_Screen if ef.ADITIVO
                                 else QPainter.CompositionMode_SourceOver)
            ef.pintar(p, t, dt, e)
            p.restore()
        self._pintar_trazo(p, t, dt)
        if self.EPICO and self._flash > 0.01:
            p.fillRect(QRectF(0, 0, W, H), QColor(255, 255, 255, int(70 * self._flash)))

    # ------------------------------------------------------------ interacción
    def _sprites_trazo(self):
        clave = int(14 * self.escala)
        if self._clave_inter != clave:
            tipo, colores = self.INTERACCION
            self._sprites_inter = [_forma(tipo, c, 18 * max(0.6, self.escala)) for c in colores]
            self._clave_inter = clave
        return self._sprites_inter

    def soltar(self, x, y, n, fuerza):
        sprites = self._sprites_trazo()
        t = self._ahora - self._t0
        for _ in range(n):
            a = self.rnd.uniform(0, 2 * math.pi)
            v = self.rnd.uniform(0.3, 1.0) * fuerza
            self._trazo.append([x, y, math.cos(a) * v, math.sin(a) * v - fuerza * 0.4, t,
                                self.rnd.uniform(0.7, 1.4), self.rnd.randrange(len(sprites)),
                                self.rnd.uniform(0, 360)])
        del self._trazo[:-MAX_TRAZO]

    def _pintar_trazo(self, p, t, dt):
        if not self._trazo:
            return
        sprites = self._sprites_trazo()
        vivos = []
        for q in self._trazo:
            u = (t - q[4]) / q[5]
            if u >= 1:
                continue
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            q[3] += 60 * self.escala * dt              # gravedad suave
            vivos.append(q)
            pm = sprites[q[6] % len(sprites)]
            p.setOpacity(1 - u)
            p.save()
            p.translate(q[0], q[1])
            p.rotate(q[7] + u * 120)
            esc = 1.0 - 0.4 * u
            p.scale(esc, esc)
            p.drawPixmap(QPointF(-pm.width() / 2, -pm.height() / 2), pm)
            p.restore()
        p.setOpacity(1.0)
        self._trazo = vivos

    def mousePressEvent(self, ev):
        x = ev.position().x() + self._margen - self._px
        y = ev.position().y() + self._margen - self._py
        self.soltar(x, y, 16, 260 * max(0.6, self.escala))
        if self.EPICO:
            self._golpe(0.8)
        super().mousePressEvent(ev)

    def _golpe(self, fuerza):
        self._sacudida = max(self._sacudida, fuerza)
        a = self.rnd.uniform(0, 2 * math.pi)
        self._sac_dir = (math.cos(a), math.sin(a))
        self._flash = max(self._flash, fuerza * 0.6)

    # ------------------------------------------------------------ cuadro
    def _seguir_cursor(self, w, h, M):
        """Paralaje hacia el cursor y partículas cuando el ratón se mueve sobre el fondo."""
        try:
            local = self.mapFromGlobal(QCursor.pos())
        except RuntimeError:
            return
        nx = max(-1.0, min(1.0, (local.x() - w / 2) / (w / 2)))
        ny = max(-1.0, min(1.0, (local.y() - h / 2) / (h / 2)))
        self._px += (-nx * M * 0.85 - self._px) * 0.06
        self._py += (-ny * M * 0.85 - self._py) * 0.06
        dentro = 0 <= local.x() < w and 0 <= local.y() < h
        if dentro and self._cursor_prev is not None:
            dx, dy = local.x() - self._cursor_prev.x(), local.y() - self._cursor_prev.y()
            if dx * dx + dy * dy > 64:
                try:
                    encima = QApplication.widgetAt(QCursor.pos())
                except RuntimeError:
                    encima = None
                if encima is self or (encima is not None and self.isAncestorOf(encima)):
                    self.soltar(local.x() + M - self._px, local.y() + M - self._py, 1, 40 * max(0.6, self.escala))
        self._cursor_prev = local

    def paintEvent(self, _ev):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        M = int(MARGEN * max(w, h))
        self._margen = M
        W, H = w + 2 * M, h + 2 * M
        acento = self.acento()
        import time as _time
        clave = (W, H, acento.rgba() if _time.monotonic() - self._acento_t > TRANSICION_ACENTO else None)
        if self._cache is None or self._cache_clave != clave:
            pm = QPixmap(W, H)
            pc = QPainter(pm)
            try:
                pc.setRenderHint(QPainter.Antialiasing, True)
                self.pintar_estatico(pc, W, H)
            finally:
                pc.end()
            self._cache, self._cache_clave = pm, clave
        t = self._ahora - self._t0
        self._seguir_cursor(w, h, M)
        # golpe de bajo: sacudida corta y destello (solo en los épicos)
        if self.EPICO:
            g = self.graves()
            self._graves_media += (g - self._graves_media) * (1.0 - 0.95 ** self._pasos)
            if g > 0.55 and g - self._graves_media > 0.18 and t - self._ult_golpe > 0.25:
                self._ult_golpe = t
                self._golpe(min(1.0, g))
            self._sacudida *= 0.82 ** self._pasos
            self._flash *= 0.80 ** self._pasos
        # solo se mueve con el ratón; los épicos además dan una sacudida corta con los golpes de bajo y el clic
        amp = self._sacudida * M * 0.8
        ox = round(-M + self._px + self._sac_dir[0] * amp * math.sin(t * 60))
        oy = round(-M + self._py + self._sac_dir[1] * amp * math.sin(t * 60))
        self._ritmo.antes()
        p = QPainter(self)
        try:
            p.drawPixmap(ox, oy, self._cache)
            p.translate(ox, oy)
            p.setRenderHint(QPainter.Antialiasing, True)
            self.pintar_animado(p, W, H, t)
        finally:
            p.end()
            self._ritmo.despues()
