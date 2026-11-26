# -*- coding: utf-8 -*-
"""Recomendaciones que aprenden de ti (igual que app/lib/nucleo/recomendador.dart).

* «Canciones similares» a una canción.
* «Descubre para ti»: canciones que aún no has oído (se arma una vez al día).
* La radio automática sin lo que saltas ni lo que sonó estos días.
* «Máquina del tiempo»: lo que escuchabas hace un mes, tres, seis o un año.
* «Tu mes pasado»: lo más escuchado el mes calendario anterior (o los últimos
  30 días si ese mes casi no tiene datos), que se puede guardar como lista.

Señales: lo que escuchas (lo reciente pesa más), lo que saltas antes de 30 s
y la radio / los relacionados de YouTube Music de varias canciones a la vez.
"""

import random
import zlib
from datetime import datetime, timedelta

from . import catalogo, mixes
from . import generos as generos_mod

CLAVE_SALTOS = "saltos"
CLAVE_DESCUBRE = "descubre_dia"
CLAVE_GUSTOS = "gustos"          # copia local de los artistas favoritos de la cuenta
CLAVE_PARA_TI = "gustos_inicio"
CLAVE_PARECIDOS = "artistas_parecidos"
SEMILLAS_PARECIDOS = 8           # de cuántos de tus artistas se miran los parecidos
MAX_PARECIDOS = 20
TOPE_POR_SEMILLA = 4             # de un solo artista tuyo no salen más (salvo que otro también los señale)
ULTIMAS = 50                     # no se repite lo de las últimas ~50 reproducciones
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def _vid(p):
    return str((p or {}).get("video_id") or "")


def _artista(p):
    a = mixes.artistas_de(p)
    return a[0][0] if a else "?"


# ================================================================ gusto

class Gusto:
    def __init__(self, artistas=None, oidas=None, recientes=None, saltos=None, saltos_artista=None,
                 ultimas=None, saltados_hoy=None, gustos=None, gustados=None,
                 artistas_gustados=None, generos_artista=None):
        self.artistas = artistas or {}
        self.oidas = oidas or set()
        self.recientes = recientes or set()
        self.saltos = saltos or {}
        self.saltos_artista = saltos_artista or {}
        self.ultimas = ultimas or set()              # lo de las últimas ~50 reproducciones
        self.saltados_hoy = saltados_hoy or set()    # lo que se saltó hoy
        self.gustos = gustos or {}                   # clave de artista -> peso (artistas elegidos)
        self.gustados = gustados or set()            # canciones con me gusta
        self.artistas_gustados = artistas_gustados or {}   # artistas de lo que tiene me gusta
        self.generos_artista = generos_artista or {}  # clave de artista -> {género: veces}

    @classmethod
    def desde(cls, historial, saltos_guardados=None, ahora=None, gustos=None, me_gusta=None):
        hoy = ahora or datetime.now()
        s = saltos_guardados or {}
        saltos = {str(k): int(v) for k, v in (s.get("canciones") or {}).items() if int(v or 0) > 0}
        saltos_a = {str(k): int(v) for k, v in (s.get("artistas") or {}).items() if int(v or 0) > 0}
        peso, oidas, recientes, generos = {}, set(), set(), {}
        for e in historial:
            p = e["pista"]
            v = _vid(p)
            if v:
                oidas.add(v)
                if (hoy - e["fecha"]).days < 4:
                    recientes.add(v)
            edad = max(0.0, (hoy - e["fecha"]).total_seconds() / 86400)
            w = 0.5 ** (edad / 30)
            if v and v in saltos:
                w *= 0.4        # una escucha que acabó en salto pesa menos que una completa
            gen = generos_mod.genero_de(p)
            for i, (clave, _n) in enumerate(mixes.artistas_de(p)):
                peso[clave] = peso.get(clave, 0) + (w if i == 0 else w * 0.5)
                if gen:
                    d = generos.setdefault(clave, {})
                    d[gen] = d.get(gen, 0) + 1
        maximo = max(peso.values(), default=0)
        artistas = {k: (v / maximo if maximo else 0.0) for k, v in peso.items()}
        for clave, n in saltos_a.items():       # saltar antes de 30 s resta
            if clave in artistas:
                artistas[clave] = max(0.0, artistas[clave] - 0.08 * n)
        # lo de las últimas ~50 reproducciones
        orden = sorted((e for e in historial if _vid(e["pista"])), key=lambda e: e["fecha"])
        ultimas = {_vid(e["pista"]) for e in orden[-ULTIMAS:]}
        hoy_s = s.get("hoy") or {}
        saltados_hoy = set(hoy_s.get("vids") or []) if hoy_s.get("dia") == mixes.clave_dia(hoy) else set()
        pesos_gustos = {}
        for x in gustos or []:
            if isinstance(x, dict) and x.get("nombre"):
                for clave in claves_artista(x.get("id"), x.get("nombre")):
                    pesos_gustos[clave] = 1.0
        gustados, art_g = set(), {}
        for p in me_gusta or []:
            if _vid(p):
                gustados.add(_vid(p))
            gen = generos_mod.genero_de(p)
            for clave, _n in mixes.artistas_de(p):
                art_g[clave] = art_g.get(clave, 0) + 1
                if gen:
                    d = generos.setdefault(clave, {})
                    d[gen] = d.get(gen, 0) + 1
        return cls(artistas, oidas, recientes, saltos, saltos_a, ultimas, saltados_hoy,
                   pesos_gustos, gustados, art_g, generos)

    def descartada(self, p):
        if self.saltos.get(_vid(p), 0) >= 2:
            return True
        for clave, _n in mixes.artistas_de(p):
            if self.saltos_artista.get(clave, 0) >= 4 and self.artistas.get(clave, 0) < 0.15 \
                    and clave not in self.gustos:
                return True
        return False

    def bono_gusto(self, p):
        """1.0 si la canción es de un artista que elegiste como favorito."""
        return max((self.gustos.get(c, 0.0) for c, _n in mixes.artistas_de(p)), default=0.0)

    def afinidad(self, p):
        hist = max((self.artistas.get(c, 0) for c, _n in mixes.artistas_de(p)), default=0.0)
        return max(hist, 0.6 * self.bono_gusto(p))

    def me_gusta(self, p):
        """0..1: la canción tiene me gusta (1) o es de un artista con canciones que te gustan."""
        if _vid(p) in self.gustados:
            return 1.0
        n = max((self.artistas_gustados.get(c, 0) for c, _n in mixes.artistas_de(p)), default=0)
        return min(0.7, 0.25 * n)

    def genero_artista(self, p):
        for c, _n in mixes.artistas_de(p):
            d = self.generos_artista.get(c)
            if d:
                return max(d, key=lambda k: d[k])
        return None


def claves_artista(ident, nombre):
    nombre = str(nombre or "").strip()
    ident = str(ident or "").strip()
    salida = []
    if ident:
        salida.append(f"id:{ident}")
    if nombre:
        salida.append(f"n:{nombre.lower()}")
    return salida


# ================================================================ señales

def anotar_salto(col, pista):
    v = _vid(pista)
    if not v:
        return
    datos = col.estado(CLAVE_SALTOS, None) or {}
    canciones = dict(datos.get("canciones") or {})
    artistas = dict(datos.get("artistas") or {})
    canciones[v] = int(canciones.get(v, 0)) + 1
    a = mixes.artistas_de(pista)
    if a:
        artistas[a[0][0]] = int(artistas.get(a[0][0], 0)) + 1
    while len(canciones) > 400:
        canciones.pop(next(iter(canciones)))
    while len(artistas) > 300:
        artistas.pop(next(iter(artistas)))
    dia = mixes.clave_dia(datetime.now())
    hoy = datos.get("hoy") or {}
    vids = list(hoy.get("vids") or []) if hoy.get("dia") == dia else []
    if v not in vids:
        vids.append(v)
    col.guardar_estado(CLAVE_SALTOS, {"canciones": canciones, "artistas": artistas,
                                      "hoy": {"dia": dia, "vids": vids[-300:]}})


def perdonar(col, pista):
    """Si una canción saltada se escucha entera, se le quita un salto."""
    v = _vid(pista)
    datos = col.estado(CLAVE_SALTOS, None)
    if not v or not datos:
        return
    canciones = dict(datos.get("canciones") or {})
    n = int(canciones.get(v, 0))
    if n <= 0:
        return
    if n <= 1:
        canciones.pop(v, None)
    else:
        canciones[v] = n - 1
    col.guardar_estado(CLAVE_SALTOS, {**datos, "canciones": canciones})


def leer_gustos(col):
    """Los artistas favoritos elegidos (copia local): [{"nombre","id","portada"}]."""
    try:
        d = col.estado(CLAVE_GUSTOS, None) or {}
    except Exception:  # noqa: BLE001
        return []
    return [x for x in (d.get("lista") or []) if isinstance(x, dict) and x.get("nombre")]


def gusto(col, ahora=None):
    hoy = ahora or datetime.now()
    historial = mixes.leer_historial(col, desde=hoy - timedelta(days=180), limite=8000)
    try:
        try:
            me_gusta = col.lista_me_gusta(limite=400)     # solo los 400 primeros, no todos
        except TypeError:                                 # colecciones de prueba sin `limite`
            me_gusta = col.lista_me_gusta()[:400]
    except Exception:  # noqa: BLE001
        me_gusta = []
    return Gusto.desde(historial, col.estado(CLAVE_SALTOS, None) or {}, ahora=hoy,
                       gustos=leer_gustos(col), me_gusta=me_gusta)


# ================================================================ lógica pura

def combinar(listas):
    """[(pista, puntos)]: una canción que sale arriba en varias listas gana."""
    puntos, pistas = {}, {}
    for lista in listas:
        vistos = set()
        for i, p in enumerate(lista):
            v = _vid(p)
            if not v or v in vistos:
                continue
            vistos.add(v)
            puntos[v] = puntos.get(v, 0) + 1 / (i + 3)
            pistas.setdefault(v, p)
    return [(pistas[k], puntos[k]) for k in sorted(puntos, key=lambda k: -puntos[k])]


def diversificar(pistas, por_artista=2, largo=30):
    cuenta, salida, resto = {}, [], []
    for p in pistas:
        a = _artista(p)
        if cuenta.get(a, 0) >= por_artista:
            resto.append(p)
            continue
        cuenta[a] = cuenta.get(a, 0) + 1
        salida.append(p)
        if len(salida) >= largo:
            return salida
    for p in resto:
        if len(salida) >= largo:
            break
        salida.append(p)
    return salida


def puntuar_descubre(candidatas, g, largo=30):
    puntuadas = []
    for p, base in candidatas:
        if _vid(p) in g.oidas or g.descartada(p):
            continue
        if p.get("es_video") and not p.get("artista"):
            continue
        puntuadas.append((p, base * (1 + 0.6 * g.afinidad(p))))
    puntuadas.sort(key=lambda x: -x[1])
    conocidas = [p for p, _ in puntuadas if g.afinidad(p) > 0.05]
    nuevas = [p for p, _ in puntuadas if g.afinidad(p) <= 0.05]
    mezcla = []
    for i in range(max(len(conocidas), len(nuevas))):
        if i < len(nuevas):
            mezcla.append(nuevas[i])
        if i < len(conocidas):
            mezcla.append(conocidas[i])
    return diversificar(mezcla, 2, largo)


def puntuar_similares(semilla, candidatas, g, largo=30):
    propia = _vid(semilla)
    lista = [(p, b * (1 + 0.3 * g.afinidad(p))) for p, b in candidatas
             if _vid(p) != propia and not g.descartada(p)]
    lista.sort(key=lambda x: -x[1])
    return diversificar([p for p, _ in lista], 2, largo)


PESO_FUENTE = {"siguientes": 1.0, "relacionados": 0.8, "artista": 0.7, "parecidos": 0.6, "gustos": 0.45}
MAX_SEGUIDAS = 2           # nunca más de 2 seguidas del mismo artista
MAX_POR_ARTISTA = 6        # ni más de 6 del mismo artista en una misma tanda
DESCUBRIMIENTO = 0.2       # ~20 % de la cola: artistas nuevos afines


def separar_artistas(pistas, max_seguidas=MAX_SEGUIDAS):
    """Reordena lo mínimo para que no haya más de `max_seguidas` del mismo artista seguidas."""
    resto = list(pistas)
    salida = []
    while resto:
        elegido = None
        for i, p in enumerate(resto):
            a = _artista(p)
            ult = [_artista(x) for x in salida[-max_seguidas:]]
            if not (len(ult) == max_seguidas and all(u == a for u in ult)):
                elegido = i
                break
        salida.append(resto.pop(0 if elegido is None else elegido))
    return salida


def _generos_conocidos(semilla, candidatas, g):
    """{clave de artista: género} con lo que se deduce de todas las canciones a la vista."""
    cuentas = {}
    todas = list(candidatas) + ([semilla] if semilla else [])
    for p in todas:
        gen = generos_mod.genero_de(p)
        if not gen:
            continue
        for c, _n in mixes.artistas_de(p):
            d = cuentas.setdefault(c, {})
            d[gen] = d.get(gen, 0) + 1
    salida = {}
    for c, d in cuentas.items():
        salida[c] = max(d, key=lambda k: d[k])
    for c, d in g.generos_artista.items():
        salida.setdefault(c, max(d, key=lambda k: d[k]))
    return salida


def puntuar_cola(semilla, fuentes, g, largo=40, semilla_rng=0, descubrimiento=DESCUBRIMIENTO,
                 estricto=False):
    """Ordena las canciones candidatas para la cola/radio de `semilla`.

    fuentes: {nombre: [pistas]} (siguientes, relacionados, artista, parecidos, gustos).
    Combina: lo que sale arriba en varias fuentes, afinidad con tu historial, me gusta y
    artistas elegidos, mismo género/idioma/época, y deja fuera (o al final, si no queda otra
    opción y no es `estricto`) lo ya oído en las últimas ~50 reproducciones y lo saltado hoy.
    Determinista para una misma `semilla_rng`."""
    rng = random.Random(semilla_rng)
    propia = _vid(semilla) if semilla else ""
    base, pistas = {}, {}
    for nombre, lista in (fuentes or {}).items():
        peso = PESO_FUENTE.get(nombre, 0.5)
        vistos = set()
        for i, p in enumerate(lista or []):
            v = _vid(p)
            if not v or v in vistos:
                continue
            vistos.add(v)
            base[v] = base.get(v, 0) + peso / (i + 3)
            pistas.setdefault(v, p)
    if not base:
        return []
    tope = max(base.values())
    conocidos = _generos_conocidos(semilla, pistas.values(), g)
    gen_sem = generos_mod.genero_de(semilla, conocidos) if semilla else None
    if semilla and not gen_sem:
        gen_sem = g.genero_artista(semilla)
    idi_sem = generos_mod.idioma_de(semilla) if semilla else None
    ep_sem = generos_mod.epoca_de(semilla) if semilla else None
    artistas_sem = {c for c, _n in mixes.artistas_de(semilla)} if semilla else set()

    puntuadas, repetidas = [], []
    for v, p in pistas.items():
        if v == propia or g.descartada(p) or v in g.saltados_hoy:
            continue
        sc = base[v] / tope
        gen = generos_mod.genero_de(p, conocidos)
        sc *= generos_mod.compatibilidad(gen_sem, gen)
        sc *= generos_mod.compat_idioma(idi_sem, generos_mod.idioma_de(p))
        sc *= generos_mod.compat_epoca(ep_sem, generos_mod.epoca_de(p))
        aprecio = 1 + 0.5 * g.afinidad(p) + 0.6 * g.bono_gusto(p) + 0.5 * g.me_gusta(p)
        if artistas_sem & {c for c, _n in mixes.artistas_de(p)}:
            aprecio += 0.15                      # el mismo artista de lo que suena
        sc *= aprecio
        sc *= 0.5 ** g.saltos.get(v, 0)          # lo que ya se ha saltado antes, más abajo
        sc *= 1 + rng.uniform(-0.02, 0.02)       # desempate estable (misma semilla, mismo orden)
        entrada = (p, sc, gen)
        (repetidas if v in g.ultimas else puntuadas).append(entrada)
    puntuadas.sort(key=lambda x: -x[1])
    repetidas.sort(key=lambda x: -x[1])

    # descubrimiento: artistas que no conoces todavía pero de género afín
    def conocido(e):
        p, _sc, _gen = e
        return (g.afinidad(p) > 0.05 or g.bono_gusto(p) > 0
                or bool(artistas_sem & {c for c, _n in mixes.artistas_de(p)}))
    viejos = [e for e in puntuadas if conocido(e)]
    nuevos = [e for e in puntuadas if not conocido(e) and generos_mod.compatibilidad(gen_sem, e[2]) >= 0.6]
    resto_nuevos = [e for e in puntuadas if not conocido(e) and e not in nuevos]
    cada = max(2, round(1 / descubrimiento)) if descubrimiento > 0 else 0
    orden, iv, inu = [], 0, 0
    while (iv < len(viejos) or inu < len(nuevos)) and len(orden) < largo * 2:
        toca_nuevo = cada and (len(orden) + 1) % cada == 0
        if toca_nuevo and inu < len(nuevos):
            orden.append(nuevos[inu])
            inu += 1
        elif iv < len(viejos):
            orden.append(viejos[iv])
            iv += 1
        elif inu < len(nuevos):
            orden.append(nuevos[inu])
            inu += 1
    orden.extend(resto_nuevos)
    # tope por artista y reparto
    cuenta, salida = {}, []
    for p, _sc, _gen in orden:
        a = _artista(p)
        if cuenta.get(a, 0) >= MAX_POR_ARTISTA:
            continue
        cuenta[a] = cuenta.get(a, 0) + 1
        salida.append(p)
    if not estricto and len(salida) < min(largo, 12):
        for p, _sc, _gen in repetidas:       # lo ya oído, solo al final y si falta cola
            if len(salida) >= largo:
                break
            salida.append(p)
    return separar_artistas(salida[:largo])


def limpiar_radio(pistas, g):
    sin_saltos = [p for p in pistas if not g.descartada(p) and _vid(p) not in g.saltados_hoy]
    frescas = [p for p in sin_saltos if _vid(p) not in g.recientes]
    return frescas if len(frescas) >= 8 else sin_saltos


def semillas(historial, n=6, ahora=None):
    hoy = ahora or datetime.now()
    peso, artista = {}, {}
    for e in historial:
        v = _vid(e["pista"])
        if len(v) != 11:
            continue
        edad = max(0.0, (hoy - e["fecha"]).total_seconds() / 86400)
        peso[v] = peso.get(v, 0) + 0.5 ** (edad / 21)
        artista.setdefault(v, _artista(e["pista"]))
    salida, usados = [], set()
    for v in sorted(peso, key=lambda k: -peso[k]):
        if artista[v] in usados:
            continue
        usados.add(artista[v])
        salida.append(v)
        if len(salida) == n:
            break
    return salida


def maquina_del_tiempo(historial, ahora=None):
    hoy = ahora or datetime.now()
    salida = []
    for dias, titulo in ((365, "Hace un año"), (182, "Hace seis meses"), (91, "Hace tres meses"),
                         (30, "Hace un mes")):
        centro = hoy - timedelta(days=dias)
        cuenta, pistas = {}, {}
        for e in historial:
            clave = str((e["pista"] or {}).get("clave") or "")
            if not clave or abs((e["fecha"] - centro).days) > 7:
                continue
            cuenta[clave] = cuenta.get(clave, 0) + 1
            pistas.setdefault(clave, e["pista"])
        if len(pistas) < 5:
            continue
        lista = [pistas[k] for k in sorted(cuenta, key=lambda k: -cuenta[k])[:40]]
        salida.append(_mix(f"tiempo_{dias}", titulo,
                           f"Lo que sonaba a mediados de {MESES[centro.month - 1]} de {centro.year}",
                           lista, color="#FFB443"))
    return salida


MINIMO_MES_PASADO = 5      # canciones distintas para que el mes pasado «cuente»
MINIMO_LISTA = 3           # por debajo de esto no se ofrece nada


def _mas_escuchadas(historial, desde, hasta, largo=50):
    """Las canciones más escuchadas entre dos fechas (desde incluida, hasta no)."""
    cuenta, pistas, ultima = {}, {}, {}
    for e in historial:
        clave = str((e["pista"] or {}).get("clave") or "")
        if not clave or not (desde <= e["fecha"] < hasta):
            continue
        cuenta[clave] = cuenta.get(clave, 0) + 1
        pistas.setdefault(clave, e["pista"])
        ultima[clave] = max(ultima.get(clave, e["fecha"]), e["fecha"])
    orden = sorted(cuenta, key=lambda k: (-cuenta[k], -ultima[k].timestamp()))
    return [pistas[k] for k in orden[:largo]]


def mes_pasado(historial, ahora=None):
    """«Tu mes pasado»: lo más escuchado el mes calendario anterior. Si ese mes
    tiene muy pocas canciones, se usan los últimos 30 días. None si no hay casi nada.

    El mix lleva `nombre_lista` (p. ej. «Lo más escuchado en octubre») para guardarlo
    como lista con un toque."""
    hoy = ahora or datetime.now()
    este_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mes_anterior = (este_mes - timedelta(days=1)).replace(day=1)
    pistas = _mas_escuchadas(historial, mes_anterior, este_mes)
    if len(pistas) >= MINIMO_MES_PASADO:
        mes = MESES[mes_anterior.month - 1]
        titulo, nombre = "Tu mes pasado", f"Lo más escuchado en {mes}"
        sub = f"Lo que más sonó en {mes}"
    else:
        pistas = _mas_escuchadas(historial, hoy - timedelta(days=30), hoy + timedelta(seconds=1))
        if len(pistas) < MINIMO_LISTA:
            return None
        titulo, nombre = "Tu último mes", "Lo más escuchado en los últimos 30 días"
        sub = "Lo que más sonó en los últimos 30 días"
    m = _mix("mes_pasado", titulo, sub, pistas, color="#FF5C8A")
    m["nombre_lista"] = nombre
    return m


def nombre_lista_libre(col, base):
    """El nombre tal cual si está libre; si no, «… (2)», «… (3)»…"""
    usados = {l["nombre"].lower() for l in col.listas()}
    if base.lower() not in usados:
        return base
    n = 2
    while f"{base} ({n})".lower() in usados:
        n += 1
    return f"{base} ({n})"


def guardar_como_lista(col, mix):
    """Guarda un mix como lista de verdad. Devuelve (id de la lista, nombre)."""
    pistas = [p for p in (mix.get("pistas") or []) if p.get("clave")]
    if not pistas:
        raise ValueError("Este mix no tiene canciones que guardar.")
    nombre = nombre_lista_libre(col, mix.get("nombre_lista") or mix.get("titulo") or "Mi lista")
    lista_id = col.crear_lista(nombre, mix.get("subtitulo") or "")
    col.agregar_a_lista(lista_id, pistas)
    return lista_id, nombre


def _mix(ident, titulo, subtitulo, pistas, color="#7C5CFF"):
    miniaturas = []
    for p in pistas:
        m = p.get("miniatura") or ""
        if m and m not in miniaturas:
            miniaturas.append(m)
        if len(miniaturas) == 4:
            break
    return {
        "tipo": "mix", "id": ident, "titulo": titulo, "subtitulo": subtitulo,
        "miniatura": miniaturas[0] if miniaturas else "", "miniaturas": miniaturas,
        "color": color, "pistas": [mixes.para_guardar(p) for p in pistas], "total": len(pistas),
        "artistas": [], "minutos": round(sum(mixes.segundos_de(p) for p in pistas) / 60),
    }


# ================================================================ con red

def _radio(video_id):
    try:
        r = catalogo.radio(video_id, limite=40)
        return [p for p in r.get("pistas") or [] if p.get("tipo", "pista") == "pista"]
    except Exception:  # noqa: BLE001
        return []


def _relacionados(video_id):
    try:
        secciones = catalogo.relacionados(video_id)
    except Exception:  # noqa: BLE001
        return []
    salida = []
    for s in secciones or []:
        for e in s.get("elementos") or []:
            if e.get("tipo") == "pista":
                salida.append(e)
    return salida


_CACHE_ARTISTA = {}        # id de artista -> (hora, canciones, artistas parecidos)
_VIDA_CACHE = 3600


def _artista_datos(browse_id):
    """(canciones, artistas parecidos) de la página de un artista; con caché de una hora."""
    import time
    if not browse_id:
        return [], []
    hecho = _CACHE_ARTISTA.get(browse_id)
    if hecho and time.time() - hecho[0] < _VIDA_CACHE:
        return hecho[1], hecho[2]
    try:
        d = catalogo.artista(browse_id)
    except Exception:  # noqa: BLE001
        return [], []
    canciones, parecidos = [], []
    for sec in d.get("secciones") or []:
        for e in sec.get("elementos") or []:
            if e.get("tipo") == "pista":
                canciones.append(e)
            elif e.get("tipo") == "artista" and e.get("id") and e.get("id") != browse_id:
                parecidos.append(e)
    _CACHE_ARTISTA[browse_id] = (time.time(), canciones, parecidos)
    return canciones, parecidos


def _en_paralelo(tareas):
    """Ejecuta {nombre: (función, args)} a la vez; lo que falle queda vacío."""
    from concurrent.futures import ThreadPoolExecutor
    if not tareas:
        return {}
    salida = {}
    with ThreadPoolExecutor(max_workers=min(6, len(tareas))) as ex:
        futuros = {k: ex.submit(f, *a) for k, (f, a) in tareas.items()}
        for k, fut in futuros.items():
            try:
                salida[k] = fut.result(timeout=25)
            except Exception:  # noqa: BLE001
                salida[k] = None
    return salida


def fuentes_de(col, pista, g=None, radio_previo=None):
    """Junta las candidatas de varias fuentes para `pista` (con red). Lo que no llega, queda vacío."""
    v = _vid(pista)
    g = g or gusto(col)
    ids = [a.get("id") for a in (pista.get("artistas") or []) if isinstance(a, dict) and a.get("id")]
    tareas = {}
    if radio_previo is None:
        tareas["siguientes"] = (_radio, (v,))
    tareas["relacionados"] = (_relacionados, (v,))
    if ids:
        tareas["artista"] = (_artista_datos, (ids[0],))
    favs = [x for x in leer_gustos(col) if x.get("id")]
    rng = random.Random(zlib.crc32(v.encode()))
    elegidos = rng.sample(favs, min(2, len(favs))) if favs else []
    for i, x in enumerate(elegidos):
        tareas[f"gusto{i}"] = (_artista_datos, (x["id"],))
    r = _en_paralelo(tareas)
    siguientes = radio_previo if radio_previo is not None else (r.get("siguientes") or [])
    cancion_artista, parecidos = ([], [])
    if r.get("artista"):
        cancion_artista, parecidos = r["artista"]
    # canciones de un par de artistas relacionados (los de la página del artista)
    parecidas = []
    extra = {f"par{i}": (_artista_datos, (x["id"],)) for i, x in enumerate(parecidos[:2])}
    for res in _en_paralelo(extra).values():
        if res:
            parecidas.extend(res[0][:8])
    gustos_c = []
    for i in range(len(elegidos)):
        if r.get(f"gusto{i}"):
            gustos_c.extend(r[f"gusto{i}"][0][:8])
    return {"siguientes": siguientes, "relacionados": r.get("relacionados") or [],
            "artista": cancion_artista[:12], "parecidos": parecidas, "gustos": gustos_c}


def radio_inteligente(col, pista, largo=40):
    """Como `catalogo.radio`, pero con las canciones más parecidas primero: las «siguientes» de
    YouTube Music, otras del artista y de artistas relacionados, lo que escuchas y tus gustos.

    Devuelve {"pistas", "letras_id", "relacionados_id"} igual que `catalogo.radio`."""
    v = _vid(pista)
    crudo = catalogo.radio(v, limite=50)          # si esto falla, falla como antes
    base = [p for p in crudo.get("pistas") or [] if p.get("tipo", "pista") == "pista"]
    try:
        g = gusto(col)
        f = fuentes_de(col, pista, g, radio_previo=base)
        ordenadas = puntuar_cola(pista, f, g, largo=largo, semilla_rng=zlib.crc32(v.encode()))
    except Exception:  # noqa: BLE001
        ordenadas = []
    if len(ordenadas) < 5:
        ordenadas = base
    return {**crudo, "pistas": ordenadas}


def similares(col, pista):
    """El mix «Similares a …» (se llama en segundo plano)."""
    v = _vid(pista)
    g = gusto(col)
    f = fuentes_de(col, pista, g)
    segundas = [_radio(_vid(p)) for p in f["siguientes"][1:3]]
    f["siguientes"] = f["siguientes"] + [p for lista in segundas for p in lista[:10]]
    pistas = puntuar_cola(pista, f, g, largo=30, semilla_rng=zlib.crc32(v.encode()))
    m = _mix(f"similares_{v}", f"Similares a «{pista.get('titulo') or ''}»",
             "Elegidas por cómo suena y por lo que escuchas", pistas, color="#22D3EE")
    if pista.get("miniatura"):
        m["miniatura"] = pista["miniatura"]
    return m


def _tus_artistas(col):
    """[(id, nombre, peso)] de más a menos, y las claves de todos los que ya conoces.

    Cuenta lo que más suena (cada repetición pesa menos que la anterior), los me gusta y los elegidos."""
    peso, nombre, conocidos = {}, {}, set()

    def sumar(p, cuanto):
        for i, a in enumerate(p.get("artistas") or []):
            if not isinstance(a, dict):
                continue
            conocidos.update(claves_artista(a.get("id"), a.get("nombre")))
            if a.get("id"):
                peso[a["id"]] = peso.get(a["id"], 0.0) + (cuanto if i == 0 else cuanto * 0.5)
                nombre.setdefault(a["id"], a.get("nombre") or "")
    for k, p in enumerate(col.mas_escuchadas(120, 120)):
        sumar(p, 1.0 + 2.0 / (1 + k / 12))
    for p in col.lista_me_gusta(limite=150):
        sumar(p, 1.0)
    for p in col.escuchado_hace_poco(60):
        sumar(p, 0.6)
    for x in leer_gustos(col):
        conocidos.update(claves_artista(x.get("id"), x.get("nombre")))
        if x.get("id"):
            peso[x["id"]] = peso.get(x["id"], 0.0) + 4.0
            nombre.setdefault(x["id"], x.get("nombre") or "")
    for g in col.guardados("artista"):
        conocidos.update(claves_artista(g.get("id"), g.get("titulo")))
    # el mismo artista puede venir con dos fichas (la suya y la de un sello): cuenta como uno
    junto, ficha = {}, {}
    for i, n in sorted(peso.items(), key=lambda x: -x[1]):
        k = nombre[i].strip().lower()
        if k:
            junto[k] = junto.get(k, 0.0) + n
            ficha.setdefault(k, i)
    orden = sorted(junto.items(), key=lambda x: -x[1])
    return [(ficha[k], nombre[ficha[k]], n) for k, n in orden], conocidos


def artistas_parecidos(col, ahora=None, datos_de=None):
    """Artistas que aún no escuchas y se parecen a los que sí: cada uno dice a quién se parece.

    Sale de la página de tus artistas («A sus fans también les gusta»). Pesa más el que señalan varios de
    los tuyos y los que más escuchas. Se arma una vez al día (con red; sin red, lo último que se supo)."""
    dia = mixes.clave_dia(ahora or datetime.now())
    tuyos, conocidos = _tus_artistas(col)
    semillas = tuyos[:SEMILLAS_PARECIDOS]
    firma = [i for i, _n, _p in semillas]
    guardado = col.estado(CLAVE_PARECIDOS, None) or {}

    def frescos(lista):
        return [e for e in lista or [] if not conocidos & set(claves_artista(e.get("id"), e.get("titulo")))]
    if guardado.get("dia") == dia and guardado.get("lista"):
        return frescos(guardado["lista"])
    if not semillas:
        return []
    leer = datos_de or _artista_datos
    r = _en_paralelo({i: (leer, (i,)) for i in firma})
    maximo = semillas[0][2] or 1.0
    puntos, ficha, quien = {}, {}, {}
    for i, nombre, peso in semillas:
        for k, e in enumerate((r.get(i) or ([], []))[1]):
            clave = e.get("id")
            if not clave or not e.get("titulo") or conocidos & set(claves_artista(clave, e["titulo"])):
                continue
            # el primero de la lista de parecidos se parece más que el décimo
            puntos[clave] = puntos.get(clave, 0.0) + (0.35 + 0.65 * peso / maximo) / (1 + k * 0.12)
            ficha.setdefault(clave, e)
            quien.setdefault(clave, []).append(nombre)
    if not puntos:
        return frescos(guardado.get("lista"))
    salida, de_semilla = [], {}
    for clave in sorted(puntos, key=lambda c: -puntos[c]):
        s = quien[clave]
        if len(s) == 1:
            if de_semilla.get(s[0], 0) >= TOPE_POR_SEMILLA:
                continue
            de_semilla[s[0]] = de_semilla.get(s[0], 0) + 1
        e = ficha[clave]
        salida.append({"tipo": "artista", "id": clave, "titulo": e["titulo"], "miniatura": e.get("miniatura") or "",
                       "radio_id": e.get("radio_id") or "",
                       "subtitulo": "Parecido a " + (s[0] if len(s) == 1 else f"{s[0]} y {s[1]}")})
        if len(salida) >= MAX_PARECIDOS:
            break
    col.guardar_estado(CLAVE_PARECIDOS, {"dia": dia, "lista": salida})
    return salida


def sugerencias_gustos(col, ahora=None, largo=30):
    """«Porque te gustan…»: canciones de tus artistas favoritos y de artistas parecidos.
    Una vez al día; None si no elegiste artistas o no hay red."""
    hoy = ahora or datetime.now()
    dia = mixes.clave_dia(hoy)
    guardado = col.estado(CLAVE_PARA_TI, None) or {}
    favs = [x for x in leer_gustos(col) if x.get("id")]
    firma = sorted(x["id"] for x in favs)
    if guardado.get("dia") == dia and guardado.get("mix") and guardado.get("firma") == firma:
        return guardado["mix"]
    if not favs:
        return None
    rng = random.Random(zlib.crc32(f"{dia}{''.join(firma)}".encode()))
    elegidos = rng.sample(favs, min(5, len(favs)))
    r = _en_paralelo({x["id"]: (_artista_datos, (x["id"],)) for x in elegidos})
    propias, parecidos = [], []
    for x in elegidos:
        d = r.get(x["id"])
        if d:
            propias.append(d[0][:8])
            parecidos.extend(d[1][:2])
    por_artista = {}
    for x in parecidos[:4]:
        por_artista[x["id"]] = (_artista_datos, (x["id"],))
    r2 = _en_paralelo(por_artista)
    nuevas = [d[0][:6] for d in r2.values() if d]
    if not propias:
        return None
    g = gusto(col, ahora=hoy)
    fuentes = {"gustos": [p for lista in propias for p in lista],
               "parecidos": [p for lista in nuevas for p in lista]}
    pistas = puntuar_cola(None, fuentes, g, largo=largo, semilla_rng=zlib.crc32(dia.encode()),
                          estricto=True)
    if len(pistas) < 5:
        return None
    nombres = ", ".join(x["nombre"] for x in elegidos[:3])
    m = _mix("porque_te_gustan", "Porque te gustan tus artistas",
             f"{nombres} y otros parecidos", pistas, color="#7C5CFF")
    col.guardar_estado(CLAVE_PARA_TI, {"dia": dia, "firma": firma, "mix": m})
    return m


def descubrir(col, ahora=None):
    """«Descubre para ti»: una vez al día (None si aún no hay historial o red)."""
    hoy = ahora or datetime.now()
    dia = mixes.clave_dia(hoy)
    guardado = col.estado(CLAVE_DESCUBRE, None) or {}
    if guardado.get("dia") == dia and guardado.get("mix"):
        return guardado["mix"]
    historial = mixes.leer_historial(col, desde=hoy - timedelta(days=180), limite=8000)
    if len(historial) < 5:
        return None
    g = gusto(col, ahora=hoy)
    sem = semillas(historial, ahora=hoy)
    if not sem:
        return None
    listas = [_radio(v) for v in sem]
    if not any(listas):
        return None
    pistas = puntuar_descubre(combinar(listas), g)
    if len(pistas) < 5:
        return None
    m = _mix("descubre_para_ti", "Descubre para ti",
             "Canciones que aún no has oído, elegidas por lo que escuchas", pistas)
    col.guardar_estado(CLAVE_DESCUBRE, {"dia": dia, "mix": m})
    return m


_CACHE_TIEMPO = {}      # (base, día, escuchas de antes de hoy) -> resultado


def _huella_tiempo(col, hoy):
    """Lo que decide la máquina del tiempo de hoy: cuántas escuchas hay de antes de hoy (y en
    total, por si el mes pasado aún se rellena con los últimos 30 días). None si no se puede."""
    try:
        medianoche = hoy.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        f = col.con.execute("SELECT COUNT(*), SUM(fecha < ?) FROM reproducciones", (medianoche,)).fetchone()
        return (str(getattr(col, "archivo", id(col))), mixes.clave_dia(hoy), int(f[1] or 0)), int(f[0] or 0)
    except Exception:  # noqa: BLE001
        return None, 0


def maquina_del_tiempo_de(col, ahora=None):
    """«Vuelve en el tiempo»: tu mes pasado primero y después lo de hace meses.

    Lee hasta un año de escuchas: el resultado se guarda para el resto del día (solo depende
    de lo escuchado antes de hoy; si el mes pasado aún tira de los últimos 30 días, también
    se rehace al sumar escuchas de hoy)."""
    hoy = ahora or datetime.now()
    clave, total = _huella_tiempo(col, hoy)
    if clave is not None:
        guardado = _CACHE_TIEMPO.get(clave)
        if guardado is not None and (not guardado["usa_hoy"] or guardado["total"] == total):
            return list(guardado["valor"])
    historial = mixes.leer_historial(col, desde=hoy - timedelta(days=380))
    salida = maquina_del_tiempo(historial, ahora=hoy)
    mes = mes_pasado(historial, ahora=hoy)
    valor = ([mes] if mes else []) + salida
    if clave is not None:
        if len(_CACHE_TIEMPO) > 8:
            _CACHE_TIEMPO.clear()
        usa_hoy = mes is None or mes.get("titulo") == "Tu último mes"
        _CACHE_TIEMPO[clave] = {"valor": valor, "usa_hoy": usa_hoy, "total": total}
    return list(valor)


def maquina_del_tiempo_en_memoria(col, ahora=None):
    """El resultado de hoy si ya está calculado (sin tocar el historial), o None."""
    hoy = ahora or datetime.now()
    clave, total = _huella_tiempo(col, hoy)
    guardado = _CACHE_TIEMPO.get(clave) if clave is not None else None
    if guardado is not None and (not guardado["usa_hoy"] or guardado["total"] == total):
        return list(guardado["valor"])
    return None


# ================================================================ ánimo de una canción
# Igual que Rasgos.animoDe de la app (app/lib/nucleo/recomendador.dart): se deduce del título y del artista con
# palabras sueltas (con límite de palabra, así «solomillo» no es «solo») en español e inglés.
# Manda la tristeza: «Sin ti» es triste aunque hable de amor.
import re as _re

_L = "a-záéíóúñü"      # letras: el \b de Python no cuenta bien las vocales con tilde pegadas al borde


def _palabras(*palabras):
    return _re.compile(r"(?<![" + _L + r"])(?:" + "|".join(palabras) + r")(?![" + _L + r"])", _re.IGNORECASE)


_TRISTE = _palabras(
    "triste", "tristeza", r"llor\w*", "lágrimas", "lagrimas", "dolor", r"duele\w*", "soledad", "adiós", "adios",
    r"olvid\w*", "extraño", "extrano", "perdón", "perdon", "ausencia", r"herid\w*", "roto", "rota", "desamor",
    "despedida", "muerte", "nostalgia", "sad", r"cry\w*", "tears?", "lonely", "alone", r"heartbreak\w*", "broken",
    "goodbye", r"hurt\w*", r"miss(?:ing)? you", "without you", "sin ti", "pain", "sorry", "farewell",
    r"depress\w*", "grief", "memories")
_FIESTA = _palabras(
    "fiesta", r"baila\w*", "bailar", "perreo", "party", "dance", "dancing", r"goza\w*", "rumba", "prende", "booty",
    "twerk", "sandungueo", "energy", "energía", "summer", "verano", "bounce", "turn up", "pop off")
_ROMANTICA = _palabras(
    "amor", "love", "te quiero", "te amo", r"besos?", "beso", "corazón", "corazon", "heart", "mi vida", "cariño",
    r"enamorad\w*", "romance", r"romántic\w*", "forever", "eres mi", "contigo")


def animo_de(texto):
    """'triste', 'fiesta', 'romantica' o '' si el texto (título y artista) no lo dice."""
    t = str(texto or "")
    if _TRISTE.search(t):
        return "triste"
    if _FIESTA.search(t):
        return "fiesta"
    if _ROMANTICA.search(t):
        return "romantica"
    return ""
