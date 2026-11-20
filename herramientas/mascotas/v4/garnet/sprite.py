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
    "A": (44, 4, 22),
    "B": (45, 7, 32),
    "C": (18, 2, 11),
    "D": (136, 3, 50),
    "E": (79, 3, 31),
    "F": (149, 23, 73),
    "G": (30, 3, 16),
    "H": (62, 7, 29),
    "I": (178, 29, 85),
    "J": (212, 34, 91),
    "K": (101, 9, 44),
    "L": (125, 24, 65),
    "M": (118, 7, 49),
    "N": (81, 16, 50),
    "O": (3, 0, 2),
    "P": (163, 6, 64),
    "Q": (215, 5, 89),
    "R": (250, 140, 187),
    "S": (240, 14, 108),
    "T": (243, 88, 150),
    "U": (223, 55, 119),
    "V": (251, 223, 187),
    "W": (251, 174, 209),
    "X": (208, 107, 156),
    "Y": (166, 88, 116),
    "Z": (91, 87, 83),
    "a": (196, 180, 143),
    "b": (151, 128, 106),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............FFFFIII..........................",
    "............FMHHKEAAHKLLAJJJ...................",
    "..........FLAKPRRMMMKEEHAAHHGJJF...............",
    ".........FNAKKRRPMMKKKKKKMKEGGCLFF.............",
    "........FHEMKRRDMKEHAAAAAEEEKKKHAAMA...........",
    ".......FGKMDPDMMEAAAAAAAAAAAAAHHKHCAF..........",
    "......FNEMMMMMMHAAAAAAAAAAAAAAAAAAAGHC.........",
    "......LAMDDMMKEAAAAAAAAAAAAAAAAAAAAACL.........",
    ".....FAKMXFEHAAAAAAAAAAAAAAAAAAAAAAAGKK........",
    ".....LAMXXMAAAAAAAAAAAAAAAAAAAAAAAAAAGK........",
    "....FHEDXFEAAAAAAAAACCCCCGAAAAAAAAAAACF........",
    "....IGMMKAAAAAAAAAAAZWVaaVNBOGGAAAAAACF........",
    "....IAMHAAAAAAAAAAGCZWRVVVVVVVVCGAAAACL........",
    "....IAEAAAAGAAAAGCCCZWRRVVVVVVVaCAAAACF........",
    "....IAAAAGGHAAAAGCCCZWRRRVVVVVVaCAAAAGF........",
    ".....KGGGCHEAAACCCCCZWRRRRVVVVVaCAAGCHL........",
    ".....OOCCHKAAAGCCCCCBRRRRRRYYVVaOCAACL.........",
    ".....FOGHMEAAACCCCCCAPFRRRIJIYVaOCGACF.........",
    "....FHAKKKHAAGCCCCCCHJJFRIJIFFJLOCCAGEL........",
    "....FAKMKHGGGCCCCCCCHJJJJJLFIJJFOCCGAGF........",
    "....FHKEAGCCCCCCCCCCHJJJJJJLKNJFOCCGAGF........",
    "....FHEGCCCCCCCCCCCCHJJJJJJNNLJLCCCGAGL........",
    "....FGACCCCCCCCCCCCCGMJJJJJJJJJHCCCCGGL........",
    "....FCCCCCCCCHHACCCCOOGPPFFJJJKOCCCCCCL........",
    "....FGCCCCCDCSSSPKCOOOAPPPAOOOOOCCCCCGF........",
    ".....KOCCAQSWWSSQSDCOOAJJIAOOOOOCCCCCK.........",
    ".....KKOGQSWWSSQQQSDOCHFFIHOOOCEMKAOAA.........",
    "......FLMSSSSSQQQQQSHHWSSSPKOEPQQQUDNM.........",
    ".......LLSSQQQQQQQQQMYWWSSSSQKHPPQUUDF.........",
    ".......LQQQQQQQQQQQQDYRWWRSSQQPKPQQQQNL........",
    ".......LDQPPPPPPQQQQDYRRRWWWRTTDKPQQQKI........",
    ".......FADEHMPPPPQQQARRRRRRWRTQQHPPQQKI........",
    ".......FKLJDHKPPPPPPNRRRRRRTQQQQEDPPPHI........",
    "......FLYTJJPEKPPPPARRRRRRTQQQQQKMPPKM.........",
    ".....FKYTJJJPDAPPDHLRRRRRRRTPPQQEDPEHFK........",
    "....FNUUJJJIPHAMECLJUUTTTTTTTPPPAMAMULNK.......",
    "...FNUUJJJIPHKGCGHPJJJIIIITTTTPEOGPJJULLK......",
    "..FEUUJJJPDHLAMLFKAFKHCCCCCNLTFGKHPPJJULMF.....",
    ".JHAFEHKPKHMCOOOOKKOOCCCGGAEHGCLNLEPIJJJEM.....",
    ".JAMAAAAGHLOOOOOOOHOOCCGBBBMMGGNOCLEPILLJHF....",
    ".JGAAAAAAHHOOOOOOOOLCCCABBBDPENOOOGFGAAAHHF....",
    "..NCAAAAAGLOOCAAAALKCGBBBBBDPENOOOOLCAAAACF....",
    "..FAAAAAAAHLNFKKLFABNBBBBBBMDELEMLLFCAAAAGF....",
    "...LCAAAAAGHNBHIFCNNBBBBBBBMDDHMHHEAAAAAAN.....",
    "...LKCAAAAGGHLFJIIABBBBBBBBMDDDALJJMGAAAGF.....",
    "....NKCAAAAABEJIIFCBBBBBBBBMDDDELLJJNGAGF......",
    ".....LLAGAAAAFIJIHGBBBBBBBBMDDDMCFFJJAGLF......",
    "......MFGGAAAFJIMCBBBBBBBBBMDDDDKAJFJACF.......",
    "........FHCGCHIKCABBBBBBBBBMDDDDDEAAMCK........",
    ".........LFOOGACAHBBBBBBBBBMKDDDDDHAOAF........",
    ".........LNCCGANNNBBBBBBBBGEEDDDDDDHNF.........",
    ".........NCHHNNNNHBBBBBBBGGGMDDDDDMDAA.........",
    ".........KBNLXFNNBBBBBBBGOCHMDDDDDDPAF.........",
    "........FANNXXNNBBBBBBBBCOAEMDDDDDIIEL.........",
    "........FGNLXLNNBBBBBBBGCGEEMDDDDDPPENF........",
    "........LBHLXNNBBBBBBBBGCAEEMDDDDDPPDAI........",
    "........FBHNNNHBBBBBBBACCEEEMDDDDDDPDAI........",
    "........FBHNNNBBBBBBBBGOHEEEEDDDDDDDDAI........",
    "........FBHNNNBBBBBBBBCOHEEEEDDDDDDDDAI........",
    "........FBHNNBBBBBBBBGCEHEEEEDDDDDDDMGI........",
    "........FABNHBBBBBBBGCHFGEEEEKDDDDDDKEL........",
    "........AAHBBBBBBBBBCOLKGEEEEKDDDDDDKF.........",
    ".........KBBBBBBBBBGCNMNNAEEEEDDDDDDHF.........",
    ".........FGBBBBBBBBCGL..LGEEEEMDDDDMAF.........",
    ".........FCBBBBBBBGCL...LNHEEEKDDDDMNF.........",
    "........NKCBBBBBBGCNL....FGEEEEMDDDHK..........",
    ".......LLGNBBBBBBCAL......FGEEEEDDDGG..........",
    "......MLBNNNBBBBCCF.......NGGEEEMDDGG..........",
    "......FGNNLHBBBGCKF........FGEEEEMDAF..........",
    ".....FHHYYNBAGGCOF.........NHEEEKDDMEF.........",
    ".....FCHFNBBBCCCCF........IAEEEEDDDKAF.........",
    ".....EBNNHBBBCCCCF........IGEEEKDDDMEI.........",
    "....BBBNBBBBACCCCF........IGEEEKDDDDKKI........",
    "....FCBHBBBBGCCCNF........IGEEEKDDDDDGJ........",
    "....FGBBBBBBGCCCL.........IGEEEKDDDDDAJ........",
    "....FGBBBBBACCCCF.........LKHEEKDDDDDAJ........",
    "....FGBBBBBGCCCKI..........FGEEEMDDDDAJ........",
    "....FGBBBBBCCCGI...........FEHEEKDDDDAJ........",
    "....FGBBBBGCCCM.............FCHEEMDDDAJ........",
    "....FCBBBBGCCAF.............LMAEEEDDDAJ........",
    "....FCBBBACCOL...............FHHEEMDDAJ........",
    "....FCBBBGCCAL................FGEEKDDAF........",
    "...JNGBBBCCCL.................ICEEEDDEKK.......",
    "...JCBBBBCCGF.................IEHEEMDDHK.......",
    "...JCBBBGCGAJ..................LHEEMDDAF.......",
    "...FCBBBGCIHJ..................FFFEEDDELN......",
    "...KGBBBGCIHJ..................FLUEEDDMHF......",
    "..FEABBBGCIHJ..................FLUEEDDDMAFN....",
    "..FCBBBBGCIHF..................LLUEEKDDDMHLL...",
    ".FBAGCGACCILF.................JAUUEEEMDDMECHF..",
    ".FGGGSSKGCIFF.................JHUUKEEEMKTTTWNF.",
    "LHGGRSSSDCNIF.................JHUUFEEEETTTRWWKK",
    "FMGRSSSSQEGIF.................JHUUFEEEFJTTTRRLF",
    "FKSSSSSQQKCGI.................IKCGGAAAHJJTTTTLF",
    "IHEEEEEEHKFI...................IIIILMHHHEEEEHHJ",
    ".IIIIIIIIF...........................IIIIIIIIJ.",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (47, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 47x96).
    scale=int   -> sprite de 47x96 px ampliado por un entero, sin márgenes.
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
