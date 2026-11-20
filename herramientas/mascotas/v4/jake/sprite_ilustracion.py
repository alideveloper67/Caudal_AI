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
    "A": (252, 192, 2),
    "B": (29, 11, 1),
    "C": (240, 142, 1),
    "D": (247, 170, 2),
    "E": (190, 92, 3),
    "F": (219, 115, 2),
    "G": (62, 29, 5),
    "H": (91, 41, 5),
    "I": (233, 232, 230),
    "J": (158, 74, 4),
    "K": (121, 57, 4),
    "L": (143, 103, 13),
    "M": (208, 145, 6),
    "N": (249, 201, 51),
    "O": (182, 128, 7),
    "P": (80, 71, 63),
    "Q": (250, 209, 81),
    "R": (250, 226, 157),
    "S": (248, 215, 120),
    "T": (230, 167, 18),
    "U": (252, 235, 189),
    "V": (249, 249, 249),
    "W": (133, 127, 119),
    "X": (196, 186, 170),
    "Y": (210, 165, 75),
    "Z": (152, 114, 63),
    "a": (200, 49, 49),
    "b": (162, 156, 147),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................BBBBBBBBBB..............................",
    "..........................BBBBBBMMMMMMBBBBBB..........................",
    "........................BBBBMMBNNAAAAAAAMMBHBB........................",
    "......................BGOOBRRRRRRNAAAAAAAAAABBBB......................",
    ".....................GJOSSSUUURQQANAAAAAAAAAABBKB.....................",
    "...................BGJTSSUUUQQAAAAAAAAAAAAAAAAAMKBK...........B.B.....",
    "...................GJTSUUUQQAAAAAAAAAAAAAAAAAAAAMKB.........BBHHGHB...",
    ".................BGJTSUUUQAAAAAAAAAAAAAAAAAAAAAAACKB........BBMMLLB...",
    "................BHETSUUUAAAAAAAAAAAAAAAAAAAAAAAAAACKB......BBKMMLLBB..",
    "................GETSRQUAAAAAAAAAAAAAAAAAAAAAAAAAAAACKB.....BOOKMMEEB..",
    "...............GGGQRQQQLLLLAAAAAAAAAAAAAAAAALLLLAAAAAGB....BBOKFMMBB..",
    "..............BGGDQQTLQPPPPLOAAAAAAAAAAAATLPPPPPLOAAAAG....BLTTFDAMB..",
    "..............GGDAATLPIIIIIPPOAAAAAAAAAATLPIIIIIPPOAAABB...BLTTDDAMB..",
    ".............BGGAATTPIIIIIIIPBAAAAAAAAAALPIIIIIIIIBAAABB....BEDDDAMB..",
    ".............BGAAALBIIVVVIIIIPAAAAAAAAAABPVVVVIIIIGOAAAHB...BHEDAAAB..",
    "............BBAAALBPIIVVVIIIIIBAAAAAAAMBPIVVVVIIIIIBOADJB....BHCAADBB.",
    "............BBAAALBPIIVVIIIIIIBBAAAAAAMBPIVVVIIIIIIBLADJB....BHCAADBB.",
    "...........BBBAAALBPIIIIIIIIIIBBHGGGGHBBPIIIIIIIIIIBLAAJBB....GAAAAMB.",
    "...........BBDAAALBPIIIIIIIIIPBGGOOOOOBBGIIIIIIIIIXBLAADJB....BHAAAMB.",
    "...........BBADAALBBWIIIIIIIPPbbQAAAAAOOGPIIIIIIIXPBLDDABB....BGAAAABB",
    "..........BHAACDAABBBWIIIIIPSSQQQAAAAAAAALPIIIIIIPBBDDCAAHB...BGAAADBB",
    "..........BBDACCAAGBBGWWWWPPSSQAAOLLOAAAQNLPWWWWGBBBDCCAABB....HAAADEB",
    "..........BJDACCADEGBBBBBBHPAAAAOGBBGOAAAQNGBBBBBBHAACCADBB.....AAADEB",
    "..........BJDDCCAADEGBBBBBBUAAAABGGGBBAAAANLBBBBBHFAAAADDKB.....GDADEB",
    "..........BBFFHDDAADDGGGBHURAAABBBBBBBGAAAALGBGGBFAAAAHFFKB.....GDADEB",
    "...........BJJHHDAAADAFFHDRAAADHBBBBBBHAAAAALKGCCAAAAAGFKB......GDADEB",
    "...........BBBHEDDAAAAAFHDRAAADDGBBBBGAAAAAALKCAAAAAAMHBBB......GDADEB",
    "............BBBGEDAAAAAAGANAAACGGFFBBGGCAAAAAJAAAAAAAMHBB.......GDADEB",
    "............BHQQQAAAAADELNAAAACGGWPPWGGCAAAADJFAAAAAAMMJB.......GDADEB",
    "...........BSNQQAAAAAADELNAAAAEBGGWWGGGFAAAADJFAAAAAACCJJB......GDADEB",
    "..........BSSSNAADDAAADELNAAAAEBGGBBGGGFAAAADJFAAAAAACCJJKB.....GAADEB",
    ".........BBRQAADJJCAAADEEAAAAAEBHaaaaHGFAAAADKFAAAAAACCAQQKB....HAADJB",
    "........BBRQAADFJJCAAADEECAAACKKGaaaaGGGCAADDKFAAAAAAAFDAQQKB..BQQADJB",
    ".......BJQQAACFHFFDAAADDHECCCKBGGHHHaGGGFCDDJHAAAAAAAFFFDAQQZBBGQAAJJB",
    "......BJQQADCGGHFFDAAAADKGEHHKGGAAOOADGBGFFGGJDAAAAAAFKKFDANNZDDAADJG.",
    "......QQQADJJBGFFCDAAAADFKHHHGGDAAAAAADEGHHGGDDAAAAAAFKGJFCDNNDDADCJB.",
    "....BHNQADCJBBHEFCDAAAAADFJJJGDAAAAAAAAAEJJGDDAAAAAADFKBBJFCDDDDDCFHB.",
    "....GNNAACJGGBKEFCCDAAAAADCCCDAAAAAAAAAADCCCDAAAAAAADFKBBGGGGCCCFFHB..",
    "..BGGAAACJBG.BKEFCCDAAAAAADDDAAAAAAAAAAAADDDAAAAAAAADFKB..BGHEEEEHB...",
    "..BBAAACCBG..BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADFKB....BBBBBB....",
    "..BOAACFHG...BKEFCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADFKB..............",
    ".BOAAAFHB....BKEFCDDAAAAAAAAAAAAAAAAAAAAAAAAAAAANAAACFKB..............",
    ".BBAAAEB.....BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAAAAANAACFKB..............",
    "BBAAAEB......BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAAANUAAACFKB..............",
    "BBAADBB......BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAAANUUAACFKB..............",
    "BBAADBB......BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAANRUUACCFKB..............",
    "BBAADBB......BKEFCCDAAAAAAAAAAAAAAAAAAAAAAAAAANURAACCFKB..............",
    "BBAAAMHG.....BGHFFCCDAAAAAAAAAAAAAAAAAAAAAAAAANURAACCFKB..............",
    "BHAAAAMMBB..GBZGKKFCDAAAAAAAAAAAAAAAAAAAAAAAAAAQAAACCFHB..............",
    ".BECAAAAAKGBBZTTOHKCDAAAAAAAAAAAAAAAAAAAAAAAAQQAAAACCEHB..............",
    ".BKECDAAAAKKHTTTOHKCCDAAAAAAAAAAAAAAAAAAAAAASSSAAACCCEHB..............",
    "..BKKDDDAAADDDDOLHHFCCAAAAAAAAAAAAAAAAAAAAAAASAAAACCCCG...............",
    "...BGKJDDDDDDAAAHLHFCCAAAAAAAAAAAAAAAAAAAAAAAAAAADCCCCB...............",
    ".....BBJDDCCCDACHHHFCCAAAAAAAAAAAAAAAAAAAAAAAAAADCCCEHB...............",
    ".......BBJJJCCDCCKKCCCCCAAAAAAAAAAAAAAAAAAAAAAADCCCCEHB...............",
    ".........BBBBCCDBBHFCCCCAAAAAAAAAAAAAAAAAAAAAADCCCCEKB................",
    "............BGGGBBEFCCCCCAAAAAAAAAAAAAAAAAAAADCCCCEEKB................",
    "...............BBJEEFCCCCCCAAAAAAAAAAAAAAAAADCCCCEEEBB................",
    "................BGJEEFFCCCCCCCCAAAAAAAAAACCCCCCCEEEGB.................",
    ".................BGJEEEFCCCCCCCCDDDDDDDDCCCCCCCEEEGB..................",
    "..................BGJEEEFCCCCCCCCCCCCCCCCCCCCCEEEHB...................",
    "...................BBHEEEFFCCCCCCCCCCCCCCCCFFFEEGB....................",
    "....................BGFFEKFFFFCCCCCCCCCCFFFJKEFEB.....................",
    "....................BHCCEKHHHGEEEEEEEEEEGHHKJECBB.....................",
    "....................GGDDFHBBBGGGGGGGGGGGGBBHECDDHB....................",
    "...................BGGADFHB..BBBBBBBBBBB...GCCADBB....................",
    "...................BHAADFB.................BKCAABB....................",
    "...................BHAADBB.................BKCAABB....................",
    "...................BHQADJB.................BHHDNXB....................",
    "...................BHQADJB.................BHHDNXB....................",
    "...................GHAAMHB..................GHDNXHB...................",
    "..................BHHRAMB...................BHDNRBB...................",
    "..................BHRRABB...................BHDNRBB...................",
    "..................BPRRDEB...................BHHNRYB...................",
    "..................BPRRDEB...................BHFNRYB...................",
    "..................BPRDDEB...................BHFAAYB...................",
    "..................BHAADEB...................BHFAABB...................",
    "..................BHAADEB...................BHFAABB...................",
    "..................BHAADEB...................BHFAAEB...................",
    "..................BHCADEB...................BHCADEB...................",
    "..................BGCADEB...................BHCADEB...................",
    "..................BGCADEB...................BHCADBB...................",
    "..................BGFADEB...................BHCAMGB...................",
    "..................BGFAABB...................BHAAMB....................",
    "...................GAAAABB..................GAAABB....................",
    "...................BHAADBB.................BHAADBB....................",
    "...................BHAADBB.................BKCADBB....................",
    "...................BGAAAFB.................BKCAAHB....................",
    "..................BBBADAFHB................GCCAABBB...................",
    ".................BGHBDDDFJB...............BHFCCCKKHB..................",
    "................GGGGDDCDFJB...............BHFCCCAKKKG.................",
    "...............GGGGGQAACFBB...............BHECCAASSSKG................",
    "...............HGGGQAACFBBB................BBECCDASSHHB...............",
    "...............HHGDDEEBBBB.................BBGBECDDSHHB...............",
    "...............BHBEEEHBB.....................BBBEEEEHB................",
    "................BBBBBB........................BBBBBBB.................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (70, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 70x96).
    scale=int   -> sprite de 70x96 px ampliado por un entero, sin márgenes.
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
