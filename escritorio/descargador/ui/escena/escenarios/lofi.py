# -*- coding: utf-8 -*-
"""Lo-fi: la ilustración que eligió la persona (chica estudiando, gato en la ventana) a pantalla completa, con
vida encima: la lámpara respira con la música, polvo flotando en su luz, vapor de la taza, pájaros que cruzan
el cielo de la ventana, la pantalla del portátil que parpadea suave y las frecuencias como un brillo sobre los
tejados. La imagen no se toca: solo se escala con suavizado y se le pone una viñeta."""
import math
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient

from .base import EscenarioBase, con_alfa

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                    "escenarios_img", "lofi.png")
ANCHO_IMG, ALTO_IMG = 1600, 896

# lugares de la ilustración (en píxeles de la imagen original)
LAMPARA = (490, 245)                     # boca de la pantalla de la lámpara
LUZ = QRectF(360, 260, 380, 460)         # donde cae su luz (polvo)
TAZA = (352, 735)                        # boca de la taza
CIELO = QRectF(335, 0, 745, 120)         # cielo visible por la ventana
TEJADOS_Y = 118                          # línea sobre los tejados (las ondas)
PORTATIL = QRectF(0, 520, 130, 230)      # pantalla del portátil


class EscenarioLofi(EscenarioBase):
    NOMBRE = "Lo-fi"
    ACENTO = "#FFB86B"
    SEMILLA = 41

    def preparar(self):
        self._img = QImage(RUTA)
        r = self.rnd
        self._polvo = [(r.random(), r.random(), r.uniform(0.6, 1.8), r.uniform(0.05, 0.16), r.uniform(0, 6.28),
                        r.uniform(40, 130)) for _ in range(70)]
        self._pajaros = [(r.uniform(0, 30), r.uniform(0.15, 0.85), r.uniform(0.6, 1.0)) for _ in range(3)]
        self._vapor = [r.uniform(0, 6.28) for _ in range(3)]
        self._mota = self._sprite_mota()

    @staticmethod
    def _sprite_mota():
        pm = QPixmap(16, 16)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            g = QRadialGradient(QPointF(8, 8), 8)
            g.setColorAt(0, QColor(255, 236, 200, 255))
            g.setColorAt(0.35, QColor(255, 210, 150, 140))
            g.setColorAt(1, QColor(255, 200, 140, 0))
            p.fillRect(0, 0, 16, 16, g)
        finally:
            p.end()
        return pm

    # ------------------------------------------------------------ geometría

    def _escala(self, w, h):
        s = max(w / ANCHO_IMG, h / ALTO_IMG)
        return s, (w - ANCHO_IMG * s) / 2, (h - ALTO_IMG * s) / 2

    def _p(self, x, y):
        s, ox, oy = self._geo
        return QPointF(ox + x * s, oy + y * s)

    def _r(self, rect):
        s, ox, oy = self._geo
        return QRectF(ox + rect.x() * s, oy + rect.y() * s, rect.width() * s, rect.height() * s)

    # ------------------------------------------------------------ pintado

    def pintar_estatico(self, p, w, h):
        self._geo = self._escala(w, h)
        s, ox, oy = self._geo
        p.fillRect(0, 0, w, h, QColor("#1A120C"))
        if not self._img.isNull():
            img = self._img.scaled(round(ANCHO_IMG * s), round(ALTO_IMG * s), Qt.IgnoreAspectRatio,
                                   Qt.SmoothTransformation)
            p.drawImage(QPointF(ox, oy), img)
        # viñeta cálida y suave: centra la mirada sin oscurecer la ilustración
        g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.75)
        g.setColorAt(0.55, QColor(0, 0, 0, 0))
        g.setColorAt(1, QColor(20, 8, 0, 120))
        p.fillRect(0, 0, w, h, g)

    def pintar_animado(self, p, w, h, t):
        if not hasattr(self, "_geo"):
            self._geo = self._escala(w, h)
        s = self._geo[0]
        e = self.energia()
        p.setRenderHint(QPainter.Antialiasing, True)

        # la lámpara respira con la música (luz que se suma, no tapa)
        p.save()
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        c = self._p(*LAMPARA)
        alfa = 26 + 70 * e + 8 * math.sin(t * 1.7)
        self.brillo(p, c.x(), c.y() + 60 * s, 300 * s, QColor(255, 176, 90), alfa)
        p.restore()

        # polvo flotando en la luz de la lámpara
        zona = self._r(LUZ)
        tam = 7 * s
        for (fx, fy, vel, amp, fase, alfa_m) in self._polvo:
            y = zona.bottom() - ((fy + t * vel * 0.03) % 1.0) * zona.height()
            x = zona.left() + fx * zona.width() + math.sin(t * 0.6 + fase) * amp * 60 * s
            borde = min(1.0, (zona.bottom() - y) / (zona.height() * 0.2), (y - zona.top()) / (zona.height() * 0.2))
            p.setOpacity(max(0.0, borde) * (alfa_m / 255) * (0.6 + 0.6 * e))
            p.drawPixmap(QRectF(x - tam / 2, y - tam / 2, tam, tam), self._mota, QRectF(0, 0, 16, 16))
        p.setOpacity(1.0)

        # vapor de la taza: tres cintas finas que suben y se desvanecen
        base = self._p(*TAZA)
        for i, fase in enumerate(self._vapor):
            camino = QPainterPath(base + QPointF((i - 1) * 9 * s, 0))
            alto = 120 * s
            for k in range(1, 9):
                f = k / 8
                camino.lineTo(base + QPointF((i - 1) * 9 * s + math.sin(t * 1.4 + fase + f * 5) * 12 * s * f,
                                             -alto * f))
            p.setPen(QPen(QColor(255, 248, 235, int(55 * (0.7 + 0.3 * math.sin(t + fase)))), 3.2 * s,
                          Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawPath(camino)

        # pájaros que cruzan el cielo de la ventana, de vez en cuando
        cielo = self._r(CIELO)
        p.save()
        p.setClipRect(cielo)
        for (ret, fy, vel) in self._pajaros:
            ciclo = 26.0
            u = ((t + ret) % ciclo) / (ciclo * 0.45)
            if u > 1:
                continue
            x = cielo.left() - 30 * s + u * (cielo.width() + 60 * s)
            y = cielo.top() + fy * cielo.height() + math.sin(u * 9) * 4 * s
            aleteo = math.sin(t * 9 * vel) * 4 * s
            ala = QPainterPath(QPointF(x - 9 * s, y - aleteo))
            ala.quadTo(QPointF(x - 4 * s, y - 3 * s), QPointF(x, y))
            ala.quadTo(QPointF(x + 4 * s, y - 3 * s), QPointF(x + 9 * s, y - aleteo))
            p.setPen(QPen(QColor(60, 50, 60, 200), 2.2 * s, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(ala)
        p.restore()

        # la pantalla del portátil parpadea muy suave
        pant = self._r(PORTATIL)
        p.fillRect(pant, QColor(200, 225, 255, int(10 + 8 * (0.5 + 0.5 * math.sin(t * 0.9)))))

        # las frecuencias: un brillo fino sobre los tejados que se ven por la ventana
        izq, der = self._p(CIELO.left(), TEJADOS_Y), self._p(CIELO.right(), TEJADOS_Y)
        p.save()
        p.setClipRect(cielo.adjusted(0, -10 * s, 0, 30 * s))
        self.ondas(p, base_y=izq.y(), ancho=der.x() - izq.x(), alto_max=58 * s,
                   color=con_alfa(self.acento(), 230), x0=izq.x(), reflejo=False, grosor=1.6 * s)
        p.restore()
