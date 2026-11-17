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
    "A": (184, 131, 79),
    "B": (36, 18, 10),
    "C": (251, 230, 192),
    "D": (166, 114, 68),
    "E": (94, 54, 24),
    "F": (147, 96, 58),
    "G": (212, 160, 106),
    "H": (236, 200, 152),
    "I": (244, 160, 138),
    "J": (255, 244, 220),
    "K": (58, 32, 16),
    "L": (74, 42, 22),
    "M": (200, 204, 216),
    "N": (255, 255, 255),
    "O": (122, 127, 148),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "....EEE......................EEE....",
    "...EGGABE..................EEGGAB...",
    "..EGGAAAAB......EEEE......EGGGAAAB..",
    ".EGFEEEEAFB.EEEEGGGABEEE.EGFEEEEAAB.",
    "EGFECCCHBEBEGGGGGAAAAGGABEEECCCCEAFB",
    "EGECCCCHEGGGGAAAAAAAAAAAAGDECCCCHBFB",
    "EAECCCHHGGAAAAAAAAAAAAAAAADDCCCHHBFB",
    ".BABHHHGGAAAAAAAAAAAAAAAAADDDHHHBFB.",
    ".EFABGGGAAAAAAAAAAAAAAAAAADDDDFBFFB.",
    "..BBEGAAAAAAAAAAAAAAAAAAAADDDDFEBB..",
    "...EGGAAAAAAAAAAAAAAAAAAAADDDDDFB...",
    "...EGAAAAAAAAAAAAAAAAAAAADDDDDDFB...",
    "..EGGAAAAAAAAAAAAAAAAAAAADDDDDDFFB..",
    "..EGAAAAAANBAAAAAAAAAAAANBDDDDDFFB..",
    "..EGAAAAABBBAAAAAAAAAAADBBBDDDDFFB..",
    "..EGAAAAABBBAAACCCCCCADDBBBDDDDFFB..",
    "..EGAAAAAAAAAACCKKKKCCDDDDDDDDFFFB..",
    "..EAAAAIIAAAACCCCKKCCCCDDDDIIDFFFB..",
    "...BDAAIIIAAACCCCCCCCCCDDDIIIFFFB...",
    "...EDDDDDAAAACCCLCCLCCCDDDDDFFFFB...",
    "....BDDDDDAADDCCCLLCCCDDDDDFFFFB....",
    ".....BDDDDDADDDCCCCCCDDDDDFFFFB.....",
    "......BDDDDDDDDDDDDDDDDDDFFFFB......",
    ".......BFFDDDDDDDDDDDDFFFFFFB.......",
    "........BFFFFFDDDDFFFFFFFFFB........",
    ".....EEEEBBBFFFDDFFFFFFFBBBEBEE.....",
    "....EAAABEAABEECDFFFCEEBGFEBAAAB....",
    "...EAAAAABBFEJJJCOOJJCHEAEBAAAAFB...",
    "...EAAAAAEBEJJCCCMMCCCCHBEBAAAAFB...",
    "...EAAAAAEBEJCCCCMMCCCCHEEBAAAAFB...",
    "...EAAAAFEEJJCCCCCCCCCHHHEEAAAAFB...",
    "...EAAAFEBECCCCCCCCCCCHHHBBEAAAFB...",
    "...EFFFEBGABCCCCCCCCCHHHBGABEFFFB...",
    "....BBBBGAAECCCCCCCCCHHHBAAFBBBB....",
    ".......BEEEEECCCCCCHHHHEEEEEB.......",
    ".......EBBBBBHHHHHHHHHHBBBBBB.......",
    "......EAAEEEEBBHHHHHHBBEEEEAAB......",
    ".....EAAECCCCEABBBBBBAECCCCBAFB.....",
    ".....EAAECCCCCBEBAAEBECCCCCBFFB.....",
    "......BFABCCCBFBBBBBBFBCCCBFFB......",
    ".......BBFBBBBB......BBBBBFBB.......",
    ".........BBBB..........BBBB.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (36, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 36x42).
    scale=int   -> sprite de 36x42 px ampliado por un entero, sin márgenes.
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
