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
    "A": (3, 22, 45),
    "B": (251, 146, 9),
    "C": (4, 9, 17),
    "D": (194, 53, 2),
    "E": (5, 31, 89),
    "F": (158, 36, 4),
    "G": (3, 51, 133),
    "H": (212, 84, 4),
    "I": (235, 116, 5),
    "J": (10, 83, 169),
    "K": (46, 22, 25),
    "L": (242, 177, 111),
    "M": (80, 35, 20),
    "N": (117, 21, 7),
    "O": (133, 76, 31),
    "P": (10, 211, 248),
    "Q": (244, 209, 171),
    "R": (8, 127, 186),
    "S": (16, 65, 99),
    "T": (205, 121, 65),
    "U": (6, 170, 223),
    "V": (86, 74, 80),
    "W": (160, 136, 115),
    "X": (64, 147, 193),
    "Y": (46, 110, 120),
    "Z": (208, 8, 11),
    "a": (89, 229, 247),
    "b": (186, 243, 251),
    "c": (250, 241, 229),
    "d": (177, 179, 183),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    ".........CCCC.....CAACC....................",
    "........CAAAACC...AASAAC...................",
    "........AAAYAAAACCCAPRAAC..................",
    "........CAYPPUSSAACARPRAAC.................",
    ".........CEUUPPaSSAARRPXAAC................",
    ".........CARURUPabXARRRPXAAC...............",
    ".........CARURJUPabXEGRPPAACCC..C..........",
    "....CC.CCCARUUJGGPabXEGPPAAAAC.ASC.........",
    "...CCSAAAAARUJJGGGPaaSGPPPASACCSYYAC.......",
    "..AXSESSAARUUGJEGGGPPPEJPPSSSACCASXA.......",
    ".CXXSSUaaaPPUGGEEGGPPPSJPPSRAACCCCXA.......",
    ".CXEAASUUPPaPPPEEGGGPPRGPPRPPACCACSC.......",
    "..ACCCARJJPPaaPPSEGGRRRRUUPPPAAASAC........",
    ".....CAARGJPPPaPUEEGRPRJJRPPUAAARAC........",
    "...CCCAAJJGGJPPPUJERabPJGRRUGAARRAC........",
    "..CAAAASERGGGJRRGJGPbaSEGRRRSAAPRAC........",
    ".CAAYYPPPRGGEGGGJJJPaaMKGRRRUPPASAAS.......",
    ".CAASPPPPPRGEEEJJJGPUaTTERRGUUSSAAAAC......",
    "..CCASPRUUPPJEEJPGMUSSQLLSSGUSGSESSAC......",
    "...CAASRJGRRGJEJPSSSSdQLSSKEUSJPPAAAC......",
    "....CCAEJJGEGGEAVVSSdSWWWKKGGJJPAAAC.......",
    "......CAAGJGEEAVVVLVVVWMYKMGEJJJAAC........",
    "......CAACGGGEVVKLLLVQQQYKKEEGEAAC.........",
    "...CEECASAGGGGAVKWLQQVWWVQKGAAAAC..........",
    "..CSCCCAAAEGGEEVWTTQQVWVWQKGSACC...........",
    ".CEXACCCCCAAAAGEAMOTQQQWQVAAACC............",
    ".CXXACCCCCCAAAAAAMTOOQQQVAACC..............",
    "..A..ACCCCACACKCKOLLOMMKAAA................",
    "......AAAMOOTBHIOOLLWTTOCMKAA..............",
    ".......AKKMTBBIHIHMWWWLLOKKMKAA............",
    "......AEKJGEOBBBHIOEWWLLLWKIIBOA...........",
    "......AAMQJJEOBBBIIOESGGWGGIIBBOA..........",
    ".....ACKQQQGGABBIBIBOEGGGGEMBIBOEA.........",
    "....AKLLLQQMEEMIDBBIBOGEEEGIBBBMGAA........",
    "...AVLLQLLQQMEAADBBBIBMGEEAIIBBKEKA........",
    "..AVLLQQLccQTCAFFBBLBIIMGEIIIIKAKWC........",
    "..AWLQQTQcQLTCANFHIBLBIIAKIVVWMKTLWA.......",
    ".AWLQLQTLLLTKAKNHIHIBBIHHHOVVWKTQLQWA......",
    "AWLLLQQWLLLKKCNFIIIDDIBHHHOWVWKTQQLQKA.....",
    "AWLLLQQQWCAACFFFDIIBDFIBHHHVWVMTTTTQLA.....",
    "AKLLLLQQQMACAKFFFDDIBFFHHHFHMFCMTTQQLAA....",
    ".AKTLQLQQWCACAMFNFNKNFKNNMFNHMAATQQLTAA....",
    "..AOTLQLWWJAAAACCAEJGGGAJJAEKAAKTQLLTCA....",
    "...KOTTLSJJJEVVKEAEGJGEESAEGAAAJJLLLMA.....",
    "....AMOOGGJJQQQQAAEEGGEGAAEEAAVJJGLLA......",
    ".....AAAEEGQQQQQQMNNNFKJACESMAVVGECA.......",
    ".......AAEETQQQQONDIFFEJAMEJOOLTEAA........",
    ".........AMTLQQQODHIDEEJSFEJONLTCA.........",
    "..........AMTLLONHBDIIEGSEEGSHOOA..........",
    "...........ACMOKHBBFBGGJSHEGGHKA...........",
    "............CMMFBBBBBBGJSHKGGOOA...........",
    "...........AKHHBBBBBBMJJSHMGJSOC...........",
    "...........CHHHBBBBBIKJJSSMEJGHM...........",
    "..........AAHHBBLBBBIAJJSFNEJJHHA..........",
    "..........AAIHBBLLBBIEJJSFFEJRIIC..........",
    "..........AAHIBLLBBINEJJSNDAGRGIOA.........",
    ".........AODDBBLLBBDMEJJEFDAEEEOOA.........",
    ".........AOHDBBLBBHDKEJJGFDKEKFBBM.........",
    "........AMFHDBBBBBHDFMEJGDHNNDIBBM.........",
    ".......AMBDHDBBBBHDHFFKAEFDHDIBBBMA........",
    ".......ABBHDDBBIHDHBHNCNMDDBIIBBBIC........",
    ".......MBBBDDDIHDHBHFKKNNFDHBBBBBIC........",
    ".......MILBDDDDDBBHFMCNNDFDDHBBBBCC........",
    ".......KHILBDFDBBIDNMCNFDIFDDHBBICCA.......",
    "......AMHDLLBBBBIDFNNAMDFIIFDDHIHFAA.......",
    "......CHHDIBBBBDDFFDKAKFDDIIDDDDDHBK.......",
    ".....AKIHFDIBBDDDFHDC.ANDDDBBBDFDBBMA......",
    "....AKBBINDDDDDFFBHKA.ANDFDHBBBBBLBMA......",
    "....AKBBBDFDDFFDBHFC..ANDDFDHIBLLBHFA......",
    "....KKIBBBDFFFBBHFKA..AFDDHFDDIBBHDFOA.....",
    "....KBHIBBBHHBBHFNC...AFDHBHFDDDDDFBOA.....",
    "...AKBHDBBBBBBHFFDC...AFDDHBHFDDDFBBOA.....",
    "...KKIHDBBBBBDFFIDC...AKDFDHBBBFFDBBMA.....",
    "..AKBHINDBBBDNFBIFA....AFDFDDBBBBBBHHK.....",
    ".AMBBHBNFDDFNHBIFC.....ANHHFFDBBBBHFKK.....",
    ".AKBBHBNNFFFBBHFFC.....CDDIIFFDDHHFFKK.....",
    "..ANBHIINNFBBDFFDC.....CDDDBBINFDDNKKA.....",
    "...CDDFINHBBNFDDFA.....AKDFFIBINNMMKK......",
    "....CNNNHHBNFDDFC.......ANFFNFNFKMNMA......",
    "....CNNKMMCMFFNK.........AKMMKNNFFFKA......",
    "....AGKNNNNNNCA...........ACKKKESEFKA......",
    "...AAXGZEEAACA.............CEAEEXGNFA......",
    "...AXXEZGGAAC..............AAAEGXJEZA......",
    "...CXGGZGGAAA..............AAAAEJJEZCA.....",
    "...AAGNNGEACA...............CEAEGGGZKA.....",
    "...AEEZAGAAC................AAAAEEENKKA....",
    "...KKAFAAACA.................CMKKKMOTTK....",
    "..AOOOTOMMOA.................KKTTTTONCA....",
    "...COMMTOOMA.................ACACCMEMFC....",
    "..AEEZEAACA..................AAAAEGGGNFCA..",
    ".AEJEFGEAAC..................CEAAEGGGJJZKA.",
    "AAJJZGGEAAC..................CKAAAEEGJGSZKA",
    "AGJJZGGEAKC..................ANFFNNKEAEEMFA",
    "AMKFNAKMNNC...................ACCKMNZZZZZNC",
    "AKZZZZZKCA........................AACCCCCA.",
    ".ACCCCCA...................................",
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
