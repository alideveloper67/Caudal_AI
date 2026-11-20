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
    "A": (252, 146, 37),
    "B": (70, 25, 32),
    "C": (249, 207, 174),
    "D": (238, 161, 125),
    "E": (130, 37, 46),
    "F": (50, 20, 19),
    "G": (142, 77, 13),
    "H": (108, 59, 12),
    "I": (170, 88, 12),
    "J": (27, 10, 11),
    "K": (189, 109, 18),
    "L": (80, 44, 12),
    "M": (225, 93, 9),
    "N": (230, 123, 24),
    "O": (94, 36, 37),
    "P": (181, 83, 68),
    "Q": (203, 129, 100),
    "R": (218, 63, 44),
    "S": (141, 108, 90),
    "T": (251, 229, 162),
    "U": (131, 75, 61),
    "V": (94, 72, 59),
    "W": (251, 228, 206),
    "X": (245, 188, 89),
    "Y": (179, 158, 137),
    "Z": (251, 245, 237),
    "a": (187, 178, 169),
    "b": (171, 46, 30),
    "c": (237, 100, 86),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".....................................GGGGII.................",
    "....................................ILGYYWHI................",
    ".................................KKYHIGOWWWWI...............",
    "...............................BHLCYYYBFWCWWOF..K...........",
    ".............................GGBCCCCCCCCFCCWWHFHH...........",
    ".....................N......GHVCCCDDCCCCCCCWWHHHH...........",
    "....................NJJG...GGVCCDDDDDDCCCCCCWWHCHG..........",
    "....................NJJLGKKHVCDDDDDCCCCCCCCCCWCSGGG.........",
    "....................HLCWSSSWCDDDDDWWZZCCCCCCCCCSWBGG........",
    ".............NN....HHLSCWZZWDDDDDCZZWWCCCCCCCCCCWWWBHK......",
    "............NLVVVVHLSSSCCCCDDDCCCCWWCCCCCGCCCDDCCWWWSGK.....",
    "............VVVVVVZZZZWCCCDDCCCSCCCCCCCCGGTCYYDDDCCCWSG.....",
    "...........VHBDWWWWZZWCCCCCCCCSCCCDCCCCEKGXTSZDDCDDDCCSS....",
    "...........NVDDDCCCWCCCCCCCCCDCCCDDCCCCEJKKXSCZCCCDDDDSI....",
    "...........NODDDDDDCCCCCDDDDDDCCDDDCCCCaaJKKFFCCCCCBDHII....",
    "...........NHDDDDDDDCDCDDDQQDQCDQDDCCCRaaaOHFFCCCDCCGLII....",
    "............IDDDDDDPDCWCCCDPPQDDQDDCCCRRbbEEFOCCDDCCGG......",
    "............ILPPPPPPWWZWCDDDPEDFDCCCCCNNAAKKEPPDDDDCCG......",
    "...........HHIJUUCCCZZCCDDDDPPEODCCCLNNNAKNNIUUDDCDCCHN.....",
    "........KKaHVVWCCCCWZWDDDDDDPPPODDCCLNAAAKHKIUOVDCDDCLN.....",
    ".......KLFaaCWWCCCCWWDDDDOOBOPPODDCCHIAAAKKAHUVDDCQDCLN.....",
    "......KBWWWCCCCCDCCCDDDLAAAAAABBDDDCHIHAAAAAPDDDCCBQCLN.....",
    ".....ILWWWCDDDDDDCCDDLAAAAWAXAAHFODDFMMHLLHPPQDDCCFVVV......",
    "....IHLLQQDDDDDCCCDDBAAAAAWXAAAAHBBFFNNMHEPPQPDDCCHHVK......",
    "....HBLLLJBDDDDDDDDDAAAATTAAAAAAAFBBFONNKLOPQDDQDCHHLK......",
    "....HHHLFWCCCDDDDQPLAAAAAAAAAAAAAHBOOBBKNKKLBOOQQLLLL.......",
    ".....LLLWZWCDDDQQPOAAAANNAAAAAAAAIEBOOOFKAAAEOLOLLL.........",
    ".....LLZZWCDDDDDDPFARRcRRRRAAAMMMIOOBOOBFKAAEEOOXLHL........",
    ".....IZZZWDDDDDDDOBRcRcRRRRRMMMMMIOPEBOFBBAOBBOOOXLLL.......",
    "....IHZCCCDDDDDPOERRcRRRRRRRbMMMIIEPPOBFBBOOBBBPHAXLK.......",
    "....IBCCCDCCDDPPBRRRRAAAARRRbbMMMLPPPPBBBBTTBBBPPAAXHK......",
    "GGVGGYCCCCCDDQPBRAAAAAAAAAAAMbLMMOPPPPEBBTTTTBOPPAAALK......",
    "GVVVYCCCCCCDQPPHAAAAAAAAAAAMMGGMLEPPPPPPTTTTTTEPPGAALK......",
    "GGCCCCDDDCDDQPOKANAAAAAAAAAMMLGLOEEPPPPPTTTTTTPPPGMALK......",
    "GLQDDDDDDCDDQDOKANAAAAAAAAMMIJFBOEEEEEEPXXXXQEEPOMMMHK......",
    ".GBQDDDDDCDDDDFAAAAANNAAMMMIJBOOBEEEEEEOXXXQEEEEFNNNN.......",
    ".BBFDPPDCCCCDOKAXXAAAAIMMMIFOFOOOOEOOBFFBXXOEEEBAAAHN.......",
    "...IIJPCCCCDDKATXXAAAAIMMHFPPBFOFFJJFBBBBBFFFOOLMAAHI.......",
    "...ILZZZCCDDHATTTAAAAANHJOPPPPBJJJFBBBBBBBBBBJLMMAAHHI......",
    "...OZZZCCDDDAATTAAAAAANNBPPPPPPJJJFBBBBBBBBBBJMMMAAHHLI.....",
    "..KOCZCCDDDOAXTAAAAAAANMFPPPPPPJJJJFBBBFFFFBBFMMMIIAXXLII...",
    "..KCCCDDDDQHAAXAAAAAAAMMFPPPPPJJBBBBBBBBBBBFJHMMMNAAAXXXK...",
    "..HaCDDDDDQHAAAAAAAAANMMOPPPBJBBEOBBBBBBBBBBFLMMNAAAAAXXHK..",
    "..LaCDDDDDQHAAAAAAAANMMFPPPFFBEQEBBBBBBBBBBBBJMMMAAAAAAXXK..",
    "..HCCQOFDDQLAAAAAAAAMMLPPPFFBEQQBBBBBBBBBBBBBFLMMAAAAAAXXX..",
    "..KKQQJCCDDBAAAAAAAAAFOPPFFBBQQOBBBBBBBBBBBBBBJMMMAAAAAAXH..",
    "..KLQBLCCDDDAAAAAAXXAAHBFFBBUQBBBBBBBBBBBBBBBBBFMMAAAAAAKH..",
    "...IOLLCCDDDLAAAAXTTAAAAJBBBUOBBBBBBBBBBBBBBBBBFMMMAAAAAKHH.",
    "....IHLCCCDQOAAAAAAAAKAAAFBBBBBBBBBBBBFBBBBFBBBBJMMMAAXAALH.",
    ".....LLCCCDQQAAAAAAAAKIAAFBBBBBBBBBBBBFFBFFBBBBBFHMLAXAAAAHK",
    "......LCCCDDQHAAAAAAAALIALBBBBBBBBBBBBJFFJBBBBBBBJHAAAAAAALK",
    "......VVCDCDUKAAAAAAAAAIALBBBBBBBBBBBBJJJBBBBBBBBJJMMAHHNAGG",
    "......VVCCCDUKAAAAAANAAAHJBBBBBBBBBBBBJJFBBBBBBBBFLMMAANNAGG",
    ".......HCJCDUAAAANNNGMAJJFBBBBBBBBBBBBJJFBBBBBBBBFJMFANAAAHG",
    ".......KFHCCDFAANMIMMGHJJLHHHHLFBBBBBBJFBBBBBBBBBBFLMHAIMMFG",
    "........KKCCDDLAIMIMMMJLAAAAAAAAHFBBBFJFBBBBBBBBBBJLMMMIMHG.",
    ".........KHCCDDHIIMIFLIMAXTAAAAAAALBFJJFFBBFFHHHHLJMGGIMHGG.",
    "..........KLCDDDLHFFJIMAXTTAAAAAAAALFJJFFBBAAAAAAAFFGGILHG..",
    "...........IDDDDOOPPFMAATTAAAAAAAAAMJJJFFAAAAAAAAALGLFLII...",
    "............IBDDOPQPLAAXXAAAAAAAAAAMFJHMAAAAAAAAAALHGNN.....",
    ".............ILUUJQQHAAAcRRRRRAAAANMJHMMAAAAAAAAAALH........",
    "..............GGLGOOHRRcRRRRRAAAAANLJMMMAAAAAAAAAAHH........",
    "..................GJORRRRRRRAAAAAAILJMMMAAAAAARNNNHH........",
    "...................GORRRRRAAAAAAAAFIFMMMAAAAAARRRNH.........",
    "..................GHRRRRAAAAAAAAALHLHLMMAAAAAAARREK.........",
    ".................HGBRRRAAAAAAAAALG..LLMMAAAAAAAARBK.........",
    "................GGHNNAAAANNNNMILG....HFMMAAAAAAAALL.........",
    "................GHNXXAAAANMMMILI.....HHGMAAAAAAAALI.........",
    "...............GLNXXAAAAAANMMHI.......GLMMAAAAAAAHI.........",
    "...............HAAXXAAAAAAAANHI......KHMMAAAAAAAAAAI........",
    "..............IHAAAAAAAAAAAANLL......KLMAAAAAAAAAALL........",
    ".............IHKAAHFFFHAAAAANL.......KHMAAAAAAAAAALL........",
    ".............JFKBBASSEOBHNAANL.......LMMAAAAAAHHHAHH........",
    ".............JJFOEEEEEEEOFNANN.......LMMAAAHFBEEHHFHH.......",
    ".............JFBEEEEEEEEEFFNLN.......LMMMAJOEEEEEEEJH.......",
    ".............HFOEEEEEEEEOBFJJN.......LMMFFBEEEEEEEEOH.......",
    "............HHFOEEEEEEEEBBBJJ........KFJFBBEEEEEEEEOH.......",
    "............HFFEEEEEEEEEBBFGG........KLFBBBOEEEEEEEOH.......",
    "............KJBEUSOEEEEOBBJG..........KJBBBBEEEEEOOOH.......",
    "............KJBUTTSEEEOBBFG...........KJBBBBEEEEEYYOH.......",
    "............KJJTTTTOEEEBBFF...........IHFBBBOEEOYTTYH.......",
    "............KLXTTTTTEEOBJF.............IJBBBBEEYTTTaH.......",
    "............KLXTTTTTEEBBLJ.............GLFBBBESTTTTaH.......",
    "............KLXTTTTEEEBJJ...............GFBBBEESTTTaH.......",
    "............KKXTTOEEEOBJJ...............KFBBBEEEOTYYLK......",
    "............HUUEEEEEEOFLJ...............KLFBBEEEEEEEBK......",
    "...........HHBEEEEEEEOFF................KKFBBEEEEEEEFB......",
    "...........KFEPPEEEEEOFH................KFBBBEEEEEEPPBB.....",
    "..........KHBFFJFOEEEEFLK...............KJBBOEEEEEEEEOJBB...",
    ".........IHJQQFOBFBEEEFJK...............KFBBEEEEEEBFBEUBFF..",
    ".........IJOQQBBBBBBEEBJK..............KLFBBEEEEEBBBBUYYOFK.",
    "........ILBOOBBBBBBFEEBJK..............NJFBBOOEEOFBBBBBOOBLK",
    "........IJBBBBBBBBBFFBFJK..............NJJFFFFBOFFBBBBBBBBJK",
    "........IJBBBBBBBBFFJJJJK..............NJJJJJJJJJFFBBBBBBBJG",
    "........GJJJJJJJJJJJJFLHK...............JLLLLLLJJJJJJJJJJJJG",
    ".........GGGGGJGGGGGGG........................LGGGGGGIIIGGG.",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (60, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 60x96).
    scale=int   -> sprite de 60x96 px ampliado por un entero, sin márgenes.
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
