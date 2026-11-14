# -*- coding: utf-8 -*-
"""Ventanas de los términos, los datos básicos y la privacidad (escritorio)."""

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout,
                               QWidget)

from .. import legal
from . import iconos
from .estilos import C, hoja


def _estilo(w):
    w.setObjectName("raiz")
    w.setAttribute(Qt.WA_StyledBackground, True)
    w.setStyleSheet(hoja(iconos.flechas_qss()))


class VentanaLegal(QDialog):
    def __init__(self, nombre, padre=None):
        super().__init__(padre)
        _estilo(self)
        self.setWindowTitle("Términos y condiciones" if nombre == "terminos" else "Política de privacidad")
        self.resize(760, 720)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        t = QTextBrowser()
        t.setOpenExternalLinks(True)
        t.setMarkdown(legal.texto(nombre))
        t.setStyleSheet(f"QTextBrowser{{background:{C['panel']};border:none;border-radius:12px;"
                        f"padding:16px;font-size:14px;color:{C['texto2']};}}")
        v.addWidget(t, 1)
        b = QPushButton("Cerrar")
        b.setObjectName("principal")
        b.clicked.connect(self.accept)
        v.addWidget(b, 0, Qt.AlignRight)


def abrir_legal(nombre, padre=None):
    VentanaLegal(nombre, padre).exec()


class CamposPerfil(QWidget):
    """Fecha de nacimiento, país, género y el permiso del tutor (si es menor)."""
    cambio = Signal()

    def __init__(self, padre=None, perfil=None):
        super().__init__(padre)
        perfil = perfil or {}
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        fila = QHBoxLayout()
        col1 = QVBoxLayout()
        et = QLabel("Fecha de nacimiento")
        et.setObjectName("ayuda")
        col1.addWidget(et)
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd/MM/yyyy")
        self.fecha.setMinimumDate(QDate(1900, 1, 1))
        self.fecha.setMaximumDate(QDate.currentDate())
        self.fecha.setSpecialValueText("Elegir")
        nac = perfil.get("nacimiento")
        self.fecha.setDate(QDate(nac.year, nac.month, nac.day) if nac else self.fecha.minimumDate())
        self.fecha.dateChanged.connect(self._al_cambiar)
        col1.addWidget(self.fecha)
        fila.addLayout(col1, 1)
        col2 = QVBoxLayout()
        et2 = QLabel("País")
        et2.setObjectName("ayuda")
        col2.addWidget(et2)
        self.pais = QComboBox()
        for k, n in legal.PAISES.items():
            self.pais.addItem(n, k)
        i = self.pais.findData(perfil.get("pais") or "PE")
        self.pais.setCurrentIndex(max(0, i))
        col2.addWidget(self.pais)
        fila.addLayout(col2, 1)
        v.addLayout(fila)
        et3 = QLabel("Género (opcional)")
        et3.setObjectName("ayuda")
        v.addWidget(et3)
        self.genero = QComboBox()
        self.genero.addItem("Elegir (opcional)", "")
        for k, n in legal.GENEROS.items():
            self.genero.addItem(n, k)
        self.genero.setCurrentIndex(max(0, self.genero.findData(perfil.get("genero") or "")))
        v.addWidget(self.genero)
        self.tutor = QCheckBox("Soy la madre, el padre o el tutor y doy permiso para que use Caudal")
        self.tutor.hide()
        v.addWidget(self.tutor)

    def nacimiento(self):
        d = self.fecha.date()
        if d == self.fecha.minimumDate():
            return None
        return date(d.year(), d.month(), d.day())

    def _al_cambiar(self, *_):
        n = self.nacimiento()
        self.tutor.setVisible(n is not None and legal.edad(n) < legal.EDAD_MINIMA)
        self.cambio.emit()

    def valores(self):
        return {"nacimiento": self.nacimiento(), "pais": self.pais.currentData(),
                "genero": self.genero.currentData() or None, "permiso_tutor": self.tutor.isChecked()}


class CasillasLegales(QWidget):
    """La casilla obligatoria de los términos y la opcional de los datos anónimos."""

    def __init__(self, padre=None, comparte=False):
        super().__init__(padre)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        fila = QHBoxLayout()
        self.acepta = QCheckBox()
        fila.addWidget(self.acepta, 0, Qt.AlignTop)
        t = QLabel(f'He leído y acepto los <a href="terminos" style="color:{C["acento"]}">Términos y condiciones</a> '
                   f'y la <a href="privacidad" style="color:{C["acento"]}">Política de privacidad</a>.')
        t.setWordWrap(True)
        t.setTextInteractionFlags(Qt.TextBrowserInteraction)
        t.linkActivated.connect(lambda n: abrir_legal(n, self))
        fila.addWidget(t, 1)
        v.addLayout(fila)
        self.comparte = QCheckBox("Compartir mis datos de uso anónimos (opcional)")
        self.comparte.setChecked(comparte)
        v.addWidget(self.comparte)
        nota = QLabel("Qué música se escucha y cuánto, en estadísticas de grupos grandes, sin tu nombre. "
                      "Lo puedes quitar cuando quieras.")
        nota.setWordWrap(True)
        nota.setObjectName("ayuda")
        v.addWidget(nota)


class DialogoAceptar(QDialog):
    """Para cuentas de antes de los términos (o con datos básicos sin poner)."""

    def __init__(self, sesion, perfil, padre=None):
        super().__init__(padre)
        _estilo(self)
        self.sesion = sesion
        self.perfil = perfil
        self.setWindowTitle("Caudal")
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 24, 28, 22)
        v.setSpacing(10)
        t = QLabel("Antes de seguir" if not perfil.get("version") else "Hemos actualizado nuestros términos")
        t.setStyleSheet("font-size:24px;font-weight:900;")
        v.addWidget(t)
        falta = not legal.completo(perfil)
        d = QLabel("Necesitamos unos datos básicos para comprobar tu edad, y que aceptes los términos y "
                   "la política de privacidad. Solo te lo pedimos una vez." if falta
                   else "Léelos y acéptalos para seguir usando Caudal.")
        d.setWordWrap(True)
        d.setObjectName("secundario")
        v.addWidget(d)
        self.nombre = QLineEdit(perfil.get("nombre") or "")
        self.nombre.setPlaceholderText("Tu nombre y apellido")
        self.campos = CamposPerfil(self, perfil)
        if falta:
            v.addWidget(self.nombre)
            v.addWidget(self.campos)
        self.casillas = CasillasLegales(self, perfil.get("comparte", False))
        v.addWidget(self.casillas)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setStyleSheet(f"color:{C['error']};font-weight:600;")
        self.error.hide()
        v.addWidget(self.error)
        fila = QHBoxLayout()
        salir = QPushButton("Cerrar sesión")
        salir.setObjectName("contorno")
        salir.clicked.connect(self.reject)
        fila.addWidget(salir)
        fila.addStretch(1)
        ok = QPushButton("Aceptar y continuar")
        ok.setObjectName("principal")
        ok.clicked.connect(self._continuar)
        fila.addWidget(ok)
        v.addLayout(fila)
        self.falta = falta

    def _continuar(self):
        if not self.casillas.acepta.isChecked():
            return self._mal("Para seguir usando Caudal tienes que aceptar los términos.")
        try:
            if self.falta:
                x = self.campos.valores()
                e = legal.revisar_perfil(self.nombre.text(), x["nacimiento"], x["pais"], x["permiso_tutor"])
                if e:
                    return self._mal(e)
                legal.completar(self.sesion, self.nombre.text(), x["nacimiento"], x["pais"], x["genero"],
                                x["permiso_tutor"])
            legal.aceptar(self.sesion, self.casillas.comparte.isChecked())
        except Exception:  # noqa: BLE001
            return self._mal("No se pudo guardar. Revisa tu internet.")
        self.accept()

    def _mal(self, texto):
        self.error.setText(texto)
        self.error.show()


class DialogoPrivacidad(QDialog):
    """Tus datos, el permiso de los datos anónimos, los textos y borrar la cuenta."""
    cuenta_eliminada = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        _estilo(self)
        self.ctx = ctx
        cuenta = getattr(ctx, "cuenta", None) or {}
        self.sesion = cuenta.get("sesion")
        self.usuario = cuenta.get("usuario") or ""
        self.setWindowTitle("Privacidad · Caudal")
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(10)
        t = QLabel("Tus datos y privacidad")
        t.setStyleSheet("font-size:22px;font-weight:900;")
        v.addWidget(t)
        try:
            self.perfil = legal.perfil(self.sesion)
        except Exception:  # noqa: BLE001
            self.perfil = None
        if self.perfil is None:
            e = QLabel("Sin conexión: vuelve cuando tengas internet.")
            e.setStyleSheet(f"color:{C['error']};")
            v.addWidget(e)
            return
        sub = QLabel("Tu nombre, tu edad y tu país (los puedes corregir)")
        sub.setObjectName("titulo_seccion")
        v.addWidget(sub)
        self.nombre = QLineEdit(self.perfil.get("nombre") or "")
        v.addWidget(self.nombre)
        self.campos = CamposPerfil(self, self.perfil)
        v.addWidget(self.campos)
        guardar = QPushButton("Guardar mis datos")
        guardar.setObjectName("contorno")
        guardar.clicked.connect(self._guardar)
        v.addWidget(guardar, 0, Qt.AlignLeft)
        self.comparte = QCheckBox("Compartir mis datos de uso anónimos (opcional)")
        self.comparte.setChecked(self.perfil.get("comparte", False))
        self.comparte.toggled.connect(self._compartir)
        v.addWidget(self.comparte)
        nota = QLabel("Estadísticas de grupos grandes (qué música se escucha y cuánto), sin tu nombre ni nada "
                      "que te identifique.")
        nota.setWordWrap(True)
        nota.setObjectName("ayuda")
        v.addWidget(nota)
        fila = QHBoxLayout()
        for texto, nombre in (("Términos y condiciones", "terminos"), ("Política de privacidad", "privacidad")):
            b = QPushButton(texto)
            b.setObjectName("contorno")
            b.clicked.connect(lambda _=False, n=nombre: abrir_legal(n, self))
            fila.addWidget(b)
        fila.addStretch(1)
        v.addLayout(fila)
        v.addSpacing(10)
        borrar = QPushButton("Eliminar mi cuenta")
        borrar.setObjectName("peligro")
        borrar.clicked.connect(self._eliminar)
        v.addWidget(borrar, 0, Qt.AlignLeft)
        aviso = QLabel("Se borra tu cuenta y todo lo que guarda. No se puede deshacer.")
        aviso.setObjectName("ayuda")
        v.addWidget(aviso)

    def _guardar(self):
        x = self.campos.valores()
        e = legal.revisar_perfil(self.nombre.text(), x["nacimiento"], x["pais"], x["permiso_tutor"])
        if e:
            QMessageBox.warning(self, "Caudal", e)
            return
        try:
            legal.completar(self.sesion, self.nombre.text(), x["nacimiento"], x["pais"], x["genero"],
                            x["permiso_tutor"])
            self.ctx.aviso.emit("Datos guardados")
        except Exception:  # noqa: BLE001
            QMessageBox.warning(self, "Caudal", "No se pudo guardar. Revisa tu internet.")

    def _compartir(self, si):
        try:
            legal.compartir(self.sesion, si)
            self.ctx.aviso.emit("Gracias: tus datos anónimos ayudan a entender la música." if si
                                else "Listo: tus datos ya no entran en las estadísticas.")
        except Exception:  # noqa: BLE001
            QMessageBox.warning(self, "Caudal", "No se pudo guardar. Revisa tu internet.")

    def _eliminar(self):
        escrito, ok = QInputDialog.getText(
            self, "Eliminar mi cuenta",
            f"Para borrar tu cuenta y TODOS tus datos para siempre, escribe tu usuario: {self.usuario}")
        if not ok:
            return
        if escrito.strip().lstrip("@").lower() != self.usuario.lower():
            QMessageBox.information(self, "Caudal", "El usuario no coincide. No se ha borrado nada.")
            return
        try:
            legal.eliminar_cuenta(self.sesion)
        except Exception:  # noqa: BLE001
            QMessageBox.warning(self, "Caudal", "No se pudo borrar. Revisa tu internet.")
            return
        self.accept()
        self.cuenta_eliminada.emit()
