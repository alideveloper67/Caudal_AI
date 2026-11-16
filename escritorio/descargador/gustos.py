# -*- coding: utf-8 -*-
"""Artistas favoritos de la cuenta (los que se eligen al crearla o en Ajustes).

Guarda en la nube (tabla perfiles: `gustos` y `gustos_elegidos`) y deja una copia local
en la colección, para que el recomendador los use sin red y para reintentar al volver.
Sin ventanas: lo de pantalla vive en ui/pantalla_gustos.py."""

import time

from . import nube

MAXIMO = 30
SUGERIDO = 3           # se sugiere elegir al menos estos
CLAVE = "gustos"       # misma clave que recomendador.CLAVE_GUSTOS

# Artistas populares para empezar (región de Caudal: Perú y Latinoamérica, más lo global).
# Se buscan en el catálogo para traer su foto y su id; si falla, se muestran igual por nombre.
POPULARES = {
    "PE": ["Grupo 5", "Corazón Serrano", "Marisol", "Armonía 10", "Agua Marina", "Eva Ayllón",
           "Pedro Suárez-Vértiz", "Bad Bunny", "Karol G", "Feid", "Peso Pluma", "Shakira",
           "Daddy Yankee", "J Balvin", "Maná", "Soda Stereo", "Los Ángeles Azules", "Romeo Santos",
           "Marc Anthony", "Luis Miguel", "Taylor Swift", "The Weeknd", "Coldplay", "Dua Lipa"],
    "GLOBAL": ["Bad Bunny", "Karol G", "Feid", "Peso Pluma", "Shakira", "Daddy Yankee", "J Balvin",
               "Maná", "Soda Stereo", "Los Ángeles Azules", "Romeo Santos", "Marc Anthony",
               "Luis Miguel", "Juanes", "Ozuna", "Maluma", "Taylor Swift", "The Weeknd", "Coldplay",
               "Dua Lipa", "Ed Sheeran", "Billie Eilish", "Imagine Dragons", "Queen"],
}


def limpiar(lista):
    """Hasta 30 artistas {"nombre","id","portada"}, sin repetidos y sin basura."""
    salida, vistos = [], set()
    for x in lista or []:
        if not isinstance(x, dict):
            continue
        nombre = str(x.get("nombre") or "").strip()[:120]
        if not nombre:
            continue
        clave = str(x.get("id") or "").strip() or nombre.lower()
        if clave in vistos or nombre.lower() in vistos:
            continue
        vistos.update({clave, nombre.lower()})
        salida.append({"nombre": nombre, "id": str(x.get("id") or "").strip(),
                       "portada": str(x.get("portada") or "").strip()})
        if len(salida) >= MAXIMO:
            break
    return salida


def artista_de_elemento(e):
    """Un resultado de búsqueda de artistas del catálogo -> {"nombre","id","portada"}."""
    return {"nombre": e.get("titulo") or e.get("nombre") or "", "id": e.get("id") or "",
            "portada": e.get("miniatura") or e.get("portada") or ""}


def populares(region="PE"):
    return list(POPULARES.get(str(region or "").upper(), POPULARES["GLOBAL"]))


def resolver_popular(nombre):
    """Busca un artista por nombre en el catálogo: {"nombre","id","portada"} o solo el nombre."""
    from . import catalogo
    try:
        for e in catalogo.buscar(nombre, "artistas", 3):
            if e.get("tipo") == "artista" and e.get("id"):
                a = artista_de_elemento(e)
                a["nombre"] = a["nombre"] or nombre
                return a
    except Exception:  # noqa: BLE001
        pass
    return {"nombre": nombre, "id": "", "portada": ""}


class Gustos:
    """Los gustos de una cuenta. Las llamadas con red bloquean: úsalas en segundo plano."""

    def __init__(self, sesion, coleccion):
        self.sesion = sesion
        self.col = coleccion

    # ---- copia local
    def local(self):
        d = self.col.estado(CLAVE, None) or {}
        return {"lista": limpiar(d.get("lista")), "elegidos": bool(d.get("elegidos")),
                "pendiente": bool(d.get("pendiente"))}

    def _guardar_local(self, lista, elegidos, pendiente):
        self.col.guardar_estado(CLAVE, {"lista": limpiar(lista), "elegidos": bool(elegidos),
                                        "pendiente": bool(pendiente), "t": time.time()})

    # ---- nube
    def leer_nube(self):
        filas = self.sesion.pedir("GET", "perfiles?select=gustos,gustos_elegidos"
                                         f"&id=eq.{self.sesion.user_id}") or []
        d = filas[0] if filas else {}
        return {"lista": limpiar(d.get("gustos") if isinstance(d.get("gustos"), list) else []),
                "elegidos": bool(d.get("gustos_elegidos"))}

    def _subir(self, lista):
        self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.sesion.user_id}",
                          json={"gustos": limpiar(lista), "gustos_elegidos": True},
                          cabeceras={"Prefer": "return=minimal"})

    def guardar(self, lista, omitido=False):
        """Guarda los gustos (o el «omitir»). Siempre queda la copia local; si no hay red,
        queda pendiente y se reintenta con `sincronizar`. Devuelve True si llegó a la nube."""
        lista = [] if omitido else limpiar(lista)
        self._guardar_local(lista, True, True)
        try:
            self._subir(lista)
        except nube.ErrorNube:
            return False
        self._guardar_local(lista, True, False)
        return True

    def sincronizar(self):
        """Reintenta lo pendiente y, si la nube tiene gustos que aquí faltan, los trae.
        Devuelve la lista vigente (o None si no hubo red)."""
        loc = self.local()
        try:
            if loc["pendiente"]:
                self._subir(loc["lista"])
                self._guardar_local(loc["lista"], True, False)
                return loc["lista"]
            remoto = self.leer_nube()
        except nube.ErrorNube:
            return None
        if remoto["elegidos"] and (remoto["lista"] != loc["lista"] or not loc["elegidos"]):
            self._guardar_local(remoto["lista"], True, False)
            return remoto["lista"]
        return loc["lista"]

    def hace_falta_pantalla(self):
        """True si hay que mostrar la pantalla de elegir artistas al entrar:
        la cuenta tiene gustos_elegidos=false. Sin red y sin respuesta antes, no se estorba."""
        loc = self.local()
        if loc["elegidos"]:
            return False
        try:
            remoto = self.leer_nube()
        except nube.ErrorNube:
            return False
        if remoto["elegidos"]:
            self._guardar_local(remoto["lista"], True, False)
            return False
        return True
