# -*- coding: utf-8 -*-
"""Doraemon corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('azul', '#2a9ae0', sombra='#1a68b8', contorno='#124a88')
    L.mat('blanco', '#fafaf8', sombra='#c4cce4', contorno='#5a78a8')
    L.mat('rojo', '#e83a30', sombra='#b8222c', contorno='#781820')
    L.mat('oro', '#f8d030', sombra='#d8981c', contorno='#8a5810')
    L.mat('ojo', '#14182c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('linea', '#26324e', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    e = 1 if pose == 1 else 0

    # cola roja
    L.linea(13, 34 + dy, 10, 35 + dy - e, 'rojo')
    L.elipse(9, 35 + dy - e * 2, 2, 2, 'rojo')
    # pie trasero
    if pose == 0:
        L.elipse(13, 41, 4, 2, 'blanco')
    else:
        L.elipse(19, 41, 4, 2, 'blanco')
    # cuerpo y panza
    L.elipse(21, 33 + dy, 8, 6, 'azul')
    L.elipse(25, 34 + dy, 5, 4, 'blanco', sin_contorno=True)
    L.linea(21, 33 + dy, 22, 31 + dy, 'linea')
    L.linea(22, 31 + dy, 28, 31 + dy, 'linea')
    # cabeza y cara
    L.elipse(25, 13 + dy, 12, 11, 'azul', borde=True)
    L.elipse(29, 15 + dy, 9, 8, 'blanco', sin_contorno=True)
    # collar y cascabel
    L.elipse(26, 26 + dy, 8, 2, 'rojo', borde=True)
    L.elipse(30, 29 + dy, 1, 1, 'oro', sin_contorno=True)
    L.px(30, 29 + dy, 'linea')
    # brazo con mano blanca
    L.elipse(24, 31 + dy, 2, 3, 'azul', borde=True)
    L.elipse(27 + e, 33 + dy - e, 2, 2, 'blanco', borde=True)
    # pie delantero
    if pose == 0:
        L.elipse(30, 41, 4, 2, 'blanco', borde=True)
    else:
        L.elipse(26, 40, 4, 2, 'blanco', borde=True)
    # ojos, nariz, boca y bigotes
    for ex in (28, 33):
        L.rect(ex, 6 + dy, ex + 3, 12 + dy, 'linea')
        L.rect(ex + 1, 7 + dy, ex + 2, 11 + dy, 'blanco', sin_contorno=True, sin_sombra=True)
        for cx_, cy_ in ((ex, 6), (ex + 3, 6), (ex, 12), (ex + 3, 12)):
            L.celda[cy_ + dy][cx_] = (L.celda[cy_ + dy][cx_][0], 'blanco')
    L.rect(30, 8 + dy, 30, 10 + dy, 'ojo')
    L.rect(35, 8 + dy, 35, 10 + dy, 'ojo')
    L.px(30, 8 + dy, 'brillo')
    L.px(35, 8 + dy, 'brillo')
    L.rect(33, 13 + dy, 35, 15 + dy, 'rojo', sin_sombra=True, sin_contorno=True)
    L.px(33, 13 + dy, 'brillo')
    L.linea(34, 16 + dy, 34, 19 + dy, 'linea')
    L.linea(30, 20 + dy, 33, 21 + dy, 'linea')
    L.linea(34, 20 + dy, 37, 19 + dy, 'linea')
    L.linea(30, 15 + dy, 28, 14 + dy, 'linea')
    L.linea(30, 17 + dy, 28, 18 + dy, 'linea')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'doraemon.png')
    vista([h], escala=9, salida=out / 'doraemon_x9.png')
    print('ok', h.size)
