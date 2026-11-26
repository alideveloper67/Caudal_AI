# -*- coding: utf-8 -*-
"""El botón de Cast de la barra de reproducción: busca las teles, Chromecast y
altavoces de la red de casa y manda allí la música (ver cast.py).

Si pychromecast no está instalado, el botón no aparece."""

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from .estilos import C


def pintar_cast(p, r, color, conectado=False, grosor=1.8):
    """El icono de Cast (pantalla con ondas) dentro del rectángulo ``r``."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), grosor)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    # la pantalla: abierta abajo a la izquierda, donde salen las ondas
    marco = QPainterPath()
    marco.moveTo(x + w * 0.08, y + h * 0.36)
    marco.lineTo(x + w * 0.08, y + h * 0.2)
    marco.lineTo(x + w * 0.92, y + h * 0.2)
    marco.lineTo(x + w * 0.92, y + h * 0.84)
    marco.lineTo(x + w * 0.58, y + h * 0.84)
    p.drawPath(marco)
    esquina = QPointF(x + w * 0.08, y + h * 0.84)
    for radio in (0.16, 0.32, 0.48):
        rr = w * radio
        p.drawArc(QRectF(esquina.x() - rr, esquina.y() - rr, rr * 2, rr * 2), 0, 90 * 16)
    p.setBrush(QColor(color))
    p.drawEllipse(esquina, w * 0.035, w * 0.035)
    if conectado:
        p.setPen(Qt.NoPen)
        c = QColor(color)
        c.setAlpha(150)
        p.setBrush(c)
        p.drawRect(QRectF(x + w * 0.24, y + h * 0.32, w * 0.56, h * 0.4))
    p.restore()


class BotonCast(QPushButton):
    """El icono de Cast: gris sin conexión, del color de acento conectado y
    parpadeando mientras conecta."""

    def __init__(self, control, lado=32, padre=None):
        super().__init__(padre)
        self.control = control
        self.setFixedSize(lado, lado)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._encima = False
        self._fase = True
        self._parpadeo = QTimer(self)
        self._parpadeo.setInterval(450)
        self._parpadeo.timeout.connect(self._parpadear)
        self._hoja = None
        self.clicked.connect(self.abrir)
        control.cambio.connect(self._actualizar)
        self._actualizar()

    def _parpadear(self):
        self._fase = not self._fase
        self.update()

    def _actualizar(self):
        c = self.control
        self.setVisible(bool(c.soportado))
        if c.activo:
            self.setToolTip(f"Sonando en {c.dispositivo.nombre if c.dispositivo else 'la tele'}")
        else:
            self.setToolTip("Enviar a una tele o altavoz")
        if c.conexion == "conectando":
            self._parpadeo.start()
        else:
            self._parpadeo.stop()
            self._fase = True
        self.update()

    def enterEvent(self, e):
        self._encima = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._encima = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _e):
        p = QPainter(self)
        activo = self.control.activo
        color = C["acento"] if activo else (C["texto"] if self._encima else C["texto2"])
        if not self._fase:
            q = QColor(color)
            q.setAlpha(90)
            color = q.name(QColor.HexArgb)
        lado = min(self.width(), self.height()) * 0.56
        r = QRectF((self.width() - lado) / 2, (self.height() - lado) / 2, lado, lado)
        pintar_cast(p, r, color, conectado=activo)
        p.end()

    def abrir(self):
        try:
            if self._hoja is not None and self._hoja.isVisible():
                self._hoja.close()
                return
        except RuntimeError:                 # la hoja ya se había destruido sola
            self._hoja = None
        self._hoja = HojaCast(self.control, self.window())
        self._hoja.mostrar_junto_a(self)


class HojaCast(QFrame):
    """La ventanita que sale del botón: la lista de aparatos o, si ya suena en
    la tele, su volumen y el botón para volver a la PC."""

    PACIENCIA_MS = 8000

    def __init__(self, control, padre=None):
        super().__init__(padre, Qt.Popup | Qt.FramelessWindowHint)
        self.control = control
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("hojaCast")
        self.setStyleSheet(
            f"#hojaCast{{background:{C['superficie2']};border:1px solid {C['borde']};border-radius:12px;}}"
            f"QLabel{{color:{C['texto']};background:transparent;}}"
            f"QLabel#ayudaCast{{color:{C['texto2']};}}"
            f"QPushButton#aparato{{background:transparent;border:none;border-radius:8px;color:{C['texto']};"
            f"text-align:left;padding:8px 10px;font-size:13.5px;}}"
            f"QPushButton#aparato:hover{{background:{C['superficie']};}}"
            f"QPushButton#volver{{background:{C['acento']};color:#03222B;border:none;border-radius:16px;"
            f"padding:8px 14px;font-weight:600;}}")
        self.setFixedWidth(320)
        self._esperado = False
        self._caja = QVBoxLayout(self)
        self._caja.setContentsMargins(14, 12, 14, 14)
        self._caja.setSpacing(6)
        self._paciencia = QTimer(self)
        self._paciencia.setSingleShot(True)
        self._paciencia.timeout.connect(self._ya_esperado)
        control.cambio.connect(self._pintar)
        if not control.activo:
            control.buscar_dispositivos()
            self._paciencia.start(self.PACIENCIA_MS)
        self._pintar()

    def _ya_esperado(self):
        self._esperado = True
        self._pintar()

    def _limpiar(self):
        while self._caja.count():
            it = self._caja.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            elif it.layout() is not None:
                lay = it.layout()
                while lay.count():
                    x = lay.takeAt(0).widget()
                    if x is not None:
                        x.setParent(None)
                        x.deleteLater()

    def _titulo(self, texto):
        t = QLabel(texto)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:15px;font-weight:700;")
        self._caja.addWidget(t)

    def _ayuda(self, texto):
        a = QLabel(texto)
        a.setObjectName("ayudaCast")
        a.setWordWrap(True)
        self._caja.addWidget(a)

    def _pintar(self):
        self._limpiar()
        c = self.control
        if c.activo:
            nombre = c.dispositivo.nombre if c.dispositivo else "la tele"
            self._titulo(f"Sonando en {nombre}")
            fila = QHBoxLayout()
            fila.addWidget(QLabel("Volumen"))
            vol = QSlider(Qt.Horizontal)
            vol.setRange(0, 100)
            vol.setValue(round(c.volumen * 100))
            vol.valueChanged.connect(lambda v: c.fijar_volumen(v / 100))
            fila.addWidget(vol, 1)
            self._caja.addLayout(fila)
            volver = QPushButton("Volver a escuchar en la PC")
            volver.setObjectName("volver")
            volver.setCursor(Qt.PointingHandCursor)
            volver.clicked.connect(self._volver)
            self._caja.addWidget(volver)
        else:
            self._titulo("Escuchar en otro aparato")
            lista = c.dispositivos
            if not lista:
                if self._esperado:
                    self._ayuda("No encuentro ninguna tele ni altavoz. La PC y la tele tienen que estar "
                                "conectadas a la misma red (la misma wifi o el mismo router).")
                else:
                    self._ayuda("Buscando teles y altavoces…")
            for d in lista:
                texto = d.nombre + (f"   ·   {d.modelo}" if d.modelo else "")
                b = QPushButton(("Altavoz:  " if d.es_altavoz else "") + texto)
                b.setObjectName("aparato")
                b.setCursor(Qt.PointingHandCursor)
                conectando = c.conexion == "conectando" and c.dispositivo == d
                if conectando:
                    b.setText(b.text() + "   (conectando…)")
                b.setEnabled(c.conexion != "conectando")
                b.clicked.connect(lambda _=False, d=d: self._conectar(d))
                self._caja.addWidget(b)
        self.adjustSize()

    def _conectar(self, d):
        self.control.conectar(d)
        self.close()

    def _volver(self):
        self.control.desconectar()
        self.close()

    def mostrar_junto_a(self, boton):
        self.adjustSize()
        abajo_izq = boton.mapToGlobal(QPoint(boton.width(), 0))
        x = abajo_izq.x() - self.width()
        y = abajo_izq.y() - self.height() - 8
        self.move(max(0, x), max(0, y))
        self.show()

    def closeEvent(self, e):
        try:
            self.control.cambio.disconnect(self._pintar)
        except (RuntimeError, TypeError):
            pass
        self.control.dejar_de_buscar()
        super().closeEvent(e)


def boton_cast(control, lado=32):
    """El botón listo para poner en una barra (oculto si no hay Cast)."""
    return BotonCast(control, lado)


__all__ = ["BotonCast", "HojaCast", "boton_cast", "pintar_cast"]
