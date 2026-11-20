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
    "A": (92, 140, 221),
    "B": (221, 238, 252),
    "C": (27, 31, 39),
    "D": (30, 43, 68),
    "E": (52, 75, 116),
    "F": (43, 61, 95),
    "G": (58, 59, 60),
    "H": (46, 47, 47),
    "I": (88, 89, 90),
    "J": (59, 87, 135),
    "K": (67, 99, 152),
    "L": (72, 73, 74),
    "M": (15, 17, 23),
    "N": (78, 121, 194),
    "O": (77, 114, 175),
    "P": (88, 132, 206),
    "Q": (197, 212, 226),
    "R": (158, 186, 225),
    "S": (152, 160, 167),
    "T": (95, 103, 113),
    "U": (62, 102, 175),
    "V": (121, 130, 140),
    "W": (246, 249, 252),
    "X": (116, 119, 120),
    "Y": (250, 247, 235),
    "Z": (106, 129, 164),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "......................................EFFFD...............",
    "...................................EEEDDDDD...............",
    "..........EEF....................JEDEEAAADD...............",
    "........EFECCF.................FJDDEERAAAEE...............",
    ".......EECFFFF................FFFQWWRAAAAME...............",
    "......FFEMDFDF...............FDFQAAAAAAAAD................",
    ".....FFFEDFFF...............EFRRAAAAAAAADD................",
    "....JDFECEFFF..............EFRRAAAAAAAADDD................",
    "....JJFFFFDCE...........EEEEAAAAAAAAAAADF.................",
    "...KCFJDFFFEMEFFFZZ.....ESSYVAKKAAAAAAACD.........EFF.....",
    "...DKAAFPPMFMCCFFGHFEE.HHSSYVQYQAAAAAADCDE........EDF.....",
    "..JCAAAPAPMCFFHCCCCCETHMHYYQQQHYQAAAAAMEEE....EFE.FKDEMFK.",
    "..JJAAAFAAMDKDCCCMCCTSSIGHCCQYQYQAAAAAAAEE....FEFFCKEFFDK.",
    ".KDRAAADAAAADK..CCMMCLIIIIILXYYYYAAAAAAADN....EEEEMDECDFD.",
    ".KGRRAADAAAEE..FMCCCCCLIIIIILXYYYYBBAAAADN....EDFCCDDDFDDD",
    ".DKRAAAAAAADE..EECHCIIIIIIIIIILLYBBBBAAADD.....DFFMDDDDDCE",
    "DDAAAAAAAAFE.....FJCCGIIIIIIIIIILBBBBFDDCE.....FFFMJDDCFDE",
    "JGAAAAAAAAF........JEECMHHIIIIIGBBBBTDDDCECFFDFFFFJAAAFAKF",
    "JSBBBJJJADF...........EEBBBXXXBBBBBTCDDDCFMDEEFMKAAAAAAAKF",
    "JSBBBBBBBGO...........EEBBBBBBBBBBBBBBDCMC..EEAKKAAAANAAKF",
    "JFSSBBBBBHO............FBBBBBBBBBBBBBBBMCC..KCKAAAAAAFNAKF",
    "JJFNNFFBUDO............DHBBBBBBBBBBBBRMMF....KCAAAAAADAAKF",
    "JFNNNUUUUCF..........EEDDCBBBBBBBBBBRRME......FAAAAAAAAAKF",
    "JJNVVVVBBFF......CCEFMDFDDBBBBBBBBBBDDE.......DDAAAAAAAADF",
    "JVVBBBBBBFCFCCFKFCCEAAAAFBBBBBBBAABDDD........ODANNNNAASSF",
    "DDVSSSSBBAACCCCKKAAAAAAAFQBBBBBBAAAADDF.......OOYSSSSQBBSS",
    ".DDPPPPAAAAARBBRAAAAAAAFBBQRBBBAAAAAAFDF......OGYBBBBBQDD.",
    ".DDAAAAAAAAARRRAAAAAAAACBBRBBBBAAAAAAADFF.....FDNTTTTUUUD.",
    ".DCAAAAAAAAAAAAAANNJJADBBQQBBBAADAAAAAAADDF...FFNNUUUUUCL.",
    "..DDAAAAAAAAAAAUUJJFCMCBBBBBBQAADDAAAAAADDDFDFCFFDDDDUSLL.",
    "...FCAANNNNNKKFFMMCCCCBBBBBBBQAADCDPAAAARRDDDMFFBBBBBBSDE.",
    "....FDCDEEEFDCDFFM...DQBBBBBBAAACFDDPAAARRAAAFAABBBBBSGE..",
    ".....KKFDDDDKKK.....JGQWBBBBBAAFE.FFCAAAAAAAAAAAAJJJFDCE..",
    "....................JVWWBBBBRAACE..FFCAAAAAAAAAAAAAPKDD...",
    "....................JVWBBBBBRAAD....FFCAAAAAAAAAAAPKKMD...",
    "....................FWWBBBBBAAFF......CCDAAAAAAAAAUJDF....",
    "...................LLBWBBBBRAACF.......CFCFUUAAAAUJFDE....",
    "...................LBBBBBBBRAAF.........CKDCFFJJJEDCE.....",
    "...................DRBBBBBBAAEE...........KKKCMMMMEE......",
    "...................FRBBBBBBAADE..............KMMNN........",
    "..................TTBBBBBBRAAC..KKK.......................",
    "..................TTBWBBBBRAKFDFEKF.......................",
    "..................TTWWBBBBRADKCDFEDFFP....................",
    "..................TTWWBBBQANDFDFFMCFPDP...................",
    ".................PHBBBBBBQANCFEEMFFFFF....................",
    ".................PGBBBBBBQAACEEFEJJCMEE...................",
    ".................GGBBBBBBQAKDEEAEMMCEEE...................",
    ".................PGBBBBBBAAKMFAEDDDEJDE...................",
    ".................PGBBBBBBAAKFFFAAFDDDJ....................",
    "..................DBBBBBBAADCFAAJCCEE.....................",
    "..................FBBBBBBAAMDJFMJJ........................",
    "..................FFBBBBAAEMDDJJ..........................",
    "...................FCBRRAEMEE.............................",
    "...................HGC..MCME..............................",
    "..................GCLM..MLH...............................",
    "..................LHLM.MMLG...............................",
    "..................HLC..CGGG...............................",
    ".................HCHM..MHHG...............................",
    ".................GHLM..MHCH...............................",
    ".................GLHH..MMH................................",
    ".................CCCH..MMC................................",
    ".................HCC...MMC................................",
    "................GLLC..CMCC................................",
    "................GGGC..CGGC................................",
    "................GGCL..CGGG................................",
    "................GGCL..CGGG................................",
    "................HGML..CGGG................................",
    "...............IHHC...CGGL................................",
    "...............IHLH...CHHL................................",
    "...............IHLH...CHGL................................",
    "...............IGLH...CHGH................................",
    "...............LHGH...CMIC................................",
    "...............HLCG....CIC................................",
    "...............HIC.....CCC................................",
    "...............HIC.....CCC................................",
    "...............HHC.....CCMG...............................",
    "...............HIC.....HCCL...............................",
    "...............HIC.....IHLL...............................",
    "...............HHC.....IHLC...............................",
    "...............HIH.....IMGMG..............................",
    "...............HIC......HGCC..............................",
    "...............HGC......GGCC..............................",
    "...............HHCL.....GGCH..............................",
    "...............HLHL.....GCHH..............................",
    "...............HLCG......HHC..............................",
    "...............GHHG......HHM..............................",
    "...............HHLG......CGMG.............................",
    "...............HHLC......GGGG.............................",
    "..........HHHGGHCLMC.....GGHG.............................",
    ".........GHHHLLLIICC.....CMIHG............................",
    "........GGGGGHLIIICG....GHCIMH............................",
    "........GMGHGGGHMHG..HHGGGGIGH............................",
    ".........HHCCMCGG...HHHIGGGIIC............................",
    "...................HHHHIIIGHCH............................",
    "...................GMGCGCCMGGG............................",
    "....................HHHHG.................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (58, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 58x96).
    scale=int   -> sprite de 58x96 px ampliado por un entero, sin márgenes.
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
