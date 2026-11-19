# -*- coding: utf-8 -*-
"""Marcos animados para la foto de perfil y efectos para el nombre (lo premium que se ve).

Todo es muy ligero, pensado para equipos viejos:
  * UN solo temporizador para toda la aplicación (RelojPremium), a 30 cuadros por segundo como mucho.
  * Solo se repinta el rectángulo del propio avatar o nombre; nada de desenfoques por cuadro.
  * El reloj duerme solo: sin avatares animados a la vista, con la ventana minimizada o sin foco, no corre.
  * En pantallas con muchos avatares (listas largas) los marcos se quedan quietos, salvo los que se
    piden «siempre» (el perfil que estás mirando).

El dibujo es el mismo en cualquier sitio: `pintar_marco` para el anillo y `NombreEfecto` para el texto.
"""

import time

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFontMetricsF, QGradient, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import QApplication, QLabel

from ..premium_datos import NINGUNO, efecto_valido, marco_valido
from .estilos import C

# marco -> (colores del degradado cónico, vueltas por segundo, ¿lleva un destello fino por dentro?)
MARCO_ESTILO = {
    "aurora": (("#34D399", "#22D3EE", "#A78BFA", "#34D399"), 0.16, False),
    "fuego": (("#F97316", "#EF4444", "#FBBF24", "#F97316"), 0.30, True),
    "oro": (("#FDE68A", "#F59E0B", "#B45309", "#FDE68A"), 0.12, True),
    "neon": (("#22D3EE", "#F0ABFC", "#22D3EE"), 0.24, True),
    "hielo": (("#E0F2FE", "#7DD3FC", "#BAE6FD", "#E0F2FE"), 0.10, False),
    "arcoiris": (("#EF4444", "#F59E0B", "#FDE047", "#34D399", "#38BDF8", "#8B5CF6", "#EF4444"), 0.22, False),
    "galaxia": (("#312E81", "#7C3AED", "#EC4899", "#1E1B4B", "#312E81"), 0.14, True),
}
ANGULO_QUIETO = 35.0            # donde se queda un marco que no se anima
FPS = 30
MAX_ANIMADOS = 6                # más avatares que estos a la vista y los marcos se quedan quietos


class RelojPremium(QObject):
    """El único temporizador de los marcos y efectos animados."""

    def __init__(self):
        super().__init__()
        self._vivos = []
        self.t = 0.0                # segundos desde que se creó (para animar)
        self._cero = time.monotonic()
        self.tics = 0
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / FPS))
        self._timer.timeout.connect(self.tic)

    def registrar(self, w):
        if w not in self._vivos:
            self._vivos.append(w)
        self._arrancar_o_parar()

    def quitar(self, w):
        if w in self._vivos:
            self._vivos.remove(w)
        self._arrancar_o_parar()

    def _arrancar_o_parar(self):
        if self._vivos and not self._timer.isActive():
            self._timer.start()
        elif not self._vivos and self._timer.isActive():
            self._timer.stop()

    @property
    def activo(self):
        return self._timer.isActive()

    def cuantos(self):
        return len(self._vivos)

    def se_anima(self, w):
        """¿Este widget se mueve? Los «siempre» sí; los demás solo si no hay demasiados a la vista."""
        if getattr(w, "siempre", False):
            return True
        sueltos = sum(1 for x in self._vivos if not getattr(x, "siempre", False))
        return sueltos <= MAX_ANIMADOS

    def angulo(self, w, vueltas):
        if not self.se_anima(w):
            return ANGULO_QUIETO
        return (ANGULO_QUIETO + self.t * vueltas * 360.0) % 360.0

    def tic(self):
        app = QApplication.instance()
        # ventana minimizada, otra aplicación al frente o pantalla bloqueada: no se gasta nada
        if app is not None and app.applicationState() != Qt.ApplicationActive:
            return
        self.t = time.monotonic() - self._cero
        self.tics += 1
        for w in list(self._vivos):
            try:
                if w.isVisible() and not w.window().isMinimized() and self.se_anima(w):
                    w.update()
            except RuntimeError:        # el widget ya no existe
                self.quitar(w)


_RELOJ = None


def reloj():
    global _RELOJ
    if _RELOJ is None:
        _RELOJ = RelojPremium()
    return _RELOJ


# ------------------------------------------------------------------ marcos

def ancho_marco(lado):
    """Grosor del anillo según el tamaño de la foto (fino en las listas, grueso en el perfil)."""
    return max(3.0, round(lado * 0.075))


def pintar_marco(p, rect, marco, angulo=ANGULO_QUIETO, ancho=4.0):
    """Dibuja el anillo del marco en el borde de `rect` (un círculo). No hace nada con «ninguno»."""
    marco = marco_valido(marco)
    if marco == NINGUNO:
        return
    colores, _v, destello = MARCO_ESTILO[marco]
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    g = QConicalGradient(rect.center(), angulo)
    n = len(colores) - 1
    for i, c in enumerate(colores):
        g.setColorAt(i / n if n else 0.0, QColor(c))
    pluma = QPen(QBrush(g), ancho)
    pluma.setCapStyle(Qt.FlatCap)
    p.setPen(pluma)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(rect.adjusted(ancho / 2, ancho / 2, -ancho / 2, -ancho / 2))
    if destello and ancho >= 4:
        # un filo claro por dentro del anillo: lo separa de la foto y le da brillo sin desenfocar nada
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawEllipse(rect.adjusted(ancho, ancho, -ancho, -ancho))
    p.restore()


# ------------------------------------------------------------------ nombre con efecto

COLORES_DEGRADADO = ("#60A5FA", "#A78BFA", "#F472B6")
COLORES_ARCOIRIS = ("#F87171", "#FBBF24", "#A3E635", "#34D399", "#38BDF8", "#A78BFA", "#F472B6", "#F87171")
COLOR_NEON = "#7DF9FF"
COLOR_NEON_HALO = "#22D3EE"


def _gradiente_texto(efecto, x0, ancho, t, animar):
    """El degradado con el que se pinta el nombre. `t` mueve el destello o el arcoíris."""
    ancho = max(1.0, ancho)
    if efecto == "degradado":
        g = QLinearGradient(x0, 0, x0 + ancho, 0)
        for i, c in enumerate(COLORES_DEGRADADO):
            g.setColorAt(i / (len(COLORES_DEGRADADO) - 1), QColor(c))
        return g
    if efecto == "arcoiris":
        g = QLinearGradient(x0, 0, x0 + ancho, 0)
        g.setSpread(QGradient.RepeatSpread)
        desfase = (t * 0.25) % 1.0 if animar else 0.0
        g.setStart(QPointF(x0 - desfase * ancho, 0))
        g.setFinalStop(QPointF(x0 - desfase * ancho + ancho, 0))
        for i, c in enumerate(COLORES_ARCOIRIS):
            g.setColorAt(i / (len(COLORES_ARCOIRIS) - 1), QColor(c))
        return g
    # brillo: el color normal con una franja clara que lo recorre
    base = QColor(C["texto"])
    g = QLinearGradient(x0, 0, x0 + ancho, 0)
    g.setSpread(QGradient.RepeatSpread)
    desfase = ((t * 0.35) % 1.6) - 0.3 if animar else 0.35
    g.setStart(QPointF(x0, 0))
    g.setFinalStop(QPointF(x0 + ancho, 0))
    claro = QColor("#FFF3B0")
    g.setColorAt(0.0, base)
    g.setColorAt(max(0.0, min(1.0, desfase - 0.18)), base)
    g.setColorAt(max(0.0, min(1.0, desfase)), claro)
    g.setColorAt(max(0.0, min(1.0, desfase + 0.18)), base)
    g.setColorAt(1.0, base)
    return g


class NombreEfecto(QLabel):
    """Un nombre con efecto (brillo, degradado, arcoíris o neón). Con «ninguno» es un QLabel normal."""

    def __init__(self, texto="", efecto=NINGUNO, estilo="", ajustar=False, siempre=False, padre=None):
        super().__init__(texto, padre)
        self.efecto = efecto_valido(efecto)
        self.siempre = siempre
        self.setWordWrap(ajustar)
        self.setStyleSheet("background:transparent;" + estilo)

    def set_efecto(self, efecto):
        efecto = efecto_valido(efecto)
        if efecto == self.efecto:
            return
        self.efecto = efecto
        self._sincronizar_reloj()
        self.update()

    def _anima(self):
        return self.efecto in ("brillo", "arcoiris")

    def _sincronizar_reloj(self):
        if self._anima() and self.isVisible():
            reloj().registrar(self)
        else:
            reloj().quitar(self)

    def showEvent(self, e):
        super().showEvent(e)
        self._sincronizar_reloj()

    def hideEvent(self, e):
        super().hideEvent(e)
        reloj().quitar(self)

    def paintEvent(self, e):
        if self.efecto == NINGUNO:
            return super().paintEvent(e)
        texto = self.text()
        if not texto:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setFont(self.font())
        r = QRectF(self.contentsRect())
        fm = QFontMetricsF(self.font())
        animar = self._anima() and reloj().se_anima(self)
        t = reloj().t
        if self.wordWrap():
            ancho = r.width()
            p.setPen(QPen(QBrush(_gradiente_texto(self.efecto, r.left(), ancho, t, animar)), 1))
            p.drawText(r, int(self.alignment()) | Qt.TextWordWrap, texto)
            return
        corto = fm.elidedText(texto, Qt.ElideRight, r.width())
        ancho_texto = fm.horizontalAdvance(corto)
        x = r.left()
        al = self.alignment()
        if al & Qt.AlignHCenter:
            x = r.left() + (r.width() - ancho_texto) / 2
        elif al & Qt.AlignRight:
            x = r.right() - ancho_texto
        y = r.top() + (r.height() - fm.height()) / 2 + fm.ascent()
        if self.efecto == "neon":
            ruta = QPainterPath()
            ruta.addText(QPointF(x, y), self.font(), corto)
            for grosor, alfa in ((7, 28), (4, 55), (2, 90)):
                halo = QColor(COLOR_NEON_HALO)
                halo.setAlpha(alfa)
                p.strokePath(ruta, QPen(halo, grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.fillPath(ruta, QColor(COLOR_NEON))
            return
        p.setPen(QPen(QBrush(_gradiente_texto(self.efecto, x, ancho_texto, t, animar)), 1))
        p.drawText(QPointF(x, y), corto)


def nombre_efecto(texto, estilo="", efecto=NINGUNO, ajustar=True, siempre=False):
    """Una etiqueta de nombre: la de siempre sin efecto, o la animada con él. Mismo estilo CSS en ambas."""
    efecto = efecto_valido(efecto)
    if efecto == NINGUNO:
        et = QLabel(texto)
        et.setWordWrap(ajustar)
        et.setStyleSheet("background:transparent;" + estilo)
        return et
    return NombreEfecto(texto, efecto, estilo, ajustar, siempre)
