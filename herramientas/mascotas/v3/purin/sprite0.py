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
    "A": (255, 226, 138),
    "B": (242, 184, 90),
    "C": (248, 205, 114),
    "D": (58, 30, 8),
    "E": (184, 122, 64),
    "F": (168, 104, 30),
    "G": (138, 84, 40),
    "H": (42, 20, 6),
    "I": (255, 243, 196),
    "J": (74, 36, 16),
    "K": (94, 52, 20),
    "L": (148, 88, 42),
    "M": (168, 112, 60),
    "N": (255, 181, 154),
    "O": (106, 58, 26),
    "P": (42, 26, 20),
    "Q": (30, 14, 4),
    "R": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...................J................",
    "..................JOQ...............",
    ".................JMOQ...............",
    "............JJJJJMMGQJJJ............",
    "..........JJMMMMMMGGGMMGQJ..........",
    ".........JMMMGGGGGGGGGGGGOQ.........",
    "........JMMGGGGGGGGGGGGGOJQF........",
    ".......FAJGGGGGGGGGGGGGOJCCCD.......",
    "......FAAIJJGGGGGGGGOJJJCCCCCD......",
    ".....FAIIIIIJJJJJJJJJICCCCCCBBD.....",
    "....FAAIIIIIIIIIIIIIIICCCCCBBBBD....",
    "...FAHHIIIIAAAAAAAAAAACCCCBBBBHAD...",
    "...KHEEHAAAAAAAAAAAAAACCCCBBBHEHH...",
    "..KEEEEKIAAAAAAAAAAAAAACCCBBHEEEEH..",
    ".KEEEEEKIAAAAAAAAAAAAAACCCBBHEEEELH.",
    ".KEEEEEKIAAARPAAAAAAAARPCCBBHEEEELH.",
    ".KEEEEEKIAAAPPAAAAAAAAPPCCBBHEEEEEH.",
    "KEEEEEEKIAAAPPAAAKKAAAPPCCCBHEEEEELH",
    "KEEEEEEKIAAAAAAAKKKKAAACCCCBKEEEEELH",
    "KEEEEEKNNNNAAAAAAAKAAACCCNNNNHEEEELH",
    "KEEEEEKNNNAAAAAAOOOOCCCCCCNNNHEEEELH",
    "KEEEEEKIAAAAAAAAACCCCCCCCCCCBHEEEELH",
    "KEEEELKCCCCCCCCCCCCCCCCCCCCBBKEEEELH",
    "KEEELKCCCCCCCCCCCCCCCCCCCCBBBBHEELLH",
    ".HELLHDBCCCCCCCCCCCCCCCCBBBBBDHELLH.",
    "..HLH..DBBBCCCCCCCCCCBBBBBBBD..HLH..",
    "...H..FFDDBBBBBBBBBBBBBBBBDFFDF.H...",
    ".....FADFFDDDBBBBBBBBBBDDDFDDAAD....",
    "....FAAADDDAADDDDDDDDDDIBFDAAAABD...",
    "...FAAAAAFDAAAAAAAAAAAAAAFDAAAABD...",
    "...FAAAAAFDAAAAAAAAAAAAAAFFAAABBD...",
    "....DAAABFDAAAAAAAAAAAAAAADFFFBD....",
    ".....DFFFDIAAAAAAAAAAAAAAAADDDD.....",
    ".....FDDDIAAAAAAAAAAAAAAAAABBBDFFF..",
    "......DBBBBBAAAAAAAABBBBBBBBBDAAABD.",
    "......FBFFFFFFAAAAABBBFFFFFFFDAAABD.",
    ".......DDDDDDDFAAABBBFDDDDDDDAAAABD.",
    "......FAAAAAAADFAAABFDAAAAAAADBBBBD.",
    ".....FAAAAAAAABFDBBFFAAAAAAABBDDDD..",
    "......DAAAAAAAFDBBBBDDAAAAAABD......",
    "......FBAAAABBBDDDDDDBAAAABBBD......",
    ".......DDBBBBDD......DDBBBBDD.......",
    ".........DDDD..........DDDD.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (36, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 36x43).
    scale=int   -> sprite de 36x43 px ampliado por un entero, sin márgenes.
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
