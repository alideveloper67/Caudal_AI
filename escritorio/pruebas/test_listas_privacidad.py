# -*- coding: utf-8 -*-
"""Listas públicas o privadas y «mostrar en mi perfil» (escritorio).

Base local, sincronización con la nube (con una nube de mentira) y pantallas. Qt offscreen y
datos en una carpeta temporal.
"""

import os
import sqlite3
import sys
import tempfile
import types
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from descargador import social as S  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402
from descargador.nube import ErrorNube  # noqa: E402
from descargador.sincronizacion import Sincronizador  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def plantilla(tmp_path_factory):
    """Crear la base desde cero tarda (cada guardado espera al disco): se hace una vez y se copia."""
    ruta = tmp_path_factory.mktemp("plantilla") / "h.db"
    Coleccion(ruta).con.close()
    return ruta


def base_nueva(plantilla, destino):
    import shutil
    shutil.copy(str(plantilla), str(destino))
    return Coleccion(destino)


@pytest.fixture
def col(tmp_path, plantilla):
    return base_nueva(plantilla, tmp_path / "h.db")


def ordenes(col):
    import json
    return [(f["op"], json.loads(f["datos"]))
            for f in col.con.execute("SELECT op, datos FROM pendientes ORDER BY id")]


# ---------------------------------------------------------------- base local
def test_una_lista_nueva_es_privada_y_fuera_del_perfil(col):
    i = col.crear_lista("Para correr")
    l = col.lista(i)
    assert not l["publica"] and not l["en_perfil"]


def test_hacerla_publica_y_mostrarla(col):
    i = col.crear_lista("Para correr")
    col.editar_lista(i, publica=True, en_perfil=True)
    l = col.lista(i)
    assert l["publica"] == 1 and l["en_perfil"] == 1


def test_en_perfil_solo_vale_si_es_publica(col):
    i = col.crear_lista("Para correr")
    col.editar_lista(i, publica=False, en_perfil=True)
    assert col.lista(i)["en_perfil"] == 0
    col.editar_lista(i, publica=True, en_perfil=True)
    col.editar_lista(i, publica=False)               # volver privada la saca del perfil
    l = col.lista(i)
    assert l["publica"] == 0 and l["en_perfil"] == 0


def test_cambiar_solo_el_nombre_no_toca_los_ajustes(col):
    i = col.crear_lista("Para correr")
    col.editar_lista(i, publica=True, en_perfil=True)
    col.editar_lista(i, nombre="Correr rápido")
    l = col.lista(i)
    assert l["publica"] == 1 and l["en_perfil"] == 1


def test_base_vieja_sin_las_columnas_se_actualiza(tmp_path):
    bd = tmp_path / "vieja.db"
    con = sqlite3.connect(str(bd))
    con.execute("CREATE TABLE listas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, creada REAL)")
    con.execute("INSERT INTO listas (nombre, creada) VALUES ('Vieja', 1)")
    con.commit()
    con.close()
    c = Coleccion(bd)
    l = c.listas()[0]
    assert l["nombre"] == "Vieja" and not l["publica"] and not l["en_perfil"]


def test_la_orden_para_la_nube_lleva_los_ajustes_solo_si_cambiaron(col):
    col.sincronizador = MagicMock()
    i = col.crear_lista("Para correr")
    col.editar_lista(i, descripcion="ritmo")
    for op, d in ordenes(col):
        assert "publica" not in d and "en_perfil" not in d, "no debe estorbar si la nube no los conoce"
    col.con.execute("DELETE FROM pendientes")
    col.editar_lista(i, publica=True, en_perfil=True)
    (op, d), = ordenes(col)
    assert op == "lista_poner" and d["publica"] is True and d["en_perfil"] is True
    col.con.execute("DELETE FROM pendientes")
    col.editar_lista(i, publica=False)
    (op, d), = ordenes(col)
    assert d["publica"] is False and d["en_perfil"] is False


# ---------------------------------------------------------------- nube de mentira
class NubeFalsa:
    def __init__(self, listas=None, rechaza_ajustes=False):
        self.listas = listas or []
        self.rechaza_ajustes = rechaza_ajustes
        self.llamadas = []

    def pedir(self, metodo, ruta, json=None, cabeceras=None, **_k):
        self.llamadas.append((metodo, ruta, json))
        if metodo == "POST" and ruta.startswith("listas?") and self.rechaza_ajustes \
                and any("publica" in f for f in json):
            raise ErrorNube("column listas.publica does not exist")
        if metodo == "GET" and ruta.startswith("listas?"):
            if self.rechaza_ajustes and "publica" in ruta:
                raise ErrorNube("column listas.publica does not exist")
            return [dict(l) for l in self.listas]
        return []


def sincronizador(col, nube):
    s = Sincronizador(col, {"sesion": nube})
    return s


def test_enviar_lista_con_ajustes(col):
    nube = NubeFalsa()
    s = sincronizador(col, nube)
    s._enviar("lista_poner", {"uuid": "u1", "nombre": "A", "descripcion": "", "fijada": False,
                              "publica": True, "en_perfil": True})
    fila = nube.llamadas[-1][2][0]
    assert fila["publica"] is True and fila["en_perfil"] is True


def test_enviar_sin_ajustes_no_los_manda(col):
    nube = NubeFalsa()
    s = sincronizador(col, nube)
    s._enviar("lista_poner", {"uuid": "u1", "nombre": "A", "descripcion": "", "fijada": False})
    assert "publica" not in nube.llamadas[-1][2][0]


def test_si_la_nube_aun_no_conoce_los_ajustes_se_guarda_lo_demas(col):
    nube = NubeFalsa(rechaza_ajustes=True)
    s = sincronizador(col, nube)
    s._enviar("lista_poner", {"uuid": "u1", "nombre": "A", "descripcion": "", "fijada": False,
                              "publica": True, "en_perfil": True})
    ultima = nube.llamadas[-1][2][0]
    assert ultima["nombre"] == "A" and "publica" not in ultima


def _traer(col, nube):
    s = sincronizador(col, nube)
    con = sqlite3.connect(str(col.archivo))
    con.row_factory = sqlite3.Row
    try:
        s._traer(con)
        con.commit()
    finally:
        con.close()


def test_traer_aplica_los_ajustes_de_la_nube(col):
    nube = NubeFalsa([{"id": "u-1", "nombre": "Nube", "descripcion": "", "fijada": False,
                       "creada": "2026-01-01T00:00:00+00:00", "publica": True, "en_perfil": True},
                      {"id": "u-2", "nombre": "Secreta", "descripcion": "", "fijada": False,
                       "creada": "2026-01-02T00:00:00+00:00", "publica": False, "en_perfil": True}])
    _traer(col, nube)
    por_nombre = {l["nombre"]: l for l in col.listas()}
    assert por_nombre["Nube"]["publica"] == 1 and por_nombre["Nube"]["en_perfil"] == 1
    assert por_nombre["Secreta"]["publica"] == 0 and por_nombre["Secreta"]["en_perfil"] == 0


def test_traer_actualiza_una_lista_que_ya_existe(col):
    i = col.crear_lista("Mía")
    u = col.lista(i)["uuid"]
    nube = NubeFalsa([{"id": u, "nombre": "Mía", "descripcion": "", "fijada": False,
                       "creada": "2026-01-01T00:00:00+00:00", "publica": True, "en_perfil": False}])
    col.con.execute("DELETE FROM pendientes")
    col.con.commit()
    _traer(col, nube)
    l = col.lista(i)
    assert l["publica"] == 1 and l["en_perfil"] == 0


def test_traer_sin_las_columnas_en_la_nube_no_rompe(col):
    nube = NubeFalsa([{"id": "u-3", "nombre": "Sin ajustes", "descripcion": "", "fijada": False,
                       "creada": "2026-01-01T00:00:00+00:00"}], rechaza_ajustes=True)
    _traer(col, nube)
    l = [x for x in col.listas() if x["nombre"] == "Sin ajustes"][0]
    assert not l["publica"]


# ---------------------------------------------------------------- pantallas
def test_dialogo_de_editar_enciende_y_apaga_en_perfil(app):
    from descargador.ui.paginas.coleccion import DialogoEditarLista
    d = DialogoEditarLista({"nombre": "A", "descripcion": "", "publica": 0, "en_perfil": 0})
    assert not d.publica.isChecked() and not d.en_perfil.isEnabled()
    assert "primero hazla pública" in d.ayuda_perfil.text()
    d.publica.setChecked(True)
    assert d.en_perfil.isEnabled()
    d.en_perfil.setChecked(True)
    d.publica.setChecked(False)
    assert not d.en_perfil.isChecked() and not d.en_perfil.isEnabled()


def test_dialogo_de_editar_respeta_lo_guardado(app):
    from descargador.ui.paginas.coleccion import DialogoEditarLista
    d = DialogoEditarLista({"nombre": "A", "descripcion": "", "publica": 1, "en_perfil": 1})
    assert d.publica.isChecked() and d.en_perfil.isChecked() and d.en_perfil.isEnabled()
    d = DialogoEditarLista({"nombre": "A", "descripcion": "", "publica": 0, "en_perfil": 1})
    assert not d.en_perfil.isChecked()       # un dato incoherente no engaña al diálogo


def test_pista_de_item_para_reproducir():
    p = S.pista_de_item({"clave": "yt:abcdefghijk", "datos": {"titulo": "Tema", "artistas": []}})
    assert p["clave"] == "yt:abcdefghijk" and p["video_id"] == "abcdefghijk" and p["titulo"] == "Tema"
    assert S.pista_de_item({"clave": "local:3", "datos": {}}) is None


def test_social_listas_de_perfil_tolera_nube_sin_la_funcion():
    class Sesion:
        def rpc(self, nombre, **k):
            raise ErrorNube("function does not exist")
    soc = S.Social(Sesion())
    assert soc.listas_de_perfil("ana") == []
    assert soc.listas_de_perfil("") == []


def _pagina_falsa(app, listas, ctx):
    from descargador.ui.paginas import perfil as P
    pag = types.SimpleNamespace()
    pag.social = MagicMock()
    pag.social.listas_de_perfil.return_value = listas
    pag.usuario = "ana"
    pag.ctx = ctx
    pag._fila_lista = types.MethodType(P.PaginaPerfil._fila_lista, pag)
    pag._abrir_lista = types.MethodType(P.PaginaPerfil._abrir_lista, pag)
    return P, pag


def test_perfil_de_otra_persona_muestra_sus_listas(app, monkeypatch):
    P, pag = _pagina_falsa(app, [{"id": "u1", "nombre": "Pública", "total": 3, "canciones": [],
                                  "publica": True, "en_perfil": True}], MagicMock())
    monkeypatch.setattr(P, "en_segundo_plano", lambda f, *a, ok=None, **k: ok(f(*a)))
    tarjeta = P.PaginaPerfil._listas(pag, {"es_mio": False})
    assert not tarjeta.isHidden()
    textos = [e.text() for e in tarjeta.findChildren(QLabel)]
    assert "Pública" in textos and "3 canciones" in textos
    assert not any("Privada" in t or "Oculta" in t for t in textos)
    assert len(tarjeta.findChildren(QPushButton)) == 1


def test_perfil_propio_marca_las_ocultas_y_las_privadas(app, monkeypatch):
    P, pag = _pagina_falsa(app, [
        {"id": "u1", "nombre": "Visible", "total": 1, "canciones": [], "publica": True, "en_perfil": True},
        {"id": "u2", "nombre": "Oculta", "total": 2, "canciones": [], "publica": True, "en_perfil": False},
        {"id": "u3", "nombre": "Secreta", "total": 0, "canciones": [], "publica": False, "en_perfil": False},
    ], MagicMock())
    monkeypatch.setattr(P, "en_segundo_plano", lambda f, *a, ok=None, **k: ok(f(*a)))
    tarjeta = P.PaginaPerfil._listas(pag, {"es_mio": True})
    textos = [e.text() for e in tarjeta.findChildren(QLabel)]
    assert "Oculta en tu perfil" in textos and "Privada" in textos
    assert textos.count("Oculta en tu perfil") == 1 and textos.count("Privada") == 1
    assert "0 canciones" in textos and "1 canción" in textos


def test_perfil_sin_listas_no_muestra_la_tarjeta(app, monkeypatch):
    P, pag = _pagina_falsa(app, [], MagicMock())
    monkeypatch.setattr(P, "en_segundo_plano", lambda f, *a, ok=None, **k: ok(f(*a)))
    assert P.PaginaPerfil._listas(pag, {"es_mio": False}).isHidden()


def test_abrir_una_lista_ajena_reproduce_sus_canciones(app, monkeypatch):
    ctx = MagicMock()
    P, pag = _pagina_falsa(app, [], ctx)
    monkeypatch.setattr(P, "en_segundo_plano", lambda f, *a, ok=None, **k: ok(f(*a)))
    pag.social.ver_lista_publica.return_value = {"canciones": [
        {"clave": "yt:aaaaaaaaaaa", "datos": {"titulo": "Uno"}},
        {"clave": "yt:bbbbbbbbbbb", "datos": {"titulo": "Dos"}}]}
    P.PaginaPerfil._abrir_lista(pag, {"id": "u1", "nombre": "Pública"}, False)
    pistas, inicio, contexto = ctx.reproducir_lista.call_args[0]
    assert [p["titulo"] for p in pistas] == ["Uno", "Dos"] and inicio == 0
    assert contexto["titulo"] == "Pública"


def test_abrir_una_lista_propia_va_a_la_lista_local(app, tmp_path, plantilla):
    from descargador.ui.paginas import perfil as P
    col = base_nueva(plantilla, tmp_path / "x.db")
    i = col.crear_lista("Mía")
    u = col.lista(i)["uuid"]
    ctx = MagicMock()
    ctx.coleccion = col
    _P, pag = _pagina_falsa(app, [], ctx)
    P.PaginaPerfil._abrir_lista(pag, {"id": u, "nombre": "Mía"}, True)
    ctx.navegar.assert_called_once_with({"pagina": "mi_lista", "id": i})
