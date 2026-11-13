# -*- coding: utf-8 -*-
"""Ecualizador de 10 bandas y ajustes de sonido, aplicados en vivo."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QVBoxLayout)

from ..reproduccion import FRECUENCIAS_EQ, PRESETS_EQ


def _nombre_frecuencia(f):
    return f"{f // 1000}k" if f >= 1000 else str(f)


class DialogoEcualizador(QDialog):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.a = ctx.ajustes
        self.r = ctx.reproductor
        self.setWindowTitle("Ecualizador y sonido")
        self.setMinimumWidth(640)
        self._cargando = True

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(14)
        cab = QHBoxLayout()
        t = QLabel("Ecualizador")
        t.setObjectName("titulo_seccion")
        cab.addWidget(t)
        cab.addStretch(1)
        self.activo = QCheckBox("Activado")
        self.activo.setChecked(bool(self.a["ecualizador"]))
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
            val = QLabel(f"{g:+.0f}")
            val.setAlignment(Qt.AlignCenter)
            val.setObjectName("secundario")
            col.addWidget(val)
            s = QSlider(Qt.Vertical)
            s.setRange(-12, 12)
            s.setValue(int(g))
            s.setFixedHeight(190)
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
        nota = QLabel("Graves a la izquierda, agudos a la derecha (en dB). Se nota al momento.")
        nota.setObjectName("ayuda")
        v.addWidget(nota)

        sep = QLabel("Más sonido")
        sep.setStyleSheet("font-size:16px;font-weight:800;margin-top:8px;")
        v.addWidget(sep)
        self.normalizar = QCheckBox("Normalizar el volumen entre canciones")
        self.normalizar.setChecked(bool(self.a["normalizar"]))
        self.normalizar.toggled.connect(self._aplicar)
        v.addWidget(self.normalizar)
        fila_v = QHBoxLayout()
        et_v = QLabel("Velocidad")
        et_v.setObjectName("secundario")
        fila_v.addWidget(et_v)
        self.velocidad = QSlider(Qt.Horizontal)
        self.velocidad.setRange(25, 300)
        self.velocidad.setSingleStep(5)
        self.velocidad.setValue(int(round(self.r.velocidad * 100)))
        self.velocidad.setFixedWidth(260)
        fila_v.addWidget(self.velocidad)
        self.et_vel = QLabel("")
        self.et_vel.setFixedWidth(70)
        fila_v.addWidget(self.et_vel)
        normal = QPushButton("Normal")
        normal.clicked.connect(lambda: self.velocidad.setValue(100))
        fila_v.addWidget(normal)
        fila_v.addStretch(1)
        self.velocidad.valueChanged.connect(self._velocidad)
        self.velocidad.sliderReleased.connect(
            lambda: self.r.fijar_velocidad(self.velocidad.value() / 100))
        v.addLayout(fila_v)
        nota2 = QLabel("La velocidad no cambia el tono de la voz.")
        nota2.setObjectName("ayuda")
        v.addWidget(nota2)

        cerrar = QPushButton("Listo")
        cerrar.setObjectName("principal")
        cerrar.clicked.connect(self.accept)
        v.addWidget(cerrar, 0, Qt.AlignRight)
        self._velocidad(self.velocidad.value(), aplicar=False)
        self._cargando = False

    def _elegir_preset(self, nombre):
        if nombre not in PRESETS_EQ:
            return
        self._cargando = True
        for s, g in zip(self.deslizadores, PRESETS_EQ[nombre]):
            s.setValue(g)
        self._cargando = False
        if nombre != "Plano":
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
        if self._cargando:
            return
        self.a["ecualizador"] = self.activo.isChecked()
        self.a["eq_bandas"] = [s.value() for s in self.deslizadores]
        self.a["eq_preset"] = self.preset.currentText()
        self.a["normalizar"] = self.normalizar.isChecked()
        self.a.guardar()
        self.r.aplicar_sonido()

    def _velocidad(self, v, aplicar=True):
        self.et_vel.setText(f"{v / 100:g}×")
        if aplicar and not self.velocidad.isSliderDown():
            self.r.fijar_velocidad(v / 100)
