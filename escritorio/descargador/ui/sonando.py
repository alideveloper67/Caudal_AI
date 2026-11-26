# -*- coding: utf-8 -*-
"""Lo que suena, en grande: la carátula fundida con su color, los controles y lo que sigue.

- `PortadaInmersiva`: la carátula a todo el ancho; abajo se funde con su color y lleva encima el
  título, el artista, el corazón y el menú.
- `Continuacion`: «lo que sigue», con fichas para elegir qué música entra sola y las canciones en
  filas que se arrastran para cambiarlas de orden.
- `PaginaSonando`: la pantalla completa del reproductor (se abre pulsando la carátula de abajo).
"""

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPixmap)
from PySide6.QtWidgets import (QBoxLayout, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import catalogo, mix_continuo
from . import iconos, imagenes
from .componentes import (BotonIcono, BotonPlay, Chip, Deslizador, FilaDesplazable, _partir,
                          formato_tiempo, fuente, suavizar)
from .estilos import C

ALTO_FILA = 60
ALTO_TITULO = 44


def _artistas(p):
    return ", ".join(a.get("nombre", "") for a in p.get("artistas") or [] if a.get("nombre")) \
        or p.get("artista") or ""


def color_de_fondo(color):
    """El color de la carátula, oscuro: encima siempre va texto blanco."""
    c = QColor(color)
    h, s, v, _a = c.getHsv()
    c.setHsv(max(0, h), min(200, s), min(86, max(34, int(v * 0.55))))
    return c


# ====================================================================== la carátula

class PortadaInmersiva(QWidget):
    color_cambio = Signal(QColor)
    ir_artista = Signal()
    pulsada = Signal()

    def __init__(self, ctx, tam_titulo=22, lado_imagen=544, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.tam_titulo = tam_titulo
        self.lado_imagen = lado_imagen
        self.url = ""
        self.titulo = ""
        self.artista = ""
        self.color = QColor("#1B2230")
        self._img = None
        self._pm = None
        self._pm_tam = None
        self._r_artista = QRect()
        self.con_botones_arriba = False
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.bt_gusta = BotonIcono("corazon", 22, "Guardar en Tus me gusta", 38, padre=self, color="#FFFFFF",
                                   color_hover="#FFFFFF")
        self.bt_gusta.clicked.connect(self._gusta)
        self.bt_mas = BotonIcono("puntos", 22, "Más opciones", 38, padre=self, color="#FFFFFF",
                                 color_hover="#FFFFFF")
        self.bt_mas.clicked.connect(self._menu)

    def poner(self, p):
        p = p or {}
        self.titulo = p.get("titulo") or "Nada sonando"
        self.artista = _artistas(p) if p else "Elige algo para escuchar"
        for b in (self.bt_gusta, self.bt_mas):
            b.setVisible(bool(p))
        self.pintar_gusta()
        self.setAccessibleName(f"{self.titulo}, {self.artista}")
        url = p.get("miniatura") or ""
        if url != self.url:
            self.url = url
            self._img = self._pm = None
            if url:
                # primero la que ya está (al instante) y encima la grande, si la hay
                imagenes.imagen(url, lambda img, u=url: self._llego(u, img, False))
                grande = catalogo.agrandar_miniatura(url, self.lado_imagen)
                if grande and grande != url:
                    imagenes.imagen(grande, lambda img, u=url: self._llego(u, img, True))
            else:
                self._poner_color(QColor("#1B2230"))
        self.update()

    def _llego(self, url, img, grande):
        try:
            if url != self.url or img is None or img.isNull():
                return
            if self._img is not None and not grande and self._img.width() >= img.width():
                return
            self._img, self._pm = img, None
            self._poner_color(imagenes.color_dominante(img))
            self.update()
        except RuntimeError:
            pass

    def _poner_color(self, c):
        c = color_de_fondo(c)
        if c != self.color:
            self.color = c
            self.color_cambio.emit(c)
            self.update()

    def pintar_gusta(self, *_a):
        p = self.ctx.reproductor.actual
        gusta = bool(p and self.ctx.coleccion.me_gusta(p.get("clave")))
        self.bt_gusta.set_icono("corazon_lleno" if gusta else "corazon")
        self.bt_gusta.set_activo(gusta, punto=False)
        self.bt_gusta.setToolTip("Quitar de Tus me gusta" if gusta else "Guardar en Tus me gusta")

    def _gusta(self):
        if self.ctx.reproductor.actual:
            self.ctx.alternar_me_gusta(self.ctx.reproductor.actual)

    def _menu(self):
        p = self.ctx.reproductor.actual
        if p:
            self.ctx.menu_pista(p, self.bt_mas.mapToGlobal(self.bt_mas.rect().bottomLeft()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._pm = None
        y = self.height() - 48
        self.bt_mas.move(self.width() - 46, y)
        self.bt_gusta.move(self.width() - 86, y)

    def mouseMoveEvent(self, e):
        sobre = self._r_artista.contains(e.position().toPoint())
        self.setCursor(Qt.PointingHandCursor if sobre else Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._r_artista.contains(e.position().toPoint()):
                self.ir_artista.emit()
            elif self.rect().contains(e.position().toPoint()):
                self.pulsada.emit()

    def _imagen_cubriendo(self):
        tam = (self.width(), self.height(), self.devicePixelRatioF())
        if self._pm is None or self._pm_tam != tam:
            dpr = tam[2]
            w, h = int(tam[0] * dpr), int(tam[1] * dpr)
            escalada = self._img.scaled(QSize(w, h), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            # la parte de arriba manda: las caras no se cortan
            x = (escalada.width() - w) // 2
            y = int((escalada.height() - h) * 0.3)
            pm = QPixmap.fromImage(escalada.copy(x, y, w, h))
            pm.setDevicePixelRatio(dpr)
            self._pm, self._pm_tam = pm, tam
        return self._pm

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, w, h + 12), 12, 12)     # redonda solo por arriba
        p.setClipPath(ruta)
        p.fillRect(self.rect(), self.color)
        if self._img is not None and w > 0 and h > 0:
            p.drawPixmap(0, 0, self._imagen_cubriendo())
        else:
            lado = int(min(w, h) * 0.26)
            p.drawPixmap((w - lado) // 2, int(h * 0.32), iconos.pixmap("musica", lado, "#FFFFFF"))
        # se funde con su color
        velo = QLinearGradient(0, h * 0.28, 0, h)
        for pos, a in ((0.0, 0), (0.45, 120), (0.75, 225), (1.0, 255)):
            c = QColor(self.color)
            c.setAlpha(a)
            velo.setColorAt(pos, c)
        p.fillRect(self.rect(), velo)
        if self.con_botones_arriba:            # para que la flecha se vea también sobre una carátula blanca
            arriba = QLinearGradient(0, 0, 0, 90)
            arriba.setColorAt(0, QColor(0, 0, 0, 100))
            arriba.setColorAt(1, QColor(0, 0, 0, 0))
            p.fillRect(QRect(0, 0, w, 90), arriba)

        margen = 18
        botones = 92 if self.bt_mas.isVisible() else 0
        f = fuente(self.tam_titulo, QFont.Black, True)
        fm = QFontMetrics(f)
        ancho_t = max(40, w - 2 * margen)
        lineas = _partir(self.titulo, fm, ancho_t, 2)
        fa = fuente(max(13, self.tam_titulo * 0.62), QFont.DemiBold)
        fma = QFontMetrics(fa)
        y = h - 14 - fma.height()
        ancho_a = max(30, w - 2 * margen - botones)
        texto = fma.elidedText(self.artista, Qt.ElideRight, ancho_a)
        self._r_artista = QRect(margen, y, fma.horizontalAdvance(texto), fma.height()) if self.artista else QRect()
        p.setFont(fa)
        p.setPen(QColor(255, 255, 255, 215))
        p.drawText(QRect(margen, y, ancho_a, fma.height()), Qt.AlignLeft | Qt.AlignVCenter, texto)
        y -= 6
        p.setFont(f)
        for linea in reversed(lineas):
            y -= fm.height()
            r = QRect(margen, y, ancho_t, fm.height())
            p.setPen(QColor(0, 0, 0, 110))
            p.drawText(r.translated(0, 1), Qt.AlignLeft | Qt.AlignVCenter, linea)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(r, Qt.AlignLeft | Qt.AlignVCenter, linea)


# ====================================================================== la cola

class ColaReordenable(QWidget):
    """Lo que sigue, pintado en una sola pieza: se arrastra por el asa para cambiar el orden."""

    def __init__(self, ctx, limite=0, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.limite = limite
        self.filas = []            # ("titulo", texto, accion) | ("pista", grupo, indice, absoluto, pista)
        self._y = []
        self._encima = -1
        self._zona = ""
        self._arrastre = None      # {"fila", "destino", "y", "dy"}
        self._pedidas = set()
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._t_scroll = QTimer(self)
        self._t_scroll.setInterval(16)
        self._t_scroll.timeout.connect(self._autodesplazar)
        self.rehacer()

    # ------------------------------------------------------------ datos

    def rehacer(self):
        r = self.r
        filas = []
        if r.proximas:
            filas.append(("titulo", "Siguiente en tu cola", ("Vaciar", r.vaciar_proximas)))
            filas += [("pista", "cola", i, i, p) for i, p in enumerate(r.proximas[:100])]
        siguientes = r.siguientes_de_contexto(80)
        normales = [(r.pos + 1 + i, p) for i, p in enumerate(siguientes) if not p.get("_auto")]
        autos = [(r.pos + 1 + i, p) for i, p in enumerate(siguientes) if p.get("_auto")]
        if normales:
            nombre = (r.contexto or {}).get("titulo") or "la cola"
            if filas:                  # si es lo primero, el título ya está arriba
                filas.append(("titulo", f"Siguiente de: {nombre}", None))
            filas += [("pista", "contexto", i, a, p) for i, (a, p) in enumerate(normales)]
        if autos:
            if filas:
                filas.append(("titulo", "Y después, canciones parecidas", None))
            filas += [("pista", "auto", i, a, p) for i, (a, p) in enumerate(autos)]
        if self.limite:
            cortadas, n = [], 0
            for f in filas:
                if f[0] == "pista":
                    n += 1
                    if n > self.limite:
                        break
                cortadas.append(f)
            while cortadas and cortadas[-1][0] == "titulo":
                cortadas.pop()
            filas = cortadas
        self.filas = filas
        self._y, y = [], 0
        for f in filas:
            self._y.append(y)
            y += ALTO_TITULO if f[0] == "titulo" else ALTO_FILA
        self._arrastre = None
        self._t_scroll.stop()
        self._encima = -1
        self.setFixedHeight(max(1, y))
        self.update()

    def _alto(self, i):
        return ALTO_TITULO if self.filas[i][0] == "titulo" else ALTO_FILA

    def _fila_en(self, y):
        for i in range(len(self.filas)):
            if self._y[i] <= y < self._y[i] + self._alto(i):
                return i
        return -1

    def _grupo(self, i):
        """(primera, última) fila del mismo grupo que la `i`."""
        grupo = self.filas[i][1]
        idx = [k for k, f in enumerate(self.filas) if f[0] == "pista" and f[1] == grupo]
        return idx[0], idx[-1]

    # ------------------------------------------------------------ zonas

    def _r_portada(self, i):
        return QRect(10, self._y[i] + 8, 44, 44)

    def _r_asa(self, i):
        return QRect(self.width() - 42, self._y[i], 42, ALTO_FILA)

    def _r_puntos(self, i):
        return QRect(self.width() - 78, self._y[i] + 14, 32, 32)

    def _r_accion(self, i):
        texto = self.filas[i][2][0]
        ancho = QFontMetrics(fuente(13, QFont.Bold)).horizontalAdvance(texto) + 16
        return QRect(self.width() - ancho - 4, self._y[i] + 8, ancho, ALTO_TITULO - 12)

    def _zona_en(self, pos, i):
        if i < 0:
            return ""
        if self.filas[i][0] == "titulo":
            return "accion" if self.filas[i][2] and self._r_accion(i).contains(pos) else ""
        if self._r_asa(i).contains(pos):
            return "asa"
        if self._r_puntos(i).contains(pos):
            return "puntos"
        return "portada" if self._r_portada(i).contains(pos) else "fila"

    # ------------------------------------------------------------ ratón

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._arrastre is not None:
            self._arrastre["y"] = pos.y()
            self._recolocar()
            return
        i = self._fila_en(pos.y())
        zona = self._zona_en(pos, i)
        # sobre el asa, arrastrar mueve la canción; en el resto de la fila desplaza la lista
        self.setProperty("sin_arrastre", zona == "asa")
        if (i, zona) != (self._encima, self._zona):
            self._encima, self._zona = i, zona
            self.setCursor({"asa": Qt.OpenHandCursor, "puntos": Qt.PointingHandCursor,
                            "accion": Qt.PointingHandCursor,
                            "portada": Qt.PointingHandCursor}.get(zona, Qt.ArrowCursor))
            self.update()

    def leaveEvent(self, _e):
        if self._arrastre is None:
            self._encima, self._zona = -1, ""
            self.update()

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        i = self._fila_en(pos.y())
        zona = self._zona_en(pos, i)
        self._pulso = None
        if i < 0:
            return
        if self.filas[i][0] == "titulo":
            if zona == "accion" and e.button() == Qt.LeftButton:
                self.filas[i][2][1]()
            return
        if e.button() == Qt.RightButton:
            self._menu(i, e.globalPosition().toPoint())
        elif e.button() == Qt.LeftButton:
            if zona == "asa":
                self._arrastre = {"fila": i, "destino": i, "y": pos.y(), "dy": pos.y() - self._y[i],
                                  "desde": pos.y()}
                self.setCursor(Qt.ClosedHandCursor)
                self._t_scroll.start()
                self.update()
            elif zona == "puntos":
                self._menu(i, self.mapToGlobal(self._r_puntos(i).bottomLeft()))
            elif zona == "portada":
                self._pulso = i

    def mouseReleaseEvent(self, e):
        a = self._arrastre
        if a is not None:
            self._arrastre = None
            self._t_scroll.stop()
            self.setCursor(Qt.ArrowCursor)
            self.update()
            if a["destino"] == a["fila"] and abs(e.position().y() - a["desde"]) < 6:
                # un clic en las rayas (sin arrastrar): las opciones para moverla, sin tener que usar el botón derecho
                self._menu_mover(a["fila"], self.mapToGlobal(self._r_asa(a["fila"]).bottomLeft()))
                return
            self.mover(a["fila"], a["destino"])
            return
        i, self._pulso = getattr(self, "_pulso", None), None
        if i is not None and i < len(self.filas) and self._r_portada(i).contains(e.position().toPoint()):
            self._reproducir(i)

    def mouseDoubleClickEvent(self, e):
        pos = e.position().toPoint()
        i = self._fila_en(pos.y())
        if e.button() == Qt.LeftButton and self._zona_en(pos, i) == "fila":
            self._reproducir(i)

    def _reproducir(self, i):
        _t, grupo, _n, absoluto, _p = self.filas[i]
        if grupo == "cola":
            self.r.saltar_a_proxima(absoluto)
        else:
            self.r.saltar_a(absoluto)

    def mover(self, fila, destino):
        """Pone la fila `fila` en el sitio de la fila `destino` (del mismo grupo)."""
        if fila == destino or not (0 <= fila < len(self.filas) and 0 <= destino < len(self.filas)):
            return
        _t, grupo, _n, de, _p = self.filas[fila]
        if self.filas[destino][0] != "pista" or self.filas[destino][1] != grupo:
            return
        a = self.filas[destino][3]
        if grupo == "cola":
            self.r.mover_proxima(de, a)
        else:
            self.r.mover_en_secuencia(de, a)

    def _quitar(self, i):
        _t, grupo, _n, absoluto, p = self.filas[i]
        r = self.r
        if grupo == "cola":
            r.quitar_proxima(absoluto)

            def deshacer():
                r.proximas.insert(min(absoluto, len(r.proximas)), p)
                r.cola_cambio.emit()
        else:
            r.quitar_de_secuencia(absoluto)

            def deshacer():
                r.secuencia.insert(max(r.pos + 1, min(absoluto, len(r.secuencia))), p)
                r.cola_cambio.emit()
        self.ctx.avisar("Quitada de la cola", deshacer)

    def _acciones_mover(self, m, i):
        primera, ultima = self._grupo(i)
        if i > primera:
            m.addAction(iconos.icono("chevron_arriba", 16, C["texto2"]), "Subir", lambda: self.mover(i, i - 1))
            if i - 1 > primera:
                m.addAction("Ponerla la primera", lambda: self.mover(i, primera))
        if i < ultima:
            m.addAction(iconos.icono("chevron_abajo", 16, C["texto2"]), "Bajar", lambda: self.mover(i, i + 1))
            if i + 1 < ultima:
                m.addAction("Ponerla la última", lambda: self.mover(i, ultima))
        m.addAction("Quitar de la cola", lambda: self._quitar(i))

    def _menu(self, i, donde):
        p = self.filas[i][4]
        self.ctx.menu_pista(p, donde, extra=lambda m: self._acciones_mover(m, i))

    def _menu_mover(self, i, donde):
        """Al tocar las rayas: mover la canción (arrastrarlas sigue sirviendo) y, debajo, lo de siempre."""
        m = QMenu(self)
        self._acciones_mover(m, i)
        m.addSeparator()
        m.addAction("Más opciones…", lambda: self._menu(i, donde))
        m.exec(donde)

    # ------------------------------------------------------------ arrastre

    def _recolocar(self):
        a = self._arrastre
        primera, ultima = self._grupo(a["fila"])
        centro = a["y"] - a["dy"] + ALTO_FILA / 2
        destino = primera + int((centro - self._y[primera]) // ALTO_FILA)
        a["destino"] = max(primera, min(ultima, destino))
        self.update()

    def _area(self):
        w = self.parentWidget()
        while w is not None and not (isinstance(w, QScrollArea) and w.verticalScrollBar().maximum() > 0):
            w = w.parentWidget()
        return w

    def _autodesplazar(self):
        """Al llevar una canción al borde, la lista avanza sola."""
        area = self._area()
        if self._arrastre is None or area is None:
            return
        y = self.mapTo(area.viewport(), QPoint(0, int(self._arrastre["y"]))).y()
        alto = area.viewport().height()
        paso = -10 if y < 36 else (10 if y > alto - 36 else 0)
        if paso:
            barra = area.verticalScrollBar()
            antes = barra.value()
            barra.setValue(antes + paso)
            self._arrastre["y"] += barra.value() - antes
            self._recolocar()

    # ------------------------------------------------------------ pintado

    def _portada(self, url):
        if not url:
            return None
        yo = self

        def listo(_pm):
            try:
                yo.update()
            except RuntimeError:
                pass
        if url in self._pedidas:
            return imagenes.pedir(url, 44, 44, "cuadrada", 6, None)
        pm = imagenes.pedir(url, 44, 44, "cuadrada", 6, listo)
        self._pedidas.add(url)
        return pm

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        a = self._arrastre
        zona = e.rect()
        for i in range(len(self.filas)):
            y = self._y[i]
            if a is not None and self.filas[i][0] == "pista":
                if i == a["fila"]:
                    continue
                # las demás hacen sitio
                if a["fila"] < i <= a["destino"]:
                    y -= ALTO_FILA
                elif a["destino"] <= i < a["fila"]:
                    y += ALTO_FILA
            if y + self._alto(i) < zona.top() or y > zona.bottom():
                continue
            if self.filas[i][0] == "titulo":
                self._pintar_titulo(p, i, y)
            else:
                self._pintar_fila(p, i, y, False)
        if a is not None:
            primera, ultima = self._grupo(a["fila"])
            y = max(self._y[primera] - 8, min(self._y[ultima] + 8, a["y"] - a["dy"]))
            self._pintar_fila(p, a["fila"], int(y), True)

    def _pintar_titulo(self, p, i, y):
        _t, texto, accion = self.filas[i]
        derecha = 8
        if accion:
            r = self._r_accion(i)
            derecha += r.width()
            f = fuente(13, QFont.Bold)
            f.setUnderline(self._encima == i and self._zona == "accion")
            p.setFont(f)
            p.setPen(QColor(C["texto"] if self._encima == i and self._zona == "accion" else C["texto2"]))
            p.drawText(r, Qt.AlignRight | Qt.AlignVCenter, accion[0])
        f = fuente(14, QFont.Bold)
        p.setFont(f)
        p.setPen(QColor(C["texto"]))
        ancho = self.width() - 10 - derecha
        p.drawText(QRect(10, y + 10, ancho, ALTO_TITULO - 14), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(texto, Qt.ElideRight, ancho))

    def _pintar_fila(self, p, i, y, flotando):
        pista = self.filas[i][4]
        w = self.width()
        encima = flotando or (self._encima == i and self._arrastre is None)
        if flotando:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["superficie3"]))
            p.drawRoundedRect(QRectF(0, y, w, ALTO_FILA), 8, 8)
        elif encima:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(0, y, w, ALTO_FILA), 8, 8)
        r = QRect(10, y + 8, 44, 44)
        pm = self._portada(pista.get("miniatura") or "")
        if pm is not None:
            p.drawPixmap(r.topLeft(), pm)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["superficie3"]))
            p.drawRoundedRect(QRectF(r), 6, 6)
            p.drawPixmap(r.x() + 13, r.y() + 13, iconos.pixmap("musica", 18, C["texto3"]))
        if encima and not flotando:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 120))
            p.drawRoundedRect(QRectF(r), 6, 6)
            p.drawPixmap(r.center().x() - 8, r.center().y() - 8, iconos.pixmap("reproducir", 17, "#FFFFFF"))
        derecha = w - 42
        # el asa de arrastrar: dos rayas
        c = QColor(C["texto"] if (encima and self._zona == "asa") or flotando else C["texto3"])
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        for dy in (-4, 3):
            p.drawRoundedRect(QRectF(w - 32, y + ALTO_FILA / 2 + dy, 18, 2), 1, 1)
        if encima and not flotando:
            p.drawPixmap(derecha - 30, y + 20, iconos.pixmap(
                "puntos", 20, C["texto"] if self._zona == "puntos" else C["texto2"]))
            derecha -= 36
        x = 66
        ancho = max(20, derecha - x - 6)
        f = fuente(14, QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRect(x, y + 10, ancho, 21), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(pista.get("titulo") or "", Qt.ElideRight, ancho))
        xs = x
        if pista.get("explicito"):
            e = QRectF(xs, y + 33.5, 14, 14)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(C["texto2"]))
            p.drawRoundedRect(e, 2, 2)
            p.setPen(QColor(C["panel"]))
            p.setFont(fuente(9.5, QFont.Bold))
            p.drawText(e, Qt.AlignCenter, "E")
            xs += 19
        dur = formato_tiempo(pista.get("duracion"))
        sub = " · ".join(t for t in (_artistas(pista), dur) if t)
        f = fuente(12.5)
        p.setFont(f)
        p.setPen(QColor(C["texto2"]))
        ancho -= xs - x
        p.drawText(QRect(xs, y + 31, ancho, 19), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(sub, Qt.ElideRight, ancho))


class Continuacion(QWidget):
    """«Mix de …»: título, fichas y la cola."""

    ver_todo = Signal()
    cambio = Signal()

    def __init__(self, ctx, limite=0, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.limite = limite
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        cab = QHBoxLayout()
        cab.setContentsMargins(10, 0, 4, 0)
        self.et_titulo = QLabel("")
        self.et_titulo.setMinimumWidth(10)
        self.et_titulo.setStyleSheet("font-size:16px;font-weight:800;background:transparent;")
        cab.addWidget(self.et_titulo, 1)
        self.bt_todo = QPushButton("Ver todo")
        self.bt_todo.setObjectName("enlace")
        self.bt_todo.setCursor(Qt.PointingHandCursor)
        self.bt_todo.clicked.connect(self.ver_todo.emit)
        self.bt_todo.hide()
        cab.addWidget(self.bt_todo)
        v.addLayout(cab)
        self.fichas = FilaDesplazable(6)
        self.fichas.h.setContentsMargins(10, 0, 0, 0)
        self.chips = {}
        for clave, texto in mix_continuo.TIPOS:
            c = Chip(texto)
            c.clicked.connect(lambda _=False, k=clave: self._elegir(k))
            self.fichas.agregar(c)
            self.chips[clave] = c
        self.chips["populares"].setToolTip("Lo más escuchado de este artista y de otros parecidos")
        self.chips["descubrir"].setToolTip("Canciones parecidas que aún no has escuchado")
        v.addWidget(self.fichas)
        self.cola = ColaReordenable(ctx, limite)
        v.addWidget(self.cola)
        self.et_vacia = QLabel("")
        self.et_vacia.setObjectName("secundario")
        self.et_vacia.setWordWrap(True)
        self.et_vacia.setContentsMargins(10, 8, 10, 8)
        v.addWidget(self.et_vacia)
        self._t = QTimer(self)              # varias señales seguidas -> un solo repintado
        self._t.setSingleShot(True)
        self._t.setInterval(60)
        self._t.timeout.connect(self.pintar)
        self.r.cola_cambio.connect(self._programar)
        self.r.pista_cambio.connect(self._programar)
        mix = getattr(self.r, "mix_cambio", None)
        if mix is not None:
            mix.connect(self._programar)
        self.pintar()

    def _programar(self, *_a):
        self._t.start()

    def _elegir(self, clave):
        elegir = getattr(self.r, "elegir_mix", None)
        if elegir is not None:
            elegir(clave)
        self._pintar_fichas()

    def _pintar_fichas(self):
        actual = getattr(self.r, "tipo_mix", "todo")
        cargando = getattr(self.r, "mix_cargando", False) is True
        for k, c in self.chips.items():
            c.setChecked(k == actual)
            nombre = dict(mix_continuo.TIPOS)[k]
            c.setText(f"{nombre}…" if cargando and k == actual else nombre)
        p = self.r.actual
        puede = bool(p and p.get("video_id") and getattr(self.r, "elegir_mix", None) is not None
                     and self.ctx.ajustes["autoplay"])
        self.fichas.setVisible(puede)

    def showEvent(self, e):
        super().showEvent(e)
        self._programar()

    def pintar(self):
        r = self.r
        self._pintar_fichas()
        if self.cola._arrastre is None:
            self.cola.rehacer()
        hay = any(f[0] == "pista" for f in self.cola.filas)
        ctx = r.contexto or {}
        if not r.actual:
            titulo = "Tu cola"
        elif r.proximas or not hay:
            titulo = "A continuación"
        elif self.cola.filas[0][0] == "pista" and self.cola.filas[0][1] == "contexto":
            titulo = ctx.get("titulo") or "A continuación"
        else:
            titulo = f"Mix de {r.actual.get('titulo') or 'esta canción'}"
        self._titulo = titulo
        self._elidir()
        faltan = len(r.proximas) + max(0, len(r.secuencia) - r.pos - 1)
        self.bt_todo.setVisible(bool(self.limite) and faltan > self.limite)
        if not r.actual:
            texto = "Tu cola está vacía. Elige algo para escuchar."
        elif not hay:
            texto = "No hay nada más en la cola." + (" Al terminar seguirán canciones parecidas."
                                                     if self.ctx.ajustes["autoplay"] else "")
        else:
            texto = ""
        self.et_vacia.setText(texto)
        self.et_vacia.setVisible(bool(texto))
        self.cambio.emit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._elidir()

    def _elidir(self):
        t = getattr(self, "_titulo", "")
        self.et_titulo.setText(QFontMetrics(fuente(16, QFont.ExtraBold)).elidedText(
            t, Qt.ElideRight, max(40, self.width() - 100)))
        self.et_titulo.setToolTip(t)


# ====================================================================== la pantalla

class PaginaSonando(QScrollArea):
    """El reproductor en grande."""

    volver = Signal()
    ANCHO_DOS = 800          # desde aquí, la cola va al lado

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.titulo = "Sonando"
        self._dur = 0.0
        self._arrastrando = False
        self.setObjectName("lienzo")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.lienzo = _Fondo()
        self.caja = QBoxLayout(QBoxLayout.LeftToRight, self.lienzo)
        self.caja.setContentsMargins(20, 16, 20, 16)
        self.caja.setSpacing(24)

        izq = QWidget()
        self.izq = izq
        v = QVBoxLayout(izq)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.portada = PortadaInmersiva(ctx, 32, 1000)
        self.portada.color_cambio.connect(self._color)
        self.portada.ir_artista.connect(self._ir_artista)
        v.addWidget(self.portada, 1)
        self.bt_volver = BotonIcono("chevron_abajo", 22, "Volver  (Esc)", 40, padre=self.portada,
                                    color="#FFFFFF", color_hover="#FFFFFF")
        self.portada.con_botones_arriba = True
        self.bt_volver.move(12, 12)
        self.bt_volver.clicked.connect(self.volver.emit)

        mando = QWidget()
        mando.setMaximumWidth(760)
        mv = QVBoxLayout(mando)
        mv.setContentsMargins(18, 10, 18, 6)
        mv.setSpacing(4)
        self.barra = Deslizador(18)
        self.barra.color_relleno = QColor("#FFFFFF")
        self.barra.movido.connect(self._moviendo)
        self.barra.soltado.connect(self._soltar)
        mv.addWidget(self.barra)
        tiempos = QHBoxLayout()
        self.et_pos = QLabel("0:00")
        self.et_total = QLabel("0:00")
        for et in (self.et_pos, self.et_total):
            et.setStyleSheet("color:rgba(255,255,255,0.75);font-size:12.5px;background:transparent;")
        tiempos.addWidget(self.et_pos)
        tiempos.addStretch(1)
        tiempos.addWidget(self.et_total)
        mv.addLayout(tiempos)
        botones = QHBoxLayout()
        botones.setSpacing(0)
        blanco = {"color": "#E4E7EE", "color_hover": "#FFFFFF"}
        self.bt_aleatorio = BotonIcono("aleatorio", 24, "Aleatorio", 46, **blanco)
        self.bt_aleatorio.clicked.connect(self._aleatorio)
        self.bt_anterior = BotonIcono("anterior", 30, "Anterior", 54, **blanco)
        self.bt_anterior.clicked.connect(self.r.anterior)
        self.bt_play = BotonPlay(76, claro=True)
        self.bt_play.setToolTip("Reproducir / pausar  (Espacio)")
        self.bt_play.clicked.connect(self.r.alternar)
        self.bt_siguiente = BotonIcono("siguiente", 30, "Siguiente", 54, **blanco)
        self.bt_siguiente.clicked.connect(lambda _=False: self.r.siguiente())
        self.bt_repetir = BotonIcono("repetir", 24, "Repetir", 46, **blanco)
        self.bt_repetir.clicked.connect(self._repetir)
        for i, b in enumerate((self.bt_aleatorio, self.bt_anterior, self.bt_play, self.bt_siguiente,
                               self.bt_repetir)):
            if i:
                botones.addStretch(1)
            botones.addWidget(b, 0, Qt.AlignVCenter)
        mv.addLayout(botones)
        centro = QHBoxLayout()
        centro.addStretch(1)
        centro.addWidget(mando, 100)
        centro.addStretch(1)
        v.addLayout(centro)
        self.caja.addWidget(izq, 1)

        self.der = QScrollArea()
        self.der.setObjectName("lienzo")
        self.der.setWidgetResizable(True)
        self.der.setFrameShape(QFrame.NoFrame)
        self.der.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interior = QWidget()
        iv = QVBoxLayout(interior)
        iv.setContentsMargins(0, 6, 4, 10)
        self.continua = Continuacion(ctx)
        iv.addWidget(self.continua)
        iv.addStretch(1)
        self._t_ordenar = QTimer(self)
        self._t_ordenar.setSingleShot(True)
        self._t_ordenar.setInterval(30)
        self._t_ordenar.timeout.connect(self.ordenar)
        self.continua.cambio.connect(self._t_ordenar.start)
        self.der.setWidget(interior)
        suavizar(self.der)
        self.caja.addWidget(self.der)
        self.setWidget(self.lienzo)

        r = self.r
        r.pista_cambio.connect(self._pista)
        r.estado_cambio.connect(self._estado)
        r.posicion_cambio.connect(self._posicion)
        r.duracion_cambio.connect(self._duracion)
        ctx.me_gusta_cambio.connect(self.portada.pintar_gusta)
        self._pista(r.actual)
        self._estado(getattr(r, "estado", ""))
        self._pintar_modos()

    # ------------------------------------------------------------ forma

    def con_cola(self):
        """La cola va aquí dentro salvo que ya se vea en el panel de la derecha."""
        panel = getattr(getattr(self.ctx, "ventana", None), "panel_der", None)
        try:
            return not (panel is not None and panel.isVisible())
        except (RuntimeError, AttributeError):
            return True

    def ordenar(self):
        ancho, alto = self.viewport().width(), self.viewport().height()
        cola = self.con_cola()
        self.der.setVisible(cola)
        dos = cola and ancho >= self.ANCHO_DOS
        self.caja.setDirection(QBoxLayout.LeftToRight if dos or not cola else QBoxLayout.TopToBottom)
        if dos:
            self.der.setFixedWidth(max(320, min(460, int(ancho * 0.38))))
            self.der.setMinimumHeight(0)
            self.der.setMaximumHeight(16777215)
        else:
            self.der.setMinimumWidth(0)
            self.der.setMaximumWidth(16777215)
            # debajo, entera: se desplaza la página, no una lista dentro de otra
            self.der.setFixedHeight(max(160, self.der.widget().sizeHint().height() + 12))
        util = max(380, alto - 32)
        self.izq.setMinimumHeight(util if (dos or not cola) else max(380, int(alto * 0.86)))
        self.portada.tam_titulo = 34 if self.portada.width() > 520 else 25
        self.portada.update()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.ordenar()

    def showEvent(self, e):
        super().showEvent(e)
        self._pista(self.r.actual)
        if self.r.actual:                # la duración pudo llegar antes de que existiera esta página
            self._duracion(getattr(self.r, "_duracion", 0) or self.r.actual.get("duracion"))
        self._pintar_modos()
        QTimer.singleShot(0, self.ordenar)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.volver.emit()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------ lo que suena

    def _color(self, c):
        self.lienzo.poner(c)

    def _pista(self, p):
        self.portada.poner(p)
        if not p:
            self._duracion(0)
            self._posicion(0)

    def _estado(self, estado):
        self.bt_play.set_sonando(estado == "sonando")
        self.bt_play.set_cargando(estado == "cargando" and self.isVisible())

    def _posicion(self, seg):
        if self._arrastrando or not self.isVisible():
            return
        self.et_pos.setText(formato_tiempo(seg) or "0:00")
        if self._dur > 0:
            self.barra.set_valor(float(seg or 0) / self._dur)
        else:
            self.barra.set_valor(0)

    def _duracion(self, d):
        self._dur = float(d or 0)
        self.et_total.setText(formato_tiempo(self._dur) or "0:00")

    def _moviendo(self, v):
        self._arrastrando = True
        self.et_pos.setText(formato_tiempo(v * self._dur) or "0:00")

    def _soltar(self, v):
        self._arrastrando = False
        if self._dur > 0:
            self.r.buscar(v * self._dur)

    # ------------------------------------------------------------ modos

    def _barra_de_abajo(self):
        barra = getattr(getattr(self.ctx, "ventana", None), "barra", None)
        pintar = getattr(barra, "_pintar_modos", None)
        if pintar is not None:
            pintar()

    def _aleatorio(self):
        activo = self.r.alternar_aleatorio()
        self.ctx.aviso.emit("Aleatorio activado" if activo else "Aleatorio desactivado")
        self._pintar_modos()
        self._barra_de_abajo()

    def _repetir(self):
        modo = self.r.ciclar_repetir()
        self.ctx.aviso.emit({"no": "Repetir desactivado", "todo": "Repetir toda la cola",
                             "una": "Repetir esta canción"}[modo])
        self._pintar_modos()
        self._barra_de_abajo()

    def _pintar_modos(self):
        self.bt_aleatorio.set_activo(bool(self.r.aleatorio))
        self.bt_repetir.set_icono("repetir_una" if self.r.repetir == "una" else "repetir")
        self.bt_repetir.set_activo(self.r.repetir != "no")

    def _ir_artista(self):
        p = self.r.actual or {}
        ident = next((a["id"] for a in p.get("artistas") or [] if a.get("id")), "")
        if ident:
            self.ctx.navegar({"pagina": "artista", "id": ident})


class _Fondo(QWidget):
    """El color de la carátula, fundiéndose hacia abajo con el panel."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.color = QColor("#1B2230")

    def poner(self, c):
        self.color = QColor(c)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, max(1, self.height()))
        g.setColorAt(0, self.color)
        g.setColorAt(0.8, self.color)
        oscuro = QColor(self.color)
        g.setColorAt(1, oscuro.darker(170))
        p.fillRect(self.rect(), g)
