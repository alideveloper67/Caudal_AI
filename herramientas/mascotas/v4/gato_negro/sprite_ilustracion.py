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
    "A": (24, 22, 23),
    "B": (0, 0, 0),
    "C": (20, 15, 16),
    "D": (17, 12, 12),
    "E": (63, 61, 65),
    "F": (23, 20, 21),
    "G": (72, 71, 76),
    "H": (47, 45, 48),
    "I": (12, 8, 9),
    "J": (34, 32, 34),
    "K": (79, 78, 83),
    "L": (6, 4, 5),
    "M": (188, 187, 190),
    "N": (117, 116, 121),
    "O": (99, 100, 101),
    "P": (198, 197, 199),
    "Q": (144, 142, 144),
    "R": (176, 174, 177),
    "S": (125, 72, 32),
    "T": (221, 132, 60),
    "U": (129, 180, 111),
    "V": (243, 242, 243),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "................................BBBBBBBB.......................BBBB....",
    "................................BBDDDDDB.......................BOOB....",
    "................................BDDDCCCBBB.....................BPPQBB..",
    "...............................LLDDEECCDBB.....................BOOQQB..",
    "..............................BIDDHKKCCCDBB....................BBOMMD..",
    "..............................BIDDHKKHHCDLLB...................BOOMMD..",
    ".............................LLDDGGKKKGDCCLB.................BBMMMMMD..",
    "............................BLDDHKKKKKGCCCLBBBBBBB...........BQQMPOOB..",
    "............................BIDDHKKKKKKGJCCCCCCCDB.........BBMMMPPBBB..",
    "............................BIDDHKKKKKKKJCCCCCCCDBBB.......BRRMMMBB....",
    "............................BIDDHKKKKKJJAACEEEEFFFDB.......FMMPMM......",
    "............................BIDDHKKKKJAAAAEKKKKFFFDBB......FMMPMBBB....",
    "...........................BIDDHHKEKJAAAAAJJJJHHEFFFBB.....FMMPPKKB....",
    "..........................BIDDDHHKEAAAAAAAAAAAAHEHFFIBB....FMMMMPPBBB..",
    "..........................BIDDEHJJJAAAAAAAAAAAAAHEEJFIB....MMMMMMMRRB..",
    "..........................BIDHEHAAAAAAAAAAAAAFFAAHAJFDB.....BMRRRMPPPBB",
    "........................BBBIDHHAAAAAAAAAAAFLLLLLAAAAFDBB.....BBBBMMMPQB",
    "........................BBIDHHHAAAAAAAAAAAFFLLLLLAAHHFDBB......BBBMMPQB",
    "........................BIDHHHHAAAAAAAAAAAAAAULLLJHKHFFIBB......BBMMPBB",
    "........................BICHGHAAAAAAAAAAAAAAAAULJJJEKHFAIB.......HMMMQB",
    "........................BICHGHAAAAAAAAAAAAAAAFFAJJJJEEAAABB......HMMRQB",
    "........................BDCHGHAAAAAAAAAAAAAAAFCCAJJJJJAHABB.....BHHRBBB",
    "........................BDCHGHAAAAAAAAAAAAGGGGGGHJJJJJHAACBBBBBBBHHBB..",
    "........................BDCHHHAAAAAAAAAEEEHHHHHHHHJJJJJCCCCCFFCCFFBBB..",
    "........................BDCFAAAAAAAAAAAEEHFFAAHHHHJJJJJSSSSQQQQQSSDBB..",
    "........................BDCFAAAAAAAAAAAAFFFFFAHHHJJJJJCSTTTCVVCCCCBDB..",
    "........................BDCFAAAAAAAAAAAAAAAEKKHJJJJJAFFCDDCCCCCCCCBBB..",
    ".......................BBDCFAAAAAAAAAAAAAAEHHHJAAAAAFCCIILLIIIIIIIB....",
    "......................BLLDCFAAAAAAAAAAAAAAHHAAAAFCCCCIBBBBBBBBBBBBB....",
    "......................BIDDDCAAAAAAAAAAAAAHHHFFFFFCIIIBB................",
    "......................BIDFAAAAAAAAAAAAAAAAFCCCCCCBBBBB.................",
    "......................LIIFAAAAAAAAAJHHAAAAAFAACIIBB....................",
    ".....................LILLFAAAAAAAAAJGGAAAAAAAJIBBB.....................",
    "................BLLLLIDDDAAAAAAAAAAJGGHHAAAAAJJLLB.....................",
    "................BIDDDDDAAAAAAAAAAAAJGGGGHAAAAJCCIB.....................",
    "..............LLBIDDDDAAAAAAAAAAAAAJGGGGGEAAAFCCIB.....................",
    "..............LDDDHEEEEAAAAAAAAAAAAJGGGGGGEAAFCCIB.....................",
    "............BBLDDDHGONOAAAAAAAAAAAAAAJGGGGGGGECCIBBB...................",
    "...........BLDDDEEGGONOAAAAAAAAAAAAAAJGGGGGGGEDDCCBB...................",
    ".........BBBLDDEKNNNJAAAAAAAAAAAAAAAAAJHGGGGGGGGHCDB...................",
    ".........BBDDDEEKNNNJAAAAAAAAAAAAAAAAAAHGGGGGGGGHCDB...................",
    ".........BDDDDGGKKKKJAAAAAAAAAAAAAAAAAAJGGGGGGGGHCDB...................",
    ".........BDDDOOGAAAAAAAAAAAAAAAAAAAAAAAAJGGGGGGGHCIB...................",
    ".........BDDEOOGAAAAAAAAAAAAAAAAAAAAAAAAAJGGGGGGHCIB...................",
    ".......BLLDEEOOGAAAAAAAAAAAAAAAAAAAAAAAAAJGGGGGGHCIB...................",
    ".......BBCCEEJFAAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGGGHCIB...................",
    ".......BCCHGGJAFAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGGGHCIB...................",
    ".......BCCHGGJAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGGGHCIB...................",
    "......BBCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGHCCCIB...................",
    "....BLDDFFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGHCDDBB...................",
    "....BLDCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHGGHCDBBB...................",
    "....BLDCAAAAAAAAAAAAAAAAAAAAAAAAFAAAAAAAAJGGGGHCDB.....................",
    "....BLDCAAAAAAAAAAAAAAAAAAAHEEAAFAAAAAAAAJKGGGHCDB.....................",
    "....BLDCAAAAAAAAAAAAAAAAAAAHGGAAFFAAAAAAAJKGHCCCDB.....................",
    "....BLDCAAAAAAAAAAAAAAAAAAAHEEHHFFAAAAAAAJKGHCCDBB.....................",
    "..BBBIDCAAAAAAAAAAAAAAAAAAAAAHGGFFAAAAAJGGKGCCDBBB.....................",
    "..BIIIDCAAAAAAAAAAAAAAAAAAAAFHGGFFAAAAAJKGGCCCDB.......................",
    "..BIDCAAAAAAAAAAAAAAAAAAAAAFCHGGFFAAAAAJKKECCCDB.......................",
    "..BIDCAAAAAAAAAAAAAEEEEEACFCCHGGFFAAAAAJKKECCCDB.......................",
    "...DDCAAAAAAAAAAAAEHKKGGGCCCCHGGFFAAAAAJKKECCCBB.......................",
    "...DDCFAAAAAAAAAAAHHHHHGGHHCCHGGFFAAAAAJKKECCBBB.......................",
    "BBBDDCFAAAAAAAAAAAAAAAAGGGGCCHEGFAAFAFJKKECCCB.........................",
    "BLLDDCFAAAAAAAAAAAAAAAAHHGGGHHDEHHFAFAJKGDDCCB.........................",
    "BDDDFFFAAAAAAAAAAAAAAAAAAGGGGHDGEEFAAAJKGCCCCB.........................",
    "BDDFFFFAAAAAAAAAAAAAAAAAAEEGGHDEGEAAAAJKGDCCCB.........................",
    "BDDCFFAAAAAAAAAAAAAAAAAAAAAGGEHIGEFAAAJKGDCCCB.........................",
    "..DCFFAAAAAAAAAAAAAAAAAAAAAGGGEIGGFFAAJKGDCCCB.........................",
    "..DCFFFAAAAAAAAAAAAAAAAAAAAAGGEIGGFAFAJKGDDCCB.........................",
    "..DCFFFAAAAAAAAAAAAAAAAAAAAAJGEIGGFAAAJKGDCCCB.........................",
    "..DCFFFFAAAAAAAAAAAAAAAAAAAAJGEIGGFFAAJKGDCCCB.........................",
    "..DCFFFAAAFAAAAAAAAAAAAAAAAAJGEIGEFFFFJKGDCCCBBBB......................",
    "..DFFFFAFFFFFFFFAAAAAAAAAAAAJGHIGEFFFFJKGDCCCIIBB......................",
    "..DFFFFFFFFFFFFFAAAAAAAAAAAAJGHIGEFFFAJKGDCCCCCDBB.....................",
    "..DDFFFFFFFIIIIDDAAAAAAAAAAAJGHIGEFFFAJKGDCCEEHCDBB....................",
    "..DDDFFFFFFIDDIDDDAAAAAAAAAAJGHIGEFFFAJKGCCCGGHCCBBB...................",
    "...DDFFFCDIIEEEJIIFAAAAAAAAAJGGIGEFFFFJKGCCCCGGECDDL...................",
    "....DFFFCDJJEEEJIIFAAAAAAAAHHJDDGEAAFFJKKHHDCCEGHCCL...................",
    "....DFCDDJEEEEFCIIFFAFAAAAAEEJDDGGGGCCFFJKEDCFEGHCCL...................",
    "....DFCDDJEEEFCDDDFAAAFAJJJHHDDCJJGGGJFFJKEDDFEHHCCL...................",
    "....DIIDJEEEEFIICFFAFFFFEEEJIDCCCCEEEJFFJKEDDFHECCCL...................",
    "....DDDJEEEEEFIICFAFFFAFEEEJICFFCCCEEJFFFEDDDCCCDCCL...................",
    "....DDDJEEJAAAIDDCCCCFFAEEEJICFFFCCEEJFCCDDIIIIIDCCL...................",
    "....BDDJEEJAANNIIIIIICFFHHHJIIFFFCCEEJCDDIIDFFFCCCCL...................",
    "....BDDJEEJANNNNJJJJIIIIIIIIIIIIIIIIIIIDIIIEEEEEECCL...................",
    "....BDDJEEEENNNNNNNIIIIIIIIIIIIIIIIIIIIEEEEEHJJJACCL...................",
    "....BDDCCEEENNNNNNNNHHHHHHHHHHHHHHHHHHHEEEEEHAAAACCL...................",
    "....BLDCCJEEGGGONNNNNNNEEEEEEEEEEEEEEEEEEEEHAAAAFCCL...................",
    "....BBLDDJEEEEEONNNNNNNEEEEEEEEEEEEEEEEEEEEHAAAAFCLB...................",
    "......LDDCAAHEEGGGGGGGGEEEEEEEEEEEEEEEEEAAAAAACCCLBB...................",
    "......LIDCCCHEEEEEEEEEEEEEEEEEEEEEEEEEEEAAFFFFCIILB....................",
    "......BBIDCDCAAAAEEEEEEEEEEEEEEEEEAAAAAAAACCCCCBBB.....................",
    ".......BLLDDCCCCCEEEEEEEEEEEEEEEEEAAAAAAAACCIIBB.......................",
    "........BBBDDDDDDCCCCCCCCCCCCCCCCCCCCCCCCCCBBBBB.......................",
    "..........BBBBBLDDDDDDDDDDDDDDDDDCDDDCCBBBBBB..........................",
    "...............LDDDDDDDDDDDDDDDDDDDDDDBB...............................",
    "...............BBBBBBBBBBBBBBBBBBBBBBBBB...............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (71, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 71x96).
    scale=int   -> sprite de 71x96 px ampliado por un entero, sin márgenes.
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
