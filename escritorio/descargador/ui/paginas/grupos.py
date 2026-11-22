# -*- coding: utf-8 -*-
"""Grupos para hablar (como los de la app del teléfono): tus grupos a la izquierda y la conversación a
la derecha, con texto, canciones y notas de voz. Explorar los abiertos, crear, entrar con código y, para
quien modera, fijar, ocultar, borrar, silenciar y sacar. No hay imágenes ni videos."""

import threading
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QRadioButton,
                               QScrollArea, QTextEdit, QToolButton, QVBoxLayout, QWidget)

from ... import grupos as G
from ... import notas_voz as NV
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Portada, _borrar_layout
from ..estilos import C
from .juntos import _fuente_emoji, menu_emojis
from .perfil_comun import Avatar


def grupos_de(ctx):
    cuenta = getattr(ctx, "cuenta", None) or {}
    s = cuenta.get("sesion")
    return G.Grupos(s) if s and getattr(s, "access", "") else None


def _html(t):
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def _hora(f):
    ahora = time.time()
    t = f.timestamp()
    if ahora - t < 20 * 3600 and time.localtime(t).tm_mday == time.localtime(ahora).tm_mday:
        return f.strftime("%H:%M")
    if ahora - t < 7 * 86400:
        return ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"][f.weekday()]
    return f"{f.day}/{f.month}"


def _motivo(e):
    from ...nube import ErrorNube, SinConexion
    if isinstance(e, SinConexion):
        return "No hay conexión. Revisa tu internet."
    if isinstance(e, ErrorNube):
        return str(e)
    return "Algo falló. Vuelve a intentarlo."


def duracion(seg):
    seg = int(seg or 0)
    return f"{seg // 60}:{seg % 60:02d}"


def _personas(n):
    n = int(n or 0)
    return f"{n} {'persona' if n == 1 else 'personas'}"


def _boton(texto, icono=None, principal=False, tip=""):
    b = QPushButton(("  " + texto) if icono else texto)
    if icono:
        b.setIcon(iconos.icono(icono, 16, C["acento_texto"] if principal else C["texto"]))
    b.setObjectName("principal" if principal else "contorno")
    b.setCursor(Qt.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    return b


# ================================================================ crear y entrar con código

class DialogoCrearGrupo(QDialog):
    def __init__(self, ctx, api, padre=None):
        super().__init__(padre)
        self.ctx, self.api, self.grupo = ctx, api, None
        self.setWindowTitle("Crear un grupo")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        t = QLabel("Crear un grupo")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        self.nombre = QLineEdit()
        self.nombre.setMaxLength(50)
        self.nombre.setPlaceholderText("Nombre (ej.: Reggaetón de Lima)")
        v.addWidget(self.nombre)
        self.desc = QTextEdit()
        self.desc.setPlaceholderText("De qué va (opcional)")
        self.desc.setFixedHeight(70)
        v.addWidget(self.desc)
        fila = QHBoxLayout()
        self.abierto = QRadioButton("Abierto: cualquiera lo encuentra y entra")
        self.privado = QRadioButton("Privado: solo con el código")
        self.abierto.setChecked(True)
        grupo = QButtonGroup(self)
        grupo.addButton(self.abierto)
        grupo.addButton(self.privado)
        col = QVBoxLayout()
        col.addWidget(self.abierto)
        col.addWidget(self.privado)
        fila.addLayout(col)
        v.addLayout(fila)
        nota = QLabel("En los grupos se comparten mensajes, canciones y notas de voz. "
                      "No se pueden enviar imágenes ni videos.")
        nota.setWordWrap(True)
        nota.setObjectName("ayuda")
        v.addWidget(nota)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color:#ff8a80;font-weight:700;")
        self.error.hide()
        v.addWidget(self.error)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = _boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        self.bt = _boton("Crear", principal=True)
        self.bt.clicked.connect(self._crear)
        botones.addWidget(cancelar)
        botones.addWidget(self.bt)
        v.addLayout(botones)

    def _crear(self):
        self.bt.setEnabled(False)
        self.bt.setText("Creando…")
        self.error.hide()

        def ok(g):
            self.grupo = g
            self.accept()

        def fallo(e):
            self.bt.setEnabled(True)
            self.bt.setText("Crear")
            self.error.setText(_motivo(e))
            self.error.show()

        en_segundo_plano(self.api.crear, self.nombre.text(), self.desc.toPlainText(), self.privado.isChecked(),
                         ok=ok, error=fallo, dueno=self, urgente=True)


def unirse_con_codigo(ctx, api, padre, al_listo):
    codigo, ok = QInputDialog.getText(padre, "Entrar con un código",
                                      "Pídele el código del grupo privado a alguien que ya esté dentro:")
    if not ok or not codigo.strip():
        return
    if len(G.limpiar_codigo(codigo)) < 6:
        ctx.avisar("Escribe el código completo (8 letras y números).")
        return
    en_segundo_plano(api.unirse_con_codigo, codigo, ok=al_listo, error=lambda e: ctx.avisar(_motivo(e)),
                     dueno=padre, urgente=True)


# ================================================================ explorar

class DialogoExplorar(QDialog):
    def __init__(self, ctx, api, padre=None):
        super().__init__(padre)
        self.ctx, self.api, self.elegido = ctx, api, None
        self.setWindowTitle("Explorar grupos")
        self.resize(520, 600)
        v = QVBoxLayout(self)
        self.busqueda = QLineEdit()
        self.busqueda.setPlaceholderText("Busca por artista, género, ciudad…")
        v.addWidget(self.busqueda)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.interior = QWidget()
        self.lay = QVBoxLayout(self.interior)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.interior)
        v.addWidget(self.scroll, 1)
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(350)
        self._espera.timeout.connect(self._buscar)
        self.busqueda.textChanged.connect(lambda _t: self._espera.start())
        self._buscar()

    def _buscar(self):
        texto = self.busqueda.text()
        en_segundo_plano(self.api.explorar, texto, ok=lambda l, t=texto: self._pintar(t, l),
                         error=lambda e: self._pintar(texto, None, _motivo(e)), dueno=self, urgente=True)

    def _pintar(self, texto, grupos, error=""):
        if texto != self.busqueda.text():
            return
        _borrar_layout(self.lay)
        if grupos is None or not grupos:
            et = QLabel(error or ("Todavía no hay grupos abiertos. ¡Crea el primero!" if not texto.strip()
                                  else f"No hay grupos con «{texto.strip()}». Puedes crearlo tú."))
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay.addWidget(et)
        for g in grupos or []:
            fila = QHBoxLayout()
            info = QLabel(f"<b>{_html(g.get('nombre'))}</b><br><span style='color:{C['texto2']}'>"
                          f"{_personas(g.get('miembros'))}"
                          f"{' · ' + _html(g.get('descripcion')) if g.get('descripcion') else ''}</span>")
            info.setWordWrap(True)
            fila.addWidget(info, 1)
            if g.get("rol"):
                et = QLabel("Ya estás")
                et.setObjectName("ayuda")
                fila.addWidget(et)
            else:
                b = _boton("Unirme", principal=True)
                b.clicked.connect(lambda _=False, g=g: self._unirse(g))
                fila.addWidget(b)
            caja = QWidget()
            caja.setLayout(fila)
            self.lay.addWidget(caja)
        self.lay.addStretch(1)

    def _unirse(self, g):
        def ok(r):
            self.elegido = r
            self.accept()
        en_segundo_plano(self.api.unirse, g["id"], ok=ok, error=lambda e: self.ctx.avisar(_motivo(e)),
                         dueno=self, urgente=True)


# ================================================================ la página

class PaginaGrupos(QWidget):
    ANCHO_LISTA = 320
    ESTRECHO = 700

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Grupos"
        self.api = grupos_de(ctx)
        self.actual = None
        self.mensajes = []
        self._enviando = 0
        self._grabacion = None
        self._t_grabar = 0.0
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(self)
        h.setContentsMargins(24, 20, 24, 20)
        h.setSpacing(16)
        h.setSizeConstraint(QHBoxLayout.SetNoConstraint)

        # ---- lista de grupos
        izq = QVBoxLayout()
        cab = QHBoxLayout()
        t = QLabel("Grupos")
        t.setObjectName("titulo_pagina")
        cab.addWidget(t)
        cab.addStretch(1)
        izq.addLayout(cab)
        bts = QHBoxLayout()
        bts.setSpacing(6)
        self.bt_crear = _boton("Crear", "mas", principal=True, tip="Crear un grupo abierto o privado")
        self.bt_crear.clicked.connect(self._crear)
        self.bt_explorar = _boton("Explorar", tip="Grupos abiertos para unirte")
        self.bt_explorar.clicked.connect(self._explorar)
        self.bt_codigo = _boton("Código", tip="Entrar a un grupo privado con su código")
        self.bt_codigo.clicked.connect(self._codigo)
        for b in (self.bt_crear, self.bt_explorar, self.bt_codigo):
            bts.addWidget(b)
        izq.addLayout(bts)
        self.scroll_lista = QScrollArea()
        self.scroll_lista.setWidgetResizable(True)
        self.scroll_lista.setFrameShape(QFrame.NoFrame)
        self.scroll_lista.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.interior_lista = QWidget()
        self.interior_lista.setObjectName("interior_lista")
        self.interior_lista.setStyleSheet("QWidget#interior_lista{background:transparent;}")
        self.lay_lista = QVBoxLayout(self.interior_lista)
        self.lay_lista.setContentsMargins(0, 0, 0, 0)
        self.lay_lista.setSpacing(4)
        et = QLabel("Cargando tus grupos…")
        et.setObjectName("ayuda")
        self.lay_lista.addWidget(et)
        self.lay_lista.addStretch(1)
        self.scroll_lista.setWidget(self.interior_lista)
        izq.addWidget(self.scroll_lista, 1)
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
        self.bt_volver = QToolButton()
        self.bt_volver.setIcon(iconos.icono("atras", 18, C["texto"]))
        self.bt_volver.setToolTip("Volver a tus grupos")
        self.bt_volver.setCursor(Qt.PointingHandCursor)
        self.bt_volver.clicked.connect(self._volver)
        self.bt_volver.hide()
        cab2.addWidget(self.bt_volver)
        self.et_grupo = QLabel("Elige un grupo, explora los abiertos o crea el tuyo")
        self.et_grupo.setStyleSheet("font-size:18px;font-weight:800;background:transparent;")
        self.et_grupo.setMinimumWidth(60)
        cab2.addWidget(self.et_grupo, 1)
        self.bt_info = _boton("Info", tip="La gente del grupo, el código y la moderación")
        self.bt_info.clicked.connect(self._info)
        self.bt_info.hide()
        cab2.addWidget(self.bt_info)
        vp.addLayout(cab2)
        self.fijado = QLabel("")
        self.fijado.setWordWrap(True)
        self.fijado.setStyleSheet(f"background:{C['superficie2']};border-radius:10px;padding:8px 12px;font-weight:700;")
        self.fijado.hide()
        vp.addWidget(self.fijado)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.interior = QWidget()
        self.interior.setObjectName("interior_chat")
        self.interior.setStyleSheet("QWidget#interior_chat{background:transparent;}")
        self.lay = QVBoxLayout(self.interior)
        self.lay.setContentsMargins(0, 0, 6, 0)
        self.lay.setSpacing(6)
        self.lay.addStretch(1)
        self.scroll.setWidget(self.interior)
        vp.addWidget(self.scroll, 1)
        self.aviso = QLabel("")
        self.aviso.setWordWrap(True)
        self.aviso.setObjectName("ayuda")
        self.aviso.hide()
        vp.addWidget(self.aviso)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        estilo_bt = (f"QToolButton{{background:{C['superficie2']};border:none;border-radius:10px;padding:7px;}}"
                     f"QToolButton:hover{{background:{C['superficie3']};}}QToolButton::menu-indicator{{image:none;}}")
        self.bt_emoji = QToolButton()
        self.bt_emoji.setText("😊")
        self.bt_emoji.setFont(_fuente_emoji(15))
        self.bt_emoji.setToolTip("Emojis")
        self.bt_emoji.setPopupMode(QToolButton.InstantPopup)
        self.bt_emoji.setStyleSheet(estilo_bt)
        self.bt_emoji.setMenu(menu_emojis(self, lambda e: (self.campo.insert(e), self.campo.setFocus())))
        fila.addWidget(self.bt_emoji)
        self.bt_suena = QToolButton()
        self.bt_suena.setIcon(iconos.icono("musica", 18, C["acento"]))
        self.bt_suena.setToolTip("Enviar la canción que está sonando")
        self.bt_suena.setCursor(Qt.PointingHandCursor)
        self.bt_suena.setStyleSheet(estilo_bt)
        self.bt_suena.clicked.connect(self._enviar_suena)
        fila.addWidget(self.bt_suena)
        self.bt_mic = QToolButton()
        self.bt_mic.setText("🎤")
        self.bt_mic.setFont(_fuente_emoji(14))
        self.bt_mic.setToolTip("Grabar una nota de voz (hasta 3 minutos)")
        self.bt_mic.setCursor(Qt.PointingHandCursor)
        self.bt_mic.setStyleSheet(estilo_bt)
        self.bt_mic.clicked.connect(self._alternar_grabar)
        fila.addWidget(self.bt_mic)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Escribe al grupo")
        self.campo.setMaxLength(2000)
        self.campo.setMinimumWidth(80)
        self.campo.setFont(_fuente_emoji(10.5))
        self.campo.returnPressed.connect(self._enviar)
        fila.addWidget(self.campo, 1)
        self.bt_cancelar_nota = _boton("Descartar")
        self.bt_cancelar_nota.clicked.connect(lambda: self._terminar_grabar(cancelar=True))
        self.bt_cancelar_nota.hide()
        fila.addWidget(self.bt_cancelar_nota)
        self.bt_enviar = _boton("Enviar", principal=True)
        self.bt_enviar.clicked.connect(self._enviar)
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
        self.reloj_grabar = QTimer(self)
        self.reloj_grabar.setInterval(500)
        self.reloj_grabar.timeout.connect(self._tic_grabar)
        if self.api is None:
            for b in (self.bt_crear, self.bt_explorar, self.bt_codigo):
                b.setEnabled(False)
            _borrar_layout(self.lay_lista)
            et = QLabel("Los grupos necesitan tu cuenta y conexión a internet. Entra con tu cuenta de Caudal.")
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
            self.lay_lista.addStretch(1)
        else:
            self._cargar_lista()
            self.reloj_lista.start()

    # ------------------------------------------------------------ disposición
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._acomodar()

    def _acomodar(self):
        estrecho = self.width() < self.ESTRECHO
        if estrecho:
            self.caja_izq.setMaximumWidth(16777215)
            self.caja_izq.setMinimumWidth(0)
            self.caja_izq.setVisible(self.actual is None)
            self.panel.setVisible(self.actual is not None)
        else:
            self.caja_izq.setFixedWidth(self.ANCHO_LISTA)
            self.caja_izq.show()
            self.panel.show()
        self.bt_volver.setVisible(estrecho and self.actual is not None)

    def _volver(self):
        self._dejar_grupo()
        self._acomodar()

    def _dejar_grupo(self):
        self.actual = None
        self.reloj_chat.stop()
        self.et_grupo.setText("Elige un grupo, explora los abiertos o crea el tuyo")
        self.bt_info.hide()
        self.fijado.hide()
        _borrar_layout(self.lay)
        self.lay.addStretch(1)
        self._activar(False)

    def _activar(self, si):
        for w in (self.campo, self.bt_enviar, self.bt_suena, self.bt_emoji, self.bt_mic):
            w.setEnabled(si)

    # ------------------------------------------------------------ lista
    def _cargar_lista(self):
        if self.api is None:
            return
        en_segundo_plano(self.api.mis_grupos, ok=self._pintar_lista, error=self._lista_fallo, dueno=self)

    def _lista_fallo(self, e):
        if self.lay_lista.count() <= 2:
            _borrar_layout(self.lay_lista)
            et = QLabel(_motivo(e))
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
            self.lay_lista.addStretch(1)

    def _pintar_lista(self, grupos):
        barra = self.scroll_lista.verticalScrollBar().value()
        _borrar_layout(self.lay_lista)
        if not grupos:
            et = QLabel("Aún no estás en ningún grupo.\nExplora los abiertos o crea el tuyo para hablar de música.")
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay_lista.addWidget(et)
        for g in grupos:
            self.lay_lista.addWidget(self._fila(g))
            if self.actual and self.actual["id"] == g["id"]:
                self.actual.update({k: g[k] for k in ("nombre", "rol", "miembros", "cerrado", "codigo") if k in g})
        self.lay_lista.addStretch(1)
        QTimer.singleShot(0, lambda: self.scroll_lista.verticalScrollBar().setValue(barra))

    def _fila(self, g):
        b = QPushButton()
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(64)
        b.setFocusPolicy(Qt.NoFocus)
        activo = self.actual and self.actual["id"] == g["id"]
        b.setStyleSheet(f"QPushButton{{text-align:left;border:none;border-radius:12px;padding:0;"
                        f"background:{C['superficie2'] if activo else 'transparent'};}}"
                        f"QPushButton:hover{{background:{C['superficie3'] if activo else C['superficie']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 6, 10, 6)
        h.addWidget(Avatar(40, g.get("nombre") or "#", C["acento"], None))
        col = QVBoxLayout()
        col.setSpacing(0)
        sin = int(g.get("sin_leer") or 0)
        n = QLabel(_html(g.get("nombre")) + (" 🔒" if g.get("tipo") == "privado" else ""))
        n.setStyleSheet(f"font-weight:{900 if sin else 700};background:transparent;")
        col.addWidget(n)
        prev = QLabel(G.vista_previa(g))
        prev.setFont(_fuente_emoji(9))
        prev.setStyleSheet(f"color:{C['texto'] if sin else C['texto2']};background:transparent;")
        prev.setMinimumWidth(10)
        col.addWidget(prev)
        h.addLayout(col, 1)
        if sin:
            gl = QLabel("99+" if sin > 99 else str(sin))
            gl.setAlignment(Qt.AlignCenter)
            gl.setStyleSheet(f"background:{C['acento']};color:{C['acento_texto']};border-radius:9px;"
                             "font-size:11px;font-weight:900;padding:1px 7px;")
            h.addWidget(gl)
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False, g=g: self.abrir(g))
        return b

    def _crear(self):
        d = DialogoCrearGrupo(self.ctx, self.api, self)
        if d.exec() == QDialog.Accepted and d.grupo:
            if d.grupo.get("codigo"):
                self.ctx.avisar(f"Grupo creado. Su código para invitar es {d.grupo['codigo']}")
            self.abrir(d.grupo)
            self._cargar_lista()

    def _explorar(self):
        d = DialogoExplorar(self.ctx, self.api, self)
        if d.exec() == QDialog.Accepted and d.elegido:
            self.abrir(d.elegido)
            self._cargar_lista()

    def _codigo(self):
        unirse_con_codigo(self.ctx, self.api, self, lambda g: (self.abrir(g), self._cargar_lista()))

    # ------------------------------------------------------------ conversación
    def abrir(self, g):
        self.actual = dict(g)
        self.mensajes = []
        self.et_grupo.setText(f"{_html(g.get('nombre'))}  <span style='color:{C['texto3']};font-size:13px;"
                              f"font-weight:600'>{'Privado' if g.get('tipo') == 'privado' else 'Abierto'} · "
                              f"{_personas(g.get('miembros'))}</span>")
        self.bt_info.show()
        cerrado = bool(g.get("cerrado"))
        self._activar(not cerrado)
        self.aviso.setText("La moderación de Caudal cerró este grupo. Ya no se puede escribir." if cerrado else "")
        self.aviso.setVisible(cerrado)
        _borrar_layout(self.lay)
        self.cargando = QLabel("Cargando el grupo…")
        self.cargando.setAlignment(Qt.AlignCenter)
        self.cargando.setObjectName("ayuda")
        self.lay.addWidget(self.cargando)
        self.lay.addStretch(1)
        self._acomodar()
        gid = g["id"]
        en_segundo_plano(self.api.mensajes, gid, ok=lambda l, gid=gid: self._llegan(gid, l, True),
                         error=lambda e, gid=gid: self._fallo_carga(gid, e), dueno=self, urgente=True)
        en_segundo_plano(self.api.fijados, gid, ok=lambda l, gid=gid: self._pintar_fijado(gid, l),
                         error=lambda _e: None, dueno=self)
        self.reloj_chat.start()

    def _fallo_carga(self, gid, e):
        if self.actual and self.actual["id"] == gid and not self.mensajes:
            self.cargando.setText(_motivo(e))

    def _pintar_fijado(self, gid, lista):
        if not self.actual or self.actual["id"] != gid:
            return
        if not lista:
            self.fijado.hide()
            return
        m = lista[-1]
        que = m.get("texto") or (f"♪ {m['pista'].get('titulo')}" if m.get("pista") else "🎤 Nota de voz")
        self.fijado.setText(f"📌 {_html(que)}" + (f"  (+{len(lista) - 1})" if len(lista) > 1 else ""))
        self.fijado.show()

    def _llegan(self, gid, lista, todo=False):
        if not self.actual or self.actual["id"] != gid:
            return
        if todo:
            _borrar_layout(self.lay)
            self.lay.addStretch(1)
            self.mensajes = []
        ids = {m["id"] for m in self.mensajes}
        nuevos = [m for m in lista if m["id"] not in ids]
        for m in nuevos:
            anterior = self.mensajes[-1] if self.mensajes else None
            con_nombre = not m.get("mio") and (anterior is None or anterior["autor"].get("id") != m["autor"].get("id"))
            self._burbuja(m, con_nombre)
            self.mensajes.append(m)
        if todo and not self.mensajes:
            et = QLabel(f"Aquí empieza «{self.actual.get('nombre')}».\n"
                        "Saluda, comparte lo que estás escuchando 🎵 o manda una nota de voz 🎤")
            et.setAlignment(Qt.AlignCenter)
            et.setWordWrap(True)
            et.setObjectName("ayuda")
            self.lay.insertWidget(0, et)
        if nuevos or todo:
            en_segundo_plano(self.api.leido, gid, dueno=self)
            barra = self.scroll.verticalScrollBar()
            QTimer.singleShot(40, lambda: barra.setValue(barra.maximum()))

    def _nuevos(self):
        if not self.actual or not self.isVisible() or self._enviando:
            return
        desde = self.mensajes[-1]["id"] if self.mensajes else 0
        gid = self.actual["id"]
        en_segundo_plano(self.api.nuevos, gid, desde, ok=lambda l: self._llegan(gid, l),
                         error=lambda _e: None, dueno=self, urgente=True)

    def _burbuja(self, m, con_nombre=False, pendiente=False):
        mio = pendiente or bool(m.get("mio"))
        caja = QFrame()
        caja.setObjectName("burbuja")
        caja.setStyleSheet(f"QFrame#burbuja{{background:{C['acento'] if mio else C['superficie2']};border-radius:14px;}}")
        caja.setMaximumWidth(440)
        v = QVBoxLayout(caja)
        v.setContentsMargins(12, 8, 12, 6)
        v.setSpacing(2)
        color = C["acento_texto"] if mio else C["texto"]
        if con_nombre:
            rol = m["autor"].get("rol")
            extra = " · dueño" if rol == "dueno" else " · modera" if rol == "moderador" else ""
            n = QLabel(_html(m.get("visible")) + extra)
            n.setStyleSheet(f"color:{C['acento']};font-weight:800;font-size:12px;background:transparent;")
            v.addWidget(n)
        p = m.get("pista")
        if m.get("audio") is not None:
            v.addLayout(self._nota(m, color, mio))
        elif p:
            fila = QHBoxLayout()
            port = Portada(52, radio=6)
            port.set_url(p.get("miniatura") or "")
            fila.addWidget(port)
            txt = QLabel(f"<b>{_html(p.get('titulo'))}</b><br><span style='font-size:11px'>{_html(p.get('artista'))}</span>")
            txt.setWordWrap(True)
            txt.setStyleSheet(f"color:{color};background:transparent;")
            fila.addWidget(txt, 1)
            play = QPushButton()
            play.setIcon(iconos.icono("reproducir", 18, C["acento_texto"] if not mio else C["acento"]))
            play.setFixedSize(34, 34)
            play.setCursor(Qt.PointingHandCursor)
            play.setToolTip("Escuchar")
            play.setStyleSheet(f"background:{C['acento'] if not mio else C['acento_texto']};border:none;border-radius:17px;")
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
        pie = "Enviando…" if pendiente else " ".join(
            x for x in ("📌" if m.get("fijado") else "", "Oculto por reportes ·" if m.get("oculto") else "",
                        _hora(m["fecha"])) if x)
        hora = QLabel(pie)
        hora.setAlignment(Qt.AlignRight)
        hora.setStyleSheet(f"color:{color};font-size:10px;background:transparent;")
        ef = QGraphicsOpacityEffect(hora)
        ef.setOpacity(0.7)
        hora.setGraphicsEffect(ef)
        v.addWidget(hora)
        if not pendiente:
            caja.setContextMenuPolicy(Qt.CustomContextMenu)
            caja.customContextMenuRequested.connect(lambda pos, m=m, c=caja: self._opciones(m, c.mapToGlobal(pos)))
            caja.setToolTip("Clic derecho: opciones")
        if m.get("oculto"):
            ef2 = QGraphicsOpacityEffect(caja)
            ef2.setOpacity(0.6)
            caja.setGraphicsEffect(ef2)
        fila_ext = QHBoxLayout()
        if mio:
            fila_ext.addStretch(1)
        fila_ext.addWidget(caja)
        if not mio:
            fila_ext.addStretch(1)
        self.lay.insertLayout(self.lay.count() - 1, fila_ext)
        return caja, hora

    def _nota(self, m, color, mio):
        fila = QHBoxLayout()
        bt = QPushButton("▶")
        bt.setFixedSize(34, 34)
        bt.setCursor(Qt.PointingHandCursor)
        bt.setToolTip("Oír la nota de voz")
        bt.setStyleSheet(f"background:{C['acento'] if not mio else C['acento_texto']};"
                         f"color:{C['acento_texto'] if not mio else C['acento']};border:none;border-radius:17px;font-size:14px;")
        et = QLabel(f"🎤 {duracion(m.get('audio_seg'))}")
        et.setFont(_fuente_emoji(10))
        et.setStyleSheet(f"color:{color};background:transparent;")
        ruta = m.get("audio") or ""
        bt.setEnabled(bool(ruta))
        bt.clicked.connect(lambda _=False: self._oir(ruta, bt, et, m.get("audio_seg")))
        fila.addWidget(bt)
        fila.addWidget(et, 1)
        return fila

    def _oir(self, ruta, bt, et, seg):
        rep = NV.Reproductor.compartido()
        if rep.sonando == ruta:
            rep.parar()
            bt.setText("▶")
            return
        bt.setText("…")

        def listo(url):
            try:
                r = getattr(self.ctx, "reproductor", None)
                if r is not None and getattr(r, "estado", "") == "sonando":
                    r.pausar()
                rep.tocar(ruta, url)
            except Exception:  # noqa: BLE001
                bt.setText("▶")
                self.ctx.avisar("No se pudo oír la nota de voz.")
                return
            bt.setText("⏸")
            reloj = QTimer(bt)

            def tic():
                try:
                    if rep.sonando != ruta or rep.termino():
                        bt.setText("▶")
                        et.setText(f"🎤 {duracion(seg)}")
                        reloj.stop()
                        return
                    et.setText(f"🎤 {duracion(rep.posicion())} / {duracion(seg)}")
                except RuntimeError:
                    reloj.stop()
            reloj.timeout.connect(tic)
            QTimer.singleShot(800, lambda: reloj.start(300))

        def fallo(e):
            bt.setText("▶")
            self.ctx.avisar(_motivo(e))

        en_segundo_plano(self.api.url_audio, ruta, ok=listo, error=fallo, dueno=self, urgente=True)

    # ------------------------------------------------------------ enviar
    def _enviar(self, pista=None):
        if self._grabacion is not None:
            self._terminar_grabar()
            return
        if not self.actual:
            return
        texto = "" if pista else self.campo.text().strip()
        if not texto and not pista:
            return
        if not pista:
            self.campo.clear()
        self._mandar(texto=texto, pista=pista)

    def _mandar(self, texto="", pista=None, datos=None, tipo="", seg=0):
        gid = self.actual["id"]
        prov = {"id": -1, "texto": texto, "pista": pista, "audio": "" if datos else None, "audio_seg": seg,
                "autor": {}, "visible": "Tú", "mio": True, "fecha": None}
        caja, hora = self._burbuja(prov, pendiente=True)
        barra = self.scroll.verticalScrollBar()
        QTimer.singleShot(40, lambda: barra.setValue(barra.maximum()))
        self._enviando += 1

        def trabajo():
            audio = self.api.subir_audio(gid, datos, tipo) if datos else None
            return self.api.enviar(gid, texto=texto, pista=pista, audio=audio, audio_seg=seg)

        def ok(m):
            self._enviando = max(0, self._enviando - 1)
            self._quitar(caja)
            if self.actual and self.actual["id"] == gid:
                self._llegan(gid, [m])

        def fallo(e):
            self._enviando = max(0, self._enviando - 1)
            try:
                hora.setText(f"⚠ {_motivo(e)}")
            except RuntimeError:
                pass

        en_segundo_plano(trabajo, ok=ok, error=fallo, dueno=self, urgente=True)

    def _quitar(self, caja):
        for i in range(self.lay.count()):
            it = self.lay.itemAt(i)
            l = it.layout() if it is not None else None
            if l is not None and any(l.itemAt(j).widget() is caja for j in range(l.count())):
                self.lay.takeAt(i)
                _borrar_layout(l)
                return

    def _enviar_suena(self):
        r = getattr(self.ctx, "reproductor", None)
        p = getattr(r, "actual", None)
        if not p:
            self.ctx.avisar("Ahora no suena nada. Pon una canción y vuelve a tocar 🎵")
            return
        if not p.get("video_id"):
            self.ctx.avisar("Esa canción es un archivo de tu PC: solo se pueden enviar canciones de YouTube Music.")
            return
        self._enviar(pista=p)

    # ------------------------------------------------------------ notas de voz
    def _alternar_grabar(self):
        if self._grabacion is None:
            self._empezar_grabar()
        else:
            self._terminar_grabar()

    def _empezar_grabar(self):
        g = NV.Grabacion()
        self._grabacion = g
        self._t_grabar = time.monotonic()
        self.campo.setEnabled(False)
        self.campo.setPlaceholderText("Grabando… pulsa Enviar para mandarla o Descartar")
        self.bt_mic.setText("⏹")
        self.bt_cancelar_nota.show()
        self.reloj_grabar.start()
        hilo = threading.Thread(target=g.correr, daemon=True)
        hilo.start()
        g.hilo = hilo

    def _tic_grabar(self):
        if self._grabacion is None:
            return
        seg = int(time.monotonic() - self._t_grabar)
        self.campo.setPlaceholderText(f"🔴 Grabando {duracion(seg)} · máx. {duracion(G.MAX_SEGUNDOS_AUDIO)}")
        if self._grabacion.error or seg >= G.MAX_SEGUNDOS_AUDIO:
            self._terminar_grabar()

    def _terminar_grabar(self, cancelar=False):
        g = self._grabacion
        if g is None:
            return
        self._grabacion = None
        self.reloj_grabar.stop()
        self.bt_mic.setText("🎤")
        self.bt_cancelar_nota.hide()
        self.campo.setEnabled(self.actual is not None)
        self.campo.setPlaceholderText("Escribe al grupo")
        if cancelar:
            g.cancelar()
            return
        g.parar()

        def esperar():
            g.hilo.join(5)
            if g.error:
                raise RuntimeError(g.error)
            if g.segundos < 1:
                raise RuntimeError("Mantén la grabación un poco más.")
            datos, tipo = NV.comprimir(g.pcm)
            return datos, tipo, max(1, min(G.MAX_SEGUNDOS_AUDIO, g.segundos))

        def ok(r):
            if self.actual:
                datos, tipo, seg = r
                self._mandar(datos=datos, tipo=tipo, seg=seg)

        en_segundo_plano(esperar, ok=ok, error=lambda e: self.ctx.avisar(str(e)), dueno=self, urgente=True)

    # ------------------------------------------------------------ opciones de un mensaje
    def _opciones(self, m, donde):
        menu = QMenu(self)
        modero = G.modera(self.actual)
        acciones = {}
        if m.get("texto"):
            acciones[menu.addAction("Copiar texto")] = "copiar"
        if modero:
            acciones[menu.addAction("Quitar de fijados" if m.get("fijado") else "Fijar arriba")] = \
                "desfijar" if m.get("fijado") else "fijar"
        if modero and not m.get("mio"):
            acciones[menu.addAction("Volver a mostrar" if m.get("oculto") else "Ocultar")] = \
                "mostrar" if m.get("oculto") else "ocultar"
        if not m.get("mio"):
            acciones[menu.addAction("Reportar…")] = "reportar"
        if m.get("mio") or modero:
            acciones[menu.addAction("Borrar")] = "borrar"
        elegida = menu.exec(donde)
        accion = acciones.get(elegida)
        if not accion:
            return
        if accion == "copiar":
            QApplication.clipboard().setText(m.get("texto") or "")
            self.ctx.avisar("Texto copiado")
            return
        if accion == "reportar":
            motivos = ["Insulta o acosa", "Contenido sexual", "Spam o estafa", "Pone en peligro a un menor", "Otra cosa"]
            motivo, ok = QInputDialog.getItem(self, "Reportar", "¿Por qué lo reportas?", motivos, 0, False)
            if not ok:
                return
            en_segundo_plano(self.api.reportar, m["id"], motivo,
                             ok=lambda _r: self.ctx.avisar("Gracias. Quien modera el grupo lo revisará; "
                                                           "con varios reportes se oculta solo."),
                             error=lambda e: self.ctx.avisar(_motivo(e)), dueno=self, urgente=True)
            return
        en_segundo_plano(self.api.accion, m["id"], accion,
                         ok=lambda _r: self.abrir(self.actual) if self.actual else None,
                         error=lambda e: self.ctx.avisar(_motivo(e)), dueno=self, urgente=True)

    # ------------------------------------------------------------ info del grupo
    def _info(self):
        if not self.actual:
            return
        d = DialogoInfoGrupo(self.ctx, self.api, self.actual, self)
        d.exec()
        if d.salio:
            self._dejar_grupo()
            self._acomodar()
        elif d.grupo:
            self.abrir({**self.actual, **d.grupo})
        self._cargar_lista()


class DialogoInfoGrupo(QDialog):
    def __init__(self, ctx, api, grupo, padre=None):
        super().__init__(padre)
        self.ctx, self.api, self.grupo, self.salio = ctx, api, dict(grupo), False
        self.setWindowTitle("Info del grupo")
        self.resize(480, 640)
        v = QVBoxLayout(self)
        self.cab = QLabel("")
        self.cab.setWordWrap(True)
        v.addWidget(self.cab)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.interior = QWidget()
        self.lay = QVBoxLayout(self.interior)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.interior)
        v.addWidget(self.scroll, 1)
        abajo = QHBoxLayout()
        self.bt_salir = _boton("Salir del grupo")
        self.bt_salir.clicked.connect(self._salir)
        abajo.addWidget(self.bt_salir)
        self.bt_borrar = _boton("Borrar el grupo")
        self.bt_borrar.clicked.connect(self._borrar)
        abajo.addWidget(self.bt_borrar)
        abajo.addStretch(1)
        cerrar = _boton("Cerrar", principal=True)
        cerrar.clicked.connect(self.accept)
        abajo.addWidget(cerrar)
        v.addLayout(abajo)
        self._cargar()

    def _cargar(self):
        gid = self.grupo["id"]

        def trabajo():
            g = self.api.ver(gid) or self.grupo
            gente = self.api.miembros(gid)
            rep = self.api.reportados(gid) if G.modera(g) else []
            return g, gente, rep

        en_segundo_plano(trabajo, ok=self._pintar, error=lambda e: self.ctx.avisar(_motivo(e)), dueno=self, urgente=True)

    def _pintar(self, r):
        g, gente, rep = r
        self.grupo = {**self.grupo, **g}
        g = self.grupo
        es_dueno = g.get("rol") == "dueno"
        self.bt_borrar.setVisible(es_dueno)
        self.cab.setText(f"<span style='font-size:20px;font-weight:900'>{_html(g.get('nombre'))}</span><br>"
                         f"<span style='color:{C['texto2']}'>{'Grupo privado' if g.get('tipo') == 'privado' else 'Grupo abierto'}"
                         f" · {_personas(g.get('miembros'))}</span>"
                         + (f"<br>{_html(g.get('descripcion'))}" if g.get("descripcion") else ""))
        _borrar_layout(self.lay)
        if g.get("tipo") == "privado" and g.get("codigo"):
            fila = QHBoxLayout()
            et = QLabel(f"Código para invitar: <b style='font-size:18px;letter-spacing:2px'>{_html(g['codigo'])}</b>")
            fila.addWidget(et, 1)
            copiar = _boton("Copiar")
            copiar.clicked.connect(lambda: (QApplication.clipboard().setText(g["codigo"]), self.ctx.avisar("Código copiado")))
            fila.addWidget(copiar)
            if es_dueno:
                nuevo = _boton("Cambiar", tip="El código anterior deja de servir")
                nuevo.clicked.connect(lambda: self._hacer(lambda: self.api.cambiar_codigo(g["id"]), "Código nuevo listo"))
                fila.addWidget(nuevo)
            caja = QWidget()
            caja.setLayout(fila)
            self.lay.addWidget(caja)
        if G.modera(g):
            editar = _boton("Editar nombre y descripción")
            editar.clicked.connect(self._editar)
            self.lay.addWidget(editar)
        if rep:
            t = QLabel(f"<b>Reportado ({len(rep)})</b>")
            self.lay.addWidget(t)
            for m in rep:
                que = m.get("texto") or ("🎤 Nota de voz" if m.get("audio") else f"♪ {(m.get('pista') or {}).get('titulo', '')}")
                fila = QHBoxLayout()
                et = QLabel(f"{_html(que)}<br><span style='color:{C['texto2']}'>{_html(m.get('visible'))} · "
                            f"{m.get('reportes', 0)} reportes · {_html(', '.join(sorted(set(m.get('motivos') or []))))}</span>")
                et.setWordWrap(True)
                fila.addWidget(et, 1)
                for texto, accion in (("Mostrar", "mostrar") if m.get("oculto") else ("Ocultar", "ocultar"), ("Borrar", "borrar")):
                    b = _boton(texto)
                    b.clicked.connect(lambda _=False, m=m, a=accion: self._hacer(lambda: self.api.accion(m["id"], a), "Hecho"))
                    fila.addWidget(b)
                caja = QWidget()
                caja.setLayout(fila)
                self.lay.addWidget(caja)
        t = QLabel("<b>Personas</b>")
        self.lay.addWidget(t)
        for p in gente:
            fila = QHBoxLayout()
            fila.addWidget(Avatar(32, p.get("nombre") or p.get("usuario") or "?", C["acento"], p.get("foto_url")))
            rol = {"dueno": " · dueño", "moderador": " · modera"}.get(p.get("rol"), "")
            sil = " · silenciado" if p.get("silenciado_hasta") else ""
            et = QLabel(f"{_html(p.get('nombre') or p.get('usuario'))}<br><span style='color:{C['texto2']}'>"
                        f"@{_html(p.get('usuario'))}{rol}{sil}</span>")
            fila.addWidget(et, 1)
            if self._puedo_con(p) or (es_dueno and p.get("rol") != "dueno"):
                b = _boton("…", tip="Opciones")
                b.clicked.connect(lambda _=False, p=p, b=b: self._sobre(p, b))
                fila.addWidget(b)
            caja = QWidget()
            caja.setLayout(fila)
            self.lay.addWidget(caja)
        self.lay.addStretch(1)

    def _yo(self):
        return str(self.api.yo)

    def _puedo_con(self, p):
        r = self.grupo.get("rol")
        if str(p.get("id")) == self._yo() or p.get("rol") == "dueno":
            return False
        return r == "dueno" or (r == "moderador" and p.get("rol") == "miembro")

    def _sobre(self, p, boton):
        menu = QMenu(self)
        acc = {}
        es_dueno = self.grupo.get("rol") == "dueno"
        if es_dueno:
            acc[menu.addAction("Quitar de moderadores" if p.get("rol") == "moderador" else "Hacer moderador")] = \
                "quitar_mod" if p.get("rol") == "moderador" else "mod"
            acc[menu.addAction("Pasarle el grupo")] = "dueno"
        if self._puedo_con(p):
            if p.get("silenciado_hasta"):
                acc[menu.addAction("Quitar el silencio")] = "sil0"
            else:
                acc[menu.addAction("Silenciar 1 hora")] = "sil60"
                acc[menu.addAction("Silenciar 1 día")] = "sil1440"
            acc[menu.addAction("Sacar del grupo")] = "expulsar"
        a = acc.get(menu.exec(boton.mapToGlobal(boton.rect().bottomLeft())))
        if not a:
            return
        gid, uid, n = self.grupo["id"], p["id"], p.get("nombre") or p.get("usuario")
        if a == "mod":
            self._hacer(lambda: self.api.poner_rol(gid, uid, True), f"{n} ahora modera el grupo")
        elif a == "quitar_mod":
            self._hacer(lambda: self.api.poner_rol(gid, uid, False), f"{n} ya no modera el grupo")
        elif a == "dueno":
            if self._confirmar(f"¿Pasarle el grupo a {n}?", f"{n} será quien lo administre. Tú quedarás como moderador."):
                self._hacer(lambda: self.api.pasar_dueno(gid, uid), f"Ahora el grupo es de {n}")
        elif a == "expulsar":
            if self._confirmar(f"¿Sacar a {n}?", f"{n} saldrá del grupo y no podrá volver a entrar."):
                self._hacer(lambda: self.api.expulsar(gid, uid), f"{n} ya no está en el grupo")
        else:
            minutos = int(a[3:])
            self._hacer(lambda: self.api.silenciar(gid, uid, minutos),
                        f"{n} puede volver a escribir" if minutos == 0 else f"{n} no podrá escribir por un rato")

    def _confirmar(self, titulo, texto):
        return QMessageBox.question(self, titulo, texto) == QMessageBox.Yes

    def _hacer(self, f, hecho):
        en_segundo_plano(f, ok=lambda _r: (self.ctx.avisar(hecho), self._cargar()),
                         error=lambda e: self.ctx.avisar(_motivo(e)), dueno=self, urgente=True)

    def _editar(self):
        nombre, ok = QInputDialog.getText(self, "Editar el grupo", "Nombre:", text=self.grupo.get("nombre") or "")
        if not ok:
            return
        desc, ok = QInputDialog.getMultiLineText(self, "Editar el grupo", "De qué va:", self.grupo.get("descripcion") or "")
        if not ok:
            return
        self._hacer(lambda: self.api.editar(self.grupo["id"], nombre, desc), "Grupo actualizado")

    def _salir(self):
        if not self._confirmar(f"¿Salir de «{self.grupo.get('nombre')}»?", "Dejarás de ver sus mensajes."):
            return

        def ok(_r):
            self.salio = True
            self.accept()
        en_segundo_plano(self.api.salir, self.grupo["id"], ok=ok, error=lambda e: self.ctx.avisar(_motivo(e)),
                         dueno=self, urgente=True)

    def _borrar(self):
        if not self._confirmar(f"¿Borrar «{self.grupo.get('nombre')}»?",
                               "Se borran todos sus mensajes y notas de voz, para todos. No se puede deshacer."):
            return

        def ok(_r):
            self.salio = True
            self.accept()
        en_segundo_plano(self.api.borrar, self.grupo["id"], ok=ok, error=lambda e: self.ctx.avisar(_motivo(e)),
                         dueno=self, urgente=True)
