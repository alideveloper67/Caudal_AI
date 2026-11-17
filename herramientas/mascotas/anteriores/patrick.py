# -*- coding: utf-8 -*-
"""Patricio Estrella corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('rosa', '#f4909e', sombra='#d65c8c', contorno='#8a3050')
    L.mat('verde', '#3cb04c', sombra='#26806c', contorno='#124a3a')
    L.mat('flor', '#9a4cb8', fijo=True)
    L.mat('mota', '#e06888', fijo=True)
    L.mat('ojob', '#f8f8ff', fijo=True)
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('boca', '#8a2440', fijo=True)
    L.mat('ceja', '#5a2a3c', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    B = 'b'

    def P(lista, m):
        for (x, y) in lista:
            L.rect(x, y + dy, x, y + dy, m, grupo=B)

    # brazo trasero
    if pose == 0:
        L.poligono([(13, 22 + dy), (9, 25 + dy), (8, 29 + dy), (11, 30 + dy), (14, 27 + dy)], 'rosa')
    else:
        L.poligono([(13, 22 + dy), (9, 22 + dy), (7, 25 + dy), (10, 27 + dy), (14, 26 + dy)], 'rosa')

    # piernas y pies
    if pose == 0:
        L.rect(14, 34, 18, 39, 'rosa')
        L.elipse(16, 41, 4, 2, 'rosa')
        L.rect(26, 34, 30, 39, 'rosa')
        L.elipse(29, 41, 5, 2, 'rosa', borde=True)
    else:
        L.rect(18, 34, 21, 39, 'rosa')
        L.elipse(20, 41, 4, 2, 'rosa')
        L.rect(24, 34, 27, 39, 'rosa')
        L.elipse(26, 41, 5, 2, 'rosa', borde=True)

    # cuerpo + cabeza conica (un solo grupo)
    L.elipse(23, 26 + dy, 10, 9, 'rosa', grupo=B)
    L.poligono([(16, 18 + dy), (26, 2 + dy), (28, 2 + dy), (36, 18 + dy)], 'rosa', grupo=B)
    L.rect(18, 14 + dy, 34, 20 + dy, 'rosa', grupo=B)
    EB = lambda x, y: L.celda[y][x][0] == B
    # pantalon verde
    L.recolorear(lambda x, y: y >= 29 + dy and EB(x, y), 'verde')
    # flores del pantalon
    P([(18, 31), (17, 32), (19, 32), (18, 33)], 'flor')
    P([(28, 32), (27, 33), (29, 33), (28, 34)], 'flor')
    P([(23, 30), (22, 31), (24, 31)], 'flor')
    # motas de la piel
    P([(17, 24), (19, 20), (30, 22)], 'mota')

    # cara
    P([(25, 8), (25, 9), (26, 8), (26, 9), (26, 10), (25, 10)], 'ojob')
    P([(29, 8), (29, 9), (30, 8), (30, 9), (30, 10), (29, 10)], 'ojob')
    P([(26, 9), (26, 10)], 'ojo')
    P([(30, 9), (30, 10)], 'ojo')
    P([(25, 6), (26, 6), (27, 6), (29, 6), (30, 6), (31, 6)], 'ceja')
    P([(24, 15), (25, 16), (26, 16), (27, 16), (28, 16), (29, 16), (30, 15)], 'boca')

    # brazo delantero
    if pose == 0:
        L.poligono([(31, 22 + dy), (35, 25 + dy), (38, 27 + dy), (38, 30 + dy), (34, 30 + dy), (30, 26 + dy)],
                   'rosa', borde=True)
    else:
        L.poligono([(31, 22 + dy), (36, 21 + dy), (39, 20 + dy), (39, 23 + dy), (35, 26 + dy), (30, 26 + dy)],
                   'rosa', borde=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'patrick.png')
    vista([h], escala=9, salida=out / 'patrick_x9.png')
    print('ok', h.size)
