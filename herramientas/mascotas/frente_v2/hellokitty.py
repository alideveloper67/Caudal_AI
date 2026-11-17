# -*- coding: utf-8 -*-
"""Hello Kitty: dibujo pixel a pixel (mitad izquierda en texto + parches asimetricos), de frente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402
from trazo import construir, espejo, parchar  # noqa: E402

A = 22  # ancho de la mitad


def R(s):
    return s.ljust(A, s[-1])


MITAD = [R(s) for s in [
    ".",                      # 0
    "......KKK.",              # 1
    ".....KWWWKK.",            # 2
    "....KWWWWWWKK.",          # 3
    "....KWWWWWWWWKK",         # 4
    "...KW",                   # 5
    "...KW",                   # 6
    "..KW",                    # 7
    "..KW", "..KW", "..KW", "..KW", "..KW", "..KW", "..KW", "..KW", "..KW",   # 8-16
    "..KW", "..KW", "..KW",   # 17-19
    "..KW",                   # 20
    "...KW",                  # 21
    "...KW",                  # 22
    "....KW",                 # 23
    ".....KKW",                # 24
    ".......K",                # 25
    ".........KW",            # 26
    "....KKKKKKWWWW",         # 27
    "....KWWWWKB",            # 28
    "....KWWWWKB",            # 29
    "....KWWWWKB",            # 30
    "....KWWWWKB",            # 31
    ".....KKKKKB",            # 32
    ".........KB",            # 33
    ".........KB",            # 34
    ".........KB",            # 35
    "........KBB",            # 36
    "........KBBBBBBBBBBK..", # 37
    "........KBBBBBBBBBBK..", # 38
    ".......KKWWWWWWWWKKK..", # 39
    "......KWWWWWWWWWWWK...", # 40
    ".......KKKKKKKKKKK....", # 41
]]
assert len(MITAD) == 42, len(MITAD)

LEYENDA_MAT = {
    'W': ('#ffffff', '#eef0f8', '#aab0d6', '#7078a8'),
    'R': ('#ff6a70', '#e02030', '#98123a', '#7a1030'),
    'B': ('#62a4f4', '#2f6fd0', '#1d479c', '#1a3a82'),
}
FIJOS = {'E': '#1c1428', 'Y': '#ffd21e', 'y': '#e0a010', 'H': '#ffffff'}

PARCHES = [
    # ojos (2x3) con brillo
    (11, 14, 'E'), (11, 15, 'E'), (11, 16, 'E'), (12, 14, 'E'), (12, 15, 'E'), (12, 16, 'E'),
    (31, 14, 'E'), (31, 15, 'E'), (31, 16, 'E'), (32, 14, 'E'), (32, 15, 'E'), (32, 16, 'E'),
    # nariz
    (21, 17, 'YY'), (20, 18, 'YYYY'), (21, 19, 'yy'),
    # bigotes (3 por lado)
    (0, 13, 'kk'), (3, 14, 'kkkk'), (0, 17, 'kk'), (3, 17, 'kkkk'), (0, 21, 'kk'), (3, 20, 'kkkk'),
    (42, 13, 'kk'), (37, 14, 'kkkk'), (42, 17, 'kk'), (37, 17, 'kkkk'), (42, 21, 'kk'), (37, 20, 'kkkk'),
    # lazo rojo en la oreja (derecha del dibujo = su oreja izquierda)
    (29, 2, '..KKK..KKK..'),
    (29, 3, '.KRRRKKRRRK.'),
    (29, 4, 'KRRRRRKRRRRK'),
    (29, 5, 'KRRRRRKRRRRK'),
    (29, 6, '.KRRRKKRRRK.'),
    (29, 7, '..KKK..KKK..'),
    # botones del overol
    (12, 26, 'KBBK'), (12, 27, 'KBBK'), (28, 26, 'KBBK'), (28, 27, 'KBBK'),
    (16, 28, 'KKKKKKKKKKKK'), (13, 29, 'Y'), (30, 29, 'Y'),
]


def _filas():
    f = espejo(MITAD)
    # oreja derecha: el espejo ya la dibuja; el lazo la tapa en parte
    return parchar(f, PARCHES)


def dibujar():
    filas, ley = construir(_filas(), LEYENDA_MAT, FIJOS, oscuro='#2a2850', banda=1)
    return dibujo(filas, ley)


def hojas():
    return hoja_rebote(dibujar())


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'hellokitty.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'hellokitty_x9.png')
    print('ok', h.size)
