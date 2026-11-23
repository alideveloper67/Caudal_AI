# -*- coding: utf-8 -*-
"""El mini reproductor no deja ningún mpv de video vivo si no hace falta.

Fallo real (22/11/2026): con una canción sonando, abrir el mini y volver a la ventana grande
dejaba Caudal sonando y pintando pero sin aceptar clics. El mini creaba un mpv de video
(force_window) cuya ventana, de otro hilo, era hija de la ventanita: Windows une la cola de
ratón/teclado de los dos hilos y, si ese mpv se cuelga con la ventanita oculta, la interfaz
entera deja de recibir entrada."""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class ReproductorFalso(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)
    modo_cambio = Signal(str)
    video_listo = Signal(object)

    def __init__(self, modo="audio"):
        super().__init__()
        self.modo = modo
        self.actual = {"titulo": "ven dale", "artista": "Doony Graff", "miniatura": ""}
        self.disponible = True
        self.destino_video = "principal"
        self._traspaso = None
        self.videos = {}
        self.registros = 0
        self.soltados = 0
        self.movidos = []

    def registrar_video(self, nombre, wid):
        if nombre not in self.videos:
            self.registros += 1
            self.videos[nombre] = object()
        return self.videos[nombre]

    def soltar_video(self, nombre):
        if self.videos.pop(nombre, None) is not None:
            self.soltados += 1
        if self.destino_video == nombre:
            self.destino_video = "principal"

    def mover_video(self, destino):
        self.movidos.append(destino)
        self.destino_video = destino

    def buscar(self, _s): pass
    def anterior(self): pass
    def siguiente(self): pass
    def alternar(self): pass


class Ctx:
    def __init__(self, r, encima=True):
        self.reproductor = r
        self.ajustes = {"mini_encima": encima}


def _mini(r, encima=True):
    from descargador.ui.video import MiniReproductor
    return MiniReproductor(Ctx(r, encima))


def test_con_una_cancion_no_se_crea_ningun_mpv_de_video(app):
    r = ReproductorFalso("audio")
    m = _mini(r)
    m.abrir()
    assert r.registros == 0 and m.motor is None
    assert m.pila.currentIndex() == 1          # la portada
    m.expandir.emit()
    m.close()
    assert not m.isVisible() and r.videos == {}


def test_abrir_y_volver_varias_veces_con_cancion(app):
    r = ReproductorFalso("audio")
    m = _mini(r)
    for _ in range(5):
        m.abrir()
        m.close()
    assert r.registros == 0 and r.videos == {}


def test_con_video_el_mpv_vive_solo_mientras_el_mini_lo_muestra(app):
    r = ReproductorFalso("video")
    m = _mini(r)
    m.abrir()
    assert r.registros == 1 and r.movidos == ["mini"] and r.destino_video == "mini"
    # volver a la grande: el cierre espera el traspaso y luego suelta el mpv del mini
    m.close()
    assert r.movidos[-1] == "principal"
    m.close()                                   # el traspaso ya terminó (_traspaso es None)
    assert not m.isVisible()
    assert r.soltados == 1 and "mini" not in r.videos and m.motor is None


def test_reabrir_con_video_crea_una_pantalla_nueva(app):
    r = ReproductorFalso("video")
    m = _mini(r)
    m.abrir()
    m.close(); m.close()
    m.abrir()
    assert r.registros == 2 and r.destino_video == "mini"


def test_cambiar_siempre_encima_suelta_el_mpv_viejo(app):
    r = ReproductorFalso("video")
    m = _mini(r, encima=True)
    m.abrir()
    assert r.registros == 1
    m.ctx.ajustes["mini_encima"] = False
    m.abrir()                                   # rehace la ventana nativa: el mpv viejo no sirve
    assert r.soltados == 1 and r.registros == 2


def test_mismas_banderas_no_rehacen_la_ventana(app, monkeypatch):
    from descargador.ui.video import MiniReproductor
    r = ReproductorFalso("audio")
    m = _mini(r)
    llamadas = []
    original = MiniReproductor.setWindowFlags
    monkeypatch.setattr(MiniReproductor, "setWindowFlags",
                        lambda self, f: (llamadas.append(f), original(self, f)))
    for _ in range(3):
        m.abrir()
        m.close()
    assert llamadas == []
