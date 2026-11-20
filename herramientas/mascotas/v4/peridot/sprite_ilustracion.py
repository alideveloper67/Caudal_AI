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
    "A": (2, 56, 43),
    "B": (232, 251, 66),
    "C": (3, 116, 67),
    "D": (161, 247, 20),
    "E": (115, 192, 13),
    "F": (97, 167, 13),
    "G": (80, 135, 12),
    "H": (5, 12, 6),
    "I": (23, 37, 10),
    "J": (136, 211, 14),
    "K": (41, 69, 9),
    "L": (58, 103, 14),
    "M": (198, 248, 36),
    "N": (240, 247, 179),
    "O": (237, 249, 120),
    "P": (185, 229, 62),
    "Q": (114, 136, 44),
    "R": (148, 162, 121),
    "S": (80, 93, 61),
    "T": (189, 201, 137),
    "U": (54, 60, 41),
    "V": (146, 184, 61),
    "W": (165, 236, 176),
    "X": (203, 242, 99),
    "Y": (247, 249, 242),
    "Z": (107, 136, 99),
    "a": (39, 149, 94),
    "b": (55, 181, 6),
    "c": (70, 181, 121),
    "d": (159, 93, 97),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......................FFEG..................................",
    ".....................FKHKEG.................................",
    "....................FFIPHHFF................................",
    "...................FFIPBOHHFE...............................",
    "..................FFIPBBBOOSKEF.............................",
    "..................FIOBOOBBONSIEF............................",
    ".................FFUOOYYOBBONSIEG...........................",
    ".................KKOOYYYOBBBONSIEG..........................",
    "................KKKOOYYNBBBBBONNIEG.........................",
    "...............KKIOBOYNBBBBBBBONNKJG........................",
    "...............FIOOBBOBBBBBBBBBONNKJG.......................",
    "..............FFUOBBBBBBBBBBBBBBONNKEG......................",
    "..............FIOOBBBBBBBBBBBBBBBONZKEG.....................",
    ".............FFFOBBBBBBBBBBBBBBBBBONZIEE....................",
    "............GGIFOBBBBBBBBBBBBBBBBBBBNNIE....................",
    "............GINNBBBBBBBBBBQQQQBBBBBBBNZKK...................",
    "...........GGUNNBBBBBBVBBTTRRQQVBBBBBBNZKE..................",
    "...........EKNNBBBBBBVNNTKTJJUNVVBBBBBBNKKE.................",
    "..........EEUNNBBBBBBNNNTTJJJJNTVBBBBBBBNKKF................",
    "..........EHNNBBBBBBBNNNYRKbbTTTVQBBBBBBBBUFF...............",
    ".........FKNNNBBBBBPPPNSRYPZZZZTVPQBBBBBBBBUFF..............",
    ".........FHNNBBBBBBQPPSYYYPXXZZWWPQBBBBBBBBPIF..............",
    "........GKNNNBBBBBBQQQYYYYPPPPWWWPQBBBBBBBPGKF..............",
    ".......GGUNNBBBBBBBSOVYYYYPPPVWWYQQBBBBBBJGHF...............",
    ".......EINNOBBBBBBBSOVYYYccPVPWYNQQBBBBJJJKGG...............",
    "......EEUNOBBBBBBBBBXXYYYYYVVVVYNQQBBJJJJKGE......JJJF......",
    "......EHNNOBBBBBBBBBBXTNYYTDDDDVVQQBBJJEKGE......JJHIEF.....",
    "......FINOBBBBBBBBBBBBTTNTDDDDDDDDDBJJEKLE......GGUTDIE.....",
    ".....FKIOBBBBBBBBBBBBBDEEDEULLULDDQDJJKLE.......GITDDHF.....",
    ".....FIKJJJJJJJJJJBBBBBDDDEERRULDDQJJKIF........GUDDDIGFIIF.",
    ".....KKHKEEJJJJJJJJBBBVEDDDKUIIDDGGJKIF.....JJJJKDDDKGFIIHFF",
    "......EEEHIIJJJJJJJJJJVVEDDEEEIDDGGKKK...EEJKIIJHDDDHKUDDDIF",
    "........FFIIIIFFJJJJJJJKEDDDEEEDLIIGF...EEIUCaCHDDDIIDDDDDII",
    "..........EEIIIHKLEEJJJEILDDDDDLHFFF..EEKERRaCAIDDDDDDDDDKKE",
    ".............EEGGLIIKGGFFILLGGKIFFK...EINNRACAHDDDDDJDDHKKE.",
    ".................GEEGGIHHHLGGHHHIHKKEEKNNNUCCIDDDDDDJDUHLLE.",
    "......................LLHILGGIADDDKUIKKMMAACADDDDDGDDDDDDDIF",
    ".....................ELLIKLLAADDDDDDDIMMMJACKDDDDbGDDDDDDDUF",
    ".....................EIHAALAAADDDDDDDGMMMJACAADKbbbbDDHLFFIF",
    ".......EEEEF........EKIAAKAAAAAFDDDDDGMMMAACAHHHHKLKDDDHLLFF",
    "......EEUEIFFF......EUUAAAAAAaFFKIDDDDDMEEAAAAHHHAHLHDDDLF..",
    ".....EKZEEEIIFF....EEUAAOOAACaCCIKIIKIFEEEEAAAHHHAIELKDDHJ..",
    "....EIZDEEEEFHG....EHUAOOOOCaCCCHIIIIKKFEEEAAAAHAHIKEKKDIJ..",
    "....GLDDXXEFFHGG...GUSOOOOOCCCCAII...FFIFFEAAAAAAIF..ELLFF..",
    "....GLDDXEEFFHKGGGGGSSCQOOCCCCCIGG....FFHILLLAAAHGF.........",
    "....GKDDDXEKLLSSHGGHSJACQACCCCAKG......EELLKHHHIGG..........",
    "....FIDDDDGGLCCSSUISDJAAAIAAAAHFF.........LLEEEGG...........",
    "....FFKDDGGGICAAMMUKDDAHAAAAAAHF............................",
    ".....JIKbbbGACAMMMMKKKHIAAAAAAHGG...........................",
    ".....JHIIKKHCCAMMMMMKKKAHAAAAACIGG..........................",
    ".....JHAHHHAAAAEMMMMIHAIAAAAAAACHLE.........................",
    ".....JHAHHAAAAEEEJJIIILAAAAAAAAAAKLE........................",
    ".....JIAAAAAAFEEEEEIILKLAAAAAAAADTUGG.......................",
    ".....GGHAAAAFEEEEELIKKKAAAAAAAADDNTIE.......................",
    "......EEHHAGGGEIIILIITDDAAAAAADDDDNNKE......................",
    ".......EEKIIIIIFFLLITNDDDAAAAADDDDNNIE......................",
    ".........EEEEEEF.LLNNDDDDDAAADDDDDXNNKE.....................",
    ".................LHNNDDDDEKAIDDDDDDXNIE.....................",
    "................KLLNDDDDDEEHIDDDDDDDDEE.....................",
    "................LIDDDDDDDEEIIDDDDDDDDEKE....................",
    "................GLDDDDDDDDHGFHDDDDDDDDIE....................",
    "...............GGLDDDDDDDLLFGKDDDDDDDDKFE...................",
    "...............GKDDDDDDDDHL..EHDDDDDDDFKK...................",
    "...............EHDDDDDDDIEE..EEKDDDDDDFKE...................",
    "...............EIDDDDDDDKE....EKDDDDDGGKE...................",
    "..............EGHCDDDDDHE.....EGHDDDDCCHGG..................",
    ".............EGHACCDDDKEE......GGKDDDCCCIFF.................",
    "............EGIACCCDDDKE........GHFDDCCWWIEE................",
    "............EKWCCCCCDHF.........FFHAACCWWWIEE...............",
    "...........EKAWWCCCAIFF..........EKKACCaWWUKE...............",
    "..........FFIWWWCCCCHF...........EKHCCCCaWWHGE..............",
    ".........EFHWWWaCCCCHF...........JKACCCCCWWWHGE.............",
    ".........EIWWWaCCCCCHF...........JKACCCCCCWWAIG.............",
    "........EEHWWWCCCCCAHF...........JKACCCCCCCWCHGG............",
    "........FHWWWCCCCCCAHF...........JKACCCCCCCCCCIG............",
    ".......FFICCCCCCCCCAHF...........JKACCCCCCCCCCIGG...........",
    ".......FHCCCCCCCCCCAIF...........JKACCCCCCCCCCCIE...........",
    "......FKACCCCCCCCCCAKF...........JJHACCCCCCCCCCIEE..........",
    ".....FFHCCCCCCCCCCAAK.............HHAACCCCCCCCCAHE..........",
    ".....EIACCCCCCCCAAAAK.............EHAAACCCCCCCCCAAL.........",
    ".....EIACCCCCCCAAAAAK.............EHAAAAACCCCCCCALL.........",
    ".....EHCCCCCAAAAAAAHH.............EKAAAAAAACCCCCCHL.........",
    "....EIAAAAAAAAAAAAAHJ..............KAAAAAAAAAACCCALE........",
    "....EHAAAAAAAAAAAAAHJ..............HHAAAAAAAAAAAAAIE........",
    "...EEHAAAAAAAAAAAAAHJ..............HHAAAAAAAAAAAAAHH........",
    "...EIAAAAAAAAAAAAAAHJ..............HHAAAAAAAAAAAAAHKK.......",
    "...EHAAAAAAAAAAAAAHKJ..............KKAAAAAAAAAAIIIHIK.......",
    "..EFHAGGGAAAAAAAAAHG................KAAAAAAAAAMMMNNUKK......",
    "..FIRNNMMMQAAAAAAAHG................HHAAAAAAAMMMMNNNUKK.....",
    ".EKRNNNMMMMQAAAAAAHJ................HHAAAAAAMMMMMMNNNIKK....",
    "EEUNNNMMMMMMKAAAAAIJ................HHAAAAAKMMMMMMMMMMIK....",
    "EHEMMMMMMMMMMAAAAHJJ................HHIAAAAMMMMMMMMMMMIF....",
    "EHMMMMMMMMMMMKAAHHF..................GHHAAAMMMMMMMMMMMIF....",
    "EHHMMMMMMMGGKIIIIFF..................GGIIHIKGGMMMMMMMMHF....",
    "EEHHHHHHHHKGGGEEEF....................GGIIGGGIHHHHHHHHFF....",
    ".FFFFFFFFFFG................................GGFFFFFFFFF.....",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (60, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 60x96).
    scale=int   -> sprite de 60x96 px ampliado por un entero, sin márgenes.
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
