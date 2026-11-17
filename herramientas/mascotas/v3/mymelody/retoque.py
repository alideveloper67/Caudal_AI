# Flor de 4 petalos en la base de la oreja (detalle chico, pixel a pixel). En f1 se inclina 1 px.
FLOR = [
    ".oo.oo.",
    "oPPoPPo",
    "oPLPPPo",
    ".oPYPo.",
    "oPPPPDo",
    "oPDoPDo",
    ".oo.oo.",
]
COL = {'o': '#7a1238', 'P': '#ff6f9f', 'L': '#ffd0e0', 'D': '#d23a72', 'Y': '#ffd84a'}


def retocar(px, f):
    x0, y0 = (10, 7) if not f else (9, 6)
    for j, fila in enumerate(FLOR):
        for i, c in enumerate(fila):
            if c != '.':
                px(x0 + i, y0 + j, COL[c])
