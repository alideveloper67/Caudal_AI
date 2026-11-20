# -*- coding: utf-8 -*-
"""Exporta las hojas dibujadas a las dos carpetas de arte que usa Caudal (móvil y escritorio).

    python exportar.py                 -> exporta todas las mascotas que tengan <clave>.py
    python exportar.py pikachu kirby   -> solo esas

No toca las estelas (estela_<clave>.png) ni el catálogo. Comprueba que cada hoja mida lo que dice el catálogo
(`cuadros` del catálogo, 2 por defecto, de ancho x alto) antes de escribir; si no coincide, avisa y no la exporta.
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
DESTINOS = [RAIZ / 'app' / 'assets' / 'mascotas', RAIZ / 'escritorio' / 'descargador' / 'mascotas']
sys.path.insert(0, str(AQUI))
import galeria  # noqa: E402
import pix  # noqa: E402


def main(claves):
    catalogo = {m['clave']: m for m in json.loads((DESTINOS[0] / 'catalogo.json').read_text(encoding='utf-8'))}
    claves = claves or sorted(p.stem for p in AQUI.glob('*.py') if p.stem not in ('pix', 'galeria', 'exportar', 'ascii', 'desde_referencia', 'trazo', '_h', 'pikachu_taller', 'comparar', 'vista_reproductor', 'importar_hoja', 'integrar_v4', 'pokemon_exacto', 'desde_png_ia', 'personajes_nov', 'integrar_nov', 'fondos_tematicos'))
    hechas, fallas = [], []
    for c in claves:
        m = catalogo.get(c)
        if not m:
            fallas.append((c, 'no está en el catálogo'))
            continue
        ancho = pix.W
        try:
            pix.W = 48
            h = galeria.cargar(c).hojas()
        except Exception as e:  # noqa: BLE001
            fallas.append((c, f'no se pudo dibujar: {e}'))
            continue
        finally:
            pix.W = ancho
        d = max(1, int(m.get('densidad', 1)))
        esperado = (m['ancho'] * max(2, int(m.get('cuadros', 2))) * d, m['alto'] * d)
        if h.size != esperado:
            fallas.append((c, f'mide {h.size} y el catálogo pide {esperado}'))
            continue
        for d in DESTINOS:
            h.save(d / f'{c}.png')
        hechas.append(c)
    print('exportadas:', ', '.join(hechas) or '(ninguna)')
    for c, why in fallas:
        print('NO exportada', c, '-', why)
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
