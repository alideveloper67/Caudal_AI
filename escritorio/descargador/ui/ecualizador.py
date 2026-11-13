# -*- coding: utf-8 -*-
"""Ecualizador, super volumen y velocidad.

Todo se oye al momento mientras mueves los controles, pero solo queda guardado
al pulsar «Guardar». Cancelar, Esc o cerrar la ventana dejan el sonido como
estaba al abrirla.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QVBoxLayout)

from ..reproduccion import FRECUENCIAS_EQ, NOMBRES_SUPER_VOLUMEN, PRESETS_EQ
from .estilos import C

CLAVES = ("ecualizador", "eq_bandas", "eq_preset", "normalizar", "super_volumen", "velocidad")


def _nombre_frecuencia(f):
    return f"{f // 1000}k" if f >= 1000 else str(f)


class DialogoEcualizador(QDialog):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.a = ctx.ajustes
        self.r = ctx.reproductor
        self.setWindowTitle("Sonido")
        self.setMinimumWidth(660)
        self._cargando = True
        # como estaba todo al abrir, para poder deshacer
        self.original = {k: (list(self.a[k]) if isinstance(self.a[k], list) else self.a[k])
                         for k in CLAVES}
        self.original_velocidad = self.r.velocidad
        self._guardado = False

        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 20)
        v.setSpacing(14)

        # ---------------- super volumen
        t = QLabel("Súper volumen")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        nota = QLabel("Sube mucho el volumen percibido sin que el sonido se rompa: un "
                      "limitador evita que la onda se recorte. Ideal para parlantes y fiestas.")
        nota.setObjectName("secundario")
        nota.setWordWrap(True)
        v.addWidget(nota)
        fila_sv = QHBoxLayout()
        fila_sv.setSpacing(8)
        self.grupo_sv = QButtonGroup(self)
        for nivel, nombre in NOMBRES_SUPER_VOLUMEN.items():
            b = QPushButton(nombre)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.grupo_sv.addButton(b, nivel)
            fila_sv.addWidget(b)
        fila_sv.addStretch(1)
        v.addLayout(fila_sv)
        boton = self.grupo_sv.button(int(self.a["super_volumen"] or 0))
        if boton:
            boton.setChecked(True)
        self.grupo_sv.idClicked.connect(lambda _i: self._aplicar())

        sep = QLabel("")
        sep.setObjectName("separador")
        sep.setFixedHeight(1)
        v.addWidget(sep)

        # ---------------- ecualizador
        cab = QHBoxLayout()
        t = QLabel("Ecualizador")
        t.setObjectName("titulo_seccion")
        cab.addWidget(t)
        cab.addStretch(1)
        self.activo = QCheckBox("Activado")
        self.activo.setChecked(bool(self.a["ecualizador"]))
        self.activo.setCursor(Qt.PointingHandCursor)
        self.activo.toggled.connect(self._aplicar)
        cab.addWidget(self.activo)
        v.addLayout(cab)

        fila = QHBoxLayout()
        et = QLabel("Ajuste")
        et.setObjectName("secundario")
        fila.addWidget(et)
        self.preset = QComboBox()
        for nombre in PRESETS_EQ:
            self.preset.addItem(nombre)
        self.preset.addItem("Personalizado")
        actual = self.a["eq_preset"] or "Plano"
        i = self.preset.findText(actual)
        self.preset.setCurrentIndex(i if i >= 0 else self.preset.count() - 1)
        self.preset.setFixedWidth(220)
        self.preset.currentTextChanged.connect(self._elegir_preset)
        fila.addWidget(self.preset)
        fila.addStretch(1)
        reset = QPushButton("Dejar plano")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(lambda: self.preset.setCurrentText("Plano"))
        fila.addWidget(reset)
        v.addLayout(fila)

        bandas = QHBoxLayout()
        bandas.setSpacing(6)
        self.deslizadores = []
        self.valores = []
        ganancias = list(self.a["eq_bandas"] or [0] * 10)[:10]
        ganancias += [0] * (10 - len(ganancias))
        for f, g in zip(FRECUENCIAS_EQ, ganancias):
            col = QVBoxLayout()
            col.setSpacing(6)
            val = QLabel(f"{int(g):+d}")
            val.setAlignment(Qt.AlignCenter)
            val.setObjectName("secundario")
            col.addWidget(val)
            s = QSlider(Qt.Vertical)
            s.setRange(-12, 12)
            s.setValue(int(g))
            s.setFixedHeight(170)
            s.setCursor(Qt.PointingHandCursor)
            s.valueChanged.connect(self._mover)
            col.addWidget(s, 0, Qt.AlignHCenter)
            nombre = QLabel(_nombre_frecuencia(f))
            nombre.setAlignment(Qt.AlignCenter)
            nombre.setObjectName("ayuda")
            col.addWidget(nombre)
            bandas.addLayout(col)
            self.deslizadores.append(s)
            self.valores.append(val)
        v.addLayout(bandas)
        nota = QLabel("Graves a la izquierda, agudos a la derecha (dB). Se oye al momento.")
        nota.setObjectName("ayuda")
        v.addWidget(nota)

        # ---------------- mas
        self.normalizar = QCheckBox("Normalizar el volumen entre canciones")
        self.normalizar.setChecked(bool(self.a["normalizar"]))
        self.normalizar.setCursor(Qt.PointingHandCursor)
        self.normalizar.toggled.connect(self._aplicar)
        v.addWidget(self.normalizar)
        fila_v = QHBoxLayout()
        et_v = QLabel("Velocidad")
        et_v.setObjectName("secundario")
        fila_v.addWidget(et_v)
        self.velocidad = QSlider(Qt.Horizontal)
        self.velocidad.setRange(25, 300)
        self.velocidad.setSingleStep(5)
        self.velocidad.setPageStep(25)
        self.velocidad.setValue(int(round(self.r.velocidad * 100)))
        self.velocidad.setFixedWidth(280)
        fila_v.addWidget(self.velocidad)
        self.et_vel = QLabel("")
        self.et_vel.setFixedWidth(60)
        fila_v.addWidget(self.et_vel)
        normal = QPushButton("Normal")
        normal.setCursor(Qt.PointingHandCursor)
        normal.clicked.connect(lambda: self.velocidad.setValue(100))
        fila_v.addWidget(normal)
        fila_v.addStretch(1)
        self.velocidad.valueChanged.connect(self._velocidad)
        v.addLayout(fila_v)
        nota2 = QLabel("La velocidad no cambia el tono de la voz.")
        nota2.setObjectName("ayuda")
        v.addWidget(nota2)

        # ---------------- botones
        pie = QHBoxLayout()
        self.et_cambios = QLabel("")
        self.et_cambios.setStyleSheet(f"color:{C['aviso']};font-size:12.5px;font-weight:600;")
        pie.addWidget(self.et_cambios)
        pie.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.setCursor(Qt.PointingHandCursor)
        cancelar.clicked.connect(self.reject)
        pie.addWidget(cancelar)
        guardar = QPushButton("Guardar")
        guardar.setObjectName("principal")
        guardar.setCursor(Qt.PointingHandCursor)
        guardar.setDefault(True)
        guardar.clicked.connect(self.accept)
        pie.addWidget(guardar)
        v.addLayout(pie)

        self._velocidad(self.velocidad.value(), aplicar=False)
        self._cargando = False

    # ------------------------------------------------------------ cambios

    def _elegir_preset(self, nombre):
        if nombre not in PRESETS_EQ:
            return
        self._cargando = True
        for s, g in zip(self.deslizadores, PRESETS_EQ[nombre]):
            s.setValue(g)
        for s, et in zip(self.deslizadores, self.valores):
            et.setText(f"{s.value():+d}")
        self._cargando = False
        if nombre != "Plano" and not self.activo.isChecked():
            self.activo.setChecked(True)
        self._aplicar()

    def _mover(self, _v):
        for s, et in zip(self.deslizadores, self.valores):
            et.setText(f"{s.value():+d}")
        if self._cargando:
            return
        self._cargando = True
        self.preset.setCurrentText("Personalizado")
        self._cargando = False
        if not self.activo.isChecked():
            self.activo.setChecked(True)
        self._aplicar()

    def _aplicar(self, *_):
        """Se oye ya, pero no se guarda en disco hasta pulsar Guardar."""
        if self._cargando:
            return
        self.a["ecualizador"] = self.activo.isChecked()
        self.a["eq_bandas"] = [s.value() for s in self.deslizadores]
        self.a["eq_preset"] = self.preset.currentText()
        self.a["normalizar"] = self.normalizar.isChecked()
        self.a["super_volumen"] = max(0, self.grupo_sv.checkedId())
        self.r.aplicar_sonido()
        self._marcar()

    def _velocidad(self, v, aplicar=True):
        self.et_vel.setText(f"{v / 100:g}×")
        if aplicar:
            self.r.fijar_velocidad(v / 100, guardar=False)
            self._marcar()

    def _marcar(self):
        distinto = any(self.a[k] != self.original[k] for k in CLAVES if k != "velocidad") \
            or abs(self.r.velocidad - self.original_velocidad) > 0.001
        self.et_cambios.setText("Cambios sin guardar" if distinto else "")

    # ------------------------------------------------------------ cerrar

    def accept(self):
        self.a["velocidad"] = self.r.velocidad
        self.a.guardar()
        self._guardado = True
        nombre = NOMBRES_SUPER_VOLUMEN.get(int(self.a["super_volumen"] or 0), "")
        self.ctx.aviso.emit("Sonido guardado" + (f" · súper volumen {nombre.lower()}"
                                                 if int(self.a["super_volumen"] or 0) else ""))
        self.ctx.sonido_cambio.emit()
        super().accept()

    def reject(self):
        self._deshacer()
        super().reject()

    def closeEvent(self, e):
        if not self._guardado:
            self._deshacer()
        super().closeEvent(e)

    def _deshacer(self):
        if self._guardado:
            return
        for k, val in self.original.items():
            self.a[k] = list(val) if isinstance(val, list) else val
        self.r.fijar_velocidad(self.original_velocidad, guardar=False)
        self.r.aplicar_sonido()
        self._guardado = True
