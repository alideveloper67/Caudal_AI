# -*- coding: utf-8 -*-
"""Carga de libmpv, el motor de reproduccion.

La DLL vive en bin/mpv junto a la aplicacion (o dentro de _internal cuando
esta empaquetada con PyInstaller). Si no aparece, la app sigue funcionando
para descargar, pero avisa de que no puede reproducir.
"""

import os
import sys

from .config import carpeta_datos, raiz_app

_mpv = None
_error = ""


def carpetas_candidatas():
    raiz = raiz_app()
    return [
        raiz / "bin" / "mpv",
        raiz / "_internal" / "bin" / "mpv",
        carpeta_datos() / "bin" / "mpv",
    ]


def carpeta_mpv():
    for c in carpetas_candidatas():
        if (c / "libmpv-2.dll").exists() or (c / "mpv-2.dll").exists():
            return str(c)
    return ""


def modulo():
    """Devuelve el modulo `mpv` listo para usar, o None si no se puede cargar."""
    global _mpv, _error
    if _mpv is not None:
        return _mpv
    if _error:
        return None
    carpeta = carpeta_mpv()
    if carpeta:
        os.environ["PATH"] = carpeta + os.pathsep + os.environ.get("PATH", "")
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(carpeta)
            except OSError:
                pass
    try:
        import mpv  # noqa: WPS433
    except Exception as e:  # OSError si falta la DLL, ImportError si falta el paquete
        _error = str(e) or "No se encontro el motor de reproduccion."
        return None
    _mpv = mpv
    return mpv


def error():
    return _error
