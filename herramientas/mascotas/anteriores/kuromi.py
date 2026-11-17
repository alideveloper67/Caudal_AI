# -*- coding: utf-8 -*-
"""Kuromi corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('blanco', '#fbfbfd', luz='#ffffff', sombra='#c6c8e2', contorno='#8c84aa')
    L.mat('negro', '#403456', luz='#6a5a8a', sombra='#241c36', contorno='#2a2040')
    L.mat('rosa', '#f66a9c', luz='#ff9cbc', sombra='#d04688', contorno='#8a2458')
    L.mat('morado', '#8a5ac8', sombra='#5e3a9a', contorno='#3a2068')
    L.mat('ojo', '#16141e', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('mejilla', '#ff8fb4', fijo=True)
    L.mat('boca', '#8a2458', fijo=True)
    L.mat('hueso', '#16141e', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    f = pose

    # colita puntiaguda
    L.poligono([(14, 35 + dy), (8, 31 + dy - f), (5, 26 + dy - 2 * f), (11, 29 + dy), (16, 31 + dy)], 'negro')
    # pata trasera
    L.elipse(13 if pose == 0 else 18, 40, 4, 3, 'blanco')
    # cuerpo
    L.elipse(21, 32 + dy, 7, 7, 'negro')
    # orejas puntiagudas (una cae un poco hacia atras)
    L.poligono([(22, 14 + dy), (14, 6 + dy - f), (11, 2 + dy - f), (26, 10 + dy)], 'negro')
    L.poligono([(30, 10 + dy), (36, 2 + dy - f), (40, 5 + dy), (39, 14 + dy)], 'negro')
    L.poligono([(17, 8 + dy - f), (14, 4 + dy - f), (22, 9 + dy)], 'rosa', sin_contorno=True, sin_sombra=True)
    L.poligono([(34, 6 + dy), (36, 5 + dy - f), (37, 8 + dy)], 'rosa', sin_contorno=True, sin_sombra=True)
    # capucha y cara
    L.elipse(29, 20 + dy, 11, 8, 'negro', borde=True)
    L.elipse(32, 22 + dy, 8, 6, 'blanco', borde=True)
    # calavera rosa en la capucha
    L.elipse(27, 15 + dy, 3, 2, 'rosa', borde=True)
    L.rect(26, 17 + dy, 28, 18 + dy, 'rosa', sin_contorno=True)
    L.px(26, 15 + dy, 'hueso')
    L.px(28, 15 + dy, 'hueso')
    L.px(27, 17 + dy, 'hueso')
    # bracito
    a = 1 if pose == 0 else -1
    L.elipse(27 + a, 31 + dy, 2, 2, 'blanco', borde=True)
    # pata delantera
    L.elipse(29 if pose == 0 else 26, 40, 4, 3, 'blanco', borde=True)
    # cara traviesa: ojos con ceja torcida, sonrisa con colmillo
    L.rect(34, 20 + dy, 35, 22 + dy, 'ojo')
    L.px(34, 20 + dy, 'brillo')
    L.rect(39, 20 + dy, 40, 22 + dy, 'ojo')
    L.px(39, 20 + dy, 'brillo')
    L.linea(33, 18 + dy, 36, 19 + dy, 'ojo')
    L.linea(38, 19 + dy, 41, 18 + dy, 'ojo')
    L.px(37, 23 + dy, 'ojo')
    L.linea(35, 24 + dy, 39, 24 + dy, 'boca')
    L.px(38, 25 + dy, 'blanco')
    L.px(33, 24 + dy, 'mejilla')
    L.px(41, 24 + dy, 'mejilla')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'kuromi.png')
    vista([h], escala=9, salida=out / 'kuromi_x9.png')
    print('ok', h.size)
