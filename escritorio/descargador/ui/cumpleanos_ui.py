# -*- coding: utf-8 -*-
"""«Feliz cumpleaños» en el escritorio: el gorrito, la pantalla de celebración, el aviso de Inicio.

Todo ligero: el gorrito es un dibujo vectorial, el confeti lo mueve UN reloj que solo corre mientras la
pantalla se ve, y con el modo ligero queda quieto. Igual que app/lib/ui/cumpleanos.dart."""

import math
import random

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPolygonF, QPixmap)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
                               QWidget)

from .. import cumpleanos as CU
from ..cumpleanos import ESTADO

ROSA = QColor("#FF4FA3")
VIOLETA = QColor("#7C5CFF")
ORO = QColor("#FFC857")
CIAN = QColor("#3DDCFF")
COLORES_CONFETI = (ROSA, ORO, CIAN, VIOLETA, QColor("#7CFFB2"), QColor("#FFFFFF"))


def pintar_gorro(p, base_x, base_y, ancho, inclinacion=-11.5):
    """Dibuja el gorrito con la base centrada en (base_x, base_y) y `ancho` de ancho (rayas y pompón)."""
    if ancho < 4:
        return
    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    p.translate(base_x, base_y)
    p.rotate(inclinacion)
    mitad, alto = ancho / 2, ancho * 1.1
    cono = QPainterPath()
    cono.moveTo(-mitad, 0)
    cono.lineTo(mitad, 0)
    cono.lineTo(ancho * 0.03, -alto)
    cono.closeSubpath()
    deg = QLinearGradient(-mitad, -alto, mitad, 0)
    deg.setColorAt(0.0, ROSA)
    deg.setColorAt(1.0, VIOLETA)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(deg))
    p.drawPath(cono)
    # rayas amarillas recortadas al cono
    p.save()
    p.setClipPath(cono)
    pluma = QPen(ORO)
    pluma.setWidthF(max(1.2, ancho * 0.11))
    p.setPen(pluma)
    for f in (0.28, 0.58):
        p.drawLine(QPointF(-mitad, -alto * f + ancho * 0.12), QPointF(mitad, -alto * f - ancho * 0.12))
    p.restore()
    p.setPen(Qt.NoPen)
    p.setBrush(CIAN)
    p.drawRoundedRect(QRectF(-mitad - ancho * 0.03, -ancho * 0.07, ancho * 1.06, ancho * 0.12),
                      ancho * 0.05, ancho * 0.05)
    p.setBrush(ORO)
    r = ancho * 0.12
    p.drawEllipse(QPointF(ancho * 0.03, -alto), r, r)
    p.restore()


def pintar_gorro_en_avatar(p, lado):
    """El gorrito sobre un avatar redondo de `lado` px (dentro de su cuadro, arriba a la derecha)."""
    if lado < 18:
        return
    ancho = lado * 0.40
    pintar_gorro(p, lado * 0.62, lado * 0.40, ancho)


# ============================================================ pantalla de celebración

class _Figura(QWidget):
    """La mascota de la persona (o el personaje de su fondo, o una tarta) con el gorrito puesto."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lado = 200
        self._personaje = None
        self.setFixedSize(self.lado, self.lado)

    def fijar_lado(self, lado):
        lado = int(max(110, min(230, lado)))
        if lado != self.lado:
            self.lado = lado
            self.setFixedSize(lado, lado)
            self.update()

    def _datos_mascota(self):
        gm = getattr(self.ctx, "mascota", None)
        try:
            return gm.datos() if gm is not None else None
        except Exception:  # noqa: BLE001
            return None

    def _pixmap_personaje(self):
        if self._personaje is None:
            try:
                from ..ui import estilos
                ruta = estilos.patron_actual()
                self._personaje = QPixmap(str(ruta)) if ruta else QPixmap()
            except Exception:  # noqa: BLE001
                self._personaje = QPixmap()
        return self._personaje

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = h = self.lado
        datos = self._datos_mascota()
        if datos:
            from .. import mascotas
            esc = max(1, int((h * 0.78) / max(1, datos["alto"])))
            mascotas.pintar(p, datos, w / 2, h - 4, 0, w, 0, 0, esc)
            ancho_m = datos["ancho"] * esc
            alto_m = datos["alto"] * esc
            pintar_gorro(p, w / 2 + ancho_m * 0.05, h - 4 - alto_m + alto_m * 0.1, ancho_m * 0.34)
            return
        pm = self._pixmap_personaje()
        if pm is not None and not pm.isNull():
            esc = pm.scaled(int(w * 0.8), int(h * 0.8), Qt.KeepAspectRatio, Qt.FastTransformation)
            p.drawPixmap(int((w - esc.width()) / 2), h - esc.height() - 4, esc)
            pintar_gorro(p, w / 2, h - esc.height() - 4 + esc.height() * 0.06, w * 0.24)
            return
        # sin mascota ni personaje: una tarta con vela
        c = QPointF(w / 2, h * 0.62)
        r = w * 0.31
        p.setPen(Qt.NoPen)
        deg = QLinearGradient(0, c.y() - r, 0, c.y() + r)
        deg.setColorAt(0, ROSA)
        deg.setColorAt(1, VIOLETA)
        p.setBrush(QBrush(deg))
        p.drawEllipse(c, r, r)
        # una carita contenta: dos ojos y una sonrisa
        p.setBrush(QColor("#FFFFFF"))
        for dx in (-0.36, 0.36):
            p.drawEllipse(QPointF(c.x() + r * dx, c.y() - r * 0.12), r * 0.13, r * 0.17)
        p.setBrush(Qt.NoBrush)
        boca = QPen(QColor("#FFFFFF"))
        boca.setWidthF(max(2.0, r * 0.1))
        boca.setCapStyle(Qt.RoundCap)
        p.setPen(boca)
        p.drawArc(QRectF(c.x() - r * 0.34, c.y() + r * 0.02, r * 0.68, r * 0.42), 200 * 16, 140 * 16)
        p.setPen(Qt.NoPen)
        pintar_gorro(p, c.x() + r * 0.1, c.y() - r * 0.78, w * 0.28)


class PantallaCumple(QWidget):
    """«¡Feliz cumpleaños, X!»: cubre toda la ventana, con confeti, la edad y la mascota con gorro."""

    cerrada = Signal()
    N_CONFETI = 56

    def __init__(self, padre, nombre="", edad=None, ctx=None, quieto=False):
        super().__init__(padre)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.quieto = bool(quieto)
        self._t = 0.35 if quieto else 0.0
        rnd = random.Random(7)
        # (x 0..1, fase 0..1, vueltas 1..3, tamaño, vaivén, giro, color) de cada pieza: fijo, sin estado
        self._piezas = [(rnd.random(), rnd.random(), 1 + i % 3, 5 + rnd.random() * 5, rnd.random(),
                         rnd.random() * 6, COLORES_CONFETI[i % len(COLORES_CONFETI)])
                        for i in range(self.N_CONFETI)]
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 16, 24, 16)
        v.setSpacing(0)
        v.addStretch(1)
        self.figura = _Figura(ctx, self)
        v.addWidget(self.figura, 0, Qt.AlignHCenter)
        v.addSpacing(14)
        nombre = (nombre or "").strip()
        self.titulo = QLabel(f"¡Feliz cumpleaños, {nombre}!" if nombre else "¡Feliz cumpleaños!")
        self.titulo.setWordWrap(True)
        self.titulo.setAlignment(Qt.AlignCenter)
        self.titulo.setStyleSheet("background:transparent;color:#FFFFFF;font-size:30px;font-weight:900;")
        v.addWidget(self.titulo)
        self.edad = QLabel(f"Hoy cumples {edad}" if edad else "")
        self.edad.setAlignment(Qt.AlignCenter)
        self.edad.setStyleSheet("background:transparent;color:#FFC857;font-size:19px;font-weight:700;")
        self.edad.setVisible(bool(edad))
        v.addSpacing(8)
        v.addWidget(self.edad)
        self.mensaje = QLabel("Que la música no pare.")
        self.mensaje.setWordWrap(True)
        self.mensaje.setAlignment(Qt.AlignCenter)
        self.mensaje.setStyleSheet("background:transparent;color:#D5CCF5;font-size:14px;")
        v.addSpacing(6)
        v.addWidget(self.mensaje)
        v.addSpacing(24)
        self.boton = QPushButton("¡Gracias!")
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.setFixedSize(220, 50)
        self.boton.setStyleSheet("QPushButton{background:#FF4FA3;color:white;border:none;border-radius:25px;"
                                 "font-size:17px;font-weight:800;}QPushButton:hover{background:#FF6FB5;}")
        self.boton.clicked.connect(self.cerrar)
        v.addWidget(self.boton, 0, Qt.AlignHCenter)
        v.addStretch(1)
        self._reloj = QTimer(self)
        self._reloj.setInterval(40)
        self._reloj.timeout.connect(self._paso)
        self._ajustar()

    # ---- animación (solo mientras se ve)
    def showEvent(self, e):
        super().showEvent(e)
        if not self.quieto:
            self._reloj.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._reloj.stop()

    def _paso(self):
        self._t = (self._t + 0.04 / 9.0) % 1.0
        self.update()

    def cerrar(self):
        self._reloj.stop()
        self.hide()
        self.cerrada.emit()
        self.deleteLater()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            self.cerrar()
        else:
            super().keyPressEvent(e)

    # ---- tamaño: en ventanas bajitas se encoge la figura y se aprietan los textos
    def _ajustar(self):
        alto = max(1, self.height())
        self.figura.fijar_lado(alto * 0.30)
        chico = self.width() < 420 or alto < 480
        self.titulo.setStyleSheet("background:transparent;color:#FFFFFF;font-weight:900;"
                                  f"font-size:{24 if chico else 30}px;")
        self.mensaje.setVisible(alto >= 380)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar()

    # ---- dibujo
    def paintEvent(self, _e):
        p = QPainter(self)
        deg = QLinearGradient(0, 0, 0, self.height())
        deg.setColorAt(0.0, QColor("#3A1D78"))
        deg.setColorAt(1.0, QColor("#1B1140"))
        p.fillRect(self.rect(), deg)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        w, h = self.width(), self.height()
        for i, (x0, fase, vueltas, tam, vaiven, giro, color) in enumerate(self._piezas):
            y = ((self._t * vueltas + fase) % 1.0) * (h + 40) - 20
            x = x0 * w + math.sin((self._t * vueltas + vaiven) * math.tau * 2) * 14
            c = QColor(color)
            c.setAlpha(230)
            p.setBrush(c)
            p.save()
            p.translate(x, y)
            p.rotate(math.degrees((self._t * vueltas * 6 + giro) * (1 if i % 2 == 0 else -1)))
            if i % 4 == 0:
                p.drawEllipse(QPointF(0, 0), tam * 0.45, tam * 0.45)
            else:
                p.drawRect(QRectF(-tam / 2, -tam / 4, tam, tam / 2))
            p.restore()


class _SigueAlPadre(QObject):
    """Mantiene la pantalla del tamaño de la ventana (cuando cambia de tamaño)."""

    def __init__(self, pantalla, padre):
        super().__init__(pantalla)
        self.pantalla = pantalla
        padre.installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Resize:
            self.pantalla.setGeometry(obj.rect())
        return False


def mostrar_celebracion(ventana, ctx=None):
    """Enseña la pantalla de celebración sobre toda la ventana. Devuelve el widget (o None si falla)."""
    try:
        quieto = False
        aj = getattr(ctx, "ajustes", None)
        if aj is not None:
            try:
                quieto = bool(aj["modo_ligero"])
            except Exception:  # noqa: BLE001
                quieto = False
        pantalla = PantallaCumple(ventana, ESTADO.nombre, ESTADO.edad, ctx, quieto=quieto)
        pantalla.setGeometry(ventana.rect())
        _SigueAlPadre(pantalla, ventana)
        pantalla.show()
        pantalla.raise_()
        pantalla.setFocus()
        return pantalla
    except Exception:  # noqa: BLE001 - una fiesta nunca debe romper la app
        return None


# ============================================================ aviso en Inicio

class AvisoCumple(QWidget):
    """«Hoy es tu cumple 🎂» y «Hoy es el cumple de X: ¡salúdalo!» con botón para escribirle.
    No ocupa nada si no hay nada que decir."""

    def __init__(self, ctx, padre=None, amigos_de_prueba=None):
        super().__init__(padre)
        self.ctx = ctx
        self._amigos = amigos_de_prueba          # lista de personas ({id, usuario, nombre...}) o None
        self._pedidos = "*" if amigos_de_prueba is not None else ""
        self._cargando = False
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 4, 0, 8)
        self.v.setSpacing(8)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        ESTADO.cambiado.connect(self._rehacer)
        self._rehacer()

    def _limpiar(self):
        while self.v.count():
            it = self.v.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _rehacer(self):
        ids = ESTADO.amigos_hoy
        self._limpiar()
        if ESTADO.es_mio_hoy:
            self.v.addWidget(_BannerMiCumple())
        amigos = [a for a in (self._amigos or []) if a.get("id") in ids]
        for a in amigos[:3]:
            self.v.addWidget(self._fila_amigo(a))
        if len(amigos) > 3:
            mas = QLabel(f"y {len(amigos) - 3} amigos más cumplen hoy")
            mas.setObjectName("secundario")
            self.v.addWidget(mas)
        self.setVisible(self.v.count() > 0)
        if ids and self._pedidos != "*" and self._pedidos != ",".join(sorted(ids)):
            QTimer.singleShot(0, self._pedir_amigos)

    def _pedir_amigos(self):
        ids = ESTADO.amigos_hoy
        clave = ",".join(sorted(ids))
        if not ids or self._cargando or clave == self._pedidos or self._pedidos == "*":
            return
        from .. import social as S
        s = S.social_de(self.ctx)
        if s is None:
            return
        from ..hilos import en_segundo_plano
        self._cargando = True

        def listo(lista):
            self._cargando = False
            self._pedidos = clave
            self._amigos = list(lista or [])
            self._rehacer()

        def fallo(_e):
            self._cargando = False        # sin red: no hay aviso; se reintenta cuando cambie algo

        en_segundo_plano(s.mis_amigos, ok=listo, error=fallo, dueno=self)

    def _fila_amigo(self, a):
        from .. import social as S
        marco = QFrame()
        marco.setObjectName("aviso_cumple_amigo")
        marco.setStyleSheet("QFrame#aviso_cumple_amigo{border:1px solid rgba(255,79,163,0.55);"
                            "border-radius:14px;background:rgba(255,255,255,0.04);}"
                            "QFrame#aviso_cumple_amigo QLabel{border:none;background:transparent;}")
        h = QHBoxLayout(marco)
        h.setContentsMargins(14, 8, 8, 8)
        h.setSpacing(10)
        gorro = _GorroSuelto(22)
        h.addWidget(gorro)
        t = QLabel(f"Hoy es el cumple de {S.nombre_visible(a)}: ¡salúdalo!")
        t.setWordWrap(True)
        t.setStyleSheet("font-weight:700;")
        h.addWidget(t, 1)
        b = QPushButton("Escribirle")
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("QPushButton{background:transparent;color:#FF4FA3;border:none;font-weight:800;"
                        "padding:6px 10px;}QPushButton:hover{color:#FF7FBF;}")
        b.clicked.connect(lambda _=False, a=a: self.escribir(a))
        h.addWidget(b)
        marco.boton = b
        return marco

    def escribir(self, a):
        """Abre el chat con esa persona (el que ya existe en Mensajes)."""
        from .. import social as S
        self.ctx.chat_pendiente = {"id": a["id"], "usuario": a.get("usuario", ""), "nombre": a.get("nombre", ""),
                                   "visible": S.nombre_visible(a)}
        self.ctx.navegar({"pagina": "mensajes"})


class _GorroSuelto(QWidget):
    def __init__(self, ancho, padre=None):
        super().__init__(padre)
        self.ancho = ancho
        self.setFixedSize(int(ancho * 1.3), int(ancho * 1.4))
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _e):
        p = QPainter(self)
        pintar_gorro(p, self.width() / 2, self.height() - 2, self.ancho)


class _BannerMiCumple(QFrame):
    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("banner_mi_cumple")
        self.setStyleSheet("QFrame#banner_mi_cumple{border-radius:16px;background:qlineargradient("
                           "x1:0,y1:0,x2:1,y2:0,stop:0 #FF4FA3,stop:1 #7C5CFF);}"
                           "QFrame#banner_mi_cumple QLabel{background:transparent;color:white;border:none;}")
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(10)
        h.addWidget(_GorroSuelto(24))
        t = QLabel("Hoy es tu cumple 🎂")
        t.setWordWrap(True)
        t.setStyleSheet("font-size:16px;font-weight:900;")
        h.addWidget(t, 1)
