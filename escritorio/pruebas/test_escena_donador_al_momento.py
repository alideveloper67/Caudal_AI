# -*- coding: utf-8 -*-
"""La escena no espera al refresco periódico (20 min) para saber si alguien es donador: al abrirla y al
tocar un escenario bloqueado pregunta al servidor, y si ya dona el fondo se pone solo."""
import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import premium as P  # noqa: E402
from descargador.ui.escena import ventana as V  # noqa: E402
from test_premium import CtxFalso, SesionFalsa, esperar  # noqa: E402

E = V.EscenaEscritorio
METODOS = ("_es_donador", "_preguntar_donador", "_soltar_espera_donador", "_estado_donador_llego",
           "_sin_respuesta_donador", "_avisar_solo_donadores", "_fondo_elegido", "_preparar_video")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")


def _escena(ctx):
    """Una escena a medias: solo la lógica del fondo, sin ventanas."""
    esc = types.SimpleNamespace(ctx=ctx, abierta=True, _escenario_negado=False, _fondo_pendiente=None,
                                _esperando_donador=False, AVISO_SOLO_DONADORES=E.AVISO_SOLO_DONADORES,
                                ESPERA_DONADOR_MS=E.ESPERA_DONADOR_MS)
    for m in METODOS:
        setattr(esc, m, types.MethodType(getattr(E, m), esc))
    esc.puestos, esc.preparados = [], []
    esc.poner_fondo = esc.puestos.append
    esc._ruta_propia_valida = lambda: True
    esc._preparar_video = lambda: esc.preparados.append(1)
    return esc


def _ctx(app, premium_servidor):
    ctx = CtxFalso(SesionFalsa({"mi_premium": premium_servidor,
                                "GET perfiles": [{"marco": "ninguno", "efecto_nombre": "ninguno",
                                                  "tema_premium": "ninguno"}]}))
    ctx.avisos = []
    ctx.avisar = ctx.avisos.append
    ctx.premium = P.GestorPremium(ctx)       # sin refrescar: lo guardado dice que NO es donador
    return ctx


def test_quien_acaba_de_donar_pone_el_escenario_al_tocarlo(app):
    ctx = _ctx(app, {"premium": True, "tipo": "donador", "vence": None})
    esc = _escena(ctx)
    assert not esc._es_donador()
    E._fondo_elegido(esc, types.SimpleNamespace(data=lambda: "goku"))
    assert esc.puestos == [] and ctx.avisos == []          # no se le dice «solo donadores» antes de preguntar
    esperar(app, lambda: esc.puestos == ["goku"], "escenario puesto tras preguntar al servidor")
    assert ctx.avisos == [] and not esc._esperando_donador


def test_quien_no_dona_recibe_el_aviso_tras_preguntar(app):
    ctx = _ctx(app, {"premium": False})
    esc = _escena(ctx)
    E._fondo_elegido(esc, types.SimpleNamespace(data=lambda: "goku"))
    esperar(app, lambda: ctx.avisos, "aviso de solo donadores")
    assert esc.puestos == [] and "donadores" in ctx.avisos[0]


def test_al_abrir_el_escenario_guardado_aparece_cuando_llega_el_si(app):
    ctx = _ctx(app, {"premium": True, "tipo": "donador", "vence": None})
    esc = _escena(ctx)
    esc._escenario_negado = True                         # se puso la carátula porque lo guardado decía no
    assert esc._preguntar_donador()
    esperar(app, lambda: esc.preparados, "escenario guardado vuelve a prepararse")
    assert esc.puestos == [] and ctx.avisos == []


def test_sin_sesion_el_aviso_es_inmediato(app):
    ctx = _ctx(app, {"premium": True})
    ctx.cuenta = {}
    esc = _escena(ctx)
    E._fondo_elegido(esc, types.SimpleNamespace(data=lambda: "goku"))
    assert esc.puestos == [] and ctx.avisos and "donadores" in ctx.avisos[0]


def test_sin_red_se_avisa_al_vencer_la_espera(app):
    ctx = _ctx(app, {"premium": True})
    ctx.cuenta["sesion"].sin_red = True
    esc = _escena(ctx)
    esc.ESPERA_DONADOR_MS = 50
    E._fondo_elegido(esc, types.SimpleNamespace(data=lambda: "goku"))
    esperar(app, lambda: ctx.avisos, "aviso tras la espera")
    assert esc.puestos == [] and not esc._esperando_donador
