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
    "A": (246, 248, 255),
    "B": (194, 203, 236),
    "C": (38, 40, 74),
    "D": (122, 74, 36),
    "E": (26, 14, 6),
    "F": (220, 226, 246),
    "G": (122, 127, 174),
    "H": (255, 255, 255),
    "I": (58, 32, 12),
    "J": (60, 42, 58),
    "K": (26, 26, 38),
    "L": (255, 138, 30),
    "M": (58, 42, 34),
    "N": (42, 42, 52),
    "O": (255, 194, 204),
    "P": (224, 90, 16),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................II......................",
    "..............IIIIDDE....I................",
    ".............IDDDEEDDE..IDE...............",
    "..............EEDDEEDE.IDE................",
    "................EDDEDEIDDE................",
    "................GEDAHAHDEG................",
    "..............GGHHHAAAAAAFCG..............",
    ".............GHFFMMAAAAMAFFFC.............",
    "............GHHMMMFFFFAAMMMFBC............",
    "...........GHHAAFFFFFFFFAAFFBBC...........",
    "...........GHAAAHKBBBFFHHKAFBBC...........",
    "...........GHAAAKKKBBBBKKKAFBBC...........",
    "...........GHAAAKKKBLLLKKKBFFBC...........",
    "...........GHAAAKKAALLLLLLLBFFC...........",
    "..I........GHOOAAAAAAPPPPPPLLOBC..........",
    ".IDE.......GHOOAAAAAAAFFFFFFOOBBC.........",
    "..EDE......GFFFFFFFFFFFFFJFFFBBBC.........",
    ".IIDE......GBFFFFJJJHHHJJJFBBBBBC.........",
    "IDDDDEI.....CBBFFJJJJHJJJJBBBBBC..........",
    ".EEEDDDE.....CCBBBJJJJJJJBBBBCC...........",
    "....EEDDEI.....CABBBJJJBBBBCC.............",
    "....IDEEDDEI..GHHAHHHAAAHHBC..............",
    "...IDE..EDDDEGHHAAAANNAAAABBC.............",
    "....E....EEDDDHAAAAANNAAAAABC..........II.",
    "...........EEDAAAAAAAAAAAAAAC........IIDDE",
    ".............CAAAAAAAAAAABBBACI....IIDDEE.",
    ".............GAAAAAANNAABBBBDDDEIIIDDDE...",
    "..............CAAAAAAAABBBBCEEDDDDDDDEI...",
    ".............GGCBBBBBBBBBBCCG.EEEEEEEDDE..",
    "............GHHHCBBBBBBBBCHAAC.......EE...",
    "...........GHHAAACCCCCCCCHAAABC...........",
    "..........GHHAAAAAAAAAAAAAAAAABC..........",
    "..........GHAAAAAAAAAAAAAAAAAABC..........",
    ".........GHHAAAAAAAAGGAAAAAAABBBC.........",
    ".........GAAAAAAAAAGNNCAAAAAABBBC.........",
    "..........CAAAAAAAAACCAAAAAABBBC..........",
    "..........GAAAAAAAAAAAAAAAABBBBC..........",
    "...........CGAAAAAAAAAAAABBBBGC...........",
    "..........GGCGGBAAAAAABBBBBGGCCG..........",
    ".........GAAACCGGGBBBBBBGGGCCAABC.........",
    ".........GAAAAACCCCBBBBGCCCAAABBC.........",
    "..........CBAAABBBCCCCCCBAAABBBC..........",
    "...........CCBBBCC......CCBBBCC...........",
    ".............CCC..........CCC.............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (42, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 42x44).
    scale=int   -> sprite de 42x44 px ampliado por un entero, sin márgenes.
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
