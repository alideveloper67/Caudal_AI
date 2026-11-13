# -*- coding: utf-8 -*-
"""Pruebas de la logica de Caudal Escritorio que no necesita red ni ventanas.

    cd escritorio
    python -m pytest pruebas -q
"""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    """Cada prueba con su propia carpeta de datos: nunca toca los del usuario."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


# ---------------------------------------------------------------- formatos

def test_maxima_calidad_no_se_limita_a_h264():
    from descargador.motor import selector_formato
    # antes, MP4 preferia H.264 y eso dejaba los videos en 1080p como mucho
    assert selector_formato("mejor", "mp4", "completo", "maxima") == "bv*+ba/b"
    assert "avc1" not in selector_formato("2160", "mp4", "completo", "maxima")
    assert "[height<=2160]" in selector_formato("2160", "mp4", "completo", "maxima")


def test_compatible_prefiere_h264_con_respaldo():
    from descargador.motor import selector_formato
    s = selector_formato("1080", "mp4", "completo", "compatible")
    assert s.startswith("bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/")
    assert s.endswith("bv*+ba/b")


def test_audio_sin_recomprimir_elige_la_pista_adecuada():
    from descargador.motor import selector_formato
    assert selector_formato("mejor", tipo="audio", formato_audio="m4a").startswith("ba[ext=m4a]")
    assert selector_formato("mejor", tipo="audio", formato_audio="opus").startswith("ba[acodec=opus]")
    assert selector_formato("mejor", tipo="audio", formato_audio="mp3") == "ba/b"


def test_solo_video_no_lleva_sonido():
    from descargador.motor import selector_formato
    assert "+ba" not in selector_formato("1080", "mp4", "video", "maxima")


# ---------------------------------------------------------------- catalogo

def test_traducciones_de_secciones_y_subtitulos():
    from descargador import catalogo as c
    assert c.traducir("Quick picks") == "Selección rápida"
    assert c.traducir("Similar to Bad Bunny") == "Parecido a Bad Bunny"
    assert c.traducir("Playlists by KAROL G") == "Listas de KAROL G"
    assert c.traducir_subtitulo("Album • 2021") == "Álbum • 2021"
    assert c.traducir_subtitulo("1.2M views") == "1.2M reproducciones"


def test_segundos_y_video_id():
    from descargador import catalogo as c
    assert c.segundos("3:25") == 205
    assert c.segundos("1:02:03") == 3723
    assert c.segundos("") == 0
    assert c.video_id_de("https://music.youtube.com/watch?v=SRkr9PyBBuU&list=X") == "SRkr9PyBBuU"
    assert c.video_id_de("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert c.video_id_de("https://www.youtube.com/shorts/abcdefghijk") == "abcdefghijk"
    assert c.video_id_de("https://www.tiktok.com/@a/video/1") == ""


def test_miniatura_se_pide_grande():
    from descargador import catalogo as c
    url = "https://lh3.googleusercontent.com/abc=w120-h120-l90-rj"
    assert c.agrandar_miniatura(url, 544).endswith("=w544-h544-l90-rj")


def test_letras_lrc():
    from descargador import catalogo as c
    lineas = c._lrc_a_lineas("[00:03.70] Hola\n[00:06.49]Adiós\n[01:00.00][01:30.00] Coro")
    assert lineas[0] == (3700, "Hola")
    assert lineas[1] == (6490, "Adiós")
    assert (60000, "Coro") in lineas and (90000, "Coro") in lineas


def test_cancion_de_album_no_es_video():
    from descargador import catalogo as c
    p = c.pista_de_ytm({"videoId": "SRkr9PyBBuU", "title": "Tusa",
                        "videoType": "MUSIC_VIDEO_TYPE_OMV",
                        "artists": [{"name": "KAROL G", "id": "UC1"}], "duration": "3:21"})
    assert p["es_video"] is False
    assert p["artista"] == "KAROL G" and p["duracion"] == 201
    v = c.pista_de_ytm({"videoId": "SRkr9PyBBuU", "title": "Tusa", "resultType": "video"})
    assert v["es_video"] is True


def test_edl_une_imagen_y_sonido():
    from descargador.reproduccion import _edl
    e = _edl("https://v/x", "https://a/yy")
    assert e == ("edl://!new_stream;!no_clip;!no_chapters;%11%https://v/x"
                 ";!new_stream;!no_clip;!no_chapters;%12%https://a/yy")


# ---------------------------------------------------------------- coleccion

def _pista(n, artista="Artista", aid="UCa"):
    from descargador import catalogo as c
    return c.nueva_pista(f"vid{n:08d}", f"Canción {n}", [{"nombre": artista, "id": aid}],
                         {"nombre": "Álbum", "id": "MPRE"}, 180, "https://x/img")


def test_me_gusta_y_listas():
    from descargador.coleccion import Coleccion
    col = Coleccion()
    a, b, cc = _pista(1), _pista(2), _pista(3)
    assert col.alternar_me_gusta(a) is True
    assert col.me_gusta(a["clave"])
    assert col.alternar_me_gusta(a) is False
    lid = col.crear_lista("Para correr")
    with pytest.raises(ValueError):
        col.crear_lista("Para correr")
    assert col.agregar_a_lista(lid, [a, b, cc]) == 3
    assert col.agregar_a_lista(lid, [a]) == 0           # no se duplica
    col.mover_en_lista(lid, [cc["clave"], a["clave"], b["clave"]])
    assert [p["titulo"] for p in col.pistas_de_lista(lid)] == ["Canción 3", "Canción 1", "Canción 2"]
    col.quitar_de_lista(lid, a["clave"])
    assert len(col.pistas_de_lista(lid)) == 2
    assert col.pistas_de_lista(lid, "3")[0]["titulo"] == "Canción 3"
    col.editar_lista(lid, nombre="Correr", fijada=True)
    assert col.listas()[0]["nombre"] == "Correr" and col.listas()[0]["fijada"] == 1
    assert col.nombre_libre() == "Mi lista n.º 1"


def test_escuchas_contextos_y_artistas_frecuentes():
    from descargador.coleccion import Coleccion
    col = Coleccion()
    for i in range(3):
        col.registrar_escucha(_pista(1, "KAROL G", "UCk"), {"tipo": "album", "id": "MPRE1",
                                                            "titulo": "KG0516"})
    col.registrar_escucha(_pista(2, "Bad Bunny", "UCb"), None)
    assert [p["titulo"] for p in col.escuchado_hace_poco()] == ["Canción 2", "Canción 1"]
    assert col.contextos_recientes()[0]["id"] == "MPRE1"
    assert col.artistas_frecuentes()[0]["nombre"] == "KAROL G"


def test_guardados_y_busquedas():
    from descargador.coleccion import Coleccion
    col = Coleccion()
    alb = {"tipo": "album", "id": "MPRE9", "titulo": "Un álbum", "pistas": [1, 2]}
    col.guardar(alb)
    assert col.guardado("album", "MPRE9")
    assert "pistas" not in col.guardados("album")[0]
    col.olvidar("album", "MPRE9")
    assert not col.guardados("album")
    col.anotar_busqueda("karol g")
    col.anotar_busqueda("bad bunny")
    assert col.busquedas_recientes()[0] == "bad bunny"


def test_listas_de_versiones_anteriores_se_migran(datos_aislados):
    """Las listas viejas apuntaban a ids de descargas: se convierten solas."""
    from descargador.config import carpeta_datos
    ruta = carpeta_datos() / "historial.db"
    con = sqlite3.connect(ruta)
    con.execute("CREATE TABLE listas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, creada REAL)")
    con.execute("CREATE TABLE lista_canciones (lista_id INTEGER, descarga_id INTEGER, orden INTEGER,"
                " PRIMARY KEY (lista_id, descarga_id))")
    con.execute("CREATE TABLE descargas (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, titulo TEXT,"
                " plataforma TEXT, archivo TEXT, tamano INTEGER, duracion INTEGER, calidad TEXT,"
                " estado TEXT, fecha REAL, caratula TEXT, es_audio INTEGER, autor TEXT)")
    archivo = datos_aislados / "cancion.mp3"
    archivo.write_bytes(b"x")
    con.execute("INSERT INTO descargas (url, titulo, archivo, estado, es_audio, autor) VALUES "
                "('https://www.youtube.com/watch?v=SRkr9PyBBuU', 'Tusa', ?, 'completada', 1, 'KAROL G')",
                (str(archivo),))
    con.execute("INSERT INTO listas (nombre, creada) VALUES ('Vieja', 0)")
    con.execute("INSERT INTO lista_canciones VALUES (1, 1, 1)")
    con.commit()
    con.close()

    from descargador.coleccion import Coleccion
    col = Coleccion()
    pistas = col.pistas_de_lista(1)
    assert len(pistas) == 1 and pistas[0]["titulo"] == "Tusa"
    assert pistas[0]["archivo"] == str(archivo)
    # y la cancion de YouTube se reconoce como descargada por su id
    assert col.copia_local("SRkr9PyBBuU")[0] == str(archivo)
    assert col.esta_descargada({"video_id": "SRkr9PyBBuU"})


# ---------------------------------------------------------------- cola

class _Falso:
    """Reproductor sin motores: solo para probar la logica de la cola."""


def _cola(n=5):
    from descargador.config import Ajustes
    from descargador.coleccion import Coleccion
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    # lo minimo para usar los metodos de la cola sin crear mpv
    from PySide6.QtCore import QObject
    QObject.__init__(r)
    r.ajustes = Ajustes()
    r.coleccion = Coleccion()
    r.secuencia, r.original, r.proximas = [], [], []
    r.pos = -1
    r.actual = None
    r.aleatorio = False
    r.repetir = "no"
    pistas = [_pista(i) for i in range(n)]
    r.secuencia = list(pistas)
    r.original = list(pistas)
    r.pos = 0
    r.actual = pistas[0]
    return r, pistas


def test_cola_manual_va_antes_y_aleatorio_no_pierde_nada():
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication([])
    r, pistas = _cola(6)
    extra = _pista(99)
    r.proximas = [extra]
    assert r._mirar_siguiente() is extra
    assert r._avanzar() is extra and r.secuencia[1] is extra and r.pos == 1
    antes = {id(p) for p in r.secuencia}
    r.ajustes.guardar = lambda: None
    r.alternar_aleatorio()
    r.alternar_aleatorio()
    assert {id(p) for p in r.secuencia} == antes
    assert r.secuencia[r.pos] is extra


def test_repetir_todo_vuelve_al_principio():
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication([])
    r, pistas = _cola(3)
    r.pos = 2
    r.actual = pistas[2]
    assert r._avanzar() is None
    r.repetir = "todo"
    assert r._avanzar() is pistas[0] and r.pos == 0
