# -*- coding: utf-8 -*-
"""My Melody: dibujo pixel a pixel (mitad izquierda en texto + parches), de frente."""
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
    ".",                          # 0
    "......KKKKKK.",               # 1
    "....KKPPPPPPKK.",             # 2
    "...KPPPPPPPPPPK.",            # 3
    "...KPPPKKKKPPPK.",            # 4
    "...KPPPKqqKPPPK.",            # 5
    "...KPqPKqqKPqPK.",            # 6
    "...KPqPKqqKPqPK.",            # 7
    "...KPqPKqqKPqPK.",            # 8
    "...KPPPKqqKPPPK.",            # 9
    "....KKKKKKKPPPKKKKKKKK",     # 10
    "........KKPPPPPPPPPPPP",     # 11
    "....KKKPPPPPPPPPPPPPPP",     # 12
    "...KPPPPPPPPPPPPPPPPPP",     # 13
    "...KPPPPPPPPKKKKKKKKKK",     # 14
    "...KPPPPPPKKWWWWWWWWWW",     # 15
    "...KPPPPPKWWWWWWWWWWWW",     # 16
    "...KPPPPKWWWWWWWWWWWWW",     # 17
    "...KPPPPKWWW", "...KPPPPKWWW", "...KPPPPKWWW", "...KPPPPKWWW",  # 18-21
    "...KPPPPKWWW", "...KPPPPKWWW",                                   # 22-23
    "...KPPPPPKWW",              # 24
    "...KPPPPPPKKWW",            # 25
    "...KPPPPPPPPKKKKKKKKKK",    # 26
    "....KPPPPPPPPPPPPPPPPP",    # 27
    ".....KPPPPPPPPPPPPPPPP",    # 28
    ".......KPPPPPPPPPPPPPP",    # 29
    "..........KKKKKKKKKKKK",    # 30
    ".........KDDDDDDDDDDDD",    # 31
    "....KKKKKKDDDDDDDDDDDD",    # 32
    "....KWWWWKDDDDDDDDDDDD",    # 33
    "....KWWWWKDDDDDDDDDDDD",    # 34
    "....KWWWWKDDDDDDDDDDDD",    # 35
    ".....KKKKKDDDDDDDDDDDD",    # 36
    ".........KDDDDDDDDDDDD",    # 37
    "........KKKKKKKKKKKKKK",    # 38
    ".......KWWWWWWWWWWK...",     # 39
    "......KWWWWWWWWWWWK...",     # 40
    ".......KKKKKKKKKKKK...",     # 41
]]
assert len(MITAD) == 42, len(MITAD)

MATS = {
    'P': ('#ffb2d8', '#f77cb6', '#c24a90', '#a03070'),
    'q': ('#ffe4f0', '#ffc6de', '#f08cba', '#c24a90'),
    'W': ('#ffffff', '#f2f0fa', '#b4b0d8', '#8078b0'),
    'D': ('#ffc4de', '#ff96c6', '#d45c9c', '#a83c78'),
    'F': ('#fff4fa', '#ffcfe6', '#ea7ab0', '#a83c78'),
}
FIJOS = {'E': '#2a1030', 'Y': '#ffd21e', 'C': '#ff8aa6', 'n': '#e8a020', 'H': '#ffffff'}

PARCHES = [
    (13, 19, 'EE'), (13, 20, 'EE'), (13, 21, 'EE'), (29, 19, 'EE'), (29, 20, 'EE'), (29, 21, 'EE'),
    (13, 19, 'H'), (29, 19, 'H'),
    (10, 22, 'CCC'), (10, 23, 'CCC'), (30, 22, 'CCC'), (30, 23, 'CCC'),
    (21, 21, 'nn'),
    (20, 23, 'k'), (21, 24, 'kk'), (23, 23, 'k'),
    # flor rosa sobre la capucha (lado derecho del dibujo)
    (30, 11, '..KKK..'), (30, 12, '.KFFFK.'), (30, 13, 'KFFYFFK'), (30, 14, 'KFYYYFK'),
    (30, 15, 'KFFYFFK'), (30, 16, '.KFFFK.'), (30, 17, '..KKK..'),
]


def dibujar():
    filas, ley = construir(parchar(espejo(MITAD), PARCHES), MATS, FIJOS, oscuro='#3a1838', banda=1)
    return dibujo(filas, ley)


def hojas():
    return hoja_rebote(dibujar())


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'mymelody.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'mymelody_x9.png')
    print('ok', h.size)
