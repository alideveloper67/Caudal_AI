# -*- coding: utf-8 -*-
"""Escenario My Melody: valle de flores en primavera con molino de viento, casita de cuento y cerezos en flor,
con luz de mañana en tonos pastel rosados (ilustración tipo fondo de Ghibli).

Solo la estética: no se dibuja ninguna cara ni figura de personaje; todo son paisaje, flores, té y cestas.
Lo fijo (cielo, nubes, montañas, colinas con perspectiva atmosférica, cerezos, molino, casita, campo de flores,
grano y vineta) se pinta una vez en `pintar_estatico`. Lo que se mueve (pétalos, mariposas, aspas del molino,
una franja de hierba con flores en el borde, resplandor y ondas de la música) usa sprites ya pre-renderizados.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient

from .base import EscenarioBase, con_alfa, mezclar

ROSA = "#FF9EC8"
BRUMA = QColor("#FFE3EF")           # color del aire lejano: la perspectiva atmosférica mezcla cada capa con él
CIELO_ARRIBA, CIELO_MEDIO, CIELO_HORIZONTE = "#FFD6E8", "#FFE8F0", "#FFF6F2"
# colinas de lejos a cerca: (base relativa, amplitud relativa, fase, frecuencia, color, mezcla con la bruma)
COLINAS = (
    (0.56, 0.10, 0.4, 0.9, "#D6EFD8", 0.65),
    (0.62, 0.11, 2.1, 1.2, "#BCE3C2", 0.40),
    (0.68, 0.11, 3.7, 1.6, "#A3D7AE", 0.15),
    (0.75, 0.09, 1.1, 2.1, "#8CCB9C", 0.00),
)
# cordilleras lejanas: (altura media relativa, amplitud relativa, color)
CORDILLERAS = ((0.46, 0.085, "#E6D2F0"), (0.50, 0.05, "#EFDDF4"))
N_PETALOS = 45
N_MARIPOSAS = 5
N_HIERBA = 150
N_FLORES_CAMPO = 3000
N_BRIZNAS = 1100
N_GRANO = 5000
N_FLORES_HIERBA = 40
ZONA_HIERBA = 0.90               # desde aquí (relativo al alto) la franja del borde se mece en lo animado
NIVEL_MAX = 7
PARES_ALAS = (("#FFFFFF", "#FFC2DC"), ("#FFD6E8", "#FFB3D6"), ("#E6F7EE", "#FFC2DC"))
COLORES_PETALO = ("#FFB3D6", "#FFD6E8", "#FFFFFF", "#FFC2DC")
COLORES_FLOR = ("#FFB0CF", "#FFFFFF", "#D9C2F0")      # rosa, blanco, lila
COLOR_TALLO = "#7DBF94"


def _petalo_unitario():
    """Pétalo redondo de 1 unidad de alto, con la base en (0, 0) y la punta en (0, -1)."""
    camino = QPainterPath(QPointF(0, 0))
    camino.cubicTo(QPointF(0.55, -0.25), QPointF(0.45, -0.85), QPointF(0, -1))
    camino.cubicTo(QPointF(-0.45, -0.85), QPointF(-0.55, -0.25), QPointF(0, 0))
    return camino


def _altura(x, w, h, base, amp, fase, frec):
    """Altura (px) de la cima de una colina en x: senos superpuestos para un borde orgánico."""
    u = x / w * math.pi * frec
    v = 0.55 + 0.30 * math.sin(u + fase) + 0.15 * math.sin(u * 2.3 + fase * 1.7)
    return h * base - amp * h * v


def _camino_colina(w, h, base, amp, fase, frec, n=40):
    """Colina suave: curvas entre puntos, cerrada hasta el fondo."""
    xs = [i * w / (n - 1) for i in range(n)]
    pts = [QPointF(x, _altura(x, w, h, base, amp, fase, frec)) for x in xs]
    camino = QPainterPath(QPointF(0, h))
    camino.lineTo(pts[0])
    for a, b in zip(pts, pts[1:]):
        medio = (a.x() + b.x()) / 2
        camino.cubicTo(QPointF(medio, a.y()), QPointF(medio, b.y()), b)
    camino.lineTo(QPointF(w, h))
    camino.closeSubpath()
    return camino


def _cresta(r, w, h, y_medio, amp):
    """Cordillera por desplazamiento del punto medio: 8 iteraciones, amp *= 0.55 en cada una."""
    ys = [h * y_medio + r.uniform(-amp, amp), h * y_medio + r.uniform(-amp, amp)]
    a = amp
    for _ in range(8):
        nuevos = [ys[0]]
        for y0, y1 in zip(ys, ys[1:]):
            nuevos.append((y0 + y1) / 2 + r.uniform(-a, a))
            nuevos.append(y1)
        ys = nuevos
        a *= 0.55
    n = len(ys)
    return [QPointF(w * i / (n - 1), y) for i, y in enumerate(ys)]


# ---------------------------------------------------------------- sprites pre-renderizados

def _sprite_flor(tipo, color, lado=64):
    """0 = tulipán (copa de 3 pétalos), 1 = margarita (7 pétalos), 2 = flor de 5 pétalos redondos."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(lado / 2, lado / 2)
        s = lado * 0.46
        c = QColor(color)
        sombra = mezclar(c, QColor("#E58FB3"), 0.22)
        p.setPen(QPen(con_alfa(QColor(ROSA), 120), max(1.0, lado * 0.02)))
        if tipo == 0:
            for ang, tono in ((-30, sombra), (30, sombra), (0, c)):
                p.save()
                p.rotate(ang)
                p.setBrush(tono)
                copa = QPainterPath(QPointF(0, 0))
                copa.cubicTo(QPointF(0.62 * s, -0.25 * s), QPointF(0.55 * s, -0.95 * s), QPointF(0, -s))
                copa.cubicTo(QPointF(-0.55 * s, -0.95 * s), QPointF(-0.62 * s, -0.25 * s), QPointF(0, 0))
                p.drawPath(copa)
                p.restore()
        elif tipo == 1:
            p.setBrush(c)
            for k in range(7):
                p.save()
                p.rotate(k * 360 / 7)
                p.drawEllipse(QPointF(0, -s * 0.55), s * 0.24, s * 0.5)
                p.restore()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFD45C"))
            p.drawEllipse(QPointF(0, 0), s * 0.22, s * 0.22)
        else:
            p.setBrush(c)
            for k in range(5):
                p.save()
                p.rotate(k * 72)
                p.drawEllipse(QPointF(0, -s * 0.5), s * 0.42, s * 0.42)
                p.restore()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFD45C"))
            p.drawEllipse(QPointF(0, 0), s * 0.2, s * 0.2)
    finally:
        p.end()
    return pm


def _sprite_petalo(color, lado=40):
    """Pétalo que vuela: forma de pétalo con una luz blanca en un lado."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(lado * 0.5, lado * 0.95)
        p.scale(lado * 0.9, lado * 0.9)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(_petalo_unitario())
        p.save()
        p.translate(-0.1, -0.15)
        p.scale(0.4, 0.55)
        p.setBrush(con_alfa(QColor("#FFFFFF"), 130))
        p.drawPath(_petalo_unitario())
        p.restore()
    finally:
        p.end()
    return pm


def _sprite_mariposa(sup, inf, lado=40):
    """Alas de una pareja de color; el cuerpo queda en (0, 20) para escalarlas en horizontal al aletear."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(inf))
        p.drawEllipse(QPointF(14, 28), 12, 8)
        p.setBrush(QColor(sup))
        p.drawEllipse(QPointF(18, 11), 16, 11)
        p.setBrush(con_alfa(QColor(ROSA), 200))
        p.drawEllipse(QPointF(20, 10), 3.5, 3.5)
        p.setBrush(con_alfa(QColor(ROSA), 170))
        p.drawEllipse(QPointF(12, 28), 2.5, 2.5)
    finally:
        p.end()
    return pm


def _sprite_resplandor(color, ancho, alto):
    pm = QPixmap(ancho, alto)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        g = QRadialGradient(QPointF(ancho / 2, alto / 2), min(ancho, alto) / 2)
        g.setColorAt(0, con_alfa(color, 170))
        g.setColorAt(1, con_alfa(color, 0))
        p.fillRect(QRectF(0, 0, ancho, alto), g)
    finally:
        p.end()
    return pm


def _sprite_aspas(radio):
    """Cuatro aspas de tela con rejilla y cubo central, centradas en el sprite (se giran desde su centro)."""
    lado = int(round(2 * radio))
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    try:
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(lado / 2, lado / 2)
        largo = radio * 0.98
        ancho = radio * 0.26
        for k in range(4):
            p.save()
            p.rotate(k * 90)
            tela = QRectF(-ancho / 2, -largo, ancho, largo - radio * 0.12)
            p.setPen(QPen(QColor("#FF9EC8"), max(1.0, radio * 0.03)))
            p.setBrush(QColor("#FFF8FB"))
            p.drawRect(tela)
            p.setPen(QPen(con_alfa(QColor("#F2B6D0"), 140), 1.0))
            for i in range(1, 4):
                yy = tela.top() + tela.height() * i / 4
                p.drawLine(QPointF(tela.left(), yy), QPointF(tela.right(), yy))
            for j in range(1, 3):
                xx = tela.left() + tela.width() * j / 3
                p.drawLine(QPointF(xx, tela.top()), QPointF(xx, tela.bottom()))
            p.restore()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFB0CF"))
        p.drawEllipse(QPointF(0, 0), radio * 0.12, radio * 0.12)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QPointF(0, 0), radio * 0.05, radio * 0.05)
    finally:
        p.end()
    return pm


# ---------------------------------------------------------------- piezas del paisaje

def _nube(p, r, x, y, tam):
    """Nube esponjosa de 20–40 círculos: pasada de sombra rosada abajo y pasada blanca arriba."""
    n = r.randint(20, 40)
    radio = tam * 0.075
    circulos = []
    for _ in range(n):
        u = r.uniform(-1, 1)
        cx = x + u * radio * 2.8
        cy = y - r.uniform(0, 1) * radio * 0.9 * (1 - abs(u) * 0.7)
        rad = radio * r.uniform(0.35, 0.8) * (1 - 0.35 * abs(u))
        circulos.append((cx, cy, rad))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#F5C0D6"))
    for cx, cy, rad in circulos:
        p.drawEllipse(QPointF(cx, cy + rad * 0.35), rad, rad)
    p.setBrush(QColor("#FFFFFF"))
    for cx, cy, rad in circulos:
        p.drawEllipse(QPointF(cx, cy), rad * 0.92, rad * 0.92)


def _rama(r, ramas, puntas, x, y, ang, largo, grosor, nivel, nivmax):
    """Rama recursiva: 2 o 3 hijos, ángulo ±18–38°, largo x0.72–0.82, grosor x0.68."""
    rad = math.radians(ang)
    x2 = x + math.sin(rad) * largo
    y2 = y - math.cos(rad) * largo
    ramas.append((x, y, x2, y2, grosor))
    if nivel >= nivmax or (nivel >= 3 and r.random() < 0.3):
        puntas.append((x2, y2))
        return
    if r.random() < 0.55:
        abanico = (-r.uniform(18, 38), r.uniform(18, 38))
    else:
        abanico = (-r.uniform(20, 38), r.uniform(-6, 6), r.uniform(20, 38))
    for giro in abanico:
        # ángulo entre 35° y 145° medido desde la horizontal: ninguna rama baja en espiral
        ang_hijo = max(-55.0, min(55.0, ang + giro))
        _rama(r, ramas, puntas, x2, y2, ang_hijo, largo * r.uniform(0.72, 0.82), grosor * 0.68,
              nivel + 1, nivmax)


def _dibujar_rama(p, x1, y1, x2, y2, g):
    """Rama como polígono ahusado con degradado de corteza."""
    dx, dy = x2 - x1, y2 - y1
    largo = math.hypot(dx, dy)
    if largo < 0.5:
        return
    nx, ny = -dy / largo, dx / largo
    gt = g * 0.68
    poligono = QPolygonF([
        QPointF(x1 + nx * g / 2, y1 + ny * g / 2),
        QPointF(x2 + nx * gt / 2, y2 + ny * gt / 2),
        QPointF(x2 - nx * gt / 2, y2 - ny * gt / 2),
        QPointF(x1 - nx * g / 2, y1 - ny * g / 2),
    ])
    grad = QLinearGradient(QPointF(x1, y1), QPointF(x2, y2))
    grad.setColorAt(0, QColor("#6B4A4A"))
    grad.setColorAt(1, QColor("#8B6060"))
    p.setBrush(grad)
    p.drawPolygon(poligono)


def _racimo(p, r, w, x, y, radio):
    """Racimo de 18–28 flores en orden: sombra desplazada abajo, tonos medios, luces arriba-izquierda.
    Los radios varían entre 0.003 y 0.012 del ancho para que no parezcan palomitas iguales."""
    n = r.randint(18, 28)
    pts = []
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi)
        d = radio * math.sqrt(r.random())
        pts.append((x + math.cos(a) * d, y + math.sin(a) * d * 0.8, w * r.uniform(0.003, 0.012)))
    p.setBrush(QColor("#E58FB3"))
    for px, py, rc in pts:
        p.drawEllipse(QPointF(px, py + rc * 0.45), rc, rc)
    for k, (px, py, rc) in enumerate(pts):
        p.setBrush(QColor("#FFC2DA" if k % 2 else "#FFB0CF"))
        p.drawEllipse(QPointF(px, py), rc * 0.9, rc * 0.9)
    p.setBrush(QColor("#FFF0F6"))
    for px, py, rc in pts:
        p.drawEllipse(QPointF(px - rc * 0.3, py - rc * 0.3), rc * 0.5, rc * 0.5)


def _flor_suelta(p, r, w, x, y):
    """Flor suelta de 5 pétalos redondos, para romper el racimo del borde exterior."""
    rf = w * r.uniform(0.006, 0.01)
    p.setBrush(QColor("#FFD6E8"))
    for k in range(5):
        p.save()
        p.translate(x, y)
        p.rotate(k * 72 + r.uniform(-8, 8))
        p.drawEllipse(QPointF(0, -rf * 0.6), rf * 0.5, rf * 0.5)
        p.restore()
    p.setBrush(QColor("#FFD45C"))
    p.drawEllipse(QPointF(x, y), rf * 0.3, rf * 0.3)


def _arbol(p, r, w, x, y, ang, largo, grosor, nivmax, radio_flor):
    """Cerezo en flor: primero todas las ramas (polígonos) y luego los racimos. Solo hay racimos en las puntas
    por encima del 55 % del alto del árbol, el 20 % de ellas quedan sin racimo (huecos entre ramas), y en el
    borde exterior de la copa el 15 % añade una flor suelta de 5 pétalos."""
    ramas, puntas = [], []
    _rama(r, ramas, puntas, x, y, ang, largo, grosor, 0, nivmax)
    p.setPen(Qt.NoPen)
    for x1, y1, x2, y2, g in ramas:
        _dibujar_rama(p, x1, y1, x2, y2, g)
    if not puntas:
        return
    alto = y - min(min(r_[1], r_[3]) for r_ in ramas)
    cx_c = sum(px for px, _ in puntas) / len(puntas)
    cy_c = sum(py for _, py in puntas) / len(puntas)
    dmax = max(math.hypot(px - cx_c, py - cy_c) for px, py in puntas) or 1.0
    for px, py in puntas:
        if (y - py) < 0.55 * alto:
            continue
        if r.random() < 0.20:
            continue
        _racimo(p, r, w, px, py, radio_flor)
        exterior = math.hypot(px - cx_c, py - cy_c) > 0.6 * dmax
        if exterior and r.random() < 0.15:
            _flor_suelta(p, r, w, px, py)


def _molino(p, cx, base, h):
    """Molino rosa: torre ahusada con franjas, ventana redonda, puerta y tejado. Las aspas van aparte."""
    alto = 0.17 * h
    ancho_b = 0.036 * h
    ancho_t = 0.022 * h
    torre = QPolygonF([QPointF(cx - ancho_b, base), QPointF(cx + ancho_b, base),
                       QPointF(cx + ancho_t, base - alto), QPointF(cx - ancho_t, base - alto)])
    g = QLinearGradient(cx - ancho_b, 0, cx + ancho_b, 0)
    g.setColorAt(0, QColor("#FFD0E4"))
    g.setColorAt(0.6, QColor("#FFB0CF"))
    g.setColorAt(1, QColor("#E88AB0"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawPolygon(torre)
    p.setPen(QPen(con_alfa(QColor("#E88AB0"), 120), max(1.0, h * 0.002)))
    for k in range(1, 5):
        yk = base - alto * k / 5
        mitad = ancho_b + (ancho_t - ancho_b) * (base - yk) / alto
        p.drawLine(QPointF(cx - mitad, yk), QPointF(cx + mitad, yk))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFF6FA"))
    p.drawEllipse(QPointF(cx, base - alto * 0.62), 0.009 * h, 0.009 * h)
    p.setBrush(QColor("#E88AB0"))
    p.drawRoundedRect(QRectF(cx - 0.012 * h, base - 0.05 * h, 0.024 * h, 0.05 * h), 0.012 * h, 0.012 * h)
    # anillo de la galería y tejado cónico
    p.setBrush(QColor("#FF9EC8"))
    p.drawRect(QRectF(cx - ancho_t - 0.008 * h, base - alto - 0.012 * h,
                      2 * (ancho_t + 0.008 * h), 0.012 * h))
    tejado = QPolygonF([QPointF(cx - ancho_t - 0.012 * h, base - alto - 0.012 * h),
                        QPointF(cx, base - alto - 0.065 * h),
                        QPointF(cx + ancho_t + 0.012 * h, base - alto - 0.012 * h)])
    p.setBrush(QColor("#FF9EC8"))
    p.drawPolygon(tejado)
    p.setBrush(con_alfa(QColor("#F27BAE"), 150))
    p.drawPolygon(QPolygonF([QPointF(cx, base - alto - 0.065 * h),
                             QPointF(cx + ancho_t + 0.012 * h, base - alto - 0.012 * h),
                             QPointF(cx, base - alto - 0.012 * h)]))


def _casita(p, x, base, h):
    """Casita de cuento: paredes crema, tejado rosa de tejas, chimenea con humo, ventanas con cortinas."""
    cw, mw = 0.12 * h, 0.075 * h
    pared = QRectF(x - cw / 2, base - mw, cw, mw)
    g = QLinearGradient(0, pared.top(), 0, base)
    g.setColorAt(0, QColor("#FFFBFD"))
    g.setColorAt(1, QColor("#F6DCE8"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRect(pared)
    apice = base - mw - 0.065 * h
    eave_y = base - mw + 0.01 * h
    mitad_alero = cw / 2 + 0.014 * h
    tejado = QPolygonF([QPointF(x, apice), QPointF(x + mitad_alero, eave_y), QPointF(x - mitad_alero, eave_y)])
    p.setBrush(QColor("#FF9EC8"))
    p.drawPolygon(tejado)
    p.setBrush(con_alfa(QColor("#F27BAE"), 150))
    p.drawPolygon(QPolygonF([QPointF(x, apice), QPointF(x + mitad_alero, eave_y), QPointF(x, eave_y)]))
    p.setPen(QPen(con_alfa(QColor("#E77FAE"), 150), max(1.0, h * 0.003)))
    for k in range(1, 5):
        yk = apice + (eave_y - apice) * k / 5
        mitad = mitad_alero * (yk - apice) / (eave_y - apice)
        p.drawLine(QPointF(x - mitad, yk), QPointF(x + mitad, yk))
    # chimenea y humo
    p.setPen(Qt.NoPen)
    xc = x + cw * 0.22
    p.setBrush(QColor("#E58FB3"))
    p.drawRect(QRectF(xc - 0.007 * h, apice + 0.025 * h, 0.014 * h, 0.05 * h))
    p.setBrush(con_alfa(QColor("#FFFFFF"), 150))
    for k in range(3):
        p.drawEllipse(QPointF(xc + (0.008 + 0.006 * k) * h, apice - (0.02 + 0.028 * k) * h),
                      (0.008 + 0.004 * k) * h, (0.008 + 0.004 * k) * h)
    # puerta en arco
    dw, dh = 0.022 * h, 0.05 * h
    puerta = QPainterPath()
    puerta.addRoundedRect(QRectF(x - dw / 2, base - dh, dw, dh), dw / 2, dw / 2)
    p.setBrush(QColor("#E58FB3"))
    p.drawPath(puerta)
    # ventanas con cortinas y macetas
    ww, wh = 0.022 * h, 0.026 * h
    for lado in (-1, 1):
        wx = x + lado * cw * 0.27
        wy = base - mw * 0.72
        p.setBrush(QColor("#FFE9A8"))
        p.setPen(QPen(QColor("#FFFFFF"), max(1.0, h * 0.003)))
        p.drawRect(QRectF(wx - ww / 2, wy, ww, wh))
        p.drawLine(QPointF(wx, wy), QPointF(wx, wy + wh))
        p.drawLine(QPointF(wx - ww / 2, wy + wh / 2), QPointF(wx + ww / 2, wy + wh / 2))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FF9EC8"))
        izq, der = wx - ww / 2, wx + ww / 2
        p.drawPolygon(QPolygonF([QPointF(izq - 0.003 * h, wy - 0.002 * h), QPointF(izq + 0.007 * h, wy),
                                 QPointF(izq + 0.004 * h, wy + wh * 0.8), QPointF(izq - 0.003 * h, wy + wh * 0.6)]))
        p.drawPolygon(QPolygonF([QPointF(der + 0.003 * h, wy - 0.002 * h), QPointF(der - 0.007 * h, wy),
                                 QPointF(der - 0.004 * h, wy + wh * 0.8), QPointF(der + 0.003 * h, wy + wh * 0.6)]))
        p.setBrush(QColor("#FFB0CF"))
        for k in range(4):
            p.drawEllipse(QPointF(wx - ww / 2 + ww * k / 3, wy + wh + 0.004 * h), 0.003 * h, 0.003 * h)


def _valla(p, x0, x1, y, h):
    """Valla blanca: postes con sombra rosada y dos travesaños."""
    p.setPen(Qt.NoPen)
    x = x0
    while x <= x1:
        p.setBrush(QColor("#F5D0E0"))
        p.drawRect(QRectF(x + 0.002 * h, y - 0.035 * h, 0.007 * h, 0.035 * h))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRect(QRectF(x, y - 0.035 * h, 0.007 * h, 0.035 * h))
        x += 0.02 * h
    p.setPen(QPen(QColor("#FFFFFF"), max(1.0, h * 0.005)))
    p.drawLine(QPointF(x0, y - 0.03 * h), QPointF(x1, y - 0.03 * h))
    p.drawLine(QPointF(x0, y - 0.014 * h), QPointF(x1, y - 0.014 * h))


def _banda_niebla(p, w, y_c, alto):
    """Banda de niebla rosada: degradado de alfa 0 → 70 → 0."""
    g = QLinearGradient(0, y_c - alto / 2, 0, y_c + alto / 2)
    g.setColorAt(0, con_alfa(QColor("#FFF0F6"), 0))
    g.setColorAt(0.5, con_alfa(QColor("#FFE0EE"), 70))
    g.setColorAt(1, con_alfa(QColor("#FFF0F6"), 0))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRect(QRectF(0, y_c - alto / 2, w, alto))


class EscenarioMyMelody(EscenarioBase):
    NOMBRE = "My Melody"
    ACENTO = "#FF9EC8"
    SEMILLA = 33

    def preparar(self):
        r = self.rnd
        # sprites: pétalos que vuelan, alas de las mariposas, flores de campo y de la franja del borde
        self._pet_pm = [_sprite_petalo(c) for c in COLORES_PETALO]
        self._mar_pm = [_sprite_mariposa(a, b) for a, b in PARES_ALAS]
        self._flor_pm = [[_sprite_flor(tipo, c) for c in COLORES_FLOR] for tipo in range(3)]
        # pétalos: (x inicial, velocidad, altura relativa, tamaño relativo, fase, giro grados/s, sprite)
        self._petalos = [(r.random(), r.uniform(0.02, 0.05), r.uniform(0.1, 0.9), r.uniform(0.012, 0.022),
                          r.random() * 6.28, r.uniform(-90, 90), r.randrange(len(COLORES_PETALO)))
                         for _ in range(N_PETALOS)]
        # mariposas: (x, y, fase, tamaño relativo al alto, pareja de alas)
        self._mariposas = [(r.uniform(0.1, 0.9), r.uniform(0.2, 0.6), r.random() * 6.28, r.uniform(0.03, 0.04),
                            i % len(PARES_ALAS)) for i in range(N_MARIPOSAS)]
        # franja del borde: (x relativo, alto relativo, fase, y relativa de la base, lleva flor,
        #                    tipo de flor, color, radio de la flor relativo al alto)
        hierba = []
        for i in range(N_HIERBA):
            hierba.append((r.random(), r.uniform(0.03, 0.07), r.random() * 6.28, r.uniform(0.93, 1.02),
                           i < N_FLORES_HIERBA, r.randrange(3), r.randrange(3), r.uniform(0.016, 0.026)))
        r.shuffle(hierba)
        self._hierba = hierba
        # geometría y pixmaps que se fijan en pintar_estatico (dependen del tamaño)
        self._aspas = None
        self._aspas_r = 0.0
        self._hub = (0.0, 0.0)
        self._resplandor = None
        self._res_pos = QPointF(0, 0)
        self._giro = 0.0
        self._t_ult = -1.0

    # ------------------------------------------------------------ estático

    def pintar_estatico(self, p, w, h):
        r = random.Random(97)
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)

        # cielo: degradado rosa con el horizonte en el 50 %
        cielo = QLinearGradient(0, 0, 0, h)
        cielo.setColorAt(0, QColor(CIELO_ARRIBA))
        cielo.setColorAt(0.3, QColor(CIELO_MEDIO))
        cielo.setColorAt(0.5, QColor(CIELO_HORIZONTE))
        cielo.setColorAt(1, QColor(CIELO_HORIZONTE))
        p.fillRect(0, 0, w, h, cielo)
        # luz de mañana: un resplandor cálido y suave hacia la izquierda del horizonte
        self.brillo(p, 0.30 * w, 0.48 * h, 0.55 * w, QColor("#FFF6E4"), 150)

        for cx, cy, tam in ((0.14, 0.16, 1.0), (0.42, 0.10, 0.8), (0.76, 0.19, 1.1),
                            (0.92, 0.33, 0.6), (0.30, 0.31, 0.5)):
            _nube(p, r, cx * w, cy * h, tam * h)

        # cordilleras lejanas por desplazamiento del punto medio, con bruma
        p.setPen(Qt.NoPen)
        for y_medio, amp, color in CORDILLERAS:
            pts = _cresta(r, w, h, y_medio, amp * h)
            p.setBrush(mezclar(QColor(color), BRUMA, 0.65))
            p.drawPolygon(QPolygonF(pts + [QPointF(w, h), QPointF(0, h)]))

        # colinas en 4 capas con perspectiva atmosférica y bandas de niebla entre ellas
        for i, (base, amp, fase, frec, color, mezcla) in enumerate(COLINAS):
            p.setPen(Qt.NoPen)
            p.setBrush(mezclar(QColor(color), BRUMA, mezcla))
            p.drawPath(_camino_colina(w, h, base, amp, fase, frec))
            if i + 1 < len(COLINAS):
                sig = COLINAS[i + 1]
                _banda_niebla(p, w, h * sig[0] - sig[1] * h * 0.9, 0.1 * h)

        # suelo del campo: se funde desde la última colina (sin borde horizontal duro)
        y_ini, y_fin = 0.73 * h, h
        f = (0.80 * h - y_ini) / (y_fin - y_ini)
        campo = QLinearGradient(0, y_ini, 0, y_fin)
        campo.setColorAt(0, con_alfa(QColor("#BDE6C8"), 0))
        campo.setColorAt(f, QColor("#BDE6C8"))
        campo.setColorAt(1, QColor("#9ED6AC"))
        p.setPen(Qt.NoPen)
        p.setBrush(campo)
        p.drawRect(QRectF(0, y_ini, w, y_fin - y_ini))

        # molino y casita en la colina media
        base_colina = COLINAS[1][:4]
        xm = 0.64 * w
        base_m = _altura(xm, w, h, *base_colina)
        _molino(p, xm, base_m, h)
        self._hub = (xm, base_m - 0.17 * h - 0.03 * h)
        self._aspas_r = 0.10 * h
        self._aspas = _sprite_aspas(self._aspas_r)
        xc = 0.86 * w
        base_c = _altura(xc, w, h, *base_colina)
        _casita(p, xc, base_c, h)
        _valla(p, 0.78 * w, 0.97 * w, _altura(0.97 * w, w, h, *base_colina) + 0.01 * h, h)

        # cerezos en plano medio (con menos ramas) y el grande a la izquierda en primer plano
        base_3 = COLINAS[2][:4]
        _arbol(p, r, w, 0.40 * w, _altura(0.40 * w, w, h, *base_3) + 0.01 * h, -10, 0.12 * h, 0.02 * h, 4, 0.022 * h)
        _arbol(p, r, w, 0.97 * w, _altura(0.97 * w, w, h, *base_3), -6, 0.11 * h, 0.018 * h, 4, 0.02 * h)

        self._campo_estatico(p, r, w, h)

        p.setPen(Qt.NoPen)
        _arbol(p, r, w, 0.10 * w, 1.02 * h, 6, 0.23 * h, 0.04 * h, NIVEL_MAX, 0.034 * h)

        # resplandor rosa que respira: se pre-renderiza y en lo animado se mueve su opacidad
        ancho, alto = max(1, int(0.36 * w)), max(1, int(0.30 * h))
        self._resplandor = _sprite_resplandor(self.acento(), ancho, alto)
        self._res_pos = QPointF(0.50 * w - ancho / 2, 0.30 * h - alto / 2)

        # grano fino y vineta rosada
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(90, 40, 70, 6), 1.5))
        puntos = [QPointF(r.uniform(0, w), r.uniform(0, h)) for _ in range(N_GRANO)]
        p.drawPoints(QPolygonF(puntos))
        radio_v = math.hypot(w, h) / 2
        vineta = QRadialGradient(QPointF(w / 2, h / 2), radio_v)
        vineta.setColorAt(0.0, con_alfa(QColor("#D98AA8"), 0))
        vineta.setColorAt(0.6, con_alfa(QColor("#D98AA8"), 0))
        vineta.setColorAt(1.0, con_alfa(QColor("#D98AA8"), 60))
        p.fillRect(0, 0, w, h, vineta)
        p.restore()

    def _campo_estatico(self, p, r, w, h):
        """Campo: flores de 3 tipos con tallo (más grandes y separadas abajo, diminutas y apretadas al fondo),
        y briznas de hierba en trazos curvos. La franja del borde se deja libre: se anima aparte."""
        y0, ys = 0.78 * h, ZONA_HIERBA * h
        tallos = QPainterPath()
        cabezas = []
        for _ in range(N_FLORES_CAMPO):
            d = r.random() ** 1.5
            y = y0 + (ys - y0) * d
            x = r.uniform(-0.01 * w, 1.01 * w)
            rr = h * (0.004 + 0.020 * d)
            if rr > 2.5:
                tallos.moveTo(x, y)
                tallos.quadTo(QPointF(x + r.uniform(-0.3, 0.3) * rr, y + rr * 0.8),
                              QPointF(x + r.uniform(-0.5, 0.5) * rr, y + rr * 1.7))
            cabezas.append((x, y, rr, r.randrange(3), r.randrange(3)))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#8CCB9C"), max(1.0, h * 0.0014), Qt.SolidLine, Qt.RoundCap))
        p.drawPath(tallos)
        for x, y, rr, tipo, ci in cabezas:
            pm = self._flor_pm[tipo][ci]
            p.drawPixmap(QRectF(x - rr, y - rr, 2 * rr, 2 * rr), pm, QRectF(pm.rect()))

        # briznas de hierba en trazos curvos, agrupadas por color
        grupos = {"#7DBF94": QPainterPath(), "#8CCB9C": QPainterPath(), "#A3D7AE": QPainterPath()}
        claves = list(grupos)
        for _ in range(N_BRIZNAS):
            d = r.random() ** 1.2
            y = y0 + (ys - y0) * d
            x = r.uniform(-0.01 * w, 1.01 * w)
            largo = h * (0.006 + 0.02 * d)
            incl = r.uniform(-0.6, 0.6)
            cam = grupos[claves[r.randrange(3)]]
            cam.moveTo(x, y)
            cam.quadTo(QPointF(x + largo * 0.3 * incl, y - largo * 0.5),
                       QPointF(x + largo * incl, y - largo))
        for color, cam in grupos.items():
            p.setPen(QPen(QColor(color), max(1.0, h * 0.0012), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(cam)

    # ------------------------------------------------------------ animado

    def pintar_animado(self, p, w, h, t):
        if self._aspas is None or self._resplandor is None:
            return
        e = self.energia()
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # resplandor rosa que respira con el tiempo y con el audio
        op = min(1.0, 0.25 + 0.22 * (0.5 + 0.5 * math.sin(t * 0.6)) + 0.3 * min(1.0, e))
        p.setOpacity(op)
        p.drawPixmap(self._res_pos, self._resplandor)
        p.setOpacity(1.0)

        # pétalos que viajan de izquierda a derecha con la brisa, balanceándose y girando
        for u0, vel, yf, tam, ph, giro, ci in self._petalos:
            u = (u0 + vel * t) % 1.0
            x = (-0.05 + 1.1 * u) * w
            y = yf * h + 0.03 * h * math.sin(t * 0.6 + ph)
            s = min(tam * h * 0.96, 12.0 * h / 1080.0)     # 40 % del tamaño anterior, máx. 12 px a 1080p
            pm = self._pet_pm[ci]
            p.save()
            p.translate(x, y)
            p.rotate(giro * t + math.degrees(ph))
            p.drawPixmap(QRectF(-s / 2, -s / 2, s, s), pm, QRectF(pm.rect()))
            p.restore()

        # mariposas pastel: alas que aletean (escala horizontal) y recorrido lento en curva
        for xf, yf, ph, tam, par in self._mariposas:
            cx = (xf + 0.08 * math.sin(t * 0.13 + ph)) * w
            cy = (yf + 0.05 * math.sin(t * 0.21 + ph * 2.0)) * h
            S = tam * h
            k = S / 40.0
            aleteo = max(0.18, abs(math.sin(t * 7.0 + ph)))
            pm = self._mar_pm[par]
            p.save()
            p.translate(cx, cy)
            p.rotate(8 * math.sin(t * 0.5 + ph))
            for lado in (-1, 1):
                p.save()
                p.scale(lado * aleteo * k, k)
                p.drawPixmap(QPointF(0, -20), pm)
                p.restore()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#B48EAD"))
            p.drawEllipse(QPointF(0, 0), 0.06 * S, 0.3 * S)
            p.restore()

        # aspas del molino: giran más rápido cuando hay música
        if self._t_ult >= 0:
            dt = max(0.0, min(0.1, t - self._t_ult))
        else:
            dt = 0.0
        self._t_ult = t
        self._giro = (self._giro + dt * (35.0 + 240.0 * e)) % 360.0
        hx, hy = self._hub
        R = self._aspas_r
        p.save()
        p.translate(hx, hy)
        p.rotate(self._giro)
        p.drawPixmap(QPointF(-R, -R), self._aspas)
        p.restore()

        # franja del borde: hierba que se mece (tallos de dos tramos rectos) y flores en las puntas
        cabezas = []
        viento = 0.006 * h * math.sin(t * 0.4)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(COLOR_TALLO), max(1.0, 0.0022 * h), Qt.SolidLine, Qt.RoundCap))
        for xf, hf, ph, yf, con_flor, tipo, ci, rf in self._hierba:
            x = xf * w
            yb = yf * h
            alt = hf * h
            bal = 0.012 * h * math.sin(t * 1.3 + ph) + viento
            medio = QPointF(x + bal * 0.4, yb - alt * 0.55)
            tip = QPointF(x + bal, yb - alt)
            p.drawLine(QPointF(x, yb), medio)
            p.drawLine(medio, tip)
            if con_flor:
                cabezas.append((tip, rf * h, tipo, ci))
        for tip, rr, tipo, ci in cabezas:
            pm = self._flor_pm[tipo][ci]
            p.drawPixmap(QRectF(tip.x() - rr, tip.y() - rr, 2 * rr, 2 * rr), pm, QRectF(pm.rect()))

        p.restore()

        # ondas de la música en rosa pastel sobre la colina más cercana
        self.ondas(p, base_y=0.70 * h, ancho=w, alto_max=0.09 * h, color=self.acento())
