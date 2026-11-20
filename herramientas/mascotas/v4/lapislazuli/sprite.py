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
    "A": (19, 94, 225),
    "B": (117, 205, 249),
    "C": (12, 54, 161),
    "D": (10, 45, 133),
    "E": (3, 18, 72),
    "F": (5, 29, 102),
    "G": (5, 18, 47),
    "H": (14, 62, 83),
    "I": (13, 43, 60),
    "J": (13, 141, 174),
    "K": (11, 63, 186),
    "L": (10, 85, 108),
    "M": (10, 116, 144),
    "N": (10, 13, 25),
    "O": (17, 83, 206),
    "P": (12, 169, 210),
    "Q": (95, 178, 232),
    "R": (35, 92, 156),
    "S": (52, 81, 97),
    "T": (54, 138, 232),
    "U": (86, 157, 196),
    "V": (63, 116, 151),
    "W": (64, 131, 183),
    "X": (96, 117, 126),
    "Y": (204, 230, 243),
    "Z": (131, 171, 190),
    "a": (251, 253, 253),
    "b": (195, 198, 202),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...................JJMMMMJ...............",
    ".................JJHIDCCDIJ..............",
    "................JHFABaYCAAEPP............",
    "...............JIKABaYKKKKCDHJ...........",
    "..............JHKOQQQKKKKCKCDIJ..........",
    "..............JDKOQKKKKKKDKKKKL..........",
    ".............JIKKOKKKKDKKFCKKKIJ.........",
    ".............JEKKKKKCFFKDEFCKDFJ.........",
    "............JEKKKCKKDDDCEHGFCDEJ.........",
    ".......PI.MMIOOKFKKCFRFFTSSECDIJ.........",
    "......PIHLIHBOOKDKCFSRRTTSSFDEL..........",
    "......PIIUUBBOKCCCERSRRRTNGGFGG..........",
    "......HHFUUKOKCFFGRRFaaZZIGGNM...........",
    ".....PGINFKKKKKKCFRRZaaZQIISIM...........",
    ".....PGKKKKKKKKKKCDBZBZQBQSBILM..........",
    "......HDKKKKKDKKAAFBBBBBBBQBBDHJ.........",
    "......LGDCCCDFKKOTTORBBUVUVBBOOLJ........",
    ".......LGFFFFEDKKOOKORBBUVBBIKOIJ........",
    ".......GHGFDFFEDDKCDDDBBBBBBDKFIJ........",
    "........JHGFFFEGEFFEGFBBBBBEDKFHJ........",
    ".........JGGNGEEEGGENDRRHHEFDKDJ.........",
    "...........LLLINGGGEGRRRGGGEFCFJ.........",
    ".......JPPINNGIHHLLNNUURGHHINDIJ.........",
    "......JHSSIHHNNNHLHHEUUUNLHILNJ..........",
    ".....JHHTTDIILINLYYBBOVVVHHLIJ...........",
    ".....MHCTDDKIFHHIYYBBOAVVRHH.............",
    ".....MFCGLLNEFFEXYBBBKAARRRII............",
    ".....JHFGLNHLLGEXBBBBKAAADADI............",
    "......JGEIIGLGFNBBBBBAAAAECAH............",
    ".......LLLIHFDGNBBBHDKAADEEEH............",
    "....MSSLLIHDCEJBBBBECCKDEEEEL............",
    "..JMHSSHHDOOELJBBBHGDCDGEEENN............",
    ".JLJTTAAAOKELIHBBBIIEFGEEEENN............",
    ".LJTTTDIIIHJ.HIBBBLIHGEEEEDNN............",
    "MHJJKIIPPPJ..IBBBIHNLNECAACNL............",
    "MDCKGI......JBYBBHNNLNGEEEGUHL...........",
    "MEGDL......JHYBBHHNIIIGEEEGUUL...........",
    "MMLGJ......IIBBBHGHIIIIFGEGBBBJ..........",
    "...JJ.....IIBBBBLHIIYAAAFEELBBIJ.........",
    "..........IBBBBHLIIYAAAAAEDFBBBB.........",
    ".........IHBBBILLIYBAAAAAOOCBBBHM........",
    ".........HBBBHLLIBBAAAAAADAOLBBBM........",
    "........HHBBBHGLBBAAAAAAKCAAIBBQH........",
    ".......ILBBBIIIHBTAAAAAAFOAAELQBBHS......",
    ".....MMIBBBIINLHTAAATAAOOAAAFGBBBH.......",
    "...MLMBBBBIHNNHAAAATAAAKAAAAFMIBBBJ......",
    ".MMMMBBBBBINNHGAACAAAAOOAAAADMLHBUHJ.....",
    ".MMMRRRQBBHNNHGADBBAAODTAAAAKLIIBBUHJ....",
    "JJMRRDNQUGGNLGFCBBTAACTAAAAAKLNHBBBBBLJ..",
    "JIRRRNVUGGNHIFBBBTAAKTAAAAAACILIHBBBBZIJ.",
    "JHIIGIVIIGHIBBBQAAAACTTAAAAAFELNHVBHRRZIJ",
    ".JIILLLIHHHBBBQAAAACTTAAAAAFDCL..HVHHRRXJ",
    ".......IHHBYBAAAAAKBBTAAACEECCEL..IIGRRXJ",
    "......IIWYYBAAAAAADUBAADGEEFKACLL.LIGNRGJ",
    "......IWYYAAAAAAAAABUFGGFFEFAAADM..G.LLL.",
    "......BBBTAAAAAAACAANEFFFDEKAATTHM.......",
    "......BBTAAAAAAAADHFGFFDCCEKAAATTIM......",
    ".....BBTAAAAAAAAADFFGFDDCCFAAAATBTIM.....",
    ".....BTAAAAAAAAAAOFFNDCCCDFAAAAATBRM.....",
    "....BBDGGGEDKAAAAODFNCCCCECAAAACDRRHP....",
    "....EGEEEEEGGEFFFEEENCCCCEOAAFGGGGGNP....",
    "...EEEEEFFFEEENEEFDGNDCCCEOKGEFEFFFGP....",
    "...NEEEFDDDEEEGFEDDNNCCCCFDGEFDEFEIP.....",
    "...LGEFDDDDEEGFKDCFGNCCCCNEEFDDFGLP......",
    "....LGFDCCDFFGCDDCEEGCCCDGEEDDDCHL.......",
    "....HLGEDCFFGFCHDDGEEDCCEEFEDDDFL........",
    ".....NHDGFFFECCDDFGNDCCCNFFEDDDII........",
    ".....INLDDFGWWKCDGEGCCCCGFFFDFII.........",
    "......LLFFDHWWCCDNEDCCCCGFFEGLJ..........",
    ".......JIEGIWDCDFGGCCCCCGEGHJJ...........",
    "........JMIIOCCDGGNKCCCCGMM..............",
    ".........MHOCCDDGLHKCCCCGG...............",
    ".........MIKCCDELGHKCCCCGP...............",
    ".........MDKCCDGGIHCCCCCGP...............",
    ".........MDCCCFL..GGCCCDLP...............",
    ".........MDDCDGP..PGCCCDM................",
    ".........LCCCFHP..PIDCCDM................",
    "........PIDDCEP....LFCCFM................",
    "........PSBBBIP....SSVVVM................",
    "........SSBBBL.....SSBBUM................",
    "........MXBBBB.....SHBBUM................",
    "........MXBBHH......LBBUM................",
    "........LBBBHH......LBBUL................",
    "........HBBBH.......JBBBIJ...............",
    ".......JIBBBJ.......JBBBHJ...............",
    ".......JBBBHJ.......SSBBBL...............",
    ".......HBBBHP.......SSBBBIM..............",
    "......IBBBQGP.......LBBBBQIM.............",
    ".....IIBBBQHP......PIBBBBBQBHV...........",
    "....MLBBBBQHP......PHBBBBBBBVGVJ.........",
    "...MMSBBBBBH.......PIBWWBBBBWVWIJ........",
    "...MSBBBBBII........ILLLIBBBBWWHJ........",
    "..PHUUBBBBL.............IIIIHIILJ........",
    "..PIIWWBBIL...............PPPPP..........",
    "...IHIIIIL...............................",
    ".....IMMI................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (41, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 41x96).
    scale=int   -> sprite de 41x96 px ampliado por un entero, sin márgenes.
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
