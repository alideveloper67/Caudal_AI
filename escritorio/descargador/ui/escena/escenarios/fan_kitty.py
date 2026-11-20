# -*- coding: utf-8 -*-
"""Escenario «Fan de Hello Kitty»: el cuarto soñado de una chica fan, en ilustración kawaii suave.

Solo estética: rosa, lazos, corazones, fresas, flores, muebles y luz de día. No dibuja ningún personaje
ni su cara. Lo estático (habitación en perspectiva, papel pintado, muebles, luz, viñeta y grano) se pinta
una vez y se guarda en caché. Lo animado (tul de las cortinas, polvo en los rayos, corazones y lazos que
suben, destellos, bombillas y ondas de la música) va en cada cuadro, con sprites pre-renderizados.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
                           QRadialGradient, QTransform)

from .base import EscenarioBase, con_alfa, mezclar

ROSA = "#FF5C8A"
ROSA_SUAVE = "#FF8FAB"
ROSA_MEDIO = "#FFC2D4"
ROSA_CLARO = "#FFE6EE"
ROSA_FRESA = "#FFB3C7"
CREMA = "#FFF8F0"
DORADO = "#E8C27A"
ROJO_LAZO = "#E5243B"
SOMBRA = "#B0607A"
VINETA = "#D9708F"
GRANO = "#7A2A4A"
BLANCO = "#FFFFFF"
DULCES = (ROSA, ROSA_MEDIO, DORADO, BLANCO, ROJO_LAZO, ROSA_SUAVE)

# Geometría (fracciones de w y h). Punto de fuga (0.5, 0.48).
PUNTO_FUGA = (0.5, 0.48)
PARED = (0.25, 0.22, 0.75, 0.74)              # pared del fondo: x0, y0, x1, y1 (el suelo empieza en y1)
VENTANA = (0.66, 0.30, 0.73, 0.62)
CORTINAS = ((0.615, 0.670), (0.712, 0.748))   # x0, x1 de cada cortina
CABECERO = (0.40, 0.36, 0.60, 0.70)           # x0, y0, x1, y1
ESPEJO = (0.86, 0.47, 0.060, 0.115)           # cx, cy; rx (de w), ry (de h)
MESA = (0.78, 0.94, 0.625, 0.80)              # x0, x1, y0 (tablero), y1 (base)
ESTANTE = (0.265, 0.395, 0.34, 0.72)          # x0, x1, y0 (techo), y1 (base)
TABLAS_ESTANTE = (0.45, 0.56, 0.67)           # tablas intermedias
FRASCOS = ((0.282, 0.592), (0.312, 0.592), (0.342, 0.592), (0.372, 0.592))   # x, y superior
FRASCO_W, FRASCO_H = 0.022, 0.075
ALFOMBRA = (0.58, 0.93, 0.19, 0.07)           # cx, cy; rx (de w), ry (de h)
BOMBILLAS = 12
RAYOS = (((0.655, 0.62), (0.735, 0.62), (0.60, 1.0), (0.42, 1.0)), 40),\
    (((0.70, 0.62), (0.735, 0.62), (0.66, 1.0), (0.58, 1.0)), 28)
EJE_RAYO = ((0.695, 0.62), (0.51, 1.0))       # eje del rayo principal (para el polvo)


# ---------------------------------------------------------------- formas y colores

def _corazon():
    """Corazón de unos 1 de ancho, centrado en el origen (se escala al pintar)."""
    c = QPainterPath(QPointF(0, 0.35))
    c.cubicTo(-0.10, 0.20, -0.55, 0.00, -0.50, -0.25)
    c.cubicTo(-0.45, -0.50, -0.15, -0.55, 0, -0.25)
    c.cubicTo(0.15, -0.55, 0.45, -0.50, 0.50, -0.25)
    c.cubicTo(0.55, 0.00, 0.10, 0.20, 0, 0.35)
    return c


def _lazo():
    """Lacito de dos lóbulos y nudo, centrado en el origen (ancho ~1.7)."""
    lobulo = QPainterPath(QPointF(0, 0))
    lobulo.cubicTo(0.25, -0.50, 0.85, -0.45, 0.80, 0.00)
    lobulo.cubicTo(0.85, 0.45, 0.25, 0.50, 0, 0)
    lazo = QPainterPath()
    lazo.addPath(lobulo)
    lazo.addPath(QTransform().scale(-1, 1).map(lobulo))
    nudo = QPainterPath()
    nudo.addEllipse(QPointF(0, 0), 0.14, 0.14)
    lazo.addPath(nudo)
    return lazo


def _destello():
    """Estrella de cuatro puntas con curvas, radio 1."""
    s = QPainterPath(QPointF(0, -1))
    s.quadTo(0.14, -0.14, 1, 0)
    s.quadTo(0.14, 0.14, 0, 1)
    s.quadTo(-0.14, 0.14, -1, 0)
    s.quadTo(-0.14, -0.14, 0, -1)
    return s


def _fresa():
    """Fresa con su hojita, ancho ~1, centrada en el origen."""
    f = QPainterPath(QPointF(0, -0.42))
    f.cubicTo(0.30, -0.48, 0.52, -0.20, 0.42, 0.10)
    f.cubicTo(0.34, 0.40, 0.10, 0.58, 0, 0.62)
    f.cubicTo(-0.10, 0.58, -0.34, 0.40, -0.42, 0.10)
    f.cubicTo(-0.52, -0.20, -0.30, -0.48, 0, -0.42)
    f.addPath(_poly([QPointF(0, -0.40), QPointF(-0.34, -0.56), QPointF(-0.08, -0.52), QPointF(0, -0.40),
                     QPointF(0.08, -0.52), QPointF(0.34, -0.56)]))
    return f


def _poly(puntos):
    camino = QPainterPath(puntos[0])
    for q in puntos[1:]:
        camino.lineTo(q)
    camino.closeSubpath()
    return camino


def _redondo(cx, cy, radio):
    """Círculo como camino (para puntos, botones y lunares)."""
    camino = QPainterPath()
    camino.addEllipse(QPointF(cx, cy), radio, radio)
    return camino


def _cara_luz(color):
    """Cara iluminada: el color mezclado un 30 % con blanco."""
    return mezclar(QColor(color), QColor(BLANCO), 0.30)


def _cara_sombra(color):
    """Cara en sombra: el color mezclado un 25 % con #B0607A (rosa oscuro, nunca negro)."""
    return mezclar(QColor(color), QColor(SOMBRA), 0.25)


def _degradado(color, y0=-0.6, y1=0.6):
    """Degradado vertical de luz a sombra, en coordenadas unitarias (para usar dentro de una transformación)."""
    g = QLinearGradient(0, y0, 0, y1)
    g.setColorAt(0, _cara_luz(color))
    g.setColorAt(0.6, QColor(color))
    g.setColorAt(1, _cara_sombra(color))
    return g


def _colocar(p, camino, cx, cy, escala, relleno):
    p.save()
    p.translate(cx, cy)
    p.scale(escala, escala)
    p.fillPath(camino, relleno)
    p.restore()


def _sombra_proy(p, camino, dx, dy):
    """Sombra suave proyectada: 4 pasadas de alfa 15, cada una un poco más desplazada."""
    p.save()
    p.setPen(Qt.NoPen)
    for k in range(1, 5):
        p.save()
        p.translate(dx * k / 4, dy * k / 4)
        p.fillPath(camino, con_alfa(SOMBRA, 15))
        p.restore()
    p.restore()


def _en_px(camino, cx, cy, escala):
    """El camino unitario ya colocado en píxeles (para proyectar sombras)."""
    return QTransform().translate(cx, cy).scale(escala, escala).map(camino)


def _caja(p, x, y, ancho, alto, color, lado=0.0):
    """Caja con cara frontal iluminada y cara lateral derecha en sombra."""
    p.fillRect(QRectF(x, y, ancho, alto), _cara_luz(color))
    if lado > 0:
        cara = _poly([QPointF(x + ancho, y), QPointF(x + ancho + lado, y - lado * 0.5),
                      QPointF(x + ancho + lado, y + alto - lado * 0.5), QPointF(x + ancho, y + alto)])
        p.fillPath(cara, _cara_sombra(color))


def _elipse(p, cx, cy, rx, ry, color):
    """Elipse con luz arriba a la izquierda y sombra abajo a la derecha."""
    camino = QPainterPath()
    camino.addEllipse(QPointF(cx, cy), rx, ry)
    g = QRadialGradient(QPointF(cx - rx * 0.3, cy - ry * 0.4), max(rx, ry) * 1.5)
    g.setColorAt(0, _cara_luz(color))
    g.setColorAt(0.65, QColor(color))
    g.setColorAt(1, _cara_sombra(color))
    p.fillPath(camino, g)


def _festones(p, x0, x1, y_arriba, y_abajo, n, prof, relleno):
    """Banda con borde inferior festoneado (volantes, valances, bordes de cojines)."""
    camino = QPainterPath(QPointF(x0, y_arriba))
    camino.lineTo(QPointF(x1, y_arriba))
    camino.lineTo(QPointF(x1, y_abajo))
    for i in range(n):
        xa = x1 - (x1 - x0) * i / n
        xb = x1 - (x1 - x0) * (i + 1) / n
        camino.quadTo(QPointF((xa + xb) / 2, y_abajo + prof), QPointF(xb, y_abajo))
    camino.closeSubpath()
    p.fillPath(camino, relleno)


def _cojin_redondo(p, cx, cy, radio, color):
    """Cojín redondo con volante de pequeñas ondas en el borde."""
    for i in range(18):
        a = math.tau * i / 18
        _elipse(p, cx + radio * math.cos(a), cy + radio * 0.8 * math.sin(a), radio * 0.16, radio * 0.16,
                color)
    _elipse(p, cx, cy, radio, radio * 0.8, color)


def _cojin_corazon(p, cx, cy, ancho, color):
    camino = _corazon()
    _sombra_proy(p, _en_px(camino, cx + ancho * 0.05, cy + ancho * 0.08, ancho), ancho * 0.02, ancho * 0.03)
    _colocar(p, camino, cx, cy, ancho, _degradado(color))


def _lazo_plano(p, cx, cy, ancho, color):
    _colocar(p, _lazo(), cx, cy, ancho / 1.7, color)


def _lazo_en(p, cx, cy, ancho, color):
    """Lazo con luz y sombra (ancho en píxeles)."""
    _colocar(p, _lazo(), cx, cy, ancho / 1.7, _degradado(color))


def _fresa_plana(p, cx, cy, ancho, color):
    _colocar(p, _fresa(), cx, cy, ancho, color)


def _sprite_estrella():
    """Destello de cuatro puntas pre-renderizado (se dibuja con opacidad en cada cuadro)."""
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    pc = QPainter(pm)
    try:
        pc.setRenderHint(QPainter.Antialiasing, True)
        pc.translate(32, 32)
        pc.scale(30, 30)
        pc.fillPath(_destello(), QColor(BLANCO))
    finally:
        pc.end()
    return pm


def _sprite(forma, color, con_brillo=True):
    """Sprite de 96 px pre-renderizado: forma con luz y sombra y un brillo, para animar después."""
    pm = QPixmap(96, 96)
    pm.fill(QColor(0, 0, 0, 0))
    pc = QPainter(pm)
    try:
        pc.setRenderHint(QPainter.Antialiasing, True)
        pc.translate(48, 48)
        pc.scale(42, 42)
        pc.fillPath(forma, _degradado(color))
        pc.setPen(QPen(con_alfa(SOMBRA, 120), 0.05, Qt.SolidLine, Qt.RoundCap))
        pc.setBrush(Qt.NoBrush)
        pc.strokePath(forma, pc.pen())
        if con_brillo:
            pc.setPen(Qt.NoPen)
            brillo = QPainterPath()
            brillo.addEllipse(QPointF(-0.25, -0.22), 0.11, 0.07)
            pc.fillPath(brillo, con_alfa(BLANCO, 120))
    finally:
        pc.end()
    return pm


def _posiciones_bombillas():
    """Posiciones (fracciones) de las bombillas del tocador, en un anillo alrededor del espejo."""
    mx, my, rx, ry = ESPEJO
    return [(mx + rx * 1.22 * math.cos(math.tau * i / BOMBILLAS), my + ry * 1.22 * math.sin(math.tau * i / BOMBILLAS))
            for i in range(BOMBILLAS)]


def _peluche(p, x, y_base, s, color, conejo=False):
    """Peluche genérico sin cara: cuerpo, cabeza y orejas redondas (círculos), sin marca."""
    _elipse(p, x, y_base - s * 0.9, s * 0.9, s * 0.9, color)
    _elipse(p, x, y_base - s * 2.1, s * 0.62, s * 0.60, color)
    for lado in (-1, 1):
        if conejo:
            _elipse(p, x + lado * s * 0.22, y_base - s * 3.1, s * 0.18, s * 0.50, color)
        else:
            _elipse(p, x + lado * s * 0.50, y_base - s * 2.8, s * 0.22, s * 0.22, color)


def _regalo(p, x, y_base, ancho, alto, color):
    """Caja de regalo con cinta cruzada y lazo encima."""
    y_top = y_base - alto
    _caja(p, x, y_top, ancho, alto, color, lado=ancho * 0.18)
    p.fillRect(QRectF(x + ancho * 0.42, y_top, ancho * 0.16, alto), con_alfa(ROJO_LAZO, 200))
    p.fillRect(QRectF(x, y_top + alto * 0.42, ancho, alto * 0.14), con_alfa(ROJO_LAZO, 200))
    _lazo_en(p, x + ancho * 0.5, y_top, ancho * 0.7, ROJO_LAZO)


def _frasco(p, x, y, ancho, alto, r):
    """Frasco de vidrio con dulces de colores y tapa dorada."""
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(QRectF(x, y, ancho, alto), ancho * 0.3, ancho * 0.3)
    p.fillPath(cuerpo, con_alfa(BLANCO, 110))
    tamano = ancho * 0.22
    for fila in range(3):
        for col in range(2):
            color = DULCES[r.randrange(len(DULCES))]
            cx = x + ancho * (0.30 + 0.40 * col)
            cy = y + alto * (0.30 + 0.22 * fila)
            _elipse(p, cx, cy, tamano * 0.5, tamano * 0.5, color)
    _caja(p, x - ancho * 0.08, y - alto * 0.10, ancho * 1.16, alto * 0.10, DORADO)
    p.strokePath(cuerpo, QPen(con_alfa(BLANCO, 190), 1.4))


def _sombra_contacto(p, cx, cy, rx, ry):
    """Elipse rosada oscura bajo un objeto para que no flote (alfa 60)."""
    camino = QPainterPath()
    camino.addEllipse(QPointF(cx, cy), rx, ry)
    p.fillPath(camino, con_alfa(SOMBRA, 60))


def _almohada(p, x0, y0, x1, y1, color):
    """Almohada rectangular redondeada con volante en el borde inferior."""
    cuerpo = QPainterPath()
    cuerpo.addRoundedRect(QRectF(x0, y0, x1 - x0, y1 - y0), (x1 - x0) * 0.22, (y1 - y0) * 0.35)
    g = QLinearGradient(0, y0, 0, y1)
    g.setColorAt(0, _cara_luz(color))
    g.setColorAt(0.6, QColor(color))
    g.setColorAt(1, _cara_sombra(color))
    p.fillPath(cuerpo, g)
    _festones(p, x0 + (x1 - x0) * 0.05, x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.12, y1, 6,
              (y1 - y0) * 0.14, _cara_luz(color))


class EscenarioFanKitty(EscenarioBase):
    NOMBRE = "Fan de Hello Kitty"
    ACENTO = "#FF5C8A"
    SEMILLA = 23

    def preparar(self):
        r = self.rnd
        self._pm_estrella = _sprite_estrella()
        self._sprites = {
            "corazon_rosa": _sprite(_corazon(), ROSA),
            "corazon_blanco": _sprite(_corazon(), BLANCO),
            "lazo_rojo": _sprite(_lazo(), ROJO_LAZO, con_brillo=False),
            "lazo_rosa": _sprite(_lazo(), ROSA_SUAVE, con_brillo=False),
        }
        # 18 corazones y 12 lazos: (x0, y0, tamaño en fracción de h, velocidad, fase, sprite, alfa)
        self._flotantes = [self._flotante(r, ("corazon_rosa", "corazon_blanco")) for _ in range(18)]
        self._flotantes += [self._flotante(r, ("lazo_rojo", "lazo_rosa")) for _ in range(12)]
        # 70 motas de polvo a lo largo del rayo: (s 0..1, desplazamiento lateral -1..1, radio, alfa, fase, vel.)
        self._motas = [(r.random(), r.uniform(-1, 1), r.uniform(0.0012, 0.0035), r.randint(40, 120),
                        r.uniform(0, math.tau), r.uniform(0.5, 1.2)) for _ in range(70)]
        # 20 destellos: 10 en el anillo del espejo, 10 sobre los frascos: (fx, fy, tamaño, fase, periodo)
        self._destellos = []
        for i in range(20):
            if i < 10:
                a = r.uniform(0, math.tau)
                fx = ESPEJO[0] + ESPEJO[2] * 1.12 * math.cos(a)
                fy = ESPEJO[1] + ESPEJO[3] * 1.12 * math.sin(a)
            else:
                jx, jy = FRASCOS[i % len(FRASCOS)]
                fx = jx + FRASCO_W * 0.5
                fy = jy + FRASCO_H * r.uniform(0.1, 0.9)
            self._destellos.append((fx, fy, r.uniform(0.010, 0.022), r.uniform(0, 10), r.uniform(3, 6)))
        self._bombillas = _posiciones_bombillas()

    @staticmethod
    def _flotante(r, claves):
        return (r.random(), r.random(), r.uniform(0.024, 0.040), r.uniform(0.012, 0.030),
                r.uniform(0.0, math.tau), r.choice(claves), r.randint(110, 210))

    # ------------------------------------------------------------ estático (una vez)

    def pintar_estatico(self, p, w, h):
        r = random.Random(71)
        p.setPen(Qt.NoPen)
        self._paredes(p, w, h)
        self._ventana(p, w, h)
        self._estanteria(p, w, h, r)
        self._suelo(p, w, h, r)
        self._alfombra(p, w, h, r)
        self._cama(p, w, h)
        self._cojines_suelo(p, w, h)
        self._tocador(p, w, h)
        self._guirnalda(p, w, h)
        self._rayos(p, w, h)
        self._vineta(p, w, h)
        self._grano(p, w, h, r)

    def _paredes(self, p, w, h):
        x0, y0, x1, y1 = PARED
        techo = _poly([QPointF(0, 0), QPointF(w, 0), QPointF(x1 * w, y0 * h), QPointF(x0 * w, y0 * h)])
        izq = _poly([QPointF(0, 0), QPointF(x0 * w, y0 * h), QPointF(x0 * w, y1 * h), QPointF(0, h)])
        der = _poly([QPointF(w, 0), QPointF(x1 * w, y0 * h), QPointF(x1 * w, y1 * h), QPointF(w, h)])
        fondo = QPainterPath()
        fondo.addRect(QRectF(x0 * w, y0 * h, (x1 - x0) * w, (y1 - y0) * h))
        paredes = QPainterPath()
        for camino in (techo, izq, der, fondo):
            paredes.addPath(camino)

        gt = QLinearGradient(0, 0, 0, y0 * h)
        gt.setColorAt(0, QColor(CREMA))
        gt.setColorAt(1, QColor(ROSA_CLARO))
        p.fillPath(techo, gt)
        p.fillPath(fondo, QColor(ROSA_CLARO))
        gi = QLinearGradient(0, 0, x0 * w, 0)              # pared izquierda, en sombra hacia el borde
        gi.setColorAt(0, _cara_sombra(ROSA_CLARO))
        gi.setColorAt(1, QColor(ROSA_CLARO))
        p.fillPath(izq, gi)
        gd = QLinearGradient(w, 0, x1 * w, 0)              # pared derecha, algo más luminosa hacia la ventana
        gd.setColorAt(0, _cara_sombra(ROSA_MEDIO))
        gd.setColorAt(1, QColor("#FFDCE8"))
        p.fillPath(der, gd)

        # papel pintado: lazos y fresas pequeñas en #FFB3C7 alfa 50
        p.save()
        p.setClipPath(paredes)
        paso = 0.075 * h
        fila = 0
        y = paso * 0.3
        while y < h + paso:
            x = paso * 0.5 if fila % 2 else 0.0
            while x < w + paso:
                if (fila + int(x / paso)) % 2 == 0:
                    _lazo_plano(p, x, y, paso * 0.40, con_alfa(ROSA_FRESA, 50))
                else:
                    _fresa_plana(p, x, y, paso * 0.30, con_alfa(ROSA_FRESA, 50))
                x += paso
            y += paso
            fila += 1
        p.restore()

        # zócalo rosa oscuro y sombra en las esquinas
        p.fillRect(QRectF(0, y1 * h - 0.006 * h, x0 * w, 0.006 * h), con_alfa(SOMBRA, 60))
        p.fillRect(QRectF(x1 * w, y1 * h - 0.006 * h, (1 - x1) * w, 0.006 * h), con_alfa(SOMBRA, 40))

    def _ventana(self, p, w, h):
        x0, y0, x1, y1 = VENTANA
        vx0, vy0, vx1, vy1 = x0 * w, y0 * h, x1 * w, y1 * h
        # halo de luz de día alrededor de la ventana
        self.brillo(p, (vx0 + vx1) / 2, (vy0 + vy1) / 2, w * 0.14, BLANCO, alfa=22)
        # marco crema con alféizar
        marco = 0.010 * w
        p.fillRect(QRectF(vx0 - marco, vy0 - marco, vx1 - vx0 + 2 * marco, vy1 - vy0 + 2 * marco),
                   _cara_luz(CREMA))
        cristal = QLinearGradient(0, vy0, 0, vy1)
        cristal.setColorAt(0, QColor("#FFF6FA"))
        cristal.setColorAt(1, QColor("#FFD3E1"))
        p.fillRect(QRectF(vx0, vy0, vx1 - vx0, vy1 - vy0), cristal)
        p.fillRect(QRectF((x0 + x1) / 2 * w - 0.004 * w, vy0, 0.008 * w, vy1 - vy0), _cara_luz(CREMA))
        p.fillRect(QRectF(vx0, (y0 + y1) / 2 * h - 0.004 * h, vx1 - vx0, 0.008 * h), _cara_luz(CREMA))
        p.fillRect(QRectF(vx0 - marco * 1.6, vy1 + marco * 0.2, vx1 - vx0 + marco * 3.2, 0.014 * h),
                   _cara_luz(ROSA_MEDIO))

        # barra dorada, volante superior, lazos de recogida y festones de cada cortina
        xr0, xr1 = CORTINAS[0][0] * w, CORTINAS[1][1] * w
        p.setPen(QPen(QColor(DORADO), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(xr0 - 0.006 * w, 0.27 * h), QPointF(xr1 + 0.006 * w, 0.27 * h))
        p.setPen(Qt.NoPen)
        for xf in (xr0 - 0.006 * w, xr1 + 0.006 * w):
            p.fillPath(_redondo(xf, 0.27 * h, 0.006 * w), _degradado(DORADO, -0.6, 0.6))
        _festones(p, xr0, xr1, 0.262 * h, 0.292 * h, 8, 0.020 * h, _cara_luz(ROSA_MEDIO))
        for c0, c1 in CORTINAS:
            _festones(p, c0 * w, c1 * w, 0.604 * h, 0.622 * h, 6, 0.014 * h, con_alfa(CREMA, 200))
        _lazo_en(p, CORTINAS[0][1] * w - 0.004 * w, 0.45 * h, 0.022 * w, ROJO_LAZO)
        _lazo_en(p, CORTINAS[1][0] * w + 0.004 * w, 0.45 * h, 0.022 * w, ROJO_LAZO)

    def _estanteria(self, p, w, h, r):
        x0, x1, yt, yb = ESTANTE[0] * w, ESTANTE[1] * w, ESTANTE[2] * h, ESTANTE[3] * h
        fondo = QPainterPath()
        fondo.addRect(QRectF(x0, yt, x1 - x0, yb - yt))
        _sombra_proy(p, fondo, 0.006 * w, 0.008 * h)
        _sombra_contacto(p, (x0 + x1) / 2 + 0.006 * w, yb + 0.002 * h, (x1 - x0) / 2 + 0.010 * w, 0.007 * h)
        p.fillPath(fondo, con_alfa(ROSA_MEDIO, 150))
        # laterales y tablas blancas, con sombra bajo cada tabla
        for xl in (x0 - 0.004 * w, x1 - 0.004 * w):
            p.fillRect(QRectF(xl, yt, 0.008 * w, yb - yt + 0.008 * h), _cara_luz(CREMA))
        for yf in TABLAS_ESTANTE + (ESTANTE[3],):
            ty = yf * h
            p.fillRect(QRectF(x0 - 0.004 * w, ty - 0.008 * h, x1 - x0 + 0.008 * w, 0.008 * h), _cara_luz(CREMA))
            p.fillRect(QRectF(x0, ty, x1 - x0, 0.004 * h), con_alfa(SOMBRA, 45))
        # nivel 1: peluches genéricos (osos y conejos) sobre la tabla 0.45
        base = TABLAS_ESTANTE[0] * h
        s = 0.016 * h
        _peluche(p, 0.296 * w, base - 0.002 * h, s, CREMA)
        _peluche(p, 0.340 * w, base - 0.002 * h, s, ROSA_MEDIO, conejo=True)
        _peluche(p, 0.374 * w, base - 0.002 * h, s * 0.8, ROSA_CLARO)
        # nivel 2: cajas de regalo con lazo sobre la tabla 0.56
        base = TABLAS_ESTANTE[1] * h
        _regalo(p, 0.283 * w, base - 0.002 * h, 0.030 * w, 0.040 * h, ROSA_MEDIO)
        _regalo(p, 0.322 * w, base - 0.002 * h, 0.026 * w, 0.030 * h, DORADO)
        _regalo(p, 0.354 * w, base - 0.002 * h, 0.022 * w, 0.050 * h, ROSA_SUAVE)
        # nivel 3: frascos de dulces sobre la tabla 0.67
        for jx, jy in FRASCOS:
            _frasco(p, jx * w, jy * h, FRASCO_W * w, FRASCO_H * h, r)
        # nivel 4: pequeño peluche sobre la base
        _peluche(p, 0.300 * w, ESTANTE[3] * h - 0.002 * h, 0.011 * h, ROSA_CLARO, conejo=True)

    def _suelo(self, p, w, h, r):
        x0, y0, x1, y1 = PARED
        suelo = _poly([QPointF(0, h), QPointF(x0 * w, y1 * h), QPointF(x1 * w, y1 * h), QPointF(w, h)])
        vx, vy = PUNTO_FUGA[0] * w, PUNTO_FUGA[1] * h
        p.save()
        p.setClipPath(suelo)
        base = QLinearGradient(0, y1 * h, 0, h)
        base.setColorAt(0, QColor("#F9DDCD"))
        base.setColorAt(1, QColor("#EFC3AC"))
        p.fillPath(suelo, base)

        n = 14
        xs = [-0.3 * w + 1.6 * w * i / n for i in range(n + 1)]

        def xen(xb, yy):
            """x de la línea que va del punto de fuga a xb, a la altura yy (píxeles)."""
            return vx + (xb - vx) * (yy - vy) / (h - vy)

        for i in range(n):
            tono = QColor("#F8D5C3") if i % 2 == 0 else QColor("#F4CBB6")
            tono = mezclar(tono, QColor(BLANCO), r.uniform(0.0, 0.12))
            p.fillPath(_poly([QPointF(vx, vy), QPointF(xs[i], h), QPointF(xs[i + 1], h)]), tono)

        # juntas de las tablas (líneas al punto de fuga) y juntas de cabeza escalonadas
        p.setBrush(Qt.NoBrush)
        juntas = QPainterPath()
        for xb in xs:
            juntas.moveTo(QPointF(vx, vy))
            juntas.lineTo(QPointF(xb, h))
        p.setPen(QPen(con_alfa(SOMBRA, 55), 1.2))
        p.drawPath(juntas)
        for i in range(n):
            for fila_f in (0.79, 0.85, 0.91, 0.96):
                yy = (fila_f + (0.03 if i % 2 else 0.0)) * h
                p.drawLine(QPointF(xen(xs[i], yy), yy), QPointF(xen(xs[i + 1], yy), yy))
        # vetas finas
        p.setPen(QPen(con_alfa(SOMBRA, 26), 1.0))
        for i in range(n):
            for g in range(2):
                mid = (xs[i] + xs[i + 1]) / 2 + g * 0.3 * (xs[i + 1] - xs[i])
                veta = QPainterPath(QPointF(xen(mid, 0.76 * h), 0.76 * h))
                for k in range(1, 9):
                    yy = h * (0.76 + 0.24 * k / 8)
                    veta.lineTo(QPointF(xen(mid, yy) + 0.002 * w * math.sin(k * 1.3 + i), yy))
                p.drawPath(veta)
        # línea de encuentro pared-suelo
        p.setPen(QPen(con_alfa(SOMBRA, 90), 2))
        p.drawLine(QPointF(x0 * w, y1 * h), QPointF(x1 * w, y1 * h))
        p.restore()

    def _alfombra(self, p, w, h, r):
        cx, cy = ALFOMBRA[0] * w, ALFOMBRA[1] * h
        rx, ry = ALFOMBRA[2] * w, ALFOMBRA[3] * h
        # círculo en perspectiva: escala vertical sobre un círculo con degradado radial
        p.save()
        p.translate(cx, cy)
        p.scale(1, ry / rx)
        g = QRadialGradient(QPointF(0, 0), rx)
        g.setColorAt(0, QColor("#FFD9E4"))
        g.setColorAt(0.8, QColor(ROSA_MEDIO))
        g.setColorAt(1, QColor("#FFB3C7"))
        circulo = QPainterPath()
        circulo.addEllipse(QPointF(0, 0), rx, rx)
        p.fillPath(circulo, g)
        p.restore()
        # pelo: trazos cortos radiales alrededor del borde
        for i in range(260):
            a = math.tau * i / 260 + r.uniform(-0.01, 0.01)
            nx, ny = math.cos(a) / rx, math.sin(a) / ry
            longitud_n = math.hypot(nx, ny)
            nx, ny = nx / longitud_n, ny / longitud_n
            ex, ey = cx + rx * math.cos(a), cy + ry * math.sin(a)
            largo = r.uniform(0.010, 0.020) * h
            color = ROSA_CLARO if i % 2 else ROSA_SUAVE
            p.setPen(QPen(con_alfa(color, 150), 2.2, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(ex - nx * largo * 0.3, ey - ny * largo * 0.3),
                       QPointF(ex + nx * largo, ey + ny * largo))
        anillo = QPainterPath()
        anillo.addEllipse(QPointF(cx, cy), rx * 0.72, ry * 0.72)
        p.setPen(QPen(con_alfa(ROSA_SUAVE, 90), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(anillo)
        p.setPen(Qt.NoPen)

    def _cama(self, p, w, h):
        hx0, hy0, hx1, hy1 = CABECERO[0] * w, CABECERO[1] * h, CABECERO[2] * w, CABECERO[3] * h
        # cabecero acolchado con sombra sobre la pared
        cabecero = QPainterPath()
        cabecero.addRoundedRect(QRectF(hx0, hy0, hx1 - hx0, hy1 - hy0), 0.018 * w, 0.018 * w)
        _sombra_proy(p, cabecero, 0.006 * w, 0.008 * h)
        g = QLinearGradient(0, hy0, 0, hy1)
        g.setColorAt(0, _cara_luz(ROSA_MEDIO))
        g.setColorAt(1, QColor(ROSA_MEDIO))
        p.fillPath(cabecero, g)
        # botones: rombos con su punto en el centro
        p.save()
        p.setClipPath(cabecero)
        dx, dy = 0.024 * w, 0.030 * h
        fila = 0
        y = hy0 + dy * 0.5
        while y < hy1 + dy:
            x = hx0 + (dx * 0.5 if fila % 2 else 0.0)
            while x < hx1 + dx:
                rombo = _poly([QPointF(x, y - dy * 0.5), QPointF(x + dx * 0.5, y),
                               QPointF(x, y + dy * 0.5), QPointF(x - dx * 0.5, y)])
                p.fillPath(rombo, con_alfa(SOMBRA, 48))
                p.fillPath(_redondo(x, y, 0.0026 * w), con_alfa(CREMA, 200))
                x += dx
            y += dy * 0.5
            fila += 1
        p.restore()
        p.setPen(QPen(con_alfa(SOMBRA, 60), 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawPath(cabecero)
        p.setPen(Qt.NoPen)

        # edredón: se extiende hacia el espectador, estampado de lunares y lazos
        edredon = _poly([QPointF(0.40 * w, 0.66 * h), QPointF(0.60 * w, 0.66 * h),
                         QPointF(0.675 * w, 0.90 * h), QPointF(0.325 * w, 0.90 * h)])
        # patas cortas bajo el somier (quedan tapadas por el edredón en su parte superior)
        for lx in (0.335, 0.655):
            p.fillRect(QRectF(lx * w, 0.89 * h, 0.014 * w, 0.035 * h), _cara_sombra(ROSA_MEDIO))
        _sombra_proy(p, edredon, 0.010 * w, 0.012 * h)
        g = QLinearGradient(0, 0.66 * h, 0, 0.90 * h)
        g.setColorAt(0, QColor("#FFF2F7"))
        g.setColorAt(0.5, QColor(ROSA_CLARO))
        g.setColorAt(1, QColor("#FFC8D9"))
        p.fillPath(edredon, g)
        # canto del colchón: franja inferior más oscura, alto 0.03*h
        canto = _poly([QPointF(0.3344 * w, 0.87 * h), QPointF(0.6656 * w, 0.87 * h),
                       QPointF(0.675 * w, 0.90 * h), QPointF(0.325 * w, 0.90 * h)])
        p.fillPath(canto, _cara_sombra(ROSA_MEDIO))
        p.save()
        p.setClipPath(edredon)
        fila = 0
        y = 0.67 * h
        while y < 0.92 * h:
            x = 0.30 * w + (0.017 * w if fila % 2 else 0.0)
            while x < 0.70 * w:
                p.fillPath(_redondo(x, y, 0.0036 * w), con_alfa(ROSA_SUAVE, 110))
                x += 0.034 * w
            y += 0.045 * h
            fila += 1
        p.restore()
        # tres pliegues: sombra suave y un reflejo claro encima
        p.save()
        p.setClipPath(edredon)
        p.setBrush(Qt.NoBrush)
        for y_f, curva in ((0.72, 0.022), (0.78, 0.026), (0.84, 0.020)):
            pl = QPainterPath(QPointF(0.30 * w, y_f * h))
            pl.cubicTo(QPointF(0.42 * w, (y_f + curva) * h), QPointF(0.58 * w, (y_f + curva) * h),
                       QPointF(0.70 * w, y_f * h))
            p.setPen(QPen(con_alfa(SOMBRA, 45), 5, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(pl)
            p.save()
            p.translate(0, -0.005 * h)
            p.setPen(QPen(con_alfa(CREMA, 130), 2, Qt.SolidLine, Qt.RoundCap))
            p.drawPath(pl)
            p.restore()
        p.restore()
        p.setPen(Qt.NoPen)
        _lazo_en(p, 0.42 * w, 0.74 * h, 0.030 * w, ROJO_LAZO)
        _lazo_en(p, 0.57 * w, 0.82 * h, 0.034 * w, ROJO_LAZO)
        _lazo_en(p, 0.45 * w, 0.87 * h, 0.026 * w, ROJO_LAZO)
        _festones(p, 0.325 * w, 0.675 * w, 0.888 * h, 0.900 * h, 8, 0.024 * h, _cara_luz(ROSA_MEDIO))

        # dosel: tela que cae del techo en forma de cúpula con festones
        dosel = QPainterPath(QPointF(0.392 * w, 0.40 * h))
        dosel.cubicTo(QPointF(0.398 * w, 0.20 * h), QPointF(0.602 * w, 0.20 * h), QPointF(0.608 * w, 0.40 * h))
        n = 6
        for i in range(n):
            xa = 0.608 * w - (0.216 * w) * i / n
            xb = 0.608 * w - (0.216 * w) * (i + 1) / n
            dosel.quadTo(QPointF((xa + xb) / 2, 0.435 * h), QPointF(xb, 0.40 * h))
        dosel.closeSubpath()
        _sombra_proy(p, dosel, 0.006 * w, 0.010 * h)
        gd = QLinearGradient(0, 0.22 * h, 0, 0.44 * h)
        gd.setColorAt(0, QColor("#FFD6E2"))
        gd.setColorAt(1, QColor(ROSA_SUAVE))
        p.fillPath(dosel, gd)
        p.setPen(QPen(con_alfa(SOMBRA, 60), 1.4))
        for x_f in (0.46, 0.50, 0.54):
            pliegue = QPainterPath(QPointF(x_f * w, 0.27 * h))
            pliegue.quadTo(QPointF(x_f * w + 0.006 * w, 0.34 * h), QPointF(x_f * w + 0.002 * w, 0.42 * h))
            p.drawPath(pliegue)
        p.setPen(Qt.NoPen)

        # cojines: dos almohadas, un corazón sobre el edredón
        for xa, xb in ((0.395, 0.495), (0.505, 0.605)):
            sombra_alm = QPainterPath()
            sombra_alm.addRoundedRect(QRectF(xa * w, 0.555 * h, (xb - xa) * w, 0.10 * h),
                                      (xb - xa) * w * 0.22, 0.035 * h)
            _sombra_proy(p, sombra_alm, 0.006 * w, 0.012 * h)
        _almohada(p, 0.395 * w, 0.555 * h, 0.495 * w, 0.655 * h, CREMA)
        _almohada(p, 0.505 * w, 0.555 * h, 0.605 * w, 0.655 * h, ROSA_CLARO)
        _cojin_corazon(p, 0.46 * w, 0.80 * h, 0.055 * h, ROSA)

    def _cojines_suelo(self, p, w, h):
        _cojin_redondo(p, 0.72 * w, 0.92 * h, 0.026 * h, ROSA_SUAVE)
        _cojin_corazon(p, 0.74 * w, 0.975 * h, 0.060 * h, ROSA_MEDIO)
        _cojin_redondo(p, 0.45 * w, 0.975 * h, 0.022 * h, ROSA_CLARO)

    def _tocador(self, p, w, h):
        mx, my, mrx, mry = ESPEJO
        cx, cy, rx, ry = mx * w, my * h, mrx * w, mry * h
        x0, x1, y0, y1 = MESA[0] * w, MESA[1] * w, MESA[2] * h, MESA[3] * h
        # patas y sombra en el suelo
        for px in (x0 + 0.012 * w, x1 - 0.020 * w):
            p.fillRect(QRectF(px, y1, 0.008 * w, 0.06 * h), _cara_sombra(ROSA_MEDIO))
        _sombra_contacto(p, (x0 + x1) / 2, y1 + 0.062 * h, (x1 - x0) / 2 * 1.04, 0.008 * h)
        suelo_sombra = QPainterPath()
        suelo_sombra.addRect(QRectF(x0, y1 + 0.05 * h, x1 - x0, 0.012 * h))
        _sombra_proy(p, suelo_sombra, 0.006 * w, 0.004 * h)
        # cuerpo con cajones
        _caja(p, x0, y0, x1 - x0, y1 - y0, ROSA_MEDIO, lado=0.012 * w)
        p.fillPath(_poly([QPointF(x0, y0), QPointF(x1, y0), QPointF(x1 + 0.012 * w, y0 - 0.02 * h),
                          QPointF(x0 + 0.012 * w, y0 - 0.02 * h)]), QColor("#FFF0F5"))
        for k in range(2):
            ca = y0 + (y1 - y0) * (0.12 + 0.48 * k)
            cb = ca + (y1 - y0) * 0.40
            p.setPen(QPen(con_alfa(SOMBRA, 90), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(x0 + 0.010 * w, ca, x1 - x0 - 0.020 * w, cb - ca), 4, 4)
            p.setPen(Qt.NoPen)
            _elipse(p, (x0 + x1) / 2, (ca + cb) / 2, 0.006 * w, 0.006 * w, DORADO)
        # objetos sobre la mesa: frasco de perfume, tarro y corazoncito
        p.fillRect(QRectF(0.812 * w, 0.570 * h, 0.014 * w, 0.055 * h), _cara_luz(ROSA_SUAVE))
        p.fillRect(QRectF(0.815 * w, 0.556 * h, 0.008 * w, 0.014 * h), _cara_luz(DORADO))
        _elipse(p, 0.905 * w, 0.612 * h, 0.012 * w, 0.010 * h, CREMA)
        _cojin_corazon(p, 0.868 * w, 0.602 * h, 0.022 * h, ROSA)

        # espejo ovalado: marco dorado con brillo y cristal con reflejos
        marco = QPainterPath()
        marco.addEllipse(QPointF(cx, cy), rx, ry)
        gm = QLinearGradient(cx - rx, cy - ry, cx + rx, cy + ry)
        gm.setColorAt(0, _cara_luz(DORADO))
        gm.setColorAt(0.5, QColor(DORADO))
        gm.setColorAt(1, _cara_sombra(DORADO))
        p.fillPath(marco, gm)
        cristal = QPainterPath()
        cristal.addEllipse(QPointF(cx, cy), rx * 0.86, ry * 0.86)
        gc = QLinearGradient(cx - rx, cy - ry, cx + rx, cy + ry)
        gc.setColorAt(0, QColor(BLANCO))
        gc.setColorAt(0.5, QColor("#FFD6E2"))
        gc.setColorAt(1, QColor(ROSA_FRESA))
        p.fillPath(cristal, gc)
        p.save()
        p.setClipPath(cristal)
        p.fillPath(_poly([QPointF(cx - 0.45 * rx, cy - ry), QPointF(cx - 0.25 * rx, cy - ry),
                          QPointF(cx + 0.10 * rx, cy + ry), QPointF(cx - 0.10 * rx, cy + ry)]),
                   con_alfa(BLANCO, 110))
        p.fillPath(_poly([QPointF(cx + 0.10 * rx, cy - ry), QPointF(cx + 0.18 * rx, cy - ry),
                          QPointF(cx + 0.45 * rx, cy + ry), QPointF(cx + 0.36 * rx, cy + ry)]),
                   con_alfa(BLANCO, 70))
        p.restore()
        self.brillo(p, cx - 0.55 * rx, cy - 0.55 * ry, w * 0.035, BLANCO, alfa=120)
        # bombillas: discos crema con brillo (la intensidad viva va en cada cuadro)
        for fx, fy in _posiciones_bombillas():
            _elipse(p, fx * w, fy * h, 0.007 * w, 0.007 * w, CREMA)

    def _guirnalda(self, p, w, h):
        p0 = (0.255 * w, 0.245 * h)
        p1 = (0.50 * w, 0.41 * h)
        p2 = (0.745 * w, 0.245 * h)
        cuerda = QPainterPath(QPointF(*p0))
        cuerda.quadTo(QPointF(*p1), QPointF(*p2))
        p.setPen(QPen(con_alfa(SOMBRA, 150), 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(cuerda)
        p.setPen(Qt.NoPen)
        colores = (ROSA_MEDIO, ROSA_SUAVE, CREMA, DORADO, ROSA_FRESA)
        n = 16
        for i in range(n):
            t = (i + 0.5) / n
            bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
            dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
            dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
            longitud = math.hypot(dx, dy)
            ux, uy = dx / longitud, dy / longitud
            nx, ny = -uy, ux
            if ny < 0:
                nx, ny = -nx, -ny
            ancho_b = 0.011 * w
            alto_b = 0.035 * h
            bandera = _poly([QPointF(bx - ux * ancho_b, by - uy * ancho_b),
                             QPointF(bx + ux * ancho_b, by + uy * ancho_b),
                             QPointF(bx + nx * alto_b, by + ny * alto_b)])
            p.fillPath(bandera, con_alfa(colores[i % len(colores)], 235))

    def _rayos(self, p, w, h):
        """Rayos de luz diagonales que entran por la ventana (degradado blanco alfa 40 -> 0)."""
        p.save()
        for puntos, alfa in RAYOS:
            g = QLinearGradient(0, 0.62 * h, 0, h)
            g.setColorAt(0, con_alfa(BLANCO, alfa))
            g.setColorAt(1, con_alfa(BLANCO, 0))
            camino = _poly([QPointF(x * w, y * h) for x, y in puntos])
            p.fillPath(camino, g)
        self.brillo(p, 0.55 * w, 0.95 * h, w * 0.16, BLANCO, alfa=40)
        p.restore()

    def _vineta(self, p, w, h):
        g = QRadialGradient(QPointF(w / 2, h / 2), max(w, h) * 0.72)
        g.setColorAt(0.38, con_alfa(VINETA, 0))
        g.setColorAt(1, con_alfa(VINETA, 70))
        p.fillRect(QRectF(0, 0, w, h), g)

    def _grano(self, p, w, h, r):
        puntos = QPolygonF([QPointF(r.uniform(0, w), r.uniform(0, h)) for _ in range(5000)])
        p.setPen(QPen(con_alfa(GRANO, 6), 1.6, Qt.SolidLine, Qt.RoundCap))
        p.drawPoints(puntos)

    # ------------------------------------------------------------ cada cuadro

    def pintar_animado(self, p, w, h, t):
        p.setPen(Qt.NoPen)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self._tul(p, w, h, t)
        self._motas_luz(p, w, h, t)
        self._flotar(p, w, h, t)
        self._bombillas_vivas(p, w, h, t)
        self._destellos_pintar(p, w, h, t)
        self.ondas(p, base_y=0.985 * h, ancho=w, alto_max=0.07 * h, color=self.acento(), reflejo=False)

    def _tul(self, p, w, h, t):
        """Tul de las cortinas: franjas verticales con degradados alternos blanco alfa 60-110 que ondean."""
        y0, y1 = 0.27 * h, 0.622 * h
        pliegues = 4
        for ci, (c0, c1) in enumerate(CORTINAS):
            x0, x1 = c0 * w, c1 * w
            ancho = (x1 - x0) / pliegues
            for k in range(pliegues):
                xl = x0 + k * ancho
                xr = xl + ancho
                d = 0.004 * w * math.sin(t * 0.9 + k * 0.8 + ci * 1.7)
                d2 = d * 1.6
                camino = _poly([QPointF(xl + d, y0), QPointF(xr + d, y0),
                                QPointF(xr + d2, y1), QPointF(xl + d2, y1)])
                g = QLinearGradient(xl + d, 0, xr + d, 0)
                a_bordes, a_centro = (60, 110) if k % 2 == 0 else (110, 60)
                g.setColorAt(0, con_alfa(BLANCO, a_bordes))
                g.setColorAt(0.5, con_alfa(BLANCO, a_centro))
                g.setColorAt(1, con_alfa(BLANCO, a_bordes))
                p.fillPath(camino, g)

    def _motas_luz(self, p, w, h, t):
        (sx0, sy0), (sx1, sy1) = EJE_RAYO
        for s0, lat, radio, alfa, fase, vel in self._motas:
            s = (s0 + t * vel * 0.02) % 1.0
            ancho = 0.08 + 0.10 * s
            x = sx0 + (sx1 - sx0) * s + lat * ancho / 2
            y = sy0 + (sy1 - sy0) * s
            a = alfa * (0.6 + 0.4 * math.sin(t * 2.0 + fase))
            rr = radio * h
            p.setBrush(con_alfa(BLANCO, a))
            p.drawEllipse(QPointF(x * w, y * h), rr, rr)

    def _flotar(self, p, w, h, t):
        p.save()
        for x0, y0, tam, vel, fase, clave, alfa in self._flotantes:
            y = (y0 - t * vel) % 1.0
            x = x0 + 0.02 * math.sin(t * 0.35 + fase)
            ang = 20 * math.sin(t * 0.6 + fase)
            s = tam * h
            pm = self._sprites[clave]
            p.save()
            p.setOpacity(alfa / 255)
            p.translate(x * w, y * h)
            p.rotate(ang)
            p.drawPixmap(QRectF(-s / 2, -s / 2, s, s), pm, QRectF(pm.rect()))
            p.restore()
        p.restore()

    def _bombillas_vivas(self, p, w, h, t):
        e = min(1.0, self.energia() * 1.6)
        for fx, fy in self._bombillas:
            a = 90 + 150 * e * (0.8 + 0.2 * math.sin(t * 3 + fx * 10))
            self.brillo(p, fx * w, fy * h, 0.022 * w, CREMA, alfa=int(a))

    def _destellos_pintar(self, p, w, h, t):
        pm = self._pm_estrella
        for fx, fy, tam, fase, periodo in self._destellos:
            f = ((t + fase) / periodo) % 1.0
            alfa = 255 * math.sin(math.pi * f) ** 2
            if alfa < 6:
                continue
            s = 2 * tam * h
            p.save()
            p.setOpacity(alfa / 255)
            p.drawPixmap(QRectF(fx * w - s / 2, fy * h - s / 2, s, s), pm, QRectF(pm.rect()))
            p.restore()
