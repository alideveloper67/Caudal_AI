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

from datetime import datetime, timedelta

from . import catalogo, mixes

CLAVE_SALTOS = "saltos"
CLAVE_DESCUBRE = "descubre_dia"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def _vid(p):
    return str((p or {}).get("video_id") or "")


def _artista(p):
    a = mixes.artistas_de(p)
    return a[0][0] if a else "?"


# ================================================================ gusto

class Gusto:
    def __init__(self, artistas=None, oidas=None, recientes=None, saltos=None, saltos_artista=None):
        self.artistas = artistas or {}
        self.oidas = oidas or set()
        self.recientes = recientes or set()
        self.saltos = saltos or {}
        self.saltos_artista = saltos_artista or {}

    @classmethod
    def desde(cls, historial, saltos_guardados=None, ahora=None):
        hoy = ahora or datetime.now()
        peso, oidas, recientes = {}, set(), set()
        for e in historial:
            p = e["pista"]
            v = _vid(p)
            if v:
                oidas.add(v)
                if (hoy - e["fecha"]).days < 4:
                    recientes.add(v)
            edad = max(0.0, (hoy - e["fecha"]).total_seconds() / 86400)
            w = 0.5 ** (edad / 30)
            for i, (clave, _n) in enumerate(mixes.artistas_de(p)):
                peso[clave] = peso.get(clave, 0) + (w if i == 0 else w * 0.5)
        maximo = max(peso.values(), default=0)
        artistas = {k: (v / maximo if maximo else 0.0) for k, v in peso.items()}
        s = saltos_guardados or {}
        saltos = {str(k): int(v) for k, v in (s.get("canciones") or {}).items() if int(v or 0) > 0}
        saltos_a = {str(k): int(v) for k, v in (s.get("artistas") or {}).items() if int(v or 0) > 0}
        return cls(artistas, oidas, recientes, saltos, saltos_a)

    def descartada(self, p):
        if self.saltos.get(_vid(p), 0) >= 2:
            return True
        for clave, _n in mixes.artistas_de(p):
            if self.saltos_artista.get(clave, 0) >= 4 and self.artistas.get(clave, 0) < 0.15:
                return True
        return False

    def afinidad(self, p):
        return max((self.artistas.get(c, 0) for c, _n in mixes.artistas_de(p)), default=0.0)


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
    col.guardar_estado(CLAVE_SALTOS, {"canciones": canciones, "artistas": artistas})


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


def gusto(col, ahora=None):
    hoy = ahora or datetime.now()
    historial = mixes.leer_historial(col, desde=hoy - timedelta(days=180), limite=8000)
    return Gusto.desde(historial, col.estado(CLAVE_SALTOS, None) or {}, ahora=hoy)


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


def limpiar_radio(pistas, g):
    sin_saltos = [p for p in pistas if not g.descartada(p)]
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


def similares(col, pista):
    """El mix «Similares a …» (se llama en segundo plano)."""
    v = _vid(pista)
    radio = _radio(v)
    rel = _relacionados(v)
    segundas = [_radio(_vid(p)) for p in radio[1:3]]
    pistas = puntuar_similares(pista, combinar([radio, rel, rel] + segundas), gusto(col))
    m = _mix(f"similares_{v}", f"Similares a «{pista.get('titulo') or ''}»",
             "Elegidas por cómo suena y por lo que escuchas", pistas, color="#22D3EE")
    if pista.get("miniatura"):
        m["miniatura"] = pista["miniatura"]
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
    g = Gusto.desde(historial, col.estado(CLAVE_SALTOS, None) or {}, ahora=hoy)
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


def maquina_del_tiempo_de(col, ahora=None):
    """«Vuelve en el tiempo»: tu mes pasado primero y después lo de hace meses."""
    hoy = ahora or datetime.now()
    historial = mixes.leer_historial(col, desde=hoy - timedelta(days=380))
    salida = maquina_del_tiempo(historial, ahora=hoy)
    mes = mes_pasado(historial, ahora=hoy)
    return ([mes] if mes else []) + salida
