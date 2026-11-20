# -*- coding: utf-8 -*-
"""Pruebas de la lista «Seguir escuchando». El cargador de miniaturas es falso y síncrono:
nunca se baja nada de la red."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QPoint, QPointF, QSize, Qt
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


def test_tamano_sugerido(app):
    w = ListaSeguir()
    assert w.sizeHint() == QSize(290, 560)


def test_clic_en_fila_emite_la_pista_correcta(app):
    w, _ = _lista(5)
    recibidas = []
    w.elegida.connect(recibidas.append)
    centro = w.rect_fila(1).center().toPoint()
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centro)
    assert recibidas == [_pistas(5)[1]]


def test_marcar_actual_se_guarda_y_activa_el_ecualizador(app):
    w, _ = _lista(5)
    w.marcar_actual("v2")
    assert w._clave_actual == "v2"
    assert w._fila_actual_visible()
    assert w._tmr_eq.isActive()
    w.marcar_actual(None)
    assert w._clave_actual is None
    assert not w._tmr_eq.isActive()


def test_clave_usa_clave_o_video_id(app):
    w = ListaSeguir()
    w.poner([{"titulo": "A", "artista": "x", "miniatura": "", "clave": "abc"}])
    w.marcar_actual("abc")
    assert w._es_actual(w._pistas[0])


def test_cargador_recibe_la_url_de_la_miniatura(app):
    w, llamadas = _lista(3)
    _render(w)
    assert "https://img.test/0.jpg" in llamadas
    assert w._miniaturas["https://img.test/0.jpg"] is not None


def test_lista_vacia_se_pinta(app):
    w = ListaSeguir()
    img = _render(w)
    assert not img.isNull()
    assert w.rect_fila(0).top() > 0


def test_rueda_desplaza_y_cambia_rect_fila(app):
    w, _ = _lista(25)
    w.show()
    QTest.qWait(20)
    antes = w.rect_fila(0).top()
    evento = QWheelEvent(QPointF(100, 200), QPointF(100, 200), QPoint(0, 0), QPoint(0, -120),
                         Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(w, evento)
    QTest.qWait(600)
    assert w._desp > 0
    assert w.rect_fila(0).top() < antes


def test_maximo_30_pistas(app):
    w = ListaSeguir()
    w.poner(_pistas(40))
    assert len(w._pistas) == 30


def test_render_con_25_pistas_sin_errores(app):
    w, _ = _lista(25)
    w.marcar_actual("v3")
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    img = _render(w)
    assert not img.isNull()
    assert img.size() == w.sizeHint()


def test_clic_fuera_de_filas_no_emite(app):
    w, _ = _lista(2)
    recibidas = []
    w.elegida.connect(recibidas.append)
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, QPoint(145, 20))
    assert recibidas == []
