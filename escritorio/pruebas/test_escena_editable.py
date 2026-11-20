# -*- coding: utf-8 -*-
"""Piezas editables de la escena: mover, redimensionar, escalar con Ctrl+rueda, ocultar,
y el estado como fracciones de la pantalla (ida y vuelta)."""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from descargador.ui.escena import editable  # noqa: E402
from descargador.ui.escena.editable import PiezaEditable, activar_edicion, edicion_activa  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def edicion_apagada():
    activar_edicion(False)
    yield
    activar_edicion(False)


@pytest.fixture
def ventana(app):
    w = QWidget()
    w.setWindowFlags(Qt.FramelessWindowHint)
    w.resize(300, 200)
    w.move(100, 100)
    w.show()
    app.processEvents()
    yield w
    w.hide()
    w.deleteLater()
    app.processEvents()


def _raton(widget, tipo, pos, boton=Qt.LeftButton, botones=Qt.LeftButton, mods=Qt.NoModifier):
    """Envía un evento de ratón a `widget` con la posición local `pos`."""
    glob = QPointF(widget.mapToGlobal(pos))
    ev = QMouseEvent(tipo, QPointF(pos), glob, boton, botones, mods)
    QApplication.sendEvent(widget, ev)


def _arrastrar(widget, desde, hasta, mods=Qt.NoModifier, soltar=True):
    _raton(widget, QEvent.MouseButtonPress, desde, mods=mods)
    _raton(widget, QEvent.MouseMove, hasta, mods=mods)
    if soltar:
        _raton(widget, QEvent.MouseButtonRelease, hasta, botones=Qt.NoButton, mods=mods)


def _rueda(widget, dy):
    pos = QPointF(10, 10)
    ev = QWheelEvent(pos, QPointF(widget.mapToGlobal(QPoint(10, 10))), QPoint(0, 0),
                     QPoint(0, dy), Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, ev)


def test_mover_con_edicion(ventana):
    p = PiezaEditable(ventana, "fondo")
    activar_edicion(True)
    assert edicion_activa() is True
    antes = ventana.pos()
    _arrastrar(ventana, QPoint(50, 50), QPoint(80, 70))
    assert ventana.pos() == antes + QPoint(30, 20)
    assert p.estado()["visible"] is True


def test_mover_muestra_cursor_de_mover(ventana):
    PiezaEditable(ventana, "fondo")
    activar_edicion(True)
    _raton(ventana, QEvent.MouseButtonPress, QPoint(50, 50))
    assert ventana.cursor().shape() == Qt.SizeAllCursor
    _raton(ventana, QEvent.MouseMove, QPoint(60, 60))
    _raton(ventana, QEvent.MouseButtonRelease, QPoint(60, 60), botones=Qt.NoButton)
    assert ventana.cursor().shape() != Qt.SizeAllCursor


def test_sin_edicion_y_sin_alt_no_mueve(ventana):
    PiezaEditable(ventana, "fondo")
    antes = ventana.pos()
    _arrastrar(ventana, QPoint(50, 50), QPoint(90, 90))
    assert ventana.pos() == antes


def test_alt_mueve_sin_edicion(ventana):
    PiezaEditable(ventana, "fondo")
    antes = ventana.pos()
    _arrastrar(ventana, QPoint(50, 50), QPoint(70, 60), mods=Qt.AltModifier)
    assert ventana.pos() == antes + QPoint(20, 10)


def test_asa_no_aparece_sin_edicion_y_si_con_edicion(ventana):
    p = PiezaEditable(ventana, "fondo")
    assert not p._boton.isVisible()
    assert not p._asa.isVisible()
    activar_edicion(True)
    assert p._boton.isVisible()
    assert p._asa.isVisible()


def test_redimensionar_desde_la_esquina(ventana):
    PiezaEditable(ventana, "fondo")
    activar_edicion(True)
    w, h = ventana.width(), ventana.height()
    _raton(ventana, QEvent.MouseMove, QPoint(w - 5, h - 5), botones=Qt.NoButton)
    assert ventana.cursor().shape() == Qt.SizeFDiagCursor
    _arrastrar(ventana, QPoint(w - 5, h - 5), QPoint(w + 45, h + 25))
    assert (ventana.width(), ventana.height()) == (w + 50, h + 30)


def test_redimensionar_desde_el_asa_hija(ventana):
    p = PiezaEditable(ventana, "fondo")
    activar_edicion(True)
    w, h = ventana.width(), ventana.height()
    # la press llega al asa (hija) y se propaga a la pieza, que es quien redimensiona
    centro_asa = QPoint(p._asa.width() // 2, p._asa.height() // 2)
    glob = QPointF(p._asa.mapToGlobal(centro_asa))
    QApplication.sendEvent(p._asa, QMouseEvent(QEvent.MouseButtonPress, QPointF(centro_asa), glob,
                                               Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    # el asa está centrada en (w-9, h-9): desplazarla 20x10 deja el widget en (w+20, h+10)
    origen = QPoint(w - 9, h - 9)
    _raton(ventana, QEvent.MouseMove, origen + QPoint(20, 10))
    _raton(ventana, QEvent.MouseButtonRelease, origen + QPoint(20, 10), botones=Qt.NoButton)
    assert (ventana.width(), ventana.height()) == (w + 20, h + 10)


def test_redimensionar_respeta_minimo_y_pantalla(ventana):
    PiezaEditable(ventana, "fondo", minimo=(120, 60))
    activar_edicion(True)
    w, h = ventana.width(), ventana.height()
    _arrastrar(ventana, QPoint(w - 5, h - 5), QPoint(-400, -400))
    assert (ventana.width(), ventana.height()) == (120, 60)

    _arrastrar(ventana, QPoint(115, 55), QPoint(5000, 5000))
    pantalla = ventana.screen().geometry()
    assert ventana.width() <= pantalla.width()
    assert ventana.height() <= pantalla.height()


def test_ctrl_rueda_escala_y_limita(ventana):
    PiezaEditable(ventana, "fondo")
    bw, bh = ventana.width(), ventana.height()
    centro = ventana.geometry().center()

    _rueda(ventana, 120)
    assert abs(ventana.width() - round(bw * 1.1)) <= 1
    assert abs(ventana.height() - round(bh * 1.1)) <= 1
    c2 = ventana.geometry().center()
    assert abs(c2.x() - centro.x()) <= 1 and abs(c2.y() - centro.y()) <= 1

    for _ in range(20):
        _rueda(ventana, 120)
    assert ventana.width() == round(bw * 2.5)
    assert ventana.height() == round(bh * 2.5)

    for _ in range(40):
        _rueda(ventana, -120)
    assert ventana.width() == round(bw * 0.5)
    assert ventana.height() == round(bh * 0.5)


def test_ocultar_oculta_y_emite(ventana):
    p = PiezaEditable(ventana, "reloj")
    recibidos = []
    p.cambiado.connect(recibidos.append)
    p.ocultar()
    assert not ventana.isVisible()
    assert recibidos == ["reloj"]
    p.mostrar()
    assert ventana.isVisible()
    assert recibidos == ["reloj", "reloj"]


def test_boton_cerrar_oculta(ventana):
    p = PiezaEditable(ventana, "reloj")
    activar_edicion(True)
    p._boton.click()
    assert not ventana.isVisible()


def test_estado_y_aplicar_ida_y_vuelta(ventana):
    p = PiezaEditable(ventana, "fondo")
    ventana.move(120, 90)
    ventana.resize(260, 150)
    pantalla = ventana.screen().geometry()
    est = p.estado()
    assert set(est) == {"x", "y", "w", "h", "visible"}
    for k in ("x", "y", "w", "h"):
        assert 0.0 <= est[k] <= 1.0
    g0 = ventana.geometry()

    ventana.move(0, 0)
    ventana.resize(50, 50)
    p.aplicar(est, pantalla)
    g1 = ventana.geometry()
    assert abs(g1.x() - g0.x()) <= 2
    assert abs(g1.y() - g0.y()) <= 2
    assert abs(g1.width() - g0.width()) <= 2
    assert abs(g1.height() - g0.height()) <= 2


def test_aplicar_recorta_a_la_pantalla(ventana):
    p = PiezaEditable(ventana, "fondo")
    pantalla = QRect(0, 0, 800, 600)
    p.aplicar({"x": 0.99, "y": 0.99, "w": 0.5, "h": 0.5, "visible": True}, pantalla)
    g = ventana.geometry()
    assert g.x() >= 0 and g.y() >= 0
    assert g.x() + g.width() <= 800
    assert g.y() + g.height() <= 600


def test_aplicar_oculta_segun_visible(ventana):
    p = PiezaEditable(ventana, "fondo")
    p.aplicar({"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "visible": False}, QRect(0, 0, 800, 600))
    assert not ventana.isVisible()
    p.aplicar({"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "visible": True}, QRect(0, 0, 800, 600))
    assert ventana.isVisible()


@pytest.mark.parametrize("malo", [{}, None, {"x": 0.1}, {"x": "hola", "y": 0, "w": 1, "h": 1},
                                  {"x": float("nan"), "y": 0, "w": 1, "h": 1}])
def test_aplicar_malformado_no_rompe(ventana, malo):
    p = PiezaEditable(ventana, "fondo")
    antes = ventana.geometry()
    p.aplicar(malo, QRect(0, 0, 800, 600))
    assert ventana.geometry() == antes


def test_activar_edicion_muestra_y_oculta_boton(ventana):
    p = PiezaEditable(ventana, "fondo")
    assert not p._boton.isVisible()
    activar_edicion(True)
    assert p._boton.isVisible()
    activar_edicion(False)
    assert not p._boton.isVisible()


def test_todas_las_piezas_vivas_se_enteran(app):
    otra = QWidget()
    otra.show()
    w1 = QWidget()
    w1.show()
    p1 = PiezaEditable(w1, "uno")
    p2 = PiezaEditable(otra, "dos")
    activar_edicion(True)
    assert p1._boton.isVisible() and p2._boton.isVisible()
    activar_edicion(False)
    assert not p1._boton.isVisible() and not p2._boton.isVisible()
    otra.close()
    w1.close()


def test_widget_destruido_no_lanza(app):
    from shiboken6 import delete

    w = QWidget()
    p = PiezaEditable(w, "fantasma")
    delete(w)
    activar_edicion(True)
    activar_edicion(False)
    assert p.estado() == {}
    p.ocultar()
    p.mostrar()
    p.aplicar({"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3, "visible": True}, QRect(0, 0, 800, 600))


# ----- piezas libres: se mueven arrastrando, sin modo edición, y un clic sigue siendo un clic -----

def test_pieza_libre_se_mueve_arrastrando_sin_modo_edicion(ventana):
    PiezaEditable(ventana, "letra", libre=True)
    antes = ventana.pos()
    _raton(ventana, QEvent.MouseButtonPress, QPoint(100, 80))
    _raton(ventana, QEvent.MouseMove, QPoint(140, 110))
    _raton(ventana, QEvent.MouseButtonRelease, QPoint(140, 110), botones=Qt.NoButton)
    assert ventana.pos() == antes + QPoint(40, 30)


def test_pieza_libre_clic_corto_no_mueve(ventana):
    PiezaEditable(ventana, "letra", libre=True)
    antes = ventana.pos()
    _raton(ventana, QEvent.MouseButtonPress, QPoint(100, 80))
    _raton(ventana, QEvent.MouseMove, QPoint(102, 81))
    _raton(ventana, QEvent.MouseButtonRelease, QPoint(102, 81), botones=Qt.NoButton)
    assert ventana.pos() == antes


def test_pieza_libre_respeta_la_zona_bloqueada(ventana):
    PiezaEditable(ventana, "barra", libre=True, bloqueo=lambda p: p.y() > 150)
    antes = ventana.pos()
    _raton(ventana, QEvent.MouseButtonPress, QPoint(100, 170))
    _raton(ventana, QEvent.MouseMove, QPoint(160, 190))
    _raton(ventana, QEvent.MouseButtonRelease, QPoint(160, 190), botones=Qt.NoButton)
    assert ventana.pos() == antes


def test_pieza_libre_agranda_desde_la_esquina(ventana):
    PiezaEditable(ventana, "reloj", libre=True)
    w, h = ventana.width(), ventana.height()
    _raton(ventana, QEvent.MouseButtonPress, QPoint(w - 5, h - 5))
    _raton(ventana, QEvent.MouseMove, QPoint(w + 25, h + 15))
    _raton(ventana, QEvent.MouseButtonRelease, QPoint(w + 25, h + 15), botones=Qt.NoButton)
    assert (ventana.width(), ventana.height()) == (w + 30, h + 20)
