# -*- coding: utf-8 -*-
"""Lista «Seguir escuchando»: lo último que sonó, en un panel de vidrio con filas
desplazables. Cada fila tiene miniatura, título y artista; la que suena lleva una barra
de acento a la izquierda y un ecualizador animado a la derecha.

Debajo de las recientes puede haber una segunda sección, «Según lo que suena», con las
pistas recomendadas (mismo estilo de fila). Todo el contenido se desplaza junto.
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

MAXIMO = 30                 # pistas guardadas como mucho (en cada sección)
ALTO_FILA = 50
MINIATURA = 36
RADIO_MINIATURA = 8
MARGEN_PANEL = 14
PADDING = 16
ALTO_CABECERA = 50          # desde el borde interior del panel hasta la primera fila
ALTO_ENCABEZADO_REC = 30    # bloque «Según lo que suena»: separador, rótulo y margen
FILAS_FANTASMA = 3          # filas de marcador mientras se cargan las recomendadas
FADE = 28                   # alto del desvanecimiento en el borde superior e inferior
PASO_RUEDA = 100.0          # píxeles por muesca de la rueda
VELOCIDAD_DESP = 10.0       # acercamiento exponencial (1/s) del desplazamiento
FPS_EQUALIZADOR = 12
FPS_FANTASMAS = 12


def _artista(pista):
    """Nombre del artista: la clave «artista»; si no, «artistas» (lista o texto)."""
    a = pista.get("artista")
    if not a:
        lista = pista.get("artistas")
        if isinstance(lista, (list, tuple)):
            a = ", ".join(str(x) for x in lista if x)
        elif lista:
            a = str(lista)
    return str(a or "")


class ListaSeguir(QWidget):
    """Panel translúcido con lo que sonó hace poco y, opcionalmente, pistas recomendadas.
    Clic en una fila emite `elegida(pista)`."""

    elegida = Signal(dict)

    def __init__(self, padre=None):
        super().__init__(padre)
        preparar_transparente(self)
        self.setMouseTracking(True)

        self._pistas = []
        self._recomendadas = []
        self._cargando_rec = False
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
        self._hover = None                # ("pista", i) | ("sugerida", i) | None

        self._tmr_desp = QTimer(self)
        self._tmr_desp.setInterval(16)
        self._tmr_desp.timeout.connect(self._tic_desplazamiento)

        self._tmr_eq = QTimer(self)
        self._tmr_eq.setInterval(int(1000 / FPS_EQUALIZADOR))
        self._tmr_eq.timeout.connect(self._tic_equalizador)

        self._tmr_fantasmas = QTimer(self)
        self._tmr_fantasmas.setInterval(int(1000 / FPS_FANTASMAS))
        self._tmr_fantasmas.timeout.connect(self._tic_fantasmas)

        self._f_titulo = fuente(14, QFont.DemiBold)
        self._f_sub = fuente(11)
        self._f_pista = fuente(13, QFont.DemiBold)
        self._f_artista = fuente(12)

    # ---- API pública ----

    def sizeHint(self):
        return QSize(290, 560)

    def poner(self, pistas):
        """Reemplaza la lista de recientes (como mucho 30 pistas) y vuelve arriba."""
        self._pistas = [dict(p) for p in list(pistas)[:MAXIMO]]
        self._podar_miniaturas()
        self._desp = self._destino = 0.0
        self._hover = None
        self._tmr_desp.stop()
        self.update()
        self._gestionar_equalizador()
        self._gestionar_fantasmas()

    def poner_recomendadas(self, pistas):
        """Reemplaza la sección «Según lo que suena» (como mucho 30). Lista vacía = no se muestra.
        No vuelve arriba: sólo recorta el desplazamiento si el contenido se encoge."""
        self._recomendadas = [dict(p) for p in list(pistas or [])[:MAXIMO]]
        self._podar_miniaturas()
        if self._hover is not None and self._hover[0] == "sugerida":
            self._hover = None
        self._clampar_desplazamiento()
        self._gestionar_equalizador()
        self._gestionar_fantasmas()
        self.update()

    def fijar_cargando_recomendadas(self, si):
        """Si es True y aún no hay recomendadas, bajo el encabezado se ven filas fantasma."""
        self._cargando_rec = bool(si)
        self._clampar_desplazamiento()
        self._gestionar_fantasmas()
        self.update()

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
        """Rectángulo de la fila i de recientes, en coordenadas del widget, con el desplazamiento."""
        panel = self._panel()
        zona = self._zona_filas()
        return QRectF(panel.left() + 8, zona.top() + i * ALTO_FILA - self._desp,
                      panel.width() - 16, ALTO_FILA)

    def rect_fila_recomendada(self, i):
        """Rectángulo de la fila i de la sección recomendada (también las fantasma)."""
        panel = self._panel()
        zona = self._zona_filas()
        arriba = zona.top() + self._y_encabezado_rec() + ALTO_ENCABEZADO_REC + i * ALTO_FILA
        return QRectF(panel.left() + 8, arriba - self._desp, panel.width() - 16, ALTO_FILA)

    # ---- geometría ----

    def _panel(self):
        return QRectF(self.rect()).adjusted(MARGEN_PANEL, MARGEN_PANEL, -MARGEN_PANEL, -MARGEN_PANEL)

    def _zona_filas(self):
        panel = self._panel()
        arriba = panel.top() + PADDING + ALTO_CABECERA
        return QRectF(panel.left(), arriba, panel.width(), panel.bottom() - 10 - arriba)

    def _y_encabezado_rec(self):
        """Posición, en el contenido sin desplazar, del bloque «Según lo que suena»."""
        return len(self._pistas) * ALTO_FILA

    def _filas_rec(self):
        """Filas de la sección recomendada: las pistas, o las fantasma mientras carga."""
        if self._recomendadas:
            return len(self._recomendadas)
        return FILAS_FANTASMA if self._cargando_rec else 0

    def _hay_seccion_rec(self):
        return self._filas_rec() > 0

    def _mostrar_fantasmas(self):
        return self._cargando_rec and not self._recomendadas

    def _contenido_alto(self):
        alto = len(self._pistas) * ALTO_FILA
        if self._hay_seccion_rec():
            alto += ALTO_ENCABEZADO_REC + self._filas_rec() * ALTO_FILA
        return alto

    def _max_desp(self):
        return max(0.0, self._contenido_alto() - self._zona_filas().height())

    def _clampar_desplazamiento(self):
        mx = self._max_desp()
        self._destino = min(self._destino, mx)
        self._desp = min(self._desp, mx)

    def _fila_en(self, punto):
        zona = self._zona_filas()
        if not zona.contains(QPointF(punto)):
            return None
        i = int((punto.y() - zona.top() + self._desp) // ALTO_FILA)
        if 0 <= i < len(self._pistas) and self.rect_fila(i).contains(QPointF(punto)):
            return i
        return None

    def _fila_recomendada_en(self, punto):
        if not self._zona_filas().contains(QPointF(punto)):
            return None
        for i in range(len(self._recomendadas)):
            if self.rect_fila_recomendada(i).contains(QPointF(punto)):
                return i
        return None

    def _fila_bajo(self, punto):
        i = self._fila_en(punto)
        if i is not None:
            return ("pista", i)
        j = self._fila_recomendada_en(punto)
        if j is not None:
            return ("sugerida", j)
        return None

    def _clave(self, pista):
        return pista.get("clave") or pista.get("video_id")

    def _es_actual(self, pista):
        return self._clave_actual is not None and self._clave(pista) == self._clave_actual

    def _fila_actual_visible(self):
        zona = self._zona_filas()
        for i, pista in enumerate(self._pistas):
            if self._es_actual(pista):
                return self.rect_fila(i).intersects(zona)
        for i, pista in enumerate(self._recomendadas):
            if self._es_actual(pista):
                return self.rect_fila_recomendada(i).intersects(zona)
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
        if not self._pistas and not self._hay_seccion_rec():
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
                if self._fuera(fila, zona):
                    continue
                self._pintar_fila(lp, pista, fila, self._hover == ("pista", i))
            if self._hay_seccion_rec():
                self._pintar_encabezado_rec(lp, zona)
                self._pintar_seccion_rec(lp, zona)
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

    @staticmethod
    def _fuera(fila, zona):
        return fila.bottom() < zona.top() or fila.top() > zona.bottom()

    def _pintar_encabezado_rec(self, p, zona):
        """Separador fino de 1 px y rótulo «Según lo que suena», con el estilo del subtítulo."""
        c = self._panel().adjusted(PADDING, 0, -PADDING, 0)
        arriba = zona.top() + self._y_encabezado_rec() - self._desp
        if self._fuera(QRectF(c.left(), arriba, c.width(), ALTO_ENCABEZADO_REC), zona):
            return
        p.fillRect(QRectF(c.left(), arriba + 6, c.width(), 1), QColor(255, 255, 255, 28))
        p.setFont(self._f_sub)
        p.setPen(TEXTO_3)
        p.drawText(QRectF(c.left(), arriba + 10, c.width(), 16), Qt.AlignLeft | Qt.AlignVCenter,
                   "Según lo que suena")

    def _pintar_seccion_rec(self, p, zona):
        if self._recomendadas:
            for i, pista in enumerate(self._recomendadas):
                fila = self.rect_fila_recomendada(i)
                if self._fuera(fila, zona):
                    continue
                self._pintar_fila(p, pista, fila, self._hover == ("sugerida", i))
        elif self._cargando_rec:
            t = time.monotonic()
            for i in range(FILAS_FANTASMA):
                fila = self.rect_fila_recomendada(i)
                if self._fuera(fila, zona):
                    continue
                self._pintar_fantasma(p, fila, t, i)

    def _pintar_fantasma(self, p, fila, t, orden):
        """Fila de marcador: rectángulos redondeados blancos con alfa que respira entre 8 y 18."""
        alfa = 8 + 10 * (0.5 + 0.5 * math.sin(t * 2.2 - orden * 0.7))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, round(alfa)))
        tr = QRectF(fila.left() + 8, fila.top() + 7, MINIATURA, MINIATURA)
        p.drawRoundedRect(tr, RADIO_MINIATURA, RADIO_MINIATURA)
        tx = tr.right() + 10
        ancho = fila.right() - 10 - tx
        p.drawRoundedRect(QRectF(tx, fila.top() + 12, ancho * 0.6, 10), 5, 5)
        p.drawRoundedRect(QRectF(tx, fila.top() + 29, ancho * 0.4, 8), 4, 4)

    def _pintar_fila(self, p, pista, fila, sobre=False):
        actual = self._es_actual(pista)
        acento = acento_legible(self._brillo)

        if sobre:
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
            _artista(pista), Qt.ElideRight, int(ancho))
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

    def _podar_miniaturas(self):
        """Conserva sólo las miniaturas de las pistas que hay ahora (recientes y recomendadas)."""
        validos = {p.get("miniatura") for p in self._pistas + self._recomendadas}
        self._miniaturas = {u: v for u, v in self._miniaturas.items() if u in validos}
        self._pendientes = {u for u in self._pendientes if u in validos}

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
        self._gestionar_fantasmas()

    def hideEvent(self, evento):
        self._tmr_desp.stop()
        self._tmr_eq.stop()
        self._tmr_fantasmas.stop()
        super().hideEvent(evento)

    def _gestionar_equalizador(self):
        debe = a_la_vista(self) and self._fila_actual_visible()
        if debe and not self._tmr_eq.isActive():
            self._tmr_eq.start()
        elif not debe and self._tmr_eq.isActive():
            self._tmr_eq.stop()

    def _gestionar_fantasmas(self):
        debe = self._mostrar_fantasmas() and a_la_vista(self)
        if debe and not self._tmr_fantasmas.isActive():
            self._tmr_fantasmas.start()
        elif not debe and self._tmr_fantasmas.isActive():
            self._tmr_fantasmas.stop()

    def _tic_fantasmas(self):
        if not a_la_vista(self) or not self._mostrar_fantasmas():
            self._tmr_fantasmas.stop()
            return
        self.update()

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
            j = self._fila_recomendada_en(evento.position())
            if j is not None:
                self.elegida.emit(dict(self._recomendadas[j]))
                evento.accept()
                return
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        h = self._fila_bajo(evento.position())
        if h != self._hover:
            self._hover = h
            self.setCursor(Qt.PointingHandCursor if h is not None else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(evento)

    def leaveEvent(self, evento):
        if self._hover is not None:
            self._hover = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
        super().leaveEvent(evento)
