# -*- coding: utf-8 -*-
"""Colores que siguen la carátula: la paleta sale de la imagen reducida (y se cachea), la transición es suave
y solo existe para donadores. Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import paleta_caratula as PC  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def imagen(*colores):
    """Una imagen con franjas verticales de los colores dados."""
    img = QImage(120, 120, QImage.Format_RGB32)
    p = QPainter(img)
    ancho = 120 // len(colores)
    for i, c in enumerate(colores):
        p.fillRect(i * ancho, 0, ancho + 1, 120, QColor(c))
    p.end()
    return img


class _Prem(QObject):
    cambiado = Signal()

    def __init__(self, premium=True):
        super().__init__()
        self.premium = premium


class _R(QObject):
    pista_cambio = Signal(object)

    def __init__(self):
        super().__init__()
        self.actual = None


class _Aj(dict):
    def guardar(self):
        pass


class _Gamer:
    ahorrando = False


class _Ctx(QObject):
    def __init__(self, premium=True):
        super().__init__()
        self.reproductor = _R()
        self.premium = _Prem(premium)
        self.ajustes = _Aj(colores_caratula=True)
        self.gamer = _Gamer()


def bombear(app, cond, maximo=3.0):
    fin = time.time() + maximo
    while not cond() and time.time() < fin:
        app.processEvents()
        time.sleep(0.01)
    return cond()


def tono(hexa):
    return QColor(hexa).hsvHueF()


# ------------------------------------------------------------------ la paleta

def test_paleta_saca_los_colores_de_la_imagen():
    pal = PC.calcular_paleta(imagen("#E11D1D", "#1D4ED8", "#16A34A"))
    assert len(pal) == 3 and all(h.startswith("#") and len(h) == 7 for h in pal)
    tonos = sorted(round(tono(h) * 360) for h in pal)
    # rojo (~0/360), verde (~120-140) y azul (~220) están: tres tonos separados
    assert any(t < 20 or t > 340 for t in tonos)
    assert any(100 <= t <= 160 for t in tonos)
    assert any(200 <= t <= 240 for t in tonos)


def test_el_dominante_va_primero():
    pal = PC.calcular_paleta(imagen("#0EA5E9", "#0EA5E9", "#0EA5E9", "#E11D1D"))
    assert 180 <= tono(pal[0]) * 360 <= 215


def test_un_solo_color_se_completa_con_tonos_vecinos():
    pal = PC.calcular_paleta(imagen("#7C3AED"))
    assert len(set(pal)) == 3
    assert all(abs(tono(h) * 360 - 262) < 45 for h in pal)


def test_gris_o_sin_imagen_da_una_paleta_neutra():
    assert PC.calcular_paleta(imagen("#808080", "#303030")) == PC.GRIS
    assert PC.calcular_paleta(QImage()) == PC.GRIS
    assert PC.calcular_paleta(None) == PC.GRIS


def test_los_colores_no_son_chillones_ni_apagados():
    for h in PC.calcular_paleta(imagen("#FF0000", "#00FF00", "#0000FF")):
        c = QColor(h)
        assert 0.5 - 0.02 <= c.hsvSaturationF() <= 0.92 + 0.02
        assert 0.58 - 0.02 <= c.valueF() <= 0.96 + 0.02


def test_la_paleta_se_cachea_por_url(app, monkeypatch):
    from descargador.ui import imagenes
    PC.CACHE.clear()
    pedidas, hechas = [], []
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: (pedidas.append(url), cb(imagen("#E11D1D")))[1])
    real = PC.calcular_paleta
    monkeypatch.setattr(PC, "calcular_paleta", lambda img: (hechas.append(1), real(img))[1])
    recibidas = []
    PC.paleta_de_url("u1", recibidas.append)
    PC.paleta_de_url("u1", recibidas.append)
    assert len(recibidas) == 2 and recibidas[0] == recibidas[1]
    assert pedidas == ["u1"] and len(hechas) == 1          # la imagen se pidió y se calculó una sola vez
    PC.paleta_de_url("", recibidas.append)
    assert recibidas[-1] == PC.GRIS


# ------------------------------------------------------------------ la transición

@pytest.fixture
def colores(app, monkeypatch):
    from descargador.ui import imagenes
    PC.CACHE.clear()
    imgs = {"rojo": imagen("#E11D1D"), "azul": imagen("#1D4ED8")}
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(imgs[url]))
    ctx = _Ctx()
    g = PC.ColoresCaratula(ctx, ctx)
    g.ctx_falso = ctx
    return g


def test_sin_pista_no_hay_paleta(colores):
    assert colores.fuerza == 0 and not colores.animando


def test_pasa_de_un_color_a_otro_sin_saltos(app, colores):
    ctx = colores.ctx_falso
    ctx.reproductor.actual = {"miniatura": "rojo"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    assert bombear(app, lambda: not colores.animando)
    assert colores.fuerza == pytest.approx(1.0, abs=0.01)
    rojo = QColor(colores.hex_actuales()[0])
    assert rojo.hsvHueF() < 0.05 or rojo.hsvHueF() > 0.95
    # otra carátula: los colores viajan hacia el azul pasando por pasos intermedios
    ctx.reproductor.actual = {"miniatura": "azul"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    pasos = []
    colores.cambio.connect(lambda: pasos.append(QColor(colores.hex_actuales()[0]).red()))
    assert colores.animando
    assert bombear(app, lambda: not colores.animando)
    assert len(pasos) >= 5                                    # no es un salto: hay varios pasos
    # el rojo baja de forma monótona (nunca rebota) hasta el del azul
    assert all(a >= b for a, b in zip(pasos, pasos[1:]))
    assert pasos[0] > pasos[-1]
    azul = QColor(colores.hex_actuales()[0])
    assert 0.55 < azul.hsvHueF() < 0.7


def test_dura_menos_de_un_segundo_y_el_reloj_se_apaga(app, colores):
    ctx = colores.ctx_falso
    ctx.reproductor.actual = {"miniatura": "rojo"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    t0 = time.time()
    assert bombear(app, lambda: not colores.animando, 2.0)
    assert time.time() - t0 < 1.5
    assert not colores._reloj.isActive()                      # en reposo no gasta nada


def test_sin_donador_o_apagado_no_cambia_nada(app, monkeypatch):
    from descargador.ui import imagenes
    PC.CACHE.clear()
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(imagen("#E11D1D")))
    ctx = _Ctx(premium=False)
    g = PC.ColoresCaratula(ctx, ctx)
    ctx.reproductor.actual = {"miniatura": "rojo"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    assert g.fuerza == 0 and not g.animando and not g.habilitado()
    # con donador pero apagado en Ajustes
    ctx2 = _Ctx()
    ctx2.ajustes["colores_caratula"] = False
    g2 = PC.ColoresCaratula(ctx2, ctx2)
    ctx2.reproductor.pista_cambio.emit({"miniatura": "rojo"})
    assert g2.fuerza == 0 and not g2.habilitado()


def test_al_apagarlo_los_colores_se_desvanecen(app, colores):
    ctx = colores.ctx_falso
    ctx.reproductor.actual = {"miniatura": "rojo"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    bombear(app, lambda: not colores.animando)
    assert colores.fuerza > 0.95
    ctx.ajustes["colores_caratula"] = False
    colores.refrescar()
    assert colores.animando
    assert bombear(app, lambda: not colores.animando)
    assert colores.fuerza == 0


def test_con_ahorro_del_modo_gamer_salta_directo(app, colores):
    ctx = colores.ctx_falso
    ctx.gamer.ahorrando = True
    ctx.reproductor.actual = {"miniatura": "azul"}
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    assert not colores.animando and colores.fuerza == 1.0      # sin animar nada
    assert 0.55 < QColor(colores.hex_actuales()[0]).hsvHueF() < 0.7


def test_colores_mezcla_con_la_base_segun_la_fuerza(colores):
    base = [QColor("#000000")] * 3
    assert [c.name() for c in colores.colores(base)] == ["#000000"] * 3     # fuerza 0: la base
    colores.fuerza = 1.0
    assert [c.name() for c in colores.colores(base)] == colores.hex_actuales()


def test_un_solo_gestor_por_aplicacion(app):
    PC.CACHE.clear()
    ctx = _Ctx()
    assert PC.colores_de(ctx) is PC.colores_de(ctx)
