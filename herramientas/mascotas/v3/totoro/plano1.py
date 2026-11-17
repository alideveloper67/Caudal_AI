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
    "A": (140, 148, 158),
    "B": (241, 230, 198),
    "C": (140, 148, 159),
    "D": (140, 147, 158),
    "E": (58, 42, 48),
    "F": (110, 118, 130),
    "G": (253, 253, 246),
    "H": (62, 68, 80),
    "I": (92, 184, 74),
    "J": (22, 22, 30),
    "K": (47, 122, 44),
    "L": (46, 48, 56),
    "M": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "............DDDD....IIIIIII..DDDD.............",
    "............DDDD....IKKKKKIIDDDDD.............",
    "............DDDDD....IIIIIIIDDDDD.............",
    "............DDDDD.....KKAI..DDDDD.............",
    "............DDDDDAAAAAAAAAAAADDDD.............",
    "............DDDAAAAAAAAAAAAAAAADD.............",
    ".............DAAAAAAAAAAAAAAAAAAD.............",
    ".............AAAAAAAAAAAAAAAAAAAA.............",
    "............AAAAAAAAAAAAAAAAAAAAAA............",
    "...........AAAAGGGGAAAAAAAAAGGGGAAA...........",
    "...........AAAAGGJJGAAAAAAAGGJJGAAA...........",
    ".......HH.AAAAGGJJJGAALLLAAGJJJGGAAA...H......",
    ".........HHAAAAGJJJGAAAAAAAGGJJGAAAAHH........",
    ".........AAAAAAGGGGAAAAAAAAAGGGGAAAAA.........",
    ".........AAAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    ".CCC....HHHHAAAAAAAAAAAAAAAAAAEEAAAHHHHH......",
    "CCCCC...AAAAAAAAEEEEMEEEEEMMEEEAAAAAAA........",
    "CCCCCC.AAAHHAAAAAAEEEEEEEEEEEEAAAAAHHHA.......",
    "CCCCCC.HHAAAAAAAAAAAEEEEEEEEAAAAAAAAAAHH......",
    "CCCCCCCAAAAAAAAAAABBBBBBBBBBBBAAAAAAAAAA......",
    ".CCCCCAAAAAAAAAAABBBBBBBBBBBBBBAAAAAAAAACC....",
    ".CCCCCAAAAAAAAABBBBBBBBBBBBBBBBBBAAAAAAACCC...",
    "..CCCCAAAAAAAABBBBBBBBBBFBBBBBBBBBAAAAAAACC...",
    "..CCCCAAAAAAAABBBBFFBBBFFFBBBFFBBBBAAAAAACCC..",
    "...CCAAAAAAAABBBBFBBFBFFBFBBFBBFBBBAAAAAACCC..",
    "....CAAAAAAAABBBBBBBBBBBBBBBBBBBBBBBAAAAACCCC.",
    ".....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBAAAAAACCC.",
    ".....AAAAAAABBBFFBBBBFFBBBFFBBBFFBBBBAAAAACCC.",
    ".....AAAAAAABBFFBFBBFBFFBFBFFBFBBFBBBAAAAACCC.",
    "....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBAAAAACCC.",
    "....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBAAAAACCC.",
    "....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBAAAAACC..",
    "....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBAAAAA....",
    ".....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBAAAAA....",
    ".....AAAAAAABBBBBBBBBBBBBBBBBBBBBBBBAAAAAA....",
    ".....AAAAAAAABBBBBBBBBBBBBBBBBBBBBBAAAAAAA....",
    "......AAAAAAAAABBBBBBBBBBBBBBBBBBAAAAAAAA.....",
    ".......AAAAAAACCAAABBBBBBBBBBBCCCAAAAAAA......",
    "..........ACCCCCCCCAAAAAAAAACCCCCCCC..........",
    "...........CCCCCCCCAAAAAAAAACCCCCCCC..........",
    "...........CCCCCCCC.........CCCCCCCC..........",
    ".............CCCC.............CCCC............",
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
