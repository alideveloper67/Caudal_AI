# -*- coding: utf-8 -*-
"""Catalogo en linea: YouTube Music para buscar y explorar, yt-dlp para sonar.

Todo aqui es bloqueante: la interfaz lo llama desde hilos (ui/hilos.py).

Las piezas que devuelve son diccionarios simples:

  pista    {"tipo": "pista", "clave", "video_id", "titulo", "artistas": [..],
            "artista", "album": {"nombre", "id"}, "duracion", "miniatura",
            "es_video", "explicito"}
  album    {"tipo": "album", "id", "titulo", "subtitulo", "miniatura", "anio"}
  lista    {"tipo": "lista", "id", "titulo", "subtitulo", "miniatura"}
  artista  {"tipo": "artista", "id", "titulo", "subtitulo", "miniatura"}
  radio    {"tipo": "radio", "id" (playlistId), "video_id", "titulo", ...}

Se piden los datos en ingles porque el analizador de ytmusicapi solo reconoce
bien las secciones en ese idioma; los titulos se traducen aqui.
"""

import re
import shutil
import threading
import time

import requests

from . import elegir_letra

REGION = "PE"
_local = threading.local()


class ErrorCatalogo(Exception):
    pass


def _yt():
    """Un cliente por hilo: la sesion HTTP de ytmusicapi no es segura entre hilos."""
    cliente = getattr(_local, "yt", None)
    region = getattr(_local, "region", None)
    if cliente is None or region != REGION:
        from ytmusicapi import YTMusic
        cliente = YTMusic(language="en", location=REGION)
        _local.yt = cliente
        _local.region = REGION
    return cliente


def fijar_region(codigo):
    global REGION
    codigo = (codigo or "").strip().upper()
    if len(codigo) == 2:
        REGION = codigo


# ---------------------------------------------------------------- utilidades

TRADUCCIONES = {
    "quick picks": "Selección rápida",
    "song mixes": "Mixes para ti",
    "mixed for you": "Mezclas para ti",
    "listen again": "Volver a escuchar",
    "new releases": "Novedades",
    "new albums & singles": "Álbumes y sencillos nuevos",
    "throwback jams": "Clásicos que vuelven",
    "all-time essentials": "Imprescindibles de siempre",
    "happy melodies": "Melodías alegres",
    "trending community playlists": "Listas en tendencia",
    "trending songs for you": "Canciones en tendencia",
    "trending": "En tendencia",
    "recommended music videos": "Videos musicales recomendados",
    "music videos for you": "Videos musicales para ti",
    "forgotten favorites": "Favoritos olvidados",
    "from the community": "De la comunidad",
    "top songs": "Canciones más escuchadas",
    "top music videos": "Videos musicales más vistos",
    "top artists": "Artistas más escuchados",
    "songs": "Canciones",
    "albums": "Álbumes",
    "singles": "Sencillos",
    "singles & eps": "Sencillos y EP",
    "videos": "Videos",
    "featured on": "Aparece en",
    "fans might also like": "A sus fans también les gusta",
    "playlists": "Listas",
    "playlists by": "Listas de",
    "live performances": "En vivo",
    "latest episodes": "Episodios recientes",
    "moods & moments": "Momentos y estados de ánimo",
    "genres": "Géneros",
    "popular": "Popular",
    "relaxing": "Para relajarse",
    "energizing": "Con energía",
    "workout": "Para entrenar",
    "commute": "De camino",
    "focus": "Concentración",
    "party": "Fiesta",
    "romance": "Romance",
    "sleep": "Para dormir",
    "feel good": "Buen rollo",
    "sad": "Melancolía",
    "chill": "Tranquilo",
    "featured playlists": "Listas destacadas",
    "albums & singles": "Álbumes y sencillos",
    "music videos": "Videos musicales",
    "new music videos": "Videos musicales nuevos",
    "romantic moods": "Para el romance",
    "your favorites": "Tus favoritos",
    "covers and remixes": "Versiones y remixes",
    "long listening": "Para escuchar largo rato",
    "mixes": "Mixes",
    "decades": "Décadas",
    "family": "En familia",
    "christian & gospel": "Cristiana y gospel",
    "country & americana": "Country",
    "dance & electronic": "Dance y electrónica",
    "folk & acoustic": "Folk y acústica",
    "hip-hop en español": "Hip-hop en español",
    "indie & alternative": "Indie y alternativa",
    "classical": "Clásica",
    "brazilian funk": "Funk brasileño",
    "african": "Africana",
    "arabic": "Árabe",
    "blues": "Blues",
    "metal": "Metal",
    "pop": "Pop",
    "r&b & soul": "R&B y soul",
    "reggae & caribbean": "Reggae y caribeña",
    "rock": "Rock",
    "soundtracks & musicals": "Bandas sonoras",
    "latin": "Latina",
    "salsa": "Salsa",
    "bachata": "Bachata",
    "regional mexican": "Regional mexicana",
    "reggaeton": "Reguetón",
    "kids": "Infantil",
    "holiday": "Navidad",
    "korean hip-hop": "Hip-hop coreano",
    "j-pop": "J-Pop",
    "k-pop": "K-Pop",
    "jazz": "Jazz",
    "cumbia": "Cumbia",
    "1980s": "Años 80",
    "1990s": "Años 90",
    "2000s": "Años 2000",
    "2010s": "Años 2010",
    "1970s": "Años 70",
    "1960s": "Años 60",
    "energy boosters": "Para cargar energía",
    "feel good": "Buen rollo",
    "gaming": "Para jugar",
    "romance": "Romance",
    "sad": "Melancolía",
    "sleep": "Para dormir",
    "workout": "Para entrenar",
    "party": "Fiesta",
    "focus": "Concentración",
    "community playlists": "Listas de la comunidad",
    "album": "Álbum",
    "single": "Sencillo",
    "ep": "EP",
    "song": "Canción",
    "video": "Video",
    "playlist": "Lista",
    "artist": "Artista",
    "station": "Radio",
    "views": "reproducciones",
    "subscribers": "suscriptores",
    "monthly audience": "oyentes al mes",
}


def traducir(texto):
    if not texto:
        return ""
    t = TRADUCCIONES.get(texto.strip().lower())
    if t:
        return t
    # "Similar to X", "More from X"...
    m = re.match(r"(?i)^similar to (.+)$", texto.strip())
    if m:
        return "Parecido a " + m.group(1)
    m = re.match(r"(?i)^playlists by (.+)$", texto.strip())
    if m:
        return "Listas de " + m.group(1)
    m = re.match(r"(?i)^more from (.+)$", texto.strip())
    if m:
        return "Más de " + m.group(1)
    m = re.match(r"(?i)^(.+) radio$", texto.strip())
    if m and len(texto) < 60:
        return "Radio de " + m.group(1)
    return texto


def traducir_subtitulo(texto):
    """'Album • 2021' -> 'Álbum • 2021', '1.2M views' -> '1.2M reproducciones'."""
    if not texto:
        return ""
    partes = [p.strip() for p in texto.split("•")]
    salida = []
    for p in partes:
        t = TRADUCCIONES.get(p.lower())
        if t:
            salida.append(t)
            continue
        m = re.match(r"^([\d.,]+[KMB]?) (views|subscribers|monthly audience|plays)$", p, re.I)
        if m:
            sufijo = {"views": "reproducciones", "plays": "reproducciones",
                      "subscribers": "suscriptores",
                      "monthly audience": "oyentes al mes"}[m.group(2).lower()]
            salida.append(f"{m.group(1)} {sufijo}")
            continue
        salida.append(p)
    return " • ".join(salida)


def mejor_miniatura(thumbs, lado=544):
    """La URL mas grande, y si es de googleusercontent, pedida al tamano deseado."""
    if not thumbs:
        return ""
    if isinstance(thumbs, dict):
        thumbs = thumbs.get("thumbnails") or []
    if not thumbs:
        return ""
    url = max(thumbs, key=lambda t: (t.get("width") or 0)).get("url", "")
    return agrandar_miniatura(url, lado)


def agrandar_miniatura(url, lado=544):
    if not url:
        return ""
    if "googleusercontent.com" in url or "ggpht.com" in url:
        url = re.sub(r"=w\d+-h\d+[^&?]*$", f"=w{lado}-h{lado}-l90-rj", url)
        url = re.sub(r"=s\d+[^&?]*$", f"=w{lado}-h{lado}-l90-rj", url)
    return url


def miniatura_video(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""


def segundos(texto):
    """'3:25' -> 205, '1:02:03' -> 3723."""
    if not texto:
        return 0
    if isinstance(texto, (int, float)):
        return int(texto)
    try:
        partes = [int(x) for x in str(texto).strip().split(":")]
    except ValueError:
        return 0
    total = 0
    for p in partes:
        total = total * 60 + p
    return total


def _runs(obj):
    if not obj:
        return []
    return obj.get("runs") or []


def _texto(obj):
    return "".join(r.get("text", "") for r in _runs(obj))


def _nav(obj, *ruta, defecto=None):
    for k in ruta:
        try:
            obj = obj[k]
        except (KeyError, IndexError, TypeError):
            return defecto
    return obj


def video_id_de(url):
    """Saca el id de un enlace de YouTube / YouTube Music, o '' si no lo es."""
    if not url:
        return ""
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else ""


def nueva_pista(video_id, titulo="", artistas=None, album=None, duracion=0,
                miniatura="", es_video=False, explicito=False):
    artistas = [a for a in (artistas or []) if a and a.get("nombre")]
    return {
        "tipo": "pista",
        "clave": f"yt:{video_id}",
        "video_id": video_id,
        "titulo": titulo or "Sin título",
        "artistas": artistas,
        "artista": ", ".join(a["nombre"] for a in artistas),
        "album": album or {},
        "duracion": int(duracion or 0),
        "miniatura": miniatura or miniatura_video(video_id),
        "es_video": bool(es_video),
        "explicito": bool(explicito),
    }


def _artistas_ytm(lista):
    salida = []
    for a in lista or []:
        nombre = a.get("name") or ""
        if not nombre or nombre.lower() in ("song", "video", "album", "single", "ep"):
            continue
        salida.append({"nombre": nombre, "id": a.get("id") or ""})
    return salida


def pista_de_ytm(x, album=None, miniatura_album=""):
    """Convierte una cancion de ytmusicapi (busqueda, radio, album) a pista."""
    vid = x.get("videoId")
    if not vid:
        return None
    alb = x.get("album") or album or {}
    if isinstance(alb, dict):
        alb = {"nombre": alb.get("name") or alb.get("nombre") or "",
               "id": alb.get("id") or alb.get("browseId") or ""}
    else:
        alb = {"nombre": str(alb), "id": ""}
    thumbs = x.get("thumbnails") or x.get("thumbnail") or []
    mini = mejor_miniatura(thumbs) if thumbs else miniatura_album
    # solo es "video" lo que se busco como video: las canciones de un album o de
    # una radio suenan como musica aunque YouTube tenga su videoclip
    es_video = x.get("resultType") == "video"
    dur = x.get("duration_seconds") or segundos(x.get("duration") or x.get("length"))
    return nueva_pista(vid, x.get("title") or "", _artistas_ytm(x.get("artists")), alb,
                       dur, mini, es_video, x.get("isExplicit"))


# ---------------------------------------------------------------- busqueda

def sugerencias(texto):
    if not texto or not texto.strip():
        return []
    try:
        return [s for s in _yt().get_search_suggestions(texto.strip()) if isinstance(s, str)][:8]
    except Exception:
        return []


def buscar(texto, filtro=None, limite=20):
    """filtro: None (todo), canciones, videos, albumes, artistas, listas."""
    texto = (texto or "").strip()
    if not texto:
        return []
    mapa = {"canciones": "songs", "videos": "videos", "albumes": "albums",
            "artistas": "artists", "listas": "playlists"}
    try:
        crudo = _yt().search(texto, filter=mapa.get(filtro), limit=limite)
    except Exception as e:
        if filtro in (None, "videos", "canciones"):
            return _buscar_ytdlp(texto, limite)
        raise ErrorCatalogo(f"No se pudo buscar: {e}") from e
    salida = []
    for x in crudo:
        el = _elemento_busqueda(x)
        if el:
            if x.get("category") == "Top result":
                el["destacado"] = True
            salida.append(el)
    if not salida and filtro in (None, "videos", "canciones"):
        return _buscar_ytdlp(texto, limite)
    return salida[:max(1, int(limite))] if filtro else salida


def buscar_todo(texto):
    """La pagina 'Todo' de la busqueda, como en Spotify: resultado principal y
    una seccion por tipo. Cada seccion se pide filtrada y en paralelo, porque la
    busqueda sin filtro de YouTube Music llega sin artistas en las canciones."""
    from concurrent.futures import ThreadPoolExecutor

    texto = (texto or "").strip()
    if not texto:
        return {"principal": None, "secciones": []}
    pedidos = [("canciones", 8), ("artistas", 8), ("albumes", 10), ("listas", 10),
               ("videos", 10)]
    resultados = {}

    def uno(par):
        filtro, n = par
        try:
            return filtro, buscar(texto, filtro, n)
        except Exception:
            return filtro, []

    def principal():
        try:
            crudo = _yt().search(texto, limit=5)
        except Exception:
            return None
        for x in crudo:
            if x.get("category") == "Top result":
                return x
        return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        fut_principal = ex.submit(principal)
        for filtro, lista in ex.map(uno, pedidos):
            resultados[filtro] = lista
        crudo_principal = fut_principal.result()

    destacado = None
    if crudo_principal:
        tipo = crudo_principal.get("resultType")
        vid = crudo_principal.get("videoId")
        if tipo in ("song", "video") and vid:
            # el mismo elemento, pero con los datos completos de la busqueda filtrada
            for lista in (resultados.get("canciones", []), resultados.get("videos", [])):
                destacado = next((p for p in lista if p.get("video_id") == vid), None)
                if destacado:
                    break
        if destacado is None:
            destacado = _elemento_busqueda(crudo_principal)
    if destacado is None:
        for filtro in ("artistas", "canciones", "albumes"):
            if resultados.get(filtro):
                destacado = resultados[filtro][0]
                break

    nombres = {"canciones": "Canciones", "artistas": "Artistas", "albumes": "Álbumes",
               "listas": "Listas", "videos": "Videos"}
    secciones = []
    for filtro, _n in pedidos:
        elementos = resultados.get(filtro) or []
        if elementos:
            secciones.append({"titulo": nombres[filtro], "filtro": filtro,
                              "estilo": "filas" if filtro == "canciones" else "carrusel",
                              "elementos": elementos})
    return {"principal": destacado, "secciones": secciones}


def _elemento_busqueda(x):
    tipo = x.get("resultType")
    if tipo in ("song", "video"):
        return pista_de_ytm(x)
    if tipo == "album":
        artistas = ", ".join(a.get("name", "") for a in x.get("artists") or [])
        sub = " • ".join(p for p in (traducir(x.get("type") or "Album"), artistas,
                                     str(x.get("year") or "")) if p)
        return {"tipo": "album", "id": x.get("browseId"), "titulo": x.get("title") or "",
                "subtitulo": sub, "miniatura": mejor_miniatura(x.get("thumbnails")),
                "anio": x.get("year") or "", "lista_id": x.get("playlistId") or ""}
    if tipo == "artist":
        nombre = x.get("artist") or x.get("title") or ""
        if not nombre and x.get("artists"):
            nombre = x["artists"][0].get("name") or ""
        bid = x.get("browseId") or (x.get("artists") or [{}])[0].get("id")
        return {"tipo": "artista", "id": bid,
                "titulo": nombre,
                "subtitulo": "Artista", "miniatura": mejor_miniatura(x.get("thumbnails")),
                "radio_id": x.get("radioId") or ""}
    if tipo == "playlist":
        bid = x.get("browseId") or ""
        return {"tipo": "lista", "id": bid[2:] if bid.startswith("VL") else bid,
                "titulo": x.get("title") or "",
                "subtitulo": " • ".join(p for p in ("Lista", x.get("author") or "",
                                                    str(x.get("itemCount") or "")) if p),
                "miniatura": mejor_miniatura(x.get("thumbnails"))}
    return None


def _buscar_ytdlp(texto, limite):
    """Respaldo si YouTube Music no responde: la busqueda normal de YouTube."""
    import yt_dlp
    opciones = {"quiet": True, "no_warnings": True, "extract_flat": True,
                "skip_download": True}
    with yt_dlp.YoutubeDL(opciones) as y:
        info = y.extract_info(f"ytsearch{limite}:{texto}", download=False)
    salida = []
    for e in info.get("entries") or []:
        vid = e.get("id")
        if not vid:
            continue
        autor = e.get("channel") or e.get("uploader") or ""
        salida.append(nueva_pista(vid, e.get("title") or "",
                                  [{"nombre": autor, "id": e.get("channel_id") or ""}] if autor else [],
                                  None, e.get("duration") or 0, miniatura_video(vid), True))
    return salida


# ---------------------------------------------------------------- paginas

def _browse(browse_id, params=None):
    cuerpo = {"browseId": browse_id}
    if params:
        cuerpo["params"] = params
    return _yt()._send_request("browse", cuerpo)


def _continuar(ctoken):
    adicional = f"&ctoken={ctoken}&continuation={ctoken}&type=next"
    return _yt()._send_request("browse", {}, adicional)


def _secciones_de(respuesta):
    contenido = _nav(respuesta, "contents", "singleColumnBrowseResultsRenderer", "tabs", 0,
                     "tabRenderer", "content", "sectionListRenderer")
    if not contenido:
        contenido = _nav(respuesta, "contents", "twoColumnBrowseResultsRenderer",
                         "secondaryContents", "sectionListRenderer")
    if not contenido:
        return [], None
    token = _nav(contenido, "continuations", 0, "nextContinuationData", "continuation")
    return contenido.get("contents") or [], token


def _item_dos_filas(r):
    """musicTwoRowItemRenderer: tarjetas de albumes, listas, artistas, videos."""
    titulo = _texto(r.get("title"))
    subtitulo = traducir_subtitulo(_texto(r.get("subtitle")))
    thumbs = _nav(r, "thumbnailRenderer", "musicThumbnailRenderer", "thumbnail", "thumbnails") \
        or _nav(r, "thumbnailRenderer", "croppedSquareThumbnailRenderer", "thumbnail", "thumbnails") or []
    mini = mejor_miniatura(thumbs)
    nav = r.get("navigationEndpoint") or {}
    if "watchEndpoint" in nav:
        we = nav["watchEndpoint"]
        vid = we.get("videoId")
        if not vid:
            return None
        artistas = []
        for run in _runs(r.get("subtitle")):
            pt = _nav(run, "navigationEndpoint", "browseEndpoint",
                      "browseEndpointContextSupportedConfigs",
                      "browseEndpointContextMusicConfig", "pageType")
            if pt in ("MUSIC_PAGE_TYPE_ARTIST", "MUSIC_PAGE_TYPE_USER_CHANNEL"):
                artistas.append({"nombre": run.get("text", ""),
                                 "id": _nav(run, "navigationEndpoint", "browseEndpoint", "browseId") or ""})
        tipo_video = _nav(we, "watchEndpointMusicSupportedConfigs", "watchEndpointMusicConfig",
                          "musicVideoType") or ""
        es_video = tipo_video != "MUSIC_VIDEO_TYPE_ATV"
        if not artistas:
            partes = [p.strip() for p in _texto(r.get("subtitle")).split("•")]
            nombre = partes[1] if len(partes) > 1 and partes[0].lower() in ("song", "video") else partes[0]
            if nombre and not re.search(r"\d.*(views|plays)", nombre, re.I):
                artistas = [{"nombre": nombre, "id": ""}]
        p = nueva_pista(vid, titulo, artistas, None, 0,
                        mini if not es_video else (mini or miniatura_video(vid)), es_video)
        p["subtitulo"] = subtitulo
        return p
    if "watchPlaylistEndpoint" in nav:
        return {"tipo": "radio", "id": nav["watchPlaylistEndpoint"].get("playlistId"),
                "titulo": titulo, "subtitulo": subtitulo, "miniatura": mini}
    be = nav.get("browseEndpoint") or {}
    bid = be.get("browseId") or ""
    tipo_pag = _nav(be, "browseEndpointContextSupportedConfigs",
                    "browseEndpointContextMusicConfig", "pageType") or ""
    if tipo_pag == "MUSIC_PAGE_TYPE_ALBUM":
        return {"tipo": "album", "id": bid, "titulo": titulo, "subtitulo": subtitulo,
                "miniatura": mini}
    if tipo_pag in ("MUSIC_PAGE_TYPE_ARTIST", "MUSIC_PAGE_TYPE_USER_CHANNEL"):
        return {"tipo": "artista", "id": bid, "titulo": titulo,
                "subtitulo": subtitulo or "Artista", "miniatura": mini}
    if tipo_pag == "MUSIC_PAGE_TYPE_PLAYLIST" or bid.startswith("VL"):
        return {"tipo": "lista", "id": bid[2:] if bid.startswith("VL") else bid,
                "titulo": titulo, "subtitulo": subtitulo, "miniatura": mini}
    if bid:
        return {"tipo": "pagina", "id": bid, "params": be.get("params"), "titulo": titulo,
                "subtitulo": subtitulo, "miniatura": mini}
    return None


def _item_lista(r):
    """musicResponsiveListItemRenderer: filas de canciones (o de albumes/artistas)."""
    columnas = [_nav(c, "musicResponsiveListItemFlexColumnRenderer", "text") or {}
                for c in r.get("flexColumns") or []]
    if not columnas:
        return None
    titulo = _texto(columnas[0])
    vid = _nav(r, "playlistItemData", "videoId") \
        or _nav(columnas[0], "runs", 0, "navigationEndpoint", "watchEndpoint", "videoId") \
        or _nav(r, "overlay", "musicItemThumbnailOverlayRenderer", "content",
                "musicPlayButtonRenderer", "playNavigationEndpoint", "watchEndpoint", "videoId")
    thumbs = _nav(r, "thumbnail", "musicThumbnailRenderer", "thumbnail", "thumbnails") or []
    if not vid:
        # una fila que apunta a un album, artista o lista
        be = _nav(r, "navigationEndpoint", "browseEndpoint") or {}
        bid = be.get("browseId") or ""
        tipo_pag = _nav(be, "browseEndpointContextSupportedConfigs",
                        "browseEndpointContextMusicConfig", "pageType") or ""
        sub = traducir_subtitulo(" • ".join(_texto(c) for c in columnas[1:] if _texto(c)))
        if tipo_pag == "MUSIC_PAGE_TYPE_ALBUM":
            return {"tipo": "album", "id": bid, "titulo": titulo, "subtitulo": sub,
                    "miniatura": mejor_miniatura(thumbs)}
        if tipo_pag in ("MUSIC_PAGE_TYPE_ARTIST", "MUSIC_PAGE_TYPE_USER_CHANNEL"):
            return {"tipo": "artista", "id": bid, "titulo": titulo, "subtitulo": sub,
                    "miniatura": mejor_miniatura(thumbs)}
        if tipo_pag == "MUSIC_PAGE_TYPE_PLAYLIST":
            return {"tipo": "lista", "id": bid[2:] if bid.startswith("VL") else bid,
                    "titulo": titulo, "subtitulo": sub, "miniatura": mejor_miniatura(thumbs)}
        return None

    artistas, album = [], {}
    extra = []
    for col in columnas[1:]:
        for run in _runs(col):
            be = _nav(run, "navigationEndpoint", "browseEndpoint") or {}
            pt = _nav(be, "browseEndpointContextSupportedConfigs",
                      "browseEndpointContextMusicConfig", "pageType") or ""
            texto = run.get("text", "")
            if pt in ("MUSIC_PAGE_TYPE_ARTIST", "MUSIC_PAGE_TYPE_USER_CHANNEL"):
                artistas.append({"nombre": texto, "id": be.get("browseId", "")})
            elif pt == "MUSIC_PAGE_TYPE_ALBUM":
                album = {"nombre": texto, "id": be.get("browseId", "")}
            elif texto.strip() not in ("", "•", " • ", "&", ","):
                extra.append(texto.strip())
    if not artistas and extra:
        candidato = extra[0]
        if candidato.lower() not in ("song", "video") and not re.search(r"\d", candidato):
            artistas = [{"nombre": candidato, "id": ""}]
    duracion = 0
    for fc in r.get("fixedColumns") or []:
        t = _texto(_nav(fc, "musicResponsiveListItemFixedColumnRenderer", "text"))
        if re.match(r"^\d+:\d{2}(:\d{2})?$", t.strip()):
            duracion = segundos(t)
    if not duracion:
        for e in extra:
            if re.match(r"^\d+:\d{2}(:\d{2})?$", e):
                duracion = segundos(e)
    es_video = False      # las filas son canciones (Seleccion rapida, populares...)
    p = nueva_pista(vid, titulo, artistas, album, duracion,
                    mejor_miniatura(thumbs) or miniatura_video(vid), es_video,
                    bool(r.get("badges")))
    vistas = [e for e in extra if re.search(r"(views|plays)", e, re.I)]
    if vistas:
        p["subtitulo"] = traducir_subtitulo(vistas[0])
    return p


def _analizar_seccion(s):
    """Devuelve {"titulo", "estilo": carrusel|filas|rejilla, "elementos", "mas"}."""
    if "musicCarouselShelfRenderer" in s:
        c = s["musicCarouselShelfRenderer"]
        cab = _nav(c, "header", "musicCarouselShelfBasicHeaderRenderer") or {}
        titulo = _texto(cab.get("title"))
        estribillo = _texto(cab.get("strapline"))
        mas = _nav(cab, "moreContentButton", "buttonRenderer", "navigationEndpoint",
                   "browseEndpoint") or _nav(cab, "title", "runs", 0, "navigationEndpoint",
                                             "browseEndpoint")
        elementos = []
        for it in c.get("contents") or []:
            el = None
            if "musicTwoRowItemRenderer" in it:
                el = _item_dos_filas(it["musicTwoRowItemRenderer"])
            elif "musicResponsiveListItemRenderer" in it:
                el = _item_lista(it["musicResponsiveListItemRenderer"])
            elif "musicMultiRowListItemRenderer" in it:
                el = None
            if el:
                elementos.append(el)
        estilo = "filas" if elementos and all(e["tipo"] == "pista" and not e.get("es_video")
                                              for e in elementos) \
            and any("musicResponsiveListItemRenderer" in it for it in c.get("contents") or []) \
            else "carrusel"
        return {"titulo": traducir(titulo), "estribillo": "", "estilo": estilo,
                "elementos": elementos,
                "mas": {"id": mas.get("browseId"), "params": mas.get("params")} if mas else None}
    if "musicShelfRenderer" in s:
        c = s["musicShelfRenderer"]
        elementos = []
        for it in c.get("contents") or []:
            if "musicResponsiveListItemRenderer" in it:
                el = _item_lista(it["musicResponsiveListItemRenderer"])
                if el:
                    elementos.append(el)
        mas = _nav(c, "bottomEndpoint", "browseEndpoint") or _nav(
            c, "title", "runs", 0, "navigationEndpoint", "browseEndpoint")
        return {"titulo": traducir(_texto(c.get("title"))), "estilo": "filas",
                "elementos": elementos,
                "mas": {"id": mas.get("browseId"), "params": mas.get("params")} if mas else None}
    if "gridRenderer" in s:
        c = s["gridRenderer"]
        titulo = _texto(_nav(c, "header", "gridHeaderRenderer", "title"))
        elementos = []
        for it in c.get("items") or []:
            if "musicTwoRowItemRenderer" in it:
                el = _item_dos_filas(it["musicTwoRowItemRenderer"])
                if el:
                    elementos.append(el)
            elif "musicNavigationButtonRenderer" in it:
                b = it["musicNavigationButtonRenderer"]
                be = _nav(b, "clickCommand", "browseEndpoint") or {}
                color = _nav(b, "solid", "leftStripeColor") or 0
                elementos.append({"tipo": "genero", "id": be.get("browseId"),
                                  "params": be.get("params"),
                                  "titulo": traducir(_texto(b.get("buttonText"))),
                                  "color": "#%06X" % (int(color) & 0xFFFFFF)})
        return {"titulo": traducir(titulo), "estilo": "rejilla", "elementos": elementos,
                "mas": None}
    if "musicDescriptionShelfRenderer" in s:
        c = s["musicDescriptionShelfRenderer"]
        return {"titulo": traducir(_texto(c.get("header"))), "estilo": "texto",
                "texto": _texto(c.get("description")), "elementos": [], "mas": None}
    return None


def pagina(browse_id, params=None, continuar=1):
    """Cualquier pagina de YouTube Music (inicio, generos, novedades...) en secciones."""
    respuesta = _browse(browse_id, params)
    contenido, token = _secciones_de(respuesta)
    secciones = [x for x in (_analizar_seccion(s) for s in contenido) if x]
    vueltas = 0
    while token and vueltas < continuar:
        vueltas += 1
        try:
            mas = _continuar(token)
        except Exception:
            break
        cont = _nav(mas, "continuationContents", "sectionListContinuation") or {}
        for s in cont.get("contents") or []:
            x = _analizar_seccion(s)
            if x:
                secciones.append(x)
        token = _nav(cont, "continuations", 0, "nextContinuationData", "continuation")
    titulo = _texto(_nav(respuesta, "header", "musicHeaderRenderer", "title")) \
        or _texto(_nav(respuesta, "header", "musicImmersiveHeaderRenderer", "title"))
    return {"titulo": traducir(titulo),
            "secciones": [s for s in secciones if s["elementos"] or s.get("texto")]}


def inicio():
    return pagina("FEmusic_home", continuar=2)


_PORTADAS_GENERO = None


def portada_genero(browse_id, params):
    """La portada de la primera lista de un genero, para ilustrar su tarjeta.
    Se guarda una semana en disco: solo se busca una vez."""
    global _PORTADAS_GENERO
    import json
    from .config import carpeta_datos
    archivo = carpeta_datos() / "portadas_generos.json"
    with _cerrojo:
        if _PORTADAS_GENERO is None:
            try:
                _PORTADAS_GENERO = json.loads(archivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                _PORTADAS_GENERO = {}
        clave = f"{browse_id}|{params}"
        dato = _PORTADAS_GENERO.get(clave)
        if dato and time.time() - dato[1] < 7 * 86400:
            return dato[0]
    url = ""
    try:
        datos = pagina(browse_id, params, continuar=0)
        for sec in datos.get("secciones") or []:
            for el in sec.get("elementos") or []:
                if el.get("miniatura"):
                    url = agrandar_miniatura(el["miniatura"], 300)
                    break
            if url:
                break
    except Exception:
        return ""
    with _cerrojo:
        _PORTADAS_GENERO[clave] = [url, time.time()]
        try:
            archivo.write_text(json.dumps(_PORTADAS_GENERO), encoding="utf-8")
        except OSError:
            pass
    return url


def explorar():
    """Novedades + generos y estados de animo."""
    salida = []
    try:
        nuevos = pagina("FEmusic_new_releases")
        salida += [s for s in nuevos["secciones"] if s["titulo"]][:3]
    except Exception:
        pass
    try:
        generos = pagina("FEmusic_moods_and_genres")
        salida += [s for s in generos["secciones"] if s["titulo"]]
    except Exception:
        pass
    return {"titulo": "Explorar", "secciones": salida}


def artista(browse_id):
    respuesta = _browse(browse_id)
    cab = _nav(respuesta, "header", "musicImmersiveHeaderRenderer") \
        or _nav(respuesta, "header", "musicVisualHeaderRenderer") or {}
    nombre = _texto(cab.get("title"))
    descripcion = _texto(cab.get("description"))
    thumbs = _nav(cab, "thumbnail", "musicThumbnailRenderer", "thumbnail", "thumbnails") or []
    foto = mejor_miniatura(thumbs, 1200)
    suscriptores = _texto(_nav(cab, "subscriptionButton", "subscribeButtonRenderer",
                               "subscriberCountText"))
    oyentes = _texto(cab.get("monthlyListenerCount"))
    def id_boton(boton):
        # el boton trae watchPlaylistEndpoint o (ahora) watchEndpoint con playlistId
        fin = _nav(cab, boton, "buttonRenderer", "navigationEndpoint") or {}
        return (_nav(fin, "watchPlaylistEndpoint", "playlistId")
                or _nav(fin, "watchEndpoint", "playlistId") or "")
    radio = id_boton("startRadioButton")
    aleatorio = id_boton("playButton")
    contenido, _ = _secciones_de(respuesta)
    secciones = [x for x in (_analizar_seccion(s) for s in contenido) if x]
    for s in secciones:
        if s.get("estilo") == "texto" and not descripcion:
            descripcion = s.get("texto", "")
    secciones = [s for s in secciones if s["elementos"]]
    return {
        "tipo": "artista", "id": browse_id, "titulo": nombre, "foto": foto,
        "descripcion": descripcion,
        "subtitulo": traducir_subtitulo(oyentes or (suscriptores and suscriptores + " subscribers") or ""),
        "radio_id": radio, "aleatorio_id": aleatorio, "secciones": secciones,
    }


def album(browse_id):
    a = _yt().get_album(browse_id)
    portada = mejor_miniatura(a.get("thumbnails"), 800)
    alb = {"nombre": a.get("title") or "", "id": browse_id}
    pistas = []
    for t in a.get("tracks") or []:
        p = pista_de_ytm(t, album=alb, miniatura_album=portada)
        if p:
            p["miniatura"] = portada or p["miniatura"]
            p["album"] = alb
            if not p["artistas"]:
                p["artistas"] = _artistas_ytm(a.get("artists"))
                p["artista"] = ", ".join(x["nombre"] for x in p["artistas"])
            pistas.append(p)
    artistas = _artistas_ytm(a.get("artists"))
    duracion = sum(p["duracion"] for p in pistas)
    return {
        "tipo": "album", "id": browse_id, "titulo": a.get("title") or "",
        "tipo_album": traducir(a.get("type") or "Album"),
        "artistas": artistas, "anio": a.get("year") or "", "miniatura": portada,
        "descripcion": a.get("description") or "", "pistas": pistas, "duracion": duracion,
        "lista_id": a.get("audioPlaylistId") or "",
    }


def lista(playlist_id, limite=300):
    """Una lista de YouTube / YouTube Music. Se lee con yt-dlp, que aguanta mejor
    los cambios de YouTube que el analizador de ytmusicapi."""
    import yt_dlp
    pid = playlist_id[2:] if playlist_id.startswith("VL") else playlist_id
    opciones = {"quiet": True, "no_warnings": True, "extract_flat": True,
                "skip_download": True, "playlistend": limite}
    with yt_dlp.YoutubeDL(opciones) as y:
        info = y.extract_info(f"https://music.youtube.com/playlist?list={pid}", download=False)
    pistas = []
    for e in info.get("entries") or []:
        vid = e.get("id")
        if not vid or len(vid) != 11:
            continue
        autor = e.get("channel") or e.get("uploader") or ""
        autor = re.sub(r"\s*-\s*Topic$", "", autor)
        mini = ""
        if e.get("thumbnails"):
            mini = mejor_miniatura(e["thumbnails"])
        pistas.append(nueva_pista(vid, e.get("title") or "",
                                  [{"nombre": autor, "id": e.get("channel_id") or ""}] if autor else [],
                                  None, e.get("duration") or 0,
                                  mini or miniatura_video(vid), False))
    portada = ""
    if info.get("thumbnails"):
        portada = mejor_miniatura(info["thumbnails"], 800)
    if not portada and pistas:
        portada = pistas[0]["miniatura"]
    return {
        "tipo": "lista", "id": pid, "titulo": info.get("title") or "Lista",
        "autor": re.sub(r"\s*-\s*Topic$", "", info.get("uploader") or info.get("channel") or ""),
        "descripcion": info.get("description") or "", "miniatura": portada,
        "pistas": pistas, "duracion": sum(p["duracion"] for p in pistas),
    }


def radio(video_id=None, playlist_id=None, limite=50):
    """La radio infinita de YouTube Music a partir de una cancion o una emisora.

    No se rinde a la primera: un fallo de red se reintenta, la radio de una cancion prueba tambien
    la peticion sin parametros de radio y, si falla una emisora (la «radio del artista»), se arma con
    su primera cancion o, de ultimo, con las canciones de la propia lista."""
    import time
    ultimo = []
    # la radio de una canción se guarda (recientes, inicio) con el id de su VIDEO: si llega
    # como emisora, YouTube la busca como lista privada y falla. Un id de 11 caracteres es
    # un video, no una lista (las listas empiezan por PL, RD, OL, VL… y son más largas).
    if playlist_id and not video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", str(playlist_id)):
        video_id, playlist_id = str(playlist_id), None

    def intentar(**kw):
        for vez in range(2):
            try:
                w = _yt().get_watch_playlist(limit=limite, **kw)
            except Exception as e:                     # red, tiempo o un cambio de YouTube
                ultimo[:] = [e]
                texto = str(e).lower()
                if vez == 0 and any(x in texto for x in ("timeout", "timed out", "connection", "resolve")):
                    time.sleep(0.7)
                    continue
                return None
            pistas = [p for p in (pista_de_ytm(t) for t in w.get("tracks") or []) if p]
            if pistas:
                return {"pistas": pistas, "letras_id": w.get("lyrics") or "",
                        "relacionados_id": w.get("related") or ""}
            ultimo[:] = ["YouTube Music no devolvió canciones"]
            return None
        return None

    solo_video = bool(video_id and not playlist_id)
    r = intentar(videoId=video_id, playlistId=playlist_id, radio=solo_video)
    if r:
        return r
    if solo_video:                                      # sin los parametros especiales de «radio»
        r = intentar(videoId=video_id)
        if r:
            return r
    if playlist_id:                                     # una emisora: su primera cancion, o la propia lista
        try:
            de_lista = lista(playlist_id, limite=60)["pistas"]
        except Exception as e:
            ultimo[:] = ultimo or [e]
            de_lista = []
        if de_lista:
            r = intentar(videoId=de_lista[0]["video_id"], radio=True)
            return r or {"pistas": de_lista[:limite], "letras_id": "", "relacionados_id": ""}
    raise ErrorCatalogo(f"No se pudo crear la radio: {ultimo[0] if ultimo else 'YouTube Music no devolvió canciones'}")


def relacionados(video_id):
    """Secciones 'Relacionado' de una cancion (para el panel lateral)."""
    w = _yt().get_watch_playlist(videoId=video_id, limit=1)
    rid = w.get("related")
    if not rid:
        return []
    respuesta = _browse(rid)
    contenido = _nav(respuesta, "contents", "sectionListRenderer", "contents") or []
    return [x for x in (_analizar_seccion(s) for s in contenido) if x and x["elementos"]]


# ---------------------------------------------------------------- letras

def _lrc_a_lineas(texto):
    """[(ms, verso)] de un texto LRC: con [offset:…], marcas por palabra <mm:ss> y varias marcas por verso."""
    corrido = 0
    m = re.search(r"\[offset:\s*([+-]?\d+)\s*\]", texto or "", flags=re.I)
    if m:
        corrido = int(m.group(1))            # en LRC, positivo = la letra va antes
    lineas = []
    for fila in (texto or "").splitlines():
        marcas = re.findall(r"\[(\d+):(\d+(?:[.:]\d+)?)\]", fila)
        contenido = re.sub(r"\[\d+:\d+(?:[.:]\d+)?\]|<\d+:\d+(?:[.:]\d+)?>", "", fila)
        contenido = re.sub(r"\s+", " ", contenido).strip()
        for mm, ss in marcas:
            ms = int((int(mm) * 60 + float(ss.replace(":", "."))) * 1000) - corrido
            lineas.append((max(0, ms), contenido))
    lineas.sort(key=lambda x: x[0])
    return lineas


_CAB_LRCLIB = {"User-Agent": "Caudal (reproductor de escritorio)"}


def _lrclib(ruta, params):
    """Lo que responde LRCLIB, o None si no está (o no contesta)."""
    try:
        r = requests.get(f"https://lrclib.net/api/{ruta}", params=params, headers=_CAB_LRCLIB, timeout=10)
        return r.json() if r.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def _candidatas_lrclib(pista):
    """Las fichas de LRCLIB que podrían ser esta canción, sin repetir (aún sin comprobar)."""
    salida, vistas = [], set()

    def sumar(x):
        for c in (x if isinstance(x, list) else [x]):
            if isinstance(c, dict) and c.get("id") not in vistas:
                vistas.add(c.get("id"))
                salida.append(c)
    dur = int(pista.get("duracion") or 0)
    for titulo, artista, _valen in elegir_letra.consultas(pista)[:2]:
        params = {"track_name": titulo, "artist_name": artista}
        if dur:
            exacta = _lrclib("get", dict(params, duration=dur))
            if exacta:
                sumar(exacta)
                if (exacta.get("syncedLyrics") or "").strip():
                    continue
        sumar(_lrclib("search", params) or [])
        if not any((c.get("syncedLyrics") or "").strip() for c in salida):
            sumar(_lrclib("search", {"q": f"{artista} {titulo}".strip()}) or [])
    return salida


def _letra_youtube(vid):
    """(líneas con tiempos, texto, fuente) de YouTube Music para ese video exacto."""
    if not vid:
        return [], "", ""
    try:
        lid = _yt().get_watch_playlist(videoId=vid, limit=1).get("lyrics")
        if not lid:
            return [], "", ""
        try:
            l = _yt().get_lyrics(lid, timestamps=True)
            if l and l.get("hasTimestamps"):
                lineas = [(int(x.start_time), x.text) for x in l.get("lyrics") or []]
                if any((t or "").strip(" ♪") for _ms, t in lineas):
                    return lineas, "\n".join(t for _ms, t in lineas), l.get("source") or "YouTube Music"
        except Exception:  # noqa: BLE001  (sin tiempos: se pide el texto)
            pass
        l = _yt().get_lyrics(lid)
        if l and l.get("lyrics"):
            return [], l["lyrics"], l.get("source") or "YouTube Music"
    except Exception:  # noqa: BLE001
        pass
    return [], "", ""


def _cancion_oficial(pista, texto=""):
    """La canción de YouTube Music de la que sale este video (o archivo), con su letra y sus tiempos:
    {"video_id", "duracion", "lineas", "texto", "fuente"}, o None. `texto`: la letra ya sabida, para no
    quedarse con otra canción."""
    dur = float(pista.get("duracion") or 0)
    for titulo, artista, _valen in elegir_letra.consultas(pista)[:2]:
        try:
            crudo = _yt().search(f"{artista} {titulo}".strip(), filter="songs", limit=10)
        except Exception:  # noqa: BLE001
            continue
        buenas = []
        for x in crudo or []:
            ficha = {"trackName": x.get("title"), "albumName": (x.get("album") or {}).get("name"),
                     "artistName": ", ".join(z.get("name") or "" for z in x.get("artists") or [])}
            if x.get("videoId") and x["videoId"] != pista.get("video_id") and elegir_letra.es_la_cancion(ficha, pista):
                buenas.append((abs(float(x.get("duration_seconds") or 0) - dur) if dur else 0, x))
        buenas.sort(key=lambda z: z[0])
        for _d, x in buenas[:2]:
            lineas, tx, fuente = _letra_youtube(x["videoId"])
            if lineas and (not texto or elegir_letra.palabras_en_comun(tx, texto) >= elegir_letra.PARECIDO_TEXTO_MIN):
                return {"video_id": x["videoId"], "duracion": float(x.get("duration_seconds") or 0),
                        "lineas": lineas, "texto": tx, "fuente": fuente}
    return None


def letras(pista):
    """{"sincronizada": bool, "lineas": [(ms, texto)] o [], "texto": str, "fuente", "verificada": bool}.

    La letra tiene que ser la de esta canción (descargador/elegir_letra.py) y sus tiempos, los del audio
    que suena:
    1. la que YouTube Music trae con tiempos para ese mismo video;
    2. la de la canción oficial de la que sale el video, si dura lo mismo. Si dura distinto, va
       «otra_duracion» hasta que cotejo_audio compare el sonido de las dos y la ponga a tiempo;
    3. la de LRCLIB con el mismo título, artista, versión y duración y, si se sabe el texto, con las
       mismas palabras;
    4. solo texto. Antes que enseñar la letra de otra canción, ninguna.
    «ref» es el video de YouTube Music al que pertenecen los tiempos («ref_lineas»)."""
    vid, dur = pista.get("video_id") or "", float(pista.get("duracion") or 0)
    lineas, texto_yt, fuente_yt = _letra_youtube(vid)
    if lineas:
        return {"sincronizada": True, "lineas": lineas, "texto": texto_yt, "fuente": fuente_yt,
                "verificada": True, "duracion": dur, "ref": vid, "ref_lineas": lineas}
    of = _cancion_oficial(pista, texto_yt)
    if of is not None and dur and abs(of["duracion"] - dur) <= elegir_letra.DIFERENCIA_OFICIAL:
        return {"sincronizada": True, "lineas": of["lineas"], "texto": of["texto"], "fuente": of["fuente"],
                "verificada": True, "duracion": of["duracion"], "ref": of["video_id"], "ref_lineas": of["lineas"]}
    bueno = texto_yt or (of["texto"] if of else "")
    con, texto, otra = elegir_letra.elegir(_candidatas_lrclib(pista), pista, bueno)
    ref = {"ref": of["video_id"], "ref_lineas": of["lineas"]} if of else {}
    if of is not None and con is not None:
        # LRCLIB tiene fichas con la duración del video y los tiempos del disco, sin ajustar: si van igual
        # que la canción oficial aunque el video dure distinto, no son de fiar
        c = elegir_letra.corrimiento(_lrc_a_lineas(con["syncedLyrics"]), of["lineas"])
        if c is None or abs(c) <= 1.0:
            con = None
    if of is not None and con is None:
        return dict({"sincronizada": True, "lineas": of["lineas"], "texto": of["texto"], "fuente": of["fuente"],
                     "verificada": True, "duracion": of["duracion"], "otra_duracion": True}, **ref)
    for c, distinta in ((con, False), (otra, True)):
        if c is None:
            continue
        d = dict({"sincronizada": True, "lineas": _lrc_a_lineas(c["syncedLyrics"]), "texto": c.get("plainLyrics") or "",
                  "fuente": "LRCLIB", "duracion": float(c.get("duration") or 0), "verificada": bool(bueno)}, **ref)
        if distinta:
            d["otra_duracion"] = True
        if d["lineas"]:
            return d
    if texto_yt:
        return {"sincronizada": False, "lineas": [], "texto": texto_yt, "fuente": fuente_yt, "verificada": True}
    if texto is not None:
        return {"sincronizada": False, "lineas": [], "texto": elegir_letra.texto_de(texto), "fuente": "LRCLIB",
                "verificada": False}
    return {"sincronizada": False, "lineas": [], "texto": "", "fuente": ""}


def letras_alternativas(pista, limite=8):
    """Otras letras de LRCLIB para la misma canción (para el botón «Otra letra»).

    Mismo formato que `letras`, más "etiqueta" para decir de cuál se trata. Primero las que son de esta
    canción, luego las sincronizadas y las de duración más parecida; sin repetir textos iguales."""
    formas = elegir_letra.consultas(pista)
    if not formas:
        return []
    dur = int(pista.get("duracion") or 0)
    candidatos, vistas = [], set()
    for titulo, artista, _valen in formas[:2]:
        for params in ({"track_name": titulo, "artist_name": artista}, {"q": f"{artista} {titulo}".strip()}):
            r = _lrclib("search", params)
            for c in r if isinstance(r, list) else []:
                if isinstance(c, dict) and c.get("id") not in vistas:
                    vistas.add(c.get("id"))
                    candidatos.append(c)
    candidatos.sort(key=lambda c: (not elegir_letra.es_la_cancion(c, pista, formas), not c.get("syncedLyrics"),
                                   abs((c.get("duration") or 0) - dur) if dur else 0))
    salida, vistos = [], set()
    for c in candidatos:
        texto = (c.get("syncedLyrics") or c.get("plainLyrics") or "").strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        seg = int(c.get("duration") or 0)
        etiqueta = f"{c.get('artistName') or ''} — {c.get('trackName') or ''}".strip(" —")
        if seg:
            etiqueta += f" ({seg // 60}:{seg % 60:02d})"
        if c.get("syncedLyrics"):
            salida.append({"sincronizada": True, "lineas": _lrc_a_lineas(c["syncedLyrics"]),
                           "texto": c.get("plainLyrics") or "", "fuente": "LRCLIB",
                           "etiqueta": etiqueta, "duracion": float(seg or 0)})
        else:
            salida.append({"sincronizada": False, "lineas": [], "texto": c["plainLyrics"],
                           "fuente": "LRCLIB", "etiqueta": etiqueta + " · sin sincronizar"})
        if len(salida) >= limite:
            break
    return salida


# ---------------------------------------------------------------- SponsorBlock

def segmentos_a_saltar(video_id, categorias):
    """Tramos que no son musica / patrocinios, de la base publica de SponsorBlock."""
    if not video_id or not categorias:
        return []
    try:
        import json as _json
        r = requests.get("https://sponsor.ajay.app/api/skipSegments",
                         params={"videoID": video_id, "categories": _json.dumps(categorias)},
                         timeout=6)
        if r.status_code != 200:
            return []
        return [(s["segment"][0], s["segment"][1], s.get("category", ""))
                for s in r.json() if s.get("actionType", "skip") == "skip"]
    except (requests.RequestException, ValueError, KeyError):
        return []


# ---------------------------------------------------------------- streams

_cache_streams = {}
_cerrojo = threading.Lock()


def _opciones_ytdlp(ajustes=None):
    o = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True,
         "socket_timeout": 20}
    if shutil.which("node"):
        o["js_runtimes"] = {"node": {}}
    if ajustes is not None:
        from .config import navegador_cookies_usable
        nav = navegador_cookies_usable(ajustes["navegador_cookies"])
        if nav:
            o["cookiesfrombrowser"] = (nav,)
        archivo = ajustes["archivo_cookies"]
        if archivo:
            import os
            if os.path.exists(archivo):
                o["cookiefile"] = archivo
        if ajustes["proxy"]:
            o["proxy"] = ajustes["proxy"]
    return o


def selector_audio(calidad):
    # la pista «DRC» de YouTube (volumen estable, ya comprimida) suena peor: solo si no hay otra
    sin_drc = "[format_id!*=drc]"
    if calidad == "ahorro":
        return f"bestaudio[abr<=70]{sin_drc}/bestaudio[abr<=70]/worstaudio/bestaudio/best"
    if calidad == "normal":
        return f"bestaudio[abr<=135]{sin_drc}/bestaudio[abr<=135]/bestaudio/best"
    return f"bestaudio{sin_drc}/bestaudio/best"


def selector_video(alto, codec="auto"):
    limite = f"[height<={int(alto)}]" if alto and str(alto).isdigit() else ""
    if codec == "compatible":
        return (f"bv*{limite}[vcodec^=avc1]+ba/bv*{limite}+ba/b{limite}/bv*+ba/b")
    if codec == "sin_av1":
        return (f"bv*{limite}[vcodec!^=av01]+ba/bv*{limite}+ba/b{limite}/bv*+ba/b")
    return f"bv*{limite}+ba/b{limite}/bv*+ba/b"


def olvidar(objetivo):
    """Descarta los enlaces guardados de un video (para pedir otros nuevos)."""
    url = objetivo if "://" in str(objetivo) else f"https://www.youtube.com/watch?v={objetivo}"
    with _cerrojo:
        for clave in [k for k in _cache_streams if k[0] == url]:
            _cache_streams.pop(clave, None)


def resolver(objetivo, modo="audio", calidad="maxima", codec="auto", ajustes=None):
    """Convierte un video_id (o enlace) en direcciones que mpv puede reproducir.

    modo "audio": solo el sonido.  modo "video": imagen + sonido (en dos pistas
    cuando YouTube las sirve separadas, que es lo normal en alta calidad).
    Devuelve {"url", "audio_url", "cabeceras", "info": {...}, "formatos": [...]}.
    """
    url = objetivo if "://" in str(objetivo) else f"https://www.youtube.com/watch?v={objetivo}"
    clave = (url, modo, str(calidad), codec)
    with _cerrojo:
        guardado = _cache_streams.get(clave)
        if guardado and time.time() - guardado[0] < 3.5 * 3600:
            return guardado[1]

    import yt_dlp
    o = _opciones_ytdlp(ajustes)
    o["format"] = selector_audio(calidad) if modo == "audio" else selector_video(calidad, codec)
    try:
        with yt_dlp.YoutubeDL(o) as y:
            info = y.extract_info(url, download=False)
    except Exception as e:
        texto = str(e)
        if "Sign in" in texto or "age" in texto.lower():
            raise ErrorCatalogo("YouTube pide iniciar sesión para este contenido. "
                                "Actívalo en Ajustes → Cuenta de YouTube.") from e
        if "unavailable" in texto.lower():
            raise ErrorCatalogo("Este contenido ya no está disponible.") from e
        raise ErrorCatalogo("No se pudo abrir: " + texto.replace("ERROR:", "").strip()[:200]) from e

    if info.get("_type") == "playlist":
        entradas = [e for e in info.get("entries") or [] if e]
        if not entradas:
            raise ErrorCatalogo("No hay nada que reproducir en ese enlace.")
        info = entradas[0]

    pedidos = info.get("requested_formats") or []
    if pedidos:
        video = next((f for f in pedidos if f.get("vcodec") not in (None, "none")), None)
        audio = next((f for f in pedidos if f.get("acodec") not in (None, "none")
                      and f.get("vcodec") in (None, "none")), None)
    else:
        video = info if info.get("vcodec") not in (None, "none") else None
        audio = info if video is None else None
    principal = video or audio or info
    cabeceras = dict(principal.get("http_headers") or info.get("http_headers") or {})

    alturas = sorted({f.get("height") for f in info.get("formats") or []
                      if f.get("height") and f.get("vcodec") not in (None, "none")},
                     reverse=True)
    subtitulos = {}
    if modo == "video":
        for origen, auto in ((info.get("subtitles") or {}, False),
                             (info.get("automatic_captions") or {}, True)):
            for idioma, pistas in origen.items():
                if auto and not (idioma.startswith("es") or idioma.startswith("en")):
                    continue
                vtt = next((p for p in pistas if p.get("ext") == "vtt"), None)
                if not vtt:
                    continue
                nombre = vtt.get("name") or idioma
                if auto:
                    nombre += " (automáticos)"
                if nombre not in subtitulos and len(subtitulos) < 30:
                    subtitulos[nombre] = vtt.get("url")
    datos = {
        "subtitulos": subtitulos,
        "url": (video or audio or info).get("url"),
        "audio_url": audio.get("url") if (video and audio) else "",
        "cabeceras": cabeceras,
        "alturas": alturas,
        "info": {
            "titulo": info.get("title") or "",
            "autor": re.sub(r"\s*-\s*Topic$", "", info.get("artist") or info.get("uploader")
                            or info.get("channel") or ""),
            "duracion": int(info.get("duration") or 0),
            "miniatura": info.get("thumbnail") or "",
            "video_id": info.get("id") if info.get("extractor_key", "").startswith("Youtube") else "",
            "alto": (video or {}).get("height") or 0,
            "fps": (video or {}).get("fps") or 0,
            "vcodec": (video or {}).get("vcodec") or "",
            "hdr": (video or {}).get("dynamic_range") not in (None, "SDR"),
            "acodec": (audio or info).get("acodec") or "",
            "abr": round((audio or info).get("abr") or 0),
            "asr": (audio or info).get("asr") or 0,
            "capitulos": [(c.get("start_time", 0), c.get("title", ""))
                          for c in info.get("chapters") or []],
            "web": info.get("webpage_url") or url,
        },
    }
    with _cerrojo:
        if len(_cache_streams) > 300:
            _cache_streams.clear()
        _cache_streams[clave] = (time.time(), datos)
    return datos


def formatos_disponibles(url, ajustes=None):
    """Todas las calidades de un enlace, para elegir con precision al descargar."""
    import yt_dlp
    o = _opciones_ytdlp(ajustes)
    with yt_dlp.YoutubeDL(o) as y:
        info = y.extract_info(url, download=False)
    if info.get("_type") == "playlist":
        entradas = [e for e in info.get("entries") or [] if e]
        if entradas:
            info = entradas[0]
    salida = []
    for f in info.get("formats") or []:
        if f.get("format_note") == "storyboard" or (f.get("ext") == "mhtml"):
            continue
        tiene_v = f.get("vcodec") not in (None, "none")
        tiene_a = f.get("acodec") not in (None, "none")
        if not tiene_v and not tiene_a:
            continue
        salida.append({
            "id": f.get("format_id"), "ext": f.get("ext"),
            "alto": f.get("height") or 0, "fps": f.get("fps") or 0,
            "vcodec": (f.get("vcodec") or "") if tiene_v else "",
            "acodec": (f.get("acodec") or "") if tiene_a else "",
            "abr": round(f.get("abr") or 0), "tbr": round(f.get("tbr") or 0),
            "tamano": f.get("filesize") or f.get("filesize_approx") or 0,
            "hdr": f.get("dynamic_range") not in (None, "SDR"),
            "nota": f.get("format_note") or "", "idioma": f.get("language") or "",
        })
    return {"titulo": info.get("title") or "", "duracion": int(info.get("duration") or 0),
            "miniatura": info.get("thumbnail") or "", "formatos": salida,
            "autor": info.get("uploader") or ""}
