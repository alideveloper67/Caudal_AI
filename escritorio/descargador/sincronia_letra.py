# -*- coding: utf-8 -*-
"""Letra que cuadra con el audio que suena de verdad.

LRCLIB elige la letra por título y duración, y eso falla: un videoclip y un remix pueden durar lo
mismo y tener otra letra u otros tiempos (medido el 21/11/2026: «La Camisa Negra» en video salía
13 s corrida; «Gasolina», 1 s tarde). Aquí Caudal ESCUCHA un tramo de la canción con un
reconocedor de voz local (faster-whisper, sin internet una vez bajado el modelo), busca en lo que
oye los versos de la letra y calcula cuánto está corrida:

- Si muchos versos coinciden con el mismo corrimiento, se corrige la letra en ese tanto.
- Si casi nada coincide, la letra es de otra versión: se prueban las otras letras de LRCLIB contra
  lo mismo que se oyó (sin volver a escuchar) y se queda la que mejor cuadra.

Todo corre en segundo plano, con prioridad baja y pocos hilos, y solo una vez por canción: el
resultado se guarda. La lógica de alinear es pura y se prueba sin audio (pruebas/test_sincronia_letra.py).
"""

import difflib
import os
import re
import statistics
import threading
import unicodedata

MODELO = "base"              # «tiny» falla mucho con música de fondo; «base» acierta y tarda ~10 s por minuto
TRAMO_S = 70.0               # cuánto se escucha: la primera estrofa y el coro casi siempre
ANTES_S = 12.0               # se empieza un poco antes del primer verso (por si la letra va adelantada)
MIN_PALABRAS_VERSO = 3       # versos más cortos («oh», «yeah») se confunden: no cuentan
PARECIDO_MIN = 0.72          # cuánto se tiene que parecer el verso a lo oído para contar
VENTANA_S = 30.0             # un verso solo se busca a ±30 s de donde dice la letra
GRUPO_S = 0.6                # versos que dan el mismo corrimiento (±0,6 s) se apoyan entre sí
APOYOS_MIN = 4               # con menos versos de acuerdo, no se toca nada
UMBRAL_CORREGIR_S = 0.7      # corrimientos menores son el margen normal del reconocedor: no se tocan
MAX_CORRIMIENTO_S = 25.0

_ES = {"que", "de", "la", "el", "y", "en", "me", "te", "mi", "tu", "lo", "se", "no", "por", "con",
       "una", "un", "los", "las", "para", "si", "yo", "es", "quiero", "como", "pero", "mas", "ya"}
_EN = {"the", "you", "i", "and", "to", "me", "my", "a", "it", "in", "of", "your", "is", "on",
       "that", "be", "love", "we", "all", "baby", "oh", "don't", "can't", "so", "just"}


def normalizar(texto):
    """Minúsculas, sin tildes ni signos: «¡Tití me preguntó!» → «titi me pregunto»."""
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9ñ' ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def idioma_de(versos):
    """'es', 'en' o None, por las palabras más comunes de la letra (para no dejar que el reconocedor
    adivine: con música de fondo adivina mal y transcribe en el idioma equivocado)."""
    palabras = normalizar(" ".join(versos)).split()
    if len(palabras) < 15:
        return None
    es = sum(p in _ES for p in palabras)
    en = sum(p in _EN for p in palabras)
    if es >= 6 and es > en * 1.3:
        return "es"
    if en >= 6 and en > es * 1.3:
        return "en"
    return None


def alinear(lineas, palabras, ventana=None):
    """Compara la letra con lo que se oyó.

    lineas: [(ms, texto)] de la letra sincronizada.
    palabras: [(segundo, palabra)] de lo que se oyó, en el tiempo de la canción.
    ventana: (desde_s, hasta_s) que se escuchó; los versos de fuera no cuentan.

    Devuelve {"corrimiento": s o None, "apoyos": n, "probados": n, "puntaje": 0..1}. El corrimiento es
    cuánto hay que SUMAR a los tiempos de la letra para que caigan donde se canta (negativo: la letra va
    tarde). Cada verso puede casar en varios sitios (un coro se repite): se elige el corrimiento en el que
    se ponen de acuerdo más versos, no el de cada uno por separado."""
    oidas = [(float(s), normalizar(w)) for s, w in palabras or []]
    oidas = [(s, w) for s, w in oidas if w]
    vacio = {"corrimiento": None, "apoyos": 0, "probados": 0, "puntaje": 0.0}
    if len(oidas) < 8:
        return vacio
    tiempos = [s for s, _ in oidas]
    textos = [w for _, w in oidas]
    candidatos = []            # (corrimiento, parecido, índice del verso)
    probados = 0
    for i, (ms, texto) in enumerate(lineas or []):
        ws = normalizar(texto).split()
        if len(ws) < MIN_PALABRAS_VERSO:
            continue
        t = (ms or 0) / 1000.0
        if ventana and not (ventana[0] - VENTANA_S * 0.2 <= t <= ventana[1]):
            continue
        probados += 1
        frase = " ".join(ws)
        n = len(ws)
        for j in range(len(textos)):
            if abs(tiempos[j] - t) > VENTANA_S:
                continue
            # se prueban trozos de lo oído de un largo parecido (el reconocedor junta o parte palabras)
            for largo in (n - 1, n, n + 1):
                if largo < 2 or j + largo > len(textos):
                    continue
                trozo = " ".join(textos[j:j + largo])
                r = difflib.SequenceMatcher(None, frase, trozo, autojunk=False).ratio()
                if r >= PARECIDO_MIN:
                    candidatos.append((tiempos[j] - t, r, i))
    if not candidatos or probados == 0:
        return dict(vacio, probados=probados)
    # el corrimiento con más versos distintos de acuerdo (cada verso vota una vez por grupo)
    mejor = None
    for c, _r, _i in candidatos:
        grupo = {}
        for c2, r2, i2 in candidatos:
            if abs(c2 - c) <= GRUPO_S and r2 > grupo.get(i2, (0, 0))[0]:
                grupo[i2] = (r2, c2)
        puntos = sum(r for r, _ in grupo.values())
        if mejor is None or puntos > mejor[0]:
            mejor = (puntos, grupo)
    _puntos, grupo = mejor
    corr = statistics.median(c for _, c in grupo.values())
    apoyos = len(grupo)
    return {"corrimiento": round(corr, 2), "apoyos": apoyos, "probados": probados,
            "puntaje": round(apoyos / probados, 3)}


def decidir(resultado):
    """Del resultado de `alinear` a qué hacer: ('bien', 0) · ('corregir', ms) · ('otra', 0) · ('nada', 0).
    - bien: cuadra (corrimiento dentro del margen normal).
    - corregir: cuadra entera pero corrida; se mueve la letra.
    - otra: casi nada coincide; puede ser la letra de otra versión.
    - nada: no se pudo saber (se oyó poco: canción instrumental, letra en otro idioma…)."""
    r = resultado or {}
    probados, apoyos, corr = r.get("probados", 0), r.get("apoyos", 0), r.get("corrimiento")
    if probados < APOYOS_MIN:
        return "nada", 0
    if corr is None or apoyos < APOYOS_MIN:
        return ("otra", 0) if probados >= 6 else ("nada", 0)
    if r.get("puntaje", 0) < 0.25:
        return "otra", 0
    if abs(corr) > MAX_CORRIMIENTO_S:
        return "otra", 0
    if abs(corr) < UMBRAL_CORREGIR_S:
        return "bien", 0
    return "corregir", int(round(corr * 1000))


def tramo_a_escuchar(lineas, duracion):
    """(desde, largo) en segundos: desde un poco antes del primer verso con texto."""
    primero = next(((ms or 0) / 1000.0 for ms, tx in lineas or [] if len(normalizar(tx).split()) >= 2), 0.0)
    desde = max(0.0, primero - ANTES_S)
    largo = TRAMO_S
    if duracion:
        largo = max(20.0, min(largo, float(duracion) - desde))
    return round(desde, 2), round(largo, 2)


# ---------------------------------------------------------------- escuchar (con audio de verdad)

_modelo = None
_cerrojo = threading.Lock()


def _importar():
    """faster_whisper importa PyAV (decodificar audio) aunque aquí no se usa: el audio ya llega
    decodificado por el ffmpeg de Caudal. El instalador no lleva PyAV (son ~65 MB); un módulo vacío
    basta para que el import funcione."""
    import sys
    import types
    try:
        import av  # noqa: F401
    except ImportError:
        sys.modules.setdefault("av", types.ModuleType("av"))
    import faster_whisper
    return faster_whisper


def disponible():
    try:
        _importar()
        return True
    except Exception:  # noqa: BLE001
        return False


def _carpeta_modelos():
    from .config import carpeta_datos
    ruta = carpeta_datos() / "modelos"
    ruta.mkdir(parents=True, exist_ok=True)
    return str(ruta)


ARCHIVOS_MODELO = ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt")


def _ruta_modelo():
    """La carpeta del modelo, bajándolo la primera vez (~145 MB). Se baja a una carpeta normal (sin los
    enlaces simbólicos de la caché de Hugging Face, que Windows no deja crear sin ser administrador)."""
    carpeta = os.path.join(_carpeta_modelos(), f"faster-whisper-{MODELO}")
    if all(os.path.exists(os.path.join(carpeta, a)) for a in ARCHIVOS_MODELO):
        return carpeta
    from huggingface_hub import snapshot_download
    snapshot_download(f"Systran/faster-whisper-{MODELO}", local_dir=carpeta,
                      allow_patterns=list(ARCHIVOS_MODELO))
    if not all(os.path.exists(os.path.join(carpeta, a)) for a in ARCHIVOS_MODELO):
        raise OSError("el modelo de voz no se bajó entero")
    return carpeta


def _cargar_modelo():
    """El reconocedor se carga una vez (la primera vez se baja a la carpeta de datos)."""
    global _modelo
    with _cerrojo:
        if _modelo is None:
            WhisperModel = _importar().WhisperModel
            hilos = max(1, min(4, (os.cpu_count() or 2) // 2))
            _modelo = WhisperModel(_ruta_modelo(), device="cpu", compute_type="int8", cpu_threads=hilos)
        return _modelo


def _leer_audio(fuente, desde, largo, exe=None):
    """El tramo de la canción como audio de 16 kHz mono (lo que pide el reconocedor), con ffmpeg sin
    ventana y con la prioridad más baja: es la misma fuente que suena (archivo o stream)."""
    import subprocess
    import numpy as np
    from .reproduccion import _ffmpeg_exe
    exe = exe or _ffmpeg_exe()
    if not exe or not fuente:
        return None
    origen = fuente.get("archivo") or fuente.get("audio_url") or fuente.get("url")
    if not origen:
        return None
    cmd = [exe, "-hide_banner", "-nostats", "-nostdin", "-loglevel", "error"]
    if not fuente.get("archivo"):
        cab = fuente.get("cabeceras") or {}
        if cab.get("User-Agent"):
            cmd += ["-user_agent", cab["User-Agent"]]
        otras = "".join(f"{k}: {v}\r\n" for k, v in cab.items()
                        if v and k.lower() not in ("user-agent", "accept-encoding"))
        if otras:
            cmd += ["-headers", otras]
        cmd += ["-rw_timeout", "15000000"]
    if desde > 0:
        cmd += ["-ss", f"{desde:.2f}"]
    cmd += ["-t", f"{largo:.2f}", "-i", origen, "-vn", "-sn", "-dn",
            "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60, creationflags=banderas)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or len(r.stdout) < 16000 * 4 * 5:      # menos de 5 s: no sirve
        return None
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def escuchar(fuente, desde, largo, idioma=None):
    """[(segundo de la canción, palabra)] de lo que se canta en el tramo, o None si no se pudo."""
    audio = _leer_audio(fuente, desde, largo)
    if audio is None:
        return None
    modelo = _cargar_modelo()
    segmentos, _info = modelo.transcribe(audio, language=idioma, word_timestamps=True, vad_filter=False,
                                         beam_size=1, condition_on_previous_text=False)
    salida = []
    for s in segmentos:
        for w in s.words or []:
            if (w.word or "").strip():
                salida.append((desde + float(w.start), w.word.strip()))
    return salida


def verificar(lineas, fuente, duracion, alternativas=None):
    """Trabajo de fondo: escucha, alinea y decide.

    alternativas: función sin argumentos que devuelve otras letras (formato de catalogo.letras); solo se
    llama si la letra no cuadra.
    Devuelve {"accion": bien|corregir|otra|nada, "desfase_ms": int, "datos": letra nueva o None, "detalle": str}."""
    versos = [tx for _ms, tx in lineas or []]
    desde, largo = tramo_a_escuchar(lineas, duracion)
    palabras = escuchar(fuente, desde, largo, idioma_de(versos))
    if palabras is None:
        return {"accion": "nada", "desfase_ms": 0, "datos": None, "detalle": "no se pudo escuchar"}
    ventana = (desde, desde + largo)
    r = alinear(lineas, palabras, ventana)
    accion, ms = decidir(r)
    detalle = f"{r['apoyos']}/{r['probados']} versos, corrimiento {r['corrimiento']}"
    if accion != "otra" or alternativas is None:
        return {"accion": accion, "desfase_ms": ms, "datos": None, "detalle": detalle}
    # otra versión: la letra que mejor cuadre con lo MISMO que se oyó (sin volver a escuchar)
    mejor = None
    try:
        otras = alternativas() or []
    except Exception:  # noqa: BLE001
        otras = []
    for d in otras:
        if not d.get("sincronizada") or not d.get("lineas"):
            continue
        r2 = alinear(d["lineas"], palabras, ventana)
        a2, ms2 = decidir(r2)
        if a2 in ("bien", "corregir") and (mejor is None or r2["apoyos"] > mejor[0]["apoyos"]):
            mejor = (r2, a2, ms2, d)
    if mejor is None:
        return {"accion": "otra", "desfase_ms": 0, "datos": None, "detalle": detalle + " · ninguna otra cuadra"}
    r2, a2, ms2, d = mejor
    return {"accion": "cambiar", "desfase_ms": ms2, "datos": d,
            "detalle": f"otra letra ({d.get('etiqueta', '')}): {r2['apoyos']}/{r2['probados']} versos"}
