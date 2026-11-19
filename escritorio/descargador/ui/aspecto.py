# -*- coding: utf-8 -*-
"""Elegir el color y el fondo de Caudal como en el teléfono: círculos de color,
tarjetas de fondo, un color propio para cada cosa y una vista previa que cambia
al momento. «Aplicar ahora» reabre Caudal con los colores nuevos sin cortar la
música (ver Ventana.reabrir_con_aspecto)."""

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractButton, QCheckBox, QColorDialog, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

from .estilos import (ACENTOS, FONDOS, TEMAS, C, acento_de, acento_de_tema, es_color, es_premium, fondo_de,
                      ruta_patron)
from .fondo_capa import pixmap_patron


def nombre_acento(valor):
    if es_premium(valor):
        return "Tema " + acento_de(valor)[0]
    return "Tu color" if es_color(valor) else (ACENTOS.get(valor) or ACENTOS["cian"])[0]


def nombre_fondo(valor):
    if es_premium(valor):
        return "Tema " + fondo_de(valor)[0]
    return "Tu fondo" if es_color(valor) else (FONDOS.get(valor) or FONDOS["oscuro"])[0]


class Muestra(QWidget):
    """Una Caudal en miniatura pintada con la paleta elegida."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setMinimumSize(260, 180)
        self.acento = acento_de("cian")
        self.fondo = fondo_de("oscuro")

    def poner(self, acento, fondo):
        self.acento = acento_de(acento)
        self.fondo = fondo_de(fondo)
        self.update()

    def sizeHint(self):
        return QSize(360, 210)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        _, fondo, panel, sup, sup2, sup3, _hover, borde = self.fondo
        _, ac, ac_alto, _ac_bajo, ac_texto = self.acento
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        marco = QPainterPath()
        marco.addRoundedRect(r, 14, 14)
        p.fillPath(marco, QColor(fondo))
        p.setPen(QPen(QColor(borde), 1))
        p.drawPath(marco)
        m = 8
        bar_h = 38
        # barra lateral
        lat = QRectF(r.left() + m, r.top() + m, r.width() * 0.26, r.height() - bar_h - m * 2.5)
        self._caja(p, lat, panel)
        for i in range(4):
            y = lat.top() + 14 + i * 22
            p.setBrush(QColor(ac if i == 0 else sup3))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(lat.left() + 10, y, 14, 14), 4, 4)
            p.setBrush(QColor(C["texto"] if i == 0 else C["texto3"]))
            p.drawRoundedRect(QRectF(lat.left() + 30, y + 4, lat.width() * 0.45, 6), 3, 3)
        # contenido
        cont = QRectF(lat.right() + m, lat.top(), r.right() - m - lat.right() - m, lat.height())
        self._caja(p, cont, panel)
        # degradado de arriba con el color
        grad_r = QRectF(cont.left() + 10, cont.top() + 10, cont.width() - 20, cont.height() * 0.32)
        p.setBrush(QColor(ac).darker(170))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(grad_r, 8, 8)
        p.setBrush(QColor(C["texto"]))
        p.drawRoundedRect(QRectF(grad_r.left() + 10, grad_r.top() + 12, grad_r.width() * 0.4, 9), 4, 4)
        boton = QRectF(grad_r.left() + 10, grad_r.bottom() - 22, 62, 16)
        p.setBrush(QColor(ac))
        p.drawRoundedRect(boton, 8, 8)
        p.setPen(QColor(ac_texto))
        f = QFont(self.font())
        f.setPointSizeF(6.5)
        f.setBold(True)
        p.setFont(f)
        p.drawText(boton, Qt.AlignCenter, "Escuchar")
        p.setPen(Qt.NoPen)
        # filas de canciones (la que suena, en color)
        for i in range(3):
            y = grad_r.bottom() + 10 + i * 20
            if y + 14 > cont.bottom():
                break
            fila = QRectF(cont.left() + 10, y, cont.width() - 20, 16)
            p.setBrush(QColor(sup2 if i == 0 else sup))
            p.drawRoundedRect(fila, 5, 5)
            p.setBrush(QColor(sup3))
            p.drawRoundedRect(QRectF(fila.left() + 3, fila.top() + 2, 12, 12), 3, 3)
            p.setBrush(QColor(ac if i == 0 else C["texto2"]))
            p.drawRoundedRect(QRectF(fila.left() + 22, fila.top() + 5, fila.width() * 0.38, 6), 3, 3)
        # barra de reproducción
        bar = QRectF(r.left() + m, r.bottom() - bar_h - m * 0.5, r.width() - m * 2, bar_h)
        cx = bar.center().x()
        p.setBrush(QColor(C["texto"]))
        p.drawEllipse(QRectF(cx - 10, bar.top() + 4, 20, 20))
        tri = QPainterPath()
        tri.moveTo(cx - 3, bar.top() + 9)
        tri.lineTo(cx + 5, bar.top() + 14)
        tri.lineTo(cx - 3, bar.top() + 19)
        tri.closeSubpath()
        p.fillPath(tri, QColor(fondo))
        linea = QRectF(cx - bar.width() * 0.28, bar.top() + 30, bar.width() * 0.56, 3)
        p.setBrush(QColor(sup3))
        p.drawRoundedRect(linea, 1.5, 1.5)
        hecho = QRectF(linea.left(), linea.top(), linea.width() * 0.42, 3)
        p.setBrush(QColor(ac_alto))
        p.drawRoundedRect(hecho, 1.5, 1.5)
        p.setBrush(QColor(sup3))
        p.drawRoundedRect(QRectF(bar.left() + 4, bar.top() + 4, 26, 26), 5, 5)
        p.end()

    def _caja(self, p, r, color):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(r, 10, 10)


class Circulo(QAbstractButton):
    """Un color para elegir. Sin color: el arcoíris de «elegir el tuyo»."""

    def __init__(self, color, nombre, padre=None):
        super().__init__(padre)
        self.color = color
        self.setToolTip(nombre)
        self.setAccessibleName(nombre)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(40, 40)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self.color:
            p.setBrush(QColor(self.color))
        else:
            g = QConicalGradient(r.center(), 90)
            for i, c in enumerate(("#FF5C8A", "#FF8A3D", "#F5C542", "#2BD576", "#22D3EE", "#4C8DFF",
                                   "#8B6CFF", "#FF5C8A")):
                g.setColorAt(i / 7, QColor(c))
            p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        p.drawEllipse(r)
        if self.isChecked():
            p.setPen(QPen(QColor(C["texto"]), 2.4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(self.rect()).adjusted(1.2, 1.2, -1.2, -1.2))
            # la marca, del color que se lea encima
            fondo = QColor(self.color or "#888888")
            claro = (0.299 * fondo.red() + 0.587 * fondo.green() + 0.114 * fondo.blue()) > 150
            p.setPen(QPen(QColor("#111111" if claro else "#FFFFFF"), 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            c = r.center()
            path = QPainterPath()
            path.moveTo(c.x() - 6, c.y())
            path.lineTo(c.x() - 2, c.y() + 4)
            path.lineTo(c.x() + 6, c.y() - 4)
            p.drawPath(path)
        elif not self.color:
            p.setPen(QPen(QColor("#FFFFFF"), 2.4, Qt.SolidLine, Qt.RoundCap))
            c = r.center()
            p.drawLine(c.x() - 5, c.y(), c.x() + 5, c.y())
            p.drawLine(c.x(), c.y() - 5, c.x(), c.y() + 5)
        if self.underMouse() and not self.isChecked():
            p.setPen(QPen(QColor(C["texto2"]), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))
        p.end()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class TarjetaFondo(QAbstractButton):
    """Un fondo para elegir: sus capas en pequeño y el nombre debajo."""

    def __init__(self, capas, nombre, padre=None, patron=None):
        super().__init__(padre)
        self.capas = capas
        self.nombre = nombre
        self.patron = patron            # el personaje del fondo (QPixmap) o None
        self.setToolTip(nombre)
        self.setAccessibleName(nombre)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(92, 78)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0, 0, self.width(), 54).adjusted(2, 2, -2, -2)
        if self.capas:
            p.setPen(QPen(QColor(C["texto"] if self.isChecked() else C["borde_claro"]),
                          2.2 if self.isChecked() else 1))
            p.setBrush(QColor(self.capas[0]))
            p.drawRoundedRect(r, 9, 9)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.capas[1]))
            p.drawRoundedRect(QRectF(r.left() + 6, r.top() + 6, r.width() * 0.3, r.height() - 12), 5, 5)
            p.setBrush(QColor(self.capas[1]))
            p.drawRoundedRect(QRectF(r.left() + r.width() * 0.3 + 10, r.top() + 6,
                                     r.width() * 0.7 - 16, r.height() - 12), 5, 5)
            p.setBrush(QColor(self.capas[3]))
            p.drawRoundedRect(QRectF(r.left() + r.width() * 0.3 + 15, r.top() + 12,
                                     r.width() * 0.5, 8), 3, 3)
            p.setBrush(QColor(self.capas[4]))
            p.drawRoundedRect(QRectF(r.left() + r.width() * 0.3 + 15, r.top() + 24,
                                     r.width() * 0.36, 8), 3, 3)
            if self.patron is not None:
                # el personaje, chico, en la esquina (como en la app)
                pm = self.patron
                th = r.height() - 8
                tw = pm.width() * th / max(1, pm.height())
                p.save()
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                p.drawPixmap(QRectF(r.right() - tw - 3, r.bottom() - th - 2, tw, th), pm, QRectF(pm.rect()))
                p.restore()
        else:
            p.setPen(QPen(QColor(C["borde_claro"]), 1.4, Qt.DashLine))
            p.setBrush(QColor(C["superficie"]))
            p.drawRoundedRect(r, 9, 9)
            p.setPen(QPen(QColor(C["texto2"]), 2.2, Qt.SolidLine, Qt.RoundCap))
            c = r.center()
            p.drawLine(c.x() - 7, c.y(), c.x() + 7, c.y())
            p.drawLine(c.x(), c.y() - 7, c.x(), c.y() + 7)
        if self.underMouse() and not self.isChecked():
            p.setPen(QPen(QColor(C["texto2"]), 1.2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(-1, -1, 1, 1), 10, 10)
        p.setPen(QColor(C["texto"] if self.isChecked() else C["texto2"]))
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        f.setBold(self.isChecked())
        p.setFont(f)
        p.drawText(QRectF(0, 56, self.width(), 20), Qt.AlignCenter, self.nombre)
        p.end()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class SelectorAspecto(QWidget):
    """Lo que va en Ajustes › Aspecto."""

    cambio = Signal(str, str)          # acento, fondo (ya guardados en los ajustes)
    aplicar = Signal()

    def __init__(self, ajustes, aplicados, padre=None):
        super().__init__(padre)
        self.a = ajustes
        self.aplicados = tuple(aplicados)        # los que se ven ahora en la app
        self.setAttribute(Qt.WA_StyledBackground, False)
        # como en el teléfono: la vista previa arriba y los colores debajo
        # (cabe igual con el panel derecho abierto o la ventana pequeña)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 8, 0, 12)
        raiz.setSpacing(18)
        self.raiz = raiz

        izq = QVBoxLayout()
        izq.setSpacing(6)
        izq.addWidget(self._titulo("Color", "Botones, lo que suena y los detalles."))
        fila_c = QGridLayout()
        fila_c.setHorizontalSpacing(6)
        fila_c.setVerticalSpacing(6)
        self.circulos = {}
        for i, (clave, v) in enumerate(ACENTOS.items()):
            c = Circulo(v[1], v[0])
            c.clicked.connect(lambda _=False, k=clave: self._elegir_acento(k))
            self.circulos[clave] = c
            fila_c.addWidget(c, 0, i)
        self.circulo_propio = Circulo("", "Elegir tu propio color…")
        self.circulo_propio.clicked.connect(self._acento_propio)
        fila_c.addWidget(self.circulo_propio, 0, len(ACENTOS))
        fila_c.setColumnStretch(len(ACENTOS) + 1, 1)
        izq.addLayout(fila_c)
        izq.addSpacing(10)
        izq.addWidget(self._titulo("Fondo", "El color de fondo de toda la app."))
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(6)
        self.tarjetas = {}
        claves = [(k, v) for k, v in FONDOS.items() if k not in TEMAS]
        for i, (clave, v) in enumerate(claves):
            t = TarjetaFondo(v[1:], v[0])
            t.clicked.connect(lambda _=False, k=clave: self._elegir_fondo(k))
            self.tarjetas[clave] = t
            rejilla.addWidget(t, i // 4, i % 4)
        self.tarjeta_propia = TarjetaFondo(None, "Elegir…")
        self.tarjeta_propia.setToolTip("Elegir tu propio fondo…")
        self.tarjeta_propia.clicked.connect(self._fondo_propio)
        rejilla.addWidget(self.tarjeta_propia, len(claves) // 4, len(claves) % 4)
        rejilla.setColumnStretch(4, 1)
        izq.addLayout(rejilla)
        # fondos con personaje: su paleta, su acento y su dibujito detrás de toda la app
        izq.addSpacing(10)
        izq.addWidget(self._titulo("Con personajes", "Sus colores y el personaje sobre la barra; si tienes mascotas, "
                                                    "también camina por ella. Arrastra al personaje adonde "
                                                    "quieras, gira la rueda sobre él para cambiar su tamaño y "
                                                    "haz doble clic para devolverlo a su esquina."))
        rejilla_t = QGridLayout()
        rejilla_t.setHorizontalSpacing(8)
        rejilla_t.setVerticalSpacing(6)
        for i, (clave, v) in enumerate(TEMAS.items()):
            t = TarjetaFondo(FONDOS[clave][1:], v[0], patron=pixmap_patron(ruta_patron(clave)))
            t.clicked.connect(lambda _=False, k=clave: self._elegir_fondo(k))
            self.tarjetas[clave] = t
            rejilla_t.addWidget(t, i // 4, i % 4)
        rejilla_t.setColumnStretch(4, 1)
        izq.addLayout(rejilla_t)
        # uno bajo el otro: en una sola fila no cabrían con el panel derecho abierto
        self.baila = QCheckBox("Que baile con la música")
        self.baila.setChecked(bool(self.a.get("personaje_baila", True)))
        self.baila.toggled.connect(self._baile_cambiado)
        izq.addWidget(self.baila)
        self.bt_esquina = QPushButton("Devolverlo a su esquina")
        self.bt_esquina.setObjectName("contorno")
        self.bt_esquina.setCursor(Qt.PointingHandCursor)
        self.bt_esquina.clicked.connect(self._personaje_a_su_esquina)
        izq.addWidget(self.bt_esquina, 0, Qt.AlignLeft)
        izq.addStretch(1)
        self.izq = izq

        der = QVBoxLayout()
        der.setSpacing(10)
        self.muestra = Muestra()
        self.muestra.setFixedHeight(200)
        self.muestra.setMaximumWidth(560)
        der.addWidget(self.muestra)
        self.estado = QLabel()
        self.estado.setWordWrap(True)
        self.estado.setObjectName("secundario")
        der.addWidget(self.estado)
        botones = QHBoxLayout()
        botones.setSpacing(8)
        self.bt_original = QPushButton("Volver al original")
        self.bt_original.setObjectName("contorno")
        self.bt_original.setCursor(Qt.PointingHandCursor)
        self.bt_original.clicked.connect(self._original)
        self._fila_botones = botones
        self.bt_aplicar = QPushButton("Aplicar ahora")
        self.bt_aplicar.setObjectName("principal")
        self.bt_aplicar.setCursor(Qt.PointingHandCursor)
        self.bt_aplicar.setToolTip("Caudal se vuelve a abrir en un momento con estos colores; "
                                   "la música sigue donde iba")
        self.bt_aplicar.clicked.connect(self.aplicar.emit)
        botones.addWidget(self.bt_aplicar)
        botones.addWidget(self.bt_original)
        botones.addStretch(1)
        der.addLayout(botones)
        self.der = der
        raiz.addLayout(der)
        raiz.addLayout(izq)
        self._refrescar()

    def _titulo(self, t, ayuda):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 2)
        v.setSpacing(1)
        a = QLabel(t)
        a.setStyleSheet("font-size:14px;font-weight:600;")
        v.addWidget(a)
        b = QLabel(ayuda)
        b.setObjectName("secundario")
        b.setWordWrap(True)          # que una ayuda larga no ensanche todo Ajustes
        v.addWidget(b)
        return w

    # ------------------------------------------------------------ elegir
    def _guardar(self, clave, valor):
        self.a[clave] = valor
        self.a.guardar()
        self._refrescar()
        self.cambio.emit(self.a["acento"], self.a["fondo"])

    def _elegir_acento(self, k):
        self._guardar("acento", k)

    def _elegir_fondo(self, k):
        # un fondo con personaje trae su color (luego se puede cambiar)
        if acento_de_tema(k):
            self.a["acento"] = acento_de_tema(k)
        self._guardar("fondo", k)

    def _personaje(self):
        """El personaje vivo de la ventana (None si esta pantalla se abre suelta, p. ej. en pruebas)."""
        return getattr(self.window(), "personaje_fondo", None)

    def _baile_cambiado(self, activo):
        self.a["personaje_baila"] = bool(activo)
        self.a.guardar()
        pj = self._personaje()
        if pj is not None:
            pj.actualizar_baile()

    def _personaje_a_su_esquina(self):
        pj = self._personaje()
        if pj is not None:
            pj.volver_a_la_esquina()
            return
        self.a["personaje_x"] = self.a["personaje_y"] = -1
        self.a.guardar()

    def _acento_propio(self):
        inicial = QColor(acento_de(self.a["acento"])[1])
        color = QColorDialog.getColor(inicial, self, "Tu color para Caudal")
        if color.isValid():
            self._guardar("acento", color.name().upper())
        else:
            self._refrescar()

    def _fondo_propio(self):
        inicial = QColor(fondo_de(self.a["fondo"])[2])
        color = QColorDialog.getColor(inicial, self, "Tu fondo para Caudal")
        if color.isValid():
            self._guardar("fondo", color.name().upper())
        else:
            self._refrescar()

    def _original(self):
        self.a["acento"] = "cian"
        self._guardar("fondo", "oscuro")

    # ------------------------------------------------------------ pintar
    def _refrescar(self):
        acento, fondo = self.a["acento"], self.a["fondo"]
        for k, c in self.circulos.items():
            c.setChecked(k == acento)
            c.update()
        propio = es_color(acento)
        self.circulo_propio.color = acento_de(acento)[1] if propio else ""
        self.circulo_propio.setChecked(propio)
        self.circulo_propio.setToolTip("Tu color (pulsa para cambiarlo)" if propio else "Elegir tu propio color…")
        self.circulo_propio.update()
        for k, t in self.tarjetas.items():
            t.setChecked(k == fondo)
            t.update()
        propio_f = es_color(fondo)
        self.tarjeta_propia.capas = fondo_de(fondo)[1:] if propio_f else None
        self.tarjeta_propia.nombre = "Tu fondo" if propio_f else "Elegir…"
        self.tarjeta_propia.setChecked(propio_f)
        self.tarjeta_propia.update()
        self.muestra.poner(acento, fondo)
        pendiente = (acento, fondo) != self.aplicados
        self.bt_aplicar.setVisible(pendiente)
        self.bt_original.setEnabled((acento, fondo) != ("cian", "oscuro"))
        texto = f"<b>{nombre_acento(acento)}</b> sobre <b>{nombre_fondo(fondo)}</b>."
        if pendiente:
            texto += ("<br>Así se verá. Pulsa «Aplicar ahora»: Caudal se reabre en un momento "
                      "con estos colores y la música sigue donde iba.")
        else:
            texto += "<br>Es el aspecto que tienes ahora."
        self.estado.setText(texto)
