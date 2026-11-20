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
    "A": (21, 20, 20),
    "B": (251, 198, 151),
    "C": (10, 8, 11),
    "D": (1, 174, 250),
    "E": (243, 242, 241),
    "F": (1, 77, 211),
    "G": (2, 73, 166),
    "H": (15, 30, 55),
    "I": (3, 40, 114),
    "J": (55, 50, 53),
    "K": (205, 208, 227),
    "L": (80, 86, 100),
    "M": (214, 153, 112),
    "N": (146, 221, 36),
    "O": (3, 136, 214),
    "P": (103, 73, 56),
    "Q": (175, 196, 228),
    "R": (19, 97, 5),
    "S": (82, 157, 14),
    "T": (133, 136, 149),
    "U": (157, 168, 196),
    "V": (159, 111, 82),
    "W": (84, 120, 162),
    "X": (65, 104, 19),
    "Y": (196, 240, 122),
    "Z": (220, 247, 175),
    "a": (137, 216, 250),
    "b": (75, 176, 243),
    "c": (106, 148, 194),
    "d": (63, 130, 231),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............AAAA................................",
    "............CAATTCC................AAA............",
    "...........CAEEEKCJA.............AJEKAAA..........",
    "...........AEEEEEKJA............AAEEEKAA..........",
    "...........AEEEEEKKJAAAAAAAAAACAAEEEEKKJA.........",
    "..........AEEEEEKKKJCJLLTTTTTLLLCLEEEKKJC.........",
    "..........AEEEEKKKKKEEEEEEEEEEEEELLKEKKKA.........",
    "..........AEEEKKKKKEEEEEEEEEEEEEEEKKKKKQA.........",
    "..........ATEEKKKKEEEEEEKKKKKKKKEEEEKKKQA.........",
    "..........ATKKKKEEEEEEEEAAAAAAAAJEEEEQQAA.........",
    "..........AUUKKEEEEEKTAAEMMMMMMMJAEUEQQJA.........",
    "...........CUUEEEEEKJJTEEEBBBBBBBBJJUEQJC.........",
    "...........AUEEEEEEJPBZEZBBBBBBBBBBBAKKJA.........",
    "..........AAEEEEEEJPBBEZBBBBBBBBBBBBBJKAA.........",
    "..........ALKEEEEEABBBBBBBBBBBBBBBBBBAUUA.........",
    "..........ALKEEEELBBBBBBAVBBBBBBBPABBVLUC.........",
    "..........ALKEEEELMBBBBMAVBBBBBBBPABBVLUC.........",
    "..........ALKEEEELMBBBBBMBBBBBBBBMMBBVLUC.........",
    "..........ALKKEEELMBBBBBBBBBBBBBBBBBBVLUC.........",
    "..........ALKKEEELMBBBBBBBBBBJJBBBBBBBLUC.........",
    ".........AACQKKEEEJMBBBBBBBBBBBBBBBBBHKUC.........",
    ".......ACXXCQQKEEETJMBBBBBBBBBBBBBBBPJKUC.........",
    ".....ACCNNNAQQKKEEETTBBBBBBBBBBBBBBPPKQQA.........",
    "....CXNNNNSCTTTKKEEEETPPBBBBBBBBBPPPEKQAA.........",
    "...CXNNNNSAXXXJTTKEEEEEEEJJJJJJJJEEEEQUJAC........",
    "..AXNZZNSANNNYYNTLEKEEEEEEEEEEEEEEEEKQUJSAA.......",
    "..JNZENNXXNSSNYYNLLLKKEEEEEEEEEEEEKKQQJSYSA.......",
    ".CCYEZNNXAAIHNNYYYLLLKKKKEEEEEEEKKKLLHRNYYAA......",
    ".CNYZNNSSCIOOGRNYYYAIIJJJJJJJJJJJJJIIGCNNYLA......",
    ".CNNNNNSRHbaDOHNNYYHHOOOOOOOOOOOOOODFGHRNYLA......",
    "CNNNNSSSAaabDDOANNNNHDDaaaabDDDDDDDDFGIRNNAA......",
    "CNNNNSSRIbaDDDFCNNNNHDbaKaabDDDDDDDDFGIRNNRA......",
    ".NNNNSSHHDbDDDGCSNNSHDbKaDDDDDDDDDDDFGIRSSIH......",
    ".NNSSRRHGGDDDGGCSSSRIDDKDDDDDDDDDDDDFGIRSSIIC.....",
    ".SSSRRRCJJHGDGICSSSAFDbbDDDDDDDDDDDOGGIRSHOOC.....",
    ".RRRRRRABBBJHGHRSSRCDDDDDDDDDDDDDDOFGGIRAHODCC....",
    "CARRRRRBBBBMMHHRRRCGDDDDDDDDDDDDDOGIGGIAHFODGA....",
    "..RRRRABBBBMMCRRRAIDDDDDDDDDDDDDOFGAGGHHGFDOGA....",
    ".CRRRRAJJJMMMARRAIGDDDDDDDDDDDDOGIHHGGHIGGHACA....",
    ".CCRRRHJJJWJACCCIGODDDDDDDDDDDGGHHGDDGHHAJMMCC....",
    "..CRRHJJJJLWAAHIIGGODDDDDDDDOOIHGDDDFGHCVMBBCC....",
    "..CCJEEEQQLHAAHGIGGGFOOODDDDDDDDDDDOGGCCVMBBBA....",
    "...CCEEQQQWWJAIGGGIIGGGGDDDDDDDDDDOGGGIAMMBBBBA...",
    "...CCELLQQWWWCIGODDDDDDDDDDDDDDDDFGIAGICAMBBBBA...",
    "...AAHLLLAIWJAGGGODDDDDDDDDDDGGGGIAAIGGHAJBBBBJA..",
    "....CEKKQWHHAHGGOOODDDDDOOGIIIAAHHIODFGHAJBBBBMA..",
    "...CJEEQQWLCCHGGODDDDDDOOOGIHHHGDDDDOGGHCABBBEMA..",
    "...CEEEQcWLCCCHHGOODDDDDDDDDDDDDDDDOGHACCCBBBEBA..",
    "...CEEQQcWLCCCIIAAAHHDDDDDDDDDDDHHHCCHIACCAMBBBA..",
    "..AJEEQQWWCCCAIFFGIIICCCCCCCCCCCIIIIIIIAC.AMBBBJA.",
    "..CEEEQcWWCCCAGFFFFFGGGGGGGGGGGGGFFFFFIAC.CJBBBBA.",
    "..AEEQQcWJCCCAGFFFFFFFFFFFFFFFFFFFFFFGIAC.AJBBBBC.",
    "..JEEQQcWHCCCAIGGFdbFFFFFFFFFFFFGGIFFII....AVBBBC.",
    "..JTTWLLLACCCCIIGFbdFFFFFFFFFGGIIIIFFIH....AVBBBC.",
    "..CJWWWLHACCCCHIFbdFFFFFGGGGGIIIHIFFFGHC...AVBBBBA",
    "..JJWQQQHHCCCCHGdadFFFFIIIIIIICHGFFFFFHC..ABBBBBMA",
    "..LKKQQQHLLCCCHFadFFFFGIIC..CCHIGFFFFFHC..JBBBBBMA",
    "..LQQQQQAULCCCGFdFFFFGIIC...CHHHIGFFFFICA.ABBBBBMA",
    "..AJJAJLCHULCAGFFFFFGIIAC...CHIHHIGFFFGCA.AVABBBJA",
    "..JTTULLAACJAHFFFFFGIIHC.....AIIGGGFFFGAC..CVBPAAA",
    "..JJTUAWLACCCHFFFFGIIIHC.....AIIGFFFFFGHC..CJPAAC.",
    "..CJHWLWWJA.CIFFFIIIIIHC.....CHIIIFFFFIHC...AC....",
    "..AAHLWAWHA.CGFFGIGFIIC......AHIIIIIIIIHC.........",
    "...CCAJACC..CGFFFFFIIIC......AHIIHHHHHHC..........",
    ".....CC.....CCCIGGIIHCA.......C.CPPPPPC...........",
    ".............CPPPPPACC..........AMMMMCC...........",
    ".............CVMMMMJ............AMMBBMC...........",
    ".............CVBMMMJ............AMBBBMC...........",
    ".............ABBBBMA............ABBBBMC...........",
    "............APBBBBPA............AJBEBMC...........",
    "............APBEBBPA............APBEEMC...........",
    "............APBEBBPA............APBEEMC...........",
    "............APBEBMPA............APBEEMC...........",
    "............CBBEBMJA............APBBBMC...........",
    "............ABBBBVC.............APBBBMC...........",
    "............JBBBBVA.............APBBBMC...........",
    "............JBBBBPA.............APBBBMC...........",
    "............JBBBBPA.............APBBBMC...........",
    "............JBBBBC..............APBBBVC...........",
    "..........AAPBBBVC.............AAPBBBVCA..........",
    ".........CJPPBBBVCC...........AATPBBBVVJC.........",
    ".........JKKJPJKJKLA..........CTEJJJJJVKJ.........",
    ".........JEEEKKKKKLA..........CTTEEEEEEKJ.........",
    ".........AAKKEEKKKLA...........ATTKKKKKAA.........",
    ".........AAAUUUUUJA.............CCJJJJCA..........",
    "..........CCCCCCCC..............CCCCCACC..........",
    "..........CACHACCA.............CCCCHHLHCA.........",
    ".........CCAEHHCCA.............ACCCHHJLJCCA.......",
    ".........CAHEJHACCA............ACCCHHHJJJUJAC.....",
    ".........CAHHJLJACCAA..........ACCCCAHHHJUHCCC....",
    ".........CAHHHJLLLHAA..........ACCCCCCAHHHHJAA....",
    ".........CCAHHHJTTTJCA..........ACCCCCCAAAAACC....",
    ".........CCCAHHHJJJJCA...........AACACCCCCCCCA....",
    "..........AACCAHHHHACA...............CAAAAAAC.....",
    "...........CACCCCCCCA.............................",
    ".............AAAAAAA..............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (50, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 50x96).
    scale=int   -> sprite de 50x96 px ampliado por un entero, sin márgenes.
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
