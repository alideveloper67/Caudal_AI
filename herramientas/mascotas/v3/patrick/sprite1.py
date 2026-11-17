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
    "A": (247, 163, 185),
    "B": (26, 17, 19),
    "C": (226, 120, 150),
    "D": (236, 142, 167),
    "E": (168, 62, 94),
    "F": (156, 204, 60),
    "G": (58, 102, 18),
    "H": (255, 255, 254),
    "I": (22, 26, 17),
    "J": (255, 184, 197),
    "K": (138, 76, 200),
    "L": (20, 16, 28),
    "M": (138, 26, 48),
    "N": (28, 20, 32),
    "O": (236, 108, 142),
    "P": (246, 224, 90),
    "Q": (114, 166, 40),
    "R": (242, 98, 126),
    "S": (190, 224, 95),
    "T": (12, 7, 13),
    "U": (200, 88, 122),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................EE..................",
    ".................EDCB.................",
    "...E............EJJDCB................",
    ".EEAB...........EJDDDB................",
    "EJJJCB.........EJJDDDCB...............",
    "EJAAACB.......EJJADDDDCB..............",
    "EJAAACB.......TNAAADDDNBT.............",
    "EAAAAACB.....TNNNNAANNNNNB............",
    ".BAAAAAB....TNJAAAAAADCCNB............",
    ".EAAAAAAB...EJAHHHAAHHHHAB............",
    "..BAAAAAAB..EJHHHHHAHHHHAB............",
    "...BAAAAAAB.EJHHHLHHHHLHAB............",
    "...EAAAAAACBJJHLLLHHHLLLHCB...........",
    "....BAAAAAAEJAHLLLLHHLLLDCB...........",
    "....EAAAAAAEAAHHLLAAHLLLDCCB..........",
    ".....BAAAAAEEAAHHAAADHHDDDCB..........",
    "......BAAAEOOOAAAAAADDDDOOOB..........",
    "......EAAAEOOOAMMMMMMMMMOOOOB.........",
    ".......BAAABBAAMMMMMMMMDCCCBBE........",
    ".......EAACCEJAAMRRRRMDDCCBJAAB.......",
    "........BECCEDDDDDRRADDDCCBAAAABE.....",
    "........EDEEDDDDDDDDDADDCCBAAAAAAB....",
    "........EDDDDDDDDDDDDDDDDCBAAAAAAAB...",
    "........ECDDDDDDDDUUDDDDCCEAAAAAAAAB..",
    ".......ECCCCCCCCCCCCCCCCDCCEEAAAAAACB.",
    ".......ECIIICCCCCCCCCCCCCCGIIEEAAAACCB",
    "......GSISFGGIIIIIIIGIIIIGKGFIIBCCCCCB",
    "......GSFFGKKGFFFFFGKGFFGKPKIFQIBCCCCB",
    "......GSFGKPPKIFFFGKPKIFGKPKIFQI.BBBB.",
    "......GSFFIKKIFGFFGKPKIFFIKIFFQI......",
    "......GFFFFIIFGKGFFIKIFFFFIFFQQI......",
    ".......IQGGFFGKPKGGGGFFFFFQGGQI.......",
    "........BBBGGGKPKAAAAGGGGGGBBB........",
    "........EAABBBBKBBBBBBBBBBBJCB........",
    "........EAAAAAABB....BAAAAACCB........",
    ".........BAAAAACB....EJAAAACB.........",
    ".........EAAAAACB....EJAAAACB.........",
    ".........EAAAACCB....EAAAAACB.........",
    ".........EAAAACB......BAAAACB.........",
    ".........EAAAACB......EJAACCB.........",
    "..........BCCCCB......ECCCCB..........",
    "...........BBBB........BBBB...........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (38, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 38x42).
    scale=int   -> sprite de 38x42 px ampliado por un entero, sin márgenes.
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
