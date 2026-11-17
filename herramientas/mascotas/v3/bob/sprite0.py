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
    "A": (255, 255, 254),
    "B": (253, 226, 74),
    "C": (242, 210, 59),
    "D": (26, 24, 17),
    "E": (230, 193, 44),
    "F": (154, 116, 16),
    "G": (154, 92, 38),
    "H": (20, 20, 30),
    "I": (61, 155, 224),
    "J": (255, 242, 107),
    "K": (38, 34, 44),
    "L": (122, 66, 24),
    "M": (124, 26, 36),
    "N": (201, 184, 46),
    "O": (246, 144, 122),
    "P": (106, 12, 28),
    "Q": (163, 170, 204),
    "R": (224, 48, 60),
    "S": (138, 140, 176),
    "T": (10, 8, 12),
    "U": (242, 106, 120),
    "V": (74, 36, 12),
    "W": (101, 103, 140),
    "X": (176, 28, 48),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...........FFFF...........FFFF.............",
    ".......FFFFJJJBDFFFFFFFFFFJJJBDFFFF........",
    "......FJJJJJBBBBJJJJJJJJJJJBBBCCCCED.......",
    ".....FJJBBBBBBBBBBBBBBBBBBBBBCCCCCEED......",
    ".....FJBBNBBBBBBBBBBBBBBBBBBCCCCNCEED......",
    ".....FJBNNNHBBBBBBHBBHBBBHBBCHCNNNEED......",
    ".....FJBBNNHHBBHBHHBBBHBBHBBHCCCCCCED......",
    ".....FJBBBBBHAAAAHBBBBBAAHAACCCCCCCED......",
    ".....FJBBBBAAAAAAAABBBAAAAAAACCCCCEEED.....",
    ".....FJBBBBAAAIIIAABBAAAIIIAAACCCEEEEDFF...",
    "....FJJBBBAAAIAIIIAABAAIAIIIAACCCEEEDFBBD..",
    "....FBBBBBAAAIAHHIAABAAIAHHIIACCCEEDFBBBBD.",
    ".....DBBBBAAAIHHHIAABAAIIHHIIACCCEEDFBBBBED",
    "......DBBBBAAIIHHIAEEAAIIHHIIACNNNEDFBBBEED",
    "......FJBBBAAAIIIAAEEAAAIIIIACCCNNEDFBBEED.",
    "......FJBBBBAAAAAAEEDDDAAAAAACCCCEED.DBED..",
    "......FJBCOBBAAAABCFBBFJAAABBCCOCEED.FBED..",
    "......FCOOOOOCCCCCCCFFFCCCCCBOOOOOED.FBED..",
    "......FCCOOOMMMCCCCCCCCCCCMMMCOOOCED.FEED..",
    "......FCCCCCCMMMMMAAAAAMMMMMCCCCCEEEDBED...",
    "......FCCCCCCCMMMMAAAAAMMMMCCCCCCCEEDBED...",
    ".....FCCNNCCCCECMMUUUUUMMCCCCCCNCCEDFEED...",
    ".....FEENNNEEEEEEEEUUEEEEEEEEENNECEEDED....",
    ".....FEEEEEEEEEESEEEEEEEESEEEEENEEEEDED....",
    ".....FEAAAAAAAAAASSSDDSSSAAAAAAAAAQEDD.....",
    ".....FEAAAAAAAAAAAQDRRDAAAAAAAAAAAQED......",
    "....FFEAAAAAAAAAAAQDRRPAAAAAAAAAAAQED......",
    "....FBDAAAAAAAAAAAQDRRPAAAAAAAAAAAQD.......",
    "...FBEFDDDQQDDDQQDDDRRPDDDQQDDDQQDDD.......",
    "..FBEEDGGGGGGGGGGGLDRRPGGGGGGGGGGGLD.......",
    "..FBEDVGGGGGGGGGGGGPRXPGGGGGGGGGGGLD.......",
    "..FBEDVGGGGGGGGGGGGGPPGGGGGGGGGGGLLD.......",
    ".FBBBD.DLLLGGGLLLLLLLLLLLLGGGLLLLLD........",
    "FBBBBED.DDDDLLLDDDDDDDDDDDDLLLDDDD.........",
    ".DBEEED....FDDDD..........FDDDD............",
    "..DEDD.....FBBED..........FBBED............",
    "...D.......FFFFD..........FFFFD............",
    "...........WAAAD..........WAAAD............",
    "..........TPPPPD.........TPPPPD............",
    ".........TKKKKKKH.......TKKKKKKH...........",
    "........TKKKKKKKHH.....TKKKKKKKHH..........",
    "........TKKKKKHHHH.....TKKKKKHHHH..........",
    ".........HHHHHHHH.......HHHHHHHH...........",
    "..........HHHHH..........HHHHH.............",
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
    render().save("sprite0.png")
    print("Guardado sprite0.png")
