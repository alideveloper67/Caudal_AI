#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano0.py                 -> guarda plano0.png
      from plano0 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (184, 131, 79),
    "B": (251, 230, 192),
    "C": (183, 131, 79),
    "D": (184, 130, 79),
    "E": (184, 131, 78),
    "F": (251, 231, 192),
    "G": (251, 230, 193),
    "H": (34, 20, 12),
    "I": (244, 160, 138),
    "J": (58, 32, 16),
    "K": (74, 42, 22),
    "L": (200, 204, 216),
    "M": (255, 255, 255),
    "N": (122, 127, 148),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................",
    "..............................................",
    ".........EEE......................EEE.........",
    "........EEEEEE..................EEEEEE........",
    ".......EEEEEEEE......AAAA......EEEEEEEE.......",
    "......EEEBBBBEE..AAAAAAAAAAAA..EEBBBBEEE......",
    "......EEBBBBBEAAAAAAAAAAAAAAAAAAEBBBBBEE......",
    "......EEBBBBBAAAAAAAAAAAAAAAAAAAABBBBBEE......",
    ".......EEBBBAAAAAAAAAAAAAAAAAAAAAABBBEE.......",
    ".......EEEAAAAAAAAAAAAAAAAAAAAAAAAAAEEE.......",
    ".........EAAAAAAAAAAAAAAAAAAAAAAAAAAE.........",
    ".........AAAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    ".........AAAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    "........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA........",
    "........AAAAAAAMHAAAAAAAAAAAAMHAAAAAAA........",
    "........AAAAAAHHHAAAAAAAAAAAAHHHAAAAAA........",
    "........AAAAAAHHHAAAFFFFFFAAAHHHAAAAAA........",
    "........AAAAAAAAAAAFFJJJJFFAAAAAAAAAAA........",
    "........AAAAIIAAAAFFFFJJFFFFAAAAIIAAAA........",
    ".........AAAIIIAAAFFFFFFFFFFAAAIIIAAA.........",
    ".........AAAAAAAAAFFFKFFKFFFAAAAAAAAA.........",
    "..........AAAAAAAAAFFFKKFFFAAAAAAAAA..........",
    "...........AAAAAAAAAFFFFFFAAAAAAAAA...........",
    "............AAAAAAAAAAAAAAAAAAAAAA............",
    ".............AAAAAAAAAAAAAAAAAAAA.............",
    "..............AAAAAAAAAAAAAAAAAA..............",
    ".............DDDDAAAAAAAAAAAADDDD.............",
    "..........CCCCDDDDDDBAAAABDDDDDDCCCC..........",
    ".........CCCCCCDDDBBBBNNBBBBDDDCCCCCC.........",
    ".........CCCCCCDDBBBBBLLBBBBBDDCCCCCC.........",
    ".........CCCCCCDDBBBBBLLBBBBBDDCCCCCC.........",
    ".........CCCCCCDBBBBBBBBBBBBBBDCCCCCC.........",
    ".........CCCCCDDBBBBBBBBBBBBBBDDCCCCC.........",
    ".........CCCCDDDDBBBBBBBBBBBBDDDDCCCC.........",
    "............DDDDDBBBBBBBBBBBBDDDDD............",
    ".............DDDDDBBBBBBBBBBDDDDD.............",
    ".............CCCCCBBBBBBBBBBCCCCC.............",
    "............CCCCCCCCBBBBBBCCCCCCCC............",
    "...........CCCGGGGCCCDDDDCCCGGGGCCC...........",
    "...........CCCGGGGGCCDDDDCCGGGGGCCC...........",
    "............CCCGGGCC......CCGGGCCC............",
    "..............CCCC..........CCCC..............",
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
    render().save("plano0.png")
    print("Guardado plano0.png")
