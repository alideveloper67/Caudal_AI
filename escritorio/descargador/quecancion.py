# -*- coding: utf-8 -*-
"""«¿Qué canción era?» (donadores): buscar en tu historial de escuchas por fecha y por texto (sin Qt).

Recibe el historial como lo da `mixes.leer_historial` (lista de {"pista", "fecha": datetime}). El texto se
compara sin tildes ni mayúsculas y TODAS sus palabras deben aparecer en el título, el artista o el álbum.
Además se entienden fechas escritas a mano dentro del texto («ayer», «semana pasada», «15/11», «noviembre»,
«el lunes»…): se quitan del texto y pasan a filtrar por fecha."""

import re
import unicodedata
from datetime import date, datetime, timedelta

MAXIMO = 300
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
NOMBRES_DIA_CORTO = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s/]", " ", t)).strip()


def _dia(d):
    return d.date() if isinstance(d, datetime) else d


def _inicio_semana(d):
    return d - timedelta(days=d.weekday())


def _mes_rango(anio, mes):
    ini = date(anio, mes, 1)
    fin = (date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)) - timedelta(days=1)
    return ini, fin


def interpretar_consulta(texto, ahora=None):
    """(texto_restante, desde, hasta) con `desde`/`hasta` como date o None. Quita del texto lo que fue una fecha."""
    hoy = _dia(ahora or datetime.now())
    t = " " + normalizar(texto) + " "
    desde = hasta = None

    def quitar(frase):
        nonlocal t
        t = t.replace(" " + frase + " ", "  ", 1)

    mes_ant = (hoy.year - 1, 12) if hoy.month == 1 else (hoy.year, hoy.month - 1)
    for frase, rango in (
        ("semana pasada", (_inicio_semana(hoy) - timedelta(days=7), _inicio_semana(hoy) - timedelta(days=1))),
        ("esta semana", (_inicio_semana(hoy), hoy)),
        ("mes pasado", _mes_rango(*mes_ant)),
        ("este mes", (date(hoy.year, hoy.month, 1), hoy)),
        ("anteayer", (hoy - timedelta(days=2),) * 2),
        ("ayer", (hoy - timedelta(days=1),) * 2),
        ("hoy", (hoy, hoy)),
    ):
        if " " + frase + " " in t:
            quitar(frase)
            desde, hasta = rango
            break
    if desde is None:
        m = re.search(r" (\d{1,2})/(\d{1,2})(?:/(\d{2,4}))? ", t)
        if m:
            dd, mm = int(m.group(1)), int(m.group(2))
            aa = int(m.group(3)) if m.group(3) else hoy.year
            if aa < 100:
                aa += 2000
            try:
                f = date(aa, mm, dd)
                if not m.group(3) and f > hoy:
                    f = date(aa - 1, mm, dd)          # «15/12» dicho en noviembre es el del año pasado
                desde = hasta = f
                t = t.replace(m.group(0), "  ", 1)
            except ValueError:
                pass
    if desde is None:
        for i, nombre in enumerate(DIAS):
            if " " + nombre + " " in t:
                atras = (hoy.weekday() - i) % 7 or 7        # el más reciente que ya pasó (o hace 7 días si es hoy)
                desde = hasta = hoy - timedelta(days=atras)
                quitar(nombre)
                break
    if desde is None:
        for i, nombre in enumerate(MESES):
            if " " + nombre + " " in t:
                anio = hoy.year if i + 1 <= hoy.month else hoy.year - 1
                desde, hasta = _mes_rango(anio, i + 1)
                quitar(nombre)
                break
    if desde is not None:
        t = re.sub(r"\b(el|la|los|las|del|de|en|que|cancion|canciones|tema|temas|escuche|puse)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip(), desde, hasta


def _texto_pista(p):
    arts = " ".join(str(a.get("nombre", "")) for a in (p.get("artistas") or []) if isinstance(a, dict))
    alb = p.get("album")
    alb = (alb.get("titulo") or alb.get("nombre") or "") if isinstance(alb, dict) else str(alb or "")
    return normalizar(f"{p.get('titulo', '')} {p.get('artista', '')} {arts} {alb}")


def buscar(historial, texto="", desde=None, hasta=None, limite=MAXIMO, ahora=None, entender_fechas=True):
    """Las escuchas que cumplen, de la más reciente a la más antigua.

    `desde`/`hasta` (date, inclusivos) se combinan con las fechas que se entiendan dentro del texto. Cada
    resultado: {"pista", "fecha", "veces"}: sale una fila por canción, con su escucha más reciente, y `veces` es
    cuántas veces sonó dentro del filtro."""
    if entender_fechas and texto:
        texto, d2, h2 = interpretar_consulta(texto, ahora)
        if d2 is not None:
            desde = d2 if desde is None else max(desde, d2)
            hasta = h2 if hasta is None else min(hasta, h2)
    palabras = normalizar(texto).split()
    vistas = {}
    for e in reversed(historial):                      # de lo más nuevo a lo más viejo
        f = e.get("fecha")
        p = e.get("pista") or {}
        if not isinstance(f, datetime) or not p.get("clave"):
            continue
        d = f.date()
        if (desde is not None and d < desde) or (hasta is not None and d > hasta):
            continue
        if palabras:
            hay = _texto_pista(p)
            if not all(w in hay for w in palabras):
                continue
        clave = str(p["clave"])
        if clave in vistas:
            vistas[clave]["veces"] += 1
        else:
            vistas[clave] = {"pista": p, "fecha": f, "veces": 1}
    filas = sorted(vistas.values(), key=lambda x: x["fecha"], reverse=True)
    return filas[:max(1, int(limite))]


def texto_fecha(f, ahora=None):
    """«hoy 21:40», «ayer 09:05», «jue 12 nov, 21:40»."""
    hoy = _dia(ahora or datetime.now())
    d = f.date()
    hora = f.strftime("%H:%M")
    if d == hoy:
        return f"hoy {hora}"
    if d == hoy - timedelta(days=1):
        return f"ayer {hora}"
    anio = f" {d.year}" if d.year != hoy.year else ""
    return f"{NOMBRES_DIA_CORTO[d.weekday()]} {d.day} {MESES[d.month - 1][:3]}{anio}, {hora}"
