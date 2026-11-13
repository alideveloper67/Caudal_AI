# -*- coding: utf-8 -*-
"""Cuentas de Caudal en este equipo.

Cada cuenta tiene su propia biblioteca (me gusta, listas, escuchas, ajustes).
La primera cuenta que se crea hereda los datos que ya habia en el equipo.
Las contrasenas se guardan derivadas con PBKDF2 (nunca en texto).
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import time

from . import config

ITERACIONES = 240_000


class ErrorCuenta(Exception):
    pass


def _derivar(contrasena, sal, iteraciones=ITERACIONES):
    return hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal),
                               iteraciones).hex()


class Cuentas:
    def __init__(self):
        self.archivo = config.carpeta_datos() / "cuentas.json"
        self.datos = {"usuarios": [], "recordado": ""}
        try:
            if self.archivo.exists():
                self.datos.update(json.loads(self.archivo.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass

    def _guardar(self):
        tmp = self.archivo.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.datos, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.archivo)

    def hay_cuentas(self):
        return bool(self.datos["usuarios"])

    def _buscar(self, usuario):
        u = (usuario or "").strip().lower()
        return next((c for c in self.datos["usuarios"] if c["usuario"].lower() == u), None)

    def crear(self, usuario, contrasena, nombre=""):
        usuario = (usuario or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,30}", usuario):
            raise ErrorCuenta("El usuario debe tener de 3 a 30 letras o números "
                              "(también . _ -), sin espacios.")
        if len(contrasena or "") < 6:
            raise ErrorCuenta("La contraseña necesita al menos 6 caracteres.")
        if self._buscar(usuario):
            raise ErrorCuenta("Ese usuario ya existe en este equipo. Inicia sesión.")
        primera = not self.datos["usuarios"]
        sal = secrets.token_hex(16)
        cuenta = {
            "usuario": usuario,
            "nombre": (nombre or "").strip() or usuario,
            "sal": sal,
            "hash": _derivar(contrasena, sal),
            "iteraciones": ITERACIONES,
            "creada": time.time(),
            # la primera cuenta se queda con lo que ya habia en el equipo
            "carpeta": "" if primera else f"perfiles/{usuario.lower()}",
        }
        self.datos["usuarios"].append(cuenta)
        self._guardar()
        return dict(cuenta)

    def entrar(self, usuario, contrasena):
        c = self._buscar(usuario)
        if not c:
            raise ErrorCuenta("No hay ninguna cuenta con ese usuario en este equipo.")
        calculado = _derivar(contrasena or "", c["sal"], c.get("iteraciones", ITERACIONES))
        if not hmac.compare_digest(calculado, c["hash"]):
            raise ErrorCuenta("La contraseña no es correcta.")
        return dict(c)

    def cambiar_contrasena(self, usuario, actual, nueva):
        c = self._buscar(usuario)
        self.entrar(usuario, actual)
        if len(nueva or "") < 6:
            raise ErrorCuenta("La contraseña nueva necesita al menos 6 caracteres.")
        c["sal"] = secrets.token_hex(16)
        c["hash"] = _derivar(nueva, c["sal"])
        c["iteraciones"] = ITERACIONES
        self._guardar()

    def recordar(self, usuario):
        self.datos["recordado"] = usuario or ""
        self._guardar()

    def olvidar(self):
        self.datos["recordado"] = ""
        self._guardar()

    def recordada(self):
        """La cuenta con la sesion guardada, o None."""
        u = self.datos.get("recordado") or ""
        c = self._buscar(u) if u else None
        return dict(c) if c else None

    def ultimo_usuario(self):
        return self.datos.get("ultimo") or ""

    def anotar_ultimo(self, usuario):
        self.datos["ultimo"] = usuario
        self._guardar()


def activar(cuenta):
    """Desde aqui, la biblioteca y los ajustes son los de esta cuenta."""
    config.fijar_perfil(cuenta.get("carpeta") or "", cuenta)
