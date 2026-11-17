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
    "A": (252, 211, 78),
    "B": (243, 188, 59),
    "C": (234, 166, 40),
    "D": (26, 23, 17),
    "E": (255, 242, 182),
    "F": (138, 78, 8),
    "G": (255, 240, 154),
    "H": (246, 216, 134),
    "I": (28, 26, 34),
    "J": (247, 160, 142),
    "K": (138, 42, 42),
    "L": (255, 233, 160),
    "M": (255, 251, 230),
    "N": (242, 122, 122),
    "O": (242, 196, 92),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "................FF.......FF................",
    "...............FLLD.....FLLD...............",
    "...............FLLOD...FLLLOD..............",
    "..............FFFFFDFFFFFFFFD..............",
    "............FFFGGGGGGGGGGGGADFF............",
    "..........FFGGGGAAAAAAAAAAAAAGADF..........",
    ".........FGGGAAAAAAAAAAAAAAAAAAABD.........",
    "........FGGAAAAAAAAAAAAAAAAAAAAABBD........",
    ".......FGGAAAAAAAAAAAAAAAAAAAAAABBBD.......",
    "......FGGAAAAAAAAAAAAAAAAAAAAAAABBBBD......",
    ".....FGGAAAAAAAAAAAAAAAAAAAAAAAABBBBCD.....",
    "....FGGAAAAAAAAAAAAAAAAAAAAAAAABBBBBBCD....",
    "....FGAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBCD....",
    "...FGGAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBCCD...",
    "...FGAAAAAAAAIIIAAAAAAAAAAAIIIBBBBBBBCCD...",
    "...FGAAAAAAAAIIIAAAAAAAAAAAIIIBBBBBBBCCD...",
    "...FGAAAAAAAAIIIAAAAAAAAAAAIIIBBBBBBCCCD...",
    "...FAAAAAAAAAIIIAAAAAAAAAAAIIIBBBBBBCCCD...",
    "....DAAAAAAAAAAAAAAAAAAAAABBBBBBBBBBCCD....",
    "....FGAAJJJJJAAAAAKKKKKKKBBBBBJJJJJCCCD....",
    "....FBBBJJJJAAAAAAAKKKKKBBBBBBBJJJJCCCD....",
    ".....DBBBBBBBAAAABBKNNNKBBBBBBBBBCCCCD.....",
    "......DBBBBBBBBBBBBBBBBBBBBBBBBBCCCCD......",
    "..FFFF.DBBBBBBBBBBBBBBBBBBBBBBBCCCCD.......",
    ".FGGGAD.DCBBBBBBBBBBBBBBBBBBBCCCCCD........",
    "FGGAAAADFDCCCBBBBBBBBBBBBBBCCCCCCD.........",
    "FGAAAAAAADAACCCCCCBBBBCCCCCCCCCAADF........",
    "FAAAAAAAAADAAAACCCCCCCCCCCCCCAADDAAD.......",
    ".DCAAAAAAAADAACCEEEECCCCEEEEEHADAAACDFFFF..",
    "..DDCAAAAAAFACCMMEEEEEEEEEEEEHFAAAAFFGGGAD.",
    "....DDCAAAAFACMMEEEEEEEEEEEEEHHDAAAADDAAACD",
    "......DDCFFFACMEEEEEEEEEEEEEEHHDAAAAFDAAACD",
    "........DAAAACMEEEEEEEEEEEEEEHHFFAACFDAAACD",
    "........FAAAACMEEEEEEEEEEEEEHHHAAFFFDGAACCD",
    "........FAAAAAEEEEEEEEEEEEEEHHHACCDDGAACCD.",
    ".........DAAAAAEEEEEEEEEEHHHHHAACDGAAACCD..",
    ".........FCCCCCCEEEEEEEHHHHHHHCCCDCCCCCD...",
    "..........DDDDDDDHHHEHHHHHHDDDDDDFDDDDD....",
    ".........FAAAAAAADHHHHHHHDDAAAAAACD........",
    "........FAAAAAAAACFAAAHAADAAAAAAACD........",
    ".........DAAAAAACFAAAAAAADAAAAAACCD........",
    "..........DCCCCCCDDDDDDDDDCCCCCCCD.........",
    "...........DDDDDD.........DDDDDDD..........",
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
