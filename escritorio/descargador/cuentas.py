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

from . import config, nube
from .nube import ErrorNube, SinConexion


class ErrorCuenta(Exception):
    pass


def _leer(nombre, defecto):
    try:
        return json.loads((config.carpeta_datos() / nombre).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def _escribir(nombre, datos):
    ruta = config.carpeta_datos() / nombre
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ruta)


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


def _cuenta(sesion, usuario, nombre, sin_conexion=False):
    return {"id": sesion.user_id if sesion else None, "usuario": usuario,
            "nombre": nombre or usuario, "carpeta": _carpeta_para(sesion.user_id) if sesion else "",
            "sesion": sesion, "sin_conexion": sin_conexion}


class Cuentas:
    def hay_cuentas(self):
        return bool(_leer("perfiles.json", {})) or bool(self.ultimo_usuario())

    def crear(self, usuario, contrasena, nombre=""):
        usuario = (usuario or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]{3,30}", usuario):
            raise ErrorCuenta("El usuario debe tener de 3 a 30 letras o números "
                              "(también . _ -), sin espacios ni tildes.")
        if len(contrasena or "") < 6:
            raise ErrorCuenta("La contraseña necesita al menos 6 caracteres.")
        try:
            if not nube.usuario_libre(usuario):
                raise ErrorCuenta("Ese usuario ya existe. Inicia sesión o elige otro.")
            sesion = nube.registrar(usuario, contrasena, (nombre or "").strip() or usuario)
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
                                  "nombre": cuenta["nombre"], "refresh": s.refresh})

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
        except SinConexion:
            sesion = nube.Sesion(guardada["id"], "", guardada["refresh"], 0)
            cuenta = _cuenta(sesion, guardada["usuario"], guardada["nombre"], sin_conexion=True)
            return cuenta
        except ErrorNube:
            self.olvidar()
            return None
        cuenta = _cuenta(sesion, guardada["usuario"], guardada["nombre"])
        self.recordar(cuenta)
        return cuenta

    def ultimo_usuario(self):
        return _leer("ultimo.json", {}).get("usuario", "")

    def anotar_ultimo(self, usuario):
        _escribir("ultimo.json", {"usuario": usuario})


def activar(cuenta):
    """Desde aqui, la biblioteca y los ajustes son los de esta cuenta."""
    config.fijar_perfil(cuenta.get("carpeta") or "", cuenta)
