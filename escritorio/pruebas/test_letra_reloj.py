# -*- coding: utf-8 -*-
"""El reloj de la letra de la escena: no se adelanta si el audio se atasca, no tiembla hacia atrás
por avisos de posición con retraso y solo salta ante un cambio grande (búsqueda)."""
import types

from descargador.ui.escena import ventana as V


def _escena(estado="sonando", modo="audio"):
    e = types.SimpleNamespace()
    e.r = types.SimpleNamespace(estado=estado, modo=modo, velocidad=1.0, actual=None)
    e._pos, e._pos_t, e._dur, e._dur_letra = 0.0, 0.0, 0.0, 0.0
    e._ms_mostrado = None
    e.ctx = types.SimpleNamespace(ajustes={"letra_desfases": {}})
    e._desfase_letra = lambda: 0
    e._desfase_video = lambda: 0
    return e


def ms(e, ahora):
    return V.EscenaEscritorio._ms_letra(e, ahora) - V.ADELANTO_LETRA_MS


def test_avanza_entre_avisos():
    e = _escena()
    e._pos, e._pos_t = 10.0, 100.0
    assert ms(e, 100.0) == 10000
    assert ms(e, 100.25) == 10250


def test_no_se_adelanta_si_el_audio_se_atasca():
    e = _escena()
    e._pos, e._pos_t = 10.0, 100.0
    assert ms(e, 105.0) == 10000 + int(V.MAX_EXTRAPOLAR_S * 1000)


def test_no_retrocede_por_un_aviso_con_retraso():
    e = _escena()
    e._pos, e._pos_t = 10.0, 100.0
    adelante = ms(e, 100.5)                 # 10500
    e._pos, e._pos_t = 10.3, 100.5          # el aviso llega atrasado: 10300
    assert ms(e, 100.5) == adelante         # espera, no tiembla hacia atrás
    assert ms(e, 100.8) == 10600            # y sigue cuando la música lo alcanza


def test_salta_si_la_persona_busca_atras():
    e = _escena()
    e._pos, e._pos_t = 60.0, 100.0
    ms(e, 100.0)
    e._pos, e._pos_t = 5.0, 100.1
    assert ms(e, 100.1) == 5000


def test_en_pausa_no_avanza():
    e = _escena(estado="pausa")
    e._pos, e._pos_t = 10.0, 100.0
    assert ms(e, 103.0) == 10000
