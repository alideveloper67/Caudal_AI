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
    "A": (250, 252, 255),
    "B": (17, 22, 26),
    "C": (198, 210, 234),
    "D": (31, 160, 230),
    "E": (26, 140, 213),
    "F": (20, 120, 196),
    "G": (224, 231, 244),
    "H": (154, 20, 36),
    "I": (10, 74, 138),
    "J": (224, 38, 47),
    "K": (176, 20, 30),
    "L": (42, 42, 58),
    "M": (92, 196, 246),
    "N": (154, 166, 188),
    "O": (246, 200, 28),
    "P": (74, 86, 132),
    "Q": (242, 102, 122),
    "R": (26, 17, 18),
    "S": (106, 10, 16),
    "T": (122, 74, 10),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "................IIIIIIIIIIIII............",
    "..............IIMMMMMMMMMMMMDBI..........",
    "............IIMMMDDDDDDDEEDDDDDBI........",
    "...........IMMMDDDDDDDDDEEEDDDDEEB.......",
    "..........IMMDDEEBBBBDDEEBBBBDDDEEB......",
    ".........IEMDDDEBAAAABDEBAAAABDDEEEB.....",
    "........IEEEDEEEBAAAAABBAAAAAABDEEEFB....",
    ".......IEEEEFEEBAAAAAABBAAAAAABDEEEEFB...",
    ".......IEEEFFFEBAAABBABBAABAAABFEEEEFB...",
    "......IEEEFFFFABAAABBABBABBAAABGCEEEEFB..",
    "......IEEEFFFAABAAABBABBABBAAABGGCEEEFB..",
    ".....IEEEEFFAAAABAAAABAABAAAABGGGCEEEFFB.",
    ".....IEEEFFFAAAAABAABBAABBAABBGGGGLEEFFB.",
    ".....IEEEFFFALLLAABBCCJJJABBAALLLGCEEFFB.",
    ".....IEEEFFAAAAAALACCJAJJKAAAAGGGGCCEFFB.",
    ".....IEEEFFAAAAAAAAACJJJKKAAAAGGGGCCEFFB.",
    ".....IEEEFFALLLLLLAAAKJKKAAAALLLLLLCEFFB.",
    ".....IEEEFFAAAAAAAAAAAABAAAAAGGGGGCCFFFB.",
    ".....IDEEFFAAAAALLAAAAABAAAALLGGGGCCFFFB.",
    "......BEEFFAALLLHHHHHHHHHHHHHHLLLLCCFFB..",
    "......IEEEFAAAAAHHHHHHHHHHHHHHGGGCCCFFB..",
    ".......BEEFGAAAAAHHHHHHHHHHHHHGGGCCCFB...",
    "..PPP..IEEEFGGGGGHHHHQQQQQHHHGGGCCCFFB...",
    ".PAAAB..BEEEGGGGGGHHHQQQQQHHGGGCCCCFB....",
    "PAAAACB..BFFFGGGGGGGHHQQQGGGGCCCCCDB.....",
    "PAAAAPBB..BFFFCCGGGGGGGGGGCCCCCCCDB......",
    "PAAACPBDBI.RJJDCCCCCCCCCCCCCCCCJJKR......",
    ".BCCPBMDDDBSJJJJJJCCCCCCCCCCJJJJJKR......",
    "..BBBMDDDDDRKKJJJJJJJJKKKJJJJJKKKKR......",
    "....BFDDDDDDBBDKKKJJJKKOOOKKKKKBBR..SSSS.",
    ".....BBDDDDDDIDDFFAKKKOOOOOADDBDDB.SJJJKR",
    ".......BFDDDDDBFFAAAACTTTTTAAIDDDDBSJJJKR",
    "........BFDDDFFBAAAAACOOOOOAACBDDDIDKKKKR",
    ".........BBFFFFIAAAAAAOOOOOAAAIDDDIDDBRR.",
    "...........BIIIFAANNNNNNNNNNAACIFIIIB....",
    "...........IDDDFAANAAAAAAAANACCDIBBBAB...",
    "............BDDDAAANAAAAAACNACDDBAAAACB..",
    "............IFFFFAAANAAAACNCCCDDBAAACCB..",
    "............PBBBBBCAANNNNNCCBBBBBACCCB...",
    "...........PAAAAAABBCCCCCBBBAAAAAACBB....",
    "..........PAAAAAAAAABDDDBAAAAAAAACCB.....",
    "..........PCAAAAAACCCBBBBAAAAAAACCB......",
    "...........BBCCCCCCBB....BCCCCCCCB.......",
    ".............BBBBBB.......BBBBBBB........",
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
    render().save("sprite1.png")
    print("Guardado sprite1.png")
