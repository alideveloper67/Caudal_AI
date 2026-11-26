# -*- coding: utf-8 -*-
"""Que Caudal no pida iniciar sesión a cada rato: el token nuevo se guarda al renovarse, un fallo del
servidor no borra la sesión y cerrar sesión solo cierra este equipo. Sin red."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import config, cuentas, nube  # noqa: E402


class _R:
    def __init__(self, estado, datos=None, texto=""):
        self.status_code = estado
        self._d = datos
        self.text = texto or (json.dumps(datos) if datos is not None else "")

    def json(self):
        if self._d is None:
            raise ValueError("no es json")
        return self._d


def _buena(refresh):
    return _R(200, {"access_token": "a-" + refresh, "refresh_token": refresh, "expires_in": 3600,
                    "user": {"id": "u1", "user_metadata": {}}})


@pytest.fixture(autouse=True)
def datos(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield config.carpeta_datos()


def _guardar(refresh):
    cuentas._escribir("sesion.json", {"id": "u1", "usuario": "ana", "nombre": "Ana", "refresh": refresh,
                                      "google": False})


def _guardado():
    return cuentas._leer("sesion.json", {}).get("refresh")


def test_al_renovarse_en_marcha_el_token_queda_guardado(monkeypatch):
    _guardar("r1")
    pedidos = []

    def peticion(metodo, ruta, token=None, **kw):
        pedidos.append(kw.get("json", {}).get("refresh_token"))
        return _buena(f"r{len(pedidos) + 1}")
    monkeypatch.setattr(nube, "_peticion", peticion)
    c = cuentas.Cuentas().recordada()
    assert _guardado() == "r2"
    c["sesion"].expira = 0                      # pasa la hora
    assert c["sesion"].token() == "a-r3"
    assert _guardado() == "r3" and pedidos == ["r1", "r2"]


@pytest.mark.parametrize("respuesta", [_R(500), _R(502, texto="<html>"), _R(429, {"msg": "rate limit"}),
                                       _R(200, None, "<html>portal del wifi</html>")])
def test_un_fallo_del_servidor_no_cierra_la_sesion(monkeypatch, respuesta):
    _guardar("r1")
    monkeypatch.setattr(nube, "_peticion", lambda *a, **k: respuesta)
    c = cuentas.Cuentas().recordada()
    assert c is not None and c["sin_conexion"] and _guardado() == "r1"


def test_una_sesion_invalida_de_verdad_si_se_olvida(monkeypatch):
    _guardar("r1")
    monkeypatch.setattr(nube, "_peticion", lambda *a, **k: _R(400, {
        "code": 400, "error_code": "refresh_token_already_used", "msg": "Invalid Refresh Token: Already Used"}))
    assert cuentas.Cuentas().recordada() is None
    assert _guardado() is None


def test_si_otro_caudal_la_renovo_se_usa_el_token_nuevo(monkeypatch):
    _guardar("r1")

    def peticion(metodo, ruta, token=None, **kw):
        if kw["json"]["refresh_token"] == "r1":
            _guardar("r7")
            return _R(400, {"msg": "Invalid Refresh Token: Already Used"})
        return _buena("r8")
    monkeypatch.setattr(nube, "_peticion", peticion)
    c = cuentas.Cuentas().recordada()
    assert c is not None and c["sesion"].refresh == "r8" and _guardado() == "r8"


def test_cerrar_sesion_solo_cierra_este_equipo(monkeypatch):
    rutas = []
    monkeypatch.setattr(nube, "_peticion", lambda m, ruta, token=None, **k: rutas.append(ruta) or _R(204))
    nube.Sesion("u1", "a", "r", 9e9).salir()
    assert rutas == ["/auth/v1/logout?scope=local"]


def test_sin_mantener_la_sesion_renovar_no_crea_el_archivo(monkeypatch):
    monkeypatch.setattr(nube, "_peticion", lambda *a, **k: _buena("r2"))
    s = nube.Sesion("u1", "a", "r1", 0)
    cuentas._cuenta(s, "ana", "Ana")
    s.token()
    assert _guardado() is None
