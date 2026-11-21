# -*- coding: utf-8 -*-
"""Vigía de tirones: anota cada vez que el hilo de la interfaz se queda bloqueado más de 120 ms
y las funciones propias de Caudal (archivos dentro de «descargador») que estaban en ejecución.

Técnica: un QTimer de latido en el hilo de la interfaz (cada 50 ms) y un hilo daemon que solo
cuando el latido se retrasa toma la pila de ese hilo con sys._current_frames(). El registro se
guarda en memoria (últimos 200) y se vuelca a trabones.txt como mucho cada 60 s, solo si hubo
trabones nuevos, desde el hilo muestreador. Sin datos personales: solo archivo, línea, función y ms.
"""
import collections
import sys
import threading
import time
from pathlib import Path

LATIDO_MS = 50
UMBRAL_S = 0.120
MUESTREO_S = 0.025
MAX_TRABONES = 200
VOLCADO_CADA_S = 60.0
PROFUNDIDAD = 4
ARCHIVO = "trabones.txt"

_lock = threading.Lock()
_trabones = collections.deque(maxlen=MAX_TRABONES)   # (ms, pila)
_ref = [0.0]          # instante del último latido
_pila_ult = [None]    # pila tomada durante el bloqueo en curso
_nuevos = [0]         # trabones nuevos desde el último volcado
_carpeta = [None]
_estado = {"iniciado": False, "timer": None}


def _pila_propia(frame):
    """Las funciones de «descargador» más recientes (de dentro hacia fuera), sin rutas completas."""
    salida = []
    f = frame
    while f is not None and len(salida) < PROFUNDIDAD:
        co = f.f_code
        ruta = Path(co.co_filename)
        if "descargador" in ruta.parts and ruta.name != "vigia.py":
            salida.append(f"{ruta.name}:{f.f_lineno} {co.co_name}")
        f = f.f_back
    return " <- ".join(salida) or "(sin funciones de descargador: Qt o librerías)"


def _formatear(lista):
    grupos = {}                                  # pila -> [veces, máximo ms, total ms]
    for ms, pila in lista:
        g = grupos.setdefault(pila, [0, 0, 0])
        g[0] += 1
        g[1] = max(g[1], ms)
        g[2] += ms
    lineas = ["Resumen por pila (de mas a menos ms totales):"]
    for pila, (veces, maximo, total) in sorted(grupos.items(), key=lambda kv: -kv[1][2]):
        lineas.append(f"  veces {veces}  max {maximo} ms  total {total} ms  {pila}")
    lineas.append("")
    lineas.append(f"Trabones de la interfaz (mas de {round(UMBRAL_S * 1000)} ms): {len(lista)} en memoria")
    for ms, pila in lista:
        lineas.append(f"  {ms:5d} ms  {pila}")
    return "\n".join(lineas) + "\n"


def _volcar():
    with _lock:
        copia = list(_trabones)
        _nuevos[0] = 0
    try:
        (Path(_carpeta[0]) / ARCHIVO).write_text(_formatear(copia), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def _muestreador(ident_principal):
    ultimo_volcado = -VOLCADO_CADA_S
    while True:
        time.sleep(MUESTREO_S)
        ahora = time.perf_counter()
        ref = _ref[0]
        if ahora - ref > UMBRAL_S:
            f = sys._current_frames().get(ident_principal)
            if f is not None:
                pila = _pila_propia(f)
                f = None
                with _lock:
                    if _ref[0] == ref:          # sigue siendo el mismo bloqueo
                        _pila_ult[0] = pila
        if _nuevos[0] and ahora - ultimo_volcado >= VOLCADO_CADA_S:
            ultimo_volcado = ahora
            _volcar()


def _latido():
    with _lock:
        ahora = time.perf_counter()
        hueco = ahora - _ref[0]
        pila = _pila_ult[0]
        _pila_ult[0] = None
        _ref[0] = ahora
        if hueco > UMBRAL_S:
            _trabones.append((round(hueco * 1000), pila or "(sin muestra)"))
            _nuevos[0] += 1


def resumen():
    """Texto con los trabones en memoria (los más recientes, como mucho 200)."""
    with _lock:
        copia = list(_trabones)
    return _formatear(copia)


def iniciar(app, carpeta_datos):
    """Arranca el vigía (una sola vez). Se llama desde el hilo de la interfaz."""
    if _estado["iniciado"]:
        return
    from PySide6.QtCore import QTimer
    carpeta = Path(carpeta_datos)
    carpeta.mkdir(parents=True, exist_ok=True)
    _carpeta[0] = str(carpeta)
    _ref[0] = time.perf_counter()
    threading.Thread(target=_muestreador, args=(threading.get_ident(),),
                     name="vigia-tirones", daemon=True).start()
    t = QTimer(app)
    t.setInterval(LATIDO_MS)
    t.timeout.connect(_latido)
    t.start()
    _estado.update(iniciado=True, timer=t)
