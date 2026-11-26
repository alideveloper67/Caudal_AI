# -*- coding: utf-8 -*-
"""Más sitios donde buscar la letra cuando YouTube Music y LRCLIB no la tienen (sin Qt).

Cada fuente devuelve fichas con la misma forma que LRCLIB (trackName, artistName, duration,
syncedLyrics, plainLyrics), así que pasan por las mismas comprobaciones de elegir_letra.py: antes que
la letra de otra canción, ninguna.

- NetEase: muchas letras con tiempos, también en español.
- Genius: el texto de casi todo (sin tiempos: se los pone sincronia_tareas escuchando la canción).
- Subtítulos que el autor subió al propio video (nunca los automáticos de YouTube).
"""

import html
import re

import requests

from . import elegir_letra

_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")
_CAB = {"User-Agent": _NAVEGADOR, "Accept-Language": "es,en;q=0.8"}
ESPERA_S = 9

# líneas que no se cantan: créditos que NetEase pone como si fueran versos
_CREDITO = re.compile(r"^\s*(?:作词|作曲|编曲|制作人|混音|母带|录音|监制|出品|词|曲|"
                      r"lyrics? by|composed by|produced by|written by|arranged by|mixed by|mastered by)\s*[:：]", re.I)


def _json(url, cabeceras=None, **params):
    try:
        r = requests.get(url, params=params or None, headers=cabeceras or _CAB, timeout=ESPERA_S)
        return r.json() if r.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def _preguntas(formas):
    """Con qué se busca: «artista título» y, si el título lleva paréntesis, también sin ellos."""
    salida = []
    for titulo, artista, _valen in formas[:2]:
        corto = re.sub(r"[(\[{].*?[)\]}]", " ", titulo)
        for t in (titulo, re.sub(r"\s+", " ", corto).strip()):
            q = f"{artista} {t}".strip()
            if t and q not in salida:
                salida.append(q)
    return salida[:4]


# ------------------------------------------------------------------ NetEase

def limpiar_lrc(lrc):
    """El LRC sin las líneas de créditos."""
    filas = []
    for fila in str(lrc or "").splitlines():
        texto = re.sub(r"\[[\d:.]+\]", "", fila).strip()
        if texto and _CREDITO.search(texto):
            continue
        filas.append(fila)
    return "\n".join(filas)


def netease(pista, limite=3):
    """Fichas de NetEase que son esta canción."""
    cab = dict(_CAB, Referer="https://music.163.com/")
    salida, vistos = [], set()
    formas = elegir_letra.consultas(pista)
    dur = float(pista.get("duracion") or 0)
    for q in _preguntas(formas):
        d = _json("https://music.163.com/api/search/get", cab, s=q, type=1, limit=8) or {}
        for s in ((d.get("result") or {}).get("songs") or []):
            if not isinstance(s, dict) or s.get("id") in vistos:
                continue
            vistos.add(s.get("id"))
            ficha = {"id": f"netease:{s.get('id')}", "trackName": s.get("name") or "",
                     "artistName": ", ".join(a.get("name") or "" for a in s.get("artists") or []),
                     "albumName": (s.get("album") or {}).get("name") or "",
                     "duration": float(s.get("duration") or 0) / 1000.0}
            if elegir_letra.es_la_cancion(ficha, pista, formas):
                salida.append(ficha)
        if salida:
            break
    salida.sort(key=lambda f: abs(f["duration"] - dur) if dur else 0)
    buenas = []
    for ficha in salida[:limite]:
        d = _json("https://music.163.com/api/song/lyric", cab, id=ficha["id"].split(":")[1], lv=1, kv=1, tv=-1) or {}
        lrc = limpiar_lrc((d.get("lrc") or {}).get("lyric"))
        if d.get("nolyric") or d.get("uncollected") or not lrc.strip():
            continue
        marcas = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*\S", lrc)
        texto = re.sub(r"\[[^\]]*\]", "", lrc).strip()
        if len(texto.split()) < 12:
            continue
        ficha["plainLyrics"] = "\n".join(x.strip() for x in texto.splitlines() if x.strip())
        # hay fichas con el texto entero en 0:00: no valen como tiempos
        tiempos = sorted({int(m) * 60 + float(s) for m, s in marcas})
        if len(tiempos) >= 8 and tiempos[-1] > 45:
            ficha["syncedLyrics"] = lrc
        buenas.append(ficha)
    return buenas


# ------------------------------------------------------------------ Genius

def _cierre(t, etiqueta, desde):
    """Dónde acaba (inicio, fin del cierre) la etiqueta abierta justo antes de `desde`; None si no cierra."""
    nivel = 1
    for x in re.finditer(rf"<(/?){etiqueta}\b[^>]*>", t[desde:]):
        nivel += -1 if x.group(1) else 1
        if nivel == 0:
            return desde + x.start(), desde + x.end()
    return None


def _quitar_excluidos(t):
    """Lo que no es letra (colaboradores, título, «Lee más») va marcado por la propia página."""
    while True:
        m = re.search(r'<(div|span)[^>]*data-exclude-from-selection="true"[^>]*>', t)
        if not m:
            return t
        c = _cierre(t, m.group(1), m.end())
        t = t[:m.start()] + (t[c[1]:] if c else "")


def texto_genius(pagina):
    """La letra de una página de Genius (su HTML), sin encabezados «[Coro]» ni la cabecera de la ficha."""
    pagina = pagina or ""
    trozos = []
    for m in re.finditer(r'<div[^>]*data-lyrics-container="true"[^>]*>', pagina):
        c = _cierre(pagina, "div", m.end())
        if c:
            trozos.append(pagina[m.end():c[0]])
    filas = []
    for t in trozos:
        t = _quitar_excluidos(t)
        t = re.sub(r"<br\s*/?>|</(?:p|div)>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", "", t))
        # los encabezados pueden ocupar varias líneas: «[Verso 1:\nFulano]»
        t = re.sub(r"\[[^\[\]]{0,160}\]", "\n", t)
        for f in t.splitlines():
            filas.append(re.sub(r"\s+", " ", f.replace("​", "").replace(" ", " ")).strip())
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(filas)).strip()
    return texto if len(texto.split()) >= 12 else ""


def genius(pista):
    """La ficha (solo texto) de Genius que es esta canción, o None."""
    formas = elegir_letra.consultas(pista)
    for q in _preguntas(formas):
        d = _json("https://genius.com/api/search/song", q=q) or {}
        secciones = (d.get("response") or {}).get("sections") or [{}]
        for h in (secciones[0].get("hits") or [])[:6]:
            r = h.get("result") or {}
            if r.get("lyrics_state") != "complete" or r.get("instrumental") or not r.get("url"):
                continue
            ficha = {"id": f"genius:{r.get('id')}", "trackName": r.get("title") or "",
                     "artistName": re.sub(r"\s*\([A-Z]{2,4}\)", "", r.get("artist_names") or ""), "duration": 0}
            if not elegir_letra.es_la_cancion(ficha, pista, formas):
                continue
            try:
                p = requests.get(r["url"], headers=_CAB, timeout=ESPERA_S)
            except requests.RequestException:
                return None
            texto = texto_genius(p.text) if p.status_code == 200 else ""
            if texto:
                ficha["plainLyrics"] = texto
                return ficha
    return None


# ------------------------------------------------------------------ subtítulos del propio video

def vtt_a_lineas(texto):
    """[(ms, verso)] de un archivo VTT/SRT, sin repetir la línea que se arrastra de un cuadro a otro."""
    lineas, anterior = [], None
    for bloque in re.split(r"\r?\n\s*\r?\n", texto or ""):
        m = re.search(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->", bloque)
        if not m:
            continue
        h, mi, s, ms = (int(x or 0) for x in m.groups())
        cuerpo = bloque[m.end():].split("\n", 1)
        dicho = re.sub(r"<[^>]+>", "", cuerpo[1] if len(cuerpo) > 1 else "")
        dicho = re.sub(r"[♪♫#]+", " ", html.unescape(dicho))
        dicho = re.sub(r"\[[^\]]*\]|\([^)]*(?:música|music|aplausos|applause)[^)]*\)", " ", dicho, flags=re.I)
        dicho = re.sub(r"\s+", " ", dicho).strip()
        if dicho and dicho != anterior:
            lineas.append((((h * 60 + mi) * 60 + s) * 1000 + ms, dicho))
            anterior = dicho
    return lineas


_IDIOMAS = ("es", "es-419", "es-ES", "es-MX", "en", "en-US", "en-GB", "pt", "pt-BR", "ja", "ko", "fr", "it")


def subtitulos_video(video_id):
    """Los subtítulos que el autor subió al video, como letra con tiempos: {"lineas", "idioma"} o None."""
    if not video_id:
        return None
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
                               "socket_timeout": ESPERA_S}) as y:
            info = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False, process=False)
    except Exception:  # noqa: BLE001
        return None
    subs = {k: v for k, v in ((info or {}).get("subtitles") or {}).items() if k != "live_chat" and v}
    if not subs:
        return None
    original = info.get("language") or ""
    if len(subs) > 4 and not original:
        return None                 # muchas traducciones y no se sabe cuál es la que se canta
    orden = [k for k in subs if original and k.split("-")[0] == original.split("-")[0]]
    orden += [k for k in _IDIOMAS if k in subs] + list(subs)
    clave = orden[0]
    url = next((x.get("url") for x in subs[clave] if x.get("ext") == "vtt"), None)
    if not url:
        return None
    try:
        r = requests.get(url, headers=_CAB, timeout=ESPERA_S)
    except requests.RequestException:
        return None
    lineas = vtt_a_lineas(r.text) if r.status_code == 200 else []
    if len(lineas) < 8 or sum(len(t.split()) for _m, t in lineas) < 40:
        return None
    return {"lineas": lineas, "idioma": clave}
