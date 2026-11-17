# -*- coding: utf-8 -*-
"""My Melody corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('blanco', '#fbfbfd', luz='#ffffff', sombra='#c6c8e2', contorno='#8c84aa')
    L.mat('rosa', '#f66a9c', luz='#ff9cbc', sombra='#d04688', contorno='#8a2458')
    L.mat('rosaclaro', '#ffb4cc', sombra='#e888ae', contorno='#a84a78')
    L.mat('flor', '#ffe84a', sombra='#f2b422', contorno='#9a5410')
    L.mat('ojo', '#16141e', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('mejilla', '#ff8fb4', fijo=True)
    L.mat('nariz', '#e0407a', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    f = pose  # las orejas ondean

    # colita
    L.elipse(12, 32 + dy, 2, 2, 'blanco')
    # pata trasera
    L.elipse(13 if pose == 0 else 18, 40, 4, 3, 'blanco')
    # cuerpo (capa rosa)
    L.elipse(21, 32 + dy, 7, 7, 'rosa')
    # orejas largas caidas de la capucha, ondeando hacia atras
    L.poligono([(21, 14 + dy), (14, 4 + dy - f), (6, 3 + dy - f), (4, 9 + dy + f), (10, 11 + dy + f),
                (18, 18 + dy)], 'rosa')
    L.poligono([(8, 6 + dy - f), (13, 6 + dy - f), (9, 9 + dy + f)], 'rosaclaro', sin_contorno=True, sin_sombra=True)
    L.poligono([(26, 12 + dy), (24, 3 + dy), (26, 0 + dy - f), (31, 3 + dy), (31, 12 + dy)], 'rosa')
    L.poligono([(26, 7 + dy), (27, 3 + dy), (29, 4 + dy), (29, 9 + dy)], 'rosaclaro', sin_contorno=True, sin_sombra=True)
    # capucha + cara
    L.elipse(29, 20 + dy, 11, 8, 'rosa', borde=True)
    L.elipse(32, 21 + dy, 8, 6, 'blanco', borde=True)
    # flor en la capucha
    for x, y in ((34, 9), (36, 11), (34, 12), (32, 11), (34, 11)):
        pass
    L.elipse(35, 10 + dy, 1, 1, 'rosaclaro', borde=True)
    L.elipse(33, 10 + dy, 1, 1, 'rosaclaro')
    L.elipse(37, 10 + dy, 1, 1, 'rosaclaro')
    L.elipse(35, 8 + dy, 1, 1, 'rosaclaro')
    L.elipse(35, 12 + dy, 1, 1, 'rosaclaro')
    L.px(35, 10 + dy, 'flor')
    # bracito
    a = 1 if pose == 0 else -1
    L.elipse(27 + a, 31 + dy, 2, 2, 'blanco', borde=True)
    # pata delantera
    L.elipse(29 if pose == 0 else 26, 40, 4, 3, 'blanco', borde=True)
    # cara
    L.rect(34, 19 + dy, 35, 21 + dy, 'ojo')
    L.px(34, 19 + dy, 'brillo')
    L.rect(39, 19 + dy, 40, 21 + dy, 'ojo')
    L.px(39, 19 + dy, 'brillo')
    L.rect(37, 22 + dy, 38, 22 + dy, 'nariz')
    L.px(33, 23 + dy, 'mejilla')
    L.px(34, 23 + dy, 'mejilla')
    L.px(41, 23 + dy, 'mejilla')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'mymelody.png')
    vista([h], escala=9, salida=out / 'mymelody_x9.png')
    print('ok', h.size)
