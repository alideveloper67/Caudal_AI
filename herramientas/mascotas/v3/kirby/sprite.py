#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python kirby.py                 -> guarda kirby.png
      from kirby import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (247, 168, 198),
    "B": (236, 145, 181),
    "C": (232, 54, 78),
    "D": (26, 17, 18),
    "E": (224, 122, 164),
    "F": (168, 58, 104),
    "G": (255, 188, 209),
    "H": (26, 26, 74),
    "I": (184, 28, 58),
    "J": (242, 100, 138),
    "K": (122, 16, 40),
    "L": (58, 98, 224),
    "M": (156, 31, 58),
    "N": (254, 94, 105),
    "O": (255, 255, 255),
    "P": (240, 90, 120),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................FFFFFFFF..................",
    "...............FFFGGGGGGGADFF...............",
    ".............FFGGGGAAAAAAAAGADF.............",
    "............FGGGAAAAAAAAAAAAAABD............",
    "..........FFGGAAAAAAAAAAAAAAAABBDF..........",
    ".........FGGGAAAAAAAAAAAAAAAAABBBED.........",
    ".....FFFFGGAAAAAAAAAAAAAAAAAAABBBBED........",
    "...FFAAFGGAAAAAAAOHAAAAAAOHAAABBBBBD........",
    "..FAAAEFGAAAAAAAHOHHAAAAHOHHAAABBBBED.......",
    ".FAAAAFGGAAAAAAAHHHHAAAAHHHHBBBBBBBBED......",
    ".FAAAEFGAAAAAAAAHHHHAAAAHHHHBBBBBBBBED......",
    "FAAAAFGGAAAAAAAAHLLHAAAAHLLHBBBBBBBBEED.....",
    "FAAAAFGAAAAAAAAAHLLHAAAAHLLHBBBBBBBBEED.....",
    ".DAAAFGAAAAAAAAAAHHAAAAAAHHBBBBBBBBBEED.....",
    "..DEEFGAAAAAAAAAAAAAAAAAAAAABBBBBBBBBED.....",
    "...DDDGAAAAJJJJAAAAAAAAAAAAAAJJJJBEEEED.....",
    "....FAGAAAAJJJJAAAAAAMMAAAAABJJJJEEEEEED....",
    ".....DAAAAAAAAAAAAAAMMMMAAABBBBBEEEEDDDAD...",
    ".....FGAAAAAAAAAAAAAAPPAAAABBBBBBEEDAAAAAD..",
    ".....FGAAAAAAAAAAAAAAAAAAABBBBBBBEFAAAAAAED.",
    ".....FGAAAAAAAAAAAAAAAAABBBBBBBBBBEDAAAAAAD.",
    ".....FAAAAAAAAAAAAAAAAABBBBBBBBBBBBFAAAAAEED",
    "......DBBBAAAAAAAAABBBBBBBBBBBBBBBEEFAAAEED.",
    "......FBBBBBAAAABBBBBBBBBBBBBBBBBEEEEDEEED..",
    ".......DBBBBBBBBBBBBBBBBBBBBBBBBBEEEDDDDD...",
    "........DBBBBBBBBBBBBBBBBBBBBBBBEEED........",
    "........FEBBBBBBBBBBBBBBBBBBBBEEEEED........",
    ".........DEBBBBBBBBBBBBBBBBBBEEEEED.........",
    "..........DDEEEEBBBBBBBBBEEEEEEEDD..........",
    "..........KKDEEEEEBBBBEEEEEEEEEDK...........",
    "........KKCCCDDDDDEEEEEEEEEDDDDNCDKK........",
    ".......KCCCCCCCCCCDDEEEEDDDNCCCCCCNCDK......",
    "......KCCCCCCCCCCCCIDDDDNCCCCCCCCCCCCID.....",
    ".....KCCCCCCCCCCCCIID.KCNCCCCCCCCCCCCCD.....",
    ".....KCCCCCCCCCCCIID...DCCCCCCCCCCCCCIID....",
    ".....KICCCCCCCCIIID....KICCCCCCCCCCCCID.....",
    "......DDIIIIIIIIDD......DDIICCCCCCIIIID.....",
    "........DDDDDDDD..........DDDIIIIIIDDD......",
    ".............................DDDDDD.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (44, 39)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 44x39).
    scale=int   -> sprite de 44x39 px ampliado por un entero, sin márgenes.
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
    render().save("kirby.png")
    print("Guardado kirby.png")
