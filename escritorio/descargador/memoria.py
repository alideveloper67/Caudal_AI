# -*- coding: utf-8 -*-
"""Cachés en memoria con tope: guardan lo último usado y sueltan lo más viejo.

Antes varias cachés (letras, traducciones, páginas del catálogo) crecían sin límite mientras
Caudal seguía abierto; con días de uso eran decenas de MB que nadie iba a volver a mirar.
"""

from collections import OrderedDict


class DiccionarioLimitado(OrderedDict):
    """Un dict normal que, al pasar de `tope` entradas, olvida las menos usadas (LRU).
    Leer con [] o get() cuenta como uso."""

    def __init__(self, tope=200, *args, **kwargs):
        self.tope = max(1, int(tope))
        super().__init__(*args, **kwargs)

    def __getitem__(self, clave):
        valor = super().__getitem__(clave)
        self.move_to_end(clave)
        return valor

    def get(self, clave, defecto=None):
        if clave in self:
            return self[clave]
        return defecto

    def __setitem__(self, clave, valor):
        super().__setitem__(clave, valor)
        self.move_to_end(clave)
        while len(self) > self.tope:
            self.popitem(last=False)
