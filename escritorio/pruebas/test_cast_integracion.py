# -*- coding: utf-8 -*-
"""Cast integrado en el Reproductor y la barra de verdad (escritorio)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_cast import COCINA, SALA, ServidorFalso, TeleFalsa  # noqa: E402,F401
from test_dj_inteligente import MotorFalso, _pista  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _rep(app, monkeypatch, tmp_path):
    from descargador import cast, mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    a = Ajustes()
    a["sponsorblock"] = False
    a["autoplay"] = False
    r = Reproductor(a, Coleccion())
    assert isinstance(r.cast, cast.ControlCast)
    tele, srv = TeleFalsa(), ServidorFalso()
    r.cast = cast.ControlCast(cast.anfitrion_de(r), puente=tele, servidor=srv, padre=r)
    r.cast.despues = lambda _ms, fn: fn()
    r.disponible = True
    r.audio = [MotorFalso(), MotorFalso()]
    r.activo = 0
    archivos = []
    for n in (1, 2, 3):
        f = tmp_path / f"{n}.opus"
        f.write_bytes(b"x")
        archivos.append(str(f))
    pistas = [_pista(n, archivo=archivos[n - 1]) for n in (1, 2, 3)]
    r.secuencia, r.original = list(pistas), list(pistas)
    r.pos = 0
    r._cargar(pistas[0])
    r.estado = "sonando"
    r._posicion = 33.0
    return r, tele, srv, pistas


def test_flujo_completo_con_el_reproductor_parcheado(app, monkeypatch, tmp_path):
    r, tele, srv, pistas = _rep(app, monkeypatch, tmp_path)
    m = r.audio[0]
    assert len(m.cargas) == 1                       # sonaba en la PC
    r.cast.conectar(SALA)
    assert r.cast.activo
    assert m.parado                                 # la PC se calla
    medio, desde, sonar = tele.cargados[-1]
    assert srv.archivos[0] == pistas[0]["archivo"]   # la descarga la sirve la PC
    assert desde == 33.0 and sonar
    tele.dice("sonando", posicion=33.0)
    assert r.estado == "sonando"

    r.pausar()
    assert tele.ordenes[-1] == "pausar" and r.estado == "pausa"
    r.alternar()
    assert tele.ordenes[-1] == "sonar"
    r.buscar(100)
    assert tele.ordenes[-1] == "ir_a 100" and r._posicion == 100
    r.fijar_volumen(30)
    assert tele.ordenes[-1] == "volumen 0.3"

    # siguiente a mano: va a la tele, no a la PC
    cargas_pc = len(m.cargas)
    r.siguiente()
    assert r.actual is pistas[1]
    assert tele.cargados[-1][0]["titulo"] == "Canción 2"
    assert len(m.cargas) == cargas_pc

    # termina en la tele: sigue la 3
    tele.dice("sonando", posicion=0)
    tele.dice("terminado")
    assert r.actual is pistas[2]
    assert tele.cargados[-1][0]["titulo"] == "Canción 3"

    # desconectar: vuelve a la PC en el mismo punto
    tele.dice("sonando", posicion=61)
    r.cast.desconectar()
    assert not r.cast.activo
    fuente, inicio = r.audio[r.activo].cargas[-1]
    assert fuente["archivo"] == pistas[2]["archivo"]
    assert 61 <= inicio < 62


def test_la_barra_parcheada_importa():
    import importlib
    mod = importlib.import_module("descargador.ui.barra_reproduccion")
    assert hasattr(mod, "BotonCast")
