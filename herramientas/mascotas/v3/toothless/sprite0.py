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
    "A": (58, 62, 94),
    "B": (48, 50, 78),
    "C": (8, 8, 14),
    "D": (37, 39, 62),
    "E": (120, 130, 200),
    "F": (142, 224, 90),
    "G": (94, 104, 160),
    "H": (53, 58, 102),
    "I": (35, 38, 74),
    "J": (216, 64, 46),
    "K": (79, 158, 44),
    "L": (12, 14, 20),
    "M": (106, 42, 74),
    "N": (26, 6, 6),
    "O": (83, 92, 154),
    "P": (168, 38, 28),
    "Q": (255, 255, 255),
    "R": (90, 18, 12),
    "S": (232, 120, 140),
    "T": (20, 21, 42),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".E......................................EE...",
    "EACE.......EE.................E.......EEDDC..",
    "EGAAC.....EAAC..............EEDC.....EGGDC...",
    "EGAAACE...EAAACEEEEEEEEEEE.EADDC...EEGGADC...",
    "EAAAAAAC...CEEEGGGGGGGGGGACEEEC...EGGGADDC...",
    ".CAAAAAAC.EEGGGGAAAAAAAAAAAGBBCE.EGGAADDC....",
    "..CAAAAADCGGGAAAAAAAAAAAAAAABBBBCGGAAADC.....",
    "..EAAAADEGGAAAAAAAAAAAAAAAAABBBBDEAAADDC.....",
    "...CAAAEGGAAAAAAAAAAAAAAAAAABBBBBDCADDC......",
    "....CADEGAAAAAAAAAAAAAAAAAAABBBBBBEDDC.......",
    ".....CEGGAAAAAAAAAAAAAAAAAAABBBBBBDEC........",
    "......CGAAAAAFFFAAAAAAAAAAFFFFBBBBDDC........",
    "......EGAAAAFFFFFFAAAAAAAFQFLFFBBBDDC........",
    "......EGAAAFQQLLFFAAAAAAFFQFLFFBBBDDC........",
    ".....EGGAAAFFFLLFFAAAAAAFFFFLFFFBBDDCCE......",
    ".....EGAAAAFFFLLFFAAAAABFFFFLFFKBBDDCHHC.....",
    ".....EGAAAAFFFLLFFAAAABBKFFFLFFKBBDDCHHIC....",
    ".....EBAAAAKFFFLFKAAABBBBKFFLFKBBDDDCHHHIC...",
    ".....ECBAAAAKKKKKAAAAABBBBKKKKBBBDDDCHHHIC...",
    "....EOEBBAAAAAAAAAAAAAABBBBBBBBBDDDCOHHHIIC..",
    "....EOHCBBAAAAAAAAATAAABBBBBBBDDDDDCHHHIIIC..",
    "....EHHHCDBAAAAAAMAAAAAABMBBBDDDDDCOHHIIIIC..",
    ".....CHHHCDDAAAAAAMMMMMMMMBBDDDDCCOHIIIIIC...",
    ".....EIIHHCCDAAAAAAMMSSSMBBDDDDCOHHHIIIIC....",
    "......CCCHHHCCAAAAAAAAAABBBBDGCOHHHHIICC.....",
    "........EOHHIEGAAAAAAAABBBBBBEHHHIHHIICR.....",
    ".......EHIHIEGGAAAAAAAABBBBBBDEHHIIIIEJJNR...",
    "........CICEGGAAAAAAAABBBBBBBBDCIIICIEJJJJNR.",
    ".........CEEGAAABBBBBBBBBBBBBBDEIIICCCNJJJJPN",
    "..........EGGAABBBBBBBBBBBBBBBDDCIC...RJJJJPN",
    "..........EBAAABBBBBBBBBBBBBBBDDCIC...ECJJJPN",
    "..........EBBAABBBBBBBBBBBBBBDDDCC....EEJJJPN",
    "..........EBBBBBBBBBBBBBBBBBBDDDC.....EEJJJPN",
    "...........CDDDBBBBBBBBBBBBBDDDC......EACPPPN",
    ".........EEEDDDDBBBBBBDDDDDDDDDCEE...EAADCCN.",
    ".......EEAACCDCCCBBBBDDDDDDDDDEECACEEAADDC...",
    "......EAAAAAACAAACBBBDDDCCCCCECCAAAECADDC....",
    ".....EAAAAAAAAAAAACBBDDCAAAAACAAAAAECDDC.....",
    ".....EAAAAAAAAAAAAEDDDDCAAAAADAAAADECCC......",
    "......CDDDDDDAAADDDCDDDCAAADDDCDDDDCC........",
    ".......CCCCCCCDDDCC.CCCCCDDDCC.CCCC..........",
    "..............CCC........CCC.................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (45, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 45x42).
    scale=int   -> sprite de 45x42 px ampliado por un entero, sin márgenes.
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
