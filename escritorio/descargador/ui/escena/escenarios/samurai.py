# -*- coding: utf-8 -*-
"""Escenario «Japón samurái»: atardecer sobre un lago, pagoda, torii y cerezos en flor.

Lo estático (una vez, con todo el detalle): cielo, sol, tres cordilleras con niebla entre ellas, pagoda,
torii con su reflejo, lago, orilla, cerezos de ramas recursivas con racimos de flor, pétalos caídos, grano
de papel y viñeta. Lo animado (30 FPS, con sprites ya pintados): niebla que pasa sobre el lago, halo del sol
que late con la música, destellos en el agua, pétalos que caen y voltean, y las ondas del espectro sobre el
horizonte.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)

from .sakura import Cerezo, petalos_en_suelo
from .base import EscenarioBase, con_alfa, mezclar

HORIZONTE = 0.70                              # línea del lago (fracción de h)
SOL_X, SOL_Y, SOL_R = 0.62, 0.57, 0.09        # sol: x (de w), y (de h), radio (de h)
CIELO = [(0.00, "#1E1433"), (0.35, "#5B2E4F"), (0.60, "#C9666B"), (0.66, "#F2B07E"), (1.00, "#F2B07E")]
NEBLINA = "#F5CFA8"                           # color claro del cielo para las bandas de niebla
TINTA_PAGODA = "#1A1020"
TORII = "#A3262A"
CORTEZA = ("#2B1A1A", "#4A2C2A")
PETALO_ARRIBA, PETALO_ABAJO = "#FFD6E4", "#F28FB1"
ROSA_SOMBRA = "#B5577A"
ROSAS = ("#F2A7C3", "#F7B9CF", "#EE9AB8")
ROSA_LUZ = "#FFE4EE"
RACIMOS = 240                                 # racimos de flor en total (cada uno 18-30 círculos)


# ---------------------------------------------------------------- geometría y color

def _cielo_en(f):
    """Color del cielo a la altura f (fracción de h)."""
    f = max(0.0, min(1.0, f))
    for (fa, ca), (fb, cb) in zip(CIELO, CIELO[1:]):
        if f <= fb:
            k = (f - fa) / (fb - fa) if fb > fa else 0.0
            return mezclar(QColor(ca), QColor(cb), k)
    return QColor(CIELO[-1][1])


def crestas(x0, x1, y_base, amplitud, rugosidad=0.55, iteraciones=8, rnd=None):
    """Perfil de cresta por desplazamiento de punto medio: parte de 2 puntos e inserta en cada paso el
    punto medio con y += uniform(-amp, amp), y amp *= rugosidad."""
    if rnd is None:
        rnd = random.Random(0)
    pts = [[x0, y_base + rnd.uniform(-amplitud, amplitud) * 0.5],
           [x1, y_base + rnd.uniform(-amplitud, amplitud) * 0.5]]
    amp = amplitud
    for _ in range(iteraciones):
        nuevos = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            nuevos.append([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + rnd.uniform(-amp, amp)])
            nuevos.append(b)
        pts = nuevos
        amp *= rugosidad
    return [QPointF(x, y) for x, y in pts]


def _hundir(pts, w, cx, ancho, y_min):
    """Empuja la cresta hacia y_min con una campana gaussiana centrada en cx (fracción de w): un valle suave
    donde el sol se pone y queda a medias detrás de la cordillera."""
    for q in pts:
        fx = q.x() / w
        f = math.exp(-((fx - cx) / ancho) ** 2)
        q.setY(q.y() + max(0.0, y_min - q.y()) * f)


def _altura(pts, x):
    """Y del perfil `pts` en la coordenada x."""
    for a, b in zip(pts, pts[1:]):
        if a.x() <= x <= b.x():
            f = (x - a.x()) / (b.x() - a.x()) if b.x() > a.x() else 0.0
            return a.y() + (b.y() - a.y()) * f
    return pts[-1].y()


def _camino_montana(pts, h):
    """Silueta cerrada por abajo (hasta h) del perfil de cresta."""
    camino = QPainterPath(QPointF(pts[0].x(), h))
    for q in pts:
        camino.lineTo(q)
    camino.lineTo(pts[-1].x(), h)
    camino.closeSubpath()
    return camino


def _llenar_montana(p, camino, color_cresta, color_base, y_top, h):
    g = QLinearGradient(0, y_top, 0, h)
    g.setColorAt(0, color_cresta)
    g.setColorAt(1, color_base)
    p.fillPath(camino, QBrush(g))


def _banda_niebla(p, w, y, alto, alfa):
    """Franja de niebla: alfa 0 -> alfa -> 0 en vertical, con el color claro del cielo."""
    g = QLinearGradient(0, y, 0, y + alto)
    g.setColorAt(0, con_alfa(QColor(NEBLINA), 0))
    g.setColorAt(0.5, con_alfa(QColor(NEBLINA), alfa))
    g.setColorAt(1, con_alfa(QColor(NEBLINA), 0))
    p.fillRect(QRectF(0, y, w, alto), g)


# ---------------------------------------------------------------- formas de la escena

def _pagoda(p, xc, yb, s, color, ventanas=True):
    """Pagoda de 5 pisos. Cada piso es 82 % del de abajo; tejado con aleros curvos hacia arriba; flecha con
    anillos. `s` es la escala (alto de referencia)."""
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    ye = yb                                    # base del piso actual
    for k in range(5):
        f = 0.82 ** k
        hw = s * 0.20 * f                      # medio ancho del cuerpo
        cuerpo = s * 0.13 * f                  # alto del cuerpo
        hr = s * 0.07 * f                      # alto del tejado
        R = hw * 1.55                          # punta del alero
        y_alero = ye - cuerpo
        p.drawRect(QRectF(xc - hw, y_alero, 2 * hw, cuerpo))
        cumbre = y_alero - hr
        punta = y_alero - hr * 0.55            # la punta de los aleros se curva hacia arriba
        tejado = QPainterPath(QPointF(xc - R, punta))
        tejado.quadTo(QPointF(xc - hw * 1.05, cumbre + hr * 0.10), QPointF(xc - hw * 0.45, cumbre))
        tejado.lineTo(QPointF(xc + hw * 0.45, cumbre))
        tejado.quadTo(QPointF(xc + hw * 1.05, cumbre + hr * 0.10), QPointF(xc + R, punta))
        tejado.lineTo(QPointF(xc + R * 0.92, y_alero + hr * 0.12))
        tejado.lineTo(QPointF(xc - R * 0.92, y_alero + hr * 0.12))
        tejado.closeSubpath()
        p.drawPath(tejado)
        if ventanas and k in (1, 3) and color.alpha() == 255:
            p.setBrush(QColor(255, 176, 112, 160))
            for j in (-1, 0, 1):
                vx = xc + j * hw * 0.45
                p.drawRect(QRectF(vx - hw * 0.12, y_alero + cuerpo * 0.30, hw * 0.24, cuerpo * 0.38))
            p.setBrush(color)
        ye = cumbre + hr * 0.15                # el piso siguiente se apoya sobre el tejado
    # flecha: mástil fino con tres anillos y remate
    p.drawRect(QRectF(xc - s * 0.006, ye - s * 0.36, s * 0.012, s * 0.36))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(color, max(1.0, s * 0.012)))
    for i in range(3):
        p.drawEllipse(QPointF(xc, ye - s * (0.07 + 0.09 * i)), s * 0.030 * (1 - 0.18 * i), s * 0.010)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(xc, ye - s * 0.36), s * 0.022, s * 0.022)


def _torii(p, xc, yb, w, h, color):
    """Torii: viga superior curvada con las puntas levantadas, travesaño recto y dos columnas ahusadas."""
    yt = yb - 0.13 * h
    anc = 0.065 * w
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    viga = QPainterPath(QPointF(xc - anc, yt - 0.035 * h))
    viga.quadTo(QPointF(xc, yt - 0.005 * h), QPointF(xc + anc, yt - 0.035 * h))
    viga.lineTo(QPointF(xc + anc * 1.02, yt - 0.018 * h))
    viga.quadTo(QPointF(xc, yt + 0.010 * h), QPointF(xc - anc * 1.02, yt - 0.018 * h))
    viga.closeSubpath()
    p.drawPath(viga)
    p.drawRect(QRectF(xc - anc * 0.84, yt + 0.030 * h, anc * 1.68, 0.014 * h))
    cw = 0.011 * w
    for sgn in (-1, 1):
        cx = xc + sgn * anc * 0.72
        p.drawPolygon(QPolygonF([QPointF(cx - cw * 0.5, yt + 0.02 * h), QPointF(cx + cw * 0.5, yt + 0.02 * h),
                                 QPointF(cx + cw * 0.62, yb), QPointF(cx - cw * 0.62, yb)]))


def _forma_petalo():
    """Pétalo en coordenadas de -0.5 a 0.5: gota con muesca en la punta (dos curvas cúbicas por lado)."""
    c = QPainterPath(QPointF(0, 0.45))
    c.cubicTo(QPointF(0.5, 0.2), QPointF(0.5, -0.4), QPointF(0.12, -0.5))
    c.cubicTo(QPointF(0.05, -0.3), QPointF(-0.05, -0.3), QPointF(-0.12, -0.5))
    c.cubicTo(QPointF(-0.5, -0.4), QPointF(-0.5, 0.2), QPointF(0, 0.45))
    return c


def _rama(p, x, y, ang, largo, grosor, nivel, r, relleno, borde, flores):
    """Rama recursiva: curva cuadrática con punto de control desplazado, polígono ahusado (grosor inicial
    `grosor`, final 68 %) con corteza y un borde de luz a la izquierda. Los extremos de nivel >= 4 son flores."""
    a = math.radians(ang)
    dx, dy = math.cos(a), -math.sin(a)
    fx, fy = x + dx * largo, y + dy * largo
    desv = r.uniform(-0.15, 0.15) * largo
    cx = (x + fx) / 2 - dy * desv
    cy = (y + fy) / 2 + dx * desv
    izq, der = [], []
    n = 8
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        bx = u * u * x + 2 * u * t * cx + t * t * fx
        by = u * u * y + 2 * u * t * cy + t * t * fy
        tx = 2 * u * (cx - x) + 2 * t * (fx - cx)
        ty = 2 * u * (cy - y) + 2 * t * (fy - cy)
        L = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / L, tx / L
        if nx > 0:                             # la normal siempre apunta a la izquierda
            nx, ny = -nx, -ny
        mitad = grosor * (1 - 0.32 * t) / 2
        izq.append(QPointF(bx + nx * mitad, by + ny * mitad))
        der.append(QPointF(bx - nx * mitad, by - ny * mitad))
    p.setPen(Qt.NoPen)
    p.setBrush(relleno)
    p.drawPolygon(QPolygonF(izq + der[::-1]))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(borde, max(0.8, grosor * 0.06), Qt.SolidLine, Qt.RoundCap))
    p.drawPolyline(QPolygonF(izq))
    if nivel >= 4:
        flores.append(QPointF(fx, fy))
    if nivel < 7:
        if r.random() < 0.5:
            angs = [ang - r.uniform(18, 38), ang + r.uniform(18, 38)]
        else:
            angs = [ang - r.uniform(18, 38), ang + r.uniform(-6, 6), ang + r.uniform(18, 38)]
        for an in angs:
            _rama(p, fx, fy, an, largo * r.uniform(0.68, 0.82), grosor * 0.68, nivel + 1,
                  r, relleno, borde, flores)


def _racimos(p, flores, w, r):
    """Racimos de 18-30 círculos por punto de flor: primero todas las sombras, luego los medios, y las luces
    solo en la mitad superior-izquierda de cada racimo."""
    circulos = []
    for f in flores:
        fx, fy = f.x(), f.y()
        for _ in range(r.randint(18, 30)):
            ang = r.uniform(0, 2 * math.pi)
            d = 0.03 * w * math.sqrt(r.random())
            x, y = fx + math.cos(ang) * d, fy + math.sin(ang) * d
            rad = r.uniform(0.004, 0.011) * w
            circulos.append((x, y, rad, r.randrange(3), x < fx and y < fy))
    p.setPen(Qt.NoPen)
    p.setBrush(con_alfa(QColor(ROSA_SOMBRA), 200))
    for x, y, rad, _k, _luz in circulos:
        p.drawEllipse(QPointF(x, y + 2), rad, rad)
    medios = [QColor(c) for c in ROSAS]
    for x, y, rad, k, _luz in circulos:
        p.setBrush(medios[k])
        p.drawEllipse(QPointF(x, y), rad, rad)
    p.setBrush(con_alfa(QColor(ROSA_LUZ), 220))
    for x, y, rad, _k, luz in circulos:
        if luz:
            p.drawEllipse(QPointF(x - rad * 0.15, y - rad * 0.15), rad * 0.6, rad * 0.6)


class EscenarioSamurai(EscenarioBase):
    NOMBRE = "Japón samurái"
    ACENTO = "#E63946"
    SEMILLA = 21

    def preparar(self):
        r = self.rnd
        self._sprites, self._sprites_h = [], None
        self._niebla, self._niebla_clave = [], None
        # pétalos: (x0, y0, caída, deriva, amp. balanceo, frec. balanceo, fase, giro, frec. volteo, sprite)
        self.petalos = []
        for _ in range(70):
            self.petalos.append((
                r.random(), r.random(),
                r.uniform(0.03, 0.06),
                r.uniform(0.005, 0.02),
                r.uniform(0.01, 0.03),
                r.uniform(0.6, 1.6),
                r.uniform(0.0, 6.28),
                r.uniform(0.4, 1.2) * r.choice((-1, 1)),
                r.uniform(0.8, 1.8),
                r.randrange(4),
            ))
        # destellos en el agua: (x, y, largo, alfa, fase, frecuencia)
        self.destellos = [(r.uniform(0.40, 0.90), r.uniform(0.72, 0.98), r.uniform(0.03, 0.09),
                           r.randint(110, 220), r.uniform(0.0, 6.28), r.uniform(0.7, 1.8))
                          for _ in range(40)]

    # ------------------------------------------------------------ estático

    def pintar_estatico(self, p, w, h):
        r = random.Random(17)
        p.setRenderHint(QPainter.Antialiasing, True)
        yh = HORIZONTE * h

        # cielo al atardecer
        cielo = QLinearGradient(0, 0, 0, h)
        for f, c in CIELO:
            cielo.setColorAt(f, QColor(c))
        p.fillRect(QRectF(0, 0, w, h), QBrush(cielo))

        # estrellas muy tenues, solo en el cuarto superior
        p.setPen(Qt.NoPen)
        for _ in range(40):
            rad = r.uniform(0.8, 1.8) * h / 1080
            p.setBrush(QColor(255, 236, 214, r.randint(40, 110)))
            p.drawEllipse(QPointF(r.uniform(0, w), r.uniform(0, 0.25 * h)), rad, rad)

        # sol hundiéndose: halo y disco
        sx, sy, sr = SOL_X * w, SOL_Y * h, SOL_R * h
        self.brillo(p, sx, sy, 0.35 * h, "#FFB27A", 120)
        disco = QRadialGradient(QPointF(sx, sy), sr)
        disco.setColorAt(0, QColor("#FFE3B0"))
        disco.setColorAt(1, QColor("#FF9A6B"))
        p.setBrush(QBrush(disco))
        p.drawEllipse(QPointF(sx, sy), sr, sr)

        # tres cordilleras, de lejos a cerca; cada color mezclado con el cielo a su altura
        capas = [(0.46, 0.10, "#5A3B5E", 0.60),
                 (0.58, 0.07, "#3E2846", 0.40),
                 (0.66, 0.045, "#261A2E", 0.15)]
        perfiles, siluetas = [], []
        for i, (yb, amp, color, f) in enumerate(capas):
            pts = crestas(-0.02 * w, 1.02 * w, yb * h, amp * h, rnd=r)
            if i == 0:
                _hundir(pts, w, SOL_X, 0.10, 0.60 * h)
            base = mezclar(QColor(color), _cielo_en(yb), f)
            cresta = mezclar(base, _cielo_en(yb - amp * 0.5), 0.12)
            camino = _camino_montana(pts, h)
            _llenar_montana(p, camino, cresta, base, min(q.y() for q in pts), h)
            perfiles.append(pts)
            siluetas.append((camino, base))
            if i == 0:
                _banda_niebla(p, w, 0.55 * h, 0.10 * h, 90)
            elif i == 1:
                # pagoda sobre la colina media
                xp = 0.545 * w
                yp = _altura(perfiles[1], xp)
                _pagoda(p, xp, yp, 0.13 * h, QColor(TINTA_PAGODA))
                _banda_niebla(p, w, 0.64 * h, 0.07 * h, 70)

        # lago: degradado oscuro y las montañas volteadas bajo el horizonte
        lago = QRectF(0, yh, w, h - yh)
        g = QLinearGradient(0, yh, 0, h)
        g.setColorAt(0, QColor("#3A2440"))
        g.setColorAt(1, QColor("#120A16"))
        p.fillRect(lago, QBrush(g))
        p.save()
        p.setClipRect(lago)
        p.translate(0, 2 * yh)
        p.scale(1, -1)
        for camino, base in siluetas:
            p.fillPath(camino, con_alfa(base, 90))
        _pagoda(p, 0.545 * w, _altura(perfiles[1], 0.545 * w), 0.13 * h,
                con_alfa(QColor(TINTA_PAGODA), 70), False)
        p.restore()

        # columna de reflejo del sol: trazos dorados cortos, más densos cerca del horizonte
        for _ in range(70):
            fr = r.random() ** 1.4
            y = yh + 0.005 * h + (h - yh) * fr * 0.97
            L = r.uniform(0.02, 0.05) * w * (1.2 - fr)
            x = sx + r.gauss(0, 0.012 * w) * (1 + fr)
            p.setPen(QPen(QColor(255, 213, 138, r.randint(120, 220)),
                          max(1.5, 0.0035 * h) * (1 - 0.4 * fr), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x - L / 2, y), QPointF(x + L / 2, y))

        # torii en el agua, con su reflejo volteado
        tx, tyb = 0.80 * w, 0.74 * h
        _torii(p, tx, tyb, w, h, QColor(TORII))
        p.save()
        p.translate(0, 2 * tyb)
        p.scale(1, -1)
        _torii(p, tx, tyb, w, h, con_alfa(QColor(TORII), 90))
        p.restore()

        # orilla oscura en primer plano
        pts_orilla = crestas(-0.02 * w, 1.02 * w, 0.945 * h, 0.02 * h, rugosidad=0.5, iteraciones=7, rnd=r)
        p.setPen(Qt.NoPen)
        p.fillPath(_camino_montana(pts_orilla, h), QColor("#120A10"))

        # pétalos caídos en el suelo y en la orilla
        petalos_en_suelo(p, r, 0, w, 0.90 * h, h, 900, h / 1080)

        # cerezos que enmarcan la escena, con el sol (a la derecha del centro) iluminándolos
        Cerezo(0.06 * w, 1.0 * h, 0.58 * h, r, inclinacion=14, lado_sol=1).crecer().pintar(p)
        Cerezo(0.95 * w, 1.0 * h, 0.46 * h, r, inclinacion=-12, lado_sol=-1).crecer().pintar(p)

        # grano de papel y viñeta
        grupos = {}
        for _ in range(6000):
            punto = QPointF(r.uniform(0, w), r.uniform(0, h))
            grupos.setdefault((r.random() < 0.5, r.randint(6, 10)), []).append(punto)
        p.setBrush(Qt.NoBrush)
        for (blanco, alfa), pts in grupos.items():
            p.setPen(QPen(QColor(255, 255, 255, alfa) if blanco else QColor(0, 0, 0, alfa), 1))
            p.drawPoints(QPolygonF(pts))
        viñeta = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w, h) / 2)
        viñeta.setColorAt(0.55, QColor(0, 0, 0, 0))
        viñeta.setColorAt(1.0, QColor(0, 0, 0, 110))
        p.setPen(Qt.NoPen)
        p.fillRect(QRectF(0, 0, w, h), QBrush(viñeta))

    # ------------------------------------------------------------ animado

    def _preparar_sprites(self, h):
        """Cuatro pétalos pre-renderizados (10-18 px a 1080p), reescalados con la altura."""
        if self._sprites_h == h:
            return
        self._sprites = []
        for base in (10, 12, 14, 18):
            s = max(6, int(round(base * h / 1080)))
            pm = QPixmap(s, s)
            pm.fill(QColor(0, 0, 0, 0))
            pc = QPainter(pm)
            try:
                pc.setRenderHint(QPainter.Antialiasing, True)
                pc.translate(s / 2, s / 2)
                pc.scale(s, s)
                g = QLinearGradient(0, -0.5, 0, 0.5)
                g.setColorAt(0, QColor(PETALO_ARRIBA))
                g.setColorAt(1, QColor(PETALO_ABAJO))
                pc.setPen(Qt.NoPen)
                pc.setBrush(QBrush(g))
                pc.drawPath(_forma_petalo())
            finally:
                pc.end()
            self._sprites.append(pm)
        self._sprites_h = h

    def _preparar_niebla(self, w, h):
        """Dos franjas de niebla pre-renderizadas, de ancho 2*w, que se desplazan sobre el lago."""
        if self._niebla_clave == (w, h):
            return
        self._niebla = []
        for k, (alto_f, y_f, vel) in enumerate(((0.12, 0.72, 0.012), (0.10, 0.86, -0.008))):
            alto = max(4, int(alto_f * h))
            ancho = 2 * w
            pm = QPixmap(ancho, alto)
            pm.fill(QColor(0, 0, 0, 0))
            pc = QPainter(pm)
            try:
                pc.setRenderHint(QPainter.Antialiasing, True)
                rr = random.Random(31 + k)
                for _ in range(16):
                    cx, cy = rr.uniform(0, ancho), alto * rr.uniform(0.35, 0.65)
                    rad = alto * rr.uniform(0.9, 1.8)
                    g = QRadialGradient(QPointF(cx, cy), rad)
                    g.setColorAt(0, QColor(255, 255, 255, 50))
                    g.setColorAt(1, QColor(255, 255, 255, 0))
                    pc.fillRect(QRectF(cx - rad, cy - rad, 2 * rad, 2 * rad), QBrush(g))
                # máscara vertical: la franja se desvanece por arriba y por abajo, sin bordes duros
                pc.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                m = QLinearGradient(0, 0, 0, alto)
                m.setColorAt(0.0, QColor(0, 0, 0, 0))
                m.setColorAt(0.35, QColor(0, 0, 0, 255))
                m.setColorAt(0.65, QColor(0, 0, 0, 255))
                m.setColorAt(1.0, QColor(0, 0, 0, 0))
                pc.fillRect(QRectF(0, 0, ancho, alto), QBrush(m))
            finally:
                pc.end()
            self._niebla.append((pm, y_f * h, vel))
        self._niebla_clave = (w, h)

    def pintar_animado(self, p, w, h, t):
        e = self.energia()
        self._preparar_sprites(h)
        self._preparar_niebla(w, h)

        # niebla baja que pasa sobre el lago
        for pm, y, vel in self._niebla:
            p.drawPixmap(QPointF(-((t * vel) % 1.0) * w, y), pm)

        # halo del sol que late con la música (aditivo)
        p.save()
        p.setCompositionMode(QPainter.CompositionMode_Screen)
        self.brillo(p, SOL_X * w, SOL_Y * h, 0.30 * h, "#FFB27A", 100 + 80 * e)
        p.restore()

        # destellos dorados en el agua
        for x, y, L, alfa, fase, frec in self.destellos:
            a = alfa * (0.5 + 0.5 * math.sin(t * frec + fase))
            p.setPen(QPen(QColor(255, 205, 120, int(a)), max(1.5, 0.0018 * h), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x * w - L * w / 2, y * h), QPointF(x * w + L * w / 2, y * h))

        # pétalos que caen en diagonal, se balancean y voltean
        p.setPen(Qt.NoPen)
        for x0, y0, vy, vx, amp, frec, fase, giro, frec_v, idx in self.petalos:
            xf = (x0 + vx * t + amp * math.sin(frec * t + fase)) % 1.0
            yf = (y0 + vy * t) % 1.0
            pm = self._sprites[idx]
            p.save()
            p.translate(xf * w, yf * h)
            p.rotate(math.degrees(giro * t + fase))
            p.scale(max(0.15, abs(math.cos(frec_v * t + fase))), 1.0)
            p.drawPixmap(QPointF(-pm.width() / 2, -pm.height() / 2), pm)
            p.restore()

        # ondas de la música sobre la línea del horizonte del lago
        # entre los dos cerezos, sobre el agua, para que no cruce los árboles
        self.ondas(p, HORIZONTE * h, 0.42 * w, 0.08 * h, con_alfa(self.acento(), 200), x0=0.36 * w)
