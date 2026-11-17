# -*- coding: utf-8 -*-
"""Galería: junta todas las mascotas dibujadas (cada <clave>.py con hojas()) a la misma escala, para comprobar que
parecen de la misma familia (mismo contorno, misma luz, misma saturación). Uso:
    python galeria.py            -> vista/galeria.png (todas)
    python galeria.py pikachu kirby  -> solo esas
"""
import importlib.util
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import pix  # noqa: E402


def cargar(clave):
    spec = importlib.util.spec_from_file_location(f'mascota_{clave}', AQUI / f'{clave}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(claves=None):
    claves = claves or sorted(p.stem for p in AQUI.glob('*.py') if p.stem not in ('pix', 'galeria', 'exportar', 'ascii', 'desde_referencia', 'trazo', '_h', 'pikachu_taller', 'comparar', 'vista_reproductor', 'importar_hoja', 'integrar_v4', 'pokemon_exacto', 'desde_png_ia'))
    hojas = []
    for c in claves:
        ancho = pix.W
        try:
            pix.W = 48
            h = cargar(c).hojas()
        except Exception as e:  # noqa: BLE001
            print('FALLA', c, e)
            continue
        finally:
            pix.W = ancho
        hojas.append((c, h))
    esc, cols = 5, 3
    celda_w = max(h.width for _, h in hojas) * esc + 30
    celda_h = pix.H * esc + 44
    filas = (len(hojas) + cols - 1) // cols
    img = Image.new('RGBA', (celda_w * cols, celda_h * filas), (30, 34, 46, 255))
    d = ImageDraw.Draw(img)
    for i, (c, h) in enumerate(hojas):
        x, y = (i % cols) * celda_w + 15, (i // cols) * celda_h + 8
        d.text((x, y), c, fill=(190, 200, 220))
        img.alpha_composite(h.resize((h.width * esc, h.height * esc), Image.NEAREST), (x, y + 22))
    (AQUI / 'vista').mkdir(exist_ok=True)
    img.save(AQUI / 'vista' / 'galeria.png')
    print('galería con', len(hojas), 'mascotas')


if __name__ == '__main__':
    main(sys.argv[1:] or None)
