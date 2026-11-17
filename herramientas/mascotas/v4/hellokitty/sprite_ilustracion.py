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
    "A": (250, 242, 242),
    "B": (20, 16, 16),
    "C": (249, 36, 57),
    "D": (226, 202, 205),
    "E": (195, 15, 43),
    "F": (74, 14, 23),
    "G": (236, 222, 223),
    "H": (47, 42, 42),
    "I": (76, 69, 70),
    "J": (129, 17, 33),
    "K": (159, 146, 147),
    "L": (252, 115, 136),
    "M": (136, 126, 127),
    "N": (252, 73, 93),
    "O": (203, 188, 189),
    "P": (182, 168, 170),
    "Q": (104, 96, 96),
    "R": (146, 94, 27),
    "S": (247, 223, 55),
    "T": (237, 187, 8),
    "U": (173, 124, 16),
    "V": (90, 67, 13),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "........................................BBBBBBB.........................",
    "........................................BBBBBBB.........................",
    "......................................BBECCCCCCBB.......................",
    "......................................BBECCCCCCBBB......................",
    "...........BBBBBBB..................BBECNNNNCCCCCBB.......BBBBBB........",
    "...........BBBBBBBB.................FFECLLLLCCCCCCB......BBBBBBBB.......",
    ".........BBGGGGGGGBBBB.............BJCNLLLLLCCCCCCEBB..BBBGGGGGGMBB.....",
    ".........BBAAAAAAAAHHH.............BJCNLLNNNCCCCCCEBB..HHAAAAAAAMBB.....",
    "........BBAAAAAAAAAAAHBBBB........FFCCNLLNCCCCCCCCEBBBBHAAAAAAAADDH.....",
    ".......BBAAAAAAAAAAAAAIIIB.......BFCCCNNNCCCCCCCCCEBBBBAAAAAAAAGDDHB....",
    ".......BBAAAAAAAAAAAAAAGDDBB.....BFCNLLCCCCCCCCCCCEBBDAAAAAAAAAGDDHB....",
    ".......BBAAAAAAAAAAAAAAGDDIBBBBBBBFCNLLCCCCCFFFFJCEBBDAAAAAAAADDDDHB....",
    ".......BAAAAAAAAAAAAAAAGDDDIBBBBBFCCNNNCCCCEFFFFJEEBBBOAAAAAAADDDDHB....",
    ".....BBKAAAAAAAAAAAAAAGGDDGAMMMBBCCCCCCCCCFFEEEFBBBBBBBOAAADDBPPPPHB....",
    ".....BBKAAAAAAAAAAAAAGDDGGAAAAGBBCCCCCCCCCFFEEJFBJJJJJBBBAABBBBBBBBB....",
    ".....BBKAAAAAAAAAAAAGGGGAAAAAAGBBCCCCCCCCCFFEJBFJNNNCCCBBPPBFFFFFBBB....",
    ".....BBKAAAAAAAAAAAAAGAAAAAAAAGBBCCCCCCCCCFFEFBJCNLLNCCCFBBCCCCCCCCBBB..",
    ".....BBKAAAAAAAAGAAAAAAAAAAAAAGBBCCCCCCCCCCEBFCCLLLLNCCCFBCCCCCCCCCBBB..",
    ".....BBKDAAAAAAADGAAAAAAAAAAAAGBBEEECCCCCCCEBFCNLLNCCCCCJBCCCCCCCCCCCEBB",
    ".....BBMDAAAAADDGAAAAAAAAAAAAAGBBEEECCCCCCCEBFCNLLNCCCCCJBCCCCCCCCCCCEBB",
    ".....BBMDGGGGAGGAAAAAAAAAAAAAAGBBEEEEEECCCCEBFCCCCCCCCCCJBCCCCCCCCCCCEBB",
    ".....BBMDDDDGAAAAAAAAAAAAAAAAAAGBBFEEEEEECFFBFCCCCCCCCCCFBFFFECCCCCCEJBB",
    ".....BBMDDDDGAAAAAAAAAAAAAAAAAAABBFEEEEEEFBBBFEECCCCCCEEFBFFFECCCCCCEJBB",
    "......BBBDDGGAAAAAAAAAAAAAAAAAAAAABBBBBBBHMMHBEECCCCCCEFFFEEFECCCCCEEJBB",
    ".......BBDDAAAAAAAAAAAAAAAAAAAAAAAABBBBBBHAAHBEEEEEEEEFBFEEEFECCCCEEEJBB",
    ".......BBDAAAAAAAAAAAAAAAAAAAAAAAAAGGGGGGGAAABBFEEEEEFBFEEEEECCCCCEEEJBB",
    ".......BBDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABFFFFFBFEEEEECCCCCCEEFB..",
    ".....BBMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBEEECCCCCCCCEEEEFB..",
    "......BMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPPBBBEEECCCCCCCCEEEEFB..",
    ".....BBMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADBBEEECCCCCCEEEEEBB...",
    "....BBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADHHJJEECCCCCEEEEFBB...",
    "....BBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMFFEEEEEEEEEEFB.....",
    "....BHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMFFJJEEEEEFFBBB.....",
    "....BHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGDDJJEEEEEBBBB......",
    "....BBAAAAAAAAAAIIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGDDDHBBBBBIIBB......",
    "BBBBBBBBAAAAAAAABBIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGDDHHHHHIKBB......",
    "BBBBBBBBBAAAAAKBBBQAAAAAAAAAAAAAAAAAAAAAAAGKMAAAAAAAAAGDDDDDDDDKBB......",
    "...BBBBBAAAAAAKBBQAQIAAAAAAAAAAAAAAAAAAAAGKBBMAAAAAAAAAAGDDDDDDKBB......",
    "...BBKGAAAAAAAKBBBBIIAAAAAAAAAAAAAAAAAAAAMBBBIHAAAAAAAAAGDDDOOOKBB......",
    "...BBKGAAAAAAAKBBBBBIAAAAAAAAAAAAAAAAAAAAMBBIHHHAAAAAAAAADDBBBBBBBBBBB..",
    "...BBKGAAAAAAAKBBBBBIAAAAAAAAAAAAAAAAAAAAMBBHHHHAAAAAAAAAQBBBBBBBBBBBB..",
    "...BBBHHHOAAAAKBBBBBIAAAAAAAAAAAAAAAAAAAAMBBBBBHAAAAAAAAAAQQOOOKBB......",
    ".BBBBBBBBOAAAAKBBBBBAAAAAAAAQQQMAAAAAAAAAMBBBBBHAAAAAAAAAAAAGDDKBB......",
    "BBBBBBBBGAAAAAABBBBAAAAAAAAARRRRMAAAAAAAAMBBBBBHAAAAAAAAAAAAGDDKBB......",
    "BBB.BBBGAAAAAAAAIIAAAAAAAAKBSSSTBPAAAAAAAMBBBBBAAAAAAAAGGGGGDDPBB.......",
    ".....BHGGAAAAAAAAAAAAAAAAAKBTTTTBPAAAAAAAAMBBBBAAAAAAAAIBBBKKPBB........",
    ".....BHHGKKKAAAAAAAAAAAAAAAAVVVVAAAAAAAAAAAHHAAAAAAAAAAIBBBBBBBB........",
    "......BBBBBAAAAAAAAAAAAAAAAAKKKKAAAAAAAAAAAAAAAAAAAAAAAAAAIIIBBBBB......",
    "......BBBBQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADDOBBBBBBB....",
    "....BBBBBQDDGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADDDOBB..BBB....",
    "...BBB..BBQDDDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPBBHDDDKQBB.........",
    "........BBQDDDDDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPBBBHHKQBB..........",
    "..........BBIDDDGGGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGDDDPPBBBHBB...........",
    "..........BBIOODDDDGAAAAAAAAAAAAAAAAAAAAAAAAAAGGGDDDDDDPBBBB............",
    "............BBHDDDDDDDDDGAAAAAAAAAAAAAAAAAAAAADDDDDDDPIII.BBBB..........",
    "............BBBHHHDDDDDDGGGGGGGAAAAAAAGGGGGGGGDDDDDPPBBBB...BB..........",
    "...............BBBMMMMDDDDDDDDDGAAAAAADDDDDDDDDDDDDBBBB.................",
    "..................BBBBBOOOOOODDDDDDDDDDDDDDDDDDDHHHBBB..................",
    "..................BBBBBBBBBBODDDDDDDDDDDBBBBBBBBBBB.....................",
    "....................BBBBBBFFBIIIIIIIIIIBFFFBBBIIB.......................",
    "..................BBBBBOBFEJBBBBBBBBBBBBEEEBBAAABBB.....................",
    "..................BBBAAOBFEJFDAAAAAAAKFEEEEBAAAAAMMBB...................",
    "..............BBBBBBAAAEECJFDAAAAAAAAKFECEBIAAAAAAABB...................",
    ".............BBQQQAAAAHBECJFAAAAAAAAAFFECEBIAAAAAAGGBBBB................",
    ".............BQAAAAAAAHBECEFAAAAAAAAFFCCCEBAAAAAAAGDAHHB................",
    "...........BBBAAAAAAAAJJCCEEEKKKKKKKFFCCCEBAAAAAGDDAAAAHB...............",
    "...........BBAAAAAAAMBJCFFFEEFFFFFFFFCJJRRBBDAAADGGAAAAAH...............",
    "..........BBAAAAAAAGMBJJUUUREEEEEEEEEERRRRFFBDGGGAAAAAAAOBB.............",
    "..........BBAAAAAAGGGJJFSSSRFCCCCCCCEFSSSUFFBBDGAAAAAAAAOBB.............",
    "..........BBAAAAAGDIBCEFSSTRFCCCCCCCEFSSSUFFBBBGAAAAAAAAPBB.............",
    "..........BBDDAAGDDIBCEFTTTRCCCCCCCCEFTTTUFEEBIAAAAAAAGGPBB.............",
    "..........BBDDDDDDDICCCCFFFCCCCCCCCCCERRRRJEEBIAAAAAAADPBBB.............",
    "...........BIDDDDDBJCCCCCJJCCCCCCCCCCCCFFJEEEBIDDDAAGDDBBB..............",
    "...........BBIPPPBBJCCLLCCCCCCCCCCCCCCCCCCCEEEIIDDGGDDDBB...............",
    ".............BBBBBFCCLLLCCCCCCCCCCCCCCCCCCCEEEJBIDDDDDBB................",
    ".............BBBBFCCLLLLCCCCCCCCCCCCCCCCCCCCEEJBBIIIIIBB................",
    "................BFCNLLNCCCCCCCCCCCCCCCCCCCCCCEEEJBBBBB..................",
    "...............BFCCNLLNCCCCCCCCCCCCCCCCCCCCCCEEEEJJJFB..................",
    "..............BFCCCCNNCCCCCCCCCCCCCCCCCCCCCCCEEEEEEEFBBB................",
    "..............BFCCCCCCCCCCCCCCCCCCCCCCCCCCCCCEEEEEEEEJBB................",
    "..............BFCCCCEEEEECCCCCCCCCCCCCCCEEEEEEEEEEEEEJBB................",
    "..............BBBBFEEEEEEECCCCCCCCCCCCCEEEEEEEEEEEFFBB..................",
    "................BBFJJJJEEEEEEEEEEEEEEEEEEEEEEEEEFFBBBB..................",
    "...................BBBJJJJEEEEEEEEEEEEEEEEEEFFFFBBB.....................",
    "...................BHPJBBBFFFFFFFFFFFFFFFFFBBBBBBBB.....................",
    "...................BHAPAAABBBBBBBBBBBBBBBBBBOOOAABB.....................",
    "..................BBAAAAAAAOOOOOKBBBPOODGGGAAAAAAABB....................",
    "..................BAAAAAAAGGDDDDKBBBPDDGAAAAAAAAAAMBB...................",
    ".................BBAAAAAAAAAGDDDKBBBPDGAAAAAAAAAADMBB...................",
    "................BBBAAAAAAAAAGDDDKBBBPDGAAAAAAAAAGDMBB...................",
    "................BBBGAAAAAADDDDDDKBBBPDGGGAAAAAAGDDMBB...................",
    "................BBBDGAAAAADDDDDKBB.BBPDDDAAAAAAGDDBBB...................",
    "................BBBDDDDDDDDDDDDBB..BBBDDDDDDDDDDDBB.....................",
    "..................BBDDDDDDDDIIBBB...BBBDDDDDDDDIIBB.....................",
    "..................BBBBBBBBBBBBB......BBHHHHHHHHBBB......................",
    "....................BBBBBBBBB..........BBBBBBBB.........................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (72, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 72x96).
    scale=int   -> sprite de 72x96 px ampliado por un entero, sin márgenes.
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
