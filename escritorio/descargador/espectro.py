# -*- coding: utf-8 -*-
"""De dónde sale la «energía» que mueve el visualizador (sin Qt, probable con datos inventados).

Dos fuentes, la mejor disponible:

1. **Medida**: el motor (mpv) mide el nivel del audio que suena con un filtro de medición (`astats`): RMS y pico
   en dB. De ahí salen la energía y los golpes (un pico que sube de golpe sobre el nivel medio).
2. **Ritmo**: si el motor no mide (no hay filtro, está cargando…), la animación sigue el ritmo conocido de la
   canción (tempo y compás guardados por el análisis; sin él, 100 pulsos por minuto) mientras suena.

mpv no entrega el espectro por bandas, así que las barras se reparten esa energía entre graves y agudos con un
vaivén propio de cada barra: se mueven con la música, no son un analizador por frecuencias.
"""

import math

N_BANDAS = 48
PISO_DB = -54.0            # por debajo de esto, silencio
TECHO_DB = -8.0            # y esto es «a tope»
BPM_POR_DEFECTO = 100.0


def db_a_unidad(db, piso=PISO_DB, techo=TECHO_DB):
    """Decibelios (negativos) a 0..1 con una curva suave."""
    try:
        db = float(db)
    except (TypeError, ValueError):
        return 0.0
    if db != db:                       # NaN
        return 0.0
    x = (db - piso) / (techo - piso)
    x = max(0.0, min(1.0, x))
    return x ** 1.35


def pulso_de_ritmo(pos, bpm, fase=0.0):
    """Un golpe por pulso: 1.0 justo en el pulso y cayendo hasta ~0 antes del siguiente."""
    bpm = float(bpm or BPM_POR_DEFECTO)
    if bpm <= 0:
        bpm = BPM_POR_DEFECTO
    ciclo = ((float(pos) - float(fase or 0.0)) * bpm / 60.0) % 1.0
    return (1.0 - ciclo) ** 3


def _acercar(actual, objetivo, dt, subida, bajada):
    k = subida if objetivo > actual else bajada
    return actual + (objetivo - actual) * (1.0 - math.exp(-dt * k))


class ModeloAudio:
    """Energía (0..1), golpe (0..1) y N bandas suavizadas, listas para dibujar."""

    def __init__(self, n_bandas=N_BANDAS):
        self.n = int(n_bandas)
        self.energia = 0.0
        self.golpe = 0.0
        self.bandas = [0.0] * self.n
        self.picos = [0.0] * self.n         # la «tapita» de cada barra, que cae despacio
        self.fuente = "ritmo"                # medida | ritmo
        self._media = 0.0                    # energía media lenta (para detectar golpes)
        self._t = 0.0

    def quieto(self):
        """Todo en reposo: el reloj del dibujo puede descansar."""
        return self.energia < 0.004 and self.golpe < 0.004 and max(self.bandas) < 0.004 and max(self.picos) < 0.004

    def reiniciar(self):
        self.energia = self.golpe = self._media = 0.0
        self.bandas = [0.0] * self.n
        self.picos = [0.0] * self.n

    def avanzar(self, dt, nivel=None, sonando=True, pos=0.0, bpm=None, fase=0.0):
        """Un paso de `dt` segundos. `nivel`: (rms_db, pico_db) medidos, o None."""
        dt = max(0.0, min(0.25, float(dt)))
        self._t += dt
        if not sonando:
            objetivo, golpe_obj = 0.0, 0.0
            self.fuente = "medida" if nivel is not None else self.fuente
        elif nivel is not None:
            self.fuente = "medida"
            rms, pico = db_a_unidad(nivel[0]), db_a_unidad(nivel[1])
            objetivo = 0.65 * rms + 0.35 * pico
            # golpe: lo que el pico sube por encima de la media lenta
            golpe_obj = max(0.0, min(1.0, (pico - self._media) * 2.2))
        else:
            self.fuente = "ritmo"
            p = pulso_de_ritmo(pos, bpm, fase)
            objetivo = 0.30 + 0.45 * p
            golpe_obj = p
        self._media = _acercar(self._media, objetivo, dt, 1.2, 1.2)
        self.energia = _acercar(self.energia, objetivo, dt, 20.0, 5.0)
        self.golpe = _acercar(self.golpe, golpe_obj, dt, 35.0, 7.0)
        t = self._t
        n = self.n
        for i in range(n):
            x = i / max(1, n - 1)                              # 0 graves .. 1 agudos
            peso = 0.30 + 0.70 * (1.0 - x) ** 0.7              # los graves se llevan más energía
            vaiven = 0.55 + 0.45 * abs(math.sin(t * (1.1 + 0.37 * i) + i * 1.7))
            obj = self.energia * peso * vaiven + self.golpe * 0.40 * (1.0 - x) ** 2
            obj = max(0.0, min(1.0, obj))
            self.bandas[i] = _acercar(self.bandas[i], obj, dt, 28.0, 7.0)
            # la tapita sube con la barra y cae despacio
            self.picos[i] = max(self.bandas[i], self.picos[i] - dt * 0.35)
        return self
