# -*- coding: utf-8 -*-
"""Importa una hoja de personajes (ilustraciones con contorno negro sobre fondo oscuro con halos, en cuadrícula) y
convierte cada uno en mascota de Caudal con la skill pixel-art-exact (camino B: pixelize).

    python importar_hoja.py hoja.png --cols 4 --filas 6 --claves zorro_aviador,conejo_mago,... [--solo zorro_aviador,robot]

Por personaje deja en v4/<clave>/: recorte.png (con fondo transparente), sprite.py + sprite.png (pixelizado),
hoja.png (4 cuadros de 96x88 = 48x44 en pantalla con densidad 2: normal, agachado, normal, estirado = rebote elástico) y hoja_vista.png.
"""
import argparse
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

AQUI = Path(__file__).parent
SKILL = Path.home() / ".claude" / "skills" / "pixel-art-exact" / "scripts"
sys.path.insert(0, str(SKILL))
import spritelib as S  # noqa: E402

# tamaño de un cuadro en pantalla; con densidad 2 la hoja trae el doble de píxeles (96x88) en ese mismo espacio
FW0, FH0 = 48, 44
DENSIDAD = 2
FW, FH = FW0 * DENSIDAD, FH0 * DENSIDAD


def recortar(celda, umbral_contorno=40, cierre=2, claro=140):
    """Fondo = lo que se alcanza desde el borde de la celda SIN cruzar:
      · el contorno oscuro, ensanchado `cierre` px para tapar los huecos finos (cuernos, alas, antenas),
      · ni los colores claros del personaje (el fondo de estas hojas es oscuro con halos: luminancia < `claro`).
    Después se quita el anillo de halo que queda pegado por fuera y se conservan solo las manchas grandes."""
    from PIL import ImageFilter
    a = np.array(celda.convert("RGB")).astype(int)
    lum = 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]
    oscuro = lum < umbral_contorno
    m = Image.fromarray((oscuro * 255).astype(np.uint8))
    muro = np.array(m.filter(ImageFilter.MaxFilter(2 * cierre + 1))) > 127
    muro |= lum >= claro
    h, w = lum.shape
    fondo = np.zeros((h, w), bool)
    cola = deque([(y, x) for x in range(w) for y in (0, h - 1)] + [(y, x) for y in range(h) for x in (0, w - 1)])
    while cola:
        y, x = cola.popleft()
        if fondo[y, x] or muro[y, x]:
            continue
        fondo[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not fondo[ny, nx]:
                cola.append((ny, nx))
    figura = ~fondo
    # anillo de halo: píxeles no oscuros pegados al fondo (los dejó el ensanche del contorno) -> fuera
    cerca = np.array(Image.fromarray((fondo * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * cierre + 3))) > 127
    figura &= ~(cerca & ~oscuro & (lum < claro))
    etiqueta = -np.ones((h, w), int)
    tam = []
    for y in range(h):
        for x in range(w):
            if figura[y, x] and etiqueta[y, x] < 0:
                k = len(tam)
                q = deque([(y, x)])
                etiqueta[y, x] = k
                n = 0
                while q:
                    cy, cx = q.popleft()
                    n += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and figura[ny, nx] and etiqueta[ny, nx] < 0:
                            etiqueta[ny, nx] = k
                            q.append((ny, nx))
                tam.append(n)
    if not tam:
        return None
    mayor = int(np.argmax(tam))
    # manchas que tocan el borde de la celda = pedazos del vecino o del fondo oscuro de las esquinas: fuera
    borde = set(etiqueta[0, :].tolist()) | set(etiqueta[-1, :].tolist()) | set(etiqueta[:, 0].tolist()) | set(etiqueta[:, -1].tolist())
    validas = {k for k, n in enumerate(tam) if k == mayor or (n >= 0.02 * tam[mayor] and k not in borde)}
    mascara = np.isin(etiqueta, list(validas))
    # el contorno negro de verdad es fino: lo oscuro que queda lejos del color del personaje es fondo oscuro pegado
    color = mascara & ~oscuro
    cerca_color = np.array(Image.fromarray((color * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(19))) > 127
    mascara &= ~oscuro | cerca_color
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = a
    rgba[..., 3] = np.where(mascara, 255, 0)
    img = Image.fromarray(rgba, "RGBA")
    return img.crop(img.getbbox())


def rebote4(sprite_py, destino, fw=None, fh=None):
    """Hoja de 4 cuadros: normal / agachado / normal / estirado (DENSIDAD filas menos / más). Pies siempre abajo."""
    FW_, FH_ = fw or FW, fh or FH
    sp = S.load(str(sprite_py))
    rows = S.crop_rows(sp["rows"], sp["bg"])
    h = len(rows)
    a = np.array([[ord(c) for c in r] for r in rows])
    mejor, costo = int(h * 0.62), 10 ** 9
    for r in range(max(1, int(h * 0.55)), min(h - 1, int(h * 0.85))):
        c = np.abs(a[r - 1] - a[r + 1]).sum()
        if c < costo:
            mejor, costo = r, c
    k = DENSIDAD
    agachado = rows[:mejor] + rows[mejor + k:]
    estirado = rows[:mejor] + [rows[mejor]] * k + rows[mejor:] if h + k <= FH_ else rows
    cuadros = [rows, agachado, rows, estirado]
    hoja = Image.new("RGBA", (FW_ * 4, FH_), (0, 0, 0, 0))
    for i, rr in enumerate(cuadros):
        im = S.to_image(rr, sp["palette"], sp["bg"])
        if im.width > FW_ or im.height > FH_:
            raise SystemExit(f"{sprite_py}: el dibujo mide {im.size} y no cabe en {FW_}x{FH_}")
        hoja.paste(im, (i * FW_ + (FW_ - im.width) // 2, FH_ - im.height))
    hoja.save(destino / "hoja.png")
    esc = 8 // DENSIDAD
    v = Image.new("RGBA", (hoja.width * esc + 20, hoja.height * esc * 2 + 30), (30, 34, 46, 255))
    v.alpha_composite(hoja.resize((hoja.width * esc, hoja.height * esc), Image.NEAREST), (10, 10))
    claro = Image.new("RGBA", (hoja.width * esc, hoja.height * esc), (255, 255, 255, 255))
    claro.alpha_composite(hoja.resize((hoja.width * esc, hoja.height * esc), Image.NEAREST))
    v.alpha_composite(claro, (10, 20 + hoja.height * esc))
    v.save(destino / "hoja_vista.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hoja")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--filas", type=int, default=6)
    ap.add_argument("--claves", required=True, help="claves en orden de lectura (izquierda a derecha, arriba a abajo)")
    ap.add_argument("--solo", help="procesar solo estas claves")
    ap.add_argument("--size", default=f"{46 * DENSIDAD}x{42 * DENSIDAD}")
    ap.add_argument("--colors", type=int, default=24)
    ap.add_argument("--erode", type=float, default=1)
    a = ap.parse_args()
    im = Image.open(a.hoja).convert("RGB")
    cw, ch = im.width // a.cols, im.height // a.filas
    claves = [c.strip() for c in a.claves.split(",") if c.strip()]
    solo = set(a.solo.split(",")) if a.solo else None
    for i, clave in enumerate(claves):
        if solo and clave not in solo:
            continue
        fila, col = divmod(i, a.cols)
        celda = im.crop((col * cw, fila * ch, (col + 1) * cw, (fila + 1) * ch))
        rec = recortar(celda)
        if rec is None:
            print("sin dibujo en la celda", i, clave)
            continue
        dst = AQUI / "v4" / clave
        dst.mkdir(parents=True, exist_ok=True)
        rec.save(dst / "recorte.png")
        r = subprocess.run([sys.executable, str(SKILL / "pixelize.py"), str(dst / "recorte.png"), "-o", str(dst / "sprite.py"),
                            "--size", a.size, "--colors", str(a.colors), "--outline", "none", "--erode", str(a.erode),
                            "--preview", str(dst / "sprite.png")], capture_output=True, text=True)
        if r.returncode:
            print("FALLA", clave, r.stderr[-400:])
            continue
        rebote4(dst / "sprite.py", dst)
        print(clave, "->", (r.stdout.splitlines() or [""])[0])


if __name__ == "__main__":
    main()
