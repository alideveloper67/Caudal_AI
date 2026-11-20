# -*- coding: utf-8 -*-
"""Pruebas de la barra mini de la escena (descargador/ui/escena/barra.py)."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.barra import ANCHO, ALTO, BarraMini  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _clic(widget, punto):
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(int(punto.x()), int(punto.y())))


def _renderizar(widget):
    img = QImage(widget.width(), widget.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    widget.render(p, QPoint(0, 0))
    p.end()
    return img


@pytest.mark.parametrize("boton,senal", [
    ("anterior", "anterior"),
    ("alternar", "alternar"),
    ("siguiente", "siguiente"),
    ("aleatorio", "aleatorio"),
    ("repetir", "repetir"),
    ("fondo", "cambiar_fondo"),
    ("abrir", "abrir_caudal"),
    ("salir", "salir"),
])
def test_clic_en_centro_de_boton_emite_su_senal(app, boton, senal):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    recibidas = []
    getattr(w, senal).connect(lambda: recibidas.append(senal))
    _clic(w, w.rect_boton(boton).center())
    assert recibidas == [senal]


def test_clic_al_25_por_ciento_del_progreso_emite_0_25(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    fracciones = []
    w.buscar_pos.connect(fracciones.append)
    r = w.rect_progreso()
    _clic(w, QPoint(int(r.left() + r.width() * 0.25), int(r.center().y())))
    assert fracciones, "no se emitió buscar_pos"
    assert abs(fracciones[-1] - 0.25) < 0.01


def test_arrastre_en_progreso_emite_fracciones_crecientes(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    fracciones = []
    w.buscar_pos.connect(fracciones.append)
    r = w.rect_progreso()
    y = int(r.center().y())
    QTest.mousePress(w, Qt.LeftButton, Qt.NoModifier, QPoint(int(r.left() + r.width() * 0.1), y))
    QTest.mouseMove(w, QPoint(int(r.left() + r.width() * 0.6), y))
    QTest.mouseRelease(w, Qt.LeftButton, Qt.NoModifier, QPoint(int(r.left() + r.width() * 0.6), y))
    assert len(fracciones) >= 2
    assert fracciones == sorted(fracciones)
    assert abs(fracciones[-1] - 0.6) < 0.02


def test_poner_none_muestra_estado_vacio_sin_errores(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.poner(None)
    w.fijar_progreso(0, 0)
    img = _renderizar(w)
    assert not img.isNull()
    assert w._pista is None


def test_cargando_arranca_la_animacion_y_sonando_la_para(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    w.fijar_estado("cargando")
    assert w._timer.isActive()
    w.fijar_estado("sonando")
    assert not w._timer.isActive()


def test_cargando_sin_verse_no_arranca_el_timer(app):
    w = BarraMini()
    w.fijar_estado("cargando")
    assert not w._timer.isActive()


def test_ocultar_la_barra_para_el_timer(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    w.fijar_estado("cargando")
    assert w._timer.isActive()
    w.hide()
    assert not w._timer.isActive()


def test_render_con_pista_portada_y_progreso_sin_errores(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.poner({"titulo": "Una canción con un título bastante largo para probar el elidido", "artista": "Artista Ejemplo"})
    portada = QImage(300, 200, QImage.Format_ARGB32)
    portada.fill(QColor(200, 80, 140))
    w.poner_portada(portada)
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.fijar_progreso(83, 225)
    w.fijar_estado("sonando")
    w.fijar_aleatorio(True)
    w.fijar_repetir("una")
    w.fijar_fondo("ambiente")
    assert not _renderizar(w).isNull()


def test_render_de_todos_los_estados_sin_errores(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.poner({"titulo": "Tema", "artista": ""})
    for estado in ("sonando", "pausa", "cargando", "parado"):
        for modo in ("no", "todo", "una"):
            w.fijar_estado(estado)
            w.fijar_repetir(modo)
            assert not _renderizar(w).isNull()
    w.fijar_estado("parado")


def test_tamano_sugerido_es_698_por_92(app):
    w = BarraMini()
    assert w.sizeHint().width() == 698
    assert w.sizeHint().height() == 92


def test_rect_boton_nombre_invalido_falla(app):
    w = BarraMini()
    with pytest.raises(KeyError):
        w.rect_boton("no_existe")


def test_boton_buscar_no_vacio_ni_solapado(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    r = w.rect_boton("buscar")
    assert not r.isEmpty()
    for otro in ("anterior", "alternar", "siguiente", "aleatorio", "repetir",
                 "fondo", "abrir", "salir"):
        assert not r.intersects(w.rect_boton(otro)), f"«buscar» se solapa con «{otro}»"


def test_clic_en_buscar_emite_pidio_buscar_una_vez_y_ninguna_otra(app):
    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.show()
    recibidas = []
    for nombre in ("anterior", "alternar", "siguiente", "aleatorio", "repetir",
                   "cambiar_fondo", "abrir_caudal", "salir", "pidio_buscar"):
        getattr(w, nombre).connect(lambda nombre=nombre: recibidas.append(nombre))
    w.buscar_pos.connect(lambda f: recibidas.append("buscar_pos"))
    _clic(w, w.rect_boton("buscar").center())
    assert recibidas == ["pidio_buscar"]
