# -*- coding: utf-8 -*-
"""Pruebas de la pieza «fondo» de la escena (FondoAmbiente)."""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.estilo import BRILLO, DOMINANTE, SEGUNDO
from descargador.ui.escena.fondo import DURACION_FUNDIDO, INTERVALO_MS, FondoAmbiente


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _imagen_color(color, w=800, h=600):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(color))
    return img


def _reloj(inicio=100.0):
    """Reloj falso: `reloj[0]` es el instante actual."""
    reloj = [inicio]
    return reloj, (lambda: reloj[0])


def _render(widget, w, h):
    destino = QImage(w, h, QImage.Format_ARGB32)
    widget.render(destino)
    return destino


def test_es_opaco_y_usa_time_monotonic_por_defecto(app):
    w = FondoAmbiente()
    assert w.testAttribute(Qt.WA_OpaquePaintEvent)
    assert FondoAmbiente()._monotonic is time.monotonic


def test_poner_portada_color_pinta_la_carátula(app):
    w = FondoAmbiente()
    w.resize(640, 360)
    reloj, fake = _reloj()
    w._monotonic = fake
    w.poner_portada(_imagen_color(QColor(230, 20, 20)))
    w.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
    reloj[0] += 5.0          # fundido terminado
    img = _render(w, 640, 360)
    assert w._base is not None
    assert w._base.width() == round(640 * 1.18)
    assert w._base.height() == round(360 * 1.18)
    c = img.pixelColor(320, 180)
    assert c.red() > c.green() + 50      # se ve el rojo de la carátula, oscurecido


def test_el_fundido_termina_con_el_reloj_inyectado(app):
    w = FondoAmbiente()
    w.resize(320, 200)
    reloj, fake = _reloj()
    w._monotonic = fake
    w.poner_portada(_imagen_color(QColor(10, 200, 40), 300, 200))
    assert w._fundiendo is True
    reloj[0] += DURACION_FUNDIDO / 2
    w._tic()
    assert w._fundiendo is True
    reloj[0] += DURACION_FUNDIDO
    w._tic()
    assert w._fundiendo is False
    assert w._base_viejo is None


def test_render_sin_errores_en_1920x1080_y_300x200(app):
    w = FondoAmbiente()
    reloj, fake = _reloj()
    w._monotonic = fake
    for tam in ((1920, 1080), (300, 200)):
        w.resize(*tam)
        w.poner_portada(_imagen_color(QColor(40, 120, 230), 500, 500))
        w.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
        reloj[0] += 5.0
        img = _render(w, *tam)
        assert not img.isNull()
        assert (img.width(), img.height()) == tam


def test_sin_portada_pinta_degradado_no_negro(app):
    w = FondoAmbiente()
    w.resize(400, 300)
    w.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
    w.poner_portada(None)
    reloj, fake = _reloj()
    w._monotonic = fake
    reloj[0] += 5.0
    img = _render(w, 400, 300)
    c = img.pixelColor(200, 150)
    assert (c.red(), c.green(), c.blue()) != (0, 0, 0)
    assert c.red() + c.green() + c.blue() > 30
    assert w._base is None


def test_fijar_movimiento_false_para_el_timer(app):
    w = FondoAmbiente()
    w.resize(320, 200)
    w.show()
    app.processEvents()
    try:
        w.fijar_movimiento(True)
        assert w._timer.isActive()
        assert w._timer.interval() == INTERVALO_MS
        w.fijar_movimiento(False)
        assert not w._timer.isActive()
        w.fijar_movimiento(True)
        assert w._timer.isActive()
    finally:
        w.hide()
    assert not w._timer.isActive()


def test_sin_timer_si_no_se_ve(app):
    w = FondoAmbiente()
    w.resize(320, 200)
    w.fijar_movimiento(True)          # nunca mostrado: no debe arrancar el timer
    assert not w._timer.isActive()


def test_rendimiento_1920x1080_menos_de_40_ms(app):
    w = FondoAmbiente()
    w.resize(1920, 1080)
    reloj, fake = _reloj()
    w._monotonic = fake
    # carátula de ejemplo: círculos de colores
    portada = QImage(900, 900, QImage.Format_ARGB32)
    portada.fill(QColor(20, 20, 30))
    p = QPainter(portada)
    p.setRenderHint(QPainter.Antialiasing, True)
    for i, c in enumerate(("#E8577E", "#3B9BE8", "#F2C14E", "#5ED39B")):
        p.setBrush(QColor(c))
        p.setPen(Qt.NoPen)
        p.drawEllipse(60 + i * 180, 60 + (i % 2) * 300, 320, 320)
    p.end()
    w.poner_portada(portada)
    w.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
    reloj[0] += 5.0                   # fundido terminado y preparación hecha
    destino = QImage(1920, 1080, QImage.Format_ARGB32)
    w.render(destino)
    tiempos = []
    for _ in range(10):
        t0 = time.perf_counter()
        w.render(destino)
        tiempos.append((time.perf_counter() - t0) * 1000.0)
    promedio = sum(tiempos) / len(tiempos)
    print(f"\nrender 1920x1080: promedio {promedio:.1f} ms")
    assert promedio < 40, f"render promedio {promedio:.1f} ms (límite 40 ms)"
