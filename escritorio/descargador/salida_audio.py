# -*- coding: utf-8 -*-
"""¿Por dónde suena ahora? Audífonos, parlante o bluetooth (para el ecualizador por salida).

En Windows se pregunta a la propia API de sonido (MMDevice, con ctypes: sin instalar nada) cuál es
la salida predeterminada, su nombre, su forma (audífonos, altavoces...) y de qué bus viene
(bluetooth, USB, la placa). `tipo_salida` decide con esos datos y es lógica pura (se prueba sin
hardware)."""

import sys

AUDIFONOS, PARLANTE, BLUETOOTH = "audifonos", "parlante", "bluetooth"
TIPOS = (AUDIFONOS, PARLANTE, BLUETOOTH)
NOMBRES_TIPO = {AUDIFONOS: "Audífonos", PARLANTE: "Parlante", BLUETOOTH: "Bluetooth"}

# EndpointFormFactor de Windows
_FORMA_AUDIFONOS = {3, 5, 6}          # Headphones, Headset, Handset
_PALABRAS_BT = ("bluetooth", "airpods", "buds", "hands-free", "manos libres", "a2dp", "bt ")
_PALABRAS_AUDIFONOS = ("auricular", "audífono", "audifono", "headphone", "headset", "casco",
                       "earphone", "cascos")


def tipo_salida(nombre="", forma=None, enumerador=""):
    """Clasifica una salida de sonido. forma: EndpointFormFactor (o None); enumerador: bus del
    dispositivo («BTHENUM» = bluetooth, «USB», «HDAUDIO»...)."""
    n = f" {str(nombre or '').lower()} "
    e = str(enumerador or "").upper()
    if e.startswith("BTH") or any(p in n for p in _PALABRAS_BT):
        return BLUETOOTH
    if forma in _FORMA_AUDIFONOS or any(p in n for p in _PALABRAS_AUDIFONOS):
        return AUDIFONOS
    return PARLANTE


# ================================================================ Windows (MMDevice por ctypes)

def _salida_windows():
    """(nombre, forma, enumerador) de la salida predeterminada, o None si no se pudo."""
    import ctypes
    from ctypes import POINTER, byref, c_uint, c_ushort, c_void_p, c_wchar_p, wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD), ("d3", wintypes.WORD),
                    ("d4", ctypes.c_ubyte * 8)]

    def guid(texto):
        g = GUID()
        ctypes.oledll.ole32.CLSIDFromString(c_wchar_p(texto), byref(g))
        return g

    class PROPERTYKEY(ctypes.Structure):
        _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [("vt", c_ushort), ("r1", c_ushort), ("r2", c_ushort), ("r3", c_ushort),
                    ("valor", c_void_p), ("extra", c_void_p)]

    ole32 = ctypes.windll.ole32
    ole32.CoInitializeEx(None, 2)        # ya iniciado por Qt: da igual lo que conteste

    def metodo(obj, indice, *tipos):
        vtabla = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
        prototipo = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *tipos)
        return prototipo(vtabla[indice])

    enum = c_void_p()
    clsid = guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
    iid = guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
    ctypes.oledll.ole32.CoCreateInstance(byref(clsid), None, 1 | 4 | 16, byref(iid), byref(enum))
    soltar = []
    try:
        soltar.append(enum)
        disp = c_void_p()
        # GetDefaultAudioEndpoint(eRender=0, eMultimedia=1)
        metodo(enum, 4, c_uint, c_uint, POINTER(c_void_p))(enum, 0, 1, byref(disp))
        soltar.append(disp)
        almacen = c_void_p()
        metodo(disp, 4, wintypes.DWORD, POINTER(c_void_p))(disp, 0, byref(almacen))   # STGM_READ
        soltar.append(almacen)
        obtener = metodo(almacen, 5, POINTER(PROPERTYKEY), POINTER(PROPVARIANT))

        def leer(fmtid, pid):
            clave = PROPERTYKEY(guid(fmtid), pid)
            pv = PROPVARIANT()
            try:
                obtener(almacen, byref(clave), byref(pv))
            except OSError:
                return None
            try:
                if pv.vt == 31 and pv.valor:          # VT_LPWSTR
                    return ctypes.wstring_at(pv.valor)
                if pv.vt in (19, 3):                   # VT_UI4 / VT_I4
                    return int(pv.valor or 0) & 0xFFFFFFFF
                return None
            finally:
                ole32.PropVariantClear(byref(pv))

        nombre = leer("{A45C254E-DF1C-4EFD-8020-67D146A850E0}", 14) or ""
        forma = leer("{1DA5D803-D492-4EDD-8C23-E0C0FFEE7F0E}", 0)
        enumerador = leer("{A45C254E-DF1C-4EFD-8020-67D146A850E0}", 24) or ""
        return nombre, (forma if isinstance(forma, int) else None), \
            (enumerador if isinstance(enumerador, str) else "")
    finally:
        for obj in reversed(soltar):
            if obj:
                try:
                    metodo(obj, 2)(obj)               # Release
                except Exception:  # noqa: BLE001
                    pass


def salida_actual():
    """{'tipo', 'nombre'} de la salida predeterminada, o None si este sistema no lo dice."""
    if sys.platform != "win32":
        return None
    try:
        datos = _salida_windows()
    except Exception:  # noqa: BLE001
        return None
    if not datos:
        return None
    nombre, forma, enumerador = datos
    return {"tipo": tipo_salida(nombre, forma, enumerador), "nombre": nombre}
