# -*- coding: utf-8 -*-
"""Doraemon dibujado a mano, pixel a pixel (mitad izquierda a mano, reflejo con luz/sombra cambiadas)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista
from _h import espejo, banda_der, parche

LEYENDA = {'B': '#103a78', 'K': '#06183c', 'L': '#6cc4ff', 'P': '#1c94e4', 'S': '#1068b8',
           'W': '#ffffff', 'w': '#cddbea', 'E': '#0a0a16', 'R': '#d82430', 'r': '#f86a70',
           'Y': '#fcd830', 'y': '#c89418', 'm': '#a01830', 't': '#f06078', 'N': '#d82430', '.': None}

MITAD = [
    "..............BBBBBB",                         # 0
    "...........BBLLLLLLL",
    ".........BBLLLPPPPPP",
    ".......BBLLPPBBBBBPP",
    "......BLPPPPBWWWWWBP",
    ".....BLPPPPPBWWWWWBP",                        # 5
    "....BLPPPPPPBWWEWWBP",
    "....BPPPPPPPBWWEEWBP",
    "....BPPPPPPPBWWEEWBP",
    "....BPPPPPPPBWWWWWBP",
    "....BPPPPBWWBBBBBBBW",                        # 10
    "....BPPBWWWWWWWWWWRR",
    "....BPBWBBBBBBWWWRRR",
    "....BPBWWWWWWWWWWWRR",
    "....BPBWBBBBBBWWWWWB",
    "....BPBWWBBWWWWWWWWB",                        # 15
    "....BPBWWWWBBBBBBBBB",
    "....BPBWWWWBmmmmttttt".replace("ttttt", "tttt"),
    "....BPPBWWWBBBBBBBBB",
    "......BPBWWWWWWWWWWW",
    "........BPBWWWWWWWWW",                        # 20
    "..........BBBBBBBBBB",
    ".........BrrRRRRRRRR",
    ".........BRRRRRRRRRR",
    "..........BLPPPPPPBB",
    "..........BLPPPPPBYY",                        # 25
    "..........BLPPPPPBYy",
    "..........BPPPPPPBBB",
    "......BBLLPPPPBWWWWW",
    "......BLPPPPPPBWWWWW",
    "....BBBPPPPPPPBWWWWW",                        # 30
    "....BWWBPPPPPPBWWWWW",
    "....BWWWBPPPPPBBBBBB",
    "....BWWWBPPPPPBBWWWW",
    ".....BBBBPPPPPBWBWWW",
    "..........BPPPBWWBBB",                        # 35
    "......BWWWWWWWWWWWW.",
    "......BWWWWWWWWWWWWB",
    "......BWWWWWWWWWWWwB",
    ".......BBBBBBBBBBBBB",
]
MAPA = {'B': 'K', 'L': 'P', 'r': 'R'}
FILAS = espejo(MITAD, MAPA, 20)
FILAS = banda_der(FILAS, 'W', 'w', 3)
FILAS = banda_der(FILAS, 'P', 'S', 3)
FILAS = parche(FILAS, [(36, 35, 'K'), (37, 35, 'K'), (35, 36, 'K'), (36, 36, 'r'), (37, 36, 'R'), (38, 36, 'K'),
                       (35, 37, 'K'), (36, 37, 'R'), (37, 37, 'R'), (38, 37, 'K'), (36, 38, 'K'), (37, 38, 'K')])


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'; out.mkdir(exist_ok=True)
    h = hojas(); h.save(out / 'doraemon.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'doraemon_x9.png')
    print('ok', h.size, len(FILAS))
