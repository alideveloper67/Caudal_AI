# -*- coding: utf-8 -*-
"""Pompompurin dibujado píxel a píxel como texto: perrito crema con boina y orejas largas caídas, de frente."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'B': '#b08828', 'K': '#4a3010',                          # contorno lado luz / lado sombra
    'Y': '#f8e0a0', 'l': '#fff4cc', 's': '#e0b868', 'd': '#c09040',   # crema: base, luz, sombra, sombra honda
    'N': '#a06a38', 'm': '#c88c50', 'n': '#7a4820', 'D': '#3e2410',   # marrón: boina y orejas
    'E': '#2a1408', 'e': '#7a4a28', 'W': '#ffffff',          # ojos, nariz, brillo
    '.': None,
}
W = 36


def R(s):
    out = ''
    for t in s.split():
        m = re.fullmatch(r'(\d+)(\D)', t)
        out += m.group(2) * int(m.group(1)) if m else t
    return out


def F(a, b, mid):
    return '.' * a + 'B' + R(mid) + 'K' + '.' * (W - b - 1)


def con_orejas(izq, a, b, mid):
    """Cabeza (a..b) con una oreja larga a cada lado; la derecha es la izquierda en espejo con la luz cambiada."""
    der = izq[::-1].translate(str.maketrans('mn', 'nm'))
    return '.' + izq + F(a, b, mid)[7:29] + der + '.'


OREJA = [".DmNnD"] + ["DmNNnD"] * 9 + ["DmNnD.", "DmNnD.", ".DNnD.", ".DNnD.", ".DDDD."]
CABEZA = ["4l 14Y 2s", "3l 15Y 2s", "2l 16Y 2s", "2l 16Y 2s", "2l 16Y 2s", "2l 16Y 2s", "2l 16Y 2s",
          "l 17Y 2s", "l 16Y 3s", "l 16Y 3s", "l 15Y 4s", "l 14Y 5s"]

ROWS = [
    "16. DNND 16.",
    "12. DDmmNNNNNNDD 12.",
    "9. D 3m 11N 2n D 9.",
    "7. D 4m 14N 2n D 7.",
    "6. D 3m 16N 3n D 6.",
    "7. D 20n D 7.",
    F(8, 27, "4l 12Y 2s"),
]
for i, mid in enumerate(CABEZA):
    ROWS.append(con_orejas(OREJA[i], 7, 28, mid))
ROWS += [
    con_orejas(OREJA[12], 7, 28, "l 13Y 6s"),
    con_orejas(OREJA[13], 8, 27, "l 11Y 6s"),
    con_orejas(OREJA[14], 9, 26, "10Y 6s"),
    "10. 8B 8K 10.",
    F(9, 26, "16s"),
    F(8, 27, "2l 11Y 5s"),
    F(5, 30, "lYY B 2l 13Y s K Yss"),
    F(5, 30, "lYY B l 14Y s K Yss"),
    F(5, 30, "YYs B l 14Y s K Yss"),
    F(5, 30, "YYs B 15Y s K Yss"),
    "6. 4B l 14Y s 4K 6.",
    F(7, 28, "2l 14Y 4s"),
    F(7, 28, "l 16Y 3s"),
    F(7, 28, "l 16Y 3s"),
    F(7, 28, "l 15Y 4s"),
    F(7, 28, "l 15Y 4s"),
    F(8, 27, "l 13Y 4s"),
    F(8, 27, "l 12Y 5s"),
    F(9, 26, "l 10Y 5s"),
    F(9, 26, "10Y 6s"),
    "10. 8B 8K 10.",
    "8. B lYYYYYs K 2. B lYYYYYs K 8.",
    "6. B lYYYYYYYs K 2. B lYYYYYYYs K 6.",
    "6. B lYYdYYdYs K 2. B lYYdYYdYs K 6.",
    "6. 11K 2. 11K 6.",
]

PUT = []
for ox in (11, 23):                                           # ojitos ovalados con brillo
    PUT += [(ox, 13, 'W'), (ox + 1, 13, 'E'), (ox, 14, 'E'), (ox + 1, 14, 'E'), (ox, 15, 'E'), (ox + 1, 15, 'E')]
PUT += [(16, 16, 'e'), (17, 16, 'E'), (18, 16, 'E'), (19, 16, 'E'), (17, 17, 'E'), (18, 17, 'E')]   # nariz
PUT += [(15, 18, 'E'), (16, 18, 'E'), (17, 19, 'E'), (18, 19, 'E'), (19, 18, 'E'), (20, 18, 'E')]   # boquita

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
    h.save(out / 'purin.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'purin_x9.png')
    print('ok', h.size, len(FILAS))
