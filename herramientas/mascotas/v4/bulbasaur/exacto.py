#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por extract_sprite.py.

Requiere solo Pillow:  pip install pillow
Uso:  python v4\bulbasaur\exacto.py                 -> guarda v4\bulbasaur\exacto.png
      from v4\bulbasaur\exacto import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (57, 148, 148),
    "B": (98, 213, 180),
    "C": (16, 16, 16),
    "D": (131, 238, 197),
    "E": (24, 74, 74),
    "F": (115, 172, 49),
    "G": (189, 255, 115),
    "H": (49, 115, 115),
    "I": (164, 213, 65),
    "J": (172, 0, 49),
    "K": (82, 98, 41),
    "L": (205, 205, 205),
    "M": (255, 106, 98),
    "N": (238, 32, 57),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    ".........................................K..........................",
    ".......................................KKICC........................",
    "...............................FFFFKKKKIFFKFC.......................",
    ".............................FFGGGGGGIIIFIKFC.......................",
    "............................FGGGGGGGGGFFIIFKC.......................",
    ".................EE........FGGGGGECFFFGIIIFKC.......................",
    "................ADDEE.HHHHHHHHHEEDBCGGGGIIIKFC......................",
    "................ADDDHHDDDDDBBBEDDDBCGGGGIIIKFFC.....................",
    "................ADADDDDDAAADBBDDDBBCGGGGIIIFKFC.....................",
    "................AHDDDDDAAAADDBBBBBBACGGGIIIFKFFC....................",
    "................HDDDDDAAAADDDBBBBBBACGGIIIIFFKFC....................",
    "................HDDDDDAAADDDDBAABBBACGIIIIFFFKFFC...................",
    "...............HEDBDDDDDDDDBDHLLEBAAACIIIFFFFKFFC...................",
    "...............ENADBDDDAADBDHNJ.LEAAACEFFFFFFKFFC...................",
    "...............ENADBDDAAADBDHNJ..EAAACEFFFFFKFFFC...................",
    "..............HLN.ADDDAADDDAN.JJ.LAAAEAEFFFFKFFFC...................",
    "..............H.J.ABDDDDDDBAJ.MM.LAAAHAAEFFKFFFC....................",
    "..............HBJJABBBBBBBBAJJMMLAAAAAAAAEEFFFFC....................",
    "..............ECBBBBBBBBBBBBBBBBAAEAAAAAAAAEFFC.....................",
    "..............EACEBBABBHBBBBBBHECCAAHAAAEEAAEC......................",
    "...............EA.JJBBBBBHECCC.HAAAAEAAAEEEAAE......................",
    "................EAAHJJJJJJJJJJHAAAAEAAAAAEEAAAE.....................",
    ".................CCAAHJNMMMMHAAAACCAAAAAHAAAAAE.....................",
    "...................CCAAAAAAAAACCCAAAHAAEAAAEAAAC....................",
    "...................EACCCCCCCCCAAAAAAEAACAAEEEAAC....................",
    "...................ABBBAEAAAAAAEBBAAAECAAAEEEAAC....................",
    "....................HABBAECAAAEAABBAAECAAAEEEAAC....................",
    "....................HABBAAACCCEAAABAAECAAAAEAAC.....................",
    "....................ABBBBAAC..ABAABAAE.CHAHAHAC.....................",
    ".....................HBABAAC..ABBBBAC..ELELELE......................",
    "....................E.E.EAC...EBABAAC...CCCCC.......................",
    ".....................CCCCC...E.E.E.C................................",
    "..............................CCCCC.................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
    "....................................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 5.647059, 5.647059      # tamaño original de cada píxel lógico en la imagen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (384, 384)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (vecino más cercano).

    scale=None  -> reproduce la imagen original (celda 5.647059x5.647059, lienzo 384x384).
    scale=int   -> sprite de 68x68 px ampliado por un entero, sin márgenes.
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
    render().save("v4\bulbasaur\exacto.png")
    print("Guardado v4\bulbasaur\exacto.png")
