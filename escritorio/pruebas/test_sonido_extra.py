# -*- coding: utf-8 -*-
"""Modo noche y sonido envolvente: entran en la cadena de filtros solo si se encienden, y mpv los acepta."""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


class _Ajustes(dict):
    def __missing__(self, k):
        return None


def _repro(**aj):
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    r.ajustes = _Ajustes({"ecualizador": False, "eq_bandas": [], "super_volumen": 0, "normalizar": False, **aj})
    return r


def test_por_defecto_no_hay_filtros_extra():
    assert _repro().cadena_filtros() == ""


def test_modo_noche_agrega_un_compresor_y_un_limitador():
    f = _repro(modo_noche=True).cadena_filtros()
    assert "acompressor" in f and "alimiter" in f and "stereowiden" not in f


def test_sonido_envolvente_agrega_el_ensanchado():
    f = _repro(sonido_envolvente=True).cadena_filtros()
    assert "stereowiden" in f and "acompressor" not in f


def test_los_dos_juntos_y_con_super_volumen_no_duplican_el_limitador():
    f = _repro(modo_noche=True, sonido_envolvente=True, super_volumen=2).cadena_filtros()
    assert f.count("alimiter") == 1


def test_los_ajustes_existen_apagados_por_defecto():
    from descargador import config
    assert config.DEFECTOS["modo_noche"] is False and config.DEFECTOS["sonido_envolvente"] is False


def test_mpv_acepta_los_filtros(tmp_path):
    from descargador import mpv_carga
    m = mpv_carga.modulo()
    if m is None:
        pytest.skip("sin libmpv")
    import locale
    import math
    import struct
    import wave
    locale.setlocale(locale.LC_NUMERIC, "C")
    ruta = tmp_path / "tono.wav"
    with wave.open(str(ruta), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"".join(struct.pack("<hh", int(8000 * math.sin(i / 20)), int(8000 * math.sin(i / 31)))
                               for i in range(44100 * 2)))
    f = _repro(modo_noche=True, sonido_envolvente=True).cadena_filtros()
    logs = []
    p = m.MPV(ytdl=False, vo="null", ao="null", video="no", msg_level="af=v,lavfi=v", idle="yes",
              log_handler=lambda _l, _lv, t: logs.append(t))
    try:
        p["af"] = f
        p.play(str(ruta))
        fin = time.time() + 3
        while time.time() < fin:
            time.sleep(0.05)
            try:
                if p.time_pos and p.time_pos > 0.2:
                    break
            except Exception:  # noqa: BLE001
                pass
        assert not any("initialized failed" in t for t in logs), logs[-5:]
    finally:
        p.terminate()
