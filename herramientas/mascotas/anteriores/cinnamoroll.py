# -*- coding: utf-8 -*-
"""Cinnamoroll corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('blanco', '#fbfbfd', luz='#ffffff', sombra='#c6c8e2', contorno='#8c84aa')
    L.mat('celeste', '#8cd0f4', luz='#bfe8ff', sombra='#5a9ae0', contorno='#2e5aa0')
    L.mat('rizo', '#c6c8e2', fijo=True)
    L.mat('ojo', '#2c58c8', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('mejilla', '#ff8fb4', fijo=True)
    L.mat('nariz', '#3a3050', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    f = pose

    # cola enroscada
    L.elipse(11, 31 + dy, 4, 4, 'blanco')
    for p in ((9, 30), (10, 29), (11, 29), (12, 30), (12, 31), (11, 32)):
        L.px(p[0], p[1] + dy, 'rizo')
    # pata trasera
    L.elipse(13 if pose == 0 else 18, 40, 4, 3, 'blanco')
    # cuerpo
    L.elipse(21, 33 + dy, 7, 6, 'blanco')
    # orejas larguisimas celestes, ondeando hacia atras
    L.poligono([(27, 12 + dy), (18, 5 + dy - f), (9, 3 + dy - 2 * f), (8, 7 + dy - f), (17, 10 + dy), (25, 16 + dy)], 'celeste')
    L.poligono([(23, 14 + dy), (13, 12 + dy - f), (3, 12 + dy - 2 * f), (2, 16 + dy - f), (12, 18 + dy), (20, 21 + dy)], 'celeste')
    # cabeza redonda
    L.elipse(30, 20 + dy, 10, 8, 'blanco', borde=True)
    # bracito
    a = 1 if pose == 0 else -1
    L.elipse(27 + a, 32 + dy, 2, 2, 'blanco', borde=True)
    # pata delantera
    L.elipse(29 if pose == 0 else 26, 40, 4, 3, 'blanco', borde=True)
    # cara: ojos azules grandes, nariz, mejillas rosas
    L.rect(34, 18 + dy, 35, 21 + dy, 'ojo')
    L.px(34, 18 + dy, 'brillo')
    L.rect(39, 18 + dy, 40, 21 + dy, 'ojo')
    L.px(39, 18 + dy, 'brillo')
    L.px(38, 22 + dy, 'nariz')
    L.rect(32, 23 + dy, 33, 23 + dy, 'mejilla')
    L.rect(41, 23 + dy, 41, 23 + dy, 'mejilla')
    L.linea(36, 24 + dy, 38, 24 + dy, 'nariz')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'cinnamoroll.png')
    vista([h], escala=9, salida=out / 'cinnamoroll_x9.png')
    print('ok', h.size)
