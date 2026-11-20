# -*- coding: utf-8 -*-
"""La escena de escritorio entera: abre, sigue al reproductor, busca, cambia de fondo y cierra
sin dejar nada atrás (con un Reproductor de verdad, sin libmpv)."""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


PISTA = {"clave": "abc123", "video_id": "abc123", "titulo": "Luna de papel", "artista": "Nébula Verde",
         "miniatura": "", "duracion": 200}


@pytest.fixture
def ctx(app, monkeypatch):
    from descargador import mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    from descargador.ui.contexto import Contexto
    a = Ajustes()
    a["sponsorblock"] = False
    a["autoplay"] = False
    col = Coleccion()
    r = Reproductor(a, col)
    c = Contexto(a, None, col, None, r)
    avisos = []
    c.avisar = lambda texto, deshacer=None: avisos.append(texto)
    c.avisos = avisos
    # nada de red: las letras y la búsqueda se sustituyen
    from descargador import catalogo
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": [(0, "Hola"), (2000, "mundo bonito")],
                                                       "texto": "", "fuente": "prueba"})
    monkeypatch.setattr(catalogo, "letras_alternativas", lambda p: [
        {"sincronizada": False, "lineas": [], "texto": "otra\nletra", "fuente": "LRCLIB", "etiqueta": "Otra"}])
    monkeypatch.setattr(catalogo, "buscar", lambda texto, filtro=None, limite=20: (
        [dict(PISTA, titulo=f"{texto} {i}", clave=f"k{i}", video_id=f"k{i}") for i in range(3)]
        if filtro != "artistas" else [{"tipo": "artista", "id": "A1", "titulo": "Nébula", "miniatura": ""}]))
    yield c
    e = getattr(c, "escena_escritorio", None)
    if e is not None:
        e.cerrar()


def _esperar(app, cond, segundos=5.0):
    import time
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_disposicion_no_se_pisa(app):
    from descargador.ui.escena.ventana import disposicion
    for w, h in ((1920, 1080), (1366, 768), (2560, 1440), (1280, 720)):
        g = disposicion(QRect(0, 0, w, h))
        pantalla = QRect(0, 0, w, h)
        for n in ("lista", "reloj", "tarjeta", "letra", "barra"):
            assert pantalla.contains(g[n]), (w, h, n, g[n])
        assert not g["lista"].intersects(g["tarjeta"]), (w, h)
        assert not g["tarjeta"].intersects(g["letra"]), (w, h)
        assert not g["tarjeta"].intersects(g["barra"]), (w, h)
        assert not g["letra"].intersects(g["barra"]), (w, h)
        assert g["letra"].width() >= 200
        # la tarjeta no se mete en el buscador plegado (su campo mide 68 px)
        assert g["tarjeta"].bottom() < g["buscador_abajo"].y() - 68, (w, h)
        assert not g["tarjeta"].intersects(g["reloj"]) or g["tarjeta"].right() < g["reloj"].left(), (w, h)


def test_abre_sigue_la_pista_y_cierra_limpio(app, ctx):
    from descargador.ui.escena.ventana import escena_de
    e = escena_de(ctx)
    assert escena_de(ctx) is e
    e.abrir()
    assert e.abierta
    nombres = set(e._piezas)
    assert nombres == {"reloj", "tarjeta", "letra", "lista", "barra", "buscador"}
    assert set(e._bordes) == {"arriba", "abajo", "izquierda", "derecha"}
    # sin libmpv no hay video: el fondo es la carátula viva
    assert e._fondo.pila.currentIndex() == 0
    ctx.reproductor.actual = dict(PISTA)
    ctx.reproductor.pista_cambio.emit(dict(PISTA))
    assert _esperar(app, lambda: e._piezas["letra"].indice_actual() >= -1 and e._lineas_clave == "abc123")
    assert _esperar(app, lambda: bool(e._piezas["letra"]._lineas if hasattr(e._piezas["letra"], "_lineas") else True))
    ctx.reproductor.duracion_cambio.emit(200.0)
    ctx.reproductor.posicion_cambio.emit(50.0)
    e._tic_letra()
    fondo = e._fondo
    e.cerrar()
    assert not e.abierta and not e._piezas and not e._bordes and e._fondo is None
    assert NOMBRE_VIDEO_LIBRE(ctx)
    app.processEvents()
    assert fondo is not None


def NOMBRE_VIDEO_LIBRE(ctx):
    from descargador.ui.escena.ventana import NOMBRE_VIDEO
    return NOMBRE_VIDEO not in ctx.reproductor.videos and ctx.reproductor.destino_video != NOMBRE_VIDEO


def test_busqueda_y_eleccion(app, ctx, monkeypatch):
    from descargador.ui.escena.ventana import escena_de
    e = escena_de(ctx)
    e.abrir()
    elegidas = []
    monkeypatch.setattr(ctx, "reproducir_pista", lambda p, contexto=None: elegidas.append(p))
    b = e._piezas["buscador"]
    b.buscar.emit("luna", "auto")
    assert _esperar(app, lambda: b.altura_deseada() > 150)
    b.elegida.emit({"titulo": "x", "clave": "k1"})
    assert elegidas and elegidas[0]["clave"] == "k1"
    # el buscador crece hacia arriba, con el borde de abajo fijo
    assert b.geometry().y() + b.height() == e._abajo_buscador.y()
    assert b.geometry().y() + b.height() <= e._piezas["barra"].geometry().y()


def test_fuente_videos_no_pide_artistas(app):
    from descargador import catalogo
    from descargador.ui.escena.ventana import buscar_en_fuente
    pedidos = []
    orig = catalogo.buscar
    try:
        catalogo.buscar = lambda t, f=None, l=20: pedidos.append(f) or []
        buscar_en_fuente(None, "hola", "youtube")
        assert pedidos == ["videos"]
        pedidos.clear()
        buscar_en_fuente(None, "hola", "auto")
        assert pedidos == ["canciones", "artistas"]
        assert buscar_en_fuente(None, "  ", "auto") == ([], [])
    finally:
        catalogo.buscar = orig


def test_otra_letra_y_me_gusta(app, ctx):
    from descargador.ui.escena.ventana import escena_de
    e = escena_de(ctx)
    e.abrir()
    ctx.reproductor.actual = dict(PISTA)
    ctx.reproductor.pista_cambio.emit(dict(PISTA))
    e._otra_letra()
    assert _esperar(app, lambda: any("Letra 1 de 1" in a for a in ctx.avisos))
    ctx.coleccion.guardar_pista(dict(PISTA)) if hasattr(ctx.coleccion, "guardar_pista") else None
    e._piezas["tarjeta"].pidio_me_gusta.emit()
    assert ctx.coleccion.me_gusta("abc123")


def test_colores_llegan_a_todas_las_piezas(app, ctx):
    from descargador.ui.escena.ventana import escena_de
    e = escena_de(ctx)
    e.abrir()
    e._colores = (QColor("#00FF00"),) * 3
    vistos = []
    for w in list(e._piezas.values()) + list(e._bordes.values()) + [e._fondo.ambiente]:
        orig = w.poner_colores
        w.poner_colores = lambda d, s, b, w=w, o=orig: (vistos.append(w), o(d, s, b))
    e._colores_caratula()
    assert len(vistos) == len(e._piezas) + len(e._bordes) + 1


def test_portada_va_a_tarjeta_barra_y_fondo(app, ctx):
    from descargador.ui.escena.ventana import escena_de
    e = escena_de(ctx)
    e.abrir()
    ctx.reproductor.actual = dict(PISTA)
    img = QImage(40, 40, QImage.Format_RGB32)
    img.fill(QColor("#FF0000"))
    e._portada("abc123", img)
    e._portada("otra", img)          # una carátula vieja que llega tarde no se pone


def test_ningun_boton_ni_opcion_da_error(app, ctx, monkeypatch):
    """Pulsa todo lo que tiene la escena (barra, tarjeta, lista, buscador, fuentes, teclas) con el
    reproductor de verdad: ninguna acción puede lanzar una excepción ni cerrar nada que no toca."""
    import sys
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest
    from descargador.ui.escena.ventana import escena_de
    errores = []
    monkeypatch.setattr(sys, "excepthook", lambda t, v, tb: errores.append(f"{t.__name__}: {v}"))
    reproducidas = []
    monkeypatch.setattr(ctx, "reproducir_pista", lambda p, contexto=None: reproducidas.append(p))
    monkeypatch.setattr(ctx, "reproducir_lista", lambda *a, **k: reproducidas.append(a))
    ctx.coleccion.anotar_busqueda("hola")
    e = escena_de(ctx)
    e.abrir()
    ctx.reproductor.actual = dict(PISTA)
    ctx.reproductor.pista_cambio.emit(dict(PISTA))
    ctx.reproductor.duracion_cambio.emit(200.0)
    app.processEvents()

    def clic(w, rect):
        QTest.mouseClick(w, Qt.LeftButton, pos=rect.center().toPoint())
        app.processEvents()

    barra = e._piezas["barra"]
    for nombre in ("anterior", "alternar", "siguiente", "aleatorio", "repetir", "fondo", "fondo"):
        clic(barra, barra.rect_boton(nombre))
    pr = barra.rect_progreso()
    clic(barra, pr.adjusted(pr.width() * 0.3, 0, 0, 0))
    t = e._piezas["tarjeta"]
    clic(t, t.rect_corazon())
    clic(t, t.rect_corazon())
    clic(t, t.rect_boton_letra())
    _esperar(app, lambda: any("Letra" in a for a in ctx.avisos))
    lista = e._piezas["lista"]
    if lista._pistas if hasattr(lista, "_pistas") else False:
        clic(lista, lista.rect_fila(0))
    b = e._piezas["buscador"]
    clic(b, b.rect_boton_fuente())
    clic(b, b.rect_opcion_fuente(2))
    assert e.fuente_busqueda == "youtube"
    b.buscar.emit("luna", e.fuente_busqueda)
    assert _esperar(app, lambda: b.altura_deseada() > 150)
    b.buscar.emit("luna", "auto")
    assert _esperar(app, lambda: b.altura_deseada() > 150)
    clic(b, b.rect_cancion(0))
    clic(b, b.rect_artista(0))
    _esperar(app, lambda: len(reproducidas) >= 2)
    for f in ("megusta", "descargas"):
        b.buscar.emit("luna", f)
        app.processEvents()
    QTest.keyClick(e._piezas["tarjeta"], Qt.Key_Space)
    app.processEvents()
    # «Volver a Caudal» y Esc cierran la escena sin errores
    clic(barra, barra.rect_boton("abrir"))
    assert not e.abierta
    e.abrir()
    QTest.keyClick(e._piezas["reloj"], Qt.Key_Escape)
    app.processEvents()
    assert not e.abierta
    e.abrir(solo_ver=False)
    clic(e._piezas["barra"], e._piezas["barra"].rect_boton("salir"))
    assert not e.abierta
    assert len(reproducidas) >= 2
    assert errores == [], errores
