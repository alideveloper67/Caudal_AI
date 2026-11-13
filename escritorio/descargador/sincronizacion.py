# -*- coding: utf-8 -*-
"""Sincronizacion de la biblioteca con la nube (Supabase).

La biblioteca local (SQLite) es la que usa la interfaz: rapida y sin internet.
Cada cambio local deja una orden en la tabla `pendientes`; un hilo las envia
en orden cuando hay conexion y despues trae lo que se cambio en otros
dispositivos. Si no hay red, las ordenes esperan y se envian luego.

La primera vez que una cuenta entra en este equipo se sube lo que ya habia.
"""

import json
import sqlite3
import threading
import time
import uuid

from PySide6.QtCore import QObject, QTimer, Signal

from .hilos import en_segundo_plano
from .nube import ErrorNube, SinConexion

CADA = 3 * 60 * 1000          # traer cambios de otros dispositivos cada 3 minutos


def nuevo_uuid():
    return str(uuid.uuid4())


def _q(valor):
    """Valor para un filtro de PostgREST (eq.)."""
    return str(valor).replace(",", "%2C").replace("(", "%28").replace(")", "%29")


class Sincronizador(QObject):
    cambio_remoto = Signal()        # llegaron cambios: la interfaz se refresca
    estado = Signal(str)            # "sincronizado" | "pendiente" | "sin_conexion" | "error"

    def __init__(self, coleccion, cuenta, al_renovar=None, padre=None):
        super().__init__(padre)
        self.coleccion = coleccion
        self.cuenta = cuenta
        self.sesion = cuenta.get("sesion")
        self.al_renovar = al_renovar
        self.archivo = str(coleccion.archivo)
        self._corriendo = False
        self._otra_vez = False
        self._cerrojo = threading.Lock()
        self.ultimo_estado = ""
        self._reloj = QTimer(self)
        self._reloj.setInterval(CADA)
        self._reloj.timeout.connect(self.ya)
        self._pronto = QTimer(self)
        self._pronto.setSingleShot(True)
        self._pronto.setInterval(1500)
        self._pronto.timeout.connect(self.ya)

    def iniciar(self):
        if not self.sesion:
            return
        self._reloj.start()
        QTimer.singleShot(800, self.ya)

    def pronto(self):
        """Un cambio local: se envia en un momento (se agrupan los seguidos)."""
        self._pronto.start()

    def ya(self):
        if not self.sesion:
            return
        if self._corriendo:
            self._otra_vez = True
            return
        self._corriendo = True
        en_segundo_plano(self._ciclo, ok=self._terminado, error=self._fallo, dueno=self)

    def _terminado(self, cambio):
        self._corriendo = False
        self._fijar("sincronizado")
        if self.al_renovar:
            self.al_renovar()
        if cambio:
            self.coleccion.olvidar_memoria()
            self.cambio_remoto.emit()
        if self._otra_vez:
            self._otra_vez = False
            self.pronto()

    def _fallo(self, e):
        self._corriendo = False
        self._fijar("sin_conexion" if isinstance(e, SinConexion) else "error")
        if self._otra_vez:
            self._otra_vez = False
            QTimer.singleShot(20000, self.ya)

    def _fijar(self, estado):
        if estado != self.ultimo_estado:
            self.ultimo_estado = estado
            self.estado.emit(estado)

    # ------------------------------------------------------------ en el hilo

    def _ciclo(self):
        con = sqlite3.connect(self.archivo, timeout=15)
        con.row_factory = sqlite3.Row
        try:
            uid = self.sesion.user_id
            marca = con.execute("SELECT valor FROM estado WHERE clave = 'nube_usuario'").fetchone()
            if not marca or json.loads(marca["valor"]) != uid:
                self._subida_inicial(con)
                con.execute("INSERT OR REPLACE INTO estado (clave, valor) VALUES ('nube_usuario', ?)",
                            (json.dumps(uid),))
                con.commit()
            self._enviar_pendientes(con)
            return self._traer(con)
        finally:
            con.close()

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
            self._upsert("listas", [{"id": u, "nombre": l["nombre"],
                                     "descripcion": l["descripcion"] or "",
                                     "fijada": bool(l["fijada"])}], "id")
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
            self._upsert("listas", [{"id": d["uuid"], "nombre": d["nombre"],
                                     "descripcion": d.get("descripcion", ""),
                                     "fijada": bool(d.get("fijada")),
                                     "actualizada": _iso(time.time())}], "id")
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

    def _traer(self, con):
        """Lo de la nube manda (salvo lo que aun espera para subir). Devuelve si
        algo cambio en la biblioteca local."""
        s = self.sesion
        if con.execute("SELECT COUNT(*) n FROM pendientes").fetchone()["n"]:
            return False
        antes = _huella(con)

        # me gusta
        remoto = s.pedir("GET", "me_gusta?select=clave,datos,fecha&order=fecha.desc&limit=5000")
        con.execute("DELETE FROM me_gusta WHERE clave LIKE 'yt:%'")
        for f in remoto:
            _recordar(con, f["clave"], f["datos"])
            con.execute("INSERT OR REPLACE INTO me_gusta (clave, fecha) VALUES (?,?)",
                        (f["clave"], _epoch(f["fecha"])))

        # listas y sus canciones
        listas = s.pedir("GET", "listas?select=id,nombre,descripcion,fijada,creada&order=creada")
        uuids = {l["id"] for l in listas}
        for l in listas:
            fila = con.execute("SELECT id FROM listas WHERE uuid = ?", (l["id"],)).fetchone()
            if fila:
                lid = fila["id"]
                con.execute("UPDATE listas SET nombre = ?, descripcion = ?, fijada = ? WHERE id = ?",
                            (l["nombre"], l["descripcion"], 1 if l["fijada"] else 0, lid))
            else:
                nombre = l["nombre"]
                if con.execute("SELECT 1 FROM listas WHERE nombre = ?", (nombre,)).fetchone():
                    nombre = f"{nombre} ({l['id'][:4]})"
                cur = con.execute("INSERT INTO listas (nombre, creada, descripcion, fijada, uuid, tocada)"
                                  " VALUES (?,?,?,?,?,?)",
                                  (nombre, _epoch(l["creada"]), l["descripcion"],
                                   1 if l["fijada"] else 0, l["id"], _epoch(l["creada"])))
                lid = cur.lastrowid
            items = s.pedir("GET", f"lista_items?select=clave,datos,orden&lista_id=eq.{l['id']}"
                                   "&order=orden&limit=5000")
            locales = [f["clave"] for f in con.execute(
                "SELECT clave FROM lista_items WHERE lista_id = ? AND clave NOT LIKE 'yt:%'", (lid,))]
            con.execute("DELETE FROM lista_items WHERE lista_id = ? AND clave LIKE 'yt:%'", (lid,))
            for i in items:
                _recordar(con, i["clave"], i["datos"])
                con.execute("INSERT OR REPLACE INTO lista_items (lista_id, clave, orden, agregada)"
                            " VALUES (?,?,?,?)", (lid, i["clave"], i["orden"], time.time()))
            _ = locales     # las canciones solo locales (archivos) se quedan como estaban
        for l in con.execute("SELECT id, uuid FROM listas WHERE uuid IS NOT NULL").fetchall():
            if l["uuid"] not in uuids:
                con.execute("DELETE FROM lista_items WHERE lista_id = ?", (l["id"],))
                con.execute("DELETE FROM listas WHERE id = ?", (l["id"],))

        # guardados
        guardados = s.pedir("GET", "guardados?select=tipo,id,datos,fecha")
        con.execute("DELETE FROM guardados")
        for g in guardados:
            con.execute("INSERT OR REPLACE INTO guardados (tipo, id, datos, fecha) VALUES (?,?,?,?)",
                        (g["tipo"], g["id"], json.dumps(g["datos"], ensure_ascii=False),
                         _epoch(g["fecha"])))

        # escuchas de otros dispositivos
        escuchas = s.pedir("GET", "escuchas?select=id,clave,datos,contexto,fecha"
                                  "&order=fecha.desc&limit=300")
        for e in escuchas:
            if con.execute("SELECT 1 FROM reproducciones WHERE nube_id = ?", (e["id"],)).fetchone():
                continue
            # la que se envio desde aqui ya existe con nube_id -1: se empareja por fecha
            ya = con.execute("SELECT id FROM reproducciones WHERE clave = ? AND nube_id = -1 "
                             "AND ABS(fecha - ?) < 5", (e["clave"], _epoch(e["fecha"]))).fetchone()
            if ya:
                con.execute("UPDATE reproducciones SET nube_id = ? WHERE id = ?", (e["id"], ya["id"]))
                continue
            _recordar(con, e["clave"], e["datos"])
            con.execute("INSERT INTO reproducciones (clave, fecha, contexto, nube_id) VALUES (?,?,?,?)",
                        (e["clave"], _epoch(e["fecha"]),
                         json.dumps(e["contexto"], ensure_ascii=False) if e["contexto"] else "",
                         e["id"]))
        con.commit()
        return _huella(con) != antes


def _recordar(con, clave, datos):
    if datos:
        con.execute("INSERT OR REPLACE INTO pistas (clave, datos, actualizada) VALUES (?,?,?)",
                    (clave, json.dumps(datos, ensure_ascii=False), time.time()))


def _huella(con):
    partes = []
    for sql in ("SELECT group_concat(clave) FROM (SELECT clave FROM me_gusta ORDER BY clave)",
                "SELECT group_concat(uuid || nombre || descripcion || fijada) FROM listas",
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
