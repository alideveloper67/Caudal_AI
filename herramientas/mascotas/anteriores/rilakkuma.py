# -*- coding: utf-8 -*-
"""Rilakkuma corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('marron', '#b0702e', sombra='#82481c', contorno='#4a2408')
    L.mat('crema', '#f8e0b0', sombra='#dcb078', contorno='#8a5a28')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)
    L.mat('nariz', '#2a1a10', fijo=True)
    L.mat('cierre', '#a8742c', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    # colita
    L.elipse(13, 33 + dy, 2, 2, 'crema')
    # pie trasero
    L.elipse(14 if pose == 0 else 19, 40, 4, 3, 'marron')
    # cuerpo + barriga con cierre
    L.elipse(23, 30 + dy, 10, 9, 'marron')
    L.elipse(26, 32 + dy, 6, 6, 'crema', borde=True)
    L.linea(26, 28 + dy, 26, 36 + dy, 'cierre')
    # bracito
    L.elipse(18, 28 + dy, 2, 3, 'marron', sin_contorno=True)
    # orejas
    L.elipse(20, 6 + dy, 3, 3, 'marron')
    L.elipse(33, 6 + dy, 3, 3, 'marron')
    # cabeza
    L.elipse(27, 15 + dy, 10, 8, 'marron', borde=True)
    # hocico
    L.elipse(33, 18 + dy, 5, 4, 'crema', borde=True)
    # pie delantero
    L.elipse(30 if pose == 0 else 27, 40, 5, 3, 'marron', borde=True)
    # ojitos y nariz
    L.rect(27, 13 + dy, 28, 14 + dy, 'ojo')
    L.px(27, 13 + dy, 'brillo')
    L.rect(34, 12 + dy, 35, 13 + dy, 'ojo')
    L.px(34, 12 + dy, 'brillo')
    L.rect(35, 17 + dy, 37, 18 + dy, 'nariz', sin_contorno=True)
    L.px(36, 20 + dy, 'nariz')
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'rilakkuma.png')
    vista([h], escala=9, salida=out / 'rilakkuma_x9.png')
    print('ok', h.size)
