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
    "A": (251, 251, 255),
    "B": (224, 110, 158),
    "C": (236, 136, 177),
    "D": (247, 161, 197),
    "E": (232, 228, 245),
    "F": (62, 14, 36),
    "G": (168, 56, 106),
    "H": (214, 205, 235),
    "I": (43, 37, 64),
    "J": (253, 211, 228),
    "K": (27, 20, 38),
    "L": (205, 200, 234),
    "M": (122, 18, 56),
    "N": (255, 111, 159),
    "O": (255, 198, 220),
    "P": (255, 143, 180),
    "Q": (119, 112, 158),
    "R": (210, 58, 114),
    "S": (246, 194, 28),
    "T": (223, 232, 255),
    "U": (255, 208, 224),
    "V": (255, 216, 74),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..GGG............................",
    ".GCCBF...........................",
    ".GOCCBF.....................GGGG.",
    ".GODCCF...................GGCBBBF",
    ".GDDJCBF.................GCCBJBBF",
    "..FDJJCBF...............GCCJJBBF.",
    "..GDDJCCF..............GCCJJBBF..",
    "...FCJJCBF............GCCCJJBF...",
    "...GCMMJMMF..........GCCCJJBF....",
    "...GMNNMNNMGGGGGGGGGGGOCJJBBF....",
    "...GMNUNNNMCCCCCCCCOOOOCJJBF.....",
    "....FMNVNMCCCCCCCCCCDDDCJJBF.....",
    "....MNNNNRMBBBBBBBCCCDDDCCCF.....",
    "....MNRMNRMBBBBBBBBBBBDDCCCCF....",
    "...GCMMBMMBBBAAAAAAABBBDCCCCBF...",
    "..GCCBBBBAAAAAAAAAAAAEEECCCCCBF..",
    "..GCBBBBAAAAAAAAAAAAAEEEHCCCCBF..",
    ".GCCBBBAAAAAAAAAAAAAAEEEEHCCCBBF.",
    ".GCCBBAAAAAAAAAAAAAAAEEEEHCCCCBF.",
    "GCCCBBAAAAAAAAAAAAAAAEEEEHHCCCBF.",
    "GCCCBBAAAAAAAAAAAAAAEEEEEHHCCCBBF",
    "GCCCBBAAAAKKKAAAAAAAKKKEEHHCCBBBF",
    "GCCCBBAAAAKTKAAAAAAEKTKEEHHCCBBBF",
    "GDCCBBAAAAKKKAAAAAAEKKKEEHHCCBBF.",
    ".FCCBBAAAAKKKAAAAEEEKKKEHHHCBBBF.",
    ".GCCCBEEAAAAAEEEEEEEEEEEHHHBBBBF.",
    "..FCCBEPPPEEEEESSSEEEEEPPPBBBBF..",
    "..GBCCBPPPEEEEEEEEEEEEEPPPBBBF...",
    "...FBCCHEEEEEEEEEEEEEHHHHBBBF....",
    "....FFBCHHHHEEEEEHHHHHHHHBBF.....",
    "......FBBBHHHHHHHHHHHHHBBBF......",
    ".......FFBBBBBHHHHHBBBBBFF.......",
    "......GOOFFFBBBBBBBBBFFFODF......",
    "....QGGGDDDDFFFFFFFFFODDBGGF.....",
    "...QAAIIFDDDDDDDDDDDDDDDGIIAI....",
    "...QAAAQFDDDDDDDDDDDDDDDGIALLI...",
    "...QLALQFDDDDDDDDDDDDDDDGQLLI....",
    "....IIQFODDDDDDDDDDDDDDDDFII.....",
    "......FDDDDDDDDDDDDDDDDDBBF......",
    ".......FGGGGGGGGBGGGGGGGGF.......",
    "......QAIIIIIIIIIIIIIIIIILI......",
    "......QLAAAAALLI.IAAAAALLI.......",
    ".......IILLLLLI...ILLLLLI........",
    ".........IIIII.....IIIII.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (33, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 33x44).
    scale=int   -> sprite de 33x44 px ampliado por un entero, sin márgenes.
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
