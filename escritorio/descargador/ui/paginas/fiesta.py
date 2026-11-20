# -*- coding: utf-8 -*-
"""«Fiesta»: el anfitrión enseña un QR; los invitados piden y votan canciones
desde su teléfono (página web, sin instalar nada) y esta PC las pone.

La fiesta vive en el ControlFiesta de la app (descargador/fiesta.py): sigue
abierta aunque se cierre esta ventana, hasta pulsar «Cerrar la fiesta».
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QSpinBox, QStackedWidget,
                               QVBoxLayout, QWidget)

from ... import fiesta as F
from ... import qr
from .. import iconos
from ..componentes import Portada, _borrar_layout
from ..estilos import C, hoja


class LienzoQR(QWidget):
    """Dibuja un QR con su margen blanco (4 módulos), lo más grande que quepa."""

    def __init__(self, lado=260, padre=None):
        super().__init__(padre)
        self.matriz = []
        self.texto = ""
        self.setFixedSize(lado, lado)

    def poner(self, texto):
        self.texto = texto or ""
        self.matriz = qr.matriz(self.texto) if self.texto else []
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        r = QRectF(self.rect())
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(r, 14, 14)
        if not self.matriz:
            return
        n = len(self.matriz)
        total = n + 8
        modulo = int(min(r.width(), r.height()) // total) or 1
        x0 = (r.width() - modulo * n) / 2
        y0 = (r.height() - modulo * n) / 2
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setBrush(QColor("#000000"))
        for y, fila in enumerate(self.matriz):
            for x, negro in enumerate(fila):
                if negro:
                    p.drawRect(QRectF(x0 + x * modulo, y0 + y * modulo, modulo, modulo))
        p.end()


def _etiqueta(texto, nombre=None, envolver=True):
    e = QLabel(texto)
    if nombre:
        e.setObjectName(nombre)
    e.setWordWrap(envolver)
    return e


class PaginaFiesta(QWidget):
    def __init__(self, ctx, padre=None, control=None):
        super().__init__(padre)
        self.ctx = ctx
        self.c = control or F.control(ctx)
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(28, 24, 28, 22)
        raiz.setSpacing(12)
        raiz.addWidget(_etiqueta("Fiesta", "titulo_pagina"))
        self.pilas = QStackedWidget()
        raiz.addWidget(self.pilas, 1)
        self.pilas.addWidget(self._hacer_entrada())
        self.pilas.addWidget(self._hacer_fiesta())
        self.pilas.addWidget(self._hacer_fin())
        self.et_error = _etiqueta("")
        self.et_error.setStyleSheet(f"color:{C['error']};")
        self.et_error.hide()
        raiz.addWidget(self.et_error)

        self.c.cambio.connect(self._pintar)
        self.c.error.connect(self._mostrar_error)
        self._pintar()

    # ------------------------------------------------------------ entrada
    def _caja(self, v):
        marco = QFrame()
        marco.setObjectName("caja")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(8)
        v.addWidget(marco)
        return lay

    def _hacer_entrada(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        v.addWidget(_etiqueta("Tú pones la música y tus invitados la eligen: escanean un QR con su "
                              "teléfono, buscan canciones, las piden y votan cuáles suenan antes. "
                              "No necesitan instalar nada ni tener cuenta.", "secundario"))
        caja = self._caja(v)
        caja.addWidget(_etiqueta("Nombre de la fiesta", "ayuda"))
        self.campo_nombre = QLineEdit()
        self.campo_nombre.setMaxLength(60)
        self.campo_nombre.setPlaceholderText("Por ejemplo: Cumple de Lu")
        caja.addWidget(self.campo_nombre)
        caja.addWidget(_etiqueta("Canciones que puede pedir cada invitado (0 = sin límite)", "ayuda"))
        self.campo_limite = QSpinBox()
        self.campo_limite.setRange(0, 50)
        self.campo_limite.setValue(F.LIMITE_DEFECTO)
        self.campo_limite.setFixedWidth(90)
        caja.addWidget(self.campo_limite)
        self.bt_crear = QPushButton("Empezar la fiesta")
        self.bt_crear.setObjectName("principal")
        self.bt_crear.setCursor(Qt.PointingHandCursor)
        self.bt_crear.clicked.connect(self._crear)
        caja.addWidget(self.bt_crear, 0, Qt.AlignLeft)
        v.addStretch(1)
        return w

    def _crear(self):
        self.et_error.hide()
        self.c.crear(self.campo_nombre.text().strip(), self.campo_limite.value())

    def _mostrar_error(self, texto):
        self.et_error.setText(texto)
        self.et_error.show()

    # ------------------------------------------------------------ fiesta abierta
    def _hacer_fiesta(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(18)

        # ---- izquierda: QR, código y ajustes
        izq = QVBoxLayout()
        izq.setSpacing(10)
        h.addLayout(izq, 0)
        self.lienzo_qr = LienzoQR(260)
        izq.addWidget(self.lienzo_qr, 0, Qt.AlignHCenter)
        izq.addWidget(_etiqueta("Que lo escaneen con la cámara del teléfono", "ayuda"), 0, Qt.AlignHCenter)
        self.et_codigo = QLabel("")
        f = QFont("Consolas")
        f.setPointSize(26)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 6)
        self.et_codigo.setFont(f)
        self.et_codigo.setAlignment(Qt.AlignCenter)
        self.et_codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        izq.addWidget(self.et_codigo)
        self.et_enlace = _etiqueta("", "ayuda")
        self.et_enlace.setAlignment(Qt.AlignCenter)
        self.et_enlace.setTextInteractionFlags(Qt.TextSelectableByMouse)
        izq.addWidget(self.et_enlace)
        self.bt_copiar = QPushButton("Copiar enlace")
        self.bt_copiar.setObjectName("contorno")
        self.bt_copiar.setCursor(Qt.PointingHandCursor)
        self.bt_copiar.clicked.connect(self._copiar)
        izq.addWidget(self.bt_copiar, 0, Qt.AlignHCenter)

        caja = self._caja(izq)
        fila = QHBoxLayout()
        fila.addWidget(_etiqueta("Canciones por invitado", "ayuda", False), 1)
        self.limite_vivo = QSpinBox()
        self.limite_vivo.setRange(0, 50)
        self.limite_vivo.setFixedWidth(80)
        self.limite_vivo.setToolTip("0 = sin límite")
        self.limite_vivo.editingFinished.connect(lambda: self.c.poner_limite(self.limite_vivo.value()))
        self.limite_vivo.valueChanged.connect(self._limite_cambiado)
        fila.addWidget(self.limite_vivo)
        caja.addLayout(fila)
        self.et_limite = _etiqueta("", "ayuda")
        caja.addWidget(self.et_limite)
        self.auto = QCheckBox("Poner la cola de la fiesta sola")
        self.auto.setChecked(True)
        self.auto.setToolTip("Cuando a tu canción le quedan unos segundos, suena la más votada de la fiesta.")
        self.auto.toggled.connect(self.c.poner_auto)
        caja.addWidget(self.auto)
        self.bt_cerrar = QPushButton("Cerrar la fiesta")
        self.bt_cerrar.setObjectName("contorno")
        self.bt_cerrar.setCursor(Qt.PointingHandCursor)
        self.bt_cerrar.clicked.connect(self._confirmar_cierre)
        izq.addWidget(self.bt_cerrar, 0, Qt.AlignHCenter)
        izq.addStretch(1)

        # ---- derecha: lo que suena y la cola
        der = QVBoxLayout()
        der.setSpacing(10)
        h.addLayout(der, 1)
        self.et_nombre = _etiqueta("", "titulo_seccion")
        der.addWidget(self.et_nombre)
        self.et_gente = _etiqueta("", "secundario")
        der.addWidget(self.et_gente)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta_fiesta")
        tarjeta.setStyleSheet(
            "QFrame#tarjeta_fiesta{border-radius:18px;"
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #2a1f4a,stop:1 {C['superficie']});}}")
        ht = QHBoxLayout(tarjeta)
        ht.setContentsMargins(16, 14, 16, 14)
        ht.setSpacing(14)
        self.portada = Portada(84, radio=10)
        ht.addWidget(self.portada)
        vt = QVBoxLayout()
        vt.setSpacing(2)
        eti = QLabel("AHORA SUENA")
        eti.setStyleSheet(f"color:{C['acento']};font-size:11px;font-weight:800;letter-spacing:1px;"
                          "background:transparent;")
        vt.addWidget(eti)
        self.et_titulo = _etiqueta("")
        self.et_titulo.setStyleSheet("font-size:19px;font-weight:900;background:transparent;")
        vt.addWidget(self.et_titulo)
        self.et_artista = _etiqueta("")
        self.et_artista.setStyleSheet(f"color:{C['texto2']};background:transparent;")
        vt.addWidget(self.et_artista)
        vt.addStretch(1)
        ht.addLayout(vt, 1)
        der.addWidget(tarjeta)

        der.addWidget(_etiqueta("Siguientes", "titulo_seccion"))
        der.addWidget(_etiqueta("Suenan primero las más votadas por tus invitados.", "ayuda"))
        self.zona = QScrollArea()
        self.zona.setWidgetResizable(True)
        self.zona.setFrameShape(QFrame.NoFrame)
        interior = QWidget()
        self.lista = QVBoxLayout(interior)
        self.lista.setContentsMargins(0, 0, 6, 0)
        self.lista.setSpacing(6)
        self.zona.setWidget(interior)
        der.addWidget(self.zona, 1)
        return w

    def _limite_cambiado(self, v):
        self.et_limite.setText("Sin límite: cada invitado pide las que quiera." if v == 0
                               else f"Cada invitado puede pedir {v} {'canción' if v == 1 else 'canciones'}.")

    def _copiar(self):
        QGuiApplication.clipboard().setText(self.c.enlace)
        aviso = getattr(self.ctx, "aviso", None)
        if aviso is not None:
            aviso.emit("Enlace de la fiesta copiado")

    def _confirmar_cierre(self):
        r = QMessageBox.question(self, "Cerrar la fiesta",
                                 "¿Cerrar la fiesta? Tus invitados ya no podrán pedir ni votar canciones.",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            self.c.cerrar()

    def _fila(self, i, c):
        caja = QFrame()
        caja.setObjectName("caja")
        h = QHBoxLayout(caja)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(10)
        n = QLabel(str(i + 1))
        n.setFixedWidth(22)
        n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet(f"color:{C['texto3']};font-weight:800;background:transparent;")
        h.addWidget(n)
        p = Portada(44, radio=8)
        p.set_url(c["miniatura"])
        h.addWidget(p)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(c["titulo"])
        t.setStyleSheet("font-weight:700;background:transparent;")
        col.addWidget(t)
        quien = "del anfitrión" if c["de_anfitrion"] else (f"la pidió {c['nombre']}" if c["nombre"] else "")
        sub = QLabel(" · ".join(x for x in (c["artista"], quien) if x))
        sub.setStyleSheet(f"color:{C['texto3']};background:transparent;")
        col.addWidget(sub)
        h.addLayout(col, 1)
        votos = QLabel(f"♥ {c['votos']}")
        votos.setObjectName("votos")
        votos.setToolTip(f"{c['votos']} {'voto' if c['votos'] == 1 else 'votos'}")
        votos.setStyleSheet(f"color:{C['acento'] if c['votos'] else C['texto3']};font-weight:800;"
                            "background:transparent;")
        h.addWidget(votos)
        ya = QPushButton("Poner ahora")
        ya.setObjectName("contorno")
        ya.setCursor(Qt.PointingHandCursor)
        ya.clicked.connect(lambda _=False, c=c: self.c.poner_ahora(c))
        h.addWidget(ya)
        quitar = QPushButton("Quitar")
        quitar.setObjectName("contorno")
        quitar.setCursor(Qt.PointingHandCursor)
        quitar.setToolTip("Quitarla de la cola de la fiesta")
        quitar.clicked.connect(lambda _=False, i=c["id"]: self.c.quitar(i))
        h.addWidget(quitar)
        return caja

    # ------------------------------------------------------------ fin
    def _hacer_fin(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.et_fin = _etiqueta("La fiesta terminó. Tus invitados ya no pueden pedir canciones.", "secundario")
        v.addWidget(self.et_fin)
        bt = QPushButton("Hacer otra fiesta")
        bt.setObjectName("principal")
        bt.setCursor(Qt.PointingHandCursor)
        bt.clicked.connect(self.c.olvidar)
        v.addWidget(bt, 0, Qt.AlignLeft)
        v.addStretch(1)
        return w

    # ------------------------------------------------------------ pintar
    def _pintar(self):
        c = self.c
        f = c.fiesta
        if not c.codigo or f is None:
            self.pilas.setCurrentIndex(0)
            self.bt_crear.setEnabled(not c.creando)
            self.bt_crear.setText("Abriendo la fiesta…" if c.creando else "Empezar la fiesta")
            return
        if not f["abierta"]:
            self.pilas.setCurrentIndex(2)
            return
        self.et_error.hide()
        self.pilas.setCurrentIndex(1)
        if self.lienzo_qr.texto != c.enlace:
            self.lienzo_qr.poner(c.enlace)
        self.et_codigo.setText(c.codigo)
        self.et_enlace.setText(c.enlace.replace("https://", ""))
        self.et_nombre.setText(f["nombre"])
        n = f["invitados"]
        self.et_gente.setText("Todavía no ha entrado nadie" if n == 0 else
                              ("1 persona en la fiesta" if n == 1 else f"{n} personas en la fiesta"))
        if not self.limite_vivo.hasFocus():
            self.limite_vivo.blockSignals(True)
            self.limite_vivo.setValue(f["limite"])
            self.limite_vivo.blockSignals(False)
            self._limite_cambiado(f["limite"])
        s = f["sonando"]
        if s:
            self.et_titulo.setText(s["titulo"] or "Sin título")
            quien = f" · la pidió {s['nombre']}" if s["nombre"] else ""
            self.et_artista.setText((s["artista"] or "") + quien + (" · en pausa" if s["pausa"] else ""))
            self.portada.set_url(s["miniatura"])
        else:
            self.et_titulo.setText("Todavía no suena nada")
            self.et_artista.setText("Pon música o espera a que pidan la primera.")
            self.portada.set_url("")
        _borrar_layout(self.lista)
        if not f["cola"]:
            vacio = _etiqueta("La cola está vacía. Cuando tus invitados pidan canciones, aparecerán aquí.", "ayuda")
            self.lista.addWidget(vacio)
        for i, cancion in enumerate(f["cola"]):
            self.lista.addWidget(self._fila(i, cancion))
        self.lista.addStretch(1)


class VentanaFiesta(QWidget):
    """La página en su propia ventana, al lado de la principal."""

    def __init__(self, ctx, padre=None, control=None):
        super().__init__(padre, Qt.Window)
        self.setWindowTitle("Fiesta · Caudal")
        self.setWindowIcon(QIcon(iconos.icono_app(256)))
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.resize(1040, 700)
        self.setMinimumSize(880, 620)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.pagina = PaginaFiesta(ctx, self, control=control)
        lay.addWidget(self.pagina)


def abrir_ventana(ctx, padre=None):
    v = getattr(ctx, "_ventana_fiesta", None)
    if v is None:
        v = VentanaFiesta(ctx, padre or getattr(ctx, "ventana", None))
        ctx._ventana_fiesta = v
    v.show()
    v.raise_()
    v.activateWindow()
    return v
