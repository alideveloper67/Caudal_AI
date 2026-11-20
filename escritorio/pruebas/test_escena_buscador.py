# -*- coding: utf-8 -*-
"""Pruebas del buscador de la escena (PanelBusqueda)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.buscador import PanelBusqueda  # noqa: E402

CANCIONES = [{"titulo": f"Tema {i}", "artista": f"Artista {i}", "miniatura": f"http://x/c{i}.jpg"}
             for i in range(6)]
ARTISTAS = [{"titulo": f"Banda {i}", "miniatura": f"http://x/a{i}.jpg"} for i in range(7)]
ALTO_REPOSO = 68          # 24 de hueco + 44 de píldora
ALTO_CON_RESULTADOS = 456  # píldora + 10 de hueco + panel de 362 + 16 de margen superior
ALTO_ERROR = 170           # píldora + 10 + panel de error de 76 + 16 de margen superior


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _sin_imagen(url, callback):
    callback(QImage())


def _imagen_color(url, callback):
    img = QImage(200, 200, QImage.Format_ARGB32)
    img.fill(QColor(200, 80, 120))
    callback(img)


def _panel(app, cargador=_sin_imagen):
    w = PanelBusqueda()
    w.fijar_cargador(cargador)
    w.show()
    app.processEvents()
    return w


def _abrir_menu(w):
    QTest.mouseClick(w, Qt.LeftButton, pos=w.rect_boton_fuente().center().toPoint())


def test_enter_emite_texto_y_fuente(app):
    w = _panel(app)
    emitidas = []
    w.buscar.connect(lambda texto, clave: emitidas.append((texto, clave)))
    w.fijar_fuente("ytmusic")
    w._campo.setText("  queen  ")
    QTest.keyClick(w._campo, Qt.Key_Return)
    assert emitidas == [("queen", "ytmusic")]
    assert w.altura_deseada() > ALTO_REPOSO  # pasa a cargando


def test_texto_vacio_no_emite(app):
    w = _panel(app)
    emitidas = []
    w.buscar.connect(lambda texto, clave: emitidas.append((texto, clave)))
    w._campo.setText("   ")
    QTest.keyClick(w._campo, Qt.Key_Return)
    assert emitidas == []
    assert w.altura_deseada() == ALTO_REPOSO


def test_menu_opcion_dos_cambia_fuente_y_emite(app):
    w = _panel(app)
    cambios = []
    w.fuente_cambiada.connect(cambios.append)
    _abrir_menu(w)
    assert w._menu_abierto
    QTest.mouseClick(w, Qt.LeftButton, pos=w.rect_opcion_fuente(1).center().toPoint())
    assert w.fuente_actual() == "ytmusic"
    assert cambios == ["ytmusic"]
    assert not w._menu_abierto


def test_clic_en_cancion_y_artista_emiten_el_dict(app):
    w = _panel(app)
    w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5])
    elegidas, artistas = [], []
    w.elegida.connect(elegidas.append)
    w.artista.connect(artistas.append)
    QTest.mouseClick(w, Qt.LeftButton, pos=w.rect_cancion(0).center().toPoint())
    QTest.mouseClick(w, Qt.LeftButton, pos=w.rect_artista(1).center().toPoint())
    assert elegidas == [CANCIONES[0]]
    assert artistas == [ARTISTAS[1]]


def test_esc_limpia_el_campo_y_los_resultados(app):
    w = _panel(app)
    w._campo.setText("queen")
    w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5])
    QTest.keyClick(w._campo, Qt.Key_Escape)
    assert w._campo.text() == ""
    assert w.altura_deseada() == ALTO_REPOSO
    assert w._modo == "reposo"


def test_esc_con_menu_abierto_solo_cierra_el_menu(app):
    w = _panel(app)
    w._campo.setText("queen")
    _abrir_menu(w)
    QTest.keyClick(w._campo, Qt.Key_Escape)
    assert not w._menu_abierto
    assert w._campo.text() == "queen"


def test_altura_crece_con_resultados_y_avisa(app):
    w = _panel(app)
    avisos = []
    w.cambio_tamano.connect(lambda: avisos.append(1))
    assert w.altura_deseada() == ALTO_REPOSO
    w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5])
    assert w.altura_deseada() == ALTO_CON_RESULTADOS
    assert w.height() == ALTO_CON_RESULTADOS
    assert avisos
    # el panel no toca el borde superior: queda a 16 px
    assert w._disposicion()["panel"].top() == 16


def test_sin_resultados_muestra_aviso_con_la_consulta(app):
    w = _panel(app)
    w._campo.setText("queen")
    QTest.keyClick(w._campo, Qt.Key_Return)
    w.mostrar_resultados([], [])
    assert w._modo == "error"
    assert w._error == "Sin resultados para «queen»"
    assert w.altura_deseada() == ALTO_ERROR


def test_cargando_y_error_cambian_la_altura(app):
    w = _panel(app)
    w.mostrar_cargando()
    assert w.altura_deseada() == ALTO_CON_RESULTADOS
    w.mostrar_error("Sin conexión con YouTube")
    assert w.altura_deseada() == ALTO_ERROR


def test_cargador_recibe_todas_las_miniaturas(app):
    pedidas = []

    def cargador(url, callback):
        pedidas.append(url)
        callback(QImage())

    w = _panel(app, cargador)
    w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5])
    assert len(pedidas) == 9
    assert set(pedidas) == {c["miniatura"] for c in CANCIONES[:4]} | {a["miniatura"] for a in ARTISTAS[:5]}


def test_animacion_solo_mientras_carga(app):
    w = _panel(app)
    w.mostrar_cargando()
    assert w._timer.isActive()
    w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5])
    assert not w._timer.isActive()


def test_render_de_todos_los_estados_sin_errores(app):
    w = _panel(app, _imagen_color)
    estados = []
    estados.append(lambda: None)                                            # solo campo
    estados.append(lambda: w.mostrar_cargando())                           # cargando
    estados.append(lambda: w.mostrar_error("No se pudo buscar. Revisa la conexión."))
    estados.append(lambda: w.mostrar_resultados(CANCIONES[:4], ARTISTAS[:5]))  # con carátulas
    estados.append(lambda: w.mostrar_resultados(CANCIONES[:2], []))         # solo canciones
    estados.append(lambda: w.mostrar_resultados([], ARTISTAS[:3]))          # solo artistas
    estados.append(lambda: _abrir_menu(w))                                  # menú abierto
    for preparar in estados:
        preparar()
        app.processEvents()
        alto = w.altura_deseada()
        w.resize(640, alto)
        img = QImage(640, alto, QImage.Format_ARGB32)
        img.fill(0)
        w.render(img)
        assert not img.isNull()
        # el centro de la píldora debe quedar pintado (alfa > 0)
        assert img.pixelColor(320, alto - 46).alpha() > 0
