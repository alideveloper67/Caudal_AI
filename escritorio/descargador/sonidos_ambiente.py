# -*- coding: utf-8 -*-
"""Sonidos ambientales del modo estudio: se fabrican en el equipo, sin descargar nada.

Cada sonido es una pista de unos 24 s (mono, 22,05 kHz, 16 bits) que se guarda como WAV en
la carpeta de caché y suena en bucle con su propia instancia de mpv (nunca con la de la
música). Todo en Python puro (la app no trae numpy). El bucle no hace clic: la pista se
fabrica un poco más larga y su principio se funde con lo que sobra del final, de modo que
la última muestra enlaza con la primera como si el sonido siguiera.

Recetas:
    blanco    muestras uniformes
    rosa      Voss-McCartney (-3 dB por octava)
    marron    ruido blanco integrado con fuga (-6 dB por octava)
    lluvia    rosa pasa-altos + gotas aleatorias + fondo suave
    chimenea  marrón suave + chasquidos aleatorios
    cafeteria murmullo (rosa pasa-banda 300-2500 Hz con modulación lenta) + tintineos
    bosque    viento (rosa pasa-bajos modulado) + trinos de pájaros con barrido
"""

import array
import math
import random
import sys
import wave
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from . import config
from .hilos import en_segundo_plano

FRECUENCIA = 22050
DURACION = 24.0          # segundos de la pista que se guarda
EMPALME = 2.0            # segundos que se funden para que el bucle no haga clic
VERSION = 2              # súbela si cambia una receta: se vuelve a fabricar

CAPAS = (
    ("lluvia", "Lluvia", "Gotas suaves en una ventana"),
    ("cafeteria", "Cafetería", "Murmullo lejano y tazas"),
    ("bosque", "Bosque", "Viento entre hojas y pájaros"),
    ("chimenea", "Chimenea", "Fuego tranquilo que crepita"),
    ("blanco", "Ruido blanco", "Parejo, tapa lo que distrae"),
    ("rosa", "Ruido rosa", "Más suave, como una cascada lejana"),
    ("marron", "Ruido marrón", "Grave y envolvente"),
)
NOMBRES = {c: n for c, n, _d in CAPAS}
DESCRIPCIONES = {c: d for c, _n, d in CAPAS}

# nivel (RMS, de 0 a 1 de la escala completa) con el que se guarda cada sonido; el
# volumen de cada capa lo pone la persona
NIVEL = {"lluvia": 0.17, "cafeteria": 0.15, "bosque": 0.15, "chimenea": 0.16,
         "blanco": 0.12, "rosa": 0.15, "marron": 0.17}
SEMILLA = {c: 1000 + i * 77 for i, (c, _n, _d) in enumerate(CAPAS)}


# ---------------------------------------------------------------------- filtros y ruidos

def _rms(x):
    return math.sqrt(sum(v * v for v in x) / max(1, len(x)))


def _a_rms(x, objetivo=1.0):
    r = _rms(x)
    g = objetivo / r if r > 1e-12 else 0.0
    return [v * g for v in x]


def _paso_bajo(x, fc):
    """Filtro de un polo."""
    a = 1.0 - math.exp(-2.0 * math.pi * fc / FRECUENCIA)
    y = 0.0
    salida = []
    anadir = salida.append
    for v in x:
        y += a * (v - y)
        anadir(y)
    return salida


def _paso_alto(x, fc):
    return [v - b for v, b in zip(x, _paso_bajo(x, fc))]


def _blanco(rng, n):
    r = rng.random
    return [r() * 2.0 - 1.0 for _ in range(n)]


def _rosa(rng, n, filas=14):
    """Voss-McCartney: cada fila se renueva el doble de despacio que la anterior."""
    r = rng.random
    f = [r() * 2.0 - 1.0 for _ in range(filas)]
    suma = sum(f)
    salida = []
    anadir = salida.append
    cont = 0
    div = filas + 1.0
    for _ in range(n):
        cont += 1
        k = (cont & -cont).bit_length() - 1
        if k < filas:
            suma -= f[k]
            f[k] = r() * 2.0 - 1.0
            suma += f[k]
        anadir((suma + r() * 2.0 - 1.0) / div)
    return salida


def _marron(rng, n, fuga=0.998):
    """Ruido blanco integrado con fuga: por debajo de ~7 Hz se aplana para no derivar."""
    r = rng.random
    y = 0.0
    salida = []
    anadir = salida.append
    for _ in range(n):
        y = y * fuga + (r() * 2.0 - 1.0)
        anadir(y)
    media = sum(salida) / max(1, n)
    return [v - media for v in salida]


def _lfo(n, partes):
    """Modulación lenta: suma de senos [(frecuencia Hz, amplitud, fase)] más una base."""
    base, senos = partes
    w = 2.0 * math.pi / FRECUENCIA
    return [base + sum(a * math.sin(w * f * i + ph) for f, a, ph in senos) for i in range(n)]


def _sumar_en(destino, origen, inicio, escala=1.0):
    n = len(destino)
    if inicio >= n:
        return
    for j, v in enumerate(origen[:n - inicio]):
        destino[inicio + j] += v * escala


def _seno_amortiguado(frec, caida_s, amp, largo_s=None):
    """Un tañido: seno que se apaga como exp(-t/caida); empieza con 8 ms de subida."""
    largo = int((largo_s or caida_s * 6.0) * FRECUENCIA)
    w = 2.0 * math.pi * frec / FRECUENCIA
    k = math.exp(-1.0 / (caida_s * FRECUENCIA))
    subida = max(1, int(0.008 * FRECUENCIA))
    e = 1.0
    salida = []
    for j in range(largo):
        sube = j / subida if j < subida else 1.0
        salida.append(amp * math.sin(w * j) * e * sube)
        e *= k
    return salida


# ---------------------------------------------------------------------- las recetas

def _lluvia(rng, n):
    hiss = _a_rms(_paso_alto(_rosa(rng, n), 1100.0))
    fondo = _a_rms(_paso_bajo(_rosa(rng, n), 260.0))
    mezcla = [0.55 * h + 0.22 * f for h, f in zip(hiss, fondo)]
    gotas = [0.0] * n
    for _ in range(int(n / FRECUENCIA * 70)):
        ini = rng.randrange(n)
        dec = rng.uniform(0.004, 0.011)
        golpe = _seno_amortiguado(rng.uniform(1800.0, 5200.0), dec, rng.random() ** 2 * 0.9 + 0.1,
                                  dec * 5.0)
        _sumar_en(gotas, golpe, ini)
    return [m + 0.28 * g for m, g in zip(mezcla, gotas)]


def _chimenea(rng, n):
    base = _a_rms(_paso_bajo(_marron(rng, n), 380.0), 0.55)
    fuego = _a_rms(_paso_alto(_paso_bajo(_rosa(rng, n), 900.0), 120.0), 0.12)
    mezcla = [b + f for b, f in zip(base, fuego)]
    ruido = rng.random
    for _ in range(int(n / FRECUENCIA * 15)):
        ini = rng.randrange(n)
        largo = int(rng.uniform(0.002, 0.014) * FRECUENCIA)
        amp = (rng.random() ** 2.6) * 3.2 + 0.12
        k = math.exp(-5.0 / max(1, largo))
        e = amp
        for j in range(min(largo, n - ini)):
            mezcla[ini + j] += (ruido() * 2.0 - 1.0) * e
            e *= k
    for _ in range(int(n / FRECUENCIA * 0.5)):          # algún chasquido más grande
        ini = rng.randrange(n)
        largo = int(rng.uniform(0.008, 0.02) * FRECUENCIA)
        k = math.exp(-4.0 / max(1, largo))
        e = rng.uniform(2.0, 3.4)
        for j in range(min(largo, n - ini)):
            mezcla[ini + j] += (ruido() * 2.0 - 1.0) * e
            e *= k
    return [math.tanh(v * 0.85) for v in mezcla]


def _cafeteria(rng, n):
    f = lambda: rng.uniform(0.0, 2 * math.pi)  # noqa: E731
    voz = _paso_bajo(_paso_bajo(_paso_alto(_rosa(rng, n), 300.0), 2500.0), 3200.0)
    voz = _a_rms(voz)
    m1 = _lfo(n, (0.58, [(0.21, 0.22, f()), (0.53, 0.18, f())]))
    sil = _a_rms(_paso_bajo(_paso_bajo(_paso_alto(_rosa(rng, n), 450.0), 1500.0), 2000.0))
    m2 = _lfo(n, (0.5, [(1.7, 0.2, f()), (2.9, 0.18, f()), (0.37, 0.1, f())]))
    mezcla = [a * b + 0.45 * c * d for a, b, c, d in zip(voz, m1, sil, m2)]
    t = rng.uniform(0.6, 3.0)
    while t * FRECUENCIA < n:
        for _ in range(rng.choice((1, 1, 2, 3))):
            ini = int(t * FRECUENCIA)
            frec = rng.uniform(2100.0, 4800.0)
            amp = rng.uniform(0.35, 0.7)
            caida = rng.uniform(0.12, 0.30)
            for parcial, peso in ((1.0, 1.0), (2.76, 0.45), (5.4, 0.18)):
                if frec * parcial < 9500.0:
                    _sumar_en(mezcla, _seno_amortiguado(frec * parcial, caida / parcial ** 0.5,
                                                        amp * peso), ini)
            t += rng.uniform(0.1, 0.4)
        t += rng.uniform(3.0, 9.0)
    return mezcla


def _bosque(rng, n):
    f = lambda: rng.uniform(0.0, 2 * math.pi)  # noqa: E731
    viento = _a_rms(_paso_bajo(_paso_bajo(_rosa(rng, n), 650.0), 900.0))
    hojas = _a_rms(_paso_alto(_rosa(rng, n), 2200.0))
    racha = _lfo(n, (0.5, [(0.09, 0.26, f()), (0.17, 0.2, f()), (0.041, 0.1, f())]))
    mezcla = [v * g + 0.10 * h * g * g for v, h, g in zip(viento, hojas, racha)]
    w2 = 2.0 * math.pi / FRECUENCIA
    t = rng.uniform(0.5, 3.0)
    while t * FRECUENCIA < n:
        base = rng.uniform(2600.0, 5000.0)
        for _ in range(rng.randint(2, 6)):
            largo = int(rng.uniform(0.05, 0.13) * FRECUENCIA)
            f0 = base * rng.uniform(0.92, 1.08)
            barrido = rng.uniform(-1400.0, 1400.0)
            amp = rng.uniform(0.28, 0.5)
            ini = int(t * FRECUENCIA)
            fase = 0.0
            nota = []
            for j in range(largo):
                u = j / largo
                fase += w2 * (f0 + barrido * u)
                nota.append(amp * math.sin(fase) * math.sin(math.pi * u) ** 2)
            _sumar_en(mezcla, nota, ini)
            t += largo / FRECUENCIA + rng.uniform(0.04, 0.11)
        t += rng.uniform(2.0, 7.0)
    return mezcla


RECETAS = {
    "blanco": lambda rng, n: _blanco(rng, n),
    "rosa": lambda rng, n: _rosa(rng, n),
    "marron": lambda rng, n: _marron(rng, n),
    "lluvia": _lluvia,
    "chimenea": _chimenea,
    "cafeteria": _cafeteria,
    "bosque": _bosque,
}


def _cerrar_bucle(x, n, empalme):
    """De n + empalme muestras saca n: el principio se funde (a potencia igual) con lo que
    sobra del final, así la muestra n-1 enlaza con la 0 sin salto."""
    salida = x[:n]
    for i in range(empalme):
        u = (i + 0.5) / empalme * (math.pi / 2.0)
        salida[i] = x[i] * math.sin(u) + x[n + i] * math.cos(u)
    return salida


def fabricar(capa, segundos=DURACION, empalme=EMPALME, frecuencia=FRECUENCIA):
    """Las muestras (enteros de 16 bits, array 'h') de un sonido, listas para guardar."""
    if capa not in RECETAS:
        raise ValueError(f"Sonido desconocido: {capa}")
    rng = random.Random(SEMILLA.get(capa, 1))
    n = int(segundos * FRECUENCIA)
    e = int(empalme * FRECUENCIA)
    x = RECETAS[capa](rng, n + e)
    x = _cerrar_bucle(x, n, e)
    media = sum(x) / len(x)
    x = [v - media for v in x]
    pico = max(abs(v) for v in x) or 1.0
    ganancia = min(NIVEL.get(capa, 0.15) / (_rms(x) or 1.0), 0.88 / pico)
    return array.array("h", [int(round(v * ganancia * 32767.0)) for v in x])


def campana(segundos=3.6):
    """Una campana suave: tres parciales que se apagan, con entrada sin golpe."""
    n = int(segundos * FRECUENCIA)
    x = [0.0] * n
    for frec, peso, caida in ((660.0, 1.0, 0.9), (1320.0 * 1.003, 0.32, 0.6),
                              (1812.0, 0.22, 0.42), (2718.0, 0.10, 0.26)):
        _sumar_en(x, _seno_amortiguado(frec, caida, peso, segundos), 0)
    cola = int(0.6 * FRECUENCIA)                      # el final se apaga del todo
    for i in range(cola):
        x[n - 1 - i] *= (i / cola)
    pico = max(abs(v) for v in x) or 1.0
    return array.array("h", [int(round(v / pico * 0.6 * 32767.0)) for v in x])


# ---------------------------------------------------------------------- archivos

def carpeta_cache():
    ruta = config.carpeta_datos() / "cache" / "ambiente"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def guardar_wav(ruta, muestras, frecuencia=FRECUENCIA):
    datos = array.array("h", muestras)
    if sys.byteorder == "big":
        datos.byteswap()
    tmp = str(ruta) + ".tmp"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(frecuencia)
        w.writeframes(datos.tobytes())
    Path(tmp).replace(ruta)


def leer_wav(ruta):
    """(muestras, frecuencia, canales, bits) de un WAV de 16 bits."""
    with wave.open(str(ruta), "rb") as w:
        crudo = w.readframes(w.getnframes())
        datos = array.array("h")
        datos.frombytes(crudo)
        if sys.byteorder == "big":
            datos.byteswap()
        return datos, w.getframerate(), w.getnchannels(), w.getsampwidth() * 8


class Generador:
    """Fabrica los WAV la primera vez y los reutiliza después."""

    def __init__(self, carpeta=None, segundos=DURACION, empalme=EMPALME):
        self.carpeta = Path(carpeta) if carpeta else carpeta_cache()
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.segundos = segundos
        self.empalme = empalme

    def ruta(self, capa):
        return self.carpeta / f"{capa}-v{VERSION}-{int(self.segundos)}s.wav"

    def asegurar(self, capa):
        """La ruta del WAV de ese sonido, fabricándolo si hace falta (tarda unos segundos:
        va en un hilo)."""
        ruta = self.ruta(capa)
        if ruta.exists() and ruta.stat().st_size > 1000:
            return str(ruta)
        if capa == "campana":
            guardar_wav(ruta, campana())
        else:
            guardar_wav(ruta, fabricar(capa, self.segundos, self.empalme))
        return str(ruta)


# ---------------------------------------------------------------------- reproducción

class MotorBucle:
    """Una instancia propia de mpv para un sonido (usa el mismo Motor que la música,
    pero uno aparte por sonido: nunca se comparte con el de la música)."""

    def __init__(self, ajustes, nombre):
        from .reproduccion import Motor
        self._m = Motor(ajustes, None, f"ambiente-{nombre}")

    def reproducir(self, ruta, volumen, bucle=True):
        try:
            self._m.mpv["loop-file"] = "inf" if bucle else "no"
        except Exception:  # noqa: BLE001
            pass
        self._m.fijar_volumen(volumen)
        self._m.cargar({"archivo": str(ruta), "titulo": ""})

    def fijar_volumen(self, v):
        self._m.fijar_volumen(v)

    def detener(self):
        self._m.detener()

    def cerrar(self):
        self._m.cerrar()


def volumen_mpv(v):
    """La perilla de 0 a 100 no es lineal: así los primeros pasos son suaves."""
    return (max(0, min(100, float(v))) / 100.0) ** 1.8 * 100.0


class Mezclador(QObject):
    """Las capas de sonido: cada una se enciende y se apaga sola y tiene su volumen."""

    cambio = Signal()
    aviso = Signal(str)
    VOLUMEN_INICIAL = 45

    def __init__(self, ajustes=None, fabrica=None, generador=None, padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self._fabrica = fabrica or (lambda nombre: MotorBucle(self.ajustes, nombre))
        self.generador = generador or Generador()
        self.estado = {c: {"on": False, "vol": self.VOLUMEN_INICIAL} for c, _n, _d in CAPAS}
        self._motores = {}
        self._preparando = set()
        self._cerrado = False

    # ---- estado
    def exportar_estado(self):
        return {c: dict(v) for c, v in self.estado.items()}

    def cargar_estado(self, capas):
        """Recupera lo guardado. Solo pone los valores: los sonidos se encienden cuando la
        persona empieza a estudiar o los pulsa."""
        for c, v in (capas or {}).items():
            if c in self.estado and isinstance(v, dict):
                self.estado[c]["vol"] = max(0, min(100, int(v.get("vol", self.VOLUMEN_INICIAL))))
                self.estado[c]["on"] = False

    def hay_algo_encendido(self):
        return any(v["on"] for v in self.estado.values())

    def activas(self):
        return [c for c, v in self.estado.items() if v["on"]]

    # ---- acciones
    def encender(self, capa, si=True):
        if capa not in self.estado:
            return
        self.estado[capa]["on"] = bool(si)
        if si:
            self._arrancar(capa)
        else:
            m = self._motores.get(capa)
            if m is not None:
                try:
                    m.detener()
                except Exception:  # noqa: BLE001
                    pass
        self.cambio.emit()

    def volumen(self, capa, v):
        if capa not in self.estado:
            return
        self.estado[capa]["vol"] = max(0, min(100, int(v)))
        m = self._motores.get(capa)
        if m is not None and self.estado[capa]["on"]:
            try:
                m.fijar_volumen(volumen_mpv(self.estado[capa]["vol"]))
            except Exception:  # noqa: BLE001
                pass
        self.cambio.emit()

    def aplicar_mezcla(self, mezcla):
        """{capa: volumen}: las que valen 0 se apagan; las demás se encienden con ese volumen."""
        for c in self.estado:
            v = int(mezcla.get(c, 0) or 0)
            if v > 0:
                self.estado[c]["vol"] = max(1, min(100, v))
                self.estado[c]["on"] = True
                self._arrancar(c)
            else:
                self.encender_sin_aviso(c, False)
        self.cambio.emit()

    def encender_sin_aviso(self, capa, si):
        self.estado[capa]["on"] = bool(si)
        if not si:
            m = self._motores.get(capa)
            if m is not None:
                try:
                    m.detener()
                except Exception:  # noqa: BLE001
                    pass

    def apagar_todo(self, guardar=True):
        for c in self.estado:
            self.encender_sin_aviso(c, False)
        self.cambio.emit()

    # ---- motores
    def _arrancar(self, capa):
        if self._cerrado:
            return
        ruta = self.generador.ruta(capa)
        if ruta.exists() and ruta.stat().st_size > 1000:
            self._sonar(capa, str(ruta))
            return
        if capa in self._preparando:
            return
        self._preparando.add(capa)
        en_segundo_plano(self.generador.asegurar, capa, ok=lambda r, c=capa: self._listo(c, r),
                         error=lambda e, c=capa: self._fallo(c, e), dueno=self)

    def esta_preparando(self, capa=None):
        return bool(self._preparando) if capa is None else capa in self._preparando

    def _listo(self, capa, ruta):
        self._preparando.discard(capa)
        if self.estado[capa]["on"] and not self._cerrado:
            self._sonar(capa, ruta)
        self.cambio.emit()

    def _fallo(self, capa, _e):
        self._preparando.discard(capa)
        self.estado[capa]["on"] = False
        self.aviso.emit(f"No se pudo preparar el sonido «{NOMBRES.get(capa, capa)}».")
        self.cambio.emit()

    def _motor(self, nombre):
        m = self._motores.get(nombre)
        if m is None:
            m = self._fabrica(nombre)
            self._motores[nombre] = m
        return m

    def _sonar(self, capa, ruta):
        try:
            m = self._motor(capa)
            m.reproducir(ruta, volumen_mpv(self.estado[capa]["vol"]), True)
        except Exception as e:  # noqa: BLE001 - sin mpv no hay sonido, pero la app sigue
            self.estado[capa]["on"] = False
            self.aviso.emit("No se pudo reproducir el sonido ambiental en este equipo.")
            self._ultimo_error = str(e)
            self.cambio.emit()

    def tocar_campana(self, fuerza=1.0):
        """La campana de fin de bloque, con su propio motor (el WAV se fabrica una vez)."""
        ruta = self.generador.ruta("campana")
        if not ruta.exists():
            self.generador.asegurar("campana")
        m = self._motor("campana")
        m.reproducir(str(ruta), max(0.0, min(1.0, fuerza)) * 55.0, False)

    def cerrar(self):
        self._cerrado = True
        for m in self._motores.values():
            try:
                m.detener()
                m.cerrar()
            except Exception:  # noqa: BLE001
                pass
        self._motores.clear()
