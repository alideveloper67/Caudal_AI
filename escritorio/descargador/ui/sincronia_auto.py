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

from .. import ayudante, letras_cache, sincronia_letra, sincronia_tareas
from ..hilos import en_segundo_plano
from ..sincronia_tareas import poner_tramos, verificar  # noqa: F401  (los usan las vistas y las pruebas)

MAX_GUARDADOS = 800
REINTENTOS_FUENTE = 12        # cada 1,5 s mientras la canción todavía carga


def huella(lineas):
    """Identifica una letra concreta (si LRCLIB devuelve otra, se vuelve a medir)."""
    texto = "|".join(f"{int(ms or 0)}:{tx}" for ms, tx in (lineas or [])[:40])
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]


def clave_pista(p):
    p = p or {}
    return p.get("clave") or p.get("video_id") or p.get("archivo") or p.get("url") or ""


def sin_tiempos(datos):
    """La misma letra, como texto corrido (cuando sus tiempos son de otra grabación y aún no se ajustaron)."""
    d = dict(datos or {})
    texto = d.get("texto") or "\n".join(tx for _ms, tx in d.get("lineas") or [])
    d.update(sincronizada=False, lineas=[], texto=texto)
    return d


def en_duda(sinc, p, datos):
    """¿Los tiempos son de una grabación que dura distinto y todavía no se ajustaron a esta?"""
    return bool((datos or {}).get("otra_duracion")) and not sinc.medida(p, datos.get("lineas"))


def _con_parejas(res):
    """Lo que volvió del ayudante (JSON) con las líneas otra vez como (ms, verso)."""
    d = (res or {}).get("datos")
    for k in ("lineas", "ref_lineas"):
        if d and d.get(k):
            d[k] = [(int(ms), str(t)) for ms, t in d[k]]
    return res


def _verificar_aparte(vigente, pista, lineas, fuente, duracion, alternativas, datos, misma, voz, region):
    """Lo que corre en el hilo de fondo: lo hace el proceso ayudante; si no se pudo abrir, este mismo hilo."""
    if not vigente():
        return None                         # ya suena otra: no se gasta en esta
    if (datos or {}).get("ref") and misma:
        return verificar(lineas, fuente, duracion, alternativas, datos, misma, voz)     # no hay nada que escuchar
    if ayudante.disponible():
        try:
            return _con_parejas(ayudante.pedir("verificar", {
                "pista": {k: v for k, v in (pista or {}).items() if not str(k).startswith("_")},
                "lineas": lineas, "fuente": fuente, "duracion": duracion, "datos": datos, "misma": misma,
                "voz": voz, "region": region,
                "alternativas": alternativas if isinstance(alternativas, list) else None}))
        except ayudante.ErrorAyudante as e:
            if "modelo" in str(e) or "huggingface" in str(e).lower():
                raise
    pedir = (lambda: alternativas) if isinstance(alternativas, list) else alternativas
    return verificar(lineas, fuente, duracion, pedir, datos, misma, voz)


def _tarea_aparte(vigente, nombre, datos):
    if not vigente():
        return None
    if ayudante.disponible():
        return ayudante.pedir(nombre, datos)
    return sincronia_tareas.tarea(nombre, datos)


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
            return bool(self.ctx.ajustes["letra_sincronia_auto"])
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
        if not self.activa() or datos.get("escuchada"):     # sus tiempos ya salieron de escuchar esta canción
            return
        self._intentar(p, list(datos["lineas"]), alternativas, REINTENTOS_FUENTE, datos)

    def _intentar(self, p, lineas, alternativas, quedan, datos=None):
        r = self.ctx.reproductor
        if clave_pista(r.actual) != clave_pista(p):
            return                       # ya suena otra cosa
        sonando = r.fuente_sonando() if hasattr(r, "fuente_sonando") else None
        if sonando is None:
            if quedan > 0:
                QTimer.singleShot(1500, self, lambda: self._intentar(p, lineas, alternativas, quedan - 1,
                                                                          datos))
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
        kc = self._clave_cotejo(p, modo, datos)
        tramos = self._cotejo_guardado(kc)
        if tramos:
            self._llego(k, clave_pista(p), poner_tramos(datos, tramos))
            return
        self._en_curso.add(k)
        dur = float(getattr(r, "_duracion", 0) or (p.get("duracion") or 0))
        if alternativas is None:
            from .. import catalogo
            alternativas = (lambda q=dict(p): catalogo.letras_alternativas(q))
        elif callable(alternativas) is False:
            alternativas = list(alternativas)
        misma = modo == "audio" and bool(datos) and bool(p.get("video_id")) and datos.get("ref") == p.get("video_id")
        voz = not self._modelo_falla and sincronia_letra.disponible()
        if not voz and not (datos or {}).get("ref"):
            self._en_curso.discard(k)
            return
        en_segundo_plano(_verificar_aparte, self._vigente(p), dict(p), lineas, fuente, dur, alternativas, datos, misma,
                         voz, self._region(),
                         ok=lambda res, k=k, kc=kc, c=clave_pista(p): self._resultado(k, kc, c, res),
                         error=lambda e, k=k: self._fallo(k, e), dueno=self, lento=True)

    def _vigente(self, p):
        """¿Sigue sonando esta canción? (se pregunta desde el hilo de fondo, justo antes de trabajar)."""
        r, clave = self.ctx.reproductor, clave_pista(p)
        return lambda: clave_pista(r.actual) == clave

    def _region(self):
        try:
            return self.ctx.ajustes["region"]
        except Exception:  # noqa: BLE001
            return ""

    def _resultado(self, k, kc, clave, res):
        if res is None:                      # se pasó de canción antes de empezar: la próxima vez
            self._en_curso.discard(k)
            return
        self._guardar_cotejo(kc, res)
        self._llego(k, clave, res)

    # ----------------------------------------------------------- canciones sin letra con tiempos
    def pedir_tiempos(self, p, datos):
        """La letra es solo texto (o no hay ninguna): se escucha la canción para ponerle tiempos (o para
        escribirla). Al acabar avisa con `listo` y {"accion": "letra", "datos": …} (o «sin_letra»)."""
        if not p or not self.activa() or not sincronia_letra.disponible() or self._modelo_falla:
            return False
        texto = ((datos or {}).get("texto") or "").strip()
        if not texto and (datos or {}).get("oida_nada"):
            return False                     # ya se escuchó y no se entendía
        if texto and (datos or {}).get("texto_nada"):
            return False
        self._intentar_tiempos(dict(p), dict(datos or {}), texto, REINTENTOS_FUENTE)
        return True

    def _intentar_tiempos(self, p, datos, texto, quedan):
        r = self.ctx.reproductor
        if clave_pista(r.actual) != clave_pista(p):
            return
        sonando = r.fuente_sonando() if hasattr(r, "fuente_sonando") else None
        if sonando is None:
            if quedan > 0:
                QTimer.singleShot(1500, self, lambda: self._intentar_tiempos(p, datos, texto, quedan - 1))
            return
        modo, fuente = sonando
        nombre = "sincronizar_texto" if texto else "transcribir"
        k = f"{clave_pista(p)}|{modo}|{nombre}"
        if k in self._memoria:
            self.listo.emit(clave_pista(p), self._memoria[k])
            return
        if k in self._en_curso:
            return
        self._en_curso.add(k)
        dur = float(getattr(r, "_duracion", 0) or (p.get("duracion") or 0))
        en_segundo_plano(_tarea_aparte, self._vigente(p), nombre, {"texto": texto, "fuente": fuente, "duracion": dur},
                         ok=lambda res, k=k: self._llegaron_tiempos(k, p, datos, texto, modo, res),
                         error=lambda e, k=k: self._fallo(k, e, clave_pista(p)), dueno=self, lento=True)

    def _llegaron_tiempos(self, k, p, datos, texto, modo, res):
        self._en_curso.discard(k)
        if res is None:
            return
        lineas = [(int(ms), str(t)) for ms, t in (res or {}).get("lineas") or []]
        if lineas:
            nuevos = {"sincronizada": True, "lineas": lineas, "escuchada": True, "verificada": False,
                      "texto": texto or "\n".join(t for _ms, t in lineas), "duracion": 0.0,
                      "fuente": (datos.get("fuente") or "") if texto else "Escuchada por Caudal (puede tener errores)"}
            final = {"accion": "letra", "desfase_ms": 0, "datos": nuevos, "detalle": "tiempos escuchados"}
        else:
            nuevos = dict(datos, sincronizada=False, lineas=[], texto=texto)
            nuevos["texto_nada" if texto else "oida_nada"] = True
            final = {"accion": "sin_letra", "desfase_ms": 0, "datos": None, "detalle": "no se pudo escuchar"}
        self._memoria[k] = final
        if modo == "audio":                  # los tiempos son de lo que sonó: el videoclip puede ser otro
            letras_cache.guardar(p, nuevos)
        self.listo.emit(clave_pista(p), final)

    @staticmethod
    def _clave_cotejo(p, modo, datos):
        ref = (datos or {}).get("ref")
        return f"{clave_pista(p)}|{modo}|cotejo:{ref}" if ref else ""

    def _cotejo_guardado(self, kc):
        try:
            t = (self.ctx.ajustes["letra_cotejo"] or {}).get(kc) if kc else None
            return [(float(a), float(b)) for a, b in t] if t else None
        except Exception:  # noqa: BLE001
            return None

    def _guardar_cotejo(self, kc, res):
        if not kc or not (res or {}).get("tramos"):
            return
        try:
            tabla = dict(self.ctx.ajustes["letra_cotejo"] or {})
            tabla[kc] = [list(x) for x in res["tramos"]]
            while len(tabla) > MAX_GUARDADOS:
                tabla.pop(next(iter(tabla)))
            self.ctx.ajustes["letra_cotejo"] = tabla
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass

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

    def _fallo(self, k, e, clave=""):
        self._en_curso.discard(k)
        if clave:
            self.listo.emit(clave, {"accion": "sin_letra", "desfase_ms": 0, "datos": None, "detalle": str(e)})
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
