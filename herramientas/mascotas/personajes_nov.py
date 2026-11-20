# -*- coding: utf-8 -*-
"""Personajes de noviembre (Messi, WOS, Nightwing, Goku UI, Goku Blue, Wanda, Loki, Jake, Finn, Marceline):
imágenes pixel art de IA SIN transparencia -> recorte de la figura -> sprite (skill pixel-art-exact, camino B)
-> hoja de 4 cuadros con pokemon_exacto.py.

    python personajes_nov.py [clave ...]        (sin claves: todos)

Cada personaje dice cómo se reconoce su fondo (negro, un color liso, azul degradado…), qué se quita aparte
(auras, círculos mágicos: con un polígono que envuelve a la figura) y qué parte se usa (las de medio cuerpo se
encuadran del pecho para arriba). Deja v4/<clave>/recorte.png, v4/<clave>/sprite_ilustracion.py, la hoja y
vista/<clave>_recorte.png (recorte sobre rosa, para ver restos del fondo).
"""
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

AQUI = Path(__file__).parent
SKILL = Path.home() / ".claude" / "skills" / "pixel-art-exact" / "scripts"
DESCARGAS = Path.home() / "Downloads"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(AQUI))

P = {
    "messi": {"img": "WhatsApp Image 2026-11-19 at 7.49.21 PM.jpeg", "fondo": "negro", "engrosar": 3},
    "wos": {"img": "WhatsApp Image 2026-11-19 at 7.52.24 PM.jpeg", "fondo": "azul", "huecos": 2000,
            "caja": (0, 0, 1254, 900)},
    "nightwing": {"img": "WhatsApp Image 2026-11-19 at 7.54.14 PM.jpeg", "fondo": "color", "caja": (0, 0, 1097, 1180)},
    "goku_ultra": {"img": "WhatsApp Image 2026-11-19 at 8.00.17 PM.jpeg", "fondo": "negro",
                   "aura": "(b > r + 6) & ((L < 75) | (L > 110))", "aura_desde_y": 380,
                   "abrir": 12, "abrir_desde_y": 380, "engrosar": 6,
                   "engrosar_luz": 70, "engrosar_caja": (510, 220, 690, 370)},
    "goku_blue": {"img": "WhatsApp Image 2026-11-19 at 8.00.17 PM (1).jpeg", "fondo": "negro",
                  "aura": "(b > r + 6) & ((L < 75) | (g > 100))", "aura_desde_y": 430, "anillo": 8,
                  "abrir": 12, "abrir_desde_y": 430, "engrosar": 5,
                  "engrosar_luz": 70, "engrosar_caja": (410, 280, 610, 430)},
    # Wanda: la magia (círculos, rayos y espirales) toca la figura; se queda solo lo de dentro del polígono que
    # sigue su silueta (mano alzada, brazo, pelo, torso hasta la cintura y el otro brazo), en px de la imagen
    "wanda": {"img": "WhatsApp Image 2026-11-19 at 8.05.03 PM.jpeg", "fondo": "negro", "engrosar": 3, "huecos": 200,
              "poligono": [[(15, 150), (60, 110), (120, 75), (150, 90), (160, 180), (200, 240), (230, 300),
                            (260, 360), (230, 330), (215, 320), (250, 250), (300, 200), (400, 190), (455, 150),
                            (465, 92), (520, 100), (600, 82), (660, 95), (720, 92), (740, 200), (800, 250),
                            (860, 330), (868, 420), (842, 520), (812, 600), (850, 700), (895, 790), (940, 880), (1000, 845),
                            (1060, 850), (1100, 880), (1095, 940), (1040, 1000), (960, 1000), (905, 985),
                            (840, 900), (780, 800), (735, 700), (705, 640), (650, 700), (632, 800), (640, 900),
                            (680, 1000), (340, 1000), (385, 940), (390, 800), (378, 700), (370, 600), (378, 530),
                            (330, 505), (250, 490), (150, 450), (90, 400), (75, 280), (20, 215)]]},
    # Loki: el círculo, los rayos y las espirales doradas tocan la figura; polígono con los cuernos del casco,
    # el pelo, los hombros y los brazos cruzados (de la cintura para arriba)
    "loki": {"img": "WhatsApp Image 2026-11-19 at 8.08.41 PM.jpeg", "fondo": "negro", "engrosar": 5, "huecos": 200,
             "engrosar_caja": (470, 380, 660, 560), "poligono": [[(470, 290), (430, 240), (390, 180), (370, 120), (380, 65), (425, 32), (440, 25),
                           (395, 18), (345, 35), (318, 90), (320, 160), (345, 220), (390, 275), (440, 320),
                           (440, 340), (400, 360), (360, 420), (345, 500), (350, 570), (290, 590), (200, 600),
                           (175, 690), (185, 760), (210, 800), (230, 850), (250, 900), (280, 950), (330, 1000),
                           (380, 1050), (850, 1050), (930, 980), (920, 900), (900, 820), (890, 740), (880, 690),
                           (885, 650), (880, 640), (800, 610), (750, 590), (742, 560), (745, 480), (730, 420),
                           (705, 360), (680, 330), (740, 270), (790, 200), (810, 120), (790, 50), (740, 20),
                           (705, 25), (700, 30), (730, 45), (765, 95), (770, 150), (745, 210), (700, 260),
                           (660, 290), (640, 230), (600, 205), (540, 200), (490, 215), (470, 250)]]},
    "jake": {"img": "WhatsApp Image 2026-11-19 at 8.10.29 PM (2).jpeg", "fondo": "color", "tol": 60, "huecos": 400},
    "finn": {"img": "WhatsApp Image 2026-11-19 at 8.11.23 PM.jpeg", "fondo": "negro", "engrosar": 3},
    "marceline": {"img": "WhatsApp Image 2026-11-19 at 8.12.41 PM.jpeg", "fondo": "negro", "umbral": 6, "engrosar": 9, "engrosar_max": 1500,
                  "engrosar_caja": (420, 200, 660, 400)},
    "pan_canela": {"img": "WhatsApp Image 2026-11-19 at 8.15.06 PM.jpeg", "fondo": "negro", "engrosar": 2},
    # Un Show Más / Steven Universe: fondo negro y un halo de color de 1-2 px por fuera del contorno negro (es parte
    # del dibujo): se deja solo 1 px de negro por fuera del halo
    "rigby": {"img": "WhatsApp Image 2026-11-19 at 8.23.26 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3,
              "huecos": 150},
    "steven": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (1).jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3},
    "perla": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (3).jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3},
    "lapislazuli": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (4).jpeg", "fondo": "negro", "contorno": 1,
                    "engrosar": 3,
                    # los chorros de agua sueltos (derecha y abajo a la izquierda) tocan su halo: fuera
                    "quitar": [[(680, 455), (860, 455), (860, 720), (800, 720), (730, 700), (700, 620), (680, 540)],
                               [(130, 850), (300, 850), (300, 880), (255, 960), (250, 1000), (290, 1060),
                                (280, 1080), (130, 1080)]]},
    "jaspe": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (5).jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3},
    "garnet": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (6).jpeg", "fondo": "negro", "contorno": 1, "umbral": 8,
               "engrosar": 3},
    "peridot": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (7).jpeg", "fondo": "negro", "contorno": 1,
                "engrosar": 3},
    "amatista": {"img": "WhatsApp Image 2026-11-19 at 8.22.10 PM (8).jpeg", "fondo": "negro", "contorno": 1,
                 "engrosar": 3},
    # León es horizontal: cuadro de 64x50 (como el caniche), centrado abajo
    "leon": {"img": "WhatsApp Image 2026-11-19 at 8.25.02 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3,
             "cuadro": (64, 50)},
    # El Increíble Mundo de Gumball
    # Richard: sin la sombra marrón del suelo ni la caja blanca (la pierna levantada queda en el aire)
    "richard": {"img": "WhatsApp Image 2026-11-19 at 8.30.52 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3,
                # sin la sombra marrón del suelo ni la caja: se quita todo lo de la caja salvo la pata levantada
                # (redondeada, con contorno negro nuevo en el borde cortado), la espinilla y el ribete del short
                "aura": "(L < 70) & (r > b + 10)", "aura_desde_y": 1000, "huecos": 200,
                "quitar": [[(0, 690), (500, 690), (500, 820), (570, 860), (570, 1254), (0, 1254)]],
                "salvo": [[(283, 690), (283, 802), (248, 803), (233, 812), (226, 830), (226, 858), (234, 876),
                           (252, 888), (300, 893), (370, 893), (404, 888), (420, 874), (426, 850), (424, 812),
                           (414, 802), (412, 690)],
                          [(412, 690), (620, 690), (620, 870), (585, 866), (430, 782), (412, 782)]],
                "contorno_salvo": (9, 800)},
    "gumball": {"img": "WhatsApp Image 2026-11-19 at 8.31.10 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3,
                "cuadro": (64, 50)},
    "darwin": {"img": "WhatsApp Image 2026-11-19 at 8.33.15 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3},
    # Mordecai (Un Show Más, igual que Rigby): mismos parámetros que Rigby
    "mordecai": {"img": "WhatsApp Image 2026-11-19 at 8.22.29 PM.jpeg", "fondo": "negro", "contorno": 1, "engrosar": 3,
                 "huecos": 150},
}


def lum(a):
    return 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]


def desde_borde(pasable):
    """Lo pasable conectado al borde de la imagen."""
    et, n = nd.label(pasable)
    bordes = set(np.unique(np.concatenate([et[0], et[-1], et[:, 0], et[:, -1]]))) - {0}
    return np.isin(et, list(bordes))


def mascara(cfg, a):
    h, w = a.shape[:2]
    L = lum(a)
    if cfg["fondo"] == "negro":
        # el contorno de la figura también es negro y está pegado al fondo: si se inunda todo lo negro, se cuela por
        # las líneas internas. Se inunda solo el negro ANCHO (abierto `apertura` px: las líneas finas no pasan) y
        # luego se extiende por lo negro hasta dejar `apertura` px de contorno.
        negro = L < cfg.get("umbral", 14)
        r, k = cfg.get("apertura", 9), cfg.get("contorno", 4)
        nucleo = desde_borde(nd.binary_erosion(negro, iterations=r, border_value=1))
        fondo = nd.binary_dilation(nucleo, iterations=r - k) & negro
        # aura / magia: lo que no es negro pero tiene el color del aura y está pegado al fondo (sin cruzar el
        # contorno negro de la figura) también es fondo; se repite por si detrás quedó otra capa
        if cfg.get("aura"):
            r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
            Y, X = np.mgrid[0:h, 0:w]
            aura = eval(cfg["aura"], {}, {"r": r_, "g": g_, "b": b_, "L": L, "np": np, "X": X, "Y": Y}) & ~negro
            aura[:cfg.get("aura_desde_y", 0)] = False      # el pelo (arriba) no se toca
            et, _ = nd.label(aura)
            cerca = nd.binary_dilation(fondo, iterations=k + 2)
            toca = set(np.unique(et[cerca & aura])) - {0}
            quita = np.isin(et, list(toca))
            # y el anillo negro que quedaba entre el fondo y el aura
            fondo |= quita | (nd.binary_dilation(quita, iterations=k + 2) & negro & cerca)
    elif cfg["fondo"] == "color":
        bg = np.median(np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]]), axis=0)
        pasable = np.sqrt(((a - bg) ** 2).sum(2)) < cfg.get("tol", 50)
        fondo = desde_borde(pasable)
        if cfg.get("huecos"):
            # el color del fondo encerrado (entre un brazo y el cuerpo) también es fondo
            justo = np.sqrt(((a - bg) ** 2).sum(2)) < cfg.get("tol_hueco", 18)
            et, n = nd.label(justo & ~fondo)
            if n:
                tam = nd.sum(justo, et, range(1, n + 1))
                fondo |= np.isin(et, [i + 1 for i, t in enumerate(tam) if t >= cfg["huecos"]])
    elif cfg["fondo"] == "azul":
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        # azul del escenario (oscuro o el foco brillante): casi sin rojo ni verde; el contorno negro lo frena
        pasable = (b >= cfg.get("azul_min", 14)) & (r < 40) & (g < 0.42 * b + 8)
        ra = cfg.get("apertura", 4)
        nucleo = desde_borde(nd.binary_erosion(pasable, iterations=ra, border_value=1))
        fondo = nd.binary_dilation(nucleo, iterations=ra + 1) & pasable
        if cfg.get("huecos"):
            # el foco azul encerrado entre el brazo y la cara: azul puro, casi sin verde (la piel, el pelo y la
            # camiseta tienen bastante más verde)
            et, n = nd.label(pasable & ~fondo)
            if n:
                tam = nd.sum(pasable, et, range(1, n + 1))
                verde = nd.mean(g, et, range(1, n + 1)) / np.maximum(1, nd.mean(b, et, range(1, n + 1)))
                fondo |= np.isin(et, [i + 1 for i in range(n) if tam[i] >= cfg["huecos"] and verde[i] < 0.2])
    figura = ~fondo
    if cfg.get("poligono"):
        pol = Image.new("L", (w, h), 0)
        for poly in cfg["poligono"]:
            ImageDraw.Draw(pol).polygon([tuple(p) for p in poly], fill=255)
        figura &= np.array(pol) > 0
    if cfg.get("quitar"):
        q = Image.new("L", (w, h), 0)
        for poly in cfg["quitar"]:
            ImageDraw.Draw(q).polygon([tuple(p) for p in poly], fill=255)
        for poly in cfg.get("salvo", []):         # lo que se conserva aunque caiga dentro de lo que se quita
            ImageDraw.Draw(q).polygon([tuple(p) for p in poly], fill=0)
        figura &= ~(np.array(q) > 0)
    # huecos negros encerrados (entre brazo y cuerpo) que son fondo de verdad
    if cfg.get("huecos") and cfg["fondo"] == "negro":
        # solo el negro ANCHO: las líneas negras del dibujo (finas) se quedan
        negro = (a.max(axis=2) < cfg.get("hueco_max", 12)) & figura
        ra = cfg.get("apertura", 9)
        nucleo = nd.binary_erosion(negro, iterations=ra)
        et, n = nd.label(nucleo)
        if n:
            tam = nd.sum(nucleo, et, range(1, n + 1))
            grandes = np.isin(et, [i + 1 for i, t in enumerate(tam) if t >= cfg["huecos"]])
            figura &= ~(nd.binary_dilation(grandes, iterations=ra - cfg.get("contorno", 4)) & negro)
    # quitar el resplandor oscuro de color pegado al borde (auras): lo no negro de poca luz junto al fondo
    if cfg.get("pelar"):
        for _ in range(cfg["pelar"]):
            borde = figura & nd.binary_dilation(~figura)
            figura &= ~(borde & (L < cfg.get("pelar_luz", 60)) & (L >= cfg.get("umbral", 14)))
    # brazos finos que unen restos (rayos del aura) al cuerpo: se cortan con una apertura y se conserva solo lo que
    # queda cerca de la mancha principal
    if cfg.get("abrir"):
        n_ = cfg["abrir"]
        ab = nd.binary_opening(figura, iterations=n_)
        et, n = nd.label(ab)
        if n:
            tam = nd.sum(ab, et, range(1, n + 1))
            principal = et == (int(np.argmax(tam)) + 1)
            cerca_ = nd.binary_dilation(principal, iterations=n_ + 2)
            cerca_[:cfg.get("abrir_desde_y", 0)] = True     # arriba (pelo en punta) no se recorta
            figura &= cerca_
    # la mancha grande (y las que pasen del 3 %)
    et, n = nd.label(figura)
    if n > 1:
        tam = nd.sum(figura, et, range(1, n + 1))
        mayor = tam.max()
        figura = np.isin(et, [i + 1 for i, t in enumerate(tam) if t >= cfg.get("minimo", 0.03) * mayor])
    figura = nd.binary_fill_holes(figura) if not cfg.get("huecos") else figura
    # devolver el contorno negro que el umbral dejó fuera
    anillo = cfg.get("anillo", 0)
    if anillo:
        figura = nd.binary_dilation(figura, iterations=anillo) & (figura | (L < 40))
    if cfg.get("caja"):
        x0, y0, x1, y1 = cfg["caja"]
        c = np.zeros_like(figura)
        c[y0:y1, x0:x1] = True
        figura &= c
    return figura


def limpiar(sprite_py, pasadas=2, luz_rasgo=70):
    """Como la limpieza de huérfanos de pixelize, pero sin tocar los píxeles oscuros sueltos: son ojos, cejas y
    bocas (pixelize los borraba y las caras quedaban vacías)."""
    import spritelib as S
    sp = S.load(str(sprite_py))
    pal, bg = sp["palette"], sp["bg"]
    rows = [list(f) for f in sp["rows"]]
    h, w = len(rows), len(rows[0])

    def l(c):
        r, g, b = pal[c]
        return 0.3 * r + 0.59 * g + 0.11 * b
    for _ in range(pasadas):
        cambios = 0
        for y in range(h):
            for x in range(w):
                c = rows[y][x]
                if c == bg or l(c) < luz_rasgo:
                    continue
                vec = [rows[y + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                       if (dy or dx) and 0 <= y + dy < h and 0 <= x + dx < w and rows[y + dy][x + dx] != bg]
                if len(vec) >= 3 and c not in vec:
                    rows[y][x] = max(set(vec), key=vec.count)
                    cambios += 1
        if not cambios:
            break
    S.save(str(sprite_py), ["".join(f) for f in rows], pal, bg=bg)


def procesar(clave):
    cfg = P[clave]
    d = AQUI / "v4" / clave
    d.mkdir(parents=True, exist_ok=True)
    src = DESCARGAS / cfg["img"]
    shutil.copy(src, AQUI / "referencias" / f"{clave}_original.jpg")
    im = Image.open(src).convert("RGB")
    if cfg.get("contorno_salvo"):
        # el borde de lo que se conserva dentro de lo quitado (la pata de Richard) lleva contorno negro, como el
        # resto del dibujo; solo de `desde` hacia abajo
        ancho, desde = cfg["contorno_salvo"]
        capa = Image.new("L", im.size, 0)
        for poly in cfg["salvo"][:1]:
            ImageDraw.Draw(capa).line([tuple(p) for p in poly] + [tuple(poly[0])], fill=255, width=ancho, joint="curve")
        borde = np.array(capa) > 0
        borde[:desde] = False
        arr = np.array(im)
        arr[borde] = (12, 8, 10)
        im = Image.fromarray(arr)
    a = np.array(im).astype(int)
    fig = mascara(cfg, a)
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
    rgba[..., :3] = a
    if cfg.get("rellenar"):
        # huecos (fondo encerrado entre la capa y los brazos): opacos, con el color de lo que los rodea (el píxel con
        # color más cercano, no el contorno negro)
        lleno = nd.binary_fill_holes(fig)
        if cfg.get("caja"):
            x0, y0, x1, y1 = cfg["caja"]
            lleno[y1 - 1:, :] = fig[y1 - 1:, :]
        hueco = lleno & ~fig
        if hueco.any():
            color = fig & (lum(a) > cfg.get("rellenar_luz", 45))
            _, (iy, ix) = nd.distance_transform_edt(~color, return_indices=True)
            rgba[hueco, :3] = a[iy[hueco], ix[hueco]]
            fig = lleno
    if cfg.get("engrosar"):
        # los rasgos finos (ojos, boca, líneas) se ensanchan ANTES de reducir para que no se pierdan
        L = lum(a)
        osc = (L < cfg.get("engrosar_luz", 50)) & nd.binary_erosion(fig, iterations=cfg["engrosar"] + 6)
        et, n = nd.label(osc)
        if n:
            tam = nd.sum(osc, et, range(1, n + 1))
            osc = np.isin(et, [i + 1 for i, t in enumerate(tam) if t <= cfg.get("engrosar_max", 4000)])
        if cfg.get("engrosar_caja"):            # solo en la cara
            x0, y0, x1, y1 = cfg["engrosar_caja"]
            zona = np.zeros_like(osc)
            zona[y0:y1, x0:x1] = True
            osc &= zona
        k = cfg["engrosar"]
        ancho = nd.binary_dilation(osc, iterations=k)
        dentro = nd.binary_erosion(fig, iterations=k + 2)
        rgba[ancho & dentro, :3] = (20, 18, 24)
    rgba[..., 3] = np.where(fig, 255, 0)
    r = Image.fromarray(rgba, "RGBA")
    r = r.crop(r.getbbox())
    r.save(d / "recorte.png")
    rosa = Image.new("RGBA", r.size, (255, 0, 200, 255))
    rosa.alpha_composite(r)
    esc = 700 / max(r.size)
    rosa.resize((int(r.width * esc), int(r.height * esc)), Image.LANCZOS).save(AQUI / "vista" / f"{clave}_recorte.png")
    ancho, alto = cfg.get("cuadro", (48, 50))
    tam = f"{ancho * 2 - 4}x{alto * 2 - 4}"
    subprocess.run([sys.executable, str(SKILL / "pixelize.py"), str(d / "recorte.png"), "-o", str(d / "sprite_ilustracion.py"),
                    "--size", tam, "--colors", str(cfg.get("colores", 26)), "--outline", "none", "--erode", "0", "--no-clean",
                    "--preview", str(d / "sprite_ilustracion.png")], check=True, capture_output=True)
    limpiar(d / "sprite_ilustracion.py")
    import pokemon_exacto as PE
    PE.construir(clave)


def vista(claves):
    """vista/personajes_nov.png: por personaje, el recorte sobre rosa, el cuadro 0 a x4 (fondo oscuro y claro) y la
    hoja completa a x2 a su tamaño de pantalla."""
    filas = []
    for c in claves:
        rec = Image.open(AQUI / "vista" / f"{c}_recorte.png").convert("RGBA")
        rec = rec.resize((int(rec.width * 400 / rec.height), 400), Image.LANCZOS)
        hoja = Image.open(AQUI / "v4" / c / "hoja.png").convert("RGBA")
        fw = hoja.width // 4
        c0 = hoja.crop((0, 0, fw, hoja.height)).resize((fw * 4, hoja.height * 4), Image.NEAREST)
        osc = Image.new("RGBA", c0.size, (24, 26, 34, 255))
        osc.alpha_composite(c0)
        cla = Image.new("RGBA", c0.size, (235, 235, 240, 255))
        cla.alpha_composite(c0)
        h1 = Image.new("RGBA", (hoja.width, hoja.height), (40, 30, 50, 255))
        h1.alpha_composite(hoja)
        h1 = h1.resize((hoja.width // 2, hoja.height // 2), Image.LANCZOS)  # como se ve en pantalla al 100 %
        fila = Image.new("RGBA", (rec.width + osc.width * 2 + h1.width + 50, 410), (60, 60, 70, 255))
        fila.alpha_composite(rec, (5, 5))
        fila.alpha_composite(osc, (rec.width + 15, 5))
        fila.alpha_composite(cla, (rec.width + osc.width + 25, 5))
        fila.alpha_composite(h1, (rec.width + osc.width * 2 + 35, 5))
        filas.append(fila)
    v = Image.new("RGBA", (max(f.width for f in filas), sum(f.height for f in filas)), (60, 60, 70, 255))
    y = 0
    for f in filas:
        v.alpha_composite(f, (0, y))
        y += f.height
    nombre = "personajes_nov.png" if len(claves) > 1 else f"{claves[0]}_hoja.png"
    v.save(AQUI / "vista" / nombre)
    return AQUI / "vista" / nombre


if __name__ == "__main__":
    cs = [c for c in sys.argv[1:] if c != "--vista"] or list(P)
    if "--vista" not in sys.argv:
        for c in cs:
            procesar(c)
    for c in cs:
        print(vista([c]))
