# -*- coding: utf-8 -*-
"""Animación de GIF para los widgets que se pintan a mano (avatar, fondo, vistas del buscador).

`GifVivo(widget, datos)` guarda el QMovie, repinta el widget en cada cuadro y se pausa solo cuando el
widget no se ve o la ventana está minimizada. `imagen()` devuelve el cuadro actual (QImage).
"""

from PySide6.QtCore import QBuffer, QByteArray, QEvent, QIODevice, QObject
from PySide6.QtGui import QImage, QMovie


class GifVivo(QObject):
    def __init__(self, widget, datos, permitido=True):
        super().__init__(widget)
        self.widget = widget
        self.permitido = permitido          # compuerta externa (límite de animaciones simultáneas)
        self._datos = QByteArray(bytes(datos))
        self._buf = QBuffer(self._datos)
        self._buf.open(QIODevice.ReadOnly)
        self.movie = QMovie(self._buf, QByteArray(b"gif"), self)
        self.movie.setCacheMode(QMovie.CacheNone)
        self.valido = self.movie.isValid()
        self._ventana = None
        if not self.valido:
            return
        self.movie.jumpToFrame(0)
        self.movie.frameChanged.connect(self._cambio)
        widget.installEventFilter(self)
        self._enlazar_ventana()
        self.ajustar()

    # ------------------------------------------------------------ cuadro actual
    def imagen(self):
        if not self.valido:
            return QImage()
        return self.movie.currentImage()

    @property
    def animado(self):
        return self.valido and self.movie.frameCount() != 1

    @property
    def corriendo(self):
        return self.valido and self.movie.state() == QMovie.Running

    def _cambio(self, _n):
        try:
            self.widget.update()
        except RuntimeError:
            pass

    # ------------------------------------------------------------ pausa inteligente
    def _enlazar_ventana(self):
        try:
            v = self.widget.window()
        except RuntimeError:
            return
        if v is not None and v is not self._ventana:
            if self._ventana is not None:
                try:
                    self._ventana.removeEventFilter(self)
                except RuntimeError:
                    pass
            self._ventana = v
            v.installEventFilter(self)

    def permitir(self, si):
        if si != self.permitido:
            self.permitido = si
            self.ajustar()

    def debe_correr(self):
        try:
            w = self.widget
            if not (self.permitido and w.isVisible()):
                return False
            v = w.window()
            return not (v.isMinimized() or not v.isVisible())
        except RuntimeError:
            return False

    def ajustar(self):
        if not self.valido or not self.animado:
            return
        if self.debe_correr():
            if self.movie.state() == QMovie.Paused:
                self.movie.setPaused(False)
            elif self.movie.state() == QMovie.NotRunning:
                self.movie.start()
        elif self.movie.state() == QMovie.Running:
            self.movie.setPaused(True)

    def eventFilter(self, obj, ev):
        t = ev.type()
        if not hasattr(self, "widget"):
            return False
        if obj is self.widget and t in (QEvent.Show, QEvent.Hide, QEvent.ParentChange):
            if t != QEvent.Hide:
                self._enlazar_ventana()
            self.ajustar()
        elif obj is self._ventana and t in (QEvent.WindowStateChange, QEvent.Show, QEvent.Hide):
            self.ajustar()
        return False

    def detener(self):
        try:
            self.movie.stop()
            self.widget.removeEventFilter(self)
            if self._ventana is not None:
                self._ventana.removeEventFilter(self)
        except RuntimeError:
            pass
        self.valido = False
        self.deleteLater()
