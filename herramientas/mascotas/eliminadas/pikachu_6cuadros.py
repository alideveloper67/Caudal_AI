# -*- coding: utf-8 -*-
"""Pikachu a partir del dibujo de referencia de la persona (referencias/pikachu_base.png, 45x44 px, hecho con
desde_referencia.py). Cuadro 0: de pie. Cuadro 1: «agachado» (se quita una fila del torso: el rebote clásico de los
sprites de Pokémon), con los pies siempre sobre la fila de abajo."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from pix import H, hoja, vista  # noqa: E402

def _base_exacta():
    """El dibujo de Pikachu sale de referencias/pikachu_exacto.py, generado y verificado con la skill pixel-art-exact
    (80x80 celdas, 13 colores, 0 celdas erróneas). Se recorta al rectángulo que ocupa el dibujo."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('pikachu_exacto', Path(__file__).parent / 'referencias' / 'pikachu_exacto.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    filas = m.ROWS
    img = Image.new('RGBA', (len(filas[0]), len(filas)), (0, 0, 0, 0))
    px = img.load()
    for y, f in enumerate(filas):
        for x, c in enumerate(f):
            if c != m.BACKGROUND:
                px[x, y] = tuple(m.PALETTE[c]) + (255,)
    return img.crop(img.getbbox())


BASE = _base_exacta()


def _fila_a_quitar(img, desde, hasta):
    """La fila del torso cuya eliminación menos cambia el dibujo (la más parecida a sus vecinas)."""
    a = np.array(img).astype(int)
    mejor, costo = desde, 10 ** 9
    for r in range(desde, hasta):
        c = np.abs(a[r - 1] - a[r + 1]).sum()
        if c < costo:
            mejor, costo = r, c
    return mejor


def cuadro(pose):
    w, h = BASE.size
    lienzo = Image.new('RGBA', (48, H), (0, 0, 0, 0))
    x = (48 - w) // 2
    if pose == 0:
        lienzo.paste(BASE, (x, H - h))
    else:
        r = _fila_a_quitar(BASE, int(h * 0.62), int(h * 0.82))
        arriba, abajo = BASE.crop((0, 0, w, r)), BASE.crop((0, r + 1, w, h))
        agachado = Image.new('RGBA', (w, h - 1), (0, 0, 0, 0))
        agachado.paste(arriba, (0, 0))
        agachado.paste(abajo, (0, r))
        lienzo.paste(agachado, (x, H - (h - 1)))
    return lienzo


# ---------------------------------------------------------------- animación (6 cuadros, a partir del dibujo exacto)
# Coordenadas sobre el dibujo de 45x44 (ver vista/pikachu_rejilla.png).
COLA = (0, 7, 16, 21)            # la paleta de la cola (el tallo de abajo queda quieto)
OREJA_DER = (36, 0, 44, 6)       # punta de la oreja derecha
OJOS = [((21, 11, 25, 16), [(21, 15), (22, 14), (23, 14), (24, 15)]),      # (caja del ojo, ojo cerrado)
        ((30, 12, 34, 17), [(30, 16), (31, 15), (32, 15), (33, 15), (34, 16)])]
CUADROS = 6


def _mover(a, caja, dx, dy):
    """Mueve los píxeles opacos de una caja (lo que sale del lienzo se pierde)."""
    b = a.copy()
    x0, y0, x1, y1 = caja
    reg = a[y0:y1 + 1, x0:x1 + 1].copy()
    m = reg[..., 3] > 0
    b[y0:y1 + 1, x0:x1 + 1][m] = 0
    for y, x in zip(*np.where(m)):
        ny, nx = y0 + y + dy, x0 + x + dx
        if 0 <= ny < b.shape[0] and 0 <= nx < b.shape[1]:
            b[ny, nx] = reg[y, x]
    return b


def _parpadeo(a):
    """Ojos cerrados: lo oscuro/blanco del ojo pasa al amarillo de la cara y se dibuja una rayita curva."""
    b = a.copy()
    cara = np.array([246, 230, 82, 255], np.uint8)          # amarillo de la cara (paleta exacta)
    negro = None
    for (x0, y0, x1, y1), linea in OJOS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                r, g, bb, al = (int(v) for v in b[y, x])
                lum = 0.3 * r + 0.59 * g + 0.11 * bb
                gris = abs(r - g) < 18 and abs(g - bb) < 18
                if al and (lum < 70 or (gris and lum < 130) or (r > 200 and g > 200 and bb > 200)):
                    if lum < 30 and negro is None:
                        negro = b[y, x].copy()
                    b[y, x] = cara
    negro = negro if negro is not None else np.array([6, 0, 0, 255], np.uint8)
    for (_, linea) in OJOS:
        for x, y in linea:
            b[y, x] = negro
    return b


def _a_img(a):
    return Image.fromarray(a, 'RGBA')


def _cuadro_anim(i):
    a = np.array(BASE)
    if i == 1:
        a = _mover(a, COLA, 0, -1)
    elif i == 2:
        a = _mover(a, OREJA_DER, 0, 1)
    elif i == 3:
        a = _mover(a, COLA, 0, 1)
    elif i == 4:
        a = _parpadeo(a)
    img = _a_img(a)
    lienzo = Image.new('RGBA', (48, H), (0, 0, 0, 0))
    x = (48 - img.width) // 2
    if i % 2 == 1:      # cuadros impares: rebote (se agacha 1 px quitando una fila del torso)
        w, h = img.size
        r = _fila_a_quitar(img, int(h * 0.62), int(h * 0.82))
        ag = Image.new('RGBA', (w, h - 1), (0, 0, 0, 0))
        ag.paste(img.crop((0, 0, w, r)), (0, 0))
        ag.paste(img.crop((0, r + 1, w, h)), (0, r))
        lienzo.paste(ag, (x, H - (h - 1)))
    else:
        lienzo.paste(img, (x, H - img.height))
    return lienzo


def hojas():
    """Hoja de 6 cuadros (288x44): de pie / rebote+cola arriba / oreja / rebote+cola abajo / parpadeo / rebote."""
    cuadros = [_cuadro_anim(i) for i in range(CUADROS)]
    out = Image.new('RGBA', (48 * CUADROS, H), (0, 0, 0, 0))
    for i, c in enumerate(cuadros):
        out.paste(c, (48 * i, 0))
    return out

if __name__ == '__main__':
    out = Path(__file__).parent / 'vista'
    out.mkdir(exist_ok=True)
    h = hojas()
    h.save(out / 'pikachu.png')
    vista([h], escala=9, fondo=(255, 255, 255), salida=out / 'pikachu_x9.png')
    print('ok', h.size)
