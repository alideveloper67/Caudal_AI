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
    "A": (252, 247, 248),
    "B": (20, 17, 17),
    "C": (209, 215, 248),
    "D": (235, 232, 243),
    "E": (253, 177, 196),
    "F": (24, 22, 28),
    "G": (222, 215, 217),
    "H": (2, 102, 182),
    "I": (51, 49, 51),
    "J": (36, 32, 33),
    "K": (24, 22, 28),
    "L": (24, 22, 28),
    "M": (24, 22, 28),
    "N": (164, 184, 212),
    "O": (192, 189, 189),
    "P": (24, 22, 28),
    "Q": (113, 164, 206),
    "R": (193, 198, 227),
    "S": (0, 150, 239),
    "T": (24, 22, 28),
    "U": (35, 116, 184),
    "V": (67, 138, 196),
    "W": (213, 147, 164),
    "X": (159, 109, 121),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......................................................BBBBBBBBBBBBBBBB......................................................",
    "......................................................BBBBBBBBBBBBBBBB......................................................",
    ".................................................BBBBBBGGGGGGGGGGGGGGBBBBB..................................................",
    "..............................................BBBBBBBBGAAAAAAAAAAAAAABBBBB..................................................",
    ".......................................BBBBB..BBBBDDDDAAAAAAAAAAAAAAADDDDDJBBB..............................................",
    "......................................BBBBBBBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAJBB..BBBBB.......................................",
    "...................................BBBBFFFBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBBBBB......................................",
    "..................................BBBBAAABBJPPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBKKKKKBBBB...................................",
    "................................BBBBAAAAABBJAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBAAAAABBBB...................................",
    ".............................BBBBMMAAAAAABBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOOOLBB.................................",
    ".............................BBBBAAAAAAABIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALBB.................................",
    "...........................BBBFFAAAAAAAABIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABB.................................",
    "...........................BBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBBB..............................",
    "........................BBBBDDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJJB..............................",
    "........................JJBAAAAAAAAAOOIIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBB.............................",
    "....................BBBBAAAAAAAAAAAABBFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBB............................",
    ".................BBBBPPPAAAAAAAAADCCBBFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBBB..........................",
    "..........BBBBBBBBBBBAAAAAAAAAAAADCCBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCDAAAAAAAAAAAAAAGTTBBB........................",
    "......BBBBBIIIIIIIIBAAAAAAAAAAAACCTBMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCDAAAAAAAAAAAAAAAAABBBB.......................",
    "......BBBBBAAAAAAAAAAAAAAAAAAAAACCTBMAAAAAAUUNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCCAAAAAAAAAAAAAAAAAKKBBBB....................",
    "....BBBGGGGAAAAAAAAAAAAAAAAAAADDCMLMAAAAAAUUNQNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPCDDAAAAAAAAAAAAAAAAABBBBBBBBBBBBBB..........",
    "....BBBAAAAAAAAAAAAAAAAAAAAAAADCMBLAAAAAAAHCAQQAAAAAAAAAAAAAAAAAAAAANNNDAAAAAALPCCCAAAAAAAAAAAAAAAAAAOOBBBBBBJJJJJBBBB......",
    "..BBOBAAAAAAAAAAAAAAAAAAAAAAAADCMBLAAAAAAHHCAQQAAAAAAAAAAAAAAAAAAAAHHHHNDAAAAALPCCCAAAAAAAAAAAAAAAAAAAAAIIIIIAAAAABBBB......",
    "..BBOAAAAAAAAAAAAAAAAAAAAAAAAADCMBAAAAAAVHHVVQQAAAAAAAAAAAAAAAAAAANHHAAQQAAAAAAACCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBBB....",
    ".BBBAAAAAAAAAAAAAAAAAAAAAAAAACCBBGAAAAAAVHHHHHQAAAAAAAAAAAAAAAAAAANHHAAQQAAAAAAOBMCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBB....",
    "BBOAAAAAAAAAAAAAAAAAAAAAAAAADCCBBGAAAAAAVSSSHHQAAAAAAAAAAAAAAAAAANHHHAAQQAAAAAAOBMCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBB..",
    "BBOAAAAAAAAAAAAAAAAAAAAAAAADCCCBBGAAAAAAVSSSHHNAAAAAAAAAAAAAAAAAANHHHUUHQAAAAAAOBMCCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBB..",
    "BBOAAAAAAAAAAAAAAAAAAAAAAADCCCCBBGAADDDAAVSSHNAAAFBAAAAAAAAAAAAAANHHHHHHQAAAAAAAALCCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBB..",
    "BBODAAAAAAAAAAAAAAAAAAAAAACCCCBBBGAEEEEEAAUUAAAAAFBBBBAOOOOBAAAAANHSSSHHQAAAAAAAALBKCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBB",
    "BBBCDAAAAAAAAAAAAAAAAAADCCCCCLBBBGEEEEEEEAAAAAAAAAOBTTBBBBBBAAAAANHSSSHHNAAAAAAAALBKCCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBB",
    "BBBCCCAAAAAAAAAAAAAADDDCCCCCCLBBBGEEEEEEEAAAAAAAAAOJEEEWWWBGAAAAAAASSSUNAAAAAAAAAABBKCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBB",
    "BBBBCCCCDAAAAAAAAAAACCCCCCCCCB.BBBEEEEEEEAAAAAAAAAOJEEEEEWBGAAAAAAAUUUNADDDDAAAAADBBBNCCCDDAAAAAAAAAAAAAAAAAAAAAAAAAAAAACKBB",
    "..BBNCCCDAAAAAAAACCCCCCCCCCCBB.BBBEEEEEEEAAAAAAAAAOJEEEEWBAAAAAAAAAAAAADEEEEEAAAADBBBNCCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAACCKBB",
    "..BBNCCCCCCCCCCCCCCCCCCCCCBB...BBBBGEEEEAAAAAAAAAAAAEEEEXBAAAAAAAAAAAADEEEEEEEAADDFBBBCCCCCDDDAAAAAAAAAAAAAAAAAAAAAAAACCCKBB",
    "..BBBBFCCCCCCCCCCCCCCCCCJJBB.....BBGAAAAAAAAAAAAAAAAAXXXBAAAAAAAAAAAAAGEEEEEEEAADFBBBBBCCCCCCCDAAAAAAAAAAAAAAAAAAAAADDCCCBBB",
    "....BBBFFCCCCCCCCCCCKKKBBB.......BBBBCAAAAAAAAAAAAAAAJJJAAAAAAAAAAAAAAGEEEEEEEADCBBB.BBBCCCCCCCCCAAAAAAAAAAAAAAAAAAACCCNBB..",
    "......BBBCCCCCCCCCCCIBBB...........BBBCCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEEEEDDCCBB...BBCCCCCCCCCDDCDDAAAAAAAAADDDDDCCCNBB..",
    "......BBBBIIIIIIIIIIBBBB...........BBBBCCCDDDAAAAAAAAAAAAAAAAAAAAAAAAAAAEEGGGDCCBBB....BBICCCCCCCCCCCDAAAAAAAAACCCCCCCMMBB..",
    ".........BBBBBBBBBBB.................BBBNNNCCDDDDDAAAAAAAAAAAAAAAAAAAAAADDDDDKKBBB......BBICCCCCCCCCCCCCCCCCCCCCCCCCCCBB....",
    ".......................................BBBBCCBBBBAAAAAAAAAAAAAFFFFAAAAADCCCCKBBB..........BBBCCCCCCCCCCCCCCCCCCCCCCCCBBB....",
    "........................................BBBJBBKKKAAFDDAAAAAAAABBBBBCCCCCCCPPBBB............BBBTTCCCCCCCCCCCCCCCCCCCTBB......",
    "..........................................BJBAAAAKAAFCDDDDDAAAGGGBBICCCCCCBBB................BBBBFFFCCCCCCCCCCCCTTTBBB......",
    "..........................................BMAAAAAAABLCCCCCCAAAAAAGBBIJJJJB..B.................BBBBBBBMMMMMMMMMMBBBB.........",
    "........................................BBMAAAAAAABBLCCCCCJIAAAAAAABBBBBB...BBBBBBB..............BBBBBBBBBBBBBBB............",
    "........................................BBDAAAAAADRBLAAAAAJIAAAAAAAABBB..BBBBKKKKKBBB...............BBBBBBBBBBBB............",
    "........................................BBDAAAAADRMBAAAAAAJIAAAAAAAAAJB.BJPPAAAAAABBBB......................................",
    "........................................BBDAAAADCCBMAAAAAAJIAAAAAAAAAJB.BJAAAAAAAADDDLB.....................................",
    "........................................BBBBDDDCCCCAAAAAAAAAAACCAAADDCBBBAAAAAAAAAAAALB.....................................",
    "..........................................BBCCCCCCCAAAAAAAAAAACCCCCCCCFBPAAAAAAAAAAAAABB....................................",
    "..........................................BBLLLLCCAAAAAAAAAAAACCCCCCCCFBPAAAOLLLMAAAAAABB...................................",
    "...........................................BBLIIAAAAAAAAAAAAAAACBBTCCCFBBAAOAPPPAMDAAAABB...................................",
    "...........................................BBBAAAAAAAAAAAAAAAAAATTCCCCCCLLDFAAAAFBDAAAABB...................................",
    "..........................................BBBAAAAAAAAAAAAAAAAAAAAADCCCCCLBDDFAAAFBDAADDBB...................................",
    "..........................................BBAAAAAAAAAAAAAAAAAAAAAAADDCCCLBDAAAAAFBAAACCBB...................................",
    "..........................................BBAAAAAAAAAAAAAAAAAAAAAAAAACCCCCBAAAAFAAAAACCBB...................................",
    "..........................................BBAAAAAAAAAAAAAAAAAAAAAAAAACCCCKBBFFFAAAAACCBB....................................",
    "..........................................BBAAAAAAAAAAAAAAAAAAAAAAAAACCCCKBBBBBAAADDCFBB....................................",
    "..........................................BBBAAAAAAAAAAAAAAAAAAAAAAAACCCCKBBRCDDAACCCFBB....................................",
    "............................................BAAAAADCCDDDDDDDDAAAAAAAACCCLBKRCCCCCCCCCB......................................",
    "...........................................BBAAAADCCCCCCCCCCCDAAAAAAACCCLBBBRCCCCCCCBB......................................",
    "..........................................BBDAAAADCCCRRRRRRRRCCAAAAAACCCLBBBBFFFFFBBB.......................................",
    "..........................................BBDAAAADCCPBBBBBBBBFCAAAAAACNBB..BBBBBBB..........................................",
    "..........................................BBDAAADCCCPBBBBBBBBFCCDDDDCCNBB...BBBBBB..........................................",
    "..........................................BBBCCCCCRCBB.....BBBCCCCCCCCBBB...................................................",
    "...........................................BBBRRRRBBB.......BBBCCCCCCBB.....................................................",
    "............................................BBBBBBBB.........BBBBBBBBB......................................................",
    "............................................BBBBBBB...........BBBBBBBB......................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (124, 67)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 124x67).
    scale=int   -> sprite de 124x67 px ampliado por un entero, sin márgenes.
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
