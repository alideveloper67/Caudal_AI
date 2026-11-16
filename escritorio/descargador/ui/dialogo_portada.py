# -*- coding: utf-8 -*-
"""Portada propia de una lista: portada grande editable, diálogo para elegirla y ayudas.

Solo las listas propias (tipo «mi_lista») se pueden personalizar: «Tus me gusta», lo
descargado, los mixes automáticos y las listas de otras personas o de YouTube no.
"""

import os

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from .. import social
from . import iconos
from .componentes import Portada
from .estilos import C

EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")


def es_editable(el_o_tipo):
    """Solo las listas propias aceptan portada personalizada."""
    tipo = el_o_tipo.get("tipo") if isinstance(el_o_tipo, dict) else el_o_tipo
    return tipo == "mi_lista"


def ruta_de_imagen(mime):
    """La primera imagen local soltada (jpg/png/webp), o ""."""
    if mime is None or not mime.hasUrls():
        return ""
    for u in mime.urls():
        if u.isLocalFile() and u.toLocalFile().lower().endswith(EXTENSIONES) \
                and os.path.isfile(u.toLocalFile()):
            return u.toLocalFile()
    return ""


def _previa(origen, lado):
    """QImage cuadrada de esquinas redondeadas con el mismo recorte que se guardará."""
    img = social.recortar_cuadrado(social._cargar_imagen(origen), lado * 2)
    img = img.scaled(lado, lado, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    sal = QImage(lado, lado, QImage.Format_ARGB32_Premultiplied)
    sal.fill(Qt.transparent)
    p = QPainter(sal)
    p.setRenderHint(QPainter.Antialiasing, True)
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(0, 0, lado, lado), 16, 16)
    p.setClipPath(ruta)
    p.drawImage(0, 0, img)
    p.end()
    return sal


class PortadaEditable(Portada):
    """Portada grande de una lista propia: botón discreto siempre, «Cambiar portada» al
    pasar el ratón, clic para elegir y se le puede soltar una imagen encima."""

    pedir_cambio = Signal()
    imagen_soltada = Signal(str)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Cambiar portada")
        self._encima = False
        self._soltando = False

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.pedir_cambio.emit()

    def dragEnterEvent(self, e):
        if ruta_de_imagen(e.mimeData()):
            self._soltando = True
            self.update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._soltando = False
        self.update()

    def dropEvent(self, e):
        self._soltando = False
        self.update()
        ruta = ruta_de_imagen(e.mimeData())
        if ruta:
            e.acceptProposedAction()
            self.imagen_soltada.emit(ruta)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(0, 0, self.ancho, self.alto)
        marco = QPainterPath()
        marco.addRoundedRect(r, self.radio, self.radio)
        if self._encima or self._soltando:
            p.fillPath(marco, QColor(6, 7, 10, 150))
            lado = 34
            p.drawPixmap(int((self.ancho - lado) / 2), int(self.alto / 2 - lado + 2),
                         iconos.pixmap("editar", lado, "#FFFFFF"))
            f = QFont(self.font())
            f.setPixelSize(14)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor("#FFFFFF"))
            texto = "Suelta la imagen aquí" if self._soltando else "Cambiar portada"
            p.drawText(QRectF(8, self.alto / 2 + 8, self.ancho - 16, 24), Qt.AlignCenter, texto)
        else:
            # insignia discreta en la esquina
            d = 30
            x, y = self.ancho - d - 10, self.alto - d - 10
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(6, 7, 10, 150))
            p.drawEllipse(QRectF(x, y, d, d))
            p.drawPixmap(int(x + (d - 16) / 2), int(y + (d - 16) / 2),
                         iconos.pixmap("editar", 16, "#FFFFFF"))
        if self._soltando:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(C["acento"]), 3))
            p.drawPath(marco)


class DialogoPortada(QDialog):
    """Elige la imagen, la ve cuadrada y con esquinas redondeadas, y guarda o cancela."""

    LADO = 280

    def __init__(self, nombre="", origen=None, hay_propia=False, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Cambiar portada")
        self.setMinimumWidth(420)
        self.setAcceptDrops(True)
        self.origen = None
        v = QVBoxLayout(self)
        v.setContentsMargins(26, 22, 26, 20)
        v.setSpacing(12)
        t = QLabel("Cambiar portada")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        s = QLabel(f"Elige la imagen que quieras para «{nombre}»." if nombre
                   else "Elige la imagen que quieras para tu lista.")
        s.setObjectName("secundario")
        s.setWordWrap(True)
        v.addWidget(s)
        self.vista = QLabel()
        self.vista.setFixedSize(self.LADO, self.LADO)
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setCursor(Qt.PointingHandCursor)
        self.vista.mousePressEvent = lambda e: self._elegir()
        v.addWidget(self.vista, 0, Qt.AlignHCenter)
        self.estado = QLabel("Se recorta en cuadrado, al centro. También puedes arrastrar una "
                             "imagen hasta aquí.")
        self.estado.setObjectName("secundario")
        self.estado.setWordWrap(True)
        self.estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.estado)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.bt_elegir = QPushButton("  Elegir imagen…")
        self.bt_elegir.setObjectName("contorno")
        self.bt_elegir.setIcon(iconos.icono("carpeta", 16, C["texto"]))
        self.bt_elegir.setCursor(Qt.PointingHandCursor)
        self.bt_elegir.clicked.connect(self._elegir)
        fila.addWidget(self.bt_elegir)
        fila.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("contorno")
        cancelar.setCursor(Qt.PointingHandCursor)
        cancelar.clicked.connect(self.reject)
        fila.addWidget(cancelar)
        self.bt_guardar = QPushButton("Guardar")
        self.bt_guardar.setObjectName("principal")
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.setEnabled(False)
        self.bt_guardar.clicked.connect(self.accept)
        fila.addWidget(self.bt_guardar)
        v.addLayout(fila)
        self._vacio()
        if origen:
            self.poner(origen)

    def _vacio(self):
        self.vista.setPixmap(self._marcador())

    def _marcador(self):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(self.LADO, self.LADO)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(1, 1, self.LADO - 2, self.LADO - 2), 16, 16)
        p.fillPath(ruta, QColor(C["superficie2"]))
        pen = QPen(QColor(C["borde_claro"]), 2, Qt.DashLine)
        p.setPen(pen)
        p.drawPath(ruta)
        p.drawPixmap(self.LADO // 2 - 22, self.LADO // 2 - 40, iconos.pixmap("editar", 44,
                                                                              C["texto3"]))
        p.setPen(QColor(C["texto2"]))
        f = QFont(self.font())
        f.setPixelSize(14)
        p.setFont(f)
        p.drawText(QRectF(0, self.LADO / 2 + 18, self.LADO, 24), Qt.AlignCenter,
                   "Pulsa para elegir una imagen")
        p.end()
        return pm

    def _elegir(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige la portada", "", social.FILTRO_IMAGEN)
        if ruta:
            self.poner(ruta)

    def poner(self, ruta):
        from PySide6.QtGui import QPixmap
        try:
            img = _previa(ruta, self.LADO)
        except social.ErrorNube as e:
            self.estado.setText(str(e))
            return False
        self.vista.setPixmap(QPixmap.fromImage(img))
        self.origen = ruta
        self.estado.setText("Así se verá. Pulsa «Guardar» para ponerla.")
        self.bt_guardar.setEnabled(True)
        return True

    def dragEnterEvent(self, e):
        if ruta_de_imagen(e.mimeData()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        ruta = ruta_de_imagen(e.mimeData())
        if ruta:
            e.acceptProposedAction()
            self.poner(ruta)


def cambiar_portada(ctx, lista_id, padre=None, ruta=None):
    """Abre el diálogo (con `ruta` ya cargada si la imagen se soltó) y guarda si se acepta.
    Devuelve True si cambió."""
    if not ctx.coleccion.lista(lista_id):
        return False
    lista = ctx.coleccion.lista(lista_id)
    d = DialogoPortada(lista.get("nombre") or "", origen=ruta,
                       hay_propia=bool(ctx.coleccion.portada_personalizada(lista_id)),
                       padre=padre)
    if not d.exec() or not d.origen:
        return False
    return guardar_portada(ctx, lista_id, d.origen)


def guardar_portada(ctx, lista_id, origen):
    try:
        ctx.coleccion.poner_portada_lista(lista_id, origen)
    except ValueError as e:
        try:
            ctx.aviso.emit(str(e))
        except Exception:  # noqa: BLE001
            pass
        return False
    ctx.listas_cambio.emit()
    try:
        ctx.aviso.emit("Portada cambiada")
    except Exception:  # noqa: BLE001
        pass
    return True


def quitar_portada(ctx, lista_id):
    ctx.coleccion.quitar_portada_lista(lista_id)
    ctx.listas_cambio.emit()
    try:
        ctx.aviso.emit("Portada personalizada quitada")
    except Exception:  # noqa: BLE001
        pass


def agregar_al_menu(menu, ctx, lista_id, padre=None):
    """«Cambiar portada…» y, si hay una propia, «Quitar portada personalizada»."""
    menu.addAction(iconos.icono("editar", 16, C["texto2"]), "Cambiar portada…",
                   lambda: cambiar_portada(ctx, lista_id, padre))
    if ctx.coleccion.portada_personalizada(lista_id):
        menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Quitar portada personalizada",
                       lambda: quitar_portada(ctx, lista_id))
