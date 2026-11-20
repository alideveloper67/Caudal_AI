# -*- coding: utf-8 -*-
"""Lista «Seguir escuchando»: lo último que sonó, en un panel de vidrio con filas
desplazables. Cada fila tiene miniatura, título y artista; la que suena lleva una barra
de acento a la izquierda y un ecualizador animado a la derecha.
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPixmap)
from PySide6.QtWidgets import QWidget

from .. import iconos, imagenes
from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, TEXTO, TEXTO_2, TEXTO_3, acento_legible,
                     fuente, pintar_vidrio, preparar_transparente)

MAXIMO = 30                 # pistas guardadas como mucho
ALTO_FILA = 50
MINIATURA = 36
RADIO_MINIATURA = 8
MARGEN_PANEL = 14
PADDING = 16
ALTO_CABECERA = 50          # desde el borde interior del panel hasta la primera fila
FADE = 28                   # alto del desvanecimiento en el borde superior e inferior
PASO_RUEDA = 100.0          # píxeles por muesca de la rueda
VELOCIDAD_DESP = 10.0       # acercamiento exponencial (1/s) del desplazamiento
FPS_EQUALIZADOR = 12


class ListaSeguir(QWidget):
    """Panel translúcido con lo que sonó hace poco. Clic en una fila emite `elegida(pista)`."""

    elegida = Signal(dict)

    def __init__(self, padre=None):
        super().__init__(padre)
        preparar_transparente(self)
        self.setMouseTracking(True)

        self._pistas = []
        self._clave_actual = None
        self._dom = QColor(DOMINANTE)
        self._seg = QColor(SEGUNDO)       # guardado por la firma de poner_colores; hoy no se dibuja
        self._brillo = QColor(BRILLO)
        self._cargador = imagenes.imagen
        self._miniaturas = {}             # url -> QPixmap redondeado, o None si no hay imagen
        self._pendientes = set()
        self._desp = 0.0                  # desplazamiento que se ve (píxeles)
        self._destino = 0.0              # desplazamiento al que se acerca
        self._t_desp = 0.0
        self._hover = None

        self._tmr_desp = QTimer(self)
        self._tmr_desp.setInterval(16)
        self._tmr_desp.timeout.connect(self._tic_desplazamiento)

        self._tmr_eq = QTimer(self)
        self._tmr_eq.setInterval(int(1000 / FPS_EQUALIZADOR))
        self._tmr_eq.timeout.connect(self._tic_equalizador)

        self._f_titulo = fuente(14, QFont.DemiBold)
        self._f_sub = fuente(11)
        self._f_pista = fuente(13, QFont.DemiBold)
        self._f_artista = fuente(12)

    # ---- API pública ----

    def sizeHint(self):
        return QSize(290, 560)

    def poner(self, pistas):
        """Reemplaza la lista (como mucho 30 pistas) y vuelve arriba."""
        self._pistas = [dict(p) for p in list(pistas)[:MAXIMO]]
        validos = {p.get("miniatura") for p in self._pistas}
        self._miniaturas = {u: v for u, v in self._miniaturas.items() if u in validos}
        self._pendientes = {u for u in self._pendientes if u in validos}
        self._desp = self._destino = 0.0
        self._hover = None
        self._tmr_desp.stop()
        self.update()
        self._gestionar_equalizador()

    def marcar_actual(self, clave):
        """Marca la pista que suena (por su clave; None quita la marca)."""
        self._clave_actual = clave or None
        self.update()
        self._gestionar_equalizador()

    def fijar_cargador(self, funcion):
        """Cambia cómo se bajan las miniaturas: `funcion(url, callback)`, callback(QImage)."""
        self._cargador = funcion
        self._pendientes.clear()
        self._miniaturas.clear()
        self.update()

    def poner_colores(self, dominante, segundo, brillo):
        self._dom = QColor(dominante)
        self._seg = QColor(segundo)
        self._brillo = QColor(brillo)
        self.update()

    def rect_fila(self, i):
        """Rectángulo de la fila i en coordenadas del widget, con el desplazamiento aplicado."""
        panel = self._panel()
        zona = self._zona_filas()
        return QRectF(panel.left() + 8, zona.top() + i * ALTO_FILA - self._desp,
                      panel.width() - 16, ALTO_FILA)

    # ---- geometría ----

    def _panel(self):
        return QRectF(self.rect()).adjusted(MARGEN_PANEL, MARGEN_PANEL, -MARGEN_PANEL, -MARGEN_PANEL)

    def _zona_filas(self):
        panel = self._panel()
        arriba = panel.top() + PADDING + ALTO_CABECERA
        return QRectF(panel.left(), arriba, panel.width(), panel.bottom() - 10 - arriba)

    def _max_desp(self):
        return max(0.0, len(self._pistas) * ALTO_FILA - self._zona_filas().height())

    def _fila_en(self, punto):
        zona = self._zona_filas()
        if not zona.contains(QPointF(punto)):
            return None
        i = int((punto.y() - zona.top() + self._desp) // ALTO_FILA)
        if 0 <= i < len(self._pistas) and self.rect_fila(i).contains(QPointF(punto)):
            return i
        return None

    def _clave(self, pista):
        return pista.get("clave") or pista.get("video_id")

    def _es_actual(self, pista):
        return self._clave_actual is not None and self._clave(pista) == self._clave_actual

    def _fila_actual_visible(self):
        for i, pista in enumerate(self._pistas):
            if self._es_actual(pista):
                return self.rect_fila(i).intersects(self._zona_filas())
        return False

    # ---- pintura ----

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        panel = self._panel()
        pintar_vidrio(p, panel, radio=20, acento=self._dom)
        self._pintar_cabecera(p, panel)
        zona = self._zona_filas()
        if not self._pistas:
            p.setFont(self._f_artista)
            p.setPen(TEXTO_3)
            p.drawText(zona, Qt.AlignCenter | Qt.TextWordWrap, "Aquí aparecerá lo que escuches")
        else:
            self._pintar_filas(p, zona)
        p.end()

    def _pintar_cabecera(self, p, panel):
        c = panel.adjusted(PADDING, PADDING, -PADDING, -PADDING)
        p.setFont(self._f_titulo)
        p.setPen(TEXTO)
        p.drawText(QRectF(c.left(), c.top(), c.width(), 20), Qt.AlignLeft | Qt.AlignVCenter,
                   "Seguir escuchando")
        p.setFont(self._f_sub)
        p.setPen(TEXTO_3)
        p.drawText(QRectF(c.left(), c.top() + 22, c.width(), 16), Qt.AlignLeft | Qt.AlignVCenter,
                   "Lo último que sonó")

    def _pintar_filas(self, p, zona):
        """Las filas van a una capa propia para poder desvanecer los bordes con DestinationOut."""
        dpr = self.devicePixelRatioF()
        capa = QPixmap(max(1, round(zona.width() * dpr)), max(1, round(zona.height() * dpr)))
        capa.setDevicePixelRatio(dpr)
        capa.fill(Qt.transparent)

        lp = QPainter(capa)
        try:
            lp.setRenderHint(QPainter.Antialiasing, True)
            lp.setRenderHint(QPainter.TextAntialiasing, True)
            lp.setRenderHint(QPainter.SmoothPixmapTransform, True)
            lp.translate(-zona.left(), -zona.top())
            for i, pista in enumerate(self._pistas):
                fila = self.rect_fila(i)
                if fila.bottom() < zona.top() or fila.top() > zona.bottom():
                    continue
                self._pintar_fila(lp, i, pista, fila)
        finally:
            lp.end()

        # desvanecimiento donde hay más contenido, arriba y abajo
        ancho, alto = zona.width(), zona.height()
        lp = QPainter(capa)
        try:
            lp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            lp.setPen(Qt.NoPen)
            if self._desp > 0.5:
                g = QLinearGradient(0, 0, 0, FADE)
                g.setColorAt(0.0, QColor(0, 0, 0, 255))
                g.setColorAt(1.0, QColor(0, 0, 0, 0))
                lp.fillRect(QRectF(0, 0, ancho, FADE), QBrush(g))
            if self._desp < self._max_desp() - 0.5:
                g = QLinearGradient(0, alto - FADE, 0, alto)
                g.setColorAt(0.0, QColor(0, 0, 0, 0))
                g.setColorAt(1.0, QColor(0, 0, 0, 255))
                lp.fillRect(QRectF(0, alto - FADE, ancho, FADE), QBrush(g))
        finally:
            lp.end()

        p.drawPixmap(zona.topLeft(), capa)

    def _pintar_fila(self, p, i, pista, fila):
        actual = self._es_actual(pista)
        acento = acento_legible(self._brillo)

        if i == self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 20))
            p.drawRoundedRect(fila, 10, 10)

        if actual:
            p.setPen(Qt.NoPen)
            p.setBrush(acento)
            p.drawRoundedRect(QRectF(fila.left() + 1, fila.center().y() - 11, 3, 22), 1.5, 1.5)

        tr = QRectF(fila.left() + 8, fila.top() + 7, MINIATURA, MINIATURA)
        self._pintar_miniatura(p, pista.get("miniatura"), tr)

        tx = tr.right() + 10
        derecha = fila.right() - 10 - (22 if actual else 0)
        ancho = max(10.0, derecha - tx)

        p.setFont(self._f_pista)
        p.setPen(acento if actual else TEXTO)
        titulo = QFontMetrics(self._f_pista).elidedText(
            str(pista.get("titulo") or "Sin título"), Qt.ElideRight, int(ancho))
        p.drawText(QRectF(tx, fila.top() + 8, ancho, 18), Qt.AlignLeft | Qt.AlignVCenter, titulo)

        p.setFont(self._f_artista)
        p.setPen(TEXTO_2)
        artista = QFontMetrics(self._f_artista).elidedText(
            str(pista.get("artista") or ""), Qt.ElideRight, int(ancho))
        p.drawText(QRectF(tx, fila.top() + 27, ancho, 16), Qt.AlignLeft | Qt.AlignVCenter, artista)

        if actual:
            self._pintar_equalizador(p, QRectF(fila.right() - 22, fila.center().y() - 6, 12, 12))

    def _pintar_miniatura(self, p, url, tr):
        pm = self._miniatura(url)
        if pm is not None:
            p.drawPixmap(tr.topLeft(), pm)      # tamaño lógico de 36 px (ver _redondear)
            return
        # cargando o sin imagen: cuadro blanco al 25 % con el icono de música
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 25))
        p.drawRoundedRect(tr, RADIO_MINIATURA, RADIO_MINIATURA)
        icono = iconos.pixmap("musica", 16, TEXTO_2)
        p.drawPixmap(QPointF(tr.center().x() - 8, tr.center().y() - 8), icono)

    def _pintar_equalizador(self, p, area):
        """Tres barritas que suben y bajan con el reloj (no con los tics del timer)."""
        t = time.monotonic()
        p.setPen(Qt.NoPen)
        p.setBrush(acento_legible(self._brillo))
        for k in range(3):
            onda = 0.5 + 0.5 * math.sin(t * 6.0 + k * 2.1)
            alto = 4 + 8 * onda
            x = area.left() + k * 4.5
            p.drawRoundedRect(QRectF(x, area.bottom() - alto, 3, alto), 1.5, 1.5)

    # ---- miniaturas ----

    def _miniatura(self, url):
        if not url:
            return None
        if url in self._miniaturas:
            return self._miniaturas[url]
        if url not in self._pendientes:
            self._pendientes.add(url)
            self._cargador(url, lambda img, u=url: self._llego(u, img))
        return self._miniaturas.get(url)

    def _llego(self, url, img):
        self._pendientes.discard(url)
        pm = None if img is None or img.isNull() else self._redondear(img)
        self._miniaturas[url] = pm
        self.update()

    def _redondear(self, img):
        dpr = self.devicePixelRatioF()
        lado = max(1, round(MINIATURA * dpr))
        escalada = img.scaled(lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (escalada.width() - lado) // 2
        y = (escalada.height() - lado) // 2
        pm = QPixmap(lado, lado)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        try:
            q.setRenderHint(QPainter.Antialiasing, True)
            q.setRenderHint(QPainter.SmoothPixmapTransform, True)
            camino = QPainterPath()
            camino.addRoundedRect(QRectF(0, 0, lado, lado), RADIO_MINIATURA * dpr, RADIO_MINIATURA * dpr)
            q.setClipPath(camino)
            q.drawImage(QRectF(0, 0, lado, lado), escalada, QRectF(x, y, lado, lado))
        finally:
            q.end()
        pm.setDevicePixelRatio(dpr)
        return pm

    # ---- animación ----

    def showEvent(self, evento):
        super().showEvent(evento)
        if self._desp != self._destino:
            self._t_desp = time.monotonic()
            self._tmr_desp.start()
        self._gestionar_equalizador()

    def hideEvent(self, evento):
        self._tmr_desp.stop()
        self._tmr_eq.stop()
        super().hideEvent(evento)

    def _gestionar_equalizador(self):
        debe = a_la_vista(self) and self._fila_actual_visible()
        if debe and not self._tmr_eq.isActive():
            self._tmr_eq.start()
        elif not debe and self._tmr_eq.isActive():
            self._tmr_eq.stop()

    def _tic_equalizador(self):
        if not a_la_vista(self) or not self._fila_actual_visible():
            self._tmr_eq.stop()
            return
        self.update()

    def _tic_desplazamiento(self):
        if not a_la_vista(self):
            self._desp = self._destino
            self._tmr_desp.stop()
            return
        ahora = time.monotonic()
        dt = min(0.1, ahora - self._t_desp)
        self._t_desp = ahora
        self._desp += (self._destino - self._desp) * (1.0 - math.exp(-VELOCIDAD_DESP * dt))
        if abs(self._destino - self._desp) < 0.25:
            self._desp = self._destino
            self._tmr_desp.stop()
        self._gestionar_equalizador()
        self.update()

    # ---- ratón ----

    def wheelEvent(self, evento):
        dy = evento.angleDelta().y()
        if dy == 0:
            super().wheelEvent(evento)
            return
        self._destino = min(max(0.0, self._destino - dy / 120.0 * PASO_RUEDA), self._max_desp())
        if not a_la_vista(self):
            self._desp = self._destino
            self.update()
        elif not self._tmr_desp.isActive() and self._desp != self._destino:
            self._t_desp = time.monotonic()
            self._tmr_desp.start()
        evento.accept()

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            i = self._fila_en(evento.position())
            if i is not None:
                self.elegida.emit(dict(self._pistas[i]))
                evento.accept()
                return
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        i = self._fila_en(evento.position())
        if i != self._hover:
            self._hover = i
            self.setCursor(Qt.PointingHandCursor if i is not None else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(evento)

    def leaveEvent(self, evento):
        if self._hover is not None:
            self._hover = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
        super().leaveEvent(evento)
