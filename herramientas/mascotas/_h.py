# ayudante comun: centra filas de texto en un ancho fijo
def mk(W):
    def row(w, l, f='', r=''):
        n = w - len(l) - len(r)
        if n < 0 or (n > 0 and not f):
            raise ValueError(f'fila mal: {l!r} {r!r} w={w}')
        s = l + (f * n if f else '') + r
        a = (W - len(s)) // 2
        return '.' * a + s + '.' * (W - len(s) - a)
    return row


def espejo(mitad, mapa, ancho_mitad):
    """Une una mitad izquierda (texto) con su reflejo derecho, cambiando caracteres con `mapa` (luz/sombra)."""
    out = []
    for i, m in enumerate(mitad):
        if len(m) > ancho_mitad:
            raise ValueError(f'mitad {i} mide {len(m)} > {ancho_mitad}')
        m = m + '.' * (ancho_mitad - len(m))
        d = ''.join(mapa.get(c, c) for c in reversed(m))
        out.append(m + d)
    return out


def banda_der(filas, de, a, n=3, tope='K'):
    """Sombra a mano en el lado derecho: los n pixeles `de` junto al contorno `tope` pasan a `a`."""
    res = []
    for f in filas:
        f = list(f)
        j = max((i for i, c in enumerate(f) if c == tope), default=-1)
        if j > 0:
            k, c = j - 1, 0
            while k >= 0 and c < n and f[k] in (de, a):
                f[k] = a
                k -= 1; c += 1
        res.append(''.join(f))
    return res


def parche(filas, cambios):
    g = [list(f) for f in filas]
    for x, y, c in cambios:
        g[y][x] = c
    return [''.join(f) for f in g]
