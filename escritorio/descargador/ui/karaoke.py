# -*- coding: utf-8 -*-
"""Modo karaoke y letras a pantalla completa (donadores).

Reusa el lienzo de la letra viva (`letra_viva.LienzoLetra`): la línea que se canta se ve enorme y se va llenando
fila por fila al ritmo de la voz, con la traducción y el salto con un clic. Aquí se le da:

- una letra más grande (hasta 88 px) y el fondo de la carátula con los colores que siguen a la carátula;
- la mascota «cantando»: se mece al ritmo, abre y cierra la boca (cambia de cuadro) mientras hay voz y suelta
  notas musicales; en un tramo instrumental solo se balancea suave y mientras la música está en pausa descansa.

Gasta poco: los relojes son hijos de la vista (el modo gamer en ahorro los detiene), el lienzo ya baja de 60 a
~7 cuadros por segundo cuando nada se mueve, y la mascota solo repinta ~7 veces por segundo.
"""

import math
import time

import shiboken6
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QPushButton, QWidget

from .. import mascotas
from ..paleta_caratula import colores_de
from .componentes import a_la_vista
from .letra_viva import FPS_DORMIDO, LienzoLetra, paleta_de
from .vista_grande import BOTON, VistaGrande, ahorrando

MS_MASCOTA = 140
LADO_MASCOTA = 230
NOTAS = ("♪", "♫", "♬")


def mascota_para(ctx):
    """La mascota que canta: la que eligió la cuenta o, si no tiene, una por defecto (capibara si existe)."""
    gestor = getattr(ctx, "mascota", None)
    datos = gestor.datos() if gestor is not None else None
    if datos:
        return datos
    try:
        lista = mascotas.catalogo_de(ctx)
    except Exception:  # noqa: BLE001
        return None
    for m in lista:
        if m.get("clave") == "capibara":
            return m
    return lista[0] if lista else None


class LienzoKaraoke(LienzoLetra):
    """La letra viva, en grande y con los colores de la carátula."""

    def __init__(self, ctx, colores, padre=None):
        self.colores = colores
        self._paleta_cover = paleta_de(None)
        super().__init__(ctx, compacto=False, padre=padre)
        colores.cambio.connect(self._colores_cambiaron)

    def _tam(self):
        return max(40, min(88, self.width() / 15))

    def _portada(self, img):
        super()._portada(img)
        self._paleta_cover = list(self.paleta)
        self._aplicar_paleta()

    def _aplicar_paleta(self):
        self.paleta = self.colores.colores(base=self._paleta_cover)

    def _colores_cambiaron(self):
        self._aplicar_paleta()
        if self.isVisible() and not self.reloj.isActive():
            self.update()

    def _cuadro(self):
        if ahorrando(self.ctx):
            # con un juego a pantalla completa no se anima nada: el lienzo solo espera
            self._ultimo_cuadro = time.monotonic()
            if self.reloj.interval() != FPS_DORMIDO:
                self.reloj.start(FPS_DORMIDO)
            return
        super()._cuadro()


class MascotaCantante(QWidget):
    """La mascota de la cuenta cantando junto a la letra."""

    def __init__(self, ctx, lienzo, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.lienzo = lienzo
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(LADO_MASCOTA, LADO_MASCOTA)
        self.datos = None
        self.cuadro = 0
        self.fase = 0.0
        self.estado = "descansa"                 # canta | tararea | descansa
        self._t = time.monotonic()
        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self._tic)
        self.reloj.setInterval(MS_MASCOTA)
        # método ligado (no lambda): Qt lo desconecta solo cuando la mascota se destruye
        self.ctx.reproductor.estado_cambio.connect(self._al_estado_reproductor)

    def _al_estado_reproductor(self, _e=None):
        if shiboken6.isValid(self):
            self._actualizar_estado()

    def calcular_estado(self):
        """canta (hay voz ahora), tararea (tramo sin letra) o descansa (en pausa o sin música)."""
        if getattr(self.ctx.reproductor, "estado", "") != "sonando":
            return "descansa"
        lc = self.lienzo
        if lc.lineas and lc.sincronizada:
            i = lc._actual
            if 0 <= i < len(lc.lineas) and not lc.lineas[i]["pausa"]:
                return "canta"
            return "tararea"
        return "canta" if lc.lineas else "tararea"

    def _actualizar_estado(self):
        self.estado = self.calcular_estado()
        if self.isVisible() and self.estado != "descansa" and not ahorrando(self.ctx):
            if not self.reloj.isActive():
                self.reloj.start()
        elif self.estado == "descansa":
            self.reloj.stop()
            self.cuadro = 0
            self.update()

    def showEvent(self, e):
        super().showEvent(e)
        d = mascota_para(self.ctx)
        # sin estelas ni arcoíris: solo la mascota (el rastro suelto parecía un artefacto)
        self.datos = dict(d, estela=None, arcoiris=False) if d else None
        self._actualizar_estado()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.reloj.stop()

    def _tic(self):
        if ahorrando(self.ctx) or not a_la_vista(self):
            if self.reloj.interval() != 1000:
                self.reloj.setInterval(1000)
            return
        if self.reloj.interval() != MS_MASCOTA:
            self.reloj.setInterval(MS_MASCOTA)
        self.estado = self.calcular_estado()
        if self.estado == "descansa":
            self.reloj.stop()
            self.cuadro = 0
            self.update()
            return
        if self.estado == "canta":
            self.cuadro += 1                       # abre y cierra la boca (cambia de cuadro)
        self.fase += 0.9
        self.update()

    def paintEvent(self, _e):
        if not self.datos:
            return
        p = QPainter(self)
        t = time.monotonic()
        ritmo = 7.0 if self.estado == "canta" else 2.4
        rebote = abs(math.sin(t * ritmo)) * (9 if self.estado == "canta" else 3) if self.estado != "descansa" else 0
        esc = max(1, round((LADO_MASCOTA * 0.62) / max(1, self.datos["alto"])))
        w = self.datos["ancho"] * esc
        from ..cumpleanos import ESTADO as _cumple
        mascotas.pintar(p, self.datos, self.width() / 2, self.height() - 12 - rebote, 0, self.width(),
                        self.cuadro, self.fase, esc, gorro=_cumple.es_mio_hoy)
        if self.estado == "canta":
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.TextAntialiasing, True)
            f = QFont("Segoe UI")
            f.setPixelSize(30)
            f.setWeight(QFont.Black)
            p.setFont(f)
            for k in range(3):
                vida = ((t * 0.55) + k / 3.0) % 1.0
                x = self.width() / 2 + w * 0.30 + math.sin(vida * 6.0 + k * 2.0) * 12 + k * 6
                y = self.height() * 0.46 - vida * (self.height() * 0.42)
                color = QColor(255, 255, 255, int(235 * (1.0 - vida) ** 0.8))
                p.setPen(color)
                p.drawText(QRectF(x - 20, y - 20, 40, 40), Qt.AlignCenter, NOTAS[k % 3])
        p.end()


class PaginaKaraoke(VistaGrande):
    titulo = "Karaoke"

    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.colores = colores_de(ctx)
        self.lienzo = LienzoKaraoke(ctx, self.colores, self)
        self.lienzo.margen_arriba = 64
        self.lienzo.margen_abajo = 130        # la letra termina (y se desvanece) sobre la franja de controles
        self.lienzo.installEventFilter(self)
        self.lienzo.setMouseTracking(True)
        self.lienzo.lower()
        self.mascota = MascotaCantante(ctx, self.lienzo, self)
        self.bt_traducir = QPushButton("Traducir")
        self.bt_traducir.setCheckable(True)
        self.bt_traducir.setChecked(bool(ctx.ajustes["traducir_letra"]))
        self.bt_traducir.setToolTip("Mostrar la traducción bajo cada línea")
        self.bt_traducir.setCursor(Qt.PointingHandCursor)
        self.bt_traducir.setStyleSheet(BOTON)
        self.bt_traducir.setFocusPolicy(Qt.NoFocus)
        self.bt_traducir.toggled.connect(self._traducir)
        self.fila_cab.insertWidget(1, self.bt_traducir, 0, Qt.AlignVCenter)
        # la misma letra, solo el verso que suena y con efectos (letra_escena.py)
        self.bt_efectos = QPushButton("Con efectos")
        self.bt_efectos.setToolTip("Solo el verso que suena, en grande y con animaciones (Ctrl+Shift+Y)")
        self.bt_efectos.setCursor(Qt.PointingHandCursor)
        self.bt_efectos.setStyleSheet(BOTON)
        self.bt_efectos.setFocusPolicy(Qt.NoFocus)
        self.bt_efectos.clicked.connect(self._abrir_efectos)
        self.fila_cab.insertWidget(2, self.bt_efectos, 0, Qt.AlignVCenter)
        # el estado de la mascota sigue a la letra (cada línea nueva cambia entre cantar y tararear)
        # método ligado (no lambda): al destruirse la página Qt lo desconecta solo y no se llama
        # sobre un objeto ya borrado («Internal C++ object (PaginaKaraoke) already deleted»)
        self.r.posicion_cambio.connect(self._al_posicion)

    def _al_posicion(self, _s=None):
        if not shiboken6.isValid(self) or not shiboken6.isValid(self.mascota):
            return
        if self.isVisible():
            self.mascota._actualizar_estado()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.lienzo.setGeometry(0, 0, self.width(), self.height())
        self.lienzo.lower()
        self.mascota.move(self.width() - LADO_MASCOTA - 18, self.height() - LADO_MASCOTA - 96)
        self.mascota.raise_()
        self.cabecera.raise_()
        self.pie.raise_()

    def _abrir_efectos(self):
        v = getattr(self.ctx, "ventana", None)
        if v is not None and hasattr(v, "abrir_escena"):
            v.abrir_escena()

    def _traducir(self, on):
        self.ctx.ajustes["traducir_letra"] = bool(on)
        try:
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        self.lienzo.pedir_traduccion()
