# -*- coding: utf-8 -*-
"""Tu biblioteca en grande: listas, albumes, artistas y lo descargado."""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from .. import iconos
from ..componentes import Chip, Pagina, _borrar_layout
from ..estilos import C
from .comun import Rejilla


class PaginaBiblioteca(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Tu biblioteca"
        self.filtro = "todo"
        cab = QHBoxLayout()
        t = QLabel("Tu biblioteca")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        cab.addWidget(t)
        cab.addStretch(1)
        nueva = QPushButton("  Crear una lista")
        nueva.setObjectName("contorno")
        nueva.setIcon(iconos.icono("mas", 15, C["texto"]))
        nueva.clicked.connect(ctx.crear_lista)
        cab.addWidget(nueva)
        self.cuerpo.addLayout(cab)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chips = {}
        for clave, texto in (("todo", "Todo"), ("listas", "Listas"), ("albumes", "Álbumes"),
                             ("artistas", "Artistas"), ("disco", "En tu disco")):
            c = Chip(texto)
            c.setChecked(clave == self.filtro)
            c.clicked.connect(lambda _=False, k=clave: self._filtrar(k))
            chips.addWidget(c)
            self.chips[clave] = c
        chips.addStretch(1)
        self.cuerpo.addLayout(chips)
        from PySide6.QtWidgets import QVBoxLayout, QWidget
        self.zona = QWidget()
        self.zv = QVBoxLayout(self.zona)
        self.zv.setContentsMargins(0, 0, 0, 0)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        for s in (ctx.listas_cambio, ctx.guardados_cambio, ctx.descargas_cambio):
            s.connect(self._pintar)
        self._pintar()

    def _filtrar(self, clave):
        self.filtro = clave
        for k, c in self.chips.items():
            c.setChecked(k == clave)
        self._pintar()

    def _pintar(self, *_):
        _borrar_layout(self.zv)
        col = self.ctx.coleccion
        f = self.filtro
        el = []
        if f in ("todo", "listas"):
            n = col.total_me_gusta()
            el.append({"tipo": "me_gusta", "titulo": "Tus me gusta",
                       "subtitulo": f"{n} canciones", "miniatura": ""})
            for l in col.listas():
                portadas = col.portadas_de_lista(l["id"], 1)
                el.append({"tipo": "mi_lista", "id": l["id"], "titulo": l["nombre"],
                           "subtitulo": f"Lista • {l['n']} canciones",
                           "miniatura": portadas[0] if portadas else ""})
            el += col.guardados("lista")
        if f in ("todo", "albumes"):
            el += col.guardados("album")
        if f in ("todo", "artistas"):
            el += [dict(g, subtitulo="Artista") for g in col.guardados("artista")]
        if f == "disco":
            el += col.descargadas()[:300]
        if not el:
            from ..componentes import SinResultados
            self.zv.addWidget(SinResultados("biblioteca", "Aquí no hay nada todavía",
                                            "Guarda álbumes, sigue artistas o crea listas."))
            return
        self.zv.addWidget(Rejilla(self.ctx, "", el))
