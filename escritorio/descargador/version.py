# -*- coding: utf-8 -*-
"""Version de Caudal Escritorio y comprobacion de actualizaciones.

Las actualizaciones se publican como *releases* de un repositorio de GitHub.
Cada release debe llevar adjunto el instalador (CaudalInstalador.exe) y, si
quieres, el APK del telefono. La app mira si hay una version mas nueva y se
ofrece a instalarla sola.

Para cambiar donde se publica basta con tocar ORIGEN.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

VERSION = "2.0.0"

# usuario/repositorio de GitHub donde publicas las versiones
ORIGEN = "alideveloper67/Caudal_AI"

# el mismo repositorio publica el escritorio y el movil: cada app solo hace
# caso a las versiones con su etiqueta (escritorio-v2.1.0, movil-v1.0.0)
PREFIJO = "escritorio-v"
API = f"https://api.github.com/repos/{ORIGEN}/releases?per_page=40"
CABECERAS = {
    "User-Agent": "Caudal",
    "Accept": "application/vnd.github+json",
}


def _numeros(version):
    """1.2.0 -> (1, 2, 0), para poder comparar de verdad."""
    partes = re.findall(r"\d+", str(version or ""))
    return tuple(int(x) for x in partes[:4]) or (0,)


def hay_novedad(instalada, publicada):
    return _numeros(publicada) > _numeros(instalada)


def elegir_release(publicadas):
    """La version mas alta del escritorio (ignora borradores, pruebas y las del movil)."""
    candidatas = [r for r in publicadas or []
                  if isinstance(r, dict) and not r.get("draft") and not r.get("prerelease")
                  and str(r.get("tag_name") or "").startswith(PREFIJO)]
    if not candidatas:
        return None
    return max(candidatas, key=lambda r: _numeros(str(r["tag_name"])[len(PREFIJO):]))


def buscar_actualizacion(espera=12):
    """Mira si hay una version nueva publicada.

    Devuelve None si ya estas al dia o si no se pudo comprobar, y si la hay:
    {"version", "notas", "instalador", "apk", "pagina"}
    """
    try:
        peticion = urllib.request.Request(API, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=espera) as r:
            publicadas = json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None
    datos = elegir_release(publicadas)
    if not datos:
        return None
    etiqueta = str(datos.get("tag_name"))[len(PREFIJO):]
    if not hay_novedad(VERSION, etiqueta):
        return None

    instalador = apk = ""
    for adjunto in datos.get("assets") or []:
        nombre = (adjunto.get("name") or "").lower()
        enlace = adjunto.get("browser_download_url") or ""
        if nombre.endswith(".exe") and not instalador:
            instalador = enlace
        elif nombre.endswith(".apk") and not apk:
            apk = enlace

    if not instalador:
        return None
    return {
        "version": etiqueta,
        "notas": (datos.get("body") or "").strip(),
        "instalador": instalador,
        "apk": apk,
        "pagina": datos.get("html_url") or "",
    }


def descargar(url, al_progresar=None):
    """Trae el instalador nuevo a una carpeta temporal y devuelve su ruta."""
    destino = os.path.join(tempfile.gettempdir(), "CaudalInstalador.exe")
    peticion = urllib.request.Request(url, headers={"User-Agent": "Caudal"})
    with urllib.request.urlopen(peticion, timeout=60) as r, open(destino, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        hecho = 0
        while True:
            trozo = r.read(262144)
            if not trozo:
                break
            f.write(trozo)
            hecho += len(trozo)
            if al_progresar and total:
                al_progresar(hecho / total * 100)
    return destino


def instalar_y_salir(ruta_instalador):
    """Lanza el instalador nuevo y cierra esta copia para que pueda sustituirla."""
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([ruta_instalador, "/actualizar"], creationflags=banderas)
    # salida inmediata, como al cerrar: nada debe quedarse vivo y bloquear
    # los archivos que el instalador tiene que sustituir
    os._exit(0)
