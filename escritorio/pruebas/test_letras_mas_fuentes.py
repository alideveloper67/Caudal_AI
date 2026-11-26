# -*- coding: utf-8 -*-
"""Más sitios donde hay letra (NetEase, Genius, subtítulos del autor) y ponerle tiempos a la que solo es
texto escuchando la canción. Sin red y sin reconocedor: todo con datos inventados."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import catalogo, letras_cache, letras_fuentes as F, sincronia_tareas as T  # noqa: E402

PISTA = {"video_id": "vvvvvvvvvvv", "titulo": "Tripolar", "artista": "Canserbero", "duracion": 240,
         "artistas": [{"nombre": "Canserbero"}]}


# ------------------------------------------------------------------ fuentes

def test_genius_saca_solo_la_letra():
    pagina = ('<div data-lyrics-container="true" class="x"><div data-exclude-from-selection="true"><div>12 '
              'Contributors</div></div>[Verso 1: <i>Canserbero</i>]<br/>Cicatrices mentales, mucha rabia<br/>Desde la '
              'infancia <a href="#"><span>hasta hoy</span></a><br/></div><p>anuncio</p>'
              '<div data-lyrics-container="true">[Coro]<br>Tripolar &amp; ya, no hay vuelta atrás en esta noche</div>')
    t = F.texto_genius(pagina)
    assert "Contributors" not in t and "[" not in t and "anuncio" not in t
    assert t.splitlines()[0] == "Cicatrices mentales, mucha rabia"
    assert "Desde la infancia hasta hoy" in t and "Tripolar & ya" in t
    assert F.texto_genius("<html>nada</html>") == ""


def test_netease_comprueba_la_cancion_y_quita_creditos(monkeypatch):
    lrc = "[00:00.00] 作词 : Alguien\n" + "\n".join(f"[00:{10 + i * 4:02d}.00]verso número {i} de la canción" for i in range(12))

    def responde(url, cabeceras=None, **k):
        if "search" in url:
            return {"result": {"songs": [
                {"id": 1, "name": "Tripolar", "artists": [{"name": "Otro Grupo"}], "duration": 240000},
                {"id": 2, "name": "Tripolar", "artists": [{"name": "Canserbero"}], "duration": 240000}]}}
        return {"lrc": {"lyric": lrc}}
    monkeypatch.setattr(F, "_json", responde)
    r = F.netease(PISTA)
    assert [x["id"] for x in r] == ["netease:2"]
    assert "作词" not in r[0]["plainLyrics"] and r[0]["syncedLyrics"].count("[") == 12


def test_netease_con_todo_en_cero_vale_solo_como_texto(monkeypatch):
    monkeypatch.setattr(F, "_json", lambda url, c=None, **k: {"result": {"songs": [
        {"id": 2, "name": "Tripolar", "artists": [{"name": "Canserbero"}], "duration": 240000}]}} if "search" in url
        else {"lrc": {"lyric": "\n".join(f"[00:00.00]un verso largo número {i}" for i in range(10))}})
    r = F.netease(PISTA)
    assert r and "syncedLyrics" not in r[0] and r[0]["plainLyrics"]


def test_subtitulos_vtt():
    vtt = ("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n♪ Hola <c>mundo</c> ♪\n\n00:00:03.000 --> 00:00:04.000\n"
           "[Música]\n\n01:02.500 --> 01:04.000\nadiós\n")
    assert F.vtt_a_lineas(vtt) == [(1000, "Hola mundo"), (62500, "adiós")]


@pytest.fixture
def activa(tmp_path):
    letras_cache.activar(tmp_path)
    yield
    letras_cache._carpeta = None


def _sin_letra(_p):
    return {"sincronizada": False, "lineas": [], "texto": "", "fuente": ""}


def test_sin_letra_se_prueba_en_los_demas_sitios(activa, monkeypatch):
    monkeypatch.setattr(catalogo, "_letras_principales", _sin_letra)
    monkeypatch.setattr(F, "netease", lambda p: [])
    monkeypatch.setattr(F, "subtitulos_video", lambda v: None)
    monkeypatch.setattr(F, "genius", lambda p: {"plainLyrics": "uno\ndos"})
    d = catalogo.letras(PISTA)
    assert d["texto"] == "uno\ndos" and d["fuente"] == "Genius" and not d["sincronizada"]
    # y queda guardada: la segunda vez no se pregunta a nadie
    monkeypatch.setattr(catalogo, "_letras_principales", lambda p: (_ for _ in ()).throw(AssertionError("otra vez")))
    assert catalogo.letras(PISTA)["texto"] == "uno\ndos"


def test_la_de_netease_con_tiempos_gana_al_texto(activa, monkeypatch):
    monkeypatch.setattr(catalogo, "_letras_principales", _sin_letra)
    lrc = "\n".join(f"[00:{10 + i:02d}.00]verso {i}" for i in range(12))
    monkeypatch.setattr(F, "netease", lambda p: [{"trackName": "Tripolar", "artistName": "Canserbero", "duration": 240.5,
                                                  "syncedLyrics": lrc, "plainLyrics": "x"}])
    d = catalogo.letras(PISTA)
    assert d["sincronizada"] and d["fuente"] == "NetEase" and len(d["lineas"]) == 12


def test_un_fallo_de_red_se_reintenta_y_no_se_da_por_perdido(activa, monkeypatch):
    veces = []

    def principal(p):
        veces.append(1)
        if len(veces) == 1:
            catalogo._anotar_fallo_letra()
            return _sin_letra(p)
        return {"sincronizada": True, "lineas": [(0, "a")], "texto": "a", "fuente": "x"}
    monkeypatch.setattr(catalogo, "_letras_principales", principal)
    monkeypatch.setattr(catalogo.time, "sleep", lambda s: None)
    assert catalogo.letras(PISTA)["sincronizada"] and len(veces) == 2


def test_sin_red_no_se_guarda_que_no_hay_letra(activa, monkeypatch):
    def principal(p):
        catalogo._anotar_fallo_letra()
        return _sin_letra(p)
    monkeypatch.setattr(catalogo, "_letras_principales", principal)
    monkeypatch.setattr(catalogo.time, "sleep", lambda s: None)
    monkeypatch.setattr(F, "netease", lambda p: [])
    monkeypatch.setattr(F, "subtitulos_video", lambda v: None)
    monkeypatch.setattr(F, "genius", lambda p: None)
    catalogo.letras(PISTA)
    assert letras_cache.leer(PISTA) is None


# ------------------------------------------------------------------ tiempos para una letra que es solo texto

LETRA = ["Cicatrices mentales mucha rabia desde la infancia", "Recuerdos circunstanciales carencia perseverancia",
         "Hasta envidia de quienes con solo nacer ya tienen todo", "Unos nacen en flores y otros en lodo",
         "Pero hoy es un día en que se acabaron mis modales", "Mientras aparecen voy a lanzarles jabón",
         "La pregunta reiterada sobre la personalidad", "Unos replican que es un fantasma otros un profeta"]


def _oidas(versos, desde=10.0, cada=4.0, quitar=()):
    salida = []
    for k, v in enumerate(versos):
        if k in quitar:
            continue
        for i, w in enumerate(v.split()):
            salida.append((desde + k * cada + i * 0.35, w))
    return salida


def test_los_tiempos_salen_de_lo_que_se_oye():
    r = T.tiempos_de_texto(LETRA, _oidas(LETRA), 60)
    assert [t for _m, t in r] == LETRA
    for k, (ms, _t) in enumerate(r):
        assert abs(ms / 1000 - (10 + k * 4)) < 0.2


def test_los_versos_que_no_se_entienden_van_entre_sus_vecinos():
    r = T.tiempos_de_texto(LETRA, _oidas(LETRA, quitar=(2, 5)), 60)
    ms = [m for m, _t in r]
    assert len(r) == len(LETRA) and ms == sorted(ms)
    assert 14000 < ms[2] < 22000


def test_si_casi_nada_coincide_no_se_inventan_tiempos():
    otra = "esto que suena no tiene absolutamente nada que ver con aquello".split()
    assert T.tiempos_de_texto(LETRA, [(i * 0.5, w) for i, w in enumerate(otra * 4)], 60) is None
    assert T.tiempos_de_texto(LETRA[:3], _oidas(LETRA[:3]), 60) is None
    assert T.tiempos_de_texto(LETRA, [], 60) is None


def test_un_coro_repetido_cae_cada_vez_en_su_sitio():
    coro = "Baila conmigo esta noche hasta que salga el sol"
    versos = LETRA[:3] + [coro] + LETRA[3:6] + [coro]
    r = dict()
    for ms, t in T.tiempos_de_texto(versos, _oidas(versos), 60):
        r.setdefault(t, []).append(ms / 1000)
    assert len(r[coro]) == 2 and abs(r[coro][0] - 22) < 0.3 and abs(r[coro][1] - 38) < 0.3


def test_transcribir_solo_si_el_reconocedor_esta_seguro():
    def seg(i, texto, **k):
        return dict({"desde": i * 5.0, "texto": texto, "logprob": -0.4, "sin_voz": 0.1, "compresion": 1.5,
                     "palabras": [(i * 5.0 + j * 0.4, w) for j, w in enumerate(texto.split())]}, **k)
    buenos = [seg(i, v) for i, v in enumerate(LETRA)]
    r = T.lineas_de_segmentos({"segmentos": buenos, "idioma_prob": 0.9})
    assert len(r["lineas"]) >= 8 and r["lineas"][0][0] == 0
    assert T.lineas_de_segmentos({"segmentos": buenos, "idioma_prob": 0.3}) == {}
    assert T.lineas_de_segmentos({"segmentos": [dict(s, logprob=-1.5) for s in buenos], "idioma_prob": 0.9}) == {}
    bucle = [seg(i, "gracias por ver el video hasta la próxima amigos") for i in range(12)]
    assert T.lineas_de_segmentos({"segmentos": bucle, "idioma_prob": 0.9}) == {}
    assert T.lineas_de_segmentos(None) == {}


def test_tarea_del_ayudante_con_datos_de_json(monkeypatch):
    visto = {}

    def verificar(lineas, fuente, dur, alternativas, datos, misma, voz):
        visto.update(lineas=lineas, ref=datos.get("ref_lineas"), otras=alternativas())
        return {"accion": "bien"}
    monkeypatch.setattr(T, "verificar", verificar)
    assert T.tarea("verificar", {"lineas": [[0, "a"]], "fuente": {"archivo": "x"}, "datos": {"ref_lineas": [[5, "b"]]},
                                 "alternativas": [{"x": 1}]}) == {"accion": "bien"}
    assert visto == {"lineas": [(0, "a")], "ref": [(5, "b")], "otras": [{"x": 1}]}
    with pytest.raises(ValueError):
        T.tarea("otra", {})
