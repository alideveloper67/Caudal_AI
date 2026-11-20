# -*- coding: utf-8 -*-
"""Escenario Cinnamoroll: un café flotando sobre un mar de nubes, en un cielo de día pastel.

Solo estética: celeste, nubes de algodón, rollos de canela, café, blanco. No se dibuja ninguna cara
ni figura de personaje con marca.

* Estático (una vez): cielo con sol, rayos, arcoíris tenue, mar de nubes lejano, café sobre una nube,
  viñeta y grano.
* Animado (30 FPS): tres capas de nubes en paralaje (pre-renderizadas), globos, vapor de la taza,
  pájaros, corazoncitos y destellos, sol que respira y ondas de la música sobre el mar de nubes.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)

from descargador.ui.escena.escenarios.base import EscenarioBase, con_alfa, mezclar

CIELO_LEJOS = "#CDEBFF"      # celeste medio: las nubes lejanas se mezclan con este color
# Capas de nubes en paralaje, de lejos a cerca: (banda superior, banda inferior, alto de nube en fracción
# de h, mezcla con el cielo 0..1, nubes por cada 2 anchos, círculos mín/máx por nube, velocidad en anchos/s).
CAPAS = (
    (0.28, 0.46, 0.07, 0.60, 8, (30, 42), 0.010),
    (0.44, 0.60, 0.11, 0.30, 7, (40, 58), 0.020),
    (0.70, 1.02, 0.20, 0.00, 5, (55, 70), 0.040),
)
# Globos lejanos: (x, y, tamaño en fracción de h, fase, colores de franjas).
GLOBOS = (
    (0.10, 0.25, 0.075, 0.0, ("#FFC9D6", "#FFFFFF")),
    (0.21, 0.19, 0.060, 1.7, ("#BFE6FF", "#FFFFFF")),
    (0.31, 0.31, 0.065, 3.1, ("#FFF0B3", "#FFFFFF")),
)
ARCOIRIS = ("#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#C9BAFF", "#FFBAE6")
CELESTE = "#9ED8FF"


# ---------------------------------------------------------------- geometría y dibujo sueltos

def _mix(hexo, mezcla):
    """Color `hexo` mezclado hacia el celeste del cielo (0 = tal cual, 1 = celeste)."""
    return mezclar(QColor(hexo), QColor(CIELO_LEJOS), mezcla)


def _curva(puntos):
    """Curva suave que pasa por los puntos (cúbicas con controles en el punto medio de cada tramo)."""
    camino = QPainterPath(puntos[0])
    for a, b in zip(puntos, puntos[1:]):
        medio = (a.x() + b.x()) / 2
        camino.cubicTo(QPointF(medio, a.y()), QPointF(medio, b.y()), b)
    return camino


def _curva_suave(puntos):
    """Spline Catmull-Rom convertida a cúbicas: pasa por todos los puntos sin picos."""
    camino = QPainterPath(puntos[0])
    n = len(puntos)
    for i in range(n - 1):
        p0 = puntos[i - 1] if i > 0 else puntos[i]
        p1, p2 = puntos[i], puntos[i + 1]
        p3 = puntos[i + 2] if i + 2 < n else p2
        c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6)
        c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6)
        camino.cubicTo(c1, c2, p2)
    return camino


def _corazon(cx, cy, s):
    """Corazoncito de tamaño s: lóbulos arriba y punta abajo."""
    camino = QPainterPath()
    camino.moveTo(cx, cy - 0.35 * s)
    camino.cubicTo(QPointF(cx + 0.6 * s, cy - 1.0 * s), QPointF(cx + 1.2 * s, cy - 0.2 * s), QPointF(cx, cy + 0.8 * s))
    camino.cubicTo(QPointF(cx - 1.2 * s, cy - 0.2 * s), QPointF(cx - 0.6 * s, cy - 1.0 * s), QPointF(cx, cy - 0.35 * s))
    return camino


def _destello(cx, cy, r):
    """Destello de cuatro puntas con curvas cuadráticas hacia el centro."""
    camino = QPainterPath()
    camino.moveTo(cx, cy - r)
    camino.quadTo(cx, cy, cx + r, cy)
    camino.quadTo(cx, cy, cx, cy + r)
    camino.quadTo(cx, cy, cx - r, cy)
    camino.quadTo(cx, cy, cx, cy - r)
    return camino


def _forma_nube(rnd, ancho, alto, n):
    """Círculos (x, y, r) de una nube, con la base en y = 0 y aplanada: bultos arriba, bolitas rasas abajo."""
    circulos = []
    for _ in range(n):
        u = rnd.random()
        campana = math.sin(math.pi * u) ** 0.7
        r = alto * rnd.uniform(0.12, 0.26) * (0.6 + 0.4 * campana)
        x = (u - 0.5) * ancho * 0.9
        y = -r * 0.8 - (alto - r) * campana * rnd.uniform(0.25, 0.95)
        circulos.append((x, y, r))
    for _ in range(max(3, n // 6)):
        u = rnd.uniform(0.08, 0.92)
        r = alto * rnd.uniform(0.12, 0.18)
        circulos.append(((u - 0.5) * ancho * 0.9, -r * 0.7, r))
    return circulos


def _nube(p, cx, cy, alto, circulos, mezcla=0.0):
    """Nube en tres pasadas: sombra azulada desplazada abajo, cuerpo blanco con contorno leve y
    luces blancas puras hacia el sol (arriba a la izquierda)."""
    desp = alto * 0.07
    sombra = _mix("#A9CBEA", mezcla)
    sombra.setAlpha(220)
    borde = _mix("#DCEBFA", mezcla)
    cuerpo = QLinearGradient(0, cy - alto, 0, cy)
    cuerpo.setColorAt(0, _mix("#FFFFFF", mezcla))
    cuerpo.setColorAt(1, _mix("#EAF4FF", mezcla))
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(sombra)
    for x, y, r in circulos:
        p.drawEllipse(QPointF(cx + x, cy + y + desp), r * 1.02, r * 1.02)
    p.setBrush(borde)
    for x, y, r in circulos:
        p.drawEllipse(QPointF(cx + x, cy + y), r + 1.2, r + 1.2)
    p.setBrush(cuerpo)
    for x, y, r in circulos:
        p.drawEllipse(QPointF(cx + x, cy + y), r, r)
    p.setBrush(_mix("#FFFFFF", mezcla))
    for x, y, r in circulos:
        if y < -alto * 0.4:
            p.drawEllipse(QPointF(cx + x - r * 0.35, cy + y - r * 0.4), r * 0.42, r * 0.42)
    p.restore()


def _mar(p, rnd, w, h, y0, y1, n, mezcla):
    """Franja de cientos de círculos pequeños: el mar de nubes del horizonte."""
    cuerpo = _mix("#FFFFFF", mezcla)
    sombra = _mix("#A9CBEA", mezcla)
    sombra.setAlpha(90)
    p.save()
    p.setPen(Qt.NoPen)
    for _ in range(n):
        f = rnd.random()
        y = (y0 + (y1 - y0) * f) * h
        r = h * (0.006 + 0.018 * f) * rnd.uniform(0.6, 1.3)
        x = rnd.uniform(-0.02, 1.02) * w
        p.setBrush(sombra)
        p.drawEllipse(QPointF(x, y + r * 0.45), r, r)
        p.setBrush(cuerpo)
        p.drawEllipse(QPointF(x, y), r, r)
    p.restore()


def _mesa(p, x, y, rx, ry, u):
    """Mesa redonda: `y` es el centro de la tapa."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#D9B68E"))
    p.drawRect(QRectF(x - 6 * u, y, 12 * u, 60 * u))
    p.drawEllipse(QPointF(x, y + 60 * u), 34 * u, 8 * u)
    p.setBrush(QColor("#E9CFAE"))
    p.drawEllipse(QPointF(x, y + 5 * u), rx, ry)
    p.setBrush(QColor("#FFFFFF"))
    p.setPen(QPen(QColor("#8FC8F2"), max(1.0, 3 * u)))
    p.drawEllipse(QPointF(x, y), rx, ry)
    p.restore()


def _sombrilla(p, x, y, u):
    """Sombrilla de rayas celestes y blancas con borde ondulado; `y` es el centro de la mesa."""
    p.save()
    yb = y - 150 * u
    yt = y - 240 * u
    p.setPen(QPen(QColor("#B9A38A"), max(1.0, 4 * u), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(x, y), QPointF(x, yt + 30 * u))
    doss = QPainterPath(QPointF(x - 130 * u, yb))
    doss.quadTo(QPointF(x - 120 * u, yt), QPointF(x, yt))
    doss.quadTo(QPointF(x + 120 * u, yt), QPointF(x + 130 * u, yb))
    doss.quadTo(QPointF(x + 65 * u, yb + 22 * u), QPointF(x, yb))
    doss.quadTo(QPointF(x - 65 * u, yb + 22 * u), QPointF(x - 130 * u, yb))
    doss.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setClipPath(doss)
    for i in range(8):
        p.setBrush(QColor("#8FD0FF") if i % 2 == 0 else QColor("#FFFFFF"))
        p.drawRect(QRectF(x - 130 * u + i * 32.5 * u, yt, 32.5 * u, yb + 30 * u - yt))
    p.setClipping(False)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(con_alfa("#6FB3E6", 120), max(1.0, 1.5 * u)))
    p.drawPath(doss)
    p.restore()


def _rollo(p, x, y, rx, ry, u):
    """Rollo de canela: espiral de dos vueltas (cúbicas) con glaseado blanco."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#E0A46C"))
    p.drawEllipse(QPointF(x, y), rx, ry)
    pts = []
    n = 36
    for i in range(n + 1):
        f = i / n
        th = f * 4 * math.pi
        r = 0.14 + 0.82 * f
        pts.append(QPointF(x + rx * 0.9 * r * math.cos(th), y + ry * 0.85 * r * math.sin(th)))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#A8643A"), max(1.0, 2.6 * u), Qt.SolidLine, Qt.RoundCap))
    p.drawPath(_curva_suave(pts))
    glaseado = [QPointF(x - rx * 0.8, y - ry * 0.3), QPointF(x - rx * 0.35, y - ry * 0.7),
                QPointF(x + rx * 0.05, y - ry * 0.2), QPointF(x + rx * 0.45, y - ry * 0.75),
                QPointF(x + rx * 0.8, y - ry * 0.35)]
    p.setPen(QPen(con_alfa("#FFFFFF", 230), max(1.0, 2.2 * u), Qt.SolidLine, Qt.RoundCap))
    p.drawPath(_curva_suave(glaseado))
    p.restore()


def _taza_cafe(p, x, y, u):
    """Taza blanca con banda celeste y café. `y` es el borde superior de la taza."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(x, y + 30 * u), 34 * u, 7 * u)
    cuerpo = QPainterPath(QPointF(x - 18 * u, y))
    cuerpo.lineTo(QPointF(x + 18 * u, y))
    cuerpo.cubicTo(QPointF(x + 18 * u, y + 22 * u), QPointF(x + 10 * u, y + 28 * u), QPointF(x, y + 28 * u))
    cuerpo.cubicTo(QPointF(x - 10 * u, y + 28 * u), QPointF(x - 18 * u, y + 22 * u), QPointF(x - 18 * u, y))
    cuerpo.closeSubpath()
    p.drawPath(cuerpo)
    p.save()
    p.setClipPath(cuerpo)
    p.setBrush(QColor("#8FD0FF"))
    p.drawRect(QRectF(x - 20 * u, y + 8 * u, 40 * u, 6 * u))
    p.restore()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#FFFFFF"), max(1.0, 5 * u)))
    p.drawArc(QRectF(x + 14 * u, y + 6 * u, 14 * u, 14 * u), -90 * 16, 180 * 16)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#7A4B2A"))
    p.drawEllipse(QPointF(x, y), 16 * u, 5 * u)
    p.restore()


def _maceta(p, x, y, u):
    """Maceta de barro con flores celestes. (x, y) es la base."""
    p.save()
    flores = ((-14, -48, 9), (2, -58, 10), (16, -46, 9), (-6, -38, 7), (9, -40, 7))
    p.setPen(QPen(QColor("#6FB3E6"), max(1.0, 2 * u)))
    for dx, dy, _ in flores:
        p.drawLine(QPointF(x, y - 30 * u), QPointF(x + dx * u, y + dy * u))
    p.setPen(Qt.NoPen)
    maceta = QPainterPath(QPointF(x - 18 * u, y - 30 * u))
    maceta.lineTo(QPointF(x + 18 * u, y - 30 * u))
    maceta.lineTo(QPointF(x + 13 * u, y))
    maceta.lineTo(QPointF(x - 13 * u, y))
    maceta.closeSubpath()
    p.setBrush(QColor("#E8C49A"))
    p.drawPath(maceta)
    for dx, dy, r in flores:
        p.setBrush(QColor("#8FC8F2"))
        p.drawEllipse(QPointF(x + dx * u, y + dy * u), r * u, r * u)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(x + dx * u, y + dy * u), r * 0.4 * u, r * 0.4 * u)
    p.restore()


def _dibujar_cafe(p, cx, fy, u, rnd):
    """Casita de madera de café sobre una nube grande. `fy` es el suelo de la casa.
    Devuelve la boca de la taza (x, y), de donde sale el vapor."""
    K = lambda v: v * u  # noqa: E731
    p.save()
    p.setPen(Qt.NoPen)

    # Nube grande que sostiene todo.
    _nube(p, cx, fy + K(150), K(210), _forma_nube(rnd, K(640), K(210), 60), 0.0)

    # Muro de madera clara con tablas y vetas, cara derecha en sombra.
    muro = QRectF(cx - K(150), fy - K(200), K(300), K(200))
    p.setBrush(QColor("#F3E1C7"))
    p.drawRect(muro)
    p.setBrush(con_alfa("#E9CFAE", 170))
    p.drawRect(QRectF(cx + K(118), fy - K(200), K(32), K(200)))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(con_alfa("#E2C6A2", 200), max(1.0, K(2))))
    for i in range(1, 10):
        y = fy - K(200) + i * K(22)
        p.drawLine(QPointF(muro.left(), y), QPointF(muro.right(), y))
    p.setPen(QPen(con_alfa("#D9B68E", 120), max(1.0, K(1.6)), Qt.SolidLine, Qt.RoundCap))
    for i in range(8):
        y = fy - K(189) + i * K(22)
        x = cx - K(140) + rnd.uniform(0, K(110))
        p.drawPath(_curva([QPointF(x, y), QPointF(x + K(40), y + K(3)),
                           QPointF(x + K(80), y - K(2)), QPointF(x + K(120), y + K(1))]))

    # Techo celeste de tejas redondeadas (filas de semicírculos recortadas al techo).
    techo = QPainterPath(QPointF(cx - K(205), fy - K(190)))
    techo.cubicTo(QPointF(cx - K(150), fy - K(240)), QPointF(cx - K(60), fy - K(300)), QPointF(cx, fy - K(330)))
    techo.cubicTo(QPointF(cx + K(60), fy - K(300)), QPointF(cx + K(150), fy - K(240)), QPointF(cx + K(205), fy - K(190)))
    techo.quadTo(QPointF(cx + K(210), fy - K(178)), QPointF(cx + K(192), fy - K(176)))
    techo.lineTo(QPointF(cx - K(192), fy - K(176)))
    techo.quadTo(QPointF(cx - K(210), fy - K(178)), QPointF(cx - K(205), fy - K(190)))
    techo.closeSubpath()
    p.setBrush(QColor("#8FC8F2"))
    p.drawPath(techo)
    p.save()
    p.setClipPath(techo)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(con_alfa("#BFE6FF", 200), max(1.0, K(2.5))))
    for fila in range(12):
        y = fy - K(330) + fila * K(20)
        desp = K(19) if fila % 2 else 0
        for c in range(-6, 7):
            x = cx + c * K(38) + desp - K(19)
            p.drawArc(QRectF(x, y, K(38), K(38)), 180 * 16, 180 * 16)
    p.restore()
    p.setPen(QPen(QColor("#6FB3E6"), max(1.0, K(6))))
    p.drawLine(QPointF(cx - K(192), fy - K(176)), QPointF(cx + K(192), fy - K(176)))
    p.setPen(Qt.NoPen)

    # Toldo de rayas celestes y blancas con borde ondulado (festones).
    y_t, n = fy - K(172), 11
    ancho_t = K(330)
    sw = ancho_t / n
    x_i = cx - K(165)
    for i in range(n):
        xs = x_i + i * sw
        p.setBrush(QColor("#8FD0FF") if i % 2 == 0 else QColor("#FFFFFF"))
        p.drawRect(QRectF(xs, y_t, sw, K(40)))
        p.drawEllipse(QRectF(xs, y_t + K(40) - sw / 2, sw, sw))

    # Ventanas redondas con marco blanco, cruz y reflejo.
    for dx in (-95, 95):
        c = QPointF(cx + K(dx), fy - K(78))
        r = K(30)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(c, r + K(6), r + K(6))
        g = QRadialGradient(QPointF(c.x() - r * 0.3, c.y() - r * 0.3), r * 1.4)
        g.setColorAt(0, QColor("#FFFFFF"))
        g.setColorAt(0.5, QColor("#BFE6FF"))
        g.setColorAt(1, QColor("#8FD0FF"))
        p.setBrush(g)
        p.drawEllipse(c, r, r)
        p.setPen(QPen(QColor("#FFFFFF"), max(1.0, K(4))))
        p.drawLine(QPointF(c.x() - r, c.y()), QPointF(c.x() + r, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - r), QPointF(c.x(), c.y() + r))
        p.setPen(Qt.NoPen)
        p.setBrush(con_alfa("#FFFFFF", 170))
        p.drawEllipse(QPointF(c.x() - r * 0.45, c.y() - r * 0.5), r * 0.18, r * 0.12)

    # Puerta en arco.
    puerta = QPainterPath(QPointF(cx - K(36), fy))
    puerta.lineTo(QPointF(cx - K(36), fy - K(80)))
    puerta.arcTo(QRectF(cx - K(36), fy - K(116), K(72), K(72)), 180, -180)
    puerta.lineTo(QPointF(cx + K(36), fy))
    puerta.closeSubpath()
    p.setBrush(QColor("#D9A877"))
    p.setPen(QPen(QColor("#FFFFFF"), max(1.0, K(5))))
    p.drawPath(puerta)
    p.setPen(QPen(con_alfa("#B98A5E", 150), max(1.0, K(2))))
    for dx in (-12, 0, 12):
        p.drawLine(QPointF(cx + K(dx), fy - K(82)), QPointF(cx + K(dx), fy))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(cx + K(24), fy - K(40)), K(3.5), K(3.5))

    # Letrero colgante con una taza dibujada, sujeto a un brazo de la pared.
    p.setPen(QPen(QColor("#B9A38A"), max(1.0, K(4))))
    p.drawLine(QPointF(cx + K(150), fy - K(150)), QPointF(cx + K(212), fy - K(150)))
    p.setPen(QPen(QColor("#B9A38A"), max(1.0, K(2))))
    p.drawLine(QPointF(cx + K(190), fy - K(150)), QPointF(cx + K(180), fy - K(96)))
    p.drawLine(QPointF(cx + K(206), fy - K(150)), QPointF(cx + K(222), fy - K(96)))
    p.setPen(QPen(QColor("#8FC8F2"), max(1.0, K(4))))
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(cx + K(176), fy - K(96), K(64), K(54)), K(10), K(10))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#8FC8F2"))
    taza = QPainterPath(QPointF(cx + K(192), fy - K(80)))
    taza.lineTo(QPointF(cx + K(222), fy - K(80)))
    taza.cubicTo(QPointF(cx + K(222), fy - K(56)), QPointF(cx + K(214), fy - K(50)), QPointF(cx + K(207), fy - K(50)))
    taza.cubicTo(QPointF(cx + K(200), fy - K(50)), QPointF(cx + K(192), fy - K(56)), QPointF(cx + K(192), fy - K(80)))
    taza.closeSubpath()
    p.drawPath(taza)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#8FC8F2"), max(1.0, K(3)), Qt.SolidLine, Qt.RoundCap))
    p.drawArc(QRectF(cx + K(216), fy - K(76), K(12), K(16)), -90 * 16, 180 * 16)
    p.drawLine(QPointF(cx + K(200), fy - K(90)), QPointF(cx + K(202), fy - K(100)))
    p.drawLine(QPointF(cx + K(210), fy - K(90)), QPointF(cx + K(212), fy - K(100)))

    # Maceta de flores azules junto a la puerta.
    _maceta(p, cx - K(190), fy + K(4), u)

    # Mesa redonda con sombrilla afuera, a la izquierda.
    _mesa(p, cx - K(300), fy + K(25), K(70), K(16), u)
    _sombrilla(p, cx - K(300), fy + K(25), u)

    # Mesa de delante: plato con rollos de canela y una taza humeante.
    xt, yt = cx + K(40), fy + K(30)
    _mesa(p, xt, yt, K(110), K(22), u)
    p.setPen(QPen(QColor("#8FD0FF"), max(1.0, K(3))))
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(xt - K(20), yt - K(6)), K(58), K(14))
    _rollo(p, xt - K(40), yt - K(14), K(26), K(16), u)
    _rollo(p, xt + K(2), yt - K(10), K(24), K(15), u)
    xc, yc = xt + K(70), yt - K(30)
    _taza_cafe(p, xc, yc, u)

    p.restore()
    return xc, yc - 6 * u


def _globo_pm(sz, cols):
    """Globo aerostático pastel: sobre con franjas, soga y cesta."""
    pm = QPixmap(max(4, int(sz)), max(4, int(sz * 1.7)))
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    try:
        q.setRenderHint(QPainter.Antialiasing, True)
        sobre = QPainterPath()
        sobre.addEllipse(QRectF(0, 0, sz, sz * 1.12))
        q.setPen(QPen(con_alfa("#B9A38A", 200), max(1.0, sz * 0.02)))
        q.drawLine(QPointF(sz * 0.22, sz * 1.0), QPointF(sz * 0.36, sz * 1.38))
        q.drawLine(QPointF(sz * 0.78, sz * 1.0), QPointF(sz * 0.64, sz * 1.38))
        q.setPen(Qt.NoPen)
        q.setBrush(QColor("#E9C9A3"))
        q.drawRoundedRect(QRectF(sz * 0.32, sz * 1.38, sz * 0.36, sz * 0.26), sz * 0.04, sz * 0.04)
        q.save()
        q.setClipPath(sobre)
        for i in range(6):
            q.setBrush(QColor(cols[i % 2]))
            q.drawRect(QRectF(i * sz / 6, 0, sz / 6, sz * 1.12))
        g = QRadialGradient(QPointF(sz * 0.4, sz * 0.35), sz * 0.75)
        g.setColorAt(0.6, con_alfa("#6FA8D6", 0))
        g.setColorAt(1, con_alfa("#6FA8D6", 70))
        q.setBrush(g)
        q.drawRect(QRectF(0, 0, sz, sz * 1.12))
        q.setBrush(con_alfa("#FFFFFF", 150))
        q.drawEllipse(QPointF(sz * 0.3, sz * 0.3), sz * 0.08, sz * 0.14)
        q.restore()
        q.setPen(QPen(con_alfa("#DCEBFA", 200), max(1.0, sz * 0.02)))
        q.setBrush(Qt.NoBrush)
        q.drawPath(sobre)
    finally:
        q.end()
    return pm


def _pajaro(p, x, y, s, t, fase):
    """Pájaro lejano: una «v» curva que aletea."""
    aleteo = 0.5 + 0.5 * math.sin(t * 6.5 + fase)
    arriba = s * (0.2 + 0.6 * aleteo)
    camino = QPainterPath(QPointF(x - s, y - arriba))
    camino.quadTo(QPointF(x - s * 0.45, y + s * 0.2), QPointF(x, y))
    camino.quadTo(QPointF(x + s * 0.45, y + s * 0.2), QPointF(x + s, y - arriba))
    p.drawPath(camino)


class EscenarioCinnamoroll(EscenarioBase):
    NOMBRE = "Cinnamoroll"
    ACENTO = "#7CC6FF"
    SEMILLA = 21

    def preparar(self):
        r = self.rnd
        # Corazoncitos que suben: (x, posición inicial, tamaño, fase, velocidad).
        self._corazones = [(r.random(), r.random(), r.uniform(0.012, 0.02), r.uniform(0, 2 * math.pi),
                            r.uniform(0.02, 0.035)) for _ in range(20)]
        # Destellos que titilan: (x, y, tamaño, fase, velocidad).
        self._destellos = [(r.random(), r.uniform(0.03, 0.97), r.uniform(0.006, 0.012),
                            r.uniform(0, 2 * math.pi), r.uniform(0.8, 2.0)) for _ in range(24)]
        # Pájaros lejanos: (x inicial, y, tamaño en fracción de h, fase, velocidad en anchos/s).
        self._pajaros = [(r.random(), r.uniform(0.08, 0.36), r.uniform(0.008, 0.014),
                          r.uniform(0, 2 * math.pi), r.uniform(0.006, 0.012)) for _ in range(5)]
        self._clave = None
        self._capas = []
        self._globos = []
        self._cafe = None
        self._taza = (0.0, 0.0)

    # ------------------------------------------------------------ recursos del tamaño actual

    def _construir(self, w, h, rnd):
        """Pre-renderiza las capas de nubes, la casita y los globos para (w, h)."""
        self._clave = (w, h)
        u = h / 1080.0

        self._capas = []
        for banda_0, banda_1, alto_f, mezcla, n_nubes, (cmin, cmax), vel in CAPAS:
            alto = alto_f * h
            ancho_nube = alto * 2.5
            top = banda_0 * h - alto * 1.15
            bot = banda_1 * h + alto * 0.25
            pm = QPixmap(2 * w, max(2, int(bot - top)))
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            try:
                q.setRenderHint(QPainter.Antialiasing, True)
                nubes = []
                for k in range(n_nubes):
                    cx = (k + rnd.uniform(0.15, 0.85)) / n_nubes * 2 * w
                    cy = rnd.uniform(banda_0, banda_1) * h - top
                    esc = rnd.uniform(0.8, 1.2)
                    nubes.append((cy, cx, esc, rnd.randint(cmin, cmax)))
                nubes.sort()
                for cy, cx, esc, n in nubes:
                    a = ancho_nube * esc
                    circ = _forma_nube(rnd, a, alto * esc, n)
                    # Copias a un lado y otro para que la capa sea periódica (sin saltos al reiniciar).
                    for dx in (-2 * w, 0, 2 * w):
                        if -a < cx + dx < 2 * w + a:
                            _nube(q, cx + dx, cy, alto * esc, circ, mezcla)
            finally:
                q.end()
            self._capas.append((pm, top, vel))

        # Casita de café sobre su nube, en una pieza propia para poder ponerla entre capas.
        cx, fy = 0.73 * w, 0.47 * h
        x0, y0 = cx - 440 * u, fy - 360 * u
        pm = QPixmap(max(2, int(880 * u)), max(2, int(540 * u)))
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        try:
            q.setRenderHint(QPainter.Antialiasing, True)
            q.translate(-x0, -y0)
            xc, yc = _dibujar_cafe(q, cx, fy, u, rnd)
        finally:
            q.end()
        self._cafe = (pm, QPointF(x0, y0))
        self._taza = (xc, yc)

        self._globos = []
        for fx, fy_g, tam, fase, cols in GLOBOS:
            sz = max(8, round(tam * h))
            self._globos.append((_globo_pm(sz, cols), fx * w, fy_g * h, fase))

    # ------------------------------------------------------------ lo que no se mueve

    def pintar_estatico(self, p, w, h):
        rnd = random.Random(83)
        self._construir(w, h, rnd)
        p.save()
        try:
            self._cielo(p, w, h)
            self._arcoiris(p, w, h)
            _mar(p, rnd, w, h, 0.50, 0.62, 260, 0.6)   # horizonte: lejano, mezclado 60 % con el cielo
            _mar(p, rnd, w, h, 0.62, 1.0, 150, 0.3)    # mar de nubes de debajo, 30 %

            # Viñeta celeste muy suave y grano fino.
            vineta = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.75)
            vineta.setColorAt(0.55, con_alfa("#6FA8D6", 0))
            vineta.setColorAt(1, con_alfa("#6FA8D6", 50))
            p.fillRect(QRectF(0, 0, w, h), vineta)
            p.setPen(QPen(con_alfa("#3D7AB0", 5), 1))
            puntos = [QPointF(rnd.uniform(0, w), rnd.uniform(0, h)) for _ in range(4000)]
            p.drawPoints(QPolygonF(puntos))
        finally:
            p.restore()

    def _sol_xy(self, w, h):
        return 0.2 * w, 0.16 * h

    def _cielo(self, p, w, h):
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor("#8FD0FF"))
        g.setColorAt(0.30, QColor("#BFE6FF"))
        g.setColorAt(0.58, QColor("#EAF7FF"))
        g.setColorAt(1, QColor("#EAF7FF"))
        p.fillRect(QRectF(0, 0, w, h), g)

        sx, sy = self._sol_xy(w, h)
        # Rayos de luz diagonales, muy suaves: degradado de blanco a transparente.
        for i, grados in enumerate((24, 31, 38, 46, 53)):
            a = math.radians(grados)
            dx, dy = math.cos(a), math.sin(a)
            nx, ny = -dy, dx
            largo = h * 1.5
            ancho0 = h * 0.004
            ancho1 = h * (0.035 + 0.01 * (i % 2))
            camino = QPainterPath(QPointF(sx + nx * ancho0, sy + ny * ancho0))
            camino.lineTo(QPointF(sx + dx * largo + nx * ancho1, sy + dy * largo + ny * ancho1))
            camino.lineTo(QPointF(sx + dx * largo - nx * ancho1, sy + dy * largo - ny * ancho1))
            camino.lineTo(QPointF(sx - nx * ancho0, sy - ny * ancho0))
            camino.closeSubpath()
            rg = QLinearGradient(QPointF(sx, sy), QPointF(sx + dx * largo, sy + dy * largo))
            rg.setColorAt(0, con_alfa("#FFFFFF", 35))
            rg.setColorAt(1, con_alfa("#FFFFFF", 0))
            p.fillPath(camino, rg)

        # Sol suave, blanco cálido, arriba a la izquierda.
        self.brillo(p, sx, sy, 0.4 * h, "#FFF6DA", alfa=150)
        self.brillo(p, sx, sy, 0.07 * h, "#FFFFFF", alfa=255)

    def _arcoiris(self, p, w, h):
        """Arcoíris pastel muy tenue a la izquierda: arcos concéntricos de cuarto de círculo."""
        cx, cy = 0.0, 0.78 * h
        p.save()
        p.setBrush(Qt.NoBrush)
        for k, color in enumerate(ARCOIRIS):
            radio = (0.52 - k * 0.026) * h
            p.setPen(QPen(con_alfa(color, 30), 0.016 * h, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(QRectF(cx - radio, cy - radio, 2 * radio, 2 * radio), 0, 90 * 16)
        p.restore()

    # ------------------------------------------------------------ lo que se mueve

    def pintar_animado(self, p, w, h, t):
        if self._clave != (w, h):
            self._construir(w, h, random.Random(83))
        p.save()
        try:
            # Globos lejanos: suben y bajan despacio.
            for pm, x0, y0, fase in self._globos:
                x = x0 + math.sin(t * 0.2 + fase) * 0.012 * w
                y = y0 + math.sin(t * 0.6 + fase) * 0.014 * h
                p.drawPixmap(QPointF(x - pm.width() / 2, y - pm.height() * 0.4), pm)

            self._capa(p, 0, w, t)
            self._capa(p, 1, w, t)
            pm_cafe, xy = self._cafe
            p.drawPixmap(xy, pm_cafe)
            self._capa(p, 2, w, t)

            self._vapor(p, h, t)
            self._dibujar_pajaros(p, w, h, t)
            self._corazones_destellos(p, w, h, t)
            self._sol(p, w, h, t)

            # Ondas de la música, celestes, sobre el mar de nubes.
            self.ondas(p, base_y=0.62 * h, ancho=w, alto_max=0.10 * h, color=self.acento())
        finally:
            p.restore()

    def _capa(self, p, idx, w, t):
        """Capa de nubes desplazada en paralaje; la pieza es periódica con período 2w."""
        pm, top, vel = self._capas[idx]
        periodo = 2 * w
        x0 = -((vel * w * t) % periodo)
        p.drawPixmap(QPointF(x0, top), pm)
        p.drawPixmap(QPointF(x0 + periodo, top), pm)

    def _vapor(self, p, h, t):
        """Tres cintas de vapor que suben desde la taza."""
        x0, y0 = self._taza
        u = h / 1080.0
        p.setBrush(Qt.NoBrush)
        for k in range(3):
            s = (t * 0.3 + k / 3.0) % 1.0
            pts = []
            for i in range(6):
                f = i / 5
                y = y0 - (s * 60 + f * 100) * u
                x = x0 + math.sin(f * 4.2 + t * 1.6 + k * 2.1) * 10 * u
                pts.append(QPointF(x, y))
            p.setPen(QPen(con_alfa("#FFFFFF", 200 * (1 - s)), max(1.2, 3 * u), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(_curva(pts))

    def _dibujar_pajaros(self, p, w, h, t):
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(con_alfa("#5E8FB8", 190), max(1.2, 0.0035 * h), Qt.SolidLine, Qt.RoundCap))
        for fx, fy, sf, fase, vel in self._pajaros:
            x = ((fx + vel * t) % 1.2 - 0.1) * w
            y = fy * h + math.sin(t * 0.5 + fase) * 0.006 * h
            _pajaro(p, x, y, sf * h, t, fase)

    def _corazones_destellos(self, p, w, h, t):
        p.setPen(Qt.NoPen)
        for fx, fy, tam, fase, vel in self._destellos:
            titileo = 0.5 + 0.5 * math.sin(t * vel + fase)
            p.fillPath(_destello(fx * w, fy * h, tam * h * (0.4 + 0.6 * titileo)),
                       con_alfa("#FFFFFF", 120 + 130 * titileo))
        for fx, pos, tam, fase, vel in self._corazones:
            u = (pos + vel * t) % 1.0
            x = fx * w + math.sin(t * 0.6 + fase) * 0.015 * w
            y = h * (1.05 - 1.15 * u)
            alfa = 200 * min(1.0, 4 * u, 4 * (1 - u))
            p.fillPath(_corazon(x, y, tam * h), con_alfa(CELESTE, alfa))

    def _sol(self, p, w, h, t):
        """El sol respira con la energía de la música."""
        sx, sy = self._sol_xy(w, h)
        resp = 0.5 + 0.5 * math.sin(t * 1.2)
        e = self.energia()
        self.brillo(p, sx, sy, h * (0.09 + 0.02 * resp + 0.03 * e), "#FFFFFF",
                    alfa=int(120 + 60 * resp + 60 * e))
