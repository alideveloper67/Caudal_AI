# -*- coding: utf-8 -*-
"""Donar a Caudal con Yape (igual que app/lib/ui/paginas/donar.dart).

Un botón discreto en Ajustes y en las funciones exclusivas de donadores abre este cuadro: el QR de
Yape y cómo mandar la captura del pago para que se compruebe. El QR es `descargador/donar/yape_qr.png`;
para cambiarlo basta reemplazar ese archivo."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .estilos import C

NUMERO = "902464984"            # al que se manda la captura del pago
ANCHO_QR = 260


def ruta_qr():
    base = (Path(getattr(sys, "_MEIPASS", "")) / "descargador"
            if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent)
    return base / "donar" / "yape_qr.png"


class DialogoDonar(QDialog):
    def __init__(self, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Apoya a Caudal")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 18)
        v.setSpacing(10)
        t = QLabel("Apoya a Caudal con Yape")
        t.setObjectName("titulo_seccion")
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        s = QLabel("Caudal es gratis. Si lo apoyas, tu cuenta pasa a ser «Donador de Caudal»: fondo propio "
                   "en toda la app, GIF en tu perfil, una mascotita en la barra de la canción, marcos animados "
                   "y efectos para tu nombre, temas de colores y tarjetas de letra exclusivas.")
        s.setObjectName("secundario")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(s)

        self.qr = QLabel()
        self.qr.setFixedWidth(ANCHO_QR + 20)
        self.qr.setAlignment(Qt.AlignCenter)
        self.qr.setStyleSheet("background:#FFFFFF;border-radius:16px;color:#555555;")
        pm = QPixmap(str(ruta_qr()))
        if pm.isNull():
            self.qr.setText("El QR de Yape aún no está disponible.")
            self.qr.setFixedHeight(ANCHO_QR)
            self.qr.setWordWrap(True)
        else:
            chico = pm.scaledToWidth(ANCHO_QR, Qt.SmoothTransformation)
            self.qr.setPixmap(chico)
            self.qr.setFixedSize(ANCHO_QR + 20, chico.height() + 20)
        v.addWidget(self.qr, 0, Qt.AlignHCenter)

        c = QLabel(f"Escanea el QR o yapea al {NUMERO}")
        c.setStyleSheet("font-size:14px;font-weight:700;")
        c.setAlignment(Qt.AlignCenter)
        v.addWidget(c)
        p = QLabel("Después envía la captura del pago por WhatsApp a ese mismo número, con tu usuario de Caudal. "
                   "La comprobamos y activamos tus beneficios.")
        p.setObjectName("secundario")
        p.setWordWrap(True)
        p.setAlignment(Qt.AlignCenter)
        v.addWidget(p)

        fila = QHBoxLayout()
        fila.setSpacing(8)
        fila.addStretch(1)
        self.bt_whatsapp = QPushButton("Enviar captura por WhatsApp")
        self.bt_whatsapp.clicked.connect(self._whatsapp)
        fila.addWidget(self.bt_whatsapp)
        self.bt_copiar = QPushButton(f"Copiar {NUMERO}")
        self.bt_copiar.setObjectName("contorno")
        self.bt_copiar.clicked.connect(self._copiar)
        fila.addWidget(self.bt_copiar)
        fila.addStretch(1)
        v.addLayout(fila)
        self.estado = QLabel("")
        self.estado.setObjectName("secundario")
        self.estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.estado)
        # ¿un amigo te pasó un código de prueba? (solo si hay una sesión desde la que canjearlo)
        ctx = getattr(padre.window(), "ctx", None) if padre is not None else None
        if ctx is not None and getattr(ctx, "premium", None) is not None:
            from .canje_pase import abrir_canje
            self.bt_codigo = QPushButton("Tengo un código de prueba")
            self.bt_codigo.setObjectName("contorno")
            self.bt_codigo.setCursor(Qt.PointingHandCursor)
            self.bt_codigo.clicked.connect(lambda: abrir_canje(ctx, self) and self.accept())
            v.addWidget(self.bt_codigo, 0, Qt.AlignHCenter)
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("contorno")
        cerrar.clicked.connect(self.accept)
        v.addWidget(cerrar, 0, Qt.AlignHCenter)

    def _copiar(self):
        QGuiApplication.clipboard().setText(NUMERO)
        self.estado.setText("Número copiado")

    def _whatsapp(self):
        if not QDesktopServices.openUrl(QUrl(f"https://wa.me/51{NUMERO}")):
            self.estado.setText(f"No pude abrir WhatsApp. Escribe al {NUMERO}.")


def abrir_donar(padre=None):
    DialogoDonar(padre).exec()


def boton_donar(padre=None, texto="Donar aquí"):
    """El botón discreto para las funciones exclusivas."""
    b = QPushButton(texto)
    b.setObjectName("contorno")
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(lambda: abrir_donar(b.window()))
    return b
