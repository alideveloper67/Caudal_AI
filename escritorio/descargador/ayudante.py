# -*- coding: utf-8 -*-
"""Un segundo Caudal, invisible y de baja prioridad, para lo pesado: el reconocedor de voz y las cuentas
de poner la letra a tiempo.

Por qué otro proceso y no un hilo: cargar el reconocedor congelaba la interfaz (7,7 s medidos el 25/11/2026)
y sus cuentas en Python se turnan con las de pintar, así que la animación se entrecortaba en cada canción.
En otro proceso, la interfaz ni se entera; y cuando lleva un rato sin trabajo se cierra y devuelve su memoria
(~300 MB).

Se habla por la entrada y la salida del proceso, una línea JSON por mensaje. `pedir` bloquea: se llama
siempre desde un hilo de fondo (hilos.en_segundo_plano).
"""

import json
import os
import subprocess
import sys
import threading

BANDERA = "--caudal-ayudante"
SIN_TRABAJO_S = 180           # sin pedidos, se cierra
ESPERA_S = 420                # una tarea que no acaba en esto, se corta

_cerrojo = threading.Lock()   # un pedido a la vez (es lo que se quiere: un solo trabajo pesado)
_proc = None
_fallos = 0
_activo = False


class ErrorAyudante(RuntimeError):
    pass


# ------------------------------------------------------------------ lado de la app

def _orden():
    if getattr(sys, "frozen", False):
        return [sys.executable, BANDERA]
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [sys.executable, os.path.join(raiz, "ejecutar.py"), BANDERA]


def _abrir():
    banderas = 0
    if sys.platform == "win32":
        banderas = subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", OMP_NUM_THREADS="2")
    return subprocess.Popen(_orden(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=banderas, env=entorno)


def _leer_respuesta(p, segundos):
    """La línea que conteste el proceso, o None si muere o se pasa de tiempo."""
    caja = []

    def leer():
        try:
            while True:
                linea = p.stdout.readline()
                if not linea:
                    return
                if linea.startswith(b"{"):
                    caja.append(linea)
                    return
        except (OSError, ValueError):
            pass
    h = threading.Thread(target=leer, name="ayudante-lee", daemon=True)
    h.start()
    h.join(segundos)
    return caja[0] if caja else None


def _matar():
    global _proc
    p, _proc = _proc, None
    if p is not None:
        try:
            p.kill()
        except OSError:
            pass


def pedir(nombre, datos, segundos=ESPERA_S):
    """Le pide una tarea (sincronia_tareas.tarea) y devuelve su resultado. Lanza ErrorAyudante si no pudo.
    Si el proceso ya había muerto (o se cerró por falta de trabajo), se abre otro."""
    global _proc, _fallos
    mensaje = (json.dumps({"tarea": nombre, "datos": datos}, ensure_ascii=True) + "\n").encode("ascii")
    with _cerrojo:
        for _intento in range(2):
            if _proc is None or _proc.poll() is not None:
                try:
                    _proc = _abrir()
                except OSError as e:
                    _fallos += 1
                    raise ErrorAyudante(f"no se pudo abrir el ayudante: {e}") from e
            try:
                _proc.stdin.write(mensaje)
                _proc.stdin.flush()
            except (OSError, ValueError):
                _matar()
                continue
            linea = _leer_respuesta(_proc, segundos)
            if linea is None:
                murio = _proc.poll() is not None
                _matar()
                if murio:
                    continue
                raise ErrorAyudante("el ayudante tardó demasiado")
            try:
                r = json.loads(linea)
            except ValueError as e:
                _matar()
                raise ErrorAyudante("respuesta ilegible del ayudante") from e
            _fallos = 0
            if r.get("error"):
                raise ErrorAyudante(r["error"])
            return r.get("resultado")
        _fallos += 1
        raise ErrorAyudante("el ayudante se cerró solo")


def activar():
    """Lo llama main al abrir: sin esto (pruebas, herramientas) lo pesado se hace en el propio proceso."""
    global _activo
    _activo = True


def disponible():
    """False si no está activado o ya falló varias veces seguidas (no se insiste en cada canción)."""
    return _activo and _fallos < 3


def cerrar():
    """Al salir de Caudal."""
    _matar()


# ------------------------------------------------------------------ lado del ayudante

def atender():
    """El bucle del proceso ayudante: lee pedidos, trabaja y contesta. Sale si se queda sin trabajo."""
    entrada = os.fdopen(os.dup(0), "rb", buffering=0)
    salida = os.fdopen(os.dup(1), "wb", buffering=0)
    nulo = os.open(os.devnull, os.O_RDWR)      # lo que imprima cualquier librería no se mezcla
    for fd in (1, 2):
        try:
            os.dup2(nulo, fd)
        except OSError:
            pass
    reloj = [None]

    def programar():
        if reloj[0] is not None:
            reloj[0].cancel()
        t = threading.Timer(SIN_TRABAJO_S, lambda: os._exit(0))
        t.daemon = True
        t.start()
        reloj[0] = t
    programar()
    resto = b""
    while True:
        trozo = entrada.read(65536)
        if not trozo:
            os._exit(0)                         # la app se cerró
        resto += trozo
        while b"\n" in resto:
            linea, resto = resto.split(b"\n", 1)
            if not linea.strip():
                continue
            reloj[0].cancel()
            try:
                m = json.loads(linea)
                from . import sincronia_tareas
                r = {"resultado": sincronia_tareas.tarea(m.get("tarea"), m.get("datos") or {})}
            except Exception as e:  # noqa: BLE001
                r = {"error": f"{type(e).__name__}: {e}"}
            salida.write((json.dumps(r, ensure_ascii=True, default=str) + "\n").encode("ascii"))
            programar()
