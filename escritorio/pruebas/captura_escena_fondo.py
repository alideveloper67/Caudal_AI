# -*- coding: utf-8 -*-
"""Captura de la pieza «fondo»: con carátula de ejemplo y sin carátula.

No usa la plataforma offscreen (si no, no hay fuentes). Guarda en pruebas/capturas_escena/.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.estilo import BRILLO, DOMINANTE, SEGUNDO
from descargador.ui.escena.fondo import FondoAmbiente

ANCHO, ALTO = 1600, 900
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena")


def caratula_ejemplo():
    """Carátula de ejemplo: círculos de colores sobre un fondo oscuro."""
    img = QImage(900, 900, QImage.Format_ARGB32)
    img.fill(QColor(24, 18, 40))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    circulos = [
        (120, 130, 300, "#E8577E"),
        (520, 180, 260, "#3B9BE8"),
        (250, 560, 340, "#F2C14E"),
        (640, 620, 220, "#5ED39B"),
        (430, 380, 150, "#B06CF0"),
    ]
    for x, y, d, color in circulos:
        p.setBrush(QColor(color))
        p.drawEllipse(x, y, d, d)
    p.end()
    return img


def fondo_fijo():
    """Degradado #1A0F2E -> #5A1E4A, que se pinta debajo como pide la guía de capturas."""
    pix = QPixmap(ANCHO, ALTO)
    p = QPainter(pix)
    grad = QLinearGradient(QPointF(0, 0), QPointF(ANCHO, ALTO))
    grad.setColorAt(0.0, QColor("#1A0F2E"))
    grad.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(0, 0, ANCHO, ALTO, grad)
    p.end()
    return pix


def capturar(nombre, portada):
    app = QApplication.instance() or QApplication([])
    w = FondoAmbiente()
    w.resize(ANCHO, ALTO)
    w.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
    if portada is not None:
        w.poner_portada(portada)
        time.sleep(1.4)           # que termine el fundido de 1.2 s
    else:
        w.poner_portada(None)
        time.sleep(1.4)

    lienzo = fondo_fijo()
    p = QPainter(lienzo)
    w.render(p, QPoint(0, 0))
    p.end()

    ruta = os.path.join(CARPETA, nombre + ".png")
    os.makedirs(CARPETA, exist_ok=True)
    lienzo.save(ruta, "PNG")
    print(ruta)
    return ruta


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    capturar("fondo", caratula_ejemplo())
    capturar("fondo_sin_portada", None)
