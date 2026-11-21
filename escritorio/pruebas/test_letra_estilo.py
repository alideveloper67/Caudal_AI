# -*- coding: utf-8 -*-
"""Estilo y tipo de letra de la letra de las canciones (ajustes «estilo_letra» y «fuente_letra»)."""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
import shiboken6  # noqa: E402
from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtGui import QFont, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from descargador.config import DEFECTOS  # noqa: E402
from descargador.ui import tipografia_letra as T  # noqa: E402
from descargador.ui.escena import letra as L  # noqa: E402

LINEAS = [
    {"ms": 0, "texto": "cuando la noche cae", "pausa": False, "canto": 1500},
    {"ms": 2000, "texto": "sobre la ciudad entera", "pausa": False, "canto": 1500},
    {"ms": 4000, "texto": "y las luces se encienden", "pausa": False},
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _restaurar():
    yield
    L.fijar_estilo_letra("clasica")
    T.fijar("predeterminada")


def _letra(estilo):
    w = L.LetraCinetica()
    w.resize(640, 420)
    w.poner_estilo(estilo)
    w.poner_lineas(LINEAS, True)
    w.fijar_traducciones(["when night falls", None, "and the lights"])
    w._sincronizada = True
    w.fijar_ms(2600)               # línea 2: su línea anterior se va, la siguiente se ve abajo
    w._entradas = {k: time.monotonic() - 10.0 for k in w._entradas}   # palabras ya asentadas
    return w


def _render(w):
    img = QImage(w.width(), w.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    w.render(img)
    return img


def _pintados(img):
    return sum(1 for y in range(0, img.height(), 2) for x in range(0, img.width(), 2)
               if img.pixelColor(x, y).alpha() > 0)


def test_ajustes_por_defecto():
    assert DEFECTOS["estilo_letra"] == "clasica"
    assert DEFECTOS["fuente_letra"] == "predeterminada"
    assert L.ESTILOS_LETRA == ("clasica", "nitida", "neon", "simple")
    assert L.normalizar_estilo("raro") == "clasica"
    assert L.LetraCinetica.__init__ and L.estilo_letra() in L.ESTILOS_LETRA


@pytest.mark.parametrize("estilo", ["clasica", "nitida", "neon", "simple"])
def test_cada_estilo_pinta_sin_error(app, estilo):
    w = _letra(estilo)
    time.sleep(0.05)
    assert w.estilo() == estilo
    assert _pintados(_render(w)) > 200


def test_los_estilos_se_ven_distintos(app):
    imagenes = {e: _render(_letra(e)) for e in L.ESTILOS_LETRA}
    assert imagenes["clasica"] != imagenes["nitida"]
    assert imagenes["clasica"] != imagenes["neon"]
    assert imagenes["clasica"] != imagenes["simple"]


def test_cambio_de_estilo_en_vivo(app):
    w = _letra("clasica")
    L.fijar_estilo_letra("neon")
    assert w.estilo() == "neon"
    L.fijar_estilo_letra("no-existe")
    assert w.estilo() == "clasica"
    shiboken6.delete(w)
    L.fijar_estilo_letra("simple")          # una letra ya destruida no rompe nada


def test_todas_las_fuentes_cargan(app):
    for clave in T.FUENTES:
        if clave == "predeterminada":
            assert T.familia(clave) is None
        else:
            assert T.familia(clave), clave
    base = QFont("Segoe UI")
    base.setPixelSize(30)
    f = T.adaptar(base, "bebas")
    assert f.family() == T.familia("bebas") and f.pixelSize() == 30 and not f.italic()
    assert T.adaptar(base, "predeterminada") is base
    assert T.normalizar("raro") == "predeterminada"


def test_fuente_que_no_carga_usa_la_predeterminada(app, monkeypatch, tmp_path):
    monkeypatch.setattr(T, "carpeta_fuentes", lambda: tmp_path)
    monkeypatch.setitem(T.FUENTES, "falsa", ("Falsa", ("NoExiste.ttf",), QFont.Normal))
    base = QFont("Segoe UI")
    assert T.familia("falsa") is None
    assert T.adaptar(base, "falsa") is base
    T._familias.pop("falsa", None)


@pytest.mark.parametrize("clave", list(T.FUENTES))
def test_cada_fuente_pinta_la_escena_y_la_letra_viva(app, clave):
    w = _letra("clasica")
    T.fijar(clave)
    assert _pintados(_render(w)) > 200
    # la letra viva usa la fuente elegida al medir
    from descargador.ui.letra_viva import LienzoLetra
    f, _ft = LienzoLetra._fuentes(_FakeLienzo())
    fam = T.familia(clave)
    assert f.family() == (fam or "Segoe UI")


class _FakeLienzo:
    compacto = False

    def _tam(self):
        return 30

    def width(self):
        return 800


def test_aviso_cierre_filtra_luajit():
    from descargador.aviso_errores import limpiar_cierre
    solo_luajit = ("Windows fatal exception: code 0xe24c4a02\n\nCurrent thread 0x1 (most recent call first):\n"
                   "  File \"a.py\", line 3 in f\n\n"
                   "Windows fatal exception: code 0xE24C4A02\n\nThread 0x2:\n  File \"b.py\", line 1 in g\n")
    assert limpiar_cierre(solo_luajit) == ""
    mezcla = solo_luajit + ("Windows fatal exception: access violation\n\nCurrent thread 0x3:\n"
                            "  File \"c.py\", line 9 in h\n")
    queda = limpiar_cierre(mezcla)
    assert queda.startswith("Windows fatal exception: access violation")
    assert "0xe24c4a02" not in queda.lower() and "c.py" in queda
    assert limpiar_cierre("Fatal Python error: Segmentation fault\n  File x") .startswith("Fatal Python error")


def test_aviso_cierre_no_envia_si_solo_hay_luajit(tmp_path, monkeypatch):
    from descargador import aviso_errores as A
    (tmp_path / "cierre_nativo.txt").write_text("Windows fatal exception: code 0xe24c4a02\n\nThread 0x1:\n",
                                                encoding="utf-8")
    monkeypatch.setattr(A, "_ruta", lambda n: str(tmp_path / n))
    monkeypatch.setattr(A, "_leer", lambda n, d: {"limpio": False})
    enviados = []
    monkeypatch.setattr(A, "encolar", lambda inf: enviados.append(inf))
    A._revisar_cierre_anterior()
    assert enviados == []
    (tmp_path / "cierre_nativo.txt").write_text("Windows fatal exception: access violation\n\nThread 0x1:\n",
                                                encoding="utf-8")
    A._revisar_cierre_anterior()
    assert len(enviados) == 1


def test_modo_gamer_ahorro_con_etiqueta_destruida(app):
    from descargador.ui.paginas.modo_gamer import PaginaModoGamer

    class _Falsa(QObject):
        pass

    falsa = _Falsa()
    falsa.et_ahorro = QLabel()
    shiboken6.delete(falsa.et_ahorro)
    PaginaModoGamer._refrescar_ahorro(falsa)      # antes: RuntimeError (QLabel ya destruido)


def test_ajustes_selectores_de_letra_aplican_en_vivo(app, tmp_path):
    """La sección «Letra de las canciones» de Ajustes: 4 estilos, cada fuente escrita en la suya."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    from descargador.ui.paginas import ajustes as AJ

    class _Aj(dict):
        def guardar(self):
            pass

    class _Falsa(QWidget):
        _seccion_letra = AJ.PaginaAjustes._seccion_letra
        _aplicar_estilo_letra = AJ.PaginaAjustes._aplicar_estilo_letra
        _aplicar_fuente_letra = AJ.PaginaAjustes._aplicar_fuente_letra
        _pintar_vista_letra = AJ.PaginaAjustes._pintar_vista_letra
        _conectar = AJ.PaginaAjustes._conectar
        _poner = AJ.PaginaAjustes._poner

    pag = _Falsa()
    pag.a = _Aj(estilo_letra="clasica", fuente_letra="predeterminada")
    pag.cuerpo = QVBoxLayout(pag)
    pag._seccion_letra()
    assert pag.estilo_letra.count() == 4
    assert pag.estilo_letra.itemText(0).startswith("Clásica")
    assert pag.fuente_letra.count() == len(T.FUENTES)
    i = pag.fuente_letra.findData("lobster")
    assert pag.fuente_letra.itemData(i, Qt.FontRole).family() == T.familia("lobster")
    w = _letra("clasica")
    pag.estilo_letra.setCurrentIndex(pag.estilo_letra.findData("neon"))
    assert pag.a["estilo_letra"] == "neon" and w.estilo() == "neon"
    pag.fuente_letra.setCurrentIndex(i)
    assert pag.a["fuente_letra"] == "lobster" and T.actual() == "lobster"
    assert "Lobster" in pag.vista_letra.styleSheet()
