# -*- coding: utf-8 -*-
"""Aviso de novedades grande.

Una pantalla casi completa, con degradado del color de acento y tarjetas que
aparecen una a una. Sale:

* una sola vez por versión, al abrir la app por primera vez tras actualizar
  (se guarda la última versión vista en los ajustes), con el botón «Empezar»;
* en lugar del aviso normal de actualización cuando las notas de la release
  empiezan con la línea `[grande]`, con el botón «Actualizar ahora».

No pausa ni corta la música. Todo se pinta con la paleta viva (`C`), así que
sigue el color y el fondo que se elijan, incluso con el aviso abierto.
"""

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRectF, QTimer, Qt,
                            QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from .. import version as _version
from .componentes import fuente
from .estilos import C

TITULO = "La actualización más grande de Caudal"
SUBTITULO = "Perfiles, amigos, tu propia música y un DJ dentro de la app"

# (icono, titular, texto)
TARJETAS = [
    ("personas", "Perfiles de verdad",
     "Foto, descripción, canción favorita con su carátula, color propio e insignias."),
    ("usuario_mas", "Amigos con solicitud",
     "Nadie te escribe sin tu permiso: primero llega una solicitud."),
    ("brujula", "Descubre gente",
     "El directorio de perfiles, me gusta y la nota ARTISTA al llegar a 200."),
    ("nube", "Sube tu música",
     "Con carátula y álbum. La escucha toda la comunidad."),
    ("discos", "Mezclador",
     "Un DJ automático y tu propia mesa para mezclar a tu gusto."),
    ("reloj", "Tu mes pasado",
     "Una lista con lo que más escuchaste el mes pasado."),
    ("paleta", "Colores al instante",
     "El color y el fondo cambian sin cerrar Caudal."),
    ("estrella", "Logo nuevo",
     "Y la versión siempre a la vista, abajo a la izquierda."),
]


# ================================================================ cuándo sale

def toca_presentacion(ajustes, version_actual=None):
    """True si hay que enseñar la segunda actualización grande (la presentación a pantalla
    completa): la versión instalada ya es de esa edición o posterior y la última presentación
    vista es anterior. Quien ya la vio no la vuelve a ver con los parches siguientes."""
    actual = version_actual or _version.VERSION
    if not _version.alcanza_edicion(actual):
        return False
    return not _version.alcanza_edicion(str(ajustes["version_novedades_vista"] or ""))


def debe_mostrarse(ajustes, version_actual=None):
    """True si esta versión aún no ha enseñado su aviso."""
    actual = version_actual or _version.VERSION
    if _version.alcanza_edicion(actual):
        # desde la edición grande, el aviso es la presentación y sale una sola vez
        return toca_presentacion(ajustes, actual)
    return str(ajustes["version_novedades_vista"] or "") != str(actual)


def marcar_vista(ajustes, version_actual=None):
    ajustes["version_novedades_vista"] = str(version_actual or _version.VERSION)
    ajustes.guardar()


# ================================================================ pintura

def _color(hexa, alfa=255):
    c = QColor(hexa)
    c.setAlpha(alfa)
    return c


def _mezcla(a, b, t):
    """De a hacia b (t = 0 → a, t = 1 → b)."""
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))


def dibujar_icono(p, nombre, rect, color, grosor=1.9):
    """Dibuja el icono en un lienzo de 24x24 ajustado a `rect`."""
    p.save()
    p.translate(rect.x(), rect.y())
    e = min(rect.width(), rect.height()) / 24.0
    p.scale(e, e)
    lapiz = QPen(QColor(color))
    lapiz.setWidthF(grosor)
    lapiz.setCapStyle(Qt.RoundCap)
    lapiz.setJoinStyle(Qt.RoundJoin)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)
    P = QPointF
    if nombre == "personas":
        p.drawEllipse(P(9, 8), 3.3, 3.3)
        p.drawArc(QRectF(3, 14, 12, 12), 20 * 16, 140 * 16)
        p.drawEllipse(P(17, 9.5), 2.6, 2.6)
        p.drawArc(QRectF(13.5, 14.5, 9, 9), 25 * 16, 130 * 16)
    elif nombre == "usuario_mas":
        p.drawEllipse(P(10, 8), 3.8, 3.8)
        p.drawArc(QRectF(2.5, 14, 15, 14), 20 * 16, 140 * 16)
        p.drawLine(P(19, 5.5), P(19, 11.5))
        p.drawLine(P(16, 8.5), P(22, 8.5))
    elif nombre == "brujula":
        p.drawEllipse(P(12, 12), 9, 9)
        ruta = QPainterPath()
        ruta.moveTo(15.5, 8.5)
        ruta.lineTo(13.4, 13.4)
        ruta.lineTo(8.5, 15.5)
        ruta.lineTo(10.6, 10.6)
        ruta.closeSubpath()
        p.drawPath(ruta)
    elif nombre == "nube":
        ruta = QPainterPath()
        ruta.moveTo(7, 18)
        ruta.cubicTo(3.5, 18, 2.5, 13.5, 6, 12.2)
        ruta.cubicTo(6.2, 8.2, 11.6, 6.2, 14.2, 9.4)
        ruta.cubicTo(18.2, 8.4, 21.2, 12.6, 18.6, 15.2)
        ruta.cubicTo(20.2, 17, 19, 18, 17.5, 18)
        p.drawPath(ruta)
        p.drawLine(P(12, 20.5), P(12, 12.5))
        p.drawPolyline([P(9, 15), P(12, 12), P(15, 15)])
    elif nombre == "discos":
        p.drawEllipse(P(9.5, 14.5), 6.2, 6.2)
        p.drawEllipse(P(9.5, 14.5), 1.6, 1.6)
        p.drawArc(QRectF(9, 3.5, 11.5, 11.5), -70 * 16, 200 * 16)
        p.drawEllipse(P(15, 9), 1.2, 1.2)
    elif nombre == "reloj":
        p.drawArc(QRectF(4, 4, 16, 16), 60 * 16, 290 * 16)
        p.drawPolyline([P(12, 8), P(12, 12), P(15, 14)])
        p.drawPolyline([P(3.2, 5.5), P(4.6, 8.8), P(8, 7.6)])
    elif nombre == "paleta":
        ruta = QPainterPath()
        ruta.moveTo(12, 3)
        ruta.cubicTo(6.5, 3, 3, 7, 3, 11.5)
        ruta.cubicTo(3, 16.5, 7.5, 20.5, 12.5, 20.5)
        ruta.cubicTo(14.8, 20.5, 14.8, 18.2, 13.4, 17)
        ruta.cubicTo(11.8, 15.6, 12.6, 13.8, 14.8, 13.8)
        ruta.lineTo(18, 13.8)
        ruta.cubicTo(20, 13.8, 21, 12.4, 21, 11)
        ruta.cubicTo(21, 6.6, 17, 3, 12, 3)
        p.drawPath(ruta)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for x, y in ((7.5, 11), (9.5, 7.2), (14.5, 7.2)):
            p.drawEllipse(P(x, y), 1.25, 1.25)
    elif nombre == "estrella":
        import math
        ruta = QPainterPath()
        for i in range(10):
            r = 9.2 if i % 2 == 0 else 4.1
            a = -math.pi / 2 + i * math.pi / 5
            punto = P(12 + r * math.cos(a), 12.6 + r * math.sin(a))
            ruta.moveTo(punto) if i == 0 else ruta.lineTo(punto)
        ruta.closeSubpath()
        p.drawPath(ruta)
    elif nombre == "cerrar":
        p.drawLine(P(6, 6), P(18, 18))
        p.drawLine(P(18, 6), P(6, 18))
    p.restore()


class TarjetaNovedad(QWidget):
    """Una novedad: icono, titular y texto. Se pinta ella sola para poder
    aparecer con un deslizamiento y un fundido suaves."""

    def __init__(self, icono, titular, texto, padre=None):
        super().__init__(padre)
        self.icono, self.titular, self.texto = icono, titular, texto
        self.vertical = True
        self._progreso = 0.0
        self._encima = False
        self._anim = None
        self.setFocusPolicy(Qt.TabFocus)
        self.setAccessibleName(titular)
        self.setAccessibleDescription(texto)
        self.setMouseTracking(True)

    # ---- animación
    def progreso(self):
        return self._progreso

    def poner_progreso(self, v):
        self._progreso = float(v)
        self.update()

    def revelar(self, ms=520):
        if self._anim is not None:
            self._anim.stop()
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(self._progreso)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(ms)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self.poner_progreso)
        self._anim.start()

    def mostrar_ya(self):
        if self._anim is not None:
            self._anim.stop()
        self.poner_progreso(1.0)

    # ---- medidas
    def _medidas(self, ancho):
        """(rect del icono, rect del titular, rect del texto, altura) para un ancho."""
        pad, lado = 18, 44
        ft, fx = fuente(15, QFont.ExtraBold), fuente(12.5)
        if self.vertical:
            util = ancho - 2 * pad
            r_ic = QRectF(pad, pad, lado, lado)
            y = pad + lado + 12
            x = pad
        else:
            util = ancho - 3 * pad - lado
            r_ic = QRectF(pad, pad, lado, lado)
            y = pad
            x = pad * 2 + lado
        hb = QFontMetrics(ft).boundingRect(0, 0, int(util), 1000, Qt.TextWordWrap, self.titular)
        r_t = QRectF(x, y, util, hb.height())
        tb = QFontMetrics(fx).boundingRect(0, 0, int(util), 1000, Qt.TextWordWrap, self.texto)
        r_x = QRectF(x, y + hb.height() + 4, util, tb.height())
        bajo = max(r_x.bottom(), r_ic.bottom()) + pad
        return r_ic, r_t, r_x, int(bajo)

    def altura_para(self, ancho):
        return self._medidas(ancho)[3]

    # ---- pintura
    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.update()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        t = self._progreso
        p.setOpacity(max(0.0, min(1.0, t)))
        p.translate(0, (1 - t) * 22)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        ruta = QPainterPath()
        ruta.addRoundedRect(r, 18, 18)
        fondo = QLinearGradient(r.topLeft(), r.bottomRight())
        fondo.setColorAt(0, QColor(255, 255, 255, 34 if self._encima else 24))
        fondo.setColorAt(1, QColor(255, 255, 255, 14 if self._encima else 8))
        p.fillPath(ruta, fondo)
        enfocada = self.hasFocus()
        p.setPen(QPen(_color(C["acento_alto"], 235) if enfocada else QColor(255, 255, 255, 46),
                      2 if enfocada else 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(ruta)

        r_ic, r_t, r_x, _h = self._medidas(self.width())
        disco = QLinearGradient(r_ic.topLeft(), r_ic.bottomRight())
        disco.setColorAt(0, QColor(C["acento_alto"]))
        disco.setColorAt(1, QColor(C["acento"]))
        p.setPen(Qt.NoPen)
        p.setBrush(disco)
        p.drawEllipse(r_ic)
        dibujar_icono(p, self.icono, r_ic.adjusted(10, 10, -10, -10), C["acento_texto"], 2.1)

        p.setPen(QColor(255, 255, 255))
        p.setFont(fuente(15, QFont.ExtraBold))
        p.drawText(r_t, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.titular)
        p.setPen(_mezcla(C["texto2"], "#FFFFFF", 0.45))
        p.setFont(fuente(12.5))
        p.drawText(r_x, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.texto)


# ================================================================ el aviso

class NovedadesGrandes(QDialog):
    """El aviso grande. `novedad` (de `version.buscar_actualizacion`) lo convierte en
    el aviso previo a actualizar, con el botón «Actualizar ahora»."""

    MARGEN = 44

    def __init__(self, padre=None, novedad=None, version_actual=None):
        super().__init__(padre)
        self.novedad = novedad
        self.descarga = None
        self._tarjetas = []
        self._revelado = False
        self._cols = 0
        self._version_actual = version_actual or _version.VERSION

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Novedades de Caudal")
        self.setAccessibleName("Novedades de Caudal")
        self.setAccessibleDescription(f"{TITULO}. {SUBTITULO}")
        self._ajustar_tamano()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(44, 30, 44, 32)
        raiz.setSpacing(0)

        # ---- cabecera: etiqueta + cerrar
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.et_nueva = QLabel("NOVEDAD · CAUDAL " + str(
            (novedad or {}).get("version") or self._version_actual))
        self.et_nueva.setAccessibleName("Versión")
        fila.addWidget(self.et_nueva, 0, Qt.AlignVCenter)
        fila.addStretch(1)
        self.bt_cerrar = QPushButton()
        self.bt_cerrar.setFixedSize(38, 38)
        self.bt_cerrar.setCursor(Qt.PointingHandCursor)
        self.bt_cerrar.setAccessibleName("Cerrar")
        self.bt_cerrar.setToolTip("Cerrar")
        self.bt_cerrar.clicked.connect(self.reject)
        fila.addWidget(self.bt_cerrar)
        raiz.addLayout(fila)
        raiz.addSpacing(14)

        self.et_titulo = QLabel(TITULO)
        self.et_titulo.setWordWrap(True)
        self.et_titulo.setAccessibleName(TITULO)
        raiz.addWidget(self.et_titulo)
        raiz.addSpacing(8)
        self.et_sub = QLabel(SUBTITULO)
        self.et_sub.setWordWrap(True)
        raiz.addWidget(self.et_sub)
        raiz.addSpacing(22)

        # ---- tarjetas (con desplazamiento si no caben)
        self.zona = QScrollArea()
        self.zona.setWidgetResizable(True)
        self.zona.setFrameShape(QFrame.NoFrame)
        self.zona.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zona.setStyleSheet("QScrollArea{background:transparent;border:none;}"
                                "QScrollArea>QWidget>QWidget{background:transparent;}")
        self.zona.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setAttribute(Qt.WA_TranslucentBackground, True)
        self.rejilla = QGridLayout(self.interior)
        self.rejilla.setContentsMargins(0, 0, 8, 0)
        self.rejilla.setSpacing(14)
        for icono, titular, texto in TARJETAS:
            t = TarjetaNovedad(icono, titular, texto)
            self._tarjetas.append(t)
        self.zona.setWidget(self.interior)
        raiz.addWidget(self.zona, 1)
        raiz.addSpacing(18)

        # ---- pie: actualización (si la hay) y botones
        self.et_estado = QLabel("")
        self.et_estado.setWordWrap(True)
        raiz.addWidget(self.et_estado)
        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setFixedHeight(6)
        self.barra.setTextVisible(False)
        self.barra.hide()
        raiz.addWidget(self.barra)
        raiz.addSpacing(6)

        pie = QHBoxLayout()
        pie.setSpacing(12)
        pie.addStretch(1)
        self.bt_luego = QPushButton("Más tarde")
        self.bt_luego.setCursor(Qt.PointingHandCursor)
        self.bt_luego.clicked.connect(self.reject)
        pie.addWidget(self.bt_luego)
        self.bt_principal = QPushButton("Actualizar ahora" if novedad else "Empezar")
        self.bt_principal.setObjectName("principal")
        self.bt_principal.setCursor(Qt.PointingHandCursor)
        self.bt_principal.setDefault(True)
        self.bt_principal.clicked.connect(self._principal)
        pie.addWidget(self.bt_principal)
        raiz.addLayout(pie)

        if novedad:
            self.et_estado.setText(
                f"Caudal {novedad.get('version', '')} ya está lista. Tienes la "
                f"{self._version_actual}: la nueva se instala encima y conserva tus "
                "descargas y ajustes. La música no se corta hasta que empiece la instalación.")
            if not novedad.get("instalador"):
                self.bt_principal.setEnabled(False)
                self.et_estado.setText(
                    "Esta versión no trae el instalador adjunto. Bájala desde la página "
                    "del proyecto.")
        else:
            self.bt_luego.hide()
            self.et_estado.hide()

        self._estilos()
        self.setTabOrder(self.bt_principal, self.bt_cerrar)
        self._distribuir()

    # ------------------------------------------------------------ medidas

    def _ajustar_tamano(self):
        padre = self.parentWidget()
        base = padre.window() if padre is not None else None
        if base is not None:
            ancho = base.width() - 2 * self.MARGEN
            alto = base.height() - 2 * self.MARGEN
        else:
            ancho, alto = 1100, 760
        ancho = max(520, min(1180, ancho))
        alto = max(460, min(820, alto))
        self.resize(ancho, alto)

    def _centrar(self):
        padre = self.parentWidget()
        base = padre.window() if padre is not None else None
        if base is None:
            return
        c = base.frameGeometry().center()
        self.move(c.x() - self.width() // 2, c.y() - self.height() // 2)

    # ------------------------------------------------------------ estilos

    def _estilos(self):
        self.et_nueva.setStyleSheet(
            f"color:{C['acento_texto']};background:{C['acento_alto']};border-radius:11px;"
            "padding:4px 12px;font-size:11px;font-weight:800;letter-spacing:1.2px;")
        self._px_titulo = 0                 # _distribuir pone el tamaño del título según el ancho
        self.et_estado.setStyleSheet(
            f"color:{C['texto2']};background:transparent;font-size:13px;")
        self.bt_cerrar.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,26);border:none;border-radius:19px;}"
            "QPushButton:hover{background:rgba(255,255,255,56);}"
            f"QPushButton:focus{{border:2px solid {C['acento_alto']};}}")
        from . import iconos
        self.bt_cerrar.setIcon(iconos.icono("cerrar", 18, "#FFFFFF"))
        self.bt_luego.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,22);color:#FFFFFF;border:none;"
            "border-radius:23px;padding:12px 26px;font-size:14px;font-weight:700;}"
            "QPushButton:hover{background:rgba(255,255,255,46);}"
            f"QPushButton:focus{{border:2px solid {C['acento_alto']};}}")
        self.bt_principal.setStyleSheet(
            f"QPushButton#principal{{background:{C['acento']};color:{C['acento_texto']};"
            "border:none;border-radius:23px;padding:12px 38px;font-size:15px;font-weight:800;}"
            f"QPushButton#principal:hover{{background:{C['acento_alto']};}}"
            f"QPushButton#principal:pressed{{background:{C['acento_bajo']};}}"
            "QPushButton#principal:disabled{background:rgba(255,255,255,30);"
            "color:rgba(255,255,255,120);}"
            f"QPushButton#principal:focus{{border:2px solid #FFFFFF;}}")
        self.barra.setStyleSheet(
            "QProgressBar{background:rgba(255,255,255,30);border:none;border-radius:3px;}"
            f"QProgressBar::chunk{{background:{C['acento_alto']};border-radius:3px;}}")

    # ------------------------------------------------------------ tarjetas

    def _distribuir(self):
        """Una, dos o cuatro columnas según el ancho; en pantallas pequeñas, una sola
        con desplazamiento."""
        util = self.width() - 88 - 8
        cols = 4 if util >= 940 else 2 if util >= 560 else 1
        ancho = (util - 14 * (cols - 1)) / cols
        for i, t in enumerate(self._tarjetas):
            t.vertical = cols == 4
        if cols != self._cols:
            while self.rejilla.count():
                self.rejilla.takeAt(0)
            for i, t in enumerate(self._tarjetas):
                self.rejilla.addWidget(t, i // cols, i % cols)
            for c in range(4):
                self.rejilla.setColumnStretch(c, 1 if c < cols else 0)
            self._cols = cols
        px = 38 if cols == 4 else 30 if cols == 2 else 24
        if getattr(self, "_px_titulo", 0) != px:
            self._px_titulo = px
            self.et_titulo.setStyleSheet(
                f"color:#FFFFFF;background:transparent;font-size:{px}px;font-weight:900;"
                "letter-spacing:-0.8px;")
            self.et_sub.setStyleSheet(
                f"color:{C['texto']};background:transparent;font-size:{max(13, px // 2 - 2)}px;")
        alto = max(t.altura_para(ancho) for t in self._tarjetas)
        for t in self._tarjetas:
            t.setFixedHeight(alto)
        self.rejilla.setRowStretch(len(self._tarjetas) // cols + 1, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._distribuir()

    # ------------------------------------------------------------ pintura

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        ruta = QPainterPath()
        ruta.addRoundedRect(r, 30, 30)
        p.setClipPath(ruta)
        panel = QColor(C["panel"])
        p.fillPath(ruta, QColor(C["fondo"]))
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0.0, _mezcla(panel, C["acento"], 0.52))
        g.setColorAt(0.5, _mezcla(panel, C["acento_bajo"], 0.16))
        g.setColorAt(1.0, _mezcla(QColor(C["fondo"]), panel, 0.6))
        p.fillPath(ruta, g)
        # resplandor del color de acento arriba a la derecha
        halo = QRadialGradient(QPointF(r.right() - r.width() * 0.12, r.top() + 30),
                               r.width() * 0.55)
        halo.setColorAt(0.0, _color(C["acento_alto"], 105))
        halo.setColorAt(1.0, _color(C["acento_alto"], 0))
        p.fillPath(ruta, halo)
        # discos concéntricos, como un vinilo
        centro = QPointF(r.right() - 110, r.top() + 100)
        for i, radio in enumerate(range(54, 260, 34)):
            p.setPen(QPen(_color(C["acento_alto"], max(10, 52 - i * 7)), 1.4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(centro, radio, radio)
        p.setPen(Qt.NoPen)
        p.setBrush(_color(C["acento_alto"], 60))
        p.drawEllipse(centro, 16, 16)
        # borde fino
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 56), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(ruta)

    # ------------------------------------------------------------ vida

    def showEvent(self, e):
        super().showEvent(e)
        self._ajustar_tamano()
        self._centrar()
        self.bt_principal.setFocus()
        if self._revelado:
            return
        self._revelado = True
        # entrada: fundido y subida suave; después, las tarjetas una a una
        self.setWindowOpacity(0.0)
        fin = self.pos()
        self.move(fin.x(), fin.y() + 26)
        self._a_op = QPropertyAnimation(self, b"windowOpacity", self)
        self._a_op.setDuration(320)
        self._a_op.setStartValue(0.0)
        self._a_op.setEndValue(1.0)
        self._a_op.setEasingCurve(QEasingCurve.OutCubic)
        self._a_pos = QPropertyAnimation(self, b"pos", self)
        self._a_pos.setDuration(420)
        self._a_pos.setStartValue(self.pos())
        self._a_pos.setEndValue(fin)
        self._a_pos.setEasingCurve(QEasingCurve.OutCubic)
        self._a_op.start()
        self._a_pos.start()
        for i, t in enumerate(self._tarjetas):
            QTimer.singleShot(330 + 120 * i, t.revelar)

    def mostrar_todo(self):
        """Todas las tarjetas visibles al instante (pruebas y capturas)."""
        for t in self._tarjetas:
            t.mostrar_ya()

    # ------------------------------------------------------------ acciones

    def _principal(self):
        if not self.novedad:
            self.accept()
            return
        from .actualizador import Descarga
        self.bt_principal.setEnabled(False)
        self.bt_luego.setEnabled(False)
        self.bt_cerrar.setEnabled(False)
        self.barra.show()
        self.et_estado.show()
        self.et_estado.setText("Bajando la actualización…")
        self.descarga = Descarga(self.novedad["instalador"])
        self.descarga.progreso.connect(self.barra.setValue)
        self.descarga.listo.connect(self._lanzar)
        self.descarga.fallo.connect(self._fallo)
        self.descarga.start()

    def _lanzar(self, ruta):
        self.et_estado.setText("Instalando. Caudal se cerrará un momento…")
        _version.instalar_y_salir(ruta)

    def _fallo(self, mensaje):
        self.barra.hide()
        self.bt_principal.setEnabled(True)
        self.bt_luego.setEnabled(True)
        self.bt_cerrar.setEnabled(True)
        self.et_estado.setText(mensaje + " Puedes intentarlo otra vez.")

    def reject(self):
        # con la descarga en marcha no se cierra a medias
        if self.descarga is not None and self.descarga.isRunning():
            return
        super().reject()


def crear_aviso(padre=None, novedad=None):
    """El aviso que toca: la presentación de la segunda actualización grande si la
    versión (la instalada, o la publicada si hay `novedad`) es de esa edición; si no,
    el aviso de tarjetas de la primera."""
    if novedad:
        usa_nueva = (_version.es_de_la_edicion(novedad.get("version"))
                     and not _version.alcanza_edicion(_version.VERSION))
    else:
        usa_nueva = _version.alcanza_edicion(_version.VERSION)
    if usa_nueva:
        from .presentacion_grande import PresentacionGrande
        return PresentacionGrande(padre, novedad)
    return NovedadesGrandes(padre, novedad)


def mostrar_si_toca(ventana):
    """Al abrir la app: enseña el aviso de esta versión si aún no se vio.
    No bloquea (la música sigue) y queda anotado al abrirse, no al cerrarse, para
    que un cierre brusco no lo repita. Devuelve el diálogo o None."""
    ajustes = ventana.ajustes
    if not debe_mostrarse(ajustes):
        return None
    marcar_vista(ajustes)
    d = crear_aviso(ventana)
    d.setAttribute(Qt.WA_DeleteOnClose, True)
    d.open()
    return d
