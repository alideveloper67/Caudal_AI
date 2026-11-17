# -*- coding: utf-8 -*-
"""La capa de «Fondo de Caudal»: se pinta detrás de todo el contenido de la ventana.

Color base de la app + la imagen «cubriendo» todo el espacio con poca opacidad (y, si se
pide, desenfocada) + una viñeta que oscurece los bordes y la parte de abajo + un toque
muy suave del color de acento. La imagen ya escalada y desenfocada se guarda en una caché:
al pintar solo se compone, y al cambiar el tamaño se re-escala una vez, con una pausa.
"""

from PySide6.QtCore import QEvent, QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget)

from .estilos import C

_PATRONES = {}


def pixmap_patron(ruta):
    """El dibujo del personaje del fondo (descargador/fondos/<clave>.png). Se carga una vez."""
    if ruta is None:
        return None
    clave = str(ruta)
    if clave not in _PATRONES:
        pm = QPixmap(clave)
        _PATRONES[clave] = None if pm.isNull() else pm
    return _PATRONES[clave]


def _con_alfa(color, alfa):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alfa))))
    return c


def escena_cubierta(img, tam, desenfoque):
    """La imagen «cubriendo» `tam` (recorte centrado) y, si se pide, desenfocada (0–20).
    El desenfoque se hace sobre una copia a mitad de tamaño y luego se agranda: barato."""
    w, h = max(1, tam.width()), max(1, tam.height())
    if desenfoque <= 0:
        c = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return QPixmap.fromImage(c.copy((c.width() - w) // 2, (c.height() - h) // 2, w, h))
    hw, hh = max(2, w // 2), max(2, h // 2)
    radio = desenfoque * 1.1
    margen = int(radio * 2) + 2
    c = img.scaled(hw, hh, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    c = c.copy((c.width() - hw) // 2, (c.height() - hh) // 2, hw, hh)
    # se estira un poco hacia los bordes para que el desenfoque no deje orillas claras
    grande = c.scaled(hw + 2 * margen, hh + 2 * margen, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    escena = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(grande))
    efecto = QGraphicsBlurEffect()
    efecto.setBlurRadius(radio)
    efecto.setBlurHints(QGraphicsBlurEffect.QualityHint)
    item.setGraphicsEffect(efecto)
    escena.addItem(item)
    salida = QImage(grande.size(), QImage.Format_ARGB32_Premultiplied)
    salida.fill(Qt.transparent)
    p = QPainter(salida)
    escena.render(p, QRectF(salida.rect()), QRectF(salida.rect()))
    p.end()
    corte = salida.copy(margen, margen, hw, hh).scaled(w, h, Qt.IgnoreAspectRatio,
                                                       Qt.SmoothTransformation)
    return QPixmap.fromImage(corte)


class Renderizador:
    """Pinta el fondo en cualquier rectángulo (la ventana o la vista previa)."""

    def __init__(self):
        self._pm = None
        self._clave = None
        self._compuesto = None
        self._clave_compuesto = None

    def compuesto(self, ancho, alto, dpr, img, serie, visible, desenfoque):
        """El fondo entero (color + imagen + velos + viñeta + acento) ya compuesto en un QPixmap.
        Se rehace solo si cambia el tamaño, la imagen, sus ajustes o los colores: la capa de la
        ventana se repinta cada vez que algo translúcido se mueve encima, y así cada repintado
        es copiar un trozo de imagen en vez de seis degradados."""
        hay = img is not None and not img.isNull()
        clave = (int(ancho), int(alto), float(dpr), serie if hay else None, visible, desenfoque,
                 C["fondo"], C["panel"], C["acento"])
        if clave != self._clave_compuesto or self._compuesto is None:
            pm = QPixmap(max(1, int(ancho * dpr)), max(1, int(alto * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            self.pintar(q, QRectF(0, 0, ancho, alto), img, serie, visible, desenfoque)
            q.end()
            self._compuesto, self._clave_compuesto = pm, clave
        return self._compuesto

    def _escena(self, img, serie, rect, desenfoque, estirar):
        tam = QSize(max(1, int(rect.width())), max(1, int(rect.height())))
        clave = (serie, tam.width(), tam.height(), desenfoque)
        if clave != self._clave:
            if estirar and self._pm is not None:
                return self._pm                 # mientras se arrastra el borde: se estira la anterior
            self._pm = escena_cubierta(img, tam, desenfoque)
            self._clave = clave
        return self._pm

    def pintar(self, p, rect, img, serie, visible, desenfoque, estirar=False, patron=None):
        """`visible` es el porcentaje (5–60) de imagen que se deja ver. `patron` (QPixmap): el personaje del
        fondo elegido; se ve chico, a un costado, y si además hay imagen de «Fondo de Caudal» va encima de
        ella en su esquina (la imagen no se tapa)."""
        rect = QRectF(rect)
        w, h = rect.width(), rect.height()
        base = QColor(C["fondo"])
        p.save()
        p.setClipRect(rect, Qt.IntersectClip)
        p.translate(rect.topLeft())
        r = QRectF(0, 0, w, h)
        # el color de la app, con un cambio de tono casi imperceptible de arriba abajo
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(C["panel"]))
        g.setColorAt(1, base)
        p.fillRect(r, g)
        v = max(0.0, min(1.0, visible / 100.0))
        hay_imagen = img is not None and not img.isNull()
        if not hay_imagen:
            v = 0.0
        if hay_imagen:
            pm = self._escena(img, serie, rect, desenfoque, estirar)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(v)
            p.drawPixmap(r.toRect(), pm)
            p.setOpacity(1.0)
        # un velo que crece con la imagen: cuanto más se ve, más se cuida el texto
        p.fillRect(r, _con_alfa(base, 255 * min(0.3, v * 0.30)))
        # viñeta: oscurece hacia los bordes y hacia abajo (profundidad y lectura)
        d = max(w, h)
        rad = QRadialGradient(w * 0.5, h * 0.42, d * 0.80)
        rad.setColorAt(0.0, _con_alfa(base, 0))
        rad.setColorAt(0.55, _con_alfa(base, 0))
        rad.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, rad)
        baja = QLinearGradient(0, h * 0.50, 0, h)
        baja.setColorAt(0.0, _con_alfa(base, 0))
        baja.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, baja)
        # un soplo del color de acento desde la esquina de arriba
        ac = QColor(C["acento"])
        brillo = QRadialGradient(w * 0.88, -h * 0.05, d * 0.70)
        brillo.setColorAt(0.0, _con_alfa(ac, 30))
        brillo.setColorAt(1.0, _con_alfa(ac, 0))
        p.fillRect(r, brillo)
        lado = QLinearGradient(0, 0, w, h)
        lado.setColorAt(0.0, _con_alfa(ac, 12))
        lado.setColorAt(0.6, _con_alfa(ac, 0))
        p.fillRect(r, lado)
        p.restore()


class PersonajeEsquina(QWidget):
    """El personaje del fondo elegido, sentado sobre el borde de arriba de la barra del reproductor, en
    la esquina derecha. Siempre se ve entero (los paneles no lo tapan) y sigue a la barra (tamaño de la
    ventana, pantalla completa). Convive con la imagen de fondo.

    Su tamaño se cambia con el ratón, sin ir a ningún ajuste: la rueda encima de él, o arrastrarlo
    (hacia arriba/izquierda crece, hacia abajo/derecha se achica). Se recuerda en los ajustes."""

    ALTO = 124         # tamaño de partida (el dibujo mide 96 px: se agranda sin suavizar, nítido)
    MINIMO, MAXIMO = 64, 280
    MARGEN = 22        # espacio para el halo
    CLAVE = "tamano_personaje"

    def __init__(self, padre, barra=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setToolTip("Gira la rueda o arrástralo para hacerlo más grande o más chico")
        self.barra = barra
        self.pm = None
        self._arrastre = None            # (punto global de inicio, alto al empezar)
        self._t_guardar = QTimer(self)
        self._t_guardar.setSingleShot(True)
        self._t_guardar.setInterval(500)
        self._t_guardar.timeout.connect(self._guardar)
        if barra is not None:
            barra.installEventFilter(self)
        self.alto = self._leer_alto()
        self.hide()

    # ---------------------------------------------------------------- tamaño
    def _ajustes(self):
        return getattr(self.parentWidget(), "ajustes", None)

    def _leer_alto(self):
        try:
            v = int((self._ajustes() or {})[self.CLAVE] or self.ALTO)
        except (TypeError, ValueError, KeyError):
            v = self.ALTO
        return max(self.MINIMO, min(self.MAXIMO, v))

    def poner_alto(self, alto):
        alto = max(self.MINIMO, min(self.MAXIMO, int(alto)))
        if alto != self.alto:
            self.alto = alto
            self.colocar()
            self._t_guardar.start()

    def _guardar(self):
        a = self._ajustes()
        if a is not None:
            a[self.CLAVE] = self.alto
            try:
                a.guardar()
            except Exception:  # noqa: BLE001
                pass

    def wheelEvent(self, e):
        paso = 1 if e.angleDelta().y() > 0 else -1
        self.poner_alto(self.alto + paso * 10)
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = (e.globalPosition(), self.alto)
            e.accept()

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            inicio, alto0 = self._arrastre
            d = e.globalPosition() - inicio
            # la esquina de abajo a la derecha queda fija: hacia arriba/izquierda crece
            self.poner_alto(alto0 - (d.x() + d.y()) / 2)
            e.accept()

    def mouseReleaseEvent(self, e):
        if self._arrastre is not None:
            self._arrastre = None
            self._guardar()
            e.accept()

    def eventFilter(self, obj, e):
        if obj is self.barra and e.type() in (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide):
            QTimer.singleShot(0, self.colocar)
        return False

    def colocar(self):
        from .estilos import patron_actual
        self.pm = pixmap_patron(patron_actual())
        padre = self.parentWidget()
        barra = self.barra
        if self.pm is None or padre is None or barra is None or not barra.isVisible():
            self.hide()
            return
        h, m = self.alto, self.MARGEN
        w = int(self.pm.width() * h / max(1, self.pm.height()))
        self.resize(w + 2 * m, h + m + 6)
        arriba = barra.mapTo(padre, QPoint(0, 0)).y()
        # los pies apoyados en el borde de arriba de la barra, en la esquina derecha
        self.move(padre.width() - self.width() - 8, arriba - h - m + 4)
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, _e):
        if self.pm is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        h, m = self.alto, self.MARGEN
        w = self.width() - 2 * m
        x, y = m, m
        p.setPen(Qt.NoPen)
        # halo suave del color del tema detrás: se nota sobre cualquier fondo, también sobre una foto
        ac = QColor(C["acento"])
        cx, cy = self.width() / 2, y + h * 0.58
        radio = min(self.width() / 2, self.height() - cy, cy) - 1    # se apaga antes de tocar el borde
        halo = QRadialGradient(cx, cy, radio)
        halo.setColorAt(0.0, _con_alfa(ac, 80))
        halo.setColorAt(0.5, _con_alfa(ac, 30))
        halo.setColorAt(1.0, _con_alfa(ac, 0))
        p.setBrush(halo)
        p.drawEllipse(QRectF(cx - radio, cy - radio, radio * 2, radio * 2))
        # sombra bajo los pies: lo «posa» sobre la barra
        sombra = QRadialGradient(x + w / 2, y + h - 1, w * 0.48)
        sombra.setColorAt(0.0, _con_alfa("#000000", 150))
        sombra.setColorAt(1.0, _con_alfa("#000000", 0))
        p.setBrush(sombra)
        p.drawEllipse(QRectF(x + w * 0.04, y + h - 8, w * 0.92, 15))
        # agrandar pixel art: sin suavizado (nítido); solo se suaviza si hubiera que achicarlo
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.pm.height() > h)
        p.drawPixmap(QRectF(x, y, w, h), self.pm, QRectF(self.pm.rect()))
        p.end()


class CapaFondo(QWidget):
    """Hija de la ventana, siempre al fondo; no recibe clics."""

    def __init__(self, gestor, padre):
        super().__init__(padre)
        self.gestor = gestor
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.rend = Renderizador()
        self._redimensionando = False
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(140)
        self._t.timeout.connect(self._fin_redimension)
        gestor.cambiado.connect(self._al_cambiar)

    def _al_cambiar(self, _a=None):
        self.update()

    def _fin_redimension(self):
        self._redimensionando = False
        self.update()

    def resizeEvent(self, e):
        self._redimensionando = True
        self._t.start()
        super().resizeEvent(e)

    def paintEvent(self, e):
        g = self.gestor
        p = QPainter(self)
        if self._redimensionando:
            # mientras se arrastra el borde: se pinta directo (componer en cada paso sería peor)
            self.rend.pintar(p, QRectF(self.rect()), g.imagen, g.serie, g.visible, g.desenfoque,
                             estirar=True)
        else:
            dpr = self.devicePixelRatioF()
            pm = self.rend.compuesto(self.width(), self.height(), dpr, g.imagen, g.serie,
                                     g.visible, g.desenfoque)
            # el pintor ya viene recortado a la zona que se repinta: solo se copia ese trozo
            p.drawPixmap(0, 0, pm)
        p.end()
