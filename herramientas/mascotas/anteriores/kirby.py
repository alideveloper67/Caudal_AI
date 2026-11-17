# -*- coding: utf-8 -*-
"""Kirby corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('rosa', '#f8a8c8', sombra='#e07aa8', contorno='#a04068')
    L.mat('pie', '#e43a3a', sombra='#b02438', contorno='#701828')
    L.mat('mejilla', '#f0608c', fijo=True)
    L.mat('ojo', '#16183c', fijo=True)
    L.mat('ojo2', '#3a5ad8', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('boca', '#a02040', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0

    # pie trasero (detras)
    if pose == 0:
        L.elipse(12, 41, 6, 2, 'pie')
    else:
        L.elipse(17, 41, 6, 2, 'pie')
    # brazo trasero (levantado hacia atras)
    if pose == 0:
        L.elipse(7, 22 + dy, 3, 4, 'rosa')
    else:
        L.elipse(7, 19 + dy, 3, 4, 'rosa')
    # cuerpo
    L.elipse(23, 24 + dy, 15, 15, 'rosa')
    # brazo delantero
    if pose == 0:
        L.elipse(36, 30 + dy, 4, 3, 'rosa', borde=True)
    else:
        L.elipse(37, 30 + dy, 4, 3, 'rosa', borde=True)
    # pie delantero
    if pose == 0:
        L.elipse(32, 41, 6, 2, 'pie', borde=True)
    else:
        L.elipse(28, 41, 6, 2, 'pie', borde=True)

    # cara: ojos ovalados (tres cuartos), mejilla y boca
    for ex in (29, 35):
        L.rect(ex, 14 + dy, ex + 1, 20 + dy, 'ojo')
        L.rect(ex, 19 + dy, ex + 1, 20 + dy, 'ojo2')
        L.px(ex, 14 + dy, 'brillo')
        L.px(ex, 15 + dy, 'brillo')
    L.elipse(26, 24 + dy, 2, 1, 'mejilla', sin_sombra=True, sin_contorno=True)
    L.linea(32, 24 + dy, 34, 24 + dy, 'boca')
    L.px(33, 25 + dy, 'boca')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'kirby.png')
    vista([h], escala=9, salida=out / 'kirby_x9.png')
    print('ok', h.size)
