# -*- coding: utf-8 -*-
"""Hello Kitty corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('blanco', '#fbfbfd', luz='#ffffff', sombra='#c6c8e2', contorno='#8c84aa')
    L.mat('rojo', '#e83a3e', sombra='#b8222e', contorno='#7a1420')
    L.mat('azul', '#3c6ed0', sombra='#2a48a0', contorno='#1c2c70')
    L.mat('amarillo', '#ffd21e', fijo=True)
    L.mat('ojo', '#16141e', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('bigote', '#4a4660', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0

    # colita
    L.elipse(12, 31 + dy + pose * -1, 3, 3, 'blanco')
    # pata trasera
    L.elipse(13 if pose == 0 else 18, 40, 4, 3, 'blanco')
    # cuerpo con peto azul
    L.elipse(21, 32 + dy, 7, 7, 'azul')
    L.rect(20, 25 + dy, 25, 26 + dy, 'blanco', sin_contorno=True, sin_sombra=True)
    # orejas (detras de la cabeza)
    L.poligono([(19, 14 + dy), (18, 3 + dy), (27, 9 + dy)], 'blanco')
    L.poligono([(33, 9 + dy), (40, 3 + dy), (40 - pose, 15 + dy)], 'blanco')
    # cabeza ancha
    L.elipse(29, 19 + dy, 11, 8, 'blanco', borde=True)
    # lazo rojo en la oreja
    bw = pose
    L.poligono([(31, 4 + dy - bw), (36, 8 + dy), (31, 12 + dy + bw)], 'rojo', borde=True)
    L.poligono([(44, 4 + dy - bw), (40, 8 + dy), (44, 12 + dy + bw)], 'rojo', borde=True)
    L.rect(35, 6 + dy, 39, 10 + dy, 'rojo', borde=True)
    L.px(37, 8 + dy, 'amarillo')
    # bracito
    a = 1 if pose == 0 else -1
    L.elipse(27 + a, 31 + dy, 2, 2, 'blanco', borde=True)
    # pata delantera
    L.elipse(29 if pose == 0 else 26, 40, 4, 3, 'blanco', borde=True)
    # cara
    L.rect(33, 17 + dy, 34, 20 + dy, 'ojo')
    L.px(33, 17 + dy, 'brillo')
    L.rect(39, 17 + dy, 40, 20 + dy, 'ojo')
    L.px(39, 17 + dy, 'brillo')
    L.rect(36, 21 + dy, 37, 22 + dy, 'amarillo')
    # bigotes
    L.linea(41, 19 + dy, 44, 18 + dy, 'bigote')
    L.linea(41, 22 + dy, 44, 23 + dy, 'bigote')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'hellokitty.png')
    vista([h], escala=9, salida=out / 'hellokitty_x9.png')
    print('ok', h.size)
