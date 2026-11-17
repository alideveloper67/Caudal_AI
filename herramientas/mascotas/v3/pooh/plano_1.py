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
    "A": (245, 181, 46),
    "B": (245, 181, 47),
    "C": (216, 35, 46),
    "D": (184, 105, 44),
    "E": (251, 211, 106),
    "F": (216, 35, 47),
    "G": (244, 228, 180),
    "H": (245, 162, 16),
    "I": (22, 16, 12),
    "J": (244, 138, 114),
    "K": (216, 138, 26),
    "L": (28, 20, 16),
    "M": (122, 52, 16),
    "N": (138, 74, 22),
    "O": (184, 105, 45),
    "P": (255, 255, 253),
    "Q": (138, 74, 28),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................",
    "..............................................",
    "........AAAAA...............AAAAA.............",
    "........AAAAAA....AAAAAA....AAAAAA............",
    ".......AAAKKAAAAAAAAAAAAAAAAAKKKAA............",
    ".......AAKKKAAAAAAAAAAAAAAAAAKKKAA............",
    "........AAKAAAAAAAAAAAAAAAAAAAAAA.............",
    "........AAAAAAAAAAAAAAAAAAAAAAAA..............",
    "..........AAAANNNAAAAAAAANNAAAAA..............",
    ".........AAAAAAAAAAAAAAAAAAAAAAA..............",
    ".........AAAAAAAIAAAAAAAAIAAAAAAA.............",
    ".....B..AAAAAAAPPIAAAAAAAPIAAAAAA.............",
    "...BBBB.AAAAAAAIIIAAAAAAIIIAAAAAA.............",
    "...BBBBBAAAAAAAIIIAAAAAAAIIAAAAAA.............",
    "...BBBBBAAAAAAAAAAEEELLEEEAAAAAAA.............",
    "...BBBBBAAAAAAAAAEEELLLLEEEAAAAAA.............",
    "....BBB.AAAJJJJAAEEEELLEEEEJJJJAA.............",
    "....BBB..AAJJJAAEEEEEEEEEEEEJJJA..............",
    "....BBBB.AAAAAAAAEEMEEEEMEEAAAAA..............",
    ".....BBB..AAAAAAAEEEMMMMEEEAAAA...............",
    ".....BBBB..AAAAAAAAEEEEEEAAAAA................",
    "......BBBB..AAAAAAAAAAAAAAAAA.................",
    "......BBBBBCCCAAAAAAAAAAAAACCCC...............",
    ".......BBBCCCCCCCAAAAAAACCCCBBCC..............",
    "........BCCCCCCCCCCCCCCCCCCBBBBB..............",
    ".........CCCCCCCCCCCCCCCCCCCBBBBB..HHH........",
    ".........CCCCCCCCCCCCCCCCCCCCBBBBBHHHHHHH.....",
    ".........CCCCCCCCCCCCCCCCCCCCCBBBBBHHHHHHO....",
    "........FFFFFFFFFFFCCCCFFFFFFFFBBBBBOOHHOO....",
    "..........FFFFFFFFFFFFFFFFFFFFFBBBBBBDHHDD....",
    "..........AAAAAAAAFFFFFFAAAAAAABBBBBDDHDDDD...",
    "..........AAAAAAAAAAAAAAAAAAAAADDBBGGGGGDDD...",
    "..........AAAAAAAAAAAAAAAAAAAADDDGGGGGGGGDD...",
    "..........AAAAAAAAAAAAAAAAAAAADDDGQGQGQGGDD...",
    "...........AAAAAAAAAAAAAAAAAAADDDGGGGGGGGDD...",
    "...........AAAAAAAAAAAAAAAAAAADDDDDDDDDDDDD...",
    "............AAAAAAAAAAAAAAAAAB.DDDDDDDDDDDD...",
    "...........BBBAAAAAAAAAAAAAABBBDDDDDDDDDDD....",
    "..........BBBBBAAAAAAAAAAABBBBBBDDDDDDDDD.....",
    "..........BBBBBBBBBAAAABBBBBBBBB..DDDDDD......",
    "..........BBBBBBBB.....BBBBBBBB...............",
    "............BBBB.........BBBBB................",
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
