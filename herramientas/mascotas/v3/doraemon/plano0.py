#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano0.py                 -> guarda plano0.png
      from plano0 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (250, 252, 255),
    "B": (31, 160, 230),
    "C": (250, 252, 254),
    "D": (251, 253, 255),
    "E": (31, 160, 231),
    "F": (21, 21, 31),
    "G": (154, 20, 36),
    "H": (224, 38, 47),
    "I": (42, 42, 58),
    "J": (224, 38, 46),
    "K": (154, 166, 188),
    "L": (246, 200, 28),
    "M": (242, 102, 122),
    "N": (122, 74, 10),
    "O": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......................BBB.....................",
    ".................BBBBBBBBBBBBB................",
    "...............BBBBBBBBBBBBBBBBB..............",
    ".............BBBBBBBBBBBBBBBBBBBBB............",
    "............BBBBBBFFFFBBBBFFFFBBBBB...........",
    "...........BBBBBBFDDDDFBBFDDDDFBBBBB..........",
    "..........BBBBBBBFDDDDDFFDDDDDDFBBBBB.........",
    ".........BBBBBBBFDDDDDDFFDDDDDDFBBBBBB........",
    ".........BBBBBBBFDDDFFDFFDDFDDDFBBBBBB........",
    "........BBBBBBBAFDDDFFDFFDFFDDDFAABBBBB.......",
    "........BBBBBBAAFDDDFFDFFDFFDDDFAAABBBB.......",
    ".......BBBBBBAAAAFDDDDFAAFDDDDFAAAABBBBB......",
    ".......BBBBBBAAAAAFDDFFAAFFDDFFAAAAIBBBB......",
    ".......BBBBBBAIIIAAFFAAJJJAFFAAIIIAABBBB......",
    ".......BBBBBAAAAAAIAAAJOJJJAAAAAAAAAABBB......",
    ".......BBBBBAAAAAAAAAAJJJJJAAAAAAAAAABBB......",
    ".......BBBBBAIIIIIIAAAJJJJAAAAIIIIIIABBB......",
    ".......BBBBBAAAAAAAAAAAAFAAAAAAAAAAAABBB......",
    ".......BBBBBAAAAAIIAAAAAFAAAAIIAAAAAABBB......",
    "........BBBBAAIIIGGGGGGGGGGGGGGIIIIAABB.......",
    "........BBBBAAAAAGGGGGGGGGGGGGGAAAAAABB.......",
    ".........BBBAAAAAAGGGGGGGGGGGGGAAAAAAB........",
    ".........BBBBAAAAAGGGGMMMMMGGGAAAAAABB........",
    "..........BBBAAAAAAGGGMMMMMGGAAAAAAAB.........",
    "...........BBBAAAAAAAGGMMMAAAAAAAAAB..........",
    "............BBBAAAAAAAAAAAAAAAAAAAB...........",
    ".............HHBAAAAAAAAAAAAAAAAHHH...........",
    "....CCC......HHHHHHAAAAAAAAAAHHHHHH...........",
    "...CCCCC.....HHHHHHHHHHHHHHHHHHHHHH...........",
    "...CCCCCEE.....BHHHHHHHHLLHHHHHHE.............",
    "...CCCCCEEEEE.BBBBBAHHLLLLLLABBEEE............",
    "...CCCCEEEEEEEEEBBAAAALNNNNLAAEEEEE...JJ......",
    "......EEEEEEEEEEEAAAAALLLLLLAAAEEEEE.JJJJ.....",
    ".........EEEEEEEEAAAAAALLLLAAAAEEEEEEJJJJ.....",
    "............EEEEBAAKKKKKKKKKKAAAEEEEEBJJ......",
    ".............BBBBAAKAAAAAAAAKAAABECCCC........",
    "..............BBBAAAKAAAAAAAKAABBCCCCCC.......",
    "..............CCCCCAKKAAAAAKCCCCBCCCCCC.......",
    ".............CCCCCCCCCKKKKCCCCCCCCCCCC........",
    "............CCCCCCCCCCAAACCCCCCCCCCC..........",
    "............CCCCCCCCCCBBBCCCCCCCCCC...........",
    "..............CCCCCC.......CCCCCCC............",
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
    render().save("plano0.png")
    print("Guardado plano0.png")
