# -*- coding: utf-8 -*-
"""Presentación «Somos 100»: recorre sus cinco diapositivas, aparece solo al llegar a 100 y
una sola vez. Qt offscreen y red simulada (nunca red real)."""

import io
import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app, tmp_path, monkeypatch):
    # nunca los ajustes reales de la persona: una carpeta de datos temporal
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador.config import Ajustes
    w = QWidget()
    w.resize(1280, 800)
    w.ajustes = Ajustes()
    w.en_completa = False
    w._saliendo = False
    w.ctx = None
    w.show()
    yield w
    w.close()


@pytest.fixture
def red_simulada(monkeypatch):
    """Sustituye en_segundo_plano: ejecuta la función en el mismo hilo y devuelve lo que la prueba diga."""
    from descargador import hilos
    llamadas = []
    estado = {"resultado": None, "error": None}

    def falso(funcion, *args, ok=None, error=None, dueno=None, **kwargs):
        llamadas.append(funcion)
        if estado["error"] is not None:
            if error:
                error(estado["error"])
            return None
        if ok:
            ok(estado["resultado"])
        return None

    monkeypatch.setattr(hilos, "en_segundo_plano", falso)

    def ni_una_peticion(*_a, **_k):
        raise AssertionError("no debe haber red real en las pruebas")

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", ni_una_peticion)
    return llamadas, estado


def test_textos_del_guion():
    from descargador.ui import presentacion_100 as P
    titulos = [d["titulo"] for d in P.DIAPOSITIVAS]
    assert titulos[:2] == ["Somos 100", "Gracias por confiar en Caudal"]
    assert titulos[-4:] == ["Todo lo que Caudal te ofrece", "Lo nuevo que vas a disfrutar",
                            "Lo que viene: la comunidad de Caudal", "Comparte Caudal con el mundo"]
    # el recorrido con demostraciones: cada una tiene su demo registrada
    from descargador.ui.demos_presentacion import DEMOS
    demos = [d["demo"] for d in P.DIAPOSITIVAS if d["tipo"] == "demo"]
    assert len(demos) >= 8 and all(k in DEMOS for k in demos)
    assert len(P.BLOQUES) == 6
    assert [t for t, _p in P.BLOQUES] == ["Escucha", "Descubre", "Juntos", "Hazlo tuyo", "Vive tu música",
                                          "Comparte y cuida lo tuyo"]
    assert P.DIAPOSITIVAS[0]["texto"] == "100 personas eligieron Caudal para acompañar su música. Gracias por estar aquí."
    assert len(P.NOVEDADES) == 9
    assert P.SITIO == "https://caudal-musica.netlify.app"
    assert P.TEXTO_COMPARTIR == "Escucho mi música con Caudal 🎵 Únete: https://caudal-musica.netlify.app"


def test_recorre_las_cinco_diapositivas(app, ventana):
    from descargador.ui.presentacion_100 import Presentacion100
    d = Presentacion100(ventana)
    d.show()
    QApplication.processEvents()
    for i in range(d.n):
        d.ir_a(i, animar=False)
        d.avanzar(3.0)
        assert d.indice == i
        d.grab()                                  # pinta la diapositiva sin errores
        assert d.bt_sig.isVisible() == (i < d.n - 1)
        assert d.bt_seguir.isVisible() == (i == d.n - 1)
        assert d.bt_copiar.isVisible() == (i == d.n - 1)
    # el contador termina en 100 y la explosión sale una sola vez
    d.ir_a(0, animar=False)
    d.avanzar(3.0)
    assert int(round(d._cont)) == 100
    assert d._exploto
    # navegación con teclado: izquierda vuelve, derecha avanza
    d.ir_a(2, animar=False)
    QTest.keyClick(d, Qt.Key_Left)
    d.avanzar(1.0)
    assert d.indice == 1
    QTest.keyClick(d, Qt.Key_Right)
    d.avanzar(1.0)
    assert d.indice == 2
    d.close()


def test_rejilla_cabe_en_1280x720_sin_desplazamiento(app, ventana):
    from descargador.ui.presentacion_100 import Presentacion100
    ventana.resize(1280, 720)
    d = Presentacion100(ventana)
    d.show()
    d.setGeometry(0, 0, 1280, 720)
    from descargador.ui.presentacion_100 import DIAPOSITIVAS
    i = next(k for k, x in enumerate(DIAPOSITIVAS) if x["tipo"] == "rejilla")
    L = d._layout(i)
    fs = L["fs"]
    fin = L["y_abajo"] + L["grid"]["total"]
    assert fin <= d.height() - 100 * fs + 0.5
    assert L["grid"]["f_ch"].pixelSize() >= 12
    assert len(L["grid"]["bloques"]) == 6
    # y cada demostración cabe entera bajo su texto
    for k, x in enumerate(DIAPOSITIVAS):
        if x["tipo"] == "demo":
            Ld = d._layout(k)
            assert Ld["y_abajo"] + Ld["demo"][1] <= d.height() - 80 * fs + 0.5, x["demo"]
    d.close()


def test_copiar_enlace_y_compartir(app, ventana, monkeypatch):
    from descargador.ui import presentacion_100 as P
    abiertos = []
    monkeypatch.setattr(P.QDesktopServices, "openUrl", lambda url: abiertos.append(url.toString()))
    avisos = []

    class Ctx:
        def avisar(self, texto, deshacer=None):
            avisos.append(texto)

    d = P.Presentacion100(ventana, Ctx())
    d.show()
    d._copiar()
    assert QApplication.clipboard().text() == P.SITIO
    assert avisos[-1] == "Enlace copiado"
    d._compartir()
    assert QApplication.clipboard().text() == P.TEXTO_COMPARTIR
    assert abiertos == [P.SITIO]
    d.close()


def test_total_99_no_abre(app, ventana, red_simulada, monkeypatch):
    from descargador.ui import presentacion_100 as P
    llamadas, estado = red_simulada
    estado["resultado"] = 99
    abiertas = []
    original = P._abrir
    monkeypatch.setattr(P, "_abrir", lambda v: abiertas.append(v) or original(v))
    P.revisar_hito_100(ventana)
    assert len(llamadas) == 1
    assert abiertas == []
    assert not ventana.ajustes.get(P.CLAVE_VISTA)


def test_total_100_abre_y_marca_vista(app, ventana, red_simulada):
    from descargador.config import Ajustes
    from descargador.ui import presentacion_100 as P
    llamadas, estado = red_simulada
    estado["resultado"] = 100
    P.revisar_hito_100(ventana)
    assert len(llamadas) == 1
    dialogos = [w for w in ventana.findChildren(P.Presentacion100)]
    assert len(dialogos) == 1
    assert dialogos[0].isVisible()
    assert ventana.ajustes.get(P.CLAVE_VISTA) is True
    # queda guardada en disco: otra sesión ya no la vuelve a pedir ni a mostrar
    assert Ajustes().get(P.CLAVE_VISTA) is True


def test_ya_vista_no_pide_nada(app, ventana, red_simulada):
    from descargador.ui import presentacion_100 as P
    llamadas, estado = red_simulada
    estado["resultado"] = 500
    ventana.ajustes[P.CLAVE_VISTA] = True
    P.revisar_hito_100(ventana)
    assert llamadas == []
    assert ventana.findChildren(P.Presentacion100) == []


def test_sin_red_no_hace_nada(app, ventana, red_simulada):
    from descargador.ui import presentacion_100 as P
    llamadas, estado = red_simulada
    estado["error"] = OSError("sin red")
    P.revisar_hito_100(ventana)
    assert len(llamadas) == 1
    assert ventana.findChildren(P.Presentacion100) == []
    assert not ventana.ajustes.get(P.CLAVE_VISTA)


def test_pedir_total_usa_la_cabecera_publica_y_cuerpo_vacio(monkeypatch):
    import urllib.request
    from descargador.ui import presentacion_100 as P
    capturada = {}

    def falsa_peticion(peticion, timeout=None):
        capturada["url"] = peticion.full_url
        capturada["cuerpo"] = peticion.data
        capturada["cabeceras"] = {k.lower(): v for k, v in peticion.header_items()}
        capturada["timeout"] = timeout
        return io.BytesIO(b"98")

    monkeypatch.setattr(urllib.request, "urlopen", falsa_peticion)
    assert P.pedir_total() == 98
    assert capturada["url"] == P.SUPABASE_TOTAL
    assert capturada["cuerpo"] == b"{}"
    assert capturada["timeout"] == 8
    assert capturada["cabeceras"]["apikey"] == P.CLAVE_PUBLICA
    assert capturada["cabeceras"]["authorization"] == "Bearer " + P.CLAVE_PUBLICA


def test_enganche_en_ventana_principal():
    """ventana.py abre primero «Somos 100» y, al cerrarla, las novedades de la versión."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "descargador", "ui", "ventana.py")
    texto = open(ruta, encoding="utf-8").read()
    assert "QTimer.singleShot(2500, self._presentaciones_inicio)" in texto
    assert "revisar_hito_100(self, despues=self._avisar_novedades)" in texto


def test_orden_primero_el_agradecimiento(app, ventana, red_simulada):
    from descargador.ui import presentacion_100 as P
    llamadas, estado = red_simulada
    despues = []
    # 99 personas: no hay agradecimiento y las novedades siguen enseguida
    estado["resultado"] = 99
    P.revisar_hito_100(ventana, despues=lambda: despues.append("novedades"))
    assert despues == ["novedades"]
    # sin red: también siguen las novedades
    despues.clear()
    estado["resultado"], estado["error"] = None, RuntimeError("sin red")
    P.revisar_hito_100(ventana, despues=lambda: despues.append("novedades"))
    assert despues == ["novedades"]
    # 100: primero la presentación; las novedades esperan a que se cierre, y salen una sola vez
    despues.clear()
    estado["resultado"], estado["error"] = 100, None
    P.revisar_hito_100(ventana, despues=lambda: despues.append("novedades"))
    dialogos = [w for w in ventana.findChildren(P.Presentacion100) if w.isVisible()]
    assert len(dialogos) == 1 and despues == []
    dialogos[0].done(0)
    QApplication.processEvents()
    assert despues == ["novedades"]
    # ya vista: directo a las novedades
    despues.clear()
    P.revisar_hito_100(ventana, despues=lambda: despues.append("novedades"))
    assert despues == ["novedades"]

