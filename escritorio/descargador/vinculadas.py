# -*- coding: utf-8 -*-
"""Lo que Caudal recuerda de cada cuenta vinculada (Spotify, YouTube y SoundCloud).

Aquí NO hay tokens (esos viven en el disco del perfil, ver servicios_externos): solo cuándo se
sincronizó, cuántas canciones entraron y qué canciones del otro servicio ya se trajeron, para no
volver a buscarlas. Todo va en el «estado» de la colección, que ni se sube a la nube ni entra en la
copia de seguridad.
"""

import time

SERVICIOS = ("spotify", "youtube", "soundcloud")
NOMBRES = {"spotify": "Spotify", "youtube": "YouTube Music", "soundcloud": "SoundCloud"}
CADA_SEG = 12 * 3600          # «Mantener al día»: como mucho una vez cada 12 horas
MAX_FALLOS = 3                # una canción que no está se busca tres veces y no más
TOPE_SILENCIOSO = 500         # por vez, sin que la persona lo pida


def _clave(servicio):
    return f"vinculada_{servicio}"


def _clave_traidas(servicio):
    return f"vinculada_{servicio}_traidas"


def info(col, servicio):
    """{'mantener', 'ultima', 'cuantas', 'completa'} (con sus valores por defecto)."""
    d = col.estado(_clave(servicio), None)
    d = d if isinstance(d, dict) else {}
    return {"mantener": bool(d.get("mantener", True)), "ultima": float(d.get("ultima") or 0),
            "cuantas": int(d.get("cuantas") or 0), "completa": bool(d.get("completa"))}


def anotar(col, servicio, **cambios):
    d = dict(info(col, servicio), **cambios)
    col.guardar_estado(_clave(servicio), d)
    return d


def olvidar(col, servicio):
    """Al desvincular: se olvida todo lo de esa cuenta (las canciones traídas se quedan)."""
    col.guardar_estado(_clave(servicio), None)
    col.guardar_estado(_clave_traidas(servicio), None)


def _traidas(col, servicio):
    d = col.estado(_clave_traidas(servicio), None)
    d = d if isinstance(d, dict) else {}
    return set(d.get("hechas") or []), dict(d.get("fallos") or {})


def conocidas(col, servicio):
    """Las canciones que ya se trajeron (o que se buscaron varias veces y no están)."""
    hechas, fallos = _traidas(col, servicio)
    return hechas | {k for k, n in fallos.items() if n >= MAX_FALLOS}


def anotar_traidas(col, servicio, encontradas, no_encontradas=()):
    hechas, fallos = _traidas(col, servicio)
    for k in encontradas:
        if k:
            hechas.add(k)
            fallos.pop(k, None)
    for k in no_encontradas:
        if k and k not in hechas:
            fallos[k] = int(fallos.get(k) or 0) + 1
    col.guardar_estado(_clave_traidas(servicio), {"hechas": sorted(hechas), "fallos": fallos})


def nuevas(canciones, ya):
    """Las que aún no se conocen (sin repetir dentro de la misma tanda)."""
    salida, vistas = [], set()
    for c in canciones or []:
        k = c.get("externa")
        if k and (k in ya or k in vistas):
            continue
        if k:
            vistas.add(k)
        salida.append(c)
    return salida


def toca_sincronizar(col, servicio, ahora=None):
    d = info(col, servicio)
    return d["mantener"] and (ahora or time.time()) - d["ultima"] >= CADA_SEG


def hace_cuanto(ts, ahora=None):
    if not ts:
        return "aún no se sincroniza"
    s = max(0, (ahora or time.time()) - ts)
    if s < 90:
        return "hace un momento"
    if s < 3600:
        return f"hace {int(s // 60)} min"
    if s < 86400:
        h = int(s // 3600)
        return f"hace {h} {'hora' if h == 1 else 'horas'}"
    d = int(s // 86400)
    return f"hace {d} {'día' if d == 1 else 'días'}"
