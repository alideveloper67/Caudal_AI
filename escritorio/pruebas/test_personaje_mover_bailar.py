# -*- coding: utf-8 -*-
"""El personaje del fondo: se arrastra a cualquier parte de la ventana (sin salirse), recuerda el lugar,
vuelve a su esquina con doble clic y baila solo mientras suena la música. Qt offscreen.

Se corre solo (un archivo por proceso): python -m pytest pruebas/test_personaje_mover_bailar.py"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, Signal  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from descargador import config  # noqa: E402
from descargador.ui import estilos as E  # noqa: E402
from descargador.ui.fondo_capa import PersonajeEsquina  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class Ajustes(dict):
    guardado = 0

    def guardar(self):
        self.guardado += 1


class RepFalso(QObject):
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    pista_cambio = Signal(object)
    estado = "parado"
    actual = None
    velocidad = 1.0
    _posicion = 0.0

    def _analisis_de(self, _pista):
        return None


def _escena(app, ajustes=None, rep=None):
    ventana = QWidget()
    ventana.ajustes = Ajustes(tamano_personaje=100, personaje_x=-1, personaje_y=-1, personaje_baila=True,
                          acento="cian", fondo="oscuro")
    ventana.ajustes.update(ajustes or {})
    ventana.resize(1200, 700)
    barra = QWidget(ventana)
    barra.setGeometry(0, 600, 1200, 100)
    ventana.show()
    E.aplicar_aspecto("cian", "kuromi")
    pj = PersonajeEsquina(ventana, barra, rep)
    pj.colocar()
    return ventana, barra, pj


def _cerrar(ventana):
    """Cierra y borra la ventana de verdad (los widgets sueltos dejan el siguiente test a merced del GC)."""
    ventana.close()
    ventana.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QApplication.processEvents()


def _arrastrar(pj, de, a):
    QTest.mousePress(pj, Qt.LeftButton, Qt.NoModifier, de)
    QTest.mouseMove(pj, a)
    QTest.mouseRelease(pj, Qt.LeftButton, Qt.NoModifier, a)


@pytest.fixture(autouse=True)
def aspecto_normal():
    yield
    E.aplicar_aspecto("cian", "oscuro")


def test_los_ajustes_nuevos_tienen_su_valor_de_siempre():
    d = config.DEFECTOS
    assert d["personaje_x"] == -1 and d["personaje_y"] == -1
    assert d["personaje_baila"] is True and d["aviso_regalo_visto"] is False


def test_arrastrar_lo_mueve_y_ya_no_cambia_el_tamano(app):
    ventana, _b, pj = _escena(app)
    try:
        assert pj.en_la_esquina
        alto, pos0 = pj.alto, pj.pos()
        _arrastrar(pj, QPoint(30, 30), QPoint(-200, -150))
        assert pj.alto == alto                                   # el arrastre ya no cambia el tamaño
        assert not pj.en_la_esquina
        assert pj.pos() != pos0
        x, y = pj.x(), pj.y()
        fx, fy = pj._frac
        assert 0 <= fx <= 1 and 0 <= fy <= 1
        assert ventana.ajustes["personaje_x"] == fx and ventana.ajustes["personaje_y"] == fy
        assert ventana.ajustes.guardado
        # un clic sin mover no lo saca de su sitio ni guarda
        n = ventana.ajustes.guardado
        QTest.mouseClick(pj, Qt.LeftButton, Qt.NoModifier, QPoint(30, 30))
        assert (pj.x(), pj.y()) == (x, y) and ventana.ajustes.guardado == n
    finally:
        _cerrar(ventana)


def test_nunca_se_sale_de_la_ventana(app):
    ventana, _b, pj = _escena(app)
    try:
        _arrastrar(pj, QPoint(30, 30), QPoint(-5000, -5000))
        assert pj.x() == 0 and pj.y() == 0
        _arrastrar(pj, QPoint(30, 30), QPoint(9000, 9000))
        assert pj.geometry().right() + 1 == ventana.width() and pj.geometry().bottom() + 1 == ventana.height()
        assert ventana.rect().contains(pj.geometry())
        assert pj._frac == (1.0, 1.0)
    finally:
        _cerrar(ventana)


def test_el_lugar_se_respeta_al_reabrir_y_al_cambiar_la_ventana(app):
    ventana, _b, pj = _escena(app, {"personaje_x": 0.5, "personaje_y": 0.25})
    try:
        assert pj._frac == (0.5, 0.25)
        libre_x, libre_y = ventana.width() - pj.width(), ventana.height() - pj.height()
        assert abs(pj.x() - libre_x * 0.5) <= 1 and abs(pj.y() - libre_y * 0.25) <= 1
        ventana.resize(800, 500)
        app.processEvents()
        pj.colocar()
        libre_x, libre_y = ventana.width() - pj.width(), ventana.height() - pj.height()
        assert abs(pj.x() - libre_x * 0.5) <= 1 and abs(pj.y() - libre_y * 0.25) <= 1   # mismo lugar relativo
        assert ventana.rect().contains(pj.geometry())
    finally:
        _cerrar(ventana)


def test_valores_basura_dejan_al_personaje_en_su_esquina(app):
    for malo in ({"personaje_x": 7, "personaje_y": 0.3}, {"personaje_x": "no", "personaje_y": None}):
        ventana, _b, pj = _escena(app, malo)
        try:
            assert pj.en_la_esquina
        finally:
            _cerrar(ventana)


def test_doble_clic_y_el_metodo_lo_devuelven_a_la_esquina(app):
    ventana, _b, pj = _escena(app)
    try:
        esquina = pj.pos()
        _arrastrar(pj, QPoint(30, 30), QPoint(-300, -300))
        assert pj.pos() != esquina
        QTest.mouseDClick(pj, Qt.LeftButton, Qt.NoModifier, QPoint(30, 30))
        assert pj.en_la_esquina and pj.pos() == esquina
        assert ventana.ajustes["personaje_x"] == -1 and ventana.ajustes["personaje_y"] == -1
        _arrastrar(pj, QPoint(30, 30), QPoint(-300, -300))
        pj.volver_a_la_esquina()
        assert pj.en_la_esquina and pj.pos() == esquina
    finally:
        _cerrar(ventana)


def test_la_rueda_cambia_el_tamano_y_en_su_sitio_la_esquina_de_abajo_se_queda(app):
    ventana, _b, pj = _escena(app, {"personaje_x": 0.4, "personaje_y": 0.4})
    try:
        abajo, derecha = pj.geometry().bottom(), pj.geometry().right()
        rueda = QWheelEvent(QPointF(20, 20), QPointF(pj.mapToGlobal(QPoint(20, 20))), QPoint(0, 0),
                            QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(pj, rueda)
        assert pj.alto == 110
        assert abs(pj.geometry().bottom() - abajo) <= 1 and abs(pj.geometry().right() - derecha) <= 1
        assert ventana.rect().contains(pj.geometry())
    finally:
        _cerrar(ventana)


def test_en_la_esquina_sigue_sentado_en_la_barra(app):
    ventana, barra, pj = _escena(app)
    try:
        lado, arriba, abajo = pj._margenes()
        pies = pj.y() + arriba + pj.alto
        assert pies == barra.y() + 4                                      # los pies, sobre el borde de la barra
        assert pj.geometry().right() < ventana.width()
        barra.setGeometry(0, 500, 1200, 200)
        pj.colocar()
        assert pj.y() + arriba + pj.alto == 504
    finally:
        _cerrar(ventana)


def _esperar_amp(app, pj, cond, que, maximo=3.0):
    import time
    fin = time.time() + maximo
    while not cond():
        QTest.qWait(20)
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que} (amp={pj._amp})")


def _en_el_tiempo(pj, tiempos):
    """Pone la canción justo en `tiempos` tiempos después del primer tiempo (fase)."""
    import time
    bpm, fase = pj._ritmo
    pj._ref = (time.monotonic(), fase + tiempos * pj._periodo())


def test_baila_solo_mientras_suena_con_fundido_de_entrada_y_salida(app):
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        assert not pj._t_baile.isActive()                       # sin música: quieto y sin reloj
        assert pj.pose() == (0.0, 0.0, 0.0, 1.0, 1.0)
        rep.estado_cambio.emit("cargando")
        assert not pj._t_baile.isActive()
        rep.estado_cambio.emit("sonando")
        assert pj._t_baile.isActive()
        QTest.qWait(120)
        assert 0 < pj._amp < 1                                  # entra con fundido, no de golpe
        _esperar_amp(app, pj, lambda: pj._amp >= 1.0, "entra del todo")
        assert 0.25 < pj.FUNDIDO_S + 0.0 < 0.5
        rep.estado_cambio.emit("pausa")
        assert pj._t_baile.isActive()                           # sigue un rato para sacarlo con suavidad
        QTest.qWait(120)
        assert 0 < pj._amp < 1                                  # sale con fundido, no de golpe
        _esperar_amp(app, pj, lambda: not pj._t_baile.isActive(), "se apaga el reloj")
        assert pj._amp == 0.0 and pj.pose() == (0.0, 0.0, 0.0, 1.0, 1.0)
        rep.estado_cambio.emit("sonando")
        assert pj._t_baile.isActive()
        rep.estado_cambio.emit("parado")
        _esperar_amp(app, pj, lambda: not pj._t_baile.isActive(), "parado: se apaga")
    finally:
        _cerrar(ventana)


def test_el_baile_es_suave_y_chico(app):
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        rep.estado_cambio.emit("sonando")
        pj._amp = 1.0
        visto = {"subida": 0.0, "desp": 0.0, "giro": 0.0, "sx": 1.0, "sy": 1.0, "sx_min": 1.0, "sy_min": 1.0}
        for i in range(0, 80):
            _en_el_tiempo(pj, i / 20.0)                          # 4 tiempos, en pasos de 1/20 de tiempo
            subida, desp, giro, sx, sy = pj.pose()
            assert 0 <= subida <= 1
            assert abs(desp) <= pj.MECE + 1e-9 and abs(giro) <= pj.GIRO + 1e-9
            assert abs(sx - 1) <= pj.ESTIRA + 1e-9 and abs(sy - 1) <= pj.ESTIRA + 1e-9
            visto["subida"] = max(visto["subida"], subida)
            visto["desp"] = max(visto["desp"], abs(desp))
            visto["giro"] = max(visto["giro"], abs(giro))
        assert visto["subida"] > 0.95 and visto["desp"] > 0.9 * pj.MECE and visto["giro"] > 0.9 * pj.GIRO
        assert pj.SALTO == 0.028 and pj.MECE == 0.012 and pj.GIRO == 1.7 and pj.ESTIRA <= 0.012
        pj.grab()                                                # pinta sin errores
    finally:
        _cerrar(ventana)


def test_cae_en_los_tiempos_de_la_cancion(app):
    rep = RepFalso()
    rep.actual = {"clave": "x"}
    rep._analisis_de = lambda pista: {"bpm": 120.0, "fase": 0.35, "uno": 0.35}   # el análisis ya guardado
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        rep.estado_cambio.emit("sonando")
        pj._amp = 1.0
        assert pj._ritmo == (120.0, 0.35) and abs(pj._periodo() - 0.5) < 1e-9
        for n in range(4):
            _en_el_tiempo(pj, n)                                 # justo en el tiempo: abajo
            assert pj.pose()[0] < 0.06
            _en_el_tiempo(pj, n + 0.5)                           # entre tiempos: arriba
            assert pj.pose()[0] > 0.94
        # el vaivén dura 2 tiempos: en el tiempo 0 y el 2 está al mismo lado, en el 1 al contrario
        _en_el_tiempo(pj, 0.5)
        a = pj.pose()[2]
        _en_el_tiempo(pj, 1.5)
        b = pj.pose()[2]
        assert a * b < 0
    finally:
        _cerrar(ventana)


def test_la_posicion_se_interpola_y_se_congela_en_pausa(app):
    import time
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        rep.estado_cambio.emit("sonando")
        rep.posicion_cambio.emit(30.0)
        p0 = pj._posicion_cancion()
        assert 30.0 <= p0 < 30.2
        time.sleep(0.2)
        assert 0.18 < pj._posicion_cancion() - p0 < 0.4          # avanza entre aviso y aviso
        rep.estado_cambio.emit("pausa")
        q = pj._posicion_cancion()
        time.sleep(0.1)
        assert pj._posicion_cancion() == q                       # en pausa, quieta
    finally:
        _cerrar(ventana)


def test_ritmo_sin_analisis_96_y_los_rapidos_a_la_mitad(app):
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        assert pj._ritmo == (96.0, 0.0) and abs(pj._periodo() - 60 / 96) < 1e-9
        for bpm, bailado in ((90, 90), (130, 130), (140, 70), (180, 90), (260, 130)):
            pj._ritmo = (float(bpm), 0.0)
            assert abs(pj._periodo() - 60 / bailado) < 1e-9, bpm
        # el cambio de canción vuelve a leer el análisis
        rep.actual = {"clave": "y"}
        rep._analisis_de = lambda pista: {"bpm": 150.0, "fase": 0.2}
        rep.pista_cambio.emit({})
        assert pj._ritmo == (150.0, 0.2)
        rep._analisis_de = lambda pista: None                    # una canción sin analizar
        rep.pista_cambio.emit({})
        assert pj._ritmo == (96.0, 0.0)
        rep._analisis_de = lambda pista: (_ for _ in ()).throw(RuntimeError("roto"))
        rep.pista_cambio.emit({})                                # un fallo del análisis no rompe nada
        assert pj._ritmo == (96.0, 0.0)
    finally:
        _cerrar(ventana)


def test_los_pies_no_se_mueven_al_bailar_y_el_dibujo_cabe(app):
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    try:
        geo = pj.geometry()
        rep.estado_cambio.emit("sonando")
        pj._amp = 1.0
        for t in (0.0, 0.13, 0.25, 0.4, 0.5, 0.75, 0.9, 1.3):
            _en_el_tiempo(pj, t)
            pj.grab()                                           # pinta sin errores
            assert pj.geometry() == geo                         # el widget no se mueve: solo el dibujo
    finally:
        _cerrar(ventana)


def test_el_ajuste_apaga_el_baile_y_ya_suena_al_crearlo(app):
    rep = RepFalso()
    rep.estado = "sonando"
    ventana, _b, pj = _escena(app, {"personaje_baila": False}, rep)
    try:
        assert not pj._t_baile.isActive()
        ventana.ajustes["personaje_baila"] = True
        pj.actualizar_baile()
        assert pj._t_baile.isActive()
        ventana.ajustes["personaje_baila"] = False
        pj.actualizar_baile()
        _esperar_amp(app, pj, lambda: not pj._t_baile.isActive(), "se apaga con fundido")
    finally:
        _cerrar(ventana)


def test_oculto_no_gasta_reloj(app):
    rep = RepFalso()
    ventana, barra, pj = _escena(app, rep=rep)
    try:
        rep.estado_cambio.emit("sonando")
        assert pj._t_baile.isActive()
        barra.hide()                                            # pantalla completa: sin barra, sin personaje
        pj.colocar()
        assert not pj.isVisible()
        _esperar_amp(app, pj, lambda: not pj._t_baile.isActive(), "sin reloj")
        barra.show()
        pj.colocar()
        assert pj._t_baile.isActive()
    finally:
        _cerrar(ventana)


def test_arrastrar_sigue_al_cursor_desde_donde_se_agarro(app):
    ventana, _b, pj = _escena(app)
    try:
        QTest.mousePress(pj, Qt.LeftButton, Qt.NoModifier, QPoint(40, 50))
        inicio = pj.pos()
        QTest.mouseMove(pj, QPoint(40 - 60, 50 - 70))            # el ratón fue 60 a la izquierda y 70 arriba
        assert pj.pos() == inicio + QPoint(-60, -70)             # y el personaje, justo lo mismo: sin retraso
        QTest.mouseRelease(pj, Qt.LeftButton, Qt.NoModifier, QPoint(40 - 60, 50 - 70))
    finally:
        _cerrar(ventana)


def test_aspecto_casilla_y_boton(app):
    from descargador.ui.aspecto import SelectorAspecto
    rep = RepFalso()
    ventana, _b, pj = _escena(app, rep=rep)
    ventana.personaje_fondo = pj
    try:
        s = SelectorAspecto(ventana.ajustes, ("cian", "oscuro"), ventana)
        assert s.baila.isChecked() and s.baila.text() == "Que baile con la música"
        assert s.bt_esquina.text() == "Devolverlo a su esquina"
        rep.estado_cambio.emit("sonando")
        assert pj._t_baile.isActive()
        s.baila.setChecked(False)
        assert ventana.ajustes["personaje_baila"] is False and not pj._quiere
        _arrastrar(pj, QPoint(30, 30), QPoint(-300, -300))
        assert not pj.en_la_esquina
        s.bt_esquina.click()
        assert pj.en_la_esquina and ventana.ajustes["personaje_x"] == -1
        # suelto (sin ventana con personaje): el botón solo borra el lugar guardado
        s2 = SelectorAspecto(Ajustes(acento="cian", fondo="oscuro", personaje_x=0.3, personaje_y=0.3), ("cian", "oscuro"))
        s2.bt_esquina.click()
        assert s2.a["personaje_x"] == -1 and s2.a["personaje_y"] == -1
    finally:
        _cerrar(ventana)
