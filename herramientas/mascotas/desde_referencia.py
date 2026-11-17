# -*- coding: utf-8 -*-
"""Convierte una imagen de pixel art ampliada (por ejemplo un JPG de un sprite) a su cuadrícula real de píxeles.

    python desde_referencia.py "C:/ruta/pikachu pixelado.jpg" pikachu --rejilla 80

Pasos: muestrea el centro de cada celda de la cuadrícula, quita el fondo (blanco conectado con el borde, para no borrar
los brillos blancos de adentro), limpia los restos de compresión del JPG juntando colores casi iguales y deja
`referencias/<clave>_base.png` (solo el dibujo, a 1x, sin márgenes). Ese PNG lo usa `<clave>.py`.
"""
import argparse
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

AQUI = Path(__file__).parent


def convertir(ruta, clave, rejilla=80, colores=14, umbral_fondo=232):
    im = Image.open(ruta).convert('RGB')
    a = np.array(im).astype(int)
    n = rejilla
    paso_x, paso_y = a.shape[1] / n, a.shape[0] / n
    celdas = np.zeros((n, n, 3), int)
    for j in range(n):
        for i in range(n):
            x, y = int((i + 0.5) * paso_x), int((j + 0.5) * paso_y)
            celdas[j, i] = a[max(0, y - 1):y + 2, max(0, x - 1):x + 2].reshape(-1, 3).mean(axis=0)
    claro = celdas.min(axis=2) > umbral_fondo
    # fondo = celdas claras conectadas con el borde
    fondo = np.zeros((n, n), bool)
    cola = deque((j, i) for j in range(n) for i in (0, n - 1) if claro[j, i])
    cola.extend((j, i) for i in range(n) for j in (0, n - 1) if claro[j, i])
    while cola:
        j, i = cola.popleft()
        if fondo[j, i] or not claro[j, i]:
            continue
        fondo[j, i] = True
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nj, ni = j + dj, i + di
            if 0 <= nj < n and 0 <= ni < n and not fondo[nj, ni]:
                cola.append((nj, ni))
    ys, xs = np.where(~fondo)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    sub = celdas[y0:y1 + 1, x0:x1 + 1].astype(np.uint8)
    mascara = ~fondo[y0:y1 + 1, x0:x1 + 1]
    # juntar colores casi iguales (restos de compresión) SIN perder los poco frecuentes pero importantes
    # (mejillas, puntas de las orejas): se agrupan por cercanía y cada grupo con >= 3 celdas es un color de la paleta
    pix = sub.reshape(-1, 3).astype(int)
    cuenta = {}
    for p in pix:
        k = tuple(p // 20)
        cuenta.setdefault(k, []).append(p)
    paleta = [np.mean(v, axis=0) for v in cuenta.values() if len(v) >= 3]
    paleta = np.array(paleta)
    d = ((pix[:, None, :] - paleta[None, :, :]) ** 2).sum(axis=2)
    q = paleta[d.argmin(axis=1)].round().astype(np.uint8).reshape(sub.shape)
    print('colores en la paleta:', len(paleta))
    sal = np.zeros(sub.shape[:2] + (4,), np.uint8)
    sal[..., :3] = q
    sal[..., 3] = np.where(mascara, 255, 0)
    out = AQUI / 'referencias'
    out.mkdir(exist_ok=True)
    destino = out / f'{clave}_base.png'
    Image.fromarray(sal, 'RGBA').save(destino)
    print(f'{clave}: dibujo de {sal.shape[1]}x{sal.shape[0]} px -> {destino}')
    return destino


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('imagen')
    p.add_argument('clave')
    p.add_argument('--rejilla', type=int, default=80)
    p.add_argument('--colores', type=int, default=14)
    a = p.parse_args()
    sys.exit(0 if convertir(a.imagen, a.clave, a.rejilla, a.colores) else 1)
