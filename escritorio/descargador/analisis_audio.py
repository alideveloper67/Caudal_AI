# -*- coding: utf-8 -*-
"""Tempo (BPM), compás y energía de una canción, a partir de su audio.

Todo en Python puro (sin numpy: la app no lo trae). El audio se decodifica con
el ffmpeg que ya lleva Caudal a 4 kHz mono —basta para el pulso— y se calcula:

* `bpm`: tempo estimado por autocorrelación de la envolvente de ataques,
  afinado con fracciones de retardo;
* `fase`: segundo del primer tiempo fuerte del compás (4/4) para alinear entradas;
* `energia`: 0 a 1 (volumen y ritmo), para ordenar un set de más calmado a más fuerte;
* `perfil`: barras de energía (por defecto 64) para dibujar la «onda».

El resultado se guarda en la colección (tabla `estado`) para no repetir el cálculo.
La parte numérica recibe muestras, así que se prueba con audio sintético.
"""

import math
import os
import time
from array import array
from operator import mul

SR = 4000                 # frecuencia de análisis
SALTO = 40                # muestras por paso de energía: 10 ms
FPS = SR / SALTO          # 100 pasos por segundo
BPM_MIN, BPM_MAX = 70.0, 180.0
MAX_SEGUNDOS = 480        # no se analiza más que esto de una canción
VENTANA_TEMPO = 150       # segundos del centro de la canción que deciden el tempo
CLAVE_CACHE = "analisis_audio"
MAX_CACHE = 600
VERSION_ANALISIS = 2


# ================================================================ numérica

def energias(muestras, salto=SALTO):
    """Energía (raíz cuadrática media) de cada paso de `salto` muestras."""
    n = len(muestras) // salto
    salida = [0.0] * n
    for i in range(n):
        trozo = muestras[i * salto:(i + 1) * salto]
        salida[i] = math.sqrt(sum(map(mul, trozo, trozo)) / salto)
    return salida


def ataques(env):
    """Envolvente de ataques: lo que sube de golpe respecto a lo cercano."""
    n = len(env)
    if n < 4:
        return [0.0] * n
    suave = [0.0] * n
    # media móvil de 60 ms para quitar el ruido fino
    acc = 0.0
    k = 6
    for i in range(n):
        acc += env[i]
        if i >= k:
            acc -= env[i - k]
        suave[i] = acc / min(i + 1, k)
    ataque = [0.0] * n
    for i in range(1, n):
        d = suave[i] - suave[i - 1]
        ataque[i] = d if d > 0 else 0.0
    # se resta la media de alrededor (±0,5 s) para que no manden las partes fuertes
    medio = FPS / 2
    ventana = int(medio)
    pref = [0.0]
    for v in ataque:
        pref.append(pref[-1] + v)
    salida = [0.0] * n
    for i in range(n):
        a, b = max(0, i - ventana), min(n, i + ventana + 1)
        m = (pref[b] - pref[a]) / (b - a)
        v = ataque[i] - m * 1.2
        salida[i] = v if v > 0 else 0.0
    return salida


def _acf(x, lag):
    """Autocorrelación en un retardo entero."""
    return sum(map(mul, x[:-lag], x[lag:]))


def _interp(x, t):
    i = int(t)
    if i < 0 or i + 1 >= len(x):
        return 0.0
    f = t - i
    return x[i] * (1 - f) + x[i + 1] * f


def _acf_frac(x, lag):
    """Autocorrelación en un retardo fraccionario (interpolación lineal)."""
    i = int(lag)
    f = lag - i
    a = sum(map(mul, x[:-i], x[i:])) if i > 0 else 0.0
    b = sum(map(mul, x[:-(i + 1)], x[i + 1:]))
    return a * (1 - f) + b * f


def _peso(bpm):
    """Preferencia suave por tempos habituales (centrada en 120)."""
    return math.exp(-0.5 * (math.log2(bpm / 120.0) / 0.9) ** 2)


def estimar_pulso(ataque, fps=FPS):
    """(bpm, fase en segundos del primer pulso, claridad 0..1) o None.

    La fase es el pulso más fuerte del tramo analizado (se reduce al primer
    pulso del tramo)."""
    n = len(ataque)
    if n < fps * 8:
        return None
    # tramo central: lo que decide el tempo
    largo = int(min(n, VENTANA_TEMPO * fps))
    ini = max(0, (n - largo) // 2)
    x = ataque[ini:ini + largo]
    total = sum(x)
    if total <= 0:
        return None
    lag_min = int(fps * 60.0 / BPM_MAX)
    lag_max = int(fps * 60.0 / BPM_MIN) + 1
    base = _acf(x, 1) if len(x) > 2 else 1.0
    del base
    puntos = []
    for lag in range(lag_min, lag_max + 1):
        bpm = 60.0 * fps / lag
        puntos.append((_acf(x, lag) * _peso(bpm), lag))
    puntos.sort(reverse=True)
    mejor = None
    for _p, lag in puntos[:4]:
        # afinado: décimas de retardo alrededor de lag
        for k in range(-20, 21):
            L = lag + k * 0.05
            if L < lag_min - 0.5 or L > lag_max + 0.5:
                continue
            s = _acf_frac(x, L) * _peso(60.0 * fps / L)
            if mejor is None or s > mejor[0]:
                mejor = (s, L)
    if mejor is None:
        return None
    _s, L = mejor
    bpm = 60.0 * fps / L
    # claridad: cuánto destaca ese retardo sobre la media de los demás
    medias = sum(p for p, _l in puntos) / len(puntos)
    claridad = max(0.0, min(1.0, (mejor[0] - medias) / (abs(mejor[0]) + 1e-9)))
    # fase: de los L posibles desfases, el que reúne más ataques
    periodo = L
    mejor_o, mejor_v = 0.0, -1.0
    pasos = max(1, int(periodo))
    for o in range(pasos):
        v, t = 0.0, float(o)
        while t < len(x) - 1:
            v += _interp(x, t)
            t += periodo
        if v > mejor_v:
            mejor_v, mejor_o = v, float(o)
    # ajuste fino: se buscan los ataques reales junto a cada pulso previsto y se traza
    # la recta tiempo = origen + k * periodo por mínimos cuadrados
    ks, ts = [], []
    k, t = 0, mejor_o
    margen = max(1, int(periodo * 0.3))
    while t < len(x) - margen - 1:
        c = int(round(t))
        a0, b0 = max(0, c - margen), min(len(x), c + margen + 1)
        if b0 - a0 > 2:
            j = max(range(a0, b0), key=lambda q: x[q])
            if x[j] > 0:
                ks.append(k)
                ts.append(float(j))
                t = t + 0.5 * (j - t)       # se sigue al pulso real para no perderlo
        k += 1
        t += periodo
    if len(ks) >= 8:
        mk, mt = sum(ks) / len(ks), sum(ts) / len(ts)
        den = sum((q - mk) ** 2 for q in ks)
        if den > 0:
            pend = sum((q - mk) * (v - mt) for q, v in zip(ks, ts)) / den
            if abs(pend - periodo) < 1.2:
                periodo = pend
                mejor_o = mt - pend * mk
                bpm = 60.0 * fps / periodo
    # el desfase del tramo, llevado al inicio de la canción
    inicio_s = (ini + mejor_o) / fps
    periodo_s = 60.0 / bpm
    fase = inicio_s % periodo_s
    return bpm, fase, claridad


def primer_tiempo_del_compas(ataque, bpm, fase, fps=FPS):
    """De los 4 tiempos del compás, el que lleva más fuerza: es el «uno».
    Devuelve el segundo del primer «uno» de la canción."""
    periodo = 60.0 / bpm
    fuerza = [0.0, 0.0, 0.0, 0.0]
    k = 0
    t = fase
    fin = len(ataque) / fps - 0.05
    while t < fin:
        i = int(t * fps)
        fuerza[k % 4] += max(ataque[max(0, i - 1):i + 2] or [0.0])
        k += 1
        t += periodo
    uno = max(range(4), key=lambda j: fuerza[j])
    return fase + uno * periodo


def perfil_de_energia(env, barras=64):
    """Barras de energía de 0 a 1 para dibujar la canción."""
    n = len(env)
    if n == 0:
        return [0.0] * barras
    salida = []
    for b in range(barras):
        a, c = int(b * n / barras), max(int(b * n / barras) + 1, int((b + 1) * n / barras))
        trozo = env[a:c]
        salida.append(sum(trozo) / len(trozo))
    mx = max(salida) or 1.0
    return [round(v / mx, 3) for v in salida]


def energia_global(env, bpm):
    """0 (calmada) a 1 (explosiva): volumen medio y ritmo."""
    if not env:
        return 0.0
    media = sum(env) / len(env)
    db = 20 * math.log10(media / 32768.0 + 1e-9)
    volumen = max(0.0, min(1.0, (db + 38.0) / 26.0))
    if not bpm:
        return round(volumen, 3)
    ritmo = max(0.0, min(1.0, (bpm - 70.0) / 110.0))
    return round(0.65 * volumen + 0.35 * ritmo, 3)


def analizar_muestras(muestras, sr=SR):
    """Analiza audio mono de 16 bits. Devuelve el dict del análisis o None."""
    if sr != SR:
        raise ValueError("el análisis espera audio a 4000 Hz")
    env = energias(muestras)
    if len(env) < FPS * 8:
        return None
    at = ataques(env)
    pulso = estimar_pulso(at)
    perfil = perfil_de_energia(env)
    if pulso is None:
        return {"bpm": 0.0, "fase": 0.0, "uno": 0.0, "claridad": 0.0,
                "energia": energia_global(env, 0), "perfil": perfil,
                "duracion": round(len(muestras) / sr, 2), "version": VERSION_ANALISIS}
    bpm, fase, claridad = pulso
    uno = primer_tiempo_del_compas(at, bpm, fase)
    return {"bpm": round(bpm, 1), "fase": round(fase, 3), "uno": round(uno, 3),
            "claridad": round(claridad, 3), "energia": energia_global(env, bpm),
            "perfil": perfil, "duracion": round(len(muestras) / sr, 2),
            "version": VERSION_ANALISIS}


# ================================================================ con ffmpeg

def decodificar(fuente, exe, max_segundos=MAX_SEGUNDOS):
    """Audio de la canción en mono a 4 kHz como `array('h')`, o None si falla."""
    import subprocess
    origen = (fuente or {}).get("archivo") or (fuente or {}).get("audio_url") \
        or (fuente or {}).get("url")
    if not exe or not origen:
        return None
    cmd = [exe, "-hide_banner", "-nostats", "-nostdin", "-loglevel", "error"]
    if not (fuente or {}).get("archivo"):
        cab = fuente.get("cabeceras") or {}
        if cab.get("User-Agent"):
            cmd += ["-user_agent", cab["User-Agent"]]
        otras = "".join(f"{k}: {v}\r\n" for k, v in cab.items()
                        if v and k.lower() not in ("user-agent", "accept-encoding"))
        if otras:
            cmd += ["-headers", otras]
        cmd += ["-rw_timeout", "15000000"]
    cmd += ["-t", str(int(max_segundos)), "-i", origen, "-vn", "-sn", "-dn", "-ac", "1",
            "-ar", str(SR), "-f", "s16le", "-"]
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    banderas |= getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120, creationflags=banderas)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or len(r.stdout) < SR * 2 * 8:
        return None
    m = array("h")
    m.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    return m


def analizar_fuente(fuente, exe=None):
    if exe is None:
        from .reproduccion import _ffmpeg_exe
        exe = _ffmpeg_exe()
    m = decodificar(fuente, exe)
    if m is None:
        return None
    return analizar_muestras(m)


# ================================================================ caché

def _clave(pista):
    return str((pista or {}).get("clave") or (pista or {}).get("video_id") or "")


def leer_cache(col):
    return col.estado(CLAVE_CACHE, None) or {}


def analisis_guardado(col, pista):
    a = leer_cache(col).get(_clave(pista))
    if a and a.get("version") == VERSION_ANALISIS:
        return a
    return None


def guardar_analisis(col, pista, datos):
    """Guarda (o corrige a mano) el análisis de una canción."""
    clave = _clave(pista)
    if not clave:
        return
    cache = leer_cache(col)
    cache.pop(clave, None)
    cache[clave] = {**datos, "version": VERSION_ANALISIS, "t": time.time()}
    while len(cache) > MAX_CACHE:
        cache.pop(next(iter(cache)))
    col.guardar_estado(CLAVE_CACHE, cache)


def fuente_local(col, pista):
    """La canción en el disco (descargada o importada), o None. Se llama desde la
    pantalla: toca la colección."""
    a = (pista or {}).get("archivo")
    if a and os.path.exists(a):
        return {"archivo": a}
    if (pista or {}).get("video_id"):
        copia = col.copia_local(pista["video_id"], False)
        if copia:
            return {"archivo": copia[0]}
    return None


def analizar_en_hilo(fuente, pista, ajustes=None, exe=None):
    """El trabajo pesado, para un hilo de fondo (no toca la colección). Si la canción
    no está en el disco pide la dirección de su audio, como al reproducir."""
    if fuente is None and ajustes is not None and (pista or {}).get("video_id"):
        try:
            from . import catalogo
            fuente = dict(catalogo.resolver(pista["video_id"], "audio", ajustes["calidad_audio"],
                                            ajustes["codec_video"], ajustes))
        except Exception:  # noqa: BLE001
            fuente = None
    if fuente is None:
        return None
    return analizar_fuente(fuente, exe)


def analizar_pista(col, pista, exe=None, forzar=False, ajustes=None):
    """El análisis de una canción: de la caché o calculándolo (bloquea: úsalo en un
    hilo o en pruebas). None si no se pudo."""
    if not forzar:
        a = analisis_guardado(col, pista)
        if a:
            return a
    datos = analizar_en_hilo(fuente_local(col, pista), pista, ajustes, exe)
    if datos:
        guardar_analisis(col, pista, datos)
    return datos


def corregir_ritmo(col, pista, bpm):
    """El tempo escrito o «tocado» a mano. Conserva lo ya calculado (perfil, energía); si
    no había análisis, no se sabe dónde cae el compás y la mezcla no se alinea."""
    previo = analisis_guardado(col, pista) or {}
    datos = {"bpm": round(float(bpm), 1), "fase": previo.get("fase", 0.0),
             "uno": previo.get("uno", 0.0), "claridad": 1.0,
             "energia": previo.get("energia", 0.5), "perfil": previo.get("perfil", []),
             "duracion": previo.get("duracion", 0.0), "manual": True,
             "sin_fase": not previo.get("perfil")}
    guardar_analisis(col, pista, datos)
    return datos
