# -*- coding: utf-8 -*-
"""Piezas visuales del modo estudio: iconos, tarjetas de perfil, mezclador, notas y el
aviso de salida. Todo pintado con la paleta de Caudal (se recolorea en vivo) y con las
mismas esquinas, sombras suaves y animaciones breves del resto de la aplicación."""

import math
import time

from PySide6.QtCore import (QEasingCurve, QEvent, QPointF, QRectF, Qt, QTimer, QVariantAnimation,
                            Signal)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QGuiApplication, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import estudio as E
from .. import sonidos_ambiente as SA
from . import estilos, iconos
from .componentes import BotonIcono, Deslizador, fuente, suavizar
from .estilos import C


# ---------------------------------------------------------------------- colores

def mezclar(a, b, t):
    """Color entre a y b (t de 0 a 1)."""
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t),
                  round(a.alpha() + (b.alpha() - a.alpha()) * t))


def con_alfa(color, alfa):
    c = QColor(color)
    c.setAlpha(int(max(0, min(255, alfa))))
    return c


def color_tarjeta(nivel="superficie"):
    """El fondo de una tarjeta; con «Fondo de Caudal» se vuelve translúcido como las demás."""
    c = QColor(C[nivel])
    if estilos.FONDO["activo"]:
        c.setAlphaF(estilos.ALFA_TARJETA)
    return c


# ---------------------------------------------------------------------- iconos

_ICONOS = {}


def icono_estudio(nombre, tam=24, color=None):
    """Iconos propios del modo estudio (mismo trazo redondeado que los de Caudal)."""
    color = color or C["texto2"]
    clave = (nombre, tam, color)
    if clave in _ICONOS:
        return _ICONOS[clave]
    pm = QPixmap(tam, tam)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    e = tam / 24.0
    lapiz = QPen(QColor(color))
    lapiz.setWidthF(1.8 if tam >= 20 else 1.6)
    lapiz.setCapStyle(Qt.RoundCap)
    lapiz.setJoinStyle(Qt.RoundJoin)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)

    def pt(x, y):
        return QPointF(x * e, y * e)

    def curva(*partes):
        ruta = QPainterPath()
        ruta.moveTo(pt(*partes[0]))
        for seg in partes[1:]:
            if len(seg) == 6:
                ruta.cubicTo(pt(seg[0], seg[1]), pt(seg[2], seg[3]), pt(seg[4], seg[5]))
            else:
                ruta.lineTo(pt(*seg))
        return ruta

    if nombre == "libro":
        p.drawPath(curva((12, 6.5), (9.5, 4.6, 5.5, 4.4, 3, 5.6), (3, 18.4),
                         (5.5, 17.2, 9.5, 17.4, 12, 19.4), (14.5, 17.4, 18.5, 17.2, 21, 18.4),
                         (21, 5.6), (18.5, 4.4, 14.5, 4.6, 12, 6.5)))
        p.drawLine(pt(12, 6.5), pt(12, 19.4))
    elif nombre == "codigo":
        p.drawPolyline([pt(8, 7.5), pt(3.5, 12), pt(8, 16.5)])
        p.drawPolyline([pt(16, 7.5), pt(20.5, 12), pt(16, 16.5)])
        p.drawLine(pt(13.5, 5.5), pt(10.5, 18.5))
    elif nombre == "tarjetas":
        p.drawRoundedRect(QRectF(6.5 * e, 3.5 * e, 14 * e, 10 * e), 2.4 * e, 2.4 * e)
        p.drawRoundedRect(QRectF(3.5 * e, 8.5 * e, 14 * e, 10.5 * e), 2.4 * e, 2.4 * e)
        p.drawLine(pt(7, 13), pt(14, 13))
        p.drawLine(pt(7, 16), pt(11.5, 16))
    elif nombre == "hoja":
        p.drawPath(curva((4.5, 19.5), (4.5, 10, 9.5, 4.8, 19.5, 4.5), (19.5, 14.5, 14, 19.5, 4.5, 19.5)))
        p.drawLine(pt(4.5, 19.5), pt(13, 11))
    elif nombre == "lluvia":
        p.drawPath(curva((7, 14.5), (4.4, 14.5, 3, 12.7, 3, 10.8), (3, 8.8, 4.6, 7.4, 6.6, 7.4),
                         (7.2, 4.8, 9.4, 3.2, 12, 3.2), (14.8, 3.2, 17, 5, 17.4, 7.6),
                         (19.6, 7.8, 21, 9.4, 21, 11.2), (21, 13.2, 19.4, 14.5, 17.4, 14.5), (7, 14.5)))
        for x in (8, 12.5, 17):
            p.drawLine(pt(x, 17.4), pt(x - 1.4, 20.6))
    elif nombre == "cafeteria":
        p.drawPath(curva((4.5, 10), (4.5, 16.5), (4.5, 18.6, 6.2, 20, 8.5, 20), (11, 20),
                         (13.3, 20, 15, 18.6, 15, 16.5), (15, 10), (4.5, 10)))
        p.drawArc(QRectF(13.2 * e, 11 * e, 6 * e, 5.4 * e), 90 * 16, -180 * 16)
        for x in (7, 10.6):
            p.drawPath(curva((x, 7.8), (x - 1.4, 6.4, x + 1.4, 5, x, 3.6)))
    elif nombre == "bosque":
        p.drawPolyline([pt(12, 3.2), pt(6.5, 10.5), pt(9, 10.5), pt(4.6, 16.2), pt(19.4, 16.2),
                        pt(15, 10.5), pt(17.5, 10.5), pt(12, 3.2)])
        p.drawLine(pt(12, 16.2), pt(12, 20.8))
    elif nombre == "chimenea":
        p.drawPath(curva((12, 3), (13.2, 7, 18.4, 9, 18.4, 14.4), (18.4, 18, 15.6, 21, 12, 21),
                         (8.4, 21, 5.6, 18.2, 5.6, 14.8), (5.6, 12.6, 6.6, 11.2, 7.8, 10.2),
                         (8.2, 12, 9, 12.8, 10, 13), (9.2, 9.2, 10.4, 5.4, 12, 3)))
        p.drawPath(curva((12, 21), (10.4, 21, 9.4, 19.8, 9.4, 18.4), (9.4, 16.8, 11, 16, 12, 14.6),
                         (13, 16, 14.6, 16.8, 14.6, 18.4), (14.6, 19.8, 13.6, 21, 12, 21)))
    elif nombre in ("blanco", "rosa", "marron"):
        ruta = QPainterPath()
        n = 15
        for i in range(n):
            x = 3 + i * 18 / (n - 1)
            if nombre == "blanco":
                y = 12 + (6.5 if i % 2 else -6.5) * (0.75 + 0.25 * math.sin(i * 2.1))
            elif nombre == "rosa":
                y = 12 + (4.6 if i % 2 else -4.6) * (0.5 + 0.5 * math.sin(i * 0.8 + 1)) \
                    + 3.6 * math.sin(i * 0.5)
            else:
                y = 12 + 6.2 * math.sin(i * 0.46) + 1.6 * math.sin(i * 1.0)
            ruta.moveTo(pt(x, y)) if i == 0 else ruta.lineTo(pt(x, y))
        if nombre == "marron":
            ruta = QPainterPath()
            ruta.moveTo(pt(3, 13))
            ruta.cubicTo(pt(6, 4), pt(8.5, 4), pt(11, 12))
            ruta.cubicTo(pt(13, 19), pt(16, 20), pt(21, 9))
        p.drawPath(ruta)
    elif nombre == "sol":
        p.drawEllipse(pt(12, 12), 4.2 * e, 4.2 * e)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(pt(12 + 7.2 * math.cos(a), 12 + 7.2 * math.sin(a)),
                       pt(12 + 9.6 * math.cos(a), 12 + 9.6 * math.sin(a)))
    elif nombre == "luna":
        ruta = QPainterPath()
        ruta.addEllipse(QRectF(4 * e, 4 * e, 16 * e, 16 * e))
        corte = QPainterPath()
        corte.addEllipse(QRectF(9 * e, 1.5 * e, 14 * e, 14 * e))
        p.drawPath(ruta.subtracted(corte))
    elif nombre == "campana":
        p.drawPath(curva((6, 16.5), (7.2, 15, 7.4, 13, 7.4, 10.4), (7.4, 7.2, 9.4, 5.2, 12, 5.2),
                         (14.6, 5.2, 16.6, 7.2, 16.6, 10.4), (16.6, 13, 16.8, 15, 18, 16.5), (6, 16.5)))
        p.drawLine(pt(12, 3), pt(12, 5.2))
        p.drawArc(QRectF(10 * e, 17.2 * e, 4 * e, 3.2 * e), 180 * 16, 180 * 16)
    elif nombre == "idea":
        p.drawPath(curva((9, 15.5), (9, 13.6, 6.2, 12.4, 6.2, 8.8), (6.2, 5.8, 8.8, 3.6, 12, 3.6),
                         (15.2, 3.6, 17.8, 5.8, 17.8, 8.8), (17.8, 12.4, 15, 13.6, 15, 15.5), (9, 15.5)))
        p.drawLine(pt(9.4, 18.4), pt(14.6, 18.4))
        p.drawLine(pt(10.4, 21), pt(13.6, 21))
    elif nombre == "pantalla":
        p.drawPolyline([pt(4, 9), pt(4, 4), pt(9, 4)])
        p.drawPolyline([pt(15, 4), pt(20, 4), pt(20, 9)])
        p.drawPolyline([pt(20, 15), pt(20, 20), pt(15, 20)])
        p.drawPolyline([pt(9, 20), pt(4, 20), pt(4, 15)])
    elif nombre == "copiar":
        p.drawRoundedRect(QRectF(8.5 * e, 8.5 * e, 11 * e, 11.5 * e), 2.2 * e, 2.2 * e)
        p.drawPolyline([pt(15.5, 8.5), pt(15.5, 6.5), pt(13.5, 4.5), pt(6.5, 4.5), pt(4.5, 6.5),
                        pt(4.5, 15.5), pt(6.5, 15.5), pt(8.5, 15.5)])
    elif nombre == "taza_pausa":
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(6 * e, 5 * e, 4 * e, 14 * e), 1.5 * e, 1.5 * e)
        p.drawRoundedRect(QRectF(14 * e, 5 * e, 4 * e, 14 * e), 1.5 * e, 1.5 * e)
    p.end()
    _ICONOS[clave] = pm
    return pm


def _mi_color_icono(nombre, tam, color):
    """Los iconos de la app para los botones; los del modo estudio se dibujan aquí."""
    if nombre in ("libro", "codigo", "tarjetas", "hoja", "lluvia", "cafeteria", "bosque",
                  "chimenea", "blanco", "rosa", "marron", "sol", "luna", "campana", "idea",
                  "pantalla", "copiar", "taza_pausa"):
        return icono_estudio(nombre, tam, color)
    return iconos.pixmap(nombre, tam, color)


class BotonRedondo(QPushButton):
    """Botón circular suave para la vista minimalista: icono sobre un círculo tenue."""

    def __init__(self, icono, lado=44, tam=20, ayuda="", relleno=False, padre=None):
        super().__init__(padre)
        self.icono, self.tam, self.relleno = icono, tam, relleno
        self.activo = False
        self.color_activo = None
        self._encima = 0.0
        self.setFixedSize(lado, lado)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip(ayuda)
        self.setAccessibleName(ayuda)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._ir)

    def _ir(self, v):
        self._encima = float(v)
        self.update()

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._encima)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._encima)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(e)

    def set_icono(self, icono):
        self.icono = icono
        self.update()

    def set_activo(self, si):
        self.activo = bool(si)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.relleno:
            fondo = mezclar(C["texto"], "#FFFFFF", 0.0)
            fondo.setAlpha(255 if self._encima > 0.5 else 240)
            p.setPen(Qt.NoPen)
            p.setBrush(fondo)
            p.drawEllipse(r)
            color = "#0B0D12"
        else:
            base = 26 + int(26 * self._encima) + (22 if self.activo else 0)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, base))
            p.drawEllipse(r)
            if self.activo:
                p.setPen(QPen(con_alfa(self.color_activo or C["acento"], 170), 1.4))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(r)
            color = (self.color_activo or C["acento_alto"]) if self.activo else C["texto"]
        pm = _mi_color_icono(self.icono, self.tam, color)
        p.drawPixmap(int((self.width() - self.tam) / 2 + (1.5 if self.icono == "reproducir" else 0)),
                     int((self.height() - self.tam) / 2), pm)


# ---------------------------------------------------------------------- segmentado

class Segmentado(QWidget):
    """Opciones en una píldora: la selección se desliza de una a otra."""

    cambiado = Signal(str)

    def __init__(self, opciones, actual, alto=38, padre=None):
        super().__init__(padre)
        self.opciones = list(opciones)               # [(clave, texto)]
        self.actual = actual
        self._pos = float(self._indice())
        self.setFixedHeight(alto)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._mover)
        self.setMouseTracking(True)
        self._sobre = -1

    def _indice(self):
        for i, (k, _t) in enumerate(self.opciones):
            if k == self.actual:
                return i
        return 0

    def _mover(self, v):
        self._pos = float(v)
        self.update()

    def poner(self, clave, emitir=False):
        if clave == self.actual:
            return
        self.actual = clave
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(float(self._indice()))
        self._anim.start()
        if emitir:
            self.cambiado.emit(clave)

    def sizeHint(self):
        fm = QFontMetrics(fuente(13, QFont.DemiBold))
        ancho = sum(fm.horizontalAdvance(t) + 34 for _k, t in self.opciones)
        from PySide6.QtCore import QSize
        return QSize(ancho, self.height())

    def _ancho_seg(self):
        return self.width() / max(1, len(self.opciones))

    def mouseMoveEvent(self, e):
        i = int(e.position().x() // self._ancho_seg())
        if i != self._sobre:
            self._sobre = i
            self.update()

    def leaveEvent(self, e):
        self._sobre = -1
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.opciones:
            i = max(0, min(len(self.opciones) - 1, int(e.position().x() // self._ancho_seg())))
            self.poner(self.opciones[i][0], emitir=True)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radio = r.height() / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 16))
        p.drawRoundedRect(r, radio, radio)
        w = self._ancho_seg()
        pieza = QRectF(r.left() + 3 + self._pos * w, r.top() + 3, w - 6 + (0 if len(self.opciones) > 1 else 0),
                       r.height() - 6)
        p.setBrush(QColor(C["texto"]))
        p.drawRoundedRect(pieza, radio - 3, radio - 3)
        f = fuente(13, QFont.DemiBold)
        p.setFont(f)
        for i, (k, texto) in enumerate(self.opciones):
            celda = QRectF(r.left() + i * w, r.top(), w, r.height())
            cerca = max(0.0, 1.0 - abs(self._pos - i))     # cuánto lo cubre la pieza
            if cerca > 0.5:
                color = QColor("#0B0D12")
            else:
                color = QColor(C["texto"] if i == self._sobre else C["texto2"])
            p.setPen(color)
            p.drawText(celda, Qt.AlignCenter, texto)


# ---------------------------------------------------------------------- tarjeta de perfil

class TarjetaPerfil(QWidget):
    elegido = Signal(str)

    def __init__(self, clave, padre=None):
        super().__init__(padre)
        self.clave = clave
        self.datos = E.PERFILES[clave]
        self.seleccionada = False
        self._encima = 0.0
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(150)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setAccessibleName(f"{self.datos['nombre']}. {self.datos['lema']}")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.valueChanged.connect(self._ir)

    def _ir(self, v):
        self._encima = float(v)
        self.update()

    def poner_seleccion(self, si):
        self.seleccionada = bool(si)
        self.update()

    def enterEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._encima)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def leaveEvent(self, e):
        self._anim.stop()
        self._anim.setStartValue(self._encima)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.elegido.emit(self.clave)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.elegido.emit(self.clave)
        else:
            super().keyPressEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        radio = 18
        ruta = QPainterPath()
        ruta.addRoundedRect(r, radio, radio)
        p.fillPath(ruta, color_tarjeta("superficie"))
        c1, c2 = (QColor(x) for x in self.datos["colores"])
        fuerza = 0.62 + 0.18 * self._encima + (0.2 if self.seleccionada else 0.0)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, con_alfa(c1, 255 * fuerza))
        g.setColorAt(1, con_alfa(c2, 255 * fuerza * 0.8))
        p.fillPath(ruta, g)
        # un brillo suave arriba a la izquierda
        luz = QRadialGradient(QPointF(r.left() + 40, r.top() + 10), r.width() * 0.7)
        luz.setColorAt(0, QColor(255, 255, 255, 34))
        luz.setColorAt(1, QColor(255, 255, 255, 0))
        p.save()
        p.setClipPath(ruta)
        p.fillRect(r, luz)
        p.restore()
        if self.seleccionada:
            p.setPen(QPen(QColor(C["acento"]), 2.0))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 22 + int(34 * self._encima)), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(ruta)
        if self.hasFocus():
            p.setPen(QPen(QColor(C["texto"]), 1.4, Qt.DashLine))
            p.drawRoundedRect(r.adjusted(4, 4, -4, -4), radio - 3, radio - 3)
        # icono en un círculo
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 36))
        p.drawEllipse(QRectF(r.left() + 20, r.top() + 18, 44, 44))
        p.drawPixmap(int(r.left() + 20 + 10), int(r.top() + 18 + 10),
                     icono_estudio(self.datos["icono"], 24, "#FFFFFF"))
        if self.seleccionada:
            p.setBrush(QColor(C["acento"]))
            c = QRectF(r.right() - 20 - 24, r.top() + 22, 24, 24)
            p.drawEllipse(c)
            p.drawPixmap(int(c.left() + 4), int(c.top() + 4),
                         iconos.pixmap("listo", 16, C["acento_texto"]))
        ancho = int(r.width() - 40)
        f1 = fuente(17, QFont.Bold, True)
        p.setFont(f1)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(r.left() + 20, r.top() + 76, ancho, 24), Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(f1).elidedText(self.datos["nombre"], Qt.ElideRight, ancho))
        f2 = fuente(13)
        p.setFont(f2)
        p.setPen(QColor(255, 255, 255, 225))
        p.drawText(QRectF(r.left() + 20, r.top() + 101, ancho, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(f2).elidedText(self.datos["lema"], Qt.ElideRight, ancho))
        f3 = fuente(11.5)
        p.setFont(f3)
        p.setPen(QColor(255, 255, 255, 150))
        p.drawText(QRectF(r.left() + 20, r.top() + 120, ancho, 18), Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(f3).elidedText(self.datos["detalle"], Qt.ElideRight, ancho))


# ---------------------------------------------------------------------- mezclador

class FilaCapa(QWidget):
    """Un sonido: icono, nombre, volumen propio e interruptor."""

    def __init__(self, ctrl, capa, compacta=False, padre=None):
        super().__init__(padre)
        self.ctrl, self.capa = ctrl, capa
        self.setFixedHeight(54)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(14)
        self.icono = QLabel()
        self.icono.setFixedSize(40, 40)
        self.icono.setAlignment(Qt.AlignCenter)
        h.addWidget(self.icono)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.setContentsMargins(0, 0, 0, 0)
        col.addStretch(1)
        self.nombre = QLabel(SA.NOMBRES[capa])
        self.nombre.setStyleSheet("font-size:14px;font-weight:600;background:transparent;")
        col.addWidget(self.nombre)
        self.desc = QLabel(SA.DESCRIPCIONES[capa])
        self.desc.setObjectName("ayuda")
        self.desc.setStyleSheet("background:transparent;")
        if not compacta:
            col.addWidget(self.desc)
        else:
            self.desc.hide()
        col.addStretch(1)
        h.addLayout(col, 1)
        self.vol = Deslizador(18)
        self.vol.setFixedWidth(120 if compacta else 150)
        self.vol.soltado.connect(self._volumen)
        self.vol.movido.connect(self._volumen)
        h.addWidget(self.vol)
        self.etq_vol = QLabel("")
        self.etq_vol.setObjectName("ayuda")
        self.etq_vol.setFixedWidth(34)
        self.etq_vol.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.etq_vol.setStyleSheet("background:transparent;")
        h.addWidget(self.etq_vol)
        self.interruptor = QCheckBox()
        self.interruptor.setFocusPolicy(Qt.TabFocus)
        self.interruptor.setAccessibleName(f"Sonido {SA.NOMBRES[capa]}")
        self.interruptor.toggled.connect(self._encender)
        h.addWidget(self.interruptor)
        self.refrescar()

    def _encender(self, si):
        if bool(self.ctrl.mezclador.estado[self.capa]["on"]) != bool(si):
            self.ctrl.mezclador.encender(self.capa, si)

    def _volumen(self, v):
        self.ctrl.mezclador.volumen(self.capa, round(v * 100))
        if not self.ctrl.mezclador.estado[self.capa]["on"] and v > 0:
            self.ctrl.mezclador.encender(self.capa, True)

    def refrescar(self):
        est = self.ctrl.mezclador.estado[self.capa]
        on = est["on"]
        self.interruptor.blockSignals(True)
        self.interruptor.setChecked(on)
        self.interruptor.blockSignals(False)
        self.vol.set_valor(est["vol"] / 100.0)
        self.vol.setEnabled(True)
        preparando = self.ctrl.mezclador.esta_preparando(self.capa)
        self.etq_vol.setText("…" if preparando and on else f"{est['vol']}")
        color = C["acento"] if on else C["texto2"]
        self.icono.setPixmap(icono_estudio(self.capa, 22, color))
        fondo = f"rgba(255,255,255,{22 if on else 12})"
        borde = f"1px solid {C['acento']}" if on else "1px solid transparent"
        self.icono.setStyleSheet(f"background:{fondo};border-radius:20px;border:{borde};")
        self.nombre.setStyleSheet(f"font-size:14px;font-weight:600;background:transparent;"
                                  f"color:{C['texto'] if on else C['texto2']};")


class PanelMezcla(QWidget):
    """La música base y los sonidos ambientales, cada uno con su volumen."""

    def __init__(self, ctrl, compacto=False, padre=None):
        super().__init__(padre)
        self.ctrl = ctrl
        self.compacto = compacto
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        # música base: el volumen del reproductor de siempre
        base = QHBoxLayout()
        base.setSpacing(14)
        ic = QLabel()
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignCenter)
        ic.setPixmap(iconos.pixmap("musica", 20, C["acento"]))
        ic.setStyleSheet(f"background:rgba(255,255,255,22);border-radius:20px;"
                         f"border:1px solid {C['acento']};")
        base.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = QLabel("Música base")
        t.setStyleSheet("font-size:14px;font-weight:600;background:transparent;")
        col.addWidget(t)
        self.sub = QLabel("")
        self.sub.setObjectName("ayuda")
        self.sub.setStyleSheet("background:transparent;")
        if not compacto:
            col.addWidget(self.sub)
        else:
            self.sub.hide()
        base.addLayout(col, 1)
        self.vol_base = Deslizador(18)
        self.vol_base.setFixedWidth(120 if compacto else 150)
        self.vol_base.movido.connect(self._volumen_base)
        self.vol_base.soltado.connect(self._volumen_base)
        base.addWidget(self.vol_base)
        self.etq_base = QLabel("")
        self.etq_base.setObjectName("ayuda")
        self.etq_base.setFixedWidth(34)
        self.etq_base.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.etq_base.setStyleSheet("background:transparent;")
        base.addWidget(self.etq_base)
        espacio = QWidget()
        espacio.setFixedWidth(36)          # alinea con los interruptores de abajo
        base.addWidget(espacio)
        cont = QWidget()
        cont.setFixedHeight(54)
        cont.setLayout(base)
        v.addWidget(cont)
        linea = QFrame()
        linea.setObjectName("separador")
        v.addWidget(linea)
        v.addSpacing(4)
        self.filas = {}
        for capa in E.CAPAS_ORDEN:
            f = FilaCapa(ctrl, capa, compacto)
            self.filas[capa] = f
            v.addWidget(f)
        ctrl.mezclador.cambio.connect(self.refrescar)
        ctrl.cambio.connect(self.refrescar)
        self.refrescar()

    def _volumen_base(self, x):
        r = self.ctrl.r
        if r is not None:
            r.fijar_volumen(round(x * 100))
        self.etq_base.setText(f"{round(x * 100)}")

    def refrescar(self):
        r = self.ctrl.r
        vol = int(getattr(r, "volumen", 80)) if r is not None else 80
        self.vol_base.set_valor(vol / 100.0)
        self.etq_base.setText(f"{vol}")
        f = self.ctrl.factor_enfoque()
        if self.ctrl.hay_bloque() and f < 1.0:
            self.sub.setText("Baja un poco mientras te concentras")
        else:
            self.sub.setText("La música del perfil que elegiste")
        for fila in self.filas.values():
            fila.refrescar()


# ---------------------------------------------------------------------- notas

class CampoNota(QPlainTextEdit):
    guardar = Signal()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and e.modifiers() & Qt.ControlModifier:
            self.guardar.emit()
            return
        super().keyPressEvent(e)


class TarjetaNota(QFrame):
    def __init__(self, ctrl, nota, al_cambiar, padre=None):
        super().__init__(padre)
        self.setObjectName("nota_estudio")
        self.ctrl, self.nota, self.al_cambiar = ctrl, nota, al_cambiar
        self.setStyleSheet(f"QFrame#nota_estudio{{background:rgba(255,255,255,12);border:none;"
                           f"border-radius:12px;}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 10, 8)
        v.setSpacing(4)
        cab = QHBoxLayout()
        fecha = QLabel(E.fecha_amable(nota.get("fecha")))
        fecha.setObjectName("ayuda")
        fecha.setStyleSheet("background:transparent;")
        cab.addWidget(fecha)
        cab.addStretch(1)
        self.bt_copiar = QPushButton("Copiar")
        self.bt_borrar = QPushButton("Borrar")
        for b in (self.bt_copiar, self.bt_borrar):
            b.setObjectName("enlace")
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setStyleSheet(f"QPushButton{{background:transparent;border:none;color:{C['texto2']};"
                            "font-size:12px;font-weight:600;padding:2px 6px;}}"
                            f"QPushButton:hover{{color:{C['texto']};}}")
            cab.addWidget(b)
        self.bt_copiar.clicked.connect(self._copiar)
        self.bt_borrar.clicked.connect(self._borrar)
        v.addLayout(cab)
        texto = QLabel(nota["texto"])
        texto.setWordWrap(True)
        texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        texto.setStyleSheet("font-size:13.5px;background:transparent;")
        v.addWidget(texto)

    def _copiar(self):
        QGuiApplication.clipboard().setText(self.nota["texto"])
        self.bt_copiar.setText("Copiado")
        QTimer.singleShot(1400, lambda: self.bt_copiar.setText("Copiar"))

    def _borrar(self):
        self.ctrl.notas.borrar(self.nota["id"])
        self.al_cambiar(self.nota)


class PanelNotas(QFrame):
    """«Captura de ideas»: panel emergente ligero para anotar sin salir de lo que haces."""

    cerrado = Signal()

    def __init__(self, ctrl, padre):
        super().__init__(padre)
        self.setObjectName("notas_estudio")
        self.ctrl = ctrl
        self.setFixedWidth(392)
        self.limite_inferior = None      # y bajo la que no debe llegar (p. ej. los controles)
        self.setStyleSheet(
            f"QFrame#notas_estudio{{background:{C['panel']};border:1px solid {C['borde_claro']};"
            "border-radius:18px;}")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)
        cab = QHBoxLayout()
        t = QLabel("Captura de ideas")
        t.setStyleSheet("font-size:16px;font-weight:800;background:transparent;")
        cab.addWidget(t)
        self.cuenta = QLabel("")
        self.cuenta.setObjectName("ayuda")
        self.cuenta.setStyleSheet("background:transparent;")
        cab.addWidget(self.cuenta)
        cab.addStretch(1)
        x = BotonIcono("cerrar", 16, "Cerrar (Esc)", 28)
        x.clicked.connect(self.cerrar)
        cab.addWidget(x)
        v.addLayout(cab)
        self.campo = CampoNota()
        self.campo.setPlaceholderText("Anota lo que se te ocurra y sigue con lo tuyo…")
        self.campo.setFixedHeight(84)
        self.campo.setTabChangesFocus(True)
        self.campo.guardar.connect(self.guardar)
        v.addWidget(self.campo)
        pie = QHBoxLayout()
        ayuda = QLabel("Ctrl + Intro para guardar")
        ayuda.setObjectName("ayuda")
        ayuda.setStyleSheet("background:transparent;")
        pie.addWidget(ayuda)
        pie.addStretch(1)
        self.bt_guardar = QPushButton("Guardar idea")
        self.bt_guardar.setObjectName("principal")
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.setStyleSheet("QPushButton#principal{padding:7px 18px;}")
        self.bt_guardar.clicked.connect(self.guardar)
        pie.addWidget(self.bt_guardar)
        v.addLayout(pie)
        self.deshacer = QPushButton("")
        self.deshacer.setCursor(Qt.PointingHandCursor)
        self.deshacer.setStyleSheet(f"QPushButton{{background:transparent;border:none;"
                                    f"color:{C['texto2']};font-size:12px;text-align:left;padding:2px 0;}}"
                                    f"QPushButton:hover{{color:{C['texto']};}}")
        self.deshacer.clicked.connect(self._deshacer)
        self.deshacer.hide()
        self._ultima = None
        v.addWidget(self.deshacer)
        self.area = QScrollArea()
        self.area.setObjectName("lienzo")
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setMinimumHeight(120)
        self.area.setMaximumHeight(260)
        self.cuerpo = QWidget()
        self.cuerpo.setStyleSheet("background:transparent;")
        self.lista = QVBoxLayout(self.cuerpo)
        self.lista.setContentsMargins(0, 0, 4, 0)
        self.lista.setSpacing(8)
        self.area.setWidget(self.cuerpo)
        suavizar(self.area)
        v.addWidget(self.area)
        self.hide()
        self.refrescar()

    def refrescar(self):
        while self.lista.count():
            it = self.lista.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        notas = self.ctrl.notas.todas()
        self.cuenta.setText(f"· {len(notas)}" if notas else "")
        if not notas:
            vacio = QLabel("Aún no hay ideas.\nAnota lo que se te cruce por la cabeza y vuelve "
                           "a tu tarea sin perder el hilo.")
            vacio.setAlignment(Qt.AlignCenter)
            vacio.setWordWrap(True)
            vacio.setObjectName("ayuda")
            vacio.setStyleSheet("background:transparent;padding:18px 8px;font-size:12.5px;")
            self.lista.addWidget(vacio)
        for n in notas[:60]:
            self.lista.addWidget(TarjetaNota(self.ctrl, n, self._borrada))
        self.lista.addStretch(1)
        self.adjustSize()

    def guardar(self):
        texto = self.campo.toPlainText().strip()
        if not texto:
            return
        self.ctrl.notas.anadir(texto)
        self.campo.clear()
        self.deshacer.hide()
        self.refrescar()
        self.colocar()

    def _borrada(self, nota):
        self._ultima = nota
        self.deshacer.setText("Idea borrada · Deshacer")
        self.deshacer.show()
        QTimer.singleShot(6000, self._olvidar)
        self.refrescar()
        self.colocar()

    def _olvidar(self):
        self._ultima = None
        try:
            self.deshacer.hide()
        except RuntimeError:
            pass

    def _deshacer(self):
        if self._ultima:
            self.ctrl.notas.deshacer_borrado(self._ultima)
        self._olvidar()
        self.refrescar()
        self.colocar()

    def abrir(self):
        self.refrescar()
        self.colocar()
        self.show()
        self.raise_()
        self.campo.setFocus()

    def cerrar(self):
        self.hide()
        self.cerrado.emit()

    def alternar(self):
        if self.isVisible():
            self.cerrar()
        else:
            self.abrir()

    def colocar(self):
        padre = self.parentWidget()
        if padre is None:
            return
        self.adjustSize()
        x = padre.width() - self.width() - 28
        base = self.limite_inferior if self.limite_inferior is not None else padre.height() - 120
        y = max(20, base - self.height())
        self.move(max(12, x), y)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cerrar()
        else:
            super().keyPressEvent(e)


# ---------------------------------------------------------------------- salida

class BotonMantener(QPushButton):
    """Un botón que hay que mantener pulsado (2 s) para que cuente: contra clics sin querer."""

    completado = Signal()

    def __init__(self, texto, segundos=2.0, reloj=time.monotonic, padre=None):
        super().__init__(texto, padre)
        self.texto_base = texto
        self.segundos = float(segundos)
        self._reloj = reloj
        self._inicio = None
        self.progreso = 0.0
        self._t = QTimer(self)
        self._t.setInterval(16)
        self._t.timeout.connect(self._paso)
        self.setCursor(Qt.PointingHandCursor)

    def comenzar(self):
        self._inicio = self._reloj()
        self.progreso = 0.0
        self._t.start()
        self.update()

    def soltar(self):
        self._t.stop()
        self._inicio = None
        self.progreso = 0.0
        self.update()

    def _paso(self):
        if self._inicio is None:
            return
        self.progreso = max(0.0, min(1.0, (self._reloj() - self._inicio) / self.segundos))
        self.update()
        if self.progreso >= 1.0:
            self.soltar()
            self.completado.emit()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.comenzar()

    def mouseReleaseEvent(self, e):
        self.soltar()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter) and not e.isAutoRepeat():
            self.comenzar()
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter) and not e.isAutoRepeat():
            self.soltar()
        else:
            super().keyReleaseEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.progreso > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
            ruta = QPainterPath()
            ruta.addRoundedRect(r, r.height() / 2, r.height() / 2)
            p.setClipPath(ruta)
            p.fillRect(QRectF(r.left(), r.top(), r.width() * self.progreso, r.height()),
                       con_alfa(C["acento"], 90))


class ConfirmaSalida(QWidget):
    """«¿Salir de tu sesión de estudio?»: un aviso propio (no un cuadro del sistema) sobre
    toda la ventana, con «Seguir estudiando» y «Salir». Con el candado puesto, «Salir» se
    mantiene pulsado 2 segundos."""

    seguir = Signal()
    salir = Signal()

    def __init__(self, padre, candado=False, resumen="", segundos=2.0, reloj=time.monotonic):
        super().__init__(padre)
        self.candado = bool(candado)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.tarjeta = QFrame(self)
        self.tarjeta.setObjectName("confirma_estudio")
        self.tarjeta.setFixedWidth(440)
        self.tarjeta.setStyleSheet(
            f"QFrame#confirma_estudio{{background:{C['panel']};border:1px solid {C['borde_claro']};"
            "border-radius:22px;}")
        v = QVBoxLayout(self.tarjeta)
        v.setContentsMargins(32, 30, 32, 26)
        v.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icono_estudio("hoja", 30, C["acento"]))
        ic.setStyleSheet("background:transparent;")
        v.addWidget(ic)
        v.addSpacing(4)
        self.titulo = QLabel("¿Salir de tu sesión de estudio?")
        self.titulo.setWordWrap(True)
        self.titulo.setStyleSheet("font-size:21px;font-weight:800;background:transparent;")
        v.addWidget(self.titulo)
        self.texto = QLabel(resumen or "Tienes un bloque en curso.")
        self.texto.setWordWrap(True)
        self.texto.setStyleSheet(f"font-size:13.5px;color:{C['texto2']};background:transparent;")
        v.addWidget(self.texto)
        v.addSpacing(14)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.bt_salir = (BotonMantener("Mantén pulsado para salir", segundos, reloj)
                         if self.candado else QPushButton("Salir"))
        self.bt_salir.setObjectName("contorno")
        self.bt_salir.setCursor(Qt.PointingHandCursor)
        self.bt_salir.setMinimumHeight(40)
        if self.candado:
            self.bt_salir.completado.connect(self.salir.emit)
        else:
            self.bt_salir.clicked.connect(self.salir.emit)
        self.bt_seguir = QPushButton("Seguir estudiando")
        self.bt_seguir.setObjectName("principal")
        self.bt_seguir.setCursor(Qt.PointingHandCursor)
        self.bt_seguir.setMinimumHeight(40)
        self.bt_seguir.clicked.connect(self.seguir.emit)
        self.bt_seguir.setDefault(True)
        fila.addWidget(self.bt_salir, 1)
        fila.addWidget(self.bt_seguir, 1)
        v.addLayout(fila)
        if self.candado:
            nota = QLabel("El candado está puesto: así no sales por accidente.")
            nota.setObjectName("ayuda")
            nota.setStyleSheet("background:transparent;")
            v.addWidget(nota)
        padre.installEventFilter(self)
        self.ajustar()
        self.show()
        self.raise_()
        self.bt_seguir.setFocus()

    def ajustar(self):
        p = self.parentWidget()
        if p is not None:
            self.setGeometry(p.rect())
        self.tarjeta.adjustSize()
        self.tarjeta.move((self.width() - self.tarjeta.width()) // 2,
                          (self.height() - self.tarjeta.height()) // 2)

    def eventFilter(self, obj, ev):
        if obj is self.parentWidget() and ev.type() == QEvent.Resize:
            self.ajustar()
        return False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.ajustar()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(4, 5, 8, 190))

    def mousePressEvent(self, e):
        e.accept()          # el fondo oscuro no deja pasar clics a lo de atrás

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.seguir.emit()
        else:
            super().keyPressEvent(e)

    def cerrar(self):
        p = self.parentWidget()
        if p is not None:
            p.removeEventFilter(self)
        self.hide()
        self.deleteLater()
