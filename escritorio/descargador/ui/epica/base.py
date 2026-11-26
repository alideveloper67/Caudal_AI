# -*- coding: utf-8 -*-
"""Lo común de las letras épicas de la escena (edits): planos, dibujos guardados y curvas de movimiento.

Cómo funciona:
- La letra se monta como un video: cada verso se corta en **planos** (una palabra, tres, un verso entero,
  según el diseño) con su entrada y su salida.
- Lo caro de cada plano (brillos, bordes, metal…) se pinta UNA vez en imágenes; en cada cuadro solo se
  colocan, giran y mezclan. Nada de desenfoques en vivo: va a 60 cuadros por segundo sin tarjeta gráfica.
- Todo sale del instante de la canción, no de un reloj: adelantar, pausar o volver atrás cae exacto.

Coordenadas: el centro del lienzo es (0, 0).
"""

import math
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient, QTransform)

from .. import tipografia_letra
from ..estilo_letra import _Tinta

BLANCO = QColor(255, 255, 255)
NEGRO = QColor(0, 0, 0)


# ------------------------------------------------------------------ curvas

def lim(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def mezcla(a, b, u):
    return a + (b - a) * u


def out_expo(u):
    u = lim(u)
    return 1.0 if u >= 1.0 else 1.0 - 2.0 ** (-10.0 * u)


def out_cubic(u):
    u = lim(u)
    return 1.0 - (1.0 - u) ** 3


def out_quint(u):
    u = lim(u)
    return 1.0 - (1.0 - u) ** 5


def in_cubic(u):
    return lim(u) ** 3


def in_out(u):
    u = lim(u)
    return u * u * (3.0 - 2.0 * u)


def out_back(u, c=1.9):
    u = lim(u)
    return 1.0 + (c + 1.0) * (u - 1.0) ** 3 + c * (u - 1.0) ** 2


def muelle(t, frec=3.2, freno=7.5):
    """De 0 a 1 con rebote, en segundos."""
    if t <= 0:
        return 0.0
    return 1.0 - math.exp(-freno * t) * math.cos(2 * math.pi * frec * t)


def azar(*claves):
    """Un número 0..1 siempre igual para las mismas claves."""
    x = 0.0
    for i, k in enumerate(claves):
        x += float(k) * (12.9898 + 78.233 * i)
    s = math.sin(x) * 43758.5453
    return s - math.floor(s)


def entre(a, b, *claves):
    return a + (b - a) * azar(*claves)


# ------------------------------------------------------------------ colores

def alfa(c, a):
    c = QColor(c)
    c.setAlpha(int(lim(a, 0, 255)))
    return c


def claro(c, u):
    """El color mezclado con blanco (u de 0 a 1)."""
    return QColor(int(mezcla(c.red(), 255, u)), int(mezcla(c.green(), 255, u)), int(mezcla(c.blue(), 255, u)))


def oscuro(c, u):
    return QColor(int(c.red() * (1 - u)), int(c.green() * (1 - u)), int(c.blue() * (1 - u)))


def vivo(c, s=0.9, v=1.0):
    """El color, saturado y luminoso (los de una carátula gris salen apagados)."""
    h, s0, v0, _ = QColor(c).getHsvF()
    if h < 0:
        return QColor(255, 255, 255)
    return QColor.fromHsvF(max(0.0, h), max(s0, s) if s0 > 0.10 else s0, max(v0, v))


# ------------------------------------------------------------------ texto

def fuente(clave, px=100.0):
    """La fuente de un diseño; si la persona eligió un tipo de letra, manda el suyo."""
    elegida = tipografia_letra.actual()
    if elegida != tipografia_letra.POR_DEFECTO:
        clave = elegida
    f = QFont("Segoe UI Black")
    f.setPixelSize(int(px))
    f.setWeight(QFont.Black)
    f.setHintingPreference(QFont.PreferNoHinting)
    return tipografia_letra.adaptar(f, clave), clave


def mayusculas(texto, clave):
    return texto if clave in tipografia_letra.SIN_MAYUSCULAS else texto.upper()


def trazo(texto, f, sesgo=0.0):
    """El contorno del texto centrado en (0, 0), y su línea de alto real."""
    t = QPainterPath()
    t.setFillRule(Qt.WindingFill)
    t.addText(QPointF(0, 0), f, texto)
    if sesgo:
        t = QTransform().shear(-sesgo, 0).map(t)
        t.setFillRule(Qt.WindingFill)
    r = t.boundingRect()
    if r.isEmpty():
        return t
    t.translate(-r.center().x(), -r.center().y())
    return t


def escalar(t, s, sy=None):
    r = QTransform.fromScale(s, s if sy is None else sy).map(t)
    r.setFillRule(Qt.WindingFill)
    return r


def mover(t, dx, dy):
    r = QPainterPath(t)
    r.setFillRule(Qt.WindingFill)
    r.translate(dx, dy)
    return r


class Pieza:
    """Una palabra (o fila) colocada: su contorno centrado en sí misma y dónde va su centro."""
    __slots__ = ("i", "texto", "trazo", "x", "y", "w", "h", "fila")

    def __init__(self, i, texto, trazo_, x, y, fila=0):
        self.i, self.texto, self.trazo, self.x, self.y, self.fila = i, texto, trazo_, x, y, fila
        r = trazo_.boundingRect()
        self.w, self.h = r.width(), r.height()

    def rect(self, aire=0.0):
        return QRectF(self.x - self.w / 2 - aire, self.y - self.h / 2 - aire, self.w + 2 * aire, self.h + 2 * aire)


def _particiones(anchos, filas):
    """Las palabras repartidas en `filas` lo más iguales posible: lista de listas de índices."""
    n = len(anchos)
    if filas >= n:
        return [[i] for i in range(n)]
    mejor = {}

    def coste(a, f):
        if (a, f) in mejor:
            return mejor[(a, f)]
        if f == 1:
            r = (sum(anchos[a:]) + 0.0, [list(range(a, n))])
        else:
            r = None
            for b in range(a + 1, n - f + 2):
                este = sum(anchos[a:b])
                resto, grupos = coste(b, f - 1)
                v = max(este, resto)
                if r is None or v < r[0]:
                    r = (v, [list(range(a, b))] + grupos)
        mejor[(a, f)] = r
        return r
    return coste(0, filas)[1]


def bloque(textos, f, ancho, alto, filas_max=2, hueco=0.26, entre_filas=0.16, sesgo=0.0, tope=None):
    """Las palabras colocadas lo más grandes posible dentro de ancho × alto: lista de Pieza."""
    fm = QFontMetricsF(f)
    px = float(f.pixelSize() or 100)
    cap = max(1.0, -fm.tightBoundingRect("HX").top())
    crudos = [trazo(x, f, sesgo) for x in textos]
    cajas = [t.boundingRect() for t in crudos]
    anchos = [max(1.0, c.width()) for c in cajas]
    # alturas sobre y bajo la línea base: para que las filas se alineen por su línea y no por su caja
    sube, baja = [], []
    for x in textos:
        r = fm.tightBoundingRect(x)
        sube.append(max(1.0, -r.top()))
        baja.append(max(0.0, r.bottom()))
    mejor = None
    for n in range(1, min(filas_max, len(textos)) + 1):
        grupos = _particiones(anchos, n)
        w = max(sum(anchos[i] for i in g) + hueco * px * (len(g) - 1) for g in grupos)
        altos = [(max(max(sube[i] for i in g), cap * 0.9), max(baja[i] for i in g)) for g in grupos]
        h = sum(a + b for a, b in altos) + entre_filas * px * (n - 1)
        s = min(ancho / w, alto / h)
        if mejor is None or s > mejor[0] * 1.04:
            mejor = (s, grupos, w, h, altos)
    s, grupos, w, h, altos = mejor
    if tope is not None:
        s = min(s, tope / cap)
    piezas = []
    y = -h * s / 2
    for k, g in enumerate(grupos):
        sub, baj = altos[k]
        ancho_fila = (sum(anchos[i] for i in g) + hueco * px * (len(g) - 1)) * s
        x = -ancho_fila / 2
        linea = y + sub * s
        for i in g:
            t = escalar(crudos[i], s)
            cw = anchos[i] * s
            cy = linea + (baja[i] - sube[i]) * s / 2
            piezas.append(Pieza(i, textos[i], t, x + cw / 2, cy, k))
            x += cw + hueco * px * s
        y += (sub + baj + entre_filas * px) * s
    piezas.sort(key=lambda z: z.i)
    return piezas


def unir(piezas):
    """Todas las piezas en un solo contorno (en su sitio)."""
    t = QPainterPath()
    t.setFillRule(Qt.WindingFill)
    for z in piezas:
        t.addPath(mover(z.trazo, z.x, z.y))
    t.setFillRule(Qt.WindingFill)
    return t


# ------------------------------------------------------------------ dibujos guardados

class Sello:
    """Una imagen ya pintada, anclada por el (0, 0) de su contorno."""
    __slots__ = ("pm", "x0", "y0", "w", "h")

    def __init__(self, pm, x0, y0, w, h):
        self.pm, self.x0, self.y0, self.w, self.h = pm, x0, y0, w, h

    def pintar(self, p, x=0.0, y=0.0, s=1.0, op=1.0, giro=0.0, sy=None, sesgo=0.0):
        """Lo coloca con su (0, 0) en (x, y), escalado, girado y con opacidad."""
        if op <= 0.004:
            return
        antes = p.opacity()
        p.setOpacity(antes * min(1.0, op))
        sy = s if sy is None else sy
        if abs(s - 1.0) < 0.0015 and abs(sy - 1.0) < 0.0015 and not giro and not sesgo:
            p.drawPixmap(QPointF(round(x + self.x0), round(y + self.y0)), self.pm)
        else:
            p.save()
            p.translate(x, y)
            if giro:
                p.rotate(giro)
            if sesgo:
                p.shear(sesgo, 0)
            p.scale(s, sy)
            p.drawPixmap(QPointF(self.x0, self.y0), self.pm)
            p.restore()
        p.setOpacity(antes)

    def franja(self, p, x, y, arriba, alto, dx=0.0):
        """Solo una franja horizontal de la imagen (de `arriba`, en px desde su borde), corrida `dx`."""
        dpr = self.pm.devicePixelRatio()
        p.drawPixmap(QRectF(x + self.x0 + dx, y + self.y0 + arriba, self.w, alto), self.pm,
                     QRectF(0, arriba * dpr, self.w * dpr, alto * dpr))


def sello(t, pintor, margen, dpr=1.0):
    """Pinta una vez `pintor(q, tinta, t)` y lo guarda. `tinta` da sombras y halos baratos del contorno."""
    caja = t.boundingRect().adjusted(-margen, -margen, margen, margen)
    x0, y0 = math.floor(caja.left()), math.floor(caja.top())
    w, h = max(1, math.ceil(caja.right()) - x0), max(1, math.ceil(caja.bottom()) - y0)
    pm = QPixmap(max(1, int(math.ceil(w * dpr))), max(1, int(math.ceil(h * dpr))))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    q = QPainter(pm)
    q.setRenderHint(QPainter.Antialiasing)
    q.setRenderHint(QPainter.SmoothPixmapTransform)
    q.translate(-x0, -y0)
    pintor(q, _Tinta(t, x0, y0, w, h, dpr), t)
    q.end()
    return Sello(pm, x0, y0, w, h)


def relleno(q, t, brocha):
    q.setPen(Qt.NoPen)
    q.setBrush(brocha)
    q.drawPath(t)


def borde(q, t, color, ancho):
    q.setBrush(Qt.NoBrush)
    q.setPen(QPen(color, ancho, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    q.drawPath(t)


def vaciar(q, t, velo=0):
    """Quita lo de dentro del contorno (letras huecas de verdad) y deja, si se pide, un velo oscuro."""
    q.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    relleno(q, t, NEGRO)
    q.setCompositionMode(QPainter.CompositionMode_SourceOver)
    if velo:
        relleno(q, t, QColor(0, 0, 0, velo))


def vertical(t, *paradas):
    """Un degradado de arriba abajo del contorno: (posición, color)…"""
    r = t.boundingRect()
    g = QLinearGradient(0, r.top(), 0, r.bottom())
    for u, c in paradas:
        g.setColorAt(u, QColor(c))
    return QBrush(g)


def diagonal(t, *paradas):
    r = t.boundingRect()
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    for u, c in paradas:
        g.setColorAt(u, QColor(c))
    return QBrush(g)


def sombra(q, tinta, k, fuerza=1.0, dy=3.0):
    """Sombra negra difusa: se lee sobre cualquier fondo."""
    tinta.difusa(q, NEGRO, max(1.6, 11.0 * k), 0.9 * fuerza, 0, dy * k)
    tinta.difusa(q, NEGRO, max(1.2, 4.0 * k), 0.95 * fuerza, 0, dy * 0.6 * k)


def extrusion(q, tinta, color_cerca, color_lejos, largo, ang):
    """Cuerpo en 3D: copias de la silueta del fondo hacia la cara."""
    pasos = max(2, int(largo))
    dx, dy = math.cos(ang), math.sin(ang)
    for i in range(pasos, 0, -1):
        u = i / pasos
        c = QColor(int(mezcla(color_cerca.red(), color_lejos.red(), u)),
                   int(mezcla(color_cerca.green(), color_lejos.green(), u)),
                   int(mezcla(color_cerca.blue(), color_lejos.blue(), u)))
        tinta.copia(q, c, ((dx * i, dy * i),))


_MANCHAS = {}


def mancha(color, radio=24):
    """Un punto de luz redondo (se guarda): partículas, chispas, halos."""
    clave = (QColor(color).rgba(), radio)
    pm = _MANCHAS.get(clave)
    if pm is None:
        if len(_MANCHAS) > 64:
            _MANCHAS.clear()
        pm = QPixmap(2 * radio, 2 * radio)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        g = QRadialGradient(QPointF(radio, radio), radio)
        c = QColor(color)
        g.setColorAt(0.0, alfa(claro(c, 0.65), 255))
        g.setColorAt(0.22, alfa(c, 215))
        g.setColorAt(0.55, alfa(c, 70))
        g.setColorAt(1.0, alfa(c, 0))
        q.fillRect(0, 0, 2 * radio, 2 * radio, QBrush(g))
        q.end()
        _MANCHAS[clave] = pm
    return pm


def carpeta_imagenes():
    """Carpeta con las texturas (también dentro del .exe de PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "descargador" / "epica_img"
    return Path(__file__).resolve().parent.parent.parent / "epica_img"


FUEGO_W, FUEGO_H, FUEGO_COL, FUEGO_N = 288, 144, 6, 24     # la hoja del fuego: 24 cuadros que se repiten sin salto
_hojas = {}


def hoja(nombre):
    """Una textura de `epica_img` (se carga la primera vez). Nula si falta: el diseño sale sin ella."""
    if nombre not in _hojas:
        _hojas[nombre] = QPixmap(str(carpeta_imagenes() / nombre))
    return _hojas[nombre]


def cuadro_fuego(t, vel=20.0):
    """El rectángulo, dentro de la hoja, del fuego en el segundo `t`."""
    n = int(t * vel) % FUEGO_N
    return QRectF((n % FUEGO_COL) * FUEGO_W, (n // FUEGO_COL) * FUEGO_H, FUEGO_W, FUEGO_H)


def punto(p, pm, x, y, radio, op=1.0):
    if op <= 0.004 or radio <= 0.2:
        return
    p.setOpacity(min(1.0, op))
    p.drawPixmap(QRectF(x - radio, y - radio, 2 * radio, 2 * radio), pm, QRectF(pm.rect()))


def rayos(p, w, h, semilla, color, u, n=26, dentro=0.30, ancho=2.4):
    """Líneas de velocidad desde los bordes hacia el centro (u: 1 recién salidas, 0 apagadas)."""
    if u <= 0.01:
        return
    r = math.hypot(w, h) * 0.56
    p.save()
    p.setPen(Qt.NoPen)
    camino = QPainterPath()
    for i in range(n):
        ang = (i + azar(semilla, i) * 0.85) / n * 2 * math.pi
        d0 = r * (dentro + 0.30 * azar(semilla, i, 2) + 0.25 * (1 - u))
        d1 = r * (0.80 + 0.35 * azar(semilla, i, 3))
        if d1 <= d0:
            continue
        c, s = math.cos(ang), math.sin(ang)
        g = ancho * (0.4 + 1.4 * azar(semilla, i, 4))
        camino.moveTo(c * d0, s * d0 * 0.8)
        camino.lineTo(c * d1 - s * g, (s * d1 + c * g) * 0.8)
        camino.lineTo(c * d1 + s * g, (s * d1 - c * g) * 0.8)
        camino.closeSubpath()
    p.fillPath(camino, alfa(color, 190 * u))
    p.restore()


def anillo(p, u, radio, color, ancho=7.0, achatado=0.62):
    """Onda expansiva."""
    if u >= 1.0 or u <= 0.0:
        return
    e = out_cubic(u)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(alfa(color, 200 * (1 - u) ** 1.4), max(0.6, ancho * (1 - u))))
    p.drawEllipse(QPointF(0, 0), radio * e, radio * e * achatado)


INTENSIDAD = [1.0]         # cuánto se mueve todo (ajuste «letra_intensidad», lo pone epica.fijar_intensidad)


def temblor(t, fuerza, freno=9.0, semilla=0.0):
    """Sacudida de cámara que se va apagando: (dx, dy, grados)."""
    a = fuerza * INTENSIDAD[0] * math.exp(-t * freno)
    if a < 0.15:
        return 0.0, 0.0, 0.0
    return (a * math.sin(t * 97 + semilla * 7), a * math.cos(t * 83 + semilla * 5),
            a * 0.10 * math.sin(t * 71 + semilla * 3))


# ------------------------------------------------------------------ planos

class Plano:
    """Lo que se ve de una vez: unas palabras con sus tiempos (en segundos de la canción)."""
    __slots__ = ("textos", "tiempos", "t0", "t1", "linea", "n", "estilo", "semilla", "ultimo")

    def __init__(self, textos, tiempos, t0, t1, linea, n, estilo, ultimo=False):
        self.textos, self.tiempos, self.t0, self.t1 = list(textos), list(tiempos), t0, t1
        self.linea, self.n, self.estilo, self.ultimo = linea, n, estilo, ultimo
        self.semilla = (n * 37 + linea * 11) % 997

    @property
    def dur(self):
        return max(0.12, self.t1 - self.t0)

    def cantadas(self, t):
        """Cuántas palabras han entrado ya (t: segundos desde que empezó el plano)."""
        return sum(1 for x in self.tiempos if x - self.t0 <= t + 1e-6)


class Lienzo:
    """Lo que necesita saber un diseño al pintar."""
    __slots__ = ("w", "h", "dpr", "a", "b", "c", "energia", "golpe", "k")

    def __init__(self, w, h, dpr, colores, energia=0.0, golpe=0.0):
        self.w, self.h, self.dpr = float(w), float(h), float(dpr or 1.0)
        self.a, self.b, self.c = vivo(colores.a), vivo(colores.b), vivo(colores.c)
        self.energia, self.golpe = min(1.3, energia * INTENSIDAD[0]), min(1.3, golpe * INTENSIDAD[0])
        self.k = max(0.35, min(w / 660.0, h / 330.0))      # 1 = el tamaño con que se diseñó

    def clave(self):
        return (int(self.w), int(self.h), self.dpr, self.a.rgb(), self.b.rgb(), self.c.rgb())


class Diseno:
    """Un diseño de letra épica. `preparar` pinta lo caro una vez; `pintar` lo mueve."""

    CLAVE = ""
    NOMBRE = ""
    DETALLE = ""
    FUENTE = "anton"
    PALABRAS = 3            # cuántas palabras, como mucho, en un plano
    LETRAS = 18             # y cuántas letras
    SALIDA = 0.22           # s que tarda en irse (encima ya entra el siguiente)

    def preparar(self, pl, cx):
        raise NotImplementedError

    def pintar(self, p, pl, o, t, cx):
        """`t`: segundos desde que empezó el plano; pasado `pl.dur`, se está yendo."""
        raise NotImplementedError

    def _salida(self, pl, t):
        """0 mientras se ve; de 0 a 1 mientras se va."""
        return lim((t - pl.dur) / self.SALIDA) if t > pl.dur else 0.0

    def _textos(self, pl):
        f, clave = fuente(self.FUENTE)
        return [mayusculas(x, clave) for x in pl.textos], f


def trocear(palabras, max_palabras, max_letras):
    """Índices de las palabras de cada plano: grupos seguidos que no pasan de tantas palabras ni letras.
    Las muy cortas («de», «y», «la») no se quedan solas."""
    grupos, g, letras = [], [], 0
    for i, w in enumerate(palabras):
        n = len(w)
        if g and (len(g) >= max_palabras or letras + n > max_letras):
            grupos.append(g)
            g, letras = [], 0
        g.append(i)
        letras += n
    if g:
        grupos.append(g)
    # una palabra corta suelta al final de un grupo de una, se va con la siguiente
    i = 0
    while i + 1 < len(grupos):
        a, b = grupos[i], grupos[i + 1]
        if len(a) == 1 and len(palabras[a[0]]) <= 3 and sum(len(palabras[k]) for k in b) + 3 <= max_letras + 4:
            grupos[i:i + 2] = [a + b]
        else:
            i += 1
    if len(grupos) > 1 and len(grupos[-1]) == 1 and len(palabras[grupos[-1][0]]) <= 2:
        ult = grupos.pop()
        grupos[-1] += ult
    return grupos
