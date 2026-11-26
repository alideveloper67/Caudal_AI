# -*- coding: utf-8 -*-
"""«Diseño de letra»: elegir el tipo de letra y el estilo con que se ven las letras de las canciones.

Cada tipo de letra se muestra escrito en su propia letra y cada estilo pintado de verdad. Al tocar uno se
aplica al momento en la Escena de escritorio, en la letra de la canción (página y panel) y en el karaoke, y
queda guardado (ajustes «fuente_letra» y «estilo_letra»).

Las letras épicas (ajuste «letra_epica», ui/epica) son de la Escena de escritorio: se montan como un edit y se
enseñan en movimiento. Con una puesta, la escena usa esa en vez del estilo.

`abrir_selector(ctx, padre)` abre la ventana; `SelectorLetra` y `VistaPreviaLetra` también valen sueltos."""

import math
import threading
import time
import weakref

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QFontMetricsF, QGuiApplication, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from . import epica, estilo_letra, presentacion_letra, tipografia_letra
from .componentes import a_la_vista
from .estilos import C

TEXTO_VISTA = "Corazón, ¿dónde estás?"
TEXTO_ESTILO = "Canción"
COLORES = ("#E8577E", "#7C5CFF", "#FFB03A")       # si no suena nada con carátula


def colores_de_muestra(ctx):
    """Los colores de la carátula que suena (los mismos que usará la letra) o unos de muestra."""
    cc = getattr(ctx, "colores_caratula", None)
    if cc is not None:
        try:
            lista = [QColor(c) for c in cc.colores()][:3]
            if len(lista) == 3 and all(c.isValid() for c in lista):
                return estilo_letra.Colores(*lista)
        except Exception:  # noqa: BLE001
            pass
    return estilo_letra.Colores(*COLORES)


def fuente_muestra(clave, px):
    """La fuente de una muestra: la elegida o, con la predeterminada, la de siempre."""
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, int(px)))
    f.setWeight(QFont.ExtraBold)
    f.setLetterSpacing(QFont.PercentageSpacing, 98)
    return tipografia_letra.adaptar(f, clave)


def fuente_que_cabe(clave, texto, ancho, alto, maximo):
    """La mayor fuente (hasta `maximo` px) con la que el texto cabe en ancho x alto."""
    px = maximo
    while px > 9:
        f = fuente_muestra(clave, px)
        fm = QFontMetricsF(f)
        caja = fm.tightBoundingRect(texto)
        if max(fm.horizontalAdvance(texto), caja.width()) <= ancho and caja.height() <= alto:
            return f
        px -= 1
    return fuente_muestra(clave, px)


def _fondo_muestra(p, rect, colores, radio):
    """Un fondo como el de la letra de la canción: los colores de la carátula, oscurecidos."""
    camino = QPainterPath()
    camino.addRoundedRect(rect, radio, radio)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0.0, QColor(colores.a).darker(330))
    g.setColorAt(1.0, QColor(colores.c).darker(420))
    p.fillPath(camino, g)
    r = QRadialGradient(rect.center().x() + rect.width() * 0.2, rect.top(), rect.width() * 0.7)
    brillo = QColor(colores.b)
    brillo.setAlpha(60)
    r.setColorAt(0.0, brillo)
    brillo.setAlpha(0)
    r.setColorAt(1.0, brillo)
    p.fillPath(camino, r)


def _pintar_centrado(p, rect, texto, f, estilo, colores, progreso, dpr):
    """El texto con su estilo, centrado por lo que de verdad ocupa (no por lo que declara la fuente)."""
    caja = QFontMetricsF(f).tightBoundingRect(texto)
    x = rect.center().x() - caja.width() / 2 - caja.left()
    linea = rect.center().y() - caja.height() / 2 - caja.top()
    estilo_letra.pintar_muestra(p, round(x), round(linea), texto, f, estilo, colores, progreso, dpr)


class VistaPreviaLetra(QWidget):
    """Así se ve tu letra: un verso con la tipografía y el estilo puestos, a medio cantar."""

    VERSOS = ("Corazón", "¿dónde estás?", "No me dejes caer", "en la oscuridad")
    CICLO = 7.0

    def __init__(self, ctx, padre=None, alto=120, texto=TEXTO_VISTA, con_epica=False):
        super().__init__(padre)
        self.ctx = ctx
        self.texto = texto
        self.con_epica = con_epica
        self._montaje = None
        self._t0 = time.monotonic()
        self._pm = None
        self.setMinimumHeight(alto)
        self.setMaximumHeight(alto)
        self.setAccessibleName("Vista previa de la letra")
        tipografia_letra.suscribir(self)
        estilo_letra.suscribir(self)
        epica.suscribir(self)

    def al_cambiar_tipografia(self):
        self._pm = None
        self._montaje = None
        self.update()

    al_cambiar_estilo_letra = al_cambiar_tipografia

    def al_cambiar_letra_epica(self):
        self._t0 = time.monotonic()
        self.al_cambiar_tipografia()

    def en_movimiento(self):
        return self.con_epica and bool(epica.actual())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._pm = None

    def showEvent(self, e):
        super().showEvent(e)
        self._pm = None                 # los colores de la carátula pueden ser otros

    def paintEvent(self, _e):
        dpr = self.devicePixelRatioF() or 1.0
        if self.en_movimiento():
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height())
            colores = colores_de_muestra(self.ctx)
            _fondo_muestra(p, rect, colores, 14)
            if self._montaje is None or self._montaje.clave != epica.actual():
                self._montaje = montaje_de_muestra(epica.actual(), self.VERSOS, self.CICLO)
            camino = QPainterPath()
            camino.addRoundedRect(rect, 14, 14)
            p.setClipPath(camino)
            pintar_epica(p, rect, self._montaje, (time.monotonic() - self._t0) % self.CICLO, colores, dpr)
            p.end()
            return
        if self._pm is None or self._pm.devicePixelRatio() != dpr:
            pm = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            rect = QRectF(0, 0, self.width(), self.height())
            colores = colores_de_muestra(self.ctx)
            _fondo_muestra(p, rect, colores, 14)
            f = fuente_que_cabe(tipografia_letra.actual(), self.texto, rect.width() - 60, rect.height() - 44, 46)
            _pintar_centrado(p, rect, self.texto, f, estilo_letra.actual(), colores, 0.56, dpr)
            p.end()
            self._pm = pm
        p = QPainter(self)
        p.drawPixmap(0, 0, self._pm)
        p.end()


class _Turnos:
    """Las muestras se pintan por tandas cortas: el panel sale al momento y se va llenando, sin parar la música
    ni la escena que hay detrás (pintarlas todas de una vez la congelaba)."""

    TANDA_S = 0.010

    def __init__(self):
        self.cola = []
        self.reloj = None

    def pedir(self, muestra):
        if any(r() is muestra for r in self.cola):
            return
        self.cola.append(weakref.ref(muestra))
        if self.reloj is None:
            self.reloj = QTimer()
            self.reloj.setInterval(16)
            self.reloj.timeout.connect(self._tanda)
        self.reloj.start()

    def _tanda(self):
        fin = time.perf_counter() + self.TANDA_S
        esperan = []
        while self.cola:
            r = self.cola.pop(0)
            m = r()
            try:
                if m is None or not m.isVisible():
                    continue
                if not m.lista():
                    esperan.append(r)
                    continue
                m.construir()
                m.update()
            except RuntimeError:                  # ya destruida
                continue
            if time.perf_counter() >= fin:
                break
        self.cola += esperan
        if not self.cola:
            self.reloj.stop()


_turnos = _Turnos()


class _Muestra(QAbstractButton):
    """Una tarjeta que se puede elegir: la muestra arriba y su nombre abajo."""

    ALTO = 92

    def __init__(self, clave, nombre, ayuda, ctx, padre=None):
        super().__init__(padre)
        self.clave = clave
        self.nombre = nombre
        self.ctx = ctx
        self._pm = None
        self._ultima = None
        self._al_momento = False         # en movimiento bajo el ratón: se pinta ya
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover)
        self.setText(nombre)
        self.setAccessibleName(nombre)
        self.setToolTip(ayuda or nombre)
        self.setFixedHeight(self.ALTO)

    def sizeHint(self):
        return QSize(150, self.ALTO)

    def rehacer(self):
        self._pm = None
        self.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._pm = None

    def zona(self):
        """Donde va la muestra (encima del nombre)."""
        return QRectF(6, 6, self.width() - 12, self.height() - 34)

    def pintar_muestra(self, p, rect, dpr):
        raise NotImplementedError

    def lista(self):
        """¿Se puede pintar ya sin esperar al disco?"""
        return tipografia_letra.lista(tipografia_letra.actual())

    def construir(self):
        dpr = self.devicePixelRatioF() or 1.0
        pm = QPixmap(max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing)
        q.setRenderHint(QPainter.TextAntialiasing)
        q.setRenderHint(QPainter.SmoothPixmapTransform)
        self.pintar_muestra(q, self.zona(), dpr)
        q.end()
        self._pm = pm
        self._ultima = pm

    def paintEvent(self, _e):
        dpr = self.devicePixelRatioF() or 1.0
        if self._pm is None or self._pm.devicePixelRatio() != dpr:
            if self.isVisible() and not self._al_momento:
                _turnos.pedir(self)
            else:
                self.construir()
            self._al_momento = False
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(1, 1, -1, -1)
        puesta = self.isChecked()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"] if (puesta or self.underMouse()) else C["superficie2"]))
        p.drawRoundedRect(rect, 12, 12)
        pm = self._pm if self._pm is not None else self._ultima       # mientras llega la nueva, la de antes
        if pm is not None:
            p.drawPixmap(0, 0, pm)
        f = QFont("Segoe UI")
        f.setPixelSize(12)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(C["texto"] if puesta else C["texto2"]))
        pie = QRectF(8, self.height() - 27, self.width() - 16, 22)
        p.drawText(pie, Qt.AlignCenter, QFontMetrics(f).elidedText(self.nombre, Qt.ElideRight, int(pie.width())))
        p.setBrush(Qt.NoBrush)
        if puesta:
            p.setPen(QPen(QColor(C["acento"]), 2))
            p.drawRoundedRect(rect, 12, 12)
            # la marca de «puesto» no depende solo del color
            c = QRectF(self.width() - 25, 8, 17, 17)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["acento"]))
            p.drawEllipse(c)
            p.setPen(QPen(QColor(C["acento_texto"]), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            v = QPainterPath()
            v.moveTo(c.left() + 4.6, c.center().y() + 0.3)
            v.lineTo(c.left() + 7.4, c.center().y() + 3.0)
            v.lineTo(c.left() + 12.6, c.center().y() - 3.0)
            p.setBrush(Qt.NoBrush)
            p.drawPath(v)
        elif self.hasFocus():
            p.setPen(QPen(QColor(C["texto2"]), 1.4, Qt.DashLine))
            p.drawRoundedRect(rect, 12, 12)
        p.end()


class MuestraFuente(_Muestra):
    """Un tipo de letra, escrito en su propia letra."""

    def lista(self):
        return tipografia_letra.lista(self.clave)

    def pintar_muestra(self, p, rect, dpr):
        f = fuente_que_cabe(self.clave, self.nombre, rect.width() - 14, rect.height() - 12, 30)
        caja = QFontMetricsF(f).tightBoundingRect(self.nombre)
        t = estilo_letra.trazo_de(self.nombre, f, rect.center().x() - caja.width() / 2 - caja.left(),
                                  rect.center().y() - caja.height() / 2 - caja.top())
        p.fillPath(t, QColor(C["texto"]))


class MuestraEstilo(_Muestra):
    """Un estilo, pintado de verdad con la tipografía puesta."""

    ALTO = 108

    def pintar_muestra(self, p, rect, dpr):
        colores = colores_de_muestra(self.ctx)
        _fondo_muestra(p, rect, colores, 8)
        f = fuente_que_cabe(tipografia_letra.actual(), TEXTO_ESTILO, rect.width() - 26, rect.height() - 26, 32)
        p.save()
        camino = QPainterPath()
        camino.addRoundedRect(rect, 8, 8)
        p.setClipPath(camino)
        _pintar_centrado(p, rect, TEXTO_ESTILO, f, self.clave, colores, 0.58, dpr)
        p.restore()


class MuestraEpica(_Muestra):
    """Una letra épica, en movimiento mientras se tiene el ratón encima."""

    ALTO = 124
    CICLO = 2.5                # segundos de la muestra
    QUIETA = 0.85              # el instante que se ve cuando está parada

    def __init__(self, clave, nombre, ayuda, ctx, padre=None):
        super().__init__(clave, nombre, ayuda, ctx, padre)
        self._montaje = None
        self._t0 = time.monotonic()

    def rehacer(self):
        self._montaje = None
        super().rehacer()

    def paso(self):
        """Un cuadro de la muestra (lo pide el reloj del selector)."""
        if self.isVisible() and self._ultima is None:
            return                       # aún no le tocó pintarse por primera vez
        self._pm = None
        self._al_momento = True
        self.update()

    def enterEvent(self, e):
        super().enterEvent(e)
        self._t0 = time.monotonic()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._pm = None

    def pintar_muestra(self, p, rect, dpr):
        colores = colores_de_muestra(self.ctx)
        _fondo_muestra(p, rect, colores, 8)
        camino = QPainterPath()
        camino.addRoundedRect(rect, 8, 8)
        p.setClipPath(camino)
        if not self.clave:
            mov = getattr(self, "mov", None)
            if mov:
                t = (time.monotonic() - self._t0) % self.CICLO if self.underMouse() else self.CICLO * 0.92
                pres = getattr(self, "pres", None) or {}
                pintar_movimiento(p, rect, mov, t, colores, pres.get("original", False), pres.get("acabado"))
                return
            f = fuente_que_cabe(tipografia_letra.actual(), TEXTO_ESTILO, rect.width() - 26, rect.height() - 30, 32)
            _pintar_centrado(p, rect, TEXTO_ESTILO, f, estilo_letra.actual(), colores, 0.58, dpr)
            return
        t = (time.monotonic() - self._t0) % self.CICLO if self.underMouse() else self.QUIETA
        if self._montaje is None:
            self._montaje = montaje_de_muestra(self.clave, (TEXTO_ESTILO,), self.CICLO)
        pintar_epica(p, rect, self._montaje, t, colores, dpr)


PALABRAS_MUESTRA = ("Tu", "voz", "me", "guía")


def pintar_movimiento(p, rect, mov, t, colores, original=False, acabado=None):
    """La letra clásica entrando palabra a palabra con su movimiento (en pequeño, para enseñarlo).
    `original`: con su letra propia (estrecha, en cursiva) y la palabra fuerte en mayúsculas, rellena."""
    if original:
        from .escena.estilo import fuente_impacto
        f = fuente_impacto(26)
        fm0 = QFontMetricsF(f)
        ancho = sum(fm0.horizontalAdvance(w) for w in PALABRAS_MUESTRA) + fm0.horizontalAdvance(" ") * 3
        f = fuente_impacto(max(10, int(26 * min(1.0, (rect.width() - 30) / max(1.0, ancho)))))
    else:
        f = fuente_que_cabe(tipografia_letra.actual(), " ".join(PALABRAS_MUESTRA), rect.width() - 30,
                            rect.height() - 34, 30)
    fm = QFontMetricsF(f)
    espacio = fm.horizontalAdvance(" ")
    anchos = [fm.horizontalAdvance(w) for w in PALABRAS_MUESTRA]
    x = rect.center().x() - (sum(anchos) + espacio * (len(anchos) - 1)) / 2
    base = rect.center().y() + fm.ascent() / 2 - fm.descent() / 2
    tam = f.pixelSize() or 24
    llegadas = [0.25 + i * 0.38 for i in range(len(PALABRAS_MUESTRA))]
    ultima = max((i for i, a in enumerate(llegadas) if t >= a), default=-1)
    latido = 1.0 + (0.03 * abs(math.sin(t * math.pi * 2.0)) if mov == "latido" else 0.0)
    p.save()
    p.translate(rect.center())
    p.scale(latido, latido)
    p.translate(-rect.center())
    palabras = [w.upper() if original and i == 1 else w for i, w in enumerate(PALABRAS_MUESTRA)]
    if original:
        anchos = [fm.horizontalAdvance(w) for w in palabras]
        x = rect.center().x() - (sum(anchos) + espacio * (len(anchos) - 1)) / 2
    for i, w in enumerate(palabras):
        x0, x = x, x + anchos[i] + espacio
        u = (t - llegadas[i]) / 0.40
        if u < 0:
            continue
        e = 1 - (1 - min(1.0, u)) ** 3
        dx = dy = 0.0
        esc, op = 1.0, 1.0
        if mov == "clasica":
            esc, dx, op = 1.25 - 0.25 * e, 12 * (1 - e), e
        elif mov in ("suave", "ola"):
            dy, op = (1 - e) * tam * (0.25 if mov == "suave" else 0.5), e
            if mov == "ola":
                dy += math.sin(t * 2.2 + i * 0.8) * tam * 0.05
        elif mov in ("brillo", "latido"):
            esc, dx, op = 1.08 - 0.08 * e, 6 * (1 - e), e
        ruta = QPainterPath()
        ruta.addText(QPointF(x0, base), f, w)
        if mov == "eco" and u < 1.6:
            for paso in (2, 1):
                eco = 1 - min(1.0, u / 1.6)
                p.save()
                p.setOpacity(0.25 * eco * (3 - paso) / 2)
                p.translate(-paso * tam * 0.2 * eco, 0)
                p.fillPath(ruta, QColor(255, 255, 255))
                p.restore()
        p.save()
        c = ruta.boundingRect().center()
        p.translate(c.x() + dx, c.y() + dy)
        p.scale(esc, esc)
        p.translate(-c.x(), -c.y())
        p.setOpacity(op)
        if mov == "brillo" and i == ultima:
            col = QColor(colores.a)
            for grosor, al in ((tam * 0.45, 40), (tam * 0.22, 70)):
                col.setAlpha(al)
                p.strokePath(ruta, QPen(col, grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        fuerte = i == 1
        if original and acabado in ("clasica", "neon", "contorno") and not fuerte:
            # la Original: contorno fino (en neón, del color de la carátula y con brillo)
            color = QColor(colores.a).lighter(140) if acabado == "neon" else QColor(255, 255, 255)
            if acabado == "neon":
                halo = QColor(colores.a)
                halo.setAlpha(70)
                p.strokePath(ruta, QPen(halo, max(2.0, tam * 0.14), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            if acabado == "contorno" and i <= ultima:
                p.fillPath(ruta, QColor(255, 255, 255))
            p.strokePath(ruta, QPen(color, max(1.0, tam * 0.045), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        else:
            p.strokePath(ruta, QPen(QColor(10, 8, 16, 170), max(1.2, tam * 0.06), Qt.SolidLine, Qt.RoundCap,
                                    Qt.RoundJoin))
            p.fillPath(ruta, QColor(colores.a).lighter(130) if fuerte else QColor(255, 255, 255))
        p.restore()
    p.restore()


def montaje_de_muestra(clave, versos, ciclo):
    """Una letra de mentira, para enseñar un diseño."""
    from .escena.letra import repartir_palabras
    cada = ciclo / len(versos)
    filas = [(i, v, int(i * cada * 1000), int(cada * 620), int((i + 1) * cada * 1000)) for i, v in enumerate(versos)]
    return epica.Montaje(clave, filas, repartir_palabras)


def pintar_epica(p, rect, montaje, t, colores, dpr):
    """Un instante del montaje dentro de `rect` (con un golpe inventado cada medio segundo)."""
    golpe = math.exp(-((t * 2.0) % 1.0) * 5.0)
    cx = epica.Lienzo(rect.width(), rect.height(), dpr, colores, 0.45, golpe * 0.8)
    p.save()
    p.translate(rect.center())
    montaje.pintar(p, t, cx)
    p.restore()


class _Rejilla(QWidget):
    """Las muestras en columnas iguales: tantas como quepan."""

    HUECO = 10

    def __init__(self, ancho_min, padre=None):
        super().__init__(padre)
        self.ancho_min = ancho_min
        self.muestras = []

    def anadir(self, m):
        m.setParent(self)
        self.muestras.append(m)

    def columnas(self, ancho):
        return max(2, (ancho + self.HUECO) // (self.ancho_min + self.HUECO))

    def _colocar(self):
        if not self.muestras:
            return
        n = self.columnas(self.width())
        w = (self.width() - self.HUECO * (n - 1)) / n
        h = self.muestras[0].ALTO
        for i, m in enumerate(self.muestras):
            x0 = round((i % n) * (w + self.HUECO))
            x1 = round((i % n) * (w + self.HUECO) + w)
            m.setGeometry(x0, (i // n) * (h + self.HUECO), x1 - x0, h)
        filas = (len(self.muestras) + n - 1) // n
        self.setFixedHeight(filas * (h + self.HUECO) - self.HUECO)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._colocar()


def _titulo(texto):
    t = QLabel(texto)
    t.setStyleSheet(f"font-size:15px;font-weight:800;color:{C['texto']};background:transparent;")
    return t


def _ficha(texto, ayuda="", marcable=False):
    b = QPushButton(texto)
    b.setCursor(Qt.PointingHandCursor)
    b.setAutoDefault(False)
    b.setCheckable(marcable)
    b.setToolTip(ayuda or texto)
    b.setStyleSheet(
        f"QPushButton{{border:1px solid {C['borde_claro']};border-radius:14px;padding:6px 13px;font-size:12.5px;"
        f"font-weight:700;color:{C['texto2']};background:transparent;}}"
        f"QPushButton:hover{{color:{C['texto']};background:{C['superficie2']};}}"
        f"QPushButton:checked{{color:{C['acento_texto']};background:{C['acento']};border-color:{C['acento']};}}")
    return b


class SelectorLetra(QWidget):
    """La vista previa, los estilos y los tipos de letra. Cada toque se aplica y se guarda al momento."""

    cambiado = Signal()

    def __init__(self, ctx, padre=None, en_escena=False):
        super().__init__(padre)
        self.ctx = ctx
        self.en_escena = en_escena       # abierto desde la Escena: elegir un estilo normal quita la letra épica
        self._quieto = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.vista = VistaPreviaLetra(ctx, self, 168 if en_escena else 124, con_epica=en_escena)
        v.addWidget(self.vista)

        # de un toque a cada parte: diseño, intensidad, estilo y tipo de letra
        ir = QHBoxLayout()
        ir.setContentsMargins(0, 0, 0, 0)
        ir.setSpacing(8)
        self.fichas_ir = {}
        for clave, texto in (("epicas", "Presentación"), ("intensidad", "Intensidad"), ("estilos", "Estilo"),
                             ("fuentes", "Tipo de letra")):
            b = self.fichas_ir[clave] = _ficha(texto, f"Ir a «{texto}»")
            b.clicked.connect(lambda _m=False, c=clave: self.ir_a(c))
            ir.addWidget(b)
        ir.addStretch(1)
        v.addLayout(ir)

        self.zona = QScrollArea()
        self.zona.setWidgetResizable(True)
        self.zona.setFrameShape(QFrame.NoFrame)
        self.zona.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # en la escena no llega la hoja de estilos de la ventana: sin esto la barra sale como la de Windows 95
        self.zona.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:transparent;width:10px;margin:0;border:none;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,0.22);border-radius:5px;min-height:40px;}"
            "QScrollBar::handle:vertical:hover{background:rgba(255,255,255,0.38);}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;border:none;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:transparent;}")
        self.zona.viewport().setAutoFillBackground(False)
        dentro = QWidget()
        dentro.setObjectName("dentro_selector")
        dentro.setStyleSheet("QWidget#dentro_selector{background:transparent;}")
        w = QVBoxLayout(dentro)
        w.setContentsMargins(0, 0, 8, 0)
        w.setSpacing(10)
        self._titulos = {}

        def titulo(clave, texto):
            t = self._titulos[clave] = _titulo(texto)
            w.addWidget(t)
        titulo("epicas", "Presentación de la letra en la Escena: la Original, con tu tipo de letra y el Eco")
        self.epicas = _Rejilla(150)
        self.grupo_epicas = QButtonGroup(self)
        # la Original (la de siempre) y sus variantes, la misma con tu tipo de letra, y el Eco fluido y las suyas
        for pres in presentacion_letra.lista():
            m = MuestraEpica(pres["epica"], pres["nombre"], pres["detalle"], ctx)
            m.mov, m.pres = pres["mov"], pres
            self.epicas.anadir(m)
            self.grupo_epicas.addButton(m)
        w.addWidget(self.epicas)
        w.addSpacing(6)
        titulo("intensidad", "Intensidad visual")
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(8)
        self.grupo_intensidad = QButtonGroup(self)
        self.intensidades = {}
        for clave, (nombre, detalle, _f) in epica.INTENSIDADES.items():
            b = self.intensidades[clave] = _ficha(nombre, detalle, True)
            b.setAccessibleName(f"Intensidad visual: {nombre}")
            self.grupo_intensidad.addButton(b)
            b.clicked.connect(lambda _m=False, c=clave: self.elegir_intensidad(c))
            fila.addWidget(b)
        fila.addStretch(1)
        w.addLayout(fila)
        self.et_intensidad = QLabel("")
        self.et_intensidad.setStyleSheet(f"font-size:12px;color:{C['texto2']};background:transparent;")
        w.addWidget(self.et_intensidad)
        w.addSpacing(6)
        titulo("estilos", "Estilo de la letra normal" if en_escena else "Estilo")
        self.estilos = _Rejilla(124)
        self.grupo_estilos = QButtonGroup(self)
        for clave, (nombre, detalle) in estilo_letra.NOMBRES.items():
            m = MuestraEstilo(clave, nombre, detalle, ctx)
            self.estilos.anadir(m)
            self.grupo_estilos.addButton(m)
        w.addWidget(self.estilos)
        w.addSpacing(6)
        titulo("fuentes", "Tipo de letra")
        self.fuentes = _Rejilla(150)
        self.grupo_fuentes = QButtonGroup(self)
        for clave, datos in tipografia_letra.FUENTES.items():
            m = MuestraFuente(clave, datos[0], "", ctx)
            self.fuentes.anadir(m)
            self.grupo_fuentes.addButton(m)
        w.addWidget(self.fuentes)
        w.addStretch(1)
        self.zona.setWidget(dentro)
        v.addWidget(self.zona, 1)

        self._marcar()
        self.grupo_estilos.buttonClicked.connect(lambda m: self.elegir_estilo(m.clave))
        self.grupo_fuentes.buttonClicked.connect(lambda m: self.elegir_fuente(m.clave))
        self.grupo_epicas.buttonClicked.connect(self.elegir_presentacion)
        tipografia_letra.suscribir(self)
        estilo_letra.suscribir(self)
        epica.suscribir(self)
        self._reloj = QTimer(self)
        self._reloj.setTimerType(Qt.PreciseTimer)
        self._reloj.setInterval(33)
        self._reloj.timeout.connect(self._mover_muestras)

    # ------------------------------------------------------------ muestras en movimiento
    def showEvent(self, e):
        super().showEvent(e)
        if not all(tipografia_letra.lista(c) for c in tipografia_letra.FUENTES):
            threading.Thread(target=tipografia_letra.leer_todas, name="tipos-de-letra", daemon=True).start()
        self._reloj.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._reloj.stop()

    def _mover_muestras(self):
        if not a_la_vista(self):
            return
        if self.vista.en_movimiento():
            self.vista.update()
        for m in self.epicas.muestras:
            if (m.clave or getattr(m, "mov", None)) and m.underMouse():
                m.paso()

    # ------------------------------------------------------------ elegir
    def _guardar(self, **valores):
        aj = getattr(self.ctx, "ajustes", None)
        if aj is None:
            return
        for k, val in valores.items():
            aj[k] = val
        try:
            aj.guardar()
        except Exception:  # noqa: BLE001  (sin poder escribir en disco, al menos queda puesto)
            pass

    def elegir_estilo(self, clave):
        clave = estilo_letra.normalizar(clave)
        self._guardar(estilo_letra=clave)
        estilo_letra.fijar(clave)
        if self.en_escena and (epica.actual() or estilo_letra.original()):
            self._a_tu_letra()                            # se está mirando la escena: que se vea el estilo elegido
        self.cambiado.emit()

    def _a_tu_letra(self):
        """En la escena, elegir estilo o tipo de letra pone «Tu tipo de letra» (la Original no los usa)."""
        mov = estilo_letra.movimiento()
        pres = presentacion_letra.por_clave("tuya" if mov == "clasica" else f"tuya_{mov}")
        presentacion_letra.aplicar(pres, getattr(self.ctx, "ajustes", None))
        self._marcar()

    def elegir_epica(self, clave):
        clave = epica.normalizar(clave)
        pres = presentacion_letra.por_clave(clave) if clave else presentacion_letra.actual()
        presentacion_letra.aplicar(pres or presentacion_letra.por_clave(presentacion_letra.POR_DEFECTO),
                                   getattr(self.ctx, "ajustes", None))
        self.cambiado.emit()

    def elegir_presentacion(self, m):
        presentacion_letra.aplicar(m.pres, getattr(self.ctx, "ajustes", None))
        self._marcar()
        self.cambiado.emit()

    def elegir_intensidad(self, clave):
        clave = clave if clave in epica.INTENSIDADES else epica.INTENSIDAD_POR_DEFECTO
        self._guardar(letra_intensidad=clave)
        epica.fijar_intensidad(clave)
        self._marcar()
        self.cambiado.emit()

    def elegir_movimiento(self, clave):
        clave = clave if clave in estilo_letra.MOVIMIENTOS else estilo_letra.MOVIMIENTO_POR_DEFECTO
        self._guardar(letra_movimiento=clave)
        if epica.actual():
            self._guardar(letra_epica=epica.NINGUNA, letra_epica_elegida=True)   # se nota en la clásica: se pone
            epica.fijar(epica.NINGUNA)
        estilo_letra.fijar_movimiento(clave)
        self._marcar()
        self.cambiado.emit()

    def ir_a(self, parte):
        """Desplaza el panel hasta esa parte (su título arriba del todo)."""
        t = self._titulos[parte]
        self.zona.verticalScrollBar().setValue(max(0, t.y() - 4))

    def elegir_fuente(self, clave):
        clave = tipografia_letra.normalizar(clave)
        self._guardar(fuente_letra=clave)
        tipografia_letra.fijar(clave)
        if self.en_escena and estilo_letra.original() and not epica.actual():
            self._a_tu_letra()
        self.cambiado.emit()

    def restablecer(self):
        """Vuelve a la letra de siempre."""
        self._guardar(estilo_letra=estilo_letra.POR_DEFECTO, fuente_letra=tipografia_letra.POR_DEFECTO,
                      letra_epica=epica.NINGUNA, letra_intensidad=epica.INTENSIDAD_POR_DEFECTO,
                      letra_movimiento=estilo_letra.MOVIMIENTO_POR_DEFECTO)
        estilo_letra.fijar_movimiento(estilo_letra.MOVIMIENTO_POR_DEFECTO)
        epica.fijar_intensidad(epica.INTENSIDAD_POR_DEFECTO)
        epica.fijar(epica.NINGUNA)
        estilo_letra.fijar(estilo_letra.POR_DEFECTO)
        tipografia_letra.fijar(tipografia_letra.POR_DEFECTO)
        self.cambiado.emit()

    # ------------------------------------------------------------ lo puesto
    def muestra_estilo(self, clave):
        return next(m for m in self.estilos.muestras if m.clave == clave)

    def muestra_epica(self, clave):
        clave = epica.normalizar(clave)
        if clave:
            return next(m for m in self.epicas.muestras if m.clave == clave)
        puesta = presentacion_letra.actual()
        return next(m for m in self.epicas.muestras if m.pres["clave"] == puesta["clave"])

    def muestra_fuente(self, clave):
        return next(m for m in self.fuentes.muestras if m.clave == clave)

    def _marcar(self):
        self.muestra_epica(epica.actual()).setChecked(True)
        self.muestra_estilo(estilo_letra.actual()).setChecked(True)
        self.muestra_fuente(tipografia_letra.actual()).setChecked(True)
        self.intensidades[epica.intensidad()].setChecked(True)
        self.et_intensidad.setText(epica.INTENSIDADES[epica.intensidad()][1]
                                   + ("" if epica.actual() else " · se nota en las presentaciones Eco"))

    def al_cambiar_tipografia(self):
        self._marcar()
        for m in self.estilos.muestras + self.epicas.muestras:       # se enseñan con la tipografía puesta
            m.rehacer()

    def al_cambiar_estilo_letra(self):
        self._marcar()
        self.muestra_epica(epica.NINGUNA).rehacer()

    def al_cambiar_letra_epica(self):
        self._marcar()

    def mostrar_puesta(self):
        """Desplaza la lista hasta el tipo de letra puesto, si no se ve."""
        m = self.muestra_fuente(tipografia_letra.actual())
        if self.en_escena:
            return                        # primero se ven las letras épicas
        if tipografia_letra.actual() != tipografia_letra.POR_DEFECTO:
            self.zona.ensureWidgetVisible(m, 0, 60)


class DialogoLetra(QDialog):
    """La ventana «Diseño de letra». Con `sin_marco` (en la Escena) lleva su propia cabecera arrastrable."""

    def __init__(self, ctx, padre=None, sin_marco=False):
        super().__init__(padre)
        self.ctx = ctx
        self.sin_marco = sin_marco
        self._arrastre = None
        self.setWindowTitle("Diseño de letra")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(False)
        if sin_marco:
            self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("dialogo_letra")
        fuera = QVBoxLayout(self)
        fuera.setContentsMargins(0, 0, 0, 0)
        self.caja = QFrame()
        self.caja.setObjectName("caja_letra")
        borde = f"border:1px solid {C['borde_claro']};border-radius:16px;" if sin_marco else "border:none;"
        self.caja.setStyleSheet(f"QFrame#caja_letra{{background:{C['panel']};{borde}}}")
        fuera.addWidget(self.caja)
        v = QVBoxLayout(self.caja)
        v.setContentsMargins(22, 18, 16, 16)
        v.setSpacing(12)

        cab = QHBoxLayout()
        cab.setContentsMargins(0, 0, 6, 0)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        t = QLabel("Diseño de letra")
        t.setStyleSheet(f"font-size:20px;font-weight:800;color:{C['texto']};background:transparent;")
        textos.addWidget(t)
        a = QLabel("Las letras épicas son de la Escena de escritorio. El estilo y el tipo de letra valen también para "
                   "la letra de la canción y el karaoke." if sin_marco else
                   "Se aplica al momento en la Escena de escritorio, en la letra de la canción y en el karaoke.")
        a.setWordWrap(True)
        a.setStyleSheet(f"font-size:12px;color:{C['texto2']};background:transparent;")
        textos.addWidget(a)
        cab.addLayout(textos, 1)
        v.addLayout(cab)

        self.selector = SelectorLetra(ctx, self.caja, en_escena=sin_marco)
        v.addWidget(self.selector, 1)

        pie = QHBoxLayout()
        pie.setContentsMargins(0, 0, 6, 0)
        self.bt_siempre = QPushButton("Volver a la de siempre")
        self.bt_siempre.setCursor(Qt.PointingHandCursor)
        self.bt_siempre.setAutoDefault(False)
        self.bt_siempre.setStyleSheet(
            f"QPushButton{{border:1px solid {C['borde_claro']};border-radius:16px;padding:7px 16px;font-size:13px;"
            f"font-weight:700;color:{C['texto2']};background:transparent;}}"
            f"QPushButton:hover{{color:{C['texto']};background:{C['superficie2']};}}")
        self.bt_siempre.clicked.connect(self.selector.restablecer)
        self.bt_listo = QPushButton("Listo")
        self.bt_listo.setCursor(Qt.PointingHandCursor)
        self.bt_listo.setAutoDefault(False)
        self.bt_listo.setStyleSheet(
            f"QPushButton{{border:none;border-radius:16px;padding:8px 26px;font-size:13px;font-weight:800;"
            f"color:{C['acento_texto']};background:{C['acento']};}}"
            f"QPushButton:hover{{background:{C['acento_alto']};}}")
        self.bt_listo.clicked.connect(self.close)
        pie.addWidget(self.bt_siempre)
        pie.addStretch(1)
        pie.addWidget(self.bt_listo)
        v.addLayout(pie)
        self.setMinimumSize(420, 420)
        self.resize(760, 680)

    def showEvent(self, e):
        super().showEvent(e)
        self.selector.mostrar_puesta()

    # ------------------------------------------------------------ arrastrar (sin marco)
    def mousePressEvent(self, e):
        if self.sin_marco and e.button() == Qt.LeftButton and e.position().y() < 70:
            self._arrastre = e.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            self.move(e.globalPosition().toPoint() - self._arrastre)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._arrastre = None
        super().mouseReleaseEvent(e)


_abierto = None            # weakref del diálogo a la vista (solo uno a la vez)


def dialogo_abierto():
    d = _abierto() if _abierto is not None else None
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:                  # ya destruido
        return None


def abrir_selector(ctx, padre=None, sin_marco=False, area=None, lado="centro"):
    """Abre «Diseño de letra» sin bloquear (la letra se ve cambiar detrás) y devuelve el diálogo. Si ya está
    abierto desde la misma ventana, lo trae al frente. `area`: dónde debe caber (QRect); `lado`: «centro» o
    «izquierda»."""
    global _abierto
    ventana = padre.window() if padre is not None else None
    d = dialogo_abierto()
    if d is not None:
        if d.parentWidget() is ventana:
            d.raise_()
            d.activateWindow()
            return d
        d.close()
    d = DialogoLetra(ctx, ventana, sin_marco)
    if area is None:
        pantalla = (ventana.screen() if ventana is not None else None) or QGuiApplication.primaryScreen()
        area = pantalla.availableGeometry() if pantalla is not None else None
    if area is not None:
        ancho, alto = min(760, area.width() - 40), min(680, area.height() - 60)
        if lado == "izquierda":
            ancho = min(ancho, max(420, int(area.width() * 0.40)))
        d.resize(max(420, ancho), max(420, alto))
        if lado == "izquierda":
            d.move(area.left() + 24, area.top() + (area.height() - d.height()) // 2)
        else:
            centro = ventana.frameGeometry().center() if ventana is not None else area.center()
            x = min(max(centro.x() - d.width() // 2, area.left() + 10), area.right() - d.width() - 10)
            y = min(max(centro.y() - d.height() // 2, area.top() + 10), area.bottom() - d.height() - 40)
            d.move(QPoint(x, max(area.top() + 10, y)))
    _abierto = weakref.ref(d)
    d.show()
    d.raise_()
    d.activateWindow()
    return d
