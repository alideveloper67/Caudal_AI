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
    "A": (251, 237, 202),
    "B": (25, 100, 99),
    "C": (251, 215, 74),
    "D": (23, 72, 71),
    "E": (36, 165, 163),
    "F": (234, 212, 182),
    "G": (31, 132, 130),
    "H": (88, 85, 77),
    "I": (141, 139, 127),
    "J": (49, 187, 182),
    "K": (99, 224, 204),
    "L": (250, 166, 135),
    "M": (22, 40, 37),
    "N": (55, 69, 64),
    "O": (119, 112, 100),
    "P": (198, 194, 166),
    "Q": (167, 164, 152),
    "R": (72, 137, 130),
    "S": (222, 122, 101),
    "T": (147, 223, 218),
    "U": (215, 171, 58),
    "V": (85, 210, 193),
    "W": (95, 69, 33),
    "X": (247, 244, 241),
    "Y": (143, 97, 55),
    "Z": (88, 170, 161),
    "a": (172, 143, 55),
    "b": (197, 196, 219),
    "c": (9, 11, 11),
    "d": (191, 227, 122),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...........EIBBBEE...........",
    "..........ENIIHHHMEE.........",
    ".........IIXXXbHHLLDE........",
    ".......BDIIXXbIIILLLDJ.......",
    ".......BIIIIIIIIIOLLLDJ......",
    "......BIQQAPPIIIOLLLLLA......",
    "......DIIQFAHHIIOOLFLANA.....",
    ".....DDRQQFAAXXIIOFFLLAA.....",
    "..BBBDIRXQAMAXXPIFSLLLFNA....",
    "..BBPPFIXQFNIXXIPFMSLLFFF....",
    "..ENPFAFQAFIXXXHAFFLLLLFME...",
    "...ENPFAAAAAbbHAAAFLLLLLLDE..",
    "....DFFFAAAAOOFAAAFFLLLLLLDEE",
    "...JNFAAAAAAAFAAQFFFLLLLLLLEE",
    "...JNAAAAAOAAASQQFFFFLSSSSLDE",
    "...JMAAANOAAAASLLLLLLLSSWcEE.",
    "....MAAAAAAAAALSLLLLSSSSWGE..",
    "....EMAAAAAAAYLLSSSSSSSMG....",
    ".....EMAAAAAFFYSSSSSSMSS.....",
    "......EDNNNAFFFYSSSMSS.......",
    "........NBDFAIMMMSSS.........",
    "..........BIIIM..............",
    "..........BKKRR..............",
    ".......GGBBKKRMDBB...........",
    "......GNGGVVVRAABB...........",
    "......DGGGdKKIAXXNB..........",
    ".....BQQGdCdKIAAXAA..........",
    ".....BQQQCCdKKAAAAD..........",
    ".....BQRKdddKJNAAXND.........",
    ".....DARKKKKKJNAAXXQ.........",
    "....ENANJJJJJJJNAAQQ.........",
    "....EAAORVVVJJMBAAAD.........",
    "....EAAORKKKJJDBAAAAB........",
    "...ENAANDKKKJRDcDAAAB........",
    "...EAAADNRRRRNDcBAAANB.......",
    "...BAADDRKKKRRMDDBAAAA.......",
    "...BFFNDZKKRKTMDNBAAADD......",
    "..QAAFMMZKKKKTDJTTNAAAD......",
    "..GQAADDDGGGGKDJBTAAAAA......",
    "..GAAAMDVVKKTKKBJJNAAAA......",
    "..GNAATVVKKKTTKTDJAAAMA......",
    "...GNTVVRRRRTTKTTMAAAA.......",
    "...BTTMMYYYYUMNTTRAANA.......",
    "..EBBBMUUUUUUUUMBRAAA........",
    "..EDBBUUCCCCCUUUBDIAA........",
    "...EBcUCCCCCCCCUcIID.........",
    "...EBDUCCCCCCCCUMIID.........",
    "...EEUUCCUCCCCCUWINDD........",
    "..ENEBUCCUWCCCCUWWDDD........",
    "..DVVBCCCCWCCCCUWWKKDD.......",
    ".BTTVECCCCWCCCCUWMJKTD.......",
    ".BTKKECCCCWCCCCUWJJKTTD......",
    "BBTKKEDCCCWCCCCUMJJKKTT......",
    "BBKKJEDCCCWCCCCCcGJKKTD......",
    "BDRKJEMCCCWCCCCYGGKKZDD......",
    ".BBREEBCCCWUCCCYGDKZDE.......",
    "..EDEBBNaaMUCCCYDDDME........",
    "...EDDMMaaaaaaYMDDME.........",
    "....JDMMAAIaAAPDDME..........",
    ".....J.MNAAIAAPDDD...........",
    "........DFFOAAAD.............",
    "........FFFOAAHG.............",
    "........GFFOAAHG.............",
    "........GOOOAAHG.............",
    "........GOFHAAHG.............",
    "........BFFHAAAA.............",
    "........BFFHAAAD.............",
    ".......JNAFHAAAND............",
    ".......JHAFHAAXXI............",
    ".......JHAFHAAXIB............",
    ".......JHAFHAAAIB............",
    ".......JNFFHAAAAB............",
    "........FFFHAAANN............",
    "........GFAHAAANN............",
    "........GOAHAAAD.............",
    "........GOAHAAAA.............",
    "........DNAHAAHG.............",
    ".........DAHAAHG.............",
    ".........DAHAADM.............",
    ".........DAHAAM..............",
    ".........BHHAAB..............",
    ".........BPHAIB..............",
    ".........BPHAIB..............",
    ".........BPHAIG..............",
    ".........BPHAIG..............",
    ".........DFHAIG..............",
    "........GFFHAAD..............",
    ".......GOAFOAANE.............",
    ".....DDOAAAOAAADE............",
    "...EDNIAAAAMIAAOO............",
    "..EDDIIIAJABBIAAOG...........",
    ".DDTTVVIJGDMBBIAANG..........",
    ".MDKKVBBMDGBBVVVAAGG.........",
    ".DDDDMBBB...GBVVTTGMJ........",
    "............GGMVBRRcJ........",
    "..............MBBBBc.........",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (29, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 29x96).
    scale=int   -> sprite de 29x96 px ampliado por un entero, sin márgenes.
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
