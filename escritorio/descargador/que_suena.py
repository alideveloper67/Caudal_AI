# -*- coding: utf-8 -*-
"""«¿Qué suena?»: escuchar unos segundos por el micrófono, reconocer la canción
y abrirla en Caudal.

- La grabación usa el micrófono predeterminado de Windows con winmm (ctypes),
  sin QtMultimedia (que la app no lleva): 10 s, mono, 16 kHz, 16 bits → WAV.
- El reconocimiento lo hace la función de Caudal /api/reconocer
  (netlify/functions/reconocer.mjs), que guarda la clave del servicio (AudD o
  ACRCloud). Aquí no hay ninguna clave.
"""

import ctypes
import io
import re
import struct
import sys

import time
import unicodedata
import wave

import requests

from . import nube  # noqa: F401 - pone los certificados de Windows (truststore)

URL = "https://caudal-musica.netlify.app/api/reconocer"
SEGUNDOS = 10
TASA = 16000
NO_DISPONIBLE = "«¿Qué suena?» todavía no está disponible: falta activarlo en el servidor de Caudal."


class ErrorQueSuena(Exception):
    """Algo que se le puede contar tal cual al usuario."""


# ================================================================ WAV

def wav_de_pcm(pcm, tasa=TASA, canales=1):
    """PCM de 16 bits → archivo WAV (bytes)."""
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(canales)
        w.setsampwidth(2)
        w.setframerate(tasa)
        w.writeframes(bytes(pcm))
    return b.getvalue()


def pico(pcm):
    """El valor absoluto más alto de las muestras (0..32768)."""
    n = len(pcm) // 2
    if n == 0:
        return 0
    muestras = struct.unpack(f"<{n}h", bytes(pcm[:n * 2]))
    return max(abs(m) for m in muestras)


def silencio(pcm, umbral=60):
    return pico(pcm) < umbral


# ================================================================ micrófono (winmm)

WAVE_MAPPER = 0xFFFFFFFF
WAVE_FORMAT_PCM = 1
WHDR_DONE = 0x1
MENSAJES_MM = {
    2: "No encontramos ningún micrófono. Conecta uno y vuelve a probar.",
    4: "Otra aplicación está usando el micrófono. Ciérrala y vuelve a probar.",
    6: "El micrófono no tiene controlador. Revisa que esté bien instalado en Windows.",
    32: "El micrófono no acepta este formato de grabación.",
}
PRIVACIDAD = ("No se oyó nada por el micrófono. Revisa que esté conectado y que Windows deje usarlo "
              "(Configuración › Privacidad y seguridad › Micrófono › «Permitir que las aplicaciones de "
              "escritorio accedan al micrófono»).")


class _FORMATO(ctypes.Structure):
    _fields_ = [("wFormatTag", ctypes.c_ushort), ("nChannels", ctypes.c_ushort),
                ("nSamplesPerSec", ctypes.c_ulong), ("nAvgBytesPerSec", ctypes.c_ulong),
                ("nBlockAlign", ctypes.c_ushort), ("wBitsPerSample", ctypes.c_ushort),
                ("cbSize", ctypes.c_ushort)]


class _CABECERA(ctypes.Structure):
    pass


_CABECERA._fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", ctypes.c_ulong),
                      ("dwBytesRecorded", ctypes.c_ulong), ("dwUser", ctypes.c_size_t),
                      ("dwFlags", ctypes.c_ulong), ("dwLoops", ctypes.c_ulong),
                      ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_size_t)]


def _winmm():
    if sys.platform != "win32":
        raise ErrorQueSuena("Grabar con el micrófono solo funciona en Windows.")
    try:
        return ctypes.WinDLL("winmm")
    except OSError as e:
        raise ErrorQueSuena("No se pudo usar el micrófono de Windows.") from e


def grabar(segundos=SEGUNDOS, tasa=TASA, cancelar=None, avance=None):
    """Graba del micrófono predeterminado. Devuelve PCM 16 bits mono (bytes).

    `cancelar`: threading.Event para cortar antes; `avance(fraccion)` se llama
    desde este hilo unas 10 veces por segundo."""
    mm = _winmm()
    if mm.waveInGetNumDevs() == 0:
        raise ErrorQueSuena(MENSAJES_MM[2])
    fmt = _FORMATO(WAVE_FORMAT_PCM, 1, tasa, tasa * 2, 2, 16, 0)
    h = ctypes.c_void_p()
    r = mm.waveInOpen(ctypes.byref(h), ctypes.c_uint(WAVE_MAPPER), ctypes.byref(fmt), None, None, 0)
    if r != 0:
        raise ErrorQueSuena(MENSAJES_MM.get(r, f"No se pudo abrir el micrófono (código {r})."))
    largo = int(segundos * tasa * 2)
    bufer = ctypes.create_string_buffer(largo)
    cab = _CABECERA()
    cab.lpData = ctypes.cast(bufer, ctypes.c_void_p)
    cab.dwBufferLength = largo
    tam = ctypes.sizeof(_CABECERA)
    preparado = False
    try:
        if mm.waveInPrepareHeader(h, ctypes.byref(cab), tam) != 0:
            raise ErrorQueSuena("No se pudo preparar la grabación.")
        preparado = True
        if mm.waveInAddBuffer(h, ctypes.byref(cab), tam) != 0 or mm.waveInStart(h) != 0:
            raise ErrorQueSuena("No se pudo empezar a grabar.")
        inicio = time.monotonic()
        limite = segundos + 4
        while not (cab.dwFlags & WHDR_DONE):
            if cancelar is not None and cancelar.is_set():
                break
            if time.monotonic() - inicio > limite:
                break
            if avance:
                avance(min(1.0, (time.monotonic() - inicio) / segundos))
            time.sleep(0.1)
        mm.waveInStop(h)
        mm.waveInReset(h)          # devuelve el búfer aunque no esté lleno
        espera = time.monotonic()
        while not (cab.dwFlags & WHDR_DONE) and time.monotonic() - espera < 1:
            time.sleep(0.02)
        grabado = int(cab.dwBytesRecorded)
        return bufer.raw[:grabado]
    finally:
        if preparado:
            mm.waveInUnprepareHeader(h, ctypes.byref(cab), tam)
        mm.waveInClose(h)


def grabar_wav(segundos=SEGUNDOS, cancelar=None, avance=None, grabador=None):
    """Graba y devuelve el WAV; lanza ErrorQueSuena si no se oyó nada."""
    pcm = (grabador or grabar)(segundos, TASA, cancelar=cancelar, avance=avance)
    if cancelar is not None and cancelar.is_set():
        return b""
    if len(pcm) < TASA * 2 or silencio(pcm):
        raise ErrorQueSuena(PRIVACIDAD)
    return wav_de_pcm(pcm)


# ================================================================ servidor

_DISPONIBLE = {"valor": None, "hasta": 0.0}


def disponible(sesion=None, ahora=time.monotonic):
    """¿Está activado en el servidor? Se recuerda 10 min (si sí) o 1 min (si no)."""
    if _DISPONIBLE["valor"] is not None and ahora() < _DISPONIBLE["hasta"]:
        return _DISPONIBLE["valor"]
    try:
        r = (sesion or requests).get(URL, timeout=10)
        valor = r.status_code == 200 and bool(r.json().get("disponible"))
    except Exception:  # noqa: BLE001 - sin red: no disponible (se vuelve a mirar pronto)
        valor = False
    _DISPONIBLE["valor"] = valor
    _DISPONIBLE["hasta"] = ahora() + (600 if valor else 60)
    return valor


def olvidar_disponible():
    _DISPONIBLE["valor"] = None


def reconocer(wav, sesion=None):
    """Manda la grabación. Devuelve {encontrada, titulo, artista, album, anio, portada, video_id, consulta}."""
    try:
        r = (sesion or requests).post(URL, data=wav, headers={"content-type": "audio/wav"}, timeout=40)
    except requests.RequestException as e:
        raise ErrorQueSuena("No pudimos hablar con Caudal. Revisa tu internet y vuelve a probar.") from e
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.status_code != 200:
        if r.status_code == 503 and d.get("disponible") is False:
            olvidar_disponible()
            raise ErrorQueSuena(NO_DISPONIBLE)
        raise ErrorQueSuena(str(d.get("mensaje") or "No se pudo reconocer ahora. Vuelve a probar."))
    if not isinstance(d, dict) or not d.get("encontrada"):
        return {"encontrada": False}
    return {
        "encontrada": True,
        "titulo": str(d.get("titulo") or ""), "artista": str(d.get("artista") or ""),
        "album": str(d.get("album") or ""), "anio": str(d.get("anio") or ""),
        "portada": d.get("portada") if str(d.get("portada") or "").startswith("https://") else "",
        "video_id": d.get("video_id") if re.fullmatch(r"[A-Za-z0-9_-]{11}", str(d.get("video_id") or "")) else "",
        "consulta": str(d.get("consulta") or f"{d.get('artista') or ''} {d.get('titulo') or ''}").strip(),
    }


# ================================================================ abrir en Caudal

def _norm(t):
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\((feat|ft|with|con)[^)]*\)|\[[^\]]*\]", " ", t)
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def parecido(resultado, pista):
    """0..1: cuánto se parece una pista del catálogo a lo reconocido."""
    t, a = set(_norm(resultado.get("titulo")).split()), set(_norm(resultado.get("artista")).split())
    pt = set(_norm(pista.get("titulo")).split())
    pa = set(_norm(pista.get("artista")).split())
    s_t = len(t & pt) / len(t) if t else 0
    s_a = len(a & (pa | pt)) / len(a) if a else 0
    return 0.65 * s_t + 0.35 * s_a


def elegir(resultado, pistas):
    """La mejor pista del catálogo para lo reconocido (o None si ninguna se parece)."""
    mejor, puntos = None, 0.0
    for p in pistas or []:
        if not isinstance(p, dict) or p.get("tipo", "pista") != "pista" or not p.get("video_id"):
            continue
        s = parecido(resultado, p)
        if s > puntos:
            mejor, puntos = p, s
    return mejor if puntos >= 0.4 else None


def buscar_en_caudal(resultado, buscar=None):
    """La pista de Caudal de la canción reconocida (o None)."""
    from . import catalogo
    if resultado.get("video_id"):
        artistas = [{"nombre": resultado["artista"], "id": ""}] if resultado.get("artista") else []
        return catalogo.nueva_pista(resultado["video_id"], titulo=resultado.get("titulo") or "",
                                    artistas=artistas)
    buscar = buscar or catalogo.buscar
    try:
        pistas = buscar(resultado.get("consulta") or "", "canciones", 5)
    except Exception:  # noqa: BLE001
        return None
    return elegir(resultado, pistas)

