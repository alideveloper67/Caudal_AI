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
    "A": (250, 239, 243),
    "B": (26, 18, 17),
    "C": (0, 0, 0),
    "D": (236, 19, 98),
    "E": (227, 201, 210),
    "F": (14, 10, 9),
    "G": (120, 48, 25),
    "H": (184, 6, 76),
    "I": (46, 25, 24),
    "J": (75, 18, 32),
    "K": (58, 50, 50),
    "L": (114, 103, 104),
    "M": (165, 147, 152),
    "N": (130, 119, 121),
    "O": (242, 119, 158),
    "P": (129, 11, 55),
    "Q": (201, 187, 191),
    "R": (181, 168, 172),
    "S": (148, 135, 138),
    "T": (184, 93, 84),
    "U": (89, 40, 24),
    "V": (153, 73, 59),
    "W": (77, 67, 67),
    "X": (94, 85, 85),
    "Y": (241, 59, 130),
    "Z": (221, 119, 118),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "............................................CCCCCCCCC............................",
    "...........................................CCFFFFFFFCC...........................",
    "..........................................CCFFBBBBBBCCC..........................",
    ".........................................CCCBBBBJJJIBFC..........................",
    "........................................CCFBIBVVVGGIBFC..........................",
    ".......................................CCFBBITZVZGGIBFC..........................",
    "......................................CCCBBBBVTZGGGIBFC..........................",
    "......................................CBBIIVOOVGGGGIBFC..........................",
    "....................................CCCBBIVTZZVGGGGIBFC..........................",
    "....................................CFFBITTTGGGGGGUIBFC..........................",
    "....................................CFBJGTTTGGGGGUBBCCC..........................",
    "...................................CCFBJGGGGGGGGGUBBCC...........................",
    "..................................CCFBBGGGGGGGGGGBBBCC...........................",
    "..................................CFBIGTGVGGGGGGIBFCCCCCCC.......................",
    "..................................CFBIGTVVGGGGGUIBFCBBBBCCC......................",
    "..................................CFBIGVVGGGGGUBBFFFBBBBBFCCCC...................",
    "..................................CFBIGGGGGGGUBBBFBBXEENBBFFFCC..................",
    "..................................CFBIGGGGGGUBBBBBBBXAANBBBBBCCC.................",
    "..................................CFBIGGGGGIBBBMMBBBKAAABKNNBBFC.................",
    ".................................CCFBIGUUUUIBBBAAANKBIAAKAAABBFC.................",
    ".................................CCFBIUBBBBBBBIWWNAABIARRAABBBFC.................",
    "...............................CCCBBBBBBBNNNNNLIWWAAKKAAAABBBCCCCC...............",
    ".............................CCCBBBKKKKKAAAAAAALLAAAAAAAABBBBBBBFCC..............",
    ".............................CFFBBBKAAAAAAAAAAAAAAAAAAAANBBBBBBBFFC..............",
    "...........................CCCFBBSSAAAAAAAAAAAAAAAAAAAAANBBSSSSBBBC..............",
    "..........................CCCBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBC..............",
    "..........................CFBBBEEAAAAAAAAAAAAAAAAAAAAAAAAAAAXXXBFFC..............",
    ".........................CCFBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBFCC..............",
    ".........................CFBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBFFCC...............",
    "........................CCFBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBFCCC...............",
    "........................CFBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWBBCCC...............",
    "........................CFBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWBBFC...............",
    "........................CFBKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQBBFC...............",
    ".......................CCFBKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQBBFCC..............",
    "..............CCCCCCCCCCBBBKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEQBBBCC..............",
    ".............CCFFBBBBFCCBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEKBCC..............",
    "............CCFBBBBBBBFCBBEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEKBCC..............",
    "...........CCFBBBSSSNBBFBBEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEBBCCCC............",
    "...........CFFBBAAAAANBBBBEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEBBFFFFCC...........",
    "...........CBBBAAAAAAABBSAAAAAAAMMAAAAAAAAAAAAAAAAAAAAAAAAAEENBBBBBBFCCCC........",
    ".........CCCBBRAAAAAAABBSAAAAAAAMMAAAAAAAAAAAAAAAAAAAAAAAAAEENBIIIIIBBFCC........",
    ".........CFFBBRAAAAAQBBBAAAAAAAABMAAAAAAAAAAAAAAAAAAAAAAAAEEENBJGGGBBBBFCCCC.....",
    ".........CFBBBAAAAAAQBWAAAAAAAAKBBBAAAAAAAAAAAAAAAAAAAAAAAEEENBJGGGGVUBBBBFCC....",
    ".........CFBLAAAAAAARBWAAAAAAAAKBBBAAAAAAAAAAAAAAAAAAAAAAAEEENBJGGGGGVUBBBBFCC...",
    ".........CFBLAAAAEEERBWAAAAAAAAABBAAAAAAAAAAAAAAAAAAAAAAAAEEEBBBGGGTTGVVGUBBCCC..",
    ".........CFBLAAAEEEERBWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEEBBBGGGGGGTTTGUBBCC..",
    ".........CFBLAEEEEXXBBBBAAAAAAAAAAAAAAAKKAAAAAAAAAAAAAAAEEEEBBFBIGGGGGGTTTGUBBCCC",
    ".........CFBXEEEEBBBBBBBAAAAAAAAAAAAAABBBKAAAAAAAANAAAAAEEEEBBFFBIGGGGGGTTTGIBCCC",
    ".........CFBXEEBBBPPPPBBBAAAAAAAAAAAAABBBAAAAAQBBBNAAAAEEEEWBFCCFBIUGGGGGTGGUIBFC",
    ".........CFBBBBBIIDDDDPBBBAAAAAAAAAAAAASSAAAAAQBBBAAAAAEEEWBFCCCCBBUGGGGGGGGGUBFC",
    ".........CFBBBBBDDYOODDDBILAAAAAAAAAAAAAAAAAAAABBBAAAAEEEQBBFC..CBBBBGGGGGGGGUBFC",
    ".........CCFBBBHDDYOODDDDIBLAAAAAAAAAAAAAAAAAAAAEEAAAAEEQBBBCC..CCFBBGGGGGGGGUBFC",
    ".........CCCBBHDYOODDDDDDDBBAAAAAAAAAAAAAAAAAAAAAAAAAAAEBBBFCC..CCCFFBIGGGGGGBBFC",
    "...........CBBHDDYYDDDDDDHHJBLLAAAAAAAAAAAAAAAAAAAAAAAEEBBFCC.....CCFBBIIIIIBBFFC",
    "...........CBBHDDDDDDDDDDDDJBBBBBAAAAAAAAAAAAAAAAAAAAAEEBBCC.......CCCFBBBBBBBCCC",
    "...........CBBHDDDDDDDDDDDDJBBBBBXAAAAAAAAAAAAAAAAAAAEEEBBFC.........CCFFFFFFCC..",
    "...........CBBBHDDDDDDDDDDDJBBQBBXEAAAAAAAAAAAAAAAAAEEEBBFCC.........CCCCCCCCCC..",
    "...........CFFBHHDDHHHHHDDDDJBQRRAAEAXXXAAAAAAEEEEEEEEEBBCCCCC...................",
    "...........CCFBIHHHHHJHHDDDDDBBRAAAAABBBXLLLAEEEEEEEWWBBBBBBFCC..................",
    "............CFBIHHHPPBJJDDDDDJJBRRAAAQQBBBBBBMMMMMMBBBBBBBBBBFCC.................",
    "............CCCBBHHBBBHDDDDDDDDBBBRAAAALRRBBBBBBBBBBBBBAAABBBBFCC................",
    ".............CCBBJJBBHDDYYDDDDDPPBBLLLLLLLBBBJJJJJJBBBEAAAABBBBFC................",
    "..............CCFBBBHDDDOODDDDDDDPBBBBBBBBHHHDDDDDDBBBEAAAAABBBBC................",
    "..............CCFBBDDYOOOODDDDDDDDHHHHHHHHHDDDDDDDDDBBBAAAAAEMBBC................",
    ".............CCBBBDDDYOOOODDDDDDDDDDDDDDDDDDDDDDDDDDDBIAAAAAEMBBC................",
    "............CCCBBHDDOOOODDDDDDDDDDDDDDDDDDDDDDDDDDDDDHIBEAAEEMBBC................",
    "............CFBBBHDDOOOODDDDDDDDDDDDDDDDDDDDDDDDDDDDDHIBEAEEEMBBC................",
    "............CFBPDDDYOODDDDDDDDDDDDDDDDDDDDDDHJBDDDDDDHIBQEEELBBBC................",
    "...........CCFBPDDDYOODDDDDDDDDDDDDDDDDDDDDDHJBDDDDDHHIBQEELBBFCC................",
    "..........CCFBBPDDDDDDDDDDDDDDDDDDDDDDDDDDDHHHJBPHHHHHIBRRRBBBFC.................",
    "..........CCBBHHHHHDDDDDDDDDDDDDDDDDDDDDDDDHHHJBPHHHHIBBBBBBFCCC.................",
    "..........CCBBBBBBHHHHHHHHHDDDDDDDDDDDDDDDDDHHJBBJHHJBBFFFFFCC...................",
    "..........CCBBKKKBJJJJJJJHHDDDDDDDDDDDDDDDDDHHJBBBJJBBBFCCCCCC...................",
    ".........CCFBKAAAABBBBBBBHHHHHHHHHDDDDDDDDDDHHHPBBBBBCCCC........................",
    ".........CCFBAAAAAAAAAEEBBBBBBBPHHDDDDDDDDDDHHHPBFCCCCC..........................",
    ".........CBBBAAAAAAAAAAAANNNNBBBPPPPHHHHHHHHHHHPBFC..............................",
    ".........CBBEAAAAAAAAAAAAAAAAABBBBBBPHHHHHHHHHHPBFC..............................",
    ".........CBBEAAAAAAAAAAAAAAAAAQQQQQIIJJJJJJHHHHPBFC..............................",
    "........CCBBEAAAAAAAAAAAAAAAAAAAAAAAKKKKKKBPPPPBBFC..............................",
    ".......CCFBBEAAAAAAAAAAAAAAAAAAAAAAAAAAAARBBBBBBBFC..............................",
    "....CCCCFBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARRBBBBFCC..............................",
    "...CCCBBBBWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEIBCCCCC............................",
    "..CCFBBBBBWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEIBBBBFCC...........................",
    ".CCFBBBBQQQAAAAAAEEAAAAAAAAAAAAAAAAAAAAEEAAAAAIBBBBBFCCC.........................",
    "CCCBBBBAAAAAAAAAAEEEEAAAAAAAAAAAAAAAAAEEEAAAAAQQQQNBBBCCC........................",
    "CFBBBAAAAAAAAAAAAEERREEEAAAAAAAAAAAAEEEEEAAAAAAAAAQNBBFFC........................",
    "CFBBAAAAAAAAAAAAAERBBEEEEEEEEEEEEEEEEEEEAAAAAAAAAAAABBBFC........................",
    "CFBSAAAAAAAAAAAAEERBBBKKKEEEEEEEEEEEKKEEAAAAAAAAAAAEENBFC........................",
    "CFBSAAAAAAAAAAEEEEMBBBBBBBLLLLLLLLLLBBEAAAAAAAAAAEEEENBFC........................",
    "CFBBEEEEEEEEEEEEEEMBBCCCFBBBBBBBBBBBBEAAAAAAAAAAEEEEENBFC........................",
    "CFBBBEEEEEEEEEEEEEBBFCCCFFFFFFFFFFBBBEAAAAAAAAEEEEEEELBFC........................",
    "CCCBBBSSSSSSSSSSBBBFCCCCCCCCCCCCCCFBBBMEEEEEEEEEEEEELBFFC........................",
    ".CCFBBBBBBBBBBBBBBCCC............CCFBBBMMMMMMMMMMMMBBBFCC........................",
    "..CCFFFFFFFFFFFFFFCCC.............CCFBBBBBBBBBBBBBBBFFCC.........................",
    "...CCCCCCCCCCCCCCCC................CCFFFFFFFFFFFFFFFFCC..........................",
    "....................................CCCCCCCCCCCCCCCCCC...........................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (81, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 81x96).
    scale=int   -> sprite de 81x96 px ampliado por un entero, sin márgenes.
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
