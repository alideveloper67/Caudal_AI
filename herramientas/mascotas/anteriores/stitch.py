# -*- coding: utf-8 -*-
"""Stitch corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('azul', '#4a7ed4', sombra='#2c58a8', contorno='#1c3a78')
    L.mat('celeste', '#a4d4f2', sombra='#74a8dc', contorno='#3a68a8')
    L.mat('rosa', '#ee8fb4', sombra='#c8588c', contorno='#7a2c58')
    L.mat('ojo', '#14142a', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('nariz', '#101020', fijo=True)
    L.mat('garra', '#2a3c78', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    e = 1 if pose == 1 else 0   # las orejas se mecen

    # cola
    L.elipse(12, 33 + dy, 3, 3, 'azul')
    # oreja trasera (larga, hacia atras y arriba)
    L.poligono([(26, 15 + dy), (18, 16 + dy), (10, 13 + dy + e), (4, 8 + dy + e), (3, 3 + dy + e), (8, 2 + dy + e),
                (15, 4 + dy), (25, 8 + dy)], 'azul')
    L.recolorear(lambda x, y: x <= 9 and y <= 10 + dy + e, 'rosa')
    # pata trasera
    if pose == 0:
        L.elipse(13, 40, 4, 3, 'azul')
    else:
        L.elipse(19, 40, 4, 3, 'azul')
    # oreja lejana (arriba, detras de la cabeza)
    L.poligono([(28, 10 + dy), (30, 4 + dy - e), (36, 1 + dy - e), (42, 2 + dy - e), (41, 7 + dy), (38, 11 + dy)], 'azul')
    L.recolorear(lambda x, y: y <= 4 + dy - e and x >= 34, 'rosa')
    # cuerpo y panza
    L.elipse(21, 31 + dy, 8, 7, 'azul')
    L.elipse(25, 32 + dy, 4, 5, 'celeste', sin_contorno=True)
    # cabeza
    L.elipse(29, 17 + dy, 10, 8, 'azul', borde=True)
    L.elipse(36, 20 + dy, 3, 3, 'celeste', sin_contorno=True, sin_sombra=True)
    # brazo
    L.elipse(28, 30 + dy, 2, 3, 'azul', sin_contorno=True)
    L.linea(26, 33 + dy, 29, 33 + dy, 'garra')
    # pata delantera
    if pose == 0:
        L.elipse(29, 40, 4, 3, 'azul', borde=True)
    else:
        L.elipse(26, 39, 4, 3, 'azul', borde=True)
    # cara
    L.elipse(32, 15 + dy, 1, 4, 'ojo')
    L.px(31, 12 + dy, 'brillo')
    L.rect(38, 17 + dy, 39, 18 + dy, 'nariz')
    L.linea(35, 22 + dy, 38, 21 + dy, 'garra')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'stitch.png')
    vista([h], escala=9, salida=out / 'stitch_x9.png')
    print('ok', h.size)
