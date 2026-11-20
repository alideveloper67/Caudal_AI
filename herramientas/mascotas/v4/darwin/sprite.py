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
    "A": (252, 109, 3),
    "B": (4, 2, 1),
    "C": (219, 96, 7),
    "D": (28, 15, 7),
    "E": (187, 85, 8),
    "F": (252, 252, 251),
    "G": (249, 12, 33),
    "H": (87, 35, 7),
    "I": (121, 50, 8),
    "J": (155, 69, 7),
    "K": (57, 21, 6),
    "L": (83, 177, 42),
    "M": (241, 237, 225),
    "N": (207, 60, 2),
    "O": (34, 44, 30),
    "P": (248, 60, 88),
    "Q": (203, 205, 197),
    "R": (249, 144, 61),
    "S": (252, 197, 138),
    "T": (99, 99, 97),
    "U": (163, 165, 156),
    "V": (68, 68, 68),
    "W": (49, 120, 29),
    "X": (176, 22, 38),
    "Y": (135, 135, 132),
    "Z": (210, 51, 74),
    "a": (166, 109, 63),
    "b": (125, 198, 90),
    "c": (180, 140, 100),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".............................KCCCCCCCCI.............................",
    ".........................EEEEEBBBBBBBHEEEEH.........................",
    "......................HEEEBBBBBIBBEEIDDBBIDEEE......................",
    "....................JEEHDKKBCCKBBBBKEACCADDDHIKKKK..................",
    "...................JJKDHAAAAAABBBBBBDHAAAAAAHKKKKEE.................",
    ".................HEEDHAAAAICAAEEEJKBBBAAAAAAAAIHDKEEEE..............",
    "................HEIDaSAACACKCJJJJEEEHAAAAAAAAAAABHDDHECD............",
    "...............IEIDaMFSCDCCBKVVVVDHEAAAAAAAAAAHBBKHHDBBCH...........",
    "..............IEIBFFFMAAIHKVFFFFFFVKEAAAAAAAAAKBBBBHHKBIEH..........",
    "..............CIBJFFMRAAABTMFFFFFFMVIAAAAAAAAAIKKBBBDHHBIEI.........",
    ".............CCDJFFFRAIADTMFFFFTTMFVDAAAAAACCCCCCJHBBDAJBIEE........",
    ".............JHBAFFAAAKBTMFFFODBBDFVVIAAAAABBBBBIJAIBAAAJBDEE.......",
    "............JJKEAAAAAAITFFFMOBBBBBVFTIAAADOFFFFFOOIAAAAAAABKEE......",
    ".........CCCJIDEMMAAAADFFFMOBBBBBBVFTIAEDYFFFFFFFFDAAAAAAAABHEE.....",
    ".......ICCHDDBIAMMAAAIFFFFVBBBBBBBBVVIEKYFFFFFYYFFFHAAAAAAAIBHCI....",
    "......EEKBBIIIAAAAAAAOFFFFDBBBBBBBBBHEHYFFFQBBBBBFFDDDAAAAAAAKKC....",
    ".....ICDBEERRRAAAAAAIVFFFVBBBBBBBOMBIIOFFFQDBBBBBFFTICAAAAAAAIBCI...",
    "....JCKDERRFFFRAAAAEDFFFFBBBBBBBBMMDIHFFFQOBBBBBBTFTHCCAAAAAAAHKCK..",
    "...JCHDERFFFFRRAAAAEVFFFBBBBBBBBOMMHIFFFFVBBBBBBBTFTDKAAAAAAAAAKIC..",
    "...IIBRRFFFFRAAAAAAEVFFQBBBBBBBDOMDHHFFFFOBBBBBBBTTTIAAAAAAAAAAHBCH.",
    "..IIBKRFFFFAAAAAAAAEVFFQBBBBBBBBFOKTTFFFFBBBBBBBOFYBBKAAAAAAAAAADIC.",
    "..IHKKFFFAAAAAAAAAAEVFFQBBBBBBBFFDOITFFFDBBBBBBBBFYICCAAAAARSRAAHBE.",
    ".HIBHAFFSAAAAAAAAAAEOFFFBBBBBBFFOEEOFFFBBBBBBBBBFFVIAAAAAARMMSRAABE.",
    ".IIDAAASAAAAAAAAAAAAIVFFFBBBQQQVDCEVFFQBBBBBBBBOFFKAAAAAAARMFMRAADEK",
    ".EBHARRAAAAAAAAAAAAAADVFFFFFQQDDCAEVFFQBBBBBBBBMMFHAAAAAAARSFFSRABBB",
    "IEDAAAAAAAAAAAAAAAAAAADDYYFFVDHAAAEVFFQBBBBBBBVMMKAAAAAAAARSMFSRAHBC",
    "IIDAASSAAAAAAAAAAAEEEEAAHHHHHAAAAAEOFFQOBBBBBVMMBIAAAAAAAARSMMSRACBC",
    "EBIAAAAAAAAAAAAAIDDDDDIAAAAAAAAAAAAHVFFUOBBOVMMOHAAAAAAAAARSSSSRACBC",
    "EBCAAAAAAAAAAAAKKXGGGXHBHAAAAAAAAAAADVFFUTTFFOOKAAAAAAAAAARSSSSRACBC",
    "CBCAAAAAAAAAAAHKXGGGGGGXKDKHAAAAAAAAADFUFFFFFOHCAAAAAAAAARSSSSSRACBC",
    "CBCAAAAAAAAAAADXGGGGGGGGGGIHDDHEEAAAAAIDOOOOKICAAAAAAAAAARSSSSSRACBC",
    "EBNCAAAAAAAAAIIGGGGGGGGGGGGGXXHBBDHHIABEEEEEAAAAAAAAAAAAASSSSSRAAHBC",
    "EBHNCAAAAAAAAIIGGGGGGGGGGGGGGGGGGXIIKBBBBBBIAAAAAAAAAAAARSSSSSRCCBIC",
    "EHBNNAAAAAAAAIIGGGGGGGGGGGGGGGGGGGGGGGGGGGGHDHAAAAAAAAARSSSSSSANNBEH",
    "IEBNNAAAAAAAAIHGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGKIAAAAAAAARSSSSSRANNBE.",
    ".EBHNNAAAAAAAAKXGGGGGGGGGGGGGGGGGGGGXXXXXXXXXXBAAAAAAAARSSSSRANNDKJ.",
    ".HHDNNNAAAAAAAIDGGGGGGGGGGGGGGGGGGHKDDDDDDDDDKBAAAAAAAAAARRRAANNDJJ.",
    ".HHBKNNCAAAAAAAKKGGGGGGGGGGGGGGXKDHXPPPPPPPPPXBAAAAAAAAAAAAAANNKKJ..",
    "..HIDNNNCAAAAAACDHGGGGGGGGGGGGIBHPPPPPPPPPPPPPBAAAAAAAAAAAAAANNKJI..",
    "..HEDDNNNCAAAAAACDHGGGGGGGGGGHKZPPPPPPPPPPPPPHKAAAAAAAAAAAAACNHKK...",
    "...EEBHNNNNNAAAAAEKKXGGGGGGGIKZPPPPPPPPPPPPPXDAAAAAAAAAAAAACNIDKI...",
    "....CJBKNNNNNAAAAAEHDHGGGGGXDZPPPPPPPPPPPPPPDIAAAAAAAAAAAAANNHKKH...",
    ".....CJBDNNNNNAAAAAAADDIGGGKHPPPPPPPPPPPPPIDHAAAAAAAAAAAAAAAAAKHHI..",
    ".....KCJBBDNNNNNAAAAAAEDBKXDPPPPPPPPPPPPXDDAAAAAAAAAAAAAAAAAAAAHHCH.",
    ".......CJJBBHNNNNNAKKKIEDHKBDKXXXXXXXXKBBAAAAAAAAAAAAAAAAAAAAAAAKHC.",
    ".........JKKBBKHIKDRccIDIAAAJJKKKKKKKKAAAAAAAAAAAAAANNAAAAAACCAAABE.",
    ".........KKKHBKDBHRRRRRRKIAAIIIIKAAAAAAAAAAAAAACCCNNNNAAAAAAIKCAADE.",
    ".........KHKKRCHHRRAAARRRDBDHaaKKKIAAAAAAACCCCNNNNNNINAAAAAAAIKAJDD.",
    "........KKDRRACDAACCAAAARADDRRRRRIDAAAAAAJNNNNNNNNHHDAAAACJAAAHKDJI.",
    "........CKHRRAHIAAHKAAAAAAKIAAAARRKIAAAAJDNNNNNHHKBKDIAAACKJAAADHC..",
    "........CBCAAADIHBKDAAAAAAADAAAAAAEKAAACHKBKKKKBIIJEEKAAAACDJAIHCI..",
    "........CBCAAAAHHCCBIAAAAAAHKAAAAAEKAACIBBBDJJJJIJ.IEHKAAAADDHKJI...",
    "........CBIAAAAAAAAIKCAAAAAAHKAAAAKAACIBBBEEE.......IEDHANNIDKJI....",
    "........EEDAAAAAAAAJBICAAAAAAHKHHKIACIBBBJJ..........IEHDKKKIII.....",
    ".........EDKAAAAAAAJKDCCAAAAAAAJJAACIDHNKJI...........IEJJJKI.......",
    ".........JEDHINNNIHDHHKCCAAAAAAAACCIDINHHJ..........................",
    "..........JEHDKKKDHHHEHKICCCCCCCCCHDIAAAHJ..........................",
    "...........JJEIIIEEH.IEHDHINNNNNHHDAAAAAHJ..........................",
    ".............EEEEE....EJJIBDDDDDHIDAAAAAHJ..........................",
    "........................JEIBDDDACCDAAAAAHJ..........................",
    "..........................EDCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJ..........................",
    "..........................ADCAAAACDAAAAAHJH.........................",
    "..........................ADCAAAACDAAAAAHJE.........................",
    "..........................ADDDDDDDBDDDDDBBE.........................",
    "..........................ADDQQQQOOQQQQQQOE.........................",
    "..........................ADQFFFFMOFFFFFFOE.........................",
    "..........................ADQFFFFMOFFFFFFOE.........................",
    "..........................ADQFFFFMOFFFFFFOE.........................",
    "..........................ADDUUUUODUUUUUUOE.........................",
    "..........................ADOOOOOOBOOOOOOBE.........................",
    "..........................ADLLLLLLDLLLLLLOE.........................",
    "..........................ADLLLLLLDLLLLLLDE.........................",
    "..........................DDLLLLLLDLLLLLLDE.........................",
    ".........................JDDLLWOWLDLLOOLLDEII.......................",
    "...................EHHHHJIIBLWDODWDLOOOOLDHIIHCCCC..................",
    ".................CEEHHHHKOOOLOOOOODWDYYDWWOODHHHHJJJJ...............",
    "...............CCIDDVVBYYQQLLDTFVODWDQQDWLQQQLDOOODHEE..............",
    "..............ECKOQQFFYObbbLLDTFVODWDQQDWLbbbLDFFFFVDEE.............",
    "..............EKOFFFFFYBLLLLLDVFOODWDQQDWLLLLOFFFFFFFDE.............",
    ".............CCBFFFFFFMOOLLLLLDDDDDLOVOOLLLLWBMMMFFFFVCC............",
    ".............CKFFFFMMMMOOLLLLLODOLDLLDDLLLLLWMMMMMFFFFBC............",
    ".............CKUMMMMMMMMDWLLLLLLLLDLLLLLLLLWBMMMMMMMMQBC............",
    ".............CKUMMMMMMMMTWLLLLLLLWBWLLLLLLLWOMMMMMMMMQBC............",
    ".............CHOMMMMMMMMTOLLLLLLWOBWWLLLLLLWOMMMMMMMMMDC............",
    ".............CCDTMMMMMMMQDLLLLLWODHDOWWLLLLBQMMMMMMMMOCC............",
    "..............CJBTQQQQQQQOWWWWDDHJJHHBDWWWWBQQQQQQQMDIC.............",
    "...............CJBOVUUUUUDBBBBICCI.IHHHBBBBBUUUUUQODHCK.............",
    "................EEEBBBBBBBBEEECH.....HHEEEBBBBBBBBICCH..............",
    "..................ECCCCCCCCE.............ECCCCCCCCCH................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (68, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 68x96).
    scale=int   -> sprite de 68x96 px ampliado por un entero, sin márgenes.
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
