# -*- coding: utf-8 -*-
"""Pruebas de la pieza «fondo synthwave» de la escena (FondoSynthwave)."""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.fondo_synthwave import (COLOR_ACENTO, FondoSynthwave, HORIZONTE,
                                                   _yh)

UMBRAL_MS = 8.0          # tiempo medio máximo por cuadro a 1920x1080


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _fondo(w=1280, h=720, inicio=100.0):
    """Widget con reloj falso: `reloj[0]` es el instante actual."""
    f = FondoSynthwave()
    reloj = [inicio]
    f._monotonic = lambda: reloj[0]
    f._t = inicio
    f._acento_t0 = inicio
    f.resize(w, h)
    return f, reloj


def _render(f, w, h):
    img = QImage(w, h, QImage.Format_ARGB32)
    f.render(img)
    return img


def _brillo(c):
    return c.red() + c.green() + c.blue()


def _avanzar_cuadros(f, reloj, n):
    """Simula `n` cuadros a 30 FPS con el reloj falso."""
    for _ in range(n):
        reloj[0] += 1.0 / 30.0
        f._avanzar(reloj[0])


def test_render_sin_errores(app):
    f, _ = _fondo()
    img = _render(f, 1280, 720)
    assert not img.isNull()
    assert (img.width(), img.height()) == (1280, 720)


def test_horizonte_mas_brillante_que_cielo_alto(app):
    f, _ = _fondo(1280, 720)
    img = _render(f, 1280, 720)
    fila = _yh(720)
    assert fila == round(720 * HORIZONTE)
    assert _brillo(img.pixelColor(640, fila)) > _brillo(img.pixelColor(640, 10))


@pytest.mark.parametrize("valores", [[], [0.5] * 64, [1.0] * 7])
def test_fijar_espectro_no_rompe(app, valores):
    f, reloj = _fondo()
    f.fijar_espectro(valores)
    _avanzar_cuadros(f, reloj, 5)
    img = _render(f, 1280, 720)
    assert not img.isNull()


def _brillantes_sobre_horizonte(img, h):
    """Píxeles brillantes en la franja donde la cordillera alta dibuja su silueta."""
    yh = _yh(h)
    alto = 0.18 * yh
    n = 0
    for y in range(int(yh - alto - 2), int(yh - 30)):
        for x in range(0, img.width(), 2):
            if _brillo(img.pixelColor(x, y)) > 270:
                n += 1
    return n


def test_espectro_alto_mas_brillante_que_vacio(app):
    vacio, reloj_v = _fondo(1280, 720)
    vacio.fijar_espectro([])
    _avanzar_cuadros(vacio, reloj_v, 20)

    alto, reloj_a = _fondo(1280, 720)
    alto.fijar_espectro([1.0] * 16)
    _avanzar_cuadros(alto, reloj_a, 20)

    n_vacio = _brillantes_sobre_horizonte(_render(vacio, 1280, 720), 720)
    n_alto = _brillantes_sobre_horizonte(_render(alto, 1280, 720), 720)
    assert n_alto > n_vacio + 500, (n_alto, n_vacio)


def test_poner_acento_cambia_color_en_1s(app):
    f, reloj = _fondo()
    assert f._color_actual().name().upper() == COLOR_ACENTO.upper()

    objetivo = QColor("#00FFAA")
    f.poner_acento(objetivo)
    _avanzar_cuadros(f, reloj, 12)                       # 0.4 s: a medio camino
    medio = f._color_actual()
    assert medio.name().upper() not in (COLOR_ACENTO.upper(), objetivo.name().upper())

    reloj[0] += 0.6                                      # ya pasó 1 s desde el cambio
    f._avanzar(reloj[0])
    assert f._color_actual().name().upper() == objetivo.name().upper()


def test_tiempo_por_cuadro_1080p(app):
    f = FondoSynthwave()
    f.resize(1920, 1080)
    img = QImage(1920, 1080, QImage.Format_ARGB32)
    for i in range(3):                                   # calentamiento y caché del cielo
        f._avanzar(100.0 + i / 30.0)
        f.render(img)
    tiempos = []
    for i in range(30):
        f._avanzar(100.1 + i / 30.0)
        inicio = time.perf_counter()
        f.render(img)
        tiempos.append((time.perf_counter() - inicio) * 1000.0)
    media = sum(tiempos) / len(tiempos)
    assert media < UMBRAL_MS, f"media {media:.2f} ms por cuadro"


def test_timer_parado_tras_hide(app):
    f = FondoSynthwave()
    f.resize(640, 360)
    f.show()
    assert f._timer.isActive()
    f.hide()
    assert not f._timer.isActive()
    f.deleteLater()
