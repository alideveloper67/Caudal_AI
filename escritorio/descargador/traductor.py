# -*- coding: utf-8 -*-
"""Traduce la letra de una cancion linea a linea (como YouTube Music Premium).

Dos caminos sin clave, por si uno falla: el traductor publico de Google y, de
respaldo, MyMemory (API gratuita y documentada). La letra se manda por trozos
con sus saltos de linea y cada linea traducida vuelve a su sitio.
"""

import re
import threading

import requests

from .memoria import DiccionarioLimitado

_CACHE = DiccionarioLimitado(300)       # las traducciones de las 300 últimas letras
_CANDADO = threading.Lock()
MISMO_IDIOMA = "mismo"


class _MismoIdioma(Exception):
    pass


def traducir(clave, lineas, destino="es"):
    """Lista con la traduccion de cada linea ('' si esa linea no la necesita),
    MISMO_IDIOMA si la letra ya esta en `destino`, o None si no se pudo."""
    k = f"{clave}|{destino}"
    with _CANDADO:
        if k in _CACHE:
            return _CACHE[k]
    resultado = _traducir(list(lineas), destino)
    if resultado is not None:  # un fallo de red no se guarda: se reintenta
        with _CANDADO:
            _CACHE[k] = resultado
    return resultado


def _traducir(lineas, destino):
    if not any(l.strip() for l in lineas):
        return MISMO_IDIOMA
    for motor, maximo in ((_google, 1400), (_mymemory, 380)):
        try:
            return _por_trozos(lineas, destino, motor, maximo)
        except _MismoIdioma:
            return MISMO_IDIOMA
        except Exception:  # noqa: BLE001 - al siguiente camino
            continue
    return None


def _por_trozos(lineas, destino, motor, maximo):
    trozos, actual, largo = [], [], 0
    for i, l in enumerate(lineas):
        l = l.strip()
        if not l:
            continue
        if actual and largo + len(l) + 1 > maximo:
            trozos.append(actual)
            actual, largo = [], 0
        actual.append(i)
        largo += len(l) + 1
    if actual:
        trozos.append(actual)

    salida = [""] * len(lineas)
    for t in trozos:
        texto = "\n".join(lineas[i].strip() for i in t)
        traducido, origen = motor(texto, destino)
        if origen and origen.split("-")[0] == destino:
            raise _MismoIdioma()
        partes = traducido.split("\n")
        if len(partes) == len(t):
            for k, i in enumerate(t):
                salida[i] = partes[k].strip()
        else:  # el traductor junto o partio lineas: una por una
            for i in t:
                una, _ = motor(lineas[i].strip(), destino)
                salida[i] = una.replace("\n", " ").strip()
    for i, l in enumerate(lineas):
        if _igual(salida[i], l):
            salida[i] = ""
    if not any(salida):
        raise _MismoIdioma()
    return salida


def _igual(a, b):
    def n(s):
        return re.sub(r"[\W_]+", "", (s or "").lower())
    return n(a) == n(b)


def _google(texto, destino):
    r = requests.post(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": destino, "dt": "t"},
        data={"q": texto}, timeout=15)
    r.raise_for_status()
    return leer_google(r.json())


def leer_google(d):
    """[[["trad","orig",...],...],None,"en",...] -> (texto, idioma)."""
    if not isinstance(d, list) or not d or not isinstance(d[0], list):
        raise ValueError("respuesta rara")
    texto = "".join(s[0] for s in d[0] if isinstance(s, list) and s and isinstance(s[0], str))
    idioma = d[2] if len(d) > 2 and isinstance(d[2], str) else ""
    return texto, idioma


def _mymemory(texto, destino):
    r = requests.get("https://api.mymemory.translated.net/get",
                     params={"q": texto, "langpair": f"autodetect|{destino}"}, timeout=15)
    d = r.json()
    if "DISTINCT LANGUAGES" in str(d.get("responseDetails", "")).upper():
        raise _MismoIdioma()
    if str(d.get("responseStatus")) != "200" or d.get("quotaFinished"):
        raise RuntimeError(f"mymemory {d.get('responseStatus')}")
    datos = d.get("responseData") or {}
    return str(datos.get("translatedText") or ""), str(datos.get("detectedLanguage") or "")
