# -*- coding: utf-8 -*-
"""Sincronizacion de la biblioteca con la nube (Supabase).

La biblioteca local (SQLite) es la que usa la interfaz: rapida y sin internet.
Cada cambio local deja una orden en la tabla `pendientes`; un hilo las envia
en orden cuando hay conexion y despues trae lo que se cambio en otros
dispositivos. Si no hay red, las ordenes esperan y se envian luego.

La primera vez que una cuenta entra en este equipo se sube lo que ya habia.
"""

import json
import os
import sqlite3
import threading
import time
import uuid

from PySide6.QtCore import QObject, QTimer, Signal

from .hilos import en_segundo_plano
from .nube import ErrorNube, SinConexion

CADA = 3 * 60 * 1000          # traer cambios de otros dispositivos cada 3 minutos

# Ajustes que valen igual en todos los dispositivos de la cuenta (misma lista
# que Ajustes.compartidos de la app movil: si se toca una, tocar la otra).
COMPARTIDOS = (
    "region", "calidad_audio", "calidad_video", "codec_video", "normalizar", "super_volumen",
    "ecualizador", "eq_bandas", "eq_preset", "autoplay", "sponsorblock", "sponsorblock_videos",
    "formato_audio", "bitrate_mp3", "crossfade",
    "descarga_inteligente", "descarga_inteligente_gb", "transicion_dj", "apagado_suave",
)


def ajustes_compartidos(ajustes):
    """Los ajustes comunes, listos para la nube (eq_bandas siempre como lista)."""
    salida = {}
    for k in COMPARTIDOS:
        if k not in ajustes:
            continue
        v = ajustes[k]
        if k == "eq_bandas" and isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                continue
        salida[k] = v
    return salida


def huella_ajustes(datos):
    return json.dumps(datos, sort_keys=True, ensure_ascii=False)


def nuevo_uuid():
    return str(uuid.uuid4())


def _q(valor):
    """Valor para un filtro de PostgREST (eq.)."""
    return str(valor).replace(",", "%2C").replace("(", "%28").replace(")", "%29")


class Sincronizador(QObject):
    cambio_remoto = Signal()        # llegaron cambios: la interfaz se refresca
    ajustes_remotos = Signal(dict)  # otro dispositivo cambio los ajustes comunes
    estado = Signal(str)            # "sincronizado" | "pendiente" | "sin_conexion" | "error"

    def __init__(self, coleccion, cuenta, al_renovar=None, padre=None, ajustes=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.coleccion = coleccion
        self.cuenta = cuenta
        self.sesion = cuenta.get("sesion")
        self.al_renovar = al_renovar
        self.archivo = str(coleccion.archivo)
        self._corriendo = False
        self._otra_vez = False
        self._otra_completa = False
        self._cerrojo = threading.Lock()
        self._envio = threading.RLock()     # un solo envío de pendientes a la vez
        self.ultimo_estado = ""
        self._reloj = QTimer(self)
        self._reloj.setInterval(CADA)
        self._reloj.timeout.connect(self.completa)
        self._pronto = QTimer(self)
        self._pronto.setSingleShot(True)
        self._pronto.setInterval(1500)
        self._pronto.timeout.connect(self.ligera)

    def iniciar(self):
        if not self.sesion:
            return
        self._reloj.start()
        QTimer.singleShot(800, self.completa)

    def pronto(self):
        """Un cambio local: se envia en un momento (se agrupan los seguidos).
        Solo SE ENVÍA lo pendiente: no se vuelve a bajar toda la biblioteca."""
        self._pronto.start()

    def ligera(self):
        self.ya(False)

    def completa(self):
        """Envía y además baja los cambios de otros dispositivos (arranque, cada 3 minutos, refrescar)."""
        self.ya(True)

    def ya(self, completo=True):
        if not self.sesion:
            return
        if self._corriendo:
            self._otra_vez = True
            self._otra_completa = self._otra_completa or completo
            return
        self._corriendo = True
        en_segundo_plano(self._ciclo, completo, ok=self._terminado, error=self._fallo, dueno=self)

    def enviar_ahora(self):
        """Sube ya lo pendiente (bloquea: llamar en segundo plano). Hace falta antes de compartir una
        lista, que tiene que existir en la nube para poder tener código."""
        if not self.sesion:
            return
        con = self._abrir()
        try:
            with self._envio:
                self._enviar_pendientes(con)
        finally:
            con.close()

    def refrescar_lista(self, lista_uuid):
        """Trae solo los cambios de UNA lista (una lista abierta que otras personas también editan)."""
        if not self.sesion or not lista_uuid:
            return
        en_segundo_plano(self._traer_una, lista_uuid,
                         ok=lambda hay: hay and (self.coleccion.olvidar_memoria(), self.cambio_remoto.emit()),
                         error=lambda _e: None, dueno=self)

    def _terminado(self, resultado):
        cambio, remotos = resultado
        self._corriendo = False
        if remotos and self.ajustes is not None:
            for k, v in remotos.items():
                self.ajustes[k] = v
            self.ajustes.guardar()
            self.ajustes_remotos.emit(remotos)
        self._fijar("sincronizado")
        if self.al_renovar:
            self.al_renovar()
        if cambio:
            self.coleccion.olvidar_memoria()
            self.cambio_remoto.emit()
        if self._otra_vez:
            self._otra_vez = False
            completa, self._otra_completa = self._otra_completa, False
            if completa:
                QTimer.singleShot(0, self.completa)
            else:
                self.pronto()

    def _fallo(self, e):
        self._corriendo = False
        self._fijar("sin_conexion" if isinstance(e, SinConexion) else "error")
        if self._otra_vez:
            self._otra_vez = False
            self._otra_completa = False
            QTimer.singleShot(20000, self.completa)

    def _fijar(self, estado):
        if estado != self.ultimo_estado:
            self.ultimo_estado = estado
            self.estado.emit(estado)

    # ------------------------------------------------------------ en el hilo

    def _ciclo(self, completo=True):
        con = self._abrir()
        try:
            uid = self.sesion.user_id
            marca = con.execute("SELECT valor FROM estado WHERE clave = 'nube_usuario'").fetchone()
            with self._envio:
                if not marca or json.loads(marca["valor"]) != uid:
                    self._subida_inicial(con)
                    con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('nube_usuario', ?)",
                                (json.dumps(uid),))
                    con.commit()
                    completo = True
                self._enviar_pendientes(con)
            cambio = self._traer(con) if completo else False
            return cambio, self._sincronizar_ajustes(con, forzar=completo)
        finally:
            con.close()

    def _abrir(self):
        con = sqlite3.connect(self.archivo, timeout=15)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA synchronous=NORMAL")    # con WAL es seguro y cada confirmación no espera al disco
        except sqlite3.DatabaseError:
            pass
        return con

    def _upsert(self, tabla, filas, conflicto):
        if not filas:
            return
        for i in range(0, len(filas), 400):
            self.sesion.pedir("POST", f"{tabla}?on_conflict={conflicto}",
                              json=filas[i:i + 400],
                              cabeceras={"Prefer": "resolution=merge-duplicates,return=minimal"})

    def _subida_inicial(self, con):
        """Lo que ya habia en este equipo pasa a la cuenta (sin pisar lo de la nube)."""
        pistas = {f["clave"]: json.loads(f["datos"])
                  for f in con.execute("SELECT clave, datos FROM pistas")}
        gustan = [{"clave": f["clave"], "datos": pistas.get(f["clave"], {}),
                   "fecha": _iso(f["fecha"])}
                  for f in con.execute("SELECT clave, fecha FROM me_gusta")
                  if f["clave"].startswith("yt:")]
        self._upsert("me_gusta", gustan, "user_id,clave")
        for l in con.execute("SELECT * FROM listas").fetchall():
            u = l["uuid"] or nuevo_uuid()
            if not l["uuid"]:
                con.execute("UPDATE listas SET uuid = ? WHERE id = ?", (u, l["id"]))
            fila_lista = {"id": u, "nombre": l["nombre"],
                          "descripcion": l["descripcion"] or "",
                          "fijada": bool(l["fijada"])}
            if l["publica"]:
                # solo si la usa: así la subida no se rompe mientras la nube no conozca estas columnas
                fila_lista["publica"] = True
                fila_lista["en_perfil"] = bool(l["en_perfil"])
            self._upsert("listas", [fila_lista], "id")
            items = [{"lista_id": u, "clave": f["clave"], "datos": pistas.get(f["clave"], {}),
                      "orden": f["orden"] or 0}
                     for f in con.execute("SELECT clave, orden FROM lista_items WHERE lista_id = ?",
                                          (l["id"],))
                     if f["clave"].startswith("yt:")]
            self._upsert("lista_items", items, "lista_id,clave")
        guardados = [{"tipo": f["tipo"], "id": f["id"], "datos": json.loads(f["datos"]),
                      "fecha": _iso(f["fecha"])}
                     for f in con.execute("SELECT * FROM guardados")]
        self._upsert("guardados", guardados, "user_id,tipo,id")
        escuchas = [{"clave": f["clave"], "datos": pistas.get(f["clave"], {}),
                     "contexto": json.loads(f["contexto"]) if f["contexto"] else None,
                     "fecha": _iso(f["fecha"])}
                    for f in con.execute("SELECT * FROM reproducciones WHERE nube_id IS NULL "
                                         "AND clave LIKE 'yt:%' ORDER BY fecha DESC LIMIT 300")]
        if escuchas:
            self.sesion.pedir("POST", "escuchas", json=escuchas,
                              cabeceras={"Prefer": "return=minimal"})
            con.execute("UPDATE reproducciones SET nube_id = -1 WHERE nube_id IS NULL")
        con.commit()

    def _enviar_pendientes(self, con):
        filas = con.execute("SELECT * FROM pendientes ORDER BY id").fetchall()
        for f in filas:
            d = json.loads(f["datos"])
            op = f["op"]
            try:
                self._enviar(op, d)
            except SinConexion:
                raise
            except ErrorNube:
                # una orden que la nube rechaza no debe bloquear las demas
                pass
            con.execute("DELETE FROM pendientes WHERE id = ?", (f["id"],))
            con.commit()

    def _enviar(self, op, d):
        s = self.sesion
        if op == "me_gusta_poner":
            self._upsert("me_gusta", [{"clave": d["clave"], "datos": d.get("datos", {})}],
                         "user_id,clave")
        elif op == "me_gusta_quitar":
            s.pedir("DELETE", f"me_gusta?clave=eq.{_q(d['clave'])}")
        elif op == "lista_poner":
            fila = {"id": d["uuid"], "nombre": d["nombre"],
                    "descripcion": d.get("descripcion", ""),
                    "fijada": bool(d.get("fijada")),
                    "actualizada": _iso(time.time())}
            if "publica" in d:
                con_ajustes = dict(fila, publica=bool(d["publica"]),
                                   en_perfil=bool(d["publica"]) and bool(d.get("en_perfil")))
                try:
                    self._upsert("listas", [con_ajustes], "id")
                    return
                except ErrorNube:
                    pass      # la nube aún no conoce estos ajustes: al menos se guarda lo demás
            self._upsert("listas", [fila], "id")
        elif op == "lista_borrar":
            s.pedir("DELETE", f"listas?id=eq.{_q(d['uuid'])}")
        elif op == "items_poner":
            self._upsert("lista_items", [{"lista_id": d["uuid"], "clave": i["clave"],
                                          "datos": i.get("datos", {}), "orden": i.get("orden", 0)}
                                         for i in d["items"]], "lista_id,clave")
        elif op == "item_quitar":
            s.pedir("DELETE", f"lista_items?lista_id=eq.{_q(d['uuid'])}&clave=eq.{_q(d['clave'])}")
        elif op == "guardado_poner":
            self._upsert("guardados", [{"tipo": d["tipo"], "id": d["id"],
                                        "datos": d.get("datos", {})}], "user_id,tipo,id")
        elif op == "guardado_quitar":
            s.pedir("DELETE", f"guardados?tipo=eq.{_q(d['tipo'])}&id=eq.{_q(d['id'])}")
        elif op == "escucha":
            s.pedir("POST", "escuchas", json=[{"clave": d["clave"], "datos": d.get("datos", {}),
                                               "contexto": d.get("contexto"),
                                               "fecha": _iso(d.get("fecha") or time.time())}],
                    cabeceras={"Prefer": "return=minimal"})
        elif op == "ajustes":
            self._upsert("ajustes", [{"datos": d, "actualizado": _iso(time.time())}], "user_id")

    def _sincronizar_ajustes(self, con, forzar=True):
        """Ajustes comunes: si solo cambiaron en otro dispositivo, se aplican
        aqui (devuelve cuales); si cambiaron aqui, se suben (gana el ultimo).
        Sin `forzar` (tras un cambio local cualquiera) no se pregunta a la nube si aqui no cambiaron."""
        if self.ajustes is None:
            return {}
        if not forzar:
            f = con.execute("SELECT valor FROM estado WHERE clave = 'ajustes_huella'").fetchone()
            if f and json.loads(f["valor"]) == huella_ajustes(ajustes_compartidos(self.ajustes)):
                return {}
        def leer(clave):
            f = con.execute("SELECT valor FROM estado WHERE clave = ?", (clave,)).fetchone()
            return json.loads(f["valor"]) if f else None
        def poner(clave, valor):
            con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES (?, ?)",
                        (clave, json.dumps(valor)))
        locales = ajustes_compartidos(self.ajustes)
        huella_local = huella_ajustes(locales)
        sincronizada = leer("ajustes_huella")          # la ultima que coincidia con la nube
        fecha_vista = leer("ajustes_fecha")            # la ultima version de la nube que vimos
        filas = self.sesion.pedir("GET", "ajustes?select=datos,actualizado")
        remoto = filas[0] if filas else None
        aplicar = {}
        primera_vez = sincronizada is None
        if remoto and remoto.get("actualizado") != fecha_vista and (huella_local == sincronizada or primera_vez):
            # cambio en otro dispositivo y aqui nada (o este equipo es nuevo
            # en la cuenta): lo de la nube manda
            datos = {k: v for k, v in (remoto.get("datos") or {}).items() if k in COMPARTIDOS}
            aplicar = {k: v for k, v in datos.items() if locales.get(k) != v}
            poner("ajustes_huella", huella_ajustes({**locales, **datos}))
            poner("ajustes_fecha", remoto.get("actualizado"))
        elif remoto is None or huella_local != sincronizada:
            # cambio aqui (o la nube aun no tiene nada): se sube
            fecha = _iso(time.time())
            self._upsert("ajustes", [{"datos": locales, "actualizado": fecha}], "user_id")
            nueva = self.sesion.pedir("GET", "ajustes?select=actualizado")
            poner("ajustes_huella", huella_local)
            poner("ajustes_fecha", nueva[0]["actualizado"] if nueva else fecha)
        con.commit()
        return aplicar

    def _paginado(self, ruta, tanda=1000):
        """Todas las filas de una consulta, de a `tanda` (la nube entrega como mucho 1000 por petición)."""
        filas, desde = [], 0
        while True:
            lote = self.sesion.pedir("GET", f"{ruta}&limit={tanda}&offset={desde}") or []
            filas += lote
            if len(lote) < tanda:
                return filas
            desde += tanda

    def _traer(self, con):
        """Lo de la nube manda (salvo lo que aun espera para subir). Devuelve si
        algo cambio en la biblioteca local. Solo se escribe lo que de verdad cambió:
        con 20 listas de 300 canciones, una descarga sin novedades no toca la base."""
        s = self.sesion
        if con.execute("SELECT COUNT(*) n FROM pendientes").fetchone()["n"]:
            return False
        cambio = False
        pistas = _pistas_conocidas(con)

        # me gusta
        remoto = s.pedir("GET", "me_gusta?select=clave,datos,fecha&order=fecha.desc&limit=5000") or []
        locales = {f["clave"] for f in con.execute("SELECT clave FROM me_gusta WHERE clave LIKE 'yt:%'")}
        nube = {f["clave"] for f in remoto}
        for clave in locales - nube:
            con.execute("DELETE FROM me_gusta WHERE clave = ?", (clave,))
            cambio = True
        for f in remoto:
            _recordar(con, f["clave"], f["datos"], pistas)
            if f["clave"] not in locales:
                con.execute("INSERT OR REPLACE INTO me_gusta (clave, fecha) VALUES (?,?)",
                            (f["clave"], _epoch(f["fecha"])))
                cambio = True

        # listas y sus canciones (las canciones de TODAS las listas en una sola consulta paginada)
        try:
            listas = s.pedir("GET", "listas?select=id,nombre,descripcion,fijada,creada,publica,en_perfil"
                                    "&order=creada")
        except ErrorNube:             # la nube aún no conoce publica / en_perfil
            listas = s.pedir("GET", "listas?select=id,nombre,descripcion,fijada,creada&order=creada")
        listas = listas or []
        items = self._paginado("lista_items?select=lista_id,clave,datos,orden&order=lista_id,orden,clave")
        por_lista = {}
        for i in items:
            por_lista.setdefault(i["lista_id"], []).append(i)
        uuids = {l["id"] for l in listas}
        for l in listas:
            fila = con.execute("SELECT * FROM listas WHERE uuid = ?", (l["id"],)).fetchone()
            if fila:
                lid = fila["id"]
                nuevo = (l["nombre"], l["descripcion"], 1 if l["fijada"] else 0)
                if nuevo != (fila["nombre"], fila["descripcion"], fila["fijada"]):
                    con.execute("UPDATE listas SET nombre = ?, descripcion = ?, fijada = ? WHERE id = ?",
                                nuevo + (lid,))
                    cambio = True
                if "publica" in l:
                    ajustes = (1 if l["publica"] else 0, 1 if (l["publica"] and l.get("en_perfil")) else 0)
                    if ajustes != (fila["publica"] or 0, fila["en_perfil"] or 0):
                        con.execute("UPDATE listas SET publica = ?, en_perfil = ? WHERE id = ?", ajustes + (lid,))
                        cambio = True
            else:
                nombre = l["nombre"]
                if con.execute("SELECT 1 FROM listas WHERE nombre = ?", (nombre,)).fetchone():
                    nombre = f"{nombre} ({l['id'][:4]})"
                cur = con.execute("INSERT INTO listas (nombre, creada, descripcion, fijada, uuid, tocada)"
                                  " VALUES (?,?,?,?,?,?)",
                                  (nombre, _epoch(l["creada"]), l["descripcion"],
                                   1 if l["fijada"] else 0, l["id"], _epoch(l["creada"])))
                lid = cur.lastrowid
                cambio = True
                if l.get("publica"):
                    con.execute("UPDATE listas SET publica = 1, en_perfil = ? WHERE id = ?",
                                (1 if l.get("en_perfil") else 0, lid))
            if _aplicar_items(con, lid, por_lista.get(l["id"], []), pistas):
                cambio = True
        for l in con.execute("SELECT id, uuid FROM listas WHERE uuid IS NOT NULL").fetchall():
            if l["uuid"] not in uuids:
                _p = con.execute("SELECT portada FROM listas WHERE id = ?", (l["id"],)).fetchone()
                if _p and _p["portada"]:
                    try:
                        os.remove(_p["portada"])
                    except OSError:
                        pass
                con.execute("DELETE FROM lista_items WHERE lista_id = ?", (l["id"],))
                con.execute("DELETE FROM listas WHERE id = ?", (l["id"],))
                cambio = True

        # guardados
        guardados = s.pedir("GET", "guardados?select=tipo,id,datos,fecha") or []
        locales_g = {(f["tipo"], f["id"]): f["datos"] for f in con.execute("SELECT tipo, id, datos FROM guardados")}
        nube_g = {(g["tipo"], g["id"]): g for g in guardados}
        if set(locales_g) != set(nube_g) or any(
                _distinto(locales_g[k], g["datos"]) for k, g in nube_g.items()):
            con.execute("DELETE FROM guardados")
            for g in guardados:
                con.execute("INSERT OR REPLACE INTO guardados (tipo, id, datos, fecha) VALUES (?,?,?,?)",
                            (g["tipo"], g["id"], json.dumps(g["datos"], ensure_ascii=False),
                             _epoch(g["fecha"])))
            cambio = True

        # escuchas de otros dispositivos
        escuchas = s.pedir("GET", "escuchas?select=id,clave,datos,contexto,fecha"
                                  "&order=fecha.desc&limit=300") or []
        for e in escuchas:
            if con.execute("SELECT 1 FROM reproducciones WHERE nube_id = ?", (e["id"],)).fetchone():
                continue
            # la que se envio desde aqui ya existe con nube_id -1: se empareja por fecha
            ya = con.execute("SELECT id FROM reproducciones WHERE clave = ? AND nube_id = -1 "
                             "AND ABS(fecha - ?) < 5", (e["clave"], _epoch(e["fecha"]))).fetchone()
            if ya:
                con.execute("UPDATE reproducciones SET nube_id = ? WHERE id = ?", (e["id"], ya["id"]))
                continue
            _recordar(con, e["clave"], e["datos"], pistas)
            con.execute("INSERT INTO reproducciones (clave, fecha, contexto, nube_id) VALUES (?,?,?,?)",
                        (e["clave"], _epoch(e["fecha"]),
                         json.dumps(e["contexto"], ensure_ascii=False) if e["contexto"] else "",
                         e["id"]))
            cambio = True
        con.commit()
        return cambio

    def _traer_una(self, lista_uuid):
        """Una sola lista (la que está abierta). Devuelve si cambió algo."""
        con = self._abrir()
        try:
            if con.execute("SELECT COUNT(*) n FROM pendientes").fetchone()["n"]:
                return False
            fila = con.execute("SELECT id FROM listas WHERE uuid = ?", (lista_uuid,)).fetchone()
            if not fila:
                return False
            items = self._paginado("lista_items?select=lista_id,clave,datos,orden"
                                   f"&lista_id=eq.{_q(lista_uuid)}&order=orden,clave")
            hay = _aplicar_items(con, fila["id"], items, _pistas_conocidas(con))
            con.commit()
            return hay
        finally:
            con.close()


def _distinto(guardado, nuevo):
    try:
        return json.loads(guardado) != nuevo
    except (TypeError, ValueError):
        return True


def _pistas_conocidas(con):
    """clave -> datos (texto) de las pistas ya guardadas, para no reescribir las que no cambiaron."""
    return {f["clave"]: f["datos"] for f in con.execute("SELECT clave, datos FROM pistas")}


def _aplicar_items(con, lista_id, remotos, pistas):
    """Deja las canciones de internet de la lista como están en la nube, tocando solo lo que
    cambió. Las que son archivos de este equipo (local:) no se tocan. Devuelve si algo cambió."""
    locales = {f["clave"]: f["orden"] for f in con.execute(
        "SELECT clave, orden FROM lista_items WHERE lista_id = ? AND clave LIKE 'yt:%'", (lista_id,))}
    cambio = False
    nube = {i["clave"]: i["orden"] for i in remotos}
    for clave in set(locales) - set(nube):
        con.execute("DELETE FROM lista_items WHERE lista_id = ? AND clave = ?", (lista_id, clave))
        cambio = True
    for i in remotos:
        _recordar(con, i["clave"], i["datos"], pistas)
        antes = locales.get(i["clave"])
        if antes is None or float(antes or 0) != float(i["orden"] or 0):
            con.execute("INSERT INTO lista_items (lista_id, clave, orden, agregada) VALUES (?,?,?,?)"
                        " ON CONFLICT(lista_id, clave) DO UPDATE SET orden = excluded.orden",
                        (lista_id, i["clave"], i["orden"], time.time()))
            cambio = True
    return cambio


def _recordar(con, clave, datos, pistas=None):
    """Guarda los datos de una pista si son nuevos o cambiaron. Devuelve si escribió."""
    if not datos:
        return False
    if pistas is not None and clave in pistas:
        try:
            if json.loads(pistas[clave]) == datos:
                return False
        except (TypeError, ValueError):
            pass
    texto = json.dumps(datos, ensure_ascii=False)
    con.execute("INSERT OR REPLACE INTO pistas (clave, datos, actualizada) VALUES (?,?,?)",
                (clave, texto, time.time()))
    if pistas is not None:
        pistas[clave] = texto
    return True


def _huella(con):
    partes = []
    for sql in ("SELECT group_concat(clave) FROM (SELECT clave FROM me_gusta ORDER BY clave)",
                "SELECT group_concat(uuid || nombre || descripcion || fijada || COALESCE(publica, 0) || COALESCE(en_perfil, 0)) FROM listas",
                "SELECT group_concat(lista_id || clave || orden) FROM lista_items",
                "SELECT group_concat(tipo || id) FROM guardados",
                "SELECT COUNT(*) FROM reproducciones"):
        partes.append(str(con.execute(sql).fetchone()[0]))
    return "|".join(partes)


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(float(epoch or time.time())))


def _epoch(iso):
    if not iso:
        return time.time()
    import datetime
    try:
        return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return time.time()
