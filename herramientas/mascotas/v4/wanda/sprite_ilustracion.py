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
    "A": (48, 4, 7),
    "B": (73, 7, 10),
    "C": (103, 5, 18),
    "D": (20, 2, 3),
    "E": (136, 7, 24),
    "F": (181, 9, 24),
    "G": (110, 33, 5),
    "H": (156, 56, 11),
    "I": (119, 38, 40),
    "J": (75, 32, 27),
    "K": (27, 20, 24),
    "L": (249, 172, 121),
    "M": (198, 73, 7),
    "N": (168, 51, 65),
    "O": (236, 149, 103),
    "P": (128, 76, 68),
    "Q": (232, 101, 15),
    "R": (96, 63, 55),
    "S": (173, 94, 51),
    "T": (216, 94, 91),
    "U": (221, 43, 44),
    "V": (152, 102, 97),
    "W": (236, 130, 56),
    "X": (177, 132, 121),
    "Y": (221, 170, 159),
    "Z": (242, 207, 184),
    "a": (227, 7, 8),
    "b": (252, 240, 238),
}

# Cada fila = una fila de píxeles lógicos; cada letra = un color de PALETTE.
ROWS = [
    "........DP..................................................................................",
    "......BBKPY...................................HHHWWOOO......................................",
    "......IKKIYA..........................V...SMMHHGHHHOOLX...TT................................",
    "...TTKKKKJAA..........................V..SQGMHHHGHHLLQWX..TV................................",
    "...TTRKRRRTX..........................NKSQHGGHHHGHHHWWQHIKVV................................",
    "....aRRKRRTX.........................NINNHBGQQWHGGGHWHHHBIFV................................",
    "....CaLRKIUV.........................IENJBHMMQWWHGGWWWGBIFIV................................",
    "JJJDDKKLRUUV........................ICFBNJBGHHWWJGGGWJAIEAIIJ...............................",
    "JJJDDKCaUaUU........................SIFABBBIABGMMGIGPACCBBIII...............................",
    "GJIKKKEFaaUVA......................SSICFABDANJBBGGAPIACACBEGQ...............................",
    "..KKBEFFFFUVK......................SMBEAABBBANJBGJIIPJCCABBBQQ..............................",
    ".KJKFFFECEUVK.............HOOL....PMMBFBABBBIAJCNIIPIJEECEEBMQ..............................",
    ".JKFFFCECFOZZ...........KHHHMLLJAPQQMAFCAAAACCJBNICIJJJAECEDHMQH............................",
    "..FBIUFCEFOOZZ..........SHADJMLLLQQMGAECBBIIABBJJCCCLLLIBEIDBHMH............................",
    "....BUUFEFECZZZ........DSA..DJMLLLQGADCEABHIOOACJALLLLLOAEIIBGHG............................",
    "...GCUUCCBD.CZZK.......HH....DJLLLGADABCJHHKOLOJIOLLLROOJEJGGJGAC...........................",
    "....DUUHHAI....KC......HH..DDHBBGGADABDFRSKKKOLOOLLJKROOOFGKGWAADDEK........................",
    ".....JCBACI....B.......HHDKDDHHBDAAGGBJFRSJKKKKOOOKKKKKOOGGMJWWOOKKK........................",
    ".....EAAABI...BB...LJ...DILLDDQQGGMMGAEERSKKKKKJOIKKKKRLIFBMWIGOOZZKK.......................",
    ".....FAAAAB...I...LLLV..DLLLMMQQQQQMBDJEJWJKKKKKOOLIKRLLIEGGMWOOOOIKKK......................",
    ".....ADDABB...C....LLLVILLQMBDAGMMQBDADECWWKKKSILLLOOLLLEEJDGMOLLOQJKGK.....................",
    ".....FAAABBI..A....DGLLLLQMABGGBDDDAGBAAESSOLLSHLLLLLLLLEDDBAAGHHAQQJKK.....................",
    "......AAABBB......D.DGLQQMBGMHGBBAABGGADGESSOOHHLLLLLLOJDDDBGGBAAAGGKKKB....................",
    "......AAABCB......KDDDGHHABQMGHAGQQMGGDDDAGHWWJJJLLLLOOODADDAGHHGBAGGKKB....................",
    "......ADDACCE....GSSJDDBGAHQGGBWWQQMBADAADDHHSSJJLLLLOLDDBBDAAGHMMMWWKJK....................",
    "......BAAABEEE...SBSSDDAABHQGGGWWQGADABBADDHHSSSOOLLOOLDDBGBABABHQQWWZZK....................",
    "......CAAABCEIV..ACASSAHQHHHAASQQGDBGGGBDAKHHHKKKKKOOLDDDAGHBABAABGAAAWW....................",
    "......FAAABCEBVVVAADGWWQHGGJSSQMMGAHGGGBDBDJHHHJIKOLODDDADGHHGABGBBAAGMW....................",
    ".......AAAABCDVVTTTTDBGGGBGGSMMQDBGHJGBDABDDJHHHSLLLSSDABAAHQQQGAGGGBDKM....................",
    "........AAABABCEFTTTXXGDDDGGBDDDDDGJHGAAAADDIAHSLLLSSODABBAAHQQQHBGHG..J....................",
    "..........ADDBAEEFFFITTDVDDICKDDECDDBAAADDDDAGABJLJSLODDABBGABGMQHGHH..G....................",
    "...........DAAABBEFCCFFFVVFFFBBTTECADDDDDDDAAHGAABSLLLDDDBBGHGBBMQGHH..B....................",
    ".............AAABCCCBEFFECEAEBBITECBACBBEAABHHHHIPLLLLIEDDABGHGAGMGMGDKJ....................",
    "...............AAABCBCEEEBECBCAEEEBBAEBEBAAABJJGPPPRRICCBBDAGHHBGMGMHJJ.....................",
    "..................AAABCCCBCCBCAECCBBBCDDBDABBABBIPPRBJIIDEEADAHBGGAHMQQ.....................",
    "....................DABBBABCBBABBBAADBBACCBBBBIIPPIACAIIIEIACADDGGGBHQQ.....................",
    ".........................AABAAADABADEECCCCCDAJAIJJBCCCDCIIJDAIIJDGHGBGQ.....................",
    "............................AAADAAABTECECBEAICBCEFFCEFCBBDACFEIINDGHGD......................",
    "..............................DDDRAATEEFBNJBCIEEFNNNEFEADABCEEINNNAHHD......................",
    "...............................DRRCAEEEFCNCCIBEENTNNNADBAACEEIIICNJGHD......................",
    "..............................DRRNCCFEEIICIIIEENTXNKACECBAAADDAAABDBH.......................",
    "..............................bbNEBIIITJNIIIBFFTXJAEEEEECECACCAJCFIDB.......................",
    "..............................bbIIBIIITNNNJCFFTTAJEECBAECECCEEECEEUD........................",
    "..............................bJEEACJIENICBFFFJBKJJCJFEBBBCCCCCEEEUD........................",
    "..............................FCFEBBFNBECBEEFACEIIJJEEEBBACBDDAABEUA........................",
    "..............................CCFECAFNDBAEEFABEECRJJEEAADAADACEEIJFA........................",
    "..............................BBCBBDCEABACEABCCCIIRJIAECDDDDBCEFTTID........................",
    "..............................ADABBDBCAABCAABCBBIIIBCEEBDDDABCEETTTDI.......................",
    "..............................BDAAAADBDDBBDBBBDECFACFCCBDDDABCEFFTTAP.......................",
    "..............................ADAAAADADDAADABDCCCABECCCAA..AABEFFFFPA.......................",
    "..............................AACCBAABDAADDAADBBBDBBBBFA....ABCCEFFFDB......................",
    "...............................BBFCDBBDABADBBAABDAAACCCB....AACCEEFTJR......................",
    "...............................EDDDDBBDBCADDABBADABCFCD......ABCEEETTR......................",
    "...............................EBDADCBDCCDBADDADABEEAA.......AACEEEFTAG.....................",
    "...............................CCAADCCDCCACBDAADDDDDAC........ABCBABIDD.....................",
    "...............................CCCADCBAECBEBABCDAAABC.........AAABEAIDDE....................",
    "...............................CCEAACCACDCCACCEDCCCBF.........AAACADBIDD....................",
    "...............................IICAACCAEBCBDEFACCCCFa..........DAACEENNKA...................",
    "...............................IICAABCACACBAFFDCECEaF..........DABBBBNYYK...................",
    "...............................UCCABBEBEACBEFIACCEFFD...........AAACEFUZZD..................",
    "................................UCBBAEAEBBDFFACECEaCD...........AAACEFFUZZ..................",
    "................................UACBBCBEACAEFACCCFaD.............AABCEFFUZD.................",
    "................................UACCBCBCACAEEAEBEaFK.............AAACEEFFKK.................",
    "................................UACCBCBCBBBEBBCCEEBF..............AABCEEEEKD................",
    "................................UBCCBCCCBACEDCEBCFFDD.............BAAACEEEEK................",
    "................................AACCBBCCBDEEACCCFFFAD..............CAABCEEEKK...............",
    "................................EACCCAEEBDFCBCEEEBJPP...............EAABCECTR.....BDVUF.....",
    "................................CBCCCAEEBAFBCEEARRRJP...............FCAAACEFTR..TBDVVU......",
    "...............................CEBBCEAEEBBFACEANPIJCC................FFAABEEFTRATBRZVE....ZZ",
    "...............................DCCDCEAECBCEABAFJNPAAB................EEEAACEFFIKDRZZC..YYZZZ",
    "...............................BBBDCEAECBCEDAFEFABCEE.................KEEABBBEIIRZZEKUYYYZFE",
    "...............................FAAAEECFAACCAEEEACEFEC..................AFCAACBJIZZFEUUUEC...",
    "...............................CEADEBCEAACACCFIJCEEEBC.................DBaCABJLLOJEEFCKKD...",
    "...............................EECDBBCEADAEDECCCJEECIE..................IDaBALLLOBKKFFKYKA..",
    "...............................CBBEIJABCEACCDBCCJBCIJBB..................DDFBLLLOFKKBFEKYKB.",
    "..............................FCDDAENNNEBAAECDEJYYIIEAA...................FDEJLLLCEFKIKKIK..",
    ".............................FCDDADDDDDDDADCEBAECYECABE...................ADDYLLEEEKJKKKK...",
    ".............................EA..BBDDDDABBDDEEABCCCABEEA...................AYLID..DKJKKK....",
    "............................EA...ACCACBECDDDEEEDFEAAFECD......................A....DAKI.....",
]

BACKGROUND = "."
CELL_X, CELL_Y = 1, 1      # tamaño original de cada píxel lógico en la imagen de origen
OFFSET_X, OFFSET_Y = 0, 0
CANVAS = (92, 79)              # tamaño original del lienzo


def _bounds(k, cell, offset):
    import math
    return math.floor(offset + k * cell), math.floor(offset + (k + 1) * cell)


def render(scale=None, transparent=False):
    """Dibuja el sprite SIN suavizado (rectángulos sólidos).

    scale=None  -> reproduce la imagen original (celda 1x1, lienzo 92x79).
    scale=int   -> sprite de 92x79 px ampliado por un entero, sin márgenes.
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
