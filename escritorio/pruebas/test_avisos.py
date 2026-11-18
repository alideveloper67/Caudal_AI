# -*- coding: utf-8 -*-
"""Avisos de Caudal (descargador/avisos.py y el cuadro): filtro por plataforma, un solo aviso visto,
fallos de red sin romper y enlaces solo https."""

import os

import requests

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from descargador import avisos  # noqa: E402

FILAS = [
    {"id": 1, "titulo": "Para todos", "texto": "Hola a todos", "plataformas": ["todas"]},
    {"id": 2, "titulo": "Solo web", "texto": "La web no está tan optimizada", "plataformas": ["web"],
     "enlace": "https://caudal-musica.netlify.app", "etiqueta_enlace": "Descargar"},
    {"id": 3, "titulo": "Solo Windows", "texto": "Actualiza", "plataformas": ["windows"]},
    {"id": 4, "titulo": "", "texto": "sin título no sirve", "plataformas": ["todas"]},
    {"id": 5, "titulo": "Enlace raro", "texto": "no es https", "plataformas": ["todas"],
     "enlace": "javascript:alert(1)"},
]


class _Resp:
    def __init__(self, datos, codigo=200):
        self._d, self.status_code = datos, codigo

    def json(self):
        return self._d


class _Sesion:
    def __init__(self, datos=None, codigo=200, falla=None):
        self.datos, self.codigo, self.falla = datos, codigo, falla

    def get(self, *a, **k):
        if self.falla:
            raise self.falla
        return _Resp(self.datos, self.codigo)


def _aislar(monkeypatch, tmp_path):
    monkeypatch.setattr(avisos, "carpeta_datos", lambda: tmp_path)


def test_cada_plataforma_recibe_lo_suyo(monkeypatch, tmp_path):
    _aislar(monkeypatch, tmp_path)
    assert [a["id"] for a in avisos.pendientes("windows", _Sesion(FILAS))] == [1, 3, 5]
    assert [a["id"] for a in avisos.pendientes("web", _Sesion(FILAS))] == [1, 2, 5]


def test_enlace_solo_https(monkeypatch, tmp_path):
    _aislar(monkeypatch, tmp_path)
    web = {a["id"]: a for a in avisos.pendientes("web", _Sesion(FILAS))}
    assert web[2]["enlace"] == "https://caudal-musica.netlify.app" and web[2]["etiqueta"] == "Descargar"
    assert web[5]["enlace"] is None


def test_un_aviso_visto_no_vuelve(monkeypatch, tmp_path):
    _aislar(monkeypatch, tmp_path)
    avisos.marcar_visto(3)
    assert [a["id"] for a in avisos.pendientes("windows", _Sesion(FILAS))] == [1, 5]


def test_fallos_de_red_o_servidor_no_rompen(monkeypatch, tmp_path):
    _aislar(monkeypatch, tmp_path)
    assert avisos.pendientes("windows", _Sesion(falla=requests.ConnectionError())) == []
    assert avisos.pendientes("windows", _Sesion({"error": "x"}, 500)) == []
    assert avisos.pendientes("windows", _Sesion({"no": "es lista"})) == []


def test_cuadro_marca_visto_al_cerrar(monkeypatch, tmp_path):
    _aislar(monkeypatch, tmp_path)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from descargador.ui.aviso_caudal import DialogoAviso
    a = avisos.aviso_de(FILAS[1])
    d = DialogoAviso(a)
    assert d.bt_enlace is not None and d.bt_enlace.text() == "Descargar"
    d.accept()
    assert 2 in avisos.vistos()
    assert app is not None
