# -*- coding: utf-8 -*-
"""Fondo synthwave/retrowave de la escena, dibujado 100 % con QPainter (sin imágenes).

Capas, de atrás adelante: cielo con degradado y brillo radial en el horizonte, estrellas
con titileo lento, suelo con rejilla en perspectiva que viaja hacia la cámara y una
cordillera de frecuencias sobre el horizonte con su reflejo.

Lo caro (cielo, suelo y brillo) se prepara en un QPixmap que solo se rehace al cambiar de
tamaño; en cada cuadro se dibujan solo la rejilla, el titileo y las frecuencias.
"""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import QWidget

FPS = 30
INTERVALO_MS = 1000 // FPS          # 33 ms por cuadro
TAU = 2.0 * math.pi
HORIZONTE = 0.52                    # fracción del alto donde cae el horizonte
COLOR_CIELO_ARRIBA = "#120818"
COLOR_CIELO_HORIZONTE = "#6A2C6E"
COLOR_SUELO_HORIZONTE = "#2A1338"
COLOR_SUELO_ABAJO = "#07040C"
COLOR_BRILLO = "#FF6EC7"
COLOR_ACENTO = "#FF4FD8"            # color por defecto de la rejilla y de la cordillera
COLOR_CRESTA = "#FFC6F0"
NUM_ESTRELLAS = 70
SEMILLA_ESTRELLAS = 7
PERIODO_VIAJE = 2.4                 # segundos por ciclo de la rejilla (avance continuo)
DURACION_ACENTO = 0.8               # segundos de la transición de color
D_CERCA = 3.0                       # profundidad de la línea que toca el borde inferior
DELTA_PROFUNDIDAD = 0.5             # separación en profundidad entre líneas horizontales
D_LLENO = 6.0                       # por debajo de esta profundidad la rejilla va a tope
D_LEJOS = 14.0                      # más allá, la línea ya no se dibuja (se desvanece antes)
NUM_VERTICALES = 28
SEPARACION_VERTICALES = 0.075       # fracción del ancho entre verticales, medida en la base
ALTURA_CORDILLERA = 0.18            # fracción del alto del cielo
BINS_ESPECTRO = 32                  # bins de un lado del centro (la silueta es simétrica)
ATAQUE = 0.45                       # suavizado por cuadro al subir
CAIDA = 0.08                        # suavizado por cuadro al bajar
PASADAS_REJILLA = ((4.0, 40), (1.2, 200))   # (ancho, alfa): resplandor y línea fina


def _limpio(valor):
    """Convierte un valor a float en el rango 0..1; lo que no sea un número válido vale 0."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return min(1.0, max(0.0, v))


def _remuestrear(valores, n):
    """Reparte `valores` (de cualquier longitud) en `n` puntos, interpolando linealmente."""
    m = len(valores)
    salida = []
    for j in range(n):
        if m == 1 or n == 1:
            v = valores[0]
        else:
            pos = j * (m - 1) / (n - 1)
            i = min(int(pos), m - 2)
            f = pos - i
            v = valores[i] * (1.0 - f) + valores[i + 1] * f
        salida.append(v)
    return salida


def _mezclar(a, b, u):
    """Interpola dos colores opacos; `u` va de 0 (color a) a 1 (color b)."""
    def mezcla(x, y):
        return int(round(x + (y - x) * u))
    return QColor(mezcla(a.red(), b.red()), mezcla(a.green(), b.green()),
                  mezcla(a.blue(), b.blue()))


def _curva(xs, ys):
    """Curva suave que pasa por los puntos (tangente horizontal en cada punto)."""
    camino = QPainterPath(QPointF(xs[0], ys[0]))
    for i in range(len(xs) - 1):
        mx = (xs[i] + xs[i + 1]) / 2.0
        camino.cubicTo(QPointF(mx, ys[i]), QPointF(mx, ys[i + 1]),
                       QPointF(xs[i + 1], ys[i + 1]))
    return camino


def _yh(h):
    """Fila del horizonte para una pantalla de `h` píxeles de alto."""
    return int(round(h * HORIZONTE))


class FondoSynthwave(QWidget):
    """Fondo animado synthwave a pantalla completa, dibujado con QPainter.

    API pública:
        fijar_espectro(valores: list[float])  frecuencias 0..1; vacío = onda suave de reposo
        poner_acento(color: QColor)           cambia el #FF4FD8 de la rejilla (800 ms)
    """

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        # reloj inyectable: las pruebas lo sustituyen por uno falso
        self._monotonic = time.monotonic
        self._t = self._monotonic()
        self._objetivo = None                       # None = reposo
        self._suave = [0.0] * BINS_ESPECTRO         # valores suavizados de la cordillera
        self._color = QColor(COLOR_ACENTO)          # color mostrado ahora
        self._acento_de = QColor(COLOR_ACENTO)
        self._acento_a = QColor(COLOR_ACENTO)
        self._acento_t0 = self._t
        self._base = None                           # cielo + suelo, cacheado
        self._velo = None                           # desvanecimiento del suelo, cacheado
        self._brillo_px = None                      # franja luminosa del horizonte, cacheada
        self._brillo_y = 0
        self._verticales = None                     # verticales de la rejilla, cacheadas
        self._verticales_clave = None               # (ancho, alto, color) con que se hicieron
        self._base_tam = None

        # estrellas: posiciones fijas (semilla 7); el titileo se calcula por cuadro
        rnd = random.Random(SEMILLA_ESTRELLAS)
        self._estrellas = []
        for _ in range(NUM_ESTRELLAS):
            fx = rnd.random()
            fy = rnd.random() * 0.95
            tam = 2 if rnd.random() < 0.25 else 1
            alfa = rnd.randint(40, 160)
            periodo = rnd.uniform(3.0, 7.0)
            fase = rnd.uniform(0.0, TAU)
            self._estrellas.append((fx, fy, tam, alfa, periodo, fase))

        self._timer = QTimer(self)
        self._timer.setInterval(INTERVALO_MS)
        self._timer.timeout.connect(self._al_tic)

    # ----- API pública -------------------------------------------------------------

    def fijar_espectro(self, valores):
        """Fija las frecuencias (0..1). Lista vacía o None = onda suave de reposo."""
        if valores is None or len(valores) == 0:
            self._objetivo = None
        else:
            limpios = [_limpio(v) for v in valores]
            self._objetivo = _remuestrear(limpios, BINS_ESPECTRO)

    def poner_acento(self, color):
        """Cambia el color de la rejilla y de la cordillera con una transición de 800 ms."""
        self._acento_de = QColor(self._color)
        self._acento_a = QColor(color)
        self._acento_a.setAlpha(255)
        self._acento_t0 = self._monotonic()

    # ----- estado y cuadros --------------------------------------------------------

    def _color_actual(self):
        """Color de acento que se está dibujando en este instante."""
        return QColor(self._color)

    def _avanzar(self, ahora=None):
        """Avanza la animación hasta `ahora` (segundos); lo llama el timer en cada cuadro."""
        if ahora is None:
            ahora = self._monotonic()
        self._t = ahora

        if self._objetivo is None:
            meta = [0.2 + 0.08 * math.sin(TAU * ahora / 6.0 + j * 0.35)
                    for j in range(BINS_ESPECTRO)]
        else:
            meta = self._objetivo
        for j in range(BINS_ESPECTRO):
            paso = ATAQUE if meta[j] > self._suave[j] else CAIDA
            self._suave[j] += (meta[j] - self._suave[j]) * paso

        u = min(1.0, max(0.0, (ahora - self._acento_t0) / DURACION_ACENTO))
        self._color = _mezclar(self._acento_de, self._acento_a, u)

    def _al_tic(self):
        self._avanzar()
        self.update()

    # ----- Qt ----------------------------------------------------------------------

    def showEvent(self, evento):
        super().showEvent(evento)
        self._timer.start()

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._construir_base()

    def paintEvent(self, evento):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if self._base is None or self._base_tam != (w, h):
            self._construir_base()
        yh = _yh(h)
        pintor = QPainter(self)
        try:
            pintor.setRenderHint(QPainter.Antialiasing, True)
            pintor.drawPixmap(0, 0, self._base)
            self._dibujar_estrellas(pintor, w, yh)
            self._dibujar_rejilla(pintor, w, h, yh)
            pintor.drawPixmap(0, yh, self._velo)
            pintor.drawPixmap(0, self._brillo_y, self._brillo_px)
            self._dibujar_cordillera(pintor, w, yh)
        finally:
            pintor.end()

    # ----- dibujo ------------------------------------------------------------------

    def _construir_base(self):
        """Pre-renderiza cielo, brillo del horizonte y suelo. Solo se llama al cambiar de tamaño."""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            self._base = None
            self._base_tam = None
            return
        yh = _yh(h)
        base = QPixmap(w, h)
        pintor = QPainter(base)
        try:
            pintor.setRenderHint(QPainter.Antialiasing, True)

            cielo = QLinearGradient(0, 0, 0, yh)
            cielo.setColorAt(0.0, QColor(COLOR_CIELO_ARRIBA))
            cielo.setColorAt(1.0, QColor(COLOR_CIELO_HORIZONTE))
            pintor.fillRect(QRectF(0, 0, w, yh), QBrush(cielo))

            suelo = QLinearGradient(0, yh, 0, h)
            suelo.setColorAt(0.0, QColor(COLOR_SUELO_HORIZONTE))
            suelo.setColorAt(1.0, QColor(COLOR_SUELO_ABAJO))
            pintor.fillRect(QRectF(0, yh, w, h - yh), QBrush(suelo))
        finally:
            pintor.end()
        self._base = base

        # velo del suelo: color del horizonte que se desvanece hacia abajo; tapa las líneas
        # lejanas (la rejilla se ve morir al acercarse al horizonte)
        alto_velo = max(1, int((h - yh) * 0.5))
        velo = QPixmap(w, alto_velo)
        velo.fill(Qt.transparent)
        pintor = QPainter(velo)
        try:
            degradado = QLinearGradient(0, 0, 0, alto_velo)
            tinta = QColor(COLOR_SUELO_HORIZONTE)
            for pos, alfa in ((0.0, 255), (0.25, 170), (0.6, 40), (1.0, 0)):
                c = QColor(tinta)
                c.setAlpha(alfa)
                degradado.setColorAt(pos, c)
            pintor.fillRect(QRectF(0, 0, w, alto_velo), QBrush(degradado))
        finally:
            pintor.end()
        self._velo = velo

        # franja luminosa del horizonte: elipse muy ancha y plana, con degradado radial.
        # Va en su propio pixmap, centrada en el horizonte, para dibujarse encima del velo
        rx = w * 0.5
        ry = h * 0.03
        alto_brillo = int(2 * ry) + 4
        brillo_px = QPixmap(w, alto_brillo)
        brillo_px.fill(Qt.transparent)
        pintor = QPainter(brillo_px)
        try:
            pintor.setRenderHint(QPainter.Antialiasing, True)
            cy = alto_brillo / 2.0
            pintor.translate(w / 2.0, cy)
            pintor.scale(1.0, ry / rx)
            brillo = QRadialGradient(QPointF(0, 0), rx)
            brillo.setColorAt(0.0, QColor(255, 240, 250, 255))
            brillo.setColorAt(0.12, QColor(255, 110, 199, 230))
            brillo.setColorAt(0.5, QColor(255, 110, 199, 90))
            brillo.setColorAt(1.0, QColor(255, 110, 199, 0))
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(QBrush(brillo))
            pintor.drawEllipse(QPointF(0, 0), rx, rx)
        finally:
            pintor.end()
        self._brillo_px = brillo_px
        self._brillo_y = int(round(yh - alto_brillo / 2.0))
        self._base_tam = (w, h)

    def _dibujar_estrellas(self, pintor, w, yh):
        """Estrellas del cielo con titileo lento (seno de periodo 3-7 s, distinto por estrella)."""
        t = self._t
        pintor.setPen(Qt.NoPen)
        for fx, fy, tam, alfa, periodo, fase in self._estrellas:
            factor = 0.55 + 0.45 * math.sin(TAU * t / periodo + fase)
            a = int(min(255, max(0, alfa * factor)))
            pintor.setBrush(QColor(255, 255, 255, a))
            x = fx * w
            y = fy * yh
            if tam == 1:
                pintor.drawRect(QRectF(x, y, 1, 1))
            else:
                pintor.drawEllipse(QRectF(x, y, 2, 2))

    def _dibujar_rejilla(self, pintor, w, h, yh):
        """Rejilla en perspectiva: horizontales que avanzan hacia la cámara y verticales que convergen."""
        color = self._color
        suelo = h - yh
        F = D_CERCA * suelo                  # y = horizonte + F / profundidad

        # profundidades visibles de las horizontales; el ciclo completo dura PERIODO_VIAJE
        fase = (self._t / PERIODO_VIAJE) % 1.0
        horizontales = []
        k = 0
        while True:
            d = D_CERCA + (k - fase) * DELTA_PROFUNDIDAD
            if d > D_LEJOS:
                break
            if d >= D_CERCA:
                u = (D_LEJOS - d) / (D_LEJOS - D_LLENO)
                u = min(1.0, max(0.0, u))
                g = u * u * (3.0 - 2.0 * u)  # desvanecimiento suave hacia el horizonte
                horizontales.append((yh + F / d, g))
            k += 1

        # las horizontales cambian en cada cuadro, pero son baratas de dibujar
        for ancho, alfa in PASADAS_REJILLA:
            for y, g in horizontales:
                c = QColor(color)
                c.setAlpha(int(alfa * g))
                pintor.setPen(QPen(c, ancho))
                pintor.drawLine(QPointF(0, y), QPointF(w, y))

        # las verticales no se mueven: se rasterizan una vez por color y tamaño, porque
        # las diagonales antialias son lo más caro de la escena
        pintor.drawPixmap(0, yh, self._verticales_px(w, h, yh, color))

    def _verticales_px(self, w, h, yh, color):
        """Pixmap transparente con las verticales que convergen en el horizonte."""
        clave = (w, h, color.name())
        if self._verticales_clave != clave:
            px = QPixmap(w, h - yh)
            px.fill(Qt.transparent)
            pintor = QPainter(px)
            try:
                pintor.setRenderHint(QPainter.Antialiasing, True)
                cx = w / 2.0
                paso = w * SEPARACION_VERTICALES
                for ancho, alfa in PASADAS_REJILLA:
                    c = QColor(color)
                    c.setAlpha(alfa)
                    pintor.setPen(QPen(c, ancho))
                    for i in range(NUM_VERTICALES):
                        xb = cx + (i - (NUM_VERTICALES - 1) / 2.0) * paso
                        pintor.drawLine(QPointF(cx, 0), QPointF(xb, h - yh))
            finally:
                pintor.end()
            self._verticales = px
            self._verticales_clave = clave
        # el desvanecimiento hacia el horizonte lo pone el velo que se dibuja después
        return self._verticales

    def _dibujar_cordillera(self, pintor, w, yh):
        """Silueta de frecuencias simétrica sobre el horizonte, con su reflejo al 25 %."""
        s = self._suave
        H = len(s)
        alto = ALTURA_CORDILLERA * yh
        # espejo en el centro: el bin 0 queda en el medio y los extremos en los bordes
        V = [s[abs(i - (H - 1))] for i in range(2 * H - 1)]
        n = len(V)
        xs = [i * w / (n - 1) for i in range(n)]
        color = self._color

        for reflejo in (False, True):
            signo = 1.0 if reflejo else -1.0
            ys = [yh + signo * alto * v for v in V]
            curva = _curva(xs, ys)
            relleno = QPainterPath(curva)
            relleno.lineTo(w, yh)
            relleno.lineTo(0, yh)
            relleno.closeSubpath()

            # el degradado va de la cresta (alfa 90) hacia el horizonte (transparente)
            degradado = QLinearGradient(0, yh + signo * alto, 0, yh)
            c0 = QColor(color)
            c0.setAlpha(90)
            c1 = QColor(color)
            c1.setAlpha(0)
            degradado.setColorAt(0.0, c0)
            degradado.setColorAt(1.0, c1)

            pintor.save()
            if reflejo:
                pintor.setOpacity(0.25)
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(QBrush(degradado))
            pintor.drawPath(relleno)
            pintor.setBrush(Qt.NoBrush)
            cresta = QColor(COLOR_CRESTA)
            cresta.setAlpha(220)
            pintor.setPen(QPen(cresta, 1.5))
            pintor.drawPath(curva)
            pintor.restore()
