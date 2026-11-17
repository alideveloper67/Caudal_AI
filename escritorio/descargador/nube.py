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
    if not isinstance(datos, dict):
        datos = {}
    texto = " ".join(str(datos.get(k, "")) for k in ("msg", "message", "error_description",
                                                     "error", "code", "details", "hint")).lower()
    for clave, frase in _FRASES_SOCIAL:
        if clave in texto:
            return ErrorNube(frase)
    # las listas compartidas (supabase/listas.sql) ya contestan con frases en español pensadas para
    # personas («Ese código no existe…», «Esta lista ya tiene 20 personas…»): se dicen tal cual
    mensaje = str(datos.get("message") or "")
    if (str(datos.get("code")) == "P0001" and mensaje[:1].isupper()
            and any(x in mensaje.lower() for x in ("lista", "código", "canciones", "sesión", "dueño", "acceso",
                                                   "persona", "permiso"))):
        return ErrorNube(mensaje)
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
    return _por_estado(r.status_code)


# lo que la base de datos de «Perfiles, amigos y música» contesta, dicho para personas
_FRASES_SOCIAL = (
    ("primero deben ser amigos", "Primero deben ser amigos: envía una solicitud y, cuando la acepten, podrán escribirse."),
    ("espera unos dias", "Esa persona rechazó tu solicitud hace poco. Podrás volver a enviarla pasados 30 días."),
    ("demasiadas solicitudes", "Tienes demasiadas solicitudes pendientes (el máximo es 30). Espera a que respondan o cancela alguna."),
    ("no se puede enviar", "No se puede enviar la solicitud a esa persona."),
    ("esa persona no existe", "Esa persona ya no existe en Caudal."),
    ("solicitud no encontrada", "Esa solicitud ya no existe: puede que la hayan cancelado. Actualiza la lista."),
    ("solicitud no valida", "No se puede enviar una solicitud a esa persona."),
    ("ese perfil no es publico", "Ese perfil es privado: solo sus amigos pueden darle me gusta."),
    ("no se puede", "No se puede hacer eso con esa persona."),
    ("la cancion necesita una portada", "Cada canción necesita su carátula. Elige una imagen y vuelve a intentarlo."),
    ("ya subiste 30", "Ya subiste 30 canciones, que es el máximo. Borra alguna para subir otra."),
    ("hoy ya subiste 10", "Hoy ya subiste 10 canciones, que es el máximo por día. Sigue mañana."),
    ("ruta no valida", "No se pudo guardar el archivo en tu carpeta. Vuelve a intentarlo."),
    ("row-level security", "Solo puedes escribir a tus amigos. Envía una solicitud primero."),
    ("perfil_limites", "Algo de lo que escribiste es demasiado largo o no es válido. Revisa la descripción, la frase y el artista favorito."),
    ("mime type", "Ese formato de archivo no se puede subir. Usa mp3, m4a, aac, flac, ogg, wav o webm; y jpg, png o webp para las imágenes."),
    ("exceeded the maximum allowed size", "El archivo pesa demasiado: el audio puede llegar a 15 MB y las imágenes a 2 MB."),
    ("payload too large", "El archivo pesa demasiado: el audio puede llegar a 15 MB y las imágenes a 2 MB."),
    ("resource already exists", "Ya existe un archivo con ese nombre. Vuelve a intentarlo."),
    ("could not find the function", "Esta función todavía no está activa en el servidor de Caudal."),
    ("pgrst202", "Esta función todavía no está activa en el servidor de Caudal."),
    ("42703", "Esta función todavía no está activa en el servidor de Caudal."),
    ("pgrst204", "Esta función todavía no está activa en el servidor de Caudal."),
)


def _por_estado(estado):
    if estado == 413:
        return ErrorNube("El archivo pesa demasiado: el audio puede llegar a 15 MB y las imágenes a 2 MB.")
    if estado in (401, 403):
        return ErrorNube("No tienes permiso para hacer eso. Cierra sesión, vuelve a entrar y prueba otra vez.")
    if estado >= 500:
        return ErrorNube("El servidor de Caudal tuvo un problema. Vuelve a intentarlo en un momento.")
    return ErrorNube(f"El servidor de cuentas respondió un error ({estado}).")


_POR_HILO = threading.local()
_REQUEST_DE_SIEMPRE = requests.request


def _sesion_del_hilo():
    """Una requests.Session por hilo: reutiliza la conexión TLS con el servidor (antes cada
    petición abría una nueva: DNS + TLS cada vez). Session no es segura entre hilos, de ahí una
    por hilo."""
    s = getattr(_POR_HILO, "sesion", None)
    if s is None:
        s = requests.Session()
        _POR_HILO.sesion = s
    return s


def _peticion(metodo, ruta, token=None, **kw):
    cab = {"apikey": CLAVE_PUBLICA, "Content-Type": "application/json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    cab.update(kw.pop("cabeceras", {}))
    tiempo = kw.pop("tiempo", TIEMPO)
    try:
        if requests.request is not _REQUEST_DE_SIEMPRE:     # una prueba lo sustituyó: se respeta
            return requests.request(metodo, URL + ruta, headers=cab, timeout=tiempo, **kw)
        return _sesion_del_hilo().request(metodo, URL + ruta, headers=cab, timeout=tiempo, **kw)
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


class _CuerpoConAvance:
    """Bytes que se envían de a pedazos avisando cuánto va (para la barra de progreso).
    Tiene `__len__`, así requests manda el tamaño exacto y no usa envío por tramos."""

    def __init__(self, datos, avance=None, bloque=64 * 1024):
        self._datos = bytes(datos)
        self._pos = 0
        self._avance = avance
        self._bloque = bloque

    def __len__(self):
        return len(self._datos)

    def read(self, n=-1):
        if self._pos >= len(self._datos):
            return b""
        n = self._bloque if n is None or n < 0 else min(n, self._bloque)
        trozo = self._datos[self._pos:self._pos + n]
        self._pos += len(trozo)
        if self._avance:
            try:
                self._avance(self._pos, len(self._datos))
            except Exception:  # noqa: BLE001 - la barra no debe romper la subida
                pass
        return trozo


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

    def rpc(self, nombre, **parametros):
        """Llama a una función de la base de datos (los parámetros empiezan con p_)."""
        return self.pedir("POST", "rpc/" + nombre, json=parametros)

    # --- almacén de archivos (fotos y música)
    def subir_archivo(self, bucket, ruta, datos, tipo, reemplazar=False, avance=None, tiempo=120):
        """Sube bytes a /storage/v1/object/<bucket>/<ruta>. `avance(enviado, total)` se llama
        mientras se envía (desde el hilo que sube, no desde la ventana)."""
        cuerpo = _CuerpoConAvance(datos, avance)
        r = _peticion("POST", f"/storage/v1/object/{bucket}/{ruta}", token=self.token(),
                      data=cuerpo, tiempo=tiempo,
                      cabeceras={"Content-Type": tipo, "x-upsert": "true" if reemplazar else "false",
                                 "cache-control": "max-age=3600"})
        if r.status_code >= 300:
            raise _traducir(r)

    def borrar_archivos(self, bucket, rutas):
        """Borra archivos de su carpeta (los que no existan se ignoran)."""
        rutas = [x for x in rutas if x]
        if not rutas:
            return
        r = _peticion("DELETE", f"/storage/v1/object/{bucket}", token=self.token(),
                      json={"prefixes": rutas})
        if r.status_code >= 300:
            raise _traducir(r)

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
