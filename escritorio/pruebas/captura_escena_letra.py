# -*- coding: utf-8 -*-
"""Captura de la letra cinética sobre un fondo oscuro simulado (sin plataforma offscreen)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.letra import LetraCinetica

FRASE_40 = ("Cae la noche sobre la ciudad y las luces se encienden una a una mientras el viento "
            "lleva tu nombre por calles que ya no recuerdan nuestros pasos cuando volvíamos juntos "
            "bajo la lluvia tibia frente a nuestra casa vacía")

LINEAS = [
    {"ms": 0, "texto": "Ya no sé", "pausa": False, "canto": 1500},
    {"ms": 2000, "texto": FRASE_40, "pausa": False, "canto": 9000},
    {"ms": 11000, "texto": "Y nadie sabe nada", "pausa": False, "canto": 2000},
]

W, H = 620, 420


def main():
    app = QApplication([])
    w = LetraCinetica()
    w.resize(W, H)
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.poner_lineas(LINEAS, True)
    w.fijar_ms(0)
    time.sleep(0.05)
    print("palabras de la frase:", len(FRASE_40.split()), "trozos:", len(w._efectivas()))
    w.fijar_ms(10800)           # frase de 40 palabras (línea impar) con todas sus palabras ya dichas
    time.sleep(0.6)             # que todas las palabras hayan asentado

    pix = QPixmap(W, H)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    grad = QLinearGradient(0, 0, W, H)
    grad.setColorAt(0.0, QColor("#1A0F2E"))
    grad.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(QRectF(0, 0, W, H), grad)
    p.end()

    p = QPainter(pix)
    w.render(p, QPoint(0, 0))
    p.end()

    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena", "letra.png")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    pix.save(salida, "PNG")
    print(salida)
    del app


if __name__ == "__main__":
    main()
