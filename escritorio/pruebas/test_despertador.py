# -*- coding: utf-8 -*-
"""Despertador con música: próxima vez, días, subida del volumen, qué suena sin internet, posponer y
apagar, guardado, el sonido suave y el gestor con un reproductor de mentira.
Sin ventanas a la vista (Qt offscreen), sin internet y sin sonar de verdad."""

import os
import random
import sys
import wave
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from descargador import despertador as dsp  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


def _alarma(**k):
    base = dsp.nueva_alarma()
    base.update(k)
    return dsp.normalizar(base)


# miércoles 19 de noviembre de 2025, 06:00
MIE = datetime(2025, 11, 19, 6, 0)


# ------------------------------------------------------------ próxima vez

def test_una_vez_hoy_si_no_paso_y_si_no_manana():
    a = _alarma(hora=7, minuto=30, dias=[])
    assert dsp.proxima_vez(a, MIE) == datetime(2025, 11, 19, 7, 30)
    assert dsp.proxima_vez(a, MIE.replace(hour=8)) == datetime(2025, 11, 20, 7, 30)


def test_entre_semana_salta_el_fin_de_semana():
    a = _alarma(hora=7, minuto=0, dias=[1, 2, 3, 4, 5])
    viernes_tarde = datetime(2025, 11, 21, 9, 0)
    assert dsp.proxima_vez(a, viernes_tarde) == datetime(2025, 11, 24, 7, 0)   # lunes


def test_misma_hora_exacta_ya_no_cuenta():
    a = _alarma(hora=6, minuto=0, dias=[3])
    assert dsp.proxima_vez(a, MIE) == datetime(2025, 11, 26, 6, 0)


def test_apagada_no_suena_y_pospuesta_manda():
    assert dsp.proxima_vez(_alarma(activa=False), MIE) is None
    p = dsp.posponer(_alarma(hora=6, minuto=0, posponer=9), MIE)
    assert dsp.proxima_vez(p, MIE) == MIE + timedelta(minutes=9)


def test_tras_sonar_apaga_la_de_una_vez_y_olvida_lo_pospuesto():
    una = dsp.tras_sonar(dsp.posponer(_alarma(dias=[]), MIE))
    assert una["activa"] is False and una["pospuesta_hasta"] == 0
    semanal = dsp.tras_sonar(_alarma(dias=[1, 2]))
    assert semanal["activa"] is True


def test_tocan_y_margen_de_media_hora():
    a = _alarma(hora=6, minuto=10, dias=[])
    assert dsp.tocan([a], MIE, MIE + timedelta(minutes=5)) == []
    assert dsp.tocan([a], MIE + timedelta(minutes=5), MIE + timedelta(minutes=11)) == [a]
    # la PC durmió toda la noche: a las 9 ya no suena la de las 6:10
    assert dsp.tocan([a], MIE - timedelta(hours=8), MIE.replace(hour=9)) == []
    # durmió, pero despertó a las 6:30: todavía suena
    assert dsp.tocan([a], MIE - timedelta(hours=8), MIE.replace(minute=30)) == [a]


# ------------------------------------------------------------ textos

def test_textos_de_dias_y_falta():
    assert dsp.texto_dias([]) == "Una vez"
    assert dsp.texto_dias([1, 2, 3, 4, 5, 6, 7]) == "Todos los días"
    assert dsp.texto_dias([5, 1, 2, 3, 4]) == "Entre semana"
    assert dsp.texto_dias([6, 7]) == "Fines de semana"
    assert dsp.texto_dias([1, 3]) == "Lun, Mié"
    assert dsp.texto_falta(7 * 3600 + 20 * 60) == "Suena en 7 h 20 min"
    assert dsp.texto_falta(30) == "Suena en 1 min"
    assert dsp.texto_falta(0) == "Suena en menos de un minuto"
    assert dsp.texto_falta(2 * 86400 + 3600) == "Suena en 2 días 1 h"


def test_normalizar_acota_valores_raros():
    a = dsp.normalizar({"hora": 99, "minuto": -3, "dias": [0, 3, "9", 3, 7], "volumen": 900,
                        "subida": -1, "posponer": 0, "fuente": {"tipo": "raro"}})
    assert (a["hora"], a["minuto"]) == (23, 0)
    assert a["dias"] == [3, 7]
    assert a["volumen"] == 100 and a["subida"] == 0 and a["posponer"] == 1
    assert a["fuente"]["tipo"] == "tono"


# ------------------------------------------------------------ volumen

def test_volumen_sube_poco_a_poco():
    assert dsp.factor_volumen(0, 60) == pytest.approx(dsp.VOLUMEN_INICIAL)
    assert dsp.factor_volumen(60, 60) == 1.0
    assert dsp.factor_volumen(120, 60) == 1.0
    assert dsp.factor_volumen(5, 0) == 1.0
    valores = [dsp.factor_volumen(t, 60) for t in range(0, 61, 5)]
    assert valores == sorted(valores)
    assert dsp.factor_volumen(15, 60) < 0.1        # al principio, muy bajito


# ------------------------------------------------------------ qué suena

P1 = {"clave": "yt:1", "video_id": "1", "titulo": "Uno"}
P2 = {"clave": "yt:2", "video_id": "2", "titulo": "Dos"}
LOCAL = {"clave": "local:3", "titulo": "Tres", "archivo": "C:/x.mp3"}


def _desc(*claves):
    return lambda p: p.get("clave") in claves


def test_con_red_suena_lo_elegido():
    a = _alarma(fuente={"tipo": "lista", "id": "1"})
    assert dsp.planear(a, True, [P1, P2], _desc(), [LOCAL]) == ("pistas", [P1, P2], "elegido")


def test_sin_red_suena_lo_descargado_de_lo_elegido():
    a = _alarma(fuente={"tipo": "lista", "id": "1"})
    assert dsp.planear(a, False, [P1, P2], _desc("yt:2"), [LOCAL]) == ("pistas", [P2], "descargado")


def test_sin_red_y_nada_descargado_suena_el_respaldo_y_si_no_el_tono():
    a = _alarma(fuente={"tipo": "cancion", "id": "yt:1"})
    tipo, pistas, motivo = dsp.planear(a, False, [P1], _desc("local:3"), [LOCAL])
    assert (tipo, pistas, motivo) == ("pistas", [LOCAL], "respaldo")
    assert dsp.planear(a, False, [P1], _desc(), [LOCAL]) == ("tono", [], "sin_musica")


def test_me_gusta_al_azar_baraja_y_tono_es_tono():
    a = _alarma(fuente={"tipo": "me_gusta", "id": "me_gusta"})
    muchas = [{"clave": f"yt:{i}"} for i in range(30)]
    _t, pistas, _m = dsp.planear(a, True, muchas, _desc(), [], random.Random(4))
    assert sorted(p["clave"] for p in pistas) == sorted(p["clave"] for p in muchas)
    assert pistas != muchas
    assert dsp.planear(_alarma(fuente={"tipo": "tono"}), True, [P1], _desc(), [])[0] == "tono"


# ------------------------------------------------------------ guardado y tono

def test_guardar_y_leer(tmp_path):
    ruta = tmp_path / "d.json"
    dsp.guardar([_alarma(hora=6, etiqueta="Trabajo")], ruta)
    leidas = dsp.leer(ruta)
    assert len(leidas) == 1 and leidas[0]["hora"] == 6 and leidas[0]["etiqueta"] == "Trabajo"
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    assert dsp.leer(tmp_path / "roto.json") == []


def test_tono_suave_se_repite_sin_clic():
    m = dsp.sintetizar_tono()
    assert len(m) == int(dsp.FRECUENCIA * 8.0)
    assert max(abs(v) for v in m) <= 32767 * 0.71
    assert abs(m[0]) < 50 and abs(m[-1]) < 50
    ruta = dsp.ruta_tono()
    with wave.open(str(ruta)) as w:
        assert w.getframerate() == dsp.FRECUENCIA and w.getnchannels() == 1


def test_tono_incluido_en_la_app_es_el_mismo():
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for rel in (("app", "assets", "despertador", "amanecer.wav"),
                ("app", "android", "app", "src", "main", "res", "raw", "despertador_amanecer.wav")):
        ruta = os.path.join(raiz, *rel)
        assert os.path.exists(ruta), ruta
        with wave.open(ruta) as w:
            assert w.getnframes() == int(dsp.FRECUENCIA * 8.0)


# ------------------------------------------------------------ gestor con reproductor de mentira

class _Rep(QObject):
    estado_cambio = Signal(str)
    pista_cambio = Signal(object)

    def __init__(self):
        super().__init__()
        self.disponible = True
        self.volumen = 55
        self.volumenes = []
        self.tocadas = []
        self.detenido = 0
        self._escucha_registrada = False

    def fijar_volumen(self, v):
        self.volumen = v
        self.volumenes.append(v)

    def reproducir_lista(self, pistas, contexto=None, modo=None, **_k):
        self.tocadas.append(("lista", [p.get("clave") for p in pistas]))

    def reproducir_pista(self, pista, contexto=None, modo=None, con_radio=True):
        self.tocadas.append(("pista", pista.get("clave")))
        self.pista_cambio.emit(pista)

    def detener(self):
        self.detenido += 1


class _Col:
    def __init__(self, gustan=(), descargadas=()):
        self._g = list(gustan)
        self._d = list(descargadas)

    def lista_me_gusta(self, filtro="", limite=None):
        return list(self._g)

    def descargadas(self, solo_audio=None, filtro=""):
        return list(self._d)

    def me_gusta(self, clave):
        return any(p.get("clave") == clave for p in self._g)

    def esta_descargada(self, p):
        return any(d.get("clave") == p.get("clave") for d in self._d)

    def pistas_de_lista(self, ident):
        return [P1, P2]

    def listas(self):
        return [{"id": 1, "nombre": "Mañanas"}]

    def estado(self, clave, defecto=None):
        return defecto


class _Aviso:
    def __init__(self):
        self.textos = []

    def mostrar(self, t, *a, **k):
        self.textos.append(t)


class _Ventana(QWidget):
    def __init__(self):
        super().__init__()
        self.aviso = _Aviso()

    def traer_al_frente(self):
        pass


class _Ctx:
    def __init__(self, col):
        self.reproductor = _Rep()
        self.coleccion = col


def _gestor(app, col, monkeypatch, red=True):
    from descargador.ui import despertador_ui as UI
    # sin hilos ni internet: se arranca al momento con la red que diga la prueba
    monkeypatch.setattr(UI, "en_segundo_plano", lambda f, ok=None, error=None, dueno=None: ok(red))
    ctx = _Ctx(col)
    g = UI.GestorDespertador(ctx, _Ventana())
    return g, ctx.reproductor


def test_gestor_suena_sube_y_pospone(app, monkeypatch):
    g, r = _gestor(app, _Col(gustan=[P1, P2]), monkeypatch)
    a = g.poner(_alarma(hora=6, minuto=0, dias=[], volumen=80, subida=60,
                        fuente={"tipo": "me_gusta", "id": "me_gusta"}))
    g.sonar(a)
    assert r.tocadas and r.tocadas[0][0] == "lista"
    assert r.volumenes[0] <= 3                       # empieza casi en silencio
    g._inicio -= 60                                  # pasó la subida entera
    g._paso_volumen()
    assert r.volumen == 80
    assert g._ventana_sonando is not None
    g.posponer()
    assert g.sonando is None and r.volumen == 55     # vuelve el volumen de antes
    guardada = [x for x in g.alarmas if x["id"] == a["id"]][0]
    assert guardada["pospuesta_hasta"] > 0
    assert any("Pospuesta" in t for t in g.ventana.aviso.textos)


def test_gestor_sin_red_ni_descargas_toca_el_tono_y_apaga(app, monkeypatch):
    g, r = _gestor(app, _Col(gustan=[P1]), monkeypatch, red=False)
    a = g.poner(_alarma(dias=[], fuente={"tipo": "cancion", "id": "yt:1", "pista": P1}))
    g.sonar(a)
    assert r.tocadas == [("pista", "despertador:tono")]
    assert r._escucha_registrada is True              # el tono no entra en tu resumen
    g.apagar()
    assert r.detenido == 1 and g.sonando is None
    assert [x for x in g.alarmas if x["id"] == a["id"]][0]["activa"] is False   # era de una vez


def test_gestor_apagar_y_seguir_no_detiene_la_musica(app, monkeypatch):
    g, r = _gestor(app, _Col(gustan=[P1, P2]), monkeypatch)
    a = g.poner(_alarma(dias=[1], fuente={"tipo": "lista", "id": "1"}))
    g.sonar(a)
    g.apagar(seguir=True)
    assert r.detenido == 0 and r.volumen == 55


def test_prueba_no_toca_lo_guardado(app, monkeypatch):
    g, r = _gestor(app, _Col(gustan=[P1]), monkeypatch)
    a = g.poner(_alarma(dias=[], fuente={"tipo": "tono"}))
    g.sonar(a, prueba=True)
    g.apagar()
    assert [x for x in g.alarmas if x["id"] == a["id"]][0]["activa"] is True


def test_editor_arma_la_alarma(app, monkeypatch):
    from descargador.ui import despertador_ui as UI
    g, _r = _gestor(app, _Col(gustan=[P1, P2]), monkeypatch)
    ed = UI.EditorAlarma(g, _alarma(hora=6, minuto=45, dias=[]), True)
    ed.botones_dia[6].setChecked(True)
    ed.tipo.setCurrentIndex(list(dsp.TIPOS).index("lista"))
    ed.opciones.setCurrentRow(0)
    a = ed.resultado()
    assert (a["hora"], a["minuto"], a["dias"]) == (6, 45, [6])
    assert a["fuente"]["tipo"] == "lista" and a["fuente"]["titulo"] == "Mañanas"
    ed.tipo.setCurrentIndex(list(dsp.TIPOS).index("cancion"))
    ed.buscar.setText("dos")
    visibles = [ed.opciones.item(i).text() for i in range(ed.opciones.count())
                if not ed.opciones.item(i).isHidden()]
    assert visibles == ["Dos"]


def test_dialogo_pinta_la_lista(app, monkeypatch):
    from descargador.ui import despertador_ui as UI
    g, _r = _gestor(app, _Col(), monkeypatch)
    g.poner(_alarma(hora=7, minuto=5, dias=[1, 2, 3, 4, 5]))
    d = UI.DialogoDespertador(g)
    assert "Suena en" in d.et_proxima.text()
    d.close()
