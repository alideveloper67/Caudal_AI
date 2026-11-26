# -*- coding: utf-8 -*-
"""Fondo ambiente de la escena: la carátula desenfocada y viva a pantalla completa.

Pieza OPACA: cubre toda su área con su propio dibujo (sin transparencia). Capas, de abajo
arriba: carátula muy desenfocada con movimiento Ken Burns, aurora de dos manchas de color
que derivan despacio, viñeta con degradado inferior y grano de película.

Lo caro se prepara una sola vez (al cambiar de carátula o de tamaño); en cada cuadro solo
se colocan pixmaps ya hechos.
"""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

from ..componentes import a_la_vista
from .estilo import BRILLO, DOMINANTE, SEGUNDO, con_alfa

FPS = 15                            # el movimiento es lentísimo (ciclos de 30-45 s)
INTERVALO_MS = 1000 // FPS          # 66 ms
TAU = 2.0 * math.pi
PERIODO_KEN_BURNS = 45.0            # segundos por ciclo de zoom y desplazamiento
PERIODO_AURORA_1 = 31.0
PERIODO_AURORA_2 = 37.0
DURACION_FUNDIDO = 1.2              # segundos del fundido cruzado entre carátulas
ESCALA_BASE = 1.18                  # la capa base se genera un 18 % más grande que el widget
ALTO_MINI = 12                      # alto al que se reduce la carátula para desenfocarla
BRILLO_FONDO = 0.45                 # oscurecimiento de la base y del degradado sin carátula
ALFA_AURORA = 70
RADIO_AURORA = 0.60                 # radio de cada mancha, en proporción al ancho
ESCALA_MANCHA = 0.5                 # las manchas se pintan a la mitad y se estiran al dibujar
TAM_GRANO = 256
ALFA_GRANO = 12


def _oscurecer(c, factor=BRILLO_FONDO):
    """Un color al factor indicado de su brillo (0.45 = al 45 %)."""
    c = QColor(c)
    return QColor(int(c.red() * factor), int(c.green() * factor), int(c.blue() * factor))


class FondoAmbiente(QWidget):
    """Fondo a pantalla completa de la escena: carátula desenfocada, aurora y grano.

    API pública:
        poner_portada(img: QImage)           cambia la carátula (None o nula = sin carátula)
        poner_colores(dominante, segundo, brillo)
        fijar_movimiento(si: bool)           False = imagen quieta, sin timer
    """

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        # reloj inyectable: las pruebas lo sustituyen por uno falso
        self._monotonic = time.monotonic
        self._t0 = self._monotonic()
        self._t_congelado = 0.0
        self._movimiento = True

        self._portada = None            # QImage original
        self._base = None               # QPixmap desenfocado al 118 %
        self._base_viejo = None         # base anterior, durante el fundido
        self._fondo_sin = None          # degradado diagonal sin carátula
        self._manchas = [None, None]    # aurora pre-renderizada (dominante, segundo)
        self._capas = None              # viñeta + degradado inferior
        self._sucio = True              # hay que regenerar degradado, aurora y capas
        self._sucio_base = True         # hay que regenerar la base desenfocada

        self._dominante = QColor(DOMINANTE)
        self._segundo = QColor(SEGUNDO)
        self._brillo = QColor(BRILLO)   # guardado; de momento no se dibuja

        self._fundiendo = False
        self._inicio_fundido = 0.0
        self._rnd = random.Random()
        self._grano = self._generar_grano()

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(INTERVALO_MS)
        self._timer.timeout.connect(self._tic)

    # ------------------------------------------------------------------ API pública

    def poner_portada(self, img):
        """Pone una carátula nueva con fundido cruzado de 1.2 s desde la anterior."""
        self._asegurar_base()
        viejo = self._base if not self._sucio_base else None
        if img is None or img.isNull():
            self._portada = None
        else:
            self._portada = QImage(img)
        self._base = None
        self._sucio_base = True
        self._base_viejo = viejo
        self._fundiendo = True
        self._inicio_fundido = self._monotonic()
        self.update()
        self._arrancar_si_procede()

    def poner_colores(self, dominante, segundo, brillo):
        """Colores de la carátula: dominante y segundo tiñen la aurora y el degradado."""
        self._dominante = QColor(dominante)
        self._segundo = QColor(segundo)
        self._brillo = QColor(brillo)
        self._sucio = True
        self.update()
        self._arrancar_si_procede()

    def fijar_movimiento(self, si):
        """True = Ken Burns y aurora en marcha; False = imagen quieta y sin timer."""
        si = bool(si)
        if si != self._movimiento:
            if si:
                self._t0 = self._monotonic() - self._t_congelado
            else:
                self._t_congelado = self._tiempo()
            self._movimiento = si
            self.update()
        self._arrancar_si_procede()

    # ------------------------------------------------------------------ eventos

    def showEvent(self, evento):
        super().showEvent(evento)
        self._arrancar_si_procede()

    def hideEvent(self, evento):
        super().hideEvent(evento)
        self._timer.stop()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._sucio = True
        self._sucio_base = True
        self._base = None
        self._base_viejo = None
        self._fundiendo = False

    def paintEvent(self, evento):
        if not self._tam_valido():
            return
        self._preparar()
        self._actualizar_fundido()
        t = self._tiempo()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self._fundiendo:
            avance = self._progreso_fundido()
            if self._base_viejo is not None:
                self._dibujar_base(p, self._base_viejo, 1.0, t)
            else:
                self._dibujar_sin_portada(p, 1.0)
            if self._base is not None:
                self._dibujar_base(p, self._base, avance, t)
            else:
                self._dibujar_sin_portada(p, avance)
        elif self._base is not None:
            self._dibujar_base(p, self._base, 1.0, t)
        else:
            self._dibujar_sin_portada(p, 1.0)

        self._dibujar_aurora(p, t)
        if self._capas is not None:
            p.drawPixmap(0, 0, self._capas)
        self._dibujar_grano(p)
        p.end()

    # ------------------------------------------------------------------ tiempo y timer

    def _tiempo(self):
        """Segundos de movimiento transcurridos (congelados si el movimiento está apagado)."""
        if self._movimiento:
            return self._monotonic() - self._t0
        return self._t_congelado

    def _progreso_fundido(self):
        if not self._fundiendo:
            return 1.0
        return min(1.0, max(0.0, (self._monotonic() - self._inicio_fundido) / DURACION_FUNDIDO))

    def _actualizar_fundido(self):
        if self._fundiendo and self._progreso_fundido() >= 1.0:
            self._fundiendo = False
            self._base_viejo = None

    def _necesita_animar(self):
        return self._movimiento or self._fundiendo

    def _arrancar_si_procede(self):
        """El timer solo corre si el widget se ve y hay algo que animar."""
        if a_la_vista(self) and self._necesita_animar():
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def _tic(self):
        self._actualizar_fundido()
        if not a_la_vista(self):
            self._timer.stop()
            return
        self.update()
        if not self._necesita_animar():
            self._timer.stop()

    # ------------------------------------------------------------------ preparación (solo al cambiar)

    def _tam_valido(self):
        return self.width() > 0 and self.height() > 0

    def _preparar(self):
        self._asegurar_base()
        if self._sucio and self._tam_valido():
            self._fondo_sin = self._generar_fondo_sin()
            self._manchas = [self._generar_mancha(self._dominante),
                             self._generar_mancha(self._segundo)]
            self._capas = self._generar_capas()
            self._sucio = False

    def _asegurar_base(self):
        if self._sucio_base and self._tam_valido():
            self._base = self._generar_base() if self._portada is not None else None
            self._sucio_base = False

    def _generar_base(self):
        """Carátula en cover, reducida a 28 px de alto, ampliada en dos pasos y oscurecida."""
        tw = max(1, round(self.width() * ESCALA_BASE))
        th = max(1, round(self.height() * ESCALA_BASE))
        sw = max(1, round(ALTO_MINI * tw / th))
        pequena = self._portada.scaled(sw, ALTO_MINI, Qt.KeepAspectRatioByExpanding,
                                       Qt.SmoothTransformation)
        x0 = (pequena.width() - sw) // 2
        y0 = (pequena.height() - ALTO_MINI) // 2
        pequena = pequena.copy(x0, y0, sw, ALTO_MINI)
        # ampliación en tres pasos: x4, x4 y el paso final al tamaño de la base
        paso1 = pequena.scaled(sw * 4, ALTO_MINI * 4, Qt.IgnoreAspectRatio,
                               Qt.SmoothTransformation)
        paso2 = paso1.scaled(sw * 16, ALTO_MINI * 16, Qt.IgnoreAspectRatio,
                             Qt.SmoothTransformation)
        # pasada de suavizado extra: la intermedia se dibuja 4 veces desplazada +-1 px
        suavizada = paso2.convertToFormat(QImage.Format_RGB32)
        p = QPainter(suavizada)
        try:
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(0.25)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                p.drawImage(dx, dy, paso2)
        finally:
            p.end()
        final = suavizada.scaled(tw, th, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        final = final.convertToFormat(QImage.Format_RGB32)
        p = QPainter(final)
        try:
            p.setCompositionMode(QPainter.CompositionMode_Multiply)
            v = round(255 * BRILLO_FONDO)
            p.fillRect(0, 0, tw, th, QColor(v, v, v))
        finally:
            p.end()
        return QPixmap.fromImage(final)

    def _generar_fondo_sin(self):
        """Degradado diagonal de segundo oscurecido a dominante oscurecido."""
        W, H = self.width(), self.height()
        pix = QPixmap(W, H)
        p = QPainter(pix)
        try:
            grad = QLinearGradient(0, 0, W, H)
            grad.setColorAt(0.0, _oscurecer(self._segundo))
            grad.setColorAt(1.0, _oscurecer(self._dominante))
            p.fillRect(0, 0, W, H, QBrush(grad))
        finally:
            p.end()
        return pix

    def _generar_mancha(self, color):
        """Mancha radial de color con alfa 70, a la mitad de resolución."""
        R = RADIO_AURORA * self.width()
        d = max(2, int(R * 2 * ESCALA_MANCHA))
        pix = QPixmap(d, d)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            grad = QRadialGradient(QPointF(d / 2, d / 2), d / 2)
            grad.setColorAt(0.0, con_alfa(color, ALFA_AURORA))
            grad.setColorAt(0.45, con_alfa(color, ALFA_AURORA * 0.45))
            grad.setColorAt(1.0, con_alfa(color, 0))
            p.fillRect(0, 0, d, d, QBrush(grad))
        finally:
            p.end()
        return pix

    def _generar_capas(self):
        """Viñeta (bordes oscuros) y degradado inferior, en un solo pixmap transparente."""
        W, H = self.width(), self.height()
        pix = QPixmap(W, H)
        pix.fill(QColor(0, 0, 0, 0))
        p = QPainter(pix)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            vineta = QRadialGradient(QPointF(W / 2, H / 2), math.hypot(W, H) / 2)
            vineta.setColorAt(0.0, QColor(0, 0, 0, 0))
            vineta.setColorAt(0.55, QColor(0, 0, 0, 0))
            vineta.setColorAt(1.0, QColor(0, 0, 0, 165))
            p.fillRect(0, 0, W, H, QBrush(vineta))
            abajo = QLinearGradient(0, H * 0.55, 0, H)
            abajo.setColorAt(0.0, QColor(0, 0, 0, 0))
            abajo.setColorAt(1.0, QColor(0, 0, 0, 175))
            p.fillRect(0, 0, W, H, QBrush(abajo))
        finally:
            p.end()
        return pix

    @staticmethod
    def _generar_grano():
        """Textura de ruido de 256x256 (alfa 12), generada una sola vez."""
        rnd = random.Random(7)
        datos = bytearray(TAM_GRANO * TAM_GRANO * 4)
        for i in range(0, len(datos), 4):
            v = rnd.randrange(ALFA_GRANO + 1)     # premultiplicado: color <= alfa
            datos[i] = v
            datos[i + 1] = v
            datos[i + 2] = v
            datos[i + 3] = ALFA_GRANO
        bruto = bytes(datos)
        img = QImage(bruto, TAM_GRANO, TAM_GRANO, TAM_GRANO * 4,
                     QImage.Format_ARGB32_Premultiplied).copy()
        return QPixmap.fromImage(img)

    # ------------------------------------------------------------------ dibujo por cuadro

    def _dibujar_base(self, p, pix, opacidad, t):
        """La carátula desenfocada con Ken Burns: zoom 1.00-1.06 y deriva lenta de 45 s."""
        W, H = self.width(), self.height()
        f = TAU * t / PERIODO_KEN_BURNS
        zoom = 1.03 + 0.03 * math.sin(f)
        rw = W * ESCALA_BASE * zoom
        rh = H * ESCALA_BASE * zoom
        sx = (rw - W) / 2
        sy = (rh - H) / 2
        # el desplazamiento nunca deja al descubierto un borde
        x = (W - rw) / 2 + sx * 0.9 * math.sin(f)
        y = (H - rh) / 2 + sy * 0.9 * math.cos(f)
        p.setOpacity(opacidad)
        p.drawPixmap(QRectF(x, y, rw, rh), pix, QRectF(0, 0, pix.width(), pix.height()))
        p.setOpacity(1.0)

    def _dibujar_sin_portada(self, p, opacidad):
        if self._fondo_sin is None:
            return
        p.setOpacity(opacidad)
        p.drawPixmap(0, 0, self._fondo_sin)
        p.setOpacity(1.0)

    def _dibujar_aurora(self, p, t):
        """Dos manchas enormes que derivan (ciclos de 31 s y 37 s), en modo Plus."""
        W, H = self.width(), self.height()
        R = RADIO_AURORA * W
        fa = TAU * t / PERIODO_AURORA_1
        fb = TAU * t / PERIODO_AURORA_2 + 1.3
        centros = [
            (W * 0.30 + W * 0.16 * math.cos(fa), H * 0.38 + H * 0.14 * math.sin(fa)),
            (W * 0.72 + W * 0.14 * math.cos(fb), H * 0.62 + H * 0.16 * math.sin(fb)),
        ]
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        for mancha, (cx, cy) in zip(self._manchas, centros):
            if mancha is None:
                continue
            p.drawPixmap(QRectF(cx - R, cy - R, 2 * R, 2 * R), mancha,
                         QRectF(0, 0, mancha.width(), mancha.height()))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)

    def _dibujar_grano(self, p):
        """El grano se tesela con un desfase aleatorio en cada cuadro (quieto sin movimiento)."""
        if self._movimiento:
            dx = self._rnd.randrange(TAM_GRANO)
            dy = self._rnd.randrange(TAM_GRANO)
        else:
            dx = dy = 0
        p.drawTiledPixmap(0, 0, self.width(), self.height(), self._grano, dx, dy)
