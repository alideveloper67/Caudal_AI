# -*- coding: utf-8 -*-
"""«Compartir perfil»: vista previa de la tarjeta vertical (9:16) del perfil, con tres estilos,
para guardarla como imagen o copiarla y subirla a un estado de WhatsApp o a una historia.

    DialogoCompartirPerfil(ctx, perfil, padre=None, imagenes=None).exec()

`imagenes` (opcional) son las imágenes ya cargadas; si no se pasan, se bajan en segundo plano.
"""

import os

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout)

from ... import social as S
from ... import tarjeta_perfil as T
from ...hilos import en_segundo_plano
from .. import iconos
from ..estilos import C, hoja
from . import perfil_comun as PC

ALTO_VISTA = 560


def carpeta_sugerida():
    """Descargas, o Imágenes si no hay."""
    for tipo in (QStandardPaths.DownloadLocation, QStandardPaths.PicturesLocation):
        ruta = QStandardPaths.writableLocation(tipo)
        if ruta and os.path.isdir(ruta):
            return ruta
    return os.path.expanduser("~")


class DialogoCompartirPerfil(QDialog):
    def __init__(self, ctx, perfil, padre=None, imagenes=None):
        super().__init__(padre)
        self.ctx = ctx
        self.p = perfil
        self.imagenes = imagenes
        self.estilo = "color"
        self.imagen = None
        self._cache = {}
        self.ultima_ruta = ""
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle("Compartir perfil · Caudal")
        self.setMinimumWidth(720)

        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(26, 22, 26, 22)
        raiz.setSpacing(28)

        self.vista = QLabel("Preparando la tarjeta…")
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setFixedSize(int(ALTO_VISTA * 9 / 16), ALTO_VISTA)
        self.vista.setStyleSheet(f"background:{C['superficie']};border-radius:18px;color:{C['texto2']};")
        raiz.addWidget(self.vista, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(10)
        t = QLabel("Compartir perfil")
        t.setStyleSheet("font-size:22px;font-weight:900;")
        col.addWidget(t)
        col.addWidget(PC.etiqueta("Una imagen vertical con todo tu perfil, lista para un estado de WhatsApp "
                                  "o una historia de Instagram. Guárdala y súbela desde tu teléfono, o "
                                  "cópiala y pégala donde quieras." if perfil.get("es_mio") else
                                  f"Una imagen vertical con el perfil de {S.nombre_visible(perfil)}, lista "
                                  "para un estado de WhatsApp o una historia de Instagram.",
                                  f"color:{C['texto2']};"))
        col.addSpacing(6)
        col.addWidget(PC.etiqueta("ESTILO", f"color:{C['texto3']};font-size:11px;font-weight:800;"
                                            "letter-spacing:1px;"))
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.grupo = QButtonGroup(self)
        self.botones = {}
        for clave, nombre in T.ESTILOS.items():
            b = QPushButton(nombre)
            b.setObjectName("contorno")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setStyleSheet(f"QPushButton:checked{{background:{C['acento']};color:{C['acento_texto']};"
                            f"border-color:{C['acento']};font-weight:800;}}")
            b.clicked.connect(lambda _=False, c=clave: self.elegir(c))
            self.grupo.addButton(b)
            self.botones[clave] = b
            fila.addWidget(b)
        self.botones["color"].setChecked(True)
        col.addLayout(fila)
        col.addSpacing(10)
        self.bt_guardar = PC.boton("Guardar imagen…", "principal", "descargar", al_pulsar=self.guardar)
        col.addWidget(self.bt_guardar)
        self.bt_copiar = PC.boton("Copiar imagen", "contorno", "pegar", al_pulsar=self.copiar)
        col.addWidget(self.bt_copiar)
        self.bt_carpeta = PC.boton("Abrir carpeta", "contorno", "carpeta", al_pulsar=self.abrir_carpeta)
        col.addWidget(self.bt_carpeta)
        self.estado = PC.etiqueta("", f"color:{C['texto2']};font-size:12.5px;")
        col.addWidget(self.estado)
        col.addStretch(1)
        cerrar = PC.boton("Cerrar", "contorno", al_pulsar=self.accept)
        col.addWidget(cerrar)
        raiz.addLayout(col, 1)
        self._activar(False)

        if imagenes is not None:
            self._pintar()
        else:
            en_segundo_plano(T.traer_imagenes, perfil, ok=self._llegaron, error=lambda _e: self._llegaron({}),
                             dueno=self, urgente=True)

    # ------------------------------------------------------------ la tarjeta
    def _activar(self, si):
        for b in (self.bt_guardar, self.bt_copiar):
            b.setEnabled(si)

    def _llegaron(self, imagenes):
        self.imagenes = imagenes or {}
        self._pintar()

    def elegir(self, clave):
        self.estilo = clave
        self.botones[clave].setChecked(True)
        self.estado.setText("")
        if self.imagenes is not None:
            self._pintar()

    def _pintar(self):
        if self.estilo not in self._cache:
            self._cache[self.estilo] = T.generar(self.p, self.estilo, self.imagenes)
        self.imagen = self._cache[self.estilo]
        pm = QPixmap.fromImage(self.imagen).scaledToHeight(ALTO_VISTA * 2, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(2.0)
        self.vista.setPixmap(pm)
        self._activar(True)

    # ------------------------------------------------------------ acciones
    def guardar(self):
        if self.imagen is None:
            return False
        sugerido = os.path.join(self.ultima_ruta and os.path.dirname(self.ultima_ruta) or carpeta_sugerida(),
                                T.nombre_sugerido(self.p))
        ruta, _filtro = QFileDialog.getSaveFileName(self, "Guardar imagen", sugerido, "Imagen PNG (*.png)")
        if not ruta:
            return False
        if not ruta.lower().endswith(".png"):
            ruta += ".png"
        return self.guardar_en(ruta)

    def guardar_en(self, ruta):
        if self.imagen is None or not self.imagen.save(ruta, "PNG"):
            self.estado.setText("No se pudo guardar la imagen. Prueba con otra carpeta.")
            return False
        self.ultima_ruta = ruta
        self.estado.setText("Imagen guardada en " + os.path.dirname(ruta))
        PC.aviso(self.ctx, "Imagen guardada")
        return True

    def copiar(self):
        if self.imagen is None:
            return
        QGuiApplication.clipboard().setImage(self.imagen)
        self.estado.setText("Imagen copiada. Ya puedes pegarla.")
        PC.aviso(self.ctx, "Imagen copiada")

    def abrir_carpeta(self):
        carpeta = os.path.dirname(self.ultima_ruta) if self.ultima_ruta else carpeta_sugerida()
        QDesktopServices.openUrl(QUrl.fromLocalFile(carpeta))
