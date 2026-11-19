# -*- coding: utf-8 -*-
"""Aviso único para donadores y fundadores: «Ahora puedes regalar códigos de prueba a tus amigos».

Sale la primera vez que un donador abre Caudal después de actualizar (se recuerda en el ajuste
«aviso_regalo_visto») y su botón lleva a la tarjeta «Regala una prueba a tus amigos» de Ajustes."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

CLAVE_AJUSTE = "aviso_regalo_visto"


class AvisoRegalo(QDialog):
    ir_a_regalar = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Regala una prueba")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 18)
        v.setSpacing(10)
        t = QLabel("Ahora puedes regalar códigos de prueba a tus amigos")
        t.setObjectName("titulo_seccion")
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        s = QLabel("Gracias por apoyar a Caudal. Crea un código y pásaselo a un amigo: tendrá 7 días con todos "
                   "los beneficios de donador. Lo creas, lo copias o lo anulas desde Ajustes.")
        s.setObjectName("secundario")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(s)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_ir = QPushButton("Ir a regalar")
        self.bt_ir.setCursor(Qt.PointingHandCursor)
        self.bt_ir.clicked.connect(self._ir)
        fila.addWidget(self.bt_ir)
        self.bt_luego = QPushButton("Ahora no")
        self.bt_luego.setObjectName("contorno")
        self.bt_luego.setCursor(Qt.PointingHandCursor)
        self.bt_luego.clicked.connect(self.reject)
        fila.addWidget(self.bt_luego)
        fila.addStretch(1)
        v.addLayout(fila)

    def _ir(self):
        self.ir_a_regalar.emit()          # antes de cerrar: al cerrarse el diálogo se borra
        self.accept()


def debe_mostrarse(ajustes, gestor):
    """True si es donador o fundador (no solo prueba) y aún no se le avisó."""
    return bool(gestor is not None and gestor.puede_regalar and not ajustes[CLAVE_AJUSTE])


def mostrar_si_toca(ventana):
    """Abre el aviso si toca y queda anotado al abrirse (un cierre brusco no lo repite). Devuelve el
    diálogo o None. No bloquea."""
    ajustes = ventana.ajustes
    if not debe_mostrarse(ajustes, getattr(ventana, "premium", None)):
        return None
    ajustes[CLAVE_AJUSTE] = True
    ajustes.guardar()
    d = AvisoRegalo(ventana)
    d.setAttribute(Qt.WA_DeleteOnClose, True)
    d.ir_a_regalar.connect(ventana.ir_a_regalo)
    d.open()
    return d
