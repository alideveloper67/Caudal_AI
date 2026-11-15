# -*- coding: utf-8 -*-
"""Caudal Escritorio 2.2: chat que no se queda en cola, colores a tu gusto y
la fecha de nacimiento del registro. Sin ventanas a la vista (Qt offscreen)."""

import os
import sys
import time
from datetime import date, datetime, timezone

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Qt, Signal  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def esperar(app, cond, que, maximo=10):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


# ---------------------------------------------------------------- colores

def test_colores_propios_y_de_la_lista():
    from descargador.ui import estilos as E
    assert E.acento_de("rosa") == E.ACENTOS["rosa"]
    assert E.fondo_de("noche") == E.FONDOS["noche"]
    assert E.acento_de("raro") == E.ACENTOS["cian"]          # lo desconocido vuelve al de siempre
    _, ac, alto, bajo, texto = E.acento_de("#A3E635")
    assert ac == "#A3E635" and alto != ac and bajo != ac
    assert E._luz(E._rgb(texto)) < 0.05                       # texto oscuro sobre un acento claro
    assert E.acento_de("#1E3A8A")[4] == "#FFFFFF"             # y blanco sobre uno oscuro
    # un fondo claro se oscurece: el texto de la app es claro
    f = E.fondo_de("#FFFFFF")
    assert E._luz(E._rgb(f[1])) <= 0.035
    assert len(f) == 8 and all(c.startswith("#") for c in f[1:])
    E.aplicar_aspecto("#A3E635", "#3B1F0F")
    assert E.C["acento"] == "#A3E635" and E.ACTUAL == {"acento": "#A3E635", "fondo": "#3B1F0F"}
    E.aplicar_aspecto("cian", "oscuro")
    assert E.C["acento"] == "#22D3EE"


def test_selector_guarda_y_ofrece_aplicar(app):
    from descargador.ui.aspecto import SelectorAspecto

    class Ajustes(dict):
        guardados = 0

        def guardar(self):
            self.guardados += 1

    a = Ajustes(acento="cian", fondo="oscuro")
    s = SelectorAspecto(a, ("cian", "oscuro"))
    s.resize(900, 400)
    s.show()
    app.processEvents()
    assert not s.bt_aplicar.isVisible()
    pedidos = []
    s.aplicar.connect(lambda: pedidos.append(1))
    QTest.mouseClick(s.circulos["verde"], Qt.LeftButton)
    QTest.mouseClick(s.tarjetas["uva"], Qt.LeftButton)
    assert (a["acento"], a["fondo"]) == ("verde", "uva") and a.guardados == 2
    assert s.bt_aplicar.isVisible() and s.circulos["verde"].isChecked()
    s._guardar("acento", "#FF00AA")
    assert s.circulo_propio.isChecked() and not s.circulos["verde"].isChecked()
    QTest.mouseClick(s.bt_aplicar, Qt.LeftButton)
    assert pedidos == [1]
    s._original()
    assert (a["acento"], a["fondo"]) == ("cian", "oscuro") and not s.bt_aplicar.isVisible()
    assert s.minimumSizeHint().width() < 520     # cabe con el panel derecho abierto


# ---------------------------------------------------------------- fecha

def test_fecha_sin_dias_imposibles(app):
    from descargador.ui.legal_ui import CamposPerfil
    c = CamposPerfil()
    assert c.nacimiento() is None
    c.dia.setCurrentIndex(c.dia.findData(31))
    c._dia_querido = 31
    c.mes.setCurrentIndex(c.mes.findData(2))
    c.anio.setCurrentIndex(c.anio.findData(2000))
    assert c.dia.count() - 1 == 29 and c.nacimiento() == date(2000, 2, 29)
    c.anio.setCurrentIndex(c.anio.findData(2001))
    assert c.nacimiento() == date(2001, 2, 28)
    c.mes.setCurrentIndex(c.mes.findData(3))
    assert c.nacimiento() == date(2001, 3, 31)                # el 31 vuelve al salir de febrero
    assert "tienes" in c.edad.text()
    hoy = date.today()
    c.anio.setCurrentIndex(c.anio.findData(hoy.year - 10))
    assert not c.tutor.isHidden() and c.valores()["permiso_tutor"] is False
    c.tutor.setChecked(True)
    assert c.valores()["permiso_tutor"] is True
    c.anio.setCurrentIndex(c.anio.findData(1990))
    assert c.tutor.isHidden() and c.valores()["permiso_tutor"] is False


def test_fecha_guardada_se_muestra(app):
    from descargador.ui.legal_ui import CamposPerfil
    c = CamposPerfil(perfil={"nacimiento": date(1988, 12, 31), "pais": "MX", "genero": "mujer"})
    assert c.nacimiento() == date(1988, 12, 31)
    assert c.valores()["pais"] == "MX" and c.valores()["genero"] == "mujer"


# ---------------------------------------------------------------- chat

class SesionFalsa:
    access = "x"
    user_id = "yo"

    def __init__(self):
        self.msgs = []
        self.falla = False

    def pedir(self, metodo, ruta, json=None, cabeceras=None):
        from descargador.nube import SinConexion
        if self.falla and ruta == "mensajes":
            raise SinConexion("sin red")
        ahora = datetime.now(timezone.utc).isoformat()
        if ruta == "rpc/mis_chats":
            return [{"id": "c1", "otro": "o", "usuario": "luis", "nombre": "Luis", "ultimo": ahora,
                     "ultimo_texto": "hola", "ultimo_pista": None, "ultimo_autor": "o", "sin_leer": 0}]
        if ruta.startswith("mensajes?"):
            return [dict(m) for m in self.msgs]
        if ruta == "mensajes" and metodo == "POST":
            m = {"id": len(self.msgs) + 1, "autor": "yo", "texto": json["texto"],
                 "pista": json.get("pista"), "creado": ahora}
            self.msgs.append(m)
            return [dict(m)]
        return None


class Reproductor(QObject):
    pista_cambio = Signal(object)

    def __init__(self):
        super().__init__()
        self.actual = None


class Ctx(QObject):
    aviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.cuenta = {"sesion": SesionFalsa(), "usuario": "yo"}
        self.reproductor = Reproductor()
        self.avisos = []
        self.aviso.connect(self.avisos.append)


def test_chat_envia_aunque_el_carril_normal_este_lleno(app):
    from descargador.hilos import en_segundo_plano
    from descargador.ui.paginas.mensajes import PaginaMensajes
    # la música, las letras y las transiciones ocupan el carril normal un rato
    for _ in range(12):
        en_segundo_plano(time.sleep, 4)
    ctx = Ctx()
    s = ctx.cuenta["sesion"]
    p = PaginaMensajes(ctx)
    p.resize(1000, 600)
    p.show()
    esperar(app, lambda: p.interior_lista.findChildren(QPushButton), "la lista de chats", 3)
    assert not p.bt_enviar.isEnabled()                       # sin conversación, no hay a quién
    QTest.mouseClick(p.interior_lista.findChildren(QPushButton)[0], Qt.LeftButton)
    assert p.campo.isEnabled()
    QTest.keyClicks(p.campo, "hola")
    assert p.bt_enviar.isEnabled()
    QTest.keyClick(p.campo, Qt.Key_Return)
    assert p.pendientes                                       # se ve al momento, «Enviando…»
    esperar(app, lambda: not p.pendientes, "que se confirme el mensaje", 3)
    assert [m["texto"] for m in s.msgs] == ["hola"]

    # lo que suena: sin nada, avisa; con una canción, la manda
    QTest.mouseClick(p.bt_suena, Qt.LeftButton)
    assert "no suena nada" in ctx.avisos[-1]
    ctx.reproductor.actual = {"tipo": "pista", "video_id": "abc12345678", "titulo": "X", "artista": "Y"}
    QTest.mouseClick(p.bt_suena, Qt.LeftButton)
    esperar(app, lambda: len(s.msgs) == 2, "la canción enviada", 3)
    assert s.msgs[1]["pista"]["video_id"] == "abc12345678"

    # sin red: la burbuja ofrece reintentar y al volver la red se manda
    s.falla = True
    QTest.keyClicks(p.campo, "otra")
    QTest.keyClick(p.campo, Qt.Key_Return)
    esperar(app, lambda: p.pendientes and "reintentar" in list(p.pendientes.values())[0][1].text(),
            "el aviso de reintentar", 3)
    s.falla = False
    list(p.pendientes.values())[0][1].mousePressEvent(None)
    esperar(app, lambda: not p.pendientes, "el reintento", 3)
    assert [m["texto"] for m in s.msgs] == ["hola", "", "otra"]


def test_chat_estrecho_alterna_lista_y_conversacion(app):
    from descargador.ui.paginas.mensajes import PaginaMensajes
    ctx = Ctx()
    p = PaginaMensajes(ctx)
    p.resize(600, 600)
    p.show()
    esperar(app, lambda: p.interior_lista.findChildren(QPushButton), "la lista de chats", 3)
    assert p.caja_izq.isVisible() and not p.panel.isVisible()
    QTest.mouseClick(p.interior_lista.findChildren(QPushButton)[0], Qt.LeftButton)
    app.processEvents()
    assert p.panel.isVisible() and not p.caja_izq.isVisible() and p.bt_volver.isVisible()
    assert p.campo.width() > 200
    QTest.mouseClick(p.bt_volver, Qt.LeftButton)
    app.processEvents()
    assert p.caja_izq.isVisible() and not p.panel.isVisible()
