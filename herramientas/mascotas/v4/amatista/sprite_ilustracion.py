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
    "A": (209, 130, 221),
    "B": (175, 97, 193),
    "C": (243, 188, 245),
    "D": (86, 52, 128),
    "E": (192, 117, 210),
    "F": (40, 23, 49),
    "G": (243, 214, 245),
    "H": (56, 34, 62),
    "I": (156, 88, 172),
    "J": (116, 68, 127),
    "K": (96, 65, 104),
    "L": (135, 74, 151),
    "M": (216, 148, 229),
    "N": (73, 47, 80),
    "O": (202, 165, 214),
    "P": (77, 44, 100),
    "Q": (226, 171, 234),
    "R": (33, 20, 39),
    "S": (48, 26, 81),
    "T": (173, 132, 187),
    "U": (250, 233, 250),
    "V": (24, 14, 30),
    "W": (12, 7, 16),
    "X": (137, 107, 144),
    "Y": (252, 249, 252),
    "Z": (188, 25, 242),
    "a": (133, 14, 184),
    "b": (106, 18, 146),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..............................KJJJJJK......................",
    "............................XHRKJJJFHKBB...................",
    "...........................PVXCCCCCCCCVBI..................",
    "......................EEFPPRTGCCCGGGCCCCHII................",
    ".....................IPFFCCTCCGCCGUYYYGCCRII...............",
    "...................IIFFCCCCCCCGGCCCUYYYGCOHLL..............",
    "..................IIRFCCCCCECCCCGGCCGYYYGCOVL..............",
    ".................LLNQGUUGCEPBCCQCUUUGCCCGCCTFFV..E.........",
    ".................LRQGYYGCEPBBBTQMCUUUGCCCCGCTVPLLHE........",
    "................KFFGYYGCCEEEEBTTQMQCGUGCCCCGGCXXXVE........",
    "................KKFYYGGCCIIHNHHNJQMQCCGCCMCCCCCCMRE........",
    "...............KHKGGGCGCJINUUNFRJJMMMCCCCCMMQQMMRPR........",
    "...............KKCGGCGCCIJUUUNVRNBNMACCCCCMQAAARRR.........",
    "...............NCCGQQCCCANUUUURKNBBKAACCCCMMMAKVRR.........",
    "..............BHCGCMCCCCAKUUUUUUKBBKHNCCCCEQGKPRRN.........",
    ".........HBBBBNUUGMGGCCCAAKUUUUUNAABKHCCCCEQGGRNNNBBB......",
    ".........HHHHNUUGMMGGCCCAAAKUUUKAAAKAICCCCCCCCCIINNRHBB....",
    ".........HHUUUUMMMGYGCCCAAAAKNKKAAAAAILCJJCCCCCAAAAACBFPB..",
    ".........PHHQQMAMMYUCCCCCCAAAKKAKKKKALLLJCCCGCAAAAAACCANHB.",
    ".........HHAAAAAMYUCCCCCCCXXXTAAANKKKNFAANCGGGEAAAAACCMAAPB",
    ".........HNNAAAMGYGCCCCCCCCCCTAAAAKKKNAAANCGGJEAAAAAAMAAAVP",
    "..........NPFAAGUGCCMCCCQQQTTTAAAAAIIAAAAACGJBBEAAAAAAAAEPJ",
    "......E...NNFUUUUCCCMMCCCCQTTTAAAAAIAAAANAAWJBBEEAAAAAAEBJJ",
    "......PPJJVNUUUCCCCMMMCCCCCCTBAAAAAAAAAANIBJVKKEEAAAAAEBBRJ",
    "......PPTTGUUUCCCCMAMAACOOCKVBBBIAEEAAHHIBBIFNEAAAAAAABBBHJ",
    "......PPCGGGGCCCCAAAAAEIOPKPWJBBIENFWHBBBBBVIAAAAAAAABBBNJ.",
    "......PHCCCCCCCCMAAAAEIILLLKKJAAEBBBFKBBBBFBAAAAAAAABBBBVJ.",
    "......JJWCCCCCQMMAAAPRHNHRSHRAAAAEBBNKKBNHEAAAAAAAABBBBKKK.",
    "....BJRJCCCCCCQMMBHHYYYMAAHDDJAAAAAEEENFFHHEAAAAAABBBBLRK..",
    "...BPNGYCCCCCMMMNHBMYYYMAAAHDDJAAAAEEEAASDPHAAAAABBBBIVL...",
    "..BPNGYYGCCCMMMVAAMMYYMAAAAAFDDAAAAAAAAAAHDPVAAABBBBIVJV...",
    "..BHUYYGCCCMENFAAACMMAAAAAAAHDDPAAAIAaaAAASDDRABBBBLVJI....",
    ".BHUYUGCCCMEFAAAMCMAAAAAAAAAADDDAAIAZZZZbAPDDPHBBBLRII.....",
    ".FUUUCCCMMEFAAAAMAAAAAAAAAAAAPDDNAaZZZZZSSPPDDRBBBWLI......",
    "FFUUCCCMMEHAAAAAAAAAAAAAAEEAISDDPPbZaZZZSSNJDDSHHRPI.......",
    "FRUGCCMMMPPAAAAAAAAAAAAAEBBEISDDDDPSSSSSPDJDDDDWAAHI.......",
    "JXGCCMAMMRAAAAAAAAAAABBBIPBBPPDDDDDDLLLLDDDDDDPRAQQFI......",
    "JXCCCAAAHAAAAAAAAAAIBBBBFIIIRPDDDDDDDDDDDDDDDPSRAQCNI......",
    "JXCCCAAAHAAAAAAAAAANIBVVBBIFSDDDDDDDDDDDDDDDPSFHAMCCNN.....",
    "JNCCCNAAHHBAAAAAAAAAWNPWFFVSDDDDDDDDDPPDDDDPSSRAAMCCNN.....",
    "NHCCRAAAHHBEAAAAAAAAFIBVSSSDDDDDDDPSSSPDDDSSSSWEMMCCCN.....",
    ".HXXFJAAAVIBEAAAAAAAINBJVSPDDDDPSSSSSPDDDSSSSFNEMQCCCHN..BB",
    ".HHLLJAAAAFIBBAAAAAAARBJVFFSPSSSSSSSPDDPSSSSDREEEQCUCNNJJKJ",
    "..LWLFACMANHBBBAAAAAAARJAABHFSSSFFPDDDPSSSPDDPNEEECCUNTTTKJ",
    "...LLNCCQMAHNBBBAAAAAAAAAABBWWWVSDDDPSSSSDDDDPNEEACCCCTGGNJ",
    ".....IHQCCMAHNBBBAAAAAAAAAIIHSPDDDDPSPPDDDDDDFEEEEACCCEEGHN",
    "....IJFCGCCMANFIBBAAAAAAABEIWPDDDDDDDDDDDDDPSWEEAAEEEEEEHH.",
    "...IJNCUYGCQMMFFIBBAAAAIBAEIVPDDDDDDDDDDDPSSFSNEAMEEEEENHB.",
    "...HHYYYUCCQMMMFVIBAAAAAILENFDDDDDDDDDPSSSSFDDVEEMMLLKREB..",
    "..HHHUYUCCCMMMEENIBEEEAAALLRDDDDDDDPSSSSSFFDDDSNEMMLNKKE...",
    "..HHUYUCCCQMMMEEERBBEHWVVVWSDDDSSSSSSSSSFSDDDDDREAMMPH.....",
    ".EPUUUCCCQMMMEEBBPWVWVFRVVVWSDDDPSSSSSSSDDDDDDSNEAMMP......",
    ".EFGUGCCQAMMAEEBBFVRFFHNFFFRWSDDDDPPPPDDDDDDDPWHEAMJJ......",
    ".EHGGCCQAAMQAEEBBWFFFPBFFFFFRWFDDDDDDDDDDDDDPWRVAAARJ......",
    ".EHGCCCAAEQMEEEBHVFFPBBPFFFFFFWVPDDDDDDDDDDSWVFRNAAPR......",
    ".EFCCCCAHEQMEEEBWFFHIBBFFFNFFFFVWRPDDDDDDSVWRFFHWWRI.......",
    ".EPCCCCHFEMMEEEWWFFDIBFFFNENFFFFRVWWRFFRWWRFPFFHWHII.......",
    "..PCCCCHHEAMAAANRFHDDHFFFEEEFFFFFRRRVWWVRFFFFEKKHHH........",
    "..CHCCCHHEAMAAANRFHPFFHFEEEEEHFFFVVVWWRFFFPFEEEEPNH........",
    "...CFCCHHAAAAAAHRFHHFFFEEEEEENFFRVWWVFFFFFFEEEEEHWB........",
    "...IIHCPKKAAAAAHFFHHFFHEEEEXFFFFRWWVRFFFFFFKEEETHWB........",
    "....IINKKRAEMMANRFHFRFKKKNEXFFFRVWVVRFFFFFFKEEETNWPB.......",
    "......EELLFEMMMFOQQOOKNRFFPFFFFRWWVVRFFFFFFKFFFFFNRI.......",
    ".........BBHEQMHOOOOOOOOONRFFFRVWWVVRFFFFFFFRFNOOQNI.......",
    "..........BPQQQHOOOOOOOOOOOFRRVWPFVVVFFFFRFFOOOOOQNI.......",
    "..........PNQQQFFFFFHOOOOOOTTFVWBWWVVRFVNOOOOOOOOOFN.......",
    "........BBPXQQABHBBBEENHOTTTTTNBBIWWVNTTOOOOOOJHHWW........",
    "........BHXQQAJBHEEEEEBBBHHTTTFBBIFWTTTTOOOOHPJBBRB........",
    ".........BPHNJJNHAAAAAAAEBBHKKPB..IRTTTTOFHBBBBBBFB........",
    "...........NJKJWAAAAAAAAAEBBFWW...IIVHRPBBBBBAACJHB........",
    ".............KNJACAAAAAAAEBBVLW....IIHBBBEAAAAACJJ.........",
    "............KKHAAYCAAAAAEBBHL.......IRBBEAAAAAAARJ.........",
    "............KVAAYUAAEEEBIBNNB.......NNBBAAAAAAAANN.........",
    "...........BNAMUUQAAEBBIBBFB.......NHBBBAAAAAAAAL..........",
    "...........BRAMUQAAAAEBBBFB........FFBBEAAAAAMMAL..........",
    "...........LAACQAAAAAAEBBFF........KPBBEAAAAAMMAF..........",
    "..........EHLACAAAAAAAEBBB.........KJBBEAAAAAQQAFF.........",
    "..........EFAAAAAAAAAAEBFB.........KJBBEAAAAAMQARL.........",
    "..........EHAAAAAAAAAABBHB.........JFBBBAAAAAMCAAL.........",
    "..........EHAAAAAAAAAABHH..........JRBBBEAAAAACAAH.........",
    "..........HHAAAAAAAAABLHH...........JNBBBEAAAAAAAHH........",
    "..........RRHHHHHHPBBBFL............IFBBBBAAAAHHFRN........",
    ".........RRRGYUUGGGGHNPW.............IRIIBNHGGGYGON........",
    ".........INGUYGGGGGGOOWB.............WWVFGGGGGGYGON........",
    ".........IKGUUGGGGGQOORB.............WWWGGGGGGGYGON........",
    ".........IKGUGGGGGGQOOBB.............WHOQGGGGGGGGOHN.......",
    ".........KKGGGGGGGCOOFB..............NNOOQGGGGGGGORJJ......",
    "........KHGGGGGGGCOOOHB...............NROOQGGGGUUUOJFKK....",
    "........WRGUYYGGGCOORL................HHOOOGGGGUYYYYYKRR...",
    ".......WWWUYYYUGGGOONL................LHOOOGGGGGUYYYYYRRR..",
    ".......WWGYYYUGGGGGOOOV...............LOOOOGGGGGGUUYYYYRR..",
    "......WHOGGGGGGGGGGOTVE..............VVOOOOGGGGGGGGGGGYRHE.",
    "......LFOTGGGGGGGGOTTFE..............AVIIIITTOOQQQQQQTTIRE.",
    "......LHTTTTTTTTTTTLLRE..............ARNJJJXXXTTTTTTTTIRRE.",
    "......IHHKKKKKKKKKNRHNE...............NPPPPPPVNNNNNNNNHRPE.",
    ".......IJJJJJJJJJJJJN.......................IILLLLLLLLLLR..",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (59, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 59x96).
    scale=int   -> sprite de 59x96 px ampliado por un entero, sin márgenes.
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
