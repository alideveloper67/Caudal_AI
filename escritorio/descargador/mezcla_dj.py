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


TIPOS = [("fundido", "Fundido"), ("graves", "Cambio de graves"), ("filtro", "Filtro"),
         ("eco", "Eco de salida"), ("corte", "Corte en el compás")]
CURVAS = [("suave", "Suave"), ("lineal", "Lineal"), ("corte", "Corte rápido")]
_TIPOS_VALIDOS = {t for t, _n in TIPOS}
_CURVAS_VALIDAS = {c for c, _n in CURVAS}
MAX_AJUSTE_TEMPO = 0.08    # hasta ±8 % de velocidad para igualar tempos
DURACION_CORTE = 0.5       # un «corte» dura medio segundo


def paso_por_defecto(segundos=SEG_DEFECTO, graves=True):
    s = limitar_segundos(segundos)
    return {"entra": s, "dur": s, "graves": bool(graves),
            "tipo": "graves" if graves else "fundido", "curva": "suave", "tempo": False}


def normalizar_paso(paso, duracion=0):
    """Deja un paso válido: números enteros, fundido ≤ entrada y entrada razonable
    para la canción (nunca más de la mitad de lo que dura).

    Los pasos guardados antes (solo entra, dur y graves) se leen igual: el tipo sale
    de «graves», la curva es la suave y no se iguala el tempo."""
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
    tipo = paso.get("tipo")
    if tipo not in _TIPOS_VALIDOS:
        tipo = "graves" if paso.get("graves", True) else "fundido"
    curva = paso.get("curva") if paso.get("curva") in _CURVAS_VALIDAS else "suave"
    return {"entra": entra, "dur": dur, "graves": tipo == "graves", "tipo": tipo,
            "curva": curva, "tempo": bool(paso.get("tempo", False))}


def configuracion_paso(paso, mezcla_dj, segundos, graves, crossfade, duracion=0):
    """El paso completo (dict) que toca ahora, o None si no hay mezcla ni fundido."""
    if paso:
        return normalizar_paso(paso, duracion)
    if mezcla_dj:
        return normalizar_paso(paso_por_defecto(limitar_segundos(segundos), graves), duracion)
    try:
        c = int(crossfade or 0)
    except (TypeError, ValueError):
        c = 0
    if c > 0:
        return {"entra": c, "dur": c, "graves": False, "tipo": "fundido", "curva": "suave",
                "tempo": False}
    return None


def configuracion_fundido(paso, mezcla_dj, segundos, graves, crossfade, duracion=0):
    """(disparo, dur, graves) del fundido que toca ahora.

    disparo = segundos antes del final en que empieza; dur = lo que dura.
    Manda el paso del set; si no hay, la mezcla DJ automática; si no, el fundido
    de siempre; si nada de eso está activo, (0, 0, False)."""
    p = configuracion_paso(paso, mezcla_dj, segundos, graves, crossfade, duracion)
    if p is None:
        return 0, 0, False
    return p["entra"], p["dur"], p["graves"]


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


def guardar_set(col, nombre, pistas, pasos, marcas=None):
    """Guarda (o reemplaza si ya existe el nombre) un set. Devuelve el set guardado."""
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("Ponle un nombre a la mezcla.")
    if len(pistas) < 2:
        raise ValueError("Una mezcla necesita al menos dos canciones.")
    s = {"nombre": nombre[:80], "pistas": [_pista_minima(p) for p in pistas],
         "pasos": pasos_para(pistas, pasos), "guardado": time.time(),
         "marcas": {k: normalizar_marcas(v) for k, v in (marcas or {}).items()
                    if not marcas_vacias(v)}}
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


# ================================================================ filtros y curvas del paso

def combinar_filtros(base, delante=(), detras=()):
    """Une partes de filtro de mpv a una cadena «lavfi=[a,b]» (o vacía)."""
    delante, detras = list(delante), list(detras)
    if not delante and not detras:
        return base or ""
    dentro = []
    resto = ""
    if base and base.startswith("lavfi=[") and base.endswith("]"):
        dentro = [base[len("lavfi=["):-1]]
    else:
        resto = base or ""
    cuerpo = ",".join(delante + dentro + detras)
    cadena = f"lavfi=[{cuerpo}]"
    return cadena + ("," + resto if resto else "")


def partes_transicion(tipo, avance):
    """(partes de la que sale, partes de la que entra) de filtros para este momento
    del fundido (avance de 0 a 1). Cambian por escalones para no sobrecargar el motor."""
    if tipo == "graves":
        s, e = graves_cortados(avance)
        corte = f"highpass=f={CORTE_GRAVES_HZ}"
        return ((corte,) if s else ()), ((corte,) if e else ())
    if tipo == "filtro":
        # la que sale se «cierra» (pasa-bajos) y la que entra se «abre» (pasa-altos)
        if avance < 0.2:
            sal = ()
        elif avance < 0.4:
            sal = ("lowpass=f=5000",)
        elif avance < 0.6:
            sal = ("lowpass=f=2200",)
        elif avance < 0.8:
            sal = ("lowpass=f=900",)
        else:
            sal = ("lowpass=f=400",)
        if avance < 0.3:
            ent = ("highpass=f=1800",)
        elif avance < 0.5:
            ent = ("highpass=f=800",)
        elif avance < 0.7:
            ent = ("highpass=f=300",)
        else:
            ent = ()
        return sal, ent
    if tipo == "eco":
        return (() if avance < 0.15 else ("aecho=0.8:0.7:380|760:0.45|0.3",)), ()
    return (), ()


def curva_volumenes(curva, avance):
    """(volumen de la que entra, volumen de la que sale), de 0 a 1."""
    a = max(0.0, min(1.0, avance))
    if curva == "lineal":
        return a, 1.0 - a
    if curva == "corte":
        return (max(0.0, min(1.0, (a - 0.45) / 0.15)),
                max(0.0, min(1.0, 1.0 - (a - 0.5) / 0.15)))
    import math
    return math.sin(a * math.pi / 2), math.cos(a * math.pi / 2)


def filtros_eq(eq):
    """Partes de filtro para un ecualizador de 3 bandas [graves, medios, agudos] en dB."""
    try:
        g, m, a = [max(-12.0, min(6.0, float(x))) for x in list(eq or [0, 0, 0])[:3]]
    except (TypeError, ValueError):
        return []
    partes = []
    if abs(g) >= 0.5:
        partes.append(f"bass=g={g:.1f}:f=110")
    if abs(m) >= 0.5:
        partes.append(f"equalizer=f=1000:t=o:w=1.5:g={m:.1f}")
    if abs(a) >= 0.5:
        partes.append(f"treble=g={a:.1f}:f=6000")
    return partes


# ================================================================ tempo y compatibilidad

def _bpm(a):
    try:
        return float((a or {}).get("bpm") or 0)
    except (TypeError, ValueError):
        return 0.0


def razon_tempo(bpm_sale, bpm_entra, maximo=MAX_AJUSTE_TEMPO):
    """Factor de velocidad para la que entra para ir al tempo de la que sale (se
    admite el doble o la mitad, habituales en el ritmo). None si pasaría del máximo."""
    if bpm_sale <= 0 or bpm_entra <= 0:
        return None
    r = bpm_sale / bpm_entra
    mejor = min((r, r * 2, r / 2), key=lambda x: abs(x - 1))
    if abs(mejor - 1) <= maximo:
        return mejor
    return None


def diferencia_tempo(bpm_a, bpm_b):
    """Diferencia relativa de tempo (0 = iguales), plegando dobles y mitades."""
    if bpm_a <= 0 or bpm_b <= 0:
        return None
    r = bpm_b / bpm_a
    return abs(min((r, r * 2, r / 2), key=lambda x: abs(x - 1)) - 1)


def compatibilidad(an_a, an_b):
    """Cómo encajan dos canciones: {"nivel": encaja|ajusta|choca|desconocido,
    "dif": diferencia relativa}. «Encaja» = ≤3 %; «ajusta» = se iguala con el
    estiramiento de tiempo (≤8 %); «choca» = más."""
    d = diferencia_tempo(_bpm(an_a), _bpm(an_b))
    if d is None:
        return {"nivel": "desconocido", "dif": None}
    if d <= 0.03:
        return {"nivel": "encaja", "dif": d}
    if d <= MAX_AJUSTE_TEMPO:
        return {"nivel": "ajusta", "dif": d}
    return {"nivel": "choca", "dif": d}


def _clave_de(p):
    return str(p.get("clave") or p.get("video_id") or "")


def ordenar_set(pistas, analisis):
    """Reordena para que el paso entre canciones sea suave: empieza por la más
    calmada y sigue siempre con la más parecida en tempo y energía (con una pizca
    de preferencia por ir subiendo). Las que no tienen análisis van al final, en
    su orden. `analisis` = {clave: dict}."""
    def an(p):
        return analisis.get(_clave_de(p)) or {}
    con = [p for p in pistas if _bpm(an(p)) > 0]
    sin = [p for p in pistas if _bpm(an(p)) <= 0]
    if len(con) < 2:
        return list(pistas)
    actual = min(con, key=lambda p: an(p).get("energia", 0.5))
    resto = [p for p in con if p is not actual]
    salida = [actual]
    while resto:
        a = an(actual)

        def costo(p, a=a):
            b = an(p)
            d = diferencia_tempo(_bpm(a), _bpm(b))
            d = 0.5 if d is None else d
            de = b.get("energia", 0.5) - a.get("energia", 0.5)
            return d * 4 + abs(de - 0.04) * 1.5
        actual = min(resto, key=costo)
        resto.remove(actual)
        salida.append(actual)
    return salida + sin


# ================================================================ compás

def _periodo(an):
    b = _bpm(an)
    return 60.0 / b if b > 0 else 0.0


def inicio_de_compas_hasta(t, an):
    """El inicio de compás más cercano a t sin pasarse (≤ t). Sin análisis, t."""
    p = _periodo(an)
    if p <= 0 or (an or {}).get("sin_fase"):
        return t
    uno = float((an or {}).get("uno") or (an or {}).get("fase") or 0.0)
    comp = p * 4
    k = int((t - uno) // comp)
    return uno + k * comp


def inicio_de_compas_desde(t, an):
    """El primer inicio de compás ≥ t. Sin análisis, t."""
    p = _periodo(an)
    if p <= 0 or (an or {}).get("sin_fase"):
        return t
    antes = inicio_de_compas_hasta(t, an)
    return antes if abs(antes - t) < 1e-6 else antes + p * 4


def entrada_alineada(minimo, an, duracion=0):
    """Segundo de la canción que entra en el que empieza a sonar, alineado con el
    compás: el primer inicio de compás ≥ `minimo` (el punto de entrada elegido o donde
    empieza la música)."""
    minimo = max(0.0, float(minimo or 0.0))
    t = inicio_de_compas_desde(minimo, an)
    if duracion and t > duracion * 0.6:
        t = inicio_de_compas_hasta(minimo, an)
    return max(0.0, t)


def disparo_alineado(t, an):
    """Momento (segundos de la canción que sale) en que empieza la transición: el
    inicio de compás anterior a `t`, para que los compases de las dos canciones
    coincidan. Sin análisis, t."""
    return max(0.0, inicio_de_compas_hasta(t, an))


# ================================================================ perfiles y mezcla automática

PERFILES = {
    # nombre: (etiqueta, compases de mezcla, tipo, curva, iguala el tempo)
    "suave": ("Suave", 4, "fundido", "suave", True),
    "club": ("Club", 2, "graves", "suave", True),
    "rapida": ("Rápida", 1, "corte", "corte", False),
}


def perfil_mezcla(nombre):
    return PERFILES.get(nombre) or PERFILES["suave"]


def pasos_automaticos(pistas, analisis, perfil="suave"):
    """Un paso por unión según el perfil: la duración se mide en compases cuando se
    conoce el tempo (si no, en segundos fijos), el tipo es el del perfil y si dos
    canciones chocan en tempo no se fuerza el estiramiento."""
    _et, compases, tipo, curva, iguala = perfil_mezcla(perfil)
    pasos = []
    for i in range(max(0, len(pistas) - 1)):
        a = analisis.get(_clave_de(pistas[i]), {})
        b = analisis.get(_clave_de(pistas[i + 1]), {})
        per = _periodo(a)
        seg = compases * 4 * per if per > 0 else {"suave": 12, "club": 8, "rapida": 4}.get(perfil, 8)
        seg = max(DUR_MIN_PASO, min(SEG_MAX, seg))
        comp = compatibilidad(a, b)
        t, tempo = tipo, iguala
        if comp["nivel"] == "choca":
            tempo = False
            if tipo == "graves":
                t = "filtro"       # con tempos distintos conviene tapar el cruce
        elif comp["nivel"] == "desconocido":
            tempo = False
        dur_pista = pistas[i].get("duracion") or 0
        pasos.append(normalizar_paso({"entra": int(round(seg)), "dur": int(round(seg)),
                                      "tipo": t, "curva": curva, "tempo": tempo}, dur_pista))
    return pasos


# ================================================================ marcas por canción

def normalizar_marcas(m, duracion=0):
    """{"entrada": s|None, "salida": s|None, "eq": [graves, medios, agudos]}."""
    m = dict(m or {})
    d = float(duracion or 0)

    def seg(v):
        if v is None:
            return None
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        if v < 0 or (d and v > d):
            return None
        return round(v, 2)
    entrada, salida = seg(m.get("entrada")), seg(m.get("salida"))
    if entrada is not None and salida is not None and salida <= entrada + 5:
        salida = None
    try:
        eq = [max(-12.0, min(6.0, float(x))) for x in list(m.get("eq") or [0, 0, 0])[:3]]
    except (TypeError, ValueError):
        eq = [0.0, 0.0, 0.0]
    while len(eq) < 3:
        eq.append(0.0)
    return {"entrada": entrada, "salida": salida, "eq": eq}


def marcas_vacias(m):
    m = normalizar_marcas(m)
    return m["entrada"] is None and m["salida"] is None and not any(abs(x) >= 0.5 for x in m["eq"])
