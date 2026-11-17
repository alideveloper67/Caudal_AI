# -*- coding: utf-8 -*-
"""Taller de pixel art para las mascotas de Caudal (estilo sprites de Pokémon).

Se dibujan FORMAS (elipses, polígonos, rectángulos, píxeles) en un lienzo de 48x44 que mira a la derecha;
el taller calcula solo el sombreado en bandas (luz arriba-izquierda, sombra abajo-derecha) y el contorno
(tono medio-oscuro del propio color en el lado iluminado, casi negro en el lado de la sombra), igual que los
sprites de Pokémon. Así todas las mascotas salen con el mismo lenguaje visual.

Uso básico (ver pikachu.py):

    L = Lienzo()
    L.elipse(24, 30, 9, 8, 'cuerpo')          # material definido en MATERIALES
    L.poligono([(x, y), ...], 'oreja')
    L.px(31, 15, 'ojo')
    img = L.render()                           # PIL.Image RGBA 48x44

Cada forma pertenece a un GRUPO (por defecto, uno por llamada). El sombreado y el contorno interno se calculan
por grupo: una pata delante del cuerpo queda separada por una línea fina si `borde=True`.
"""
from __future__ import annotations

from PIL import Image

W, H = 48, 44


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mezcla(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Material:
    """Un color con su rampa: luz / base / sombra. `fijo=True` = sin sombreado (ojos, dientes, nariz)."""

    def __init__(self, base, luz=None, sombra=None, fijo=False, contorno=None):
        self.base = hex_rgb(base)
        self.luz = hex_rgb(luz) if luz else mezcla(self.base, (255, 255, 235), 0.35)
        # al oscurecer se desplaza hacia azul/morado, no solo se baja el brillo
        self.sombra = hex_rgb(sombra) if sombra else mezcla(self.base, (70, 40, 110), 0.38)
        self.fijo = fijo
        self.contorno_claro = hex_rgb(contorno) if contorno else mezcla(self.base, (60, 30, 20), 0.62)
        self.contorno_oscuro = mezcla(self.base, (12, 8, 24), 0.86)


class Lienzo:
    def __init__(self, materiales=None):
        self.m = materiales or {}
        self.celda = [[None] * W for _ in range(H)]      # (grupo, material) por píxel
        self.grupos = {}                                  # id -> dict(borde, sin_contorno, sin_sombra)
        self._n = 0

    # ----------------------------------------------------------------- materiales
    def mat(self, nombre, *a, **k):
        self.m[nombre] = Material(*a, **k)
        return nombre

    # ----------------------------------------------------------------- formas
    def _grupo(self, borde, sin_contorno, sin_sombra, grupo):
        if grupo is None:
            self._n += 1
            grupo = self._n
        g = self.grupos.setdefault(grupo, {})
        if borde:
            g['borde'] = True
        if sin_contorno:
            g['sin_contorno'] = True
        if sin_sombra:
            g['sin_sombra'] = True
        return grupo

    def _poner(self, x, y, grupo, mat):
        if 0 <= x < W and 0 <= y < H:
            self.celda[y][x] = (grupo, mat)

    def px(self, x, y, mat, grupo=None):
        g = self._grupo(False, True, True, grupo)
        self._poner(x, y, g, mat)

    def rect(self, x0, y0, x1, y1, mat, borde=False, sin_contorno=False, sin_sombra=False, grupo=None):
        g = self._grupo(borde, sin_contorno, sin_sombra, grupo)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self._poner(x, y, g, mat)
        return g

    def elipse(self, cx, cy, rx, ry, mat, borde=False, sin_contorno=False, sin_sombra=False, grupo=None):
        """Elipse rellena. rx, ry en píxeles (el ancho total es 2*rx+1)."""
        g = self._grupo(borde, sin_contorno, sin_sombra, grupo)
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                dx = (x - cx) / (rx + 0.5)
                dy = (y - cy) / (ry + 0.5)
                if dx * dx + dy * dy <= 1.0:
                    self._poner(x, y, g, mat)
        return g

    def poligono(self, pts, mat, borde=False, sin_contorno=False, sin_sombra=False, grupo=None):
        """Polígono relleno (regla par-impar) por los centros de los píxeles."""
        g = self._grupo(borde, sin_contorno, sin_sombra, grupo)
        n = len(pts)
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            cruces = []
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    cruces.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            cruces.sort()
            for i in range(0, len(cruces) - 1, 2):
                for x in range(round(cruces[i]), round(cruces[i + 1])):
                    self._poner(x, y, g, mat)
        return g

    def linea(self, x0, y0, x1, y1, mat, grupo=None):
        g = self._grupo(False, True, True, grupo)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self._poner(x0, y0, g, mat)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
        return g

    def recolorear(self, fn, mat):
        """Cambia a `mat` todos los píxeles (x, y) donde fn(x, y) sea verdadero y ya haya algo pintado."""
        for y in range(H):
            for x in range(W):
                if self.celda[y][x] and fn(x, y):
                    g, _ = self.celda[y][x]
                    self.celda[y][x] = (g, mat)

    # ----------------------------------------------------------------- render
    def _en(self, x, y, g):
        return 0 <= x < W and 0 <= y < H and self.celda[y][x] is not None and self.celda[y][x][0] == g

    def render(self, sombreado=True, contorno=True):
        sal = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        px = sal.load()
        # tamaño (ancho, alto) de cada grupo, para decidir el grosor de la sombra
        cajas = {}
        for y in range(H):
            for x in range(W):
                c = self.celda[y][x]
                if c:
                    x0, y0, x1, y1 = cajas.get(c[0], (x, y, x, y))
                    cajas[c[0]] = (min(x0, x), min(y0, y), max(x1, x), max(y1, y))
        self._tam = {g: (b[2] - b[0] + 1, b[3] - b[1] + 1) for g, b in cajas.items()}
        # 1) relleno con bandas de luz y sombra por grupo
        color = [[None] * W for _ in range(H)]
        for y in range(H):
            for x in range(W):
                c = self.celda[y][x]
                if not c:
                    continue
                g, nombre = c
                mt = self.m[nombre]
                rgb = mt.base
                gi = self.grupos.get(g, {})
                if sombreado and not mt.fijo and not gi.get('sin_sombra'):
                    # banda de sombra en el borde inferior/derecho del grupo (diagonal, como en los sprites de Pokémon);
                    # en formas grandes la banda es de 2 px
                    gr = self._tam.get(g, (0, 0))
                    grosor = 2 if min(gr) >= 9 else 1
                    if any(not self._en(x + k, y + k, g) for k in range(1, grosor + 1)) or not self._en(x, y + 1, g) and not self._en(x + 1, y, g):
                        rgb = mt.sombra
                color[y][x] = rgb
        # 2) contorno interno entre grupos (el que queda delante se marca donde toca a otro grupo)
        if contorno:
            ids = {}
            for y in range(H):
                for x in range(W):
                    c = self.celda[y][x]
                    if c:
                        ids.setdefault(c[0], len(ids))
            for y in range(H):
                for x in range(W):
                    c = self.celda[y][x]
                    if not c:
                        continue
                    g, nombre = c
                    if not self.grupos.get(g, {}).get('borde'):
                        continue
                    for dx, dy in ((-1, 0), (0, -1), (1, 0), (0, 1)):
                        nx, ny = x + dx, y + dy
                        o = self.celda[ny][nx] if 0 <= nx < W and 0 <= ny < H else None
                        if o and o[0] != g and ids.get(o[0], 0) < ids.get(g, 0):
                            mt = self.m[nombre]
                            color[y][x] = mt.contorno_oscuro if (dx > 0 or dy > 0) else mt.contorno_claro
                            break
        # 3) contorno exterior de 1 px: marrón en el lado iluminado, oscuro en el de la sombra
        for y in range(H):
            for x in range(W):
                if color[y][x] is not None:
                    px[x, y] = color[y][x] + (255,)
        if contorno:
            for y in range(H):
                for x in range(W):
                    if self.celda[y][x]:
                        continue
                    vecino = None
                    luz_lado = False
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < W and 0 <= ny < H and self.celda[ny][nx]:
                            g, nombre = self.celda[ny][nx]
                            if self.grupos.get(g, {}).get('sin_contorno'):
                                continue
                            vecino = nombre
                            # el contorno está arriba o a la izquierda del relleno = lado iluminado
                            luz_lado = luz_lado or (dx > 0 or dy > 0)
                    if vecino:
                        mt = self.m[vecino]
                        px[x, y] = (mt.contorno_claro if luz_lado else mt.contorno_oscuro) + (255,)
        return sal


def hoja(cuadros):
    """Une cuadros de 48x44 lado a lado en una hoja."""
    out = Image.new('RGBA', (W * len(cuadros), H), (0, 0, 0, 0))
    for i, c in enumerate(cuadros):
        out.paste(c, (i * W, 0))
    return out


def vista(hojas, escala=8, fondo=(30, 34, 46), salida=None, columnas=1):
    """Contact sheet ampliada con vecino más cercano, para mirar el dibujo."""
    cw = 2 * W * escala + 24
    ch = H * escala + 24
    filas = (len(hojas) + columnas - 1) // columnas
    img = Image.new('RGBA', (cw * columnas, ch * filas), fondo + (255,))
    for i, h in enumerate(hojas):
        g = h.resize((h.width * escala, h.height * escala), Image.NEAREST)
        img.alpha_composite(g, ((i % columnas) * cw + 12, (i // columnas) * ch + 12))
    if salida:
        img.save(salida)
    return img
