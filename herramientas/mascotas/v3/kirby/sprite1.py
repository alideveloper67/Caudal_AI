#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite1.py                 -> guarda sprite1.png
      from sprite1 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (247, 168, 198),
    "B": (236, 145, 181),
    "C": (26, 17, 18),
    "D": (232, 54, 79),
    "E": (224, 122, 164),
    "F": (168, 58, 104),
    "G": (184, 28, 58),
    "H": (26, 26, 74),
    "I": (255, 188, 209),
    "J": (242, 100, 138),
    "K": (254, 94, 105),
    "L": (122, 16, 40),
    "M": (252, 210, 226),
    "N": (255, 216, 74),
    "O": (156, 31, 58),
    "P": (58, 98, 224),
    "Q": (107, 79, 17),
    "R": (255, 255, 255),
    "S": (127, 166, 255),
    "T": (240, 90, 120),
    "U": (100, 101, 139),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...QQ.........................................",
    ".QQNNCQ.......................................",
    "QNNNNNNCF..............FF.....................",
    ".CCNNCCFACF.......FFFFFIACFFFF................",
    "...CCFAAAAAC....UFIIIIIIAAIIIACF..............",
    ".....FAAAAAAC.FUMMMAAAAAAAAAAAAACF............",
    ".....FAAAAAAECAMMMMAAAAAAAAAAAAABBC...........",
    ".....FAAAAAEFIMMMMMAAAAAAAAAAAAABBBC..........",
    ".....FAAAAEFIIMMMMAAAAAAAAAAAAAABBBBC.........",
    "......CAAEFIIAMMMAARHAAAAAARHAAABBBBBC........",
    "......FAEFIIAAAAAAHRHHAAAAHRHHAAABBBBEC.......",
    ".......CFIIAAAAAAAHHHHAAAAHHHHBBBBBBBBEC......",
    "........CIAAAAAAAAHHHHAAAAHHHHBBBBBBBBEC......",
    ".......FIIAAAAAAAAHPPHAAAAHPPHBBBBBBBBEEC.....",
    ".......FIAAAAAAAAAHPPHAAAAHPPHBBBBBBBBEEC.....",
    ".......FIAAAAAAAAAASSAAAAAASSBBBBBBBBBEEC.....",
    ".......FIAAAAAAAAAAAAAAAAAAAAABBBBBBBBBEC.....",
    ".......FIAAAJJJJJJAAAAAAAAAAAAJJJJJJEEEEC.....",
    "......FAIAAAJJJJJJAAAOAAAAOAAAJJJJJJEEEEEC....",
    ".......CAAAAAAAAAAAAAOOOOOOAABBBBBEEEECCCAC...",
    ".......FIAAAAAAAAAAAAAOTTOAABBBBBBBEECAAAAAC..",
    ".......FIAAAAAAAAAAAAAATTAABBBBBBBBEFAAAAAAEC.",
    ".......FIAAAAAAAAAAAAAAAAABBBBBBBBBBECAAAAAAC.",
    ".......FAAAAAAAAAAAAAAAABBBBBBBBBBBBBFAAAAAEEC",
    "........CAAAAAAAAAAAAABBBBBBBBBBBBBBEEFAAAEEC.",
    "........FBBBBBBAABBBBBBBBBBBBBBBBBBEEEECEEEC..",
    ".........CBBBBBBBBBBBBBBBBBBBBBBBBEEEECCCCC...",
    "..........CBBBBBBBBBBBBBBBBBBBBBBEEEEC........",
    "...........CBBBBBBBBBBBBBBBBBBBBEEEEC.........",
    "............CEBBBBBBBBBBBBBBBBEEEEEC..........",
    ".............CEBBBBBBBBBBBBBEEEEEEC...........",
    "..............CCEEEEEBBEEEEEEEEECC............",
    "............LLLLCEEEEEEEEEEEEECCLLL...........",
    "..........LLKKKKKCCCCCCEECCCCCKKKKDCLL........",
    ".........LKKKDDDDDDDDGCCCLKKKKDDDDDDKDCL......",
    "........LKKDDDDDDDDDDGC..LKDDDDDDDDDDDDGC.....",
    ".......LKKDDDDDDDDDDDGC.LDKDDDDDDDDDDDDDC.....",
    ".......LKDDDDDDDDDDGGGC..CDDDDDDDDDDDDDGGC....",
    ".......LDDDDDDDDDDGGCC...LGDDDDDDDDDDDDGC.....",
    "........CGGGDGGGGGGC......CCGGDDDDDDGGGGC.....",
    ".........CCCCGCCCCC.........CCCGGGGGGCCC......",
    ".............C.................CCCCCC.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (46, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 46x42).
    scale=int   -> sprite de 46x42 px ampliado por un entero, sin márgenes.
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
    render().save("sprite1.png")
    print("Guardado sprite1.png")
