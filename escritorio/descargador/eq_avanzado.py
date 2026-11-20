# -*- coding: utf-8 -*-
"""Ecualizador avanzado (donadores y fundadores): 15 bandas, preamplificador, ajustes guardados
con nombre y un ajuste para cada salida (audífonos, parlante, bluetooth) que entra solo al
cambiar de salida.

El ecualizador normal (10 bandas, `eq_bandas`) sigue igual para todos. Sin beneficios activos el
avanzado no suena aunque esté guardado (se oye el normal) y la pantalla lo muestra con candado.
Lógica pura: los ajustes son cualquier objeto con [] (el de la app o un dict en las pruebas)."""

from .salida_audio import TIPOS

# bandas de 2/3 de octava (ISO): el doble de detalle que el normal en graves y medios
FRECUENCIAS = (25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000)
ANCHO_OCTAVAS = 0.67
RANGO_BANDA = 12.0          # ± dB
PASO = 0.5
PREAMP_MIN, PREAMP_MAX = -12.0, 6.0
MAX_GUARDADOS = 30
LARGO_NOMBRE = 32

# un punto de partida por cada salida (se pueden cambiar y guardar con otro nombre)
INICIALES = {
    "Audífonos cálidos": ([2, 2.5, 2, 1, 0, 0, -0.5, -0.5, 0, 0.5, 1, 1, 0.5, 0, -0.5], -2.5),
    "Parlante pequeño": ([-6, -5, -3, 0, 2, 3, 2.5, 2, 1.5, 1, 1, 1.5, 1, 0, -1], -3.0),
    "Bluetooth claro": ([1, 1, 1, 0.5, 0, -0.5, -0.5, 0, 0.5, 1, 1.5, 2, 2, 1.5, 1], -2.0),
}


def _num(v, defecto=0.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return defecto
    return x if x == x else defecto     # NaN fuera


def limpiar_bandas(bandas):
    """Siempre 15 valores, dentro del rango y en pasos de 0,5 dB."""
    lista = list(bandas or [])[:len(FRECUENCIAS)]
    lista += [0] * (len(FRECUENCIAS) - len(lista))
    return [round(max(-RANGO_BANDA, min(RANGO_BANDA, _num(g))) / PASO) * PASO for g in lista]


def limpiar_preamp(v):
    return round(max(PREAMP_MIN, min(PREAMP_MAX, _num(v))) / PASO) * PASO


def disponible(premium):
    """El avanzado solo existe con beneficios activos."""
    return bool(premium)


def activo(ajustes, premium):
    """¿Suena el avanzado (en lugar del normal)?"""
    return disponible(premium) and bool(_leer(ajustes, "eq_avanzado", False))


def _leer(ajustes, clave, defecto=None):
    try:
        v = ajustes[clave]
    except (KeyError, TypeError):
        return defecto
    return defecto if v is None else v


def partes_filtro(bandas):
    """Filtros `equalizer` de ffmpeg para las bandas que no están a 0."""
    partes = []
    for f, g in zip(FRECUENCIAS, limpiar_bandas(bandas)):
        if abs(g) >= 0.25:
            partes.append(f"equalizer=f={f}:t=o:w={ANCHO_OCTAVAS}:g={g:.1f}")
    return partes


def ganancia_previa(bandas, preamp):
    """dB que se suman antes del ecualizador: el preamplificador que elige la persona y un margen
    automático cuando hay bandas subidas (para que no sature)."""
    bandas = limpiar_bandas(bandas)
    maximo = max([0.0] + bandas)
    return round(limpiar_preamp(preamp) - maximo * 0.6, 2)


# ================================================================ ajustes guardados con nombre

def guardados(ajustes):
    """{nombre: {"bandas": [...], "preamp": x}} con los iniciales si aún no hay nada."""
    g = _leer(ajustes, "eq_av_guardados", None)
    if not isinstance(g, dict) or not g:
        return {n: {"bandas": limpiar_bandas(b), "preamp": p} for n, (b, p) in INICIALES.items()}
    return {str(n): {"bandas": limpiar_bandas((d or {}).get("bandas")),
                     "preamp": limpiar_preamp((d or {}).get("preamp"))}
            for n, d in g.items() if isinstance(d, dict)}


def limpiar_nombre(nombre):
    return " ".join(str(nombre or "").split())[:LARGO_NOMBRE]


def guardar_ajuste(ajustes, nombre, bandas, preamp):
    """Guarda (o sobrescribe) un ajuste con nombre. Devuelve el nombre limpio, o "" si no vale."""
    nombre = limpiar_nombre(nombre)
    if not nombre:
        return ""
    g = guardados(ajustes)
    if nombre not in g and len(g) >= MAX_GUARDADOS:
        return ""
    g[nombre] = {"bandas": limpiar_bandas(bandas), "preamp": limpiar_preamp(preamp)}
    ajustes["eq_av_guardados"] = g
    return nombre


def borrar_ajuste(ajustes, nombre):
    g = guardados(ajustes)
    g.pop(nombre, None)
    ajustes["eq_av_guardados"] = g
    # la salida que lo usaba se queda sin ajuste propio
    por = dict(_leer(ajustes, "eq_por_salida", {}) or {})
    for t, n in list(por.items()):
        if n == nombre:
            por[t] = ""
    ajustes["eq_por_salida"] = por


def cargar_ajuste(ajustes, nombre):
    """Pone un ajuste guardado como el actual. True si existía."""
    d = guardados(ajustes).get(nombre)
    if d is None:
        return False
    ajustes["eq_av_bandas"] = list(d["bandas"])
    ajustes["eq_av_preamp"] = d["preamp"]
    ajustes["eq_av_nombre"] = nombre
    return True


# ================================================================ por salida

def por_salida(ajustes):
    por = _leer(ajustes, "eq_por_salida", {}) or {}
    return {t: str(por.get(t) or "") for t in TIPOS}


def asignar_salida(ajustes, tipo, nombre):
    if tipo not in TIPOS:
        return
    por = por_salida(ajustes)
    por[tipo] = nombre if nombre in guardados(ajustes) else ""
    ajustes["eq_por_salida"] = por


def al_cambiar_salida(ajustes, premium, tipo_antes, tipo_ahora):
    """Se llama cuando cambia la salida. Si es otra y tiene un ajuste asignado, lo pone y enciende
    el avanzado. Devuelve el nombre puesto o None (nada cambió).

    Solo al CAMBIAR: abrir la app con los mismos audífonos no pisa lo que se dejó a mano."""
    if not disponible(premium) or not tipo_ahora or tipo_ahora == tipo_antes:
        return None
    if tipo_antes is None:
        return None                     # primera lectura al arrancar: solo se anota
    nombre = por_salida(ajustes).get(tipo_ahora) or ""
    if not nombre or not cargar_ajuste(ajustes, nombre):
        return None
    ajustes["eq_avanzado"] = True
    return nombre
