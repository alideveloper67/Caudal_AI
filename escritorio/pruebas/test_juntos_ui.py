# -*- coding: utf-8 -*-
"""La pantalla de «Escuchar juntos» y el botón de la barra, sin ventanas a la
vista (Qt offscreen). La sala es real: un segundo cliente Python entra en ella.
"""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QWidget  # noqa: E402

from descargador import juntos as J  # noqa: E402
from pruebas.test_juntos import ReproductorFalso, _hay_red  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class ReproductorQt(QObject):
    """Lo que ControlReproductor usa del Reproductor de verdad."""
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    cola_cambio = Signal()

    def __init__(self):
        super().__init__()
        self.actual = None
        self._posicion = 0.0
        self.estado = "parado"
        self.cargas = []

    def _cargar(self, pista, inicio=0.0, pausado=False):
        self.cargas.append((pista, inicio, pausado))
        self.actual = pista
        self._posicion = inicio
        self.estado = "pausa" if pausado else "sonando"
        self.pista_cambio.emit(pista)
        self.estado_cambio.emit(self.estado)

    def buscar(self, s):
        self._posicion = s

    def pausar(self):
        self.estado = "pausa"
        self.estado_cambio.emit(self.estado)

    def reanudar(self):
        self.estado = "sonando"
        self.estado_cambio.emit(self.estado)


class CtxFalso(QObject):
    aviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.reproductor = ReproductorQt()
        self.cuenta = {"nombre": "Ana PC", "usuario": "ana"}
        self.ventana = QWidget()
        self.ventana.resize(900, 600)
        self.avisos = []
        self.aviso.connect(self.avisos.append)


def esperar(app, cond, que, maximo=30):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.03)


def test_control_reproductor_convierte_la_pista(app):
    r = ReproductorQt()
    c = J.ControlReproductor(r)
    c.cargar({"video_id": "dQw4w9WgXcQ", "titulo": "T", "artista": "A, B", "duracion": 213},
             inicio_ms=42500, pausado=True)
    p, inicio, pausado = r.cargas[-1]
    assert p["clave"] == "yt:dQw4w9WgXcQ" and [a["nombre"] for a in p["artistas"]] == ["A", "B"]
    assert inicio == 42.5 and pausado is True
    assert r.contexto["tipo"] == "juntos" and c.posicion_ms == 42500 and not c.sonando


def test_codigo_malo_se_explica(app):
    from descargador.ui.paginas.juntos import PaginaJuntos
    ctx = CtxFalso()
    pag = PaginaJuntos(ctx)
    pag.campo_codigo.setText("hola")
    pag._unirse()
    assert "no es válido" in pag.et_error.text()


@pytest.mark.skipif(not _hay_red(), reason="sin internet hasta Supabase")
def test_pantalla_con_sala_real(app):
    from descargador.ui.paginas.juntos import PaginaJuntos, gestor
    ctx = CtxFalso()
    ctx.reproductor._cargar({"video_id": "dQw4w9WgXcQ", "titulo": "Prueba UI", "artista": "Caudal",
                             "duracion": 213, "clave": "yt:dQw4w9WgXcQ"}, 10.0)
    pag = PaginaJuntos(ctx)
    pag.resize(560, 640)
    pag.show()
    assert pag.campo_nombre.text() == "Ana PC"
    pag.bt_crear.click()
    g = gestor(ctx)
    esperar(app, lambda: g.sala is not None, "la sala abre")
    s = g.sala
    assert pag.pilas.currentIndex() == 1 and pag.et_codigo.text() == s.codigo
    assert "Tú pones la música" in pag.et_estado.text()
    assert "Prueba UI" in pag.et_suena.text()

    # un invitado (otro "aparato") entra con el enlace
    bucle = J.BucleSimple()
    b = ReproductorFalso()
    inv = J.SalaJuntos(J.codigo_de_texto(s.enlace), b, "Beto", "beto", despachar=bucle.despachar)
    abierto = []
    inv.al_abierta = abierto.append
    bucle.salas.append(inv)
    try:
        bucle.llamar(inv.abrir)
        esperar(app, lambda: pag.lista.count() == 2, "Beto aparece en la lista")
        textos = [pag.lista.item(i).text() for i in range(pag.lista.count())]
        assert any("Ana PC" in t and "pone la música" in t for t in textos)
        assert any("Beto" in t for t in textos)
        esperar(app, lambda: (b.pista or {}).get("video_id") == "dQw4w9WgXcQ", "Beto la carga")

        # reaccion de Beto: flota en la pantalla
        antes = len(pag.findChildren(QLabel))
        bucle.llamar(lambda: inv.reaccionar("👏"))
        esperar(app, lambda: any(l.text() == "👏" for l in pag.findChildren(QLabel)),
                "el emoji flota")
        assert len(pag.findChildren(QLabel)) > antes

        # pasar el mando a Beto
        s.ceder_anfitrion(inv.mi_id)
        esperar(app, lambda: inv.soy_anfitrion, "Beto recibe el mando")
        app.processEvents()
        assert "Pone la música Beto" in pag.et_estado.text()
    finally:
        bucle.llamar(inv.salir)
        bucle.parar()
    g.salir()
    app.processEvents()
    assert pag.pilas.currentIndex() == 0


def test_boton_de_la_barra_abre_la_sala(app, monkeypatch):
    from descargador.ui import barra_reproduccion as B
    from descargador.ui.paginas import juntos as PJ
    abiertas = []
    monkeypatch.setattr(PJ, "abrir_ventana", lambda ctx, padre=None: abiertas.append(ctx))

    class Falsa:
        def __init__(self):
            self.ctx = CtxFalso()
            self.bt_juntos = type("B", (), {"set_activo": lambda *a, **k: None,
                                            "setToolTip": lambda *a: None})()

        def window(self):
            return None

    f = Falsa()
    B.BarraReproduccion._abrir_juntos(f)
    assert abiertas == [f.ctx]
    f._pintar_juntos = lambda g: B.BarraReproduccion._pintar_juntos(f, g)
    PJ.gestor(f.ctx).cambio.emit()


def test_barra_real_lleva_el_boton(app, monkeypatch):
    """La barra de verdad se construye y su botón abre «Escuchar juntos»."""
    from descargador.ui import barra_reproduccion as B
    from descargador.ui.paginas import juntos as PJ

    class Rep(ReproductorQt):
        posicion_cambio = Signal(float)
        duracion_cambio = Signal(float)
        calidad_cambio = Signal(object)
        modo_cambio = Signal(str)
        temporizador_cambio = Signal(object)

        def __init__(self):
            super().__init__()
            self.volumen, self.aleatorio, self.repetir, self.modo = 70, False, "no", "audio"

        def anterior(self):
            pass

        siguiente = alternar = anterior

    class Ctx(CtxFalso):
        me_gusta_cambio = Signal(str, bool)
        sonido_cambio = Signal()

        def __init__(self):
            super().__init__()
            self.reproductor = Rep()
            self.ajustes = {"super_volumen": 0}

    abiertas = []
    monkeypatch.setattr(PJ, "abrir_ventana", lambda ctx, padre=None: abiertas.append(ctx))
    ctx = Ctx()
    barra = B.BarraReproduccion(ctx)
    barra.bt_juntos.click()
    assert abiertas == [ctx] and barra.bt_juntos.toolTip() == "Escuchar juntos"
    PJ.gestor(ctx).cambio.emit()
