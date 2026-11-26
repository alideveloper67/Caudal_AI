# -*- coding: utf-8 -*-
"""¿Se pueden leer las cookies del navegador elegido en Ajustes? Sin hacer esperar a la música.

Chrome y Edge recientes cifran sus cookies de forma que ningún programa externo puede leerlas («Failed to
decrypt with DPAPI», yt-dlp #10927). Si pasa eso se sigue SIN cookies, en lugar de hacer fallar cada canción.

Averiguarlo costaba carísimo: yt-dlp recorre TODA la carpeta del navegador (cachés incluidas) buscando un
archivo, y se hacía antes de la primera canción y en varios hilos a la vez. En un disco de platos, más de 90
segundos medidos sin que sonara nada (y otra vez con cada canción si las cookies sí se podían leer). Ahora:

* se mira solo donde los navegadores guardan ese archivo (`buscar_rapido`);
* se prueba una vez, en un hilo, y el resultado se recuerda entre sesiones (`_VIGENCIA_S`);
* quien necesita saberlo espera como mucho `ESPERA_S`; si aún no se sabe, sigue sin cookies.
"""

import json
import os
import threading
import time

ESPERA_S = 1.5
_VIGENCIA_S = 3 * 86400
_cerrojo = threading.Lock()
_sabido = {}                  # navegador -> True/False
_en_curso = {}                # navegador -> Event (se está probando)
_leido = False


def _archivo():
    from .config import carpeta_datos
    return carpeta_datos() / "cookies_navegador.json"


def _recordar():
    """Lo averiguado en otra sesión (una vez)."""
    global _leido
    if _leido:
        return
    _leido = True
    try:
        datos = json.loads(_archivo().read_text(encoding="utf-8"))
        for nav, d in datos.items():
            if time.time() - float(d.get("fecha") or 0) < _VIGENCIA_S:
                _sabido.setdefault(nav, bool(d.get("puede")))
    except (OSError, ValueError, AttributeError, TypeError):
        pass


def _anotar(nav, puede):
    try:
        try:
            datos = json.loads(_archivo().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        datos[nav] = {"puede": puede, "fecha": time.time()}
        _archivo().write_text(json.dumps(datos), encoding="utf-8")
    except OSError:
        pass


def buscar_rapido(raiz, nombre, _registro=None):
    """Como yt_dlp.cookies._find_files, pero mirando solo los sitios donde está: la carpeta, la de cada
    perfil y su «Network». Recorrerlo todo son cientos de miles de archivos de caché."""
    def candidatos(carpeta):
        yield os.path.join(carpeta, nombre)
        yield os.path.join(carpeta, "Network", nombre)
    vistas = [raiz]
    for nivel in (raiz, os.path.join(raiz, "Profiles")):
        try:
            with os.scandir(nivel) as it:
                vistas += [e.path for e in it if e.is_dir(follow_symlinks=False)]
        except OSError:
            pass
    hechos = set()
    for carpeta in vistas:
        for ruta in candidatos(carpeta):
            if ruta not in hechos and os.path.isfile(ruta):
                hechos.add(ruta)
                yield ruta


def aligerar_ytdlp():
    """yt-dlp busca las cookies con `buscar_rapido` (lo hace en cada canción si las cookies se usan)."""
    try:
        from yt_dlp import cookies
        if hasattr(cookies, "_find_files"):
            cookies._find_files = buscar_rapido
    except Exception:  # noqa: BLE001 - otra versión de yt-dlp: como siempre
        pass


def _leer(nav):
    """Lanza si no se pueden leer."""
    aligerar_ytdlp()
    from yt_dlp.cookies import extract_cookies_from_browser
    return extract_cookies_from_browser(nav)


def _probar(nav, listo):
    try:
        _leer(nav)
        puede = True
    except Exception:  # noqa: BLE001 - cualquier fallo al leerlas: sin cookies
        puede = False
    _sabido[nav] = puede
    _anotar(nav, puede)
    with _cerrojo:
        _en_curso.pop(nav, None)
    listo.set()


def empezar(nav):
    """Lo averigua en un hilo (si no se sabe ya). Devuelve el aviso de que terminó, o None."""
    if not nav or nav == "ninguno":
        return None
    with _cerrojo:
        _recordar()
        if nav in _sabido:
            return None
        listo = _en_curso.get(nav)
        if listo is None:
            listo = _en_curso[nav] = threading.Event()
            threading.Thread(target=_probar, args=(nav, listo), name="cookies-navegador", daemon=True).start()
        return listo


def usable(nav, espera=ESPERA_S):
    """El navegador del que se pueden leer las cookies, o None (también si aún no se sabe)."""
    if not nav or nav == "ninguno":
        return None
    listo = empezar(nav)
    if listo is not None:
        listo.wait(espera)
    if _sabido.get(nav):
        aligerar_ytdlp()
        return nav
    return None


def olvidar(nav=None):
    """Volver a averiguarlo (al cambiar de navegador en Ajustes)."""
    global _leido
    with _cerrojo:
        for n in [nav] if nav else list(_sabido):
            _sabido.pop(n, None)
        _leido = True
