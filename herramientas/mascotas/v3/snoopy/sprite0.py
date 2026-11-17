#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite0.py                 -> guarda sprite0.png
      from sprite0 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (255, 255, 255),
    "B": (200, 198, 224),
    "C": (18, 18, 26),
    "D": (228, 226, 240),
    "E": (34, 32, 42),
    "F": (122, 120, 152),
    "G": (26, 18, 18),
    "H": (224, 48, 46),
    "I": (10, 8, 14),
    "J": (192, 30, 36),
    "K": (42, 28, 36),
    "L": (74, 70, 88),
    "M": (246, 160, 176),
    "N": (242, 194, 48),
    "O": (138, 20, 24),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".........FFFFFFF.....................",
    "......FFFAAAAAAAGFF..................",
    ".....FBBBAAAAAAAAAAGF................",
    "....FBBBBBAAAAAAAAAAAGF..............",
    "...FBBCCCCCAAAAAAAAAAAAG.............",
    "...FBBCEEEECAAAAAAAAAAAAGF...........",
    "..FBBCLEEEEIAAAAAAAAAAAAAAGFF........",
    "..FBBCEEEEEIAAAAAAAAAAAAAAAAAGFF.....",
    "..FBBCEEEEEIAAAAAAAACAAAAAAADDDDGIII.",
    "..FBCLEEEEEIAAAAAAACCCAAAAAADDDDCCCCC",
    "..FBCEEEEEEIAAAAAAACCCAAAAADDDDCCCCCC",
    "..FBCEEEEEEIAAAAAAACCAAAADDDDDDCCCCCC",
    "..FBCEEEEEEIAAAAAAAAAADDDDDDDDDDCCCC.",
    "..FBCEEEEECIAAAAADDDDDDDDDDDDDDDBBBG.",
    "..FBCEEEEEIDDDDDDMMMDDDDDDDDDDDBBBG..",
    "...CLEEEEEIDDDDDDDMKKDDDDDKDDBBBBBG..",
    "...ILEEEECIDDDDDDDDDDKKKKKBBBBBBBG...",
    "...ILEEECIDDDDDDDDDDDBBBBBBBBBBGG....",
    "...IEEEEIBDDDDBBBBBBBBBBBBBBGGG......",
    "....CIIIIBBBBBBBBBBBBBBGGGCC.........",
    "....OHHHHHGGBBBBHHHJGGG..FAAC........",
    "....OHHHHHHHHHHHHHHJG...FAAABC.......",
    ".....GJJJHHHHHJJJJJJG.FFAAAABC.......",
    ".....FAAAAJJHNNBBBBBGFAABBBBBC.......",
    ".....FAAAAAAANNABCCCAABBBCCCC........",
    ".....FAAAAAAAAAAAFFFFFBCC............",
    ".FF.FAAAAAAAAAAAAAAABBG..............",
    "FABCFAAAAAAAAAAAAAAABBG..............",
    "FAACFAAAAAAAAAAAAAAABBG..............",
    "FAAAGAAAAAAAAAAAAAAABBG..............",
    ".CAAFAAAAAAAAAAAAAAABBG..............",
    ".FBAFAAAAAAAAAAAAAAABBG..............",
    "..CCFAAAAAAAAAAAAAABBBG..............",
    "....GAAAAAAAAAAAAAABBBG..............",
    ".....GAAAAAAAAAAAABBBG...............",
    ".....FBAAAAAAAAABBBBBG...............",
    "......GBBBBBBBBBBBBBG................",
    "......FCCBBBBBBBBBCCACFF.............",
    ".....FAAACCCCCCCCCAAAAAAC............",
    "....FAAAAAAABBCAAAAAAAAABC...........",
    "....FBAAAABBBC.CBAAAAABBBC...........",
    ".....CCBBBBCC...CCBBBBBCC............",
    ".......CCCC.......CCCCC..............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (37, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 37x43).
    scale=int   -> sprite de 37x43 px ampliado por un entero, sin márgenes.
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
    render().save("sprite0.png")
    print("Guardado sprite0.png")
