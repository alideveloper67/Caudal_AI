# -*- coding: utf-8 -*-
"""Todos los escenarios de la escena: cargan, pintan sin errores, se mueven con la música y van fluidos."""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena import escenarios

CLAVES = sorted(escenarios.ESCENARIOS)
TOPE_MS = 12.0          # por cuadro a 1920x1080 (sin contar el primero, que arma la caché)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _render(w):
    img = QImage(w.width(), w.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    w.render(img)
    return img


def _avanzar(w, n=12, valores=None):
    w.fijar_espectro(valores if valores is not None else [])
    for _ in range(n):
        if hasattr(w, "_cuadro"):
            w._cuadro()


@pytest.mark.parametrize("clave", CLAVES)
def test_carga_y_pinta(app, clave):
    w = escenarios.crear(clave)
    assert w is not None, f"no se pudo crear {clave}"
    w.resize(1280, 720)
    img = _render(w)
    assert not img.isNull()
    # no es una pantalla de un solo color
    colores = {img.pixel(x, y) for x in range(0, 1280, 160) for y in range(0, 720, 120)}
    assert len(colores) > 4


@pytest.mark.parametrize("clave", CLAVES)
def test_espectros_raros_no_rompen(app, clave):
    w = escenarios.crear(clave)
    w.resize(640, 360)
    for v in ([], [0.5] * 64, [1.0] * 7, [0.0], [float("nan"), 2.0, -1.0]):
        _avanzar(w, 3, v)
        _render(w)


@pytest.mark.parametrize("clave", [c for c in CLAVES if c != "synthwave"])
def test_la_musica_se_nota(app, clave):
    w = escenarios.crear(clave)
    w.resize(800, 450)
    _avanzar(w, 20, [])
    quieto = _render(w)
    _avanzar(w, 20, [1.0] * 32)
    fuerte = _render(w)
    distintos = sum(1 for x in range(0, 800, 8) for y in range(0, 450, 8)
                    if quieto.pixel(x, y) != fuerte.pixel(x, y))
    assert distintos > 30, f"{clave}: el audio casi no cambia el dibujo ({distintos})"


@pytest.mark.parametrize("clave", CLAVES)
def test_fluido_a_1080p(app, clave):
    w = escenarios.crear(clave)
    w.resize(1920, 1080)
    _avanzar(w, 3, [0.6] * 32)
    _render(w)                       # arma la caché
    t = time.perf_counter()
    for _ in range(15):
        _avanzar(w, 1, [0.6] * 32)
        _render(w)
    ms = (time.perf_counter() - t) / 15 * 1000
    assert ms < TOPE_MS, f"{clave}: {ms:.1f} ms por cuadro"


@pytest.mark.parametrize("clave", CLAVES)
def test_acento_y_reloj(app, clave):
    w = escenarios.crear(clave)
    w.resize(320, 180)
    w.poner_acento(QColor("#00FFAA"))
    w.show()
    assert w._timer.isActive()
    w.hide()
    assert not w._timer.isActive()
