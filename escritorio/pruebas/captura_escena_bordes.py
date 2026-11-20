# -*- coding: utf-8 -*-
"""Captura del marco de brillo sobre un fondo oscuro simulado (sin plataforma offscreen)."""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.bordes import LADOS, BordeBrillo, geometrias_borde
from descargador.ui.escena.estilo import BRILLO, DOMINANTE, SEGUNDO

ANCHO, ALTO, GROSOR = 1280, 720, 48
SALIDA = os.path.join(RAIZ, "pruebas", "capturas_escena", "bordes.png")


def main():
    app = QApplication.instance() or QApplication([])
    from PySide6.QtCore import QRect

    lienzo = QPixmap(ANCHO, ALTO)
    p = QPainter(lienzo)
    fondo = QLinearGradient(QPointF(0, 0), QPointF(ANCHO, ALTO))
    fondo.setColorAt(0.0, QColor("#1A0F2E"))
    fondo.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(lienzo.rect(), fondo)
    p.end()

    geometrias = geometrias_borde(QRect(0, 0, ANCHO, ALTO), GROSOR)
    bordes = []
    for lado in LADOS:
        b = BordeBrillo(lado)
        r = geometrias[lado]
        b.resize(r.size())
        b.poner_colores(DOMINANTE, SEGUNDO, BRILLO)
        b.fijar_intensidad(0.85)
        bordes.append((b, r))

    # el reloj de la transición ya ha terminado porque poner_colores se llamó hace un instante;
    # para la captura se usan los colores finales directamente
    for b, _ in bordes:
        b._transicion = None
        b._colores = (QColor(DOMINANTE), QColor(SEGUNDO), QColor(BRILLO))

    p = QPainter(lienzo)
    p.setRenderHint(QPainter.Antialiasing, True)
    for b, r in bordes:
        b.render(p, QPoint(r.x(), r.y()))
    p.end()

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    if not lienzo.save(SALIDA, "PNG"):
        raise SystemExit(f"no se pudo guardar {SALIDA}")
    print(SALIDA)


if __name__ == "__main__":
    main()
