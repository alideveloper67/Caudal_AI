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
    "A": (21, 21, 28),
    "B": (38, 38, 46),
    "C": (2, 2, 3),
    "D": (26, 23, 17),
    "E": (11, 11, 16),
    "F": (245, 194, 26),
    "G": (251, 251, 255),
    "H": (239, 187, 147),
    "I": (232, 173, 134),
    "J": (246, 201, 160),
    "K": (224, 36, 46),
    "L": (74, 74, 94),
    "M": (212, 144, 12),
    "N": (106, 26, 34),
    "O": (106, 10, 18),
    "P": (255, 222, 182),
    "Q": (196, 200, 228),
    "R": (106, 108, 148),
    "S": (122, 74, 6),
    "T": (168, 20, 30),
    "U": (98, 98, 122),
    "V": (243, 154, 138),
    "W": (236, 106, 120),
    "X": (255, 210, 58),
    "Y": (154, 90, 52),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".....EEEE......................EEEE.....",
    "...EELLLBCE..................EELLLBCE...",
    "..ELLLBBBBAC................ELLLBBBBAC..",
    ".ELLEBBBBBBAC..............ELLEBBBBBBAC.",
    ".ELEUCBBBBBAC..............ELEUCBBBBBAC.",
    "ELEUCBBBBBBAAC............ELEUCBBBBBBAAC",
    "ELEUCBBBBBBAAC..EEEEEEEE..ELEUCBBBBBBAAC",
    "ELBCBBBBBBAAACEELLLLAAABCEELBCBBBBBBAAAC",
    "EBBBBBBBBBAAECAAABBAAAAABBCEBBBBBBBBAAAC",
    ".CBBBBBBBAAEAAAPPJAAAAHHHBBACBBBBBBAAAC.",
    ".EABBBBAAAAEAAPPJJJAAHHHHIBBEBBBBAAAAAC.",
    "..CEEAAAAAEAAPPJGGJJPHGGHIIBAEAAAAAAAC..",
    "..RAAEAAACLAAPJGGGGJJGGGGIILBACAAAACC...",
    ".RGGGAACCELAAPJGGAGJJGGAGIILBACCCCC.....",
    "RGGGGGQAELLAAPJGGAAJJGGAAIILBAAC........",
    "RGGGGGGAELBAAPJGAAAJJGAAAIILBAAC........",
    "RGGGGGGQCAAAAPJJAAAJJJAAAHILBAAC........",
    "RGGGGGQQCAAAAPJJJAJJJJJAHHHABAAC........",
    ".AQGQRRAEAAPPPJJJJJAAJHHHHHHIAAC........",
    "..AARCCCEAPPJJJJJJAAAAHHHHHHIIAC........",
    "....CLBC.DPJJJJJJJAAAAHHHHHIIID.........",
    "....EBBBCYHHVVHHNHHHHHHNHHVVIID.........",
    ".....CBBBCDHHHHHNNNNNNNNHHIIID..........",
    "......CBBBDIHHHHNNNNNNNNIIIIID..........",
    "......EBBBBDIIHHHNWWWWNIIIIID...........",
    ".......CABBBCDIIIIIIIIIIIIDD............",
    "........CCBBBAEBIIIIIIIIBCCE............",
    "..........CAAEBBBBBBBBBBEBBBC...........",
    "...........CCBBBBBBBBBBBBEEBBCE.........",
    "............EAAAAAAAAAAAAAACBAECRR......",
    "............ODDDDDDDDDDDDDDCAEAGGGA..E..",
    "...........OKKKKKOKKKKOKKKKTAAGGGGQAEAC.",
    "...........OKKKKOXDKKOXDKKKTAGGGGGQAEAC.",
    "...........OKKKKOXDKKOXDKKKTDAGGGGQAEAC.",
    "...........OKKKKKDKKKKDKKKTTDRQQQQQCAAC.",
    "..........SSDOOOOKKKKKTOOOOCBBCCCCCAAC..",
    "........SSFFFDDBBDTTTTOBBDDFDDBBBBBCC...",
    "......SSFFFFFFFDDDDDDDDDDFFFFFDDDDC.....",
    ".....SFFFFFFFFFFMMD..SFFFFFFFFFFFMD.....",
    ".....SFFFFFFFFFFMD....DFFFFFFFFFFMD.....",
    ".....SFFFFFFFFMMMD....SMFFFFFFFFMMD.....",
    "......DMMMMMMMMDD......DDMMMMMMMMD......",
    ".......DDDDDDDD..........DDDDDDDD.......",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (40, 43)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 40x43).
    scale=int   -> sprite de 40x43 px ampliado por un entero, sin márgenes.
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
