# -*- coding: utf-8 -*-
"""La capa de «Fondo de Caudal»: se pinta detrás de todo el contenido de la ventana.

Color base de la app + la imagen «cubriendo» todo el espacio con poca opacidad (y, si se
pide, desenfocada) + una viñeta que oscurece los bordes y la parte de abajo + un toque
muy suave del color de acento. La imagen ya escalada y desenfocada se guarda en una caché:
al pintar solo se compone, y al cambiar el tamaño se re-escala una vez, con una pausa.
"""

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget)

from .estilos import C


def _con_alfa(color, alfa):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alfa))))
    return c


def escena_cubierta(img, tam, desenfoque):
    """La imagen «cubriendo» `tam` (recorte centrado) y, si se pide, desenfocada (0–20).
    El desenfoque se hace sobre una copia a mitad de tamaño y luego se agranda: barato."""
    w, h = max(1, tam.width()), max(1, tam.height())
    if desenfoque <= 0:
        c = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return QPixmap.fromImage(c.copy((c.width() - w) // 2, (c.height() - h) // 2, w, h))
    hw, hh = max(2, w // 2), max(2, h // 2)
    radio = desenfoque * 1.1
    margen = int(radio * 2) + 2
    c = img.scaled(hw, hh, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    c = c.copy((c.width() - hw) // 2, (c.height() - hh) // 2, hw, hh)
    # se estira un poco hacia los bordes para que el desenfoque no deje orillas claras
    grande = c.scaled(hw + 2 * margen, hh + 2 * margen, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    escena = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(grande))
    efecto = QGraphicsBlurEffect()
    efecto.setBlurRadius(radio)
    efecto.setBlurHints(QGraphicsBlurEffect.QualityHint)
    item.setGraphicsEffect(efecto)
    escena.addItem(item)
    salida = QImage(grande.size(), QImage.Format_ARGB32_Premultiplied)
    salida.fill(Qt.transparent)
    p = QPainter(salida)
    escena.render(p, QRectF(salida.rect()), QRectF(salida.rect()))
    p.end()
    corte = salida.copy(margen, margen, hw, hh).scaled(w, h, Qt.IgnoreAspectRatio,
                                                       Qt.SmoothTransformation)
    return QPixmap.fromImage(corte)


class Renderizador:
    """Pinta el fondo en cualquier rectángulo (la ventana o la vista previa)."""

    def __init__(self):
        self._pm = None
        self._clave = None

    def _escena(self, img, serie, rect, desenfoque, estirar):
        tam = QSize(max(1, int(rect.width())), max(1, int(rect.height())))
        clave = (serie, tam.width(), tam.height(), desenfoque)
        if clave != self._clave:
            if estirar and self._pm is not None:
                return self._pm                 # mientras se arrastra el borde: se estira la anterior
            self._pm = escena_cubierta(img, tam, desenfoque)
            self._clave = clave
        return self._pm

    def pintar(self, p, rect, img, serie, visible, desenfoque, estirar=False):
        """`visible` es el porcentaje (5–60) de imagen que se deja ver."""
        rect = QRectF(rect)
        w, h = rect.width(), rect.height()
        base = QColor(C["fondo"])
        p.save()
        p.setClipRect(rect, Qt.IntersectClip)
        p.translate(rect.topLeft())
        r = QRectF(0, 0, w, h)
        # el color de la app, con un cambio de tono casi imperceptible de arriba abajo
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(C["panel"]))
        g.setColorAt(1, base)
        p.fillRect(r, g)
        v = max(0.0, min(1.0, visible / 100.0))
        if img is not None and not img.isNull():
            pm = self._escena(img, serie, rect, desenfoque, estirar)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(v)
            p.drawPixmap(r.toRect(), pm)
            p.setOpacity(1.0)
        # un velo que crece con la imagen: cuanto más se ve, más se cuida el texto
        p.fillRect(r, _con_alfa(base, 255 * min(0.3, v * 0.30)))
        # viñeta: oscurece hacia los bordes y hacia abajo (profundidad y lectura)
        d = max(w, h)
        rad = QRadialGradient(w * 0.5, h * 0.42, d * 0.80)
        rad.setColorAt(0.0, _con_alfa(base, 0))
        rad.setColorAt(0.55, _con_alfa(base, 0))
        rad.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, rad)
        baja = QLinearGradient(0, h * 0.50, 0, h)
        baja.setColorAt(0.0, _con_alfa(base, 0))
        baja.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, baja)
        # un soplo del color de acento desde la esquina de arriba
        ac = QColor(C["acento"])
        brillo = QRadialGradient(w * 0.88, -h * 0.05, d * 0.70)
        brillo.setColorAt(0.0, _con_alfa(ac, 30))
        brillo.setColorAt(1.0, _con_alfa(ac, 0))
        p.fillRect(r, brillo)
        lado = QLinearGradient(0, 0, w, h)
        lado.setColorAt(0.0, _con_alfa(ac, 12))
        lado.setColorAt(0.6, _con_alfa(ac, 0))
        p.fillRect(r, lado)
        p.restore()


class CapaFondo(QWidget):
    """Hija de la ventana, siempre al fondo; no recibe clics."""

    def __init__(self, gestor, padre):
        super().__init__(padre)
        self.gestor = gestor
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.rend = Renderizador()
        self._redimensionando = False
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(140)
        self._t.timeout.connect(self._fin_redimension)
        gestor.cambiado.connect(lambda _a: self.update())

    def _fin_redimension(self):
        self._redimensionando = False
        self.update()

    def resizeEvent(self, e):
        self._redimensionando = True
        self._t.start()
        super().resizeEvent(e)

    def paintEvent(self, _e):
        g = self.gestor
        p = QPainter(self)
        self.rend.pintar(p, QRectF(self.rect()), g.imagen, g.serie, g.visible, g.desenfoque,
                         estirar=self._redimensionando)
        p.end()
