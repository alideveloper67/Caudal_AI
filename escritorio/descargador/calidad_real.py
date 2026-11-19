# -*- coding: utf-8 -*-
"""La insignia de calidad real: códec y tasa del audio que el motor decodifica de verdad (sin Qt).

Los datos vienen de mpv (`audio-codec-name`, `audio-params`, `audio-bitrate`), no de lo que anunciaba la
plataforma: es lo que está sonando. `etiqueta()` da el texto corto de la barra y `ayuda()` el detalle."""

NOMBRES_CODEC = {
    "aac": "AAC", "aac_latm": "AAC", "mp3": "MP3", "mp3float": "MP3", "mp2": "MP2", "opus": "OPUS",
    "vorbis": "OGG", "flac": "FLAC", "alac": "ALAC", "ac3": "AC3", "eac3": "E-AC3", "wmav2": "WMA",
    "wmav1": "WMA", "wmapro": "WMA", "wavpack": "WV", "ape": "APE", "dts": "DTS", "truehd": "TrueHD",
}
SIN_PERDIDA = {"FLAC", "ALAC", "WAV", "WV", "APE", "TrueHD"}
CANALES = {"mono": "mono", "stereo": "estéreo", "2.1": "2.1", "5.1": "5.1", "7.1": "7.1"}


def nombre_codec(codec):
    c = str(codec or "").strip().lower()
    if not c:
        return ""
    if c.startswith("pcm_") or c in ("pcm", "wav"):
        return "WAV"
    return NOMBRES_CODEC.get(c, c.upper())


def texto_khz(hz):
    """44100 -> «44,1 kHz»; 48000 -> «48 kHz»; vacío si no hay dato."""
    try:
        hz = float(hz)
    except (TypeError, ValueError):
        return ""
    if hz <= 0:
        return ""
    k = hz / 1000.0
    texto = f"{k:.1f}".rstrip("0").rstrip(".") if abs(k - round(k)) > 0.04 else f"{round(k)}"
    return texto.replace(".", ",") + " kHz"


def _kbps(bits):
    try:
        v = float(bits)
    except (TypeError, ValueError):
        return 0
    return int(round(v / 1000.0)) if v > 0 else 0


def _bits(codec, formato):
    """Profundidad de bits que se puede afirmar: de pcm_sNNle o de un formato s16/s24 (s32 puede ser 24 real)."""
    c = str(codec or "").lower()
    if c.startswith("pcm_"):
        for n in (8, 16, 24, 32, 64):
            if f"{n}" in c:
                return n
    f = str(formato or "").lower().rstrip("p")
    return {"s16": 16, "s24": 24}.get(f, 0)


def interpretar(datos):
    """Los datos de mpv a un diccionario limpio: codec, hz, kbps, bits, canales, sin_perdida. {} si no hay audio."""
    datos = datos or {}
    params = datos.get("params") or {}
    codec = nombre_codec(datos.get("codec"))
    hz = params.get("samplerate") or 0
    if not codec and not hz:
        return {}
    kbps = _kbps(datos.get("bitrate"))
    sin_perdida = codec in SIN_PERDIDA
    bits = _bits(datos.get("codec"), params.get("format")) if sin_perdida else 0
    canales = CANALES.get(str(params.get("channels") or ""), str(params.get("channels") or ""))
    return {"codec": codec, "hz": int(hz or 0), "kbps": kbps, "bits": bits, "canales": canales,
            "sin_perdida": sin_perdida}


def etiqueta(datos):
    """El texto corto de la insignia: «OPUS 160 kbps», «FLAC 16/44,1» o «AAC 48 kHz»."""
    d = interpretar(datos)
    if not d:
        return ""
    codec = d["codec"] or "AUDIO"
    khz = texto_khz(d["hz"])
    if d["sin_perdida"]:
        if d["bits"] and khz:
            return f"{codec} {d['bits']}/{khz.replace(' kHz', '')}"
        return f"{codec} {khz}".strip()
    if d["kbps"] >= 8:
        return f"{codec} {d['kbps']} kbps"
    return f"{codec} {khz}".strip()


def ayuda(datos):
    """El detalle para el globito de la insignia."""
    d = interpretar(datos)
    if not d:
        return ""
    partes = [f"Audio {d['codec'] or 'desconocido'}" + (" (sin pérdida)" if d["sin_perdida"] else "")]
    if d["kbps"] >= 8:
        partes.append(f"{d['kbps']} kbps")
    khz = texto_khz(d["hz"])
    if khz:
        partes.append(khz)
    if d["bits"]:
        partes.append(f"{d['bits']} bits")
    if d["canales"]:
        partes.append(d["canales"])
    return " · ".join(partes) + "\nLo que el motor decodifica ahora mismo."
