# -*- coding: utf-8 -*-
"""Charmander: extraído EXACTO (verify_sprite: EXACTO ✔) de la imagen que pasó la persona (referencias/charmander.png,
pixel art 52x52 a 7,385 px por celda). Fuente: v4/charmander/exacto.py.

Animación de 4 cuadros (densidad 2: cada píxel del dibujo = 2x2 en la hoja de 96x88):
  normal · agachado · normal con la llama titilando · estirado con la llama titilando.
Estela: llamitas de su misma paleta.
"""
import sys
from collections import deque
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).parent
SKILL = Path.home() / ".claude" / "skills" / "pixel-art-exact" / "scripts"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(AQUI))
import spritelib as S  # noqa: E402
import importar_hoja as I  # noqa: E402

D = AQUI / "v4" / "charmander"
LLAMA = (29, 9, 38, 23)  # x0, y0, x1, y1 (en el dibujo recortado de 38x42)


def base():
    sp = S.load(str(D / "exacto.py"))
    pal = dict(sp["palette"])
    rows = [list(r) for r in S.crop_rows(sp["rows"], sp["bg"])]
    h, w = len(rows), len(rows[0])
    # el fondo es blanco: lo blanco que NO se alcanza desde fuera es el brillo del ojo -> color propio
    fuera, q = set(), deque((y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and rows[y][x] == ".")
    while q:
        y, x = q.popleft()
        if (y, x) in fuera:
            continue
        fuera.add((y, x))
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and rows[ny][nx] == "." and (ny, nx) not in fuera:
                q.append((ny, nx))
    pal["W"] = (255, 255, 255)
    for y in range(h):
        for x in range(w):
            if rows[y][x] == "." and (y, x) not in fuera:
                rows[y][x] = "W"
    return rows, pal


def llama_titila(rows):
    """Amarillo y ámbar intercambiados en la llama y la punta un poco más baja."""
    r = [list(f) for f in rows]
    x0, y0, x1, y1 = LLAMA
    for y in range(y0, y1):
        for x in range(x0, x1):
            r[y][x] = {"H": "I", "I": "H"}.get(r[y][x], r[y][x])
    # la punta (filas 10-11) baja un píxel: se borra la de arriba y su lado queda con el contorno rojo
    for y, x in ((10, 32), (11, 33)):
        r[y][x] = "."
    r[11][32] = "G"
    r[12][33] = "G" if r[12][33] == "H" else r[12][33]
    return r


def x2(rows):
    return ["".join(c * 2 for c in f) for f in rows for _ in range(2)]


def estela():
    pal = {".": (0, 0, 0), "G": (230, 57, 0), "I": (246, 164, 0), "H": (255, 213, 8), "E": (255, 240, 170)}
    a = ["....G......", "...GH......", "...GHG.....", "..GHHG.G...", "..GHIHGHG..", ".GHIIHHHG..",
         ".GHIEIIHG..", ".GHIEEIHG..", "..GHIIHG...", "...GGGG....", "..........."]
    b = [".....G.....", "....GHG....", "....GHG....", "...GHIHG...", "..GHIIIHG..", "..GHIEIHG..",
         "..GHIEIHG..", "..GHIIIHG..", "...GHHHG...", "....GGG....", "..........."]
    im = Image.new("RGBA", (22, 11), (0, 0, 0, 0))
    for k, filas in enumerate((a, b)):
        for y, f in enumerate(filas):
            for x, c in enumerate(f):
                if c != ".":
                    im.putpixel((k * 11 + x, y), (*pal[c], 255))
    im.save(D / "estela.png")


def construir():
    rows, pal = base()
    S.save(str(D / "sprite.py"), x2(rows), pal, bg=".")
    S.save(str(D / "sprite_llama.py"), x2(llama_titila(rows)), pal, bg=".")
    I.rebote4(D / "sprite.py", D)
    a = Image.open(D / "hoja.png")
    I.rebote4(D / "sprite_llama.py", D)
    b = Image.open(D / "hoja.png")
    hoja = Image.new("RGBA", a.size, (0, 0, 0, 0))
    fw = I.FW
    for i, fuente in enumerate((a, a, b, b)):
        hoja.paste(fuente.crop((i * fw, 0, (i + 1) * fw, I.FH)), (i * fw, 0))
    hoja.save(D / "hoja.png")
    estela()
    print("charmander: hoja", hoja.size, "y estela listas")


def hojas():
    return Image.open(D / "hoja.png").convert("RGBA")


if __name__ == "__main__":
    construir()
