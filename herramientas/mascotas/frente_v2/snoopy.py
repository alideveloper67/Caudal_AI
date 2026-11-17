# -*- coding: utf-8 -*-
"""Snoopy, pixel art de pie y de 3/4. Silueta por filas (columna izquierda, derecha) para cada parte; contorno y
bandas de luz/sombra con la misma regla y retoque a mano de la cara, el collar y los dedos."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista

LEYENDA = {'K': '#101016', 'o': '#2c2c38', 'W': '#fbfcff', 'L': '#ffffff', 'S': '#b8c2d8', 'E': '#2a2a34',
           'e': '#5c5c70', 'B': '#101014', 'g': '#8a8a9c', 'R': '#d83030', 'r': '#f86858', 'D': '#8c1818',
           'N': '#d04c68', '.': None}
W, H = 34, 44
G = [['.'] * W for _ in range(H)]
def parte(spans, base, luz, sombra, ol='O', od='K', banda=2):
    m = {(x, y) for y, (a, b) in spans.items() for x in range(a, b + 1)}
    def borde(x, y):
        return any((x + dx, y + dy) not in m for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    for (x, y) in m:
        if borde(x, y):
            c = od if ((x + 1, y) not in m or (x, y + 1) not in m) else ol
        else:
            d = lambda dx, dy: next((k for k in range(1, 9) if (x + dx * k, y + dy * k) not in m), 9)
            if d(1, 0) <= banda + 1 or d(0, 1) <= banda:
                c = sombra
            elif min(d(-1, 0), d(0, -1)) <= 2:
                c = luz
            else:
                c = base
        G[y][x] = c
def put(f, c, t):
    for i, ch in enumerate(t):
        if ch != '.':
            G[f][c + i] = ch


def pr(a, b, ys):
    return {y: (a, b) for y in ys}

BL = dict(ol='K', od='K')
# patas y pies (pies hacia la derecha)
parte(pr(10, 14, range(33, 40)) | {40: (9, 16), 41: (8, 18), 42: (8, 19), 43: (9, 19)}, 'W', 'L', 'S', **BL)
parte(pr(19, 23, range(33, 40)) | {40: (18, 24), 41: (17, 26), 42: (17, 27), 43: (18, 27)}, 'W', 'L', 'S', **BL)
# cola/orejita derecha asomando
parte({3: (22, 26), 4: (23, 28), 5: (23, 28), 6: (23, 27)}, 'E', 'e', 'B', **BL, banda=1)
# cuerpo
cuerpo = {19: (10, 23), 20: (9, 24)}
for y in range(21, 31): cuerpo[y] = (8, 25)
cuerpo.update({31: (9, 24), 32: (10, 23), 33: (11, 22), 34: (12, 21)})
parte(cuerpo, 'W', 'L', 'S', **BL)
# cabeza
cab = {2: (12, 20), 3: (10, 22), 4: (9, 23), 5: (8, 24)}
for y in range(6, 16): cab[y] = (7, 25)
cab.update({16: (8, 24), 17: (9, 23), 18: (11, 21)})
parte(cab, 'W', 'L', 'S', **BL)
# hocico y nariz
parte({10: (21, 28), 11: (20, 29), 12: (20, 29), 13: (20, 29), 14: (21, 28), 15: (22, 27)}, 'W', 'L', 'S', **BL, banda=1)
parte({5: (28, 30), 6: (27, 31), 7: (26, 32), 8: (26, 32), 9: (26, 32), 10: (27, 31), 11: (28, 30)}, 'E', 'e', 'B', **BL, banda=1)
put(6, 28, 'g'); put(7, 28, 'e'); put(7, 29, 'g') if False else None
# collar
parte(pr(10, 23, range(19, 22)), 'R', 'r', 'D', ol='D', od='K', banda=1)
put(21, 17, 'o'); put(21, 18, 'o')
# oreja izquierda larga
oreja = {5: (5, 9), 6: (3, 10), 7: (2, 10), 8: (2, 10)}
for y in range(9, 15): oreja[y] = (1, 9)
oreja.update({15: (2, 9), 16: (2, 9), 17: (2, 8), 18: (3, 8), 19: (3, 8), 20: (4, 8), 21: (4, 7), 22: (5, 7)})
parte(oreja, 'E', 'e', 'B', **BL, banda=1)
# brazos
parte({y: (4, 8) for y in range(23, 31)} | {31: (4, 7)}, 'W', 'L', 'S', **BL, banda=1)
parte({22: (24, 28), 21: (25, 29), 20: (26, 30), 19: (27, 31), 18: (28, 32), 17: (28, 32)}, 'W', 'L', 'S', **BL, banda=1)
put(16, 29, 'K'); put(16, 31, 'K'); put(31, 5, 'K')
# cara
put(8, 13, 'BB'); put(9, 13, 'BB'); put(10, 13, 'BB'); put(8, 18, 'BB'); put(9, 18, 'BB'); put(10, 18, 'BB')
put(8, 13, 'L'); put(8, 18, 'L')
put(13, 21, 'K'); put(14, 22, 'KKKK'); put(13, 26, 'K')
put(15, 23, 'N'); put(15, 24, 'N')
FILAS = [''.join(r) for r in G]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    vd = Path(__file__).parent / 'vista'; vd.mkdir(exist_ok=True)
    vista([hojas()], escala=9, fondo=(255, 255, 255), salida=vd / 'snoopy_x9.png')
