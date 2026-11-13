# -*- coding: utf-8 -*-
"""Inicio: lo tuyo arriba, y lo que propone YouTube Music debajo."""

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from ... import catalogo
from ...hilos import en_segundo_plano
from ..componentes import Carrusel, Chip, Pagina
from .comun import Atajo, cache, guardar_cache, pintar_secciones


def saludo():
    h = time.localtime().tm_hour
    if 5 <= h < 12:
        return "Buenos días"
    if 12 <= h < 19:
        return "Buenas tardes"
    return "Buenas noches"


class PaginaInicio(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Inicio"
        self.set_color("#16324A")
        self.filtro = "todo"
        self._construir()

    def _construir(self):
        ctx = self.ctx
        col = ctx.coleccion
        cab = QHBoxLayout()
        cuenta = getattr(ctx, "cuenta", None) or {}
        nombre = (cuenta.get("nombre") or "").split(" ")[0]
        t = QLabel(f"{saludo()}, {nombre}" if nombre else saludo())
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.cuerpo.addLayout(cab)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chips = {}
        for clave, texto in (("todo", "Todo"), ("musica", "Música"), ("videos", "Videos"),
                             ("disco", "En tu disco")):
            c = Chip(texto)
            c.setChecked(clave == self.filtro)
            c.clicked.connect(lambda _=False, k=clave: self._filtrar(k))
            chips.addWidget(c)
            self.chips[clave] = c
        chips.addStretch(1)
        self.cuerpo.addLayout(chips)

        self.zona = QWidget()
        from PySide6.QtWidgets import QVBoxLayout
        self.zv = QVBoxLayout(self.zona)
        self.zv.setContentsMargins(0, 0, 0, 0)
        self.zv.setSpacing(30)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        self._pintar()

    def _filtrar(self, clave):
        self.filtro = clave
        for k, c in self.chips.items():
            c.setChecked(k == clave)
        self._pintar()

    def _limpiar(self):
        from ..componentes import _borrar_layout
        _borrar_layout(self.zv)

    def _pintar(self):
        self._limpiar()
        ctx = self.ctx
        col = ctx.coleccion
        if self.filtro in ("todo", "musica"):
            self._atajos()
            recientes = [p for p in col.escuchado_hace_poco(24)
                         if self.filtro == "todo" or not p.get("es_video")]
            if recientes:
                self.zv.addWidget(Carrusel(ctx, "Volver a escuchar", recientes,
                                           subtitulo="lo último que sonó"))
            mixes = self._mixes()
            if mixes:
                self.zv.addWidget(Carrusel(ctx, "Tus mixes", mixes,
                                           subtitulo="hechos con lo que más escuchas"))
        if self.filtro == "disco":
            musica = col.descargadas(True)
            videos = col.descargadas(False)
            if musica:
                self.zv.addWidget(Carrusel(ctx, "Tu música descargada", musica[:40],
                                           mas=lambda: ctx.navegar({"pagina": "disco", "solo": True})))
            if videos:
                self.zv.addWidget(Carrusel(ctx, "Tus videos descargados", videos[:40],
                                           mas=lambda: ctx.navegar({"pagina": "disco", "solo": False})))
            if not musica and not videos:
                from ..componentes import SinResultados
                self.zv.addWidget(SinResultados(
                    "descargar", "Aún no hay nada en tu disco",
                    "Descarga canciones o videos y aparecerán aquí para escucharlos sin internet."))
            return

        if self.filtro == "videos":
            recientes_v = [p for p in col.escuchado_hace_poco(30) if p.get("es_video")]
            if recientes_v:
                self.zv.addWidget(Carrusel(ctx, "Videos que viste", recientes_v))

        datos = cache("inicio")
        if datos is not None:
            self._con_catalogo(datos)
        else:
            from ..componentes import Esqueleto
            self.et_cargando = Esqueleto("tarjetas")
            self.zv.addWidget(self.et_cargando)
            en_segundo_plano(catalogo.inicio, ok=self._llego, error=self._sin_red, dueno=self)

    def _llego(self, datos):
        guardar_cache("inicio", datos)
        if getattr(self, "et_cargando", None) is not None:
            try:
                self.et_cargando.deleteLater()
            except RuntimeError:
                pass
            self.et_cargando = None
        self._con_catalogo(datos)

    def _con_catalogo(self, datos):
        secciones = datos.get("secciones") or []
        if self.filtro == "videos":
            secciones = [dict(s, elementos=[e for e in s["elementos"]
                                            if e.get("tipo") == "pista" and e.get("es_video")])
                         for s in secciones]
            secciones = [s for s in secciones if len(s["elementos"]) >= 3]
            for s in secciones:
                s["estilo"] = "carrusel"
        elif self.filtro == "musica":
            secciones = [s for s in secciones
                         if not all(e.get("tipo") == "pista" and e.get("es_video")
                                    for e in s["elementos"])]

        pintar_secciones(self.ctx, self.zv, secciones)

    def _sin_red(self, _e):
        if getattr(self, "et_cargando", None) is not None:
            try:
                self.et_cargando.deleteLater()
                self.et_cargando = None
                from ..componentes import SinResultados
                self.zv.addWidget(SinResultados(
                    "globo", "Sin conexión con YouTube Music",
                    "Mientras vuelve, tienes lo descargado en «En tu disco»."))
            except RuntimeError:
                pass

    def _atajos(self):
        col = self.ctx.coleccion
        elementos = [{"tipo": "me_gusta", "especial": "me_gusta", "titulo": "Tus me gusta"}]
        vistos = set()
        for c in col.contextos_recientes(12):
            clave = (c.get("tipo"), str(c.get("id")))
            if clave in vistos or c.get("tipo") not in ("album", "lista", "mi_lista", "radio",
                                                         "artista"):
                continue
            vistos.add(clave)
            el = {"tipo": c["tipo"], "id": c["id"], "titulo": c.get("titulo") or "",
                  "miniatura": c.get("miniatura") or ""}
            if c["tipo"] == "mi_lista":
                portadas = col.portadas_de_lista(c["id"], 1)
                el["miniatura"] = portadas[0] if portadas else ""
            if c["tipo"] == "radio":
                el["miniatura"] = el["miniatura"] or self._portada_radio(c)
            elementos.append(el)
        for l in col.listas()[:8]:
            clave = ("mi_lista", str(l["id"]))
            if clave not in vistos:
                vistos.add(clave)
                portadas = col.portadas_de_lista(l["id"], 1)
                elementos.append({"tipo": "mi_lista", "id": l["id"], "titulo": l["nombre"],
                                  "miniatura": portadas[0] if portadas else ""})
        elementos = elementos[:8]
        if len(elementos) < 2:
            return
        caja = QWidget()
        rej = QGridLayout(caja)
        rej.setContentsMargins(0, 0, 0, 0)
        rej.setSpacing(8)
        columnas = 4 if len(elementos) > 4 else 2
        for i, el in enumerate(elementos):
            a = Atajo(self.ctx, el)
            a.abrir.connect(self._abrir_atajo)
            a.reproducir.connect(self.ctx.reproducir_elemento)
            rej.addWidget(a, i // columnas, i % columnas)
        self.zv.addWidget(caja)

    def _portada_radio(self, c):
        for p in self.ctx.coleccion.escuchado_hace_poco(40):
            if p.get("video_id") == c.get("id"):
                return p.get("miniatura") or ""
        return ""

    def _abrir_atajo(self, el):
        if el.get("tipo") == "radio":
            if el.get("id") and len(str(el["id"])) == 11:
                p = next((x for x in self.ctx.coleccion.escuchado_hace_poco(60)
                          if x.get("video_id") == el["id"]), None)
                if p:
                    self.ctx.reproductor.iniciar_radio(p)
                    return
            self.ctx.reproductor.reproducir_radio_id(el["id"], el.get("titulo") or "Radio")
        else:
            self.ctx.abrir_elemento(el)

    def _mixes(self):
        col = self.ctx.coleccion
        salida = []
        historial = col.escuchado_hace_poco(150) + col.lista_me_gusta()[:100]
        for a in col.artistas_frecuentes(8):
            portada = next((p.get("miniatura") for p in historial
                            if any(x.get("id") == a["id"] for x in p.get("artistas") or [])), "")
            salida.append({"tipo": "artista", "id": a["id"], "titulo": f"Mix de {a['nombre']}",
                           "subtitulo": f"{a['nombre']} y artistas parecidos",
                           "miniatura": portada})
        return salida


def _sin_usar():  # pragma: no cover
    return Qt
