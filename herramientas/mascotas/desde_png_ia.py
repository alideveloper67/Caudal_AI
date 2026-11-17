# -*- coding: utf-8 -*-
"""Pasa una imagen pixel art hecha por IA (fondo transparente, cuadrícula irregular) a sprite para pokemon_exacto.py.

    python desde_png_ia.py <clave> <imagen.png> [--alto 96] [--colores 20]

Deja referencias/<clave>_original.png, v4/<clave>/recorte.png (alfa binario: fuera el brillo semitransparente)
y v4/<clave>/sprite_ilustracion.py (pixelize de la skill, camino B, sin erosión), más una vista comparativa.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

AQUI = Path(__file__).parent
SKILL = Path.home() / ".claude" / "skills" / "pixel-art-exact" / "scripts"
sys.path.insert(0, str(SKILL))
import spritelib as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clave")
    ap.add_argument("imagen")
    ap.add_argument("--alto", type=int, default=96)
    ap.add_argument("--ancho", type=int, default=92)
    ap.add_argument("--colores", type=int, default=20)
    ap.add_argument("--lineas", action="store_true",
                    help="los grises intermedios sin color (líneas negras finas promediadas con blanco) vuelven a negro")
    ap.add_argument("--engrosar", type=int, default=0,
                    help="px que se ensancha lo casi negro ANTES de reducir, para que las líneas finas no se pierdan")
    ap.add_argument("--fondo-negro", type=int, default=0,
                    help="la imagen no trae transparencia sino fondo negro: se quita el negro que toca el borde y se "
                         "devuelve un anillo de N px alrededor de la figura (su contorno negro)")
    a = ap.parse_args()
    d = AQUI / "v4" / a.clave
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.imagen, AQUI / "referencias" / f"{a.clave}_original.png")
    im = np.array(Image.open(a.imagen).convert("RGBA"))
    im[..., 3] = np.where(im[..., 3] >= 160, 255, 0)
    if a.fondo_negro:
        from collections import deque
        from PIL import ImageFilter
        lum = 0.3 * im[..., 0] + 0.59 * im[..., 1] + 0.11 * im[..., 2]
        negro = lum < 14
        h, w = negro.shape
        fondo = np.zeros((h, w), bool)
        q = deque([(y, x) for x in range(w) for y in (0, h - 1)] + [(y, x) for y in range(h) for x in (0, w - 1)])
        while q:
            y, x = q.popleft()
            if fondo[y, x] or not negro[y, x]:
                continue
            fondo[y, x] = True
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not fondo[ny, nx] and negro[ny, nx]:
                    q.append((ny, nx))
        figura = Image.fromarray((~fondo).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * a.fondo_negro + 1))
        im[..., 3] = np.where(np.array(figura) > 127, 255, 0)
    if a.engrosar:
        from PIL import ImageFilter
        lum = 0.3 * im[..., 0] + 0.59 * im[..., 1] + 0.11 * im[..., 2]
        negro = Image.fromarray(((lum < 55) & (im[..., 3] > 0)).astype(np.uint8) * 255)
        ancho = np.array(negro.filter(ImageFilter.MaxFilter(2 * a.engrosar + 1))) > 127
        dentro = np.array(Image.fromarray(im[..., 3]).filter(ImageFilter.MinFilter(2 * a.engrosar + 1))) > 0
        im[ancho & dentro, :3] = (20, 18, 24)
    r = Image.fromarray(im)
    r = r.crop(r.getbbox())
    r.save(d / "recorte.png")
    subprocess.run([sys.executable, str(SKILL / "pixelize.py"), str(d / "recorte.png"), "-o", str(d / "sprite_ilustracion.py"),
                    "--size", f"{a.ancho}x{a.alto}", "--colors", str(a.colores), "--outline", "none", "--erode", "0"],
                   check=True)
    sp = S.load(str(d / "sprite_ilustracion.py"))
    if a.lineas:
        pal = dict(sp["palette"])
        for k, (r_, g_, b_) in pal.items():
            lum = 0.3 * r_ + 0.59 * g_ + 0.11 * b_
            if k != sp["bg"] and max(r_, g_, b_) - min(r_, g_, b_) < 40 and 60 < lum < 185:
                pal[k] = (24, 22, 28)
        S.save(str(d / "sprite_ilustracion.py"), sp["rows"], pal, bg=sp["bg"])
        sp = S.load(str(d / "sprite_ilustracion.py"))
    px = S.to_image(sp["rows"], sp["palette"], sp["bg"])
    orig = r.resize((int(r.width * 400 / r.height), 400), Image.LANCZOS)
    px4 = px.resize((px.width * 4, px.height * 4), Image.NEAREST)
    v = Image.new("RGBA", (orig.width + px4.width + 30, max(400, px4.height) + 20), (30, 34, 46, 255))
    v.alpha_composite(orig, (10, 10))
    v.alpha_composite(px4, (orig.width + 20, 10))
    v.save(AQUI / "vista" / f"{a.clave}_prueba.png")
    print(a.clave, "->", px.size)


if __name__ == "__main__":
    main()
