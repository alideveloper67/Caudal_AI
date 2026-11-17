# -*- coding: utf-8 -*-
"""Bob Esponja, pixel art a mano (texto), de pie, de frente."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ascii import dibujo, hoja_rebote
from pix import vista

LEYENDA = {'K': '#14100c', 'O': '#a87808', 'Y': '#f8d820', 'L': '#fff470', 'S': '#d8a810', 'P': '#c69a10',
           'W': '#ffffff', 'w': '#c8d0e0', 'E': '#58a8e8', 'R': '#d02828', 'r': '#8c1818', 'N': '#8a5428',
           'n': '#5a3414', 'M': '#b87838', '.': None}

E = [".KKKKK.", "KWWWWWK", "KWEWEWK", "KWEKKwK", "KWEKKwK", "KWWWwwK", ".KKKKK."]

def cara(i, izq, der):
    return 'O' + izq + E[i] + E[i][1:] + der + 'K'   # ojos pegados, comparten el contorno central

INNER = [
 "..OOOOOOOOOOOOOOOOOOOO..",
 ".OLLLLLLYYYYYYYYYYYYYYK.",
 "OLLLLYYYYYYYYYYYYPYYYYYK",
 "OLLYYYYPYYYYYYYYYYYYYYYK",
 cara(0, 'LYYYY', 'YYYY'),
 cara(1, 'LYPYY', 'YYYY'),
 cara(2, 'YYYYY', 'YYYY'),
 cara(3, 'YYYYY', 'YYPY'),
 cara(4, 'YPYYY', 'YYYY'),
 cara(5, 'YYYYY', 'YYYY'),
 cara(6, 'YYYYY', 'YYPY'),
 "OYYYYYYYYYYYYKKKYYYYYYYK",
 "OYYPYYPYYYYYKYLYKYYPYYYK",
 "OYYYYYYYYYYYKYYSYKYYYYYK",
 "OYYYYYYYYYYYYKSSKYYYYYYK",
 "OYYYYYYYYYYYYYYYYYYYYYYK",
 "OYYYYKKKKKKKKKKKKKKKYYYK",
 "OYYYYKRRRRRRRRRRRRRRKYYK",
 "OYPYYKRRRWWKWWRRRRRRKYYK",
 "OYYYYYKRRWWKWWRRRRRKYYYK",
 "OYYYYYYKKRRRRRRRKKKYYYYK",
 "OYYYYYYYYKKKKKKKYYYYPYYK",
 "OYYPYYYYYYYYYYYYYYYYYYSK",
 "OYYYYYYYYYYYYPYYYYYYYSSK",
 "OSSSSSSSSSSSSSSSSSSSSSSK",
]
RESTO = [
 "......KWWWWWWWWWRRWWWWWWWWK.....",
 "......KWWWWWWWWRRRRWWWWWwwK.....",
 "......KWWWWWWWWWRRWWWWWwwwK.....",
 "......KKKKKKKKKKKKKKKKKKKKK.....",
 "......KMNNNNNNNNNNNNNNNNNNK.....",
 "......KMNNNNNNNNNNNNNNNNnnK.....",
 "......KNNNNNNNNNNNNNNNNnnnK.....",
 "......KNNNNNNnnnnnnNNNNnnnK.....",
 "......KKKKKKKKKKKKKKKKKKKKK.....",
]
G = [list(('....' + r + '....')) for r in INNER] + [list(r) for r in RESTO]
G += [list('.' * 32) for _ in range(44 - len(G))]

def put(fila, col, txt):
    for i, c in enumerate(txt):
        G[fila][col + i] = c

# brazo izquierdo levantado (saluda) y mano con dedos
for f, t in {8: "K.K.", 9: "KYYK", 10: "KYYK", 11: ".KYK"}.items(): put(f, 0, t)
for f in range(12, 25): put(f, 1, ".OYY"[1:] if False else "OYY")
put(25, 1, "OYY"); put(26, 2, "OY"); 
# brazo derecho caído y mano
for f in range(26, 34): put(f, 27, "YSK")
for f, t in {34: "KYYYK", 35: "KYYYK", 36: ".KKK."}.items(): put(f, 26, t)
# piernas, calcetines y zapatos
for f in range(33, 37):
    put(f, 9, "OYYK"); put(f, 19, "OYYK")
for f, t in {37: "KWWK", 38: "KRRK", 39: "KWWK", 40: "KWwK"}.items():
    put(f, 9, t); put(f, 19, t)
put(41, 8, "KKKKKK"); put(41, 18, "KKKKKK")
put(42, 6, "KKwKKKKK"); put(42, 18, "KKwKKKKKK"[:8])
put(43, 5, "KKKKKKKKK"); put(43, 18, "KKKKKKKKK")
FILAS = [''.join(r) for r in G]

def hojas():
    return hoja_rebote(dibujo(FILAS, LEYENDA))

if __name__ == '__main__':
    vd = Path(__file__).parent / 'vista'; vd.mkdir(exist_ok=True)
    h = hojas()
    vista([h], escala=9, fondo=(255, 255, 255), salida=vd / 'bob_x9.png')
    print(len(FILAS), set(len(f) for f in FILAS))
