# -*- coding: utf-8 -*-
"""Mensajes (como los de Spotify): conversaciones a la izquierda y el chat a
la derecha, con canciones que se tocan para sonar, emojis y «Mezcla»."""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu,
                               QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from ... import chat as CH
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Portada, _borrar_layout
from ..estilos import C
from .juntos import _fuente_emoji, menu_emojis


def chat_de(ctx):
    cuenta = getattr(ctx, "cuenta", None) or {}
    s = cuenta.get("sesion")
    return CH.Chat(s) if s and getattr(s, "access", "") else None


def _hora(f):
    ahora = time.time()
    t = f.timestamp()
    if ahora - t < 20 * 3600 and time.localtime(t).tm_mday == time.localtime(ahora).tm_mday:
        return f.strftime("%H:%M")
    if ahora - t < 7 * 86400:
        return ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"][f.weekday()]
    return f"{f.day}/{f.month}"


def _html(t):
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def nuevo_chat(ctx, padre, al_listo):
    """Pide un usuario y abre (o crea) la conversación con esa persona."""
    c = chat_de(ctx)
    if c is None:
        ctx.aviso.emit("Los mensajes necesitan internet.")
        return
    usuario, ok = QInputDialog.getText(padre, "Escribir a…", "Usuario de Caudal de la otra persona:")
    if not ok or not usuario.strip():
        return

    def buscar():
        p = c.buscar(usuario)
        if p is None:
            return None
        cid = c.abrir(p["id"])
        return {"id": cid, "otro": p["id"], "usuario": p["usuario"], "nombre": p.get("nombre") or "",
                "visible": p.get("nombre") or p["usuario"]}

    def listo(r):
        if r is None:
            ctx.aviso.emit(f"No hay nadie con el usuario «{usuario.strip()}». Pídele el suyo exacto.")
            return
        al_listo(r)

    en_segundo_plano(buscar, ok=listo, error=lambda _e: ctx.aviso.emit("No se pudo conectar."),
                     dueno=padre)


def enviar_pista_a_chat(ctx, pista):
    """«Enviar en un chat…» del menú de una canción."""
    c = chat_de(ctx)
    if c is None:
        ctx.aviso.emit("Los mensajes necesitan internet.")
        return
    ventana = getattr(ctx, "ventana", None)

    def mandar(destino):
        en_segundo_plano(c.enviar, destino["id"], "", pista,
                         ok=lambda _m: ctx.aviso.emit(f"Enviada a {destino['visible']}"),
                         error=lambda _e: ctx.aviso.emit("No se pudo enviar. Revisa tu internet."),
                         dueno=ventana)

    def con_chats(chats):
        from PySide6.QtGui import QCursor
        menu = QMenu(ventana)
        menu.addAction(iconos.icono("mas", 16, C["texto2"]), "Alguien nuevo…",
                       lambda: nuevo_chat(ctx, ventana, mandar))
        if chats:
            menu.addSeparator()
        for ch in chats[:30]:
            menu.addAction(f"{ch['visible']}   @{ch.get('usuario') or ''}", lambda ch=ch: mandar(ch))
        menu.exec(QCursor.pos())

    en_segundo_plano(c.mis_chats, ok=con_chats,
                     error=lambda _e: ctx.aviso.emit("No se pudo conectar. Revisa tu internet."),
                     dueno=ventana)


class PaginaMensajes(QWidget):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Mensajes"
        self.chat = chat_de(ctx)
        self.actual = None
        self.mensajes = []
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(self)
        h.setContentsMargins(24, 20, 24, 20)
        h.setSpacing(16)

        # ---- lista de conversaciones
        izq = QVBoxLayout()
        cab = QHBoxLayout()
        t = QLabel("Mensajes")
        t.setObjectName("titulo_pagina")
        cab.addWidget(t)
        cab.addStretch(1)
        nuevo = QPushButton("Nuevo")
        nuevo.setObjectName("principal")
        nuevo.setCursor(Qt.PointingHandCursor)
        nuevo.clicked.connect(lambda: nuevo_chat(self.ctx, self, self._abrir))
        cab.addWidget(nuevo)
        izq.addLayout(cab)
        self.scroll_lista = QScrollArea()
        self.scroll_lista.setWidgetResizable(True)
        self.scroll_lista.setFrameShape(QFrame.NoFrame)
        self.interior_lista = QWidget()
        self.lay_lista = QVBoxLayout(self.interior_lista)
        self.lay_lista.setContentsMargins(0, 0, 0, 0)
        self.lay_lista.setSpacing(4)
        self.lay_lista.addStretch(1)
        self.scroll_lista.setWidget(self.interior_lista)
        izq.addWidget(self.scroll_lista, 1)
        caja_izq = QWidget()
        caja_izq.setLayout(izq)
        caja_izq.setFixedWidth(320)
        h.addWidget(caja_izq)

        # ---- la conversación
        self.panel = QFrame()
        self.panel.setObjectName("panel_chat")
        self.panel.setStyleSheet(f"QFrame#panel_chat{{background:{C['panel']};border:1px solid {C['borde']};"
                                 "border-radius:16px;}")
        vp = QVBoxLayout(self.panel)
        vp.setContentsMargins(16, 12, 16, 12)
        vp.setSpacing(8)
        cab2 = QHBoxLayout()
        self.et_con = QLabel("Elige una conversación o empieza una nueva")
        self.et_con.setStyleSheet("font-size:18px;font-weight:800;background:transparent;")
        cab2.addWidget(self.et_con, 1)
        self.bt_mezcla = QPushButton("  Mezcla")
        self.bt_mezcla.setIcon(iconos.icono("estrella", 16, C["texto"]))
        self.bt_mezcla.setObjectName("contorno")
        self.bt_mezcla.setCursor(Qt.PointingHandCursor)
        self.bt_mezcla.setToolTip("Una lista con lo que escuchan los dos")
        self.bt_mezcla.clicked.connect(self._mezcla)
        cab2.addWidget(self.bt_mezcla)
        vp.addLayout(cab2)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("background:transparent;")
        self.interior = QWidget()
        self.interior.setStyleSheet("background:transparent;")
        self.lay = QVBoxLayout(self.interior)
        self.lay.setContentsMargins(0, 0, 6, 0)
        self.lay.setSpacing(6)
        self.lay.addStretch(1)
        self.scroll.setWidget(self.interior)
        vp.addWidget(self.scroll, 1)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.bt_emoji = QToolButton()
        self.bt_emoji.setText("😊")
        self.bt_emoji.setFont(_fuente_emoji(15))
        self.bt_emoji.setPopupMode(QToolButton.InstantPopup)
        self.bt_emoji.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    "padding:6px 8px;}QToolButton::menu-indicator{image:none;}")
        self.bt_emoji.setMenu(menu_emojis(self, lambda e: (self.campo.insert(e), self.campo.setFocus())))
        fila.addWidget(self.bt_emoji)
        self.bt_suena = QToolButton()
        self.bt_suena.setIcon(iconos.icono("musica", 18, C["acento"]))
        self.bt_suena.setToolTip("Enviar lo que suena")
        self.bt_suena.setCursor(Qt.PointingHandCursor)
        self.bt_suena.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    "padding:7px;}")
        self.bt_suena.clicked.connect(self._enviar_suena)
        fila.addWidget(self.bt_suena)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Mensaje")
        self.campo.setMaxLength(2000)
        self.campo.setFont(_fuente_emoji(10.5))
        self.campo.returnPressed.connect(self._enviar)
        fila.addWidget(self.campo, 1)
        enviar = QPushButton("Enviar")
        enviar.setObjectName("principal")
        enviar.setCursor(Qt.PointingHandCursor)
        enviar.clicked.connect(self._enviar)
        fila.addWidget(enviar)
        vp.addLayout(fila)
        h.addWidget(self.panel, 1)
        self._activar(False)

        self.reloj_lista = QTimer(self)
        self.reloj_lista.setInterval(10000)
        self.reloj_lista.timeout.connect(self._cargar_lista)
        self.reloj_chat = QTimer(self)
        self.reloj_chat.setInterval(3000)
        self.reloj_chat.timeout.connect(self._nuevos)
        if self.chat is None:
            self._sin_red()
        else:
            self._cargar_lista()
            self.reloj_lista.start()

    def _activar(self, si):
        for w in (self.bt_mezcla, self.bt_emoji, self.bt_suena, self.campo):
            w.setEnabled(si)

    def _sin_red(self):
        et = QLabel("Los mensajes necesitan internet. Vuelve a abrir Caudal con conexión.")
        et.setWordWrap(True)
        et.setObjectName("secundario")
        self.lay_lista.insertWidget(0, et)

    # ------------------------------------------------------------ lista
    def _cargar_lista(self):
        if self.chat is None or not self.isVisible() and self.lay_lista.count() > 1:
            return
        en_segundo_plano(self.chat.mis_chats, ok=self._pintar_lista, error=lambda _e: None, dueno=self)

    def _pintar_lista(self, chats):
        _borrar_layout(self.lay_lista)
        if not chats:
            et = QLabel("Escríbele a alguien por su usuario de Caudal, mándale canciones y "
                        "creen una mezcla con lo que escuchan los dos.")
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
        for c in chats:
            self.lay_lista.addWidget(self._fila(c))
        self.lay_lista.addStretch(1)

    def _fila(self, c):
        b = QPushButton()
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(64)
        activo = self.actual and self.actual["id"] == c["id"]
        b.setStyleSheet(f"QPushButton{{text-align:left;border:none;border-radius:12px;padding:0;"
                        f"background:{C['superficie2'] if activo else 'transparent'};}}"
                        f"QPushButton:hover{{background:{C['superficie']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 6, 10, 6)
        ini = QLabel((c["visible"] or "?")[:1].upper())
        ini.setFixedSize(40, 40)
        ini.setAlignment(Qt.AlignCenter)
        ini.setStyleSheet(f"background:{C['superficie3']};color:{C['acento']};border-radius:20px;"
                          "font-weight:900;font-size:16px;")
        h.addWidget(ini)
        col = QVBoxLayout()
        col.setSpacing(0)
        n = QLabel(c["visible"])
        sin = int(c.get("sin_leer") or 0)
        n.setStyleSheet(f"font-weight:{900 if sin else 700};background:transparent;")
        col.addWidget(n)
        prev = QLabel(CH.vista_previa(c, self.chat.yo))
        prev.setFont(_fuente_emoji(9))
        prev.setStyleSheet(f"color:{C['texto'] if sin else C['texto2']};background:transparent;")
        col.addWidget(prev)
        h.addLayout(col, 1)
        der = QVBoxLayout()
        der.addWidget(QLabel(_hora(c["fecha"])), 0, Qt.AlignRight)
        if sin:
            g = QLabel(str(sin))
            g.setAlignment(Qt.AlignCenter)
            g.setStyleSheet(f"background:{C['acento']};color:{C['acento_texto']};border-radius:9px;"
                            "font-size:11px;font-weight:900;padding:1px 7px;")
            der.addWidget(g, 0, Qt.AlignRight)
        h.addLayout(der)
        b.clicked.connect(lambda _=False, c=c: self._abrir(c))
        return b

    # ------------------------------------------------------------ conversacion
    def _abrir(self, c):
        self.actual = c
        self.mensajes = []
        self.et_con.setText(f"{c['visible']}   @{c.get('usuario') or ''}")
        self._activar(True)
        _borrar_layout(self.lay)
        self.lay.addStretch(1)
        en_segundo_plano(self.chat.mensajes, c["id"], ok=lambda l, cid=c["id"]: self._llegan(cid, l, True),
                         error=lambda _e: self.ctx.aviso.emit("No se pudo cargar la conversación."),
                         dueno=self)
        self.reloj_chat.start()
        self._cargar_lista()

    def _llegan(self, cid, lista, todo=False):
        if not self.actual or self.actual["id"] != cid:
            return
        ids = {m["id"] for m in self.mensajes}
        nuevos = [m for m in lista if m["id"] not in ids]
        for m in nuevos:
            self._burbuja(m)
        self.mensajes += nuevos
        if nuevos or todo:
            en_segundo_plano(self.chat.marcar_leido, cid, dueno=self)
            barra = self.scroll.verticalScrollBar()
            QTimer.singleShot(40, lambda: barra.setValue(barra.maximum()))

    def _nuevos(self):
        if not self.actual or not self.isVisible():
            return
        desde = self.mensajes[-1]["id"] if self.mensajes else 0
        cid = self.actual["id"]
        en_segundo_plano(self.chat.mensajes, cid, desde, ok=lambda l: self._llegan(cid, l),
                         error=lambda _e: None, dueno=self)

    def _burbuja(self, m):
        mio = str(m.get("autor")) == str(self.chat.yo)
        caja = QFrame()
        caja.setObjectName("burbuja")
        caja.setStyleSheet(f"QFrame#burbuja{{background:{C['acento'] if mio else C['superficie2']};"
                           "border-radius:14px;}")
        caja.setMaximumWidth(420)
        v = QVBoxLayout(caja)
        v.setContentsMargins(12, 8, 12, 6)
        v.setSpacing(2)
        color = C["acento_texto"] if mio else C["texto"]
        p = m.get("pista")
        if p:
            fila = QHBoxLayout()
            port = Portada(52, radio=6)
            port.set_url(p.get("miniatura") or "")
            fila.addWidget(port)
            txt = QLabel(f"<b>{_html(p.get('titulo'))}</b><br>"
                         f"<span style='font-size:11px'>{_html(p.get('artista'))}</span>")
            txt.setWordWrap(True)
            txt.setStyleSheet(f"color:{color};background:transparent;")
            fila.addWidget(txt, 1)
            play = QPushButton()
            play.setIcon(iconos.icono("reproducir", 18, C["acento_texto"] if not mio else C["acento"]))
            play.setFixedSize(34, 34)
            play.setCursor(Qt.PointingHandCursor)
            play.setStyleSheet(f"background:{C['acento'] if not mio else C['acento_texto']};border:none;"
                               "border-radius:17px;")
            play.clicked.connect(lambda _=False, p=p: self.ctx.reproducir_pista(p))
            fila.addWidget(play)
            v.addLayout(fila)
        else:
            t = QLabel(_html(m.get("texto")))
            t.setWordWrap(True)
            t.setTextInteractionFlags(Qt.TextSelectableByMouse)
            t.setFont(_fuente_emoji(10.5))
            t.setStyleSheet(f"color:{color};background:transparent;")
            v.addWidget(t)
        hora = QLabel(_hora(m["fecha"]))
        hora.setAlignment(Qt.AlignRight)
        hora.setStyleSheet(f"color:{'#2A5A66' if mio else C['texto3']};font-size:10px;background:transparent;")
        v.addWidget(hora)
        fila_ext = QHBoxLayout()
        if mio:
            fila_ext.addStretch(1)
        fila_ext.addWidget(caja)
        if not mio:
            fila_ext.addStretch(1)
        self.lay.insertLayout(self.lay.count() - 1, fila_ext)

    def _enviar(self, pista=None):
        if not self.actual:
            return
        texto = self.campo.text().strip()
        if not texto and pista is None:
            return
        cid = self.actual["id"]
        if pista is None:
            self.campo.clear()
        en_segundo_plano(self.chat.enviar, cid, "" if pista else texto, pista,
                         ok=lambda m: self._llegan(cid, [m]),
                         error=lambda _e: self.ctx.aviso.emit("No se pudo enviar. Revisa tu internet."),
                         dueno=self)

    def _enviar_suena(self):
        p = self.ctx.reproductor.actual
        if not p or not p.get("video_id"):
            self.ctx.aviso.emit("Ahora no suena nada que se pueda enviar.")
            return
        self._enviar(pista=p)

    def _mezcla(self):
        if not self.actual:
            return
        c = self.actual
        self.ctx.aviso.emit("Preparando su mezcla…")

        def listo(m):
            mix = CH.mix_de_mezcla(m, c["visible"], c["id"])
            if not mix["pistas"]:
                self.ctx.aviso.emit("Aún no hay suficiente: escuchen un poco más de música los dos.")
                return
            self.ctx.navegar({"pagina": "mix", "id": mix["id"], "el": mix})

        en_segundo_plano(self.chat.mezcla, c["id"], ok=listo,
                         error=lambda _e: self.ctx.aviso.emit("No se pudo crear la mezcla."), dueno=self)
