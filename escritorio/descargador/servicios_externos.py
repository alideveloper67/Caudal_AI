# -*- coding: utf-8 -*-
"""Cuentas vinculadas (Spotify, YouTube y SoundCloud) con sus conexiones oficiales.

Un solo sitio de configuracion: las variables de entorno del sitio de Netlify.
La funcion /api/servicios entrega lo que es publico (los client_id, que en el
flujo PKCE no son secretos) y dice si las funciones /api/spotify y
/api/soundcloud tienen sus credenciales. Los secretos nunca salen del servidor.

Vincular: OAuth «Authorization Code» con PKCE en los tres. El servicio vuelve a
    https://caudal-musica.netlify.app/api/vincular
y, como el `state` empieza por «e-» (escritorio), el sitio reenvia el navegador a
un servidor diminuto que esta esperando en esta PC:
    http://127.0.0.1:43821/vincular
Spotify canjea el codigo directamente (no necesita secreto); YouTube y SoundCloud
lo canjean por la funcion /api/vincular, que guarda el secreto.

Las sesiones (tokens) se guardan SOLO en la carpeta del perfil de esta PC: no van
ni a la copia de seguridad ni a la sincronizacion de Caudal.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import urlencode

import requests

from . import listas
from .config import carpeta_perfil

PUERTO = 43821
VUELTA = f"{listas.SERVIDOR_WEB}/api/vincular"
VUELTA_LOCAL = f"http://127.0.0.1:{PUERTO}/vincular"
PERMISOS_SPOTIFY = "user-library-read playlist-read-private playlist-read-collaborative"
PERMISO_YOUTUBE = "https://www.googleapis.com/auth/youtube.readonly"
API_YOUTUBE = "https://www.googleapis.com/youtube/v3"
CATEGORIA_MUSICA = "10"

NOMBRES = {"spotify": "Spotify", "youtube": "YouTube", "soundcloud": "SoundCloud"}

_config = {"datos": None, "cuando": 0.0}
_cerrojos = {s: threading.Lock() for s in NOMBRES}


class ErrorServicio(Exception):
    """Algo que se le puede contar a la persona tal cual."""


VACIA = {"spotify_client_id": "", "spotify": False, "soundcloud": False,
         "soundcloud_client_id": "", "youtube_client_id": ""}


def configuracion(forzar=False, pedir=None):
    """Lo que el sitio de Caudal tiene activado. Sin respuesta (sin internet o sin
    publicar la funcion) todo viene vacio."""
    if not forzar and _config["datos"] is not None and time.time() - _config["cuando"] < 600:
        return _config["datos"]
    datos = dict(VACIA)
    try:
        r = (pedir or requests.get)(f"{listas.SERVIDOR_WEB}/api/servicios", timeout=10,
                                    headers=listas.CABECERAS)
        d = r.json() if r.status_code == 200 else {}
        if isinstance(d, dict):
            for k in ("spotify_client_id", "soundcloud_client_id", "youtube_client_id"):
                datos[k] = str(d.get(k) or "").strip()
            datos["spotify"] = bool(d.get("spotify"))
            datos["soundcloud"] = bool(d.get("soundcloud"))
    except (requests.RequestException, ValueError):
        pass
    _config.update(datos=datos, cuando=time.time())
    return datos


def configuracion_en_memoria():
    """Lo ultimo que se supo, sin tocar la red (para pintar al instante)."""
    return _config["datos"]


def client_id(conf, servicio):
    return str((conf or {}).get(f"{servicio}_client_id") or "")


# ---------------------------------------------------------------- sesiones en el disco

def _archivo_sesion(servicio="spotify"):
    return carpeta_perfil() / f"{servicio}_sesion.json"


def _leer_sesion(servicio="spotify"):
    try:
        d = json.loads(_archivo_sesion(servicio).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar_sesion(servicio, datos):
    # se escribe aparte y se cambia de golpe: un corte a medias no deja la sesion rota
    destino = _archivo_sesion(servicio)
    borrador = destino.with_suffix(".tmp")
    borrador.write_text(json.dumps(datos), encoding="utf-8")
    os.replace(borrador, destino)


def vinculada(servicio):
    return bool(_leer_sesion(servicio).get("refresh"))


def desvincular(servicio, publicar=None):
    """Borra la sesion de esta PC y, en Google, retira ademas el permiso."""
    s = _leer_sesion(servicio)
    try:
        _archivo_sesion(servicio).unlink()
    except OSError:
        pass
    ficha = s.get("refresh") or s.get("access")
    if servicio == "youtube" and ficha:
        try:
            (publicar or requests.post)("https://oauth2.googleapis.com/revoke",
                                        data={"token": ficha}, timeout=15)
        except requests.RequestException:
            pass


# ---------------------------------------------------------------- PKCE

def nuevo_verificador():
    return secrets.token_urlsafe(64)[:96]


def huella(verificador):
    return base64.urlsafe_b64encode(
        hashlib.sha256(verificador.encode("ascii")).digest()).decode().rstrip("=")


def nuevo_estado(servicio):
    """«e-<servicio>-<azar>»: la «e» le dice al sitio que quien espera es una PC."""
    return f"e-{servicio}-{secrets.token_hex(16)}"


def url_autorizar(servicio, ident, verificador, estado):
    q = {"client_id": ident, "response_type": "code", "redirect_uri": VUELTA,
         "code_challenge_method": "S256", "code_challenge": huella(verificador), "state": estado}
    if servicio == "spotify":
        return "https://accounts.spotify.com/authorize?" + urlencode({**q, "scope": PERMISOS_SPOTIFY})
    if servicio == "youtube":
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
            {**q, "scope": PERMISO_YOUTUBE, "access_type": "offline", "prompt": "consent"})
    if servicio == "soundcloud":
        return "https://secure.soundcloud.com/authorize?" + urlencode(q)
    raise ErrorServicio("Ese servicio no se puede vincular.")


def _sesion_de(acceso, refresco, dura):
    return {"access": str(acceso or ""), "refresh": str(refresco or ""),
            "caduca": time.time() + max(60, int(float(dura or 3600))) - 60}


def _canjear_spotify(cuerpo, publicar=None):
    try:
        r = (publicar or requests.post)("https://accounts.spotify.com/api/token", data=cuerpo,
                                        timeout=20)
    except requests.RequestException as e:
        raise ErrorServicio("No se pudo conectar con Spotify. Revisa tu internet.") from e
    if r.status_code != 200:
        raise ErrorServicio("Spotify no aceptó la conexión. Vuelve a vincular tu cuenta.")
    d = r.json()
    return _sesion_de(d.get("access_token"), d.get("refresh_token"), d.get("expires_in"))


def _canjear_servidor(servicio, cuerpo, publicar=None):
    nombre = NOMBRES[servicio]
    try:
        r = (publicar or requests.post)(VUELTA, json={"servicio": servicio, **cuerpo}, timeout=30,
                                        headers=listas.CABECERAS)
        d = r.json()
    except requests.RequestException as e:
        raise ErrorServicio(f"No se pudo conectar con {nombre}. Revisa tu internet.") from e
    except ValueError as e:
        raise ErrorServicio(f"{nombre} no contestó bien. Prueba otra vez en un rato.") from e
    if not isinstance(d, dict) or d.get("error") or not d.get("access"):
        mensaje = d.get("mensaje") if isinstance(d, dict) else ""
        raise ErrorServicio(mensaje or f"{nombre} no aceptó la conexión. Vuelve a vincular tu cuenta.")
    return _sesion_de(d.get("access"), d.get("refresh"), d.get("caduca_en"))


def _pagina_vuelta(texto):
    return (f"<!doctype html><html lang=es><meta charset=utf-8><title>Caudal</title>"
            "<body style='font-family:sans-serif;background:#06070A;color:#F3F5F9;"
            f"display:grid;place-items:center;height:90vh'><h2>{texto}</h2></body></html>").encode("utf-8")


def vincular(servicio, cancelado=None, espera=300, abrir=None, publicar=None, puerto=PUERTO):
    """Abre el navegador para que la persona acepte y guarda su sesion en esta PC."""
    import http.server
    import webbrowser
    from urllib.parse import parse_qs, urlparse

    nombre = NOMBRES[servicio]
    ident = client_id(configuracion(forzar=True), servicio)
    if not ident:
        raise ErrorServicio(f"Vincular {nombre} todavía no está disponible. "
                            "Mientras tanto, trae tus me gusta desde un archivo.")
    estado = nuevo_estado(servicio)
    verificador = nuevo_verificador()
    recibido = {}

    class _Vuelta(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - nombre que pide http.server
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            # solo vale la vuelta que pedimos nosotros: cualquier otra se ignora y se sigue esperando
            mia = u.path == "/vincular" and secrets.compare_digest(
                q.get("state", "").encode(), estado.encode())
            if mia and not recibido and (q.get("code") or q.get("error")):
                recibido.update(q)
            texto = ("Listo. Ya puedes volver a Caudal." if mia and q.get("code")
                     else "No se vinculó. Vuelve a Caudal e inténtalo otra vez.")
            cuerpo = _pagina_vuelta(texto)
            self.send_response(200 if mia else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *_a):
            pass

    try:
        servidor = http.server.HTTPServer(("127.0.0.1", puerto), _Vuelta)
    except OSError as e:
        raise ErrorServicio("Otra ventana de Caudal está esperando para vincular una cuenta. "
                            "Ciérrala y vuelve a probar.") from e
    servidor.timeout = 0.5
    try:
        if not (abrir or webbrowser.open)(url_autorizar(servicio, ident, verificador, estado)):
            raise ErrorServicio(f"No se pudo abrir el navegador para entrar en {nombre}.")
        limite = time.monotonic() + espera
        while not recibido:
            if cancelado is not None and cancelado():
                raise ErrorServicio("")
            if time.monotonic() > limite:
                raise ErrorServicio(f"Se acabó el tiempo para entrar en {nombre}. Vuelve a intentarlo.")
            servidor.handle_request()
    finally:
        servidor.server_close()

    if not recibido.get("code"):
        if recibido.get("error") == "access_denied":
            raise ErrorServicio(f"Cancelaste la conexión con {nombre}.")
        raise ErrorServicio(f"{nombre} no dejó vincular tu cuenta. Vuelve a intentarlo.")
    if servicio == "spotify":
        sesion = _canjear_spotify({"grant_type": "authorization_code", "code": recibido["code"],
                                   "redirect_uri": VUELTA, "client_id": ident,
                                   "code_verifier": verificador}, publicar)
    else:
        sesion = _canjear_servidor(servicio, {"code": recibido["code"], "verificador": verificador},
                                   publicar)
    if not sesion["refresh"]:
        raise ErrorServicio(f"{nombre} no dio permiso para mantener la cuenta vinculada. Vuelve a intentarlo.")
    sesion["client_id"] = ident
    _guardar_sesion(servicio, sesion)
    return True


def token(servicio, publicar=None):
    """El token de la cuenta vinculada, renovado si hace falta ('' si no hay o ya no vale)."""
    with _cerrojos[servicio]:        # el de SoundCloud solo se puede renovar una vez: de uno en uno
        s = _leer_sesion(servicio)
        if not s.get("refresh"):
            return ""
        if s.get("access") and time.time() < float(s.get("caduca") or 0):
            return s["access"]
        try:
            if servicio == "spotify":
                nueva = _canjear_spotify({"grant_type": "refresh_token", "refresh_token": s["refresh"],
                                          "client_id": s.get("client_id", "")}, publicar)
            else:
                nueva = _canjear_servidor(servicio, {"refresh": s["refresh"]}, publicar)
        except ErrorServicio:
            return ""
        nueva["refresh"] = nueva["refresh"] or s["refresh"]   # no siempre lo cambian
        nueva["client_id"] = s.get("client_id", "")
        _guardar_sesion(servicio, nueva)
        return nueva["access"]


# ---------------------------------------------------------------- leer los me gusta

def _exigir_token(servicio):
    t = token(servicio)
    if not t:
        raise ErrorServicio(f"Vincula otra vez tu cuenta de {NOMBRES[servicio]} para traer tus me gusta.")
    return t


def _parar_si(conocidas):
    if not conocidas:
        return None
    return lambda elementos: all(c.get("externa") in conocidas for c in elementos)


def _lista(servicio, canciones):
    nombre = "YouTube Music" if servicio == "youtube" else NOMBRES[servicio]
    return {"plataforma": nombre, "titulo": f"Me gusta de {nombre}", "autor": "",
            "canciones": canciones, "completa": True, "aviso": "", "total": len(canciones)}


def me_gusta_spotify(al_avanzar=None, conocidas=None):
    """Tus «Canciones que te gustan» de Spotify, todas (de 50 en 50)."""
    t = _exigir_token("spotify")
    try:
        canciones = listas.spotify_paginado(f"{listas.API_SPOTIFY}/me/tracks?limit=50", t,
                                            al_avanzar=al_avanzar, parar=_parar_si(conocidas))
    except listas.ListaAjena as e:
        raise ErrorServicio("Spotify no dejó leer tus me gusta. Vuelve a vincular tu cuenta; si sigue "
                            "igual, tráelos desde el archivo de tus datos de Spotify.") from e
    return _lista("spotify", canciones)


def _segundos_iso(texto):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", str(texto or ""))
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def cancion_youtube(v):
    """Un video que te gusta -> cancion, o None si no es de musica."""
    sn = v.get("snippet") or {}
    vid = str(v.get("id") or "")
    if str(sn.get("categoryId")) != CATEGORIA_MUSICA or not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return None
    titulo = listas._limpiar(sn.get("title"))
    canal = listas._limpiar(sn.get("channelTitle"))
    artista = re.sub(r"\s+-\s+(Topic|Tema)$", "", canal)
    if artista == canal:                       # no es un canal de disco: el titulo suele ser «Artista - Tema»
        m = re.match(r"^(.+?)\s+[-–—]\s+(.+)$", titulo)
        if m:
            artista, titulo = m.group(1).strip(), m.group(2).strip()
        else:
            artista = re.sub(r"\s*VEVO$", "", canal)
    minis = sn.get("thumbnails") or {}
    mini = next((minis[k].get("url") for k in ("maxres", "standard", "high", "medium", "default")
                 if isinstance(minis.get(k), dict) and minis[k].get("url")), "")
    return {"titulo": titulo, "artista": artista,
            "duracion": _segundos_iso((v.get("contentDetails") or {}).get("duration")),
            "url": f"https://www.youtube.com/watch?v={vid}", "miniatura": mini, "externa": f"yt:{vid}"}


def me_gusta_youtube(al_avanzar=None, conocidas=None, dormir=time.sleep):
    """Los videos de musica que te gustan (YouTube y YouTube Music comparten los me gusta)."""
    cab = {"Authorization": f"Bearer {_exigir_token('youtube')}"}
    base = {"part": "snippet,contentDetails", "myRating": "like", "maxResults": "50"}
    parar = _parar_si(conocidas)

    def pedir(cursor):
        r = listas._pedir("GET", f"{API_YOUTUBE}/videos", headers=cab, dormir=dormir,
                          params={**base, **({"pageToken": cursor} if cursor else {})})
        if r.status_code == 401:
            raise ErrorServicio("Vincula otra vez tu cuenta de YouTube para traer tus me gusta.")
        if r.status_code == 403:
            raise ErrorServicio("YouTube no dejó leer tus me gusta ahora (puede ser el límite de hoy). "
                                "Prueba más tarde.")
        if r.status_code != 200:
            raise ErrorServicio("YouTube no contestó bien. Prueba otra vez en un rato.")
        d = r.json()
        return ([c for c in (cancion_youtube(v) for v in d.get("items") or []) if c],
                d.get("nextPageToken"))

    return _lista("youtube", listas.paginar(pedir, al_avanzar=al_avanzar, parar=parar))


def me_gusta_soundcloud(al_avanzar=None, conocidas=None):
    """Las canciones que te gustan de SoundCloud (de 200 en 200)."""
    t = _exigir_token("soundcloud")
    try:
        canciones = listas.soundcloud_paginado(
            f"{listas.API_SOUNDCLOUD}/me/likes/tracks?limit=200&linked_partitioning=true", t,
            al_avanzar=al_avanzar, parar=_parar_si(conocidas))
    except listas.ErrorLista as e:
        if "privado" in str(e):
            raise ErrorServicio("Vincula otra vez tu cuenta de SoundCloud para traer tus me gusta.") from e
        raise
    return _lista("soundcloud", canciones)


def me_gusta(servicio, al_avanzar=None, conocidas=None):
    f = {"spotify": me_gusta_spotify, "youtube": me_gusta_youtube, "soundcloud": me_gusta_soundcloud}
    return f[servicio](al_avanzar=al_avanzar, conocidas=conocidas)


# ---------------------------------------------------------------- nombres de antes

def spotify_conectado():
    return vinculada("spotify")


def token_spotify_usuario(publicar=None):
    return token("spotify", publicar)
