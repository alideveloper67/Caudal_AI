# -*- coding: utf-8 -*-
"""Captura de la lista «Seguir escuchando» sobre un fondo oscuro simulado.
Usa la plataforma real (no offscreen) para que salgan las fuentes. Las miniaturas son
degradados generados aquí, sin red."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.lista_reciente import ListaSeguir

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena")
SALIDA = os.path.join(CARPETA, "lista.png")

PALETA = [("#E8577E", "#FF9EC0"), ("#3B8FD9", "#9FD4FF"), ("#45B36B", "#B4F0C8"),
          ("#E8AB16", "#FFE08A"), ("#8E5BD9", "#D0B4FF"), ("#D9653B", "#FFC0A6")]

DATOS = [
    ("Luna de papel", "Nébula Verde", "v1"),
    ("Corazón de neón", "Sofía Lirio", "v2"),
    ("Tren a medianoche", "Los Faroles", "v3"),
    ("Agua tibia", "Marina Ocaso", "v4"),
    ("Sin fin", "Trío Azafrán", "v5"),
    ("Cielo bajo", "Hanna Brisa", "v6"),
    ("Bailando en el techo", "Dúo Vela", "v7"),
    ("Mapas viejos", "Ricardo Aire", "v8"),
    ("Girasoles", "Ana Ruiz", "v9"),
    ("Nocturno 4", "Quinteto Ámbar", "v10"),
    ("Pequeño faro", "Lía Sol", "v11"),
]


def _imagen_de(url):
    """Degradado de color según la url, para que cada miniatura se distinga."""
    i = int(url.rsplit("/", 1)[-1].split(".")[0])
    a, b = PALETA[i % len(PALETA)]
    img = QImage(96, 96, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 96, 96)
    g.setColorAt(0.0, QColor(a))
    g.setColorAt(1.0, QColor(b))
    p.fillRect(QRectF(0, 0, 96, 96), g)
    p.end()
    return img


def _cargador(url, callback):
    callback(_imagen_de(url))


def main():
    app = QApplication.instance() or QApplication([])
    os.makedirs(CARPETA, exist_ok=True)

    w = ListaSeguir()
    w.resize(w.sizeHint())
    w.fijar_cargador(_cargador)
    pistas = [{"titulo": t, "artista": a, "miniatura": f"https://img.test/{k}.jpg", "video_id": v}
              for k, (t, a, v) in enumerate(DATOS)]
    w.poner(pistas)
    w.marcar_actual("v3")
    w.poner_colores(QColor("#E8577E"), QColor("#3B2A6B"), QColor("#FF9EC0"))

    ancho, alto = 330, 600
    lienzo = QPixmap(ancho, alto)
    p = QPainter(lienzo)
    fondo = QLinearGradient(0, 0, ancho, alto)
    fondo.setColorAt(0.0, QColor("#1A0F2E"))
    fondo.setColorAt(1.0, QColor("#5A1E4A"))
    p.fillRect(QRectF(0, 0, ancho, alto), fondo)
    p.end()

    # render pinta el widget encima del fondo, con desplazamiento 20 px
    p = QPainter(lienzo)
    p.setRenderHint(QPainter.Antialiasing, True)
    w.render(p, QPoint(20, 20))
    p.end()

    if not lienzo.save(SALIDA, "PNG"):
        raise SystemExit(f"No se pudo guardar {SALIDA}")
    print(SALIDA)


if __name__ == "__main__":
    main()
