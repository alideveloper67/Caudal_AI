# -*- coding: utf-8 -*-
"""Conexion con Supabase: cuentas y biblioteca compartidas entre dispositivos.

La clave que va aqui es la PUBLICA del proyecto (publishable/anon): esta hecha
para ir dentro de las apps. La seguridad la ponen las reglas de la base de
datos (cada usuario solo puede leer y escribir lo suyo).

Se entra con usuario y contrasena. Supabase pide un correo, asi que cada usuario
se traduce a "<usuario>@usuarios.caudal.app": nunca se envia ningun correo.
"""

import base64
import hashlib
import secrets
import threading
import time
from urllib.parse import urlencode

import requests

# Usar los certificados de Windows (los mismos que el navegador) en lugar de la
# lista fija de certifi. Sin esto, en PCs con antivirus que revisa HTTPS
# (Avast, AVG, Kaspersky, ESET...) o con proxy, el navegador funciona pero la
# app rechaza la conexion y parece que "no hay internet".
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # sin truststore se sigue con certifi
    pass

URL = "https://nztirmwqykbxadidpzzt.supabase.co"
CLAVE_PUBLICA = "sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl"
DOMINIO = "usuarios.caudal.app"
TIEMPO = 15


class ErrorNube(Exception):
    """Algo que se le puede contar tal cual al usuario."""


class SinConexion(ErrorNube):
    pass


def correo_de(usuario):
    return f"{usuario.strip().lower()}@{DOMINIO}"


def _traducir(r):
    try:
        datos = r.json()
    except ValueError:
        datos = {}
    texto = " ".join(str(datos.get(k, "")) for k in ("msg", "message", "error_description",
                                                     "error", "code")).lower()
    if "invalid login" in texto or "invalid_grant" in texto or "invalid_credentials" in texto:
        return ErrorNube("Usuario o contraseña incorrectos.")
    if "already registered" in texto or "already exists" in texto or "user_already_exists" in texto:
        return ErrorNube("Ese usuario ya existe. Inicia sesión o elige otro.")
    if "password" in texto and ("short" in texto or "least" in texto or "weak" in texto):
        return ErrorNube("La contraseña es demasiado corta (mínimo 6 caracteres).")
    if "rate limit" in texto or r.status_code == 429:
        return ErrorNube("Demasiados intentos seguidos. Espera un minuto y vuelve a probar.")
    if "refresh" in texto and ("not found" in texto or "invalid" in texto):
        return ErrorNube("La sesión guardada caducó. Vuelve a iniciar sesión.")
    return ErrorNube(f"El servidor de cuentas respondió un error ({r.status_code}).")


def _peticion(metodo, ruta, token=None, **kw):
    cab = {"apikey": CLAVE_PUBLICA, "Content-Type": "application/json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    cab.update(kw.pop("cabeceras", {}))
    try:
        return requests.request(metodo, URL + ruta, headers=cab, timeout=TIEMPO, **kw)
    except requests.RequestException as e:
        raise SinConexion(_motivo_sin_conexion(e)) from e


def _motivo_sin_conexion(e):
    """Explica por qué no se llegó al servidor, para que el usuario sepa qué tocar."""
    texto = str(e).lower()
    if isinstance(e, requests.exceptions.SSLError) or "certificate" in texto or "ssl" in texto:
        return ("No se pudo abrir una conexión segura con el servidor de cuentas. "
                "Revisa que la fecha y la hora de Windows estén bien; si usas un antivirus "
                "que revisa HTTPS (Avast, AVG, Kaspersky, ESET...), permite Caudal en él.")
    if isinstance(e, requests.exceptions.ProxyError):
        return ("Un proxy de esta PC está bloqueando la conexión con el servidor de cuentas. "
                "Revisa la configuración de proxy de Windows.")
    if isinstance(e, requests.exceptions.Timeout):
        return ("El servidor de cuentas tardó demasiado en responder. "
                "Vuelve a intentarlo en un momento.")
    if "getaddrinfo" in texto or "name resolution" in texto or "nameresolution" in texto:
        return ("Esta PC no encuentra el servidor de cuentas (fallo de DNS). "
                "Revisa tu internet o prueba con otra red.")
    if "10013" in texto or "forbidden by its access permissions" in texto:
        return ("El firewall o el antivirus de esta PC está bloqueando a Caudal. "
                "Permite Caudal en él y vuelve a intentarlo.")
    return "No hay conexión con el servidor de cuentas. Revisa tu internet."


# ---------------------------------------------------------------- cuentas


def google_activo():
    """¿Tiene Supabase activado el acceso con Google? Sin respuesta, no."""
    try:
        r = _peticion("GET", "/auth/v1/settings")
        return r.status_code == 200 and bool((r.json().get("external") or {}).get("google"))
    except Exception:
        return False


def usuario_libre(usuario):
    r = _peticion("POST", "/rest/v1/rpc/usuario_libre", json={"p_usuario": usuario})
    if r.status_code != 200:
        raise _traducir(r)
    return bool(r.json())


def registrar(usuario, contrasena, nombre, extra=None):
    """`extra`: aceptación de los términos y datos básicos (ver legal.extra_registro)."""
    r = _peticion("POST", "/auth/v1/signup", json={
        "email": correo_de(usuario), "password": contrasena,
        "data": {**(extra or {}), "usuario": usuario.strip().lower(), "nombre": nombre}})
    if r.status_code >= 300:
        raise _traducir(r)
    datos = r.json()
    if not datos.get("access_token"):
        raise ErrorNube("La cuenta se creó pero no se pudo entrar. Prueba a iniciar sesión.")
    return Sesion.desde_respuesta(datos)


def entrar(usuario, contrasena):
    r = _peticion("POST", "/auth/v1/token?grant_type=password",
                  json={"email": correo_de(usuario), "password": contrasena})
    if r.status_code >= 300:
        raise _traducir(r)
    return Sesion.desde_respuesta(r.json())


# ---------------------------------------------------------------- Google

def nuevo_verificador():
    """Codigo de un solo uso (PKCE): el navegador se lleva su huella y la app
    presenta el original al canjear, asi nadie mas puede usar el codigo."""
    return secrets.token_urlsafe(48)[:64]


def url_google(verificador, vuelta):
    huella = base64.urlsafe_b64encode(
        hashlib.sha256(verificador.encode("ascii")).digest()).decode().rstrip("=")
    return f"{URL}/auth/v1/authorize?" + urlencode({
        "provider": "google", "redirect_to": vuelta, "code_challenge": huella,
        "code_challenge_method": "s256", "prompt": "select_account"})


def canjear_google(codigo, verificador):
    r = _peticion("POST", "/auth/v1/token?grant_type=pkce",
                  json={"auth_code": codigo, "code_verifier": verificador})
    if r.status_code >= 300:
        if 400 <= r.status_code < 500:
            raise ErrorNube("No se pudo terminar de entrar con Google. Vuelve a intentarlo.")
        raise _traducir(r)
    return Sesion.desde_respuesta(r.json())


def renovar(refresh_token):
    r = _peticion("POST", "/auth/v1/token?grant_type=refresh_token",
                  json={"refresh_token": refresh_token})
    if r.status_code >= 300:
        raise _traducir(r)
    return Sesion.desde_respuesta(r.json())


class Sesion:
    """Tokens de una sesion abierta; se renueva sola antes de caducar."""

    def __init__(self, user_id, access, refresh, expira, metadatos=None):
        self.user_id = user_id
        self.access = access
        self.refresh = refresh
        self.expira = expira
        self.metadatos = metadatos or {}
        self._cerrojo = threading.Lock()

    @classmethod
    def desde_respuesta(cls, d):
        usuario = d.get("user") or {}
        return cls(usuario.get("id"), d["access_token"], d["refresh_token"],
                   time.time() + int(d.get("expires_in") or 3600),
                   usuario.get("user_metadata") or {})

    def token(self):
        with self._cerrojo:
            if time.time() > self.expira - 120:
                nueva = renovar(self.refresh)
                self.access, self.refresh, self.expira = nueva.access, nueva.refresh, nueva.expira
            return self.access

    # --- atajos para la API de datos (PostgREST)
    def pedir(self, metodo, ruta, **kw):
        r = _peticion(metodo, "/rest/v1/" + ruta, token=self.token(), **kw)
        if r.status_code >= 300:
            raise _traducir(r)
        return r.json() if r.text.strip() else None

    def perfil(self):
        filas = self.pedir("GET", f"perfiles?select=usuario,nombre&id=eq.{self.user_id}")
        return filas[0] if filas else {"usuario": self.metadatos.get("usuario", ""),
                                       "nombre": self.metadatos.get("nombre", "")}

    def cambiar_contrasena(self, nueva):
        r = _peticion("PUT", "/auth/v1/user", token=self.token(), json={"password": nueva})
        if r.status_code >= 300:
            raise _traducir(r)

    def salir(self):
        try:
            _peticion("POST", "/auth/v1/logout", token=self.access)
        except ErrorNube:
            pass
