#!/usr/bin/env python3
"""Pixel art reproducido de forma exacta. Generado por la skill pixel-art-exact.

Requiere solo Pillow:  pip install pillow
Uso:  python prueba_e1.py                 -> guarda prueba_e1.png
      from prueba_e1 import render; render(scale=8).save("x.png")
"""
from PIL import Image, ImageDraw

# Paleta: símbolo -> (R, G, B). '.' es el fondo.
PALETTE = {
    ".": (255, 255, 255),
    "A": (70, 57, 71),
    "B": (21, 19, 18),
    "C": (252, 245, 241),
    "D": (51, 40, 50),
    "E": (34, 29, 31),
    "F": (147, 125, 151),
    "G": (244, 133, 175),
    "H": (229, 209, 201),
    "I": (60, 48, 59),
    "J": (228, 97, 144),
    "K": (240, 227, 222),
    "L": (118, 102, 113),
    "M": (90, 79, 87),
    "N": (248, 172, 178),
    "O": (170, 94, 123),
    "P": (208, 196, 192),
    "Q": (166, 156, 153),
    "R": (106, 54, 73),
    "S": (187, 177, 174),
    "T": (250, 205, 206),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..BBBBB.....................................................................",
    "..BBBBB.....................................................................",
    "BBJJJJBBB...................................................................",
    "BBGGGJJBB............................................................BBBBB..",
    "BBGGGJJBB............................................................BBBBB..",
    "BBJJJJJBB..........................................................BBOOOOOBB",
    "BBJJJJJBB..........................................................BBGGGGJBB",
    "..RRRREEEBBB.......................................................BBGGGJJBB",
    "..BBBBAAABBBB......................................................BBJJJJJBB",
    "....BBAAAEEEEBBBB..................................................BBJJJJJBB",
    "....BBAAAAAAEBBBB...............................................BBBBBBJJJJ..",
    "....BBAAAMMMAEBBB...............................................BBEEBBRRBB..",
    "....BBAAAFFFFAAAABBB........................................BBBBDAAAIBBBBB..",
    "....BBAAAFFFFAAAABBB........................................BBBBDAAAIBB.....",
    "....BBAAAFFFFFFFAIIIBBB.................................BBBEFFFMAAAABBB.....",
    "....BBAAAAFFFFFFAAAAABB.................................EEEFFFFMAAAABBB.....",
    "....BBAAAAAFFFFFAAAAAABBBB..........................BBBBLFFFFLFMAAAABBB.....",
    "....BBAAAAAFFFFFAAAAAAABBBB.........................BBBBLFFFLAAAAAAEBBB.....",
    "....BBAAAAAFFFFFAAAAAAAAAIEBB...................BBBELLLLFFFFLAAAAAAEBB......",
    "....BBDIAAAAALFFAAAAAAAAIDEBB...................BBBEFFFFFFFAAAAAAAAEB.......",
    "....BBDIAAAAALFFAAAAAAAAIDEBB.................BBBABFFFFFFFAAAAAAAAAEB.......",
    "....BBDIAAAAAAAAAAAAAAAAIDEBBBBBBBBBBBBBBBB...BBALFFFFMMMMAAAAAAAAAEB.......",
    "....BBDIAAAAAAAAAAAAAAAAEDBDDDDDDDDDDDDDDDDBBBBBALFFFFAAAAAAAAAAAAAEB.......",
    "....BBDIAAAAAAAAAAAAAAAEBBBAAAAAAAAAAAAAAAABBBBDAMMMMMAAAAAAAAAAAIIEB.......",
    "....BBDIAAAAAAAAAAAAIEELLLLAAAAAAAAAAAAAAAADDBBDAAAAAAAAAAAAAAAAAIDEB.......",
    "....BBDDIIAAAAAAAAAAIBBFFFFAAAAAAAAAAAAAAAAAADBDAAAAAAAAAAAAAAAAAIDEB.......",
    "....BBDDDDAAAAAAAAIEIFFFFFFAAALLLLLLMAAAAAAAAADAAAAAAAAAAAAAAAAAAIDEB.......",
    ".....BEEDDAAAAAAAAIEFFFFLMMAALGGGGGGGMAAAAAAAAAAAAAAAAAAAAAAAAAAAIDEB.......",
    "......BBDDDDDAAADDDFFFFFLAAALGGGGGGGGGGAAAAAAAAAAAAAAAAAAAAAAAAIIDBB........",
    "......BBDDDDDIIDDMMFFFLLAAAGGGGGGGGGGGGJAAAAAAAAAAAAAAAAAAAAAAADDDBB........",
    "......BBEEEDDDDBMFFFFFMAALLGGGGGGGGGGGGGJAAAAAAAAAAAAAAAAAAAAAADDDBB........",
    "........BBBDDBBFFFFFFFMAAGGGGGGGGGGGGGGGGJAAAAAAAAAAAAAAAAAIIIIDDDBB........",
    "........BBBBBEEFFFFLLLAAAGGREEEGGGGORRRGGJAAAAAAAAAAAAAAAAAIDDDDDDBB........",
    "...........BBAAFFFLAAAAAAGGREEEGGGGOEEEOGJAAAAAAAAAAAAAIIIIDDDDEBB..........",
    "...........BBAAFFFLAAAAAAGGREEEGGGGOEEEOGJAAAAAAAAAAAAAIDDDDDDDEBB..........",
    "...........BBAAAAAAAAAAAAAGREEOGGGGOEEEJGOAAAAAAAAAAAAAIDDEEEEEEB...........",
    ".........BBIAAAAAAAAAAAAAAAGOOGGGGGGOGJGOAAAAAAAAAAAAAAIDDBBBBB.............",
    ".........BBIAAAAAAAAAAAAAAMOGGGGGGGGGGGMMAAAAAAAAAAAAAAAIDBBBBB.............",
    ".........BBIAAAAAAAAEEEEAAAMOGGGGGGGGOOAAAAAAAAAAAAAAAAAIDBB................",
    ".........BBIAAAAAADDEMMAIIAAMGGIGGGGGAAAAAAAAAAAAAAAAAAAIDBB................",
    ".........EEIAAAAIIBBCCCCPIIAAOOIOOGOOAAAADDIIAAAAAAAAAAAIDDDBB..............",
    "........BDAAAAAABBPCCCCCPPIAAAAAAAAAAAAAABBBEAAAAAAAAAAAIDDDBB..............",
    "........BDAAAAABBPCCCCCCCCCAIAAAAAAAABBBBKKKEEAAAAAAAAAAIDDDBB..............",
    "........BDAAAADBBBLCCCCCCCCCIIAAAAAEESSSKCCCCMMDAAAAAAAAIDDDBB..............",
    "........BDAAADACCCELCCCCCCCCCIAAIAAFFCCCCCCCCCCCDAAAAAAADDDDBB..............",
    "........BDAADALCCCEEECCCCCCCCCAIIACCCCCCCCCCCCCQCIIAAAADDDDDBB..............",
    "........BDAAELCCQQEEEECCCCCCCCCIICCCCCCCCCCCCCQCCIIAAAADDDDDBB..............",
    "........BDAAECCCCQEEEEEEPCCCCCCKKCCCCCCCCCCCECCCCCIIAAADDDDDBB..............",
    "........BDAAACCCCCMEEEEEPCCCCCCCCCCCCCCCCCEEECCCCCDEAAADDDDDBB..............",
    "........BDABQCCCCCMEEEEEPCCCCCCCCCCCCCMMEEQEEECCCCDEAAADDDDDBB..............",
    "........BDABQCCCCCMEEEEECCCCCCCCCCCCCCCEEEQEEECCCCCBBAADDDDDBB..............",
    "........BBDBQCCCCCEEEEEECCCCCCCCCCCCCCFEEEBBECCCCCCLBIIDDDDDBB..............",
    ".........BBBQCCTTKKEEEEPCCCCCCCCCCCCCCFEEEEEACCCCCCLBDDDDDEEB...............",
    ".........BBBQCTNNTKKCCPCCCCCCJCCCCCCCCFEEEEEACCCCCCLBDDDDDBB................",
    ".........BBBQNNNNNTCCCCCCCCCJJJCCCCCCCCEEEEECCCCCCCLBDDDDDBB................",
    "...........BBNNNNNTCCCCCCCCCCOOCCCCCCCCEEEEECCCCCCCBEDDDDDBB................",
    "...........BBBNNNNKCCCCCCCCHHCCCCCFCCCCCCEEENNNCCFBEDDDDBB..................",
    "............BBBPNKCCCCCCCCCCMCCCCFECCCCCCCTNNNNNCFBEDDDDBB..................",
    ".............BBPCCCCCCCCCCCCCMFFFECCCCCCCCTNNNNNNBEDDDEEBB..................",
    ".............BBBBCHKCCCCCCCCCCMMCCCCCCCCCCTNNNNNBEIIDDEB....................",
    "...............BBBHKKKKCCCCCCCCCCCCCCCCCCCCTNNNBEEIDEEBB....................",
    "...............BBBFFFKHKCCCCCCCCCCCCCCCCCKKKHFBBIIIIBB......................",
    ".................BBBBBHHHHHHHCCCCCCCCHHHHHHHHFBBBBBBBB......................",
    ".................BBBBBBBBBMHHHHHHHHHHHHHHHHEEEBBBBBB........................",
    "..............BBBBIMABBBBBDMMMMMMMMMMMMAAABBBEAABBBBBB......................",
    "..............BRRIIMAADDDDDBBBBBBBBBBBBBBBAIIIAAAIBBBB......................",
    ".............BOGGJRDAAAAAAAABBBBBBBBBBAAAAAAAAAAAIBGGGBB....................",
    ".............BOGGJRDAAAAAAAAAAAAAAAAAAAAAAAAAIIIIBJGGGBB....................",
    ".............BOJJJRBBBBBBAAAAAAAAAAAAAAAAAAEEBBBBBJJGJBB....................",
    "..............BOJJEBLLLBBAAAAAAAIIAAAAAAADBEEQQQEERJJRB.....................",
    "..............BBBBELCCCLBBDAAAAABBAAAAAAADBSKCCCEBBRRB......................",
    "................BACCCCKLLBDAAAEAOOAEDAAAADBSKCCCCBBBBB......................",
    "...............BACCCCKHHLBDAABEGGGOEEDAAADBBHCCCCCBB........................",
    "..............BBSCCCKHHHLBDDBBBGGJJEBBAAADBBBHCCCCCMB.....BBBBB.............",
    "..............BBSCCCKHQQLLSBBBBJJJJBBFEEDDBBBCCCCCCMB..BBBBBBBB.............",
    "..............BBSCCCKHQBLCSSPBBJJJJBFCAADDDAACCCCCCMB..BBBAAAIB.............",
    "...............BBSCCCKQBLCCCCPBDIIICCCCCLBFHCCCKHHHMB..BBAAAAIB.............",
    "................BBCCCBBLCCCCCCCIDDCCCCCCLBFHHCCKHHBB....BIAAAIB.............",
    "................BBBCHBBQCCCCCCCCCCCCCCCCCBBAHHHHHBBB....BIAAAIB.............",
    "..................BBHBBQCCCCCCCCCCCCCCCCKBBAHHHHBB.....BBAABEEB.............",
    "..................BBBEBCCCCCCCCCCCCCCCCCCKBBBBBBBB.....BIAABBBB.............",
    "...................BBECCCCCCCCCCCCCCCCCCCCHBFBBBBB...BBAAIBB..B.............",
    "....................BECCCCCCCCCCCCCCCCCCCCCHHFBBBBBBBBAAAIB.................",
    "....................BEKKCCCCCCCCCCCCCCCCCCCHHFBDAAAAAAAADB..................",
    "....................BEHHCCCCCKKKKKKKKKCCCCCHHFBDAAAAAAADBB..................",
    "...................BBEHHCCCCKHHHHHHHHKCCCCCHHFBBBBBBBBBB....................",
    "..................BBBBKKCCCCKHQQQQQHHKCCCCCKKCDDBBBBBBB.....................",
    ".................BDPPPCCCCCCKHDBBBBQHKCCCCCCCCCBBB..........................",
    ".................BDCCCCCCCCCKHDBBBBQHHCCCCCCCCCCBB..........................",
    "...............BBBPCCCCCCCKHHHDB.BBQHHKKCCCCCCCCCLB.........................",
    "...............BBPCCCCCCCCKHPPBB...EHHHKCCCCCCCHHLB.........................",
    "...............BBPCCCCCCKHHHFBB....BEHHHHHCCCCCHHLB.........................",
    "...............BBPKKCKKKHHHPFBB....BEHHHHHHHHHHHHBB.........................",
    "...............BBBPHHPPPPPPBBB.....BBIIHHHHHHHHHBB..........................",
    ".................BBBBBBBBBBBB........BBBAAAAAAABBB..........................",
    ".................BBBBBBBBBBBB........BBBBBBBBBBB............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (76, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 76x96).
    scale=int   -> sprite de 76x96 px ampliado por un entero, sin márgenes.
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
    render().save("prueba_e1.png")
    print("Guardado prueba_e1.png")
