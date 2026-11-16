# -*- coding: utf-8 -*-
"""Ajustes › «Fondo de Caudal»: elegir la imagen, cuánto se ve y cuánto se desenfoca.
Solo aparece para quien puede (Donador o Fundador de Caudal). Los cambios se ven en vivo en
toda la aplicación y se guardan (en la nube y en esta PC) al soltar el deslizador."""

import os

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QSlider, QVBoxLayout, QWidget)

from .. import fondo as F
from .. import nube
from .. import social as S
from .estilos import ALFA_BARRA, ALFA_PANEL, ALFA_TARJETA, C
from .fondo_capa import Renderizador, _con_alfa


class Insignia(QWidget):
    """«Donador de Caudal» en dorado o «Fundador de Caudal» en violeta."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.texto = ""
        self.setFixedHeight(26)
        self.hide()

    @staticmethod
    def _fuente():
        f = QFont("Segoe UI")
        f.setPixelSize(12)
        f.setBold(True)
        return f

    def poner(self, texto):
        self.texto = texto or ""
        self.setVisible(bool(self.texto))
        self.setAccessibleName(self.texto)
        self.setFixedWidth(QFontMetrics(self._fuente()).horizontalAdvance(self.texto) + 50
                           if self.texto else 0)
        self.update()

    def paintEvent(self, _e):
        if not self.texto:
            return
        fundador = self.texto == F.TITULO_FUNDADOR
        a, b = ("#7C5CFF", "#B794F6") if fundador else ("#F5C542", "#FFB454")
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor(a))
        g.setColorAt(1, QColor(b))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        # una estrella pequeña, como el resto de títulos de Caudal
        c = r.left() + 15, r.center().y()
        est = QPainterPath()
        import math
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = 5.2 if i % 2 == 0 else 2.3
            pt = (c[0] + rad * math.cos(ang), c[1] + rad * math.sin(ang))
            est.moveTo(*pt) if i == 0 else est.lineTo(*pt)
        est.closeSubpath()
        p.setBrush(QColor("#FFFFFF" if fundador else "#3A2600"))
        p.drawPath(est)
        p.setFont(self._fuente())
        p.setPen(QColor("#FFFFFF" if fundador else "#3A2600"))
        p.drawText(r.adjusted(26, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, self.texto)
        p.end()


class VistaPreviaFondo(QWidget):
    """16:9 con esquinas redondeadas: el efecto real y una Caudal en miniatura encima."""

    def __init__(self, gestor, padre=None):
        super().__init__(padre)
        self.gestor = gestor
        self.rend = Renderizador()
        self.soltando = False
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)
        self.setAccessibleName("Vista previa del fondo")
        gestor.cambiado.connect(lambda _a: self.update())

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return int(w * 9 / 16)

    def sizeHint(self):
        return QSize(640, 360)

    def paintEvent(self, _e):
        g = self.gestor
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        marco = QPainterPath()
        marco.addRoundedRect(r, 16, 16)
        p.setClipPath(marco)
        self.rend.pintar(p, r, g.imagen, g.serie, g.visible, g.desenfoque)
        w, h = r.width(), r.height()
        m = max(8.0, w * 0.014)
        barra_h = h * 0.15
        lat = QRectF(r.left() + m, r.top() + m, w * 0.22, h - barra_h - m * 2.6)
        cen = QRectF(lat.right() + m, lat.top(), r.right() - m - lat.right() - m, lat.height())
        rad = max(6.0, h * 0.035)
        p.setPen(Qt.NoPen)
        for caja in (lat, cen):
            p.setBrush(_con_alfa(C["panel"], 255 * ALFA_PANEL))
            p.drawRoundedRect(caja, rad, rad)
        ac = QColor(C["acento"])
        # barra lateral
        for i in range(4):
            y = lat.top() + h * 0.05 + i * h * 0.085
            p.setBrush(ac if i == 0 else _con_alfa(C["superficie3"], 230))
            p.drawRoundedRect(QRectF(lat.left() + w * 0.014, y, h * 0.045, h * 0.045), 3, 3)
            p.setBrush(QColor(C["texto"]) if i == 0 else QColor(C["texto3"]))
            p.drawRoundedRect(QRectF(lat.left() + w * 0.014 + h * 0.07, y + h * 0.014,
                                     lat.width() * 0.5, h * 0.018), 2, 2)
        # título y filas de canciones (tarjetas casi opacas)
        p.setBrush(QColor(C["texto"]))
        p.drawRoundedRect(QRectF(cen.left() + w * 0.02, cen.top() + h * 0.05, cen.width() * 0.34,
                                 h * 0.034), 3, 3)
        p.setBrush(_con_alfa(C["texto2"], 200))
        p.drawRoundedRect(QRectF(cen.left() + w * 0.02, cen.top() + h * 0.115, cen.width() * 0.2,
                                 h * 0.018), 2, 2)
        for i in range(3):
            y = cen.top() + h * 0.19 + i * h * 0.105
            if y + h * 0.085 > cen.bottom():
                break
            fila = QRectF(cen.left() + w * 0.02, y, cen.width() - w * 0.04, h * 0.085)
            p.setBrush(_con_alfa(C["superficie2" if i == 0 else "superficie"], 255 * ALFA_TARJETA))
            p.drawRoundedRect(fila, 6, 6)
            p.setBrush(_con_alfa(C["superficie3"], 230))
            p.drawRoundedRect(QRectF(fila.left() + 6, fila.top() + h * 0.014, h * 0.057,
                                     h * 0.057), 4, 4)
            p.setBrush(ac if i == 0 else QColor(C["texto2"]))
            p.drawRoundedRect(QRectF(fila.left() + h * 0.1, fila.center().y() - h * 0.01,
                                     fila.width() * 0.34, h * 0.02), 2, 2)
        # barra del reproductor
        bar = QRectF(r.left() + m, r.bottom() - barra_h - m * 0.6, w - 2 * m, barra_h)
        p.setBrush(_con_alfa(C["fondo"], 255 * ALFA_BARRA))
        p.drawRoundedRect(bar, rad, rad)
        cx = bar.center().x()
        p.setBrush(QColor(C["texto"]))
        p.drawEllipse(QRectF(cx - h * 0.035, bar.top() + h * 0.02, h * 0.07, h * 0.07))
        p.setBrush(_con_alfa(C["superficie3"], 240))
        lin = QRectF(cx - w * 0.2, bar.bottom() - h * 0.04, w * 0.4, 3)
        p.drawRoundedRect(lin, 1.5, 1.5)
        p.setBrush(QColor(C["acento_alto"]))
        p.drawRoundedRect(QRectF(lin.left(), lin.top(), lin.width() * 0.4, 3), 1.5, 1.5)
        p.setClipping(False)
        # el marco, finísimo
        p.setBrush(Qt.NoBrush)
        if self.soltando:
            pen = QPen(QColor(C["acento"]), 2, Qt.DashLine)
        else:
            pen = QPen(_con_alfa(C["borde_claro"], 200), 1)
        p.setPen(pen)
        p.drawRoundedRect(r, 16, 16)
        if g.imagen is None:
            p.setPen(QColor(C["texto2"]))
            f = QFont(self.font())
            f.setPixelSize(13)
            f.setBold(True)
            p.setFont(f)
            p.drawText(QRectF(cen.left(), cen.top() + h * 0.12, cen.width(), cen.height() * 0.6),
                       Qt.AlignCenter, "Elige o suelta aquí una imagen\npara ver cómo queda")
        p.end()


class SeccionFondo(QFrame):
    def __init__(self, gestor, padre=None):
        super().__init__(padre)
        self.gestor = gestor
        self.setObjectName("caja")
        self.setAcceptDrops(True)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(12)

        cab = QHBoxLayout()
        t = QLabel("Fondo de Caudal")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.insignia = Insignia()
        cab.addWidget(self.insignia)
        v.addLayout(cab)
        ayuda = QLabel("Pon una imagen detrás de toda la aplicación. Se ve suave y transparente, "
                       "para que todo siga leyéndose bien.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)

        self.vista = VistaPreviaFondo(gestor)
        v.addWidget(self.vista)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.bt_elegir = QPushButton("Elegir imagen…")
        self.bt_elegir.setObjectName("principal")
        self.bt_elegir.setCursor(Qt.PointingHandCursor)
        self.bt_elegir.clicked.connect(self.elegir)
        self.bt_quitar = QPushButton("Quitar fondo")
        self.bt_quitar.setObjectName("contorno")
        self.bt_quitar.setCursor(Qt.PointingHandCursor)
        self.bt_quitar.clicked.connect(self.quitar)
        fila.addWidget(self.bt_elegir)
        fila.addWidget(self.bt_quitar)
        fila.addStretch(1)
        v.addLayout(fila)

        self.s_visible, self.et_visible = self._deslizador(
            v, "Cuánto se ve", "Qué tanto de la imagen se deja ver detrás de la aplicación.",
            F.VISIBLE_MIN, F.VISIBLE_MAX, gestor.visible, lambda n: f"{n} %")
        self.s_desen, self.et_desen = self._deslizador(
            v, "Desenfoque", "Suaviza la imagen para que no distraiga.",
            F.DESENFOQUE_MIN, F.DESENFOQUE_MAX, gestor.desenfoque, lambda n: str(n))
        self.s_visible.valueChanged.connect(self._mover)
        self.s_desen.valueChanged.connect(self._mover)
        self.s_visible.sliderReleased.connect(self._soltado)
        self.s_desen.sliderReleased.connect(self._soltado)
        self._t_guardar = QTimer(self)          # para el teclado y la rueda: guarda sin soltar nada
        self._t_guardar.setSingleShot(True)
        self._t_guardar.setInterval(600)
        self._t_guardar.timeout.connect(self._guardar)

        self.estado = QLabel("También puedes arrastrar una imagen hasta aquí (jpg, png o webp).")
        self.estado.setObjectName("ayuda")
        self.estado.setWordWrap(True)
        v.addWidget(self.estado)

        gestor.cambiado.connect(self._refrescar)
        gestor.permiso_cambiado.connect(lambda _p: self._refrescar())
        self._refrescar()

    def _deslizador(self, v, titulo, ayuda, minimo, maximo, valor, formato):
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(16)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        a = QLabel(titulo)
        a.setStyleSheet("font-size:14px;font-weight:600;")
        b = QLabel(ayuda)
        b.setObjectName("secundario")
        b.setWordWrap(True)
        textos.addWidget(a)
        textos.addWidget(b)
        h.addLayout(textos, 1)
        s = QSlider(Qt.Horizontal)
        s.setRange(minimo, maximo)
        s.setValue(valor)
        s.setFixedWidth(240)
        s.setCursor(Qt.PointingHandCursor)
        s.setAccessibleName(titulo)
        et = QLabel(formato(valor))
        et.setMinimumWidth(44)
        et.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        et.setStyleSheet("font-weight:700;")
        s._formato = formato
        h.addWidget(s)
        h.addWidget(et)
        v.addWidget(caja)
        return s, et

    # ------------------------------------------------------------ estado
    def _refrescar(self):
        g = self.gestor
        self.setVisible(g.puede)
        self.insignia.poner(g.titulo if g.puede else "")
        self.bt_quitar.setEnabled(g.activo)
        for s, et, valor in ((self.s_visible, self.et_visible, g.visible),
                             (self.s_desen, self.et_desen, g.desenfoque)):
            s.setEnabled(g.activo)
            if s.value() != valor:
                s.blockSignals(True)
                s.setValue(valor)
                s.blockSignals(False)
            et.setText(s._formato(valor))

    def _mover(self, _n):
        # en vivo: se ve ya en toda la aplicación
        self.gestor.poner_valores(self.s_visible.value(), self.s_desen.value())
        if not (self.s_visible.isSliderDown() or self.s_desen.isSliderDown()):
            self._t_guardar.start()

    def _soltado(self):
        self._t_guardar.stop()
        self._guardar()

    def _guardar(self):
        self.gestor.guardar_ajustes()

    # ------------------------------------------------------------ acciones
    def elegir(self):
        inicio = os.path.join(os.path.expanduser("~"), "Pictures")
        if not os.path.isdir(inicio):
            inicio = os.path.expanduser("~")
        ruta, _ = QFileDialog.getOpenFileName(self, "Elige la imagen de tu fondo", inicio,
                                              S.FILTRO_IMAGEN)
        if ruta:
            self.poner(ruta)

    def poner(self, ruta):
        try:
            self.gestor.poner_imagen(ruta)
        except nube.ErrorNube as e:
            self.estado.setText(S.explicar(e, "poner ese fondo"))
            return False
        self.estado.setText("Listo. Mueve los deslizadores para dejarlo a tu gusto.")
        return True

    def quitar(self):
        self.gestor.quitar()
        self.estado.setText("Fondo quitado. Caudal vuelve a su aspecto de siempre.")

    # ------------------------------------------------------------ arrastrar y soltar
    @staticmethod
    def _imagenes(e):
        d = e.mimeData()
        if not d.hasUrls():
            return []
        return [u.toLocalFile() for u in d.urls() if u.isLocalFile() and F.es_imagen(u.toLocalFile())]

    def dragEnterEvent(self, e):
        if self._imagenes(e):
            self.vista.soltando = True
            self.vista.update()
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.vista.soltando = False
        self.vista.update()

    def dropEvent(self, e):
        self.vista.soltando = False
        self.vista.update()
        archivos = self._imagenes(e)
        if archivos:
            self.poner(archivos[0])
            e.acceptProposedAction()
