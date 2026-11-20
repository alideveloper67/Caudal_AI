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
    "A": (237, 170, 111),
    "B": (196, 82, 20),
    "C": (33, 16, 16),
    "D": (18, 7, 6),
    "E": (177, 71, 18),
    "F": (243, 200, 149),
    "G": (43, 26, 27),
    "H": (141, 43, 6),
    "I": (239, 185, 130),
    "J": (56, 35, 35),
    "K": (247, 214, 166),
    "L": (156, 57, 12),
    "M": (208, 98, 33),
    "N": (71, 25, 9),
    "O": (251, 226, 183),
    "P": (109, 39, 11),
    "Q": (80, 51, 39),
    "R": (225, 139, 101),
    "S": (187, 127, 84),
    "T": (224, 115, 47),
    "U": (151, 96, 72),
    "V": (116, 85, 63),
    "W": (252, 245, 239),
    "X": (136, 122, 101),
    "Y": (97, 71, 52),
    "Z": (197, 179, 145),
    "a": (245, 89, 122),
    "b": (192, 67, 93),
    "c": (247, 141, 163),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "....................................JJJJJJJJJJJJ..........................................",
    "...................................GCDDDDDDDDDDCCJJJ......................................",
    ".............................JJJJJJGCNQQQQQQQQQGDCCGC.....................................",
    "............................JGCDDDDDPPOOOOOOOOODDDDDCGJ...................................",
    ".........................JJJCDNDEEDZZIIAAAAAAAADKKKQDDCGJJ................................",
    ".......................JJGCDNPMMTIIFIIAAAAAAAAAIIIIKXXYDDCG...............................",
    "......................DJCDNNTMMTKKFFKKKKKFFAAAAAAAAAKKYYYCG...............................",
    "...................JJJGCCGTTTMMKKKFWWWWWOOOAAAAAAAAAAAAOOYGG..............................",
    "..................JCCDDNCTMMTTOKKWWWWOAAAAAAAAAAAAAAAAAAAOGCG.............................",
    ".................CJCNBBMMMTTFFFOWWWWOAAAAAAAAAAAAAAAAAAAAAACCG............................",
    "................JGNNPBMMMRFFFFOWWWWAAAAAAAAAAAAAAAAAAAAAAAAZDGG...........................",
    "...............GGNMMMMMMRKAAFOWWWWAAAAAAAAAAAAAAAAAAAAAAAAFZQCGJJJ........................",
    "..............GCNTMMMMBMKAAFWWWWWAAAAAAAAAAAAIKKKKKFAAAAAAAFFDDDCG........................",
    ".............JCLMTTMBBBKAAAWWWWWAAAAAAAAAAAAKKIIIIIFAAIAAAAAFOODDCJ.......................",
    ".............GDLMMMEBBFIAIWWWIIAAAAAAAAAAAAAAAAAAAAAAIIIAAAAAAFZZXCJ......................",
    "............GGDHBBBEFFIAIIWWIAAAAAAAAAAAAAAAAAAAQQQAAAIAFAAAAAAFXXDGD.....................",
    "............JDHBBBEEAFAAIWAAAAAAAAAAAAAAAAAAAAACCCCGAAAAFFAAAAAAAXXCJ.....................",
    "...........CJDBBBBEFFAAAAAAAAAAAIFFFAAAAAAAAAAAAAAACCAAAAFAAFAAAAIXXCJ....................",
    "..........CGCBBMBLTFFAAAAAAAAAAIKIIIAAAAAAAAAAAAAAAAQCJAAAAFAAAAAAIKDG....................",
    ".........JGGPMMMBLTFFAAAAAAAAAKKIAIVVAAAAAAAAAAAAAAARRGAAAAAFKAAAAIKDG....................",
    "........GGCPMMMMBLTFFAAFAAAAAKKIAAJCCVAAAAAAAAAAAAAAAAAAAAAAAKAAAAAIQQJ......JJJJJJJ......",
    ".......GGNMMMMMMBEFFFAFOAAAAKKAAAGAAAAAAAAAAAAAAAAAAAAAAAAAAAKAAAAAAOQCC....GCDDDDDGC.....",
    ".......JCNMMMMMBEMFFAFOFAAAFKAAAGJAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOQCC..GGCCVVVVQCGG....",
    "......JGNPMMMMBEMAAAAFFAAAAFFAAAGAAAAAAAAAAAAAAAAAAAAAAAUUAAAAAAAAAAOQCCGGCNNEIIIIENDCG...",
    "......JDBMMMMMEBROAAAOIAAAAFAAACQAAAAAAAAAAAAAAAAAAAAYAAUUAAAAAAAAAAOQCCJDDEEEEEEEEEECJ...",
    ".....JGDBMMMMHETROAAAOIAAAAAAAQGAAAAAAAAAAAAAAAAAAAAAYYACUUJAAAAAAAAAACGCPEBEEPNPHEEEDJ...",
    "....JGGNMMMMBHMTROAAAOIAAAAAAYJYAAAAAAAAAAAAAAAAAAAAAAGXXUGUAAAAAAAAAKXDNHBEPPDDDPHEENGG..",
    "....JCNMMMMMBHMRIAAAAAIAAAAAAGYAAAAAAAAAAAAAAAAAAAAAAAGJXYYAAAAAAAAAAKXDPEEPDDCGCDPEEENCJ.",
    "....JDNMMGPBLMTIKAAAAAAAAAAAAGYAAAAAAAAAAAAAAAAAAAAAAAGCCCGGAAAFAAAAAFFXNHNDDC...GCPEECCJ.",
    "....JDNMMCQBLTTIKAAAAAAAAAAAAQAAAAAAAAUVAAAAAAAAAAAAAAAUJUGSAAAAFKAAAAFFQNCDG....GCNEECCJ.",
    "....JDNNCCPBLTTIKAAAAAAAAAAAAAAAAAAAAAUVVUAAAAAAAAAAAAAAUASAAAAAAFKAAAAFFDDG.....JCNEECCJ.",
    "....GDNLCPBBBLTIKAAAAAAAAAAAAAAAAAAQAAJVVUAAAAAAAAAAAAAAAAAAAAAAAAKFAAAAFZDJ.....GCNEECCJ.",
    "...JCPLLCPBBBLEIKAAAAAAAAAAAAAAAAAAQGAZQVAAAAAAAAAQAAAAAASSASSAAAAAKFAAAFZDG....JGCEEEHNCJ",
    "...JDLBLCPBBBELSIAAAAAAAAAAAAAAAAAAUCZZVQURAAAAAAAGAAAAASQSSQAAAAAAFFAAAFZDG....JCNEEEEPDG",
    "...JDLBLCPBBBBLLSOAAAAAAAAAAAAAAAAAUCCJGVURAAUUAAVXXQAAQQQDAAAAAAAAAFAAAFZDG....JNEEEEEEDG",
    "...JDLBBLCQBBBBESOAAAAAAAAAAAAAAAAUGGJGQAAAAAAYYVXOOZCCOOQAAAAAAAAAAAAAAFZDG....GCNPEEHEDG",
    "...JDLBBCCQBBBBESOAAAAAAAAAAAAAAAAUUQRRJAAAAAAYYOZZOZCCCOCAAAAAAAAAAFFAAFZCCJ...JCDDHENPDG",
    "...JDLBLCCMMBBLAKAAAAAAAAIFAAAAAAAAAARARAAAAAAYOOOOOCCCCCCJSSSAAAAAAAKAAAIOJG....CGDDNDDG.",
    "...JDLBLCEMMBBLAKAAAAAAAAIFAAAAAAAAAAAAAAAAAAAQOOOOCCCCCCCDQUUSAAAAAAKAAAIOJG.....DGCCCG..",
    "...JDPHPCEMBBBLAKAAAAAAAAIFAAAAAAAAAAAAAAAAAAAJGXXGCCCCCCCAAAAAAAAAAAKAAAIOJG.............",
    "...JDPHPCEMBBBLAKAAAAAAAAIKKAAAAAAAAAAAAAAAVQZCCCCCQUUUQCAAAAAAAIAAAIOAAAIOJCC............",
    "...JDPHHPCQMBBLLAKAAAAAAAAFAIAAAAAAAAAAAAAAAVOZCCQQQQUaaQSAAAAAAFIAFOIAAAAAACGJ...........",
    "...JCNPHHCQMBBELEEFAAAAAAAAFIAAAAAAAAAAAAAAAQOCCQaKKaaaaJSSAAAAAFIIOFAAAAAAKXDG...........",
    "....JDNHHCQMBBBEEEKFAAAAAAAFKIAAAAAAAAAAAAAAGCCGaccaaaaSSSAAAAAAFIIFAAAAAAAKXDJ...........",
    "....JDNHHHPHBBBBELAKFIAAAAAAKKAAAAAAFIAAASAACCCbaaaUUAAAAAAAAAIIKAIFAAAAAAAKXDJ...........",
    "....JDCNHHPPPBBBBBLAFIFAAAAAAKAAAAAAFIAASQQVCCCbaabUAAAAAAAAAAFKIAIFAAAAAAAKXDJ...........",
    "....JCDCPNNNNCHEBBLFFFFFAAAAAOAAAAAAFIAAAQQCVVVVQbQAAAAAAAAAAAFAAAIFAAAAAAAKXDG...........",
    "...GGGDDCCCCCCCPEBLAFIOOAAAAAOAAAAAAFIAAAQJRAAAAAVVAAAAAAAAAAAFIAAFFAAAAAAAKXDG...........",
    "...GCDDPTCBBBCLNNBLAFAIOOAAAAIOKAAAAFFAARQRAAAAAAAQRAAAAAAAAAFKIAFKAAAAAAAAKXDG...........",
    "..JCDDTTPPLLHLHNNBLIFAAAIKKAAAIKAKFAAKIAARAAAAAAAARAAAAAAAAAFKIAFKAAAAAAAAAKXDG...........",
    ".JGCCDTLPPNDCCDNHBLSIFAAAIKAAAAAFFKAAIKIAAAFAAAAAAAAAAAAAAAAFAAIKAAAAAAAAAAKXDJ...........",
    "JGCQEELHDDCNNNDHBBLLSAAAAIKAAAAAAAFKAAAKIIKFKAAAAAAAAAAAAAAAAAAKKAAAAAAAAAIVVDJ...........",
    "JDDEEHNDDDNHHHNHBBBELEAAIAAAIAAAAAAKFAAIKKIAAKAAFFAAAAAAAAAAAAIKAAAAAAAAAIIJDDJ...........",
    "JDHEENCCGDNHHHPPHBBBELLLFAAIKAAAAAAAFAAAAAAAAFFFKKFAAAAAAAAIAAOIAAAAAAAAFFECCGJ...........",
    "JDPEEDCDJDNHHHHHHBBBBLLLFIAAKIAAAAAAFAAAAAAAAAKKAAFAAAAAAAFIIAOIAAAAAAAFFSECGC............",
    "JDPEEDCDCCNHHHEBBBBBBBBLIIIAKKIAAAAAAKAAAAAAAAAAAAAAAAAAIFFIKIOIAAAAAFFFSBBCG.............",
    "JDPEEDGDDCDCHHHEBMMMBBBELIIAAIKKIIAAAAKKAAAAAAAAAAAAAAAAIFARIKIAAAAAAFFEEBBCG.............",
    "GDPEECGDDCCCHHHEMMMMMBBELOIAAAAKAAAAAAAAAAAAAAAAIIAAAAAAFFRARRRAAAAAOMEEBBBCG.............",
    "GDPEECCCDCGCHHHEMMWITBBELOIIAAAAAAAAAAAAAAAAAAAAIFAAKAAAFFAAAAAAAAAAOMEBBBECG.............",
    "JCDNEENCGDGCDHHHMMIWTTBELEIIFIAAAAAAAAAAAAAAAAAAIKFKFFAAFFAAAAAAAAAAOMEBBEDCG.............",
    ".JDNEENDCJGJDCPHMMWWOTTBELEEFFIAAAAAAAAAAAAAAAAAAFKAAOAAFFAAAAAAAAIOEEBBEHDG..............",
    ".JGCHEEELDGQCDPHLMTTOOTBBELLLLAAAAAAAAAAAAAAAAAAARRAAOAKKFAAAAAAAAIOEBBEHNDJ..............",
    "..JCNEEMMLDCJDPHHLMTTOOTBBBELLLAIAAAAAAAAAAAAAAAAAAAAOKKOAAAAAAAAAKEEBBPCDGG..............",
    "..JDLEEELLDGDCDPHHHHTTTTTBBBELLLIAAAAAIAAAAAAAAAAAAAAKFOIAAAAAAAIKABBEPCCCCCJ.............",
    "..JDLEEEPNDG.JDPHHHHETTTTBBBBELLFIAAAIAAFFFFAAAAAAAAAAFIAAAAFFFFIREBBNNECCCNDGG...GJJJ....",
    "..JCNLENNDCG.GGCNHHHHEBTTTBBBELLIFIIAAIFOOOFAAAAAAAAAARRAAAIFOOORLEBBNPNECCEDDGG.JCDDCG...",
    "..JGCNPDDGJ...JCCNHHHHHBBBMBBBELLLOOAAAAAAAAAAAFFFFAAAAAAAAIHHHHLEBBHNNNNHEEMPNDGCJDHPCG..",
    "...DJCCCJ......GCDHHHHHHHHMMBBBELLEEKKAAAAAAAFKKKKKIAAAAAAAMEEEEEBBBHCDDDDNHEMBPDDTTHHDG..",
    "................GCNPHHHHHHETTBBBEELLSSFFFFFFFFELLLEIFFFFFAMEBBBBBBBHDCCGGCDNPLBMPNTEEHDG..",
    ".................CCNHHHHHHHEEEBBBBELLLKKKKKKKLEEBELLKKKKFLEBBBBBBBHPDG...JGCDHLBMMEEEPDG..",
    "..................GCDNHHHHHHHHEBBBBBEHHHHHHHLBBBBBBLHHHHLBBBBBBBLHPDGG.....GCDNPLLLHCDCG..",
    "...................GCCNCPHHHHHEBBBBBBEEEEEEEEBBBBBBEEEEEEBBBBBLLHNCGJ.......CCDNHHHNDCC...",
    "....................GJCDNPHHHHHEEBBBBBBBBBBBBBBBBBBBBBBBBBBBEEHPPCG...........GCDDDDCG....",
    "......................CCDCHHHHHHHBBBBBBBBBBBBBBBBBBBBBBBBBBEHHHNDGD............GCDDCG.....",
    ".......................CCCPPHHHHHHHHEBBBBBBNNBBBPPBBBBBBBHHHNNDDCC..............GGGG......",
    "........................GCDDNPHHHHHHHEBBBEPNNNCDNPBBELLLLPPPDDCGJ.........................",
    ".........................JGCDDPPPHHHHHEEEHDNHNLCPEEEHHHHPNDDCGG...........................",
    "...........................CGCDDDPHHHHHHHPCDPEMLNPHHPPPDDDCGG.............................",
    ".............................DGCCDNHHHHHHHHCCPEMLCPNDDDCCGD...............................",
    "................................DGDDDDDDDDDDDPHBTQDDCGJC..................................",
    "..................................GCCCCCCCCCCDPBBTDCD.....................................",
    "............................................GCCPBBDJ......................................",
    ".............................................GDPEBDJ......................................",
    ".............................................GCPEEDG......................................",
    "...........................................JGDHEEEDJ......................................",
    "..........................................DGDNLEEPDJ......................................",
    "..........................................JCPLELHCCJ......................................",
    ".........................................GNNLEEHNCJ.......................................",
    "........................................GDPEEEHNDG........................................",
    "........................................GDPEEENDCG........................................",
    "........................................JCPLEEPNGCJ.......................................",
    ".........................................CDNLEEEEDG.......................................",
    ".........................................GGDCLEEDDG.......................................",
    "..........................................GCDPPNCDJ.......................................",
    "...........................................JCDDDDGG.......................................",
    "............................................GGGGJ.........................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (90, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 90x96).
    scale=int   -> sprite de 90x96 px ampliado por un entero, sin márgenes.
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
