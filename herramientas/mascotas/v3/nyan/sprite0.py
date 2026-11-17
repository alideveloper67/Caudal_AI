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
    "A": (255, 158, 224),
    "B": (156, 156, 166),
    "C": (224, 166, 110),
    "D": (248, 136, 210),
    "E": (136, 136, 152),
    "F": (236, 186, 132),
    "G": (116, 116, 138),
    "H": (17, 17, 26),
    "I": (242, 114, 196),
    "J": (138, 90, 42),
    "K": (70, 70, 90),
    "L": (255, 196, 238),
    "M": (26, 21, 17),
    "N": (28, 28, 38),
    "O": (232, 48, 138),
    "P": (255, 143, 168),
    "Q": (188, 188, 198),
    "R": (58, 42, 54),
    "S": (255, 210, 58),
    "T": (74, 200, 240),
    "U": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..........JJJJJJJJJJJJJJJJJJJJJJJJJJ................",
    ".........JFFFFFFFFFFFFFFFFFFFFFFFFFFM...............",
    "........JFCCCCCCCCCCCCCCCCCCCCCCFFFFCM..............",
    ".......JFCCCCCCCCCCCCCCOOCCCCCCCCFFFCCM.............",
    ".......JFCCCLLLLLLLLLLLLAADDDDDIIIFFCCM.............",
    ".......JFCCLLAAAAAAAAAAAAADDDDDIIIIFCCM.......NKK...",
    ".......JFCCLAAOAAAAAAAAAAADDDDIIKQBFCCM......NKEGH..",
    ".......JFCCLAAOAAAAAAAAAAASSDDIIKBBBCCM.....NKEEGH..",
    ".......JFCCLAAAAAAAAAAAAAADDDDIKQBBBBCM....NKEEEGGH.",
    ".......JFCCLAAAAAAAAAAAAAADDDDIKBBBBBBH...NKEEEEGGH.",
    ".......JFCCLAAAAAAAAAAAAADDDDDIKBBBBBBBHKNKQBEEEGGH.",
    ".KK....JFCCLAAAATAAAAAAOADDDDDIKBBBBBBBBQQQBBEEEGGH.",
    "KBGH...JFCCLOOAATAAAAAAAADDDDOIKBBBBBBBBBBBBBEEEGGH.",
    "KBGH...JFCCLAAAAAAAAAAAAADDDDDIKBBBBBBBBBBBBBEEEGGH.",
    "KBGH...JFCCLAAAAAAAAAAAAADDDDIIKBBBBBBBBBBBBBEEEEGH.",
    "KBBH...JFCCLAAAAAAAAAAAAADDDDIIKBBBBBBBBBBBBBEEEEGH.",
    "KBBGH..JFCCLAAAAAAAAOAAAAADDDIKQBBBBUNBBBBBBUNEEEGGH",
    "KBBBH..JFCCLASAAAAAAAAAAAAADDIKBBBBBNNBBBBBENNEEEGGH",
    ".HBBBHKJFCCLAAAAAAAAAAAAAAAADIKBBBBBNNBBBBEENNEEEGGH",
    ".KGBBBBKFCCDDDDDDDDDDDDDDDDDDIKBBBBBBBBBEEEEEEEEEGGH",
    "..HHGGGKFCCDDDDDDDDDDDDDDDDDDDKBBPPBBEREEEEREEEPPGGH",
    "....HHHMFCCDDDDDDDDDDDDDDDDTDDKEEPPPEEERRRREEEPPPGGH",
    ".......JFFCDDDDDODDDDDDDDDDDDDDKEEEEEEEEEEEEEEGGGGH.",
    ".......JFFFIIIIIIIIIIIIIIIIIIIIIKEEEEEEEEEEEGGGGGH..",
    ".......JFFFFIIIIIIIIIIIIIIIIIIIIIKGEEEEEEGGGGGGGH...",
    ".......JFFFFFFFFFFFFFFFFFFFFFFFFFFCKGGGGGGGGGGHH....",
    "........MCCCCCCCCCCCCCCCCCCCCCCCCCCCCKGGGGGHHH......",
    "........JCCCCCCCCCCCCCCCCCCCCCCCCCCCHHHHHHH.........",
    "........KHHHHHHHHHHHMMMMMMMMMMHHHHHHKBBBGH..........",
    ".........HBGGHKBBBGH..........KBBGGHKBBBGH..........",
    "..........HGH.KGGGGH...........HGGH.KGGGGH..........",
    "...........H...HHHH.............HH...HHHH...........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (52, 32)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 52x32).
    scale=int   -> sprite de 52x32 px ampliado por un entero, sin márgenes.
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
