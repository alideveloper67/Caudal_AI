# -*- coding: utf-8 -*-
"""Escenarios animados de la escena de escritorio. Cada uno vive en su archivo y se registra aquí.

ESCENARIOS: clave -> (nombre visible, "modulo:Clase"). Se importan al elegirse (no al abrir la escena).
"""
import importlib

ESCENARIOS = {
    "synthwave": ("Synthwave", "descargador.ui.escena.fondo_synthwave:FondoSynthwave"),
    "retro": ("Retro", "descargador.ui.escena.escenarios.retro:EscenarioRetro"),
    "cyberpunk": ("Cyberpunk", "descargador.ui.escena.escenarios.cyberpunk:EscenarioCyberpunk"),
    "samurai": ("Japón samurái", "descargador.ui.escena.escenarios.samurai:EscenarioSamurai"),
    "boxeo": ("Boxeo", "descargador.ui.escena.escenarios.boxeo:EscenarioBoxeo"),
    "gym": ("Gym", "descargador.ui.escena.escenarios.gym:EscenarioGym"),
    "fan_kitty": ("Fan de Hello Kitty", "descargador.ui.escena.escenarios.fan_kitty:EscenarioFanKitty"),
    "gotico": ("Gótico", "descargador.ui.escena.escenarios.gotico:EscenarioGotico"),
    "lofi": ("Lo-fi", "descargador.ui.escena.escenarios.lofi:EscenarioLofi"),
    "kuromi": ("Kuromi", "descargador.ui.escena.escenarios.kuromi:EscenarioKuromi"),
    "cinnamoroll": ("Cinnamoroll", "descargador.ui.escena.escenarios.cinnamoroll:EscenarioCinnamoroll"),
    "pompompurin": ("Pompompurin", "descargador.ui.escena.escenarios.pompompurin:EscenarioPompompurin"),
    "hellokitty": ("Hello Kitty", "descargador.ui.escena.escenarios.hellokitty:EscenarioHelloKitty"),
    "mymelody": ("My Melody", "descargador.ui.escena.escenarios.mymelody:EscenarioMyMelody"),
}


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
    from . import base, boxeo, cinnamoroll, cyberpunk, fan_kitty, gotico, gym, hellokitty  # noqa: F401
    from . import kuromi, lofi, mymelody, pompompurin, retro, sakura, samurai  # noqa: F401
    from .. import fondo_synthwave  # noqa: F401
