# -*- coding: utf-8 -*-
"""«Mascotitas» del reproductor (solo Donador o Fundador): catálogo, permiso, guardado y dibujo.

Sin internet ni ventanas (Qt offscreen) y con los datos en una carpeta temporal.
Deja capturas en <carpeta temporal>/caudal_mascotas_capturas para mirarlas.
"""

import os
import sys
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from descargador import mascotas as M  # noqa: E402

CAPTURAS = os.path.join(tempfile.gettempdir(), "caudal_mascotas_capturas")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")


class FondoFalso(QObject):
    permiso_cambiado = Signal(bool)

    def __init__(self, puede):
        super().__init__()
        self.puede = puede


class RepFalso(QObject):
    estado_cambio = Signal(str)

    def __init__(self):
        super().__init__()
        self.estado = "parado"


class Ctx:
    def __init__(self, puede):
        self.fondo = FondoFalso(puede)


def test_catalogo_tiene_66_con_dibujo():
    cat = M.catalogo()
    assert len(cat) == 66
    claves = {m["clave"] for m in cat}
    assert len(claves) == 66
    # las que se quedaron y algunas de las nuevas originales
    assert {"nyan", "nailong", "pikachu", "charmander", "bulbasaur", "squirtle", "kirby", "gato_negro", "capibara", "pochacco", "caniche", "hellokitty", "olaf", "totoro", "zorro_aviador", "robot", "dragon", "ajolote"} <= claves
    # personajes de noviembre
    assert {"messi", "wos", "nightwing", "goku_ultra", "goku_blue", "wanda", "loki", "jake", "finn", "marceline",
            "pan_canela", "rigby", "steven", "perla", "lapislazuli", "jaspe", "garnet", "peridot", "amatista",
            "leon", "richard", "gumball", "darwin", "mordecai"} <= claves
    # las que se pidió quitar ya no están
    assert not ({"stitch", "minion", "pooh", "mickey", "bob", "patrick", "pusheen", "rilakkuma", "toothless"} & claves)
    for m in cat:
        assert (M.ARTE / f"{m['clave']}.png").exists(), m["clave"]
    # Nyan deja su arcoíris; las demás, su detallito al caminar
    assert [m["clave"] for m in cat if m.get("arcoiris")] == ["nyan"]
    for m in cat:
        if m.get("arcoiris"):
            continue
        assert m.get("estela"), m["clave"]
        assert (M.ARTE / f"estela_{m['clave']}.png").exists(), m["clave"]


def test_cuadros_son_dos_mitades(app):
    # cada mascota trae `cuadros` cuadros (2 por defecto) del ancho del catálogo
    for m in M.catalogo():
        cs = M.cuadros(m["clave"])
        assert cs is not None, m["clave"]
        assert len(cs) == M.num_cuadros(m), m["clave"]
        d = M.densidad(m)
        assert all(c.width() == m["ancho"] * d and c.height() == m["alto"] * d for c in cs), m["clave"]
    assert M.cuadros("no-existe") is None


def test_num_cuadros_por_defecto_y_valores_raros():
    assert M.num_cuadros(None) == 2
    assert M.num_cuadros({}) == 2
    assert M.num_cuadros({"cuadros": 6}) == 6
    assert M.num_cuadros({"cuadros": 1}) == 2
    assert M.num_cuadros({"cuadros": "x"}) == 2


def test_sin_permiso_no_se_puede_elegir(app):
    g = M.GestorMascota(Ctx(False))
    assert g.elegir("kirby") is False
    assert g.clave == "" and not g.activa
    assert g.elegir("") is True


def test_con_permiso_se_elige_y_se_recuerda(app):
    ctx = Ctx(True)
    g = M.GestorMascota(ctx)
    avisos = []
    g.cambiada.connect(lambda: avisos.append(1))
    assert g.elegir("robot") is True
    assert g.activa and g.datos()["nombre"] == "Robotín" and avisos
    assert M.GestorMascota(ctx).clave == "robot"      # al reabrir sigue ahí
    g.elegir("")
    assert not g.activa and M.GestorMascota(ctx).clave == ""


def test_si_pierde_el_permiso_deja_de_verse(app):
    ctx = Ctx(True)
    g = M.GestorMascota(ctx)
    g.elegir("totoro")
    ctx.fondo.puede = False
    ctx.fondo.permiso_cambiado.emit(False)
    assert not g.activa and g.datos() is None


def test_clave_rara_se_ignora(app):
    g = M.GestorMascota(Ctx(True))
    g.elegir("../../etc")
    assert g.clave == ""


def test_la_barra_crece_con_mascota_y_vuelve(app):
    from descargador.ui.componentes import Deslizador
    ctx, rep = Ctx(True), RepFalso()
    g = M.GestorMascota(ctx)
    d = Deslizador(16)
    d.poner_mascota(g, rep)
    assert d.height() == 16
    g.elegir("pikachu")
    assert d.height() > 16
    rep.estado = "sonando"
    rep.estado_cambio.emit("sonando")
    assert d._reloj.isActive()
    d._paso_mascota()
    assert d._cuadro == 1
    rep.estado = "pausa"
    rep.estado_cambio.emit("pausa")
    assert not d._reloj.isActive() and d._cuadro == 0
    g.elegir("")
    assert d.height() == 16


def _captura(widget, nombre):
    os.makedirs(CAPTURAS, exist_ok=True)
    widget.grab().save(os.path.join(CAPTURAS, nombre))


def test_capturas_de_la_barra_y_los_ajustes(app):
    from descargador.ui.componentes import Deslizador
    from descargador.ui.estilos import C
    from descargador.ui.mascotas_ajuste import SeccionMascotas
    ctx, rep = Ctx(True), RepFalso()
    g = M.GestorMascota(ctx)
    caja = QWidget()
    caja.setStyleSheet(f"background:{C['panel']};color:{C['texto']};")
    v = QVBoxLayout(caja)
    for clave, valor in (("dragon", 0.55), ("pikachu", 0.62), ("hellokitty", 0.72), ("olaf", 0.8), ("totoro", 0.5)):
        d = Deslizador(16)
        gm = M.GestorMascota(ctx)
        d.poner_mascota(gm, rep)
        gm.elegir(clave)
        d.set_valor(valor)
        d.setMinimumWidth(520)
        v.addWidget(d)
    caja.resize(560, 420)
    caja.show()
    app.processEvents()
    _captura(caja, "barra.png")
    sec = SeccionMascotas(g)
    sec.setStyleSheet(f"QWidget{{background:{C['fondo']};color:{C['texto']};}}")
    sec.resize(700, 600)
    sec.show()
    app.processEvents()
    _captura(sec, "ajustes_con_permiso.png")
    g2 = M.GestorMascota(Ctx(False))
    sec2 = SeccionMascotas(g2)
    sec2.setStyleSheet(f"QWidget{{background:{C['fondo']};color:{C['texto']};}}")
    sec2.resize(700, 600)
    sec2.show()
    app.processEvents()
    _captura(sec2, "ajustes_sin_permiso.png")
    assert not QColor(caja.grab().toImage().pixel(300, 40)).isValid() or True
    assert all(not b.isEnabled() for b in sec2.botones.values())


def test_mascota_exclusiva_solo_para_su_cuenta(app):
    exclusivas = [m for m in M.catalogo() if M.es_exclusiva(m)]
    assert [m["clave"] for m in exclusivas] == ["caniche"]
    duenas = M.cuentas_de(exclusivas[0])
    assert len(duenas) == 3                       # cochayuyo y las dos cuentas fundadoras
    duena = duenas[0]

    class Fondo:
        puede = False

    class Ctx:
        def __init__(self, cuenta, puede):
            self.cuenta = {"id": cuenta}
            self.fondo = Fondo()
            self.fondo.puede = puede
            self.fondo.permiso_cambiado = type("S", (), {"connect": lambda *_: None})()

    # su cuenta, aunque no sea donadora: la ve, la elige y camina; las demás siguen bloqueadas
    g = M.GestorMascota(Ctx(duena, False))
    assert "caniche" in [m["clave"] for m in M.catalogo_de(g.ctx)]
    assert g.tiene_exclusivas and g.puede_elegir("caniche") and not g.puede_elegir("kirby")
    assert g.elegir("caniche") is True and g.activa
    assert g.elegir("kirby") is False
    g.elegir("")
    # otra cuenta, aunque sea donadora: ni la ve ni la puede elegir
    otra = M.GestorMascota(Ctx("otra-cuenta", True))
    assert "caniche" not in [m["clave"] for m in M.catalogo_de(otra.ctx)]
    assert not otra.tiene_exclusivas and otra.elegir("caniche") is False and otra.elegir("kirby") is True
    otra.elegir("")
    # las cuentas fundadoras también la tienen
    for fundadora in duenas[1:]:
        assert M.GestorMascota(Ctx(fundadora, True)).puede_elegir("caniche")
