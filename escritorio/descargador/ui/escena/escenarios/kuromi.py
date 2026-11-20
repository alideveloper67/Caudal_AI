# -*- coding: utf-8 -*-
"""Escenario Kuromi: un castillito gótico-kawaii en una colina bajo una noche morada y mágica.

Solo estética (negro, morado, rosa, calaveritas, murciélagos, lunas, gótico-tierno). No se dibuja ninguna
figura ni cara de personajes con marca: los únicos rostros son calaveritas genéricas."""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)

from .base import EscenarioBase, con_alfa, mezclar

BRUMA = "#4A2A6B"          # color de la niebla atmosférica (lejos = 60 %, medio = 30 %, cerca = 0 %)
ROSA = "#FF77B7"
ROSA_HALO = "#FF9ED2"
ROSA_PALIDO = "#FFD1EA"
LUZ_NUBE = "#B78ACF"
SOMBRA_NUBE = "#2A1640"
PIEDRA = "#2A1A3A"
NEGRO = "#0A0512"
TINTA = "#120A1F"
TAU = 2 * math.pi
HORIZONTE = 0.62           # fracción de h donde termina el cielo
BASE_CASTILLO = 0.60       # fracción de h donde se asientan las torres

# Torres: (cx en w, ancho en w, alto en h, techo en h, ventanas [(tipo, altura desde la base / alto)])
TORRES = (
    (0.345, 0.034, 0.12, 0.085, (("redonda", 0.55),)),
    (0.385, 0.052, 0.20, 0.135, (("arco", 0.35), ("redonda", 0.76))),
    (0.465, 0.074, 0.30, 0.185, (("arco", 0.30), ("arco", 0.52), ("redonda", 0.80))),
    (0.545, 0.058, 0.22, 0.145, (("arco", 0.34), ("redonda", 0.74))),
    (0.585, 0.034, 0.13, 0.090, (("redonda", 0.55),)),
)
MURO = (0.33, 0.62, 0.075)  # x0 y x1 en w, alto en h


# ---------------------------------------------------------------- funciones auxiliares

def _lado(v):
    """Tamaño de sprite cuantizado a múltiplos de 4 (para que la caché no crezca sin límite)."""
    return max(8, int(round(v / 4.0)) * 4)


def _ajustar(color, d):
    return QColor(max(0, min(255, color.red() + d)), max(0, min(255, color.green() + d)),
                  max(0, min(255, color.blue() + d)))


def _bruma(color, f):
    """Mezcla un color con la bruma #4A2A6B (f = 0..1): perspectiva atmosférica."""
    return mezclar(QColor(color), QColor(BRUMA), f)


def _crestas(r, y0, y1, amp, iteraciones=8):
    """Cresta por desplazamiento de punto medio: parte de 2 puntos e inserta puntos medios con
    y += uniform(-amp, amp); amp *= 0.55 en cada vuelta. Devuelve (x, y) en fracciones de w y h."""
    pts = [(0.0, y0), (1.0, y1)]
    for _ in range(iteraciones):
        nuevos = []
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            nuevos.append((xa, ya))
            nuevos.append(((xa + xb) / 2, (ya + yb) / 2 + r.uniform(-amp, amp)))
        nuevos.append(pts[-1])
        pts = nuevos
        amp *= 0.55
    return pts


def _ruta_suave(pts):
    """Camino que pasa por los puntos con cuadráticas entre puntos medios (picos suaves)."""
    camino = QPainterPath(pts[0])
    for i in range(1, len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        camino.quadTo(a, QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2))
    camino.lineTo(pts[-1])
    return camino


def _puntos_nube(r, cx, cy, ancho, alto, n):
    """Círculos de una nube: más altos en el centro, con bultos de distinto tamaño."""
    out = []
    for _ in range(n):
        u = r.random()
        cupula = math.sqrt(max(0.0, 1 - (2 * u - 1) ** 2))
        x = cx + (u - 0.5) * ancho
        y = cy - alto * cupula * r.uniform(0.3, 1.0) + r.uniform(-0.04, 0.02) * alto
        rad = alto * r.uniform(0.28, 0.5) * (0.6 + 0.4 * cupula)
        out.append((x, y, rad))
    return out


def _estrella4(cx, cy, rad):
    """Estrella de 4 puntas: cuatro curvas cóncavas (como un destello)."""
    k = rad * 0.16
    camino = QPainterPath(QPointF(cx, cy - rad))
    camino.quadTo(QPointF(cx + k, cy - k), QPointF(cx + rad, cy))
    camino.quadTo(QPointF(cx + k, cy + k), QPointF(cx, cy + rad))
    camino.quadTo(QPointF(cx - k, cy + k), QPointF(cx - rad, cy))
    camino.quadTo(QPointF(cx - k, cy - k), QPointF(cx, cy - rad))
    camino.closeSubpath()
    return camino


def _corazon(cx, cy, s):
    camino = QPainterPath(QPointF(cx, cy + s * 0.5))
    camino.cubicTo(QPointF(cx - s * 1.1, cy - s * 0.1), QPointF(cx - s * 0.5, cy - s * 0.9),
                   QPointF(cx, cy - s * 0.35))
    camino.cubicTo(QPointF(cx + s * 0.5, cy - s * 0.9), QPointF(cx + s * 1.1, cy - s * 0.1),
                   QPointF(cx, cy + s * 0.5))
    camino.closeSubpath()
    return camino


def _calavera(p, cx, cy, rad, cabeza, ojos):
    """Calaverita kawaii: cráneo redondo, mandíbula, dos ojos grandes y dientitos."""
    p.save()
    p.setPen(Qt.NoPen)
    craneo = QPainterPath()
    craneo.addEllipse(QPointF(cx, cy), rad, rad * 0.92)
    mandibula = QPainterPath()
    mandibula.addRoundedRect(QRectF(cx - 0.5 * rad, cy + 0.35 * rad, rad, 0.6 * rad), 0.25 * rad, 0.25 * rad)
    p.fillPath(craneo, QBrush(cabeza))
    p.fillPath(mandibula, QBrush(cabeza))
    cuencas = QPainterPath()
    cuencas.addEllipse(QPointF(cx - 0.38 * rad, cy - 0.05 * rad), 0.27 * rad, 0.32 * rad)
    cuencas.addEllipse(QPointF(cx + 0.38 * rad, cy - 0.05 * rad), 0.27 * rad, 0.32 * rad)
    p.fillPath(cuencas, QBrush(ojos))
    p.setPen(QPen(ojos, max(1.0, 0.1 * rad), Qt.SolidLine, Qt.RoundCap))
    for dx in (-0.25, 0.0, 0.25):
        p.drawLine(QPointF(cx + dx * rad, cy + 0.5 * rad), QPointF(cx + dx * rad, cy + 0.92 * rad))
    p.restore()


def _forma_ventana(x, y, aw, ah, arco):
    """Ventana: (x centro, y arriba). Arco gótico apuntado o redonda (ojo de buey)."""
    camino = QPainterPath()
    if arco:
        izq, der = x - aw / 2, x + aw / 2
        camino.moveTo(QPointF(izq, y + ah))
        camino.lineTo(QPointF(izq, y + aw / 2))
        camino.arcTo(QRectF(izq, y, aw, aw), 180, -180)
        camino.lineTo(QPointF(der, y + ah))
        camino.closeSubpath()
    else:
        camino.addEllipse(QPointF(x, y + aw / 2), aw / 2, aw / 2)
    return camino


def _ventanas(w, h):
    """Todas las ventanas iluminables del castillo: (x centro, y arriba, ancho, alto, arco)."""
    out = []
    for cx, tw, th, _techo, vent in TORRES:
        ancho = tw * w
        base = BASE_CASTILLO * h
        alto = th * h
        for tipo, f in vent:
            y_centro = base - f * alto
            if tipo == "arco":
                aw = 0.26 * ancho
                ah = aw * 2.1
                out.append((cx * w, y_centro - ah / 2, aw, ah, True))
            else:
                aw = 0.24 * ancho
                out.append((cx * w, y_centro - aw / 2, aw, aw, False))
    return out


def _piedras(p, rect, filas, columnas, r, base):
    """Pared de piedras: rectángulos redondeados con juntas oscuras y un tono distinto por piedra."""
    ancho_f = rect.width() / columnas
    alto_f = rect.height() / filas
    p.save()
    p.setClipRect(rect, Qt.IntersectClip)
    p.setPen(QPen(con_alfa(TINTA, 200), max(1.0, alto_f * 0.08)))
    for i in range(filas):
        desp = ancho_f / 2 if i % 2 else 0.0
        y = rect.top() + i * alto_f
        for j in range(-1, columnas + 1):
            x = rect.left() + j * ancho_f + desp
            p.setBrush(QBrush(_ajustar(QColor(base), r.randint(-7, 7))))
            p.drawRoundedRect(QRectF(x + 1, y + 1, ancho_f - 2, alto_f - 2), alto_f * 0.28, alto_f * 0.28)
    p.restore()


def _luz_lunar(p, rect):
    """Luz de luna: el lado derecho (hacia la luna) se aclara con morado-lila."""
    g = QLinearGradient(rect.left(), 0, rect.right(), 0)
    g.setColorAt(0, con_alfa(NEGRO, 90))
    g.setColorAt(0.5, con_alfa(NEGRO, 0))
    g.setColorAt(0.85, con_alfa(LUZ_NUBE, 40))
    g.setColorAt(1, con_alfa(LUZ_NUBE, 110))
    p.fillRect(rect, QBrush(g))


def _tejado(p, cx, yb, ancho, techo):
    """Tejado cónico con la punta que se dobla (curva). Devuelve la punta."""
    izq, der = cx - ancho * 0.56, cx + ancho * 0.56
    punta = QPointF(cx + ancho * 0.20, yb - techo)
    camino = QPainterPath(QPointF(izq, yb))
    camino.quadTo(QPointF(cx - ancho * 0.12, yb - techo * 0.62), punta)                       # lado izq. cóncavo
    camino.quadTo(QPointF(cx + ancho * 0.62, yb - techo * 1.06), QPointF(cx + ancho * 0.40, yb - techo * 0.80))  # punta que se dobla
    camino.quadTo(QPointF(cx + ancho * 0.30, yb - techo * 0.42), QPointF(der, yb))              # lado der.
    camino.closeSubpath()
    g = QLinearGradient(izq, yb - techo, der, yb)
    g.setColorAt(0, QColor("#4A2A6E"))
    g.setColorAt(0.6, QColor("#2E1A4E"))
    g.setColorAt(1, QColor("#5E3C86"))
    p.save()
    p.setPen(Qt.NoPen)
    p.fillPath(camino, QBrush(g))
    p.setClipPath(camino)
    p.setPen(QPen(con_alfa(TINTA, 110), max(1.0, techo * 0.02)))                              # tejas en arco
    for k in (0.3, 0.55, 0.78):
        p.drawArc(QRectF(cx - ancho * 0.6, yb - techo * k - ancho * 0.15, ancho * 1.2, ancho * 0.3), 200 * 16, 140 * 16)
    p.setClipping(False)
    p.setPen(QPen(con_alfa(ROSA_HALO, 110), max(1.0, ancho * 0.02)))
    p.setBrush(Qt.NoBrush)
    p.drawPath(camino)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(ROSA)))
    p.drawEllipse(punta, ancho * 0.03, ancho * 0.03)
    p.restore()
    return punta


def _banderin(p, x, y, alto):
    """Poste con banderín rosa y una calaverita dentro."""
    p.save()
    p.setPen(QPen(QColor("#1A0F26"), max(1.5, alto * 0.05)))
    p.drawLine(QPointF(x, y), QPointF(x, y - alto))
    fw, fh = alto * 0.6, alto * 0.45
    px, py = x, y - alto
    bandera = QPainterPath(QPointF(px, py))
    bandera.quadTo(QPointF(px + fw * 0.5, py - fh * 0.18), QPointF(px + fw, py + fh * 0.08))
    bandera.lineTo(QPointF(px + fw * 0.78, py + fh * 0.5))
    bandera.lineTo(QPointF(px + fw, py + fh * 0.92))
    bandera.quadTo(QPointF(px + fw * 0.5, py + fh * 1.08), QPointF(px, py + fh))
    bandera.closeSubpath()
    p.setPen(Qt.NoPen)
    p.fillPath(bandera, QBrush(QColor(ROSA)))
    _calavera(p, px + fw * 0.42, py + fh * 0.5, max(2.0, fh * 0.2), QColor("#FFF0FA"), QColor(SOMBRA_NUBE))
    p.restore()


def _puente_y_rio_dibujo(p, w, h):
    """Río oscuro con brillo rosa y un puente de piedra en arco."""
    p.save()
    p.setPen(Qt.NoPen)
    rio = QPainterPath()
    rio.addEllipse(QPointF(0.31 * w, 0.745 * h), 0.17 * w, 0.016 * h)
    p.fillPath(rio, QBrush(QColor("#2B1650")))
    reflejo = QPainterPath()
    reflejo.addEllipse(QPointF(0.31 * w, 0.748 * h), 0.10 * w, 0.004 * h)
    p.fillPath(reflejo, QBrush(con_alfa(ROSA_HALO, 120)))
    hueco = QPainterPath(QPointF(0.245 * w, 0.752 * h))         # ojo del arco: sombra bajo el tablero
    hueco.quadTo(QPointF(0.31 * w, 0.668 * h), QPointF(0.375 * w, 0.752 * h))
    hueco.closeSubpath()
    p.fillPath(hueco, QBrush(con_alfa(TINTA, 210)))
    tablero = QPainterPath(QPointF(0.22 * w, 0.736 * h))
    tablero.quadTo(QPointF(0.31 * w, 0.652 * h), QPointF(0.40 * w, 0.736 * h))
    tablero.lineTo(QPointF(0.40 * w, 0.752 * h))
    tablero.quadTo(QPointF(0.31 * w, 0.668 * h), QPointF(0.22 * w, 0.752 * h))
    tablero.closeSubpath()
    p.fillPath(tablero, QBrush(QColor("#3F2D58")))
    p.setPen(QPen(con_alfa(TINTA, 170), 1.0))
    for fx in (0.25, 0.28, 0.34, 0.37):
        p.drawLine(QPointF(fx * w, 0.73 * h), QPointF(fx * w + 0.004 * w, 0.745 * h))
    p.restore()


# ---------------------------------------------------------------- el escenario

class EscenarioKuromi(EscenarioBase):
    NOMBRE = "Kuromi"
    ACENTO = "#FF77B7"
    SEMILLA = 13

    def preparar(self):
        r = self.rnd
        # Estrellas que titilan: las rellena pintar_estatico (ver _brillantes ahí).
        self._brillantes = []
        # Calaveritas y corazones que flotan: (x, y, tamaño, fase, amplitud, giro en grados/s, tipo).
        # 9 calaveritas al 55 % del tamaño y 7 corazones; ninguno cae dentro del rectángulo del castillo.
        self._flotan = []
        for i in range(16):
            tipo = "calavera" if i < 9 else "corazon"
            while True:
                fx, fy = r.random(), r.uniform(0.06, 0.9)
                if not (0.27 <= fx <= 0.70 and fy <= 0.68):
                    break
            tam = r.uniform(0.018, 0.03) * (0.55 if tipo == "calavera" else 1.0)
            self._flotan.append((fx, fy, tam, r.uniform(0, TAU), r.uniform(0.004, 0.012), r.uniform(-3, 3), tipo))
        # Murciélagos tiernos: (fase, periodo en s, altura base, amplitud de la curva, tamaño en fracción de h).
        # El de tamaño 0.048 es el doble de los pequeños, misma silueta.
        self._murcielagos = [(r.random(), r.uniform(14, 22), r.uniform(0.12, 0.3), r.uniform(0.02, 0.06), tam)
                             for tam in (0.024, 0.026, 0.048)]
        self._capa_cementerio = None
        self._spr = {}
        self._alto_spr = None
        self._niebla = None
        self._niebla_clave = None

    # ------------------------------------------------------------ lo que no se mueve

    def pintar_estatico(self, p, w, h):
        r = random.Random(79)
        self._brillantes = []
        p.save()
        self._cielo(p, w, h)
        self._estrellas(p, w, h, r)
        self._luna(p, w, h)
        self._nubes(p, w, h, r, ((0.18, 0.31, 0.34, 0.07, 0.25), (0.55, 0.22, 0.30, 0.05, 0.20),
                                 (0.36, 0.42, 0.42, 0.06, 0.30)))
        self._montana(p, w, h, r, 0.47, 0.50, 0.09, 0.60, "#2A1650", 0.72)
        self._nubes(p, w, h, r, ((0.22, 0.555, 0.50, 0.05, 0.60), (0.84, 0.575, 0.40, 0.045, 0.60)))
        self._montana(p, w, h, r, 0.56, 0.60, 0.06, 0.30, "#3A1E5C", 0.80)
        self._bosque(p, w, h, r, 0.66, 0.30, (0.03, 0.10, 0.17, 0.74, 0.82, 0.90, 0.97), (0.14, 0.22))
        self._colina(p, w, h, r)
        _puente_y_rio_dibujo(p, w, h)
        self._castillo(p, w, h, r)
        self._suelo(p, w, h)
        self._bosque(p, w, h, r, 0.86, 0.0, (0.015, 0.11, 0.90, 0.985), (0.36, 0.50))
        self._capa_cementerio = self._capa_lapidas(w, h, r)
        self._granulado(p, w, h, r)
        self._vineta(p, w, h)
        p.restore()

    def _cielo(self, p, w, h):
        g = QLinearGradient(0, 0, 0, HORIZONTE * h)
        g.setColorAt(0, QColor("#120A1F"))
        g.setColorAt(0.5, QColor("#2E1650"))
        g.setColorAt(1.0, QColor("#5A2A7A"))
        p.fillRect(QRectF(0, 0, w, h), QBrush(g))   # debajo del horizonte el degradado repite #5A2A7A

    def _estrellas(self, p, w, h, r):
        p.setPen(Qt.NoPen)
        for _ in range(300):
            fx = r.random()
            fy = (r.random() ** 1.5) * 0.58
            u = r.random()
            rad = (0.0007 + 0.0024 * u * u) * h
            color = "#FFE3F2" if r.random() < 0.35 else "#FFFFFF"
            p.setBrush(QBrush(con_alfa(color, r.randint(110, 255))))
            p.drawEllipse(QPointF(fx * w, fy * h), rad, rad)
            if rad > 0.0018 * h and len(self._brillantes) < 48 and r.random() < 0.5:
                self._brillantes.append((fx, fy, rad * 9 / h, r.uniform(0, TAU), r.uniform(0.8, 2.2)))
        for _ in range(16):
            x = r.random() * w
            y = r.random() * 0.5 * h
            rad = r.uniform(0.010, 0.016) * h
            self.brillo(p, x, y, rad * 4.5, "#FFE3F2", alfa=75)
            p.setPen(Qt.NoPen)
            p.fillPath(_estrella4(x, y, rad), QBrush(con_alfa("#FFF0FA", 235)))

    def _luna(self, p, w, h):
        mx, my, mr = 0.80 * w, 0.27 * h, 0.19 * h
        self.brillo(p, mx, my, 0.52 * h, ROSA_HALO, alfa=90)
        luna = QPainterPath()
        luna.addEllipse(QPointF(mx, my), mr, mr)
        corte = QPainterPath()
        corte.addEllipse(QPointF(mx + 0.42 * mr, my - 0.18 * mr), mr * 0.92, mr * 0.92)
        creciente = luna.subtracted(corte)
        p.save()
        p.setPen(Qt.NoPen)
        p.fillPath(creciente, QBrush(QColor(ROSA_PALIDO)))
        p.setClipPath(creciente)
        for dx, dy, rr in ((-0.50, 0.25, 0.16), (-0.66, -0.06, 0.11), (-0.20, 0.62, 0.10), (-0.78, 0.36, 0.08)):
            c = QPointF(mx + dx * mr, my + dy * mr)
            g = QRadialGradient(c, rr * mr)
            g.setColorAt(0, con_alfa("#E59BC6", 120))
            g.setColorAt(0.7, con_alfa("#E59BC6", 60))
            g.setColorAt(1, con_alfa("#E59BC6", 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(c, rr * mr, rr * mr)
        p.restore()

    def _nubes(self, p, w, h, r, lista):
        """Nubes de muchos círculos en dos pasadas: sombra y, arriba-derecha, borde iluminado por la luna."""
        for cx, cy, ancho, alto, bruma_f in lista:
            puntos = _puntos_nube(r, cx * w, cy * h, ancho * w, alto * h, r.randint(25, 45))
            camino = QPainterPath()
            camino.setFillRule(Qt.WindingFill)
            for x, y, rad in puntos:
                camino.addEllipse(QPointF(x, y), rad, rad)
            sombra = _bruma(SOMBRA_NUBE, bruma_f)
            luz = _bruma(LUZ_NUBE, bruma_f)
            p.save()
            p.setPen(Qt.NoPen)
            p.fillPath(camino, QBrush(sombra))                       # pasada 1: sombra
            p.setClipPath(camino)                                    # pasada 2: borde iluminado
            p.fillPath(camino, QBrush(con_alfa(luz, 140)))
            desfase = 0.012 * h
            p.fillPath(camino.translated(-desfase, desfase), QBrush(sombra))
            p.restore()

    def _montana(self, p, w, h, r, y0, y1, amp, f, color, fondo):
        pts = [QPointF(x * w, y * h) for x, y in _crestas(r, y0, y1, amp)]
        camino = _ruta_suave(pts)
        camino.lineTo(QPointF(w, fondo * h))
        camino.lineTo(QPointF(0, fondo * h))
        camino.closeSubpath()
        c = _bruma(color, f)
        g = QLinearGradient(0, y0 * h, 0, fondo * h)
        g.setColorAt(0, _ajustar(c, 14))
        g.setColorAt(1, c)
        p.fillPath(camino, QBrush(g))

    def _colina(self, p, w, h, r):
        """Colina con la cresta redonda donde se asienta el castillo; borde iluminado por la luna."""
        cima = QPainterPath(QPointF(-0.02 * w, 0.95 * h))
        cima.cubicTo(QPointF(0.18 * w, 0.70 * h), QPointF(0.34 * w, 0.575 * h), QPointF(0.46 * w, 0.56 * h))
        cima.cubicTo(QPointF(0.58 * w, 0.55 * h), QPointF(0.74 * w, 0.66 * h), QPointF(1.02 * w, 0.78 * h))
        colina = QPainterPath(cima)
        colina.lineTo(QPointF(1.02 * w, h))
        colina.lineTo(QPointF(-0.02 * w, h))
        colina.closeSubpath()
        g = QLinearGradient(0, 0.55 * h, 0, h)
        g.setColorAt(0, QColor("#4A2A72"))
        g.setColorAt(0.5, QColor("#2A1648"))
        g.setColorAt(1, QColor("#14091F"))
        p.save()
        p.fillPath(colina, QBrush(g))
        p.setClipPath(colina)
        rg = QRadialGradient(QPointF(0.46 * w, 0.66 * h), 0.42 * w)     # relieve: más claro bajo el castillo
        rg.setColorAt(0, con_alfa("#5A3A7A", 230))
        rg.setColorAt(1, con_alfa("#2A1840", 0))
        p.fillPath(colina, QBrush(rg))
        p.setPen(QPen(con_alfa("#1A0E2A", 170), 1.2, Qt.SolidLine, Qt.RoundCap))
        for _ in range(1500):                                           # hierba morada en la mitad inferior
            x = r.uniform(0, w)
            y = r.uniform(0.75 * h, h)
            largo = r.uniform(0.006, 0.012) * h
            p.drawLine(QPointF(x, y), QPointF(x + r.uniform(-0.4, 0.4) * largo, y - largo))
        p.setClipping(False)
        p.setPen(QPen(con_alfa(LUZ_NUBE, 60), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawPath(cima)
        p.restore()

    def _bosque(self, p, w, h, r, base_f, fog_f, xs, altos):
        """Árboles curvos. fog_f > 0 los aleja (bosque lejano); 0 los pone en primer plano."""
        tronco, rama, raya = _bruma("#1E1030", fog_f), _bruma("#3A2456", fog_f), _bruma("#5A3A80", fog_f)
        for fx in xs:
            self._arbol(p, fx * w, base_f * h, r.uniform(*altos) * h, 0.02 * h, r, tronco, rama, raya)

    def _arbol(self, p, x, base, alto, g, r, tronco, rama, raya):
        """Árbol tipo Tim Burton: tronco con espiral y ramas que se rizan con cubicTo."""
        bend = r.uniform(-0.1, 0.1) * alto
        tope = QPointF(x + bend, base - alto)
        p.save()
        p.setPen(Qt.NoPen)
        cuerpo = QPainterPath(QPointF(x - g, base))
        cuerpo.cubicTo(QPointF(x - g * 0.9, base - alto * 0.4), QPointF(x + bend - g * 0.6, base - alto * 0.7),
                       QPointF(tope.x() - g * 0.25, tope.y()))
        cuerpo.lineTo(QPointF(tope.x() + g * 0.25, tope.y()))
        cuerpo.cubicTo(QPointF(x + bend + g * 0.6, base - alto * 0.7), QPointF(x + g * 0.9, base - alto * 0.4),
                       QPointF(x + g, base))
        cuerpo.closeSubpath()
        p.fillPath(cuerpo, QBrush(QColor(tronco)))
        espiral = QPainterPath()
        for k in range(40):
            tt = k / 39
            px = x + bend * tt * tt + g * 0.85 * (1 - 0.35 * tt) * math.cos(tt * TAU * 2.6)
            py = base - alto * 0.96 * tt
            if k == 0:
                espiral.moveTo(QPointF(px, py))
            else:
                espiral.lineTo(QPointF(px, py))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(raya), max(1.0, g * 0.25), Qt.SolidLine, Qt.RoundCap))
        p.drawPath(espiral)
        ramas = r.randint(4, 6)
        for k in range(ramas):
            ang = -math.pi / 2 + (k - (ramas - 1) / 2) * r.uniform(0.35, 0.6)
            self._rama(p, tope.x(), tope.y() + alto * 0.02, ang, alto * r.uniform(0.25, 0.4), g * 0.55, 2, r, rama)
        p.restore()

    def _rama(self, p, x, y, ang, largo, grosor, prof, r, color):
        """Rama que termina en un rizo (cubicTo) y se bifurca mientras le queda profundidad."""
        sent = 1 if r.random() < 0.5 else -1
        ex, ey = x + math.cos(ang) * largo, y + math.sin(ang) * largo
        camino = QPainterPath(QPointF(x, y))
        camino.cubicTo(QPointF(x + math.cos(ang + 0.5 * sent) * largo * 0.45,
                               y + math.sin(ang + 0.5 * sent) * largo * 0.45),
                       QPointF(ex - math.cos(ang - 0.3 * sent) * largo * 0.25,
                               ey - math.sin(ang - 0.3 * sent) * largo * 0.25),
                       QPointF(ex, ey))
        rz = largo * 0.18
        kx, ky = ex + math.cos(ang + sent * 1.1) * rz, ey + math.sin(ang + sent * 1.1) * rz
        camino.cubicTo(QPointF(ex + math.cos(ang + sent * 0.2) * rz * 1.6, ey + math.sin(ang + sent * 0.2) * rz * 1.6),
                       QPointF(kx + math.cos(ang + sent * 2.4) * rz * 1.2, ky + math.sin(ang + sent * 2.4) * rz * 1.2),
                       QPointF(kx + math.cos(ang + sent * 3.4) * rz * 0.9, ky + math.sin(ang + sent * 3.4) * rz * 0.9))
        p.save()
        p.setPen(QPen(QColor(color), max(1.0, grosor), Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawPath(camino)
        p.restore()
        if prof > 0:
            for lado in (-1, 1):
                if r.random() < 0.75:
                    self._rama(p, ex, ey, ang + lado * r.uniform(0.35, 0.7), largo * 0.68, grosor * 0.7,
                               prof - 1, r, color)

    def _castillo(self, p, w, h, r):
        base = BASE_CASTILLO * h
        p.save()
        x0, x1, alto_m = MURO[0] * w, MURO[1] * w, MURO[2] * h
        muro = QRectF(x0, base - alto_m, x1 - x0, alto_m)
        p.fillRect(muro, QColor(PIEDRA))
        _piedras(p, muro, 3, 16, r, PIEDRA)
        _luz_lunar(p, muro)
        p.setPen(QPen(con_alfa(TINTA, 200), 1.2))
        p.setBrush(QBrush(QColor(PIEDRA)))
        n = 18
        for i in range(0, n, 2):
            xa = x0 + (x1 - x0) * i / n
            p.drawRect(QRectF(xa, muro.top() - 0.014 * h, (x1 - x0) / n, 0.014 * h))
        for cx, tw, th, techo, _v in sorted(TORRES, key=lambda t: t[1]):
            self._torre(p, cx * w, base, tw * w, th * h, techo * h, r, h)
        # Puerta del homenaje: arco oscuro con luz rosa al fondo.
        cx = TORRES[2][0] * w
        aw, ah = 0.034 * w, 0.075 * h
        puerta = _forma_ventana(cx, base - ah, aw, ah, True)
        g = QLinearGradient(cx, base - ah, cx, base)
        g.setColorAt(0, QColor(TINTA))
        g.setColorAt(0.6, QColor("#3A1E5C"))
        g.setColorAt(1, QColor(ROSA_HALO))
        p.fillPath(puerta, QBrush(g))
        p.setPen(QPen(QColor(TINTA), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(puerta)
        # Ventanas (encima de todo, para que no las tape ninguna torre).
        for x, y, aw2, ah2, arco in _ventanas(w, h):
            p.setPen(QPen(QColor(TINTA), max(1.5, 0.0016 * h)))
            p.setBrush(QBrush(con_alfa(ROSA_HALO, 120)))
            p.drawPath(_forma_ventana(x, y, aw2, ah2, arco))
            p.setPen(QPen(QColor(TINTA), max(1.0, 0.0012 * h)))
            if arco:
                p.drawLine(QPointF(x, y + aw2 / 2), QPointF(x, y + ah2))
            else:
                p.drawLine(QPointF(x - aw2 / 2, y + aw2 / 2), QPointF(x + aw2 / 2, y + aw2 / 2))
                p.drawLine(QPointF(x, y), QPointF(x, y + aw2))
        p.restore()

    def _torre(self, p, cx, base, ancho, alto, techo, r, h):
        x0 = cx - ancho / 2
        top = base - alto
        cuerpo = QPainterPath()
        cuerpo.addRoundedRect(QRectF(x0, top, ancho, alto + 0.03 * alto), ancho * 0.14, ancho * 0.14)
        g = QLinearGradient(x0, 0, x0 + ancho, 0)
        g.setColorAt(0, QColor("#1A0E2A"))
        g.setColorAt(0.55, QColor(PIEDRA))
        g.setColorAt(1, QColor("#4A3566"))
        p.save()
        p.setPen(Qt.NoPen)
        p.fillPath(cuerpo, QBrush(g))
        p.setClipPath(cuerpo)
        _piedras(p, QRectF(x0, top, ancho, alto), max(4, int(alto / (0.028 * h))), 3, r, PIEDRA)
        _luz_lunar(p, QRectF(x0, top, ancho, alto))
        p.restore()
        punta = _tejado(p, cx, top, ancho, techo)
        _banderin(p, punta.x(), punta.y(), 0.05 * h)

    def _suelo(self, p, w, h):
        camino = QPainterPath(QPointF(0, 0.86 * h))
        camino.quadTo(QPointF(0.5 * w, 0.79 * h), QPointF(w, 0.86 * h))
        camino.lineTo(QPointF(w, h))
        camino.lineTo(QPointF(0, h))
        camino.closeSubpath()
        g = QLinearGradient(0, 0.8 * h, 0, h)
        g.setColorAt(0, QColor("#2A1640"))
        g.setColorAt(1, QColor(NEGRO))
        p.fillPath(camino, QBrush(g))

    def _capa_lapidas(self, w, h, r):
        """Primer plano (lápidas, calabazas, hongos, rosas, verja) en una capa transparente que se dibuja
        encima de la niebla animada: así la niebla queda detrás de las lápidas."""
        y0 = int(0.78 * h)
        capa = QPixmap(w, h - y0)
        capa.fill(Qt.transparent)
        pc = QPainter(capa)
        try:
            pc.setRenderHint(QPainter.Antialiasing, True)
            pc.translate(0, -y0)
            self._cementerio(pc, w, h, r)
        finally:
            pc.end()
        return (y0, capa)

    def _cementerio(self, p, w, h, r):
        """Primer plano tierno: lápidas con calaveritas, calabazas, hongos, rosas negras y una verja."""
        for fx, fy, aw_f, ah_f in ((0.05, 0.95, 0.05, 0.10), (0.14, 0.90, 0.04, 0.085), (0.22, 0.97, 0.055, 0.12),
                                   (0.31, 0.90, 0.045, 0.09), (0.41, 0.96, 0.05, 0.11), (0.49, 0.90, 0.04, 0.085)):
            self._lapida(p, fx * w, fy * h, aw_f * w, ah_f * h, r)
        for fx, fy in ((0.11, 0.985), (0.44, 0.99)):
            self._calabaza(p, fx * w, fy * h, 0.035 * h)
        for fx, fy in ((0.06, 0.99), (0.18, 0.975), (0.36, 0.995)):
            self._hongo(p, fx * w, fy * h, 0.02 * h)
        for fx, fy in ((0.27, 0.99), (0.56, 0.975)):
            self._rosa(p, fx * w, fy * h, 0.02 * h)
        _verja(p, 0.62 * w, 0.99 * w, 0.90 * h, 0.10 * h, w, h)

    def _lapida(self, p, cx, base, ancho, alto, r):
        camino = QPainterPath(QPointF(cx - ancho / 2, base))
        camino.lineTo(QPointF(cx - ancho / 2, base - alto + ancho / 2))
        camino.arcTo(QRectF(cx - ancho / 2, base - alto, ancho, ancho), 180, -180)
        camino.lineTo(QPointF(cx + ancho / 2, base))
        camino.closeSubpath()
        g = QLinearGradient(cx - ancho / 2, 0, cx + ancho / 2, 0)
        g.setColorAt(0, QColor("#2E2046"))
        g.setColorAt(0.7, QColor("#3E2C5A"))
        g.setColorAt(1, QColor("#5A4478"))
        p.save()
        p.fillPath(camino, QBrush(g))
        arco = QPainterPath(QPointF(cx - ancho / 2, base - alto + ancho / 2))     # borde iluminado arriba
        arco.arcTo(QRectF(cx - ancho / 2, base - alto, ancho, ancho), 180, -180)
        p.setPen(QPen(con_alfa("#C9A6E0", 160), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawPath(arco)
        _calavera(p, cx, base - alto * 0.62, ancho * 0.22, con_alfa("#6B5A88", 170), con_alfa(TINTA, 200))
        p.restore()

    def _calabaza(self, p, cx, base, rad):
        p.save()
        p.setPen(Qt.NoPen)
        cuerpo = QPainterPath()
        cuerpo.setFillRule(Qt.WindingFill)
        for dx, rx in ((-0.42, 0.62), (0.42, 0.62), (0.0, 0.8)):
            cuerpo.addEllipse(QPointF(cx + dx * rad, base - 0.7 * rad), rx * rad, 0.7 * rad)
        g = QLinearGradient(cx - rad, 0, cx + rad, 0)
        g.setColorAt(0, QColor("#4E2470"))
        g.setColorAt(0.5, QColor("#8A55B0"))
        g.setColorAt(1, QColor("#3A1A58"))
        p.fillPath(cuerpo, QBrush(g))
        p.setPen(QPen(con_alfa(SOMBRA_NUBE, 150), max(1.0, rad * 0.04)))
        p.setBrush(Qt.NoBrush)
        for dx in (-0.45, 0.0, 0.45):
            costilla = QPainterPath(QPointF(cx + dx * rad, base - 1.38 * rad))
            costilla.quadTo(QPointF(cx + dx * rad * 1.35, base - 0.7 * rad), QPointF(cx + dx * rad, base - 0.02 * rad))
            p.drawPath(costilla)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(SOMBRA_NUBE)))
        p.drawRoundedRect(QRectF(cx - 0.08 * rad, base - 1.6 * rad, 0.16 * rad, 0.36 * rad), 0.05 * rad, 0.05 * rad)
        p.setBrush(QBrush(con_alfa("#FFE3F2", 70)))
        p.drawEllipse(QPointF(cx - 0.45 * rad, base - 1.05 * rad), 0.14 * rad, 0.10 * rad)
        p.restore()

    def _hongo(self, p, cx, base, rad):
        p.save()
        p.setPen(Qt.NoPen)
        tallo = QPainterPath()
        tallo.addRoundedRect(QRectF(cx - 0.32 * rad, base - 0.95 * rad, 0.64 * rad, 0.95 * rad), 0.2 * rad, 0.2 * rad)
        p.fillPath(tallo, QBrush(QColor("#EADDFB")))
        tapa = QPainterPath(QPointF(cx - rad, base - 0.8 * rad))
        tapa.cubicTo(QPointF(cx - rad, base - 2.4 * rad), QPointF(cx + rad, base - 2.4 * rad),
                     QPointF(cx + rad, base - 0.8 * rad))
        tapa.cubicTo(QPointF(cx + 0.5 * rad, base - 0.55 * rad), QPointF(cx - 0.5 * rad, base - 0.55 * rad),
                     QPointF(cx - rad, base - 0.8 * rad))
        tapa.closeSubpath()
        g = QLinearGradient(cx - rad, base - 2.4 * rad, cx + rad, base - 0.8 * rad)
        g.setColorAt(0, QColor("#FFA6D6"))
        g.setColorAt(1, QColor("#C2407F"))
        p.fillPath(tapa, QBrush(g))
        p.setBrush(QBrush(QColor("#FFF4FB")))
        for dx, dy, rr in ((-0.45, -1.40, 0.17), (0.30, -1.60, 0.14), (0.60, -1.10, 0.12), (-0.05, -1.00, 0.10)):
            p.drawEllipse(QPointF(cx + dx * rad, base + dy * rad), rr * rad, rr * rad)
        p.restore()

    def _rosa(self, p, cx, base, rad):
        """Rosa negra con brillo rosa y pétalos en espiral."""
        p.save()
        tallo = QPainterPath(QPointF(cx, base))
        tallo.cubicTo(QPointF(cx - 0.2 * rad, base - 1.0 * rad), QPointF(cx + 0.2 * rad, base - 1.6 * rad),
                      QPointF(cx, base - 2.0 * rad))
        p.setPen(QPen(QColor("#1A0E26"), max(2.0, rad * 0.16), Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawPath(tallo)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#1F1030")))
        for sg in (-1, 1):
            p.save()
            p.translate(cx + sg * 0.45 * rad, base - 1.2 * rad)
            p.rotate(-sg * 35)
            p.drawEllipse(QPointF(0, 0), 0.42 * rad, 0.18 * rad)
            p.restore()
        cy = base - 2.0 * rad
        self.brillo(p, cx, cy, 2.4 * rad, ROSA, alfa=110)
        p.setBrush(QBrush(QColor("#140A1C")))
        p.drawEllipse(QPointF(cx, cy), rad, rad)
        n = 64
        espiral = QPainterPath()
        for k in range(n):
            th = k / (n - 1) * 4 * math.pi
            rr = rad * (0.92 - 0.82 * k / (n - 1))
            pt = QPointF(cx + rr * math.cos(th), cy + rr * math.sin(th) * 0.92)
            if k == 0:
                espiral.moveTo(pt)
            else:
                espiral.lineTo(pt)
        p.setPen(QPen(con_alfa(ROSA, 190), max(1.0, rad * 0.09), Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawPath(espiral)
        p.restore()

    def _granulado(self, p, w, h, r):
        puntos = QPolygonF([QPointF(r.random() * w, r.random() * h) for _ in range(6000)])
        p.save()
        p.setPen(QPen(con_alfa("#FFFFFF", 8), 1.0))
        p.drawPoints(puntos)
        p.restore()

    def _vineta(self, p, w, h):
        g = QRadialGradient(QPointF(w / 2, h * 0.46), math.hypot(w / 2, h / 2))
        g.setColorAt(0.55, con_alfa(NEGRO, 0))
        g.setColorAt(1, con_alfa(NEGRO, 150))
        p.fillRect(QRectF(0, 0, w, h), QBrush(g))

    # ------------------------------------------------------------ lo que se mueve

    def pintar_animado(self, p, w, h, t):
        if self._alto_spr != h:
            self._spr = {}
            self._alto_spr = h
        p.save()
        self._titilan(p, w, h, t)
        self._fugaz(p, w, h, t)
        self._murcielagos_dibujar(p, w, h, t)
        self._ventanas_brillan(p, w, h)
        self._flotantes(p, w, h, t)
        self._niebla_dibujar(p, w, h, t)
        if self._capa_cementerio is not None:
            y0, capa = self._capa_cementerio
            p.drawPixmap(0, y0, capa)
        p.restore()
        self.ondas(p, base_y=0.82 * h, ancho=w, alto_max=0.10 * h, color=self.acento())

    def _pixmap(self, clave, lado, dibujar):
        """Sprite pre-renderizado (transparente) de lado x lado, guardado en caché."""
        pm = self._spr.get(clave)
        if pm is None:
            pm = QPixmap(lado, lado)
            pm.fill(Qt.transparent)
            pc = QPainter(pm)
            try:
                pc.setRenderHint(QPainter.Antialiasing, True)
                dibujar(pc, lado / 2)
            finally:
                pc.end()
            self._spr[clave] = pm
        return pm

    def _destello(self, lado, color, alfa):
        def dib(pc, c):
            g = QRadialGradient(QPointF(c, c), c)
            g.setColorAt(0, con_alfa(color, alfa))
            g.setColorAt(0.3, con_alfa(color, alfa * 0.4))
            g.setColorAt(1, con_alfa(color, 0))
            pc.fillRect(QRectF(0, 0, 2 * c, 2 * c), QBrush(g))
        return self._pixmap(("destello", lado, color, alfa), lado, dib)

    def _sprite_flot(self, tipo, lado):
        def dib(pc, c):
            if tipo == "corazon":
                pc.setPen(Qt.NoPen)
                pc.fillPath(_corazon(c, c, lado * 0.36), QBrush(QColor(ROSA_HALO)))
            else:
                _calavera(pc, c, c, lado * 0.36, con_alfa(ROSA, 170), con_alfa(SOMBRA_NUBE, 170))
        return self._pixmap((tipo, lado), lado, dib)

    def _murcielago(self, lado, idx):
        """Murciélago tierno sin cara: alas redondeadas en 3 cuadros (arriba, medio, abajo)."""
        def dib(pc, c):
            s = lado / 4.2     # con margen: las alas no se cortan en el borde del sprite (no más rectángulos)
            tip_y = (-0.8, -0.05, 0.5)[idx] * s
            pc.setPen(Qt.NoPen)
            for sg in (-1, 1):
                ala = QPainterPath(QPointF(c, c))
                ala.cubicTo(QPointF(c + sg * 0.5 * s, c + tip_y * 0.1 - 0.2 * s),
                            QPointF(c + sg * 1.2 * s, c + tip_y - 0.25 * s),
                            QPointF(c + sg * 1.7 * s, c + tip_y))
                ala.quadTo(QPointF(c + sg * 1.8 * s, c + tip_y + 0.85 * s), QPointF(c + sg * 1.25 * s, c + 0.5 * s))
                ala.quadTo(QPointF(c + sg * 1.0 * s, c + 0.9 * s), QPointF(c + sg * 0.6 * s, c + 0.55 * s))
                ala.quadTo(QPointF(c + sg * 0.3 * s, c + 0.85 * s), QPointF(c + sg * 0.15 * s, c + 0.3 * s))
                ala.closeSubpath()
                pc.fillPath(ala, QBrush(QColor("#241238")))
                pc.fillPath(_ovalo(c + sg * 1.05 * s, c + tip_y * 0.45 + 0.1 * s, 0.12 * s, 0.09 * s),
                            QBrush(con_alfa(ROSA_HALO, 110)))
            cuerpo = QPainterPath()
            cuerpo.addEllipse(QPointF(c, c + 0.1 * s), 0.42 * s, 0.55 * s)
            cuerpo.addEllipse(QPointF(c, c - 0.35 * s), 0.30 * s, 0.30 * s)
            for sg in (-1, 1):
                cuerpo.moveTo(QPointF(c + sg * 0.24 * s, c - 0.45 * s))
                cuerpo.lineTo(QPointF(c + sg * 0.30 * s, c - 0.95 * s))
                cuerpo.lineTo(QPointF(c + sg * 0.02 * s, c - 0.60 * s))
                cuerpo.closeSubpath()
            cuerpo.setFillRule(Qt.WindingFill)
            pc.fillPath(cuerpo, QBrush(QColor("#1A0B2E")))
        return self._pixmap(("murcielago", lado, idx), lado, dib)

    def _titilan(self, p, w, h, t):
        p.setPen(Qt.NoPen)
        for fx, fy, tam, fase, vel in self._brillantes:
            e = 0.5 + 0.5 * math.sin(t * vel + fase)
            lado = _lado(tam * h)
            p.setOpacity(0.25 + 0.75 * e)
            p.drawPixmap(QPointF(fx * w - lado / 2, fy * h - lado / 2), self._destello(lado, "#FFFFFF", 230))
        p.setOpacity(1.0)

    def _fugaz(self, p, w, h, t):
        """Una estrella fugaz cada 4-7 s: estela que se desvanece. Cada franja de 5.5 s tiene su propio azar."""
        k0 = int(t // 5.5)
        for k in (k0 - 1, k0):
            if k < 0:
                continue
            rr = random.Random(k * 7919 + 79)
            inicio = k * 5.5 + (rr.random() - 0.5) * 1.5
            x0, y0 = rr.uniform(0.12, 0.7), rr.uniform(0.05, 0.28)
            edad = t - inicio
            if not (0 <= edad < 0.9):
                continue
            s = edad / 0.9
            cab = QPointF((x0 + 0.32 * s) * w, (y0 + 0.12 * s) * h)
            largo = min(1.0, 0.3 + s)
            cola = QPointF(cab.x() - 0.16 * w * largo, cab.y() - 0.066 * h * largo)
            fade = 1 - s * s
            g = QLinearGradient(cola, cab)
            g.setColorAt(0, con_alfa("#FFFFFF", 0))
            g.setColorAt(1, con_alfa("#FFE3F2", 240 * fade))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QBrush(g), max(1.5, 0.0035 * h), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(cola, cab)
            lado = _lado(0.05 * h)
            p.setOpacity(fade)
            p.drawPixmap(QPointF(cab.x() - lado / 2, cab.y() - lado / 2), self._destello(lado, "#FFFFFF", 255))
            p.setOpacity(1.0)

    def _murcielagos_dibujar(self, p, w, h, t):
        for fase, periodo, y0, amp, tam in self._murcielagos:
            u = (t / periodo + fase) % 1.0
            x = (-0.08 + 1.16 * u) * w
            y = (y0 + amp * math.sin(u * math.pi)) * h
            lado = _lado(tam * h * 3.6)
            idx = (0, 1, 2, 1)[int(t * 9 + fase * 40) % 4]
            p.drawPixmap(QPointF(x - lado / 2, y - lado / 2), self._murcielago(lado, idx))

    def _ventanas_brillan(self, p, w, h):
        e = max(0.0, min(1.0, 0.2 + 0.9 * self.energia()))
        lado = _lado(0.13 * h)
        glow = self._destello(lado, ROSA_HALO, 200)
        for x, y, aw, ah, arco in _ventanas(w, h):
            p.setPen(Qt.NoPen)
            p.fillPath(_forma_ventana(x, y, aw, ah, arco), QBrush(con_alfa("#FFD1EA", 60 + 170 * e)))
            p.setOpacity(0.15 + 0.6 * e)
            p.drawPixmap(QPointF(x - lado / 2, y + ah / 2 - lado / 2), glow)
            p.setOpacity(1.0)

    def _flotantes(self, p, w, h, t):
        for fx, fy, tam, fase, amp, giro, tipo in self._flotan:
            cx = (fx + math.sin(t * 0.3 + fase) * amp) * w
            cy = (fy + math.sin(t * 0.22 + fase * 1.7) * 0.025) * h
            ang = 18 * math.sin(t * 0.5 + fase) + (giro * t) % 360
            lado = _lado(tam * h * 2.6)
            pm = self._sprite_flot(tipo, lado)
            p.save()
            p.translate(cx, cy)
            p.rotate(ang)
            p.drawPixmap(QPointF(-lado / 2, -lado / 2), pm)
            p.restore()

    def _niebla_dibujar(self, p, w, h, t):
        clave = (w, h)
        if self._niebla_clave != clave:
            self._niebla = [self._pm_niebla(w, int(0.13 * h), 101), self._pm_niebla(w, int(0.10 * h), 202)]
            self._niebla_clave = clave
        for pm, y, vel in zip(self._niebla, (0.76 * h, 0.87 * h), (16.0, -10.0)):
            off = (t * vel) % (2 * w)
            p.drawPixmap(QPointF(-off, y), pm)
            p.drawPixmap(QPointF(2 * w - off, y), pm)

    def _pm_niebla(self, w, fh, semilla):
        """Franja de niebla morada de 2*w de ancho, periódica: se desplaza sin saltos."""
        pm = QPixmap(2 * w, max(8, fh))
        pm.fill(Qt.transparent)
        rr = random.Random(semilla)
        pc = QPainter(pm)
        try:
            pc.setRenderHint(QPainter.Antialiasing, True)
            pc.setPen(Qt.NoPen)
            for _ in range(30):
                x = rr.uniform(0, 2 * w)
                y = rr.uniform(0.3, 0.7) * fh
                rad = rr.uniform(0.25, 0.5) * fh
                g = QRadialGradient(QPointF(0, 0), rad)
                g.setColorAt(0, con_alfa("#8A55B0", 70))
                g.setColorAt(1, con_alfa("#8A55B0", 0))
                pc.setBrush(QBrush(g))
                for dx in (-2 * w, 0, 2 * w):
                    pc.save()
                    pc.translate(x + dx, y)
                    pc.scale(2.6, 1.0)          # niebla achatada, no bolitas
                    pc.drawEllipse(QPointF(0, 0), rad, rad)
                    pc.restore()
        finally:
            pc.end()
        return pm


def _ovalo(cx, cy, rx, ry):
    camino = QPainterPath()
    camino.addEllipse(QPointF(cx, cy), rx, ry)
    return camino


def _verja(p, x0, x1, base, alto, w, h):
    """Verja con postes y remates de corazón; dos travesaños."""
    p.save()
    p.setPen(Qt.NoPen)
    oscuro = QColor("#1A0F26")
    grosor_barra = max(2.0, 0.006 * h)
    p.fillRect(QRectF(x0, base - alto * 0.35, x1 - x0, grosor_barra), oscuro)
    p.fillRect(QRectF(x0, base - alto * 0.8, x1 - x0, grosor_barra), oscuro)
    grosor = max(2.0, 0.0022 * w)
    s = max(3.0, 0.011 * h)
    x = x0
    while x <= x1:
        p.fillRect(QRectF(x - grosor / 2, base - alto, grosor, alto), oscuro)
        p.fillPath(_corazon(x, base - alto - s * 0.6, s), QBrush(QColor(ROSA)))
        x += 0.026 * w
    p.restore()
