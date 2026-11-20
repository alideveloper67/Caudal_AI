# -*- coding: utf-8 -*-
"""Captura de la escena entera (sin abrir ventanas): pinta el fondo y cada pieza en su sitio,
como quedarían en una pantalla, en pruebas/capturas_escena/escena_<ancho>x<alto>.png."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPixmap, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from descargador.ui.escena.barra import BarraMini  # noqa: E402
from descargador.ui.escena.bordes import BordeBrillo  # noqa: E402
from descargador.ui.escena.buscador import PanelBusqueda  # noqa: E402
from descargador.ui.escena.fondo import FondoAmbiente  # noqa: E402
from descargador.ui.escena.letra import LetraCinetica  # noqa: E402
from descargador.ui.escena.lista_reciente import ListaSeguir  # noqa: E402
from descargador.ui.escena.reloj import RelojGigante  # noqa: E402
from descargador.ui.escena.tarjeta import TarjetaCancion  # noqa: E402
from descargador.ui.escena.ventana import disposicion  # noqa: E402

D, S, B = QColor("#E0457B"), QColor("#2B1B5A"), QColor("#FF8FB8")


def caratula():
    img = QImage(600, 600, QImage.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 0, 600)
    g.setColorAt(0, QColor("#FF7A59"))
    g.setColorAt(1, QColor("#7B2C8F"))
    p.fillRect(img.rect(), g)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FFD36E"))
    p.drawEllipse(QPoint(300, 230), 110, 110)
    p.setBrush(QColor("#2A1846"))
    p.drawEllipse(QRect(-150, 380, 700, 400))
    p.setBrush(QColor("#170C2A"))
    p.drawEllipse(QRect(150, 420, 700, 400))
    p.end()
    return img


def miniatura(color):
    img = QImage(80, 80, QImage.Format_RGB32)
    img.fill(QColor(color))
    return img


def capturar(W, H, con_resultados=False):
    pantalla = QRect(0, 0, W, H)
    g = disposicion(pantalla)
    lienzo = QPixmap(W, H)
    p = QPainter(lienzo)
    portada = caratula()

    fondo = FondoAmbiente()
    fondo.resize(W, H)
    fondo.poner_colores(D, S, B)
    fondo.poner_portada(portada)
    fondo._transicion = None if hasattr(fondo, "_transicion") else None
    fondo.render(p, QPoint(0, 0))

    pista = {"titulo": "Atardecer en Miraflores", "artista": "Lúa Serrano", "clave": "a",
             "fuente_texto": "Desde YouTube Music"}
    colores = ["#E86A92", "#5B8DEF", "#5FCB8A", "#F2B544", "#9B6CF0", "#EF7F5A", "#4FC3D9"]
    recientes = [{"titulo": t, "artista": a, "miniatura": f"m{i}", "clave": f"c{i}"} for i, (t, a) in enumerate([
        ("Atardecer en Miraflores", "Lúa Serrano"), ("Corazón de neón", "Sofía Lirio"),
        ("Tren a medianoche", "Los Faroles"), ("Agua tibia", "Marina Ocaso"), ("Sin fin", "Trío Azafrán"),
        ("Cielo bajo", "Hanna Brisa"), ("Bailando en el techo", "Dúo Vela"), ("Mapas viejos", "Ricardo Aire"),
        ("Girasoles", "Ana Ruiz"), ("Otra vez", "Kai Montes")])]

    def cargador(url, cb):
        cb(miniatura(colores[int(url[1:]) % len(colores)]))

    piezas = []
    lista = ListaSeguir()
    lista.fijar_cargador(cargador)
    lista.poner(recientes)
    lista.marcar_actual("c0")
    piezas.append((lista, g["lista"]))

    reloj = RelojGigante()
    from datetime import datetime
    reloj.fijar_ahora(lambda: datetime(2026, 11, 20, 19, 0))
    piezas.append((reloj, g["reloj"]))

    tarjeta = TarjetaCancion()
    tarjeta.poner(pista)
    tarjeta.poner_portada(portada)
    tarjeta.fijar_me_gusta(True)
    tarjeta.fijar_progreso(0.38)
    piezas.append((tarjeta, g["tarjeta"]))

    letra = LetraCinetica()
    letra.poner_lineas([{"ms": 0, "texto": "Y nadie sabe nada de nosotros", "pausa": False, "canto": 2200},
                        {"ms": 4000, "texto": "bajo la luna de papel", "pausa": False, "canto": 2000}], True)
    piezas.append((letra, g["letra"]))

    barra = BarraMini()
    barra.poner(pista)
    barra.poner_portada(portada)
    barra.fijar_estado("sonando")
    barra.fijar_progreso(76, 200)
    piezas.append((barra, g["barra"]))

    busc = PanelBusqueda()
    if con_resultados:
        busc.fijar_cargador(cargador)
        busc.mostrar_resultados(
            [{"titulo": f"Luna {i}", "artista": "Lúa Serrano", "miniatura": f"m{i}"} for i in range(4)],
            [{"titulo": n, "miniatura": f"m{i + 3}"} for i, n in enumerate(["Lúa Serrano", "Sofía Lirio", "Kai Montes"])])
    alto = busc.altura_deseada()
    ab = g["buscador_abajo"]
    piezas.append((busc, QRect(ab.x(), ab.y() - alto, ab.width(), alto)))

    for w, r in piezas:
        w.poner_colores(D, S, B)
        w.setGeometry(r)
        w.resize(r.size())
    for lado, r in g["bordes"].items():
        b = BordeBrillo(lado)
        b.poner_colores(D, S, B)
        b.resize(r.size())
        piezas.insert(0, (b, r))
    app.processEvents()
    letra.fijar_ms(4000 if con_resultados else 2600)
    app.processEvents()
    # que terminen las entradas animadas
    import time
    t_fin = time.monotonic() + 1.2
    while time.monotonic() < t_fin:
        app.processEvents()
        time.sleep(0.02)
    for w, r in piezas:
        w.render(p, r.topLeft())
    p.end()
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_escena")
    os.makedirs(carpeta, exist_ok=True)
    nombre = f"escena_{W}x{H}{'_busqueda' if con_resultados else ''}.png"
    lienzo.save(os.path.join(carpeta, nombre))
    print(nombre)


if __name__ == "__main__":
    capturar(1920, 1080)
    capturar(1920, 1080, con_resultados=True)
    capturar(1366, 768)
