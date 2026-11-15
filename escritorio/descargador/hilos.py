# -*- coding: utf-8 -*-
"""Trabajo en segundo plano con respuesta en el hilo de la interfaz.

    en_segundo_plano(funcion, arg1, ok=al_terminar, error=al_fallar, dueno=widget)

`ok` y `error` se llaman en el hilo principal. Si el `dueno` (un QObject) ya se
destruyo cuando llega la respuesta, la respuesta se descarta: asi una pagina que
se cerro no recibe datos de una busqueda vieja.
"""

import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

try:
    from shiboken6 import isValid as _valido
except ImportError:  # pragma: no cover
    def _valido(_obj):
        return True


class _Senales(QObject):
    listo = Signal(object)
    fallo = Signal(object)


class _Trabajo(QRunnable):
    def __init__(self, funcion, args, kwargs):
        super().__init__()
        self.setAutoDelete(True)
        self.funcion = funcion
        self.args = args
        self.kwargs = kwargs
        self.senales = _Senales()

    def run(self):
        try:
            resultado = self.funcion(*self.args, **self.kwargs)
        except Exception as e:  # noqa: BLE001 - se informa a quien llamo
            e._traza = traceback.format_exc()
            try:
                self.senales.fallo.emit(e)
            except RuntimeError:
                pass
            return
        try:
            self.senales.listo.emit(resultado)
        except RuntimeError:
            pass


_POOL = QThreadPool()
_POOL.setMaxThreadCount(8)
# carril aparte para lo que la persona espera al instante (enviar un mensaje,
# abrir un chat): asi no se queda en cola detras de la musica, las letras o
# el analisis de las transiciones, que pueden ocupar el carril normal un rato
_POOL_RAPIDO = QThreadPool()
_POOL_RAPIDO.setMaxThreadCount(4)
_vivos = set()


def en_segundo_plano(funcion, *args, ok=None, error=None, dueno=None, urgente=False, **kwargs):
    trabajo = _Trabajo(funcion, args, kwargs)
    senales = trabajo.senales
    _vivos.add(senales)

    def _ok(resultado):
        _vivos.discard(senales)
        if dueno is not None and not _valido(dueno):
            return
        if ok:
            ok(resultado)

    def _error(exc):
        _vivos.discard(senales)
        if dueno is not None and not _valido(dueno):
            return
        if error:
            error(exc)

    senales.listo.connect(_ok)
    senales.fallo.connect(_error)
    (_POOL_RAPIDO if urgente else _POOL).start(trabajo)
    return trabajo


def esperar_todo(ms=3000):
    _POOL.waitForDone(ms)
    _POOL_RAPIDO.waitForDone(ms)
