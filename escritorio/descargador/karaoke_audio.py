# -*- coding: utf-8 -*-
"""Lo que suena en el karaoke: bajar la voz de la canción, cambiar el tono, y escucharte para el puntaje.

- **Voz**: casi todas las canciones llevan la voz en el centro del estéreo. Se quita el centro y se deja lo de los
  lados; los graves (bombo y bajo, también centrados) van por otro camino para que no se pierdan. No es magia: en
  canciones con la voz abierta o grabadas en mono queda algo de voz.
- **Tono**: de -6 a +6 semitonos sin cambiar la velocidad (rubberband).
- **Micrófono**: solo con permiso (se enciende con su botón). Del sonido se mira el volumen, en memoria y al momento:
  no se graba, no se guarda y no sale de la PC. El puntaje dice si cantas cuando toca, no si afinas.

Las cuentas (`partes`, `Puntaje`, `nivel`) no tocan Qt ni el audio: se prueban solas.
"""

import array
import ctypes
import sys
import threading
import time

VOCES = {"original": ("Voz original", 0.0), "baja": ("Voz baja", 0.72), "sin": ("Sin voz", 1.0)}
TONO_MAX = 6
CORTE_GRAVES = 150                # Hz: por debajo no hay voz que quitar


def tono_valido(n):
    try:
        return max(-TONO_MAX, min(TONO_MAX, int(n)))
    except (TypeError, ValueError):
        return 0


def partes(voz="original", tono=0):
    """Los filtros (para meter en una cadena lavfi) del karaoke."""
    salida = []
    quita = VOCES.get(voz, VOCES["original"])[1]
    if quita > 0:
        medio = max(0.016, 1.0 - quita)
        salida.append(
            f"aformat=channel_layouts=stereo,asplit=2[kgra][kres];[kgra]lowpass=f={CORTE_GRAVES}[kg];"
            f"[kres]highpass=f={CORTE_GRAVES},stereotools=mlev={medio:.3f}[kr];"
            f"[kg][kr]amix=inputs=2:normalize=0")
        salida.append(f"volume={2.5 * quita:.2f}dB")
    tono = tono_valido(tono)
    if tono:
        salida.append(f"rubberband=pitch={2.0 ** (tono / 12.0):.6f}")
    return salida


# ------------------------------------------------------------------ micrófono

TASA = 16000
TROZO_S = 0.05


def nivel(pcm):
    """Volumen (0..1) de un trozo de 16 bits mono."""
    n = len(pcm) // 2
    if not n:
        return 0.0
    m = array.array("h")
    m.frombytes(bytes(pcm[:n * 2]))
    m = m[::2]                                    # de sobra para medir el volumen, a la mitad de trabajo
    media = sum(m) / len(m)
    return min(1.0, (sum((x - media) ** 2 for x in m) / len(m)) ** 0.5 / 32768.0)


class Microfono:
    """Escucha el micrófono en un hilo y deja su volumen en `nivel_ahora`. Sin guardar nada."""

    def __init__(self):
        self.nivel_ahora = 0.0
        self.error = ""
        self._parar = threading.Event()
        self._hilo = None

    @property
    def encendido(self):
        return self._hilo is not None and self._hilo.is_alive()

    def encender(self):
        if self.encendido:
            return
        self.error = ""
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._escuchar, args=(self._parar,), name="karaoke-microfono",
                                      daemon=True)
        self._hilo.start()

    def apagar(self):
        self._parar.set()
        self._hilo = None
        self.nivel_ahora = 0.0

    def _escuchar(self, parar):
        if sys.platform != "win32":
            self.error = "El micrófono solo funciona en Windows."
            return
        from . import que_suena as Q
        try:
            mm = Q._winmm()
            if mm.waveInGetNumDevs() == 0:
                self.error = "No hay ningún micrófono conectado."
                return
            fmt = Q._FORMATO(1, 1, TASA, TASA * 2, 2, 16, 0)
            h = ctypes.c_void_p()
            if mm.waveInOpen(ctypes.byref(h), ctypes.c_uint(Q.WAVE_MAPPER), ctypes.byref(fmt), None, None, 0):
                self.error = "No se pudo abrir el micrófono. Revisa el permiso en Windows."
                return
        except Exception:  # noqa: BLE001
            self.error = "No se pudo abrir el micrófono."
            return
        tam_cab = ctypes.sizeof(Q._CABECERA)
        octetos = int(TASA * TROZO_S) * 2
        cabs = []
        try:
            for _ in range(4):
                datos = ctypes.create_string_buffer(octetos)
                c = Q._CABECERA()
                c.lpData = ctypes.cast(datos, ctypes.c_void_p)
                c.dwBufferLength = octetos
                if mm.waveInPrepareHeader(h, ctypes.byref(c), tam_cab) or mm.waveInAddBuffer(h, ctypes.byref(c), tam_cab):
                    self.error = "No se pudo usar el micrófono."
                    return
                cabs.append((c, datos))
            if mm.waveInStart(h):
                self.error = "No se pudo usar el micrófono."
                return
            while not parar.is_set():
                for c, datos in cabs:
                    if c.dwFlags & 1:                          # WHDR_DONE
                        self.nivel_ahora = nivel(datos.raw[:c.dwBytesRecorded])
                        c.dwFlags &= ~1
                        mm.waveInAddBuffer(h, ctypes.byref(c), tam_cab)
                time.sleep(0.02)
        except Exception:  # noqa: BLE001
            self.error = "Se perdió el micrófono."
        finally:
            try:
                mm.waveInStop(h)
                mm.waveInReset(h)
                for c, _d in cabs:
                    mm.waveInUnprepareHeader(h, ctypes.byref(c), tam_cab)
                mm.waveInClose(h)
            except Exception:  # noqa: BLE001
                pass
            if parar is self._parar:
                self.nivel_ahora = 0.0


# ------------------------------------------------------------------ puntaje

NOTAS = ((0.72, "¡Perfecto!", 100), (0.50, "¡Muy bien!", 70), (0.25, "Bien", 40))


def nota_de(parte):
    """(texto, puntos) de un verso según la parte que se cantó."""
    for minimo, texto, puntos in NOTAS:
        if parte >= minimo:
            return texto, puntos
    return "", 0


class Puntaje:
    """Si cantas cuando toca. Aprende solo el ruido de fondo (la música que entra por el micrófono)."""

    SUELO = 0.006

    def __init__(self):
        self.empezar()

    def empezar(self):
        self.puntos = 0
        self.combo = 0
        self.mejor_combo = 0
        self.versos = 0
        self.suma = 0.0
        self.fondo = self.SUELO
        self._verso = None
        self._canto = self._total = 0.0
        self.cantando = False

    def umbral(self):
        return max(self.SUELO, self.fondo * 1.9)

    def oir(self, vol, verso, toca, dt):
        """Un instante: volumen del micrófono, qué verso suena (o None) y si ahora toca cantar.
        Devuelve (texto, puntos) al acabar un verso, o None."""
        aviso = None
        if verso != self._verso:
            aviso = self._cerrar()
            self._verso = verso
        self.cantando = vol > self.umbral()
        if not toca:
            # con la música sola se aprende cuánto se cuela por el micrófono
            self.fondo += (max(self.SUELO, min(0.2, vol)) - self.fondo) * min(1.0, dt * 1.5)
            return aviso
        if verso is not None:
            self._total += dt
            if self.cantando:
                self._canto += dt
        return aviso

    def _cerrar(self):
        total, canto = self._total, self._canto
        self._total = self._canto = 0.0
        if self._verso is None or total < 0.4:
            return None
        parte = min(1.0, canto / (total * 0.85))      # entre palabra y palabra se respira
        texto, puntos = nota_de(parte)
        self.versos += 1
        self.suma += parte
        if puntos >= 70:
            self.combo += 1
            self.mejor_combo = max(self.mejor_combo, self.combo)
        else:
            self.combo = 0
        self.puntos += puntos + min(50, max(0, self.combo - 1) * 10) if puntos else 0
        return texto, puntos

    def porcentaje(self):
        return int(round(100 * self.suma / self.versos)) if self.versos else 0

    def estrellas(self):
        p = self.porcentaje()
        return 5 if p >= 85 else 4 if p >= 70 else 3 if p >= 50 else 2 if p >= 30 else 1
