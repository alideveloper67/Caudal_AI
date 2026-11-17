# -*- coding: utf-8 -*-
"""Winnie the Pooh corriendo hacia la derecha (2 cuadros de 48x44)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pix import Lienzo, hoja, vista  # noqa: E402


def materiales(L):
    L.mat('miel', '#eca02a', sombra='#cc6a22', contorno='#7a3a10')
    L.mat('hocico', '#f6cc78', sombra='#dc9c4e', contorno='#7a3a10')
    L.mat('rojo', '#e03a2e', sombra='#b0222c', contorno='#6c1018')
    L.mat('ojo', '#14141c', fijo=True)
    L.mat('nariz', '#2a1a14', fijo=True)
    L.mat('boca', '#6a2418', fijo=True)
    L.mat('brillo', '#ffffff', fijo=True)


def cuadro(pose):
    L = Lienzo()
    materiales(L)
    dy = -1 if pose == 1 else 0
    B = 'b'

    def P(lista, m):
        for (x, y) in lista:
            L.rect(x, y + dy, x, y + dy, m, grupo=B)

    # cola (detras)
    L.elipse(11, 31 + dy, 2, 2, 'miel')
    # brazo trasero
    if pose == 0:
        L.elipse(11, 27 + dy, 3, 3, 'miel')
    else:
        L.elipse(11, 24 + dy, 3, 3, 'miel')

    # patas
    if pose == 0:
        L.elipse(15, 40, 4, 3, 'miel')
        L.elipse(30, 40, 5, 3, 'miel', borde=True)
    else:
        L.elipse(20, 40, 4, 3, 'miel')
        L.elipse(27, 40, 5, 3, 'miel', borde=True)

    # orejas redondas (detras de la cabeza)
    L.elipse(23, 6 + dy, 3, 3, 'miel')
    L.elipse(34, 6 + dy, 3, 3, 'miel')

    # cuerpo de oso (barrigon) y camiseta roja
    L.elipse(22, 30 + dy, 9, 9, 'miel', grupo=B)
    EB = lambda x, y: L.celda[y][x][0] == B
    L.recolorear(lambda x, y: y <= 30 + dy and y >= 22 + dy and EB(x, y), 'rojo')
    # borde inferior de la camiseta
    P([(x, 31) for x in range(14, 30)], 'rojo')

    # cabeza
    L.elipse(29, 14 + dy, 9, 8, 'miel', borde=True)
    # hocico claro
    L.elipse(35, 17 + dy, 4, 3, 'hocico', sin_sombra=True)
    L.rect(37, 14 + dy, 38, 15 + dy, 'nariz')
    # ojo y sonrisa
    L.rect(32, 11 + dy, 32, 13 + dy, 'ojo')
    L.rect(33, 11 + dy, 33, 11 + dy, 'brillo')
    L.rect(34, 19 + dy, 36, 19 + dy, 'boca')
    L.rect(37, 18 + dy, 37, 18 + dy, 'boca')
    L.rect(33, 11 + dy, 33, 11 + dy, 'brillo')

    # brazo delantero
    if pose == 0:
        L.poligono([(27, 24 + dy), (31, 27 + dy), (34, 29 + dy), (34, 32 + dy), (30, 32 + dy), (26, 28 + dy)],
                   'miel', borde=True)
    else:
        L.poligono([(27, 24 + dy), (32, 23 + dy), (35, 22 + dy), (36, 25 + dy), (32, 27 + dy), (26, 28 + dy)],
                   'miel', borde=True)
    return L.render()


def hojas():
    return hoja([cuadro(0), cuadro(1)])


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'pooh.png')
    vista([h], escala=9, salida=out / 'pooh_x9.png')
    print('ok', h.size)
