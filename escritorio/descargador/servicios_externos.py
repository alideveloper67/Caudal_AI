# -*- coding: utf-8 -*-
"""Conexiones oficiales con Spotify (tu cuenta) y la configuracion publica de Caudal.

Un solo sitio de configuracion: las variables de entorno del sitio de Netlify.
La funcion /api/servicios entrega lo que es publico (el client_id de Spotify, que
en el flujo PKCE no es secreto) y dice si las funciones /api/spotify y
/api/soundcloud tienen sus credenciales. Los secretos nunca salen del servidor.

Spotify, tu cuenta: flujo oficial «Authorization Code con PKCE» (sin secreto).
El navegador vuelve a un servidor diminuto en esta PC:
    http://127.0.0.1:43821/spotify
que tiene que estar en las «Redirect URIs» de la app de Spotify del dueno.
"""

import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode

import requests

from . import listas
from .config import carpeta_perfil

PUERTO_SPOTIFY = 43821
VUELTA_SPOTIFY = f"http://127.0.0.1:{PUERTO_SPOTIFY}/spotify"
PERMISOS_SPOTIFY = "user-library-read playlist-read-private playlist-read-collaborative"

_config = {"datos": None, "cuando": 0.0}


class ErrorServicio(Exception):
    """Algo que se le puede contar a la persona tal cual."""


def configuracion(forzar=False, pedir=None):
    """{'spotify_client_id', 'spotify', 'soundcloud'} del sitio de Caudal. Sin
    respuesta (sin internet o sin publicar la funcion) todo viene vacio."""
    if not forzar and _config["datos"] is not None and time.time() - _config["cuando"] < 600:
        return _config["datos"]
    datos = {"spotify_client_id": "", "spotify": False, "soundcloud": False}
    try:
        r = (pedir or requests.get)(f"{listas.SERVIDOR_WEB}/api/servicios", timeout=10,
                                    headers=listas.CABECERAS)
        d = r.json() if r.status_code == 200 else {}
        if isinstance(d, dict):
            datos["spotify_client_id"] = str(d.get("spotify_client_id") or "").strip()
            datos["spotify"] = bool(d.get("spotify"))
            datos["soundcloud"] = bool(d.get("soundcloud"))
    except (requests.RequestException, ValueError):
        pass
    _config.update(datos=datos, cuando=time.time())
    return datos


# ---------------------------------------------------------------- Spotify: tu cuenta

def _archivo_sesion():
    return carpeta_perfil() / "spotify_sesion.json"


def _leer_sesion():
    try:
        return json.loads(_archivo_sesion().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_sesion(datos):
    _archivo_sesion().write_text(json.dumps(datos), encoding="utf-8")


def spotify_conectado():
    return bool(_leer_sesion().get("refresh"))


def desconectar_spotify():
    try:
        _archivo_sesion().unlink()
    except OSError:
        pass


def nuevo_verificador():
    return secrets.token_urlsafe(64)[:96]


def huella(verificador):
    return base64.urlsafe_b64encode(
        hashlib.sha256(verificador.encode("ascii")).digest()).decode().rstrip("=")


def url_autorizar_spotify(client_id, verificador, estado, vuelta=VUELTA_SPOTIFY):
    return "https://accounts.spotify.com/authorize?" + urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": vuelta,
        "code_challenge_method": "S256", "code_challenge": huella(verificador),
        "scope": PERMISOS_SPOTIFY, "state": estado})


def _canjear(cuerpo, pedir=None):
    try:
        r = (pedir or requests.post)("https://accounts.spotify.com/api/token", data=cuerpo,
                                     timeout=20)
    except requests.RequestException as e:
        raise ErrorServicio("No se pudo conectar con Spotify. Revisa tu internet.") from e
    if r.status_code != 200:
        raise ErrorServicio("Spotify no aceptó la conexión. Vuelve a conectar tu cuenta.")
    d = r.json()
    return {"access": d.get("access_token", ""), "refresh": d.get("refresh_token", ""),
            "caduca": time.time() + int(d.get("expires_in", 3600)) - 60}


def conectar_spotify(cancelado=None, espera=300, abrir=None):
    """Abre el navegador para que la persona entre en Spotify y guarda su sesion."""
    import http.server
    import webbrowser
    from urllib.parse import parse_qs, urlparse

    client_id = configuracion(forzar=True)["spotify_client_id"]
    if not client_id:
        raise ErrorServicio("La conexión con Spotify aún no está activada en Caudal.")
    recibido = {}

    class _Vuelta(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - nombre que pide http.server
            u = urlparse(self.path)
            if u.path == "/spotify":
                recibido.update({k: v[0] for k, v in parse_qs(u.query).items()})
            cuerpo = ("<!doctype html><meta charset=utf-8><title>Caudal</title>"
                      "<body style='font-family:sans-serif;background:#061A2B;color:#F3F5F9;"
                      "display:grid;place-items:center;height:90vh'><h2>Listo. Ya puedes volver "
                      "a Caudal.</h2></body>").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *_a):
            pass

    try:
        servidor = http.server.HTTPServer(("127.0.0.1", PUERTO_SPOTIFY), _Vuelta)
    except OSError as e:
        raise ErrorServicio("Otra ventana de Caudal está esperando a Spotify. Ciérrala y "
                            "vuelve a probar.") from e
    servidor.timeout = 0.5
    verificador = nuevo_verificador()
    estado = secrets.token_urlsafe(16)
    try:
        if not (abrir or webbrowser.open)(url_autorizar_spotify(client_id, verificador, estado)):
            raise ErrorServicio("No se pudo abrir el navegador para entrar en Spotify.")
        limite = time.monotonic() + espera
        while not recibido:
            if cancelado is not None and cancelado():
                raise ErrorServicio("")
            if time.monotonic() > limite:
                raise ErrorServicio("Se acabó el tiempo para entrar en Spotify. Vuelve a intentarlo.")
            servidor.handle_request()
    finally:
        servidor.server_close()

    if recibido.get("state") != estado or not recibido.get("code"):
        if recibido.get("error") == "access_denied":
            raise ErrorServicio("Cancelaste la conexión con Spotify.")
        raise ErrorServicio("Spotify no dejó conectar tu cuenta. Vuelve a intentarlo.")
    sesion = _canjear({"grant_type": "authorization_code", "code": recibido["code"],
                       "redirect_uri": VUELTA_SPOTIFY, "client_id": client_id,
                       "code_verifier": verificador})
    sesion["client_id"] = client_id
    _guardar_sesion(sesion)
    return True


def token_spotify_usuario(pedir=None):
    """El token de tu cuenta de Spotify, renovado si hace falta ('' si no hay)."""
    s = _leer_sesion()
    if not s.get("refresh"):
        return ""
    if s.get("access") and time.time() < float(s.get("caduca") or 0):
        return s["access"]
    try:
        nueva = _canjear({"grant_type": "refresh_token", "refresh_token": s["refresh"],
                          "client_id": s.get("client_id", "")}, pedir)
    except ErrorServicio:
        return ""
    nueva["refresh"] = nueva["refresh"] or s["refresh"]   # Spotify a veces no lo cambia
    nueva["client_id"] = s.get("client_id", "")
    _guardar_sesion(nueva)
    return nueva["access"]


def me_gusta_spotify(al_avanzar=None):
    """Tus «Canciones que te gustan» de Spotify, todas (de 50 en 50)."""
    token = token_spotify_usuario()
    if not token:
        raise ErrorServicio("Conecta tu cuenta de Spotify para traer tus me gusta.")
    try:
        canciones = listas.spotify_paginado(f"{listas.API_SPOTIFY}/me/tracks?limit=50", token,
                                            al_avanzar=al_avanzar)
    except listas.ListaAjena as e:
        raise ErrorServicio("Spotify no dejó leer tus me gusta. Vuelve a conectar tu cuenta; "
                            "si sigue igual, pide al dueño de Caudal que te añada como "
                            "usuario de prueba.") from e
    return {"plataforma": "Spotify", "titulo": "Me gusta de Spotify", "autor": "",
            "canciones": canciones, "completa": True, "aviso": "", "total": len(canciones)}
