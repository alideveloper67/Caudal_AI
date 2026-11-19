# -*- coding: utf-8 -*-
"""«Tu año en Caudal»: el resumen del año calculado de tus escuchas locales (sin Qt, sin red).

Recibe el historial como lo da `mixes.leer_historial` (lista de {"pista", "fecha": datetime}) y devuelve
un diccionario con lo que se cuenta en la imagen para estados: minutos escuchados, tu canción y tu artista
del año, tu top 5 de artistas, el ánimo que más sonó, tu mejor racha y el día que más escuchaste."""

from datetime import datetime, timedelta

from . import mixes
from .recomendador import animo_de

MINIMO_ESCUCHAS = 5       # con menos no hay año que contar

NOMBRES_ANIMO = {"triste": "Melancólico", "fiesta": "Fiestero", "romantica": "Romántico"}
FRASES_ANIMO = {"triste": "Tu año sonó a sentimientos", "fiesta": "Tu año sonó a fiesta",
                "romantica": "Tu año sonó a amor"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def _titulo(p):
    return str((p or {}).get("titulo") or "").strip()


def _artista_visible(p):
    arts = mixes.artistas_de(p)
    return arts[0][1] if arts else str((p or {}).get("artista") or "").strip()


def mejor_racha(dias):
    """Los días seguidos más largos con escuchas. `dias`: conjunto de date."""
    mejor = actual = 0
    previo = None
    for d in sorted(dias):
        actual = actual + 1 if previo is not None and d - previo == timedelta(days=1) else 1
        mejor = max(mejor, actual)
        previo = d
    return mejor


def calcular(historial, anio=None, ahora=None):
    """El resumen del año `anio` (por defecto el actual). Siempre devuelve el diccionario; `hay_datos` dice si
    alcanza para mostrarlo."""
    hoy = ahora or datetime.now()
    anio = int(anio or hoy.year)
    escuchas = [e for e in historial if isinstance(e.get("fecha"), datetime) and e["fecha"].year == anio
                and (e.get("pista") or {}).get("clave")]
    por_cancion, por_artista, por_dia, por_mes, animos = {}, {}, {}, {}, {}
    pista_de = {}
    segundos = 0
    for e in escuchas:
        p = e["pista"]
        clave = str(p["clave"])
        por_cancion[clave] = por_cancion.get(clave, 0) + 1
        pista_de.setdefault(clave, p)
        segundos += mixes.segundos_de(p)
        for i, (k, nombre) in enumerate(mixes.artistas_de(p)):
            if i == 0:
                prev = por_artista.get(k, [nombre, 0])
                prev[1] += 1
                por_artista[k] = prev
        d = e["fecha"].date()
        por_dia[d] = por_dia.get(d, 0) + 1
        por_mes[e["fecha"].month] = por_mes.get(e["fecha"].month, 0) + 1
        a = animo_de(f"{_titulo(p)} {_artista_visible(p)}")
        if a:
            animos[a] = animos.get(a, 0) + 1

    top_artistas = sorted(por_artista.values(), key=lambda x: (-x[1], x[0].lower()))[:5]
    cancion = None
    if por_cancion:
        c = sorted(por_cancion, key=lambda k: (-por_cancion[k], _titulo(pista_de[k]).lower()))[0]
        cancion = {"titulo": _titulo(pista_de[c]) or "Sin título", "artista": _artista_visible(pista_de[c]),
                   "veces": por_cancion[c], "miniatura": str(pista_de[c].get("miniatura") or "")}
    dia = None
    if por_dia:
        d = sorted(por_dia, key=lambda k: (-por_dia[k], k))[0]
        dia = {"fecha": d, "escuchas": por_dia[d], "texto": f"{d.day} de {MESES[d.month - 1]}"}
    mes = None
    if por_mes:
        m = sorted(por_mes, key=lambda k: (-por_mes[k], k))[0]
        mes = {"mes": m, "nombre": MESES[m - 1], "escuchas": por_mes[m]}
    animo = None
    clasificadas = sum(animos.values())
    if clasificadas >= 3 and len(escuchas) >= MINIMO_ESCUCHAS:
        a = sorted(animos, key=lambda k: (-animos[k], k))[0]
        animo = {"clave": a, "nombre": NOMBRES_ANIMO[a], "frase": FRASES_ANIMO[a],
                 "porcentaje": round(100 * animos[a] / clasificadas)}
    return {
        "anio": anio,
        "escuchas": len(escuchas),
        "minutos": round(segundos / 60),
        "canciones_distintas": len(por_cancion),
        "artistas_distintos": len(por_artista),
        "artista_top": ({"nombre": top_artistas[0][0], "veces": top_artistas[0][1]} if top_artistas else None),
        "top_artistas": [{"nombre": n, "veces": v} for n, v in top_artistas],
        "cancion_top": cancion,
        "animo": animo,
        "racha": mejor_racha(set(por_dia)),
        "dia_top": dia,
        "mes_top": mes,
        "hay_datos": len(escuchas) >= MINIMO_ESCUCHAS,
    }


def leer(coleccion, anio=None, ahora=None):
    """Lee las escuchas del año de la colección y calcula el resumen. Bloquea (pesa): llamarlo en segundo plano."""
    hoy = ahora or datetime.now()
    anio = int(anio or hoy.year)
    historial = mixes.leer_historial(coleccion, desde=datetime(anio, 1, 1), limite=200000)
    return calcular(historial, anio, hoy)


def texto_horas(minutos):
    """«1 234 min» o «20 h 34 min» legible."""
    minutos = int(minutos or 0)
    if minutos < 120:
        return f"{minutos} min"
    h, m = divmod(minutos, 60)
    return f"{h} h {m:02d} min" if m else f"{h} h"
