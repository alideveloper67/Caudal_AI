# -*- coding: utf-8 -*-
"""Snoopy corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('blanco', '#f6f6fa', sombra='#b4b8da', contorno='#3a3a5c')
    L.mat('negro', '#2a2832', sombra='#16141c', contorno='#0a080e')
    L.mat('rojo', '#e03a30', sombra='#b0222c', contorno='#6c1018')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('nariz', '#16141c', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    B = 'b'

    def P(lista, m):
        for (x, y) in lista:
            L.rect(x, y + dy, x, y + dy, m, grupo=B)

    # cola negra
    L.poligono([(15, 26 + dy), (10, 22 + dy), (9, 25 + dy), (13, 30 + dy)], 'negro')
    # brazo trasero
    if pose == 0:
        L.poligono([(15, 23 + dy), (11, 27 + dy), (11, 30 + dy), (14, 30 + dy), (17, 27 + dy)], 'blanco')
    else:
        L.poligono([(15, 23 + dy), (11, 23 + dy), (9, 26 + dy), (12, 28 + dy), (17, 27 + dy)], 'blanco')

    # patas con pies largos
    if pose == 0:
        L.rect(16, 36, 18, 39, 'blanco')
        L.elipse(18, 41, 4, 2, 'blanco')
        L.rect(28, 36, 30, 39, 'blanco')
        L.elipse(31, 41, 5, 2, 'blanco', borde=True)
    else:
        L.rect(19, 36, 21, 39, 'blanco')
        L.elipse(21, 41, 4, 2, 'blanco')
        L.rect(25, 36, 27, 39, 'blanco')
        L.elipse(28, 41, 5, 2, 'blanco', borde=True)

    # cuerpo
    L.elipse(23, 29 + dy, 8, 8, 'blanco')
    # mancha negra en la espalda
    L.poligono([(15, 25 + dy), (19, 22 + dy), (20, 28 + dy), (16, 31 + dy)], 'negro', sin_sombra=True,
               borde=True)

    # cabeza + hocico largo
    L.elipse(26, 11 + dy, 8, 7, 'blanco', grupo=B)
    L.elipse(34, 14 + dy, 5, 3, 'blanco', grupo=B)
    # nariz negra grande
    L.elipse(39, 12 + dy, 2, 2, 'nariz', grupo=B)
    # collar rojo
    L.rect(22, 19 + dy, 30, 20 + dy, 'rojo', sin_sombra=True, borde=True)
    # ojo
    P([(30, 9), (30, 10)], 'ojo')
    P([(31, 9)], 'brillo')
    P([(35, 16), (36, 16), (37, 16)], 'ojo')
    # oreja negra larga colgando
    if pose == 0:
        L.poligono([(21, 6 + dy), (27, 5 + dy), (28, 11 + dy), (27, 19 + dy), (22, 22 + dy), (19, 14 + dy)],
                   'negro', borde=True)
    else:
        L.poligono([(21, 6 + dy), (27, 5 + dy), (28, 11 + dy), (28, 18 + dy), (24, 22 + dy), (19, 13 + dy)],
                   'negro', borde=True)

    # brazo delantero
    if pose == 0:
        L.poligono([(30, 24 + dy), (34, 27 + dy), (37, 29 + dy), (37, 32 + dy), (33, 32 + dy), (29, 28 + dy)],
                   'blanco', borde=True)
    else:
        L.poligono([(30, 24 + dy), (35, 23 + dy), (38, 22 + dy), (39, 25 + dy), (34, 28 + dy), (29, 28 + dy)],
                   'blanco', borde=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'snoopy.png')
    vista([h], escala=9, salida=out / 'snoopy_x9.png')
    print('ok', h.size)
