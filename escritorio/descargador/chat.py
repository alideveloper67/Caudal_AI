# -*- coding: utf-8 -*-
"""Mensajes entre dos personas y «Mezcla con un amigo» (igual que
app/lib/nucleo/chat.dart). Todo va por Supabase con las reglas de
supabase/esquema.sql: cada uno solo ve sus conversaciones."""

from datetime import datetime


def _fecha(texto):
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00")).astimezone()
    except (TypeError, ValueError):
        return datetime.now().astimezone()


def pista_jugable(p):
    """Una canción guardada en la nube vuelve a poder sonar."""
    p = dict(p or {})
    clave = str(p.get("clave") or "")
    vid = str(p.get("video_id") or "")
    if not vid and clave.startswith("yt:"):
        vid = clave[3:]
    p.update(tipo="pista", clave=clave or f"yt:{vid}", video_id=vid)
    if not p.get("miniatura") and vid:
        p["miniatura"] = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    return p


def vista_previa(c, yo):
    quien = "Tú: " if str(c.get("ultimo_autor")) == str(yo) else ""
    if c.get("ultimo_pista"):
        return f"{quien}♪ {c['ultimo_pista'].get('titulo') or 'Una canción'}"
    if not c.get("ultimo_texto"):
        return "Di hola 👋"
    return quien + c["ultimo_texto"]


def para_nube(p):
    fuera = {"archivo", "descarga_id", "tamano", "calidad", "fecha", "url"}
    return {k: v for k, v in (p or {}).items() if k not in fuera and not str(k).startswith("_")}


class Chat:
    def __init__(self, sesion):
        self.sesion = sesion

    @property
    def yo(self):
        return self.sesion.user_id

    def mis_chats(self):
        filas = self.sesion.pedir("POST", "rpc/mis_chats", json={}) or []
        for f in filas:
            f["fecha"] = _fecha(f.get("ultimo"))
            f["visible"] = f.get("nombre") or f.get("usuario") or "?"
        return filas

    def panorama(self):
        """(chats, solicitudes nuevas). Cada chat trae `es_amigo`: solo se escribe a un amigo
        (si se dejó de ser amigo, la conversación se ve pero ya no se puede escribir)."""
        chats = self.mis_chats()
        try:
            r = self.sesion.pedir("POST", "rpc/mis_amigos", json={})
            amigos = None if r is None else {str(a.get("id")) for a in r}   # sin respuesta: no se sabe
        except Exception:  # noqa: BLE001 - sin las funciones nuevas, todo sigue como antes
            amigos = None
        for c in chats:
            c["es_amigo"] = True if amigos is None else str(c.get("otro")) in amigos
        try:
            n = len(self.sesion.pedir("POST", "rpc/mis_solicitudes", json={}) or [])
        except Exception:  # noqa: BLE001
            n = 0
        return chats, n

    def solo_amigos(self):
        """Los chats con quien sigue siendo amigo (para «Enviar en un chat»)."""
        return [c for c in self.panorama()[0] if c.get("es_amigo")]

    def sin_leer(self):
        return sum(int(c.get("sin_leer") or 0) for c in self.mis_chats())

    def buscar(self, usuario):
        """La persona con ese usuario exacto, con su `relacion` (amigo, enviada, recibida, ninguna)."""
        u = (usuario or "").strip().lstrip("@").lower()
        if not u:
            return None
        filas = self.sesion.pedir("POST", "rpc/buscar_persona", json={"p_usuario": u}) or []
        if filas:
            filas[0].setdefault("relacion", "ninguna")
        return filas[0] if filas else None

    def abrir(self, otro):
        r = self.sesion.pedir("POST", "rpc/abrir_chat", json={"p_otro": otro})
        return str(r).strip('"')

    def mensajes(self, chat, desde=0, limite=200):
        filtro = f"&id=gt.{int(desde)}" if desde else ""
        orden = "id.asc" if desde else "id.desc"
        filas = self.sesion.pedir(
            "GET", f"mensajes?chat=eq.{chat}{filtro}&select=id,autor,texto,pista,creado"
                   f"&order={orden}&limit={limite}") or []
        for f in filas:
            f["fecha"] = _fecha(f.get("creado"))
            if f.get("pista"):
                f["pista"] = pista_jugable(f["pista"])
        return filas if desde else list(reversed(filas))

    def enviar(self, chat, texto="", pista=None):
        cuerpo = {"chat": chat, "texto": (texto or "").strip()}
        if pista is not None:
            cuerpo["pista"] = para_nube(pista)
        filas = self.sesion.pedir("POST", "mensajes", json=cuerpo,
                                  cabeceras={"Prefer": "return=representation"})
        m = filas[0]
        m["fecha"] = _fecha(m.get("creado"))
        if m.get("pista"):
            m["pista"] = pista_jugable(m["pista"])
        return m

    def marcar_leido(self, chat):
        try:
            self.sesion.pedir("POST", "rpc/marcar_leido", json={"p_chat": chat})
        except Exception:  # noqa: BLE001
            pass

    def mezcla(self, chat):
        return self.sesion.pedir("POST", "rpc/mezcla", json={"p_chat": chat}) or {}


def mix_de_mezcla(m, nombre_amigo, chat):
    comunes = [x for x in m.get("comunes") or [] if isinstance(x, dict)]
    resto = [x for x in m.get("mezcla") or [] if isinstance(x, dict)]
    pistas, vistas = [], set()
    i = j = 0
    while i < len(comunes) or j < len(resto):
        tanda = []
        if i < len(comunes):
            tanda.append(comunes[i])
            i += 1
        for _ in range(2):
            if j < len(resto):
                tanda.append(resto[j])
                j += 1
        for p in tanda:
            x = pista_jugable(p)
            if x["video_id"] and x["video_id"] not in vistas:
                vistas.add(x["video_id"])
                pistas.append(x)
    afinidad = int(m.get("afinidad") or 0)
    artistas = [str(a) for a in m.get("artistas_comunes") or []]
    miniaturas = []
    for p in pistas:
        if p.get("miniatura") and p["miniatura"] not in miniaturas:
            miniaturas.append(p["miniatura"])
        if len(miniaturas) == 4:
            break
    sub = f"Coinciden en un {afinidad} %"
    if artistas:
        sub += " · Los dos escuchan a " + ", ".join(artistas[:3])
    return {"tipo": "mix", "id": f"mezcla_{chat}", "titulo": f"Tu mezcla con {nombre_amigo}",
            "subtitulo": sub, "miniatura": miniaturas[0] if miniaturas else "",
            "miniaturas": miniaturas, "color": "#FF5C8A", "pistas": pistas, "total": len(pistas),
            "artistas": artistas, "afinidad": afinidad, "minutos": 0}
