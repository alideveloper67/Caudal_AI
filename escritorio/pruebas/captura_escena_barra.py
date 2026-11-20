# -*- coding: utf-8 -*-
"""Captura visual de la barra mini: se pinta sobre un degradado oscuro simulado
y se guarda en pruebas/capturas_escena/barra.png. No usa la plataforma offscreen
(sin ella no hay fuentes)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPixmap,  # noqa: E402
                           QRadialGradient)
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.barra import ANCHO, ALTO, BarraMini  # noqa: E402

SALIDA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena")


def portada_ejemplo():
    """Carátula de mentira: un degradado con un círculo, para ver la miniatura."""
    img = QImage(300, 300, QImage.Format_ARGB32)
    img.fill(QColor("#E8577E"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    g = QLinearGradient(QPointF(0, 0), QPointF(300, 300))
    g.setColorAt(0.0, QColor("#FF9EC0"))
    g.setColorAt(1.0, QColor("#3B2A6B"))
    p.fillRect(img.rect(), g)
    p.setBrush(QColor(255, 255, 255, 90))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(150, 150), 80, 80)
    p.end()
    return img


def fondo(ancho, alto):
    """Degradado #1A0F2E -> #5A1E4A con un resplandor suave, como la escena."""
    pm = QPixmap(ancho, alto)
    p = QPainter(pm)
    g = QLinearGradient(QPointF(0, 0), QPointF(ancho, alto))
    g.setColorAt(0.0, QColor("#1A0F2E"))
    g.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(QRectF(0, 0, ancho, alto), g)
    r = QRadialGradient(QPointF(ancho * 0.7, alto * 0.4), ancho * 0.5)
    r.setColorAt(0.0, QColor(232, 87, 126, 60))
    r.setColorAt(1.0, QColor(232, 87, 126, 0))
    p.fillRect(QRectF(0, 0, ancho, alto), r)
    p.end()
    return pm


def main():
    app = QApplication.instance() or QApplication([])
    os.makedirs(SALIDA_DIR, exist_ok=True)

    w = BarraMini()
    w.resize(ANCHO, ALTO)
    w.poner({"titulo": "Cosas que no se olvidan", "artista": "Lúa Serrano"})
    w.poner_portada(portada_ejemplo())
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.fijar_progreso(83, 225)
    w.fijar_estado("sonando")
    w.fijar_aleatorio(True)
    w.fijar_repetir("todo")
    w.fijar_fondo("video")

    pm = fondo(ANCHO, ALTO)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    w.render(p, QPoint(0, 0))
    p.end()

    ruta = os.path.join(SALIDA_DIR, "barra.png")
    pm.save(ruta, "PNG")
    print(ruta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
