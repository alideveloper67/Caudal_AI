# -*- coding: utf-8 -*-
"""Pompompurin corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('crema', '#f8e2a0', sombra='#e0b668', contorno='#8a5a22')
    L.mat('marron', '#a8662a', sombra='#7a4418', contorno='#442208')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('nariz', '#3a2210', fijo=True)
    L.mat('mejilla', '#f09a7a', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    # colita
    L.elipse(13, 33 + dy, 2, 3, 'crema')
    # oreja trasera (cae)
    L.elipse(17, 20 + dy - pose, 3, 7, 'marron')
    # oreja del otro lado (asoma detras de la cabeza)
    L.elipse(35, 20 + dy + pose, 3, 7, 'marron')
    # pie trasero
    L.elipse(14 if pose == 0 else 19, 40, 4, 3, 'marron')
    # cuerpo
    L.elipse(23, 32 + dy, 8, 7, 'crema')
    # bracito
    L.elipse(19, 30 + dy, 2, 3, 'crema', sin_contorno=True)
    # cabeza
    L.elipse(26, 16 + dy, 10, 8, 'crema', borde=True)
    # boina
    L.elipse(26, 8 + dy, 8, 3, 'marron', borde=True)
    L.rect(26, 3 + dy, 27, 5 + dy, 'marron', sin_sombra=True)
    # pie delantero
    L.elipse(29 if pose == 0 else 26, 40, 5, 3, 'marron', borde=True)
    # cara: ojos, hocico
    L.rect(26, 14 + dy, 27, 16 + dy, 'ojo')
    L.px(26, 14 + dy, 'brillo')
    L.rect(32, 14 + dy, 33, 16 + dy, 'ojo')
    L.px(32, 14 + dy, 'brillo')
    L.elipse(34, 18 + dy, 1, 1, 'nariz', sin_sombra=True, sin_contorno=True)
    L.px(30, 21 + dy, 'nariz')
    L.px(31, 22 + dy, 'nariz')
    L.px(32, 22 + dy, 'nariz')
    L.px(33, 21 + dy, 'nariz')
    L.elipse(23, 19 + dy, 1, 1, 'mejilla', sin_sombra=True, sin_contorno=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'purin.png')
    vista([h], escala=9, salida=out / 'purin_x9.png')
    print('ok', h.size)
