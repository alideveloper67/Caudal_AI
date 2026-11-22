# -*- coding: utf-8 -*-
"""Añadir canciones a una lista propia con la página abierta: la página NO se rehace (el buscador
y sus resultados siguen ahí, la vista no salta) y cada canción añadida aparece como una fila nueva.

Sin ventanas reales (Qt offscreen) y con los datos en una carpeta temporal.
"""

import os
import sys
import tempfile
import time
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEvent, QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from descargador.coleccion import Coleccion  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet(monkeypatch):
    from descargador import catalogo
    from descargador.ui import imagenes
    leer = imagenes._leer
    monkeypatch.setattr(imagenes, "_leer", lambda url: leer(url) if "://" not in (url or "") else b"")
    monkeypatch.setattr(catalogo, "radio", lambda *a, **k: {"pistas": []})
    monkeypatch.setattr(catalogo, "buscar", lambda *a, **k: [])


def pista(i):
    return {"clave": f"yt:{i:011d}", "video_id": f"{i:011d}", "titulo": f"Canción {i}",
            "artista": "Ana", "miniatura": "", "duracion": 100}


class CtxFalso(QObject):
    aviso = Signal(str)
    listas_cambio = Signal()
    me_gusta_cambio = Signal()
    descargas_cambio = Signal()
    guardados_cambio = Signal()

    def __init__(self, col):
        super().__init__()
        self.coleccion = col
        self.reproductor = MagicMock()
        self.ventana = None
        self.ajustes = {"carpeta": ""}

    def navegar(self, d):
        pass

    def anadir_a_lista(self, pistas, lista_id):
        self.coleccion.agregar_a_lista(lista_id, pistas)
        self.listas_cambio.emit()

    def reproducir_pista(self, p):
        pass

    def menu_pista(self, *a, **k):
        pass


def _asentar(app):
    for _ in range(15):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        time.sleep(0.01)


def _pagina(tmp_path, app, n):
    from descargador.ui.paginas.coleccion import PaginaColeccion
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Para el viaje")
    if n:
        col.agregar_a_lista(lid, [pista(i) for i in range(n)])
    pag = PaginaColeccion(ctx, {"pagina": "mi_lista", "id": lid})
    pag.resize(1000, 700)
    pag.show()
    _asentar(app)
    return pag, ctx, col, lid


def test_anadir_desde_el_buscador_no_rehace_la_pagina(tmp_path, app):
    pag, ctx, col, lid = _pagina(tmp_path, app, 30)
    buscador, lista, cuenta = pag.e_buscar, pag.lista, pag._et_cuenta
    buscador.setText("reguetón")                 # lo que el usuario ya escribió
    pag._t_buscar.stop()                         # sus resultados se ponen a mano abajo
    pag._mostrar_sugeridas([pista(100), pista(101), pista(102)], "")
    _asentar(app)
    pag.verticalScrollBar().setValue(pag.verticalScrollBar().maximum())
    barra = pag.verticalScrollBar().value()
    filas_antes = len(lista.filas)

    botones = [b for b in pag.findChildren(QPushButton) if b.text() == "Añadir"]
    assert len(botones) == 3
    botones[0].click()
    _asentar(app)

    # la misma página: mismo buscador (con su texto), misma lista, mismas filas de antes
    assert pag.e_buscar is buscador and buscador.text() == "reguetón"
    assert pag.lista is lista and pag._et_cuenta is cuenta
    assert len(lista.filas) == filas_antes + 1           # una fila nueva por canción añadida
    assert lista.pistas[-1]["clave"] == pista(100)["clave"]
    assert cuenta.text().startswith("31 canciones")
    assert botones[0].text() == "Añadida" and not botones[0].isEnabled()
    assert botones[1].text() == "Añadir" and botones[1].isEnabled()
    # la vista no subió
    assert pag.verticalScrollBar().value() >= barra

    botones[1].click()
    botones[2].click()
    _asentar(app)
    assert len(lista.filas) == filas_antes + 3
    assert cuenta.text().startswith("33 canciones")


def test_deshacer_pone_al_dia_sin_rehacer_y_vuelve_el_boton(tmp_path, app):
    pag, ctx, col, lid = _pagina(tmp_path, app, 5)
    lista = pag.lista
    pag._mostrar_sugeridas([pista(50)], "")
    _asentar(app)
    b = next(b for b in pag.findChildren(QPushButton) if b.text() == "Añadir")
    b.click()
    _asentar(app)
    assert b.text() == "Añadida"
    col.quitar_de_lista(lid, pista(50)["clave"])         # «Deshacer»
    ctx.listas_cambio.emit()
    _asentar(app)
    assert pag.lista is lista and len(lista.pistas) == 5
    assert b.text() == "Añadir" and b.isEnabled()
    assert pag._et_cuenta.text().startswith("5 canciones")


def test_primera_cancion_en_una_lista_vacia(tmp_path, app):
    pag, ctx, col, lid = _pagina(tmp_path, app, 0)
    assert pag.lista is None and pag._w_vacia is not None
    buscador = pag.e_buscar
    buscador.setText("algo")
    pag._t_buscar.stop()
    pag._mostrar_sugeridas([pista(7)], "")
    _asentar(app)
    next(b for b in pag.findChildren(QPushButton) if b.text() == "Añadir").click()
    _asentar(app)
    assert pag.e_buscar is buscador and buscador.text() == "algo"
    assert pag.lista is not None and len(pag.lista.filas) == 1
    assert pag._w_vacia is None
    assert pag._et_cuenta.text().startswith("1 canción")


def test_cambiar_el_nombre_si_rehace(tmp_path, app):
    pag, ctx, col, lid = _pagina(tmp_path, app, 3)
    vieja = pag._et_cuenta
    col.editar_lista(lid, "Nombre nuevo", "")
    ctx.listas_cambio.emit()
    _asentar(app)
    assert pag.titulo == "Nombre nuevo"
    assert pag._et_cuenta is not vieja


def test_orden_por_titulo_sigue_ordenado_al_anadir(tmp_path, app):
    pag, ctx, col, lid = _pagina(tmp_path, app, 3)
    pag.orden = "titulo"
    pag._aplicar_orden()
    lista = pag.lista
    col.agregar_a_lista(lid, [{**pista(9), "titulo": "AAA primera"}])
    ctx.listas_cambio.emit()
    _asentar(app)
    assert pag.lista is lista
    assert lista.pistas[0]["titulo"] == "AAA primera"
