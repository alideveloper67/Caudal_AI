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
    "A": (15, 13, 14),
    "B": (40, 35, 43),
    "C": (19, 11, 11),
    "D": (28, 24, 29),
    "E": (251, 185, 113),
    "F": (2, 187, 249),
    "G": (34, 38, 59),
    "H": (99, 107, 170),
    "I": (6, 88, 218),
    "J": (221, 137, 88),
    "K": (59, 60, 91),
    "L": (117, 83, 55),
    "M": (14, 62, 92),
    "N": (5, 164, 226),
    "O": (172, 102, 67),
    "P": (80, 86, 133),
    "Q": (75, 53, 36),
    "R": (37, 79, 181),
    "S": (9, 106, 137),
    "T": (7, 144, 184),
    "U": (4, 120, 228),
    "V": (2, 206, 220),
    "W": (117, 217, 248),
    "X": (29, 65, 138),
    "Y": (209, 239, 249),
    "Z": (54, 199, 248),
    "a": (147, 181, 212),
    "b": (54, 131, 229),
    "c": (193, 193, 193),
    "d": (114, 114, 113),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".........................................CCCCCCCA........................",
    "......................................AACCDDDDDDCAAAA....................",
    ".....................................CCCCBGGGGGGDCCCCC....CCCCCCCA.......",
    "..................................ACCCDBKPPPGBDDADDDDCCCCCCCDBBDDCA......",
    "..................................CCCDGGPHHPGDAADGGGGBCCCCCAGGGDDDACC....",
    "................................ACCDGPPPHHKGDDBGGGGGBDAAADDDDDDA..CCCA...",
    "................................CCCBKHHHHHDDADGGGGGDAAAAABGBACCC....CC...",
    "...............................CCDBGKHHHKGABPPPKGGDAAAAABGGGBBDCC........",
    "..............................CCDGGPPHHGDAPPHHHKGAAAAAAAGBDBGGGBDCA......",
    ".............................CCDGGGPHHKADBHHHHHKBDDDDAADGBCDBBBBBCAA.....",
    ".............................CDGGGDDDAAAKHHHHKAAAKHHDGGGGBCCCCCDBGDAA....",
    "............................CADGGGAADAAAKPPPPGABBHHHKGGGBDCCCCCAABBBDCCCD",
    "...........................ACGGGDAAAAAABBGDAAAAHHHHGGGGGAACCCAAACADBBDDCA",
    "...........................ACGGBDAAAAAABDDAAADDHHHKBDGGDACCDCABDACCACAAA.",
    "..........................AACGBAAAAAAAADAAAADBGPPGADBDDACCQELCDBDCCCC....",
    "..........................CDBGDAAAAAAAAAAAADGGGDAAABGAAACOEELCCBBDCCCAA..",
    "..........................CDGDDAAAAAAAAAAADBGBDAAAADDACDOEEELCCDDBCAACCC.",
    "..........................CCDAAAACCCCAAAAABGGDAAAAAAACCOEEEELCCAABC.ACCCC",
    "..........................CCAAAACOOOODAAAABBDAAAAAAACCCLLEEELCCCADCA..ACC",
    "..........................CCCAACEEEEEODAAAAAACCAAACCMUMAAQEELCCCCACC...C.",
    "..........................AACAADEEOOOEODAAAACCCAACAUUUUMAAQELCCCCAAC.....",
    "...........................CCACDEJOOOOEQCAACCLCCCCMUUXMMAAAQDCCCCAAC.....",
    "...........................CCCCDEOJJJOEQCAADELACCCAMUUMMAAAACCCCCAACCC...",
    "...........................CCCCDEJJOOOEELCQEELCEEEADMUUYYADAAACCC.ACCC...",
    "...........................CCCCDEEJOOOEELQEEEQEEEEAADDUUDAJEQA.CC...CC...",
    "..............................CACJEJOOOEEEEEEEEEEEQEEEDDDJEEED...........",
    "..............................CACCEEEOOEEEEEEEEEEEEEEEEEEEEEEQC..........",
    "............................DCAAAACEEEEEEEEEEEEEEEEEEEEEEEEEEEBC.........",
    "...........................CCCAACACBQQQQEEEEEEEEEEEEEEEEEEEEEEQC.........",
    "...........................CCCCACACQLLLDLEEEEEEEEEEEEEEEEELQQQD..........",
    ".............................ACCCCAEJJJQLEEEEEEEEEEEEEEEEEELCC...........",
    "..............................CCCCEEEEEQLEEEEEEEEEEEEEEEEEELA............",
    "...............................ACQEEEEEQLEEEEEEEEEEEEEQQQQLDC............",
    "...............................ALEEEEEEEQQEEEEEEEEEEEEJJJJDC.............",
    "...............................CLEEJJEEEECCEEEEEEEEEEEEEEEB..............",
    "..............................CQEEEJJEEEEJCCCEEEEEEEEEEEEEB..............",
    "..............................CJEEEJJEEEEEJOCCBEEEEEEEEEEED..............",
    "..............................CJEEEJJJEEEEEJOODQQQEEEEEEEED..............",
    ".............................ACJEEEJJJEEEEEJJJJDCCLLEEEEEED..............",
    "............................ACCQLLLJJJEEEEEEJJJOOCCCLLLLLLD..............",
    ".........................AAACCAAAAAJJJEEEEEEEJJJJDA.CCCCCC...............",
    ".........................CCDDBBDAAAQQQEEEEEEEEJJJD.......................",
    "......................CCCCBGKHHGDAAAAAAEEEEEEEEJJD.......................",
    ".....................ACKKKPPPKKDAAAAADAQLLLEEEEJLC.......................",
    "..................ACCCCPHHHKDAAAAAAADBDAAAAQEEELCC.......................",
    "..................CCBKPHHGDDAAAAAAAADBBBDAADBEELC........................",
    "...............CCCCAKPHHHDAAAAAAAAAADBBBBAAAAAELC........................",
    "..............CCAAADHHHKAAAAAAAAAAABBBBBBBAAAAACC........................",
    ".............CCCDPPPKKBDAAAAAAAAAABBBBBBBBDAAAACC........................",
    "..........AAACADBKKKDDAAAAAAAAAAAABBBBBBBBBDAAACC........................",
    "..........CCACABBBDAAAAAAAAAAAAAAAADBBBBBBBBAAACC........................",
    "........AACCNNAAAAAAAAAAAAAANNNNNNNMAADBBBBBDAACC........................",
    "........AAGZZZNMDAAAAAADMMMFFFFFFFFFMMDDBBBBBAACCA.......................",
    ".......ACAWWYNNIMAAAAAAMFFFFFFFFFFFFFFAABBBBBBDACCA......................",
    "......AAATWYYbIIRXAGFFFFFFFFFFNFFFFFFFFMABBBBBBDDACAAA...................",
    ".....ACMTWYYbIIIIRAGFFFNUUUUINFFFFFFFFFSAAAABBBBBDCCCC...................",
    ".....ACMFYYbIIIIINNZWZFNIIIIIFFFFFFFFFSGNNNAAAABBBBDACCC.................",
    ".....ACMFFIIIIIINFZWWZFNIIIIIFFFFFFFFSSMFFFFMMGDDDBBACCC.................",
    ".....ACMFFIIIIIIFFWWFFFNIIIIIFFFFFFFFASFFFFFFFFAAADBBAAAA................",
    ".....ACMFUIIIIIFFWWWFFFNIIIUNFFFFFFFMFFFFFFFFFFTTTAAADDAAAA..............",
    ".....ACMFUIIIIIFFWWFFFFNIIIUNNNNNNNMGFFFFFFFFFFFFFGGGDDAAAA..............",
    ".....ACMFUIIIIIFFFFFFFFNIIIMAAAAAAAAMFFFFFFFFFFFFFFFFDAAMMAA.............",
    "......ADGIIIIIIFFFFFFFNUIMMDAADDAAAAMSFFFFFFFFFFFFFFFSSSGSSAA............",
    ".......AADIIIIIFFFFFFNUIAAAAADBBDAAAAASFFFFFFFFFFFFFFFFFDFFAAA...........",
    "......ACAAAIIIIFFFFFFGAAAAAAABBBAAAAAAAAAMFFFFFFFFFFFFFFFFFFDA...........",
    ".....CCCDAAGIIIFFFMMMAAAAAADBBBBAAABBBDAAGNNNFFFFFFFFFFFFFFFGAA..........",
    ".....CDGHGAAAGAFFFAAAAAAAAABBBDAAABBBBBBBDAAAFFFFFFFFFFFFFFFFSC..........",
    ".....CKHHKGAAAASSDAAAAAAAABBBDDAAABBBBBKHHGGDMTTTFFFFFFFFFFFFSC..........",
    "...ACCKHHHPAAAAAAAAAAAAAAABBBAAAAAABBBBGHHHPBDAAASFFFFFFFFFFFSCA.........",
    "...CCKHHHHPDAAAAAAAAAAAAAADDDAAAAAADDBBBKKHHPGDDDMSSFFFFFFFFFFSCC........",
    "...CDHHHHKGBDAAAAAAAAAAAAAAAAAAAAAAAABBBBGHHHKBBBAAASFFFFFFFFFNAA........",
    "...CDHHHDAABBDAAAAAAAAAAAAAADDCAAAAAAADBBBGGGHHKBBBDAMFFFFFFFFNCA........",
    "...CDHHPAAABBBAAAAAAAAAADDDDDDCAAAAAAADDBBBBBKKKBBBBDDFFFFFFFFCCA........",
    ".AACDHPGAAABBBAAAAAAAAADBBBBBDCAAAAAAAAABBBBBBBBBBBBBADFFFFFFFXCA........",
    ".ACKHHKAAAABBBBBBBBBBBBBBBBBBDCADBBAAAAAAAAAADBBBBBBBBDATFFFFFACC........",
    ".ACKHHKAAAABBBBBBBBBBBBBBBBBBDCADBBDAAAAAAAAADDDDDDDDDDAGTFFFMACC........",
    ".ACKHHGAAAABBBBBBBBBBBBBBBBBBDCADBBBDAAAAAAAAAAAAAAAAAAAAAFFGAACC........",
    ".ACKHAAAAAABBBBBBBBBBBBBBBBBBDCADDBBBBDAAAAAAAAAAAAAAAAAAAMFDCCCC........",
    ".ACKHAAAAAABBBBBBBBBBBBBBBBBACCAAAABBBBBBDAAAAAAAAAAAAAAAAADACC..........",
    ".ACBGAAAAADBBBBAAADBBBBBBBBDCAAAAAAADBBBBBDDDDDDDDDDDDDDAAAAACC..........",
    ".ACDDAAAAABBBBBAAADBBBBBBBDDCAAAAAAADDBBBBBBBBBBBBBBBBBBDAAAACC..........",
    ".ACCAAAAADBBBBAAAADBBBBBBBCCCAAAAAAAAADBBBBBBBBBBBBBBBBBBBAACCC..........",
    ".ACCCAAADBBBDDAAADDBBBBBBDCCAAAAAADAAADDDDBBBBBBBBBBBBBBBBDACA...........",
    "...ACAAABBBBDAAAADBBBBBBDCCAAAAAADBDAAAAAABBBBBBBBBBBBBBBBDACA...........",
    "...ACAAABBBBAAAAABBBBBBAACDDAAAAADBBBBBDAAADBBBBBBABBBBBBBBACA...........",
    "...ACAAABBBBAAAAADBBBBDACARGAAAAADBBBBBBAAAADBBBDAAAAAAAABBACA...........",
    "...ACADBBBBAAAAAAAADDDACAGRGAAAAAAABBBBBBDAAADBBDAAAAAAAABBACA...........",
    "...ACDBBBBBAAAAAAAAAAACDMRRGAAAAAAADBBBBBDAAADDDAAAAAAAAADDACA...........",
    "...ACHKBBBBAAAAAAAAAAACRRRRGAAAAAAAADBBBBBDAAAAAAABBBBBAAAAACA...........",
    "..CCDHKBBBBDAAAAAAACCCCRRRRXXAAAAAAAADBBBBBDDAAADDBBBBBDAAAC.............",
    "..CGHHKBBBBBBDAAAACDMMAXRRRRRAAAAAAAAADBBBBBBAABBBBBBBBBAAAC.............",
    "..CGHHKBBBBBBBAACCCVVTAAGRRRRRMAAAAAAAAAABBBBAABBBBBBBBBADDC.............",
    "..CGHHKDDBBBBBDACMVVVTAAGRRRRRMAAAAAAAAAAADDDAABBBBBBBBBADDC.............",
    "DCDKHKDAADBBBBBACSVVVVTSGXXRRRMAAAAAAAAAAAAAAAABBBBBBBBBADCC.............",
    "DCPHHAAAAABBBBBDCSVVVVVSAAAXRRMAAAAAAAAAAAAAAAABBBBBBBBBACCA.............",
    "DCPHHAAAAAABBBBBCSVVVVVSACAXRRRXAAAAAAAABBBBDAAAAAAAAAAAACC..............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (73, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 73x96).
    scale=int   -> sprite de 73x96 px ampliado por un entero, sin márgenes.
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
