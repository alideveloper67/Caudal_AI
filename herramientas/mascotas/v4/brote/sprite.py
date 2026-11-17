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
    "A": (252, 184, 191),
    "B": (3, 2, 1),
    "C": (249, 160, 175),
    "D": (232, 64, 79),
    "E": (249, 81, 80),
    "F": (214, 52, 75),
    "G": (14, 8, 6),
    "H": (245, 131, 157),
    "I": (249, 200, 207),
    "J": (248, 111, 129),
    "K": (150, 202, 20),
    "L": (99, 169, 8),
    "M": (74, 143, 6),
    "N": (125, 186, 12),
    "O": (64, 40, 44),
    "P": (167, 106, 118),
    "Q": (173, 219, 31),
    "R": (105, 25, 32),
    "S": (111, 68, 76),
    "T": (48, 75, 9),
    "U": (32, 25, 18),
    "V": (171, 40, 54),
    "W": (55, 9, 11),
    "X": (200, 144, 153),
    "Y": (202, 238, 46),
    "Z": (152, 134, 138),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................................BBBBBBBBBB..............................",
    "............................................BBBBGGGGGBBBB.............................",
    ".....................BBBBBBBB.............BBBBBTTTTTTBBBBB............................",
    ".................BBBBBBBBBBBBBBB.........BBBBBQQQQQQQNNTBBB...........................",
    "...............BBBBBGGTTTTTTBBBBBB......BBBTKKKQQQKKNNNTBB............................",
    "..............BBBBBBQQQQKKKKKKBBBBBB...BBBTKNNKKKQNNNKKBBB............................",
    ".............BBBBBBYYQQQKKKKKKKKKBBBB..BBTKKNNKNNKKKKKKBBB............................",
    "............BBBBQQQQQQQKKKKKKKNKKKBBBBBBBKNNNLMLKKKKKKBBB.............................",
    "............BBBQQKKKKKKLLLLLNNNNKKKGBBBBBKNNLMLKKKKKKKBBB.............................",
    "............BBBBKKKKKKKKKNNLMMMLLKKNGBBBMLLLMNNLLLLLLTBB..............................",
    "............BBBUMNKQQQQKKKQQNMMMMLLNMBBBMMMMLNNNLLLMTBBB..............................",
    ".............BBBUMNNQQKKKQQKKNNLMMMMMBBBTMTLNNLLLMMGBBB...............................",
    "..............BBBGMLNNNNKKKKKNNNLLMMMMBBGTMLLLLLMMGBBB................................",
    "...............BBBGBLLNNNKKKNLLLLLMMMMMTBGMMMMMBGBBBB.................................",
    "................BBBBBMMLLNNNLMLLLLMMUUTMTGGGBBBBGBUO..................................",
    ".................BBBBBBTTLLLMMMLLBBBBBBMTBBBBBBBBOOU..................................",
    "...................BBBBBBGGBBBBBBBBUBBBTMGBBBBBBGGBBBBB...............................",
    ".....................BBBBBBBBBBBBBBUUBBBGBGGBBBBBGGBBBBGGG............................",
    ".........................BBBUUGBBBBBBBBSSSIXXXXXXXIOOOBGGBBB..........................",
    "............................BGGBBGGBBBAAAIIIIIAAAIIIIAZZGBGGBBB.......................",
    "...........................BBBGBBBAAAAAAIIIIAAAAAAAAAIIIAIIBBGBB......................",
    ".........................BBBBGBBBAAAAAAAAAAAAAAAAAAAAAAAIIAAABGBBB....................",
    "........................BBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIIGGBB...................",
    ".......................BBBUBCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIIIIBBB..................",
    "......................BBBUCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIIIIBBBB.................",
    ".....................BBBSCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIICBBBB................",
    "....................BBBSHCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACBBBB...............",
    "...................BBBSHCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCCBGGG..............",
    "..................BBBSCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCAAUGBB.............",
    ".................BBBBCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAUBB.............",
    ".................BBBCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBBBBBB........",
    "................BBBCCCCCAAAAAAAAAAAAAAAAAAASSAAAAAAAAAAAAAAAAAAAAAAAAAABBBBGGGBBB.....",
    "................BBBCCCCAAAAAAAAAAAAAAAAAAABBBAAAAAAAAAAAAAAXGAASAAAAAAABBBBUUUBBBB....",
    "...............BBBCCCCCAAAAAAAAAAAAAAAAAAGGIIOAAAAAAAAAAAAAXBGSBBBAAAAACBBBIIIIOBBB...",
    "...............BBBCCCCCAAAAAAAAAAAAAAAAAABGIOOBAAAAAAAAAAAAXBBBBBBXAAACAAGGIIIIIOBBB..",
    "..............BBBBHCCCAAAAAAAAAAAAAAAAAIGBBOOBBPAAAAAAAAAAAXBBBBBBXCCAAAAGGIIIIIIBBBB.",
    "...........BBBBBOHHCCCAAAAAAAAAAAAAAAAAIGBBBBBBPAAAAAAAAAAAABBBBBBXCCAAAAGGGAAAAAABBB.",
    "........BBBBGGBBOHHCCCAAAAAAAAAAAAAAAAAIGBBBBBBPAAAAAIAACCAIIBBBBBCCCCAAAAGBAAAAAABBB.",
    "......BBBBBBGGGGBBSHCAAAAAAAAAAAAAAAAAAIIBBBBBBAAAAIIIICCCAIIBBBBPAACJJAAABBBCAAAABBBB",
    ".....BBBBBBIIIIIIISSCCAAAAAAAAAAAAAAAAAAABBBBBBXAAAIIAAACAIIIAPPPAAJJJJJAABBGCAAACHOBG",
    "....BBBBBIIIIIIIIIAACAAAAAAAAAAAAAACCCAAAABBBBXCAAAIAAAAAIIIIAAAAAJJJJJJJCCGBPAACHHOBG",
    "...BBBBBAIIIIIAAAAAAAAAAAAAAAAAAAHJJJJJAAAAOOXACAAAIIAAAAIIIIAAAAAJJJJJJJHCUBPAAAHHOBG",
    "..BBBBBAAAAAAAAAAAAAAAAAAAAAAAAAHJJJJJJJJAAAAAAAAOOIIBBAAWIIIAAAAAHJJJJJHCAUGSAACHHOBG",
    ".BBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAHJJJJJJJJJAAAAAAAOGBBBBWWWWIBAAAAAAHJJJHAAAPGSCCHHSBBB",
    ".BBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAJJJJJJJJJJAAAAAAAOBGRRRWWWWWBAAAAAAACCCAAAAPGGCCHHSBB.",
    ".BBSCAAAAAAAAAAAAAAAAAAAAAAAAAAAAJJJJJJJJHAAAAAAAABRVVVVRWWWBAAAAAAAAAAAAAAPGGHHHHBBB.",
    "BBBSCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJJJJJJHAAAAAAAAAARVVFFVRWGAAAAAAAAAAAAAAAPBGHHHBBB..",
    "GBOCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJJJJAAAAAAAAAAAARDDEEEEGAAAAAAAAAAAAAAAAPBGHHSBBB..",
    "GBOCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAARDEEEEEAAAAAAAAAAAAAAAAPBGHSBBB...",
    "GBOCCAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAGREEEEEAAAAAAAAAAAAAAACPBGBBBB....",
    "GBOCCCAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAAAAGROOEAAAAAAAAAAAAAAAACPBBBBB.....",
    "GBOCCCCAAAAAAAAAAAAAAAACCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOOOAAAAAAAAAAAAAAAAACBBBBB......",
    ".BBBHCCCAAAAAAAAAAAAACCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB........",
    ".BBBHHCCCAAAAAAAAACCCCCHHAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB........",
    ".BBBBHHCCCCCAAACCCCCCCCPCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB.........",
    "..BBBBHHHCCCCCCCCCCCHHPPCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB.........",
    "...BBBPHHHHCCCCCHHHHHPPCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB.........",
    "...BBBBPHHHHHHHHHHHHHUHHCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB..........",
    "....BBBBBPPHHHHHHHHUUHHHCCCCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB..........",
    ".....BBBBBBSSSSSBBBPPHHHHCCCBUUUUUBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCBBB...........",
    ".......BBBBBBBBBGBPPJHHHHGGBBBBBBBBBBBIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACCSGB............",
    ".........BBBBBBGGGPJJJHHGGGGBSSSSBGGBBGIAAAAAAAAAAAAAAAAAAAAAAAAAAACCHSGBB............",
    "................GBOJJPBBGGGEEEEEEEEEEGGGAAAAAAAAAAAAAAAAAAAAAAAAAACCHPBBBBG...........",
    "................BBBOPBBGGJJJEEEEEEEEEEGGGAAAAAAAAAAAAAAAAAAAAAAAACCHPGBRRGBB..........",
    ".................BBBBBBEEJEEEEEEEEEEEEEWBBAAAAAAAAAAAAAAAAAAAAACCCHPGBWRDRBBB.........",
    "..................BBBBVEEEEEEEEEEEEEEEEEWBBAAAAAAAAAAAAAAAAAACCCHHBGBWDDEEBBB.........",
    "..................BBBVEEEEEEEEEEEEEEEEEEBBBBCAAAAAAAAAAAACCCCCCHHBBBWFDEEEEBBB........",
    "..................BBBEEEEEEEEEDDDEEEEEEEEBBBCCCCCCCCCCCCCCCCCHHHBBGFFFEEEEEGBB........",
    ".................BBBVEEEEEEEDDDDDDDEEEEEEBBBCCCCCCCCCCCCCHHHHHHBBGVFFEEEEEEGBB........",
    ".................BBBVEEEEEDDDDDDDDDDDEEEEDBGHHHCCCCHHHHHHHHHHHBBBVFFDEEEEEEGBB........",
    ".................BBRDEEEEEDDDDDDDDDDDDEEEDBGHJJHHHHJJJJJHHHGGBBBFFDDDDEEEEEBBB........",
    ".................BBRDEEEDDDDDDDDDDDDDDDEEDBGJJJHHHJJJJPPBBBBFFFFFDDDDDDEEEBBB.........",
    ".................BBRDEEEDDDDDDDDDDDDDDDEEDBGJJJJJJJOOOBBBBBFFFFDDDDDDDDEEBBBB.........",
    ".................BBRDEEDDDDDDDDDDDDDDDDEEBBBGGGGGGGBBBBRRFFFFDDDDDDDDDDDBBBB..........",
    ".................BBRDDEDDDDFFDFFFDDDDDDDDBBBGGGBBGGGBVVFFFFDDDDDDDDDDDDDRBBB..........",
    ".................BBBDDDDDFFFFFFFFFFDDDDDFBBB..GBBBVVVFFFFFDDDDDDDDDDDFFRBBB...........",
    ".................BBBBDFFFFFFFFFFFFFFFFFFBBB....BBBVVFFFFFFFFDDDDDDDFFFGBBB............",
    "..................BBBVFFFFFFFFFFFFFFFFFVBBB.....BBBBVFFFFFFFFFFFFFDFFGBBB.............",
    "...................BBBVFFFFFFFFFFFFFFFVGBB......BBBBBVFFFFFFFFFFFFFBBBBB..............",
    "...................BBBBBFFFFFFFFFFFFFFGBBB.......BBBBGGFRRRRRRRFFBBBBB................",
    "....................BBBBBFFFFFFFFFFFBBBBB..........BBBBBBBBBBBBBBBBBB.................",
    ".....................BBBBBBBRRRRRBBBBBBB.............BBBBBBBBBBBBB....................",
    ".......................BBBBBBBBBBBBBBB................................................",
    ".........................BBBBBBBBBBB..................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (86, 84)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 86x84).
    scale=int   -> sprite de 86x84 px ampliado por un entero, sin márgenes.
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
