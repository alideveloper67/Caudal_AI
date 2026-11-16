# -*- coding: utf-8 -*-
"""Buscar un GIF en internet para la foto o el fondo del perfil (solo Donador o Fundador de Caudal).

`DialogoBuscarGif(ctx, modo, padre, cliente=None)`: buscador con rejilla de vistas animadas, carga
perezosa al hacer scroll, pocas animaciones a la vez y una vista previa (redonda para la foto, 8:3 para
el fondo) antes de usarlo. Al aceptar, `.datos` trae los bytes del GIF elegido.
"""

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QStackedWidget, QVBoxLayout, QWidget)

from ... import gif_perfil as G
from ...hilos import en_segundo_plano
from .. import iconos
from ..estilos import C, hoja
from ..gif_animado import GifVivo
from . import perfil_comun as PC

COLUMNAS = 3
MAX_ANIMADAS = 6           # vistas que se animan a la vez (el resto muestra su primer cuadro)
MAX_BAJANDO = 4            # descargas de vistas en paralelo
RETRASO_BUSQUEDA_MS = 350


# ------------------------------------------------------------------ insignia y botón «GIF · Donador»
def _chip(padre=None):
    """La insignia pequeña «GIF · Donador» (una etiqueta: así el texto siempre cabe)."""
    from PySide6.QtGui import QFontMetrics
    et = QLabel("GIF · Donador", padre)
    f = PC.fuente_px(10, QFont.Bold)
    et.setFont(f)
    et.setStyleSheet(f"background:{C['acento']};color:{C['acento_texto']};border-radius:8px;"
                     "font-size:10px;font-weight:700;")
    et.setAlignment(Qt.AlignCenter)
    et.setFixedSize(QFontMetrics(f).horizontalAdvance("GIF · Donador") + 26, 17)
    et.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    return et


class BotonGif(QPushButton):
    """Botón de contorno con la insignia «GIF · Donador» a la derecha."""

    def __init__(self, texto, icono=None, al_pulsar=None, padre=None):
        super().__init__(padre)
        self.setObjectName("contorno")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        if icono:
            self.setIcon(iconos.icono(icono, 16, C["texto"]))
        self._chip = _chip(self)
        espacio = self.fontMetrics().horizontalAdvance(" ") or 12
        self.setText(("  " if icono else "") + texto + " " * (int(self._chip.width() / espacio) + 1))
        self.setToolTip("Los GIF animados son exclusivos de los donadores de Caudal")
        if al_pulsar:
            self.clicked.connect(lambda _=False: al_pulsar())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        c = self._chip
        c.move(self.width() - c.width() - 10, (self.height() - c.height()) // 2)


def InsigniaGif(padre=None):
    return _chip(padre)


# ------------------------------------------------------------------ una vista de la rejilla
class _Vista(QFrame):
    elegido = Signal(object)

    def __init__(self, item, ancho, alto, padre=None):
        super().__init__(padre)
        self.item = item
        self.gif = None
        self.pedida = False
        self.setFixedSize(ancho, alto)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(item.get("titulo") or "")
        self._encima = False
        self.setAttribute(Qt.WA_Hover, True)

    def poner(self, datos):
        g = GifVivo(self, datos, permitido=False)
        if g.valido:
            self.gif = g
        self.update()

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.elegido.emit(self.item)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w, h = self.width(), self.height()
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 14, 14)
        p.setClipPath(ruta)
        img = self.gif.imagen() if self.gif is not None else None
        if img is not None and not img.isNull():
            esc = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.FastTransformation if self.gif.corriendo
                             else Qt.SmoothTransformation)
            p.drawImage(0, 0, esc, (esc.width() - w) // 2, (esc.height() - h) // 2, w, h)
        else:
            p.fillRect(0, 0, w, h, QColor(C["superficie2"]))
        p.setClipping(False)
        p.setPen(QPen(QColor(C["acento"] if self._encima else C["borde"]), 2 if self._encima else 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(ruta)


# ------------------------------------------------------------------ el diálogo
class DialogoBuscarGif(QDialog):
    def __init__(self, ctx, modo=G.RAZON_FOTO, padre=None, cliente=None):
        super().__init__(padre)
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle("Buscar GIF · Caudal")
        self.ctx = ctx
        self.modo = modo
        self.cliente = cliente or G.ClienteGifs()
        self.datos = None
        self.resize(700, 680)
        self.setMinimumSize(660, 560)
        self._gen = 0                 # cada búsqueda nueva invalida las respuestas viejas
        self._texto = ""
        self._siguiente = ""
        self._cargando = False
        self._bajando = 0
        self._vistas = []
        self._elegido = None
        self.columnas, self.tw, self.th = COLUMNAS, 200, 200 if modo == G.RAZON_FOTO else 124

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 16)
        v.setSpacing(10)
        cab = QHBoxLayout()
        cab.setSpacing(10)
        t = QLabel("Buscar GIF")
        t.setStyleSheet("font-size:22px;font-weight:900;background:transparent;")
        cab.addWidget(t)
        cab.addWidget(InsigniaGif(), 0, Qt.AlignVCenter)
        cab.addStretch(1)
        v.addLayout(cab)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Busca un GIF: gato, baile, anime, celebración…")
        self.campo.setClearButtonEnabled(True)
        self.campo.textEdited.connect(lambda _t: self.reloj.start())
        self.campo.returnPressed.connect(self._buscar_ya)
        v.addWidget(self.campo)
        self.estado = PC.etiqueta("", f"color:{C['texto3']};font-size:12px;", True)
        v.addWidget(self.estado)

        self.paginas = QStackedWidget()
        v.addWidget(self.paginas, 1)
        self.paginas.addWidget(self._pagina_rejilla())     # 0
        self.paginas.addWidget(self._pagina_vacia())       # 1
        self.paginas.addWidget(self._pagina_previa())      # 2

        pie = QHBoxLayout()
        self.atribucion = QLabel("Powered by GIPHY")
        self.atribucion.setObjectName("atribucion_giphy")
        self.atribucion.setStyleSheet(f"color:{C['texto3']};font-size:10.5px;font-weight:600;"
                                      "letter-spacing:0.4px;background:transparent;")
        pie.addWidget(self.atribucion, 0, Qt.AlignVCenter)
        pie.addStretch(1)
        c = QPushButton("Cancelar")
        c.setObjectName("contorno")
        c.setFocusPolicy(Qt.NoFocus)
        c.clicked.connect(self.reject)
        pie.addWidget(c)
        v.addLayout(pie)

        self.reloj = QTimer(self)
        self.reloj.setSingleShot(True)
        self.reloj.setInterval(RETRASO_BUSQUEDA_MS)
        self.reloj.timeout.connect(self._buscar_ya)
        # los GIF del momento al abrir
        QTimer.singleShot(0, lambda: self._buscar("", nueva=True))

    # ------------------------------------------------------------ páginas
    def _pagina_rejilla(self):
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setStyleSheet("background:transparent;")
        self.rejilla = QGridLayout(self.interior)
        self.rejilla.setContentsMargins(0, 4, 8, 8)
        self.rejilla.setHorizontalSpacing(12)
        self.rejilla.setVerticalSpacing(12)
        self.rejilla.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.area.setWidget(self.interior)
        self.area.verticalScrollBar().valueChanged.connect(self._al_desplazar)
        self.area.verticalScrollBar().rangeChanged.connect(lambda *_a: QTimer.singleShot(0, self._al_desplazar))
        return self.area

    def _pagina_vacia(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(8)
        self.vacio_icono = QLabel()
        self.vacio_icono.setAlignment(Qt.AlignCenter)
        self.vacio_icono.setPixmap(iconos.pixmap("lupa", 44, C["texto3"]))
        self.vacio_icono.setStyleSheet("background:transparent;")
        v.addWidget(self.vacio_icono)
        self.vacio_titulo = QLabel("")
        self.vacio_titulo.setAlignment(Qt.AlignCenter)
        self.vacio_titulo.setStyleSheet("font-size:17px;font-weight:800;background:transparent;")
        v.addWidget(self.vacio_titulo)
        self.vacio_texto = QLabel("")
        self.vacio_texto.setWordWrap(True)
        self.vacio_texto.setAlignment(Qt.AlignCenter)
        self.vacio_texto.setMaximumWidth(440)
        self.vacio_texto.setStyleSheet(f"color:{C['texto2']};font-size:13px;background:transparent;")
        v.addWidget(self.vacio_texto, 0, Qt.AlignHCenter)
        return w

    def _pagina_previa(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(14)
        self.previa_titulo = QLabel("Así se verá")
        self.previa_titulo.setAlignment(Qt.AlignCenter)
        self.previa_titulo.setStyleSheet("font-size:17px;font-weight:800;background:transparent;")
        v.addWidget(self.previa_titulo)
        if self.modo == G.RAZON_FOTO:
            self.previa = PC.Avatar(230, "", None, None, anillo=C["superficie3"])
        else:
            self.previa = PC.FondoPerfil(180, 18, False, 0.0, None, None)
            self.previa.setFixedWidth(480)
        v.addWidget(self.previa, 0, Qt.AlignHCenter)
        self.previa_estado = PC.etiqueta("", f"color:{C['texto2']};font-size:12.5px;", True)
        self.previa_estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.previa_estado)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        fila.addStretch(1)
        self.bt_otro = PC.boton("Elegir otro", "contorno", al_pulsar=self._elegir_otro)
        fila.addWidget(self.bt_otro)
        self.bt_usar = PC.boton("Usar este GIF", "principal", "listo", al_pulsar=self._usar)
        self.bt_usar.setEnabled(False)
        fila.addWidget(self.bt_usar)
        fila.addStretch(1)
        v.addLayout(fila)
        return w

    # ------------------------------------------------------------ búsqueda
    def _buscar_ya(self):
        self.reloj.stop()
        texto = self.campo.text().strip()
        if texto == self._texto and self._vistas:
            return
        self._buscar(texto, nueva=True)

    def _buscar(self, texto, nueva=True, pos=""):
        self._gen += 1
        gen = self._gen
        self._cargando = True
        if nueva:
            self._texto = texto
            self._siguiente = ""
            self.estado.setText("Buscando…" if texto else "Cargando los GIF del momento…")
        else:
            self.estado.setText("Buscando más…")
        en_segundo_plano(self.cliente.buscar, texto, pos,
                         ok=lambda r, g=gen, n=nueva: self._llego(g, r, n),
                         error=lambda e, g=gen: self._fallo(g, e), dueno=self, urgente=True)

    def _fallo(self, gen, _e):
        if gen != self._gen:
            return
        self._cargando = False
        if not self._vistas:
            self._vacio("No pudimos buscar", G.MSG_FALLO_BUSQUEDA, "globo")
        self.estado.setText("")

    def _vacio(self, titulo, texto, icono="lupa"):
        self.vacio_icono.setPixmap(iconos.pixmap(icono, 44, C["texto3"]))
        self.vacio_titulo.setText(titulo)
        self.vacio_texto.setText(texto)
        self.paginas.setCurrentIndex(1)

    def _llego(self, gen, r, nueva):
        if gen != self._gen:
            return
        self._cargando = False
        r = r if isinstance(r, dict) else {}
        err = r.get("error") or ""
        aviso = r.get("aviso") or ""
        if nueva:
            self._limpiar()
        if err:
            if err == "sin_clave":
                self._vacio("Muy pronto", G.MSG_SIN_CLAVE, "estrella")
            elif err == "no_permitido":
                self._vacio("Solo para donadores", G.MSG_NO_PERMITIDO, "estrella")
            else:
                self._vacio("No pudimos buscar", G.MSG_FALLO_BUSQUEDA, "globo")
            self.estado.setText(aviso)
            return
        items = r.get("items") or []
        self._siguiente = r.get("siguiente") or ""
        for it in items:
            self._agregar(it)
        # el aviso del servicio nunca se ignora
        self.estado.setText(aviso)
        if not self._vistas:
            q = self._texto
            self._vacio("Sin resultados" if q else "Aún no hay GIF",
                        f"No encontramos GIF para «{q}». Prueba con otra palabra." if q
                        else "Ahora mismo no hay GIF del momento. Prueba a buscar algo.")
            return
        if self.paginas.currentIndex() != 2:
            self.paginas.setCurrentIndex(0)
        self._reacomodar()
        QTimer.singleShot(0, self._al_desplazar)

    def _limpiar(self):
        for vis in self._vistas:
            if vis.gif is not None:
                vis.gif.detener()
            self.rejilla.removeWidget(vis)
            vis.deleteLater()
        self._vistas = []
        self.area.verticalScrollBar().setValue(0)

    def _agregar(self, item):
        i = len(self._vistas)
        vis = _Vista(item, self.tw, self.th, self.interior)
        vis.elegido.connect(self._elegir)
        self._vistas.append(vis)
        self.rejilla.addWidget(vis, i // self.columnas, i % self.columnas)
        vis.show()

    def _medidas(self):
        """Columnas (3 o 4) y tamaño de cada vista según el ancho disponible."""
        ancho = max(300, self.area.viewport().width() - 10)
        cols = 4 if ancho >= 860 else 3
        tw = (ancho - 12 * (cols - 1)) // cols
        th = tw if self.modo == G.RAZON_FOTO else int(tw * 0.62)
        return cols, tw, th

    def _reacomodar(self):
        cols, tw, th = self._medidas()
        if (cols, tw, th) == (self.columnas, self.tw, self.th):
            return
        self.columnas, self.tw, self.th = cols, tw, th
        for vis in self._vistas:
            self.rejilla.removeWidget(vis)
        for i, vis in enumerate(self._vistas):
            vis.setFixedSize(tw, th)
            self.rejilla.addWidget(vis, i // cols, i % cols)
        QTimer.singleShot(0, self._al_desplazar)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reacomodar()

    # ------------------------------------------------------------ carga perezosa y animación limitada
    def _visible(self, vis, margen=0):
        vp = self.area.viewport()
        y = vis.mapTo(vp, vis.rect().topLeft()).y()
        return y + vis.height() > -margen and y < vp.height() + margen

    def _al_desplazar(self, *_a):
        if self.paginas.currentIndex() == 2:
            return
        # 1) pedir las vistas que están cerca de verse
        for vis in self._vistas:
            if self._bajando >= MAX_BAJANDO:
                break
            if not vis.pedida and self._visible(vis, 260):
                self._pedir_vista(vis)
        # 2) animar solo unas pocas, las primeras a la vista
        animadas = 0
        for vis in self._vistas:
            if vis.gif is None:
                continue
            si = self._visible(vis) and animadas < MAX_ANIMADAS
            vis.gif.permitir(si)
            animadas += 1 if si else 0
        # 3) paginación al llegar abajo
        b = self.area.verticalScrollBar()
        if self._siguiente and not self._cargando and b.value() >= b.maximum() - 320:
            self._buscar(self._texto, nueva=False, pos=self._siguiente)

    def _pedir_vista(self, vis):
        vis.pedida = True
        self._bajando += 1
        url = vis.item.get("vista") or ""

        def listo(datos, vis=vis):
            self._bajando -= 1
            try:
                if datos:
                    vis.poner(datos)
            except RuntimeError:
                return
            self._al_desplazar()

        def fallo(_e):
            self._bajando -= 1
            self._al_desplazar()
        en_segundo_plano(self.cliente.vista, url, ok=listo, error=fallo, dueno=vis)

    # ------------------------------------------------------------ elegir, previsualizar, usar
    def _pausar_rejilla(self, si):
        for vis in self._vistas:
            if vis.gif is not None and si:
                vis.gif.permitir(False)

    def _elegir(self, item):
        self._elegido = item
        self._pausar_rejilla(True)
        self.paginas.setCurrentIndex(2)
        self.bt_usar.setEnabled(False)
        self.previa_estado.setText("Descargando tu GIF…")
        self.previa_titulo.setText(item.get("titulo") or "Así se verá")
        if self.modo == G.RAZON_FOTO:
            self.previa._quitar_gif()
            self.previa.update()
        else:
            self.previa.quitar()
        gif = item.get("gif") or ""

        def listo(datos, item=item):
            if item is not self._elegido:
                return
            self.datos_elegidos = datos
            self.previa.poner_gif(datos)
            self.previa_estado.setText("Así se verá en tu perfil." if self.modo == G.RAZON_FOTO
                                       else "Así se verá tu fondo.")
            self.bt_usar.setEnabled(True)

        def fallo(e, item=item):
            if item is self._elegido:
                self.previa_estado.setText(str(e) or "No se pudo bajar ese GIF. Prueba con otro.")
        en_segundo_plano(self.cliente.bajar, gif, ok=listo, error=fallo, dueno=self, urgente=True)

    def _elegir_otro(self):
        self._elegido = None
        self.paginas.setCurrentIndex(0 if self._vistas else 1)
        QTimer.singleShot(0, self._al_desplazar)

    def _usar(self):
        d = getattr(self, "datos_elegidos", None)
        if not d:
            return
        self.datos = d
        self.accept()

    def done(self, r):
        for vis in self._vistas:
            if vis.gif is not None:
                vis.gif.permitir(False)
        super().done(r)
