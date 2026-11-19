# -*- coding: utf-8 -*-
"""Ilustraciones animadas de la tercera «Actualización grande de Caudal» (escritorio).

Mismas reglas que ilustraciones_grandes.py: cada una es `ilus_xxx(p, X)` y pinta en un lienzo
de 100 x 100 unidades centrado en (0, 0). Se registran en `ILUSTRACIONES` al importar este módulo.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QConicalGradient, QFont, QGradient, QLinearGradient, QPainterPath, QRadialGradient)

from . import ilustraciones_grandes as I
from .ilustraciones_grandes import (alfa, azar, brillo, clamp, cristal, destello, eo, lapiz, liso, mezcla, nota,
                                    pastilla, texto, tramo)

ORO = QColor("#F5C542")
ORO_CLARO = QColor("#FFE08A")
ORO_OSCURO = QColor("#D99A12")
TINTA = QColor("#3A2800")


# ================================================================ utilidades

def _persona(p, cx, cy, R, color):
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(cx, cy - R * 0.18), R * 0.36, R * 0.36)
    ruta = QPainterPath()
    ruta.addEllipse(QPointF(cx, cy + R * 0.95), R * 0.78, R * 0.58)
    p.drawPath(ruta)


def _avatar(p, cx, cy, R, a, b):
    g = QLinearGradient(cx - R, cy - R, cx + R, cy + R)
    g.setColorAt(0, a)
    g.setColorAt(1, b)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawEllipse(QPointF(cx, cy), R, R)
    ruta = QPainterPath()
    ruta.addEllipse(QPointF(cx, cy), R, R)
    p.save()
    p.setClipPath(ruta)
    _persona(p, cx, cy + R * 0.1, R, QColor(255, 255, 255, 225))
    p.restore()


def _anillo(p, cx, cy, R, grosor, colores, giro):
    cono = QConicalGradient(QPointF(cx, cy), giro % 360)
    n = len(colores)
    for i, c in enumerate(colores):
        cono.setColorAt(i / n, c)
    cono.setColorAt(1.0, colores[0])
    p.setPen(lapiz(cono, grosor, Qt.FlatCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(cx, cy), R, R)


def _texto_degradado(p, x, y, cadena, tam, colores, fase):
    """Texto centrado con un degradado que lo recorre (el efecto de nombre)."""
    p.save()
    p.scale(0.1, 0.1)
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(tam * 10)))
    f.setWeight(QFont.Black)
    ruta = QPainterPath()
    ruta.addText(0, 0, f, cadena)
    caja = ruta.boundingRect()
    ruta.translate(x * 10 - caja.width() / 2 - caja.left(), y * 10 - caja.height() / 2 - caja.top())
    ancho = caja.width()
    g = QLinearGradient(x * 10 - ancho / 2 + fase * ancho, 0, x * 10 + ancho / 2 + fase * ancho, 0)
    for i, c in enumerate(colores):
        g.setColorAt(i / (len(colores) - 1), c)
    g.setSpread(QGradient.ReflectSpread)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawPath(ruta)
    p.restore()


def _texto_brillante(p, x, y, cadena, tam, color, a=255, halo=0):
    """Texto con un halo suave: el mismo texto repetido alrededor, muy tenue (así queda alineado)."""
    if halo > 0:
        for radio, alto in ((1.1, 0.16), (0.6, 0.22)):
            for k in range(8):
                ang = k * math.pi / 4
                texto(p, x + math.cos(ang) * radio, y + math.sin(ang) * radio, cadena, tam,
                      alfa(color, halo * alto), peso=QFont.Black, ancho=95)
    texto(p, x, y, cadena, tam, alfa(color, a), peso=QFont.Black, ancho=95)


# ================================================================ marcos y nombres

def ilus_marcos(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -6, 58, pal.ac, 50)
    p.translate(0, (1 - r) * 8)
    R = 16.0
    _avatar(p, 0, -7, R, mezcla(pal.ac, "#FFFFFF", 0.12), mezcla(pal.ac, "#000000", 0.6))
    _anillo(p, 0, -7, R + 2.6, 2.6, [QColor("#22D3EE"), QColor("#8B6CFF"), QColor("#FF5C8A")], tg * 60)
    otros = [
        ([QColor("#B8860B"), QColor("#FFE08A"), QColor("#F5C542"), QColor("#9A6B06")], QColor("#5B4A1A")),
        ([QColor("#FF3D00"), QColor("#FFB000"), QColor("#FF6A00"), QColor("#D50000")], QColor("#5A2A1A")),
        ([QColor("#B3E5FC"), QColor("#FFFFFF"), QColor("#4FC3F7"), QColor("#81D4FA")], QColor("#1A4A66")),
    ]
    for i, (cols, fondo) in enumerate(otros):
        ang = 2 * math.pi * (i / 3 + tg / 24) - math.pi / 2 + 0.6
        x, y = math.cos(ang) * 33, -7 + math.sin(ang) * 18
        _avatar(p, x, y, 6.2, fondo, QColor("#14101F"))
        _anillo(p, x, y, 7.4, 1.2, cols, tg * 90 + i * 100)
    destello(p, 14, -23, 1.2 + 2.2 * (0.5 + 0.5 * math.sin(tg * 2.1)), "#FFFFFF", 230)
    destello(p, -15, 4, 1.0 + 1.9 * (0.5 + 0.5 * math.sin(tg * 1.6 + 1)), "#FFFFFF", 200)
    _texto_degradado(p, 0, 26, "Valentina", 9.5,
                     [QColor("#22D3EE"), QColor("#8B6CFF"), QColor("#FF5C8A"), QColor("#F5C542")], (tg * 0.25) % 1)
    texto(p, 0, 39, "marcos animados · nombres con efecto", 3.2, QColor(255, 255, 255, 150), ancho=96)
    p.restore()


# ================================================================ temas

PALETAS = [
    ("Atardecer", "#2B1224", "#3F1B33", "#FF8A3D"),
    ("Bosque", "#0E2218", "#16352A", "#4ADE80"),
    ("Sakura", "#2A1621", "#3B1F2E", "#FF9EC4"),
    ("Océano", "#0A1F33", "#10304D", "#38BDF8"),
    ("Medianoche", "#0E1030", "#181B49", "#8B6CFF"),
    ("Ámbar", "#241A06", "#38280A", "#F5C542"),
]


def ilus_temas(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, 0, 60, pal.c2, 40)
    p.translate(0, (1 - r) * 8)
    i = int(tg // 2) % 6
    t = liso((tg % 2), 1.5, 2.0)
    a, b = PALETAS[i], PALETAS[(i + 1) % 6]
    fondo, sup, ac = mezcla(a[1], b[1], t), mezcla(a[2], b[2], t), mezcla(a[3], b[3], t)
    tel = QRectF(-17, -43, 34, 74)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 55))
    p.drawRoundedRect(tel.adjusted(-0.6, 1.6, 0.6, 2.6), 6, 6)
    p.setPen(lapiz(QColor(255, 255, 255, 110), 0.5))
    p.setBrush(QColor(20, 23, 29))
    p.drawRoundedRect(tel, 6, 6)
    pant = tel.adjusted(1.4, 1.4, -1.4, -1.4)
    ruta = QPainterPath()
    ruta.addRoundedRect(pant, 5, 5)
    p.save()
    p.setClipPath(ruta)
    p.fillRect(pant, fondo)
    p.fillRect(QRectF(pant.left(), pant.top(), pant.width(), 9), sup)
    pastilla(p, QRectF(pant.left() + 3, pant.top() + 3, 11, 2.4), ac)
    gr = QRectF(pant.left() + 3, pant.top() + 12, pant.width() - 6, 18)
    g = QLinearGradient(gr.topLeft(), gr.bottomRight())
    g.setColorAt(0, ac)
    g.setColorAt(1, mezcla(ac, fondo, 0.7))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(gr, 2.5, 2.5)
    for k in range(3):
        f = QRectF(pant.left() + 3, pant.top() + 33 + k * 7.6, pant.width() - 6, 6.2)
        p.setBrush(sup)
        p.drawRoundedRect(f, 1.6, 1.6)
        p.setBrush(alfa(ac, 230 - k * 50))
        p.drawRoundedRect(QRectF(f.left() + 0.9, f.top() + 0.9, 4.4, 4.4), 1, 1)
        pastilla(p, QRectF(f.left() + 7, f.top() + 1.7, 12 - k * 2, 1.3), QColor(255, 255, 255), 215)
        pastilla(p, QRectF(f.left() + 7, f.top() + 3.6, 7, 0.9), QColor(255, 255, 255), 100)
    barra = QRectF(pant.left(), pant.bottom() - 7, pant.width(), 7)
    p.fillRect(barra, sup)
    p.setBrush(ac)
    p.drawEllipse(barra.center(), 2.2, 2.2)
    p.restore()
    # las seis paletas
    for k in range(6):
        act = (1 - t) if k == i else (t if k == (i + 1) % 6 else 0.0)
        x = (k - 2.5) * 9.2
        rad = 2.1 + 1.3 * act
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PALETAS[k][3]))
        p.drawEllipse(QPointF(x, 38), rad, rad)
        if act > 0.5:
            p.setPen(lapiz(QColor(255, 255, 255, 230), 0.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x, 38), rad + 1.1, rad + 1.1)
    texto(p, 0, 46, (b if t > 0.5 else a)[0], 3.6, QColor(255, 255, 255, 220), ancho=60)
    p.restore()


# ================================================================ pase de prueba

def ilus_pase(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -4, 58, ORO, 46)
    p.translate(0, (1 - r) * 8 + 1.2 * math.sin(tg * 1.0))
    p.save()
    p.translate(0, -5)
    p.rotate(-4 + 1.2 * math.sin(tg * 1.05))
    w, h = 74.0, 36.0
    caja = QRectF(-w / 2, -h / 2, w, h)
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(caja, 4.5, 4.5)
    muescas = QPainterPath()
    muescas.addEllipse(QPointF(caja.left(), 0), 3.6, 3.6)
    muescas.addEllipse(QPointF(caja.right(), 0), 3.6, 3.6)
    boleto = cuerpo.subtracted(muescas)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 55))
    p.save()
    p.translate(0, 1.6)
    p.drawPath(boleto)
    p.restore()
    g = QLinearGradient(caja.topLeft(), caja.bottomRight())
    g.setColorAt(0, ORO_CLARO)
    g.setColorAt(0.5, ORO)
    g.setColorAt(1, ORO_OSCURO)
    p.setBrush(g)
    p.drawPath(boleto)
    # línea punteada
    x0 = caja.left() + w * 0.355
    p.setPen(lapiz(alfa(TINTA, 120), 0.35, Qt.FlatCap))
    y = caja.top() + 4
    while y < caja.bottom() - 3:
        p.drawLine(QPointF(x0, y), QPointF(x0, y + 1.8))
        y += 3.6
    # días
    cd = QPointF(caja.left() + w * 0.185, 0)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa(TINTA, 46), 1.6))
    p.drawEllipse(cd, 9.2, 9.2)
    p.setPen(lapiz(TINTA, 1.6))
    llena = liso(tg % 6, 0.0, 5.0)
    p.drawArc(QRectF(cd.x() - 9.2, -9.2, 18.4, 18.4), 90 * 16, int(-360 * llena * 16))
    texto(p, cd.x(), -1.6, "7", 9.5, TINTA, peso=QFont.Black, ancho=18)
    texto(p, cd.x(), 5.2, "DÍAS", 2.4, TINTA, ancho=18)
    # código
    cx = caja.left() + w * 0.68
    texto(p, cx, -10, "PASE DE PRUEBA", 3.0, TINTA, ancho=40)
    texto(p, cx, 0.5, "K7QM-3XPD", 6.2, TINTA, peso=QFont.Black, ancho=44)
    texto(p, cx, 10.5, "beneficios de donador", 2.7, alfa(TINTA, 190), peso=QFont.DemiBold, ancho=44)
    p.restore()
    for i in range(6):
        ang = 2 * math.pi * (i / 6 + tg / 12)
        destello(p, math.cos(ang) * 46, -5 + math.sin(ang) * 27, 0.8 + 2.2 * (0.5 + 0.5 * math.sin(tg * 2 + i)),
                 ORO_CLARO, 230)
    pastilla(p, QRectF(-31, 31, 62, 9.4), QColor(255, 255, 255), 28)
    p.setPen(lapiz(QColor(255, 255, 255, 80), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(-31, 31, 62, 9.4), 4.7, 4.7)
    texto(p, 0, 35.7, "Canjéalo y disfruta 7 días", 3.8, QColor("#FFFFFF"), ancho=60)
    p.restore()


# ================================================================ letras y tarjetas

def ilus_letras(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, -8, 0, 60, pal.c2, 40)
    p.translate(0, (1 - r) * 8)
    p.save()
    p.translate(-12, 0)
    p.rotate(-4)
    w = 34.0
    h = w * 16 / 9
    caja = QRectF(-w / 2, -h / 2 + 3, w, h)
    sombra = QPainterPath()
    sombra.addRoundedRect(caja.adjusted(-1, 3, 1, 5), 4, 4)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 110))
    p.drawPath(sombra)
    ruta = QPainterPath()
    ruta.addRoundedRect(caja, 4, 4)
    p.save()
    p.setClipPath(ruta)
    g = QLinearGradient(caja.topLeft(), caja.bottomRight())
    g.setColorAt(0, QColor("#3B1E54"))
    g.setColorAt(1, QColor("#0E1030"))
    p.fillRect(caja, g)
    brillo(p, caja.left() + 6, caja.top() + 14, 22, "#FF5C8A", 150)
    brillo(p, caja.right() - 3, caja.bottom() - 18, 24, "#22D3EE", 130)
    car = QRectF(-8, caja.top() + 6.5, 16, 16)
    g2 = QLinearGradient(car.topLeft(), car.bottomRight())
    g2.setColorAt(0, QColor("#FF8A3D"))
    g2.setColorAt(1, QColor("#8B6CFF"))
    p.setBrush(g2)
    p.drawRoundedRect(car, 2.2, 2.2)
    nota(p, car.center().x() - 0.4, car.center().y() - 0.6, 10, "#FFFFFF", 1, 230)
    texto(p, 0, caja.top() + 28, "Tu canción", 3.0, QColor("#FFFFFF"), ancho=30)
    texto(p, 0, caja.top() + 31.4, "Tu artista favorito", 2.1, QColor(255, 255, 255, 170), peso=QFont.DemiBold, ancho=30)
    lineas = ["Cada verso brilla", "cuando lo compartes", "en tu estado"]
    activa = int(tg // 3) % 3
    for i, t in enumerate(lineas):
        y = caja.top() + 38.5 + i * 5.0
        if i == activa:
            _texto_brillante(p, 0, y, t, 2.9, QColor("#FFFFFF"), 255, halo=170)
        else:
            texto(p, 0, y, t, 2.7, QColor(255, 255, 255, 105), peso=QFont.Black, ancho=32)
    texto(p, 0, caja.bottom() - 2.2, "Caudal", 2.3, QColor(255, 255, 255, 200), ancho=20)
    p.restore()
    p.setPen(lapiz(QColor(255, 255, 255, 70), 0.4))
    p.setBrush(Qt.NoBrush)
    p.drawPath(ruta)
    p.restore()
    # formas de compartir
    iconos = [("#25D366", "#128C7E", "Estado"), ("#F58529", "#DD2A7B", "Historia"), ("#FFE08A", "#D99A12", "Video")]
    for i, (a, b, nombre) in enumerate(iconos):
        y = -26 + i * 24 + 1.0 * math.sin(tg * 1.0 + i * 2.1)
        x = 33
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawEllipse(QPointF(x, y + 0.9), 6.2, 6.2)
        g3 = QLinearGradient(x - 6, y - 6, x + 6, y + 6)
        g3.setColorAt(0, QColor(a))
        g3.setColorAt(1, QColor(b))
        p.setBrush(g3)
        p.drawEllipse(QPointF(x, y), 6.0, 6.0)
        p.setBrush(QColor(255, 255, 255))
        if i == 0:
            p.drawRoundedRect(QRectF(x - 2.8, y - 2.6, 5.6, 4.4), 1.4, 1.4)
            ptr = QPainterPath()
            ptr.moveTo(x - 1.6, y + 1.6)
            ptr.lineTo(x - 3.1, y + 3.4)
            ptr.lineTo(x + 0.4, y + 1.8)
            p.drawPath(ptr)
        elif i == 1:
            p.drawRoundedRect(QRectF(x - 3, y - 2.4, 6, 4.8), 1.2, 1.2)
            p.setBrush(QColor(b))
            p.drawEllipse(QPointF(x, y), 1.3, 1.3)
        else:
            p.drawRoundedRect(QRectF(x - 3, y - 2.2, 6, 4.6), 0.8, 0.8)
            p.setBrush(QColor(b))
            p.drawRect(QRectF(x - 3, y - 3.2, 6, 1.1))
        texto(p, x, y + 9.4, nombre, 2.5, QColor(255, 255, 255, 200), ancho=22)
    p.restore()


# ================================================================ tu año en Caudal

def ilus_anio(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -10, 60, pal.c2, 42)
    ciclo = tg % 12
    texto(p, 0, -43, "TU AÑO EN CAUDAL", 3.0, QColor(255, 255, 255, 170), ancho=70)
    n = int(12480 * liso(ciclo, 0.3, 3.5))
    cadena = f"{n // 1000} {n % 1000:03d}" if n >= 1000 else str(n)
    texto(p, 0, -31, cadena, 12.5, QColor("#FFFFFF"), peso=QFont.Black, ancho=90)
    texto(p, 0, -21.2, "minutos de música", 3.4, pal.al, ancho=70)
    alturas = [0.30, 0.42, 0.36, 0.55, 0.48, 0.62, 0.58, 0.72, 0.66, 0.86, 0.78, 1.0]
    base = 22.0
    paso = 7.4
    x0 = -paso * 5.5
    for i, a in enumerate(alturas):
        pr = liso(ciclo, 0.5 + i * 0.15, 1.6 + i * 0.15)
        hh = 26 * a * pr
        rect = QRectF(x0 + i * paso - 2.5, base - hh, 5.0, hh)
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if i == 11:
            g.setColorAt(0, ORO_CLARO)
            g.setColorAt(1, ORO_OSCURO)
        else:
            g.setColorAt(0, mezcla(pal.al, "#FFFFFF", 0.25))
            g.setColorAt(1, mezcla(pal.ac, "#8B6CFF", 0.6))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(rect, 2.0, 2.0)
    p.setPen(lapiz(QColor(255, 255, 255, 50), 0.3))
    p.drawLine(QPointF(x0 - 4, base + 0.5), QPointF(x0 + paso * 11 + 4, base + 0.5))
    # podio
    cols = [pal.c2, pal.al, pal.c3]
    for i, (num, alto) in enumerate((("2", 7.0), ("1", 10.5), ("3", 5.0))):
        x = (i - 1) * 22
        ap = liso(ciclo, 3.6 + i * 0.3, 4.6 + i * 0.3)
        p.save()
        p.setOpacity(X.alfa * r * ap)
        _avatar(p, x, 33 - 7 * 0 + (1 - ap) * 5, 4.2 if i != 1 else 5.2, cols[i], QColor("#14101F"))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        rr = QRectF(x - 8.5, 38.5, 17, alto)
        p.drawRoundedRect(rr, 1.4, 1.4)
        texto(p, x, rr.center().y(), num, 4.0, QColor(255, 255, 255, 220), peso=QFont.Black, ancho=17)
        p.restore()
    p.restore()


# ================================================================ fluidez

def ilus_fluido(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -3, 58, QColor("#34D399"), 38)
    p.translate(0, (1 - r) * 8)
    cx, cy, R = 0.0, -2.0, 33.0
    caja = QRectF(cx - R, cy - R, 2 * R, 2 * R)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(QColor(255, 255, 255, 36), 4.4, Qt.FlatCap))
    p.drawArc(caja, 216 * 16, -252 * 16)      # de abajo-izquierda, pasando por arriba, a abajo-derecha
    fin = 0.92 + 0.02 * math.sin(tg * 2.0)
    pasos = 70
    colores = [QColor("#FFB000"), QColor("#4ADE80"), QColor("#22D3EE")]
    for k in range(int(pasos * fin)):
        t = k / pasos
        c = mezcla(colores[0], colores[1], t * 2) if t < 0.5 else mezcla(colores[1], colores[2], (t - 0.5) * 2)
        p.setPen(lapiz(c, 4.4, Qt.FlatCap))
        p.drawArc(caja, int((216 - 252 * t) * 16), int(-252 / pasos * 16) - 8)
    for i in range(11):
        a = math.radians(216 - 252 * i / 10)
        p.setPen(lapiz(QColor(255, 255, 255, 120), 0.4))
        p.drawLine(QPointF(cx + math.cos(a) * (R - 5.5), cy - math.sin(a) * (R - 5.5)),
                   QPointF(cx + math.cos(a) * (R - 8), cy - math.sin(a) * (R - 8)))
    ang = math.radians(216 - 252 * fin)
    p.setPen(lapiz(QColor("#FFFFFF"), 1.3))
    p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(ang) * (R - 10), cy - math.sin(ang) * (R - 10)))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(cx, cy), 2.8, 2.8)
    texto(p, 0, 17, "60", 11, QColor("#FFFFFF"), peso=QFont.Black, ancho=40)
    texto(p, 0, 26, "cuadros por segundo", 3.2, QColor(255, 255, 255, 170), ancho=60)
    # ajustes al instante
    pastilla(p, QRectF(-27, 33, 54, 8.6), QColor(255, 255, 255), 26)
    p.setPen(lapiz(QColor(255, 255, 255, 80), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(-27, 33, 54, 8.6), 4.3, 4.3)
    texto(p, 0, 37.3, "Ajustes abre al instante", 3.6, QColor("#FFFFFF"), ancho=54)
    p.restore()


I.ILUSTRACIONES.update({
    "marcos": ilus_marcos, "temas": ilus_temas, "pase": ilus_pase, "letras": ilus_letras,
    "anio": ilus_anio, "fluido": ilus_fluido,
})
