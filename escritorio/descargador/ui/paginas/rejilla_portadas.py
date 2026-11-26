# -*- coding: utf-8 -*-
"""La rejilla de carátulas de Inicio: cuadradas, con el título encima, por páginas con puntitos.

Se pinta en una sola pieza (nada de un widget por carátula) y las columnas salen del ancho que haya.
"""

from PySide6.QtCore import QEasingCurve, QPointF, QRect, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from .. import iconos, imagenes
from ..componentes import Puntitos, fuente
from ..estilos import C

FILAS = 2
MAX_PAGINAS = 3
HUECO = 10
LADO_IDEAL = 158
MIN_COLUMNAS, MAX_COLUMNAS = 3, 10
RADIO = 8
ICONO_TIPO = {"album": "album", "lista": "lista", "mi_lista": "lista", "radio": "radio",
              "artista": "usuario", "me_gusta": "corazon_lleno"}


def columnas_para(ancho):
    return max(MIN_COLUMNAS, min(MAX_COLUMNAS, round((ancho + HUECO) / (LADO_IDEAL + HUECO))))


def paginas_para(n, columnas):
    """Cuántas páginas llenas salen (una incompleta solo se enseña si es la única)."""
    por_pagina = columnas * FILAS
    return max(1, min(MAX_PAGINAS, n // por_pagina)) if n else 0


def clave_de(el):
    if el.get("tipo") == "pista":
        return ("pista", el.get("clave") or el.get("video_id"))
    return (el.get("tipo"), str(el.get("id") or el.get("especial") or ""))


def mezclar(contextos, canciones, tope=60):
    """Lo más usado: una lista/álbum/artista y dos canciones por vuelta, sin repetir."""
    salida, vistas = [], set()

    def poner(el):
        k = clave_de(el)
        if k in vistas or not el.get("titulo"):
            return
        vistas.add(k)
        salida.append(el)
    contextos, canciones = list(contextos), list(canciones)
    while (contextos or canciones) and len(salida) < tope:
        if contextos:
            poner(contextos.pop(0))
        for _ in range(2):
            if canciones:
                poner(canciones.pop(0))
    return salida[:tope]


class _Lienzo(QWidget):
    """Las páginas, pintadas."""

    def __init__(self, dueno):
        super().__init__(dueno)
        self.d = dueno
        self._encima = -1
        self._en_play = False
        self._pulso = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self._foco = 0

    # ---- geometría
    def rect_de(self, k):
        """El cuadro del elemento k de la página que se ve."""
        d = self.d
        f, c = divmod(k, d.columnas)
        return QRectF(c * (d.lado + HUECO), f * (d.lado + HUECO), d.lado, d.lado)

    def indice_en(self, pos):
        for k in range(len(self.d.de_pagina(self.d.pagina))):
            if self.rect_de(k).contains(QPointF(pos)):
                return k
        return -1

    def rect_play(self, k):
        r = self.rect_de(k)
        lado = min(40, r.width() * 0.28)
        return QRectF(r.right() - lado - 8, r.top() + 8, lado, lado)

    # ---- ratón y teclado
    def mouseMoveEvent(self, e):
        k = self.indice_en(e.position())
        play = k >= 0 and self.rect_play(k).contains(e.position())
        if (k, play) != (self._encima, self._en_play):
            self._encima, self._en_play = k, play
            els = self.d.de_pagina(self.d.pagina)
            self.setToolTip(self.d.nombre(els[k]) if k >= 0 else "")
            self.update()

    def leaveEvent(self, _e):
        self._encima, self._en_play = -1, False
        self.update()

    def mousePressEvent(self, e):
        k = self.indice_en(e.position())
        if k < 0:
            return
        el = self.d.de_pagina(self.d.pagina)[k]
        if e.button() == Qt.RightButton:
            self.d.ctx.menu_elemento(el, e.globalPosition().toPoint())
        elif e.button() == Qt.LeftButton:
            self._pulso = k          # se abre al soltar, para poder arrastrar la página desde aquí

    def mouseReleaseEvent(self, e):
        k, self._pulso = self._pulso, -1
        if e.button() != Qt.LeftButton or k < 0 or self.indice_en(e.position()) != k:
            return
        self._activar(k, self.rect_play(k).contains(e.position()))

    def _activar(self, k, reproducir):
        els = self.d.de_pagina(self.d.pagina)
        if not 0 <= k < len(els):
            return
        el = els[k]
        (self.d.reproducir if reproducir or el.get("tipo") == "pista" else self.d.abrir).emit(el)

    def keyPressEvent(self, e):
        n = len(self.d.de_pagina(self.d.pagina))
        paso = {Qt.Key_Right: 1, Qt.Key_Left: -1, Qt.Key_Down: self.d.columnas,
                Qt.Key_Up: -self.d.columnas}.get(e.key())
        if paso:
            nuevo = self._foco + paso
            if nuevo >= n and e.key() == Qt.Key_Right and self.d.pagina < self.d.paginas - 1:
                self.d.ir_a(self.d.pagina + 1)
                nuevo = 0
            elif nuevo < 0 and e.key() == Qt.Key_Left and self.d.pagina > 0:
                self.d.ir_a(self.d.pagina - 1)
                nuevo = 0
            self._foco = max(0, min(nuevo, len(self.d.de_pagina(self.d.pagina)) - 1))
            self.update()
            return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._activar(self._foco, False)
            return
        super().keyPressEvent(e)

    def wheelEvent(self, e):
        dx = e.angleDelta().x() or (e.angleDelta().y() if e.modifiers() & Qt.ShiftModifier else 0)
        if dx:
            self.d.ir_a(self.d.pagina + (-1 if dx > 0 else 1))
            e.accept()
        else:
            e.ignore()

    # ---- pintado
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        d = self.d
        if d.lado <= 0:
            return
        base = int(d.avance)
        for pagina in (base, base + 1):
            els = d.de_pagina(pagina)
            if not els:
                continue
            x = (pagina - d.avance) * (self.width() + HUECO)
            if x >= self.width() or x <= -self.width() - HUECO:
                continue
            p.save()
            p.translate(x, 0)
            quieta = d.avance == d.pagina == pagina
            for k, el in enumerate(els):
                self._pintar(p, k, el, quieta)
            p.restore()

    def _pintar(self, p, k, el, quieta):
        d = self.d
        r = self.rect_de(k)
        suena = d.es_la_que_suena(el)
        encima = quieta and self._encima == k
        ruta = QPainterPath()
        ruta.addRoundedRect(r, RADIO, RADIO)
        p.save()
        p.setClipPath(ruta)
        if el.get("especial") == "me_gusta":
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, QColor("#5B3DF5"))
            g.setColorAt(1, QColor("#22D3EE"))
            p.fillRect(r, g)
            lado = int(r.width() * 0.34)
            p.drawPixmap(int(r.center().x() - lado / 2), int(r.center().y() - lado * 0.6),
                         iconos.pixmap("corazon_lleno", lado, "#FFFFFF"))
        else:
            pm = d.portada(el)
            if pm is not None:
                p.drawPixmap(r.toRect(), pm)
            else:
                p.fillRect(r, QColor(C["superficie3"]))
                lado = int(r.width() * 0.28)
                p.drawPixmap(int(r.center().x() - lado / 2), int(r.center().y() - lado * 0.7),
                             iconos.pixmap(ICONO_TIPO.get(el.get("tipo"), "musica"), lado, C["texto3"]))
        velo = QLinearGradient(0, r.top() + r.height() * 0.45, 0, r.bottom())
        velo.setColorAt(0, QColor(0, 0, 0, 0))
        velo.setColorAt(1, QColor(0, 0, 0, 215))
        p.fillRect(r, velo)
        if encima:
            p.fillRect(r, QColor(255, 255, 255, 20))
        p.restore()

        # el título, con una marquita si es una lista, un álbum...
        x = r.left() + 11
        icono = ICONO_TIPO.get(el.get("tipo")) if el.get("especial") != "me_gusta" else None
        alto = 34
        if icono:
            p.drawPixmap(int(x), int(r.bottom() - alto / 2 - 8), iconos.pixmap(icono, 15, "#FFFFFF"))
            x += 20
        f = fuente(13.5 if r.width() < 140 else 14.5, QFont.Bold)
        p.setFont(f)
        ancho = int(r.right() - 10 - x)
        texto = QFontMetrics(f).elidedText(el.get("titulo") or "", Qt.ElideRight, ancho)
        caja = QRect(int(x), int(r.bottom() - alto), ancho, alto - 2)
        p.setPen(QColor(0, 0, 0, 140))
        p.drawText(caja.translated(0, 1), Qt.AlignLeft | Qt.AlignVCenter, texto)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(caja, Qt.AlignLeft | Qt.AlignVCenter, texto)

        if suena:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#FFFFFF"), 3))
            p.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), RADIO, RADIO)
            if not encima:
                self._barritas(p, r)
        elif quieta and self.hasFocus() and self._foco == k:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(C["acento"]), 2))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), RADIO, RADIO)
        if encima:
            rp = self.rect_play(k)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 255 if self._en_play else 235))
            p.drawEllipse(rp)
            t = int(rp.width() * 0.45)
            sonando = suena and d.suena_ahora()
            p.drawPixmap(int(rp.center().x() - t / 2 + (0 if sonando else 1)), int(rp.center().y() - t / 2),
                         iconos.pixmap("pausa" if sonando else "reproducir", t, "#06070A"))

    def _barritas(self, p, r):
        """Tres barritas en el centro: esta es la que suena (quietas si está en pausa)."""
        c = r.center()
        alto = r.height() * 0.15
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(c, alto * 1.15, alto * 1.15)
        p.setBrush(QColor("#FFFFFF"))
        for i, f in enumerate((0.55, 1.0, 0.72) if self.d.suena_ahora() else (0.3, 0.3, 0.3)):
            h = alto * f
            p.drawRoundedRect(QRectF(c.x() - 9 + i * 7, c.y() + alto / 2 - h, 4, h), 1.5, 1.5)


class RejillaPortadas(QWidget):
    abrir = Signal(dict)
    reproducir = Signal(dict)

    def __init__(self, ctx, elementos=(), padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.elementos = list(elementos)
        self.columnas, self.lado, self.paginas, self.pagina = 4, 0, 1, 0
        self.avance = 0.0
        self._pedidas = set()
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.lienzo = _Lienzo(self)
        v.addWidget(self.lienzo)
        self.puntos = Puntitos()
        self.puntos.hide()
        self.puntos.ir.connect(self.ir_a)
        v.addWidget(self.puntos)
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(self._mover)
        # al cambiar el ancho de la ventana se estira lo que hay; la portada fina se pide al parar
        self._t_fina = QTimer(self)
        self._t_fina.setSingleShot(True)
        self._t_fina.setInterval(160)
        self._t_fina.timeout.connect(self._pedir_finas)
        self._lado_fino = 0
        r = ctx.reproductor
        r.pista_cambio.connect(self._al_cambiar)
        r.estado_cambio.connect(self._al_cambiar)
        self._colocar()

    # ------------------------------------------------------------ datos

    def poner(self, elementos):
        self.elementos = list(elementos)
        self.pagina, self.avance = 0, 0.0
        self._colocar()

    def de_pagina(self, i):
        if not 0 <= i < self.paginas:
            return []
        n = self.columnas * FILAS
        return self.elementos[i * n:(i + 1) * n]

    def visibles(self):
        """Todo lo que se puede ver pasando las páginas (para no repetirlo debajo)."""
        return self.elementos[:self.paginas * self.columnas * FILAS]

    def nombre(self, el):
        artista = el.get("artista") or ""
        return f"{el.get('titulo') or ''}" + (f" · {artista}" if artista else "")

    def es_la_que_suena(self, el):
        r = self.ctx.reproductor
        actual = r.actual
        if not actual:
            return False
        if el.get("tipo") == "pista":
            return bool((el.get("clave") and el.get("clave") == actual.get("clave"))
                        or (el.get("video_id") and el.get("video_id") == actual.get("video_id")))
        c = r.contexto or {}
        if el.get("especial") == "me_gusta":
            return c.get("tipo") == "me_gusta"
        return bool(c.get("tipo") == el.get("tipo") and c.get("id") is not None
                    and str(c.get("id")) == str(el.get("id")))

    def suena_ahora(self):
        return getattr(self.ctx.reproductor, "estado", "") in ("sonando", "cargando")

    def _al_cambiar(self, *_a):
        self.lienzo.update()

    # ------------------------------------------------------------ forma

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._colocar()

    def _colocar(self):
        w = self.width()
        if w < 120:
            return
        self.columnas = columnas_para(w)
        self.lado = (w - HUECO * (self.columnas - 1)) / self.columnas
        n = len(self.elementos)
        self.paginas = paginas_para(n, self.columnas)
        self.pagina = max(0, min(self.pagina, self.paginas - 1))
        self.avance = float(self.pagina)
        self.anim.stop()
        filas = min(FILAS, -(-len(self.de_pagina(0)) // self.columnas)) if n else 0
        alto = int(filas * self.lado + max(0, filas - 1) * HUECO) + 1
        if self.lienzo.height() != alto:
            self.lienzo.setFixedHeight(max(1, alto))
        self.puntos.poner(self.paginas, self.pagina)
        self.setVisible(n > 0)
        if not self._lado_fino:
            self._lado_fino = int(self.lado)
        self._t_fina.start()
        self.lienzo.update()

    def _pedir_finas(self):
        if int(self.lado) != self._lado_fino:
            self._lado_fino = int(self.lado)
            self._pedidas.clear()
            self.lienzo.update()

    def portada(self, el):
        url = el.get("miniatura") or ""
        lado = self._lado_fino
        if not url or lado <= 0:
            return None
        yo = self

        def listo(_pm):
            try:
                yo.lienzo.update()
            except RuntimeError:
                pass
        primera = url not in self._pedidas
        self._pedidas.add(url)
        return imagenes.pedir(url, lado, lado, "cuadrada", 0, listo if primera else None)

    # ------------------------------------------------------------ páginas

    def ir_a(self, pagina):
        pagina = max(0, min(int(pagina), self.paginas - 1))
        if pagina == self.pagina:
            return
        self.pagina = pagina
        self.puntos.poner(self.paginas, pagina)
        self.anim.stop()
        self.anim.setStartValue(float(self.avance))
        self.anim.setEndValue(float(pagina))
        self.anim.start()

    def _mover(self, v):
        self.avance = float(v)
        self.lienzo.update()
