# -*- coding: utf-8 -*-
"""Traer los me gusta desde un archivo (Spotify, Google Takeout, tablas y texto pegado)."""

import io
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import archivo_me_gusta as A  # noqa: E402

URI = "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
BIBLIOTECA = {"tracks": [{"artist": "Yeyo", "album": "X", "track": "Perdóname", "uri": URI},
                         {"artist": "Cidtronyck", "album": "", "track": "Esta Noche", "uri": ""}],
              "albums": [], "shows": []}


def guardar(tmp_path, nombre, datos):
    f = tmp_path / nombre
    f.write_bytes(datos if isinstance(datos, bytes) else datos.encode("utf-8"))
    return f


def zip_de(tmp_path, archivos, nombre="datos.zip"):
    f = tmp_path / nombre
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        for n, c in archivos.items():
            z.writestr(n, c)
    return f


def nombres(r):
    return [(c["artista"], c["titulo"]) for c in r["canciones"]]


def test_spotify_json_y_zip(tmp_path):
    texto = json.dumps(BIBLIOTECA, ensure_ascii=False)
    r = A.desde_archivo(guardar(tmp_path, "YourLibrary.json", texto))
    assert r["servicio"] == "spotify" and nombres(r) == [("Yeyo", "Perdóname"), ("Cidtronyck", "Esta Noche")]
    assert r["canciones"][0]["externa"] == "sp:4uLU6hMCjMI75M1A2tKUQC"
    z = zip_de(tmp_path, {"Spotify Account Data/YourLibrary.json": texto,
                          "Spotify Account Data/StreamingHistory_music_0.json": "[]",
                          "Spotify Account Data/Userdata.json": "{}"})
    assert nombres(A.desde_archivo(z)) == nombres(r)


@pytest.mark.parametrize("datos", [{"playlists": []}, [{"endTime": "x", "msPlayed": 1}], {"otra": 1}])
def test_json_que_no_es_el_de_los_me_gusta_lo_explica(tmp_path, datos):
    with pytest.raises(A.ErrorArchivo, match="YourLibrary"):
        A.desde_archivo(guardar(tmp_path, "x.json", json.dumps(datos)))


def test_json_roto(tmp_path):
    with pytest.raises(A.ErrorArchivo, match="dañado"):
        A.desde_archivo(guardar(tmp_path, "x.json", "{no"))


def test_takeout_en_espanol_elige_los_me_gusta(tmp_path):
    z = zip_de(tmp_path, {
        "Takeout/YouTube y YouTube Music/playlists/Vídeos que me gustan-vídeos.csv":
            "ID de vídeo,Marca de tiempo de creación\ndQw4w9WgXcQ,2024-01-01\nabcdefghijk,2024-01-02\n",
        "Takeout/YouTube y YouTube Music/playlists/Para correr-vídeos.csv":
            "ID de vídeo,Marca de tiempo\nzzzzzzzzzzz,2024\n",
        "Takeout/YouTube y YouTube Music/historial/watch.json": "[]"})
    r = A.desde_archivo(z)
    assert r["servicio"] == "youtube" and r["plataforma"] == "YouTube Music"
    assert [c["externa"] for c in r["canciones"]] == ["yt:dQw4w9WgXcQ", "yt:abcdefghijk"]
    assert r["canciones"][0]["url"].endswith("dQw4w9WgXcQ") and not r["aviso"]


def test_takeout_en_ingles_sin_me_gusta_usa_la_biblioteca_y_lo_dice(tmp_path):
    z = zip_de(tmp_path, {"Takeout/YouTube and YouTube Music/music (library and uploads)/music library songs.csv":
                          "Video ID,Song Title,Album Title,Artist Name 1,Artist Name 2\n"
                          "dQw4w9WgXcQ,Never Gonna,Album,Rick Astley,\n"})
    r = A.desde_archivo(z)
    assert nombres(r) == [("Rick Astley", "Never Gonna")] and "biblioteca" in r["aviso"]


def test_takeout_con_lineas_antes_de_la_cabecera(tmp_path):
    r = A.desde_archivo(guardar(tmp_path, "Liked videos.csv",
                                "Playlist ID,Channel ID,Title\nLL,UC1,Liked videos\n\nVideo ID,Time Added\n"
                                "dQw4w9WgXcQ,2020\n"))
    assert [c["externa"] for c in r["canciones"]] == ["yt:dQw4w9WgXcQ"]


def test_csv_de_exportify_con_bom_comillas_y_milisegundos(tmp_path):
    texto = ('﻿"Track URI","Track Name","Album Name","Artist Name(s)","Duration (ms)"\n'
             f'"{URI}","Hola, ""mundo""","A","Uno, Dos",215000\n')
    r = A.desde_archivo(guardar(tmp_path, "liked.csv", texto))
    c = r["canciones"][0]
    assert r["servicio"] == "spotify" and c["titulo"] == 'Hola, "mundo"' and c["artista"] == "Uno, Dos"
    assert c["duracion"] == 215


def test_csv_con_punto_y_coma_en_cp1252_y_con_tabuladores(tmp_path):
    r = A.desde_archivo(guardar(tmp_path, "s.csv", "Título;Artista;Duración\nCanción;Ñandú;3:25\n".encode("cp1252")))
    assert nombres(r) == [("Ñandú", "Canción")] and r["canciones"][0]["duracion"] == 205
    r = A.desde_archivo(guardar(tmp_path, "s.tsv", "title\tartist\nA\tB\n"))
    assert nombres(r) == [("B", "A")]
    r = A.desde_archivo(guardar(tmp_path, "u16.csv", "title,artist\nA,B\n".encode("utf-16")))
    assert nombres(r) == [("B", "A")]


def test_csv_sin_columnas_utiles(tmp_path):
    with pytest.raises(A.ErrorArchivo, match="columnas"):
        A.desde_archivo(guardar(tmp_path, "x.csv", "fecha,importe\n1,2\n"))


def test_texto_pegado():
    r = A.desde_texto("1. Yeyo - Oye Morena\n\n• Junior H – Suena\nGasolina\nhttps://youtu.be/dQw4w9WgXcQ\n"
                      "Yeyo - Oye Morena\nhttps://otra.web/x")
    assert nombres(r) == [("Yeyo", "Oye Morena"), ("Junior H", "Suena"), ("", "Gasolina"), ("", "")]
    assert r["canciones"][-1]["externa"] == "yt:dQw4w9WgXcQ"
    assert nombres(A.desde_texto("Blink - 182 - Dumpweed"))[0][0] == "Blink"
    with pytest.raises(A.ErrorArchivo, match="Artista - Título"):
        A.desde_texto("   \n")


def test_txt_que_es_una_tabla(tmp_path):
    assert nombres(A.desde_archivo(guardar(tmp_path, "t.txt", "title,artist\nA,B\n"))) == [("B", "A")]
    assert nombres(A.desde_archivo(guardar(tmp_path, "u.txt", "B - A\n"))) == [("B", "A")]


def test_bomba_zip_no_se_abre(tmp_path):
    z = zip_de(tmp_path, {"YourLibrary.json": b"0" * (A.MAX_TEXTO + 10)})
    with pytest.raises(A.ErrorArchivo, match="demasiado grande"):
        A.desde_archivo(z)


def test_zip_que_miente_en_el_tamano_se_corta_al_leer(tmp_path, monkeypatch):
    z = zip_de(tmp_path, {"YourLibrary.json": json.dumps(BIBLIOTECA) + " " * 5000})
    monkeypatch.setattr(A, "MAX_TOTAL_ZIP", 1000)
    with pytest.raises(A.ErrorArchivo, match="demasiado grande"):
        A.desde_archivo(z)


def test_zip_danado_sin_nada_util_o_con_varias_listas(tmp_path):
    with pytest.raises(A.ErrorArchivo, match="zip"):
        A.desde_archivo(guardar(tmp_path, "x.zip", b"no soy un zip"))
    with pytest.raises(A.ErrorArchivo, match="no encontré"):
        A.desde_archivo(zip_de(tmp_path, {"foto.jpg": b"x"}, "a.zip"))
    with pytest.raises(A.ErrorArchivo, match="varias listas"):
        A.desde_archivo(zip_de(tmp_path, {"a.csv": "title,artist\nA,B", "b.csv": "title,artist\nC,D"}, "b.zip"))
    datos = io.BytesIO()
    with zipfile.ZipFile(datos, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("YourLibrary.json", json.dumps(BIBLIOTECA) * 50)
    bruto = bytearray(datos.getvalue())
    bruto[60:90] = b"\xff" * 30
    with pytest.raises(A.ErrorArchivo):
        A.desde_archivo(guardar(tmp_path, "c.zip", bytes(bruto)))


def test_vacio_extension_rara_y_que_no_existe(tmp_path):
    with pytest.raises(A.ErrorArchivo, match="vacío"):
        A.desde_archivo(guardar(tmp_path, "v.csv", ""))
    with pytest.raises(A.ErrorArchivo, match="Elige"):
        A.desde_archivo(guardar(tmp_path, "v.exe", "x"))
    with pytest.raises(A.ErrorArchivo, match="abrir"):
        A.desde_archivo(tmp_path / "nada.csv")
