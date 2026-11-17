# -*- coding: utf-8 -*-
"""Cinnamoroll: dibujo pixel a pixel (mitad izquierda en texto + parches), de frente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402
from trazo import construir, espejo, parchar  # noqa: E402

A = 22


def R(s):
    return s.ljust(A, s[-1])


MITAD = [R(s) for s in [
    ".",                                   # 0
    ".",                                   # 1
    ".",                                   # 2
    "..............KKKKKKKK",              # 3
    "............KKWWWWWWWW",              # 4
    "..........KKWWWWWWWWWW",              # 5
    ".....KKKKKKWWWWWWWWWWW",              # 6
    "...KKLLLLLKWWWWWWWWWWW",              # 7
    "..KLLLLLLLKWWWWWWWWWWW",              # 8
    ".KLLLLLLLLKWWWWWWWWWWW",              # 9
    ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW",
    ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW",
    ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW", ".KLLLLLLLLKWWWWWWWWWWW",
    ".KLLLLLLLLKWWWWWWWWWWW",              # 10-19
    ".KLLLLLLLLLKWWWWWWWWWW",              # 20
    ".KLLLLLLLLLLKWWWWWWWWW",              # 21
    "..KLLLLLLLLLLKKKKKKKKK",              # 22
    "..KLLLLLLLLKKWWWWWWWWW",              # 23
    "..KLLLLLLLLKKWWWWWWWWW",              # 24
    "...KLLLLLLKKWWWWWWWWWW",              # 25
    "....KLLLLKKWWWWWWWWWWW",              # 26
    ".....KLLKKWWWWWWWWWWWW",              # 27
    "......KKK.KWWWWWWWWWWW",              # 28
    "............KWWWWWWWWW", "............KWWWWWWWWW", "............KWWWWWWWWW",
    "............KWWWWWWWWW", "............KWWWWWWWWW", "............KWWWWWWWWW",
    "............KWWWWWWWWW", "............KWWWWWWWWW",   # 29-36
    "...........KWWWWWWWWWW",              # 37
    ".........KWWWWWWWWWKK..",             # 38
    ".........KWWWWWWWWWK...",             # 39
    "........KWWWWWWWWWWK...",             # 40
    "........KKKKKKKKKKK...",              # 41
]]
assert len(MITAD) == 42, len(MITAD)

MATS = {
    'W': ('#ffffff', '#f4f6fd', '#b0bfe6', '#6c88c0'),
    'L': ('#c6eefc', '#90d2f6', '#5aa2dc', '#3e7cbc'),
}
FIJOS = {'E': '#2a54a8', 'e': '#16286a', 'H': '#ffffff', 'C': '#ffa0be', 'n': '#2a2040'}

PARCHES = [
    # mechon de la frente
    (19, 1, '.KKKK.'), (19, 2, 'KWWWWK'),
    # ojos azules grandes con brillo
    (14, 11, 'EEE'), (14, 12, 'EEE'), (14, 13, 'EEE'), (14, 14, 'eee'),
    (28, 11, 'EEE'), (28, 12, 'EEE'), (28, 13, 'EEE'), (28, 14, 'eee'),
    (14, 11, 'H'), (28, 11, 'H'), (15, 12, 'H'), (29, 12, 'H'),
    # mejillas
    (12, 16, 'CCC'), (12, 17, 'CCC'), (30, 16, 'CCC'), (30, 17, 'CCC'),
    # nariz y boca
    (21, 15, 'nn'), (20, 17, 'k'), (21, 18, 'kk'), (23, 17, 'k'),
    # cola enroscada (lado derecho)
    (32, 27, '..KKKKK..'), (32, 28, '.KWWWWWK.'), (32, 29, 'KWWKKKWWK'),
    (32, 30, 'KWKWWWKWK'), (32, 31, 'KWKWWWKWK'), (32, 32, 'KWWKKKWWK'),
    (32, 33, '.KWWWWWK.'), (32, 34, '..KKKKK..'),
]


def dibujar():
    filas, ley = construir(parchar(espejo(MITAD), PARCHES), MATS, FIJOS, oscuro='#26407e', banda=1)
    return dibujo(filas, ley)


def hojas():
    return hoja_rebote(dibujar())


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'cinnamoroll.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'cinnamoroll_x9.png')
    print('ok', h.size)
