# -*- coding: utf-8 -*-
"""Pusheen corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('gris', '#bcbcc8', luz='#dcdce6', sombra='#8a88a8', contorno='#5a5470')
    L.mat('raya', '#7c7a92', sombra='#5a5874', contorno='#3a3650')
    L.mat('crema', '#ece4dc', sombra='#c4bccc', contorno='#8a8098')
    L.mat('ojo', '#16141e', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('mejilla', '#ffa0b8', fijo=True)
    L.mat('nariz', '#e0809c', fijo=True)
    L.mat('boca', '#3a3050', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    f = pose

    # cola rayada, levantada
    L.poligono([(10, 34 + dy), (4, 30 + dy - f), (2, 22 + dy - 2 * f), (6, 20 + dy - 2 * f), (8, 27 + dy), (14, 29 + dy)], 'gris')
    L.rect(3, 23 + dy - 2 * f, 6, 24 + dy - 2 * f, 'raya', sin_contorno=True)
    L.rect(4, 27 + dy - f, 7, 28 + dy - f, 'raya', sin_contorno=True)
    # patitas traseras
    L.elipse(12 if pose == 0 else 17, 41, 3, 2, 'gris')
    # cuerpo gordito
    L.elipse(22, 32 + dy, 13, 8, 'gris')
    # barriga crema
    L.elipse(24, 36 + dy, 7, 3, 'crema', sin_contorno=True)
    # rayas del lomo
    for x in (14, 19, 24):
        L.rect(x, 24 + dy, x + 1, 26 + dy, 'raya', sin_contorno=True, sin_sombra=True)
    # orejitas
    L.poligono([(22, 15 + dy), (23, 8 + dy), (29, 13 + dy)], 'gris')
    L.poligono([(34, 13 + dy), (38, 7 + dy), (41, 15 + dy - f)], 'gris')
    # cabeza ancha
    L.elipse(31, 20 + dy, 11, 8, 'gris', borde=True)
    # rayas de la frente
    for x in (29, 32, 35):
        L.rect(x, 13 + dy, x, 15 + dy, 'raya', sin_contorno=True, sin_sombra=True)
    # bracito
    a = 1 if pose == 0 else -1
    L.elipse(28 + a, 33 + dy, 2, 2, 'gris', borde=True)
    # patita delantera
    L.elipse(30 if pose == 0 else 27, 41, 3, 2, 'gris', borde=True)
    # cara
    L.rect(35, 19 + dy, 36, 21 + dy, 'ojo')
    L.px(35, 19 + dy, 'brillo')
    L.rect(40, 19 + dy, 41, 21 + dy, 'ojo')
    L.px(40, 19 + dy, 'brillo')
    L.px(38, 22 + dy, 'nariz')
    L.linea(37, 23 + dy, 38, 24 + dy, 'boca')
    L.linea(38, 24 + dy, 40, 23 + dy, 'boca')
    L.rect(33, 23 + dy, 34, 23 + dy, 'mejilla')
    L.px(42, 23 + dy, 'mejilla')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'pusheen.png')
    vista([h], escala=9, salida=out / 'pusheen_x9.png')
    print('ok', h.size)
