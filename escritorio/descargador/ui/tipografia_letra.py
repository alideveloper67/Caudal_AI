# -*- coding: utf-8 -*-
"""Tipo de letra (tipografía) con que se pinta la letra de las canciones: la escena de escritorio,
la letra viva y el karaoke. Ajuste «fuente_letra» (mismas claves que en Android).

Las fuentes vienen en `descargador/fuentes_letra/` (licencias libres, ver LICENCIAS.txt) y se cargan con
QFontDatabase la primera vez que se piden. Si una no carga, se usa la predeterminada sin error."""

import sys
import weakref
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF

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
    "lilita": ("Lilita One", ("LilitaOne-Regular.ttf",), QFont.Normal),
    "titan": ("Titan One", ("TitanOne-Regular.ttf",), QFont.Normal),
    "bungee": ("Bungee", ("Bungee-Regular.ttf",), QFont.Normal),
    "russo": ("Russo One", ("RussoOne-Regular.ttf",), QFont.Normal),
    "audiowide": ("Audiowide", ("Audiowide-Regular.ttf",), QFont.Normal),
    "monoton": ("Monoton", ("Monoton-Regular.ttf",), QFont.Normal),
    "abril": ("Abril Fatface", ("AbrilFatface-Regular.ttf",), QFont.Normal),
    "shrikhand": ("Shrikhand", ("Shrikhand-Regular.ttf",), QFont.Normal),
    "staatliches": ("Staatliches", ("Staatliches-Regular.ttf",), QFont.Normal),
    "marker": ("Permanent Marker", ("PermanentMarker-Regular.ttf",), QFont.Normal),
    "kaushan": ("Kaushan Script", ("KaushanScript-Regular.ttf",), QFont.Normal),
    "vibes": ("Great Vibes", ("GreatVibes-Regular.ttf",), QFont.Normal),
    "elite": ("Special Elite", ("SpecialElite-Regular.ttf",), QFont.Normal),
    "pixel": ("Press Start 2P", ("PressStart2P-Regular.ttf",), QFont.Normal),
    "limelight": ("Limelight", ("Limelight-Regular.ttf",), QFont.Normal),
    "caveat": ("Caveat Brush", ("CaveatBrush-Regular.ttf",), QFont.Normal),
    "ops": ("Black Ops One", ("BlackOpsOne-Regular.ttf",), QFont.Normal),
    "courgette": ("Courgette", ("Courgette-Regular.ttf",), QFont.Normal),
}

# las que ya estaban antes de ampliar la colección
DE_SIEMPRE = ("predeterminada", "poppins", "bebas", "anton", "pacifico", "lobster", "righteous", "serif", "bangers")
# cuánto se agranda o achica cada fuente para que todas se vean de un tamaño parecido (las que no
# están aquí van tal cual)
FACTORES = {"titan": 0.92, "bungee": 0.80, "russo": 0.93, "audiowide": 0.88, "monoton": 0.82,
            "shrikhand": 0.92, "staatliches": 1.12, "marker": 0.92, "kaushan": 1.06, "vibes": 1.30,
            "elite": 0.94, "pixel": 0.62, "limelight": 0.90, "caveat": 1.18, "ops": 0.88}
# de trazo tan fino (o tan junto) que un borde encima las empasta: se pintan con bordes finos y sin hueco
FINAS = ("monoton", "vibes")
# aire de más entre palabras (en tamaños de letra) para las que traen un espacio casi invisible
ESPACIO_PALABRAS = {"monoton": 0.30, "vibes": 0.06}
# de letras que se pisan al enlazarse: para dibujar solo su contorno hay que unirlas antes
ENLAZADAS = ("pacifico", "lobster", "bangers", "kaushan", "vibes", "courgette")
# de caligrafía: una palabra entera en mayúsculas no se lee, así que la palabra fuerte no se pasa a mayúsculas
SIN_MAYUSCULAS = ("vibes", "kaushan", "courgette")
# aire de más (subida, bajada) en tamaños de letra, para las que declaran menos alto del que ocupan
AIRE = {"pixel": (0.10, 0.30), "elite": (0.22, 0.04), "vibes": (0.06, 0.06), "titan": (0.08, 0.06),
        "lilita": (0.06, 0.04)}

_leidas = {}                   # archivo -> bytes (leídos en un hilo: el disco no hace esperar a la ventana)
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
            datos = _leidas.pop(archivo, None)
            if datos is not None:
                if not datos:
                    continue
                ident = QFontDatabase.addApplicationFontFromData(QByteArray(datos))
            else:
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


def leer_todas():
    """Lee los archivos (en un hilo): abrir «Diseño de letra» con el disco ocupado paraba la ventana 4 segundos."""
    for clave, datos in list(FUENTES.items()):
        for archivo in (datos[1] or ()):
            if clave in _familias or archivo in _leidas:
                continue
            try:
                _leidas[archivo] = (carpeta_fuentes() / archivo).read_bytes()
            except OSError:
                _leidas[archivo] = b""          # no está: se verá con la predeterminada


def lista(clave):
    """¿Se puede usar ya sin esperar al disco?"""
    clave = normalizar(clave)
    return clave == POR_DEFECTO or clave in _familias or all(a in _leidas for a in (FUENTES[clave][1] or ()))


def calentar_una():
    """Deja puesta una más de las leídas (una por vez, en el hilo de la interfaz). False = no queda ninguna."""
    for clave in FUENTES:
        if clave != POR_DEFECTO and clave not in _familias and lista(clave):
            familia(clave)
            return True
    return False


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
    if clave in ESPACIO_PALABRAS and g.pixelSize() > 0:
        g.setWordSpacing(g.pixelSize() * FACTORES.get(clave, 1.0) * ESPACIO_PALABRAS[clave])
    factor = FACTORES.get(clave, 1.0)
    if factor != 1.0:
        if g.pixelSize() > 0:
            g.setPixelSize(max(1, int(round(g.pixelSize() * factor))))
        elif g.pointSizeF() > 0:
            g.setPointSizeF(max(1.0, g.pointSizeF() * factor))
    return g


def subida_bajada(f, clave=None):
    """(subida, bajada) de una fila escrita con `f` (ya adaptada): lo que declara la fuente, más el aire que
    le falta a las que se salen de su propia caja."""
    clave = normalizar(_actual if clave is None else clave)
    m = QFontMetricsF(f)
    mas_sube, mas_baja = AIRE.get(clave, (0.0, 0.0))
    px = f.pixelSize() if f.pixelSize() > 0 else 0
    return m.ascent() + mas_sube * px, m.descent() + mas_baja * px


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
