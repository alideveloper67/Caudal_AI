# -*- coding: utf-8 -*-
"""Piezas visuales de Caudal: todo pintado a mano para que vaya fluido."""

import json

from PySide6.QtCore import (QEasingCurve, QEvent, QMimeData, QObject, QPoint, QPointF,
                            QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QCursor, QDrag, QFont, QFontMetrics, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import iconos, imagenes
from .estilos import FONDO, C, FUENTE_TITULO

MIME_PISTAS = "application/x-caudal-pistas"


_FAMILIA_TITULO = None


def _familia_titulo():
    """Segoe UI Variable Display solo existe en Windows 11; en Windows 10, Segoe UI."""
    global _FAMILIA_TITULO
    if _FAMILIA_TITULO is None:
        from PySide6.QtGui import QFontDatabase
        _FAMILIA_TITULO = ("Segoe UI Variable Display"
                           if "Segoe UI Variable Display" in QFontDatabase.families() else "Segoe UI")
    return _FAMILIA_TITULO


def fuente(px, peso=QFont.Normal, titulo=False):
    f = QFont(_familia_titulo() if titulo else "Segoe UI")
    f.setPixelSize(int(px))
    f.setWeight(peso)
    return f


def formato_tiempo(s):
    s = int(s or 0)
    if s <= 0:
        return ""
    h, r = divmod(s, 3600)
    m, seg = divmod(r, 60)
    return f"{h}:{m:02d}:{seg:02d}" if h else f"{m}:{seg:02d}"


def formato_duracion_larga(s):
    s = int(s or 0)
    h, r = divmod(s, 3600)
    m = r // 60
    if h:
        return f"{h} h {m} min"
    return f"{m} min" if m else ""


# ---------------------------------------------------------------- portada

class Portada(QWidget):
    """Imagen recortada que se carga sola en segundo plano."""

    def __init__(self, ancho=48, alto=None, forma="cuadrada", radio=4, icono="musica",
                 padre=None):
        super().__init__(padre)
        self.ancho = ancho
        self.alto = alto or ancho
        self.forma = forma
        self.radio = radio
        self.icono = icono
        self.url = ""
        self.pm = None
        self.setFixedSize(self.ancho, self.alto)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_url(self, url):
        if url == self.url and self.pm is not None:
            return
        self.url = url or ""
        self.pm = None
        if self.url:
            yo = self
            objetivo = self.url

            def listo(pm):
                try:
                    if yo.url == objetivo:
                        yo.pm = pm
                        yo.update()
                except RuntimeError:
                    pass
            self.pm = imagenes.pedir(self.url, self.ancho, self.alto, self.forma, self.radio, listo)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self.pm is not None:
            p.drawPixmap(0, 0, self.pm)
            return
        ruta = QPainterPath()
        r = QRectF(0, 0, self.ancho, self.alto)
        if self.forma == "redonda":
            ruta.addEllipse(r)
        else:
            ruta.addRoundedRect(r, self.radio, self.radio)
        p.fillPath(ruta, QColor(C["superficie3"]))
        lado = int(min(self.ancho, self.alto) * 0.38)
        if lado >= 10:
            p.drawPixmap(int((self.ancho - lado) / 2), int((self.alto - lado) / 2),
                         iconos.pixmap(self.icono, lado, C["texto3"]))


# ---------------------------------------------------------------- botones

class BotonIcono(QPushButton):
    """Boton de icono que se ilumina al pasar el raton y marca su estado activo."""

    def __init__(self, icono, tam=20, ayuda="", lado=32, padre=None, color=None,
                 color_hover=None, conmutable=False):
        super().__init__(padre)
        self._icono = icono
        self._tam = tam
        self._color = color or C["texto2"]
        self._hover = color_hover or C["texto"]
        self._activo = False
        self._punto = False
        self.setCheckable(conmutable)
        self.setFixedSize(lado, lado)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(ayuda)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._encima = False

    def set_icono(self, icono):
        self._icono = icono
        self.update()

    def set_activo(self, activo, punto=True):
        self._activo = bool(activo)
        self._punto = punto and bool(activo)
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
        p.setRenderHint(QPainter.Antialiasing, True)
        if not self.isEnabled():
            color = C["texto3"]
        elif self._activo:
            color = C["acento_alto"] if self._encima else C["acento"]
        else:
            color = self._hover if self._encima else self._color
        if self.isDown():
            color = C["texto2"]
        pm = iconos.pixmap(self._icono, self._tam, color)
        x = (self.width() - self._tam) // 2
        y = (self.height() - self._tam) // 2 - (2 if self._punto else 0)
        p.drawPixmap(x, y, pm)
        if self._punto:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(self.width() / 2, self.height() - 4), 2, 2)


class BotonPlay(QPushButton):
    """El boton redondo de reproducir (cian) que cambia a pausa."""

    def __init__(self, lado=48, padre=None, claro=False):
        super().__init__(padre)
        self.lado = lado
        self.claro = claro
        self.sonando = False
        self.cargando = False
        self.setFixedSize(lado, lado)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._encima = False
        self._giro = 0
        self._reloj = QTimer(self)
        self._reloj.setInterval(30)
        self._reloj.timeout.connect(self._girar)

    def set_sonando(self, si):
        self.sonando = bool(si)
        self.update()

    def set_cargando(self, si):
        self.cargando = bool(si)
        if si:
            self._reloj.start()
        else:
            self._reloj.stop()
        self.update()

    def _girar(self):
        self._giro = (self._giro + 12) % 360
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
        p.setRenderHint(QPainter.Antialiasing, True)
        lado = self.lado
        escala = 1.04 if self._encima and not self.isDown() else (0.96 if self.isDown() else 1.0)
        r = lado / 2 * escala
        centro = QPointF(self.width() / 2, self.height() / 2)
        fondo = QColor("#FFFFFF") if self.claro else QColor(C["acento_alto"] if self._encima else C["acento"])
        p.setPen(Qt.NoPen)
        p.setBrush(fondo)
        p.drawEllipse(centro, r, r)
        tam = int(lado * 0.42)
        pm = iconos.pixmap("pausa" if self.sonando else "reproducir", tam, "#06070A")
        dx = 0 if self.sonando else lado * 0.03
        p.drawPixmap(int(centro.x() - tam / 2 + dx), int(centro.y() - tam / 2), pm)
        if self.cargando:
            lapiz = QPen(QColor(6, 7, 10, 150))
            lapiz.setWidthF(max(2.0, lado * 0.05))
            lapiz.setCapStyle(Qt.RoundCap)
            p.setPen(lapiz)
            p.setBrush(Qt.NoBrush)
            rr = r * 0.82
            p.drawArc(QRectF(centro.x() - rr, centro.y() - rr, rr * 2, rr * 2),
                      -self._giro * 16, 90 * 16)


class Chip(QPushButton):
    def __init__(self, texto, conmutable=True, padre=None):
        super().__init__(texto, padre)
        self.setObjectName("chip")
        self.setCheckable(conmutable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)


# ---------------------------------------------------------------- deslizador

class Deslizador(QWidget):
    """Barra fina como la de Spotify: se ilumina y muestra el punto al pasar."""

    movido = Signal(float)       # mientras se arrastra (0..1)
    soltado = Signal(float)      # al soltar (0..1)

    def __init__(self, alto=16, rueda=False, padre=None):
        super().__init__(padre)
        self.setFixedHeight(alto)
        self.setMinimumWidth(60)
        self.valor = 0.0
        self.buffer = 0.0
        self.marcas = []
        self.arrastrando = False
        self._encima = False
        self.rueda = rueda
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._x_raton = None

    def set_valor(self, v):
        if self.arrastrando:
            return
        self.valor = max(0.0, min(1.0, float(v or 0)))
        self.update()

    def set_buffer(self, v):
        self.buffer = max(0.0, min(1.0, float(v or 0)))
        self.update()

    def set_marcas(self, marcas):
        self.marcas = [m for m in marcas if 0 < m < 1]
        self.update()

    def _valor_en(self, x):
        margen = 6
        return max(0.0, min(1.0, (x - margen) / max(1, self.width() - 2 * margen)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.arrastrando = True
            self.valor = self._valor_en(e.position().x())
            self.movido.emit(self.valor)
            self.update()

    def mouseMoveEvent(self, e):
        self._x_raton = e.position().x()
        if self.arrastrando:
            self.valor = self._valor_en(e.position().x())
            self.movido.emit(self.valor)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.arrastrando and e.button() == Qt.LeftButton:
            self.arrastrando = False
            self.valor = self._valor_en(e.position().x())
            self.soltado.emit(self.valor)
            self.update()

    def wheelEvent(self, e):
        if not self.rueda:
            e.ignore()
            return
        paso = 0.05 if e.angleDelta().y() > 0 else -0.05
        self.valor = max(0.0, min(1.0, self.valor + paso))
        self.soltado.emit(self.valor)
        self.update()

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self._x_raton = None
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        margen = 6
        ancho = self.width() - 2 * margen
        y = self.height() / 2
        grosor = 4
        pista = QRectF(margen, y - grosor / 2, ancho, grosor)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 46))
        p.drawRoundedRect(pista, 2, 2)
        if self.buffer > self.valor:
            p.setBrush(QColor(255, 255, 255, 34))
            p.drawRoundedRect(QRectF(margen, y - grosor / 2, ancho * self.buffer, grosor), 2, 2)
        activo = self._encima or self.arrastrando
        p.setBrush(QColor(C["acento"]) if activo else QColor(C["texto"]))
        p.drawRoundedRect(QRectF(margen, y - grosor / 2, ancho * self.valor, grosor), 2, 2)
        if self.marcas:
            p.setBrush(QColor(C["panel"]))
            for m in self.marcas:
                p.drawRect(QRectF(margen + ancho * m - 1, y - grosor / 2, 2, grosor))
        if activo:
            p.setBrush(QColor("#FFFFFF"))
            p.drawEllipse(QPointF(margen + ancho * self.valor, y), 6, 6)


# ---------------------------------------------------------------- filas

class FilaPista(QWidget):
    """Una cancion en una lista. Una sola pieza pintada: hover, numero que se
    vuelve play, portada, titulo/artista, album, corazon, duracion y menu."""

    ALTO = 56

    reproducir = Signal(int)
    menu = Signal(int, QPoint)
    me_gusta = Signal(int)
    ir_artista = Signal(dict)
    ir_album = Signal(dict)

    def __init__(self, ctx, pista, indice, numero=None, mostrar_album=True,
                 mostrar_portada=True, mostrar_numero=True, arrastrable=True, padre=None,
                 compacto=False):
        super().__init__(padre)
        self.ctx = ctx
        self.pista = pista
        self.indice = indice
        self.compacto = compacto
        self.numero = numero if numero is not None else indice + 1
        self.mostrar_album = mostrar_album
        self.mostrar_portada = mostrar_portada
        self.mostrar_numero = mostrar_numero
        self.arrastrable = arrastrable
        self.setFixedHeight(self.ALTO)
        self.setMouseTracking(True)
        self._encima = False
        self._zona = ""
        self._rects = {}
        self._rects_artistas = []
        self._pm = None
        self._pulsado_en = None
        if mostrar_portada:
            self._pedir_portada()

    def _pedir_portada(self):
        url = self.pista.get("miniatura") or ""
        yo = self

        def listo(pm):
            try:
                yo._pm = pm
                yo.update()
            except RuntimeError:
                pass
        self._pm = imagenes.pedir(url, 40, 40, "cuadrada", 4, listo) if url else None

    def es_actual(self):
        actual = self.ctx.reproductor.actual
        if not actual:
            return False
        if actual is self.pista:
            return True
        a, b = actual.get("clave"), self.pista.get("clave")
        if a and a == b:
            return True
        va, vb = actual.get("video_id"), self.pista.get("video_id")
        return bool(va and va == vb)

    # --- raton
    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self._zona = ""
        self.unsetCursor()
        self.update()

    def _zona_en(self, pos):
        for nombre, r in self._rects.items():
            if r.contains(pos):
                return nombre
        return ""

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        zona = self._zona_en(pos)
        if zona != self._zona:
            self._zona = zona
            if zona in ("artista", "album", "corazon", "puntos", "numero"):
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.unsetCursor()
            self.update()
        if (self.arrastrable and self._pulsado_en is not None
                and (pos - self._pulsado_en).manhattanLength() > 12):
            self._pulsado_en = None
            self._arrastrar()

    def _arrastrar(self):
        datos = QMimeData()
        datos.setData(MIME_PISTAS, json.dumps([self.pista], ensure_ascii=False).encode("utf-8"))
        datos.setText(self.pista.get("titulo") or "")
        drag = QDrag(self)
        drag.setMimeData(datos)
        # una etiqueta flotante con el titulo, como en Spotify
        fm = QFontMetrics(fuente(13, QFont.DemiBold))
        texto = fm.elidedText(self.pista.get("titulo") or "", Qt.ElideRight, 260)
        from PySide6.QtGui import QPixmap
        pm = QPixmap(fm.horizontalAdvance(texto) + 28, 32)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"]))
        p.drawRoundedRect(QRectF(0, 0, pm.width(), pm.height()), 6, 6)
        p.setPen(QColor(C["texto"]))
        p.setFont(fuente(13, QFont.DemiBold))
        p.drawText(QRectF(14, 0, pm.width() - 14, 32), Qt.AlignVCenter, texto)
        p.end()
        drag.setPixmap(pm)
        drag.exec(Qt.CopyAction)

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        zona = self._zona_en(pos)
        if e.button() == Qt.RightButton:
            self.menu.emit(self.indice, e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton:
            return
        self._pulsado_en = pos
        if zona == "corazon":
            self.me_gusta.emit(self.indice)
        elif zona == "puntos":
            self.menu.emit(self.indice, self.mapToGlobal(self._rects["puntos"].bottomLeft()))
        elif zona == "numero" and self._encima:
            if self.es_actual():
                self.ctx.reproductor.alternar()
            else:
                self.reproducir.emit(self.indice)
        elif zona == "artista":
            artistas = [a for a in self.pista.get("artistas") or [] if a.get("id")]
            if artistas:
                x = pos.x()
                elegido = artistas[0]
                for a, r in self._rects_artistas:
                    if r.left() <= x <= r.right():
                        elegido = a
                self.ir_artista.emit(elegido)
        elif zona == "album":
            alb = self.pista.get("album") or {}
            if alb.get("id"):
                self.ir_album.emit(alb)

    def mouseReleaseEvent(self, e):
        self._pulsado_en = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton and self._zona_en(e.position().toPoint()) not in (
                "corazon", "puntos", "artista", "album"):
            self.reproducir.emit(self.indice)

    # --- pintado
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        actual = self.es_actual()
        sonando = actual and self.ctx.reproductor.estado in ("sonando", "cargando")
        if self._encima:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(0, 0, w, h), 6, 6)
        self._rects = {}
        x = 12
        # numero / play / ecualizador
        if self.mostrar_numero:
            r_num = QRect(x, 0, 28, h)
            self._rects["numero"] = r_num
            if self._encima:
                icono = "pausa" if (actual and sonando) else "reproducir"
                p.drawPixmap(r_num.center().x() - 8, h // 2 - 8, iconos.pixmap(icono, 16, C["texto"]))
            elif actual:
                p.drawPixmap(r_num.center().x() - 7, h // 2 - 7,
                             iconos.pixmap("sonando" if sonando else "reproducir", 14, C["acento"]))
            else:
                p.setPen(QColor(C["texto2"]))
                p.setFont(fuente(14))
                p.drawText(r_num, Qt.AlignCenter, str(self.numero))
            x += 40
        if self.mostrar_portada:
            r_por = QRect(x, (h - 40) // 2, 40, 40)
            if self._pm is not None:
                p.drawPixmap(r_por.topLeft(), self._pm)
            else:
                ruta = QPainterPath()
                ruta.addRoundedRect(QRectF(r_por), 4, 4)
                p.fillPath(ruta, QColor(C["superficie3"]))
                p.drawPixmap(r_por.x() + 12, r_por.y() + 12,
                             iconos.pixmap("video" if self.pista.get("es_video") else "musica",
                                           16, C["texto3"]))
            if not self.mostrar_numero and self._encima:
                p.fillRect(r_por, QColor(0, 0, 0, 120))
                p.drawPixmap(r_por.center().x() - 8, r_por.center().y() - 8,
                             iconos.pixmap("pausa" if (actual and sonando) else "reproducir",
                                           16, "#FFFFFF"))
                self._rects["numero"] = r_por
            x += 52

        # columnas de la derecha
        derecha = w - 12
        r_puntos = QRect(derecha - 28, (h - 28) // 2, 28, 28)
        self._rects["puntos"] = r_puntos
        if self._encima:
            p.drawPixmap(r_puntos.x() + 4, r_puntos.y() + 4,
                         iconos.pixmap("puntos", 20, C["texto"] if self._zona == "puntos" else C["texto2"]))
        gusta = self.ctx.coleccion.me_gusta(self.pista.get("clave"))
        if self.compacto:
            # en la cola y el panel: el titulo manda; solo el menu y el corazon
            derecha -= 32 if self._encima else 4
            if gusta:
                r_cor = QRect(derecha - 20, (h - 20) // 2, 20, 20)
                self._rects["corazon"] = r_cor
                p.drawPixmap(r_cor.x() + 2, r_cor.y() + 2,
                             iconos.pixmap("corazon_lleno", 16, C["acento"]))
                derecha -= 26
        else:
            derecha -= 36
            dur = formato_tiempo(self.pista.get("duracion"))
            p.setFont(fuente(13))
            p.setPen(QColor(C["texto2"]))
            r_dur = QRect(derecha - 44, 0, 44, h)
            p.drawText(r_dur, Qt.AlignVCenter | Qt.AlignRight, dur)
            derecha -= 58
            descargada = self.ctx.coleccion.esta_descargada(self.pista)
            r_desc = QRect(derecha - 16, (h - 16) // 2, 16, 16)
            if descargada:
                p.drawPixmap(r_desc.topLeft(), iconos.pixmap("descargado", 16, C["acento"]))
            derecha -= 26
            r_cor = QRect(derecha - 22, (h - 22) // 2, 22, 22)
            self._rects["corazon"] = r_cor
            if gusta or self._encima:
                color = C["acento"] if gusta else (C["texto"] if self._zona == "corazon" else C["texto2"])
                p.drawPixmap(r_cor.x() + 2, r_cor.y() + 2,
                             iconos.pixmap("corazon_lleno" if gusta else "corazon", 18, color))
            derecha -= 34

        # album
        ancho_texto = derecha - x
        if self.mostrar_album and w > 640:
            ancho_album = int(ancho_texto * 0.38)
            ancho_texto -= ancho_album + 16
            alb = (self.pista.get("album") or {}).get("nombre") or ""
            if alb:
                fm = QFontMetrics(fuente(13))
                t = fm.elidedText(alb, Qt.ElideRight, ancho_album)
                r_alb = QRect(x + ancho_texto + 16, 0, fm.horizontalAdvance(t), h)
                hay_id = bool((self.pista.get("album") or {}).get("id"))
                if hay_id:
                    self._rects["album"] = r_alb.adjusted(0, h // 2 - 10, 0, -(h // 2 - 10))
                f = fuente(13)
                f.setUnderline(self._zona == "album" and hay_id)
                p.setFont(f)
                p.setPen(QColor(C["texto"] if self._zona == "album" else C["texto2"]))
                p.drawText(r_alb, Qt.AlignVCenter | Qt.AlignLeft, t)

        # titulo y artistas
        titulo = self.pista.get("titulo") or ""
        p.setFont(fuente(14.5, QFont.DemiBold))
        fm = QFontMetrics(p.font())
        p.setPen(QColor(C["acento"] if actual else C["texto"]))
        p.drawText(QRect(x, 8, ancho_texto, 22), Qt.AlignVCenter | Qt.AlignLeft,
                   fm.elidedText(titulo, Qt.ElideRight, ancho_texto))
        xa = x
        if self.pista.get("explicito"):
            r_e = QRectF(xa, 34, 15, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["texto2"]))
            p.drawRoundedRect(r_e, 2, 2)
            p.setPen(QColor(C["panel"]))
            p.setFont(fuente(10, QFont.Bold))
            p.drawText(r_e, Qt.AlignCenter, "E")
            xa += 21
        if self.pista.get("es_video") and not self.pista.get("archivo"):
            p.drawPixmap(xa, 34, iconos.pixmap("video", 15, C["texto3"]))
            xa += 21
        self._rects_artistas = []
        artistas = self.pista.get("artistas") or []
        f_art = fuente(13)
        fm_a = QFontMetrics(f_art)
        restante = x + ancho_texto - xa
        if artistas:
            for i, a in enumerate(artistas):
                nombre = a.get("nombre") or ""
                sep = ", " if i < len(artistas) - 1 else ""
                ancho = fm_a.horizontalAdvance(nombre)
                if ancho > restante:
                    nombre = fm_a.elidedText(nombre, Qt.ElideRight, max(0, restante))
                    ancho = fm_a.horizontalAdvance(nombre)
                    sep = ""
                r_a = QRect(xa, 31, ancho, 20)
                encima = (self._zona == "artista" and a.get("id")
                          and self._x_raton_en(r_a))
                f = fuente(13)
                f.setUnderline(bool(encima))
                p.setFont(f)
                p.setPen(QColor(C["texto"] if (self._encima and a.get("id") and encima) else C["texto2"]))
                p.drawText(r_a, Qt.AlignVCenter | Qt.AlignLeft, nombre)
                if a.get("id"):
                    self._rects_artistas.append((a, r_a))
                xa += ancho
                restante -= ancho
                if sep and restante > 12:
                    p.setFont(fuente(13))
                    p.setPen(QColor(C["texto2"]))
                    p.drawText(QRect(xa, 31, 12, 20), Qt.AlignVCenter | Qt.AlignLeft, sep)
                    xa += fm_a.horizontalAdvance(sep)
                    restante -= fm_a.horizontalAdvance(sep)
                if restante <= 8:
                    break
            if self._rects_artistas:
                izquierda = min(r.left() for _a, r in self._rects_artistas)
                derecha_a = max(r.right() for _a, r in self._rects_artistas)
                self._rects["artista"] = QRect(izquierda, 31, derecha_a - izquierda, 20)
        else:
            sub = self.pista.get("subtitulo") or self.pista.get("artista") or ""
            p.setFont(f_art)
            p.setPen(QColor(C["texto2"]))
            p.drawText(QRect(xa, 31, max(0, restante), 20), Qt.AlignVCenter | Qt.AlignLeft,
                       fm_a.elidedText(sub, Qt.ElideRight, max(0, restante)))

    def _x_raton_en(self, r):
        pos = self.mapFromGlobal(QCursor.pos())
        return r.left() <= pos.x() <= r.right() and 28 <= pos.y() <= 52


class ListaPistas(QWidget):
    """Lista de canciones con cabecera de columnas."""

    def __init__(self, ctx, mostrar_album=True, mostrar_cabecera=True, mostrar_numero=True,
                 padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.mostrar_album = mostrar_album
        self.mostrar_numero = mostrar_numero
        self.pistas = []
        self.contexto = None
        self.filas = []
        self.al_reproducir = None          # funcion(indice) opcional
        self.al_menu_extra = None          # funcion(menu, indice) para anadir opciones
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(0)
        self.cabecera = None
        if mostrar_cabecera:
            self.cabecera = self._crear_cabecera()
            self.v.addWidget(self.cabecera)
        self.caja = QVBoxLayout()
        self.caja.setSpacing(0)
        self.v.addLayout(self.caja)
        ctx.reproductor.pista_cambio.connect(self._repintar)
        ctx.reproductor.estado_cambio.connect(self._repintar)
        ctx.me_gusta_cambio.connect(self._repintar)
        ctx.descargas_cambio.connect(self._repintar)

    def _crear_cabecera(self):
        caja = QWidget()
        caja.setFixedHeight(36)
        h = QHBoxLayout(caja)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(0)
        if self.mostrar_numero:
            n = QLabel("#")
            n.setFixedWidth(40)
            n.setAlignment(Qt.AlignCenter)
            n.setObjectName("secundario")
            h.addWidget(n)
        t = QLabel("Título")
        t.setObjectName("secundario")
        h.addWidget(t, 62)
        self.et_album = QLabel("Álbum" if self.mostrar_album else "")
        self.et_album.setObjectName("secundario")
        h.addWidget(self.et_album, 38)
        h.addSpacing(120)
        reloj = QLabel()
        reloj.setPixmap(iconos.pixmap("reloj", 16, C["texto2"]))
        h.addWidget(reloj)
        h.addSpacing(48)
        linea = QFrame(caja)
        linea.setObjectName("separador")
        caja.linea = linea
        return caja

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.cabecera is not None:
            self.cabecera.linea.setGeometry(0, 35, self.width(), 1)
            self.et_album.setVisible(self.mostrar_album and self.width() > 640)

    def set_pistas(self, pistas, contexto=None):
        self.pistas = list(pistas)
        self.contexto = contexto
        for f in self.filas:
            f.deleteLater()
        self.filas = []
        if self.cabecera is not None:
            self.cabecera.setVisible(bool(pistas))
        # en tandas, para que una lista grande no congele la ventana
        self._pendientes = list(enumerate(self.pistas))
        self._tanda()

    def _tanda(self):
        lote, self._pendientes = self._pendientes[:60], self._pendientes[60:]
        for i, p in lote:
            fila = FilaPista(self.ctx, p, i, mostrar_album=self.mostrar_album,
                             mostrar_numero=self.mostrar_numero)
            fila.reproducir.connect(self._reproducir)
            fila.menu.connect(self._menu)
            fila.me_gusta.connect(self._me_gusta)
            fila.ir_artista.connect(lambda a: self.ctx.navegar({"pagina": "artista", "id": a["id"]}))
            fila.ir_album.connect(lambda a: self.ctx.navegar({"pagina": "album", "id": a["id"]}))
            self.caja.addWidget(fila)
            self.filas.append(fila)
        if self._pendientes:
            QTimer.singleShot(0, self._tanda)

    def _reproducir(self, i):
        if self.al_reproducir:
            self.al_reproducir(i)
        else:
            self.ctx.reproducir_lista(self.pistas, i, self.contexto)

    def _menu(self, i, pos):
        if 0 <= i < len(self.pistas):
            self.ctx.menu_pista(self.pistas[i], pos, extra=(
                (lambda m: self.al_menu_extra(m, i)) if self.al_menu_extra else None))

    def _me_gusta(self, i):
        if 0 <= i < len(self.pistas):
            self.ctx.alternar_me_gusta(self.pistas[i])

    def _repintar(self, *_):
        for f in self.filas:
            f.update()


# ---------------------------------------------------------------- tarjetas

class Tarjeta(QWidget):
    """Tarjeta de album, lista, artista, radio, cancion o video."""

    abrir = Signal(dict)
    reproducir = Signal(dict)
    menu = Signal(dict, QPoint)

    def __init__(self, ctx, elemento, ancho=176, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.el = elemento
        tipo = elemento.get("tipo")
        self.es_video = tipo == "pista" and elemento.get("es_video") and not elemento.get("archivo")
        self.es_genero = tipo == "genero"
        if self.es_video:
            ancho = int(ancho * 1.55)
        self.ancho = ancho
        self.lado_img = ancho - 24
        self.alto_img = int(self.lado_img * 9 / 16) if self.es_video else self.lado_img
        if self.es_genero:
            self.alto_img = int(self.lado_img * 0.62)
        self.forma = "redonda" if tipo == "artista" else "cuadrada"
        alto_textos = 0 if self.es_genero else 52
        self.setFixedSize(ancho, 12 + self.alto_img + 10 + alto_textos + 8)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._encima = False
        self._en_play = False
        self._pm = None
        self._anim = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._paso)
        if self.es_genero:
            self._img_genero = None
            from ..hilos import en_segundo_plano
            from .. import catalogo
            yo = self

            def con_url(url):
                if not url:
                    return
                imagenes.imagen(url, lambda img: _poner_img(img))

            def _poner_img(img):
                try:
                    yo._img_genero = img
                    yo.update()
                except RuntimeError:
                    pass
            en_segundo_plano(catalogo.portada_genero, elemento.get("id"), elemento.get("params"),
                             ok=con_url, error=lambda _e: None, dueno=self)
        if not self.es_genero:
            url = elemento.get("miniatura") or elemento.get("foto") or ""
            yo = self

            def listo(pm):
                try:
                    yo._pm = pm
                    yo.update()
                except RuntimeError:
                    pass
            if url:
                self._pm = imagenes.pedir(url, self.lado_img, self.alto_img, self.forma,
                                          6 if not self.es_video else 8, listo)

    def _paso(self):
        objetivo = 1.0 if self._encima else 0.0
        self._anim += (objetivo - self._anim) * 0.35
        if abs(self._anim - objetivo) < 0.02:
            self._anim = objetivo
            self._timer.stop()
        self.update()

    def enterEvent(self, e):
        self._encima = True
        self._timer.start()

    def leaveEvent(self, e):
        self._encima = False
        self._en_play = False
        self._timer.start()

    def _rect_play(self):
        lado = 46
        return QRectF(12 + self.lado_img - lado - 8, 12 + self.alto_img - lado - 8, lado, lado)

    def mouseMoveEvent(self, e):
        dentro = self._rect_play().contains(e.position()) and not self.es_genero
        if dentro != self._en_play:
            self._en_play = dentro
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.menu.emit(self.el, e.globalPosition().toPoint())
            return
        if e.button() != Qt.LeftButton:
            return
        self._pulso = True     # el clic se cuenta al soltar: así también se puede arrastrar desde aquí

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not getattr(self, "_pulso", False):
            return
        self._pulso = False
        if not self.rect().contains(e.position().toPoint()):
            return
        if not self.es_genero and self._rect_play().contains(e.position()):
            self.reproducir.emit(self.el)
        else:
            self.abrir.emit(self.el)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        if self._anim > 0.01 and not self.es_genero:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(16 * self._anim)))
            p.drawRoundedRect(QRectF(0, 0, w, self.height()), 8, 8)
        r_img = QRectF(12, 12, self.lado_img, self.alto_img)
        if self.es_genero:
            ruta = QPainterPath()
            ruta.addRoundedRect(r_img, 8, 8)
            color = QColor(self.el.get("color") or C["violeta"])
            grad = QLinearGradient(r_img.topLeft(), r_img.bottomRight())
            grad.setColorAt(0, color.lighter(115))
            grad.setColorAt(1, color.darker(160))
            p.fillPath(ruta, grad)
            p.save()
            p.setClipPath(ruta)
            img = getattr(self, "_img_genero", None)
            if img is not None and not img.isNull():
                # la portada inclinada asomando por la esquina, con su sombra
                lado = r_img.height() * 0.78
                p.translate(r_img.right() - lado * 0.42, r_img.bottom() - lado * 0.50)
                p.rotate(25 - (4 if self._encima else 0))
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(0, 0, 0, 90))
                p.drawRoundedRect(QRectF(-lado / 2 + 4, -lado / 2 + 6, lado, lado), 4, 4)
                p.setRenderHint(QPainter.SmoothPixmapTransform, True)
                p.drawImage(QRectF(-lado / 2, -lado / 2, lado, lado), img)
            p.restore()
            if self._encima:
                p.fillPath(ruta, QColor(255, 255, 255, 22))
            p.setPen(QColor("#FFFFFF"))
            p.setFont(fuente(17, QFont.Bold, True))
            p.drawText(r_img.adjusted(14, 12, -(r_img.width() * 0.32), -10),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.el.get("titulo") or "")
            return
        if self.el.get("tipo") == "me_gusta":
            ruta = QPainterPath()
            ruta.addRoundedRect(r_img, 6, 6)
            grad = QLinearGradient(r_img.topLeft(), r_img.bottomRight())
            grad.setColorAt(0, QColor("#5B3DF5"))
            grad.setColorAt(1, QColor("#22D3EE"))
            p.fillPath(ruta, grad)
            lado = int(self.alto_img * 0.34)
            p.drawPixmap(int(r_img.center().x() - lado / 2), int(r_img.center().y() - lado / 2),
                         iconos.pixmap("corazon_lleno", lado, "#FFFFFF"))
        elif self._pm is not None:
            p.drawPixmap(r_img.topLeft(), self._pm)
        else:
            ruta = QPainterPath()
            if self.forma == "redonda":
                ruta.addEllipse(r_img)
            else:
                ruta.addRoundedRect(r_img, 6, 6)
            p.fillPath(ruta, QColor(C["superficie3"]))
            icono = {"artista": "usuario", "album": "album", "lista": "lista",
                     "radio": "radio"}.get(self.el.get("tipo"), "musica")
            lado = int(self.alto_img * 0.32)
            p.drawPixmap(int(r_img.center().x() - lado / 2), int(r_img.center().y() - lado / 2),
                         iconos.pixmap(icono, lado, C["texto3"]))
        # boton de reproducir que sube al pasar el raton
        if self._anim > 0.01:
            r = self._rect_play().translated(0, 8 * (1 - self._anim))
            p.setOpacity(self._anim)
            sombra = QColor(0, 0, 0, 110)
            p.setPen(Qt.NoPen)
            p.setBrush(sombra)
            p.drawEllipse(r.translated(0, 3))
            p.setBrush(QColor(C["acento_alto"] if self._en_play else C["acento"]))
            p.drawEllipse(r)
            p.drawPixmap(int(r.center().x() - 9), int(r.center().y() - 10),
                         iconos.pixmap("reproducir", 20, "#06070A"))
            p.setOpacity(1.0)
        # textos
        ancho_t = self.lado_img
        y = 12 + self.alto_img + 10
        f1 = fuente(14.5, QFont.DemiBold)
        p.setFont(f1)
        p.setPen(QColor(C["texto"]))
        fm = QFontMetrics(f1)
        p.drawText(QRect(12, y, ancho_t, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   fm.elidedText(self.el.get("titulo") or "", Qt.ElideRight, ancho_t))
        sub = self.el.get("subtitulo") or self.el.get("artista") or ""
        if self.el.get("tipo") == "artista" and not sub:
            sub = "Artista"
        f2 = fuente(12.5)
        p.setFont(f2)
        p.setPen(QColor(C["texto2"]))
        fm2 = QFontMetrics(f2)
        lineas = _partir(sub, fm2, ancho_t, 2)
        for i, linea in enumerate(lineas):
            p.drawText(QRect(12, y + 22 + i * 17, ancho_t, 17), Qt.AlignLeft | Qt.AlignVCenter, linea)


def _partir(texto, fm, ancho, max_lineas):
    palabras = (texto or "").split()
    lineas, actual = [], ""
    for pal in palabras:
        prueba = (actual + " " + pal).strip()
        if fm.horizontalAdvance(prueba) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = pal
            if len(lineas) == max_lineas - 1:
                break
    resto = " ".join(palabras[len(" ".join(lineas).split()):])
    if len(lineas) < max_lineas and resto:
        lineas.append(fm.elidedText(resto, Qt.ElideRight, ancho))
    return lineas[:max_lineas]


class _AreaHorizontal(QScrollArea):
    """Scroll horizontal que deja pasar la rueda vertical a la pagina."""

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ShiftModifier or abs(e.angleDelta().x()) > abs(e.angleDelta().y()):
            barra = self.horizontalScrollBar()
            barra.setValue(barra.value() - (e.angleDelta().x() or e.angleDelta().y()))
            e.accept()
        else:
            e.ignore()


class Carrusel(QWidget):
    """Una fila de tarjetas con titulo, 'Mostrar todo' y flechas."""

    def __init__(self, ctx, titulo, elementos, al_abrir=None, mas=None, subtitulo="",
                 ancho_tarjeta=176, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        cab = QHBoxLayout()
        cab.setContentsMargins(4, 0, 0, 0)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        if subtitulo:
            s = QLabel(subtitulo.upper())
            s.setObjectName("ayuda")
            textos.addWidget(s)
        t = QLabel(titulo)
        t.setObjectName("titulo_seccion")
        textos.addWidget(t)
        cab.addLayout(textos)
        cab.addStretch(1)
        if mas:
            bt_mas = QPushButton("Mostrar todo")
            bt_mas.setObjectName("enlace")
            bt_mas.setCursor(Qt.PointingHandCursor)
            bt_mas.clicked.connect(mas)
            cab.addWidget(bt_mas)
        self.bt_izq = BotonIcono("atras", 16, "", 30)
        self.bt_der = BotonIcono("adelante", 16, "", 30)
        for b in (self.bt_izq, self.bt_der):
            b.setStyleSheet(f"QPushButton{{background:{C['superficie2']};border:none;border-radius:15px;}}"
                            f"QPushButton:hover{{background:{C['superficie3']};}}")
            cab.addWidget(b)
        v.addLayout(cab)

        self.area = _AreaHorizontal()
        self.area.setObjectName("lienzo")
        self.area.setWidgetResizable(True)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setFrameShape(QFrame.NoFrame)
        interior = QWidget()
        fila = QHBoxLayout(interior)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(4)
        alto = 0
        for el in elementos:
            tj = Tarjeta(ctx, el, ancho_tarjeta)
            tj.abrir.connect(al_abrir or ctx.abrir_elemento)
            tj.reproducir.connect(ctx.reproducir_elemento)
            tj.menu.connect(ctx.menu_elemento)
            fila.addWidget(tj)
            alto = max(alto, tj.height())
        fila.addStretch(1)
        self.area.setWidget(interior)
        self.area.setFixedHeight(alto + 2)
        v.addWidget(self.area)

        self.anim = QPropertyAnimation(self.area.horizontalScrollBar(), b"value", self)
        self.anim.setDuration(380)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.bt_izq.clicked.connect(lambda: self._desplazar(-1))
        self.bt_der.clicked.connect(lambda: self._desplazar(1))
        self.area.horizontalScrollBar().rangeChanged.connect(self._flechas)
        self.area.horizontalScrollBar().valueChanged.connect(self._flechas)
        QTimer.singleShot(0, self._flechas)

    def _desplazar(self, sentido):
        barra = self.area.horizontalScrollBar()
        destino = barra.value() + sentido * int(self.area.viewport().width() * 0.85)
        self.anim.stop()
        self.anim.setStartValue(barra.value())
        self.anim.setEndValue(max(0, min(barra.maximum(), destino)))
        self.anim.start()

    def _flechas(self, *_):
        barra = self.area.horizontalScrollBar()
        self.bt_izq.setEnabled(barra.value() > 0)
        self.bt_der.setEnabled(barra.value() < barra.maximum())
        visible = barra.maximum() > 0
        self.bt_izq.setVisible(visible)
        self.bt_der.setVisible(visible)


class FilaCompacta(QWidget):
    """Cancion en una rejilla de 'Seleccion rapida': portada + titulo + artista."""

    def __init__(self, ctx, pista, al_reproducir, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.pista = pista
        self.al_reproducir = al_reproducir
        self.setFixedHeight(60)
        self.setMinimumWidth(220)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._encima = False
        self._pm = None
        url = pista.get("miniatura") or ""
        yo = self

        def listo(pm):
            try:
                yo._pm = pm
                yo.update()
            except RuntimeError:
                pass
        if url:
            self._pm = imagenes.pedir(url, 48, 48, "cuadrada", 4, listo)
        ctx.reproductor.pista_cambio.connect(lambda *_: self.update())

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.ctx.menu_pista(self.pista, e.globalPosition().toPoint())
        elif e.button() == Qt.LeftButton:
            self._pulso = True     # se reproduce al soltar, para poder arrastrar desde aquí

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and getattr(self, "_pulso", False):
            self._pulso = False
            if self.rect().contains(e.position().toPoint()):
                self.al_reproducir(self.pista)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        if self._encima:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 6, 6)
        r = QRect(6, 6, 48, 48)
        if self._pm is not None:
            p.drawPixmap(r.topLeft(), self._pm)
        else:
            ruta = QPainterPath()
            ruta.addRoundedRect(QRectF(r), 4, 4)
            p.fillPath(ruta, QColor(C["superficie3"]))
        if self._encima:
            p.fillRect(r, QColor(0, 0, 0, 110))
            p.drawPixmap(r.center().x() - 9, r.center().y() - 9,
                         iconos.pixmap("reproducir", 18, "#FFFFFF"))
        actual = self.ctx.reproductor.actual
        es_actual = bool(actual and actual.get("video_id") and
                         actual.get("video_id") == self.pista.get("video_id"))
        ancho = self.width() - 70
        f = fuente(14, QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(C["acento"] if es_actual else C["texto"]))
        fm = QFontMetrics(f)
        p.drawText(QRect(64, 10, ancho, 20), Qt.AlignVCenter,
                   fm.elidedText(self.pista.get("titulo") or "", Qt.ElideRight, ancho))
        f2 = fuente(12.5)
        p.setFont(f2)
        p.setPen(QColor(C["texto2"]))
        sub = self.pista.get("artista") or self.pista.get("subtitulo") or ""
        if self.pista.get("subtitulo") and self.pista.get("artista"):
            sub = f"{self.pista['artista']} • {self.pista['subtitulo']}"
        p.drawText(QRect(64, 31, ancho, 18), Qt.AlignVCenter,
                   QFontMetrics(f2).elidedText(sub, Qt.ElideRight, ancho))


class RejillaRapida(QWidget):
    """Canciones en columnas (la 'Seleccion rapida' de YouTube Music)."""

    def __init__(self, ctx, titulo, pistas, columnas=3, filas=4, subtitulo="", padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.pistas = pistas
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        cab = QHBoxLayout()
        cab.setContentsMargins(4, 0, 0, 0)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        if subtitulo:
            s = QLabel(subtitulo.upper())
            s.setObjectName("ayuda")
            textos.addWidget(s)
        t = QLabel(titulo)
        t.setObjectName("titulo_seccion")
        textos.addWidget(t)
        cab.addLayout(textos)
        cab.addStretch(1)
        bt = QPushButton("  Reproducir todo")
        bt.setObjectName("contorno")
        bt.setIcon(iconos.icono("reproducir", 14, C["texto"]))
        bt.setCursor(Qt.PointingHandCursor)
        bt.clicked.connect(lambda: ctx.reproducir_lista(pistas, 0, {"tipo": "seleccion",
                                                                     "id": titulo, "titulo": titulo}))
        cab.addWidget(bt)
        v.addLayout(cab)
        from PySide6.QtWidgets import QGridLayout
        rej = QGridLayout()
        rej.setHorizontalSpacing(8)
        rej.setVerticalSpacing(0)
        for i, pista in enumerate(pistas[:columnas * filas]):
            fila = FilaCompacta(ctx, pista, lambda p, i=i: ctx.reproducir_lista(
                self.pistas, i, {"tipo": "seleccion", "id": titulo, "titulo": titulo}))
            rej.addWidget(fila, i % filas, i // filas)
        for c in range(columnas):
            rej.setColumnStretch(c, 1)
        v.addLayout(rej)


# ---------------------------------------------------------------- paginas

class Lienzo(QWidget):
    """Interior de pagina que pinta un degradado de color arriba."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.color = None
        self.alto_degradado = 340
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_color(self, color):
        self.color = QColor(color) if color else None
        self.update()

    def paintEvent(self, _e):
        if not self.color:
            return
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.alto_degradado)
        c1 = QColor(self.color)
        c2 = QColor(C["panel"])
        if FONDO["activo"]:                  # con «Fondo de Caudal» el degradado deja ver la imagen
            c1.setAlpha(120)
            c2.setAlpha(0)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.fillRect(QRect(0, 0, self.width(), self.alto_degradado), grad)


class _RuedaSuave(QObject):
    """Desplazamiento suave con la rueda del raton (en vez de saltos secos)."""

    def __init__(self, area):
        super().__init__(area)
        self.area = area
        self.barra = area.verticalScrollBar()
        self.anim = QPropertyAnimation(self.barra, b"value", self)
        self.anim.setDuration(260)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.destino = None
        area.viewport().installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Wheel and not (e.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
            d = e.angleDelta().y()
            if d == 0 or e.pixelDelta().y():
                return False          # touchpads ya desplazan suave por su cuenta
            if self.anim.state() != QPropertyAnimation.Running:
                self.destino = self.barra.value()
            paso = -d / 120 * max(110, self.area.viewport().height() * 0.16)
            self.destino = max(self.barra.minimum(), min(self.barra.maximum(), self.destino + paso))
            self.anim.stop()
            self.anim.setStartValue(self.barra.value())
            self.anim.setEndValue(int(self.destino))
            self.anim.start()
            return True
        return False


def suavizar(area):
    area._rueda = _RuedaSuave(area)
    return area


class Esqueleto(QWidget):
    """Formas grises con un brillo que pasa: lo que se ve mientras algo carga."""

    def __init__(self, tipo="tarjetas", padre=None):
        super().__init__(padre)
        self.tipo = tipo
        self.fase = 0.0
        self.setMinimumHeight(260 if tipo == "tarjetas" else 330)
        self._t = QTimer(self)
        self._t.setInterval(33)
        self._t.timeout.connect(self._paso)
        self._t.start()

    def _paso(self):
        self.fase = (self.fase + 0.025) % 1.6
        self.update()

    def _formas(self):
        w = self.width()
        formas = []
        if self.tipo == "tarjetas":
            formas.append(QRectF(4, 0, 220, 24))
            x = 4
            while x + 160 < w:
                formas.append(QRectF(x + 12, 46, 152, 152))
                formas.append(QRectF(x + 12, 210, 120, 14))
                formas.append(QRectF(x + 12, 232, 90, 12))
                x += 180
        else:
            for i in range(6):
                y = i * 56
                formas.append(QRectF(12, y + 18, 20, 18))
                formas.append(QRectF(52, y + 8, 40, 40))
                formas.append(QRectF(104, y + 12, min(320, w * 0.4), 14))
                formas.append(QRectF(104, y + 34, min(200, w * 0.25), 11))
        return formas

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w = max(1, self.width())
        grad = QLinearGradient(0, 0, w, 0)
        centro = self.fase - 0.3
        base = QColor(255, 255, 255, 16)
        brillo = QColor(255, 255, 255, 34)
        grad.setColorAt(0, base)
        for pos, c in ((centro - 0.15, base), (centro, brillo), (centro + 0.15, base)):
            if 0 <= pos <= 1:
                grad.setColorAt(pos, c)
        grad.setColorAt(1, base)
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        for r in self._formas():
            p.drawRoundedRect(r, 6, 6)


def aparecer(widget, ms=170):
    """Fundido de entrada al mostrar una pagina."""
    from PySide6.QtWidgets import QGraphicsOpacityEffect
    efecto = QGraphicsOpacityEffect(widget)
    efecto.setOpacity(0.0)
    widget.setGraphicsEffect(efecto)
    anim = QPropertyAnimation(efecto, b"opacity", widget)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.OutCubic)

    def fin():
        try:
            widget.setGraphicsEffect(None)   # sin efecto, pintar sale gratis
        except RuntimeError:
            pass
    anim.finished.connect(fin)
    anim.start(QPropertyAnimation.DeleteWhenStopped)


class Pagina(QScrollArea):
    """Pagina con desplazamiento vertical, margenes y degradado opcional."""

    titulo_cambio = Signal(str)

    def __init__(self, ctx, padre=None, margen=(24, 18, 24, 32)):
        super().__init__(padre)
        self.ctx = ctx
        self.setObjectName("lienzo")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lienzo = Lienzo()
        self.cuerpo = QVBoxLayout(self.lienzo)
        self.cuerpo.setContentsMargins(*margen)
        self.cuerpo.setSpacing(28)
        self.setWidget(self.lienzo)
        self.titulo = ""
        self.color = None
        suavizar(self)

    def set_color(self, color):
        self.color = color
        self.lienzo.set_color(color)

    def cargando(self, texto="", tipo="tarjetas"):
        caja = QWidget()
        h = QVBoxLayout(caja)
        h.setContentsMargins(0, 30, 0, 0)
        h.setSpacing(30)
        h.addWidget(Esqueleto("filas" if tipo == "filas" else "tarjetas"))
        h.addWidget(Esqueleto("tarjetas"))
        self.cuerpo.addWidget(caja)
        self.cuerpo.addStretch(1)
        return caja

    def vaciar(self):
        while self.cuerpo.count():
            it = self.cuerpo.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
            elif it.layout() is not None:
                _borrar_layout(it.layout())

    def error(self, texto, reintentar=None):
        self.vaciar()
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 80, 0, 0)
        v.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(iconos.pixmap("aviso", 44, C["texto3"]))
        ic.setAlignment(Qt.AlignCenter)
        v.addWidget(ic)
        t = QLabel(texto)
        t.setAlignment(Qt.AlignCenter)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:15px;font-weight:600;")
        v.addWidget(t)
        if reintentar:
            b = QPushButton("Reintentar")
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(reintentar)
            v.addWidget(b, 0, Qt.AlignCenter)
        self.cuerpo.addWidget(caja)
        self.cuerpo.addStretch(1)


def _borrar_layout(layout):
    while layout.count():
        it = layout.takeAt(0)
        if it.widget():
            it.widget().deleteLater()
        elif it.layout():
            _borrar_layout(it.layout())


class EtiquetaTitulo(QLabel):
    """Titulo enorme que se achica para caber (como en Spotify)."""

    def __init__(self, texto="", maximo=72, minimo=28, padre=None, color="#FFFFFF"):
        super().__init__(texto, padre)
        self.maximo = maximo
        self.minimo = minimo
        self._color = color
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._ajustar()

    def setText(self, t):
        super().setText(t)
        self._ajustar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ajustar()

    def _ajustar(self):
        ancho = max(100, self.width()) * 0.97
        tam = self.maximo
        while tam > self.minimo:
            f = fuente(tam, QFont.Black, True)
            if QFontMetrics(f).horizontalAdvance(self.text()) <= ancho:
                break
            tam -= 2
        f = fuente(tam, QFont.Black, True)
        if getattr(self, "_tam", None) == tam:
            return
        self._tam = tam
        self.setFont(f)
        self.setStyleSheet(f"font-family:'{_familia_titulo()}';font-size:{tam}px;font-weight:900;"
                           f"color:{self._color};")
        self.setMinimumHeight(int(tam * 1.25))
        if QFontMetrics(f).horizontalAdvance(self.text()) > ancho:
            self.setToolTip(self.text())


class Cabecera(QWidget):
    """Cabecera grande: portada, tipo, titulo y datos, sobre el degradado."""

    color_listo = Signal(object)

    def __init__(self, ctx, tipo, titulo, url="", forma="cuadrada", lado=220, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 36, 0, 8)
        h.setSpacing(24)
        self.portada = Portada(lado, lado, forma, 6 if forma != "redonda" else 0,
                               icono={"Lista": "lista", "Artista": "usuario"}.get(tipo, "musica"))
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        sombra = QGraphicsDropShadowEffect(self.portada)
        sombra.setBlurRadius(48)
        sombra.setOffset(0, 8)
        sombra.setColor(QColor(0, 0, 0, 150))
        self.portada.setGraphicsEffect(sombra)
        h.addWidget(self.portada, 0, Qt.AlignBottom)
        v = QVBoxLayout()
        v.setSpacing(4)
        v.addStretch(1)
        self.et_tipo = QLabel(tipo)
        self.et_tipo.setStyleSheet("font-size:13px;font-weight:600;")
        v.addWidget(self.et_tipo)
        self.et_titulo = EtiquetaTitulo(titulo)
        v.addWidget(self.et_titulo)
        self.et_desc = QLabel("")
        self.et_desc.setObjectName("secundario")
        self.et_desc.setWordWrap(True)
        self.et_desc.hide()
        v.addWidget(self.et_desc)
        self.linea = QHBoxLayout()
        self.linea.setSpacing(6)
        v.addLayout(self.linea)
        h.addLayout(v, 1)
        if url:
            self.set_portada(url)

    def set_portada(self, url):
        self.portada.set_url(url)
        imagenes.imagen(url, self._con_imagen)

    def _con_imagen(self, img):
        try:
            self.color_listo.emit(imagenes.color_dominante(img))
        except RuntimeError:
            pass

    def set_descripcion(self, texto):
        texto = (texto or "").strip()
        if len(texto) > 260:
            texto = texto[:257].rsplit(" ", 1)[0] + "…"
        self.et_desc.setText(texto)
        self.et_desc.setVisible(bool(texto))

    def add_dato(self, texto, negrita=False, al_pulsar=None):
        if self.linea.count():
            sep = QLabel("•")
            sep.setStyleSheet("font-size:13px;color:#C9CFDA;")
            self.linea.addWidget(sep)
        if al_pulsar:
            b = QPushButton(texto)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:transparent;border:none;padding:0;"
                            "font-size:13.5px;font-weight:800;color:#FFFFFF;text-align:left;}"
                            "QPushButton:hover{text-decoration:underline;}")
            b.clicked.connect(al_pulsar)
            self.linea.addWidget(b)
        else:
            et = QLabel(texto)
            et.setStyleSheet(f"font-size:13.5px;{'font-weight:800;' if negrita else 'color:#D6DBE4;'}")
            self.linea.addWidget(et)

    def terminar(self):
        self.linea.addStretch(1)


class BarraAcciones(QWidget):
    """Fila bajo la cabecera: play grande, aleatorio, guardar, descargar, mas."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.h = QHBoxLayout(self)
        self.h.setContentsMargins(0, 4, 0, 4)
        self.h.setSpacing(14)
        self.bt_play = BotonPlay(56)
        self.h.addWidget(self.bt_play)
        self.h.addSpacing(4)

    def boton(self, icono, ayuda, al_pulsar, tam=26, lado=40, conmutable=False):
        b = BotonIcono(icono, tam, ayuda, lado, conmutable=conmutable)
        b.clicked.connect(al_pulsar)
        self.h.addWidget(b)
        return b

    def widget(self, w):
        self.h.addWidget(w)
        return w

    def terminar(self):
        self.h.addStretch(1)


class Aviso(QFrame):
    """Mensaje flotante abajo al centro: aparece y se va con un fundido, y puede
    llevar una accion (por ejemplo «Deshacer»)."""

    def __init__(self, padre):
        super().__init__(padre)
        self.setObjectName("aviso")
        self.setStyleSheet(f"QFrame#aviso{{background:{C['texto']};border-radius:10px;}}"
                           "QLabel{color:#0A0B0E;font-size:13.5px;font-weight:600;background:transparent;}"
                           "QPushButton{background:transparent;border:none;color:#0B6E82;"
                           "font-size:13.5px;font-weight:800;padding:0 4px;}"
                           "QPushButton:hover{text-decoration:underline;}")
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 10, 14, 10)
        h.setSpacing(16)
        self.et = QLabel("")
        h.addWidget(self.et)
        self.bt = QPushButton("")
        self.bt.setCursor(Qt.PointingHandCursor)
        self.bt.clicked.connect(self._accion)
        h.addWidget(self.bt)
        self.hide()
        self._funcion = None
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        self._opacidad = QGraphicsOpacityEffect(self)
        self._opacidad.setOpacity(1.0)
        self.setGraphicsEffect(self._opacidad)
        self._anim = QPropertyAnimation(self._opacidad, b"opacity", self)
        self._anim.setDuration(180)
        self._anim.finished.connect(self._fin_anim)
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.timeout.connect(self._ocultar)

    def mostrar(self, texto, ms=3200, accion=None, al_pulsar=None):
        if not texto:
            return
        self.et.setText(texto)
        self._funcion = al_pulsar
        self.bt.setText(accion or "")
        self.bt.setVisible(bool(accion))
        self.adjustSize()
        self.colocar()
        self.raise_()
        if not self.isVisible() or self._anim.endValue() == 0.0:
            self._anim.stop()
            self._anim.setStartValue(self._opacidad.opacity() if self.isVisible() else 0.0)
            self._anim.setEndValue(1.0)
            self.show()
            self._anim.start()
        self._t.start(ms if not accion else max(ms, 6000))

    def colocar(self):
        padre = self.parentWidget()
        self.move((padre.width() - self.width()) // 2, padre.height() - self.height() - 112)

    def _accion(self):
        funcion, self._funcion = self._funcion, None
        self._ocultar()
        if funcion:
            funcion()

    def _ocultar(self):
        self._anim.stop()
        self._anim.setStartValue(self._opacidad.opacity())
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _fin_anim(self):
        if self._anim.endValue() == 0.0:
            self.hide()


class SinResultados(QWidget):
    def __init__(self, icono, titulo, texto, padre=None):
        super().__init__(padre)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 50, 0, 50)
        v.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(iconos.pixmap(icono, 48, C["texto3"]))
        ic.setAlignment(Qt.AlignCenter)
        v.addWidget(ic)
        t = QLabel(titulo)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size:20px;font-weight:800;")
        v.addWidget(t)
        s = QLabel(texto)
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setObjectName("secundario")
        v.addWidget(s)


def size(w, h):
    return QSize(w, h)
