# -*- coding: utf-8 -*-
"""La segunda «Actualización grande de Caudal» (presentación a pantalla completa):
cuándo sale, cómo se maneja y capturas de todas las diapositivas. Sin ventanas
a la vista (Qt offscreen) y sin red."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_novedades2")


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def padre(app):
    w = QWidget()
    w.resize(1280, 800)
    w.show()
    app.processEvents()
    yield w
    w.close()


def _nueva(padre, app, **kw):
    from descargador.ui.presentacion_grande import PresentacionGrande
    d = PresentacionGrande(padre, **kw)
    d.show()
    app.processEvents()
    return d


# ================================================================ cuándo sale

def test_edicion_y_comparaciones():
    from descargador import version
    assert version.EDICION_GRANDE == "2.6.0"
    assert version.alcanza_edicion("2.6.0") and version.alcanza_edicion("2.6.3") and version.alcanza_edicion("3.0.0")
    assert not version.alcanza_edicion("2.5.9")
    assert version.es_de_la_edicion("2.6.1") and not version.es_de_la_edicion("2.7.0")
    assert version.hay_novedad("2.5.4", "2.6.0")


def test_toca_una_sola_vez(datos_aislados):
    from descargador.config import Ajustes
    from descargador.ui import novedades_grandes as ng
    a = Ajustes()
    # quien ya vio la presentación anterior (2.5.x) ve esta al llegar a 2.6
    a["version_novedades_vista"] = "2.5.0"
    assert ng.toca_presentacion(a, "2.6.0") and ng.debe_mostrarse(a, "2.6.0")
    # antes de la edición no sale
    assert not ng.toca_presentacion(a, "2.5.9")
    ng.marcar_vista(a, "2.6.0")
    assert not ng.toca_presentacion(a, "2.6.0") and not ng.debe_mostrarse(a, "2.6.0")
    # ni con los parches siguientes
    assert not ng.toca_presentacion(a, "2.6.1") and not ng.debe_mostrarse(a, "2.6.1")
    # y la lógica de antes sigue igual por debajo de la edición
    a["version_novedades_vista"] = "2.4.0"
    assert ng.debe_mostrarse(a, "2.4.4") and not ng.debe_mostrarse(a, "2.4.0")


def test_mostrar_si_toca_abre_la_presentacion_y_no_repite(app, monkeypatch, padre):
    from descargador import version
    from descargador.config import Ajustes
    from descargador.ui import novedades_grandes as ng
    from descargador.ui.presentacion_grande import PresentacionGrande
    monkeypatch.setattr(version, "VERSION", "2.6.0")
    padre.ajustes = Ajustes()
    padre.ajustes["version_novedades_vista"] = "2.5.0"
    d = ng.mostrar_si_toca(padre)
    assert isinstance(d, PresentacionGrande) and d.isVisible()
    assert Ajustes()["version_novedades_vista"] == "2.6.0"
    d.reject()
    app.processEvents()
    assert ng.mostrar_si_toca(padre) is None                    # una sola vez


def test_aviso_antes_de_actualizar_usa_la_presentacion_solo_de_su_edicion(app, monkeypatch, padre):
    from descargador import version
    from descargador.ui import novedades_grandes as ng
    from descargador.ui.presentacion_grande import PresentacionGrande
    monkeypatch.setattr(version, "VERSION", "2.5.4")
    nov = {"version": "2.6.0", "instalador": "https://x/i.exe", "notas": "", "grande": True}
    d = ng.crear_aviso(padre, nov)
    assert isinstance(d, PresentacionGrande)
    d.show()
    app.processEvents()
    d.ir_a(d.n - 1, animar=False)
    d.avanzar(1)
    assert d.bt_sig.text() == "Actualizar ahora" and d.bt_saltar.text() == "Más tarde"
    d.reject()
    sin = ng.crear_aviso(padre, {"version": "2.6.0", "instalador": "", "notas": "", "grande": True})
    sin.show()
    sin.ir_a(sin.n - 1, animar=False)
    sin.avanzar(1)
    assert not sin.bt_sig.isEnabled()
    sin.reject()
    # otra edición (2.7) o una instalación que ya la alcanzó: el aviso de siempre
    assert not isinstance(ng.crear_aviso(padre, {**nov, "version": "2.7.0"}), PresentacionGrande)
    monkeypatch.setattr(version, "VERSION", "2.6.0")
    assert not isinstance(ng.crear_aviso(padre, {**nov, "version": "2.6.1"}), PresentacionGrande)


# ================================================================ manejo

def test_contenido_de_las_diapositivas(app):
    from descargador.ui import presentacion_grande as pg
    assert pg.TITULO == "ACTUALIZACIÓN GRANDE DE CAUDAL"
    assert [d["clave"] for d in pg.DIAPOSITIVAS] == [
        "v5_portada", "gamer", "nivel", "ahora_suena", "personaje", "regalo", "v5_final"]
    assert pg.DIAPOSITIVAS[-1]["titulo"] == "Gracias por escuchar con Caudal"
    todo = " ".join(d["titulo"] + " " + d["texto"] for d in pg.DIAPOSITIVAS).lower()
    assert "triste" not in todo and "ánimo" not in todo and "animo" not in todo and "mood" not in todo
    from descargador.ui.ilustraciones_grandes import ILUSTRACIONES
    assert all(d["clave"] in ILUSTRACIONES for d in pg.DIAPOSITIVAS)


def test_teclado_navega_y_cierra(app, padre):
    d = _nueva(padre, app)
    assert d.indice == 0 and d.bt_saltar.isVisible() and not d.bt_ant.isVisible()
    QTest.keyClick(d, Qt.Key_Right)
    assert d.indice == 1 and d.bt_ant.isVisible()
    QTest.keyClick(d, Qt.Key_Down)
    assert d.indice == 2
    QTest.keyClick(d, Qt.Key_Left)
    assert d.indice == 1
    QTest.keyClick(d, Qt.Key_Return)                           # Enter avanza
    assert d.indice == 2
    QTest.keyClick(d, Qt.Key_End)
    assert d.indice == d.n - 1
    QTest.keyClick(d, Qt.Key_Right)                            # no se sale por el final
    assert d.indice == d.n - 1
    QTest.keyClick(d, Qt.Key_Home)
    assert d.indice == 0
    d.avanzar(1)
    QTest.keyClick(d, Qt.Key_Escape)
    assert not d.isVisible() and d.result() == 0
    app.processEvents()


def test_saltar_empezar_y_enter_final(app, padre):
    d = _nueva(padre, app)
    assert d.bt_saltar.text() == "Saltar" and d.bt_saltar.isVisible()
    QTest.mouseClick(d.bt_saltar, Qt.LeftButton)
    assert not d.isVisible() and d.result() == 0

    d = _nueva(padre, app)
    for _ in range(d.n - 1):
        QTest.mouseClick(d.bt_sig, Qt.LeftButton)
        d.avanzar(1)
    assert d.indice == d.n - 1 and d.bt_sig.text() == "Empezar" and d.bt_saltar.isVisible()
    QTest.mouseClick(d.bt_sig, Qt.LeftButton)
    assert not d.isVisible() and d.result() == 1               # «Empezar» acepta

    d = _nueva(padre, app)
    d.ir_a(d.n - 1, animar=False)
    d.avanzar(1)
    QTest.keyClick(d, Qt.Key_Return)
    assert not d.isVisible() and d.result() == 1               # Enter en la última = Empezar


def test_clic_rueda_y_puntos(app, padre):
    d = _nueva(padre, app)
    QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, QPoint(300, 300))
    assert d.indice == 1                                       # un clic cualquiera avanza
    d.avanzar(1)
    d.grab()                                                   # al pintar se calculan los puntos
    punto = d._puntos[5].center().toPoint()
    QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, punto)
    assert d.indice == 5                                       # un punto lleva a su diapositiva
    d.avanzar(1)
    time.sleep(0.8)
    ev = QWheelEvent(QPointF(400, 400), QPointF(400, 400), QPoint(0, 0), QPoint(0, -120), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    d.wheelEvent(ev)
    assert d.indice == 6                                       # rueda hacia abajo avanza
    d.avanzar(1)
    time.sleep(0.8)
    ev = QWheelEvent(QPointF(400, 400), QPointF(400, 400), QPoint(0, 0), QPoint(0, 120), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    d.wheelEvent(ev)
    assert d.indice == 5
    d.reject()


def test_transicion_real_termina_sola(app, padre):
    d = _nueva(padre, app)
    d.siguiente()
    assert d._ant == 0 and d._p_trans < 1.0
    fin = time.time() + 2.5
    while d._ant is not None and time.time() < fin:
        app.processEvents()
        time.sleep(0.01)
    assert d._ant is None and d._p_trans == 1.0
    d.reject()


def test_pinta_sin_errores_en_todos_los_tamanos(app):
    from descargador.ui.presentacion_grande import PresentacionGrande
    for ancho, alto in ((900, 600), (1000, 900), (1280, 800), (1920, 1080)):
        w = QWidget()
        w.resize(ancho, alto)
        w.show()
        d = PresentacionGrande(w)
        d.show()
        app.processEvents()
        assert (d.width(), d.height()) == (ancho, alto)
        for i in range(d.n):
            d.ir_a(i, animar=False)
            d.avanzar(3.0)
            d.grab()
        # a medias de una transición también pinta
        d.ir_a(0, animar=False)
        d.avanzar(2)
        d.siguiente()
        d._p_trans = 0.5
        d.grab()
        d.reject()
        w.close()


def test_rendimiento_de_un_fotograma(app, padre):
    d = _nueva(padre, app)
    d.avanzar(3)
    for i in (0, 3, 5):
        d.ir_a(i, animar=False)
        d.avanzar(3)
        d.grab()
        t = time.perf_counter()
        for _ in range(5):
            d.grab()
        medio = (time.perf_counter() - t) / 5
        assert medio < 0.12, f"diapositiva {i}: {medio * 1000:.0f} ms por fotograma"
    d.reject()


def test_capturas_de_todas_las_diapositivas(app):
    os.makedirs(CAPTURAS, exist_ok=True)
    w = QWidget()
    w.resize(1280, 800)
    w.show()
    from descargador.ui.presentacion_grande import PresentacionGrande
    d = PresentacionGrande(w)
    d.show()
    app.processEvents()
    for i in range(d.n):
        d.ir_a(i, animar=False)
        d.avanzar(4.0)
        img = d.grab().toImage()
        assert img.width() == 1280 and img.height() == 800
        img.save(os.path.join(CAPTURAS, f"d{i:02d}_1280.png"))
    d.reject()
    w.close()
