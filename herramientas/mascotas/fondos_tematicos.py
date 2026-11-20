# -*- coding: utf-8 -*-
"""Fondos temáticos de Caudal: una paleta oscura teñida con los colores del personaje + un mosaico tenue
con su dibujo (cuadro 0 de su hoja de mascota) y su estela, en pixel art.

    python fondos_tematicos.py

Escribe el mosaico de cada tema (a densidad 2: se dibuja a la mitad de su tamaño en pantalla) en
app/assets/fondos/<clave>.png y escritorio/descargador/fondos/<clave>.png, más una vista en vista/fondos.png,
e imprime las capas de color calculadas (las mismas que van en estilos.py y tema.dart).
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
ARTE_APP = RAIZ / "app" / "assets" / "mascotas"
DESTINOS = [RAIZ / "app" / "assets" / "fondos", RAIZ / "escritorio" / "descargador" / "fondos"]

# clave (= mascota): nombre, color base del fondo, acento
TEMAS = [
    ("hellokitty", "Hello Kitty", "#1C0A10", "#FF4D6D"),
    ("kuromi", "Kuromi", "#120A1C", "#FF77B7"),
    ("pikachu", "Pikachu", "#17130A", "#F5D142"),
    ("charmander", "Charmander", "#1A0D07", "#FF8A3D"),
    ("squirtle", "Squirtle", "#071420", "#5EC8E5"),
    ("bulbasaur", "Bulbasaur", "#061712", "#5FD3A0"),
    ("snoopy", "Snoopy", "#111215", "#E8403F"),
    ("totoro", "Totoro", "#0E1210", "#8CCB6E"),
    ("mymelody", "My Melody", "#1C0A16", "#FF6FA5"),
    ("purin", "Pompompurin", "#181306", "#F7C948"),
    ("cinnamoroll", "Cinnamoroll", "#0A1324", "#7FB8FF"),
    ("kirby", "Kirby", "#1C0B16", "#FF8FB8"),
    ("doraemon", "Doraemon", "#06111F", "#2E8BFF"),
    ("olaf", "Olaf", "#0A1520", "#8ECDF5"),
    ("nyan", "Nyan Cat", "#0B0E2C", "#FF7AC8"),
    ("gato_negro", "Gato negro", "#0F0F12", "#7BD88F"),
    ("capibara", "Capibara", "#1A1008", "#FFA53D"),
    ("pochacco", "Pochacco", "#1A0A12", "#FF3D86"),
    ("nailong", "Nailong", "#181406", "#FFD23F"),
    ("messi", "Messi", "#0E0A1E", "#E8395F"),
    ("wos", "WOS", "#060C24", "#3D8BFF"),
    ("nightwing", "Nightwing", "#070B16", "#2E9BFF"),
    ("goku_ultra", "Goku Ultra Instinto", "#0E1118", "#C9D3E6"),
    ("goku_blue", "Goku Super Saiyajin Blue", "#061226", "#32C5FF"),
    ("wanda", "Wanda", "#1E0609", "#FF2D45"),
    ("loki", "Loki", "#06150B", "#E8B23A"),
    ("jake", "Jake el Perro", "#1A1204", "#FFC21F"),
    ("finn", "Finn el Humano", "#06121F", "#4FB3FF"),
    ("marceline", "Marceline", "#130A1E", "#E5303F"),
    ("pan_canela", "Pan de Canela", "#1A0E06", "#E08A3C"),
    ("rigby", "Rigby", "#150F09", "#C89A5E"),
    ("steven", "Steven", "#1E080D", "#FFD447"),
    ("perla", "Perla", "#061716", "#5EE6D8"),
    ("lapislazuli", "Lapislázuli", "#060E22", "#3D7BFF"),
    ("jaspe", "Jaspe", "#1C0D05", "#FF8A2B"),
    ("garnet", "Garnet", "#1C0510", "#FF3D8B"),
    ("peridot", "Peridot", "#0A1606", "#B6F03C"),
    ("amatista", "Amatista", "#150A1E", "#C08CFF"),
    ("leon", "León", "#1E0A14", "#FF8FC4"),
    ("richard", "Richard", "#1E0912", "#FF7FB6"),
    ("gumball", "Gumball", "#061424", "#4FC8FF"),
    ("darwin", "Darwin", "#1C0D04", "#FF8C1A"),
    ("mordecai", "Mordecai", "#3A6FD8", "#A9C8FF"),
]

LADO = 300              # mosaico a densidad 2 (150 px en pantalla)
ALFA_MASCOTA = 0.17
ALFA_ESTELA = 0.15


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x))) for x in c)


def _luz(rgb):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _mezcla(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def capas(base, escritorio=True):
    """Igual que estilos.fondo_de / Aspecto.fondoDe para un color propio."""
    rgb = _rgb(base)
    while _luz(rgb) > 0.035:
        rgb = _mezcla(rgb, (0, 0, 0), 0.15)
    pasos = (0.0, 0.035, 0.06, 0.09, 0.14, 0.11, 0.12) if escritorio else (0.0, 0.035, 0.06, 0.09, 0.14, 0.12)
    return [_hex(_mezcla(rgb, (255, 255, 255), t)) for t in pasos]


def _con_alfa(im, alfa):
    im = im.convert("RGBA")
    a = im.getchannel("A").point(lambda v: int(v * alfa))
    im.putalpha(a)
    return im


def _mascota(clave):
    cat = {m["clave"]: m for m in json.loads((ARTE_APP / "catalogo.json").read_text(encoding="utf-8"))}
    m = cat[clave]
    d = int(m.get("densidad", 1))
    hoja = Image.open(ARTE_APP / f"{clave}.png").convert("RGBA")
    cuadro = hoja.crop((0, 0, m["ancho"] * d, m["alto"] * d))
    cuadro = cuadro.crop(cuadro.getbbox())
    # el mosaico es a densidad 2: lo que viene a densidad 1 se duplica (nítido)
    if d == 1:
        cuadro = cuadro.resize((cuadro.width * 2, cuadro.height * 2), Image.NEAREST)
    # que no pase de ~ 96 px de alto
    lado = cuadro.height
    if lado > 100:
        f = 100 / lado
        cuadro = cuadro.resize((max(1, int(cuadro.width * f)), max(1, int(cuadro.height * f))), Image.NEAREST)
    return cuadro


def _estelas(clave):
    p = ARTE_APP / f"estela_{clave}.png"
    if p.exists():
        e = Image.open(p).convert("RGBA")
        return [e.crop((0, 0, 11, 11)), e.crop((11, 0, 22, 11))]
    # Nyan: estrellitas de su espacio
    estrellas = []
    for forma in ([".....W.....", ".....W.....", "...........", ".....P.....", "..W.PYP.W..", ".....P.....",
                   "...........", ".....W.....", ".....W.....", "...........", "..........."],
                  ["...........", "....W.W....", ".....W.....", "....W.W....", "...........", "........P..",
                   ".......PYP.", "........P..", "...........", "...........", "..........."]):
        im = Image.new("RGBA", (11, 11), (0, 0, 0, 0))
        col = {"W": (255, 255, 255, 255), "P": (255, 140, 210, 255), "Y": (255, 236, 120, 255)}
        for y, f in enumerate(forma):
            for x, c in enumerate(f):
                if c in col:
                    im.putpixel((x, y), col[c])
        estrellas.append(im)
    return estrellas


def mosaico(clave):
    t = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    # un personaje oscuro sobre su fondo oscuro necesita asomarse más
    m = _con_alfa(_mascota(clave), ALFA_MASCOTA * (2.6 if clave == "gato_negro" else 1))
    es = [_con_alfa(e.resize((44, 44), Image.NEAREST), ALFA_ESTELA) for e in _estelas(clave)]
    pequenas = [_con_alfa(e.resize((22, 22), Image.NEAREST), ALFA_ESTELA * 0.8) for e in _estelas(clave)]
    # la mascota arriba a la izquierda y otra copia (espejada) abajo a la derecha: el mosaico no se nota
    t.alpha_composite(m, (26, 24))
    espejo = m.transpose(Image.FLIP_LEFT_RIGHT)
    t.alpha_composite(espejo, (LADO // 2 + 16, LADO // 2 + 22))
    t.alpha_composite(es[0], (190, 44))
    t.alpha_composite(es[1], (44, 206))
    t.alpha_composite(pequenas[1], (150, 132))
    t.alpha_composite(pequenas[0], (260, 250))
    t.alpha_composite(pequenas[0], (112, 10))
    return t


def personaje(clave):
    """El cuadro 0 de su hoja de mascota, a densidad 2, con su color completo (la app le baja la opacidad)."""
    return _mascota(clave)


def main():
    for d in DESTINOS:
        d.mkdir(parents=True, exist_ok=True)
    vistas = []
    for clave, nombre, base, acento in TEMAS:
        t = personaje(clave)
        for d in DESTINOS:
            t.save(d / f"{clave}.png", optimize=True)
        c = capas(base)
        fondo = Image.new("RGBA", (LADO * 2, LADO), c[0])
        chico = _con_alfa(t, 0.6)
        fondo.alpha_composite(chico, (LADO * 2 - chico.width - 20, LADO - chico.height - 14))
        dib = ImageDraw.Draw(fondo)
        dib.rounded_rectangle((60, 90, 540, 210), 18, fill=c[2])
        dib.rounded_rectangle((80, 110, 140, 190), 10, fill=c[4])
        dib.text((160, 120), nombre, fill="#F3F5F9")
        dib.rounded_rectangle((160, 150, 330, 162), 6, fill=acento)
        dib.ellipse((480, 125, 520, 165), fill=acento)
        vistas.append(fondo.resize((LADO, LADO // 2), Image.LANCZOS))
        print(clave, nombre, "escritorio", c, "| móvil", capas(base, False), "| acento", acento)
    cols = 3
    v = Image.new("RGBA", (cols * (LADO + 10) + 10, ((len(vistas) + cols - 1) // cols) * (LADO // 2 + 10) + 10),
                  (20, 20, 24, 255))
    for i, im in enumerate(vistas):
        v.alpha_composite(im, (10 + (i % cols) * (LADO + 10), 10 + (i // cols) * (LADO // 2 + 10)))
    v.save(AQUI / "vista" / "fondos.png")


if __name__ == "__main__":
    main()
