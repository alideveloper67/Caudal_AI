# -*- coding: utf-8 -*-
"""Avisos que Caudal manda a todas las apps sin sacar una versión nueva (igual que
app/lib/nucleo/avisos.dart).

Viven en la tabla `avisos` de la nube (supabase/avisos.sql) y se envían con
herramientas/enviar_aviso.py. La app los lee al abrirse y muestra cada uno UNA sola vez en este
equipo; sin conexión, simplemente no sale ninguno."""

import json

import requests

from . import nube
from .config import carpeta_datos

PLATAFORMA = "windows"


def _archivo():
    return carpeta_datos() / "avisos_vistos.json"


def vistos():
    try:
        datos = json.loads(_archivo().read_text(encoding="utf-8"))
        return {int(x) for x in datos if str(x).lstrip("-").isdigit()}
    except (OSError, ValueError, TypeError):
        return set()


def marcar_visto(id_):
    """Que este equipo ya lo vio: no vuelve a salir."""
    try:
        v = vistos() | {int(id_)}
        _archivo().write_text(json.dumps(sorted(v)), encoding="utf-8")
    except (OSError, ValueError):
        pass


def aviso_de(fila):
    """Un aviso limpio, o None si la fila no sirve (sin id, título o texto)."""
    if not isinstance(fila, dict):
        return None
    id_ = fila.get("id")
    titulo = str(fila.get("titulo") or "").strip()
    texto = str(fila.get("texto") or "").strip()
    if isinstance(id_, bool) or not isinstance(id_, (int, float)) or not titulo or not texto:
        return None
    enlace = str(fila.get("enlace") or "").strip()
    etiqueta = str(fila.get("etiqueta_enlace") or "").strip()
    plat = fila.get("plataformas")
    return {
        "id": int(id_),
        "titulo": titulo,
        "texto": texto,
        "plataformas": [str(p).lower() for p in plat] if isinstance(plat, list) and plat else ["todas"],
        # solo https: un aviso nunca abre otra cosa
        "enlace": enlace if enlace.startswith("https://") else None,
        "etiqueta": etiqueta or None,
    }


def pendientes(plataforma=PLATAFORMA, sesion=None):
    """Los avisos vigentes de [plataforma] que este equipo aún no vio, del más viejo al más nuevo.
    Nunca lanza: con cualquier fallo devuelve una lista vacía."""
    try:
        r = (sesion or requests).get(
            f"{nube.URL}/rest/v1/avisos",
            params={"select": "id,titulo,texto,plataformas,enlace,etiqueta_enlace", "order": "id.asc"},
            headers={"apikey": nube.CLAVE_PUBLICA, "Authorization": f"Bearer {nube.CLAVE_PUBLICA}"},
            timeout=10)
        if r.status_code != 200:
            return []
        datos = r.json()
    except (requests.RequestException, ValueError):
        return []
    if not isinstance(datos, list):
        return []
    ya = vistos()
    salida = []
    for f in datos:
        a = aviso_de(f)
        if a and a["id"] not in ya and ("todas" in a["plataformas"] or plataforma in a["plataformas"]):
            salida.append(a)
    return salida
