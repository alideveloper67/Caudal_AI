# -*- coding: utf-8 -*-
"""Totoro dibujado a mano, pixel a pixel (mitad izquierda a mano, reflejo con luz/sombra cambiadas)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista
from _h import espejo, banda_der, parche

LEYENDA = {'B': '#2c3350', 'K': '#12162a', 'L': '#bcc4d4', 'P': '#8890a2', 'S': '#6a7288', 'Q': '#7a8296',
           'C': '#f4e8c4', 'c': '#d4c496', 'v': '#9a8860', 'W': '#ffffff', 'E': '#0c0c18', 'N': '#14141e',
           'm': '#5a1c2c', '.': None}

MITAD = [
    "..........BBB",                                # 0
    ".........BLLPB",
    ".........BLPPPB",
    ".........BLPPPPB",
    ".........BLPPPPPB",
    ".........BLPPPPPBBBBBB",                        # 5
    ".........BLPPPPPBLLLLL",
    "........BLPPPPPPPPPPPP",
    ".......BLPPPPPPPPPPPPP",
    "......BLPPPPPPPPPPPPPP",
    "......BPPPPPPPPPPPPPPP",                        # 10
    ".....BLPPPPPPPPPPPPPPP",
    "....BPPPPPPPKKKKPPPPPP",
    "....BPPPPPPKWWWWKPPPPP",
    "...BLPPPPPPKWEEWKPPPPP",
    "...BPPPPPPPKWEEWKPPPPP",                        # 15
    "...BPPPPPPPKWWWWKPPPNN",
    "...BPPPPPPPPKKKKPPPPNN",
    "..BLKKKKKPPPPPPPPPPPPP",
    "..BLPPPPPPKKKKKKKKKKKK",
    "..BLPPPPPPPKmmmmmmmmmm",                        # 20
    "..BPPPPPPPPPKKKKKKKKKK",
    "..BLKKKKKPPPPPPPPPPPPP",
    ".BLPPPPPPPPPPPPPPPPPPP",
    ".BLPPPPPPPPPPPPCCCCCCC",
    ".BLPPPPPPPPPPCCCCCCCCC",                        # 25
    "BLPPPPPPPPPPCCCCCCCCCC",
    "BLPPPPPPPPCvCvCvCvCvCv",
    "BLPPPPPPPCCCvCCCvCCCvC",
    "BLPPPPPPCCCCCCCCCCCCCC",
    "BLPPPPPPCCCCCCCCCCCCCC",                        # 30
    "BLPPPPPPCCCCCvCvCvCvCC",
    "BLPPPPPPCCCCCCvCCCvCCC",
    "BLPPPPPPCCCCCCCCCCCCCC",
    "BPPPPPPPCCCCCCCCCCCCCC",
    ".BPPPPPPPCCCCCCCCCCCCC",                        # 35
    ".BPPPPPPPPCCCCCCCCCCCC",
    "..BPPPPPPPPPCCCCCCCCCC",
    "...BPPPPPPPPPPPPPPPPPP",
    "....BBBBBBBBBBBBBBBBBB",
    "......BPPPPPPB",                                # 40
    "......BBBBBBBB",
]
MAPA = {'B': 'K', 'L': 'P'}
FILAS = espejo(MITAD, MAPA, 22)
FILAS = banda_der(FILAS, 'P', 'S', 4)
FILAS = banda_der(FILAS, 'C', 'c', 3)
FILAS = parche(FILAS, [(5, y, 'Q') for y in range(27, 34)] + [(38, y, 'S') for y in range(27, 34)]
               + [(5, 34, 'Q'), (4, 34, 'Q'), (38, 34, 'S'), (39, 34, 'S'),
                  (7, 41, 'K'), (9, 41, 'K'), (11, 41, 'K')])


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA), ancho_cuadro=48)


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'; out.mkdir(exist_ok=True)
    h = hojas(); h.save(out / 'totoro.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'totoro_x9.png')
    print('ok', h.size, len(FILAS))
