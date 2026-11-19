# -*- coding: utf-8 -*-
"""El visualizador a pantalla completa (donadores): Ondas, Partículas y Barras.

Se mueve con el nivel real del audio cuando el motor lo mide (ver `espectro.py`) y, si no, con el ritmo conocido
de la canción. Los colores son los de la carátula (si están activados) o el acento de la app.

Gasta poco: ~30 cuadros por segundo solo mientras suena y la ventana se ve; en reposo el reloj baja a ~4 por
segundo y cuando todo queda quieto deja de repintar; el medidor de nivel del motor solo existe mientras esta
vista está abierta; y el modo gamer en ahorro lo detiene (sus relojes son hijos de la vista).
"""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import QPushButton

from .. import espectro
from ..paleta_caratula import colores_de
from . import imagenes
from .componentes import a_la_vista
from .vista_grande import BOTON, VistaGrande, ahorrando

ESTILOS = {"ondas": "Ondas", "particulas": "Partículas", "barras": "Barras"}
MS_SONANDO = 33                  # ~30 cuadros por segundo
MS_REPOSO = 250                  # en pausa: lo justo para que las barras terminen de bajar
MS_DORMIDO = 300                 # minimizada u oculta: solo mira si vuelve a verse
N_PARTICULAS = 96


def estilo_valido(valor):
    return valor if valor in ESTILOS else "ondas"


def _con_alfa(c, a):
    c = QColor(c)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


class PaginaVisualizador(VistaGrande):
    titulo = "Visualizador"

    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.colores = colores_de(ctx)
        self.modelo = espectro.ModeloAudio()
        self.estilo = estilo_valido(ctx.ajustes["visualizador_estilo"])
        self._t0 = time.monotonic()
        self._ultimo = self._t0
        self._pos_base = 0.0
        self._pos_reloj = self._t0
        self._bpm = None
        self._fase = 0.0
        self._rng = random.Random(7)
        self._parts = [self._nueva_particula(inicial=True) for _ in range(N_PARTICULAS)]
        self._cover = None            # (url, QImage)
        self._cover_pm = None         # (lado, QPixmap redondo)
        self.cuadros = 0              # cuántos cuadros se han pintado (para las pruebas)

        self.botones_estilo = {}
        for i, (clave, nombre) in enumerate(ESTILOS.items()):
            b = QPushButton(nombre)
            b.setCheckable(True)
            b.setChecked(clave == self.estilo)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(BOTON)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, k=clave: self.elegir_estilo(k))
            self.fila_cab.insertWidget(1 + i, b, 0, Qt.AlignVCenter)
            self.botones_estilo[clave] = b

        self.reloj = QTimer(self)
        self.reloj.setTimerType(Qt.CoarseTimer)
        self.reloj.timeout.connect(self._cuadro)
        self.r.posicion_cambio.connect(self._posicion)
        self.r.estado_cambio.connect(self._al_estado)
        self.r.pista_cambio.connect(self._pista)
        self.colores.cambio.connect(self._pintar_si_quieto)
        self._pista(self.r.actual)

    # ------------------------------------------------------------ datos
    def elegir_estilo(self, clave):
        self.estilo = estilo_valido(clave)
        for k, b in self.botones_estilo.items():
            b.setChecked(k == self.estilo)
        self.ctx.ajustes["visualizador_estilo"] = self.estilo
        try:
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        self.update()

    def _posicion(self, seg):
        self._pos_base = float(seg or 0)
        self._pos_reloj = time.monotonic()

    def _pos_ahora(self):
        pos = self._pos_base
        if self.suena():
            pos += min(1.0, time.monotonic() - self._pos_reloj) * float(getattr(self.r, "velocidad", 1.0) or 1.0)
        return pos

    def _pista(self, p):
        self._bpm, self._fase = None, 0.0
        buscar = getattr(self.r, "_analisis_de", None)
        if p and buscar is not None:
            try:
                an = buscar(p) or {}
                self._bpm = float(an.get("bpm") or 0) or None
                self._fase = float(an.get("fase") or 0)
            except Exception:  # noqa: BLE001
                pass
        url = (p or {}).get("miniatura") or ""
        self._cover_pm = None
        if not url:
            self._cover = None
        else:
            self._cover = (url, QImage())
            imagenes.imagen(url, lambda img, u=url: self._cover and self._cover[0] == u
                            and self._cover_llego(u, img))
        self.update()

    def _cover_llego(self, url, img):
        self._cover = (url, img if img is not None else QImage())
        self._cover_pm = None
        self.update()

    def _al_estado(self, _e):
        self._ritmo()

    # ------------------------------------------------------------ reloj
    def showEvent(self, e):
        super().showEvent(e)
        act = getattr(self.r, "activar_espectro", None)
        if act is not None:
            act(True)
        self._pos_base = float(getattr(self.r, "_posicion", 0) or 0)
        self._pos_reloj = time.monotonic()
        self._ultimo = time.monotonic()
        self._ritmo()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.reloj.stop()
        act = getattr(self.r, "activar_espectro", None)
        if act is not None:
            act(False)
        self.modelo.reiniciar()

    def _ms_objetivo(self):
        if not a_la_vista(self):
            return MS_DORMIDO
        if self.suena():
            return MS_SONANDO
        return MS_REPOSO

    def _ritmo(self):
        if not self.isVisible() or ahorrando(self.ctx):
            self.reloj.stop()
            return
        ms = self._ms_objetivo()
        if not self.reloj.isActive() or self.reloj.interval() != ms:
            self.reloj.start(ms)

    def _pintar_si_quieto(self):
        """Mientras dura la transición de colores y el reloj descansa, se repinta con ella."""
        if self.isVisible() and not self.suena() and a_la_vista(self) and not ahorrando(self.ctx):
            self.update()

    def _cuadro(self):
        ahora = time.monotonic()
        if ahorrando(self.ctx) or not a_la_vista(self):
            self._ultimo = ahora
            self._ritmo()
            return
        dt = min(0.25, ahora - self._ultimo)
        self._ultimo = ahora
        sonando = self.suena()
        nivel = None
        if sonando:
            f = getattr(self.r, "nivel_audio", None)
            if f is not None:
                try:
                    nivel = f()
                except Exception:  # noqa: BLE001
                    nivel = None
        self.modelo.avanzar(dt, nivel, sonando, self._pos_ahora(), self._bpm, self._fase)
        if self.estilo == "particulas":
            self._mover_particulas(dt)
        ms = self._ms_objetivo()
        if not sonando and self.modelo.quieto() and not self.colores.animando:
            # todo en reposo: se pinta este último cuadro y el reloj espera a que algo cambie
            self.update()
            self.reloj.stop()
            return
        if self.reloj.interval() != ms:
            self.reloj.start(ms)
        self.update()

    # ------------------------------------------------------------ partículas
    def _nueva_particula(self, inicial=False):
        rng = self._rng
        return [rng.uniform(0, math.tau),                     # ángulo
                rng.uniform(0.0, 1.0) if inicial else 0.0,     # radio (fracción del radio máximo)
                rng.uniform(0.05, 0.22),                       # velocidad base
                rng.uniform(1.6, 4.6),                         # tamaño
                rng.uniform(0.6, 1.0),                         # vida
                rng.random()]                                  # qué color de la paleta

    def _mover_particulas(self, dt):
        m = self.modelo
        empuje = 0.25 + m.energia * 2.1 + m.golpe * 1.4
        for p in self._parts:
            p[1] += p[2] * empuje * dt
            p[0] += dt * (0.10 + 0.25 * m.energia) * (1 if p[5] > 0.5 else -1)
            p[4] -= dt * 0.12
            if p[1] >= 1.0 or p[4] <= 0.0:
                p[:] = self._nueva_particula()

    # ------------------------------------------------------------ pintura
    def paintEvent(self, _e):
        self.cuadros += 1
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cols = self.colores.colores()
        self._fondo(p, w, h, cols)
        if self.estilo == "barras":
            self._barras(p, w, h, cols)
        elif self.estilo == "particulas":
            self._particulas(p, w, h, cols)
        else:
            self._ondas(p, w, h, cols)
        p.end()

    def _fondo(self, p, w, h, cols):
        m = self.modelo
        base = QColor.fromHsvF(max(0.0, cols[1].hsvHueF()), min(1.0, cols[1].hsvSaturationF() * 0.8), 0.13)
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0.0, base.lighter(130))
        g.setColorAt(1.0, QColor(4, 5, 8))
        p.fillRect(QRectF(0, 0, w, h), QBrush(g))
        brillo = QRadialGradient(QPointF(w / 2, h * 0.52), max(w, h) * 0.62)
        brillo.setColorAt(0.0, _con_alfa(cols[0], 0.14 + 0.34 * m.energia + 0.10 * m.golpe))
        brillo.setColorAt(1.0, _con_alfa(cols[0], 0.0))
        p.fillRect(QRectF(0, 0, w, h), QBrush(brillo))

    def _ondas(self, p, w, h, cols):
        m = self.modelo
        t = time.monotonic() - self._t0
        y0 = h * 0.52
        paso = max(6.0, w / 110.0)
        n = int(w / paso) + 2
        for k in range(3):
            amp = h * (0.035 + 0.20 * m.energia + 0.08 * m.golpe) * (1.0 - 0.24 * k)
            frec = 1.25 + 0.75 * k
            fase = t * (0.55 + 0.35 * k) * (1.0 + m.energia) + k * 1.7
            ruta = QPainterPath()
            for i in range(n):
                x = min(w, i * paso)
                u = x / max(1.0, w)
                sobre = math.sin(math.pi * u) ** 0.85
                y = y0 + amp * sobre * (math.sin(u * math.tau * frec + fase)
                                        + 0.35 * math.sin(u * math.tau * frec * 2.3 - fase * 1.4))
                if i == 0:
                    ruta.moveTo(x, y)
                else:
                    ruta.lineTo(x, y)
            relleno = QPainterPath(ruta)
            relleno.lineTo(w, h)
            relleno.lineTo(0, h)
            relleno.closeSubpath()
            c = cols[k % 3]
            g = QLinearGradient(0, y0 - amp, 0, h)
            g.setColorAt(0.0, _con_alfa(c, 0.34 - 0.07 * k))
            g.setColorAt(1.0, _con_alfa(c, 0.0))
            p.fillPath(relleno, QBrush(g))
            p.setPen(QPen(_con_alfa(c.lighter(125), 0.9 - 0.2 * k), 2.4 - 0.4 * k))
            p.setBrush(Qt.NoBrush)
            p.drawPath(ruta)

    def _barras(self, p, w, h, cols):
        m = self.modelo
        n = m.n
        margen = w * 0.07
        ancho_total = w - 2 * margen
        hueco = ancho_total / n
        ancho = hueco * 0.62
        y0 = h * 0.56
        alto_max = h * 0.40
        g = QLinearGradient(0, y0 - alto_max, 0, y0)
        g.setColorAt(0.0, cols[2].lighter(115))
        g.setColorAt(0.55, cols[0])
        g.setColorAt(1.0, cols[1])
        pincel = QBrush(g)
        p.setPen(Qt.NoPen)
        radio = ancho / 2
        for i in range(n):
            x = margen + i * hueco + (hueco - ancho) / 2
            alto = max(ancho, m.bandas[i] * alto_max)
            p.setBrush(pincel)
            p.drawRoundedRect(QRectF(x, y0 - alto, ancho, alto), radio, radio)
            # reflejo, más corto y apagado
            refl = alto * 0.45
            gr = QLinearGradient(0, y0 + 4, 0, y0 + 4 + refl)
            gr.setColorAt(0.0, _con_alfa(cols[0], 0.30))
            gr.setColorAt(1.0, _con_alfa(cols[0], 0.0))
            p.setBrush(QBrush(gr))
            p.drawRoundedRect(QRectF(x, y0 + 4, ancho, refl), radio, radio)
            # la tapita que cae despacio
            ty = y0 - max(alto, m.picos[i] * alto_max) - ancho * 0.9
            p.setBrush(_con_alfa(cols[2].lighter(130), 0.9))
            p.drawRoundedRect(QRectF(x, ty, ancho, max(2.0, ancho * 0.32)), 1.5, 1.5)

    def _caratula_redonda(self, lado):
        if self._cover is None or self._cover[1].isNull():
            return None
        if self._cover_pm is None or self._cover_pm[0] != lado:
            pm = QPixmap(lado, lado)
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            q.setRenderHint(QPainter.Antialiasing, True)
            q.setRenderHint(QPainter.SmoothPixmapTransform, True)
            ruta = QPainterPath()
            ruta.addEllipse(QRectF(0, 0, lado, lado))
            q.setClipPath(ruta)
            img = self._cover[1].scaled(lado, lado, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            q.drawImage((lado - img.width()) // 2, (lado - img.height()) // 2, img)
            q.end()
            self._cover_pm = (lado, pm)
        return self._cover_pm[1]

    def _particulas(self, p, w, h, cols):
        m = self.modelo
        cx, cy = w / 2, h * 0.5
        rmax = math.hypot(w, h) * 0.5
        base = min(w, h) * 0.17
        lado = int(base * 2 * (1.0 + 0.07 * m.golpe + 0.03 * m.energia))
        # anillos de pulso alrededor de la carátula
        for k in range(3):
            r = lado / 2 + 10 + k * 14 + 22 * m.energia * (k + 1) * 0.5
            p.setPen(QPen(_con_alfa(cols[k % 3], 0.34 - 0.08 * k), 2.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.setCompositionMode(QPainter.CompositionMode_Plus)
        p.setPen(Qt.NoPen)
        for ang, rad, _v, tam, vida, col in self._parts:
            r = lado / 2 + 14 + rad * rmax * 0.8
            x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r
            c = cols[int(col * 3) % 3].lighter(120)
            a = max(0.0, min(1.0, vida)) * (1.0 - rad) ** 0.7
            s = tam * (1.0 + 0.8 * m.golpe)
            p.setBrush(_con_alfa(c, a * 0.20))
            p.drawEllipse(QPointF(x, y), s * 2.6, s * 2.6)
            p.setBrush(_con_alfa(c, a * 0.85))
            p.drawEllipse(QPointF(x, y), s, s)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        pm = self._caratula_redonda(max(40, lado))
        if pm is not None:
            p.drawPixmap(int(cx - lado / 2), int(cy - lado / 2), pm)
            p.setPen(QPen(_con_alfa(cols[0].lighter(140), 0.9), 3.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), lado / 2, lado / 2)
        else:
            g = QRadialGradient(QPointF(cx, cy), lado / 2)
            g.setColorAt(0.0, _con_alfa(cols[0].lighter(130), 0.95))
            g.setColorAt(1.0, _con_alfa(cols[1], 0.9))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(cx, cy), lado / 2, lado / 2)
