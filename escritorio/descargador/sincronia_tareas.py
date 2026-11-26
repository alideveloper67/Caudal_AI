# -*- coding: utf-8 -*-
"""Lo pesado de poner la letra a tiempo (escuchar, comparar, alinear), sin Qt: lo ejecuta el proceso
ayudante (ayudante.py) para que la interfaz no se entere. Todo lo que entra y sale cabe en JSON.
"""

import difflib

from . import cotejo_audio, sincronia_letra

MIN_VERSOS_TEXTO = 6          # con menos versos no se ponen tiempos
ANCLAS_MIN = 0.45             # parte de los versos que hay que reconocer para fiarse
PARECIDO_PALABRA = 0.74
HUECO_MAX_S = 45.0            # entre dos versos reconocidos no se inventan tiempos más allá de esto
SEG_POR_PALABRA = 0.34
LARGO_MAX_S = 600.0


def verificar(lineas, fuente, duracion, alternativas, datos=None, misma=False, voz=True):
    """Trabajo de fondo: primero se compara el sonido con el de la canción de la que son los tiempos (exacto
    y sin entender la voz); si no se puede, se escucha lo que se canta (sincronia_letra).

    misma: lo que suena ES esa grabación (nada que comparar). voz: hay reconocedor de voz."""
    ref = (datos or {}).get("ref")
    if ref and misma:
        return {"accion": "bien", "desfase_ms": 0, "datos": None, "detalle": "los tiempos son de esta grabación"}
    if ref and datos.get("ref_lineas"):
        try:
            tramos = cotejo_audio.cotejar(fuente, ref)
        except Exception:  # noqa: BLE001  (sin numpy, sin red…: se escucha)
            tramos = None
        if tramos:
            return dict(poner_tramos(datos, tramos), tramos=tramos)
    if not voz:
        return {"accion": "nada", "desfase_ms": 0, "datos": None, "detalle": "sin reconocedor de voz"}
    return sincronia_letra.verificar(lineas, fuente, duracion, alternativas)


def poner_tramos(datos, tramos):
    d = dict(datos, lineas=cotejo_audio.colocar(datos["ref_lineas"], tramos), sincronizada=True)
    for k in ("otra_duracion", "ref", "ref_lineas"):
        d.pop(k, None)
    return {"accion": "cambiar", "desfase_ms": 0, "datos": d, "detalle": f"cotejo {tramos}"}


# ------------------------------------------------------------------ texto sin tiempos

def _parecidas(a, b, memoria):
    if a == b:
        return 1.0
    k = (a, b)
    r = memoria.get(k)
    if r is None:
        if abs(len(a) - len(b)) > 4 or len(a) < 3 or len(b) < 3:
            r = 0.0
        else:
            r = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
            r = r if r >= PARECIDO_PALABRA else 0.0
        memoria[k] = r
    return r


def casar(letra, oidas):
    """Parejas (i, j): la palabra i de la letra es la j de las oídas, en orden (alineación global)."""
    n, m = len(letra), len(oidas)
    if not n or not m:
        return []
    memoria = {}
    previa = [0.0] * (m + 1)
    camino = []
    for i in range(1, n + 1):
        actual = [0.0] * (m + 1)
        fila = bytearray(m + 1)
        a = letra[i - 1]
        peso = 0.6 if len(a) <= 2 else 1.0           # «de», «la»… casan en cualquier sitio: pesan menos
        for j in range(1, m + 1):
            mejor, paso = previa[j], 1
            if actual[j - 1] > mejor:
                mejor, paso = actual[j - 1], 2
            r = _parecidas(a, oidas[j - 1], memoria)
            if r:
                v = previa[j - 1] + r * peso
                if v > mejor:
                    mejor, paso = v, 3
            actual[j], fila[j] = mejor, paso
        camino.append(fila)
        previa = actual
    parejas, i, j = [], n, m
    while i > 0 and j > 0:
        paso = camino[i - 1][j]
        if paso == 3:
            parejas.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif paso == 2:
            j -= 1
        else:
            i -= 1
    parejas.reverse()
    return parejas


def tiempos_de_texto(versos, palabras, duracion=0.0):
    """[(ms, verso)] con los tiempos de lo que se oyó, o None si no hay con qué fiarse.

    versos: las líneas de la letra (texto). palabras: [(segundo, palabra)] de toda la canción."""
    versos = [str(v).strip() for v in versos or [] if str(v).strip()]
    if len(versos) < MIN_VERSOS_TEXTO or not palabras:
        return None
    letra, dueno = [], []
    for k, v in enumerate(versos):
        for w in sincronia_letra.normalizar(v).split():
            letra.append(w)
            dueno.append(k)
    # una palabra oída puede traer varias («pa' que»)
    piezas = [(float(s), x) for s, w in palabras for x in sincronia_letra.normalizar(w).split()]
    parejas = casar(letra, [w for _s, w in piezas])
    primera, largo = {}, {}
    for i, v in enumerate(dueno):
        primera.setdefault(v, i)
        largo[v] = largo.get(v, 0) + 1
    por_verso = {}
    for i, j in parejas:
        por_verso.setdefault(dueno[i], []).append((i - primera[dueno[i]], piezas[j][0]))
    anclas = {}
    for k, casadas in por_verso.items():
        if len(casadas) < max(1, round(largo[k] * 0.4)) or (largo[k] >= 3 and len(casadas) < 2):
            continue
        if casadas[-1][1] - casadas[0][1] > 12.0:
            continue                               # desparramada por media canción: no es el verso
        # cuándo empieza el verso: en su primera palabra; si no se reconoció, contando hacia atrás
        pos, t = casadas[0]
        anclas[k] = max(0.0, t - pos * SEG_POR_PALABRA)
    # tienen que ir en orden: fuera las que rompen la subida
    anclas = _creciente(anclas)
    if len(anclas) < max(MIN_VERSOS_TEXTO, ANCLAS_MIN * len(versos)):
        return None
    salida = []
    claves = sorted(anclas)
    for k in range(len(versos)):
        if k in anclas:
            salida.append((k, anclas[k]))
            continue
        antes = [c for c in claves if c < k]
        despues = [c for c in claves if c > k]
        if antes and despues:
            a, b = antes[-1], despues[0]
            total = sum(largo.get(x, 1) for x in range(a, b)) or 1
            hasta = sum(largo.get(x, 1) for x in range(a, k))
            hueco = anclas[b] - anclas[a]
            if hueco > HUECO_MAX_S:
                # entre medias hay un solo: los versos van a su ritmo detrás del anterior
                t = anclas[a] + hasta * SEG_POR_PALABRA * 1.3
            else:
                t = anclas[a] + hueco * hasta / total
            salida.append((k, t))
        elif antes:
            a = antes[-1]
            t = anclas[a] + sum(largo.get(x, 1) for x in range(a, k)) * SEG_POR_PALABRA * 1.3
            if not duracion or t < duracion - 1.0:
                salida.append((k, t))
        else:
            b = despues[0]
            t = anclas[b] - sum(largo.get(x, 1) for x in range(k, b)) * SEG_POR_PALABRA * 1.3
            if t >= 0:
                salida.append((k, t))
    salida.sort(key=lambda x: (x[1], x[0]))
    return [(int(round(t * 1000)), versos[k]) for k, t in salida]


def _creciente(anclas):
    """Las anclas {verso: segundo} de la cadena más larga en la que el tiempo siempre sube."""
    ks = sorted(anclas)
    if not ks:
        return {}
    mejor = [1] * len(ks)
    previo = [-1] * len(ks)
    for i in range(len(ks)):
        for j in range(i):
            if anclas[ks[j]] < anclas[ks[i]] - 0.15 and mejor[j] + 1 > mejor[i]:
                mejor[i], previo[i] = mejor[j] + 1, j
    i = max(range(len(ks)), key=lambda x: mejor[x])
    salida = {}
    while i >= 0:
        salida[ks[i]] = anclas[ks[i]]
        i = previo[i]
    return salida


def _largo(duracion):
    d = float(duracion or 0)
    return min(LARGO_MAX_S, d + 2.0 if d > 10 else 420.0)


def sincronizar_texto(texto, fuente, duracion):
    """Le pone tiempos a una letra que solo es texto, escuchando la canción entera. {"lineas": […]} o {}."""
    versos = [v for v in (texto or "").splitlines() if v.strip()]
    palabras = sincronia_letra.escuchar(fuente, 0.0, _largo(duracion), sincronia_letra.idioma_de(versos))
    lineas = tiempos_de_texto(versos, palabras, float(duracion or 0))
    return {"lineas": lineas} if lineas else {}


# ------------------------------------------------------------------ ninguna letra en ningún sitio

def transcribir(fuente, duracion):
    """Lo que se canta, según el reconocedor: {"lineas": [(ms, verso)]} o {} si no se entiende bien."""
    return lineas_de_segmentos(sincronia_letra.escuchar_segmentos(fuente, 0.0, _largo(duracion)))


def lineas_de_segmentos(oido):
    """Las frases oídas, solo si el reconocedor está seguro (con mucha música se inventa cosas)."""
    if not oido or not oido.get("segmentos"):
        return {}
    segs = oido["segmentos"]
    buenos = [s for s in segs if s["logprob"] > -0.95 and s["sin_voz"] < 0.6 and s["compresion"] < 2.4]
    dichas = sum(len(s["texto"].split()) for s in buenos)
    if oido.get("idioma_prob", 0) < 0.55 or dichas < 40 or len(buenos) < 0.6 * len(segs):
        return {}
    lineas, anterior, repes = [], None, 0
    for s in buenos:
        for t0, verso in _partir_segmento(s):
            n = sincronia_letra.normalizar(verso)
            repes = repes + 1 if n == anterior else 0
            anterior = n
            if n and repes < 4:                 # el reconocedor se queda en bucle con la música
                lineas.append((int(t0 * 1000), verso))
    distintos = {sincronia_letra.normalizar(t) for _m, t in lineas}
    if len(lineas) < 8 or len(distintos) < 0.35 * len(lineas):
        return {}
    return {"lineas": lineas}


def _partir_segmento(s, tope=8):
    """Un segmento largo, en versos de hasta `tope` palabras (cortando en comas y pausas)."""
    palabras = s.get("palabras") or []
    if not palabras:
        return [(s["desde"], s["texto"].strip())]
    grupos, grupo = [], []
    for i, (t, w) in enumerate(palabras):
        grupo.append((t, w))
        pausa = i + 1 < len(palabras) and palabras[i + 1][0] - t > 0.9
        if len(grupo) >= tope or pausa or (len(grupo) >= 4 and w.strip().endswith((",", ".", "?", "!"))):
            grupos.append(grupo)
            grupo = []
    if grupo:
        if grupos and len(grupo) == 1:
            grupos[-1] += grupo
        else:
            grupos.append(grupo)
    return [(g[0][0], " ".join(w.strip() for _t, w in g).strip()) for g in grupos]


# ------------------------------------------------------------------ lo que se le puede pedir al ayudante

def tarea(nombre, d):
    """Ejecuta una tarea con sus datos (JSON) y devuelve su resultado (JSON)."""
    if nombre == "verificar":
        from . import catalogo
        if d.get("region"):
            catalogo.fijar_region(d["region"])
        pista = d.get("pista") or {}
        datos = d.get("datos") or {}
        for k in ("lineas", "ref_lineas"):
            if datos.get(k):
                datos[k] = [(int(a), str(b)) for a, b in datos[k]]
        lineas = [(int(a), str(b)) for a, b in d.get("lineas") or []]
        otras = d.get("alternativas")
        pedir = (lambda: otras) if otras is not None else (lambda: catalogo.letras_alternativas(pista))
        return verificar(lineas, d["fuente"], d.get("duracion") or 0, pedir, datos, bool(d.get("misma")),
                         bool(d.get("voz", True)))
    if nombre == "sincronizar_texto":
        return sincronizar_texto(d["texto"], d["fuente"], d.get("duracion") or 0)
    if nombre == "transcribir":
        return transcribir(d["fuente"], d.get("duracion") or 0)
    if nombre == "hola":
        return {"hola": True}
    raise ValueError(f"tarea desconocida: {nombre}")
