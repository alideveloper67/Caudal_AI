# -*- coding: utf-8 -*-
"""Fondos con personaje: paleta + acento + mosaico, y la capa los pinta sin imagen."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui import estilos as E  # noqa: E402

PERSONAJES = {"hellokitty", "kuromi", "pikachu", "charmander", "squirtle", "bulbasaur", "snoopy", "totoro",
              "mymelody", "purin", "cinnamoroll", "kirby", "doraemon", "olaf", "nyan", "gato_negro", "capibara", "pochacco", "nailong"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_estan_los_19_y_los_de_siempre():
    assert set(E.TEMAS) == PERSONAJES
    for k in ("oscuro", "negro", "noche", "uva", "bosque", "grafito"):
        assert k in E.FONDOS and not E.es_tema(k)
    for k, v in E.TEMAS.items():
        assert E.FONDOS[k][0] == v[0]
        assert len(E.FONDOS[k]) == 8 and all(E.es_color(c) for c in E.FONDOS[k][1:]), k
        assert E.es_color(E.acento_de_tema(k)), k
        assert E.ruta_patron(k) is not None and E.ruta_patron(k).exists(), k
    assert E.acento_de_tema("oscuro") == "" and E.ruta_patron("oscuro") is None


def test_el_fondo_queda_oscuro_para_leer():
    for k in E.TEMAS:
        assert E._luz(E._rgb(E.FONDOS[k][1])) <= 0.035, k


def test_aplicar_tema_cambia_la_paleta_y_enciende_el_mosaico():
    antes = dict(E.ACTUAL)
    try:
        E.aplicar_aspecto(E.acento_de_tema("kuromi"), "kuromi")
        assert E.C["fondo"] == E.FONDOS["kuromi"][1]
        assert E.C["acento"].upper() == "#FF77B7"
        assert E.patron_actual() is not None
        E.aplicar_aspecto("cian", "oscuro")
        assert E.patron_actual() is None
    finally:
        E.aplicar_aspecto(antes["acento"], antes["fondo"])


def test_el_personaje_se_sienta_sobre_la_barra(app):
    from PySide6.QtWidgets import QWidget
    from descargador.ui.fondo_capa import PersonajeEsquina
    ventana = QWidget()
    ventana.resize(1200, 700)
    barra = QWidget(ventana)
    barra.setGeometry(0, 600, 1200, 100)
    ventana.show()
    E.aplicar_aspecto("cian", "pikachu")
    try:
        pj = PersonajeEsquina(ventana, barra)
        pj.colocar()
        assert pj.isVisible()
        g = pj.geometry()
        assert g.right() > 1100 and g.right() <= 1200          # a un costado (derecha)
        assert 590 <= g.bottom() <= 612                         # los pies sobre el borde de la barra
        assert g.height() < 180                                 # chico, a un costado
        img = pj.grab().toImage()
        assert any(img.pixelColor(x, y).alpha() > 200 for x in range(img.width()) for y in range(img.height()))
        barra.setGeometry(0, 500, 1200, 200)                    # la barra se mueve: el personaje la sigue
        pj.colocar()
        assert 490 <= pj.geometry().bottom() <= 512
        E.aplicar_aspecto("cian", "oscuro")                     # fondo normal: se va
        pj.colocar()
        assert not pj.isVisible()
    finally:
        E.aplicar_aspecto("cian", "oscuro")
        ventana.close()


def test_el_personaje_se_agranda_con_la_rueda_y_arrastrando(app):
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QWidget
    from PySide6.QtTest import QTest
    from descargador.ui.fondo_capa import PersonajeEsquina

    class Ajustes(dict):
        guardado = 0

        def guardar(self):
            self.guardado += 1

    ventana = QWidget()
    ventana.ajustes = Ajustes(tamano_personaje=100)
    ventana.resize(1200, 700)
    barra = QWidget(ventana)
    barra.setGeometry(0, 600, 1200, 100)
    ventana.show()
    E.aplicar_aspecto("cian", "kuromi")
    try:
        pj = PersonajeEsquina(ventana, barra)
        pj.colocar()
        assert pj.alto == 100                                    # recuerda el tamaño guardado
        pie = pj.geometry().bottom()
        rueda = QWheelEvent(QPointF(20, 20), QPointF(pj.mapToGlobal(QPoint(20, 20))), QPoint(0, 0), QPoint(0, 120),
                            Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(pj, rueda)
        assert pj.alto == 110 and pj.geometry().bottom() == pie  # crece y sigue sentado en la barra
        QTest.mousePress(pj, Qt.LeftButton, Qt.NoModifier, QPoint(30, 30))
        QTest.mouseMove(pj, QPoint(30 - 40, 30 - 40))             # arrastrar hacia arriba/izquierda
        QTest.mouseRelease(pj, Qt.LeftButton, Qt.NoModifier, QPoint(-10, -10))
        assert pj.alto > 110
        pj.poner_alto(5)
        assert pj.alto == PersonajeEsquina.MINIMO                # con límites
        pj.poner_alto(9999)
        assert pj.alto == PersonajeEsquina.MAXIMO
        pj._guardar()
        assert ventana.ajustes["tamano_personaje"] == PersonajeEsquina.MAXIMO and ventana.ajustes.guardado
    finally:
        E.aplicar_aspecto("cian", "oscuro")
        ventana.close()


def test_con_imagen_de_fondo_la_imagen_se_sigue_viendo(app):
    from PySide6.QtGui import QColor
    from descargador.ui.fondo_capa import Renderizador, pixmap_patron
    E.aplicar_aspecto("cian", "purin")
    try:
        foto = QImage(400, 400, QImage.Format_RGB32)
        foto.fill(QColor("#00FF00"))                 # una «foto» verde chillón
        img = QImage(400, 400, QImage.Format_ARGB32)
        p = QPainter(img)
        Renderizador().pintar(p, QRectF(0, 0, 400, 400), foto, 1, 60, 0, patron=pixmap_patron(E.patron_actual()))
        p.end()
        c = QColor(img.pixel(200, 150))
        assert c.green() > c.red() + 40              # el tema no tapa la imagen de la persona
    finally:
        E.aplicar_aspecto("cian", "oscuro")


def test_elegir_un_fondo_con_personaje_pone_su_mascota(app):
    from descargador.ui.paginas.ajustes import PaginaAjustes  # noqa: F401  (existe)
    from descargador.ui.paginas import ajustes as A

    class Gestor:
        clave = ""

        def elegir(self, k):
            self.clave = k
            return True

    class Falsa:
        ctx = type("Ctx", (), {"mascota": Gestor()})()
    f = Falsa()
    A.PaginaAjustes._mascota_del_fondo(f, "#FF8A3D", "charmander")
    assert f.ctx.mascota.clave == "charmander"
    A.PaginaAjustes._mascota_del_fondo(f, "cian", "noche")      # un fondo normal no cambia la mascota
    assert f.ctx.mascota.clave == "charmander"


def test_selector_trae_la_seccion_y_elegir_pone_el_acento(app):
    from descargador.ui.aspecto import SelectorAspecto

    class Ajustes(dict):
        def guardar(self):
            pass

    a = Ajustes(acento="cian", fondo="oscuro")
    s = SelectorAspecto(a, ("cian", "oscuro"))
    assert PERSONAJES <= set(s.tarjetas)
    assert s.tarjetas["olaf"].patron is not None and s.tarjetas["oscuro"].patron is None
    s.tarjetas["charmander"].click()
    assert a["fondo"] == "charmander" and a["acento"] == "#FF8A3D"
    assert s.tarjetas["charmander"].isChecked()
    s.tarjetas["noche"].click()
    assert a["fondo"] == "noche" and a["acento"] == "#FF8A3D"   # el color elegido se queda
