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
    "A": (252, 219, 115),
    "B": (252, 217, 111),
    "C": (22, 15, 13),
    "D": (248, 180, 57),
    "E": (157, 69, 58),
    "F": (252, 236, 197),
    "G": (102, 41, 34),
    "H": (250, 198, 80),
    "I": (167, 85, 62),
    "J": (183, 103, 66),
    "K": (41, 25, 19),
    "L": (58, 38, 24),
    "M": (108, 84, 43),
    "N": (73, 38, 28),
    "O": (208, 151, 52),
    "P": (155, 133, 75),
    "Q": (221, 191, 106),
    "R": (194, 154, 98),
    "S": (247, 224, 161),
    "T": (79, 61, 35),
    "U": (155, 112, 39),
    "V": (117, 56, 43),
    "W": (130, 109, 64),
    "X": (139, 67, 51),
    "Y": (207, 188, 157),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...............................................CCCCC........................................",
    "..............................................CCNNNLC.......................................",
    "..............................................CGEEEVLC......................................",
    "..............................................CGEEEEVC......................................",
    "........................................CCCCCCCGEEEEVC......................................",
    ".....................................CCCKKCCCCCGEEXKKC......................................",
    "....................................CCCEEEEEEEGVEXXCCC......................................",
    ".................................CCCCEEEEEEEEEGVEECCCCCCC...................................",
    "...............................CCCVVJJJJEEEEEEEEEECCCXXXCCCCC...............................",
    ".............................CCNNJJJJRRRIEEEEEEEENNNEEEEKKKKKC..............................",
    ".............................CCEEEJRRRRRIEEEEEEEEEEEEEEEEEEEGKC.............................",
    "............................CCXEERRRRREEEEEEEEEEEEEEEEEEEEEEGGKC............................",
    "...........................CCXEEERRRJJEEEEEEEEEEEEEEEEEEEEEEVGGCC...........................",
    "...........................CCXEEIRREEEEEEEEEEEEEEEEEEEEEEEEEVGGGCC..........................",
    "...........................CCXEEIJJEEEEEEEEEEEEEEEEEEEEEEEXXGGGGLC..........................",
    "........................CCCCCVVEEEEEEEEEEEEEEEEEEEEEEEEEEEGGGGGGLC..........................",
    "........................CCCCCGGXXEEEEEEEEEEEEEEEEEEEEEVVVVGGGGGGLC..........................",
    "....................CCCCCRRRCKGGGEEEEEEEEEEEEEEEEEEEEEGGGGGGGGGGLC..........................",
    "...................CCTTTRAAHHCKGGGGGGGGGEEEEEEEEEEGGGGGGGGGGGGGLCCCC........................",
    "...................CCAAAAAHHHOKKKGNGGGGGGGGGGGGGGGGGGGGGGGGGGGNCCCCCC.......................",
    "................CCCCAAAABBHHHHOTTTNNGGGGGGGGGGGGGGGGGGGGGGGGNNNCCRRRTCC.....................",
    "................CCCAAAAAHHHHHHSSAATCCCCGGGGGGGGGGGGGGGGGGGGKCCCCAAAATCC.....................",
    "..............CCCAAAAABHHHHHFFFFSAAAWWKKKKKKKKKKKKKKKKKKKKKKWWAAAAAAAACCC...................",
    "..........CCCLCCAAAAAABHHHHFFFFFSAAAAAAKKKKKKCCCCCCCCCCCKKKAAAAAAAAAAAACC...................",
    ".........CLLLAAAAAAAABHHAAFFFFFAAAAAAAAAAAAAAPPPPPPPPPPPAAAAAAAAAAAAAAAACC..................",
    "......CCCLAAAAAAAAAAAHHHFFFFFFFBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCC................",
    ".....CCPPAASSAAAAAAAAHHHFFFAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCC...............",
    ".....CAAAASFFSAAAAAAAPPASSSAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBAAAAAAAAAAARCCC.............",
    "...CCAAAFFFFFSAAAAAAPPPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHDBAAAAAAAAAAAARRCCCC..........",
    "..CCAAFFFFFSAAAAAAACLPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHDBAAAAAAAAAAAAAARKKC..........",
    "..CPAAFFFFFSAAAAAAACLAAAAAAQQQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHDDAAAAAAAAAAAAAAAAAQCCC.......",
    "..CPSFFFFBABAAAAAPPCAAAAAAANNNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHOCMAAAAAAAAAAAAAAAAQWWWCC.....",
    "CLLSSFFSSBBAAAAAATCQAAAAAAANNNNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHOCMAAAAAAAAAAAAAAAAAAAACC.....",
    "CLAAFFFBBBBAAAAAATCQAAAAAATNNNNAAAAAAAAAAAAAAAAAAAAAAAMMAAAAAAQCMAAAAAAAAAAAAAAAAAAAAQQCC...",
    "CLAAAAABBBBAAAAAATQQAAAAAATNNLAAAAASSSFFFFFSSAAAAAAAANNNNQAAAAQCMAAAABAAAAAAAAABAAAAAAAAC...",
    "CLAAAAABABAAAAAPCPAAAAAAAAANNLRASSSFFFYMMMRFFSSSAAAAANNNNQAAAAQUCCRAABAAAAAAAAABAAAAAAAAUCC.",
    "CLAAAAAAAAAAAAAPCPAAAAAAAAAWWRSSFFFFFYNNNNNRFFFFSAAANNNNNQAAAABDUCRAAAAAAAAABBAAAAAAAAAAUCC.",
    "CLAAAAAAAAAAADDUCPAAAAAAAAAAAASFFFFFFYNNNNNFFFFFFFAANNNNNQAAAABDUCRAAAAAAAAAAAAAAAAAAAAADDLC",
    "CKHHBAAAAAAHHDDUCPAAAAAAAAAAASFFFFFFFFYNNNFFFFFFFFSAANNNNAAAAABDUCOHHAAAAAAAAAAAAAAAAAAADDLC",
    "CKDDBAAAAAHDDDMCPAAAAAAAAAAAAFFFFPFFFFFYLYFFFFFFFFFSAQQQAAAAAABDUCODHAAAAAAAAAAAAAAAAAAADDLC",
    "CKDDDDAAAADDDDMCRAAAAAAAAAAAAFFFFPFFFFFWLYFFFFWFFFFSAAAAAAAAAABBDUCDDDDBAAAAAAAAAAAAABHHDDLC",
    "CKMDDDDDDDDDDDMCRAAAAAAAAAABBFFFFRFFYYWTTLYFFFTWFFFSBAAAABABBAABDDCTDDDBBBBBAAAAAAAAABDDDDLC",
    "..CMDDDDDDDDDDMCRAAAAAAAAAABAFFFFFRFYYTTTFFMMTTYFFFSBAAABBABAAABDDCTDDDDDDDHAAABAAHHHDDDDDLC",
    "..CCUUDDDDDDDDCCRAAAAAAAAAAAAAFFFFFFYYFFFFFMMFYFFFFSBBAABBBAAAABDDUUDDDDDDDHBBBBBBHDDDDDDDLC",
    "...CCKDDDDDDDCCCCAAAAAAAAAAAAASFFFFFFFFFFFFFFFFFFFFSBBBAABBAAAAAADDOCMDDDDDDDDDDDDDDDDDDULC.",
    "....CKLLLLLLCC..CTAAAAAAAAAAAAASFFFFFFFFFFFFFFFFFFSBAAAAAAAAAAAAADDOCCMMODDDDDDDDDDDDDDDUCC.",
    "......CCCCCC....CTTAAAAAAAAAAAAAAFFFFFFFFFFFFFFFFABBAAAAAAABBBABDDDOCCCCODDDDDDDDDDDDDDUCC..",
    "..................CAAAAAAAAAAAAAAAAAAFFFFFFFFAAAAAAAAAAAAAAABBABDDDUCC.CLLLDDDDDDDDDDDDCC...",
    "..................CAAAAPMMMMAAAAAAAABAAAAAAAAAAAAAAAAAAAAAABBBHHDDUCC...CCCOOOOOOOOODKKC....",
    "................CKAQAAPPCCCCMMAAAAAABAAAAAABBAAAAAQWWWWWABAABBDDDDUCC......CCCCCCCCCCCC.....",
    "................CKAAQPPPAAAAMMAQQAAABAAAAAAAAAAAQQQKKKKKPPBBABHHDDUCC......CCCCCCCCC........",
    "..............CCCAAAAPQAAAAAAAWMMAAAAAAAAAAAAAAAPQQAAAAAPLPBBBBBHDDULC......................",
    "..............CCRAAAPQAAAAAAAAWMMQAAAAAAAAAAAAQMMPPAABBBBPLLBBBBHHDDLC......................",
    "..............CCRAAAAAAAAAAAAAAATCQAAAABAAAAAQRMMAAAABBBBBPWLBBBBHHDML......................",
    ".............CTAAAAAAAAAAAAAAAAATCQAAAABAAAAAWCRAAAABBBBBBBBWBBBBBHDDMC.....................",
    ".............CTAAAHHAAAAAAAAJJJJLCQAAAAABAAAAWCRAAABBBBBBBBBBBBBBBHDDMC.....................",
    ".............CTAAAHDAAAAAAQQJJJJLCQAAAAAAAAAAWCXJJJRBBBBBBBBBBBBBBHHDMC.....................",
    "............CTPAAAHDDBAAARJJJJJJLCQAAAAAAAAABWCXJJJJRRBBBBDHHBBBBBBHDOOCC...................",
    "............CPAAAAHOCCBQQRJJJJJJCCQAAAAABABBAWCXJJJJJJQQBBDDDBBBBBBHDDDCC...................",
    "............CCAAAAHOCUQJJJJJJJICTQAAAABBBBBBAACCXJJJJJJJDDDMDBBBBBBHDDDCC...................",
    "............CCAAAAABUCXXJJJJJJICTAAAAABBBBBBAARCCJJJJJJJOOMMDBBBBBBBBDDCC...................",
    "..........CCCAAAAAABBCCXJJJJJLLLAAAABABAAAAAAARCCCJJJJJJLOMOBBBBBBBBBDDMC...................",
    "..........CCAAAAAAAAAAACCCCCCLLAAAAAABBAAAAABBBRCCCVVVVVLLOBBBBBBBBBBDDDMCCCCC..............",
    "..........CCBAAAAAAAAAAATTTTTAAAABABAAAAAAAABBBBRCCCCCCCPBBBBBBBBBBBBDDDMCCCWCC.............",
    "..........CCBAAAABBAAAABAAAAAAAABABBABBBAAAAAABAABBPPPPPBBBBBBBBBBBBBDDDMCQAAWKK............",
    "..........CCBAAABBBBBBBAAAAAAAABBBBBBBBBABABBBBBBBBBBBBBBBBBBBBBBBBHHDDDMCQAAAAMC...........",
    "..........CCBAAABAABBBBBBBAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDMCQAAAAMC...........",
    "..........CCBBBBAAABBBBBBBAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDMCQAAAAMC...........",
    "..........CCDDDBAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDMCQAAAAMC...........",
    "..........CCUDDBAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDHDDDDMCQABBBMC...........",
    "............CUDBAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBDDDDDDDDTTQADDCCC...........",
    "............CUDHHHBABBBBBBBBBBBBBBBBBBBBBBABBBBBBBBBBBBBBBBBBBBBDDDDDDDLLHHHDUCC............",
    "............CUDDDHBBBABBBBBBBBBBBBBBBBBBBBABBBBBBBBBBBBBBBBBBBBBDDDDDDDLLDDDDUC.............",
    "............CUDDDHBAABABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDDDDDDLLDDDMMC.............",
    "............CLDDDHBAABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDDDDDDCLOOCCC..............",
    ".............CLDDHBBBABBBBBABBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBHDDDDDDDMCCCCCC................",
    ".............CLDDDDDHBBBBAAAABBBBBBBBABBBBBBBBBBBBBBBBBBBBHDDDDDDDDDDMCCCCC.................",
    "...............CMDDDDHHHHHHBAAAABBBAAABBBBBBBBBBBBBBHHHHHHHDDDDDDDDDDCC.....................",
    "...............CMDDDDDDDDDHBAAABBBBBAABBBABBBBBBBBBBDDDDDDDDDDDDDDDDCC......................",
    ".................MMDDDDDDDDDDDDBBBBBAABBAABBBBBBBDDDDDDDDDDDDDDDDODCC.......................",
    ".................CMOOODDDDDDDDDDHHHHHAABAABAAAABDDDDDDDDDDDDDDDOOOCC........................",
    "..................CCCCODDDDDDDDDDDDDDHHHHHHHHHHHDDDDDDDDDDDDDDDKCC..........................",
    "....................CCOOOODDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDOOOOKCC..........................",
    "....................CCEIIIODDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDJIIIICC...........................",
    "....................CCEIIIIIIIIIDDDOOOOOOOOOOOODDDDOJJJJJJIIIIICC...........................",
    "...................CNIIIIIIIIIIIEECCCCCCCCCCCCCMMDOJIIIIIIIIIIICC...........................",
    "...................CNIIIIIIIIIIIEECCCCCCCCCCCCCCCCIIIIIIIIIIIICCC...........................",
    "...................CNIIIIIIIIIIIEKCC...........CCVIIIIIIIIIIIVCCC...........................",
    "...................CCVIIIIIIIIXVKKCC...........CCCVIIIIIIIIIVCC.............................",
    "....................CCVIIIIIIXVCCC...............CCVIIIIIIICCCC.............................",
    ".....................CCCCCCCCCCCC................CCCCCCCCCCCCC..............................",
    "......................CCCCCCCCCC...................CCCCCCCCCC...............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (92, 92)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 92x92).
    scale=int   -> sprite de 92x92 px ampliado por un entero, sin márgenes.
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
