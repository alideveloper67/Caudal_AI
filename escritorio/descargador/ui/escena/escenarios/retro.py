# -*- coding: utf-8 -*-
"""Escenario «Retro»: atardecer outrun. El cielo, el sol de franjas y las montañas van en caché (fijos);
la rejilla del suelo avanza hacia la cámara, el sol late muy poco y la música se dibuja como ondas
justo sobre el horizonte, delante del sol.

El sol y las montañas se pintan como sprites aparte (no en la caché) porque el sol late con el audio y
las montañas tienen que quedar por delante de él."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from descargador.ui.escena.escenarios.base import EscenarioBase, con_alfa

HORIZONTE = 0.58        # fracción del alto donde está la línea del horizonte
RADIO_SOL = 0.22        # fracción del alto
PERIODO_REJILLA = 3.0   # s por ciclo de avance de la rejilla
LINEAS_REJILLA = 14


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
        self._capas_clave = None
        self._sol = None
        self._montes = None
        self._montes_linea = None

    # ------------------------------------------------------------ fijo (caché)

    def pintar_estatico(self, p, w, h):
        hz = HORIZONTE * h
        cx = w / 2
        cielo = QLinearGradient(0, 0, 0, hz)
        cielo.setColorAt(0.0, QColor("#1A0B2E"))
        cielo.setColorAt(0.6, QColor("#FF6B6B"))
        cielo.setColorAt(1.0, QColor("#FFB347"))
        p.fillRect(QRectF(0, 0, w, h), QBrush(cielo))
        # Halo cálido alrededor del sol, centrado en el horizonte.
        self.brillo(p, cx, hz, RADIO_SOL * h * 2.2, "#FFB347", 80)
        # Suelo: degradado oscuro bajo el horizonte.
        suelo = QLinearGradient(0, hz, 0, h)
        suelo.setColorAt(0.0, QColor("#2A0F3A"))
        suelo.setColorAt(1.0, QColor("#0B0418"))
        p.fillRect(QRectF(0, hz, w, h - hz), QBrush(suelo))
        # Líneas verticales de la rejilla, convergiendo en el horizonte.
        p.setPen(QPen(con_alfa(self.acento(), 70), 1))
        for j in range(-9, 10):
            p.drawLine(QPointF(cx + j * w * 0.012, hz), QPointF(cx + j * w * 0.11, h))

    # ------------------------------------------------------------ sprites del sol y las montañas

    def _preparar_capas(self, w, h):
        if self._capas_clave == (w, h):
            return
        self._capas_clave = (w, h)
        hz = HORIZONTE * h

        # Sol: semicírculo con degradado. Las franjas son huecos transparentes, así se ve el cielo.
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
            ps.setCompositionMode(QPainter.CompositionMode_Clear)
            y = 0.48 * r
            for k in range(6):
                grueso = r * (0.02 + 0.022 * k)     # cada franja más gruesa hacia el horizonte
                ps.fillRect(QRectF(0, y, 2 * r, grueso), QColor(0, 0, 0))
                y += grueso + 0.09 * r
        finally:
            ps.end()

        # Montañas en silueta, de borde a borde, apoyadas en el horizonte.
        cimas = [QPointF(fx * w, hz - fh * h) for fx, fh in self._cimas]
        camino = QPainterPath(QPointF(0, hz))
        for pt in cimas:
            camino.lineTo(pt)
        camino.lineTo(QPointF(w, hz))
        camino.closeSubpath()
        montes = QPixmap(w, max(1, round(hz)))
        montes.fill(QColor(0, 0, 0, 0))
        pm = QPainter(montes)
        try:
            pm.setRenderHint(QPainter.Antialiasing, True)
            pm.fillPath(camino, QBrush(QColor("#2B1240")))
        finally:
            pm.end()

        # Borde fino de las crestas (en el acento; se dibuja cada cuadro para que siga la transición).
        linea = QPainterPath(cimas[0])
        for pt in cimas[1:]:
            linea.lineTo(pt)

        self._sol = sol
        self._montes = montes
        self._montes_linea = linea

    # ------------------------------------------------------------ animado (cada cuadro)

    def pintar_animado(self, p, w, h, t):
        hz = HORIZONTE * h
        self._preparar_capas(w, h)
        acento = self.acento()

        # Sol que late muy poco con el audio (escala 1..1.03), con la base sobre el horizonte.
        r = self._sol.height()
        escala = 1.0 + 0.03 * max(0.0, min(1.0, self.energia()))
        p.save()
        p.translate(w / 2, hz)
        p.scale(escala, escala)
        p.drawPixmap(QPointF(-r, -r), self._sol)
        p.restore()

        # Montañas delante del sol, con su borde fino en el acento.
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
