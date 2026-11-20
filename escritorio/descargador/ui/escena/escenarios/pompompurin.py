# -*- coding: utf-8 -*-
"""Escenario Pompompurin: una pastelería acogedora por dentro, en la tarde dorada.

Solo es estética (amarillo crema, caramelo, flan, galletas, magdalenas, tartas, picnic de postres). No hay
personaje ni cara dibujados. `pintar_estatico` se pinta una vez y queda en caché: pared de azulejos, friso,
ventana con rayos de sol, pizarra con el menú escrito a mano, guirnalda, estantería de tarros, ganchos con
tazas, vitrina con postres en tres baldas, mostrador con frente de damero, flan grande en plato de porcelana
y taza de café con corazón. El flan grande se pre-renderiza en un QPixmap y en cada cuadro tiembla con una
cizalla alrededor de su base; el vapor, las motas de luz, los destellos del cristal, la gota de caramelo y las
ondas de la música se dibujan en `pintar_animado`.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QRadialGradient)

from .base import EscenarioBase, con_alfa, mezclar

LUZ = QColor("#FFF1C9")         # mezcla de la cara iluminada (30 %)
SOMBRA = QColor("#8B5A2B")      # mezcla de la cara en sombra (30 %)
CARAMELO_CLARO = QColor("#C97A34")
CARAMELO = QColor("#8B4513")
N_MOTAS = 80
N_RAYOS = 5
N_GRANO = 5000
# gotas de caramelo del flan: (posición horizontal relativa al ancho, largo relativo al alto)
GOTAS = ((-0.34, 0.20), (-0.25, 0.42), (-0.15, 0.14), (-0.05, 0.30), (0.05, 0.10), (0.16, 0.46),
         (0.27, 0.22), (0.35, 0.12))
# líneas verticales del layout (fracciones de h)
Y_PARED = 0.52          # friso de madera: 0.52 - 0.56
Y_MOSTRADOR = 0.70      # borde trasero del mostrador
Y_FRENTE = 0.78         # borde del frente: el frente ocupa el 22 % inferior
Y_FLAN = 0.735          # base del flan y centro del plato


# ---------------------------------------------------------------- utilidades de dibujo

def _c(color, alfa=255):
    return con_alfa(QColor(color), alfa)


def _volumen(p, camino, color, x0, x1):
    """Luz desde la izquierda: lado iluminado mezclado 30 % con LUZ, lado en sombra 30 % con SOMBRA."""
    c = QColor(color)
    g = QLinearGradient(x0, 0, x1, 0)
    g.setColorAt(0, mezclar(c, LUZ, 0.3))
    g.setColorAt(0.5, c)
    g.setColorAt(1, mezclar(c, SOMBRA, 0.3))
    p.fillPath(camino, g)


def _sombra_suave(p, camino, dx, dy):
    """Sombra proyectada suave: 4 pasadas de alfa 15 con desplazamiento creciente."""
    for k in range(1, 5):
        p.save()
        p.translate(dx * k / 4, dy * k / 4)
        p.fillPath(camino, QColor(70, 35, 10, 15))
        p.restore()


def _objeto(p, camino, color, sombra=None):
    """Objeto con volumen y, si `sombra` = (dx, dy), su sombra proyectada."""
    if sombra:
        _sombra_suave(p, camino, sombra[0], sombra[1])
    r = camino.boundingRect()
    _volumen(p, camino, color, r.left(), r.right())


def _caramelo(p, camino, y0, y1):
    g = QLinearGradient(0, y0, 0, y1)
    g.setColorAt(0, CARAMELO_CLARO)
    g.setColorAt(1, CARAMELO)
    p.fillPath(camino, g)


def _brillo_punto(p, x, y, rx, ry, alfa=220):
    """Reflejo especular: elipse blanca."""
    camino = QPainterPath()
    camino.addEllipse(QRectF(x - rx, y - ry, 2 * rx, 2 * ry))
    p.fillPath(camino, _c("#FFFFFF", alfa))


def _vetas(p, x0, x1, y0, y1, n, color, alfa, r):
    """Vetas de madera: líneas finas onduladas y horizontales entre y0 e y1."""
    p.save()
    p.setPen(QPen(_c(color, alfa), 1.2))
    p.setBrush(Qt.NoBrush)
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        fase = r.random() * 6.28
        amp = (y1 - y0) / n * 0.3
        pts = [QPointF(x0 + (x1 - x0) * i / 40, y + amp * math.sin(fase + i * 0.45)) for i in range(41)]
        p.drawPolyline(QPolygonF(pts))
    p.restore()


def _fuente_manuscrita(px):
    """Fuente de estilo a mano: Segoe Print, si no Comic Sans MS, si no Segoe UI cursiva."""
    familias = set(QFontDatabase.families())
    for nombre in ("Segoe Print", "Comic Sans MS"):
        if nombre in familias:
            f = QFont(nombre)
            f.setPixelSize(px)
            return f
    f = QFont("Segoe UI")
    f.setItalic(True)
    f.setPixelSize(px)
    return f


def _rayos(w, h):
    """Haces de sol que entran por la ventana: (inicio, fin) de cada uno."""
    return [((0.13 * w, (0.10 + 0.075 * k) * h), (0.43 * w, (0.62 + 0.075 * k) * h)) for k in range(N_RAYOS)]


# ---------------------------------------------------------------- forma del flan grande

def _cuerpo_flan(cx, fw, fh, base, ytop):
    """Flan clásico: base ancha con esquinas muy redondeadas, lados que se estrechan con una leve curva
    hacia fuera y cima abombada."""
    camino = QPainterPath(QPointF(cx - 0.38 * fw, base))
    camino.lineTo(QPointF(cx + 0.38 * fw, base))
    camino.quadTo(QPointF(cx + 0.50 * fw, base), QPointF(cx + 0.50 * fw, base - 0.14 * fh))
    camino.cubicTo(QPointF(cx + 0.51 * fw, base - 0.50 * fh), QPointF(cx + 0.40 * fw, ytop + 0.30 * fh),
                   QPointF(cx + 0.34 * fw, ytop + 0.08 * fh))
    camino.cubicTo(QPointF(cx + 0.24 * fw, ytop - 0.04 * fh), QPointF(cx - 0.24 * fw, ytop - 0.04 * fh),
                   QPointF(cx - 0.34 * fw, ytop + 0.08 * fh))
    camino.cubicTo(QPointF(cx - 0.40 * fw, ytop + 0.30 * fh), QPointF(cx - 0.51 * fw, base - 0.50 * fh),
                   QPointF(cx - 0.50 * fw, base - 0.14 * fh))
    camino.quadTo(QPointF(cx - 0.50 * fw, base), QPointF(cx - 0.38 * fw, base))
    camino.closeSubpath()
    return camino


def _cima_caramelo(cx, fw, fh, ytop):
    """Caramelo que solo cubre la cima y cae en gotas de largos distintos."""
    borde = ytop + 0.09 * fh
    camino = QPainterPath(QPointF(cx - 0.36 * fw, borde))
    camino.cubicTo(QPointF(cx - 0.42 * fw, ytop - 0.02 * fh), QPointF(cx - 0.20 * fw, ytop - 0.09 * fh),
                   QPointF(cx, ytop - 0.07 * fh))
    camino.cubicTo(QPointF(cx + 0.20 * fw, ytop - 0.09 * fh), QPointF(cx + 0.42 * fw, ytop - 0.02 * fh),
                   QPointF(cx + 0.36 * fw, borde))
    camino.closeSubpath()
    ancho_gota = 0.05 * fw
    for fx, largo in GOTAS:
        gota = QPainterPath()
        gota.addRoundedRect(QRectF(cx + fx * fw - ancho_gota / 2, borde - 0.04 * fh, ancho_gota,
                                   largo * fh + 0.04 * fh), ancho_gota / 2, ancho_gota / 2)
        camino = camino.united(gota)
    return camino


# ---------------------------------------------------------------- postres y objetos de la vitrina

def _flan_mini(p, x, base, rw, rh, sombra, vaso=False):
    """Flan individual en molde: cuerpo amarillo, caramelo marrón con brillo y una gotita por el lado."""
    top = base - rh
    cuerpo = QPainterPath()
    cuerpo.moveTo(x - rw, top)
    cuerpo.lineTo(x + rw, top)
    cuerpo.lineTo(x + rw * 0.8, base)
    cuerpo.lineTo(x - rw * 0.8, base)
    cuerpo.closeSubpath()
    _objeto(p, cuerpo, "#FFD45C", sombra)
    cara = QPainterPath()
    cara.addEllipse(QRectF(x - rw, top - rw * 0.25, 2 * rw, rw * 0.5))
    _caramelo(p, cara, top - rw * 0.25, top + rw * 0.25)
    _brillo_punto(p, x - rw * 0.35, top - rw * 0.04, rw * 0.22, rw * 0.07, 230)
    gota = QPainterPath()
    gota.addRoundedRect(QRectF(x + rw * 0.55, top, rw * 0.18, rh * 0.22), rw * 0.09, rw * 0.09)
    p.fillPath(gota, CARAMELO)
    if vaso:
        p.save()
        p.setPen(QPen(_c("#FFFFFF", 170), 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(x - rw * 1.08, top - rw * 0.3, rw * 2.16, rh + rw * 0.3 + 1), rw * 0.2, rw * 0.2)
        p.restore()


def _magdalena(p, x, base, rw, rh, sombra):
    """Magdalena con molde plisado, bizcocho en cúpula, crema en espiral y cereza."""
    top = base - rh * 0.42
    molde = QPainterPath()
    molde.moveTo(x - rw * 0.8, top)
    molde.lineTo(x + rw * 0.8, top)
    molde.lineTo(x + rw * 0.55, base)
    molde.lineTo(x - rw * 0.55, base)
    molde.closeSubpath()
    _objeto(p, molde, "#F2A56E", sombra)
    p.save()
    p.setPen(QPen(_c("#8B4513", 70), max(1.0, rw * 0.05)))
    for k in (-0.4, 0.0, 0.4):
        p.drawLine(QPointF(x + k * rw * 0.8, top), QPointF(x + k * rw * 0.55, base))
    p.restore()
    cupula = QPainterPath(QPointF(x - rw * 0.82, top))
    cupula.cubicTo(QPointF(x - rw * 0.9, top - rh * 0.5), QPointF(x + rw * 0.9, top - rh * 0.5),
                   QPointF(x + rw * 0.82, top))
    cupula.closeSubpath()
    _objeto(p, cupula, "#F3C98B")
    for k, a in enumerate((0.78, 0.6, 0.38)):
        yc = top - rh * (0.22 + 0.2 * k)
        b = rh * 0.22
        crema = QPainterPath(QPointF(x - a * rw, yc))
        crema.cubicTo(QPointF(x - a * rw, yc - b), QPointF(x + a * rw, yc - b), QPointF(x + a * rw, yc))
        crema.cubicTo(QPointF(x + a * rw * 0.5, yc + b * 0.35), QPointF(x - a * rw * 0.5, yc + b * 0.35),
                      QPointF(x - a * rw, yc))
        crema.closeSubpath()
        _objeto(p, crema, "#FFF6E8")
    cereza = QPainterPath()
    cereza.addEllipse(QRectF(x - rw * 0.18, top - rh * 0.82 - rw * 0.18, rw * 0.36, rw * 0.36))
    _objeto(p, cereza, "#D6334B")
    _brillo_punto(p, x - rw * 0.06, top - rh * 0.86, rw * 0.05, rw * 0.04, 230)


def _macarons(p, x, base, rw, colores, sombra):
    """Pila de macarons de colores pastel, cada uno con su relleno de crema."""
    alto = rw * 0.5
    for i, color in enumerate(colores):
        y = base - i * alto * 0.95 - alto
        disco = QPainterPath()
        disco.addRoundedRect(QRectF(x - rw, y, 2 * rw, alto), alto * 0.5, alto * 0.5)
        _objeto(p, disco, color, sombra if i == 0 else None)
        p.save()
        p.setPen(QPen(_c("#FFF6E8", 150), max(1.0, alto * 0.2)))
        p.drawLine(QPointF(x - rw * 0.7, y + alto * 0.5), QPointF(x + rw * 0.7, y + alto * 0.5))
        p.restore()


def _galletas(p, x, base, rc, sombra):
    """Tres galletas con gotas de chocolate, apiladas en la balda."""
    for dx, dy in ((-1.0, 1.0), (1.0, 1.0), (0.0, 2.9)):
        cx, cy = x + dx * rc, base - dy * rc
        redonda = QPainterPath()
        redonda.addEllipse(QPointF(cx, cy), rc, rc)
        _objeto(p, redonda, "#E3A65A", sombra if dy > 2 else None)
        for ang in (0.5, 2.1, 3.7, 5.2):
            gx = cx + math.cos(ang) * rc * 0.5
            gy = cy + math.sin(ang) * rc * 0.5
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(_c("#5A3520"))
            p.drawEllipse(QPointF(gx, gy), rc * 0.13, rc * 0.13)
            p.restore()


def _porcion(p, x, base, rw, rh, sombra):
    """Porción de tarta de capas: galleta abajo, crema, mermelada de fresa y bizcocho arriba."""
    cuna = QPainterPath()
    cuna.moveTo(x - rw, base)
    cuna.lineTo(x + rw, base)
    cuna.lineTo(x + rw * 0.55, base - rh)
    cuna.lineTo(x - rw * 0.55, base - rh)
    cuna.closeSubpath()
    _objeto(p, cuna, "#F2D7A8", sombra)
    p.save()
    p.setClipPath(cuna)
    p.fillRect(QRectF(x - rw, base - rh * 0.2, 2 * rw, rh * 0.2), _c("#C98A3E"))
    p.fillRect(QRectF(x - rw, base - rh * 0.5, 2 * rw, rh * 0.3), _c("#FFF1D0"))
    p.fillRect(QRectF(x - rw, base - rh * 0.58, 2 * rw, rh * 0.08), _c("#E8736B", 230))
    p.fillRect(QRectF(x - rw, base - rh, 2 * rw, rh * 0.42), _c("#F0C27A"))
    p.fillRect(QRectF(x - rw, base - rh, 2 * rw, rh * 0.1), _c("#FFF8EE"))
    p.restore()


def _tarta(p, x, base, rw, rh, sombra):
    """Tarta entera de tres capas, con fresas sobre la cúpula de crema."""
    cuerpo = QPainterPath()
    cuerpo.addRect(QRectF(x - rw, base - rh * 0.72, 2 * rw, rh * 0.72))
    tapa = QPainterPath()
    tapa.addEllipse(QRectF(x - rw, base - rh * 0.72 - rw * 0.2, 2 * rw, rw * 0.4))
    todo = cuerpo.united(tapa)
    _objeto(p, todo, "#E8B26A", sombra)
    p.save()
    p.setClipPath(todo)
    p.fillRect(QRectF(x - rw, base - rh * 0.45, 2 * rw, rh * 0.12), _c("#FFF1D0"))
    p.fillRect(QRectF(x - rw, base - rh * 0.18, 2 * rw, rh * 0.06), _c("#E8736B", 200))
    p.restore()
    p.fillPath(tapa, _c("#FFF6E0"))
    for k in range(4):
        fx = x + (k - 1.5) * rw * 0.55
        _brillo_punto(p, fx, base - rh * 0.72 - rw * 0.02, rw * 0.13, rw * 0.13, 255)
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(_c("#D6334B"))
        p.drawEllipse(QPointF(fx, base - rh * 0.72 - rw * 0.02), rw * 0.12, rw * 0.12)
        p.restore()


def _tarro(p, x, base, rw, rh, contenido, sombra):
    """Tarro de cristal con galletas o caramelos dentro y tapa de madera."""
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(QRectF(x - rw, base - rh, 2 * rw, rh), rw * 0.3, rw * 0.3)
    p.save()
    p.setClipPath(cuerpo)
    if contenido == "galletas":
        for k in range(3):
            p.setPen(Qt.NoPen)
            p.setBrush(_c("#D9963F"))
            p.drawEllipse(QPointF(x - rw * 0.5 + k * rw * 0.5, base - rh * (0.2 + 0.25 * (k % 2))),
                          rw * 0.42, rw * 0.42)
    else:
        for k, color in enumerate(("#FF9AA8", "#9FD8F0", "#FFE070", "#B8E6A0")):
            p.setPen(Qt.NoPen)
            p.setBrush(_c(color))
            p.drawEllipse(QPointF(x - rw * 0.5 + (k % 2) * rw, base - rh * (0.25 + 0.3 * (k // 2))),
                          rw * 0.3, rw * 0.3)
    p.restore()
    vidrio = QLinearGradient(x - rw, 0, x + rw, 0)
    vidrio.setColorAt(0, _c("#FFFFFF", 170))
    vidrio.setColorAt(0.5, _c("#FFF3D2", 90))
    vidrio.setColorAt(1, _c("#E8C98F", 170))
    p.fillPath(cuerpo, vidrio)
    p.save()
    p.setPen(QPen(_c("#FFFFFF", 200), max(1.0, rw * 0.15), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(x - rw * 0.62, base - rh * 0.85), QPointF(x - rw * 0.62, base - rh * 0.15))
    p.restore()
    tapa = QPainterPath()
    tapa.addRoundedRect(QRectF(x - rw * 1.08, base - rh - rh * 0.14, rw * 2.16, rh * 0.14), rw * 0.1, rw * 0.1)
    _objeto(p, tapa, "#9A6A3A", sombra)


def _corazon(p, x, y, s, color):
    """Corazón de espuma para el café con leche."""
    camino = QPainterPath(QPointF(x, y + 0.35 * s))
    camino.cubicTo(QPointF(x - 0.9 * s, y - 0.25 * s), QPointF(x - 0.45 * s, y - 0.75 * s),
                   QPointF(x, y - 0.25 * s))
    camino.cubicTo(QPointF(x + 0.45 * s, y - 0.75 * s), QPointF(x + 0.9 * s, y - 0.25 * s),
                   QPointF(x, y + 0.35 * s))
    camino.closeSubpath()
    p.fillPath(camino, _c(color))


def _dibujar_cafe(p, w, h, sombra):
    """Taza de café con leche con corazón en la espuma, sobre platito, y una cucharita plateada."""
    xc, yc = 0.925 * w, 0.745 * h
    rx, ry = 0.06 * w, 0.012 * w
    platito = QPainterPath()
    platito.addEllipse(QRectF(xc - rx, yc - ry, 2 * rx, 2 * ry))
    _objeto(p, platito, "#FFF8EE", (sombra[0] * 0.8, sombra[1]))
    p.save()
    p.setPen(QPen(_c("#5F86C0", 200), 1.2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(xc - rx * 0.92, yc - ry * 0.85, 2 * rx * 0.92, 2 * ry * 0.85))
    p.restore()

    cw, ch = 0.052 * w, 0.085 * h
    y_b = yc - 0.002 * h
    y_t = y_b - ch
    asa = QRectF(xc + cw * 0.36, y_t + ch * 0.22, cw * 0.42, ch * 0.42)
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(_c("#D8BD93", 230), cw * 0.13))
    p.drawEllipse(asa)
    p.setPen(QPen(_c("#FFF8EE"), cw * 0.09))
    p.drawEllipse(asa)
    p.restore()

    cuerpo = QPainterPath(QPointF(xc - cw / 2, y_t))
    cuerpo.lineTo(QPointF(xc + cw / 2, y_t))
    cuerpo.lineTo(QPointF(xc + cw * 0.36, y_b - ch * 0.12))
    cuerpo.quadTo(QPointF(xc + cw * 0.34, y_b), QPointF(xc + cw * 0.20, y_b))
    cuerpo.lineTo(QPointF(xc - cw * 0.20, y_b))
    cuerpo.quadTo(QPointF(xc - cw * 0.34, y_b), QPointF(xc - cw * 0.36, y_b - ch * 0.12))
    cuerpo.closeSubpath()
    _objeto(p, cuerpo, "#FFF8EE", (sombra[0] * 0.6, sombra[1] * 0.6))

    cafe = QPainterPath()
    cafe.addEllipse(QRectF(xc - cw / 2, y_t - cw * 0.18, cw, cw * 0.36))
    cg = QLinearGradient(xc - cw / 2, 0, xc + cw / 2, 0)
    cg.setColorAt(0, CARAMELO)
    cg.setColorAt(1, QColor("#C98B52"))
    p.fillPath(cafe, cg)
    _corazon(p, xc, y_t - cw * 0.02, cw * 0.13, "#FFF8EE")

    cuchara = QPainterPath()
    cuchara.addEllipse(QRectF(xc + 0.012 * w, yc + 0.002 * h, 0.016 * w, 0.011 * h))
    _objeto(p, cuchara, "#D9DEE3")
    p.save()
    p.setPen(QPen(_c("#B8BEC4"), max(1.5, 0.003 * h), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(xc + 0.020 * w, yc + 0.006 * h), QPointF(xc + 0.044 * w, yc + 0.012 * h))
    p.restore()


# ---------------------------------------------------------------- escenario

class EscenarioPompompurin(EscenarioBase):
    NOMBRE = "Pompompurin"
    ACENTO = "#FFD45C"
    SEMILLA = 21

    def preparar(self):
        r = self.rnd
        # motas de luz en los rayos: (rayo, posición a lo largo, desvío lateral, alfa, tamaño, fase, velocidad)
        self._motas = [(r.randrange(N_RAYOS), r.uniform(0.05, 1.0), r.uniform(-1.0, 1.0), r.randint(30, 100),
                        r.uniform(1.2, 3.0), r.random() * 6.28, r.uniform(0.2, 0.6)) for _ in range(N_MOTAS)]
        # destellos del cristal de la vitrina: (x, y relativos, periodo s, fase s)
        self._destellos = [(r.uniform(0.16, 0.52), r.uniform(0.28, 0.62), r.uniform(3.5, 6.0), r.uniform(0.0, 6.0))
                           for _ in range(6)]
        self._flan = None

    # ------------------------------------------------------------ geometría del flan

    @staticmethod
    def _geometria(w, h):
        fw = 0.20 * w
        fh = 0.6 * fw
        base = Y_FLAN * h
        return {"fw": fw, "fh": fh, "cx": 0.72 * w, "base": base, "ytop": base - fh}

    def _armar_flan(self, g):
        """Pre-renderiza el flan grande (cuerpo, caramelo, gotas, brillos) en un QPixmap transparente."""
        fw, fh, cx, base, ytop = g["fw"], g["fh"], g["cx"], g["base"], g["ytop"]
        sx, sy = cx - 0.62 * fw, ytop - 0.14 * fh
        ancho, alto = int(1.24 * fw) + 2, int(base + 0.02 * fh - sy) + 2
        pm = QPixmap(ancho, alto)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.translate(-sx, -sy)
            p.setPen(Qt.NoPen)

            cuerpo = _cuerpo_flan(cx, fw, fh, base, ytop)
            _objeto(p, cuerpo, "#FFD45C")
            abajo = QLinearGradient(0, ytop, 0, base)
            abajo.setColorAt(0, _c("#FFEFA0", 0))
            abajo.setColorAt(0.6, _c("#E4A23A", 0))
            abajo.setColorAt(1, _c("#E4A23A", 120))
            p.fillPath(cuerpo, abajo)

            # brillo especular curvo en el lado izquierdo del cuerpo
            curva = QPainterPath(QPointF(cx - 0.40 * fw, ytop + 0.30 * fh))
            curva.cubicTo(QPointF(cx - 0.46 * fw, ytop + 0.55 * fh), QPointF(cx - 0.44 * fw, base - 0.30 * fh),
                          QPointF(cx - 0.38 * fw, base - 0.16 * fh))
            p.save()
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(_c("#FFFFFF", 225), max(2.0, 0.022 * fw), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(curva)
            p.restore()
            _brillo_punto(p, cx - 0.42 * fw, ytop + 0.27 * fh, 0.012 * fw, 0.02 * fh, 255)

            cima = _cima_caramelo(cx, fw, fh, ytop)
            _caramelo(p, cima, ytop - 0.09 * fh, ytop + 0.62 * fh)
            _brillo_punto(p, cx - 0.20 * fw, ytop - 0.01 * fh, 0.08 * fw, 0.018 * fh, 230)
            for fx, largo in GOTAS:
                _brillo_punto(p, cx + fx * fw, ytop + 0.16 * fh + largo * fh - 0.01 * fh,
                              0.010 * fw, 0.012 * fh, 130)
        finally:
            p.end()
        return {"pm": pm, "sx": sx, "sy": sy, "g": g}

    # ------------------------------------------------------------ estático

    def pintar_estatico(self, p, w, h):
        r = random.Random(89)
        sh = (0.004 * w, 0.008 * h)
        p.save()
        self._pared(p, w, h, r)
        self._ventana(p, w, h, sh)
        self._pizarra(p, w, h, r, sh)
        self._guirnalda(p, w, h)
        self._estanteria(p, w, h, sh)
        self._ganchos(p, w, h, sh)
        self._vitrina(p, w, h, r, sh)
        self._mostrador(p, w, h, r, sh)
        g = self._geometria(w, h)
        self._plato(p, g, sh)
        self._flan = self._armar_flan(g)
        _dibujar_cafe(p, w, h, sh)
        self._lampara(p, w, h, sh)
        self._rayos_estatico(p, w, h)
        luz = QLinearGradient(0, 0, w, 0)
        luz.setColorAt(0, _c("#FFD89A", 50))
        luz.setColorAt(0.6, _c("#FFD89A", 0))
        luz.setColorAt(1, _c("#FFD89A", 0))
        p.fillRect(QRectF(0, 0, w, h), luz)
        self._grano_y_vineta(p, w, h, r)
        p.restore()

    def _pared(self, p, w, h, r):
        """Azulejos crema con juntas finas y friso de madera."""
        muro = QLinearGradient(0, 0, 0, Y_MOSTRADOR * h)
        muro.setColorAt(0, QColor("#FFF4D6"))
        muro.setColorAt(0.75, QColor("#FBE6B8"))
        muro.setColorAt(1, QColor("#F3D08E"))
        p.fillRect(QRectF(0, 0, w, Y_MOSTRADOR * h), muro)
        filas = 10
        alto_fila = Y_PARED * h / filas
        ancho = 0.05 * w
        p.save()
        p.setPen(QPen(_c("#C9A46A", 25), max(1.0, 0.0015 * w)))
        for k in range(filas + 1):
            y = k * alto_fila
            p.drawLine(QPointF(0, y), QPointF(w, y))
        for k in range(filas):
            off = (k % 2) * ancho / 2
            for i in range(-1, int(w / ancho) + 2):
                xx = i * ancho + off
                p.drawLine(QPointF(xx, k * alto_fila), QPointF(xx, (k + 1) * alto_fila))
        p.setPen(Qt.NoPen)
        for _ in range(60):
            x, y = r.uniform(0, w), r.uniform(0, Y_PARED * h)
            p.fillRect(QRectF(x, y, ancho * 0.9, alto_fila * 0.8), _c("#FFFFFF", 22))
        p.restore()

        friso = QRectF(0, Y_PARED * h, w, 0.04 * h)
        g = QLinearGradient(0, friso.top(), 0, friso.bottom())
        g.setColorAt(0, _c("#D89A5A"))
        g.setColorAt(1, _c("#A4663A"))
        p.fillRect(friso, g)
        _vetas(p, 0, w, friso.top(), friso.bottom(), 12, "#6E3F1C", 45, r)

    def _ventana(self, p, w, h, sh):
        """Ventana grande a la izquierda: de ella entra la luz dorada."""
        self.brillo(p, 0.13 * w, 0.28 * h, 0.45 * h, "#FFD89A", 110)
        marco = QRectF(0.03 * w, 0.07 * h, 0.10 * w, 0.43 * h)
        cristal = marco.adjusted(0.008 * w, 0.008 * w, -0.008 * w, -0.008 * w)
        vidrio = QLinearGradient(0, cristal.top(), 0, cristal.bottom())
        vidrio.setColorAt(0, _c("#FFF8E0"))
        vidrio.setColorAt(1, _c("#FFD89A"))
        p.fillRect(cristal, vidrio)
        p.save()
        p.setPen(QPen(_c("#8B5A2B"), max(2.0, 0.006 * w)))
        p.drawLine(QPointF(cristal.center().x(), cristal.top()), QPointF(cristal.center().x(), cristal.bottom()))
        p.drawLine(QPointF(cristal.left(), cristal.top() + cristal.height() * 0.45),
                   QPointF(cristal.right(), cristal.top() + cristal.height() * 0.45))
        p.restore()
        anillo = QPainterPath()
        anillo.addRect(marco)
        hueco = QPainterPath()
        hueco.addRect(cristal)
        _objeto(p, anillo.subtracted(hueco), "#A86B35", sh)
        alfeizar = QPainterPath()
        alfeizar.addRoundedRect(QRectF(0.02 * w, 0.50 * h, 0.12 * w, 0.012 * h), 0.003 * w, 0.003 * w)
        _objeto(p, alfeizar, "#B9824A", sh)
        _tarro(p, 0.05 * w, 0.50 * h, 0.011 * w, 0.05 * h, "galletas", None)
        _tarro(p, 0.09 * w, 0.50 * h, 0.011 * w, 0.045 * h, "caramelos", None)

    def _pizarra(self, p, w, h, r, sh):
        """Pizarra con el menú escrito con letra a mano (QFont) en tiza blanca."""
        marco = QRectF(0.58 * w, 0.10 * h, 0.19 * w, 0.24 * h)
        exterior = QPainterPath()
        exterior.addRoundedRect(marco, 0.006 * w, 0.006 * w)
        _objeto(p, exterior, "#A86B35", sh)
        interior = marco.adjusted(0.008 * w, 0.012 * h, -0.008 * w, -0.012 * h)
        pizarra = QPainterPath()
        pizarra.addRoundedRect(interior, 0.003 * w, 0.003 * w)
        g = QLinearGradient(0, interior.top(), 0, interior.bottom())
        g.setColorAt(0, QColor("#3A3A2E"))
        g.setColorAt(1, QColor("#2C2C22"))
        p.fillPath(pizarra, g)
        tinta = _c("#FFFFFF", 220)
        p.save()
        p.setPen(QPen(tinta))
        p.setFont(_fuente_manuscrita(max(10, int(0.031 * h))))
        x0 = interior.left() + 0.018 * w
        p.drawText(QPointF(x0, interior.top() + 0.042 * h), "Menú del día")
        p.setFont(_fuente_manuscrita(max(9, int(0.021 * h))))
        platos = (("Flan de caramelo", "3.50"), ("Café con leche", "2.80"),
                  ("Galletas", "1.50"), ("Tarta de fresa", "4.20"))
        for k, (nombre, precio) in enumerate(platos):
            y = interior.top() + (0.088 + 0.040 * k) * h
            p.drawText(QPointF(x0, y), nombre)
            p.drawText(QRectF(interior.right() - 0.07 * w, y - 0.03 * h, 0.05 * w, 0.04 * h),
                       Qt.AlignRight | Qt.AlignVCenter, precio)
        # dibujito de taza en la esquina inferior derecha
        tx, ty = interior.right() - 0.022 * w, interior.top() + 0.030 * h
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(tinta, max(1.2, 0.0015 * w), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        taza = QPainterPath(QPointF(tx - 0.008 * w, ty - 0.012 * h))
        taza.lineTo(QPointF(tx + 0.008 * w, ty - 0.012 * h))
        taza.quadTo(QPointF(tx + 0.008 * w, ty + 0.010 * h), QPointF(tx, ty + 0.010 * h))
        taza.quadTo(QPointF(tx - 0.008 * w, ty + 0.010 * h), QPointF(tx - 0.008 * w, ty - 0.012 * h))
        p.drawPath(taza)
        p.drawArc(QRectF(tx + 0.006 * w, ty - 0.006 * h, 0.006 * w, 0.010 * h), -90 * 16, 180 * 16)
        p.drawLine(QPointF(tx - 0.011 * w, ty + 0.011 * h), QPointF(tx + 0.011 * w, ty + 0.011 * h))
        vapor = QPainterPath(QPointF(tx - 0.002 * w, ty - 0.016 * h))
        vapor.cubicTo(QPointF(tx - 0.006 * w, ty - 0.020 * h), QPointF(tx + 0.002 * w, ty - 0.024 * h),
                      QPointF(tx - 0.001 * w, ty - 0.028 * h))
        p.drawPath(vapor)
        p.restore()
        p.save()
        p.setClipPath(pizarra)
        for _ in range(35):
            x, y = r.uniform(interior.left(), interior.right()), r.uniform(interior.top(), interior.bottom())
            p.fillRect(QRectF(x, y, 0.02 * w, 0.01 * h), _c("#FFFFFF", 9))
        p.restore()

    def _guirnalda(self, p, w, h):
        """Guirnalda de banderines amarillos y marrones colgada en lo alto de la pared."""
        cuerda = QPainterPath(QPointF(0, 0.03 * h))
        cuerda.quadTo(QPointF(0.5 * w, 0.10 * h), QPointF(w, 0.03 * h))
        p.save()
        p.setPen(QPen(_c("#8B5A2B", 170), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(cuerda)
        p.restore()
        colores = ("#FFD45C", "#B8733A", "#FFF1C9")
        n = 26
        for i in range(n):
            u = (i + 0.5) / n
            x = u * w
            y = 0.03 * h + 2 * u * (1 - u) * 0.07 * h
            banderin = QPainterPath()
            banderin.moveTo(x - 0.012 * w, y)
            banderin.lineTo(x + 0.012 * w, y)
            banderin.lineTo(x, y + 0.04 * h)
            banderin.closeSubpath()
            _objeto(p, banderin, colores[i % 3], (0.002 * w, 0.003 * h))

    def _estanteria(self, p, w, h, sh):
        """Estantería de la pared derecha con tarros de galletas y caramelos."""
        for k, yb in enumerate((0.20, 0.33, 0.46)):
            tabla = QPainterPath()
            tabla.addRect(QRectF(0.80 * w, yb * h, 0.18 * w, 0.008 * h))
            _objeto(p, tabla, "#B8733A", (0.003 * w, 0.006 * h))
            xs = (0.83, 0.865, 0.90, 0.935) if k < 2 else (0.83, 0.87, 0.91, 0.95)
            rh = (0.07, 0.06, 0.08)[k] * h
            for i, xf in enumerate(xs):
                contenido = "galletas" if (i + k) % 2 == 0 else "caramelos"
                _tarro(p, xf * w, yb * h, 0.013 * w, rh, contenido, None)

    def _ganchos(self, p, w, h, sh):
        """Varilla con tazas colgadas de ganchos, entre la pizarra y el flan."""
        vara = QRectF(0.60 * w, 0.37 * h, 0.16 * w, 0.006 * h)
        camino = QPainterPath()
        camino.addRect(vara)
        _objeto(p, camino, "#8B5A2B", sh)
        for xf, color in ((0.62, "#FFF8EE"), (0.66, "#F5C6C0"), (0.70, "#CFE3C4")):
            x = xf * w
            rw, rh = 0.012 * w, 0.034 * h
            top = vara.bottom() + 0.006 * h
            p.save()
            p.setPen(QPen(_c("#6B4A2A", 200), 1.2))
            p.drawLine(QPointF(x, vara.bottom()), QPointF(x, top))
            p.restore()
            p.save()
            p.setPen(QPen(_c(color, 255).darker(118), rw * 0.3))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(x + rw * 0.6, top + rh * 0.2, rw * 0.9, rh * 0.5))
            p.restore()
            cuerpo = QPainterPath()
            cuerpo.addRoundedRect(QRectF(x - rw, top, 2 * rw, rh), rw * 0.25, rw * 0.25)
            _objeto(p, cuerpo, color, (sh[0] * 0.5, sh[1] * 0.5))
            p.save()
            p.setPen(Qt.NoPen)
            p.setBrush(_c("#6B4A2A", 150))
            p.drawEllipse(QRectF(x - rw * 0.8, top + 0.001 * h, rw * 1.6, rh * 0.12))
            p.restore()

    def _vitrina(self, p, w, h, r, sh):
        """Vitrina de cristal grande sobre el mostrador, con postres en tres baldas."""
        x0, x1, y0, y1 = 0.12 * w, 0.58 * w, 0.20 * h, Y_MOSTRADOR * h
        exterior = QPainterPath()
        exterior.addRoundedRect(QRectF(x0 - 0.008 * w, y0, x1 - x0 + 0.016 * w, y1 - y0 + 0.008 * h),
                                0.004 * w, 0.004 * w)
        _objeto(p, exterior, "#A86B35", sh)
        interior = QRectF(x0 + 0.008 * w, y0 + 0.012 * h, x1 - x0 - 0.016 * w, y1 - y0 - 0.012 * h)
        fondo = QLinearGradient(interior.left(), 0, interior.right(), 0)
        fondo.setColorAt(0, _c("#FFF8E6"))
        fondo.setColorAt(1, _c("#F3D9A0"))
        p.fillRect(interior, fondo)

        bal = (0.41, 0.54, 0.665)
        for i, xf in enumerate((0.165, 0.23, 0.295, 0.36, 0.425, 0.49)):
            if i % 2 == 0:
                _flan_mini(p, xf * w, bal[0] * h, 0.020 * w, 0.07 * h, sh, vaso=True)
            else:
                _magdalena(p, xf * w, bal[0] * h, 0.021 * w, 0.085 * h, sh)
        _macarons(p, 0.18 * w, bal[1] * h, 0.018 * w, ("#F9C6D3", "#BDE4C8", "#C9C7F2"), sh)
        _galletas(p, 0.25 * w, bal[1] * h, 0.012 * w, sh)
        _porcion(p, 0.33 * w, bal[1] * h, 0.03 * w, 0.085 * h, sh)
        _macarons(p, 0.40 * w, bal[1] * h, 0.018 * w, ("#FFE3A3", "#F7B7A3", "#D6E8F7"), sh)
        _galletas(p, 0.47 * w, bal[1] * h, 0.012 * w, sh)
        _porcion(p, 0.53 * w, bal[1] * h, 0.028 * w, 0.085 * h, sh)
        _tarta(p, 0.20 * w, bal[2] * h, 0.042 * w, 0.09 * h, sh)
        _flan_mini(p, 0.31 * w, bal[2] * h, 0.025 * w, 0.06 * h, sh, vaso=True)
        _galletas(p, 0.39 * w, bal[2] * h, 0.012 * w, sh)
        _flan_mini(p, 0.46 * w, bal[2] * h, 0.025 * w, 0.06 * h, sh, vaso=True)
        _magdalena(p, 0.53 * w, bal[2] * h, 0.021 * w, 0.075 * h, sh)

        for yb in bal:
            p.fillRect(QRectF(interior.left(), yb * h, interior.width(), 0.006 * h), _c("#FFFFFF", 130))

        # cristal: velo blanco tenue y reflejo diagonal blanco alfa 40
        p.fillRect(interior, _c("#FFFFFF", 18))
        for ox, ancho_f in ((0.10, 0.07), (0.22, 0.025)):
            xa = interior.left() + ox * interior.width()
            reflejo = QPainterPath()
            reflejo.moveTo(xa, interior.top())
            reflejo.lineTo(xa + ancho_f * w, interior.top())
            reflejo.lineTo(xa + ancho_f * w - 0.10 * w, interior.bottom())
            reflejo.lineTo(xa - 0.10 * w, interior.bottom())
            reflejo.closeSubpath()
            p.fillPath(reflejo, _c("#FFFFFF", 40))

    def _mostrador(self, p, w, h, r, sh):
        """Mostrador de madera: tablero con vetas y brillo; frente decorado con festón, damero y zócalo."""
        tope = QPainterPath()
        tope.moveTo(0.03 * w, Y_MOSTRADOR * h)
        tope.lineTo(0.97 * w, Y_MOSTRADOR * h)
        tope.lineTo(w, Y_FRENTE * h)
        tope.lineTo(0, Y_FRENTE * h)
        tope.closeSubpath()
        g = QLinearGradient(0, Y_MOSTRADOR * h, 0, Y_FRENTE * h)
        g.setColorAt(0, _c("#E9B97C"))
        g.setColorAt(1, _c("#C98A4A"))
        p.fillRect(QRectF(0, Y_MOSTRADOR * h, w, (Y_FRENTE - Y_MOSTRADOR) * h), _c("#D9A463"))
        p.fillPath(tope, g)
        p.save()
        p.setClipPath(tope)
        _vetas(p, 0, w, Y_MOSTRADOR * h, Y_FRENTE * h, 6, "#8B5A2B", 45, r)
        self.brillo(p, 0.3 * w, 0.74 * h, 0.28 * w, "#FFF4D6", 90)
        p.restore()

        # frente: 22 % inferior de la pantalla
        y_top = Y_FRENTE * h
        frente = QRectF(0, y_top, w, h - y_top)
        gf = QLinearGradient(0, y_top, 0, h)
        gf.setColorAt(0, _c("#C98A4A"))
        gf.setColorAt(1, _c("#8B5A2B"))
        p.fillRect(frente, gf)
        # damero de azulejos pequeños crema y caramelo
        y_dam, alto_dam = 0.80 * h, 0.13 * h
        filas, cols = 4, int(w / (0.025 * w)) + 1
        ch = alto_dam / filas
        cw = w / cols
        p.save()
        p.setPen(QPen(_c("#8B5A2B", 70), 1.0))
        for j in range(filas):
            for i in range(cols):
                color = "#FFF4D6" if (i + j) % 2 == 0 else "#C97A34"
                celda = QRectF(i * cw, y_dam + j * ch, cw, ch)
                p.fillRect(celda, _c(color))
                p.drawRect(celda)
        p.restore()
        # festón: banda de caramelo con semicírculos colgando sobre el damero
        p.fillRect(QRectF(0, y_top, w, y_dam - y_top + 2), _c("#C97A34"))
        rs = 0.0125 * w
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(_c("#C97A34"))
        for i in range(int(w / (2 * rs)) + 2):
            p.drawEllipse(QPointF(i * 2 * rs, y_dam), rs, rs)
        p.restore()
        # zócalo de madera oscura
        zocalo = QRectF(0, 0.93 * h, w, 0.07 * h)
        gz = QLinearGradient(0, zocalo.top(), 0, zocalo.bottom())
        gz.setColorAt(0, _c("#6B4223"))
        gz.setColorAt(1, _c("#3E2411"))
        p.fillRect(zocalo, gz)
        _vetas(p, 0, w, zocalo.top(), zocalo.bottom(), 4, "#2A1808", 70, r)
        p.save()
        p.setPen(QPen(_c("#FFF1C9", 120), 1.5))
        p.drawLine(QPointF(0, zocalo.top()), QPointF(w, zocalo.top()))
        p.restore()

    def _plato(self, p, g, sh):
        """Plato de porcelana blanca con borde azul fino y la sombra suave del flan sobre él."""
        cx, base, fw = g["cx"], g["base"], g["fw"]
        plato = QPainterPath()
        plato.addEllipse(QRectF(cx - 0.66 * fw, base - 0.10 * fw, 1.32 * fw, 0.20 * fw))
        _objeto(p, plato, "#FFFBF0", (sh[0] * 1.5, sh[1] * 1.6))
        p.save()
        p.setPen(QPen(_c("#4F7CC0", 230), max(1.4, 0.0018 * fw)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - 0.64 * fw, base - 0.095 * fw, 1.28 * fw, 0.19 * fw))
        p.restore()
        hueco = QPainterPath()
        hueco.addEllipse(QRectF(cx - 0.50 * fw, base - 0.07 * fw, 1.00 * fw, 0.14 * fw))
        hg = QLinearGradient(0, base - 0.07 * fw, 0, base + 0.07 * fw)
        hg.setColorAt(0, _c("#FFFFFF", 200))
        hg.setColorAt(1, _c("#F5E4C0", 150))
        p.fillPath(hueco, hg)
        # sombra suave del flan sobre el plato
        base_sombra = QPainterPath()
        base_sombra.addEllipse(QRectF(cx - 0.52 * fw, base - 0.05 * fw, 1.04 * fw, 0.12 * fw))
        _sombra_suave(p, base_sombra, 0.05 * fw, 0.02 * fw)
        _sombra_suave(p, _cuerpo_flan(cx, fw, g["fh"], base, g["ytop"]), 0.03 * fw, 0.01 * fw)

    def _lampara(self, p, w, h, sh):
        """Lámpara colgante de campana: cable, campana de latón y cono de luz cálida."""
        cx = 0.5 * w
        p.save()
        p.setPen(QPen(_c("#6B4A2A", 200), max(1.5, 0.002 * w)))
        p.drawLine(QPointF(cx, 0), QPointF(cx, 0.10 * h))
        p.restore()
        y0, y1 = 0.10 * h, 0.165 * h
        campana = QPainterPath(QPointF(cx - 0.012 * w, y0))
        campana.cubicTo(QPointF(cx - 0.012 * w, y0 + 0.035 * h), QPointF(cx - 0.046 * w, y1 - 0.03 * h),
                        QPointF(cx - 0.046 * w, y1))
        campana.lineTo(QPointF(cx + 0.046 * w, y1))
        campana.cubicTo(QPointF(cx + 0.046 * w, y1 - 0.03 * h), QPointF(cx + 0.012 * w, y0 + 0.035 * h),
                        QPointF(cx + 0.012 * w, y0))
        campana.closeSubpath()
        _objeto(p, campana, "#E8B45A", (sh[0] * 0.8, sh[1] * 0.8))
        borde = QPainterPath()
        borde.addEllipse(QRectF(cx - 0.046 * w, y1 - 0.008 * h, 0.092 * w, 0.016 * h))
        _objeto(p, borde, "#B8843A")
        self.brillo(p, cx, y1 + 0.01 * h, 0.05 * w, "#FFF4D6", 200)
        cono = QPainterPath()
        cono.moveTo(cx - 0.046 * w, y1)
        cono.lineTo(cx + 0.046 * w, y1)
        cono.lineTo(cx + 0.24 * w, Y_MOSTRADOR * h)
        cono.lineTo(cx - 0.24 * w, Y_MOSTRADOR * h)
        cono.closeSubpath()
        gc = QLinearGradient(0, y1, 0, Y_MOSTRADOR * h)
        gc.setColorAt(0, _c("#FFF2C4", 95))
        gc.setColorAt(1, _c("#FFF2C4", 0))
        p.fillPath(cono, gc)

    def _rayos_estatico(self, p, w, h):
        """Rayos diagonales que bajan desde la ventana: polígonos con degradado de alfa 50 a 0."""
        for (sx, sy), (ex, ey) in _rayos(w, h):
            dx, dy = ex - sx, ey - sy
            largo = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / largo, dx / largo
            ancho0, ancho1 = 0.006 * h, 0.035 * h
            rayo = QPainterPath(QPointF(sx + nx * ancho0, sy + ny * ancho0))
            rayo.lineTo(QPointF(ex + nx * ancho1, ey + ny * ancho1))
            rayo.lineTo(QPointF(ex - nx * ancho1, ey - ny * ancho1))
            rayo.lineTo(QPointF(sx - nx * ancho0, sy - ny * ancho0))
            rayo.closeSubpath()
            g = QLinearGradient(sx, sy, ex, ey)
            g.setColorAt(0, _c("#FFF0C0", 50))
            g.setColorAt(1, _c("#FFF0C0", 0))
            p.fillPath(rayo, g)

    def _grano_y_vineta(self, p, w, h, r):
        """Grano de película (5000 puntos alfa 6) y viñeta cálida hacia #7A4A1E."""
        puntos = QPolygonF([QPointF(r.random() * w, r.random() * h) for _ in range(N_GRANO)])
        p.save()
        p.setPen(QPen(_c("#3A2010", 6), 1.0))
        p.drawPoints(puntos)
        p.restore()
        vineta = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w, h) / 2)
        vineta.setColorAt(0.55, _c("#7A4A1E", 0))
        vineta.setColorAt(1, _c("#7A4A1E", 90))
        p.fillRect(QRectF(0, 0, w, h), vineta)

    # ------------------------------------------------------------ animado

    def pintar_animado(self, p, w, h, t):
        e = self.energia()
        ac = self.acento()
        self._motas_luz(p, w, h, t, ac)
        self._destellos_cristal(p, w, h, t)
        self._vapor(p, w, h, t)
        self._flan_tembloroso(p, w, h, t, e)
        self.ondas(p, base_y=Y_FRENTE * h, ancho=w, alto_max=0.08 * h, color=self.acento())

    def _motas_luz(self, p, w, h, t, ac):
        """Motas doradas flotando dentro de los rayos de sol."""
        rayos = _rayos(w, h)
        tinte = mezclar(QColor("#FFE9A0"), ac, 0.25)
        p.save()
        p.setPen(Qt.NoPen)
        for k, u, lat, alfa, tam, ph, sp in self._motas:
            (sx, sy), (ex, ey) = rayos[k]
            dx, dy = ex - sx, ey - sy
            largo = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / largo, dx / largo
            desvio = (0.006 * h + 0.035 * h * u) * lat
            x = sx + dx * u + nx * desvio + 0.006 * w * math.sin(t * sp + ph)
            y = sy + dy * u + ny * desvio + 0.004 * h * math.cos(t * sp * 0.7 + ph)
            brillo = alfa * (0.55 + 0.45 * math.sin(t * 1.7 + ph))
            radio = tam * h / 1080.0
            p.setBrush(con_alfa(tinte, brillo))
            p.drawEllipse(QPointF(x, y), radio, radio)
        p.restore()

    def _destellos_cristal(self, p, w, h, t):
        """Destellos en el cristal de la vitrina: aparecen un instante y se apagan."""
        p.save()
        for xf, yf, periodo, fase in self._destellos:
            q = ((t + fase) % periodo) / periodo
            if q > 0.1:
                continue
            a = math.sin(math.pi * q / 0.1)
            x, y = xf * w, yf * h
            talla = 0.018 * h
            p.setPen(QPen(_c("#FFFFFF", int(230 * a)), max(1.2, 0.0025 * h)))
            p.drawLine(QPointF(x - talla, y), QPointF(x + talla, y))
            p.drawLine(QPointF(x, y - talla), QPointF(x, y + talla))
            self.brillo(p, x, y, 0.03 * h, "#FFFFFF", int(170 * a))
        p.restore()

    def _vapor(self, p, w, h, t):
        """Vapor del café: tres cintas curvas que suben y se mueven."""
        xc, y0 = 0.925 * w, (Y_FRENTE - 0.123) * h
        p.save()
        p.setBrush(Qt.NoBrush)
        for i in range(3):
            ox = (i - 1) * 0.011 * w
            ph = i * 2.1
            a1 = 0.010 * w * math.sin(t * 1.6 + ph)
            a2 = 0.012 * w * math.sin(t * 1.1 + ph + 1.0)
            a3 = 0.008 * w * math.sin(t * 1.9 + ph + 2.0)
            cinta = QPainterPath(QPointF(xc + ox, y0))
            cinta.cubicTo(QPointF(xc + ox + a1, y0 - 0.05 * h), QPointF(xc + ox - a2, y0 - 0.10 * h),
                          QPointF(xc + ox + a3, y0 - 0.15 * h))
            p.setPen(QPen(_c("#FFF8EE", 40), max(3.0, 0.003 * w), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(cinta)
            p.setPen(QPen(_c("#FFF8EE", 150), max(1.2, 0.0012 * w), Qt.SolidLine, Qt.RoundCap))
            p.drawPath(cinta)
        p.restore()

    def _flan_tembloroso(self, p, w, h, t, e):
        """El flan grande tiembla como gelatina (cizalla alrededor de su base) y gotea caramelo cada 3 s."""
        fl = self._flan
        if not fl:
            return
        g = fl["g"]
        cx, base, fw, fh, ytop = g["cx"], g["base"], g["fw"], g["fh"], g["ytop"]
        s = 0.02 * math.sin(t * 9) * e + 0.004 * math.sin(t * 3)
        escala = 1 - 0.015 * e
        p.save()
        p.translate(cx, base)
        p.shear(s, 0)
        p.scale(1, escala)
        p.translate(-cx, -base)
        p.drawPixmap(QPointF(fl["sx"], fl["sy"]), fl["pm"])
        q = (t % 3.0) / 3.0
        if q < 0.8:
            f = q / 0.8
            x = cx + 0.36 * fw
            y = ytop + (0.14 + 0.66 * f) * fh
            radio = 0.011 * fw
            p.setPen(Qt.NoPen)
            p.setBrush(_c("#8B4513", 235))
            p.drawEllipse(QPointF(x, y), radio, radio * (1 + 0.5 * f))
            p.setBrush(_c("#FFFFFF", 150))
            p.drawEllipse(QPointF(x - radio * 0.3, y - radio * 0.4), radio * 0.3, radio * 0.25)
        p.restore()
