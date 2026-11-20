# -*- coding: utf-8 -*-
"""El instalador corrige los accesos directos que abren una copia vieja de Caudal.

Caso real: el acceso del escritorio abria una copia suelta antigua; esa copia
avisaba de la version nueva, se instalaba en Programas\\Caudal, y al volver a
abrir desde el escritorio salia otra vez el aviso, sin fin.
"""

import os
import subprocess
import sys

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "instalador"))

import instalador  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="accesos directos de Windows")


def _crear(lnk, destino):
    guion = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:L);"
             "$s.TargetPath=$env:D;$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", guion],
                   check=True, capture_output=True, env=dict(os.environ, L=lnk, D=destino))


def _destino(lnk):
    guion = "(New-Object -ComObject WScript.Shell).CreateShortcut($env:L).TargetPath"
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", guion],
                       check=True, capture_output=True, text=True, env=dict(os.environ, L=lnk))
    return r.stdout.strip()


def _exe(carpeta, nombre="Caudal Escritorio.exe"):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre)
    open(ruta, "wb").close()
    return ruta


def test_corrige_solo_los_accesos_a_otra_copia_de_caudal(tmp_path):
    instalada = _exe(str(tmp_path / "Programas" / "Caudal"))
    vieja = _exe(str(tmp_path / "copia vieja" / "Caudal Escritorio"))
    otro = _exe(str(tmp_path / "Otro"), "Otro programa.exe")

    escritorio = tmp_path / "Escritorio"
    menu = tmp_path / "Menu" / "Programs" / "Sub"
    escritorio.mkdir()
    menu.mkdir(parents=True)

    a_vieja = str(escritorio / "Caudal Escritorio.lnk")
    a_vieja_menu = str(menu / "Caudal viejo.lnk")
    a_bien = str(escritorio / "Caudal.lnk")
    a_otro = str(escritorio / "Otro.lnk")
    _crear(a_vieja, vieja)
    _crear(a_vieja_menu, vieja)
    _crear(a_bien, instalada)
    _crear(a_otro, otro)

    corregidos = instalador.reparar_accesos(instalada, [str(escritorio), str(tmp_path / "Menu")])

    assert sorted(corregidos) == sorted([a_vieja, a_vieja_menu])
    assert _destino(a_vieja).lower() == instalada.lower()
    assert _destino(a_vieja_menu).lower() == instalada.lower()
    assert _destino(a_bien).lower() == instalada.lower()
    assert _destino(a_otro).lower() == otro.lower()


def test_sin_sitios_no_hace_nada(tmp_path):
    assert instalador.reparar_accesos(str(tmp_path / "x.exe"), []) == []
    assert instalador.reparar_accesos(str(tmp_path / "x.exe"), [str(tmp_path / "no existe")]) == []


def test_escritorio_es_el_que_muestra_windows():
    real = instalador._escritorio_de_windows()
    assert real and os.path.isdir(real)
    assert instalador.escritorio() == real
