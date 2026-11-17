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
    "A": (252, 217, 58),
    "B": (17, 20, 26),
    "C": (226, 180, 30),
    "D": (41, 98, 164),
    "E": (47, 111, 184),
    "F": (35, 84, 144),
    "G": (255, 255, 254),
    "H": (38, 36, 44),
    "I": (174, 182, 194),
    "J": (18, 42, 82),
    "K": (148, 106, 12),
    "L": (255, 237, 94),
    "M": (26, 23, 17),
    "N": (132, 140, 156),
    "O": (10, 8, 12),
    "P": (74, 136, 208),
    "Q": (228, 234, 242),
    "R": (42, 42, 50),
    "S": (138, 84, 40),
    "T": (90, 30, 24),
    "U": (28, 26, 32),
    "V": (238, 106, 106),
    "W": (212, 236, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...............OO...O..OO................",
    "..............OUUBKOUBOUUB...............",
    "..............KBUULLUAUUBK...............",
    "............KKLLLUAAAAUAAAMK.............",
    "...........KLLLAAAAAAAAAAAAAM............",
    "..........KLLAAAAAAAAAAAAAAAAM...........",
    ".........KLCCCCAAAAAACCCCAAAACM..........",
    "........KLCCCCCCCAACCCCCCCAAAACM.........",
    "........KCCCCQQQICACCCCQQQIAAACM.........",
    ".......KCCCCQQIIIINCCQQQIIIIAAACM........",
    ".......KCCCQQIGGGIICCQIWGGGIIAACM...OOO..",
    "......KLCCQQGWGGGGIIQQGGGGGGIIACCM.OHHHB.",
    "......BRRRQIGGGSSGIIIIWGGSSGIIRRRBOHHHHBB",
    "......BRRRIIGGSBSSIIIIGGSBSGNNRRRBOHHHHBB",
    "......BRRRIIGGSBSGNIIIGGSBSGNNRRRBOHHHBBB",
    "......KLAAIIIGGSSGNNIIGGSSSNNNLACM.BOOBB.",
    "......KLAAANNNGGNNNLANNNGGNNNLLACM.KMMM..",
    "......KLAAAANNNNNNLLAANNNNNNLLAACM.KACM..",
    "......KLAAAAALLLLLLAAAALLLLLLAAACM.KACM..",
    "......KAAAAAAAAAAAAAAAAAAAAAAAACCM.KACM..",
    "......JBCCAAAAAAAAAAAAAAAAAACCCCBBKACCM..",
    ".....JFJBBBAAAAATGGGGGGTAAACCBBBJFMACM...",
    "......MAJJEBAAAATTTTTTTTAACCBFJJCMACCM...",
    "......KAAAJJBCCCCTTVVTTCCCCBJJAACMCCM....",
    "......KAAAAAJJBBBJJVVJJBBBJJAAAACMCM.....",
    "......KAAAAACBBEJPPPPPPBEJBJAAAACMM......",
    ".....KKAAAACCBEEJPPBBPPBEEBAAAAACM.......",
    "....KAKAACCCBPEEJPPBBPPBEEDBCAAACM.......",
    "...KACKCCCBBPEEEJPPPPPPBEEDDBBCCCM.......",
    "..KACCBBBBPEEEEEEBBBBBBEDDDDDDBBBB.......",
    "..KACMJPEEEEEEEEEEEEEEDDDDDDDDDFFB.......",
    "..KKKMJPEEEEDDDDEEEEEEDDDDDDDDFFFB.......",
    ".OHBBBJDEEEDDDDDDEEEEEDDDDDDDDFFFB.......",
    "OHHHHBBBDDEDDDDDDDDDDDDDDDDDFFFFB........",
    "OHHHBBBJFFDDDDDDDDDDDDDDDDFFFFFFB........",
    ".BBBBB..BBFDDDDDFFFFDDDDDDFFFFBB.........",
    "..BBB.....BBDDDFFFFFFDDDDDFFBB...........",
    "...........JFFDFFFBBBBFFFFFFB............",
    "...........JJJJJFB....BFJJJJB............",
    "..........OHBBBBJB....JJBBBBHB...........",
    ".........OHHHHHHBBB...OBHHHHHBB..........",
    ".........OHHHHHBBBB...OHHHHHBBB..........",
    "..........BBBBBBBB.....BBBBBBB...........",
    "...........BBBBB........BBBBB............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (41, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 41x44).
    scale=int   -> sprite de 41x44 px ampliado por un entero, sin márgenes.
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
