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
    "A": (9, 8, 5),
    "B": (36, 16, 6),
    "C": (22, 31, 17),
    "D": (62, 31, 8),
    "E": (90, 42, 9),
    "F": (116, 54, 8),
    "G": (146, 70, 6),
    "H": (93, 70, 30),
    "I": (169, 91, 13),
    "J": (191, 114, 55),
    "K": (131, 78, 33),
    "L": (198, 113, 16),
    "M": (58, 45, 39),
    "N": (208, 154, 82),
    "O": (226, 141, 26),
    "P": (236, 176, 59),
    "Q": (43, 86, 18),
    "R": (142, 109, 46),
    "S": (161, 134, 78),
    "T": (243, 210, 101),
    "U": (246, 170, 114),
    "V": (101, 83, 64),
    "W": (199, 174, 128),
    "X": (242, 229, 164),
    "Y": (250, 245, 214),
    "Z": (142, 155, 36),
    "a": (134, 124, 99),
    "b": (80, 162, 24),
    "c": (106, 208, 31),
    "d": (136, 196, 66),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "...................GGGD...........................UUI.................",
    "................YGGGGGG..........................MUIIIG...............",
    "...............YGGFB.................................BGF..............",
    "...............GGG....................................EGG.............",
    "..............GGGF....................................BIG.............",
    "..............GGGF.....................................IGI............",
    ".............IIFIG.....................................LIG............",
    ".............IFGGI.....................................LLG............",
    ".............IEGOI.....................................LLGF...........",
    ".............IEGOO.....................................OOGG...........",
    ".............IEGOPP....................................OOGF...........",
    ".............EEFPPP....................................PPG............",
    ".............EEFTTX....................................TTG............",
    "..............FFTXX....................................TTI............",
    "..............GFFYYX..................................YYOI............",
    "..............FGYYYY..................................YYO.............",
    "...............GGYYTP................................TTYI.............",
    "...............GGGTPPP..........WWWEEEEE.............TTII.............",
    "................FGPPLL.......DDWWWWFEBDEE...........OTLI..............",
    "................FGPPLLR......RDDBDBBBBABBEE........OOLF...............",
    ".................EFLLGRR....SREBBBBDDBDBBAB.......LLIFF...............",
    "..................EGLIGG...SSDABBDHHDMBDMABA......LIFE................",
    "...................EGIGIT..SSBBEBEEMDBBBBBBB.....LGGE.................",
    "....................EGGGIT.EBBDDBBABAAAAAAAA...OOGFE..................",
    ".....................FFEGIIEEHAAAAAAAAAAAABKK.OPDEE...................",
    "......................EDEILLEEHHAAAABDKKKAEEELPDDD....................",
    ".......................DBELLLFSCCAAAADDKDMJELLBBB.....................",
    "........................BBDLLESCMACQQHCCKJFGLEBB......................",
    ".........................BAAFEESSHHCQQHRKKDGBAB.......................",
    ".........................DBAAADSSEHHQQQERDBAAAB.......................",
    ".......................BRRDAABDHHHEHYXQFEDDBBBBB......................",
    ".....................BBBKDEEFIIHDHFGYXIIEEDFFEFBB.....................",
    "....................DBBKDDEEIEIHHHGGGOLFQEFDFFFFF.....................",
    "....................DDBJBWEEBFHHHMHGGOLCFFFFAFFFFS....................",
    "...................DEDJBBWPDBFCCCCEIGOKKCCMDDDFFBS....................",
    "..................DDDDBAMJPBFMCCCCCEIKKCCCCCDDDFAAD...................",
    "..................DFKAKBMJPKKCMCCCCCEDCCCCCFKDJAABE...................",
    ".................EEEDKBBAJNKKNCCCCCCJHCCCCCFRKJBBED...................",
    ".................FFEBKFBAANKKTNUHHUJUJHEMDJJRJJBBKDE..................",
    ".................GGGEKKDABNNETUUUUUUUJJJJJJNNNFAADKE..................",
    ".................GGJJKKDAAANNTUUUUUUUNJJJJJNEEAAADNK..................",
    "................GGGNNKEABAACRRUUUUUUUNJJJJJJEEAAAAEN..................",
    "................GLPDDBAABAAHHRNUUUNUUNMJJJKVCMAABEFEE.................",
    "................LPFBDDADBAABHMNNUUNMMCMJJKCCVBAABEEEI.................",
    "................LLDDDBDDBBAAAHHKUUUUKKJKMFCCVAAAADEFI.................",
    "................LDDDDKEDABAAMHCKUMCMMCCMKHCCBAABABEEE.................",
    "................OFDDKDDBDAAAAHEHUUNMMMJJJHCAAAABDABEE.................",
    "................OOSEBBAMBCEBAADHKUUNKKJJJMCAAAABDBAAB.................",
    "................OSSBAAABAABAABDKBUUUUUNJDBBAAAAAABDAA.................",
    "................EDABBADAABAIIEBBDDUUUUNFBEBAABEABABEA.................",
    "................EBRRDAFAAAACDIBMDDBEEEBDKKBAARRAABAAD.................",
    "................BBBFBADAAARCCCCBBBEDEEFKJKAARRDAABDEA.................",
    ".............WWJJBBBBABAMARCCCCLBCBEKKJJNDABRQDAAADFE.................",
    "........BBWNNWWWWVVVVVVBEEBCCCCLBACMMNJNJCABFQAAAABDHH................",
    "..CSSWWWWWWWSSWWXXXVVVVEBEEAACCIBAAMMMNUCCABFQAAAABBHHPPP.............",
    "..SSSSWWWTTPPPLWFXOOLEDCCADEBCCIAAACMMJUMCABFCADABBBHPTTOOO...........",
    "..SE..ABDEELLLLWWWFJOLLFDCAEEAAIAAAACMJJCAAAAAADABEHESWLLLOOOO........",
    ".II....AAABELLLWWWJFLLLIIIEEFDBIABBAACECCAAAFBADDAAESSWWLLRRFGGF......",
    ".ID...EDBDBBBLWWWPPOLIIJIFIIIFDFAADAEAABCADBAFCEEBCCDIOOLXXXRVVEBB....",
    ".AA.DDFDFBBFDBDWWAAAOOPJPOOIFADDBAAAEEHAABAAABDEGGCFIOOOLLIIOOOEEE....",
    ".FAADDDEENNDDGEBAAAADAPPTPJDAAFBDECACCHCCKEAAABDAFFFNNOLIIIOOOOEEE....",
    "FDAADFFLPNNNDGBAAACCAABATJAAACFEBEEMCCCCQKCCAAAFBAAANNPOOOOOOOBAA.....",
    "FBEAGFFLPNNNBAACDDACQAAADBACCCEEAEFIIMCQQQCCCADBFCAAANNPOEEOOBBFM.....",
    "FFEEGFEEENNBACQZZDDBCQCAAFDCQQCEDDGIILLQQQQCCDDBFFCCCABBBAAABFBLLL....",
    "DFEEDAAAAAAAHQQZHGGGDACAAEEQQQQIIABGLLLPQQQCCGFDARQQCCDBAACAABLLLL....",
    "FFJBAABDAAAHHQZHPGGBAAACAAEQQQQQAAAADLOOPTXXOGFEARRQQCEFACCDCAADLL....",
    ".JBABBDDACCZQZDPPMACCAAAACMQQQQQTMAACCCOPTXXOIIBABRQQQHAACCDDQCAAA....",
    ".BAAADFACCCZZQPPDACMMMCAACAAQQQQTAACCCQQQQTYOOCCAARRQQHRAAAFDKHCAA....",
    ".BBAOFFACCZZZXPPAACCMCCCAAADQQQQSSAACCQQbQQYOQQCCAARQCRKAAAAEKKHQC....",
    ".AAAOOBCECZZQXXCCMVMMCABMAMADDCCCOAAACQQbcccMbQCCAAACCKAAACCACKIHHA...",
    "..AXODEGLLZVVXXAMVVVMMJNNNNNBDCCDOAACCCQbcccbQQCAAAADCCDAAMCAABIFHH...",
    "..MXXEFGLLLCNTCAMMVMMDJJUUNNNDCCAADDCCQQQQQbQQQACDBEEAFBAACMMMABFFH...",
    "...IIFFDAADGTNAACCCCBJJJJNUUUJBAAADACCCQQCQbQQAAABBBEAFAAAMMMCCAFFF...",
    "....IEAAADGGGAACMVVMBKKJJNJUJNNDAFDACCCCCCAACCMAAABBCMBAAACCVVMCAEF...",
    "....F.BBEFGGEBACMVVVMAJJKJNUNJJJADBAAABMMCCCNNNNAANNNSSAMACCMVMMCAB...",
    "......DFFEB..AACMVMCCAABBKFDEFJJaaaSSSSSMMCCNNJNNNNNNNDDUUBCCMMVMCA...",
    "......FIFA..AACDACCMMCAABFBDDIJOOOaHDDDDDMCCNSSJFFFFEDDDUUUAACVMCAAB..",
    "......IIAA.AACHMMMVMMWPPHCMCDIILODLHHQHHHQQDLLEEEFFDBFBCKUJAACCAMMCE..",
    "......F..BAAAAHCCCVHWYYHMMMVXOOLLLLLLLLQQCCCAFFDADDBBEAAKJJAAAACCCCA..",
    ".........FDAABDAAMMHHYYMRVVXXTRLTTLJLLFFECCCAADBADBADDAAFFDHANNNCCCC..",
    ".........FFBBBAAACCLLLCMRMXYYRTTLLJJLFFFDEAAAADABEDABAAADEFHBENNXXMAC.",
    "..........IIBDAAACDLLCMMMMOORRTTLLLLFEDBDCAAABEBBAAABDEFFFFFEEHHHPPLA.",
    "..........FOFEAAAAFGFACMCCOORRIIGFFEDDBDBAAABDBAAABBDDSPPFFWEEERHMLLE.",
    "...........FOAABABFGACCCCCGFEEEGEEDDBBDBAABDAAAAAERRNSSSSYYNWEERMHBLL.",
    "............LODDADEEACCAEFGEEEFFFBDBDBAABDB.AABDHHRRRNSSSSNNLLOOMMCAI.",
    ".............LOBAEFBACCAAGGEEEFFBDBBAABDB...BDDHDHHRRREIIFENNFIIFCCABI",
    "..............OODFFAACAAAEEEEEFDBBAABDBA..AACBHHHDDDDFEEEHIIDDFFFBCAAB",
    "..............OOOFFAAAADFEBDDFDAAABDBAAA..CCCCCCEFDDDEDDHGIDQBDFEEACAA",
    "...............DPOEAAAAEEDBBEDAABDBAABBBBAAAAAACCABFFDBDGGDCCCAEEEAAAA",
    "................PPEAAAAEDBBEEBCDBAA..BBEEDBAAAAAAACAABEFEBCCCAAEBBAACC",
    ".................PAAAAEFFEEEAAA...BB..AAADFFFDBAAAAAADDBAAAAAABDEAAAC.",
    "..................AFBBBFDDBAAAA...DB..AAAAAABDEEFEBBDDBAAAAAABFEDACC..",
    "...................DDBD....ABAABA.DDAAAACCAAAAAAABBFEBBDDDDBDGEECC....",
    "...................BBA....AADAABCAEEAAAAACCQCCAAAAAAAABBBDDGGFDAA.....",
    "....................EB..AAAAEBACDCFAAAACCAQQbCACCAAAABAAA......A......",
    "....................EFAAAAAAEDCCCCCAAAACCCCQbbQQCAAAADBAB...ABD.......",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (70, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 70x96).
    scale=int   -> sprite de 70x96 px ampliado por un entero, sin márgenes.
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
