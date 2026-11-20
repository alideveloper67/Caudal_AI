# -*- coding: utf-8 -*-
"""Pokémon extraídos EXACTOS (verify_sprite: EXACTO ✔) de las imágenes pixel art que pasó la persona
(referencias/<clave>.png -> v4/<clave>/exacto.py).

    python pokemon_exacto.py [clave ...]      (sin claves: todos)

Hoja de 4 cuadros con densidad 2 (cada píxel del dibujo = 2x2):
  normal · agachado · normal con detalle (parpadeo o llama) · estirado con detalle.
"""
import shutil
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

# clave: tamaño del cuadro en pantalla y detalle animado (sobre el dibujo recortado)
POKEMON = {
    "pikachu": {"cuadro": (48, 50)},
    "charmander": {"cuadro": (48, 44), "llama": True},
    "bulbasaur": {"cuadro": (48, 44)},
    "squirtle": {"cuadro": (48, 44)},
    # imagen pixel art de IA con cuadrícula irregular: no se puede extraer exacto, se pixeliza (camino B) ya a 2x
    "kuromi": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "hellokitty": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "doraemon": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "purin": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "cinnamoroll": {"cuadro": (64, 50), "pixelizado": "sprite_ilustracion.py"},
    "mymelody": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "snoopy": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "totoro": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "nyan": {"cuadro": (64, 40), "pixelizado": "sprite_ilustracion.py"},
    "olaf": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "kirby": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "gato_negro": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "capibara": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "pochacco": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "nailong": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "caniche": {"cuadro": (64, 50), "pixelizado": "sprite_ilustracion.py"},
    # imágenes de IA sin transparencia: el recorte lo hace personajes_nov.py
    "messi": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "wos": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "nightwing": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "goku_ultra": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "goku_blue": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "wanda": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "loki": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "jake": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "finn": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "marceline": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "pan_canela": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "rigby": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "mordecai": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "steven": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "perla": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "lapislazuli": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "jaspe": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "garnet": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "peridot": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "amatista": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "leon": {"cuadro": (64, 50), "pixelizado": "sprite_ilustracion.py"},
    "richard": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
    "gumball": {"cuadro": (64, 50), "pixelizado": "sprite_ilustracion.py"},
    "darwin": {"cuadro": (48, 50), "pixelizado": "sprite_ilustracion.py"},
}


def base(clave):
    sp = S.load(str(AQUI / "v4" / clave / "exacto.py"))
    pal = dict(sp["palette"])
    rows = [list(r) for r in S.crop_rows(sp["rows"], sp["bg"])]
    h, w = len(rows), len(rows[0])
    # el fondo es blanco: lo blanco que NO se alcanza desde fuera es blanco del personaje (brillo de ojos)
    fuera = set()
    q = deque((y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and rows[y][x] == ".")
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


def parpadeo(rows, caja, piel, linea):
    r = [list(f) for f in rows]
    x0, y0, x1, y1 = caja
    for y in range(y0, y1):
        for x in range(x0, x1):
            if r[y][x] not in ".":
                r[y][x] = "C" if y == linea else piel
    return r


def llama_charmander(rows):
    """Amarillo y ámbar intercambiados en la llama y la punta un poco más baja."""
    r = [list(f) for f in rows]
    for y in range(9, 23):
        for x in range(29, 38):
            r[y][x] = {"H": "I", "I": "H"}.get(r[y][x], r[y][x])
    for y, x in ((10, 32), (11, 33)):
        r[y][x] = "."
    r[11][32] = "G"
    if r[12][33] == "H":
        r[12][33] = "G"
    return r


def x2(rows):
    return ["".join(c * 2 for c in f) for f in rows for _ in range(2)]


def estela_llamas(destino):
    pal = {"G": (230, 57, 0), "I": (246, 164, 0), "H": (255, 213, 8), "E": (255, 240, 170)}
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
    im.save(destino)


def construir(clave):
    cfg = POKEMON[clave]
    d = AQUI / "v4" / clave
    fw, fh = cfg["cuadro"][0] * I.DENSIDAD, cfg["cuadro"][1] * I.DENSIDAD
    if cfg.get("pixelizado"):
        shutil.copy(d / cfg["pixelizado"], d / "sprite.py")
        I.rebote4(d / "sprite.py", d, fw, fh)
        print(clave, "hoja", Image.open(d / "hoja.png").size)
        return
    rows, pal = base(clave)
    if "parpadeo" in cfg:
        otro = parpadeo(rows, **cfg["parpadeo"])
    elif cfg.get("llama"):
        otro = llama_charmander(rows)
    else:
        otro = rows
    fw, fh = cfg["cuadro"][0] * I.DENSIDAD, cfg["cuadro"][1] * I.DENSIDAD
    S.save(str(d / "sprite.py"), x2(rows), pal, bg=".")
    S.save(str(d / "sprite_detalle.py"), x2(otro), pal, bg=".")
    I.rebote4(d / "sprite.py", d, fw, fh)
    a = Image.open(d / "hoja.png")
    I.rebote4(d / "sprite_detalle.py", d, fw, fh)
    b = Image.open(d / "hoja.png")
    hoja = Image.new("RGBA", a.size, (0, 0, 0, 0))
    for i, fuente in enumerate((a, a, b, b)):
        hoja.paste(fuente.crop((i * fw, 0, (i + 1) * fw, fh)), (i * fw, 0))
    hoja.save(d / "hoja.png")
    if cfg.get("llama"):
        estela_llamas(d / "estela.png")
    print(clave, "hoja", hoja.size)


if __name__ == "__main__":
    for c in sys.argv[1:] or POKEMON:
        construir(c)
