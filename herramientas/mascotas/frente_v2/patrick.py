# -*- coding: utf-8 -*-
"""Patricio Estrella, pixel art de pie y de frente. La silueta de cada parte se da fila a fila (columna izquierda,
columna derecha); contorno y bandas de luz/sombra se reparten con la misma regla en todas las partes y después
se retocan a mano píxel a píxel (cara, flores, dedos)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista

LEYENDA = {'K': '#2a1020', 'O': '#a84862', 'P': '#f090a8', 'L': '#ffc4d4', 'S': '#cc6884', 'W': '#ffffff',
           'B': '#201018', 'm': '#7a1c34', 'R': '#e8607c', 'G': '#58b848', 'g': '#388030', 'l': '#8ad870',
           'k': '#1e4818', 'V': '#8a58c8', 'v': '#c4a0f0', 'Q': '#5a2c9a', '.': None}
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


# piernas
parte({y: (10, 15) for y in range(36, 42)} | {42: (8, 15), 43: (7, 15)}, 'P', 'L', 'S')
parte({y: (18, 23) for y in range(36, 42)} | {42: (18, 26), 43: (18, 27)}, 'P', 'L', 'S')
# cabeza y cuerpo
cab = {0: (15, 17), 1: (14, 18), 2: (13, 19), 3: (13, 19), 4: (12, 20), 5: (12, 20), 6: (11, 21), 7: (11, 21),
       8: (10, 22), 9: (10, 22), 10: (9, 23), 11: (9, 23), 12: (8, 24), 13: (8, 24), 14: (8, 24), 15: (8, 24),
       16: (8, 24), 17: (8, 24), 18: (8, 24), 19: (8, 25), 20: (7, 25), 21: (7, 25), 22: (7, 26), 23: (7, 26),
       24: (7, 26), 25: (7, 26), 26: (7, 26), 27: (7, 26), 28: (8, 25), 29: (8, 25)}
parte(cab, 'P', 'L', 'S')
# pantalón
sh = {29: (7, 26), 30: (7, 26), 31: (7, 26), 32: (7, 26), 33: (7, 26), 34: (8, 25), 35: (9, 24), 36: (10, 23)}
parte(sh, 'G', 'l', 'g', ol='k', od='k')
for x, y in ((11, 31), (18, 33), (22, 31), (14, 34)):
    put(y - 1, x + 1, 'V'); put(y, x, 'VvV'); put(y + 1, x + 1, 'Q')
# brazo izquierdo (cae hacia fuera) y derecho (levantado)
bi = {19: (4, 9), 20: (3, 8), 21: (2, 7), 22: (2, 6), 23: (1, 5), 24: (1, 5), 25: (0, 5), 26: (0, 5), 27: (0, 4), 28: (1, 4)}
parte(bi, 'P', 'L', 'S')
bd = {21: (24, 28), 20: (25, 29), 19: (26, 30), 18: (27, 31), 17: (28, 32), 16: (29, 33), 15: (29, 33), 14: (29, 33),
      13: (29, 33), 12: (30, 33)}
parte(bd, 'P', 'L', 'S')
put(13, 31, 'K'); put(14, 30, 'K'); put(15, 31, 'K')   # insinuar dedos
put(26, 2, 'K'); put(27, 2, 'K'); put(28, 2, 'K')
# cara
for cx in (11, 17):
    for i, t in enumerate((".KKK.", "KWWWK", "KWWBK", "KWWBK", ".KKK.")):
        put(11 + i, cx, t)
put(9, 11, 'KKKK'); put(9, 18, 'KKKK')
put(17, 11, 'KKKKKKKKKKK'); put(18, 11, 'KmmmmmmmmmK'); put(19, 12, 'KmmRRRmmK'); put(20, 13, 'KKKKKKK')
put(18, 10, 'R'); put(18, 22, 'R') if False else None
FILAS = [''.join(r) for r in G]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    vd = Path(__file__).parent / 'vista'; vd.mkdir(exist_ok=True)
    vista([hojas()], escala=9, fondo=(255, 255, 255), salida=vd / 'patrick_x9.png')
