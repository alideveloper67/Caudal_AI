# -*- coding: utf-8 -*-
"""Emparejar miles de canciones de otra app con YouTube Music, sin congelar nada.

  * en lotes (50 por defecto) con pocas busquedas a la vez (4), para no
    provocar al buscador;
  * cada fallo de red se reintenta con esperas crecientes; «no hay resultados»
    no se reintenta;
  * despues de cada lote se avisa (para guardar lo encontrado y el punto donde
    se va): si se cierra Caudal, se sigue desde ahi;
  * sin topes de cantidad.

Tambien tiene la fusion de «me gusta» externos con los de Caudal, sin repetir.
"""

import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

CLAVE_PENDIENTE = "importacion_pendiente"
CLAVE_FUENTES = "fuentes_me_gusta"


def elegir(cancion, resultados):
    """De los resultados, el que mejor casa: el primero, salvo que otro case
    mucho mejor en duracion (igual que en la app movil)."""
    pistas = [r for r in resultados or [] if r and r.get("video_id")]
    if not pistas:
        return None
    dur = int(cancion.get("duracion") or 0)
    if dur <= 0:
        return pistas[0]
    mejor = min(pistas, key=lambda p: abs(int(p.get("duracion") or 0) - dur))
    dp = abs(int(pistas[0].get("duracion") or 0) - dur)
    dm = abs(int(mejor.get("duracion") or 0) - dur)
    return mejor if dp > 15 and dm + 10 < dp else pistas[0]


def resolver_una(cancion, buscar, reintentos=3, espera=1.0, dormir=time.sleep):
    """Busca una cancion. Devuelve la pista o None si de verdad no esta.
    `buscar(consulta)` puede lanzar excepciones de red: se reintenta."""
    consulta = (cancion.get("busqueda")
                or " ".join(x for x in (cancion.get("artista"), cancion.get("titulo")) if x)).strip()
    if not consulta:
        return None
    for intento in range(reintentos):
        try:
            return elegir(cancion, buscar(consulta))
        except Exception:  # noqa: BLE001 - red o limite del buscador: se espera y se repite
            if intento + 1 < reintentos:
                dormir(espera * (2 ** intento))
    return None


def emparejar(canciones, buscar_pista, *, desde=0, lote=50, hilos=4,
              al_avanzar=None, al_lote=None, cancelado=None):
    """Recorre `canciones[desde:]` de lote en lote.

    `buscar_pista(cancion) -> pista | None` (ya con sus reintentos).
    `al_lote(fin, pistas, no_encontradas)` tras cada lote, en orden.
    `al_avanzar(hechas, total)` tras cada cancion.
    Devuelve {'hechas', 'encontradas', 'no_encontradas', 'cancelado'}."""
    total = len(canciones)
    hechas = desde
    encontradas = 0
    faltan = []
    with ThreadPoolExecutor(max_workers=max(1, hilos)) as grupo:
        for inicio in range(desde, total, max(1, lote)):
            if cancelado and cancelado():
                return {"hechas": hechas, "encontradas": encontradas,
                        "no_encontradas": faltan, "cancelado": True}
            trozo = canciones[inicio:inicio + lote]
            futuros = [grupo.submit(buscar_pista, c) for c in trozo]
            pistas, sin = [], []
            for c, f in zip(trozo, futuros):
                try:
                    p = f.result()
                except Exception:  # noqa: BLE001
                    p = None
                if p:
                    pistas.append(p)
                else:
                    sin.append(nombre_de(c))
                hechas += 1
                if al_avanzar:
                    al_avanzar(hechas, total)
            encontradas += len(pistas)
            faltan += sin
            if al_lote:
                al_lote(inicio + len(trozo), pistas, sin)
    return {"hechas": hechas, "encontradas": encontradas, "no_encontradas": faltan,
            "cancelado": False}


def nombre_de(cancion):
    t = cancion.get("titulo") or ""
    a = cancion.get("artista") or ""
    return f"{a} - {t}" if a and t else (t or a or "Sin nombre")


def miles(n):
    """1240 -> «1 240» (como se escribe en espanol)."""
    return f"{int(n):,}".replace(",", " ")


def texto_avance(hechas, total):
    return f"{miles(hechas)} de {miles(total)}"


# ---------------------------------------------------------------- me gusta sin repetir

_ADORNOS = re.compile(
    r"[\(\[][^\)\]]*(official|oficial|video|vídeo|lyrics?|letra|audio|hd|hq|4k|mv|"
    r"visualizer|remaster(ed)?)[^\)\]]*[\)\]]", re.I)


def huella_cancion(titulo, artista=""):
    """«titulo|primer artista» sin tildes ni adornos: la misma cancion subida dos
    veces (con otro video) se reconoce igual."""
    def limpio(s):
        s = _ADORNOS.sub("", s or "")
        s = unicodedata.normalize("NFKD", s.lower())
        s = "".join(c for c in s if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+", " ", s).strip()
    primer = re.split(r",|&| feat\.? | ft\.? | x ", artista or "", maxsplit=1)[0]
    return f"{limpio(titulo)}|{limpio(primer)}"


def huella_pista(p):
    artista = p.get("artista") or ", ".join(a.get("nombre", "") for a in p.get("artistas") or [])
    return huella_cancion(p.get("titulo", ""), artista)


def separar_nuevas(pistas, claves_actuales, huellas_actuales):
    """(nuevas, repetidas): fuera las que ya estan (por clave o por huella) y las
    repetidas dentro de la misma tanda."""
    claves = set(claves_actuales)
    huellas = set(huellas_actuales)
    nuevas, repetidas = [], 0
    for p in pistas:
        clave = p.get("clave")
        h = huella_pista(p)
        if not clave or clave in claves or (h != "|" and h in huellas):
            repetidas += 1
            continue
        claves.add(clave)
        huellas.add(h)
        nuevas.append(p)
    return nuevas, repetidas


def anotar_fuente(col, servicio, enlace, titulo, anadidas, no_encontradas):
    """Recuerda de donde se trajeron me gusta, para «Volver a sincronizar»."""
    fuentes = [f for f in (col.estado(CLAVE_FUENTES, []) or [])
               if isinstance(f, dict) and f.get("enlace") != enlace]
    fuentes.insert(0, {"servicio": servicio, "enlace": enlace, "titulo": titulo,
                       "cuando": time.time(), "anadidas": anadidas,
                       "no_encontradas": no_encontradas})
    col.guardar_estado(CLAVE_FUENTES, fuentes[:12])
