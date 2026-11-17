#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite.py                 -> guarda sprite.png
      from sprite import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (246, 230, 82),
    "B": (246, 189, 32),
    "C": (0, 0, 0),
    "D": (156, 82, 0),
    "E": (222, 148, 0),
    "F": (98, 49, 8),
    "G": (65, 65, 74),
    "H": (41, 41, 41),
    "I": (255, 246, 164),
    "J": (197, 32, 24),
    "K": (230, 90, 65),
    "L": (115, 115, 131),
    "W": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......CC......................................................................",
    "......CC......................................................................",
    "....CCHHCC....................................................................",
    "....CCHHCC....................................................................",
    "....CCHHCC....................................................................",
    "....CCHHCC....................................................................",
    "....CCHHHHCC..................................................................",
    "....CCHHHHCC..................................................................",
    "..CCHHHHHHCC..................................................................",
    "..CCHHHHHHCC..................................................................",
    "..CCHHHHHHFF..................................................................",
    "..CCHHHHHHFF..................................................................",
    "..CCHHGGBBFF..................................HHHHHHHH........................",
    "..CCHHGGBBFF..................................HHHHHHHH........................",
    "..CCGGBBBBBBFF..........................HHHHHHGGGGGGGGHHCC....................",
    "..CCGGBBBBBBFF..........................HHHHHHGGGGGGGGHHCC....................",
    "..CCBBBBBBBBFF......................DDDDBBAAAAGGGGGGGGGGCC....................",
    "..CCBBBBBBBBFF......................DDDDBBAAAAGGGGGGGGGGCC....................",
    "..CCBBBBBBBBFF....DDDDDDDDDD....DDDDAAAAAAAAAAGGGGGGGGCC......................",
    "..CCBBBBBBBBFF....DDDDDDDDDD....DDDDAAAAAAAAAAGGGGGGGGCC......................",
    "....FFBBBBBBDDDDEEIIIIIIAAAAEEDDAAAAAAAAAAAALLGGGGGGCC........................",
    "....FFBBBBBBDDDDEEIIIIIIAAAAEEDDAAAAAAAAAAAALLGGGGGGCC........................",
    "....FFBBBBEEEEIIIIIIIIIIIIAAAAAAAAAAAAAAAAAAGGGGCCCC..............DDDD........",
    "....FFBBBBEEEEIIIIIIIIIIIIAAAAAAAAAAAAAAAAAAGGGGCCCC..............DDDD........",
    "......FFEEAAIIIIIIIIIIIIAAAAAAAAAAAAAAAAAACCCCCC................DDAAAADD......",
    "......FFEEAAIIIIIIIIIIIIAAAAAAAAAAAAAAAAAACCCCCC................DDAAAADD......",
    "......DDAAAAAAAAAAAAAAAABBCCCCBBAAAAEEDDCC....................DDAAAAAAAADD....",
    "......DDAAAAAAAAAAAAAAAABBCCCCBBAAAAEEDDCC....................DDAAAAAAAADD....",
    "....FFEECCBBAAAAAAAAAAAAGGWWCCHHAAAAAACC....................EEAAAAAAAAAADD....",
    "....FFEECCBBAAAAAAAAAAAAGGWWCCHHAAAAAACC....................EEAAAAAAAAAADD....",
    "....FFCCWWBBAAAAAAAAAAAACCCCGGHHAAAAAACC..................EEAAAAAAAAAAAAAADD..",
    "....FFCCWWBBAAAAAAAAAAAACCCCGGHHAAAAAACC..................EEAAAAAAAAAAAAAADD..",
    "....FFGGCCAAAAFFEEAAAAAABBCCCCBBAAAAAADD..............EEEEAAAAAAAAAAAAAAAADD..",
    "....FFGGCCAAAAFFEEAAAAAABBCCCCBBAAAAAADD..............EEEEAAAAAAAAAAAAAAAADD..",
    "....DDHHDDAAAAAAAAAAAAAAAAAAAAAAKKKKAAEEFF..........DDAAAAAAAAAAAAAAAAAAAADD..",
    "....DDHHDDAAAAAAAAAAAAAAAAAAAAAAKKKKAAEEFF..........DDAAAAAAAAAAAAAAAAAAAADD..",
    "..FFAAAAAAAAAAFFDDEEAAAAAAAAAAKKKKKKJJBBCC........DDAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFAAAAAAAAAAFFDDEEAAAAAAAAAAKKKKKKJJBBCC........DDAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFKKBBAAEEFFDDBBBBDDDDEEAABBJJJJJJJJBBCC......DDAAAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFKKBBAAEEFFDDBBBBDDDDEEAABBJJJJJJJJBBCC......DDAAAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFJJBBBBBBBBBBBBBBBBBBBBBBBBJJJJJJJJBBCC......DDBBAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFJJBBBBBBBBBBBBBBBBBBBBBBBBJJJJJJJJBBCC......DDBBAAAAAAAAAAAAAAAAAAAAAAAADD",
    "..FFJJBBBBBBBBBBBBBBBBBBBBBBBBBBJJJJBBBBCC....DDBBBBBBBBAAAAAAAAAAAAAAAAAACC..",
    "..FFJJBBBBBBBBBBBBBBBBBBBBBBBBBBJJJJBBBBCC....DDBBBBBBBBAAAAAAAAAAAAAAAAAACC..",
    "....DDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBCC..DDBBBBBBBBBBBBBBAAAAAAAAAACCCC....",
    "....DDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBCC..DDBBBBBBBBBBBBBBAAAAAAAAAACCCC....",
    "......CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBFF..DDBBBBBBBBBBBBBBBBBBAACCCC........",
    "......CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBFF..DDBBBBBBBBBBBBBBBBBBAACCCC........",
    "......CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBAACCWWFFBBBBBBBBBBBBBBCCCC............",
    "......CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBAACCWWFFBBBBBBBBBBBBBBCCCC............",
    "......CCAABBBBBBBBBBBBBBBBBBBBBBBBBBBBAAAACCWWWWFFBBBBBBBBCCCC................",
    "......CCAABBBBBBBBBBBBBBBBBBBBBBBBBBBBAAAACCWWWWFFBBBBBBBBCCCC................",
    "......CCAAAAAABBBBBBBBBBBBBBBBBBBBBBAAAAAACCWWWWWWFFBBBBDD....................",
    "......CCAAAAAABBBBBBBBBBBBBBBBBBBBBBAAAAAACCWWWWWWFFBBBBDD....................",
    "......CCAAAAAAAAAABBBBBBBBBBEEBBAAAAAAAAAACCWWWWWWWWFFBBBBFF..................",
    "......CCAAAAAAAAAABBBBBBBBBBEEBBAAAAAAAAAACCWWWWWWWWFFBBBBFF..................",
    "......EEAAAADDAAAAAAAAAAAAEEAAAAAAAAAAAAAAFFWWWWWWCCEEBBBBFF..................",
    "......EEAAAADDAAAAAAAAAAAAEEAAAAAAAAAAAAAAFFWWWWWWCCEEBBBBFF..................",
    "....CCAAAAAAEEAAAAAAAAAAAAEEAAAAAAAAAAAAAAAACCWWCCEEBBBBBBBBFF................",
    "....CCAAAAAAEEAAAAAAAAAAAAEEAAAAAAAAAAAAAAAACCWWCCEEBBBBBBBBFF................",
    "....CCAAAAAAAADDAAAAAAAADDAAAAAAAAAABBAAAAAACCFFEEEEEEBBEEFFCC................",
    "....CCAAAAAAAADDAAAAAAAADDAAAAAAAAAABBAAAAAACCFFEEEEEEBBEEFFCC................",
    "....CCEEAAAAAADDAAAAAAAADDAAAAAAAABBEEAAAABBCCEEEEEEEEFFFF....................",
    "....CCEEAAAAAADDAAAAAAAADDAAAAAAAABBEEAAAABBCCEEEEEEEEFFFF....................",
    "....CCDDAAAAAAEEAAAAAADDAAAAAAAAAADDAAAAAABBCCCCEEEECC........................",
    "....CCDDAAAAAAEEAAAAAADDAAAAAAAAAADDAAAAAABBCCCCEEEECC........................",
    "....CCDDAAAAAAAADDAAAACCEEAAAAAADDAAAAAABBBBBBCCCCDDDDCC......................",
    "....CCDDAAAAAAAADDAAAACCEEAAAAAADDAAAAAABBBBBBCCCCDDDDCC......................",
    "..CCAAAADDAAEEDDAAAAAAAACCAAEEDDAAAAAAAABBBBBBCCWWCCDDDDCC....................",
    "..CCAAAADDAAEEDDAAAAAAAACCAAEEDDAAAAAAAABBBBBBCCWWCCDDDDCC....................",
    "..DDAAAAAADDDDAAAAAAAAAAAADDDDAAAAAAAABBBBBBBBCCCCDDDDDDCC....................",
    "..DDAAAAAADDDDAAAAAAAAAAAADDDDAAAAAAAABBBBBBBBCCCCDDDDDDCC....................",
    "CCBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBAABBBBBBBBFFFFDDCCCC......................",
    "CCBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBAABBBBBBBBFFFFDDCCCC......................",
    "CCBBBBAAAAAAAAAAAAAAAAAAAAAAAAAABBAABBAABBBBBBBBCCCC..........................",
    "CCBBBBAAAAAAAAAAAAAAAAAAAAAAAAAABBAABBAABBBBBBBBCCCC..........................",
    "CCBBBBBBBBBBAAAAAAAAAAAAAABBBBBBAABBAABBBBBBBBBBCC............................",
    "CCBBBBBBBBBBAAAAAAAAAAAAAABBBBBBAABBAABBBBBBBBBBCC............................",
    "..DDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBFF..............................",
    "..DDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBFF..............................",
    "..CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBEECC..............................",
    "..CCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBEECC..............................",
    "....CCCCBBBBBBEEEECCCCCCCCFFBBBBBBBBBBBBBBEECC................................",
    "....CCCCBBBBBBEEEECCCCCCCCFFBBBBBBBBBBBBBBEECC................................",
    "..FFFFEEDDDDDDDDCC..........CCFFDDDDEEEEDDCC..................................",
    "..FFFFEEDDDDDDDDCC..........CCFFDDDDEEEEDDCC..................................",
    "FFAADDAAEEFFCCCC..................FFBBBBBBDDCC................................",
    "FFAADDAAEEFFCCCC..................FFBBBBBBDDCC................................",
    "..CCCCCCFF........................CCCCAADDAACC................................",
    "..CCCCCCFF........................CCCCAADDAACC................................",
    "......................................CCCCCC..................................",
    "......................................CCCCCC..................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (78, 92)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 78x92).
    scale=int   -> sprite de 78x92 px ampliado por un entero, sin márgenes.
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
    render().save("sprite.png")
    print("Guardado sprite.png")
