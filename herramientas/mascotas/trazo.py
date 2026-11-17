# -*- coding: utf-8 -*-
"""Ayuda para dibujar a mano en texto: se escribe la MITAD izquierda (o el dibujo entero) con letras de material y
'K' (contorno); parches pixel a pixel retocan lo asimetrico; luego un pase de sombreado en 3 tonos (luz arriba-izq,
sombra abajo-der) y contorno (oscuro del lado de la sombra, tono calido del lado de la luz).
Devuelve (filas, leyenda) para ascii.dibujo."""


def _rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return '#%02x%02x%02x' % tuple(c)


def espejo(mitad):
    return [r + r[::-1] for r in mitad]


def parchar(filas, parches):
    g = [list(f) for f in filas]
    for x, y, s in parches:
        for i, c in enumerate(s):
            if c != ' ':
                g[y][x + i] = c
    return [''.join(f) for f in g]


def construir(filas, mats, fijos, oscuro='#1c1428', banda=2, sin_luz=''):
    """mats: letra -> (luz, base, sombra, contorno_luz). fijos: letra -> color (sin sombreado)."""
    h, w = len(filas), len(filas[0])
    g = [list(f) for f in filas]

    def vacio(x, y):  # fuera, transparente o contorno
        if x < 0 or y < 0 or x >= w or y >= h:
            return True
        return g[y][x] in '.K'

    def mat_vec(x, y):
        for dx, dy in ((-1, 0), (0, -1), (-1, -1), (1, 0), (0, 1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < w and 0 <= yy < h and g[yy][xx] in mats:
                return g[yy][xx]
        return None

    sal = [['.'] * w for _ in range(h)]
    leyenda = {'.': None}
    claves = {}

    def car(color):
        if color not in claves:
            claves[color] = chr(33 + len(claves)) if chr(33 + len(claves)) != '.' else '~'
            leyenda[claves[color]] = color
        return claves[color]

    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c == '.':
                continue
            if c in fijos:
                sal[y][x] = car(fijos[c])
            elif c in mats:
                luz, base, som, _ = mats[c]
                esq = vacio(x + 1, y) or vacio(x, y + 1) or vacio(x + 1, y + 1)
                esq2 = banda >= 2 and (vacio(x + 2, y + 1) or vacio(x + 1, y + 2) or vacio(x + 2, y + 2))
                lit = vacio(x - 1, y) or vacio(x, y - 1)
                if esq or esq2:
                    col = som
                elif lit and c not in sin_luz:
                    col = luz
                else:
                    col = base
                sal[y][x] = car(col)
            elif c in 'Kk':
                afuera_ds = (x + 1 >= w or g[y][x + 1] == '.') or (y + 1 >= h or g[y + 1][x] == '.')
                afuera = any((xx < 0 or yy < 0 or xx >= w or yy >= h or g[yy][xx] == '.')
                             for xx, yy in ((x - 1, y), (x, y - 1), (x + 1, y), (x, y + 1)))
                m = mat_vec(x, y)
                if c == 'k' or afuera_ds or m is None:
                    col = oscuro
                elif afuera:
                    col = mats[m][3]
                else:
                    col = mats[m][3]
                sal[y][x] = car(col)
            else:
                raise ValueError(f'letra desconocida {c!r} en {x},{y}')
    return [''.join(r) for r in sal], leyenda
