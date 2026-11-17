# -*- coding: utf-8 -*-
"""Nyan Cat dibujado píxel a píxel como texto: el gato-pop-tart que vuela de lado hacia la derecha (cuadro 56x44).
Sin arcoíris (lo dibuja el código de la app). Entre cuadros se mueven la cola y las patitas."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'K': '#181820',                                          # contorno
    'T': '#f8c890', 't': '#ffe2b8', 'U': '#dca468',          # borde de la galleta: base, luz, sombra
    'P': '#f898c8', 'p': '#ffc4e0', 'Q': '#e872a8', 'S': '#e03478',   # glaseado, luz, sombra, puntitos
    'G': '#9c9ca4', 'g': '#c8c8d0', 'h': '#6c6c78',          # gato gris: base, luz, sombra
    'C': '#f8a0b8', 'W': '#ffffff', 'i': '#e89ab0',          # mejillas, brillo, interior de la oreja
    '.': None,
}
W = 56
H = 38


def R(s):
    out = ''
    for t in s.split():
        m = re.fullmatch(r'(\d+)(\D)', t)
        out += m.group(2) * int(m.group(1)) if m else t
    return out


def lienzo():
    return [['.'] * W for _ in range(H)]


def poner(L, x, y, s):
    """Escribe la cadena s (con repeticiones) en la fila y desde la columna x; el punto no borra nada."""
    for i, c in enumerate(R(s)):
        if c != '.' and 0 <= y < H and 0 <= x + i < W:
            L[y][x + i] = c


def cuerpo(L):
    """La galleta rosa: borde crema, glaseado con contorno rosa oscuro y puntitos."""
    poner(L, 11, 0, "26K")
    poner(L, 9, 1, "K 4t 22T 2U K")
    for y, mid in ((2, "5t 23T 2U"), (3, "4t 22T 4U")):
        poner(L, 8, y, "K " + mid + " K")
    poner(L, 8, 4, "K tT 26Q TU K")
    gl = ["3p 19P 2Q", "2p 20P 2Q"] + ["p 21P 2Q"] * 11 + ["21P 3Q"] * 6 + ["20P 4Q", "19P 5Q"]   # 21 filas (5..25)
    for i, g in enumerate(gl):
        poner(L, 8, 5 + i, "K tT Q " + g + " Q TU K")
    poner(L, 8, 26, "K tT 26Q TU K")
    poner(L, 8, 27, "K 2t 22T 6U K")
    poner(L, 8, 28, "K 2t 20T 8U K")
    poner(L, 9, 29, "K 2t 18T 8U K")
    poner(L, 11, 30, "26K")
    for (x, y) in [(14, 7), (23, 6), (30, 8), (16, 12), (26, 11), (33, 14), (14, 17), (22, 16), (29, 19),
                   (18, 22), (25, 23), (33, 24), (13, 25), (20, 9)]:     # puntitos de azúcar
        poner(L, x, y, "SS")


def cabeza(L):
    """Cabeza gris de gato (casi de frente) con orejas, mejillas rosas, ojos con brillo y boquita."""
    poner(L, 36, 10, "KK"); poner(L, 48, 10, "KK")
    poner(L, 35, 11, "KgGK"); poner(L, 47, 11, "KgGK")
    poner(L, 34, 12, "KgiGGK"); poner(L, 46, 12, "KgiGGK")
    poner(L, 34, 13, "KgiGGK 6K KgiGGK")
    # (a, b, relleno) desde la fila 14 hasta la 33
    tabla = [
        (33, 52, "3g 14G h"),
        (32, 53, "3g 16G h"),
        (31, 54, "3g 17G 3h"),
    ] + [(31, 54, "2g 19G 3h")] * 14 + [(32, 53, "2g 17G h"), (33, 52, "g 15G 2h"), (34, 51, "g 13G 2h"), (36, 49, "g 12G h"), None]
    y = 14
    for item in tabla:
        if item is None:
            poner(L, 37, y, "12K")
        else:
            a, b, mid = item
            poner(L, a, y, "K " + mid + " K")
        y += 1
    for ox in (37, 47):                                       # ojos
        poner(L, ox, 20, "WK"); poner(L, ox, 21, "KK"); poner(L, ox, 22, "KK")
    poner(L, 34, 24, "3C"); poner(L, 34, 25, "3C"); poner(L, 49, 24, "3C"); poner(L, 49, 25, "3C")   # mejillas
    poner(L, 42, 23, "KK")                                    # nariz
    poner(L, 40, 25, "KK"); poner(L, 44, 25, "KK"); poner(L, 42, 26, "KK")   # sonrisa


def patas(L, dx):
    for x in (11 - dx, 21 - dx):                              # traseras
        for y in range(31, 37):
            poner(L, x, y, "KgGGhK")
        poner(L, x, 37, "6K")
    for x in (36 + dx, 45 + dx):                              # delanteras
        for y in range(34, 37):
            poner(L, x, y, "KgGhK")
        poner(L, x, 37, "5K")


def cola(L, dy):
    poner(L, 2, 14 + dy, "6K")
    poner(L, 1, 15 + dy, "KgGGGGh")
    poner(L, 0, 16 + dy, "KgGGGGGh")
    poner(L, 1, 17 + dy, "KGGGGhh")
    poner(L, 2, 18 + dy, "6K")


def cuadro(dy, dx):
    L = lienzo()
    cola(L, dy)
    patas(L, dx)
    cuerpo(L)
    cabeza(L)
    return [''.join(f) for f in L]


FILAS = cuadro(0, 0)
FILAS2 = cuadro(1, 1)


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA), base2=dibujo(FILAS2, LEYENDA), ancho_cuadro=56)


if __name__ == '__main__':
    import pix
    pix.W = 56
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'nyan.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'nyan_x9.png')
    print('ok', h.size)
