# -*- coding: utf-8 -*-
"""Captura de la TarjetaCancion sobre un fondo oscuro simulado. No usa la plataforma offscreen."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.tarjeta import TarjetaCancion

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena")
SALIDA = os.path.join(CARPETA, "tarjeta.png")


def portada_ejemplo(lado=600):
    """Carátula de ejemplo: un atardecer con sol y colinas, pintado con QPainter."""
    img = QImage(lado, lado, QImage.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    cielo = QLinearGradient(QPointF(0, 0), QPointF(0, lado))
    cielo.setColorAt(0.0, QColor("#FF7A59"))
    cielo.setColorAt(0.55, QColor("#E8577E"))
    cielo.setColorAt(1.0, QColor("#3B2A6B"))
    p.fillRect(QRectF(0, 0, lado, lado), cielo)
    p.setBrush(QColor("#FFD27A"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(lado * 0.36, lado * 0.22, lado * 0.28, lado * 0.28))
    p.setBrush(QColor("#2A1B4D"))
    p.drawEllipse(QRectF(-lado * 0.2, lado * 0.62, lado * 1.0, lado * 0.6))
    p.setBrush(QColor("#120B26"))
    p.drawEllipse(QRectF(lado * 0.25, lado * 0.74, lado * 1.1, lado * 0.5))
    p.end()
    return img


def captura(ancho, alto, salida):
    margen = 20
    lienzo = QPixmap(ancho + 2 * margen, alto + 2 * margen)

    fondo = QPainter(lienzo)
    degradado = QLinearGradient(QPointF(0, 0), QPointF(lienzo.width(), lienzo.height()))
    degradado.setColorAt(0.0, QColor("#1A0F2E"))
    degradado.setColorAt(1.0, QColor("#5A1E4A"))
    fondo.fillRect(lienzo.rect(), degradado)
    fondo.end()

    w = TarjetaCancion()
    w.resize(ancho, alto)
    w.poner({"titulo": "Blinding Lights con una letra muy larga para ver el corte",
             "artista": "The Weeknd",
             "fuente_texto": "YouTube · Música"})
    w.poner_portada(portada_ejemplo())
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.fijar_me_gusta(True)
    w.fijar_progreso(0.42)
    # una inclinación leve para que se note la perspectiva y el reflejo
    w._ang_y = 5.0
    w._ang_x = -3.0

    p = QPainter(lienzo)
    p.setRenderHint(QPainter.Antialiasing, True)
    w.render(p, QPoint(margen, margen))
    p.end()

    lienzo.save(salida, "PNG")
    print(salida)


def main():
    QApplication.instance() or QApplication([])
    os.makedirs(CARPETA, exist_ok=True)
    captura(360, 520, SALIDA)
    captura(256, 370, os.path.join(CARPETA, "tarjeta_256x370.png"))


if __name__ == "__main__":
    main()
