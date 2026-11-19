# -*- coding: utf-8 -*-
"""La tarjeta de tu semana (donadores): lo que escuchaste en los últimos 7 días, listo para una imagen (sin Qt).

Se apoya en `mixes.calcular_resumen` (el mismo cálculo de la pantalla «Tu resumen»), así las cifras de la tarjeta
y las de la pantalla siempre coinciden. Recibe el historial como lo da `mixes.leer_historial`."""

from datetime import datetime, timedelta

from . import mixes

MINIMO_ESCUCHAS = 3                 # con menos no hay semana que contar
DIAS_LETRA = ["L", "M", "X", "J", "V", "S", "D"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _titulo(p):
    return str((p or {}).get("titulo") or "").strip() or "Sin título"


def _artista(p):
    arts = mixes.artistas_de(p)
    return arts[0][1] if arts else str((p or {}).get("artista") or "").strip()


def texto_rango(desde, hasta):
    """«13 – 19 nov» (o «28 oct – 3 nov» si cruza de mes)."""
    if desde.month == hasta.month:
        return f"{desde.day} – {hasta.day} {MESES_CORTOS[hasta.month - 1]}"
    return f"{desde.day} {MESES_CORTOS[desde.month - 1]} – {hasta.day} {MESES_CORTOS[hasta.month - 1]}"


def calcular(historial, ahora=None):
    """El resumen de la semana para la tarjeta. `hay_datos` dice si alcanza para mostrarla."""
    hoy = ahora or datetime.now()
    r = mixes.calcular_resumen(historial, "semana", hoy)
    desde = r["desde"]
    por_dia = list(r["por_dia"])
    dias = []
    for i, minutos in enumerate(por_dia):
        d = desde + timedelta(days=i)
        dias.append({"letra": DIAS_LETRA[d.weekday()], "minutos": minutos, "fecha": d.date()})
    top = [{"titulo": _titulo(c["pista"]), "artista": _artista(c["pista"]), "veces": c["veces"],
            "miniatura": str(c["pista"].get("miniatura") or "")} for c in r["top_canciones"][:3]]
    artistas = [{"nombre": a["nombre"], "veces": a["veces"], "minutos": a["minutos"]}
                for a in r["top_artistas"][:3]]
    mejor_dia = None
    if any(por_dia):
        i = max(range(len(por_dia)), key=lambda k: (por_dia[k], -k))
        mejor_dia = dias[i]
    return {
        "desde": desde, "hasta": hoy, "rango": texto_rango(desde, hoy),
        "minutos": r["minutos"], "escuchas": r["escuchas"],
        "canciones_distintas": r["canciones_distintas"], "artistas_distintos": r["artistas_distintos"],
        "dias_con_musica": r["dias_con_musica"], "racha": r["racha_actual"],
        "cambio": r["cambio"],                       # % frente a la semana anterior (None si no hay con qué comparar)
        "franja": r["franja"], "hora_pico": r["hora_pico"],
        "dias": dias, "mejor_dia": mejor_dia,
        "top_canciones": top, "cancion_top": top[0] if top else None,
        "top_artistas": artistas, "artista_top": artistas[0] if artistas else None,
        "hay_datos": r["escuchas"] >= MINIMO_ESCUCHAS,
    }


def leer(coleccion, ahora=None):
    """Lee el historial de la colección y calcula la semana. Bloquea (pesa): llamarlo en segundo plano."""
    hoy = ahora or datetime.now()
    return calcular(mixes.leer_historial(coleccion, desde=hoy - timedelta(days=15), limite=60000), hoy)


def frase_cambio(cambio):
    """«+12 % que la semana pasada» o «» si no hay con qué comparar."""
    if cambio is None:
        return ""
    if cambio == 0:
        return "igual que la semana pasada"
    return f"{'+' if cambio > 0 else '−'}{abs(cambio)} % que la semana pasada"
