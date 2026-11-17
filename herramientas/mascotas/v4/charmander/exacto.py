#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por extract_sprite.py.

Requiere solo Pillow:  pip install pillow
Uso:  python v4\charmander\exacto.py                 -> guarda v4\charmander\exacto.png
      from v4\charmander\exacto import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (255, 148, 65),
    "B": (222, 82, 57),
    "C": (16, 16, 16),
    "D": (139, 41, 0),
    "E": (255, 213, 123),
    "F": (230, 172, 90),
    "G": (230, 57, 0),
    "H": (255, 213, 8),
    "I": (246, 164, 0),
    "J": (8, 57, 139),
    "K": (24, 139, 180),
    "L": (49, 172, 238),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "....................................................",
    "....................................................",
    "....................................................",
    "....................................................",
    "....................................................",
    "....................................................",
    "....................................................",
    "..............BBDDD.................................",
    "............BBAAAAADD...............................",
    "...........BEAAAAAAAAC..............................",
    "..........BEEEAAAAAAAC..............................",
    "..........BEEEAAAAAAAAC.............................",
    ".........BAAEAAAAABAAAC.............................",
    ".........BAAAAAAABAAAABC............................",
    ".........JBAAAAAABAJJBBC............................",
    ".........KBAAAAAAAJJJDBC............................",
    "..........AAAAAAAA.CKDBC............................",
    ".........CAAAAAAAA.JLDBC.............G..............",
    "........DJAAAAAAAADKLBBC.............GH.............",
    "........DEEEAAAAAAABBBBC.............GH.............",
    "........DEEAABAAAABBDBBC............GIH.............",
    ".........DAAAAAAABDDBBC......DD.....GHHI............",
    ".........CCAAAADDC.BBBC..DDDDBC.....GIHHG...........",
    "......DD...CCCCGGDBBBBDDDAAAABC.....GHGHI...........",
    "......CBDDDCBBDDDBBCBBAAAAAABBBC...GGGGHHG..........",
    "......CBAAABCCAABCCBBBBAABBBBCC....GGIGGHIG.........",
    ".....CBBBAABBBCCCBBBBBBBBBBBC......GHHGHHHG.........",
    "......CCBBBBBBBBBBBBBBBBBBCC.......GIHHHHHG.........",
    "........CCBBBBDBFFFBBBBDDC.........GIIIHHIG.........",
    "..........CCBBDFFFFFBBAAC...........GIGIIGG.........",
    "............CDBEEEEEFAAAC............GGDGG..........",
    ".............DFEEEEEEAAABC............DDG...........",
    ".............DEEEEEEEAAAAC............DEC...........",
    ".............DEEEEEEEAAAAAC...........DAC...........",
    "............DFEEEEEEEFAAAAC..........DAAC...........",
    "............DEEEEEEEEEAAAAC........DDAABC...........",
    "...........DDEEEEEEEEEBAAAAC....DDDAAABC............",
    "..........DABFEEEEEEEFBAAAABCDDDAAAAABFC............",
    "..........DAABFEEEEFFBAAAAAACBBBBAABFFC.............",
    ".........CAAADFFFFFFFBAAAAAABCBBBBBFFC..............",
    ".........CAAAACFFFFFFBAAAAABBCBBBFFFC...............",
    ".........CAAAABCFFFFFDBAAABBBCFFFFCC................",
    "..........CAABBBCCFFFDBBBBBBBCFFDD..................",
    "...........CBBBBBBCCCCDBBBBBCDDD....................",
    "...........CBBBBCC.....DBBBBC.......................",
    "..........CBBBBBC......DAAABC.......................",
    ".........C.D.BBC.......DBAAABC......................",
    "..........CCCCC.........C.D.D.C.....................",
    ".........................CCCCC......................",
    "....................................................",
    "....................................................",
    "....................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 7.384615, 7.384615      # tamaño original de cada píxel lógico en la imagen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (384, 384)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (vecino más cercano).

    scale=None  -> reproduce la imagen original (celda 7.384615x7.384615, lienzo 384x384).
    scale=int   -> sprite de 52x52 px ampliado por un entero, sin márgenes.
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
    render().save("v4\charmander\exacto.png")
    print("Guardado v4\charmander\exacto.png")
