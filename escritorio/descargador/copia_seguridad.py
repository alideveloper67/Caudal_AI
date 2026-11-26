# -*- coding: utf-8 -*-
"""Copia de seguridad de Caudal: todos tus datos en un archivo `.caudal`.

El archivo es un ZIP con dos JSON (y las imágenes que hagan falta):

    manifiesto.json   qué es, de qué versión, de qué app y un resumen
    datos.json        la colección, los ajustes y lo demás (ver más abajo)
    portadas/N.jpg    portadas propias de tus listas
    fondo/fondo.jpg   tu imagen de fondo de Caudal (si tienes una)

El MISMO formato lo escribe y lo lee la app del teléfono (app/lib/nucleo/copia_seguridad.dart):
una copia hecha en la PC se abre en el teléfono y al revés.

Lo que NO va nunca: sesiones, tokens, contraseñas, cookies, claves de Spotify, el proxy, la
geometría de la ventana ni los audios/videos descargados (solo su registro).

Versiones: `version` es la del formato con que se escribió y `lee_desde` la versión mínima
de lector que la entiende. Si una versión futura añade cosas sin romper nada, sube `version`
y deja `lee_desde` en 1: las apps viejas la siguen abriendo e ignoran lo nuevo.
"""

import io
import json
import os
import time
import zipfile
import zlib

from . import disco
from datetime import datetime, timezone
from pathlib import Path

FORMATO = "caudal-copia"
VERSION_FORMATO = 1          # la que escribe esta app
LEE_HASTA = 1                # la más nueva que esta app sabe leer
EXTENSION = ".caudal"
APP = "escritorio"

MAX_ARCHIVO = 400 * 1024 * 1024          # una copia más grande no es nuestra (o está mal)
MAX_DESCOMPRIMIDO = 800 * 1024 * 1024

# ajustes que significan lo mismo en la PC y en el teléfono (mismo nombre, mismo valor)
AJUSTES_COMUNES = (
    "region", "calidad_audio", "calidad_video", "codec_video", "crossfade", "normalizar",
    "traducir_letra", "acento", "fondo", "personaje_baila", "super_volumen", "ecualizador",
    "eq_bandas", "eq_preset", "velocidad", "autoplay", "sponsorblock", "sponsorblock_videos",
    "preferir_descargado", "aleatorio", "repetir", "formato_audio", "bitrate_mp3", "tipo_descarga",
    "letras_auto", "descarga_inteligente", "descarga_inteligente_gb", "transicion_dj", "mezcla_dj",
    "mezcla_dj_seg", "mezcla_dj_graves", "apagado_suave",
    "estilo_letra", "fuente_letra",      # cómo se ve la letra (mismas claves en Android)
)
# nunca salen del equipo: sesiones, secretos, cookies, rutas y avisos de una sola vez
AJUSTES_FUERA = {
    "sesion_token", "sesion_usuario", "mantener_sesion", "recordar_sesion", "spotify_id",
    "spotify_secreto", "soundcloud_id", "soundcloud_secreto", "navegador_cookies", "archivo_cookies", "proxy", "geometria",
    "version_novedades_vista", "presentacion_mascotas_vista", "cumple_celebrado",
    "aviso_regalo_visto", "segundo_plano",
}
# lo que se guarda en el «estado» de la colección y vale la pena llevarse
ESTADO_COPIABLE = ("saltos", "mezclas_dj", "mezclador_borrador")
# archivos propios de Caudal Escritorio que viajan tal cual (solo se restauran en una PC)
ARCHIVOS_ESCRITORIO = ("modo_gamer.json", "modo_gamer_progreso.json")

TABLAS_REEMPLAZABLES = ("me_gusta", "lista_items", "listas", "reproducciones",
                        "contextos_recientes", "guardados", "busquedas")


class ErrorCopia(Exception):
    """Un problema con la copia, explicado para la persona."""


# ====================================================================== utilidades


def _json(texto, defecto=None):
    try:
        return json.loads(texto) if texto else defecto
    except (TypeError, ValueError):
        return defecto


def _num(v, defecto=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return defecto


def _video_id_de_url(url):
    from .coleccion import _video_id_de_url as vid
    return vid(url)


def nombre_sugerido(automatica=False, ahora=None):
    f = datetime.fromtimestamp(ahora or time.time())
    base = "Caudal-auto" if automatica else "Caudal-copia"
    return f"{base}-{f:%Y-%m-%d-%H%M}{EXTENSION}"


def _ahora_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ====================================================================== exportar


def _datos_coleccion(col):
    con = col.con
    me_gusta = [{"clave": f["clave"], "fecha": f["fecha"]}
                for f in con.execute("SELECT clave, fecha FROM me_gusta ORDER BY fecha DESC")]
    listas = []
    portadas = {}
    for i, l in enumerate(con.execute("SELECT * FROM listas ORDER BY id").fetchall()):
        l = dict(l)
        uuid = l.get("uuid") or col._uuid_lista(l["id"]) or ""
        items = [{"clave": f["clave"], "orden": f["orden"], "agregada": f["agregada"]}
                 for f in con.execute("SELECT clave, orden, agregada FROM lista_items "
                                      "WHERE lista_id = ? ORDER BY orden", (l["id"],))]
        entrada = {"uuid": uuid, "nombre": l["nombre"], "descripcion": l.get("descripcion") or "",
                   "fijada": bool(l.get("fijada")), "color": l.get("color") or "",
                   "creada": l.get("creada"), "tocada": l.get("tocada") or 0,
                   "publica": bool(l.get("publica")), "en_perfil": bool(l.get("en_perfil")),
                   "portada": None, "items": items}
        ruta = col.portada_personalizada(l["id"])
        if ruta:
            try:
                nombre = f"portadas/{i + 1}.jpg"
                portadas[nombre] = Path(ruta).read_bytes()
                entrada["portada"] = nombre
            except OSError:
                pass
        listas.append(entrada)
    escuchas = [{"clave": f["clave"], "fecha": f["fecha"], "contexto": _json(f["contexto"])}
                for f in con.execute("SELECT clave, fecha, contexto FROM reproducciones ORDER BY fecha")]
    contextos = [{"tipo": f["tipo"], "id": f["id"], "datos": _json(f["datos"], {}), "fecha": f["fecha"]}
                 for f in con.execute("SELECT * FROM contextos_recientes ORDER BY fecha DESC")]
    guardados = [{"tipo": f["tipo"], "id": f["id"], "datos": _json(f["datos"], {}), "fecha": f["fecha"]}
                 for f in con.execute("SELECT * FROM guardados ORDER BY fecha DESC")]
    busquedas = [{"texto": f["texto"], "fecha": f["fecha"]}
                 for f in con.execute("SELECT texto, fecha FROM busquedas ORDER BY fecha DESC")]
    descargas = []
    for f in con.execute("SELECT * FROM descargas ORDER BY id"):
        f = dict(f)
        descargas.append({
            "ref": f"local:{f['id']}", "video_id": _video_id_de_url(f.get("url")),
            "url": f.get("url") or "", "titulo": f.get("titulo") or "",
            "artista": f.get("autor") or "", "plataforma": f.get("plataforma") or "",
            "archivo": f.get("archivo") or "", "es_audio": bool(f.get("es_audio")),
            "tamano": int(f.get("tamano") or 0), "duracion": int(f.get("duracion") or 0),
            "calidad": f.get("calidad") or "", "caratula": f.get("caratula") or "",
            "estado": f.get("estado") or "completada", "fecha": f.get("fecha") or 0, "datos": {}})
    # los datos de cada canción que se nombra (sin rutas de este equipo)
    usadas = {g["clave"] for g in me_gusta} | {e["clave"] for e in escuchas}
    for l in listas:
        usadas |= {it["clave"] for it in l["items"]}
    en_linea = sorted(c for c in usadas if c and not c.startswith("local:"))
    pistas = {}
    for i in range(0, len(en_linea), 500):
        tanda = en_linea[i:i + 500]
        marcas = ",".join("?" * len(tanda))
        for f in con.execute(f"SELECT clave, datos FROM pistas WHERE clave IN ({marcas})", tanda):
            d = _json(f["datos"])
            if isinstance(d, dict):
                d.pop("archivo", None)
                pistas[f["clave"]] = d
    estado = {}
    for k in ESTADO_COPIABLE:
        v = col.estado(k)
        if v is not None:
            estado[k] = v
    return {"pistas": pistas, "me_gusta": me_gusta, "listas": listas, "escuchas": escuchas,
            "contextos": contextos, "guardados": guardados, "busquedas": busquedas,
            "descargas": descargas, "estado": estado}, portadas


def _datos_ajustes(ajustes):
    from .config import DEFECTOS
    valores = dict(getattr(ajustes, "datos", None) or ajustes or {})
    comunes, propios = {}, {}
    for k in DEFECTOS:
        if k in AJUSTES_FUERA or k not in valores:
            continue
        v = valores[k]
        if k == "eq_bandas" and isinstance(v, str):
            v = _json(v, [0] * 10)
        (comunes if k in AJUSTES_COMUNES else propios)[k] = v
    return {"comunes": comunes, "escritorio": propios}


def _datos_estudio(carpeta):
    def leer(nombre, defecto):
        try:
            disco.vaciar()
            return json.loads((carpeta / nombre).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return defecto
    hist = leer("estudio_historial.json", {})
    notas = leer("estudio_notas.json", [])
    cfg = leer("estudio.json", {})
    notas = [{"id": str(n.get("id") or ""), "texto": str(n.get("texto") or ""),
              "fecha": str(n.get("fecha") or "")}
             for n in (notas if isinstance(notas, list) else []) if isinstance(n, dict) and n.get("texto")]
    dias = {str(k): int(v) for k, v in ((hist or {}).get("dias") or {}).items()
            if isinstance(v, (int, float))}
    if not notas and not dias and not cfg:
        return None
    return {"notas": notas, "dias": dias, "sesiones": list((hist or {}).get("sesiones") or []),
            "config_escritorio": cfg if isinstance(cfg, dict) else {}}


def _datos_gustos(col):
    d = col.estado("gustos") or {}
    lista = d.get("lista") if isinstance(d, dict) else None
    if not lista and not (isinstance(d, dict) and d.get("elegidos")):
        return None
    return {"artistas": [{"nombre": str(a.get("nombre") or ""), "id": str(a.get("id") or ""),
                          "portada": str(a.get("portada") or "")}
                         for a in (lista or []) if isinstance(a, dict) and a.get("nombre")],
            "elegidos": bool(d.get("elegidos"))}


def resumen(datos):
    """Cuántas cosas trae una copia (sale de los datos, no del manifiesto)."""
    col = datos.get("coleccion") or {}
    listas = col.get("listas") or []
    estudio = datos.get("estudio") or {}
    ajustes = datos.get("ajustes") or {}
    n_aj = sum(len(v) for v in ajustes.values() if isinstance(v, dict))
    return {
        "me_gusta": len(col.get("me_gusta") or []),
        "listas": len(listas),
        "canciones_en_listas": sum(len(l.get("items") or []) for l in listas),
        "escuchas": len(col.get("escuchas") or []),
        "guardados": len(col.get("guardados") or []),
        "descargas": len(col.get("descargas") or []),
        "busquedas": len(col.get("busquedas") or []),
        "notas": len(estudio.get("notas") or []),
        "dias_estudio": len(estudio.get("dias") or {}),
        "ajustes": n_aj,
        "ecualizador": "eq_bandas" in (ajustes.get("comunes") or {}),
        "mascota": bool(datos.get("mascota")),
        "fondo": bool((datos.get("fondo") or {}).get("imagen")),
        "gustos": len((datos.get("gustos") or {}).get("artistas") or []),
    }


def _miles(n):
    return f"{n:,}".replace(",", ".")


def texto_resumen(r):
    """«142 canciones en me gusta · 12 listas (310 canciones) · …» (para la vista previa)."""
    partes = []

    def poner(n, uno, varios):
        if n:
            partes.append(f"{_miles(n)} {uno if n == 1 else varios}")
    poner(r.get("me_gusta", 0), "canción en me gusta", "canciones en me gusta")
    if r.get("listas"):
        c = r.get("canciones_en_listas", 0)
        partes.append(f"{_miles(r['listas'])} {'lista' if r['listas'] == 1 else 'listas'}"
                      f" ({_miles(c)} {'canción' if c == 1 else 'canciones'})")
    poner(r.get("escuchas", 0), "escucha en tu historial", "escuchas en tu historial")
    poner(r.get("guardados", 0), "álbum, lista o artista guardado", "álbumes, listas y artistas guardados")
    poner(r.get("descargas", 0), "descarga registrada", "descargas registradas")
    poner(r.get("busquedas", 0), "búsqueda reciente", "búsquedas recientes")
    poner(r.get("notas", 0), "nota del modo estudio", "notas del modo estudio")
    poner(r.get("dias_estudio", 0), "día de estudio", "días de estudio")
    poner(r.get("gustos", 0), "artista favorito", "artistas favoritos")
    if r.get("ajustes"):
        partes.append("tus ajustes" + (" y el ecualizador" if r.get("ecualizador") else ""))
    if r.get("mascota"):
        partes.append("tu mascota")
    if r.get("fondo"):
        partes.append("tu imagen de fondo")
    return " · ".join(partes) if partes else "La copia está vacía."


def crear_copia(col, ajustes=None, carpeta=None, mascota=None, fondo=None):
    """Arma la copia en memoria y devuelve los bytes del `.caudal`.

    `col` es la Coleccion (vale una `copia_de_lectura()` para hacerlo en otro hilo); `carpeta` la
    carpeta de la cuenta (estudio, modo gamer, fondo); `mascota` la clave elegida; `fondo` un dict
    {"visible", "desenfoque", "imagen": bytes | None}."""
    from . import version
    if carpeta is None:
        from .config import carpeta_perfil
        carpeta = carpeta_perfil()
    carpeta = Path(carpeta)
    coleccion, portadas = _datos_coleccion(col)
    datos = {"coleccion": coleccion, "ajustes": _datos_ajustes(ajustes) if ajustes is not None else {}}
    if mascota is None:
        mascota = (_json(_leer_texto(carpeta / "mascota.json"), {}) or {}).get("clave") or ""
    datos["mascota"] = mascota or None
    imagen_fondo = None
    if fondo is None:
        info = _json(_leer_texto(carpeta / "fondo_app.json"), {}) or {}
        jpg = carpeta / "fondo_app.jpg"
        fondo = {"visible": info.get("visible"), "desenfoque": info.get("desenfoque"),
                 "imagen": jpg.read_bytes() if info.get("tiene") and jpg.exists() else None}
    if fondo and (fondo.get("visible") is not None or fondo.get("imagen")):
        imagen_fondo = fondo.get("imagen")
        datos["fondo"] = {"visible": fondo.get("visible"), "desenfoque": fondo.get("desenfoque"),
                          "imagen": "fondo/fondo.jpg" if imagen_fondo else None}
    datos["estudio"] = _datos_estudio(carpeta)
    datos["gustos"] = _datos_gustos(col)
    archivos = {}
    for nombre in ARCHIVOS_ESCRITORIO:
        v = _json(_leer_texto(carpeta / nombre))
        if v is not None:
            archivos[nombre] = v
    datos["archivos_escritorio"] = archivos
    manifiesto = {"formato": FORMATO, "version": VERSION_FORMATO, "lee_desde": 1,
                  "creada": _ahora_iso(),
                  "origen": {"app": APP, "version_app": getattr(version, "VERSION", ""),
                             "sistema": os.name},
                  "resumen": resumen(datos)}
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False, indent=1))
        z.writestr("datos.json", json.dumps(datos, ensure_ascii=False))
        for nombre, b in portadas.items():
            z.writestr(nombre, b)
        if imagen_fondo:
            z.writestr("fondo/fondo.jpg", imagen_fondo)
    return salida.getvalue()


def _leer_texto(ruta):
    try:
        return Path(ruta).read_text(encoding="utf-8")
    except OSError:
        return ""


def guardar_copia(destino, contenido):
    """Escribe el archivo de forma segura (temporal + renombrar). Devuelve la ruta final."""
    destino = Path(destino)
    if destino.suffix.lower() != EXTENSION:
        destino = destino.with_name(destino.name + EXTENSION)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    try:
        tmp.write_bytes(contenido)
        os.replace(tmp, destino)
    except OSError as e:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise ErrorCopia("No se pudo guardar la copia en esa carpeta. Elige otra o revisa que "
                         "haya espacio libre.") from e
    return destino


# ====================================================================== leer


class Copia:
    """Una copia ya abierta y revisada: manifiesto, datos e imágenes."""

    def __init__(self, manifiesto, datos, archivos):
        self.manifiesto = manifiesto
        self.datos = datos
        self.archivos = archivos        # nombre -> bytes (portadas, fondo)

    @property
    def origen(self):
        return (self.manifiesto.get("origen") or {}).get("app") or ""

    @property
    def creada(self):
        return self.manifiesto.get("creada") or ""

    def resumen(self):
        return resumen(self.datos)

    def texto_resumen(self):
        return texto_resumen(self.resumen())

    def descripcion(self):
        """«Hecha el 19/11/2026 a las 10:20 en Caudal para teléfono 2.6.1»."""
        app = {"escritorio": "Caudal Escritorio", "movil": "Caudal para teléfono"}.get(
            self.origen, "Caudal")
        version_app = (self.manifiesto.get("origen") or {}).get("version_app") or ""
        cuando = ""
        try:
            f = datetime.fromisoformat(self.creada.replace("Z", "+00:00")).astimezone()
            cuando = f"Hecha el {f:%d/%m/%Y} a las {f:%H:%M} en "
        except ValueError:
            cuando = "Hecha en "
        return f"{cuando}{app} {version_app}".strip()


def abrir_copia(origen):
    """Lee y revisa una copia (ruta o bytes). Lanza ErrorCopia con un mensaje claro."""
    try:
        if isinstance(origen, (bytes, bytearray)):
            contenido = bytes(origen)
        else:
            ruta = Path(origen)
            if not ruta.exists():
                raise ErrorCopia("No se encuentra ese archivo. Puede que se haya movido o borrado.")
            if ruta.stat().st_size > MAX_ARCHIVO:
                raise ErrorCopia("Ese archivo es demasiado grande para ser una copia de Caudal.")
            contenido = ruta.read_bytes()
    except OSError as e:
        raise ErrorCopia("No se pudo leer el archivo. Revisa que no esté abierto en otro programa.") from e
    if not contenido:
        raise ErrorCopia("El archivo está vacío: la copia no se terminó de guardar.")
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile as e:
        raise ErrorCopia("Este archivo no es una copia de Caudal, o está dañado.") from e
    with z:
        nombres = set(z.namelist())
        if "manifiesto.json" not in nombres:
            raise ErrorCopia("Este archivo no es una copia de seguridad de Caudal.")
        if sum(i.file_size for i in z.infolist()) > MAX_DESCOMPRIMIDO:
            raise ErrorCopia("La copia es demasiado grande o está dañada.")
        try:
            manifiesto = json.loads(z.read("manifiesto.json").decode("utf-8"))
        except (ValueError, UnicodeDecodeError, zipfile.BadZipFile, OSError, zlib.error) as e:
            raise ErrorCopia("La copia está dañada (puede que no se terminara de copiar). "
                             "Prueba con otra copia.") from e
        if not isinstance(manifiesto, dict) or manifiesto.get("formato") != FORMATO:
            raise ErrorCopia("Este archivo no es una copia de seguridad de Caudal.")
        try:
            lee_desde = int(manifiesto.get("lee_desde", manifiesto.get("version", 1)))
        except (TypeError, ValueError):
            lee_desde = 999
        if lee_desde > LEE_HASTA:
            raise ErrorCopia("Esta copia se hizo con una versión más nueva de Caudal. Actualiza "
                             "Caudal en este equipo y vuelve a intentarlo.")
        if "datos.json" not in nombres:
            raise ErrorCopia("La copia está incompleta: le falta lo más importante. Prueba con otra copia.")
        try:
            datos = json.loads(z.read("datos.json").decode("utf-8"))
            archivos = {n: z.read(n) for n in nombres
                        if n.startswith(("portadas/", "fondo/")) and not n.endswith("/")}
        except (ValueError, UnicodeDecodeError, zipfile.BadZipFile, OSError, EOFError, zlib.error) as e:
            # BadZipFile también salta cuando el CRC no cuadra (archivo cortado o alterado)
            raise ErrorCopia("La copia está dañada (puede que no se terminara de copiar). "
                             "Prueba con otra copia.") from e
        if not isinstance(datos, dict):
            raise ErrorCopia("La copia está dañada. Prueba con otra copia.")
    return Copia(manifiesto, datos, archivos)


# ====================================================================== restaurar la colección


def _pista_de_descarga(d, clave):
    artista = d.get("artista") or ""
    base = dict(d.get("datos") or {})
    base.update({"tipo": "pista", "clave": clave, "video_id": d.get("video_id") or "",
                 "titulo": d.get("titulo") or base.get("titulo") or "Sin título",
                 "artista": artista or base.get("artista") or "",
                 "artistas": base.get("artistas") or ([{"nombre": artista, "id": ""}] if artista else []),
                 "duracion": int(d.get("duracion") or 0),
                 "miniatura": d.get("caratula") or base.get("miniatura") or ""})
    for k in ("archivo", "descarga_id", "es_audio", "tamano", "calidad", "fecha", "url"):
        base.pop(k, None)
    return base


def _restaurar_descargas(con, descargas, existe=os.path.exists, misma_app=True):
    """Mete el registro de descargas que falte y devuelve {ref de la copia: clave en este equipo}.
    Si el archivo no está en este equipo pero se sabe qué video era, la canción se escucha desde
    internet (clave yt:...). Las descargas del teléfono cuyo archivo no está en esta PC no se
    apuntan en el historial (serían filas fantasma)."""
    mapa, pistas_nuevas, nuevas = {}, {}, 0
    for d in descargas or []:
        if not isinstance(d, dict) or not d.get("ref"):
            continue
        archivo = d.get("archivo") or ""
        url = d.get("url") or ""
        es_audio = 1 if d.get("es_audio") else 0
        fila = None
        if archivo:
            fila = con.execute("SELECT id FROM descargas WHERE archivo = ?", (archivo,)).fetchone()
        if fila is None and url:
            fila = con.execute("SELECT id FROM descargas WHERE url = ? AND es_audio = ? AND "
                               "COALESCE(titulo,'') = ?", (url, es_audio, d.get("titulo") or "")).fetchone()
        esta_aqui = bool(archivo) and existe(archivo)
        if fila is None and not misma_app and not esta_aqui:
            if d.get("video_id"):
                clave = f"yt:{d['video_id']}"
                mapa[d["ref"]] = clave
                pistas_nuevas[clave] = _pista_de_descarga(d, clave)
            continue
        if fila is None:
            cur = con.execute(
                "INSERT INTO descargas (url, titulo, plataforma, archivo, tamano, duracion, calidad,"
                " estado, fecha, caratula, es_audio, autor) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (url or (f"https://www.youtube.com/watch?v={d['video_id']}" if d.get("video_id") else ""),
                 d.get("titulo") or "", d.get("plataforma") or "", archivo, int(d.get("tamano") or 0),
                 int(d.get("duracion") or 0), d.get("calidad") or "", d.get("estado") or "completada",
                 _num(d.get("fecha"), time.time()), d.get("caratula") or "", es_audio,
                 d.get("artista") or ""))
            ident = cur.lastrowid
            nuevas += 1
        else:
            ident = fila["id"]
        if esta_aqui:
            mapa[d["ref"]] = f"local:{ident}"
        elif d.get("video_id"):
            clave = f"yt:{d['video_id']}"
            mapa[d["ref"]] = clave
            pistas_nuevas[clave] = _pista_de_descarga(d, clave)
        else:
            mapa[d["ref"]] = f"local:{ident}"
    return mapa, pistas_nuevas, nuevas


def _anotar(con, op, datos):
    """Deja la orden para la nube, igual que hace la colección."""
    con.execute("INSERT INTO pendientes (op, datos, creada) VALUES (?,?,?)",
                    (op, json.dumps(datos, ensure_ascii=False), time.time()))


def restaurar_coleccion(col, copia, modo="juntar", existe=os.path.exists, anotar=None):
    """Mete la colección de la copia en `col`. modo: «juntar» (sin duplicar) o «reemplazar».
    `anotar`: dejar las órdenes para la nube (por defecto, si `col` tiene sincronizador; desde otro
    hilo se pasa a mano porque la copia de lectura no lo lleva). Devuelve un dict con lo que entró
    de nuevo. Las descargas nunca se borran."""
    if anotar is None:
        anotar = getattr(col, "sincronizador", None) is not None
    from .coleccion import para_nube
    if modo not in ("juntar", "reemplazar"):
        raise ValueError(modo)
    datos = (copia.datos if isinstance(copia, Copia) else copia).get("coleccion") or {}
    archivos = copia.archivos if isinstance(copia, Copia) else {}
    con = col.con
    cuenta = {"me_gusta": 0, "listas": 0, "canciones_en_listas": 0, "escuchas": 0,
              "guardados": 0, "descargas": 0, "busquedas": 0}
    portadas_pendientes, portadas_viejas = [], []
    if con.in_transaction:
        con.commit()
    try:
        con.execute("BEGIN")
        def nota(op, d):
            if anotar:
                _anotar(con, op, d)

        mapa, pistas_desc, cuenta["descargas"] = _restaurar_descargas(
            con, datos.get("descargas"), existe,
            misma_app=(copia.origen if isinstance(copia, Copia) else APP) == APP)

        def clave_aqui(c):
            if not isinstance(c, str) or not c:
                return None
            if c.startswith("local:"):
                return mapa.get(c)        # una descarga que no vino en la copia: no se inventa
            return c

        if modo == "reemplazar":
            if anotar:
                # lo que se quita también se quita de la cuenta (si no, volvería al sincronizar)
                for f in con.execute("SELECT clave FROM me_gusta WHERE clave LIKE 'yt:%'").fetchall():
                    nota("me_gusta_quitar", {"clave": f["clave"]})
                for f in con.execute("SELECT uuid FROM listas WHERE uuid IS NOT NULL AND uuid != ''").fetchall():
                    nota("lista_borrar", {"uuid": f["uuid"]})
                for f in con.execute("SELECT tipo, id FROM guardados").fetchall():
                    if f["tipo"] in ("album", "lista", "artista"):
                        nota("guardado_quitar", {"tipo": f["tipo"], "id": f["id"]})
            # las imágenes se borran solo si todo sale bien (después del COMMIT)
            portadas_viejas.extend(f["portada"] for f in con.execute(
                "SELECT portada FROM listas WHERE portada IS NOT NULL").fetchall())
            for t in TABLAS_REEMPLAZABLES:
                con.execute(f"DELETE FROM {t}")

        # canciones
        modo_pista = "REPLACE" if modo == "reemplazar" else "IGNORE"
        ahora = time.time()
        pistas = dict(datos.get("pistas") or {})
        for c, p in pistas_desc.items():
            pistas.setdefault(c, p)
        for c, p in pistas.items():
            if isinstance(p, dict) and isinstance(c, str) and c and not c.startswith("local:"):
                p = {k: v for k, v in p.items() if k != "archivo"}
                p["clave"] = c
                con.execute(f"INSERT OR {modo_pista} INTO pistas (clave, datos, actualizada) VALUES (?,?,?)",
                            (c, json.dumps(p, ensure_ascii=False), ahora))

        def datos_pista(c):
            p = pistas.get(c)
            return para_nube(p) if isinstance(p, dict) else {"clave": c}

        # me gusta
        for g in datos.get("me_gusta") or []:
            c = clave_aqui(g.get("clave") if isinstance(g, dict) else None)
            if not c:
                continue
            cur = con.execute("INSERT OR IGNORE INTO me_gusta (clave, fecha) VALUES (?,?)",
                              (c, _num(g.get("fecha"), ahora)))
            if cur.rowcount:
                cuenta["me_gusta"] += 1
                if c.startswith("yt:"):
                    nota("me_gusta_poner", {"clave": c, "datos": datos_pista(c)})

        # listas
        import uuid as _uuid
        for l in datos.get("listas") or []:
            if not isinstance(l, dict) or not str(l.get("nombre") or "").strip():
                continue
            nombre = str(l["nombre"]).strip()
            uuid = str(l.get("uuid") or "") or str(_uuid.uuid4())
            fila = con.execute("SELECT id, uuid, portada FROM listas WHERE uuid = ?", (uuid,)).fetchone()
            if fila is None:
                fila = con.execute("SELECT id, uuid, portada FROM listas WHERE nombre = ?", (nombre,)).fetchone()
            if fila is None:
                cur = con.execute(
                    "INSERT INTO listas (nombre, creada, descripcion, fijada, color, tocada, uuid, publica,"
                    " en_perfil) VALUES (?,?,?,?,?,?,?,?,?)",
                    (nombre, _num(l.get("creada"), ahora), l.get("descripcion") or "",
                     1 if l.get("fijada") else 0, l.get("color") or "", _num(l.get("tocada"), 0),
                     uuid, 1 if l.get("publica") else 0,
                     1 if (l.get("publica") and l.get("en_perfil")) else 0))
                lista_id, tenia_portada = cur.lastrowid, False
                cuenta["listas"] += 1
                nota("lista_poner", {"uuid": uuid, "nombre": nombre,
                                             "descripcion": l.get("descripcion") or "",
                                             "fijada": bool(l.get("fijada"))})
            else:
                lista_id, uuid = fila["id"], fila["uuid"] or uuid
                tenia_portada = bool(fila["portada"] and os.path.isfile(fila["portada"]))
            ya = {f["clave"] for f in con.execute("SELECT clave FROM lista_items WHERE lista_id = ?",
                                                  (lista_id,))}
            orden = con.execute("SELECT COALESCE(MAX(orden), 0) m FROM lista_items WHERE lista_id = ?",
                                (lista_id,)).fetchone()["m"]
            subir = []
            for it in sorted((i for i in l.get("items") or [] if isinstance(i, dict)),
                             key=lambda i: _num(i.get("orden"))):
                c = clave_aqui(it.get("clave"))
                if not c or c in ya:
                    continue
                ya.add(c)
                orden += 1
                con.execute("INSERT OR IGNORE INTO lista_items (lista_id, clave, orden, agregada) "
                            "VALUES (?,?,?,?)", (lista_id, c, orden, _num(it.get("agregada"), ahora)))
                cuenta["canciones_en_listas"] += 1
                if c.startswith("yt:"):
                    subir.append({"clave": c, "datos": datos_pista(c), "orden": orden})
            if subir:
                nota("items_poner", {"uuid": uuid, "items": subir})
            if l.get("portada") and l["portada"] in archivos and not tenia_portada:
                portadas_pendientes.append((lista_id, archivos[l["portada"]]))

        # escuchas (sin duplicar: misma canción a la misma hora = la misma escucha)
        vistas = set()
        if modo == "juntar":
            vistas = {(f["clave"], round(f["fecha"] or 0)) for f in
                      con.execute("SELECT clave, fecha FROM reproducciones")}
        for e in datos.get("escuchas") or []:
            if not isinstance(e, dict):
                continue
            c = clave_aqui(e.get("clave"))
            fecha = _num(e.get("fecha"), 0)
            if not c or not fecha or (c, round(fecha)) in vistas:
                continue
            vistas.add((c, round(fecha)))
            ctx = e.get("contexto")
            # nube_id -1: no se vuelve a subir a la cuenta (allí ya está o es solo de este equipo)
            con.execute("INSERT INTO reproducciones (clave, fecha, contexto, nube_id) VALUES (?,?,?,?)",
                        (c, fecha, json.dumps(ctx, ensure_ascii=False) if ctx else "", -1))
            cuenta["escuchas"] += 1

        for x in datos.get("contextos") or []:
            if isinstance(x, dict) and x.get("tipo") and x.get("id") is not None:
                previo = con.execute("SELECT fecha FROM contextos_recientes WHERE tipo = ? AND id = ?",
                                     (str(x["tipo"]), str(x["id"]))).fetchone()
                if previo is None or _num(previo["fecha"]) < _num(x.get("fecha")):
                    con.execute("INSERT OR REPLACE INTO contextos_recientes (tipo, id, datos, fecha) "
                                "VALUES (?,?,?,?)", (str(x["tipo"]), str(x["id"]),
                                                     json.dumps(x.get("datos") or {}, ensure_ascii=False),
                                                     _num(x.get("fecha"), ahora)))

        for g in datos.get("guardados") or []:
            if not isinstance(g, dict) or not g.get("tipo") or not g.get("id"):
                continue
            el = g.get("datos") or {}
            cur = con.execute("INSERT OR IGNORE INTO guardados (tipo, id, datos, fecha) VALUES (?,?,?,?)",
                              (str(g["tipo"]), str(g["id"]), json.dumps(el, ensure_ascii=False),
                               _num(g.get("fecha"), ahora)))
            if cur.rowcount:
                cuenta["guardados"] += 1
                if g["tipo"] in ("album", "lista", "artista"):
                    nota("guardado_poner", {"tipo": g["tipo"], "id": g["id"], "datos": el})

        for b in datos.get("busquedas") or []:
            texto = str((b or {}).get("texto") or "").strip() if isinstance(b, dict) else ""
            if texto:
                cur = con.execute("INSERT OR IGNORE INTO busquedas (texto, fecha) VALUES (?,?)",
                                  (texto, _num(b.get("fecha"), ahora)))
                cuenta["busquedas"] += cur.rowcount
        con.execute("DELETE FROM busquedas WHERE texto NOT IN "
                    "(SELECT texto FROM busquedas ORDER BY fecha DESC, rowid DESC LIMIT 30)")

        _restaurar_estado(con, datos.get("estado") or {},
                          (copia.origen if isinstance(copia, Copia) else APP), modo)
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:  # noqa: BLE001
            pass
        raise
    for ruta in portadas_viejas:
        try:
            os.remove(ruta)
        except (OSError, TypeError):
            pass
    for lista_id, b in portadas_pendientes:
        try:
            col.poner_portada_lista(lista_id, b)
        except Exception:  # noqa: BLE001 - una portada que no se abre no frena lo demás
            pass
    try:
        col.olvidar_memoria()
        col.invalidar_indice()
    except Exception:  # noqa: BLE001
        pass
    if getattr(col, "sincronizador", None) is not None:
        try:
            col.sincronizador.pronto()
        except Exception:  # noqa: BLE001
            pass
    return cuenta


def _restaurar_estado(con, estado, origen, modo):
    def leer(k):
        f = con.execute("SELECT valor FROM estado WHERE clave = ?", (k,)).fetchone()
        return _json(f["valor"]) if f else None

    def poner(k, v):
        con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES (?,?)",
                    (k, json.dumps(v, ensure_ascii=False)))
    for k in ESTADO_COPIABLE:
        if k not in estado:
            continue
        v = estado[k]
        if k == "saltos":
            if not isinstance(v, dict):
                continue
            actual = leer(k) if modo == "juntar" else None
            actual = actual if isinstance(actual, dict) else {}
            if origen == APP and not actual:
                poner(k, v)
                continue
            # de otro equipo solo sirven los saltos por canción (las demás claves difieren)
            canciones = dict(actual.get("canciones") or {})
            for vid, n in (v.get("canciones") or {}).items():
                canciones[vid] = max(int(_num(canciones.get(vid), 0)), int(_num(n, 0)))
            actual["canciones"] = canciones
            actual.setdefault("artistas", {})
            poner(k, actual)
        elif origen == APP and (modo == "reemplazar" or leer(k) is None):
            poner(k, v)


# ====================================================================== restaurar lo demás


def restaurar_extras(copia, modo="juntar", ajustes=None, carpeta=None, col=None, ctx=None,
                     con_ajustes=True):
    """Ajustes, ecualizador, estudio, gustos, mascota, fondo y archivos propios.
    Devuelve la lista de cosas que se aplicaron (para el aviso final)."""
    if carpeta is None:
        from .config import carpeta_perfil
        carpeta = carpeta_perfil()
    carpeta = Path(carpeta)
    datos = copia.datos
    hecho = []
    if con_ajustes and ajustes is not None and _restaurar_ajustes(ajustes, datos.get("ajustes") or {},
                                                                  copia.origen):
        hecho.append("ajustes")
    if _restaurar_estudio(carpeta, datos.get("estudio"), modo, ctx):
        hecho.append("estudio")
    if col is not None and _restaurar_gustos(col, datos.get("gustos"), modo, ctx):
        hecho.append("gustos")
    if con_ajustes:
        m = datos.get("mascota")
        if isinstance(m, str):
            gestor = getattr(ctx, "mascota", None) if ctx is not None else None
            if gestor is not None:
                if gestor.elegir(m):
                    hecho.append("mascota")
            else:
                try:
                    (carpeta / "mascota.json").write_text(json.dumps({"clave": m}), encoding="utf-8")
                    hecho.append("mascota")
                except OSError:
                    pass
        if _restaurar_fondo(carpeta, datos.get("fondo"), copia.archivos, ctx):
            hecho.append("fondo")
        if copia.origen == APP:
            for nombre, v in (datos.get("archivos_escritorio") or {}).items():
                if nombre in ARCHIVOS_ESCRITORIO and (modo == "reemplazar" or not (carpeta / nombre).exists()):
                    try:
                        (carpeta / nombre).write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
                        hecho.append(nombre)
                    except OSError:
                        pass
    return hecho


def _restaurar_ajustes(ajustes, bloque, origen):
    from .config import DEFECTOS
    valores = dict(bloque.get("comunes") or {})
    if origen == APP:
        valores.update(bloque.get("escritorio") or {})
    cambios = 0
    for k, v in valores.items():
        if k not in DEFECTOS or k in AJUSTES_FUERA:
            continue
        defecto = DEFECTOS[k]
        if k == "eq_bandas":
            if isinstance(v, str):
                v = _json(v, None)
            if not isinstance(v, list):
                continue
            v = [int(_num(x)) for x in v][:10]
        elif k == "carpeta":
            if not isinstance(v, str) or not os.path.isdir(v):
                continue      # la carpeta de descargas de otro equipo no existe aquí
        elif isinstance(defecto, bool):
            v = bool(v)
        elif isinstance(defecto, int):
            try:
                v = int(round(float(v)))
            except (TypeError, ValueError):
                continue
        elif isinstance(defecto, float):
            v = _num(v, defecto)
        elif isinstance(defecto, str):
            if not isinstance(v, (str, int, float)):
                continue
            v = str(v)
        ajustes[k] = v
        cambios += 1
    if cambios:
        ajustes.guardar()
    return cambios > 0


def _restaurar_estudio(carpeta, bloque, modo, ctx):
    if not isinstance(bloque, dict):
        return False
    from . import estudio as E
    ctrl = getattr(ctx, "estudio", None) if ctx is not None else None
    notas_obj = getattr(ctrl, "notas", None) or E.Notas(carpeta / "estudio_notas.json")
    est_obj = getattr(ctrl, "est", None) or E.Estadisticas(carpeta / "estudio_historial.json")
    nuevas = [{"id": str(n.get("id") or "") or os.urandom(6).hex(), "texto": str(n["texto"])[:4000],
               "fecha": str(n.get("fecha") or "")[:19]}
              for n in bloque.get("notas") or [] if isinstance(n, dict) and n.get("texto")]
    if modo == "reemplazar":
        lista = []
    else:
        lista = list(notas_obj.lista)
    vistas = {(str(n.get("texto") or "").strip(), str(n.get("fecha") or "")[:16]) for n in lista}
    ids = {n.get("id") for n in lista}
    for n in nuevas:
        clave = (n["texto"].strip(), n["fecha"][:16])
        if clave in vistas:
            continue
        vistas.add(clave)
        if n["id"] in ids:
            n["id"] = os.urandom(6).hex()
        ids.add(n["id"])
        lista.append(n)
    lista.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    notas_obj.lista = lista[:E.Notas.MAXIMO]
    E._escribir_json(notas_obj.ruta, notas_obj.lista)
    dias = {} if modo == "reemplazar" else dict(est_obj.dias)
    for k, v in (bloque.get("dias") or {}).items():
        try:
            dias[str(k)] = max(int(dias.get(str(k), 0)), int(v))
        except (TypeError, ValueError):
            pass
    est_obj.dias = dias
    if isinstance(bloque.get("sesiones"), list) and (modo == "reemplazar" or not est_obj.sesiones):
        est_obj.sesiones = list(bloque["sesiones"])[-200:]
    est_obj.guardar()
    cfg = bloque.get("config_escritorio")
    if isinstance(cfg, dict) and cfg:
        if ctrl is not None and getattr(ctrl, "cfg", None) is not None:
            for k, v in cfg.items():
                if k in E.DEFECTOS:
                    ctrl.cfg[k] = v
            ctrl.cfg.guardar()
        else:
            c = E.Configuracion(carpeta / "estudio.json")
            for k, v in cfg.items():
                if k in E.DEFECTOS:
                    c[k] = v
            c.guardar()
    return True


def _restaurar_gustos(col, bloque, modo, ctx):
    if not isinstance(bloque, dict):
        return False
    from . import gustos as G
    actual = col.estado(G.CLAVE) or {}
    previos = (actual.get("lista") or []) if (isinstance(actual, dict) and modo == "juntar") else []
    lista = G.limpiar(list(previos) + list(bloque.get("artistas") or []))
    con_cuenta = ctx is not None and (getattr(ctx, "cuenta", None) or {}).get("sesion") is not None
    col.guardar_estado(G.CLAVE, {"lista": lista,
                                 "elegidos": bool(bloque.get("elegidos")) or bool(actual.get("elegidos")),
                                 "pendiente": con_cuenta, "t": time.time()})
    return True


def _restaurar_fondo(carpeta, bloque, archivos, ctx):
    if not isinstance(bloque, dict):
        return False
    gestor = getattr(ctx, "fondo", None) if ctx is not None else None
    if gestor is None:
        return False          # sin el gestor (y su permiso de la cuenta) no se toca
    hecho = False
    try:
        if bloque.get("visible") is not None or bloque.get("desenfoque") is not None:
            gestor.poner_valores(visible=bloque.get("visible"), desenfoque=bloque.get("desenfoque"))
            gestor.guardar_ajustes()
            hecho = True
        img = archivos.get(bloque.get("imagen") or "")
        if img and getattr(gestor, "puede", False):
            gestor.poner_imagen(img)
            hecho = True
    except Exception:  # noqa: BLE001 - el fondo es un extra: no frena la restauración
        pass
    return hecho


# ====================================================================== copia automática


def ruta_config(carpeta=None):
    if carpeta is None:
        from .config import carpeta_perfil
        carpeta = carpeta_perfil()
    return Path(carpeta) / "copia_seguridad.json"


def carpeta_por_defecto():
    from .config import carpeta_perfil
    return str(carpeta_perfil() / "copias")


CONFIG_DEFECTO = {"automatica": False, "cada_dias": 7, "carpeta": "", "ultima": 0, "conservar": 5}


def leer_config(carpeta=None):
    d = dict(CONFIG_DEFECTO)
    guardado = _json(_leer_texto(ruta_config(carpeta)), {}) or {}
    if isinstance(guardado, dict):
        d.update({k: v for k, v in guardado.items() if k in CONFIG_DEFECTO})
    return d


def guardar_config(cfg, carpeta=None):
    try:
        ruta_config(carpeta).write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def toca_automatica(cfg, ahora=None):
    if not cfg.get("automatica"):
        return False
    dias = max(1, int(_num(cfg.get("cada_dias"), 7)))
    return (ahora or time.time()) - _num(cfg.get("ultima"), 0) >= dias * 86400


def podar_automaticas(carpeta, conservar=5):
    """Deja solo las `conservar` copias automáticas más nuevas (las hechas a mano no se tocan)."""
    try:
        # el nombre lleva la fecha (aaaa-mm-dd-hhmm): ordenar por nombre es ordenar por fecha
        autos = sorted(Path(carpeta).glob(f"Caudal-auto-*{EXTENSION}"), key=lambda p: p.name, reverse=True)
    except OSError:
        return
    for viejo in autos[max(1, int(conservar)):]:
        try:
            viejo.unlink()
        except OSError:
            pass


def hacer_automatica(col, ajustes, carpeta_perfil_=None, ahora=None, **extras):
    """Si toca, hace la copia automática. Devuelve la ruta o None."""
    cfg = leer_config(carpeta_perfil_)
    if not toca_automatica(cfg, ahora):
        return None
    destino = Path(cfg.get("carpeta") or (Path(carpeta_perfil_) / "copias" if carpeta_perfil_
                                          else carpeta_por_defecto()))
    contenido = crear_copia(col, ajustes, carpeta_perfil_, **extras)
    ruta = guardar_copia(destino / nombre_sugerido(True, ahora), contenido)
    cfg["ultima"] = ahora or time.time()
    guardar_config(cfg, carpeta_perfil_)
    podar_automaticas(destino, cfg.get("conservar", 5))
    return ruta


def extras_de(ctx):
    """Mascota y fondo tal como los tiene la app abierta (si los gestores existen)."""
    extras = {}
    m = getattr(ctx, "mascota", None)
    if m is not None:
        extras["mascota"] = getattr(m, "clave", "") or ""
    return extras


def programar_automatica(ctx, intervalo_ms=6 * 3600 * 1000):
    """Engancha la copia automática a la app abierta: mira al arrancar (con un minuto de margen
    para no estorbar) y luego cada pocas horas. Todo en segundo plano."""
    from PySide6.QtCore import QTimer
    from .config import carpeta_perfil
    from .hilos import en_segundo_plano
    carpeta = carpeta_perfil()

    def revisar():
        if not toca_automatica(leer_config(carpeta)):
            return
        extras = extras_de(ctx)

        def trabajo():
            with ctx.coleccion.copia_de_lectura() as c:
                return hacer_automatica(c, ctx.ajustes, carpeta, **extras)
        en_segundo_plano(trabajo, ok=lambda _r: None, error=lambda _e: None)

    reloj = QTimer(ctx)
    reloj.setInterval(intervalo_ms)
    reloj.timeout.connect(revisar)
    reloj.start()
    QTimer.singleShot(60 * 1000, revisar)
    ctx._reloj_copia = reloj
    return reloj
