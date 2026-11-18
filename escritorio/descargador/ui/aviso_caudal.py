# -*- coding: utf-8 -*-
"""El cuadro de un aviso de Caudal (ver descargador/avisos.py): título, texto y, si lleva, un botón
que abre su enlace. Al cerrarlo el aviso queda como visto."""

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import avisos


class DialogoAviso(QDialog):
    def __init__(self, aviso, padre=None):
        super().__init__(padre)
        self.aviso = aviso
        self.setWindowTitle("Aviso de Caudal")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 18)
        v.setSpacing(10)
        t = QLabel(aviso["titulo"])
        t.setObjectName("titulo_seccion")
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        s = QLabel(aviso["texto"])
        s.setObjectName("secundario")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(s)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_enlace = None
        if aviso.get("enlace"):
            self.bt_enlace = QPushButton(aviso.get("etiqueta") or "Abrir")
            self.bt_enlace.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(aviso["enlace"])))
            fila.addWidget(self.bt_enlace)
        self.bt_ok = QPushButton("Entendido")
        self.bt_ok.setObjectName("contorno")
        self.bt_ok.setDefault(True)
        self.bt_ok.clicked.connect(self.accept)
        fila.addWidget(self.bt_ok)
        fila.addStretch(1)
        v.addLayout(fila)

    def done(self, resultado):
        avisos.marcar_visto(self.aviso["id"])
        super().done(resultado)


def mostrar_avisos(lista, padre=None):
    """Uno tras otro; cada uno se da por visto al cerrarlo."""
    for a in lista:
        DialogoAviso(a, padre).exec()
