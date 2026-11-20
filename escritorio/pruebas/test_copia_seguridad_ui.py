# -*- coding: utf-8 -*-
"""Las tarjetas nuevas de Ajustes (Copia de seguridad y Discord) se construyen y funcionan
sin ventanas reales (Qt offscreen) y con los datos en una carpeta temporal."""

import os
import sys
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_copia_ui_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox  # noqa: E402

from descargador import copia_seguridad as CS  # noqa: E402
from descargador import discord_presencia as D  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402
from descargador.hilos import esperar_todo  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class AjustesFalsos(dict):
    @property
    def datos(self):
        return self

    def guardar(self):
        pass


class Ctx(QObject):
    aviso = Signal(str)
    me_gusta_cambio = Signal(str, bool)
    listas_cambio = Signal()
    guardados_cambio = Signal()
    descargas_cambio = Signal()

    def __init__(self, col):
        super().__init__()
        self.coleccion = col
        self.ajustes = AjustesFalsos(acento="rosa")
        self.cuenta = {}


def _textos(w):
    return " ".join(l.text() for l in w.findChildren(QLabel))


def test_seccion_copia_guarda_y_restaura(app, tmp_path, monkeypatch):
    from descargador.ui import copia_seguridad_ui as UI
    col = Coleccion(tmp_path / "h.db")
    col.alternar_me_gusta({"clave": "yt:aaaaaaaaaa1", "titulo": "Uno", "video_id": "aaaaaaaaaa1"})
    ctx = Ctx(col)
    s = UI.SeccionCopia(ctx)
    assert "Copia automática cada semana" in _textos(s)
    assert "todavía ninguna" in _textos(s)

    # guardar: el diálogo de archivo y el aviso final se contestan solos
    destino = tmp_path / "mi copia.caudal"
    monkeypatch.setattr(UI.QFileDialog, "getSaveFileName", lambda *a, **k: (str(destino), ""))
    avisos = []
    monkeypatch.setattr(UI.QMessageBox, "information", lambda *a, **k: avisos.append(a[2]))
    s._guardar()
    for _ in range(100):
        esperar_todo(100)
        app.processEvents()
        if avisos:
            break
    assert destino.exists() and "1 canción en me gusta" in avisos[0]

    # restaurar: vista previa, juntar, y el aviso de lo que entró
    otra = Coleccion(tmp_path / "otra.db")
    ctx2 = Ctx(otra)
    s2 = UI.SeccionCopia(ctx2)
    monkeypatch.setattr(UI.QFileDialog, "getOpenFileName", lambda *a, **k: (str(destino), ""))
    vistos = []

    def exec_previa(dlg):
        vistos.append(_textos(dlg))
        return QDialog.Accepted
    monkeypatch.setattr(UI.DialogoRestaurar, "exec", exec_previa)
    finales = []
    monkeypatch.setattr(UI.QMessageBox, "exec", lambda caja: finales.append(caja.text()) or 0)
    s2._elegir()
    for _ in range(200):
        esperar_todo(100)
        app.processEvents()
        if finales:
            break
    assert "1 canción en me gusta" in vistos[0]
    previa = UI.DialogoRestaurar(CS.abrir_copia(destino))
    assert "Juntar con lo que tengo" in " ".join(b.text() for b in previa.findChildren(UI.QRadioButton))
    assert otra.me_gusta("yt:aaaaaaaaaa1")
    assert "1 me gusta" in finales[0]
    col.con.close()
    otra.con.close()


def test_copia_danada_avisa_sin_romper(app, tmp_path, monkeypatch):
    from descargador.ui import copia_seguridad_ui as UI
    malo = tmp_path / "rota.caudal"
    malo.write_bytes(b"no soy un zip")
    col = Coleccion(tmp_path / "h.db")
    s = UI.SeccionCopia(Ctx(col))
    monkeypatch.setattr(UI.QFileDialog, "getOpenFileName", lambda *a, **k: (str(malo), ""))
    avisos = []
    monkeypatch.setattr(UI.QMessageBox, "warning", lambda *a, **k: avisos.append(a[2]))
    s._elegir()
    for _ in range(100):
        esperar_todo(100)
        app.processEvents()
        if avisos:
            break
    assert "no es una copia de Caudal" in avisos[0]
    assert s.bt_restaurar.isEnabled()
    col.con.close()


def test_reemplazar_pide_confirmacion(app, tmp_path, monkeypatch):
    from descargador.ui import copia_seguridad_ui as UI
    col = Coleccion(tmp_path / "h.db")
    copia = CS.abrir_copia(CS.crear_copia(col, None, carpeta=tmp_path))
    dlg = UI.DialogoRestaurar(copia)
    dlg.reemplazar.setChecked(True)
    preguntas = []
    monkeypatch.setattr(QMessageBox, "exec", lambda caja: preguntas.append(caja.text()) or 0)
    dlg._aceptar()          # se cierra la pregunta sin decir que sí: no se acepta
    assert preguntas and "¿Reemplazar todo?" in preguntas[0]
    assert dlg.result() != QDialog.Accepted
    col.con.close()


def test_seccion_discord(app, tmp_path):
    from descargador.ui.discord_ajuste import seccion_discord

    class Ctx2:
        discord = None
    assert seccion_discord(Ctx2()) is None                 # sin enganche: nada

    class Enganche:
        disponible, activa, con_boton = False, True, True
    Ctx2.discord = Enganche()
    assert seccion_discord(Ctx2()) is None                 # sin ID de aplicación: nada

    cambios = []

    class Activo(Enganche):
        disponible = True

        def poner_activa(self, v):
            cambios.append(("activa", v))

        def poner_boton(self, v):
            cambios.append(("boton", v))
    Ctx2.discord = Activo()
    s = seccion_discord(Ctx2())
    assert s is not None and "Mostrar lo que escucho en Discord" in _textos(s)
    from PySide6.QtWidgets import QCheckBox
    cajas = s.findChildren(QCheckBox)
    cajas[0].setChecked(False)
    cajas[1].setChecked(False)
    assert cambios == [("activa", False), ("boton", False)]
    assert D.WEB_CAUDAL == "https://caudal-musica.netlify.app"
