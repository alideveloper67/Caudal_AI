# -*- coding: utf-8 -*-
"""Captura visual del buscador de la escena (sin plataforma offscreen: hacen falta fuentes).

Pinta el buscador con resultados de ejemplo encima de un fondo simulado y guarda
pruebas/capturas_escena/buscador.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.buscador import PanelBusqueda  # noqa: E402

CANCIONES = [
    {"titulo": "Bohemian Rhapsody", "artista": "Queen", "miniatura": "mem://q1"},
    {"titulo": "Under Pressure (Remastered 2011)", "artista": "Queen & David Bowie", "miniatura": "mem://q2"},
    {"titulo": "Don't Stop Me Now", "artista": "Queen", "miniatura": "mem://q3"},
    {"titulo": "Somebody to Love", "artista": "Queen", "miniatura": "mem://q4"},
]
ARTISTAS = [
    {"titulo": "Queen", "miniatura": "mem://a1"},
    {"titulo": "David Bowie", "miniatura": "mem://a2"},
    {"titulo": "Freddie Mercury", "miniatura": "mem://a3"},
    {"titulo": "Brian May", "miniatura": "mem://a4"},
    {"titulo": "Roger Taylor", "miniatura": "mem://a5"},
]
COLORES = {
    "mem://q1": ("#E8577E", "#3B2A6B"), "mem://q2": ("#2F6FD6", "#14B8A6"),
    "mem://q3": ("#F59E0B", "#7C2D12"), "mem://q4": ("#8B5CF6", "#1E1B4B"),
    "mem://a1": ("#E8577E", "#3B2A6B"), "mem://a2": ("#14B8A6", "#0F172A"),
    "mem://a3": ("#F43F5E", "#4C0519"), "mem://a4": ("#38BDF8", "#0C4A6E"),
    "mem://a5": ("#A3E635", "#365314"),
}


def _imagen_de_prueba(url, callback):
    """Carátula sintética (degradado) para no depender de la red."""
    c1, c2 = COLORES.get(url, ("#888888", "#333333"))
    img = QImage(300, 300, QImage.Format_ARGB32)
    img.fill(QColor(c1))
    p = QPainter(img)
    g = QLinearGradient(QPointF(0, 0), QPointF(300, 300))
    g.setColorAt(0.0, QColor(c1))
    g.setColorAt(1.0, QColor(c2))
    p.fillRect(img.rect(), g)
    p.end()
    callback(img)


def main():
    app = QApplication.instance() or QApplication([])
    w = PanelBusqueda()
    w.fijar_cargador(_imagen_de_prueba)
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))
    w.fijar_fuente("youtube")
    w.show()
    w._campo.setText("queen")
    w.mostrar_resultados(CANCIONES, ARTISTAS)
    app.processEvents()

    alto = w.altura_deseada()
    w.resize(640, alto)
    pm = QPixmap(640, alto)
    p = QPainter(pm)
    fondo = QLinearGradient(QPointF(0, 0), QPointF(0, alto))
    fondo.setColorAt(0.0, QColor("#1A0F2E"))
    fondo.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(pm.rect(), fondo)
    w.render(p, QPoint(0, 0))
    p.end()

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    carpeta = os.path.join(raiz, "pruebas", "capturas_escena")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "buscador.png")
    pm.save(ruta)
    print(ruta)


if __name__ == "__main__":
    main()
