# -*- coding: utf-8 -*-
"""Escenario «Gym»: gimnasio nocturno de estética premium, de anuncio deportivo.

Sala en perspectiva de un punto de fuga (0.5w, 0.45h): pared de ladrillo visto con viñeta, suelo de caucho con
losetas y reflejo de las lámparas, espejos en las paredes laterales, vigas y conductos en el techo y tres lámparas
de campana. En el equipo: rack de sentadillas con barra y discos de competición, banco, saco de boxeo, estante de
mancuernas hexagonales, cuerda de batalla y kettlebells.

Lo estático se pinta una vez y se guarda; cada cuadro solo mueve el letrero de neón, las tiras LED, la barra, el
saco, el polvo de tiza y el monitor de ritmo, todo con sprites ya pre-renderizados.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
                           QRadialGradient)

from .base import EscenarioBase, con_alfa, mezclar

TEXTO_NEON = "NO PAIN NO GAIN"
PARTICULAS = 90                       # polvo de tiza en los conos de luz
GRANO = 6000
LAMPARAS = (0.20, 0.52, 0.82)         # x de cada lámpara (fracción de w)
PIVOTE_SACO = (0.29, 0.108)           # de dónde cuelga el saco (fracción de w y h)
VP = (0.5, 0.45)                      # punto de fuga
FONDO_X = (0.30, 0.70)                # bordes izquierdo y derecho de la pared del fondo
FONDO_Y = (0.20, 0.70)                # techo y suelo de la pared del fondo
COLOR_VERDE, COLOR_ROJO = "#2E7D32", "#C62828"
COLOR_AZUL, COLOR_AMARILLO = "#1565C0", "#F9A825"


class _Sala:
    """Geometría de la sala. Para un punto de la pared lateral: `u` es la distancia horizontal al punto de fuga
    (px) y `k` la altura relativa (-1 techo del fondo, +1 suelo del fondo). Así las líneas son exactas en
    perspectiva."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.vx, self.vy = VP[0] * w, VP[1] * h
        self.ub = (VP[0] - FONDO_X[0]) * w                 # profundidad del borde del fondo
        self.hc = (FONDO_Y[1] - VP[1]) * h / self.ub       # pendiente de techo y suelo
        self.xl, self.xr = FONDO_X[0] * w, FONDO_X[1] * w
        self.yt, self.yb = FONDO_Y[0] * h, FONDO_Y[1] * h

    def pared(self, u, k, lado):
        return QPointF(self.vx + lado * u, self.vy + k * self.hc * u)


# ---------------------------------------------------------------- ayudas de dibujo (módulo)

def _lerp(a, b, f):
    return QPointF(a.x() + (b.x() - a.x()) * f, a.y() + (b.y() - a.y()) * f)


def _camino(puntos):
    c = QPainterPath()
    c.addPolygon(QPolygonF(puntos))
    c.closeSubpath()
    return c


def _rr(x0, y0, x1, y1, radio=2.0):
    c = QPainterPath()
    c.addRoundedRect(QRectF(x0, y0, x1 - x0, y1 - y0), radio, radio)
    return c


def _elipse(caja):
    c = QPainterPath()
    c.addEllipse(caja)
    return c


def _hex(cx, cy, r):
    """Hexágono de punta arriba."""
    return [QPointF(cx + r * math.cos(math.radians(-90 + 60 * k)),
                    cy + r * math.sin(math.radians(-90 + 60 * k))) for k in range(6)]


def _volumen(p, camino, base, claro=0.22, oscuro=0.55):
    """Relleno con lado iluminado a la izquierda y lado en sombra a la derecha."""
    r = camino.boundingRect()
    g = QLinearGradient(r.left(), 0, r.right(), 0)
    g.setColorAt(0.0, mezclar(QColor(base), QColor("#FFFFFF"), claro))
    g.setColorAt(0.45, QColor(base))
    g.setColorAt(1.0, mezclar(QColor(base), QColor("#000000"), oscuro))
    p.fillPath(camino, g)


def _metal(p, camino):
    """Acero cilíndrico: plateado en el centro, oscuro a los lados."""
    r = camino.boundingRect()
    g = QLinearGradient(r.left(), 0, r.right(), 0)
    g.setColorAt(0.0, QColor("#5A5E64"))
    g.setColorAt(0.4, QColor("#C9CDD3"))
    g.setColorAt(1.0, QColor("#4A4E54"))
    p.fillPath(camino, g)


def _sombra(p, cx, cy, rx, ry):
    """Sombra blanda en el suelo: cuatro elipses #000 alfa 60 con desplazamiento creciente."""
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 60))
    for i in range(4):
        p.drawEllipse(QPointF(cx + rx * 0.05 * i, cy + ry * 0.12 * i), rx * (1 - 0.07 * i), ry * (1 - 0.12 * i))
    p.restore()


def _sprite(w, h, x0f, y0f, x1f, y1f, dibujar):
    """Pre-renderiza una región (coordenadas absolutas dentro de la función `dibujar`)."""
    x0, y0 = x0f * w, y0f * h
    pm = QPixmap(max(1, int((x1f - x0f) * w)), max(1, int((y1f - y0f) * h)))
    pm.fill(QColor(0, 0, 0, 0))
    q = QPainter(pm)
    try:
        q.setRenderHint(QPainter.Antialiasing, True)
        q.translate(-x0, -y0)
        dibujar(q)
    finally:
        q.end()
    return pm, x0, y0


def _pm_trazo(ancho, alto, m, asc, trazo, pinceles):
    """Sprite de un glifo (trazo centrado en su línea base) con uno o más pinceles en capas."""
    pm = QPixmap(ancho, alto)
    pm.fill(QColor(0, 0, 0, 0))
    q = QPainter(pm)
    try:
        q.setRenderHint(QPainter.Antialiasing, True)
        q.translate(m, m + asc)
        q.setBrush(Qt.NoBrush)
        for color, grosor in pinceles:
            q.setPen(QPen(color, grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            q.drawPath(trazo)
    finally:
        q.end()
    return pm


# Letras del neón como trazos (tubo de neón), en unidades de altura: no dependen de fuentes del sistema.
ANCHO_GLIFO = 0.62
GLIFOS = {
    "N": [[(0, 1), (0, 0), (ANCHO_GLIFO, 1), (ANCHO_GLIFO, 0)]],
    "O": "ovalo",
    "P": [[(0, 1), (0, 0), (0.42, 0), (0.56, 0.10), (0.56, 0.40), (0.42, 0.52), (0, 0.52)]],
    "A": [[(0, 1), (0.31, 0), (ANCHO_GLIFO, 1)], [(0.12, 0.60), (0.50, 0.60)]],
    "I": [[(0.31, 0), (0.31, 1)]],
    "G": [[(0.62, 0.18), (0.50, 0.03), (0.30, 0), (0.10, 0.08), (0, 0.50), (0.10, 0.92), (0.30, 1),
           (0.55, 0.90), (0.62, 0.62), (0.34, 0.62)]],
}
ESPACIO_LETRA = 0.12                  # hueco entre letras (en altura)
ESPACIO_PALABRA = 0.80                # avance de un espacio (en altura)


def _trazo_letra(ch, lh):
    """Trazo de una letra con altura `lh` y origen arriba a la izquierda."""
    c = QPainterPath()
    dato = GLIFOS[ch]
    if dato == "ovalo":
        c.addEllipse(QRectF(0, 0, ANCHO_GLIFO * lh, lh))
        return c
    for linea in dato:
        c.moveTo(QPointF(linea[0][0] * lh, linea[0][1] * lh))
        for x, y in linea[1:]:
            c.lineTo(QPointF(x * lh, y * lh))
    return c


def _tira(p, pts, color, fuerza, s):
    """Tira de LED: halo ancho y suave, cuerpo del color y núcleo casi blanco."""
    poli = QPolygonF(pts)
    nucleo = mezclar(QColor(color), QColor("#FFFFFF"), 0.6)
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(con_alfa(color, 40 * fuerza), 9 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline(poli)
    p.setPen(QPen(con_alfa(color, 90 * fuerza), 3 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline(poli)
    p.setPen(QPen(con_alfa(nucleo, 230 * fuerza), 1.4 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline(poli)
    p.restore()


def _disco(p, cx, cy, rx, ry, color, s):
    """Disco de competición visto de lado: negro con anillo de color, cubo interior y brillo especular."""
    p.save()
    p.setPen(Qt.NoPen)
    caja = QRectF(cx - rx, cy - ry, 2 * rx, 2 * ry)
    _volumen(p, _elipse(caja), "#15171A", 0.25, 0.7)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(color), max(1.5, rx * 0.22)))
    p.drawEllipse(caja.adjusted(rx * 0.11, ry * 0.11, -rx * 0.11, -ry * 0.11))
    cubo = QRectF(cx - rx * 0.42, cy - ry * 0.42, rx * 0.84, ry * 0.84)
    _volumen(p, _elipse(cubo), "#8A9097", 0.35, 0.6)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#050505"))
    p.drawEllipse(QPointF(cx, cy), rx * 0.18, ry * 0.18)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 85), max(1.0, rx * 0.09)))
    p.drawArc(caja.adjusted(rx * 0.3, ry * 0.3, -rx * 0.3, -ry * 0.3), 120 * 16, 50 * 16)
    p.restore()


def _dib_barra(p, w, h, s):
    """Barra olímpica con manguitos y discos de competición (se dibuja en un sprite que vibra)."""
    y = 0.42 * h
    barra = _rr(0.004 * w, y - 0.0045 * h, 0.262 * w, y + 0.0045 * h, 3 * s)
    g = QLinearGradient(0, y - 0.0045 * h, 0, y + 0.0045 * h)
    g.setColorAt(0.0, QColor("#7D838A"))
    g.setColorAt(0.45, QColor("#E9ECF0"))
    g.setColorAt(1.0, QColor("#4B5056"))
    p.fillPath(barra, g)
    for x0, x1 in ((0.0515, 0.0555), (0.2185, 0.2225)):
        _metal(p, _rr(x0 * w, y - 0.014 * h, x1 * w, y + 0.014 * h, 2 * s))
    # de fuera hacia dentro: (x, radio x, radio y, color del anillo)
    for xf, rxf, ryf, color in ((0.030, 0.011, 0.094, COLOR_VERDE), (0.046, 0.0105, 0.078, COLOR_ROJO),
                                (0.225, 0.010, 0.078, COLOR_AZUL), (0.240, 0.011, 0.094, COLOR_AMARILLO)):
        cx, rx, ry = xf * w, rxf * w, ryf * h
        grosor = QRectF(cx - rx + 0.004 * w, y - ry, 2 * rx, 2 * ry)          # cara trasera del disco
        _volumen(p, _elipse(grosor), "#050605", 0.1, 0.6)
        _disco(p, cx, y, rx, ry, color, s)


def _dib_saco(p, w, h, s):
    """Saco de boxeo con cadenas. El pivote es el gancho bajo el conducto; el sprite gira alrededor de él."""
    px, py = PIVOTE_SACO[0] * w, PIVOTE_SACO[1] * h
    fin_y = 0.25 * h
    p.save()
    p.setPen(Qt.NoPen)
    for sgn in (-1, 1):
        ini = QPointF(px + sgn * 0.006 * w, py)
        fin = QPointF(px + sgn * 0.018 * w, fin_y)
        p.setPen(QPen(QColor("#6B7178"), 1.2 * s))
        p.drawLine(ini, fin)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#B8BEC5"), 1.2 * s))
        for i in range(1, 12):
            c = _lerp(ini, fin, i / 12.0)
            p.drawEllipse(c, 2.6 * s, 3.8 * s)
        p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor("#9AA0A6"), 2.0 * s))
    p.setBrush(QColor("#2A2D2A"))
    p.drawEllipse(QPointF(px, py), 0.006 * w, 0.006 * w)
    p.setPen(Qt.NoPen)
    cuerpo = QRectF(px - 0.024 * w, fin_y, 0.048 * w, 0.37 * h)
    camino = QPainterPath()
    camino.addRoundedRect(cuerpo, 0.024 * w, 0.024 * w)
    _volumen(p, camino, "#4A1418", 0.30, 0.72)
    # costuras y brillo del cuero
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 40), 1.2 * s, Qt.DashLine))
    for dx in (-0.011, 0.011):
        p.drawLine(QPointF(px + dx * w, fin_y + 0.02 * h), QPointF(px + dx * w, fin_y + 0.34 * h))
    for yf in (0.33, 0.44, 0.55):
        p.setPen(QPen(QColor(255, 255, 255, 26), 1.2 * s))
        p.drawLine(QPointF(px - 0.02 * w, yf * h), QPointF(px + 0.02 * w, yf * h))
    p.setPen(QPen(QColor(255, 255, 255, 40), 3 * s, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(px - 0.016 * w, fin_y + 0.03 * h), QPointF(px - 0.016 * w, fin_y + 0.24 * h))
    p.restore()


def _mancuerna(p, cx, base, r):
    """Mancuerna hexagonal vista de frente: dos cabezas con mango cromado entre ellas, apoyada en `base`."""
    cy = base - r
    dx = r * 1.35
    _metal(p, _rr(cx - dx, cy - 0.22 * r, cx + dx, cy + 0.22 * r, 0.2 * r + 0.5))
    for hx in (cx - dx, cx + dx):
        _volumen(p, _camino(_hex(hx, cy, r)), "#1A1C1A", 0.22, 0.55)
        _metal(p, _elipse(QRectF(hx - 0.42 * r, cy - 0.42 * r, 0.84 * r, 0.84 * r)))


class EscenarioGym(EscenarioBase):
    NOMBRE = "Gym"
    ACENTO = "#A3E635"
    SEMILLA = 11

    def preparar(self):
        r = self.rnd
        # polvo de tiza: (lámpara, posición dentro del cono, altura de partida, velocidad, fase, radio)
        self._polvo = [(i % len(LAMPARAS), r.random(), r.random(), r.uniform(0.03, 0.08),
                        r.uniform(0.0, math.tau), r.uniform(0.0012, 0.0030)) for i in range(PARTICULAS)]
        self._neon = []
        self._clave_neon = None
        self._clave_fijos = None
        self._barra = None
        self._saco = None
        self._parp_letra = -1
        self._parp_ini = -10.0
        self._prox_parpadeo = 3.5
        self._rng_parp = random.Random(67)

    # ------------------------------------------------------------ estático (una vez)

    def pintar_estatico(self, p, w, h):
        r = random.Random(61)
        s = h / 1080.0
        sala = _Sala(w, h)
        p.fillRect(0, 0, w, h, QColor("#050605"))
        self._techo(p, sala, s)
        self._ductos(p, w, h, s)
        self._paredes_laterales(p, sala)
        self._espejos(p, sala)
        self._pared_fondo(p, sala, r, s)
        self._monitor(p, sala, s)
        self._suelo(p, sala, s)
        self._rack(p, w, h, s)
        self._banco(p, w, h, s)
        self._estante(p, w, h, s)
        self._pesas(p, w, h, s)
        self._cuerda(p, w, h, s)
        self._lamparas(p, sala, s)
        # grano del hormigón y viñeta al final
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.drawPoints(QPolygonF([QPointF(r.random() * w, r.random() * h) for _ in range(GRANO)]))
        g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.72)
        g.setColorAt(0.0, QColor(0, 0, 0, 0))
        g.setColorAt(0.55, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 140))
        p.fillRect(0, 0, w, h, g)

    def _techo(self, p, sala, s):
        w, h = sala.w, sala.h
        techo = _camino([QPointF(sala.xl, sala.yt), QPointF(sala.xr, sala.yt),
                         sala.pared(0.8 * w, -1, 1), sala.pared(0.8 * w, -1, -1)])
        g = QLinearGradient(0, 0, 0, sala.yt)
        g.setColorAt(0, QColor("#040504"))
        g.setColorAt(1, QColor("#181A18"))
        p.fillPath(techo, g)
        # vigas negras en perspectiva (convergen al punto de fuga) y vigas transversales
        p.save()
        p.setClipPath(techo)
        for xf in (0.08, 0.22, 0.78, 0.92):
            lejos = QPointF(xf * w, -0.1 * h)
            fin = _lerp(QPointF(sala.vx, sala.vy), lejos, 2.6)
            p.setPen(QPen(QColor("#050605"), 0.010 * w))
            p.drawLine(QPointF(sala.vx, sala.vy), fin)
            p.setPen(QPen(QColor(255, 255, 255, 22), 1.2 * s))
            p.drawLine(QPointF(sala.vx + 0.004 * w, sala.vy), QPointF(fin.x() + 0.004 * w, fin.y()))
        for z in (1.35, 1.9, 2.4):
            y = sala.vy - (h - sala.vy) / z
            p.setPen(QPen(QColor("#050605"), 0.010 * h))
            p.drawLine(QPointF(-0.1 * w, y), QPointF(1.1 * w, y))
            p.setPen(QPen(QColor(255, 255, 255, 22), 1.0 * s))
            p.drawLine(QPointF(-0.1 * w, y - 0.006 * h), QPointF(1.1 * w, y - 0.006 * h))
        p.restore()

    def _ductos(self, p, w, h, s):
        """Conductos de ventilación cilíndricos: degradado horizontal gris para el volumen."""
        for y0f, hf in ((0.078, 0.030), (0.022, 0.012)):
            caja = QRectF(-0.05 * w, y0f * h, 1.10 * w, hf * h)
            g = QLinearGradient(caja.left(), 0, caja.right(), 0)
            g.setColorAt(0.0, QColor("#1C1F21"))
            g.setColorAt(0.25, QColor("#5E656B"))
            g.setColorAt(0.5, QColor("#9AA1A8"))
            g.setColorAt(0.75, QColor("#5E656B"))
            g.setColorAt(1.0, QColor("#1C1F21"))
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(caja, hf * h / 2, hf * h / 2)
            y_luz = caja.top() + caja.height() * 0.25
            p.setPen(QPen(QColor(255, 255, 255, 50), 1.5 * s))
            p.drawLine(QPointF(0.05 * w, y_luz), QPointF(0.95 * w, y_luz))
            p.restore()

    def _paredes_laterales(self, p, sala):
        w = sala.w
        for lado in (-1, 1):
            pts = [sala.pared(sala.ub, -1, lado), sala.pared(0.8 * w, -1, lado),
                   sala.pared(0.8 * w, 1, lado), sala.pared(sala.ub, 1, lado)]
            if lado < 0:
                g = QLinearGradient(0, 0, sala.xl, 0)
            else:
                g = QLinearGradient(w, 0, sala.xr, 0)
            g.setColorAt(0, QColor("#060706"))
            g.setColorAt(1, QColor("#1C1F1C"))
            p.fillPath(_camino(pts), g)

    def _espejos(self, p, sala):
        """Dos espejos por pared, en perspectiva: degradado diagonal gris azulado y un reflejo blanco."""
        w = sala.w
        for lado in (-1, 1):
            for u1, u2, k1, k2 in ((0.24, 0.36, -0.70, 0.25), (0.40, 0.46, -0.90, 0.60)):
                a = sala.pared(u1 * w, k1, lado)
                b = sala.pared(u2 * w, k1, lado)
                c = sala.pared(u2 * w, k2, lado)
                d = sala.pared(u1 * w, k2, lado)
                cam = _camino([a, b, c, d])
                p.fillPath(cam, QColor("#0B0D10"))
                g = QLinearGradient(a, c)
                g.setColorAt(0.0, QColor(138, 154, 174, 40))
                g.setColorAt(0.5, QColor(60, 72, 88, 10))
                g.setColorAt(1.0, QColor(138, 154, 174, 40))
                p.fillPath(cam, g)
                p.save()
                p.setPen(QPen(QColor(255, 255, 255, 30), 3 * sala.h / 1080.0))
                p.drawLine(_lerp(a, b, 0.18), _lerp(d, c, 0.42))
                p.setPen(QPen(QColor("#2A2D2A"), 2 * sala.h / 1080.0))
                p.setBrush(Qt.NoBrush)
                p.drawPath(cam)
                p.restore()

    def _pared_fondo(self, p, sala, r, s):
        """Ladrillo visto: filas alternas desplazadas medio ladrillo, color ±6 por ladrillo, viñeta hacia los lados."""
        w = sala.w
        x0, x1, y0, y1 = sala.xl, sala.xr, sala.yt, sala.yb
        p.fillRect(QRectF(x0, y0, x1 - x0, y1 - y0), QColor("#060706"))      # juntas más oscuras
        cols, filas = 14, 15
        bw, bh = (x1 - x0) / cols, (y1 - y0) / filas
        p.save()
        p.setPen(Qt.NoPen)
        for fila in range(filas):
            yy = y0 + fila * bh
            desp = bw / 2 if fila % 2 else 0.0
            for col in range(-1, cols + 1):
                xa = x0 + col * bw + desp
                xb = xa + bw
                ca, cb = max(xa, x0), min(xb, x1)
                if cb - ca < 4:
                    continue
                f = 1 - 0.6 * (((ca + cb) / 2 - w / 2) / (0.2 * w)) ** 2
                f = max(0.35, min(1.0, f))
                j = r.randint(-6, 6)
                p.setBrush(QColor(round((26 + j) * f), round((28 + j) * f), round((26 + j) * f)))
                p.drawRoundedRect(QRectF(ca + 1.5 * s, yy + 1.5 * s, cb - ca - 3 * s, bh - 3 * s), 2 * s, 2 * s)
                p.fillRect(QRectF(ca + 2 * s, yy + 2 * s, cb - ca - 4 * s, max(1.0, s)), QColor(255, 255, 255, 14))
        p.restore()
        # resplandores tenues sobre el ladrillo (recortados a la pared)
        p.save()
        p.setClipRect(QRectF(x0, y0, x1 - x0, y1 - y0))
        self.brillo(p, sala.vx, sala.vy, 0.26 * w, self.acento(), 16)
        for lf in LAMPARAS:
            self.brillo(p, lf * w, 0.36 * sala.h, 0.12 * w, QColor("#FFE2B0"), 20)
        p.restore()

    def _monitor(self, p, sala, s):
        """Monitor de ritmo: pantalla oscura con borde; la línea de ondas se dibuja en cada cuadro."""
        w, h = sala.w, sala.h
        pant = QRectF(0.325 * w, 0.215 * h, 0.35 * w, 0.103 * h)
        p.save()
        p.setPen(QPen(QColor("#2B2E2B"), 3 * s))
        p.setBrush(QColor("#0B0C0B"))
        p.drawRoundedRect(pant.adjusted(-10 * s, -10 * s, 10 * s, 10 * s), 12 * s, 12 * s)
        g = QLinearGradient(pant.topLeft(), pant.bottomLeft())
        g.setColorAt(0, QColor("#0B1412"))
        g.setColorAt(1, QColor("#040705"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(pant, 6 * s, 6 * s)
        p.setPen(QPen(QColor(255, 255, 255, 14), max(1.0, s)))
        for i in range(1, 4):
            y = pant.top() + pant.height() * i / 4
            p.drawLine(QPointF(pant.left(), y), QPointF(pant.right(), y))
        for i in range(1, 12):
            x = pant.left() + pant.width() * i / 12
            p.drawLine(QPointF(x, pant.top()), QPointF(x, pant.bottom()))
        p.restore()

    def _suelo(self, p, sala, s):
        """Caucho oscuro con losetas en perspectiva; las líneas horizontales se separan hacia abajo."""
        w, h = sala.w, sala.h
        cam = _camino([QPointF(sala.xl, sala.yb), QPointF(sala.xr, sala.yb),
                       sala.pared(0.8 * w, 1, 1), sala.pared(0.8 * w, 1, -1)])
        g = QLinearGradient(0, sala.yb, 0, h)
        g.setColorAt(0, QColor("#0E100E"))
        g.setColorAt(1, QColor("#080908"))
        p.fillPath(cam, g)
        p.save()
        p.setClipPath(cam)
        vx, vy = sala.vx, sala.vy
        p.setPen(QPen(QColor(255, 255, 255, 25), max(1.0, s)))
        for i in range(-8, 19):
            xb = i * 0.1 * w
            escala = (1.6 * h - vy) / (h - vy)
            fin = QPointF(vx + (xb - vx) * escala, 1.6 * h)
            p.drawLine(QPointF(vx, vy), fin)
        for k in range(0, 12):
            z = 1 + 0.22 * k
            y = vy + (h - vy) / z
            p.drawLine(QPointF(-0.1 * w, y), QPointF(1.1 * w, y))
        # reflejo pulido de las lámparas sobre el suelo
        for lf in LAMPARAS:
            p.save()
            p.translate(lf * w, 0.80 * h)
            p.scale(1, 0.22)
            self.brillo(p, 0, 0, 0.16 * w, QColor("#FFE2B0"), 90)
            p.restore()
        p.restore()

    def _rack(self, p, w, h, s):
        """Power rack: postes plateados, travesaño, soportes en J y base negra."""
        base = 0.875 * h
        _sombra(p, 0.125 * w, base, 0.13 * w, 0.012 * h)
        p.save()
        p.setPen(Qt.NoPen)
        _volumen(p, _rr(0.040 * w, base - 0.010 * h, 0.200 * w, base + 0.004 * h, 4 * s), "#0C0D0C", 0.12, 0.5)
        for x0 in (0.060, 0.170):
            _metal(p, _rr(x0 * w, 0.200 * h, (x0 + 0.013) * w, base - 0.008 * h, 3 * s))
        _volumen(p, _rr(0.058 * w, 0.196 * h, 0.185 * w, 0.216 * h, 3 * s), "#1B1D1B", 0.2, 0.55)
        for yf in (0.42, 0.60):
            _volumen(p, _rr(0.073 * w, (yf - 0.006) * h, 0.088 * w, (yf + 0.006) * h, 2 * s), "#16181A", 0.25, 0.5)
            _volumen(p, _rr(0.155 * w, (yf - 0.006) * h, 0.170 * w, (yf + 0.006) * h, 2 * s), "#16181A", 0.25, 0.5)
        p.restore()

    def _banco(self, p, w, h, s):
        """Banco plano acolchado con patas de acero."""
        _sombra(p, 0.425 * w, 0.885 * h, 0.10 * w, 0.011 * h)
        p.save()
        p.setPen(Qt.NoPen)
        for xf in (0.375, 0.478):
            pata = _camino([QPointF(xf * w - 0.008 * w, 0.765 * h), QPointF(xf * w + 0.008 * w, 0.765 * h),
                            QPointF(xf * w + 0.012 * w, 0.87 * h), QPointF(xf * w - 0.012 * w, 0.87 * h)])
            _volumen(p, pata, "#1A1C1A", 0.2, 0.55)
            _volumen(p, _rr(xf * w - 0.02 * w, 0.868 * h, xf * w + 0.02 * w, 0.882 * h, 3 * s), "#0E0F0E")
        _volumen(p, _rr(0.34 * w, 0.732 * h, 0.51 * w, 0.768 * h, 0.012 * h), "#26292A", 0.25, 0.6)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.4 * s))
        p.drawLine(QPointF(0.35 * w, 0.738 * h), QPointF(0.50 * w, 0.738 * h))
        p.setPen(QPen(QColor(0, 0, 0, 120), 1.2 * s, Qt.DashLine))
        p.drawLine(QPointF(0.345 * w, 0.752 * h), QPointF(0.505 * w, 0.752 * h))
        p.restore()

    def _estante(self, p, w, h, s):
        """Estante de mancuernas: dos baldas de acero con hexágonos y mango cromado."""
        _sombra(p, 0.888 * w, 0.912 * h, 0.10 * w, 0.012 * h)
        p.save()
        p.setPen(Qt.NoPen)
        for x0 in (0.800, 0.964):
            _metal(p, _rr(x0 * w, 0.50 * h, (x0 + 0.009) * w, 0.91 * h, 3 * s))
        for yf in (0.600, 0.775):
            _metal(p, _rr(0.79 * w, yf * h, 0.982 * w, (yf + 0.012) * h, 3 * s))
        for cx_f, r_f in ((0.835, 0.010), (0.885, 0.011), (0.935, 0.010)):
            _mancuerna(p, cx_f * w, 0.600 * h, r_f * w)
        for cx_f, r_f in ((0.830, 0.0125), (0.888, 0.0135), (0.946, 0.0125)):
            _mancuerna(p, cx_f * w, 0.775 * h, r_f * w)
        p.restore()

    def _pesas(self, p, w, h, s):
        """Kettlebells en el suelo."""
        self._kettlebell(p, 0.640 * w, 0.845 * h, 0.024 * w, s)
        self._kettlebell(p, 0.715 * w, 0.885 * h, 0.030 * w, s)

    def _kettlebell(self, p, cx, cy, r, s):
        _sombra(p, cx, cy + r, r * 1.25, r * 0.22)
        p.save()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#141614"), 0.30 * r, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - 0.62 * r, cy - 1.45 * r, 1.24 * r, 1.7 * r), 0, 180 * 16)
        p.setPen(QPen(QColor(255, 255, 255, 40), 0.07 * r, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - 0.62 * r, cy - 1.45 * r, 1.24 * r, 1.7 * r), 40 * 16, 100 * 16)
        p.setPen(Qt.NoPen)
        cuerpo = _elipse(QRectF(cx - r, cy - r, 2 * r, 2 * r))
        g = QRadialGradient(QPointF(cx - 0.35 * r, cy - 0.4 * r), 1.7 * r)
        g.setColorAt(0.0, QColor("#3D413F"))
        g.setColorAt(0.45, QColor("#1A1D1B"))
        g.setColorAt(1.0, QColor("#050605"))
        p.fillPath(cuerpo, g)
        p.setBrush(QColor(255, 255, 255, 50))
        p.drawEllipse(QPointF(cx - 0.45 * r, cy - 0.5 * r), 0.22 * r, 0.12 * r)
        p.restore()

    def _cuerda(self, p, w, h, s):
        """Cuerda de batalla enrollada en el suelo: anillos gruesos con brillo."""
        cx, cy = 0.565 * w, 0.925 * h
        _sombra(p, cx, cy + 0.01 * h, 0.075 * w, 0.024 * h)
        p.save()
        p.setBrush(Qt.NoBrush)
        for i in range(5):
            k = 1 - i * 0.16
            caja = QRectF(cx - 0.07 * w * k, cy - 0.022 * h * k + i * 1.5 * s, 0.14 * w * k, 0.044 * h * k)
            p.setPen(QPen(QColor("#3A3F3A"), 0.0065 * w, Qt.SolidLine, Qt.RoundCap))
            p.drawEllipse(caja)
            p.setPen(QPen(QColor(255, 255, 255, 34), 1.6 * s, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(caja.adjusted(0.003 * w, 0.002 * h, -0.003 * w, -0.002 * h), 200 * 16, 100 * 16)
        p.restore()

    def _lamparas(self, p, sala, s):
        """Tres lámparas de campana: cable, campana con volumen, cono cálido y charco de luz en el suelo."""
        w, h = sala.w, sala.h
        for lf in LAMPARAS:
            x = lf * w
            p.save()
            p.setPen(QPen(QColor("#0B0C0B"), 2.2 * s))
            p.drawLine(QPointF(x, 0.108 * h), QPointF(x, 0.205 * h))
            p.restore()
            cono = _camino([QPointF(x - 0.034 * w, 0.245 * h), QPointF(x + 0.034 * w, 0.245 * h),
                            QPointF(x + 0.16 * w, 0.80 * h), QPointF(x - 0.16 * w, 0.80 * h)])
            g = QLinearGradient(0, 0.245 * h, 0, 0.80 * h)
            g.setColorAt(0, con_alfa(QColor("#FFE2B0"), 80))
            g.setColorAt(1, con_alfa(QColor("#FFE2B0"), 0))
            p.fillPath(cono, g)
            p.save()
            p.translate(x, 0.80 * h)
            p.scale(1, 0.25)
            self.brillo(p, 0, 0, 0.15 * w, QColor("#FFE2B0"), 70)
            p.restore()
            campana = QPainterPath(QPointF(x - 0.009 * w, 0.205 * h))
            campana.lineTo(QPointF(x + 0.009 * w, 0.205 * h))
            campana.cubicTo(QPointF(x + 0.012 * w, 0.215 * h), QPointF(x + 0.030 * w, 0.222 * h),
                            QPointF(x + 0.038 * w, 0.245 * h))
            campana.lineTo(QPointF(x - 0.038 * w, 0.245 * h))
            campana.cubicTo(QPointF(x - 0.030 * w, 0.222 * h), QPointF(x - 0.012 * w, 0.215 * h),
                            QPointF(x - 0.009 * w, 0.205 * h))
            campana.closeSubpath()
            p.save()
            p.setPen(Qt.NoPen)
            _volumen(p, campana, "#1E2120", 0.3, 0.6)
            p.setPen(QPen(QColor(255, 236, 200, 150), 1.5 * s))
            p.drawLine(QPointF(x - 0.038 * w, 0.245 * h), QPointF(x + 0.038 * w, 0.245 * h))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFF3D6"))
            p.drawEllipse(QPointF(x, 0.243 * h), 0.008 * w, 0.009 * h)
            p.restore()
            self.brillo(p, x, 0.246 * h, 0.09 * w, QColor("#FFE2B0"), 170)

    # ------------------------------------------------------------ sprites (se reconstruyen al cambiar tamaño/color)

    def _preparar_sprites(self, w, h, col, s):
        if self._clave_fijos != (w, h):
            self._barra = _sprite(w, h, 0.0, 0.30, 0.28, 0.54, lambda q: _dib_barra(q, w, h, s))
            self._saco = _sprite(w, h, 0.24, PIVOTE_SACO[1], 0.34, 0.70, lambda q: _dib_saco(q, w, h, s))
            self._clave_fijos = (w, h)
        clave = (w, h, col.name())
        if self._clave_neon != clave:
            self._neon = self._construir_neon(w, h, col, s)
            self._clave_neon = clave

    def _construir_neon(self, w, h, col, s):
        """Letrero «NO PAIN NO GAIN»: por letra, un sprite de halo (alfa 35, 14 px) y otro de medio (alfa 90, 6 px)
        y núcleo casi blanco (2 px). Así cada letra puede apagarse sola al parpadear."""
        lh = 0.052 * h                                   # altura de letra
        m = 18 * s                                       # margen del sprite (para el halo)
        base = 0.505 * h
        # avance de cada carácter y ancho total, para centrar el texto en la pared
        avances = [ESPACIO_PALABRA * lh if ch == " " else (ANCHO_GLIFO + ESPACIO_LETRA) * lh for ch in TEXTO_NEON]
        x = 0.5 * w - sum(avances) / 2
        nucleo = mezclar(QColor(col), QColor("#FFFFFF"), 0.85)
        nucleo.setAlpha(255)
        capas = []
        for ch, avance in zip(TEXTO_NEON, avances):
            if ch != " ":
                ancho = int(ANCHO_GLIFO * lh + 2 * m) + 2
                alto = int(lh + 2 * m) + 2
                trazo = _trazo_letra(ch, lh)
                halo = _pm_trazo(ancho, alto, m, 0.0, trazo, [(con_alfa(col, 35), 14 * s)])
                nuc = _pm_trazo(ancho, alto, m, 0.0, trazo, [(con_alfa(col, 90), 6 * s), (nucleo, 2 * s)])
                capas.append((QPointF(x - m, base - lh - m), halo, nuc))
            x += avance
        return capas

    # ------------------------------------------------------------ cada cuadro

    def _parpadeo(self, t):
        """Cada 6 a 9 s una letra del letrero parpadea (el apagado dura unos 0.45 s)."""
        if t >= self._prox_parpadeo and self._neon:
            self._parp_letra = self._rng_parp.randrange(len(self._neon))
            self._parp_ini = t
            self._prox_parpadeo = t + self._rng_parp.uniform(6.0, 9.0)

    def pintar_animado(self, p, w, h, t):
        s = h / 1080.0
        e = self.energia()
        col = self.acento()
        sala = _Sala(w, h)
        self._preparar_sprites(w, h, col, s)
        self._parpadeo(t)
        p.setRenderHint(QPainter.Antialiasing, True)

        # tiras LED: el zócalo y el borde superior del fondo respiran y se intensifican con la música
        zocalo = [sala.pared(0.5 * w, 1, -1), QPointF(sala.xl, sala.yb), QPointF(sala.xr, sala.yb),
                  sala.pared(0.5 * w, 1, 1)]
        borde = [QPointF(sala.xl, sala.yt), QPointF(sala.xr, sala.yt)]
        for desfase, pts in ((0.0, zocalo), (1.7, borde)):
            respira = 0.5 + 0.5 * math.sin(t * 0.9 + desfase)
            _tira(p, pts, col, min(1.0, 0.45 + 0.35 * respira + 0.6 * e), s)

        # letrero de neón: el halo zumba (ruido suave) y una letra se apaga un instante
        ruido = (math.sin(t * 5.3) + 0.6 * math.sin(t * 11.7 + 1.3) + 0.4 * math.sin(t * 23.1 + 0.4)) / 2.0
        op_halo = 0.82 + 0.18 * ruido
        fase = (t - self._parp_ini) / 0.45
        apagando = 0.0 <= fase < 1.0 and (0.15 <= fase < 0.25 or 0.35 <= fase < 0.42)
        for k, (pos, halo, nuc) in enumerate(self._neon):
            f = 0.2 if (apagando and k == self._parp_letra) else 1.0
            p.setOpacity(op_halo * f)
            p.drawPixmap(pos, halo)
            p.setOpacity(f)
            p.drawPixmap(pos, nuc)
        p.setOpacity(1.0)

        # barra sobre el rack: vibra 1 px con los golpes de la música
        vib = max(0.0, min(1.0, (e - 0.25) * 2.5))
        dy = int(round(vib * math.sin(t * 50.0)))
        pm, x0, y0 = self._barra
        p.drawPixmap(QPointF(x0, y0 + dy), pm)

        # saco de boxeo: péndulo alrededor de la cadena
        ang = 4.0 * math.sin(t * 1.3) + 3.0 * e
        pm, x0, y0 = self._saco
        px, py = PIVOTE_SACO[0] * w, PIVOTE_SACO[1] * h
        p.save()
        p.translate(px, py)
        p.rotate(ang)
        p.drawPixmap(QPointF(x0 - px, y0 - py), pm)
        p.restore()

        # polvo de tiza que flota dentro de los conos de luz
        p.save()
        p.setPen(Qt.NoPen)
        for li, u, y0_, vy, fase_, rad in self._polvo:
            yy = 0.245 + ((y0_ - t * vy) % 1.0) * 0.555           # fracción de h, de abajo arriba
            mitad = (0.034 + (0.16 - 0.034) * (yy - 0.245) / 0.555) * w
            xx = LAMPARAS[li] * w + (2 * u - 1) * mitad * 0.92 + 0.006 * w * math.sin(t * 0.5 + fase_)
            alfa = 30 + 50 * (0.5 + 0.5 * math.sin(t * 0.9 + fase_))
            p.setBrush(QColor(255, 240, 214, int(alfa)))
            p.drawEllipse(QPointF(xx, yy * h), rad * h, rad * h)
        p.restore()

        # música como pulso de ritmo en el monitor de la pared
        self.ondas(p, 0.30 * h, 0.34 * w, 0.08 * h, col, x0=0.33 * w, espejo=False, reflejo=False)
        p.setOpacity(1.0)
