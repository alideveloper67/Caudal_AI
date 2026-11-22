# -*- coding: utf-8 -*-
"""Grupos para hablar (igual que app/lib/nucleo/grupos.dart; reglas en supabase/grupos.sql).

Abiertos (cualquiera entra) y privados (con código). Dentro: texto, canciones y notas de voz. No hay
imágenes ni videos: la base no tiene dónde guardarlos y el almacén de audios solo acepta audio."""

import re
import time

from .chat import _fecha, pista_jugable

ALMACEN_AUDIOS = "audios-grupos"
MAX_SEGUNDOS_AUDIO = 180


def limpiar_codigo(c):
    """El código se escribe como sea: minúsculas, con espacios o guiones."""
    return re.sub(r"[^A-Z0-9]", "", str(c or "").upper())


def pista_para_grupo(p):
    """Lo justo para que la canción suene (la base descarta lo demás)."""
    p = p or {}
    artista = str(p.get("artista") or "")
    if not artista and isinstance(p.get("artistas"), list):
        artista = ", ".join(str(a.get("nombre") if isinstance(a, dict) else a) for a in p["artistas"] if a)
    try:
        dur = str(int(round(float(p.get("duracion") or 0))))
    except (TypeError, ValueError):
        dur = "0"
    return {"video_id": str(p.get("video_id") or ""), "titulo": str(p.get("titulo") or ""), "artista": artista,
            "miniatura": str(p.get("miniatura") or ""), "duracion": dur}


def vista_previa(g):
    u = g.get("ultimo_mensaje")
    if not isinstance(u, dict):
        n = int(g.get("miembros") or 0)
        return f"{n} {'persona' if n == 1 else 'personas'}"
    quien = u.get("nombre") or u.get("usuario") or ""
    que = "🎤 Nota de voz" if u.get("audio") else "♪ Una canción" if u.get("pista") else str(u.get("texto") or "")
    return f"{quien}: {que}" if quien else que


def modera(g):
    return (g or {}).get("rol") in ("dueno", "moderador")


def _mensaje(d):
    d = dict(d or {})
    if isinstance(d.get("pista"), dict):
        d["pista"] = pista_jugable(d["pista"])
    a = d.get("autor") if isinstance(d.get("autor"), dict) else {}
    d["autor"] = a
    d["visible"] = a.get("nombre") or a.get("usuario") or "Alguien que ya no está"
    d["fecha"] = _fecha(d.get("creado"))
    return d


class Grupos:
    def __init__(self, sesion):
        self.sesion = sesion

    @property
    def yo(self):
        return self.sesion.user_id

    def _rpc(self, nombre, **p):
        return self.sesion.rpc(nombre, **p)

    def mis_grupos(self):
        return [g for g in (self._rpc("mis_grupos") or []) if isinstance(g, dict)]

    def sin_leer(self):
        return sum(int(g.get("sin_leer") or 0) for g in self.mis_grupos())

    def explorar(self, busqueda="", desde=0):
        return [g for g in (self._rpc("grupos_explorar", p_busqueda=str(busqueda or "").strip(), p_desde=desde) or [])
                if isinstance(g, dict)]

    def crear(self, nombre, descripcion="", privado=False):
        return self._rpc("grupo_crear", p_nombre=str(nombre or "").strip(), p_descripcion=str(descripcion or "").strip(),
                         p_tipo="privado" if privado else "abierto")

    def ver(self, gid):
        r = self._rpc("grupo_ver", p_grupo=gid)
        return r if isinstance(r, dict) else None

    def unirse(self, gid):
        return self._rpc("grupo_unirse", p_grupo=gid)

    def unirse_con_codigo(self, codigo):
        return self._rpc("grupo_unirse_codigo", p_codigo=limpiar_codigo(codigo))

    def salir(self, gid):
        self._rpc("grupo_salir", p_grupo=gid)

    def mensajes(self, gid, antes=None, limite=50):
        """Del más viejo al más nuevo."""
        filas = self._rpc("grupo_mensajes", p_grupo=gid, p_antes=antes, p_limite=limite) or []
        return [_mensaje(d) for d in reversed(filas) if isinstance(d, dict)]

    def nuevos(self, gid, desde):
        return [_mensaje(d) for d in (self._rpc("grupo_mensajes_desde", p_grupo=gid, p_desde=desde) or [])
                if isinstance(d, dict)]

    def enviar(self, gid, texto="", pista=None, audio=None, audio_seg=0):
        r = self._rpc("grupo_enviar", p_grupo=gid, p_texto=str(texto or "").strip(),
                      p_pista=pista_para_grupo(pista) if pista else None, p_audio=audio,
                      p_audio_seg=max(1, min(MAX_SEGUNDOS_AUDIO, int(audio_seg or 1))) if audio else None)
        return _mensaje(r)

    def subir_audio(self, gid, datos, tipo="audio/mp4"):
        ext = "webm" if "webm" in tipo else "ogg" if "ogg" in tipo else "wav" if "wav" in tipo else "m4a"
        ruta = f"{gid}/{self.yo}/{int(time.time() * 1000)}.{ext}"
        self.sesion.subir_archivo(ALMACEN_AUDIOS, ruta, datos, tipo)
        return ruta

    def url_audio(self, ruta):
        return self.sesion.url_firmada(ALMACEN_AUDIOS, ruta)

    def leido(self, gid):
        try:
            self._rpc("grupo_leido", p_grupo=gid)
        except Exception:  # noqa: BLE001
            pass

    def reportar(self, mid, motivo=""):
        self._rpc("grupo_reportar", p_mensaje=mid, p_motivo=motivo)

    def accion(self, mid, accion):
        """borrar · ocultar · mostrar · fijar · desfijar"""
        self._rpc("grupo_mensaje_accion", p_mensaje=mid, p_accion=accion)

    def fijados(self, gid):
        return [_mensaje(d) for d in (self._rpc("grupo_fijados", p_grupo=gid) or []) if isinstance(d, dict)]

    def reportados(self, gid):
        return [_mensaje(d) for d in (self._rpc("grupo_reportados", p_grupo=gid) or []) if isinstance(d, dict)]

    def miembros(self, gid):
        return [d for d in (self._rpc("grupo_miembros_lista", p_grupo=gid) or []) if isinstance(d, dict)]

    def poner_rol(self, gid, usuario, moderador):
        self._rpc("grupo_poner_rol", p_grupo=gid, p_usuario=usuario, p_rol="moderador" if moderador else "miembro")

    def pasar_dueno(self, gid, usuario):
        self._rpc("grupo_pasar_dueno", p_grupo=gid, p_usuario=usuario)

    def silenciar(self, gid, usuario, minutos):
        self._rpc("grupo_silenciar", p_grupo=gid, p_usuario=usuario, p_minutos=int(minutos))

    def expulsar(self, gid, usuario):
        self._rpc("grupo_expulsar", p_grupo=gid, p_usuario=usuario)

    def editar(self, gid, nombre, descripcion):
        return self._rpc("grupo_editar", p_grupo=gid, p_nombre=str(nombre or "").strip(),
                         p_descripcion=str(descripcion or "").strip())

    def cambiar_codigo(self, gid):
        return str(self._rpc("grupo_cambiar_codigo", p_grupo=gid) or "").strip('"')

    def borrar(self, gid):
        self._rpc("grupo_borrar", p_grupo=gid)
