#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por extract_sprite.py.

Requiere solo Pillow:  pip install pillow
Uso:  python v4\squirtle\exacto.py                 -> guarda v4\squirtle\exacto.png
      from v4\squirtle\exacto import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (90, 156, 164),
    "B": (139, 197, 205),
    "C": (16, 16, 16),
    "D": (41, 115, 131),
    "E": (205, 123, 41),
    "F": (230, 172, 90),
    "G": (255, 230, 156),
    "H": (255, 213, 106),
    "I": (131, 41, 0),
    "J": (180, 230, 238),
    "K": (213, 205, 205),
    "L": (189, 106, 0),
    "M": (98, 41, 0),
    "N": (213, 148, 82),
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
    "..........................AAAADD....................................",
    "........................AAJJJJBBDD..................................",
    ".......................AJJJJBBBBBBD.................................",
    "......................DJJJJBBBBBBBBD................................",
    ".....................DBJJJBBBBBBBBBBD...............................",
    ".....................DBBBBBBBABBBBBBD...............................",
    "....................DABBBBBBABAAABBBAD..............................",
    "....................DIBBBBBBBACKKABAAC..............................",
    "....................D.ABBBBBBCCCKDAAAC..............................",
    "....................DIABBBBBBCCI.DAAAC..............................",
    "....................DCBBBBBBB.CI.DAAAC..............................",
    "...................DJJBBBBBBBICI.AAAAC..............................",
    "...................CJBABABBBBBBAAAAAAC..............................",
    "....................CDBBBBBBBBAADAAAC..ADDD.........................",
    "................A.A..CCBBADDDDDIIAAAD.ABBAAC........................",
    "................DBADCCACCIEEEEIIAAACABBBDAC.........................",
    "...............ABBBBAACAAIIIIIAAADCDBBBDDAC.........................",
    "...............DBBBBBBBCDAAAAAACCEKABBBAAC..........................",
    "................DABBBBBAADCCCCCFFFDBBBAAAC..........................",
    ".................DAAAAAAEFHHHHFFFDABBAAAC...........................",
    "..................DDAAAEEHHHHEEEEDAAAAACM.....DDDD..................",
    "....................CCAEGEEEEFHHHEDAAACLLM..DDBBBAD.................",
    "......................EGGHFGGGGHHEFCCCKLLM.DABBBBBAD................",
    "......................EGGGFGGGGHFFFFMKKLLMDABBBBBBBD................",
    "......................EGGGFGGGGHEHFFMKKLLCAAABBDDBBAC...............",
    "......................EEHGEGGGHEHHFFLKKLCMAAAADBBDBAC...............",
    "......................EGFEEEFFEEHHHFELKNLMAAADABBBAAC...............",
    "......................EGGGEGGGHFEHHFEMKKLCAAACAAAAAC................",
    ".....................AEHGGFGGGGHFEFAADDKLCAAACAAAAAC................",
    "....................ABBEHHFHGGGHFFABBBADKCAAAACAAAC.................",
    "...................ABBBEFFEEFFFFFABBBBBADAAAAAACCC..................",
    "...................ABBBBEEFFEEFFFDBBBBBACAAAACCC....................",
    "...................DBBBBAIFFFFEEEDBBBBBADCCCC.......................",
    "...................CABBAAAIIFFFFECABBBAAAC..........................",
    "....................CAAAAAACIICCCCDAAAAAAC..........................",
    "....................DAAAAACC......CAAAAAAC..........................",
    "...................DBADBACC........CAAAAAAC.........................",
    "....................CC.CC..........CBACBDCC.........................",
    "....................................CC.CC...........................",
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
    render().save("v4\squirtle\exacto.png")
    print("Guardado v4\squirtle\exacto.png")
