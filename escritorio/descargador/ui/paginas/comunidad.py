# -*- coding: utf-8 -*-
"""Comunidad: el catálogo de la música que sube la gente, con buscador. Se escucha,
se reporta y (lo propio) se borra.

    PaginaComunidad(ctx)
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Esqueleto, SinResultados, suavizar
from ..estilos import C
from . import perfil_comun as PC

LOTE = 30


class PaginaComunidad(QWidget):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Comunidad"
        self.social = S.social_de(ctx)
        self.yo = (getattr(self.social, "yo", "") if self.social else "") or ""
        self.busqueda = ""
        self.subidas = []
        self.desde = 0
        self.fin = False
        self.cargando = False
        self._generacion = 0
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 0)
        raiz.setSpacing(12)
        cab = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Comunidad")
        t.setObjectName("titulo_pagina")
        col.addWidget(t)
        col.addWidget(PC.etiqueta("La música que sube la gente de Caudal. Escúchala, y si algo no debería "
                                  "estar aquí, repórtalo.", f"color:{C['texto2']};"))
        cab.addLayout(col, 1)
        cab.addWidget(PC.boton("Subir mi música", "principal", "compartir",
                               al_pulsar=lambda: ctx.navegar({"pagina": "subir_musica"})), 0, Qt.AlignTop)
        raiz.addLayout(cab)
        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setObjectName("buscador")
        self.campo.setPlaceholderText("Buscar por título o artista")
        self.campo.setMaximumWidth(420)
        self.campo.addAction(iconos.icono("lupa", 16, C["texto3"]), QLineEdit.LeadingPosition)
        self.campo.textChanged.connect(lambda _t: self.reloj.start())
        fila.addWidget(self.campo)
        fila.addStretch(1)
        self.bt_todo = PC.boton("Reproducir todo", "contorno", "reproducir", al_pulsar=self._todo)
        self.bt_todo.hide()
        fila.addWidget(self.bt_todo)
        raiz.addLayout(fila)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        suavizar(self.area)
        self.interior = QWidget()
        self.interior.setObjectName("interior_com")
        self.interior.setStyleSheet("QWidget#interior_com{background:transparent;}")
        iv = QVBoxLayout(self.interior)
        iv.setContentsMargins(0, 4, 6, 24)
        iv.setSpacing(8)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(8)
        iv.addLayout(self.lista)
        self.pie = QVBoxLayout()
        iv.addLayout(self.pie)
        iv.addStretch(1)
        self.area.setWidget(self.interior)
        self.area.verticalScrollBar().valueChanged.connect(self._al_desplazar)
        raiz.addWidget(self.area, 1)
        self.reloj = QTimer(self)
        self.reloj.setSingleShot(True)
        self.reloj.setInterval(450)
        self.reloj.timeout.connect(self._nueva_busqueda)
        if self.social is None:
            self.pie.addWidget(SinResultados("musica", "La comunidad necesita tu cuenta",
                                             "Abre Caudal con internet e inicia sesión para escuchar a la comunidad."))
        else:
            self._cargar_mas()

    def _nueva_busqueda(self):
        texto = self.campo.text().strip()
        if texto == self.busqueda and self.subidas:
            return
        self.busqueda = texto
        self.recargar()

    def recargar(self):
        self._generacion += 1
        PC.limpiar(self.lista)
        PC.limpiar(self.pie)
        self.subidas, self.desde, self.fin, self.cargando = [], 0, False, False
        self._cargar_mas()

    def _cargar_mas(self):
        if self.social is None or self.cargando or self.fin:
            return
        self.cargando = True
        gen = self._generacion
        PC.limpiar(self.pie)
        self.pie.addWidget(Esqueleto("filas") if not self.subidas else
                           PC.etiqueta("Cargando más canciones…", f"color:{C['texto3']};", False))
        en_segundo_plano(self.social.explorar_subidas, self.busqueda, LOTE, self.desde,
                         ok=lambda r, g=gen: self._llegan(g, r),
                         error=lambda e, g=gen: self._fallo(g, e), dueno=self, urgente=True)

    def _llegan(self, gen, nuevas):
        if gen != self._generacion:
            return
        self.cargando = False
        PC.limpiar(self.pie)
        self.desde += len(nuevas)
        self.fin = len(nuevas) < LOTE
        for s in nuevas:
            self.subidas.append(s)
            propia = bool(self.yo) and s["user_id"] == self.yo
            t = PC.TarjetaSubida(s, propia=propia)
            t.reproducir.connect(lambda s=s: self._tocar(s))
            t.reportar.connect(lambda s=s: PC.reportar_subida(self.ctx, self.social, s, self))
            t.borrar.connect(lambda s=s: PC.borrar_subida(self.ctx, self.social, s, self, self.recargar))
            t.abrir_perfil.connect(lambda u: self.ctx.navegar({"pagina": "perfil", "usuario": u}))
            self.lista.addWidget(t)
        self.bt_todo.setVisible(bool(self.subidas))
        if not self.subidas:
            if self.busqueda:
                self.pie.addWidget(SinResultados("lupa", "Sin resultados",
                                                 f"No hay canciones que coincidan con «{self.busqueda}»."))
            else:
                self.pie.addWidget(SinResultados(
                    "musica", "Todavía no hay música aquí",
                    "Sé la primera persona en compartir una canción: pulsa «Subir mi música»."))
        elif not self.fin:
            self.pie.addWidget(PC.boton("Mostrar más canciones", "contorno", al_pulsar=self._cargar_mas), 0,
                               Qt.AlignCenter)
        QTimer.singleShot(0, self._al_desplazar)

    def _fallo(self, gen, e):
        if gen != self._generacion:
            return
        self.cargando = False
        PC.limpiar(self.pie)
        self.pie.addWidget(PC.etiqueta(S.explicar(e, "cargar la música de la comunidad"), f"color:{C['error']};"))
        self.pie.addWidget(PC.boton("Reintentar", "contorno", al_pulsar=self._cargar_mas), 0, Qt.AlignLeft)

    def _al_desplazar(self, *_):
        b = self.area.verticalScrollBar()
        if self.subidas and not self.fin and not self.cargando and b.value() >= b.maximum() - 300:
            self._cargar_mas()

    def _tocar(self, s):
        PC.reproducir_subidas(self.ctx, self.social, self.subidas, self.subidas.index(s), self)

    def _todo(self):
        if self.subidas:
            PC.reproducir_subidas(self.ctx, self.social, self.subidas, 0, self)
