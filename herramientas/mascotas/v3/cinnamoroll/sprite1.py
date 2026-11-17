#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite1.py                 -> guarda sprite1.png
      from sprite1 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (251, 251, 255),
    "B": (229, 230, 248),
    "C": (207, 210, 240),
    "D": (35, 42, 74),
    "E": (125, 132, 184),
    "F": (214, 236, 255),
    "G": (92, 130, 192),
    "H": (28, 42, 82),
    "I": (240, 248, 255),
    "J": (168, 200, 240),
    "K": (29, 42, 107),
    "L": (79, 142, 240),
    "M": (255, 163, 196),
    "N": (163, 176, 230),
    "O": (106, 63, 110),
    "P": (230, 240, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................EEEEEEEEE..................",
    "...............EEEAAAAAAAAADEE...............",
    "....GGGGGGGGGEEAAAAAAAAAAAAAABDEGGGGGGGGG....",
    "...GIIIIIIIJGAAAAAAAAAAAAAAAAABBGIIIIIIIFH...",
    "..GIIFFFFFJGAAAAAAAAAAAAAAAAAABBBGFFFFFFFFH..",
    ".GIIFFFFFJGAAAAAAAAAAAAAAAAAAABBBCGFFFFFFFFH.",
    "GIIFFFFFFGAAAAAAAAAAAAAAAAAAAABBBBCHFFFFFFFJH",
    "GIFFFFFFJGAAAAAAAAAAAAAAAAAAABBBBBCGFFFFFFFJH",
    "GIFFFFJFGAAAAAAAAAAAAAAAAAAAABBBBBBCHFFFFFFJH",
    "GIFFJJJHGAAAAAAAAAAAAAAAAAAAABBBBBBCGHJFFFFJH",
    "GJJJJHHEAAAAAAAAAAAAAAAAAAAABBBBBBBCCDHHJJJJH",
    ".HHHH..EAAAAAAAAAAAAAAAAAAAABBBBBBBCCD..HHHH.",
    ".......EAAAAAAAAAKAAAAAAAAAKBBBBBBCCCD.......",
    ".......EAAAAAAAAPKKAAAAAAAPKKBBBBBCCCD.......",
    "........DAAAAAAAKKKAAAAABBKKKBBBBBCCD........",
    "........EAAAAAAALLLAAABBBBLLLBBBBCCCD........",
    "........EBBBAAAALLLBBBBBBBLLLBBBBCCCD........",
    ".........DBBBBBBBBBBBBBBBBBBBBBBCCCD.........",
    ".........EBMMMMBBBBBBOBOBBBBBBMMMMCD.........",
    "..........DCBBBBBBBBBBOBBBBBBCCCCCD..........",
    "...........DCCBBBBBBBBBBBBBCCCCCCD...........",
    "............DDCCCBBBBBBBCCCCCCCDD............",
    "..............DDCCCCCCCCCCCCCDD..............",
    "................DDDCCCCCCCDDD................",
    ".................EEDDDDDDDDE.................",
    "...............EEAAAAAAAAACCDE...............",
    "..............EEEAAAAAAAAACCEDD..............",
    ".............EAADDAAAAAAAACEDAAD.EEEE........",
    "............EAAAEDAAAAAAAAAEDAAADAAAAD.......",
    "............EAACEDAAAAAAAAAEEAAAAAAAAAD......",
    ".............DEEDAAAAAAAAAAADEEAAAANNACD.....",
    ".............EDDAAAAAAAAAAAACDDDAANAANCD.....",
    ".............EAAAAAAAAAAAAAACCCDAANANCD......",
    "..............DAAAAAAAAAAAACCCDECAANCCD......",
    "..............ECAAAAAAAAACCCCCD.DDCCDD.......",
    "...............DEECCCCCCCCCEED....DD.........",
    "..............EADDEEEECEEEEDDAD..............",
    ".............EAAAADDDDDDDDDAAACD.............",
    ".............EAAAAACCD.DAAAAACCD.............",
    "..............DCCCCCD...DCCCCCD..............",
    "...............DDDDD.....DDDDD...............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (45, 41)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 45x41).
    scale=int   -> sprite de 45x41 px ampliado por un entero, sin márgenes.
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
    render().save("sprite1.png")
    print("Guardado sprite1.png")
