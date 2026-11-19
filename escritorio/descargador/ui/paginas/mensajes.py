# -*- coding: utf-8 -*-
"""Mensajes (como los de Spotify): conversaciones a la izquierda y el chat a
la derecha, con canciones que se tocan para sonar, emojis y «Mezcla»."""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from ... import chat as CH
from ... import listas_compartidas as LC
from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Portada, _borrar_layout
from ..estilos import C
from ..premium_estilos import nombre_efecto
from .amigos import PanelAmigos, PanelSolicitudes
from .juntos import _fuente_emoji, menu_emojis
from .perfil_comun import Avatar


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


class DialogoNuevoChat(QDialog):
    """Elige a quién escribir: solo la lista de tus amigos (con buscador y foto). Para
    escribirle a alguien nuevo primero hay que agregarlo como amigo."""

    def __init__(self, ctx, chat, padre=None):
        super().__init__(padre)
        from .. import iconos as _i
        from ..estilos import hoja
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(_i.flechas_qss()))
        self.setWindowTitle("Nuevo mensaje · Caudal")
        self.setMinimumSize(440, 480)
        self.ctx = ctx
        self.chat = chat
        self.resultado = None
        self.ir_a_amigos = False
        self.amigos = []
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(10)
        t = QLabel("Nuevo mensaje")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        nota = QLabel("Elige a quién escribirle. Solo puedes escribir a tus amigos.")
        nota.setWordWrap(True)
        nota.setObjectName("ayuda")
        v.addWidget(nota)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Buscar entre mis amigos")
        self.campo.textChanged.connect(self._filtrar)
        v.addWidget(self.campo)
        self.estado = QLabel("Cargando tus amigos…")
        self.estado.setWordWrap(True)
        self.estado.setObjectName("secundario")
        v.addWidget(self.estado)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setObjectName("interior_nuevo")
        self.interior.setStyleSheet("QWidget#interior_nuevo{background:transparent;}")
        self.lista = QVBoxLayout(self.interior)
        self.lista.setContentsMargins(0, 0, 6, 0)
        self.lista.setSpacing(4)
        self.lista.addStretch(1)
        self.area.setWidget(self.interior)
        v.addWidget(self.area, 1)
        fila = QHBoxLayout()
        agregar = QPushButton("  Agregar un amigo")
        agregar.setIcon(iconos.icono("mas", 16, C["texto"]))
        agregar.setObjectName("contorno")
        agregar.setCursor(Qt.PointingHandCursor)
        agregar.setToolTip("Buscar a alguien por su usuario y enviarle una solicitud")
        agregar.clicked.connect(self._agregar)
        fila.addWidget(agregar)
        fila.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("contorno")
        cancelar.clicked.connect(self.reject)
        fila.addWidget(cancelar)
        v.addLayout(fila)
        social = S.Social(chat.sesion)
        en_segundo_plano(social.mis_amigos, ok=self._llegan,
                         error=lambda e: self.estado.setText(S.explicar(e, "cargar tus amigos")),
                         dueno=self, urgente=True)

    # ------------------------------------------------------------ lista
    def _llegan(self, amigos):
        self.amigos = amigos
        self._filtrar()

    def _filtrar(self, *_):
        _borrar_layout(self.lista)
        q = self.campo.text().strip().lstrip("@").lower()
        vistos = [p for p in self.amigos
                  if not q or q in (p.get("usuario") or "").lower() or q in (p.get("nombre") or "").lower()]
        if not self.amigos:
            self.estado.setText("Aún no tienes amigos con quien hablar. Pulsa «Agregar un amigo», busca su "
                                "usuario y envíale una solicitud: cuando la acepte podrán escribirse.")
        elif not vistos:
            self.estado.setText(f"Ninguno de tus amigos coincide con «{self.campo.text().strip()}».")
        else:
            self.estado.setText("")
        self.estado.setVisible(bool(self.estado.text()))
        for p in vistos:
            self.lista.addWidget(self._fila(p))
        self.lista.addStretch(1)

    def _fila(self, p):
        b = QPushButton()
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(58)
        b.setFocusPolicy(Qt.NoFocus)
        b.setStyleSheet(f"QPushButton{{text-align:left;border:none;border-radius:12px;background:transparent;}}"
                        f"QPushButton:hover{{background:{C['superficie2']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 6, 10, 6)
        h.addWidget(Avatar(42, S.nombre_visible(p), C["acento"], p.get("foto_url"), marco=p.get("marco")))
        col = QVBoxLayout()
        col.setSpacing(0)
        n = nombre_efecto(S.nombre_visible(p), "font-weight:700;", p.get("efecto_nombre"), False)
        u = QLabel("@" + (p.get("usuario") or ""))
        u.setStyleSheet(f"color:{C['texto3']};font-size:11.5px;background:transparent;")
        col.addWidget(n)
        col.addWidget(u)
        h.addLayout(col, 1)
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False, p=p: self._abrir(p))
        return b

    def _agregar(self):
        self.ir_a_amigos = True
        self.reject()

    def _abrir(self, p):
        self.estado.setText("Abriendo la conversación…")
        self.estado.show()

        def listo(cid):
            self.resultado = {"id": cid, "otro": p["id"], "usuario": p["usuario"], "nombre": p.get("nombre") or "",
                              "visible": S.nombre_visible(p), "es_amigo": True}
            self.accept()

        en_segundo_plano(self.chat.abrir, p["id"], ok=listo,
                         error=lambda e: self.estado.setText(S.explicar(e, "abrir la conversación")),
                         dueno=self, urgente=True)


def nuevo_chat(ctx, padre, al_listo):
    """Elige entre tus amigos y abre el chat. «Agregar un amigo» lleva a la pantalla de Amigos."""
    c = chat_de(ctx)
    if c is None:
        ctx.aviso.emit("Los mensajes necesitan internet.")
        return
    d = DialogoNuevoChat(ctx, c, padre)
    if d.exec() == QDialog.Accepted and d.resultado:
        al_listo(d.resultado)
    elif d.ir_a_amigos:
        ctx.navegar({"pagina": "amigos", "pestana": "amigos"})


def _pedir_destino(ctx, mandar):
    """Muestra a quién enviarlo (tus conversaciones o alguien nuevo) y llama a `mandar(destino)`."""
    c = chat_de(ctx)
    if c is None:
        ctx.aviso.emit("Los mensajes necesitan internet.")
        return
    ventana = getattr(ctx, "ventana", None)

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

    en_segundo_plano(c.solo_amigos, ok=con_chats,
                     error=lambda _e: ctx.aviso.emit("No se pudo conectar. Revisa tu internet."),
                     dueno=ventana, urgente=True)


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
                         error=lambda e: ctx.aviso.emit(_motivo(e)),
                         dueno=ventana, urgente=True)
    _pedir_destino(ctx, mandar)


def enviar_lista_a_chat(ctx, tarjeta):
    """«Enviar por el chat» del diálogo de compartir: la lista ya tiene código; falta elegir a quién."""
    c = chat_de(ctx)
    if c is None:
        ctx.aviso.emit("Los mensajes necesitan internet.")
        return
    ventana = getattr(ctx, "ventana", None)

    def mandar(destino):
        en_segundo_plano(c.enviar, destino["id"], "", None, tarjeta,
                         ok=lambda _m: ctx.aviso.emit(f"Lista enviada a {destino['visible']}"),
                         error=lambda e: ctx.aviso.emit(_motivo(e)),
                         dueno=ventana, urgente=True)
    _pedir_destino(ctx, mandar)


def _motivo(e, que="enviar"):
    """Un error de la nube contado para personas (sin jerga)."""
    from ...nube import ErrorNube, SinConexion
    if isinstance(e, SinConexion):
        return "Sin conexión. Revisa tu internet y vuelve a intentarlo."
    if isinstance(e, ErrorNube) and str(e).strip():
        return str(e)
    return f"No se pudo {que}. Vuelve a intentarlo."


class PaginaMensajes(QWidget):
    ANCHO_LISTA = 320      # la lista de chats cuando sobra espacio
    ESTRECHO = 700         # por debajo, se ve la lista o el chat, no los dos

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Mensajes"
        self.chat = chat_de(ctx)
        self.actual = None
        self.mensajes = []          # los confirmados por el servidor
        self.pendientes = {}        # clave local -> (burbuja, etiqueta de hora, texto, pista)
        self._siguiente_local = 0
        self._enviando = 0
        self.cargando = None
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(self)
        h.setContentsMargins(24, 20, 24, 20)
        h.setSpacing(16)
        # sin ancho mínimo rígido: con poco sitio se ve la lista o la conversación (ver _acomodar),
        # así que la suma de las dos no debe impedir que la página se estreche
        h.setSizeConstraint(QHBoxLayout.SetNoConstraint)

        # ---- lista de conversaciones
        izq = QVBoxLayout()
        izq.setContentsMargins(0, 0, 0, 0)
        cab = QHBoxLayout()
        t = QLabel("Mensajes")
        t.setObjectName("titulo_pagina")
        cab.addWidget(t)
        cab.addStretch(1)
        nuevo = QPushButton("  Nuevo")
        nuevo.setIcon(iconos.icono("mas", 16, C["acento_texto"]))
        nuevo.setObjectName("principal")
        nuevo.setCursor(Qt.PointingHandCursor)
        nuevo.setToolTip("Escribirle a alguien por su usuario de Caudal")
        nuevo.clicked.connect(lambda: nuevo_chat(self.ctx, self, self._abrir))
        cab.addWidget(nuevo)
        izq.addLayout(cab)
        tabs = QHBoxLayout()
        tabs.setSpacing(0)
        self.tabs = {}
        for clave, texto in (("chats", "Chats"), ("solicitudes", "Solicitudes"), ("amigos", "Amigos")):
            b = QPushButton(texto)
            b.setObjectName("pestana")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, k=clave: self._pestana(k))
            self.tabs[clave] = b
            tabs.addWidget(b)
        tabs.addStretch(1)
        izq.addLayout(tabs)
        self.scroll_lista = QScrollArea()
        self.scroll_lista.setWidgetResizable(True)
        self.scroll_lista.setFrameShape(QFrame.NoFrame)
        self.scroll_lista.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.scroll_lista.viewport().setAutoFillBackground(False)
        self.interior_lista = QWidget()
        self.interior_lista.setObjectName("interior_lista")
        self.interior_lista.setStyleSheet("QWidget#interior_lista{background:transparent;}")
        self.lay_lista = QVBoxLayout(self.interior_lista)
        self.lay_lista.setContentsMargins(0, 0, 0, 0)
        self.lay_lista.setSpacing(4)
        cargando = QLabel("Cargando tus conversaciones…")
        cargando.setObjectName("ayuda")
        self.lay_lista.addWidget(cargando)
        self.lay_lista.addStretch(1)
        self._lista_cargada = False
        self.scroll_lista.setWidget(self.interior_lista)
        self.panel_sol = PanelSolicitudes(ctx, compacto=True)
        self.panel_ami = PanelAmigos(ctx, compacto=True)
        self.paneles = {"chats": self.scroll_lista, "solicitudes": self.panel_sol, "amigos": self.panel_ami}
        for w in self.paneles.values():
            izq.addWidget(w, 1)
        self.panel_sol.contador.connect(self._badge_solicitudes)
        self.panel_sol.cambio.connect(self.panel_ami.cargar)
        self.panel_sol.cambio.connect(self._cargar_lista)
        self.panel_ami.cambio.connect(self.panel_sol.cargar)
        self.panel_ami.cambio.connect(self._cargar_lista)
        self.panel_ami.escribir.connect(self._escribir_a)
        self.caja_izq = QWidget()
        self.caja_izq.setLayout(izq)
        self.caja_izq.setFixedWidth(self.ANCHO_LISTA)
        h.addWidget(self.caja_izq)

        # ---- la conversación
        self.panel = QFrame()
        self.panel.setObjectName("panel_chat")
        self.panel.setStyleSheet(f"QFrame#panel_chat{{background:{C['panel']};border:1px solid {C['borde']};"
                                 "border-radius:16px;}")
        vp = QVBoxLayout(self.panel)
        vp.setContentsMargins(16, 12, 16, 12)
        vp.setSpacing(8)
        cab2 = QHBoxLayout()
        cab2.setSpacing(8)
        self.bt_volver = QToolButton()
        self.bt_volver.setIcon(iconos.icono("atras", 18, C["texto"]))
        self.bt_volver.setToolTip("Volver a tus conversaciones")
        self.bt_volver.setCursor(Qt.PointingHandCursor)
        self.bt_volver.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                     "padding:6px;}")
        self.bt_volver.clicked.connect(self._volver_a_lista)
        self.bt_volver.hide()
        cab2.addWidget(self.bt_volver)
        self.et_con = QLabel("Elige una conversación o empieza una nueva")
        self.et_con.setStyleSheet("font-size:18px;font-weight:800;background:transparent;")
        self.et_con.setMinimumWidth(60)
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
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.scroll.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setObjectName("interior_chat")
        self.interior.setStyleSheet("QWidget#interior_chat{background:transparent;}")
        self.lay = QVBoxLayout(self.interior)
        self.lay.setContentsMargins(0, 0, 6, 0)
        self.lay.setSpacing(6)
        self.lay.addStretch(1)
        self.scroll.setWidget(self.interior)
        vp.addWidget(self.scroll, 1)
        self.aviso_no_amigo = QLabel("Ya no son amigos, así que no pueden escribirse. "
                                     "Si quieres volver a hablar, envíale una solicitud desde su perfil.")
        self.aviso_no_amigo.setWordWrap(True)
        self.aviso_no_amigo.setStyleSheet(f"background:{C['superficie2']};color:{C['texto2']};"
                                          "border-radius:10px;padding:10px 12px;")
        self.aviso_no_amigo.hide()
        vp.addWidget(self.aviso_no_amigo)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.bt_emoji = QToolButton()
        self.bt_emoji.setText("😊")
        self.bt_emoji.setFont(_fuente_emoji(15))
        self.bt_emoji.setToolTip("Emojis")
        self.bt_emoji.setCursor(Qt.PointingHandCursor)
        self.bt_emoji.setPopupMode(QToolButton.InstantPopup)
        self.bt_emoji.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    "padding:6px 8px;}QToolButton::menu-indicator{image:none;}")
        self.bt_emoji.setMenu(menu_emojis(self, lambda e: (self.campo.insert(e), self.campo.setFocus())))
        fila.addWidget(self.bt_emoji)
        self.bt_suena = QToolButton()
        self.bt_suena.setIcon(iconos.icono("musica", 18, C["acento"]))
        self.bt_suena.setToolTip("Enviar la canción que está sonando")
        self.bt_suena.setCursor(Qt.PointingHandCursor)
        self.bt_suena.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    f"padding:7px;}}QToolButton:hover{{background:{C['superficie3']};}}")
        self.bt_suena.clicked.connect(self._enviar_suena)
        fila.addWidget(self.bt_suena)
        self.bt_lista = QToolButton()
        self.bt_lista.setIcon(iconos.icono("lista", 18, C["acento"]))
        self.bt_lista.setText("")
        self.bt_lista.setToolTip("Enviar una lista")
        self.bt_lista.setCursor(Qt.PointingHandCursor)
        self.bt_lista.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    f"padding:7px;}}QToolButton:hover{{background:{C['superficie3']};}}")
        self.bt_lista.clicked.connect(self._elegir_lista)
        fila.addWidget(self.bt_lista)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Escribe un mensaje")
        self.campo.setMaxLength(2000)
        self.campo.setMinimumWidth(80)
        self.campo.setFont(_fuente_emoji(10.5))
        self.campo.returnPressed.connect(self._enviar)
        self.campo.textChanged.connect(self._al_escribir)
        fila.addWidget(self.campo, 1)
        self.bt_enviar = QPushButton("Enviar")
        self.bt_enviar.setObjectName("principal")
        self.bt_enviar.setCursor(Qt.PointingHandCursor)
        self.bt_enviar.clicked.connect(lambda: self._enviar())
        fila.addWidget(self.bt_enviar)
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
        # «Enviar lo que suena» dice qué canción va a mandar
        r = getattr(ctx, "reproductor", None)
        if r is not None and hasattr(r, "pista_cambio"):
            r.pista_cambio.connect(self._al_cambiar_pista)
        self._al_cambiar_pista(getattr(r, "actual", None))
        self._pestana("chats")
        pend = getattr(ctx, "chat_pendiente", None)
        if pend and self.chat is not None:
            ctx.chat_pendiente = None
            self._abrir_con(pend)

    # ------------------------------------------------------------ pestañas y amigos
    def _pestana(self, clave):
        for k, w in self.paneles.items():
            w.setVisible(k == clave)
            self.tabs[k].setChecked(k == clave)

    def _badge_solicitudes(self, n):
        self.tabs["solicitudes"].setText(f"Solicitudes ({n})" if n else "Solicitudes")

    def _abrir_con(self, p):
        """Abre (o crea) la conversación con un amigo que se eligió fuera de la lista de chats."""
        if self.chat is None:
            return
        nombre = p.get("visible") or p.get("nombre") or p.get("usuario") or "?"

        def listo(cid):
            self._pestana("chats")
            self._abrir({"id": cid, "otro": p["id"], "usuario": p.get("usuario") or "",
                         "nombre": p.get("nombre") or "", "visible": nombre, "es_amigo": True})
        en_segundo_plano(self.chat.abrir, p["id"], ok=listo,
                         error=lambda e: self.ctx.aviso.emit(_motivo(e, "abrir la conversación")),
                         dueno=self, urgente=True)

    def _escribir_a(self, p):
        p = dict(p)
        p["visible"] = S.nombre_visible(p)
        self._abrir_con(p)

    # ------------------------------------------------------------ estado
    def _activar(self, si):
        for w in (self.bt_mezcla, self.bt_emoji, self.bt_suena, self.bt_lista, self.campo):
            w.setEnabled(si)
        self.bt_enviar.setEnabled(si and bool(self.campo.text().strip()))

    def _al_escribir(self, texto):
        self.bt_enviar.setEnabled(self.actual is not None and self.campo.isEnabled() and bool(texto.strip()))

    def _al_cambiar_pista(self, p):
        try:
            if p and p.get("video_id"):
                self.bt_suena.setToolTip(f"Enviar «{p.get('titulo') or 'lo que suena'}»")
            elif p:
                self.bt_suena.setToolTip("Lo que suena es un archivo de tu disco: solo se pueden enviar "
                                         "canciones de YouTube Music")
            else:
                self.bt_suena.setToolTip("Enviar la canción que está sonando (ahora no suena nada)")
        except RuntimeError:
            pass

    def _sin_red(self):
        _borrar_layout(self.lay_lista)
        et = QLabel("Los mensajes necesitan una cuenta de Caudal con internet. "
                    "Vuelve a abrir Caudal con conexión.")
        et.setWordWrap(True)
        et.setObjectName("secundario")
        self.lay_lista.addWidget(et)
        self.lay_lista.addStretch(1)

    # ------------------------------------------------------------ espacio
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._acomodar()

    def showEvent(self, e):
        super().showEvent(e)
        self._acomodar()

    def _acomodar(self):
        """Con poco sitio (panel de la derecha abierto, ventana pequeña) la lista
        se estrecha y, si aun así no cabe, se alterna lista / conversación."""
        if getattr(self, "_acomodando", False):
            return
        self._acomodando = True
        try:
            ancho = self.width() - 48
            estrecho = ancho < self.ESTRECHO
            if estrecho:
                # a lo ancho, sin tamaño fijo (un tamaño fijo aquí realimenta el redimensionado)
                if self.caja_izq.maximumWidth() != 16777215:
                    self.caja_izq.setMinimumWidth(0)
                    self.caja_izq.setMaximumWidth(16777215)
                lista, chat = self.actual is None, self.actual is not None
            else:
                fijo = max(230, min(self.ANCHO_LISTA, int(ancho * 0.34)))
                if self.caja_izq.maximumWidth() != fijo or self.caja_izq.minimumWidth() != fijo:
                    self.caja_izq.setFixedWidth(fijo)
                lista = chat = True
            if self.caja_izq.isVisibleTo(self) != lista:
                self.caja_izq.setVisible(lista)
            if self.panel.isVisibleTo(self) != chat:
                self.panel.setVisible(chat)
            self.bt_volver.setVisible(estrecho and self.actual is not None)
        finally:
            self._acomodando = False

    def _volver_a_lista(self):
        self.actual = None
        self.reloj_chat.stop()
        self._activar(False)
        self.et_con.setText("Elige una conversación o empieza una nueva")
        self.campo.setPlaceholderText("Escribe un mensaje")
        self.aviso_no_amigo.hide()
        self.cargando = None
        _borrar_layout(self.lay)
        self.lay.addStretch(1)
        self._acomodar()
        self._cargar_lista()

    # ------------------------------------------------------------ lista
    def _cargar_lista(self):
        if self.chat is None or (not self.isVisible() and self._lista_cargada):
            return
        en_segundo_plano(self.chat.panorama, ok=self._pintar_lista, error=self._lista_fallo,
                         dueno=self, urgente=True)

    def _lista_fallo(self, e):
        if not self._lista_cargada:
            _borrar_layout(self.lay_lista)
            et = QLabel(_motivo(e, "cargar tus conversaciones"))
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
            self.lay_lista.addStretch(1)

    def _pintar_lista(self, datos):
        chats, solicitudes = datos
        self._badge_solicitudes(solicitudes)
        self._lista_cargada = True
        barra = self.scroll_lista.verticalScrollBar().value()
        _borrar_layout(self.lay_lista)
        if not chats:
            et = QLabel("Aún no tienes conversaciones.\n\nSolo puedes escribir a tus amigos: pulsa «Nuevo», "
                        "escribe el usuario de Caudal de alguien y envíale una solicitud. Cuando la acepte "
                        "podrán mandarse mensajes y canciones, y crear una mezcla con lo que escuchan los dos.")
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
        for c in chats:
            self.lay_lista.addWidget(self._fila(c))
        self.lay_lista.addStretch(1)
        QTimer.singleShot(0, lambda: self.scroll_lista.verticalScrollBar().setValue(barra))

    def _fila(self, c):
        b = QPushButton()
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(64)
        b.setFocusPolicy(Qt.NoFocus)
        activo = self.actual and self.actual["id"] == c["id"]
        b.setStyleSheet(f"QPushButton{{text-align:left;border:none;border-radius:12px;padding:0;"
                        f"background:{C['superficie2'] if activo else 'transparent'};}}"
                        f"QPushButton:hover{{background:{C['superficie3'] if activo else C['superficie']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 6, 10, 6)
        h.addWidget(Avatar(40, c["visible"] or "?", C["acento"], c.get("foto_url"), marco=c.get("marco")))
        col = QVBoxLayout()
        col.setSpacing(0)
        n = QLabel(c["visible"])
        sin = int(c.get("sin_leer") or 0)
        n.setStyleSheet(f"font-weight:{900 if sin else 700};background:transparent;")
        col.addWidget(n)
        prev = QLabel(CH.vista_previa(c, self.chat.yo))
        prev.setFont(_fuente_emoji(9))
        prev.setStyleSheet(f"color:{C['texto'] if sin else C['texto2']};background:transparent;")
        prev.setMinimumWidth(10)
        col.addWidget(prev)
        h.addLayout(col, 1)
        der = QVBoxLayout()
        hora = QLabel(_hora(c["fecha"]))
        hora.setStyleSheet(f"color:{C['texto3']};background:transparent;font-size:11px;")
        der.addWidget(hora, 0, Qt.AlignRight)
        if sin:
            g = QLabel(str(sin))
            g.setAlignment(Qt.AlignCenter)
            g.setStyleSheet(f"background:{C['acento']};color:{C['acento_texto']};border-radius:9px;"
                            "font-size:11px;font-weight:900;padding:1px 7px;")
            der.addWidget(g, 0, Qt.AlignRight)
        h.addLayout(der)
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False, c=c: self._abrir(c))
        return b

    # ------------------------------------------------------------ conversacion
    def _abrir(self, c):
        self.actual = c
        self.mensajes = []
        self.pendientes = {}
        usuario = c.get("usuario") or ""
        self.et_con.setText(f"{_html(c['visible'])}  <span style='color:{C['texto3']};font-size:13px;"
                            f"font-weight:600'>@{_html(usuario)}</span>" if usuario else _html(c["visible"]))
        self.campo.setPlaceholderText(f"Escríbele a {c['visible']}")
        amigo = c.get("es_amigo", True)
        self._activar(bool(amigo))
        self.aviso_no_amigo.setVisible(not amigo)
        if not amigo:
            self.campo.setPlaceholderText("Ya no son amigos")
        _borrar_layout(self.lay)
        self.cargando = QLabel("Cargando la conversación…")
        self.cargando.setAlignment(Qt.AlignCenter)
        self.cargando.setWordWrap(True)
        self.cargando.setObjectName("ayuda")
        self.lay.addWidget(self.cargando)
        self.lay.addStretch(1)
        self._enviando = 0
        self._acomodar()
        self.campo.setFocus()
        en_segundo_plano(self.chat.mensajes, c["id"], ok=lambda l, cid=c["id"]: self._llegan(cid, l, True),
                         error=lambda e, cid=c["id"]: self._carga_fallo(cid, e),
                         dueno=self, urgente=True)
        self.reloj_chat.start()
        self._cargar_lista()

    # un solo aviso arriba del chat («Cargando…», el saludo o el error): se
    # muestra u oculta, nunca se quita del layout
    def _quitar_cargando(self):
        if self.cargando is not None:
            try:
                self.cargando.hide()
            except RuntimeError:
                self.cargando = None

    def _aviso_chat(self, texto):
        if self.cargando is not None:
            try:
                self.cargando.setText(texto)
                self.cargando.show()
            except RuntimeError:
                self.cargando = None

    def _carga_fallo(self, cid, e):
        if not self.actual or self.actual["id"] != cid:
            return
        if not self.mensajes and not self.pendientes:
            self._aviso_chat(_motivo(e, "cargar la conversación") + "\nPuedes escribir igual.")

    def _llegan(self, cid, lista, todo=False):
        if not self.actual or self.actual["id"] != cid:
            return
        ids = {m["id"] for m in self.mensajes}
        nuevos = [m for m in lista if m["id"] not in ids]
        for m in nuevos:
            self._burbuja(m)
        self.mensajes += nuevos
        self.mensajes.sort(key=lambda m: m["id"])
        if self.mensajes or self.pendientes:
            self._quitar_cargando()
        elif todo:
            self._aviso_chat(f"Aquí empieza tu conversación con {c_visible(self.actual)}.\n"
                             "Escribe algo o mándale lo que estás escuchando 🎵")
        if nuevos or todo:
            en_segundo_plano(self.chat.marcar_leido, cid, dueno=self, urgente=True)
            self._al_final()

    def _al_final(self):
        barra = self.scroll.verticalScrollBar()
        QTimer.singleShot(40, lambda: barra.setValue(barra.maximum()))

    def _nuevos(self):
        # mientras un envío va en camino no se pregunta (evita burbujas dobles)
        if not self.actual or not self.isVisible() or self._enviando:
            return
        desde = self.mensajes[-1]["id"] if self.mensajes else 0
        cid = self.actual["id"]
        en_segundo_plano(self.chat.mensajes, cid, desde, ok=lambda l: self._llegan(cid, l),
                         error=lambda _e: None, dueno=self, urgente=True)

    def _burbuja(self, m, pendiente=False):
        """Pinta un mensaje. Devuelve (burbuja, etiqueta de la hora)."""
        mio = pendiente or str(m.get("autor")) == str(self.chat.yo)
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
        tarjeta = LC.tarjeta_limpia(m.get("lista")) if not p else None
        if tarjeta:
            v.addLayout(self._tarjeta_lista(tarjeta, mio, color))
        elif p:
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
            play.setToolTip("Escuchar")
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
        hora = QLabel("Enviando…" if pendiente else _hora(m["fecha"]))
        hora.setAlignment(Qt.AlignRight)
        hora.setWordWrap(True)
        hora.setStyleSheet(f"color:{color};font-size:10px;background:transparent;")
        efecto = QGraphicsOpacityEffect(hora)
        efecto.setOpacity(0.7)
        hora.setGraphicsEffect(efecto)
        v.addWidget(hora)
        fila_ext = QHBoxLayout()
        if mio:
            fila_ext.addStretch(1)
        fila_ext.addWidget(caja)
        if not mio:
            fila_ext.addStretch(1)
        self.lay.insertLayout(self.lay.count() - 1, fila_ext)
        return caja, hora

    def _tarjeta_lista(self, t, mio, color):
        """La tarjeta de una lista compartida: nombre, canciones, permiso y «Unirme» / «Abrir»."""
        fila = QHBoxLayout()
        port = Portada(52, radio=6)
        port.set_url(t.get("portada") or "")
        fila.addWidget(port)
        n = t["canciones"]
        txt = QLabel(f"<b>{_html(t['nombre'])}</b><br><span style='font-size:11px'>"
                     f"Lista · {n} {'canción' if n == 1 else 'canciones'} · {LC.etiqueta_rol(t['rol'])}</span>")
        txt.setWordWrap(True)
        txt.setStyleSheet(f"color:{color};background:transparent;")
        fila.addWidget(txt, 1)
        conocida = LC.lista_de_codigo(self.ctx.coleccion, t["codigo"])
        boton = QPushButton("Abrir" if conocida else "Unirme")
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFixedHeight(32)
        boton.setStyleSheet(f"QPushButton{{background:{C['acento_texto'] if mio else C['acento']};"
                            f"color:{C['acento'] if mio else C['acento_texto']};border:none;border-radius:16px;"
                            "padding:0 16px;font-weight:800;}")
        boton.clicked.connect(lambda _=False, t=t, b=boton: self._abrir_tarjeta(t, b))
        fila.addWidget(boton)
        return fila

    def _abrir_tarjeta(self, t, boton):
        from ..contexto import nube_de
        from ..dialogos_listas import abrir_lista_unida
        col = self.ctx.coleccion
        conocida = LC.lista_de_codigo(col, t["codigo"])
        if conocida and conocida["tipo"] == "mia":
            self.ctx.navegar({"pagina": "mi_lista", "id": conocida["id"]})
            return
        if conocida:
            self.ctx.navegar({"pagina": "lista_compartida", "id": conocida["id"],
                              "el": {"tipo": "lista_compartida", "id": conocida["id"], "titulo": t["nombre"],
                                     "rol": t["rol"], "dueno": {}}})
            return
        nube = nube_de(self.ctx)
        if nube is None:
            self.ctx.aviso.emit("Unirte a una lista necesita internet.")
            return
        boton.setEnabled(False)
        boton.setText("Uniéndote…")

        def listo(r):
            LC.recordar_union(col, t["codigo"], r["lista_id"])
            try:
                boton.setEnabled(True)
                boton.setText("Abrir")
            except RuntimeError:
                pass
            abrir_lista_unida(self.ctx, dict(r, codigo=t["codigo"]))

        def fallo(e):
            from ..contexto import explicar_error
            try:
                boton.setEnabled(True)
                boton.setText("Unirme")
            except RuntimeError:
                pass
            self.ctx.aviso.emit(explicar_error(e, "unirte a la lista"))
        en_segundo_plano(nube.unirse, t["codigo"], ok=listo, error=fallo, dueno=self, urgente=True)

    def _elegir_lista(self):
        """«Enviar una lista» desde dentro del chat."""
        if not self.actual or self.chat is None:
            return
        from ..dialogos_listas import DialogoEnviarLista
        d = DialogoEnviarLista(self.ctx, self.actual.get("visible") or "", self)
        if d.exec() == QDialog.Accepted and d.tarjeta:
            self.ctx.aviso.emit(d.frase)
            self._enviar(lista=d.tarjeta)

    def _enviar(self, pista=None, lista=None):
        if not self.actual or self.chat is None:
            return
        texto = "" if (pista or lista) else self.campo.text().strip()
        if not texto and pista is None and lista is None:
            return
        if pista is None and lista is None:
            self.campo.clear()
        self.campo.setFocus()
        self._quitar_cargando()
        cid = self.actual["id"]
        # se ve al momento, con «Enviando…», y se confirma (o se ofrece reintentar)
        self._siguiente_local += 1
        clave = self._siguiente_local
        caja, hora = self._burbuja({"texto": texto, "pista": pista, "lista": lista}, pendiente=True)
        self.pendientes[clave] = (caja, hora, texto, pista, lista)
        self._al_final()
        self._mandar(cid, clave)

    def _mandar(self, cid, clave):
        _caja, hora, texto, pista, lista = self.pendientes[clave]
        hora.setText("Enviando…")
        hora.setCursor(Qt.ArrowCursor)
        hora.mousePressEvent = lambda _ev: None
        self._enviando += 1

        def ok(m):
            self._enviando = max(0, self._enviando - 1)
            self.pendientes.pop(clave, None)
            try:
                hora.setText(_hora(m["fecha"]))
            except RuntimeError:
                return
            if self.actual and self.actual["id"] == cid and m["id"] not in {x["id"] for x in self.mensajes}:
                self.mensajes.append(m)
                self.mensajes.sort(key=lambda x: x["id"])
            self._cargar_lista()

        def fallo(e):
            self._enviando = max(0, self._enviando - 1)
            try:
                hora.setText(f"⚠ {_motivo(e)}  ·  Haz clic aquí para reintentar")
                hora.setCursor(Qt.PointingHandCursor)
                hora.mousePressEvent = lambda _ev: (clave in self.pendientes) and self._mandar(cid, clave)
            except RuntimeError:
                pass

        en_segundo_plano(self.chat.enviar, cid, texto, pista, lista, ok=ok, error=fallo, dueno=self, urgente=True)

    def _enviar_suena(self):
        r = getattr(self.ctx, "reproductor", None)
        p = getattr(r, "actual", None)
        if not p:
            self.ctx.aviso.emit("Ahora no suena nada. Pon una canción y vuelve a pulsar 🎵")
            return
        if not p.get("video_id"):
            self.ctx.aviso.emit("Esa canción es un archivo de tu disco: solo se pueden enviar "
                                "canciones de YouTube Music.")
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
                         error=lambda e: self.ctx.aviso.emit(_motivo(e, "crear la mezcla")),
                         dueno=self, urgente=True)


def c_visible(c):
    return _html((c or {}).get("visible") or "esa persona")
