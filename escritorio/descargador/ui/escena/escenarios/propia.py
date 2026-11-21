# -*- coding: utf-8 -*-
"""Mi imagen o GIF: el archivo que eligió la persona a pantalla completa, con el mismo motor que los escenarios
con ilustración (paralaje, partículas al mover el ratón, ondas de la música, motas de luz y un brillo que late).
Si es un GIF animado, se reproduce en bucle.

La ruta llega por `fijar_ruta(ruta)` (el escenario lo crea `escenarios.crear(clave)` sin argumentos): ventana.py
la llama ANTES de crear el escenario con `ajustes["escena_imagen_propia"]`. Sin imagen se pinta un degradado.
"""
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QMovie, QPainter

from .imagen_motor import Brillo, EscenarioImagen, Luciernagas, Ondas

_RUTA = ""                  # la fija fijar_ruta(); "" = sin imagen propia
ANCHO_MAX = 2560            # una imagen más ancha se reduce una sola vez al cargarla


def fijar_ruta(ruta):
    global _RUTA
    _RUTA = str(ruta) if ruta else ""


def _cargar_imagen(ruta):
    if not ruta or not os.path.isfile(ruta):
        return QImage()
    img = QImage(ruta)
    if not img.isNull() and img.width() > ANCHO_MAX:
        img = img.scaledToWidth(ANCHO_MAX, Qt.SmoothTransformation)
    return img


class EscenarioPropia(EscenarioImagen):
    NOMBRE = "Mi imagen o GIF"
    ACENTO = "#C8A2FF"
    SEMILLA = 57
    INTERACCION = ("chispa", ("#FFFFFF", "#E7D4FF"))
    SUPER = 1

    def preparar(self):
        self._ruta = _RUTA
        self._movie = None
        es_gif = self._ruta.lower().endswith(".gif") and os.path.isfile(self._ruta)
        if es_gif:
            mv = QMovie(self._ruta)
            mv.setCacheMode(QMovie.CacheAll)
            if mv.isValid() and mv.frameCount() != 1:
                self._movie = mv
        super().preparar()
        if self._movie is not None:
            self._movie.jumpToFrame(0)
            self._img = self._movie.currentImage()
            self.iw, self.ih = max(1, self._img.width()), max(1, self._img.height())
        else:
            self._img = _cargar_imagen(self._ruta)
            self.iw, self.ih = max(1, self._img.width()), max(1, self._img.height())
        if self._img.isNull():
            self.iw, self.ih = 1920, 1080          # sin imagen: degradado, con los mismos efectos

    def crear_efectos(self):
        # coordenadas relativas al tamaño de la imagen, que aún no se conoce: se usan fracciones de 1000x1000
        return ()

    def _efectos_propios(self):
        iw, ih = self.iw, self.ih
        return [
            Brillo(1, punto=(iw * 0.5, ih * 0.92), radio=max(iw, ih) * 0.40, color="#C8A2FF", modo="latido",
                   alfa=0.25, dureza=0.2),
            Luciernagas(2, rect=(0, 0, iw, ih), n=36, radio=max(iw, ih) * 0.004, color="#FFF4E6", parpadeo=1,
                        alfa=0.6, sube=0.02),
            Ondas(3, x0=iw * 0.15, y=ih * 0.95, ancho=iw * 0.70, alto=ih * 0.08),
        ]

    def pintar_estatico(self, p, W, H):
        if not self.efectos:
            self.efectos = self._efectos_propios()
            for ef in self.efectos:
                ef.unir(self)
        if self._img.isNull():
            self._geometria(W, H)
            g = QLinearGradient(0, 0, 0, H)
            g.setColorAt(0, QColor("#15151c"))
            g.setColorAt(1, QColor("#0b0b10"))
            p.fillRect(QRectF(0, 0, W, H), g)
            return
        super().pintar_estatico(p, W, H)
        # velo suave abajo para que se lean la letra y la barra
        self.velo(p, QRectF(0, H * 0.55, W, H * 0.45), QColor(8, 8, 12, 0), QColor(8, 8, 12, 150))

    def pintar_animado(self, p, W, H, t):
        if self._movie is not None:
            if self._movie.state() != QMovie.Running:
                self._movie.start()
            pm = self._movie.currentPixmap()
            if not pm.isNull():
                p.save()
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                p.drawPixmap(QRectF(self._ox, self._oy, self.iw * self.escala, self.ih * self.escala), pm,
                             QRectF(pm.rect()))
                p.restore()
        super().pintar_animado(p, W, H, t)

    def hideEvent(self, ev):
        if self._movie is not None:
            self._movie.setPaused(True)
        super().hideEvent(ev)
