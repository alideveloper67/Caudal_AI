# -*- coding: utf-8 -*-
"""Pruebas del fondo vivo (escritorio_win). Usan un user32 falso: nunca tocan el escritorio real."""
import ctypes
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtWidgets import QApplication

from descargador.ui.escena import escritorio_win as ew

SPI_GET = 0x0073
SPI_SET = 0x0014


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class FalsoUser32:
    """Imita las funciones de user32 que usa el módulo y registra cada llamada."""

    def __init__(self, progman=0x100, ventanas=(), defview=None, workerw_tras=None,
                 workerw_progman=0, setparent=1, error=0, spi_get=1, ruta="C:\\fondo.jpg",
                 lanza=None):
        self.progman = progman
        self.ventanas = list(ventanas)
        self.defview = defview or {}            # ventana padre -> SHELLDLL_DefView
        self.workerw_tras = workerw_tras or {}  # ventana -> WorkerW hermana siguiente
        self.workerw_progman = workerw_progman  # WorkerW colgando del Progman (Win 11)
        self.setparent_ret = setparent
        self.error = error
        self.spi_get_ret = spi_get
        self.ruta = ruta
        self.lanza = lanza
        self.llamadas = []
        self.escrituras = []

    def FindWindowW(self, clase, titulo):
        self.llamadas.append(("FindWindowW", clase, titulo))
        return self.progman if clase == "Progman" else 0

    def FindWindowExW(self, padre, despues, clase, titulo):
        self.llamadas.append(("FindWindowExW", padre, despues, clase, titulo))
        if clase == "SHELLDLL_DefView":
            return self.defview.get(padre, 0)
        if clase == "WorkerW":
            if padre is None:
                return self.workerw_tras.get(despues, 0)
            if padre == self.progman:
                return self.workerw_progman
        return 0

    def SendMessageTimeoutW(self, hwnd, msg, wp, lp, flags, timeout, resultado):
        self.llamadas.append(("SendMessageTimeoutW", hwnd, msg, wp, lp, flags, timeout))
        return 1

    def EnumWindows(self, cb, lp):
        self.llamadas.append(("EnumWindows", lp))
        for h in self.ventanas:
            if not cb(h, lp):
                break
        return 1

    def SetParent(self, hijo, padre):
        self.llamadas.append(("SetParent", hijo, padre))
        if self.lanza is not None:
            raise self.lanza
        if not self.setparent_ret and self.error:
            ctypes.set_last_error(self.error)
        return self.setparent_ret

    def SystemParametersInfoW(self, accion, param, pv, flags):
        self.llamadas.append(("SystemParametersInfoW", accion, param, flags))
        if accion == SPI_GET:
            if self.spi_get_ret:
                pv.value = self.ruta
            return self.spi_get_ret
        self.escrituras.append(pv.value)
        return 1


def _nombres(fake, *nombres):
    return [l for l in fake.llamadas if l[0] in nombres]


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(ew, "ES_WINDOWS", True)


def test_es_compatible_con_progman(windows):
    assert ew.es_compatible(FalsoUser32(progman=0x100)) is True
    assert ew.es_compatible(FalsoUser32(progman=0)) is False


def test_encuentra_workerw_por_shelldllview(windows):
    fake = FalsoUser32(ventanas=[0x200, 0x300], defview={0x300: 0x310},
                       workerw_tras={0x300: 0x400}, workerw_progman=0x500)
    assert ew.buscar_workerw(fake) == 0x400
    # el mensaje 0x052C va dos veces: (0xD, 1) y luego (0, 0)
    mensajes = _nombres(fake, "SendMessageTimeoutW")
    assert mensajes == [
        ("SendMessageTimeoutW", 0x100, 0x052C, 0xD, 0x1, 0, 1000),
        ("SendMessageTimeoutW", 0x100, 0x052C, 0, 0, 0, 1000),
    ]


def test_encuentra_workerw_via_windows_11(windows):
    # sin SHELLDLL_DefView en ninguna ventana: la WorkerW cuelga del Progman
    fake = FalsoUser32(progman=0x100, ventanas=[0x200], workerw_progman=0x500)
    assert ew.buscar_workerw(fake) == 0x500
    assert ("FindWindowExW", 0x100, None, "WorkerW", None) in fake.llamadas


def test_sin_progman_devuelve_cero_sin_mensajes(windows):
    fake = FalsoUser32(progman=0)
    assert ew.buscar_workerw(fake) == 0
    assert ew.incrustar_como_fondo(0x999, fake) is False
    assert _nombres(fake, "SendMessageTimeoutW", "SetParent") == []


def test_incrustar_llama_setparent_con_workerw(windows):
    fake = FalsoUser32(ventanas=[0x300], defview={0x300: 0x310}, workerw_tras={0x300: 0x400})
    assert ew.incrustar_como_fondo(0x999, fake) is True
    assert ("SetParent", 0x999, 0x400) in fake.llamadas


def test_incrustar_sin_workerw_devuelve_false(windows):
    fake = FalsoUser32(progman=0x100, workerw_progman=0)
    assert ew.incrustar_como_fondo(0x999, fake) is False
    assert _nombres(fake, "SetParent") == []


def test_incrustar_error_de_setparent_devuelve_false(windows):
    fake = FalsoUser32(workerw_progman=0x500, setparent=0, error=5)
    assert ew.incrustar_como_fondo(0x999, fake) is False


def test_incrustar_setparent_sin_padre_previo_sin_error_es_true(windows):
    # SetParent devuelve NULL pero sin error: era una ventana sin padre previo, todo bien
    fake = FalsoUser32(workerw_progman=0x500, setparent=0, error=0)
    assert ew.incrustar_como_fondo(0x999, fake) is True


def test_soltar_pone_padre_nulo_y_repinta_fondo_sin_cambiarlo(windows):
    fake = FalsoUser32(ruta="C:\\fondo.jpg")
    ew.soltar_de_fondo(0x999, fake)
    assert ("SetParent", 0x999, None) in fake.llamadas
    assert _nombres(fake, "SystemParametersInfoW") == [
        ("SystemParametersInfoW", SPI_GET, 260, 0),
        ("SystemParametersInfoW", SPI_SET, 0, 0),
    ]
    # la ruta que se vuelve a poner es la misma que se leyó
    assert fake.escrituras == ["C:\\fondo.jpg"]


def test_soltar_no_reescribe_fondo_si_no_se_puede_leer(windows):
    fake = FalsoUser32(spi_get=0)
    ew.soltar_de_fondo(0x999, fake)
    assert fake.escrituras == []
    assert ("SetParent", 0x999, None) in fake.llamadas


def test_fuera_de_windows_todo_devuelve_false_sin_llamar(monkeypatch):
    monkeypatch.setattr(ew, "ES_WINDOWS", False)
    fake = FalsoUser32(ventanas=[0x300], defview={0x300: 0x310}, workerw_tras={0x300: 0x400})
    assert ew.es_compatible(fake) is False
    assert ew.buscar_workerw(fake) == 0
    assert ew.incrustar_como_fondo(0x999, fake) is False
    assert ew.soltar_de_fondo(0x999, fake) is None
    assert fake.llamadas == []


def test_oserror_del_falso_no_se_propaga(windows):
    fake = FalsoUser32(workerw_progman=0x500, lanza=OSError("fallo de prueba"))
    assert ew.incrustar_como_fondo(0x999, fake) is False
    assert ew.soltar_de_fondo(0x999, fake) is None
    fake_sin_progman = FalsoUser32(progman=0)
    assert ew.buscar_workerw(fake_sin_progman) == 0
