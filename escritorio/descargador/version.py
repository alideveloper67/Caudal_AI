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

VERSION = "2.8.6"

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


MARCA_GRANDE = "[grande]"

# «Edición» de la quinta actualización grande (la presentación a pantalla completa).
# Se muestra una sola vez a quien llega a esta versión o a una posterior sin haberla visto.
EDICION_GRANDE = "2.7.0"


def alcanza_edicion(version, edicion=None):
    """True si `version` es igual o posterior a la edición grande."""
    return _numeros(version) >= _numeros(edicion or EDICION_GRANDE)


def es_de_la_edicion(version, edicion=None):
    """True si `version` es de la serie de esa edición (2.7.x para la 2.7.0)."""
    return _numeros(version)[:2] == _numeros(edicion or EDICION_GRANDE)[:2]


def separar_marca_grande(notas):
    """(es_grande, notas sin la marca). Una release avisa de una actualización grande
    si sus notas empiezan con la línea `[grande]`."""
    texto = str(notas or "").strip()
    if texto.lower().startswith(MARCA_GRANDE):
        return True, texto[len(MARCA_GRANDE):].strip()
    return False, texto


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
    {"version", "notas", "grande", "instalador", "apk", "pagina"}
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
    grande, notas = separar_marca_grande(datos.get("body"))
    return {
        "version": etiqueta,
        "notas": notas,
        "grande": grande,
        "instalador": instalador,
        "apk": apk,
        "pagina": datos.get("html_url") or "",
    }


# Versiones publicadas con fallos conocidos: no se ofrecen para volver atrás.
RETIRADAS = {"2.8.0"}


def versiones_anteriores(espera=12, limite=6):
    """Las versiones del escritorio más antiguas que esta, de la más nueva a la más vieja.

    Cada una: {"version", "instalador", "fecha"}. Lanza OSError si no se pudo preguntar."""
    peticion = urllib.request.Request(API, headers=CABECERAS)
    with urllib.request.urlopen(peticion, timeout=espera) as r:
        publicadas = json.loads(r.read().decode())
    salida = []
    for datos in publicadas or []:
        if not isinstance(datos, dict) or datos.get("draft") or datos.get("prerelease"):
            continue
        etiqueta = str(datos.get("tag_name") or "")
        if not etiqueta.startswith(PREFIJO):
            continue
        numero = etiqueta[len(PREFIJO):]
        if not hay_novedad(numero, VERSION) or numero in RETIRADAS:   # solo las MÁS viejas y sanas
            continue
        instalador = next((a.get("browser_download_url") for a in datos.get("assets") or []
                           if str(a.get("name") or "").lower().endswith(".exe")
                           and a.get("browser_download_url")), "")
        if instalador:
            salida.append({"version": numero, "instalador": instalador,
                           "fecha": str(datos.get("published_at") or "")[:10]})
    salida.sort(key=lambda d: _numeros(d["version"]), reverse=True)
    return salida[:limite]


def descargar(url, al_progresar=None):
    """Trae el instalador a una carpeta temporal y devuelve su ruta.

    Solo lo da por bueno si llegó entero (tamaño exacto y cabecera de programa de Windows):
    un instalador cortado no se ejecuta nunca."""
    destino = os.path.join(tempfile.gettempdir(), "CaudalInstalador.exe")
    parcial = destino + ".parcial"
    peticion = urllib.request.Request(url, headers={"User-Agent": "Caudal",
                                                    "Accept-Encoding": "identity"})
    with urllib.request.urlopen(peticion, timeout=60) as r, open(parcial, "wb") as f:
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
    with open(parcial, "rb") as f:
        cabeza = f.read(2)
    if (total and hecho != total) or cabeza != b"MZ":
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise OSError("la descarga llegó incompleta; revisa tu internet y vuelve a intentarlo")
    os.replace(parcial, destino)
    return destino


def instalar_y_salir(ruta_instalador):
    """Lanza el instalador nuevo y cierra esta copia para que pueda sustituirla."""
    banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([ruta_instalador, "/actualizar"], creationflags=banderas)
    # salida inmediata, como al cerrar: nada debe quedarse vivo y bloquear
    # los archivos que el instalador tiene que sustituir
    try:
        from . import ayudante, disco
        ayudante.cerrar()               # si sigue vivo, el instalador no puede sustituir el .exe
        disco.vaciar()                  # lo último guardado, antes de salir de golpe
    except Exception:  # noqa: BLE001
        pass
    os._exit(0)
