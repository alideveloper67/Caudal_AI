# -*- coding: utf-8 -*-
"""Nyan Cat volando hacia la derecha (2 cuadros de 56x44). El arcoíris lo dibuja la app."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pix  # noqa: E402
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('galleta', '#f8c890', sombra='#d89860', contorno='#8a4a20')
    L.mat('rosa', '#f89ac4', sombra='#d8689c', contorno='#8a2a5a')
    L.mat('chispa', '#e03a82', fijo=True)
    L.mat('gris', '#9a9aae', luz='#c0c0d2', sombra='#6a6a88', contorno='#3a3a52')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('mejilla', '#f87aa8', fijo=True)
    L.mat('boca', '#2a2a3a', fijo=True)


def _oct(x0, y0, x1, y1, c=3):
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def cuadro(pose):
    pix.W = 56
    try:
        L = Lienzo()
        materiales(L)
        dy = -1 if pose == 1 else 0
        # cola gris (detrás)
        if pose == 0:
            L.poligono([(10, 22 + dy), (2, 25 + dy), (1, 29 + dy), (6, 28 + dy), (12, 27 + dy)], 'gris')
        else:
            L.poligono([(10, 22 + dy), (3, 18 + dy), (1, 22 + dy), (6, 24 + dy), (12, 27 + dy)], 'gris')
        # patas traseras
        if pose == 0:
            L.rect(12, 33, 15, 38, 'gris')
            L.rect(20, 33, 23, 37, 'gris')
        else:
            L.rect(14, 33, 17, 37, 'gris')
            L.rect(22, 33, 25, 38, 'gris')
        # pop-tart: galleta + glaseado rosa
        L.poligono(_oct(9, 8 + dy, 41, 34 + dy, 4), 'galleta')
        L.poligono(_oct(12, 11 + dy, 38, 31 + dy, 3), 'rosa', sin_contorno=True)
        for (x, y) in [(16, 15), (24, 14), (32, 16), (19, 22), (28, 21), (35, 25), (15, 27), (24, 28), (31, 29)]:
            L.px(x, y + dy, 'chispa')
        # patas delanteras
        if pose == 0:
            L.rect(34, 33, 37, 38, 'gris')
            L.rect(42, 34, 45, 39, 'gris')
        else:
            L.rect(36, 33, 39, 37, 'gris')
            L.rect(40, 33, 43, 38, 'gris')
        # orejas y cabeza
        L.poligono([(39, 23 + dy), (40, 16 + dy), (45, 21 + dy)], 'gris')
        L.poligono([(49, 21 + dy), (53, 16 + dy), (54, 24 + dy)], 'gris')
        L.elipse(46, 29 + dy, 9, 7, 'gris', borde=True)
        # cara
        L.rect(42, 26 + dy, 43, 28 + dy, 'ojo')
        L.px(42, 26 + dy, 'brillo')
        L.rect(50, 26 + dy, 51, 28 + dy, 'ojo')
        L.px(50, 26 + dy, 'brillo')
        L.elipse(40, 32 + dy, 1, 1, 'mejilla', sin_sombra=True, sin_contorno=True)
        L.elipse(52, 32 + dy, 1, 1, 'mejilla', sin_sombra=True, sin_contorno=True)
        L.linea(44, 32 + dy, 45, 33 + dy, 'boca')
        L.linea(45, 33 + dy, 47, 33 + dy, 'boca')
        L.linea(47, 33 + dy, 48, 32 + dy, 'boca')
        return L.render()
    finally:
        pix.W = 48


def hojas():
    a, b = cuadro(0), cuadro(1)   # cada cuadro restaura el ancho a 48 al terminar
    pix.W = 56                    # la hoja se une con el ancho de Nyan (2 x 56)
    try:
        return hoja([a, b])
    finally:
        pix.W = 48


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'nyan.png')
    vista([h], escala=8, salida=out / 'nyan_x9.png')
    print('ok', h.size)
