# -*- coding: utf-8 -*-
"""Que la letra sea la de la canción: cuentas puras de descargador/elegir_letra.py y catalogo.letras sin red."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from descargador import catalogo, elegir_letra as e  # noqa: E402


def pista(titulo, *artistas, dur=200, vid=""):
    return {"titulo": titulo, "artistas": [{"nombre": a} for a in artistas], "duracion": dur, "video_id": vid}


def ficha(titulo, artista, dur=200, sinc=True, texto="una letra cualquiera", **mas):
    return dict({"id": f"{titulo}{artista}{dur}{sinc}", "trackName": titulo, "artistName": artista, "duration": dur,
                 "plainLyrics": texto, "syncedLyrics": f"[00:01.00] {texto}" if sinc else None}, **mas)


@pytest.mark.parametrize("crudo, limpio", [
    ("Hello (Official Music Video)", "Hello"),
    ("Adele - Hello (Official Video) [4K]", "Adele - Hello"),
    ("Gasolina (feat. Glory)", "Gasolina"),
    ("01 La Flaca", "La Flaca"),
    ("24 horas", "24 horas"),
    ("7 rings", "7 rings"),
    ("La Camisa Negra (Full Phatt Remix)", "La Camisa Negra (Full Phatt Remix)"),
    ("Flaca | Andrés Calamaro | Video Oficial", "Flaca"),
])
def test_titulo_limpio(crudo, limpio):
    assert e.titulo_limpio(crudo) == limpio


@pytest.mark.parametrize("p, c, vale", [
    (pista("Hello", "Adele"), ficha("Hello", "Adele"), True),
    (pista("Hello", "Adele"), ficha("Hello", "Lionel Richie"), False),
    (pista("Hello", "Adele"), ficha("Hello, Goodbye", "Adele"), False),
    (pista("Tití Me Preguntó", "Bad Bunny"), ficha("Titi Me Pregunto", "Bad Bunny"), True),
    (pista("Eres", "Café Tacvba"), ficha("Eres", "Cafe Tacuba"), True),
    (pista("Lágrimas", "Grupo Néctar"), ficha("Lágrimas", "Néctar"), True),
    (pista("Despacito", "Luis Fonsi", "Daddy Yankee"), ficha("Despacito", "Luis Fonsi feat. Daddy Yankee"), True),
    (pista("Despacito", "Luis Fonsi"), ficha("Despacito (Remix)", "Luis Fonsi, Justin Bieber"), False),
    (pista("Despacito (Remix)", "Luis Fonsi"), ficha("Despacito", "Luis Fonsi"), False),
    (pista("Mojado (Versión Acústica)", "Ricardo Arjona"), ficha("Mojado", "Ricardo Arjona"), False),
    (pista("Bohemian Rhapsody - Remastered 2011", "Queen"), ficha("Bohemian Rhapsody", "Queen"), True),
    (pista("De Música Ligera (Remasterizado 2007)", "Soda Stereo"), ficha("De Musica Ligera", "Soda Stereo"), True),
    (pista("Adele - Hello (Official Video)", "Canal Cualquiera"), ficha("Hello", "Adele"), True),
    (pista("Hello - Adele", "Canal Cualquiera"), ficha("Hello", "Adele"), True),
    (pista("De YouTube", "x", dur=19), ficha("Alcohol", "X"), False),
    (pista("アイドル", "YOASOBI"), ficha("アイドル", "YOASOBI"), True),
    (pista("アイドル", "YOASOBI"), ficha("夜に駆ける", "YOASOBI"), False),
    (pista("Hello", "Adele"), ficha("Hello", "Adele", instrumental=True), False),
])
def test_es_la_cancion(p, c, vale):
    assert e.es_la_cancion(c, p) is vale


def test_los_tiempos_solo_si_dura_lo_mismo():
    p = pista("Hello", "Adele", dur=367)
    album, video = ficha("Hello", "Adele", 295), ficha("Hello", "Adele", 366)
    assert e.elegir([album, video], p)[0] is video
    con, texto, otra = e.elegir([album], p)
    assert con is None and texto is album and otra is album


def test_el_texto_de_youtube_descarta_otra_letra():
    buena = "si estoy tomando es porque estoy echando alcohol a las heridas que por dentro estoy curando hoy"
    mala = "ella durmió al calor de las masas y yo desperté queriendo soñarla algún tiempo atrás pensé en escribirle"
    p = pista("Alcohol", "Grupo X")
    a, b = ficha("Alcohol", "Grupo X", 200, texto=mala), ficha("Alcohol", "Grupo X", 201, texto=buena)
    assert e.elegir([a, b], p)[0] is a
    assert e.elegir([a, b], p, buena)[0] is b
    assert e.elegir([a], p, buena) == (None, None, None)


def test_lrc_con_offset_marcas_de_palabra_y_repetidas():
    assert catalogo._lrc_a_lineas("[offset:+500]\n[00:10.00]Uno\n[00:20.50]<00:20.50> Dos <00:21.00> tres\n[00:30.00][00:40.00]Coro") == [
        (9500, "Uno"), (20000, "Dos tres"), (29500, "Coro"), (39500, "Coro")]


def _sin_red(monkeypatch, youtube, fichas):
    monkeypatch.setattr(catalogo, "_letra_youtube", lambda v: youtube)
    monkeypatch.setattr(catalogo, "_candidatas_lrclib", lambda p: fichas)


def test_primero_los_tiempos_de_youtube_para_ese_video(monkeypatch):
    _sin_red(monkeypatch, ([(1000, "hola")], "hola", "Musixmatch"), [ficha("Hello", "Adele")])
    l = catalogo.letras(pista("Hello", "Adele", vid="v"))
    assert l["sincronizada"] and l["lineas"] == [(1000, "hola")] and l["verificada"]


def test_nunca_la_letra_de_otra_cancion(monkeypatch):
    _sin_red(monkeypatch, ([], "", ""), [ficha("Otra cosa", "Alguien"), ficha("Hello", "Lionel Richie")])
    l = catalogo.letras(pista("Hello", "Adele"))
    assert not l["sincronizada"] and not l["texto"] and not l["lineas"]


def test_otra_duracion_queda_en_duda_hasta_medirla(monkeypatch):
    from descargador.ui.sincronia_auto import sin_tiempos
    _sin_red(monkeypatch, ([], "", ""), [ficha("Hello", "Adele", 295)])
    l = catalogo.letras(pista("Hello", "Adele", dur=367))
    assert l["sincronizada"] and l["otra_duracion"]
    s = sin_tiempos(l)
    assert not s["sincronizada"] and s["lineas"] == [] and s["texto"]
    assert l["lineas"], "la original no se toca"


def test_sin_red_no_rompe(monkeypatch):
    def cae(*_a, **_k):
        raise catalogo.requests.ConnectionError()
    monkeypatch.setattr(catalogo.requests, "get", cae)
    monkeypatch.setattr(catalogo, "_yt", cae)
    l = catalogo.letras(pista("Hello", "Adele", vid="v"))
    assert l["texto"] == "" and not l["sincronizada"]
    assert catalogo.letras_alternativas(pista("Hello", "Adele")) == []
