# -*- coding: utf-8 -*-
"""Ilustraciones animadas de la segunda «Actualización grande de Caudal».

Todo se dibuja con QPainter, sin ninguna imagen. Cada ilustración es una función
`ilus_xxx(p, X)` que pinta en un lienzo de 100 x 100 unidades centrado en (0, 0)
(el painter ya viene trasladado y escalado). `X` trae:

    X.tl      segundos desde que la diapositiva entró (para las entradas escalonadas)
    X.tg      segundos globales (para lo que da vueltas sin parar)
    X.pal     paleta viva, a partir del color de acento
    X.hw,hh   medio ancho y medio alto visibles, en esas mismas unidades
    X.alfa    opacidad del conjunto (1 = opaco)
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)


# ================================================================ utilidades

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def tramo(t, ini, dur):
    """0 antes de `ini`, 1 pasados `dur` segundos."""
    return clamp((t - ini) / dur) if dur > 0 else (1.0 if t >= ini else 0.0)


def eo(t):
    """Salida suave (cúbica)."""
    return 1 - (1 - t) ** 3


def eio(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def liso(x, a, b):
    t = clamp((x - a) / (b - a)) if b != a else 1.0
    return t * t * (3 - 2 * t)


def rebote(t):
    """Entrada con un pequeño rebote al final."""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def azar(i, k=0):
    """Número repetible entre 0 y 1."""
    v = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return v - math.floor(v)


def alfa(color, a):
    c = QColor(color)
    c.setAlpha(int(clamp(a, 0, 255)))
    return c


def mezcla(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


def tono(color, grados, s_min=0.0, v_min=0.0, a=255):
    """El mismo color con el matiz girado."""
    c = QColor(color)
    h, s, v, _ = c.getHsvF()
    h = (max(h, 0.0) + grados / 360.0) % 1.0
    q = QColor.fromHsvF(h, max(s, s_min), max(v, v_min))
    q.setAlpha(a)
    return q


class Paleta:
    """Colores de la presentación, todos hijos del acento elegido."""

    def __init__(self, C):
        self.ac = QColor(C["acento"])
        self.al = QColor(C["acento_alto"])
        self.ba = QColor(C["acento_bajo"])
        self.tx = QColor(C["acento_texto"])
        self.c2 = tono(C["acento"], 42, 0.55, 0.85)       # vecino cálido
        self.c3 = tono(C["acento"], -48, 0.5, 0.8)        # vecino frío
        self.c4 = tono(C["acento"], 150, 0.5, 0.9)        # contraste
        self.oro = QColor("#F5C451")
        self.fondo = QColor(C["fondo"])
        self.panel = QColor(C["panel"])
        self.noche = mezcla(C["fondo"], "#000000", 0.35)


class Ctx:
    def __init__(self, pal, tl, tg, hw, hh, alfa_=1.0):
        self.pal, self.tl, self.tg, self.hw, self.hh, self.alfa = pal, tl, tg, hw, hh, alfa_


def lapiz(color, ancho=1.0, cap=Qt.RoundCap, union=Qt.RoundJoin):
    pen = QPen(QBrush(color) if not isinstance(color, (QColor, str)) else QColor(color), ancho)
    pen.setWidthF(ancho)
    pen.setCapStyle(cap)
    pen.setJoinStyle(union)
    return pen


def texto(p, x, y, cadena, tam, color, peso=QFont.Bold, alin=Qt.AlignCenter, ancho=60.0, alto=None):
    """Texto en unidades del lienzo (el tamaño admite decimales)."""
    p.save()
    p.scale(0.1, 0.1)
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(tam * 10)))
    f.setWeight(peso)
    p.setFont(f)
    p.setPen(QColor(color))
    alto = alto if alto is not None else tam * 1.6
    p.drawText(QRectF((x - (ancho / 2 if alin == Qt.AlignCenter else 0)) * 10, (y - alto / 2) * 10,
                      ancho * 10, alto * 10), int(alin | Qt.AlignVCenter), cadena)
    p.restore()


def brillo(p, cx, cy, radio, color, a=120):
    g = QRadialGradient(QPointF(cx, cy), radio)
    g.setColorAt(0.0, alfa(color, a))
    g.setColorAt(1.0, alfa(color, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(cx, cy), radio, radio)


def estrella(p, cx, cy, R, r, relleno, giro=-90.0):
    ruta = QPainterPath()
    for i in range(10):
        rad = R if i % 2 == 0 else r
        a = math.radians(giro + i * 36)
        pt = QPointF(cx + rad * math.cos(a), cy + rad * math.sin(a))
        ruta.moveTo(pt) if i == 0 else ruta.lineTo(pt)
    ruta.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(relleno)
    p.drawPath(ruta)


def destello(p, cx, cy, tam, color, a=255):
    """Cruz de cuatro puntas, como un brillo de cámara."""
    ruta = QPainterPath()
    ruta.moveTo(cx, cy - tam)
    ruta.quadTo(cx, cy, cx + tam, cy)
    ruta.quadTo(cx, cy, cx, cy + tam)
    ruta.quadTo(cx, cy, cx - tam, cy)
    ruta.quadTo(cx, cy, cx, cy - tam)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    p.drawPath(ruta)


def nota(p, x, y, tam, color, tipo=0, a=255):
    """Nota musical: 0 corchea, 1 negra, 2 dos corcheas unidas."""
    col = alfa(color, a)
    p.save()
    p.translate(x, y)
    p.setPen(Qt.NoPen)
    p.setBrush(col)

    def cabeza(cx, cy):
        p.save()
        p.translate(cx, cy)
        p.rotate(-22)
        p.drawEllipse(QPointF(0, 0), tam * 0.30, tam * 0.21)
        p.restore()

    if tipo == 2:
        cabeza(-tam * 0.32, tam * 0.45)
        cabeza(tam * 0.38, tam * 0.30)
        p.setPen(lapiz(col, tam * 0.075, Qt.FlatCap))
        p.drawLine(QPointF(-tam * 0.08, tam * 0.40), QPointF(-tam * 0.08, -tam * 0.45))
        p.drawLine(QPointF(tam * 0.62, tam * 0.25), QPointF(tam * 0.62, -tam * 0.60))
        p.setPen(Qt.NoPen)
        viga = QPainterPath()
        viga.moveTo(-tam * 0.08, -tam * 0.45)
        viga.lineTo(tam * 0.62, -tam * 0.60)
        viga.lineTo(tam * 0.62, -tam * 0.38)
        viga.lineTo(-tam * 0.08, -tam * 0.23)
        viga.closeSubpath()
        p.drawPath(viga)
    else:
        cabeza(0, tam * 0.40)
        p.setPen(lapiz(col, tam * 0.075, Qt.FlatCap))
        p.drawLine(QPointF(tam * 0.27, tam * 0.34), QPointF(tam * 0.27, -tam * 0.55))
        if tipo == 0:
            p.setPen(Qt.NoPen)
            bandera = QPainterPath()
            bandera.moveTo(tam * 0.27, -tam * 0.55)
            bandera.cubicTo(tam * 0.30, -tam * 0.20, tam * 0.62, -tam * 0.22, tam * 0.58, tam * 0.10)
            bandera.cubicTo(tam * 0.58, -tam * 0.10, tam * 0.40, -tam * 0.10, tam * 0.27, -tam * 0.32)
            bandera.closeSubpath()
            p.drawPath(bandera)
    p.restore()


def pastilla(p, rect, color, a=255):
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)


def cristal(p, rect, radio, a_relleno=22, a_borde=46):
    """Panel de cristal: relleno blanco muy tenue y filo fino."""
    p.setPen(lapiz(QColor(255, 255, 255, a_borde), 0.35))
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor(255, 255, 255, a_relleno + 14))
    g.setColorAt(1, QColor(255, 255, 255, max(0, a_relleno - 10)))
    p.setBrush(g)
    p.drawRoundedRect(rect, radio, radio)


def cursor(p, x, y, esc=1.0, a=255):
    """Flecha del ratón."""
    ruta = QPainterPath()
    ruta.moveTo(0, 0)
    ruta.lineTo(0, 9.5)
    ruta.lineTo(2.5, 7.3)
    ruta.lineTo(4.2, 11.2)
    ruta.lineTo(5.9, 10.4)
    ruta.lineTo(4.3, 6.7)
    ruta.lineTo(7.5, 6.5)
    ruta.closeSubpath()
    p.save()
    p.translate(x, y)
    p.scale(esc, esc)
    p.setPen(lapiz(QColor(10, 12, 18, a), 0.7))
    p.setBrush(QColor(255, 255, 255, a))
    p.drawPath(ruta)
    p.restore()


# ================================================================ 1. portada

def _ola(x, k, tg, hh):
    f = 0.045 + 0.008 * k
    return (hh * (0.54 + 0.09 * k) + 3.2 * math.sin(x * f * 2.0 + tg * (0.55 + 0.1 * k) + k * 1.7)
            + 1.8 * math.sin(x * f * 4.3 - tg * (0.8 + 0.07 * k) + k))


def ilus_portada(p, X):
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    sube = eo(tramo(tl, 0.0, 1.6))
    colores = [pal.c3, pal.ac, pal.al, pal.c2, pal.ac]
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    p.translate(0, (1 - sube) * hh * 0.9)
    pasos = 70
    for k in range(5):
        ruta = QPainterPath()
        ruta.moveTo(-hw, hh + 6)
        xs = [-hw + (2 * hw) * i / pasos for i in range(pasos + 1)]
        for x in xs:
            ruta.lineTo(x, _ola(x, k, tg, hh))
        ruta.lineTo(hw, hh + 6)
        ruta.closeSubpath()
        g = QLinearGradient(0, hh * (0.48 + 0.09 * k), 0, hh)
        g.setColorAt(0, alfa(colores[k], 74 - k * 7))
        g.setColorAt(1, alfa(colores[k], 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(ruta)
        cresta = QPainterPath()
        for i, x in enumerate(xs):
            pt = QPointF(x, _ola(x, k, tg, hh))
            cresta.moveTo(pt) if i == 0 else cresta.lineTo(pt)
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(mezcla(colores[k], "#FFFFFF", 0.35), 150 - k * 14), 0.28))
        p.drawPath(cresta)
    # la estela: un cometa que viaja por la cresta de la ola del medio
    ancho = hw * 2 + 40
    cx = -hw - 20 + ((tg * 17 + 40) % ancho)
    for j in range(26):
        x = cx - j * 1.7
        y = _ola(x, 2, tg, hh) - 1.4
        a = (1 - j / 26.0) ** 2
        brillo(p, x, y, 2.0 + 2.2 * a, pal.al, 190 * a)
    destello(p, cx, _ola(cx, 2, tg, hh) - 1.4, 3.6, "#FFFFFF", 235)
    p.restore()


# ================================================================ 2. fondo de Caudal

def _paisaje(p, rect, tg, pal, a):
    """Un paisaje de pantalla: cielo, sol y dos montañas."""
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, alfa(pal.c3, a))
    g.setColorAt(0.55, alfa(pal.c2, a))
    g.setColorAt(1.0, alfa(pal.ac, a))
    p.fillRect(rect, g)
    sx = rect.center().x() + 12 + 3 * math.sin(tg * 0.5)
    brillo(p, sx, rect.top() + 17, 24, "#FFFFFF", a * 0.55)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa("#FFF3D6", a))
    p.drawEllipse(QPointF(sx, rect.top() + 17), 6.5, 6.5)
    for (k, col, base) in ((0, pal.ba, 0.62), (1, pal.noche, 0.78)):
        ruta = QPainterPath()
        ruta.moveTo(rect.left(), rect.bottom())
        y0 = rect.top() + rect.height() * base
        for i in range(0, 21):
            x = rect.left() + rect.width() * i / 20
            ruta.lineTo(x, y0 - 7 * math.sin(i * 0.8 + k * 2.1) - 5 * math.sin(i * 0.37 + k))
        ruta.lineTo(rect.right(), rect.bottom())
        ruta.closeSubpath()
        p.setBrush(alfa(col, a * (0.9 if k == 0 else 0.95)))
        p.drawPath(ruta)


def ilus_fondo(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.12, 0.9))
    p.save()
    p.translate(0, (1 - r) * 10 - 4)
    p.scale(0.94 + 0.06 * r, 0.94 + 0.06 * r)
    p.setOpacity(X.alfa * r)
    brillo(p, 0, 0, 62, pal.ac, 62)
    win = QRectF(-47, -31, 94, 62)
    ruta = QPainterPath()
    ruta.addRoundedRect(win, 5, 5)
    # sombra
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(win.adjusted(-1, 3, 1, 5), 6, 6)
    p.setClipPath(ruta)
    p.fillRect(win, pal.panel)
    # «tenue»: la imagen sube y baja de intensidad, como el control de la app
    nivel = 0.5 + 0.22 * math.sin(tg * 0.9)
    _paisaje(p, win, tg, pal, 255 * (0.3 + 0.5 * nivel) * eo(tramo(tl, 0.35, 1.0)))
    # app encima: barra lateral, tarjetas y reproductor
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(8, 10, 16, 150))
    p.drawRect(QRectF(win.left(), win.top(), 15, win.height()))
    for i in range(4):
        pastilla(p, QRectF(win.left() + 3.5, win.top() + 7 + i * 6.2, 8, 2.2),
                 pal.al if i == 0 else QColor(255, 255, 255), 255 if i == 0 else 90)
    pastilla(p, QRectF(win.left() + 20, win.top() + 5, 30, 3), QColor(255, 255, 255), 150)
    pastilla(p, QRectF(win.left() + 20, win.top() + 10, 18, 2), QColor(255, 255, 255), 80)
    for i in range(3):
        c = QRectF(win.left() + 20 + i * 23, win.top() + 17, 20, 20)
        p.setPen(lapiz(QColor(255, 255, 255, 36), 0.3))
        p.setBrush(QColor(8, 10, 16, 118))
        p.drawRoundedRect(c, 2.5, 2.5)
        g = QLinearGradient(c.topLeft(), c.bottomRight())
        g.setColorAt(0, alfa([pal.ac, pal.c2, pal.c3][i], 220))
        g.setColorAt(1, alfa([pal.ba, pal.c3, pal.c4][i], 220))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(c.adjusted(2, 2, -2, -9), 1.6, 1.6)
        pastilla(p, QRectF(c.left() + 2, c.bottom() - 6, 12, 1.5), QColor(255, 255, 255), 170)
        pastilla(p, QRectF(c.left() + 2, c.bottom() - 3.2, 7, 1.3), QColor(255, 255, 255), 90)
    barra = QRectF(win.left() + 15, win.bottom() - 10.5, win.width() - 15, 10.5)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(8, 10, 16, 190))
    p.drawRect(barra)
    prog = (tg * 0.07) % 1
    pastilla(p, QRectF(barra.left() + 14, barra.center().y() - 0.6, 52, 1.2), QColor(255, 255, 255), 60)
    pastilla(p, QRectF(barra.left() + 14, barra.center().y() - 0.6, 52 * prog, 1.2), pal.al, 255)
    p.setBrush(pal.ac)
    p.drawEllipse(QPointF(barra.left() + 7, barra.center().y()), 3.1, 3.1)
    p.setBrush(pal.tx)
    tri = QPainterPath()
    tri.moveTo(barra.left() + 6.2, barra.center().y() - 1.3)
    tri.lineTo(barra.left() + 6.2, barra.center().y() + 1.3)
    tri.lineTo(barra.left() + 8.4, barra.center().y())
    tri.closeSubpath()
    p.drawPath(tri)
    # barrido de luz
    bx = win.left() - 30 + ((tg * 26) % (win.width() + 90))
    g = QLinearGradient(bx - 14, 0, bx + 14, 0)
    g.setColorAt(0, QColor(255, 255, 255, 0))
    g.setColorAt(0.5, QColor(255, 255, 255, 34))
    g.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(win, g)
    p.setClipping(False)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(QColor(255, 255, 255, 80), 0.45))
    p.drawPath(ruta)

    # control «tenue» debajo
    y = 42
    pastilla(p, QRectF(-20, y - 0.9, 40, 1.8), QColor(255, 255, 255), 50)
    pastilla(p, QRectF(-20, y - 0.9, 40 * nivel, 1.8), pal.al, 255)
    brillo(p, -20 + 40 * nivel, y, 5, pal.al, 120)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(-20 + 40 * nivel, y), 2.6, 2.6)
    texto(p, -32, y, "Tenue", 3.0, QColor(255, 255, 255, 170), QFont.DemiBold, Qt.AlignRight, 10)

    # insignia de donador
    b = rebote(tramo(tl, 0.8, 0.8))
    p.save()
    p.translate(43, -33)
    p.scale(b, b)
    brillo(p, 0, 0, 12, pal.oro, 120)
    p.setPen(lapiz("#FFF4C9", 0.5))
    p.setBrush(pal.oro)
    p.drawEllipse(QPointF(0, 0), 6.6, 6.6)
    estrella(p, 0, 0.3, 3.8, 1.6, QColor("#7A5200"))
    p.restore()
    p.restore()


# ================================================================ 3. donadores

def ilus_donadores(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.1, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 8)
    brillo(p, 0, 0, 60, pal.ac, 55)

    # tarjeta de perfil
    card = QRectF(-44, -37, 56, 74)
    ruta = QPainterPath()
    ruta.addRoundedRect(card, 5, 5)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(card.adjusted(-1, 3, 1, 5), 6, 6)
    p.setClipPath(ruta)
    p.fillRect(card, mezcla(pal.panel, "#FFFFFF", 0.05))
    # fondo de perfil animado (un GIF): degradado que corre y formas que flotan
    banner = QRectF(card.left(), card.top(), card.width(), 28)
    g = QLinearGradient(banner.left() - tg * 11 % 60, 0, banner.left() + 60 - tg * 11 % 60, 20)
    g.setColorAt(0.0, pal.c3)
    g.setColorAt(0.33, pal.ac)
    g.setColorAt(0.66, pal.c2)
    g.setColorAt(1.0, pal.c3)
    g.setSpread(QLinearGradient.RepeatSpread)
    p.fillRect(banner, g)
    for i in range(5):
        x = banner.left() + ((azar(i, 3) * 70 + tg * (4 + 3 * azar(i, 4))) % 80) - 12
        y = banner.top() + 4 + 20 * azar(i, 5) + 2 * math.sin(tg * 1.3 + i)
        brillo(p, x, y, 5 + 6 * azar(i, 6), "#FFFFFF", 70)
    p.setClipping(False)
    p.setClipPath(ruta)
    # insignia GIF en el fondo
    pastilla(p, QRectF(banner.right() - 14.5, banner.top() + 2.5, 12, 5.2), QColor(8, 10, 16), 170)
    texto(p, banner.right() - 8.5, banner.top() + 5.1, "GIF", 3.2, QColor("#FFFFFF"), QFont.Black, Qt.AlignCenter, 12)

    # foto con anillo animado
    cx, cy, R = card.center().x(), banner.bottom() - 2, 12.5
    p.setClipping(False)
    giro = (tg * 80) % 360
    cono = QConicalGradient(QPointF(cx, cy), giro)
    cono.setColorAt(0.0, pal.al)
    cono.setColorAt(0.33, pal.c2)
    cono.setColorAt(0.66, pal.c3)
    cono.setColorAt(1.0, pal.al)
    p.setPen(Qt.NoPen)
    p.setBrush(cono)
    p.drawEllipse(QPointF(cx, cy), R + 1.8, R + 1.8)
    p.setBrush(pal.panel)
    p.drawEllipse(QPointF(cx, cy), R + 0.5, R + 0.5)
    foto = QRectF(cx - R, cy - R, R * 2, R * 2)
    fruta = QPainterPath()
    fruta.addEllipse(foto)
    p.save()
    p.setClipPath(fruta)
    g = QLinearGradient(foto.topLeft(), foto.bottomRight())
    g.setColorAt(0, pal.c2)
    g.setColorAt(1, pal.ba)
    p.fillRect(foto, g)
    p.setBrush(alfa("#FFFFFF", 235))
    p.drawEllipse(QPointF(cx, cy - 2.6), 4.4, 4.4)
    p.drawEllipse(QPointF(cx, cy + 11), 8.6, 8.6)
    # movimiento dentro de la foto (también es un GIF)
    brillo(p, cx - R + ((tg * 12) % (R * 3)), cy - 3, 8, "#FFFFFF", 80)
    p.restore()
    pastilla(p, QRectF(cx + 3.5, cy + 4.2, 10, 4.6), QColor(8, 10, 16), 215)
    texto(p, cx + 8.5, cy + 6.6, "GIF", 2.9, QColor("#FFFFFF"), QFont.Black, Qt.AlignCenter, 10)

    # nombre y etiqueta
    pastilla(p, QRectF(cx - 12, cy + R + 3.5, 24, 2.6), QColor(255, 255, 255), 215)
    pastilla(p, QRectF(cx - 8, cy + R + 8, 16, 1.8), QColor(255, 255, 255), 90)
    e = rebote(tramo(tl, 0.75, 0.8))
    p.save()
    p.translate(cx, cy + R + 17.2)
    p.scale(e, e)
    brillo(p, 0, 0, 22, pal.oro, 80)
    etiqueta = QRectF(-21, -4.6, 42, 9.2)
    g = QLinearGradient(etiqueta.topLeft(), etiqueta.bottomRight())
    g.setColorAt(0, QColor("#FFE08A"))
    g.setColorAt(1, QColor("#E8A52C"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(etiqueta, 4.6, 4.6)
    estrella(p, -15.5, 0.1, 2.5, 1.1, QColor("#6B4500"))
    texto(p, -11.8, 0.1, "Donador de Caudal", 3.45, QColor("#4A2F00"), QFont.Black, Qt.AlignLeft, 33)
    # brillo que cruza la etiqueta
    bx = -26 + ((tg * 22) % 80)
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(etiqueta, 4.6, 4.6)
    p.setClipPath(clip)
    gg = QLinearGradient(bx - 6, -4, bx + 6, 4)
    gg.setColorAt(0, QColor(255, 255, 255, 0))
    gg.setColorAt(0.5, QColor(255, 255, 255, 140))
    gg.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(etiqueta, gg)
    p.restore()
    p.restore()
    p.setClipping(False)

    # búsqueda segura de GIF
    q = eo(tramo(tl, 0.5, 0.9))
    p.save()
    p.translate((1 - q) * 14, 0)
    p.setOpacity(X.alfa * r * q)
    panel = QRectF(15, -22, 34, 52)
    cristal(p, panel, 4.5, 28, 60)
    pastilla(p, QRectF(panel.left() + 3, panel.top() + 3.5, panel.width() - 6, 6.4), QColor(8, 10, 16), 170)
    p.setPen(lapiz(QColor(255, 255, 255, 190), 0.55))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(panel.left() + 7, panel.top() + 6.6), 1.6, 1.6)
    p.drawLine(QPointF(panel.left() + 8.2, panel.top() + 7.8), QPointF(panel.left() + 9.5, panel.top() + 9.1))
    pastilla(p, QRectF(panel.left() + 12.5, panel.top() + 6, 11, 1.2), QColor(255, 255, 255), 130)
    for i in range(4):
        c = QRectF(panel.left() + 3 + (i % 2) * 14.2, panel.top() + 13 + (i // 2) * 14.5, 13.2, 13.2)
        g = QLinearGradient(c.left() - (tg * 9 + i * 7) % 30, 0, c.left() + 26 - (tg * 9 + i * 7) % 30, 18)
        g.setColorAt(0, [pal.ac, pal.c2, pal.c3, pal.c4][i])
        g.setColorAt(0.5, [pal.c3, pal.c4, pal.ac, pal.c2][i])
        g.setColorAt(1, [pal.ac, pal.c2, pal.c3, pal.c4][i])
        g.setSpread(QLinearGradient.RepeatSpread)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(c, 2, 2)
        brillo(p, c.center().x() + 2.5 * math.sin(tg * 2 + i), c.center().y() + 2 * math.cos(tg * 1.7 + i), 3.2, "#FFFFFF", 110)
    # escudo
    esc = QPainterPath()
    ex, ey = panel.center().x(), panel.bottom() - 6.4
    esc.moveTo(ex, ey - 4)
    esc.cubicTo(ex + 2.2, ey - 3.2, ex + 3.6, ey - 3, ex + 3.8, ey - 3)
    esc.cubicTo(ex + 3.8, ey + 1.5, ex + 2.2, ey + 3.4, ex, ey + 4.6)
    esc.cubicTo(ex - 2.2, ey + 3.4, ex - 3.8, ey + 1.5, ex - 3.8, ey - 3)
    esc.cubicTo(ex - 3.6, ey - 3, ex - 2.2, ey - 3.2, ex, ey - 4)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#2BD576"))
    p.drawPath(esc)
    p.setPen(lapiz("#06210F", 0.6))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline([QPointF(ex - 1.7, ey), QPointF(ex - 0.4, ey + 1.4), QPointF(ex + 1.9, ey - 1.4)])
    p.restore()
    p.restore()


# ================================================================ 4. modo vinilo

def ilus_vinilo(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 10)
    brillo(p, -4, 0, 64, pal.ac, 60)
    caja = QRectF(-48, -35, 96, 70)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 100))
    p.drawRoundedRect(caja.adjusted(-1, 3, 1, 5), 6, 6)
    g = QLinearGradient(caja.topLeft(), caja.bottomRight())
    g.setColorAt(0, mezcla(pal.panel, "#FFFFFF", 0.14))
    g.setColorAt(1, mezcla(pal.panel, "#000000", 0.25))
    p.setPen(lapiz(QColor(255, 255, 255, 56), 0.4))
    p.setBrush(g)
    p.drawRoundedRect(caja, 6, 6)

    centro = QPointF(-10, 0)
    # plato
    p.setPen(lapiz(QColor(255, 255, 255, 50), 0.4))
    p.setBrush(QColor(10, 12, 18))
    p.drawEllipse(centro, 29.5, 29.5)

    # velocidad del disco: arranca cuando la aguja toca
    caida = liso(tl, 1.5, 2.4)
    arranque = liso(tl, 2.0, 3.6)
    # integral de una rampa sencilla: así el disco acelera sin saltos
    if tl < 2.0:
        giro_total = 0.0
    else:
        s = min(tl, 3.6) - 2.0
        giro_total = 180 * (s * s / (2 * 1.6)) if tl < 3.6 else 180 * (1.6 / 2) + 180 * (tl - 3.6)
    giro = giro_total
    p.save()
    p.translate(centro)
    p.rotate(giro % 360)
    disco = QRectF(-26, -26, 52, 52)
    p.setPen(Qt.NoPen)
    g = QRadialGradient(QPointF(0, 0), 26)
    g.setColorAt(0, QColor(30, 33, 42))
    g.setColorAt(1, QColor(8, 9, 13))
    p.setBrush(g)
    p.drawEllipse(disco)
    for i, rr in enumerate((24.5, 22.2, 20, 17.8, 15.8, 14.2)):
        p.setPen(lapiz(QColor(255, 255, 255, 14 + (i % 2) * 10), 0.25))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), rr, rr)
    # reflejo en cono
    cono = QConicalGradient(QPointF(0, 0), 35)
    cono.setColorAt(0.0, QColor(255, 255, 255, 0))
    cono.setColorAt(0.05, QColor(255, 255, 255, 38))
    cono.setColorAt(0.12, QColor(255, 255, 255, 0))
    cono.setColorAt(0.5, QColor(255, 255, 255, 0))
    cono.setColorAt(0.55, QColor(255, 255, 255, 30))
    cono.setColorAt(0.62, QColor(255, 255, 255, 0))
    cono.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setPen(Qt.NoPen)
    p.setBrush(cono)
    p.drawEllipse(QPointF(0, 0), 25.6, 25.6)
    # etiqueta central
    g = QLinearGradient(-9, -9, 9, 9)
    g.setColorAt(0, pal.al)
    g.setColorAt(1, pal.c2)
    p.setBrush(g)
    p.drawEllipse(QPointF(0, 0), 9.2, 9.2)
    p.setBrush(Qt.NoBrush)
    for rr in (7.0, 5.0):
        p.setPen(lapiz(alfa(pal.tx, 70), 0.3))
        p.drawEllipse(QPointF(0, 0), rr, rr)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa("#FFFFFF", 200))
    p.drawEllipse(QPointF(0, -6.4), 1.1, 1.1)
    p.restore()
    p.setBrush(QColor("#0B0D12"))
    p.setPen(lapiz(QColor(255, 255, 255, 120), 0.3))
    p.drawEllipse(centro, 1.1, 1.1)

    # brazo: de reposo a la aguja sobre el disco
    pivote = QPointF(35, -22)
    ang = -8 + 48.5 * caida
    L = 40.0
    fin = QPointF(pivote.x() - L * math.sin(math.radians(ang)), pivote.y() + L * math.cos(math.radians(ang)))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 80))
    p.drawEllipse(QPointF(pivote.x() + 1, pivote.y() + 1.6), 6.8, 6.8)
    p.setBrush(mezcla(pal.panel, "#FFFFFF", 0.3))
    p.setPen(lapiz(QColor(255, 255, 255, 90), 0.35))
    p.drawEllipse(pivote, 6.2, 6.2)
    p.setPen(lapiz(QColor("#DDE3EC"), 1.7, Qt.RoundCap))
    p.drawLine(pivote, fin)
    p.setPen(lapiz(QColor(0, 0, 0, 60), 0.5, Qt.RoundCap))
    p.drawLine(QPointF(pivote.x() + 0.6, pivote.y() + 0.6), QPointF(fin.x() + 0.6, fin.y() + 0.6))
    # cabezal
    p.save()
    p.translate(fin)
    p.rotate(-ang + 8)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#EDF1F7"))
    p.drawRoundedRect(QRectF(-2.2, -0.6, 4.4, 6.6), 1.2, 1.2)
    p.setBrush(pal.ac)
    p.drawRect(QRectF(-1.1, 5.2, 2.2, 1.6))
    p.restore()
    p.setBrush(pal.ac)
    p.setPen(Qt.NoPen)
    p.drawEllipse(pivote, 2.2, 2.2)

    # pantalla encendida
    enc = liso(tl, 2.3, 3.0)
    pan = QRectF(14, 15, 29, 14.5)
    p.setPen(lapiz(QColor(255, 255, 255, 60), 0.35))
    p.setBrush(QColor(5, 7, 11))
    p.drawRoundedRect(pan, 2.2, 2.2)
    if enc > 0:
        brillo(p, pan.center().x(), pan.center().y(), 24, pal.al, 75 * enc)
        p.setPen(Qt.NoPen)
        pastilla(p, QRectF(pan.left() + 2.5, pan.top() + 2.8, 12 * enc, 1.6), pal.al, 255)
        pastilla(p, QRectF(pan.left() + 2.5, pan.top() + 5.6, 8 * enc, 1.2), QColor(255, 255, 255), 130)
        for i in range(7):
            h = 1.5 + 5.5 * (0.5 + 0.5 * math.sin(tg * (3 + i * 0.7) + i * 1.9)) ** 1.5
            p.setBrush(alfa(pal.ac if i % 2 else pal.al, 255 * enc))
            p.drawRoundedRect(QRectF(pan.left() + 2.5 + i * 2.15, pan.bottom() - 2 - h * enc, 1.4, h * enc), 0.6, 0.6)
        p.setBrush(alfa("#FFFFFF", 255 * enc * (0.5 + 0.5 * math.sin(tg * 3))))
        p.drawEllipse(QPointF(pan.right() - 3.5, pan.top() + 3.6), 0.9, 0.9)
    # perilla
    p.setBrush(QColor("#1A1D25"))
    p.setPen(lapiz(QColor(255, 255, 255, 60), 0.3))
    p.drawEllipse(QPointF(-40, 26), 3, 3)
    p.setPen(lapiz(pal.al, 0.5))
    ang_p = math.radians(-40 + 60 * arranque)
    p.drawLine(QPointF(-40, 26), QPointF(-40 + 2.4 * math.sin(ang_p), 26 - 2.4 * math.cos(ang_p)))
    p.restore()


# ================================================================ 5. modo estudio

def ilus_estudio(p, X):
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)

    # lluvia detrás de todo
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    alto = hh * 2 + 24
    for i in range(34):
        x = -hw + 2 * hw * azar(i, 1)
        v = 22 + 26 * azar(i, 2)
        y = -hh - 12 + ((tg * v + azar(i, 3) * alto) % alto)
        largo = 3.2 + 4.2 * azar(i, 4)
        a = 55 + 90 * azar(i, 5)
        p.setPen(lapiz(alfa(pal.al, a), 0.28 + 0.2 * azar(i, 6)))
        p.drawLine(QPointF(x, y), QPointF(x - largo * 0.18, y + largo))
        if y > hh - 14 - 18 * azar(i, 7) and y < hh - 5:
            e = (y - (hh - 14 - 18 * azar(i, 7))) / 14
            p.setPen(lapiz(alfa(pal.al, 70 * (1 - e)), 0.25))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x, hh - 4), 0.6 + 3.4 * e, 0.3 + 1.2 * e)
    p.restore()

    p.translate(0, (1 - r) * 8)
    brillo(p, -10, -6, 52, pal.ac, 58)

    # anillo del temporizador
    c = QPointF(-14, -8)
    R = 25.0
    frac = ((tg * 0.075) + 0.04) % 1.0
    p.setBrush(QColor(8, 10, 16, 150))
    p.setPen(lapiz(QColor(255, 255, 255, 30), 0.3))
    p.drawEllipse(c, R + 6.2, R + 6.2)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(QColor(255, 255, 255, 34), 3.2))
    p.drawEllipse(c, R, R)
    cono = QConicalGradient(c, 90)
    cono.setColorAt(0.0, pal.al)
    cono.setColorAt(0.7, pal.ac)
    cono.setColorAt(1.0, pal.c3)
    pen = QPen(cono, 3.2)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    barrido = eo(tramo(tl, 0.2, 1.2))
    p.drawArc(QRectF(c.x() - R, c.y() - R, R * 2, R * 2), 90 * 16, int(-(1 - frac) * 360 * 16 * barrido))
    # punta luminosa
    ang = math.radians(90 - (1 - frac) * 360 * barrido)
    brillo(p, c.x() + R * math.cos(ang), c.y() - R * math.sin(ang), 5.5, pal.al, 190)
    seg = int(1500 * (1 - frac))
    texto(p, c.x(), c.y() - 1.6, f"{seg // 60:02d}:{seg % 60:02d}", 11.5, "#FFFFFF", QFont.Black, Qt.AlignCenter, 34)
    texto(p, c.x(), c.y() + 8.2, "ENFOQUE", 2.8, alfa(pal.al, 230), QFont.Bold, Qt.AlignCenter, 24)
    # marcas de los minutos
    for i in range(12):
        a = math.radians(i * 30)
        p.setPen(lapiz(QColor(255, 255, 255, 60), 0.35))
        p.drawLine(QPointF(c.x() + (R + 3.4) * math.cos(a), c.y() + (R + 3.4) * math.sin(a)),
                   QPointF(c.x() + (R + 4.6) * math.cos(a), c.y() + (R + 4.6) * math.sin(a)))

    # Pomodoro: cuatro puntos
    hecho = int(frac * 4)
    for i in range(4):
        x = c.x() - 10.5 + i * 7
        y = c.y() + R + 12.5
        p.setPen(Qt.NoPen)
        if i < hecho:
            p.setBrush(pal.al)
            p.drawEllipse(QPointF(x, y), 2.1, 2.1)
        elif i == hecho:
            pul = 0.5 + 0.5 * math.sin(tg * 4)
            brillo(p, x, y, 5, pal.al, 90 * pul)
            p.setBrush(alfa(pal.al, 120 + 120 * pul))
            p.drawEllipse(QPointF(x, y), 2.1, 2.1)
        else:
            p.setBrush(QColor(255, 255, 255, 50))
            p.drawEllipse(QPointF(x, y), 2.1, 2.1)

    # mezclador de sonidos ambientales
    m = eo(tramo(tl, 0.45, 0.9))
    p.save()
    p.translate((1 - m) * 12, 0)
    p.setOpacity(X.alfa * r * m)
    panel = QRectF(20, -34, 30, 48)
    cristal(p, panel, 4.5, 26, 58)
    nombres = ["Lluvia", "Café", "Olas"]
    for i in range(3):
        x = panel.left() + 6 + i * 9
        y0, y1 = panel.top() + 6, panel.bottom() - 11
        pastilla(p, QRectF(x - 0.7, y0, 1.4, y1 - y0), QColor(255, 255, 255), 56)
        nivel = 0.5 + 0.38 * math.sin(tg * (0.8 + 0.25 * i) + i * 2.1)
        ky = y1 - (y1 - y0) * nivel
        pastilla(p, QRectF(x - 0.7, ky, 1.4, y1 - ky), [pal.al, pal.c2, pal.c3][i], 255)
        brillo(p, x, ky, 4, [pal.al, pal.c2, pal.c3][i], 100)
        p.setPen(lapiz(QColor(255, 255, 255, 230), 0.3))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(x - 2.4, ky - 1.5, 4.8, 3), 1.2, 1.2)
        texto(p, x, panel.bottom() - 5, nombres[i], 2.3, QColor(255, 255, 255, 170), QFont.DemiBold, Qt.AlignCenter, 9)
    p.restore()

    # racha
    k = rebote(tramo(tl, 0.9, 0.8))
    p.save()
    p.translate(35, 25)
    p.scale(k, k)
    pill = QRectF(-15.5, -5.5, 31, 11)
    cristal(p, pill, 5.5, 30, 62)
    fl = QPainterPath()
    oscila = 0.25 * math.sin(tg * 9)
    fl.moveTo(-9.6, 3.6)
    fl.cubicTo(-12.4, 1.2, -10.4, -2.2, -9.2, -3.9 + oscila)
    fl.cubicTo(-8.8, -2.2, -7.8, -1.6, -7.2, -2.6)
    fl.cubicTo(-5.4, -0.6, -6.6, 1.6, -6.2, 2.4)
    fl.cubicTo(-6.8, 4.4, -8.6, 4.6, -9.6, 3.6)
    g = QLinearGradient(-9, -4, -9, 4)
    g.setColorAt(0, QColor("#FFD05A"))
    g.setColorAt(1, QColor("#FF6A3D"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawPath(fl)
    texto(p, -3.2, 0.2, "7 días", 4.4, "#FFFFFF", QFont.Black, Qt.AlignLeft, 18)
    p.restore()
    p.restore()


# ================================================================ 6. música sin cortes

def ilus_musica(p, X):
    pal, tl, tg, hw = X.pal, X.tl, X.tg, X.hw
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, 0, 64, pal.ac, 55)
    n = 46
    ancho = 100.0
    paso = ancho / n
    avance = (tg * 0.16) % 1.0           # la cabeza de lectura recorre las ondas
    cabeza = -ancho / 2 + ancho * avance
    for i in range(n):
        x = -ancho / 2 + paso * (i + 0.5)
        f = (i + 0.5) / n
        # dos canciones: la primera se apaga y la segunda sube, con un cruce en el medio
        amp_a = (0.55 + 0.45 * math.sin(i * 0.9 + 1.3) * math.sin(i * 0.37)) ** 1.0
        amp_b = (0.55 + 0.45 * math.sin(i * 0.7 + 4.1) * math.cos(i * 0.51))
        ca = 1 - liso(f, 0.32, 0.68)
        cb = liso(f, 0.32, 0.68)
        vivo = eo(tramo(tl, 0.15 + 0.012 * i, 0.6))
        for amp, cc, col, dy in ((amp_a, ca, pal.al, -1), (amp_b, cb, pal.c2, 1)):
            h = (3 + 21 * clamp(amp)) * cc * vivo
            if h < 0.4:
                continue
            tocada = x < cabeza
            pulso = 1.0 + (0.14 * math.sin(tg * 6 + i) if abs(x - cabeza) < 8 else 0)
            a = (255 if tocada else 120) * (0.35 + 0.65 * cc)
            p.setPen(Qt.NoPen)
            p.setBrush(alfa(col, a))
            hh_ = h * pulso
            p.drawRoundedRect(QRectF(x - paso * 0.3, -hh_ * 0.5 + dy * 0.0 - 0.0, paso * 0.6, hh_), paso * 0.3, paso * 0.3)
    # cabeza de lectura
    g = QLinearGradient(cabeza, -28, cabeza, 28)
    g.setColorAt(0, QColor(255, 255, 255, 0))
    g.setColorAt(0.5, QColor(255, 255, 255, 220))
    g.setColorAt(1, QColor(255, 255, 255, 0))
    p.setPen(lapiz(g, 0.6))
    p.drawLine(QPointF(cabeza, -28), QPointF(cabeza, 28))
    brillo(p, cabeza, 0, 9, "#FFFFFF", 90)
    # curvas de volumen del cruce
    p.setBrush(Qt.NoBrush)
    sa, sb = QPainterPath(), QPainterPath()
    for i in range(41):
        f = i / 40
        x = -ancho / 2 + ancho * f
        sa.moveTo(x, 38 - 16 * (1 - liso(f, 0.3, 0.7))) if i == 0 else sa.lineTo(x, 38 - 16 * (1 - liso(f, 0.3, 0.7)))
        sb.moveTo(x, 38 - 16 * liso(f, 0.3, 0.7)) if i == 0 else sb.lineTo(x, 38 - 16 * liso(f, 0.3, 0.7))
    p.setPen(lapiz(alfa(pal.al, 230), 0.9))
    p.drawPath(sa)
    p.setPen(lapiz(alfa(pal.c2, 230), 0.9))
    p.drawPath(sb)
    p.setPen(lapiz(QColor(255, 255, 255, 40), 0.25, Qt.FlatCap))
    p.drawLine(QPointF(-50, 38), QPointF(50, 38))
    # el nudo: el cruce no deja silencio
    brillo(p, 0, 30, 7, "#FFFFFF", 70 + 40 * math.sin(tg * 3))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(0, 30), 1.4, 1.4)
    # carátulas de las dos canciones
    for lado, col, col2 in ((-1, pal.al, pal.c3), (1, pal.c2, pal.c4)):
        rect = QRectF(lado * 44 - 7, -46, 14, 14) if lado < 0 else QRectF(30, -46, 14, 14)
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, col)
        g.setColorAt(1, col2)
        p.setPen(lapiz(QColor(255, 255, 255, 70), 0.3))
        p.setBrush(g)
        p.drawRoundedRect(rect, 2.4, 2.4)
        nota(p, rect.center().x() - 0.4, rect.center().y() - 0.4, 8, "#FFFFFF", 1, 220)
    p.restore()


# ================================================================ 7. compartir perfil

def ilus_compartir(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, 0, 60, pal.c2, 52)
    flot = 1.6 * math.sin(tg * 1.3)
    p.translate(0, (1 - r) * 10 + flot)
    # teléfono
    tel = QRectF(-19, -44, 38, 84)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 100))
    p.drawRoundedRect(tel.adjusted(-1, 3, 1, 5), 7, 7)
    p.setPen(lapiz(QColor(255, 255, 255, 120), 0.6))
    p.setBrush(QColor(8, 10, 16))
    p.drawRoundedRect(tel, 7, 7)
    pant = tel.adjusted(1.6, 1.6, -1.6, -1.6)
    ruta = QPainterPath()
    ruta.addRoundedRect(pant, 5.6, 5.6)
    p.save()
    p.setClipPath(ruta)
    g = QLinearGradient(pant.topLeft(), pant.bottomRight())
    g.setColorAt(0, pal.c3)
    g.setColorAt(0.55, pal.ac)
    g.setColorAt(1, pal.c2)
    p.fillRect(pant, g)
    brillo(p, pant.center().x() + 6 * math.sin(tg * 0.7), pant.top() + 20, 24, "#FFFFFF", 60)
    # barra de la historia
    pastilla(p, QRectF(pant.left() + 2.4, pant.top() + 3.5, pant.width() - 4.8, 1.0), QColor(255, 255, 255), 90)
    pastilla(p, QRectF(pant.left() + 2.4, pant.top() + 3.5, (pant.width() - 4.8) * ((tg * 0.2) % 1), 1.0), QColor(255, 255, 255), 255)
    # tarjeta de perfil dentro
    carta = QRectF(pant.left() + 3, pant.top() + 11, pant.width() - 6, 42)
    p.setPen(lapiz(QColor(255, 255, 255, 60), 0.3))
    p.setBrush(QColor(8, 10, 16, 150))
    p.drawRoundedRect(carta, 3, 3)
    cx, cy = carta.center().x(), carta.top() + 11
    cono = QConicalGradient(QPointF(cx, cy), (tg * 60) % 360)
    cono.setColorAt(0, pal.al)
    cono.setColorAt(0.5, pal.c2)
    cono.setColorAt(1, pal.al)
    p.setPen(Qt.NoPen)
    p.setBrush(cono)
    p.drawEllipse(QPointF(cx, cy), 7.2, 7.2)
    p.setBrush(QColor(8, 10, 16))
    p.drawEllipse(QPointF(cx, cy), 6.2, 6.2)
    g2 = QLinearGradient(cx - 5.4, cy - 5.4, cx + 5.4, cy + 5.4)
    g2.setColorAt(0, pal.c2)
    g2.setColorAt(1, pal.ba)
    p.setBrush(g2)
    p.drawEllipse(QPointF(cx, cy), 5.5, 5.5)
    p.setBrush(QColor(255, 255, 255, 230))
    p.drawEllipse(QPointF(cx, cy - 1.4), 2.0, 2.0)
    pastilla(p, QRectF(cx - 7, cy + 9.5, 14, 2.2), QColor(255, 255, 255), 230)
    pastilla(p, QRectF(cx - 10, cy + 14, 20, 1.5), QColor(255, 255, 255), 100)
    for i in range(3):
        pastilla(p, QRectF(cx - 11 + i * 7.6, cy + 19.5, 6.6, 3.8), alfa(pal.al, 200), 255)
    # canción favorita
    pastilla(p, QRectF(carta.left() + 2.6, carta.bottom() + 3, carta.width() - 5.2, 7.2), QColor(8, 10, 16), 150)
    p.setBrush(alfa(pal.al, 255))
    p.drawRoundedRect(QRectF(carta.left() + 3.6, carta.bottom() + 4, 5.2, 5.2), 1, 1)
    pastilla(p, QRectF(carta.left() + 10.4, carta.bottom() + 4.7, 11, 1.2), QColor(255, 255, 255), 220)
    pastilla(p, QRectF(carta.left() + 10.4, carta.bottom() + 7, 7, 1.0), QColor(255, 255, 255), 110)
    # barra «Responder» de historia
    pastilla(p, QRectF(pant.left() + 3, pant.bottom() - 9, pant.width() - 6, 5.4), QColor(255, 255, 255), 70)
    p.restore()
    p.setBrush(QColor(8, 10, 16))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(-4.5, tel.top() + 2.2, 9, 2.4), 1.2, 1.2)

    # las tarjetas que salen volando: la imagen exportada
    s = eo(tramo(tl, 0.7, 1.0))
    for k, (dx, dy, rot, col) in enumerate(((30, -18, 12, pal.al), (36, 6, -8, pal.c2))):
        t = (tg * 0.5 + k * 0.5) % 1.0
        sc = s * (0.9 + 0.1 * math.sin(t * math.pi))
        p.save()
        p.translate(dx + 3 * math.sin(tg + k), dy - 8 * t * 0 + 2 * math.sin(tg * 1.4 + k * 2))
        p.rotate(rot + 4 * math.sin(tg * 0.9 + k))
        p.scale(sc, sc)
        mini = QRectF(-8, -11, 16, 22)
        p.setPen(lapiz(QColor(255, 255, 255, 120), 0.4))
        g = QLinearGradient(mini.topLeft(), mini.bottomRight())
        g.setColorAt(0, col)
        g.setColorAt(1, pal.panel)
        p.setBrush(g)
        p.drawRoundedRect(mini, 2.6, 2.6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawEllipse(QPointF(0, -3.2), 2.6, 2.6)
        pastilla(p, QRectF(-4.6, 1, 9.2, 1.5), QColor(255, 255, 255), 220)
        pastilla(p, QRectF(-3.4, 4, 6.8, 1.2), QColor(255, 255, 255), 120)
        p.restore()

    # botón de compartir con ondas
    b = rebote(tramo(tl, 1.0, 0.8))
    bx, by = 26, 34
    for i in range(2):
        t = (tg * 0.7 + i * 0.5) % 1.0
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(pal.al, 160 * (1 - t)), 0.5))
        p.drawEllipse(QPointF(bx, by), 7 + 9 * t, 7 + 9 * t)
    p.save()
    p.translate(bx, by)
    p.scale(b, b)
    g = QLinearGradient(-7, -7, 7, 7)
    g.setColorAt(0, pal.al)
    g.setColorAt(1, pal.ac)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(0, 0), 7.4, 7.4)
    p.setPen(lapiz(pal.tx, 0.9))
    p.setBrush(Qt.NoBrush)
    dy = -0.6 * math.sin(tg * 4)
    p.drawLine(QPointF(0, 2.6), QPointF(0, -3.6 + dy))
    p.drawPolyline([QPointF(-2.4, -1.2 + dy), QPointF(0, -3.8 + dy), QPointF(2.4, -1.2 + dy)])
    p.drawPolyline([QPointF(-3.4, 0.6), QPointF(-3.4, 3.6), QPointF(3.4, 3.6), QPointF(3.4, 0.6)])
    p.restore()
    for i, (x, y, tam) in enumerate(((-34, -36, 3.6), (38, -40, 2.6), (-38, 28, 2.6))):
        a = 0.5 + 0.5 * math.sin(tg * 2.4 + i * 2)
        destello(p, x, y, tam * (0.6 + 0.6 * a), "#FFFFFF", 240 * a)
    p.restore()


# ================================================================ 8. artistas y parecidos

def ilus_gustos(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa)
    brillo(p, 0, 0, 62, pal.ac, 50)
    ciclo = 9.0
    fase = (tg % ciclo) / ciclo
    # 0..0.45 se reparten, 0.45..0.7 se acercan y se unen, 0.7..1 se separan de nuevo
    junta = liso(fase, 0.42, 0.62) * (1 - liso(fase, 0.78, 0.98))
    colores = [pal.al, pal.c2, pal.c3, pal.c4, pal.ac, pal.al, pal.c2, pal.c3, pal.c4]
    cen = QPointF(0, 0)
    pts = []
    for i in range(9):
        a = i / 9 * 2 * math.pi + tg * (0.10 + 0.04 * azar(i, 1)) + 1.7 * azar(i, 2)
        rad = (19 + 21 * azar(i, 3)) * (1 - 0.5 * junta) + 2.5 * math.sin(tg * 0.9 + i)
        pts.append(QPointF(cen.x() + rad * math.cos(a) * 1.18, cen.y() + rad * math.sin(a) * 0.9))
    tam = [4.2 + 3.0 * azar(i, 4) for i in range(9)]
    # puentes entre burbujas cercanas (como gotas que se funden)
    for i in range(9):
        for j in range(i + 1, 9):
            d = math.hypot(pts[i].x() - pts[j].x(), pts[i].y() - pts[j].y())
            lim = (tam[i] + tam[j]) * 2.1
            if d < lim:
                v = (1 - d / lim)
                aa = tramo(tl, 0.5 + 0.1 * max(i, j), 0.6)
                mix = mezcla(colores[i], colores[j], 0.5)
                p.setPen(lapiz(alfa(mix, 190 * v * aa), min(tam[i], tam[j]) * 1.5 * v))
                p.drawLine(pts[i], pts[j])
    # centro: tu artista
    pulso = 1 + 0.06 * math.sin(tg * 2.6)
    e0 = rebote(tramo(tl, 0.15, 0.8))
    cr = (8.2 + 2.4 * junta) * pulso * e0
    brillo(p, 0, 0, cr * 2.6, pal.al, 110)
    g = QRadialGradient(QPointF(-2, -3), cr * 1.4)
    g.setColorAt(0, QColor("#FFFFFF"))
    g.setColorAt(0.3, pal.al)
    g.setColorAt(1, pal.ac)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(cen, cr, cr)
    p.save()
    p.scale(e0, e0)
    nota(p, -0.4, -0.5, 8.4, pal.tx, 2)
    p.restore()
    for i in range(9):
        aa = rebote(tramo(tl, 0.45 + 0.12 * i, 0.7))
        if aa <= 0:
            continue
        rr = tam[i] * aa * (1 + 0.1 * junta)
        brillo(p, pts[i].x(), pts[i].y(), rr * 2.2, colores[i], 90)
        g = QRadialGradient(QPointF(pts[i].x() - rr * 0.3, pts[i].y() - rr * 0.4), rr * 1.4)
        g.setColorAt(0, mezcla(colores[i], "#FFFFFF", 0.6))
        g.setColorAt(1, colores[i])
        p.setPen(lapiz(QColor(255, 255, 255, 120), 0.3))
        p.setBrush(g)
        p.drawEllipse(pts[i], rr, rr)
        # los elegidos llevan una marca
        if i % 3 == 0:
            p.setPen(lapiz(pal.tx, 0.7))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline([QPointF(pts[i].x() - rr * 0.32, pts[i].y()), QPointF(pts[i].x() - rr * 0.05, pts[i].y() + rr * 0.28),
                            QPointF(pts[i].x() + rr * 0.38, pts[i].y() - rr * 0.26)])
        else:
            nota(p, pts[i].x() - rr * 0.05, pts[i].y() - rr * 0.08, rr * 1.1, pal.tx, 1, 210)
    # ondas hacia fuera del centro (lo parecido)
    for k in range(2):
        t = (tg * 0.45 + k * 0.5) % 1.0
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(pal.al, 120 * (1 - t) * r), 0.45))
        p.drawEllipse(cen, 12 + 26 * t, 12 + 26 * t)
    p.restore()


# ================================================================ 9. portadas de listas

def _arte(p, rect, k, tg, pal):
    """Tres ilustraciones generativas que hacen de «imagen elegida»."""
    ruta = QPainterPath()
    ruta.addRoundedRect(rect, 3.2, 3.2)
    p.save()
    p.setClipPath(ruta)
    if k == 0:                      # atardecer
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        g.setColorAt(0, pal.c3)
        g.setColorAt(0.6, pal.c2)
        g.setColorAt(1, pal.c4)
        p.fillRect(rect, g)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFF3D6"))
        p.drawEllipse(QPointF(rect.center().x(), rect.top() + rect.height() * (0.58 - 0.04 * math.sin(tg))), rect.width() * 0.17, rect.width() * 0.17)
        p.setBrush(alfa(pal.noche, 230))
        base = QPainterPath()
        base.moveTo(rect.left(), rect.bottom())
        for i in range(11):
            base.lineTo(rect.left() + rect.width() * i / 10, rect.top() + rect.height() * (0.74 + 0.07 * math.sin(i * 1.3)))
        base.lineTo(rect.right(), rect.bottom())
        p.drawPath(base)
    elif k == 1:                    # círculos
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, mezcla(pal.ba, "#000000", 0.5))
        g.setColorAt(1, mezcla(pal.c3, "#000000", 0.35))
        p.fillRect(rect, g)
        for i in range(5):
            a = tg * 0.6 + i * 1.3
            col = [pal.ac, pal.c2, pal.al, pal.c3, pal.c4][i]
            brillo(p, rect.center().x() + rect.width() * 0.28 * math.cos(a), rect.center().y() + rect.height() * 0.26 * math.sin(a * 1.2),
                   rect.width() * 0.5, col, 235)
    else:                           # foto de perfil / retrato
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, pal.ba)
        g.setColorAt(1, pal.c3)
        p.fillRect(rect, g)
        p.setPen(Qt.NoPen)
        p.setBrush(alfa("#FFFFFF", 235))
        p.drawEllipse(QPointF(rect.center().x(), rect.top() + rect.height() * 0.4), rect.width() * 0.17, rect.width() * 0.17)
        p.drawEllipse(QPointF(rect.center().x(), rect.bottom() + rect.height() * 0.04), rect.width() * 0.34, rect.width() * 0.3)
    p.restore()


def ilus_portadas(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa)
    brillo(p, 0, 0, 62, pal.c2, 52)
    ciclo = 3.4
    paso = tg / ciclo
    k = int(paso) % 3
    f = liso(paso % 1.0, 0.72, 1.0)       # fundido entre una imagen y la siguiente
    # dos portadas de acompañamiento, en abanico
    for lado in (-1, 1):
        s = eo(tramo(tl, 0.3 + 0.12 * (lado > 0), 0.8))
        p.save()
        p.translate(lado * (22 + 10 * (1 - s)), 7 + 2 * math.sin(tg * 1.1 + lado))
        p.rotate(lado * 9 * s)
        p.setOpacity(X.alfa * s * 0.92)
        rect = QRectF(-15, -15, 30, 30)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.adjusted(-0.5, 2, 0.5, 3), 3.4, 3.4)
        _arte(p, rect, (k + 1 + (lado > 0)) % 3, tg + lado * 3, pal)
        p.setPen(lapiz(QColor(255, 255, 255, 70), 0.3))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, 3.2, 3.2)
        p.restore()
    # portada principal con el cambio de imagen
    s = rebote(tramo(tl, 0.1, 0.9))
    p.save()
    p.translate(0, -3 + 1.4 * math.sin(tg * 1.2))
    p.scale(s, s)
    rect = QRectF(-22, -25, 44, 44)
    p.setOpacity(X.alfa)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 110))
    p.drawRoundedRect(rect.adjusted(1, 3, -1, 2), 4.4, 4.4)
    _arte(p, rect, k, tg, pal)
    if f > 0:
        p.setOpacity(X.alfa * f)
        _arte(p, rect, (k + 1) % 3, tg, pal)
        p.setOpacity(X.alfa)
    # barrido de luz en el cambio
    clip = QPainterPath()
    clip.addRoundedRect(rect, 3.2, 3.2)
    p.save()
    p.setClipPath(clip)
    bx = rect.left() - 20 + 90 * ((paso % 1.0 - 0.7) / 0.3 if paso % 1.0 > 0.7 else -1)
    g = QLinearGradient(bx - 10, rect.top(), bx + 10, rect.bottom())
    g.setColorAt(0, QColor(255, 255, 255, 0))
    g.setColorAt(0.5, QColor(255, 255, 255, 90))
    g.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(rect, g)
    p.restore()
    p.setPen(lapiz(QColor(255, 255, 255, 110), 0.45))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect, 3.2, 3.2)
    # insignia de imagen
    ins = QRectF(rect.right() - 10.5, rect.top() + 2.4, 8.2, 8.2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(8, 10, 16, 190))
    p.drawEllipse(ins)
    p.setPen(lapiz("#FFFFFF", 0.45))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(ins.adjusted(1.9, 2.3, -1.9, -2.3), 0.7, 0.7)
    p.drawPolyline([QPointF(ins.left() + 2.6, ins.bottom() - 2.9), QPointF(ins.center().x() - 0.2, ins.center().y() + 0.2),
                    QPointF(ins.right() - 2.4, ins.bottom() - 3.2)])
    p.restore()
    # título de la lista debajo
    pastilla(p, QRectF(-14, 24, 28, 2.8), QColor(255, 255, 255), 230)
    pastilla(p, QRectF(-9, 29.5, 18, 1.8), QColor(255, 255, 255), 100)
    # el ratón que elige imagen
    cx = 22 + 3 * math.sin(tg * 0.9)
    cy = 20 + 2 * math.cos(tg * 0.9)
    cursor(p, cx, cy, 0.9)
    for i, (x, y, tam) in enumerate(((-40, -32, 3.2), (38, -34, 2.4), (-40, 34, 2.2))):
        a = 0.5 + 0.5 * math.sin(tg * 2.2 + i * 2)
        destello(p, x, y, tam * (0.6 + 0.6 * a), "#FFFFFF", 230 * a)
    p.restore()


# ================================================================ 10. arrastrar

def ilus_arrastrar(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, 0, 62, pal.ac, 52)
    p.translate(0, (1 - r) * 8)
    panel = QRectF(-42, -37, 84, 74)
    cristal(p, panel, 5, 20, 48)
    ciclo = 6.4
    ph = (tg + 1.0) % ciclo
    paso = 12.6
    # d sube de 0 a 1 entre 1.0 y 2.9 y vuelve a 0 entre 4.4 y 6.0
    d = liso(ph, 1.0, 2.9) if ph < 3.7 else 1 - liso(ph, 4.4, 6.0)
    alza = (liso(ph, 0.5, 1.0) * (1 - liso(ph, 3.0, 3.4))) + (liso(ph, 3.7, 4.1) * (1 - liso(ph, 5.7, 6.2)))
    alza = clamp(alza)
    cols = [pal.al, pal.c2, pal.c3, pal.c4, pal.ac]
    nombres = [(15, 9), (17, 8), (12, 10), (16, 7), (13, 9)]
    # fila 3 sube a la posición 1; las filas 1 y 2 bajan una posición
    y0 = panel.top() + 8
    def y_de(slot):
        return y0 + slot * paso
    orden = [0, 1, 2, 3, 4]
    pos = {0: 0.0, 1: 1.0 + d, 2: 2.0 + d, 3: 3.0 - 2.0 * d, 4: 4.0}
    for i in orden:
        if i == 3:
            continue
        _fila(p, panel, y_de(pos[i]), cols[i], nombres[i], pal, tg, 0.0, False)
    # fila arrastrada (encima y levantada)
    ya = y_de(pos[3])
    _fila(p, panel, ya - 1.6 * alza, cols[3], nombres[3], pal, tg, alza, True)
    # el ratón agarra la fila y la mueve
    mx = panel.left() + 8 + 4 * math.sin(tg * 0.8) * 0.0
    cursor(p, panel.right() - 22 + 1.5 * alza, ya + 1.5 - 1.6 * alza, 1.0 - 0.1 * alza)
    # agarradera: puntitos que se iluminan
    p.restore()


def _fila(p, panel, y, color, nombre, pal, tg, alza, activa):
    sc = 1 + 0.045 * alza
    rect = QRectF(panel.left() + 4, y, panel.width() - 8, 11.4)
    p.save()
    c = rect.center()
    p.translate(c)
    p.scale(sc, sc)
    p.translate(-c.x(), -c.y())
    if alza > 0:
        p.setPen(Qt.NoPen)
        for k in range(4):
            p.setBrush(QColor(0, 0, 0, int(26 * alza)))
            p.drawRoundedRect(rect.adjusted(-k * 0.5, 1.8 + k * 1.1, k * 0.5, 1.8 + k * 1.1), 3 + k, 3 + k)
        brillo(p, c.x(), c.y(), 34, pal.al, 40 * alza)
    p.setPen(lapiz(alfa(pal.al, 130 * alza + 34 * (1 - alza)), 0.35))
    p.setBrush(mezcla(pal.panel, "#FFFFFF", 0.07 + 0.08 * alza))
    p.drawRoundedRect(rect, 3, 3)
    # agarradera
    p.setPen(Qt.NoPen)
    for i in range(2):
        for j in range(3):
            p.setBrush(alfa("#FFFFFF" if alza < 0.2 else pal.al, 80 + 170 * alza))
            p.drawEllipse(QPointF(rect.left() + 3.6 + i * 1.7, rect.center().y() - 2.2 + j * 2.2), 0.55, 0.55)
    # carátula
    cara = QRectF(rect.left() + 8, rect.top() + 1.9, 7.6, 7.6)
    g = QLinearGradient(cara.topLeft(), cara.bottomRight())
    g.setColorAt(0, color)
    g.setColorAt(1, mezcla(color, "#000000", 0.45))
    p.setBrush(g)
    p.drawRoundedRect(cara, 1.4, 1.4)
    nota(p, cara.center().x() - 0.2, cara.center().y() - 0.2, 5, "#FFFFFF", 1, 210)
    pastilla(p, QRectF(rect.left() + 18, rect.top() + 3.1, nombre[0], 1.7), QColor(255, 255, 255), 225)
    pastilla(p, QRectF(rect.left() + 18, rect.top() + 6.3, nombre[1], 1.3), QColor(255, 255, 255), 100)
    pastilla(p, QRectF(rect.right() - 11, rect.center().y() - 0.6, 7, 1.2), QColor(255, 255, 255), 80)
    p.restore()


# ================================================================ 11. final

NOTAS = [(azar(i, 11), azar(i, 12), azar(i, 13), azar(i, 14), i % 3) for i in range(22)]


def I_claro(c):
    return mezcla(c, "#FFFFFF", 0.45)


def ilus_final(p, X):
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.0, 1.2))
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    alto = hh * 2 + 30
    cols = [pal.al, pal.c2, pal.c3, pal.ac, pal.c4]
    for i, (ax, ay, av, at, tipo) in enumerate(NOTAS):
        vel = 7 + 8 * av
        y = hh + 12 - ((tg * vel + ay * alto) % alto)
        x = -hw + 2 * hw * ax + 5 * math.sin(tg * (0.6 + av) + i)
        borde = clamp(min((hh - y) / 12.0, (y + hh) / 16.0))
        tam = 4.5 + 5.5 * at
        a = 150 * borde * r * (0.45 + 0.55 * at)
        p.save()
        p.translate(x, y)
        p.rotate(12 * math.sin(tg * 0.9 + i * 1.7))
        brillo(p, 0, 0, tam * 1.3, cols[i % 5], 38 * borde * r)
        nota(p, 0, 0, tam, I_claro(cols[i % 5]), tipo, a)
        p.restore()
    for i in range(10):
        a = 0.5 + 0.5 * math.sin(tg * 2 + i * 1.9)
        destello(p, -hw + 2 * hw * azar(i, 20), -hh + 2 * hh * azar(i, 21) * 0.9, 1.4 + 2.2 * azar(i, 22) * a,
                 "#FFFFFF", 200 * a * r)
    p.restore()


ILUSTRACIONES = {
    "portada": ilus_portada, "fondo": ilus_fondo, "donadores": ilus_donadores, "vinilo": ilus_vinilo,
    "estudio": ilus_estudio, "musica": ilus_musica, "compartir": ilus_compartir, "gustos": ilus_gustos,
    "portadas": ilus_portadas, "arrastrar": ilus_arrastrar, "final": ilus_final,
}
