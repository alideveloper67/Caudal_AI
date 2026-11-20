# -*- coding: utf-8 -*-
"""Integra los personajes de noviembre (hechos con personajes_nov.py) en Caudal:

1. Dibuja la estela de cada uno (11x11, 2 cuadros: balón, nota, rayo, gota, brillo...) en v4/<clave>/estela.png.
2. Crea su cargador <clave>.py (para exportar.py y la galería).
3. Copia hoja y estela a las dos carpetas de arte (móvil y escritorio) y los añade al final de los dos catálogos
   (si ya estaban, actualiza su entrada en el mismo sitio).

    python integrar_nov.py

Los fondos con personaje se hacen aparte: fondos_tematicos.py (TEMAS) + las capas en estilos.py y tema.dart.
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
ARTE = [RAIZ / "app" / "assets" / "mascotas", RAIZ / "escritorio" / "descargador" / "mascotas"]
sys.path.insert(0, str(AQUI))
import pokemon_exacto as PE  # noqa: E402

# clave: (nombre, origen, estela, forma de la estela, colores {letra: rgb})
PERSONAJES = {
    "messi": ("Messi", "Fútbol", "balon", "BALON", {"O": (40, 40, 56), "W": (250, 250, 252), "F": (28, 28, 40)}),
    "wos": ("WOS", "Música", "nota", "NOTA", {"O": (20, 40, 110), "F": (80, 190, 255), "H": (200, 240, 255)}),
    "nightwing": ("Nightwing", "DC", "simbolo", "ALAS", {"O": (10, 20, 60), "F": (40, 140, 255)}),
    "goku_ultra": ("Goku Ultra Instinto", "Dragon Ball", "rayo", "RAYO", {"O": (90, 100, 130), "F": (225, 230, 245)}),
    "goku_blue": ("Goku Super Saiyajin Blue", "Dragon Ball", "rayo", "RAYO", {"O": (20, 60, 140), "F": (60, 200, 255)}),
    "wanda": ("Wanda", "Marvel", "magia", "BRILLO",
              {"O": (100, 10, 30), "F": (230, 40, 60), "H": (255, 120, 120), "W": (255, 220, 220)}),
    "loki": ("Loki", "Marvel", "magia", "BRILLO",
             {"O": (90, 60, 10), "F": (240, 190, 50), "H": (120, 220, 90), "W": (255, 245, 180)}),
    "jake": ("Jake el Perro", "Hora de Aventura", "huella", "HUELLA", {"O": (130, 70, 10), "F": (250, 180, 40)}),
    "finn": ("Finn el Humano", "Hora de Aventura", "espada", "ESPADA",
             {"O": (60, 60, 80), "W": (230, 235, 245), "F": (240, 190, 40)}),
    "marceline": ("Marceline", "Hora de Aventura", "nota", "NOTA",
                  {"O": (100, 10, 30), "F": (230, 50, 60), "H": (255, 160, 160)}),
    "pan_canela": ("Pan de Canela", "Hora de Aventura", "glaseado", "GOTA",
                   {"O": (150, 90, 40), "F": (250, 225, 180), "H": (255, 250, 235)}),
    "rigby": ("Rigby", "Un Show Más", "hoja", "HOJA", {"O": (90, 55, 25), "F": (190, 140, 80), "H": (230, 190, 130)}),
    "steven": ("Steven", "Steven Universe", "estrella", "ESTRELLA", {"O": (150, 90, 0), "F": (255, 215, 60)}),
    "perla": ("Perla", "Steven Universe", "brillo", "BRILLO",
              {"O": (30, 110, 120), "F": (120, 230, 220), "H": (200, 250, 245), "W": (255, 255, 255)}),
    "lapislazuli": ("Lapislázuli", "Steven Universe", "gota", "GOTA",
                    {"O": (20, 40, 120), "F": (60, 140, 255), "H": (170, 220, 255)}),
    "jaspe": ("Jaspe", "Steven Universe", "chispa", "BRILLO",
              {"O": (120, 50, 10), "F": (255, 140, 40), "H": (255, 200, 90), "W": (255, 240, 200)}),
    "garnet": ("Garnet", "Steven Universe", "rombo", "ROMBO", {"O": (100, 10, 50), "F": (230, 40, 110), "H": (255, 140, 190)}),
    "peridot": ("Peridot", "Steven Universe", "triangulo", "TRIANGULO",
                {"O": (50, 110, 20), "F": (190, 240, 60), "H": (240, 255, 170)}),
    "amatista": ("Amatista", "Steven Universe", "estrella", "ESTRELLA", {"O": (90, 50, 130), "F": (200, 150, 240)}),
    "leon": ("León", "Steven Universe", "estrella", "ESTRELLA", {"O": (150, 60, 100), "F": (255, 160, 200)}),
    "richard": ("Richard", "El Increíble Mundo de Gumball", "corazon", "CORAZON",
                {"O": (140, 50, 90), "F": (255, 140, 190), "H": (255, 220, 235)}),
    "gumball": ("Gumball", "El Increíble Mundo de Gumball", "estrella", "ESTRELLA", {"O": (20, 90, 150), "F": (90, 200, 255)}),
    "darwin": ("Darwin", "El Increíble Mundo de Gumball", "burbuja", "BURBUJA",
               {"O": (40, 110, 170), "F": (150, 215, 255), "H": (255, 255, 255)}),
    "mordecai": ("Mordecai", "Un Show Más", "pluma", "PLUMA",
                 {"O": (20, 40, 110), "F": (58, 111, 216), "H": (169, 200, 255)}),
}

FORMAS = {
    "ESTRELLA": ["...........", ".....O.....", ".....O.....", "....OFO....", ".OOOFFFOOO.", "..OFFFFFO..",
                 "...OFFFO...", "...OFO.FO..", "..OO...OO..", "...........", "..........."],
    "NOTA": ["...........", ".....OO....", ".....OFO...", ".....OFFO..", ".....OFOFO.", ".....OFO.O.", "..OOOOFO...",
             ".OFFFFFO...", ".OFHFFFO...", "..OOOOO....", "..........."],
    "RAYO": ["......OOO..", ".....OFFO..", "....OFFO...", "...OFFO....", "..OFFFFOO..", "..OOOFFFO..", "....OFFO...",
             "...OFFO....", "..OFO......", "..OO.......", "..........."],
    "GOTA": [".....O.....", "....OFO....", "....OFO....", "...OFFFO...", "..OFFFFFO..", "..OFHFFFO..", "..OFHFFFO..",
             "..OFFFFFO..", "...OFFFO...", "....OOO....", "..........."],
    "BRILLO": [".....O.....", "....OFO....", "....OFO....", "...OFHFO...", ".OOFHWHFOO.", "OFFHWWWHFFO", ".OOFHWHFOO.",
               "...OFHFO...", "....OFO....", "....OFO....", ".....O....."],
    "ROMBO": ["...........", ".....O.....", "....OFO....", "...OFHFO...", "..OFHFFFO..", ".OFHFFFFFO.", "..OFFFFFO..",
              "...OFFFO...", "....OFO....", ".....O.....", "..........."],
    "TRIANGULO": ["...........", ".....O.....", "....OFO....", "....OFO....", "...OFHFO...", "...OFHFO...", "..OFHFFFO..",
                  "..OFFFFFO..", ".OFFFFFFFO.", ".OOOOOOOOO.", "..........."],
    "HUELLA": ["...........", "..OO...OO..", ".OFFO.OFFO.", ".OFFO.OFFO.", "..OO...OO..", "....OOO....", "...OFFFO...",
               "..OFFFFFO..", "..OFFFFFO..", "...OOOOO...", "..........."],
    "HOJA": ["...........", "........OO.", "......OOFO.", "....OOFFFO.", "...OFFHFFO.", "..OFFHFFO..", "..OFHFFO...",
             ".OFHFOO....", ".OHOO......", "O.O........", "..........."],
    "BALON": ["...........", "...OOOOO...", "..OFWWWFO..", ".OFWWWWWFO.", ".OWWWWWWWO.", ".OWWFFFWWO.", ".OWWFFFWWO.",
              ".OWWWWWWWO.", "..OFWWWFO..", "...OOOOO...", "..........."],
    "ALAS": ["...........", "...........", "O.........O", "OFO.....OFO", ".OFO...OFO.", ".OFFO.OFFO.", "..OFFOFFO..",
             "..OFFFFFO..", "...OFFFO...", "....OOO....", "..........."],
    "CORAZON": ["...........", "..OO...OO..", ".OFFO.OFFO.", "OFHFFOFFFFO", "OFHFFFFFFFO", "OFFFFFFFFFO", ".OFFFFFFFO.",
                "..OFFFFFO..", "...OFFFO...", "....OFO....", ".....O....."],
    "BURBUJA": ["...........", "...OOOOO...", "..O.....O..", ".O.HH....O.", ".O.H.....O.", ".O.......O.", ".O.......O.",
                ".O......FO.", "..O....FO..", "...OOOOO...", "..........."],
    # pluma azul: diagonal desde arriba a la derecha, con el cañón claro
    "PLUMA": ["........OO.", ".......OFHO", "......OFHFO", ".....OFHFO.", "....OFHFO..", "...OFHFO...",
              "..OFHFO....", ".OFHFO.....", ".OHFO......", "OFO........", "O.........."],
    "ESPADA": ["........OO.",".......OWO.", "......OWO..", ".....OWO...", "..O.OWO....", "..OOWO.....", "...OO......",
               "..OFOO.....", ".OFO.......", ".OO........", "..........."],
}


def estela(clave):
    """2 cuadros de 11x11: el segundo con el relleno sombreado a trozos (como las estelas que ya hay)."""
    _, _, _, forma, col = PERSONAJES[clave]
    filas = FORMAS[forma]
    im = Image.new("RGBA", (22, 11), (0, 0, 0, 0))
    for k in (0, 1):
        for y, f in enumerate(filas):
            for x, c in enumerate(f):
                if c == ".":
                    continue
                rgb = col.get(c, col["F"])
                if k == 1 and c == "F" and (x + y) % 3 == 0:
                    rgb = tuple(int(v * 0.85) for v in rgb)
                im.putpixel((k * 11 + x, y), (*rgb, 255))
    destino = AQUI / "v4" / clave / "estela.png"
    im.save(destino)
    return destino


CARGADOR = '''# -*- coding: utf-8 -*-
"""{nombre}: de la imagen de la persona (pixel art de IA sin transparencia), recortada con personajes_nov.py y
pixelizada con la skill; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / '{clave}' / 'hoja.png').convert('RGBA')
'''


def main():
    for clave, (nombre, origen, nombre_estela, _, _) in PERSONAJES.items():
        estela(clave)
        (AQUI / f"{clave}.py").write_text(CARGADOR.format(nombre=nombre, clave=clave), encoding="utf-8")
    for arte in ARTE:
        cat = json.loads((arte / "catalogo.json").read_text(encoding="utf-8"))
        donde = {m["clave"]: i for i, m in enumerate(cat)}
        for clave, (nombre, origen, nombre_estela, _, _) in PERSONAJES.items():
            ancho, alto = PE.POKEMON[clave]["cuadro"]
            hoja = Image.open(AQUI / "v4" / clave / "hoja.png")
            assert hoja.size == (ancho * 4 * 2, alto * 2), (clave, hoja.size)
            entrada = {"clave": clave, "nombre": nombre, "origen": origen, "ancho": ancho, "alto": alto,
                       "arcoiris": False, "estela": nombre_estela, "estela_colores": [], "estela_ancho": 11,
                       "estela_alto": 11, "cuadros": 4, "densidad": 2}
            if clave in donde:
                cat[donde[clave]] = entrada
            else:
                cat.append(entrada)
            shutil.copy(AQUI / "v4" / clave / "hoja.png", arte / f"{clave}.png")
            shutil.copy(AQUI / "v4" / clave / "estela.png", arte / f"estela_{clave}.png")
        (arte / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
        print(arte, "->", len(cat), "mascotas")


def vista():
    """vista/personajes_nov_resumen.png: de cada personaje, su mascota (cuadro 0, x3), su estela (x4), la hoja a
    tamaño de pantalla y su fondo con personaje (paleta + personaje en la esquina, como en fondos_tematicos.py)."""
    from PIL import ImageDraw
    import fondos_tematicos as F
    temas = {t[0]: t for t in F.TEMAS}
    tarjetas = []
    for clave, (nombre, origen, *_r) in PERSONAJES.items():
        hoja = Image.open(AQUI / "v4" / clave / "hoja.png").convert("RGBA")
        fw = hoja.width // 4
        c0 = hoja.crop((0, 0, fw, hoja.height)).resize((fw * 3 // 2, hoja.height * 3 // 2), Image.NEAREST)
        est = Image.open(AQUI / "v4" / clave / "estela.png").convert("RGBA").resize((88, 44), Image.NEAREST)
        _, nom, base, acento = temas[clave]
        c = F.capas(base)
        fondo = Image.new("RGBA", (300, 230), c[0])
        per = F._con_alfa(F.personaje(clave), 0.6)
        fondo.alpha_composite(per, (300 - per.width - 10, 230 - per.height - 8))
        d = ImageDraw.Draw(fondo)
        d.rounded_rectangle((14, 60, 190, 130), 12, fill=c[2])
        d.rounded_rectangle((24, 72, 64, 118), 8, fill=c[4])
        d.text((74, 76), nom[:18], fill="#F3F5F9")
        d.rounded_rectangle((74, 98, 170, 106), 4, fill=acento)
        d.ellipse((150, 160, 180, 190), fill=acento)
        t = Image.new("RGBA", (c0.width + 330, max(c0.height, 230) + 40), (30, 32, 40, 255))
        t.alpha_composite(c0, (6, 30))
        t.alpha_composite(fondo, (c0.width + 20, 30))
        d = ImageDraw.Draw(t)
        d.text((8, 8), f"{nombre} ({clave}) - {origen}", fill="#FFFFFF")
        e = Image.new("RGBA", (96, 52), (30, 32, 40, 255))
        e.alpha_composite(est, (4, 4))
        tarjetas.append((t, e))
    cols = 4
    tw = max(t.width for t, _ in tarjetas)
    th = max(t.height for t, _ in tarjetas) + 56
    v = Image.new("RGBA", (cols * (tw + 10) + 10, ((len(tarjetas) + cols - 1) // cols) * (th + 10) + 10), (18, 18, 22, 255))
    for i, (t, e) in enumerate(tarjetas):
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 10)
        v.alpha_composite(t, (x, y))
        v.alpha_composite(e, (x, y + t.height + 2))
    destino = AQUI / "vista" / "personajes_nov_resumen.png"
    v.save(destino)
    print(destino)


def arreglos(claves=("goku_ultra", "goku_blue", "loki", "perla", "wanda", "richard")):
    """vista/arreglos_nov.png: ANTES (antes_nov/) y DESPUÉS de los personajes retocados: cuadro 0 ampliado x4 y el
    fondo con personaje (su paleta y el personaje en la esquina)."""
    from PIL import ImageDraw
    import fondos_tematicos as F
    temas = {t[0]: t for t in F.TEMAS}

    def bloque(hoja, fondo_png, clave):
        fw = hoja.width // 4
        c0 = hoja.crop((0, 0, fw, hoja.height)).resize((fw * 4, hoja.height * 4), Image.NEAREST)
        caja = Image.new("RGBA", (128 * 4, 100 * 4), (36, 38, 48, 255))
        caja.alpha_composite(c0, ((caja.width - c0.width) // 2, 0))
        c = F.capas(temas[clave][2])
        fondo = Image.new("RGBA", (300, 400), c[0])
        per = F._con_alfa(Image.open(fondo_png).convert("RGBA"), 0.6)
        per = per.resize((per.width * 2, per.height * 2), Image.NEAREST)
        fondo.alpha_composite(per, (300 - per.width - 10, 400 - per.height - 10))
        b = Image.new("RGBA", (caja.width + fondo.width + 10, 400), (20, 20, 24, 255))
        b.alpha_composite(caja, (0, 0))
        b.alpha_composite(fondo, (caja.width + 10, 0))
        return b

    filas = []
    for clave in claves:
        antes = bloque(Image.open(AQUI / "antes_nov" / f"{clave}_hoja.png").convert("RGBA"),
                       AQUI / "antes_nov" / f"{clave}_fondo.png", clave)
        despues = bloque(Image.open(AQUI / "v4" / clave / "hoja.png").convert("RGBA"),
                         ARTE[0].parent / "fondos" / f"{clave}.png", clave)
        f = Image.new("RGBA", (antes.width * 2 + 40, 430), (20, 20, 24, 255))
        d = ImageDraw.Draw(f)
        d.text((10, 6), f"{clave}: ANTES", fill="#FFB0B0")
        d.text((antes.width + 40, 6), f"{clave}: DESPUES", fill="#B0FFB0")
        f.alpha_composite(antes, (10, 26))
        f.alpha_composite(despues, (antes.width + 40, 26))
        filas.append(f)
    v = Image.new("RGBA", (filas[0].width, sum(x.height for x in filas)), (20, 20, 24, 255))
    for i, f in enumerate(filas):
        v.alpha_composite(f, (0, i * 430))
    destino = AQUI / "vista" / "arreglos_nov.png"
    v.save(destino)
    print(destino)


if __name__ == "__main__":
    if "--arreglos" in sys.argv:
        arreglos()
        sys.exit()
    if "--vista" not in sys.argv:
        main()
    vista()
