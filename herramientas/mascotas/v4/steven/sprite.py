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
    "A": (252, 171, 135),
    "B": (236, 53, 78),
    "C": (33, 110, 171),
    "D": (59, 15, 15),
    "E": (26, 6, 7),
    "F": (78, 31, 28),
    "G": (109, 37, 35),
    "H": (20, 65, 109),
    "I": (131, 57, 49),
    "J": (181, 43, 60),
    "K": (42, 91, 131),
    "L": (232, 149, 120),
    "M": (253, 210, 40),
    "N": (137, 35, 42),
    "O": (26, 49, 71),
    "P": (237, 109, 96),
    "Q": (187, 123, 101),
    "R": (89, 70, 65),
    "S": (16, 26, 39),
    "T": (147, 96, 80),
    "U": (137, 178, 213),
    "V": (248, 247, 247),
    "W": (243, 220, 208),
    "X": (110, 140, 168),
    "Y": (249, 188, 172),
    "Z": (183, 195, 208),
    "a": (248, 166, 53),
    "b": (162, 168, 175),
    "c": (121, 120, 124),
    "d": (251, 224, 142),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".............................GGGGGGG............",
    "....................IJJJJ...GDDGFDEDG...........",
    "..................GIFEEEEGFFDDDDNGGDEG..........",
    ".................GFEGQQNFDDDDGFDDDFFFEN.........",
    "................GDFWWQQNGGFNFDDDDDDDFFD.........",
    "................GFYYDDDDDGGFDDDDDDDDDFEG........",
    "...............GDGGGDDDDDDDDDDDDDDDDDDEG........",
    "...............GDNDDDDDDDDDDDDDDDFGGFDEGGN......",
    ".............GGFDFDDDDDDEEEDDDDDGJJNGFEEEDG.....",
    "...........FGDFFDDDDDEDFRRFDEEDDDDDFGGGNNFEF....",
    "...........DFLLGDDDEDDAAAFFDDFEDDDDDFGGGNNGEG...",
    "..........GDFFDDDEDFDDAAADDDDDDDDDDDDFGGGNGFDG..",
    "..........GGFFDDDDDEDDAAARTTREQQEDDDDDDFDGNFEG..",
    ".........JENFDDDEDFDLLAAATRRRRAAEEDDDDDDDDGFEN..",
    ".........JEGDDDDRQDRRLAAAARRRRAAAEDDDDDDDDDDEN..",
    ".........JEFDDDEQRbbRRAAAVRSZRAAADEDDDDDDDDDEN..",
    ".........GFEEDDDQVVRSSARVVOSZZRAAADDDDDDDDDDDG..",
    "..........GEEEERRVVOSOARVVVOVZRAAAEDDDDDDDDEF...",
    "...........FEEEQRVVVROTRVVVVVVQAAEDEEEEDDDEEG...",
    "...........NFEEQRVVVRFATVVVVVRAQDDEEEEEEDDDEFN..",
    "............NEDTTVVVFFAAAcccRAADDEEEEEEEEDDDEG..",
    "...........GDDAAATFFFAAAAAQQYWADDEEFTTEEEEDDDEJ.",
    "..........NDDWWWAAAAAAAAAAQAWYAFEEFAAAEEEEEDDEJ.",
    "..........NFWWWAAAAAAAAAAQRAAAAAEELAPPAREEEEDEJ.",
    ".........NDWWAAAAAAAAAAATRAAAAAALLALPLAREEEEEEJ.",
    ".........JEYYAAAAAAAAAAATAAAAAAAAAAPLAAREEEEEG..",
    ".........JEAAAAAAAAFFAAAAAAAAAAAAAAAAAAEEEEEEG..",
    ".........JEAAAAAAAAAAAAAAAAAAAAAAAAAAAEEEEEEF...",
    ".........GFAAAAAAAAAAAAAAAAAAAAAPGAAAFEEEEEG....",
    "..........NDAAAAAAAAAAAAAAAAAAAPPGEEEEEDEFG.....",
    "...........FIAAAAAAAAAAAAAAAAAPPEEEEEEEDEG......",
    "...........IFFAAAAAAAAAAAAAAPPPEEEEEEEEEDN......",
    "............IFEFALLLLLLLLPPPPPFEDDDEEEEEG.......",
    "............GFFEEDGLQPPPPPLLPPGBBBBENEDNF.......",
    "...........GFEGJJJJEQPPPAAAFFBBBBBVABBFDG.......",
    ".........GGENPPBBBBFFAAAAAFNBBBBBBAVBBBNDG......",
    "........GFFPWPBBBBBBNFFFNBBBBBBBBBBBBBBBNDN.....",
    ".......GDFPWPBBBBBBBBPBBBBBBBBBBBBBBBBBBBGGN....",
    ".......NFPWPBBBPBBBBPMBBBBBBBBBBBBBBBBBBBBEG....",
    "......NDPPPBBNPBBBBBMMMBBBBBBBBBBBBBBBBBBBBEN...",
    ".....NDNPPBBBGPBBBBMMMMaBBBBBBBBBBBBBBBBBBBFF...",
    ".....GGPBBBBGBBPPBBMMMMMaaBBBBNBBBBBBBBBBBBEDG..",
    ".....DDBBBBBDBaMdWWMMMMMMMMMBBJJBBBBBBBGDEEEEN..",
    "....GDRRFJBJFBaMWdMMMMMMMMMMBBJGBBBBBFFALLLLEG..",
    "....GFAAAEJNJBBaMMMMMMMMMMMBBBBFBBBNDAAAAAAAADI.",
    "...GEYYAALFDJBBBaMMMMMMMMMBBBBBNNBNFLAAYWAAAAEI.",
    "...GGVAAAALFBBBBMMMMMMMMMBBBBBBBEFFLAAAAYWAAAIG.",
    "..GFVVAAAAAFBBBBMMMMMMMMMBBBBBBBFEFAAAAAWVAAAAFI",
    "..GFVWAAAAANBBBBMMMMMMMMMaBBBBBBBDRAAAAYVYAAALDI",
    "..FQWAAAAADBBBBMMMBBBBMMMaBBBBBBJJDRAAAYYAAAALFI",
    "..FQAAAAAADBBBBMBBBBBBBBMaBBBBJJJJFAAAAAAAAAALFI",
    "..FQAAAAAADBBBBBBBBBBBBBBBBBBJJJJDAAAAAAAAAAAADI",
    "..FAAAAAAEJJJBBBBBBBBBBBBBBBJJJJJFAAAAAAAAAALAFI",
    "..IFAAAAAEBBJJBBBBBBBBBBBBBJJJJBFAAAAAAAAAALPFG.",
    "..IDAAAAAFBBBBJBBBBBBBBBBJJJJBBJFAAAAAAAAALPPEI.",
    "...GIAAAAADBBBBBBBBBBBBJJJJBBBBGAAAAAAAAALPPFI..",
    "...IDPAAAAAFBBBBBBBBBBBBBBBBBBDFAAAAAAAAPPPFGG..",
    "....IFPAAAAASFBBBBBBBBBBBBBBDSHAAAAAAAAPPPGFG...",
    "....GFGPAAAACOOEGNBBBBBBBGDOHHCHAAAAALPPTDGG....",
    ".....GDILALKCHCCCOSSSSSSSHCCCKKCRAAALPPTDGG.....",
    "......IDLLKCKHCCCCCHCCHKCCCCCCHCCRAAPPGDG.......",
    ".......FEKKCOCCCCCCHCCHKCCCCCCCHCCOAPFDG........",
    ".......FFHCHKCCCCCCHCCKKCCCCCCCCHCCCOSS.........",
    "........FOHKCCCCCCCKKCKHCCCCCCCCCOHCCSS.........",
    "........OSHCCCCCHKCCHCKCCCCCCCCCCCCOOOS.........",
    "........HOHCCCCCKOHHCCCCCCCCCCCCCCCCOO..........",
    ".........OOZCCCCCCHOSSOHCCCCCCCCCCCCKS..........",
    ".........OCZZCCCCCCHHHSHHHHCCCCCCCCCKSK.........",
    "........OSCCCCCCCCKHHHSOCHHHHCCCCCCCCOK.........",
    "........HOCCCCCCCKHHHHESCCCCCCCCCCCCCOO.........",
    "........KHCCCCCCKOHHHHSOKCCCCCCCCCCCCCS.........",
    "........KHCCCCCKOHHHHHSKOCCCCCCCCCCCCCSK........",
    "........HHCCCCKOHHHHHOSKSCCCCCCCCCCCCCOK........",
    ".......CSCCCCOOHHHKHHSOOSKCCCCCCCCXKKCOO........",
    ".......CSCCCHHHHHKCHHSOSOKCCCCCCCXKHHCCSS.......",
    ".......CSCCOHHHHCCKHHSHSHSCCCCCCCHHHHCCSS.......",
    ".......CSCCCCCCCCCHHHOS.SSCCCCCCHHHHHHCOO.......",
    ".......KSCCCCCCCCCHHOO..SOHCCCCHHHHHHHCHOK......",
    "......KOOOOHCCCCCHHHSH...HHCCCHHHHOOOOOOSK......",
    "......KOOZZUUCSOHHHHSS...KSCCOHOSOObbUUUSSX.....",
    "......KHVVUUUZZUUUOSSS...KSOOOOUZZUUUUUUUSX.....",
    "......KKVVUUUUUUUUUXSO...KKZZZUUUUUUUUUUUSX.....",
    "......KOXXUUUUUUUXXXKO...KSUUUUUUUUUUUXXKSX.....",
    "......KKEFFOUUUUUXXXKH....OUUUUUUUUUOFFFEK......",
    "......KKFAAAAFDSKKKXSK....OKXXUUSDFAAAALFK......",
    ".....TTSAAAAAALLIIFESK....KEEFAALLAAAALJJSJI....",
    "....IDTTAAALAAAAAAIOK......KHTAAAAAAAIIJJJGFI...",
    "..IIEIQTABBILAAAAAAO.......GTTAAAAATTWWBBJNGDI..",
    "..GFQQQQGBBBIAAAAAAD.......FFAAAAATTWWWFBQQQIDG.",
    ".IFQQQQQLGBBBAAAAAADI......FFAAAAANBWWTATLLQQQF.",
    "IFTQQQQAALNBBAAAAAADI......GDIAAAAJBBTAAATALQQDI",
    "IEFTQQQAAAGJJFGGNBBGI......GNBIFGFJBGAAAATALIGEI",
    "IGGNGFFIIGBNJBBBBBBDI......GGBBBBBJNGGIIIFGGIGNG",
    "IGBBBBBBBBBBBBBNNDDFI......GFDNNBBBBBBBBBBBBBBGI",
    "IGDGNNNNNNNFFFDGGGJJ........GGGGDFDNNNNNNNNNNDFI",
    "..IIIIIIIIIIF.....................IIIIIIIIIIIII.",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (48, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 48x96).
    scale=int   -> sprite de 48x96 px ampliado por un entero, sin márgenes.
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
