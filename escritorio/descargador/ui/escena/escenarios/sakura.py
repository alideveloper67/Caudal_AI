# -*- coding: utf-8 -*-
"""Cerezos en flor que se ven naturales (para los escenarios que los usan: Japón samurái, My Melody…).

Cómo se consigue que no parezcan forzados:

* Estructura de paraguas: el tronco sube inclinado y las ramas se abren hacia los lados (el ángulo de cada rama
  hija se acerca a la horizontal de su lado) y las finas se doblan un poco por su peso. Cada rama empieza con el
  grosor con que terminó su madre: el árbol es continuo, sin escalones.
* Las flores no son manchas: son miles de florecitas pequeñas agrupadas en nubecitas A LO LARGO de las ramas finas
  (no solo en las puntas), con huecos donde se ve la rama.
* Luz con volumen: cada florecita recibe una luz según su altura en la copa y el lado del sol; se pintan ordenadas
  de oscura a clara, así lo iluminado queda encima y la copa tiene forma. Un velo de sombra suave bajo la copa la
  separa del fondo, y en el borde algunas flores de cinco pétalos con centro claro dan el detalle de cerca.

Todo se dibuja una sola vez (en la parte estática del escenario).
"""
import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPolygonF, QRadialGradient

SOMBRA = QColor("#B85C84")
MEDIO = QColor("#F2A6C2")
CLARO = QColor("#FFE6F0")
CORTEZA_OSCURA = QColor("#2A1A1C")
CORTEZA_CLARA = QColor("#5A3A38")


def _mezcla(a, b, f):
    f = max(0.0, min(1.0, f))
    return QColor(round(a.red() + (b.red() - a.red()) * f), round(a.green() + (b.green() - a.green()) * f),
                  round(a.blue() + (b.blue() - a.blue()) * f))


def _color_luz(luz):
    """0 = sombra, 1 = a pleno sol."""
    return _mezcla(SOMBRA, MEDIO, luz * 1.6) if luz < 0.62 else _mezcla(MEDIO, CLARO, (luz - 0.62) / 0.38)


class Cerezo:
    """Un cerezo: `crecer()` arma las ramas; `pintar(p)` dibuja ramas, copa y flores."""

    def __init__(self, x, y, alto, rnd, inclinacion=0.0, lado_sol=-1, densidad=1.0, colgante=False,
                 angulo=None):
        self.x, self.y, self.alto, self.r = x, y, alto, rnd
        self.inclinacion = inclinacion          # grados: + hacia la derecha
        self.lado_sol = lado_sol                # -1 sol a la izquierda, +1 a la derecha
        self.densidad = densidad
        self.colgante = colgante                # rama que entra desde un borde (no tiene suelo)
        self.angulo = angulo                    # ángulo inicial si es colgante
        self.segmentos = []                     # (x0, y0, x1, y1, ctrl, g0, g1, nivel)
        self.puntos_flor = []                   # (x, y, peso)

    # ------------------------------------------------------------ estructura

    def crecer(self):
        r = self.r
        g = self.alto * 0.11
        if self.colgante:
            self._rama(self.x, self.y, self.angulo, self.alto * 0.42, g * 0.7, 1)
        else:
            ang = 90 - self.inclinacion
            # el tronco en dos tramos con un quiebre suave
            l1 = self.alto * 0.34
            x1, y1, g1 = self._tramo(self.x, self.y, ang, l1, g, g * 0.82, 0)
            ang2 = ang + r.uniform(-14, 14)
            x2, y2, g2 = self._tramo(x1, y1, ang2, self.alto * 0.18, g * 0.82, g * 0.66, 0)
            # de ahí salen 3–4 ramas principales en abanico, abiertas hacia los lados
            n = r.choice((3, 4))
            for i in range(n):
                f = i / (n - 1)
                a = 152 - f * 124 + r.uniform(-10, 10) - self.inclinacion * 0.5
                self._rama(x2, y2, a, self.alto * r.uniform(0.30, 0.40), g2 * r.uniform(0.62, 0.78), 1)
        return self

    def _tramo(self, x, y, ang, largo, g0, g1, nivel):
        a = math.radians(ang)
        fx, fy = x + math.cos(a) * largo, y - math.sin(a) * largo
        desv = self.r.uniform(-0.12, 0.12) * largo
        cx = (x + fx) / 2 + math.sin(a) * desv
        cy = (y + fy) / 2 + math.cos(a) * desv
        self.segmentos.append((x, y, fx, fy, (cx, cy), g0, g1, nivel))
        return fx, fy, g1

    def _rama(self, x, y, ang, largo, grosor, nivel):
        r = self.r
        # paraguas: las ramas se acercan a la horizontal de su lado; las finas se doblan por su peso
        lado = 1 if math.cos(math.radians(ang)) >= 0 else -1
        horizontal = 18 if lado > 0 else 162
        ang = ang + (horizontal - ang) * (0.05 + 0.025 * nivel) * r.uniform(0.6, 1.1)
        ang = max(8.0, min(172.0, ang))           # nunca hacia abajo
        if nivel >= 4:
            ang -= lado * r.uniform(1, 5)
        g1 = grosor * 0.70
        fx, fy, _ = self._tramo(x, y, ang, largo, grosor, g1, nivel)
        if nivel >= 2:
            # flores a lo largo de la rama, más hacia la punta
            for k in range(1 + int(largo / (self.alto * 0.035))):
                t = 0.35 + 0.65 * r.random()
                self.puntos_flor.append((x + (fx - x) * t, y + (fy - y) * t, 1.0 / (1 + nivel * 0.15)))
        if nivel >= 6 or grosor < 0.9:
            self.puntos_flor.append((fx, fy, 1.2))
            return
        hijos = 2 if r.random() < 0.55 else 3
        for i in range(hijos):
            d = r.uniform(16, 42) * (-1 if i % 2 == 0 else 1)
            if hijos == 3 and i == 2:
                d = r.uniform(-8, 8)
            self._rama(fx, fy, ang + d, largo * r.uniform(0.62, 0.78), g1 * r.uniform(0.80, 0.95), nivel + 1)

    # ------------------------------------------------------------ dibujo

    def pintar(self, p, escala_flor=1.0):
        r = self.r
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        self._pintar_ramas(p)
        if not self.puntos_flor:
            p.restore()
            return
        xs = [f[0] for f in self.puntos_flor]
        ys = [f[1] for f in self.puntos_flor]
        top, bot = min(ys), max(ys)
        izq, der = min(xs), max(xs)
        alto_copa = max(1.0, bot - top)
        ancho_copa = max(1.0, der - izq)

        # velo de sombra bajo la copa: la separa del fondo y le da cuerpo
        p.setPen(Qt.NoPen)
        for (fx, fy, _peso) in self.puntos_flor[::3]:
            g = QRadialGradient(QPointF(fx, fy + 6), self.alto * 0.07)
            g.setColorAt(0, QColor(120, 50, 80, 26))
            g.setColorAt(1, QColor(120, 50, 80, 0))
            p.setBrush(g)
            p.drawEllipse(QPointF(fx, fy + 6), self.alto * 0.07, self.alto * 0.05)

        # florecitas: nubecitas gaussianas alrededor de cada punto, con su luz
        base = self.alto * 0.0105 * escala_flor
        flores = []
        for (fx, fy, peso) in self.puntos_flor:
            if r.random() > self.densidad:
                continue
            n = int(r.randint(12, 20) * peso)
            sx, sy = self.alto * 0.026, self.alto * 0.017
            for _ in range(n):
                x = fx + r.gauss(0, sx)
                y = fy + r.gauss(0, sy) - self.alto * 0.006
                altura = 1 - (y - top) / alto_copa                      # 1 arriba de la copa
                lado = ((x - izq) / ancho_copa - 0.5) * -self.lado_sol   # + hacia el sol
                local = (fy - y) / (sy * 2.2)                           # arriba de su nubecita
                luz = 0.18 + 0.42 * altura + 0.20 * lado + 0.26 * local + r.uniform(-0.10, 0.10)
                rad = base * r.uniform(0.45, 1.0)
                flores.append((luz, x, y, rad))
        flores.sort(key=lambda f: f[0])
        for luz, x, y, rad in flores:
            p.setBrush(_color_luz(luz))
            p.drawEllipse(QPointF(x, y), rad, rad)

        # detalle de cerca: flores de cinco pétalos en el borde exterior de la copa
        petalo = QPainterPath()
        petalo.addEllipse(QPointF(0, -0.55), 0.42, 0.58)
        for luz, x, y, rad in flores[::14]:
            if luz < 0.55:
                continue
            p.save()
            p.translate(x, y)
            p.rotate(r.uniform(0, 72))
            p.scale(rad * 1.5, rad * 1.5)
            p.setBrush(_color_luz(min(1.0, luz + 0.12)))
            for k in range(5):
                p.drawPath(petalo)
                p.rotate(72)
            p.setBrush(QColor("#FFF6C8"))
            p.drawEllipse(QPointF(0, 0), 0.22, 0.22)
            p.restore()
        p.restore()

    def _pintar_ramas(self, p):
        p.setPen(Qt.NoPen)
        for (x0, y0, x1, y1, (cx, cy), g0, g1, nivel) in sorted(self.segmentos, key=lambda s: -s[5]):
            izq, der = [], []
            n = 10
            for i in range(n + 1):
                t = i / n
                u = 1 - t
                bx = u * u * x0 + 2 * u * t * cx + t * t * x1
                by = u * u * y0 + 2 * u * t * cy + t * t * y1
                tx = 2 * u * (cx - x0) + 2 * t * (x1 - cx)
                ty = 2 * u * (cy - y0) + 2 * t * (y1 - cy)
                L = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / L, tx / L
                m = (g0 + (g1 - g0) * t) / 2
                izq.append(QPointF(bx + nx * m, by + ny * m))
                der.append(QPointF(bx - nx * m, by - ny * m))
            p.setBrush(_mezcla(CORTEZA_OSCURA, CORTEZA_CLARA, 0.15 + 0.08 * nivel))
            p.drawPolygon(QPolygonF(izq + der[::-1]))
            # luz fina del lado del sol en las ramas gruesas
            if g0 > 3:
                p.setBrush(QColor(140, 90, 90, 70))
                lado = izq if self.lado_sol < 0 else der
                medio = [QPointF((a.x() * 0.75 + b.x() * 0.25), (a.y() * 0.75 + b.y() * 0.25))
                         for a, b in zip(lado, (der if lado is izq else izq))]
                p.drawPolygon(QPolygonF(lado + medio[::-1]))
            # un nudo redondo en la unión, para que no se vea el corte
            p.setBrush(_mezcla(CORTEZA_OSCURA, CORTEZA_CLARA, 0.15 + 0.08 * nivel))
            p.drawEllipse(QPointF(x0, y0), g0 / 2, g0 / 2)


def petalos_en_suelo(p, rnd, x0, x1, y0, y1, n, escala):
    """Pétalos caídos: elipses diminutas giradas, en tonos rosados, más juntos bajo los árboles."""
    p.save()
    p.setPen(Qt.NoPen)
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        p.save()
        p.translate(x, y)
        p.rotate(rnd.uniform(0, 180))
        c = _color_luz(rnd.uniform(0.45, 0.95))
        c.setAlpha(rnd.randint(150, 230))
        p.setBrush(c)
        rx = escala * rnd.uniform(2.0, 3.6)
        p.drawEllipse(QPointF(0, 0), rx, rx * 0.55)
        p.restore()
    p.restore()
