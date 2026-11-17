# -*- coding: utf-8 -*-
"""Chimuelo (Toothless) corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista, hex_rgb  # noqa: E402


def materiales(L):
    L.mat('negro', '#2e3248', sombra='#1c1e30', contorno='#5a68b4')
    L.m['negro'].contorno_oscuro = hex_rgb('#3a4272')
    L.mat('lejos', '#222538', sombra='#161828', contorno='#4a5598')
    L.m['lejos'].contorno_oscuro = hex_rgb('#30386a')
    L.mat('ala', '#40306a', sombra='#281e48', contorno='#8470c8')
    L.m['ala'].contorno_oscuro = hex_rgb('#3a2c68')
    L.mat('rojo', '#e04030', sombra='#a82428', contorno='#ff8a70')
    L.m['rojo'].contorno_oscuro = hex_rgb('#701820')
    L.mat('luz', '#6a78b8', fijo=True)
    L.mat('verde', '#8af04c', fijo=True)
    L.mat('pupila', '#0a0c18', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('nariz', '#12142a', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    e = 1 if pose == 1 else 0

    # cola con aleta roja
    L.poligono([(15, 27 + dy), (10, 30 + dy), (7, 33 + dy + e), (8, 37 + dy + e), (11, 36 + dy + e), (12, 34 + dy),
                (16, 33 + dy)], 'negro')
    L.poligono([(9, 35 + dy + e), (3, 30 + dy + e), (2, 34 + dy + e), (3, 39 + dy + e), (9, 38 + dy + e)], 'rojo')
    # ala plegada atras
    L.poligono([(23, 23 + dy), (13, 14 + dy - e), (10, 8 + dy - e), (15, 9 + dy - e), (18, 13 + dy), (21, 10 + dy - e), (27, 16 + dy), (30, 22 + dy)], 'ala')
    # patas lejanas
    if pose == 0:
        L.elipse(19, 40, 2, 3, 'lejos')
        L.elipse(26, 40, 2, 3, 'lejos')
    else:
        L.elipse(23, 40, 2, 3, 'lejos')
        L.elipse(25, 40, 2, 3, 'lejos')
    # cuerpo
    L.elipse(22, 29 + dy, 10, 6, 'negro')
    # pata trasera cercana
    if pose == 0:
        L.elipse(12, 39, 3, 4, 'negro')
    else:
        L.elipse(18, 39, 3, 4, 'negro')
    # cuello y cabeza
    L.elipse(30, 24 + dy, 4, 5, 'negro')
    # orejas-aleta
    L.poligono([(30, 18 + dy), (26, 10 + dy + e), (24, 7 + dy + e), (33, 16 + dy)], 'negro')
    L.poligono([(34, 16 + dy), (33, 9 + dy + e), (33, 6 + dy + e), (38, 15 + dy)], 'negro')
    L.elipse(36, 21 + dy, 7, 5, 'negro', borde=True)
    # pata delantera cercana
    if pose == 0:
        L.elipse(33, 39, 2, 4, 'negro')
    else:
        L.elipse(29, 39, 2, 4, 'negro')
    # luces del lomo y cabeza
    L.linea(14, 25 + dy, 22, 23 + dy, 'luz')
    L.linea(33, 17 + dy, 38, 16 + dy, 'luz')
    # ojo verde grande y nariz
    L.rect(35, 18 + dy, 38, 21 + dy, 'verde')
    L.rect(37, 18 + dy, 37, 21 + dy, 'pupila')
    L.px(35, 18 + dy, 'brillo')
    L.px(42, 20 + dy, 'nariz')
    L.linea(37, 24 + dy, 41, 24 + dy, 'luz')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'toothless.png')
    vista([h], escala=9, salida=out / 'toothless_x9.png')
    print('ok', h.size)
