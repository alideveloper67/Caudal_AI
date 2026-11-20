# -*- coding: utf-8 -*-
"""Tarjeta de la canción que suena: vidrio con carátula, inclinación 3D y dos botones.

Todo se dibuja en un espacio de diseño de 360x520 que se escala y centra para caber en el
widget (factor = min(ancho/360, alto/520), sin pasar de 1.6). La tarjeta entera (vidrio,
carátula, textos, corazón y progreso) se pinta en un QPixmap en caché, al tamaño ya escalado
y multiplicado por devicePixelRatio, que solo se rehace cuando cambian datos, portada,
colores, me gusta, progreso, tamaño o dpr. Cada cuadro se dibuja ese pixmap con una
transformación de perspectiva; el reflejo, el halo y las píldoras "Otra letra" y "Traducir" se
dibujan en vivo.
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QTransform)
from PySide6.QtWidgets import QWidget

from .. import iconos
from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, SOMBRA, TEXTO, TEXTO_2, acento_legible, con_alfa,
                     fuente, pintar_vidrio, preparar_transparente)

ANCHO_SUG, ALTO_SUG = 360, 520          # espacio de diseño (tamaño sugerido del widget)
FACTOR_MAX = 1.6                        # no se agranda más de esto
ANCHO, ALTO = 300, 430                  # la tarjeta de vidrio
MARGEN = int(SOMBRA)                    # aire alrededor de la tarjeta dentro del pixmap (sombra)
RADIO = 22.0                            # esquinas del vidrio
PAD = 14                                # padding de la carátula dentro de la tarjeta
LADO = ANCHO - 2 * PAD                  # carátula cuadrada: 272
RADIO_PORTADA = 16.0
HUECO = 14                              # separación entre la tarjeta y la píldora
ALTO_PILDORA, ANCHO_PILDORA = 30, 140
SEPARACION_PILDORAS = 8                 # hueco entre "Otra letra" y "Traducir"
ANCHO_PAR_PILDORAS = 2 * ANCHO_PILDORA + SEPARACION_PILDORAS   # 288: el par va centrado
DIAM_CORAZON = 34

MAX_ANG = 10.0                          # inclinación máxima con el ratón (grados)
VAIVEN_AMP, VAIVEN_PERIODO = 2.5, 7.0   # vaivén sin ratón (grados, segundos)
FLOTA_AMP, FLOTA_PERIODO = 4.0, 6.0     # flotación vertical (unidades de diseño, segundos)
SUAVIDAD = 6.0                          # velocidad del acercamiento exponencial a los objetivos
PRECISION_PROGRESO = 200                # el progreso se redondea a 1/200 para no rehacer la caché por nada

TITULO_VACIO = "Nada sonando"
ARTISTA_VACIO = "Elige una canción"
FUENTE_POR_DEFECTO = "Sonando en Caudal"


def _texto(p, rect, texto, fuente_, color):
    """Dibuja una línea de texto elidida (con puntos suspensivos) dentro de rect."""
    p.setFont(fuente_)
    p.setPen(color)
    fm = QFontMetrics(fuente_)
    p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter,
               fm.elidedText(texto, Qt.ElideRight, int(rect.width())))


def _cover(img, lado_px):
    """Escala la imagen para cubrir un cuadrado y recorta el centro."""
    esc = img.scaled(QSize(lado_px, lado_px), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (esc.width() - lado_px) // 2
    y = (esc.height() - lado_px) // 2
    return esc.copy(x, y, lado_px, lado_px)


def _lugar_corazon(R):
    """Círculo del corazón: arriba a la derecha, sobre la carátula. R es la tarjeta (diseño)."""
    return QRectF(R.x() + PAD + LADO - 8 - DIAM_CORAZON, R.y() + PAD + 8, DIAM_CORAZON, DIAM_CORAZON)


def _sub(R):
    """Zona de la carátula dentro de la tarjeta R."""
    return QRectF(R.x() + PAD, R.y() + PAD, LADO, LADO)


class TarjetaCancion(QWidget):
    """Tarjeta de la canción que suena. Emite pidio_otra_letra, pidio_traducir y pidio_me_gusta
    al hacer clic."""

    pidio_otra_letra = Signal()
    pidio_traducir = Signal()
    pidio_me_gusta = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        preparar_transparente(self)
        self.setMouseTracking(True)

        # datos que se muestran
        self._pista = None
        self._titulo = TITULO_VACIO
        self._artista = ARTISTA_VACIO
        self._fuente_texto = FUENTE_POR_DEFECTO
        self._portada = None            # QImage original
        self._portada_clave = None      # cacheKey de la original, para saber si cambió
        self._portada_escalada = None   # carátula recortada a cuadrado, al tamaño físico indicado
        self._portada_dpr = None
        self._dominante = QColor(DOMINANTE)
        self._segundo = QColor(SEGUNDO)
        self._brillo = QColor(BRILLO)
        self._me_gusta = False
        self._progreso = 0.0
        self._traduccion_activa = False  # True: la píldora dice "Original" y va resaltada

        # caché de la tarjeta
        self._cache = None
        self._clave_cache = None        # (factor, dpr) con que se pintó la caché
        self._sucia = True
        self._rehechos = 0              # cuántas veces se ha rehecho la caché (para las pruebas)

        # inclinación y flotación (cambian en cada cuadro, no tocan la caché)
        self._ang_x = 0.0
        self._ang_y = 0.0
        self._flota = 0.0
        self._raton = None              # QPointF dentro del widget, o None si no hay ratón
        self._encima = False
        self._pildora_bajo_raton = None  # 0 = "Otra letra", 1 = "Traducir", None = ninguna
        self._t0 = time.monotonic()
        self._ultimo = self._t0

        self._timer = QTimer(self)
        self._timer.setInterval(50)     # 20 fps en reposo (vaivén lento); 60 con el ratón encima
        self._timer.timeout.connect(self._tic)

    # ------------------------------------------------------------------ API pública

    def sizeHint(self):
        return QSize(ANCHO_SUG, ALTO_SUG)

    def poner(self, pista):
        """Pone la canción (dict con titulo, artista, fuente_texto) o None si no suena nada."""
        if pista is None:
            titulo, artista, fuente_t = TITULO_VACIO, ARTISTA_VACIO, FUENTE_POR_DEFECTO
            nueva = None
        else:
            titulo = str(pista.get("titulo") or "Sin título")
            artista = str(pista.get("artista") or "")
            fuente_t = str(pista.get("fuente_texto") or FUENTE_POR_DEFECTO)
            nueva = dict(pista)
        self._pista = nueva
        if (titulo, artista, fuente_t) != (self._titulo, self._artista, self._fuente_texto):
            self._titulo, self._artista, self._fuente_texto = titulo, artista, fuente_t
            self._marcar()

    def poner_portada(self, img):
        """Pone la carátula (QImage) o None para mostrar el degradado con el icono."""
        if img is None or img.isNull():
            clave, nueva = None, None
        else:
            clave, nueva = img.cacheKey(), img
        if clave != self._portada_clave:
            self._portada_clave = clave
            self._portada = nueva
            self._portada_escalada = None
            self._marcar()

    def poner_colores(self, dominante, segundo, brillo):
        """Colores de la carátula: dominante y segundo para el degradado, brillo para el acento."""
        nuevos = (QColor(dominante), QColor(segundo), QColor(brillo))
        actuales = (self._dominante, self._segundo, self._brillo)
        if nuevos != actuales:
            self._dominante, self._segundo, self._brillo = nuevos
            self._marcar()

    def fijar_me_gusta(self, si):
        si = bool(si)
        if si != self._me_gusta:
            self._me_gusta = si
            self._marcar()

    def fijar_progreso(self, fraccion):
        """Progreso de la canción entre 0 y 1 (la línea inferior)."""
        f = max(0.0, min(1.0, float(fraccion)))
        f = round(f * PRECISION_PROGRESO) / PRECISION_PROGRESO
        if f != self._progreso:
            self._progreso = f
            self._marcar()

    def fijar_traduccion(self, activa):
        """Con la traducción activa, la píldora "Traducir" dice "Original" y se resalta.
        No toca la caché: la píldora se pinta en vivo."""
        activa = bool(activa)
        if activa != self._traduccion_activa:
            self._traduccion_activa = activa
            self.update()

    def rect_boton_letra(self):
        """Píldora "Otra letra", ya escalada, en coordenadas del widget y sin inclinación."""
        return self._a_widget(self._pildora_diseno(0))

    def rect_boton_traducir(self):
        """Píldora "Traducir", ya escalada, en coordenadas del widget y sin inclinación."""
        return self._a_widget(self._pildora_diseno(1))

    def rect_corazon(self):
        """Corazón, ya escalado, en coordenadas del widget y sin inclinación."""
        x_t, y_t = self._origen()
        return self._a_widget(_lugar_corazon(QRectF(x_t, y_t, ANCHO, ALTO)))

    # ------------------------------------------------------------------ escala y geometría

    def _factor(self):
        """Escala del espacio de diseño: lo que cabe en el widget, sin pasar de FACTOR_MAX."""
        w = max(1, self.width())
        h = max(1, self.height())
        return max(0.05, min(w / ANCHO_SUG, h / ALTO_SUG, FACTOR_MAX))

    def _transformada_base(self):
        """Del espacio de diseño al widget: centrado y escalado."""
        f = self._factor()
        t = QTransform()
        t.translate(self.width() / 2, self.height() / 2)
        t.scale(f, f)
        t.translate(-ANCHO_SUG / 2, -ALTO_SUG / 2)
        return t

    def _a_widget(self, r):
        """Pasa un rectángulo del espacio de diseño a coordenadas del widget."""
        f = self._factor()
        ox = self.width() / 2 - ANCHO_SUG / 2 * f
        oy = self.height() / 2 - ALTO_SUG / 2 * f
        return QRectF(ox + r.x() * f, oy + r.y() * f, r.width() * f, r.height() * f)

    def _pildora_diseno(self, indice):
        """Píldora en el espacio de diseño (con la flotación): 0 = "Otra letra", 1 = "Traducir".
        El par va centrado bajo la tarjeta, separado por SEPARACION_PILDORAS. Como todo se escala
        con el mismo factor, la separación y el no solapamiento se mantienen a cualquier tamaño."""
        x_t, y_t = self._origen()
        x0 = (ANCHO_SUG - ANCHO_PAR_PILDORAS) / 2
        x = x0 + indice * (ANCHO_PILDORA + SEPARACION_PILDORAS)
        return QRectF(x, y_t + ALTO + HUECO, ANCHO_PILDORA, ALTO_PILDORA)

    def _pildora_en(self, pos):
        """Índice de la píldora bajo pos (en coordenadas del widget), o None."""
        for indice, rect in enumerate((self.rect_boton_letra(), self.rect_boton_traducir())):
            if rect.contains(pos):
                return indice
        return None

    def _marcar(self):
        """Marca la caché como vieja: se rehará en el siguiente dibujo."""
        self._sucia = True
        self.update()

    def _origen(self):
        """Esquina superior izquierda de la tarjeta en el espacio de diseño, con la flotación."""
        x = (ANCHO_SUG - ANCHO) / 2
        y = (ALTO_SUG - (ALTO + HUECO + ALTO_PILDORA)) / 2 + self._flota
        return x, y

    def _centro_reposo(self):
        """Centro de la tarjeta en el widget, sin flotación; el ratón se mide contra él."""
        x_t, y_t = (ANCHO_SUG - ANCHO) / 2, (ALTO_SUG - (ALTO + HUECO + ALTO_PILDORA)) / 2
        return self._transformada_base().map(QPointF(x_t + ANCHO / 2, y_t + ALTO / 2))

    def _portada_para(self, dpr):
        """La carátula cuadrada al tamaño físico (dpr); se reescala solo si cambia el dpr."""
        if self._portada is None:
            return None
        if self._portada_escalada is None or self._portada_dpr != dpr:
            self._portada_escalada = _cover(self._portada, int(round(LADO * dpr)))
            self._portada_dpr = dpr
        return self._portada_escalada

    # ------------------------------------------------------------------ caché de la tarjeta

    def _reconstruir(self, f, dpr):
        """Pinta la tarjeta completa (sin inclinación) en el pixmap de caché, al tamaño escalado.

        El pixmap tiene dpr = factor * dpr de pantalla: su tamaño lógico es el del diseño y se
        ve nítido al escalarlo en el widget.
        """
        eff = f * dpr
        pm = QPixmap(int(round((ANCHO + 2 * MARGEN) * eff)), int(round((ALTO + 2 * MARGEN) * eff)))
        pm.setDevicePixelRatio(eff)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.TextAntialiasing, True)
            R = QRectF(MARGEN, MARGEN, ANCHO, ALTO)
            pintar_vidrio(p, R, radio=RADIO, acento=self._brillo)
            self._dibujar_caratula(p, R, eff)
            self._dibujar_textos(p, R)
            self._dibujar_corazon(p, R)
        finally:
            p.end()
        self._cache = pm
        self._clave_cache = (f, dpr)
        self._sucia = False
        self._rehechos += 1

    def _dibujar_caratula(self, p, R, eff):
        caja = _sub(R)
        camino = QPainterPath()
        camino.addRoundedRect(caja, RADIO_PORTADA, RADIO_PORTADA)
        img = self._portada_para(eff)
        p.save()
        p.setClipPath(camino)
        if img is not None:
            p.drawImage(caja, img)
        else:
            grad = QLinearGradient(caja.topLeft(), caja.bottomRight())
            grad.setColorAt(0.0, self._dominante)
            grad.setColorAt(1.0, self._segundo)
            p.fillPath(camino, QBrush(grad))
            # iconos.pixmap pide un color con clave (hashable): blanco y la transparencia por opacidad
            icono = iconos.pixmap("musica", 96, "#ffffff")
            c = caja.center()
            p.setOpacity(200 / 255)
            p.drawPixmap(QPointF(c.x() - icono.width() / 2, c.y() - icono.height() / 2), icono)
            p.setOpacity(1.0)
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawPath(camino)

    def _dibujar_textos(self, p, R):
        x = R.x() + 16
        ancho = ANCHO - 32
        _texto(p, QRectF(x, R.y() + 302, ancho, 26), self._titulo, fuente(18, QFont.DemiBold), TEXTO)
        _texto(p, QRectF(x, R.y() + 330, ancho, 20), self._artista, fuente(14), TEXTO_2)

        # píldora con el ecualizador y la fuente
        f11 = fuente(11)
        fm = QFontMetrics(f11)
        texto = fm.elidedText(self._fuente_texto, Qt.ElideRight, 232)
        tw = fm.horizontalAdvance(texto)
        alto_p = 24
        pildora = QRectF(x, R.y() + 358, 43 + tw, alto_p)
        camino = QPainterPath()
        camino.addRoundedRect(pildora, alto_p / 2, alto_p / 2)
        p.fillPath(camino, QColor(255, 255, 255, 30))
        acento = acento_legible(self._brillo)
        p.setPen(Qt.NoPen)
        p.setBrush(acento)
        cy = pildora.center().y()
        for i, alto_barra in enumerate((6, 12, 8)):
            bx = pildora.x() + 10 + i * 5
            p.drawRoundedRect(QRectF(bx, cy - alto_barra / 2, 3, alto_barra), 1.5, 1.5)
        _texto(p, QRectF(pildora.x() + 31, pildora.y(), tw + 4, alto_p), texto, f11, TEXTO_2)

        # línea de progreso
        pista_r = QRectF(x, R.bottom() - 24, ancho, 3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(pista_r, 1.5, 1.5)
        if self._progreso > 0:
            relleno = QRectF(pista_r.x(), pista_r.y(), ancho * self._progreso, 3)
            p.setBrush(acento)
            p.drawRoundedRect(relleno, 1.5, 1.5)

    def _dibujar_corazon(self, p, R):
        c = _lugar_corazon(R)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawEllipse(c)
        if self._me_gusta:
            icono = iconos.pixmap("corazon_lleno", 18, acento_legible(self._brillo).name())
            alfa = 1.0
        else:
            icono = iconos.pixmap("corazon", 18, "#ffffff")
            alfa = TEXTO.alpha() / 255
        ctr = c.center()
        p.setOpacity(alfa)
        p.drawPixmap(QPointF(ctr.x() - icono.width() / 2, ctr.y() - icono.height() / 2), icono)
        p.setOpacity(1.0)

    # ------------------------------------------------------------------ dibujo en vivo

    def _transformada_inclinada(self, R):
        """Perspectiva de la tarjeta (en diseño): gira alrededor de su centro en Y y luego en X."""
        cx, cy = R.center().x(), R.center().y()
        t = QTransform()
        t.translate(cx, cy)
        t.rotate(self._ang_y, Qt.YAxis)
        t.rotate(self._ang_x, Qt.XAxis)
        t.translate(-cx, -cy)
        return t

    def _pintar_halo(self, p, R):
        """Halo del color de la carátula alrededor de la tarjeta: capas con alfa decreciente."""
        p.setPen(Qt.NoPen)
        for i in range(8, 0, -1):
            d = 2.0 * i
            p.setBrush(con_alfa(self._brillo, 6 + (8 - i) * 2.5))
            p.drawRoundedRect(R.adjusted(-d, -d, d, d), RADIO + d, RADIO + d)

    def _pintar_reflejo(self, p, R):
        """Banda especular diagonal; su posición sigue a la inclinación."""
        camino = QPainterPath()
        camino.addRoundedRect(R, RADIO, RADIO)
        s = (self._ang_y - self._ang_x) / (2 * MAX_ANG)
        nx, ny = math.sqrt(0.5), -math.sqrt(0.5)     # normal de la banda (la banda va en diagonal)
        c = R.center()
        cen = QPointF(c.x() + nx * s * 150, c.y() + ny * s * 150)
        L = 260.0
        grad = QLinearGradient(QPointF(cen.x() - nx * L, cen.y() - ny * L),
                               QPointF(cen.x() + nx * L, cen.y() + ny * L))
        grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.44, QColor(255, 255, 255, 0))
        grad.setColorAt(0.5, QColor(255, 255, 255, 38))
        grad.setColorAt(0.56, QColor(255, 255, 255, 0))
        grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(camino, QBrush(grad))

    def _pintar_pildora(self, p, indice, texto, icono_nombre, fondo=None):
        """Pinta una píldora de vidrio con icono y texto. fondo, si se da, se pinta encima del vidrio."""
        r = self._pildora_diseno(indice)
        pintar_vidrio(p, r, radio=r.height() / 2, acento=self._brillo, sombra=False)
        camino = QPainterPath()
        camino.addRoundedRect(r, r.height() / 2, r.height() / 2)
        if fondo is not None:
            p.fillPath(camino, fondo)
        if self._pildora_bajo_raton == indice:
            p.fillPath(camino, QColor(255, 255, 255, 36))
        f = fuente(12, QFont.DemiBold)
        ancho_txt = QFontMetrics(f).horizontalAdvance(texto)
        icono = iconos.pixmap(icono_nombre, 14, "#ffffff")
        x0 = r.x() + (r.width() - (14 + 6 + ancho_txt)) / 2
        p.setOpacity(230 / 255)
        p.drawPixmap(QPointF(x0, r.center().y() - 7), icono)
        p.setOpacity(1.0)
        _texto(p, QRectF(x0 + 20, r.y(), ancho_txt + 4, r.height()), texto, f, TEXTO)

    def _pintar_pildoras(self, p):
        self._pintar_pildora(p, 0, "Otra letra", "lupa")
        # activa: fondo del color de acento al 35 % de alfa (0.35 * 255 = 89)
        fondo = None
        if self._traduccion_activa:
            fondo = QColor(acento_legible(self._brillo))
            fondo.setAlpha(89)
        texto = "Original" if self._traduccion_activa else "Traducir"
        self._pintar_pildora(p, 1, texto, "idioma", fondo)

    def paintEvent(self, _evento):
        f = self._factor()
        dpr = self.devicePixelRatioF() or 1.0
        if self._sucia or self._cache is None or self._clave_cache != (f, dpr):
            self._reconstruir(f, dpr)
        T = self._transformada_base()
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        p.setWorldTransform(T, False)
        x_t, y_t = self._origen()
        R = QRectF(x_t, y_t, ANCHO, ALTO)
        self._pintar_halo(p, R)
        p.save()
        p.setWorldTransform(self._transformada_inclinada(R) * T, False)
        p.drawPixmap(QPointF(x_t - MARGEN, y_t - MARGEN), self._cache)
        self._pintar_reflejo(p, R)
        p.restore()
        p.setWorldTransform(T, False)
        self._pintar_pildoras(p)
        p.end()

    # ------------------------------------------------------------------ animación y ratón

    def _tic(self):
        ahora = time.monotonic()
        dt = min(0.1, max(0.0, ahora - self._ultimo))
        self._ultimo = ahora
        t = ahora - self._t0
        if self._encima and self._raton is not None:
            centro = self._centro_reposo()
            f = self._factor()
            nx = max(-1.0, min(1.0, (self._raton.x() - centro.x()) / (ANCHO / 2 * f)))
            ny = max(-1.0, min(1.0, (self._raton.y() - centro.y()) / (ALTO / 2 * f)))
            obj_y, obj_x = nx * MAX_ANG, -ny * MAX_ANG
        else:
            obj_y = VAIVEN_AMP * math.sin(2 * math.pi * t / VAIVEN_PERIODO)
            obj_x = 0.0
        k = 1.0 - math.exp(-SUAVIDAD * dt)
        self._ang_y += (obj_y - self._ang_y) * k
        self._ang_x += (obj_x - self._ang_x) * k
        self._flota = FLOTA_AMP * math.sin(2 * math.pi * t / FLOTA_PERIODO)
        # el ratón encima pide fluidez; en reposo basta con 20 cuadros (cada uno cuesta repintar la ventana)
        intervalo = 16 if self._encima else 50
        if self._timer.interval() != intervalo:
            self._timer.setInterval(intervalo)
        self.update()
        if not a_la_vista(self):
            self._timer.stop()

    def showEvent(self, evento):
        super().showEvent(evento)
        self._ultimo = time.monotonic()
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def resizeEvent(self, evento):
        self._marcar()
        super().resizeEvent(evento)

    def mouseMoveEvent(self, evento):
        pos = evento.position()
        self._raton = pos
        self._encima = True
        bajo_raton = self._pildora_en(pos)
        if bajo_raton != self._pildora_bajo_raton:
            self._pildora_bajo_raton = bajo_raton
            self.update()
        if bajo_raton is not None or self.rect_corazon().contains(pos):
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(evento)

    def leaveEvent(self, evento):
        self._encima = False
        self._raton = None
        self._pildora_bajo_raton = None
        self.unsetCursor()
        self.update()
        super().leaveEvent(evento)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            pos = evento.position()
            if self.rect_corazon().contains(pos):
                self.pidio_me_gusta.emit()
                evento.accept()
                return
            indice = self._pildora_en(pos)
            if indice == 0:
                self.pidio_otra_letra.emit()
                evento.accept()
                return
            if indice == 1:
                self.pidio_traducir.emit()
                evento.accept()
                return
        super().mousePressEvent(evento)
