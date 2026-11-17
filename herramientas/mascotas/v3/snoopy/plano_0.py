#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano_0.py                 -> guarda plano_0.png
      from plano_0 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (255, 255, 255),
    "B": (254, 254, 255),
    "C": (34, 32, 42),
    "D": (224, 48, 46),
    "E": (22, 20, 28),
    "F": (20, 18, 26),
    "G": (42, 28, 36),
    "H": (246, 160, 176),
    "I": (242, 194, 48),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................",
    "................AAAAAAA.......................",
    ".............AAAAAAAAAAAAA....................",
    "............AAAAAAAAAAAAAAAA..................",
    "...........AACCCCCAAAAAAAAAAAA................",
    "...........AACCCCCCAAAAAAAAAAAA...............",
    "..........AACCCCCCCAAAAAAAAAAAAAA.............",
    "..........AACCCCCCCAAAAAAAAAAAAAAAAA..........",
    "..........AACCCCCCCAAAAAAAAFAAAAAAAAAAA.......",
    "..........ACCCCCCCCAAAAAAAFFFAAAAAAAAAAEEEE...",
    "..........ACCCCCCCCAAAAAAAFFFAAAAAAAAAEEEEE...",
    "..........ACCCCCCCCAAAAAAAFFAAAAAAAAAAEEEEE...",
    "..........ACCCCCCCCAAAAAAAAAAAAAAAAAAAAEEE....",
    "..........ACCCCCCCCAAAAAAAAAAAAAAAAAAAAAAA....",
    "..........ACCCCCCCAAAAAAHHHAAAAAAAAAAAAAA.....",
    "...........CCCCCCCAAAAAAAHGGAAAAAGAAAAAAA.....",
    "...........CCCCCCCAAAAAAAAAAGGGGGAAAAAAA......",
    "...........CCCCCCAAAAAAAAAAAAAAAAAAAAA........",
    "...........CCCCCAAAAAAAAAAAAAAAAAAA...........",
    "............CCCCAAAAAAAAAAAAAA................",
    "............DDDDD..AAAADDDD......BB...........",
    "............DDDDDDDDDDDDDDD.....BBBB..........",
    ".............DDDDDDDDDDDDDD....BBBBB..........",
    ".............AAAADDDIIAAAAA..BBBBBBB..........",
    ".............AAAAAAAIIAABBBBBBBB..............",
    ".............AAAAAAAAAAABBBBBB................",
    "............AAAAAAAAAAAAAAAAA.................",
    "........BB..AAAAAAAAAAAAAAAAA.................",
    "........BB..AAAAAAAAAAAAAAAAA.................",
    "........BBB.AAAAAAAAAAAAAAAAA.................",
    ".........BBBAAAAAAAAAAAAAAAAA.................",
    ".........BBBAAAAAAAAAAAAAAAAA.................",
    "...........BAAAAAAAAAAAAAAAAA.................",
    "............AAAAAAAAAAAAAAAAA.................",
    ".............AAAAAAAAAAAAAAA..................",
    ".............AAAAAAAAAAAAAAA..................",
    "..............AAAAAAAAAAAAA...................",
    "...............BAAAAAAAAABBB..................",
    ".............BBBBBBBB..BBBBBBBB...............",
    "............BBBBBBBBB.BBBBBBBBBB..............",
    "............BBBBBBBB...BBBBBBBBB..............",
    "..............BBBB.......BBBBB................",
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
    render().save("plano_0.png")
    print("Guardado plano_0.png")
