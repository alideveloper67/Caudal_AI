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
    "B": (228, 226, 244),
    "C": (205, 200, 234),
    "D": (58, 120, 216),
    "E": (43, 37, 64),
    "F": (232, 32, 58),
    "G": (58, 52, 80),
    "H": (119, 112, 158),
    "I": (12, 20, 48),
    "J": (138, 90, 16),
    "K": (22, 48, 112),
    "L": (39, 82, 171),
    "M": (179, 18, 47),
    "N": (27, 20, 38),
    "O": (122, 12, 34),
    "P": (246, 210, 58),
    "Q": (58, 6, 16),
    "R": (58, 34, 8),
    "S": (255, 90, 108),
    "T": (249, 168, 192),
    "U": (246, 194, 28),
    "V": (106, 160, 240),
    "W": (217, 160, 32),
    "X": (255, 194, 204),
    "Y": (223, 232, 255),
    "Z": (255, 229, 138),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......HHH...................OOOO..OOOOOO...",
    ".....HAAAEHH..............OOSSSFQOFFFFFFQ..",
    "....HAAAAAAAEH..HHHHHHHHHOSSSFFFMAFFFFFFFQ.",
    "....HAAAAAAAAAEHAAAAAABCCSSXFFMMMQFFXFFFFMQ",
    "....HAAAAAAAAAAAAAAAAAACCSFFFFMQQFQFFFFFFMQ",
    "....HAAAAAAAAAAAAAAAAAAACSFFFFMQFFFQFFFFFMQ",
    "....HAAAAAAAAAAAAAAAAAAAAFFFFFFOFFMOFFFFMMQ",
    "...HAAAAAAAAAAAAAAAAAAAAAAMFMMMMOOOBMMMMMQ.",
    "...HAAAAAAAAAAAAAAAAAAAAAAAAMAAABBBBBCCEQ..",
    "...HAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBCCE...",
    "...HAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBCCE...",
    "...HAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBCCE...",
    "...HAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBCE...",
    "...HAAAAAAAANNNAAAAAAAAANNNAABBBBBBBBCCE...",
    "GGGHAAAAAAAAYNNAAAAAAAAAYNNABBBBBBBBBCCCGGG",
    "...GGGGGAAAANNNAAAAAAAAANNNBBBBBBBBGGGGG...",
    "...HAAAAAAAANNNAAAAAAAAANNNBBBBBBBBBCCCE...",
    "...HBBBAAAAAAAAAAAAAAABBBBBBBBBBBBBCCCCE...",
    "GGGGGGGGBBBBBBBBBBUUUBBBBBBBBBBBBBCGGGGGGGG",
    ".....EBTTTTBBBBBBBUUUBBBBBBBTTTTBCCCCE.....",
    "......EBBBBBBBBBBBBBBBBBBBBBBBBBCCCCE......",
    "...GGGGGCBBBBBBBBBBBBBBBBBBBBBCCCCCGGGGG...",
    "GGG.....ECCCBBBBBBBBBBBBBBBCCCCCCCE.....GGG",
    ".........EECCCCCCCCCCCCCCCCCCCCCEE.........",
    "...........EEECCCCCCCCCCCCCCCEEE...........",
    "..............IIIJRRRRRRRJIII..............",
    "............JJKKDIJJJJJJJILKIJJ............",
    "...........JPPPRIKIIIIIIIKKRPPPR...........",
    "..........JPPPPJKZIDDDDDKZKRPPPWR..........",
    "..........JJPPWJIIDDDDDDDIKJPPWJR..........",
    ".........HAEJJJIVDDDDDDDDDDIJJJEAE.........",
    "........HAAAEHIVDDDDDDDDDDDDIHEAACE........",
    "........HAACHIVDDDDDDDDDDDDDDIHAACE........",
    "........HAAHIVDDDDDDDDDDDDDDDLIEACE........",
    "........HCCHIDDDDDDDDDDDDDDDDLKECCE........",
    ".........EEIVDLLDDDLDDDLLDDDLLLIEE.........",
    "...........KLLLLKKLLLLLLLKKLLLLI...........",
    "............IKKKEEKKKILKKEEKKKI............",
    "............HEEEAAEEEEEEEAAEEEE............",
    "...........HAAAAAAAACEAAAAAAAACE...........",
    "...........HCAAAAACCCEEAAAAAACCE...........",
    "............EECCCCCEE..ECCCCCCE............",
    "..............EEEEE.....EEEEEE.............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (43, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 43x43).
    scale=int   -> sprite de 43x43 px ampliado por un entero, sin márgenes.
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
