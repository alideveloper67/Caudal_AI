#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite_detalle.py                 -> guarda sprite_detalle.png
      from sprite_detalle import render; render(scale=8).save("x.png")
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
    "W": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......................................................KK..............",
    "......................................................KK..............",
    "..................................................KKKKIICCCC..........",
    "..................................................KKKKIICCCC..........",
    "..................................FFFFFFFFKKKKKKKKIIFFFFKKFFCC........",
    "..................................FFFFFFFFKKKKKKKKIIFFFFKKFFCC........",
    "..............................FFFFGGGGGGGGGGGGIIIIIIFFIIKKFFCC........",
    "..............................FFFFGGGGGGGGGGGGIIIIIIFFIIKKFFCC........",
    "............................FFGGGGGGGGGGGGGGGGGGFFFFIIIIFFKKCC........",
    "............................FFGGGGGGGGGGGGGGGGGGFFFFIIIIFFKKCC........",
    "......EEEE................FFGGGGGGGGGGEECCFFFFFFGGIIIIIIFFKKCC........",
    "......EEEE................FFGGGGGGGGGGEECCFFFFFFGGIIIIIIFFKKCC........",
    "....AADDDDEEEE..HHHHHHHHHHHHHHHHHHEEEEDDBBCCGGGGGGGGIIIIIIKKFFCC......",
    "....AADDDDEEEE..HHHHHHHHHHHHHHHHHHEEEEDDBBCCGGGGGGGGIIIIIIKKFFCC......",
    "....AADDDDDDHHHHDDDDDDDDDDBBBBBBEEDDDDDDBBCCGGGGGGGGIIIIIIKKFFFFCC....",
    "....AADDDDDDHHHHDDDDDDDDDDBBBBBBEEDDDDDDBBCCGGGGGGGGIIIIIIKKFFFFCC....",
    "....AADDAADDDDDDDDDDAAAAAADDBBBBDDDDDDBBBBCCGGGGGGGGIIIIIIFFKKFFCC....",
    "....AADDAADDDDDDDDDDAAAAAADDBBBBDDDDDDBBBBCCGGGGGGGGIIIIIIFFKKFFCC....",
    "....AAHHDDDDDDDDDDAAAAAAAADDDDBBBBBBBBBBBBAACCGGGGGGIIIIIIFFKKFFFFCC..",
    "....AAHHDDDDDDDDDDAAAAAAAADDDDBBBBBBBBBBBBAACCGGGGGGIIIIIIFFKKFFFFCC..",
    "....HHDDDDDDDDDDAAAAAAAADDDDDDBBBBBBBBBBBBAACCGGGGIIIIIIIIFFFFKKFFCC..",
    "....HHDDDDDDDDDDAAAAAAAADDDDDDBBBBBBBBBBBBAACCGGGGIIIIIIIIFFFFKKFFCC..",
    "....HHDDDDDDDDDDAAAAAADDDDDDDDBBAAAABBBBBBAACCGGIIIIIIIIFFFFFFKKFFFFCC",
    "....HHDDDDDDDDDDAAAAAADDDDDDDDBBAAAABBBBBBAACCGGIIIIIIIIFFFFFFKKFFFFCC",
    "..HHEEDDBBDDDDDDDDDDDDDDDDBBDDHHLLLLEEBBAAAAAACCIIIIIIFFFFFFFFKKFFFFCC",
    "..HHEEDDBBDDDDDDDDDDDDDDDDBBDDHHLLLLEEBBAAAAAACCIIIIIIFFFFFFFFKKFFFFCC",
    "..EENNAADDBBDDDDDDAAAADDBBDDHHNNJJWWLLEEAAAAAACCEEFFFFFFFFFFFFKKFFFFCC",
    "..EENNAADDBBDDDDDDAAAADDBBDDHHNNJJWWLLEEAAAAAACCEEFFFFFFFFFFFFKKFFFFCC",
    "..EENNAADDBBDDDDAAAAAADDBBDDHHNNJJWWWWEEAAAAAACCEEFFFFFFFFFFKKFFFFFFCC",
    "..EENNAADDBBDDDDAAAAAADDBBDDHHNNJJWWWWEEAAAAAACCEEFFFFFFFFFFKKFFFFFFCC",
    "HHLLNNWWAADDDDDDAAAADDDDDDAANNWWJJJJWWLLAAAAAAEEAAEEFFFFFFFFKKFFFFFFCC",
    "HHLLNNWWAADDDDDDAAAADDDDDDAANNWWJJJJWWLLAAAAAAEEAAEEFFFFFFFFKKFFFFFFCC",
    "HHWWJJWWAABBDDDDDDDDDDDDBBAAJJWWMMMMWWLLAAAAAAHHAAAAEEFFFFKKFFFFFFCC..",
    "HHWWJJWWAABBDDDDDDDDDDDDBBAAJJWWMMMMWWLLAAAAAAHHAAAAEEFFFFKKFFFFFFCC..",
    "HHBBJJJJAABBBBBBBBBBBBBBBBAAJJJJMMMMLLAAAAAAAAAAAAAAAAEEEEFFFFFFFFCC..",
    "HHBBJJJJAABBBBBBBBBBBBBBBBAAJJJJMMMMLLAAAAAAAAAAAAAAAAEEEEFFFFFFFFCC..",
    "EECCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBAAAAEEAAAAAAAAAAAAAAAAEEFFFFCC....",
    "EECCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBAAAAEEAAAAAAAAAAAAAAAAEEFFFFCC....",
    "EEAACCEEBBBBAABBBBHHBBBBBBBBBBBBHHEECCCCAAAAHHAAAAAAEEEEAAAAEECC......",
    "EEAACCEEBBBBAABBBBHHBBBBBBBBBBBBHHEECCCCAAAAHHAAAAAAEEEEAAAAEECC......",
    "..EEAAWWJJJJBBBBBBBBBBHHEECCCCCCWWHHAAAAAAAAEEAAAAAAEEEEEEAAAAEE......",
    "..EEAAWWJJJJBBBBBBBBBBHHEECCCCCCWWHHAAAAAAAAEEAAAAAAEEEEEEAAAAEE......",
    "....EEAAAAHHJJJJJJJJJJJJJJJJJJJJHHAAAAAAAAEEAAAAAAAAAAEEEEAAAAAAEE....",
    "....EEAAAAHHJJJJJJJJJJJJJJJJJJJJHHAAAAAAAAEEAAAAAAAAAAEEEEAAAAAAEE....",
    "......CCCCAAAAHHJJNNMMMMMMMMHHAAAAAAAACCCCAAAAAAAAAAHHAAAAAAAAAAEE....",
    "......CCCCAAAAHHJJNNMMMMMMMMHHAAAAAAAACCCCAAAAAAAAAAHHAAAAAAAAAAEE....",
    "..........CCCCAAAAAAAAAAAAAAAAAACCCCCCAAAAAAHHAAAAEEAAAAAAEEAAAAAACC..",
    "..........CCCCAAAAAAAAAAAAAAAAAACCCCCCAAAAAAHHAAAAEEAAAAAAEEAAAAAACC..",
    "..........EEAACCCCCCCCCCCCCCCCCCAAAAAAAAAAAAEEAAAACCAAAAEEEEEEAAAACC..",
    "..........EEAACCCCCCCCCCCCCCCCCCAAAAAAAAAAAAEEAAAACCAAAAEEEEEEAAAACC..",
    "..........AABBBBBBAAEEAAAAAAAAAAAAEEBBBBAAAAAAEECCAAAAAAEEEEEEAAAACC..",
    "..........AABBBBBBAAEEAAAAAAAAAAAAEEBBBBAAAAAAEECCAAAAAAEEEEEEAAAACC..",
    "............HHAABBBBAAEECCAAAAAAEEAAAABBBBAAAAEECCAAAAAAEEEEEEAAAACC..",
    "............HHAABBBBAAEECCAAAAAAEEAAAABBBBAAAAEECCAAAAAAEEEEEEAAAACC..",
    "............HHAABBBBAAAAAACCCCCCEEAAAAAABBAAAAEECCAAAAAAAAEEAAAACC....",
    "............HHAABBBBAAAAAACCCCCCEEAAAAAABBAAAAEECCAAAAAAAAEEAAAACC....",
    "............AABBBBBBBBAAAACC....AABBAAAABBAAAAEE..CCHHAAHHAAHHAACC....",
    "............AABBBBBBBBAAAACC....AABBAAAABBAAAAEE..CCHHAAHHAAHHAACC....",
    "..............HHBBAABBAAAACC....AABBBBBBBBAACC....EELLEELLEELLEE......",
    "..............HHBBAABBAAAACC....AABBBBBBBBAACC....EELLEELLEELLEE......",
    "............EEWWEEWWEEAACC......EEBBAABBAAAACC......CCCCCCCCCC........",
    "............EEWWEEWWEEAACC......EEBBAABBAAAACC......CCCCCCCCCC........",
    "..............CCCCCCCCCC......EEWWEEWWEEWWCC..........................",
    "..............CCCCCCCCCC......EEWWEEWWEEWWCC..........................",
    "................................CCCCCCCCCC............................",
    "................................CCCCCCCCCC............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (70, 66)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 70x66).
    scale=int   -> sprite de 70x66 px ampliado por un entero, sin márgenes.
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
    render().save("sprite_detalle.png")
    print("Guardado sprite_detalle.png")
