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
    "A": (167, 163, 180),
    "B": (148, 144, 166),
    "C": (130, 125, 152),
    "D": (26, 22, 36),
    "E": (244, 234, 216),
    "F": (78, 72, 98),
    "G": (111, 106, 128),
    "H": (196, 192, 208),
    "I": (242, 178, 196),
    "J": (221, 205, 182),
    "K": (255, 250, 240),
    "L": (245, 154, 184),
    "M": (58, 42, 62),
    "N": (230, 240, 255),
    "O": (19, 17, 26),
    "P": (44, 39, 54),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......FF..............FF.....................",
    ".....FHAD............FCCD....................",
    ".....FHAADF.........FBBCD....................",
    ".....FHAAAAD.......FHHBCD....................",
    "....FHHIIAAAD.....FHHIICCD...................",
    "....FHAIIAAAAD...FHHIIIACD...................",
    "....FHIIIIAAAADFFHHAIIIAAD...................",
    "....FHAAIIIAAAAHHHAIIIIAAADF.................",
    "...FHHAAAAAAGAAGAAGAAAAAAAAADF...............",
    "...FHAAAAAAAGAAGAAGAAAAAAAAABBDF.............",
    "...FHAAAAAAAGAAGAAGAAAAAAAAAGBBBD............",
    "...FHAAAAAAAAAAAAAAAAAAAAAAAGBBBBDF..........",
    "...FHAAAAAAAAAAAAAAAAAAAAAAAGBBBGBCD.........",
    "...FHAAAAAAAAAAAAAAAAAAAAAAGGABBGBBCD...FFF..",
    "..FHHAAAAAAAAAAAAAAAAAAAAAAGGBBGGBBCD..FAAAD.",
    "..FHAAAAAAAAAAAAAAAAAAAAAAAGABBGGBBGCD.FAAACD",
    ".FHHAAAAADAAAAAAAAADAAAAAAAGABBGBBBGCD.FAAACD",
    ".FHAAAAADNDAAAAAAADNDAAAAAAGABBGBBBGCCDFFFFCD",
    ".FHAAAAADDDAAAAAAADDDAAAAAAAABBGBBBGBCDPGGGFD",
    ".FBBBBBBADAAAAAAAAADAAAAAAAABBBGBBBGBCDFDDGGO",
    ".FBBBBBBBBBAAMAMAAAAAAAAAAAABBBBBBGGBCCDAADDD",
    ".FBBBLLLBBBBBAMAMAAAALLLAAAABBBBBBBBBBCDAAACD",
    ".FBBBBBBBBBBBBAAAAAAAAAAAAAABBBBBBBBBCCDFFACD",
    ".FBBBBBBBBBBBBBAAAAAAAAAAAABBBBBBBBBBCCGGGFFD",
    ".FBBBBBBBBBBBBBBAAAAAAAAAAABBBBBBBBBBCCDDGGGO",
    "FBBBBBBBBBBBBBBBBAAAAAAAAABBBBBBBBBBBCCDADDD.",
    "FBBBBBBBBBBBBBBBBBAAAAAAABBBBBBBBBBBBCCDACCD.",
    "FBBBBBBBBBCCCCCCBBBAAAABBBBBBBBBBBBBCCCDCCD..",
    ".DBBBBBCCCCCCCCCCCCBBBBBBBBBBBBBBBBBCCCDCD...",
    ".FBBBBCCCCCCKKKKKECCCBBBBBBBBBBBBBBBCCDCD....",
    ".FBBBCCCCKKKKEEEEEEKECBBBBBBBBBBBBBBCCDD.....",
    ".FBBBCCCKKEEEEEEEEEEEEJBBBBBBBBBBBBCCCD......",
    ".FBBBCCKKEEEEEEEEEEEEEEBBBBBBBBBBBBCCCD......",
    "..DBBBCKEEEEEEEEEEEEEEJJBBBBBBBBBBCCCD.......",
    "..FBBBBEEEEEEEEEEEEEEEJBBBBBBBBBBCCCCD.......",
    "...DCBBBJEEEEEEEEEEEJJJBBBBBBBBCCCCCD........",
    "....DCCCCBJJJEEEJJJJJBBBBCCCCCCCCCCD.........",
    ".....DDCCCCCCCJJJCCCCCCCCCCCCCCCCDDD.........",
    "......FDDDDCDCCCCCCCCCCCCCCDDDDDDAAAD........",
    ".....FAAAACDDDDDDDDDDDDDDDDAACCAAAACCD.......",
    "......DCCCCD..DAAAD.......DCCCDDCCCCD........",
    ".......DDDD....DDD.........DDD..DDDD.........",
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
