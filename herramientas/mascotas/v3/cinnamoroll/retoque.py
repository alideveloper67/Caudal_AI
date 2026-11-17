# Espiral de la cola (la «rollo de canela»): detalle de 1 px.
ESP = [
    ".SS.",
    "S..S",
    "S.S.",
    ".S..",
]


def retocar(px, f):
    x0, y0 = (34, 33) if not f else (34, 32)
    for j, fila in enumerate(ESP):
        for i, c in enumerate(fila):
            if c == 'S':
                px(x0 + i, y0 + j, '#a3b0e6')
