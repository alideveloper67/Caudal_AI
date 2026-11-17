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
    "A": (52, 99, 192),
    "B": (63, 116, 208),
    "C": (74, 134, 225),
    "D": (17, 20, 26),
    "E": (166, 210, 247),
    "F": (30, 60, 138),
    "G": (20, 22, 42),
    "H": (127, 176, 232),
    "I": (90, 22, 48),
    "J": (233, 140, 188),
    "K": (210, 236, 255),
    "L": (116, 168, 240),
    "M": (47, 95, 184),
    "N": (200, 100, 152),
    "O": (29, 43, 92),
    "P": (255, 255, 255),
    "Q": (240, 106, 138),
    "R": (9, 25, 77),
    "S": (244, 246, 255),
    "T": (90, 111, 176),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".FF........................................FF.",
    "FAADFF..................................FFFAAD",
    "FLAFFADFFFF......FFFFRRRRRFFFFF....FFFFFAFFAAD",
    "FCFJJFFFLLCDF.FFFLLBBMMMMMBBLLCDFFFAAAFFFNNDAD",
    ".DCDJJJJFFAAADBLLLBBBMMMMMBBBCCBBBFFFFJJNNDAD.",
    ".FCCDJJJJJFFFBBBCCBBBMMMMMBBBBCBBBBAJJJNNDAAD.",
    "..DCCDJJJJNNBBBBBCBBBBMMMCBBBBBBBBBBJJJNDAAD..",
    "...DCFJJJNNBLAAAABBBBBBMBBCAAAABBBBBAJNNDAD...",
    "....DCDJJNBAABAAAAABBBBBBAACAAAAABBBBANDAD....",
    "....FCCDNNBAAAAEEEEABBBBBAAAAEEEEABBBAFAAD....",
    ".....DCADBAAAKKGGGGEEBBBAAAKKGGGGEEBBAADD.....",
    "......DAFBAAAKGPPGGGEBBBAAAKGPPGGGEBBAAD......",
    ".......DFBAAKKGPPGGGGHBBAAKKGPPGGGGEBAAD......",
    "........DBAAKEGGGGGGGHBBAAKEGGGGGGGEBAAD......",
    "........FLBAKEGGGGGGGHBBBAKEGGGGGGGEBAAD......",
    "........FLCAEEGGGGPGGEBBBAKEGGGGPGGEBAAD......",
    "........FLCCAEEGGGGGEEOTOOOEEGGGGGHBBAAD......",
    "........FLCCCHEEGGEEEOOOOOOEEEGGHHHBAAAD......",
    "........FBCCCBBEEEEEEEOOOOOEEEHHHBBAAAAD......",
    "......FFFDBCBBBBEEEEEEEEEEEEEHHIBBAAAAD.......",
    ".....FLLLADBBBBBBIISSIIIIIIISSIIAAAAAD........",
    ".....FLCCCADABBBBBIIIIIIIIIIIIIAAAAAD.........",
    ".....FCCCCCDDABBBBBIIIIQQQQIIIAAAADD..........",
    "......DCCCCCDDDBBBBBIIQQQQQIBBAADD............",
    ".......DCCCCCD.DBBBAAAAAAABBBBAD..............",
    "........DCCCCCDBBBAAAAAKKEABBAAADF............",
    ".........DCCCCFBBAAAAKKKEEEEBAAADCD...........",
    "..........DCCCADBAAAKKEEEEEEEAADCCCD..........",
    "...........DCAAAFAAKKEEEEEEEEHADCCCAD.........",
    "............DAAFBAAKEEEEEEEEHHHDCCCAD.........",
    ".............DFBBAAKEEEEEEEEHHHDCCCAD.........",
    ".............FAAAAAKEEEEEEEHHHCFCCCAD.........",
    "..............DAAAAKEEEEEHHHHHCCDCAAD.........",
    "..............FADDDHHEEEHHHHHDCCDAAD..........",
    ".............FCDCCCDDHHHHHHDDCDDCDD...........",
    "............FCCCCCCCCDCHHHDCCCCCCAD...........",
    "............FCCCCCCCAFCCCCDCCCCCCAD...........",
    ".............DACCCAAADDDDDACCCCAAAD...........",
    "..............DDAAADD.....DDAAAADD............",
    "................DDD.........DDDD..............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (46, 40)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 46x40).
    scale=int   -> sprite de 46x40 px ampliado por un entero, sin márgenes.
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
