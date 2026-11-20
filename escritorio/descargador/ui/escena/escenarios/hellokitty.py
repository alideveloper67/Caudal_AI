# -*- coding: utf-8 -*-
"""Escenario «Hello Kitty»: un picnic en un jardín de cuento al atardecer suave, con estética Sanrio clásica.

Solo estética: rojo, blanco y rosa, lazos, manzanas, flores, vichy, mimbre, tartas y tacitas. No dibuja ningún
personaje ni su cara.

Capas de profundidad (de lejos a cerca): cielo con nubes y sol, colinas lejanas (mezcladas con el cielo al 55 %),
una casita roja con techo de tejas, colinas medias (30 %), pradera con hierba y flores, dos árboles de manzanas,
mantel vichy en perspectiva y, al frente, la cesta con el gran lazo, una tarta de fresa, tacitas y galletas.

Lo estático se pinta una vez (`pintar_estatico`). Lo animado (pétalos y manzanitas que caen, mariposas, hierba que
se mece, lazo que late, sol que respira y ondas de la música) usa sprites ya pintados (`pintar_animado`).
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient, QTransform)

from descargador.ui.escena.escenarios.base import EscenarioBase, mezclar

# ---------------------------------------------------------------- paleta
CIELO_ARRIBA = "#FFD6DE"
CIELO_MEDIO = "#FFE9E0"
CIELO_HORIZONTE = "#FFF6EA"
NUBE_SOMBRA = "#F7B9C8"
PRADERA_CLARA = "#B9E6A8"
PRADERA_OSCURA = "#8CCB7E"
VERDE_MEDIO = "#7CC27E"
VERDE_OSCURO = "#5DAA63"
VERDE_CLARO = "#A7DCA0"
COPA_SOMBRA = "#4E9A57"
COPA_LUZ = "#B5E5A8"
TIERRA_CLARA = "#EAD6AE"
ROJO = "#E5243B"
ROJO_OSCURO = "#B81B2E"
ROSA = "#FFB3C7"
ROSA_FUERTE = "#FF8FA3"
MIMBRE_CLARO = "#F2CF9C"
MIMBRE = "#D9A66B"
MIMBRE_OSCURO = "#9C6434"

# ---------------------------------------------------------------- geometría (fracciones de w y h)
HORIZONTE = 0.55
SOL = (0.72, 0.41, 0.035)               # x de w, y de h, radio de h
CASA_X = 0.72
ARBOL_A = (0.15, 0.665, 0.13, 12)       # x de w, base de h, radio de copa de h, manzanas
ARBOL_B = (0.87, 0.64, 0.10, 8)
CESTA_CX, CESTA_TOP, CESTA_BOT, CESTA_BW = 0.22, 0.78, 0.975, 0.15
TARTA = (0.60, 0.86, 0.15, 0.10)        # centro x de w, base de h, ancho de w, alto de h
TAZAS = ((0.79, 0.86, 0.030), (0.885, 0.905, 0.026))   # x de w, base de h, radio de la taza (de w)
GALLETAS = ((0.40, 0.87), (0.455, 0.905), (0.345, 0.92))
NUBES = ((0.12, 0.17, 0.20), (0.46, 0.10, 0.17), (0.86, 0.20, 0.22), (0.30, 0.31, 0.11), (0.60, 0.28, 0.10))
MANTEL = ((0.28, 0.66), (0.72, 0.66), (1.06, 0.94), (-0.06, 0.94))   # TL, TR, BR, BL (fracciones de w, h)
CAMINO = ((0.50, 0.67), (0.58, 0.62), (0.66, 0.58), (0.72, 0.535))   # bezier de tierra hacia la casita
ARBUSTOS = ((0.40, 0.62, 0.030), (0.62, 0.615, 0.026))             # x de w, base de h, radio de h
MARIPOSAS = ((0.30, 0.44, 0.0, "#FFFFFF"), (0.63, 0.36, 2.1, ROSA), (0.50, 0.60, 4.0, "#FFFFFF"),
             (0.80, 0.50, 5.2, ROSA))

_SEMILLA = 73
_LAZO_PASOS = 6                          # fotogramas pre-renderizados del lazo (escala 1..1.05)


def _cresta_lejana(xf):
    return HORIZONTE - 0.06 * (0.5 + 0.5 * math.sin(4.2 * xf + 0.4)) - 0.012 * math.sin(9.0 * xf)


def _cresta_media(xf):
    return HORIZONTE + 0.005 - 0.03 * (0.5 + 0.5 * math.sin(3.1 * xf + 2.0)) + 0.008 * math.sin(7.0 * xf + 0.3)


def _pradera(xf):
    return _cresta_media(xf) + 0.035 + 0.006 * math.sin(5.5 * xf + 1.1)


def _ancla_cesta(w, h):
    """Centro del lazo: justo sobre el asa de la cesta (la curva del asa pasa por su punto medio)."""
    bh = (CESTA_BOT - CESTA_TOP) * h
    return CESTA_CX * w, CESTA_TOP * h + 0.005 * h - 0.3375 * bh


def _camino_colina(fn, w, h, fondo):
    camino = QPainterPath(QPointF(0, fondo * h))
    for i in range(81):
        xf = i / 80.0
        camino.lineTo(QPointF(xf * w, fn(xf) * h))
    camino.lineTo(QPointF(w, fondo * h))
    camino.closeSubpath()
    return camino


# ---------------------------------------------------------------- formas reutilizables

def _lazo_forma():
    """Lóbulos, colas, brillo, pliegue y nudo del lazo, en unidades de escala 1 (centro en 0,0)."""
    lobulo = QPainterPath(QPointF(0, 0))
    lobulo.cubicTo(QPointF(0.22, -0.52), QPointF(0.92, -0.46), QPointF(0.86, 0.02))
    lobulo.cubicTo(QPointF(0.84, 0.42), QPointF(0.22, 0.48), QPointF(0, 0))
    lobulo.closeSubpath()
    cola = QPainterPath(QPointF(0.0, 0.05))
    cola.cubicTo(QPointF(0.20, 0.25), QPointF(0.42, 0.42), QPointF(0.36, 0.62))
    cola.lineTo(QPointF(0.22, 0.58))
    cola.cubicTo(QPointF(0.26, 0.40), QPointF(0.10, 0.25), QPointF(-0.02, 0.12))
    cola.closeSubpath()
    espejo = QTransform().scale(-1, 1)
    cuerpo = QPainterPath(lobulo)
    cuerpo.addPath(cola)
    cuerpo.addPath(espejo.map(lobulo))
    cuerpo.addPath(espejo.map(cola))
    brillo_i = QPainterPath()
    brillo_i.addEllipse(QRectF(0.30, -0.36, 0.22, 0.12))
    brillo = QPainterPath(brillo_i)
    brillo.addPath(espejo.map(brillo_i))
    pliegue = QPainterPath(QPointF(0.12, 0.02))
    pliegue.quadTo(QPointF(0.46, -0.20), QPointF(0.80, -0.08))
    pliegue.addPath(espejo.map(pliegue))
    nudo = QPainterPath()
    nudo.addEllipse(QPointF(0, 0), 0.14, 0.14)
    return cuerpo, nudo, brillo, pliegue


def _dibujar_lazo(p, k, sombra=True):
    """Lazo rojo centrado en el origen, a escala `k` px por unidad."""
    cuerpo, nudo, brillo, pliegue = _lazo_forma()
    p.save()
    p.scale(k, k)
    if sombra:
        p.save()
        p.translate(0.035, 0.06)
        p.fillPath(cuerpo, QColor(70, 0, 20, 90))
        p.restore()
    g = QLinearGradient(-0.9, -0.5, 0.9, 0.6)
    g.setColorAt(0.0, QColor("#FF6A7A"))
    g.setColorAt(0.5, QColor(ROJO))
    g.setColorAt(1.0, QColor(ROJO_OSCURO))
    p.fillPath(cuerpo, QBrush(g))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(120, 10, 28, 150), 0.045, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(pliegue)
    p.setPen(Qt.NoPen)
    p.fillPath(brillo, QColor(255, 255, 255, 130))
    gn = QRadialGradient(-0.04, -0.04, 0.17, -0.06, -0.06)
    gn.setColorAt(0.0, QColor("#FF6A7A"))
    gn.setColorAt(1.0, QColor(ROJO_OSCURO))
    p.fillPath(nudo, QBrush(gn))
    p.restore()


def _galleta(p, x, y, k, angulo):
    """Galleta con forma de lazo: masa dorada, glaseado rosa y perlitas blancas."""
    cuerpo, _nudo, _brillo, _pliegue = _lazo_forma()
    p.save()
    p.translate(x, y)
    p.rotate(angulo)
    p.scale(k, k)
    g = QLinearGradient(-0.9, -0.5, 0.9, 0.6)
    g.setColorAt(0.0, QColor("#F8D49A"))
    g.setColorAt(1.0, QColor("#E9A95C"))
    p.setPen(QPen(QColor("#C98B4A"), 0.05))
    p.setBrush(QBrush(g))
    p.drawPath(cuerpo)
    p.save()
    p.scale(0.74, 0.74)
    p.setPen(Qt.NoPen)
    p.fillPath(cuerpo, QColor(ROSA_FUERTE))
    p.restore()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    for dx, dy in ((-0.30, -0.10), (0.30, -0.12), (0.0, 0.20), (-0.42, 0.18), (0.42, 0.20)):
        p.drawEllipse(QPointF(dx, dy), 0.05, 0.05)
    p.restore()


def _manzana(p, x, y, rad):
    """Manzana roja brillante con brillo blanco, tallo y hojita."""
    fx, fy = x - 0.35 * rad, y - 0.35 * rad
    g = QRadialGradient(fx, fy, rad * 1.9, fx, fy)
    g.setColorAt(0.0, QColor("#FF8A96"))
    g.setColorAt(0.45, QColor(ROJO))
    g.setColorAt(0.9, QColor("#A5162A"))
    g.setColorAt(1.0, QColor("#8A1224"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(x, y), rad * 1.05, rad * 0.95)
    p.setBrush(QColor(255, 255, 255, 215))
    p.drawEllipse(QPointF(x - 0.42 * rad, y - 0.38 * rad), rad * 0.26, rad * 0.16)
    p.setPen(QPen(QColor("#6B4A2B"), max(1.0, rad * 0.16), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(x, y - rad * 0.85), QPointF(x + rad * 0.12, y - rad * 1.45))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(VERDE_MEDIO))
    p.save()
    p.translate(x + rad * 0.35, y - rad * 1.3)
    p.rotate(-25)
    p.drawEllipse(QPointF(0, 0), rad * 0.42, rad * 0.2)
    p.restore()


def _hoja(p, x, y, angulo, color, h):
    """Hojita elíptica suelta."""
    p.save()
    p.translate(x, y)
    p.rotate(angulo)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QPointF(0, 0), 0.010 * h, 0.0052 * h)
    p.restore()


def _arbusto(p, rnd, w, h, arbusto):
    """Arbusto redondo de tres tonos con matas de flores blancas y rosas."""
    xf, bf, Rf = arbusto
    x, base, R = xf * w, bf * h, Rf * h
    cy = base - R * 0.9
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(60, 90, 40, 60))
    p.drawEllipse(QPointF(x + 0.3 * R, base), R * 1.1, R * 0.22)
    for ox, oy, color in ((-0.3, 0.0, COPA_SOMBRA), (0.3, -0.1, VERDE_MEDIO), (-0.1, -0.35, COPA_LUZ)):
        p.setBrush(QColor(color))
        for _ in range(12):
            ang = rnd.uniform(0, math.tau)
            rad = math.sqrt(rnd.random())
            px = x + ox * R + math.cos(ang) * rad * R * 0.5
            py = cy + oy * R + math.sin(ang) * rad * R * 0.42
            rr = R * rnd.uniform(0.35, 0.5)
            p.drawEllipse(QPointF(px, py), rr, rr)
    for _ in range(22):
        ang = rnd.uniform(0, math.tau)
        rad = math.sqrt(rnd.random())
        px = x + math.cos(ang) * rad * R * 0.85
        py = cy + math.sin(ang) * rad * R * 0.7
        p.setBrush(QColor("#FFFFFF") if rnd.random() < 0.5 else QColor(ROSA))
        p.drawEllipse(QPointF(px, py), R * 0.05, R * 0.05)


def _camino_tierra(p, w, h):
    """Camino curvo de tierra clara que sale de la cesta hacia la casita, con guijarros."""
    pts = [(xf * w, yf * h) for xf, yf in CAMINO]
    p.setBrush(Qt.NoBrush)
    n = 14
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        tramo = QPainterPath(QPointF(*_bezier(pts, t0)))
        tramo.lineTo(QPointF(*_bezier(pts, t1)))
        p.setPen(QPen(QColor(TIERRA_CLARA), h * (0.006 + 0.03 * (1 - t0)), Qt.SolidLine, Qt.RoundCap))
        p.drawPath(tramo)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 245, 225, 150))
    for i in range(0, n, 2):
        px, py = _bezier(pts, (i + 0.5) / n)
        p.drawEllipse(QPointF(px, py - 0.004 * h), 0.004 * h, 0.0025 * h)


def _bezier(pts, t):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
    u = 1 - t
    return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3,
            u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)


def _fresa(p, x, y, rad, angulo):
    """Fresa con semillas y cáliz verde."""
    p.save()
    p.translate(x, y)
    p.rotate(angulo)
    cuerpo = QPainterPath(QPointF(0, -rad * 0.85))
    cuerpo.cubicTo(QPointF(rad * 0.95, -rad * 0.95), QPointF(rad * 0.85, rad * 0.5), QPointF(0, rad * 1.05))
    cuerpo.cubicTo(QPointF(-rad * 0.85, rad * 0.5), QPointF(-rad * 0.95, -rad * 0.95), QPointF(0, -rad * 0.85))
    g = QLinearGradient(0, -rad, 0, rad)
    g.setColorAt(0.0, QColor("#FF6B7A"))
    g.setColorAt(0.6, QColor(ROJO))
    g.setColorAt(1.0, QColor(ROJO_OSCURO))
    p.setPen(Qt.NoPen)
    p.fillPath(cuerpo, QBrush(g))
    p.setBrush(QColor(255, 242, 176, 220))
    for fx, fy in ((-0.45, -0.35), (0.0, -0.25), (0.45, -0.35), (-0.25, 0.2), (0.25, 0.2), (0.0, 0.6)):
        p.drawEllipse(QPointF(fx * rad, fy * rad), rad * 0.07, rad * 0.1)
    p.setBrush(QColor(VERDE_MEDIO))
    for a in (-55, 0, 55):
        p.save()
        p.translate(0, -rad * 0.85)
        p.rotate(a)
        p.drawEllipse(QPointF(0, -rad * 0.22), rad * 0.14, rad * 0.3)
        p.restore()
    p.restore()


def _cilindro(cx, yb, rx, ry, alto):
    """Cuerpo cilíndrico de altura `alto` cuya base es la mitad frontal de la elipse en `yb`."""
    cuerpo = QPainterPath()
    cuerpo.addRect(QRectF(cx - rx, yb - alto, 2 * rx, alto))
    cuerpo = cuerpo.united(_elipse(cx, yb - alto, rx, ry))
    media = QPainterPath(QPointF(cx - rx, yb))
    media.arcTo(QRectF(cx - rx, yb - ry, 2 * rx, 2 * ry), 180, 180)
    media.closeSubpath()
    return cuerpo.united(media)


def _elipse(cx, cy, rx, ry):
    camino = QPainterPath()
    camino.addEllipse(QPointF(cx, cy), rx, ry)
    return camino


def _tarta(p, cx, yb, cw, ch):
    """Tarta de fresa con nata: plato, bizcocho, dos capas de nata, glaseado con gotas y fresas arriba."""
    rx = cw / 2.0
    ry = rx * 0.24
    yt = yb - ch
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(ROSA))
    p.drawEllipse(QPointF(cx, yb + ry * 0.2), rx * 1.36, ry * 1.42)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(cx, yb + ry * 0.2), rx * 1.26, ry * 1.26)
    # bizcocho
    g = QLinearGradient(cx - rx, 0, cx + rx, 0)
    g.setColorAt(0.0, QColor("#F8D9A8"))
    g.setColorAt(0.5, QColor("#F0BE7E"))
    g.setColorAt(1.0, QColor("#F8D9A8"))
    p.setBrush(QBrush(g))
    p.drawPath(_cilindro(cx, yb, rx, ry, ch))
    # capas de nata con borde rosa
    for frac in (0.36, 0.70):
        yb1 = yb - ch * frac
        hb = ch * 0.12
        p.setBrush(QColor("#FFF8FB"))
        p.drawPath(_cilindro(cx, yb1, rx * 1.005, ry * 1.005, hb))
        borde = QPainterPath(QPointF(cx - rx, yb1))
        borde.arcTo(QRectF(cx - rx, yb1 - ry, 2 * rx, 2 * ry), 180, 180)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(ROSA_FUERTE), max(1.0, ch * 0.014)))
        p.drawPath(borde)
        p.setPen(Qt.NoPen)
    # glaseado de nata en la tapa, con gotas
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(cx, yt), rx * 1.0, ry * 1.0)
    rd = rx * 0.09
    for k in range(13):
        a = math.pi * k / 12.0
        x = cx + math.cos(a) * rx * 0.98
        y0 = yt + ry * math.sin(a)
        largo = ch * (0.04 + 0.05 * ((k * 37) % 5) / 4.0)
        p.drawRect(QRectF(x - rd, y0 - 1, 2 * rd, largo + 1))
        p.drawEllipse(QPointF(x, y0 + largo), rd, rd)
    # fresas sobre la tarta
    for fx, fy, ang in ((-0.55, 0.10, -20), (-0.20, -0.12, 15), (0.15, 0.12, -5), (0.50, -0.05, 25), (0.0, 0.42, 0)):
        _fresa(p, cx + fx * rx, yt + fy * ry, rx * 0.13, ang)


def _taza(p, x, yb, rw):
    """Tacita de té rosa con platito; `yb` es la línea del platito."""
    ch = rw * 2.1
    top = yb - ch
    base_c = yb - 0.22 * rw
    p.setPen(QPen(QColor(ROSA), max(1.0, rw * 0.06)))
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(x, yb), 1.65 * rw, 0.36 * rw)
    asa = QPainterPath(QPointF(x + rw * 0.92, top + 0.25 * ch))
    asa.cubicTo(QPointF(x + 1.5 * rw, top + 0.2 * ch), QPointF(x + 1.5 * rw, top + 0.75 * ch),
                QPointF(x + 0.88 * rw, top + 0.72 * ch))
    p.setPen(QPen(QColor(ROSA_FUERTE), rw * 0.30, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawPath(asa)
    p.setPen(QPen(QColor("#FFFFFF"), rw * 0.14, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(asa)
    cuerpo = QPainterPath(QPointF(x - rw, top))
    cuerpo.cubicTo(QPointF(x - rw, top + 0.6 * (base_c - top)), QPointF(x - 0.7 * rw, base_c), QPointF(x, base_c))
    cuerpo.cubicTo(QPointF(x + 0.7 * rw, base_c), QPointF(x + rw, top + 0.6 * (base_c - top)), QPointF(x + rw, top))
    cuerpo.closeSubpath()
    g = QLinearGradient(x - rw, 0, x + rw, 0)
    g.setColorAt(0.0, QColor("#FFFFFF"))
    g.setColorAt(0.5, QColor("#FFE6EE"))
    g.setColorAt(1.0, QColor("#F9CCD8"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawPath(cuerpo)
    p.save()
    p.setClipPath(cuerpo)
    p.setBrush(QColor(ROSA_FUERTE))
    p.drawRect(QRectF(x - rw, top + 0.28 * ch, 2 * rw, 0.12 * ch))
    p.restore()
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(x, top), rw, 0.24 * rw)
    p.setBrush(QColor("#F3A2B8"))
    p.drawEllipse(QPointF(x, top + 0.01 * rw), 0.84 * rw, 0.19 * rw)


def _casita(p, x, yb, h):
    """Casita roja con techo de tejas, ventana y chimenea, a lo lejos (sus colores se mezclan con el cielo)."""
    def c(hexcolor):
        return mezclar(QColor(hexcolor), QColor(CIELO_HORIZONTE), 0.35)
    ancho = 0.05 * h
    alto = 0.032 * h
    techo = 0.03 * h
    apice = yb - alto - techo
    p.setPen(Qt.NoPen)
    p.setBrush(c(ROJO))
    p.drawRect(QRectF(x - ancho / 2, yb - alto, ancho, alto))
    tejado = QPainterPath(QPointF(x - ancho * 0.62, yb - alto))
    tejado.lineTo(QPointF(x + ancho * 0.62, yb - alto))
    tejado.lineTo(QPointF(x, apice))
    tejado.closeSubpath()
    p.setBrush(c(ROJO_OSCURO))
    p.drawPath(tejado)
    p.setPen(QPen(c("#E8707E"), max(1.0, h * 0.0012)))
    for k in range(1, 4):
        yk = apice + techo * k / 4.0
        mitad = ancho * 0.62 * (yk - apice) / techo
        p.drawLine(QPointF(x - mitad, yk), QPointF(x + mitad, yk))
    p.setPen(Qt.NoPen)
    p.setBrush(c("#9C1A2A"))
    p.drawRect(QRectF(x + ancho * 0.18, apice + techo * 0.25, ancho * 0.1, techo * 0.6))
    p.setBrush(c("#FFFFFF"))
    p.drawRect(QRectF(x - ancho * 0.34, yb - alto * 0.72, ancho * 0.26, alto * 0.30))
    p.setBrush(c(ROSA))
    p.drawRect(QRectF(x - ancho * 0.30, yb - alto * 0.68, ancho * 0.18, alto * 0.22))
    p.setBrush(c("#B81B2E"))
    p.drawRect(QRectF(x + ancho * 0.08, yb - alto * 0.52, ancho * 0.20, alto * 0.52))


def _nube(p, rnd, w, h, cx, base, cw):
    """Nube de 20 a 40 círculos, con base aplanada: sombra rosa abajo y blanco arriba."""
    x0, yb, ancho = cx * w, base * h, cw * w
    circulos = []
    for _ in range(rnd.randint(20, 40)):
        dx = rnd.uniform(-0.5, 0.5)
        f = 1.0 - (abs(dx) * 2.0) ** 1.6 * 0.75
        rad = rnd.uniform(0.10, 0.20) * ancho * (0.7 + 0.3 * f)
        y = yb - rad * 0.35 - rnd.uniform(0.0, 0.24) * ancho * f
        circulos.append((x0 + dx * ancho, y, rad))
    dy = 0.014 * h
    # sombra: degradado que pasa de transparente arriba a rosa en la base (sin franja sólida)
    sombra = QLinearGradient(0, yb - ancho * 0.22, 0, yb + 0.02 * h)
    sombra.setColorAt(0.0, QColor(247, 185, 200, 0))
    sombra.setColorAt(0.55, QColor(247, 185, 200, 170))
    sombra.setColorAt(1.0, QColor(247, 185, 200, 255))
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(sombra))
    for x, y, rad in circulos:
        p.drawEllipse(QPointF(x, y), rad, rad)
    p.setBrush(QColor("#FFFFFF"))
    for x, y, rad in circulos:
        p.drawEllipse(QPointF(x, y - dy), rad * 0.97, rad * 0.97)
    p.restore()


def _arbol(p, rnd, w, h, arbol):
    """Árbol de manzanas: tronco ahusado con corteza, ramas, copa de 75-90 círculos en 3 tonos y manzanas."""
    xf, bf, Rf, n_manzanas = arbol
    x, base, R = xf * w, bf * h, Rf * h
    cy = base - 2.0 * R
    p.setPen(Qt.NoPen)
    sombra = QPainterPath()
    sombra.addEllipse(QPointF(x + 0.6 * R, base), R * 0.9, R * 0.16)
    p.fillPath(sombra, QColor(60, 90, 40, 70))
    ytop = cy + 0.4 * R
    tb, tt = 0.018 * h, 0.010 * h
    # ramas (detrás de la copa)
    for sgn in (-1, 1):
        rama = QPainterPath(QPointF(x, ytop + 0.05 * R))
        rama.quadTo(QPointF(x + sgn * 0.45 * R, ytop - 0.15 * R), QPointF(x + sgn * 0.75 * R, cy + 0.2 * R))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#8A5A3C"), max(2.0, 0.012 * h), Qt.SolidLine, Qt.RoundCap))
        p.drawPath(rama)
    # tronco ahusado
    tronco = QPainterPath(QPointF(x - tb, base))
    tronco.cubicTo(QPointF(x - tb * 0.7, base - (base - ytop) * 0.45), QPointF(x - tt, ytop + (base - ytop) * 0.2),
                   QPointF(x - tt, ytop))
    tronco.lineTo(QPointF(x + tt, ytop))
    tronco.cubicTo(QPointF(x + tt, ytop + (base - ytop) * 0.2), QPointF(x + tb * 0.7, base - (base - ytop) * 0.45),
                   QPointF(x + tb, base))
    tronco.closeSubpath()
    g = QLinearGradient(x - tb, 0, x + tb, 0)
    g.setColorAt(0.0, QColor("#B98062"))
    g.setColorAt(0.45, QColor("#8A5A3C"))
    g.setColorAt(1.0, QColor("#5E3A24"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawPath(tronco)
    # corteza: líneas finas
    p.setBrush(Qt.NoBrush)
    for _ in range(6):
        fx = rnd.uniform(-0.7, 0.7)
        y0 = rnd.uniform(base - 0.5 * (base - ytop), base - 0.02 * h)
        y1 = y0 - rnd.uniform(0.15, 0.4) * (base - ytop)
        xa = x + fx * tb * 0.8
        xb = x + fx * tt * 0.8 + rnd.uniform(-1.0, 1.0) * 0.002 * h
        corteza = QPainterPath(QPointF(xa, y0))
        corteza.quadTo(QPointF((xa + xb) / 2 + 0.002 * h, (y0 + y1) / 2), QPointF(xb, y1))
        p.setPen(QPen(QColor(60, 34, 20, 150), max(1.0, 0.0012 * h)))
        p.drawPath(corteza)
    p.setPen(Qt.NoPen)
    # copa: 3 racimos; cada uno con 3 tonos según su propia luz (arriba-izquierda) y sombra (abajo-derecha)
    for ox, oy in ((-0.45, -0.1), (0.42, -0.22), (0.0, 0.32)):
        rcx, rcy, rr_c = x + ox * R, cy + oy * R, R * 0.62
        grupos = ([], [], [])
        for _ in range(rnd.randint(26, 32)):
            ang = rnd.uniform(0, math.tau)
            rad = math.sqrt(rnd.random())
            px = rcx + math.cos(ang) * rad * rr_c
            py = rcy + math.sin(ang) * rad * rr_c * 0.9
            rr = R * rnd.uniform(0.20, 0.32)
            s = ((px - rcx) * -0.6 + (py - rcy) * -0.8) / rr_c
            idx = 2 if s > 0.30 else (1 if s > -0.22 else 0)
            grupos[idx].append((px, py, rr))
        for grupo, color in zip(grupos, (COPA_SOMBRA, VERDE_MEDIO, COPA_LUZ)):
            p.setBrush(QColor(color))
            for px, py, rr in grupo:
                p.drawEllipse(QPointF(px, py), rr, rr)
    # hojitas sueltas en el borde
    for _ in range(20):
        ang = rnd.uniform(0, math.tau)
        px = x + math.cos(ang) * R * rnd.uniform(0.92, 1.12)
        py = cy + math.sin(ang) * R * rnd.uniform(0.82, 1.0)
        _hoja(p, px, py, rnd.uniform(0, 360), rnd.choice((VERDE_MEDIO, COPA_LUZ, COPA_SOMBRA)), h)
    # manzanas de tamaños variados; algunas medio tapadas por hojas
    apples = []
    for _ in range(n_manzanas):
        ang = rnd.uniform(0, math.tau)
        rad = math.sqrt(rnd.uniform(0.05, 0.8))
        ax = x + math.cos(ang) * rad * R * 0.92
        ay = cy + math.sin(ang) * rad * R * 0.8 + 0.12 * R
        ar = h * rnd.uniform(0.008, 0.015)
        apples.append((ax, ay, ar))
        _manzana(p, ax, ay, ar)
    for ax, ay, ar in apples[::2]:
        _hoja(p, ax + ar * 0.6, ay - ar * 0.9, rnd.uniform(-60, 60), COPA_LUZ, h)
    for ax, ay, ar in apples[1::3]:
        _hoja(p, ax - ar * 0.7, ay + ar * 0.2, rnd.uniform(-60, 60), VERDE_MEDIO, h)


def _pasto(p, rnd, w, h):
    """2500 briznas en tres verdes, más grandes cerca del frente."""
    caminos = [QPainterPath(), QPainterPath(), QPainterPath()]
    for _ in range(2500):
        xf = rnd.random()
        top = _pradera(xf)
        yf = top + (1.0 - top) * rnd.random()
        d = max(0.0, min(1.0, (yf - HORIZONTE) / (1.0 - HORIZONTE)))
        alt = h * (0.006 + 0.016 * d) * rnd.uniform(0.6, 1.3)
        lean = alt * rnd.uniform(-0.5, 0.5)
        x, y = xf * w, yf * h
        u = rnd.random()
        k = 0 if u < 0.5 else (1 if u < 0.8 else 2)
        caminos[k].moveTo(QPointF(x, y))
        caminos[k].quadTo(QPointF(x + lean * 0.2, y - alt * 0.55), QPointF(x + lean, y - alt))
    p.setBrush(Qt.NoBrush)
    for camino, color in zip(caminos, (VERDE_MEDIO, VERDE_OSCURO, VERDE_CLARO)):
        p.setPen(QPen(QColor(color), max(1.0, h * 0.0018), Qt.SolidLine, Qt.RoundCap))
        p.drawPath(camino)
    p.setPen(Qt.NoPen)


def _flores(p, rnd, w, h):
    """300 flores: margaritas blancas (5-8 pétalos) y florecitas rosas; más densas y pequeñas hacia el fondo."""
    margaritas = QPainterPath()
    margaritas_c = QPainterPath()
    rosas = QPainterPath()
    rosas_c = QPainterPath()
    petalo_m = _elipse(0, -0.55, 0.20, 0.45)
    petalo_r = _elipse(0, -0.50, 0.26, 0.36)
    # 15 matas de 20 flores: cada una agrupada alrededor de su centro, más pequeña y apretada hacia el fondo
    puntos = []
    for _ in range(15):
        xc = rnd.uniform(0.02, 0.98)
        yc = _pradera(xc) + (1.0 - _pradera(xc)) * (rnd.random() ** 1.6)
        d0 = max(0.0, min(1.0, (yc - HORIZONTE) / (1.0 - HORIZONTE)))
        sx = w * (0.012 + 0.03 * d0)
        sy = h * (0.006 + 0.02 * d0)
        for _ in range(20):
            x = min(w * 0.995, max(0.0, xc * w + rnd.gauss(0, sx)))
            y = max(_pradera(x / w) * h + 2, min(h * 0.995, yc * h + rnd.gauss(0, sy)))
            puntos.append((x, y))
    for x, y in puntos:
        yf = y / h
        d = max(0.0, min(1.0, (yf - HORIZONTE) / (1.0 - HORIZONTE)))
        s = h * (0.0035 + 0.011 * d) * rnd.uniform(0.85, 1.15)
        ang0 = rnd.uniform(0, 360)
        if rnd.random() < 0.6:
            n = rnd.randint(5, 8)
            for k in range(n):
                tr = QTransform().translate(x, y).rotate(ang0 + k * 360.0 / n).scale(s, s)
                margaritas.addPath(tr.map(petalo_m))
            margaritas_c.addEllipse(QPointF(x, y), 0.2 * s, 0.2 * s)
        else:
            for k in range(5):
                tr = QTransform().translate(x, y).rotate(ang0 + k * 72.0).scale(s * 0.85, s * 0.85)
                rosas.addPath(tr.map(petalo_r))
            rosas_c.addEllipse(QPointF(x, y), 0.14 * s, 0.14 * s)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawPath(margaritas)
    p.setBrush(QColor(ROSA))
    p.drawPath(rosas)
    p.setBrush(QColor("#FFD54F"))
    p.drawPath(margaritas_c)
    p.setBrush(QColor("#FFF0A8"))
    p.drawPath(rosas_c)


def _mantel(p, w, h):
    """Mantel vichy rojo y blanco en perspectiva: la rejilla se proyecta con QTransform.quadToQuad."""
    destino = QPolygonF([QPointF(xf * w, yf * h) for xf, yf in MANTEL])
    unidad = QPolygonF([QPointF(0, 0), QPointF(1, 0), QPointF(1, 1), QPointF(0, 1)])
    t = QTransform.quadToQuad(unidad, destino)

    def pt(u, v):
        return t.map(QPointF(u, v))

    contorno = QPolygonF([pt(0, 0), pt(1, 0), pt(1, 1), pt(0, 1)])
    # sombra suave del mantel sobre la hierba (capas que se desvanecen)
    p.setPen(Qt.NoPen)
    for k, alfa in enumerate((26, 22, 18, 14)):
        desp = (k + 1) * 0.004 * h
        sombra_k = QPolygonF([QPointF(q.x() - 0.004 * w * (k + 1), q.y() + desp) for q in contorno])
        p.setBrush(QColor(70, 90, 40, alfa))
        p.drawPolygon(sombra_k)
    p.setBrush(QColor("#FFF8F9"))
    p.drawPolygon(contorno)
    n_col, n_fil = 14, 8
    # vichy: franjas rojas alfa 110 cruzadas sobre blanco (donde se cruzan queda más oscuro)
    p.setBrush(QColor(229, 36, 59, 110))
    for i in range(0, n_col, 2):
        u0, u1 = i / n_col, (i + 1) / n_col
        p.drawPolygon(QPolygonF([pt(u0, 0), pt(u1, 0), pt(u1, 1), pt(u0, 1)]))
    for j in range(0, n_fil, 2):
        v0, v1 = j / n_fil, (j + 1) / n_fil
        p.setBrush(QColor(229, 36, 59, 110))
        p.drawPolygon(QPolygonF([pt(0, v0), pt(1, v0), pt(1, v1), pt(0, v1)]))
    # textura de tela: líneas finísimas en ambas direcciones
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(120, 20, 40, 12), 1.0))
    for i in range(1, n_col * 4):
        u = i / (n_col * 4.0)
        p.drawLine(pt(u, 0), pt(u, 1))
    for j in range(1, n_fil * 4):
        v = j / (n_fil * 4.0)
        p.drawLine(pt(0, v), pt(1, v))
    # sombra suave hacia el borde lejano
    sombra = QLinearGradient(0, pt(0, 0).y(), 0, pt(0, 1).y())
    sombra.setColorAt(0.0, QColor(90, 10, 30, 60))
    sombra.setColorAt(0.45, QColor(90, 10, 30, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(sombra))
    p.drawPolygon(contorno)
    # borde delantero con flecos cortos
    p.setPen(QPen(QColor("#FFF6F0"), max(1.2, h * 0.0016), Qt.SolidLine, Qt.RoundCap))
    for k in range(70):
        base = pt(k / 69.0, 1)
        p.drawLine(base, QPointF(base.x() + (k % 3 - 1) * 1.5, base.y() + h * 0.012))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(ROJO_OSCURO), 1.6))
    p.drawLine(pt(0, 1), pt(1, 1))


def _cesta(p, w, h):
    """Cesta de picnic de mimbre con tejido, fresas asomando y asa."""
    cx = CESTA_CX * w
    top, bot = CESTA_TOP * h, CESTA_BOT * h
    bw = CESTA_BW * w
    bh = bot - top
    p.setPen(Qt.NoPen)
    sombra = QPainterPath()
    sombra.addEllipse(QPointF(cx + 0.012 * w, bot), bw * 0.56, 0.018 * h)
    p.fillPath(sombra, QColor(90, 20, 40, 70))
    # asa (antes del cuerpo: sus extremos quedan tapados)
    asa = QPainterPath(QPointF(cx - bw * 0.46, top + 0.02 * h))
    asa.cubicTo(QPointF(cx - bw * 0.5, top - 0.45 * bh), QPointF(cx + bw * 0.5, top - 0.45 * bh),
                QPointF(cx + bw * 0.46, top + 0.02 * h))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(MIMBRE_OSCURO), max(3.0, h * 0.026), Qt.SolidLine, Qt.RoundCap))
    p.drawPath(asa)
    p.setPen(QPen(QColor(MIMBRE_CLARO), max(2.0, h * 0.014), Qt.SolidLine, Qt.RoundCap))
    p.drawPath(asa)
    # cuerpo
    cuerpo = QPainterPath(QPointF(cx - bw / 2, top))
    cuerpo.lineTo(QPointF(cx + bw / 2, top))
    cuerpo.cubicTo(QPointF(cx + bw * 0.47, top + bh * 0.45), QPointF(cx + bw * 0.42, bot - bh * 0.12),
                   QPointF(cx + bw * 0.34, bot))
    cuerpo.quadTo(QPointF(cx, bot + bh * 0.04), QPointF(cx - bw * 0.34, bot))
    cuerpo.cubicTo(QPointF(cx - bw * 0.42, bot - bh * 0.12), QPointF(cx - bw * 0.47, top + bh * 0.45),
                   QPointF(cx - bw / 2, top))
    cuerpo.closeSubpath()
    g = QLinearGradient(cx - bw / 2, 0, cx + bw / 2, 0)
    g.setColorAt(0.0, QColor(MIMBRE_CLARO))
    g.setColorAt(0.55, QColor(MIMBRE))
    g.setColorAt(1.0, QColor(MIMBRE_OSCURO))
    p.setBrush(QBrush(g))
    p.drawPath(cuerpo)
    # tejido: bandas curvas alternando sombra y luz, y tiras verticales
    p.save()
    p.setClipPath(cuerpo)
    filas = 7
    for k in range(filas + 1):
        yk = top + (k + 0.5) * bh / filas
        tejido = QPainterPath(QPointF(cx - bw, yk))
        tejido.quadTo(QPointF(cx, yk + 0.05 * bh), QPointF(cx + bw, yk))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(MIMBRE_OSCURO), bh * 0.05, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(tejido)
        luz = QPainterPath(QPointF(cx - bw, yk - 0.02 * bh))
        luz.quadTo(QPointF(cx, yk + 0.03 * bh), QPointF(cx + bw, yk - 0.02 * bh))
        p.setPen(QPen(QColor(255, 236, 200, 140), max(1.0, bh * 0.012)))
        p.drawPath(luz)
    for i in range(-9, 10):
        x = cx + i * bw / 18.0
        p.setPen(QPen(QColor(MIMBRE_OSCURO), max(1.0, bw * 0.006)))
        p.drawLine(QPointF(x, top), QPointF(x, bot))
    p.restore()
    # boca: aro, interior oscuro, fresas asomando y aro delantero
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(MIMBRE_CLARO))
    p.drawEllipse(QPointF(cx, top), bw / 2 + 2, bw * 0.04)
    p.setBrush(QColor("#7A4A2A"))
    p.drawEllipse(QPointF(cx, top), bw / 2 - bw * 0.02, bw * 0.028)
    for fx, dy, ang in ((-0.22, -0.03, -15), (0.02, -0.06, 10), (0.24, -0.02, 25)):
        _fresa(p, cx + fx * bw, top + dy * h, bw * 0.075, ang)
    frente = QPainterPath(QPointF(cx - bw / 2 - 2, top))
    frente.arcTo(QRectF(cx - bw / 2 - 2, top - bw * 0.04, bw + 4, bw * 0.08), 180, 180)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(MIMBRE_CLARO), max(2.0, bh * 0.05)))
    p.drawPath(frente)


def _sprite_petalo():
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing, True)
    camino = QPainterPath(QPointF(24, 44))
    camino.cubicTo(QPointF(4, 34), QPointF(6, 8), QPointF(24, 4))
    camino.cubicTo(QPointF(42, 8), QPointF(44, 34), QPointF(24, 44))
    camino.closeSubpath()
    g = QLinearGradient(0, 4, 0, 44)
    g.setColorAt(0.0, QColor("#FFFFFF"))
    g.setColorAt(1.0, QColor(ROSA))
    q.setPen(Qt.NoPen)
    q.fillPath(camino, QBrush(g))
    q.setPen(QPen(QColor(255, 143, 163, 160), 1.2))
    q.drawLine(QPointF(24, 42), QPointF(24, 12))
    q.end()
    return pm


def _sprite_manzana():
    pm = QPixmap(48, 48)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing, True)
    _manzana(q, 24, 28, 13)
    q.end()
    return pm


def _sprite_brillo():
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing, True)
    g = QRadialGradient(QPointF(128, 128), 128)
    g.setColorAt(0.0, QColor(255, 236, 190, 255))
    g.setColorAt(0.35, QColor(255, 214, 170, 140))
    g.setColorAt(1.0, QColor(255, 200, 160, 0))
    q.setPen(Qt.NoPen)
    q.setBrush(QBrush(g))
    q.drawEllipse(QPointF(128, 128), 128, 128)
    q.end()
    return pm


def _ala_sup():
    return _elipse(0.55, -0.35, 0.55, 0.42)


def _ala_inf():
    return _elipse(0.42, 0.35, 0.36, 0.30)


def _cuerpo_mariposa():
    return _elipse(0, 0, 0.05, 0.42)


_ALA_SUP = _ala_sup()
_ALA_INF = _ala_inf()
_CUERPO_MARIPOSA = _cuerpo_mariposa()


class EscenarioHelloKitty(EscenarioBase):
    NOMBRE = "Hello Kitty"
    ACENTO = "#FF4D6D"
    SEMILLA = _SEMILLA

    def preparar(self):
        r = self.rnd
        self._lazos = None       # (h, S, [fotogramas del lazo])
        self._brillo = None      # sprite del resplandor del sol
        self._sprites = None     # (pétalo, manzanita)
        # pétalos (26) y manzanitas (14) que caen de los árboles: (tipo, árbol, desfase x, fase, velocidad,
        # balanceo, giro, tamaño)
        self._caidas = []
        for i in range(40):
            self._caidas.append((0 if i < 26 else 1, r.randint(0, 1), r.uniform(-1.0, 1.0), r.random(),
                                 r.uniform(0.010, 0.020), r.uniform(0, math.tau), r.uniform(-40, 40),
                                 r.uniform(0.018, 0.030)))
        # hierba que se mece: (posición x, altura, fase, color)
        self._mecida = [(r.random(), r.uniform(0.03, 0.06), r.uniform(0, math.tau), r.randint(0, 2))
                        for _ in range(120)]

    # ------------------------------------------------------------ estático

    def pintar_estatico(self, p, w, h):
        p.save()
        rnd = random.Random(_SEMILLA)
        p.setPen(Qt.NoPen)
        # cielo: #FFD6DE arriba → #FFE9E0 → #FFF6EA en el horizonte (55 %)
        cielo = QLinearGradient(0, 0, 0, HORIZONTE * h)
        cielo.setColorAt(0.0, QColor(CIELO_ARRIBA))
        cielo.setColorAt(0.6, QColor(CIELO_MEDIO))
        cielo.setColorAt(1.0, QColor(CIELO_HORIZONTE))
        p.fillRect(QRectF(0, 0, w, h), QBrush(cielo))
        # sol detrás de la casita
        sx, sy, sr = SOL[0] * w, SOL[1] * h, SOL[2] * h
        self.brillo(p, sx, sy, sr * 5.0, "#FFF4D6", alfa=200)
        p.setBrush(QColor("#FFF8E2"))
        p.drawEllipse(QPointF(sx, sy), sr, sr)
        # nubes
        for cx, base, cw in NUBES:
            _nube(p, rnd, w, h, cx, base, cw)
        # colinas lejanas: mezcladas con el cielo al 55 %, y la casita
        p.setBrush(QBrush(mezclar(QColor("#A6DBA6"), QColor(CIELO_HORIZONTE), 0.55)))
        p.drawPath(_camino_colina(_cresta_lejana, w, h, 1.0))
        _casita(p, CASA_X * w, (_cresta_lejana(CASA_X) + 0.004) * h, h)
        # colinas medias: 30 %
        p.setBrush(QBrush(mezclar(QColor("#8DCD94"), QColor(CIELO_HORIZONTE), 0.30)))
        p.drawPath(_camino_colina(_cresta_media, w, h, 1.0))
        # pradera (sin mezcla)
        prado = QLinearGradient(0, HORIZONTE * h, 0, h)
        prado.setColorAt(0.0, QColor(PRADERA_CLARA))
        prado.setColorAt(1.0, QColor(PRADERA_OSCURA))
        p.setBrush(QBrush(prado))
        p.drawPath(_camino_colina(_pradera, w, h, 1.0))
        _pasto(p, rnd, w, h)
        _flores(p, rnd, w, h)
        _camino_tierra(p, w, h)
        for xf, bf, rf in ARBUSTOS:
            _arbusto(p, rnd, w, h, (xf, bf, rf))
        # árboles de manzanas (el lejano primero)
        _arbol(p, rnd, w, h, ARBOL_B)
        _arbol(p, rnd, w, h, ARBOL_A)
        # mantel, tarta, tacitas, galletas y cesta
        _mantel(p, w, h)
        x, yb, cw, ch = TARTA[0] * w, TARTA[1] * h, TARTA[2] * w, TARTA[3] * h
        _tarta(p, x, yb, cw, ch)
        for xf, base, rw in TAZAS:
            _taza(p, xf * w, base * h, rw * w)
        for xf, yf in GALLETAS:
            _galleta(p, xf * w, yf * h, 0.038 * h, rnd.uniform(-18, 18))
        _cesta(p, w, h)
        # grano fino y viñeta cálida
        grano = QPolygonF([QPointF(rnd.uniform(0, w), rnd.uniform(0, h)) for _ in range(5000)])
        p.setPen(QPen(QColor(90, 30, 40, 6), 1.6))
        p.drawPoints(grano)
        p.setPen(Qt.NoPen)
        viñeta = QRadialGradient(QPointF(w / 2.0, h / 2.0), math.hypot(w / 2.0, h / 2.0))
        viñeta.setColorAt(0.0, QColor(201, 112, 127, 0))
        viñeta.setColorAt(0.6, QColor(201, 112, 127, 0))
        viñeta.setColorAt(1.0, QColor(201, 112, 127, 60))
        p.fillRect(QRectF(0, 0, w, h), QBrush(viñeta))
        p.restore()

    # ------------------------------------------------------------ cada cuadro

    def pintar_animado(self, p, w, h, t):
        p.save()
        p.setPen(Qt.NoPen)
        e = self.energia()
        # resplandor cálido del sol que respira detrás de la casita
        respira = 0.5 + 0.5 * math.sin(t * 0.9)
        p.setOpacity(min(1.0, 0.28 + 0.2 * respira + 0.15 * e))
        sx, sy, sr = SOL[0] * w, SOL[1] * h, 0.24 * h
        p.drawPixmap(QRectF(sx - sr, sy - sr, 2 * sr, 2 * sr), self._sprite_brillo(), QRectF(0, 0, 256, 256))
        p.setOpacity(1.0)
        self._caer(p, w, h, t)
        for bx, by, fase, color in MARIPOSAS:
            self._mariposa(p, w, h, t, bx, by, fase, color)
        # lazo de la cesta: se infla con la música (6 fotogramas pre-renderizados, escala 1..1.05)
        ax, ay = _ancla_cesta(w, h)
        S, pms = self._lazo_pixmaps(h)
        paso = int(round(min(1.0, 0.2 + 1.5 * e) * (_LAZO_PASOS - 1)))
        p.drawPixmap(QRectF(ax - S / 2.0, ay - S / 2.0, S, S), pms[paso], QRectF(0, 0, S, S))
        self._hierba(p, w, h, t)
        # ondas de la música en el horizonte
        self.ondas(p, base_y=0.60 * h, ancho=0.5 * w, alto_max=0.08 * h, color=self.acento(), x0=0.25 * w)
        p.restore()

    # ------------------------------------------------------------ sprites y animación

    def _sprite_brillo(self):
        if self._brillo is None:
            self._brillo = _sprite_brillo()
        return self._brillo

    def _sprites_caida(self):
        if self._sprites is None:
            self._sprites = (_sprite_petalo(), _sprite_manzana())
        return self._sprites

    def _lazo_pixmaps(self, h):
        if self._lazos is None or self._lazos[0] != h:
            S = int(round(0.30 * h))
            pms = []
            for i in range(_LAZO_PASOS):
                pm = QPixmap(S, S)
                pm.fill(Qt.transparent)
                q = QPainter(pm)
                q.setRenderHint(QPainter.Antialiasing, True)
                q.translate(S / 2.0, S / 2.0)
                _dibujar_lazo(q, 0.075 * h * (1.0 + 0.05 * i / (_LAZO_PASOS - 1)))
                q.end()
                pms.append(pm)
            self._lazos = (h, S, pms)
        return self._lazos[1], self._lazos[2]

    def _caer(self, p, w, h, t):
        """Pétalos y manzanitas que caen de los árboles, girando y balanceándose, con fundido en los extremos."""
        petalo, manzana = self._sprites_caida()
        for tipo, arbol, desfase, fase, vel, bal, giro, tam in self._caidas:
            xf, bf, Rf, _n = ARBOL_A if arbol == 0 else ARBOL_B
            R = Rf * h
            cy = bf * h - 2.0 * R
            u = (fase + t * vel) % 1.0
            y = cy + u * (0.97 * h - cy)
            x = xf * w + desfase * 0.95 * R + 0.025 * h * math.sin(t * 0.7 + bal)
            ang = 35.0 * math.sin(t * 0.9 + bal) + giro * t * 0.5
            s = tam * h
            p.save()
            p.setOpacity(max(0.0, min(1.0, u * 6.0)) * max(0.0, min(1.0, (1.0 - u) * 5.0)))
            p.translate(x, y)
            p.rotate(ang)
            pix = petalo if tipo == 0 else manzana
            p.drawPixmap(QRectF(-s / 2.0, -s / 2.0, s, s), pix, QRectF(0, 0, 48, 48))
            p.restore()

    def _mariposa(self, p, w, h, t, bx, by, fase, color):
        """Mariposa con trayectoria curva lenta; las alas se estrechan y se abren con el aleteo."""
        x = (bx + 0.07 * math.sin(t * 0.21 + fase) + 0.02 * math.sin(t * 0.53 + fase * 2.0)) * w
        y = (by + 0.04 * math.sin(t * 0.33 + fase * 1.3)) * h
        s = 0.022 * h
        aleteo = max(0.12, abs(math.sin(t * 9.0 + fase)))
        p.save()
        p.translate(x, y)
        p.scale(s, s)
        for lado in (1, -1):
            p.save()
            p.scale(lado * aleteo, 1.0)
            p.fillPath(_ALA_SUP, QColor(color))
            p.fillPath(_ALA_INF, QColor(ROSA_FUERTE))
            p.restore()
        p.fillPath(_CUERPO_MARIPOSA, QColor("#5B3A4A"))
        p.restore()

    def _hierba(self, p, w, h, t):
        """Briznas del borde inferior que se mecen con una onda que recorre el ancho."""
        caminos = [QPainterPath(), QPainterPath(), QPainterPath()]
        for xf, alt, fase, k in self._mecida:
            x = xf * w
            base = h + 2.0
            inclinacion = 0.32 * math.sin(t * 1.4 + xf * 7.0 + fase) + 0.08 * math.sin(t * 0.6 + fase)
            lean = inclinacion * alt * h
            alt_px = alt * h
            caminos[k].moveTo(QPointF(x, base))
            caminos[k].quadTo(QPointF(x + lean * 0.25, base - alt_px * 0.55), QPointF(x + lean, base - alt_px))
        p.setBrush(Qt.NoBrush)
        for camino, color in zip(caminos, (VERDE_OSCURO, VERDE_MEDIO, VERDE_CLARO)):
            p.setPen(QPen(QColor(color), max(1.4, h * 0.0025), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(camino)
        p.setPen(Qt.NoPen)
