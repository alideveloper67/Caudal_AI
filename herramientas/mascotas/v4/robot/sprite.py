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
    "A": (4, 4, 4),
    "B": (247, 245, 245),
    "C": (28, 40, 59),
    "D": (224, 222, 235),
    "E": (249, 185, 11),
    "F": (207, 203, 215),
    "G": (16, 21, 28),
    "H": (87, 182, 234),
    "I": (33, 117, 182),
    "J": (55, 155, 211),
    "K": (208, 128, 9),
    "L": (169, 175, 202),
    "M": (104, 104, 108),
    "N": (133, 135, 150),
    "O": (28, 98, 142),
    "P": (166, 210, 237),
    "Q": (43, 224, 245),
    "R": (253, 221, 54),
    "S": (25, 66, 99),
    "T": (74, 75, 79),
    "U": (120, 159, 198),
    "V": (32, 216, 240),
    "W": (117, 73, 8),
    "X": (252, 240, 148),
    "Y": (220, 161, 63),
    "Z": (225, 197, 116),
    "a": (161, 107, 10),
    "b": (146, 119, 66),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".................................AAAAA.................................",
    "...............................AAAAAAAAA...............................",
    "..............................AAAAAKKAAAA..............................",
    "..............................AAAKERREAAAA.............................",
    ".............................AAAKERXXREAAAA............................",
    ".............................AAAERRBBXREAAA............................",
    ".............................AAEERRBBXREEAAA...........................",
    ".............................AAEEERRRRREEAAA...........................",
    ".............................AAKEEERRREEEAAA...........................",
    ".............................AAAKEEEEEEKAAA............................",
    ".............................AAAAKEEEEKaAAA............................",
    "..............................AAAKKKKKaAAA.............................",
    "...............................AAAWWAAAAA..............................",
    "................................AAAAAAAA...............................",
    ".................................AAACAA................................",
    ".................................AACSGAA...............................",
    ".................................AASSGAA...............................",
    ".................................AACSSAA...............................",
    "................................AACSSSGAA..............................",
    "....................AAAAAAAAAAAAAAACCCGAAAAAAAAAAAAAAA.................",
    "................AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA..............",
    "..............AAAAAAALLLLFFFFFFFFFFFFFFFFFFFFFFFFFFTTTAAAA.............",
    ".............AAAALLFDDDDDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBAGAAA...........",
    "............AAANDFFDDDDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBGAAA..........",
    "...........AAGNDDDDDDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBCAAA.........",
    "..........AAGFDDDDDDDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDCAA.........",
    ".........AAAFFDDDDDDBBBBBBBBMMMMMMMMMMMMMMMMMMMMMMMMMBBBBBBDCAA........",
    ".........AAAFFFDDDDBBBBBBFAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBAAA.......",
    ".......AAAAAAFFFDDDBBBBBFAAAAGGGGGGGGGGGGGGGGGGGGGGGGAAGNBBBBAAA.......",
    ".....AAAAAAAAAFFDDDBBBBBAAGGCCCCCCCCCCCCCCCCCCCCCCCCCGGAANBBBAAAAAA....",
    "....AAAAIHHHAAAAFDDBBBBBAACCCCCCCCCCCCCCCCCCCCCCCCCCCCGAAABBBFAAAAAA...",
    "..AAAAAAIHHHHAAAADDBBBBAAGCCCCCCCCCCCCCCCCCCCCCCCCCCCCCGAABBBFAAOGAAA..",
    "..AAAAAAIIHHHJAAADDBBBBAAGCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCAAABBBAAOOGAA..",
    ".AAAAEEEEIHHHHJAADDBBBBAACCCCCCCCCCCCCCCCCCCCCCCCCJJCCCCCAABBBTAOOYGAA.",
    ".AAAEERRXEHHPPHAADDBBBBAGCCCCCQPPVCCCCCCCCCCCCCCCJJPCCCCCGGBBBTASHYAAA.",
    ".AAAERRXRROOHHHHATDBBBBAGCCCCCQQPVOCCCCCCCCCCCCCCQPQQOCCCGGBBBTASHYYAAA",
    "AAAEEERRXREOHHHHHTBBBBBAGCCCCOQQQVOCCCCCCCCCCCCCCVQQQOCCCGGBBBTASHNYAAA",
    "AAWEEEERRREEHHHHOANBBBBAGCCCCOVQQVOCCCCCCCCCCCCCCVQQVOCCCGGBBBTAAHNEAAA",
    "AAWEEEEEEEETIHHHOANBBBDAGCCCCOVQQVOCCCCCCCCCCCCCCVQVVOCCCGGBBBTAAJNEKAA",
    "AAWEEEEEEEETIHJJOANDBBDAGCCCCCVVQVCCCCCCCCCCCCCCCVQVVCCCCGGBBBTAAJNEKAA",
    "AAWEEEEEEEETIHJJOAMDBBBAGCCCCCCVQCCCSCCCCCCCCOCSCCQVCCCCCGGBBBTASJNEAAA",
    "AAAEEEEEEEEIIJJJJAMDBBBAGCCCCCCOOCCCSQQQCCCCOQVSCCSSCCCCCGGBBBTASIbAAAA",
    ".AAAEEEEEEEGIJJJGGDDBBBAACCCCCCCCCCCCJQQQJJQQVVCCCCCCCCCCAGBBBTASIbWAA.",
    ".AAAKKEEEEGIIJIIGGFDBBBAACCCCCCCCCCCCCJQQQQQQVSCCCCCCCCCCAGBBBTASIWGAA.",
    ".AAAAKKEEEOOIIIIAFFDBBBAACCCCCCCCCCCCCCCQQQQQSCCCCCCCCCCGAABBBTASSGAA..",
    "..AAAAKKKOOOIIICAFFDBBBAAGCCCCCCCCCCCCCCCSSSCCCCCCCCCCCGAABBBBTACCAAA..",
    "...AAAGKKSOOOOCACFFDBBBBAAGCCCCCCCCCCCCCCCCCCCCCCCCCCCGAABBBBBTAAAA....",
    "....AAAGSOOOOAAAFFFFDBBBBGAAGGGGGGGGGGGGGGGGGGGGGGGGGAAABBBBDAAAAA.....",
    ".....AAAAGGGAAAALFFFDBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBDDAAAA......",
    ".......AAAAAATLLLFFFFDBBBBBBMMMMMMMMMMMMMMMMMMMMMMMMMBBBBBDFLGAA.......",
    ".........AAATLLLLLFFFFDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDFLGAA........",
    "..........AAATLLLLLLFFFDBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDDDFFGAA.........",
    "...........AAAALLLLLLLFFDDDDDDBBBBBBBBBBBBBBBBBBDDDDDFFFDFGAAA.........",
    "............AAAAANNLLLLLFFFFFFDDDDDDDDDDDDDDDDDDFFFFFFNNAAAAA..........",
    "..............AAAAACCCNNNNNNNNNNNNNNNNNNNNNNNNNMMAACCCAAAAA............",
    "................GGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA..............",
    "................AGAAAAAAAGGGAAAAAAGGGAAAAAAAGGAAAAAAAAAAAA.............",
    "...............AAAAAAAAASIIIIIAUULLLLLLLLLLLLLLLLLAAAAAAAAA............",
    "..............AAAAAFFFAAASIJIIUUPDDDDDDDDDDDDDDDDDDAAALLAAAAA..........",
    "............AAAGAADDBBBAAAIJJHUPDBBBFFFFFFFFFFKKBBBAAAADBBMAAA.........",
    "...........AAAGFDDBBBBBBAAAJHHPDBBBBKKKKKKKKKKKKZBBBNACDBBBMAAAA.......",
    "..........AAAAFDBBBBBBBBAAAAHHPDBBBKEREEEEEEEREEKZBBNACDBBBBBCAAA......",
    ".........AAAADDBBBBBBBBBDAAOHPPBBFKERRREEEEEERRREKDBBCANBBBBBBCAAA.....",
    "........AAAAADDBBBBBBBBDDAAOHPPBBFKEEEEEEEEEEEREEKDBBTANDBBBBPOAAA.....",
    ".......AAAAIIIJJBBBBBBBDDAAOHPPBBFKEEEEEEEEEEEEEEKDBBTANDDBBPJJOAAA....",
    ".......AAAJJIJJHJBBBBBBDAAAJJPPBBDKEEEEEEEEEEEEEEKDBBTANDDDBHHHJAAA....",
    "......AAAAJJJHHHHJHBBDDFAAAJJPPBBDKEEEEEEEEEEEEEEKDBBTANFFHHHHHJJAA....",
    "......AAAIIJJHHHHHHJFDFLAAAJJHPBBBKKEEEEEEEEEEEEKKBBBTAAFFIHHHHJJGAA...",
    "......AAAIIJHHHHHHHHJFLAAAIJJHPPBBZKKEEEEEEEEEKKKFBBFAAAIIJHHHHJJGAA...",
    "......AAAIIJHHHHHHHJIIAAAIIJJJPPBBBZKKKKKKKKKKKKFBBDFAACIIJHHHJJJGAA...",
    ".......AAAIIJHHHHHHJIIAAIIIJJJPPDDBBDFFFFFFFFFFDBBDFAACIIIJJHJJIAAA....",
    ".......AAGOIIJJJJJJIIAAGIIIIJJJPPFFDDDDDDDDDFFDDDBBAAAAAIIIIJJIAAAA....",
    "........AAGOIIIIIIIICAAGAGGGAAAAUPPPPPPPPPPPLLLDDAAAAAAAAIIIIIAAAA.....",
    "........AAAAOIOOOIICAAAAAAAAAAAAAUUUUUUUUUUUUUUAAAAAAAAAAAAAAAAAAA.....",
    ".........AAAAASSSAAAAAAAAALLLLAAAGUUUUUUUUUUCCAAAAAANAAAGAAAAAAA.......",
    "..........AAAAAAAAAAAAAAFDDBBBBAAGAAAAAAAAAAAAAAADDFFNAAGAAAAA.........",
    ".............AAAAAAAAAFFDDBBBBBBDAGAAAAAAAAAAAFDBBBBBFNAAA.............",
    "..................AAAAFDDDBBBBBBBDAAAAMMAAAAFFDBBBBBBBDAAA.............",
    ".................AAAADDBBBBBBBBBBBAAAAMMAAAFFDDBBBBBBBDAAA.............",
    ".................AAAADDBBBBBBBBBBBBAAATAAAAFFBBBBBBBBBBAAAA............",
    ".................AA..DDBBBBBBBBBBBBAAATAAAFFFBDDBBBBBPPJIAA............",
    ".................AA......HPPPPPPHH..AATAAA......BBHHHHHJIAA............",
    ".................AA......HHHHHHHHH..AATAAA........HHHHHIAAA............",
    ".................AAA.....HHHHHHHH..AAATAAA......HHHHHH.AAAA............",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (71, 84)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 71x84).
    scale=int   -> sprite de 71x84 px ampliado por un entero, sin márgenes.
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
