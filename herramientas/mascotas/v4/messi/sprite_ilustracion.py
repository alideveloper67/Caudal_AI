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
    "A": (27, 15, 14),
    "B": (16, 9, 9),
    "C": (250, 186, 139),
    "D": (19, 31, 98),
    "E": (50, 26, 26),
    "F": (169, 10, 52),
    "G": (116, 7, 41),
    "H": (238, 154, 108),
    "I": (79, 49, 28),
    "J": (14, 23, 76),
    "K": (14, 18, 53),
    "L": (120, 73, 36),
    "M": (15, 14, 28),
    "N": (158, 98, 64),
    "O": (79, 11, 40),
    "P": (205, 127, 77),
    "Q": (46, 27, 77),
    "R": (177, 138, 113),
    "S": (110, 80, 70),
    "T": (156, 116, 16),
    "U": (204, 147, 11),
    "V": (56, 66, 137),
    "W": (245, 195, 19),
    "X": (244, 219, 201),
    "Y": (189, 44, 85),
    "Z": (147, 149, 179),
    "a": (251, 221, 96),
    "b": (226, 144, 170),
    "c": (194, 204, 232),
    "d": (222, 78, 21),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..........................................BBBB...............................",
    ".......................................BBBAAABBB.............................",
    "......................................BAAAEAIIIAB............................",
    ".....................................AAAALLPIINNAB...........................",
    "..................................ABAALLPPLIPNINIAB..........................",
    ".................................BAEEELLRRLEIIELLEAB.........................",
    "................................BAAEXXEEIIIEBEIAEEAA.........................",
    "...............................AAEEIEAMIEAAABAABEEAB.........................",
    "..............................BAESIIIAAABBBBBBBBEIAB.........................",
    ".............................BAASREIEBBBBBILLLIBEAAB.........................",
    ".............................AAARAIEBBBBBPPCCCCCAABB.........................",
    "............................BAERREEABBABCCCCCCCXXEAB.........................",
    "............................AEIRIEBBBAECCCCCCCCXXRAAB........................",
    "............................ALIIIABBBAIIHCCCCCCCCXRAB........................",
    "............................AILIEAAAAIIIHCCCMMMICCCIAB.......................",
    "............................AILEAAAAEIIHCCHNMMMEHHCIAB.......................",
    "............................AILAAAAAEIIHCCHNQMAHCbEAAB.......................",
    "............................AIIAAEIIIIIHCCCCCMIHHCbEAB.......................",
    "............................AAAAARRCIIIHCXXCCCCCHHCAAB.......................",
    ".............................AAARRISCIHHCCXXCCCCHHHAAAB......................",
    ".............................BAAHHHSSCHHCCCCCCCHHELASAB......................",
    "..............................AAHHCNNCHPHHCCCCCHNLLSRAB......................",
    "..............................AAHHCNNCCPPPHCCCCPNNLNRAB......................",
    "..............................BAICHCNHCPPPPHCCPNLNNNNAB......................",
    "...............................BAECCCHHPPPPPCPNLSSSEAAB......................",
    "................................BAEEEIHPLLPPPPPCCHHAAAB......................",
    "................................BAABEHHHIILLPNNHCNNHAB.......................",
    "..........................BBBBBBBABBHHHHIEIINLLNHPPPAB.......................",
    ".........................BAAAAAAABBEHHCHPIAEILLLNLPLAB.......................",
    "........................BAAEEEEEKKBBHHCCHPIAAEILIILAAB.......................",
    ".......................BAAEYYYYYODJBHHCCHHPLEAABBBAAB........................",
    "......................BAAEYYYYYYFQDJBHCCCCHHLEEBBBAABB.......................",
    ".....................BAASYYYFFYYFFDDKECCCCCHHLLBMGGAAAB......................",
    "...................BAAAKQSYFFFFFFFDDDKECCCCHPPEMJFFYAAAB.....................",
    ".................BBBAAZZZDGFFFGFFFQDDDJACCCHPIMJDQFYYOAAB....................",
    "......BBBB......BAAAEQZZDDDGFGGFFFQDDDDJELTTIMDDDQFFFFQAABB..................",
    ".....BBAAAB.....BAVVVVVDDDDQGGGFFFQDDZDQFLWWIQJJDQFFFOVVAAAB.................",
    ".....BARRAAB.BAAAAVVVDDDDDDJOOGFFGQZZVDQFGWLGLPPTTGGGQDVVEAAB......BAAAB.....",
    ".....BARCRIAEAAEEEBDDDDDDDJJEEGFFGDZVDDQFFWLGLPPPTGGGJDDVVVAAB....BAESEA.....",
    "..BBBBBERCCIEEXXXXIBKDDDDJJKKAFFEODDDDDQFFGGGPPPUUGOKDDDDVVBAABB.BAESEIA.....",
    ".BAAAAAEHHCCCXXXCCCIMDDJJKKMBOOAOFQDDDDQFOMFOIMEMIGBKJDDDDMSSEEEAAASCCEABBB..",
    "BAARRRRHHHCCCXCCCCCCAKDJKMMBBEEOGFQJJJDQFGOFOIEOAOOBKJJJDKECXXXEIERCCCAAAAAB.",
    "BECCCHCCHHHHCCCCCCHHEMJKMBBBMMOGGFQJJJJOFFFFOJIEIOAMKKJJJMCCCXXCRRCCHCRRRREAB",
    "BICCIIHCHHHCCCCCHHPPABMBBBABKEGGFFJJJJJFFFFFOKKEGGBBMKJJMCCCCCCCCCCCHHCHHCCEA",
    "BAACCCHCCCCCCHHHHAAAABBBB.BAKOGGFFJJJJQFFFFGMKKOGABBBBMMBCHHCCCCCCHHHHCCCCCEB",
    "BAECPPHHCCCCCAAAAAABBB.B..BAKOGFFQJJDDFFFGOOKMOGGABBBBBBAIIHHHHHHCCCHCCHCCEAB",
    ".AAEPHHSCCIIEABBBBB.......AABGFFFJDDDDQGGGGOKKGGABB..BBBAAAEIIIICCCCCCHNHAEA.",
    ".BAAAASCCIAAAB...........BAMEGFFODDDJKOGGGGQJJGGAB........BAAAAAEAACCRNHHAAA.",
    "..BAAAAAAAAB............BAQQGGFFJDKKKKOGGGGJJJGEAB.............BAAAICCRIIAA..",
    "...BBAAAAB..............BAJGFYYFKKKKKEGGGFGJJOEAB................BAAAAAAABB..",
    ".....BBBB..............BAAMYYFGGKKJKJGGFFFGJKGEA...................BBAAAB....",
    "......................BAAAOGGGGGJJJDDFFFFGEKKGOA....................BBBB.....",
    "......................AAIAGGGGGOKKJJQGGGGOKMOOEA.............................",
    ".....................BAEAFFGGGFQJJKKOGGGOEKKGEAA.............................",
    ".....................AAOYFFFGGGQDDJQGGGGOKKJFEA..............................",
    ".....................AAOYFFFFFOJKKJQFFGFEKJQFEA..............................",
    ".....................ABBBAGGFFQDDJKOGGFFGJJGFEA..............................",
    ".....................BAMKMMAEOKJDDDGGOOGEKKGOAA..............................",
    "......................AKDKMMMMMMKJDFFFGOKKKGAAB..............................",
    "......................AQVJTMEMTKBBBGFFFGJKQFAB...............................",
    "......................AQVDTTTTTTJKKMBAOOJJQFAB...............................",
    ".....................BAQVDTTTITIDJKKKMBBMMMOAB...............................",
    ".....................AEDVJTLUEUQDDKKJKMMMBAAAB...............................",
    ".....................AQVDETLTUUJDDDMKJJMKKAAB................................",
    "............BAAAAB...AQVDDITLIKDDDDKBKMMKKAB.................................",
    "...........AENNAEABBBAEQDDDIIIDDDDDJMMMKKMAB.................................",
    "..........AAXXaWLAAAAAAKDDIEIIJDDJDDKBMJMAB..................................",
    "..........AAXaWLAEZZVMAMJDEIIEDDDDDJKBMMAA...................................",
    ".........BAAaWWEZZVVDGFEKJDJKKMAAAAKMBMAA....................................",
    ".........BAAWWIDVVDDEGGEMKDKMAINNNNEBBAAB....................................",
    "........BAIWWTBDDJJJOFGMEEMAIHHCCCCSEBAB.....................................",
    "........BAAWWTBJJJJJOFGBLNAAHHCCXXCCSAB......................................",
    ".......BAAAWUTBBMMKKEGGBLPNAACCCHCCHSA.......................................",
    ".......BAAWUUTIBBBBBAOGOENPIERCCHHHIEA.......................................",
    ".......BAaWUUTIABBAAAAAAAIIESRRCEEIIAB.......................................",
    ".......BAaUUUTAAB...BABAAAAASSKQOOQMA........................................",
    ".......BAAUUUAAB........BBBAMQYYFFFGAB.......................................",
    ".......BAIUUIAA............AObbFFFFFOA.......................................",
    ".......BBAIIAAB............AGYYFOEEOOA.......................................",
    "........BAAAAB.............AGFEMJDDJMA.......................................",
    "...........................AEAJDDDDDKA.......................................",
    "...........................BAMDVDDDDKA.......................................",
    "............................AMDVDDDDKA.......................................",
    "............................AAQVDDDDKA.......................................",
    "............................BAADDDDDKAB......................................",
    ".............................AADDDDKMAAB.....................................",
    ".............................BAMDDKWWAAB.....................................",
    "..............................BADJIWWUIAAAB..................................",
    "..............................AAJMWWWWUaIAAB.................................",
    ".............................BAAAWWXXWaaaAAAB................................",
    ".............................BATWWWWaaWWWWUAB................................",
    ".............................BATWWWWWWUUUUUAB................................",
    ".............................BATUUUTTLUIUUEAB................................",
    ".............................BAAAAATLAIEEIAB.................................",
    "..............................BAAAAAAAAAAAB..................................",
    "...............................BBBBB.........................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (77, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 77x96).
    scale=int   -> sprite de 77x96 px ampliado por un entero, sin márgenes.
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
