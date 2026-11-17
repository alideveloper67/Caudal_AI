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
    "A": (21, 21, 28),
    "B": (38, 38, 46),
    "C": (2, 2, 3),
    "D": (11, 11, 16),
    "E": (26, 23, 17),
    "F": (245, 194, 27),
    "G": (251, 251, 255),
    "H": (239, 187, 147),
    "I": (232, 173, 134),
    "J": (246, 201, 160),
    "K": (224, 36, 46),
    "L": (74, 74, 94),
    "M": (212, 144, 12),
    "N": (106, 26, 34),
    "O": (255, 222, 182),
    "P": (122, 74, 6),
    "Q": (106, 10, 18),
    "R": (106, 108, 148),
    "S": (168, 20, 30),
    "T": (196, 200, 228),
    "U": (98, 98, 122),
    "V": (243, 154, 138),
    "W": (236, 106, 120),
    "X": (255, 210, 58),
    "Y": (154, 90, 52),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "........DDDD......................DDDD.....",
    "......DDLLLBCD..................DDLLLBCD...",
    ".....DLLLBBBBAC................DLLLBBBBAC..",
    "....DLLDBBBBBBAC..............DLLDBBBBBBAC.",
    "....DLDUCBBBBBAC..............DLDUCBBBBBAC.",
    "...DLDUCBBBBBBAAC............DLDUCBBBBBBAAC",
    "...DLDUCBBBBBBAAC..DDDDDDDD..DLDUCBBBBBBAAC",
    "...DLBCBBBBBBAAACDDLLLLAAABCDDLBCBBBBBBAAAC",
    "...DBBBBBBBBBAADCAAABBAAAAABBCDBBBBBBBBAAAC",
    "....CBBBBBBBAADAAAOOJAAAAHHHBBACBBBBBBAAAC.",
    "....DABBBBAAAADAAOOJJJAAHHHHIBBDBBBBAAAAAC.",
    ".....CAAAAAAADAAOOJGGJJOHGGHIIBADAAAAAAAC..",
    "......CCAAAACLAAOJGGGGJJGGGGIILBACAAAACC...",
    "........CCCCDLAAOJGGAGJJGGAGIILBACCCCC.....",
    "...RRR.....DLLAAOJGGAAJJGGAAIILBAAC........",
    "..RGGGA....DLBAAOJGAAAJJGAAAIILBAAC........",
    ".RGGGGGA...DAAAAOJJAAAJJJAAAHILBAAC........",
    "RGGGGGGTA..DAAAAOJJJAJJJJJAHHHABAAC........",
    "RGGGGGGTA..DAAOOOJJJJJAAJHHHHHHIAAC........",
    "RGGGGGGTA..DAOOJJJJJJAAAAHHHHHHIIAC........",
    ".AGGGGTTA...EOJJJJJJJAAAAHHHHHIIIE.........",
    "..ATTTRA....YHHVVHHNHHHHHHNHHVVIIE.........",
    "...AACCCD....EHHHHHNNNNNNNNHHIIIE..........",
    ".....DBBBC...YIHHHHNNNNNNNNIIIIIE..........",
    ".....DABBBC...EIIHHHNWWWWNIIIIIE...........",
    "......CCBBBCDDDEEIIIIIIIIIIIIEE............",
    "........CABBBBBCDCBIIIIIIIIBCCD............",
    ".........CCABBBBDBBBBBBBBBBDBBBC.......DD..",
    "...........CCAAADBBBBBBBBBBBDDBBCD....DBAC.",
    ".............CCCAAAAAAAAAAAAAACBADCRR.DBAC.",
    "...............QEEEEEEEEEEEEEECADAGGGADAAC.",
    "..............QKKKKKQKKKKQKKKKSAAGGGGTCAC..",
    "..............QKKKKQXEKKQXEKKKSAGGGGGRAAC..",
    "..............QKKKKQXEKKQXEKKKSEAGGGGRAC...",
    "..............QKKKKKEKKKKEKKKSQBBRRTTTA....",
    "...............ESSQQKKKKKSQQSSECCBBCAA.....",
    ".............PPPECBBESSSSQBBCEPPPCC........",
    "...........PPFFFFPBBCEEEECBBEFFFFEP........",
    ".........PPFFFFFFFEEE....PEEFFFFFFFEP......",
    "........PFFFFFFFFFFMME..PFFFFFFFFFFFME.....",
    "........PFFFFFFFFFFME....EFFFFFFFFFFME.....",
    "........PFFFFFFFFMMME....PMFFFFFFFFMME.....",
    ".........EMMMMMMMMEE......EEMMMMMMMME......",
    "..........EEEEEEEE..........EEEEEEEE.......",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (43, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 43x44).
    scale=int   -> sprite de 43x44 px ampliado por un entero, sin márgenes.
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
