# -*- coding: utf-8 -*-
"""Presentación «Gracias, donador»: recorre sus cinco diapositivas, solo para donadores de verdad,
una sola vez, y espera a «Somos 100». Qt offscreen; ajustes aislados en una carpeta temporal."""

import os
import sys
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app, tmp_path, monkeypatch):
    # ajustes en una carpeta temporal: nunca los de la persona
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador.config import Ajustes
    w = QWidget()
    w.resize(1280, 720)
    w.ajustes = Ajustes()
    w.en_completa = False
    w._saliendo = False
    w.navegados = []
    w.navegar = lambda destino: w.navegados.append(destino)
    w.show()
    yield w
    w.close()


def _ctx(donador=True, tipo="donador", nombre="Ana"):
    premium = SimpleNamespace(donador_de_verdad=donador, tipo=tipo)
    return SimpleNamespace(premium=premium, cuenta={"nombre": nombre, "usuario": "ana"})


def _hijos(ventana):
    from descargador.ui.presentacion_donadores import PresentacionDonadores
    return ventana.findChildren(PresentacionDonadores)


def test_textos_del_guion():
    from descargador.ui import presentacion_donadores as P
    d = P.diapositivas("Ana")
    titulos = [x["titulo"] for x in d]
    assert titulos[:3] == ["Gracias, Ana", "Ayudaste a que Caudal crezca", "Tu perfil de donador"]
    assert titulos[-3:] == ["Todas tus exclusivas", "Y esto sigue", "Gracias por creer en Caudal."]
    from descargador.ui.demos_presentacion import DEMOS
    demos = [x["demo"] for x in d if x.get("vis") == "demo"]
    assert demos[0] == "mi_perfil" and len(demos) >= 6 and all(k in DEMOS for k in demos)
    assert P.diapositivas("")[0]["titulo"] == "Gracias"
    assert len(P.EXCLUSIVAS) == 10
    assert P.CLAVE_VISTA == "presentacion_donadores_vista"


def test_recorre_las_cinco_diapositivas(app, ventana):
    from descargador.ui.presentacion_donadores import PresentacionDonadores
    d = PresentacionDonadores(ventana, ctx=_ctx(), nombre="Ana")
    d.show()
    QApplication.processEvents()
    for i in range(d.n):
        d.ir_a(i, animar=False)
        d.avanzar(3.0)
        assert d.indice == i
        d.grab()                                  # pinta la diapositiva sin errores
        assert d.bt_sig.isVisible() == (i < d.n - 1)
        assert d.bt_descubrir.isVisible() == (i == d.n - 1)
        assert d.bt_seguir.isVisible() == (i == d.n - 1)
    d.ir_a(2, animar=False)
    QTest.keyClick(d, Qt.Key_Left)
    d.avanzar(1.0)
    assert d.indice == 1
    QTest.keyClick(d, Qt.Key_Right)
    d.avanzar(1.0)
    assert d.indice == 2
    d.close()


def test_grid_cabe_en_1280x720(app, ventana):
    from descargador.ui.presentacion_donadores import PresentacionDonadores
    d = PresentacionDonadores(ventana, ctx=_ctx())
    d.show()
    d.setGeometry(0, 0, 1280, 720)
    i = next(k for k, x in enumerate(d.diap) if x.get("grid"))
    L = d._layout(i)
    fs = L["fs"]
    fin = L["y_abajo"] + L["grid"]["total"]
    assert fin <= d.height() - 100 * fs + 0.5
    assert len(L["grid"]["tarjetas"]) == 10
    d.close()


def test_no_se_abre_con_prueba_gratuita(app, ventana):
    from descargador.ui import presentacion_donadores as P
    ventana.ctx = _ctx(donador=False, tipo="prueba")
    assert P.revisar_donador(ventana) is None
    assert _hijos(ventana) == []
    assert ventana.ajustes.get(P.CLAVE_VISTA) is False


def test_se_abre_y_queda_marcada(app, ventana, tmp_path, monkeypatch):
    from descargador.ui import presentacion_donadores as P
    from descargador.config import Ajustes
    ventana.ctx = _ctx()
    dlg = P.revisar_donador(ventana)
    assert dlg is not None
    assert len(_hijos(ventana)) == 1
    assert ventana.ajustes.get(P.CLAVE_VISTA) is True
    # persistido en la carpeta temporal
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert Ajustes().get(P.CLAVE_VISTA) is True
    dlg.close()


def test_ya_vista_no_abre(app, ventana):
    from descargador.ui import presentacion_donadores as P
    ventana.ctx = _ctx()
    ventana.ajustes[P.CLAVE_VISTA] = True
    assert P.revisar_donador(ventana) is None
    assert _hijos(ventana) == []


def test_fundador_muestra_medalla(app, ventana):
    from descargador.ui import presentacion_donadores as P
    ventana.ctx = _ctx(tipo="fundador")
    dlg = P.revisar_donador(ventana)
    assert dlg.medalla == "Fundador de Caudal"
    dlg.close()
    ventana.ajustes[P.CLAVE_VISTA] = False
    ventana.ctx = _ctx(tipo="donador")
    dlg2 = P.revisar_donador(ventana)
    assert dlg2.medalla == "Donador de Caudal"
    dlg2.close()


def test_espera_a_somos_100(app, ventana):
    from descargador.ui import presentacion_donadores as P
    from descargador.ui.presentacion_100 import Presentacion100
    ventana.ctx = _ctx()
    somos = Presentacion100(ventana)
    somos.show()
    QApplication.processEvents()
    assert P.revisar_donador(ventana) is None          # Somos 100 en pantalla: espera
    assert ventana.ajustes.get(P.CLAVE_VISTA) is False
    assert _hijos(ventana) == []
    somos.close()
    QApplication.processEvents()
    dlg = P.revisar_donador(ventana)                   # ya cerrada: ahora sí
    assert dlg is not None
    assert ventana.ajustes.get(P.CLAVE_VISTA) is True
    dlg.close()


def test_descubrir_navega_y_cierra(app, ventana):
    from descargador.ui import presentacion_donadores as P
    ventana.ctx = _ctx()
    dlg = P.revisar_donador(ventana)
    dlg.ir_a(4, animar=False)
    dlg.avanzar(3.0)
    dlg._descubrir()
    assert not dlg.isVisible()                 # cierra en el acto (WA_DeleteOnClose la borra después)
    QApplication.processEvents()
    assert ventana.navegados == [{"pagina": "ajustes"}]
