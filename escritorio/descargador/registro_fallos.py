# -*- coding: utf-8 -*-
"""Cuaderno de fallos: lo que sale mal queda escrito en fallos.log.

En el .exe no hay consola, asi que un error en un boton o en un hilo se perdia
sin dejar rastro. Aqui se anotan (con hora y version) los errores de Python de
la interfaz y de los hilos, y los avisos graves de Qt. El archivo no pasa de
~1 MB: al llenarse se guarda una copia (.1) y se empieza otro.
"""

import os
import sys
import threading
import time
import traceback

TOPE = 1024 * 1024
_ruta = {"archivo": None}
_candado = threading.Lock()


def _escribir(texto):
    ruta = _ruta["archivo"]
    if not ruta:
        return
    try:
        with _candado:
            if os.path.exists(ruta) and os.path.getsize(ruta) > TOPE:
                os.replace(ruta, ruta + ".1")
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(texto)
    except Exception:  # noqa: BLE001 - el cuaderno nunca debe tumbar la app
        pass


_ultimo = {"clave": None, "cuando": 0.0, "repetido": 0}


def anotar(titulo, detalle=""):
    """Anota un fallo. El mismo fallo repetido en ráfaga (p. ej. desde una señal que se
    dispara muchas veces seguidas) se escribe una vez y luego solo se cuenta: así una
    ráfaga no llena el disco desde el hilo de la interfaz."""
    from .version import VERSION
    clave = (titulo, detalle)
    ahora = time.monotonic()
    with _candado:
        if clave == _ultimo["clave"] and ahora - _ultimo["cuando"] < 10:
            _ultimo["repetido"] += 1
            _ultimo["cuando"] = ahora
            return
        repetido = _ultimo["repetido"]
        _ultimo.update(clave=clave, cuando=ahora, repetido=0)
    if repetido:
        _escribir(f"(el fallo anterior se repitió {repetido} veces más)\n")
    _escribir(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Caudal {VERSION} · {titulo}\n"
              f"{detalle.rstrip()}\n")


def activar(carpeta):
    _ruta["archivo"] = os.path.join(str(carpeta), "fallos.log")
    anterior = sys.excepthook

    def gancho(tipo, valor, tb):
        anotar("Error en la interfaz", "".join(traceback.format_exception(tipo, valor, tb)))
        try:
            if anterior and anterior is not sys.__excepthook__:
                anterior(tipo, valor, tb)
        except Exception:  # noqa: BLE001
            pass

    sys.excepthook = gancho

    def gancho_hilo(args):
        if args.exc_type is SystemExit:
            return
        anotar(f"Error en un hilo ({getattr(args.thread, 'name', '?')})",
               "".join(traceback.format_exception(args.exc_type, args.exc_value,
                                                  args.exc_traceback)))

    threading.excepthook = gancho_hilo

    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler

        graves = {QtMsgType.QtCriticalMsg: "Qt crítico", QtMsgType.QtFatalMsg: "Qt fatal"}

        def mensajes_qt(tipo, contexto, mensaje):
            if tipo in graves:
                anotar(graves[tipo], f"{mensaje}\n({contexto.file}:{contexto.line})")
        qInstallMessageHandler(mensajes_qt)
    except Exception:  # noqa: BLE001
        pass
