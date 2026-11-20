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
    "A": (253, 174, 201),
    "B": (48, 32, 38),
    "C": (78, 50, 61),
    "D": (21, 13, 17),
    "E": (185, 127, 147),
    "F": (157, 108, 124),
    "G": (104, 73, 82),
    "H": (135, 89, 104),
    "I": (252, 249, 251),
    "J": (241, 160, 189),
    "K": (212, 145, 167),
    "L": (207, 29, 37),
    "M": (245, 105, 157),
    "N": (245, 227, 234),
    "O": (201, 79, 82),
    "P": (251, 199, 218),
    "Q": (248, 130, 176),
    "R": (133, 53, 63),
    "S": (82, 20, 22),
    "T": (203, 202, 205),
    "U": (135, 134, 136),
    "V": (239, 195, 160),
    "W": (138, 16, 21),
    "X": (195, 87, 129),
    "Y": (171, 170, 173),
    "Z": (101, 98, 102),
    "a": (246, 86, 113),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...........................................FKKB...................................",
    ".........................................FFDBBCEF.................................",
    "........................................FCCIAAEBF.................................",
    ".......................................FCFNIAAAABEEHHHHHH.........................",
    ".......................................FCIINAAAACBBHHHHBEE........................",
    "......................................FBIINAAAAABBBNHAAABF........................",
    "......................................FFPNAAAAQCBNIINAAAACF.......................",
    ".....................................KBFPPAAAQQQIINAAAAAJBE.......................",
    ".....................................KBAAAAAQQQAINAAAAAAJCE.......................",
    ".................................EEEGGGAAAAAQCAANAAAAAAAJCE.......................",
    "..............................EEEGGGCDCGGGGFFFAAAAAAAAAJJBC.......................",
    ".............................EEDCEEEEEEEEEEFFCAAAAAAAAJQJJB.......................",
    "............................KCCDGGEAAAAAAAAINAAGAAAAAJQQBE........................",
    "...........................KHHDDDDBAAAAAAAAAINAAGJAAQMMBHE........................",
    "...........................HBPDDCGGAAAAAAAAAAAAAACJQMXBHH.........................",
    ".....................FF...HBKPDAAAAAACAAAAAAAAAAAACMXBHH..........................",
    "....................FDFG.HHGGKAAAAAACDCFFAAAAAAAAAACDBB...........................",
    "..................KFCCDFGCBHGCCKKKAAKBDDDCABCKAAAAKDDBHBB.........................",
    ".................KBBFFDBFGJJHDCUUUKKJBDCIIBBDKAAAAKDDHBDB.........................",
    ".................GGBDDDIINAJJDUIIIKKJDDCIIBBFAAAAAAKDDCGG.........................",
    ".................FFGBDNIINAAJJUTTIBKKDCYYYBFAAAAAAAAABGGGG........................",
    "................FDDBCNINAAAAJAAATRKKOKGGCRRAAAABAAAAABBDDG........................",
    "................FFCDNNNAJAAAAAAAARaaOKKGRRRQAABAAAAAKBDCGG........................",
    ".................HCBAAAABJAAAAAAAHHFHHWLLWCQABAAAAAAKFCCB.........................",
    "..................HCAAAADJACLLWAACFHSWWCaaSAFCAAAAAAAAFBCC........................",
    "..................HHAAAAAAKWLLLLIIIIWSRaaaAACFAAAAAAAAKDCCFF......................",
    "..............FKKBBAAAAAACKWLLLLIIIISRaaaCKABAAAAAAAAAKKEEDBFF....................",
    "............FFGDBBBCAFAAACJJLLLWWTTIWaaaCKAAAAAAAAAAAQJAAAAFBEF...................",
    "..........CCBGGAAAAAAFACKAAJCLLLWWWLLaaaAAAAAAAAAAAAQJAAAAAJXBEKKKKKKE............",
    "........FFCCIIIAAAAAAAAAAKAAJJSWLLWWSAaaAAAAAAAAAAAAAAAAAAJXSBBBBBBDDEEK..........",
    ".......EFBCNIIIAAAAAAAAAAAAAAAJAFFFAAAAaBAAAAAAAAAAAAAAAAACJJPNNNNPPICBCK.........",
    "......EECENIINPAAAAAAAAAAACAAAAAAAAAAAABHAAAAAAAAAAAAAAAAAAAPNNNNNIIINCCCK........",
    "......EBEIIINPAAAAAAAAAAABAPAAAPAAAAAABHAAAAAAAAAAAAAAAAAAAAAAAAAAPNIINJCCB.......",
    ".....ECAAIIPAAAAAAAAAAAAFFPAABPAAAAAABHAAAAAAAAAAAAAAAAAAAAAAAAAAAAPNIINJBF.......",
    ".....EDAAIPAAAAAAAAAAAAAFCCAACPAAAAABHBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANIIIFFF......",
    "....CCAAAPAAAAABAAAAAAAAACCCCDCJJACBXCHAAAAPPAAAAAAAAAAAAAAAAAAAAAAAAPNIPFBE......",
    "....JCAAAAAAAACAAAAAAAAAAAABCCDBBDCXEBAAAAIIIAAAAAAAAAAAAAAAAAAAAAAAAAPPAACE......",
    "....JCAAAAAAFBAAAAAAAAAAAAAQQQAHHDCCCEAANIIIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCEE....",
    "....CCCAAAAACFAAAAAAAAHAAAAAAAAAAACCBAANINAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBGE...",
    "...FFDCAAAAAFAAAAAAAAAHEAAIIIIPAAAACGAAINAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGBE..",
    "...EBFAAAAAAAAAAAAAAAQHEAAIIIIPAAAAHGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCE.",
    "..EBFNIIAAAAAAAAAAAAQMHEAAAAAAAAAAAHGAAAAAAAAAAAAAAAAAEEEHBAAAAIAAAAAAAAAAAAAAABE.",
    "..CCNIIPAAAAAAAAAAAAMMBAAAAAAAAAAAAAGAAAAAAAAAAAAAAAAABDDDHAAAAIIPPAAAAAAAAAAAAAFF",
    ".CCCNIPAJACGGAAAAAQMMXCAAAAAAAAAAAAABAAAAAAAAAAAAAAAQMCDDDDAAAAAIIPAAAAAAAAAAAAABE",
    ".FCPINAAJJJJGAACAQMMMBXAAAAAAAAAAAAACAAAAAAAAAAAAAAQMMCCMDCMJAAAPPPAAAAAAAAAAAAABE",
    "FFFPIAAAAIIINPAAABBBBCMAAAAAAAAAAAAAAAAAAAAAAAAAAAMMMCBMMMDXMJAAAAAAAAACAAAAAAAABE",
    "EBAAAAAAAAIIINPAAAAAABRMMJJAAAAAAAAAAAABAAMMMMMMMMMMBBAAMMBBXMJJAAAAAAAADAAAAAJJBE",
    "EBAAAAAAAAAAAAAAAAAAAAARMMMMMMMMMAGAAAAACDBCCCCCCBDCAAAAMMMDRMMMMAGBBBAADAAAAAJREE",
    "EBAAAAAAAAAAAAAAAAAAAAAACMMMMMMMCGGNNAAAAAAACCCHHAAAAAAAMMMR.RHHDDGGEEAAAAAAAARRE.",
    "EBAAAAAAAAAAAAAAAAAAAAAACDBCCCAAJGGNAAAAAAAAACGAAAAAAAAQMMX....DHIIIIPAAAAAAAAXDE.",
    "EBAAAAAAAAAAAAAAAAAAAAAAADDAAAAAAJGGAAAAAAAAAGAAAAAAAAQMMXDBF.JJPIIIPAAAAAAAAQXCE.",
    "HHAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAHHAAAAAJAAGBAAAAAAAQMMXBBFGGJPIIPAAAAAAAAAQMCCC.",
    ".HBXQQAAAAAAAAAAAAAAAAAAAFBAAAAAAAACBCCAAJACCGAAAAAAAQMXDDCCGJPIPPAAAAAAAAAQMMDC..",
    ".HHBXMMQQQQQQQAAAAAAAAAAAADBGGGAAAAACNAAAAAAABAAAAAAAAXDDDCCJAPPAAAAAAAAAAMMMBCC..",
    "..HHDCMMMMMMMQDDAAAAAAAGAABUGKKAAAAGANAAAAAAAHGAAAAAAAQBEEBJAAAAAAAAAAAAQMMMDCE...",
    ".......DDDDDDDSDAAAAAAAAGABNUUAAAAAGJAAAAAAAAHGAAAAAAAQCCDEAAAAAAAAAAAAQMMMDEE....",
    ".......SOOOOORRRCAAAEAAAGGBZNUUAAAAJCAAAAAAAACHAAAAAAQMCCBAAAAAAAAAAAMMMMCBEE.....",
    ".......ROOOOOOORBAAAEHAACCZTZUUUAAATCFAAAAJAACAAAAAJQMMCBAAAAAAAAJAXXXMCBHHE......",
    ".......ROOOOOOOORDQQHHDDDWSTTZUUUCZTTBFAAAJJAAAAAAJQMMCCBKAAAAAAAJACDBFFHH........",
    ".......SOOOOOOOORDDBDDDSLLLCTTZUUZTIYYGGAJAAAAAAAMMMMCCTCKAAAAAAAAAACBB...........",
    ".......DDDRRRRRRDDDDSLLLLLLLSTTTCUIIIIGGUIBBBBBBBBCIIIITCAAAAAAAAAAAEBK...........",
    ".......FVVVGGGGVVBDDCWLLLLLLLSTTUUIIIIUUZIIIIIIIIIIIITUZZBAAAAAAAAAAEBK...........",
    ".......FVVVVVVVVVCBDTBLLLLLLWLWSBBUIIBBZZZZYTTTTTTYZZUTIDDEAAAAAAAKKCKK...........",
    ".......CVVVVVVVVVC..TTLWLLLLWWLWZZCUBBBBIINYUUUUUUYIIIIICDBEJJAAAACBBK............",
    "....DCCBBVVVVVVVDB....WWWWWLLWWSUZUDZZTBIYYNIIIIIIIYIIDSWWSBBMMQQQCCEE............",
    "..BDGGAAABDDDDDDDDD.....WWWBSWWDYUNSUZTSWWWBBBBBBBBWWLLLLWWBBBCXXQDEE.............",
    "..DGGGAAAAEEEEEEDCD.......IIIIBDYUNDUUNDSWWLLLLLLLLLLLLLLWSUCCCCCJJE..............",
    "..DKFBJAAAAAAAAAADD.........IIGGTUTWUUNSLWWWLLLLLLLLLLLLWWDUCCCJJJ................",
    "..DKCFAJDAAAAAAAADD..........GGGGTTSUUISLLLLLLLLLLLLLLLLBSDDC.....................",
    "..DDBFADBAAAAAAAABD............DIIYDUYIBSLLLLLLLLLLLLLSDDWDN......................",
    "...DDCFDDFFFHHHCDD.............BIIY.YIICCDDSWLLLLLLLSDDWDBYN......................",
    "....BDDDDDDDDDDDB..............IIIN.IIIZTTDSWWWLLLLWSDSBNNYY......................",
    "...............................YIIN.TIIIZTTTTWSSSSSSSSINNYY.......................",
    "...............................YYIN.TIII..TTIITTTTTTTIIINC........................",
    "...............................DCYY.YYC...CDBTTTTTTTTSBDFF........................",
    ".........................................EESSSSSSSSSSSSFF.........................",
    ".........................................EGSOOOOOOOOOOSF..........................",
    ".........................................GGROOOOOOOOOOSF..........................",
    ".........................................CCROOOOOOOOOOBF..........................",
    ".........................................ECOOOOOOOOOOOCF..........................",
    ".........................................EBOOOOOOOOOOSG...........................",
    ".........................................HCVDSRRRRRSBBG...........................",
    ".........................................HHVVVVGGGVVVHH...........................",
    ".........................................HFVVVVVVVVVVBF...........................",
    ".........................................GFVVVVVVVVVVBF...........................",
    "........................................EGGVVVVVVVVVBBFFF.........................",
    "........................................EDSRRRKKKKRRSBBBFF........................",
    ".......................................EEDFCSRRRRRRBJJAFCFE.......................",
    ".......................................KCFAAAAGGGGAJAAAAACE.......................",
    ".......................................KCKAAAAAAAAAAAAAAAABB......................",
    ".......................................CCKAAAAAAAAKAAAFFAADB......................",
    "........................................BCAAAAAAAAKDAAAGAADD......................",
    ".........................................DEAAAAAAAAGGAAGKKD.......................",
    ".......................................DDDBEAAAAAAAGGAAGGCDD......................",
    "........................................DDDDBAAKKKKCCDGDBDD.......................",
    ".............................................DDDDDDDDDD...........................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (82, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 82x96).
    scale=int   -> sprite de 82x96 px ampliado por un entero, sin márgenes.
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
