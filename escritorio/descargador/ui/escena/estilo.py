# -*- coding: utf-8 -*-
"""Lo que comparten todas las piezas de la escena: fuentes, vidrio y colores.

Cada pieza es una ventanita translúcida propia (encima del video, que mpv pinta en una
ventana nativa), así que todo se dibuja con QPainter sobre fondo transparente y sin
QGraphicsEffect (cuestan demasiado a pantalla completa).
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPainterPath,
                           QPen, QRadialGradient)

# colores de partida (antes de que llegue la paleta de la carátula)
DOMINANTE = QColor("#E8577E")
SEGUNDO = QColor("#3B2A6B")
BRILLO = QColor("#FF9EC0")

TEXTO = QColor(255, 255, 255, 240)
TEXTO_2 = QColor(255, 255, 255, 165)
TEXTO_3 = QColor(255, 255, 255, 105)

RADIO = 18.0          # esquinas de los paneles de vidrio
SOMBRA = 22.0         # lo que se reserva alrededor de cada panel para su sombra

_FAMILIAS = {}


def _primera(*familias):
    clave = familias
    if clave not in _FAMILIAS:
        hay = set(QFontDatabase.families())
        _FAMILIAS[clave] = next((f for f in familias if f in hay), "Segoe UI")
    return _FAMILIAS[clave]


def fuente_fina(px):
    """La del reloj gigante: estrecha y finísima (Bahnschrift viene con Windows 10)."""
    f = QFont(_primera("Bahnschrift Light Condensed", "Bahnschrift SemiLight Condensed",
                       "Bahnschrift Light", "Segoe UI Light"))
    f.setPixelSize(max(1, int(px)))
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def fuente_impacto(px, cursiva=True):
    """La de la letra animada: estrecha, gruesa y en cursiva, como un póster."""
    f = QFont(_primera("Bahnschrift SemiBold Condensed", "Bahnschrift Condensed", "Bahnschrift",
                       "Segoe UI Black"))
    f.setPixelSize(max(1, int(px)))
    f.setItalic(cursiva)
    f.setWeight(QFont.Bold)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def fuente(px, peso=QFont.Normal):
    """La de los textos normales (títulos, listas, botones)."""
    f = QFont(_primera("Segoe UI Variable Display", "Segoe UI"))
    f.setPixelSize(max(1, int(px)))
    f.setWeight(peso)
    return f


def mezclar(a, b, t):
    t = max(0.0, min(1.0, float(t)))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t),
                  int(a.alpha() + (b.alpha() - a.alpha()) * t))


def con_alfa(c, alfa):
    c = QColor(c)
    c.setAlpha(max(0, min(255, int(alfa))))
    return c


def acento_legible(c):
    """El color de la carátula llevado a algo que se lee sobre un fondo oscuro."""
    c = QColor(c).toHsv()
    h, s, v = c.hsvHueF(), c.hsvSaturationF(), c.valueF()
    if h < 0:
        h = 0.0
    return QColor.fromHsvF(h, max(0.35, min(0.85, s)), max(0.82, v))


def pintar_sombra(p, rect, radio=RADIO, fuerza=1.0):
    """Sombra suave alrededor de un rectángulo redondeado (unas capas de borde que se
    desvanecen: barato y sin efectos)."""
    rect = QRectF(rect)
    p.save()
    p.setPen(Qt.NoPen)
    capas = 9
    for i in range(capas, 0, -1):
        d = SOMBRA * i / capas
        p.setBrush(QColor(0, 0, 0, int(14 * fuerza * (1 - i / (capas + 1)) + 2)))
        p.drawRoundedRect(rect.adjusted(-d * 0.6, -d * 0.35, d * 0.6, d), radio + d, radio + d)
    p.restore()


def pintar_vidrio(p, rect, radio=RADIO, acento=None, fuerza=1.0, sombra=True):
    """Panel de vidrio esmerilado: relleno oscuro translúcido, brillo arriba, borde fino
    claro y un toque del color de la carátula abajo."""
    rect = QRectF(rect)
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    if sombra:
        pintar_sombra(p, rect, radio, fuerza)
    camino = QPainterPath()
    camino.addRoundedRect(rect, radio, radio)
    p.fillPath(camino, QColor(16, 16, 22, int(150 * fuerza)))
    brillo = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    brillo.setColorAt(0.0, QColor(255, 255, 255, int(34 * fuerza)))
    brillo.setColorAt(0.35, QColor(255, 255, 255, int(10 * fuerza)))
    brillo.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillPath(camino, brillo)
    if acento is not None:
        tinte = QRadialGradient(QPointF(rect.center().x(), rect.bottom() + rect.height() * 0.15),
                                max(rect.width(), rect.height()) * 0.8)
        tinte.setColorAt(0.0, con_alfa(acento, 70 * fuerza))
        tinte.setColorAt(1.0, con_alfa(acento, 0))
        p.fillPath(camino, tinte)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, int(40 * fuerza)), 1.0))
    p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radio, radio)
    p.restore()


def preparar_transparente(widget):
    """Lo que necesita una ventanita de la escena para ser translúcida y sin marco."""
    widget.setAttribute(Qt.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WA_NoSystemBackground, True)
    widget.setAutoFillBackground(False)
