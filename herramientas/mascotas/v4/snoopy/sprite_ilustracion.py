#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite_ilustracion.py                 -> guarda sprite_ilustracion.png
      from sprite_ilustracion import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (251, 246, 244),
    "B": (20, 17, 17),
    "C": (220, 206, 209),
    "D": (37, 32, 35),
    "E": (24, 22, 28),
    "F": (46, 41, 44),
    "G": (246, 239, 238),
    "H": (232, 224, 224),
    "I": (225, 215, 216),
    "J": (24, 22, 28),
    "K": (24, 22, 28),
    "L": (200, 193, 194),
    "M": (239, 231, 231),
    "N": (24, 22, 28),
    "O": (57, 52, 55),
    "P": (118, 25, 31),
    "Q": (24, 22, 28),
    "R": (202, 28, 42),
    "S": (24, 22, 28),
    "T": (24, 22, 28),
    "U": (24, 22, 28),
    "V": (24, 22, 28),
    "W": (246, 53, 56),
    "X": (61, 19, 22),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...........................................BBBB........................",
    "......................................BBBBBBBBBB.......................",
    "......................................BBBBBBJJJBBBB....................",
    "..................................BBBBBJJJJAAAABBBBBBB.................",
    "..................................BBBBBAAAAAAAAACCBBBB.................",
    "..............................BBBBBMMMAAAAAAAAAAAABBBBBB...............",
    "..............................BBBBAAAAAAAAAAAAAAAAAMMBBB...............",
    "............................BBBBHHAAAAAAAAAAAAAAAAAAABBBBB.............",
    "............................BBBBAAAAAAAAAAAAAAAAAAAAACCBBB.............",
    "..........................BBBBAASBBAAAAAAAAAAAAAAAAAAACCBBBB...........",
    "..................BBBBBBBBBBBAASJJJAAAAAAAAAAAAAAAAAAAMCCJBB...........",
    ".............BBBBBBBBBBBBBBBAAAJJAAAAAAAAAQQAAAAAAAAAAMCCJBB...........",
    ".............BBBBBLLLLLLLLLLAAAAAAAAAAAAAANNQAAAAAAAAAAAAJBB...........",
    "..........BBBBKKKLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHIIBBB.........",
    "..........BBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAAAAAAAHIIJBB.........",
    ".......BBBBLLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAAAAAAAAAAMJBB.........",
    ".......BBBBAAAAAAAAAAAAAAAAAAAABBSAAAAAAAAAAAAAAAAAAAAAAAAMCJBBB.......",
    ".....BBBCCAAAAAAAAAAAAAAAAAAAABBBSAAAAAAAAAAAAAAAAAAAAAAGGGGCBBB.......",
    ".....BBKAAAAAAAAAAAAAAAAAAAAAABBBSAAAAATTAAAAAAAAAAAAAAABBBCCCSBBB.....",
    "....BBKAAAAAAAAAAAAAAAAAAAAAAABBBAAAAABBBAAAAAAAAAAAGGABBDDECCCSBB.....",
    "...BBJAAAAAAAAAAAAAAAAAAAAAAADBBUAAAAJBBBVAAAAAAAAAIHJBBBEEEECCSBB.....",
    "...BBJAAAAAAATTTTTAAAAAAAAAAADBBUAAAAJBBBVAAAAAAAGICHJBBOEEEECCCCOBB...",
    "..BBKAAAAAAAUUUTDDAAAAAAAAAAADBBTAAAABBBBVAAAAAAAGCIBBBOEEEEEECCCOBB...",
    ".BBKAAAAAAAAAAATEEDUAAAAAAAAAAATAAAAGBBBBAAAAAAAAGCCSBBOEEEEEEECCOBB...",
    ".BBKAAAAAHBAAAAFEEDDUAAAAAAAAAAAAAAAGBBBBAAAAAAACCHSBBBOEEEEEEEEEDBB...",
    ".BBKAAAAAHBBEEFFFFBBQAAAAAAAAAAAAAAAGBBBBAAAAAAACHABBBBOEEEEEEUUEDBB...",
    "BBBAAAAAAHBBBBBBBBBBQAAAAAAAAAAAAAAAABBBAAAAAAAACHABBFFOEEEEETNNEEEBB..",
    "BBIAAAAAAHBBBBBBBBBBAAAAAAAAAAAAAAAAAAJJAAAAAAAAHASBBEEEEEEEETNNEEEBB..",
    "BBIAAAAAAAABBBBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAIIASBBBEEEEEEUUNNNEEEBB..",
    "BBIAAAAAAAAABBBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAIIASBBBEEEEEENNNNNEEEBB..",
    "BBIAAAAAAAAAAHHHHHAAAAAAAAAAAAAAAAAAAAAAAAAAACCIASBBBEEEEEENNNNNEEEDDBB",
    "BBCGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCIASBBBEEEEEENNNVEEEFDDBB",
    "BBBCCGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASAAAAAAACCLBBBBEEEEEEENNNVEEEFDDBB",
    "BBBCCMGAAAAAAAAAAAAAAAAAAAAAAAAAAAAASBBJAAAACCMLBBBBEEEEEEEQQQEEEEFDDBB",
    "..BQCCMAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBJAAAMCCMLBBBBEEEEEEEEEOOOEEFFDBB",
    "..BQCCCHHAAAAAAAAAAAAAAAAAAAAAAAAAAABBBJAAAMCCMLBBBDEEEEEEEEODDDEEFDDBB",
    "..BQCCCCHAAAAAAAAAAAAAAAAAAAAAAAAAABBBBAAAAMCCCBBBBDEEEEEEEEODDDFFFDDBB",
    "...BBCCCCIIAAAAAAAAAAAAFAAAAAAAAAAABBBGAAAACCCDBDDDDEEEEEEEEODDDDDDDDBB",
    "...BBBCCCCCIGGGGAAAAAAAFBBAAAAAAAABBBGAAAACCCCDBDDDDDDOEOFFFFDDDDDDDDBB",
    "....BDDCCCCCCCCIAAAAAAAABBBBJJJJABBBAAAAAACCCCDBDDDDDDOEODDDDDDDDDDBBBB",
    ".....BBBBBCCCCCIMMMMMAAAAABBBBBBJAAAAAAAAACCCCDBDDDDDDOODDDDDDDDDDDBB..",
    ".......BBBBCCCCCCCCCCMAAAAAJJJJJJAAAAAAAACCCCCDBDDDDDDDDDDDDDDDDDDDBB..",
    "........BBBBBCCCCCCCCCHHHAAAAAAAAAAAAAAACCCCCBBBBBDDDDDDDDDDDDDDDBBBB..",
    "..........BBBBKKKKCCCCCCCHMMGAAAAAAAAACCCCJJBBBBBBDDDDDDDDDDDDDDDBB....",
    ".............BBBBBCCCCCCCCCCMGGGGGGGGCCCCCBBB...BBDDDDDDDDDDDDDBBBB....",
    ".............BBBBBBOOOOOOCCCCCCCCCCCCCCJOOBBB...BBDDDDDDDDDDDDDBBBB....",
    "..................BBBBBBBBCCCCCCCCCCCCJBBBB.....BBBBBDDDDDDDBBBBB......",
    ".........................BBQQCCCCCCCCBBB..........BBBDDDDDDBBBBBB......",
    "..........BBBBB..........BBBBCCCCCCCBBBB..........BBBBBBBBBBBBB........",
    "........BBBKKKBB........BBBBBCCCCCCBBBB..............BBBBBBB...........",
    "........BBJAAAUB.......BBPPBVVVVVVVPBPPBB..............................",
    "......BBBBJAAAUB.......BBWWPPPPPPPPPPRRPB.......BBBBB..................",
    ".....BDJJJAHAAAADBBB...BBRRWWWWWWRRRRRRPB......BBNNNBB.................",
    ".....BDAAAAHAAAAADDDB..BBBRRRRRRRRRRRPXXB.....BBBAAATB.................",
    ".....BDAAAAAAAAAAAABBBBBBBPPPRRRRRPPPXBBBBBBBBBBAAAATBBB...............",
    ".....BDAAAAAAAAAAAAAKKKBBBBBBPPPPPBBBUBBBBBBBBBAAAAAAKKBB..............",
    ".....BBVVAAAAAAAAAAAAAABBTTTBBBBBBBBUBBBLLLLLLAAAAAAAAAVB..............",
    "......BBBAAAAIIAAAAAAAABBAAAAIIIIIBBBAAAAAAAAAAAAAAAAAAVB..............",
    "......BBKAAAICCHHHAAAAKBAAAAAAAAAAAAAAAAAAAAAAAAAAAAGHHVB..............",
    "......BBKHHISSCCCCMMMKBJAAAAAAAAAAAAAAAAAAAAAAAGGAAAGGBBB..............",
    "........BKKKBBBLLCCCCBBJAAAAAAAAAAAAAAAAAAACCCCCCGAAAKBB...............",
    "........BBBBB.BBBBCCBBBGAAAAAAAAAAAAAAACCCCCCCLCLCAAAKBB...............",
    "...............BBBBBBBGAAAAAAAAAAAAAGCCCLLLLLLBBBLCAABB................",
    "..................BBBBGAAAAAAAAAAAAAGCCLBBBBBBBBBBNNBB.................",
    "...................BTAAAAAAAAAAAAAAAAGGCDDBBBBB..BBBB..................",
    "...................BTAAAAAAAAAAAAAAAAAAFDDB............................",
    ".................BBBAAAAAAAAAAAAAAAAAAKFFDDB...........................",
    ".................BBHAAAAAAAAAAAAAAAAAAKFFFDBB..........................",
    ".................BBHAAAAAAAAAAAAAAAAAAKFFFFDBB.........................",
    ".................BBHAAAAAAAAAAAAAAAAAAKFFFFFDB.........................",
    ".................BBHAAAAAAAAAAAAAAAAAAKFFFFFDB.......BBBBB.............",
    ".................BDHGGAAAAAAAAAAAAAAAAAAFFFFDB.......BBBBB.............",
    "................BDCCCCGAAAAAAAAAAAAAAAAAAFFFDB.....BBBAJBB.............",
    "................BDCCCCGAAAAAAAAAAAAAAAAAAFFFDB....BBBAAJBB.............",
    "................BDCCCCCIIHAAAAAAAAAAAAAAAAJJBBBBBBBBAAABBB.............",
    "................BBBCCCCCCHAAAAAAAAAAAAAAAAAABBBBBBAAAGCSBB.............",
    ".................BBSCCCCCCIIIIAAAAAAAAAAAAACNBLHHMAAGCSBB..............",
    ".................BBSCCCCCCCCCIAAAAAAAAAAAMCCNBLIMAAHABBB...............",
    ".................BBBBCCCCCCCCCIIIIIGAAAAAMCCCDCCIHHABBB................",
    "...................BBBCCCCCCCCCCCCCGAAAAACCCDCCCCCCBBB.................",
    "...................BBBBIIICCJJCCCCCGAAAAACCDBEEEOOOBB..................",
    ".....................BQAAACCSCCQQCCIIAAAACBBBBBBBBB....................",
    "....................BBQAAACCCSBBBCCCCAAAICBB...........................",
    "...............BBBBBBBQAAACCCCBBBCCHHAAAICBB...........................",
    "............BBBKKKKKKBQAAACCCCCBBBCHAAAAICBBBBB........................",
    "............BBAAAAAAAAAAAAIICCCBBBGGAAAAAAMMHHBBBB.....................",
    "..........BBCAAAAAAAAAAAAAAGCCCDBAAAAAAAAAAAAAAKKBBB...................",
    "..........BBCAAAAAAAAAAAAAAGCKBDAAAAAAAAAAAAAAAAALBB...................",
    ".........BBBAAIIAAAAAAAAAAGHCKBFAAAAAAAAAAAAAAAAALEB...................",
    "........BBVAAATAAAAAAAAAAAHCCKBFAAAAAAAAAAAAAAAAAAAEB..................",
    "........BBVAAATAAAAQAAAAAAHCCKBFHHGAAAAAEAAAAAAAAAGEB..................",
    "........BBVGGANAAAQTAHHHHHCCCBBFCCGAAAAAEAAAAAUUAGCEB..................",
    "........BBBCCBNGGGQTCCCCCCCCBBBFCCIIIIMAQQAHHHUUIICBB..................",
    "..........BBBBBCCFFFCCCCCCCBBB.BBCCCIIMAQQCCCCUBFFBB...................",
    "..........BBBBBFFFBBFFFFFFBBB..BBBBBOOBBBBUUUUBBFFBB...................",
    "............BBBBBBBBBBBBBB.......BBBBBBBBBBBBBBBBB.....................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (71, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 71x96).
    scale=int   -> sprite de 71x96 px ampliado por un entero, sin márgenes.
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
    render().save("sprite_ilustracion.png")
    print("Guardado sprite_ilustracion.png")
