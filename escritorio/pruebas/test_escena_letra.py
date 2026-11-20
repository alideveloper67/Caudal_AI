# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.letra import (LetraCinetica, indice_en, palabra_fuerte,
                                         repartir_palabras)

LINEAS = [
    {"ms": 1000, "texto": "hola mundo", "pausa": False, "canto": 1200},
    {"ms": 3000, "texto": "", "pausa": True, "hasta": 4000},
    {"ms": 5000, "texto": "uno dos tres", "pausa": False},
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _render(widget):
    img = QImage(widget.width(), widget.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    widget.render(img)
    return img


def _pixeles_pintados(img):
    return sum(1 for y in range(img.height()) for x in range(0, img.width(), 3)
               if img.pixelColor(x, y).alpha() > 0)


def test_indice_en_antes_de_empezar():
    assert indice_en(LINEAS, 500) == -1
    assert indice_en([], 100) == -1
    assert indice_en(LINEAS, None) == -1


def test_indice_en_en_medio():
    assert indice_en(LINEAS, 1000) == 0
    assert indice_en(LINEAS, 3500) == 1


def test_indice_en_al_final():
    assert indice_en(LINEAS, 5000) == 2
    assert indice_en(LINEAS, 999999) == 2


def test_indice_en_sin_sincronizar():
    sin_ms = [{"ms": None, "texto": "a", "pausa": False}, {"ms": None, "texto": "b", "pausa": False}]
    assert indice_en(sin_ms, 10000) == -1


def test_repartir_primera_en_inicio():
    r = repartir_palabras("uno dos tres", 1000, 1800)
    assert [p for p, _ in r] == ["uno", "dos", "tres"]
    assert r[0][1] == 1000


def test_repartir_monotona_y_ultimo_menor_que_fin():
    r = repartir_palabras("cae la noche sobre la ciudad entera", 2000, 2400)
    tiempos = [ms for _, ms in r]
    assert all(a <= b for a, b in zip(tiempos, tiempos[1:]))
    assert tiempos[-1] < 2000 + 2400


def test_repartir_canto_por_defecto_1800():
    assert repartir_palabras("a b", 0) == [("a", 0), ("b", 900)]
    assert repartir_palabras("a b", 0, 0) == [("a", 0), ("b", 900)]
    assert repartir_palabras("", 0, 1000) == []


def test_palabra_fuerte_la_mas_larga_y_empate_a_la_ultima():
    assert palabra_fuerte(["sol", "estrella", "luna"]) == 1
    assert palabra_fuerte(["abc", "xyz"]) == 1
    assert palabra_fuerte([]) == -1
    assert palabra_fuerte(repartir_palabras("a bbbb cc", 0, 1000)) == 1


def test_render_lista_vacia_no_pinta_nada(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas([], True)
    w.fijar_ms(5000)
    assert w.indice_actual() == -1
    assert _pixeles_pintados(_render(w)) == 0


def test_render_linea_larguisima(app):
    texto = " ".join(f"palabra{i}" for i in range(60))
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas([{"ms": 0, "texto": texto, "pausa": False, "canto": 2000}], True)
    w.fijar_ms(2000)
    assert w.indice_actual() == 0
    assert _pixeles_pintados(_render(w)) > 0


def test_render_pausa(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.poner_lineas(LINEAS, True)
    w.fijar_ms(3500)
    assert w.indice_actual() == 1
    assert _pixeles_pintados(_render(w)) > 0


def test_render_sin_sincronizar(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas([{"ms": None, "texto": f"verso {i}", "pausa": False} for i in range(8)], False)
    w.fijar_ms(4000)
    assert w.indice_actual() == -1
    assert _pixeles_pintados(_render(w)) > 0


def test_render_mensaje_sin_letra(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas(LINEAS, True)
    w.fijar_ms(1500)
    w.poner_mensaje("Cargando letra…")
    assert _pixeles_pintados(_render(w)) > 0
    w.poner_mensaje("")
    assert w.indice_actual() == 0


def test_linea_de_60_palabras_no_sale_del_rectangulo(app):
    from PySide6.QtCore import QRectF
    texto = " ".join(f"palabra{i}" for i in range(60))
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas([{"ms": 0, "texto": texto, "pausa": False, "canto": 6000}], True)
    marco = QRectF(0, 0, 620, 420)
    ef = w._efectivas()
    assert len(ef) > 1                                   # tuvo que partirse en trozos
    assert sum(len(e["texto"].split()) for e in ef) == 60
    for k in range(len(ef)):
        disp = w._disposicion(k)
        assert len({round(it.rect.top()) for it in disp.items}) <= 4
        for it in disp.items:
            assert marco.contains(it.rect)
    for ms in range(0, 6001, 50):                        # en ningún instante se sale
        w.fijar_ms(ms)
        if w._indice >= 0:
            for it in w._disposicion(w._indice).items:
                assert marco.contains(it.rect)
    assert w.indice_actual() == 0


def test_linea_siguiente_vacia_o_pausa_no_pinta_nada(app):
    def banda_inferior_vacia(lineas):
        w = LetraCinetica()
        w.resize(620, 420)
        w.poner_lineas(lineas, True)
        w.fijar_ms(500)
        assert w.indice_actual() == 0
        img = _render(w)
        # franja donde va la línea siguiente (fuente(15), alto 24, a PAD del borde inferior)
        return sum(1 for y in range(420 - 28 - 24, 420 - 28) for x in range(620)
                   if img.pixelColor(x, y).alpha() > 0)

    actual = [{"ms": 0, "texto": "uno dos", "pausa": False, "canto": 1000}]
    assert banda_inferior_vacia(actual + [{"ms": 3000, "texto": "", "pausa": False}]) == 0
    assert banda_inferior_vacia(actual + [{"ms": 3000, "texto": "", "pausa": True}]) == 0


def test_fijar_ms_solo_actualiza_si_algo_cambia(app):
    w = LetraCinetica()
    w.resize(620, 420)
    w.poner_lineas(LINEAS, True)
    llamadas = []
    w.update = lambda *a: llamadas.append(1)
    w.fijar_ms(500)                       # sigue antes de la primera línea: nada cambia
    assert llamadas == []
    w.fijar_ms(1500)                     # entra la línea 0 y su primera palabra
    assert len(llamadas) == 1
    w.fijar_ms(1520)                     # la segunda palabra aún no llega (entra en 1533): nada cambia
    assert len(llamadas) == 1
    w.fijar_ms(1600)                     # llega la segunda palabra
    assert len(llamadas) == 2
