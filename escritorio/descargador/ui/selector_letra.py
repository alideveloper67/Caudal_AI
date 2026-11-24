# -*- coding: utf-8 -*-
"""«Diseño de letra»: elegir el tipo de letra y el estilo con que se ven las letras de las canciones.

Cada tipo de letra se muestra escrito en su propia letra y cada estilo pintado de verdad. Al tocar uno se
aplica al momento en la Escena de escritorio, en la letra de la canción (página y panel) y en el karaoke, y
queda guardado (ajustes «fuente_letra» y «estilo_letra»).

`abrir_selector(ctx, padre)` abre la ventana; `SelectorLetra` y `VistaPreviaLetra` también valen sueltos."""

import weakref

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QFontMetricsF, QGuiApplication, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from . import estilo_letra, tipografia_letra
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

    def __init__(self, ctx, padre=None, alto=120, texto=TEXTO_VISTA):
        super().__init__(padre)
        self.ctx = ctx
        self.texto = texto
        self._pm = None
        self.setMinimumHeight(alto)
        self.setMaximumHeight(alto)
        self.setAccessibleName("Vista previa de la letra")
        tipografia_letra.suscribir(self)
        estilo_letra.suscribir(self)

    def al_cambiar_tipografia(self):
        self._pm = None
        self.update()

    al_cambiar_estilo_letra = al_cambiar_tipografia

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._pm = None

    def showEvent(self, e):
        super().showEvent(e)
        self._pm = None                 # los colores de la carátula pueden ser otros

    def paintEvent(self, _e):
        dpr = self.devicePixelRatioF() or 1.0
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


class _Muestra(QAbstractButton):
    """Una tarjeta que se puede elegir: la muestra arriba y su nombre abajo."""

    ALTO = 92

    def __init__(self, clave, nombre, ayuda, ctx, padre=None):
        super().__init__(padre)
        self.clave = clave
        self.nombre = nombre
        self.ctx = ctx
        self._pm = None
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

    def paintEvent(self, _e):
        dpr = self.devicePixelRatioF() or 1.0
        if self._pm is None or self._pm.devicePixelRatio() != dpr:
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
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(1, 1, -1, -1)
        puesta = self.isChecked()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"] if (puesta or self.underMouse()) else C["superficie2"]))
        p.drawRoundedRect(rect, 12, 12)
        p.drawPixmap(0, 0, self._pm)
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


class SelectorLetra(QWidget):
    """La vista previa, los estilos y los tipos de letra. Cada toque se aplica y se guarda al momento."""

    cambiado = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self._quieto = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.vista = VistaPreviaLetra(ctx, self, 124)
        v.addWidget(self.vista)

        self.zona = QScrollArea()
        self.zona.setWidgetResizable(True)
        self.zona.setFrameShape(QFrame.NoFrame)
        self.zona.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zona.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.zona.viewport().setAutoFillBackground(False)
        dentro = QWidget()
        dentro.setObjectName("dentro_selector")
        dentro.setStyleSheet("QWidget#dentro_selector{background:transparent;}")
        w = QVBoxLayout(dentro)
        w.setContentsMargins(0, 0, 8, 0)
        w.setSpacing(10)
        w.addWidget(_titulo("Estilo"))
        self.estilos = _Rejilla(124)
        self.grupo_estilos = QButtonGroup(self)
        for clave, (nombre, detalle) in estilo_letra.NOMBRES.items():
            m = MuestraEstilo(clave, nombre, detalle, ctx)
            self.estilos.anadir(m)
            self.grupo_estilos.addButton(m)
        w.addWidget(self.estilos)
        w.addSpacing(6)
        w.addWidget(_titulo("Tipo de letra"))
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
        tipografia_letra.suscribir(self)
        estilo_letra.suscribir(self)

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
        self.cambiado.emit()

    def elegir_fuente(self, clave):
        clave = tipografia_letra.normalizar(clave)
        self._guardar(fuente_letra=clave)
        tipografia_letra.fijar(clave)
        self.cambiado.emit()

    def restablecer(self):
        """Vuelve a la letra de siempre."""
        self._guardar(estilo_letra=estilo_letra.POR_DEFECTO, fuente_letra=tipografia_letra.POR_DEFECTO)
        estilo_letra.fijar(estilo_letra.POR_DEFECTO)
        tipografia_letra.fijar(tipografia_letra.POR_DEFECTO)
        self.cambiado.emit()

    # ------------------------------------------------------------ lo puesto
    def muestra_estilo(self, clave):
        return next(m for m in self.estilos.muestras if m.clave == clave)

    def muestra_fuente(self, clave):
        return next(m for m in self.fuentes.muestras if m.clave == clave)

    def _marcar(self):
        self.muestra_estilo(estilo_letra.actual()).setChecked(True)
        self.muestra_fuente(tipografia_letra.actual()).setChecked(True)

    def al_cambiar_tipografia(self):
        self._marcar()
        for m in self.estilos.muestras:       # cada estilo se enseña con la tipografía puesta
            m.rehacer()

    def al_cambiar_estilo_letra(self):
        self._marcar()

    def mostrar_puesta(self):
        """Desplaza la lista hasta el tipo de letra puesto, si no se ve."""
        m = self.muestra_fuente(tipografia_letra.actual())
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
        a = QLabel("Se aplica al momento en la Escena de escritorio, en la letra de la canción y en el karaoke.")
        a.setWordWrap(True)
        a.setStyleSheet(f"font-size:12px;color:{C['texto2']};background:transparent;")
        textos.addWidget(a)
        cab.addLayout(textos, 1)
        v.addLayout(cab)

        self.selector = SelectorLetra(ctx, self.caja)
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
