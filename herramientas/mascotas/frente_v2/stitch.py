# -*- coding: utf-8 -*-
"""Stitch dibujado a mano, pixel a pixel (mitad izquierda a mano, reflejo con luz/sombra cambiadas)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista
from _h import espejo, banda_der, parche

LEYENDA = {'B': '#1a2a6a', 'K': '#0a0e2c', 'L': '#7ea6f4', 'P': '#3868d0', 'S': '#2848a8', 'Q': '#20388a',
           'p': '#f6b0c8', 'q': '#d880a4', 'U': '#bcdcfa', 'u': '#8cb8ec', 'E': '#0a0a16', 'W': '#ffffff',
           'N': '#101018', 'M': '#3a0a20', 'T': '#fafafa', 'm': '#c03050', '.': None}

MITAD = [
    "..BBBB",                                        # 0
    ".BpppqB",
    ".BppppqB",
    ".BpppqqqB",
    "..BppqqqqB",
    "..BpqqqqPB",                                    # 5
    "...BqqqPPPB",
    "...BqqPPPPPB",
    "....BqPPPPPPB..BBBBBBB",
    "....BLPPPPPPBLLLLLLLLL",
    ".....BLPPPPBLLLLLLLLLL",                        # 10
    "......BLPPBLLLLLLLLLLL",
    ".......BPBLLLLLLLLLLLL",
    "........BLLLPPPPPPPPPP",
    "........BPPPPPEEEPPPPP",
    "........BPPPPEEEEEPPPP",                        # 15
    "........BPPPEWWEEEUUNN",
    "........BPPPEWEEEEUUNN",
    "........BPPPEEEEEEUUUU",
    "........BPPPEEEEEEUUUU",
    "........BPPPPPEEEUUUUU",                        # 20
    "........BPPPPPPMMMMMMM",
    ".........BPPPPPMTTTTTT",
    "..........BPPPPMMMmmmm",
    "...........BPPPPPUUUUU",
    "............BPPPPPUUUU",                        # 25
    ".........BBPPPPPPUUUUU",
    "........BLPPPPPPPUUUUU",
    "........BLPPPPPPUUUUUU",
    "........BPPPQPPUUUUUUU",
    ".........BPQPPPUUUUUUU",                        # 30
    ".........BBPPPPUUUUUUU",
    "..........BPPPPUUUUUUU",
    "...........BPPPPUUUUUU",
    "...........BPPPPPPPPPP",
    "........BBBBBBBPPPPPPP",                        # 35
    ".......BLPPPPPPPBBBBBB",
    ".......BPPPPPPPPPQQQQQ",
    ".......BPPPPPPPPPPBBBB",
    ".......BBBBBBBBBBBB...",
]
MAPA = {'B': 'K', 'L': 'P', 'U': 'U'}
FILAS = espejo(MITAD, MAPA, 22)
FILAS = banda_der(FILAS, 'P', 'S', 4)
FILAS = banda_der(FILAS, 'U', 'u', 2)
FILAS = parche(FILAS, [(30, 16, 'E'), (29, 16, 'E'), (30, 17, 'E'), (27, 16, 'W'), (28, 16, 'W'), (27, 17, 'W')])


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'; out.mkdir(exist_ok=True)
    h = hojas(); h.save(out / 'stitch.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'stitch_x9.png')
    print('ok', h.size, len(FILAS))
