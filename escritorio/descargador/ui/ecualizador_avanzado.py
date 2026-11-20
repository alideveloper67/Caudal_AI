# -*- coding: utf-8 -*-
"""Ecualizador avanzado (donadores y fundadores): 15 bandas, preamplificador, ajustes guardados con
nombre y un ajuste para cada salida (audífonos, parlante, bluetooth).

Como el ecualizador normal: se oye al momento y solo queda al pulsar «Guardar». Sin beneficios no
se abre: `aviso_bloqueado` explica cómo conseguirlo."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QInputDialog, QLabel,
                               QMessageBox, QPushButton, QSlider, QVBoxLayout)

from .. import eq_avanzado as EQ
from ..salida_audio import NOMBRES_TIPO, TIPOS
from .estilos import C

CLAVES = ("eq_avanzado", "eq_av_bandas", "eq_av_preamp", "eq_av_nombre", "eq_av_guardados",
          "eq_por_salida")
TEXTO_BLOQUEO = ("🔒 El ecualizador avanzado es para donadores y fundadores de Caudal: 15 bandas, "
                 "preamplificador, tus ajustes guardados con nombre y uno distinto para audífonos, "
                 "parlante y bluetooth que se pone solo al cambiar de salida.\n\n"
                 "Para tenerlo, apoya a Caudal con una donación o canjea un código de prueba. "
                 "El ecualizador normal sigue disponible para todos.")


def _nombre_frecuencia(f):
    if f >= 1000:
        k = f / 1000
        return f"{k:g}k".replace(".", ",")
    return str(f)


def _copiar(v):
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return {k: (dict(x) if isinstance(x, dict) else x) for k, x in v.items()}
    return v


def es_premium(ctx):
    g = getattr(ctx, "premium", None)
    return bool(g is not None and g.premium)


def aviso_bloqueado(ctx, padre=None):
    """El candado: qué es y cómo conseguirlo (con los botones de donar y de código de prueba)."""
    from .canje_pase import boton_codigo
    from .donar import boton_donar
    d = QDialog(padre)
    d.setWindowTitle("Ecualizador avanzado")
    d.setMinimumWidth(460)
    v = QVBoxLayout(d)
    v.setContentsMargins(24, 20, 24, 18)
    v.setSpacing(12)
    t = QLabel(TEXTO_BLOQUEO)
    t.setWordWrap(True)
    v.addWidget(t)
    fila = QHBoxLayout()
    fila.addWidget(boton_donar(texto="Donar aquí"))
    fila.addWidget(boton_codigo(ctx, texto="Tengo un código de prueba"))
    fila.addStretch(1)
    cerrar = QPushButton("Entendido")
    cerrar.clicked.connect(d.accept)
    fila.addWidget(cerrar)
    v.addLayout(fila)
    d.exec()


def abrir(ctx, padre=None):
    """Abre el avanzado o, sin beneficios, el aviso del candado."""
    if not es_premium(ctx):
        aviso_bloqueado(ctx, padre)
        return None
    dlg = DialogoEqAvanzado(ctx, padre)
    dlg.exec()
    return dlg


class DialogoEqAvanzado(QDialog):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.a = ctx.ajustes
        self.r = ctx.reproductor
        self.setWindowTitle("Ecualizador avanzado")
        self.setMinimumWidth(820)
        self._cargando = True
        self.original = {k: _copiar(self.a[k]) for k in CLAVES}
        self._guardado = False

        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 20)
        v.setSpacing(12)

        cab = QHBoxLayout()
        t = QLabel("Ecualizador avanzado")
        t.setObjectName("titulo_seccion")
        cab.addWidget(t)
        cab.addStretch(1)
        self.activo = QCheckBox("Usar en lugar del normal")
        self.activo.setChecked(bool(self.a["eq_avanzado"]))
        self.activo.setCursor(Qt.PointingHandCursor)
        self.activo.toggled.connect(self._aplicar)
        cab.addWidget(self.activo)
        v.addLayout(cab)

        # ---------------- ajustes guardados
        fila = QHBoxLayout()
        et = QLabel("Ajuste")
        et.setObjectName("secundario")
        fila.addWidget(et)
        self.guardados = QComboBox()
        self.guardados.setFixedWidth(240)
        self.guardados.activated.connect(self._elegir_guardado)
        fila.addWidget(self.guardados)
        self.bt_guardar_como = QPushButton("Guardar como…")
        self.bt_guardar_como.clicked.connect(self._guardar_como)
        fila.addWidget(self.bt_guardar_como)
        self.bt_borrar = QPushButton("Borrar")
        self.bt_borrar.clicked.connect(self._borrar)
        fila.addWidget(self.bt_borrar)
        fila.addStretch(1)
        plano = QPushButton("Dejar plano")
        plano.clicked.connect(self._plano)
        fila.addWidget(plano)
        v.addLayout(fila)

        # ---------------- preamplificador + 15 bandas
        bandas = QHBoxLayout()
        bandas.setSpacing(4)
        self.deslizadores, self.valores = [], []
        self.pre, self.et_pre = self._columna(bandas, "Pre", EQ.PREAMP_MIN, EQ.PREAMP_MAX,
                                              EQ.limpiar_preamp(self.a["eq_av_preamp"]))
        sep = QLabel("")
        sep.setFixedWidth(10)
        bandas.addWidget(sep)
        for f, g in zip(EQ.FRECUENCIAS, EQ.limpiar_bandas(self.a["eq_av_bandas"])):
            s, et = self._columna(bandas, _nombre_frecuencia(f), -EQ.RANGO_BANDA, EQ.RANGO_BANDA, g)
            self.deslizadores.append(s)
            self.valores.append(et)
        v.addLayout(bandas)
        nota = QLabel("«Pre» sube o baja todo antes del ecualizador. Bandas en pasos de 0,5 dB; "
                      "un limitador evita que se rompa el sonido.")
        nota.setObjectName("ayuda")
        nota.setWordWrap(True)
        v.addWidget(nota)

        # ---------------- por salida
        t2 = QLabel("Un ajuste para cada salida")
        t2.setObjectName("titulo_seccion")
        v.addWidget(t2)
        vigia = getattr(ctx, "vigia_salida", None)
        ahora = NOMBRES_TIPO.get(getattr(vigia, "tipo", None) or "", "")
        nota2 = QLabel("Cuando cambias de salida (conectas audífonos, un parlante o algo por "
                       "bluetooth), Caudal pone solo el ajuste que elijas aquí."
                       + (f" Ahora suena por: {ahora.lower()}." if ahora else ""))
        nota2.setObjectName("secundario")
        nota2.setWordWrap(True)
        v.addWidget(nota2)
        filas = QHBoxLayout()
        self.por_salida = {}
        for tipo in TIPOS:
            col = QVBoxLayout()
            et = QLabel(NOMBRES_TIPO[tipo])
            et.setObjectName("secundario")
            col.addWidget(et)
            combo = QComboBox()
            combo.setFixedWidth(220)
            combo.activated.connect(lambda _i, t=tipo: self._asignar(t))
            col.addWidget(combo)
            filas.addLayout(col)
            self.por_salida[tipo] = combo
        filas.addStretch(1)
        v.addLayout(filas)

        # ---------------- botones
        pie = QHBoxLayout()
        self.et_cambios = QLabel("")
        self.et_cambios.setStyleSheet(f"color:{C['aviso']};font-size:12.5px;font-weight:600;")
        pie.addWidget(self.et_cambios)
        pie.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        pie.addWidget(cancelar)
        guardar = QPushButton("Guardar")
        guardar.setObjectName("principal")
        guardar.setDefault(True)
        guardar.clicked.connect(self.accept)
        pie.addWidget(guardar)
        v.addLayout(pie)

        self._llenar_listas()
        self._cargando = False

    # ------------------------------------------------------------ piezas

    def _columna(self, fila, nombre, minimo, maximo, valor):
        col = QVBoxLayout()
        col.setSpacing(4)
        et = QLabel(self._texto_db(valor))
        et.setAlignment(Qt.AlignCenter)
        et.setObjectName("secundario")
        col.addWidget(et)
        s = QSlider(Qt.Vertical)
        s.setRange(int(minimo / EQ.PASO), int(maximo / EQ.PASO))     # en medios dB
        s.setValue(int(round(valor / EQ.PASO)))
        s.setFixedHeight(170)
        s.setCursor(Qt.PointingHandCursor)
        s.valueChanged.connect(self._mover)
        col.addWidget(s, 0, Qt.AlignHCenter)
        n = QLabel(nombre)
        n.setAlignment(Qt.AlignCenter)
        n.setObjectName("ayuda")
        col.addWidget(n)
        fila.addLayout(col)
        return s, et

    @staticmethod
    def _texto_db(v):
        return f"{v:+.1f}".replace(".", ",").replace(",0", "")

    def bandas(self):
        return [s.value() * EQ.PASO for s in self.deslizadores]

    def preamp(self):
        return self.pre.value() * EQ.PASO

    def _poner(self, bandas, preamp):
        self._cargando = True
        for s, g in zip(self.deslizadores, EQ.limpiar_bandas(bandas)):
            s.setValue(int(round(g / EQ.PASO)))
        self.pre.setValue(int(round(EQ.limpiar_preamp(preamp) / EQ.PASO)))
        self._cargando = False
        self._rotular()

    def _rotular(self):
        for s, et in zip(self.deslizadores, self.valores):
            et.setText(self._texto_db(s.value() * EQ.PASO))
        self.et_pre.setText(self._texto_db(self.preamp()))

    def _llenar_listas(self):
        nombres = list(EQ.guardados(self.a))
        actual = self.a["eq_av_nombre"] or ""
        self.guardados.clear()
        self.guardados.addItem("Personalizado")
        for n in nombres:
            self.guardados.addItem(n)
        i = self.guardados.findText(actual) if actual else 0
        self.guardados.setCurrentIndex(max(0, i))
        self.bt_borrar.setEnabled(self.guardados.currentIndex() > 0)
        por = EQ.por_salida(self.a)
        for tipo, combo in self.por_salida.items():
            combo.clear()
            combo.addItem("No cambiar")
            for n in nombres:
                combo.addItem(n)
            j = combo.findText(por.get(tipo) or "")
            combo.setCurrentIndex(max(0, j))

    # ------------------------------------------------------------ cambios

    def _mover(self, _v):
        self._rotular()
        if self._cargando:
            return
        self.a["eq_av_nombre"] = ""
        self._cargando = True
        self.guardados.setCurrentIndex(0)
        self.bt_borrar.setEnabled(False)
        self.activo.setChecked(True)
        self._cargando = False
        self._aplicar()

    def _elegir_guardado(self, i):
        if i <= 0:
            return
        nombre = self.guardados.itemText(i)
        if EQ.cargar_ajuste(self.a, nombre):
            d = EQ.guardados(self.a)[nombre]
            self._poner(d["bandas"], d["preamp"])
            self._cargando = True
            self.activo.setChecked(True)
            self._cargando = False
        self.bt_borrar.setEnabled(True)
        self._aplicar()

    def _plano(self):
        self._poner([0] * len(EQ.FRECUENCIAS), 0)
        self.a["eq_av_nombre"] = ""
        self.guardados.setCurrentIndex(0)
        self._aplicar()

    def _guardar_como(self):
        sugerido = self.a["eq_av_nombre"] or ""
        nombre, ok = QInputDialog.getText(self, "Guardar ajuste", "Nombre del ajuste:", text=sugerido)
        if not ok:
            return
        hecho = EQ.guardar_ajuste(self.a, nombre, self.bandas(), self.preamp())
        if not hecho:
            QMessageBox.information(self, "Guardar ajuste",
                                    "Escribe un nombre (o borra alguno: caben "
                                    f"{EQ.MAX_GUARDADOS} ajustes).")
            return
        self.a["eq_av_nombre"] = hecho
        self._llenar_listas()
        self._marcar()

    def _borrar(self):
        nombre = self.guardados.currentText()
        if self.guardados.currentIndex() <= 0:
            return
        EQ.borrar_ajuste(self.a, nombre)
        self.a["eq_av_nombre"] = ""
        self._llenar_listas()
        self._marcar()

    def _asignar(self, tipo):
        combo = self.por_salida[tipo]
        EQ.asignar_salida(self.a, tipo, combo.currentText() if combo.currentIndex() > 0 else "")
        self._marcar()

    def _aplicar(self, *_):
        if self._cargando:
            return
        self.a["eq_avanzado"] = self.activo.isChecked()
        self.a["eq_av_bandas"] = self.bandas()
        self.a["eq_av_preamp"] = self.preamp()
        self.r.aplicar_sonido()
        self._marcar()

    def _marcar(self):
        distinto = any(self.a[k] != self.original[k] for k in CLAVES)
        self.et_cambios.setText("Cambios sin guardar" if distinto else "")

    # ------------------------------------------------------------ cerrar

    def accept(self):
        self.a.guardar()
        self._guardado = True
        self.ctx.aviso.emit("Ecualizador avanzado guardado")
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
            self.a[k] = _copiar(val)
        self.r.aplicar_sonido()
        self._guardado = True
