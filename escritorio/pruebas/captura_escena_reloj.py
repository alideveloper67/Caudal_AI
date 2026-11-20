# -*- coding: utf-8 -*-
"""Captura del reloj gigante sobre un fondo degradado simulado (sin plataforma offscreen,
para que se usen las fuentes reales)."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtGui import QColor, QFontInfo, QLinearGradient, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.estilo import fuente_fina  # noqa: E402
from descargador.ui.escena.reloj import RelojGigante  # noqa: E402

MARGEN = 40


def main():
    app = QApplication.instance() or QApplication([])
    familia = QFontInfo(fuente_fina(200)).family()
    print("familia real:", familia)
    w = RelojGigante()
    w.resize(560, 320)
    w.fijar_ahora(lambda: datetime(2026, 11, 20, 19, 5))
    w.fijar_24h(True)

    lienzo = QPixmap(560 + 2 * MARGEN, 320 + 2 * MARGEN)
    p = QPainter(lienzo)
    degradado = QLinearGradient(0, 0, lienzo.width(), lienzo.height())
    degradado.setColorAt(0.0, QColor("#1A0F2E"))
    degradado.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(lienzo.rect(), degradado)
    p.end()

    p = QPainter(lienzo)
    w.render(p, QPoint(MARGEN, MARGEN))
    p.end()

    salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena", "reloj.png")
    lienzo.save(salida, "PNG")
    print(salida)


if __name__ == "__main__":
    main()
