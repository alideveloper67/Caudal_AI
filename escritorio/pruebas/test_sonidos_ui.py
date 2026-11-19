# -*- coding: utf-8 -*-
"""Sonidos de interfaz (donadores): bajitos, opcionales y solo con «me gusta» y al abrir.
Sin ventanas a la vista (Qt offscreen), sin internet y sin sonar de verdad."""

import os
import sys
import wave

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import sonidos_ui as SU  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


class _Prem:
    def __init__(self, si=True):
        self.premium = si


class _Aj(dict):
    def guardar(self):
        pass


class _Ctx(QObject):
    me_gusta_cambio = Signal(str, bool)

    def __init__(self, premium=True, activo=True, tipo="moneda"):
        super().__init__()
        self.premium = _Prem(premium)
        self.ajustes = _Aj(sonidos_ui=activo, sonido_ui_tipo=tipo)


@pytest.fixture
def sonados(monkeypatch):
    lista = []
    monkeypatch.setattr(SU, "tocar", lambda nombre: lista.append(nombre) or True)
    return lista


# ------------------------------------------------------------------ los sonidos

@pytest.mark.parametrize("nombre", list(SU.SONIDOS))
def test_los_sonidos_son_bajitos_y_limpios(nombre):
    x = SU.sintetizar(nombre)
    assert 0.2 < len(x) / SU.FRECUENCIA < 1.2                  # breves
    pico = max(abs(v) for v in x)
    assert 0.25 * 32767 < pico <= 0.31 * 32767                 # volumen bajo: pico al 30 %, sin saturar
    assert abs(x[0]) < 0.02 * 32767                            # empieza sin «clic»
    assert max(abs(v) for v in x[-200:]) < 0.05 * 32767         # y se apaga solo


def test_los_tres_suenan_distinto():
    a, b, c = (SU.sintetizar(n) for n in ("burbuja", "moneda", "campana"))
    assert a != b != c and len(a) != len(c)


def test_un_nombre_raro_cae_en_burbuja():
    assert SU.sonido_valido("explosion") == "burbuja"
    assert SU.sintetizar("explosion") == SU.sintetizar("burbuja")


def test_el_wav_se_fabrica_una_vez_y_es_valido(datos_aislados):
    ruta = SU.ruta_sonido("campana")
    assert ruta.exists() and str(datos_aislados) in str(ruta)
    with wave.open(str(ruta), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, SU.FRECUENCIA)
        assert w.getnframes() > 1000
    t = ruta.stat().st_mtime_ns
    assert SU.ruta_sonido("campana") == ruta and ruta.stat().st_mtime_ns == t     # no se rehace


# ------------------------------------------------------------------ cuándo suenan

def test_suena_al_dar_me_gusta_y_no_al_quitarlo(app, sonados):
    ctx = _Ctx()
    SU.SonidosUI(ctx, ctx)
    ctx.me_gusta_cambio.emit("a", True)
    assert sonados == ["moneda"]
    ctx.me_gusta_cambio.emit("a", False)                       # quitar el me gusta: silencio
    assert sonados == ["moneda"]


def test_sin_donador_o_apagado_no_suena(app, sonados):
    for ctx in (_Ctx(premium=False), _Ctx(activo=False)):
        g = SU.SonidosUI(ctx, ctx)
        ctx.me_gusta_cambio.emit("a", True)
        g.al_abrir()
        assert sonados == [] and g.tocados == []


def test_al_abrir_suena_una_sola_vez(app, sonados):
    ctx = _Ctx(tipo="campana")
    g = SU.SonidosUI(ctx, ctx)
    g.al_abrir()
    g.al_abrir()
    assert sonados == ["campana"]


def test_el_tipo_se_lee_en_cada_sonido_y_un_evento_raro_se_ignora(app, sonados):
    ctx = _Ctx()
    g = SU.SonidosUI(ctx, ctx)
    ctx.ajustes["sonido_ui_tipo"] = "burbuja"
    assert g.sonar("gusta") == "burbuja"
    assert g.sonar("explotar") is None
    ctx.ajustes["sonido_ui_tipo"] = "otro"
    assert g.sonar("gusta") == "burbuja"


def test_instalar_crea_un_solo_gestor(app, sonados):
    ctx = _Ctx()
    assert SU.instalar(ctx) is SU.instalar(ctx)
    ctx.me_gusta_cambio.emit("a", True)
    assert len(sonados) == 1                                   # no se conectó dos veces


def test_tocar_no_revienta_sin_winsound(monkeypatch):
    monkeypatch.setattr(SU, "winsound", None)
    assert SU.tocar("moneda") is False
