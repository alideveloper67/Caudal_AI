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
    "A": (240, 241, 252),
    "B": (20, 18, 23),
    "C": (193, 205, 249),
    "D": (15, 13, 18),
    "E": (220, 224, 245),
    "F": (155, 76, 42),
    "G": (63, 63, 72),
    "H": (173, 187, 233),
    "I": (158, 172, 221),
    "J": (39, 30, 34),
    "K": (163, 163, 172),
    "L": (119, 122, 139),
    "M": (124, 57, 36),
    "N": (98, 46, 33),
    "O": (139, 152, 197),
    "P": (63, 34, 28),
    "Q": (252, 158, 167),
    "R": (202, 201, 211),
    "S": (90, 91, 105),
    "T": (186, 104, 60),
    "U": (247, 125, 133),
    "V": (243, 125, 19),
    "W": (237, 73, 5),
    "X": (248, 192, 201),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "................................DDDD................................",
    "................................BBBB................................",
    "..............................BBTTNB................................",
    "..............................BBTTNB................................",
    "..............................BBMFNB................................",
    ".......................DDD....DBMFNB................................",
    "......................DBBBD....DNFNB.....DDD........................",
    ".....................DBFTTBD...DDNNBB...DPPDDD......................",
    ".....................DBFTTFBD...DNFFB...DPPDBD......................",
    ".....................DBBBFFFBD..DNFFB.DDPMMMBD......................",
    ".......................BBBBFFDD.DNMB..DDMNMMDD......................",
    ".......................DDDBFFPD.DNMB.DJMNMDD........................",
    "..........................DBFPBBBNMBDDJMBD..........................",
    "..........................DBBBBGGPNBBBJMB...........................",
    "........................BBBBBBAAAGPALLBBBDD.........................",
    "........................BBAAAAAAAAAAAAKKBBB.........................",
    "......................DBGAAAAAAAAAAAAAAAAABBB.......................",
    ".....................DDGAAAAAAAAAAAAAAAAAAABBD......................",
    "....................DDSAAAAAAAAAAAAAAAAAAAAAKBD.....................",
    "...................DDSAAAAAAAAAAAAAAAAAAAAAAKBD.....................",
    "..................DDGAAAAAAAAAAAAAAAAAAJJJAAAASBD...................",
    "..................DGAAAAAAAAAAAAAAAAAAABGJJKAASBD...................",
    ".................BBEAAAAEKKKRAAAAAAAARBBGBBKAAASDD..................",
    ".................BBEAAAEBBBBLRAAAAAAARBBBBBKAAACBB..................",
    ".................BBEAAAKBBGBBLAAAAARRBBBBBBKAAACBB..................",
    "...............DDBAAAAAKBBBGBLAAAKKBJJBBBBBRAAACBB..................",
    "...............DBKAAAAAKBBBBBLAAABBJVVVWBBRXQQQCLBDD................",
    "...............DBKAAAAAKBBBBBLABVVVVVWWBBBXQQQQRCLBD................",
    "...............DBKAAAAARBBBBBBBVVVVWWWPBKAXQQQQRCLBD................",
    "...............DBKAAAAXXRLLLBEBVVWWWWPBKAAAXQQQCCLBD................",
    "...............DBKAAAXQQXAAAAEBBWWWWBBKKKKAAAAACCLBD................",
    "...............DBKAAXQQQQAAEEEKBBBBBRRKKBAAAAAACCLBD................",
    "...............DBKAAXQQQQAASBBEKKKKRRKBBBAAAAACCCLBD................",
    "................DGAAAXXXAAASBBBKKKKKBBBBGAAAAACCJB..................",
    ".................BGAAAAAAAAASBBBBBBBBBBBGAAAAACCJB..................",
    "......DDD........BGEEAAAAAAAABNNNBNNNBJJAAAACCCCJB........DBBD......",
    ".....DBBBD.......BGEEAAAAAAAKAMMUUUUUJJJAAACCCCCJD.......DDFFBD.....",
    ".....DBBTBB.......DBIEEAAAAAAKBMUUUUUJJAAACCCCLBD........BPFFFD.....",
    ".....DBBTBB.......DBICCAAAAAAAGBUUUUUJGAAACCCCLBD........BPFFFD.....",
    "..DD..DBBFB.......DDLLCCCAAAAAAGBUMMJGEAACCCOCCD.........BPMFD......",
    ".DBBD..BPFB.........BBCCCCCCEAAAABBBGEAACCCCODD..........BPMB...BBD.",
    "DJTTBDDBPFB.........DDBLCCCCEEEAAAAAAACCCCCGGDD.........DDMMBDDBFFDD",
    "DJTTPPPPFFBD..........BBLCCCCCCEEEEEECCCCCCBB...........DPFFPPPPTTDD",
    "DBNNFFFFFFFBD.........BBBBCCCCCCCCCCCCCCCCBBB...........DPFFFFFFNNDD",
    ".DBBFMMFFFFBD.......DBBKKKOOOCCCCCCCCCOIILLLBD.........DBPFMMMMFBBD.",
    "..DDBJJJJNFFBD......DBBAAAAAAOOOOOOOOOOCCCCCBBD........BPFMJJJJBDD..",
    "....DDDDBNFFFDD....BGEEAAAAAAEEEEEEEEEEECCCCCCJB....DDDPMFPBDDDD....",
    "........DBFFFFBB..DBGAAAAAAAAAAAAAAAAAAACCCCCCJB...DBJJMMPBD........",
    ".........DBFFFMPDDBBAAAAAAAAAAAAAAAAAAAAACCCCCCCDDDBMFFMPDD.........",
    ".........DDBFFFMPBBAAAAAAAAAAAAAAAAAAAAAAACCCCCCBBDMMMNNBDD.........",
    "..........DBBBMFFNNAAAAAAAAAAAAAJJJAAAAAAAAACCCCNNFFMBBBBD..........",
    "...........DDDDFFFFAAAAAAAAAAAABGJBBAAAAAAAACCCCNFFFJD..............",
    ".............DDBNNFAAAAAAAAAARBGJJBBJAAAAAAACCCCNNNJDD..............",
    "...............DBBAAAAAAAAAAARBJGBBBJAAAAAAACCCIBBBB................",
    "...............DBLCAAAAAAAAAARBBBBBBJAAAAAACCCCHIBB.................",
    "...............DBLCCCAAAAAAAAEBBBBBBAAAAAAACCCHIIBB.................",
    "...............DBLCCCAAAAAAAAAEBBBBAAAAAECCCCCHIIBB.................",
    "...............DDDDCCEEEAAAAAAAEEEEAAAAAECCCCHIIIDD.................",
    ".................DBOCCCCAAAAAAAAAAAAAAECCCCCCIIGBD..................",
    ".................BBBOCCCEEEAAAAAAAAAAAECCCCCCOOGB...................",
    "..................BBBICCCCCEEAAAAAAACCCCCCCHHGBD....................",
    "...................BBLICCCCCCEEEEEEECCCCCCCIHGBD....................",
    ".................DDBLIHHHHHCCCCCCCCCCCCCHOOIHHBDD...................",
    ".................BBAAAAHHHHHHHHHHHHHHHHHHHIHCCHDDD..................",
    "...............BBLLAAAAAAAHHHHHHHHHHHHHAAACCCCCLLDD.................",
    "...............BBAAAAAAAAAAAAAAAAAAAAAAAAAAAECCCCGD.................",
    "..............DBAAAAAAAAAAAAAAASGGGAAAAAAAAAECCCCCGDD...............",
    ".............DBRAAAAAAAAAAAAAASGGGBGAAAAAAAAAAECCCHBD...............",
    ".............DBRAAAAAAAAAAAAAGBGLGBBGAAAAAAAAAECCCHBD...............",
    "............DDAAAAAAAAAAAAAAAGBLGBBBGAAAAAAAAAECCCHHB...............",
    "............BLAAAAAAAAAAAAAAAGBBBBBBGAAAAAAAAAECCCCCSBD.............",
    "............BLAAAAAAAAAAAAAAAGBBBBBJAAAAAAAAAAAEECCCSBD.............",
    "...........DBLAAAAAAAAAAAAAAARBBBBJAAAAAAAAAAAAAECCCSBD.............",
    "..........DBKAAAAAAAAAAAAAAAAARKKKKAAAAAAAAAAAAAECCCCIBB............",
    "..........DBKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAECCCCIBB............",
    "..........DBOCEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAECCCCIBB............",
    "..........DBOCEAAAAAAAAAAAAAAAAGJJJGAAAAAAAAAAAAECCCCOBB............",
    "..........DBOCEAAAAAAAAAAAAAAAGJGGBBGEAAAAAAAAAAECCHHOBB............",
    "..........DBOCEAAAAAAAAAAAAAAGGGGGBBBEAAAAAAAACCCCCIIOBB............",
    "..........DBOCCCCAAAAAAAAAAAAGGGGBBBBEAAAAAAAACCCCCIIOBB............",
    "..........DDBCCCCAAAAAAAAAAAAGBBBBBBBAAAAAAAAACCCCCIIDDD............",
    "............BBHCCEEAAAAAAAAAAGBBBBBBBEAAAAAAECCCCCCIGBD.............",
    "............BBHCCCCEAAAAAAAAAALBBBBBEAAAAAAAECCCCHHIGBD.............",
    "............BBBCCCCCEEAAAAAAAAALLLLAAAAAAAECCCCCHIIIBBD.............",
    ".............BBJCCCCCCAAAAAAAAAAAAAAAAAAAAECCCCHHISBD...............",
    "..............BJOOCCCCCCAAAAAAAAAAAAAAACCCCCCCCIOOSBD...............",
    "...............DBBCCCCCCEEEEAAAAAAAAEEECCCCCCCCISBD.................",
    "...............DBBHHHCCCCCCCAAAAAAAECCCCCCCCCCCISBD.................",
    "...............BBBHHICCCCCCCCCCCCCCCCCCCCCCIIIEAEKBB................",
    ".............DBBKAAAHIIIHCCCCCCCCCCCCCCCIIIEEEAAAEKBB...............",
    ".............DBKAAAAAECHIICLLLOCCCCCLLLLICCAAAAAAAEGB...............",
    ".............DBLEEAAAAECHILBBBBOOOOLBBBGHEEAAAAAEECGB...............",
    ".............DBLCCEEEECCILBDDDBBBBBBBDDGHHEEEEEECCCGB...............",
    "..............DBBIIIIIIIBBBD..DDDDDDD..BBBIIIIIIIBBD................",
    "...............DBBBBBBBBBDD............DDBBBBBBBBBDD................",
    ".................DDDDDDDDD...............DDDDDDDDD..................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (68, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 68x96).
    scale=int   -> sprite de 68x96 px ampliado por un entero, sin márgenes.
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
