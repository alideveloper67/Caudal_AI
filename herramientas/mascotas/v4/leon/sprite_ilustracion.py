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
    "A": (252, 185, 194),
    "B": (249, 128, 157),
    "C": (20, 5, 7),
    "D": (252, 224, 227),
    "E": (232, 112, 139),
    "F": (61, 33, 37),
    "G": (33, 14, 17),
    "H": (251, 198, 205),
    "I": (224, 92, 123),
    "J": (46, 24, 28),
    "K": (248, 170, 179),
    "L": (251, 212, 217),
    "M": (245, 150, 163),
    "N": (76, 42, 48),
    "O": (98, 49, 57),
    "P": (210, 81, 110),
    "Q": (123, 58, 71),
    "R": (152, 70, 87),
    "S": (174, 83, 103),
    "T": (197, 103, 124),
    "U": (21, 18, 24),
    "V": (252, 246, 248),
    "W": (151, 113, 118),
    "X": (110, 83, 87),
    "Y": (216, 163, 169),
    "Z": (178, 143, 148),
    "a": (219, 203, 206),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "................................NNNFFFFFFJJFF.......................................................................",
    "...........................NNFFGCCCCCCCCCCCCCJFFN...................................................................",
    ".........................NJCCCCGSSCCCHHHHHHCGCCCCGFN................................................................",
    "........................FGCCRRWWLHLLHHHHHHHHYYYYCCCGGN..............................................................",
    "......................OJCCNCRRLLHHHHDDHHAAAAHHHAAZZFCCJNO...........................................................",
    ".....................FGCXCCAHHAAHHDDVVVDDLHAAAAAHHZZCOCCGFO.........................................................",
    "....................JGCXLLHAAALLVVVVVVVDDDLHAAAAAAAAAAXXGGJF........................................................",
    "...................JGGGLLHAHDDVVVVVDDDDHHHHHAAAAAAAAAHLLLXCGFO......................................................",
    "..................JGCALAAAHDVVVVVDDAAAAAAAAAAAAAAAAAAAHHLLXFCGJNO...................................................",
    ".................JGFAAAAALDVVVVVAAAAAAAAAAAAAAAAAAAAAAAAHLHLXXCGGJJ.................................................",
    "................JGNAAAAALVVVVVVAAAAAAAAAAAAAAAAAAAAAAAAAAAHLLXXXOGGJC...JGGGJJ...............................JGGJ...",
    "...............NGJDDAAAHVVVDAAAAAAAAAAAAHHHHHHAAAAAAAAAAAAAAAALLDDOJGJJJGJNNCF..............................FCNJGN..",
    "...............GCXDAAAHVVVDAAAAAAAAAAADDDDDDDDHHHAAAAAAAAAAAAAAAADDDFFFJJJJYCF..............................JCCCCJ..",
    "..............NGXDLAAADVVAAAAAAAAAADDDDDDAAAADDDDDAAAAAAAAAAAAAAAAAADDDDDAAYCF............................FJCOCCFGN.",
    "..............JCXLAAAADAAAAAAAAAAADDDDAAAAAAAAADDDDDDAAAAAAAAAAAAAAAAAAAAAACCF.........................FFJGCGLLBRCN.",
    ".............NCXLAAAAAAAAAAAAAAHLDDDAAAAAAAAAAAAAADDDDDAAAAAAAAAAAAAAAAAAAACCF.......................FJCCCFLLLLBRCF.",
    ".............FCWLAAAOXXAAAAAAAHDDLAAAAAAAAAAAAAAAAAADDDDAAAAAAAAAAAAAAAAAAAGGN.....................NGCCNCHLLHLLBBCG.",
    "............NGGWLAAUUUUUXAAAAADDLAAAAAAUUUUAAAAAAAAAAHDDDLHAAAAAAAAAAAAAAKACJ.....................FGCCCCLHHLHHMMBGGN",
    "............NCWLLAUFUTTUUXAAAHDHAAAAAAUFUONUNAAAAAAAAAHHLDLHAAAAAAAAAAAAKSCGF.....................FCCCHLVVVVHHMMAZCF",
    "............NCZLAFFBBBBBFJAAAAHAAAAAAUOBBBBBUAAAAAAAAAAAHLDLHAAAAAAAAAAASFCF.....................FGOHHLVVVLLHAMAAZCF",
    "............NCZLAUBBBBBEJOAAAHAAAAAAUFEBBBBBOJYAAAAAAAAAAHLDLLAAAAAAAAAASCGF.....................JCHHLVVLLAAAKKAAZCF",
    "........N..FJCZLAUBBBBEEELKKKKKKKKKANEEBBBBBTUYAAAAAAAAAAAHLDDLLHAAAMMMACCF.....................JGCHLVVVAAAAAAAAAZCF",
    "......UGGGGCCCZAAUBBBEDELWWXXXXXRMMKDDBBBBBBTUYAAAAAAAAAAAAAKLDDLHHMMAAACCF.....................JJHHDVVAAAAAAAAAACCF",
    "....FGGNOXXOJCWAAJFEEEDLWWNUUUUUURRDDDMMBBBBTUYAAAAAAAAAAAAKKKLLLLLHAAACCGN.....................GJJADHAAAAAAAAAAWCGN",
    "..NFGFFALLLAAWWKAWUOEEWWUFBBBBBBRFUWHHDDBBBTJYAAAAAAAAAAAAAAAKKKKAAAAAACCF......................GJAAHHAAAAAAAAKKWCJ.",
    ".OFGOLLAAAAAAAKKAAWUUWWUBBBBBBBBBBBUWHHDDBBJUYAAAAAAAAAAAAAAAAAAAAAAAACCGN......................GJAAAAAAAAAAAKKKOCN.",
    "NGCLLLAAAAAAAAHHAAAAWSUSBBBBBBBBBBBRUWHDDNUUZAAAAAAAAAAAAAAAAAAAAAAAACFCF.......................GJAAAAAAAAAAMMMOCG..",
    "FCCLLDDDAAAAAAAAAAAAACSBBBBBBBBBBBBBRUWHKKZZAAAAAAAAAAAAAAAAAAAAAAAACCCJ........................FGNAMEAAAAMMBBOCJO..",
    "FCJRAAHDDAAAAAAAAAAAAJBBBBBBBBBBBBBBBJWAKKAAAAAAAAAAAAAAAAKAMMAMMAFFGCF.........................CJCEEMAAABBFFFGGJ...",
    "FCCJRAAHDDAAAAAAAAAAAJEEBBBBBBBBTTTBBBUZAAAAAAAAAAAAAAAAAAKMMMNNNFCCJGU..........................JGCEMMSOONFCCGN....",
    ".NJCAAAADDAAAAAADLAAJJUUBBBBBBBUUUUBBEUZAAAAADDDDDDAAAAAAAAAAMACCCGJNJJFFFFFFFFFFFFNN.............FCMMSJCCCGGN......",
    "..OGFAAAADHAAALDLAAAJFZOUBBBBBUUaaUUEEUAAAAAAAAAAADDDDDAAAAAAAAACNQQCCCCCCCCCCCCCCCCGN............FCBMSCGGFN........",
    "...GCOAAAHAAADDLAAAAJFZUUBBBBJUUVVVFEEFAAAAAAAAAAAADDDDDAAAAAAAAAAAEEEEEEEEEEEEEEEOCCGJN..........FCBMMNGJ..........",
    "...NCOAAAAAADDDAAAAAAJZJUOBBSJJUVVVNEEDLLAAAAAAAAAAAAALDDLAAAAAAAAAEEBBBBBBALLEBBBEECCCGF.........FCCMMMCJ..........",
    "....GOAAAAALDLAAAAAAAFJJJBBBSJJVVVVVEEDLLHAAAAAAAAAAAAALDDLAAAAAAAAKEEBBBMAAAVVDDBBBETTCCJ........FCGTMMFGF.........",
    "....GOAAAAADLHAAAAAAACJNBBBBEJJVVVOBEEHHHHHAAAAAAAAAAAAALDDAAAAAAAAAKEBBBBMMMKKVVVDBBBBTCCF........JCTBBBCJ.........",
    "....GOAAAADDHAAAAAAAOBBBBBBBBEBNOBBBEEHAAAAAAAAAAAAAAAAAALDLAAAAAAAAABEBBBBBBBBMMBBDLBBBTJCG.......FCOTBBOCN........",
    "....GOAAAKLDHAAAAAAAFBBBBBBBBBBBBBBBEEEAAAAAAAAAAAAAAAAAAHLLAAAAAAAAAKBEBBBBBBBBBBBBLLBBBTNCJ......FGCRBBBCF........",
    "....GOAAAKLDHAAAAAAOBBBBBBBBBBBBBBBEEDDLHAAAAAAAAAAAAAAAAAHLAAAAAAAAAAKBEBBBBBBBBBBBBBBBBBTFCJ......FGCRBBBGF.......",
    "....GOAAAKKDHAAAAAAOBBBBBBBBBBBBBBBMDLLLHAAAAAAAAAAAAAAAAAHLAAAAAAAAAAAKBBBBBBBBBBBBBBBBBBBSFCN......NCCBBTCF.......",
    "....GFAAAKKLLHAAAAGROOOOOQQQBBBBBBBMHHAAAAAAAAAAAAAAAAAAAAHHAAAAAHHHHHAAAABEBBBBBBBBBBBBKBEESJGN.....NGCIBTCF.......",
    "....GCJAAAKHLLAAANNROOOOOOOOOBBBBBBBHHAAAAAAAAAAAAAAAAAAAAAAAAAALDDLLLHAAAAAEBBBBBBBBBBKKBBBBBCJ......FCIBTCF.......",
    "....FGJAAAHALAAAANSSOOOOOOOOBBBBBBTJBBMMKAAAAAAAAAAAAAAAAAAAAAADDLLAAAAAAABBBBBBBBBBBBBBBBBOBBOCF.....JCIBTCF.......",
    ".....GJAAADHAAAAANSBBOOOOOONBBBBBTOUMMMKAAAAAAAAAAAAAAAAAAAAAAADDKKAAAAAIPPPBBBBBBBBBBBBBBBOEBBCGF...FGNEBTCF.......",
    ".....GGAAKDDHAAAAOBBBBONNOBBBBBBBOUAAAAAAAAAAAAAAAAAAAHAAAAAAAHDDKKAAAAPPIIBBBBBBBBBBBBBBBBEOEBBCCJFJCCBBENCF.......",
    ".....JCJAKDDDAAAAACBBBBQQBBBBBBBBOAAAAAAAAAAAAAAAAAAADHAAAAAAHDDAAAAAAPPPIBBBBBBBBBBBBBBBBBIFIBBBNCCCOBBBECGJ.......",
    "......GGAAKDDDAAAAACBBQTTQBBBBBGAAAAAAAAAAAAAAAAAAAADDHAAAAAHDDDKAAAAPPIIBBBBBBBBBBBBBBBBBBIGFIBBBTTEEBBECCF........",
    "......GGGKKALDDLAAAYCCJSSSQFJCCAAAAAAAAAAAAAAAAAAAADDDAAAHDDDDDKAAAAEPPIBBBBBBBBBBBBBBBBBBBECCFIBBBBBBBBGCGF........",
    "......JGCKAKALDLAAAAYYJJGGGGJAAAAAAAAAAAAAAAAAAAAADDDAKAHDDDDDKKAAAEPPIEBBBBBPBBBBBBBBBBBBBECCCGJBBBBBBGGGF.........",
    ".......FCCKAKMDDLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADDDDDDKKAAHMMMMAAAAAPPPEBBBBBBPBBBBBBBBBBBBBECGJCCFNNNNJCJF..........",
    ".......JGCYAKMDDDLAAAAAAAAAAAAAAAAAAAAAAAAAADDDDDDDDKKAAAKKAAAAAAAPPPEBBBBBBPPBBBBBBBBBBBBBEPCJUJCCCCCGJN...........",
    "........NCOYAAKDDDDLAAAAAAAAAAAAAAAAAAAAAAAHDKKKKKKKKAAAAAAAAAAAEIPPEBBBBBBEJRBBBBBBBBBBBBBEPCF.ONNNNNO.............",
    ".........JCAAAKMDDDDLLAAAAAAAAAAAAAAAAAAAAAHDMMMMMKKAAAAAAAAAAAEPPIEBBBBBBBEURBBBBBBBBBBBBBEPCF.....................",
    ".........FGGGKKKMMMMMDAAAHDAAAAAAAAAAAAAAADDDMKKAAAAAAAAAAAAAAPPPPEBBBBBBBBEUQBBBBBBBBBBBBBEPCF.....................",
    "..........FGGJKMMMEMMDAAAHHDAAAAAAAAAAAALDDDDMKAAAAAAAAAAAAAAPPPPEBBBBBBBBBBUQBBBBBBBBBBBBBBECJ.....................",
    "...........JGCJOMMEAAADAAAADDAAAAAHLLLLLDDDDKKAAAAAAAAAAAAAPPPPEEBBBBBBBBBBPUQPBBBBBBBBBBBBBEECF....................",
    "............FJCGOOOAAAHHHAADDAAAAAAHLAAAAAAKKAAAAAAAAAAAAPPPPPEBBBBBBBBBBBBPNFPIBBBBBBBBBBBBBTFCF...................",
    "..............FGCCCOAAAHAAAADDAAAAAAHKMMMMMKAAAAAAAAEEPPPPIIPEBBBBBBBBBBBBEIIGPIIBBBBBBBBBBBMMTFGJ..................",
    "................FGCNAAAAAAMMDDAAAAAAAAKKKKKAAAAAAEEEPPPPIEEBOEBBBBBBBBBBBEIIIOOPIEBBBBBBBBBBMMMFFGJ.................",
    ".................NGFAAAAKKMMMDHAAAAAAAAAAAAAAAUAPPPPPIIIEBBBTBBBBBBBBBBBEIIIIIJSIIEBBBBBBBBBBHHMFGGJ................",
    "..................JGAAAAAAKMMDDHAAAAAAAAAAAAYCIIIIIIIBBBBBBBTFBBBBBBBBBEIIIIIIOFSIEBBBBBBBBBBMDHBGJG................",
    "..................JGFKAAAAAKMDDDHAAAAAAAAAAYGIIIIBBBBBBBBBBBTFBBBBBBBBIIIIIIIPCGRIIEBBBBBBBBBBMDBBNCG...............",
    "...................GJKKAAAAAMMLDDDAAAAAAAAAYGIIIBBBBBBBBBBBBTFBBBBBIIIIIIIIIPCCCCRIIIBBBBBBBBBBMDBBOGO..............",
    "...................JCGMKAAAAKMMLDDDLAAAAAAAYGIIBBBBBBBBBBBBBTJEEEIIIIIIIIIIJJCGJGJRIIIEBBBBBBBBBBBBOCO..............",
    "....................JCQMMAAAAKMKKKADLAAAAAAYGIEBBBBBBBBBBBBBTJIIIIIIIIIIIONCGG..JCFIIIIEEBBBBBBBBBBOCO..............",
    "....................JGCQRAAAAAKMMMMADHAAAAAYGGEBMKBBBBBBBBBBTJIIIIIIIIIQOFCGJ....JCJOIIIIEEBBBBBBBBQCG..............",
    ".....................FGCGRMAAAAAKKMMDDHHAAAAYGEMKDBBBBBBBBBBJJIIIIIIIIQGOCCF......JGCCRRRPIEBBBBBBBBQGN.............",
    "......................NCNRPMAAAAAAKMMDDDLHHHHFNNDVBBBBBBBBBBNIIIIIPIIOFQPRCF.......NFGCCCPIEBBBBBBBBQCN.............",
    ".....................JGCEPPPMKAAAAAKMMDLDDLLHNNMVDBBBBBBBBBSFIIIPPNGGPPPPRCF.........FJCCPIIEBBBBBBBQCN.............",
    ".....................FCEEEIPSSKAAAAAKMMMMMMMMGBMVBBBBBBBBBESNPPPGCCPPPPPPSCN...........JCIIIEBBBBBBBQCN.............",
    "....................FGGBBEEIISSSAKKAAAMMMMMMCBMMDBBBBBBBBEERCCCCPPPPPIIESFGN...........GGGIIEBBBBBBBQCN.............",
    "....................JGMDDEMEIIPPSPPAAAAAAKKKCCDDMBBBBBBBEERCCCCFPPPPIIEERCJ.............JGIIEBBBBBBBQCN.............",
    "...................JGFMDDMBBEIIIPPPFNAAAAAKKCBDDBBBBBBBBEIRCJGGFPPIIEEEERCF.............FGIIEBBBBBBBQCN.............",
    "...................GJMMDBBBBBEIIIISCCOOAAKKCOBDBBBBBBBBBEIRCFCFIIIEEEEEEFGN..............GJIEBBBBBBBQCN.............",
    "...................GFBHBBBBBBBEIISNCGGCGACOCCMBBBBBBBBBEIINGFGOEEEEEEEEECG...............JJIEBBBBBBBQCN.............",
    "...................GNBHBBBBBBBBESOCUUNJGCCCCSMBBBBBBBBBEIQCFGFEEEEEEEEEECF...............JJEEBBBBBBBQCN.............",
    "...................GNBBBBBBBBBBBBBCUF..FFJJCSKKBBBBBBBBEIQCFCFEEEEEEEEENCN..............JGJEBBBBBBBBQCN.............",
    "...................GNMMBBBBBBBBBBBBCN....FCCMKBBBBBBBBBEQOCGFEEEEEEEEERCGF..............FCGBBBBBBBBBQCN.............",
    "...................GNBBBBBBBBBBBBBTCF....FCSMKBBBBBBBBEIQCJCQEEOEEQEEERCF..............FGGEBBBBBBBBBQCN.............",
    "...................GFBBBBBBBBBBBBBTCF....FCSMKBBBBBBBBEIQCFCQENEEOQEEEJCN..............FCBBEEBBBBBBBOCN.............",
    "...................JCFBBBBBBBBBBBBSCF...NJGSMMBBBBBBBEIIQCNCQEFEEFEEEFCJ...............JGBBFBBBUBBBOCGO.............",
    "...................JGJBBBBBBBBBBIISCF...NCSBBBBBBBBBBEIIFGOGGFGQQGQQFCG................JGBBBBBOBBBBOGF..............",
    "....................JGFEBOTBBGBBESOCF...FCSBBBBBBBBBBEIOCGJFGCCCCCCCGJ.................FGGBTBBNBBTOJGO..............",
    ".....................JCOETOBBNEEERCGF...GJBBBBBBBBBBBIICCF..NNFFFFFFN..................FCCFCTTFTTCCGF...............",
    ".....................OJGOONEEEJERNGN...NCSBBBBBBBBBBBIIOCN..............................NGCCCCCCCCGF................",
    ".......................NJCCCCCCCCGF....FCSBBBBBBBBBBIIOCG................................JFFFFJFFFJ.................",
    ".........................JJJJJJJFC....NGCSBBBBBBBBBBIIOCN...........................................................",
    "......................................JCBBBBBBBBBBBBIIOCN...........................................................",
    ".....................................FGBEBBBBBBBBBBBIIFGN...........................................................",
    ".....................................FCTBENBBBBFBBBIINCG............................................................",
    ".....................................FCTBBBBBBNBBBBIINCN............................................................",
    ".....................................FCTBOBBBBNBBBEIOGJO............................................................",
    ".....................................FCCFOBBBBFEEEICJCF.............................................................",
    ".....................................FGCFFCSSCJSSRRCCJ..............................................................",
    "......................................NJCCCCCCCCCCCCF...............................................................",
    "........................................FFJJJJJJJJFF................................................................",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (116, 96)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 116x96).
    scale=int   -> sprite de 116x96 px ampliado por un entero, sin márgenes.
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
