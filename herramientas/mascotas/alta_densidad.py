# -*- coding: utf-8 -*-
"""Rehace en alta definición las mascotas y fondos de los personajes de noviembre (Messi, WOS, Mordecai…).

Las primeras versiones se sacaron de las imágenes de la persona reducidas a 96 px y cuantizadas: se veían
ruidosas, con orillas sucias del fondo y sin contorno, «como recortadas y pegadas». Aquí se parte del mismo
recorte en grande (v4/<clave>/recorte.png), sin rediseñar nada:

  1. se limpia la orilla (fuera los píxeles semitransparentes y los restos del fondo pegados al borde),
  2. se reduce con un filtro de calidad a 4 píxeles de hoja por píxel de pantalla (densidad 4: el doble de
     detalle que antes, el mismo tamaño en pantalla),
  3. se le pone un contorno oscuro limpio por fuera, como las mascotas de siempre,
  4. se arma la hoja de 4 cuadros (normal / agachado / normal / estirado) con los pies abajo.

El fondo (descargador/fondos/<clave>.png) es el mismo dibujo, a 192 px de alto.

    python alta_densidad.py [clave ...]          (sin claves: los 24)
    python alta_densidad.py --vista              (además, una hoja de comparación en vista/)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as nd

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
MASCOTAS = [RAIZ / "escritorio" / "descargador" / "mascotas", RAIZ / "app" / "assets" / "mascotas"]
FONDOS = [RAIZ / "escritorio" / "descargador" / "fondos", RAIZ / "app" / "assets" / "fondos"]

CLAVES = ["messi", "wos", "nightwing", "goku_ultra", "goku_blue", "wanda", "loki", "finn", "jake", "marceline",
          "pan_canela", "mordecai", "rigby", "steven", "perla", "lapislazuli", "jaspe", "garnet", "peridot",
          "amatista", "gumball", "darwin", "richard", "leon"]

DENSIDAD = 4            # píxeles de hoja por píxel de pantalla
CONTORNO = 3            # grosor del contorno, en píxeles de hoja (¾ de píxel de pantalla)
ALTO_FONDO = 192        # alto del dibujo del fondo


def limpiar(im):
    """Alfa duro, sin restos del fondo pegados a la orilla ni islas sueltas."""
    a = np.array(im.convert("RGBA")).astype(np.float32)
    alfa = a[..., 3] > 140
    alfa = nd.binary_opening(alfa, iterations=2)                 # hilos y motas del fondo
    etiquetas, n = nd.label(alfa)
    if n > 1:                                                     # solo las piezas grandes (la figura)
        tam = nd.sum(alfa, etiquetas, range(1, n + 1))
        grande = tam.max()
        alfa = np.isin(etiquetas, [i + 1 for i, t in enumerate(tam) if t >= grande * 0.02])
    a[..., 3] = np.where(alfa, 255, 0)
    # el color de la orilla: lo de dentro, sin el halo oscuro/claro del fondo original
    borde = alfa & ~nd.binary_erosion(alfa, iterations=2)
    dentro = nd.binary_erosion(alfa, iterations=2)
    if dentro.any():
        _, (iy, ix) = nd.distance_transform_edt(~dentro, return_indices=True)
        for c in range(3):
            canal = a[..., c]
            canal[borde] = canal[iy[borde], ix[borde]]
    out = Image.fromarray(a.astype(np.uint8), "RGBA")
    return out.crop(out.getbbox())


def reducir(im, alto):
    """Reducción de calidad con alfa premultiplicado (sin halos), alfa duro y un toque de nitidez."""
    ancho = max(1, round(im.width * alto / im.height))
    a = np.array(im).astype(np.float32) / 255
    a[..., :3] *= a[..., 3:4]
    pre = Image.fromarray((a * 255).astype(np.uint8), "RGBA")
    chico = np.array(pre.resize((ancho, alto), Image.LANCZOS)).astype(np.float32) / 255
    al = chico[..., 3:4]
    rgb = np.where(al > 0.01, chico[..., :3] / np.maximum(al, 0.01), 0)
    rgb = np.clip(rgb, 0, 1)
    solido = (al[..., 0] > 0.5)
    out = np.dstack([rgb * 255, np.where(solido, 255, 0)]).astype(np.uint8)
    im2 = Image.fromarray(out, "RGBA")
    rgb_n = im2.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
    final = Image.merge("RGBA", (*rgb_n.split(), im2.getchannel("A")))
    return final


def contornear(im, grosor, color):
    """Contorno oscuro por fuera de la silueta (no come el dibujo)."""
    a = np.array(im)
    alfa = a[..., 3] > 0
    pad = grosor + 1
    alfa_p = np.pad(alfa, pad)
    rgba_p = np.pad(a, ((pad, pad), (pad, pad), (0, 0)))
    disco = np.hypot(*np.mgrid[-grosor:grosor + 1, -grosor:grosor + 1]) <= grosor + 0.35
    fuera = nd.binary_dilation(alfa_p, structure=disco) & ~alfa_p
    rgba_p[fuera] = (*color, 255)
    out = Image.fromarray(rgba_p, "RGBA")
    return out.crop(out.getbbox())


def color_contorno(im):
    """Un oscuro con el tono del personaje (como el contorno de las mascotas dibujadas a mano)."""
    a = np.array(im).reshape(-1, 4)
    a = a[a[:, 3] > 0][:, :3].astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114])
    oscuros = a[lum <= np.percentile(lum, 12)]
    base = oscuros.mean(axis=0) if len(oscuros) else np.array([30, 26, 40])
    base = base * 0.45 + np.array([18, 14, 26]) * 0.55
    return tuple(int(v) for v in np.clip(base, 0, 70))


def cintura(a):
    """La fila donde menos cambia el dibujo (de 55 % a 85 % del alto): ahí se agacha o se estira."""
    h = a.shape[0]
    mejor, costo = int(h * 0.62), None
    for r in range(max(1, int(h * 0.55)), min(h - 1, int(h * 0.85))):
        c = np.abs(a[r - 1].astype(np.int32) - a[r + 1].astype(np.int32)).sum()
        if costo is None or c < costo:
            mejor, costo = r, c
    return mejor


def hoja(figura, fw, fh, k):
    a = np.array(figura)
    r = cintura(a)
    agachado = np.concatenate([a[:r], a[r + k:]])
    estirado = np.concatenate([a[:r]] + [a[r:r + 1]] * k + [a[r:]]) if a.shape[0] + k <= fh else a
    cuadros = [a, agachado, a, estirado]
    out = Image.new("RGBA", (fw * 4, fh), (0, 0, 0, 0))
    for i, c in enumerate(cuadros):
        im = Image.fromarray(c, "RGBA")
        if im.width > fw or im.height > fh:
            raise SystemExit(f"no cabe: {im.size} en {fw}x{fh}")
        out.paste(im, (i * fw + (fw - im.width) // 2, fh - im.height))
    return out


def construir(clave, catalogo):
    datos = catalogo[clave]
    vieja = Image.open(MASCOTAS[0] / f"{clave}.png").convert("RGBA")
    fw0 = vieja.width // datos.get("cuadros", 4)
    caja0 = vieja.crop((0, 0, fw0, vieja.height)).getbbox()
    alto0 = caja0[3] - caja0[1]                    # alto del dibujo en la hoja vieja (densidad 2)
    d0 = datos.get("densidad", 2)
    fw, fh = datos["ancho"] * DENSIDAD, datos["alto"] * DENSIDAD
    limpio = limpiar(Image.open(AQUI / "v4" / clave / "recorte.png"))
    color = color_contorno(limpio)
    # el mismo alto en pantalla que antes, con el estirado (k filas) cabiendo en el cuadro
    alto = int(alto0 * DENSIDAD / d0) - 2 * CONTORNO
    while True:
        fig = contornear(reducir(limpio, alto), CONTORNO, color)
        if fig.width <= fw and fig.height + DENSIDAD <= fh:
            break
        alto -= 2
    h = hoja(fig, fw, fh, DENSIDAD)
    fondo = contornear(reducir(limpio, ALTO_FONDO - 2 * CONTORNO), CONTORNO, color)
    return h, fondo


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    claves = args or CLAVES
    catalogos = []
    for carpeta in MASCOTAS:
        ruta = carpeta / "catalogo.json"
        catalogos.append((ruta, json.loads(ruta.read_text(encoding="utf-8"))))
    por_clave = {m["clave"]: m for m in catalogos[0][1]}
    vistas = []
    for c in claves:
        h, fondo = construir(c, por_clave)
        for carpeta in MASCOTAS:
            h.save(carpeta / f"{c}.png", optimize=True)
        for carpeta in FONDOS:
            fondo.save(carpeta / f"{c}.png", optimize=True)
        for _, cat in catalogos:
            for m in cat:
                if m["clave"] == c:
                    m["densidad"] = DENSIDAD
        vistas.append((c, h, fondo))
        print(c, "hoja", h.size, "fondo", fondo.size)
    for ruta, cat in catalogos:
        ruta.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if "--vista" in sys.argv:
        ancho = max(h.width for _, h, _ in vistas) + 260
        alto = sum(max(h.height, f.height) + 12 for _, h, f in vistas)
        v = Image.new("RGBA", (ancho, alto), (40, 40, 60, 255))
        y = 0
        for _, h, f in vistas:
            v.alpha_composite(h, (0, y))
            v.alpha_composite(f, (h.width + 20, y))
            y += max(h.height, f.height) + 12
        (AQUI / "vista").mkdir(exist_ok=True)
        v.save(AQUI / "vista" / "alta_densidad.png")


if __name__ == "__main__":
    main()
