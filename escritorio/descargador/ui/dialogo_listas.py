# -*- coding: utf-8 -*-
"""Traer una lista de Spotify, Apple Music, YouTube Music o SoundCloud y guardarla o descargarla."""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout)

from .. import importacion, listas
from ..motor import formato_tiempo
from .estilos import C
from . import iconos


class Lector(QThread):
    listo = Signal(dict)
    fallo = Signal(str)

    def __init__(self, url, ajustes):
        super().__init__()
        self.url = url
        self.ajustes = ajustes

    def run(self):
        try:
            self.listo.emit(listas.leer(self.url, self.ajustes))
        except listas.ErrorLista as e:
            self.fallo.emit(str(e))
        except Exception as e:
            self.fallo.emit(f"No se pudo leer la lista: {str(e)[:90]}")


class DialogoListas(QDialog):
    """Pega un enlace, elige las canciones y guárdalas como lista (o descárgalas)."""

    descargar = Signal(list)                  # [{titulo, artista, url|busqueda}]
    guardar = Signal(list, str, str)          # canciones elegidas, nombre de la lista y de donde vienen
    a_me_gusta = Signal(list, str, str, str)  # canciones, titulo, servicio y enlace
    pasar_me_gusta = Signal()                 # abrir «Pasar tus me gusta»

    def __init__(self, ajustes, padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.lector = None
        self.lista = None

        self.setWindowTitle("Traer una lista")
        self.setMinimumSize(620, 560)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 20, 22, 18)
        raiz.setSpacing(14)

        titulo = QLabel("Traer una lista")
        titulo.setStyleSheet("font-size:19px;font-weight:700;letter-spacing:-0.3px;")
        raiz.addWidget(titulo)

        ayuda = QLabel("Pega el enlace de una lista o un álbum público de Spotify, Apple Music, "
                       "YouTube Music o SoundCloud. Se leen todas sus canciones (sin límite) y "
                       "las guardas como lista, en tus Me gusta o las descargas en audio.")
        ayuda.setObjectName("ayuda")
        ayuda.setWordWrap(True)
        raiz.addWidget(ayuda)

        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Enlace de Spotify, Apple Music, YouTube Music o SoundCloud")
        self.campo.returnPressed.connect(self._leer)
        fila.addWidget(self.campo, 1)

        self.bt_pegar = QPushButton()
        self.bt_pegar.setIcon(iconos.icono("pegar", 17))
        self.bt_pegar.setToolTip("Pegar")
        self.bt_pegar.setCursor(Qt.PointingHandCursor)
        self.bt_pegar.clicked.connect(self._pegar)
        fila.addWidget(self.bt_pegar)

        self.bt_leer = QPushButton("  Leer")
        self.bt_leer.setObjectName("principal")
        self.bt_leer.setIcon(iconos.icono("lupa", 16, C["acento_texto"]))
        self.bt_leer.setCursor(Qt.PointingHandCursor)
        self.bt_leer.clicked.connect(self._leer)
        fila.addWidget(self.bt_leer)
        raiz.addLayout(fila)

        self.barra = QProgressBar()
        self.barra.setRange(0, 0)
        self.barra.setFixedHeight(4)
        self.barra.hide()
        raiz.addWidget(self.barra)

        self.et_estado = QLabel("")
        self.et_estado.setObjectName("ayuda")
        self.et_estado.setWordWrap(True)
        raiz.addWidget(self.et_estado)

        self.canciones = QListWidget()
        self.canciones.setSelectionMode(QAbstractItemView.NoSelection)
        self.canciones.setAlternatingRowColors(False)
        self.canciones.setUniformItemSizes(True)     # miles de filas sin trabarse
        self.canciones.itemChanged.connect(self._marcada)
        self._marcadas = 0
        raiz.addWidget(self.canciones, 1)

        self.bt_me_gusta_externos = QPushButton(
            "Pasar tus me gusta de Spotify, YouTube Music o SoundCloud…")
        self.bt_me_gusta_externos.setObjectName("enlace")
        self.bt_me_gusta_externos.setCursor(Qt.PointingHandCursor)
        self.bt_me_gusta_externos.clicked.connect(self._abrir_me_gusta)
        raiz.addWidget(self.bt_me_gusta_externos, 0, Qt.AlignLeft)

        fila2 = QHBoxLayout()
        self.casilla_todas = QCheckBox("Marcar todas")
        self.casilla_todas.setChecked(True)
        self.casilla_todas.toggled.connect(self._marcar_todas)
        self.casilla_todas.setEnabled(False)
        fila2.addWidget(self.casilla_todas)
        fila2.addStretch(1)

        self.bt_cancelar = QPushButton("Cerrar")
        self.bt_cancelar.clicked.connect(self.reject)
        fila2.addWidget(self.bt_cancelar)

        self.bt_guardar = QPushButton("  Guardar como lista")
        self.bt_guardar.setObjectName("principal")
        self.bt_guardar.setIcon(iconos.icono("anadir_lista", 16, C["acento_texto"]))
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.setEnabled(False)
        self.bt_guardar.setToolTip("Se guarda en Tu biblioteca y aparece también en el teléfono y en la web")
        self.bt_guardar.clicked.connect(self._guardar)

        self.bt_me_gusta = QPushButton("  A mis Me gusta")
        self.bt_me_gusta.setObjectName("contorno")
        self.bt_me_gusta.setIcon(iconos.icono("corazon", 16, C["texto"]))
        self.bt_me_gusta.setCursor(Qt.PointingHandCursor)
        self.bt_me_gusta.setEnabled(False)
        self.bt_me_gusta.setToolTip("Añade las canciones a tus Me gusta, sin repetir las que ya están")
        self.bt_me_gusta.clicked.connect(self._a_me_gusta)

        self.bt_descargar = QPushButton("  Descargar")
        self.bt_descargar.setObjectName("contorno")
        self.bt_descargar.setIcon(iconos.icono("descargar", 16, C["texto"]))
        self.bt_descargar.setCursor(Qt.PointingHandCursor)
        self.bt_descargar.setEnabled(False)
        self.bt_descargar.clicked.connect(self._descargar)
        fila2.addWidget(self.bt_descargar)
        fila2.addWidget(self.bt_me_gusta)
        fila2.addWidget(self.bt_guardar)
        raiz.addLayout(fila2)

    # ------------------------------------------------------------ leer

    def _pegar(self):
        texto = QApplication.clipboard().text().strip()
        if texto:
            self.campo.setText(texto)
            self._leer()

    def _leer(self):
        url = self.campo.text().strip()
        if not url:
            return
        self.bt_leer.setEnabled(False)
        self.barra.show()
        self.et_estado.setText("Leyendo la lista...")
        self.canciones.blockSignals(True)
        self.canciones.clear()
        self.canciones.blockSignals(False)
        self._marcadas = 0
        self.et_estado.setStyleSheet("")
        self.bt_descargar.setEnabled(False)
        self.bt_me_gusta.setEnabled(False)
        self.casilla_todas.setEnabled(False)

        self.lector = Lector(url, self.ajustes)
        self.lector.listo.connect(self._pintar)
        self.lector.fallo.connect(self._fallo)
        self.lector.start()

    def _pintar(self, datos):
        self.lista = datos
        self.barra.hide()
        self.bt_leer.setEnabled(True)

        resumen = (f"{datos['plataforma']}  ·  {datos['titulo']}  ·  "
                   f"{importacion.miles(datos['total'])} canciones")
        if datos.get("aviso"):
            resumen += f"\n{datos['aviso']}"
        self.et_estado.setText(resumen)

        self.canciones.blockSignals(True)
        self.canciones.setUpdatesEnabled(False)
        for c in datos["canciones"]:
            partes = [c.get("artista", "")]
            if c.get("duracion"):
                partes.append(formato_tiempo(c["duracion"]))
            detalle = "  ·  ".join(x for x in partes if x)
            item = QListWidgetItem(f"{c['titulo']}\n{detalle}" if detalle else c["titulo"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.canciones.addItem(item)
        self.canciones.setUpdatesEnabled(True)
        self.canciones.blockSignals(False)
        self._marcadas = self.canciones.count()

        hay = datos["total"] > 0
        self.bt_descargar.setEnabled(hay)
        self.bt_guardar.setEnabled(hay)
        self.bt_me_gusta.setEnabled(hay)
        self.casilla_todas.setEnabled(hay)
        self.casilla_todas.blockSignals(True)
        self.casilla_todas.setChecked(True)
        self.casilla_todas.blockSignals(False)
        self._actualizar_boton()

    def _fallo(self, mensaje):
        self.barra.hide()
        self.bt_leer.setEnabled(True)
        self.et_estado.setText(mensaje)
        self.et_estado.setStyleSheet(f"color:{C['error']};font-size:11px;")

    # ------------------------------------------------------------ elegir

    def _marcar_todas(self, valor):
        # sin avisar fila por fila: con 5 000 canciones, contar en cada cambio trababa la ventana
        estado = Qt.Checked if valor else Qt.Unchecked
        self.canciones.blockSignals(True)
        for i in range(self.canciones.count()):
            self.canciones.item(i).setCheckState(estado)
        self.canciones.blockSignals(False)
        self._marcadas = self.canciones.count() if valor else 0
        self._actualizar_boton()

    def _marcada(self, item):
        self._marcadas += 1 if item.checkState() == Qt.Checked else -1
        self._actualizar_boton()

    def _elegidas(self):
        if not self.lista:
            return []
        salida = []
        for i in range(self.canciones.count()):
            if self.canciones.item(i).checkState() == Qt.Checked:
                salida.append(self.lista["canciones"][i])
        return salida

    def _actualizar_boton(self, *_):
        n = max(0, self._marcadas)
        txt = importacion.miles(n)
        self.bt_descargar.setText(f"  Descargar {txt}" if n else "  Descargar")
        self.bt_descargar.setEnabled(n > 0)
        self.bt_guardar.setText(f"  Guardar {txt} como lista" if n else "  Guardar como lista")
        self.bt_guardar.setEnabled(n > 0)
        self.bt_me_gusta.setEnabled(n > 0)

    def _guardar(self):
        elegidas = self._elegidas()
        if elegidas:
            self.guardar.emit(elegidas, (self.lista or {}).get("titulo") or "Lista traída",
                              (self.lista or {}).get("plataforma") or "")
            self.accept()

    def _a_me_gusta(self):
        elegidas = self._elegidas()
        if elegidas:
            lista = self.lista or {}
            self.a_me_gusta.emit(elegidas, lista.get("titulo") or "", lista.get("plataforma") or "",
                                 self.campo.text().strip())
            self.accept()

    def _abrir_me_gusta(self):
        self.reject()
        self.pasar_me_gusta.emit()

    def _descargar(self):
        elegidas = self._elegidas()
        if elegidas:
            self.descargar.emit(elegidas)
            self.accept()
