# -*- coding: utf-8 -*-
"""Ilustraciones animadas de la cuarta «Actualización grande de Caudal» (2.6.0): modo gamer,
el personaje que cobra vida y los regalos de prueba.

Mismas reglas que ilustraciones_v4.py: cada una es `ilus_xxx(p, X)` y pinta en un lienzo de
100 x 100 unidades centrado en (0, 0) (la portada y el cierre usan toda la pantalla, `X.hw` y
`X.hh`). Se registran en `ILUSTRACIONES` al importar este módulo, con claves propias para no
pisar las de las ediciones anteriores.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainterPath, QRadialGradient

from . import ilustraciones_grandes as I
from .ilustraciones_grandes import (alfa, azar, brillo, clamp, destello, eo, lapiz, liso, mezcla, nota, pastilla,
                                    texto, tramo)

ORO = QColor("#F5C542")
ORO_CLARO = QColor("#FFE08A")
ORO_OSCURO = QColor("#D99A12")
TINTA = QColor("#3A2800")
BLANCO = QColor("#FFFFFF")
FONDO_JUEGO = QColor("#0B0E1E")


# ================================================================ utilidades

def _neon(tg, desfase=0.0, v=1.0, s=0.75):
    return QColor.fromHsvF((tg * 0.12 + desfase) % 1.0, s, v)


def _panel(p, rect, radio, relleno="#14101F", borde=None, a=255, a_borde=90):
    p.setPen(lapiz(alfa(borde, a_borde), 0.4) if borde is not None else Qt.NoPen)
    p.setBrush(alfa(relleno, a))
    p.drawRoundedRect(rect, radio, radio)


def _caratula(p, rect, a, b, radio=1.6, tg=0.0, nota_=True):
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor(a))
    g.setColorAt(1, QColor(b))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(rect, radio, radio)
    if nota_:
        nota(p, rect.center().x() - rect.width() * 0.03, rect.center().y() - rect.height() * 0.09,
             rect.width() * 0.62, "#FFFFFF", 1, 225)


def _mando(p, cx, cy, tam, tg, color, a=255):
    """Mando de consola con luz neón. `tam` es el ancho en unidades."""
    s = tam / 28.0
    p.save()
    p.translate(cx, cy)
    p.scale(s, s)
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(-12.5, -7, 25, 13.5), 6.5, 6.5)
    for sx in (-1, 1):
        agarre = QPainterPath()
        agarre.addEllipse(QPointF(sx * 10.6, 5.2), 5.0, 7.4)
        ruta = ruta.united(agarre)
    brillo(p, 0, 0, 24, color, 70 * a / 255)
    g = QLinearGradient(0, -8, 0, 12)
    g.setColorAt(0, mezcla("#3A3F66", color, 0.18))
    g.setColorAt(1, QColor("#161A33"))
    p.setPen(lapiz(alfa(color, 235 * a / 255), 0.7))
    p.setBrush(g)
    p.drawPath(ruta)
    # cruceta
    p.setPen(Qt.NoPen)
    p.setBrush(alfa("#C9CCE6", a))
    p.drawRoundedRect(QRectF(-9.4, -2.1, 6.6, 2.2), 0.7, 0.7)
    p.drawRoundedRect(QRectF(-7.2, -4.3, 2.2, 6.6), 0.7, 0.7)
    # botones
    cols = ["#4ADE80", "#FF5C8A", "#22D3EE", "#F5C542"]
    for k, (bx, by) in enumerate(((8.6, -0.1), (11.2, -2.7), (6.0, -2.7), (8.6, -5.3))):
        viva = 0.5 + 0.5 * math.sin(tg * 3.0 + k * 1.6)
        p.setBrush(alfa(cols[k], (150 + 105 * viva) * a / 255))
        p.drawEllipse(QPointF(bx, by + 2.2), 1.15, 1.15)
    # palancas
    for px, py in ((-4.2, 3.6), (4.6, 3.6)):
        p.setBrush(alfa("#0B0E1E", a))
        p.drawEllipse(QPointF(px, py), 2.1, 2.1)
        p.setBrush(alfa("#6C7096", a))
        p.drawEllipse(QPointF(px, py), 1.2, 1.2)
    p.restore()


def _bicho(p, cx, cy, s, tg, a_cuerpo="#8B6CFF", b_cuerpo="#FF5C8A", baile=1.0, brazos=1.0, fase=0.0, boca=True):
    """El personaje de Caudal: una bolita con orejas, auriculares y ganas de bailar.
    `s` es la escala (1 = unos 22 unidades de ancho); `baile` va de 0 (quieto) a 1."""
    ritmo = tg * 5.2 + fase
    bota = abs(math.sin(ritmo)) * 2.4 * baile * s
    ladea = math.sin(ritmo * 0.5) * 9 * baile
    aplasta = 1.0 + 0.05 * math.sin(ritmo * 2 + 1.0) * baile
    p.save()
    p.translate(cx, cy - bota)
    p.rotate(ladea)
    p.scale(s * aplasta, s / aplasta)
    # patitas
    p.setPen(Qt.NoPen)
    for sx in (-1, 1):
        p.setBrush(mezcla(b_cuerpo, "#000000", 0.25))
        p.drawEllipse(QPointF(sx * 4.6, 9.4), 3.0, 2.0)
    # brazos
    for sx in (-1, 1):
        ang = math.radians(35 + 70 * brazos * (0.5 + 0.5 * math.sin(ritmo + (0 if sx < 0 else math.pi))) * baile - 20)
        bx, by = sx * 10.4, 1.5
        ex, ey = bx + sx * math.sin(ang) * 4.6, by - math.cos(ang) * 4.6 + 3
        p.setPen(lapiz(mezcla(a_cuerpo, "#000000", 0.18), 2.6))
        p.drawLine(QPointF(bx, by), QPointF(ex, ey))
        p.setPen(Qt.NoPen)
        p.setBrush(mezcla(a_cuerpo, "#FFFFFF", 0.2))
        p.drawEllipse(QPointF(ex, ey), 1.7, 1.7)
    # orejas
    for sx in (-1, 1):
        oreja = QPainterPath()
        oreja.moveTo(sx * 4.2, -8.0)
        oreja.quadTo(sx * 10.5, -15.5, sx * 11.2, -7.0)
        oreja.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(mezcla(a_cuerpo, "#000000", 0.1))
        p.drawPath(oreja)
        interior = QPainterPath()
        interior.moveTo(sx * 5.8, -8.4)
        interior.quadTo(sx * 9.4, -12.6, sx * 9.8, -8.0)
        interior.closeSubpath()
        p.setBrush(alfa("#FFB3CF", 200))
        p.drawPath(interior)
    # cuerpo
    g = QLinearGradient(-9, -10, 9, 11)
    g.setColorAt(0, mezcla(a_cuerpo, "#FFFFFF", 0.22))
    g.setColorAt(1, b_cuerpo if isinstance(b_cuerpo, QColor) else QColor(b_cuerpo))
    p.setBrush(g)
    p.drawEllipse(QPointF(0, 0), 11.2, 10.2)
    p.setBrush(alfa("#FFFFFF", 38))
    p.drawEllipse(QPointF(-3.2, -5.4), 5.2, 2.6)
    # barriguita
    p.setBrush(alfa("#FFFFFF", 70))
    p.drawEllipse(QPointF(0, 5.2), 5.2, 3.8)
    # ojos
    parpadeo = 1.0 - 0.9 * (1.0 if (tg * 0.8 + fase) % 3.7 > 3.55 else 0.0)
    for sx in (-1, 1):
        p.setBrush(QColor("#1A1030"))
        p.drawEllipse(QPointF(sx * 4.2, -0.8), 1.9, 2.5 * parpadeo)
        p.setBrush(BLANCO)
        p.drawEllipse(QPointF(sx * 4.2 - 0.6, -1.8), 0.7, 0.8 * parpadeo)
        p.setBrush(alfa("#FF7BA8", 150))
        p.drawEllipse(QPointF(sx * 7.0, 2.6), 1.9, 1.2)
    # boca
    if boca:
        abierta = (0.5 + 0.5 * math.sin(ritmo * 2)) * baile
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#5A1030"))
        p.drawEllipse(QPointF(0, 3.3), 1.5, 0.8 + 1.1 * abierta)
    # auriculares
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(QColor("#22D3EE"), 1.5))
    p.drawArc(QRectF(-10.4, -11.4, 20.8, 19.0), 12 * 16, 156 * 16)
    for sx in (-1, 1):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0E1030"))
        p.drawRoundedRect(QRectF(sx * 10.6 - 2.1, -3.6, 4.2, 7.2), 1.8, 1.8)
        p.setBrush(alfa("#22D3EE", 230))
        p.drawRoundedRect(QRectF(sx * 10.6 - 1.0, -2.2, 2.0, 4.4), 1.0, 1.0)
    p.restore()


def _nota_flotante(p, x, y, tam, color, a, giro=0.0, tipo=0):
    p.save()
    p.translate(x, y)
    p.rotate(giro)
    brillo(p, 0, 0, tam * 1.2, color, 30 * a / 255)
    nota(p, 0, 0, tam, mezcla(color, "#FFFFFF", 0.4), tipo, a)
    p.restore()


def _icono_altavoz(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    ruta = QPainterPath()
    ruta.moveTo(-1.6, -0.9)
    ruta.lineTo(-0.4, -0.9)
    ruta.lineTo(1.0, -2.1)
    ruta.lineTo(1.0, 2.1)
    ruta.lineTo(-0.4, 0.9)
    ruta.lineTo(-1.6, 0.9)
    ruta.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    p.drawPath(ruta)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa(color, a), 0.34))
    p.drawArc(QRectF(-0.6, -1.4, 2.8, 2.8), -50 * 16, 100 * 16)
    p.drawArc(QRectF(-1.0, -2.0, 4.0, 4.0), -50 * 16, 100 * 16)
    p.restore()


def _icono_micro(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    p.drawRoundedRect(QRectF(-0.8, -2.1, 1.6, 2.8), 0.8, 0.8)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa(color, a), 0.3))
    p.drawArc(QRectF(-1.35, -1.2, 2.7, 2.6), 180 * 16, 180 * 16)
    p.drawLine(QPointF(0, 1.4), QPointF(0, 2.2))
    p.drawLine(QPointF(-0.7, 2.2), QPointF(0.7, 2.2))
    p.restore()


def _icono_pantalla(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa(color, a), 0.34))
    for sx in (-1, 1):
        for sy in (-1, 1):
            ruta = QPainterPath()
            ruta.moveTo(sx * 0.9, sy * 2.0)
            ruta.lineTo(sx * 2.0, sy * 2.0)
            ruta.lineTo(sx * 2.0, sy * 0.9)
            p.drawPath(ruta)
    p.restore()


def _icono_mando(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(-2.1, -1.2, 4.2, 2.4), 1.1, 1.1)
    for sx in (-1, 1):
        e = QPainterPath()
        e.addEllipse(QPointF(sx * 1.6, 0.7), 0.8, 1.1)
        ruta = ruta.united(e)
    p.drawPath(ruta)
    p.setBrush(alfa("#14101F", a))
    p.drawRect(QRectF(-1.5, -0.2, 1.0, 0.32))
    p.drawRect(QRectF(-1.16, -0.54, 0.32, 1.0))
    p.drawEllipse(QPointF(1.1, -0.2), 0.2, 0.2)
    p.drawEllipse(QPointF(1.6, 0.25), 0.2, 0.2)
    p.restore()


def _fuente_texto(tam):
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(tam * 10)))
    f.setWeight(QFont.DemiBold)
    return f


def _ficha(p, cx, y, ancho, alto, cadena, color, icono, tam_t=2.9, a=255, activa=0.0):
    """Píldora de cristal con un icono a la izquierda y un texto."""
    fm = QFontMetricsF(_fuente_texto(tam_t))
    tw = fm.horizontalAdvance(cadena) / 10.0
    ancho = alto * 1.3 + tw + alto * 0.75            # icono + texto + el mismo aire a los dos lados
    r = QRectF(cx - ancho / 2, y - alto / 2, ancho, alto)
    p.setPen(lapiz(alfa(color, 60 + 140 * activa), 0.35 + 0.25 * activa))
    p.setBrush(alfa(mezcla("#FFFFFF", color, 0.5), 18 + 34 * activa))
    p.drawRoundedRect(r, alto / 2, alto / 2)
    icono(p, r.left() + alto * 0.62, y, alto * 0.135, mezcla(color, "#FFFFFF", 0.35), a)
    texto(p, r.left() + alto * 1.3, y, cadena, tam_t, alfa("#FFFFFF", 235), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=tw + alto * 0.6)


# ================================================================ 1. portada

def ilus_portada_v5(p, X):
    """Fondo de aurora con olas de neón y, abajo, mando, regalo y el personaje bailando."""
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.0, 1.4))
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    # olas
    cols = [pal.c3, pal.ac, pal.al, pal.c2]
    for k in range(4):
        ruta = QPainterPath()
        ruta.moveTo(-hw, hh)
        for s in range(0, 61):
            x = -hw + 2 * hw * s / 60
            y = hh * (0.55 + 0.1 * k) + 3.4 * math.sin(x * (0.05 + 0.007 * k) + tg * (0.5 + 0.1 * k) + k * 1.7) \
                + 1.8 * math.sin(x * 0.11 - tg * (0.7 + 0.06 * k) + k)
            ruta.lineTo(x, y + (1 - r) * 30)
        ruta.lineTo(hw, hh)
        ruta.closeSubpath()
        g = QLinearGradient(0, hh * 0.45, 0, hh)
        g.setColorAt(0, alfa(cols[k], 70 - 8 * k))
        g.setColorAt(1, alfa(cols[k], 6))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(ruta)
    # notas y brillos por todo el cielo
    for i in range(16):
        ax, ay = azar(i, 1), azar(i, 2)
        vel = 4 + 7 * azar(i, 3)
        alto = hh * 2 + 20
        y = hh + 10 - ((tg * vel + ay * alto) % alto)
        x = -hw + 2 * hw * ax + 4 * math.sin(tg * 0.7 + i)
        borde = clamp(min((hh - y) / 10.0, (y + hh) / 12.0))
        _nota_flotante(p, x, y, 4.0 + 4.0 * azar(i, 4), [pal.al, pal.c2, pal.c3, pal.c4][i % 4],
                       120 * borde * r, 12 * math.sin(tg * 0.9 + i), i % 3)
    for i in range(14):
        a = 0.5 + 0.5 * math.sin(tg * 2 + i * 1.9)
        destello(p, -hw + 2 * hw * azar(i, 20), -hh + 2 * hh * azar(i, 21) * 0.9, 1.2 + 2.0 * azar(i, 22) * a,
                 "#FFFFFF", 190 * a * r)
    # el trío de abajo, a los lados para dejar el centro al texto
    sube = eo(tramo(tl, 0.5, 1.2))
    yb = hh - 19
    py = (1 - sube) * 24
    p.save()
    p.setOpacity(X.alfa * sube)
    _mando(p, -hw * 0.48, yb + py + 1.0 * math.sin(tg * 1.3), 22, tg, _neon(tg))
    _bicho(p, hw * 0.46, yb + py + 3, 0.88, tg, baile=1.0, fase=0.4)
    # regalo pequeño
    _regalo(p, -hw * 0.82, yb + py + 1.0, 0.62, tg, 0.0)
    p.restore()
    p.restore()


# ================================================================ 2. modo gamer

def ilus_gamer(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    neon = _neon(tg)
    brillo(p, 0, -14, 62, neon, 40)
    p.translate(0, (1 - r) * 8)
    # monitor con un juego de fondo
    m = QRectF(-43, -46, 86, 49)
    p.setPen(lapiz(alfa(neon, 220), 0.8))
    p.setBrush(FONDO_JUEGO)
    p.drawRoundedRect(m, 2.6, 2.6)
    ruta = QPainterPath()
    pant = m.adjusted(1.1, 1.1, -1.1, -1.1)
    ruta.addRoundedRect(pant, 1.9, 1.9)
    p.save()
    p.setClipPath(ruta)
    cielo = QLinearGradient(pant.topLeft(), pant.bottomLeft())
    cielo.setColorAt(0, QColor("#1B1245"))
    cielo.setColorAt(0.6, QColor("#7A2A6B"))
    cielo.setColorAt(1, QColor("#FF8A3D"))
    p.fillRect(pant, cielo)
    brillo(p, pant.center().x() + 8, pant.top() + 20, 14, "#FFE08A", 200)
    for k, (col, alt, off) in enumerate((("#2A1450", 13, 0.0), ("#170B33", 9, 1.7))):
        mon = QPainterPath()
        mon.moveTo(pant.left(), pant.bottom())
        for s in range(0, 22):
            x = pant.left() + pant.width() * s / 21
            mon.lineTo(x, pant.bottom() - alt * (0.55 + 0.45 * abs(math.sin(s * 0.9 + off))) - k * 1.5)
        mon.lineTo(pant.right(), pant.bottom())
        mon.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(col))
        p.drawPath(mon)
    # mira y marcadores del juego
    cx, cy = pant.center().x() - 12 + 3 * math.sin(tg * 0.8), pant.center().y() - 3 + 2 * math.cos(tg * 1.1)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa("#FFFFFF", 200), 0.4))
    p.drawEllipse(QPointF(cx, cy), 2.6, 2.6)
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        p.drawLine(QPointF(cx + math.cos(a) * 1.6, cy + math.sin(a) * 1.6),
                   QPointF(cx + math.cos(a) * 4.2, cy + math.sin(a) * 4.2))
    pastilla(p, QRectF(pant.left() + 2.2, pant.top() + 2.2, 17, 2.2), QColor("#4ADE80"), 200)
    pastilla(p, QRectF(pant.left() + 2.2, pant.top() + 5.4, 11, 1.6), QColor("#FFFFFF"), 80)
    # mini reproductor flotante, encima del juego
    flota = 0.7 * math.sin(tg * 1.5)
    mp = QRectF(pant.right() - 33.5, pant.bottom() - 14.2 + flota, 31.5, 12.2)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(mp.translated(0, 0.9), 2.6, 2.6)
    p.setPen(lapiz(alfa(neon, 210), 0.45))
    p.setBrush(alfa("#14101F", 235))
    p.drawRoundedRect(mp, 2.6, 2.6)
    _caratula(p, QRectF(mp.left() + 1.4, mp.top() + 1.4, 9.4, 9.4), "#FF5C8A", "#8B6CFF", 1.4)
    texto(p, mp.left() + 12.2, mp.top() + 3.4, "Tu canción", 2.5, BLANCO, peso=QFont.Bold, alin=Qt.AlignLeft, ancho=18)
    texto(p, mp.left() + 12.2, mp.top() + 6.0, "Tu artista", 1.9, alfa(BLANCO, 150), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=18)
    pastilla(p, QRectF(mp.left() + 12.2, mp.top() + 8.5, 17.5, 0.9), BLANCO, 50)
    pastilla(p, QRectF(mp.left() + 12.2, mp.top() + 8.5, 17.5 * liso(tg % 9, 0, 9), 0.9), neon, 240)
    p.restore()
    # el pie del monitor
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(neon, 120))
    p.drawRoundedRect(QRectF(-9, 3.6, 18, 1.6), 0.8, 0.8)
    # atajos globales de teclado
    teclas = ["Ctrl", "Alt", "→"]
    ancho_t = [10.5, 9.5, 8.0]
    total = sum(ancho_t) + 3.2 * 2 + 2.6 * 5.5          # las teclas y el texto «atajos»
    x = -total / 2 + 0.0
    y0 = 14.3
    activa = int(tg * 1.6) % 4          # 0..2 se hunde esa tecla, 3 todas a la vez
    for k, t in enumerate(teclas):
        w_ = ancho_t[k]
        hundida = (activa == k) or activa == 3
        yy = y0 + (0.9 if hundida else 0.0)
        rect = QRectF(x, yy - 3.4, w_, 6.8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.translated(0, 1.0 - (0.9 if hundida else 0.0)), 1.6, 1.6)
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        g.setColorAt(0, mezcla("#3C4170", neon, 0.35 if hundida else 0.0))
        g.setColorAt(1, QColor("#1D2040"))
        p.setPen(lapiz(alfa(neon, 220 if hundida else 110), 0.4))
        p.setBrush(g)
        p.drawRoundedRect(rect, 1.6, 1.6)
        texto(p, rect.center().x(), rect.center().y(), t, 3.0, BLANCO, peso=QFont.Bold, ancho=w_)
        x += w_ + 3.2
    texto(p, x - 0.4 + 2.6, y0, "atajos globales", 2.7, alfa(BLANCO, 190), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=26)
    # las tres ayudas
    cur = int(tg * 0.7) % 3
    _ficha(p, 0, 26.5, 76, 6.6, "Ahorro al jugar a pantalla completa", QColor("#4ADE80"), _icono_pantalla,
           activa=1.0 if cur == 0 else 0.0)
    _ficha(p, 0, 34.2, 76, 6.6, "Sonido por tipo de juego", QColor("#F5C542"), _icono_mando,
           activa=1.0 if cur == 1 else 0.0)
    _ficha(p, 0, 41.9, 76, 6.6, "La música baja cuando hablas", QColor("#22D3EE"), _icono_micro,
           activa=1.0 if cur == 2 else 0.0)
    # ondas del micro que "agachan" la música
    if cur == 2:
        for k in range(4):
            h_ = 1.0 + 1.6 * abs(math.sin(tg * 9 + k * 1.3))
            pastilla(p, QRectF(33 + k * 2.4, 41.9 - h_ / 2, 1.2, h_), QColor("#22D3EE"), 230)
    p.restore()


# ================================================================ 3. nivel, misiones, listas, RGB

SITUACIONES = [
    ("Lobby", "#22D3EE"), ("Concentración", "#8B6CFF"), ("Clutch", "#FF5C8A"),
    ("Victoria", "#F5C542"), ("Derrota", "#7C8AA5"),
]


def _llama(p, cx, cy, t, tg, a=255):
    p.save()
    p.translate(cx, cy)
    p.scale(t * (1 + 0.04 * math.sin(tg * 7)), t * (1 + 0.07 * math.sin(tg * 6 + 1)))
    ext = QPainterPath()
    ext.moveTo(0, -3.4)
    ext.cubicTo(1.2, -1.8, 2.8, -1.0, 2.5, 1.0)
    ext.cubicTo(2.2, 2.9, 0.9, 3.4, 0, 3.4)
    ext.cubicTo(-1.0, 3.4, -2.6, 2.8, -2.5, 1.0)
    ext.cubicTo(-2.4, -0.6, -0.6, -1.2, 0, -3.4)
    g = QLinearGradient(0, -3.4, 0, 3.4)
    g.setColorAt(0, QColor("#FFD36B"))
    g.setColorAt(0.5, QColor("#FF8A3D"))
    g.setColorAt(1, QColor("#E53935"))
    p.setPen(Qt.NoPen)
    p.setOpacity(p.opacity() * a / 255)
    p.setBrush(g)
    p.drawPath(ext)
    p.setBrush(QColor("#FFF3B0"))
    p.drawEllipse(QPointF(0, 1.6), 1.0, 1.4)
    p.restore()


def ilus_nivel(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    neon = _neon(tg)
    brillo(p, 0, -6, 62, pal.c2, 36)
    p.translate(0, (1 - r) * 8)
    ciclo = tl % 10
    # nivel: anillo de experiencia
    cx, cy, R = -25, -26, 14.5
    caja = QRectF(cx - R, cy - R, 2 * R, 2 * R)
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(QColor(255, 255, 255, 34), 3.2))
    p.drawEllipse(QPointF(cx, cy), R, R)
    prog = liso(ciclo, 0.4, 5.0)
    g = QLinearGradient(cx - R, cy, cx + R, cy)
    g.setColorAt(0, mezcla(pal.al, "#FFFFFF", 0.1))
    g.setColorAt(1, pal.c2)
    p.setPen(lapiz(g, 3.2))
    p.drawArc(caja, 90 * 16, int(-360 * prog * 16))
    brillo(p, cx, cy, R * 0.95, pal.al, 40)
    texto(p, cx, cy - 4.2, "NIVEL", 2.6, alfa(BLANCO, 190), peso=QFont.DemiBold, ancho=20)
    texto(p, cx, cy + 2.6, str(12 + (1 if ciclo > 5.2 else 0)), 10.5, BLANCO, peso=QFont.Black, ancho=20)
    if ciclo > 5.0 and ciclo < 6.6:                 # sube de nivel: anillo que se abre y destellos
        k = tramo(ciclo, 5.0, 1.4)
        p.setPen(lapiz(alfa(ORO_CLARO, 220 * (1 - k)), 0.8))
        p.drawEllipse(QPointF(cx, cy), R + 2 + 9 * k, R + 2 + 9 * k)
        for i in range(6):
            a = i * math.pi / 3 + 0.3
            destello(p, cx + math.cos(a) * (R + 4 + 8 * k), cy + math.sin(a) * (R + 4 + 8 * k), 2.2 * (1 - k) + 0.4,
                     ORO_CLARO, 240 * (1 - k))
    # racha
    rr = QRectF(-5, -39, 44, 12)
    p.setPen(lapiz(alfa(ORO, 90), 0.35))
    p.setBrush(alfa("#FFB000", 26))
    p.drawRoundedRect(rr, 6, 6)
    _llama(p, rr.left() + 6.0, rr.center().y(), 1.25, tg)
    texto(p, rr.left() + 11.5, rr.center().y() - 2.5, "7 días", 4.6, BLANCO, peso=QFont.Black, alin=Qt.AlignLeft, ancho=28)
    texto(p, rr.left() + 11.5, rr.center().y() + 2.9, "de racha", 2.6, alfa(BLANCO, 170), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=28)
    # misiones
    misiones = [("Escucha 30 minutos", 1.0), ("Crea una lista", 0.6)]
    for k, (nombre, av) in enumerate(misiones):
        rm = QRectF(-5, -24.5 + k * 9.6, 44, 8.2)
        p.setPen(lapiz(QColor(255, 255, 255, 44), 0.3))
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(rm, 2.4, 2.4)
        hecho = k == 0 or ciclo > 6
        p.setPen(lapiz(alfa("#4ADE80" if hecho else "#FFFFFF", 230 if hecho else 110), 0.5))
        p.setBrush(alfa("#4ADE80", 200) if hecho else Qt.NoBrush)
        p.drawEllipse(QPointF(rm.left() + 4.2, rm.center().y()), 2.1, 2.1)
        if hecho:
            p.setPen(lapiz(QColor("#0B2A18"), 0.55))
            ck = QPainterPath()
            ck.moveTo(rm.left() + 3.2, rm.center().y() + 0.1)
            ck.lineTo(rm.left() + 4.0, rm.center().y() + 0.9)
            ck.lineTo(rm.left() + 5.4, rm.center().y() - 0.9)
            p.setBrush(Qt.NoBrush)
            p.drawPath(ck)
        texto(p, rm.left() + 8.0, rm.center().y() - 0.5, nombre, 3.0, alfa(BLANCO, 235), peso=QFont.DemiBold,
              alin=Qt.AlignLeft, ancho=34)
        pastilla(p, QRectF(rm.left() + 8.0, rm.bottom() - 2.0, 33, 0.8), BLANCO, 40)
        pastilla(p, QRectF(rm.left() + 8.0, rm.bottom() - 2.0, 33 * (1.0 if hecho else av * liso(ciclo, 0.5, 4)), 0.8),
                 QColor("#4ADE80"), 230)
    # listas por situación
    texto(p, 0, -1.5, "LISTAS POR SITUACIÓN", 2.7, alfa(BLANCO, 150), peso=QFont.DemiBold, ancho=70)
    activa = int(tg * 0.6) % 5
    filas = ((0, 1, 2), (3, 4))
    for fi, fila in enumerate(filas):
        anchos = [len(SITUACIONES[k][0]) * 1.95 + 9 for k in fila]
        total = sum(anchos) + 2.6 * (len(fila) - 1)
        x = -total / 2
        y = 5.6 + fi * 8.2
        for k, w_ in zip(fila, anchos):
            nombre, col = SITUACIONES[k]
            on = k == activa
            rc = QRectF(x, y - 3.3, w_, 6.6)
            p.setPen(lapiz(alfa(col, 255 if on else 110), 0.4 + 0.3 * on))
            p.setBrush(alfa(col, 70 if on else 24))
            p.drawRoundedRect(rc, 3.3, 3.3)
            p.setPen(Qt.NoPen)
            p.setBrush(alfa(col, 255 if on else 190))
            p.drawEllipse(QPointF(rc.left() + 3.3, y), 1.1 + 0.3 * on, 1.1 + 0.3 * on)
            texto(p, rc.left() + 5.9, y, nombre, 3.0, BLANCO, peso=QFont.Bold if on else QFont.DemiBold,
                  alin=Qt.AlignLeft, ancho=w_ - 6)
            x += w_ + 2.6
    # tema RGB neón
    rect = QRectF(-39, 28.2, 78, 14.5)
    for k in range(3):
        c = _neon(tg, k * 0.07)
        brillo(p, rect.center().x() + (k - 1) * 26, rect.center().y(), 20, c, 34)
    g = QLinearGradient(rect.left(), 0, rect.right(), 0)
    for k in range(7):
        g.setColorAt(k / 6, _neon(tg, k / 7.0 * 0.9))
    p.setPen(lapiz(g, 0.9))
    p.setBrush(alfa("#0E1030", 220))
    p.drawRoundedRect(rect, 3.6, 3.6)
    texto(p, 0, rect.top() + 4.4, "Tema RGB neón", 3.7, BLANCO, peso=QFont.Black, ancho=60)
    ancho_b, n = 3.2, 18
    x0 = -(n * ancho_b) / 2
    for k in range(n):
        alto = 1.0 + 3.4 * abs(math.sin(tg * 3.2 + k * 0.55))
        c = _neon(tg, k / n * 0.9)
        pastilla(p, QRectF(x0 + k * ancho_b + 0.4, rect.bottom() - 2.4 - alto, ancho_b - 0.8, alto), c, 235)
    p.restore()


# ================================================================ 4. «Ahora suena» para OBS

def ilus_ahora_suena(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -12, 62, QColor("#9146FF"), 46)
    p.translate(0, (1 - r) * 8)
    m = QRectF(-44, -46, 88, 49.5)
    p.setPen(lapiz(QColor(255, 255, 255, 80), 0.5))
    p.setBrush(QColor("#0E0B1F"))
    p.drawRoundedRect(m, 2.8, 2.8)
    pant = m.adjusted(1.0, 1.0, -1.0, -1.0)
    ruta = QPainterPath()
    ruta.addRoundedRect(pant, 2.0, 2.0)
    p.save()
    p.setClipPath(ruta)
    g = QLinearGradient(pant.topLeft(), pant.bottomRight())
    g.setColorAt(0, QColor("#2B1A5C"))
    g.setColorAt(1, QColor("#0B1A3A"))
    p.fillRect(pant, g)
    brillo(p, pant.left() + 12, pant.top() + 10, 26, "#FF5C8A", 90)
    brillo(p, pant.right() - 10, pant.bottom() - 6, 28, "#22D3EE", 80)
    # cámara del streamer: silueta
    cam = QRectF(pant.right() - 24, pant.top() + 3.2, 21, 14.5)
    p.setPen(lapiz(alfa("#FFFFFF", 90), 0.3))
    p.setBrush(alfa("#000000", 90))
    p.drawRoundedRect(cam, 1.6, 1.6)
    p.save()
    p.setClipRect(cam)
    I.brillo(p, cam.center().x(), cam.center().y(), 12, "#8B6CFF", 80)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa("#FFFFFF", 215))
    p.drawEllipse(QPointF(cam.center().x(), cam.center().y() - 1.8), 3.2, 3.2)
    p.drawEllipse(QPointF(cam.center().x(), cam.center().y() + 7.8), 6.4, 4.8)
    p.restore()
    # EN VIVO
    pulso = 0.5 + 0.5 * math.sin(tg * 3)
    pr = QRectF(pant.left() + 2.6, pant.top() + 2.6, 15, 4.8)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#E53935"))
    p.drawRoundedRect(pr, 1.6, 1.6)
    p.setBrush(alfa("#FFFFFF", 160 + 95 * pulso))
    p.drawEllipse(QPointF(pr.left() + 2.4, pr.center().y()), 0.9, 0.9)
    texto(p, pr.left() + 4.4, pr.center().y(), "EN VIVO", 2.5, BLANCO, peso=QFont.Black, alin=Qt.AlignLeft, ancho=11)
    # tarjeta «Ahora suena» que entra deslizándose
    ciclo = tl % 8
    ent = eo(tramo(ciclo, 0.2, 0.9))
    sale = 1 - eo(tramo(ciclo, 7.2, 0.7))
    k = min(ent, sale)
    tarj = QRectF(pant.left() + 3.0 - (1 - k) * 46, pant.bottom() - 17.5, 47, 14.5)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawRoundedRect(tarj.translated(0, 0.9), 3.2, 3.2)
    gg = QLinearGradient(tarj.topLeft(), tarj.topRight())
    gg.setColorAt(0, alfa("#1B1340", 245))
    gg.setColorAt(1, alfa("#2A1B5C", 245))
    p.setPen(lapiz(alfa("#B79CFF", 180), 0.4))
    p.setBrush(gg)
    p.drawRoundedRect(tarj, 3.2, 3.2)
    _caratula(p, QRectF(tarj.left() + 1.9, tarj.top() + 1.9, 10.7, 10.7), "#FF8A3D", "#8B6CFF", 1.7)
    texto(p, tarj.left() + 14.2, tarj.top() + 3.2, "AHORA SUENA", 2.1, alfa("#B79CFF", 255), peso=QFont.Black,
          alin=Qt.AlignLeft, ancho=30)
    texto(p, tarj.left() + 14.2, tarj.top() + 7.1, "Tu canción", 3.6, BLANCO, peso=QFont.Black, alin=Qt.AlignLeft, ancho=30)
    texto(p, tarj.left() + 14.2, tarj.top() + 10.7, "Tu artista", 2.5, alfa(BLANCO, 170), peso=QFont.DemiBold,
          alin=Qt.AlignLeft, ancho=30)
    for j in range(4):
        alto = 1.0 + 3.2 * abs(math.sin(tg * 5 + j * 1.4))
        pastilla(p, QRectF(tarj.right() - 8.6 + j * 1.9, tarj.center().y() + 2.0 - alto, 1.2, alto),
                 QColor("#B79CFF"), 235)
    p.restore()
    p.setPen(lapiz(alfa("#FFFFFF", 70), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(pant, 2.0, 2.0)
    # nota de derechos
    nt = QRectF(-44, 8.0, 88, 36)
    p.setPen(lapiz(alfa("#F5C542", 110), 0.4))
    p.setBrush(alfa("#F5C542", 20))
    p.drawRoundedRect(nt, 4.0, 4.0)
    # triángulo de aviso
    tx, ty = nt.left() + 8.0, nt.top() + 8.6
    tri = QPainterPath()
    tri.moveTo(tx, ty - 4.4)
    tri.lineTo(tx + 4.8, ty + 3.6)
    tri.lineTo(tx - 4.8, ty + 3.6)
    tri.closeSubpath()
    p.setPen(lapiz(ORO, 0.7))
    p.setBrush(alfa("#F5C542", 60))
    p.drawPath(tri)
    texto(p, tx, ty + 1.2, "!", 4.2, ORO_CLARO, peso=QFont.Black, ancho=6)
    texto(p, nt.left() + 15.0, nt.top() + 5.6, "Una nota sobre los directos", 3.6, ORO_CLARO, peso=QFont.Black,
          alin=Qt.AlignLeft, ancho=70)
    texto(p, nt.left() + 15.0, nt.top() + 11.6, "La música de YouTube no se puede usar", 3.1, alfa(BLANCO, 230),
          peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=72)
    texto(p, nt.left() + 15.0, nt.top() + 15.9, "en directos por derechos de autor.", 3.1, alfa(BLANCO, 230),
          peso=QFont.DemiBold, alin=Qt.AlignLeft, ancho=72)
    texto(p, nt.center().x(), nt.top() + 24.0, "Usa música tuya o con licencia", 2.9, alfa(BLANCO, 150),
          peso=QFont.DemiBold, ancho=80)
    # indicador: «Ahora suena» pegado al directo (fuente de navegador)
    pastilla(p, QRectF(-30, nt.bottom() - 8.6, 60, 5.6), QColor("#9146FF"), 60)
    p.setPen(lapiz(alfa("#B79CFF", 200), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(-30, nt.bottom() - 8.6, 60, 5.6), 2.8, 2.8)
    texto(p, 0, nt.bottom() - 5.8, "Fuente de navegador en OBS", 2.9, BLANCO, peso=QFont.DemiBold, ancho=58)
    p.restore()


# ================================================================ 5. el personaje cobra vida

def ilus_personaje(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -6, 62, pal.c3, 40)
    p.translate(0, (1 - r) * 8)
    # escritorio
    m = QRectF(-44, -44, 88, 66)
    p.setPen(lapiz(QColor(255, 255, 255, 90), 0.5))
    g = QLinearGradient(m.topLeft(), m.bottomRight())
    g.setColorAt(0, QColor("#1B1646"))
    g.setColorAt(1, QColor("#0B1030"))
    p.setBrush(g)
    p.drawRoundedRect(m, 3, 3)
    pant = m.adjusted(1, 1, -1, -1)
    ruta = QPainterPath()
    ruta.addRoundedRect(pant, 2.2, 2.2)
    p.save()
    p.setClipPath(ruta)
    brillo(p, -20, -20, 30, "#8B6CFF", 60)
    brillo(p, 25, 10, 30, "#FF5C8A", 44)
    # ventana de fondo (la app)
    vent = QRectF(pant.left() + 5, pant.top() + 6, 48, 34)
    p.setPen(lapiz(QColor(255, 255, 255, 40), 0.3))
    p.setBrush(QColor(255, 255, 255, 14))
    p.drawRoundedRect(vent, 2, 2)
    for k in range(4):
        pastilla(p, QRectF(vent.left() + 3, vent.top() + 5 + k * 6.5, 28 - k * 4, 2.2), QColor(255, 255, 255), 50)
    # esquina de reposo (punteada)
    casa = QPointF(pant.right() - 17, pant.bottom() - 15)
    p.setBrush(Qt.NoBrush)
    pen = lapiz(alfa("#FFFFFF", 130), 0.4, Qt.FlatCap)
    pen.setDashPattern([2.5, 2.5])
    p.setPen(pen)
    p.drawEllipse(casa, 11.0, 11.0)
    # ciclo de 10 s: reposo, agarrar, arrastrar, bailar, doble clic y volver
    t = tl % 10.0
    destino = QPointF(-14, -4)
    if t < 2.2:                                   # baila en su esquina
        pos, pos_ruta = casa, 0.0
        cur, agarrado = None, False
    elif t < 3.4:                                 # llega el ratón
        k = liso(t, 2.2, 3.4)
        pos = casa
        cur = QPointF(casa.x() + 14 * (1 - k) + 1.5, casa.y() + 12 * (1 - k) + 2)
        agarrado = False
    elif t < 5.4:                                 # lo arrastra
        k = liso(t, 3.4, 5.4)
        pos = QPointF(casa.x() + (destino.x() - casa.x()) * k,
                      casa.y() + (destino.y() - casa.y()) * k - 12 * math.sin(k * math.pi))
        cur = QPointF(pos.x() + 1.5, pos.y() + 2)
        agarrado = True
    elif t < 7.4:                                 # baila donde lo dejó
        pos = destino
        cur = QPointF(destino.x() + 14 * liso(t, 5.4, 6.4), destino.y() + 12 * liso(t, 5.4, 6.4) + 2) \
            if t < 6.4 else None
        agarrado = False
    else:                                         # doble clic y vuelve
        k = liso(t, 8.0, 9.4)
        pos = QPointF(destino.x() + (casa.x() - destino.x()) * k,
                      destino.y() + (casa.y() - destino.y()) * k - 8 * math.sin(k * math.pi))
        cur = QPointF(destino.x() + 1.5, destino.y() + 2) if t < 8.0 else None
        agarrado = False
    # rastro mientras lo arrastra
    if 3.4 <= t < 5.4:
        for k in range(7):
            f = liso(t - 0.06 * k, 3.4, 5.4)
            q = QPointF(casa.x() + (destino.x() - casa.x()) * f,
                        casa.y() + (destino.y() - casa.y()) * f - 12 * math.sin(f * math.pi))
            p.setPen(Qt.NoPen)
            p.setBrush(alfa(pal.al, 110 - 14 * k))
            p.drawEllipse(q, 3.2 - 0.3 * k, 3.2 - 0.3 * k)
    # onda del doble clic
    if 7.4 <= t < 8.4:
        k = tramo(t, 7.4, 1.0)
        for j in range(2):
            kk = clamp(k - 0.18 * j)
            p.setBrush(Qt.NoBrush)
            p.setPen(lapiz(alfa("#FFFFFF", 200 * (1 - kk)), 0.5))
            p.drawEllipse(QPointF(destino.x(), destino.y()), 6 + 10 * kk, 6 + 10 * kk)
        texto(p, destino.x(), destino.y() - 20, "doble clic", 2.8, alfa("#FFFFFF", 230 * (1 - abs(2 * k - 1) * 0.6)),
              peso=QFont.Bold, ancho=30)
    # sombra
    alto_suelo = pos.y() + 11.5
    esc = 1.0
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 70))
    p.drawEllipse(QPointF(pos.x(), alto_suelo), 9 * esc, 1.8)
    # notas que salen del personaje al ritmo
    baila = 0.25 if agarrado else 1.0
    for j in range(3):
        f = (tg * 0.5 + j / 3.0) % 1.0
        _nota_flotante(p, pos.x() + (j - 1) * 9 + 3 * math.sin(tg * 2 + j), pos.y() - 14 - 20 * f,
                       4.2, [pal.al, pal.c2, QColor("#22D3EE")][j], 230 * math.sin(f * math.pi) * (0.3 if agarrado else 1),
                       10 * math.sin(tg * 2 + j), j % 3)
    _bicho(p, pos.x(), pos.y(), 0.92, tg, baile=baila, brazos=1.0 if not agarrado else 0.2, fase=0.0,
           boca=not agarrado)
    if cur is not None:
        I.cursor(p, cur.x(), cur.y(), 0.95)
    p.restore()
    p.setPen(lapiz(alfa("#FFFFFF", 70), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(pant, 2.2, 2.2)
    # pie: lo que se puede hacer
    _ficha(p, -23.5, 34.5, 42, 7.2, "Arrástralo a donde quieras", QColor("#22D3EE"), _icono_mano, tam_t=2.3)
    _ficha(p, 23.5, 34.5, 42, 7.2, "Doble clic: a su esquina", QColor("#F5C542"), _icono_casa, tam_t=2.3)
    texto(p, 0, 43.2, "Baila suave al ritmo de tu música", 3.1, alfa("#FFFFFF", 175), peso=QFont.DemiBold, ancho=84)
    p.restore()


def _icono_mano(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    for dx in (-1.35, -0.45, 0.45, 1.35):
        p.drawRoundedRect(QRectF(dx - 0.4, -2.2 + abs(dx) * 0.25, 0.8, 2.4), 0.4, 0.4)
    p.drawRoundedRect(QRectF(-1.8, -0.5, 3.6, 2.9), 1.2, 1.2)
    p.restore()


def _icono_casa(p, x, y, t, color, a=255):
    p.save()
    p.translate(x, y)
    p.scale(t, t)
    ruta = QPainterPath()
    ruta.moveTo(0, -2.2)
    ruta.lineTo(2.3, -0.1)
    ruta.lineTo(1.6, -0.1)
    ruta.lineTo(1.6, 2.0)
    ruta.lineTo(-1.6, 2.0)
    ruta.lineTo(-1.6, -0.1)
    ruta.lineTo(-2.3, -0.1)
    ruta.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(alfa(color, a))
    p.drawPath(ruta)
    p.restore()


# ================================================================ 6. regala una prueba

def _regalo(p, cx, cy, s, tg, abre, color="#FF5C8A"):
    """Caja de regalo; `abre` (0..1) levanta la tapa."""
    p.save()
    p.translate(cx, cy)
    p.scale(s, s)
    ca, cb = QColor(color), mezcla(color, "#000000", 0.35)
    # caja
    cuerpo = QRectF(-11, -2, 22, 14)
    g = QLinearGradient(cuerpo.topLeft(), cuerpo.bottomRight())
    g.setColorAt(0, mezcla(ca, "#FFFFFF", 0.1))
    g.setColorAt(1, cb)
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(cuerpo, 1.6, 1.6)
    p.setBrush(alfa(ORO, 245))
    p.drawRect(QRectF(-1.8, -2, 3.6, 14))
    # tapa
    p.save()
    p.translate(0, -3.8 - 7 * abre)
    p.rotate(-14 * abre)
    tapa = QRectF(-12.4, -3.2, 24.8, 5.6)
    g2 = QLinearGradient(tapa.topLeft(), tapa.bottomRight())
    g2.setColorAt(0, mezcla(ca, "#FFFFFF", 0.22))
    g2.setColorAt(1, mezcla(ca, "#000000", 0.2))
    p.setBrush(g2)
    p.drawRoundedRect(tapa, 1.4, 1.4)
    p.setBrush(alfa(ORO, 245))
    p.drawRect(QRectF(-1.8, -3.2, 3.6, 5.6))
    # lazo
    for sx in (-1, 1):
        lazo = QPainterPath()
        lazo.moveTo(0, -3.0)
        lazo.cubicTo(sx * 3, -9.4, sx * 8.4, -7.6, sx * 5.4, -3.0)
        lazo.closeSubpath()
        p.setBrush(alfa(ORO_CLARO, 250))
        p.setPen(lapiz(alfa(ORO_OSCURO, 255), 0.4))
        p.drawPath(lazo)
    p.setPen(Qt.NoPen)
    p.setBrush(ORO)
    p.drawEllipse(QPointF(0, -3.0), 1.6, 1.4)
    p.restore()
    p.restore()


def _confeti(p, cx, cy, tg, t0, a, radio=40, n=26):
    """Confeti que sale hacia arriba desde (cx, cy) a partir del instante t0 (segundos)."""
    k = tg - t0
    if k < 0 or k > 3.2:
        return
    cols = ["#FF5C8A", "#F5C542", "#22D3EE", "#4ADE80", "#8B6CFF", "#FFFFFF"]
    for i in range(n):
        ang = math.radians(-90 + (azar(i, 1) - 0.5) * 120)
        vel = 14 + 26 * azar(i, 2)
        x = cx + math.cos(ang) * vel * k
        y = cy + math.sin(ang) * vel * k + 9 * k * k
        vida = clamp(1 - k / 3.2)
        p.save()
        p.translate(x, y)
        p.rotate(360 * azar(i, 3) + k * 240 * (azar(i, 4) - 0.5))
        p.setPen(Qt.NoPen)
        p.setBrush(alfa(cols[i % 6], 255 * vida * a))
        p.drawRect(QRectF(-0.9, -0.5, 1.8, 1.0))
        p.restore()


def ilus_regalo(p, X):
    pal, tl, tg = X.pal, X.tl, X.tg
    r = eo(tramo(tl, 0.05, 0.9))
    p.save()
    p.setOpacity(X.alfa * r)
    brillo(p, 0, -8, 62, ORO, 48)
    p.translate(0, (1 - r) * 8)
    ciclo = tl % 8.0
    abre = liso(ciclo, 0.8, 1.5) * (1 - liso(ciclo, 6.6, 7.4))
    # la caja flota y se abre
    cy = -8 + 1.0 * math.sin(tg * 1.4)
    _regalo(p, 0, cy, 1.1, tg, abre)
    brillo(p, 0, cy - 4, 12 + 14 * abre, ORO_CLARO, 140 * abre)
    _confeti(p, 0, cy - 6, ciclo, 1.0, X.alfa * r)
    # el boleto sale de la caja
    sal = eo(tramo(ciclo, 1.1, 1.0)) * (1 - liso(ciclo, 6.6, 7.4))
    w, h = 60.0, 25.0
    p.save()
    p.translate(0, cy + 4 - 27 * sal)
    p.setOpacity(p.opacity() * clamp(sal * 1.5))
    p.rotate(-3 + 1.2 * math.sin(tg * 1.1))
    caja = QRectF(-w / 2, -h / 2 - 8, w, h)
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(caja, 3.8, 3.8)
    mu = QPainterPath()
    mu.addEllipse(QPointF(caja.left(), caja.center().y()), 3.0, 3.0)
    mu.addEllipse(QPointF(caja.right(), caja.center().y()), 3.0, 3.0)
    boleto = cuerpo.subtracted(mu)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 55))
    p.save()
    p.translate(0, 1.3)
    p.drawPath(boleto)
    p.restore()
    g = QLinearGradient(caja.topLeft(), caja.bottomRight())
    g.setColorAt(0, ORO_CLARO)
    g.setColorAt(0.5, ORO)
    g.setColorAt(1, ORO_OSCURO)
    p.setBrush(g)
    p.drawPath(boleto)
    cd = QPointF(caja.left() + 12.5, caja.center().y())
    p.setBrush(Qt.NoBrush)
    p.setPen(lapiz(alfa(TINTA, 50), 1.4))
    p.drawEllipse(cd, 7.4, 7.4)
    p.setPen(lapiz(TINTA, 1.4))
    p.drawArc(QRectF(cd.x() - 7.4, cd.y() - 7.4, 14.8, 14.8), 90 * 16, int(-360 * liso(tg % 6, 0, 5) * 16))
    texto(p, cd.x(), cd.y() - 1.2, "7", 7.6, TINTA, peso=QFont.Black, ancho=14)
    texto(p, cd.x(), cd.y() + 4.4, "DÍAS", 2.0, TINTA, ancho=14)
    x0 = caja.left() + 25.0
    p.setPen(lapiz(alfa(TINTA, 120), 0.3, Qt.FlatCap))
    y = caja.top() + 3.4
    while y < caja.bottom() - 2.6:
        p.drawLine(QPointF(x0, y), QPointF(x0, y + 1.5))
        y += 3.0
    cx2 = caja.left() + 43.0
    texto(p, cx2, caja.center().y() - 6.2, "REGALO DE PRUEBA", 2.4, TINTA, peso=QFont.Black, ancho=32)
    texto(p, cx2, caja.center().y() + 0.2, "R7K2-9XMD", 5.2, TINTA, peso=QFont.Black, ancho=34)
    texto(p, cx2, caja.center().y() + 6.2, "beneficios de donador", 2.2, alfa(TINTA, 200), peso=QFont.DemiBold, ancho=34)
    p.restore()
    # amigos que lo reciben
    cols = [("#FF5C8A", "#8B6CFF"), ("#22D3EE", "#4ADE80"), ("#F5C542", "#FF8A3D")]
    for k in range(3):
        x = (k - 1) * 27
        ap = eo(tramo(ciclo, 2.4 + 0.45 * k, 0.8)) * (1 - liso(ciclo, 7.2, 7.8))
        p.save()
        p.setOpacity(p.opacity() * clamp(ap * 1.4))
        yy = 19 + (1 - ap) * 8 + 1.0 * math.sin(tg * 1.8 + k)
        from .ilustraciones_v4 import _avatar
        _avatar(p, x, yy, 6.4, QColor(cols[k][0]), QColor(cols[k][1]))
        # insignia de donador
        p.setPen(lapiz(QColor("#14101F"), 0.4))
        p.setBrush(ORO)
        p.drawEllipse(QPointF(x + 5.0, yy - 4.6), 2.5, 2.5)
        I.estrella(p, x + 5.0, yy - 4.6, 1.6, 0.7, QColor("#3A2800"))
        texto(p, x, yy + 10.2, ("Ana", "Leo", "Mía")[k], 2.8, alfa(BLANCO, 220), peso=QFont.DemiBold, ancho=22)
        p.restore()
    pastilla(p, QRectF(-35, 37.2, 70, 8.4), QColor("#FFFFFF"), 26)
    p.setPen(lapiz(QColor(255, 255, 255, 80), 0.3))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(-35, 37.2, 70, 8.4), 4.2, 4.2)
    texto(p, 0, 41.4, "Para que tus amigos prueben 7 días", 3.5, BLANCO, ancho=68)
    p.restore()


# ================================================================ 7. cierre

def ilus_final_v5(p, X):
    pal, tl, tg, hw, hh = X.pal, X.tl, X.tg, X.hw, X.hh
    r = eo(tramo(tl, 0.0, 1.2))
    p.save()
    p.setClipRect(QRectF(-hw, -hh, hw * 2, hh * 2))
    cols = [pal.al, pal.c2, pal.c3, pal.ac, pal.c4]
    alto = hh * 2 + 30
    for i in range(18):
        ax, ay, av, at = azar(i, 31), azar(i, 32), azar(i, 33), azar(i, 34)
        vel = 6 + 8 * av
        y = hh + 12 - ((tg * vel + ay * alto) % alto)
        x = -hw + 2 * hw * ax + 5 * math.sin(tg * (0.6 + av) + i)
        borde = clamp(min((hh - y) / 12.0, (y + hh) / 16.0))
        tam = 4.5 + 5.5 * at
        _nota_flotante(p, x, y, tam, cols[i % 5], 150 * borde * r * (0.45 + 0.55 * at),
                       12 * math.sin(tg * 0.9 + i * 1.7), i % 3)
    # corazones sutiles
    for i in range(8):
        f = ((tg * 0.12 + azar(i, 41)) % 1.0)
        x = -hw + 2 * hw * azar(i, 42) + 4 * math.sin(tg + i)
        y = hh - f * (hh * 2)
        t = 1.3 + 1.2 * azar(i, 43)
        c = QPainterPath()
        c.moveTo(x, y + t * 0.9)
        c.cubicTo(x - t * 2.2, y - t * 0.6, x - t * 0.8, y - t * 1.9, x, y - t * 0.6)
        c.cubicTo(x + t * 0.8, y - t * 1.9, x + t * 2.2, y - t * 0.6, x, y + t * 0.9)
        p.setPen(Qt.NoPen)
        p.setBrush(alfa("#FF5C8A", 120 * math.sin(f * math.pi) * r))
        p.drawPath(c)
    for i in range(12):
        a = 0.5 + 0.5 * math.sin(tg * 2 + i * 1.9)
        destello(p, -hw + 2 * hw * azar(i, 20), -hh + 2 * hh * azar(i, 21) * 0.9, 1.4 + 2.2 * azar(i, 22) * a,
                 "#FFFFFF", 200 * a * r)
    # el personaje saluda desde la esquina de abajo
    ap = eo(tramo(tl, 0.8, 1.2))
    p.save()
    p.setOpacity(X.alfa * ap)
    _bicho(p, hw * 0.55, hh - 15 + (1 - ap) * 20, 1.15, tg, baile=0.8, fase=0.9)
    _mando(p, -hw * 0.55, hh - 14 + (1 - ap) * 20, 24, tg, _neon(tg, 0.3))
    p.restore()
    p.restore()


I.ILUSTRACIONES.update({
    "v5_portada": ilus_portada_v5, "gamer": ilus_gamer, "nivel": ilus_nivel, "ahora_suena": ilus_ahora_suena,
    "personaje": ilus_personaje, "regalo": ilus_regalo, "v5_final": ilus_final_v5,
})
