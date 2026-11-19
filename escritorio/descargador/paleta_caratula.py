# -*- coding: utf-8 -*-
"""Colores que siguen la carátula (donadores).

La barra del reproductor y las vistas grandes (visualizador, karaoke) toman tres colores de la carátula
que suena y pasan de unos a otros con una transición suave, sin saltos.

- `calcular_paleta(img)`: de la imagen reducida a 24×24 saca tres colores (dominante, segundo y brillo) agrupando
  los tonos en 12 cubos pesados por viveza. Es barato (576 píxeles) y se cachea por carátula.
- `ColoresCaratula`: uno por aplicación (`colores_de(ctx)`); escucha la pista, pide la paleta y anima hacia ella
  con un reloj propio que solo corre mientras dura la transición. Si el modo gamer está en ahorro, salta directo.
"""

import math
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage

from .memoria import DiccionarioLimitado

CACHE = DiccionarioLimitado(240)        # url de la carátula -> (hex, hex, hex)
LADO = 24                                # la carátula se reduce a 24×24 antes de mirarla
BANDAS_TONO = 12
SEGUNDOS_TRANSICION = 0.7                # lo que tarda en asentarse (≈ 3 constantes de tiempo)
MS_PASO = 33                             # ~30 cuadros por segundo mientras dura la transición
GRIS = ("#5B6475", "#3C4352", "#9AA4B8")  # carátula sin color: un azul grisáceo discreto


def _hex(c):
    return QColor(c).name()


def _viva(c, s_min=0.5, s_max=0.92, v_min=0.58, v_max=0.96):
    """El color con saturación y brillo dentro de un rango agradable (vivo, no chillón)."""
    h, s, v, _a = QColor(c).getHsvF()
    return QColor.fromHsvF(h if h >= 0 else 0.6, min(s_max, max(s_min, s)), min(v_max, max(v_min, v)))


def calcular_paleta(img):
    """Tres colores (hex) de una carátula `QImage`. Sin imagen o gris: una paleta neutra."""
    if img is None or img.isNull():
        return GRIS
    peq = img.scaled(LADO, LADO, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if peq.format() != QImage.Format_RGB32:
        peq = peq.convertToFormat(QImage.Format_RGB32)
    peso = [0.0] * BANDAS_TONO
    suma = [[0.0, 0.0, 0.0] for _ in range(BANDAS_TONO)]
    total = 0.0
    for y in range(LADO):
        for x in range(LADO):
            c = QColor(peq.pixel(x, y))
            h, s, v, _a = c.getHsvF()
            if h < 0 or v < 0.14 or s < 0.12:
                continue                              # negros y grises no dan color
            w = s * (0.35 + v)
            i = int(h * BANDAS_TONO) % BANDAS_TONO
            peso[i] += w
            suma[i][0] += c.redF() * w
            suma[i][1] += c.greenF() * w
            suma[i][2] += c.blueF() * w
            total += w
    if total < 1.2:
        return GRIS
    orden = sorted(range(BANDAS_TONO), key=lambda i: -peso[i])
    elegidos = []
    for i in orden:
        if peso[i] < total * 0.06:
            break
        # tonos de verdad distintos entre sí (a 2 cubos o más, con la vuelta del círculo)
        if all(min((i - j) % BANDAS_TONO, (j - i) % BANDAS_TONO) >= 2 for j in elegidos):
            elegidos.append(i)
        if len(elegidos) == 3:
            break
    colores = []
    for i in elegidos:
        w = peso[i]
        colores.append(_viva(QColor.fromRgbF(suma[i][0] / w, suma[i][1] / w, suma[i][2] / w)))
    base = colores[0]
    while len(colores) < 3:
        h, s, v, _a = base.getHsvF()
        paso = 0.09 if len(colores) == 1 else -0.09
        colores.append(_viva(QColor.fromHsvF((h + paso) % 1.0, s, min(1.0, v * (1.0 if len(colores) == 1 else 1.12)))))
    return tuple(_hex(c) for c in colores)


def paleta_en_cache(url):
    return CACHE.get(url) if url else None


def paleta_de_url(url, callback):
    """Llama a `callback(paleta)` con la paleta de la carátula (pidiendo la imagen si hace falta)."""
    if not url:
        callback(GRIS)
        return
    hecha = CACHE.get(url)
    if hecha is not None:
        callback(hecha)
        return
    from .ui import imagenes

    def llego(img, u=url):
        pal = calcular_paleta(img)
        CACHE[u] = pal
        callback(pal)
    imagenes.imagen(url, llego)


def mezclar(a, b, t):
    """Mezcla lineal de dos QColor (t de 0 a 1)."""
    t = max(0.0, min(1.0, t))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def _ahorrando(ctx):
    g = getattr(ctx, "gamer", None)
    return bool(g is not None and getattr(g, "ahorrando", False))


class ColoresCaratula(QObject):
    """Los tres colores de la carátula que suena, siempre en transición suave."""

    cambio = Signal()            # los colores actuales cambiaron (un paso de la transición)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.fuerza = 0.0                         # 0 = sin paleta (colores de la app), 1 = la de la carátula
        self._fuerza_obj = 0.0
        self._actual = [QColor(h) for h in GRIS]
        self._objetivo = [QColor(h) for h in GRIS]
        self._clave = None
        self._reloj = QTimer(self)
        self._reloj.setInterval(MS_PASO)
        self._reloj.timeout.connect(self._paso)
        self._t_ultimo = time.monotonic()
        r = getattr(ctx, "reproductor", None)
        if r is not None:
            r.pista_cambio.connect(self._pista)
        g = getattr(ctx, "premium", None)
        if g is not None:
            g.cambiado.connect(self.refrescar)
        self._pista(getattr(r, "actual", None) if r is not None else None)

    # ------------------------------------------------------------ estado
    def habilitado(self):
        """Solo donadores (o prueba/fundador) y si no lo apagaron en Ajustes."""
        g = getattr(self.ctx, "premium", None)
        if g is None or not g.premium:
            return False
        return bool(self.ctx.ajustes["colores_caratula"])

    def refrescar(self):
        self._pista(getattr(getattr(self.ctx, "reproductor", None), "actual", None), forzar=True)

    def colores(self, base=None):
        """Tres QColor listos para pintar: la paleta mezclada con `base` (los colores de la app) según `fuerza`."""
        if base is None:
            from .ui.estilos import C
            a = QColor(C["acento"])
            base = [a, a.darker(150), a.lighter(120)]
        return [mezclar(QColor(b), c, self.fuerza) for b, c in zip(base, self._actual)]

    def hex_actuales(self):
        return [c.name() for c in self._actual]

    @property
    def animando(self):
        return self._reloj.isActive()

    # ------------------------------------------------------------ pista nueva
    def _pista(self, pista, forzar=False):
        pista = pista or {}
        url = pista.get("miniatura") or ""
        clave = (url, self.habilitado())
        if clave == self._clave and not forzar:
            return
        self._clave = clave
        if not clave[1] or not url:
            self._ir_a(None)
            return
        paleta_de_url(url, lambda pal, c=clave: self._clave == c and self._ir_a(pal))

    def _ir_a(self, paleta):
        if paleta is None:
            self._fuerza_obj = 0.0
        else:
            self._fuerza_obj = 1.0
            self._objetivo = [QColor(h) for h in paleta]
            if self.fuerza <= 0.001:
                self._actual = [QColor(c) for c in self._objetivo]   # venía sin paleta: se desvanece sin pasar por otros tonos
        if abs(self._fuerza_obj - self.fuerza) <= 0.01 and all(
                max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= 2
                for a, b in zip(self._actual, self._objetivo)):
            return                                  # ya está donde debe: nada que animar
        if _ahorrando(self.ctx):
            self._asentar()
            return
        self._t_ultimo = time.monotonic()
        if not self._reloj.isActive():
            self._reloj.start()

    def _asentar(self):
        self._actual = [QColor(c) for c in self._objetivo]
        self.fuerza = self._fuerza_obj
        self._reloj.stop()
        self.cambio.emit()

    def _paso(self):
        if _ahorrando(self.ctx):
            self._asentar()
            return
        ahora = time.monotonic()
        dt = min(0.2, ahora - self._t_ultimo)
        self._t_ultimo = ahora
        k = 1.0 - math.exp(-dt * 3.0 / SEGUNDOS_TRANSICION)
        quieto = True
        nuevos = []
        for c, o in zip(self._actual, self._objetivo):
            canales = []
            for x, y in ((c.red(), o.red()), (c.green(), o.green()), (c.blue(), o.blue())):
                if abs(y - x) <= 2:
                    canales.append(y)                     # ya casi llegó: se asienta sin parpadeos de redondeo
                else:
                    canales.append(int(round(x + (y - x) * k)))
                    quieto = False
            nuevos.append(QColor(*canales))
        self._actual = nuevos
        self.fuerza += (self._fuerza_obj - self.fuerza) * k
        if abs(self._fuerza_obj - self.fuerza) > 0.01:
            quieto = False
        if quieto:
            self._asentar()
            return
        self.cambio.emit()


def colores_de(ctx):
    """El gestor único de colores de la aplicación (se crea la primera vez que alguien lo pide)."""
    g = getattr(ctx, "colores_caratula", None)
    if g is None:
        g = ColoresCaratula(ctx, ctx)
        ctx.colores_caratula = g
    return g
