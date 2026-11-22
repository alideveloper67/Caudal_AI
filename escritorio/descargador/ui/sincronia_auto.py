# -*- coding: utf-8 -*-
"""La letra se pone sola a tiempo: un solo coordinador para todas las vistas de letra.

Cuando llega una letra sincronizada, la vista se la pasa aquí (`pedir`). Se escucha un tramo del audio
que suena (sincronia_letra.verificar, en segundo plano) y se avisa con `listo(clave, resultado)`:
- un corrimiento → la vista lo suma a sus tiempos (`desfase`), igual que el ajuste fino de la persona;
- otra letra que cuadra mejor → `letra_nueva` la devuelve y la vista la cambia.

Se hace una vez por canción, modo (audio/video) y letra: lo medido se guarda en ajustes «letra_auto».
Si la persona movió la letra a mano (Ctrl+←/→), su ajuste se suma encima; nunca se pisa.
"""

import hashlib

from PySide6.QtCore import QObject, QTimer, Signal

from .. import sincronia_letra
from ..hilos import en_segundo_plano

MAX_GUARDADOS = 800
REINTENTOS_FUENTE = 12        # cada 1,5 s mientras la canción todavía carga


def huella(lineas):
    """Identifica una letra concreta (si LRCLIB devuelve otra, se vuelve a medir)."""
    texto = "|".join(f"{int(ms or 0)}:{tx}" for ms, tx in (lineas or [])[:40])
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]


def clave_pista(p):
    p = p or {}
    return p.get("clave") or p.get("video_id") or p.get("archivo") or p.get("url") or ""


class SincroniaAuto(QObject):
    listo = Signal(str, object)        # (clave de la pista, resultado de verificar)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._en_curso = set()          # claves completas que se están midiendo
        self._memoria = {}              # clave completa -> resultado (también lo que no se guarda)
        self._modelo_falla = False

    # ----------------------------------------------------------- lo que consultan las vistas
    def activa(self):
        try:
            return bool(self.ctx.ajustes["letra_sincronia_auto"]) and not self._modelo_falla \
                and sincronia_letra.disponible()
        except Exception:  # noqa: BLE001
            return False

    def _clave(self, p, modo, lineas):
        return f"{clave_pista(p)}|{modo}|{huella(lineas)}"

    def desfase(self, p, lineas):
        """ms que hay que sumar al RELOJ de la letra de `p` (la que suena, en el modo actual), con el mismo
        sentido que el ajuste fino de la persona: positivo la adelanta. 0 si no se sabe.
        (sincronia_letra mide cuánto hay que sumar a los TIEMPOS de la letra: es lo mismo con el signo cambiado.)"""
        if not p or not lineas or not self.activa():
            return 0
        k = self._clave(p, getattr(self.ctx.reproductor, "modo", "audio"), lineas)
        r = self._memoria.get(k)
        if r is not None:
            return -int(r.get("desfase_ms") or 0) if r.get("accion") in ("corregir", "cambiar") else 0
        try:
            return -int((self.ctx.ajustes["letra_auto"] or {}).get(k, 0))
        except Exception:  # noqa: BLE001
            return 0

    def medida(self, p, lineas):
        """¿Ya se sabe cómo va esta letra con el audio que suena (en esta sesión o en otra)?"""
        if not p or not lineas:
            return False
        k = self._clave(p, getattr(self.ctx.reproductor, "modo", "audio"), lineas)
        if k in self._memoria:
            return self._memoria[k].get("accion") in ("bien", "corregir", "cambiar")
        try:
            return k in (self.ctx.ajustes["letra_auto"] or {})
        except Exception:  # noqa: BLE001
            return False

    def letra_nueva(self, p, lineas):
        """(datos, ms) si se encontró otra letra que cuadra con el audio; si no, None."""
        if not p or not lineas:
            return None
        k = self._clave(p, getattr(self.ctx.reproductor, "modo", "audio"), lineas)
        r = self._memoria.get(k)
        if r and r.get("accion") == "cambiar" and r.get("datos"):
            return r["datos"], int(r.get("desfase_ms") or 0)
        return None

    # ----------------------------------------------------------- medir
    def pedir(self, p, datos, alternativas=None):
        """La vista recibió `datos` (formato de catalogo.letras) para la pista `p`."""
        if not p or not datos or not datos.get("sincronizada") or not datos.get("lineas"):
            return
        if not self.activa():
            return
        self._intentar(p, list(datos["lineas"]), alternativas, REINTENTOS_FUENTE)

    def _intentar(self, p, lineas, alternativas, quedan):
        r = self.ctx.reproductor
        if clave_pista(r.actual) != clave_pista(p):
            return                       # ya suena otra cosa
        sonando = r.fuente_sonando() if hasattr(r, "fuente_sonando") else None
        if sonando is None:
            if quedan > 0:
                QTimer.singleShot(1500, self, lambda: self._intentar(p, lineas, alternativas, quedan - 1))
            return
        modo, fuente = sonando
        k = self._clave(p, modo, lineas)
        if k in self._memoria or k in self._en_curso:
            if k in self._memoria:
                self.listo.emit(clave_pista(p), self._memoria[k])
            return
        try:
            if k in (self.ctx.ajustes["letra_auto"] or {}):
                return                   # ya medida en otra sesión
        except Exception:  # noqa: BLE001
            pass
        self._en_curso.add(k)
        dur = float(getattr(r, "_duracion", 0) or (p.get("duracion") or 0))
        if alternativas is None:
            from .. import catalogo
            alternativas = (lambda q=dict(p): catalogo.letras_alternativas(q))
        en_segundo_plano(sincronia_letra.verificar, lineas, fuente, dur, alternativas,
                         ok=lambda res, k=k, c=clave_pista(p): self._llego(k, c, res),
                         error=lambda e, k=k: self._fallo(k, e), dueno=self)

    def _llego(self, k, clave, res):
        self._en_curso.discard(k)
        res = res or {}
        self._memoria[k] = res
        if len(self._memoria) > 300:
            for viejo in list(self._memoria)[:100]:
                self._memoria.pop(viejo, None)
        accion = res.get("accion")
        if accion == "cambiar" and res.get("datos"):
            _pista, modo, _h = k.rsplit("|", 2)
            nueva = f"{_pista}|{modo}|{huella(res['datos'].get('lineas'))}"
            ms = int(res.get("desfase_ms") or 0)
            self._memoria[nueva] = {"accion": "corregir" if ms else "bien", "desfase_ms": ms,
                                    "detalle": res.get("detalle", "")}
        if accion in ("bien", "corregir"):
            # se guarda: la próxima vez se pone a tiempo sin volver a escuchar
            try:
                tabla = dict(self.ctx.ajustes["letra_auto"] or {})
                tabla[k] = int(res.get("desfase_ms") or 0) if accion == "corregir" else 0
                while len(tabla) > MAX_GUARDADOS:
                    tabla.pop(next(iter(tabla)))
                self.ctx.ajustes["letra_auto"] = tabla
                self.ctx.ajustes.guardar()
            except Exception:  # noqa: BLE001
                pass
        self.listo.emit(clave, res)

    def _fallo(self, k, e):
        self._en_curso.discard(k)
        # sin modelo (no se pudo bajar, sin internet la primera vez…) no se insiste en cada canción
        texto = str(e)
        if "modelo" in texto or "huggingface" in texto.lower() or isinstance(e, (ImportError, OSError)):
            self._modelo_falla = True
            QTimer.singleShot(10 * 60 * 1000, self, self._reactivar)

    def _reactivar(self):
        self._modelo_falla = False


def sincronia_de(ctx):
    """El coordinador de esta ventana (uno solo, lo comparten la letra, el karaoke y la escena)."""
    s = getattr(ctx, "_sincronia_letra", None)
    if s is None:
        s = SincroniaAuto(ctx)
        try:
            ctx._sincronia_letra = s
        except Exception:  # noqa: BLE001
            pass
    return s
