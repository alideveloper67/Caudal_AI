# -*- coding: utf-8 -*-
"""Escenarios animados de la escena de escritorio. Cada uno vive en su archivo y se registra aquí.

ESCENARIOS: clave -> (nombre visible, "modulo:Clase"). Se importan al elegirse (no al abrir la escena).
"""
import importlib
import os
import threading

ESCENARIOS = {
    "retro": ("Retro", "descargador.ui.escena.escenarios.retro:EscenarioRetro"),
    "synthwave": ("Synthwave", "descargador.ui.escena.fondo_synthwave:FondoSynthwave"),
    "lofi": ("Lo-fi", "descargador.ui.escena.escenarios.imagenes:EscenarioLofi"),
    "cyberpunk": ("Cyberpunk", "descargador.ui.escena.escenarios.imagenes:EscenarioCyberpunk"),
    "samurai": ("Japón antiguo", "descargador.ui.escena.escenarios.imagenes:EscenarioSamurai"),
    "cinnamoroll": ("Cinnamoroll", "descargador.ui.escena.escenarios.imagenes:EscenarioCinnamoroll"),
    "pompompurin": ("Pompompurin", "descargador.ui.escena.escenarios.imagenes:EscenarioPompompurin"),
    "mymelody": ("My Melody", "descargador.ui.escena.escenarios.imagenes:EscenarioMyMelody"),
    "hellokitty": ("Hello Kitty", "descargador.ui.escena.escenarios.imagenes:EscenarioHelloKitty"),
    "kuromi": ("Kuromi", "descargador.ui.escena.escenarios.imagenes:EscenarioKuromi"),
    "ippo": ("Hajime no Ippo", "descargador.ui.escena.escenarios.imagenes:EscenarioIppo"),
    "kaneki": ("Kaneki", "descargador.ui.escena.escenarios.imagenes:EscenarioKaneki"),
    "goku": ("Goku", "descargador.ui.escena.escenarios.imagenes:EscenarioGoku"),
    "propia": ("Mi imagen o GIF", "descargador.ui.escena.escenarios.propia:EscenarioPropia"),
}


_calentadas = False


def calentar():
    """Lee en un hilo las ilustraciones (solo leerlas: quedan en la memoria del sistema), para que elegir un
    escenario no espere al disco."""
    global _calentadas
    if _calentadas:
        return
    _calentadas = True

    def leer():
        try:
            from .imagen_motor import CARPETA
            for nombre in os.listdir(CARPETA):
                with open(os.path.join(CARPETA, nombre), "rb") as f:
                    while f.read(1 << 20):
                        pass
        except OSError:
            pass
    threading.Thread(target=leer, name="escenarios", daemon=True).start()


def preparacion(clave):
    """Lo que conviene hacer en un hilo antes de crear(clave) para que no dé un tirón, o None si no hace falta."""
    datos = ESCENARIOS.get(clave)
    if not datos or not datos[1].split(":")[0].endswith(".imagenes"):
        return None

    def hacer():
        from . import imagen_motor
        modulo, clase = datos[1].split(":")
        nombre = getattr(importlib.import_module(modulo), clase).IMAGEN
        if nombre:
            imagen_motor.adelantar(nombre)
    return hacer


def crear(clave):
    """Una instancia del escenario `clave`, o None si no existe o no se pudo cargar."""
    datos = ESCENARIOS.get(clave)
    if not datos:
        return None
    modulo, clase = datos[1].split(":")
    try:
        return getattr(importlib.import_module(modulo), clase)()
    except Exception:  # noqa: BLE001
        return None


def _para_empaquetar():  # pragma: no cover
    """Nunca se llama: deja escritos los imports para que PyInstaller meta todos los escenarios en el .exe
    (se cargan por nombre con importlib y, sin esto, el empaquetador no los ve)."""
    from . import base, imagen_motor, imagenes, propia, retro  # noqa: F401
    from .. import fondo_synthwave  # noqa: F401
