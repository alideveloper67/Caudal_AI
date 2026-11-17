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
    "A": (253, 226, 74),
    "B": (255, 255, 255),
    "C": (154, 92, 38),
    "D": (255, 255, 254),
    "E": (253, 226, 75),
    "F": (38, 34, 44),
    "G": (61, 155, 224),
    "H": (224, 48, 60),
    "I": (20, 20, 30),
    "J": (124, 26, 36),
    "K": (201, 184, 46),
    "L": (246, 144, 122),
    "M": (30, 22, 20),
    "N": (253, 226, 76),
    "O": (255, 255, 252),
    "P": (255, 255, 250),
    "Q": (242, 106, 120),
    "R": (255, 255, 253),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................",
    ".............AAAA...........AAAA..............",
    ".........AAAAAAAAAAAAAAAAAAAAAAAAAAAA.........",
    "........AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA........",
    "........AAAKAAAAAAAAAAAAAAAAAAAAAAKAAA........",
    "........AAKKKIAAAAAAIAAIAAAIAAAIAKKKAA........",
    "........AAAKKIIAAIAIIAAAIAAIAAIAAAAAAA........",
    "........AAAAAAIDDDDIAAAAADDIDDAAAAAAAA........",
    "........AAAAADDDDDDDDAAADDDDDDDAAAAAAAA.......",
    "........AAAAADDDGGGDDAADDDGGGDDDAAAAAAA.......",
    ".......AAAAADDDGRGGGDDADDGRGGGDDAAAAAA..EE....",
    ".......AAAAADDDGRIIGDDADDGRIIGGDAAAAA..EEEE...",
    "........AAAADDDGIIIGDDADDGGIIGGDAAAAA..EEEEE..",
    ".........AAAADDGGIIGDAADDGGIIGGDAKKKA..EEEEE..",
    ".........AAAADDDGGGDDAADDDGGGGDAAAKKA..EEEE...",
    ".........AAAAADDDDDDAANNNDDDDDDAAAAAA...EE....",
    ".........AAALAADDDDAANNNNADDDAAAALAAA...EE....",
    ".........ALLLLLAAAAAAANNNAAAAAALLLLLA...EE....",
    ".........AALLLJJJAAAAAAAAAAAJJJALLLAA...EE....",
    ".........AAAAAAJJJJJOOOOOJJJJJAAAAAAAA.EEE....",
    ".........AAAAAAAJJJJOOOOOJJJJAAAAAAAAA.EE.....",
    "........AAKKAAAAAAJJQQQQQJJAAAAAAKAAA.EEE.....",
    "........AAKKKAAAAAAAAQQAAAAAAAAAKKAAAAEE......",
    "........AAAAAAAAAAPAAAAAAAAPAAAAAKAAAAE.......",
    "........ABBBBBBBBBBPPPHHPPPBBBBBBBBBBA........",
    "........ABBBBBBBBBBBBHHHHBBBBBBBBBBBBA........",
    "........ABBBBBBBBBBBBHHHHBBBBBBBBBBBBA........",
    ".......EEBBBBBBBBBBBBHHHHBBBBBBBBBBBB.........",
    "......EEEMMMBBMMMBBMMHHHHMMMBBMMMBBMM.........",
    ".....EEE.CCCCCCCCCCCCHHHHCCCCCCCCCCCC.........",
    ".....EE..CCCCCCCCCCCCHHHHCCCCCCCCCCCC.........",
    "....EEE..CCCCCCCCCCCCCHHCCCCCCCCCCCCC.........",
    "...EEEEE..CCCCCCCCCCCCCCCCCCCCCCCCCC..........",
    "....EEEE......CCC............CCC..............",
    ".....E........EEE............EEE..............",
    "..............EEE............EEE..............",
    "..............BBB............BBB..............",
    "..............HHH............HHH..............",
    "............FFFFFF.........FFFFFF.............",
    "...........FFFFFFFF.......FFFFFFFF............",
    "...........FFFFFFFF.......FFFFFFFF............",
    "............FFFFF..........FFFFF..............",
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
