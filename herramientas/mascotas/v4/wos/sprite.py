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
    "A": (2, 1, 8),
    "B": (2, 11, 35),
    "C": (4, 28, 83),
    "D": (3, 18, 59),
    "E": (3, 39, 113),
    "F": (84, 200, 248),
    "G": (46, 155, 247),
    "H": (32, 140, 244),
    "I": (11, 213, 249),
    "J": (3, 52, 146),
    "K": (13, 115, 225),
    "L": (6, 91, 202),
    "M": (100, 229, 251),
    "N": (12, 85, 148),
    "O": (65, 179, 247),
    "P": (3, 69, 181),
    "Q": (15, 180, 234),
    "R": (13, 151, 200),
    "S": (15, 119, 166),
    "T": (15, 72, 104),
    "U": (15, 40, 51),
    "V": (143, 235, 248),
    "W": (45, 127, 186),
    "X": (54, 111, 123),
    "Y": (63, 169, 201),
    "Z": (123, 187, 197),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".................................AA.........................................................",
    ".........................AAAAAAAAXXAAA.AA...................................................",
    "........................ABXTAAAAAAAQQUBAUBAA................................................",
    ".......................ABXXFFFAQQAOQQQQQQQQBBA..............................................",
    "......................ABXXQFFFLLPPPOKKPPQQQQQUAA............................................",
    ".....................BMMFFQPPLEEJPPPKPPPPPPQQQAA............................................",
    "...................AUMMMMKKJDCJJJPPEEPPEEEEJLQAAAA..........................................",
    "...................AAUIMMPECBCCJPECCECDBDCEJPLLDTB..........................................",
    "...................AAUIMKEBDECCCJPLJDDDCJLLJEEPKKUA.........................................",
    "....................BYYKJFMOOOCEDPPLCJJJPPCBDEPLKEAA........................................",
    "....................BTYYFMFMFOOFDDDPDCJCEJECCCJJLKKA........................................",
    "....................AATTMFMFFFFFFPECDBBBBEPEPPJJPKEA........................................",
    ".....................AAMMMMMMFFFFOGGGPEBBBDEPKJJJPKBA.......................................",
    "......................AMMMMMVVFFFFOGGGKPCBBBEPKKPPKNA.......................................",
    "......................UMMDDCCFFFFFFOOGGKKEDBBCPKKKPNA.......................................",
    "......................TYYDBELLPFFFFOGGGGHKPCBBCLLHNAA.......................................",
    "......................AYYEDBLCLFFFFFOGGHTWWPDBBEPKHA........................................",
    ".....................ATYOFWWOOMMFFFOGGOFTTWKJBBDDKAA........................................",
    ".....................UYOFFFOOVVMFFOOGOFWWWWKPCBDPPBA........................................",
    "....................AAVFOFMMMVFFFOOOGOFWCWWKPCBDPPC.........................................",
    "....................AVFFFOMMMOOOGGGOGFFTWWWKPCBJLLB.........................................",
    "....................AAPFWWMMGGGGGGOOGFYYWWKKPDCLLUA.........................................",
    "...........AAABUA...AUEEWMMMGGGGGGOOGOOYYPKKPBELCA..........................................",
    ".........AUUAAAATAAAAAAWMMMMFGGGGGGGGGXCEHHKLBLTA...........................................",
    ".......UXXMFFAAAAUNNNNTTMFFFFFGGGGGGGGXNXOHHLCJA............................................",
    "......UVVOMMFFWAJNNNNWWCTCEOFFGGGGGGGPCXNOHHKEAA............................................",
    ".....ACCMMOMMWWOXNWWNNJEACGGOOGGGGGHPPJNOFHHKAA.............................................",
    "..UCDCCCMMMMMWWOXXCCDCCDCGGGGGGGGGHPPPHFFFFHHHBA............................................",
    "ATTDWWCCTMMMTEBJKEDDBBDBDEGGGGGGGGPJJPHFFFFHHHHA............................................",
    "ACCDBBBBADDMBAAKKCBDBBABBEOFOGGGPJEEEPHFFFFFHHHUAAAA........................................",
    ".CDDBBBAAAAATAAGKBAAAA..XJFOGGJEECCCJLHGFFFFHHHNBCETAAAAAAAAA...............................",
    ".AAAAWWECCCKFFGKKB......XJJJECEEECCELLHGFFMFFHNBDDDDATUARRRATAA.............................",
    "....AWWWKKKOOOKJDA......BAJJEECTTCEKHLKGGFMMFDDCDCDBCCTTDDDCAAUAA...........................",
    "....AAFHKKKHHJJDA........AAAAAAUTEJKHLKGGGFMWDCDECBCCEBDCCCCDDDDUUA.........................",
    ".....AFKHKJJPJAA...............AYYCJKLKGGGFWDCCCCBCCJDBDCCCCCDDTRSBA........................",
    ".....AAJJJJECA..................UYYCJPKGGGWTCCSCBEEJJBDCDCCCCCDRRSBUA.......................",
    ".....UMLJPLJBA..................AYYECJKGGGTIRRISQQQQCBECBDCCCRTABBCAA.......................",
    "....AYMLPLPPA...................AUYYCEKGGTIIRRIQIQIIDJBDBDCCRTBCCCBCDA......................",
    "....AYMLPHLPA................AABUUYYJCDCDIITCIIQIIIIEIKBDDBERACCCCCBBA......................",
    "...AXMGKLHLDA............ABBBTRRRAEYPDADEDUDIIIQIRIIIIKCEBBRBCCCCCCDBAA.....................",
    "...AXMGKKHLA............AUQQQQCCRRBAABCCDBDBJIEQTRRCIIIIIDTTDCCCCCCCDBA.....................",
    "...UMMKKHKLA.........AUTTTTDEBBSSPEDCCDBBDDDJEEJBEDEIIIIQETACCDBDCCCCDBA....................",
    "...TMOKKHKPA.........URSTEBECBSSSEDDDBABDCBCEDDBBDBJIIQIQQTBCCBBDCCCCCDAA...................",
    "..UMMOHHHKCA.......AURSBCCEPASICCEBAABBBJCBEEDBBBBCJJCQIQQUCCDBBCCCCCCDBA...................",
    "..UMMGHHHKB.......ATUUJBNCCBBIIBDEDBBBBJBBCJCBBBDBJJCCRRRRBCCBBDCCEJPJJEBAA.................",
    "..UMMGHHHKA......AAAUEPNIIITBIDCBCEDBBDQBBPRCBBCCEJCBDPCNNDCBBBCCCCCCEJJJCAA................",
    ".AMMMHHHHKA......AAJBCIIIIICDDDDBDDJCDIIQIIRDDCCJJCBBDDDSTDCBBBCDBBDEJECCEJAA...............",
    ".BMMGHHHHKA.....AAUEDDRIITIDCDNCBBDIPJIIIIIRIIIRPEBBDBDBSBJCBBDBBBCJJCAAAADCAA.........AAAA.",
    ".BMMGHHHHKA...AUNRRBCRQISBJBDEDNDDQIIIIIQIIIIIIREBBCBBBBSABEBBBBBCJEBUAFFYUDDA........AUAAU.",
    "AMMMHHHHHKAAABTRRNCAIIQSSDDBCDTDNEQIIIIIEQIIIIIRDBECBBBBNBASBBBBCJCAUUMVMFYUAA.......AUAAAU.",
    "AFMMHHHHHKBBTRRCCCCBIIICJEBADCDDIQIIQCIIBSSIIIIRTSBDBCBANASIBBBCJEAEUFFMVVVVVDA.....AUZAAAA.",
    "AFMHHHHHHKCTTTCCCDDBIIIEDEBBDCBTIIIQQBTDDECJIPRIIISBCEBANAAIEBBJEADEEOFFFVVVVVCA..AAAZZATA..",
    "AFFHHHHHHKJBCCCCCDBAAPIIBCBDBCCIIICTDBBDCCCECDEIIISECJBANADABBCEBAEJKGOFFFMVVVYUAAXAAHPDA...",
    "AFOHLHHHHLJABCCDDDBAEECITBATDDIIRRDBBBDCCCCDBBNIQQQIICBANAAABBCDABEEPKGFFFFMVVVYUXVAHPDA....",
    "AFOKLKHHKLPXABCCBBBACEBCRDASDDIIRDDBBDCCCDBBBDPNCQIIIBBANBADBDCAAACEEPHGMFFMMMVVVVGGGDAA....",
    "AFOKLKHHKLLFXADCDBBBBJCCRTASIIIITBBBDCCCDBBBBDEBBCIIRBBAECABDEBAAABCEJPHMMMMMMGVVOHGGOTAA...",
    "AFGLLLHHLLFFGTADCDABBJEBTPASIIBCCBBDCCCDBBBBBCCBCCJRRRCCCEAACDAAAAABEEJPMMMMMGOVOHHHOMFAAAA.",
    "AFGLLLLLLGFGGGBADCBAAAECBCARRIBBBBBDCDBBBBBBDCDDCCCCRIICBPAADDAAAAAABCJPPMMMMGVOHHHOMFFAAABA",
    "AFGLLLLLLGGHHPCAADDAAAATBBARCEDBBBBCDBBBBBBBDCCCCCDBRIITABBADJAAAAAABADPPPPMMMFFHHOMMWWAAVVB",
    "AAQLLLLLHHHHPJCAAADDATAACBAEBCCBBBDDBBBDBDBDCCCCCDBCIIIPBBBAAAAAAAADDAADJPPLLFFMMVMMOWUDAGGB",
    ".BQLLLLLHHPJJJEBBAADADAAJBABBCCBBBBBDNNITTTCCCCCDBBJJIIINBAAACEAABEJBA.AACJJJMMVVVVOOFFTABUA",
    ".BQPPPLPJJJJJEAADAABBADPDEBBBBCCBBBERRIIIQISECCBBBBBBTIINAAAAAEDBEJDA...AAADDMMVVVOOCFFFTUA.",
    ".AAEJJJJEEEAAAAADBAAAABDSQCABBDDBBBRIIIIQIIISEBBBBBBBJIINDAAAAAEJEAA......AAABWMVPFFTBFOOTA.",
    ".AABCCCCBAAACAAABCAAAADBSQTBBBBDDDQIIIISSQQIITDBBBBDDCEIIEBAAAAAAAA..........ABWMTFFFXACAUA.",
    "...AAAAAA..AEAAAAEAAABRRQSUBBBBBDDIQNTCDCDDRIRCBBBDCCCCIICBAAAAAAA............ATMMAFFFXAAA..",
    "...........ACDAAACBAABRRRDADCBBBDIQNBBBBBBDCRIEDBDCCCCDTIDBADAAABA.............AMMUAFFFA....",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (92, 66)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 92x66).
    scale=int   -> sprite de 92x66 px ampliado por un entero, sin márgenes.
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
