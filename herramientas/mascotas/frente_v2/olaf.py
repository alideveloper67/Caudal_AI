# -*- coding: utf-8 -*-
"""Olaf dibujado píxel a píxel como texto: tres bolas de nieve apiladas, de frente."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'B': '#7890a8', 'K': '#40506a',                          # contorno lado luz / lado sombra (gris-azulado)
    'W': '#ffffff', 'w': '#e8f0fa', 'v': '#bccae2', 'u': '#8ea2c8',   # nieve: luz, base, sombra, sombra honda
    't': '#9a6030', 'T': '#4a2810', 'q': '#b88050',          # ramitas y pies
    'O': '#f08020', 'o': '#c05810', 'L': '#ffb858',          # zanahoria
    'E': '#101820', 'M': '#3a1420', 'P': '#e06878',          # ojos, boca, lengua
    'c': '#243040', 'g': '#7a8aa8',                          # botones de carbón y su brillo
    '.': None,
}
W = 34


def R(s):
    out = ''
    for t in s.split():
        m = re.fullmatch(r'(\d+)(\D)', t)
        out += m.group(2) * int(m.group(1)) if m else t
    return out


def F(a, b, mid):
    return '.' * a + 'B' + R(mid) + 'K' + '.' * (W - b - 1)


ROWS = [
    "12. t 4. t 3. t 12.",
    "12. t 4. T 3. t 12.",
    "14. T 2. T 2. T 13.",
    F(12, 21, "2W 5w v"),
    F(10, 23, "3W 7w 2v"),
    F(8, 25, "4W 10w 2v"),
    F(7, 26, "4W 11w 3v"),
    F(6, 27, "3W 13w 4v"),
    F(6, 27, "3W 13w 4v"),
    F(6, 27, "2W 14w 3v u"),
    F(6, 27, "2W 14w 3v u"),
    F(6, 27, "2W 14w 3v u"),
    F(6, 27, "2W 13w 4v u"),
    F(6, 27, "2W 13w 4v u"),
    F(7, 26, "4w 10M 2w 2v"),
    F(8, 25, "4w 2M 4W 2M 3w v"),
    F(10, 23, "3w M 4P M 2w v"),
    "11. 6B 6K 11.",
    F(9, 24, "14v"),
    F(8, 25, "3W 10w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(7, 26, "2W 13w 2v u"),
    F(8, 25, "2W 11w 2v u"),
    F(9, 24, "14v"),
    "8. 9B 9K 8.",
    F(6, 27, "2W 15w 2v u"),
    F(5, 28, "3W 15w 3v u"),
    F(4, 29, "3W 16w 4v u"),
    F(4, 29, "3W 16w 4v u"),
    F(4, 29, "2W 17w 4v u"),
    F(4, 29, "2W 17w 4v u"),
    F(4, 29, "2W 15w 5v 2u"),
    F(4, 29, "2W 15w 5v 2u"),
    F(5, 28, "2W 13w 5v 2u"),
    F(6, 27, "2W 11w 5v 2u"),
    "8. 9B 9K 8.",
    "8. 6T 4. 6T 10.",
    "6. T q 7t T 2. T q 7t T 6.",
    "6. 10T 2. 10T 6.",
]

# detalles puestos pixel a pixel (x, y, carácter): cejas, ojos, zanahoria, brazos de ramitas, botones
PUT = []


def poner(x, y, c):
    PUT.append((x, y, c))


for (x, y) in [(10, 7), (11, 6), (12, 6), (13, 7), (16, 7), (17, 6), (18, 6), (19, 7)]:
    poner(x, y, 't')
for ox in (11, 17):                                           # ojos: puntos negros grandes con brillo
    poner(ox, 8, 'W'); poner(ox + 1, 8, 'E')
    for y in (9, 10):
        poner(ox, y, 'E'); poner(ox + 1, y, 'E')
for i, c in enumerate('LOOo'):                                # nariz de zanahoria apuntando a la derecha
    poner(14 + i, 11, c)
for i, c in enumerate('LOOOOoo'):
    poner(14 + i, 12, c)
for i, c in enumerate('ooooo'):
    poner(17 + i, 13, c)
# brazo izquierdo (alzado) y derecho (saludando)
for (x, y, c) in [(6, 22, 'T'), (5, 21, 't'), (4, 20, 't'), (3, 19, 't'), (2, 18, 'T'), (1, 17, 't'), (3, 17, 't'), (2, 16, 'T'),
                  (27, 22, 'T'), (28, 21, 't'), (29, 20, 't'), (30, 19, 't'), (31, 18, 'T'), (32, 17, 't'), (30, 17, 't'), (31, 16, 'T')]:
    poner(x, y, c)
for y0 in (20, 23, 26):                                       # tres botones de carbón
    poner(16, y0, 'g'); poner(17, y0, 'c'); poner(16, y0 + 1, 'c'); poner(17, y0 + 1, 'c')

FILAS = []
for n, f in enumerate(ROWS):
    r = R(f)
    if len(r) != W:
        print('fila', n, 'mide', len(r), f)
    FILAS.append(r)
for x, y, c in PUT:
    f = FILAS[y]
    FILAS[y] = f[:x] + c + f[x + 1:]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'olaf.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'olaf_x9.png')
    print('ok', h.size, len(FILAS))
