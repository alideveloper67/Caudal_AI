# -*- coding: utf-8 -*-
"""Marco de brillo de la escena: cuatro franjas, una por borde de la pantalla, que
resplandecen hacia dentro con los colores de la carátula.

Cada borde es un BordeBrillo propio. Su resplandor nace pegado al borde exterior y se
apaga hacia dentro; el color recorre el borde a lo largo y respira (o sigue al nivel del
audio si alguien lo fija). Todo se pinta con QPainter, sin QGraphicsEffect.
"""

import math
import time

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from ..componentes import a_la_vista
from .estilo import BRILLO, DOMINANTE, SEGUNDO, acento_legible, mezclar, preparar_transparente

LADOS = ("arriba", "abajo", "izquierda", "derecha")


def geometrias_borde(rect_pantalla: QRect, grosor: int) -> dict[str, QRect]:
    """Las cuatro franjas de `grosor` px pegadas a cada borde, por dentro del rectángulo.

    Arriba y abajo ocupan todo el ancho; las laterales ocupan todo el alto. Las esquinas
    quedan cubiertas por dos franjas a la vez: se solapan, y eso está bien porque son
    translúcidas. Si el grosor pide más de la mitad del lado, se recorta a la mitad.
    """
    if grosor < 1:
        raise ValueError("el grosor debe ser de al menos 1 px")
    ancho, alto = rect_pantalla.width(), rect_pantalla.height()
    g = min(int(grosor), ancho // 2, alto // 2)
    x, y = rect_pantalla.x(), rect_pantalla.y()
    return {
        "arriba": QRect(x, y, ancho, g),
        "abajo": QRect(x, y + alto - g, ancho, g),
        "izquierda": QRect(x, y, g, alto),
        "derecha": QRect(x + ancho - g, y, g, alto),
    }


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class BordeBrillo(QWidget):
    """Una franja translúcida de resplandor en un borde de la pantalla.

    Colores: `poner_colores` cambia dominante, segundo y brillo con una transición de
    800 ms. Intensidad: `fijar_intensidad` (0..1, por defecto 0.85). Nivel del audio:
    `fijar_nivel` (0..1); si nunca se llama, la intensidad respira con periodo de 5 s.
    """

    PERIODO_COLOR = 14.0        # s para que el color recorra el borde entero
    PERIODO_RESPIRACION = 5.0   # s de la respiración
    DURACION_TRANSICION = 0.8   # s del cambio de colores
    CONSTANTE_NIVEL = 0.12      # s del suavizado del nivel del audio
    FPS = 10

    def __init__(self, lado: str, padre=None):
        if lado not in LADOS:
            raise ValueError(f"lado inválido: {lado!r}; debe ser uno de {LADOS}")
        super().__init__(padre)
        self._lado = lado
        self._horizontal = lado in ("arriba", "abajo")
        # reloj inyectable: las pruebas lo cambian por uno falso
        self._monotonic = time.monotonic
        self._t0 = self._monotonic()
        self._colores = (acento_legible(DOMINANTE), acento_legible(SEGUNDO), acento_legible(BRILLO))
        self._transicion = None            # (colores de origen, destino, instante de inicio)
        self._intensidad = 0.85
        self._nivel_objetivo = None
        self._nivel_suave = 0.0
        self._t_ultimo = None
        self._tamano = None                # tamaño para el que están hechas máscara y buffer
        self._mascara = None
        self._buffer = None                # QImage ARGB premultiplicado, transparente
        self._clave_franja = None
        self._franja = None

        preparar_transparente(self)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(int(1000 / self.FPS))
        self._timer.timeout.connect(self._tic)

    # ------------------------------------------------------------------ API pública
    def poner_colores(self, dominante, segundo, brillo):
        """Cambia los tres colores; la transición dura 800 ms desde los colores actuales."""
        ahora = self._monotonic()
        actuales = self._colores_actuales(ahora)
        # un resplandor nunca oscurece: los tres tonos se aclaran hasta ser luz
        destino = (acento_legible(dominante), acento_legible(segundo), acento_legible(brillo))
        self._transicion = (actuales, destino, ahora)
        self.update()

    def fijar_intensidad(self, v: float):
        """Intensidad base 0..1 (por defecto 0.85)."""
        self._intensidad = max(0.0, min(1.0, float(v)))
        self.update()

    def fijar_nivel(self, v: float):
        """Nivel del audio 0..1; la intensidad sigue a este valor suavizado."""
        self._nivel_objetivo = max(0.0, min(1.0, float(v)))
        self.update()

    # ------------------------------------------------------------------ cálculos
    def _colores_actuales(self, ahora):
        if self._transicion is None:
            return self._colores
        origen, destino, inicio = self._transicion
        t = (ahora - inicio) / self.DURACION_TRANSICION
        if t >= 1.0:
            self._colores = destino
            self._transicion = None
            return destino
        e = _smoothstep(t)
        return tuple(mezclar(a, b, e) for a, b in zip(origen, destino))

    def _factor_intensidad(self, ahora):
        """Multiplicador 0..1 de la intensidad base: respiración o nivel del audio."""
        dt = 0.0 if self._t_ultimo is None else min(0.2, max(0.0, ahora - self._t_ultimo))
        self._t_ultimo = ahora
        if self._nivel_objetivo is None:
            fase = 2.0 * math.pi * (ahora - self._t0) / self.PERIODO_RESPIRACION
            return 0.925 + 0.075 * math.cos(fase)        # entre 0.85 y 1.0
        k = 1.0 - math.exp(-dt / self.CONSTANTE_NIVEL)
        self._nivel_suave += (self._nivel_objetivo - self._nivel_suave) * k
        return 0.25 + 0.75 * self._nivel_suave

    def _asegurar_recursos(self, ancho, alto):
        """Máscara de desvanecimiento y buffer, rehechos solo si cambia el tamaño."""
        if self._tamano != (ancho, alto):
            self._mascara = self._renderizar_mascara(ancho, alto)
            self._buffer = QImage(ancho, alto, QImage.Format_ARGB32_Premultiplied)
            self._tamano = (ancho, alto)
            self._clave_franja = None

    def _renderizar_mascara(self, ancho, alto):
        """Máscara de alfa: 255 en el borde exterior, 0 exacto en el interior.

        Solo importa su alfa (se usa con DestinationIn); el color es negro transparente
        para que nunca tiña nada de oscuro. Curva suave: 255 → 120 → 30 → 0."""
        m = QImage(ancho, alto, QImage.Format_ARGB32_Premultiplied)
        m.fill(Qt.transparent)
        if self._lado == "arriba":
            inicio, fin = (0, 0), (0, alto)
        elif self._lado == "abajo":
            inicio, fin = (0, alto), (0, 0)
        elif self._lado == "izquierda":
            inicio, fin = (0, 0), (ancho, 0)
        else:
            inicio, fin = (ancho, 0), (0, 0)
        grad = QLinearGradient(QPointF(*inicio), QPointF(*fin))
        for posicion, alfa in ((0.0, 255), (0.35, 120), (0.7, 30), (1.0, 0)):
            grad.setColorAt(posicion, QColor(0, 0, 0, alfa))
        p = QPainter(m)
        try:
            p.fillRect(m.rect(), grad)
        finally:
            p.end()
        return m

    def _renderizar_franja(self, longitud, dom, seg, bri):
        """Franja de color de 1 px de grosor y el doble de la longitud del borde.

        El patrón dominante → brillo → segundo → dominante se repite cada media franja,
        así que desplazarla un tramo de longitud del borde sigue siendo continuo."""
        n = 2 * longitud
        franja = QImage(n, 1, QImage.Format_ARGB32_Premultiplied) if self._horizontal \
            else QImage(1, n, QImage.Format_ARGB32_Premultiplied)
        franja.fill(Qt.transparent)
        fin = QPointF(n, 0) if self._horizontal else QPointF(0, n)
        grad = QLinearGradient(QPointF(0, 0), fin)
        paradas = ((0.0, dom), (1 / 6, bri), (2 / 6, seg), (3 / 6, dom),
                   (4 / 6, bri), (5 / 6, seg), (1.0, dom))
        for posicion, color in paradas:
            grad.setColorAt(posicion, color)
        p = QPainter(franja)
        try:
            p.fillRect(franja.rect(), grad)
        finally:
            p.end()
        return franja

    def _rect_linea(self, ancho, alto):
        """Línea caliente de 2 px pegada al borde exterior."""
        if self._lado == "arriba":
            return QRect(0, 0, ancho, 2)
        if self._lado == "abajo":
            return QRect(0, alto - 2, ancho, 2)
        if self._lado == "izquierda":
            return QRect(0, 0, 2, alto)
        return QRect(ancho - 2, 0, 2, alto)

    # ------------------------------------------------------------------ dibujo
    def paintEvent(self, evento):
        ancho, alto = self.width(), self.height()
        if ancho < 1 or alto < 1:
            return
        ahora = self._monotonic()
        dom, seg, bri = self._colores_actuales(ahora)
        self._asegurar_recursos(ancho, alto)

        longitud = ancho if self._horizontal else alto
        grosor = alto if self._horizontal else ancho
        clave = (longitud, dom.rgb(), seg.rgb(), bri.rgb())
        if clave != self._clave_franja:
            self._franja = self._renderizar_franja(longitud, dom, seg, bri)
            self._clave_franja = clave

        desfase = ((ahora - self._t0) / self.PERIODO_COLOR) % 1.0 * longitud
        intensidad = self._intensidad * self._factor_intensidad(ahora)

        # el color recorre el borde, se enmascara y se compone en el buffer
        self._buffer.fill(Qt.transparent)
        p = QPainter(self._buffer)
        try:
            if self._horizontal:
                p.drawImage(QRectF(-desfase, 0, 2 * longitud, grosor), self._franja,
                            QRectF(0, 0, 2 * longitud, 1))
            else:
                p.drawImage(QRectF(0, -desfase, grosor, 2 * longitud), self._franja,
                            QRectF(0, 0, 1, 2 * longitud))
            p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p.drawImage(0, 0, self._mascara)
        finally:
            p.end()

        p = QPainter(self)
        p.setOpacity(intensidad)
        p.drawImage(0, 0, self._buffer)
        p.setOpacity(1.0)
        linea = QColor(bri.red(), bri.green(), bri.blue(), 230)
        p.fillRect(self._rect_linea(ancho, alto), linea)
        p.end()

    # ------------------------------------------------------------------ animación
    def showEvent(self, evento):
        super().showEvent(evento)
        self._timer.start()

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def _tic(self):
        if not a_la_vista(self):
            self._timer.stop()
            return
        self.update()
