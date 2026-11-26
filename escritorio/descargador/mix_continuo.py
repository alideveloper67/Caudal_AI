# -*- coding: utf-8 -*-
"""Qué canciones siguen solas cuando se acaba lo que pusiste («Mix de …»), según la ficha elegida.

  * todo: la radio de siempre (parecidas + lo que escuchas);
  * populares: lo más escuchado del artista que suena y de los artistas de esa radio;
  * descubrir: las de la radio que nunca has escuchado ni marcado.

Solo hay fichas que se pueden cumplir: el catálogo no dice cuántas veces se oye cada canción de una
radio, así que no existe una ficha de «poco conocidas».
"""

from concurrent.futures import ThreadPoolExecutor

TIPOS = (("todo", "Todo"), ("populares", "Populares"), ("descubrir", "Descubrir"))


def valido(tipo):
    return tipo if any(t == tipo for t, _n in TIPOS) else "todo"


def _ids_artistas(pistas):
    salida = []
    for p in pistas:
        for a in p.get("artistas") or []:
            i = a.get("id")
            if i and i not in salida:
                salida.append(i)
    return salida


def _populares_de(catalogo, ident, n=8):
    """Las primeras canciones de la página del artista (vienen de más a menos escuchada)."""
    try:
        datos = catalogo.artista(ident)
    except Exception:  # noqa: BLE001 - un artista que no carga no estropea el resto
        return []
    for s in datos.get("secciones") or []:
        pistas = [e for e in s.get("elementos") or []
                  if e.get("tipo") == "pista" and e.get("video_id") and not e.get("es_video")]
        if len(pistas) >= 3:
            return pistas[:n]
    return []


def intercalar(grupos):
    """Una de cada grupo por vuelta, sin repetir canción."""
    salida, vistas = [], set()
    for i in range(max((len(g) for g in grupos), default=0)):
        for g in grupos:
            if i < len(g):
                v = g[i].get("video_id")
                if v and v not in vistas:
                    vistas.add(v)
                    salida.append(g[i])
    return salida


def populares(catalogo, pista, base, artistas=5):
    ids = _ids_artistas([pista] + list(base))[:artistas]
    if not ids:
        return []
    with ThreadPoolExecutor(max_workers=3) as grupo:
        return intercalar(list(grupo.map(lambda i: _populares_de(catalogo, i), ids)))


def sin_escuchar(pistas, claves):
    return [p for p in pistas if p.get("clave") not in claves]


def _escuchadas(col):
    con = col.con
    claves = {f["clave"] for f in con.execute("SELECT DISTINCT clave FROM reproducciones")}
    claves |= {f["clave"] for f in con.execute("SELECT clave FROM me_gusta")}
    return claves


def candidatas(col, pista, tipo="todo"):
    """{"pistas": [...]} como `recomendador.radio_inteligente`. Va en segundo plano (red y base)."""
    from . import catalogo, recomendador
    tipo = valido(tipo)
    if tipo == "populares":
        base = [p for p in catalogo.radio(pista.get("video_id"), limite=50).get("pistas") or []]
        pistas = populares(catalogo, pista, base)
        return {"pistas": [p for p in pistas if p.get("video_id") != pista.get("video_id")]}
    datos = recomendador.radio_inteligente(col, pista)
    if tipo == "descubrir":
        copiar = getattr(col, "copia_de_lectura", None)
        if copiar is None:
            claves = _escuchadas(col)
        else:
            with copiar() as c:
                claves = _escuchadas(c)
        # la radio ordenada por gustos deja fuera lo menos conocido: se añade la radio tal cual
        crudas = [p for p in catalogo.radio(pista.get("video_id"), limite=50).get("pistas") or []]
        juntas, vistas = [], {pista.get("video_id")}
        for p in list(datos.get("pistas") or []) + crudas:
            v = p.get("video_id")
            if v and v not in vistas and p.get("tipo", "pista") == "pista":
                vistas.add(v)
                juntas.append(p)
        datos = {**datos, "pistas": sin_escuchar(juntas, claves)}
    return datos
