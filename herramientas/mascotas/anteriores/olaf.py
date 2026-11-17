# -*- coding: utf-8 -*-
"""Olaf caminando hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('nieve', '#f6f8fc', luz='#ffffff', sombra='#b8c0dc', contorno='#7a7ca4')
    L.mat('rama', '#7a4a22', sombra='#4e2c12', contorno='#2a1608')
    L.mat('zanahoria', '#f08a1c', sombra='#c05a10', contorno='#6a2c08')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boca', '#5a1e1e', fijo=True)
    L.mat('diente', '#ffffff', fijo=True)
    L.mat('boton', '#3a2a24', fijo=True)
    L.mat('pie', '#d8782a', sombra='#a8501a', contorno='#5a2808')


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    # pies
    if pose == 0:
        L.elipse(16, 41, 3, 2, 'pie')
        L.elipse(28, 41, 4, 2, 'pie', borde=True)
    else:
        L.elipse(20, 41, 3, 2, 'pie')
        L.elipse(26, 41, 4, 2, 'pie', borde=True)
    # brazo trasero
    if pose == 0:
        L.linea(15, 25, 8, 22, 'rama')
        L.linea(9, 22, 6, 19, 'rama')
        L.linea(10, 21, 9, 18, 'rama')
    else:
        L.linea(15, 24 + dy, 9, 27 + dy, 'rama')
        L.linea(10, 27 + dy, 6, 28 + dy, 'rama')
        L.linea(10, 27 + dy, 8, 30 + dy, 'rama')
    # tres bolas de nieve
    L.elipse(22, 35 + dy, 9, 6, 'nieve')
    L.elipse(22, 25 + dy, 7, 6, 'nieve', borde=True)
    L.elipse(24, 13 + dy, 9, 8, 'nieve', borde=True)
    # botones
    L.px(25, 24 + dy, 'boton')
    L.px(25, 28 + dy, 'boton')
    L.px(26, 34 + dy, 'boton')
    # pelitos
    L.linea(20, 5 + dy, 19, 1 + dy, 'rama')
    L.linea(24, 5 + dy, 24, 1 + dy, 'rama')
    L.linea(28, 5 + dy, 29, 2 + dy, 'rama')
    # brazo delantero
    if pose == 0:
        L.linea(28, 25, 35, 28, 'rama')
        L.linea(34, 28, 38, 26, 'rama')
        L.linea(34, 28, 38, 30, 'rama')
    else:
        L.linea(28, 24 + dy, 35, 21 + dy, 'rama')
        L.linea(34, 21 + dy, 38, 19 + dy, 'rama')
        L.linea(34, 21 + dy, 38, 23 + dy, 'rama')
    # cara: ojos, nariz, boca con dientes
    L.rect(24, 10 + dy, 25, 12 + dy, 'ojo')
    L.px(24, 10 + dy, 'brillo')
    L.rect(30, 10 + dy, 31, 12 + dy, 'ojo')
    L.px(30, 10 + dy, 'brillo')
    L.poligono([(32, 13 + dy), (40, 15 + dy), (32, 17 + dy)], 'zanahoria')
    L.rect(26, 18 + dy, 32, 20 + dy, 'boca', sin_contorno=True)
    L.rect(27, 18 + dy, 28, 18 + dy, 'diente')
    L.rect(30, 18 + dy, 31, 18 + dy, 'diente')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'olaf.png')
    vista([h], escala=9, salida=out / 'olaf_x9.png')
    print('ok', h.size)
