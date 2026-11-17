# -*- coding: utf-8 -*-
"""«Escuchar juntos»: crear una sala o entrar con un código, ver quién está,
quién pone la música, y mandar reacciones que flotan por la pantalla.

La sala vive en el GestorJuntos (uno por aplicación): sigue sonando aunque se
cierre esta ventana, hasta que se pulsa «Salir de la sala».
"""

import getpass
import random

from PySide6.QtCore import (QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation,
                            Qt, QObject, Signal)
import time

from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QPushButton, QScrollArea,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget, QWidgetAction)

from ... import juntos as J
from .. import iconos
from ..componentes import Portada, _borrar_layout
from ..estilos import C, hoja

# Los que salen al tocar el botón de emojis del chat (el teclado de Windows
# también los tiene con Win + .).
EMOJIS_CHAT = ["😀", "😂", "🤣", "😊", "😍", "🥰", "😘", "😎", "🤩", "🥳", "😮", "😢", "😭", "😡",
               "🤔", "🙄", "😴", "🤯", "🙌", "👏", "👍", "👎", "🙏", "💪", "🔥", "❤️", "💔", "💯",
               "🎵", "🎶", "🎧", "🎤", "🎸", "🥁", "🎹", "🕺", "💃", "🎉", "✨", "⭐"]


def _nombre_por_defecto(ctx):
    cuenta = getattr(ctx, "cuenta", None) or {}
    nombre = cuenta.get("nombre") or cuenta.get("usuario")
    if not nombre:
        try:
            nombre = getpass.getuser()
        except Exception:  # noqa: BLE001
            nombre = ""
    return (nombre or "Alguien en Windows")[:40]


# ================================================================ gestor

class GestorJuntos(QObject):
    """La sala abierta en la app (una a la vez)."""
    cambio = Signal()                     # entró, salió, cambió la lista…
    reaccion = Signal(str, str, bool)     # emoji, nombre, de_mi
    chat = Signal(dict)                   # mensaje del chat de la sala
    error = Signal(str)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.sala_qt = None
        self.abriendo = False

    @property
    def sala(self):
        return self.sala_qt.sala if self.sala_qt and self.sala_qt.sala.abierta else None

    def _empezar(self, nombre, codigo=None):
        if self.sala_qt is not None:
            self.salir()
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        s = J.SalaQt(self.ctx.reproductor, (nombre or "").strip() or _nombre_por_defecto(self.ctx),
                     cuenta.get("usuario") or "", codigo=codigo, padre=self)
        s.abierta.connect(lambda err, s=s: self._abierta(s, err))
        s.cambio.connect(self.cambio.emit)
        s.reaccion.connect(self.reaccion.emit)
        s.chat.connect(self.chat.emit)
        self.sala_qt = s
        self.abriendo = True
        self.cambio.emit()
        s.abrir()

    def crear(self, nombre):
        self._empezar(nombre)

    def unirse(self, texto, nombre):
        codigo = J.codigo_de_texto(texto)
        if codigo is None:
            self.error.emit("Ese código no es válido: son 6 letras o números.")
            return
        self._empezar(nombre, codigo)

    def _abierta(self, s, error):
        if s is not self.sala_qt:
            return
        self.abriendo = False
        if error:
            self.sala_qt = None
            s.deleteLater()
            self.error.emit(error)
        else:
            self.ctx.aviso.emit("Estás en la sala " + s.sala.codigo)
        self.cambio.emit()

    def salir(self):
        s = self.sala_qt
        self.sala_qt = None
        self.abriendo = False
        if s is not None:
            s.salir()
            s.deleteLater()
        self.cambio.emit()


def gestor(ctx):
    g = getattr(ctx, "_gestor_juntos", None)
    if g is None:
        g = GestorJuntos(ctx, ctx)
        ctx._gestor_juntos = g
        g.reaccion.connect(lambda e, n, mio: _flotar_fuera(ctx, e, n, mio))
    return g


# ============================================================ reacciones

def flotar_emoji(lienzo, emoji, nombre="", de_mi=False):
    """Un emoji que sube desde abajo y se desvanece, encima de `lienzo`."""
    if lienzo is None or not lienzo.isVisible():
        return
    caja = QWidget(lienzo)
    caja.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    v = QVBoxLayout(caja)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    e = QLabel(emoji)
    f = QFont()
    f.setPointSize(30)
    e.setFont(f)
    e.setAlignment(Qt.AlignCenter)
    e.setStyleSheet("background:transparent;")
    v.addWidget(e)
    if nombre and not de_mi:
        n = QLabel(nombre[:18])
        n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet(f"background:transparent;color:{C['texto2']};font-size:11px;")
        v.addWidget(n)
    caja.adjustSize()
    w, h = lienzo.width(), lienzo.height()
    x = random.randint(int(w * 0.12), max(int(w * 0.12) + 1, int(w * 0.88) - caja.width()))
    y0 = h - caja.height() - 20
    caja.move(x, y0)
    caja.show()
    caja.raise_()
    efecto = QGraphicsOpacityEffect(caja)
    caja.setGraphicsEffect(efecto)
    grupo = QParallelAnimationGroup(caja)
    sube = QPropertyAnimation(caja, b"pos", grupo)
    sube.setDuration(2600)
    sube.setStartValue(QPoint(x, y0))
    sube.setEndValue(QPoint(x + random.randint(-40, 40), max(0, int(h * 0.25))))
    sube.setEasingCurve(QEasingCurve.OutCubic)
    apaga = QPropertyAnimation(efecto, b"opacity", grupo)
    apaga.setDuration(2600)
    apaga.setKeyValueAt(0, 0.0)
    apaga.setKeyValueAt(0.12, 1.0)
    apaga.setKeyValueAt(0.7, 1.0)
    apaga.setKeyValueAt(1, 0.0)
    grupo.addAnimation(sube)
    grupo.addAnimation(apaga)
    grupo.finished.connect(caja.deleteLater)
    grupo.start()


def _flotar_fuera(ctx, emoji, nombre, de_mi):
    """Si la ventana de la sala no está a la vista, flota sobre la principal."""
    v = getattr(ctx, "_ventana_juntos", None)
    if v is not None and v.isVisible() and not v.isMinimized():
        return
    flotar_emoji(getattr(ctx, "ventana", None), emoji, nombre, de_mi)


# ================================================================ pagina

class PaginaJuntos(QWidget):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.g = gestor(ctx)
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(14)
        titulo = QLabel("Escuchar juntos")
        titulo.setObjectName("titulo_pagina")
        raiz.addWidget(titulo)
        self.pilas = QStackedWidget()
        raiz.addWidget(self.pilas, 1)
        self.pilas.addWidget(self._hacer_entrada())
        self.pilas.addWidget(self._hacer_sala())

        self.g.cambio.connect(self._pintar)
        self.g.error.connect(self._mostrar_error)
        self.g.reaccion.connect(self._al_reaccionar)
        self._pintar()

    # ------------------------------------------------------------ entrada
    def _hacer_entrada(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        ayuda = QLabel("Oíd lo mismo a la vez, en la PC o en el teléfono: quien pone la música "
                       "manda, los demás lo siguen al segundo. Cada uno puede usar su cuenta.")
        ayuda.setWordWrap(True)
        ayuda.setObjectName("secundario")
        v.addWidget(ayuda)

        et = QLabel("Tu nombre en la sala")
        et.setObjectName("ayuda")
        v.addWidget(et)
        self.campo_nombre = QLineEdit(_nombre_por_defecto(self.ctx))
        self.campo_nombre.setMaxLength(40)
        v.addWidget(self.campo_nombre)

        caja1 = self._caja(v)
        t1 = QLabel("Crear una sala")
        t1.setObjectName("titulo_seccion")
        caja1.addWidget(t1)
        d1 = QLabel("Tú pones la música. Te damos un código para pasárselo a los demás.")
        d1.setWordWrap(True)
        d1.setObjectName("ayuda")
        caja1.addWidget(d1)
        self.bt_crear = QPushButton("Crear sala")
        self.bt_crear.setObjectName("principal")
        self.bt_crear.setCursor(Qt.PointingHandCursor)
        self.bt_crear.clicked.connect(lambda: self.g.crear(self.campo_nombre.text()))
        caja1.addWidget(self.bt_crear, 0, Qt.AlignLeft)

        caja2 = self._caja(v)
        t2 = QLabel("Entrar en una sala")
        t2.setObjectName("titulo_seccion")
        caja2.addWidget(t2)
        fila = QHBoxLayout()
        self.campo_codigo = QLineEdit()
        self.campo_codigo.setPlaceholderText("Código de 6 letras o el enlace")
        self.campo_codigo.returnPressed.connect(self._unirse)
        fila.addWidget(self.campo_codigo, 1)
        self.bt_unirse = QPushButton("Entrar")
        self.bt_unirse.setObjectName("contorno")
        self.bt_unirse.setCursor(Qt.PointingHandCursor)
        self.bt_unirse.clicked.connect(self._unirse)
        fila.addWidget(self.bt_unirse)
        caja2.addLayout(fila)

        self.et_error = QLabel("")
        self.et_error.setWordWrap(True)
        self.et_error.setStyleSheet(f"color:{C['error']};")
        self.et_error.hide()
        v.addWidget(self.et_error)
        self.et_abriendo = QLabel("Entrando en la sala…")
        self.et_abriendo.setObjectName("secundario")
        self.et_abriendo.hide()
        v.addWidget(self.et_abriendo)
        v.addStretch(1)
        return w

    def _caja(self, v):
        marco = QFrame()
        marco.setObjectName("caja")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(8)
        v.addWidget(marco)
        return lay

    def _unirse(self):
        self.g.unirse(self.campo_codigo.text(), self.campo_nombre.text())

    def _mostrar_error(self, texto):
        self.et_error.setText(texto)
        self.et_error.show()

    # ------------------------------------------------------------ sala
    def _hacer_sala(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)

        # ---- izquierda: lo que suena, quién está y las reacciones
        izq = QVBoxLayout()
        izq.setSpacing(12)
        h.addLayout(izq, 3)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_suena")
        tarjeta.setStyleSheet(
            "QFrame#tarjeta_suena{border-radius:18px;"
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1f2a4a,stop:1 {C['superficie']});}}")
        ht = QHBoxLayout(tarjeta)
        ht.setContentsMargins(18, 18, 18, 18)
        ht.setSpacing(16)
        self.portada = Portada(120, radio=12)
        ht.addWidget(self.portada)
        vt = QVBoxLayout()
        vt.setSpacing(4)
        self.et_suena_eti = QLabel("AHORA SUENA")
        self.et_suena_eti.setStyleSheet(f"color:{C['acento']};font-size:11px;font-weight:800;"
                                        "letter-spacing:1px;background:transparent;")
        vt.addWidget(self.et_suena_eti)
        self.et_titulo = QLabel("")
        self.et_titulo.setWordWrap(True)
        self.et_titulo.setStyleSheet("font-size:22px;font-weight:900;background:transparent;")
        vt.addWidget(self.et_titulo)
        self.et_artista = QLabel("")
        self.et_artista.setStyleSheet(f"color:{C['texto2']};font-size:14px;background:transparent;")
        vt.addWidget(self.et_artista)
        vt.addStretch(1)
        self.et_estado = QLabel("")
        self.et_estado.setWordWrap(True)
        self.et_estado.setStyleSheet(f"color:{C['texto2']};font-size:12.5px;background:transparent;")
        vt.addWidget(self.et_estado)
        ht.addLayout(vt, 1)
        izq.addWidget(tarjeta)

        # código de la sala, compacto
        caja = self._caja(izq)
        fila = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(0)
        et = QLabel("Código para invitar")
        et.setObjectName("ayuda")
        col.addWidget(et)
        self.et_codigo = QLabel("")
        self.et_codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.et_codigo.setStyleSheet(f"font-size:28px;font-weight:800;letter-spacing:5px;color:{C['acento']};")
        col.addWidget(self.et_codigo)
        fila.addLayout(col)
        fila.addStretch(1)
        for texto, f in (("Copiar código", self._copiar_codigo), ("Copiar enlace", self._copiar_enlace)):
            b = QPushButton(texto)
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(f)
            fila.addWidget(b)
        caja.addLayout(fila)

        self.et_aviso = QLabel("")
        self.et_aviso.setWordWrap(True)
        self.et_aviso.setStyleSheet(f"color:{C['aviso']};")
        self.et_aviso.hide()
        izq.addWidget(self.et_aviso)

        t = QLabel("En la sala")
        t.setObjectName("titulo_seccion")
        izq.addWidget(t)
        self.caja_miembros = QWidget()
        self.lay_miembros = QGridLayout(self.caja_miembros)
        self.lay_miembros.setContentsMargins(0, 0, 0, 0)
        self.lay_miembros.setHorizontalSpacing(10)
        self.lay_miembros.setVerticalSpacing(10)
        izq.addWidget(self.caja_miembros)
        self.et_ceder = QLabel("Clic derecho en alguien para pasarle el mando.")
        self.et_ceder.setObjectName("ayuda")
        izq.addWidget(self.et_ceder)
        izq.addStretch(1)

        emojis = QHBoxLayout()
        emojis.setSpacing(6)
        for e in J.EMOJIS:
            b = QPushButton(e)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(46, 42)
            b.setToolTip("Mandar a todos")
            b.setFont(_fuente_emoji(18))
            b.setStyleSheet(f"QPushButton{{background:{C['superficie2']};border:none;border-radius:12px;}}"
                            f"QPushButton:hover{{background:{C['superficie3']};}}")
            b.clicked.connect(lambda _=False, e=e: self._reaccionar(e))
            emojis.addWidget(b)
        emojis.addStretch(1)
        salir = QPushButton("Salir de la sala")
        salir.setObjectName("peligro")
        salir.setCursor(Qt.PointingHandCursor)
        salir.clicked.connect(self.g.salir)
        emojis.addWidget(salir)
        izq.addLayout(emojis)

        # ---- derecha: el chat de la sala
        panel = QFrame()
        panel.setObjectName("chat_sala")
        panel.setStyleSheet(f"QFrame#chat_sala{{background:{C['panel']};border:1px solid {C['borde']};"
                            "border-radius:16px;}")
        panel.setMinimumWidth(300)
        vp = QVBoxLayout(panel)
        vp.setContentsMargins(14, 12, 14, 12)
        vp.setSpacing(8)
        tc = QLabel("Chat de la sala")
        tc.setStyleSheet("font-size:16px;font-weight:800;background:transparent;")
        vp.addWidget(tc)
        self.scroll_chat = QScrollArea()
        self.scroll_chat.setWidgetResizable(True)
        self.scroll_chat.setFrameShape(QFrame.NoFrame)
        self.scroll_chat.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_chat.setStyleSheet("background:transparent;")
        self.interior_chat = QWidget()
        self.interior_chat.setStyleSheet("background:transparent;")
        self.lay_chat = QVBoxLayout(self.interior_chat)
        self.lay_chat.setContentsMargins(0, 0, 4, 0)
        self.lay_chat.setSpacing(6)
        self.lay_chat.addStretch(1)
        self.scroll_chat.setWidget(self.interior_chat)
        vp.addWidget(self.scroll_chat, 1)
        self.et_chat_vacio = QLabel("Aún no hay mensajes. ¡Saluda!")
        self.et_chat_vacio.setObjectName("ayuda")
        self.et_chat_vacio.setAlignment(Qt.AlignCenter)
        self.lay_chat.insertWidget(0, self.et_chat_vacio)

        entrada = QHBoxLayout()
        entrada.setSpacing(6)
        self.bt_emoji = QToolButton()
        self.bt_emoji.setText("😊")
        self.bt_emoji.setFont(_fuente_emoji(15))
        self.bt_emoji.setToolTip("Emojis")
        self.bt_emoji.setCursor(Qt.PointingHandCursor)
        self.bt_emoji.setPopupMode(QToolButton.InstantPopup)
        self.bt_emoji.setStyleSheet(f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;"
                                    "padding:6px 8px;}QToolButton::menu-indicator{image:none;}")
        self.bt_emoji.setMenu(menu_emojis(self, lambda e: self._poner_emoji(e)))
        entrada.addWidget(self.bt_emoji)
        self.campo_chat = QLineEdit()
        self.campo_chat.setPlaceholderText("Escribe a la sala…")
        self.campo_chat.setMaxLength(J.LARGO_CHAT)
        self.campo_chat.setFont(_fuente_emoji(10.5))
        self.campo_chat.returnPressed.connect(self._enviar_chat)
        entrada.addWidget(self.campo_chat, 1)
        enviar = QPushButton("Enviar")
        enviar.setObjectName("principal")
        enviar.setCursor(Qt.PointingHandCursor)
        enviar.clicked.connect(self._enviar_chat)
        entrada.addWidget(enviar)
        vp.addLayout(entrada)
        h.addWidget(panel, 2)

        self.g.chat.connect(self._llega_chat)
        self._chat_de = None
        return w

    # ------------------------------------------------------------ chat
    def _poner_emoji(self, e):
        self.campo_chat.insert(e)
        self.campo_chat.setFocus()

    def _enviar_chat(self):
        s = self.g.sala
        if s and s.enviar_chat(self.campo_chat.text()):
            self.campo_chat.clear()

    def _llega_chat(self, m):
        s = self.g.sala
        mio = bool(s) and m.get("de") == s.mi_id
        self.et_chat_vacio.hide()
        burbuja = QLabel()
        burbuja.setWordWrap(True)
        burbuja.setTextFormat(Qt.RichText)
        burbuja.setTextInteractionFlags(Qt.TextSelectableByMouse)
        burbuja.setFont(_fuente_emoji(10.5))
        hora = time.strftime("%H:%M", time.localtime((m.get("t") or 0) / 1000))
        quien = "" if mio else f"<b style='color:{C['acento']}'>{_html(m.get('nombre'))}</b><br>"
        burbuja.setText(f"{quien}{_html(m.get('texto'))}"
                        f"<span style='color:{C['acento_texto'] if mio else C['texto3']};font-size:10px'>  {hora}</span>")
        burbuja.setStyleSheet(
            f"background:{C['acento'] if mio else C['superficie2']};color:{C['acento_texto'] if mio else C['texto']};"
            "border-radius:12px;padding:7px 10px;")
        burbuja.setMaximumWidth(260)
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        if mio:
            fila.addStretch(1)
        fila.addWidget(burbuja)
        if not mio:
            fila.addStretch(1)
        self.lay_chat.insertLayout(self.lay_chat.count() - 1, fila)
        barra = self.scroll_chat.verticalScrollBar()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(30, lambda: barra.setValue(barra.maximum()))

    def _vaciar_chat(self):
        while self.lay_chat.count() > 2:
            it = self.lay_chat.takeAt(1)
            if it.layout():
                _borrar_layout(it.layout())
            elif it.widget():
                it.widget().deleteLater()
        self.et_chat_vacio.show()

    def _reaccionar(self, emoji):
        s = self.g.sala
        if s:
            s.reaccionar(emoji)

    def _copiar_codigo(self):
        s = self.g.sala
        if s:
            QGuiApplication.clipboard().setText(s.codigo)
            self.ctx.aviso.emit("Código copiado")

    def _copiar_enlace(self):
        s = self.g.sala
        if s:
            QGuiApplication.clipboard().setText(s.enlace)
            self.ctx.aviso.emit("Enlace copiado: ábrelo en el teléfono con Caudal")

    def _menu_miembro(self, caja, pos, mid, nombre):
        s = self.g.sala
        if not s or not s.soy_anfitrion or mid == s.mi_id:
            return
        menu = QMenu(self)
        menu.addAction(f"Pasarle el mando a {nombre}", lambda: s.ceder_anfitrion(mid))
        menu.exec(caja.mapToGlobal(pos))

    # ------------------------------------------------------------ pintar
    def _al_reaccionar(self, e, n, mio):
        flotar_emoji(self, e, n, mio)

    def _pintar(self):
        s = self.g.sala
        if s is None:
            self.pilas.setCurrentIndex(0)
            ocupado = self.g.abriendo
            self.et_abriendo.setVisible(ocupado)
            self.bt_crear.setEnabled(not ocupado)
            self.bt_unirse.setEnabled(not ocupado)
            if ocupado:
                self.et_error.hide()
            return
        self.pilas.setCurrentIndex(1)
        if self._chat_de is not s:
            # otra sala: el chat empieza de cero (con lo que ya hubiera en esta)
            self._chat_de = s
            self._vaciar_chat()
            for m in list(s.chat):
                self._llega_chat(m)
        self.et_codigo.setText(s.codigo)
        anf = s.anfitrion
        if not s.conectado:
            estado = "Sin conexión con la sala: reconectando…"
        elif s.soy_anfitrion:
            estado = "🎧 Tú pones la música: los demás oyen lo mismo que tú."
        elif anf is not None:
            estado = f"🎧 Pone la música {anf.nombre}. Si tocas pausa o la barra, vuelves a su punto."
        else:
            estado = "Esperando a quien pone la música…"
        self.et_estado.setText(estado)
        p = s.pista_sala
        if p:
            self.et_suena_eti.setText("AHORA SUENA")
            self.et_titulo.setText(p.get("titulo") or "Sin título")
            self.et_artista.setText(p.get("artista") or "")
            self.portada.set_url(p.get("miniatura") or "")
        else:
            self.et_suena_eti.setText("EN SILENCIO")
            self.et_titulo.setText("Ahora no suena nada")
            self.et_artista.setText("Quien pone la música elige qué suena")
            self.portada.set_url("")
        self.et_aviso.setText(s.aviso or "")
        self.et_aviso.setVisible(bool(s.aviso))
        self.et_ceder.setVisible(s.soy_anfitrion and len(s.miembros) > 1)
        _borrar_layout(self.lay_miembros)
        for i, m in enumerate(s.miembros):
            self.lay_miembros.addWidget(self._miembro(s, m), i // 3, i % 3)

    def _miembro(self, s, m):
        caja = QFrame()
        caja.setObjectName("miembro")
        es_dj = m.id == s.anfitrion_id
        caja.setStyleSheet(f"QFrame#miembro{{background:{C['superficie']};border-radius:14px;"
                           f"border:1px solid {C['acento'] if es_dj else C['borde']};}}")
        caja.setContextMenuPolicy(Qt.CustomContextMenu)
        caja.customContextMenuRequested.connect(
            lambda pos, c=caja, mid=m.id, n=m.nombre: self._menu_miembro(c, pos, mid, n))
        h = QHBoxLayout(caja)
        h.setContentsMargins(10, 8, 12, 8)
        h.setSpacing(10)
        inicial = QLabel((m.nombre or "?")[:1].upper())
        inicial.setFixedSize(36, 36)
        inicial.setAlignment(Qt.AlignCenter)
        inicial.setStyleSheet(f"background:{C['acento'] if es_dj else C['superficie3']};"
                              f"color:{C['acento_texto'] if es_dj else C['texto']};border-radius:18px;"
                              "font-weight:900;font-size:15px;")
        h.addWidget(inicial)
        col = QVBoxLayout()
        col.setSpacing(0)
        nombre = QLabel(m.nombre + ("  (tú)" if m.id == s.mi_id else ""))
        nombre.setStyleSheet("font-weight:700;background:transparent;")
        col.addWidget(nombre)
        sub = QLabel("🎧 Pone la música" if es_dj else (f"@{m.usuario}" if m.usuario else "Escuchando"))
        sub.setFont(_fuente_emoji(8.5))
        sub.setStyleSheet(f"color:{C['acento'] if es_dj else C['texto3']};background:transparent;")
        col.addWidget(sub)
        h.addLayout(col, 1)
        return caja


def _html(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ================================================================ ventana

class VentanaJuntos(QWidget):
    """La página en su propia ventana, al lado de la principal."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre, Qt.Window)
        self.setWindowTitle("Escuchar juntos · Caudal")
        self.setWindowIcon(QIcon(iconos.icono_app(256)))
        # una ventana aparte no hereda el estilo de la principal: se le pone el suyo
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.resize(1000, 680)
        self.setMinimumSize(860, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.pagina = PaginaJuntos(ctx, self)
        lay.addWidget(self.pagina)


def abrir_ventana(ctx, padre=None):
    v = getattr(ctx, "_ventana_juntos", None)
    if v is None:
        v = VentanaJuntos(ctx, padre or getattr(ctx, "ventana", None))
        ctx._ventana_juntos = v
    v.show()
    v.raise_()
    v.activateWindow()
    return v


def _fuente_emoji(puntos):
    """Texto normal y emojis a color (Segoe UI Emoji en Windows)."""
    f = QFont()
    f.setFamilies(["Segoe UI", "Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"])
    f.setPointSizeF(puntos)
    return f


def menu_emojis(padre, al_elegir):
    """Un menú con una rejilla de emojis (para el chat)."""
    menu = QMenu(padre)
    rejilla = QWidget()
    lay = QGridLayout(rejilla)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(2)
    for i, e in enumerate(EMOJIS_CHAT):
        b = QToolButton()
        b.setText(e)
        b.setFont(_fuente_emoji(16))
        b.setAutoRaise(True)
        b.setFixedSize(38, 38)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, e=e: (al_elegir(e), menu.close()))
        lay.addWidget(b, i // 8, i % 8)
    accion = QWidgetAction(menu)
    accion.setDefaultWidget(rejilla)
    menu.addAction(accion)
    return menu
