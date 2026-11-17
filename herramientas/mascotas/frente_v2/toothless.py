# -*- coding: utf-8 -*-
"""Chimuelo dibujado a mano, pixel a pixel (mitad izquierda a mano, reflejo con luz/sombra cambiadas)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista
from _h import espejo, banda_der, parche

LEYENDA = {'K': '#0a0a12', 'L': '#7a7cb4', 'P': '#34344c', 'S': '#222234', 'Q': '#46466a', 'p': '#5e4678',
           'G': '#6cec4c', 'g': '#2c9c34', 'E': '#06060c', 'W': '#ffffff', 'M': '#08080e', 'N': '#0c0c14',
           'R': '#d82828', 'r': '#f86a50', 'D': '#a01818', '.': None}

MITAD = [
    ".....KK",                                      # 0
    "....KLPK",
    "....KLPPK",
    "....KLpPPK",
    "....KLppPPK",
    ".....KLppPPKKKKKKKKKKK",                        # 5
    ".....KLppPPKLLLLLLLLL".replace("LLLLLLLLL", "LLLLLLLLLL"),
    "....KLPPPPPPPPPPPPPPPP",
    "...KLPPPPPPPPPPPPPPPPP",
    "..KLPPPPPPPPPPPPPPPPPP",
    "..KPPPPPPPPPPggggPPPPP",                        # 10
    "..KPPPPPPPPPgGEEGgPPPP",
    "..KPPPPPPPPgGWEEGGgPPP",
    "..KPPPPPPPPgGWEEGGgPPP",
    "..KPPPPPPPPgGGEEGGgPPP",
    "..KPPPPPPPPgGGEEGGgPPP",                        # 15
    "..KPPPPPPPPPgGGGGgPPPP",
    "..KPPPPPPPPPPggggPPPPP",
    "..KPPPPPPPPPPPPPPPPPLL",
    "..KPPPPPPPPPPPPPPPPNPP",
    "..KPPPPPPPPPMMPPPPPPPP",                        # 20
    "..KPPPPPPPPPPMMMMMMMMM",
    "...KPPPPPPPPPPPPPPPPPP",
    "....KPPPPPPPPPPPPPPPPP",
    ".....KKKKKKKPPPPPPPPPP",
    "....KLpppPPKPPPPPPPPPP",                        # 25
    "....KLppppPKPPPPPPPPPP",
    ".....KLpppPKPPPPPQQQQQ",
    ".....KLppPPKPPPPQQQQQQ",
    "......KLpPPKPPPPQQQQQQ",
    "......KLPPPKPPPPQQQQQQ",                        # 30
    ".......KLPPKPPPPQQQQQQ",
    ".......KKPPKPPPPPQQQQQ",
    "........KKPKPPPPPPQQQQ",
    "..........KPPPPPPPPPPP",
    ".........KPPPPPPPPPPPP",                        # 35
    "........KLPPPPPPPPPPPP",
    "........KPPPPPPPPPPPPP",
    ".......KLPPPPPPPPPPPPP",
    ".......KPPPPPPPPPPPPPP",
    "......KKKKKKKKKKKKKKKK",                        # 40
    ".......L.L.L..........",
]
MAPA = {'L': 'P'}
FILAS = espejo(MITAD, MAPA, 22)
FILAS = banda_der(FILAS, 'P', 'S', 4)
FILAS = parche(FILAS, [(30, 12, 'G'), (30, 13, 'G'), (27, 12, 'W'), (27, 13, 'W'),
                       (21, 37, 'K'), (22, 37, 'K'), (21, 38, 'K'), (22, 38, 'K'), (21, 39, 'K'), (22, 39, 'K'),
                       # cola con aleta roja
                       (34, 36, 'K'), (35, 36, 'K'), (36, 36, 'K'), (37, 36, 'K'), (38, 36, 'K'),
                       (34, 37, 'P'), (35, 37, 'P'), (36, 37, 'P'), (37, 37, 'S'), (38, 37, 'S'),
                       (34, 38, 'K'), (35, 38, 'K'), (36, 38, 'K'), (37, 38, 'K'), (38, 38, 'K'),
                       (38, 35, 'K'), (39, 35, 'K'), (39, 36, 'R'), (40, 36, 'K'),
                       (39, 37, 'r'), (40, 37, 'R'), (41, 37, 'K'),
                       (39, 38, 'R'), (40, 38, 'R'), (41, 38, 'D'), (42, 38, 'K'),
                       (39, 39, 'K'), (40, 39, 'D'), (41, 39, 'D'), (42, 39, 'K'), (40, 40, 'K'), (41, 40, 'K')])


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA), ancho_cuadro=48)


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'; out.mkdir(exist_ok=True)
    h = hojas(); h.save(out / 'toothless.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'toothless_x9.png')
    print('ok', h.size, len(FILAS))
