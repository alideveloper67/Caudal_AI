# -*- coding: utf-8 -*-
"""Escenario «Gótico»: catedral nocturna bajo la luna llena, con perspectiva atmosférica.

Lo estático se pinta una vez: cielo, luna con halo y cráteres, cinco bandas de nubes con borde lunar,
colinas y pinos lejanos, bandas de niebla, catedral con arbotantes y vitrales, árboles muertos, cementerio,
verja de hierro y grano con viñeta. Lo animado (cada cuadro) es ligero: niebla en tres capas pregeneradas que
se desplazan, murciélagos con tres cuadros de aleteo, velas que titilan tras las ventanas, el rosetón que
brilla con la música, un cuervo que gira la cabeza y ascuas que suben.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)

from .base import EscenarioBase, con_alfa, mezclar

NOCHE = "#050307"          # siluetas cercanas (cementerio, árboles, verja, lápidas)
SUELO = "#1C1424"          # colina del cementerio
HIERBA_A, HIERBA_B = "#1A1220", "#241A2C"
CATEDRAL = "#07050A"       # silueta de la catedral
LEJANO = "#0E0A14"         # colinas lejanas antes de mezclar con la niebla
NIEBLA = "#3B2A45"         # color de la niebla (destino de la perspectiva atmosférica)
SOMBRA_NUBE = "#140C1A"
LUZ_LUNA = "#8C7FA0"
CALIDA = "#FF9F5A"         # luz de las velas
VINO, PURPURA, TERRACOTA, AZUL = "#6B0F1A", "#3B1458", "#A0522D", "#1F4E79"
PLOMO = "#050305"

MEZCLA_LEJOS, MEZCLA_MEDIO, MEZCLA_CERCA = 0.65, 0.35, 0.0
PERIODO_CABEZA = 6.5       # s entre giros de la cabeza del cuervo
LUNA_X, LUNA_Y, LUNA_R = 0.36, 0.17, 0.085     # luna (fracciones de w, h y h), entre el árbol y la aguja

# Ventanas de la catedral: (x, base, ancho, alto) en fracciones de w (x, ancho) y h (base, alto);
# las encendidas (True) son las seis velas que titilan.
VENTANAS = (
    (0.24, 0.50, 0.018, 0.10, True),
    (0.24, 0.36, 0.014, 0.07, True),
    (0.76, 0.50, 0.018, 0.10, True),
    (0.76, 0.36, 0.014, 0.07, True),
    (0.41, 0.72, 0.024, 0.14, True),
    (0.59, 0.72, 0.024, 0.14, True),
    (0.24, 0.70, 0.020, 0.12, False),
    (0.76, 0.70, 0.020, 0.12, False),
)


# ---------------------------------------------------------------- geometría (devuelve QPainterPath)

def _rect(x0, y0, x1, y1):
    c = QPainterPath()
    c.addRect(QRectF(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))
    return c


def _pinaculo(x, yb, ancho, alto):
    """Triángulo de pináculo apoyado en (x, yb)."""
    c = QPainterPath(QPointF(x - ancho / 2, yb))
    c.lineTo(QPointF(x, yb - alto))
    c.lineTo(QPointF(x + ancho / 2, yb))
    c.closeSubpath()
    return c


def _aguja(cx, yb, hb, yt):
    """Aguja gótica: de la base (semiancho hb en yb) a la punta (cx, yt), con lados cóncavos."""
    alto = yb - yt
    c = QPainterPath(QPointF(cx - hb, yb))
    c.cubicTo(QPointF(cx - hb * 0.85, yb - alto * 0.40), QPointF(cx - hb * 0.20, yt + alto * 0.25), QPointF(cx, yt))
    c.cubicTo(QPointF(cx + hb * 0.20, yt + alto * 0.25), QPointF(cx + hb * 0.85, yb - alto * 0.40), QPointF(cx + hb, yb))
    c.closeSubpath()
    return c


def _ojival(x, base, ancho, alto):
    """Ventana de arco apuntado (dos arcos que se juntan arriba), centrada en x, base en `base`."""
    izq, der = x - ancho / 2, x + ancho / 2
    cima = base - alto
    arranque = base - alto * 0.62
    c = QPainterPath(QPointF(izq, base))
    c.lineTo(QPointF(izq, arranque))
    c.cubicTo(QPointF(izq, arranque - alto * 0.20), QPointF(x - ancho * 0.10, cima + alto * 0.12), QPointF(x, cima))
    c.cubicTo(QPointF(x + ancho * 0.10, cima + alto * 0.12), QPointF(der, arranque - alto * 0.20), QPointF(der, arranque))
    c.lineTo(QPointF(der, base))
    c.closeSubpath()
    return c


def _gargola(x, y, s, lado):
    """Gárgola agachada sobre el borde (x, y): cuerpo, cabeza y cuerno hacia `lado` (-1 o 1). Lista de piezas."""
    cab = QPointF(x + lado * s * 0.36, y - s * 0.92)
    cuerpo = QPainterPath()
    cuerpo.addEllipse(QPointF(x, y - s * 0.45), s * 0.30, s * 0.42)
    cabeza = QPainterPath()
    cabeza.addEllipse(cab, s * 0.24, s * 0.20)
    cuerno = QPainterPath(QPointF(cab.x() - lado * s * 0.05, cab.y() - s * 0.12))
    cuerno.lineTo(QPointF(cab.x() + lado * s * 0.10, cab.y() - s * 0.42))
    cuerno.lineTo(QPointF(cab.x() + lado * s * 0.18, cab.y() - s * 0.10))
    cuerno.closeSubpath()
    return [cuerpo, cabeza, cuerno]


def _pintar_piezas(p, piezas, color, grueso=0.0):
    """Rellena las piezas; con `grueso`, primero un borde de luna en su parte superior."""
    p.setPen(Qt.NoPen)
    if grueso > 0:
        borde = QColor(LUZ_LUNA)
        borde.setAlpha(90)
        p.setBrush(borde)
        for c in piezas:
            p.save()
            p.translate(0, -grueso)
            p.drawPath(c)
            p.restore()
    p.setBrush(QBrush(QColor(color)))
    for c in piezas:
        p.drawPath(c)


def _relleno_hasta_abajo(xs, ys, h):
    c = QPainterPath(QPointF(xs[0], h))
    for x, y in zip(xs, ys):
        c.lineTo(QPointF(x, y))
    c.lineTo(QPointF(xs[-1], h))
    c.closeSubpath()
    return c


class EscenarioGotico(EscenarioBase):
    NOMBRE = "Gótico"
    ACENTO = "#B91C3C"
    SEMILLA = 33

    def preparar(self):
        r = self.rnd
        # murciélagos: (altura, posición inicial, velocidad, escala, fase, cuadros de aleteo por segundo)
        self.murcielagos = []
        for _ in range(8):
            sentido = 1 if r.random() < 0.5 else -1
            self.murcielagos.append((
                r.uniform(0.12, 0.50),
                r.random(),
                sentido * r.uniform(0.008, 0.016),
                r.uniform(0.012, 0.020),
                r.uniform(0.0, 6.28),
                r.uniform(3.0, 5.0),
            ))
        # ascuas que suben: (x, y inicial, velocidad, fase de recorrido, tamaño, fase de parpadeo)
        self.ascuas = [(r.random(), r.uniform(0.70, 0.95), r.uniform(0.02, 0.05), r.random(),
                        r.uniform(0.8, 1.8), r.uniform(0.0, 6.28)) for _ in range(30)]
        self._clave_sprites = None
        self._capas_niebla = []
        self._pm_murcielagos = []

    # ------------------------------------------------------------ perspectiva y ayudas del estático

    def _cresta_lejana(self, x, w, h):
        u = x / w
        return h * (0.655 + 0.020 * math.sin(2 * math.pi * 1.3 * u + 0.7)
                    + 0.011 * math.sin(2 * math.pi * 3.1 * u + 2.1) + 0.005 * math.sin(2 * math.pi * 7.7 * u))

    def _cresta_media(self, x, w, h):
        u = x / w
        return h * (0.765 + 0.012 * math.sin(2 * math.pi * 2.1 * u + 1.3) + 0.006 * math.sin(2 * math.pi * 5.3 * u))

    def _banda_niebla(self, p, w, y, alto, color, alfa):
        """Banda de niebla entre capas: alfa 0 → `alfa` → 0 en vertical."""
        g = QLinearGradient(0, y, 0, y + alto)
        c = QColor(color)
        g.setColorAt(0, con_alfa(c, 0))
        g.setColorAt(0.5, con_alfa(c, alfa))
        g.setColorAt(1, con_alfa(c, 0))
        p.fillRect(QRectF(0, y, w, alto), g)

    def _estrellas(self, p, w, h, r):
        p.setPen(Qt.NoPen)
        for _ in range(160):
            x, y = r.random() * w, r.random() * 0.50 * h
            p.setBrush(con_alfa(QColor("#E8E1EF"), r.randint(40, 120)))
            tam = (0.4 + 0.9 * r.random()) * h / 540.0
            p.drawEllipse(QPointF(x, y), tam, tam)

    def _luna(self, p, w, h, r):
        cx, cy, rad = LUNA_X * w, LUNA_Y * h, LUNA_R * h
        self.brillo(p, cx, cy, 0.35 * h, "#C9B8E8", 90)
        g = QRadialGradient(QPointF(cx - rad * 0.3, cy - rad * 0.3), rad * 1.25)
        g.setColorAt(0.0, QColor("#F8F4FA"))
        g.setColorAt(0.7, QColor("#EDE6F2"))
        g.setColorAt(1.0, QColor("#CFC3DA"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), rad, rad)
        # cráteres tenues de tamaños variados, con un borde más claro abajo-derecha
        for _ in range(12):
            ang = r.uniform(0.0, 2 * math.pi)
            dist = rad * r.uniform(0.05, 0.75)
            cr = rad * r.uniform(0.04, 0.22)
            px, py = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
            p.setBrush(QColor(255, 255, 255, 25))
            p.drawEllipse(QPointF(px + cr * 0.25, py + cr * 0.25), cr, cr * 0.8)
            p.setBrush(QColor(90, 80, 105, 25))
            p.drawEllipse(QPointF(px, py), cr, cr * r.uniform(0.7, 1.0))

    def _nubes(self, p, w, h, r):
        """Cinco nubes alargadas y difusas: 40–80 elipses aplanadas (2.5:1) con degradado. Detrás de cada una,
        una elipse más clara desplazada hacia arriba: solo se ve el borde superior iluminado por la luna."""
        bandas = ((0.07, 0.20), (0.17, 0.30), (0.28, 0.35), (0.40, 0.45), (0.52, 0.65))
        dy = max(1.5, h / 360.0)
        lx, ly, lr = LUNA_X * w, LUNA_Y * h, LUNA_R * h
        p.setPen(Qt.NoPen)
        for yc, mezcla in bandas:
            n = r.randint(40, 80)
            espesor = 0.07 * h
            elipses = []
            for _ in range(n):
                xf = r.uniform(-0.05, 1.05)
                x = xf * w
                y = yc * h + r.uniform(-espesor / 2, espesor / 2)
                rx = w * r.uniform(0.035, 0.09) * (1.0 - min(1.0, abs(xf - 0.5) * 1.6) * 0.35)
                alfa = r.randint(160, 220)
                if math.hypot(x - lx, y - ly) < lr * 2.0 + rx * 0.6:
                    continue          # la luna se ve despejada
                elipses.append((x, y, rx, rx / 2.5, alfa))
            sombra = mezclar(QColor(SOMBRA_NUBE), QColor(NIEBLA), mezcla)
            luz = mezclar(QColor(LUZ_LUNA), QColor(NIEBLA), mezcla)
            # pasada 1: el borde iluminado, desplazado hacia arriba
            p.setBrush(con_alfa(luz, 90))
            for x, y, rx, ry, _ in elipses:
                p.drawEllipse(QPointF(x, y - dy), rx, ry)
            # pasada 2: el cuerpo de la nube, con degradado; más claro cerca de la luna
            for x, y, rx, ry, alfa in elipses:
                cerca = max(0.0, 1.0 - math.hypot(x - lx, y - ly) / (lr * 4.0)) * 0.35
                centro = mezclar(sombra, luz, cerca)
                g = QRadialGradient(QPointF(0, 0), 1.0)
                g.setColorAt(0.0, con_alfa(centro, alfa))
                g.setColorAt(0.7, con_alfa(centro, alfa * 0.85))
                g.setColorAt(1.0, con_alfa(centro, 0))
                p.save()
                p.translate(x, y)
                p.scale(rx, ry)
                p.setBrush(QBrush(g))
                p.drawEllipse(QPointF(0, 0), 1.0, 1.0)
                p.restore()

    def _colina(self, p, w, h, ridge, color):
        xs = [w * i / 60.0 for i in range(61)]
        ys = [ridge(x) for x in xs]
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawPath(_relleno_hasta_abajo(xs, ys, h))
        return ys

    def _pinos(self, p, w, h, r, color):
        """Fila de pinos lejanos: triángulos dentados apilados (5 a 7 escalones)."""
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        for _ in range(46):
            px = min(w, max(0.0, r.uniform(-0.01, 1.01) * w))
            base = self._cresta_lejana(px, w, h) + r.uniform(0.0, 0.01) * h
            hp = h * r.uniform(0.045, 0.085)
            n = r.randint(5, 7)
            for i in range(n):
                k = i / n
                yb = base - hp * 0.78 * k
                yt = yb - hp * 0.45
                mitad = hp * 0.40 * (1.0 - 0.55 * k)
                p.drawPolygon(QPolygonF([QPointF(px - mitad, yb), QPointF(px, yb - hp * 0.06),
                                         QPointF(px + mitad, yb), QPointF(px, yt)]))

    def _catedral(self, w, h):
        """Piezas (rellenos) y trazos (arbotantes) de la catedral, en silueta."""
        piezas = []
        izq, der = 0.36 * w, 0.64 * w
        # nave: muros y tejado a dos aguas
        tejado = QPainterPath(QPointF(izq, 0.80 * h))
        tejado.lineTo(QPointF(izq, 0.46 * h))
        tejado.lineTo(QPointF(0.5 * w, 0.36 * h))
        tejado.lineTo(QPointF(der, 0.46 * h))
        tejado.lineTo(QPointF(der, 0.80 * h))
        tejado.closeSubpath()
        piezas.append(tejado)
        piezas.append(_aguja(0.5 * w, 0.38 * h, 0.022 * w, 0.12 * h))
        piezas.append(_pinaculo(izq, 0.46 * h, 0.016 * w, 0.05 * h))
        piezas.append(_pinaculo(der, 0.46 * h, 0.016 * w, 0.05 * h))
        # cuerpo bajo de las naves laterales, entre los contrafuertes
        piezas.append(_rect(0.31 * w, 0.64 * h, 0.69 * w, 0.80 * h))
        # contrafuertes con pináculo
        for xp in (0.31 * w, 0.69 * w):
            piezas.append(_rect(xp - 0.006 * w, 0.58 * h, xp + 0.006 * w, 0.80 * h))
            piezas.append(_pinaculo(xp, 0.58 * h, 0.014 * w, 0.06 * h))
        # torres: tres cuerpos que se estrechan, cornisas, pináculos, agujas y gárgolas
        for cx in (0.24 * w, 0.76 * w):
            for yb, yt, mitad in ((0.80, 0.54, 0.050), (0.54, 0.38, 0.040), (0.38, 0.26, 0.030)):
                piezas.append(_rect(cx - mitad * w, yt * h, cx + mitad * w, yb * h))
            for yc, mitad in ((0.54, 0.052), (0.38, 0.042)):
                piezas.append(_rect(cx - mitad * w, yc * h - 0.010 * h, cx + mitad * w, yc * h + 0.006 * h))
                piezas.append(_pinaculo(cx - mitad * w * 0.75, yc * h, 0.010 * w, 0.06 * h))
                piezas.append(_pinaculo(cx + mitad * w * 0.75, yc * h, 0.010 * w, 0.06 * h))
            piezas.append(_aguja(cx, 0.265 * h, 0.030 * w, 0.07 * h))
            lado = -1 if cx < 0.5 * w else 1
            piezas += _gargola(cx + lado * 0.05 * w, 0.54 * h, 0.035 * h, lado)
            piezas += _gargola(cx - lado * 0.05 * w, 0.54 * h, 0.035 * h, -lado)
        # gárgolas en las esquinas del tejado de la nave
        piezas += _gargola(izq, 0.46 * h, 0.030 * h, -1)
        piezas += _gargola(der, 0.46 * h, 0.030 * h, 1)
        # arbotantes: cuartos de arco desde el pináculo del contrafuerte hasta el muro de la nave
        trazos = []
        ancho_trazo = max(2.0, 0.009 * h)
        for xp, xw, sentido in ((0.31 * w, izq, -1), (0.69 * w, der, 1)):
            rx = abs(xw - xp)
            ry = 0.58 * h - 0.48 * h
            rect = QRectF(xw - rx, 0.58 * h - ry, 2 * rx, 2 * ry)
            arco = QPainterPath(QPointF(xp, 0.58 * h))
            if sentido < 0:
                arco.arcTo(rect, 180, -90)
            else:
                arco.arcTo(rect, 0, 90)
            trazos.append((arco, ancho_trazo))
        return piezas, trazos

    def _rosetón(self, p, cx, cy, rad):
        vidrio = [VINO, PURPURA, TERRACOTA, AZUL]
        # anillo de piedra alrededor del rosetón
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(CATEDRAL), rad * 0.12))
        p.drawEllipse(QPointF(cx, cy), rad * 1.10, rad * 1.10)
        p.setPen(Qt.NoPen)
        # 16 sectores de vitral en colores alternos
        for i in range(16):
            camino = QPainterPath(QPointF(cx, cy))
            camino.arcTo(QRectF(cx - rad, cy - rad, 2 * rad, 2 * rad), i * 22.5, 22.5)
            camino.closeSubpath()
            p.setBrush(con_alfa(QColor(vidrio[i % 4]), 215))
            p.drawPath(camino)
        # 8 pétalos interiores, radiales
        for i in range(8):
            th = i * 45 + 22.5
            ang = math.radians(th)
            px, py = cx + math.cos(ang) * rad * 0.36, cy - math.sin(ang) * rad * 0.36
            p.save()
            p.translate(px, py)
            p.rotate(90 - th)
            p.setBrush(con_alfa(QColor(vidrio[(i + 2) % 4]), 235))
            p.drawEllipse(QRectF(-rad * 0.12, -rad * 0.26, rad * 0.24, rad * 0.52))
            p.restore()
        p.setBrush(QColor(PURPURA))
        p.drawEllipse(QPointF(cx, cy), rad * 0.14, rad * 0.14)
        # emplomado: 16 radios y dos anillos, en plomo
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(PLOMO), max(1.5, rad * 0.035)))
        for i in range(16):
            ang = math.radians(i * 22.5)
            d = QPointF(math.cos(ang), -math.sin(ang))
            p.drawLine(QPointF(cx + d.x() * rad * 0.14, cy + d.y() * rad * 0.14),
                       QPointF(cx + d.x() * rad, cy + d.y() * rad))
        p.setPen(QPen(QColor(PLOMO), max(2.0, rad * 0.05)))
        p.drawEllipse(QPointF(cx, cy), rad * 0.98, rad * 0.98)
        p.setPen(QPen(QColor(PLOMO), max(1.5, rad * 0.035)))
        p.drawEllipse(QPointF(cx, cy), rad * 0.60, rad * 0.60)
        p.setPen(Qt.NoPen)

    def _arbol(self, p, x, y, largo, grosor, r):
        self._rama(p, x, y, -90.0 + r.uniform(-4, 4), largo, grosor, 0, r)

    def _rama(self, p, x, y, ang, largo, grosor, nivel, r):
        """Rama ahusada (polígono) y, recursivamente, 2 o 3 hijos con ±20–45° y largo×0.7, grosor×0.65."""
        rad = math.radians(ang)
        dx, dy = math.cos(rad), math.sin(rad)
        x2, y2 = x + dx * largo, y + dy * largo
        nx, ny = -dy, dx
        g2 = grosor * 0.65
        p.drawPolygon(QPolygonF([QPointF(x + nx * grosor / 2, y + ny * grosor / 2),
                                 QPointF(x2 + nx * g2 / 2, y2 + ny * g2 / 2),
                                 QPointF(x2 - nx * g2 / 2, y2 - ny * g2 / 2),
                                 QPointF(x - nx * grosor / 2, y - ny * grosor / 2)]))
        if nivel >= 7 or g2 < 0.6 or largo < 2.0:
            return
        if r.random() < 0.5:
            deltas = (-r.uniform(20, 45), r.uniform(20, 45))
        else:
            deltas = (-r.uniform(25, 45), r.uniform(-8, 8), r.uniform(25, 45))
        for d in deltas:
            nuevo = min(-8.0, max(-172.0, ang + d))
            self._rama(p, x2, y2, nuevo, largo * 0.7 * r.uniform(0.92, 1.06), g2, nivel + 1, r)

    def _lapida(self, p, x, y, ancho, alto, tipo, giro, grueso):
        """Lápida en silueta con su base en (x, y). Borde de luna de `grueso` px en la parte superior."""
        hw = ancho / 2
        piezas = []
        if tipo == "redondeada":
            yc = -(alto - hw)
            c = QPainterPath(QPointF(-hw, 0))
            c.lineTo(QPointF(-hw, yc))
            c.arcTo(QRectF(-hw, yc - hw, ancho, ancho), 180, -180)
            c.lineTo(QPointF(hw, 0))
            c.closeSubpath()
            piezas.append(c)
        elif tipo == "obelisco":
            c = QPainterPath(QPointF(-hw * 0.8, 0))
            c.lineTo(QPointF(-hw * 0.6, -alto * 0.85))
            c.lineTo(QPointF(0, -alto))
            c.lineTo(QPointF(hw * 0.6, -alto * 0.85))
            c.lineTo(QPointF(hw * 0.8, 0))
            c.closeSubpath()
            piezas.append(c)
        elif tipo == "losa":
            c = QPainterPath()
            c.addRoundedRect(QRectF(-hw, -alto, ancho, alto), ancho * 0.12, ancho * 0.12)
            piezas.append(c)
        else:  # cruz celta: fuste, travesaño y círculo en el cruce
            fuste = _rect(-ancho * 0.11, -alto, ancho * 0.11, 0)
            travesano = _rect(-hw * 0.9, -alto * 0.74, hw * 0.9, -alto * 0.74 + ancho * 0.16)
            piezas += [fuste, travesano]
        p.save()
        p.translate(x, y)
        p.rotate(giro)
        p.setPen(Qt.NoPen)
        borde = QColor(LUZ_LUNA)
        borde.setAlpha(100)
        p.setBrush(borde)
        for c in piezas:
            p.save()
            p.translate(0, -grueso)
            p.drawPath(c)
            p.restore()
        p.setBrush(QColor(NOCHE))
        for c in piezas:
            p.drawPath(c)
        if tipo == "cruz":
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(NOCHE), ancho * 0.16))
            p.drawEllipse(QPointF(0, -alto * 0.74 + ancho * 0.08), ancho * 0.30, ancho * 0.30)
        p.restore()

    def _verja(self, p, w, h):
        """Verja de hierro forjado a lo ancho: barrotes con punta de lanza, riel superior e inferior y volutas."""
        top, bot = 0.86 * h, h
        paso = max(10.0, w * 0.011)
        bw = max(2.0, w * 0.0035)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(NOCHE))
        p.drawRect(QRectF(0, top, w, max(3.0, 0.012 * h)))
        p.drawRect(QRectF(0, bot - 0.06 * h, w, max(3.0, 0.012 * h)))
        x = 0.0
        while x <= w + paso:
            p.drawRect(QRectF(x - bw / 2, top, bw, bot - top))
            p.drawPath(_pinaculo(x, top, bw * 2.6, 0.022 * h))
            x += paso
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(NOCHE), max(1.5, bw * 0.7)))
        x = paso / 2
        while x < w:
            p.drawEllipse(QPointF(x, top + 0.018 * h), paso * 0.18, paso * 0.18)
            x += paso
        p.setPen(Qt.NoPen)

    def _piedras_y_arboles(self, p, w, h, r):
        # cementerio: suelo en primer plano con una pequeña ondulación
        suelo = QPainterPath(QPointF(0, 0.84 * h))
        suelo.cubicTo(QPointF(0.30 * w, 0.80 * h), QPointF(0.62 * w, 0.88 * h), QPointF(w, 0.83 * h))
        suelo.lineTo(QPointF(w, h))
        suelo.lineTo(QPointF(0, h))
        suelo.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(SUELO))
        p.drawPath(suelo)
        # hierba: trazos cortos y curvos, verticales, muy oscuros
        p.setBrush(Qt.NoBrush)
        for i in range(2000):
            x = r.uniform(0, w)
            yb = r.uniform(0.86, 1.0) * h
            largo = h * r.uniform(0.012, 0.035)
            curva = r.uniform(-0.4, 0.4) * largo
            p.setPen(QPen(QColor(HIERBA_A if i % 2 else HIERBA_B), max(1.0, h * 0.0015), Qt.SolidLine, Qt.RoundCap))
            camino = QPainterPath(QPointF(x, yb))
            camino.quadTo(QPointF(x + curva * 0.5, yb - largo * 0.5), QPointF(x + curva, yb - largo))
            p.drawPath(camino)
        # niebla baja delante del suelo: la verja y las lápidas se leen contra ella
        self._banda_niebla(p, w, 0.80 * h, 0.17 * h, NIEBLA, 80)
        # árboles muertos a los lados
        p.setBrush(QColor(NOCHE))
        self._arbol(p, 0.09 * w, 0.86 * h, 0.30 * h, 0.030 * h, r)
        self._arbol(p, 0.92 * w, 0.86 * h, 0.27 * h, 0.028 * h, r)
        # doce lápidas de formas variadas
        grueso = max(1.0, h * 0.0013)
        tipos = ("redondeada", "cruz", "obelisco", "losa")
        for i in range(12):
            x = (0.07 + i * 0.077 + r.uniform(-0.010, 0.010)) * w
            if abs(x - 0.66 * w) < 0.05 * w:
                x += 0.07 * w
            y = r.uniform(0.90, 0.93) * h
            ancho = h * 0.062 * r.uniform(0.8, 1.2)
            alto = h * r.uniform(0.09, 0.15)
            giro = r.uniform(-6, 6) if r.random() < 0.35 else 0.0
            self._lapida(p, x, y, ancho, alto, tipos[i % 4], giro, grueso)
        # lápida del cuervo, en el centro derecho (su cima es (0.66w, 0.78h))
        self._lapida(p, 0.66 * w, 0.92 * h, 0.075 * h, 0.14 * h, "redondeada", 0.0, grueso)

    def _ventanas_estaticas(self, p, w, h, color):
        for xf, bf, af, hf, encendida in VENTANAS:
            x, base = xf * w, bf * h
            camino = _ojival(x, base, af * w, hf * h)
            if encendida:
                p.setPen(Qt.NoPen)
                p.setBrush(con_alfa(QColor(CALIDA), 60))
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(mezclar(QColor(color), QColor("#000000"), 0.5)))
            p.drawPath(camino)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(color), max(1.0, 0.003 * h)))
            p.drawLine(QPointF(x, base - hf * h * 0.85), QPointF(x, base))
            p.setPen(Qt.NoPen)

    def pintar_estatico(self, p, w, h):
        r = random.Random(31)
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        # cielo nocturno
        cielo = QLinearGradient(0, 0, 0, h)
        cielo.setColorAt(0.00, QColor("#06040A"))
        cielo.setColorAt(0.50, QColor("#1A1024"))
        cielo.setColorAt(0.72, QColor("#2E1E36"))
        cielo.setColorAt(1.00, QColor("#2E1E36"))
        p.fillRect(QRectF(0, 0, w, h), cielo)
        self._estrellas(p, w, h, r)
        self._luna(p, w, h, r)
        self._nubes(p, w, h, r)
        # capa lejana (65 % de niebla): colinas y pinos
        lejano = mezclar(QColor(LEJANO), QColor(NIEBLA), MEZCLA_LEJOS)
        self._colina(p, w, h, lambda x: self._cresta_lejana(x, w, h), lejano)
        self._pinos(p, w, h, r, lejano)
        self._banda_niebla(p, w, 0.60 * h, 0.16 * h, NIEBLA, 100)
        # capa media (35 % de niebla): colina y catedral
        medio = mezclar(QColor(CATEDRAL), QColor(NIEBLA), MEZCLA_MEDIO)
        self._colina(p, w, h, lambda x: self._cresta_media(x, w, h), medio)
        piezas, trazos = self._catedral(w, h)
        _pintar_piezas(p, piezas, medio, grueso=max(1.0, h * 0.0013))
        p.setBrush(Qt.NoBrush)
        for camino, grosor in trazos:
            p.setPen(QPen(medio, grosor, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(camino)
        self._ventanas_estaticas(p, w, h, medio)
        self._rosetón(p, 0.5 * w, 0.56 * h, 0.08 * h)
        self._banda_niebla(p, w, 0.74 * h, 0.12 * h, NIEBLA, 100)
        # capa cercana (sin niebla): cementerio, árboles, lápidas y verja
        p.setPen(Qt.NoPen)
        self._piedras_y_arboles(p, w, h, r)
        self._verja(p, w, h)
        # grano y viñeta
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        puntos = QPolygonF([QPointF(r.random() * w, r.random() * h) for _ in range(6000)])
        p.drawPoints(puntos)
        viñeta = QRadialGradient(QPointF(w / 2.0, h / 2.0), max(w, h) * 0.60)
        viñeta.setColorAt(0.00, QColor(0, 0, 0, 0))
        viñeta.setColorAt(0.45, QColor(0, 0, 0, 0))
        viñeta.setColorAt(1.00, QColor(0, 0, 0, 160))
        p.setPen(Qt.NoPen)
        p.fillRect(QRectF(0, 0, w, h), viñeta)
        p.restore()

    # ------------------------------------------------------------ sprites pregenerados

    def _pm_niebla(self, w, alto, color, semilla):
        """Franja de niebla de ancho 2*w y periódica en w (se desliza sin cortes)."""
        pm = QPixmap(2 * w, alto)
        pm.fill(Qt.transparent)
        rnd = random.Random(semilla)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing, True)
        q.setPen(Qt.NoPen)
        c = QColor(color)
        g = QRadialGradient(QPointF(0, 0), 1.0)
        g.setColorAt(0.0, con_alfa(c, 255))
        g.setColorAt(0.55, con_alfa(c, 110))
        g.setColorAt(1.0, con_alfa(c, 0))
        for _ in range(14):
            cx = rnd.uniform(0, w)
            cy = alto * rnd.uniform(0.40, 0.60)
            rx = w * rnd.uniform(0.08, 0.17)
            ry = alto * rnd.uniform(0.35, 0.60)
            for k in (-1, 0, 1, 2):
                q.save()
                q.translate(cx + k * w, cy)
                q.scale(rx, ry)
                q.setBrush(QBrush(g))
                q.drawEllipse(QPointF(0, 0), 1.0, 1.0)
                q.restore()
        q.end()
        q = QPainter(pm)
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        v = QLinearGradient(0, 0, 0, alto)
        v.setColorAt(0.0, QColor(0, 0, 0, 0))
        v.setColorAt(0.5, QColor(0, 0, 0, 255))
        v.setColorAt(1.0, QColor(0, 0, 0, 0))
        q.fillRect(QRectF(0, 0, 2 * w, alto), v)
        q.end()
        return pm

    def _pm_murcielago(self, cuadro):
        """Murciélago de 120x60 con alas de curvas y festones; `cuadro` 0 (arriba), 1 (medio), 2 (abajo)."""
        pm = QPixmap(120, 60)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing, True)
        q.setPen(Qt.NoPen)
        q.setBrush(con_alfa(QColor(CATEDRAL), 240))
        punta_y = (-26, -4, 16)[cuadro]
        for lado in (-1, 1):
            ala = QPainterPath(QPointF(60, 36))
            ala.quadTo(QPointF(60 + lado * 22, 20 + punta_y * 0.3), QPointF(60 + lado * 56, 36 + punta_y))
            ala.quadTo(QPointF(60 + lado * 50, 42 + punta_y * 0.2), QPointF(60 + lado * 42, 48))
            ala.quadTo(QPointF(60 + lado * 32, 40), QPointF(60 + lado * 24, 52))
            ala.quadTo(QPointF(60 + lado * 14, 46), QPointF(60, 48))
            ala.closeSubpath()
            q.drawPath(ala)
        q.drawEllipse(QPointF(60, 34), 4.5, 8.0)
        q.drawEllipse(QPointF(60, 24), 4.5, 4.5)
        q.end()
        return pm

    def _preparar_sprites(self, w, h):
        if not self._pm_murcielagos:
            self._pm_murcielagos = [self._pm_murcielago(i) for i in range(3)]
        if self._clave_sprites == (w, h):
            return
        self._clave_sprites = (w, h)
        alto = max(8, int(0.16 * h))
        capas = []
        for y, vel, alfa, color, semilla in ((0.70, 0.004, 40, "#6B5A7F", 101),
                                             (0.78, 0.007, 55, "#5E4D70", 102),
                                             (0.86, 0.011, 70, "#4F4062", 103)):
            capas.append((self._pm_niebla(w, alto, color, semilla), y * h, vel, alfa))
        self._capas_niebla = capas

    # ------------------------------------------------------------ animado

    def _velas(self, p, w, h, t):
        """Seis ventanas con vela: el vidrio titila y la llama parpadea."""
        p.setPen(Qt.NoPen)
        k = 0
        for xf, bf, af, hf, encendida in VENTANAS:
            if not encendida:
                continue
            fase = 1.3 * k
            k += 1
            x, base = xf * w, bf * h
            aw, ah = af * w, hf * h
            flick = 0.55 + 0.25 * math.sin(t * 2.1 + fase) + 0.12 * math.sin(t * 5.7 + fase * 1.7) \
                + 0.08 * math.sin(t * 12.9 + fase * 0.4)
            flick = min(1.0, max(0.0, flick))
            p.setBrush(con_alfa(QColor(CALIDA), 40 + 120 * flick))
            p.drawPath(_ojival(x, base, aw, ah))
            p.save()
            p.setCompositionMode(QPainter.CompositionMode_Plus)
            self.brillo(p, x, base - ah * 0.45, ah * 0.75, CALIDA, 25 + 70 * flick)
            p.restore()
            lam = 1 + 0.12 * math.sin(t * 11 + fase) + 0.06 * math.sin(t * 23 + fase * 2.0)
            yb = base - ah * 0.10
            alto_llama = ah * 0.20 * lam
            ancho_llama = max(2.0, aw * 0.22)
            llama = QPainterPath(QPointF(x, yb - alto_llama))
            llama.cubicTo(QPointF(x + ancho_llama, yb - alto_llama * 0.45), QPointF(x + ancho_llama * 0.8, yb),
                          QPointF(x, yb))
            llama.cubicTo(QPointF(x - ancho_llama * 0.8, yb), QPointF(x - ancho_llama, yb - alto_llama * 0.45),
                          QPointF(x, yb - alto_llama))
            p.setBrush(con_alfa(QColor("#FFC36B"), 235))
            p.drawPath(llama)
            p.setBrush(con_alfa(QColor("#FFF4D0"), 230))
            p.drawEllipse(QPointF(x, yb - alto_llama * 0.35), ancho_llama * 0.35, alto_llama * 0.35)

    def _cuervo(self, p, x, y, s, t):
        """Cuervo posado en (x, y), con la cabeza que gira (en flip horizontal) cada PERIODO_CABEZA segundos."""
        k = int(t // PERIODO_CABEZA)
        fase = t - k * PERIODO_CABEZA
        nuevo = 1 if k % 2 == 0 else -1
        anterior = -nuevo
        if fase < 0.8 and anterior != nuevo:
            f = fase / 0.8
            f = f * f * (3 - 2 * f)
            sentido = anterior * math.cos(math.pi * f)   # de un lado a otro, con la cabeza pasando por el centro
        else:
            sentido = float(nuevo)
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(NOCHE))
        p.drawEllipse(QPointF(x, y - 1.25 * s), 0.95 * s, 1.35 * s)
        cola = QPainterPath(QPointF(x - 0.5 * s, y - 0.6 * s))
        cola.lineTo(QPointF(x - 1.8 * s, y + 0.25 * s))
        cola.lineTo(QPointF(x - 0.7 * s, y + 0.2 * s))
        cola.closeSubpath()
        p.drawPath(cola)
        kx = sentido if abs(sentido) > 0.05 else (0.05 if sentido >= 0 else -0.05)
        p.translate(x + 0.35 * s, y - 2.6 * s)
        p.scale(kx, 1.0)
        p.drawEllipse(QPointF(0, 0), 0.75 * s, 0.70 * s)
        p.drawPolygon(QPolygonF([QPointF(0.45 * s, -0.20 * s), QPointF(1.55 * s, 0.02 * s),
                                 QPointF(0.45 * s, 0.26 * s)]))
        p.setBrush(con_alfa(QColor("#C9B8E8"), 200))
        p.drawEllipse(QPointF(0.20 * s, -0.22 * s), 0.10 * s, 0.10 * s)
        p.restore()

    def _murcielagos(self, p, w, h, t):
        for altura, x0, vel, escala, fase, frec in self.murcielagos:
            xf = (x0 + vel * t) % 1.2 - 0.1
            y = (altura + 0.015 * math.sin(0.3 * t + fase)) * h
            ancho = escala * h * 4.6
            cuadro = int((t * frec) % 3)
            p.drawPixmap(QRectF(xf * w - ancho / 2, y - ancho * 0.25, ancho, ancho * 0.5),
                         self._pm_murcielagos[cuadro], QRectF(0, 0, 120, 60))

    def _ascuas(self, p, w, h, t):
        p.save()
        p.setPen(Qt.NoPen)
        for x0, y0, spd, ph, tam, fase in self.ascuas:
            f = (t * spd + ph) % 1.0
            x = (x0 + 0.012 * math.sin(t * 0.9 + fase)) * w
            y = (y0 - f * 0.42) * h
            titila = 0.4 + 0.6 * math.sin(t * 3.0 + fase) ** 2
            p.setBrush(con_alfa(QColor("#FF5A3C"), 170 * titila * (1 - f)))
            rad = tam * h / 900.0
            p.drawEllipse(QPointF(x, y), rad, rad)
        p.restore()

    def pintar_animado(self, p, w, h, t):
        self._preparar_sprites(w, h)
        self._velas(p, w, h, t)
        # el rosetón brilla con la música
        p.save()
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        self.brillo(p, 0.5 * w, 0.56 * h, 0.08 * h * 2.8, self.acento(),
                    40 + 140 * min(1.0, max(0.0, self.energia())))
        p.restore()
        self._murcielagos(p, w, h, t)
        self._cuervo(p, 0.66 * w, 0.78 * h, 0.028 * h, t)
        # niebla en tres capas que se desplazan a distinta velocidad
        for pm, y, vel, alfa in self._capas_niebla:
            desplazamiento = (t * vel * w) % w
            p.setOpacity(alfa / 255.0)
            p.drawPixmap(QRectF(0, y, w, pm.height()), pm, QRectF(desplazamiento, 0, w, pm.height()))
        p.setOpacity(1.0)
        self._ascuas(p, w, h, t)
        # ondas de la música en la base de la catedral
        self.ondas(p, base_y=0.80 * h, ancho=w, alto_max=0.09 * h, color=self.acento(), reflejo=False)
