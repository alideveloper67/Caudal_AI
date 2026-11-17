#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano1.py                 -> guarda plano1.png
      from plano1 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (252, 211, 78),
    "B": (252, 211, 79),
    "C": (255, 242, 182),
    "D": (252, 212, 78),
    "E": (230, 164, 44),
    "F": (255, 233, 160),
    "G": (247, 160, 142),
    "H": (138, 42, 42),
    "I": (28, 26, 34),
    "J": (242, 122, 122),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................FF.......FF.................",
    "..................FFF.....FFFF................",
    ".................FFFF.....FFFF................",
    ".................AAAAAAAAAAAAA................",
    "..............AAAAAAAAAAAAAAAAAAA.............",
    "............AAAAAAAAAAAAAAAAAAAAAAA...........",
    "...........AAAAAAAAAAAAAAAAAAAAAAAAA..........",
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    ".........AAAAAAAAAAAAAAAAAAAAAAAAAAAAA........",
    "........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.......",
    ".......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA......",
    ".......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA......",
    "......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.....",
    "......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.....",
    "......AAAAAAAAAIIAAAAAAAAAAAAAIIAAAAAAAAA.....",
    "......AAAAAAAAIIAIAAAAAAAAAAAIAIIAAAAAAAA.....",
    "......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.....",
    ".......AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA......",
    ".......AAAGGGGGAAAAAHHHHHHHAAAAAGGGGGAAA......",
    "....BB.AAAGGGGAAAAAAAHHHHHAAAAAAAGGGGAAA......",
    "...BBBBBAAAAAAAAAAAAAHJJJHAAAAAAAAAAAAA.......",
    "..BBBBBB.AAAAAAAAAAAAAAAAAAAAAAAAAAAAA........",
    "..BBBBBBB.AAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    "...BBBBBBB.AAAAAAAAAAAAAAAAAAAAAAAAA..........",
    "....BBBBBBB.EEEAAAAAAAAAAAAAAAAAAEE...........",
    ".....BBBBBBBAAEEEAAAAAAAAAAAAAAEEAA...........",
    "......BBBBBBBAAAAEEEEEEEEEEEEEEAABBBB.........",
    ".......BBBBBBBAAAACCCCEEEECCCCCCABBBBBDDDDD...",
    "........BBBBBBAAACCCCCCCCCCCCCCCBBBBBBDDDDDD..",
    ".........BBBBBAACCCCCCCCCCCCCCCCCBBBBBBDDDDD..",
    "..........BBBBAACCCCCCCCCCCCCCCCCBBBBBBDDDDD..",
    "...........AAAAACCCCCCCCCCCCCCCCCBBBBBBDDDD...",
    "...........AAAAACCCCCCCCCCCCCCCCCAABBBDDDDD...",
    "...........AAAAACCCCCCCCCCCCCCCCCAAADDDDDD....",
    "............AAAAACCCCCCCCCCCCCCCAAA.DDDDD.....",
    "............AAAAAACCCCCCCCCCCCCCAAA...........",
    ".............AAAAAACCCCCCCCCCCCAAA............",
    ".............BBBBBBACCCCCCCCCBBBBB............",
    "............BBBBBBBBAAAACAABBBBBBBBB..........",
    "...........BBBBBBBBBBAAAAAABBBBBBBBB..........",
    "............BBBBBBBB.......BBBBBBBBB..........",
    ".............BBBBBB.........BBBBBBB...........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (46, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 46x42).
    scale=int   -> sprite de 46x42 px ampliado por un entero, sin márgenes.
    transparent -> el fondo pasa a ser transparente (RGBA).
    """
    mode = "RGBA" if transparent else "RGB"
    if scale is None:
        cx, cy, ox, oy, size = CELL_X, CELL_Y, OFFSET_X, OFFSET_Y, CANVAS
    else:
        cx = cy = scale
        ox = oy = 0
        size = (len(ROWS[0]) * scale, len(ROWS) * scale)
    bg = PALETTE[BACKGROUND]
    bg_fill = (*bg, 0) if transparent else bg
    img = Image.new(mode, size, bg_fill)
    d = ImageDraw.Draw(img)
    for r, row in enumerate(ROWS):
        y0, y1 = _bounds(r, cy, oy)
        for c, ch in enumerate(row):
            if ch == BACKGROUND:
                continue
            x0, x1 = _bounds(c, cx, ox)
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=(*PALETTE[ch], 255) if transparent else PALETTE[ch])
    return img


if __name__ == "__main__":
    render().save("plano1.png")
    print("Guardado plano1.png")
