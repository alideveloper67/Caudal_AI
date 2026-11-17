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
    "A": (44, 38, 64),
    "B": (251, 251, 255),
    "C": (57, 50, 79),
    "D": (70, 62, 95),
    "E": (8, 6, 12),
    "F": (28, 24, 40),
    "G": (214, 205, 235),
    "H": (247, 143, 184),
    "I": (205, 200, 234),
    "J": (106, 96, 136),
    "K": (119, 112, 158),
    "L": (255, 156, 192),
    "M": (42, 26, 46),
    "N": (104, 48, 75),
    "O": (42, 34, 56),
    "P": (223, 232, 255),
    "Q": (240, 106, 154),
    "R": (255, 255, 240),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".F.....................................FF.",
    "FDEF.................................FFAAE",
    "FJDDE...............................FAAAE.",
    "FDDDDEF............................FCAAAE.",
    ".EDDDDDE.........................FFCAAAE..",
    ".FDDDDDDEF.....................FFCCCAAAE..",
    "..EDDDDDDDE...................FCCCCAAAE...",
    "..FDDDDDDDDE....FFFNNNFFF....FCCCCCAAAE...",
    "...EDDDDDDDDEFFFJJJHHHJJDEFFFCCCCCAAAE....",
    "...FDDDCCCCCCCCCCCHHHHHDDDJJCCCCCCAAAE....",
    "....ECCCCCCCCCCCCHHOHOHHDDDDCCCCCAAAE.....",
    "....FCCCCCCCCCCCCCHHHHHCDDDDCCCCCAAAE.....",
    ".....ECCCCCCCCCCCCHHHHHCCDDDDCCCAAAE......",
    ".....FCCCCCCCCCCCCCHOHCCCCDDCCCCCAAE......",
    "......ECCCCCAAAAAAAAAAAAACCDCCCCCAE.......",
    ".....FCCCAAAAAAAAAAAAAAAAAAACCCCCAAE......",
    ".....FCCCAAAAABBBBBBBBBBBBBAACCCCAAE......",
    ".....FCCAAABBBBBBBBBBBBBBBBBBGCCCCAE......",
    ".....FCCAAABBBBBBBBBBBBBBBBBBGCCCAAE......",
    "....FCCCAABBBBBBBBBBBBBBBBBBBGGCCAAAE.....",
    ".....ECCAABBBBBFBBBBBBBBBFBBBGGCCAAE......",
    ".....FCCAABBBBFPFBBBBBBBFPFBBGGCCAAE......",
    ".....FCCAABBBBFFFBBBBBBBFFFBBGGCAAAE......",
    ".....FCCAABBBBFFFBBBBBBBFFFBBGGAAAAE......",
    "......ECCABBBBBBBBBBBBBBBBBBGGGAAAE.......",
    ".......ECABLLLBBBBBBQQBBBBBLLLGAAE........",
    ".......FAAALLLBBBBBBBBBMBBBLLLAAAE......F.",
    "........EEABBBBBBBBBMMMBBBGGGGAEE.....FFAE",
    "..........EDGGBBBBBBBRBGGGGGGDE......FJAAE",
    "...........EAGGGGGGGGGGGGGGGAE......FAJAAE",
    "...........FJEEEGGGGGGGGGEEEAE.......EAAAE",
    "..........FJJDDDEEEEEEEEEJDAAAE.....FAAEAE",
    "........KFFFDDDDDDDDDDDDDDAAAFAA....FAAEE.",
    ".......KBBAAEDDDDDDDDDDDDDDAFABBA..FAAE...",
    ".......KBBBKEDDDDDDDDDDDDDDFKBBIKAFAAE....",
    ".......KIBIKEDDDDDDDDDDDDDDDEKKKEAAAE.....",
    "........AAKEJDDDDDDDDDDDDDDAAEEEAAAE......",
    "..........EAAAAAAAAAAAAAAAAAAAEEEEE.......",
    "...........EFFFFFFFFAFFFFFFFFE............",
    "..........KBAAAAAAAAAAAAAAAAAIA...........",
    "..........KIBBBBBIIA.ABBBBBIIA............",
    "...........AAIIIIIA...AIIIIIA.............",
    ".............AAAAA.....AAAAA..............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (42, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 42x43).
    scale=int   -> sprite de 42x43 px ampliado por un entero, sin márgenes.
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
