# -*- coding: utf-8 -*-
"""Barra mini de la escena: una píldora de vidrio con los controles de reproducción,
la canción que suena, el progreso y los botones de la escena (fondo, volver, salir).

Es una ventanita translúcida propia, dibujada con QPainter. Su única animación es el arco
de «cargando» alrededor del botón de reproducir; el timer solo corre mientras se ve.
"""

import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QToolTip, QWidget

from .. import iconos
from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, TEXTO, TEXTO_2, TEXTO_3, acento_legible, con_alfa,
                     fuente, pintar_vidrio, preparar_transparente)

ANCHO, ALTO = 698, 92              # tamaño de la ventanita (incluye margen para la sombra)
PILDORA_X, PILDORA_Y = 20, 16      # la píldora queda centrada
PILDORA_ANCHO, PILDORA_ALTO = 620, 60
RADIO_PILDORA = 30
PAD = 14                           # padding interior de la píldora
BOTON = 34                         # botones normales
PLAY = 40                          # botón de reproducir
ESPACIO = 4                        # hueco entre botones
MARGEN_PROG = 26                   # márgenes laterales de la línea de progreso
PORTADA = 38                       # miniatura de la carátula
PORTADA_PX = 76                    # resolución interna de la miniatura (x2 para nitidez)

_SENALES = {
    "anterior": "anterior",
    "alternar": "alternar",
    "siguiente": "siguiente",
    "aleatorio": "aleatorio",
    "repetir": "repetir",
    "fondo": "cambiar_fondo",
    "abrir": "abrir_caudal",
    "salir": "salir",
    "buscar": "pidio_buscar",
}


def _tiempo(segundos):
    """Formatea segundos como 1:23 (o 1:02:03 si pasa de una hora)."""
    s = max(0, int(segundos or 0))
    horas, resto = divmod(s, 3600)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{seg:02d}"
    return f"{minutos}:{seg:02d}"


class BarraMini(QWidget):
    """Píldora de controles flotante sobre la escena. Las acciones salen por señales;
    la barra no sabe nada de reproducción, solo se pinta con lo que le fijan."""

    anterior = Signal()
    alternar = Signal()
    siguiente = Signal()
    aleatorio = Signal()
    repetir = Signal()
    cambiar_fondo = Signal()
    abrir_caudal = Signal()
    salir = Signal()
    pidio_buscar = Signal()        # el usuario pulsó la lupa (buscar)
    buscar_pos = Signal(float)     # fracción 0..1 de la canción

    def __init__(self, padre=None):
        super().__init__(padre)
        preparar_transparente(self)
        self.setMouseTracking(True)
        self.setMinimumSize(ANCHO, ALTO)

        self._pista = None
        self._portada = None           # QImage ya recortada a PORTADA_PX cuadrados
        self._estado = "parado"
        self._pos = 0.0
        self._dur = 0.0
        self._aleatorio = False
        self._repetir = "no"
        self._fondo = "video"
        self._dominante = QColor(DOMINANTE)
        self._segundo = QColor(SEGUNDO)
        self._brillo = QColor(BRILLO)

        self._hover = None             # nombre del botón bajo el ratón
        self._hover_prog = False       # ratón sobre la línea de progreso
        self._arrastrando = False      # arrastre en la línea de progreso
        self._pulsado = None           # botón donde empezó el clic

        self._t0 = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tic)

    # ------------------------------------------------------------------ API pública

    def sizeHint(self):
        return QSize(ANCHO, ALTO)

    def poner(self, pista):
        """pista: dict con «titulo» y «artista», o None para la barra vacía."""
        self._pista = dict(pista) if pista else None
        self.update()

    def poner_portada(self, img):
        """Carátula (QImage o QPixmap), o None para el icono de música."""
        if isinstance(img, QPixmap):
            img = img.toImage()
        if img is None or img.isNull():
            self._portada = None
        else:
            s = img.scaled(PORTADA_PX, PORTADA_PX, Qt.KeepAspectRatioByExpanding,
                           Qt.SmoothTransformation)
            x = (s.width() - PORTADA_PX) // 2
            y = (s.height() - PORTADA_PX) // 2
            self._portada = s.copy(x, y, PORTADA_PX, PORTADA_PX)
        self.update()

    def fijar_estado(self, estado):
        """estado: "sonando" | "pausa" | "cargando" | "parado"."""
        self._estado = estado if estado in ("sonando", "pausa", "cargando", "parado") else "parado"
        self._sincronizar_timer()
        self.update()

    def fijar_progreso(self, pos_s, dur_s):
        self._pos = max(0.0, float(pos_s or 0))
        self._dur = max(0.0, float(dur_s or 0))
        self.update()

    def fijar_aleatorio(self, si):
        self._aleatorio = bool(si)
        self.update()

    def fijar_repetir(self, modo):
        """modo: "no" | "todo" | "una"."""
        self._repetir = modo if modo in ("no", "todo", "una") else "no"
        self.update()

    def fijar_fondo(self, modo):
        """modo: "video" (videoclip) | "ambiente" (carátula)."""
        self._fondo = modo if modo in ("video", "ambiente") else ("escenario" if modo else "video")
        self.update()

    def poner_colores(self, dominante, segundo, brillo):
        self._dominante = QColor(dominante)
        self._segundo = QColor(segundo)
        self._brillo = QColor(brillo)
        self.update()

    def rect_boton(self, nombre):
        """Rectángulo de un botón por su nombre: anterior, alternar, siguiente, aleatorio,
        repetir, fondo, abrir, buscar o salir."""
        return QRectF(self._geometria()["botones"][nombre])

    def rect_progreso(self):
        """Zona sensible de la línea de progreso (la línea se dibuja dentro de ella)."""
        return QRectF(self._geometria()["hit"])

    # ------------------------------------------------------------------ geometría

    def _geometria(self):
        """Todas las cajas de la barra, calculadas a partir del estado actual."""
        pildora = QRectF(PILDORA_X, PILDORA_Y, PILDORA_ANCHO, PILDORA_ALTO)
        cy = pildora.center().y()

        botones = {}
        x = pildora.left() + PAD
        for nombre, lado in (("anterior", BOTON), ("alternar", PLAY), ("siguiente", BOTON),
                             ("aleatorio", BOTON), ("repetir", BOTON)):
            botones[nombre] = QRectF(x, cy - lado / 2, lado, lado)
            x += lado + ESPACIO

        x_sep = x - ESPACIO + 12
        portada = QRectF(x_sep + 12, cy - PORTADA / 2, PORTADA, PORTADA)
        x_txt = portada.right() + 10

        x = pildora.right() - PAD
        for nombre in ("salir", "abrir", "fondo", "buscar"):
            botones[nombre] = QRectF(x - BOTON, cy - BOTON / 2, BOTON, BOTON)
            x -= BOTON + ESPACIO
        x_fin = x - 12

        texto_tiempo = ""
        if self._pista is not None:
            texto_tiempo = f"{_tiempo(self._pos)} / {_tiempo(self._dur)}"
        tw = QFontMetrics(fuente(11)).horizontalAdvance(texto_tiempo) if texto_tiempo else 0
        tiempo = QRectF(x_fin - tw, cy - 19, tw, 38)
        x_limite = (x_fin - tw - 12) if tw else x_fin
        ancho_txt = max(60.0, x_limite - x_txt)
        titulo = QRectF(x_txt, cy - 19, ancho_txt, 20)
        artista = QRectF(x_txt, cy + 2, ancho_txt, 17)

        x0 = pildora.left() + MARGEN_PROG
        x1 = pildora.right() - MARGEN_PROG
        yc = pildora.bottom() - 7
        hit = QRectF(x0, pildora.bottom() - 12, x1 - x0, 12)

        return {
            "pildora": pildora,
            "botones": botones,
            "separador": (x_sep, cy - 12, cy + 12),
            "portada": portada,
            "titulo": titulo,
            "artista": artista,
            "tiempo": tiempo,
            "tiempo_txt": texto_tiempo,
            "prog": (x0, x1, yc),
            "hit": hit,
        }

    def _en_boton(self, pos, g):
        for nombre, r in g["botones"].items():
            if r.contains(pos):
                return nombre
        return None

    def _fraccion(self):
        return min(1.0, self._pos / self._dur) if self._dur > 0 else 0.0

    # ------------------------------------------------------------------ pintura

    def paintEvent(self, _ev):
        g = self._geometria()
        acento = acento_legible(self._brillo)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        pintar_vidrio(p, g["pildora"], RADIO_PILDORA, acento=self._dominante)
        self._pintar_botones(p, g, acento)
        self._pintar_separador(p, g)
        self._pintar_pista(p, g)
        self._pintar_progreso(p, g, acento)
        self._pintar_cargando(p, g, acento)
        p.end()

    def _icono(self, p, nombre, tam, color, r):
        # iconos.pixmap usa el color como clave de caché: se le pasa como texto #AARRGGBB
        pm = iconos.pixmap(nombre, tam, QColor(color).name(QColor.HexArgb))
        p.drawPixmap(QPointF(r.center().x() - tam / 2, r.center().y() - tam / 2), pm)

    def _halo(self, p, r, nombre):
        if self._hover == nombre:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 22))
            p.drawEllipse(r)

    def _pintar_botones(self, p, g, acento):
        b = g["botones"]
        sonando = self._estado == "sonando"
        cfg = {
            "anterior": ("anterior", TEXTO_2),
            "siguiente": ("siguiente", TEXTO_2),
            "aleatorio": ("aleatorio", acento if self._aleatorio else TEXTO_2),
            "repetir": ("repetir_una" if self._repetir == "una" else "repetir",
                        acento if self._repetir != "no" else TEXTO_2),
            "fondo": ({"video": "video", "escenario": "ecualizador"}.get(self._fondo, "disco"), TEXTO_2),
            "abrir": ("abrir", TEXTO_2),
            "buscar": ("lupa", TEXTO_2),
            "salir": ("salir_pantalla", TEXTO_2),
        }
        for nombre, (icono, color) in cfg.items():
            self._halo(p, b[nombre], nombre)
            self._icono(p, icono, 18, color, b[nombre])

        r = b["alternar"]
        p.setPen(Qt.NoPen)
        p.setBrush(acento)
        p.drawEllipse(r)
        self._halo(p, r, "alternar")
        self._icono(p, "pausa" if sonando else "reproducir", 18, QColor(17, 17, 17), r)

    def _pintar_separador(self, p, g):
        x, y0, y1 = g["separador"]
        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.drawLine(QPointF(x, y0), QPointF(x, y1))

    def _pintar_pista(self, p, g):
        # miniatura con esquinas redondeadas
        r = g["portada"]
        camino = QPainterPath()
        camino.addRoundedRect(r, 9, 9)
        p.save()
        p.setClipPath(camino)
        if self._portada is not None:
            p.drawImage(r, self._portada)
        else:
            p.fillPath(camino, QColor(255, 255, 255, 28))
            self._icono(p, "musica", 18, TEXTO_3, r)
        p.restore()

        # textos
        if self._pista is None:
            titulo, artista = "Nada sonando", "Busca algo para empezar"
        else:
            titulo = str(self._pista.get("titulo") or "Sin título")
            artista = str(self._pista.get("artista") or "")

        p.setPen(TEXTO)
        p.setFont(fuente(13, QFont.DemiBold))
        rt = g["titulo"]
        p.drawText(rt, int(Qt.AlignLeft | Qt.AlignVCenter),
                   QFontMetrics(p.font()).elidedText(titulo, Qt.ElideRight, int(rt.width())))

        p.setPen(TEXTO_2)
        p.setFont(fuente(11.5))
        ra = g["artista"]
        p.drawText(ra, int(Qt.AlignLeft | Qt.AlignVCenter),
                   QFontMetrics(p.font()).elidedText(artista, Qt.ElideRight, int(ra.width())))

        if g["tiempo_txt"]:
            p.setPen(TEXTO_3)
            p.setFont(fuente(11))
            p.drawText(g["tiempo"], int(Qt.AlignRight | Qt.AlignVCenter), g["tiempo_txt"])

    def _pintar_progreso(self, p, g, acento):
        x0, x1, yc = g["prog"]
        activo = self._hover_prog or self._arrastrando
        h = 5.0 if activo else 3.0
        ancho = x1 - x0
        f = self._fraccion()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(x0, yc - h / 2, ancho, h), h / 2, h / 2)
        if f > 0:
            p.setBrush(acento)
            p.drawRoundedRect(QRectF(x0, yc - h / 2, max(h, ancho * f), h), h / 2, h / 2)
        if activo:
            p.setBrush(TEXTO)
            p.drawEllipse(QPointF(x0 + ancho * f, yc), 5, 5)

    def _pintar_cargando(self, p, g, acento):
        if self._estado != "cargando":
            return
        r = g["botones"]["alternar"].adjusted(-5, -5, 5, 5)
        p.setBrush(Qt.NoBrush)
        pluma = QPen(con_alfa(acento, 60), 2.5)
        pluma.setCapStyle(Qt.RoundCap)
        p.setPen(pluma)
        p.drawEllipse(r)
        pluma.setColor(acento)
        p.setPen(pluma)
        angulo = ((time.monotonic() - self._t0) / 0.9 * 360.0) % 360.0
        p.drawArc(r, int(-angulo * 16), int(110 * 16))

    # ------------------------------------------------------------------ animación

    def _sincronizar_timer(self):
        """El timer solo corre si hay que animar («cargando») y la barra se ve."""
        if self._estado == "cargando" and a_la_vista(self):
            if not self._timer.isActive():
                self._t0 = time.monotonic()
                self._timer.start()
        else:
            self._timer.stop()

    def _tic(self):
        if self._estado != "cargando" or not a_la_vista(self):
            self._timer.stop()
            return
        self.update()

    def showEvent(self, ev):
        super().showEvent(ev)
        self._sincronizar_timer()

    def hideEvent(self, ev):
        self._timer.stop()
        super().hideEvent(ev)

    # ------------------------------------------------------------------ ratón

    def _emitir_fraccion(self, x, g):
        x0, x1, _ = g["prog"]
        f = min(1.0, max(0.0, (x - x0) / (x1 - x0)))
        self.buscar_pos.emit(float(f))

    def _tooltip(self, nombre):
        if nombre == "alternar":
            return "Pausa" if self._estado == "sonando" else "Reproducir"
        if nombre == "repetir":
            return {"no": "Repetir: desactivado", "todo": "Repetir: todo",
                    "una": "Repetir: una canción"}[self._repetir]
        if nombre == "fondo":
            return "Elegir fondo: videoclip, carátula o escenarios"
        if nombre == "aleatorio":
            return "Aleatorio: activado" if self._aleatorio else "Aleatorio: desactivado"
        return {"anterior": "Anterior", "siguiente": "Siguiente", "abrir": "Volver a Caudal",
                "buscar": "Buscar", "salir": "Salir de la escena (Esc)"}[nombre]

    def mouseMoveEvent(self, ev):
        g = self._geometria()
        pos = QPointF(ev.position())
        if self._arrastrando:
            self._emitir_fraccion(pos.x(), g)
        boton = self._en_boton(pos, g)
        prog = g["hit"].contains(pos)
        if boton != self._hover or prog != self._hover_prog:
            self._hover = boton
            self._hover_prog = prog
            self.setCursor(Qt.PointingHandCursor if (boton or prog) else Qt.ArrowCursor)
            self.update()
        if boton:
            QToolTip.showText(ev.globalPosition().toPoint(), self._tooltip(boton), self)
        else:
            QToolTip.hideText()
        ev.accept()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)
        g = self._geometria()
        pos = QPointF(ev.position())
        boton = self._en_boton(pos, g)
        if boton:
            self._pulsado = boton
        elif g["hit"].contains(pos):
            self._arrastrando = True
            self._emitir_fraccion(pos.x(), g)
            self.update()
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return super().mouseReleaseEvent(ev)
        g = self._geometria()
        pos = QPointF(ev.position())
        if self._pulsado:
            if self._en_boton(pos, g) == self._pulsado:
                getattr(self, _SENALES[self._pulsado]).emit()
            self._pulsado = None
        if self._arrastrando:
            self._arrastrando = False
            self.update()
        ev.accept()

    def leaveEvent(self, ev):
        self._hover = None
        self._hover_prog = False
        self.unsetCursor()
        QToolTip.hideText()
        self.update()
        super().leaveEvent(ev)
