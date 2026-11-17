# -*- coding: utf-8 -*-
"""Minion corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('amarillo', '#f8d838', sombra='#e0a41c', contorno='#8a5a10')
    L.mat('azul', '#2e62b4', sombra='#22407e', contorno='#14284c')
    L.mat('gris', '#9aa2b0', sombra='#6c7488', contorno='#3a4050')
    L.mat('negro', '#26242e', sombra='#14121a', contorno='#0c0a10')
    L.mat('ojob', '#f8f8ff', fijo=True)
    L.mat('ojo', '#5a3418', fijo=True)
    L.mat('pupila', '#14141c', fijo=True)
    L.mat('boca', '#8a2418', fijo=True)
    L.mat('pelo', '#26242e', fijo=True)


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
        L.poligono([(15, 24 + dy), (11, 27 + dy), (10, 30 + dy), (12, 31 + dy), (16, 28 + dy)], 'amarillo')
        L.elipse(11, 31 + dy, 1, 1, 'negro')
    else:
        L.poligono([(15, 24 + dy), (11, 24 + dy), (9, 26 + dy), (11, 28 + dy), (16, 27 + dy)], 'amarillo')
        L.elipse(10, 27 + dy, 1, 1, 'negro')

    # piernas y zapatos
    if pose == 0:
        L.rect(16, 36, 18, 39, 'azul')
        L.elipse(17, 41, 3, 2, 'negro')
        L.rect(28, 36, 30, 39, 'azul')
        L.elipse(30, 41, 4, 2, 'negro', borde=True)
    else:
        L.rect(19, 36, 21, 39, 'azul')
        L.elipse(21, 41, 4, 2, 'negro')
        L.rect(24, 36, 26, 39, 'azul')
        L.elipse(26, 41, 4, 2, 'negro', borde=True)

    # capsula
    L.elipse(24, 11 + dy, 10, 9, 'amarillo', grupo=B)
    L.rect(14, 11 + dy, 34, 28 + dy, 'amarillo', grupo=B)
    L.elipse(24, 29 + dy, 10, 8, 'amarillo', grupo=B)
    EB = lambda x, y: L.celda[y][x][0] == B
    # overol
    L.recolorear(lambda x, y: y >= 26 + dy and EB(x, y), 'azul')
    L.recolorear(lambda x, y: y >= 23 + dy and 18 <= x <= 30 and EB(x, y), 'azul')
    L.recolorear(lambda x, y: 20 + dy <= y <= 22 + dy and (x in (18, 19, 29, 30)) and EB(x, y), 'azul')
    P([(23, 29), (24, 29), (25, 29), (23, 30), (24, 30), (25, 30)], 'gris')
    P([(22, 29), (22, 30), (26, 29), (26, 30)], 'gris')

    # pelo
    P([(22, 2), (24, 1), (26, 2), (23, 3), (25, 3)], 'pelo')
    # correa de las gafas
    for x in range(14, 35):
        P([(x, 14), (x, 15), (x, 16)], 'negro')
    # gafa: aro gris, ojo blanco, iris
    for (cx, cy, r, m) in ((28, 15, 6, 'gris'), (28, 15, 4, 'ojob')):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r // 2:
                    P([(x, y)], m)
    P([(29, 14), (30, 14), (29, 15), (30, 15), (29, 16), (30, 16)], 'ojo')
    P([(30, 15), (30, 16)], 'pupila')
    P([(28, 13)], 'ojob')
    # boca
    P([(27, 20), (28, 21), (29, 21), (30, 21), (31, 20)], 'boca')

    # brazo delantero
    if pose == 0:
        L.poligono([(30, 25 + dy), (33, 29 + dy), (35, 31 + dy), (37, 30 + dy), (35, 27 + dy), (32, 24 + dy)],
                   'amarillo', borde=True)
        L.elipse(36, 31 + dy, 1, 1, 'negro')
    else:
        L.poligono([(30, 25 + dy), (34, 25 + dy), (37, 24 + dy), (37, 26 + dy), (34, 28 + dy), (30, 28 + dy)],
                   'amarillo', borde=True)
        L.elipse(37, 25 + dy, 1, 1, 'negro')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'minion.png')
    vista([h], escala=9, salida=out / 'minion_x9.png')
    print('ok', h.size)
