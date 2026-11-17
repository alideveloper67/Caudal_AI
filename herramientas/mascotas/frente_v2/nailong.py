# -*- coding: utf-8 -*-
"""Nailong (el dragoncito amarillo) dibujado píxel a píxel como texto, de frente."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'B': '#9a5a10', 'K': '#3a2208',                          # contorno lado luz / lado sombra
    'Y': '#f8e080', 'l': '#fff4b0', 's': '#e0b848', 'd': '#c09030',   # cuerpo: base, luz, sombra, sombra honda
    'b': '#fff8d0', 'e': '#ecd890',                          # barriguita
    'h': '#f2b840', 'H': '#ffe080',                          # cuernos
    'E': '#201008', 'W': '#ffffff', 'M': '#8a2818', 'p': '#f8a078',   # ojos, brillo, boca, mejillas
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
    """Silueta: contorno claro en la columna a, oscuro en la b, y el relleno `mid` entre medias."""
    return '.' * a + 'B' + R(mid) + 'K' + '.' * (W - b - 1)


ROWS = [
    "9. BK 14. BK 9.",
    "8. BHhK 12. BHhK 8.",
    "7. BHhhhK 10. BHhhhK 7.",
    "7. BHhhhK 5B 5K BHhhhK 7.",
    F(9, 26, "3l 11Y 2s"),
    F(7, 28, "4l 14Y 2s"),
    F(6, 29, "6l 15Y s"),
    F(5, 30, "4l 18Y 2s"),
    F(4, 31, "3l 21Y 2s"),
    F(3, 32, "3l 22Y 3s"),
    F(3, 32, "2l 23Y 3s"),
    F(3, 32, "5Y WE 14Y WE 4Y s"),
    F(3, 32, "5Y EE 14Y EE 3Y 2s"),
    F(3, 32, "5Y EE 14Y EE 3Y 2s"),
    F(3, 32, "2Y 3p 7Y 4M 7Y 3p 2s"),
    F(3, 32, "2Y 3p 8Y 2M 8Y 3p 2s"),
    F(3, 32, "24Y 4s"),
    F(3, 32, "22Y 6s"),
    F(4, 31, "22Y 4s"),
    "5. 13B 13K 5.",
    F(6, 29, "22s"),
    F(5, 30, "2l 20Y 2s"),
    F(5, 30, "7Y 10b 5Y 2s"),
    F(4, 31, "lY B 3Y 14b 3s K ss"),
    F(3, 32, "lYY B 3Y 14b 3s K Yss"),
    F(3, 32, "lYY B 3Y 14b 3s K Yss"),
    F(3, 32, "YYY B 3Y 14b 3s K Yss"),
    F(3, 32, "YYs B 3Y 14b 3s K sss"),
    F(4, 31, "Ys B 3Y 14b 3s K ss"),
    "5. BBB 3Y 14b 3s KKK 5.",
    F(5, 30, "5Y 14b 5s"),
    F(5, 30, "5Y 14b 5s"),
    F(5, 30, "5Y 6b 8e 5s") + "",
    F(6, 29, "5Y 10e 7s"),
    F(7, 28, "3Y 17s"),
    F(8, 27, "2Y 16s"),
    "9. B lYYYYs K 2. B lYYYss K 9.",
    "9. B YYYYYs K 2. B YYYYss K 9.",
    "9. B YYYYYs K 2. B YYYYss K 9.",
    "7. B lYYYYYYYs K B lYYYYYYYs K 7.",
    "5. B lYYYYYYYYYs K B lYYYYYYYYYs K 5.",
    "4. B lYYdYYdYYYYs K B lYYdYYdYYYYs K 4.",
    "4. B lYYYYYYYYYss K B lYYYYYYYYYss K 4.",
    "4. 28K 4.",
]
# cola corta redondeada a la derecha (columnas 30-34)
ROWS[32] = F(5, 30, "5Y 6b 8e 5s")[:31] + "BBK" + ".."
ROWS[33] = F(6, 29, "5Y 10e 7s")[:30] + "lYsK" + ".."
ROWS[34] = F(7, 28, "3Y 17s")[:29] + ".BBBK" + ".."

FILAS = []
for n, f in enumerate(ROWS):
    r = R(f)
    if len(r) != W:
        print('fila', n, 'mide', len(r), f)
    FILAS.append(r)


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'nailong.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'nailong_x9.png')
    print('ok', h.size, len(FILAS))
