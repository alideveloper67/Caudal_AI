# -*- coding: utf-8 -*-
"""Minion, pixel art de pie y de frente (una pastilla amarilla con gafas, overol y guantes). La silueta de cada parte
se da fila a fila; contorno y bandas de luz/sombra siguen la misma regla en todas las partes y luego se retoca a mano."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista

LEYENDA = {'K': '#1c1608', 'O': '#a87c10', 'Y': '#f8d838', 'L': '#fff488', 'S': '#d4a418',
           'U': '#3860b8', 'u': '#6c90e0', 'D': '#24408a', 'k': '#101a3c', 'W': '#ffffff', 'w': '#c8ccd8',
           'A': '#8c9098', 'a': '#c4c8d0', 'T': '#5c6068', 'N': '#7a4a22', 'B': '#101010', 'M': '#6a1c1c',
           'G': '#3c3c44', 'g': '#6a6a74', 'R': '#d84a4a', '.': None}
W, H = 32, 44
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

# piernas y zapatos
parte(pr(10, 13, range(37, 41)), 'U', 'u', 'D', ol='k', od='k')
parte(pr(18, 21, range(37, 41)), 'U', 'u', 'D', ol='k', od='k')
parte({41: (8, 14), 42: (7, 14), 43: (7, 14)}, 'G', 'g', 'B', ol='B', od='B')
parte({41: (17, 23), 42: (17, 24), 43: (17, 25)}, 'G', 'g', 'B', ol='B', od='B')
# brazos (detrás del cuerpo)
parte({y: (2, 6) for y in range(22, 30)}, 'Y', 'L', 'S', ol='O')
parte({y: (25, 29) for y in range(14, 22)}, 'Y', 'L', 'S', ol='O')
# cuerpo amarillo (pastilla)
cuerpo = {2: (12, 19), 3: (10, 21), 4: (9, 22), 5: (8, 23), 6: (7, 24), 7: (7, 24)}
for y in range(8, 34): cuerpo[y] = (6, 25)
cuerpo.update({34: (7, 24), 35: (8, 23), 36: (10, 21), 37: (11, 20)})
parte(cuerpo, 'Y', 'L', 'S', ol='O')
# banda de las gafas
parte(pr(6, 25, range(9, 14)), 'A', 'a', 'T', ol='T', od='K')
# aro y ojo
aro = {6: (12, 19), 7: (10, 21), 8: (9, 22), 9: (8, 23), 10: (8, 23), 11: (8, 23), 12: (8, 23), 13: (8, 23), 14: (8, 23),
       15: (9, 22), 16: (10, 21), 17: (12, 19)}
parte(aro, 'A', 'a', 'T', ol='K', od='K', banda=1)
ojo = {8: (12, 19), 9: (10, 21), 10: (10, 21), 11: (10, 21), 12: (10, 21), 13: (10, 21), 14: (10, 21), 15: (12, 19)}
parte(ojo, 'W', 'W', 'w', ol='K', od='K', banda=1)
put(10, 13, 'NNNNNN'); put(11, 12, 'NNNNNNNN'); put(12, 12, 'NNNBBNNN'); put(13, 12, 'NNNBBNNN'); put(14, 13, 'NNNNNN')
put(11, 14, 'NNBBNN'[0:0] + 'N'); put(11, 15, 'BB'); put(12, 14, 'W')
put(12, 13, 'N'); put(12, 15, 'BB'); put(13, 15, 'BB'); put(12, 14, 'W')
# mejilla/boca
put(19, 11, 'K'); put(19, 20, 'K'); put(20, 12, 'KKKKKKKK'); put(21, 13, 'KWWWWK'); put(22, 14, 'KMMK'); put(23, 15, 'KK')
# overol
ov = {24: (6, 25)}
for y in range(25, 34): ov[y] = (6, 25)
ov.update({34: (7, 24), 35: (8, 23), 36: (10, 21), 37: (11, 20)})
parte(ov, 'U', 'u', 'D', ol='k', od='k')
parte({y: (10, 21) for y in range(22, 30)}, 'U', 'u', 'D', ol='k', od='k', banda=1)
parte(pr(6, 8, range(18, 24)), 'U', 'u', 'D', ol='k', od='k', banda=1)
parte(pr(23, 25, range(18, 24)), 'U', 'u', 'D', ol='k', od='k', banda=1)
put(26, 12, 'DDDDDD'); put(27, 12, 'DuuuuD'); put(28, 12, 'DuuuuD'); put(29, 12, 'DDDDDD')
put(24, 7, 'W'); put(24, 24, 'W')
# guantes
parte({y: (1, 6) for y in range(29, 33)}, 'G', 'g', 'B', ol='B', od='B', banda=1)
parte({y: (25, 30) for y in range(11, 15)}, 'G', 'g', 'B', ol='B', od='B', banda=1)
# pelos
put(0, 14, 'K'); put(1, 14, 'K'); put(0, 17, 'K'); put(1, 17, 'K'); put(1, 11, 'K'); put(2, 11, 'K'); put(1, 12, 'K')
FILAS = [''.join(r) for r in G]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    vd = Path(__file__).parent / 'vista'; vd.mkdir(exist_ok=True)
    vista([hojas()], escala=9, fondo=(255, 255, 255), salida=vd / 'minion_x9.png')
