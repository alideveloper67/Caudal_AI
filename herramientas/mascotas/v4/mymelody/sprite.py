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
    "A": (251, 103, 149),
    "B": (252, 244, 245),
    "C": (17, 14, 13),
    "D": (226, 65, 115),
    "E": (234, 214, 214),
    "F": (42, 29, 31),
    "G": (237, 88, 135),
    "H": (108, 43, 63),
    "I": (71, 34, 43),
    "J": (244, 228, 229),
    "K": (252, 172, 198),
    "L": (24, 22, 28),
    "M": (195, 186, 185),
    "N": (24, 22, 28),
    "O": (24, 22, 28),
    "P": (252, 182, 189),
    "Q": (24, 22, 28),
    "R": (139, 53, 80),
    "S": (250, 143, 177),
    "T": (170, 54, 90),
    "U": (24, 22, 28),
    "V": (184, 74, 108),
    "W": (238, 208, 40),
    "X": (213, 88, 127),
    "Y": (140, 115, 31),
    "Z": (206, 178, 37),
    "a": (101, 74, 25),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".............CCCCCCC..........................................",
    ".............CCCCCCC..........................................",
    "...........CCCCAGGGCCC........................................",
    "..........CCHCAAAAAAACC.......................................",
    ".........CCHASSSSAAAARC.......................................",
    "........CIIAASKKKAAAAARCC.....................................",
    "........CIASSKKKKAAAAAGCC.....................................",
    "........CIASKKKSSAAAAAGCC.....................................",
    "........CAASKKKAAAAAAAACC.....................................",
    "......CFAASKKKKAAAAAAAAAC.....................................",
    "......CFASKKKKKAAAAAAAADHCC...................................",
    "......CFASKKKAAAAAAAAAADHCC...................................",
    "......CFASKKKAAAAAAAAAADHCC...................................",
    ".....CCAAAAAAAAAAAAAAAADHCC...................................",
    "....CCRAAAAAAAAAAAAAAAADHCC...................................",
    "....CCRAAAAAAAAAAAAAAAADHCC...................................",
    "....CCRAAAAAAAAAAAAAAAADHCC...................................",
    "....CCRAAAAAAAAAAAAAAAADHCC...................................",
    "....CCRAAAAAAAAAAAAAAAGDHCC.........CCCCCCCCC.................",
    "....CCRAAAAAAAAAAAAAAGDDHCC.......CCCHHHHHHHCCCC..............",
    "....CCRAAAAAAAAAAAAAAGDDHCC.....CCCCAAAAAAAACCCC..............",
    "....CCRAAAAAAAAAAAAAAGDDC.......CCAAAAAAAAAAAVVCCCC...........",
    ".....CCAAAAAAAAAAAAAAGDFC.....CCCAAAAAASKKKKAAAAFFFCC.........",
    "......CHAAAAAAAAAAAGDDDFC.....CCAAAAAAASKKKKSSSAAAACC.........",
    "......CHAAAAAAAAAAAGDDDFC...CCCVAAAAAAASKKKKKKKAAAAACCC.......",
    "......CHAAAXXXXAAAGDDDDFC...CCVAAAAAAAAAAAKKKKKKKAAAACCC......",
    "......CHAAICCCCAAADDDDDFC..CCCAAAAAAAAAAAAKKKKKKKAAAAACCC.....",
    "......CHAILMMMCCADDDDRCC...CIAAAAAAAAAAAAAAAAKKKKAAAAAAHCC....",
    "...CCCCHILOBBBMCCDDDDRCC...CIAAAAAAGGAAAAAAAASSSSAAAAAAAHCC...",
    "...CCCCIIOBBBBBMCHDDDRCCCCCIAAAAAAADDAAAAAAAAAAAAAAAAAAAAHCC..",
    ".CCQEEEIIOBBBBBMCHDDDDAAAAAIAAAAAAADDGGAAAAAAAAAAAAAAAAAAAHCC.",
    "CCQEBBBJJBBBBBBBCUHRDDAAAAAAAAAAAAADDDDGAAAAAAAAAAAAAAAAAAACCC",
    "CCBBBBBBBBOOBBBCUUUURXAAAAAAAAAAAAADTIDGGGAAAAAAAAAAAAAAAAAGCC",
    "CCBBBBBBOYYYQBBBBBBUCXAAAAAAAAAAAAADTTIDDDGAAAAAAAAAAAAAAAAGCC",
    "CCBBBBBOYZWWYQJBBBBBNCXAAAAAAAAAAAADDTCDDDDGGAAAAAAAAAAAAAAGCC",
    "CCCBBBBIZWWWWFJBBBBBNCXAAAAAAAAAAAAAGDTCDDDDDAAAAAAAAAAAAGGGCC",
    ".CCFFBBIZWWWWFJBBBBBNCXAAAAAAAAAAAAAGDDHIIDDDDDDDGAAAAAAADDDCC",
    "...CBBBMUZWWaMJJBBBENCXAAAAAAAAAAAAAAGDDHCIRDDDDDGGGGGGGGDDCCC",
    "..CQBBBBMUaaMBJJBEENNNAAAAAAAAAAAAAAAADDDICIRRVDDDDDDDDDDDTCC.",
    ".CQBBBBBBMMMBBBBFIIINAAAAAAAAAAAAAAAAAAAGDIICCRVVDDDDDDDTTCCC.",
    ".CQBBBBBBMBBBBBBCFHAAAAAAAAAAAAAAAAAAAAAGDDDDCCCCDDDDDDDICC...",
    ".CQEBBBEECJBBBBBCHAAAAAAAAAAAAAAAAAAAAAAAGGDDTCCCCIIIIIICCC...",
    ".CCQEEEEICJBBBBECAAAAAGGGGGGGGAAAAAAAAAAAAGDDTCC.CCCCCCCC.....",
    "..CCLLLIIFFFEEEEHAAAVVTTTTTTTTGAAAAAAAAAAAAADTCC..............",
    "...CCIIIIAHFLLLHHAAICCCCCCCCCCDDDDAAAAAAAAAADDDFC.............",
    "...CCGGAAAAHHHHHHIIMMMMMMMMMMMIIIHGGGAAAAAAAGGDFC.............",
    ".CCRAAAAAAAAAHHHLLLMBBBBBBBBBBLLLHTTTGAAAAAAAGDDCC............",
    ".CCRAAAAAAAAAFCCEBBBBBBBBBBBBBBBBOCCCDDAAAAAAGDDHCC...........",
    ".CCRAAAAAAAFFFEEBBBBBBBBBBBBBBBBBBOOCIIDAAAAAGDDHCC...........",
    ".CCAAAAAAANNNEBBBBBBBBBBBBBBBBBBBBBBBCCCAAAAAGDDHCC...........",
    "CCGAAAAAAANBBBBBBBBBBBBBBBBBBBBBBBBBBBCCHAAAAGDDHCC...........",
    "CCGAAAAAAABBBBMMBBBBBBBBBBBBBBBBBBBBBBBBHAAAAGDDHCC...........",
    "CCGAAAAAABBBBLCMMBBBBBBBBBBBBBBBBBBBBBBBLFAAAGDDHCC...........",
    "CCGAAAFNBBBBBCLMMMBBBBBBBBBBBBBBELLBBBBBLFAADDDDHCC...........",
    "CCAAAAFNBBBJCCCFFOBBBBBBBBBBBBBECCFFNBBBBBAGDDDDHCC...........",
    "CCGAAAFQBBBJCCFCCOBBBBBBBBBBBBBBCCCNNBBBBNCGDDDDHCC...........",
    "CCGGGCQBBBBJCCCCCOBBBBBBBBBBBBBUCCCNNBBBBNCDDDDIC.............",
    "CCCDGCQBBBBJFCCCCOBBBBBUUBBBBBBUCCCCNBBBBNCDDDDIC.............",
    ".CCRDCQBBEEEMFCCQBBBBBYWWBBBBBBUCCCCNBBBBNCDDDDIC.............",
    ".CCRDCQBEPPPEMQQBBBBBBYYYBBBBBBBCCCFMBBBBNCDDDDIC.............",
    "..CCCCCEPPPPPJBBBBBBBBBMMBBBBBBBBCFMJJJBBNCDDVCC..............",
    "...CCCCQPPPPPJBBBBBBUBBBBBBQBBBBBEEJPPPJBNCDDVCC..............",
    "...CCCCQPPPPJBBBBBBBBUBBBBBQBBBBBBEPPPPPPIDDDCC...............",
    "....CCCCPBBBBBBBBBBBBBFFFFBBBBBBBBEPPPPPLIDDDC................",
    "......CCCOOBBBBBBBBBBBBOOBBBBBBBBBBPPPPLITDFF.................",
    ".......CCCCMMEBBBBBBBBBBBBBBBBBBBBJJEPPPHTTCC.................",
    "........CCCCFEEJJJJBBBBBBBBBBBBJJJEEFCCHHCC...................",
    "..........CCCFFJJEEJJJJJJJJJJJEEEEFFFHHCCCC...................",
    "............CCFRJLLLLLLLLLLLLLLLLLHHHIIC......................",
    "...........CCAAARIIIIILCCIIIIIIIIHAGGCC.......................",
    "..........CHVAAAAAAAAIICCDDDGGGAAAAAAGHC......................",
    ".........CHVAAAAAGXXXIIQQVVVGAAAAAAAAAAHC.....................",
    "........CCAAAAAAGCCCCCFQQCCCVAAAAAAAAAACCC....................",
    "........CCAAAAAGCCBBBFFQCBBBBAAAAAAAAAACCC....................",
    ".........CCAAAGFEEBBBBLCBBBBBBFAAAAAAACC......................",
    "..........CFFFFFEBBBBBLBBBBBBBNFHHHHHCC.......................",
    "...........CCCFBBBBBBBLBBBBBBBBNFFFCC..CCCC...................",
    ".............CEBBBBBBELNJBBBBBBBLFEFC.CCCCC...................",
    ".............CCEBBBBENNLNJBBBBEEFLEEECCMMMMCC.................",
    ".............CCEEJJEMNNULEEJJJEUFBBEECCBBBBBCC................",
    "..............CCEEEMMNNUUEEEEEUFBBBBECCBBBBBOCC...............",
    "..............CCFFFFMMBBBEFFFFFBBBBBEOCCBBBBOCC...............",
    "..............CCCFOOBBBBBEOOOOBBBBBBBJOCMBBBOCC...............",
    "..............CCOJBBBBBBBBBBBBBBBBBBBJOCMBBENCC...............",
    "..............CCOJBBBBBBBBBBBBBBBBBBBJOCOEENC.................",
    "..............CCOJBBBBBBBBBBBBBBBBBBBJOCOEECC.................",
    "...............CUOBBBBBBBBBBBBBBBBBBJJOCCCCC..................",
    "................CUBBBBBEEEEEEEJBBBBBJQCCCCC...................",
    "..............CCCBBBBBBEENNNNMJBBBBBJQC.......................",
    "..............CCEBBBBBBEQCCCNMJBBBBBEQC.......................",
    ".............CFEBBBBBBBEQCCNEBBBBBBJEQC.......................",
    ".............CFBBBBBBBEEQCCNEBBBBBJEEC........................",
    ".............CFFBBBBEEENFCCNEEBBBEEECC........................",
    "..............CFFEEEEENFC.CCLEEEEEECC.........................",
    "...............CLLLLLLCCC..CCLLLLLLCC.........................",
    "................CCCCCC......CCCCCCC...........................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (62, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 62x96).
    scale=int   -> sprite de 62x96 px ampliado por un entero, sin márgenes.
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
