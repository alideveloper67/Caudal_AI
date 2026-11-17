#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python plano_0.py                 -> guarda plano_0.png
      from plano_0 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (252, 217, 58),
    "B": (47, 111, 184),
    "C": (174, 182, 194),
    "D": (38, 36, 44),
    "E": (255, 255, 254),
    "F": (252, 217, 59),
    "G": (74, 136, 208),
    "H": (42, 42, 50),
    "I": (138, 84, 40),
    "J": (90, 30, 24),
    "K": (28, 26, 32),
    "L": (255, 255, 252),
    "M": (20, 20, 26),
    "N": (20, 16, 26),
    "O": (238, 106, 106),
    "P": (212, 236, 255),
    "Q": (255, 255, 253),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................KK...K..KK..................",
    "...................KKAAKAKK...................",
    ".................AAAKAAAAKAAA.................",
    "...............AAAAAAAAAAAAAAAA...............",
    "..............AAAAAAAAAAAAAAAAAA..............",
    ".............AAAAAAAAAAAAAAAAAAAA.............",
    "............AAAAAAAAAAAAAAAAAAAAAA............",
    "............AAAACCCCAAAAAACCCCAAAA............",
    "...........AAAACCCCCCCAACCCCCCCAAAA...........",
    "...........AAACCCEEECCAACCPEEECCAAA...........",
    "..........AAACCEPEEEECCCCEEEEEECCAAA...DDD....",
    "..........HHHCCEEQIIECCCCPEQIIECCHHH..DDDDD...",
    "..........HHHCCEEINIICCCCEEINIECCHHH..DDDDD...",
    "..........HHHCCEEINIECCCCEEINIECCHHH..DDDDD...",
    "..........AAACCCEEIIECCCCEEIIICCCAAA...DDD....",
    "..........AAAACCCEECCCAACCCEECCCAAAA...FF.....",
    "..........AAAAACCCCCCAAAACCCCCCAAAAA...FF.....",
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAA...FF.....",
    "..........AAAAAAAAAAAAAAAAAAAAAAAAAA...FF.....",
    "..........BAAAAAAAAAAAAAAAAAAAAAAAAB..FFF.....",
    ".........BBBBBAAAAAJLLLLLLJAAAAABBBBB.FF......",
    "..........ABBBBAAAAJJJJJJJJAAAABBBBA.FFF......",
    "..........AAABBBAAAAJJOOJJAAAABBBAAAFFF.......",
    "..........AAAAABBBBBBBOOBBBBBBBAAAAAFF........",
    "..........AAAAAAMBBBGGGGGGBBBMBAAAAAF.........",
    ".........FAAAAAABBBBGGMMGGBBBBAAAAAA..........",
    "........FFAAAAABBBBBGGMMGGBBBBBAAAAA..........",
    ".......FFFAAABBBBBBBGGGGGGBBBBBBBAAA..........",
    "......FFF.BBBBBBBBBBBBBBBBBBBBBBBBBB..........",
    "......FF..BBBBBBBBBBBBBBBBBBBBBBBBBB..........",
    "......FF..BBBBBBBBBBBBBBBBBBBBBBBBBB..........",
    ".....DDD..BBBBBBBBBBBBBBBBBBBBBBBBBB..........",
    "....DDDDD..BBBBBBBBBBBBBBBBBBBBBBBB...........",
    "....DDDDD..BBBBBBBBBBBBBBBBBBBBBBBB...........",
    ".....DDD.....BBBBBBBBBBBBBBBBBBBB.............",
    "...............BBBBBBBBBBBBBBBB...............",
    "...............BBBBBB....BBBBBB...............",
    "...............BBBBB......BBBBB...............",
    "..............DDDDDB......BDDDDD..............",
    ".............DDDDDDDD.....DDDDDDD.............",
    ".............DDDDDDDD.....DDDDDDD.............",
    "..............DDDDD........DDDDD..............",
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
    render().save("plano_0.png")
    print("Guardado plano_0.png")
