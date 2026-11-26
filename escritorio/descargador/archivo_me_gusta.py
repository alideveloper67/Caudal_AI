# -*- coding: utf-8 -*-
"""Traer tus «me gusta» desde un archivo, sin vincular ninguna cuenta.

Entiende:
  * Spotify, «Descarga tus datos»: el .zip tal cual o su YourLibrary.json;
  * Google Takeout (YouTube y YouTube Music): el .zip o sus .csv, en español o inglés;
  * cualquier .csv con título y artista (Exportify, TuneMyMusic, Soundiiz...);
  * un .txt, o texto pegado, con «Artista - Título» en cada línea.

Los archivos vienen de fuera: se leen con topes de tamaño (nada de «bombas» zip), no se extrae
nada al disco y de un zip solo se abren los .json, .csv y .txt.
"""

import csv
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

MAX_TEXTO = 40 * 1024 * 1024          # un .json/.csv/.txt suelto o dentro de un zip
MAX_TOTAL_ZIP = 120 * 1024 * 1024     # todo lo que se lee de un mismo zip
MAX_PROPORCION = 300                  # descomprimido / comprimido
MAX_MIEMBROS = 20000
MAX_LEIDOS = 400
MAX_CANCIONES = 50000

EXTENSIONES = (".zip", ".json", ".csv", ".tsv", ".txt")
FILTRO_DIALOGO = "Tus datos (*.zip *.json *.csv *.tsv *.txt)"


class ErrorArchivo(Exception):
    """Algo que se le puede contar a la persona tal cual."""


# ---------------------------------------------------------------- utilidades

def _limpio(s):
    return re.sub(r"\s+", " ", str(s or "").replace("\x00", "")).strip()


def _normal(s):
    s = unicodedata.normalize("NFKD", _limpio(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def decodificar(datos):
    if datos[:3] == b"\xef\xbb\xbf":
        return datos[3:].decode("utf-8", "replace")
    if datos[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return datos.decode("utf-16", "replace")
    try:
        return datos.decode("utf-8")
    except UnicodeDecodeError:
        return datos.decode("cp1252", "replace")


_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _video_de(texto):
    texto = _limpio(texto)
    if _VIDEO.match(texto):
        return texto
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])", texto)
    return m.group(1) if m else ""


def _duracion(valor, en_ms=False):
    v = _limpio(valor)
    if not v:
        return 0
    if ":" in v:
        try:
            n = 0
            for trozo in v.split(":"):
                n = n * 60 + int(float(trozo))
            return n
        except ValueError:
            return 0
    try:
        n = float(v.replace(",", "."))
    except ValueError:
        return 0
    if n != n or n < 0 or n > 10 ** 9:
        return 0
    return int(n / 1000) if en_ms or n > 10000 else int(n)


def _cancion(titulo="", artista="", duracion=0, video="", externa=""):
    c = {"titulo": _limpio(titulo)[:300], "artista": _limpio(artista)[:300], "duracion": int(duracion or 0)}
    if video:
        c["url"] = f"https://www.youtube.com/watch?v={video}"
        externa = externa or f"yt:{video}"
    if externa:
        c["externa"] = externa
    return c


def _sin_repetir(canciones):
    vistas, salida = set(), []
    for c in canciones:
        k = c.get("externa") or (_normal(c["titulo"]), _normal(c["artista"]))
        if k in vistas or k == ("", ""):
            continue
        vistas.add(k)
        salida.append(c)
    if len(salida) > MAX_CANCIONES:
        raise ErrorArchivo("Ese archivo trae demasiadas canciones. Divídelo en partes.")
    return salida


def _resultado(servicio, plataforma, canciones, aviso=""):
    canciones = _sin_repetir(canciones)
    if not canciones:
        raise ErrorArchivo("No encontré canciones en ese archivo.")
    return {"servicio": servicio, "plataforma": plataforma, "titulo": f"Me gusta de {plataforma}",
            "autor": "", "canciones": canciones, "completa": True, "aviso": aviso, "total": len(canciones)}


# ---------------------------------------------------------------- JSON

def _uri_spotify(uri):
    m = re.search(r"(?:spotify:track:|/track/)([A-Za-z0-9]{15,30})", _limpio(uri))
    return f"sp:{m.group(1)}" if m else ""


def leer_json(texto):
    """Los me gusta de un JSON. Devuelve (servicio, plataforma, canciones)."""
    try:
        d = json.loads(texto)
    except (ValueError, RecursionError) as e:
        raise ErrorArchivo("Ese archivo está dañado: no se pudo leer.") from e
    if isinstance(d, dict) and isinstance(d.get("tracks"), list):
        canciones = []
        for t in d["tracks"]:
            if not isinstance(t, dict):
                continue
            titulo = t.get("track") or t.get("name") or t.get("title")
            if not _limpio(titulo):
                continue
            canciones.append(_cancion(titulo, t.get("artist"), externa=_uri_spotify(t.get("uri"))))
        return "spotify", "Spotify", canciones
    if isinstance(d, dict) and isinstance(d.get("playlists"), list):
        raise ErrorArchivo("Ese archivo tiene tus listas de Spotify, no tus me gusta. "
                           "Elige el que se llama YourLibrary.json (o el .zip entero).")
    filas = d if isinstance(d, list) else []
    if filas and isinstance(filas[0], dict) and ("endTime" in filas[0] or "ts" in filas[0]
                                                 or "msPlayed" in filas[0]):
        raise ErrorArchivo("Ese archivo es tu historial de Spotify, no tus me gusta. "
                           "Elige el que se llama YourLibrary.json (o el .zip entero).")
    canciones = []
    for f in filas:
        if not isinstance(f, dict):
            continue
        n = {_normal(k): v for k, v in f.items()}
        fila = _fila_a_cancion(n.get)
        if fila:
            canciones.append(fila)
    if canciones:
        return "", "tu archivo", canciones
    raise ErrorArchivo("En ese archivo no hay me gusta. Si es de Spotify, elige YourLibrary.json.")


# ---------------------------------------------------------------- CSV

TITULO = ("track name", "track title", "titulo de la cancion", "titulo de cancion", "nombre de la cancion",
          "nombre de la pista", "nombre de pista", "song title", "song name", "titulo de la pista",
          "titulo del video", "titulo de video", "video title", "title", "titulo", "track", "song",
          "cancion", "pista", "name", "nombre")
ARTISTA = ("artist name s", "artist names", "artist name", "artist name 1", "artists", "artist",
           "nombre del artista", "nombre del artista 1", "nombre de artista", "nombre de artista 1",
           "nombre de los artistas", "artista s", "artistas", "artista", "album artist", "channel title",
           "channel", "canal", "nombre del canal", "author", "autor")
DURACION_MS = ("duration ms", "track duration ms", "duracion ms", "duracion de la pista ms",
               "duracion de la cancion ms", "duration milliseconds")
DURACION = ("duration", "duracion", "length", "time", "duration s", "duration seconds", "duracion s")
VIDEO = ("video id", "videoid", "id de video", "id del video", "id de video de youtube",
         "identificador de video", "identificador del video", "youtube id", "song url", "video url",
         "url de la cancion", "url del video", "url de video", "youtube url")
URI = ("track uri", "spotify uri", "uri de la pista", "uri", "track id", "spotify id", "spotify track id",
       "spotify url", "track url", "url")


def _primera(get, nombres):
    for n in nombres:
        v = get(n)
        if v is not None and _limpio(v):
            return _limpio(v)
    return ""


def _fila_a_cancion(get):
    titulo = _primera(get, TITULO)
    video = _video_de(_primera(get, VIDEO))
    uri = _primera(get, URI)
    externa = _uri_spotify(uri)
    if not video and not externa and "youtu" in uri:
        video = _video_de(uri)
    if not titulo and not video:
        return None
    dur = _duracion(_primera(get, DURACION_MS), True) or _duracion(_primera(get, DURACION))
    return _cancion(titulo, _primera(get, ARTISTA), dur, video, externa)


def _delimitador(linea):
    cuentas = {d: linea.count(d) for d in (",", ";", "\t")}
    mejor = max(cuentas, key=cuentas.get)
    return mejor if cuentas[mejor] else ","


def leer_csv(texto):
    """Las canciones de un CSV con cabecera. Devuelve (servicio, canciones)."""
    texto = texto.lstrip("﻿")
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas[:20]):
        # algunos Takeout llevan unas líneas con los datos de la lista antes de la cabecera
        sep = _delimitador(linea)
        try:
            celdas = [_normal(x) for x in next(csv.reader([linea], delimiter=sep), [])]
        except csv.Error:
            continue
        hay_video = any(c in VIDEO for c in celdas)
        hay_titulo = any(c in TITULO for c in celdas)
        hay_artista = any(c in ARTISTA for c in celdas)
        if not (hay_video or (hay_titulo and hay_artista)):
            continue
        canciones = []
        csv.field_size_limit(1024 * 1024)
        try:
            for fila in csv.reader(io.StringIO("\n".join(lineas[i + 1:])), delimiter=sep):
                d = {}
                for k, v in zip(celdas, fila):
                    d.setdefault(k, v)
                c = _fila_a_cancion(d.get)
                if c:
                    canciones.append(c)
                if len(canciones) > MAX_CANCIONES:
                    raise ErrorArchivo("Ese archivo trae demasiadas canciones. Divídelo en partes.")
        except csv.Error as e:
            raise ErrorArchivo("Ese archivo está dañado: no se pudo leer.") from e
        servicio = ""
        if any(c.get("externa", "").startswith("sp:") for c in canciones):
            servicio = "spotify"
        elif hay_video and any(c.get("url") for c in canciones):
            servicio = "youtube"
        return servicio, canciones
    raise ErrorArchivo("No encontré las columnas del título y el artista en ese archivo.")


# ---------------------------------------------------------------- texto

_NUMERO = re.compile(r"^\s*(?:\d{1,5}\s*[.)\-]\s+|[-•*·]\s+)")


def leer_texto(texto):
    """«Artista - Título» por líneas (vale también el enlace de un video)."""
    if len(texto) > MAX_TEXTO:
        raise ErrorArchivo("Ese texto es demasiado largo.")
    canciones = []
    for linea in texto.lstrip("﻿").splitlines():
        linea = _limpio(_NUMERO.sub("", linea))
        if not linea:
            continue
        if linea.startswith(("http://", "https://")):
            video = _video_de(linea) if "youtu" in linea else ""
            if video:
                canciones.append(_cancion(video=video))
            continue
        m = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", linea)
        canciones.append(_cancion(m.group(2), m.group(1)) if m else _cancion(linea))
    return canciones


def desde_texto(texto):
    """Texto pegado por la persona -> lista lista para pasar a Me gusta."""
    canciones = leer_texto(texto or "")
    if not canciones:
        raise ErrorArchivo("Escribe una canción en cada línea: «Artista - Título».")
    return _resultado("", "tu lista", canciones)


# ---------------------------------------------------------------- zip

_ME_GUSTA = re.compile(r"(liked|\blikes?\b|me gusta|que te gustan|que me gustan|favorit)")
_BIBLIOTECA = re.compile(r"(music library songs|biblioteca musical|canciones de la biblioteca|"
                         r"biblioteca de musica)")


def _leer_miembro(z, m, presupuesto):
    if m.flag_bits & 0x1:
        raise ErrorArchivo("Ese zip tiene contraseña. Ábrelo y elige el archivo de dentro.")
    if m.file_size > MAX_TEXTO or (m.compress_size and m.file_size > 1024 * 1024
                                   and m.file_size / m.compress_size > MAX_PROPORCION):
        raise ErrorArchivo("Ese zip trae un archivo demasiado grande y no se abrió.")
    partes, total = [], 0
    with z.open(m) as f:
        while True:
            trozo = f.read(256 * 1024)
            if not trozo:
                break
            total += len(trozo)           # lo que dice la cabecera puede ser mentira: se cuenta lo leído
            if total > MAX_TEXTO or total > presupuesto[0]:
                raise ErrorArchivo("Ese zip trae un archivo demasiado grande y no se abrió.")
            partes.append(trozo)
    presupuesto[0] -= total
    return decodificar(b"".join(partes))


def _leer_zip(ruta):
    try:
        z = zipfile.ZipFile(ruta)
    except (zipfile.BadZipFile, OSError) as e:
        raise ErrorArchivo("Ese zip está dañado o no es un zip.") from e
    presupuesto = [MAX_TOTAL_ZIP]
    with z:
        miembros = z.infolist()
        if len(miembros) > MAX_MIEMBROS:
            raise ErrorArchivo("Ese zip trae demasiados archivos y no se abrió.")
        utiles = [m for m in miembros if not m.is_dir()
                  and m.filename.lower().endswith((".json", ".csv", ".tsv", ".txt"))]
        base = {m.filename: _normal(Path(m.filename.replace("\\", "/")).stem) for m in utiles}
        try:
            # Spotify
            for m in utiles:
                if base[m.filename] == "yourlibrary" and m.filename.lower().endswith(".json"):
                    s, p, c = leer_json(_leer_miembro(z, m, presupuesto))
                    return _resultado(s, p, c)
            tablas = [m for m in utiles if m.filename.lower().endswith((".csv", ".tsv"))]
            gustan = [m for m in tablas if _ME_GUSTA.search(base[m.filename])]
            musica = [m for m in tablas if _BIBLIOTECA.search(base[m.filename])]
            for grupo, aviso in ((gustan, ""), (musica, "No venía la lista de me gusta: se traen las "
                                                        "canciones de tu biblioteca de YouTube Music.")):
                r = _juntar(z, grupo, presupuesto)
                if r:
                    return _resultado(r[0], _plataforma(r[0]), r[1], aviso)
            if len(tablas) == 1:
                r = _juntar(z, tablas, presupuesto)
                if r:
                    return _resultado(r[0], _plataforma(r[0]), r[1])
            if len(tablas) > 1:
                raise ErrorArchivo("Ese zip trae varias listas. Ábrelo y elige el .csv que quieras pasar.")
            if any(base[m.filename].startswith(("streaminghistory", "playlist")) for m in utiles):
                raise ErrorArchivo("Ese zip de Spotify no trae YourLibrary.json, donde están tus me gusta.")
            textos = [m for m in utiles if m.filename.lower().endswith(".txt")]
            if len(textos) == 1:
                return _resultado("", "tu lista", leer_texto(_leer_miembro(z, textos[0], presupuesto)))
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, OSError) as e:
            raise ErrorArchivo("Ese zip está dañado: no se pudo leer.") from e
        except Exception as e:  # noqa: BLE001 - zlib.error y parecidos
            if isinstance(e, ErrorArchivo):
                raise
            raise ErrorArchivo("Ese zip está dañado: no se pudo leer.") from e
    raise ErrorArchivo("En ese zip no encontré tus me gusta.")


def _juntar(z, grupo, presupuesto):
    canciones, servicio = [], ""
    for m in grupo[:MAX_LEIDOS]:
        try:
            s, c = leer_csv(_leer_miembro(z, m, presupuesto))
        except ErrorArchivo as e:
            if "columnas" in str(e):
                continue              # ese .csv no era de canciones
            raise
        servicio = servicio or s
        canciones += c
    return (servicio, canciones) if canciones else None


def _plataforma(servicio):
    return {"spotify": "Spotify", "youtube": "YouTube Music", "soundcloud": "SoundCloud"}.get(
        servicio, "tu archivo")


# ---------------------------------------------------------------- puerta de entrada

def desde_archivo(ruta):
    """{'servicio', 'plataforma', 'titulo', 'canciones', ...} o ErrorArchivo."""
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext not in EXTENSIONES:
        raise ErrorArchivo("Elige un archivo .zip, .json, .csv o .txt.")
    try:
        tamano = ruta.stat().st_size
    except OSError as e:
        raise ErrorArchivo("No se pudo abrir ese archivo.") from e
    if ext == ".zip":
        return _leer_zip(ruta)
    if tamano > MAX_TEXTO:
        raise ErrorArchivo("Ese archivo es demasiado grande para ser una lista de canciones.")
    try:
        texto = decodificar(ruta.read_bytes())
    except OSError as e:
        raise ErrorArchivo("No se pudo abrir ese archivo.") from e
    if not texto.strip():
        raise ErrorArchivo("Ese archivo está vacío.")
    if ext == ".json":
        s, p, c = leer_json(texto)
        return _resultado(s, p, c)
    if ext in (".csv", ".tsv"):
        s, c = leer_csv(texto)
        return _resultado(s, _plataforma(s), c)
    # un .txt puede ser también una tabla guardada como texto
    try:
        s, c = leer_csv(texto)
        if c:
            return _resultado(s, _plataforma(s), c)
    except ErrorArchivo:
        pass
    return _resultado("", "tu lista", leer_texto(texto))
