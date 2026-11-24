# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.tarjeta import TarjetaCancion


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


PISTA = {"titulo": "Canción de prueba", "artista": "Artista de prueba", "fuente_texto": "YouTube"}


def _portada(color="#ff8800", lado=400):
    img = QImage(lado, lado, QImage.Format_ARGB32)
    img.fill(QColor(color))
    return img


def _render(w):
    img = QImage(w.width(), w.height(), QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    w.render(img)
    return img


def _tarjeta(app):
    w = TarjetaCancion()
    w.resize(360, 520)
    w.show()
    app.processEvents()
    w._timer.stop()        # sin animación en las pruebas: las posiciones de clic quedan fijas
    return w


def test_poner_con_datos_y_valor_por_defecto(app):
    w = TarjetaCancion()
    w.resize(360, 520)
    w.poner(PISTA)
    assert w._titulo == "Canción de prueba"
    assert w._artista == "Artista de prueba"
    assert w._fuente_texto == "YouTube"
    w.poner({"titulo": "Sin fuente"})
    assert w._fuente_texto == "Sonando en Caudal"
    assert _render(w).width() == w.width()


def test_poner_none_no_falla(app):
    w = TarjetaCancion()
    w.poner(PISTA)
    w.poner(None)
    assert w._pista is None
    assert w._titulo == "Nada sonando"
    assert w._fuente_texto == "Sonando en Caudal"
    img = _render(w)
    assert not img.isNull()


def test_poner_portada_de_color(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_portada(_portada("#00aa55"))
    assert w._portada is not None
    img = _render(w)
    assert not img.isNull()
    w.poner_portada(None)
    assert w._portada is None
    assert not _render(w).isNull()


def test_cache_se_rehace_solo_si_cambia_algo(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    _render(w)
    base = w._rehechos
    assert base >= 1

    # repintar sin cambios no rehace la caché (la inclinación no cuenta)
    w._ang_y = 7.0
    w._flota = 3.0
    _render(w)
    assert w._rehechos == base

    # mismos datos: no cambia nada
    w.poner(dict(PISTA))
    _render(w)
    assert w._rehechos == base

    w.poner({**PISTA, "titulo": "Otra"})
    _render(w)
    assert w._rehechos == base + 1

    w.poner_portada(_portada())
    _render(w)
    assert w._rehechos == base + 2

    w.poner_colores(QColor("#112233"), QColor("#445566"), QColor("#778899"))
    _render(w)
    assert w._rehechos == base + 3

    w.fijar_me_gusta(True)
    _render(w)
    assert w._rehechos == base + 4

    w.fijar_me_gusta(True)           # sin cambio
    _render(w)
    assert w._rehechos == base + 4

    w.fijar_progreso(0.4)
    _render(w)
    assert w._rehechos == base + 5

    w.resize(380, 520)               # cambio de tamaño
    _render(w)
    assert w._rehechos == base + 6


def test_clic_en_boton_letra_emite_senal(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    cuenta = {"letra": 0, "gusta": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_me_gusta.connect(lambda: cuenta.__setitem__("gusta", cuenta["gusta"] + 1))
    centro = w.rect_boton_letra().center().toPoint()
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centro)
    assert cuenta == {"letra": 1, "gusta": 0}


def test_clic_en_corazon_emite_senal(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_portada(_portada())
    cuenta = {"letra": 0, "gusta": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_me_gusta.connect(lambda: cuenta.__setitem__("gusta", cuenta["gusta"] + 1))
    centro = w.rect_corazon().center().toPoint()
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, centro)
    assert cuenta == {"letra": 0, "gusta": 1}


def test_clic_fuera_no_emite(app):
    w = _tarjeta(app)
    cuenta = []
    w.pidio_otra_letra.connect(lambda: cuenta.append(1))
    w.pidio_me_gusta.connect(lambda: cuenta.append(1))
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5))
    assert cuenta == []


def test_render_sin_portada(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.fijar_progreso(0.5)
    img = _render(w)
    assert not img.isNull()
    assert img.pixelColor(180, 260).alpha() > 0      # la tarjeta se ve en el centro


def test_render_con_portada_y_me_gusta(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_portada(_portada("#2255cc"))
    w.fijar_me_gusta(True)
    w.fijar_progreso(1.0)
    img = _render(w)
    assert not img.isNull()
    assert img.pixelColor(180, 200).alpha() > 0


def test_rectangulos_dentro_del_widget(app):
    w = _tarjeta(app)
    assert w.rect_boton_letra().bottom() <= w.height()
    assert w.rect_corazon().right() <= w.width()
    assert w.rect_corazon().top() >= 0
    assert w.rect_boton_letra().contains(w.rect_boton_letra().center())


def test_timer_solo_mientras_se_ve(app):
    w = TarjetaCancion()
    w.resize(360, 520)
    w.show()
    app.processEvents()
    assert w._timer.isActive()
    w.hide()
    assert not w._timer.isActive()


def _borde_vacio(img):
    """True si ningún píxel no transparente toca la fila o columna del borde."""
    ancho, alto = img.width(), img.height()
    bordes = [(x, 0) for x in range(ancho)] + [(x, alto - 1) for x in range(ancho)]
    bordes += [(0, y) for y in range(alto)] + [(ancho - 1, y) for y in range(alto)]
    return all(img.pixelColor(x, y).alpha() == 0 for x, y in bordes)


@pytest.mark.parametrize("ancho,alto", [(256, 370), (540, 780)])
def test_escala_no_corta_el_dibujo(app, ancho, alto):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_portada(_portada())
    w.fijar_me_gusta(True)
    w.fijar_progreso(0.5)
    w.resize(ancho, alto)
    app.processEvents()
    img = _render(w)
    assert _borde_vacio(img)
    assert img.pixelColor(ancho // 2, alto // 2).alpha() > 0   # el contenido sigue visible


@pytest.mark.parametrize("ancho,alto", [(256, 370), (540, 780)])
def test_clics_en_rectangulos_escalados(app, ancho, alto):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.resize(ancho, alto)
    app.processEvents()
    w._timer.stop()
    cuenta = {"letra": 0, "gusta": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_me_gusta.connect(lambda: cuenta.__setitem__("gusta", cuenta["gusta"] + 1))
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, w.rect_corazon().center().toPoint())
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, w.rect_boton_letra().center().toPoint())
    assert cuenta == {"letra": 1, "gusta": 1}


def test_clic_en_traducir_emite_solo_traducir(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    cuenta = {"letra": 0, "traducir": 0, "gusta": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_traducir.connect(lambda: cuenta.__setitem__("traducir", cuenta["traducir"] + 1))
    w.pidio_me_gusta.connect(lambda: cuenta.__setitem__("gusta", cuenta["gusta"] + 1))
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, w.rect_boton_traducir().center().toPoint())
    assert cuenta == {"letra": 0, "traducir": 1, "gusta": 0}


def test_clic_en_aa_pide_el_diseno_de_letra(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    cuenta = {"letra": 0, "traducir": 0, "diseno": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_traducir.connect(lambda: cuenta.__setitem__("traducir", cuenta["traducir"] + 1))
    w.pidio_diseno.connect(lambda: cuenta.__setitem__("diseno", cuenta["diseno"] + 1))
    for ancho, alto in ((360, 520), (180, 260), (540, 780)):
        w.resize(ancho, alto)
        app.processEvents()
        w._timer.stop()
        r = w.rect_boton_diseno()
        assert not r.intersects(w.rect_boton_traducir()) and r.right() <= w.width() and r.left() >= 0
        QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, r.center().toPoint())
    assert cuenta == {"letra": 0, "traducir": 0, "diseno": 3}
    assert not _render(w).isNull()


def test_clic_en_otra_letra_no_emite_traducir(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    cuenta = {"letra": 0, "traducir": 0}
    w.pidio_otra_letra.connect(lambda: cuenta.__setitem__("letra", cuenta["letra"] + 1))
    w.pidio_traducir.connect(lambda: cuenta.__setitem__("traducir", cuenta["traducir"] + 1))
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, w.rect_boton_letra().center().toPoint())
    assert cuenta == {"letra": 1, "traducir": 0}


@pytest.mark.parametrize("ancho,alto", [(360, 520), (180, 260)])
def test_pildoras_no_se_solapan(app, ancho, alto):
    w = _tarjeta(app)
    w.resize(ancho, alto)
    app.processEvents()
    w._timer.stop()
    letra, traducir = w.rect_boton_letra(), w.rect_boton_traducir()
    assert not letra.intersects(traducir)
    assert letra.right() < traducir.left()
    # separación de 8 px en el espacio de diseño, escalada como el resto
    assert traducir.left() - letra.right() == pytest.approx(8 * w._factor())
    assert letra.height() == pytest.approx(traducir.height())
    assert letra.top() == pytest.approx(traducir.top())
    # el par queda dentro del widget
    assert letra.left() >= 0 and traducir.right() <= w.width()


def test_fijar_traduccion_no_rompe_render(app):
    w = _tarjeta(app)
    w.poner(PISTA)
    w.poner_portada(_portada())
    w.fijar_traduccion(True)
    assert w._traduccion_activa is True
    img = _render(w)
    assert not img.isNull()
    assert img.pixelColor(180, 200).alpha() > 0
    w.fijar_traduccion(False)
    assert w._traduccion_activa is False
    assert not _render(w).isNull()
