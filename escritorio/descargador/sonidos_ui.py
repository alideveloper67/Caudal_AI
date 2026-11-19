# -*- coding: utf-8 -*-
"""Sonidos de interfaz (donadores): un sonidito suave al dar «me gusta» y al abrir Caudal.

Opcional (apagado por defecto) y siempre bajito: los tres sonidos (burbuja, moneda y campana) se fabrican aquí
con senos amortiguados, con el volumen ya bajo dentro del archivo (pico al 30 %), y se guardan una sola vez como
WAV en la carpeta de datos. Se tocan con `winsound` (viene con Python, no abre ningún motor ni gasta nada en
reposo) y no pisan la música: es el mezclador de Windows el que los suma.
"""

import array
import math
import sys
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from . import config

try:                                          # solo Windows; en otro sistema simplemente no suena
    import winsound
except ImportError:  # pragma: no cover
    winsound = None

FRECUENCIA = 22050
PICO = 0.30                                    # volumen bajo: el pico es el 30 % del máximo
VERSION = 1
SONIDOS = {"burbuja": "Burbuja", "moneda": "Moneda", "campana": "Campana"}
EVENTOS = ("gusta", "abrir")


def sonido_valido(nombre):
    return nombre if nombre in SONIDOS else "burbuja"


def _normalizar(x, pico=PICO):
    m = max((abs(v) for v in x), default=0.0) or 1.0
    k = pico * 32767.0 / m
    return [int(v * k) for v in x]


def _tono(frec, seg, caida, fase=0.0, armonicos=()):
    n = int(FRECUENCIA * seg)
    salida = [0.0] * n
    for i in range(n):
        t = i / FRECUENCIA
        env = math.exp(-t * caida) * min(1.0, t * 400.0)           # entrada de 2,5 ms: sin «clic»
        v = math.sin(math.tau * frec * t + fase)
        for mult, amp in armonicos:
            v += amp * math.sin(math.tau * frec * mult * t)
        salida[i] = v * env
    return salida


def _sumar(destino, origen, inicio_seg):
    ini = int(inicio_seg * FRECUENCIA)
    for i, v in enumerate(origen):
        if ini + i < len(destino):
            destino[ini + i] += v


def sintetizar(nombre):
    """Las muestras (enteros de 16 bits, mono, 22 050 Hz) de un sonido."""
    nombre = sonido_valido(nombre)
    if nombre == "burbuja":
        # una gota que sube de tono y un segundo «blup» más agudo y breve
        n = int(FRECUENCIA * 0.26)
        x = [0.0] * n
        for i in range(int(FRECUENCIA * 0.11)):
            t = i / FRECUENCIA
            f = 420 + 5200 * t
            x[i] += math.sin(math.tau * f * t) * math.exp(-t * 26) * min(1.0, t * 500)
        for i in range(int(FRECUENCIA * 0.09)):
            t = i / FRECUENCIA
            f = 620 + 6600 * t
            x[i + int(FRECUENCIA * 0.12)] += 0.7 * math.sin(math.tau * f * t) * math.exp(-t * 30) * min(1.0, t * 500)
        return _normalizar(x)
    if nombre == "moneda":
        x = [0.0] * int(FRECUENCIA * 0.5)
        _sumar(x, _tono(988.0, 0.07, 18, armonicos=((2, 0.35), (3, 0.12))), 0.0)
        _sumar(x, _tono(1319.0, 0.42, 7, armonicos=((2, 0.35), (3, 0.12))), 0.065)
        return _normalizar(x)
    # campana: parciales inarmónicos que se apagan a distinto paso
    x = [0.0] * int(FRECUENCIA * 1.0)
    for mult, amp, caida in ((1.0, 1.0, 4.5), (2.0, 0.55, 5.5), (2.76, 0.42, 7.0), (5.4, 0.22, 11.0), (8.93, 0.1, 16.0)):
        _sumar(x, [v * amp for v in _tono(880.0 * mult, 1.0, caida)], 0.0)
    return _normalizar(x)


def carpeta_sonidos():
    ruta = config.carpeta_datos() / "cache" / "sonidos_ui"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_sonido(nombre):
    """El WAV de un sonido (se fabrica la primera vez)."""
    nombre = sonido_valido(nombre)
    ruta = carpeta_sonidos() / f"{nombre}_v{VERSION}.wav"
    if not ruta.exists():
        datos = array.array("h", sintetizar(nombre))
        if sys.byteorder == "big":
            datos.byteswap()
        tmp = Path(str(ruta) + ".tmp")
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(FRECUENCIA)
            w.writeframes(datos.tobytes())
        tmp.replace(ruta)
    return ruta


def tocar(nombre):
    """Suena el sonido sin esperar. True si se pidió a Windows."""
    if winsound is None:
        return False
    try:
        winsound.PlaySound(str(ruta_sonido(nombre)),
                           winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        return True
    except Exception:  # noqa: BLE001 - un sonidito que falla no debe molestar
        return False


class SonidosUI(QObject):
    """Escucha el «me gusta» y la apertura de la ventana y suena si la cuenta es donadora y lo activó."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.tocados = []                      # lo que sonó (para las pruebas)
        self._abierto = False
        ctx.me_gusta_cambio.connect(self._al_me_gusta)

    def activo(self):
        g = getattr(self.ctx, "premium", None)
        return bool(g is not None and g.premium and self.ctx.ajustes["sonidos_ui"])

    def sonar(self, evento):
        """`evento`: «gusta» o «abrir». Devuelve el nombre del sonido que sonó o None."""
        if evento not in EVENTOS or not self.activo():
            return None
        nombre = sonido_valido(self.ctx.ajustes["sonido_ui_tipo"])
        self.tocados.append((evento, nombre))
        tocar(nombre)
        return nombre

    def _al_me_gusta(self, _clave, ahora):
        if ahora:
            self.sonar("gusta")

    def al_abrir(self):
        """Una sola vez por sesión, cuando la ventana ya está lista."""
        if not self._abierto:
            self._abierto = True
            self.sonar("abrir")


def instalar(ctx):
    """Crea (una vez) el gestor de sonidos de la aplicación y programa el de apertura."""
    g = getattr(ctx, "sonidos_ui", None)
    if g is None:
        g = SonidosUI(ctx, ctx)
        ctx.sonidos_ui = g
        # el estado de donador llega de la copia local al instante, pero se espera un poco a que la ventana
        # termine de abrir para que el sonido acompañe lo que se ve
        QTimer.singleShot(1500, g.al_abrir)
    return g
