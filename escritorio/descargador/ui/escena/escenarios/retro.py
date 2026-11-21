# -*- coding: utf-8 -*-
"""Escenario «Retro»: atardecer outrun. La composición se mantiene (sol, montañas, rejilla, horizonte);
se añade profundidad (cordillera lejana con bruma), luz (rayos del sol como de persiana, halo que respira),
textura (grano, viñeta, velo inferior) y pequeños detalles animados (estrellas, polvo en los rayos,
ecualizador en la esquina con las bandas de audio).

Lo fijo va en caché (`pintar_estatico` y las capas de `_preparar_capas`); cada cuadro solo dibuja lo que se
mueve. El sol y las montañas son sprites aparte porque el sol late con el audio y las montañas tienen que
quedar por delante de él."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient

from descargador.ui.escena.escenarios.base import EscenarioBase, con_alfa

HORIZONTE = 0.58        # fracción del alto donde está la línea del horizonte
RADIO_SOL = 0.22        # fracción del alto
PERIODO_REJILLA = 3.0   # s por ciclo de avance de la rejilla
LINEAS_REJILLA = 14
N_LEJANAS = 13          # crestas de la cordillera lejana
N_ESTRELLAS = 34
N_MOTAS = 26
N_RAYOS = 7
N_GRANO = 2200
N_EQ = 16               # barras del ecualizador de la esquina


class EscenarioRetro(EscenarioBase):
    NOMBRE = "Retro"
    ACENTO = "#FF8C42"
    SEMILLA = 11

    def preparar(self):
        # Crestas de las montañas: (fracción del ancho, fracción del alto sobre el horizonte).
        n = 9
        cimas = []
        for i in range(n):
            fx = (i + 0.5 + (self.rnd.random() - 0.5) * 0.5) / n
            cimas.append((fx, 0.04 + 0.11 * self.rnd.random()))
        self._cimas = [(0.0, 0.025)] + cimas + [(1.0, 0.025)]
        # Cordillera lejana: más baja, detrás del sol, tintada por la bruma del atardecer.
        lejanas = []
        for i in range(N_LEJANAS):
            fx = (i + 0.5 + (self.rnd.random() - 0.5) * 0.6) / N_LEJANAS
            lejanas.append((fx, 0.05 + 0.07 * self.rnd.random()))
        self._cimas_lejanas = [(0.0, 0.04)] + lejanas + [(1.0, 0.04)]
        # Estrellas (fx, fy, radio, fase): solo en la franja alta del cielo, lejos del sol.
        self._estrellas = [(self.rnd.random(), 0.02 + 0.28 * self.rnd.random(),
                            0.6 + 0.9 * self.rnd.random(), self.rnd.random() * math.tau)
                           for _ in range(N_ESTRELLAS)]
        # Polvo que flota en los rayos (fx, fase, velocidad, tamaño).
        self._motas = [(0.3 + 0.4 * self.rnd.random(), self.rnd.random(),
                        0.6 + 0.8 * self.rnd.random(), 0.6 + 0.6 * self.rnd.random())
                       for _ in range(N_MOTAS)]
        # Grano de la imagen (fx, fy, es_claro), precalculado para que sea siempre el mismo.
        self._grano = [(self.rnd.random(), self.rnd.random(), self.rnd.random() < 0.5)
                       for _ in range(N_GRANO)]
        self._capas_clave = None
        self._sol = None
        self._montes = None
        self._montes_linea = None
        self._lejanos = None
        self._rayos = None

    # ------------------------------------------------------------ fijo (caché)

    def pintar_estatico(self, p, w, h):
        hz = HORIZONTE * h
        cx = w / 2
        acento = self.acento()
        self._preparar_capas(w, h)
        cielo = QLinearGradient(0, 0, 0, hz)
        cielo.setColorAt(0.0, QColor("#1A0B2E"))
        cielo.setColorAt(0.6, QColor("#FF6B6B"))
        cielo.setColorAt(1.0, QColor("#FFB347"))
        p.fillRect(QRectF(0, 0, w, h), QBrush(cielo))
        # Halo cálido alrededor del sol, centrado en el horizonte.
        self.brillo(p, cx, hz, RADIO_SOL * h * 2.2, "#FFB347", 80)
        # Rayos del sol, como la luz que entra por una persiana (fijos, van en caché).
        p.drawPixmap(0, 0, self._rayos)
        # Suelo: degradado oscuro bajo el horizonte.
        suelo = QLinearGradient(0, hz, 0, h)
        suelo.setColorAt(0.0, QColor("#2A0F3A"))
        suelo.setColorAt(1.0, QColor("#0B0418"))
        p.fillRect(QRectF(0, hz, w, h - hz), QBrush(suelo))
        # Luz del horizonte reflejada en el suelo, justo bajo la línea.
        reflejo = QLinearGradient(0, hz, 0, hz + 0.06 * h)
        reflejo.setColorAt(0.0, con_alfa(acento, 70))
        reflejo.setColorAt(1.0, con_alfa(acento, 0))
        p.fillRect(QRectF(0, hz, w, 0.06 * h), QBrush(reflejo))
        # Líneas verticales de la rejilla, convergiendo en el horizonte; con un halo fino debajo.
        for j in range(-9, 10):
            a = QPointF(cx + j * w * 0.012, hz)
            b = QPointF(cx + j * w * 0.11, h)
            p.setPen(QPen(con_alfa(acento, 16), 3.0))
            p.drawLine(a, b)
            p.setPen(QPen(con_alfa(acento, 70), 1))
            p.drawLine(a, b)
        # Grano fino de la imagen.
        p.setPen(QPen(QColor(255, 226, 196, 10), 1))
        p.drawPoints([QPointF(fx * w, fy * h) for fx, fy, claro in self._grano if claro])
        p.setPen(QPen(QColor(12, 0, 22, 16), 1))
        p.drawPoints([QPointF(fx * w, fy * h) for fx, fy, claro in self._grano if not claro])
        # Velo oscuro inferior, para que se lean la letra y la barra.
        self.velo(p, QRectF(0, 0.70 * h, w, 0.30 * h), QColor(0, 0, 0, 0), QColor(8, 2, 16, 150))
        # Viñeta suave en las esquinas.
        v = QRadialGradient(QPointF(cx, h * 0.5), math.hypot(w, h) * 0.62)
        v.setColorAt(0.6, QColor(0, 0, 0, 0))
        v.setColorAt(1.0, QColor(8, 2, 16, 170))
        p.fillRect(QRectF(0, 0, w, h), QBrush(v))

    # ------------------------------------------------------------ sprites del sol, rayos y montañas

    @staticmethod
    def _camino_perfil(cimas, w, h, hz):
        """Camino cerrado de una cordillera apoyada en el horizonte, y sus puntos de cresta."""
        pts = [QPointF(fx * w, hz - fh * h) for fx, fh in cimas]
        camino = QPainterPath(QPointF(0, hz))
        for pt in pts:
            camino.lineTo(pt)
        camino.lineTo(QPointF(w, hz))
        camino.closeSubpath()
        return camino, pts

    def _preparar_capas(self, w, h):
        if self._capas_clave == (w, h):
            return
        self._capas_clave = (w, h)
        hz = HORIZONTE * h
        cx = w / 2

        # Sol: semicírculo con degradado y borde de luz arriba. Las franjas son huecos transparentes.
        r = max(2, round(RADIO_SOL * h))
        sol = QPixmap(2 * r, r)
        sol.fill(QColor(0, 0, 0, 0))
        ps = QPainter(sol)
        try:
            ps.setRenderHint(QPainter.Antialiasing, True)
            g = QLinearGradient(0, 0, 0, r)
            g.setColorAt(0.0, QColor("#FFE066"))
            g.setColorAt(1.0, QColor("#FF5E7E"))
            ps.setPen(Qt.NoPen)
            ps.setBrush(QBrush(g))
            ps.drawEllipse(QRectF(0, 0, 2 * r, 2 * r))
            ps.setBrush(Qt.NoBrush)
            ps.setPen(QPen(QColor(255, 255, 240, 70), max(1.0, r * 0.02)))
            ps.drawEllipse(QRectF(0.5, 0.5, 2 * r - 1, 2 * r - 1))
            ps.setPen(Qt.NoPen)
            ps.setCompositionMode(QPainter.CompositionMode_Clear)
            y = 0.48 * r
            for k in range(6):
                grueso = r * (0.02 + 0.022 * k)     # cada franja más gruesa hacia el horizonte
                ps.fillRect(QRectF(0, y, 2 * r, grueso), QColor(0, 0, 0))
                y += grueso + 0.09 * r
        finally:
            ps.end()

        # Rayos del sol que se abren hacia arriba, como la luz que entra por una persiana.
        rayos = QPixmap(w, max(1, round(hz)))
        rayos.fill(QColor(0, 0, 0, 0))
        pr = QPainter(rayos)
        try:
            pr.setRenderHint(QPainter.Antialiasing, True)
            pr.setPen(Qt.NoPen)
            for k in range(N_RAYOS):
                f = (k + 0.5) / N_RAYOS
                xt = cx + (f - 0.5) * w * 1.2
                haz = QPainterPath(QPointF(cx - 0.012 * w, hz))
                haz.lineTo(QPointF(cx + 0.012 * w, hz))
                haz.lineTo(QPointF(xt + 0.05 * w, 0))
                haz.lineTo(QPointF(xt - 0.05 * w, 0))
                haz.closeSubpath()
                g = QLinearGradient(0, hz, 0, 0)
                g.setColorAt(0.0, con_alfa("#FFE9A8", 24))
                g.setColorAt(1.0, con_alfa("#FFE9A8", 0))
                pr.fillPath(haz, QBrush(g))
        finally:
            pr.end()

        # Cordillera lejana: más clara y azulada por la bruma, detrás del sol.
        camino_lejos, _ = self._camino_perfil(self._cimas_lejanas, w, h, hz)
        lejanos = QPixmap(w, max(1, round(hz)))
        lejanos.fill(QColor(0, 0, 0, 0))
        pl = QPainter(lejanos)
        try:
            pl.setRenderHint(QPainter.Antialiasing, True)
            g = QLinearGradient(0, hz * 0.45, 0, hz)
            g.setColorAt(0.0, QColor("#5E2F72"))
            g.setColorAt(1.0, QColor("#9A4F6E"))
            pl.fillPath(camino_lejos, QBrush(g))
        finally:
            pl.end()

        # Montañas en silueta, de borde a borde, apoyadas en el horizonte. Luz arriba, sombra abajo.
        camino, cimas_pt = self._camino_perfil(self._cimas, w, h, hz)
        montes = QPixmap(w, max(1, round(hz)))
        montes.fill(QColor(0, 0, 0, 0))
        pm = QPainter(montes)
        try:
            pm.setRenderHint(QPainter.Antialiasing, True)
            g = QLinearGradient(0, hz * 0.5, 0, hz)
            g.setColorAt(0.0, QColor("#4A1F5A"))
            g.setColorAt(0.55, QColor("#2B1240"))
            g.setColorAt(1.0, QColor("#1C0B2C"))
            pm.fillPath(camino, QBrush(g))
        finally:
            pm.end()

        # Borde fino de las crestas (en el acento; se dibuja cada cuadro para que siga la transición).
        linea = QPainterPath(cimas_pt[0])
        for pt in cimas_pt[1:]:
            linea.lineTo(pt)

        self._sol = sol
        self._rayos = rayos
        self._lejanos = lejanos
        self._montes = montes
        self._montes_linea = linea

    # ------------------------------------------------------------ animado (cada cuadro)

    def pintar_animado(self, p, w, h, t):
        hz = HORIZONTE * h
        self._preparar_capas(w, h)
        acento = self.acento()
        nivel = max(0.0, min(1.0, self.energia()))
        cx = w / 2

        # Estrellas que parpadean despacio en la franja alta.
        p.setPen(Qt.NoPen)
        for fx, fy, rad, ph in self._estrellas:
            p.setBrush(con_alfa("#FFF4E0", 90 + 80 * math.sin(t * 0.9 + ph)))
            p.drawEllipse(QPointF(fx * w, fy * h), rad, rad)

        # Polvo que sube lento dentro de los rayos.
        for fx, ph, vel, tam in self._motas:
            f = (t * 0.025 * vel + ph) % 1.0
            x = w * fx + 0.02 * w * math.sin(t * 0.4 + ph * math.tau)
            y = hz * (0.9 - 0.75 * f)
            p.setBrush(con_alfa("#FFF1C1", 150 * math.sin(math.pi * f)))
            p.drawEllipse(QPointF(x, y), 1.2 * tam, 1.2 * tam)

        # Halo del sol que respira con el audio (luz), y el sol con una escala muy leve.
        self.brillo(p, cx, hz, RADIO_SOL * h * 1.1, "#FFE066", 30 + 60 * nivel)
        r = self._sol.height()
        escala = 1.0 + 0.03 * nivel
        p.save()
        p.translate(cx, hz)
        p.scale(escala, escala)
        p.drawPixmap(QPointF(-r, -r), self._sol)
        p.restore()

        # Cordillera lejana, después del sol; luego las montañas delante, con su borde en el acento.
        p.drawPixmap(0, 0, self._lejanos)
        p.drawPixmap(0, 0, self._montes)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(con_alfa(acento, 150), 1.2))
        p.drawPath(self._montes_linea)

        # Rejilla en perspectiva: las líneas bajan hacia la cámara en cada ciclo de 3 s.
        fase = (t % PERIODO_REJILLA) / PERIODO_REJILLA
        for i in range(LINEAS_REJILLA + 1):
            u = (i + fase) / LINEAS_REJILLA
            if u > 1.0:
                continue
            y = hz + (h - hz) * u * u
            p.setPen(QPen(con_alfa(acento, 190 * min(1.0, u * 1.5)), 1.3))
            p.drawLine(QPointF(0, y), QPointF(w, y))

        # Música: ondas justo sobre el horizonte, delante del sol.
        self.ondas(p, hz, w, 0.16 * h, acento)

        # Ecualizador pequeño en la esquina inferior derecha, lejos del centro.
        base_eq = 0.955 * h
        p.setPen(Qt.NoPen)
        for i in range(N_EQ):
            v = self.bandas[i * 2]
            alto = 0.075 * h * max(0.06, v)
            x = w * 0.835 + i * w * 0.0085
            p.setBrush(con_alfa(acento, 120))
            p.drawRect(QRectF(x, base_eq - alto, w * 0.0055, alto))
