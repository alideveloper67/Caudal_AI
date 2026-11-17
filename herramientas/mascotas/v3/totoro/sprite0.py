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
    "A": (123, 130, 143),
    "B": (106, 112, 128),
    "C": (140, 148, 158),
    "D": (241, 230, 198),
    "E": (17, 20, 26),
    "F": (228, 214, 179),
    "G": (60, 66, 80),
    "H": (214, 199, 160),
    "I": (58, 42, 48),
    "J": (253, 253, 246),
    "K": (170, 178, 188),
    "L": (255, 247, 224),
    "M": (92, 184, 74),
    "N": (30, 90, 30),
    "O": (22, 25, 34),
    "P": (60, 146, 52),
    "Q": (17, 26, 17),
    "R": (47, 122, 44),
    "S": (46, 48, 56),
    "T": (255, 255, 255),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".............GG.......NNNNN...GGG.............",
    "............GCCE....NNMMMMPQ.GCCBE............",
    "............GCCCE..NMMMMRPPQGCCCBE............",
    "...........GCCCCBE.NMRRPPPQ.GCCCBE............",
    "...........GCCCCBE.NPMMPQQ.GCCCCBE............",
    "...........GCCCCBEGGEKRRQGGGGCCCBE............",
    "...........GCCBGGKKKKKCCCKKKAGGCBE............",
    "...........GCBGKKKCCCCCCCCCCAAAGBE............",
    "............EGKKCCCCCCCCCCCCCAAAGE............",
    "............GKKCCCCCCCCCCCCCCAAAAE............",
    "...........GKKCCCCCCCCCCCCCCCAAAABE...........",
    "..........GKKCCJJJJCCCCCCCCCJJJJAABE..........",
    ".......OO.GAAAAJJEEJACCCCCCJJEEJAAAE...O......",
    "......OGGEAAAAJJEEEJAASSSCCJEEEJJAABEOOGE.....",
    ".......EEGGAAAAJEEEJAAAACCCJJEEJAAABGGEE......",
    "........GAAAAAAJJJJAAAAAACCCJJJJAAAABE........",
    "........GAAAAAAAAAAAAAAAAACCCCCCAAAABEOO......",
    ".......OGGGGAAAAAAAAAAAAAAACCCIIAAAGGGGGE.....",
    ".......GAAAAAAAAIIIITIIIIITTIIICCAAAABEE......",
    ".......GAAGGAAAABBIIIIIIIIIIIICCCAAGGGCE......",
    "......OGGAAAAAABBBBBIIIIIIIIBACCCAAAAAGGE.....",
    ".....GGAAAAAABBBBBLLLDDDDDDDDDBCCAAAAABBEG....",
    "....GGAAAAAABBBBBLLDDDDDDDDDDDFBCAAAAAABECE...",
    "...GCGAAAAAABBBLLLDDDDDDDDDDDDDFFAAAAAABGCBE..",
    "..GCCGAAAAABBBLLDDDDDDDDBDDDDDDFFHAAAAABBECE..",
    ".GCCBGAAAAABBBLDDDBBDDDBBBDDDBBFFFHAAAAABECBE.",
    ".GCCGAAAAABBBLLDDBDDBDBBDBDDBDDBFFHAAAAABGCCE.",
    ".GCCGAAAAABBBLDDDDDDDDDDDDDDDDDFFFFHAAAABBECBE",
    "GCCCGAAAAABBLLDDDDDDDDDDDDDDDDDFFFFHAAAABBECBE",
    "GCCCGAAAABBBLDDBBDDDDBBDDDBBDDFBBFFHHAAABBECBE",
    "GCCBGAAAABBBLDBBDBDDBDBBDBDBBFBFFBFHHAAABBECBE",
    "GCCGAAAAABBLLDDDDDDDDDDDDDDFFFFFFFFHHAAABBECBE",
    "GCCGAAAAABBFFFDDDDDDDDDDFFFFFFFFFFFHHAAABBEBBE",
    ".EBGAAAAAABFFFFFFFFFFFFFFFFFFFFFFFHHHAAABBEBE.",
    "..EEEAAAAAAFFFFFFFFFFFFFFFFFFFFFFHHHHAAABBEE..",
    "....GAAAAAAAHHFFFFFFFFFFFFFFFFFHHHHHAAABBBE...",
    "....GAAAAAAABHHHHHFFFFFFFFFFHHHHHHHAAABBBBE...",
    ".....EBBABBBBBBBHHHHHHHHHHHHHHHHHBBBBBBBBE....",
    "......EBBBBBBBEEBBCCHHHHHHHHHHEEEBBBBBBBE.....",
    ".......EEEBEEECCEEECCCCCCCCBEECCCEEEEEEE......",
    "..........ECCCCCCCGBBBBBBBBBECCCCCCBE.........",
    "..........GBCCCCBBBEEEEEEEEEBCCCCBBBE.........",
    "...........EEBBBBEE.........EEBBBBEE..........",
    ".............EEEE.............EEEE............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (46, 44)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 46x44).
    scale=int   -> sprite de 46x44 px ampliado por un entero, sin márgenes.
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
