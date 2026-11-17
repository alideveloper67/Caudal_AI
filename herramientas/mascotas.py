# -*- coding: utf-8 -*-
"""Dibuja las «mascotitas» del reproductor de Caudal (pixel art dibujado a mano aquí).

Cada personaje se dibuja a mano en una rejilla chica (la mitad izquierda, que se refleja; más
pequeños detalles asimétricos), se suaviza con un escalado de pixel art (Scale2x) y se le pone
contorno oscuro: queda en el estilo de los sprites de 3ª generación, pero con arte propio.
Cada mascota también tiene su «estela»: un detalle chiquito que va dejando al caminar.

Salidas (a las dos apps): escritorio/descargador/mascotas/ y app/assets/mascotas/
   <clave>.png          hoja de 2 cuadros (caminar), mira al frente/derecha
   estela_<clave>.png   2 variantes del detalle de la estela, lado a lado
   catalogo.json
Uso:  python herramientas/mascotas.py [ruta_de_la_hoja_de_contacto.png]
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS = [RAIZ / "escritorio" / "descargador" / "mascotas", RAIZ / "app" / "assets" / "mascotas"]
MITAD = 12


def rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def oscuro(c, f):
    return tuple(max(0, int(v * (1 - f))) for v in c)


def fila(texto, ancho):
    """'.1 y2 k2 y*' -> lista de letras (un '*' rellena lo que falta con ese color)."""
    toks = texto.split()
    partes = []
    for t in toks:
        m = re.fullmatch(r"(.)(\d+|\*)", t)
        if not m:
            raise ValueError(f"token raro {t!r} en {texto!r}")
        partes.append((m.group(1), m.group(2)))
    fijo = sum(int(n) for _c, n in partes if n != "*")
    res = []
    for c, n in partes:
        res += [c] * ((ancho - fijo) if n == "*" else int(n))
    if len(res) < ancho:                      # una columna de menos: se completa con el último color
        res += [res[-1]] * (ancho - len(res))
    return res[:ancho]


class Personaje:
    def __init__(self, pal, filas, extras=(), completo=False, ancho=MITAD):
        self.pal = {k: rgb(v) for k, v in pal.items()}
        self.completo = completo
        self.ancho = ancho * (1 if completo else 2)
        self.alto = 22
        izq = [fila(t, ancho) for t in filas]
        while len(izq) < 21:
            izq.append(["."] * ancho)
        self.rej = [r + (r if completo else r[::-1]) if not completo else r for r in izq]
        if not completo:
            self.rej = [r + r[::-1] for r in izq]
        for x, y, texto in extras:
            letras = fila(texto, sum(int(n) if n != "*" else 0 for _c, n in re.findall(r"(.)(\d+|\*)", texto)))
            for i, c in enumerate(letras):
                if c != "." and 0 <= x + i < self.ancho and 0 <= y < 21:
                    self.rej[y][x + i] = c

    def cuadro(self, bob):
        """Rejilla de colores (None = transparente) con la mascota bajada `bob` píxeles."""
        w = self.ancho
        g = [[None] * w for _ in range(self.alto)]
        for y, r in enumerate(self.rej):
            for x, c in enumerate(r):
                if c != "." and 0 <= y + bob < self.alto:
                    g[y + bob][x] = self.pal[c]
        return redondear(g)


def redondear(g):
    h, w = len(g), len(g[0])

    def lleno(x, y):
        return 0 <= x < w and 0 <= y < h and g[y][x] is not None
    quitar = []
    for y in range(h):
        for x in range(w):
            if not lleno(x, y):
                continue
            for sx in (-1, 1):
                for sy in (-1, 1):
                    if (not lleno(x + sx, y) and not lleno(x, y + sy) and lleno(x - sx, y) and lleno(x, y - sy)
                            and lleno(x - sx * 2, y) and lleno(x, y - sy * 2) and lleno(x - sx, y - sy)):
                        quitar.append((x, y))
    for x, y in quitar:
        g[y][x] = None
    return g


def scale2x(g):
    h, w = len(g), len(g[0])
    out = [[None] * (w * 2) for _ in range(h * 2)]

    def at(x, y):
        return g[y][x] if 0 <= x < w and 0 <= y < h else None
    for y in range(h):
        for x in range(w):
            p = g[y][x]
            a, b, c, d = at(x, y - 1), at(x + 1, y), at(x - 1, y), at(x, y + 1)
            e0 = a if (c == a and c != d and a != b) else p
            e1 = b if (a == b and a != c and b != d) else p
            e2 = c if (d == c and d != b and c != a) else p
            e3 = d if (b == d and b != a and d != c) else p
            out[2 * y][2 * x], out[2 * y][2 * x + 1] = e0, e1
            out[2 * y + 1][2 * x], out[2 * y + 1][2 * x + 1] = e2, e3
    return out


def a_imagen(g):
    h, w = len(g), len(g[0])
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pix = img.load()
    for y in range(h):
        for x in range(w):
            if g[y][x] is not None:
                pix[x, y] = g[y][x] + (255,)
    # contorno oscuro del color de la parte vecina
    for y in range(h):
        for x in range(w):
            if g[y][x] is None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and g[ny][nx] is None:
                    pix[nx, ny] = oscuro(g[y][x], 0.72) + (255,)
    return img


def hoja(p):
    a = a_imagen(scale2x(p.cuadro(1)))
    b = a_imagen(scale2x(p.cuadro(0)))
    img = Image.new("RGBA", (a.width * 2, a.height), (0, 0, 0, 0))
    img.paste(a, (0, 0))
    img.paste(b, (a.width, 0))
    return img, a.size


# =====================================================================  LOS PERSONAJES
PIKACHU = Personaje(
    dict(y="#FFD93B", l="#FFF08A", o="#E0A81A", k="#2b2233", r="#E8403A", w="#ffffff", b="#8a5a22"),
    [".1 k3 .*", ".1 k3 .*", ".1 k3 .*", ".1 y3 .*", ".2 y3 .*", ".2 y3 .2 y*", ".2 y3 l1 y*", ".1 l2 y*",
     ".1 y*", ".1 y2 k2 y*", ".1 y2 k1 w1 y*", ".1 y1 r2 y6 k1", ".1 y1 r2 y5 k1 y2", ".1 y9 k2", ".2 y*",
     ".2 y*", ".2 o1 y*", ".2 o2 y*", ".3 o2 y*", ".2 y4 .*", ".2 o4 .*"],
    extras=[(21, 15, "b2"), (20, 13, "y4"), (22, 10, "y2"), (21, 8, "y3"), (22, 6, "y2")])

NAILONG = Personaje(
    dict(y="#FFD84A", l="#FFF0A0", o="#E8B320", c="#FFF3B8", k="#2b2233", r="#C43B3B", p="#FF8F8F", h="#FFA56B"),
    [".*", ".3 c2 .*", ".3 c3 .*", ".3 c1 y*", ".2 l2 y*", ".1 l2 y*", ".1 y*", ".1 y4 k1 y*", ".1 y4 k1 y*",
     "y1 h2 y*", "y*", "y8 k1 y3", "y9 r3", "y9 k3", ".1 y*", ".1 y2 c*", ".1 y2 c*", ".1 o1 y1 c*",
     ".2 o1 y*", ".2 y4 .*", ".2 o4 .*"],
    extras=[(22, 17, "y2"), (21, 18, "y3")])

KIRBY = Personaje(
    dict(p="#FFA6C9", l="#FFD0E4", o="#E57BA6", k="#2b2233", w="#ffffff", b="#2d3fa0", r="#E8434F",
         c="#FF6F91", d="#C7254E"),
    [".*", ".*", ".6 l3 p*", ".4 l2 p*", ".3 l1 p*", ".2 l1 p*", ".2 p*", ".1 p7 k2 p*", ".1 p7 w1 k1 p*",
     ".1 p7 k2 p*", ".1 p7 b2 p*", ".1 p7 b2 p*", "p2 c3 p*", ".1 p1 c3 p5 d2", ".1 p*", ".2 o1 p*",
     ".3 o2 p*", ".4 o4 p*", ".1 r7 .*", ".1 r7 .*", ".2 d4 .*"])

HELLOKITTY = Personaje(
    dict(w="#FFFFFF", g="#DDE0EA", k="#2b2233", y="#FFCC33", r="#FF4D6D", p="#FF9DB3"),
    [".*", ".1 w2 .*", ".1 w4 .*", ".1 w*", ".1 w*", "w*", "w*", "w*", "w3 k2 w*", "k2 w1 k2 w*", "w11 y1",
     "k2 w*", "w*", ".1 w*", ".2 w*", ".3 w*", ".3 w*", ".3 g1 w*", ".4 g1 w*", ".3 w4 .*", ".3 g4 .*"],
    extras=[(14, 2, "r2 .1 p2 .1 r2"), (14, 3, "r3 p2 r3"), (14, 4, "r2 .1 p2 .1 r2")])

DORAEMON = Personaje(
    dict(b="#2AA7E8", B="#7AD0F7", d="#1C86BE", w="#ffffff", g="#E4E8F0", k="#2b2233", r="#E8433F", y="#FFD93B"),
    [".*", ".4 b*", ".2 b*", ".1 b3 B1 b*", "b3 B1 b2 k6", "b5 k1 w5 k1", "b5 k1 w5 k1", "b5 k1 w3 k1 w1 k1",
     "b5 k1 w3 k1 w1 k1", "b3 w2 k*", "b2 k3 w5 r2", "b2 w9 k1", "b2 k3 w6 k1", "b2 w5 k*", "b3 w*", ".1 r*",
     ".2 r*", ".3 b*", ".3 d*", ".2 w4 .*", ".2 g4 .*"],
    extras=[(11, 16, "y2"), (11, 17, "y2")])

TOTORO = Personaje(
    dict(g="#8A8F99", G="#A9AEB8", d="#6F7480", w="#F1ECDC", k="#2b2233", W="#ffffff"),
    [".2 g2 .*", ".2 g3 .*", ".2 g3 .*", ".1 g4 .*", ".1 g*", ".1 G1 g*", "g*", "g3 W4 g*", "g3 W1 k2 W1 g*",
     "k2 g1 W1 k2 W1 g*", "g3 W4 g3 k2", "k2 g*", "g3 w*", "g2 w*", "g2 w1 d1 w2 d1 w*", "g1 w*",
     "g1 w2 d1 w2 d1 w*", "g2 w*", ".1 g2 w*", ".2 d4 .*", ".2 d4 .*"])

SNOOPY = Personaje(
    dict(w="#FFFFFF", g="#E4E4EC", k="#2b2233", r="#E8433F"),
    [".*", ".5 w*", ".3 w*", ".2 w*", ".1 k2 w*", ".1 k2 w*", "k3 w*", "k3 w4 k1 w*", "k3 w*", "k3 w6 k3",
     "k3 w6 k3", "k2 w*", ".1 w*", ".2 r*", ".2 w*", ".2 w*", ".2 g1 w*", ".3 g1 w*", ".3 w*", ".3 w4 .*",
     ".3 g4 .*"])

POOH = Personaje(
    dict(y="#F2B33D", l="#FFD27A", o="#C98A20", r="#E03A3A", R="#B82A2A", c="#F9D38A", k="#2b2233"),
    [".*", ".1 y3 .*", ".1 y3 .*", ".4 y*", ".2 l1 y*", ".1 y*", ".1 y5 k1 y*", ".1 y5 k1 y*", ".1 y7 c3 k1",
     ".1 y6 c5", ".2 y5 c4 k1", ".2 y*", ".1 r*", "y1 r*", "y1 r*", ".1 r*", ".2 r*", ".2 R2 r*", ".3 y*",
     ".2 y4 .*", ".2 o4 .*"])

STITCH = Personaje(
    dict(b="#3F8FE0", B="#6AAEF0", d="#2C5FB0", p="#E88AB4", i="#9FD0FF", k="#2b2233", w="#ffffff"),
    [".*", "b1 .*", "b2 .*", "b1 p1 b1 .*", "b1 p1 b2 .*", "b1 p1 b3 .*", "b1 p1 b5 d*", "b7 d*", "b*",
     "b4 w1 k3 b*", "b4 k4 b*", "b4 k4 b*", "b4 k4 b2 k2", "b5 k3 b4", "b*", ".2 b2 i*", ".2 b1 i*", ".3 i*",
     ".3 d1 i*", ".2 d4 .*", ".2 d4 .*"])

MICKEY = Personaje(
    dict(k="#2b2233", s="#FFE0BD", S="#E8B890", r="#E8433F", y="#FFD93B", w="#ffffff"),
    [".1 k3 .*", "k5 .*", "k5 .*", "k5 .1 k*", ".1 k3 .1 k*", ".2 k*", ".1 k2 s*", ".1 k1 s*", ".2 s7 k1 s*", ".2 s7 k1 s*",
     ".2 s7 k1 s*", ".2 s*", ".2 s8 k2", ".3 s*", ".4 s3 r*", ".5 s*", ".3 r*", ".3 r*", ".3 r1 y2 r*",
     ".2 y4 .*", ".2 y4 .*"])

BOB = Personaje(
    dict(y="#FFE23F", Y="#FFF08A", o="#D9B814", b="#8B5A2B", B="#6B4220", w="#ffffff", e="#2D7DD2",
         k="#2b2233", h="#FFB347", r="#E8433F"),
    [".*", ".2 Y1 y*", ".2 y*", ".2 y*", ".2 y2 w4 y*", ".2 y1 w6 y*", ".2 y1 w3 e2 w1 y*",
     ".2 y1 w3 e1 k1 w1 y*", ".2 y1 w6 y*", ".2 y2 w4 y*", "y*", ".2 y1 h3 y*", ".2 y3 k1 y*",
     ".2 y3 k5 w2", ".2 y8 w2", ".2 w*", ".2 b*", ".2 b*", ".2 B*", ".4 y2 .*", ".3 k4 .*"])

PATRICK = Personaje(
    dict(p="#F58FB0", P="#FFB5CC", o="#D66A8E", g="#7ACB4A", G="#4F9A2C", m="#D94F9A", w="#ffffff",
         k="#2b2233", r="#7A2030"),
    [".11 p1", ".10 p2", ".9 p3", ".8 p4", ".7 P1 p4", ".6 p*", ".5 p*", ".4 p*", ".3 p*", ".3 p2 w3 p*",
     ".3 p2 w1 k1 w1 p*", ".3 p*", ".2 p*", ".2 p2 k*", ".3 p3 r*", ".2 p*", ".1 g*", ".1 g2 m1 g2 m1 g*",
     ".1 G1 g*", ".2 p4 .*", ".2 o4 .*"])

PUSHEEN = Personaje(
    dict(g="#BFC3CC", G="#DDE0E8", d="#8D92A0", p="#E88AA0", k="#2b2233", h="#FF9FB4"),
    [".*", ".1 g2 .*", ".1 g3 .*", ".1 g*", ".1 g6 d1 g1 d1 g1 d1", ".1 g6 d1 g1 d1 g1 d1", "g*", "g3 k2 g*",
     "g3 k2 g*", "g11 p1", "g1 h2 g7 k1 g1", "d2 g*", "g*", "d2 g*", ".1 g*", ".2 g*", ".3 g*", ".3 d1 g*",
     ".4 g*", ".3 g4 .*", ".3 d4 .*"],
    extras=[(20, 14, "g3"), (21, 13, "g3"), (22, 12, "g2")])

KUROMI = Personaje(
    dict(k="#2b2233", K="#4a4458", w="#FFFFFF", p="#FF9EC8", P="#FF6FA8"),
    [".1 k1 .*", ".1 k2 .*", ".1 k3 .*", ".2 k3 .*", ".2 k*", ".1 k9 p2", ".1 k8 p3", ".1 k8 p1 k1 p1", ".2 k*",
     ".1 k1 w*", ".1 k1 w3 k2 w*", ".1 k1 w3 k2 w*", ".1 k1 w9 k1", ".1 k1 w1 p2 w*", ".1 k1 w*", ".2 w*",
     ".3 k*", ".3 k*", ".3 k*", ".3 k4 .*", ".3 k4 .*"])

MYMELODY = Personaje(
    dict(p="#FF9BC2", P="#FFC8DC", w="#ffffff", c="#FFD1E3", k="#2b2233", y="#FFCC33", f="#FFE066", g="#E8E8F0"),
    [".2 p2 .*", ".1 p4 .*", ".1 p1 c2 p1 .*", ".1 p1 c2 p1 .*", ".1 p1 c2 p1 .*", ".1 p1 c2 p1 .*", ".1 p*",
     ".1 P1 p*", ".1 p*", ".1 p2 w*", ".1 p1 w*", ".1 p1 w3 k2 w*", ".1 p1 w3 k2 w*", ".1 p1 w9 y1",
     ".1 p1 w1 p2 w*", ".2 w*", ".2 p*", ".3 w*", ".3 w*", ".3 w4 .*", ".3 g4 .*"],
    extras=[(19, 7, "f1 y1 f1"), (20, 6, "f1"), (20, 8, "f1")])

CINNAMOROLL = Personaje(
    dict(w="#FFFFFF", g="#E4E8F2", b="#AEE0FF", B="#7EC4F5", k="#2b2233", i="#3A6FD8", h="#FFB3C8"),
    [".*", ".*", ".5 w*", ".3 w*", ".2 w*", ".1 w*", ".1 w*", ".1 w*", "b3 w*", "b4 w*", "b4 w2 i2 w*",
     "b4 w2 i2 w*", "b4 w2 i2 w3 k1", "b3 w2 h2 w*", "b3 w*", ".1 b2 w*", ".3 w*", ".3 w*", ".3 g1 w*",
     ".3 w4 .*", ".3 g4 .*"],
    extras=[(21, 17, "w3"), (22, 16, "w2"), (23, 15, "w1")])

PURIN = Personaje(
    dict(y="#FBE58A", Y="#FFF3B0", o="#E0C060", n="#8B5E3C", N="#6E4A2E", b="#9A6A3F", k="#2b2233", h="#FFB38A"),
    [".*", ".10 n2", ".4 n*", ".3 n*", ".2 N1 n*", ".2 n*", "b2 y*", "b3 y*", "b3 y*", "b3 y3 k1 y*",
     "b3 y3 k1 y*", "b2 h2 y6 b2", ".1 y*", ".1 y*", ".2 y*", ".2 y*", ".3 y*", ".3 y*", ".3 o1 y*",
     ".3 y4 .*", ".3 o4 .*"])

RILAKKUMA = Personaje(
    dict(b="#A8754A", B="#C08C5C", d="#8D5F38", c="#F1D9B5", e="#E0B98A", k="#2b2233"),
    [".2 b3 .*", ".1 b1 e2 b1 .*", ".1 b4 .*", ".1 b*", ".1 B1 b*", "b*", "b*", "b*", "b3 k2 b*", "b3 k2 b*",
     "b6 c4 k2", "b7 c*", "b7 c*", "b7 c*", ".1 b*", ".1 b*", ".2 b*", ".2 d1 b*", ".3 d1 b*", ".2 d4 .*",
     ".2 d4 .*"])

OLAF = Personaje(
    dict(w="#FFFFFF", g="#DDE6F0", k="#2b2233", n="#FF8A1F", t="#6B4A2A", r="#7A2030"),
    [".9 t1 .1 t1", ".9 t1 .1 t1", ".4 w*", ".3 w*", ".2 w*", ".2 w*", ".2 w3 k2 w*", ".2 w3 k2 w*", ".2 w*",
     ".2 w8 n2", ".2 w9 n1", ".3 w1 k8", ".3 w2 r*", ".3 w*", ".2 w*", ".1 w10 k1", ".1 w*", ".1 w10 k1",
     ".2 g1 w*", ".2 w4 .*", ".2 g4 .*"],
    extras=[(0, 13, "t3"), (0, 12, "t1"), (21, 13, "t3"), (23, 12, "t1")])

MINION = Personaje(
    dict(y="#FFD93B", Y="#FFEB78", o="#E0B01A", b="#2C5FB0", B="#1F4A90", g="#9AA3B0", d="#5A626E", w="#ffffff",
         k="#2b2233", e="#6B4A2A"),
    [".10 k1 .1", ".4 y*", ".3 y*", ".2 Y1 y*", ".2 y5 g*", ".2 d5 g*", ".2 d4 g1 w*", ".2 d4 g1 w3 e2",
     ".2 d4 g1 w3 e1 k1", ".2 y4 g*", ".2 y*", ".2 y*", ".2 y5 k5", ".2 y*", ".2 b*", ".2 b3 B4 b*",
     ".2 b3 B4 b*", ".2 b*", ".2 b*", ".2 k4 .*", ".2 k4 .*"],
    extras=[(0, 14, "y2"), (0, 15, "y2"), (22, 14, "y2"), (22, 15, "y2")])

TOOTHLESS = Personaje(
    dict(d="#2F3640", D="#4A5360", k="#2b2233", g="#7EE05A", G="#4CB02E", w="#ffffff"),
    [".*", "d1 .*", "d2 .*", "d3 .*", "d4 .*", "d5 .*", ".2 d*", ".1 d*", ".1 D1 d*", "d3 g4 d*",
     "d2 g1 w1 g4 d*", "d2 g3 k1 g2 d*", "d2 g3 k1 g2 d*", "d2 g6 d*", "d3 g4 d*", "d*", ".1 d*", ".2 d*",
     ".2 d*", ".2 d4 .*", ".2 k4 .*"],
    extras=[(21, 16, "d3"), (22, 15, "d2")])

_NY = ".2 {t} "
NYAN = Personaje(
    dict(t="#F2C58F", p="#FF9AD5", s="#E8437F", g="#9A9AA8", d="#75758A", k="#2b2233", h="#FF9FB4"),
    [".*", ".*", ".*",
     ".16 g2 .6 g2 .*",
     ".2 t13 .1 g3 .4 g3 .*",
     ".2 t13 g12 .*",
     ".2 t1 p3 s1 p7 t1 g12 .*",
     ".2 t1 p8 s1 p2 t1 g3 k1 g4 k1 g3 .*",
     ".2 t1 p1 s1 p9 t1 g3 k1 g4 k1 g3 .*",
     ".2 t1 p5 s1 p5 t1 g12 .*",
     ".2 t1 p8 s1 p2 t1 g1 h2 g6 h2 g1 .*",
     "g2 t1 p2 s1 p8 t1 g3 k1 g1 k1 g1 k1 g4 .*",
     "g2 t1 p6 s1 p4 t1 g12 .*",
     ".2 t1 p11 t1 g12 .*",
     ".2 t1 p3 s1 p7 t1 g12 .*",
     ".2 t13 g12 .*",
     ".4 g2 .3 g2 .6 g2 .4 g2 .*",
     ".4 g2 .3 g2 .6 g2 .4 g2 .*",
     ".4 d2 .3 d2 .6 d2 .4 d2 .*", ".*", ".*"],
    completo=True, ancho=28)

# (clave, nombre, origen, personaje, forma de la estela, colores de la estela)
MASCOTAS = [
    ("nyan", "Nyan Cat", "Nyan Cat", NYAN, "arcoiris", ()),
    ("nailong", "Nailong", "Nailong", NAILONG, "estrella", ("#FFE45C", "#FFB830")),
    ("pikachu", "Pikachu", "Pokémon", PIKACHU, "rayo", ("#FFE94A", "#FFB400")),
    ("kirby", "Kirby", "Kirby", KIRBY, "estrella", ("#FFB6D5", "#FF7FB0")),
    ("hellokitty", "Hello Kitty", "Sanrio", HELLOKITTY, "corazon", ("#FF6F91", "#FFB3C8")),
    ("doraemon", "Doraemon", "Doraemon", DORAEMON, "cascabel", ("#FFD93B", "#FFB400")),
    ("totoro", "Totoro", "Mi vecino Totoro", TOTORO, "hoja", ("#6BCB5C", "#3E9F3A")),
    ("snoopy", "Snoopy", "Peanuts", SNOOPY, "hueso", ("#FFFFFF", "#D9DDE8")),
    ("pooh", "Winnie the Pooh", "Disney", POOH, "gota", ("#FFC93C", "#E89A1A")),
    ("stitch", "Stitch", "Lilo y Stitch", STITCH, "estrella", ("#7CC4FF", "#B07CFF")),
    ("mickey", "Mickey Mouse", "Disney", MICKEY, "orejas", ("#2b2233", "#4a4458")),
    ("bob", "Bob Esponja", "Bob Esponja", BOB, "burbuja", ("#BFE9FF", "#7CC4FF")),
    ("patrick", "Patricio", "Bob Esponja", PATRICK, "burbuja", ("#FFC2DA", "#FF8FB8")),
    ("pusheen", "Pusheen", "Pusheen", PUSHEEN, "galleta", ("#E0A66B", "#B97A3E")),
    ("kuromi", "Kuromi", "Sanrio", KUROMI, "calavera", ("#FF9EC8", "#B07CFF")),
    ("mymelody", "My Melody", "Sanrio", MYMELODY, "flor", ("#FF9BC2", "#FFE066")),
    ("cinnamoroll", "Cinnamoroll", "Sanrio", CINNAMOROLL, "nube", ("#FFFFFF", "#CFE8FF")),
    ("purin", "Pompompurin", "Sanrio", PURIN, "flan", ("#FFD966", "#8B5E3C")),
    ("rilakkuma", "Rilakkuma", "San-X", RILAKKUMA, "miga", ("#F1D9B5", "#C08C5C")),
    ("olaf", "Olaf", "Frozen", OLAF, "copo", ("#FFFFFF", "#BFE9FF")),
    ("minion", "Minion", "Mi villano favorito", MINION, "banana", ("#FFE45C", "#E8B810")),
    ("toothless", "Chimuelo", "Cómo entrenar a tu dragón", TOOTHLESS, "llama", ("#B6FF7A", "#4CB02E")),
]

# =====================================================================  LAS ESTELAS (detalles de 9x9)
FORMAS = {
    "corazon": ["..aa.aa..", ".abbabba.", "abbbbbba.", "abbbbbba.", ".abbbba..", "..abba...", "...aa....", ".........",
                "........."],
    "estrella": ["....a....", "....a....", "...aba...", "aaabbbaaa", ".abbbbba.", "..abbba..", "..aba.ba.",
                 ".aa...aa.", "........."],
    "rayo": ["...aaaa..", "..abbba..", "..abba...", ".abbbba..", "..aabba..", "...abba..", "...abba..", "....aa...",
             "........."],
    "cascabel": ["..aaaaa..", ".abbbbba.", "abbbbbbba", "abbbbbbba", "aaaaaaaaa", "abbaaabba", "abbbbbbba", ".aaaaaaa.",
                 "........."],
    "hoja": ["......aa.", "....aabba", "..aabbbba", ".abbbbba.", "abbbbba..", "abbbba...", "aabba....", "a.aa.....",
             "........."],
    "hueso": ["aa.....aa", "abaaaaaba", "aabbbbbaa", ".aabbbaa.", "aabbbbbaa", "abaaaaaba", "aa.....aa", ".........",
              "........."],
    "gota": ["....a....", "...aba...", "..abbba..", ".abbbbba.", ".abbbbba.", ".abbbbba.", "..abbba..", "...aaa...",
             "........."],
    "orejas": ["aaa...aaa", "abbaaabba", "abbbabbba", "abbbaabbb", ".aaa.aaa.", ".........", ".........", ".........",
               "........."],
    "burbuja": ["..aaaaa..", ".abbbbba.", "abcbbbbba", "abcbbbbba", "abbbbbbba", "abbbbbbba", ".abbbbba.", "..aaaaa..",
                "........."],
    "galleta": ["..aaaaa..", ".abbbbba.", "abbabbba.", "abbbbabba", "abbabbbba", "abbbbabba", ".abbbbba.", "..aaaaa..",
                "........."],
    "calavera": ["..aaaaa..", ".abbbbba.", "abbbbbbba", "abaabaabb", "abaabaabb", ".abbbbba.", "..abaaba.", "..a.a.a..",
                 "........."],
    "flor": ["..aa.aa..", ".abbabba.", "..abccba.", "aabbccbba", ".abbccba.", "..abbbba.", ".aa.aa.aa", ".........",
             "........."],
    "nube": ["...aaa...", "..abbba..", ".aabbbbaa", "abbbbbbba", "abbbbbbba", ".aaaaaaa.", ".........", ".........",
             "........."],
    "flan": ["...bbb...", "..aaaaa..", ".abbbbba.", ".abbbbba.", "abbbbbbba", "abbbbbbba", "abbbbbbba", ".aaaaaaa.",
             "........."],
    "miga": ["..aa.....", ".abba.aa.", ".abba.ab.", "..aa..ab.", ".....aa..", "..aa.....", ".abba....", "..aa.....",
             "........."],
    "copo": ["....a....", "a...a...a", ".a.aba.a.", "..aabaa..", "aabbbbbaa", "..aabaa..", ".a.aba.a.", "a...a...a",
             "....a...."],
    "banana": ["......aa.", ".....abba", "....abbba", "...abbba.", "..abbba..", ".abbba...", "aabba....", ".aa......",
               "........."],
    "llama": ["....a....", "...aba...", "...abba..", "..abbba..", ".abbcbba.", ".abbcbba.", ".abbbbba.", "..aaaaa..",
              "........."],
}


def estela_imagen(forma, colores):
    """Dos variantes (la segunda más chica) del detallito, ya con contorno, lado a lado."""
    a_c, b_c = (rgb(colores[0]), rgb(colores[1])) if colores else ((255, 255, 255),) * 2
    filas = FORMAS[forma]
    img = Image.new("RGBA", (22, 11), (0, 0, 0, 0))
    pix = img.load()
    mapa = {"a": oscuro(b_c, 0.45), "b": a_c, "c": (255, 255, 255)}
    for y, f in enumerate(filas):
        for x, c in enumerate(f):
            if c in mapa:
                pix[x + 1, y + 1] = mapa[c] + (255,)
                pix[x + 12, y + 1] = mapa[c] + (255,)
    # variante 2: sin el brillo interior, para que parpadeen
    for y in range(11):
        for x in range(12, 22):
            if pix[x, y][3] and pix[x, y][:3] == a_c and (x + y) % 3 == 0:
                pix[x, y] = oscuro(a_c, 0.15) + (255,)
    return img


def main():
    catalogo = []
    ex = []
    for clave, nombre, origen, p, forma, colores in MASCOTAS:
        img, (w, h) = hoja(p)
        for s in SALIDAS:
            s.mkdir(parents=True, exist_ok=True)
            img.save(s / f"{clave}.png")
        entrada = {"clave": clave, "nombre": nombre, "origen": origen, "ancho": w, "alto": h,
                   "arcoiris": forma == "arcoiris", "estela": forma, "estela_colores": list(colores)}
        if forma != "arcoiris":
            ei = estela_imagen(forma, colores)
            for s in SALIDAS:
                ei.save(s / f"estela_{clave}.png")
            entrada["estela_ancho"] = 11
            entrada["estela_alto"] = 11
        catalogo.append(entrada)
        ex.append((clave, forma, colores))
    for s in SALIDAS:
        (s / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=1), encoding="utf-8")
    esc, cols = 3, 6
    filas = (len(MASCOTAS) + cols - 1) // cols
    cw, ch = 64 * esc, 46 * esc
    sheet = Image.new("RGBA", (cols * cw, filas * ch), (40, 36, 56, 255))
    for i, (clave, forma, colores) in enumerate(ex):
        im = Image.open(SALIDAS[0] / f"{clave}.png")
        fr = im.crop((0, 0, im.width // 2, im.height)).resize((im.width // 2 * esc, im.height * esc), Image.NEAREST)
        x0, y0 = (i % cols) * cw, (i // cols) * ch
        sheet.paste(fr, (x0, y0), fr)
        if forma != "arcoiris":
            e = Image.open(SALIDAS[0] / f"estela_{clave}.png")
            e = e.crop((0, 0, 11, 11)).resize((11 * esc * 2, 11 * esc * 2), Image.NEAREST)
            sheet.paste(e, (x0 + cw - 70, y0 + ch - 70), e)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "herramientas" / "contacto_mascotas.png"
    sheet.save(out)
    print("listo", len(MASCOTAS), "mascotas ->", out)


if __name__ == "__main__":
    main()
