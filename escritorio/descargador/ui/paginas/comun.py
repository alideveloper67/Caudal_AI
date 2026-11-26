# -*- coding: utf-8 -*-
"""Piezas que comparten varias paginas."""

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QWidget

from ...memoria import DiccionarioLimitado
from ..componentes import Carrusel, RejillaRapida

# respuestas del catálogo (Inicio, álbumes, listas...): las 200 últimas, y las de más de una
# hora se tiran (ninguna página las acepta tan viejas)
TOPE_CACHE = 200
CADUCA_SEG = 60 * 60
_CACHE = DiccionarioLimitado(TOPE_CACHE)


def cache(clave, minutos=15):
    dato = _CACHE.get(clave)
    if dato and time.time() - dato[0] < minutos * 60:
        return dato[1]
    return None


def guardar_cache(clave, valor):
    ahora = time.time()
    if len(_CACHE) >= TOPE_CACHE // 2:
        for k in [k for k, (t, _v) in _CACHE.items() if ahora - t > CADUCA_SEG]:
            _CACHE.pop(k, None)
    _CACHE[clave] = (ahora, valor)


def pintar_secciones(ctx, layout, secciones, desde=0):
    """Convierte las secciones del catalogo en carruseles y rejillas."""
    for s in secciones[desde:]:
        elementos = s.get("elementos") or []
        if not elementos:
            continue
        mas = None
        if s.get("mas") and s["mas"].get("id"):
            m = s["mas"]
            # el clic manda `checked` como primer argumento: no debe pisar `m`
            mas = (lambda *_a, m=m, t=s["titulo"]: ctx.navegar(
                {"pagina": "genero", "id": m["id"], "params": m.get("params"), "titulo": t}))
        if s.get("estilo") == "filas" and all(e.get("tipo") == "pista" for e in elementos):
            layout.addWidget(RejillaRapida(ctx, s["titulo"], elementos,
                                           columnas=4, filas=4,
                                           subtitulo=s.get("estribillo", "")))
        elif s.get("estilo") == "rejilla":
            layout.addWidget(Rejilla(ctx, s["titulo"], elementos))
        else:
            layout.addWidget(Carrusel(ctx, s["titulo"], elementos, mas=mas,
                                             subtitulo=s.get("estribillo", "")))


class Rejilla(QWidget):
    """Tarjetas en varias filas (generos, resultados de 'Mostrar todo')."""

    def __init__(self, ctx, titulo, elementos, ancho=176, padre=None):
        super().__init__(padre)
        from PySide6.QtWidgets import QLabel, QVBoxLayout
        from ..componentes import Tarjeta
        self.ctx = ctx
        self.elementos = elementos
        self.ancho = ancho
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        if titulo:
            t = QLabel(titulo)
            t.setObjectName("titulo_seccion")
            t.setContentsMargins(4, 0, 0, 0)
            v.addWidget(t)
        self.rej = QGridLayout()
        self.rej.setSpacing(6)
        self.rej.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        v.addLayout(self.rej)
        self.tarjetas = []
        for el in elementos:
            tj = Tarjeta(ctx, el, ancho)
            tj.abrir.connect(ctx.abrir_elemento)
            tj.reproducir.connect(ctx.reproducir_elemento)
            tj.menu.connect(ctx.menu_elemento)
            self.tarjetas.append(tj)
        self._columnas = 0
        self._ordenar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ordenar()

    def _ordenar(self):
        if not self.tarjetas:
            return
        ancho_t = self.tarjetas[0].width() + 6
        columnas = max(1, self.width() // ancho_t) if self.width() > 50 else 5
        if columnas == self._columnas:
            return
        self._columnas = columnas
        for tj in self.tarjetas:
            self.rej.removeWidget(tj)
        for i, tj in enumerate(self.tarjetas):
            self.rej.addWidget(tj, i // columnas, i % columnas)
