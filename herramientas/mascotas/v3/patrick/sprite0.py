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
    "A": (247, 163, 185),
    "B": (26, 17, 19),
    "C": (226, 120, 150),
    "D": (236, 142, 167),
    "E": (156, 204, 60),
    "F": (168, 62, 94),
    "G": (22, 26, 17),
    "H": (58, 102, 18),
    "I": (255, 255, 254),
    "J": (255, 184, 197),
    "K": (138, 76, 200),
    "L": (20, 16, 28),
    "M": (138, 26, 48),
    "N": (28, 20, 32),
    "O": (236, 108, 142),
    "P": (114, 166, 40),
    "Q": (246, 224, 90),
    "R": (242, 98, 126),
    "S": (190, 224, 95),
    "T": (12, 7, 13),
    "U": (200, 88, 122),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................FF..................",
    ".................FDCB.................",
    "................FJJDCB................",
    "................FJDDDB................",
    "...............FJJDDDCB...............",
    "..F...........FJJADDDDCB..............",
    ".FAB..........TNAAADDDNBT.............",
    "FJJAB........TNNNNAANNNNNB............",
    "FJAAAB......TNJAAAAAADCCNB............",
    "FAAAAAB.....FJAIIIAAIIIIAB............",
    ".BAAAAAB....FJIIIIIAIIIIAB............",
    ".FAAAAAABF..FJIIILIIIILIAB............",
    "..BAAAAAAABFJJILLLIIILLLICB...........",
    "...BAAAAAAABJAILLLLIILLLDCB...........",
    "...FAAAAAAAFAAIILLAAILLLDCCB..........",
    "....BAAAAAAFFAAIIAAADIIDDDCB..........",
    ".....BAAAAFOOOAAAAAADDDDOOOB..........",
    ".....FAAAAFOOOAMMMMMMMMMOOOOB.........",
    "......BAAACBBAAMMMMMMMMDCCCBBF........",
    ".......BAACCFJAAMRRRRMDDCCBJAAB.......",
    "........BFCFDDDDDDRRADDDCCBAAAABF.....",
    "........FDFFDDDDDDDDDADDCCBAAAAAAB....",
    "........FDDDDDDDDDDDDDDDDCBAAAAAAAB...",
    "........FCDDDDDDDDUUDDDDCCFAAAAAAAAB..",
    ".......FCCCCCCCCCCCCCCCCDCCFFAAAAAACB.",
    ".......FCGGGCCCCCCCCCCCCCCHGGFFAAAACCB",
    "......HSGSEHHGGGGGGGHGGGGHKHEGGBCCCCCB",
    "......HSEEHKKHEEEEEHKHEEHKQKGEPGBCCCCB",
    "......HSEHKQQKGEEEHKQKGEHKQKGEPG.BBBB.",
    "......HSEEGKKGEHEEHKQKGEEGKGEEPG......",
    "......HEEEEGGEHKHEEGKGEEEEGEEPPG......",
    ".......GEEEEEHKQKGHHGEEEEEEEPPG.......",
    "........GPHEEHKQKHAAGHEEEEPHPG........",
    ".........BBHHHHKBBBBBBHHHHHBB.........",
    "........FJJBBBBBCB..FABBBBBJCB........",
    "........FAAAAAACB....BAAAAACCB........",
    ".........BAAAAACB....FJAAAACB.........",
    ".........FJAAAACB....FJAAAACB.........",
    ".........FJAAACCB....FAAAAACB.........",
    ".........FJAAACB......BAAAACB.........",
    ".........FAAAACB......FJAACCB.........",
    "..........BCCCCB......FCCCCB..........",
    "...........BBBB........BBBB...........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (38, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 38x43).
    scale=int   -> sprite de 38x43 px ampliado por un entero, sin márgenes.
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
