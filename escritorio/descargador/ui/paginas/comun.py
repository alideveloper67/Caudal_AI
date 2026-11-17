# -*- coding: utf-8 -*-
"""Piezas que comparten varias paginas."""

import time

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import QGridLayout, QWidget

from ...memoria import DiccionarioLimitado
from .. import iconos, imagenes
from ..componentes import Carrusel, RejillaRapida, fuente
from ..estilos import C

# respuestas del catálogo (Inicio, álbumes, listas...): las 200 últimas, y las de más de una
# hora se tiran (ninguna página las acepta tan viejas)
TOPE_CACHE = 200
CADUCA_SEG = 60 * 60
_CACHE = DiccionarioLimitado(TOPE_CACHE)


def cache(clave, minutos=15):
    dato = _CACHE.get(clave)
    if dato and time.time() - dato[0] < minutos * 60:
        return dato[1]
    return None


def guardar_cache(clave, valor):
    ahora = time.time()
    if len(_CACHE) >= TOPE_CACHE // 2:
        for k in [k for k, (t, _v) in _CACHE.items() if ahora - t > CADUCA_SEG]:
            _CACHE.pop(k, None)
    _CACHE[clave] = (ahora, valor)


def pintar_secciones(ctx, layout, secciones, desde=0):
    """Convierte las secciones del catalogo en carruseles y rejillas."""
    for s in secciones[desde:]:
        elementos = s.get("elementos") or []
        if not elementos:
            continue
        mas = None
        if s.get("mas") and s["mas"].get("id"):
            m = s["mas"]
            # el clic manda `checked` como primer argumento: no debe pisar `m`
            mas = (lambda *_a, m=m, t=s["titulo"]: ctx.navegar(
                {"pagina": "genero", "id": m["id"], "params": m.get("params"), "titulo": t}))
        if s.get("estilo") == "filas" and all(e.get("tipo") == "pista" for e in elementos):
            layout.addWidget(RejillaRapida(ctx, s["titulo"], elementos,
                                                  columnas=3 if len(elementos) > 8 else 2,
                                                  filas=4, subtitulo=s.get("estribillo", "")))
        elif s.get("estilo") == "rejilla":
            layout.addWidget(Rejilla(ctx, s["titulo"], elementos))
        else:
            layout.addWidget(Carrusel(ctx, s["titulo"], elementos, mas=mas,
                                             subtitulo=s.get("estribillo", "")))


class Rejilla(QWidget):
    """Tarjetas en varias filas (generos, resultados de 'Mostrar todo')."""

    def __init__(self, ctx, titulo, elementos, ancho=176, padre=None):
        super().__init__(padre)
        from PySide6.QtWidgets import QLabel, QVBoxLayout
        from ..componentes import Tarjeta
        self.ctx = ctx
        self.elementos = elementos
        self.ancho = ancho
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        if titulo:
            t = QLabel(titulo)
            t.setObjectName("titulo_seccion")
            t.setContentsMargins(4, 0, 0, 0)
            v.addWidget(t)
        self.rej = QGridLayout()
        self.rej.setSpacing(6)
        self.rej.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        v.addLayout(self.rej)
        self.tarjetas = []
        for el in elementos:
            tj = Tarjeta(ctx, el, ancho)
            tj.abrir.connect(ctx.abrir_elemento)
            tj.reproducir.connect(ctx.reproducir_elemento)
            tj.menu.connect(ctx.menu_elemento)
            self.tarjetas.append(tj)
        self._columnas = 0
        self._ordenar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ordenar()

    def _ordenar(self):
        if not self.tarjetas:
            return
        ancho_t = self.tarjetas[0].width() + 6
        columnas = max(1, self.width() // ancho_t) if self.width() > 50 else 5
        if columnas == self._columnas:
            return
        self._columnas = columnas
        for tj in self.tarjetas:
            self.rej.removeWidget(tj)
        for i, tj in enumerate(self.tarjetas):
            self.rej.addWidget(tj, i // columnas, i % columnas)


class Atajo(QWidget):
    """Atajo horizontal de Inicio (portada + nombre), como los de Spotify."""

    abrir = Signal(dict)
    reproducir = Signal(dict)

    def __init__(self, ctx, el, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.el = el
        self.setFixedHeight(64)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._encima = False
        self._en_play = False
        self.pm = None
        url = el.get("miniatura") or ""
        if url:
            yo = self

            def listo(pm):
                try:
                    yo.pm = pm
                    yo.update()
                except RuntimeError:
                    pass
            self.pm = imagenes.pedir(url, 64, 64, "cuadrada", 0, listo)

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def _r_play(self):
        return QRectF(self.width() - 50, 14, 36, 36)

    def mouseMoveEvent(self, e):
        dentro = self._r_play().contains(e.position())
        if dentro != self._en_play:
            self._en_play = dentro
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._r_play().contains(e.position()):
                self.reproducir.emit(self.el)
            else:
                self.abrir.emit(self.el)
        elif e.button() == Qt.RightButton:
            self.ctx.menu_elemento(self.el, e.globalPosition().toPoint())

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 6, 6)
        p.fillPath(ruta, QColor(255, 255, 255, 30 if self._encima else 18))
        p.setClipPath(ruta)
        if self.el.get("especial") == "me_gusta":
            from PySide6.QtGui import QLinearGradient
            g = QLinearGradient(0, 0, 64, 64)
            g.setColorAt(0, QColor("#5B3DF5"))
            g.setColorAt(1, QColor("#22D3EE"))
            p.fillRect(QRect(0, 0, 64, 64), g)
            p.drawPixmap(20, 20, iconos.pixmap("corazon_lleno", 24, "#FFFFFF"))
        elif self.pm is not None:
            p.drawPixmap(0, 0, self.pm)
        else:
            p.fillRect(QRect(0, 0, 64, 64), QColor(C["superficie3"]))
            p.drawPixmap(20, 20, iconos.pixmap("musica", 24, C["texto3"]))
        p.setClipping(False)
        ancho = self.width() - 64 - 16 - (50 if self._encima else 0)
        f = fuente(14, QFont.Bold)
        p.setFont(f)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRect(78, 0, ancho, 64), Qt.AlignVCenter | Qt.AlignLeft,
                   QFontMetrics(f).elidedText(self.el.get("titulo") or "", Qt.ElideRight, ancho))
        if self._encima:
            r = self._r_play()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["acento_alto"] if self._en_play else C["acento"]))
            p.drawEllipse(r)
            p.drawPixmap(int(r.center().x() - 8), int(r.center().y() - 9),
                         iconos.pixmap("reproducir", 17, "#06070A"))
