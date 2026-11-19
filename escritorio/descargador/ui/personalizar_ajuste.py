# -*- coding: utf-8 -*-
"""Ajustes › «Personalizar»: marco animado para tu foto, efecto para tu nombre y tema de colores.

Arriba una vista previa en vivo (tu foto con el marco, tu nombre con el efecto y una Caudal en miniatura
con el tema); debajo, tres rejillas para elegir. Es exclusivo de donadores y fundadores (o de quien tenga un
pase de prueba): para el resto se puede probar cómo queda, pero «Aplicar» está bloqueado y salen los botones
«Donar aquí» y «Tengo un código de prueba». Igual que la app del teléfono."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QToolButton, QVBoxLayout, QWidget)

from ..premium_datos import (EFECTOS, MARCOS, NINGUNO, NOMBRES_EFECTO, NOMBRES_MARCO, NOMBRES_TEMA, TEMAS,
                             texto_vencimiento)
from .aspecto import Muestra
from .canje_pase import boton_codigo
from .donar import boton_donar
from .estilos import ACTUAL, C, acento_de, fondo_de
from .paginas import perfil_comun as PC
from .premium_estilos import NombreEfecto, pintar_marco

COLUMNAS = 4


def icono_marco(marco, lado=44):
    """Una muestra quieta del marco (la rejilla no anima nada: solo la vista previa)."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    if marco == NINGUNO:
        p.setPen(QPen(QColor(C["texto3"]), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(3, 3, lado - 6, lado - 6))
    else:
        pintar_marco(p, QRectF(1, 1, lado - 2, lado - 2), marco, ancho=6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"]))
        p.drawEllipse(QRectF(9, 9, lado - 18, lado - 18))
    p.end()
    return pm


def icono_tema(tema, ancho=64, alto=40):
    """Tres franjas con los colores del tema: fondo, panel y acento."""
    pm = QPixmap(ancho, alto)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    if tema == NINGUNO:
        f, ac = fondo_de("oscuro"), acento_de("cian")
    else:
        f, ac = fondo_de("premium_" + tema), acento_de("premium_" + tema)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(f[1]))
    p.drawRoundedRect(QRectF(0, 0, ancho, alto), 8, 8)
    p.setBrush(QColor(f[2]))
    p.drawRoundedRect(QRectF(5, 5, ancho * 0.42, alto - 10), 5, 5)
    p.setBrush(QColor(f[4]))
    p.drawRoundedRect(QRectF(ancho * 0.42 + 10, 5, ancho * 0.58 - 15, alto * 0.42), 5, 5)
    p.setBrush(QColor(ac[1]))
    p.drawRoundedRect(QRectF(ancho * 0.42 + 10, alto * 0.42 + 10, ancho * 0.3, alto * 0.22), 4, 4)
    p.end()
    return pm


class SeccionPersonalizar(QFrame):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.gestor = getattr(ctx, "premium", None)
        self.setObjectName("caja")
        g = self.gestor
        self.sel = {"marco": g.marco if g else NINGUNO, "efecto": g.efecto if g else NINGUNO,
                    "tema": g.tema if g else NINGUNO}
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(12)

        cab = QHBoxLayout()
        t = QLabel("Personalizar")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.estado = QLabel("")
        self.estado.setObjectName("secundario")
        cab.addWidget(self.estado)
        v.addLayout(cab)
        ayuda = QLabel("Un marco animado para tu foto, un efecto para tu nombre y un tema de colores propio. "
                       "Lo ven también tus amigos.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)

        # bloqueo amable para quien aún no es donador
        self.caja_bloqueo = QWidget()
        h = QHBoxLayout(self.caja_bloqueo)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.aviso = QLabel("🔒 Exclusivo para donadores. Puedes probar cómo queda; para aplicarlo, apoya a "
                            "Caudal o canjea un código de prueba.")
        self.aviso.setObjectName("ayuda")
        self.aviso.setWordWrap(True)
        h.addWidget(self.aviso, 1)
        self.bt_donar = boton_donar(texto="Donar aquí")
        h.addWidget(self.bt_donar)
        self.bt_codigo = boton_codigo(ctx, texto="Tengo un código de prueba")
        h.addWidget(self.bt_codigo)
        v.addWidget(self.caja_bloqueo)

        # vista previa en vivo
        prev = QFrame()
        prev.setStyleSheet(f"QFrame{{background:{C['superficie']};border-radius:14px;}}")
        ph = QHBoxLayout(prev)
        ph.setContentsMargins(16, 14, 16, 14)
        ph.setSpacing(16)
        cuenta = getattr(ctx, "cuenta", None) or {}
        nombre = (cuenta.get("nombre") or cuenta.get("usuario") or "Tu nombre")
        self.avatar = PC.Avatar(88, nombre, None, None, marco=self.sel["marco"], marco_siempre=True)
        ph.addWidget(self.avatar, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.nombre = NombreEfecto(nombre, self.sel["efecto"], "font-size:24px;font-weight:900;", siempre=True)
        col.addStretch(1)
        col.addWidget(self.nombre)
        usuario = QLabel("@" + str(cuenta.get("usuario") or "tu_usuario"))
        usuario.setObjectName("secundario")
        usuario.setStyleSheet("background:transparent;")
        col.addWidget(usuario)
        col.addStretch(1)
        ph.addLayout(col, 1)
        self.muestra = Muestra()
        self.muestra.setMinimumSize(190, 118)
        self.muestra.setMaximumSize(230, 140)
        ph.addWidget(self.muestra, 0, Qt.AlignVCenter)
        v.addWidget(prev)

        self.botones = {"marco": {}, "efecto": {}, "tema": {}}
        self._rejilla(v, "Marco de la foto", "marco", MARCOS, NOMBRES_MARCO, lambda k: QIcon(icono_marco(k)),
                      QSize(44, 44))
        self._rejilla(v, "Efecto del nombre", "efecto", EFECTOS, NOMBRES_EFECTO, None, QSize(1, 1))
        self._rejilla(v, "Tema de colores", "tema", TEMAS, NOMBRES_TEMA, lambda k: QIcon(icono_tema(k)),
                      QSize(64, 40))

        fila = QHBoxLayout()
        self.bt_aplicar = QPushButton("Aplicar")
        self.bt_aplicar.clicked.connect(self._aplicar)
        fila.addWidget(self.bt_aplicar)
        self.bt_quitar = QPushButton("Quitar todo")
        self.bt_quitar.setObjectName("contorno")
        self.bt_quitar.clicked.connect(self._quitar_todo)
        fila.addWidget(self.bt_quitar)
        self.msg = QLabel("")
        self.msg.setObjectName("secundario")
        self.msg.setWordWrap(True)
        fila.addWidget(self.msg, 1)
        v.addLayout(fila)

        if g is not None:
            g.cambiado.connect(self.refrescar)
        self._marcar()
        self.refrescar()

    # ------------------------------------------------------------ rejillas
    def _rejilla(self, v, titulo, clave, valores, nombres, icono, tam):
        et = QLabel(titulo)
        et.setStyleSheet("font-size:13px;font-weight:800;")
        v.addWidget(et)
        rej = QGridLayout()
        rej.setSpacing(8)
        for i, valor in enumerate(valores):
            b = QToolButton()
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon if icono else Qt.ToolButtonTextOnly)
            b.setText(nombres[valor])
            b.setToolTip(nombres[valor])
            b.setAccessibleName(f"{titulo}: {nombres[valor]}")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumSize(96, 78 if icono else 40)
            if icono is not None:
                b.setIcon(icono(valor))
                b.setIconSize(tam)
            b.setStyleSheet(
                f"QToolButton{{background:rgba(255,255,255,0.05);border:2px solid transparent;border-radius:12px;"
                f"color:{C['texto']};font-size:11.5px;padding:4px 2px;}}"
                f"QToolButton:hover{{background:rgba(255,255,255,0.10);}}"
                f"QToolButton:checked{{border:2px solid {C['acento']};background:rgba(255,255,255,0.12);}}")
            b.clicked.connect(lambda _=False, c=clave, val=valor: self._elegir(c, val))
            self.botones[clave][valor] = b
            rej.addWidget(b, i // COLUMNAS, i % COLUMNAS)
        for c in range(COLUMNAS):
            rej.setColumnStretch(c, 1)
        v.addLayout(rej)

    def _elegir(self, clave, valor):
        self.sel[clave] = valor
        self.msg.setText("")
        self._marcar()

    def _marcar(self):
        """Pinta lo elegido: marca los botones y mueve la vista previa."""
        for clave, d in self.botones.items():
            for valor, b in d.items():
                b.setChecked(valor == self.sel[clave])
        self.avatar.set_marco(self.sel["marco"])
        self.nombre.set_efecto(self.sel["efecto"])
        t = self.sel["tema"]
        if t == NINGUNO:
            self.muestra.poner(ACTUAL.get("acento", "cian") if not str(ACTUAL.get("acento", "")).startswith("premium_")
                               else "cian",
                               ACTUAL.get("fondo", "oscuro") if not str(ACTUAL.get("fondo", "")).startswith("premium_")
                               else "oscuro")
        else:
            self.muestra.poner("premium_" + t, "premium_" + t)

    # ------------------------------------------------------------ estado
    def refrescar(self):
        g = self.gestor
        premium = bool(g and g.premium)
        self.caja_bloqueo.setVisible(not premium)
        self.bt_aplicar.setEnabled(premium)
        self.bt_quitar.setEnabled(premium)
        if not premium:
            self.estado.setText("🔒 Exclusivo")
        elif g.tipo == "prueba":
            self.estado.setText(texto_vencimiento(g.dias_de_prueba()))
        else:
            self.estado.setText("Fundador de Caudal" if g.tipo == "fundador" else "Donador de Caudal")

    def _aplicar(self):
        g = self.gestor
        if g is None or not g.premium:
            return
        cambia_tema = g.guardar_personalizacion(self.sel["marco"], self.sel["efecto"], self.sel["tema"],
                                                alerta=self._alerta)
        self.msg.setText("Guardado. Así te ve la gente.")
        if cambia_tema:
            ventana = self.ctx.ventana if getattr(self.ctx, "ventana", None) is not None else None
            if ventana is not None and hasattr(ventana, "reabrir_con_aspecto"):
                ventana.reabrir_con_aspecto()

    def _alerta(self, texto):
        self.msg.setText(texto)

    def _quitar_todo(self):
        self.sel = {"marco": NINGUNO, "efecto": NINGUNO, "tema": NINGUNO}
        self._marcar()
        self._aplicar()
