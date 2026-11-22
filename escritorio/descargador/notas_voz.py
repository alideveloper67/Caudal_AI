# -*- coding: utf-8 -*-
"""Notas de voz de los grupos en Windows: grabar con el micrófono (winmm, como «¿Qué suena?»),
comprimir a AAC con el ffmpeg de Caudal y oírlas con un mpv aparte (sin tocar la música)."""

import os
import subprocess
import tempfile
import threading

from . import que_suena
from .grupos import MAX_SEGUNDOS_AUDIO

TASA = 16000


class Grabacion:
    """Una grabación en un hilo: `parar()` la termina y deja los datos; `cancelar()` los tira."""

    def __init__(self):
        self._parar = threading.Event()
        self._tirar = False
        self.pcm = b""
        self.error = None

    def correr(self):
        """Trabajo de fondo: graba hasta que se pare (o 3 minutos)."""
        try:
            self.pcm = que_suena.grabar(MAX_SEGUNDOS_AUDIO, TASA, cancelar=self._parar)
        except que_suena.ErrorQueSuena as e:
            self.error = str(e)
        return self

    def parar(self):
        self._parar.set()

    def cancelar(self):
        self._tirar = True
        self._parar.set()

    @property
    def tirada(self):
        return self._tirar

    @property
    def segundos(self):
        return len(self.pcm) // (TASA * 2)


def _ffmpeg():
    from .reproduccion import _ffmpeg_exe
    return _ffmpeg_exe()


def comprimir(pcm):
    """PCM 16 kHz mono → (bytes, tipo). AAC en .m4a con ffmpeg (~30 KB por minuto de voz a 32 kbps);
    sin ffmpeg, WAV (pesa más: el almacén admite 3 MB, unos 90 s)."""
    wav = que_suena.wav_de_pcm(pcm, TASA)
    exe = _ffmpeg()
    if not exe:
        return wav, "audio/wav"
    with tempfile.TemporaryDirectory() as d:
        entrada, salida = os.path.join(d, "nota.wav"), os.path.join(d, "nota.m4a")
        with open(entrada, "wb") as f:
            f.write(wav)
        banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            r = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", "-i", entrada, "-ac", "1",
                                "-c:a", "aac", "-b:a", "48k", "-movflags", "+faststart", salida],
                               capture_output=True, timeout=60, creationflags=banderas)
        except (OSError, subprocess.SubprocessError):
            return wav, "audio/wav"
        if r.returncode != 0 or not os.path.exists(salida):
            return wav, "audio/wav"
        with open(salida, "rb") as f:
            return f.read(), "audio/mp4"


class Reproductor:
    """Un mpv solo para las notas de voz (uno para toda la app)."""

    _uno = None

    @classmethod
    def compartido(cls):
        if cls._uno is None:
            cls._uno = cls()
        return cls._uno

    def __init__(self):
        self._mpv = None
        self.sonando = None          # ruta de la nota que suena

    def _crear(self):
        if self._mpv is None:
            from . import mpv_carga
            mpv = mpv_carga.modulo()
            if mpv is None:
                raise RuntimeError("no hay mpv")
            import locale
            try:
                locale.setlocale(locale.LC_NUMERIC, "C")
            except locale.Error:
                pass
            self._mpv = mpv.MPV(video="no", vo="null", audio_display="no", ytdl="no", terminal="no",
                                input_default_bindings="no", media_controls="no")
        return self._mpv

    def tocar(self, ruta, url):
        m = self._crear()
        self.sonando = ruta
        m.pause = False
        m.play(url)

    def parar(self):
        self.sonando = None
        if self._mpv is not None:
            try:
                self._mpv.command("stop")
            except Exception:  # noqa: BLE001
                pass

    def posicion(self):
        try:
            return float(self._mpv.time_pos or 0) if self._mpv is not None else 0.0
        except Exception:  # noqa: BLE001
            return 0.0

    def termino(self):
        try:
            return self._mpv is None or bool(self._mpv.idle_active)
        except Exception:  # noqa: BLE001
            return True
