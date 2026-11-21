# -*- coding: utf-8 -*-
"""Avisar de versiones nuevas y instalarlas sin que el usuario busque nada."""

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout)

from .. import version
from . import iconos
from .estilos import C


class Buscador(QThread):
    """Pregunta a GitHub si hay algo nuevo. Nunca molesta si no lo hay."""

    resultado = Signal(object)      # dict con la novedad, o None

    def run(self):
        try:
            self.resultado.emit(version.buscar_actualizacion())
        except Exception:
            self.resultado.emit(None)


class Descarga(QThread):
    progreso = Signal(int)
    listo = Signal(str)
    fallo = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            ruta = version.descargar(self.url, lambda p: self.progreso.emit(int(p)))
            self.listo.emit(ruta)
        except Exception as e:
            self.fallo.emit(f"No se pudo bajar la actualizacion: {str(e)[:110]}")


def mostrar_aviso(novedad, padre=None):
    """Avisa de una versión nueva, siempre con la ventanita sencilla: ya no hay «gran
    actualización» ni presentación de novedades (aunque la release lleve `[grande]`)."""
    return DialogoActualizacion(novedad, padre).exec()


class DialogoActualizacion(QDialog):
    """Ventanita sencilla: hay versión nueva y se instala si la persona quiere (sin notas)."""

    def __init__(self, novedad, padre=None):
        super().__init__(padre)
        self.novedad = novedad
        self.descarga = None

        self.setWindowTitle("Hay una versión nueva")
        self.setMinimumWidth(520)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 18)
        v.setSpacing(13)

        titulo = QLabel(f"Caudal {novedad['version']} ya está lista")
        titulo.setStyleSheet("font-size:19px;font-weight:700;letter-spacing:-0.3px;")
        v.addWidget(titulo)

        sub = QLabel("Descárgala para tener las últimas mejoras y arreglos.")
        sub.setObjectName("ayuda")
        sub.setWordWrap(True)
        v.addWidget(sub)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setFixedHeight(6)
        self.barra.setTextVisible(False)
        self.barra.hide()
        v.addWidget(self.barra)

        self.et_estado = QLabel("")
        self.et_estado.setObjectName("ayuda")
        v.addWidget(self.et_estado)

        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_luego = QPushButton("Más tarde")
        self.bt_luego.clicked.connect(self.reject)
        fila.addWidget(self.bt_luego)

        self.bt_instalar = QPushButton("  Instalar ahora")
        self.bt_instalar.setObjectName("principal")
        self.bt_instalar.setIcon(iconos.icono("descargar", 16, C["acento_texto"]))
        self.bt_instalar.setCursor(Qt.PointingHandCursor)
        self.bt_instalar.clicked.connect(self._instalar)
        fila.addWidget(self.bt_instalar)
        v.addLayout(fila)

        if not novedad.get("instalador"):
            self.bt_instalar.setEnabled(False)
            self.et_estado.setText(
                "Esta version no trae instalador adjunto. Bajala desde la pagina "
                "del proyecto.")

    def _instalar(self):
        self.bt_instalar.setEnabled(False)
        self.bt_luego.setEnabled(False)
        self.barra.show()
        self.et_estado.setText("Bajando la actualizacion...")

        self.descarga = Descarga(self.novedad["instalador"])
        self.descarga.progreso.connect(self.barra.setValue)
        self.descarga.listo.connect(self._lanzar)
        self.descarga.fallo.connect(self._fallo)
        self.descarga.start()

    def _lanzar(self, ruta):
        self.et_estado.setText("Instalando. Caudal se cerrara un momento...")
        version.instalar_y_salir(ruta)

    def _fallo(self, mensaje):
        self.barra.hide()
        self.bt_instalar.setEnabled(True)
        self.bt_luego.setEnabled(True)
        self.et_estado.setText(mensaje)


class BuscadorAnteriores(QThread):
    """Trae de GitHub las versiones anteriores a esta."""

    resultado = Signal(object)      # lista, o None si no se pudo preguntar

    def run(self):
        try:
            self.resultado.emit(version.versiones_anteriores())
        except Exception:
            self.resultado.emit(None)


class DialogoVolverVersion(QDialog):
    """Instala una versión anterior de Caudal encima de esta, por si la nueva falla.

    Tus listas, «me gusta», descargas y ajustes se quedan: viven fuera de la carpeta del programa."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.descarga = None
        self.setWindowTitle("Volver a una versión anterior")
        self.setMinimumWidth(500)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 18)
        v.setSpacing(13)

        titulo = QLabel("Volver a una versión anterior")
        titulo.setStyleSheet("font-size:19px;font-weight:700;letter-spacing:-0.3px;")
        v.addWidget(titulo)

        sub = QLabel(f"Tienes la {version.VERSION}. Si algo falla en ella, elige una versión "
                     "anterior: se instala encima y conserva tus listas, «me gusta», descargas "
                     "y ajustes. Cuando salga un arreglo, Caudal te lo ofrecerá como siempre.")
        sub.setObjectName("ayuda")
        sub.setWordWrap(True)
        v.addWidget(sub)

        self.combo = QComboBox()
        self.combo.setEnabled(False)
        self.combo.addItem("Buscando versiones…")
        v.addWidget(self.combo)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setFixedHeight(6)
        self.barra.setTextVisible(False)
        self.barra.hide()
        v.addWidget(self.barra)

        self.et_estado = QLabel("")
        self.et_estado.setObjectName("ayuda")
        self.et_estado.setWordWrap(True)
        v.addWidget(self.et_estado)

        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_cerrar = QPushButton("Cancelar")
        self.bt_cerrar.clicked.connect(self.reject)
        fila.addWidget(self.bt_cerrar)
        self.bt_volver = QPushButton("  Instalar esta versión")
        self.bt_volver.setObjectName("principal")
        self.bt_volver.setIcon(iconos.icono("descargar", 16, C["acento_texto"]))
        self.bt_volver.setCursor(Qt.PointingHandCursor)
        self.bt_volver.setEnabled(False)
        self.bt_volver.clicked.connect(self._instalar)
        fila.addWidget(self.bt_volver)
        v.addLayout(fila)

        self.buscador = BuscadorAnteriores(self)
        self.buscador.resultado.connect(self._llegaron)
        self.buscador.start()

    def _llegaron(self, lista):
        self.combo.clear()
        if lista is None:
            self.combo.addItem("Sin conexión")
            self.et_estado.setText("No se pudo preguntar por las versiones. Revisa tu internet "
                                   "y vuelve a abrir esta ventana.")
            return
        if not lista:
            self.combo.addItem("No hay versiones anteriores")
            self.et_estado.setText("Esta es la primera versión publicada.")
            return
        for d in lista:
            fecha = f"  ·  {d['fecha']}" if d.get("fecha") else ""
            self.combo.addItem(f"Caudal {d['version']}{fecha}", d)
        self.combo.setEnabled(True)
        self.bt_volver.setEnabled(True)

    def _instalar(self):
        d = self.combo.currentData()
        if not isinstance(d, dict):
            return
        self.combo.setEnabled(False)
        self.bt_volver.setEnabled(False)
        self.bt_cerrar.setEnabled(False)
        self.barra.show()
        self.et_estado.setText(f"Bajando Caudal {d['version']}…")
        self.descarga = Descarga(d["instalador"])
        self.descarga.progreso.connect(self.barra.setValue)
        self.descarga.listo.connect(self._lanzar)
        self.descarga.fallo.connect(self._fallo)
        self.descarga.start()

    def _lanzar(self, ruta):
        self.et_estado.setText("Instalando. Caudal se cerrará un momento…")
        version.instalar_y_salir(ruta)

    def _fallo(self, mensaje):
        self.barra.hide()
        self.combo.setEnabled(True)
        self.bt_volver.setEnabled(True)
        self.bt_cerrar.setEnabled(True)
        self.et_estado.setText(mensaje)

    def reject(self):
        if self.descarga is not None and self.descarga.isRunning():
            return                          # a media descarga no se cierra
        super().reject()
