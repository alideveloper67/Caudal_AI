# -*- coding: utf-8 -*-
"""Pruebas de la sección «Según lo que suena» de la lista «Seguir escuchando». El cargador
de miniaturas es falso y síncrono: nunca se baja nada de la red."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.lista_reciente import ListaSeguir


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _pistas(n):
    return [{"titulo": f"Tema {i}", "artista": f"Artista {i}",
             "miniatura": f"https://img.test/{i}.jpg", "video_id": f"v{i}"} for i in range(n)]


def _recomendadas(n):
    return [{"titulo": f"Sugerida {i}", "artistas": [f"Banda {i}"],
             "miniatura": f"https://img.test/rec{i}.jpg", "video_id": f"r{i}"} for i in range(n)]


def _cargador_falso(llamadas):
    def cargador(url, callback):
        llamadas.append(url)
        img = QImage(72, 72, QImage.Format_ARGB32)
        img.fill(QColor(200, 60, 120))
        callback(img)
    return cargador


def _lista(n=5, mostrar=True):
    w = ListaSeguir()
    w.resize(w.sizeHint())
    llamadas = []
    w.fijar_cargador(_cargador_falso(llamadas))
    w.poner(_pistas(n))
    if mostrar:
        w.show()
        QTest.qWait(20)
    return w, llamadas


def _render(w):
    img = QImage(w.sizeHint(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    w.render(img)
    return img


def test_clic_en_recomendada_emite_esa_pista(app):
    w, _ = _lista(3)
    w.poner_recomendadas(_recomendadas(4))
    recibidas = []
    w.elegida.connect(recibidas.append)
    centro = w.rect_fila_recomendada(1).center().toPoint()
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centro)
    assert recibidas == [_recomendadas(4)[1]]


def test_clic_en_reciente_sigue_emitiendo_la_reciente(app):
    w, _ = _lista(3)
    w.poner_recomendadas(_recomendadas(4))
    recibidas = []
    w.elegida.connect(recibidas.append)
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, w.rect_fila(0).center().toPoint())
    assert recibidas == [_pistas(3)[0]]


def test_sin_recomendadas_no_se_pinta_el_encabezado(app):
    w, _ = _lista(3)
    _render(w)                       # calentamiento: carga las miniaturas
    sin_seccion = _render(w)
    w.poner_recomendadas([])
    assert _render(w) == sin_seccion
    w.poner_recomendadas(_recomendadas(2))
    assert _render(w) != sin_seccion


def test_recomendadas_cargan_miniaturas_con_el_mismo_cargador(app):
    w, llamadas = _lista(2)
    w.poner_recomendadas(_recomendadas(2))
    _render(w)
    assert "https://img.test/rec0.jpg" in llamadas
    assert w._miniaturas["https://img.test/rec0.jpg"] is not None


def test_maximo_del_desplazamiento_crece_con_recomendadas(app):
    w, _ = _lista(30)
    antes = w._max_desp()
    w.poner_recomendadas(_recomendadas(4))
    assert w._max_desp() > antes


def test_rueda_lleva_la_seccion_recomendada_a_la_vista(app):
    w, _ = _lista(30)
    w.poner_recomendadas(_recomendadas(4))
    for _ in range(60):
        evento = QWheelEvent(QPointF(100, 200), QPointF(100, 200), QPoint(0, 0), QPoint(0, -120),
                             Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(w, evento)
    QTest.qWait(1000)
    ultima = w.rect_fila_recomendada(3)
    assert ultima.bottom() <= w._zona_filas().bottom() + 0.5
    assert ultima.top() >= w._zona_filas().top() - 0.5


def test_fijar_cargando_recomendadas_no_rompe_el_render(app):
    w, _ = _lista(3)
    _render(w)                       # calentamiento
    base = _render(w)
    w.fijar_cargando_recomendadas(True)
    QTest.qWait(150)
    con_fantasmas = _render(w)
    assert not con_fantasmas.isNull()
    assert con_fantasmas != base
    w.fijar_cargando_recomendadas(False)
    assert _render(w) == base


def test_fantasmas_no_aparecen_si_ya_hay_recomendadas(app):
    w, _ = _lista(3)
    w.fijar_cargando_recomendadas(True)
    w.poner_recomendadas(_recomendadas(2))
    assert not w._mostrar_fantasmas()
    assert w._filas_rec() == 2
