# -*- coding: utf-8 -*-
"""Totoro corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('gris', '#8a98a8', sombra='#5e6c8c', contorno='#3a4258')
    L.mat('crema', '#f4e8c4', sombra='#d0bc9c', contorno='#7a6a58')
    L.mat('marca', '#a8987c', fijo=True)
    L.mat('ojo', '#14182c', fijo=True)
    L.mat('blanco', '#fafaf8', fijo=True)
    L.mat('boca', '#2a2e44', fijo=True)
    L.mat('garra', '#3a4258', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    e = 1 if pose == 1 else 0

    # cola
    L.elipse(8, 33 + dy - e, 3, 3, 'gris')
    # pie trasero
    if pose == 0:
        L.elipse(13, 41, 4, 2, 'gris')
    else:
        L.elipse(19, 41, 4, 2, 'gris')
    # orejas puntiagudas
    L.poligono([(14, 15 + dy), (12 - e, 5 + dy), (13 - e, 2 + dy), (19, 9 + dy), (21, 14 + dy)], 'gris')
    L.poligono([(26, 13 + dy), (27 + e, 4 + dy), (28 + e, 1 + dy), (33, 8 + dy), (34, 14 + dy)], 'gris')
    # cuerpo y panza
    L.elipse(23, 26 + dy, 15, 13, 'gris')
    L.elipse(28, 31 + dy, 8, 8, 'crema', sin_contorno=True)
    for (vx, vy) in ((24, 28), (29, 28), (27, 33), (32, 33)):
        L.px(vx, vy + dy, 'marca')
        L.px(vx + 1, vy + 1 + dy, 'marca')
        L.px(vx + 2, vy + dy, 'marca')
    # brazo
    if pose == 0:
        L.elipse(36, 32 + dy, 2, 4, 'gris', borde=True)
    else:
        L.elipse(37, 30 + dy, 2, 4, 'gris', borde=True)
    # pie delantero
    if pose == 0:
        L.elipse(31, 41, 4, 2, 'gris', borde=True)
    else:
        L.elipse(27, 40, 4, 2, 'gris', borde=True)
    # cara: ojos, nariz, sonrisa, bigotes
    for ex in (25, 32):
        L.rect(ex, 14 + dy, ex + 2, 17 + dy, 'blanco')
        L.px(ex + 2, 15 + dy, 'ojo')
        L.px(ex + 2, 16 + dy, 'ojo')
    L.rect(30, 19 + dy, 33, 20 + dy, 'ojo')
    L.linea(26, 23 + dy, 29, 23 + dy, 'boca')
    L.linea(29, 24 + dy, 35, 24 + dy, 'boca')
    L.px(36, 23 + dy, 'boca')
    L.linea(24, 20 + dy, 19, 19 + dy + e, 'garra')
    L.linea(24, 22 + dy, 19, 23 + dy - e, 'garra')
    L.linea(38, 19 + dy, 45, 18 + dy - e, 'garra')
    L.linea(38, 22 + dy, 45, 23 + dy + e, 'garra')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'totoro.png')
    vista([h], escala=9, salida=out / 'totoro_x9.png')
    print('ok', h.size)
