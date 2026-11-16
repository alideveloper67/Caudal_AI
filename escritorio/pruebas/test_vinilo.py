# -*- coding: utf-8 -*-
"""Modo vinilo: gira solo al sonar, el brazo se posa, la pantalla se mantiene encendida.
Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_vinilo")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _R(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = None
        self.estado = "pausa"
        self._posicion = 0.0
        self._duracion = 200.0
        self.llamadas = []

    def anterior(self):
        self.llamadas.append("anterior")

    def siguiente(self):
        self.llamadas.append("siguiente")

    def alternar(self):
        self.llamadas.append("alternar")

    def buscar(self, s):
        self.llamadas.append(("buscar", s))

    def fijar(self, estado):
        self.estado = estado
        self.estado_cambio.emit(estado)


class _Aj(dict):
    guardados = 0

    def guardar(self):
        self.guardados += 1


class _Ctx:
    def __init__(self):
        self.reproductor = _R()
        self.ajustes = _Aj(vinilo_pantalla=True, vinilo_auto=False)


def caratula(c1, c2):
    img = QImage(400, 400, QImage.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 400, 400)
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    p.fillRect(0, 0, 400, 400, QBrush(g))
    p.setPen(QColor(255, 255, 255, 200))
    p.setBrush(QColor(255, 255, 255, 60))
    p.drawEllipse(80, 80, 240, 240)
    p.drawRect(150, 150, 100, 100)
    p.end()
    return img


IMGS = {"u1": caratula("#E8590C", "#7A1BFF"), "u2": caratula("#0EA5E9", "#14B8A6")}
P1 = {"clave": "a", "titulo": "Medianoche en Lima", "artista": "Las Estrellas del Sur",
      "miniatura": "u1"}
P2 = {"clave": "b", "titulo": "Otra canción", "artista": "Otro artista", "miniatura": "u2"}


@pytest.fixture
def vinilo(app, monkeypatch):
    from descargador.ui import imagenes, vinilo as V
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(IMGS[url]))
    llamadas = []

    class _K32:
        def SetThreadExecutionState(self, v):
            llamadas.append(int(getattr(v, "value", v)))
            return 0

    class _W:
        kernel32 = _K32()
    monkeypatch.setattr(V.ctypes, "windll", _W(), raising=False)
    monkeypatch.setattr(V.sys, "platform", "win32")
    ctx = _Ctx()
    ctx.reproductor.actual = P1
    w = V.PaginaVinilo(ctx)
    w.resize(1280, 800)
    w.llamadas = llamadas
    yield w
    w.hide()
    w.deleteLater()


def avanzar(w, seg, paso=0.016):
    for _ in range(int(seg / paso)):
        w._cuadro(paso)


def test_gira_solo_al_sonar_y_frena_con_inercia(vinilo):
    w = vinilo
    w.show()
    r = w.r
    assert w.velocidad == 0 and not w.reloj.isActive()
    r.fijar("sonando")
    assert w.reloj.isActive()
    a0 = w.angulo
    avanzar(w, 0.3)
    assert 0 < w.velocidad < 200          # arranca con inercia, no de golpe
    avanzar(w, 5)
    assert abs(w.velocidad - 200) < 2     # 33 1/3 rpm = 200 grados/s
    r.fijar("pausa")
    avanzar(w, 0.3)
    assert 0 < w.velocidad < 200          # sigue girando un poco al frenar
    a1 = w.angulo
    avanzar(w, 12)
    assert w.velocidad == 0
    a2 = w.angulo
    avanzar(w, 1)
    assert w.angulo == a2 and a1 != a0
    assert not w.reloj.isActive()         # quieto: no consume


def test_aguja_se_posa_y_se_levanta(vinilo):
    w = vinilo
    w.show()
    reposo = w.giro_brazo()
    w.r.fijar("sonando")
    avanzar(w, 3)
    assert w.aguja == 1.0
    puesto = w.giro_brazo()
    assert abs(puesto - reposo) > 10
    w.r._posicion = 100.0
    w.r.posicion_cambio.emit(100.0)
    avanzar(w, 3)
    assert w.giro_brazo() != puesto       # avanza hacia el centro con la cancion
    w.r.fijar("pausa")
    avanzar(w, 2)
    assert w.aguja == 0.0 and abs(w.giro_brazo() - reposo) < 0.01


def test_cambiar_de_cancion_cambia_etiqueta_y_levanta_aguja(vinilo):
    w = vinilo
    w.show()
    assert w.etiqueta_clave == "a"
    w._preparar()
    clave_antes = w._pm_disco.cacheKey()
    w.r.fijar("sonando")
    avanzar(w, 3)
    assert w.aguja == 1.0
    w.r.actual = P2
    w.r.pista_cambio.emit(P2)
    avanzar(w, 0.2)
    assert w.aguja < 1.0                  # se levanta
    avanzar(w, 3)
    assert w.etiqueta_clave == "b"
    assert w.et_titulo._texto == "Otra canción"
    w._preparar()
    assert w._pm_disco.cacheKey() != clave_antes
    assert w.aguja == 1.0                 # y vuelve a posarse


def test_sin_timers_si_esta_oculto(vinilo):
    w = vinilo
    w.show()
    w.r.fijar("sonando")
    assert w.reloj.isActive()
    w.hide()
    assert not w.reloj.isActive() and not w._t_pausa.isActive()
    w.r.fijar("pausa")
    w.r.fijar("sonando")
    assert not w.reloj.isActive()         # oculto no se arranca


def test_pantalla_encendida(vinilo):
    from descargador.ui import vinilo as V
    w = vinilo
    llam = w.llamadas
    activar = V.ES_CONTINUOUS | V.ES_DISPLAY_REQUIRED | V.ES_SYSTEM_REQUIRED
    w.show()
    assert llam == []                     # pausado: aun nada
    w.r.fijar("sonando")
    assert llam == [activar]
    w.r.fijar("pausa")
    assert w._t_pausa.isActive() and w.pantalla.activa   # 60 s de gracia
    w._t_pausa.timeout.emit()
    assert llam[-1] == V.ES_CONTINUOUS and not w.pantalla.activa
    w.r.fijar("sonando")
    assert llam[-1] == activar
    w.hide()                              # salir libera
    assert llam[-1] == V.ES_CONTINUOUS and not w.pantalla.activa
    w.show()
    assert llam[-1] == activar            # sigue sonando: vuelve a activarse
    w.bt_pantalla.setChecked(False)       # el interruptor libera
    assert llam[-1] == V.ES_CONTINUOUS
    assert w.ctx.ajustes["vinilo_pantalla"] is False and w.ctx.ajustes.guardados == 1
    w.bt_pantalla.setChecked(True)
    assert llam[-1] == activar
    w.destroyed.emit()                    # cerrar la ventana libera
    assert llam[-1] == V.ES_CONTINUOUS


def test_botones_y_barra(vinilo):
    w = vinilo
    w.show()
    w.bt_anterior.click()
    w.bt_play.click()
    w.bt_siguiente.click()
    assert w.r.llamadas == ["anterior", "alternar", "siguiente"]
    w._soltado(0.5)
    assert w.r.llamadas[-1] == ("buscar", 100.0)
    visto = []
    w.volver.connect(lambda: visto.append(1))
    w.bt_cerrar.click()
    assert visto == [1]


def test_capturas(vinilo):
    os.makedirs(CAPTURAS, exist_ok=True)
    w = vinilo
    w.show()
    w.r._posicion = 62.0
    w.r.posicion_cambio.emit(62.0)
    w.r.fijar("sonando")
    avanzar(w, 6.4)
    w.grab().save(os.path.join(CAPTURAS, "sonando.png"))
    w.r.fijar("pausa")
    avanzar(w, 14)
    w.grab().save(os.path.join(CAPTURAS, "pausado.png"))
    w.r.actual = P2
    w.r.pista_cambio.emit(P2)
    w.r.fijar("sonando")
    avanzar(w, 0.5)
    w.grab().save(os.path.join(CAPTURAS, "cambio_a_mitad.png"))
    w.resize(900, 640)
    avanzar(w, 3)
    w.grab().save(os.path.join(CAPTURAS, "pequeno.png"))
