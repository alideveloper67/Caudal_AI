# -*- coding: utf-8 -*-
"""Aviso de errores (descargador/aviso_errores.py): sin datos personales, casilla para apagarlo,
cola en el disco sin red, freno contra inundaciones, ganchos de la interfaz y de los hilos, y el
cierre de la vez anterior. Sin internet: el envío se sustituye por una función de prueba."""

import os
import sys
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import aviso_errores as AE  # noqa: E402


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    viejos = (sys.excepthook, threading.excepthook)
    AE._estado.update(carpeta=str(tmp_path), pantalla="", capturas=0, version="9.9.9", enviar=None)
    # que ningún temporizador real mande nada durante la prueba
    monkeypatch.setattr(AE, "_programar_envio", lambda *a, **k: None)
    yield tmp_path
    sys.excepthook, threading.excepthook = viejos
    f = AE._estado.get("cierre")
    if f is not None:
        import faulthandler
        faulthandler.disable()
        f.close()
        AE._estado["cierre"] = None
    AE._estado["carpeta"] = None


def _error(mensaje="fallo"):
    try:
        raise ValueError(mensaje)
    except ValueError:
        return sys.exc_info()


class Envio:
    def __init__(self, codigo=201):
        self.codigo, self.filas = codigo, []

    def __call__(self, fila):
        self.filas.append(fila)
        return self.codigo


# ---------------------------------------------------------------- privacidad

def test_limpiar_quita_lo_personal():
    t = AE.limpiar(r'File "C:\Users\María José\AppData\Roaming\x.py", ana@usuarios.caudal.app '
                   "https://sitio.com/ruta?token=abc#x eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.firma "
                   "/home/pedro/caudal /Users/luisa/Library clave ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ab")
    for no in ("María", "José", "ana@", "token=abc", "eyJhbGci", "pedro", "luisa", "ABCDEFGHIJ"):
        assert no not in t, no
    assert r"C:\Users\~\AppData" in t and "https://sitio.com/ruta?…" in t and "<correo>" in t


def test_informe_lleva_lo_justo_y_ninguna_cuenta():
    tipo, valor, tb = _error(r"no se abrió C:\Users\Ana\Music\cancion.mp3")
    inf = AE.informe_de(tipo, valor, tb, pantalla="Ventana > PaginaInicio", version="2.7.2", sistema="Windows 10")
    assert set(inf) == {"plataforma", "version", "sistema", "pantalla", "origen", "tipo", "mensaje", "traza",
                        "huella", "veces", "primera_vez", "ultima_vez"}
    assert inf["tipo"] == "ValueError" and inf["version"] == "2.7.2" and inf["plataforma"] == "windows"
    assert "Ana" not in inf["mensaje"] and "Ana" not in inf["traza"]
    assert "test_aviso_errores.py" in inf["traza"] and len(inf["huella"]) == 20


def test_misma_huella_aunque_cambie_la_linea_o_el_mensaje():
    a = AE.informe_de(*_error("uno"), version="1")
    b = AE.informe_de(*_error("dos"), version="2")
    assert a["huella"] == b["huella"]
    try:
        {}["x"]
    except KeyError:
        c = AE.informe_de(*sys.exc_info())
    assert c["huella"] != a["huella"]


def test_traza_larga_se_recorta_por_delante():
    inf = AE.informe_texto("Cierre inesperado", "x", "linea A\n" * 1500 + "FINAL\n" + "linea B\n" * 1500, version="1")
    assert len(inf["traza"]) <= 8000 and inf["traza"].startswith("…") and inf["traza"].endswith("linea B\n")


# ---------------------------------------------------------------- casilla y cola

def test_casilla_apagada_no_guarda_nada(aislado):
    AE.poner_activo(False)
    assert AE.activo() is False
    assert AE.encolar(AE.informe_de(*_error())) is False
    assert AE.cola() == []
    AE.poner_activo(True)
    assert AE.activo() is True


def test_apagar_vacia_la_cola():
    AE.encolar(AE.informe_de(*_error()))
    assert len(AE.cola()) == 1
    AE.poner_activo(False)
    AE.poner_activo(True)
    assert AE.cola() == []


def test_repetidos_se_juntan_y_la_cola_tiene_tope():
    inf = AE.informe_de(*_error())
    for _ in range(5):
        AE.encolar(inf)
    c = AE.cola()
    assert len(c) == 1 and c[0]["veces"] == 5
    for i in range(AE.TOPE_COLA + 10):
        x = dict(inf, huella=f"{i:020x}", ultima_vez=1000 + i)
        AE.encolar(x)
    assert len(AE.cola()) == AE.TOPE_COLA


def test_sin_red_queda_en_cola_y_sale_despues():
    AE.encolar(AE.informe_de(*_error()))
    assert AE.enviar_pendientes(Envio(0)) == 0          # sin red
    assert len(AE.cola()) == 1
    envio = Envio(201)
    assert AE.enviar_pendientes(envio) == 1
    assert AE.cola() == []
    fila = envio.filas[0]
    assert fila["version"] and fila["veces"] == 1
    assert "primera_vez" in fila and fila["primera_vez"].endswith("Z")
    assert "user_id" not in fila and "usuario" not in fila


def test_mismo_error_no_sale_dos_veces_en_6_horas():
    inf = AE.informe_de(*_error())
    AE.encolar(inf)
    ahora = time.time()
    assert AE.enviar_pendientes(Envio(), ahora=ahora) == 1
    AE.encolar(inf)
    assert AE.enviar_pendientes(Envio(), ahora=ahora + 60) == 0
    assert len(AE.cola()) == 1                          # espera su turno con las veces juntas
    assert AE.enviar_pendientes(Envio(), ahora=ahora + AE.ESPERA_MISMO + 1) == 1


def test_tope_diario():
    for i in range(AE.TOPE_DIA + 5):
        AE.encolar(dict(AE.informe_de(*_error()), huella=f"{i:020x}"))
    assert AE.enviar_pendientes(Envio()) == min(AE.TOPE_DIA, AE.TOPE_COLA)
    assert AE.enviar_pendientes(Envio()) == 0           # el resto, mañana


def test_sin_tabla_en_el_servidor_se_pausa_un_dia():
    AE.encolar(AE.informe_de(*_error()))
    envio = Envio(404)
    assert AE.enviar_pendientes(envio) == 0 and len(envio.filas) == 1
    assert AE.enviar_pendientes(Envio(201)) == 0        # en pausa
    assert AE.enviar_pendientes(Envio(201), ahora=time.time() + AE.PAUSA_SIN_TABLA + 1) == 1


def test_lo_que_el_servidor_rechaza_no_se_reintenta():
    AE.encolar(AE.informe_de(*_error()))
    AE.enviar_pendientes(Envio(400))
    assert AE.cola() == []


# ---------------------------------------------------------------- ganchos

@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_ganchos_capturan_interfaz_e_hilos_y_llaman_a_los_anteriores(aislado):
    vistos = []
    sys.excepthook = lambda *a: vistos.append("viejo")
    AE.activar(aislado, version="9.9.9", demora=None)
    AE.fijar_pantalla("PaginaLogros")
    sys.excepthook(*_error("interfaz"))
    assert vistos == ["viejo"]

    def falla():
        raise RuntimeError("en un hilo")
    h = threading.Thread(target=falla, name="Trabajo-12")
    h.start()
    h.join()
    c = {x["tipo"]: x for x in AE.cola()}
    assert c["ValueError"]["pantalla"] == "PaginaLogros" and c["ValueError"]["origen"] == "interfaz"
    assert c["RuntimeError"]["origen"] == "hilo:Trabajo-"


def test_convive_con_el_cuaderno_de_fallos(aislado):
    """Como en main.py: primero registro_fallos (fallos.log) y luego el aviso; los dos se enteran."""
    from descargador import registro_fallos
    registro_fallos.activar(aislado)
    AE.activar(aislado, demora=None)
    sys.excepthook(*_error("los dos"))
    log = (aislado / "fallos.log").read_text(encoding="utf-8")
    assert "los dos" in log
    assert AE.cola()[0]["mensaje"] == "los dos"


def test_salir_con_ctrl_c_no_es_un_error(aislado):
    AE.activar(aislado, demora=None)
    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        AE.capturar(*sys.exc_info())
    assert AE.cola() == []


def test_tope_por_sesion(aislado):
    AE.activar(aislado, demora=None)
    for i in range(AE.TOPE_SESION + 20):
        AE.capturar(*_error(str(i)))
    assert AE._estado["capturas"] == AE.TOPE_SESION + 20
    assert AE.cola()[0]["veces"] == AE.TOPE_SESION


def test_cierre_de_la_vez_anterior_se_manda_solo_si_no_salio_bien(aislado):
    ruta = os.path.join(str(aislado), "cierre_nativo.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write('Windows fatal exception: access violation\n\nCurrent thread 0x1 (most recent call first):\n'
                '  File "C:\\Users\\Ana\\caudal\\reproduccion.py", line 12 in tocar\n')
    AE._escribir("aviso_errores_sesion.json", {"limpio": False})
    AE.activar(aislado, demora=None)
    c = AE.cola()
    assert len(c) == 1 and c[0]["tipo"] == "Cierre inesperado" and "Ana" not in c[0]["traza"]
    # esta sesión sale bien: lo que escriba faulthandler ya no cuenta
    AE.marcar_salida_limpia()
    AE.poner_activo(False)
    AE.poner_activo(True)
    with open(ruta, "a", encoding="utf-8") as f:
        f.write("algo\n")
    AE.activar(aislado, demora=None)
    assert AE.cola() == []


def test_ajuste_casilla_qt(aislado):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from descargador.ui.ajuste_aviso_errores import casilla_aviso_errores
    c = casilla_aviso_errores()
    assert c.isChecked()
    c.setChecked(False)
    assert AE.activo() is False
