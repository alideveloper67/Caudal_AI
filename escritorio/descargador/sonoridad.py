# -*- coding: utf-8 -*-
"""Volumen máximo sin distorsión: cuánto subir (o bajar) cada canción y cómo limitar sus picos.

Cómo funciona
-------------
* Cada canción se mide una vez (sonoridad integrada en LUFS y pico verdadero en dBTP, con el
  filtro `ebur128` del ffmpeg de Caudal) y el resultado queda guardado.
* La ganancia de una canción es la que la lleva al objetivo del nivel elegido (Normal, Alto o
  Máximo), con un tope: el limitador solo puede «comerse» unos pocos dB de picos (0, 3 o 6 según
  el nivel). Así las canciones grabadas bajas suben hasta sonar como las fuertes, pero nunca se
  aplastan hasta distorsionar.
* Detrás va un limitador de picos verdaderos con sobremuestreo x4: la ganancia extra no recorta
  (medido: sin sobremuestreo un ruido rosa a -1 dBFS llegaba a +0,2 dBTP; con él, -0,6 dBTP).
* La ganancia es fija para toda la canción: nada de «bombeo» (subir y bajar dentro de la canción).

Todo lo de este archivo es lógica pura (sin Qt) salvo `medir`, que llama a ffmpeg.
"""

import math
import os
import re
import time

# nivel -> (objetivo en LUFS integrados, dB que el limitador puede recortar como mucho)
NIVELES = {
    "normal": (-14.0, 0.0),
    "alto": (-10.0, 3.0),
    "maximo": (-8.0, 6.0),
}
NOMBRES_NIVEL = {"normal": "Normal", "alto": "Alto", "maximo": "Máximo"}
NIVEL_POR_DEFECTO = "alto"
TECHO_DBTP = -1.0               # los picos verdaderos nunca pasan de aquí
LIMITE_LIMITADOR = 0.871        # -1,2 dBFS en el limitador x4: con margen para quedar bajo -1 dBTP
GANANCIA_MAX = 12.0
GANANCIA_MIN = -12.0
# sin medir todavía: lo típico de la música publicada hoy (master fuerte, picos casi a 0 dBFS)
LUFS_SUPUESTO = -9.0
PICO_SUPUESTO = -0.5
CLAVE_CACHE = "sonoridad"
MAX_CACHE = 2000
VERSION = 1

# lo que hacía antes el súper volumen (0..4) -> nivel nuevo, para quien ya lo tenía puesto
DESDE_SUPER_VOLUMEN = {1: "alto", 2: "alto", 3: "maximo", 4: "maximo"}
# y al revés: la clave antigua se sigue escribiendo para que otras versiones y el icono sepan
A_SUPER_VOLUMEN = {"no": 0, "normal": 1, "alto": 2, "maximo": 4}


def nivel_efectivo(ajustes):
    """'normal' | 'alto' | 'maximo' o None (sin tocar el volumen de las canciones).

    `volumen_maximo` manda; si está apagado, «Igualar el volumen entre canciones» equivale
    al nivel Normal (iguala sin forzar nada)."""
    try:
        v = ajustes["volumen_maximo"]
    except (KeyError, TypeError):
        v = None
    if v in NIVELES:
        return v
    if v in (None, ""):
        # ajustes de una versión anterior: el súper volumen antiguo
        try:
            antiguo = int(ajustes["super_volumen"] or 0)
        except (KeyError, TypeError, ValueError):
            antiguo = 0
        if antiguo in DESDE_SUPER_VOLUMEN:
            return DESDE_SUPER_VOLUMEN[antiguo]
    try:
        return "normal" if ajustes["normalizar"] else None
    except (KeyError, TypeError):
        return None


def poner_nivel(ajustes, nivel):
    """Guarda el nivel (o 'no') y mantiene la clave antigua al día."""
    nivel = nivel if nivel in NIVELES else "no"
    ajustes["volumen_maximo"] = nivel
    ajustes["super_volumen"] = A_SUPER_VOLUMEN[nivel]


def migrar(datos):
    """Al cargar unos ajustes guardados por una versión sin «Volumen máximo»: quien tenía el
    súper volumen encendido conserva un nivel parecido. Devuelve True si cambió algo."""
    if "volumen_maximo" in datos:
        return False
    try:
        antiguo = int(datos.get("super_volumen") or 0)
    except (TypeError, ValueError):
        antiguo = 0
    if antiguo in DESDE_SUPER_VOLUMEN:
        datos["volumen_maximo"] = DESDE_SUPER_VOLUMEN[antiguo]
        return True
    if datos.get("normalizar") is False:
        # había apagado a propósito el igualar volumen: no se le cambia el sonido sin preguntar
        datos["volumen_maximo"] = "no"
        return True
    return False


def ganancia_db(nivel, lufs=None, pico=None, extra_db=0.0):
    """dB que se le aplican a una canción.

    nivel: 'normal' | 'alto' | 'maximo' (o None: 0 dB).
    lufs, pico: lo medido (sonoridad integrada y pico verdadero); None si aún no se sabe.
    extra_db: lo que suman otros ajustes antes del limitador (preamplificador, margen del ecualizador).
    """
    if nivel not in NIVELES:
        return 0.0
    objetivo, presupuesto = NIVELES[nivel]
    lufs = LUFS_SUPUESTO if lufs is None or not math.isfinite(lufs) else float(lufs)
    pico = PICO_SUPUESTO if pico is None or not math.isfinite(pico) else float(pico)
    g = objetivo - lufs
    # el limitador puede recortar como mucho `presupuesto` dB de picos (contando el preamplificador)
    tope = (TECHO_DBTP - pico) + presupuesto - float(extra_db or 0.0)
    g = min(g, tope)
    return round(max(GANANCIA_MIN, min(GANANCIA_MAX, g)), 2)


def partes_limitador():
    """Limitador de picos verdaderos: sobremuestrea x4, limita y vuelve a 48 kHz."""
    return ["aresample=192000",
            f"alimiter=limit={LIMITE_LIMITADOR}:attack=5:release=60:level=disabled",
            "aresample=48000"]


def partes_ganancia(db):
    return [f"volume={db:.2f}dB"] if abs(db) >= 0.05 else []


# ================================================================ medir

_RE_I = re.compile(r"I:\s+(-?[\d.]+|-inf) LUFS")
_RE_PICO = re.compile(r"Peak:\s+(-?[\d.]+|-inf) dBFS")


def leer_resumen_ebur128(texto):
    """(LUFS integrados, pico verdadero dBTP) del resumen final de `ebur128`, o None."""
    i = _RE_I.findall(texto or "")
    p = _RE_PICO.findall(texto or "")
    if not i:
        return None
    try:
        lufs = float(i[-1])
    except ValueError:
        return None
    if not math.isfinite(lufs) or lufs < -70:
        return None                       # silencio: no hay nada que igualar
    pico = None
    if p:
        try:
            pico = float(p[-1])
        except ValueError:
            pico = None
        if pico is not None and not math.isfinite(pico):
            pico = None
    return round(lufs, 2), (round(pico, 2) if pico is not None else None)


def orden_medir(fuente, exe):
    """La orden de ffmpeg que mide una canción (archivo o dirección de la plataforma)."""
    origen = (fuente or {}).get("archivo") or (fuente or {}).get("audio_url") \
        or (fuente or {}).get("url")
    if not exe or not origen:
        return None
    cmd = [exe, "-hide_banner", "-nostats", "-nostdin", "-loglevel", "info"]
    if not (fuente or {}).get("archivo"):
        cab = (fuente or {}).get("cabeceras") or {}
        if cab.get("User-Agent"):
            cmd += ["-user_agent", cab["User-Agent"]]
        otras = "".join(f"{k}: {v}\r\n" for k, v in cab.items()
                        if v and k.lower() not in ("user-agent", "accept-encoding"))
        if otras:
            cmd += ["-headers", otras]
        cmd += ["-rw_timeout", "15000000"]
    cmd += ["-t", "900", "-i", origen, "-vn", "-sn", "-dn",
            "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"]
    return cmd


def medir(fuente, exe=None, timeout=120):
    """Mide una canción con ffmpeg (bloquea: para un hilo de fondo). (lufs, pico) o None."""
    import subprocess
    if exe is None:
        from .reproduccion import _ffmpeg_exe
        exe = _ffmpeg_exe()
    cmd = orden_medir(fuente, exe)
    if not cmd:
        return None
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    banderas |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=timeout, creationflags=banderas)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return leer_resumen_ebur128(r.stderr)


# ================================================================ caché

def clave_de(fuente=None, pista=None):
    """La canción, la toque desde el disco o desde internet: su video_id si lo tiene."""
    for d in (pista or {}, (fuente or {}).get("info") or {}, fuente or {}):
        vid = d.get("video_id")
        if vid:
            return f"yt:{vid}"
    arch = (fuente or {}).get("archivo") or (pista or {}).get("archivo")
    if arch:
        return "archivo:" + os.path.normcase(os.path.abspath(arch))
    return ""


class CacheSonoridad:
    """Lo medido, en memoria y en la colección (tabla `estado`)."""

    def __init__(self, coleccion=None):
        self.col = coleccion
        self.datos = {}
        if coleccion is not None:
            try:
                self.datos = dict(coleccion.estado(CLAVE_CACHE, None) or {})
            except Exception:  # noqa: BLE001
                self.datos = {}

    def leer(self, clave):
        d = self.datos.get(clave) if clave else None
        if not d or d.get("v") != VERSION:
            return None
        return d.get("i"), d.get("p")

    def guardar(self, clave, medida):
        if not clave or not medida:
            return
        self.datos.pop(clave, None)
        self.datos[clave] = {"i": medida[0], "p": medida[1], "v": VERSION, "t": round(time.time())}
        while len(self.datos) > MAX_CACHE:
            self.datos.pop(next(iter(self.datos)))
        if self.col is not None:
            try:
                self.col.guardar_estado(CLAVE_CACHE, self.datos)
            except Exception:  # noqa: BLE001
                pass


# ================================================================ descargas

def filtro_descarga(medida, nivel="maximo"):
    """Filtro de ffmpeg para dejar un archivo descargado fuerte y parejo (ganancia fija + limitador),
    o el de respaldo si no se pudo medir."""
    if not medida:
        # sin medida: un loudnorm suave (corrige poco a poco) mejor que nada
        return "loudnorm=I=-10:TP=-1.0:LRA=11"
    g = ganancia_db(nivel, medida[0], medida[1])
    partes = partes_ganancia(g) + partes_limitador()
    return ",".join(partes)


def args_descarga(formato_audio, acodec, medida, nivel="maximo"):
    """Lo que se le pasa a la extracción de audio de yt-dlp en el «modo música».

    Si el formato pedido es el mismo que el descargado (M4A desde AAC, OPUS desde Opus, «original»),
    yt-dlp copiaría la pista sin tocarla y el filtro no se puede aplicar a una copia: se recodifica
    a una tasa alta (AAC 256 kb/s, Opus 192 kb/s) para que la pérdida no se note."""
    args = ["-af", filtro_descarga(medida, nivel)]
    c = str(acodec or "").lower()
    if formato_audio == "m4a" or (formato_audio == "original" and c.startswith("mp4a")):
        args += ["-c:a", "aac", "-b:a", "256k"]
    elif formato_audio in ("opus", "original"):
        args += ["-c:a", "libopus", "-b:a", "192k"]
    return args
