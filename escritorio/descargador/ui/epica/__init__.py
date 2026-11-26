# -*- coding: utf-8 -*-
"""Letras épicas de la escena: la letra montada como un edit (ver base.py).

- `DISENOS`: clave -> diseño. `NOMBRES`: clave -> (nombre, en qué consiste), para los selectores.
- `Montaje`: corta la letra en planos y los pinta en el instante que toque.
- `actual()` / `fijar()` / `suscribir()`: cuál está puesto (ajuste «letra_epica»; «» = la letra normal).
"""

import bisect
import re
import weakref
from collections import OrderedDict

from PySide6.QtGui import QPainter

from . import base, efectos, golpe
from .base import Lienzo, Plano, azar, trocear  # noqa: F401

DISENOS = OrderedDict((d.CLAVE, d()) for d in (
    golpe.Impacto, golpe.Viral, golpe.Poster, efectos.Katana, efectos.Glitch, efectos.Fuego, efectos.Electro,
    efectos.Cromo, golpe.Tunel, golpe.Eco, golpe.Phonk, efectos.Neon, efectos.Estelar, efectos.Garabato,
    golpe.EcoSuave, golpe.EcoEspejo, golpe.EcoColor, golpe.EcoFrase))
# las que se ofrecen: el Eco fluido y sus derivaciones (las demás quedaron muy forzadas; su código sigue por si
# alguna vuelve, pero no se eligen)
OFRECIDAS = ("eco", "eco_suave", "eco_espejo", "eco_color", "eco_frase")

EDIT = "edit"                     # cada verso con un diseño distinto (los coros, siempre el mismo)
NINGUNA = ""
NOMBRES = OrderedDict([(EDIT, ("Edit total", "Cada verso con un diseño distinto, como un edit: los coros siempre igual"))])
NOMBRES.update((k, (d.NOMBRE, d.DETALLE)) for k, d in DISENOS.items())
POR_DEFECTO = ""                  # la clásica de la escena; las épicas se eligen

# con qué diseños se monta «Edit total» según lo largo que sea el verso
_CORTOS = ("impacto", "tunel", "eco", "phonk", "katana", "fuego")
_MEDIOS = ("impacto", "poster", "katana", "glitch", "cromo", "electro", "phonk", "fuego", "viral", "eco", "garabato")
_LARGOS = ("viral", "poster", "glitch", "impacto", "letrero", "katana", "estelar", "cromo", "garabato")

ADELANTO_S = 0.09                 # lo que tarda en clavarse la entrada: se suma a la música
COLA_S = 1.6                      # lo que se queda el último plano de un verso si luego no viene nada
GUARDADOS = 8                     # planos preparados a la vez

# cuánto se mueve la letra con la música: clave -> (nombre, en qué consiste, factor)
INTENSIDADES = OrderedDict((
    ("suave", ("Suave", "Se mueve poco: para leer con calma", 0.30)),
    ("normal", ("Normal", "Acompaña a la música sin exagerar", 0.60)),
    ("fuerte", ("Fuerte", "Golpes y sacudidas como en un edit", 1.0)),
    ("brutal", ("Brutal", "Todo al máximo: late y tiembla con cada golpe", 1.8))))
INTENSIDAD_POR_DEFECTO = "normal"

_intensidad = INTENSIDAD_POR_DEFECTO
_actual = POR_DEFECTO
_vivos = weakref.WeakSet()


def normalizar(clave):
    return clave if clave in OFRECIDAS else NINGUNA


def actual():
    return _actual


def fijar(clave):
    global _actual
    _actual = normalizar(clave)
    for w in list(_vivos):
        try:
            w.al_cambiar_letra_epica()
        except RuntimeError:
            pass


def intensidad():
    return _intensidad


def fijar_intensidad(clave):
    """Se nota en el siguiente cuadro: no hay que volver a preparar nada."""
    global _intensidad
    _intensidad = clave if clave in INTENSIDADES else INTENSIDAD_POR_DEFECTO
    base.INTENSIDAD[0] = INTENSIDADES[_intensidad][2]


def suscribir(widget):
    """El widget recibe `al_cambiar_letra_epica()` cuando cambia el ajuste."""
    _vivos.add(widget)


def _limpia(texto):
    return re.sub(r"[^\w]+", " ", str(texto or "").lower()).strip()


def elegir_de(clave, texto, indice, anterior=None):
    """Qué diseño lleva un verso. En «Edit total» sale del propio texto: un coro repetido se ve siempre igual."""
    if clave != EDIT:
        return clave
    palabras = _limpia(texto).split()
    lista = _CORTOS if len(palabras) <= 2 else _MEDIOS if len(palabras) <= 6 else _LARGOS
    n = sum((i + 1) * ord(c) for i, c in enumerate("".join(palabras)[:40]))
    elegido = lista[n % len(lista)]
    if elegido == anterior:
        elegido = lista[(n + 1 + indice % 2) % len(lista)]
    return elegido


def limpiar_palabra(w):
    """La palabra sin lo que solo estorba en grande: paréntesis de coros, guiones sueltos."""
    return re.sub(r"^[\"“”«»(\[¡¿]*[(\[]|[)\]]$|^[-–—]+$", "", w).strip() or w


class Montaje:
    """La letra entera cortada en planos, para un diseño (o «Edit total»)."""

    def __init__(self, clave, versos, repartir):
        """versos: [(índice de línea, texto, ms, canto_ms, ms_siguiente o None)], en orden.
        repartir(texto, ms, canto) -> [(palabra, ms)]."""
        self.clave = clave
        self.planos = []
        self._prep = OrderedDict()
        self._clave_cx = None
        anterior, de_texto = None, {}
        for k, (linea, texto, ms, canto, ms_sig) in enumerate(versos):
            limpio = _limpia(texto)
            if limpio in de_texto:
                estilo = de_texto[limpio]
            else:
                estilo = elegir_de(clave, texto, k, anterior)
                de_texto[limpio] = estilo
            anterior = estilo
            self._cortar(estilo, linea, texto, ms, canto, ms_sig, repartir)
        # el fin de cada plano: cuando entra el siguiente, o su cola
        for i, pl in enumerate(self.planos):
            sig = self.planos[i + 1].t0 if i + 1 < len(self.planos) else None
            tope = pl.t1
            if sig is not None and sig <= tope + 0.35:
                pl.t1 = max(pl.t0 + 0.05, sig)
            elif sig is not None:
                pl.t1 = min(tope, sig)
        self._inicios = [pl.t0 for pl in self.planos]

    def _cortar(self, estilo, linea, texto, ms, canto, ms_sig, repartir):
        d = DISENOS[estilo]
        pares = [(limpiar_palabra(w), t / 1000.0) for w, t in repartir(texto, ms, canto)]
        pares = [(w, t) for w, t in pares if re.search(r"\w", w)]
        if not pares:
            return
        grupos = trocear([w for w, _t in pares], d.PALABRAS, d.LETRAS)
        fin_canto = (ms + (canto or 1800)) / 1000.0
        fin = fin_canto + COLA_S
        if ms_sig is not None:
            fin = min(fin, max(ms_sig / 1000.0, pares[-1][1] + 0.25))
        for j, g in enumerate(grupos):
            ult = j + 1 == len(grupos)
            t1 = fin if ult else pares[grupos[j + 1][0]][1]
            self.planos.append(Plano([pares[i][0] for i in g], [pares[i][1] for i in g], pares[g[0]][1], t1, linea,
                                     len(self.planos), estilo, ult))

    # ------------------------------------------------------------ en qué plano se está

    def indice(self, t):
        return bisect.bisect_right(self._inicios, t) - 1

    def viva(self, t):
        """¿Hay algo en pantalla en el segundo `t`?"""
        i = self.indice(t)
        if i < 0:
            return False
        pl = self.planos[i]
        return t <= pl.t1 + DISENOS[pl.estilo].SALIDA

    # ------------------------------------------------------------ preparar y pintar

    def preparado(self, i, cx):
        if self._clave_cx != cx.clave():
            self._clave_cx = cx.clave()
            self._prep.clear()
        o = self._prep.get(i)
        if o is None:
            pl = self.planos[i]
            o = self._prep[i] = DISENOS[pl.estilo].preparar(pl, cx)
            while len(self._prep) > GUARDADOS:
                self._prep.popitem(last=False)
        else:
            self._prep.move_to_end(i)
        return o

    def adelantar(self, t, cx, cuantos=2):
        """Prepara el siguiente plano que falte (uno por llamada). True si hizo algo."""
        i = self.indice(t)
        for j in range(max(0, i), min(len(self.planos), i + 1 + cuantos)):
            if j not in self._prep or self._clave_cx != cx.clave():
                self.preparado(j, cx)
                return True
        return False

    def olvidar(self):
        self._prep.clear()

    def pintar(self, p, t, cx):
        """Pinta lo que toca en el segundo `t`, con el centro del lienzo en el (0, 0) del pintor."""
        i = self.indice(t)
        if i < 0:
            return False
        algo = False
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if base.INTENSIDAD[0] > 1.0:                # la letra entera late con la música, sea cual sea el diseño
            s = 1.0 + 0.055 * (base.INTENSIDAD[0] - 1.0) * cx.golpe
            p.scale(s, s)
        for j in (i - 1, i):                        # el que se va, debajo del que entra
            if j < 0:
                continue
            pl = self.planos[j]
            d = DISENOS[pl.estilo]
            dt = t - pl.t0
            if dt > pl.dur + d.SALIDA:
                continue
            p.save()
            d.pintar(p, pl, self.preparado(j, cx), dt, cx)
            p.restore()
            algo = True
        return algo
