# -*- coding: utf-8 -*-
"""Volumen máximo sin distorsión: ganancia por canción según su sonoridad, tope del limitador,
cadena de filtros, elección de formato, y una medición real con ffmpeg (sonoridad y pico)."""

import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from descargador import sonoridad as S  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


class _Ajustes(dict):
    def __missing__(self, k):
        return None


# ------------------------------------------------------------ nivel y ganancia

def test_nivel_efectivo_y_compatibilidad_con_el_super_volumen():
    assert S.nivel_efectivo({"volumen_maximo": "alto"}) == "alto"
    assert S.nivel_efectivo({"volumen_maximo": "no", "normalizar": True}) == "normal"
    assert S.nivel_efectivo({"volumen_maximo": "no", "normalizar": False}) is None
    # ajustes de antes (sin la clave nueva): el súper volumen antiguo
    assert S.nivel_efectivo(_Ajustes(super_volumen=4)) == "maximo"
    assert S.nivel_efectivo(_Ajustes(super_volumen=1)) == "alto"
    assert S.nivel_efectivo(_Ajustes()) is None


def test_migrar_respeta_lo_que_tenia():
    d = {"super_volumen": 3}
    assert S.migrar(d) and d["volumen_maximo"] == "maximo"
    d = {"super_volumen": 0, "normalizar": False}
    assert S.migrar(d) and d["volumen_maximo"] == "no"
    d = {"super_volumen": 0, "normalizar": True}
    assert not S.migrar(d) and "volumen_maximo" not in d      # queda el de fábrica (Alto)
    assert not S.migrar({"volumen_maximo": "normal", "super_volumen": 4})


def test_poner_nivel_mantiene_la_clave_antigua():
    a = {}
    S.poner_nivel(a, "maximo")
    assert a == {"volumen_maximo": "maximo", "super_volumen": 4}
    S.poner_nivel(a, "cualquiera")
    assert a == {"volumen_maximo": "no", "super_volumen": 0}


def test_una_cancion_baja_sube_y_una_fuerte_baja():
    # canción baja y con margen de picos: sube justo hasta el objetivo
    assert S.ganancia_db("alto", -16.0, -6.0) == pytest.approx(6.0)
    # master fuerte: baja hasta el objetivo
    assert S.ganancia_db("alto", -7.0, -0.1) == pytest.approx(-3.0)
    assert S.ganancia_db("maximo", -7.0, -0.1) == pytest.approx(-1.0)


def test_el_limitador_solo_puede_recortar_su_presupuesto():
    # -20 LUFS con picos a -1 dBTP: para llegar a -8 haría falta +12 dB (11 dB de recorte);
    # Máximo deja recortar 6 dB, Alto 3 y Normal ninguno
    assert S.ganancia_db("maximo", -20.0, -1.0) == pytest.approx(6.0)
    assert S.ganancia_db("alto", -20.0, -1.0) == pytest.approx(3.0)
    assert S.ganancia_db("normal", -20.0, -1.0) == pytest.approx(0.0)
    # el preamplificador cuenta: si ya sube 2 dB, quedan 4 para Volumen máximo
    assert S.ganancia_db("maximo", -20.0, -1.0, extra_db=2.0) == pytest.approx(4.0)


def test_sin_medir_supone_un_master_tipico_y_no_se_pasa():
    g = S.ganancia_db("alto")
    assert g == pytest.approx(-1.0)                 # -10 - (-9)
    assert S.ganancia_db("maximo") <= S.NIVELES["maximo"][1]
    assert S.ganancia_db(None, -30, -20) == 0.0
    assert S.ganancia_db("maximo", -60, -40) == S.GANANCIA_MAX


def test_leer_resumen_de_ebur128():
    texto = """[Parsed_ebur128_0 @ 0x] Summary:

  Integrated loudness:
    I:         -12.3 LUFS
    Threshold: -22.6 LUFS

  Loudness range:
    LRA:         5.1 LU

  True peak:
    Peak:       -0.4 dBFS"""
    assert S.leer_resumen_ebur128(texto) == (-12.3, -0.4)
    assert S.leer_resumen_ebur128("I: -inf LUFS") is None
    assert S.leer_resumen_ebur128("") is None


def test_clave_y_cache(tmp_path):
    assert S.clave_de({"info": {"video_id": "abc"}}) == "yt:abc"
    assert S.clave_de(None, {"video_id": "xyz", "archivo": "c:/a.mp3"}) == "yt:xyz"
    assert S.clave_de({"archivo": str(tmp_path / "a.mp3")}).startswith("archivo:")

    class Col:
        def __init__(self):
            self.d = {}

        def estado(self, k, defecto=None):
            return self.d.get(k, defecto)

        def guardar_estado(self, k, v):
            self.d[k] = dict(v)

    col = Col()
    c = S.CacheSonoridad(col)
    c.guardar("yt:abc", (-11.5, -0.8))
    assert S.CacheSonoridad(col).leer("yt:abc") == (-11.5, -0.8)
    assert c.leer("yt:otro") is None


def test_args_de_descarga_recodifican_solo_si_yt_dlp_copiaria():
    m = (-15.0, -3.0)
    assert S.args_descarga("mp3", "opus", m)[:1] == ["-af"] and "-c:a" not in S.args_descarga("mp3", "opus", m)
    assert S.args_descarga("m4a", "mp4a.40.2", m)[-4:] == ["-c:a", "aac", "-b:a", "256k"]
    assert S.args_descarga("opus", "opus", m)[-4:] == ["-c:a", "libopus", "-b:a", "192k"]
    assert "loudnorm" in S.filtro_descarga(None)
    assert "alimiter" in S.filtro_descarga(m) and "volume=" in S.filtro_descarga(m)


# ------------------------------------------------------------ cadena del reproductor

def _repro(**aj):
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    r.ajustes = _Ajustes({"ecualizador": False, "eq_bandas": [], "normalizar": False, **aj})
    return r


def test_volumen_maximo_pone_ganancia_y_un_solo_limitador_al_final():
    r = _repro(volumen_maximo="maximo")
    r._cache_sonoridad().guardar("yt:a", (-16.0, -6.0))
    f = r.cadena_filtros({"video_id": "a"})
    assert f.startswith("lavfi=[volume=") and f.count("alimiter") == 1
    assert f.endswith("aresample=48000]")
    assert "volume=8.00dB" in f                     # -8 - (-16)
    assert "dynaudnorm" not in f and "loudnorm" not in f   # nada de ganancia que «respira»


def test_apagado_no_toca_el_sonido():
    assert _repro(volumen_maximo="no").cadena_filtros() == ""


def test_el_ecualizador_del_mezclador_va_antes_del_limitador():
    r = _repro(volumen_maximo="alto")
    f = r.cadena_filtros(extra=["bass=g=6.0:f=110"])
    assert f.index("bass=g=6.0") < f.index("alimiter")


def test_selectores_evitan_la_pista_drc():
    from descargador.catalogo import selector_audio
    from descargador.motor import selector_formato
    assert selector_audio("maxima").startswith("bestaudio[format_id!*=drc]")
    assert selector_formato("mejor", tipo="audio", formato_audio="mp3").startswith("ba[format_id!*=drc]")
    assert selector_formato("mejor", tipo="audio", formato_audio="opus").endswith("/ba/b")


# ------------------------------------------------------------ medición real con ffmpeg

def _ffmpeg():
    from descargador.reproduccion import _ffmpeg_exe
    exe = _ffmpeg_exe()
    if not exe:
        pytest.skip("sin ffmpeg")
    return exe


def _generar(exe, ruta, amplitud, golpe, master=False):
    """Ruido rosa con golpes de bombo (una «canción» sintética de 20 s)."""
    subprocess.run([exe, "-hide_banner", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude={amplitud}:duration=20:sample_rate=44100",
                    "-f", "lavfi", "-i", f"aevalsrc='{golpe}*sin(2*PI*60*t)*exp(-10*mod(t,0.5))':d=20:s=44100",
                    "-filter_complex", "[0][1]amix=inputs=2:normalize=0," + ("volume=10dB,alimiter=limit=0.97:level=disabled," if master else "") + "aformat=channel_layouts=stereo",
                    "-c:a", "pcm_s16le", str(ruta)], check=True, capture_output=True)


def _medir_con(exe, ruta, af):
    r = subprocess.run([exe, "-hide_banner", "-nostdin", "-i", str(ruta), "-af",
                        (af + "," if af else "") + "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    return S.leer_resumen_ebur128(r.stderr)


@pytest.mark.parametrize("nivel", ["alto", "maximo"])
def test_con_ffmpeg_las_bajas_suben_y_ningun_pico_pasa_de_menos_1_dbtp(tmp_path, nivel):
    exe = _ffmpeg()
    baja, fuerte = tmp_path / "baja.wav", tmp_path / "fuerte.wav"
    _generar(exe, baja, 0.12, 0.5)          # ~ -18 LUFS
    _generar(exe, fuerte, 0.3, 0.8, master=True)   # master aplastado, picos casi a 0
    antes = {k: S.medir({"archivo": str(v)}, exe) for k, v in (("baja", baja), ("fuerte", fuerte))}
    assert antes["baja"][0] < antes["fuerte"][0] - 8
    despues = {}
    for k, ruta in (("baja", baja), ("fuerte", fuerte)):
        g = S.ganancia_db(nivel, *antes[k])
        af = ",".join(S.partes_ganancia(g) + S.partes_limitador())
        despues[k] = _medir_con(exe, ruta, af)
        assert despues[k][1] <= S.TECHO_DBTP + 0.3, (k, despues[k])     # sin recortes
    objetivo = S.NIVELES[nivel][0]
    # la fuerte queda en el objetivo; la baja sube mucho (hasta donde deja el presupuesto)
    # en «máximo» el limitador (techo -1 dBTP) se come algo de sonoridad en un master ya
    # aplastado: puede quedar hasta 1,5 dB por debajo del objetivo, nunca por encima
    margen = 1.5 if nivel == "maximo" else 1.0
    assert -margen < despues["fuerte"][0] - objetivo < 1.0
    assert despues["baja"][0] > antes["baja"][0] + 2.5
    # y la diferencia entre las dos se achica de verdad
    assert (despues["fuerte"][0] - despues["baja"][0]) < (antes["fuerte"][0] - antes["baja"][0]) - 3


def test_mpv_acepta_la_cadena_nueva(tmp_path):
    from descargador import mpv_carga
    m = mpv_carga.modulo()
    if m is None:
        pytest.skip("sin libmpv")
    import locale
    import time
    exe = _ffmpeg()
    ruta = tmp_path / "c.wav"
    _generar(exe, ruta, 0.2, 0.6)
    locale.setlocale(locale.LC_NUMERIC, "C")
    r = _repro(volumen_maximo="maximo", ecualizador=True, eq_bandas=[3, 0, 0, 0, 0, 0, 0, 0, 0, -2],
               modo_noche=True)
    f = r.cadena_filtros()
    logs = []
    p = m.MPV(ytdl=False, vo="null", ao="null", video="no", msg_level="af=v,lavfi=v", idle="yes",
              log_handler=lambda _l, _lv, t: logs.append(t))
    try:
        p["af"] = f
        p.play(str(ruta))
        fin = time.time() + 40
        while time.time() < fin:
            time.sleep(0.05)
            try:
                if p.time_pos and p.time_pos > 0.3:
                    break
            except Exception:  # noqa: BLE001
                pass
        assert p.time_pos and p.time_pos > 0.3, logs[-5:]
        assert not any("initialized failed" in t or "Disabling filter" in t for t in logs), logs[-5:]
    finally:
        p.terminate()
