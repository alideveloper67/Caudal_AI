# -*- coding: utf-8 -*-
"""Ventanas de los términos, los datos básicos y la privacidad (escritorio)."""

import calendar
from datetime import date

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout,
                               QWidget)

from .. import legal
from . import iconos
from .estilos import C, hoja

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


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
    """Fecha de nacimiento, país, género y el permiso del tutor (si es menor).

    La fecha son tres listas (día, mes, año): el campo de fecha de Qt salía en
    blanco y obligaba a ir mes a mes por el calendario. Al elegir el día se
    abre el mes, y al elegir el mes, el año; el día nunca puede quedar
    imposible (31 de febrero) y debajo se confirma la edad que resulta."""
    cambio = Signal()

    def __init__(self, padre=None, perfil=None):
        super().__init__(padre)
        perfil = perfil or {}
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(5)
        v.addWidget(self._etiqueta("Fecha de nacimiento"))
        fecha = QHBoxLayout()
        fecha.setSpacing(8)
        nac = perfil.get("nacimiento")
        self.dia = self._lista("Día", [(str(i), i) for i in range(1, 32)])
        self.mes = self._lista("Mes", [(m.capitalize(), i) for i, m in enumerate(MESES, 1)])
        hoy = date.today().year
        self.anio = self._lista("Año", [(str(a), a) for a in range(hoy, hoy - 101, -1)])
        self.anio.setToolTip("Escribe el año con el teclado para saltar a él (por ejemplo 1998)")
        for c, estira in ((self.dia, 2), (self.mes, 4), (self.anio, 3)):
            fecha.addWidget(c, estira)
        v.addLayout(fecha)
        if nac:
            self.anio.setCurrentIndex(max(0, self.anio.findData(nac.year)))
            self.mes.setCurrentIndex(max(0, self.mes.findData(nac.month)))
            self._ajustar_dias()
            self.dia.setCurrentIndex(max(0, self.dia.findData(nac.day)))
        # el siguiente se abre solo: tres clics y listo
        self.dia.activated.connect(lambda _i: self._siguiente(self.dia, self.mes))
        self.dia.activated.connect(lambda _i: setattr(self, "_dia_querido", self.dia.currentData()))
        self.mes.activated.connect(lambda _i: self._siguiente(self.mes, self.anio))
        for c in (self.dia, self.mes, self.anio):
            c.currentIndexChanged.connect(self._al_cambiar)
        self.edad = QLabel("")
        self.edad.setObjectName("ayuda")
        self.edad.setWordWrap(True)
        v.addWidget(self.edad)

        v.addSpacing(6)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        col_p = QVBoxLayout()
        col_p.setSpacing(5)
        col_p.addWidget(self._etiqueta("País"))
        self.pais = self._lista(None, [(n, k) for k, n in legal.PAISES.items()])
        self.pais.setCurrentIndex(max(0, self.pais.findData(perfil.get("pais") or "PE")))
        col_p.addWidget(self.pais)
        fila.addLayout(col_p, 1)
        col_g = QVBoxLayout()
        col_g.setSpacing(5)
        col_g.addWidget(self._etiqueta("Género (opcional)"))
        self.genero = self._lista("Prefiero no elegir", [(n, k) for k, n in legal.GENEROS.items()], vacio="")
        self.genero.setCurrentIndex(max(0, self.genero.findData(perfil.get("genero") or "")))
        col_g.addWidget(self.genero)
        fila.addLayout(col_g, 1)
        v.addLayout(fila)
        self.tutor = QCheckBox("Soy la madre, el padre o el tutor y doy permiso para que use Caudal")
        self.tutor.setCursor(Qt.PointingHandCursor)
        self.tutor.hide()
        self.tutor.toggled.connect(lambda _v: self.cambio.emit())
        v.addSpacing(4)
        v.addWidget(self.tutor)
        self._al_cambiar()

    # ------------------------------------------------------------ piezas
    def _etiqueta(self, texto):
        et = QLabel(texto)
        et.setStyleSheet("font-size:13px;font-weight:700;")
        return et

    def _lista(self, vacio_texto, opciones, vacio=0):
        c = QComboBox()
        c.setMinimumHeight(42)
        c.setMinimumWidth(0)
        c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        c.setMinimumContentsLength(3)
        c.setMaxVisibleItems(12)
        c.setCursor(Qt.PointingHandCursor)
        c.setStyleSheet(f"QComboBox{{font-size:14px;border-radius:10px;padding:8px 12px;"
                        f"background:{C['superficie2']};border:1px solid {C['borde_claro']};}}"
                        f"QComboBox:focus{{border:2px solid {C['acento']};}}")
        if vacio_texto:
            c.addItem(vacio_texto, vacio)
        for texto, valor in opciones:
            c.addItem(texto, valor)
        return c

    def _siguiente(self, actual, siguiente):
        if actual.currentData() and not siguiente.currentData():
            siguiente.setFocus()
            QTimer.singleShot(60, siguiente.showPopup)

    def _ajustar_dias(self):
        """Los días que tiene ese mes (febrero de un año bisiesto incluido)."""
        m, a = self.mes.currentData(), self.anio.currentData()
        tope = calendar.monthrange(a or 2000, m)[1] if m else 31
        elegido = self.dia.currentData()
        if self.dia.count() - 1 == tope:
            return
        self.dia.blockSignals(True)
        while self.dia.count() - 1 > tope:
            self.dia.removeItem(self.dia.count() - 1)
        while self.dia.count() - 1 < tope:
            n = self.dia.count()
            self.dia.addItem(str(n), n)
        querido = getattr(self, "_dia_querido", 0) or elegido   # el 31 vuelve al salir de febrero
        if querido:
            self.dia.setCurrentIndex(min(querido, tope))
        self.dia.blockSignals(False)

    # ------------------------------------------------------------ valores
    def nacimiento(self):
        d, m, a = self.dia.currentData(), self.mes.currentData(), self.anio.currentData()
        if not (d and m and a):
            return None
        return date(a, m, min(d, calendar.monthrange(a, m)[1]))

    def _al_cambiar(self, *_):
        self._ajustar_dias()
        n = self.nacimiento()
        if n is None:
            faltan = [t for t, c in (("el día", self.dia), ("el mes", self.mes), ("el año", self.anio))
                      if not c.currentData()]
            self.edad.setStyleSheet("")
            if len(faltan) == 3:
                self.edad.setText("Solo la usamos para comprobar tu edad. No se muestra a nadie.")
            else:
                self.edad.setText("Falta elegir " + " y ".join(faltan) + ".")
            self.tutor.hide()
        else:
            e = legal.edad(n)
            menor = e < legal.EDAD_MINIMA
            self.edad.setStyleSheet(f"color:{C['aviso'] if menor else C['exito']};font-weight:600;")
            self.edad.setText(f"{n.day} de {MESES[n.month - 1]} de {n.year} · tienes {e} años"
                              + (f". Al ser menor de {legal.EDAD_MINIMA}, una persona adulta "
                                 "responsable tiene que dar su permiso aquí abajo." if menor else " ✓"))
            self.tutor.setVisible(menor)
        self.cambio.emit()

    def valores(self):
        return {"nacimiento": self.nacimiento(), "pais": self.pais.currentData(),
                "genero": self.genero.currentData() or None,
                "permiso_tutor": self.tutor.isChecked() and not self.tutor.isHidden()}


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
