# -*- coding: utf-8 -*-
"""Mezcla como un DJ: lógica pura (sin mpv ni ventanas), para poder probarla.

Dos usos:

* «Mezcla DJ» automática (Ajustes › Sonido): cada canción entra en la siguiente
  unos segundos antes de acabar, con cambio de graves.
* «Mezclador»: un set con pasos a medida. Un paso es la unión entre una
  canción y la siguiente:

      {"entra": 10, "dur": 8, "graves": True}

  - entra: cuántos segundos antes del final de la canción empieza a entrar la
    siguiente;
  - dur: cuánto dura el fundido (nunca más que `entra`);
  - graves: si hay cambio de graves (mientras la nueva entra se le quitan los
    graves; a mitad del fundido los graves pasan de una canción a la otra).

Los sets guardados viven en la colección (tabla `estado`), sin tocar la nube.
"""

import time

SEG_MIN = 4
SEG_MAX = 16
SEG_DEFECTO = 8
DUR_MIN_PASO = 2           # un fundido de menos de 2 s ya es un corte
ENTRA_MAX = 30
CORTE_GRAVES_HZ = 220      # por debajo de esto «viven» los graves
CLAVE_SETS = "mezclas_dj"
MAX_SETS = 60


def limitar_segundos(valor, defecto=SEG_DEFECTO):
    """Los segundos de la mezcla automática, siempre entre 4 y 16."""
    try:
        n = int(round(float(valor)))
    except (TypeError, ValueError):
        n = defecto
    return max(SEG_MIN, min(SEG_MAX, n))


def paso_por_defecto(segundos=SEG_DEFECTO, graves=True):
    s = limitar_segundos(segundos)
    return {"entra": s, "dur": s, "graves": bool(graves)}


def normalizar_paso(paso, duracion=0):
    """Deja un paso válido: números enteros, fundido ≤ entrada y entrada razonable
    para la canción (nunca más de la mitad de lo que dura)."""
    paso = dict(paso or {})
    base = paso_por_defecto()
    try:
        entra = int(round(float(paso.get("entra", base["entra"]))))
    except (TypeError, ValueError):
        entra = base["entra"]
    try:
        dur = int(round(float(paso.get("dur", base["dur"]))))
    except (TypeError, ValueError):
        dur = base["dur"]
    tope = ENTRA_MAX
    if duracion and float(duracion) > 0:
        tope = max(DUR_MIN_PASO, min(ENTRA_MAX, int(float(duracion) * 0.5)))
    entra = max(DUR_MIN_PASO, min(tope, entra))
    dur = max(DUR_MIN_PASO, min(SEG_MAX, dur, entra))
    graves = paso.get("graves", True)
    return {"entra": entra, "dur": dur, "graves": bool(graves)}


def configuracion_fundido(paso, mezcla_dj, segundos, graves, crossfade, duracion=0):
    """(disparo, dur, graves) del fundido que toca ahora.

    disparo = segundos antes del final en que empieza; dur = lo que dura.
    Manda el paso del set; si no hay, la mezcla DJ automática; si no, el fundido
    de siempre; si nada de eso está activo, (0, 0, False)."""
    if paso:
        p = normalizar_paso(paso, duracion)
        return p["entra"], p["dur"], p["graves"]
    if mezcla_dj:
        p = normalizar_paso({"entra": limitar_segundos(segundos),
                             "dur": limitar_segundos(segundos), "graves": graves}, duracion)
        return p["entra"], p["dur"], p["graves"]
    try:
        c = int(crossfade or 0)
    except (TypeError, ValueError):
        c = 0
    if c > 0:
        return c, c, False
    return 0, 0, False


def con_graves(cadena, corte=CORTE_GRAVES_HZ):
    """Añade al principio de una cadena de filtros de mpv (la de `cadena_filtros`,
    «lavfi=[a,b]» o vacía) un corte de graves."""
    corte_f = f"highpass=f={int(corte)}"
    if not cadena:
        return f"lavfi=[{corte_f}]"
    if cadena.startswith("lavfi=[") and cadena.endswith("]"):
        return f"lavfi=[{corte_f},{cadena[len('lavfi=['):]}"
    return f"lavfi=[{corte_f}]," + cadena


def graves_cortados(avance):
    """(saliente_sin_graves, entrante_sin_graves) según el avance del fundido (0 a 1).

    Al principio manda la que sale (la que entra llega sin graves); a la mitad se
    cambian los graves: la que sale los pierde y la que entra los gana."""
    if avance < 0.5:
        return False, True
    return True, False


def plan_de_set(pistas, pasos):
    """{clave de la canción: paso hacia la siguiente}. La última no tiene paso."""
    plan = {}
    for i, p in enumerate(pistas[:-1]):
        clave = str(p.get("clave") or p.get("video_id") or "")
        if not clave:
            continue
        paso = pasos[i] if i < len(pasos) else None
        plan[clave] = normalizar_paso(paso, p.get("duracion") or 0)
    return plan


def pasos_para(pistas, antiguos=None, segundos=SEG_DEFECTO, graves=True):
    """Un paso por cada unión, conservando los que ya había."""
    antiguos = list(antiguos or [])
    salida = []
    for i in range(max(0, len(pistas) - 1)):
        if i < len(antiguos) and antiguos[i]:
            salida.append(normalizar_paso(antiguos[i], pistas[i].get("duracion") or 0))
        else:
            salida.append(normalizar_paso(paso_por_defecto(segundos, graves),
                                          pistas[i].get("duracion") or 0))
    return salida


def duracion_del_set(pistas, pasos):
    """Segundos que dura el set entero (cada paso solapa lo que entra antes del final)."""
    total = 0.0
    for i, p in enumerate(pistas):
        d = float(p.get("duracion") or 0) or 210.0
        total += d
        if i < len(pistas) - 1:
            paso = normalizar_paso(pasos[i] if i < len(pasos) else None, d)
            total -= paso["entra"]
    return max(0.0, total)


def inicio_de_prueba(duracion, paso, antes=10):
    """Segundo en el que se coloca la canción para probar un paso: un poco antes
    de que empiece a entrar la siguiente."""
    p = normalizar_paso(paso, duracion)
    return max(0.0, float(duracion or 0) - p["entra"] - float(antes))


# ================================================================ sets guardados

def _pista_minima(p):
    quitar = {"archivo", "descarga_id", "tamano", "calidad", "fecha"}
    return {k: v for k, v in dict(p).items() if k not in quitar}


def leer_sets(col):
    datos = col.estado(CLAVE_SETS, None)
    return [s for s in (datos or []) if isinstance(s, dict) and s.get("nombre")]


def guardar_set(col, nombre, pistas, pasos):
    """Guarda (o reemplaza si ya existe el nombre) un set. Devuelve el set guardado."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("Ponle un nombre a la mezcla.")
    if len(pistas) < 2:
        raise ValueError("Una mezcla necesita al menos dos canciones.")
    s = {"nombre": nombre[:80], "pistas": [_pista_minima(p) for p in pistas],
         "pasos": pasos_para(pistas, pasos), "guardado": time.time()}
    sets = [x for x in leer_sets(col) if x["nombre"].lower() != nombre.lower()]
    sets.insert(0, s)
    col.guardar_estado(CLAVE_SETS, sets[:MAX_SETS])
    return s


def borrar_set(col, nombre):
    sets = [x for x in leer_sets(col) if x["nombre"].lower() != (nombre or "").strip().lower()]
    col.guardar_estado(CLAVE_SETS, sets)


def nombre_libre(col, base="Mi mezcla"):
    usados = {s["nombre"].lower() for s in leer_sets(col)}
    n = 1
    while f"{base} n.º {n}".lower() in usados:
        n += 1
    return f"{base} n.º {n}"
