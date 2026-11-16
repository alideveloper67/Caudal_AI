# -*- coding: utf-8 -*-
"""Tu coleccion: me gusta, listas, escuchado hace poco, artistas y albumes guardados.

Vive en la misma base que el historial de descargas (historial.db) y convive con
ella: una pista puede ser de YouTube ("yt:<id>") o un archivo descargado
("local:<id de la descarga>"). Las listas mezclan las dos cosas.
"""

import json
import os
import re
import sqlite3
import time
from pathlib import Path

from .config import carpeta_datos, carpeta_perfil


def _video_id_de_url(url):
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else ""


def pista_de_descarga(fila):
    """Una fila del historial de descargas, como pista reproducible."""
    autor = fila.get("autor") or ""
    url = fila.get("url") or ""
    vid = _video_id_de_url(url)
    return {
        "tipo": "pista",
        "clave": f"local:{fila['id']}",
        "descarga_id": fila["id"],
        "video_id": vid,
        "titulo": fila.get("titulo") or os.path.basename(fila.get("archivo") or "") or "Sin título",
        "artistas": [{"nombre": autor, "id": ""}] if autor else [],
        "artista": autor or fila.get("plataforma") or "",
        "album": {},
        "duracion": int(fila.get("duracion") or 0),
        "miniatura": fila.get("caratula") or "",
        "archivo": fila.get("archivo") or "",
        "es_audio": bool(fila.get("es_audio")),
        "es_video": not bool(fila.get("es_audio")),
        "url": url,
        "calidad": fila.get("calidad") or "",
        "tamano": fila.get("tamano") or 0,
        "plataforma": fila.get("plataforma") or "",
        "fecha": fila.get("fecha") or 0,
    }


class Coleccion:
    def __init__(self, archivo=None):
        self.archivo = Path(archivo) if archivo else carpeta_perfil() / "historial.db"
        self.con = sqlite3.connect(str(self.archivo), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self._indice_local = None
        self._existe_cache = {}
        self._gustan = None
        self.sincronizador = None       # lo pone main al entrar con una cuenta
        self._crear()
        try:
            self.con.execute("PRAGMA journal_mode=WAL")   # leer mientras se sincroniza
        except sqlite3.DatabaseError:
            pass

    # ------------------------------------------------------------ esquema

    def _crear(self):
        c = self.con
        c.execute("""CREATE TABLE IF NOT EXISTS descargas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, titulo TEXT,
            plataforma TEXT, archivo TEXT, tamano INTEGER DEFAULT 0,
            duracion INTEGER DEFAULT 0, calidad TEXT, estado TEXT, fecha REAL,
            caratula TEXT, es_audio INTEGER DEFAULT 0, autor TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS pistas (
            clave TEXT PRIMARY KEY, datos TEXT NOT NULL, actualizada REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS me_gusta (
            clave TEXT PRIMARY KEY, fecha REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS listas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, creada REAL)""")
        columnas = {f["name"] for f in c.execute("PRAGMA table_info(listas)").fetchall()}
        for col, tipo in (("descripcion", "TEXT DEFAULT ''"), ("fijada", "INTEGER DEFAULT 0"),
                          ("color", "TEXT DEFAULT ''"), ("tocada", "REAL DEFAULT 0"),
                          ("uuid", "TEXT"), ("portada", "TEXT")):
            if col not in columnas:
                c.execute(f"ALTER TABLE listas ADD COLUMN {col} {tipo}")
        c.execute("""CREATE TABLE IF NOT EXISTS lista_items (
            lista_id INTEGER NOT NULL, clave TEXT NOT NULL, orden REAL DEFAULT 0,
            agregada REAL, PRIMARY KEY (lista_id, clave))""")
        c.execute("""CREATE TABLE IF NOT EXISTS reproducciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, fecha REAL,
            contexto TEXT DEFAULT '')""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_repro_fecha ON reproducciones(fecha DESC)")
        if "nube_id" not in {f["name"] for f in c.execute("PRAGMA table_info(reproducciones)")}:
            c.execute("ALTER TABLE reproducciones ADD COLUMN nube_id INTEGER")
        c.execute("""CREATE TABLE IF NOT EXISTS pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, op TEXT NOT NULL, datos TEXT NOT NULL,
            creada REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS guardados (
            tipo TEXT NOT NULL, id TEXT NOT NULL, datos TEXT NOT NULL, fecha REAL,
            PRIMARY KEY (tipo, id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS contextos_recientes (
            tipo TEXT NOT NULL, id TEXT NOT NULL, datos TEXT NOT NULL, fecha REAL,
            PRIMARY KEY (tipo, id))""")
        c.execute("""CREATE TABLE IF NOT EXISTS busquedas (
            texto TEXT PRIMARY KEY, fecha REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS estado (
            clave TEXT PRIMARY KEY, valor TEXT)""")
        c.commit()
        self._migrar_listas_viejas()

    def _migrar_listas_viejas(self):
        """Las listas de versiones anteriores apuntaban a ids de descargas."""
        existe = self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='lista_canciones'"
        ).fetchone()
        if not existe:
            return
        if self.estado("listas_migradas"):
            return
        for f in self.con.execute("SELECT * FROM lista_canciones").fetchall():
            self.con.execute(
                "INSERT OR IGNORE INTO lista_items (lista_id, clave, orden, agregada)"
                " VALUES (?,?,?,?)",
                (f["lista_id"], f"local:{f['descarga_id']}", f["orden"], time.time()))
        self.con.commit()
        self.guardar_estado("listas_migradas", True)

    # ------------------------------------------------------------ nube

    def _anotar(self, op, datos):
        """Deja una orden para la nube; el sincronizador la envia cuando puede."""
        if self.sincronizador is None:
            return
        self.con.execute("INSERT INTO pendientes (op, datos, creada) VALUES (?,?,?)",
                         (op, json.dumps(datos, ensure_ascii=False), time.time()))
        self.con.commit()
        self.sincronizador.pronto()

    def olvidar_memoria(self):
        """Tras traer cambios de otros dispositivos."""
        self._gustan = None
        self._indice_local = None

    def _uuid_lista(self, lista_id):
        f = self.con.execute("SELECT uuid FROM listas WHERE id = ?", (lista_id,)).fetchone()
        if not f:
            return None
        if f["uuid"]:
            return f["uuid"]
        import uuid as _uuid
        nuevo = str(_uuid.uuid4())
        self.con.execute("UPDATE listas SET uuid = ? WHERE id = ?", (nuevo, lista_id))
        self.con.commit()
        return nuevo

    def _anotar_lista(self, lista_id):
        l = self.lista(lista_id)
        if l:
            self._anotar("lista_poner", {"uuid": self._uuid_lista(lista_id), "nombre": l["nombre"],
                                         "descripcion": l.get("descripcion") or "",
                                         "fijada": bool(l.get("fijada"))})

    # ------------------------------------------------------------ pistas

    def recordar(self, pista):
        """Guarda los datos de una pista en linea para poder pintarla sin internet."""
        if not pista or not pista.get("clave") or pista["clave"].startswith("local:"):
            return
        datos = {k: v for k, v in pista.items() if k not in ("archivo",)}
        self.con.execute(
            "INSERT OR REPLACE INTO pistas (clave, datos, actualizada) VALUES (?,?,?)",
            (pista["clave"], json.dumps(datos, ensure_ascii=False), time.time()))
        self.con.commit()

    def pista(self, clave):
        if not clave:
            return None
        if clave.startswith("local:"):
            try:
                ident = int(clave.split(":", 1)[1])
            except ValueError:
                return None
            f = self.con.execute("SELECT * FROM descargas WHERE id = ?", (ident,)).fetchone()
            return pista_de_descarga(dict(f)) if f else None
        f = self.con.execute("SELECT datos FROM pistas WHERE clave = ?", (clave,)).fetchone()
        if not f:
            return None
        try:
            return json.loads(f["datos"])
        except ValueError:
            return None

    def pistas(self, claves):
        salida = []
        for c in claves:
            p = self.pista(c)
            if p:
                salida.append(p)
        return salida

    # ------------------------------------------------------------ descargas locales

    def descargadas(self, solo_audio=None, filtro=""):
        donde = ["estado = 'completada'", "archivo IS NOT NULL", "archivo != ''"]
        args = []
        if solo_audio is not None:
            donde.append("es_audio = ?")
            args.append(1 if solo_audio else 0)
        if filtro.strip():
            donde.append("(titulo LIKE ? OR autor LIKE ? OR plataforma LIKE ?)")
            patron = f"%{filtro.strip()}%"
            args += [patron, patron, patron]
        filas = self.con.execute(
            f"SELECT * FROM descargas WHERE {' AND '.join(donde)} ORDER BY fecha DESC",
            args).fetchall()
        return [pista_de_descarga(dict(f)) for f in filas
                if f["archivo"] and os.path.exists(f["archivo"])]

    def invalidar_indice(self):
        self._indice_local = None
        self._existe_cache.clear()

    def _existe(self, ruta):
        """os.path.exists con memoria de 20 s: las filas se repintan sin tocar el disco."""
        ahora = time.time()
        dato = self._existe_cache.get(ruta)
        if dato is not None and ahora - dato[1] < 20:
            return dato[0]
        existe = bool(ruta) and os.path.exists(ruta)
        if len(self._existe_cache) > 5000:
            self._existe_cache.clear()
        self._existe_cache[ruta] = (existe, ahora)
        return existe

    def _indice(self):
        if self._indice_local is None:
            indice = {}
            for f in self.con.execute(
                    "SELECT id, url, archivo, es_audio FROM descargas "
                    "WHERE estado='completada' AND archivo != '' ORDER BY fecha DESC").fetchall():
                vid = _video_id_de_url(f["url"])
                if vid:
                    indice.setdefault(vid, []).append((f["archivo"], bool(f["es_audio"]), f["id"]))
            self._indice_local = indice
        return self._indice_local

    def copia_local(self, video_id, querer_video=False):
        """Archivo ya descargado de ese video, si lo hay: asi suena sin internet."""
        if not video_id:
            return None
        candidatos = [c for c in self._indice().get(video_id, []) if self._existe(c[0])]
        if not candidatos:
            return None
        if querer_video:
            con_video = [c for c in candidatos if not c[1]]
            return con_video[0] if con_video else None
        audio = [c for c in candidatos if c[1]]
        return (audio or candidatos)[0]

    def esta_descargada(self, pista):
        if not pista:
            return False
        if pista.get("archivo"):
            return self._existe(pista["archivo"])
        return self.copia_local(pista.get("video_id")) is not None

    # ------------------------------------------------------------ me gusta

    def me_gusta(self, clave):
        if self._gustan is None:
            self._gustan = {f["clave"] for f in self.con.execute("SELECT clave FROM me_gusta")}
        return clave in self._gustan

    def alternar_me_gusta(self, pista):
        clave = pista.get("clave")
        if not clave:
            return False
        if self.me_gusta(clave):
            self.con.execute("DELETE FROM me_gusta WHERE clave = ?", (clave,))
            self.con.commit()
            self._gustan.discard(clave)
            if clave.startswith("yt:"):
                self._anotar("me_gusta_quitar", {"clave": clave})
            return False
        self.recordar(pista)
        self.con.execute("INSERT OR REPLACE INTO me_gusta (clave, fecha) VALUES (?,?)",
                         (clave, time.time()))
        self.con.commit()
        self._gustan.add(clave)
        if clave.startswith("yt:"):
            self._anotar("me_gusta_poner", {"clave": clave, "datos": para_nube(pista)})
        return True

    def lista_me_gusta(self, filtro=""):
        claves = [f["clave"] for f in self.con.execute(
            "SELECT clave FROM me_gusta ORDER BY fecha DESC").fetchall()]
        pistas = self.pistas(claves)
        return _filtrar(pistas, filtro)

    def total_me_gusta(self):
        return self.con.execute("SELECT COUNT(*) n FROM me_gusta").fetchone()["n"]

    # ------------------------------------------------------------ listas

    def listas(self, filtro=""):
        sql = ("SELECT l.*, COUNT(i.clave) n FROM listas l "
               "LEFT JOIN lista_items i ON i.lista_id = l.id ")
        args = []
        if filtro.strip():
            sql += "WHERE l.nombre LIKE ? "
            args.append(f"%{filtro.strip()}%")
        sql += "GROUP BY l.id ORDER BY l.fijada DESC, l.tocada DESC, l.nombre COLLATE NOCASE"
        return [dict(f) for f in self.con.execute(sql, args).fetchall()]

    def lista(self, lista_id):
        f = self.con.execute("SELECT * FROM listas WHERE id = ?", (lista_id,)).fetchone()
        return dict(f) if f else None

    def crear_lista(self, nombre, descripcion=""):
        nombre = (nombre or "").strip()
        if not nombre:
            raise ValueError("La lista necesita un nombre.")
        if self.con.execute("SELECT 1 FROM listas WHERE nombre = ?", (nombre,)).fetchone():
            raise ValueError("Ya tienes una lista con ese nombre.")
        import uuid as _uuid
        cur = self.con.execute(
            "INSERT INTO listas (nombre, creada, descripcion, tocada, uuid) VALUES (?,?,?,?,?)",
            (nombre, time.time(), descripcion, time.time(), str(_uuid.uuid4())))
        self.con.commit()
        self._anotar_lista(cur.lastrowid)
        return cur.lastrowid

    def nombre_libre(self, base="Mi lista"):
        n = 1
        while True:
            nombre = f"{base} n.º {n}"
            if not self.con.execute("SELECT 1 FROM listas WHERE nombre = ?", (nombre,)).fetchone():
                return nombre
            n += 1

    def editar_lista(self, lista_id, nombre=None, descripcion=None, fijada=None):
        if nombre is not None:
            nombre = nombre.strip()
            if not nombre:
                raise ValueError("La lista necesita un nombre.")
            otra = self.con.execute("SELECT id FROM listas WHERE nombre = ? AND id != ?",
                                    (nombre, lista_id)).fetchone()
            if otra:
                raise ValueError("Ya tienes una lista con ese nombre.")
            self.con.execute("UPDATE listas SET nombre = ? WHERE id = ?", (nombre, lista_id))
        if descripcion is not None:
            self.con.execute("UPDATE listas SET descripcion = ? WHERE id = ?",
                             (descripcion, lista_id))
        if fijada is not None:
            self.con.execute("UPDATE listas SET fijada = ? WHERE id = ?",
                             (1 if fijada else 0, lista_id))
        self.con.commit()
        self._anotar_lista(lista_id)

    def borrar_lista(self, lista_id):
        self._borrar_archivo_portada(lista_id)
        u = self._uuid_lista(lista_id)
        if u:
            self._anotar("lista_borrar", {"uuid": u})
        self.con.execute("DELETE FROM lista_items WHERE lista_id = ?", (lista_id,))
        self.con.execute("DELETE FROM listas WHERE id = ?", (lista_id,))
        self.con.commit()

    def agregar_a_lista(self, lista_id, pistas):
        """Anade al final; devuelve cuantas eran nuevas."""
        if isinstance(pistas, dict):
            pistas = [pistas]
        f = self.con.execute("SELECT COALESCE(MAX(orden), 0) m FROM lista_items WHERE lista_id = ?",
                             (lista_id,)).fetchone()
        orden = f["m"]
        nuevas = 0
        para_subir = []
        for p in pistas:
            if not p.get("clave"):
                continue
            self.recordar(p)
            orden += 1
            cur = self.con.execute(
                "INSERT OR IGNORE INTO lista_items (lista_id, clave, orden, agregada)"
                " VALUES (?,?,?,?)", (lista_id, p["clave"], orden, time.time()))
            nuevas += cur.rowcount
            if cur.rowcount and p["clave"].startswith("yt:"):
                para_subir.append({"clave": p["clave"], "datos": para_nube(p), "orden": orden})
        self.con.execute("UPDATE listas SET tocada = ? WHERE id = ?", (time.time(), lista_id))
        self.con.commit()
        if para_subir:
            self._anotar("items_poner", {"uuid": self._uuid_lista(lista_id), "items": para_subir})
        return nuevas

    def quitar_de_lista(self, lista_id, clave):
        self.con.execute("DELETE FROM lista_items WHERE lista_id = ? AND clave = ?",
                         (lista_id, clave))
        self.con.commit()
        if clave.startswith("yt:"):
            self._anotar("item_quitar", {"uuid": self._uuid_lista(lista_id), "clave": clave})

    def mover_en_lista(self, lista_id, claves_en_orden):
        for i, clave in enumerate(claves_en_orden):
            self.con.execute("UPDATE lista_items SET orden = ? WHERE lista_id = ? AND clave = ?",
                             (i + 1, lista_id, clave))
        self.con.commit()
        items = [{"clave": c, "datos": para_nube(self.pista(c) or {}), "orden": i + 1}
                 for i, c in enumerate(claves_en_orden) if c.startswith("yt:")]
        if items:
            self._anotar("items_poner", {"uuid": self._uuid_lista(lista_id), "items": items})

    def pistas_de_lista(self, lista_id, filtro=""):
        claves = [f["clave"] for f in self.con.execute(
            "SELECT clave FROM lista_items WHERE lista_id = ? ORDER BY orden", (lista_id,))]
        return _filtrar(self.pistas(claves), filtro)

    def listas_con(self, clave):
        return {f["lista_id"] for f in self.con.execute(
            "SELECT lista_id FROM lista_items WHERE clave = ?", (clave,))}

    # ---- portada personalizada (solo local: no se sincroniza con la nube)

    def carpeta_portadas(self):
        ruta = self.archivo.parent / "portadas_listas"
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta

    def portada_personalizada(self, lista_id):
        """Ruta de la portada elegida por la persona, o "" si no hay (o el archivo se perdio)."""
        f = self.con.execute("SELECT portada FROM listas WHERE id = ?", (lista_id,)).fetchone()
        ruta = (f["portada"] if f else "") or ""
        return ruta if ruta and os.path.isfile(ruta) else ""

    def _borrar_archivo_portada(self, lista_id):
        f = self.con.execute("SELECT portada FROM listas WHERE id = ?", (lista_id,)).fetchone()
        if f and f["portada"]:
            try:
                os.remove(f["portada"])
            except OSError:
                pass

    def poner_portada_lista(self, lista_id, origen):
        """Pone la imagen elegida (ruta o bytes): recorte cuadrado al centro, 800 px, JPEG.
        Devuelve la ruta guardada. Lanza ValueError si la imagen no se puede abrir."""
        if not self.lista(lista_id):
            raise ValueError("Esa lista ya no existe.")
        from . import social
        try:
            datos = social.preparar_portada(origen)
        except Exception as e:      # ErrorNube: imagen ilegible
            raise ValueError(str(e) or "No se pudo abrir esa imagen.") from e
        nueva = self.carpeta_portadas() / f"{lista_id}_{int(time.time() * 1000)}.jpg"
        nueva.write_bytes(datos)
        self._borrar_archivo_portada(lista_id)
        self.con.execute("UPDATE listas SET portada = ? WHERE id = ?", (str(nueva), lista_id))
        self.con.commit()
        return str(nueva)

    def quitar_portada_lista(self, lista_id):
        self._borrar_archivo_portada(lista_id)
        self.con.execute("UPDATE listas SET portada = NULL WHERE id = ?", (lista_id,))
        self.con.commit()

    def portadas_de_lista(self, lista_id, n=4):
        """Portada personalizada (1 ruta local) si la hay; si no, hasta cuatro para el mosaico."""
        propia = self.portada_personalizada(lista_id)
        if propia:
            return [propia]
        salida = []
        for p in self.pistas_de_lista(lista_id)[:40]:
            m = p.get("miniatura")
            if m and m not in salida:
                salida.append(m)
            if len(salida) >= n:
                break
        return salida

    # ------------------------------------------------------------ guardados

    def guardar(self, elemento):
        """Guarda un album, lista de YouTube o artista en tu biblioteca."""
        tipo, ident = elemento.get("tipo"), elemento.get("id")
        if not tipo or not ident:
            return
        datos = {k: v for k, v in elemento.items() if k not in ("pistas", "secciones")}
        self.con.execute("INSERT OR REPLACE INTO guardados (tipo, id, datos, fecha) VALUES (?,?,?,?)",
                         (tipo, ident, json.dumps(datos, ensure_ascii=False), time.time()))
        self.con.commit()
        if tipo in ("album", "lista", "artista"):
            self._anotar("guardado_poner", {"tipo": tipo, "id": ident, "datos": datos})

    def olvidar(self, tipo, ident):
        self.con.execute("DELETE FROM guardados WHERE tipo = ? AND id = ?", (tipo, ident))
        self.con.commit()
        if tipo in ("album", "lista", "artista"):
            self._anotar("guardado_quitar", {"tipo": tipo, "id": ident})

    def guardado(self, tipo, ident):
        return bool(self.con.execute("SELECT 1 FROM guardados WHERE tipo = ? AND id = ?",
                                     (tipo, ident)).fetchone())

    def guardados(self, tipo=None):
        if tipo:
            filas = self.con.execute("SELECT datos FROM guardados WHERE tipo = ? ORDER BY fecha DESC",
                                     (tipo,)).fetchall()
        else:
            filas = self.con.execute("SELECT datos FROM guardados ORDER BY fecha DESC").fetchall()
        salida = []
        for f in filas:
            try:
                salida.append(json.loads(f["datos"]))
            except ValueError:
                pass
        return salida

    # ------------------------------------------------------------ escuchas

    def registrar_escucha(self, pista, contexto=None):
        if not pista or not pista.get("clave"):
            return
        self.recordar(pista)
        ahora = time.time()
        en_nube = self.sincronizador is not None and pista["clave"].startswith("yt:")
        self.con.execute("INSERT INTO reproducciones (clave, fecha, contexto, nube_id) VALUES (?,?,?,?)",
                         (pista["clave"], ahora,
                          json.dumps(contexto, ensure_ascii=False) if contexto else "",
                          -1 if en_nube else None))
        if en_nube:
            self._anotar("escucha", {"clave": pista["clave"], "datos": para_nube(pista),
                                     "contexto": contexto, "fecha": ahora})
        if contexto and contexto.get("tipo") and contexto.get("id") is not None:
            self.con.execute(
                "INSERT OR REPLACE INTO contextos_recientes (tipo, id, datos, fecha) VALUES (?,?,?,?)",
                (contexto["tipo"], str(contexto["id"]),
                 json.dumps(contexto, ensure_ascii=False), time.time()))
            if contexto["tipo"] == "mi_lista":
                self.con.execute("UPDATE listas SET tocada = ? WHERE id = ?",
                                 (time.time(), contexto["id"]))
        self.con.commit()

    def escuchado_hace_poco(self, n=30):
        filas = self.con.execute(
            "SELECT clave, MAX(fecha) f FROM reproducciones GROUP BY clave ORDER BY f DESC LIMIT ?",
            (n,)).fetchall()
        return self.pistas([f["clave"] for f in filas])

    def contextos_recientes(self, n=12):
        salida = []
        for f in self.con.execute(
                "SELECT datos FROM contextos_recientes ORDER BY fecha DESC LIMIT ?", (n,)):
            try:
                salida.append(json.loads(f["datos"]))
            except ValueError:
                pass
        return salida

    def mas_escuchadas(self, n=25, dias=60):
        desde = time.time() - dias * 86400
        filas = self.con.execute(
            "SELECT clave, COUNT(*) veces FROM reproducciones WHERE fecha > ? "
            "GROUP BY clave ORDER BY veces DESC LIMIT ?", (desde, n)).fetchall()
        return self.pistas([f["clave"] for f in filas])

    def artistas_frecuentes(self, n=10):
        """Artistas que mas escuchas, a partir de tus reproducciones y me gusta."""
        cuenta = {}
        for p in self.mas_escuchadas(80, 120) + self.lista_me_gusta()[:80]:
            for a in p.get("artistas") or []:
                if a.get("id"):
                    clave = (a["id"], a["nombre"])
                    cuenta[clave] = cuenta.get(clave, 0) + 1
        orden = sorted(cuenta.items(), key=lambda x: -x[1])[:n]
        return [{"id": k[0], "nombre": k[1]} for k, _ in orden]

    def borrar_escuchas(self):
        self.con.execute("DELETE FROM reproducciones")
        self.con.execute("DELETE FROM contextos_recientes")
        self.con.commit()

    # ------------------------------------------------------------ busquedas

    def anotar_busqueda(self, texto):
        texto = (texto or "").strip()
        if not texto:
            return
        self.con.execute("INSERT OR REPLACE INTO busquedas (texto, fecha) VALUES (?,?)",
                         (texto, time.time()))
        self.con.execute("DELETE FROM busquedas WHERE texto NOT IN "
                         "(SELECT texto FROM busquedas ORDER BY fecha DESC LIMIT 30)")
        self.con.commit()

    def busquedas_recientes(self, n=12):
        return [f["texto"] for f in self.con.execute(
            "SELECT texto FROM busquedas ORDER BY fecha DESC LIMIT ?", (n,))]

    def borrar_busquedas(self):
        self.con.execute("DELETE FROM busquedas")
        self.con.commit()

    # ------------------------------------------------------------ estado

    def guardar_estado(self, clave, valor):
        self.con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES (?,?)",
                         (clave, json.dumps(valor, ensure_ascii=False)))
        self.con.commit()

    def estado(self, clave, defecto=None):
        f = self.con.execute("SELECT valor FROM estado WHERE clave = ?", (clave,)).fetchone()
        if not f:
            return defecto
        try:
            return json.loads(f["valor"])
        except ValueError:
            return defecto


def para_nube(pista):
    """Lo que se comparte de una pista: sin rutas de este equipo."""
    fuera = {"archivo", "descarga_id", "es_audio", "tamano", "calidad", "fecha", "url"}
    return {k: v for k, v in (pista or {}).items()
            if k not in fuera and not str(k).startswith("_")}


def _filtrar(pistas, filtro):
    filtro = (filtro or "").strip().lower()
    if not filtro:
        return pistas
    return [p for p in pistas
            if filtro in (p.get("titulo") or "").lower()
            or filtro in (p.get("artista") or "").lower()
            or filtro in ((p.get("album") or {}).get("nombre") or "").lower()]
