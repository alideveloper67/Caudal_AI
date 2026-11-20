# -*- coding: utf-8 -*-
"""Fondo vivo: pone una ventana detrás de los iconos del escritorio de Windows.

Es el mismo truco que usan los fondos animados: se manda al Progman el mensaje 0x052C
para que cree una ventana WorkerW por debajo de los iconos, y ahí se incrusta nuestra
ventana con SetParent. Al soltarla se vuelve a poner el mismo fondo de pantalla (sin
cambiarlo y sin tocar el registro) para que Windows repinte el escritorio.

Fuera de Windows todo devuelve False / 0 / None sin tocar nada. Ninguna función lanza
excepciones: cualquier fallo de user32 se traga y devuelve el valor de "no se pudo".
"""

import ctypes
import sys
from ctypes import wintypes

ES_WINDOWS = sys.platform == "win32"

MSG_WORKERW = 0x052C          # mensaje que hace aparecer la WorkerW detrás de los iconos
SMTO_NORMAL = 0               # SendMessageTimeoutW: espera normal
SPI_GETDESKWALLPAPER = 0x0073
SPI_SETDESKWALLPAPER = 0x0014
LONGITUD_RUTA = 260           # MAX_PATH


def _preparar(u):
    """Declara argtypes/restype de las funciones de user32 que usamos.

    Recibe el objeto user32 (el real o un falso de las pruebas). Si un método no admite
    atributos (un falso en Python), se omite la declaración sin error.
    """
    def declarar(nombre, restype, argtypes):
        try:
            f = getattr(u, nombre)
            f.restype = restype
            f.argtypes = argtypes
        except (AttributeError, TypeError):
            pass

    declarar("FindWindowW", wintypes.HWND, [wintypes.LPCWSTR, wintypes.LPCWSTR])
    declarar("FindWindowExW", wintypes.HWND,
             [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR])
    declarar("SendMessageTimeoutW", wintypes.LPARAM,
             [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
              wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)])
    if hasattr(ctypes, "WINFUNCTYPE"):
        tipo_enum = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        declarar("EnumWindows", wintypes.BOOL, [tipo_enum, wintypes.LPARAM])
    declarar("SetParent", wintypes.HWND, [wintypes.HWND, wintypes.HWND])
    declarar("SystemParametersInfoW", wintypes.BOOL,
             [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.DWORD])
    return u


def _cargar_user32():
    """user32 real, solo en Windows; en otro sistema no existe."""
    if not ES_WINDOWS:
        return None
    try:
        return _preparar(ctypes.WinDLL("user32", use_last_error=True))
    except OSError:
        return None


_user32 = _cargar_user32()


def _usar(u):
    """El user32 a usar: el que llega (pruebas) o el real. None si no es Windows."""
    if not ES_WINDOWS:
        return None
    return _user32 if u is None else u


def _h(valor):
    """Convierte un handle devuelto por ctypes (None si era NULL) en entero (0)."""
    return int(valor) if valor else 0


def es_compatible(u=None) -> bool:
    """True si estamos en Windows y existe la ventana "Progman" del escritorio."""
    u = _usar(u)
    if u is None:
        return False
    try:
        return _h(u.FindWindowW("Progman", None)) != 0
    except Exception:
        return False


def buscar_workerw(u=None) -> int:
    """Devuelve el handle de la WorkerW que queda detrás de los iconos, o 0."""
    u = _usar(u)
    if u is None:
        return 0
    try:
        progman = _h(u.FindWindowW("Progman", None))
        if not progman:
            return 0

        # pedirle al Progman que cree la WorkerW (dos llamadas, como hacen los fondos vivos)
        resultado = ctypes.c_size_t(0)
        u.SendMessageTimeoutW(progman, MSG_WORKERW, 0xD, 0x1, SMTO_NORMAL, 1000,
                              ctypes.byref(resultado))
        u.SendMessageTimeoutW(progman, MSG_WORKERW, 0, 0, SMTO_NORMAL, 1000,
                              ctypes.byref(resultado))

        # la WorkerW buscada es la hermana siguiente de la ventana que contiene SHELLDLL_DefView
        encontrado = [0]

        def al_encontrar(hwnd, _lparam):
            try:
                if _h(u.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)):
                    workerw = _h(u.FindWindowExW(None, hwnd, "WorkerW", None))
                    if workerw:
                        encontrado[0] = workerw
                        return 0          # ya la tenemos: dejar de enumerar
                return 1
            except Exception:
                return 0

        if hasattr(ctypes, "WINFUNCTYPE"):
            tipo_enum = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            callback = tipo_enum(al_encontrar)   # se guarda en variable: no se recoge antes de tiempo
            u.EnumWindows(callback, 0)
        if encontrado[0]:
            return encontrado[0]

        # Windows 11 24H2: la WorkerW cuelga directamente del Progman
        return _h(u.FindWindowExW(progman, None, "WorkerW", None))
    except Exception:
        return 0


def incrustar_como_fondo(hwnd: int, u=None) -> bool:
    """Mete la ventana `hwnd` dentro de la WorkerW (detrás de los iconos).

    Devuelve False si no es compatible, si no hay WorkerW o si SetParent falla.
    """
    u = _usar(u)
    if u is None or not hwnd:
        return False
    try:
        if not es_compatible(u):
            return False
        workerw = buscar_workerw(u)
        if not workerw:
            return False
        ctypes.set_last_error(0)
        previo = u.SetParent(hwnd, workerw)
        if _h(previo):
            return True
        # SetParent devuelve NULL también cuando no había padre previo: ahí manda GetLastError
        return ctypes.get_last_error() == 0
    except Exception:
        return False


def soltar_de_fondo(hwnd: int, u=None) -> None:
    """Saca la ventana de la WorkerW y repinta el fondo sin cambiarlo.

    Lee la ruta actual del fondo y la vuelve a poner (flags 0: no escribe en el registro).
    Si no se puede leer la ruta, no se toca el fondo.
    """
    u = _usar(u)
    if u is None or not hwnd:
        return
    try:
        u.SetParent(hwnd, None)
        ruta = ctypes.create_unicode_buffer(LONGITUD_RUTA)
        leido = u.SystemParametersInfoW(SPI_GETDESKWALLPAPER, LONGITUD_RUTA, ruta, 0)
        if leido and ruta.value:
            u.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, ruta, 0)
    except Exception:
        return
