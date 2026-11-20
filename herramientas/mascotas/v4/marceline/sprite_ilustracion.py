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
    "A": (3, 1, 8),
    "B": (27, 15, 18),
    "C": (46, 34, 99),
    "D": (15, 7, 13),
    "E": (145, 9, 20),
    "F": (177, 12, 9),
    "G": (128, 135, 151),
    "H": (34, 24, 28),
    "I": (226, 243, 251),
    "J": (17, 13, 35),
    "K": (106, 6, 10),
    "L": (78, 78, 88),
    "M": (91, 48, 168),
    "N": (66, 6, 10),
    "O": (29, 25, 54),
    "P": (36, 29, 77),
    "Q": (65, 53, 61),
    "R": (160, 169, 192),
    "S": (103, 109, 124),
    "T": (190, 212, 232),
    "U": (151, 79, 99),
    "V": (147, 52, 66),
    "W": (72, 35, 138),
    "X": (210, 107, 107),
    "Y": (201, 56, 52),
    "Z": (68, 65, 122),
    "a": (127, 92, 196),
    "b": (233, 173, 175),
    "c": (245, 208, 210),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "..................................BHHBBBBBBH...........................................",
    "................................BBBJJJJJJJJDBBB........................................",
    "...............................HBJOZZZCCCCCPJJDBB......................................",
    "..............................BHPBRRRZZCCCCCCPOJBH.....................................",
    ".............................HDPSRTRZZCCCCCCCCCPJBH....................................",
    "............................HBPSTTRZCCCCCCCCCCCCPDB....................................",
    "...........................ABJCTTRSCCCCCCCCCCCCCCPJH...................................",
    ".............B.............HDCCRTSCCCCCCCCCCCCCCCCJBD..................................",
    "........BB..QLHA..........HBPCCRZCCCCCCCCCCCCCCCCCCJH..................................",
    "......DHDDDBLLSB.........BDCPJZZCCCCCCCCCCCCCCCCJOCJB..................................",
    "......BNXDBHLSLBDB......DHDDODPCCCCCCCCCCCCCCCPOAAOCBH.................................",
    ".....HBXXFEQODBDHHB.....BQRDJADPCCCCCCCCCCCCPODAAAOCDH.................................",
    ".....BDFFFEKNDDDGGOB....HZRZJAADOOPCCCCCCCCCOOJAAAAPDH.................................",
    "....BHDKVVEEENDBGGBB...BHZZOAAAAAADJOPCCCCCCCCPJAAAJDH.................................",
    "...DQLQQEKFFFENGQOBD...BOCCJADJAAAAAAJJJJJJJJJJJAAAAAB.................................",
    "...BRRLDKFFFFEENDDB....BOCCJAJIQAAAAAAAAAAAAAAAAAAAAABH................................",
    "...BBBQBDEFFFFQEDH.....BOCOAAHIIIIQAAAAAAAAAAAAAAAAAADH................................",
    "....BBDDANFFFFFFBB.....BOCJAAHIIIIIRRRRRQAAAAAAAAAAAADH................................",
    ".....DBGGQEFEEEFNB.....BADDAAHIIIIIIIRQTTODAAAAAAAAAADB................................",
    "....DHGGGGNFFKEENDH....BAAAAAHIIIIIIIQBTIOOAAAAAAAAAODH................................",
    "....HHGGGSRNEFEBBBB....HDAAAAAAIIIIIIQQTIIOAJAAAAAAAPDBD...............................",
    "....HHSGSGRBANHUVVDB....BADAAAGQBIIIIQQTIIIADPAAAAAAPJDH...............................",
    "....BSHTRRRLDDQVUUNBB...HAOOAAHGHIGBHBBSIIQQDOJAAAAAPCAH...............................",
    "....BBBTRTRLBDBUVUUNBB..ABJCJAAGIGBBBBBSIIIQQJJAAAAAPCJBB..............................",
    "......BBRTTTBDBNUUVQDB...BDOJAADGRBBHHHIIIIIAJAAAAAAOCCAH..............................",
    ".......BQTTTOBDBKUVVKBB...HDPJAABRRHBHIIIIIIAAAAAAAAAPCODB.............................",
    "........HDIIBBABBQVUUNDB..BBJPAAAAARHSIIIIRROAAAAAAAAJCCOBH............................",
    ".........BIIIBHABNUUUUDB...BBJOAAAAAOSSSITHQAAAAAAAAAAJCCPJHHA.........................",
    ".........BOIIIDBDBKUUQQDB...DBJJAAAAAAAAITTHRJAAAAAAAAACZZZODH.........................",
    "..........HIIIIBABBBHUUNBB...DBPAAAAAADHLITIIRLHHDAAAAADOZZZPDB........................",
    "..........DHIIIIBABBUVVUDB....BOAAAAQHLLLIIIIILSSQAAAAAAAACCZPBD.......................",
    "...........BIIIIDDABKUUQQDB...BOAAQRILLLLIIIIIQGGIIIDAAAAAADPCJB.......................",
    "...........BHIIIIBDBDQQUUNDB.DBJHIIIRLLLIIIIIIGGQIIIIAAAAAAAAOODH......................",
    "............HIIITBBDBNUVVLNBHDQIIIIISSLRIIIIIQGSGIIIIAAAAAAAADJAH......................",
    "............BOIIITBBBDNULVVBOIIIIITTQGLRIIIIIQGSGIIIIIAAAADJBDBAH......................",
    ".............BHRIIIIHBDQVUUKIIIITTTTLGLRIIIISSGLGIIIIIBAAADJB.DBH......................",
    "..............BHRIIIIIINUVVUDITTTTHALGGQIIIGQGGLGGTIIIIAAADPBD.........................",
    ".............BBBHIIIIIIIKUUQUHTQDAAOGTGGQOOGGGGSLTSIIITBAADPJB.........................",
    "............BBOOOJQIITTTOQQUUKADDAASRTRGGGGGGGGSQSSIIITAAAADPBB........................",
    "...........BJCMMMWCOQGGGABUUUUBADAASRRGGGGGGGGGSLQOQIIIAJAADCOBB.......................",
    "..........BHWRTaMMMMCJAADANUQQUNAAAQGGGGGGGGGGGSLLLDIIIIQAAAOCJB.......................",
    "..........HPRTaMMMMMMWCDDDDHVUVVDAABGSSSSSSSSSLLLLQAOIIIIAAAJCPJH......................",
    ".........BHWTaMWCCWMMMMWJAABUVUUKAAAHQLLLLLQQQQLLLOAAIIITHAAAOCPJHD....................",
    ".........HJMRMMWPOCWMMMMWJAANUVVQNAAADQLLLLLLLLLLLDAAQIITAAAAJCCPJHBH..................",
    ".........BJMRMMWCOPCWMMMMWPAAVVVVVDAAALLLLLHQHHQLLAAAHIITAAAAAJCCGQHBB.................",
    ".........BJMMMMMWPOCCWMMMMWCJDQVUUKAAAQLLLLQRGGQHQAAAARIITAAAAJPCGGGODH................",
    ".........HJMMMMMWCJPCCWMMMMWCJNUVVLBAAQLLLLQRGGGGHAAAARIITAAAAAJPCGGZOBB...............",
    ".........HDMMWCCPPJJCCCWMMMMWCJKULQUDDQLLLQLGGGGGGQDAARIITAAAAAAJPCCZCJBB..............",
    ".........BAWPBKEKNDAPCCCWMMMMWPDQVUUNBLLLLHKNGGGGGGGBHIITAAAAAAAAJOPCCCDH..............",
    ".........BBJEFFFFKKBDPCCCWMMMMWONUVQVNOLLQNFEENGSGGGGQIITAAAAAAAAAAJJCCJBH.............",
    "..........BNFbFFFEKNADPCCCCMMMMWONVUVUNQLHEEbEEKHSGGQIIIAHAAAAAAAAAAAJCPDH.............",
    "..........BBEbbFFFENADDPCCCCMMMWCDVVUVVBQNEbVEEEENGGIIIIAAAAAAAAAAAAAAJPDH.............",
    "...........DEXbFFFENADAAPCCCCMMMCONUVUUKAEbVEEEEEENBIIIIDAAAAAAAAAAAAAADDH.............",
    "...........BKYXFFFEKDAAADPCCCCMMWCONUUVLNEVEEEEEEEKIIITOQHAAAAAAADPJADBDDH.............",
    "..........ABDFYXFFEKDAAAADPCCCCCCCCJQQLVVNEEEEEEEKIIITLQSSAAAAAAAAOPDDBBBB.............",
    ".........AHBDFFXFFFKDAAAAADPCCCCCCCPDVVUUKKEEEEEKLIITLQSGGSAAAAAAAOCJDB................",
    "......AHBBJAANFXFFFKKAAAAAAAPCCCCCCJNNUVVUNEEEEKLIITNNBGGGGBAAAAAAOCCDHA........HHH....",
    ".....BBDPCCPANFXXFFKKAAAAAAAACCCCCJNEKKUUQNNEENQIITGNEEQGGGGAAAAAAAPCPDHBB....HHJDH....",
    "....BHPGGGCCPBFFFFFEKAAAAAAAAAPPODKEEENUQQNNIQIIITGNKEEKGGGGOAAAAAAAPCCDBBBBBBHDPDH....",
    "...BHQGGCCCCPAKFFFFEKAAAAAAAAAADNEEEEEENUBIIIIIITNNKSSKENGGGGAAAAAAAAPCCCOJJJOCPJDH....",
    "...HOSSCCCPOAABFFFFEKNAAADHHHDKEFXXXEEENHIIIIIIRNNKKKSNEEGGGGHAAAAAAAJPPCCCCPPPJAB.....",
    "..BBCCCPOODAAAAFFFFFKKAAAQRRRNEEXcbVEEKGRRIIIIRHNEEEKNEEENGGGLAAAAAAAAAAOOOOJAAADB.....",
    "..HJCCOJAAAAAAAEFFFFKKAAAORGGHEEcbVEEENGRRIIIQBKEEEQQEEEEKKGLQAAAAAAAAAAAAAAAAAABBHA...",
    "..BOCJAAAAAAAAANFFFFKKAAAHRGGGNVXXEEEEKQGGRRQQQKEEKGGKEEEKBJJAAAAAAAAAAAAAAAAAAJOODBHA.",
    "..BOPAAAAAAAOAANFFFFEKNAAHRGGGNEVXEEEEEKBGQQQUUKNNEHHEEKBDPCWWWWWOAAAAAAAAAAAOPCCOPPDH.",
    "..BJAABBBDAJPAABEFFFFKNAAAGGGGGKEVEEEEEEEKNNUUVQGLKEEKNDPCWMMaaaaMMMCJJAAAAAAAAAOPPCPBD",
    "..HADBD..BACPAAANFFFFKNAAAQGGGGHEEEEEEEEEEEKVVVRGLNENDPCCWMMMMMaRRMRaaaCPJAAAAAAAAADPOB",
    "..BDB...BDOCPAAANFFFFEKDAAAGGGGGNEEEEEEEEEEENSRGQNENJCCCWMMMMMMMMMaaRaaaMMCJAAAAAADDDJB",
    "...H....HACCJAAANFFFFEKNAAAOGGGGQKEEEEEEEEEKERSHKEBOCCCCWWWWMMMMMMMMMMMMaaMWOAAAAAB.BBB",
    ".......BBOCCAAAADEFFFEKNAAAAGGGGGQKEEEEEEEEEQSNEKBPCCCCCCCCCCCCCWWWWWWCCWMMMWOAAAABH.BB",
    ".......BJCCDAAAAAKFFFFKKDAAADGGGGGHKEEEEEEEEKKENDDJJJJJOOOOCCCCCCCPOJJCMMMMMMCDAAODH...",
    ".....ABOCCJAAAAAAKFFFFEKBAAAAQGGGGGQKEEEEEEEEEKDAAAAAAAAAAADJDJJOJDCWaRRMMMMWCJAAPDH...",
    "...DHHOCCJAAAAAAAKFFFFEKNAAAAALGGGGGQNEEEEEEEKDAAAAAAAAAAAAAAAAANBPMaRMMMMMMWCJAAPDH...",
    "..HBDOCCJAAAAAAANXFFFFEKKDAAAADLGGGGGGHNEEEEKAAAAAAAAAAAAAAAADNEEFKCMMMMMMMWCOAAAPDH...",
    "HBDJPCPAAAAAAAADEXXFFEKKKKAAAAADLGGGGGGGBNEEBAAAAAAAAAAAAAABKFYbFFFNWMMMMWCCCDAAAADH...",
    "DOPCPAAAAADAAAANYXFFFKKKEKAAAAAADLGGGGGGGGHNAAAAAAAAAAAADKEFFbbYFFFFBMMWCCCPDAAAPDBH...",
    "HBAAAAADBBDBADNYXXFFKKKKKKAAAAAAAAQGGGGGGGGHAAAAAAAAADNKFFFXXFFFFFFFNCCCCPJAAAAJPDB....",
    ".AHBBBHB.ABDANFXXFFKKKNKKNAAAAAAAAAAGGGGGGQAAAAAAAABKEFFFFFFFFFFFFFEKJCPOAAAAAOCJBH....",
    ".........DHBEFFFFFKNKNANDAAAAAAAAAAAAJGGGGHAAAAAANKFFYYFFFFFFFFFEKKKKDJAAAAAAOPJDB.....",
    ".........HDEEFFEKKKKBAAAAAAADPAAAAAAAAAAOADAAABKFFYYFFFFFFFFFFEKKKNDAAAAAAAAOCJDH......",
    ".........BKFEKKEEENDAAAAAADJPPAAAAAAAAAAAABNKFFYYYFFFFFFFFFEKKKNBAAAAAAAAADJODBB.......",
    ".........HDNNNNNNDAAAAADJJPCCPAAAAAAAAADNKFFFYXXYFFFFFFEEKKKBDAAAAAAADJAAADBBHD........",
    "..........HBBBBBBBAAAJJPPOPCCAAAAAAAANEEFFFXFXYFFFFFFKKKNDDDAAAAAAAAAJJBBBH............",
    ".................BAJJOJDDAAPOAAAAADBDKFFEFFXFFFFFEEKKNAAAAAAAAAAAAAAAAB................",
    ".................HDJJDDBBBDPDAAAADBABKEEKbbFFFEEKKNDAAAAAAAAAADJAAABBB.................",
    ".................HDABBB..BOOAAAADBB.BBDKEbbFFEKNBDAAAAAAAAAAAAJCJAAB...................",
    ".................BBBB...HDJAAADDBH..BDDKFbFFFKNDAAAAAAAAAAAAAAJCPJABB..................",
    "..................BB....HBBBBBBH.....BKEFFFFKNDAAAAJPDAAAAAAAAAOCPPJDBHHHH.............",
    ".....................................BKFEFFEKABHHBBDPJAAAAAAAAAAOCCCCJJJDH.............",
    ".....................................HNFKFFENDB...BBODAADBDAAAAAAJOPCCPOBB.............",
    ".....................................HDEFKFFBBB..BBJJAABBDBBAAAAAAADJJJHB..............",
    ".....................................DBNFEKEDH...BDADBHB...BHBBAAAAABHBD...............",
    "......................................HBKFEKDH...HHHHB........DHHBHHB..................",
    ".......................................HDEFEDH.........................................",
    ".......................................AHDBBB..........................................",
    ".........................................BBH...........................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (87, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 87x96).
    scale=int   -> sprite de 87x96 px ampliado por un entero, sin márgenes.
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
