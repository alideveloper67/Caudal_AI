# -*- coding: utf-8 -*-
"""Ecualizador avanzado (donadores y fundadores): 15 bandas, preamplificador, ajustes con nombre,
uno por salida que entra solo al cambiar de salida, candado sin beneficios y la detección de salida."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from descargador import eq_avanzado as EQ  # noqa: E402
from descargador import salida_audio as SA  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


class _Ajustes(dict):
    def __missing__(self, k):
        return None

    def guardar(self):
        self["_guardado"] = (self.get("_guardado") or 0) + 1


def test_bandas_y_preamp_se_limpian():
    assert len(EQ.FRECUENCIAS) == 15
    b = EQ.limpiar_bandas([30, -30, 1.26, "x", None])
    assert len(b) == 15 and b[:4] == [12.0, -12.0, 1.5, 0.0]
    assert EQ.limpiar_preamp(10) == 6.0 and EQ.limpiar_preamp(-20) == -12.0


def test_filtros_y_ganancia_previa():
    partes = EQ.partes_filtro([0] * 7 + [3] + [0] * 7)
    assert partes == ["equalizer=f=630:t=o:w=0.67:g=3.0"]
    # preamplificador -2 y una banda a +5: margen automático de 3 dB
    assert EQ.ganancia_previa([5] + [0] * 14, -2) == pytest.approx(-5.0)


def test_solo_suena_con_beneficios():
    a = _Ajustes(eq_avanzado=True)
    assert EQ.activo(a, True)
    assert not EQ.activo(a, False)


def test_guardar_cargar_y_borrar_ajustes_con_nombre():
    a = _Ajustes()
    assert set(EQ.guardados(a)) == set(EQ.INICIALES)          # de fábrica, para empezar
    assert EQ.guardar_ajuste(a, "  Mi   coche ", [2] * 15, -3) == "Mi coche"
    assert EQ.guardar_ajuste(a, "   ", [0] * 15, 0) == ""
    assert EQ.cargar_ajuste(a, "Mi coche")
    assert a["eq_av_bandas"] == [2.0] * 15 and a["eq_av_preamp"] == -3.0 and a["eq_av_nombre"] == "Mi coche"
    EQ.asignar_salida(a, "bluetooth", "Mi coche")
    EQ.borrar_ajuste(a, "Mi coche")
    assert "Mi coche" not in EQ.guardados(a)
    assert EQ.por_salida(a)["bluetooth"] == ""                # la salida se queda sin él


def test_no_caben_infinitos():
    a = _Ajustes()
    for i in range(EQ.MAX_GUARDADOS):
        EQ.guardar_ajuste(a, f"a{i}", [0] * 15, 0)
    assert EQ.guardar_ajuste(a, "uno más", [0] * 15, 0) == ""
    assert EQ.guardar_ajuste(a, "a1", [1] * 15, 0) == "a1"     # sobrescribir sí


def test_al_cambiar_de_salida_pone_su_ajuste_solo_al_cambiar():
    a = _Ajustes()
    EQ.guardar_ajuste(a, "Coche", [4] * 15, -4)
    EQ.asignar_salida(a, "bluetooth", "Coche")
    # primera lectura (al abrir la app): no pisa lo que haya
    assert EQ.al_cambiar_salida(a, True, None, "bluetooth") is None
    # la misma salida: nada
    assert EQ.al_cambiar_salida(a, True, "bluetooth", "bluetooth") is None
    # sin beneficios: nada
    assert EQ.al_cambiar_salida(a, False, "audifonos", "bluetooth") is None
    # cambio de verdad: se pone y se enciende el avanzado
    assert EQ.al_cambiar_salida(a, True, "audifonos", "bluetooth") == "Coche"
    assert a["eq_avanzado"] is True and a["eq_av_bandas"] == [4.0] * 15
    # una salida sin ajuste asignado no toca nada
    assert EQ.al_cambiar_salida(a, True, "bluetooth", "parlante") is None


def test_tipo_de_salida():
    assert SA.tipo_salida("Auriculares (Realtek)", 3, "HDAUDIO") == SA.AUDIFONOS
    assert SA.tipo_salida("Altavoces (Realtek)", 1, "HDAUDIO") == SA.PARLANTE
    assert SA.tipo_salida("Auriculares (WH-1000XM4)", 3, "BTHENUM") == SA.BLUETOOTH
    assert SA.tipo_salida("AirPods de Ana", None, "") == SA.BLUETOOTH
    assert SA.tipo_salida("Headset USB", None, "USB") == SA.AUDIFONOS
    assert SA.tipo_salida("", None, "") == SA.PARLANTE


def test_salida_actual_en_esta_pc():
    d = SA.salida_actual()
    if d is None:
        pytest.skip("este sistema no dice su salida")
    assert d["tipo"] in SA.TIPOS


def test_la_cadena_usa_el_avanzado_solo_con_beneficios():
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    r.ajustes = _Ajustes(ecualizador=True, eq_bandas=[2] + [0] * 9, eq_avanzado=True,
                         eq_av_bandas=[0] * 14 + [3], eq_av_preamp=-1.5, volumen_maximo="no")
    r.consultar_premium = lambda: True
    f = r.cadena_filtros()
    assert "f=16000:t=o:w=0.67:g=3.0" in f and "f=31:" not in f
    assert "volume=-3.30dB" in f                   # -1,5 de pre y -1,8 de margen
    r.consultar_premium = lambda: False            # sin beneficios: el normal de siempre
    f = r.cadena_filtros()
    assert "equalizer=f=31:t=o:w=1:g=2.0" in f and "w=0.67" not in f


# ------------------------------------------------------------ pantallas

class _Señal:
    def __init__(self):
        self.emitidos = []

    def emit(self, *a):
        self.emitidos.append(a)


class _Rep:
    actual = None

    def __init__(self):
        self.aplicado = 0

    def aplicar_sonido(self):
        self.aplicado += 1


class _Ctx:
    def __init__(self, premium):
        self.ajustes = _Ajustes(eq_avanzado=False, eq_av_bandas=[0] * 15, eq_av_preamp=0.0,
                                eq_av_nombre="", eq_av_guardados={}, eq_por_salida={})
        self.reproductor = _Rep()
        self.aviso = _Señal()
        self.sonido_cambio = _Señal()
        self.premium = type("G", (), {"premium": premium})()


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_sin_beneficios_sale_el_candado(app, monkeypatch):
    from descargador.ui import ecualizador_avanzado as UI
    vistos = []
    monkeypatch.setattr(UI, "aviso_bloqueado", lambda ctx, padre=None: vistos.append(ctx))
    ctx = _Ctx(False)
    assert UI.abrir(ctx) is None and vistos == [ctx]
    assert "donadores y fundadores" in UI.TEXTO_BLOQUEO


def test_dialogo_avanzado_se_oye_al_momento_y_cancelar_deshace(app):
    from descargador.ui.ecualizador_avanzado import DialogoEqAvanzado
    ctx = _Ctx(True)
    d = DialogoEqAvanzado(ctx)
    assert len(d.deslizadores) == 15
    d.deslizadores[3].setValue(7)                 # +3,5 dB
    assert ctx.ajustes["eq_avanzado"] is True and ctx.ajustes["eq_av_bandas"][3] == 3.5
    assert ctx.reproductor.aplicado >= 1
    d.reject()
    assert ctx.ajustes["eq_avanzado"] is False and ctx.ajustes["eq_av_bandas"] == [0] * 15


def test_dialogo_avanzado_elige_guardado_y_asigna_salida(app):
    from descargador.ui.ecualizador_avanzado import DialogoEqAvanzado
    ctx = _Ctx(True)
    d = DialogoEqAvanzado(ctx)
    nombre = list(EQ.INICIALES)[1]
    i = d.guardados.findText(nombre)
    d.guardados.setCurrentIndex(i)
    d._elegir_guardado(i)
    assert ctx.ajustes["eq_av_nombre"] == nombre and d.preamp() == EQ.INICIALES[nombre][1]
    combo = d.por_salida["parlante"]
    combo.setCurrentIndex(combo.findText(nombre))
    d._asignar("parlante")
    assert EQ.por_salida(ctx.ajustes)["parlante"] == nombre
    d.accept()
    assert ctx.ajustes["_guardado"] == 1 and ctx.aviso.emitidos


def test_vigia_de_salida_pone_el_ajuste_al_conectar(app):
    from descargador.ui.vigia_salida import VigiaSalida
    ctx = _Ctx(True)
    EQ.guardar_ajuste(ctx.ajustes, "Audífonos", [1] * 15, -1)
    EQ.asignar_salida(ctx.ajustes, "audifonos", "Audífonos")
    salidas = iter([{"tipo": "parlante", "nombre": "Altavoces"}, {"tipo": "audifonos", "nombre": "Auriculares"}])
    v = VigiaSalida(ctx, leer=lambda: next(salidas))
    v.mirar()
    assert ctx.ajustes["eq_avanzado"] is False          # arrancar no cambia nada
    v.mirar()
    assert ctx.ajustes["eq_avanzado"] is True and ctx.ajustes["eq_av_nombre"] == "Audífonos"
    assert ctx.reproductor.aplicado == 1 and "audífonos" in ctx.aviso.emitidos[-1][0]
