# -*- coding: utf-8 -*-
"""Traduccion de letras, sin salir a internet."""

from descargador import traductor


def _limpiar():
    traductor._CACHE.clear()


def test_reparte_por_lineas(monkeypatch):
    _limpiar()
    monkeypatch.setattr(traductor, "_google", lambda t, d: (t.replace("love", "amor").replace("night", "noche"), "en"))
    r = traductor.traducir("a", ["my love", "", "the night"])
    assert r == ["my amor", "", "the noche"]


def test_ya_en_espanol(monkeypatch):
    _limpiar()
    monkeypatch.setattr(traductor, "_google", lambda t, d: (t, "es"))
    assert traductor.traducir("b", ["te quiero"]) == traductor.MISMO_IDIOMA


def test_si_google_falla_usa_mymemory(monkeypatch):
    _limpiar()

    def roto(t, d):
        raise RuntimeError("429")

    monkeypatch.setattr(traductor, "_google", roto)
    monkeypatch.setattr(traductor, "_mymemory", lambda t, d: ("hola", "en"))
    assert traductor.traducir("c", ["hello"]) == ["hola"]


def test_sin_red_no_se_guarda(monkeypatch):
    _limpiar()

    def roto(t, d):
        raise RuntimeError("sin red")

    monkeypatch.setattr(traductor, "_google", roto)
    monkeypatch.setattr(traductor, "_mymemory", roto)
    assert traductor.traducir("d", ["hello"]) is None
    assert not traductor._CACHE


def test_lee_respuesta_de_google():
    d = [[["Siempre te amaré\n", "I will always love you\n"], ["Adiós", "Goodbye"]], None, "en"]
    assert traductor.leer_google(d) == ("Siempre te amaré\nAdiós", "en")
