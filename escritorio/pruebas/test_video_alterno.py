# -*- coding: utf-8 -*-
"""Si YouTube no deja reproducir un video, suena otra subida de la misma cancion."""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import catalogo, reproduccion  # noqa: E402

Rep = reproduccion.Reproductor
PISTA = {"titulo": "Préndele Fuego", "artista": "Mon Laferte", "video_id": "MALO"}


def test_elige_otra_subida_distinta_de_la_rota(monkeypatch):
    monkeypatch.setattr(catalogo, "buscar", lambda *a, **k: [
        {"tipo": "pista", "video_id": "MALO"},
        {"tipo": "album", "video_id": "ALBUM"},
        {"tipo": "pista", "video_id": "BUENO"},
    ])
    assert Rep._buscar_alterno(PISTA, "MALO") == "BUENO"


def test_sin_alternativas_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(catalogo, "buscar", lambda *a, **k: [{"tipo": "pista", "video_id": "MALO"}])
    assert Rep._buscar_alterno(PISTA, "MALO") == ""
    assert Rep._buscar_alterno({"video_id": "X"}, "X") == ""


def test_busca_por_titulo_y_artista(monkeypatch):
    visto = {}

    def falso(texto, filtro=None, limite=20):
        visto["q"], visto["f"] = texto, filtro
        return []

    monkeypatch.setattr(catalogo, "buscar", falso)
    Rep._buscar_alterno(PISTA, "MALO")
    assert visto == {"q": "Préndele Fuego Mon Laferte", "f": "canciones"}
