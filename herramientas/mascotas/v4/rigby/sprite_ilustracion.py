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
    "A": (191, 133, 88),
    "B": (199, 186, 177),
    "C": (76, 60, 36),
    "D": (57, 42, 28),
    "E": (141, 98, 65),
    "F": (177, 124, 82),
    "G": (68, 49, 35),
    "H": (152, 106, 71),
    "I": (164, 114, 76),
    "J": (112, 79, 54),
    "K": (36, 27, 20),
    "L": (127, 89, 59),
    "M": (46, 35, 24),
    "N": (99, 69, 48),
    "O": (86, 62, 46),
    "P": (24, 17, 13),
    "Q": (249, 242, 230),
    "R": (198, 151, 113),
    "S": (10, 6, 4),
    "T": (184, 168, 155),
    "U": (144, 133, 125),
    "V": (220, 185, 156),
    "W": (227, 211, 195),
    "X": (95, 88, 85),
    "Y": (117, 110, 106),
    "Z": (132, 65, 86),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "............................................KKKEEEJ.........................................",
    ".........................................MEEDKMMMKJJ........................................",
    "......................................JOOOMGRRHMMMCGF.......................................",
    "...................................LLJOGOORRRAHHLDDDF.......................................",
    ".................................MLLGOJRRAAAAAHHLLLDI.......................................",
    "................................HOMGAAARAAAAAAAALGDI........................................",
    "..............................HHKGAAAAAAALKKCKCAGMI.........................................",
    "............................GHOKRWRAAAADPMLHHHHGGG......GHHH................................",
    "...........................GGPVVWRAAADMCIIG...HHGK.....EEMKNGOJJJ...........................",
    "..........................NNDVVVAAAODDDD.........KKEEOOOEVKNOJDKN...........................",
    ".........................NCOVWVAACGCDD..........KOXECODUVADKGRRNN...II......................",
    "........................NGNWWAAJMNNN...........KDXEEGKUAAASKRRRGCPNDDGI.....................",
    ".......................NDNNVAAMGJN...........EEOMAALSLAAAKDRAARSKNDNRPF.....................",
    "......................NNMAVAADJJK...........LGMKAAAALAAALDAAAACKGPNRPPF.....................",
    "......................NKRRAAKJJ............LGAACAAAAAAAALAAACCKKKIAAPPP.....................",
    "......................KCRAASJO............LGAAAAAAAAAAAAAOMGMMDKCIIIKP......KKJ.............",
    ".....................LGRRAADJ......EHHH...LKAAFAAGMKMAAAODKGUUKKMCIMNO.....JMKJJ............",
    "...ONLLLDG...........LCAAAPJ.......EDDCNNOKAAAFDDGMKMDMODKQQQQQKMKKNN.....JDMMSH............",
    "..ONMGGDDDDD........CCAAAOCJ......IMFDEKOCDAAFGGMMQTTOMDMQQQQQQQGDMN.....JMMGPSH............",
    ".JDOQWWVDCDOJ.......CCAAAKJ.......IPFGEEGSFAAAGKQQQQQQMMKBQQQQQQQDPP....JJKPPPKH............",
    "JCGQQQVVAAAGJJ......NOAAADJ.......IPAADOEKFAADDGQQQQUTQKKBQQQQQQGDKKEENNMKMSSPL.............",
    "HSAQQVAAIAAICCD.....NOAAGJD.......ICAAHDEEAAEDDUQQQQUTQGKKQQQQQQKKSKKPONAAADGLO.............",
    "HSAQVAAAAIAAIDDI....NOAAGJ.........EMHAEMAAAEDMUQQQQQQQGGKQQQQQMDGKIIAAAATTMOK..............",
    "HSAVAAAAAAAAADSI....NOAAGJ.........GEPLAEAAAAMDQQQQQQQQKDGMPPPMDDRAAAAATBTMOPKKFFFFFFFH.....",
    "HSAAAFAAAAAMMKSKJ...NOAAGJC.........MLPSAAAAAGCKQQQQQQMDGGMDDKDYRRRRBBBBTODPNNPSSSSSSPHHJ...",
    "HPAAAFAAAKDCCCCPJJ..NOAAAKJ.........KPPIAAAAAAMCKGUUQKDMAATTKUUYYUBBBBBBBSPMCAAAQQQQAAKPOJ..",
    "KLSAAAAMGCCCCCCDPJ..CCAAADJD........HPIIAAAAAAADCDMMDGMAAATTKKXYGPUBBBBBDEIAAAAAAAAAAAAAGJJ.",
    ".LKAFFDCCCCCCCCGPNNPMCAAAASJ........HKSKAAAAAAAAGKKKDDAATTTKDDXYGMBBBBBDEEIIAEEEEEEAAAAAAOJJ",
    ".DLSDDCCCCCDMDGGDPOPDOOAAAACOO......MGDFAAAAAAAAAFFFAATBTODZZZGGGMBBBYPMOGMDDGGGGGDGOEAAAAPH",
    "..LDDMCCCDDDAAAAAMOO.OGJAAAOOOOJ...JCDDFAAAAFFAAAAAARTBBODZZZZZNOMBBYSMMMMMIIFFFFGGGCDEAAAKH",
    "...DDPDCDDRVVRAAAAMO..JMAAAAACCJJDJJSSCGMAAAAAAAAAARTBBBKZZZZZZNKYBYPOMMM.........OGCCAAAAPH",
    "...PPSMMDRRRRAAAAAKNO.JOGFAAAAAADDDMSSAAAAAAAAAAAARTBBBXGZZZZZZMXBYPPC..........MMCDAAAAACOE",
    "....OMSOAARRAAAIIANGD..JJKFAAAAAAAAAAAAAAAAAAAAAAABBBBBXGZZZZZKXBYPPO.........KKMSDAAAAAADE.",
    ".....MMDAAAAAAAAAAKDD...JJPAAAAAAAAAAAAAAAAAAAAARBBBBBBTPOOOKKTTXPP.........GKKKWWAAAAACKEM.",
    ".....KMSAFFFAAAGDDKKKK...LJMDJAFFFFFFAACAAAAAAARBBBBBBBBTOOOUTTOKP.......CLLMGKWWAAAAJDDEE..",
    "......SSCAAAODMCCCGKCF....LJJOGDDDDDMDAAAAAAAAATBBBBBBBBBBBBBUGGP.....LLOCCRRVVAAAAODCJJ....",
    "......SSPAAMGCCCCCCMCF.......JJJDDPGDAAAAAAEAATBBBBBBBBBBBBBBDJJ....ENMLAARRRAAAOGDDOO......",
    ".......SSGMCCCCCCCCMCC.........PDCMAAAAAAAEAARBBBBBBBBBBBBBDKHJ....ENCMAAAAAAAGDCIDD........",
    ".......GSSGCCCCDKKKPCO.........POPAAAAFAAAAARBBBBBBBBBBBBBKDH......FPHHMAAAAKPLLI...........",
    "........SSDCGMDAIIIAMOO........OGAAAAFAAAAARBBQWBBBBBBBBTPCK.......FDHDIEFFKLLL.............",
    "........SKKDAAAAAAAAOOH.......OOOAAAAAAAAAARBQQWBBBBBBBTKDL.........HPIELLCCL...............",
    "........DLPEAAAAAAAAOOH.......OGORWAAAAAAARBWQWBBBBBBBTMDL...........EMKLLDL................",
    ".........LPEAAAAAFFAOOI......GOORWQAAAAAAABWQQBBBBBBBTTDL.............EFDDL.................",
    ".........LPEAAAAAFFAOOI......OKRRQWAAAAAAABQQWBBBBBBBTKK...............FFD..................",
    ".........LPEAAAAAFFAOOH.....JOCRQQAAAAAARBWQWBBBBBBBTOKK....................................",
    ".........LPPAAAAAAAFCOH.....JKRRQAAAAAAARBBWBBBBBBBBBKL.....................................",
    ".........LPPPAAAAAAAGOH....GKKRWWAAAAAAABBBBBBBBBBBTOCL.....................................",
    ".........LSDDMMCCOAADOH....HGKVVVAAAAAAABBBBBBBBBBBTGG......................................",
    "........LDMCCCCCCGGKDH.....HMVVVRAAAAAAABBBBBBBBBBTTGN......................................",
    "........ESCCCCCCCCCMGH.....IPVRRAAAEAAABBBBBBBBBBBTON......IISS.............................",
    "........ESKDCCCCCCCKCH....IDIAAAAAEFAAABBBBBBBBBBBTGG....GEPSSJJ............................",
    ".......GIMAADMMGGGDKKH....IMLAAAAAEFAABBBBBBBBBBBBYGG...HEPPPAMJ............................",
    ".......IPIAAAAAJJGMGK.....MMLAAAAAAAAABBBBBBBBBBBBYGG..HNCVVAAADJ...........................",
    ".......IKAAAAAAAAACGG....MNGAAIIAAAAAABBBBBBBBBBBBGGG.HONVVAAAACJ...........................",
    "......IIDAAAAAAAAAMOE....HGNAAIIAAAAAABBBBBBBBBBBUGOKOCNNVAAAAANN...........................",
    "......ISAAAAAAAAALME.....HGJAAFFAAAAAABBBBBBBBBBBUDOKGORRAADKAANN...........................",
    "......ESAAAAAAAAALMI.....IGJAAAAAAEAAABBBBBBBBBBBUDDCGRRAIDCDAANN...........................",
    "......ESAAAAAAAAALMI.....IGJAAAAAAEFAABBBBBBBBBBBUDDDRRAIMDDOLANNN..KFFK....................",
    "......ESGAAAAAAALDME.....IGJAAAAAAFAAABBBBBBBBBBBUMGDAAFGODMNLANNPHHKKKMK...................",
    "......ESDGDKMMMKDDPME....GGJAAIIAAAAAABBBBBBBBBBBUSGAAFCCJ.NNLANGNMGFFLKOK..................",
    "......ESDCCCCCCCCCMGG.....GDAAIIAAAAAABQQBBBBBBBBTMAAAADJ..EKAAOKAAAAALJKK..................",
    "......ESDCCCCCCCCCMGJ.....IMLAAEAAAAAABQQBBBBBBBBTTFAAKDD..EKAAFFAAAAGMPJH..................",
    "......EPMDCCCCCGMDGPJJ....IMLAAEAAAAAABQQQBBBBBBBTUAFACO...EKAAAAAAAHHGPH...................",
    "......KESGDKKPMOAAAGCJ....IMMAAAAAAAAAABQQBBBBBBBTUFAPP....EKAAAAAGPDGGOP...................",
    ".......EPEEFFFFAAVADDJJ....OPAAAAFAAAAABQQQBBBBBBUUUKNP....JODGKDNNPHHH.....................",
    ".......EMDHAAAAAAVVIDPONN..KKAAAFAAAAAABBQQBBBBBBUUOCN......JLLLNN..........................",
    "........EKEHAAIAAAIDCGKPNSSSKGAAAAFAAAAABBBBBBBBUUUDI.......................................",
    "........ESEEAAIAAIDCCCCMKSSSSPHAAFAAAAAABBBBBBBTUUPII.......................................",
    "........GEPLLHAALDCCCCDKAAASMKGHAAAAAAAAABBBBBTUUOME........................................",
    ".........GGPLLHLKCCCCDDAQQAAMCKCIAAAAHAAAUBBUUUUOKE.........................................",
    "..........JPKLLKCCCCGAAAAAAAGCCSIIAAAAHAAAUUUUUMKK..........................................",
    "..........JJPKMDDGCCMAAIIIAAAGCMSIIAAAAAAAUUUGPII...........................................",
    "...........GPPSMDMDGEAAAAAAAADDDMSIIAAAAAAAGPKII............................................",
    "............PPGPKKMKEEEFFFFAEDKKKPPCAAAAASMMPP..............................................",
    "..............JJMPKPEEEEEEEEDCPPMPEKOAAAAPPP................................................",
    "...............JJJGDDGGGGGGGMDGPPE.HMHRAAADP................................................",
    ".................JJDCCGDDDGCJJII....HDHRAASD................................................",
    ".....................CFFFFFF........GJGVRADDD...............................................",
    ".....................................JGVVAIPF...............................................",
    "......................................OVVAIPF...............................................",
    "......................................NOAAIKF...............................................",
    ".....................................NNOAAIKF...............................................",
    ".....................................NKAAAGGF...............................................",
    ".....................................KKAAASH................................................",
    "....................................KKKVACGH................................................",
    "...................................KKDVAAPH.................................................",
    "...................................KSRRACPP.................................................",
    "..................................KOAAAAGP..................................................",
    ".................................KKDAAAGODO.................................................",
    ".................................KKAAAASKDGIII..............................................",
    "................................JJJAAAIIFAADPII.............................................",
    "................................JDJAAAAAAFAADIOO............................................",
    "................................JOKJJAAAAACDCGO.............................................",
    ".................................JJOJKGGAAAKKKK.............................................",
    "....................................JJGGMPKDPK..............................................",
    ".......................................OPEEEE...............................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (92, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 92x96).
    scale=int   -> sprite de 92x96 px ampliado por un entero, sin márgenes.
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
