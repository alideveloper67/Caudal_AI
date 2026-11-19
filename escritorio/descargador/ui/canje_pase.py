# -*- coding: utf-8 -*-
"""«Tengo un código»: canjear un pase de prueba (7 días de beneficios de donador).

Se abre desde Personalizar, desde el cuadro de donar y desde Ajustes. El código tiene la forma
XXXX-XXXX; aquí se escribe en mayúsculas y con su guion solo. Todo va en segundo plano."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from ..premium_datos import codigo_completo, limpiar_codigo


class DialogoCanje(QDialog):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.canjeado = False
        self.setWindowTitle("Tengo un código")
        self.setMinimumWidth(400)
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 18)
        v.setSpacing(10)
        t = QLabel("Canjea tu código de prueba")
        t.setObjectName("titulo_seccion")
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        s = QLabel("Un amigo te pasó un código. Con él tienes 7 días de beneficios de donador: marcos animados, "
                   "efectos en tu nombre, temas de colores, fondo propio y más.")
        s.setObjectName("secundario")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignCenter)
        v.addWidget(s)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("XXXX-XXXX")
        self.campo.setMaxLength(9)
        self.campo.setAlignment(Qt.AlignCenter)
        self.campo.setStyleSheet("font-size:20px;font-weight:800;letter-spacing:2px;padding:8px;")
        self.campo.setAccessibleName("Código de prueba")
        self.campo.textEdited.connect(self._al_escribir)
        self.campo.returnPressed.connect(self._canjear)
        v.addWidget(self.campo)
        self.estado = QLabel("")
        self.estado.setObjectName("secundario")
        self.estado.setWordWrap(True)
        self.estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.estado)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_canjear = QPushButton("Canjear")
        self.bt_canjear.setEnabled(False)
        self.bt_canjear.clicked.connect(self._canjear)
        fila.addWidget(self.bt_canjear)
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("contorno")
        cerrar.clicked.connect(self.reject)
        fila.addWidget(cerrar)
        fila.addStretch(1)
        v.addLayout(fila)

    def _al_escribir(self, texto):
        limpio = limpiar_codigo(texto)
        if limpio != texto:
            self.campo.setText(limpio)
        self.bt_canjear.setEnabled(codigo_completo(limpio))
        self.estado.setText("")

    def _canjear(self):
        codigo = limpiar_codigo(self.campo.text())
        if not codigo_completo(codigo) or not self.bt_canjear.isEnabled():
            return
        gestor = getattr(self.ctx, "premium", None)
        if gestor is None:
            self.estado.setText("Inicia sesión para canjear un código.")
            return
        self.bt_canjear.setEnabled(False)
        self.campo.setEnabled(False)
        self.estado.setText("Comprobando el código…")
        gestor.canjear(codigo, ok=self._listo, error=self._fallo)

    def _listo(self, res):
        self.campo.setEnabled(True)
        if res.get("ok"):
            self.canjeado = True
            dias = res.get("dias")
            self.estado.setText(res.get("mensaje") or
                                f"¡Listo! Tienes {dias or 7} días de beneficios de donador.")
            self.bt_canjear.setVisible(False)
            self.campo.setEnabled(False)
            QTimer.singleShot(1600, self.accept)
        else:
            self.estado.setText(res.get("mensaje") or "Ese código no sirve. Revisa que esté bien escrito.")
            self.bt_canjear.setEnabled(codigo_completo(self.campo.text()))

    def _fallo(self, e):
        self.campo.setEnabled(True)
        from .. import social as S
        self.estado.setText(S.explicar(e, "comprobar el código"))
        self.bt_canjear.setEnabled(codigo_completo(self.campo.text()))


def abrir_canje(ctx, padre=None):
    """Abre el cuadro de canje. Devuelve True si se canjeó un código."""
    d = DialogoCanje(ctx, padre)
    d.exec()
    return d.canjeado


def boton_codigo(ctx, padre=None, texto="Tengo un código de prueba"):
    """El botón discreto «Tengo un código» (para Personalizar y el cuadro de donar)."""
    b = QPushButton(texto)
    b.setObjectName("contorno")
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(lambda: abrir_canje(ctx, b.window()))
    return b
