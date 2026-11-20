# -*- coding: utf-8 -*-
"""Despertador con música: la lógica, sin ventanas (se prueba sola).

Cada alarma dice a qué hora suena, qué días, qué suena (una canción, una lista, un mix del día, tus
«me gusta» al azar o el sonido suave de Caudal), hasta qué volumen sube, en cuántos segundos llega a él
y cuántos minutos se pospone. Las mismas claves que la app del teléfono (nucleo/despertador.dart), para
que una alarma signifique lo mismo en los dos lados.

Si al sonar no hay internet, suena lo que ya está descargado (la canción elegida si está, si no otra
descargada de tus «me gusta» o de tu música) y, si no hay nada, el sonido suave que viene con Caudal.
"""

import array
import json
import math
import random
import socket
import time
import wave
from datetime import datetime, timedelta
from pathlib import Path

from . import config

# lunes = 1 ... domingo = 7 (como DateTime.weekday en la app y isoweekday() aquí)
DIAS = (1, 2, 3, 4, 5, 6, 7)
NOMBRE_DIA = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb", 7: "Dom"}
INICIAL_DIA = {1: "L", 2: "M", 3: "X", 4: "J", 5: "V", 6: "S", 7: "D"}

TIPOS = ("cancion", "lista", "mix", "me_gusta", "tono")
NOMBRE_TIPO = {
    "cancion": "Una canción",
    "lista": "Una de tus listas",
    "mix": "Un mix del día",
    "me_gusta": "Al azar de tus «me gusta»",
    "tono": "Sonido suave de Caudal",
}

VOLUMEN_INICIAL = 0.03      # arranca casi en silencio (3 % del volumen elegido)
MAX_SONANDO_SEG = 10 * 60   # si nadie la apaga, se calla sola a los 10 minutos
TARDE_MAX_SEG = 30 * 60     # si la PC estaba dormida, suena al despertar si no pasó media hora


# ------------------------------------------------------------ alarmas

def nueva_alarma(hora=7, minuto=0, ahora=None):
    t = ahora or time.time()
    return normalizar({
        "id": f"a{int(t * 1000)}",
        "hora": hora,
        "minuto": minuto,
        "dias": [1, 2, 3, 4, 5],
        "activa": True,
        "etiqueta": "",
        "fuente": {"tipo": "me_gusta", "id": "me_gusta", "titulo": "Tus «me gusta»"},
        "volumen": 80,
        "subida": 60,
        "posponer": 9,
        "vibrar": True,
    })


def _entero(v, defecto, minimo, maximo):
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        n = defecto
    return max(minimo, min(maximo, n))


def normalizar(d):
    """Una alarma con todas sus claves y valores dentro de rango (lo que venga de disco o de la nube)."""
    d = dict(d or {})
    fuente = dict(d.get("fuente") or {})
    tipo = fuente.get("tipo") if fuente.get("tipo") in TIPOS else "tono"
    fuente["tipo"] = tipo
    fuente.setdefault("id", "")
    fuente.setdefault("titulo", NOMBRE_TIPO[tipo])
    dias = sorted({int(x) for x in (d.get("dias") or []) if str(x).isdigit() and 1 <= int(x) <= 7})
    return {
        "id": str(d.get("id") or f"a{int(time.time() * 1000)}"),
        "hora": _entero(d.get("hora"), 7, 0, 23),
        "minuto": _entero(d.get("minuto"), 0, 0, 59),
        "dias": dias,
        "activa": bool(d.get("activa", True)),
        "etiqueta": str(d.get("etiqueta") or "")[:40],
        "fuente": fuente,
        "volumen": _entero(d.get("volumen"), 80, 5, 100),
        "subida": _entero(d.get("subida"), 60, 0, 600),
        "posponer": _entero(d.get("posponer"), 9, 1, 60),
        "vibrar": bool(d.get("vibrar", True)),
        "pospuesta_hasta": float(d.get("pospuesta_hasta") or 0),
    }


def proxima_vez(alarma, ahora=None):
    """La próxima fecha en que suena (datetime local), o None si está apagada.

    Sin días es «una sola vez»: hoy si aún no pasó la hora, si no mañana. Con días, el primero de
    ellos (desde hoy) en que la hora todavía no pasó. Una pospuesta manda sobre lo demás."""
    if not alarma.get("activa"):
        return None
    ahora = ahora or datetime.now()
    pospuesta = float(alarma.get("pospuesta_hasta") or 0)
    if pospuesta > ahora.timestamp():
        return datetime.fromtimestamp(pospuesta)
    hora, minuto = int(alarma["hora"]), int(alarma["minuto"])
    dias = alarma.get("dias") or []
    for d in range(0, 8):
        dia = (ahora + timedelta(days=d)).date()
        cand = datetime(dia.year, dia.month, dia.day, hora, minuto)
        if cand <= ahora:
            continue
        if not dias or cand.isoweekday() in dias:
            return cand
    return None


def texto_dias(dias):
    dias = sorted(set(dias or []))
    if not dias:
        return "Una vez"
    if dias == list(DIAS):
        return "Todos los días"
    if dias == [1, 2, 3, 4, 5]:
        return "Entre semana"
    if dias == [6, 7]:
        return "Fines de semana"
    return ", ".join(NOMBRE_DIA[d] for d in dias)


def texto_falta(segundos):
    """«Suena en 7 h 20 min» (lo que se enseña al guardar una alarma)."""
    minutos = max(0, int(math.ceil(segundos / 60.0)))
    if minutos < 1:
        return "Suena en menos de un minuto"
    dias, resto = divmod(minutos, 24 * 60)
    horas, mins = divmod(resto, 60)
    partes = []
    if dias:
        partes.append(f"{dias} {'día' if dias == 1 else 'días'}")
    if horas:
        partes.append(f"{horas} h")
    if mins and not dias:
        partes.append(f"{mins} min")
    return "Suena en " + " ".join(partes)


def texto_hora(alarma):
    return f"{int(alarma['hora']):02d}:{int(alarma['minuto']):02d}"


def factor_volumen(segundo, subida):
    """De casi nada al volumen elegido en `subida` segundos, con curva suave (cuadrática: al principio
    sube muy despacio, que es cuando más asusta un salto)."""
    if subida <= 0:
        return 1.0
    p = max(0.0, min(1.0, segundo / float(subida)))
    return VOLUMEN_INICIAL + (1.0 - VOLUMEN_INICIAL) * p * p


def posponer(alarma, ahora=None):
    """La alarma pospuesta sus minutos desde ahora."""
    t = (ahora or datetime.now()).timestamp()
    a = dict(alarma)
    a["pospuesta_hasta"] = t + int(alarma.get("posponer") or 9) * 60
    return a


def tras_sonar(alarma):
    """Al apagarla: se olvida lo pospuesto y la de «una vez» se apaga sola."""
    a = dict(alarma)
    a["pospuesta_hasta"] = 0
    if not a.get("dias"):
        a["activa"] = False
    return a


def tocan(alarmas, ultima_mirada, ahora=None):
    """Las alarmas que debían sonar entre `ultima_mirada` y ahora (con TARDE_MAX_SEG de margen si la
    PC estuvo dormida: lo de hace más de media hora ya no suena)."""
    ahora = ahora or datetime.now()
    desde = max(ultima_mirada, ahora - timedelta(seconds=TARDE_MAX_SEG))
    salen = []
    for a in alarmas:
        p = proxima_vez(a, desde)
        if p is not None and desde < p <= ahora:
            salen.append(a)
    return salen


# ------------------------------------------------------------ qué suena

def planear(alarma, hay_red, candidatas, descargada, respaldo, azar=None):
    """Qué suena: ("pistas", [pistas], motivo) o ("tono", [], motivo).

    candidatas: las pistas de la fuente elegida (la canción, la lista, el mix o los «me gusta»).
    descargada(pista) -> bool: si está en el equipo.
    respaldo: pistas descargadas para cuando no hay red (mejor primero las de «me gusta»)."""
    azar = azar or random.Random()
    tipo = (alarma.get("fuente") or {}).get("tipo")
    if tipo == "tono":
        return "tono", [], "elegido"
    pistas = [p for p in candidatas if p]
    if tipo == "me_gusta":
        pistas = list(pistas)
        azar.shuffle(pistas)
    if hay_red and pistas:
        return "pistas", pistas, "elegido"
    locales = [p for p in pistas if descargada(p)]
    if locales:
        return "pistas", locales, "descargado" if not hay_red else "elegido"
    reserva = [p for p in respaldo if p and descargada(p)]
    if reserva:
        reserva = list(reserva)
        azar.shuffle(reserva)
        return "pistas", reserva, "respaldo"
    return "tono", [], "sin_musica"


# ------------------------------------------------------------ guardado

def archivo_alarmas():
    return config.carpeta_perfil() / "despertador.json"


def leer(ruta=None):
    ruta = Path(ruta) if ruta else archivo_alarmas()
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    lista = datos.get("alarmas") if isinstance(datos, dict) else datos
    return [normalizar(a) for a in (lista or []) if isinstance(a, dict)]


def guardar(alarmas, ruta=None):
    ruta = Path(ruta) if ruta else archivo_alarmas()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "alarmas": [normalizar(a) for a in alarmas]},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta)


def hay_internet(espera=1.5):
    for anfitrion in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            with socket.create_connection(anfitrion, timeout=espera):
                return True
        except OSError:
            continue
    return False


# ------------------------------------------------------------ el sonido suave de Caudal

FRECUENCIA = 22050
TONO_VERSION = 1


def sintetizar_tono(segundos=8.0):
    """«Amanecer»: un arpegio de marimba suave (pentatónica de Do) que se puede repetir sin corte.
    Enteros de 16 bits, mono, 22 050 Hz, con pico al 70 % (la subida de volumen la pone quien lo toca)."""
    n = int(FRECUENCIA * segundos)
    x = [0.0] * n
    # (segundo, frecuencia): sube, respira y baja; el último golpe acaba antes del final del ciclo
    base = [523.25, 659.25, 783.99, 880.00, 1046.50, 880.00, 783.99, 659.25]
    golpes = []
    for vuelta in range(2):
        for i, f in enumerate(base):
            golpes.append((vuelta * 4.0 + i * 0.42, f * (1.0 if vuelta == 0 else 0.749)))
    for inicio, frec in golpes:
        ini = int(inicio * FRECUENCIA)
        largo = int(FRECUENCIA * 1.6)
        for k in range(largo):
            j = ini + k
            if j >= n:
                break
            t = k / FRECUENCIA
            env = math.exp(-t * 3.2) * min(1.0, t * 300.0)
            v = (math.sin(math.tau * frec * t)
                 + 0.35 * math.sin(math.tau * frec * 4.0 * t) * math.exp(-t * 9.0)
                 + 0.18 * math.sin(math.tau * frec * 0.5 * t))
            x[j] += v * env
    # fundido en los bordes del ciclo: al repetirse no hay «clic»
    borde = int(FRECUENCIA * 0.02)
    for i in range(borde):
        g = i / borde
        x[i] *= g
        x[n - 1 - i] *= g
    m = max((abs(v) for v in x), default=1.0) or 1.0
    k = 0.70 * 32767.0 / m
    return [int(v * k) for v in x]


def escribir_wav(ruta, muestras):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(array.array("h", muestras).tobytes())
    return ruta


def ruta_tono():
    """El WAV del sonido suave (se fabrica una sola vez en la carpeta de datos)."""
    ruta = config.carpeta_datos() / "sonidos" / f"despertador_amanecer_v{TONO_VERSION}.wav"
    if not ruta.exists() or ruta.stat().st_size < 1000:
        escribir_wav(ruta, sintetizar_tono())
    return ruta
