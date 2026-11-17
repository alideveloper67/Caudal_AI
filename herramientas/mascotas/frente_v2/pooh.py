# -*- coding: utf-8 -*-
"""Winnie the Pooh, pixel art de pie y de frente saludando. Silueta por filas (columna izquierda, derecha) para cada
parte; contorno y bandas de luz/sombra con la misma regla y retoque a mano de cara, dedos y camiseta."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista

LEYENDA = {'K': '#3c1c08', 'O': '#8a4a14', 'P': '#e89c2c', 'L': '#fbc860', 'S': '#b8681c', 'T': '#f6d494',
           't': '#d4a45c', 'R': '#d83a32', 'r': '#f06c5a', 'D': '#9c2020', 'Q': '#6c1010', 'B': '#140c08',
           'W': '#ffffff', 'N': '#c4783c', '.': None}
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

# piernas y pies
parte(pr(9, 15, range(34, 41)) | {41: (8, 16), 42: (7, 16), 43: (7, 16)}, 'P', 'L', 'S', ol='O')
parte(pr(19, 25, range(34, 41)) | {41: (18, 26), 42: (18, 27), 43: (18, 27)}, 'P', 'L', 'S', ol='O')
# cuerpo (barriga redonda)
cuerpo = {17: (11, 23), 18: (9, 25), 19: (8, 26), 20: (7, 27)}
for y in range(21, 30): cuerpo[y] = (6, 28)
cuerpo.update({30: (7, 27), 31: (7, 27), 32: (8, 26), 33: (9, 25), 34: (10, 24), 35: (12, 22)})
parte(cuerpo, 'P', 'L', 'S', ol='O')
# camiseta roja corta
cam = {19: (9, 25), 20: (7, 27)}
for y in range(21, 27): cam[y] = (6, 28)
parte(cam, 'R', 'r', 'D', ol='D', od='Q', banda=2)
# orejas
parte({0: (8, 11), 1: (6, 12), 2: (5, 13), 3: (5, 13), 4: (5, 13), 5: (6, 13), 6: (8, 12)}, 'P', 'L', 'S', ol='O')
parte({0: (23, 26), 1: (21, 27), 2: (20, 28), 3: (20, 28), 4: (20, 28), 5: (20, 27), 6: (21, 26)}, 'P', 'L', 'S', ol='O')
put(2, 8, 'NN'); put(3, 7, 'NNN'); put(4, 8, 'NN'); put(2, 23, 'NN'); put(3, 23, 'NNN'); put(4, 23, 'NN')
# cabeza
cab = {3: (14, 20), 4: (12, 22), 5: (10, 24), 6: (9, 25), 7: (8, 26)}
for y in range(8, 14): cab[y] = (7, 27)
cab.update({14: (8, 26), 15: (9, 25), 16: (10, 24), 17: (12, 22), 18: (14, 20)})
parte(cab, 'P', 'L', 'S', ol='O')
# hocico claro
hoc = {10: (14, 20), 11: (12, 22), 12: (11, 23), 13: (11, 23), 14: (11, 23), 15: (12, 22), 16: (14, 20)}
parte(hoc, 'T', 'T', 't', ol='O', od='O', banda=1)
# brazo izquierdo (colgando) y derecho (saluda)
parte({y: (2, 7) for y in range(21, 29)} | {29: (1, 7), 30: (1, 6), 31: (2, 6)}, 'P', 'L', 'S', ol='O')
parte({21: (26, 30), 20: (27, 31), 19: (28, 32), 18: (28, 32), 17: (28, 32), 16: (28, 32), 15: (28, 32), 14: (28, 32),
       13: (29, 33), 12: (29, 33), 11: (29, 33)}, 'P', 'L', 'S', ol='O')
put(11, 31, 'K'); put(12, 31, 'K'); put(12, 32, 'K'); put(30, 3, 'K'); put(31, 3, 'K')
# cara
put(8, 10, 'BB'); put(9, 10, 'BB'); put(8, 23, 'BB'); put(9, 23, 'BB'); put(8, 10, 'W'); put(8, 23, 'W')
put(10, 15, 'BBBB'); put(11, 14, 'BBBBBB'); put(12, 15, 'BBBB'); put(11, 15, 'W') if False else None
put(14, 16, 'B'); put(14, 18, 'B'); put(15, 17, 'B'); put(13, 17, 'B')
FILAS = [''.join(r) for r in G]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    vd = Path(__file__).parent / 'vista'; vd.mkdir(exist_ok=True)
    vista([hojas()], escala=9, fondo=(255, 255, 255), salida=vd / 'pooh_x9.png')
