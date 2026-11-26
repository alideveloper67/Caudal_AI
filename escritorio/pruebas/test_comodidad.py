# -*- coding: utf-8 -*-
"""Comodidad del escritorio: artistas parecidos a los que escuchas, el panel «Más» de la barra, el menú lateral
plegable y que nada de los primeros segundos espere a cargar módulos. Sin red, sin motor de audio."""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from descargador import catalogo, recomendador as rc  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ artistas parecidos

AHORA = datetime(2026, 11, 25, 12)


def cancion(i, *artistas):
    return catalogo.nueva_pista(f"{i:011d}", f"Canción {i}", [{"nombre": n, "id": f"UC{n}"} for n in artistas],
                                duracion=180)


def artista(nombre):
    return {"tipo": "artista", "id": f"UC{nombre}", "titulo": nombre, "miniatura": f"http://x/{nombre}.jpg"}


class ColFalsa:
    """Solo lo que mira el recomendador."""

    def __init__(self, usadas=(), gustan=(), recientes=(), guardados=()):
        self.usadas, self.gustan, self.recientes, self.guardadas = usadas, gustan, recientes, guardados
        self.dicho = {}

    def mas_escuchadas(self, *_a):
        return list(self.usadas)

    def lista_me_gusta(self, limite=0):
        return list(self.gustan)

    def escuchado_hace_poco(self, n=0):
        return list(self.recientes)

    def guardados(self, _tipo):
        return list(self.guardadas)

    def estado(self, clave, defecto=None):
        return self.dicho.get(clave, defecto)

    def guardar_estado(self, clave, valor):
        self.dicho[clave] = valor


def test_salen_los_que_se_parecen_y_no_los_que_ya_escuchas():
    c = ColFalsa(usadas=[cancion(1, "Fuerza"), cancion(2, "Fuerza"), cancion(3, "Junior"), cancion(4, "Peso")],
                 guardados=[artista("Seguido")])
    paginas = {"UCFuerza": [artista("Junior"), artista("Marca"), artista("Seguido"), artista("Clave")],
               "UCJunior": [artista("Clave"), artista("Ivan")], "UCPeso": [artista("Ivan"), artista("Nuevo")]}
    r = rc.artistas_parecidos(c, AHORA, lambda i: ([], paginas.get(i, [])))
    nombres = [e["titulo"] for e in r]
    assert set(nombres) == {"Marca", "Clave", "Ivan", "Nuevo"}          # ni los que ya escuchas ni los que sigues
    por = {e["titulo"]: e for e in r}
    assert nombres[0] == "Clave"                                         # lo señalan dos de los tuyos
    assert por["Clave"]["subtitulo"] == "Parecido a Fuerza y Junior"
    assert por["Marca"]["subtitulo"] == "Parecido a Fuerza" and por["Marca"]["tipo"] == "artista"
    assert por["Marca"]["miniatura"] and por["Marca"]["id"] == "UCMarca"


def test_de_un_solo_artista_no_se_llena_la_lista():
    c = ColFalsa(usadas=[cancion(1, "Fuerza"), cancion(2, "Junior")])
    paginas = {"UCFuerza": [artista(f"F{i}") for i in range(20)], "UCJunior": [artista(f"J{i}") for i in range(20)]}
    nombres = [e["titulo"] for e in rc.artistas_parecidos(c, AHORA, lambda i: ([], paginas[i]))]
    assert len(nombres) == 2 * rc.TOPE_POR_SEMILLA
    assert sum(n.startswith("F") for n in nombres) == rc.TOPE_POR_SEMILLA


def test_una_vez_al_dia_y_sin_red_lo_ultimo_que_se_supo():
    c = ColFalsa(usadas=[cancion(1, "Fuerza")])
    veces = []

    def leer(i):
        veces.append(i)
        return [], [artista("A"), artista("B")]
    assert len(rc.artistas_parecidos(c, AHORA, leer)) == 2 and veces == ["UCFuerza"]
    assert len(rc.artistas_parecidos(c, AHORA + timedelta(hours=3), leer)) == 2 and len(veces) == 1
    # empezaste a escuchar a uno: ya no es «nuevo para ti»
    c.usadas = [cancion(1, "Fuerza"), cancion(2, "A")]
    assert [e["titulo"] for e in rc.artistas_parecidos(c, AHORA, leer)] == ["B"]
    # al día siguiente, sin red
    assert [e["titulo"] for e in rc.artistas_parecidos(c, AHORA + timedelta(days=1), lambda i: ([], []))] == ["B"]
    assert rc.artistas_parecidos(ColFalsa(), AHORA, leer) == []          # sin historial no se inventa nada


def test_el_mismo_artista_con_dos_fichas_cuenta_como_uno():
    a, b = cancion(1, "Junior"), cancion(2, "Junior")
    b["artistas"] = [{"nombre": "junior", "id": "UCotra"}]
    tuyos, conocidos = rc._tus_artistas(ColFalsa(usadas=[a, b]))
    assert len(tuyos) == 1 and {"id:UCJunior", "id:UCotra", "n:junior"} <= conocidos


def test_mixes_de_tus_artistas_sin_repetidos():
    from descargador.ui.paginas.inicio import mixes_de_artistas
    c = ColFalsa()
    c.artistas_frecuentes = lambda n: [{"id": "1", "nombre": "Junior H"}, {"id": "2", "nombre": "junior h"},
                                       {"id": "3", "nombre": "Yeyo"}]
    assert [e["titulo"] for e in mixes_de_artistas(c)] == ["Mix de Junior H", "Mix de Yeyo"]


# ------------------------------------------------------------------ el panel «Más»

def test_panel_mas_fichas_con_nombre_y_se_cierra_al_elegir(app):
    from descargador.ui.panel_mas import COLUMNAS, FichaMas, PanelMas
    p = PanelMas()
    hecho = []
    directa = p.agregar(FichaMas("disco", "Modo vinilo"))
    directa.clicked.connect(lambda: hecho.append("vinilo" if p.isHidden() else "encima"))
    con_menu = p.agregar(FichaMas("temporizador", "Apagar en…", cierra=False))
    for i in range(4):
        p.agregar(FichaMas("disco", f"Otra {i}"))
    ancla = QPushButton("Más")
    ancla.show()
    p.alternar(ancla)
    assert p.isVisible()
    QTest.mouseClick(con_menu, Qt.LeftButton)
    assert p.isVisible()                                      # la que abre un menú deja el panel
    QTest.mouseClick(directa, Qt.LeftButton)
    assert hecho == ["vinilo"] and p.isHidden()               # se cierra antes de hacer lo suyo
    p.alternar(ancla)
    assert p.isHidden()                                       # el mismo clic que lo cerró no lo reabre
    p._cerrado = 0
    p.alternar(ancla)
    assert p.isVisible()
    QTest.keyClick(p, Qt.Key_Escape)
    assert p.isHidden()
    for f in p.fichas:
        assert f.width() >= 100 and f.height() >= 72 and f.accessibleName()
    assert p.rejilla.columnCount() == COLUMNAS
    # se pinta en todos los estados
    directa.set_activo(True)
    assert not directa.grab().isNull()
    directa.setEnabled(False)
    assert not directa.grab().isNull()


def test_los_iconos_de_la_barra_son_grandes_y_lo_demas_esta_en_mas():
    import inspect
    from descargador.ui import barra_reproduccion as B
    codigo = inspect.getsource(B.BarraReproduccion.__init__)
    derecha = codigo[codigo.index("# ---- derecha"):codigo.index("# ---- senales")]
    assert derecha.count("= BotonIcono(") <= 6
    for n in ("bt_vinilo", "bt_mini", "bt_eq", "bt_super", "bt_temporizador", "bt_juntos", "bt_visual"):
        assert f"self.{n} = mas(FichaMas(" in derecha
    assert B.ALTO >= 88


# ------------------------------------------------------------------ menú lateral

def test_mas_de_caudal_abre_sus_fichas_y_nunca_se_aplasta(app, tmp_path):
    from PySide6.QtCore import QObject, Signal
    from descargador.ui.panel_lateral import PanelLateral

    class R(QObject):
        estado_cambio = Signal(str)
        pista_cambio = Signal(object)
        contexto, estado, actual = None, "parado", None

    class Ajustes(dict):
        def guardar(self):
            self["guardado"] = True

    class Ctx(QObject):
        listas_cambio = Signal()
        guardados_cambio = Signal()
        descargas_cambio = Signal()
        me_gusta_cambio = Signal(str, bool)

        def __init__(self):
            super().__init__()
            self.ajustes, self.reproductor = Ajustes(), R()
            self.coleccion, self.cuenta = Coleccion(tmp_path / "h.db"), {}
    ctx = Ctx()
    p = PanelLateral(ctx)
    assert p.panel_mas.isHidden() and set(p.botones) >= {"inicio", "explorar", "directorio", "estudio", "gamer"}
    p.resize(290, 420)                                        # ventana baja: nada se aplasta
    p.show()
    p.marcar({"pagina": "inicio"})
    p.bt_mas.click()
    assert p.panel_mas.isVisible() and not p.bt_mas.isChecked() and p.botones["inicio"].isChecked()
    for clave, texto, _i in p.NAV_MAS:
        f = p.botones[clave]
        assert f.texto == texto and f.isVisible() and f.height() >= 72 and f.width() >= 100
    assert p.bt_mas.height() >= 36
    ido = []
    p.ir.connect(ido.append)
    QTest.mouseClick(p.botones["gamer"], Qt.LeftButton)
    assert ido == [{"pagina": "gamer"}] and p.panel_mas.isHidden()
    p.marcar({"pagina": "estudio"})                           # se está en una de dentro: se ve cuál
    assert p.bt_mas.isChecked() and p.botones["estudio"]._activo and not p.botones["inicio"].isChecked()
    p.marcar({"pagina": "explorar"})
    assert not p.bt_mas.isChecked() and not p.botones["estudio"]._activo and p.botones["explorar"].isChecked()
    p.deleteLater()


# ------------------------------------------------------------------ los primeros segundos

def test_lo_que_no_corre_prisa_espera_a_la_precarga(app, monkeypatch):
    from descargador import fluidez
    from descargador.ui.ventana import Ventana
    hecho, cargando = [], [True]
    monkeypatch.setattr(fluidez, "precargando", lambda: cargando[0])

    from PySide6.QtCore import QObject

    class V(QObject):
        _con_calma = Ventana._con_calma
    v = V()
    v._con_calma(lambda: hecho.append(1))
    assert hecho == []
    cargando[0] = False
    tope = time.monotonic() + 3
    while not hecho and time.monotonic() < tope:
        app.processEvents()
        time.sleep(0.01)
    assert hecho == [1]
    v._con_calma(lambda: hecho.append(2))
    assert hecho == [1, 2]                                    # ya cargado: en el momento


def test_todo_lo_que_se_precarga_existe():
    import importlib.util
    from descargador import fluidez
    assert [n for n in fluidez.PRECARGA if importlib.util.find_spec(n) is None] == []
    assert len(set(fluidez.PRECARGA)) == len(fluidez.PRECARGA)


def test_boton_de_icono_marca_al_pasar(app):
    from descargador.ui.componentes import BotonIcono
    b = BotonIcono("cola", 20, "Cola", 40)
    quieto = b.grab().toImage()
    b._encima = True
    assert b.grab().toImage() != quieto
    b.setEnabled(False)
    assert not b.grab().isNull()


# ------------------------------------------------------------------ diseño de letra

def test_los_tipos_de_letra_se_leen_en_un_hilo_y_se_ponen_de_uno_en_uno(app, monkeypatch):
    from descargador.ui import tipografia_letra as T
    monkeypatch.setattr(T, "_familias", {})
    monkeypatch.setattr(T, "_leidas", {})
    assert T.lista(T.POR_DEFECTO) and not T.lista("anton")
    T.leer_todas()
    assert all(T.lista(c) for c in T.FUENTES)
    monkeypatch.setattr(T, "carpeta_fuentes", lambda: 1 / 0)      # ya no se toca el disco
    assert T.familia("anton") and T.familia("poppins")
    n = 0
    while T.calentar_una():
        n += 1
    assert n == len(T.FUENTES) - 3 and not T._leidas              # y no se queda en memoria lo ya puesto
    assert all(T._familias.values())


def test_la_intensidad_visual_se_elige_se_guarda_y_se_nota(app):
    from types import SimpleNamespace
    from descargador.ui import epica
    from descargador.ui.epica import base
    from descargador.ui.estilo_letra import Colores
    from descargador.ui.selector_letra import SelectorLetra

    class Aj(dict):
        def guardar(self):
            self["guardado"] = True
    aj = Aj()
    s = SelectorLetra(SimpleNamespace(ajustes=aj), en_escena=True)
    try:
        assert list(s.intensidades) == ["suave", "normal", "fuerte", "brutal"] and s.intensidades["normal"].isChecked()
        s.intensidades["brutal"].click()
        assert aj["letra_intensidad"] == "brutal" and aj["guardado"] and epica.intensidad() == "brutal"
        cx = epica.Lienzo(400, 200, 1, Colores("#E8577E", "#7C5CFF", "#FFB03A"), 0.4, 0.5)
        fuerte = abs(base.temblor(0.02, 10)[0])
        s.intensidades["suave"].click()
        suave = epica.Lienzo(400, 200, 1, Colores("#E8577E", "#7C5CFF", "#FFB03A"), 0.4, 0.5)
        assert cx.golpe > 0.5 > suave.golpe and fuerte > abs(base.temblor(0.02, 10)[0])
        assert cx.golpe <= 1.3
        s.restablecer()
        assert epica.intensidad() == "normal" and s.intensidades["normal"].isChecked()
        epica.fijar_intensidad("no existe")
        assert epica.intensidad() == "normal"
        s.resize(520, 500)
        s.show()
        app.processEvents()
        s.ir_a("fuentes")
        assert s.zona.verticalScrollBar().value() > 0
    finally:
        epica.fijar_intensidad("normal")
        epica.fijar(epica.POR_DEFECTO)
        s.deleteLater()


def test_las_muestras_se_pintan_por_tandas(app):
    from types import SimpleNamespace
    from descargador.ui.selector_letra import SelectorLetra
    s = SelectorLetra(SimpleNamespace(ajustes={}), en_escena=True)
    s.resize(520, 500)
    s.show()
    tope = time.monotonic() + 10
    a_la_vista = [m for m in s.epicas.muestras[:3]]
    while any(m._ultima is None for m in a_la_vista) and time.monotonic() < tope:
        app.processEvents()
        time.sleep(0.005)
    assert all(m._ultima is not None for m in a_la_vista)
    s.hide()
    s.deleteLater()
