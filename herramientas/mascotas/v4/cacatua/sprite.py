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
    "A": (253, 217, 81),
    "B": (5, 4, 2),
    "C": (251, 245, 241),
    "D": (240, 228, 228),
    "E": (208, 189, 203),
    "F": (252, 208, 58),
    "G": (250, 188, 29),
    "H": (251, 116, 51),
    "I": (177, 155, 174),
    "J": (221, 205, 215),
    "K": (195, 175, 189),
    "L": (37, 26, 14),
    "M": (234, 156, 13),
    "N": (96, 66, 17),
    "O": (53, 47, 51),
    "P": (87, 78, 86),
    "Q": (238, 188, 74),
    "R": (251, 232, 154),
    "S": (238, 102, 87),
    "T": (157, 142, 155),
    "U": (123, 110, 121),
    "V": (185, 157, 59),
    "W": (155, 106, 30),
    "X": (189, 111, 7),
    "Y": (160, 60, 46),
    "Z": (244, 151, 135),
    "a": (204, 72, 60),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "....................................BBB..........................................",
    "..................................BBBBBBB........................................",
    "..................................BBBBBBBB.......................................",
    "..................................BBBBWBBBB......................................",
    ".................................BBBGAAWBBBB.....................................",
    ".................................BBNGAAAWBBBB....................................",
    ".................................BBNGAARAWBBBB...................................",
    ".................................BBNGFAARAVLBBB..................................",
    ".................................BBNGFAAAAAVLBBB.................................",
    ".......................BB........BBNGGFFAAAAALBBBB...............................",
    ".....................BBBBBB......BBBGGGFAAAAAABBBBB..............................",
    ".....................BBBBBBBBBB..BBBBGGFAAAAAAABBBBBB............................",
    "....................BBBBBBBBBBBBBLLBBGGGAAAAAAAABBBBBBB..........................",
    "....................BBLFAAANNBBBBBBBBBGGFAAAAAAFFABBBBBBB........................",
    "....................BBLFFAARRVVBBBBBBBMGGFAAAAAFFAAABBBBBB.......................",
    "....................BBBBGFAAAAAAAALLBBNMGGGFFAAFFAAAAABBBBBBB....................",
    ".....................BBBBGFAAAAAAAAAANNNMGGGFAAAAAAAAAAFBBBBBBB..................",
    ".....................BBBBGGFFFFFAAAAAFFFMMGGGFAAAFFFFFFFFABBBBBB.................",
    "......................BBBWGGFFFFFAAAAAFFFFFFFFFFFFFAAAAAAAAABBBBB................",
    ".......................BBBWMGFFFFFFFFFFFFFFFGGFAAAAAAAAAAAAAABBBBBB..............",
    ".......................BBBBBMGGFFFFFFFFFFGGFFAAAAAAAAAAAAAAAAAABBBBBB............",
    "......................BBBBBBLLGGGGGGGGGGGFAAAAAAAAAAAAAAAAAAAAAAABBBBB...........",
    ".....................BBBBBBBBLLMMGGGGGGFAAAAAAAAAAAAAAAAAAAAAAAAAABBBBB..........",
    "....................BBBNNBGBFFFGGFGGMGFAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBB.........",
    "....................BBBMGGFAAAAAAFGMGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVBBB.........",
    "....................BBBNMMGFAAAAGGGGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVBBB........",
    ".....................BBBNMMMGGGMGGGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANBBB.......",
    "......................BBBBMMMMNNMGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANBBB......",
    ".......................BBBBBNNNXGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBB......",
    "........................BBBBBBXGFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBB.....",
    "..........................BBBBGFFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALAAAABBB.....",
    "..........................BBBGGFAAAAAAAAAAAAAAABBBAAAAAAAAAAAAAAAAALLAAAABBBB....",
    "..........................BBGGGFAAAAAAAAAAAAAABBBBBAAAAAAAAAAAAAAQLLBBBAAQBBB....",
    ".........................BBBGGFAAAAAAAAAAAAAABBBBBBBAAAAAAAAAAAAAQBBBBBWAQBBBB...",
    ".........................BBBGFFAAAAAAAAAAAAAABBBBBBBQAAAAAAAAAAAAQBBBBBWAAVBBB...",
    "........................BBBMGFFAAAAAAAAAAAAAALBBBBBBQAAAAAAALLLAAQBBBBBWAAVBBBB..",
    "........................BBBMFFFAAAAAAAAAQQQAALBBBBBBAAAAAAALYYYBVQVBBBBBQQQWBBB..",
    "........................BBWGFFAAAAAAAAQHHHHHABBBBBBBAAAAALSSZZSYBVAABBBQHHHWBBB..",
    ".......................BBBWGFFAAAAAAAQHHHHHHHHBBBBBAAAAAALSSZZSSSNAAVVQHHHHHLBB..",
    ".......................BBNGFFFAAAAAAAHHHHHHHHHABBBAAAAAAALSSSSSSNNAAAAHHHHHHLBB..",
    ".......................BBNGFFFAAAAAAQHHHHHHHHHHAAAAAAAAAALaSSSSSNNAAAAHHHHHHLBB..",
    "......................BBBNGFFFAAAAAAQHHHHHHHHHHAAAAAAAAAALLaSSSYNNAAAAAHHHHHLBB..",
    "......................BBBGGFFAAAAAAAAHHHHHHHHHHAAAAAAAAAAALLSSYNNAAAAAAAHHHHLBB..",
    "......................BBBGGFFAAAAAAAAHHHHHHHHHAAAAAAAAAAAAAABBBNAAAAAAAAAAFWBBB..",
    "......................BBLGGGARRAAAAAAAHHHHHHHHAAAAAAAAAAAAAAVVVAAAAAAAAAAAFWBBB..",
    ".....................BBBLGCCCCCCDDAAAAAAHHHHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBB...",
    "....................BBBLCCCCCCCCCCCCRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBB...",
    "...................BBBLCCCCCCCCCCCCCCRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBB...",
    "..................BBBBCCCCCCCCCCCCCCCCRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBBBBBB..",
    ".................BBBBCCCCCCCCCCCCCCCCCCDQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBBBOBBB..",
    ".................BBBCCCCCCCCCCCCCCCCCCCDQQAAAAAAAAAAAAAAAAAAAAAAAAAAAAFBLBOBBBBB.",
    "................BBBTCCCCCCCCCCCCCCCCCCCCQQAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBLEEJBBB.",
    "...............BBBTCCCCCCCCCCCCCCCCCCCCCDKKDRRRAAAAAAAAAAAAAAAAAAAAAARABBBEEJBBB.",
    "...............BBBCCCCCCCCCCCCCCCCCCCCCCDKKDCCCRADCRAAARRAAAAAAACAAARCCBBOBJJBBBB",
    "..............BBBCCCCCCCCCCCCCCCCCCCCCCCDKICCCCCDCCCRAACCRAAAAACCCARCCCCOBUJJEPBB",
    ".............BBBCCCCCCCCCCCCCCCCCCCCCCCCDKIKCCCCCCCCCRRCCCAAAACCCCCCCCCDOBUJJEPBB",
    "............BBBBCCCCCCCCCCCCCCCCCCCCCCCDDKTKCCCCCCCCCCCCCCCRRCCCCCCCCCCDOBPJJEPBB",
    "...........BBBBECCCCCCCCCCCCCCCCCCCCCCCDDTKKCCCCCCCCCCCCCCCCCCCCCCCCCCCDLBPJJKPBB",
    "...........BBBEEECCCCDDCCCCCCCCCCCCCCCCDDTBKCCCCCCCCCCCCCCCCCCCCCCCCCCCDLBPPKIBBB",
    "..........BBBEEKKEJJEECCCCCCCCCCCCCCCCDJKBBCCCCCCCCCCCCCCCCCCCCCCCCCCCDDLBPKIUBBB",
    ".........BBBPEEEEJJEEECCCCCCCDDCCCCCCDJKBBBDCCCCCCCCCCCCCCCCCCCCCCCCCCDDBBPKIUBB.",
    "........BBBPJJJJJJEKEEECCCCCDJDCCCDCDJKIOBBDCCCCCCCCCCCCCCCCCCCCCCCCCCDPBBIIIBBB.",
    ".......BBBBBJJEEJEKKEEEEDDDKEJDCCDDDJKIBBOBCCCCCCCCCCCCCCCCCCCCCCCCCCCPPBBKKBBBB.",
    ".....BBBBBEEEJEEEKKEEEEEEEKIKEDDDEEEKIIBBBDCCCCCCCCCCCCCCCCCCCCCCCCCCDPBBTIIBBB..",
    ".....BBBBEEEEEKKIKEEEEEEEKIKEEEEEEEKKIOBBBDCCCCCCCCCCCCCCCCCCCCCCCCCCDBBBTIPBBB..",
    "....BBBBBEEIIIIIKEEEEEEKIIKEEEEEEEIIKOBLBJCCCCCCCCCCCCCCCCCCCCCCCCCCDDBBBIPBBB...",
    ".....BBBBIIIIIIKKKKKKKKIIKEKKKKKIIIIBBLBJDCCCCCCCCCCCCCCCCCCCCCCCCCDDDBBIUBBBB...",
    ".....BBBBBBIIIIIIIKKIIIKEEEKIIIIIIIBBBBEJDDCCCCCCCCCCCCCCCCCCCCCCCDDDBBBUBBB.....",
    ".....BBBBBBBLBUUIIIIIIKEEEIIIIIIIOBBBBEJDDDDCCCCCCCCCCCCCCCCCCCCCDDJBBBBBBBB.....",
    "...BBBBBBBBLBBBBBPPPIIIIIIIUUUBBBBOBEJJDDDDDDCCCCCCCCCCCCCCCCCCCDDJUBBBBBBB......",
    "..BBBBBDDKKKKBBBBBBBOOOOOOBBBBBLLEEEEJDDDDDDDDDCCCCCCCCCCCCCCDDCDJUBBBBBB........",
    ".BBBBBDDDJKKKKKIBOOOBBBBBBBBPPPEEEEEJDDDDDDDDDDDDDCCCCCCCCCDDDDDJBBBBBB..........",
    "BBBBBDDDDJJEEKKIITTTUUPPOBBBBKEEEEEEJDDDDDDDDDDDDDDDDDCCDDDDDJJEBBBBB............",
    "BBLJJJJJJJEEEEKIIIITTPPOBBBBBBKEKEEEEJDDDDDDDDDDDDDDDDDDDDDDJJEBBBBB.............",
    "BBLLKKKKKKKKIIIIITTTPBBBBBBBBBBBBKEEEEJJJJJDDDDDJJJDDDJJJJJDBBBBBBB..............",
    "BBBBBIIIIIIIIIITTOOBBBBBB..BBBBBBBBEEEJEEEEJJJJJJJJJJJJJJJJBBBBBB................",
    ".BBBBBBUUUUUUBLLLBBBBBB.......BBBBBBOOOBTTEEJJJJJJJJTTBBLLBBLLBBB................",
    "..BBBBBBBBBBBBBBBBBBB..........BBBNNBBBBBBBOOOOOOOOOBBBBBBLMXXLBBB...............",
    "....BBBBBBBBBBBBBB.............BBLMMXXXBBBBBBBBBBBBBBBLLBBMMMMXBBB...............",
    "......BB...B...................BBBLMMMMMMMXXXBBBBBBBBBMMMMMMMMLBBB...............",
    "................................BBBLMMMMGGMBBBBBBBBBBBBBBNNBLLBBB................",
    ".................................BBBBBBBBBBBBBBB...BBBBBBBBBBBBB.................",
    "..................................BBBBBBBBBBBBB......BBBBBBBBBB..................",
    ".....................................BBLLLLL.....................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (81, 84)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 81x84).
    scale=int   -> sprite de 81x84 px ampliado por un entero, sin márgenes.
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
