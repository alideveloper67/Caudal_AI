# -*- coding: utf-8 -*-
"""Rilakkuma dibujado píxel a píxel como texto: osito marrón con hocico y barriga crema, de frente."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'B': '#6a3c18', 'K': '#2a1409',                          # contorno lado luz / lado sombra
    'Y': '#b07840', 'l': '#cc9458', 's': '#8c5c2c', 'd': '#6c4020',   # marrón: base, luz, sombra, sombra honda
    'C': '#f4dcae', 'c': '#fff2d4', 'z': '#d4b078', 'x': '#b08c58',   # crema: base, luz, sombra, costura
    'i': '#e4ac7c',                                          # interior de la oreja
    'E': '#181008', 'W': '#ffffff', 'g': '#7a6858',          # ojos, brillo, brillo de la nariz
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
    "7. BlK 14. BlK 7.",
    "6. BlYYK 12. BlYYK 6.",
    "5. BliiYsK 10. BliiYsK 5.",
    "5. BliiYsK 5B 5K BliiYsK 5.",
    F(7, 26, "4l 12Y 2s"),
    F(6, 27, "4l 14Y 2s"),
    F(5, 28, "3l 16Y 3s"),
    F(4, 29, "3l 17Y 4s"),
    F(4, 29, "2l 18Y 4s"),
    F(4, 29, "2l 18Y 4s"),
    F(4, 29, "l 19Y 4s"),
    F(4, 29, "l 19Y 4s"),
    F(4, 29, "l 7Y 2c 5C z 5Y 3s"),
    F(4, 29, "l 6Y 2c 7C z 4Y 3s"),
    F(4, 29, "l 5Y 2c 9C z 3Y 3s"),
    F(4, 29, "l 5Y 2c 9C z 3Y 3s"),
    F(5, 28, "l 5Y 9C z 3Y 3s"),
    F(6, 27, "l 5Y 7C z 3Y 3s"),
    F(8, 25, "l 11Y 4s"),
    "9. 8B 8K 9.",
    F(7, 26, "l 13Y 4s"),
    F(6, 27, "2l 15Y 3s"),
    F(3, 30, "BB B 2l 3Y 2c 7C z 3Y 2s K KK"),
    F(2, 31, "lYY B l 2Y 2c 11C z 2Y s K Yss"),
    F(2, 31, "lYY B l 2Y 2c 11C z 2Y s K Yss"),
    F(2, 31, "lYY B l 2Y 2c 11C z 2Y s K Yss"),
    F(2, 31, "lYs B l 2Y 2c 11C z 2Y s K Yss"),
    F(2, 31, "lYs B l 2Y 2c 11C z 2Y s K sss"),
    "2. 5B l 2Y 2c 11C z 2Y s 5K 2.",
    F(6, 27, "l 2Y 2c 11C z 2Y s"),
    F(6, 27, "l 2Y 2c 11C z 2Y s"),
    F(6, 27, "2l 2Y 2c 9C z 2Y 2s"),
    F(6, 27, "l 4Y 2c 7C z 3Y 2s"),
    F(7, 26, "l 3Y 10C 2Y 2s"),
    F(7, 26, "l 13Y 4s"),
    F(7, 26, "l 12Y 5s"),
    F(8, 25, "l 10Y 5s"),
    "8. 9B 9K 8.",
    "7. B lYYYYYs K 2. B lYYYYYs K 7.",
    "5. B lYYYYYYYs K 2. B lYYYYYYYs K 5.",
    "5. B lY 5C Ys K 2. B lY 5C Ys K 5.",
    "5. B lY 5z Ys K 2. B lY 5z Ys K 5.",
    "5. B lYYYYYYYs K 2. B lYYYYYYYs K 5.",
    "5. 11K 2. 11K 5.",
]
# la fila del arco inferior del hocico y los detalles pixel a pixel
PUT = []
for ox in (9, 23):                                            # ojitos pequeños y separados, con brillo
    PUT += [(ox, 10, 'W'), (ox + 1, 10, 'E'), (ox, 11, 'E'), (ox + 1, 11, 'E')]
PUT += [(16, 13, 'E'), (17, 13, 'E'), (15, 14, 'g'), (16, 14, 'E'), (17, 14, 'E'), (18, 14, 'E')]   # nariz
PUT += [(16, 15, 'E'), (17, 15, 'E'), (14, 16, 'E'), (15, 16, 'E'), (18, 16, 'E'), (19, 16, 'E')]   # boquita
for y in range(23, 33):                                       # línea vertical (cierre) de la barriga
    PUT.append((16, y, 'x'))

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
    h.save(out / 'rilakkuma.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'rilakkuma_x9.png')
    print('ok', h.size, len(FILAS))
