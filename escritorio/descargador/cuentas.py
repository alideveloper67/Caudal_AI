# -*- coding: utf-8 -*-
"""Cuentas de Caudal: las mismas en Windows, Android y iPhone (Supabase).

La biblioteca de cada cuenta vive en este equipo (rapida y sin internet) y se
sincroniza con la nube en segundo plano (sincronizacion.py).

En el equipo solo se guarda:
  - sesion.json   el token de renovacion si marcaste «Mantener la sesion»
                  (nunca la contrasena)
  - perfiles.json que carpeta local usa cada cuenta
"""

import json
import os
import re
import threading
import time

from . import config, nube
from .nube import ErrorNube, SinConexion  # noqa: F401


class ErrorCuenta(Exception):
    pass


def _leer(nombre, defecto):
    try:
        return json.loads((config.carpeta_datos() / nombre).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _escribir(nombre, datos):
    ruta = config.carpeta_datos() / nombre
    tmp = ruta.with_suffix(f".{os.getpid()}-{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    for intento in range(5):
        try:
            os.replace(tmp, ruta)
            return
        except PermissionError:              # el antivirus tiene el archivo abierto un instante
            time.sleep(0.05 * (intento + 1))
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")


def _carpeta_para(user_id):
    """La primera cuenta que entra en este equipo se queda con lo que ya habia."""
    mapa = _leer("perfiles.json", {})
    if user_id in mapa:
        return mapa[user_id]
    raiz_ocupada = "" in mapa.values()
    carpeta = "" if not raiz_ocupada else f"perfiles/{user_id}"
    mapa[user_id] = carpeta
    _escribir("perfiles.json", mapa)
    return carpeta


def _cuenta(sesion, usuario, nombre, sin_conexion=False, google=False):
    cuenta = {"id": sesion.user_id if sesion else None, "usuario": usuario,
              "nombre": nombre or usuario, "carpeta": _carpeta_para(sesion.user_id) if sesion else "",
              "sesion": sesion, "sin_conexion": sin_conexion, "google": google}
    if sesion is not None:
        sesion.al_renovar = lambda: Cuentas().actualizar_recordada(cuenta)
    return cuenta


_PAGINA_VUELTA = """<!doctype html><html lang="es"><meta charset="utf-8">
<title>Caudal</title>
<body style="font-family:Segoe UI,sans-serif;background:#06070A;color:#F3F5F9;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center"><h1 style="color:#22D3EE">Listo</h1>
<p>Ya puedes cerrar esta pestaña y volver a Caudal.</p></div>
<script>
// si Google devolvio el error tras "#", se lo pasamos a Caudal
if (location.hash.length > 1 && location.search.indexOf("code=") < 0) {
  location.replace("/acceso?" + location.hash.substring(1));
}
</script></body></html>"""


class Cuentas:
    def hay_cuentas(self):
        return bool(_leer("perfiles.json", {})) or bool(self.ultimo_usuario())

    def crear(self, usuario, contrasena, nombre="", extra=None):
        usuario = (usuario or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,30}", usuario):
            raise ErrorCuenta("El usuario debe tener de 3 a 30 letras o números "
                              "(también . _ -), sin espacios ni tildes.")
        if len(contrasena or "") < 6:
            raise ErrorCuenta("La contraseña necesita al menos 6 caracteres.")
        try:
            if not nube.usuario_libre(usuario):
                raise ErrorCuenta("Ese usuario ya existe. Inicia sesión o elige otro.")
            sesion = nube.registrar(usuario, contrasena, (nombre or "").strip() or usuario, extra)
        except ErrorNube as e:
            raise ErrorCuenta(str(e)) from e
        return _cuenta(sesion, usuario, (nombre or "").strip() or usuario)

    def entrar(self, usuario, contrasena):
        usuario = (usuario or "").strip().lower()
        if not usuario:
            raise ErrorCuenta("Escribe tu usuario.")
        try:
            sesion = nube.entrar(usuario, contrasena or "")
            perfil = sesion.perfil()
        except ErrorNube as e:
            raise ErrorCuenta(str(e)) from e
        return _cuenta(sesion, perfil.get("usuario") or usuario, perfil.get("nombre") or usuario)

    def con_google(self, cancelado=None, espera=300):
        """Entrar (o registrarse, es lo mismo) con la cuenta de Google.

        Abre el navegador; Google devuelve a un servidor diminuto en este
        equipo (127.0.0.1) que recoge el codigo y lo canjea por la sesion.
        """
        import http.server
        import webbrowser
        from urllib.parse import parse_qs, urlparse

        recibido = {}

        class _Vuelta(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - nombre que pide http.server
                u = urlparse(self.path)
                if u.path == "/acceso":
                    q = {k: v[0] for k, v in parse_qs(u.query).items()}
                    if q:
                        recibido.update(q)
                cuerpo = _PAGINA_VUELTA.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def log_message(self, *_a):
                pass

        servidor = http.server.HTTPServer(("127.0.0.1", 0), _Vuelta)
        servidor.timeout = 0.5
        vuelta = f"http://127.0.0.1:{servidor.server_address[1]}/acceso"
        verificador = nube.nuevo_verificador()
        try:
            if not webbrowser.open(nube.url_google(verificador, vuelta)):
                raise ErrorCuenta("No se pudo abrir el navegador para entrar con Google.")
            import time
            limite = time.monotonic() + espera
            while not recibido:
                if cancelado is not None and cancelado():
                    raise ErrorCuenta("")
                if time.monotonic() > limite:
                    raise ErrorCuenta("Se acabó el tiempo para elegir la cuenta de Google. "
                                      "Vuelve a intentarlo.")
                servidor.handle_request()
        finally:
            servidor.server_close()

        codigo = recibido.get("code", "")
        if not codigo:
            motivo = (recibido.get("error_description") or recibido.get("error") or "").lower()
            if "denied" in motivo or "cancel" in motivo:
                raise ErrorCuenta("Cancelaste la entrada con Google.")
            raise ErrorCuenta("Google no dejó entrar. Vuelve a intentarlo.")
        try:
            sesion = nube.canjear_google(codigo, verificador)
            perfil = sesion.perfil()
        except ErrorNube as e:
            raise ErrorCuenta(str(e)) from e
        usuario = perfil.get("usuario") or ""
        return _cuenta(sesion, usuario, perfil.get("nombre") or usuario, google=True)

    def cambiar_contrasena(self, cuenta, actual, nueva):
        if len(nueva or "") < 6:
            raise ErrorCuenta("La contraseña nueva necesita al menos 6 caracteres.")
        try:
            nube.entrar(cuenta["usuario"], actual)
        except ErrorNube as e:
            raise ErrorCuenta("La contraseña actual no es correcta.") from e
        try:
            cuenta["sesion"].cambiar_contrasena(nueva)
        except ErrorNube as e:
            raise ErrorCuenta(str(e)) from e

    # ------------------------------------------------------------ sesion guardada

    def recordar(self, cuenta):
        s = cuenta.get("sesion")
        if not s:
            return
        _escribir("sesion.json", {"id": cuenta["id"], "usuario": cuenta["usuario"],
                                  "nombre": cuenta["nombre"], "refresh": s.refresh,
                                  "google": bool(cuenta.get("google"))})

    def actualizar_recordada(self, cuenta):
        """El token de renovacion cambia al usarse: se guarda el nuevo."""
        if (config.carpeta_datos() / "sesion.json").exists():
            self.recordar(cuenta)

    def olvidar(self, cuenta=None):
        try:
            (config.carpeta_datos() / "sesion.json").unlink()
        except OSError:
            pass
        if cuenta and cuenta.get("sesion"):
            cuenta["sesion"].salir()

    def recordada(self):
        """La sesion guardada, renovada. Sin internet se entra igual con la
        biblioteca local (y se sincroniza cuando vuelva la conexion)."""
        guardada = _leer("sesion.json", None)
        if not guardada or not guardada.get("refresh"):
            return None
        try:
            sesion = nube.renovar(guardada["refresh"])
        except nube.SesionCaducada:
            # ¿la renovó otro Caudal mientras tanto? Se prueba con lo último guardado antes de rendirse
            otra = _leer("sesion.json", None) or {}
            try:
                if not otra.get("refresh") or otra["refresh"] == guardada["refresh"]:
                    raise nube.SesionCaducada("")
                guardada, sesion = otra, nube.renovar(otra["refresh"])
            except nube.SesionCaducada:
                self.olvidar()
                return None
            except ErrorNube:
                return self._sin_red(otra)
        except ErrorNube:                # sin red, o el servidor no pudo: nunca se cierra la sesión por eso
            return self._sin_red(guardada)
        cuenta = _cuenta(sesion, guardada["usuario"], guardada["nombre"],
                         google=bool(guardada.get("google")))
        self.recordar(cuenta)
        return cuenta

    @staticmethod
    def _sin_red(guardada):
        """Se entra con la biblioteca local; la sesión se renueva sola cuando vuelva la conexión."""
        return _cuenta(nube.Sesion(guardada["id"], "", guardada["refresh"], 0), guardada["usuario"],
                       guardada["nombre"], sin_conexion=True, google=bool(guardada.get("google")))

    def ultimo_usuario(self):
        return _leer("ultimo.json", {}).get("usuario", "")

    def anotar_ultimo(self, usuario):
        _escribir("ultimo.json", {"usuario": usuario})


def activar(cuenta):
    """Desde aqui, la biblioteca y los ajustes son los de esta cuenta."""
    config.fijar_perfil(cuenta.get("carpeta") or "", cuenta)
