# -*- coding: utf-8 -*-
"""Traducción bajo la línea de la letra animada: cuándo se dibuja, que no se salga del widget,
que una letra nueva la borra y que la lista de largo distinto se ignora."""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.letra import LetraCinetica

LINEAS = [
    {"ms": 1000, "texto": "hola mundo", "pausa": False, "canto": 1200},
    {"ms": 3000, "texto": "", "pausa": True, "hasta": 4000},
    {"ms": 5000, "texto": "uno dos tres", "pausa": False},
]
TRADUCCIONES = ["hello world", None, "one two three"]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _render(widget):
    img = QImage(widget.width(), widget.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    widget.render(img)
    return img


def _asentar(widget):
    """Da por terminadas las entradas de palabras y el fundido, para renderizar un estado fijo."""
    widget._t_linea -= 5.0
    for k in list(widget._entradas):
        widget._entradas[k] -= 5.0


def _claros_debajo(img, y0):
    """Píxeles visibles y claros por debajo de la fila y0."""
    return sum(1 for y in range(int(y0), img.height()) for x in range(img.width())
               if img.pixelColor(x, y).alpha() > 60 and img.pixelColor(x, y).lightness() > 150)


def _letra(lineas=LINEAS, traducciones=None, ms=1500):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas(lineas, True)
    if traducciones is not None:
        w.fijar_traducciones(traducciones)
    w.fijar_ms(ms)
    _asentar(w)
    return w


def _bajo_del_bloque(w):
    """Fila donde acaba el bloque principal sin desplazar (con un margen de 2 px)."""
    disp = w._disposicion(w._indice)
    return max(it.rect.bottom() for it in disp.items) + 2


def test_con_traduccion_hay_pixeles_claros_debajo_del_bloque(app):
    sin = _letra()
    y0 = _bajo_del_bloque(sin)
    assert _claros_debajo(_render(sin), y0) == 0

    con = _letra(traducciones=TRADUCCIONES)
    assert con.indice_actual() == 0
    assert _claros_debajo(_render(con), y0) > 0


def test_lista_de_largo_distinto_no_dibuja_nada_extra(app):
    w = _letra(traducciones=["solo una"])
    assert w._traduccion_actual() is None
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) == 0


def test_fijar_traducciones_none_o_vacia_quita_todas(app):
    w = _letra(traducciones=TRADUCCIONES)
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) > 0
    w.fijar_traducciones(None)
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) == 0
    w.fijar_traducciones(TRADUCCIONES)
    w.fijar_traducciones([])
    assert w._traduccion_actual() is None
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) == 0


def test_poner_letra_nueva_borra_las_traducciones(app):
    w = _letra(traducciones=TRADUCCIONES)
    assert w._traduccion_actual() == "hello world"
    w.poner_lineas([{"ms": 0, "texto": "otra linea", "pausa": False, "canto": 1000}], True)
    assert w._trad == []
    w.fijar_ms(500)
    _asentar(w)
    assert w._traduccion_actual() is None
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) == 0


def test_traduccion_sin_letra_no_rompe(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.fijar_traducciones(["algo"])
    w.fijar_ms(1500)
    _render(w)
    assert w._traduccion_actual() is None
    w.poner_lineas(LINEAS, True)
    w.fijar_ms(1500)
    assert w._traduccion_actual() is None         # las que llegaron antes se descartaron


def test_fijar_none_con_letra_no_rompe(app):
    w = _letra(traducciones=None)
    w.fijar_traducciones(None)
    w.fijar_ms(1500)
    _render(w)
    assert w.indice_actual() == 0


def test_linea_sin_traduccion_y_pausa_no_muestran_nada(app):
    w = _letra(traducciones=["hello world", None, None])
    w.fijar_ms(3500)                              # pausa
    assert w.indice_actual() == 1
    assert w._traduccion_actual() is None
    w.fijar_ms(5500)                              # línea 2 sin traducción
    assert w._traduccion_actual() is None


def test_traduccion_larga_se_recorta_y_no_sale_del_widget(app):
    largo = " ".join(f"palabra{i}" for i in range(80))
    w = _letra(traducciones=[largo, None, None])
    disp = w._disposicion(w._indice)
    capa = w._capa_traduccion(disp)
    assert capa is not None
    _, texto, _, rect = capa
    assert texto.endswith("…")
    marco = QRectF(0, 0, w.width(), w.height())
    assert marco.contains(rect)
    assert _claros_debajo(_render(w), _bajo_del_bloque(w)) > 0


def _alfa_maximo_debajo(img, y0):
    return max((img.pixelColor(x, y).alpha() for y in range(int(y0), img.height())
                for x in range(img.width())), default=0)


def test_fundido_de_la_traduccion_al_cambiar_de_linea(app):
    w = _letra(traducciones=TRADUCCIONES)
    y0 = _bajo_del_bloque(w)
    # justo al cambiar de línea el texto está invisible; a mitad del fundido, más tenue que al final
    w._t_linea = time.monotonic() + 1.0          # reloj en el futuro: fundido exactamente 0
    al_inicio = _alfa_maximo_debajo(_render(w), y0)
    w._t_linea = time.monotonic() - 0.15
    a_mitad = _alfa_maximo_debajo(_render(w), y0)
    w._t_linea = time.monotonic() - 5.0
    al_final = _alfa_maximo_debajo(_render(w), y0)
    assert al_inicio == 0
    assert 0 < a_mitad < al_final
