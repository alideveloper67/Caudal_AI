# -*- coding: utf-8 -*-
"""Listas compartidas y colaborativas (igual que en el teléfono).

Sin pantallas: aquí viven los códigos, los datos que devuelve la base
(supabase/listas.sql), el mensaje para compartir y los pasos de «compartir una
lista y mandarla por el chat». Las ventanas solo llaman a esto.

El código de una lista son 8 caracteres legibles (sin I, L, O, 0 ni 1). Se muestra
con guion (K7M2-9QXP); se acepta en minúsculas, con espacios y con o sin guion.
"""

import re
import time

from .chat import pista_jugable
from .coleccion import para_nube

ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO = 8
SERVIDOR_WEB = "https://caudal-musica.netlify.app"
ROLES = ("colaborador", "oyente")
POR_DEFECTO = "colaborador"
MAX_MIEMBROS = 20
MAX_CANCIONES = 2000
CADA_REFRESCO = 20            # segundos: lista compartida abierta

# ---------------------------------------------------------------- códigos


def normalizar_codigo(texto):
    """Los 8 caracteres en mayúsculas, sin espacios ni guiones ("" si no es un código)."""
    limpio = re.sub(r"[\s\-]", "", str(texto or "")).upper()
    if len(limpio) == LARGO and all(c in ALFABETO for c in limpio):
        return limpio
    return ""


def con_guion(codigo):
    c = normalizar_codigo(codigo)
    return f"{c[:4]}-{c[4:]}" if c else ""


def extraer_codigo(texto):
    """El código de lo que la persona pegó: el código solo, el enlace de Caudal
    (https://…/l/K7M2-9QXP) o el enlace directo (caudal://lista?codigo=…)."""
    t = str(texto or "").strip()
    if not t:
        return ""
    for patron in (r"[?&]codigo=([A-Za-z0-9\- ]+)", r"/l/([A-Za-z0-9\-]+)"):
        m = re.search(patron, t)
        if m:
            return normalizar_codigo(m.group(1))
    # un mensaje entero pegado: se busca algo con forma de código
    directo = normalizar_codigo(t)
    if directo:
        return directo
    for m in re.finditer(r"\b([A-Za-z0-9]{4})-([A-Za-z0-9]{4})\b", t):
        c = normalizar_codigo(m.group(1) + m.group(2))
        if c:
            return c
    return ""


def enlace(codigo):
    return f"{SERVIDOR_WEB}/l/{con_guion(codigo)}"


def enlace_app(codigo):
    return f"caudal://lista?codigo={con_guion(codigo)}"


def mensaje_compartir(nombre, codigo):
    """El texto que se copia al compartir una lista."""
    c = con_guion(codigo)
    return (f"Te paso mi lista «{nombre}» en Caudal 🎧\n"
            f"Ábrela aquí: {SERVIDOR_WEB}/l/{c}\n"
            f"O entra a Caudal › Biblioteca › «Tengo un código» y escribe: {c}")


# ---------------------------------------------------------------- permisos


def normalizar_rol(rol):
    return rol if rol in ROLES else POR_DEFECTO


def etiqueta_rol(rol):
    return "Colaborativa" if normalizar_rol(rol) == "colaborador" else "Solo escuchar"


def frase_permiso(rol):
    """Qué permiso quedó, dicho para personas."""
    if normalizar_rol(rol) == "colaborador":
        return "Quien tenga el código podrá escuchar y añadir canciones."
    return "Quien tenga el código podrá solo escuchar; no podrá añadir canciones."


# ---------------------------------------------------------------- modelos


def _texto(v):
    return str(v) if v is not None else ""


def _entero(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _persona(d):
    d = d if isinstance(d, dict) else {}
    return {"id": _texto(d.get("id")), "usuario": _texto(d.get("usuario")),
            "nombre": _texto(d.get("nombre")), "foto_url": d.get("foto_url") or ""}


def nombre_persona(p):
    p = p or {}
    return p.get("nombre") or p.get("usuario") or "alguien"


def vista_previa(d):
    """`ver_lista_codigo`: {nombre, descripcion, total, rol, miembros, dueno, canciones[≤6]}.
    Devuelve None si el código no existe (la base contesta null)."""
    if not isinstance(d, dict) or not d.get("nombre") and d.get("total") is None:
        return None
    return {"nombre": _texto(d.get("nombre")), "descripcion": _texto(d.get("descripcion")),
            "total": _entero(d.get("total")), "rol": normalizar_rol(d.get("rol")),
            "miembros": _entero(d.get("miembros")), "dueno": _persona(d.get("dueno")),
            "canciones": [{"titulo": _texto(c.get("titulo")), "artista": _texto(c.get("artista")),
                           "miniatura": _texto(c.get("miniatura"))}
                          for c in (d.get("canciones") or []) if isinstance(c, dict)][:6]}


def resultado_unirse(d):
    """`unirse_a_lista`: {lista_id, nombre, rol, es_dueno}."""
    d = d if isinstance(d, dict) else {}
    return {"lista_id": _texto(d.get("lista_id")), "nombre": _texto(d.get("nombre")),
            "rol": normalizar_rol(d.get("rol")), "es_dueno": bool(d.get("es_dueno"))}


def lista_compartida(d):
    """Una fila de `mis_listas_compartidas`."""
    return {"id": _texto(d.get("id")), "nombre": _texto(d.get("nombre")),
            "descripcion": _texto(d.get("descripcion")), "rol": normalizar_rol(d.get("rol")),
            "total": _entero(d.get("total")), "actualizada": _texto(d.get("actualizada")),
            "dueno": _persona(d.get("dueno"))}


def miembro(d):
    """Una fila de `miembros_lista`."""
    p = _persona(d)
    p.update(rol=normalizar_rol(d.get("rol")), desde=_texto(d.get("desde")),
             es_dueno=bool(d.get("es_dueno")))
    return p


def pista_compartida(d):
    """Una fila de `pistas_de_lista`: la canción lista para sonar y quién la añadió."""
    p = pista_jugable(d.get("datos") or {"clave": d.get("clave")})
    if d.get("clave"):
        p["clave"] = d["clave"]
    p["_orden"] = d.get("orden") or 0
    p["_agregada_por"] = _persona(d.get("agregada_por"))
    return p


def quien_agrego(pista):
    return nombre_persona(pista.get("_agregada_por"))


def puede_quitar(rol, es_dueno, pista, yo):
    """El dueño quita cualquiera; un colaborador solo las suyas; quien solo escucha, ninguna."""
    if es_dueno:
        return True
    if rol != "colaborador":
        return False
    return str((pista.get("_agregada_por") or {}).get("id")) == str(yo)


def tarjeta_para_chat(codigo, nombre, canciones, rol, portada=""):
    """`mensajes.lista`: {codigo, nombre, canciones, rol, portada?}."""
    t = {"codigo": normalizar_codigo(codigo), "nombre": _texto(nombre)[:120],
         "canciones": _entero(canciones), "rol": normalizar_rol(rol)}
    if portada and str(portada).startswith("http"):
        t["portada"] = str(portada)
    return t


def tarjeta_limpia(d):
    """La tarjeta tal como llega en un mensaje (o None si no sirve)."""
    if not isinstance(d, dict) or not normalizar_codigo(d.get("codigo")):
        return None
    return tarjeta_para_chat(d["codigo"], d.get("nombre") or "Lista", d.get("canciones"),
                             d.get("rol"), d.get("portada") or "")


# ---------------------------------------------------------------- la nube


class ListasCompartidas:
    """Las llamadas a la base; `sesion.rpc(nombre, p_…=…)` es la de nube.Sesion."""

    def __init__(self, sesion):
        self.sesion = sesion

    @property
    def yo(self):
        return self.sesion.user_id

    def compartir(self, lista_uuid, rol=POR_DEFECTO):
        return normalizar_codigo(self.sesion.rpc("compartir_lista", p_lista=lista_uuid,
                                                 p_rol=normalizar_rol(rol)))

    def dejar_de_compartir(self, lista_uuid):
        self.sesion.rpc("dejar_de_compartir_lista", p_lista=lista_uuid)

    def ver_codigo(self, codigo):
        c = normalizar_codigo(codigo)
        if not c:
            return None
        return vista_previa(self.sesion.rpc("ver_lista_codigo", p_codigo=c))

    def unirse(self, codigo):
        return resultado_unirse(self.sesion.rpc("unirse_a_lista", p_codigo=normalizar_codigo(codigo)))

    def salir(self, lista_id):
        self.sesion.rpc("salir_de_lista", p_lista=lista_id)

    def quitar_miembro(self, lista_id, usuario_id):
        self.sesion.rpc("quitar_miembro", p_lista=lista_id, p_usuario=usuario_id)

    def miembros(self, lista_id):
        return [miembro(m) for m in (self.sesion.rpc("miembros_lista", p_lista=lista_id) or [])]

    def mis_compartidas(self):
        return [lista_compartida(x) for x in (self.sesion.rpc("mis_listas_compartidas") or [])]

    def pistas(self, lista_id):
        return [pista_compartida(x) for x in (self.sesion.rpc("pistas_de_lista", p_lista=lista_id) or [])]

    def agregar(self, lista_id, pistas):
        """Cuántas entraron (las repetidas se ignoran)."""
        items = [{"clave": p["clave"], "datos": para_nube(p)} for p in pistas
                 if p.get("clave") and str(p["clave"]).startswith("yt:")]
        if not items:
            return 0
        return _entero(self.sesion.rpc("agregar_a_lista_compartida", p_lista=lista_id, p_items=items))

    def quitar(self, lista_id, clave):
        self.sesion.rpc("quitar_de_lista_compartida", p_lista=lista_id, p_clave=clave)


# ---------------------------------------------------------------- compartir una lista mía


CLAVE_CODIGOS = "codigos_listas"       # estado local: {uuid de la lista: {"codigo", "rol"}}


def codigos_guardados(col):
    d = col.estado(CLAVE_CODIGOS, {})
    return d if isinstance(d, dict) else {}


def recordar_codigo(col, lista_uuid, codigo, rol):
    d = codigos_guardados(col)
    d[lista_uuid] = {"codigo": normalizar_codigo(codigo), "rol": normalizar_rol(rol)}
    col.guardar_estado(CLAVE_CODIGOS, d)


def olvidar_codigo(col, lista_uuid):
    d = codigos_guardados(col)
    if d.pop(lista_uuid, None) is not None:
        col.guardar_estado(CLAVE_CODIGOS, d)


def estado_de_mi_lista(col, nube, lista_uuid):
    """¿Mi lista ya está compartida? Devuelve {"codigo", "rol"} o None. Se confirma con la base:
    el código guardado puede haberse dejado de compartir desde el teléfono."""
    g = codigos_guardados(col).get(lista_uuid)
    if not g:
        return None
    vista = nube.ver_codigo(g["codigo"])
    if vista is None:
        olvidar_codigo(col, lista_uuid)
        return None
    if vista["rol"] != g["rol"]:
        recordar_codigo(col, lista_uuid, g["codigo"], vista["rol"])
    return {"codigo": g["codigo"], "rol": vista["rol"]}


def compartir_mi_lista(col, nube, lista_id, rol=None, antes=None):
    """Comparte (o cambia el permiso de) una lista mía y devuelve {codigo, rol, nombre, canciones}.
    `antes()` sube lo pendiente a la nube: la lista tiene que existir allí para tener código."""
    if antes:
        antes()
    lista = col.lista(lista_id)
    if not lista:
        raise ValueError("Esa lista ya no existe.")
    u = col._uuid_lista(lista_id)
    actual = estado_de_mi_lista(col, nube, u)
    rol = normalizar_rol(rol or (actual or {}).get("rol") or POR_DEFECTO)
    if actual and actual["rol"] == rol:
        codigo = actual["codigo"]
    else:
        codigo = nube.compartir(u, rol)
        recordar_codigo(col, u, codigo, rol)
    n = sum(1 for p in col.pistas_de_lista(lista_id) if str(p.get("clave", "")).startswith("yt:"))
    return {"codigo": codigo, "rol": rol, "nombre": lista["nombre"], "canciones": n,
            "portada": _portada_web(col, lista_id), "lista_id": lista_id, "uuid": u,
            "ya": actual is not None}


def _portada_web(col, lista_id):
    for m in col.portadas_de_lista(lista_id, 4):
        if str(m).startswith("http"):
            return m
    return ""


def dejar_de_compartir_mi_lista(col, nube, lista_id, antes=None):
    if antes:
        antes()
    u = col._uuid_lista(lista_id)
    nube.dejar_de_compartir(u)
    olvidar_codigo(col, u)


def preparar_lista_para_chat(col, nube, lista_id, rol=None, antes=None):
    """«Enviar una lista» desde un chat: elige la lista → se comparte sola si aún no lo estaba
    (permiso por defecto: pueden añadir canciones) → devuelve lo que va en el mensaje.
    Si ya estaba compartida, se reutiliza su código y su permiso (salvo que se pida otro)."""
    r = compartir_mi_lista(col, nube, lista_id, rol, antes)
    return {"tarjeta": tarjeta_para_chat(r["codigo"], r["nombre"], r["canciones"], r["rol"], r["portada"]),
            "frase": frase_permiso(r["rol"]), "ya_compartida": r["ya"]}


# ---------------------------------------------------------------- caché (que no haya pantallas en blanco)

_CACHE = {}


def en_cache(clave, vigencia=60):
    d = _CACHE.get(clave)
    if d and time.time() - d[0] < vigencia:
        return d[1]
    return None


def guardar_cache(clave, valor):
    _CACHE[clave] = (time.time(), valor)


def ultima_conocida(clave):
    d = _CACHE.get(clave)
    return d[1] if d else None


# ---------------------------------------------------------------- lo último que se sabía (pintar al instante)

CLAVE_COMPARTIDAS = "listas_compartidas"      # estado local: la última respuesta de mis_listas_compartidas
CLAVE_UNIONES = "listas_unidas"               # estado local: {código: id de la lista} de las que ya me uní


def compartidas_guardadas(col):
    d = col.estado(CLAVE_COMPARTIDAS, [])
    return d if isinstance(d, list) else []


def guardar_compartidas(col, filas):
    if filas != compartidas_guardadas(col):
        col.guardar_estado(CLAVE_COMPARTIDAS, filas)


def recordar_union(col, codigo, lista_id):
    d = col.estado(CLAVE_UNIONES, {})
    d = d if isinstance(d, dict) else {}
    d[normalizar_codigo(codigo)] = lista_id
    col.guardar_estado(CLAVE_UNIONES, d)


def lista_de_codigo(col, codigo):
    """Si esa tarjeta del chat es una lista que ya es mía o a la que ya me uní:
    {"tipo": "mia", "id": id local} | {"tipo": "unida", "id": uuid} | None."""
    c = normalizar_codigo(codigo)
    for u, g in codigos_guardados(col).items():
        if g.get("codigo") == c:
            mia = col.lista_por_uuid(u)
            if mia:
                return {"tipo": "mia", "id": mia["id"]}
    d = col.estado(CLAVE_UNIONES, {})
    if isinstance(d, dict) and c in d:
        return {"tipo": "unida", "id": d[c]}
    return None
