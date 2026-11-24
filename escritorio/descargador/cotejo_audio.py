# -*- coding: utf-8 -*-
"""Dónde cae una grabación dentro de otra, comparando su sonido (mismas cuentas en la app:
app/lib/nucleo/cotejo_audio.dart).

Un videoclip lleva la misma grabación que la canción oficial, pero con intro, escenas o cortes; la
canción oficial trae la letra con sus tiempos. Comparando los golpes de cada banda de frecuencia se
sabe al centésimo cuánto está corrida una respecto a la otra, sin entender lo que se canta (medido el
23/11/2026 con 18 videos: parecido 0,80-0,98; «Bendecido» +4,22 s, «666» +3,64 s).
"""

HZ = 8000
SALTO = 160                  # 20 ms
VENTANA = 1024
BANDAS = 16
TROZO_S = 25                 # cada trozo que se busca
ESCUCHA_S = 150              # cuánto se baja de cada una
PARECIDO_MIN = 0.62          # menos: no es la misma grabación


def rasgos(muestras):
    """Los golpes (subidas de energía) de cada banda, cada 20 ms: matriz BANDAS x cuadros."""
    import numpy as np
    x = np.asarray(muestras, dtype=np.float32)
    n = 1 + (len(x) - VENTANA) // SALTO
    if n < 50:
        return None
    w = np.hanning(VENTANA).astype(np.float32)
    bordes = np.round(np.geomspace(150, 3600, BANDAS + 1) / (HZ / VENTANA)).astype(int)
    m = np.zeros((BANDAS, n), np.float32)
    for k in range(0, n, 2000):
        idx = np.arange(VENTANA)[None] + SALTO * np.arange(k, min(n, k + 2000))[:, None]
        p = np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2
        for b in range(BANDAS):
            m[b, k:k + len(p)] = np.log(1e-7 + p[:, bordes[b]:max(bordes[b] + 1, bordes[b + 1])].mean(1))
    d = np.maximum(0, np.diff(m, axis=1, prepend=m[:, :1]))
    d -= d.mean(1, keepdims=True)
    d /= d.std(1, keepdims=True) + 1e-6
    return d


def _parecido_en(t, a, p):
    """Parecido (-1..1) del trozo `t` puesto en el cuadro `p` de `a`."""
    import numpy as np
    largo = t.shape[1]
    i, j = max(0, p), min(a.shape[1], p + largo)
    if j - i < largo * 0.3:
        return 0.0
    ta, aa = t[:, i - p:j - p], a[:, i:j]
    return float((ta * aa).sum() / np.sqrt((ta ** 2).sum() * (aa ** 2).sum() + 1e-9))


def desfases(v, a):
    """[(segundo de V, cuánto hay que sumar a los tiempos de A para caer en V)] por tramos, o None si no
    son la misma grabación. Con un solo corrimiento (lo normal) devuelve un solo tramo."""
    import numpy as np
    largo = TROZO_S * HZ // SALTO
    if v is None or a is None or v.shape[1] < largo * 0.6 or a.shape[1] < largo * 0.6:
        return None
    largo = min(largo, v.shape[1], a.shape[1])
    tam = 1 << int(np.ceil(np.log2(a.shape[1] + largo)))
    fa = [np.fft.rfft(a[b], tam) for b in range(BANDAS)]
    hallados = []                                  # (cuadro de V, corrimiento en cuadros, parecido)
    trozos = list(range(0, v.shape[1] - largo + 1, largo))
    for ini in trozos:
        t = v[:, ini:ini + largo]
        s = np.zeros(tam)
        for b in range(BANDAS):
            s += np.fft.irfft(fa[b] * np.conj(np.fft.rfft(t[b], tam)), tam)
        s = np.concatenate([s[-largo:], s[:a.shape[1]]])
        p = int(np.argmax(s)) - largo
        hallados.append((ini, ini - p, _parecido_en(t, a, p)))
    buenos = [h for h in hallados if h[2] >= PARECIDO_MIN]
    if not buenos:
        return None
    # el corrimiento en el que más trozos se ponen de acuerdo (±0,1 s); una música que se repite puede
    # encajar igual de bien en otro compás: si en el común casi se parece lo mismo, vale el común
    comun = max((h[1] for h in buenos), key=lambda c: sum(h[2] for h in buenos if abs(h[1] - c) <= 5))
    iguales = [h for h in buenos if abs(h[1] - comun) <= 5]
    comun = int(round(float(np.median([h[1] for h in iguales]))))
    tramos = []
    for ini, c, r in hallados:
        aqui = max(_parecido_en(v[:, ini:ini + largo], a, ini - comun - d) for d in (-2, -1, 0, 1, 2))
        if r < PARECIDO_MIN and aqui < PARECIDO_MIN:
            continue                               # silencio, escena hablada: no dice nada
        tramos.append((ini, comun if aqui >= r * 0.85 or r < PARECIDO_MIN else c))
    if len(iguales) < 2 and len(hallados) > 2:
        return None                                # un solo trozo de acuerdo: no basta
    if sum(c == comun for _i, c in tramos) >= 0.7 * len(tramos):
        return [(0.0, comun * SALTO / HZ)]
    # varios corrimientos: la grabación va cortada. Tienen que ir en orden o no se puede fiar
    salida = []
    for ini, c in tramos:
        if not salida or abs(salida[-1][1] - c * SALTO / HZ) > 0.1:
            salida.append((ini * SALTO / HZ, c * SALTO / HZ))
    en_a = [t - c for t, c in salida]
    if len(salida) > 4 or en_a != sorted(en_a):
        return None
    salida[0] = (0.0, salida[0][1])
    return salida


def colocar(lineas, tramos):
    """Las líneas [(ms, texto)] de A, puestas donde caen en V."""
    salida = []
    for ms, texto in lineas or []:
        t = None
        for i, (desde, c) in enumerate(tramos):
            hasta = tramos[i + 1][0] if i + 1 < len(tramos) else float("inf")
            x = ms / 1000.0 + c
            if x < hasta or t is None:
                t = min(x, hasta)
            if x < hasta:
                break
        salida.append((max(0, int(round(t * 1000))), texto))
    return salida


def _muestras(fuente):
    from . import sincronia_letra
    import numpy as np
    x = sincronia_letra._leer_audio(fuente, 0, ESCUCHA_S, hz=HZ)
    return None if x is None else np.asarray(x)


def cotejar(fuente, video_id):
    """Los tramos (ver `desfases`) de lo que suena (`fuente`) respecto al audio de YouTube `video_id`, o
    None. Baja poco: la pista más ligera y solo los primeros minutos."""
    from . import catalogo
    x = _muestras(fuente)
    if x is None:
        return None
    for intento in range(2):
        try:
            y = _muestras(catalogo.resolver(video_id, modo="audio", calidad="ahorro"))
        except Exception:  # noqa: BLE001
            y = None
        if y is not None:
            return desfases(rasgos(x), rasgos(y))
        catalogo.olvidar(video_id)            # el enlace guardado pudo caducar: uno nuevo
    return None
