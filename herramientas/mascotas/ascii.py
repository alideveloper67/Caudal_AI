# -*- coding: utf-8 -*-
"""Pixel art dibujado a mano como texto (un carácter = un píxel), como en los sprites de Pokémon.

    from ascii import dibujo, hoja_rebote

    LEYENDA = {'K': '#101010',   # contorno oscuro
               'B': '#985000',   # contorno marrón (lado iluminado)
               'Y': '#f0e050',   # amarillo claro
               'y': '#f0b820',   # amarillo sombra
               '.': None}        # '.' o espacio = transparente
    FILAS = ['....KK....', '...KYYK...', ...]       # todas del mismo ancho, hasta 48 de ancho x 44 de alto
    base = dibujo(FILAS, LEYENDA)                    # PIL.Image RGBA (ancho x alto del dibujo)
    hoja = hoja_rebote(base)                         # hoja de 2 cuadros de 48x44 lista para exportar

`hoja_rebote` pone el dibujo centrado con los pies en la fila de abajo y genera el segundo cuadro «agachado»
(quita una fila del torso: el rebote clásico de los sprites de Pokémon). Si el segundo cuadro necesita algo más
(brazos, cola, orejas que se mueven) pasa `ajuste=fn(img)` que reciba el cuadro 1 y devuelva el cuadro 1 retocado,
o pasa `base2=` con otro dibujo hecho a mano para ese cuadro.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

W_DEF, H = 48, 44


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dibujo(filas, leyenda):
    """Convierte filas de texto a una imagen RGBA. Avisa (ValueError) si una fila mide distinto o falta un color."""
    filas = [f.replace(' ', '') for f in filas]
    ancho = len(filas[0])
    for n, f in enumerate(filas):
        if len(f) != ancho:
            raise ValueError(f'la fila {n} mide {len(f)} y la primera {ancho}')
    img = Image.new('RGBA', (ancho, len(filas)), (0, 0, 0, 0))
    px = img.load()
    for y, f in enumerate(filas):
        for x, c in enumerate(f):
            if c == '.':
                continue
            if c not in leyenda:
                raise ValueError(f"fila {y}, columna {x}: el carácter '{c}' no está en la leyenda")
            col = leyenda[c]
            if col is not None:
                px[x, y] = _rgb(col) + (255,)
    return img


def _fila_a_quitar(img, desde, hasta):
    a = np.array(img).astype(int)
    mejor, costo = desde, 10 ** 9
    for r in range(max(1, desde), min(len(a) - 1, hasta)):
        c = np.abs(a[r - 1] - a[r + 1]).sum()
        if c < costo:
            mejor, costo = r, c
    return mejor


def agachar(img, desde=0.62, hasta=0.82):
    """El dibujo con una fila menos del torso (queda 1 px más bajo, con los pies en el mismo sitio)."""
    w, h = img.size
    r = _fila_a_quitar(img, int(h * desde), int(h * hasta))
    out = Image.new('RGBA', (w, h - 1), (0, 0, 0, 0))
    out.paste(img.crop((0, 0, w, r)), (0, 0))
    out.paste(img.crop((0, r + 1, w, h)), (0, r))
    return out


def _poner(img, ancho_cuadro):
    w, h = img.size
    if w > ancho_cuadro or h > H:
        raise ValueError(f'el dibujo mide {w}x{h} y el cuadro es {ancho_cuadro}x{H}')
    c = Image.new('RGBA', (ancho_cuadro, H), (0, 0, 0, 0))
    c.paste(img, ((ancho_cuadro - w) // 2, H - h))
    return c


def hoja_rebote(base, base2=None, ajuste=None, ancho_cuadro=W_DEF):
    """Hoja de 2 cuadros: de pie + agachado (o `base2` hecho a mano). Cuadro de ancho_cuadro x 44."""
    c0 = _poner(base, ancho_cuadro)
    if base2 is not None:
        seg = base2
    else:
        seg = agachar(base)
    c1 = _poner(seg, ancho_cuadro)
    if ajuste is not None:
        c1 = ajuste(c1)
    out = Image.new('RGBA', (ancho_cuadro * 2, H), (0, 0, 0, 0))
    out.paste(c0, (0, 0))
    out.paste(c1, (ancho_cuadro, 0))
    return out
