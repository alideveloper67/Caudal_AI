# -*- coding: utf-8 -*-
"""Pikachu corriendo hacia la derecha (2 cuadros de 48x44). Es el modelo de estilo del resto de mascotas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('amarillo', '#f8e458', sombra='#f2b422', contorno='#9a5410')
    L.mat('marron', '#a8601a', sombra='#7a420e', contorno='#4a2808')
    L.mat('punta', '#34343c', sombra='#1c1c22', contorno='#101014')
    L.mat('rojo', '#e8402e', sombra='#bc2420', contorno='#7a1810')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boca', '#8a2418', fijo=True)
    L.mat('nariz', '#3a2210', fijo=True)


def cuadro(pose):
    """pose 0: contacto (pata delantera adelante, trasera atrás) · pose 1: vuelo (patas recogidas, cuerpo arriba)."""
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0

    # cola: va primero (queda detrás de todo). Base marrón y rayo amarillo en zigzag.
    L.poligono([(14, 35 + dy), (9, 32 + dy), (11, 29 + dy), (15, 31 + dy)], 'marron', sin_sombra=True)
    L.poligono([(12, 31 + dy), (6, 28 + dy), (9, 24 + dy), (4, 21 + dy), (6, 16 + dy), (3, 13 + dy), (2, 8 + dy),
                (12, 8 + dy), (12, 13 + dy), (9, 15 + dy), (13, 19 + dy), (11, 23 + dy), (15, 27 + dy)], 'amarillo')

    # pata trasera (detrás del cuerpo)
    if pose == 0:
        L.elipse(12, 39, 4, 3, 'amarillo')
    else:
        L.elipse(18, 40, 4, 3, 'amarillo')

    # orejas largas y finas (detrás de la cabeza), punta negra
    L.poligono([(22, 13 + dy), (21, 6 + dy), (22, 1 + dy), (25, 3 + dy), (27, 13 + dy)], 'amarillo')
    L.poligono([(32, 12 + dy), (34, 4 + dy), (37, 0 + dy), (39, 3 + dy), (38, 13 + dy)], 'amarillo')
    L.recolorear(lambda x, y: y <= 4 + dy and 20 <= x <= 27, 'punta')
    L.recolorear(lambda x, y: y <= 3 + dy and 33 <= x <= 40, 'punta')

    # cuerpo
    L.elipse(22, 30 + dy, 9, 8, 'amarillo')

    # cabeza
    L.elipse(29, 17 + dy, 9, 7, 'amarillo', borde=True)

    # bracito (sin aro: solo una sombra y un trazo debajo)
    L.elipse(27, 29 + dy, 2, 2, 'amarillo', sin_contorno=True)
    L.linea(25, 31 + dy, 28, 32 + dy, 'marron')

    # pata delantera (delante del cuerpo, pegada a él)
    if pose == 0:
        L.elipse(30, 40, 4, 3, 'amarillo', borde=True)
    else:
        L.elipse(27, 39, 4, 3, 'amarillo', borde=True)

    # cara: ojo con brillo, mejilla redonda y pequeña, nariz y sonrisa
    L.rect(32, 14 + dy, 33, 16 + dy, 'ojo')
    L.px(32, 14 + dy, 'brillo')
    L.elipse(34, 20 + dy, 1, 1, 'rojo', sin_sombra=True, sin_contorno=True)
    L.px(38, 16 + dy, 'nariz')
    L.linea(36, 21 + dy, 38, 20 + dy, 'boca')
    return L.render()

def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'pikachu.png')
    vista([h], escala=9, salida=out / 'pikachu_x9.png')
    print('ok', h.size)
