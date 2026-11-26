# -*- coding: utf-8 -*-
"""Importar listas de reproduccion de Spotify, Apple Music, YouTube Music y SoundCloud.

Se leen los datos publicos de la lista (que canciones tiene) y despues cada
cancion se busca y se descarga desde YouTube.

Cuantas canciones se pueden leer de cada sitio (sin topes propios de Caudal:
se pagina hasta que el servicio dice que no hay mas):
  * YouTube / YouTube Music -> la lista entera.
  * Spotify -> con la API oficial: albumes completos, tus listas completas
    (si conectas tu cuenta de Spotify) y las listas ajenas solo si la app de
    Caudal tiene cuota ampliada en Spotify. Sin eso, las 50 de la pagina publica.
  * SoundCloud -> con la API oficial (app registrada): listas y me gusta
    completos. Sin credenciales, lo poco que ensena su pagina publica.
  * Apple Music -> alrededor de 100, que es lo que trae su propia pagina.

Las credenciales van en un solo sitio: las variables de entorno del sitio de
Netlify (funciones /api/spotify y /api/soundcloud). Quien quiera puede poner
las suyas en los ajustes de esta PC y se usan directamente.

Lo que NO hace, porque no se puede: convertir los archivos que Spotify, Apple
Music o YouTube Premium guardan en el telefono para escuchar sin conexion. Esos
archivos van cifrados con DRM y solo sirven dentro de su propia app.
"""

import base64
import html
import json
import re
import time
from urllib.parse import urlparse

import requests

AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
CABECERAS = {"User-Agent": AGENTE, "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}

# las funciones de Caudal en Netlify (guardan los secretos del servidor)
SERVIDOR_WEB = "https://caudal-musica.netlify.app"

# guarda de cordura: ningun servicio tiene listas asi de largas; solo evita
# girar para siempre si un servicio devolviera el mismo cursor una y otra vez
GUARDA_PAGINAS = 100000


class ErrorLista(Exception):
    """Problema contable al usuario."""


class SinCredenciales(Exception):
    """El servicio pide credenciales oficiales que aun no estan configuradas."""


def paginar(pedir_pagina, inicio=None, al_avanzar=None, parar=None):
    """Junta todas las paginas: `pedir_pagina(cursor) -> (elementos, siguiente)`.

    Sin tope de cantidad: sigue mientras el servicio de un `siguiente`. Se corta
    solo si un cursor se repite (el servicio se quedo dando vueltas) o si
    `parar(elementos)` dice que lo que sigue ya se conoce."""
    todos = []
    cursor = inicio
    vistos = set()
    for _ in range(GUARDA_PAGINAS):
        elementos, siguiente = pedir_pagina(cursor)
        todos.extend(elementos)
        if al_avanzar:
            al_avanzar(len(todos))
        if parar is not None and elementos and parar(elementos):
            break
        if siguiente is None or siguiente == "" or siguiente in vistos:
            break
        vistos.add(siguiente)
        cursor = siguiente
    return todos


def _pedir(metodo, url, reintentos=5, dormir=time.sleep, **kw):
    """Una peticion que respeta los «espera un poco» (429) y reintenta los fallos de red."""
    kw.setdefault("timeout", 30)
    ultimo = None
    for intento in range(reintentos):
        try:
            r = requests.request(metodo, url, **kw)
        except requests.RequestException as e:
            ultimo = e
            dormir(min(2 ** intento, 20))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            try:
                espera = float(r.headers.get("Retry-After") or 0)
            except ValueError:
                espera = 0
            dormir(min(max(espera, 2 ** intento), 30))
            ultimo = r
            continue
        return r
    if isinstance(ultimo, requests.Response):
        return ultimo
    raise ErrorLista("No se pudo conectar. Revisa tu internet y vuelve a probar.") from ultimo


def _limpiar(texto):
    return html.unescape(re.sub(r"\s+", " ", str(texto or ""))).strip()


def detectar_plataforma(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if "spotify" in host:
        return "spotify"
    if "music.apple" in host or "itunes.apple" in host:
        return "apple"
    if "youtube" in host or "youtu.be" in host:
        return "youtube"
    if host == "soundcloud.com" or host.endswith(".soundcloud.com"):
        return "soundcloud"
    return ""


def es_lista_soportada(url: str) -> bool:
    return detectar_plataforma(url) != ""


def _buscar_clave(objeto, clave, profundidad=0):
    """Busca una clave a cualquier nivel del JSON, sin perderse en el camino."""
    if profundidad > 14:
        return None
    if isinstance(objeto, dict):
        if clave in objeto:
            return objeto[clave]
        for valor in objeto.values():
            hallado = _buscar_clave(valor, clave, profundidad + 1)
            if hallado is not None:
                return hallado
    elif isinstance(objeto, list):
        for valor in objeto[:60]:
            hallado = _buscar_clave(valor, clave, profundidad + 1)
            if hallado is not None:
                return hallado
    return None


# ---------------------------------------------------------------- Spotify
#
# Desde 2026 Spotify solo deja leer las canciones de una lista a la persona que
# es su duena o colabora en ella (GET /playlists/{id}/items). Con credenciales
# de cliente (sin cuenta) se leen albumes completos; las listas ajenas solo si la
# app de Caudal tiene «cuota ampliada» en Spotify. Por eso el orden es:
#   1. tu cuenta de Spotify conectada (tus listas y las colaborativas, enteras)
#   2. las credenciales de cliente de esta PC (si alguien las puso en ajustes)
#   3. la funcion /api/spotify de Caudal (credenciales del dueno, en Netlify)
#   4. la pagina publica: las 50 primeras

API_SPOTIFY = "https://api.spotify.com/v1"

_token_spotify = {"valor": "", "caduca": 0, "de": ""}


class ListaAjena(Exception):
    """Spotify no deja leer las canciones de una lista que no es de quien pregunta."""


def _ajuste(ajustes, clave):
    try:
        return (ajustes[clave] or "").strip() if ajustes else ""
    except (KeyError, TypeError, AttributeError):
        return ""


def _token_api_spotify(ajustes):
    """Token de la API oficial con credenciales de cliente (ID y secreto de esta PC)."""
    ident = _ajuste(ajustes, "spotify_id")
    secreto = _ajuste(ajustes, "spotify_secreto")
    if not ident or not secreto:
        return ""

    if (_token_spotify["valor"] and _token_spotify["de"] == ident
            and time.time() < _token_spotify["caduca"]):
        return _token_spotify["valor"]

    credencial = base64.b64encode(f"{ident}:{secreto}".encode()).decode()
    try:
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {credencial}"},
            timeout=20,
        )
    except requests.RequestException:
        return ""
    if r.status_code != 200:
        return ""

    datos = r.json()
    _token_spotify["valor"] = datos.get("access_token", "")
    _token_spotify["de"] = ident
    _token_spotify["caduca"] = time.time() + int(datos.get("expires_in", 3600)) - 60
    return _token_spotify["valor"]


def _pistas_de_pagina(pagina):
    """Las pistas de una pagina de Spotify, venga de un album (la pista tal cual),
    de una lista (`item`, antes `track`) o de tus me gusta (`track`)."""
    salida = []
    for fila in (pagina or {}).get("items") or []:
        if not isinstance(fila, dict):
            continue
        if isinstance(fila.get("item"), dict):
            pista = fila["item"]
        elif isinstance(fila.get("track"), dict):
            pista = fila["track"]
        else:
            pista = fila
        if pista.get("type") not in (None, "track"):
            continue                    # episodios de podcast
        if pista.get("name"):
            salida.append(pista)
    return salida


def spotify_paginado(primera_url, token, dormir=time.sleep, al_avanzar=None, parar=None):
    """Todas las canciones desde `primera_url`, siguiendo `next` sin tope."""
    cab = {"Authorization": f"Bearer {token}"}

    def pedir(cursor):
        r = _pedir("GET", cursor or primera_url, headers=cab, dormir=dormir)
        if r.status_code in (401, 403):
            raise ListaAjena()
        if r.status_code == 404:
            raise ErrorLista("Esa lista no existe o es privada.")
        if r.status_code != 200:
            raise ErrorLista("Spotify no contestó bien. Prueba otra vez en un rato.")
        pagina = r.json()
        return [_cancion_spotify(p) for p in _pistas_de_pagina(pagina)], pagina.get("next")

    return paginar(pedir, al_avanzar=al_avanzar, parar=parar)


def _spotify_api(tipo, ident, token, dormir=time.sleep):
    """Lee el album o la lista entera con un token de la API oficial."""
    cab = {"Authorization": f"Bearer {token}"}

    if tipo == "track":
        r = _pedir("GET", f"{API_SPOTIFY}/tracks/{ident}", headers=cab, dormir=dormir)
        if r.status_code != 200:
            raise ErrorLista("Spotify no devolvio esa cancion.")
        t = r.json()
        return {
            "titulo": _limpiar(t.get("name")),
            "autor": ", ".join(a.get("name", "") for a in t.get("artists", [])),
            "portada": (t.get("album", {}).get("images") or [{}])[0].get("url", ""),
            "canciones": [_cancion_spotify(t)],
        }

    r = _pedir("GET", f"{API_SPOTIFY}/{tipo}s/{ident}", headers=cab, dormir=dormir)
    if r.status_code == 404:
        raise ErrorLista("Esa lista no existe o es privada.")
    if r.status_code in (401, 403):
        raise ListaAjena()
    if r.status_code != 200:
        raise ErrorLista("Spotify rechazo la peticion. Revisa las credenciales.")
    cabecera = r.json()

    if tipo == "album":
        canciones = spotify_paginado(f"{API_SPOTIFY}/albums/{ident}/tracks?limit=50", token, dormir)
        autor = ", ".join(a.get("name", "") for a in cabecera.get("artists") or [])
    else:
        try:
            canciones = spotify_paginado(f"{API_SPOTIFY}/playlists/{ident}/items?limit=50", token, dormir)
        except ListaAjena:
            # la ruta de siempre, que aun contesta a las apps con cuota ampliada
            canciones = spotify_paginado(f"{API_SPOTIFY}/playlists/{ident}/tracks?limit=100", token, dormir)
        autor = _limpiar((cabecera.get("owner") or {}).get("display_name", ""))

    imagenes = cabecera.get("images") or []
    return {
        "titulo": _limpiar(cabecera.get("name")),
        "autor": autor,
        "portada": imagenes[0].get("url", "") if imagenes else "",
        "canciones": canciones,
    }


def _cancion_spotify(pista):
    c = {
        "titulo": _limpiar(pista.get("name")),
        "artista": ", ".join(a.get("name", "") for a in pista.get("artists", [])),
        "duracion": int((pista.get("duration_ms") or 0) / 1000),
    }
    if pista.get("id"):
        c["externa"] = f"sp:{pista['id']}"     # para no volver a buscarla al sincronizar
    return c


def _funcion(ruta, params, dormir=time.sleep, timeout=40):
    """Llama a una funcion de Caudal en Netlify. Si aun no esta publicada o no
    tiene credenciales, lanza SinCredenciales."""
    try:
        r = _pedir("GET", f"{SERVIDOR_WEB}{ruta}", params=params, headers=CABECERAS,
                   timeout=timeout, dormir=dormir, reintentos=3)
    except ErrorLista as e:
        raise SinCredenciales() from e
    try:
        datos = r.json()
    except ValueError as e:
        raise SinCredenciales() from e     # la funcion no existe todavia (pagina 404)
    if not isinstance(datos, dict) or datos.get("error") == "sin_credenciales":
        raise SinCredenciales()
    return r.status_code, datos


def _spotify_por_funcion(tipo, ident, dormir=time.sleep):
    """La funcion /api/spotify pagina en el servidor y entrega de a trozos."""
    cabecera = {}

    def pedir(desde):
        _estado, d = _funcion("/api/spotify", {"tipo": tipo, "id": ident, "desde": desde or 0},
                              dormir=dormir)
        if d.get("error") == "lista_ajena":
            raise ListaAjena()
        if d.get("error"):
            raise ErrorLista(d.get("mensaje") or "Spotify no devolvio esa lista.")
        if not cabecera:
            cabecera.update({k: d.get(k, "") for k in ("titulo", "autor", "portada")})
        siguiente = d.get("siguiente")
        return list(d.get("canciones") or []), (siguiente if isinstance(siguiente, int) else None)

    canciones = paginar(pedir)
    return {**cabecera, "canciones": canciones}


def _spotify_pagina(tipo, ident):
    """Sin credenciales solo se puede leer lo que ensena la pagina publica."""
    try:
        r = requests.get(f"https://open.spotify.com/embed/{tipo}/{ident}",
                         headers=CABECERAS, timeout=25)
    except requests.RequestException as e:
        raise ErrorLista(f"No se pudo conectar con Spotify: {e}") from e
    if r.status_code != 200:
        raise ErrorLista("Spotify no devolvio esa lista. Comprueba que sea publica.")
    r.encoding = "utf-8"
    return leer_spotify_pagina(r.text)


def leer_spotify_pagina(pagina):
    """Separado para probarlo con una pagina guardada."""
    bloque = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', pagina, re.S)
    if not bloque:
        raise ErrorLista(
            "Spotify cambio su pagina y no se pudieron leer las canciones.")
    try:
        datos = json.loads(bloque.group(1))
    except json.JSONDecodeError as e:
        raise ErrorLista("La respuesta de Spotify no se entendio.") from e

    entidad = _buscar_clave(datos, "entity") or {}
    pistas = entidad.get("trackList") or _buscar_clave(datos, "trackList") or []
    if not pistas:
        raise ErrorLista("Esa lista de Spotify esta vacia o es privada.")

    canciones = []
    for p in pistas:
        titulo = _limpiar(p.get("title"))
        if titulo:
            canciones.append({
                "titulo": titulo,
                "artista": _limpiar(p.get("subtitle")),
                "duracion": int((p.get("duration") or 0) / 1000),
            })

    imagenes = (entidad.get("coverArt") or {}).get("sources") or []
    return {
        "titulo": _limpiar(entidad.get("name")) or "Lista de Spotify",
        "autor": _limpiar(entidad.get("subtitle")),
        "portada": imagenes[-1].get("url", "") if imagenes else "",
        "canciones": canciones,
    }


AVISO_SPOTIFY_SIN_CONEXION = (
    "Spotify solo deja ver 50 canciones sin su conexión oficial. Si la lista es tuya, "
    "conecta tu cuenta de Spotify en «Pasar tus me gusta» y vuelve a traerla.")
AVISO_SPOTIFY_AJENA = (
    "Spotify ya no deja a otras apps leer listas de otras personas: llegaron las 50 que "
    "muestra su página. Copia la lista a una tuya en Spotify, conecta tu cuenta y tráela otra vez.")


def _spotify(url: str, ajustes, dormir=time.sleep) -> dict:
    m = re.search(r"/(playlist|album|track)/([A-Za-z0-9]+)", url)
    if not m:
        raise ErrorLista("Ese enlace de Spotify no es de una lista, un album ni una cancion.")
    tipo, ident = m.group(1), m.group(2)

    def completa(datos):
        datos["plataforma"] = "Spotify"
        datos["completa"] = True
        return datos

    ajena = False
    # 1. tu cuenta de Spotify (tus listas y las colaborativas)
    try:
        from . import servicios_externos
        token_tuyo = servicios_externos.token_spotify_usuario()
    except Exception:  # noqa: BLE001 - sin cuenta conectada se sigue
        token_tuyo = ""
    for token in [t for t in (token_tuyo, _token_api_spotify(ajustes)) if t]:
        try:
            return completa(_spotify_api(tipo, ident, token, dormir))
        except ListaAjena:
            ajena = True
        except ErrorLista:
            raise
        except Exception:  # noqa: BLE001 - si la API falla, se prueba lo siguiente
            pass

    # 3. la funcion de Caudal (credenciales del dueno guardadas en Netlify)
    if not ajena:
        try:
            return completa(_spotify_por_funcion(tipo, ident, dormir))
        except ListaAjena:
            ajena = True
        except SinCredenciales:
            pass
        except ErrorLista:
            raise

    # 4. la pagina publica
    datos = _spotify_pagina(tipo, ident)
    datos["plataforma"] = "Spotify"
    datos["completa"] = len(datos["canciones"]) < 50
    if not datos["completa"]:
        datos["aviso"] = AVISO_SPOTIFY_AJENA if ajena else AVISO_SPOTIFY_SIN_CONEXION
    return datos


# ---------------------------------------------------------------- SoundCloud
#
# La API oficial pide una app registrada (ID y secreto) y un token de cliente en
# cada peticion. Sin eso, la pagina publica de una lista solo trae completas sus
# primeras canciones (el resto llega como numeros que solo la API traduce), y la
# de «me gusta» no trae ninguna. No se usa la clave interna de la web de
# SoundCloud: no es nuestra.

API_SOUNDCLOUD = "https://api.soundcloud.com"
_token_soundcloud = {"valor": "", "caduca": 0, "de": ""}


def tipo_soundcloud(url):
    """('lista'|'me_gusta'|'cancion'|'perfil'|'', ruta). El perfil solo sirve para sus me gusta."""
    try:
        u = urlparse((url or "").strip())
    except ValueError:
        return "", ""
    partes = [p for p in (u.path or "").split("/") if p]
    if not partes:
        return "", ""
    if (u.hostname or "").startswith("on."):
        return "corto", u.path
    reservadas = {"discover", "search", "stream", "you", "charts", "upload", "settings", "pages"}
    if partes[0] in reservadas:
        return "", ""
    if len(partes) >= 3 and partes[1] == "sets":
        return "lista", "/".join(partes[:3])
    if len(partes) >= 2 and partes[1] == "likes":
        return "me_gusta", partes[0]
    if len(partes) == 1:
        return "perfil", partes[0]
    if len(partes) == 2 and partes[1] not in ("sets", "tracks", "albums", "reposts", "followers",
                                               "following", "popular-tracks", "comments"):
        return "cancion", "/".join(partes[:2])
    return "", ""


def _token_api_soundcloud(ajustes):
    ident = _ajuste(ajustes, "soundcloud_id")
    secreto = _ajuste(ajustes, "soundcloud_secreto")
    if not ident or not secreto:
        return ""
    if (_token_soundcloud["valor"] and _token_soundcloud["de"] == ident
            and time.time() < _token_soundcloud["caduca"]):
        return _token_soundcloud["valor"]
    credencial = base64.b64encode(f"{ident}:{secreto}".encode()).decode()
    try:
        r = requests.post("https://secure.soundcloud.com/oauth/token",
                          data={"grant_type": "client_credentials"},
                          headers={"Authorization": f"Basic {credencial}",
                                   "Accept": "application/json; charset=utf-8"},
                          timeout=20)
    except requests.RequestException:
        return ""
    if r.status_code != 200:
        return ""
    d = r.json()
    _token_soundcloud.update(valor=d.get("access_token", ""), de=ident,
                             caduca=time.time() + int(d.get("expires_in", 3600)) - 60)
    return _token_soundcloud["valor"]


def cancion_soundcloud(t):
    """Una pista de la API de SoundCloud -> {titulo, artista, duracion}."""
    meta = t.get("publisher_metadata") or {}
    artista = _limpiar(meta.get("artist")) or _limpiar((t.get("user") or {}).get("username"))
    titulo = _limpiar(t.get("title"))
    # muchas subidas se llaman «Artista - Tema»: se separa para buscar mejor
    m = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", titulo)
    if m and not meta.get("artist"):
        artista, titulo = m.group(1).strip(), m.group(2).strip()
    c = {"titulo": titulo, "artista": artista,
         "duracion": int((t.get("duration") or t.get("full_duration") or 0) / 1000)}
    ident = str(t.get("urn") or t.get("id") or "").rsplit(":", 1)[-1]
    if ident:
        c["externa"] = f"sc:{ident}"
    enlace = str(t.get("permalink_url") or "").split("?")[0]
    if enlace:                          # su original, por si no está en YouTube Music
        c["sc_url"] = enlace
        c["miniatura"] = str(t.get("artwork_url") or "").replace("-large.", "-t500x500.")
    return c


def soundcloud_paginado(primera_url, token, dormir=time.sleep, al_avanzar=None, parar=None):
    """Sigue `next_href` hasta el final (linked_partitioning), sin tope."""
    cab = {"Authorization": f"OAuth {token}", "Accept": "application/json; charset=utf-8"}

    def pedir(cursor):
        r = _pedir("GET", cursor or primera_url, headers=cab, dormir=dormir)
        if r.status_code in (401, 403):
            raise ErrorLista("SoundCloud no dejó leer eso: puede ser privado.")
        if r.status_code == 404:
            raise ErrorLista("Eso no existe en SoundCloud o es privado.")
        if r.status_code != 200:
            raise ErrorLista("SoundCloud no contestó bien. Prueba otra vez en un rato.")
        d = r.json()
        filas = d.get("collection") if isinstance(d, dict) else d
        canciones = []
        for f in filas or []:
            t = f.get("track") if isinstance(f, dict) and isinstance(f.get("track"), dict) else f
            if isinstance(t, dict) and t.get("title") and t.get("kind", "track") == "track":
                canciones.append(cancion_soundcloud(t))
        siguiente = d.get("next_href") if isinstance(d, dict) else None
        if siguiente and not str(siguiente).startswith(API_SOUNDCLOUD + "/"):
            siguiente = None            # solo se siguen enlaces de la propia API
        return canciones, siguiente

    return paginar(pedir, al_avanzar=al_avanzar, parar=parar)


def _soundcloud_api(url, tipo, token, dormir=time.sleep):
    cab = {"Authorization": f"OAuth {token}", "Accept": "application/json; charset=utf-8"}
    r = _pedir("GET", f"{API_SOUNDCLOUD}/resolve", params={"url": url}, headers=cab, dormir=dormir)
    if r.status_code == 404:
        raise ErrorLista("Ese enlace no existe en SoundCloud o es privado.")
    if r.status_code != 200:
        raise ErrorLista("SoundCloud no reconoció ese enlace.")
    recurso = r.json()
    clase = recurso.get("kind")
    ident = recurso.get("urn") or recurso.get("id")
    imagen = recurso.get("artwork_url") or recurso.get("avatar_url") or ""
    if clase == "track":
        return {"titulo": _limpiar(recurso.get("title")),
                "autor": _limpiar((recurso.get("user") or {}).get("username")),
                "portada": imagen, "canciones": [cancion_soundcloud(recurso)]}
    if clase == "playlist":
        canciones = soundcloud_paginado(
            f"{API_SOUNDCLOUD}/playlists/{ident}/tracks?linked_partitioning=true&limit=200",
            token, dormir)
        return {"titulo": _limpiar(recurso.get("title")) or "Lista de SoundCloud",
                "autor": _limpiar((recurso.get("user") or {}).get("username")),
                "portada": imagen, "canciones": canciones}
    if clase == "user":
        canciones = soundcloud_paginado(
            f"{API_SOUNDCLOUD}/users/{ident}/likes/tracks?linked_partitioning=true&limit=200",
            token, dormir)
        nombre = _limpiar(recurso.get("username")) or "SoundCloud"
        return {"titulo": f"Me gusta de {nombre}", "autor": nombre, "portada": imagen,
                "canciones": canciones, "me_gusta": True}
    raise ErrorLista("Ese enlace de SoundCloud no es de una lista, una canción ni un perfil.")


def _soundcloud_por_funcion(url, dormir=time.sleep):
    cabecera = {}

    def pedir(cursor):
        params = {"url": url}
        if cursor:
            params["cursor"] = cursor
        _estado, d = _funcion("/api/soundcloud", params, dormir=dormir)
        if d.get("error"):
            raise ErrorLista(d.get("mensaje") or "SoundCloud no devolvio eso.")
        if not cabecera:
            cabecera.update({k: d.get(k, "") for k in ("titulo", "autor", "portada")})
            cabecera["me_gusta"] = bool(d.get("me_gusta"))
        return list(d.get("canciones") or []), d.get("siguiente") or None

    canciones = paginar(pedir)
    return {**cabecera, "canciones": canciones}


def _lista_hidratada(pagina):
    m = re.search(r"window\.__sc_hydration\s*=\s*(\[.*?\]);\s*</script>", pagina, re.S)
    if not m:
        raise ErrorLista("SoundCloud cambió su página y no se pudo leer.")
    try:
        hidratado = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        raise ErrorLista("La página de SoundCloud no se entendió.") from e
    lista = next((x.get("data") for x in hidratado
                  if isinstance(x, dict) and x.get("hydratable") == "playlist"), None)
    if not isinstance(lista, dict):
        raise SinCredenciales()
    return lista


def _datos_lista(lista, canciones):
    return {"titulo": _limpiar(lista.get("title")) or "Lista de SoundCloud",
            "autor": _limpiar((lista.get("user") or {}).get("username")),
            "portada": lista.get("artwork_url") or "", "canciones": canciones}


def leer_soundcloud_pagina(pagina):
    """Lo que trae la pagina publica de una lista: las primeras canciones completas
    y cuantas tiene en total. Devuelve (datos, total)."""
    lista = _lista_hidratada(pagina)
    canciones = [cancion_soundcloud(t) for t in lista.get("tracks") or []
                 if isinstance(t, dict) and t.get("title")]
    total = int(lista.get("track_count") or len(canciones))
    return _datos_lista(lista, canciones), total


def soundcloud_pagina_entera(pagina, completar=None):
    """Todas las canciones de la lista, en su orden: de las que la página solo da el número, se pregunta
    cuál es a oEmbed (la API pública de SoundCloud). Devuelve (datos, total)."""
    from . import soundcloud
    lista = _lista_hidratada(pagina)
    pistas = [t for t in lista.get("tracks") or [] if isinstance(t, dict)]
    faltan = [t["id"] for t in pistas if not t.get("title") and t.get("id")]
    fichas = dict(zip(faltan, (completar or soundcloud.completar)(faltan)))
    canciones = []
    for t in pistas:
        if t.get("title"):
            canciones.append(cancion_soundcloud(t))
            continue
        f = fichas.get(t.get("id"))
        if f:
            canciones.append(soundcloud.cancion_de_pista(soundcloud.pista(
                f["titulo"], f["autor"], f["enlace"], 0, f["miniatura"], t["id"])))
    total = max(int(lista.get("track_count") or 0), len(pistas))
    return _datos_lista(lista, canciones), total


AVISO_SOUNDCLOUD_SIN_CONEXION = (
    "Se leyeron {n} de sus {total} canciones: las demás son privadas o ya no están en SoundCloud.")
MENSAJE_SOUNDCLOUD_SIN_CONEXION = (
    "No se pudieron leer los me gusta de ese perfil de SoundCloud. Comprueba que sean públicos, o pasa esas "
    "canciones a una lista pública y trae la lista.")


def _soundcloud(url, ajustes, dormir=time.sleep):
    tipo, _ruta = tipo_soundcloud(url)
    if tipo == "corto":
        # on.soundcloud.com/xxxx: el propio enlace lleva a la pagina de verdad
        try:
            url = requests.head(url, allow_redirects=True, timeout=15, headers=CABECERAS).url
        except requests.RequestException as e:
            raise ErrorLista("No se pudo abrir ese enlace de SoundCloud.") from e
        tipo, _ruta = tipo_soundcloud(url)
    if not tipo:
        raise ErrorLista("Pega el enlace de una lista, una canción o un perfil de SoundCloud.")
    if tipo == "me_gusta":
        url = "https://soundcloud.com/" + _ruta
    url = url.split("?")[0]

    def hecho(datos, completa=True, aviso=""):
        datos["plataforma"] = "SoundCloud"
        datos["completa"] = completa
        datos["aviso"] = aviso
        return datos

    token = _token_api_soundcloud(ajustes)
    if token:
        return hecho(_soundcloud_api(url, tipo, token, dormir))
    try:
        return hecho(_soundcloud_por_funcion(url, dormir))
    except SinCredenciales:
        pass

    from . import soundcloud
    if tipo in ("me_gusta", "perfil"):
        try:
            canciones = [soundcloud.cancion_de_pista(p) for p in soundcloud.me_gusta_de(_ruta)]
        except soundcloud.ErrorSoundcloud as e:
            raise ErrorLista(MENSAJE_SOUNDCLOUD_SIN_CONEXION) from e
        if not canciones:
            raise ErrorLista(MENSAJE_SOUNDCLOUD_SIN_CONEXION)
        return hecho({"titulo": f"Me gusta de {_ruta}", "autor": _ruta, "portada": "", "canciones": canciones,
                      "me_gusta": True})
    if tipo == "cancion":
        ficha = soundcloud.ficha_oembed(url)
        if not ficha:
            raise ErrorLista("SoundCloud no mostró eso. Comprueba que sea público.")
        p = soundcloud.pista(ficha["titulo"], ficha["autor"], url, 0, ficha["miniatura"])
        return hecho({"titulo": p["titulo"], "autor": ficha["autor"], "portada": ficha["miniatura"],
                      "canciones": [soundcloud.cancion_de_pista(p)]})
    try:
        r = requests.get(url, headers=CABECERAS, timeout=25)
    except requests.RequestException as e:
        raise ErrorLista(f"No se pudo conectar con SoundCloud: {e}") from e
    if r.status_code != 200:
        raise ErrorLista("SoundCloud no mostró eso. Comprueba que sea público.")
    r.encoding = "utf-8"
    try:
        datos, total = soundcloud_pagina_entera(r.text)
    except SinCredenciales as e:
        raise ErrorLista("SoundCloud no mostró esa lista. Comprueba que sea pública.") from e
    n = len(datos["canciones"])
    if not n:
        raise ErrorLista("Esa lista de SoundCloud está vacía o es privada.")
    if n >= total:
        return hecho(datos)
    return hecho(datos, False, AVISO_SOUNDCLOUD_SIN_CONEXION.format(n=n, total=total))


# ---------------------------------------------------------------- Apple Music

def _apple(url: str) -> dict:
    try:
        r = requests.get(url, headers=CABECERAS, timeout=25)
    except requests.RequestException as e:
        raise ErrorLista(f"No se pudo conectar con Apple Music: {e}") from e
    if r.status_code != 200:
        raise ErrorLista("Apple Music no devolvio esa lista. Comprueba que sea publica.")
    r.encoding = "utf-8"

    titulo, autor = _apple_titulo(r.text)
    canciones = _apple_del_bloque(r.text, titulo)
    if not canciones:
        canciones, titulo_ld, autor_ld = _apple_del_jsonld(r.text)
        titulo = titulo_ld or titulo
        autor = autor_ld or autor

    if not canciones:
        raise ErrorLista("Esa pagina de Apple Music no tiene canciones que leer.")

    return {
        "plataforma": "Apple Music",
        "titulo": titulo or "Lista de Apple Music",
        "autor": autor,
        "portada": _portada_apple(r.text),
        "canciones": canciones,
        "completa": False,
        "aviso": "Apple Music solo publica una parte de las listas largas en su "
                 "pagina; puede que falten canciones del final.",
    }


def _apple_del_bloque(pagina, titulo_lista=""):
    """La propia pagina lleva mas canciones que los datos para buscadores."""
    bloque = re.search(
        r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>', pagina, re.S)
    if not bloque:
        return []
    try:
        datos = json.loads(bloque.group(1))
    except json.JSONDecodeError:
        return []

    encontradas = []
    vistas = set()

    def recorrer(o, prof=0):
        if prof > 18:
            return
        if isinstance(o, dict):
            if o.get("kind") == "song" or ("title" in o and "subtitleLinks" in o):
                titulo = _limpiar(o.get("title") or o.get("name"))
                enlaces = o.get("subtitleLinks") or []
                artista = ", ".join(
                    _limpiar(a.get("title")) for a in enlaces if isinstance(a, dict))
                # la cabecera de la lista aparece con la misma forma que una
                # cancion: se descarta comparandola con el titulo de la pagina
                es_cabecera = (titulo_lista
                               and titulo.lower() == titulo_lista.lower())
                if (titulo and artista and not es_cabecera
                        and (titulo, artista) not in vistas):
                    vistas.add((titulo, artista))
                    encontradas.append({
                        "titulo": titulo, "artista": artista, "duracion": 0})
            for v in o.values():
                recorrer(v, prof + 1)
        elif isinstance(o, list):
            for v in o:
                recorrer(v, prof + 1)

    recorrer(datos)
    return encontradas


def _apple_del_jsonld(pagina):
    bloques = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', pagina, re.S)
    for bruto in bloques:
        try:
            datos = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if datos.get("@type") not in ("MusicPlaylist", "MusicAlbum"):
            continue
        artista_album = _artista_de(datos.get("byArtist"))
        canciones = []
        for p in datos.get("track") or datos.get("tracks") or []:
            if isinstance(p, dict) and p.get("name"):
                canciones.append({
                    "titulo": _limpiar(p.get("name")),
                    "artista": _artista_de(p.get("byArtist")) or artista_album,
                    "duracion": _duracion_iso(p.get("duration")),
                })
        if canciones:
            return canciones, _limpiar(datos.get("name")), artista_album
    return [], "", ""


def _apple_titulo(pagina):
    m = re.search(r'<meta property="og:title" content="([^"]+)"', pagina)
    titulo = html.unescape(m.group(1)) if m else ""
    for coletilla in (" on Apple Music", " - Apple Music"):
        if titulo.endswith(coletilla):
            titulo = titulo[: -len(coletilla)]
    m2 = re.search(r'<meta property="og:description" content="([^"]{0,80})"', pagina)
    return titulo, html.unescape(m2.group(1)) if m2 else ""


def _artista_de(valor):
    if isinstance(valor, list):
        return ", ".join(_limpiar(a.get("name")) for a in valor if isinstance(a, dict))
    if isinstance(valor, dict):
        return _limpiar(valor.get("name"))
    return _limpiar(valor) if valor else ""


def _duracion_iso(texto):
    if not texto:
        return 0
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(texto))
    if not m:
        return 0
    horas, minutos, segundos = (int(x) if x else 0 for x in m.groups())
    return horas * 3600 + minutos * 60 + segundos


def _portada_apple(pagina):
    m = re.search(r'<meta property="og:image" content="([^"]+)"', pagina)
    return html.unescape(m.group(1)) if m else ""


# ---------------------------------------------------------------- YouTube

MENSAJE_ME_GUSTA_YOUTUBE = (
    "Tus «Me gusta» de YouTube Music son privados y Caudal no tiene permiso para leerlos. "
    "En YouTube Music abre «Música que te gusta», toca ⋮ › «Agregar a playlist», crea una "
    "lista pública o no listada y pega aquí su enlace.")

def _youtube(url: str, ajustes) -> dict:
    """YouTube y YouTube Music, sin tope de canciones."""
    import yt_dlp

    m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    if m and m.group(1) in ("LM", "LL", "WL"):
        raise ErrorLista(MENSAJE_ME_GUSTA_YOUTUBE)

    opciones = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "extract_flat": "in_playlist", "socket_timeout": 30, "no_color": True,
        "ignoreerrors": True,
    }
    try:
        nav = (ajustes["navegador_cookies"] if ajustes else "ninguno") or "ninguno"
    except (KeyError, TypeError):
        nav = "ninguno"
    from .config import navegador_cookies_usable
    nav = navegador_cookies_usable(nav)
    if nav:
        opciones["cookiesfrombrowser"] = (nav,)

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raise ErrorLista(f"No se pudo leer esa lista de YouTube: {str(e)[:90]}") from e

    info = info or {}
    if info.get("_type") != "playlist":
        return {
            "plataforma": "YouTube",
            "titulo": info.get("title", ""),
            "autor": info.get("uploader", ""),
            "portada": info.get("thumbnail", ""),
            "completa": True,
            "canciones": [{
                "titulo": info.get("title", ""),
                "artista": info.get("uploader", ""),
                "duracion": int(info.get("duration") or 0),
                "url": info.get("webpage_url") or url,
            }],
        }

    canciones = []
    for e in info.get("entries") or []:
        if not e:
            continue
        enlace = e.get("url") or e.get("webpage_url") or ""
        if e.get("ie_key") == "Youtube" and enlace and not enlace.startswith("http"):
            enlace = "https://www.youtube.com/watch?v=" + enlace
        if not enlace:
            continue
        mini = e.get("thumbnail") or ""
        if not mini and e.get("thumbnails"):
            mini = e["thumbnails"][-1].get("url", "")
        canciones.append({
            "titulo": e.get("title") or "",
            "artista": e.get("uploader") or e.get("channel") or "",
            "duracion": int(e.get("duration") or 0),
            "url": enlace,
            "miniatura": mini,
        })

    return {
        "plataforma": "YouTube",
        "titulo": info.get("title", "Lista"),
        "autor": info.get("uploader", "") or info.get("channel", ""),
        "portada": "",
        "completa": True,
        "canciones": canciones,
    }


# ---------------------------------------------------------------- publico

def leer(url: str, ajustes) -> dict:
    """Devuelve las canciones de una lista de Spotify, Apple Music, YouTube o SoundCloud."""
    url = (url or "").strip()
    plataforma = detectar_plataforma(url)

    if plataforma == "spotify":
        resultado = _spotify(url, ajustes)
    elif plataforma == "apple":
        resultado = _apple(url)
    elif plataforma == "youtube":
        resultado = _youtube(url, ajustes)
    elif plataforma == "soundcloud":
        resultado = _soundcloud(url, ajustes)
    else:
        raise ErrorLista(
            "Pega el enlace de una lista de Spotify, Apple Music, YouTube Music o SoundCloud.")

    for c in resultado["canciones"]:
        if not c.get("url"):
            c["busqueda"] = " ".join(x for x in [c.get("artista"), c.get("titulo")] if x)

    resultado["total"] = len(resultado["canciones"])
    resultado.setdefault("completa", True)
    resultado.setdefault("aviso", "")
    return resultado
