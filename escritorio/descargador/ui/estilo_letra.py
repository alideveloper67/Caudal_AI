# -*- coding: utf-8 -*-
"""Con qué diseño se pinta la letra de las canciones (ajuste «estilo_letra», mismas claves que en Android):
la escena de escritorio, la letra en la canción (página y panel) y el karaoke.

Los estilos elaborados se pintan UNA vez en una imagen (trazos anchos, degradados, relieve) y después solo se
copia esa imagen en cada cuadro: nada de desenfoques en vivo. Cada estilo tiene tres «capas»:

- `base`:   el texto de la línea que suena que todavía no se canta;
- `viva`:   el texto ya cantado (o la palabra que suena);
- `reposo`: las demás líneas.

Todos llevan su propia sombra o borde oscuro para leerse sobre un fondo claro, oscuro o un videoclip."""

import math
import weakref
from collections import OrderedDict

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF)

from . import tipografia_letra

POR_DEFECTO = "clasica"

# clave -> (nombre que ve la persona, en qué consiste)
NOMBRES = {
    "clasica": ("Clásica", "La de siempre"),
    "nitida": ("Nítida", "Con borde y sombra: se lee sobre cualquier fondo"),
    "neon": ("Neón", "Brilla como un letrero con los colores de la carátula"),
    "simple": ("Simple", "Limpia y ligera"),
    "degradado": ("Degradado", "Rellena con los colores de la carátula"),
    "contorno": ("Contorno", "Letras huecas que se rellenan al cantarse"),
    "relieve": ("Relieve", "Letras en 3D, con cuerpo y cara clara"),
    "marcador": ("Marcador", "Como pasar un resaltador por lo que suena"),
    "oro": ("Oro", "Dorado metálico con brillo"),
    "vhs": ("VHS", "Como una cinta de video: cian, magenta y líneas"),
}
ESTILOS = tuple(NOMBRES)
# los que se pintan con imágenes guardadas también en la escena de escritorio
ESTILOS_CAPAS = ("degradado", "contorno", "relieve", "marcador", "oro", "vhs")

TINTA_MARCADOR = QColor("#17101F")        # el texto sobre el resaltador
MAX_CACHE = 48 * 1024 * 1024              # bytes de imágenes guardadas por lienzo

_actual = POR_DEFECTO
_vivos = weakref.WeakSet()                # widgets que se repintan al cambiar el estilo


# cuánto se ven (0..1) las líneas que no suenan: el contorno, al ser hueco, necesita más
OPACIDAD_REPOSO = {"contorno": 0.60, "vhs": 0.38}


# ------------------------------------------------------------------ cuál está puesto

def normalizar(estilo):
    """El estilo pedido si es válido; si no, el clásico."""
    return estilo if estilo in NOMBRES else POR_DEFECTO


def nombre(estilo):
    return NOMBRES[normalizar(estilo)][0]


def actual():
    return _actual


def fijar(estilo):
    """Cambia el estilo de toda la letra; las vistas registradas se repintan al momento."""
    global _actual
    _actual = normalizar(estilo)
    for w in list(_vivos):
        try:
            w.al_cambiar_estilo_letra()
        except RuntimeError:              # el widget ya se destruyó
            pass


def suscribir(widget):
    """El widget recibe `al_cambiar_estilo_letra()` cuando cambia el ajuste."""
    _vivos.add(widget)


# ------------------------------------------------------------------ colores

def luminancia(c):
    """Luminancia relativa (0 negro, 1 blanco) de un color."""
    def canal(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * canal(c.redF()) + 0.7152 * canal(c.greenF()) + 0.0722 * canal(c.blueF())


def aclarar(c, minimo=0.34):
    """El color, aclarado lo justo para que se lea (sin perder el tono)."""
    c = QColor(c).toHsv()
    h, s, v = max(0.0, c.hsvHueF()), c.hsvSaturationF(), c.valueF()
    if c.hsvHueF() < 0:
        s = 0.0
    for _ in range(40):
        col = QColor.fromHsvF(h, s, v)
        if luminancia(col) >= minimo:
            break
        if v < 1.0:
            v = min(1.0, v + 0.06)
        elif s > 0.0:
            s = max(0.0, s - 0.04)
        else:
            break
    return QColor.fromHsvF(h, s, v)


def _girar(c, grados):
    h, s, v, _a = c.getHsvF()
    return QColor.fromHsvF((max(0.0, h) + grados / 360.0) % 1.0, max(0.45, s), v)


def _cerca(a, b):
    if a.hsvSaturationF() < 0.12 or b.hsvSaturationF() < 0.12:
        return a.hsvSaturationF() < 0.12 and b.hsvSaturationF() < 0.12
    d = abs(a.hsvHueF() - b.hsvHueF())
    return min(d, 1.0 - d) < 0.07


class Colores:
    """Los colores de la carátula listos para la letra: legibles y distintos entre sí."""
    __slots__ = ("a", "b", "c", "clave")

    def __init__(self, c1, c2, c3):
        c1, c2, c3 = QColor(c1), QColor(c2), QColor(c3)
        if _cerca(c1, c2):
            c2 = _girar(c2, 42)
        if _cerca(c3, c1) or _cerca(c3, c2):
            c3 = _girar(c1, -42)
        self.a, self.b, self.c = aclarar(c1), aclarar(c2), aclarar(c3)
        self.clave = (self.a.rgb(), self.b.rgb(), self.c.rgb())


# ------------------------------------------------------------------ trazos

def trazo_de(texto, f, x=0.0, y=0.0):
    """El contorno del texto con la línea base en (x, y). Relleno «winding»: en las letras enlazadas
    (Pacifico, Great Vibes…) no quedan huecos donde se pisan. Los bordes se pintan siempre DEBAJO del relleno
    (o se vacía lo de dentro), así que tampoco se ven por dentro y no hace falta unir las letras."""
    t = QPainterPath()
    t.setFillRule(Qt.WindingFill)
    t.addText(QPointF(x, y), f, texto)
    return t


class _Tinta:
    """El texto que se está pintando en una imagen: su trazo y su silueta. Las sombras, los halos y el cuerpo
    en 3D salen de copiar (y encoger y estirar) la silueta, que cuesta cien veces menos que repasar el
    contorno con plumas anchas."""

    def __init__(self, trazo, x0, y0, w, h, dpr):
        self.trazo = trazo
        self.x0, self.y0, self.w, self.h, self.dpr = x0, y0, w, h, dpr
        self._silueta = None
        self._suaves = {}

    def silueta(self):
        if self._silueta is None:
            img = QImage(max(1, int(math.ceil(self.w * self.dpr))), max(1, int(math.ceil(self.h * self.dpr))),
                         QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.scale(self.dpr, self.dpr)
            p.translate(-self.x0, -self.y0)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawPath(self.trazo)
            p.end()
            self._silueta = img
        return self._silueta

    def _tenida(self, img, color):
        copia = img.copy()
        p = QPainter(copia)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.fillRect(copia.rect(), color)
        p.end()
        return copia

    def copia(self, p, color, pasos):
        """Copia la silueta, de un color, en cada (dx, dy) de `pasos` (píxeles enteros)."""
        img = self._tenida(self.silueta(), color)
        img.setDevicePixelRatio(self.dpr)
        for dx, dy in pasos:
            p.drawImage(QPointF(self.x0 + dx, self.y0 + dy), img)

    def _suave(self, radio):
        """La silueta difuminada (se encoge y se vuelve a estirar), en pequeño."""
        f = max(1.0, radio * self.dpr / 1.15)
        clave = round(f, 2)
        if clave not in self._suaves:
            s = self.silueta()
            w, h = max(2, int(math.ceil(s.width() / f))), max(2, int(math.ceil(s.height() / f)))
            chica = s.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            medio = chica.scaled(min(s.width(), w * 2), min(s.height(), h * 2), Qt.IgnoreAspectRatio,
                                 Qt.SmoothTransformation)
            self._suaves[clave] = medio
        return self._suaves[clave]

    def difusa(self, p, color, radio, fuerza, dx=0.0, dy=0.0):
        """Una mancha suave del texto. `fuerza` puede pasar de 1: se repite para que se note alrededor."""
        img = self._tenida(self._suave(radio), color)
        antes = p.opacity()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        destino = QRectF(self.x0 + dx, self.y0 + dy, self.w, self.h)
        while fuerza > 0.01:
            p.setOpacity(antes * min(1.0, fuerza))
            p.drawImage(destino, img, QRectF(0, 0, img.width(), img.height()))
            fuerza -= 1.0
        p.setOpacity(antes)


def alturas(f):
    """(subida de las mayúsculas, bajada de la «g») reales de la fuente: no dependen de lo que declare."""
    fm = QFontMetricsF(f)
    r = fm.tightBoundingRect("HÑgy")
    h = fm.tightBoundingRect("Hh")
    return max(1.0, -h.top()), max(0.0, r.bottom())


def grosor_borde(f):
    """1 en las fuentes normales; menos en las de trazo tan fino que un borde las empasta."""
    return 0.4 if f.family() in _familias_finas() else 1.0


def _familias_finas():
    return {tipografia_letra.familia(k) for k in tipografia_letra.FINAS if k in tipografia_letra._familias}


def _pluma(color, ancho):
    return QPen(color, ancho, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _bordes(p, t, pasadas, color):
    trazo = t.trazo
    p.setBrush(Qt.NoBrush)
    for ancho, alfa in pasadas:
        c = QColor(color)
        c.setAlpha(alfa)
        p.setPen(_pluma(c, ancho))
        p.drawPath(trazo)


def _sombra(p, t, k, dy=2.2, fuerza=1.0, dx=0.0):
    """Sombra difusa, un poco hacia abajo: una ceñida y otra más ancha."""
    negro = QColor(0, 0, 0)
    t.difusa(p, negro, max(1.6, 7.0 * k), 1.05 * fuerza, dx, dy * k)
    t.difusa(p, negro, max(1.2, 3.0 * k), 1.0 * fuerza, dx, dy * 0.7 * k)


def _relleno(p, t, brocha):
    p.setPen(Qt.NoPen)
    p.setBrush(brocha)
    p.drawPath(t.trazo)


def _estrella(p, x, y, r, alfa=240):
    """Un destello de cuatro puntas (el brillo del oro)."""
    puntas = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.16
        puntas.append(QPointF(x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 252, 230, alfa))
    p.drawPolygon(QPolygonF(puntas))


# ------------------------------------------------------------------ estilos

def _nitida(p, t, k, capa, col, m):
    if capa == "base":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 255, 255, 120))
        return
    _sombra(p, t, k)
    _bordes(p, t, ((2.4 * k * m.borde, 180),), QColor(10, 8, 16))
    g = QLinearGradient(0, m.arriba, 0, m.linea)
    g.setColorAt(0, QColor(255, 255, 255))
    g.setColorAt(1, QColor(236, 230, 246))
    _relleno(p, t, QBrush(g))


def _neon(p, t, k, capa, col, m):
    if capa == "viva":
        for radio, fuerza in ((15.0, 1.3), (8.0, 1.7), (4.0, 1.8), (2.0, 1.2)):
            t.difusa(p, col.a, max(1.2, radio * k), fuerza)
        _relleno(p, t, QColor(255, 255, 255))
        return
    t.difusa(p, QColor(0, 0, 0), max(1.2, 4 * k), 0.45)
    _relleno(p, t, QColor(255, 255, 255, 115 if capa == "base" else 255))


def _simple(p, t, k, capa, col, m):
    _relleno(p, t, QColor(255, 255, 255, 115 if capa == "base" else 255))


def _degradado(p, t, k, capa, col, m):
    if capa == "base":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 255, 255, 125))
        return
    if capa == "reposo":                          # las demás líneas, en blanco: el color es de lo que suena
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 255, 255))
        return
    _sombra(p, t, k, fuerza=1.15)
    _bordes(p, t, ((3.0 * k * m.borde, 190),), QColor(12, 8, 20))
    g = QLinearGradient(QPointF(m.marco.left(), m.arriba), QPointF(m.marco.right(), m.linea))
    for u, c in ((0.0, col.a), (0.5, col.b), (1.0, col.c)):
        g.setColorAt(u, c if m.borde >= 1.0 else aclarar(c, 0.58))
    _relleno(p, t, QBrush(g))
    luz = QLinearGradient(0, m.arriba, 0, m.linea)          # un brillo arriba, como esmalte
    luz.setColorAt(0.0, QColor(255, 255, 255, 95))
    luz.setColorAt(0.5, QColor(255, 255, 255, 18))
    luz.setColorAt(0.52, QColor(255, 255, 255, 0))
    _relleno(p, t, QBrush(luz))


def _contorno(p, t, k, capa, col, m):
    _sombra(p, t, k, dy=1.2, fuerza=0.9)
    if m.borde < 1.0:                             # trazo fino: sin sitio para un hueco, se ve tenue y se enciende
        _bordes(p, t, ((4.0 * k * m.borde, 170),), QColor(8, 6, 14))
        _relleno(p, t, col.a.lighter(118) if capa == "viva" else QColor(255, 255, 255, 150))
        return
    # dos filos por fuera de la letra: el claro junto a ella y el oscuro que la recorta del fondo
    filo = max(0.9, 1.6 * k)
    _bordes(p, t, ((2 * filo + 3.4 * k, 215),), QColor(8, 6, 14))
    _bordes(p, t, ((2 * filo, 255),), QColor(255, 255, 255))
    if capa != "viva":
        # hueca de verdad: se vacía lo de dentro para que se vea el fondo
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        _relleno(p, t, QColor(0, 0, 0))
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        _relleno(p, t, QColor(255, 255, 255, 30))       # un velo de vidrio
        return
    g = QLinearGradient(0, m.arriba, 0, m.linea)
    g.setColorAt(0.0, col.a.lighter(118))
    g.setColorAt(1.0, col.a)
    _relleno(p, t, QBrush(g))


def _relieve(p, t, k, capa, col, m):
    vivo = capa != "base"
    h, s, _v, _a = col.a.getHsvF()
    h = max(0.0, h)
    fondo = max(2.2, 5.6 * k * (0.45 + 0.55 * m.borde))       # cuánto sale el cuerpo
    pasos = max(3, int(round(fondo)))
    _sombra(p, t, k, dy=2.0 + fondo / k, fuerza=1.0, dx=fondo * 0.75)
    _bordes(p, t, ((2.2 * k * m.borde, 110),), QColor(8, 6, 12))
    for i in range(pasos, 0, -1):                 # del fondo hacia la cara
        u = i / pasos
        if vivo:
            cuerpo = QColor.fromHsvF(h, min(0.95, s * 0.85 + 0.18), 0.64 - 0.34 * u)
        else:
            cuerpo = QColor.fromHsvF(h, min(0.35, s), 0.34 - 0.18 * u)
        t.copia(p, cuerpo, ((fondo * 0.75 * u, fondo * u),))
    g = QLinearGradient(0, m.arriba, 0, m.linea)
    if vivo:
        g.setColorAt(0.0, QColor(255, 255, 255))
        g.setColorAt(0.55, QColor(252, 250, 255))
        g.setColorAt(1.0, QColor.fromHsvF(h, min(0.30, s * 0.4), 1.0))
    else:
        g.setColorAt(0.0, QColor(176, 174, 188))
        g.setColorAt(1.0, QColor(146, 143, 160))
    _relleno(p, t, QBrush(g))


def _marcador(p, t, k, capa, col, m):
    if capa == "viva":                            # va sobre la pastilla, que se pinta aparte
        _relleno(p, t, TINTA_MARCADOR)
        return
    _sombra(p, t, k)
    _bordes(p, t, ((2.2 * k * m.borde, 150),), QColor(10, 8, 16))
    _relleno(p, t, QColor(255, 255, 255))


def _oro(p, t, k, capa, col, m):
    if capa == "base":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 231, 176, 130))
        return
    if capa == "reposo":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 232, 178))
        return
    _sombra(p, t, k, fuerza=1.2)
    _bordes(p, t, ((4.2 * k * m.borde, 225),), QColor(52, 28, 4))
    if m.borde >= 1.0:
        _bordes(p, t, ((1.6 * k, 255),), QColor(255, 226, 140))
    g = QLinearGradient(0, m.arriba, 0, m.linea)
    tonos = ((0.0, "#FFF8D2"), (0.25, "#FADB72"), (0.47, "#C98B22"), (0.52, "#FFF3B4"), (0.74, "#EDB647"),
             (1.0, "#A66A16"))
    if m.borde < 1.0:                             # en un trazo fino los tonos oscuros se pierden
        tonos = ((0.0, "#FFF6CC"), (0.48, "#FFD75E"), (0.52, "#FFF3B4"), (1.0, "#F5BE45"))
    for u, c in tonos:
        g.setColorAt(u, QColor(c))
    _relleno(p, t, QBrush(g))
    # el brillo: una banda clara en diagonal que se repite, como luz sobre metal
    alto = max(1.0, m.linea - m.arriba)
    luz = QLinearGradient(QPointF(0, 0), QPointF(alto * 2.2, alto * 1.1))
    luz.setSpread(QLinearGradient.RepeatSpread)
    for u, a in ((0.0, 0), (0.40, 0), (0.48, 150), (0.52, 190), (0.56, 130), (0.62, 0), (1.0, 0)):
        luz.setColorAt(u, QColor(255, 255, 244, a))
    _relleno(p, t, QBrush(luz))
    caja = t.trazo.boundingRect()
    if caja.width() > alto * 2.6:                 # en las palabras cortas los destellos estorban
        _estrella(p, caja.left() + min(caja.width() * 0.14, alto), m.arriba + alto * 0.12, alto * 0.24)
        _estrella(p, caja.right() - min(caja.width() * 0.10, alto * 0.8), m.arriba + alto * 0.62,
                  alto * 0.17, 225)


def _vhs(p, t, k, capa, col, m):
    if capa == "base":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(255, 255, 255, 120))
        return
    if capa == "reposo":
        _sombra(p, t, k, fuerza=0.55)
        _relleno(p, t, QColor(252, 252, 255))
        return
    d = max(1.6, 2.6 * k * (0.5 + 0.5 * m.borde))
    _sombra(p, t, k, dy=1.0)
    _bordes(p, t, ((2 * d + 1.6 * k * m.borde, 120),), QColor(6, 4, 14))
    t.copia(p, QColor("#FF1FA8"), ((d, 0.25 * d),))
    t.copia(p, QColor("#12E6FF"), ((-d, -0.15 * d),))
    _relleno(p, t, QColor(252, 252, 255))


_PINTORES = {"nitida": _nitida, "neon": _neon, "simple": _simple, "degradado": _degradado,
             "contorno": _contorno, "relieve": _relieve, "marcador": _marcador, "oro": _oro, "vhs": _vhs}


def _rayas_vhs(p, rect, k):
    """Las líneas de la cinta: se quita un poco de tinta cada pocos píxeles."""
    paso = max(3.0, 3.2 * k)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    y = math.floor(rect.top())
    while y < rect.bottom():
        p.fillRect(QRectF(rect.left(), y, rect.width(), max(1.0, paso * 0.30)), QColor(0, 0, 0, 62))
        y += paso
    p.setCompositionMode(QPainter.CompositionMode_SourceOver)
    p.setRenderHint(QPainter.Antialiasing, True)


class Medida:
    """Dónde está la línea de texto que se pinta: la caja para los degradados, lo alto de las mayúsculas y la
    línea base (en las mismas coordenadas que el trazo)."""
    __slots__ = ("marco", "arriba", "linea", "abajo", "borde")

    def __init__(self, marco, linea, subida, bajada=0.0, borde=1.0):
        self.borde = borde                # cuánto se engorda el borde (menos en las fuentes de trazo fino)
        self.marco = QRectF(marco)
        self.linea = linea
        self.arriba = linea - subida
        self.abajo = linea + bajada


def imagen_capa(trazo, tam, estilo, capa, colores, medida, dpr=1.0):
    """(imagen, punto donde va) de una capa: se pinta una vez y luego solo se copia."""
    margen = math.ceil(max(6.0, tam * 0.36))
    caja = trazo.boundingRect().adjusted(-margen, -margen, margen, margen)
    x0, y0 = math.floor(caja.left()), math.floor(caja.top())
    w = max(1, math.ceil(caja.right()) - x0)
    h = max(1, math.ceil(caja.bottom()) - y0)
    img = QImage(max(1, int(math.ceil(w * dpr))), max(1, int(math.ceil(h * dpr))),
                 QImage.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(dpr)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(-x0, -y0)
    k = max(0.34, tam / 60.0)
    _PINTORES[estilo](p, _Tinta(trazo, x0, y0, w, h, dpr), k, capa, colores, medida)
    if estilo == "vhs" and capa == "viva" and tam >= 26:       # en letra pequeña las rayas solo ensucian
        _rayas_vhs(p, QRectF(x0, y0, w, h), k)
    p.end()
    return img, QPointF(x0, y0)


def capa_real(estilo, capa):
    """Qué capa se pinta de verdad (varios estilos muestran igual lo cantado y las demás líneas)."""
    if capa == "reposo":
        if estilo in ("nitida", "relieve"):
            return "viva"
        if estilo in ("contorno", "marcador"):
            return "base"
    return capa


def rect_pastilla(caja, medida, tam):
    """La pastilla del marcador para un texto que ocupa `caja` (a lo ancho) en esa línea."""
    aire = tam * 0.16
    arriba = min(medida.arriba, caja.top()) - tam * 0.06
    abajo = max(medida.linea + (medida.abajo - medida.linea) * 0.75, caja.bottom()) + tam * 0.06
    return QRectF(caja.left() - aire, arriba, caja.width() + 2 * aire, abajo - arriba)


def pintar_pastilla(p, rect, colores, tam):
    """El resaltador: una pastilla del color de la carátula, siempre clara para que el texto oscuro se lea."""
    if rect.width() < 1:
        return
    radio = min(rect.height() * 0.26, rect.width() / 2, tam * 0.30)
    k = max(0.34, tam / 60.0)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    for d, a in ((4.0, 16), (2.2, 28), (1.0, 40)):
        p.setBrush(QColor(0, 0, 0, a))
        p.drawRoundedRect(rect.adjusted(-d * k, -d * 0.4 * k, d * k, d * 1.5 * k), radio + d * k, radio + d * k)
    color = aclarar(colores.a, 0.48)
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0.0, color.lighter(112))
    g.setColorAt(1.0, color)
    p.setBrush(QBrush(g))
    p.drawRoundedRect(rect, radio, radio)
    p.restore()


def dibujar_hasta(p, img, en, hasta, borde):
    """Copia la imagen hasta la x `hasta` (coordenadas del pintor), apagándose en `borde` píxeles a cada lado.
    Se recorta en una copia y se dibuja de una vez: con el pintor escalado no quedan costuras."""
    dpr = img.devicePixelRatio()
    x0 = (hasta - borde - en.x()) * dpr                  # en píxeles de la imagen
    x1 = (hasta + borde - en.x()) * dpr
    if x1 <= 0:
        return
    if x0 >= img.width():
        p.drawImage(en, img)
        return
    trozo = img.copy(0, 0, max(1, min(img.width(), int(math.ceil(x1)))), img.height())
    trozo.setDevicePixelRatio(1.0)
    q = QPainter(trozo)
    q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    g = QLinearGradient(x0, 0, max(x1, x0 + 1.0), 0)
    g.setColorAt(0.0, QColor(0, 0, 0, 255))
    g.setColorAt(1.0, QColor(0, 0, 0, 0))
    desde = max(0, int(math.floor(x0)))
    q.fillRect(QRectF(desde, 0, trozo.width() - desde, trozo.height()), QBrush(g))
    q.end()
    trozo.setDevicePixelRatio(dpr)
    p.drawImage(en, trozo)


class CacheCapas:
    """Imágenes ya pintadas; si ocupan demasiado se sueltan las que hace más tiempo que no se usan."""

    def __init__(self, tope=MAX_CACHE):
        self.tope = tope
        self._d = OrderedDict()
        self._bytes = 0

    def __len__(self):
        return len(self._d)

    def __contains__(self, clave):
        return clave in self._d

    def vaciar(self):
        self._d.clear()
        self._bytes = 0

    def pedir(self, clave, crear):
        hecho = self._d.get(clave)
        if hecho is not None:
            self._d.move_to_end(clave)
            return hecho
        hecho = crear()
        self._d[clave] = hecho
        self._bytes += hecho[0].sizeInBytes()
        while self._bytes > self.tope and len(self._d) > 1:
            _k, (img, *_r) = self._d.popitem(last=False)
            self._bytes -= img.sizeInBytes()
        return hecho


# ------------------------------------------------------------------ muestra (selector y vista previa)

def pintar_muestra(p, x, linea, texto, f, estilo, colores, progreso=0.6, dpr=1.0):
    """Una línea de texto con su estilo, cantada hasta `progreso` (0..1): para las vistas previas."""
    estilo = normalizar(estilo)
    tam = f.pixelSize() if f.pixelSize() > 0 else 24
    fm = QFontMetricsF(f)
    ancho = fm.horizontalAdvance(texto)
    hasta = x + ancho * max(0.0, min(1.0, progreso))
    if estilo == POR_DEFECTO:
        t = trazo_de(texto, f, x, linea)
        p.setBrush(Qt.NoBrush)
        for grosor, alfa in ((0.28, 10), (0.16, 18), (0.08, 26)):
            p.setPen(_pluma(QColor(255, 255, 255, alfa), tam * grosor))
            p.drawPath(t)
        g = QLinearGradient(hasta - tam * 0.5, 0, hasta + tam * 0.5, 0)
        g.setColorAt(0.0, QColor(255, 255, 255, 255))
        g.setColorAt(1.0, QColor(255, 255, 255, 255 if progreso >= 1 else 105))
        p.fillPath(t, QBrush(g))
        return
    t = trazo_de(texto, f, x, linea)
    subida, bajada = alturas(f)
    m = Medida(QRectF(x, linea - subida, ancho, subida + bajada), linea, subida, bajada, grosor_borde(f))
    if progreso < 1:
        img, en = imagen_capa(t, tam, estilo, "base", colores, m, dpr)
        p.drawImage(en, img)
    if estilo == "marcador" and progreso > 0:
        caja = t.boundingRect()
        caja.setRight(x + ancho * min(1.0, progreso))
        pintar_pastilla(p, rect_pastilla(caja, m, tam), colores, tam)
    img, en = imagen_capa(t, tam, estilo, "viva", colores, m, dpr)
    if progreso >= 1:
        p.drawImage(en, img)
    else:
        dibujar_hasta(p, img, en, hasta, tam * (0.10 if estilo == "marcador" else 0.32))
