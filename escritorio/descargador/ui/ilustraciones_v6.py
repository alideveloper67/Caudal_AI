# -*- coding: utf-8 -*-
"""Ilustraciones animadas de la quinta «Actualización grande de Caudal» (2.7.0): visualizador a
pantalla completa, modo karaoke, colores que siguen la carátula, cumpleaños, tu semana y
«¿Qué canción era?».

Mismas reglas que ilustraciones_v5.py: cada una es `ilus_xxx(p, X)` y pinta en un lienzo de
100 x 100 unidades centrado en (0, 0) (la portada y el cierre usan toda la pantalla, `X.hw` y
`X.hh`). Se registran en `ILUSTRACIONES` al importar este módulo, con claves propias (`v6_...`)
para no pisar las de las ediciones anteriores.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainterPath, QRadialGradient

from . import ilustraciones_grandes as I
from .ilustraciones_grandes import (alfa, azar, brillo, clamp, cristal, destello, eo, lapiz, liso, mezcla, nota,
                                    texto, tramo)
from .ilustraciones_v4 import _avatar
from .ilustraciones_v5 import (BLANCO, ORO, ORO_CLARO, ORO_OSCURO, TINTA, _bicho, _icono_altavoz, _icono_micro,
                               _icono_pantalla, _nota_flotante)

NOCHE = QColor("#0B0E1E")
CONFETI = ["#FF5C8A", "#F5C542", "#22D3EE", "#4ADE80", "#8B6CFF", "#FFFFFF"]


# ================================================================ utilidades

def _ancho_txt(cadena, tam, peso=QFont.DemiBold):
    """Ancho en unidades del lienzo de un texto dibujado con `texto()`."""
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(tam * 10)))
    f.setWeight(peso)
    return QFontMetricsF(f).horizontalAdvance(cadena) / 10.0


def _chip(p, cx, y, cadena, tam, color, icono=None, a=255, activa=0.0, alto=None, iw_f=0.62):
    """Píldora de cristal con icono opcional y texto; el aire es el mismo a los dos lados."""
    alto = alto or tam * 2.55
    pad = alto * 0.55
    iw = alto * iw_f if icono else 0.0
    gap = alto * 0.26 if icono else 0.0
    tw = _ancho_txt(cadena, tam)
    ancho = 2 * pad + iw + gap + tw
    r = QRectF(cx - ancho / 2, y - alto / 2, ancho, alto)
    p.save()
    p.setOpacity(p.opacity() * a / 255.0)
    p.setPen(lapiz(alfa(color, 70 + 150 * activa), 0.35 + 0.25 * activa))
    p.setBrush(alfa(mezcla("#FFFFFF", color, 0.5), 20 + 40 * activa))
    p.drawRoundedRect(r, alto / 2, alto / 2)
    x = r.left() + pad
    if icono:
        icono(p, x + iw / 2, y, alto * 0.115, mezcla(color, "#FFFFFF", 0.4), 255)
        x += iw + gap
    texto(p, x, y, cadena, tam, alfa("#FFFFFF", 238), peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=tw + 2)
    p.restore()
    return r


def _estrella_donador(p, x, y, R=2.6):
    p.setPen(lapiz(QColor("#14101F"), 0.4))
    p.setBrush(ORO)
    p.drawEllipse(QPointF(x, y), R, R)
    I.estrella(p, x, y, R * 0.62, R * 0.27, TINTA)


def _nivel(i, n, tg):
    """Nivel (0..1) de la banda i de n de una música inventada que late a 120 pulsaciones."""
    fase = (tg * 2.0) % 1.0
    golpe = math.exp(-fase * 5.0)
    grave = 1.0 - 0.55 * i / max(1, n - 1)
    v = 0.30 * abs(math.sin(tg * 2.1 + i * 0.55)) * (0.65 + 0.35 * math.sin(i * 0.37 + 1)) \
        + 0.22 * abs(math.sin(tg * 3.4 + i * 1.3)) + 0.5 * golpe * grave
    return clamp(v)


def _pulso(tg):
    return math.exp(-((tg * 2.0) % 1.0) * 5.0)


def _gorro(p, cx, cy, s, tg, baile=1.0, fase=0.0):
    """Gorrito de fiesta pegado a la cabeza de `_bicho` (mismos saltos y balanceo)."""
    ritmo = tg * 5.2 + fase
    bota = abs(math.sin(ritmo)) * 2.4 * baile * s
    ladea = math.sin(ritmo * 0.5) * 9 * baile
    aplasta = 1.0 + 0.05 * math.sin(ritmo * 2 + 1.0) * baile
    p.save()
    p.translate(cx, cy - bota)
    p.rotate(ladea)
    p.scale(s * aplasta, s / aplasta)
    p.translate(0, -9.6)
    p.rotate(-10)
    cono = QPainterPath()
    cono.moveTo(-5.4, 0.8)
    cono.lineTo(0.6, -13.0)
    cono.lineTo(5.4, 0.8)
    cono.closeSubpath()
    g = QLinearGradient(-5, -12, 5, 1)
    g.setColorAt(0, QColor("#FFD66B"))
    g.setColorAt(1, QColor("#FF5C8A"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawPath(cono)
    p.save()
    p.setClipPath(cono)
    p.setPen(lapiz(alfa("#FFFFFF", 200), 1.1, Qt.FlatCap))
    for k in range(3):
        y = -9.0 + k * 3.8
        p.drawLine(QPointF(-7, y + 2.2), QPointF(7, y - 2.2))
    p.restore()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#22D3EE"))
    p.drawEllipse(QPointF(0.6, -13.2), 1.7, 1.7)
    p.setBrush(alfa("#FFFFFF", 150))
    p.drawEllipse(QPointF(0.1, -13.8), 0.6, 0.6)
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(-5.8, 0.2, 11.6, 1.8), 0.9, 0.9)
    p.restore()


def _micro(p, cx, cy, s, tg, color, a=255, giro=-35.0):
    """Micrófono de mano con su luz. `s` es la escala (1 = unos 13 unidades de largo)."""
    p.save()
    p.translate(cx, cy)
    p.rotate(giro)
    p.scale(s, s)
    brillo(p, 0, -4.5, 9, color, 70 * a / 255 * (0.7 + 0.3 * math.sin(tg * 3)))
    p.setPen(Qt.NoPen)
    g = QLinearGradient(-1.5, 0, 1.5, 0)
    g.setColorAt(0, QColor("#4A4F7A"))
    g.setColorAt(1, QColor("#1B1F3D"))
    p.setBrush(g)
    cuerpo = QPainterPath()
    cuerpo.moveTo(-1.5, -1.5)
    cuerpo.lineTo(1.5, -1.5)
    cuerpo.lineTo(1.0, 7.0)
    cuerpo.quadTo(0, 8.0, -1.0, 7.0)
    cuerpo.closeSubpath()
    p.drawPath(cuerpo)
    p.setBrush(alfa(color, a))
    p.drawRoundedRect(QRectF(-1.55, 0.6, 3.1, 0.9), 0.4, 0.4)
    gm = QRadialGradient(QPointF(-0.8, -6.2), 4.5)
    gm.setColorAt(0, mezcla(color, "#FFFFFF", 0.6))
    gm.setColorAt(1, mezcla(color, "#000000", 0.2))
    p.setBrush(gm)
    p.drawEllipse(QPointF(0, -4.6), 2.9, 2.9)
    p.setPen(lapiz(alfa("#FFFFFF", 90 * a / 255), 0.2))
    for k in (-1, 0, 1):
        p.drawLine(QPointF(k * 1.2, -7.0), QPointF(k * 1.2, -2.2))
    p.drawLine(QPointF(-2.5, -4.6), QPointF(2.5, -4.6))
    p.restore()


def _globo(p, x, y, s, color, tg, fase=0.0):
    """Globo con su cuerda, que se mece."""
    bal = math.sin(tg * 1.3 + fase) * 1.4
    cx = x + bal
    p.save()
    p.setPen(lapiz(alfa("#FFFFFF", 110), 0.28))
    ruta = QPainterPath()
    ruta.moveTo(cx, y + 6.2 * s)
    ruta.cubicTo(cx - 2 - bal * 0.6, y + 11 * s, cx + 2 + bal * 0.6, y + 15 * s, x - bal * 0.4, y + 20 * s)
    p.setBrush(Qt.NoBrush)
    p.drawPath(ruta)
    g = QRadialGradient(QPointF(cx - 2.2 * s, y - 2.6 * s), 9 * s)
    g.setColorAt(0, mezcla(color, "#FFFFFF", 0.55))
    g.setColorAt(0.55, QColor(color))
    g.setColorAt(1, mezcla(color, "#000000", 0.3))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    cuerpo = QPainterPath()
    cuerpo.moveTo(cx, y + 6.4 * s)
    cuerpo.cubicTo(cx - 8.6 * s, y + 1.2 * s, cx - 6.4 * s, y - 8.2 * s, cx, y - 8.2 * s)
    cuerpo.cubicTo(cx + 6.4 * s, y - 8.2 * s, cx + 8.6 * s, y + 1.2 * s, cx, y + 6.4 * s)
    p.drawPath(cuerpo)
    p.setBrush(QColor(color).darker(125))
    nudo = QPainterPath()
    nudo.moveTo(cx, y + 6.0 * s)
    nudo.lineTo(cx - 1.1 * s, y + 7.8 * s)
    nudo.lineTo(cx + 1.1 * s, y + 7.8 * s)
    nudo.closeSubpath()
    p.drawPath(nudo)
    p.setBrush(alfa("#FFFFFF", 110))
    p.drawEllipse(QPointF(cx - 3.0 * s, y - 4.4 * s), 1.4 * s, 2.3 * s)
    p.restore()


def _confeti_cae(p, n, tg, x0, x1, y0, y1, a, sembrado=50):
    """Confeti que cae por el rectángulo (x0..x1, y0..y1); aparece y se apaga en los bordes."""
    alto = y1 - y0
    for i in range(n):
        ax, ay, av = azar(i, sembrado + 1), azar(i, sembrado + 2), azar(i, sembrado + 3)
        f = ((tg * (0.07 + 0.09 * av) + ay) % 1.0)
        y = y0 + f * alto
        x = x0 + (x1 - x0) * ax + 3.0 * math.sin(tg * (0.9 + av) + i)
        vida = clamp(min(f / 0.12, (1 - f) / 0.18))
        p.save()
        p.translate(x, y)
        p.rotate(360 * azar(i, sembrado + 4) + tg * (60 + 160 * av))
        p.setPen(Qt.NoPen)
        p.setBrush(alfa(CONFETI[i % 6], 235 * vida * a))
        if i % 4 == 0:
            p.drawEllipse(QPointF(0, 0), 0.75, 0.75)
        else:
            p.drawRect(QRectF(-0.95, -0.5, 1.9, 1.0))
        p.restore()


def _barras_mini(p, cx, cy, n, ancho, alto, tg, color, a=255):
    """Un puñado de barras de ecualizador sobre la línea cy (crecen hacia arriba)."""
    paso = ancho / n
    for k in range(n):
        h = alto * (0.18 + 0.82 * _nivel(k * 2 + 1, n * 2, tg))
        x = cx - ancho / 2 + paso * (k + 0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(alfa(mezcla(color, "#FFFFFF", 0.25 * k / max(1, n - 1)), a))
        p.drawRoundedRect(QRectF(x - paso * 0.3, cy - h, paso * 0.6, h), paso * 0.3, paso * 0.3)


# ================================================================ 1. portada

def ilus_portada_v6(p, X):
    """Cintas de sonido que fluyen, notas y confeti por el cielo y, abajo, ecualizador, micro y
    la mascota con su gorrito."""
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.0, 1.4))
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    # cintas de sonido: líneas de luz que laten con la música
    cols = [pal.al, pal.c2, pal.c3, pal.c4, pal.ac]
    pu = _pulso(tg)
    for k in range(5):
        ruta = QPainterPath()
        base = hh * (0.50 + 0.11 * k)
        for s in range(0, 81):
            x = -hw + 2 * hw * s / 80
            env = 0.35 + 0.65 * math.sin(math.pi * s / 80)
            y = base + env * (3.4 + 2.2 * pu) * math.sin(x * (0.06 + 0.008 * k) + tg * (0.9 + 0.15 * k) + k * 1.9) \
                + 1.3 * math.sin(x * 0.17 - tg * (1.2 + 0.1 * k)) + (1 - r) * 26
            ruta.moveTo(x, y) if s == 0 else ruta.lineTo(x, y)
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(cols[k], 34), 2.6))
        p.drawPath(ruta)
        p.setPen(lapiz(alfa(mezcla(cols[k], "#FFFFFF", 0.35), 120 - 12 * k), 0.55))
        p.drawPath(ruta)
    # notas, confeti y brillos por todo el cielo
    for i in range(14):
        ax, ay = azar(i, 61), azar(i, 62)
        vel = 4 + 7 * azar(i, 63)
        alto = hh * 2 + 20
        y = hh + 10 - ((tg * vel + ay * alto) % alto)
        x = -hw + 2 * hw * ax + 4 * math.sin(tg * 0.7 + i)
        borde = clamp(min((hh - y) / 10.0, (y + hh) / 12.0))
        _nota_flotante(p, x, y, 4.0 + 4.0 * azar(i, 64), [pal.al, pal.c2, pal.c3, pal.c4][i % 4],
                       115 * borde * r, 12 * math.sin(tg * 0.9 + i), i % 3)
    _confeti_cae(p, 26, tg, -hw, hw, -hh - 4, hh + 4, 0.8 * r, 70)
    for i in range(12):
        a = 0.5 + 0.5 * math.sin(tg * 2 + i * 1.9)
        destello(p, -hw + 2 * hw * azar(i, 80), -hh + 2 * hh * azar(i, 81) * 0.9, 1.2 + 2.0 * azar(i, 82) * a,
                 "#FFFFFF", 190 * a * r)
    # el trío de abajo, a los lados para dejar el centro al texto
    sube = eo(tramo(tl, 0.5, 1.2))
    # (a los lados y a media altura: el texto ocupa el centro y los botones, las esquinas de abajo)
    py = (1 - sube) * 24
    p.save()
    p.setOpacity(X.alfa * sube)
    _micro(p, -hw * 0.80, 2 + py + 1.0 * math.sin(tg * 1.3), 1.3, tg, pal.c2)
    _barras_mini(p, -hw * 0.80, hh - 15 + py, 6, 11, 13, tg, pal.al)
    _bicho(p, hw * 0.80, 4 + py, 0.78, tg, baile=1.0, fase=0.4)
    _gorro(p, hw * 0.80, 4 + py, 0.78, tg, 1.0, 0.4)
    p.restore()
    p.restore()


# ================================================================ 2. visualizador a pantalla completa

def _modo_ondas(p, cx, cy, ancho, alto, tg, pal):
    pu = _pulso(tg)
    cols = [pal.al, pal.c2, pal.c3, pal.c4]
    for k in range(4):
        ruta = QPainterPath()
        n = 70
        for s in range(n + 1):
            x = cx - ancho / 2 + ancho * s / n
            env = math.sin(math.pi * s / n) ** 0.8
            y = cy + alto * 0.30 * env * (0.45 + 0.75 * pu) * math.sin(x * (0.11 + 0.025 * k) + tg * (2.2 + 0.7 * k) + k * 1.4) \
                + alto * 0.08 * env * math.sin(x * 0.31 - tg * 1.6 + k)
            ruta.moveTo(x, y) if s == 0 else ruta.lineTo(x, y)
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(cols[k], 50), 2.6))
        p.drawPath(ruta)
        p.setPen(lapiz(alfa(mezcla(cols[k], "#FFFFFF", 0.3), 235), 0.8))
        p.drawPath(ruta)


def _modo_particulas(p, cx, cy, radio, tg, pal):
    pu = _pulso(tg)
    brillo(p, cx, cy, radio * 0.9, pal.al, 70 + 70 * pu)
    cols = [pal.al, pal.c2, pal.c3, pal.c4, QColor("#FFFFFF")]
    n = 72
    for i in range(n):
        anillo = i % 3
        r0 = radio * (0.38 + 0.26 * anillo) * (1.0 + 0.12 * pu * (anillo + 1) * 0.5) \
            + radio * 0.07 * math.sin(tg * 1.7 + i)
        ang = azar(i, 91) * math.tau + tg * (0.35 + 0.18 * anillo) * (1 if anillo % 2 == 0 else -1)
        x, y = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 0.9
        tam = 0.45 + 0.75 * azar(i, 92) + 0.5 * pu * azar(i, 93)
        p.setPen(Qt.NoPen)
        p.setBrush(alfa(cols[i % 5], 235))
        p.drawEllipse(QPointF(x, y), tam, tam)
        p.setBrush(alfa(cols[i % 5], 50))
        p.drawEllipse(QPointF(x, y), tam * 2.4, tam * 2.4)
    nucleo = 3.4 + 2.0 * pu
    p.setBrush(alfa("#FFFFFF", 235))
    p.drawEllipse(QPointF(cx, cy), nucleo, nucleo)


def _modo_barras(p, cx, cy, ancho, alto, tg, pal):
    n = 32
    paso = ancho / n
    for k in range(n):
        h = alto * 0.5 * (0.10 + 0.90 * _nivel(k, n, tg))
        x = cx - ancho / 2 + paso * (k + 0.5)
        c = mezcla(pal.al, pal.c2, k / (n - 1))
        p.setPen(Qt.NoPen)
        p.setBrush(alfa(c, 255))
        p.drawRoundedRect(QRectF(x - paso * 0.32, cy - h, paso * 0.64, h), paso * 0.3, paso * 0.3)
        p.setBrush(alfa(c, 85))
        p.drawRoundedRect(QRectF(x - paso * 0.32, cy + 0.8, paso * 0.64, h * 0.55), paso * 0.3, paso * 0.3)


def ilus_visualizador(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 8)
    marco = QRectF(-44, -41, 88, 54)
    brillo(p, 0, -14, 58, pal.al, 40)
    # la pantalla
    sombra = QRectF(marco).adjusted(-0.4, 1.4, 0.4, 1.4)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawRoundedRect(sombra, 3.2, 3.2)
    g = QLinearGradient(marco.topLeft(), marco.bottomRight())
    g.setColorAt(0, mezcla(NOCHE, pal.ac, 0.18))
    g.setColorAt(1, mezcla(NOCHE, pal.c3, 0.10))
    p.setPen(lapiz(alfa("#FFFFFF", 70), 0.4))
    p.setBrush(g)
    p.drawRoundedRect(marco, 3.2, 3.2)
    clip = QPainterPath()
    clip.addRoundedRect(marco.adjusted(0.4, 0.4, -0.4, -0.4), 2.8, 2.8)
    p.save()
    p.setClipPath(clip)
    # tres modos que se turnan cada 3 segundos
    ciclo = tl % 9.0
    modo = int(ciclo // 3)
    loc = ciclo % 3
    aparece = liso(loc, 0.0, 0.45) * (1 - liso(loc, 2.55, 3.0))
    p.save()
    p.setOpacity(p.opacity() * aparece)
    if modo == 0:
        _modo_ondas(p, 0, -8, 76, 36, tg, pal)
    elif modo == 1:
        _modo_particulas(p, 0, -13, 14.5, tg, pal)
    else:
        _modo_barras(p, 0, -6, 76, 34, tg, pal)
    p.restore()
    # etiqueta del modo (arriba a la izquierda) y pantalla completa (arriba a la derecha)
    nombres = ("Ondas", "Partículas", "Barras")
    texto(p, marco.left() + 4.5, marco.top() + 5.2, nombres[modo], 2.7, alfa("#FFFFFF", 200 * aparece),
          peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=30)
    _icono_pantalla(p, marco.right() - 6.4, marco.top() + 5.2, 1.25, alfa("#FFFFFF", 200))
    # barra de reproducción abajo
    yb = marco.bottom() - 4.2
    texto(p, marco.left() + 4.5, yb, "Noche de verano  ·  Caudal", 2.4, alfa("#FFFFFF", 170),
          peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=44)
    p.setPen(lapiz(alfa("#FFFFFF", 50), 0.7))
    p.drawLine(QPointF(marco.left() + 4.5, yb - 3.6), QPointF(marco.right() - 4.5, yb - 3.6))
    prog = (tg * 0.05) % 1.0
    p.setPen(lapiz(pal.al, 0.7))
    x_fin = marco.left() + 4.5 + (marco.width() - 9.0) * prog
    p.drawLine(QPointF(marco.left() + 4.5, yb - 3.6), QPointF(x_fin, yb - 3.6))
    p.restore()
    # los tres modos como fichas
    chips = [("Ondas", pal.al), ("Partículas", pal.c2), ("Barras", pal.c3)]
    anchos = [2 * 2.55 * 3.1 * 0.55 + _ancho_txt(c[0], 3.1) for c in chips]
    gap = 3.2
    x = -(sum(anchos) + gap * 2) / 2
    for k, (nom, col) in enumerate(chips):
        w = anchos[k]
        _chip(p, x + w / 2, 27, nom, 3.1, col, None, 255, 1.0 if k == modo else 0.0)
        x += w + gap
    # insignia de donador
    _estrella_donador(p, marco.right() - 1.0, marco.top() - 1.0, 3.2)
    texto(p, 0, 38, "Para donadores", 2.6, alfa(ORO_CLARO, 230), peso=QFont.DemiBold, ancho=40)
    p.restore()


# ================================================================ 3. modo karaoke

def ilus_karaoke(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 8)
    brillo(p, 0, -18, 60, pal.c2, 42)
    panel = QRectF(-46, -45, 92, 54)
    cristal(p, panel, 4.2, 26, 60)
    lineas = ["Canta conmigo", "Suena fuerte la música", "Caudal pone el ritmo"]
    tam = 6.4
    mx = max(_ancho_txt(s, tam, QFont.Black) for s in lineas)
    if mx > 78:
        tam *= 78 / mx
    ciclo = tl % 8.4
    fade = 1 - liso(ciclo, 7.6, 8.2)
    cols = [pal.al, pal.c2, pal.c3]
    for k, s in enumerate(lineas):
        y = -33 + 14.2 * k
        tw = _ancho_txt(s, tam, QFont.Black)
        x0 = -tw / 2
        avance = clamp((ciclo - 0.6 - 2.1 * k) / 1.9)
        activa = 1.0 if 0 < avance < 1 else 0.0
        p.save()
        p.setOpacity(p.opacity() * (0.6 + 0.4 * fade))
        texto(p, x0, y, s, tam, alfa("#FFFFFF", 66), peso=QFont.Black, alin=Qt.AlignLeft, ancho=tw + 4)
        if avance > 0:
            corte = x0 + tw * avance
            p.save()
            p.setClipRect(QRectF(x0 - 2, y - 7, corte - x0 + 2, 14))
            gr = QLinearGradient(x0, 0, x0 + tw, 0)
            gr.setColorAt(0, ORO_CLARO)
            gr.setColorAt(1, mezcla(cols[k], "#FFFFFF", 0.2))
            brillo(p, corte, y, 9, cols[k], 70 * activa)
            p.save()
            p.translate(0, 0)
            texto(p, x0, y, s, tam, mezcla(ORO_CLARO, cols[k], 0.25 + 0.2 * k), peso=QFont.Black,
                  alin=Qt.AlignLeft, ancho=tw + 4)
            p.restore()
            p.restore()
            if activa:
                p.setPen(Qt.NoPen)
                p.setBrush(alfa("#FFFFFF", 235))
                p.drawEllipse(QPointF(corte, y + 5.6 - 1.4 * abs(math.sin(tg * 6)) ), 0.95, 0.95)
        p.restore()
    # la mascota canta con el micro
    p.save()
    _bicho(p, -25, 31.5, 0.95, tg, baile=0.6, fase=0.3)
    _micro(p, -14.7, 38.1, 0.92, tg, pal.c2, 255, -70.0)
    p.restore()
    for k in range(3):
        f = ((tg * 0.55 + k / 3.0) % 1.0)
        _nota_flotante(p, -36 + 4 * k + 7 * f * (k - 1), 21 - 12 * f, 4.2, [pal.al, pal.c2, pal.c3][k],
                       200 * math.sin(f * math.pi), 14 * math.sin(tg + k), k % 3)
    rc = _chip(p, 22, 31.5, "Modo karaoke", 3.2, pal.c2, _icono_micro)
    _estrella_donador(p, rc.right() - 0.5, rc.top() + 0.4, 3.0)
    texto(p, 22, 40.5, "Para donadores", 2.6, alfa(ORO_CLARO, 230), peso=QFont.DemiBold, ancho=34)
    p.restore()


# ================================================================ 4. colores, sonidos y calidad

_CARATULAS = [("#FF5C8A", "#8B6CFF", "FLAC  ·  24-bit"), ("#22D3EE", "#4ADE80", "M4A  ·  256 kbps"),
              ("#F5C542", "#FF8A3D", "OPUS  ·  160 kbps")]


def _mezcla_caratulas(ciclo):
    """(a, b, texto, k) de la carátula activa, con fundido entre una y la siguiente."""
    seg = ciclo % 9.0
    k = int(seg // 3)
    f = liso(seg % 3, 2.4, 3.0)
    a0, b0, t0 = _CARATULAS[k]
    a1, b1, _t1 = _CARATULAS[(k + 1) % 3]
    return mezcla(a0, a1, f), mezcla(b0, b1, f), t0, k, f


def ilus_colores(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    ca, cb, insignia, k, f = _mezcla_caratulas(tl)
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 8)
    brillo(p, 0, -14, 60, ca, 50)
    ventana = QRectF(-44, -42, 88, 56)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawRoundedRect(ventana.adjusted(-0.4, 1.4, 0.4, 1.4), 3.4, 3.4)
    g = QLinearGradient(ventana.topLeft(), ventana.bottomRight())
    g.setColorAt(0, mezcla(NOCHE, ca, 0.34))
    g.setColorAt(1, mezcla(NOCHE, cb, 0.22))
    p.setPen(lapiz(alfa(mezcla("#FFFFFF", ca, 0.4), 120), 0.45))
    p.setBrush(g)
    p.drawRoundedRect(ventana, 3.4, 3.4)
    # carátula
    art = QRectF(-39, -37, 29, 29)
    sg = QLinearGradient(art.topLeft(), art.bottomRight())
    sg.setColorAt(0, ca)
    sg.setColorAt(1, cb)
    p.setPen(Qt.NoPen)
    p.setBrush(sg)
    p.drawRoundedRect(art, 2.6, 2.6)
    p.save()
    p.setClipRect(art)
    brillo(p, art.left() + 8, art.top() + 7, 14, "#FFFFFF", 70)
    p.restore()
    nota(p, art.center().x() - 0.7, art.center().y() - 2.4, 19, "#FFFFFF", 1, 225)
    # título, artista y la insignia con la calidad real
    xt = -5.5
    texto(p, xt, -32, "Noche de verano", 4.2, BLANCO, peso=QFont.Bold, alin=Qt.AlignLeft, ancho=40)
    texto(p, xt, -26, "Caudal Sessions", 3.0, alfa("#FFFFFF", 170), peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=40)
    tw = _ancho_txt(insignia, 2.8, QFont.Bold)
    pad, alto = 3.0, 6.4
    ins = QRectF(xt, -19.6, tw + 2 * pad, alto)
    p.setPen(lapiz(alfa(mezcla("#FFFFFF", ca, 0.3), 220), 0.4))
    p.setBrush(alfa(mezcla("#FFFFFF", cb, 0.45), 40))
    p.drawRoundedRect(ins, alto / 2, alto / 2)
    texto(p, ins.left() + pad, ins.center().y(), insignia, 2.8, mezcla("#FFFFFF", ca, 0.15), peso=QFont.Bold,
          alin=Qt.AlignLeft, ancho=tw + 2)
    # barra de progreso y botones, todo con el color de la carátula
    p.setPen(lapiz(alfa("#FFFFFF", 50), 0.8))
    p.drawLine(QPointF(-39, -2.4), QPointF(39, -2.4))
    px = -39 + 78 * ((tg * 0.06) % 1.0)
    p.setPen(lapiz(mezcla(ca, "#FFFFFF", 0.25), 0.8))
    p.drawLine(QPointF(-39, -2.4), QPointF(px, -2.4))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(px, -2.4), 1.3, 1.3)
    for j, bx in enumerate((-12, 0, 12)):
        p.setBrush(alfa("#FFFFFF", 60) if j != 1 else mezcla(ca, cb, 0.4))
        p.drawEllipse(QPointF(bx, 7.4), 3.0 if j == 1 else 2.4, 3.0 if j == 1 else 2.4)
    p.setBrush(QColor("#FFFFFF"))
    tri = QPainterPath()
    tri.moveTo(-0.9, 5.7)
    tri.lineTo(-0.9, 9.1)
    tri.lineTo(1.9, 7.4)
    tri.closeSubpath()
    p.drawPath(tri)
    # ficha: los colores siguen la carátula
    y1, y2 = 26.0, 37.5
    tam = 3.0

    def paleta(pp, x, y, t, _c, aa=255):
        for j, c in enumerate((ca, cb, mezcla(ca, cb, 0.5))):
            pp.setPen(lapiz(alfa("#FFFFFF", 170), 0.25))
            pp.setBrush(c)
            pp.drawEllipse(QPointF(x + (j - 1) * 3.6 * t, y), 1.5, 1.5)

    _chip(p, 0, y1, "Colores que siguen la carátula", tam, ca, paleta, iw_f=1.25)
    # ficha: sonidos de interfaz; al «sonar» un aro se abre alrededor
    r2 = _chip(p, 0, y2, "Sonidos de interfaz", tam, pal.c2, _icono_altavoz)
    cic = (tl * 0.8) % 2.4
    if cic < 1.2:
        q = cic / 1.2
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(pal.c2, 190 * (1 - q)), 0.45))
        g_ = 0.5 + 2.4 * q
        p.drawRoundedRect(r2.adjusted(-g_, -g_, g_, g_), r2.height() / 2 + g_, r2.height() / 2 + g_)
    _estrella_donador(p, ventana.right() - 1.5, ventana.top() - 0.5, 3.0)
    p.restore()


# ================================================================ 5. cumpleaños

def ilus_cumple(p, X):
    pal, tl, tg, hw = X.pal, X.tl, X.tg, X.hw
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setClipRect(QRectF(-hw, -50, hw * 2, 100))
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -4, 56, "#FF5C8A", 46)
    _confeti_cae(p, 44, tg, -46, 46, -50, 50, 1.0, 120)
    _globo(p, -37, -20, 1.1, "#FF5C8A", tg, 0.0)
    _globo(p, -22, -33, 0.9, "#F5C542", tg, 1.7)
    _globo(p, 39, -21, 1.0, "#22D3EE", tg, 2.3)
    _globo(p, 24, -34, 0.8, "#8B6CFF", tg, 0.6)
    # la mascota festeja con su gorrito
    ap = eo(tramo(tl, 0.3, 0.9))
    sc = 1.45
    cy = 3 + (1 - ap) * 10
    _bicho(p, 0, cy, sc, tg, baile=0.9, fase=0.2)
    _gorro(p, 0, cy, sc, tg, 0.9, 0.2)
    for k in range(5):
        a = 0.5 + 0.5 * math.sin(tg * 3 + k * 1.7)
        ang = math.radians(-150 + 30 * k)
        destello(p, math.cos(ang) * 25, 3 + math.sin(ang) * 22, 1.0 + 1.6 * a, "#FFFFFF", 200 * a)
    # los amigos saludan, uno tras otro
    nombres = [("#FF5C8A", "#8B6CFF", "¡Felicidades!"), ("#22D3EE", "#4ADE80", "¡Feliz cumple!"),
               ("#F5C542", "#FF8A3D", "¡A celebrar!")]
    ciclo = tl % 6.0
    for k, (c1, c2, frase) in enumerate(nombres):
        x = (k - 1) * 31
        ap = eo(tramo(tl, 0.8 + 0.25 * k, 0.8))
        yy = 40.5 + (1 - ap) * 8 + 0.8 * math.sin(tg * 1.8 + k)
        p.save()
        p.setOpacity(p.opacity() * clamp(ap * 1.4))
        _avatar(p, x, yy, 5.8, QColor(c1), QColor(c2))
        p.restore()
        t_k = ciclo - 0.9 - 1.6 * k
        if 0 <= t_k < 1.9:
            q = eo(tramo(t_k, 0.0, 0.3)) * (1 - liso(t_k, 1.6, 1.9))
            tw = _ancho_txt(frase, 2.4, QFont.Bold)
            ancho, alto = tw + 6.4, 6.0
            by = yy - 11.4 - (1 - q) * 3
            p.save()
            p.setOpacity(p.opacity() * q)
            rb = QRectF(x - ancho / 2, by - alto / 2, ancho, alto)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFFFFF"))
            p.drawRoundedRect(rb, alto / 2, alto / 2)
            pico = QPainterPath()
            pico.moveTo(x - 1.6, by + alto / 2 - 0.2)
            pico.lineTo(x, by + alto / 2 + 2.0)
            pico.lineTo(x + 1.6, by + alto / 2 - 0.2)
            pico.closeSubpath()
            p.drawPath(pico)
            texto(p, x, by, frase, 2.4, "#3A1030", peso=QFont.Bold, ancho=ancho)
            p.restore()
    p.restore()


# ================================================================ 6. tu semana y «¿Qué canción era?»

def ilus_semana(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    p.translate(0, (1 - r) * 8)
    brillo(p, -10, -6, 58, pal.al, 38)
    # --- la tarjeta de la semana
    p.save()
    p.translate(-22, -5)
    p.rotate(-3.5 + 0.8 * math.sin(tg * 0.9))
    carta = QRectF(-26, -35, 52, 66)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawRoundedRect(carta.adjusted(-0.4, 1.4, 0.4, 1.4), 3.4, 3.4)
    g = QLinearGradient(carta.topLeft(), carta.bottomRight())
    g.setColorAt(0, mezcla(pal.ac, "#6A4CFF", 0.5))
    g.setColorAt(1, mezcla(pal.c3, "#FF5C8A", 0.45))
    p.setPen(lapiz(alfa("#FFFFFF", 110), 0.4))
    p.setBrush(g)
    p.drawRoundedRect(carta, 3.4, 3.4)
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(carta, 3.4, 3.4)
    p.setClipPath(clip)
    brillo(p, carta.right() - 4, carta.top() + 5, 26, "#FFFFFF", 60)
    p.restore()
    texto(p, carta.left() + 5, -29, "TU SEMANA", 3.0, alfa("#FFFFFF", 215), peso=QFont.Bold, alin=Qt.AlignLeft, ancho=40)
    texto(p, carta.left() + 5, -19.5, "12 h 40 min", 7.4, BLANCO, peso=QFont.Black, alin=Qt.AlignLeft, ancho=44)
    texto(p, carta.left() + 5, -11.4, "de música escuchada", 2.7, alfa("#FFFFFF", 190), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=44)
    dias = "LMXJVSD"
    alturas = [0.45, 0.7, 0.55, 0.9, 0.75, 1.0, 0.6]
    base = 14.0
    paso = 40.0 / 7
    mejor = 5
    for k in range(7):
        ap = eo(tramo(tl, 0.6 + 0.08 * k, 0.7))
        h = 21.0 * alturas[k] * ap * (1 + 0.05 * math.sin(tg * 2 + k))
        x = carta.left() + 6 + paso * (k + 0.5)
        col = QColor("#F5C542") if k == mejor else alfa("#FFFFFF", 170)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(QRectF(x - 2.1, base - h, 4.2, h), 2.0, 2.0)
        texto(p, x, 19.4, dias[k], 2.6, alfa("#FFFFFF", 215 if k == mejor else 160), peso=QFont.DemiBold, ancho=6)
    p.restore()
    # --- «¿Qué canción era?»
    q = QRectF(8, -26, 39, 50)
    p.save()
    p.translate(0, 1.0 * math.sin(tg * 1.2))
    cristal(p, q, 3.6, 28, 70)
    cx = q.center().x()
    # el oído que escucha: aros que se expanden desde el centro
    ci = QPointF(cx, q.top() + 13)
    for j in range(3):
        f = ((tg * 0.6 + j / 3.0) % 1.0)
        p.setBrush(Qt.NoBrush)
        p.setPen(lapiz(alfa(pal.c2, 190 * (1 - f)), 0.5))
        p.drawEllipse(ci, 3.5 + 7.2 * f, 3.5 + 7.2 * f)
    gb = QRadialGradient(ci + QPointF(-1.5, -1.5), 8)
    gb.setColorAt(0, mezcla(pal.c2, "#FFFFFF", 0.4))
    gb.setColorAt(1, pal.c2)
    p.setPen(Qt.NoPen)
    p.setBrush(gb)
    p.drawEllipse(ci, 5.2, 5.2)
    texto(p, ci.x(), ci.y() + 0.2, "?", 7.4, "#FFFFFF", peso=QFont.Black, ancho=8)
    # una melodía tarareada
    yv = q.top() + 26
    for j in range(11):
        h = 0.8 + 3.4 * abs(math.sin(tg * 3.0 + j * 0.8)) * (0.5 + 0.5 * math.sin(j * 0.5 + 1))
        x = cx - 11 + 2.2 * j
        p.setPen(Qt.NoPen)
        p.setBrush(alfa("#FFFFFF", 200))
        p.drawRoundedRect(QRectF(x - 0.55, yv - h / 2, 1.1, h), 0.55, 0.55)
    # la respuesta
    ciclo = tl % 6.0
    resp = eo(tramo(ciclo, 1.4, 0.6)) * (1 - liso(ciclo, 5.4, 5.9))
    texto(p, cx, q.top() + 32.5, "¿Qué canción era?", 3.0, alfa("#FFFFFF", 235), peso=QFont.Bold, ancho=q.width() - 2)
    pista = QRectF(q.left() + 3.2, q.top() + 36.5, q.width() - 6.4, 9.6)
    p.save()
    p.setOpacity(p.opacity() * resp)
    p.translate(0, (1 - resp) * 3)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa("#FFFFFF", 34))
    p.drawRoundedRect(pista, 2.6, 2.6)
    mini = QRectF(pista.left() + 1.5, pista.top() + 1.5, 6.6, 6.6)
    sg = QLinearGradient(mini.topLeft(), mini.bottomRight())
    sg.setColorAt(0, QColor("#F5C542"))
    sg.setColorAt(1, QColor("#FF5C8A"))
    p.setBrush(sg)
    p.drawRoundedRect(mini, 1.4, 1.4)
    texto(p, mini.right() + 2.2, pista.center().y() - 1.7, "Mar de luz", 2.6, BLANCO, peso=QFont.Bold,
          alin=Qt.AlignLeft, ancho=22)
    texto(p, mini.right() + 2.2, pista.center().y() + 2.0, "¡Era esta!", 2.2, alfa(ORO_CLARO, 235),
          peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=22)
    p.restore()
    p.restore()
    _estrella_donador(p, q.right() - 0.6, q.top() - 0.4, 3.0)
    texto(p, q.center().x(), 33.5, "Para donadores", 2.6, alfa(ORO_CLARO, 230), peso=QFont.DemiBold, ancho=40)
    p.restore()


# ================================================================ 7. cierre

def ilus_final_v6(p, X):
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.0, 1.2))
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    cols = [pal.al, pal.c2, pal.c3, pal.ac, pal.c4]
    alto = hh * 2 + 30
    for i in range(18):
        ax, ay, av, at = azar(i, 131), azar(i, 132), azar(i, 133), azar(i, 134)
        vel = 6 + 8 * av
        y = hh + 12 - ((tg * vel + ay * alto) % alto)
        x = -hw + 2 * hw * ax + 5 * math.sin(tg * (0.6 + av) + i)
        borde = clamp(min((hh - y) / 12.0, (y + hh) / 16.0))
        tam = 4.5 + 5.5 * at
        _nota_flotante(p, x, y, tam, cols[i % 5], 150 * borde * r * (0.45 + 0.55 * at),
                       12 * math.sin(tg * 0.9 + i * 1.7), i % 3)
    _confeti_cae(p, 30, tg, -hw, hw, -hh - 4, hh + 4, 0.75 * r, 150)
    for i in range(12):
        a = 0.5 + 0.5 * math.sin(tg * 2 + i * 1.9)
        destello(p, -hw + 2 * hw * azar(i, 120), -hh + 2 * hh * azar(i, 121) * 0.9, 1.4 + 2.2 * azar(i, 122) * a,
                 "#FFFFFF", 200 * a * r)
    ap = eo(tramo(tl, 0.8, 1.2))
    p.save()
    p.setOpacity(X.alfa * ap)
    yb = hh - 18 + (1 - ap) * 20
    _bicho(p, hw * 0.55, yb, 1.15, tg, baile=0.8, fase=0.9)
    _gorro(p, hw * 0.55, yb, 1.15, tg, 0.8, 0.9)
    _micro(p, -hw * 0.62, yb - 7, 1.6, tg, pal.c2)
    _barras_mini(p, -hw * 0.30, hh - 14 + (1 - ap) * 20, 6, 12, 13, tg, pal.al)
    p.restore()
    p.restore()


I.ILUSTRACIONES.update({
    "v6_portada": ilus_portada_v6, "v6_visualizador": ilus_visualizador, "v6_karaoke": ilus_karaoke,
    "v6_colores": ilus_colores, "v6_cumple": ilus_cumple, "v6_semana": ilus_semana, "v6_final": ilus_final_v6,
})
