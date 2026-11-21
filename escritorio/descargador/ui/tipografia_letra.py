# -*- coding: utf-8 -*-
"""Tipo de letra (tipografía) con que se pinta la letra de las canciones: la escena de escritorio,
la letra viva y el karaoke. Ajuste «fuente_letra» (mismas claves que en Android).

Las fuentes vienen en `descargador/fuentes_letra/` (licencia OFL, ver OFL.txt) y se cargan con
QFontDatabase la primera vez que se piden. Si una no carga, se usa la predeterminada sin error."""

import sys
import weakref
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

POR_DEFECTO = "predeterminada"

# clave -> (nombre que ve la persona, archivos, peso con que se pide)
FUENTES = {
    "predeterminada": ("Predeterminada", (), None),
    "poppins": ("Poppins", ("Poppins-ExtraBold.ttf", "Poppins-Bold.ttf"), QFont.ExtraBold),
    "bebas": ("Bebas Neue", ("BebasNeue-Regular.ttf",), QFont.Normal),
    "anton": ("Anton", ("Anton-Regular.ttf",), QFont.Normal),
    "pacifico": ("Pacifico", ("Pacifico-Regular.ttf",), QFont.Normal),
    "lobster": ("Lobster", ("Lobster-Regular.ttf",), QFont.Normal),
    "righteous": ("Righteous", ("Righteous-Regular.ttf",), QFont.Normal),
    "serif": ("DM Serif Display", ("DMSerifDisplay-Regular.ttf",), QFont.Normal),
    "bangers": ("Bangers", ("Bangers-Regular.ttf",), QFont.Normal),
}

_familias = {}                 # clave -> familia ya cargada (o None si no se pudo)
_actual = POR_DEFECTO
_vivos = weakref.WeakSet()     # widgets que se repintan al cambiar la tipografía


def carpeta_fuentes():
    """Carpeta con los .ttf (también dentro del .exe de PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "descargador" / "fuentes_letra"
    return Path(__file__).resolve().parent.parent / "fuentes_letra"


def normalizar(clave):
    return clave if clave in FUENTES else POR_DEFECTO


def nombre(clave):
    return FUENTES[normalizar(clave)][0]


def familia(clave):
    """Familia de Qt para la clave (la carga la primera vez), o None = la predeterminada."""
    clave = normalizar(clave)
    if clave == POR_DEFECTO:
        return None
    if clave in _familias:
        return _familias[clave]
    fam = None
    try:
        for archivo in FUENTES[clave][1]:
            ruta = carpeta_fuentes() / archivo
            if not ruta.exists():
                continue
            ident = QFontDatabase.addApplicationFont(str(ruta))
            if ident < 0:
                continue
            nombres = QFontDatabase.applicationFontFamilies(ident)
            if nombres and fam is None:
                fam = nombres[0]
    except Exception:  # noqa: BLE001  (sin fuente: se usa la predeterminada)
        fam = None
    _familias[clave] = fam
    return fam


def adaptar(f, clave=None):
    """Copia de la QFont `f` con la tipografía elegida (o `clave`), mismo tamaño. Con la
    predeterminada, o si la fuente no cargó, devuelve `f` tal cual."""
    clave = normalizar(_actual if clave is None else clave)
    fam = familia(clave)
    if not fam:
        return f
    g = QFont(f)
    g.setFamilies([fam])
    g.setItalic(False)               # las fuentes de aquí no traen cursiva: no se inventa
    peso = FUENTES[clave][2]
    if peso is not None:
        g.setWeight(peso)
    return g


def actual():
    return _actual


def fijar(clave):
    """Cambia la tipografía de toda la letra; las vistas registradas se rehacen al momento."""
    global _actual
    _actual = normalizar(clave)
    for w in list(_vivos):
        try:
            w.al_cambiar_tipografia()
        except RuntimeError:          # el widget ya se destruyó
            pass


def suscribir(widget):
    """El widget recibe `al_cambiar_tipografia()` cuando cambia el ajuste."""
    _vivos.add(widget)
