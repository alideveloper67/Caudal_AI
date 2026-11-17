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
    "W": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................BBBBDDDDDD................................................",
    "..................BBBBDDDDDD................................................",
    "..............BBBBAAAAAAAAAADDDD............................................",
    "..............BBBBAAAAAAAAAADDDD............................................",
    "............BBEEAAAAAAAAAAAAAAAACC..........................................",
    "............BBEEAAAAAAAAAAAAAAAACC..........................................",
    "..........BBEEEEEEAAAAAAAAAAAAAACC..........................................",
    "..........BBEEEEEEAAAAAAAAAAAAAACC..........................................",
    "..........BBEEEEEEAAAAAAAAAAAAAAAACC........................................",
    "..........BBEEEEEEAAAAAAAAAAAAAAAACC........................................",
    "........BBAAAAEEAAAAAAAAAABBAAAAAACC........................................",
    "........BBAAAAEEAAAAAAAAAABBAAAAAACC........................................",
    "........BBAAAAAAAAAAAAAABBAAAAAAAABBCC......................................",
    "........BBAAAAAAAAAAAAAABBAAAAAAAABBCC......................................",
    "........JJBBAAAAAAAAAAAABBAAJJJJBBBBCC......................................",
    "........JJBBAAAAAAAAAAAABBAAJJJJBBBBCC......................................",
    "........KKBBAAAAAAAAAAAAAAJJJJJJDDBBCC......................................",
    "........KKBBAAAAAAAAAAAAAAJJJJJJDDBBCC......................................",
    "..........AAAAAAAAAAAAAAAAWWCCKKDDBBCC......................................",
    "..........AAAAAAAAAAAAAAAAWWCCKKDDBBCC......................................",
    "........CCAAAAAAAAAAAAAAAAWWJJLLDDBBCC..........................GG..........",
    "........CCAAAAAAAAAAAAAAAAWWJJLLDDBBCC..........................GG..........",
    "......DDJJAAAAAAAAAAAAAAAADDKKLLBBBBCC..........................GGHH........",
    "......DDJJAAAAAAAAAAAAAAAADDKKLLBBBBCC..........................GGHH........",
    "......DDEEEEEEAAAAAAAAAAAAAABBBBBBBBCC..........................GGHH........",
    "......DDEEEEEEAAAAAAAAAAAAAABBBBBBBBCC..........................GGHH........",
    "......DDEEEEAAAABBAAAAAAAABBBBDDBBBBCC........................GGIIHH........",
    "......DDEEEEAAAABBAAAAAAAABBBBDDBBBBCC........................GGIIHH........",
    "........DDAAAAAAAAAAAAAABBDDDDBBBBCC............DDDD..........GGHHHHII......",
    "........DDAAAAAAAAAAAAAABBDDDDBBBBCC............DDDD..........GGHHHHII......",
    "........CCCCAAAAAAAADDDDCCWWBBBBBBCC....DDDDDDDDBBCC..........GGIIHHHHGG....",
    "........CCCCAAAAAAAADDDDCCWWBBBBBBCC....DDDDDDDDBBCC..........GGIIHHHHGG....",
    "..DDDD......CCCCCCCCGGGGDDBBBBBBBBDDDDDDAAAAAAAABBCC..........GGHHGGHHII....",
    "..DDDD......CCCCCCCCGGGGDDBBBBBBBBDDDDDDAAAAAAAABBCC..........GGHHGGHHII....",
    "..CCBBDDDDDDCCBBBBDDDDDDBBBBCCBBBBAAAAAAAAAAAABBBBBBCC......GGGGGGGGHHHHGG..",
    "..CCBBDDDDDDCCBBBBDDDDDDBBBBCCBBBBAAAAAAAAAAAABBBBBBCC......GGGGGGGGHHHHGG..",
    "..CCBBAAAAAABBCCCCAAAABBCCCCBBBBBBBBAAAABBBBBBBBCCCC........GGGGIIGGGGHHIIGG",
    "..CCBBAAAAAABBCCCCAAAABBCCCCBBBBBBBBAAAABBBBBBBBCCCC........GGGGIIGGGGHHIIGG",
    "CCBBBBBBAAAABBBBBBCCCCCCBBBBBBBBBBBBBBBBBBBBBBCC............GGHHHHGGHHHHHHGG",
    "CCBBBBBBAAAABBBBBBCCCCCCBBBBBBBBBBBBBBBBBBBBBBCC............GGHHHHGGHHHHHHGG",
    "..CCCCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBCCCC..............GGIIHHHHHHHHHHGG",
    "..CCCCBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBCCCC..............GGIIHHHHHHHHHHGG",
    "......CCCCBBBBBBBBDDBBFFFFFFBBBBBBBBDDDDCC..................GGIIIIIIHHHHIIGG",
    "......CCCCBBBBBBBBDDBBFFFFFFBBBBBBBBDDDDCC..................GGIIIIIIHHHHIIGG",
    "..........CCCCBBBBDDFFFFFFFFFFBBBBAAAACC......................GGIIGGIIIIGGGG",
    "..........CCCCBBBBDDFFFFFFFFFFBBBBAAAACC......................GGIIGGIIIIGGGG",
    "..............CCDDBBEEEEEEEEEEFFAAAAAACC........................GGGGDDGGGG..",
    "..............CCDDBBEEEEEEEEEEFFAAAAAACC........................GGGGDDGGGG..",
    "................DDFFEEEEEEEEEEEEAAAAAABBCC........................DDDDGG....",
    "................DDFFEEEEEEEEEEEEAAAAAABBCC........................DDDDGG....",
    "................DDEEEEEEEEEEEEEEAAAAAAAACC........................DDEECC....",
    "................DDEEEEEEEEEEEEEEAAAAAAAACC........................DDEECC....",
    "................DDEEEEEEEEEEEEEEAAAAAAAAAACC......................DDAACC....",
    "................DDEEEEEEEEEEEEEEAAAAAAAAAACC......................DDAACC....",
    "..............DDFFEEEEEEEEEEEEEEFFAAAAAAAACC....................DDAAAACC....",
    "..............DDFFEEEEEEEEEEEEEEFFAAAAAAAACC....................DDAAAACC....",
    "..............DDEEEEEEEEEEEEEEEEEEAAAAAAAACC................DDDDAAAABBCC....",
    "..............DDEEEEEEEEEEEEEEEEEEAAAAAAAACC................DDDDAAAABBCC....",
    "............DDDDEEEEEEEEEEEEEEEEEEBBAAAAAAAACC........DDDDDDAAAAAABBCC......",
    "............DDDDEEEEEEEEEEEEEEEEEEBBAAAAAAAACC........DDDDDDAAAAAABBCC......",
    "..........DDAABBFFEEEEEEEEEEEEEEFFBBAAAAAAAABBCCDDDDDDAAAAAAAAAABBFFCC......",
    "..........DDAABBFFEEEEEEEEEEEEEEFFBBAAAAAAAABBCCDDDDDDAAAAAAAAAABBFFCC......",
    "..........DDAAAABBFFEEEEEEEEFFFFBBAAAAAAAAAAAACCBBBBBBBBAAAABBFFFFCC........",
    "..........DDAAAABBFFEEEEEEEEFFFFBBAAAAAAAAAAAACCBBBBBBBBAAAABBFFFFCC........",
    "........CCAAAAAADDFFFFFFFFFFFFFFBBAAAAAAAAAAAABBCCBBBBBBBBBBFFFFCC..........",
    "........CCAAAAAADDFFFFFFFFFFFFFFBBAAAAAAAAAAAABBCCBBBBBBBBBBFFFFCC..........",
    "........CCAAAAAAAACCFFFFFFFFFFFFBBAAAAAAAAAABBBBCCBBBBBBFFFFFFCC............",
    "........CCAAAAAAAACCFFFFFFFFFFFFBBAAAAAAAAAABBBBCCBBBBBBFFFFFFCC............",
    "........CCAAAAAAAABBCCFFFFFFFFFFDDBBAAAAAABBBBBBCCFFFFFFFFCCCC..............",
    "........CCAAAAAAAABBCCFFFFFFFFFFDDBBAAAAAABBBBBBCCFFFFFFFFCCCC..............",
    "..........CCAAAABBBBBBCCCCFFFFFFDDBBBBBBBBBBBBBBCCFFFFDDDD..................",
    "..........CCAAAABBBBBBCCCCFFFFFFDDBBBBBBBBBBBBBBCCFFFFDDDD..................",
    "............CCBBBBBBBBBBBBCCCCCCCCDDBBBBBBBBBBCCDDDDDD......................",
    "............CCBBBBBBBBBBBBCCCCCCCCDDBBBBBBBBBBCCDDDDDD......................",
    "............CCBBBBBBBBCCCC..........DDBBBBBBBBCC............................",
    "............CCBBBBBBBBCCCC..........DDBBBBBBBBCC............................",
    "..........CCBBBBBBBBBBCC............DDAAAAAABBCC............................",
    "..........CCBBBBBBBBBBCC............DDAAAAAABBCC............................",
    "........CCWWDDWWBBBBCC..............DDBBAAAAAABBCC..........................",
    "........CCWWDDWWBBBBCC..............DDBBAAAAAABBCC..........................",
    "..........CCCCCCCCCC..................CCWWDDWWDDWWCC........................",
    "..........CCCCCCCCCC..................CCWWDDWWDDWWCC........................",
    "........................................CCCCCCCCCC..........................",
    "........................................CCCCCCCCCC..........................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (76, 84)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 76x84).
    scale=int   -> sprite de 76x84 px ampliado por un entero, sin márgenes.
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
