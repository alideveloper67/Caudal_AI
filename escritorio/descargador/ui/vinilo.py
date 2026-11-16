# -*- coding: utf-8 -*-
"""Modo vinilo: un tocadiscos a pantalla completa mientras suena la canción.

Todo está dibujado con QPainter (sin imágenes):

- el disco (surcos finos, separaciones entre pistas y la carátula como etiqueta con su
  agujero) se pinta UNA vez en un QPixmap y luego solo se rota; el brillo cónico es otra
  capa fija (la luz no gira con el disco);
- gira a 33⅓ rpm solo mientras suena, con inercia al arrancar y al frenar;
- el brazo se posa sobre el disco al sonar, avanza hacia el centro con la canción y se
  levanta al pausar o cambiar de canción;
- el fondo (colores de la carátula, desenfocados, con viñeta), la placa del tocadiscos y
  las sombras son otra capa cacheada: por cuadro solo se compone.

La animación corre a ~60 fps con un QTimer que se detiene solo cuando todo está quieto o
la pantalla no se ve. Mientras el vinilo se ve y suena (o hace menos de 60 s que se pausó)
puede impedir que Windows apague la pantalla o entre en reposo.
"""

import ctypes
import math
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from . import imagenes
from .componentes import BotonIcono, BotonPlay, Deslizador
from .letra_viva import _BOTON, desenfocar, paleta_de

RPM = 100.0 / 3.0                 # 33 1/3 vueltas por minuto
GRADOS_POR_SEG = RPM * 6.0        # = 200 grados por segundo
MS_CUADRO = 16                    # ~60 fps
ESPERA_BAJAR = 0.9                # s que el brazo espera antes de posarse al empezar
SEG_BAJAR = 0.95                  # lo que tarda el brazo en posarse
SEG_SUBIR = 0.55                  # y en levantarse
TAU_ARRANQUE = 0.65               # inercia del plato al arrancar (s)
TAU_FRENO = 1.5                   # y al frenar
GRACIA_PAUSA = 60.0               # tras pausar, la pantalla sigue encendida 60 s

# --- reglas del brazo (en fracciones del radio del disco R)
PIVOTE = (1.12, -0.62)            # respecto al centro del disco
LARGO_BRAZO = 1.0
R_EXTERIOR = 0.935                # donde cae la aguja al empezar
R_INTERIOR = 0.43                 # y donde termina la canción
R_ETIQUETA = 0.335                # la carátula ocupa hasta aquí
GIRO_REPOSO = 24.0                # grados que se aparta el brazo cuando está levantado


# ------------------------------------------------------------ pantalla encendida

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def _estado_ejecucion(banderas):
    """SetThreadExecutionState de Windows; en otros sistemas no hace nada."""
    if sys.platform != "win32":
        return None
    try:
        f = ctypes.windll.kernel32.SetThreadExecutionState
        try:
            f.restype = ctypes.c_uint
        except Exception:
            pass
        return f(ctypes.c_uint(banderas))
    except Exception:
        return None


class MantenerPantalla:
    """Impide el apagado de pantalla y el reposo mientras esté activa."""

    def __init__(self):
        self.activa = False

    def activar(self):
        if not self.activa:
            _estado_ejecucion(ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)
            self.activa = True

    def liberar(self):
        if self.activa:
            _estado_ejecucion(ES_CONTINUOUS)
            self.activa = False


# ------------------------------------------------------------------ dibujo

def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _con_alfa(c, a):
    c = QColor(c)
    c.setAlpha(max(0, min(255, int(a))))
    return c


def _aclarar(c, f):
    h, s, v, _ = QColor(c).getHsvF()
    return QColor.fromHsvF(max(0.0, h), s, min(1.0, v * f))


def pintar_disco(lado, img, paleta, dpr=1.0):
    """El disco entero (surcos + etiqueta) en un pixmap cuadrado de `lado` px lógicos."""
    px = max(8, int(lado * dpr))
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    R = lado / 2.0
    c = QPointF(R, R)
    p.setPen(Qt.NoPen)

    # vinilo base: casi negro, un poco más claro hacia el centro
    g = QRadialGradient(c, R)
    g.setColorAt(0.0, QColor("#1b1c21"))
    g.setColorAt(0.55, QColor("#111216"))
    g.setColorAt(1.0, QColor("#08090b"))
    p.setBrush(QBrush(g))
    p.drawEllipse(c, R * 0.995, R * 0.995)

    # surcos finos: anillos alternados claro/oscuro muy tenues
    paso = max(1.7, lado * 0.0036)
    r = R * (R_ETIQUETA + 0.035)
    i = 0
    p.setBrush(Qt.NoBrush)
    while r < R * 0.972:
        lapiz = QPen(QColor(255, 255, 255, 9) if i % 2 == 0 else QColor(0, 0, 0, 70))
        lapiz.setWidthF(max(0.5, paso * 0.42))
        p.setPen(lapiz)
        p.drawEllipse(c, r, r)
        r += paso
        i += 1

    # separaciones entre pistas: bandas lisas y más oscuras
    for f in (0.585, 0.715, 0.835):
        rr = R * f
        lapiz = QPen(QColor(0, 0, 0, 150))
        lapiz.setWidthF(max(2.0, lado * 0.0085))
        p.setPen(lapiz)
        p.drawEllipse(c, rr, rr)
        lapiz = QPen(QColor(255, 255, 255, 16))
        lapiz.setWidthF(0.9)
        p.setPen(lapiz)
        p.drawEllipse(c, rr + lado * 0.0065, rr + lado * 0.0065)

    # borde del disco: un hilo de luz
    lapiz = QPen(QColor(255, 255, 255, 30))
    lapiz.setWidthF(1.1)
    p.setPen(lapiz)
    p.drawEllipse(c, R * 0.992, R * 0.992)
    # y un anillo liso alrededor de la etiqueta
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(8, 8, 10))
    p.drawEllipse(c, R * (R_ETIQUETA + 0.03), R * (R_ETIQUETA + 0.03))

    # etiqueta: la carátula recortada en círculo
    re = R * R_ETIQUETA
    ruta = QPainterPath()
    ruta.addEllipse(c, re, re)
    p.save()
    p.setClipPath(ruta)
    if img is not None and not img.isNull():
        lado_e = int(re * 2 * dpr) + 2
        esc = img.scaled(lado_e, lado_e, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (esc.width() - lado_e) // 2
        y = (esc.height() - lado_e) // 2
        p.drawImage(QRectF(c.x() - re, c.y() - re, re * 2, re * 2), esc,
                    QRectF(x, y, lado_e, lado_e))
    else:
        g = QRadialGradient(c, re)
        g.setColorAt(0.0, _aclarar(paleta[0], 1.0))
        g.setColorAt(1.0, _aclarar(paleta[1], 0.7))
        p.fillPath(ruta, QBrush(g))
        p.setBrush(Qt.NoBrush)
        lapiz = QPen(QColor(255, 255, 255, 60))
        lapiz.setWidthF(1.2)
        p.setPen(lapiz)
        for k in (0.35, 0.6, 0.85):
            p.drawEllipse(c, re * k, re * k)
    # un toque de volumen: se oscurece hacia el borde y brilla un poco al centro
    g = QRadialGradient(c, re)
    g.setColorAt(0.0, QColor(255, 255, 255, 16))
    g.setColorAt(0.78, QColor(0, 0, 0, 0))
    g.setColorAt(1.0, QColor(0, 0, 0, 80))
    p.fillPath(ruta, QBrush(g))
    p.restore()
    lapiz = QPen(QColor(0, 0, 0, 170))
    lapiz.setWidthF(1.6)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(c, re, re)
    lapiz = QPen(QColor(255, 255, 255, 36))
    lapiz.setWidthF(0.8)
    p.setPen(lapiz)
    p.drawEllipse(c, re - 1.4, re - 1.4)

    # agujero central con su aro
    rh = max(3.0, R * 0.032)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 90))
    p.drawEllipse(c, rh * 2.1, rh * 2.1)
    p.setBrush(QColor("#050506"))
    p.drawEllipse(c, rh, rh)
    lapiz = QPen(QColor(210, 214, 222, 150))
    lapiz.setWidthF(1.0)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(c, rh, rh)
    p.end()
    return pm


def pintar_brillo(lado, dpr=1.0):
    """El brillo cónico del vinilo (capa fija: la luz no gira con el disco)."""
    px = max(8, int(lado * dpr))
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    R = lado / 2.0
    c = QPointF(R, R)
    ruta = QPainterPath()
    ruta.addEllipse(c, R * 0.99, R * 0.99)
    hueco = QPainterPath()
    hueco.addEllipse(c, R * (R_ETIQUETA + 0.03), R * (R_ETIQUETA + 0.03))
    p.setClipPath(ruta.subtracted(hueco))
    g = QConicalGradient(c, 38)
    g.setColorAt(0.00, QColor(255, 255, 255, 0))
    g.setColorAt(0.035, QColor(255, 255, 255, 62))
    g.setColorAt(0.085, QColor(255, 255, 255, 0))
    g.setColorAt(0.50, QColor(255, 255, 255, 0))
    g.setColorAt(0.535, QColor(255, 255, 255, 50))
    g.setColorAt(0.585, QColor(255, 255, 255, 0))
    g.setColorAt(1.00, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, lado, lado), QBrush(g))
    # reflejo suave arriba a la izquierda
    r = QRadialGradient(QPointF(R * 0.55, R * 0.45), R * 0.95)
    r.setColorAt(0.0, QColor(255, 255, 255, 20))
    r.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, lado, lado), QBrush(r))
    p.end()
    return pm


class Geometria:
    """Dónde va cada cosa, para un disco de radio R centrado en (cx, cy)."""

    def __init__(self, ancho, alto_zona, margen_arriba=0):
        zona = max(120.0, alto_zona - margen_arriba)
        self.R = max(60.0, min(zona * 0.425, (ancho - 56) / 2.9))
        self.cx = ancho / 2.0 - 0.2 * self.R
        self.cy = margen_arriba + zona * 0.5
        px, py = PIVOTE
        self.pivote = QPointF(self.cx + px * self.R, self.cy + py * self.R)
        self.d = math.hypot(px, py) * self.R
        self.dir_centro = math.degrees(math.atan2(self.cy - self.pivote.y(),
                                                  self.cx - self.pivote.x()))
        self.L = LARGO_BRAZO * self.R

    def giro_para(self, fraccion_radio):
        """Ángulo del brazo para que la aguja caiga a `fraccion_radio` del radio."""
        r = fraccion_radio * self.R
        cosa = (self.d ** 2 + self.L ** 2 - r ** 2) / (2 * self.d * self.L)
        a = math.degrees(math.acos(max(-1.0, min(1.0, cosa))))
        return self.dir_centro - a

    def placa(self):
        R = self.R
        return QRectF(self.cx - 1.27 * R, self.cy - 1.13 * R, 2.97 * R, 2.26 * R)


def pintar_base(ancho, alto, geo, img, paleta, mancha, dpr=1.0):
    """Fondo + placa del tocadiscos + plato + sombra del disco: todo lo que no se mueve."""
    pm = QPixmap(max(8, int(ancho * dpr)), max(8, int(alto * dpr)))
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    c1, c2, c3 = paleta
    # fondo: color dominante de la carátula, desenfocado, con viñeta
    base = QColor.fromHsvF(max(0.0, c1.hsvHueF()), min(1.0, c1.hsvSaturationF() * 0.85), 0.13)
    p.fillRect(QRectF(0, 0, ancho, alto), base)
    if mancha is not None and not mancha.isNull():
        p.setOpacity(0.62)
        lado = max(ancho, alto) * 1.25
        p.drawImage(QRectF((ancho - lado) / 2, (alto - lado) / 2, lado, lado), mancha)
        p.setOpacity(1.0)
    p.setPen(Qt.NoPen)
    for color, fx, fy, k in ((c1, 0.30, 0.42, 0.75), (c2, 0.78, 0.30, 0.55), (c3, 0.55, 0.95, 0.6)):
        g = QRadialGradient(QPointF(ancho * fx, alto * fy), max(ancho, alto) * k)
        g.setColorAt(0.0, _con_alfa(color, 120))
        g.setColorAt(0.5, _con_alfa(color, 36))
        g.setColorAt(1.0, _con_alfa(color, 0))
        p.setBrush(QBrush(g))
        p.drawRect(QRectF(0, 0, ancho, alto))
    p.fillRect(QRectF(0, 0, ancho, alto), QColor(0, 0, 0, 96))
    v = QRadialGradient(QPointF(ancho / 2, alto * 0.46), max(ancho, alto) * 0.72)
    v.setColorAt(0.5, QColor(0, 0, 0, 0))
    v.setColorAt(1.0, QColor(0, 0, 0, 150))
    p.setBrush(QBrush(v))
    p.drawRect(QRectF(0, 0, ancho, alto))

    R = geo.R
    cx, cy = geo.cx, geo.cy
    # sombra de la placa
    placa = geo.placa()
    for i in range(7):
        grow = i * 5.0
        p.setBrush(QColor(0, 0, 0, 14))
        p.drawRoundedRect(placa.adjusted(-grow, -grow + 12, grow, grow + 14), 26 + grow, 26 + grow)
    # la placa: cristal oscuro con un filo de luz arriba
    g = QLinearGradient(placa.topLeft(), placa.bottomLeft())
    g.setColorAt(0.0, QColor(24, 25, 31, 215))
    g.setColorAt(1.0, QColor(9, 10, 13, 232))
    p.setBrush(QBrush(g))
    lapiz = QPen(QColor(255, 255, 255, 22))
    lapiz.setWidthF(1.0)
    p.setPen(lapiz)
    p.drawRoundedRect(placa, 26, 26)
    p.setPen(Qt.NoPen)
    # sombra del disco (cae hacia abajo a la derecha, suave)
    g = QRadialGradient(QPointF(cx + R * 0.05, cy + R * 0.09), R * 1.2)
    g.setColorAt(0.80, QColor(0, 0, 0, 170))
    g.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(cx + R * 0.05, cy + R * 0.09), R * 1.2, R * 1.2)
    # plato: anillo de metal oscuro con borde pulido
    rp = R * 1.045
    g = QLinearGradient(QPointF(cx - rp, cy - rp), QPointF(cx + rp, cy + rp))
    g.setColorAt(0.0, QColor("#4a4d57"))
    g.setColorAt(0.45, QColor("#16171c"))
    g.setColorAt(1.0, QColor("#2c2e36"))
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(cx, cy), rp, rp)
    p.setBrush(QColor("#0c0d10"))
    p.drawEllipse(QPointF(cx, cy), rp - R * 0.014, rp - R * 0.014)

    # base del brazo (el pivote)
    b = geo.pivote
    for rad, col in ((R * 0.145, QColor(0, 0, 0, 90)), ):
        p.setBrush(col)
        p.drawEllipse(QPointF(b.x() + 3, b.y() + 5), rad, rad)
    g = QRadialGradient(QPointF(b.x() - R * 0.03, b.y() - R * 0.03), R * 0.15)
    g.setColorAt(0.0, QColor("#5b5e69"))
    g.setColorAt(1.0, QColor("#1a1b20"))
    p.setBrush(QBrush(g))
    p.drawEllipse(b, R * 0.125, R * 0.125)
    lapiz = QPen(QColor(255, 255, 255, 40))
    lapiz.setWidthF(1.0)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(b, R * 0.125, R * 0.125)
    # apoyo del brazo (donde descansa cuando está levantado)
    ang = math.radians(geo.giro_para(R_EXTERIOR) - GIRO_REPOSO)
    punta = QPointF(b.x() + math.cos(ang) * geo.L * 1.02, b.y() + math.sin(ang) * geo.L * 1.02)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 22))
    p.drawRoundedRect(QRectF(punta.x() - R * 0.05, punta.y() + R * 0.02, R * 0.1, R * 0.07), 3, 3)
    p.end()
    return pm


def pintar_brazo(p, geo, giro, alzada, acento):
    """El brazo con su contrapeso y su cabezal, girado `giro` grados sobre el pivote.
    `alzada` (0..1) separa la sombra: cuanto más alto, más lejos cae."""
    R = geo.R
    b = geo.pivote

    def forma(q, sombra):
        tubo = max(3.0, R * 0.026)
        # contrapeso
        if not sombra:
            q.setPen(QPen(QColor(0, 0, 0, 120), 1.0))
            g = QLinearGradient(QPointF(0, -R * 0.06), QPointF(0, R * 0.06))
            g.setColorAt(0.0, QColor("#4a4d58"))
            g.setColorAt(1.0, QColor("#1b1c22"))
            q.setBrush(QBrush(g))
        q.drawRoundedRect(QRectF(-R * 0.36, -R * 0.06, R * 0.17, R * 0.12), R * 0.03, R * 0.03)
        # tubo
        if sombra:
            lapiz = QPen(QColor(0, 0, 0, 255), tubo)
            lapiz.setCapStyle(Qt.RoundCap)
            q.setPen(lapiz)
            q.drawLine(QPointF(-R * 0.19, 0), QPointF(geo.L, 0))
        else:
            lapiz = QPen(QColor("#9da1ad"), tubo)
            lapiz.setCapStyle(Qt.RoundCap)
            q.setPen(lapiz)
            q.drawLine(QPointF(-R * 0.19, 0), QPointF(geo.L, 0))
            lapiz = QPen(QColor(255, 255, 255, 120), max(1.0, tubo * 0.28))
            lapiz.setCapStyle(Qt.RoundCap)
            q.setPen(lapiz)
            q.drawLine(QPointF(-R * 0.15, -tubo * 0.22), QPointF(geo.L - 2, -tubo * 0.22))
        # cabezal: pieza corta, inclinada hacia el centro del disco
        q.save()
        q.translate(geo.L, 0)
        q.rotate(19)
        cab = QRectF(-R * 0.025, -R * 0.034, R * 0.175, R * 0.068)
        if not sombra:
            q.setPen(QPen(QColor(0, 0, 0, 140), 1.0))
            g = QLinearGradient(cab.topLeft(), cab.bottomLeft())
            g.setColorAt(0.0, QColor("#2c2e36"))
            g.setColorAt(1.0, QColor("#121317"))
            q.setBrush(QBrush(g))
        q.drawRoundedRect(cab, R * 0.016, R * 0.016)
        if not sombra:
            q.setPen(Qt.NoPen)
            q.setBrush(QColor(acento))
            q.drawRoundedRect(QRectF(cab.left() + R * 0.012, cab.top() + R * 0.012,
                                     R * 0.05, cab.height() - R * 0.024), 2, 2)
            # la aguja
            q.setBrush(QColor("#e9ecf2"))
            q.drawEllipse(QPointF(cab.right() - R * 0.012, 0), R * 0.011, R * 0.011)
        q.restore()

    # sombra: se aleja del disco al levantarse
    dx = R * (0.012 + 0.07 * alzada)
    dy = R * (0.02 + 0.10 * alzada)
    for grosor, alfa in ((1.0, 0.16), ):
        p.save()
        p.translate(b.x() + dx, b.y() + dy)
        p.rotate(giro)
        p.setOpacity(alfa * (1.0 - 0.35 * alzada))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0))
        forma(p, True)
        p.restore()
    p.save()
    p.translate(b.x(), b.y())
    p.rotate(giro)
    forma(p, False)
    p.restore()
    # tapa del pivote encima del brazo
    g = QRadialGradient(QPointF(b.x() - R * 0.02, b.y() - R * 0.02), R * 0.08)
    g.setColorAt(0.0, QColor("#8a8d99"))
    g.setColorAt(1.0, QColor("#2a2c33"))
    p.setPen(QPen(QColor(0, 0, 0, 120), 1.0))
    p.setBrush(QBrush(g))
    p.drawEllipse(b, R * 0.055, R * 0.055)


# ------------------------------------------------------------------ pagina

class _Elidida(QLabel):
    """Texto centrado que se corta con «…» en vez de ensanchar la pantalla."""

    def __init__(self, estilo, padre=None):
        super().__init__("", padre)
        self._texto = ""
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(estilo)
        self.setMinimumWidth(10)

    def poner(self, texto):
        self._texto = texto or ""
        self._repintar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._repintar()

    def _repintar(self):
        fm = self.fontMetrics()
        self.setText(fm.elidedText(self._texto, Qt.ElideRight, max(20, self.width() - 4)))


def _t(seg):
    seg = int(max(0, seg or 0))
    return f"{seg // 60}:{seg % 60:02d}"


class PaginaVinilo(QWidget):
    """El tocadiscos a pantalla completa de la ventana."""
    volver = Signal()
    titulo = "Vinilo"
    ALTO_PIE = 162

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.setFocusPolicy(Qt.NoFocus)
        self.setAutoFillBackground(False)

        # estado de la animacion
        self.angulo = 0.0
        self.velocidad = 0.0            # grados por segundo
        self.aguja = 0.0                # 0 levantada .. 1 posada
        self.prog = 0.0                 # progreso de la cancion que se muestra (0..1)
        self._prog_obj = 0.0
        self._dur = 0.0
        self._t = 0.0                   # reloj interno de la animacion (s)
        self._bajar_en = 0.0
        self._ult = None
        self._clave = None
        self._url = ""
        self.etiqueta_clave = ""        # de que cancion es la etiqueta que se ve
        self._img = QImage()
        self._img_pend = None           # carátula nueva esperando a que el brazo se levante
        self.paleta = paleta_de(None)
        self.mancha = None

        # caches
        self._pm_disco = None
        self._pm_brillo = None
        self._pm_base = None
        self._clave_disco = None
        self._clave_base = None
        self._geo = None
        self._arrastrando = False

        self.reloj = QTimer(self)
        self.reloj.setTimerType(Qt.PreciseTimer)
        self.reloj.timeout.connect(self._cuadro)
        self._t_pausa = QTimer(self)
        self._t_pausa.setSingleShot(True)
        self._t_pausa.setInterval(int(GRACIA_PAUSA * 1000))
        self._t_pausa.timeout.connect(self._fin_gracia)
        self.pantalla = MantenerPantalla()
        self.destroyed.connect(self.pantalla.liberar)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.pantalla.liberar)

        self._construir_controles()

        r = self.r
        r.pista_cambio.connect(self._pista)
        r.estado_cambio.connect(self._estado)
        r.posicion_cambio.connect(self._posicion)
        r.duracion_cambio.connect(self._duracion)
        self._duracion(getattr(r, "_duracion", 0.0))
        self._posicion(getattr(r, "_posicion", 0.0))
        self.prog = self._prog_obj
        self._poner_textos(r.actual)
        self._pedir_portada(r.actual, inmediato=True)
        if self._suena():
            self.velocidad = 0.0
            self._bajar_en = 0.0

    # ------------------------------------------------------------ controles
    def _construir_controles(self):
        self.pie = QWidget(self)
        self.pie.setAttribute(Qt.WA_TranslucentBackground)
        v = QVBoxLayout(self.pie)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addStretch(1)
        self.et_titulo = _Elidida("color:#FFFFFF;font-size:24px;font-weight:800;"
                                  "background:transparent;")
        self.et_artista = _Elidida("color:rgba(255,255,255,0.72);font-size:15px;"
                                   "font-weight:600;background:transparent;")
        v.addWidget(self.et_titulo)
        v.addWidget(self.et_artista)
        v.addSpacing(10)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        est = "color:rgba(255,255,255,0.62);font-size:12px;background:transparent;"
        self.et_actual = QLabel("0:00")
        self.et_actual.setStyleSheet(est)
        self.et_actual.setFixedWidth(42)
        self.et_actual.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.et_total = QLabel("0:00")
        self.et_total.setStyleSheet(est)
        self.et_total.setFixedWidth(42)
        self.barra = Deslizador(16)
        self.barra.movido.connect(self._moviendo)
        self.barra.soltado.connect(self._soltado)
        fila.addWidget(self.et_actual)
        fila.addWidget(self.barra, 1)
        fila.addWidget(self.et_total)
        v.addLayout(fila)
        botones = QHBoxLayout()
        botones.setSpacing(18)
        botones.addStretch(1)
        self.bt_anterior = BotonIcono("anterior", 24, "Anterior", 42, color="#E4E7EE",
                                      color_hover="#FFFFFF")
        self.bt_anterior.clicked.connect(self.r.anterior)
        self.bt_play = BotonPlay(56, claro=True)
        self.bt_play.setToolTip("Reproducir / pausar")
        self.bt_play.clicked.connect(self.r.alternar)
        self.bt_siguiente = BotonIcono("siguiente", 24, "Siguiente", 42, color="#E4E7EE",
                                       color_hover="#FFFFFF")
        self.bt_siguiente.clicked.connect(self.r.siguiente)
        for w in (self.bt_anterior, self.bt_play, self.bt_siguiente):
            botones.addWidget(w, 0, Qt.AlignVCenter)
        botones.addStretch(1)
        v.addSpacing(4)
        v.addLayout(botones)
        self.bt_play.set_sonando(self._suena())

        self.bt_pantalla = QPushButton("Mantener la pantalla encendida", self)
        self.bt_pantalla.setCheckable(True)
        self.bt_pantalla.setChecked(bool(self.ctx.ajustes["vinilo_pantalla"]))
        self.bt_pantalla.setCursor(Qt.PointingHandCursor)
        self.bt_pantalla.setFocusPolicy(Qt.NoFocus)
        self.bt_pantalla.setStyleSheet(_BOTON)
        self.bt_pantalla.setToolTip("Mientras suena el vinilo, la pantalla no se apaga ni el "
                                    "equipo entra en reposo")
        self.bt_pantalla.toggled.connect(self._cambio_pantalla)
        self.bt_cerrar = QPushButton("Cerrar", self)
        self.bt_cerrar.setCursor(Qt.PointingHandCursor)
        self.bt_cerrar.setFocusPolicy(Qt.NoFocus)
        self.bt_cerrar.setStyleSheet(_BOTON)
        self.bt_cerrar.setToolTip("Volver  (Esc)")
        self.bt_cerrar.clicked.connect(self.volver.emit)

    def _cambio_pantalla(self, on):
        self.ctx.ajustes["vinilo_pantalla"] = bool(on)
        try:
            self.ctx.ajustes.guardar()
        except Exception:
            pass
        self._evaluar_pantalla()

    # ------------------------------------------------------------ estado
    def _suena(self):
        return getattr(self.r, "estado", "") == "sonando"

    def _pista(self, p):
        self._poner_textos(p)
        clave = (p.get("clave") or p.get("video_id")) if p else None
        if clave != self._clave:
            self._clave = clave
            # el brazo se levanta y vuelve a posarse un instante despues
            self._bajar_en = self._t + ESPERA_BAJAR
            self.prog = self._prog_obj = 0.0
            self.barra.set_valor(0.0)
            self.et_actual.setText("0:00")
        self._pedir_portada(p)
        self._ritmo()

    def _estado(self, estado):
        self.bt_play.set_sonando(estado == "sonando")
        self.bt_play.set_cargando(estado == "cargando")
        if estado == "sonando" and self.aguja <= 0.0:
            self._bajar_en = max(self._bajar_en, self._t + 0.35)
        self._evaluar_pantalla()
        self._ritmo()

    def _posicion(self, seg):
        if self._dur > 0:
            self._prog_obj = max(0.0, min(1.0, float(seg or 0) / self._dur))
        if not self._arrastrando:
            self.et_actual.setText(_t(seg))
            self.barra.set_valor(self._prog_obj)

    def _duracion(self, d):
        self._dur = float(d or 0)
        self.et_total.setText(_t(self._dur))

    def _moviendo(self, v):
        self._arrastrando = True
        self.et_actual.setText(_t(v * self._dur))

    def _soltado(self, v):
        self._arrastrando = False
        if self._dur > 0:
            self.r.buscar(v * self._dur)

    def _poner_textos(self, p):
        if not p:
            self.et_titulo.poner("Nada sonando")
            self.et_artista.poner("Elige algo para escuchar")
            return
        self.et_titulo.poner(p.get("titulo") or "")
        artista = ", ".join(a.get("nombre", "") for a in p.get("artistas") or []) \
            or p.get("artista") or ""
        self.et_artista.poner(artista)

    def _pedir_portada(self, p, inmediato=False):
        url = (p.get("miniatura") or "") if p else ""
        self._url = url
        clave = (p.get("clave") or p.get("video_id") or url) if p else ""

        def llego(img, c=clave, u=url):
            if self._url != u:
                return
            self._recibir_portada(img if img is not None else QImage(), c, inmediato)
        if not url:
            llego(QImage())
        else:
            imagenes.imagen(url, llego)

    def _recibir_portada(self, img, clave, inmediato):
        # con el brazo posado se espera a que se levante para cambiar la etiqueta
        if inmediato or not self.isVisible() or self.aguja < 0.4:
            self._aplicar_portada(img, clave)
        else:
            self._img_pend = (img, clave)
            self._ritmo()

    def _aplicar_portada(self, img, clave):
        self._img_pend = None
        self._img = img
        self.etiqueta_clave = clave
        self.paleta = paleta_de(img)
        self.mancha = desenfocar(img)
        self._pm_disco = self._pm_base = None
        self.update()

    # ------------------------------------------------------------ pantalla encendida
    def _evaluar_pantalla(self):
        quiere = self.isVisible() and self.bt_pantalla.isChecked()
        if not quiere:
            self._t_pausa.stop()
            self.pantalla.liberar()
            return
        if self._suena():
            self._t_pausa.stop()
            self.pantalla.activar()
        elif self.pantalla.activa and not self._t_pausa.isActive():
            self._t_pausa.start()

    def _fin_gracia(self):
        if not self._suena():
            self.pantalla.liberar()

    # ------------------------------------------------------------ animacion
    def _quieto(self):
        return (not self._suena() and self.velocidad < 0.6 and self.aguja <= 0.0
                and self._img_pend is None)

    def _ritmo(self):
        if not self.isVisible():
            self.reloj.stop()
            return
        if self._quieto():
            self.reloj.stop()
            self.update()
        elif not self.reloj.isActive():
            self._ult = None
            self.reloj.start(MS_CUADRO)

    def _cuadro(self, dt=None):
        """Un cuadro de la animacion. `dt` explicito solo en las pruebas."""
        if dt is None:
            import time
            ahora = time.monotonic()
            dt = 0.0 if self._ult is None else min(0.05, ahora - self._ult)
            self._ult = ahora
        self._t += dt
        sonando = self._suena()
        # plato: inercia al arrancar y al frenar
        objetivo = GRADOS_POR_SEG if sonando else 0.0
        tau = TAU_ARRANQUE if objetivo > self.velocidad else TAU_FRENO
        self.velocidad += (objetivo - self.velocidad) * (1.0 - math.exp(-dt / tau))
        if not sonando and self.velocidad < 0.6:
            self.velocidad = 0.0
        self.angulo = (self.angulo + self.velocidad * dt) % 360.0
        # brazo
        if sonando and self._t >= self._bajar_en:
            self.aguja = min(1.0, self.aguja + dt / SEG_BAJAR)
        else:
            self.aguja = max(0.0, self.aguja - dt / SEG_SUBIR)
        if self._img_pend is not None and self.aguja < 0.4:
            self._aplicar_portada(*self._img_pend)
        # progreso: la aguja avanza hacia el centro sin saltos
        self.prog += (self._prog_obj - self.prog) * min(1.0, dt * 5.0)
        if self._quieto():
            self.reloj.stop()
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        p = self.r.actual
        clave = (p.get("clave") or p.get("video_id")) if p else None
        self._poner_textos(p)
        if clave != self._clave or not self.etiqueta_clave:
            self._clave = clave
            self._pedir_portada(p, inmediato=True)
        self.bt_play.set_sonando(self._suena())
        self._posicion(getattr(self.r, "_posicion", 0.0))
        self.prog = self._prog_obj
        if self._suena() and self.aguja <= 0.0:
            self._bajar_en = self._t + 0.5
        self._evaluar_pantalla()
        self._ritmo()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.reloj.stop()
        self._t_pausa.stop()
        self.pantalla.liberar()

    # ------------------------------------------------------------ pintura
    def resizeEvent(self, e):
        super().resizeEvent(e)
        w, h = self.width(), self.height()
        ancho_pie = max(260, min(620, w - 60))
        self.pie.setGeometry((w - ancho_pie) // 2, h - self.ALTO_PIE - 14, ancho_pie, self.ALTO_PIE)
        self.bt_cerrar.adjustSize()
        self.bt_cerrar.move(w - self.bt_cerrar.width() - 24, 18)
        self.bt_pantalla.adjustSize()
        self.bt_pantalla.move(24, 18)
        self._geo = None
        self._pm_disco = self._pm_base = self._pm_brillo = None

    def _dpr(self):
        try:
            return float(self.devicePixelRatioF())
        except Exception:
            return 1.0

    def _preparar(self):
        w, h = self.width(), self.height()
        if self._geo is None:
            self._geo = Geometria(w, h - self.ALTO_PIE - 24, margen_arriba=52)
        geo = self._geo
        dpr = self._dpr()
        if self._pm_base is None:
            self._pm_base = pintar_base(w, h, geo, self._img, self.paleta, self.mancha, dpr)
        if self._pm_disco is None:
            self._pm_disco = pintar_disco(geo.R * 2, self._img, self.paleta, dpr)
        if self._pm_brillo is None:
            self._pm_brillo = pintar_brillo(geo.R * 2, dpr)

    def giro_brazo(self):
        """Ángulo actual del brazo (grados): cambia al posarse, avanzar y levantarse."""
        geo = self._geo or Geometria(self.width(), self.height() - self.ALTO_PIE - 24, 52)
        reposo = geo.giro_para(R_EXTERIOR) - GIRO_REPOSO
        r = R_EXTERIOR - (R_EXTERIOR - R_INTERIOR) * self.prog
        jugando = geo.giro_para(r)
        return reposo + (jugando - reposo) * _suave(self.aguja)

    def paintEvent(self, _e):
        self._preparar()
        geo = self._geo
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setOpacity(0.97)
        p.drawPixmap(0, 0, self._pm_base)
        p.setOpacity(1.0)
        R = geo.R
        p.save()
        p.translate(geo.cx, geo.cy)
        p.rotate(self.angulo)
        p.drawPixmap(QPointF(-R, -R), self._pm_disco)
        p.restore()
        p.drawPixmap(QPointF(geo.cx - R, geo.cy - R), self._pm_brillo)
        pintar_brazo(p, geo, self.giro_brazo(), 1.0 - _suave(self.aguja), self.paleta[0])
        p.end()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.volver.emit()
            return
        super().keyPressEvent(e)
