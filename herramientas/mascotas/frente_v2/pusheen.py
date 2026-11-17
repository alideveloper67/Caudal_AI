# -*- coding: utf-8 -*-
"""Pusheen: gata gris gordita, dibujo pixel a pixel (mitad izquierda en texto + parches), de frente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402
from trazo import construir, espejo, parchar  # noqa: E402

A = 22


def R(s):
    return s.ljust(A, s[-1])


# columna donde empieza la panza crema en cada fila (y -> x); fuera de la tabla no hay panza
PANZA = {24: 15, 25: 13, 26: 11, 27: 10, 28: 10, 29: 10, 30: 10, 31: 10, 32: 11, 33: 12, 34: 13, 35: 15}
BORDE = {32: 6, 33: 7, 34: 8, 35: 9}  # el cuerpo se cierra hacia los pies


def _cuerpo(y):
    lx = BORDE.get(y, 5)
    gris = 'G' * (A - lx - 1)
    s = '.' * lx + 'K' + gris
    if y in PANZA:
        px = PANZA[y]
        s = s[:px] + 'C' * (A - px)
    return s


MITAD = [R(s) for s in [
    ".",                                 # 0
    ".",                                 # 1
    "........KK.",                        # 2
    ".......KGGK.",                       # 3
    ".......KGGGK.",                      # 4
    "......KGGGGGKK.",                    # 5
    "......KGGGGGGGKKKKKKKK",            # 6
    "......KGGGGGGGGGGGGGGG",            # 7
]] + [R(_cuerpo(y)) for y in range(8, 36)] + [R(s) for s in [
    "........KGGGGGGGGGGGGG",            # 36
    "........KGGGGGGGGGGGGG",            # 37
    "........KGGGGGGGGGGGK.",            # 38
    "........KGGGGGGGGGGGK.",            # 39
    "........KGGGGGGGGGGGK.",            # 40
    "........KKKKKKKKKKKK..",            # 41
]]
assert len(MITAD) == 42, len(MITAD)

MATS = {
    'G': ('#b4b8cc', '#8c90a8', '#62667e', '#4a4e68'),
    'C': ('#fff0dc', '#f4dcbc', '#d4b48c', '#8a6a50'),
}
FIJOS = {'S': '#585c74', 's': '#454861', 'E': '#161420', 'H': '#ffffff', 'N': '#f08aa0'}

PARCHES = [
    # rayas de la frente
    (17, 7, 'S'), (17, 8, 'S'), (21, 7, 'SS'), (21, 8, 'SS'), (21, 9, 'SS'), (26, 7, 'S'), (26, 8, 'S'),
    # rayas de las mejillas y el lomo
    (6, 14, 'SSS'), (6, 16, 'SSS'), (35, 14, 'SSS'), (35, 16, 'SSS'),
    (6, 24, 'SSS'), (6, 27, 'SSS'), (6, 30, 'SSS'), (35, 24, 'SSS'), (35, 27, 'SSS'), (35, 30, 'SSS'),
    # ojos con brillo
    (13, 15, 'EE'), (13, 16, 'EE'), (13, 17, 'EE'), (29, 15, 'EE'), (29, 16, 'EE'), (29, 17, 'EE'),
    (13, 15, 'H'), (29, 15, 'H'),
    # nariz y boca en w
    (21, 17, 'NN'), (19, 19, 'k'), (20, 20, 'k'), (21, 19, 'kk'), (23, 20, 'k'), (24, 19, 'k'),
    # bracitos sobre la panza
    (9, 26, 'k'), (9, 27, 'k'), (9, 28, 'k'), (10, 29, 'k'), (11, 29, 'k'),
    (34, 26, 'k'), (34, 27, 'k'), (34, 28, 'k'), (33, 29, 'k'), (32, 29, 'k'),
    # patitas: dos dedos
    (12, 40, 'K'), (15, 40, 'K'), (28, 40, 'K'), (31, 40, 'K'),
    # cola con rayas (lado derecho)
    (39, 18, '.KKK.'), (39, 19, 'KGGGK'), (39, 20, 'KSSSK'), (39, 21, 'KGGGK'), (39, 22, 'KGGGK'),
    (39, 23, 'KSSSK'), (39, 24, 'KGGGK'), (39, 25, 'KGGGK'), (39, 26, 'KSSSK'), (39, 27, 'KGGGK'),
    (39, 28, 'KGGGK'), (39, 29, 'KSSSK'), (39, 30, 'KGGGK'), (39, 31, 'KKKK.'),
]


def dibujar():
    filas, ley = construir(parchar(espejo(MITAD), PARCHES), MATS, FIJOS, oscuro='#26283c', banda=1)
    return dibujo(filas, ley)


def hojas():
    return hoja_rebote(dibujar())


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'pusheen.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'pusheen_x9.png')
    print('ok', h.size)
