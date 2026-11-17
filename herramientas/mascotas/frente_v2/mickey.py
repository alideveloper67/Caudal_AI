# -*- coding: utf-8 -*-
"""Mickey Mouse dibujado píxel a píxel como texto (de frente, ligeramente girado a la derecha)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote  # noqa: E402
from pix import vista  # noqa: E402

LEYENDA = {
    'K': '#14141c', 'k': '#34344a', 'g': '#5a5a78',          # negro, luz, brillo
    'S': '#f8c490', 's': '#d8946c', 'd': '#8a4a2a', 'h': '#ffe4c0',  # piel
    'W': '#ffffff', 'w': '#d4d8ec', 'v': '#9aa0c4',          # guantes
    'R': '#e83a30', 'r': '#a81c24', 'L': '#ff7058', 'T': '#6a1018',  # rojo
    'Y': '#f8d020', 'y': '#d09010', 'O': '#8a5008', 'J': '#fff0a0',  # amarillo
    '.': None,
}


def R(s):
    """Fila con repeticiones: '4.' = 4 puntos; lo demás se copia tal cual."""
    out = ''
    for t in s.split():
        m = re.fullmatch(r'(\d+)(\D)', t)
        out += m.group(2) * int(m.group(1)) if m else t
    return out


ROWS = [
    "4. 4K 20. 4K 4.",
    "3. KggKKK 18. KgKKKK 3.",
    "2. KgggKKKK 16. KggKKKKK 2.",
    "1. KgggKKKKKK 14. KggKKKKKKK 1.",
    "1. KgkKKKKKKK 14. KgkKKKKKKK 1.",
    "1. KkKKKKKKKK 14. KkKKKKKKKK 1.",
    "1. KkKKKKKKKK 14. KkKKKKKKKK 1.",
    "2. KkKKKKKK 2. gkk 9K 2. KkKKKKKK 2.",
    "3. KkKKKK gkk 15K 6K 3.",
    "7. gk 20K 7.",
    "6. 4K hSSSS 6K SSSSs 4K 6.",
    "5. 4K hhSSSSS 4K SSSSSss 4K 5.",
    "4. 4K hhhSSSSSS 2K SSSSSSsss 4K 4.",
    "4. d hhSSSSSS SKKS 2S SKKS SSSSSsss K 4.",
    "4. d hhSSSSSS KWWK 2S KWWK SSSSSsss K 4.",
    "4. d hSSSSSSS KWKK 2S KKWK SSSSssss K 4.",
    "4. d hSSSSSSS KWKK 2S KKWK SSSSssss K 4.",
    "4. d SSSSSSSS SKKS 2S SKKS SSSSssss K 4.",
    "5. d hSSSSSSSSS KgKK SSSSSSssss K 5.",
    "5. d SSSSSSSSS KgKKKK SSSSSSsss K 5.",
    "6. d SSSSSSSS SKKKKS SSSSssss K 6.",
    "7. d 13S 7s K 7.",
    "7. d SSS K 12S K sss K 7.",
    "8. d SS 14K ss K 8.",
    "9. d SS KRLLRRRRRrrK ss K 9.",
    "11. d 10S 2s K 11.",
    "13. 10K 13.",
    "11. gk 12K 11.",
    "7. gkK k g 13K k KKK 7.",
    "6. gkKK k g 13K k KKKK 6.",
    "4. KhWWwK T LL 12R K KWWwvK 4.",
    "4. KhWWWK T LR JY 6R JY Rr K KWWvvK 4.",
    "4. KWWWvK T RR Yy 6R Yy rr K KWWvvK 4.",
    "5. KWvK 1. T 12R rr K 1. KWvK 5.",
    "6. KK 2. T 6R r r 5R r K 2. KK 6.",
    "10. T 6r K T 6r K 5. gKK 2.",
    "12. gkKK 4. gkKK 5. gKKK 3.",
    "12. gkKK 4. gkKK 3. gKKK 5.",
    "12. gkKK 4. gkKK 1. gKKK 7.",
    "10. 7K 2. 7K 10.",
    "7. KhYYYYYYyyK KYYYYYYYyyK 7.",
    "5. KhYYYYYYYYyyK K YYYYYYYYyyyK 5.",
    "4. KhYYYYYYYYYyyK K YYYYYYYYYyyyK 4.",
    "4. K 12O K K 12O K 4.",
]

FILAS = []
for n, f in enumerate(ROWS):
    r = R(f)
    if len(r) != 36:
        print('fila', n, 'mide', len(r), f)
    FILAS.append(r)


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'mickey.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'mickey_x9.png')
    print('ok', h.size, len(FILAS))
