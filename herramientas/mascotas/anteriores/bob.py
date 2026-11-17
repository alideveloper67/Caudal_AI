# -*- coding: utf-8 -*-
"""Bob Esponja corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('amarillo', '#f4d82a', sombra='#e0a416', contorno='#8a5a0c')
    L.mat('marron', '#9a5a22', sombra='#6c3a18', contorno='#3e2010')
    L.mat('blanco', '#f4f4f8', sombra='#b8b8d8', contorno='#5c5c78')
    L.mat('rojo', '#e03028', sombra='#b01c28', contorno='#6c1018')
    L.mat('negro', '#26242e', sombra='#14121a', contorno='#0c0a10')
    L.mat('poro', '#c8981a', fijo=True)
    L.mat('azul', '#3a9ce0', fijo=True)
    L.mat('aro', '#7a5a2a', fijo=True)
    L.mat('ojob', '#f8f8ff', fijo=True)
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boca', '#8a2418', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0

    # brazo trasero (detras del cuerpo)
    if pose == 0:
        L.poligono([(9, 22 + dy), (5, 26 + dy), (4, 30 + dy), (6, 31 + dy), (10, 27 + dy), (11, 24 + dy)], 'amarillo')
    else:
        L.poligono([(9, 22 + dy), (5, 24 + dy), (3, 27 + dy), (5, 28 + dy), (8, 26 + dy), (11, 24 + dy)], 'amarillo')

    # piernas finas, calcetin blanco y zapato
    if pose == 0:
        L.rect(13, 32, 15, 38, 'amarillo')
        L.rect(13, 36, 15, 38, 'blanco')
        L.elipse(15, 41, 3, 2, 'negro')
        L.rect(27, 32, 29, 38, 'amarillo')
        L.rect(27, 36, 29, 38, 'blanco')
        L.elipse(30, 41, 4, 2, 'negro', borde=True)
    else:
        L.rect(16, 32, 18, 38, 'amarillo')
        L.rect(16, 36, 18, 38, 'blanco')
        L.elipse(19, 41, 4, 2, 'negro')
        L.rect(23, 32, 25, 38, 'amarillo')
        L.rect(23, 36, 25, 38, 'blanco')
        L.elipse(26, 41, 4, 2, 'negro', borde=True)

    # cuerpo-esponja cuadrado
    L.poligono([(11, 3 + dy), (33, 3 + dy), (35, 5 + dy), (35, 24 + dy), (33, 26 + dy), (11, 26 + dy),
                (9, 24 + dy), (9, 5 + dy)], 'amarillo', grupo='b')
    L.recolorear(lambda x, y: y >= 25 + dy and y <= 26 + dy and 9 <= x <= 35, 'blanco')
    # pantalon
    L.rect(9, 27 + dy, 35, 32 + dy, 'marron', borde=True)
    L.rect(9, 27 + dy, 35, 27 + dy, 'blanco', sin_contorno=True, sin_sombra=True)
    # corbata
    L.poligono([(23, 26 + dy), (27, 26 + dy), (26, 30 + dy), (24, 30 + dy)], 'rojo', sin_sombra=True)

    # cara (mismo grupo que el cuerpo: asi no deja huecos de sombra)
    B = 'b'

    def P(lista, m):
        for (x, y) in lista:
            L.rect(x, y + dy, x, y + dy, m, grupo=B)

    for x, y in ((12, 7), (15, 17), (12, 21), (19, 5), (31, 5)):
        P([(x, y)], 'poro')
    for cx in (23, 31):
        L.elipse(cx, 11 + dy, 3, 3, 'aro', grupo=B)
        L.elipse(cx, 11 + dy, 2, 2, 'ojob', grupo=B)
        L.rect(cx + 2, 10 + dy, cx + 3, 12 + dy, 'azul', grupo=B)
        P([(cx + 3, 11)], 'ojo')
    L.rect(34, 14 + dy, 37, 16 + dy, 'amarillo', grupo=B)
    L.rect(36, 14 + dy, 37, 14 + dy, 'aro', grupo=B)
    L.rect(38, 15 + dy, 38, 16 + dy, 'aro', grupo=B)
    P([(23, 19), (24, 20), (25, 21)], 'boca')
    P([(x, 21) for x in range(26, 33)], 'boca')
    P([(33, 20), (34, 19)], 'boca')
    L.rect(28, 22 + dy, 29, 23 + dy, 'brillo', grupo=B)
    P([(20, 18), (21, 18), (20, 19), (21, 19)], 'poro')

    # brazo delantero
    if pose == 0:
        L.poligono([(32, 22 + dy), (36, 26 + dy), (39, 27 + dy), (39, 29 + dy), (35, 29 + dy), (31, 25 + dy)],
                   'amarillo', borde=True)
    else:
        L.poligono([(32, 22 + dy), (36, 22 + dy), (39, 21 + dy), (39, 23 + dy), (36, 25 + dy), (31, 25 + dy)],
                   'amarillo', borde=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'bob.png')
    vista([h], escala=9, salida=out / 'bob_x9.png')
    print('ok', h.size)
