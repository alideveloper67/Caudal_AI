# -*- coding: utf-8 -*-
"""Tus mixes diarios y tu resumen de escuchas.

Todo sale de la tabla `reproducciones` de la coleccion (lo que de verdad
escuchaste). La logica pesada es pura —recibe una lista de escuchas— para
poder probarla sin base ni red; leer la coleccion o pedir la radio a YouTube
Music es una capa fina por encima. Es la misma logica que la app movil
(app/lib/nucleo/mixes.dart), para que ambos den mixes y resumenes parecidos.

Una escucha es un dict: {"pista": {...}, "fecha": datetime, "contexto": {...}|None}.
"""

import json
import math
import random
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

CLAVE_CACHE = "mixes_del_dia"

# un color por mix (como los de Spotify)
COLORES = ["#22D3EE", "#FF5C8A", "#FFB443", "#7C5CFF", "#2BD576", "#FF7A45"]

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

PERIODOS = {
    # clave: (dias, etiqueta, nombre, rango)
    "semana": (7, "Semana", "tu semana", "los últimos 7 días"),
    "mes": (30, "Mes", "tu mes", "los últimos 30 días"),
    "anio": (365, "Año", "tu año", "los últimos 12 meses"),
}


# ============================================================ historial

def escucha(pista, fecha, contexto=None):
    if not isinstance(fecha, datetime):
        fecha = datetime.fromtimestamp(float(fecha))
    return {"pista": pista, "fecha": fecha, "contexto": contexto}


def segundos_de(pista):
    """Lo que cuenta una escucha: sin duracion se supone una cancion normal, y
    los videos larguisimos (sesiones de una hora) se cortan a 15 min."""
    try:
        n = int(float((pista or {}).get("duracion") or 0))
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return 210
    return min(n, 900)


_SEPARADORES = re.compile(r",|&| feat\.? | ft\.? ", re.IGNORECASE)


def artistas_de(pista):
    """[(clave, nombre)] de una pista: por id si lo hay, si no por el nombre."""
    salida, vistos = [], set()

    def poner(ident, nombre):
        nombre = (nombre or "").strip()
        if not nombre:
            return
        ident = str(ident or "").strip()
        clave = f"id:{ident}" if ident else f"n:{nombre.lower()}"
        if clave not in vistos:
            vistos.add(clave)
            salida.append((clave, nombre))

    for a in (pista or {}).get("artistas") or []:
        if isinstance(a, dict):
            poner(a.get("id"), a.get("nombre"))
    if not salida:
        for n in _SEPARADORES.split((pista or {}).get("artista") or ""):
            poner("", n)
    return salida


def _clave(e):
    return str((e["pista"] or {}).get("clave") or "")


def _id(p):
    return str(p.get("video_id") or p.get("clave") or "")


def clave_dia(f):
    return f"{f.year}-{f.month:02d}-{f.day:02d}"


def _dia(f):
    return datetime(f.year, f.month, f.day)


def leer_historial(col, desde=None, limite=40000):
    """Las escuchas de la coleccion en orden cronologico (la mas vieja primero)."""
    t0 = desde.timestamp() if isinstance(desde, datetime) else float(desde or 0)
    filas = col.con.execute(
        "SELECT clave, fecha, contexto FROM reproducciones WHERE fecha >= ? "
        "ORDER BY fecha DESC, id DESC LIMIT ?", (t0, int(limite))).fetchall()
    if not filas:
        return []
    claves = list({f["clave"] for f in filas})
    pistas = {}
    en_linea = [c for c in claves if not c.startswith("local:")]
    for i in range(0, len(en_linea), 500):
        trozo = en_linea[i:i + 500]
        marcas = ",".join("?" * len(trozo))
        for f in col.con.execute(f"SELECT clave, datos FROM pistas WHERE clave IN ({marcas})",
                                 trozo):
            try:
                pistas[f["clave"]] = json.loads(f["datos"])
            except ValueError:
                pass
    for c in claves:
        if c.startswith("local:"):
            p = col.pista(c)
            if p:
                pistas[c] = p
    salida = []
    for f in reversed(filas):
        p = pistas.get(f["clave"])
        if not p or f["fecha"] is None:
            continue
        contexto = None
        if f["contexto"]:
            try:
                d = json.loads(f["contexto"])
                contexto = d if isinstance(d, dict) else None
            except ValueError:
                pass
        salida.append(escucha(p, float(f["fecha"]), contexto))
    return salida


# ============================================================ mixes

class GrupoMix:
    """Artistas que sueles escuchar juntos: la semilla de un mix."""

    def __init__(self, artistas):
        self.artistas = list(artistas)
        self.nombres = {}
        self.pistas = []
        self.estilo = None
        self.peso = 0.0


def agrupar(historial, ahora=None, maximo=6):
    """Hasta `maximo` grupos de artistas. Dos artistas van juntos si suenan en
    la misma sesion (o cantan juntos): asi un mix queda «de un estilo» sin
    necesitar el genero de cada cancion."""
    if not historial or maximo <= 0:
        return []
    hoy = ahora or datetime.now()
    orden = sorted(historial, key=lambda e: e["fecha"])
    peso, nombres, sesiones, juntos = {}, {}, {}, {}
    peso_pista, pistas = {}, {}

    def sumar_juntos(a, b, v):
        if a == b:
            return
        juntos.setdefault(a, {})[b] = juntos.get(a, {}).get(b, 0) + v
        juntos.setdefault(b, {})[a] = juntos.get(b, {}).get(a, 0) + v

    sesion = []
    ultima = None

    def cerrar():
        for a in sesion:
            sesiones[a] = sesiones.get(a, 0) + 1
        for i in range(len(sesion)):
            for j in range(i + 1, len(sesion)):
                sumar_juntos(sesion[i], sesion[j], 1)
        sesion.clear()

    for e in orden:
        arts = artistas_de(e["pista"])
        clave = _clave(e)
        if not arts or not clave:
            continue
        if ultima is not None and (e["fecha"] - ultima).total_seconds() > 45 * 60:
            cerrar()
        ultima = e["fecha"]
        # lo reciente pesa mas: tu gusto de hoy manda sobre el de hace meses
        edad = (hoy - e["fecha"]).total_seconds() / 86400.0
        w = 0.5 ** (max(0.0, edad) / 30.0)
        for i, (a, nombre) in enumerate(arts):
            peso[a] = peso.get(a, 0.0) + (w if i == 0 else w * 0.5)
            nombres.setdefault(a, nombre)
            if i == 0 and a not in sesion:
                sesion.append(a)
        for i in range(len(arts)):
            for j in range(i + 1, len(arts)):
                sumar_juntos(arts[i][0], arts[j][0], 2)
        peso_pista[clave] = peso_pista.get(clave, 0.0) + w
        pistas[clave] = e["pista"]
    cerrar()
    if not peso:
        return []

    principales = sorted(peso, key=lambda a: -peso[a])[:40]
    grupos = []
    max_por_grupo = 6

    def afinidad(a, g):
        ja = juntos.get(a, {})
        co = sum(ja.get(b, 0) for b in g.artistas)
        ses = sum(sesiones.get(b, 1) for b in g.artistas)
        return co / math.sqrt(max(1, sesiones.get(a, 1)) * max(1, ses))

    for a in principales:
        mejor, mejor_af = None, 0.0
        for g in grupos:
            if len(g.artistas) >= max_por_grupo:
                continue
            af = afinidad(a, g)
            if af > mejor_af:
                mejor, mejor_af = g, af
        if mejor is not None and (mejor_af >= 0.35 or len(grupos) >= maximo):
            mejor.artistas.append(a)
        elif len(grupos) < maximo:
            grupos.append(GrupoMix([a]))

    # con poco historial todo cae en uno o dos grupos: se separan para que
    # haya al menos tres mixes si hay artistas para ello
    minimo = min(3, maximo)
    while len(grupos) < minimo:
        grandes = [g for g in grupos if len(g.artistas) > 1]
        if not grandes:
            break
        grande = max(grandes, key=lambda g: len(g.artistas))
        grupos.append(GrupoMix([grande.artistas.pop(1)]))

    grupo_de = {}
    for g in grupos:
        for a in g.artistas:
            grupo_de[a] = g
            g.nombres[a] = nombres.get(a, "")
            g.peso += peso.get(a, 0.0)
    # cada pista va al grupo de su primer artista que tenga grupo
    for clave in sorted(peso_pista, key=lambda c: -peso_pista[c]):
        p = pistas[clave]
        for a, _n in artistas_de(p):
            g = grupo_de.get(a)
            if g is not None:
                g.pistas.append(p)
                break

    # estilo: el genero o animo desde el que sono la mayor parte del grupo
    por_estilo, totales = {}, {}
    for e in orden:
        arts = artistas_de(e["pista"])
        g = grupo_de.get(arts[0][0]) if arts else None
        if g is None:
            continue
        totales[id(g)] = totales.get(id(g), 0) + 1
        ctx = e.get("contexto") or {}
        titulo = str(ctx.get("titulo") or "").strip()
        if ctx.get("tipo") == "genero" and titulo:
            m = por_estilo.setdefault(id(g), {})
            m[titulo] = m.get(titulo, 0) + 1
    usados = set()
    for g in grupos:
        m = por_estilo.get(id(g))
        if not m:
            continue
        top, veces = max(m.items(), key=lambda x: x[1])
        if veces >= 3 and veces / totales.get(id(g), 1) >= 0.4 and top not in usados:
            usados.add(top)
            g.estilo = top

    salida = [g for g in grupos if g.pistas]
    salida.sort(key=lambda g: -g.peso)
    return salida


def semillas(g, n=2):
    """Canciones desde las que se pide la radio: tus mas escuchadas del grupo,
    de artistas distintos si se puede."""
    salida, artistas = [], set()
    for pasada in (True, False):
        for p in g.pistas:
            vid = str(p.get("video_id") or "")
            if len(vid) != 11 or vid in salida:
                continue
            arts = artistas_de(p)
            a = arts[0][0] if arts else ""
            if pasada:
                if a in artistas:
                    continue
                artistas.add(a)
            salida.append(vid)
            if len(salida) == n:
                return salida
    return salida


def mezclar(propias, radios, largo=50, azar=None):
    """Una tuya, dos nuevas, y asi. Tus favoritas van mas al principio, pero sin
    repetir siempre el mismo orden."""
    r = azar or random.Random()
    vistas = set()

    def nueva(p):
        i = _id(p)
        if not i or i in vistas:
            return False
        vistas.add(i)
        return True

    tuyas = [p for p in propias[:25] if nueva(p)]
    cabeza, cola = tuyas[:8], tuyas[8:]
    r.shuffle(cabeza)
    r.shuffle(cola)
    mias = cabeza + cola

    otras = []
    colas = [list(l) for l in radios]
    quedan = True
    while quedan:
        quedan = False
        for l in colas:
            while l:
                p = l.pop(0)
                if nueva(p):
                    otras.append(p)
                    quedan = True
                    break
            if l:
                quedan = True

    salida, i, j = [], 0, 0
    while len(salida) < largo and (i < len(mias) or j < len(otras)):
        toca_mia = len(salida) % 3 == 0
        if (toca_mia and i < len(mias)) or j >= len(otras):
            salida.append(mias[i])
            i += 1
        else:
            salida.append(otras[j])
            j += 1
    return salida


def _hash(s):
    h = 0x811C9DC5
    for c in s.encode("utf-8"):
        h = ((h ^ c) * 0x01000193) & 0x7FFFFFFF
    return h


def nombre_mix(i, estilo=None):
    return f"Mix de {estilo.strip()}" if estilo and estilo.strip() else f"Mix diario {i + 1}"


def subtitulo_mix(nombres):
    if not nombres:
        return "Lo que más escuchas y más"
    return ", ".join(nombres[:3]) + " y más"


def para_guardar(p):
    fuera = {"archivo", "descarga_id", "tamano", "calidad", "fecha"}
    return {k: v for k, v in p.items() if k not in fuera and not str(k).startswith("_")}


def _elemento(g, i, pistas, dia, con_radio):
    nombres = [g.nombres.get(a, "") for a in g.artistas if g.nombres.get(a)]
    # portada en mosaico: una por artista distinto, luego lo que haya
    miniaturas, vistos = [], set()
    for p in g.pistas + pistas:
        m = p.get("miniatura") or ""
        arts = artistas_de(p)
        a = arts[0][0] if arts else ""
        if not m or m in miniaturas or a in vistos:
            continue
        vistos.add(a)
        miniaturas.append(m)
        if len(miniaturas) == 4:
            break
    for p in pistas:
        if len(miniaturas) >= 4:
            break
        m = p.get("miniatura") or ""
        if m and m not in miniaturas:
            miniaturas.append(m)
    segundos = sum(segundos_de(p) for p in pistas)
    return {
        "tipo": "mix",
        "id": f"mix_diario_{i + 1}",
        "titulo": nombre_mix(i, g.estilo),
        "subtitulo": subtitulo_mix(nombres),
        "miniatura": miniaturas[0] if miniaturas else "",
        "miniaturas": miniaturas,
        "artistas": nombres,
        "color": COLORES[i % len(COLORES)],
        "numero": i + 1,
        "estilo": g.estilo,
        "pistas": [para_guardar(p) for p in pistas],
        "total": len(pistas),
        "minutos": round(segundos / 60),
        "dia": dia,
        "con_radio": con_radio,
    }


def radio_catalogo(video_id):
    from . import catalogo
    return catalogo.radio(video_id, limite=40).get("pistas") or []


def construir(historial, radio=None, ahora=None, maximo=6, largo=50):
    """Arma los mixes. `radio(video_id)` trae la radio de una cancion; si falla
    (o es None), el mix sale solo con tus canciones."""
    hoy = ahora or datetime.now()
    grupos = agrupar(historial, ahora=hoy, maximo=maximo)
    if not grupos:
        return []
    dia = clave_dia(hoy)
    por_grupo = [semillas(g) for g in grupos]
    pedidas = list(dict.fromkeys(s for ss in por_grupo for s in ss))
    radios = {}
    if radio is not None and pedidas:
        def una(vid):
            try:
                return vid, list(radio(vid) or [])
            except Exception:  # noqa: BLE001 - sin red el mix sale con lo tuyo
                return vid, None
        with ThreadPoolExecutor(max_workers=min(6, len(pedidas))) as pool:
            for vid, r in pool.map(una, pedidas):
                radios[vid] = r

    # una cancion de radio va a un solo mix: que no se repitan entre ellos
    usadas = {_id(p) for g in grupos for p in g.pistas}
    salida = []
    for i, g in enumerate(grupos):
        de_radio = []
        con_radio = not por_grupo[i]
        for s in por_grupo[i]:
            r = radios.get(s)
            if r is None:
                continue
            con_radio = True
            de_radio.append([p for p in r if _id(p) not in usadas])
        azar = random.Random(_hash(f"{dia}|{i}|{g.artistas[0]}"))
        pistas = mezclar(g.pistas, de_radio, largo=largo, azar=azar)
        usadas.update(_id(p) for p in pistas)
        salida.append(_elemento(g, i, pistas, dia, con_radio))
    return salida


def guardados_de_hoy(col, ahora=None):
    """(mixes, completos) guardados hoy, o (None, False) si no hay de hoy."""
    dia = clave_dia(ahora or datetime.now())
    g = col.estado(CLAVE_CACHE)
    if isinstance(g, dict) and g.get("dia") == dia and isinstance(g.get("mixes"), list):
        return [m for m in g["mixes"] if isinstance(m, dict)], bool(g.get("completo"))
    return None, False


def guardar(col, mixes, ahora=None):
    """Guarda los mixes de hoy. Un armado sin radio no pisa uno con radio."""
    if not mixes:
        return
    completo = all(m.get("con_radio") for m in mixes)
    anteriores, _c = guardados_de_hoy(col, ahora)
    if not completo and anteriores and any(m.get("con_radio") for m in anteriores):
        return
    col.guardar_estado(CLAVE_CACHE, {"dia": clave_dia(ahora or datetime.now()),
                                     "completo": completo, "mixes": mixes})


def olvidar(col):
    col.guardar_estado(CLAVE_CACHE, None)


def historial_para_mixes(col, ahora=None):
    hoy = ahora or datetime.now()
    return leer_historial(col, desde=hoy - timedelta(days=90), limite=6000)


def del_dia(col, radio=radio_catalogo, ahora=None, maximo=6):
    """Los mixes de hoy: se arman una vez al dia y se guardan en la coleccion; si
    hoy no hubo internet para la radio, se reintenta la proxima vez."""
    anteriores, completos = guardados_de_hoy(col, ahora)
    if anteriores and completos:
        return anteriores
    mixes = construir(historial_para_mixes(col, ahora), radio=radio, ahora=ahora, maximo=maximo)
    if not mixes:
        return anteriores or []
    guardar(col, mixes, ahora)
    nuevos, _c = guardados_de_hoy(col, ahora)
    return nuevos or mixes


# ============================================================ resumen

def _orden_cancion(c):
    return (-c["veces"], -c["segundos"])


def calcular_resumen(historial, periodo="semana", ahora=None):
    """El resumen de un periodo (semana, mes o año) a partir del historial."""
    dias_periodo, etiqueta, nombre, rango = PERIODOS[periodo]
    hoy = ahora or datetime.now()
    inicio_hoy = _dia(hoy)
    desde = inicio_hoy - timedelta(days=dias_periodo - 1)
    antes_desde = desde - timedelta(days=dias_periodo)
    inicio_mes = datetime(hoy.year, hoy.month, 1)
    r = {
        "periodo": periodo, "etiqueta": etiqueta, "nombre": nombre, "rango": rango,
        "desde": desde, "hasta": hoy, "segundos": 0, "escuchas": 0,
        "por_hora": [0] * 24, "por_dia": [0] * dias_periodo, "nombre_mes": MESES[hoy.month - 1],
        "minutos_antes": 0, "racha_mas_larga": 0, "racha_actual": 0,
    }
    canciones, artistas, del_mes = {}, {}, {}
    artistas_antes, dias = set(), set()
    antes = 0
    for e in historial:
        f = e["fecha"]
        clave = _clave(e)
        if f > hoy or not clave:
            continue
        dias.add(clave_dia(f))
        seg = segundos_de(e["pista"])
        arts = artistas_de(e["pista"])
        if f < desde:
            artistas_antes.update(a for a, _n in arts)
            if f >= antes_desde:
                antes += seg
        if f >= inicio_mes:
            m = del_mes.setdefault(clave, {"pista": e["pista"], "veces": 0, "segundos": 0})
            m["veces"] += 1
            m["segundos"] += seg
        if f < desde:
            continue
        r["escuchas"] += 1
        r["segundos"] += seg
        c = canciones.setdefault(clave, {"pista": e["pista"], "veces": 0, "segundos": 0})
        c["veces"] += 1
        c["segundos"] += seg
        for i, (a, n) in enumerate(arts):
            p = artistas.setdefault(a, {"clave": a, "nombre": n, "miniatura": "",
                                        "id": a[3:] if a.startswith("id:") else "",
                                        "veces": 0, "segundos": 0})
            if not p["miniatura"]:
                p["miniatura"] = e["pista"].get("miniatura") or ""
            p["veces"] += 1
            # los minutos cuentan para el artista principal; los invitados suman la escucha
            if i == 0:
                p["segundos"] += seg
        r["por_hora"][f.hour] += seg
        d = (_dia(f) - desde).days
        if 0 <= d < dias_periodo:
            r["por_dia"][d] += seg

    minutos = lambda s: int(round(s / 60))  # noqa: E731
    r["minutos"] = minutos(r["segundos"])
    r["minutos_antes"] = minutos(antes)
    r["por_hora"] = [minutos(s) for s in r["por_hora"]]
    r["por_dia"] = [minutos(s) for s in r["por_dia"]]
    r["dias_con_musica"] = sum(1 for m in r["por_dia"] if m > 0)
    for lista in (canciones, artistas, del_mes):
        for x in lista.values():
            x["minutos"] = minutos(x["segundos"])
    r["top_canciones"] = sorted(canciones.values(), key=_orden_cancion)[:5]
    arts = sorted(artistas.values(), key=lambda a: (-a["segundos"], -a["veces"]))
    r["top_artistas"] = arts[:5]
    r["canciones_distintas"] = len(canciones)
    r["artistas_distintos"] = len(artistas)
    # sin historial previo todo seria «nuevo»
    r["descubrimientos"] = ([a for a in arts if a["clave"] not in artistas_antes][:3]
                            if artistas_antes else [])
    pico = max(range(24), key=lambda h: (r["por_hora"][h], -h))
    r["hora_pico"] = pico
    r["franja"] = ("madrugada" if pico < 6 else "mañana" if pico < 12
                   else "tarde" if pico < 19 else "noche")
    mes = sorted(del_mes.values(), key=_orden_cancion)
    r["cancion_del_mes"] = mes[0] if mes else None
    actual = 0
    for m in r["por_dia"]:
        actual = actual + 1 if m > 0 else 0
        r["racha_mas_larga"] = max(r["racha_mas_larga"], actual)
    # racha de hoy: dias seguidos hasta hoy (o hasta ayer, si hoy aun no)
    dia = inicio_hoy
    if clave_dia(dia) not in dias:
        dia -= timedelta(days=1)
    while clave_dia(dia) in dias:
        r["racha_actual"] += 1
        dia -= timedelta(days=1)
    r["vacio"] = r["escuchas"] == 0
    r["cambio"] = (None if r["minutos_antes"] == 0 else
                   int(round((r["minutos"] - r["minutos_antes"]) * 100 / r["minutos_antes"])))
    return r


def resumen(col, periodo="semana", ahora=None):
    return calcular_resumen(leer_historial(col), periodo, ahora)

