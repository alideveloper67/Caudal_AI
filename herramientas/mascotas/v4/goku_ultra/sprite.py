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
    "A": (246, 122, 4),
    "B": (13, 15, 30),
    "C": (22, 27, 51),
    "D": (9, 4, 7),
    "E": (210, 89, 5),
    "F": (175, 51, 2),
    "G": (43, 47, 74),
    "H": (106, 27, 9),
    "I": (119, 126, 152),
    "J": (72, 83, 119),
    "K": (21, 52, 117),
    "L": (59, 13, 7),
    "M": (144, 35, 4),
    "N": (173, 178, 197),
    "O": (247, 196, 141),
    "P": (9, 33, 89),
    "Q": (234, 233, 236),
    "R": (66, 37, 33),
    "S": (220, 155, 110),
    "T": (142, 72, 36),
    "U": (92, 71, 76),
    "V": (64, 100, 167),
    "W": (199, 115, 71),
    "X": (148, 106, 75),
    "Y": (249, 171, 62),
    "Z": (186, 31, 52),
    "a": (250, 216, 181),
    "b": (103, 141, 200),
    "c": (181, 140, 102),
    "d": (183, 164, 153),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..........BBBBBB...........................",
    "........CGGGGGCBGCCBBBBB...................",
    "........BGGQQQQQQCCCCCBCB..................",
    ".......BCCCINNNQQQCCGCNGCB.GB..............",
    "......BJJGCCIIJJNQQNCCNNBCDGGCB............",
    "......BJJJKGGIJJJNQQNJNNGCBCGGC............",
    "....BCCGJJGKBIIJGJNQQNJNUCBBGNC............",
    "...BBCBCGCCCBJIJGGINQQQIUCBBINC............",
    "...BGINQQQQQJGIJJGGIQQQIGGCGNICBB..........",
    "...BCCINNQQQQNIJJGGINQQIGGGIICCBBBBB.......",
    "...BCCBNNIINNNNIJGCCNNNIGCGGGCCUBBGBB......",
    "....BCCBIIJJIINNIGCGIIIIIIBGCCCCUCCCB......",
    "......CCBIIGGGIIINQNIIQQNNNBGNCCBBCBBB.....",
    ".....BCVVGIJGGGIQQNINQQNNNNGIINQQQQBGBB....",
    "...BCKVCCBQIJGCQQNIIQQQGGNNQNQQQNNGGBBB....",
    "..BCKKBGQQQQQIQQQIGIQQCCCGQQNNIINGDCKGB....",
    ".BGGGCQQQQQNNIIQQIRIQQRCCRQQNIIICCJJJJC....",
    ".GGGGQQQNNNJJJIQIRRRQQSOOUUNJNNIQCBGJJC....",
    ".GICNQQJJJJJJJGNNRCRUUSOOSUCJNNQQQIGBGC....",
    ".KGINIIIIJGGGGGGNWWWIUUSSUURGJIIQNNIBBB....",
    ".CDCDDDDGGIIGGCRCWWaaIUOSGUUGGJICCBCBBB....",
    ".BBGGGJGCDGINIRUBRWWaaaOSSUUGJGCBCGGC......",
    "..BBBCGJBIINIJUXBTWSSOOSBXOUJNNIBGCB.......",
    "......GCIIIIJGCXRBTSOOScXSOJJIIIGBCB.......",
    "......CDGCBBBGGGXBHWOOSScSOOCDBBBCJJB......",
    "......BCGGJJGBBCCBHTWOOOOORDBCCCCGIIB......",
    "...BBBBBCCGKJVBBBDTTLLOOORDKGCBBCIIGB......",
    "..BCJJBBCGJJVVGBDDTSSHLLHRJJKCCCJIGB.......",
    ".........VVCDBREETWSSSWWSRDLBKKJJ..........",
    ".........BVVAAAEEETWWSWSSWHHXRDGK..........",
    "........DLRVAAAAEETTSSSSWSSXXXAACB.........",
    ".......DDbVPRAAAAEARGSSSWSSKRAAAAAD........",
    "......DIIbVKPRAAAAEECPKKKKKKCAAAATCD.......",
    "......DDHRKKKPHAAAAAAPKPPPPKCAAAATTGD......",
    "......DRSSKCKPBAAAAAARKKVVKPRAAEERKCD......",
    ".....CaSSSWHCPBMAFAAAARPPPPPEAAEECPLG......",
    "....DaaaSWSTLCBHFFAEAEECPKKEEEEALCCXD......",
    "...DROaOSSaSTBBHHEAEEAEECPREEEXEBRSSXD.....",
    "..DOOOOSOaOSTDDHHEAAEEAEELEEIIIXLSOSSSG....",
    "..BOOOSSOOTTDDLHFAAAAEEAEEEEIJUXHSSOSOB....",
    ".DOOOOaSOTHBBHHMFAEEAEMEAEATIIJUHSSOOOOC...",
    ".DDOTSaOOODJJLMMMFEFFAEHEAAMTIUHLTTOOOSR...",
    ".DDSSTSOOORJbGLMMMMFHMEHHAHFFHMRGBTOOOSSB..",
    "..DSSSSSOOOCJbGRHHLLLDLLBGCLLHLJJROOOSSRC..",
    "..LLSSSSScVKBCGDDBBPPKKPBBCCKBBJDPbOSSSD...",
    "...GDSSScKVVVRccRBBCPKKCBCCBPBDLPbbGSSD....",
    ".....DRSRPKVVOOOOXBBBBBBPBDPBBBOObKPHLC....",
    "......CDBCPCOOOOOXLFFHFCPLLPGHOOOOPCDG.....",
    ".......VBBBROOOOOHFFMMFPPRMCKEOOOOBDG......",
    "........VGDROOOOOHEEMAMPKREBKEHOOOD........",
    "...........DLOWWLAAFEAHPKREBKKMTTD.........",
    "............DHHRMEAFAARPKREBKKKLDB.........",
    "............RHMMFAEEYACPKRECPGKMD..........",
    "...........DEFFFFAAYYEPPKREBPKEED..........",
    "...........BEEFFEAAAAEPPKCECPKKAHB.........",
    "...........RYEEEAAYYAAPPKCERPKKAAC.........",
    "..........DYYEEAAYYYAHKPKBERPKKAEB.........",
    "..........LAAEEAAYYAARKPVCFRKKVEAH.........",
    ".........DLMAEEAAYAAECKPVCFHKPVAAT.........",
    ".........LMMEAEAAAAEMCKPbGFHPBGAAT.........",
    "........DAAMFAAAAAEFHPPPbPFMHAEEATD........",
    ".......DDAAMFAAAAEFMHCCPPPMEEAAAYAL........",
    ".......VDAAFFFAAEFFFEMLBPPMFAAAYOAH........",
    "......VDDAAAMFFFFFFAEHLLLDMFFAAOOAH........",
    "......VDHEAAMFFFFEAADDDHMMHFFEAAAEH........",
    "......GLEEAAFMFFEYYEHDLLMEEMFFEAAEL........",
    ".....DDAEMEAAFFOOYEMHLLHMFAAMFFFEFMLB......",
    "......DAEHEAAAAOOEMHFLLMHFFAAFFFFFFAC......",
    "......DAEHFAAAAAFFHFMDLMFMFFAAEMMMEAD......",
    "......LAAHFEEEEFFMFFHDLHEEMFFAAEMEAAL......",
    ".....DLAAHMFFFFFMFAFD.LLFAEMFFAAAYYAL......",
    ".....LAAAHHMFFFMFAALD.DHLFAEMFFEAYYED......",
    "....DAAAAAHMFFMFAALCVVDHMHEAEMFFEEEHD......",
    "....DDEAAAFHHMAAAMLG..DLMHHEAAFFFFFHR......",
    "...DDDEEAAAFAAAAFLHG...DHMHMFAAEFMHFHD.....",
    "...RDAAMEAAAAAAFLMBG....LMEMMFEAAEEAAL.....",
    "..RRAAAHFAAAAFMHFMC....DEEEAAMFEAAYYAR.....",
    "..GLAHAEHFAAMHFAAMD...DDEAAAAAHMFFAFML.....",
    "....LMHEHMMHMEAAFHD....BHEAHAAMMHFFHL......",
    "....DLDHHLHHLEMFHD......DHHMLHMLLLLLC......",
    ".....DLLLLHMLLHHD........DHHLDDLLLLLG......",
    ".....DPGLRLLLDCB..........DDLLHHRRZDG......",
    ".....BGUUKPCBBB............DCCPKVKZLG......",
    "....DCZZGKKCBC..............BCKKVKKHK......",
    "....DPZZKKPCB...............DCPKVVGZG......",
    "....DPZZKKPBC...............DCPKKVPZDK.....",
    "...DRCMGKPCDD...............DBCPKKPHDR.....",
    "...RRRRRBBBD.................DRCBRXTTDD....",
    "...DRHTBBBBD.................DHBBXTTRD.....",
    "..DCGZBTBBD..................DBBCPGGGZD....",
    ".DCKZZKKKCD.................DDCCPKVVKGZLDG.",
    "DGbZZKKKPCD..................DCCPPKVVKKZUB.",
    "DbKZGKKPCBD..................DMHHCCPKKKKZUD",
    "DGGZPPCRMHD..................DLLLHZZHRGGRZD",
    "DZZZZZZLD......................BGDDDHZZZZMD",
    ".DDDDDDD............................DDDDDD.",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (43, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 43x96).
    scale=int   -> sprite de 43x96 px ampliado por un entero, sin márgenes.
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
