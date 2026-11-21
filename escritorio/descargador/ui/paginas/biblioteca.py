# -*- coding: utf-8 -*-
"""Tu biblioteca en grande: listas, albumes, artistas y lo descargado."""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from .. import iconos
from ...hilos import en_segundo_plano
from ..componentes import Chip, Esqueleto, Pagina, _borrar_layout
from ..estilos import C
from .comun import Rejilla


def _descargadas_fondo(col):
    """Las descargas del disco (cada archivo se comprueba en la PC): corre en segundo plano con
    una conexión propia a la base, si la colección la ofrece."""
    copiar = getattr(col, "copia_de_lectura", None)
    if copiar is None:
        return col.descargadas()[:300]
    with copiar() as c:
        return c.descargadas()[:300]


class PaginaBiblioteca(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Tu biblioteca"
        self.filtro = "todo"
        self._pedido_disco = 0
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
        importar = QPushButton("  Importar de tu PC")
        importar.setObjectName("contorno")
        importar.setIcon(iconos.icono("carpeta", 15, C["texto"]))
        importar.setToolTip("Canciones que ya tienes en la computadora (MP3, M4A, FLAC...)")
        importar.clicked.connect(ctx.importar_de_pc)
        cab.addWidget(importar)
        traer = QPushButton("  Traer una lista")
        traer.setObjectName("contorno")
        traer.setIcon(iconos.icono("anadir_lista", 15, C["texto"]))
        traer.setToolTip("De Spotify, Apple Music o YouTube Music")
        traer.clicked.connect(lambda: ctx.ventana._traer_lista())
        cab.addWidget(traer)
        codigo = QPushButton("  Tengo un código")
        codigo.setObjectName("contorno")
        codigo.setIcon(iconos.icono("compartir", 15, C["texto"]))
        codigo.setToolTip("Unirte a una lista que te compartieron")
        codigo.clicked.connect(lambda: ctx.tengo_un_codigo())
        cab.addWidget(codigo)
        cab.addWidget(nueva)
        self.cuerpo.addLayout(cab)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chips = {}
        for clave, texto in (("todo", "Todo"), ("listas", "Listas"), ("compartidas", "Compartidas"),
                             ("albumes", "Álbumes"),
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
        self._traer_compartidas()

    def _filtrar(self, clave):
        self.filtro = clave
        for k, c in self.chips.items():
            c.setChecked(k == clave)
        self._pintar()

    def _compartidas(self):
        from ... import listas_compartidas as LC
        datos = LC.ultima_conocida("mis_compartidas")
        return datos if datos is not None else LC.compartidas_guardadas(self.ctx.coleccion)

    def _traer_compartidas(self):
        """Las listas de otras personas: se pinta lo último que se sabía y se actualiza en segundo plano."""
        from ... import listas_compartidas as LC
        from ...hilos import en_segundo_plano
        from ..contexto import nube_de
        nube = nube_de(self.ctx)
        if nube is None or LC.en_cache("mis_compartidas", 20) is not None:
            return

        def listo(filas):
            anterior = self._compartidas()
            LC.guardar_cache("mis_compartidas", filas)
            LC.guardar_compartidas(self.ctx.coleccion, filas)
            if filas != anterior:
                self._pintar()
        en_segundo_plano(nube.mis_compartidas, ok=listo, error=lambda _e: None, dueno=self)

    def _disco_llego(self, n, filas):
        # una respuesta vieja (pedida antes de cambiar de filtro) no pinta nada
        if n != self._pedido_disco or self.filtro != "disco":
            return
        self._pintar_disco(filas)

    def _pintar_disco(self, filas):
        _borrar_layout(self.zv)
        if not filas:
            from ..componentes import SinResultados
            self.zv.addWidget(SinResultados("biblioteca", "Aquí no hay nada todavía",
                                            "Guarda álbumes, sigue artistas o crea listas."))
            return
        self.zv.addWidget(Rejilla(self.ctx, "", filas))

    def _pintar(self, *_):
        _borrar_layout(self.zv)
        col = self.ctx.coleccion
        f = self.filtro
        if f == "disco":
            # leer el disco comprueba cada archivo: va en segundo plano y muestra el esqueleto mientras
            self._pedido_disco += 1
            n = self._pedido_disco
            self.zv.addWidget(Esqueleto("filas"))
            en_segundo_plano(_descargadas_fondo, col, ok=lambda r, n=n: self._disco_llego(n, r),
                             error=lambda _e, n=n: self._disco_llego(n, []), dueno=self)
            return
        el = []
        from ... import listas_compartidas as LC
        mias_comp = {u for u in LC.codigos_guardados(col)}
        if f in ("todo", "listas"):
            n = col.total_me_gusta()
            el.append({"tipo": "me_gusta", "titulo": "Tus me gusta",
                       "subtitulo": f"{n} canciones", "miniatura": ""})
            for l in col.listas():
                portadas = col.portadas_de_lista(l["id"], 1)
                el.append({"tipo": "mi_lista", "id": l["id"], "titulo": l["nombre"],
                           "subtitulo": f"Lista • {l['n']} canciones"
                                        + (" • Compartida" if l.get("uuid") in mias_comp else ""),
                           "miniatura": portadas[0] if portadas else ""})
            el += col.guardados("lista")
        if f in ("todo", "albumes"):
            el += col.guardados("album")
        if f in ("todo", "artistas"):
            el += [dict(g, subtitulo="Artista") for g in col.guardados("artista")]
        comp = []
        if f in ("todo", "listas", "compartidas"):
            comp = [{"tipo": "lista_compartida", "id": c["id"], "titulo": c["nombre"],
                     "subtitulo": "Compartida · " + LC.nombre_persona(c["dueno"]),
                     "rol": c["rol"], "dueno": c["dueno"], "miniatura": ""}
                    for c in self._compartidas()]
        if not el and not comp and f != "compartidas":
            from ..componentes import SinResultados
            self.zv.addWidget(SinResultados("biblioteca", "Aquí no hay nada todavía",
                                            "Guarda álbumes, sigue artistas o crea listas."))
            return
        if el:
            self.zv.addWidget(Rejilla(self.ctx, "", el))
        if comp:
            self.zv.addSpacing(18)
            self.zv.addWidget(Rejilla(self.ctx, "Listas compartidas", comp))
        elif f == "compartidas":
            from ..componentes import SinResultados
            self.zv.addWidget(SinResultados("compartir", "Aquí aparecerán las listas que compartan contigo",
                                            "Pulsa «Tengo un código» y escribe el que te pasaron."))
