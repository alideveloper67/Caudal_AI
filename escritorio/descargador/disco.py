# -*- coding: utf-8 -*-
"""Guardar archivos pequeños sin que la interfaz espere al disco.

Un guardado (ajustes, XP del Modo gamer…) tardaba 50-300 ms cuando el antivirus o el disco estaban
ocupados, y se hacía en el hilo que pinta. Aquí se anota QUÉ hay que escribir y un hilo aparte lo
escribe; si llegan varios del mismo archivo, solo se escribe el último. Cada archivo se cambia de una
vez (se escribe al lado y se sustituye): un corte de luz no lo deja a medias.

Hasta que `activar()` no se llama (lo hace main al abrir la app), todo se escribe en el momento: las
pruebas y las herramientas siguen viendo el archivo nada más guardarlo.
"""

import os
import threading
import time

_cerrojo = threading.Condition()
_pendientes = {}              # ruta -> texto por escribir
_escribiendo = set()          # rutas que se escriben ahora mismo
_activo = False
_hilo = None


def _escribir_ya(ruta, texto):
    """Escribe el archivo de una vez. True si quedó guardado."""
    tmp = f"{ruta}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(texto)
        for intento in range(4):
            try:
                os.replace(tmp, ruta)
                return True
            except PermissionError:          # el antivirus lo tiene abierto un instante
                time.sleep(0.05 * (intento + 1))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)
        return True
    except OSError:
        return False
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _trabajar():
    while True:
        with _cerrojo:
            while not _pendientes:
                _cerrojo.wait()
            ruta, texto = next(iter(_pendientes.items()))
            del _pendientes[ruta]
            _escribiendo.add(ruta)
        try:
            _escribir_ya(ruta, texto)
        finally:
            with _cerrojo:
                _escribiendo.discard(ruta)
                _cerrojo.notify_all()


def activar():
    """A partir de aquí se escribe en segundo plano."""
    global _activo, _hilo
    with _cerrojo:
        if _hilo is None:
            _hilo = threading.Thread(target=_trabajar, name="guardar-disco", daemon=True)
            _hilo.start()
        _activo = True


def desactivar():
    """Vuelve a escribir al momento (y termina lo pendiente)."""
    global _activo
    _activo = False
    vaciar()


def escribir(ruta, texto):
    """Guarda `texto` en `ruta`. Sin esperar al disco si está activado."""
    ruta = str(ruta)
    if not _activo:
        return _escribir_ya(ruta, texto)
    with _cerrojo:
        _pendientes[ruta] = texto
        _cerrojo.notify_all()
    return True


def vaciar(ruta=None, segundos=5.0):
    """Espera a que lo pendiente (o ese archivo) esté escrito. True si terminó a tiempo."""
    ruta = None if ruta is None else str(ruta)
    fin = time.monotonic() + segundos

    def queda():
        if ruta is None:
            return bool(_pendientes or _escribiendo)
        return ruta in _pendientes or ruta in _escribiendo
    with _cerrojo:
        while queda():
            resto = fin - time.monotonic()
            if resto <= 0:
                return False
            _cerrojo.wait(resto)
    return True
