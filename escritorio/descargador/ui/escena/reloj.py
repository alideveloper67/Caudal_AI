# -*- coding: utf-8 -*-
"""Reloj gigante de la escena: la hora enorme, translúcida, con la fecha encima.

Cuando cambia el minuto, cada dígito que cambia sube y se desvanece mientras el nuevo
entra desde abajo. Los colores cambian con una transición suave. Todo con QPainter.
"""

import time
from datetime import datetime

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen,
                           QTransform)
from PySide6.QtWidgets import QWidget

from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, TEXTO_2, acento_legible, con_alfa, fuente,
                     fuente_fina, mezclar, preparar_transparente)

DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

ALTO_DIGITOS = 0.88     # fracción de la altura del widget que ocupan los dígitos
TOP_DIGITOS = 0.10      # dónde empieza la tinta de los dígitos (fracción de la altura)
MARGEN_DER = 0.035      # margen derecho (fracción del ancho)
MAX_ANCHO = 0.96        # tope de ancho por si la hora no cabe (fracción del ancho)
ESTIRADO = 1.38         # los dígitos se estiran en vertical: altos y estrechos, como póster
PX_BASE = 200           # tamaño de medida; luego todo se escala con QTransform
DESPLAZ = 0.30          # cuánto sube el dígito viejo (fracción de la altura de dígito)
DUR_DIGITO = 0.650      # segundos de la transición de cada dígito
DUR_COLOR = 0.700       # segundos de la transición de colores


def texto_hora(dt, h24=True):
    """Hora sin cero a la izquierda: «7:05», «19:05» (24h) o «12:30» (12h)."""
    if h24:
        return f"{dt.hour}:{dt.minute:02d}"
    h = dt.hour % 12 or 12
    return f"{h}:{dt.minute:02d}"


def texto_fecha(dt):
    """Fecha corta en español sin usar locale: «vie 20 nov»."""
    return f"{DIAS[dt.weekday()]} {dt.day} {MESES[dt.month - 1]}"


def _ease(t):
    """Curva ease-out cúbica (t entre 0 y 1)."""
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


def _medir(texto):
    """Caja de tinta del texto entero y un camino por carácter, a PX_BASE."""
    f = fuente_fina(PX_BASE)
    fm = QFontMetricsF(f)
    estirar = QTransform().scale(1.0, ESTIRADO)
    total = QPainterPath()
    total.addText(0, 0, f, texto)
    total = estirar.map(total)
    unidades = []
    for i, ch in enumerate(texto):
        g = QPainterPath()
        g.addText(fm.horizontalAdvance(texto[:i]), 0, f, ch)
        unidades.append(estirar.map(g))
    return total.boundingRect(), unidades


class _Maqueta:
    """Lo medido de un texto y cómo se coloca en el widget (escala k y posición)."""

    def __init__(self, texto, caja, unidades, k, dx, ty):
        self.texto = texto
        self.caja = caja
        self.unidades = unidades
        self.k = k
        self.dx = dx
        self.ty = ty


def _pintar_camino(p, camino, acento, a):
    """Resplandor de tres trazos, relleno del acento y un filo blanco fino.
    `a` es la opacidad (0 a 1) para las transiciones."""
    if a <= 0.005 or camino.isEmpty():
        return
    # las fuentes tienen contornos que se solapan: con relleno par-impar se verían agujeros
    camino.setFillRule(Qt.WindingFill)
    for ancho, alfa in ((22, 18), (12, 30)):
        pluma = QPen(con_alfa(acento, alfa * a))
        pluma.setWidthF(ancho)
        pluma.setCapStyle(Qt.RoundCap)
        pluma.setJoinStyle(Qt.RoundJoin)
        p.strokePath(camino, pluma)
    p.fillPath(camino, con_alfa(acento, 255 * a))
    filo = QPen(con_alfa(QColor(255, 255, 255), 60 * a))
    filo.setWidthF(0.8)
    p.strokePath(camino, filo)


class RelojGigante(QWidget):
    """Hora enorme sobre fondo transparente, con la fecha encima de los dígitos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        preparar_transparente(self)
        self.dominante = QColor(DOMINANTE)
        self.segundo = QColor(SEGUNDO)
        self._acento_destino = acento_legible(BRILLO)
        self._trans_col = None          # {"t0", "origen"} mientras cambian los colores
        self._trans_dig = None          # {"t0", "pares", "viejo"} mientras cambia un minuto
        self._h24 = True
        self._ahora = datetime.now      # inyectable para pruebas
        self._monotonic = time.monotonic  # inyectable para pruebas
        ahora = self._ahora()
        self._texto = texto_hora(ahora, self._h24)
        self._fecha = texto_fecha(ahora)
        self._m = None
        self._m_tam = None
        self._anim = QTimer(self)       # 16 ms solo durante una transición
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._tick_animacion)
        self._reloj = QTimer(self)      # 1 s, solo mientras el widget se ve
        self._reloj.setInterval(1000)
        self._reloj.timeout.connect(self._comprobar)

    def sizeHint(self):
        return QSize(560, 320)

    def poner_colores(self, dominante, segundo, brillo):
        """Fija los colores de la carátula. El acento cambia en 700 ms."""
        self.dominante = QColor(dominante)
        self.segundo = QColor(segundo)
        destino = acento_legible(brillo)
        if destino == self._acento_destino:
            return
        origen = self._acento_actual()
        self._acento_destino = destino
        self._trans_col = {"t0": self._monotonic(), "origen": origen}
        self._asegurar_anim()
        self.update()

    def fijar_24h(self, si):
        """Cambia entre formato de 24 y de 12 horas (sin animación)."""
        self._h24 = bool(si)
        self._cambiar_texto(texto_hora(self._ahora(), self._h24), animar=False)
        self.update()

    def fijar_ahora(self, funcion):
        """Reemplaza la fuente de la hora (por defecto datetime.now) y la muestra en el acto,
        sin animar. Los cambios de minuto posteriores sí se animan al detectarlos."""
        self._ahora = funcion
        ahora = funcion()
        self._fecha = texto_fecha(ahora)
        self._cambiar_texto(texto_hora(ahora, self._h24), animar=False)
        self.update()

    # ----- estado y transiciones -----

    def showEvent(self, ev):
        super().showEvent(ev)
        self._sincronizar()
        self._reloj.start()
        self._asegurar_anim()

    def hideEvent(self, ev):
        super().hideEvent(ev)
        self._reloj.stop()
        self._anim.stop()

    def _sincronizar(self):
        """Pone la hora al día sin animar (por si cambió mientras estaba oculto)."""
        ahora = self._ahora()
        nuevo = texto_hora(ahora, self._h24)
        if nuevo != self._texto:
            self._cambiar_texto(nuevo, animar=False)
        self._fecha = texto_fecha(ahora)

    def _comprobar(self):
        """Lo llama el reloj de 1 s: si cambió la hora, arranca la transición."""
        ahora = self._ahora()
        nuevo = texto_hora(ahora, self._h24)
        if nuevo != self._texto:
            self._cambiar_texto(nuevo, animar=True)
        fecha = texto_fecha(ahora)
        if fecha != self._fecha:
            self._fecha = fecha
            self.update()

    def _cambiar_texto(self, nuevo, animar=True):
        """Pasa a mostrar `nuevo`. Con `animar`, los dígitos que cambian se animan."""
        viejo = self._texto
        W, H = max(1, self.width()), max(1, self.height())
        nuevo_m = self._maquetar(nuevo)
        self._trans_dig = None
        pares = []
        if animar and viejo != nuevo:
            # se comparan alineados por la derecha; los ':' nunca se animan
            n, o = len(nuevo), len(viejo)
            for k in range(1, min(n, o) + 1):
                ii, io = n - k, o - k
                a, b = nuevo[ii], viejo[io]
                if a != b and a.isdigit() and b.isdigit():
                    pares.append((ii, io))
        self._texto = nuevo
        self._m = nuevo_m
        self._m_tam = (W, H)
        if pares:
            self._trans_dig = {"t0": self._monotonic(), "pares": pares,
                               "viejo": self._maquetar(viejo, ref=nuevo_m)}
        self._asegurar_anim()
        self.update()

    def _asegurar_anim(self):
        """Arranca el timer de 16 ms solo si hay algo que animar y el widget se ve."""
        hay = self._trans_dig is not None or self._trans_col is not None
        if hay and a_la_vista(self) and not self._anim.isActive():
            self._anim.start()

    def _tick_animacion(self):
        """Un paso de la animación: cierra las transiciones cumplidas y repinta."""
        ahora = self._monotonic()
        if self._trans_dig is not None and ahora - self._trans_dig["t0"] >= DUR_DIGITO:
            self._trans_dig = None
        if self._trans_col is not None and ahora - self._trans_col["t0"] >= DUR_COLOR:
            self._trans_col = None
        self.update()
        sin_nada = self._trans_dig is None and self._trans_col is None
        if sin_nada or not a_la_vista(self):
            self._anim.stop()

    def _acento_actual(self):
        """El acento que toca ahora, mezclando si hay transición de color."""
        tr = self._trans_col
        if tr is None:
            return QColor(self._acento_destino)
        t = (self._monotonic() - tr["t0"]) / DUR_COLOR
        return mezclar(tr["origen"], self._acento_destino, _ease(t))

    # ----- geometría -----

    def _maquetar(self, texto, ref=None):
        """Escala y posición de `texto`. Con `ref` usa la misma escala y altura que él."""
        W, H = max(1, self.width()), max(1, self.height())
        caja, unidades = _medir(texto)
        if ref is None:
            alto = caja.height()
            k = H * ALTO_DIGITOS / alto if alto > 0 else 1.0
            if caja.width() > 0 and caja.width() * k > W * MAX_ANCHO:
                k = W * MAX_ANCHO / caja.width()
            ty = H * TOP_DIGITOS - k * caja.top()
        else:
            k, ty = ref.k, ref.ty
        dx = W * (1 - MARGEN_DER) - k * caja.right()
        return _Maqueta(texto, caja, unidades, k, dx, ty)

    def _camino(self, m, i, oy=0.0):
        """Camino del carácter i ya colocado en el widget, desplazado `oy` píxeles."""
        t = QTransform()
        t.translate(m.dx, m.ty + oy)
        t.scale(m.k, m.k)
        return t.map(m.unidades[i])

    # ----- pintura -----

    def paintEvent(self, _ev):
        W, H = max(1, self.width()), max(1, self.height())
        if self._m is None or self._m_tam != (W, H):
            self._m = self._maquetar(self._texto)
            self._m_tam = (W, H)
        m = self._m
        acento = self._acento_actual()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # fecha encima de los dígitos, alineada al borde derecho de la tinta
        f_fecha = fuente(H * 0.075, QFont.DemiBold)
        p.setFont(f_fecha)
        fm = QFontMetricsF(f_fecha)
        borde = W * (1 - MARGEN_DER)
        base_fecha = H * TOP_DIGITOS - H * 0.03
        p.setPen(TEXTO_2)
        p.drawText(QPointF(borde - fm.horizontalAdvance(self._fecha), base_fecha), self._fecha)

        # dígitos: los que no cambian se pintan juntos; los que cambian, animados
        dig = self._trans_dig
        animados = {}
        e = 1.0
        if dig is not None:
            e = _ease((self._monotonic() - dig["t0"]) / DUR_DIGITO)
            animados = {ii: io for ii, io in dig["pares"]}
        estaticos = QPainterPath()
        for i in range(len(m.texto)):
            if i not in animados:
                estaticos.addPath(self._camino(m, i))
        _pintar_camino(p, estaticos, acento, 1.0)
        if dig is not None:
            hd = m.k * m.caja.height()          # altura real de los dígitos en píxeles
            viejo = dig["viejo"]
            for ii, io in animados.items():
                _pintar_camino(p, self._camino(viejo, io, -DESPLAZ * hd * e), acento, 1 - e)
                _pintar_camino(p, self._camino(m, ii, DESPLAZ * hd * (1 - e)), acento, e)
        p.end()
