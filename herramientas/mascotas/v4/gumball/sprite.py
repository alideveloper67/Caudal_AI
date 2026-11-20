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
    "A": (20, 187, 251),
    "B": (1, 2, 3),
    "C": (15, 21, 25),
    "D": (82, 180, 203),
    "E": (250, 218, 176),
    "F": (5, 149, 219),
    "G": (71, 155, 175),
    "H": (18, 63, 81),
    "I": (59, 130, 146),
    "J": (15, 42, 52),
    "K": (238, 153, 139),
    "L": (118, 115, 112),
    "M": (63, 42, 38),
    "N": (15, 169, 234),
    "O": (43, 94, 106),
    "P": (92, 207, 240),
    "Q": (15, 140, 191),
    "R": (11, 117, 163),
    "S": (12, 98, 135),
    "T": (228, 84, 103),
    "U": (89, 82, 81),
    "V": (9, 78, 110),
    "W": (191, 231, 246),
    "X": (247, 251, 252),
    "Y": (156, 167, 170),
    "Z": (143, 70, 60),
    "a": (140, 223, 248),
    "b": (113, 52, 29),
    "c": (184, 146, 107),
    "d": (242, 96, 28),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".............................DDDDDDDDDDDDDDDDDDD........................................................",
    "........................PPPPDHBBBBBBBBBBBBBBBBCDPPPP....................................................",
    ".....................GBBBBBBBCASSSSSSSSSSSSSSSBBBBBBBB..................................................",
    "..................HBGBBBBIIRRRAAAAAAAAAAAAAAAASSVBHBBHGG................................................",
    "................GIIBBBBSSAAAAAAAAAAAAAAAAAAAAAAAAAAJJBJDDD..............................................",
    "...............GIJBCIBBAAAPPaAAAAAAAAAAAAAAAAAAAAAAAAHJBJDO.............................................",
    "..............OOBBIIPWWWAAPaPAAAAAAAAAAAAAAAAAAAAAAAAAAOBHOO............................................",
    "............JGOBOBBPWXXXWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOCODO...........................................",
    "...........GGHCOBPXXXXXXPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHCODH..........................................",
    "..........GGHCCPPXXXXXXPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAICODH.........................................",
    ".........GGGJGPPXXXXXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIBHD.........................................",
    "........GGJBGPXXXXWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABDD........................................",
    ".......DDBCGPXXXXWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBG........................................",
    "......DDCCIPWXXXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABGG.......................................",
    "......GJBIaWXXXPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVVAAAAAJCG.......................................",
    ".....GOBOPaXXXPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVBBCAAAAABG.......................................",
    "....DDJOPAaXXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVBBBBAAAAFBGG......................................",
    "....IJJPAAAPPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVBBBBCQAAAFBBG......................................",
    "...IIBJPPPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJBBBJQAAAAAABG......................................",
    "...IBBAAPWWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANJBBBCAAAAAAAABIJ.....................................",
    "...GBBAAWWaAAAAAVBBBAAAAAAAAAAAAAAAAAAAAAAAAAAAAANCBBBCAAAAAAAAACID.....................................",
    "..GGBBAAaaAAAAARBBBBBAAAAAAAAAAAAAAAAAAAAAAAAAAANJBBBBAAAAAAAAAAHBD.....................................",
    "..GHBAAAAAAAAAARBBBBBCJAAAAAAAAAAAAAAAAAAAAAAAANHBBBCQAAAAAAAAAAFBP.....................................",
    ".GGBAAAAAAAAAAAAVBBBBBBCJAAAAAAAAAAAAAAAAAAAAAAVBBBCQAAAAAACCAAAFBPII...................................",
    ".PBJAAAAAAAAAAAAAAAJBBBBBBBAAAAAAAAAAAAAANAAAAQBBBBAAAAABBBBBBAAFCHHIGG.................................",
    ".PBBAAAAAAAAAAAAAAAAHCBBBBBJAAAAAAAQQAAANJHAAQCBBBVAARRBBBBBBCAAAAHHCJGO................................",
    "DDBSAAAAAAAAAAAAAAAAAABBBBBBBHAAAAAVBQAAACAAQJBBBVBBVBBBBBBBHAAAAAAPPHJOO...............................",
    "DOBSAAAAAAAAAAAAAAAAAAAAVBBBBBCHAAAAQCQACAAAJBBBVHHBBBBBBBBBAAAAAAXXPPHBBBB.............................",
    "DBOAAAAAAAAAAAAAAAAAAAAAAAJBBBBBCAAAAHJNBAACBBBBCBBBBBBBBBAAAAAAAAXXXPPBBHB.............................",
    "DBSAAAAAAAAAAAAFFFFFFFFAAAANJCBBBBBAANBNBBJBBBBBBBBBCJAAAAAAAAAAAAAaXXPAACCC............................",
    "DBSAAAAAAAAAARBBBBBBBBBBNNNNNVBBBBBBBNBBBJBBBBBBBBJVAAAAAAAAAAAAAAAAaaaPAVCG............................",
    "DBSAAAAAAAAARBBBBBBBBBBBBBBBBBBBBBBBBBBBCBBBBBBCHAAAAAAAAAAAAAAAAAAAAAAaAACGG...........................",
    "DBSAAAAAAAAARBBBBBBBBBBBBBBBBBBBBBBBBBCASBBBCHHAAAAAAAAAAAAAAAAAAAAAAAAAAAHBG...........................",
    "DBVNAAAAAAAAAHBBBBBBBBBBBBBBBBBBBBBBBBRAASHHRAAAAAAAAAAAAAAAAAAAAAAAAAAAAANBG...........................",
    "DBVNAAAAAAAAAAQQQQQQQQQQQQQQQQQQQQQQRRBARRSRRAAAAAAAAAAAAAAAAAAAAAAAAAAAAANBBG...........PPPPP..........",
    "DBVNAAAAAAAAAAAAAAAAAAAAAAAAAQHJCCBCCCBCbbbbbMBBCJHAAAAAAAAAAAAAAAAAAAAAAAABBD..........OOCCCPP..GGGGDG.",
    "DBVNNAAAAAAAAAAAAAAAAAAAAAAAABBYYWWWWWWbddddddCWWWWMBAAAAAAAAAAAAAAAAAAAAAAQBD.........OOCYCHCIIIOBBBCDG",
    "DBCRNAAAAAAAAAAAAAAAAAAAAAAABBUYWWWWWWWWMMCMCCWWWWWWWCAAAAAAAAAAAAAAAAAAAAAQBD.........GBYPPPHBCJOAAAACD",
    "GGBRFAAAAAAAAAAAAAAAAAAAAAAABBYUCWWWWWWWWWWWYJWWWWWWWWAAAAAAAAAAAAAAAAAAAAAQBD........JGBPAAAPHJPPAAAABD",
    ".DBRFAAAAAAAAAAAAAAAAAAAAAAABYXXCbMCCJWYYYYYYCCYYYYWHBAAAAAAAAAAAAAARRAAAAAQBD......GGBOBAAAAAJJAAANNBBD",
    ".DBRFAAAAAASAAAAAAAAAAAAAAAABYXXCTTTTTbMMCCCCCCCCCMbBBAAAAAAAAAAAAAACBAAAAAQBD...IIIBBBJONJAAAAJJAVVVBOD",
    ".DBJFFAAAAJBSAAAAAAAAAAAAAAABYXMZTTTTTTTTTTTTTTTTTTTBRAAAAAAAAAAAAAAACBHAAARBBDJIIHBCbCCNNCAAAACJCBBBOD.",
    ".IIBFFFAACBHAAAAAAAAAAAAAAAABYXBZZZZTTTTTTTTTTTTTTTTBRAAAAAAAAAAAAAAAACBCAARBDJJCCMZZbCSAAAJVVCAAHHDDD..",
    "..BBBFFSBBVAAAAAAAAAAAAAAAAABBCMbbMMCMbTTTTTTTTTTTTTBRAAAAAAAAAAAAAAAAAHCBBJBBMLMMbMMbMSAAAVVRNAAVHD....",
    "..BOBBSBCAAAAAAAAAAAAAAAAAAABBBKKKKKKKKMMZTTTTTTTTTMJAAAAAAAAAAAAAAAAAAARCBBBEEELCZZZbMJQAAVRAANACHP....",
    "..OIBVBCRAAAAAAAJAAAAAAAAAAABBBKKKKKKKKKZMbTTTTTTTTCSAAAAAAAAAAAVAAAAAAANRCBBEEELCbMCMbBBQFFCVVHJCHP....",
    "...ICBCRNAAAAARBBQAAAAAAAAAAAJCKKKKKKKKKKKMMTTTTTTTCSAAAAAAAAAAVBJAAAAANFFCMEEEEKMMbMbbBBBJFCRQQQBDD....",
    "...IIBRFFNAAARBCQAAAAAAAAAAAAABKKKKKKKKKKKKKMTTTTTMCAAAAAAAAAAAAHBJQAANFFRCCEEEKKMMMBBBHOBJCHHRQCHD.....",
    "....IBCFFFAAQBBAAAAAAAAAAAAAAAJMKKKKKKKKKKKKKbTTTTCHAAAAAAAAAAAAAVBBQNFFRJMKKKKKMCBBBGGHHODHBBBBHD......",
    "....DIBHFFFQCBAAAAAAARRAAAAAAAABbKKKKKKKKKKKKMZTTMCAAAAAAAAAAAAAAASCBBFFVCcccMCCJJDDG.....HDDDDDDJ......",
    ".....DOBVFQJBVAAAAAAACBAAAAAAAAVBMKKKKKKKKKKKZCTbBVAAAAAAAAAAAAAAAASBBBVBMBBBJCIPPD.....................",
    ".....ODOBVVBHFAAAAAAJBAAAAAAAAAAACMKKKKKKKKKKKCMBVAAAAAAAAAAAAAANNFFSBCBBBBBGBIP........................",
    "......IIBCBJQFFAAAABBCAAAAAAAAAAAAJCMKKKKKKKKMBCAAAAAAAAAAAAAAANFFFFBBBJHBBG............................",
    ".......IBVBJQFFFFABBBAAAAAAAAAAAAAAAHBBBBBBBBJVAAAAAAAAAAAANNFFFFFFHBOOPPI..............................",
    ".......IBBHBJQFFFFHBVAAAAAAAAAAAAAAAARRRRRRRRAAAAAAAAAAANNFFFFFFFHJBIIOOII..............................",
    ".......ICBFFCCVFFFBHFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFFFFFFFFFFHCBCCCCHHCII.............................",
    ".......ICPFFFHBCFCCFFFFFNNNAAAAAAAAAAANNNNNNNNNNFFFFFFFFFFFSSBBBBPPHCDPPQBIIGGGG........................",
    ".......ICPAAFFFHBBCCFFFFFFFFNNNNNNNNNNFNHHHHHHHHHHHHHHHHHHCBBBGGPPPBDPAQHBBBBBBIG.......................",
    ".......GCHAAANFFFCCCCVFFFFFFFFFFFFFFFFVCCCCCCCCCCCCCCCCCCCCCBCCCCCCCPAAAPPWWWBIBB.......................",
    ".......GOJAAAANFFFFHHBBBCSSSFFFFFFFFFVBLEEEEEEEEEEEEEEEEEEEEBZZZZMOPAAAAPAAAAABBB.......................",
    ".......GOJAAAAAAFFFFFSSJBBBBHHHHHHHHHBLEEEEEEEEEEEEEEEEEEEEEBMMMMCOAAAAAAAFFFFVBB.......................",
    ".......GGCOAAAAAAAAFFFFFBRJCJJJJJJJJJBBEEEEEEEEEEEEEEEEEEEEEBZZZZMVAAAAAAAVBBBBBD.......................",
    "........GJONAAAAAAAAFFFFRCJDDDDDDJJGGBBEEEEEEEEEEEEEEEEEEEEEBMMMMCVNAAAAAAACOBBD........................",
    "........DGBNNAAAAAAAFFFSCBDI........GBMKEEEEKKKKKKKKKKKKKKKKBZZZZMVNNAAAAANCGO..........................",
    ".........DBCNFAAAAFFFFSCBGI.........GGBcKEEEMMMMMMMMMMMMMMMMBCCCCBCJSFAAANFBG...........................",
    ".........DDJBBFFFFFFFBBJGG...........GGCcEEEEUUUUUUMBOOOOOOOOOOOOOOHBSFFFFVBB...........................",
    "..........IIHBJRRRRBBJBBG.............GJMKEEEEEEKKKKCOOHDDDDDDDDDDDDBBJHHHBOG...........................",
    "...........IIGCBBBBJBBB...............OOCCKEEEEEEKKKKCDD............GGCCCCOG............................",
    "............GIGGGGGBB......GPPPPP......OCCcEEEEEEEEEKMHD.............DDDDDD.............................",
    "..........................GGCCCCPPP.....CHMcEEEEEEEEEcCHD...............................................",
    "..........................GCCYYABHIGG...CIJEKEEEEEEEEEcCCC..............................................",
    "..........................OJAAAAPIBHGG...GIBEKEEEEEEEEECCGG.............................................",
    "..........................OJNAAAAPAHCHGG..GCMKKEEEEEEEEEMHG.............................................",
    "..........................OCNNAAAAAAAJJGG.OGCKKEEEEEEEEEECII............................................",
    "..........................DOBVNNNAAAADHJGIOOOBUKEEEEEEEEEMHIGG..........................................",
    "...........................DHBJVFFNNAADSCICCBUEEEEEEEEEEEEMBJGG.........................................",
    "............................DGJCCVNFFFBBSCCMEEEEEEEEEEEEEEEEMCGGDDDDDDDD................................",
    ".............................GGCOCBBCBBBBBBCLLLLLLLLLLLLLLLLLBBBBBBBBBCDD...............................",
    "..............................HOOCLLLLLLLLBCCCCCCBLYYYYYLBCCCCMLLLLLLLMCID..............................",
    "..............................OOCYYLLLLLLLBULLLLLMMYWWWYMMLLLCMLLLLLLLYCBID.............................",
    ".............................JJBLYLLLLLLLLMBULLLLLUCJCCBULLLLCMLLLLLLLLYCJD.............................",
    ".............................JJMYLLLLUUUUUUJCUUUUUMMUUUBUUUUCCUUUUULLLLYUBD.............................",
    ".............................PJJLLLLUMMUUUUUJBMUUUCMUUUBUUMBCUUUUMMULLLLUBD.............................",
    ".............................PJMLLLLUMCBBBBBBBBBBBBBBBBBBBBBBBBBBCMULLLLMBD.............................",
    ".............................DBBLLLLLUCHIIIIIIIIIIIIIIIIIIIIIIIIJCUULLLLBHD.............................",
    "..............................DBCMMMMMCCIH....................JGCCMMMMMMBBB.............................",
    "..............................BBMUUUUUMBII....................GGBMUUUUUCJB..............................",
    "..............................GCMEEEEccMPP....................GJMcKEEEEMCJC.............................",
    "............................IGGCMCEEEccMHP....................GJCcKEEECCHCCC............................",
    "...........................IICCCCCCCCCCCJP...................GGCCCCCCCCCCCJDH...........................",
    "..........................PICCCPPAAAAAACCDD..................GJJCAAAAAACCCHJD...........................",
    "..........................PHHCQQAAAAAAANHHD..................GBFAAAAAANNSCBBD...........................",
    "..........................PHHCCQQCAAAANNHHD..................GBFAAAAARHNVSBBD...........................",
    "..........................PICHBBVCRRRRRVBOD..................DJJRRRRRBBBHJJJD...........................",
    "...........................DIBBBBBBBBBBBOD...................DDCBBBBBBBBBBJDD...........................",
    "............................DDDDDDDDDDDDD.....................DDDDDDDDDDDDDD............................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (104, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 104x96).
    scale=int   -> sprite de 104x96 px ampliado por un entero, sin márgenes.
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
