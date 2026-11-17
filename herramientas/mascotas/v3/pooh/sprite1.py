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
    "A": (245, 181, 46),
    "B": (220, 142, 24),
    "C": (26, 22, 17),
    "D": (232, 162, 35),
    "E": (138, 74, 12),
    "F": (216, 35, 46),
    "G": (255, 212, 85),
    "H": (251, 211, 106),
    "I": (147, 73, 28),
    "J": (172, 20, 38),
    "K": (244, 228, 180),
    "L": (110, 12, 24),
    "M": (184, 105, 44),
    "N": (22, 16, 12),
    "O": (244, 138, 114),
    "P": (78, 36, 16),
    "Q": (245, 162, 16),
    "R": (138, 74, 22),
    "S": (122, 52, 16),
    "T": (255, 255, 253),
    "U": (94, 10, 20),
    "V": (216, 122, 8),
    "W": (208, 136, 72),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......EEEEE...............EEEEE...........",
    ".....EGGGGAC....EEEEEE...EDDDDBC..........",
    ".....EGAAAAACEEEGGGGGACEEEDDDDBBC.........",
    "....EGGABBAAAGGGGAAAAAAGGDDBBBBBC.........",
    "....EAABBBAAAAAAAAAAAAAAADDBBBBBC.........",
    ".....CAABAAAAAAAAAAAAAAAADDDBBBC..........",
    ".....EBAAAAAAAAAAAAAAAAAADDDBBC...........",
    "......CCAADDRRRDDDAAAAARRDDDDBC...........",
    "......EGGDDDDDAADDDAAAAAADDDDBC...........",
    "...E..EGADDDDDNDDDDDAAANADDDDBBC..........",
    ".EEACEGGDDDDDTTNDDDDDAATNDDDDBBC..........",
    "EGGGACGAADDDDNNNBDDBBBNNNDDDDBBC..........",
    "EGAAAEGAADDDDNNNBBDDBBBNNDDDDBBC..........",
    "EGAAAEGAAADDDBBBHHHCCHHHDDDDDBBC..........",
    "EAAABEGAAAADBBBHHHCCCCHHHDDDBBBC..........",
    ".CAABCAAAOOOOBBHHHHCCHHHHOOOOBBC..........",
    ".EGAACCDDOOOABHHHHHHHHHHAAOOOBC...........",
    ".EAAABCDDDDDDDBHHSHHHHSHADBBBBC...........",
    "..CAAACCDDDDDDDAHHSSSSAAABBBBC............",
    "..EAAAACCBDDDDDDDAAAAAABBBBBC.............",
    "...CAAAACCBBBDDDDDDDBBBBBBBCU.............",
    "...EAAABEFFFBBBBBBBBBBBBBJJFFC............",
    "....CABEFFFFFFFBBBBBBBFFJJCCJJC...........",
    ".....CEFFFFFFFFFFFFFFFFFFEGACCC..EEE......",
    "......CFFFFFFFFFFFFFFFFFFFEAAAACEQQQCEE...",
    "......UFFFFFFFFFFFFFFFFFFFFEAAAEEQQQQQVC..",
    "......UJJJJJJJJJFFFFJJJJJJJJEAAACEEEQVECC.",
    ".....LJCCCCCCCCCCJJJJCCCCCCCCCAAACPPCEPPC.",
    "......CCLLLLLLLLFCCCCJLLLLLLLCAAABECCECCC.",
    ".......EGGGGGGGALLLLLLGGGGBBBEEAAEPPEPWIIC",
    ".......EGAAAAAAAAGGGGGGAAABBBCCEEKKKKKPIIC",
    ".......EGAAAAAAAAAAAAAAAAABBCWPKKKKKKKKCIC",
    ".......EAAAAAAAAAAAAAAAAAABBCMPKRKRKRKKCIC",
    "........CAAAAAAAAAAAAAAAABBBCMPKKKKKKKKCIC",
    "........EBAAAAAAAAAAAAAABBBBCMMCCCCCCCCIIC",
    ".........CBAAAAAAAAAAABBBBBCCMMMMMMMMIIIIC",
    "........EACCBBBAAAABBBBBBBCAEPMMMMMMIIIIC.",
    ".......EAAAACBBBBBBBBBBBCCAAACCIIIIIIIIC..",
    ".......EAAAAACCCCBBBBCCCAAAABBCCIIIIIIC...",
    ".......EBAAAABBBCCCCCBAAAAABBC..CCCCCC....",
    "........CCBBBBCC.....CCBBBBBC.............",
    "..........CCCC.........CCCCC..............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (42, 42)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 42x42).
    scale=int   -> sprite de 42x42 px ampliado por un entero, sin márgenes.
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
