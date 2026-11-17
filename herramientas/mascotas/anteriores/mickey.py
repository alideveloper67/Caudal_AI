# -*- coding: utf-8 -*-
"""Mickey corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('negro', '#2c2c3c', luz='#4a4a60', sombra='#16161e', contorno='#14141c')
    L.mat('piel', '#f8c490', sombra='#d8946c', contorno='#8a4a2a')
    L.mat('rojo', '#e83a30', sombra='#b8202a', contorno='#6a1018')
    L.mat('blanco', '#fafaf4', sombra='#b8b8d8', contorno='#6a6a90')
    L.mat('amarillo', '#f8c818', sombra='#d08a14', contorno='#7a4a08')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boton', '#fff0a0', fijo=True)
    L.mat('boca', '#8a2418', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0

    # cola (detrás)
    L.poligono([(15, 30 + dy), (9, 28 + dy), (6, 24 + dy), (8, 23 + dy), (11, 26 + dy), (16, 27 + dy)], 'negro', sin_sombra=True)

    # brazo trasero (detrás del cuerpo)
    if pose == 0:
        L.linea(19, 25, 14, 28, 'negro'); L.linea(19, 26, 14, 29, 'negro')
        L.elipse(12, 29, 2, 2, 'blanco')
    else:
        L.linea(19, 24 + dy, 15, 21 + dy, 'negro'); L.linea(19, 25 + dy, 15, 22 + dy, 'negro')
        L.elipse(13, 21 + dy, 2, 2, 'blanco')

    # piernas y zapatones
    if pose == 0:
        L.poligono([(17, 34), (21, 34), (19, 40), (15, 40)], 'negro', sin_sombra=True)
        L.elipse(14, 40, 4, 3, 'amarillo')
        L.poligono([(23, 34), (27, 34), (30, 40), (27, 40)], 'negro', sin_sombra=True)
        L.elipse(31, 40, 5, 3, 'amarillo', borde=True)
    else:
        L.poligono([(18, 33), (22, 33), (22, 39), (19, 39)], 'negro', sin_sombra=True)
        L.elipse(19, 40, 4, 3, 'amarillo')
        L.poligono([(23, 33), (27, 33), (27, 39), (24, 39)], 'negro', sin_sombra=True)
        L.elipse(29, 40, 5, 3, 'amarillo', borde=True)

    # torso + pantalón
    L.elipse(22, 26 + dy, 5, 5, 'negro')
    L.elipse(22, 31 + dy, 7, 5, 'rojo', borde=True)
    L.px(20, 30 + dy, 'boton'); L.px(20, 31 + dy, 'boton')
    L.px(26, 30 + dy, 'boton'); L.px(26, 31 + dy, 'boton')

    # orejas
    L.elipse(20, 5 + dy, 4, 4, 'negro')
    L.elipse(35, 4 + dy, 4, 4, 'negro')
    # cabeza
    L.elipse(28, 14 + dy, 8, 7, 'negro', borde=True)
    # cara de piel (3/4, hocico a la derecha)
    L.elipse(31, 16 + dy, 6, 5, 'piel', borde=True)
    L.rect(30, 11 + dy, 31, 14 + dy, 'blanco', sin_sombra=True, sin_contorno=True)
    L.rect(31, 12 + dy, 31, 14 + dy, 'ojo')
    L.px(31, 12 + dy, 'brillo')
    L.elipse(37, 15 + dy, 1, 1, 'ojo', sin_contorno=True, sin_sombra=True)
    L.linea(33, 19 + dy, 36, 18 + dy, 'boca')

    # brazo delantero con guante
    if pose == 0:
        L.linea(25, 25, 30, 28, 'negro'); L.linea(25, 26, 30, 29, 'negro')
        L.elipse(32, 28, 3, 3, 'blanco', borde=True)
    else:
        L.linea(25, 24 + dy, 31, 24 + dy, 'negro'); L.linea(25, 25 + dy, 31, 25 + dy, 'negro')
        L.elipse(33, 25 + dy, 3, 3, 'blanco', borde=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'mickey.png')
    vista([h], escala=9, salida=out / 'mickey_x9.png')
    print('ok', h.size)
