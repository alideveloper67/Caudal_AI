# -*- coding: utf-8 -*-
"""Arrastrar con el ratón para desplazar, como con el dedo en el teléfono.

Se instala una sola vez en la aplicación (`instalar()`): al pulsar y mover el
ratón sobre cualquier página, lista o carrusel, el contenido sigue al puntero y,
al soltar, se desliza un poco más (inercia). Los clics normales no cambian: solo
cuenta como arrastre si el puntero se mueve unos pocos píxeles.

Solo se mira la pulsación en cada ventana y, mientras dura, el widget pulsado y los que lo contienen.
(Antes era un filtro de toda la aplicación: cada evento de cada widget —miles por pantalla— pasaba por
Python, y solo eso eran ~100 ms al abrir Ajustes.)
"""
from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QMouseEvent, QWindow
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QAbstractSlider, QAbstractSpinBox,
                               QApplication, QComboBox, QLineEdit, QPlainTextEdit, QTabBar, QTextEdit, QWidget)

# lo que ya hace algo propio con el arrastre (texto, deslizadores, listas con su propio desplazamiento)
_PROPIOS = (QAbstractSlider, QAbstractSpinBox, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
            QTabBar, QAbstractItemView)


class ArrastreRaton(QObject):
    UMBRAL = 7          # píxeles que hay que mover para que cuente como arrastre
    FRICCION = 0.93     # cuánto se frena la inercia en cada paso

    def __init__(self, padre=None):
        super().__init__(padre)
        self._objetivo = None       # el widget donde se pulsó
        self._origen = None         # punto global donde se pulsó
        self._cadena = []           # áreas de desplazamiento por encima del widget
        self._area = None
        self._eje = None
        self._base = 0
        self._arrastrando = False
        self._ultimo = None
        self._velocidad = 0.0
        self._barra = None
        self._cursor = False
        self._vigilados = []        # widgets con el filtro puesto mientras dura la pulsación
        self._inercia = QTimer(self)
        self._inercia.setInterval(16)
        self._inercia.timeout.connect(self._paso_inercia)

    # ---------------------------------------------------------------- utilidades
    @staticmethod
    def _areas_sobre(w):
        areas = []
        p = w
        while p is not None:
            if isinstance(p, QAbstractScrollArea):
                areas.append(p)
            p = p.parentWidget()
        return areas

    @staticmethod
    def _se_excluye(w):
        p = w
        while p is not None:
            if isinstance(p, _PROPIOS):
                return True
            # filas que se arrastran para reordenar, y deslizadores propios
            if hasattr(p, "_pulsado_en") or hasattr(p, "arrastrando") or p.property("sin_arrastre"):
                return True
            p = p.parentWidget()
        return False

    def _poner_cursor(self, si):
        if si and not self._cursor:
            QGuiApplication.setOverrideCursor(Qt.ClosedHandCursor)
            self._cursor = True
        elif not si and self._cursor:
            QGuiApplication.restoreOverrideCursor()
            self._cursor = False

    def vigilar_ventana(self, ventana):
        """Cada ventana nativa se mira una sola vez (llega sola al ganar el foco)."""
        if ventana is None or ventana.property("_caudal_arrastre"):
            return
        ventana.setProperty("_caudal_arrastre", True)
        ventana.installEventFilter(self)

    def _vigilar(self, widget):
        """El filtro, en el widget pulsado y los que lo contienen (hasta su ventana)."""
        self._soltar_vigilados()
        p = widget
        while p is not None:
            p.installEventFilter(self)
            self._vigilados.append(p)
            if p.isWindow():
                break
            p = p.parentWidget()

    def _soltar_vigilados(self):
        for w in self._vigilados:
            try:
                w.removeEventFilter(self)
            except RuntimeError:            # ya se destruyó
                pass
        self._vigilados = []

    def _reiniciar(self):
        self._poner_cursor(False)
        self._soltar_vigilados()
        self._objetivo = None
        self._origen = None
        self._cadena = []
        self._area = None
        self._eje = None
        self._arrastrando = False

    # ---------------------------------------------------------------- eventos
    def eventFilter(self, obj, e):
        t = e.type()
        if isinstance(obj, QWindow):
            # la pulsación llega antes a la ventana que al widget: ahí se pone a mirar lo que se pulsó
            if t == QEvent.MouseButtonPress:
                self._inercia.stop()
                self._reiniciar()
                if e.button() == Qt.LeftButton:
                    w = QApplication.widgetAt(e.globalPosition().toPoint())
                    if w is not None and self._areas_sobre(w):
                        self._vigilar(w)
            elif t in (QEvent.Close, QEvent.Hide):
                self._reiniciar()
            return False
        if t == QEvent.MouseButtonPress:
            if e.button() == Qt.LeftButton and isinstance(obj, QWidget):
                self._inercia.stop()
                self._objetivo = None
                if not self._se_excluye(obj):
                    cadena = self._areas_sobre(obj)
                    if cadena:
                        self._objetivo = obj
                        self._cadena = cadena
                        self._origen = e.globalPosition()
            return False
        if self._objetivo is None or obj is not self._objetivo:
            return False
        if t == QEvent.MouseMove:
            if not (e.buttons() & Qt.LeftButton):
                self._reiniciar()
                return False
            return self._mover(e)
        if t == QEvent.MouseButtonRelease and e.button() == Qt.LeftButton:
            if self._arrastrando:
                self._soltar()
                return True          # no cuenta como clic
            self._reiniciar()
            return False
        return False

    def _mover(self, e):
        pos = e.globalPosition()
        if not self._arrastrando:
            dx = pos.x() - self._origen.x()
            dy = pos.y() - self._origen.y()
            if abs(dx) < self.UMBRAL and abs(dy) < self.UMBRAL:
                return False
            self._eje = "h" if abs(dx) > abs(dy) else "v"
            area = None
            for a in self._cadena:
                barra = a.horizontalScrollBar() if self._eje == "h" else a.verticalScrollBar()
                if barra.maximum() > barra.minimum():
                    area = a
                    break
            if area is None:
                self._reiniciar()
                return False
            self._area = area
            self._barra = area.horizontalScrollBar() if self._eje == "h" else area.verticalScrollBar()
            self._base = self._barra.value()
            self._origen = pos
            self._ultimo = (pos, None)
            self._velocidad = 0.0
            self._arrastrando = True
            self._poner_cursor(True)
            self._cancelar_pulsacion()
            return True
        delta = (pos.x() - self._origen.x()) if self._eje == "h" else (pos.y() - self._origen.y())
        self._barra.setValue(int(self._base - delta))
        anterior = self._ultimo[0]
        paso = (pos.x() - anterior.x()) if self._eje == "h" else (pos.y() - anterior.y())
        self._velocidad = 0.6 * self._velocidad + 0.4 * (-paso)
        self._ultimo = (pos, None)
        return True

    def _cancelar_pulsacion(self):
        """El widget ya recibió la pulsación: se le suelta fuera de sí para que no cuente como clic."""
        w = self._objetivo
        if w is None:
            return
        fuera = QPointF(-5000.0, -5000.0)
        ev = QMouseEvent(QEvent.MouseButtonRelease, fuera, w.mapToGlobal(fuera.toPoint()),
                         Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
        # directo al widget, sin pasar otra vez por este filtro
        self._objetivo = None
        try:
            QApplication.sendEvent(w, ev)
        finally:
            self._objetivo = w

    def _soltar(self):
        self._poner_cursor(False)
        self._arrastrando = False
        if abs(self._velocidad) > 1.5 and self._barra is not None:
            self._inercia.start()
        else:
            self._reiniciar()
        self._soltar_vigilados()
        self._objetivo = None

    def _paso_inercia(self):
        barra = self._barra
        if barra is None:
            self._inercia.stop()
            return
        self._velocidad *= self.FRICCION
        nuevo = barra.value() + int(round(self._velocidad * 1.6))
        barra.setValue(nuevo)
        if abs(self._velocidad) < 0.6 or nuevo <= barra.minimum() or nuevo >= barra.maximum():
            self._inercia.stop()
            self._reiniciar()


_instancia = None


def instalar(app=None):
    """Activa el arrastre con el ratón en toda la aplicación (una sola vez)."""
    global _instancia
    app = app or QApplication.instance()
    if _instancia is None and app is not None:
        _instancia = ArrastreRaton(app)
        app.focusWindowChanged.connect(_instancia.vigilar_ventana)
    if _instancia is not None and app is not None:
        for v in app.topLevelWindows():
            _instancia.vigilar_ventana(v)
    return _instancia
