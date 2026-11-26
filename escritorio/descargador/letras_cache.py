# -*- coding: utf-8 -*-
"""Las letras ya encontradas se guardan en el equipo: la segunda vez salen al instante (y sin internet).

Una letra con tiempos vale 60 días; una que solo es texto, 2 días (por si alguien la sincroniza); que no
haya letra, unas horas. Se activa al abrir la app (`activar`); sin eso no guarda ni lee nada.
"""

import hashlib
import json
import os
import threading
import time
from pathlib import Path

from . import disco

DIA = 86400
VALE = {"sinc": 60 * DIA, "oida": 365 * DIA, "duda": 3 * DIA, "texto": 2 * DIA, "nada": 4 * 3600}
MAX_ARCHIVOS = 4000
VERSION = 1

_carpeta = None
_cerrojo = threading.Lock()


def activar(carpeta):
    global _carpeta
    _carpeta = Path(carpeta) / "letras"
    try:
        _carpeta.mkdir(parents=True, exist_ok=True)
    except OSError:
        _carpeta = None


def activa():
    return _carpeta is not None


def _ruta(pista):
    p = pista or {}
    base = p.get("video_id") or p.get("clave") or p.get("archivo") or ""
    if not base or _carpeta is None:
        return None
    # el título va en la firma: si se corrige el de un archivo propio, se busca otra vez
    firma = f"{base}|{p.get('titulo') or ''}|{p.get('artista') or ''}"
    return _carpeta / (hashlib.sha1(firma.encode("utf-8")).hexdigest()[:24] + ".json")


def clase(datos):
    d = datos or {}
    if d.get("sincronizada") and d.get("lineas"):
        if d.get("escuchada"):
            return "oida"
        return "duda" if d.get("otra_duracion") else "sinc"
    return "texto" if (d.get("texto") or "").strip() else "nada"


def leer(pista, caducada=False):
    """La letra guardada de esa pista, o None. Con `caducada`, aunque sea vieja (sin internet)."""
    ruta = _ruta(pista)
    if ruta is None:
        return None
    try:
        with open(ruta, encoding="utf-8") as f:
            g = json.load(f)
        if g.get("v") != VERSION:
            return None
        d = g["datos"]
        if not caducada and time.time() - float(g["cuando"]) > VALE.get(clase(d), 0):
            return None
        for k in ("lineas", "ref_lineas"):
            if d.get(k):
                d[k] = [(int(ms), str(t)) for ms, t in d[k]]
        return d
    except (OSError, ValueError, KeyError, TypeError):
        return None


def guardar(pista, datos):
    ruta = _ruta(pista)
    if ruta is None or not datos:
        return
    try:
        disco.escribir(ruta, json.dumps({"v": VERSION, "cuando": time.time(), "datos": datos}, ensure_ascii=False))
    except (TypeError, ValueError, OSError):
        pass


def olvidar(pista):
    ruta = _ruta(pista)
    try:
        if ruta is not None:
            disco.vaciar(ruta)
            if ruta.exists():
                os.remove(ruta)
    except OSError:
        pass


def podar():
    """Si hay demasiadas, fuera las más viejas (en segundo plano)."""
    if _carpeta is None:
        return
    with _cerrojo:
        try:
            archivos = sorted(_carpeta.glob("*.json"), key=lambda r: r.stat().st_mtime)
            for r in archivos[:max(0, len(archivos) - MAX_ARCHIVOS)]:
                os.remove(r)
        except OSError:
            pass
