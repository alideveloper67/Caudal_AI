# -*- coding: utf-8 -*-
"""Música de SoundCloud dentro de Caudal: buscarla, oírla tal cual y traer sus listas (sin Qt).

- Buscar, los me gusta de un perfil y las parecidas: con yt-dlp, el mismo motor con que suena y se baja
  todo lo demás.
- Las listas enteras: la página pública trae completas unas pocas canciones y, del resto, solo su número;
  quién es cada una se pregunta a oEmbed, la API pública de SoundCloud (no pide clave).

Una canción de SoundCloud es una pista normal con su enlace: `clave` = «url:https://soundcloud.com/…».
Suena, se descarga, entra en listas y me gusta. Como no es de YouTube, se queda en este equipo (no viaja al
teléfono); al traer una lista, las que están en YouTube Music sí viajan.
"""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

OEMBED = "https://soundcloud.com/oembed"
CADUCA_STREAM_S = 25 * 60         # los enlaces de audio de SoundCloud duran poco
_CAB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0 Safari/537.36"}
_cerrojo = threading.Lock()
_sabidas = {}                     # id -> ficha de oEmbed


class ErrorSoundcloud(Exception):
    pass


def es_enlace(url):
    return bool(re.match(r"https?://(?:[\w-]+\.)?soundcloud\.com/", str(url or ""), re.I))


def es(pista):
    """¿La pista es de SoundCloud?"""
    return bool(pista) and not pista.get("video_id") and es_enlace(pista.get("url"))


def enlace_de_id(ident):
    return f"https://api.soundcloud.com/tracks/{ident}"


def separar(titulo, autor):
    """(título, artista): muchas subidas se llaman «Artista - Tema» y el canal es de otro."""
    t = re.sub(r"\s+", " ", str(titulo or "")).strip()
    t = re.sub(r"^\d{1,2}\s*[.\-)]\s+(?=.+\s[-–—]\s)", "", t)      # «06 - Artista - Tema»
    m = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", t)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    return t, str(autor or "").strip()


def pista(titulo, autor, url, duracion=0, miniatura="", ident=""):
    from . import catalogo
    t, a = separar(titulo, autor)
    p = catalogo.nueva_pista("", t, [{"nombre": a, "id": ""}] if a else [], None, int(float(duracion or 0)), miniatura)
    p["clave"] = "url:" + url
    p["url"] = url
    p["plataforma"] = "soundcloud"
    if ident:
        p["sc_id"] = str(ident)
    return p


def _mejor_miniatura(e):
    """Una carátula ni diminuta ni enorme."""
    lista = [x for x in e.get("thumbnails") or [] if x.get("url")]
    for ident in ("t500x500", "crop", "t300x300"):
        for x in lista:
            if x.get("id") == ident:
                return x["url"]
    return e.get("thumbnail") or (lista[-1]["url"] if lista else "")


def _autor_del_enlace(url):
    m = re.match(r"https?://(?:www\.|m\.)?soundcloud\.com/([\w-]+)/", str(url or ""))
    return re.sub(r"[-_]+", " ", m.group(1)).strip().title() if m else ""


def _limpio(url):
    return str(url or "").split("?")[0]


def de_entrada(e):
    """Una entrada de yt-dlp (búsqueda, perfil, parecidas) -> pista, o None."""
    if not e or not e.get("title"):
        return None
    url = _limpio(e.get("webpage_url") or e.get("url"))
    if not es_enlace(url):
        return None
    autor = e.get("uploader") or _autor_del_enlace(url)
    return pista(e["title"], autor, url, e.get("duration") or 0, _mejor_miniatura(e), e.get("id") or "")


def _entradas(objetivo, limite=0):
    import yt_dlp
    o = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True,
         "socket_timeout": 12}
    if limite:
        o["playlistend"] = int(limite)
    try:
        with yt_dlp.YoutubeDL(o) as y:
            r = y.extract_info(objetivo, download=False)
    except Exception as e:  # noqa: BLE001
        texto = str(e)
        if "404" in texto:
            raise ErrorSoundcloud("Eso no existe en SoundCloud o es privado.") from e
        raise ErrorSoundcloud("SoundCloud no contestó bien. Prueba otra vez en un rato.") from e
    if not r:
        return []
    return [x for x in (r.get("entries") or [r]) if x]


def buscar(texto, limite=30):
    """Canciones de SoundCloud que casan con el texto."""
    texto = (texto or "").strip()
    if not texto:
        return []
    return [p for p in map(de_entrada, _entradas(f"scsearch{int(limite)}:{texto}")) if p]


def parecidas(url, limite=12):
    """La radio de SoundCloud de una canción (para que la música siga sola)."""
    base = _limpio(url).rstrip("/")
    if not re.match(r"https?://(?:www\.|m\.)?soundcloud\.com/[\w-]+/[\w-]+$", base):
        return []
    salida = [p for p in map(de_entrada, _entradas(base + "/recommended", limite)) if p]
    sin = [p for p in salida if not p.get("miniatura")][:12]
    for p, f in zip(sin, completar([p["url"] for p in sin])):     # llegan sin carátula
        if f:
            p["miniatura"] = f["miniatura"]
    return salida


def me_gusta_de(perfil, limite=0):
    """Los me gusta públicos de un perfil."""
    return [p for p in map(de_entrada, _entradas(f"https://soundcloud.com/{perfil}/likes", limite)) if p]


def subidas_de(perfil, limite=0):
    """Lo que subió un perfil."""
    return [p for p in map(de_entrada, _entradas(f"https://soundcloud.com/{perfil}/tracks", limite)) if p]


# ------------------------------------------------------------------ oEmbed

def ficha_oembed(ident_o_enlace, reintentos=3):
    """{"titulo", "autor", "miniatura", "enlace"} de una canción, o None si no existe o es privada."""
    clave = str(ident_o_enlace)
    with _cerrojo:
        if clave in _sabidas:
            return _sabidas[clave]
    objetivo = clave if "://" in clave else enlace_de_id(clave)
    for intento in range(reintentos):
        try:
            r = requests.get(OEMBED, params={"format": "json", "url": objetivo}, headers=_CAB, timeout=12)
        except requests.RequestException:
            time.sleep(0.6 * (intento + 1))
            continue
        if r.status_code in (429, 500, 502, 503):
            time.sleep(0.9 * (intento + 1))
            continue
        if r.status_code != 200:
            return None
        try:
            d = r.json()
        except ValueError:
            return None
        autor = str(d.get("author_name") or "").strip()
        titulo = str(d.get("title") or "").strip()
        cola = f" by {autor}"
        if autor and titulo.endswith(cola):
            titulo = titulo[:-len(cola)].strip()
        if not titulo:
            return None
        f = {"titulo": titulo, "autor": autor, "miniatura": d.get("thumbnail_url") or "", "enlace": objetivo}
        with _cerrojo:
            if len(_sabidas) > 5000:
                _sabidas.clear()
            _sabidas[clave] = f
        return f
    return None


def completar(idents, hilos=8):
    """[ficha o None] de cada número de canción, en el mismo orden."""
    idents = list(idents)
    if not idents:
        return []
    with ThreadPoolExecutor(max_workers=max(1, min(hilos, len(idents)))) as ex:
        return list(ex.map(ficha_oembed, idents))


# ------------------------------------------------------------------ canciones para «Traer una lista»

def cancion_de_pista(p):
    """Como las canciones que devuelve listas.leer: con qué buscarla y, si no está, su original."""
    c = {"titulo": p.get("titulo") or "", "artista": p.get("artista") or "", "duracion": int(p.get("duracion") or 0),
         "sc_url": p.get("url") or "", "miniatura": p.get("miniatura") or ""}
    if p.get("sc_id"):
        c["externa"] = f"sc:{p['sc_id']}"
    return c


def pista_original(cancion):
    """La pista de SoundCloud de una canción traída, o None si no se sabe su enlace."""
    url = cancion.get("sc_url") or ""
    if not es_enlace(url):
        return None
    if not cancion.get("miniatura"):
        f = ficha_oembed(url, 1)                     # los me gusta llegan sin carátula
        if f:
            cancion = dict(cancion, miniatura=f["miniatura"])
    return dict(pista(cancion.get("titulo") or "", cancion.get("artista") or "", url, cancion.get("duracion") or 0,
                      cancion.get("miniatura") or "", str(cancion.get("externa") or "").replace("sc:", "")),
                titulo=cancion.get("titulo") or "Sin título",
                artista=cancion.get("artista") or "",
                artistas=[{"nombre": cancion["artista"], "id": ""}] if cancion.get("artista") else [])


def es_la_misma(cancion, hallada):
    """¿Lo que se encontró en YouTube Music es esta canción (título, artista y versión)? En SoundCloud hay
    remixes y subidas propias que no están en otro sitio: mejor su original que otra canción."""
    from . import elegir_letra
    ficha = {"trackName": hallada.get("titulo") or "", "artistName": hallada.get("artista") or ""}
    quien = {"titulo": cancion.get("titulo") or "", "artista": cancion.get("artista") or ""}
    if not quien["artista"]:
        return elegir_letra.mismo_titulo(quien["titulo"], ficha["trackName"])
    return elegir_letra.es_la_cancion(ficha, quien)
