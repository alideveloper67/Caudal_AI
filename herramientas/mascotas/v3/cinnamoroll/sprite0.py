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
    "B": (229, 230, 248),
    "C": (207, 210, 240),
    "D": (35, 42, 74),
    "E": (125, 132, 184),
    "F": (168, 200, 240),
    "G": (214, 236, 255),
    "H": (92, 130, 192),
    "I": (28, 42, 82),
    "J": (240, 248, 255),
    "K": (29, 42, 107),
    "L": (79, 142, 240),
    "M": (255, 163, 196),
    "N": (163, 176, 230),
    "O": (106, 63, 110),
    "P": (230, 240, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................EEEEEEEEE..................",
    "...............EEEAAAAAAAAADEE...............",
    "..............EAAAAAAAAAAAAAABD..............",
    ".........HHHEEAAAAAAAAAAAAAAAABDEHHH.........",
    ".......HHFFHAAAAAAAAAAAAAAAAAABBBHJGIH.......",
    ".....HHJFFHAAAAAAAAAAAAAAAAAAABBBCHGGGIH.....",
    "....HJJFFHAAAAAAAAAAAAAAAAAAAABBBBCIGGGFI....",
    "...HJJGFFHAAAAAAAAAAAAAAAAAAABBBBBCHGGGGFI...",
    "...HJGFFHAAAAAAAAAAAAAAAAAAAABBBBBBCIGGGFI...",
    "..HJJGFFHAAAAAAAAAAAAAAAAAAAABBBBBBCHGGGGFI..",
    "..HJGGFHAAAAAAAAAAAAAAAAAAAABBBBBBBCCIGGGFI..",
    ".HJJGGFHAAAAAAAAAAAAAAAAAAAABBBBBBBCCIGGGFFI.",
    ".HJGGFFHAAAAAAAAAKAAAAAAAAAKBBBBBBCCCIGGGFFI.",
    ".HJGFFFHAAAAAAAAPKKAAAAAAAPKKBBBBBCCCIGGGFFI.",
    ".HJGFFFIDAAAAAAAKKKAAAAABBKKKBBBBBCCDIGGGGFI.",
    ".HJGFFI.EAAAAAAALLLAAABBBBLLLBBBBCCCD.IGGGFI.",
    "HJJFFFI.EBBBAAAALLLBBBBBBBLLLBBBBCCCD.HJGFFFI",
    "HGFFFFI..DBBBBBBBBBBBBBBBBBBBBBBCCCD..HGGFFFI",
    ".IFFFI...EBMMMMBBBBBBOBOBBBBBBMMMMCD...IFFFI.",
    ".HFFI.....DCBBBBBBBBBBOBBBBBBCCCCCD.....IFFI.",
    "..II.......DCCBBBBBBBBBBBBBCCCCCCD.......II..",
    "............DDCCCBBBBBBBCCCCCCCDD............",
    "..............DDCCCCCCCCCCCCCDD..............",
    "................DDDCCCCCCCDDD................",
    "................EEADDDDDDDADE................",
    "...............EAAAAAAAAAACCCD...............",
    "..............EEEAAAAAAAAACCEDD..............",
    ".............EAADDAAAAAAAACEDAAD.EEE.........",
    "............EAAAEDAAAAAAAAAEDAAADAAADE.......",
    "............EAACEDAAAAAAAAAEEAAAAAAAACD......",
    ".............DEEDAAAAAAAAAAADEEAAAANNCD......",
    ".............EDDAAAAAAAAAAAACDDDAANAAND......",
    ".............EAAAAAAAAAAAAACCCEDAANANCD......",
    "..............DAAAAAAAAAAACCCCDDAAANCD.......",
    "...............DECAAAAACCCCCED..DCCCD........",
    "..............EADEEECCCCCEEEDAD..DDD.........",
    ".............EAAADDDECCCEDDDAACD.............",
    ".............EAAAAACDDDDDAAAACCD.............",
    "..............DCCCCCD...DCCCCCD..............",
    "...............DDDDD.....DDDDD...............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (45, 40)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 45x40).
    scale=int   -> sprite de 45x40 px ampliado por un entero, sin márgenes.
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
