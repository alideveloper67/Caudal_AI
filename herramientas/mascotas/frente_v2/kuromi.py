# -*- coding: utf-8 -*-
"""Kuromi: dibujo pixel a pixel (mitad izquierda en texto + parches), de frente."""
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
    ".KK.",                         # 0
    ".KNKK.",                       # 1
    "..KNNK.",                      # 2
    "..KNNNK.",                     # 3
    "...KNNNK.",                    # 4
    "...KNpNNK.",                   # 5
    "...KNpNNNK.",                  # 6
    "....KNpNNNK.",                 # 7
    "....KNpNNNNK.",                # 8
    "....KNpNNNNNK.",               # 9
    ".....KNNNNNNNNKKKKKKK",        # 10
    "....KNNNNNNNNNNNNNNNNN",       # 11
    "....KNNNNNNNNNNNNNNNNN",       # 12
    "...KNNNNNNNNNNNNNNNNNN",       # 13
    "...KNNNNNNNNKKKKKKKKKK",       # 14
    "...KNNNNNNKKWWWWWWWWWW",       # 15
    "...KNNNNNKWWWWWWWWWWWW",       # 16
    "...KNNNNKWWWWWWWWWWWWW",       # 17
    "...KNNNNKWWW", "...KNNNNKWWW", "...KNNNNKWWW", "...KNNNNKWWW",
    "...KNNNNKWWW", "...KNNNNKWWW",                                   # 22-23
    "...KNNNNNKWW",                 # 24
    "...KNNNNNNKKWW",               # 25
    "...KNNNNNNNNKKKKKKKKKK",       # 26
    "....KNNNNNNNNNNNNNNNNN",       # 27
    ".....KNNNNNNNNNNNNNNNN",       # 28
    ".......KNNNNNNNNNNNNNN",       # 29
    "..........KKKKKKKKKKKK",       # 30
    ".........KDDDDDDDDDDDD",       # 31
    "....KKKKKKNNNNNNNNNNNN",       # 32
    "....KNNNNKNNNNNNNNNNNN",       # 33
    "....KNNNNKNNNNNNNNNNNN",       # 34
    "....KWWWWKNNNNNNNNNNNN",       # 35
    ".....KKKKKNNNNNNNNNNNN",       # 36
    ".........KDDDDDDDDDDDD",       # 37
    "........KKKKKKKKKKKKKK",       # 38
    ".......KNNNNNNNNNNK...",       # 39
    "......KNNNNNNNNNNNK...",       # 40
    ".......KKKKKKKKKKKK...",       # 41
]]
assert len(MITAD) == 42, len(MITAD)

MATS = {
    'N': ('#5a5478', '#302a46', '#16121f', '#8a82b8'),
    'p': ('#ffc0dc', '#ff84bc', '#c84a90', '#8a3070'),
    'S': ('#ffc0dc', '#ff84bc', '#c84a90', '#8a3070'),
    'W': ('#ffffff', '#f2f0fa', '#b4b0d8', '#8078b0'),
    'D': ('#ffc4de', '#ff8cc0', '#d0549a', '#8a3070'),
}
FIJOS = {'E': '#161020', 'C': '#ff8aa6', 'H': '#ffffff', 'T': '#ff5a8c'}

PARCHES = [
    (13, 19, 'EE'), (13, 20, 'EE'), (13, 21, 'EE'), (29, 19, 'EE'), (29, 20, 'EE'), (29, 21, 'EE'),
    (13, 19, 'H'), (29, 19, 'H'),
    # cejas traviesas
    (11, 17, 'kk'), (13, 18, 'kk'), (31, 17, 'kk'), (29, 18, 'kk'),
    (10, 22, 'CCC'), (10, 23, 'CCC'), (30, 22, 'CCC'), (30, 23, 'CCC'),
    # sonrisa de medio lado con lengua
    (19, 23, 'k'), (20, 24, 'kkkk'), (24, 23, 'k'), (21, 25, 'TT'),
    # calavera rosa
    (18, 10, '.KKKKKK.'), (18, 11, 'KSSSSSSK'), (18, 12, 'KSkSSkSK'), (18, 13, 'KSkSSkSK'),
    (18, 14, '.KSSSSK.'), (18, 15, '.KSkkSK.'), (18, 16, '..KKKK..'),
]


def dibujar():
    filas, ley = construir(parchar(espejo(MITAD), PARCHES), MATS, FIJOS, oscuro='#0c0814', banda=1)
    return dibujo(filas, ley)


def hojas():
    return hoja_rebote(dibujar())


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'kuromi.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'kuromi_x9.png')
    print('ok', h.size)
