# -*- coding: utf-8 -*-
"""Logros en la interfaz: las insignias en pixel art, la pantalla de logros, el aviso al conseguir
uno, la vitrina del perfil y el vigía que cuenta lo que se escucha (descargador/logros.py).

Se engancha en main.py (tras crear la ventana) con una línea:
    from descargador.ui.logros_ui import VigiaLogros; VigiaLogros(ctx)
y la pantalla se abre con abrir_logros(ctx, padre). La vitrina va en el perfil con
VitrinaLogros(ctx, usuario, es_mio).
"""

import math
import time

from PySide6.QtCore import QEasingCurve, QObject, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import logros as L
from ..logros_dibujos import DIBUJOS, LADO
from .estilos import C

ORO = "#F2B829"
TIC_MS = 5000                   # cada cuánto se mira si suena música
SEGUNDOS_PARA_CONTAR = 20       # una canción cuenta si sonó al menos esto
SINCRONIZAR_MS = 120000

_cache = {}


# ---------------------------------------------------------------- insignias

def imagen_insignia(clave, apagado=False):
    """QImage 24x24 de una insignia; `apagado`: en grises (aún no conseguida)."""
    k = (clave, apagado)
    if k in _cache:
        return _cache[k]
    paleta, filas = DIBUJOS.get(clave, DIBUJOS["primera_nota"])
    img = QImage(LADO, LADO, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    for y, fila in enumerate(filas):
        for x, s in enumerate(fila):
            if s == ".":
                continue
            c = QColor(paleta[s])
            if apagado:
                g = int(0.30 * c.red() + 0.59 * c.green() + 0.11 * c.blue())
                g = int(40 + g * 0.42)
                c = QColor(g, g, min(255, g + 10), 235)
            img.setPixelColor(x, y, c)
    _cache[k] = img
    return img


def pixmap_insignia(clave, lado=72, apagado=False):
    """La insignia ampliada sin suavizar (pixeles nítidos)."""
    return QPixmap.fromImage(imagen_insignia(clave, apagado)).scaled(
        lado, lado, Qt.KeepAspectRatio, Qt.FastTransformation)


class Insignia(QWidget):
    """Una insignia dibujada con un halo suave si está conseguida."""

    def __init__(self, clave, lado=72, conseguida=True, padre=None):
        super().__init__(padre)
        self.clave, self.lado, self.conseguida = clave, lado, conseguida
        self.setFixedSize(lado + 16, lado + 16)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def poner(self, clave=None, conseguida=None):
        if clave is not None:
            self.clave = clave
        if conseguida is not None:
            self.conseguida = conseguida
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if self.conseguida:
            halo = QColor(C["acento"])
            halo.setAlpha(40)
            p.setPen(Qt.NoPen)
            p.setBrush(halo)
            p.drawEllipse(r)
        else:
            p.setPen(QPen(QColor(C["borde_claro"]), 1.2, Qt.DashLine))
            p.setBrush(QColor(C["superficie2"]))
            p.drawEllipse(r)
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        pm = pixmap_insignia(self.clave, self.lado, not self.conseguida)
        p.drawPixmap(int((self.width() - pm.width()) / 2), int((self.height() - pm.height()) / 2), pm)
        p.end()


# ---------------------------------------------------------------- pantalla de logros

def _fecha_corta(epoch):
    try:
        return time.strftime("%d/%m/%Y", time.localtime(int(epoch)))
    except (TypeError, ValueError, OSError):
        return ""


class TarjetaLogro(QFrame):
    """Un logro: insignia, nombre, qué hay que hacer, progreso y botón para lucirlo."""
    alternar = Signal(str)

    def __init__(self, logros, logro, padre=None):
        super().__init__(padre)
        self.logros, self.logro = logros, logro
        self.setObjectName("tarjeta_logro")
        self.setMinimumWidth(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 12, 14, 12)
        h.setSpacing(12)
        self.insignia = Insignia(logro.id, 48, padre=self)
        h.addWidget(self.insignia, 0, Qt.AlignTop)
        v = QVBoxLayout()
        v.setSpacing(3)
        self.nombre = QLabel(logro.nombre)
        self.nombre.setStyleSheet("font-size:14px;font-weight:800;background:transparent;")
        self.detalle = QLabel(logro.descripcion)
        self.detalle.setWordWrap(True)
        self.detalle.setStyleSheet(f"color:{C['texto2']};font-size:12px;background:transparent;")
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(6)
        self.barra.setRange(0, 1000)
        self.estado = QLabel("")
        self.estado.setStyleSheet(f"color:{C['texto3']};font-size:11px;background:transparent;")
        self.bt = QPushButton("")
        self.bt.setCursor(Qt.PointingHandCursor)
        self.bt.setFixedHeight(26)
        self.bt.clicked.connect(lambda: self.alternar.emit(self.logro.id))
        fila = QHBoxLayout()
        fila.setSpacing(8)
        fila.addWidget(self.estado, 1)
        fila.addWidget(self.bt, 0)
        v.addWidget(self.nombre)
        v.addWidget(self.detalle)
        v.addWidget(self.barra)
        v.addLayout(fila)
        h.addLayout(v, 1)
        self.pintar()

    def pintar(self):
        lg = self.logros
        valor, meta, frac = lg.progreso(self.logro)
        hecho = lg.conseguido(self.logro.id)
        en_vitrina = self.logro.id in lg.vitrina
        self.insignia.poner(conseguida=hecho)
        self.barra.setValue(int(frac * 1000))
        color = ORO if hecho else C["acento"]
        self.barra.setStyleSheet(
            f"QProgressBar{{background:{C['superficie3']};border:none;border-radius:3px;}}"
            f"QProgressBar::chunk{{background:{color};border-radius:3px;}}")
        borde = ORO if en_vitrina else (C["borde_claro"] if hecho else C["borde"])
        self.setStyleSheet(
            f"QFrame#tarjeta_logro{{background:{C['superficie'] if hecho else C['panel']};"
            f"border:1px solid {borde};border-radius:14px;}}")
        self.nombre.setStyleSheet(
            f"font-size:14px;font-weight:800;background:transparent;color:{C['texto'] if hecho else C['texto2']};")
        if hecho:
            self.estado.setText("Conseguido el " + _fecha_corta(lg.desbloqueados.get(self.logro.id)))
            self.bt.setVisible(True)
            self.bt.setText("★ En tu perfil" if en_vitrina else "Lucir")
            self.bt.setToolTip("Quitar del perfil" if en_vitrina else "Mostrar en tu perfil (hasta 3)")
            if en_vitrina:
                self.bt.setStyleSheet(f"QPushButton{{background:{ORO};color:#2A1A00;border:none;border-radius:13px;"
                                      "padding:0 12px;font-weight:800;}")
            else:
                self.bt.setStyleSheet(f"QPushButton{{background:transparent;color:{C['acento']};"
                                      f"border:1px solid {C['acento']};border-radius:13px;padding:0 14px;"
                                      "font-weight:700;}")
        else:
            unidad = {"horas": " h", "dia_horas": " h", "racha": " días"}.get(self.logro.metrica, "")
            self.estado.setText(f"{min(valor, meta)} de {meta}{unidad}")
            self.bt.setVisible(False)


class PaginaLogros(QWidget):
    """Todos los logros por categorías, con el resumen arriba."""

    def __init__(self, logros, al_cambiar_vitrina=None, padre=None):
        super().__init__(padre)
        self.logros = logros
        self.al_cambiar_vitrina = al_cambiar_vitrina
        self.tarjetas = []
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        cab = QFrame()
        cab.setObjectName("cabecera_logros")
        cab.setStyleSheet(
            "QFrame#cabecera_logros{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {C['superficie2']},stop:1 {C['panel']});border-radius:16px;}}")
        hc = QHBoxLayout(cab)
        hc.setContentsMargins(20, 16, 20, 16)
        hc.setSpacing(16)
        self.trofeo = Insignia("coleccionista", 64, padre=cab)
        hc.addWidget(self.trofeo)
        tv = QVBoxLayout()
        t = QLabel("Tus logros")
        t.setStyleSheet("font-size:26px;font-weight:900;background:transparent;")
        self.resumen = QLabel("")
        self.resumen.setStyleSheet(f"color:{C['texto2']};font-size:13px;background:transparent;")
        self.ayuda = QLabel("Elige hasta 3 con «Lucir» para que se vean en tu perfil.")
        self.ayuda.setStyleSheet(f"color:{C['texto3']};font-size:12px;background:transparent;")
        tv.addWidget(t)
        tv.addWidget(self.resumen)
        tv.addWidget(self.ayuda)
        self.aviso = QLabel("")
        self.aviso.setStyleSheet(f"color:{C['aviso']};font-size:12px;font-weight:700;background:transparent;")
        tv.addWidget(self.aviso)
        hc.addLayout(tv, 1)
        raiz.addWidget(cab)

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setStyleSheet(f"QScrollArea{{background:{C['fondo']};border:none;}}")
        area.viewport().setStyleSheet(f"background:{C['fondo']};")
        cont = QWidget()
        cont.setObjectName("logros_contenido")
        cont.setStyleSheet(f"QWidget#logros_contenido{{background:{C['fondo']};}}")
        v = QVBoxLayout(cont)
        v.setContentsMargins(2, 14, 8, 14)
        v.setSpacing(8)
        for cat, titulo in L.CATEGORIAS:
            de_cat = [l for l in L.CATALOGO if l.categoria == cat]
            if not de_cat:
                continue
            et = QLabel(titulo.upper())
            et.setStyleSheet(f"color:{C['acento']};font-size:12px;font-weight:800;letter-spacing:1px;"
                             "background:transparent;margin-top:10px;")
            v.addWidget(et)
            g = QGridLayout()
            g.setSpacing(10)
            g.setColumnStretch(0, 1)
            g.setColumnStretch(1, 1)
            for i, l in enumerate(de_cat):
                tj = TarjetaLogro(logros, l)
                tj.alternar.connect(self._alternar)
                self.tarjetas.append(tj)
                g.addWidget(tj, i // 2, i % 2)
            v.addLayout(g)
        v.addStretch(1)
        area.setWidget(cont)
        raiz.addWidget(area, 1)
        self.pintar()

    def pintar(self):
        r = self.logros.resumen()
        dias = "día" if r["racha"] == 1 else "días"
        self.resumen.setText(f"{r['conseguidos']} de {r['total']} conseguidos · racha de {r['racha']} {dias}"
                             f" · {r['horas']} h de música")
        for t in self.tarjetas:
            t.pintar()

    def _alternar(self, ident):
        if not self.logros.alternar_vitrina(ident):
            self.aviso.setText("Tu vitrina ya tiene 3: quita uno para poner otro.")
            QTimer.singleShot(3500, lambda: self.aviso.setText(""))
        self.pintar()
        if self.al_cambiar_vitrina:
            self.al_cambiar_vitrina()


class DialogoLogros(QDialog):
    def __init__(self, logros, al_cambiar_vitrina=None, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Logros")
        self.resize(820, 680)
        self.setStyleSheet(f"QDialog{{background:{C['fondo']};}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 18, 18, 18)
        self.pagina = PaginaLogros(logros, al_cambiar_vitrina, self)
        v.addWidget(self.pagina)
        self._repintar = self.pagina.pintar
        logros.al_cambiar.append(self._repintar)

    def done(self, r):
        try:
            self.pagina.logros.al_cambiar.remove(self._repintar)
        except ValueError:
            pass
        super().done(r)


def logros_de_ctx(ctx):
    """Los logros de la cuenta abierta (los crea el vigía; sin vigía, se leen del disco)."""
    lg = getattr(ctx, "logros", None)
    if lg is None:
        from ..config import carpeta_perfil
        lg = L.Logros(str(carpeta_perfil() / "logros.json"))
        ctx.logros = lg
    return lg


def abrir_logros(ctx, padre=None):
    vigia = getattr(ctx, "vigia_logros", None)
    d = DialogoLogros(logros_de_ctx(ctx), vigia.pronto if vigia else None,
                      padre or getattr(ctx, "ventana", None))
    d.setAttribute(Qt.WA_DeleteOnClose)
    d.show()
    return d


# ---------------------------------------------------------------- aviso al conseguir uno

class AvisoLogro(QWidget):
    """Tarjeta que baja desde arriba con la insignia que «salta» y destellos alrededor."""
    cerrado = Signal()
    pulsado = Signal()

    ANCHO, ALTO = 400, 112

    def __init__(self, logro, padre, extra=0, duracion=4800):
        super().__init__(padre)
        self.logro, self.extra = logro, extra
        self.setFixedSize(self.ANCHO, self.ALTO)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        self.t = 0.0          # 0..1 entrada
        self.brillo = 0.0     # giro de los destellos
        self._entrada = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=650)
        self._entrada.setEasingCurve(QEasingCurve.OutBack)
        self._entrada.valueChanged.connect(self._mover)
        self._giro = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=2400, loopCount=-1)
        self._giro.valueChanged.connect(self._girar)
        self._salida = QVariantAnimation(self, startValue=1.0, endValue=0.0, duration=320)
        self._salida.setEasingCurve(QEasingCurve.InCubic)
        self._salida.valueChanged.connect(self._mover)
        self._salida.finished.connect(self._fin)
        self._reloj = QTimer(self, singleShot=True, interval=duracion)
        self._reloj.timeout.connect(self.cerrar)

    def mostrar(self):
        self._mover(0.0)
        self.show()
        self.raise_()
        self._entrada.start()
        self._giro.start()
        self._reloj.start()

    def cerrar(self):
        if self._salida.state() == QVariantAnimation.Running:
            return
        self._reloj.stop()
        self._salida.start()

    def _fin(self):
        self._giro.stop()
        self.hide()
        self.cerrado.emit()
        self.deleteLater()

    def _mover(self, t):
        self.t = float(t)
        padre = self.parentWidget()
        if padre is not None:
            x = (padre.width() - self.width()) // 2
            y = int(-self.height() + (self.height() + 18) * max(0.0, min(1.15, self.t)))
            self.move(x, y)
        self.update()

    def _girar(self, v):
        self.brillo = float(v)
        self.update()

    def mousePressEvent(self, _e):
        self.pulsado.emit()
        self.cerrar()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        fondo = QLinearGradient(r.topLeft(), r.bottomRight())
        fondo.setColorAt(0, QColor(C["superficie2"]))
        fondo.setColorAt(1, QColor(C["panel"]))
        camino = QPainterPath()
        camino.addRoundedRect(r, 18, 18)
        sombra = QColor(0, 0, 0, 90)
        p.setPen(Qt.NoPen)
        p.setBrush(sombra)
        p.drawRoundedRect(r.translated(0, 3), 18, 18)
        p.setBrush(QBrush(fondo))
        p.setPen(QPen(QColor(ORO), 1.6))
        p.drawPath(camino)

        # insignia con rebote y rayos
        cx, cy = r.left() + 54, r.center().y()
        escala = max(0.0, min(1.0, self.t * 1.25)) ** 0.6
        rayo = QColor(ORO)
        for k in range(10):
            a = self.brillo * 2 * math.pi + k * math.pi / 5
            rayo.setAlpha(70 if k % 2 else 120)
            p.setPen(QPen(rayo, 3, Qt.SolidLine, Qt.RoundCap))
            r1, r2 = 34 * escala, (44 + 4 * math.sin(self.brillo * 6.28 + k)) * escala
            p.drawLine(QPointF(cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                       QPointF(cx + r2 * math.cos(a), cy + r2 * math.sin(a)))
        halo = QColor(ORO)
        halo.setAlpha(50)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), 34 * escala, 34 * escala)
        lado = max(1, int(72 * escala) // 24 * 24) if escala > 0.34 else max(1, int(72 * escala))
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)
        pm = pixmap_insignia(self.logro.id, lado)
        p.drawPixmap(int(cx - pm.width() / 2), int(cy - pm.height() / 2), pm)
        # destellos en pixel (crucecitas)
        for k in range(4):
            a = -self.brillo * 2 * math.pi + k * math.pi / 2 + 0.6
            sx, sy = cx + 40 * math.cos(a), cy + 40 * math.sin(a)
            c = QColor("#FFF6B0")
            c.setAlpha(int(140 + 110 * math.sin(self.brillo * 12 + k)))
            p.fillRect(QRectF(sx - 1, sy - 4, 2, 8), c)
            p.fillRect(QRectF(sx - 4, sy - 1, 8, 2), c)

        # textos
        x = r.left() + 108
        p.setPen(QColor(ORO))
        f = QFont(self.font())
        f.setPixelSize(11)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        p.setFont(f)
        cab = "¡LOGRO CONSEGUIDO!" if not self.extra else f"¡LOGRO CONSEGUIDO! (+{self.extra} más)"
        p.drawText(QRectF(x, r.top() + 14, r.right() - x - 12, 16), Qt.AlignLeft | Qt.AlignVCenter, cab)
        f2 = QFont(self.font())
        f2.setPixelSize(18)
        f2.setWeight(QFont.Black)
        p.setFont(f2)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRectF(x, r.top() + 32, r.right() - x - 12, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   self.logro.nombre)
        f3 = QFont(self.font())
        f3.setPixelSize(12)
        p.setFont(f3)
        p.setPen(QColor(C["texto2"]))
        p.drawText(QRectF(x, r.top() + 60, r.right() - x - 12, 34), Qt.AlignLeft | Qt.TextWordWrap,
                   self.logro.descripcion)
        p.end()


class ColaAvisos(QObject):
    """Muestra los avisos de uno en uno sobre la ventana."""

    def __init__(self, ventana, al_pulsar=None):
        super().__init__(ventana)
        self.ventana = ventana
        self.al_pulsar = al_pulsar
        self.pendientes = []
        self.actual = None

    def poner(self, nuevos):
        """Muchos de golpe (p. ej. al importar lo escuchado antes): un solo aviso con el total."""
        if not nuevos:
            return
        if len(nuevos) > 2:
            self.pendientes.append((nuevos[-1], len(nuevos) - 1))
        else:
            self.pendientes.extend((n, 0) for n in nuevos)
        if self.actual is None:
            self._siguiente()

    def _siguiente(self):
        if not self.pendientes or self.ventana is None:
            self.actual = None
            return
        logro, extra = self.pendientes.pop(0)
        a = AvisoLogro(logro, self.ventana, extra)
        a.cerrado.connect(self._siguiente)
        if self.al_pulsar:
            a.pulsado.connect(self.al_pulsar)
        self.actual = a
        a.mostrar()


# ---------------------------------------------------------------- vitrina del perfil

class VitrinaLogros(QFrame):
    """Los logros que la persona eligió lucir (hasta 3). Si no hay nada que enseñar, no se ve."""
    listo = Signal(object)

    def __init__(self, ctx, usuario="", es_mio=False, padre=None):
        super().__init__(padre)
        self.ctx, self.usuario, self.es_mio = ctx, usuario, es_mio
        self.setObjectName("caja")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 16, 22, 16)
        self.v.setSpacing(10)
        cab = QHBoxLayout()
        t = QLabel("Logros")
        t.setStyleSheet("font-size:18px;font-weight:800;background:transparent;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.total = QLabel("")
        self.total.setStyleSheet(f"color:{C['texto2']};background:transparent;")
        cab.addWidget(self.total)
        if es_mio:
            bt = QPushButton("Ver todos")
            bt.setCursor(Qt.PointingHandCursor)
            bt.clicked.connect(lambda: abrir_logros(ctx, self.window()))
            cab.addWidget(bt)
        self.v.addLayout(cab)
        self.fila = QHBoxLayout()
        self.fila.setSpacing(14)
        self.v.addLayout(self.fila)
        self.listo.connect(self.pintar)
        if es_mio:
            lg = logros_de_ctx(ctx)
            self._repintar = lambda: self.pintar({"vitrina": lg.vitrina, "total": len(lg.desbloqueados),
                                                  "fechas": lg.desbloqueados})
            lg.al_cambiar.append(self._repintar)
            self.destroyed.connect(lambda *_: lg.al_cambiar.remove(self._repintar)
                                   if self._repintar in lg.al_cambiar else None)
            self._repintar()
        else:
            self.setVisible(False)
            from ..hilos import en_segundo_plano
            sesion = (getattr(ctx, "cuenta", None) or {}).get("sesion")
            en_segundo_plano(L.vitrina_de, sesion, usuario, ok=self.pintar, dueno=self)

    def _vaciar(self):
        while self.fila.count():
            it = self.fila.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def pintar(self, datos):
        self._vaciar()
        if not datos or (not datos.get("vitrina") and not self.es_mio):
            self.setVisible(False)
            return
        self.setVisible(True)
        n = int(datos.get("total") or 0)
        self.total.setText(f"{n} de {len(L.CATALOGO)}")
        if not datos.get("vitrina"):
            et = QLabel("Elige hasta 3 logros en «Ver todos» para lucirlos aquí.")
            et.setStyleSheet(f"color:{C['texto3']};background:transparent;")
            self.fila.addWidget(et)
            self.fila.addStretch(1)
            return
        for ident in datos["vitrina"]:
            logro = L.POR_ID.get(ident)
            if logro is None:
                continue
            caja = QVBoxLayout()
            caja.setSpacing(4)
            ins = Insignia(ident, 48)
            fecha = (datos.get("fechas") or {}).get(ident)
            ins.setToolTip(f"{logro.nombre}\n{logro.descripcion}" + (f"\n{_fecha_corta(fecha)}" if fecha else ""))
            nombre = QLabel(logro.nombre)
            nombre.setAlignment(Qt.AlignCenter)
            nombre.setWordWrap(True)
            nombre.setFixedWidth(110)
            nombre.setStyleSheet("font-size:12px;font-weight:700;background:transparent;")
            caja.addWidget(ins, 0, Qt.AlignHCenter)
            caja.addWidget(nombre, 0, Qt.AlignHCenter)
            w = QWidget()
            w.setStyleSheet("background:transparent;")
            w.setLayout(caja)
            self.fila.addWidget(w)
        self.fila.addStretch(1)


# ---------------------------------------------------------------- vigía

def _total_descargas(cuenta):
    """contar_descargadas() da {True: canciones, False: videos}; aquí cuentan las dos."""
    if isinstance(cuenta, dict):
        return sum(int(v or 0) for v in cuenta.values())
    return int(cuenta or 0)


class VigiaLogros(QObject):
    """Cuenta lo que pasa en la app (sin tocar el reproductor: solo escucha sus señales) y avisa
    al conseguir un logro. Uno por cuenta abierta."""

    def __init__(self, ctx, logros=None, tic_ms=TIC_MS, importar=True, sincronizar_ms=SINCRONIZAR_MS):
        super().__init__(ctx)
        self.ctx = ctx
        if logros is None:
            from ..config import carpeta_perfil
            logros = L.Logros(str(carpeta_perfil() / "logros.json"))
        self.logros = logros
        ctx.logros = logros
        ctx.vigia_logros = self
        self.avisos = ColaAvisos(getattr(ctx, "ventana", None), lambda: abrir_logros(ctx))
        self._marca = time.monotonic()
        self._pista = None
        self._sonada = 0.0
        self._sincronizando = False
        r = getattr(ctx, "reproductor", None)
        if r is not None:
            r.pista_cambio.connect(self._al_pista)
            r.estado_cambio.connect(self._al_estado)
        for senal, funcion in (("listas_cambio", self._totales), ("descargas_cambio", self._totales)):
            s = getattr(ctx, senal, None)
            if s is not None:
                s.connect(funcion)
        if getattr(ctx, "me_gusta_cambio", None) is not None:
            ctx.me_gusta_cambio.connect(lambda *_: self._totales())
        try:
            from .paginas import juntos as J
            self._juntos = J.gestor(ctx)
            self._juntos.cambio.connect(self._al_juntos)
        except Exception:  # noqa: BLE001 - sin «Escuchar juntos» los logros de amigos esperan
            self._juntos = None
        self.tic = QTimer(self)
        self.tic.setInterval(tic_ms)
        self.tic.timeout.connect(self._al_tic)
        self.tic.start()
        self.reloj_nube = QTimer(self)
        self.reloj_nube.setInterval(sincronizar_ms)
        self.reloj_nube.timeout.connect(self._sincronizar)
        self.reloj_nube.start()
        if importar:
            QTimer.singleShot(2500, self._importar)

    # ---- lo que se escucha
    def _al_estado(self, _estado):
        self._al_tic()

    def _al_pista(self, pista):
        self._al_tic()
        self._pista = pista if isinstance(pista, dict) else None
        self._sonada = 0.0

    def _al_tic(self):
        ahora = time.monotonic()
        paso = min(ahora - self._marca, 3 * self.tic.interval() / 1000.0)
        self._marca = ahora
        r = getattr(self.ctx, "reproductor", None)
        if r is None or getattr(r, "estado", "") != "sonando" or paso <= 0:
            return
        self.logros.anotar_segundos(paso)
        if self._pista is not None:
            self._sonada += paso
            if self._sonada >= SEGUNDOS_PARA_CONTAR:
                self.logros.anotar_pista(self._pista)
                self._pista = None
        self.revisar()

    # ---- la colección
    def _totales(self):
        col = getattr(self.ctx, "coleccion", None)
        if col is None:
            return
        for f, anotar in ((lambda: len(col.listas()), self.logros.anotar_listas),
                          (lambda: col.total_me_gusta(), self.logros.anotar_me_gusta),
                          (lambda: _total_descargas(col.contar_descargadas()), self.logros.anotar_descargas)):
            try:
                anotar(f())
            except Exception:  # noqa: BLE001
                pass
        self.revisar()

    def _al_juntos(self):
        g = self._juntos
        s = g.sala if g is not None else None
        if s is None:
            return
        try:
            self.logros.anotar_sala(f"{s.codigo}|{s.mi_id}", len(s.miembros) >= 2, s.soy_anfitrion)
        except Exception:  # noqa: BLE001
            return
        self.revisar()

    # ---- lo de antes
    def _importar(self):
        self._totales()
        if self.logros.importado:
            self._sincronizar()
            return
        col = getattr(self.ctx, "coleccion", None)
        ruta = str(getattr(col, "archivo", "") or "")
        from ..hilos import en_segundo_plano

        def hecho(filas):
            self.logros.importar(filas or [])
            self.revisar()
            self._sincronizar()
        en_segundo_plano(L.reproducciones_de, ruta, ok=hecho, error=lambda _e: hecho([]), dueno=self)

    # ---- avisos y nube
    def revisar(self):
        nuevos = self.logros.revisar()
        if nuevos:
            if self.avisos.ventana is None:
                self.avisos.ventana = getattr(self.ctx, "ventana", None)
            self.avisos.poner(nuevos)
            self.pronto()
        return nuevos

    def pronto(self):
        """Sube a la nube en un momento (la vitrina cambió o hay un logro nuevo)."""
        QTimer.singleShot(4000, self._sincronizar)

    def _sincronizar(self):
        sesion = (getattr(self.ctx, "cuenta", None) or {}).get("sesion")
        if self._sincronizando or sesion is None or not self.logros.pendiente_nube:
            return
        self._sincronizando = True
        from ..hilos import en_segundo_plano

        def fin(remoto=None):
            self._sincronizando = False
            if isinstance(remoto, dict):
                self.logros.pendiente_nube = False
                self.logros.mezclar(remoto)        # en el hilo de la interfaz (repinta pantallas)
                self.revisar()
        en_segundo_plano(L.subir, self.logros.para_nube(), sesion, ok=fin, error=lambda _e: fin(None), dueno=self)
