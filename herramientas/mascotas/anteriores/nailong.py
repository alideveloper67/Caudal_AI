# -*- coding: utf-8 -*-
"""Nailong corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('amarillo', '#f8d848', sombra='#e0a424', contorno='#946012')
    L.mat('crema', '#fff0b4', sombra='#e8c47c', contorno='#a8782c')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boca', '#8a2418', fijo=True)
    L.mat('mejilla', '#f09a6a', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    # cola corta
    L.poligono([(15, 33 + dy), (8, 33 + dy - pose * 2), (6, 30 + dy - pose * 2), (10, 29 + dy - pose * 2), (16, 29 + dy)], 'amarillo')
    # pie trasero
    L.elipse(15 if pose == 0 else 19, 40, 4, 3, 'amarillo')
    # cuernitos
    L.poligono([(22, 8 + dy), (21, 2 + dy), (26, 7 + dy)], 'crema')
    L.poligono([(31, 7 + dy), (34, 2 + dy), (36, 8 + dy)], 'crema')
    # cuerpo regordete con barriguita
    L.elipse(23, 30 + dy, 10, 9, 'amarillo')
    L.elipse(26, 32 + dy, 6, 6, 'crema', borde=True)
    # bracito
    L.elipse(18, 28 + dy, 2, 3, 'amarillo', sin_contorno=True)
    # cabeza grande
    L.elipse(27, 15 + dy, 11, 8, 'amarillo', borde=True)
    # pie delantero
    L.elipse(30 if pose == 0 else 27, 40, 5, 3, 'amarillo', borde=True)
    # cara simple y chiquita
    L.rect(32, 14 + dy, 33, 16 + dy, 'ojo')
    L.px(32, 14 + dy, 'brillo')
    L.rect(24, 14 + dy, 25, 16 + dy, 'ojo')
    L.px(24, 14 + dy, 'brillo')
    L.linea(29, 20 + dy, 31, 20 + dy, 'boca')
    L.px(28, 19 + dy, 'boca')
    L.px(32, 19 + dy, 'boca')
    L.elipse(35, 19 + dy, 1, 1, 'mejilla', sin_sombra=True, sin_contorno=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'nailong.png')
    vista([h], escala=9, salida=out / 'nailong_x9.png')
    print('ok', h.size)
