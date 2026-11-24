# -*- coding: utf-8 -*-
"""Poner la letra a tiempo comparando el sonido del video con el de la canción oficial."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

np = pytest.importorskip("numpy")

from descargador import catalogo, cotejo_audio as c, elegir_letra as e  # noqa: E402
from descargador.ui import sincronia_auto as s  # noqa: E402

HZ = c.HZ


def cancion(semilla, segundos):
    r = random.Random(semilla)
    x = np.zeros(segundos * HZ, np.float32)
    t = 0.0
    while t < segundos - 1:
        f, dur, fuerza = 180 * 2 ** (r.random() * 4), 0.1 + r.random() * 0.3, 0.2 + r.random() * 0.5
        i = np.arange(int(dur * HZ))
        i0 = int(t * HZ)
        x[i0:i0 + len(i)] += fuerza * np.exp(-i / (HZ * dur * 0.4)) * np.sin(2 * np.pi * f * i / HZ)
        t += 0.18 + r.random() * 0.35
    return x


def ruido(segundos, fuerza=0.05):
    return (np.random.default_rng(9).random(int(segundos * HZ)) - 0.5).astype(np.float32) * fuerza


def des(v, a):
    return c.desfases(c.rasgos(v), c.rasgos(a))


def test_un_video_con_intro():
    a = cancion(1, 100)
    t = des(np.concatenate([ruido(4.22), a]), a)
    assert len(t) == 1 and abs(t[0][1] - 4.22) < 0.05


def test_empieza_mas_tarde_con_ruido_y_otro_volumen():
    a = cancion(2, 100)
    v = a[int(7.5 * HZ):] * 0.4
    # como en la vida real, ninguna de las dos tiene silencio absoluto
    t = des(v + np.random.default_rng(3).normal(0, 0.001, len(v)), a + ruido(100, 0.004)[:len(a)])
    assert abs(t[0][1] + 7.5) < 0.05


def test_cortado_por_una_escena():
    a = cancion(4, 140)
    t = des(np.concatenate([a[:60 * HZ], ruido(15), a[60 * HZ:]]), a)
    assert abs(t[0][1]) < 0.05 and abs(t[-1][1] - 15) < 0.1
    l = c.colocar([(10000, "antes"), (100000, "después")], t)
    assert abs(l[0][0] - 10000) < 60 and abs(l[1][0] - 115000) < 120


def test_otra_cancion_no_se_toca():
    assert des(cancion(5, 100), cancion(6, 100)) is None
    assert des(ruido(100), cancion(6, 100)) is None
    assert c.desfases(c.rasgos(np.zeros(HZ)), c.rasgos(cancion(6, 100))) is None


DATOS = {"sincronizada": True, "lineas": [(5000, "hola")], "texto": "hola", "otra_duracion": True,
         "ref": "of", "ref_lineas": [(5000, "hola")]}


def test_verificar_usa_el_sonido_antes_que_la_voz(monkeypatch):
    monkeypatch.setattr(c, "cotejar", lambda f, v: [(0.0, 4.22)])
    monkeypatch.setattr(s.sincronia_letra, "verificar", lambda *a: pytest.fail("no hace falta escuchar"))
    r = s.verificar(DATOS["lineas"], {}, 100, None, DATOS)
    assert r["accion"] == "cambiar" and r["datos"]["lineas"] == [(9220, "hola")]
    assert "otra_duracion" not in r["datos"] and "ref" not in r["datos"]
    assert DATOS["lineas"] == [(5000, "hola")], "la original no se toca"


def test_si_es_la_misma_grabacion_no_se_compara(monkeypatch):
    monkeypatch.setattr(c, "cotejar", lambda f, v: pytest.fail("es la misma"))
    assert s.verificar(DATOS["lineas"], {}, 100, None, DATOS, misma=True)["accion"] == "bien"


def test_sin_cotejo_se_escucha_y_sin_voz_no_se_hace_nada(monkeypatch):
    monkeypatch.setattr(c, "cotejar", lambda f, v: None)
    monkeypatch.setattr(s.sincronia_letra, "verificar", lambda *a: {"accion": "corregir", "desfase_ms": 700})
    assert s.verificar(DATOS["lineas"], {}, 100, None, DATOS)["accion"] == "corregir"
    assert s.verificar(DATOS["lineas"], {}, 100, None, DATOS, voz=False)["accion"] == "nada"


def _letras(monkeypatch, oficial, fichas, dur):
    monkeypatch.setattr(catalogo, "_letra_youtube", lambda v: ([], "", ""))
    monkeypatch.setattr(catalogo, "_cancion_oficial", lambda p, t="": oficial)
    monkeypatch.setattr(catalogo, "_candidatas_lrclib", lambda p: fichas)
    return catalogo.letras({"titulo": "666", "artistas": [{"nombre": "Yan Block"}], "duracion": dur, "video_id": "v"})


VERSOS = ["el diablo vestido de prada", "para el vip tengo entrada", "tu eres peor que la fama", "cuando yo mas te quiero"]


def _oficial(dur):
    l = [(1000 * i + 1000, t) for i, t in enumerate(VERSOS)]
    return {"video_id": "of", "duracion": dur, "lineas": l, "texto": "\n".join(VERSOS), "fuente": "Musixmatch"}


def _ficha(corrido, dur):
    return {"id": 1, "trackName": "666", "artistName": "Yan Block", "duration": dur, "plainLyrics": "\n".join(VERSOS),
            "syncedLyrics": "\n".join(f"[00:{i + 1 + corrido:02d}.00]{t}" for i, t in enumerate(VERSOS))}


def test_un_video_que_dura_como_la_cancion_usa_sus_tiempos(monkeypatch):
    l = _letras(monkeypatch, _oficial(156), [], 157)
    assert l["sincronizada"] and not l.get("otra_duracion") and l["ref"] == "of"


def test_una_ficha_con_los_tiempos_del_disco_no_engana(monkeypatch):
    l = _letras(monkeypatch, _oficial(141), [_ficha(0, 157)], 157)
    assert l["otra_duracion"] and l["ref"] == "of", "dura como el video pero lleva los tiempos del disco"


def test_una_ficha_hecha_para_el_video_si_vale(monkeypatch):
    l = _letras(monkeypatch, _oficial(141), [_ficha(9, 157)], 157)
    assert not l.get("otra_duracion") and l["lineas"][0][0] == 10000


def test_titulo_con_invitado_delante():
    assert e.titulo_limpio("Junior H Ft. Jose Mejia - Suena (Audio Oficial)") == "Junior H - Suena"
    assert e.titulo_limpio("Gasolina ft. Glory") == "Gasolina"
