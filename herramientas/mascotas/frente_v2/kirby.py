# -*- coding: utf-8 -*-
"""Kirby dibujado a mano, pixel a pixel (estilo sprites de Pokemon)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista
from _h import mk

LEYENDA = {'B': '#8a2a58', 'K': '#3c0f2a', 'L': '#fde0ec', 'P': '#f8a8c8', 'S': '#d878a8', 'Q': '#b85084',
           'C': '#f0507a', 'E': '#14184c', 'e': '#3a5cd0', 'W': '#ffffff',
           'M': '#a01838', 'T': '#f86078',
           'R': '#e02840', 'r': '#f87464', 'd': '#a01030', 'b': '#7a1830', 'k': '#3a0a18', '.': None}
row = mk(40)
PRE, POST = 'BPPPPPPPPP', 'PPPSSSSK'
PC1, QC1 = 'BPPPPCCCPP', 'PPCCCSSK'
PC2, QC2 = 'BPPPCCCCPP', 'PCCCCSSK'


def cara(l, g, r, pre=PRE, post=POST):
    return row(30, pre + l + g + r + post)


FILAS = [
    row(10, 'B', 'B', 'K'),
    row(16, 'BBB', 'L', 'PPKK'),
    row(20, 'BBLLL', 'L', 'PPPSK'),
    row(24, 'BLLLLL', 'P', 'PPSSK'),
    row(26, 'BLLLL', 'P', 'PSSSK'),
    row(28, 'BLLL', 'P', 'PPSSSK'),
    row(28, 'BLL', 'P', 'PPSSSK'),
    row(30, 'BLP', 'P', 'PPPSSSSK'),
    cara('PEEP', 'PPPP', 'PEEP'),
    cara('WWEE', 'PPPP', 'WWEE'),
    cara('WEEE', 'PPPP', 'WEEE'),
    cara('EEEE', 'PPPP', 'EEEE'),
    cara('EEEE', 'PPPP', 'EEEE'),
    cara('EEEE', 'PPPP', 'EEEE'),
    cara('eeee', 'PPPP', 'eeee', PC1, QC1),
    cara('PeeP', 'PMMP', 'PeeP', PC2, QC2),
    cara('PPPP', 'PTTP', 'PPPP', PC1, QC1),
    row(30, 'BP', 'P', 'PPPSSSSK'),
    row(30, 'BP', 'P', 'PPPSSSSK'),
    row(32, 'BBLP', 'P', 'PPSSSKK'),
    row(32, 'BLPPQ', 'P', 'QSSSSK'),
    row(32, 'BPPPQ', 'P', 'QSSSSK'),
    row(32, 'BPPPQ', 'P', 'QSSSKK'),
    row(32, '.KPPQ', 'P', 'QSSKK.'),
    row(30, 'KKP', 'P', 'PSSSSK'),
    row(30, 'KP', 'P', 'PPSSSSK'),
    row(28, 'KP', 'P', 'PSSSSK'),
    row(26, 'KP', 'S', 'SSSK'),
    row(34, '..' + '..BBBBBBBB..', 'S', '..BBBBBBBB..' + '..'),
    row(34, '..' + '.BrrrRRRRRK.', 'S', '.BrrrRRRRRK.' + '..'),
    row(34, '..' + 'BrrRRRRRRRdK', 'K', 'BrrRRRRRRRdK' + '..'),
    row(34, '..' + 'BrRRRRRRRRdK', '.', 'BrRRRRRRRRdK' + '..'),
    row(34, '..' + 'BRRRRRRRRddK', '.', 'BRRRRRRRRddK' + '..'),
    row(34, '..' + 'BRRRRRRRdddK', '.', 'BRRRRRRRdddK' + '..'),
    row(34, '..' + '.KRRRddddddK', '.', '.KRRRddddddK' + '..'),
    row(34, '..' + '..KKKKKKKK..', '.', '..KKKKKKKK..' + '..'),
]


def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))


if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'; out.mkdir(exist_ok=True)
    h = hojas(); h.save(out / 'kirby.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'kirby_x9.png')
    print('ok', h.size, len(FILAS))
