# -*- coding: utf-8 -*-
"""«Mantener al día»: al abrir Caudal, lo nuevo de las cuentas vinculadas entra solo en Me gusta.

En silencio, como mucho cada 12 horas por cuenta, y solo lo que aún no se trajo. Leer y buscar van
en segundo plano; guardar, en el hilo de la interfaz (la base es suya), de tanda en tanda.
"""

import time

from PySide6.QtCore import QObject, Signal

from .. import importacion, servicios_externos, vinculadas
from ..hilos import en_segundo_plano

LOTE = 25


def _leer(servicio, conocidas):
    return servicios_externos.me_gusta(servicio, conocidas=conocidas).get("canciones") or []


def _buscar(canciones):
    """[(pista|None, clave externa)] de una tanda, buscando con calma (de dos en dos)."""
    from .dialogo_importacion import buscar_pista
    salida = {}

    def una(c):
        p = buscar_pista(c)
        salida[id(c)] = p
        return p
    importacion.emparejar(canciones, una, lote=LOTE, hilos=2)
    return [(salida.get(id(c)), c.get("externa") or "") for c in canciones]


class SincronizadorCuentas(QObject):
    termino = Signal(str, int)          # servicio, canciones nuevas

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.cola = []
        self.ocupado = False

    def revisar(self):
        """Pone al día las cuentas a las que les toca. Devuelve las que se van a revisar."""
        if self.ocupado:
            return []
        col = self.ctx.coleccion
        if col.estado(importacion.CLAVE_PENDIENTE, None):
            return []                   # hay una importación a medias: que acabe primero
        # la primera vez la pide la persona (con su avance a la vista); aquí, solo lo nuevo
        self.cola = [s for s in vinculadas.SERVICIOS
                     if servicios_externos.vinculada(s) and vinculadas.info(col, s)["completa"]
                     and vinculadas.toca_sincronizar(col, s)]
        salida = list(self.cola)
        self._otra()
        return salida

    def _otra(self):
        if not self.cola:
            self.ocupado = False
            return
        self.ocupado = True
        servicio = self.cola.pop(0)
        ya = vinculadas.conocidas(self.ctx.coleccion, servicio)
        en_segundo_plano(_leer, servicio, ya, ok=lambda c: self._leidas(servicio, ya, c),
                         error=lambda _e: self._otra(), dueno=self)

    def _leidas(self, servicio, ya, canciones):
        nuevas = vinculadas.nuevas(canciones, ya)[:vinculadas.TOPE_SILENCIOSO]
        # las más viejas primero: así las más nuevas quedan arriba en Me gusta
        self._tanda(servicio, list(reversed(nuevas)), 0)

    def _tanda(self, servicio, faltan, entraron):
        col = self.ctx.coleccion
        if not faltan:
            antes = vinculadas.info(col, servicio)
            vinculadas.anotar(col, servicio, ultima=time.time(), cuantas=antes["cuantas"] + entraron)
            if entraron and getattr(self.ctx, "me_gusta_cambio", None) is not None:
                self.ctx.me_gusta_cambio.emit("", True)
            self.termino.emit(servicio, entraron)
            self._otra()
            return

        def listas(pares):
            pistas = [p for p, _k in pares if p]
            n = col.agregar_me_gusta_varios(list(reversed(pistas)))[0] if pistas else 0
            vinculadas.anotar_traidas(col, servicio, [k for p, k in pares if p and k],
                                      [k for p, k in pares if not p and k])
            self._tanda(servicio, faltan[LOTE:], entraron + n)

        en_segundo_plano(_buscar, faltan[:LOTE], ok=listas, error=lambda _e: self._otra(), dueno=self)
