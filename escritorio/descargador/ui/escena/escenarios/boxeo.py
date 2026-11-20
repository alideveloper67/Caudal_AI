# -*- coding: utf-8 -*-
"""Escenario «Boxeo»: pelea de título de noche en Las Vegas, con cara de póster de cine.

Estadio en penumbra con público en silueta y haz de focos, pantalla gigante con el ecualizador de la música,
ring en perspectiva con el logo en la lona, postes con esquineros y cuerdas. Lo estático se pinta una vez
(y se guarda en caché); lo animado usa sprites pre-renderizados para ir fluido: haces de luz que se balancean,
polvo en suspensión, destellos de cámara, cuerdas que vibran con la música, texto que late y confeti.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QRadialGradient, QTransform)

from .base import EscenarioBase, con_alfa, mezclar

ROJO = "#E11D2E"
ORO = ("#E8B923", "#FFD86B", "#F5F0E1")
FX, FY = 0.5, 0.42                          # punto de fuga (fracciones de w y h)
ESQ_CERCA = ((0.12, 0.92), (0.88, 0.92))    # esquinas del ring más cercanas (escala s = 1)
S_LEJOS = 0.36                              # escala de las esquinas del fondo del ring
ALTURA_POSTE = 0.22                         # alto del poste en escala 1 (fracción de h)
FRACCIONES_CUERDA = (0.35, 0.62, 0.88)      # altura de cada cuerda como fracción de la altura del poste
# cada lado une solo sus dos postes; de atrás hacia delante (el último queda por delante)
LADOS = (("fl", "fr"), ("nl", "fl"), ("nr", "fr"), ("nl", "nr"))
FOCOS = (0.20, 0.50, 0.80)                  # donde están los focos (fracción de w)
Y_LUZ = 0.075                               # altura de los focos en el truss (fracción de h)
Y_SUELO = 0.74                              # centro de la lona donde caen los haces
N_FILAS = 20
N_GRADERIA = 1400
N_LATERAL = 100
N_POLVO = 100
N_CONFETI = 40
N_LUCES_MOVIL = 60
LOGO_PX = 900


def _proy(x, y, s, w, h):
    """Proyecta (x, y) en píxeles hacia el punto de fuga con escala s (s < 1 = más lejos)."""
    fx, fy = FX * w, FY * h
    return QPointF(fx + (x - fx) * s, fy + (y - fy) * s)


def _esquinas(w, h):
    """Esquinas del ring en píxeles: nombre -> (punto, escala). Las del fondo salen del punto de fuga."""
    (xi, yi), (xd, yd) = ((x * w, y * h) for x, y in ESQ_CERCA)
    return {
        "nl": (QPointF(xi, yi), 1.0),
        "nr": (QPointF(xd, yd), 1.0),
        "fl": (_proy(xi, yi, S_LEJOS, w, h), S_LEJOS),
        "fr": (_proy(xd, yd, S_LEJOS, w, h), S_LEJOS),
    }


def _fuente(pixeles):
    """Tipografía en negrita; Segoe UI existe en Windows y evita los cuadritos de texto sin glifos."""
    f = QFont("Segoe UI")
    f.setBold(True)
    f.setPixelSize(max(8, int(pixeles)))
    return f


def _figura(p, x, y, r, col):
    """Silueta de persona: cabeza y hombros."""
    p.setBrush(col)
    p.drawEllipse(QPointF(x, y), r, r)
    p.drawPie(QRectF(x - 2.2 * r, y + 1.1 * r, 4.4 * r, 3.6 * r), 0, 180 * 16)


def _texto_en_arco(q, texto, c, tam, radio, arriba, color):
    """Escribe `texto` siguiendo un arco centrado en (c, c). Arriba: letras hacia fuera; abajo: hacia dentro."""
    f = _fuente(tam)
    q.setFont(f)
    q.setPen(QColor(color))
    fm = QFontMetrics(f)
    avances = [fm.horizontalAdvance(ch) for ch in texto]
    total = sum(avances)
    acumulado = 0.0
    for ch, a in zip(texto, avances):
        s = -total / 2 + acumulado + a / 2       # centro de la letra sobre el arco, en píxeles
        acumulado += a
        d = math.degrees(s / radio)
        if arriba:
            phi = 90.0 - d
            rot = 90.0 - phi
        else:
            phi = -90.0 + d
            rot = -(phi + 90.0)
        x = c + radio * math.cos(math.radians(phi))
        y = c - radio * math.sin(math.radians(phi))
        q.save()
        q.translate(x, y)
        q.rotate(rot)
        q.drawText(QPointF(-a / 2, 0), ch)
        q.restore()


def _construir_logo():
    """Logo circular del ring: disco oscuro, anillo rojo, «CAUDAL» arriba y placa de campeón en el centro."""
    L = LOGO_PX
    c = L / 2
    pm = QPixmap(L, L)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    try:
        q.setRenderHint(QPainter.Antialiasing, True)
        # disco crema con dos anillos rojos
        q.setPen(Qt.NoPen)
        q.setBrush(QColor("#F3EBDC"))
        q.drawEllipse(QPointF(c, c), c * 0.97, c * 0.97)
        q.setBrush(Qt.NoBrush)
        q.setPen(QPen(QColor(ROJO), L * 0.035))
        q.drawEllipse(QPointF(c, c), c * 0.93, c * 0.93)
        q.setPen(QPen(QColor(ROJO), L * 0.012))
        q.drawEllipse(QPointF(c, c), c * 0.84, c * 0.84)
        # textos siguiendo el arco: «CAUDAL» arriba, «TÍTULO MUNDIAL» abajo
        # letras grandes: en la lona se aplastan en vertical y, si no, no se leen
        tam = c * 0.20
        _texto_en_arco(q, "CAUDAL", c, tam, c * 0.60, arriba=True, color="#17151B")
        _texto_en_arco(q, "TÍTULO MUNDIAL", c, tam * 0.70, c * 0.80, arriba=False, color="#B3121F")
        # corona dorada pequeña en el centro: base, 5 puntas y 3 bolitas
        cy = c * 1.02
        oro = QLinearGradient(0, cy - 0.30 * c, 0, cy + 0.06 * c)
        oro.setColorAt(0, QColor("#FFF0B0"))
        oro.setColorAt(1, QColor("#B8860B"))
        q.setPen(QPen(QColor("#5C4300"), L * 0.004))
        q.setBrush(oro)
        puntos = [(-0.22, 0.06), (-0.22, -0.14), (-0.15, -0.06), (-0.10, -0.22), (-0.05, -0.06),
                  (0.0, -0.30), (0.05, -0.06), (0.10, -0.22), (0.15, -0.06), (0.22, -0.14), (0.22, 0.06)]
        q.drawPolygon(QPolygonF([QPointF(c + x * c, cy + y * c) for x, y in puntos]))
        q.setBrush(oro)
        for x, y in ((-0.22, -0.14), (0.0, -0.30), (0.22, -0.14)):
            q.drawEllipse(QPointF(c + x * c, cy + y * c), c * 0.03, c * 0.03)
    finally:
        q.end()
    return pm


class EscenarioBoxeo(EscenarioBase):
    NOMBRE = "Boxeo"
    ACENTO = "#E11D2E"
    SEMILLA = 47

    def preparar(self):
        r = self.rnd
        # polvo en la luz: (foco, posición a lo ancho, posición a lo alto, velocidad, radio, fase)
        self.polvo = [(r.randrange(len(FOCOS)), r.random(), r.random(), r.uniform(0.02, 0.05),
                       r.uniform(0.9, 1.8), r.uniform(0.0, 6.28)) for _ in range(N_POLVO)]
        # confeti: (x, y, velocidad de caída, tamaño, giro, fase, color)
        self._confeti = [(r.random(), r.random(), r.uniform(0.015, 0.035), r.uniform(0.005, 0.009),
                          r.uniform(-1.5, 1.5), r.uniform(0.0, 6.28), r.randrange(len(ORO)))
                         for _ in range(N_CONFETI)]
        self._proximo_destello = 1.2
        self._destello = None           # (x, y, instante)
        self._gente = []                # posiciones del público, para los destellos
        self._spr_clave = None
        self._cono = self._halo = self._texto = self._logo = None

    # ------------------------------------------------------------ sprites pre-renderizados

    def _asegurar(self, w, h):
        """Sprites que dependen del tamaño: se construyen una vez por resolución."""
        if self._spr_clave == (w, h):
            return
        # haz de luz: trapecio que se desvanece y cuyos bordes se suavizan con una máscara horizontal
        cw, ch = max(2, int(0.26 * w)), max(2, int(0.86 * h))
        cono = QPixmap(cw, ch)
        cono.fill(Qt.transparent)
        q = QPainter(cono)
        try:
            q.setRenderHint(QPainter.Antialiasing, True)
            base = QColor("#FFF6E0")
            g = QLinearGradient(0, 0, 0, ch)
            g.setColorAt(0, con_alfa(base, 120))
            g.setColorAt(0.5, con_alfa(base, 60))
            g.setColorAt(1, con_alfa(base, 0))
            pol = QPolygonF([QPointF(cw / 2 - 0.004 * w, 0), QPointF(cw / 2 + 0.004 * w, 0),
                             QPointF(cw, ch), QPointF(0, ch)])
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawPolygon(pol)
            q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            mascara = QLinearGradient(0, 0, cw, 0)
            mascara.setColorAt(0.0, QColor(0, 0, 0, 0))
            mascara.setColorAt(0.3, QColor(0, 0, 0, 255))
            mascara.setColorAt(0.7, QColor(0, 0, 0, 255))
            mascara.setColorAt(1.0, QColor(0, 0, 0, 0))
            q.fillRect(0, 0, cw, ch, mascara)
        finally:
            q.end()
        # mancha de luz donde el haz pega en la lona
        hw, hh = max(2, int(0.30 * w)), max(2, int(0.12 * h))
        halo = QPixmap(hw, hh)
        halo.fill(Qt.transparent)
        q = QPainter(halo)
        try:
            q.setRenderHint(QPainter.Antialiasing, True)
            q.translate(hw / 2, hh / 2)
            q.scale(1.0, hh / hw)
            g = QRadialGradient(QPointF(0, 0), hw / 2)
            g.setColorAt(0, con_alfa(QColor("#FFF2D0"), 130))
            g.setColorAt(0.5, con_alfa(QColor("#FFF2D0"), 45))
            g.setColorAt(1, con_alfa(QColor("#FFF2D0"), 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(0, 0), hw / 2, hw / 2)
        finally:
            q.end()
        # texto de la pantalla gigante
        f = _fuente(0.030 * h)
        s = "LAS VEGAS  ·  TÍTULO MUNDIAL"
        fm = QFontMetrics(f)
        tw, th = fm.horizontalAdvance(s) + 12, fm.height() + 8
        texto = QPixmap(tw, th)
        texto.fill(Qt.transparent)
        q = QPainter(texto)
        try:
            q.setRenderHint(QPainter.Antialiasing, True)
            q.setFont(f)
            q.setPen(QColor("#FFFFFF"))
            q.drawText(QRectF(0, 0, tw, th), Qt.AlignCenter, s)
        finally:
            q.end()
        self._cono, self._halo, self._texto = cono, halo, texto
        if self._logo is None:
            self._logo = _construir_logo()
        self._spr_clave = (w, h)

    # ------------------------------------------------------------ estático

    def _graderias(self, p, w, h):
        """Cinco franjas curvas del graderío: las de arriba más oscuras y más lejanas."""
        bases = (0.22, 0.28, 0.34, 0.40, 0.46)
        tonos = ("#0B090E", "#120F16", "#1A1620", "#221D2A", "#2B2533")
        p.setPen(Qt.NoPen)
        for base, tono in zip(bases, tonos):
            b, tp = base * h, (base - 0.075) * h
            camino = QPainterPath(QPointF(-0.04 * w, b))
            camino.quadTo(QPointF(0.5 * w, 2 * tp - b), QPointF(1.04 * w, b))
            camino.lineTo(QPointF(1.04 * w, b))
            camino.lineTo(QPointF(-0.04 * w, b))
            camino.closeSubpath()
            g = QLinearGradient(0, tp, 0, b)
            g.setColorAt(0, QColor(tono))
            g.setColorAt(1, mezclar(QColor(tono), QColor("#3A3346"), 0.35))
            p.setBrush(g)
            p.drawPath(camino)

    def _pantalla(self, p, w, h):
        """Pantalla gigante colgada sobre el ring: cubo con la cara frontal luminosa."""
        m = min(w, h)
        x0, x1, y0, y1 = 0.25 * w, 0.75 * w, 0.17 * h, 0.37 * h
        F = [QPointF(x0, y0), QPointF(x1, y0), QPointF(x1, y1), QPointF(x0, y1)]
        B = [_proy(q.x(), q.y(), 0.93, w, h) for q in F]
        p.setPen(Qt.NoPen)
        # caras laterales y la inferior (visible porque la cámara mira desde abajo)
        p.setBrush(QColor("#13307A"))
        p.drawPolygon(QPolygonF([F[3], F[2], B[2], B[3]]))
        p.setBrush(QColor("#0B1F4D"))
        p.drawPolygon(QPolygonF([F[0], F[3], B[3], B[0]]))
        p.drawPolygon(QPolygonF([F[1], F[2], B[2], B[1]]))
        # resplandor azulado alrededor
        self.brillo(p, 0.5 * w, 0.27 * h, 0.42 * w, "#2A6BFF", 70)
        # cara frontal
        g = QLinearGradient(0, y0, 0, y1)
        g.setColorAt(0, QColor("#1F5BD9"))
        g.setColorAt(1, QColor("#0A1C4F"))
        p.setBrush(g)
        p.drawPolygon(QPolygonF(F))
        # líneas de barrido del LED
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        for yy in range(int(y0), int(y1), 4):
            p.drawLine(QPointF(x0, yy), QPointF(x1, yy))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(127, 176, 255, 150), max(1.5, 0.003 * m)))
        p.drawPolygon(QPolygonF(F))

    def _truss(self, p, w, h):
        """Estructura de luces: dos largueros con celosía en zigzag y los focos."""
        m = min(w, h)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#4A4450"), max(2.0, 0.0035 * m)))
        y_a, y_b = 0.035 * h, 0.075 * h
        p.drawLine(QPointF(0.05 * w, y_a), QPointF(0.95 * w, y_a))
        p.drawLine(QPointF(0.05 * w, y_b), QPointF(0.95 * w, y_b))
        pts = []
        x = 0.05 * w
        arriba = True
        while x <= 0.95 * w:
            pts.append(QPointF(x, y_a if arriba else y_b))
            arriba = not arriba
            x += 0.03 * w
        p.setPen(QPen(QColor("#3A3440"), max(1.5, 0.0025 * m)))
        p.drawPolyline(QPolygonF(pts))
        p.setPen(Qt.NoPen)
        for sx in FOCOS:
            p.setBrush(QColor("#1E1B22"))
            p.drawRect(QRectF(sx * w - 0.018 * w, Y_LUZ * h - 0.012 * h, 0.036 * w, 0.024 * h))
            p.setBrush(QColor("#FFF2D0"))
            p.drawRect(QRectF(sx * w - 0.012 * w, Y_LUZ * h + 0.006 * h, 0.024 * w, 0.004 * h))

    def _sombra(self, p, w, h):
        """Sombra elíptica suave del ring sobre el suelo, bajo el faldón."""
        p.save()
        p.translate(0.5 * w, 0.93 * h)
        p.scale(1.0, (0.065 * h) / (0.45 * w))      # elipse: 0,9 w de ancho y 0,13 h de alto
        g = QRadialGradient(QPointF(0, 0), 0.45 * w)
        g.setColorAt(0.0, QColor(0, 0, 0, 170))
        g.setColorAt(0.6, QColor(0, 0, 0, 90))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(0, 0), 0.45 * w, 0.45 * w)
        p.restore()

    def _suelo(self, p, esq, w, h):
        """Lona: degradado radial, más clara bajo el foco."""
        poligono = QPolygonF([esq["nl"][0], esq["nr"][0], esq["fr"][0], esq["fl"][0]])
        g = QRadialGradient(QPointF(0.5 * w, Y_SUELO * h), 0.62 * w)
        g.setColorAt(0, QColor("#4A4652"))
        g.setColorAt(1, QColor("#1C1A22"))
        p.setPen(QPen(QColor("#0A090C"), 2))
        p.setBrush(g)
        p.drawPolygon(poligono)

    def _logo_en_lona(self, p, w, h):
        """El logo en perspectiva: el cuadrado del logo se deforma sobre el suelo con quadToQuad."""
        L = self._logo.width()
        cx = 0.5 * w
        origen = QPolygonF([QPointF(0, 0), QPointF(L, 0), QPointF(L, L), QPointF(0, L)])
        # logo subido y 15 % más plano: «TÍTULO MUNDIAL» queda por encima de la cuerda delantera
        y_lejos, y_cerca = 0.55 * h, 0.73 * h
        ancho_lejos = 0.195 * w * (y_lejos - FY * h) / (y_cerca - FY * h)
        destino = QPolygonF([QPointF(cx - ancho_lejos, y_lejos), QPointF(cx + ancho_lejos, y_lejos),
                             QPointF(cx + 0.195 * w, y_cerca), QPointF(cx - 0.195 * w, y_cerca)])
        t = QTransform()
        QTransform.quadToQuad(origen, destino, t)
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setTransform(t)
        p.drawPixmap(0, 0, self._logo)
        p.restore()

    def _faldon(self, p, esq, w, h):
        """Faldón del ring: cuerpo oscuro, banda roja y texto repetido en el lado frontal."""
        (nl, _), (nr, _), (fl, _), (fr, _) = esq["nl"], esq["nr"], esq["fl"], esq["fr"]
        oscuro = QColor("#14111A")
        p.setPen(Qt.NoPen)
        p.setBrush(oscuro)
        p.drawPolygon(QPolygonF([nl, nr, QPointF(nr.x(), nr.y() + 0.045 * h),
                                 QPointF(nl.x(), nl.y() + 0.045 * h)]))
        p.drawPolygon(QPolygonF([nl, fl, QPointF(fl.x(), fl.y() + 0.04 * h),
                                 QPointF(nl.x(), nl.y() + 0.045 * h)]))
        p.drawPolygon(QPolygonF([nr, fr, QPointF(fr.x(), fr.y() + 0.04 * h),
                                 QPointF(nr.x(), nr.y() + 0.045 * h)]))
        p.setBrush(QColor(ROJO))
        p.drawRect(QRectF(nl.x(), nl.y() + 0.010 * h, nr.x() - nl.x(), 0.018 * h))
        # bandas rojas de los laterales
        for a, b in ((nl, fl), (nr, fr)):
            p.drawPolygon(QPolygonF([QPointF(a.x(), a.y() + 0.010 * h), QPointF(b.x(), b.y() + 0.010 * h),
                                     QPointF(b.x(), b.y() + 0.020 * h), QPointF(a.x(), a.y() + 0.020 * h)]))
        f = _fuente(0.0155 * h)
        fm = QFontMetrics(f)
        frase = "CAUDAL  •  TÍTULO MUNDIAL  •  LAS VEGAS  •  "
        ancho = fm.horizontalAdvance(frase)
        p.save()
        p.setClipRect(QRectF(nl.x(), nl.y() + 0.010 * h, nr.x() - nl.x(), 0.018 * h))
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 220))
        x = nl.x() - 0.02 * w
        while x < nr.x():
            p.drawText(QPointF(x, nl.y() + 0.0235 * h), frase)
            x += ancho
        p.restore()

    def _postes(self, p, esq, w, h):
        """Cuatro postes cilíndricos con esquineros acolchados (rojo, azul y dos blancos)."""
        m = min(w, h)
        colores = {"nl": "#F2F2F5", "nr": "#F2F2F5", "fl": ROJO, "fr": "#1F4FD8"}
        for k in ("fl", "fr", "nl", "nr"):
            base, s = esq[k]
            wd = 0.0055 * m * (0.5 + 0.5 * s) * 2
            top = base.y() - ALTURA_POSTE * h * s
            g = QLinearGradient(base.x() - wd, 0, base.x() + wd, 0)
            g.setColorAt(0.0, QColor("#8A8A95"))
            g.setColorAt(0.5, QColor("#E8E8EF"))
            g.setColorAt(1.0, QColor("#6A6A75"))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#0A090C"))
            p.drawEllipse(QRectF(base.x() - 2 * wd, base.y() - 0.4 * wd, 4 * wd, 0.8 * wd))
            p.setBrush(g)
            p.drawRect(QRectF(base.x() - wd, top, 2 * wd, base.y() - top))
            pad = QColor(colores[k])
            p.setBrush(pad)
            p.drawRoundedRect(QRectF(base.x() - 2.5 * wd, top - 2.2 * wd, 5 * wd, 4.4 * wd), wd, wd)
            p.setBrush(con_alfa(QColor("#FFFFFF"), 70))
            p.drawRoundedRect(QRectF(base.x() - 2.0 * wd, top - 1.9 * wd, 2.2 * wd, 1.2 * wd), wd / 2, wd / 2)

    def _cuerdas(self, p, esq, w, h, t, en):
        """Tres cuerdas por lado en catenaria: sombra, rojo y brillo arriba. Con `t` vibran con la música."""
        m = min(w, h)
        p.setBrush(Qt.NoBrush)
        for li, (a_k, b_k) in enumerate(LADOS):
            (a, sa), (b, sb) = esq[a_k], esq[b_k]
            sm = (sa + sb) / 2
            for k, fr in enumerate(FRACCIONES_CUERDA):
                pa = QPointF(a.x(), a.y() - ALTURA_POSTE * h * sa * fr)
                pb = QPointF(b.x(), b.y() - ALTURA_POSTE * h * sb * fr)
                vib = 0.0
                if t is not None and en > 0:
                    vib = 0.004 * h * en * math.sin(t * 11 + k * 1.9 + li * 1.3)
                caida = (0.016 + 0.012 * en) * h * sm
                mid = QPointF((pa.x() + pb.x()) / 2, (pa.y() + pb.y()) / 2 + 2 * caida + vib)
                cuerda = QPainterPath(pa)
                cuerda.quadTo(mid, pb)
                p.setPen(QPen(QColor(20, 4, 8, 210), 0.016 * m, Qt.SolidLine, Qt.RoundCap))
                p.drawPath(cuerda)
                p.setPen(QPen(QColor("#C81E2B"), 0.0095 * m, Qt.SolidLine, Qt.RoundCap))
                p.drawPath(cuerda)
                p.save()
                p.translate(0, -0.0035 * m)
                p.setPen(QPen(QColor(255, 255, 255, 120), 0.0022 * m, Qt.SolidLine, Qt.RoundCap))
                p.drawPath(cuerda)
                p.restore()
                # separador blanco en el centro de la cuerda
                x = 0.25 * pa.x() + 0.5 * mid.x() + 0.25 * pb.x()
                y = 0.25 * pa.y() + 0.5 * mid.y() + 0.25 * pb.y()
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 235))
                p.drawRect(QRectF(x - 0.0055 * m, y - 0.009 * m, 0.011 * m, 0.018 * m))
                p.setBrush(Qt.NoBrush)

    def _publico_graderia(self, p, w, h, r):
        """Público de las graderías: filas de siluetas, más pequeñas y claras al alejarse."""
        p.setPen(Qt.NoPen)
        por_fila = N_GRADERIA // N_FILAS
        for fila in range(N_FILAS):
            f = fila / (N_FILAS - 1)                  # 0 = lejos (arriba), 1 = cerca (abajo)
            yf = 0.12 + 0.34 * f
            rad = h * (0.0040 + 0.0085 * f)
            col = mezclar(QColor("#2A2430"), QColor("#120F14"), f)
            for k in range(por_fila):
                x = (0.04 + 0.92 * (k + r.random()) / por_fila) * w
                y = (yf + r.uniform(-0.004, 0.004)) * h
                rr = rad * (0.85 + 0.3 * r.random())
                _figura(p, x, y, rr, col)
                self._gente.append((x, y, rr))

    def pintar_estatico(self, p, w, h):
        self._asegurar(w, h)
        m = min(w, h)
        r = random.Random(53)
        self._gente = []
        p.fillRect(0, 0, w, h, QColor("#07060A"))
        self.velo(p, QRectF(0, 0, w, h * 0.62), "#1B1218", "#07060A")
        self.brillo(p, 0.5 * w, 0.02 * h, 0.7 * w, "#5A1A22", 90)
        self._graderias(p, w, h)
        self._publico_graderia(p, w, h, r)
        # bruma sobre el público del fondo
        niebla = QLinearGradient(0, 0.08 * h, 0, 0.44 * h)
        niebla.setColorAt(0, con_alfa(QColor("#4A4358"), 150))
        niebla.setColorAt(1, con_alfa(QColor("#4A4358"), 0))
        p.fillRect(QRectF(0, 0.08 * h, w, 0.36 * h), niebla)
        # lucecitas de móviles
        p.setPen(Qt.NoPen)
        for _ in range(N_LUCES_MOVIL):
            x = r.uniform(0.05, 0.95) * w
            y = r.uniform(0.12, 0.44) * h
            p.setBrush(con_alfa(QColor("#FFF4D8"), r.randint(50, 110)))
            p.drawEllipse(QPointF(x, y), 0.0022 * h, 0.0022 * h)
        # público pegado a los lados del ring
        p.setPen(Qt.NoPen)
        for lado in range(2):
            for _ in range(N_LATERAL // 2):
                yf = 0.50 + 0.45 * r.random()
                xf = 0.10 * r.random() if lado == 0 else 0.90 + 0.10 * r.random()
                rr = h * (0.010 + 0.012 * (yf - 0.5) / 0.45)
                _figura(p, xf * w, yf * h, rr, QColor("#120F14"))
                self._gente.append((xf * w, yf * h, rr))
        self._pantalla(p, w, h)
        self._truss(p, w, h)
        esq = _esquinas(w, h)
        self._sombra(p, w, h)
        self._suelo(p, esq, w, h)
        self._logo_en_lona(p, w, h)
        self._faldon(p, esq, w, h)
        self._postes(p, esq, w, h)
        self._cuerdas(p, esq, w, h, None, 0.0)
        # humo iluminado en el centro, encima de todo
        self.brillo(p, 0.5 * w, 0.60 * h, 0.5 * w, "#A9A3B8", 36)
        self.brillo(p, 0.5 * w, 0.56 * h, 0.28 * w, "#C7C0D4", 30)
        self.brillo(p, 0.5 * w, 0.66 * h, 0.18 * w, "#D8D2E2", 26)
        # grano
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        granos = [QPointF(r.random() * w, r.random() * h) for _ in range(6000)]
        p.drawPoints(QPolygonF(granos))
        # viñeta
        viñeta = QRadialGradient(QPointF(0.5 * w, 0.48 * h), 0.75 * max(w, h))
        viñeta.setColorAt(0.55, QColor(0, 0, 0, 0))
        viñeta.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.fillRect(0, 0, w, h, viñeta)

    # ------------------------------------------------------------ animado

    def pintar_animado(self, p, w, h, t):
        self._asegurar(w, h)
        m = min(w, h)
        acento = self.acento()
        en = self.energia()
        # sin antialiasing en los haces, el polvo y las cuerdas: son los trazos más caros del cuadro
        p.setRenderHint(QPainter.Antialiasing, False)
        esq = _esquinas(w, h)
        # haces: un cono pre-renderizado por foco, rotado hacia la lona con un balanceo lento distinto
        haces = []
        for i, sx in enumerate(FOCOS):
            tx = 0.5 + (sx - 0.5) * 0.55 + 0.035 * math.sin(0.25 * t + i * 2.1)
            src = QPointF(sx * w, Y_LUZ * h)
            dst = QPointF(tx * w, Y_SUELO * h)
            haces.append((src, dst))
            dx, dy = dst.x() - src.x(), dst.y() - src.y()
            largo = math.hypot(dx, dy)
            angulo = -math.degrees(math.atan2(dx, dy)) + 2.0 * math.sin(0.23 * t + i * 2.1)
            p.save()
            p.setOpacity(0.8 + 0.2 * math.sin(0.9 * t + i))
            p.translate(src)
            p.rotate(angulo)
            p.scale(1.0, largo / self._cono.height())
            p.drawPixmap(QPointF(-self._cono.width() / 2, 0), self._cono)
            p.restore()
            self.brillo(p, src.x(), src.y(), 0.05 * h, "#FFE7B0", 150)
            p.save()
            p.setOpacity(0.55 + 0.25 * math.sin(1.3 * t + i))
            p.drawPixmap(QPointF(dst.x() - self._halo.width() / 2, dst.y() - self._halo.height() / 2),
                         self._halo)
            p.restore()
        # polvo que sube despacio dentro de los haces
        p.setPen(Qt.NoPen)
        escala = h / 1080.0
        for fi, u, y0, vel, rad, ph in self.polvo:
            yf = (y0 - vel * t) % 1.0
            src, dst = haces[fi]
            x = src.x() + (dst.x() - src.x()) * yf + (u - 0.5) * (0.02 + 0.16 * yf) * w
            x += 0.006 * w * math.sin(0.5 * t + ph)
            y = (Y_LUZ + yf * (Y_SUELO - Y_LUZ)) * h
            alfa = 30 + 60 * (0.5 + 0.5 * math.sin(1.1 * t + ph))
            p.setBrush(con_alfa(QColor("#FFF1D0"), alfa))
            rr = rad * escala
            p.drawEllipse(QPointF(x, y), rr, rr)
        # cuerdas que vibran con la música
        self._cuerdas(p, esq, w, h, t, en)
        # confeti dorado que cae a ratos
        ritmo = max(0.0, math.sin(0.19 * t + 0.4)) ** 2
        if ritmo > 0.02:
            for x0, y0, vel, sz, giro, ph, col in self._confeti:
                y = ((y0 + vel * t) % 1.0) * h
                x = (x0 + 0.015 * math.sin(0.6 * t + ph)) * w
                p.save()
                p.setOpacity(min(1.0, ritmo))
                p.translate(x, y)
                p.rotate(math.degrees(giro * t + ph))
                p.setBrush(QColor(ORO[col]))
                p.drawRect(QRectF(-sz * m / 2, -sz * m * 0.3, sz * m, sz * m * 0.6))
                p.restore()
        # pantalla gigante: ecualizador de la música y texto que late
        p.setRenderHint(QPainter.Antialiasing, True)
        self.ondas(p, 0.36 * h, 0.46 * w, 0.07 * h, acento, x0=0.27 * w)
        p.save()
        p.setOpacity(0.78 + 0.22 * math.sin(2.4 * t))
        p.translate(0.5 * w, 0.235 * h)
        sc = 1.0 + 0.015 * en
        p.scale(sc, sc)
        p.drawPixmap(QPointF(-self._texto.width() / 2, -self._texto.height() / 2), self._texto)
        p.restore()
        # destellos de cámara del público: como mucho uno cada 0,5 s, de 0,12 s
        if t >= self._proximo_destello and self._destello is None and self._gente:
            x, y, _rr = self._gente[self.rnd.randrange(len(self._gente))]
            self._destello = (x, y, t)
            self._proximo_destello = t + 0.5 + 2.5 * self.rnd.random()
        if self._destello is not None:
            x, y, t0 = self._destello
            edad = t - t0
            if 0 <= edad < 0.12:
                a = 1.0 - edad / 0.12
                self.brillo(p, x, y, 0.03 * h, "#FFFFFF", int(200 * a))
                p.setPen(Qt.NoPen)
                p.setBrush(con_alfa(QColor("#FFFFFF"), 255 * a))
                p.drawEllipse(QPointF(x, y), 0.0025 * h, 0.0025 * h)
            else:
                self._destello = None
