# -*- coding: utf-8 -*-
"""Entrar con Google en el escritorio, sin abrir el navegador de verdad."""

import base64
import hashlib
import threading
import urllib.request
from urllib.parse import parse_qs, urlparse

import pytest

from descargador import cuentas, nube


def test_huella_pkce():
    v = nube.nuevo_verificador()
    assert len(v) == 64
    q = parse_qs(urlparse(nube.url_google(v, "http://127.0.0.1:5/acceso")).query)
    esperada = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).decode().rstrip("=")
    assert q["code_challenge"] == [esperada]
    assert q["provider"] == ["google"]
    assert q["redirect_to"] == ["http://127.0.0.1:5/acceso"]


def _navegador_que_vuelve(consulta):
    """Hace de navegador: en vez de ir a Google, vuelve directo a Caudal."""
    def abrir(url):
        vuelta = parse_qs(urlparse(url).query)["redirect_to"][0]
        threading.Timer(0.3, lambda: urllib.request.urlopen(f"{vuelta}?{consulta}", timeout=5).read()).start()
        return True
    return abrir


def test_cancelar_en_google(monkeypatch):
    monkeypatch.setattr("webbrowser.open", _navegador_que_vuelve("error=access_denied&error_description=denied"))
    with pytest.raises(cuentas.ErrorCuenta, match="Cancelaste"):
        cuentas.Cuentas().con_google(espera=10)


def test_codigo_se_canjea(monkeypatch):
    monkeypatch.setattr("webbrowser.open", _navegador_que_vuelve("code=ABC"))
    vistos = {}

    class _Sesion:
        user_id = "u1"
        refresh = "r"

        def perfil(self):
            return {"usuario": "ana", "nombre": "Ana Pérez"}

    def canjear(codigo, verificador):
        vistos["codigo"], vistos["verificador"] = codigo, verificador
        return _Sesion()

    monkeypatch.setattr(nube, "canjear_google", canjear)
    monkeypatch.setattr(cuentas, "_carpeta_para", lambda _id: "")
    c = cuentas.Cuentas().con_google(espera=10)
    assert vistos["codigo"] == "ABC" and len(vistos["verificador"]) == 64
    assert c["usuario"] == "ana" and c["nombre"] == "Ana Pérez" and c["google"] is True


def test_el_boton_cancela(monkeypatch):
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    with pytest.raises(cuentas.ErrorCuenta) as e:
        cuentas.Cuentas().con_google(cancelado=lambda: True, espera=10)
    assert str(e.value) == ""
