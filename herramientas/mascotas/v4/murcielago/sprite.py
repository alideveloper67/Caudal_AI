#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python sprite.py                 -> guarda sprite.png
      from sprite import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (3, 2, 4),
    "B": (228, 139, 210),
    "C": (135, 95, 179),
    "D": (129, 91, 173),
    "E": (141, 98, 185),
    "F": (119, 78, 164),
    "G": (107, 65, 152),
    "H": (210, 121, 197),
    "I": (192, 106, 187),
    "J": (19, 11, 25),
    "K": (92, 54, 135),
    "L": (178, 116, 201),
    "M": (41, 25, 55),
    "N": (80, 50, 108),
    "O": (165, 91, 172),
    "P": (153, 107, 195),
    "Q": (61, 39, 85),
    "R": (245, 207, 60),
    "S": (226, 125, 126),
    "T": (114, 74, 122),
    "U": (95, 29, 39),
    "V": (171, 113, 148),
    "W": (177, 44, 54),
    "X": (203, 164, 100),
    "Y": (240, 88, 96),
    "Z": (168, 167, 168),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "............................................................................AAAAA...........",
    ".........................................................................AAAAAAAAA..........",
    "...........AAAAAAAA....................................................AAAAAAAAAAAA.........",
    "..........AAAAAAAAAAAAAAA...........................................AAAAAAAAEEEAAAA.........",
    ".........AAAANNNNNJJJAAAAAAA.......................................AAAAAAPPPEFEAAA..........",
    ".........AAAANEEECCEPPPAAAAAAA...................................AAAAAAAACCGGGFAAA..........",
    "..........AAANDDDFFEEPPDAAAAAAAA................................AAAAACADFFGGGGAAA...........",
    "...........AAAADKKFFEDDCCCCCAAAAAA............................AAAJAEPCDFGNGGBGAAA...........",
    "............AAMIIKFFKKDDDCCCCPAAAAA..........................AAAJJLPEDFGNOHBBAAA............",
    "............AAAMBHHHKKKKKCCCCCPDAAAAA.......................AAAAELPEEDGNOHBBHAAA............",
    ".............AAABBBBHKKKKKCDDDDCCAAAAA.....................AAAQELPEPEGNNHBBBHAAA............",
    "..............AAABBBBBHHIINNDDDDCPPAAAA...................AAAQPPEPEEFNOHBBBBVAAA............",
    "...............AABBBBBBBHIINQDDCEEEPAAAAA................AAAAEPEEEEFNOHBBBBBVAAA............",
    "...............AAJBBBBBBBHIIIQFCEEEPEFAAAA..............AAAJFEEEEEFNNHBBBBBBVAAA............",
    "...............AAJBBBBBBBBHIIONFEEEEPEFAAA..............AAJFEEEEECNNNHBBBBBBVAAA............",
    "...............AAJBBBBBBBBBBHHONECCCEPPFJAA............AAAFDCEECCNNNIBBBBBBBBAAA............",
    "................AATBBBBBBBBBBHHONNFCCEEENJAA..........AAAADDCEECCFQIBBBBBBBBBAAA............",
    "................AATBBBBBBBBBBBHINNFCCEEDDNAAA...AAAAAAAAAGDDEEECFQFIBBBBBBBBBAAA............",
    "................AATBBBBBBBBBBBBIINNCCCEDDDAAAAAAAAAAAAAAAGFFEEEEFQIIBBBBBBBBBBAA............",
    "................AATBBBBBBBBBBBBIHNNCCCDDDCAAAAAAAAAAAAAAAAAFFEEFFQIIBBBBBBBBBBAAA...........",
    "...............AAJBBBBBBBBBBBBHIHHNKDDDCDCDAAAAAPPACCCDNNAAAJEFFNNIIBBBBBBBBBBAAA...........",
    "...............AAJHBBBBBBBBBBBHIHHHQKDCCCDGDDPEEECDDDCDDNCCCJJJJTTIIIBBBBBBBBBAAA...........",
    "...............AAJHBBBBBBBBBBHHHHHHQNKDDFGDEEPCCCDDDDDXDDCCCDJJJATIIIIHBBBBBBBAAA...........",
    "...............AAJBBBBBBBBBBHHHHHHHNMKFDFCCCCCCCDDDDXRXCDDCDDDDJJAIIIHBBBBBBBBAAA...........",
    "...............AAJBBBBBBBBBBBHHHHHHHJMFFCCDDCCDDDDDXRRCCDDCDDDCCNAATBBBBBBBBBAAA............",
    "................AABBBBBBBBBBBBHHHHHHJFFCCCDDDCDDDDDRRRCCDCCDDDDCCNAATBBBBBBBBAAA............",
    "................AAABBBBBBBBBBBBHIIHQGFDCCCCDDDDDDCXRRRCDDCCXVDDCCDQAABBBBBBBAAAA............",
    "................AAAABBBBBBBBBBHIIIQGFDDCCCCDDDDDDCXRRRRDDCXRVDDDDDDQAMBBBBBIAAA.............",
    "................AAAAHBBBBBBBBBHIIQQFDCDCCCCCDDDDDCCRRRRRRRRRVDDDDDDDMATBBBIOAAA.............",
    ".................AAAAHHBBBBBBBBHIQQDCCCDCCCCDDDDDCCRRRRRRRRRDDDCDDDCMAATBIOAAA..............",
    "..................AAAAHHHBBBBBBMMQQDCCCCCCCCCDDDDDDCRRRRRRRDDCCCDDDCDMAAAAAAA...............",
    "...................AAANOOOHHHHHMMGDCCCCCCCCCDDDDDDDCCDVVVDDDDCCFJDDDDDAAAAAA................",
    "...................AAAANOOOOOOOMGFDCCCCCCCCDDDAMFDDCCDDDDDDDDCFJJJDDCDAAAAAA................",
    "....................AAAAAAAOOONNGFDCCCCCCCCDDAAZMFDDDDDDDDDDDCCJJJDDDCAAAA..................",
    "....................QQJJAAAAAAANFDCCCCCCECCCAAAZMMDDDDDDDDDDDCMAJAADDCDAA...................",
    ".................AAAAAAJMJJJAAANFDCCCCCEECCMAAAAAMDDDDDCCDDDDCMAAAADCCDAAA..................",
    "...............AAAAAAAAAAMQQJAAKFCECCCCEEECMAAAAAMCDDDCEPPDDDDDAAAADCCCAAAA.A...............",
    ".............AAAAAAATTNAAAQQAAMKFCECCCEEEECMAAAAACCCCCEEPPPDDDDAAAQCOOCCAAAAAAA.............",
    "............AAAAAAPPPPPNAAQQAAMKFFCEEEEEESSSMAAAAEECCDCCEEEDDDCCAQCSSSOCAAAAAAAAA...........",
    "..........AAAAPPPCCPFFFFAAAQAAMKGFEEEEEESSSSSMMMCEEECDDCEDDDDQQEEESSSSOCMAAAAAAAAA..........",
    ".........AAAAPPPCCGGKKKGGAAAJAMKGFFCEEEESSSSSOMCCCEMJDDDUJJQQJQECCESSSCCMAAFPPFAAAA.........",
    "........AAAAEPPPNNNKKKKKGAAJJAANKFFCEEEESSSSSOCCCCCMAJDWUUAAAJEECCEEEECCMAAFFFFFQAAA........",
    ".......AAAAPEGGNNNNIIOOKKFFAAAANKGFCCEECCSSSOCCCCCCDAJWWWWUAAEECCCCCEEEMAAGFGGFEEQAAA.......",
    ".....AAAADPDGKGHHHHHHOOOKFFFAAAJKKGFCEEECCCEECCCCCCDJWYYYYWUUEECCCCCCEEMAAFGKFGGCCCAAA......",
    ".....AAJPPDGKKHHHHHHHOOOOKFGAAJAKKGFDEEECCEEECCCCCCDDWYSSYYUMEECCCCCCDJJAFGKKIIGGDCAAAA.....",
    "....AAJPPFGGBHBBBBBBHOOIOKGFGJAAANKGFDEEECEECCCCCCCDDWWSSYUMCCECCCCCDJJAAGKGIHHIOGDAAAAA....",
    "...AAJGPFGGHBBBBBBBBHOOIIOKGFGGAAANKKFDEECEECCCCCCCCCCCUUUUDCCCCCCDCJJAAGKGOHBBBBOGFFAAA....",
    "..AAAGLGGGHBBBBBBBBBBOOIIHOKKGGGAAAANKKFFCEEECCCCCCCCCCCFFDCCCCDDDCAAAQGKGOIBBBBBBIGDDAAA...",
    "..AAALPGGBBBBBBBBBBBBOIIHBIOKKGGGAAAANKKGFFEEEECCCCCCCCCCCCCCCDDDDAAAQGGGOIIBBBBBBHIGDAAA...",
    ".AAAAPEBBBBBBBBBBBBBBOIHBBHIIGKGGGGAAAAKKGGFFECCCCDDCCCCCCCCCCCDDAAAQGGGOIIIBBBBBBBHOOEAAA..",
    ".AAAEEBBBBBBBBBBBBBBBOIHBBBHIIOKKGGKAAAAAAQQJGGFFFFFFFFFFFFFCCAAAAAKKGOIIIIHBBBBBBBBHOEAAAA.",
    "AAAAEEBTTBBBBBBBBBBBBIIBBBBBHHIOOGGGKKAAAAAAJJMMFKKKFKKKKMMMAAAAMKKKGOIHIIIHBBBBBBBBBBBAAAA.",
    "JAJEAMMAAAAAABBBBBBBIIIBBBBBBBHIOOGGGJAJQQQJJJJAAAAAAAAAAAAAAAAMKKKKOIHHIIIHBBBBBBBBBBOAAAA.",
    "JAJAAAAAAAAAAAABBBBBIIIBBBBBBBBHIIOOOJJJGFFGGGJJMMMQQQMMMAKAAMMAMOOIIHBHIIHBBBBBBBIIIIBOAAAA",
    "JAAAAAA....AAAAJBBBBIIHBBBBBBBBHIIIIOAJGEEEECFFGGGGFFGGGGGKKMMMMAOIIHBBBIIHBBBBBBAAAAAAAAJAJ",
    ".AAAA........AAAJHBBIIHBBBBBBBBBIIIOAANFCEEEECNFGGPPLCCCGGGGMAGGMAOHBBBBIIHBBBQAAAAAAAAAJAAJ",
    "..............AAAJHBIIBBBBBBBBBBHIIAAANFCEEEECNNLLLLLLEELLLNNAKFFAABBBBBHHBBHQAAAA...AAAAAAA",
    "...............AAAABIIBBBBBBBBBBHIIAAJQCCEEECCNATLLLLLLLLLLCNAKFFAABBBBBHHBHMAAA.......AAAA.",
    "................AAAAIIBBBBBNNBBBHIIAAQJKFEEECCJATLLLLLLLLLLCNAKFGAQBBBBBHHBMAAA.............",
    ".................AAAHIBBBAAAAAABBIIANNAKKFCECCJJLLLLLLLLLLLLAAKGAAAQBBBBHHAAAA..............",
    ".................AAAAHIAAAAAAAAAAAAANKKAJJFCCQJLLLLLLLLLLLLLAAKAAAAAAAAHHAAAA...............",
    "..................AATTAAAA....AAAAAMKGKJAJJJJJQPLLLLLLLLLLLKAAAAAAAAAAAAAMAA................",
    "..................AAAAAAA......AAAAMKGFFJJJJJJJCPLLLLLLLLEKKQAAAA....AAAMAAA................",
    "...................AAAA..........AAMKGFDFJJJJECCDLLLLLLLEKKKQAA.......AAAAA.................",
    "....................AA............AAKGDECDDCEEECGDLLPPLLKKGGJAA........AAA..................",
    "..................................AAAGFCEECEEEEAGGGFFMMMMFFJJAA.............................",
    "..................................AAAGGFEECEEEEAAQQMMMMMGFFFAA..............................",
    "..................................AAAGGEEECEEEEAAAAJJMKGDFFFAA..............................",
    "...................................AAJGEEPCCCEAAAAAJKKKDGDKJAA..............................",
    "...................................AAAJGPPQCCAAAAAAJKKDAAKJAAA..............................",
    "....................................AAAAAQQAAAA...AAAAAAAAAAA...............................",
    ".....................................AAAAAAAAAA....AAAAAAAAA................................",
    ".......................................AAAAA................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (92, 73)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 92x73).
    scale=int   -> sprite de 92x73 px ampliado por un entero, sin márgenes.
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
    render().save("sprite.png")
    print("Guardado sprite.png")
