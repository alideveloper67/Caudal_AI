# -*- coding: utf-8 -*-
"""Explorar (novedades y generos) y las paginas de cada genero."""

from PySide6.QtWidgets import QLabel

from ... import catalogo
from ...hilos import en_segundo_plano
from ..componentes import Pagina
from .comun import cache, guardar_cache, pintar_secciones


class PaginaExplorar(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Explorar"
        self.set_color("#2B1F4A")
        t = QLabel("Explorar")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        self.cuerpo.addWidget(t)
        datos = cache("explorar", 60)
        if datos is not None:
            self._pintar(datos)
        else:
            self.espera = QLabel("Cargando novedades y géneros…")
            self.espera.setObjectName("secundario")
            self.cuerpo.addWidget(self.espera)
            en_segundo_plano(catalogo.explorar, ok=self._llego,
                             error=lambda e: self.error("Sin conexión con YouTube Music.",
                                                        lambda: ctx.navegar({"pagina": "explorar"})),
                             dueno=self)

    def _llego(self, datos):
        guardar_cache("explorar", datos)
        try:
            self.espera.deleteLater()
        except (RuntimeError, AttributeError):
            pass
        self._pintar(datos)

    def _pintar(self, datos):
        pintar_secciones(self.ctx, self.cuerpo, datos.get("secciones") or [])
        self.cuerpo.addStretch(1)


class PaginaGenero(Pagina):
    """Cualquier pagina de YouTube Music: un genero, un estado de animo, 'Mostrar todo'."""

    def __init__(self, ctx, ident, params=None, titulo="", padre=None):
        super().__init__(ctx, padre)
        self.ident = ident
        self.params = params
        self.titulo = titulo or "Explorar"
        self.set_color("#1F3A3F")
        self.et = QLabel(self.titulo)
        self.et.setObjectName("titulo_pagina")
        self.et.setStyleSheet("font-size:30px;font-weight:900;")
        self.cuerpo.addWidget(self.et)
        clave = ("pagina", ident, params)
        datos = cache(clave, 30)
        if datos is not None:
            self._pintar(datos)
        else:
            self.espera = QLabel("Cargando…")
            self.espera.setObjectName("secundario")
            self.cuerpo.addWidget(self.espera)
            en_segundo_plano(catalogo.pagina, ident, params, ok=lambda d: self._llego(clave, d),
                             error=lambda e: self.error(f"No se pudo abrir.\n{e}"), dueno=self)

    def _llego(self, clave, datos):
        guardar_cache(clave, datos)
        try:
            self.espera.deleteLater()
        except (RuntimeError, AttributeError):
            pass
        self._pintar(datos)

    def _pintar(self, datos):
        if datos.get("titulo"):
            self.titulo = datos["titulo"]
            self.et.setText(self.titulo)
            self.titulo_cambio.emit(self.titulo)
        secciones = datos.get("secciones") or []
        # una sola seccion grande se ve mejor en rejilla
        if len(secciones) == 1 and secciones[0]["estilo"] == "carrusel":
            secciones[0] = dict(secciones[0], estilo="rejilla")
        pintar_secciones(self.ctx, self.cuerpo, secciones)
        self.cuerpo.addStretch(1)
