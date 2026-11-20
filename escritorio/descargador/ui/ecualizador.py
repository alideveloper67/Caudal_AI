# -*- coding: utf-8 -*-
"""Volumen máximo, ecualizador (y el avanzado de los donadores) y velocidad.

Todo se oye al momento mientras mueves los controles, pero solo queda guardado
al pulsar «Guardar». Cancelar, Esc o cerrar la ventana dejan el sonido como
estaba al abrirla.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
                               QPushButton, QSlider, QVBoxLayout)

from .. import sonoridad
from ..reproduccion import FRECUENCIAS_EQ, PRESETS_EQ
from .estilos import C

CLAVES = ("ecualizador", "eq_bandas", "eq_preset", "normalizar", "super_volumen", "volumen_maximo",
          "velocidad")
NIVELES = list(sonoridad.NIVELES)          # normal, alto, maximo
TEXTO_VOLUMEN = ("Sube las canciones grabadas bajas hasta que suenen como las fuertes y deja todo "
                 "lo más alto posible sin que el sonido se rompa: un limitador frena los picos. "
                 "Con audífonos puede notarse bastante más fuerte: si te molesta, baja el volumen "
                 "o elige Normal.")


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

        # ---------------- volumen maximo
        cab_v = QHBoxLayout()
        t = QLabel("Volumen máximo")
        t.setObjectName("titulo_seccion")
        cab_v.addWidget(t)
        cab_v.addStretch(1)
        nivel = sonoridad.nivel_efectivo(self.a) if self.a["volumen_maximo"] != "no" else None
        self.vol_max = QCheckBox("Activado")
        self.vol_max.setChecked(self.a["volumen_maximo"] in sonoridad.NIVELES)
        self.vol_max.setCursor(Qt.PointingHandCursor)
        self.vol_max.toggled.connect(self._aplicar)
        cab_v.addWidget(self.vol_max)
        v.addLayout(cab_v)
        nota = QLabel(TEXTO_VOLUMEN)
        nota.setObjectName("secundario")
        nota.setWordWrap(True)
        v.addWidget(nota)
        fila_sv = QHBoxLayout()
        fila_sv.setSpacing(8)
        self.grupo_sv = QButtonGroup(self)
        for i, clave in enumerate(NIVELES):
            b = QPushButton(sonoridad.NOMBRES_NIVEL[clave])
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.grupo_sv.addButton(b, i)
            fila_sv.addWidget(b)
        fila_sv.addStretch(1)
        self.et_ganancia = QLabel("")
        self.et_ganancia.setObjectName("ayuda")
        fila_sv.addWidget(self.et_ganancia)
        v.addLayout(fila_sv)
        boton = self.grupo_sv.button(NIVELES.index(nivel or sonoridad.NIVEL_POR_DEFECTO))
        if boton:
            boton.setChecked(True)
        self.grupo_sv.idClicked.connect(self._elegir_nivel)

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
        from .ecualizador_avanzado import es_premium
        premium = es_premium(ctx)
        fila_av = QHBoxLayout()
        self.bt_avanzado = QPushButton(("" if premium else "🔒 ") + "Ecualizador avanzado…")
        self.bt_avanzado.setObjectName("contorno")
        self.bt_avanzado.setCursor(Qt.PointingHandCursor)
        self.bt_avanzado.clicked.connect(self._abrir_avanzado)
        fila_av.addWidget(self.bt_avanzado)
        av = QLabel("15 bandas, preamplificador, ajustes con nombre y uno por salida"
                    + ("" if premium else " · para donadores y fundadores")
                    + (" · en uso" if premium and self.a["eq_avanzado"] else ""))
        av.setObjectName("ayuda")
        fila_av.addWidget(av)
        fila_av.addStretch(1)
        v.addLayout(fila_av)

        # ---------------- mas
        self.normalizar = QCheckBox("Igualar el volumen entre canciones (si Volumen máximo está apagado)")
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
        self._pintar_ganancia()
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
        i = max(0, self.grupo_sv.checkedId())
        sonoridad.poner_nivel(self.a, NIVELES[i] if self.vol_max.isChecked() else "no")
        self.r.aplicar_sonido()
        self._pintar_ganancia()
        self._marcar()

    def _elegir_nivel(self, _i):
        if not self.vol_max.isChecked():
            self._cargando = True
            self.vol_max.setChecked(True)
            self._cargando = False
        self._aplicar()

    def _pintar_ganancia(self):
        """Lo que se le está sumando (o quitando) a la canción que suena."""
        if sonoridad.nivel_efectivo(self.a) is None or self.r.actual is None:
            self.et_ganancia.setText("")
            return
        g = self.r.ganancia_actual(self.r.actual)
        medida = self.r.medida_de(self.r.actual)
        texto = f"Esta canción: {g:+.1f} dB".replace(".", ",")
        self.et_ganancia.setText(texto if medida else texto + " (midiéndola…)")

    def _abrir_avanzado(self):
        from . import ecualizador_avanzado
        ecualizador_avanzado.abrir(self.ctx, self)
        self.r.aplicar_sonido()

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
        nivel = self.a["volumen_maximo"]
        self.ctx.aviso.emit("Sonido guardado" + (f" · volumen máximo {sonoridad.NOMBRES_NIVEL[nivel].lower()}"
                                                 if nivel in sonoridad.NIVELES else ""))
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
