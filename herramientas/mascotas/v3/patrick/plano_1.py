#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano_1.py                 -> guarda plano_1.png
      from plano_1 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (247, 163, 185),
    "B": (247, 163, 184),
    "C": (156, 204, 60),
    "D": (255, 255, 254),
    "E": (138, 76, 200),
    "F": (20, 16, 28),
    "G": (138, 26, 48),
    "H": (28, 20, 32),
    "I": (236, 108, 142),
    "J": (246, 224, 90),
    "K": (242, 98, 126),
    "L": (255, 255, 253),
    "M": (200, 88, 122),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................",
    "..............................................",
    "......................BB......................",
    ".....................BBBB.....................",
    ".......A.............BBBB.....................",
    ".....AAAA...........BBBBBB....................",
    ".....AAAAA.........BBBBBBBB...................",
    ".....AAAAA.........HBBBBBBH...................",
    ".....AAAAAA.......HHHHBBHHHHH.................",
    "......AAAAA......HBBBBBBBBBBH.................",
    "......AAAAAA.....BBDDDBBDDDDB.................",
    ".......AAAAAA....BDDDDDBDDDDB.................",
    "........AAAAAA...BDDLFDDDLFDB.................",
    "........AAAAAAA.BBDFFFDDDFFFDB................",
    ".........AAAAAAABBDFFFFDDFFFBB................",
    ".........AAAAAAABBDDFFBBDFFFBBB...............",
    "..........AAAAAAABBDDBBBBDDBBBB...............",
    "...........AAAAIIIBBBBBBBBBBIII...............",
    "...........AAAAIIIBGGGGGGGGGIIII..............",
    "............AAAAABBGGGGGGGGBBBBA..............",
    "............AAAAABBBGKKKKGBBBBAAAA............",
    ".............AAAABBBBBKKBBBBBBAAAAA...........",
    ".............BAABBBBBBBBBBBBBBAAAAAAA.........",
    ".............BBBBBBBBBBBBBBBBBAAAAAAAA........",
    ".............BBBBBBBBBMMBBBBBBAAAAAAAAA.......",
    "............BBBBBBBBBBBBBBBBBBBAAAAAAAAA......",
    "............BCCCBBBBBBBBBBBBBBCCCAAAAAAAA.....",
    "...........CCCCCCCCCCCCCCCCCCCECCCCAAAAAA.....",
    "...........CCCCEECCCCCCCECCCCEJECCC..AAAA.....",
    "...........CCCEJJECCCCCEJECCCEJECCC...........",
    "...........CCCCEECCCCCCEJECCCCECCCC...........",
    "...........CCCCCCCCECCCCECCCCCCCCCC...........",
    "............CCCCCCEJECCCCCCCCCCCCC............",
    ".............AACCCEJEBBBBCCCCCCAA.............",
    ".............AAAAAAEA....AAAAAAAA.............",
    ".............AAAAAAA......AAAAAAA.............",
    "..............AAAAAA......AAAAAA..............",
    "..............AAAAAA......AAAAAA..............",
    "..............AAAAAA......AAAAAA..............",
    "..............AAAAA........AAAAA..............",
    "..............AAAAA........AAAAA..............",
    "...............AAAA........AAAA...............",
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
    render().save("plano_1.png")
    print("Guardado plano_1.png")
