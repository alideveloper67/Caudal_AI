# -*- coding: utf-8 -*-
"""Insignia de calidad real y medidor de nivel del motor.

La parte de texto es pura; la del motor usa el libmpv de verdad con un WAV sintético y la salida «null»
(no suena nada). Sin ventanas a la vista (Qt offscreen) y sin internet."""

import faulthandler
import os
import subprocess
import sys
import time
import wave

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import calidad_real as CR  # noqa: E402
from descargador import mpv_carga  # noqa: E402

# libmpv lanza por dentro excepciones que él mismo gestiona (código 0xe24c4a02). El faulthandler
# de pytest las intercepta y, al volcar las pilas a mitad de ellas, tumba el proceso (9 de cada 10
# corridas). La app no usa faulthandler; aquí se apaga para medir a mpv como corre de verdad.
faulthandler.disable()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ texto de la insignia

def datos(codec, hz=48000, bitrate=0, formato="fltp", canales="stereo"):
    return {"codec": codec, "bitrate": bitrate,
            "params": {"samplerate": hz, "format": formato, "channels": canales}}


def test_texto_de_la_tasa():
    assert CR.texto_khz(44100) == "44,1 kHz"
    assert CR.texto_khz(48000) == "48 kHz"
    assert CR.texto_khz(96000) == "96 kHz"
    assert CR.texto_khz(0) == "" and CR.texto_khz(None) == "" and CR.texto_khz("x") == ""


def test_etiqueta_con_perdida_muestra_codec_y_kbps():
    assert CR.etiqueta(datos("opus", bitrate=160000)) == "OPUS 160 kbps"
    assert CR.etiqueta(datos("aac", 44100, 128000)) == "AAC 128 kbps"
    assert CR.etiqueta(datos("mp3", 44100, 320000)) == "MP3 320 kbps"
    assert CR.etiqueta(datos("vorbis", bitrate=0)) == "OGG 48 kHz"     # sin tasa de bits: la de muestreo


def test_etiqueta_sin_perdida_muestra_bits_y_tasa():
    assert CR.etiqueta(datos("flac", 44100, 900000, "s16")) == "FLAC 16/44,1"
    assert CR.etiqueta(datos("flac", 96000, 0, "s24")) == "FLAC 24/96"
    assert CR.etiqueta(datos("flac", 48000, 0, "s32")) == "FLAC 48 kHz"   # s32 puede ser 24 real: no se afirma
    assert CR.etiqueta(datos("pcm_s16le", 44100, 705600, "s16")) == "WAV 16/44,1"
    assert CR.etiqueta(datos("alac", 44100, 0, "s16p")) == "ALAC 16/44,1"


def test_sin_datos_no_hay_insignia():
    assert CR.etiqueta({}) == "" and CR.etiqueta(None) == ""
    assert CR.etiqueta({"codec": None, "params": {}}) == ""
    assert CR.ayuda(None) == ""


def test_la_ayuda_cuenta_el_detalle():
    a = CR.ayuda(datos("flac", 44100, 900000, "s16"))
    assert "sin pérdida" in a and "44,1 kHz" in a and "16 bits" in a and "estéreo" in a
    b = CR.ayuda(datos("opus", 48000, 160000))
    assert "160 kbps" in b and "pérdida" not in b


# ------------------------------------------------------------------ el motor de verdad

def _ffmpeg():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "ffmpeg.exe")


@pytest.fixture(scope="module")
def wav(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("audio") / "seno.wav"
    r = subprocess.run([_ffmpeg(), "-y", "-f", "lavfi", "-i", "sine=f=440:d=12:r=44100",
                        "-f", "lavfi", "-i", "sine=f=2000:d=12:r=44100", "-filter_complex", "amix=inputs=2,volume=2",
                        str(ruta)], capture_output=True)
    if r.returncode != 0 or not ruta.exists():
        pytest.skip("no hay ffmpeg para fabricar el audio de prueba")
    return str(ruta)


class _Aj(dict):
    def guardar(self):
        pass


@pytest.fixture(scope="module")
def _motor_unico(app):
    # UN solo motor para todo el módulo, como en la app (crea sus motores una vez al arrancar):
    # crear uno nuevo mientras el anterior aún se apaga en segundo plano tumba libmpv
    if mpv_carga.modulo() is None:
        pytest.skip("no hay libmpv")
    from descargador.reproduccion import Motor
    m = Motor(_Aj(aceleracion=False), None, "prueba")
    m.mpv["ao"] = "null"                      # no suena nada
    m.fijar_volumen(0)
    yield m
    m.cerrar()


@pytest.fixture
def motor(_motor_unico):
    m = _motor_unico
    m.fijar_espectro(False)
    m.fijar_filtros("")
    yield m
    m.fijar_espectro(False)
    m.fijar_filtros("")


def esperar(app, cond, maximo=6.0):
    fin = time.time() + maximo
    while not cond() and time.time() < fin:
        app.processEvents()
        time.sleep(0.02)
    return cond()


def test_el_motor_dice_que_audio_decodifica(app, motor, wav):
    motor.mpv.command("stop")
    motor.cargar({"archivo": wav})
    assert esperar(app, lambda: bool(motor.info_audio().get("codec"))), "mpv no dijo qué audio decodifica"
    d = motor.info_audio()
    assert d["codec"] == "pcm_s16le"
    assert d["params"]["samplerate"] == 44100
    assert CR.etiqueta(d) == "WAV 16/44,1"


def test_el_medidor_da_el_nivel_solo_mientras_esta_puesto(app, motor, wav):
    motor.cargar({"archivo": wav})
    assert esperar(app, lambda: motor.info_audio().get("codec"))
    assert motor.nivel_audio() is None                       # sin medidor no hay nivel
    motor.fijar_espectro(True)
    assert esperar(app, lambda: motor.nivel_audio() is not None), "el filtro de medición no entregó nada"
    rms, pico = motor.nivel_audio()
    assert -60 < rms < 0 and rms <= pico <= 0.5
    motor.fijar_espectro(False)
    assert motor.nivel_audio() is None


def test_el_medidor_convive_con_los_filtros_del_sonido(app, motor, wav):
    """El medidor se añade al final de la cadena: cambiar los filtros no lo pierde ni los pisa."""
    motor.cargar({"archivo": wav})
    motor.fijar_espectro(True)
    motor.fijar_filtros("lavfi=[volume=-3dB]")
    assert esperar(app, lambda: motor.nivel_audio() is not None)
    assert motor.esperar_ordenes()                 # las órdenes van por el hilo del motor
    etiquetas = [f.get("label") for f in motor.mpv.af]
    assert "vis" in etiquetas and len(motor.mpv.af) == 2
    motor.fijar_filtros("")
    assert esperar(app, lambda: motor.nivel_audio() is not None)
    assert motor.esperar_ordenes()
    assert [f.get("label") for f in motor.mpv.af] == ["vis"]
    motor.fijar_espectro(False)
    assert motor.esperar_ordenes()
    assert list(motor.mpv.af) == []


def test_el_nivel_sube_con_el_volumen_del_audio(app, motor, wav):
    motor.cargar({"archivo": wav})
    motor.fijar_espectro(True)
    motor.fijar_filtros("lavfi=[volume=-20dB]")
    assert esperar(app, lambda: motor.nivel_audio() is not None)
    time.sleep(0.4)
    app.processEvents()
    bajo = motor.nivel_audio()[0]
    motor.fijar_filtros("lavfi=[volume=0dB]")
    time.sleep(0.8)
    app.processEvents()
    alto = motor.nivel_audio()[0]
    assert alto > bajo + 10


# ------------------------------------------------------------------ el reproductor lo expone

class _MotorFalso(QObject):
    def __init__(self, nivel):
        super().__init__()
        self._n, self.espectro = nivel, None

    def fijar_espectro(self, si):
        self.espectro = si

    def nivel_audio(self):
        return self._n


def test_reproductor_activa_el_medidor_en_los_motores_de_audio_y_da_el_nivel():
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    a, b = _MotorFalso((-20.0, -10.0)), _MotorFalso(None)
    r.audio, r.videos, r.activo, r.modo, r.destino_video = [a, b], {}, 0, "audio", None
    r.activar_espectro(True)
    assert a.espectro is True and b.espectro is True
    assert r.nivel_audio() == (-20.0, -10.0)
    r.activar_espectro(False)
    assert a.espectro is False
    r.modo = "video"                                          # en video no hay motor de audio que medir
    assert r.nivel_audio() is None
