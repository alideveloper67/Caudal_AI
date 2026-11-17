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
    "A": (58, 62, 94),
    "B": (48, 50, 78),
    "C": (37, 39, 62),
    "D": (8, 8, 14),
    "E": (120, 130, 200),
    "F": (142, 224, 90),
    "G": (53, 58, 102),
    "H": (94, 104, 160),
    "I": (35, 38, 74),
    "J": (216, 64, 46),
    "K": (79, 158, 44),
    "L": (12, 14, 20),
    "M": (106, 42, 74),
    "N": (83, 92, 154),
    "O": (26, 6, 6),
    "P": (168, 38, 28),
    "Q": (255, 255, 255),
    "R": (232, 120, 140),
    "S": (90, 18, 12),
    "T": (20, 21, 42),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".EEE..................................EEEE...",
    "EHHAD......E..................E......EHCCCD..",
    "EHAAAD....EADE...............ECD....EHCCCD...",
    "EAAAAAD...EAAAD.............ECCD...EHHCCCD...",
    ".DAAAAAD...DAACDEEEEEEEEEEEEACD...EHHCCCD....",
    ".EAAAAAAD..EEEEHHHHHHHHHHHAEEED..EHHACCCD....",
    "..DAAAAAADEEHHHHAAAAAAAAAAAABBDEEHHACCCD.....",
    "..EAAAAACEHHHAAAAAAAAAAAAAAABBBBEHAACCCD.....",
    "...DAAACEHHAAAAAAAAAAAAAAAAABBBBCEACCCD......",
    "...EAAAEHHAAAAAAAAAAAAAAAAAABBBBBCDCCCD......",
    "....DACEHAAAAAAAAAAAAAAAAAAABBBBBCECED.......",
    ".....DEHHAAAAAAAAAAAAAAAAAAABBBBBBCEDD.......",
    "......DHAAAAAFFFAAAAAAAAAAFFFFBBBBCENGD......",
    "......EHAAAAFFFFFFAAAAAAAFQFLFFBBBCCDGGD.....",
    "......EHAAAFQQLLFFAAAAAAFFQFLFFBBBCCDGGID....",
    ".....EHHAAAFFFLLFFAAAAAAFFFFLFFFBBCCDGGGID...",
    ".....EHAAAAFFFLLFFAAAAABFFFFLFFKBBCCDGGGID...",
    "....EEHAAAAFFFLLFFAABABBKFFFLFFKBBCCDGGGIID..",
    "....EEBAAAAKFFFLFKAAABBBBKFFLFKBBCCCDGGGIID..",
    "....ENDBAAAAKKKKKAAAAABBBBKKKKBBBCCCDGGGIID..",
    "....ENEBBAAAAAAAAAAAAAABBBBBBBBBCCCDNGGIIID..",
    "....EGGDBBAAAAAAAAATAAABBBBBBBCCCCCDGGGIIID..",
    ".....DGGDCBAAAAAAMAAAAAABMBBBCCCCCDNGGIIID...",
    ".....ENGGDCCAAAAAAMMMMMMMMCBCCCCDDNGIIIIID...",
    ".....EIIGGDDCAAAAAAMMRRRMBBCCCCDNGGGIIEED....",
    "......DDDGGGDDAAAAAAAAAABBBBEHDNGGGGIEJJO....",
    "........ENGGIEHAAAAAAAABBBBBBHDGGGGGIEJJJO.S.",
    "........ENGIEHHAAAAAAAABBBBBBCEGGIIIIEJJJJOPO",
    ".......EIIGEHHAAAAAAAABBBBBBBBCDGIIIIIOJJJJPO",
    "........DDDEHAAAAAAAABBBBBBBBBCEIIIDDDSPJJJPO",
    "..........EHHAAABBBBBBBBBBBBBBCCDIID..EDEJJPO",
    "..........EHAAABBBBBBBBBBBBBBBCCDID...EEJJJPO",
    "..........EBAAABBBBBBBBBBBBBBCCCDID...EEJJPPO",
    "..........EBBBBBBBBBBBBBBBBBBCCCDD....EADPPO.",
    "...........DBBBBBBBBBBBBBBBBCCCD.....EAACDD..",
    "...........ECCCBBBBBBBBBBBBCCCCD.....EAACD...",
    ".........EE.DCCCBBBBBBCCCCCCCCDCDE..EAACCD...",
    ".......EEAADECDDDBBBBCCCCCCCCDEEDADEAACCD....",
    "......EAAAAAADAAADBBBCCCDDDDDEDDAAAEDCCD.....",
    ".....EAAAAAAAAAAAADCCCCDAAAAADAAAAAEDCD......",
    ".....EAAAAAAAAAAACCDCCCDAAAAACAAAACEDD.......",
    "......DCCCCCCAAACCD.DDDCAAACCCDCCCCDD........",
    ".......DDDDDDDCCCD.....DDCCCDD.DDDD..........",
    "..............DDD........DDD.................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (45, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 45x44).
    scale=int   -> sprite de 45x44 px ampliado por un entero, sin márgenes.
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
