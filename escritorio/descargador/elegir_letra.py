# -*- coding: utf-8 -*-
"""Que la letra sea la de ESTA canción: cuentas puras, sin red (mismas reglas en la app:
app/lib/nucleo/elegir_letra.dart).

Una letra encontrada por búsqueda solo vale si el título y el artista son los de la canción, si es la
misma versión (en vivo, remix, acústica…) y, cuando YouTube Music da el texto de esa canción, si las
palabras coinciden. Sus tiempos solo valen si además dura lo mismo.
"""

import difflib
import re
import unicodedata

DIFERENCIA_MAX_S = 2.5        # más diferencia de duración: los tiempos serían de otra grabación
DIFERENCIA_OFICIAL = 2.0      # con la canción oficial de un video (medido: hasta 3 s, 0,3 s de corrimiento)
PARECIDO_TEXTO_MIN = 0.6      # palabras en común con la letra de YouTube Music para darla por buena

# palabras del título que cambian la grabación (y con ella, los tiempos o la letra)
_VERSIONES = {
    "remix": r"remix|rmx|bootleg|mashup|mix(?!tape)",
    "vivo": r"live|en vivo|en directo|ao vivo|concierto|concert|unplugged|tour",
    "acustica": r"acoustic|acustic[oa]",
    "instrumental": r"instrumental|karaoke|backing track|pista",
    "cover": r"cover|tributo|tribute|version de",
    "rapida": r"sped up|speed up|nightcore|acelerad[oa]",
    "lenta": r"slowed|reverb|screwed",
    "sesion": r"session|sesion|sessions",
    "demo": r"demo",
    "orquesta": r"sinfonic[oa]|symphonic|orchestral|piano version|version piano",
}
_RUIDO = (r"official|oficial|video|audio|lyrics?|letra|visuali[sz]er|hd|hq|4k|8k|1080p|720p|clip|full|"
          r"remaster(?:ed|izad[oa])?|mono|stereo|explicit|clean|prod|color coded|subtitulad[oa]|sub|"
          r"estreno|nuevo|new|album version|radio edit|single version|\d{4}")
_INVITADOS = r"\b(?:feat|ft|featuring|with|con la participacion de|junto a)\b\.?"


def normalizar(texto):
    """Minúsculas, sin tildes ni signos, en cualquier alfabeto: «¡Tití!» → «titi», «アイドル» → «アイドル»."""
    t = unicodedata.normalize("NFKD", str(texto or "").casefold())
    t = "".join(c for c in t if not unicodedata.combining(c) or ord(c) in (0x3099, 0x309A))
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"['’`´]", "", t)
    t = re.sub(r"[^\w]+|_", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def versiones(titulo):
    """Qué versión dice ser el título: {'remix', 'vivo'…} (vacío: la de siempre)."""
    n = normalizar(titulo)
    return {k for k, p in _VERSIONES.items() if re.search(rf"\b(?:{p})\b", n)}


def titulo_limpio(titulo):
    """El título sin adornos: «Adele - Hello (Official Video) [HD]» → «Adele - Hello»."""
    t = re.sub(r"^\s*(?:0\d|\d{1,2}\s*[.\-_)])\s*(?=\D)", "", str(titulo or ""))     # «01 La Flaca», «3. Eres»

    def quitar(m):
        dentro = normalizar(m.group(1))
        if re.search(rf"^(?:{_INVITADOS})", dentro) or (not versiones(dentro) and re.search(rf"\b(?:{_RUIDO})\b", dentro)):
            return " "
        return m.group(0)
    t = re.sub(r"[(\[{【]([^)\]}】]*)[)\]}】]", quitar, t)
    t = re.split(r"\s[|·•]\s|\s\|\||//", t)[0]
    # «Junior H Ft. Jose Mejia - Suena»: el invitado se quita, la canción no
    t = re.sub(r"\s+(?:feat|ft|featuring)\b\.?.*?(?=\s+[-–—]\s+|$)", "", t, flags=re.I)
    t = re.sub(r"\s+(?:official|oficial)\s+(?:music\s+)?(?:video|audio|lyric video)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s+(?:video|audio)\s+oficial\s*$", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -–—\"'")


def _nombres(texto):
    """«Luis Fonsi & Daddy Yankee» → ['luis fonsi', 'daddy yankee'] (y el texto entero)."""
    entero = normalizar(texto)
    partes = re.split(r"\s*(?:,|;|/|&|\+|\sx\s|\sy\s|\sand\s|\sfeat\.?\s|\sft\.?\s|\svs\.?\s|\scon\s)\s*",
                      str(texto or ""), flags=re.I)
    salida = []
    for p in [entero] + [normalizar(p) for p in partes]:
        p = re.sub(r"\b(?:topic|vevo|oficial|official|tv|music)\b", "", p).strip()
        if p and p not in salida:
            salida.append(p)
    return salida


def _parecidos(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    ja, jb = a.replace(" ", ""), b.replace(" ", "")
    if ja == jb:
        return True
    if len(ja) < 4 or len(jb) < 4:
        return False
    return difflib.SequenceMatcher(None, ja, jb, autojunk=False).ratio() >= 0.84


def mismo_artista(de_pista, de_letra):
    """¿Alguno de los artistas coincide? «Juanes» con «Juanes feat. X»: sí."""
    for a in de_pista:
        for b in _nombres(de_letra):
            if _parecidos(a, b):
                return True
            # «Grupo Néctar» y «Néctar»; «La Mosca» y «La Mosca Tsé-Tsé»: todas las palabras del corto
            pa, pb = a.split(), b.split()
            corto, largo = (pa, pb) if len(pa) <= len(pb) else (pb, pa)
            if corto and set(corto) <= set(largo) and len("".join(corto)) >= 5:
                return True
    return False


def _sin_version(n):
    for p in _VERSIONES.values():
        n = re.sub(rf"\b(?:{p})\b", " ", n)
    n = re.sub(rf"\b(?:{_RUIDO})\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def mismo_titulo(de_pista, de_letra):
    """¿Es el mismo título? «Gasolina» y «Gasolina (feat. Glory)»: sí. «Hello» y «Hello Goodbye»: no."""
    a, b = normalizar(titulo_limpio(de_pista)), normalizar(titulo_limpio(de_letra))
    if _parecidos(a, b):
        return True
    a, b = _sin_version(a) or a, _sin_version(b) or b
    if _parecidos(a, b):
        return True
    # lo de entre paréntesis cambia de una ficha a otra («De Música Ligera (Remasterizado 2007)»)
    qa = normalizar(re.sub(r"[(\[].*?[)\]]", " ", str(de_pista or "")))
    qb = normalizar(re.sub(r"[(\[].*?[)\]]", " ", str(de_letra or "")))
    return bool(qa and qb) and _parecidos(_sin_version(qa) or qa, _sin_version(qb) or qb)


def consultas(pista):
    """Las formas de nombrar la canción: [(título, artista, [artistas que valen])].

    Los videos subidos por cualquiera traen «Artista - Canción» en el título y el canal como artista."""
    crudo = pista.get("titulo") or ""
    titulo = titulo_limpio(crudo)
    arts = [a.get("nombre") for a in pista.get("artistas") or [] if isinstance(a, dict) and a.get("nombre")]
    artista = (arts[0] if arts else "") or pista.get("artista") or ""
    valen = []
    for x in (arts or []) + [pista.get("artista") or ""]:
        for n in _nombres(x):
            if n not in valen:
                valen.append(n)
    salida = []
    partes = re.split(r"\s+[-–—]\s+", titulo, maxsplit=1)
    if len(partes) == 2 and all(normalizar(x) for x in partes):
        izq, der = partes
        if mismo_artista(valen, izq):            # «Adele - Hello» de Adele
            return [(der, izq, valen + _nombres(izq))]
        if mismo_artista(valen, der):
            return [(izq, der, valen + _nombres(der))]
        salida = [(der, izq, _nombres(izq)), (izq, der, _nombres(der))]
    if titulo and valen:
        salida.insert(0, (titulo, artista, valen))
    return salida


def palabras_en_comun(a, b):
    """Cuánto de la letra más corta está en la otra, por parejas de palabras seguidas (0..1).
    (Por parejas: dos canciones distintas comparten «que», «de», «amor», pero no las frases.)"""
    def pares(t):
        w = normalizar(re.sub(r"[(\[].*?[)\]]", " ", t or "")).split()
        if len(w) < 12:                       # sin espacios entre palabras (japonés, chino…): por letras
            j = "".join(w)
            return {j[i:i + 3] for i in range(len(j) - 2)}
        return {(w[i], w[i + 1]) for i in range(len(w) - 1)}
    pa, pb = pares(a), pares(b)
    if not pa or not pb:
        return 0.0
    return len(pa & pb) / min(len(pa), len(pb))


def corrimiento(a, b):
    """Cuántos segundos más tarde van los versos de `a` que los mismos de `b` ([(ms, texto)]); None si
    coinciden pocos o no se ponen de acuerdo."""
    difs = []
    otros = [(ms, normalizar(t)) for ms, t in b or []]
    for ms, texto in a or []:
        n = normalizar(texto)
        if len(n.split()) < 3:
            continue
        mismos = [m2 for m2, t2 in otros if t2 == n]
        if len(mismos) == 1 and sum(normalizar(t) == n for _m, t in a) == 1:
            difs.append((ms - mismos[0]) / 1000.0)       # los que se repiten no dicen cuál es cuál
    if len(difs) < 4:
        return None
    difs.sort()
    medio = difs[len(difs) // 2]
    cerca = sum(abs(d - medio) <= 1.0 for d in difs)
    return round(medio, 2) if cerca >= 0.6 * len(difs) else None


def texto_de(cand):
    """El texto corrido de una ficha de LRCLIB."""
    t = cand.get("plainLyrics") or ""
    return t if t.strip() else re.sub(r"\[[\d:.]+\]|<[\d:.]+>", "", cand.get("syncedLyrics") or "")


def es_la_cancion(cand, pista, formas=None):
    """¿La ficha de LRCLIB es de esta canción (título, artista y versión)?"""
    if not isinstance(cand, dict) or cand.get("instrumental"):
        return False
    t2, a2 = cand.get("trackName") or cand.get("name") or "", cand.get("artistName") or ""
    v1, v2 = versiones(pista.get("titulo")), versiones(t2)
    if "instrumental" in versiones(cand.get("albumName")):      # «Karaoke Hits, vol. 3»
        v2 = v2 | {"instrumental"}
    if (v1 ^ v2) - {"sesion", "demo"}:
        return False
    for titulo, _artista, valen in (formas if formas is not None else consultas(pista)):
        if mismo_titulo(titulo, t2) and mismo_artista(valen, a2):
            return True
    return False


def elegir(candidatos, pista, texto_bueno=""):
    """De las fichas de LRCLIB, (la que sirve con tiempos, la que sirve solo como texto, la que tiene
    tiempos pero de una grabación que dura distinto). Cualquiera puede ser None."""
    dur = float(pista.get("duracion") or 0)
    formas = consultas(pista)
    buenas = []
    for c in candidatos or []:
        if not es_la_cancion(c, pista, formas):
            continue
        if texto_bueno and palabras_en_comun(texto_de(c), texto_bueno) < PARECIDO_TEXTO_MIN:
            continue
        buenas.append(c)

    def distancia(c):
        d = float(c.get("duration") or 0)
        return abs(d - dur) if dur and d else (0.0 if not dur else 1.0)
    buenas.sort(key=distancia)
    con, texto, otra = None, None, None
    for c in buenas:
        if (c.get("syncedLyrics") or "").strip():
            if con is None and distancia(c) <= DIFERENCIA_MAX_S:
                con = c
            elif otra is None:
                otra = c
        if texto is None and texto_de(c).strip():
            texto = c
    return con, texto, otra
