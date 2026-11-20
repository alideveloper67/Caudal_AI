# -*- coding: utf-8 -*-
"""Desfase de la letra por canción: se suma a ADELANTO_MS, se mueve con Ctrl+→ / Ctrl+← / Ctrl+0
(y con los botones de la página) y se guarda en ajustes["letra_desfases"]. Sin ventanas ni internet."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtGui import QKeySequence, QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

LRC = [(0, ""), (12000, "Cuando la noche cae"), (16000, "y las luces se encienden"),
       (20500, "te busco entre la gente"), (24000, ""), (40000, "baila conmigo")]
PISTA = {"clave": "yt:abc", "video_id": "abc", "titulo": "Noche", "artista": "Luna"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _R(QObject):
    pista_cambio = Signal(object)
    posicion_cambio = Signal(float)
    estado_cambio = Signal(str)

    def __init__(self):
        super().__init__()
        self.actual = None
        self.estado = "sonando"
        self.velocidad = 1.0
        self._posicion = 0.0
        self.saltos = []

    def buscar(self, s):
        self.saltos.append(s)
        self._posicion = s
        self.posicion_cambio.emit(s)


class _Aj(dict):
    """Ajustes falsos: cuenta cuántas veces se guardan."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.guardados = 0

    def guardar(self):
        self.guardados += 1


class _Ctx:
    def __init__(self):
        self.reproductor = _R()
        self.ajustes = _Aj(traducir_letra=False)
        self.avisos = []

    def avisar(self, texto, deshacer=None):
        self.avisos.append(texto)


def bombear(app, seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture
def vista(app, monkeypatch):
    from descargador import catalogo
    from descargador.ui import letra_viva as L
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": LRC,
                                                       "texto": "", "fuente": "LRCLIB"})
    L.CACHE_LETRAS.clear()
    ctx = _Ctx()
    lz = L.LienzoLetra(ctx, compacto=False)
    lz.resize(1100, 680)
    lz.show()
    ctx.reproductor.actual = PISTA
    ctx.reproductor.pista_cambio.emit(PISTA)
    bombear(app, 0.4)
    assert lz.lineas, "la letra tenia que llegar"
    yield lz, ctx
    lz.close()
    lz.deleteLater()


def _atajo(lz, tecla):
    """El QShortcut de la vista para esa tecla (se dispara con su señal, sin depender del foco)."""
    buscado = QKeySequence(tecla).toString()
    for sc in lz.findChildren(QShortcut):
        if sc.key().toString() == buscado:
            return sc
    raise AssertionError(f"no hay atajo {tecla}")


def test_desfase_positivo_mira_un_segundo_despues(vista):
    lz, ctx = vista
    # con +1 s, a los 15 s se canta lo que tocaria a los 16 s (sin desfase)
    ctx.ajustes["letra_desfases"] = {}
    indice_16 = lz._indice(16000)
    ctx.ajustes["letra_desfases"] = {"abc": 1000}
    assert lz._indice(15000) == indice_16
    assert lz.lineas[lz._indice(15000)]["texto"] == "y las luces se encienden"
    # y con el desfase quitado vuelve a la linea de su momento
    ctx.ajustes["letra_desfases"] = {}
    assert lz.lineas[lz._indice(15000)]["texto"] == "Cuando la noche cae"


def test_desfase_negativo_mira_un_segundo_antes(vista):
    lz, ctx = vista
    ctx.ajustes["letra_desfases"] = {}
    indice_16 = lz._indice(16000)
    ctx.ajustes["letra_desfases"] = {"abc": -1000}
    # con -1 s, a los 17 s se canta lo que tocaria a los 16 s
    assert lz._indice(17000) == indice_16
    # el progreso del karaoke sigue el mismo desplazamiento
    ctx.ajustes["letra_desfases"] = {}
    progreso_sin = lz._progreso(indice_16, 16500)
    ctx.ajustes["letra_desfases"] = {"abc": -1000}
    assert lz._progreso(indice_16, 17500) == pytest.approx(progreso_sin)


def test_ctrl_flecha_derecha_adelanta_250_y_guarda(vista):
    lz, ctx = vista
    ctx.ajustes["letra_desfases"] = {}
    _atajo(lz, "Ctrl+Right").activated.emit()
    assert ctx.ajustes["letra_desfases"] == {"abc": 250}
    assert ctx.ajustes.guardados == 1
    assert ctx.avisos[-1] == "Letra adelantada 0,25 s"
    # Ctrl+← lo devuelve a cero: la clave desaparece y avisa que va a tiempo
    _atajo(lz, "Ctrl+Left").activated.emit()
    assert "abc" not in ctx.ajustes["letra_desfases"]
    assert ctx.ajustes.guardados == 2
    assert ctx.avisos[-1] == "Letra a tiempo"
    # atrasar deja el aviso en negativo con coma decimal
    _atajo(lz, "Ctrl+Left").activated.emit()
    assert ctx.ajustes["letra_desfases"] == {"abc": -250}
    assert ctx.avisos[-1] == "Letra atrasada 0,25 s"


def test_ctrl_0_vuelve_a_cero_y_borra_la_clave(vista):
    lz, ctx = vista
    ctx.ajustes["letra_desfases"] = {"abc": -750, "otra": 300}
    _atajo(lz, "Ctrl+0").activated.emit()
    assert ctx.ajustes["letra_desfases"] == {"otra": 300}
    assert ctx.ajustes.guardados == 1
    assert ctx.avisos[-1] == "Letra a tiempo"


def test_el_desfase_tiene_tope_de_10_segundos(vista):
    lz, ctx = vista
    ctx.ajustes["letra_desfases"] = {"abc": 9900}
    _atajo(lz, "Ctrl+Right").activated.emit()
    assert ctx.ajustes["letra_desfases"] == {"abc": 10000}
    assert ctx.avisos[-1] == "Letra adelantada 10,00 s"


def test_sin_la_clave_o_con_basura_vale_cero_y_no_rompe(vista):
    lz, ctx = vista
    ctx.ajustes.pop("letra_desfases", None)
    assert lz._desfase_ms() == 0
    assert lz.lineas[lz._indice(15000)]["texto"] == "Cuando la noche cae"
    ctx.ajustes["letra_desfases"] = "basura"
    assert lz._desfase_ms() == 0
    assert lz.lineas[lz._indice(15000)]["texto"] == "Cuando la noche cae"
    lz.grab()  # pintar con un ajuste roto no falla


def test_botones_de_la_pagina_mueven_la_letra(app, monkeypatch):
    from descargador import catalogo
    from descargador.ui import letra_viva as L
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": LRC,
                                                       "texto": "", "fuente": "LRCLIB"})
    L.CACHE_LETRAS.clear()
    ctx = _Ctx()
    pag = L.PaginaLetra(ctx)
    pag.resize(1100, 680)
    pag.show()
    ctx.reproductor.actual = PISTA
    ctx.reproductor.pista_cambio.emit(PISTA)
    bombear(app, 0.4)
    pag.bt_antes.click()
    assert ctx.ajustes["letra_desfases"] == {"abc": 250}
    pag.bt_despues.click()
    pag.bt_despues.click()
    assert ctx.ajustes["letra_desfases"] == {"abc": -250}
    assert ctx.avisos[-1] == "Letra atrasada 0,25 s"
    pag.close()
    pag.deleteLater()
