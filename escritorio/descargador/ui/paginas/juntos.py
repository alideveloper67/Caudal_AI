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
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from ... import juntos as J
from ..estilos import C


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
        self.g.reaccion.connect(lambda e, n, mio: flotar_emoji(self, e, n, mio))
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
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        caja = self._caja(v)
        et = QLabel("Código de la sala")
        et.setObjectName("ayuda")
        caja.addWidget(et)
        fila = QHBoxLayout()
        self.et_codigo = QLabel("")
        self.et_codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.et_codigo.setStyleSheet(f"font-size:34px;font-weight:700;letter-spacing:6px;"
                                     f"color:{C['acento']};")
        fila.addWidget(self.et_codigo)
        fila.addStretch(1)
        for texto, f in (("Copiar código", self._copiar_codigo), ("Copiar enlace", self._copiar_enlace)):
            b = QPushButton(texto)
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(f)
            fila.addWidget(b)
        caja.addLayout(fila)
        self.et_estado = QLabel("")
        self.et_estado.setObjectName("secundario")
        self.et_estado.setWordWrap(True)
        caja.addWidget(self.et_estado)

        self.et_suena = QLabel("")
        self.et_suena.setWordWrap(True)
        self.et_suena.setStyleSheet("font-size:15px;")
        v.addWidget(self.et_suena)
        self.et_aviso = QLabel("")
        self.et_aviso.setWordWrap(True)
        self.et_aviso.setStyleSheet(f"color:{C['aviso']};")
        self.et_aviso.hide()
        v.addWidget(self.et_aviso)

        t = QLabel("En la sala")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        self.lista = QListWidget()
        self.lista.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista.customContextMenuRequested.connect(self._menu_miembro)
        self.lista.setStyleSheet(f"QListWidget{{background:{C['superficie']};border:none;"
                                 f"border-radius:10px;padding:6px;}}"
                                 f"QListWidget::item{{padding:7px 8px;border-radius:6px;}}")
        v.addWidget(self.lista, 1)
        self.et_ceder = QLabel("Clic derecho en alguien para pasarle el mando.")
        self.et_ceder.setObjectName("ayuda")
        v.addWidget(self.et_ceder)

        emojis = QHBoxLayout()
        emojis.setSpacing(6)
        for e in J.EMOJIS:
            b = QPushButton(e)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(44, 40)
            b.setToolTip("Mandar a todos")
            b.setStyleSheet(f"QPushButton{{font-size:20px;background:{C['superficie2']};"
                            f"border:none;border-radius:10px;}}"
                            f"QPushButton:hover{{background:{C['superficie3']};}}")
            b.clicked.connect(lambda _=False, e=e: self._reaccionar(e))
            emojis.addWidget(b)
        emojis.addStretch(1)
        salir = QPushButton("Salir de la sala")
        salir.setObjectName("peligro")
        salir.setCursor(Qt.PointingHandCursor)
        salir.clicked.connect(self.g.salir)
        emojis.addWidget(salir)
        v.addLayout(emojis)
        return w

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

    def _menu_miembro(self, pos):
        s = self.g.sala
        it = self.lista.itemAt(pos)
        if not s or it is None or not s.soy_anfitrion:
            return
        mid = it.data(Qt.UserRole)
        if mid == s.mi_id:
            return
        menu = QMenu(self)
        menu.addAction(f"Pasarle el mando a {it.data(Qt.UserRole + 1)}",
                       lambda: s.ceder_anfitrion(mid))
        menu.exec(self.lista.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------ pintar
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
        self.et_codigo.setText(s.codigo)
        anf = s.anfitrion
        if not s.conectado:
            estado = "Sin conexión con la sala: reconectando…"
        elif s.soy_anfitrion:
            estado = "Tú pones la música: los demás oyen lo mismo que tú."
        elif anf is not None:
            estado = f"Pone la música {anf.nombre}. Si tocas pausa o la barra, vuelves a su punto."
        else:
            estado = "Esperando a quien pone la música…"
        self.et_estado.setText(estado)
        p = s.pista_sala
        if p:
            artista = p.get("artista") or ""
            self.et_suena.setText(f"Suena: <b>{_html(p.get('titulo') or 'Sin título')}</b>"
                                  + (f" · {_html(artista)}" if artista else ""))
        else:
            self.et_suena.setText("Ahora no suena nada.")
        self.et_aviso.setText(s.aviso or "")
        self.et_aviso.setVisible(bool(s.aviso))
        self.et_ceder.setVisible(s.soy_anfitrion and len(s.miembros) > 1)
        self.lista.clear()
        for m in s.miembros:
            texto = m.nombre
            if m.id == s.mi_id:
                texto += "  (tú)"
            if m.usuario:
                texto += f"   @{m.usuario}"
            if m.id == s.anfitrion_id:
                texto = "🎧  " + texto + "  · pone la música"
            else:
                texto = "      " + texto
            it = QListWidgetItem(texto)
            it.setData(Qt.UserRole, m.id)
            it.setData(Qt.UserRole + 1, m.nombre)
            self.lista.addItem(it)


def _html(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ================================================================ ventana

class VentanaJuntos(QWidget):
    """La página en su propia ventana, al lado de la principal."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre, Qt.Window)
        self.setWindowTitle("Escuchar juntos · Caudal")
        self.resize(560, 640)
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
