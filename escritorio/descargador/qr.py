# -*- coding: utf-8 -*-
"""Codigos QR sin dependencias (para el QR de la Fiesta).

Modo byte (UTF-8), correccion de errores nivel M, versiones 1 a 10 (hasta 213
bytes). Es el algoritmo estandar (ISO/IEC 18004, el de la biblioteca de Nayuki):
la version es la mas pequena en la que cabe el texto y la mascara, la de menor
penalizacion (a igualdad, la de numero menor). La app movil usa el mismo
algoritmo (app/lib/nucleo/qr.dart), asi que los dos dibujan el mismo QR.

    m = matriz("https://...")      # lista de filas de bool (True = negro), sin margen
"""

# nivel M: codewords de correccion por bloque y numero de bloques, por version (1..10)
_ECC_M = [None, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26]
_BLOQUES_M = [None, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5]
_FORMATO_M = 0          # bits de formato del nivel M
VERSION_MAXIMA = 10


class ErrorQR(ValueError):
    pass


def _modulos_datos(ver):
    r = (16 * ver + 128) * ver + 64
    if ver >= 2:
        n = ver // 7 + 2
        r -= (25 * n - 10) * n - 55
        if ver >= 7:
            r -= 36
    return r


def capacidad_bytes(ver):
    """Cuantos bytes caben en modo byte con nivel M."""
    datos = _modulos_datos(ver) // 8 - _ECC_M[ver] * _BLOQUES_M[ver]
    bits_cuenta = 8 if ver <= 9 else 16
    return (datos * 8 - 4 - bits_cuenta) // 8


def _posiciones_alineacion(ver):
    if ver == 1:
        return []
    n = ver // 7 + 2
    paso = (ver * 8 + n * 3 + 5) // (n * 4 - 4) * 2
    lado = ver * 4 + 17
    r = [lado - 7 - i * paso for i in range(n - 1)] + [6]
    return list(reversed(r))


# ------------------------------------------------------------- Reed-Solomon
def _mult(x, y):
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _divisor(grado):
    r = [0] * (grado - 1) + [1]
    raiz = 1
    for _ in range(grado):
        for j in range(len(r)):
            r[j] = _mult(r[j], raiz)
            if j + 1 < len(r):
                r[j] ^= r[j + 1]
        raiz = _mult(raiz, 0x02)
    return r


def _resto(datos, divisor):
    r = [0] * len(divisor)
    for b in datos:
        f = b ^ r.pop(0)
        r.append(0)
        for i, c in enumerate(divisor):
            r[i] ^= _mult(c, f)
    return r


# ------------------------------------------------------------- codewords
def _codewords(datos, ver):
    bits = []

    def poner(valor, n):
        for i in range(n - 1, -1, -1):
            bits.append((valor >> i) & 1)

    poner(0b0100, 4)
    poner(len(datos), 8 if ver <= 9 else 16)
    for b in datos:
        poner(b, 8)
    capacidad = (_modulos_datos(ver) // 8 - _ECC_M[ver] * _BLOQUES_M[ver]) * 8
    poner(0, min(4, capacidad - len(bits)))
    poner(0, (-len(bits)) % 8)
    relleno = 0xEC
    while len(bits) < capacidad:
        poner(relleno, 8)
        relleno ^= 0xEC ^ 0x11
    cw = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    nbloques = _BLOQUES_M[ver]
    ecc = _ECC_M[ver]
    crudos = _modulos_datos(ver) // 8
    cortos = nbloques - crudos % nbloques
    largo_corto = crudos // nbloques
    div = _divisor(ecc)
    bloques = []
    k = 0
    for i in range(nbloques):
        n = largo_corto - ecc + (0 if i < cortos else 1)
        d = cw[k:k + n]
        k += n
        e = _resto(d, div)
        if i < cortos:
            d = d + [None]          # hueco para igualar largos al intercalar
        bloques.append(d + e)
    salida = []
    for i in range(len(bloques[0])):
        for j, b in enumerate(bloques):
            if b[i] is not None:
                salida.append(b[i])
    return salida


# ------------------------------------------------------------- dibujo
class _Lienzo:
    def __init__(self, ver):
        self.ver = ver
        self.lado = ver * 4 + 17
        self.m = [[False] * self.lado for _ in range(self.lado)]
        self.funcion = [[False] * self.lado for _ in range(self.lado)]

    def fijar(self, x, y, negro):
        self.m[y][x] = bool(negro)
        self.funcion[y][x] = True

    def patrones(self):
        n = self.lado
        for i in range(n):
            self.fijar(6, i, i % 2 == 0)
            self.fijar(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        d = max(abs(dx), abs(dy))
                        self.fijar(x, y, d not in (2, 4))
        pos = _posiciones_alineacion(self.ver)
        u = len(pos)
        for i in range(u):
            for j in range(u):
                if (i == 0 and j == 0) or (i == 0 and j == u - 1) or (i == u - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.fijar(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self.formato(0)
        self.version()

    def formato(self, mascara):
        dato = _FORMATO_M << 3 | mascara
        r = dato
        for _ in range(10):
            r = (r << 1) ^ ((r >> 9) * 0x537)
        bits = (dato << 10 | r) ^ 0x5412
        b = lambda i: (bits >> i) & 1  # noqa: E731
        n = self.lado
        for i in range(6):
            self.fijar(8, i, b(i))
        self.fijar(8, 7, b(6))
        self.fijar(8, 8, b(7))
        self.fijar(7, 8, b(8))
        for i in range(9, 15):
            self.fijar(14 - i, 8, b(i))
        for i in range(8):
            self.fijar(n - 1 - i, 8, b(i))
        for i in range(8, 15):
            self.fijar(8, n - 15 + i, b(i))
        self.fijar(8, n - 8, True)

    def version(self):
        if self.ver < 7:
            return
        r = self.ver
        for _ in range(12):
            r = (r << 1) ^ ((r >> 11) * 0x1F25)
        bits = self.ver << 12 | r
        for i in range(18):
            bit = (bits >> i) & 1
            a, c = self.lado - 11 + i % 3, i // 3
            self.fijar(a, c, bit)
            self.fijar(c, a, bit)

    def datos(self, cw):
        n = self.lado
        i = 0
        total = len(cw) * 8
        der = n - 1
        while der >= 1:
            if der == 6:
                der = 5
            for vert in range(n):
                for j in range(2):
                    x = der - j
                    arriba = ((der + 1) & 2) == 0
                    y = n - 1 - vert if arriba else vert
                    if not self.funcion[y][x] and i < total:
                        self.m[y][x] = bool((cw[i >> 3] >> (7 - (i & 7))) & 1)
                        i += 1
            der -= 2

    def enmascarar(self, mascara):
        f = _MASCARAS[mascara]
        for y in range(self.lado):
            for x in range(self.lado):
                if not self.funcion[y][x] and f(x, y):
                    self.m[y][x] = not self.m[y][x]


_MASCARAS = [
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


def penalizacion(m):
    """Penalizacion estandar (reglas N1..N4) de una matriz terminada."""
    n = len(m)

    def anotar(largo, hist):
        if hist[0] == 0:
            largo += n
        hist.pop()
        hist.insert(0, largo)

    def contar(h):
        k = h[1]
        nucleo = k > 0 and h[2] == h[4] == h[5] == k and h[3] == k * 3
        return ((1 if nucleo and h[0] >= k * 4 and h[6] >= k else 0)
                + (1 if nucleo and h[6] >= k * 4 and h[0] >= k else 0))

    def terminar(color, largo, hist):
        if color:
            anotar(largo, hist)
            largo = 0
        largo += n
        anotar(largo, hist)
        return contar(hist)

    total = 0
    for leer in (lambda a, b: m[a][b], lambda a, b: m[b][a]):
        for a in range(n):
            color = False
            largo = 0
            hist = [0] * 7
            for b in range(n):
                if leer(a, b) == color:
                    largo += 1
                    if largo == 5:
                        total += 3
                    elif largo > 5:
                        total += 1
                else:
                    anotar(largo, hist)
                    if not color:
                        total += contar(hist) * 40
                    color = leer(a, b)
                    largo = 1
            total += terminar(color, largo, hist) * 40
    for y in range(n - 1):
        for x in range(n - 1):
            c = m[y][x]
            if c == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                total += 3
    oscuros = sum(sum(1 for v in fila if v) for fila in m)
    t = n * n
    k = (abs(oscuros * 20 - t * 10) + t - 1) // t - 1
    total += k * 10
    return total


def version_para(texto):
    largo = len(str(texto).encode("utf-8"))
    for v in range(1, VERSION_MAXIMA + 1):
        if largo <= capacidad_bytes(v):
            return v
    raise ErrorQR("El texto es demasiado largo para el QR.")


def matriz(texto):
    """El QR de `texto`: lista de filas de bool (True = negro), sin margen blanco."""
    datos = list(str(texto).encode("utf-8"))
    ver = version_para(texto)
    cw = _codewords(datos, ver)
    mejor = None
    for mascara in range(8):
        l = _Lienzo(ver)
        l.patrones()
        l.datos(cw)
        l.enmascarar(mascara)
        l.formato(mascara)
        p = penalizacion(l.m)
        if mejor is None or p < mejor[0]:
            mejor = (p, mascara, l.m)
    return mejor[2]


def mascara_elegida(texto):
    """Que mascara gano (para comparar con la app movil)."""
    datos = list(str(texto).encode("utf-8"))
    ver = version_para(texto)
    cw = _codewords(datos, ver)
    puntos = []
    for mascara in range(8):
        l = _Lienzo(ver)
        l.patrones()
        l.datos(cw)
        l.enmascarar(mascara)
        l.formato(mascara)
        puntos.append(penalizacion(l.m))
    return puntos.index(min(puntos))


def como_texto(m):
    return "\n".join("".join("1" if v else "0" for v in fila) for fila in m)
