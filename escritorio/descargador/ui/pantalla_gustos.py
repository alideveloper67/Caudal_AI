# -*- coding: utf-8 -*-
"""«¿Qué artistas te gustan?»: pantalla a pantalla completa para elegir artistas favoritos.

Se muestra al crear la cuenta (o al entrar con una que aún no eligió) y se reabre desde
Ajustes. Foto circular, aro de acento animado con check, chips de lo elegido, buscador con
retraso de 350 ms y «Omitir por ahora» siempre a la vista. El guardado lo hace `gustos.Gustos`."""

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QColor, QFontMetrics, QIcon, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from .. import gustos as G
from ..hilos import en_segundo_plano
from . import iconos, imagenes
from .componentes import fuente as _fuente
from .estilos import C, hoja

def fuente(px, peso=400, titulo=False):
    from PySide6.QtGui import QFont
    return _fuente(px, QFont.Weight(int(peso)), titulo)


RETRASO_BUSQUEDA_MS = 350
LADO_FOTO = 108
ANCHO_TARJETA = 148
ALTO_TARJETA = 168
_RESUELTOS = {}            # nombre en minúsculas -> artista del catálogo (en memoria)


def _clave(d):
    return str(d.get("nombre") or "").strip().lower()


def _color_de(nombre):
    h = sum(ord(c) * (i + 3) for i, c in enumerate(nombre)) % 360
    return QColor.fromHsv(h, 120, 150), QColor.fromHsv((h + 40) % 360, 150, 90)


def _iniciales(nombre):
    partes = [p for p in nombre.replace("-", " ").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


class TarjetaArtista(QWidget):
    """Foto circular + nombre. Al elegirla, un aro de acento y un check aparecen con animación."""

    alternar = Signal(object)

    def __init__(self, dato, padre=None):
        super().__init__(padre)
        self.dato = dato
        self.setFixedSize(ANCHO_TARJETA, ALTO_TARJETA)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAccessibleName(dato.get("nombre", ""))
        self.setToolTip(dato.get("nombre", ""))
        self._foto = None
        self._foto_url = None
        self._sel = 0.0
        self._hover = 0.0
        self.marcada = False
        self._anim_sel = QVariantAnimation(self, duration=260, startValue=0.0, endValue=1.0)
        self._anim_sel.setEasingCurve(QEasingCurve.OutBack)
        self._anim_sel.valueChanged.connect(self._poner_sel)
        self._anim_hover = QVariantAnimation(self, duration=140)
        self._anim_hover.valueChanged.connect(self._poner_hover)
        self.refrescar_foto()

    # ---- datos
    def refrescar_foto(self):
        url = self.dato.get("portada") or ""
        if url == self._foto_url:
            return
        self._foto_url = url
        self._foto = None
        if url:
            pm = imagenes.pedir(url, LADO_FOTO * 2, LADO_FOTO * 2, "redonda", callback=self._llego)
            if pm is not None:
                self._foto = pm

    def _llego(self, pm):
        self._foto = pm
        self.update()

    def poner_marcada(self, valor, animar=True):
        valor = bool(valor)
        if valor == self.marcada:
            return
        self.marcada = valor
        self.setAccessibleDescription("Elegido" if valor else "")
        self._anim_sel.stop()
        if not animar:
            self._sel = 1.0 if valor else 0.0
            self.update()
            return
        self._anim_sel.setDirection(self._anim_sel.Direction.Forward)
        self._anim_sel.setStartValue(self._sel)
        self._anim_sel.setEndValue(1.0 if valor else 0.0)
        self._anim_sel.setEasingCurve(QEasingCurve.OutBack if valor else QEasingCurve.OutCubic)
        self._anim_sel.start()

    def _poner_sel(self, v):
        self._sel = float(v)
        self.update()

    def _poner_hover(self, v):
        self._hover = float(v)
        self.update()

    # ---- eventos
    def enterEvent(self, e):
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover)
        self._anim_hover.setEndValue(1.0)
        self._anim_hover.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim_hover.stop()
        self._anim_hover.setStartValue(self._hover)
        self._anim_hover.setEndValue(0.0)
        self._anim_hover.start()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.alternar.emit(self)
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.alternar.emit(self)
            return
        super().keyPressEvent(e)

    # ---- dibujo
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w = self.width()
        cx, cy = w / 2, 8 + 6 + LADO_FOTO / 2
        sel = max(0.0, min(1.0, self._sel))
        crece = 1.0 + 0.04 * self._hover - 0.07 * sel
        radio = LADO_FOTO / 2 * crece
        acento = QColor(C["acento"])
        # halo suave al elegir
        if sel > 0.01:
            g = QRadialGradient(QPointF(cx, cy), radio + 26)
            c0 = QColor(acento)
            c0.setAlphaF(0.34 * sel)
            c1 = QColor(acento)
            c1.setAlphaF(0.0)
            g.setColorAt(0.62, c0)
            g.setColorAt(1.0, c1)
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), radio + 26, radio + 26)
        # sombra
        sombra = QColor(0, 0, 0, 70)
        p.setPen(Qt.NoPen)
        p.setBrush(sombra)
        p.drawEllipse(QPointF(cx, cy + 4), radio, radio)
        rect = QRectF(cx - radio, cy - radio, radio * 2, radio * 2)
        if self._foto is not None and not self._foto.isNull():
            p.drawPixmap(rect, self._foto, QRectF(self._foto.rect()))
        else:
            c_a, c_b = _color_de(self.dato.get("nombre", ""))
            g = QLinearGradient(rect.topLeft(), rect.bottomRight())
            g.setColorAt(0, c_a)
            g.setColorAt(1, c_b)
            p.setBrush(g)
            p.drawEllipse(rect)
            p.setPen(QColor(255, 255, 255, 235))
            p.setFont(fuente(radio * 0.62, 800, titulo=True))
            p.drawText(rect, Qt.AlignCenter, _iniciales(self.dato.get("nombre", "")))
        # velo oscuro leve sobre lo no elegido al pasar el ratón por otro lado: no hace falta;
        # un borde fino da forma a las fotos claras
        p.setBrush(Qt.NoBrush)
        borde = QColor(255, 255, 255, int(26 + 30 * self._hover))
        p.setPen(QPen(borde, 1.2))
        p.drawEllipse(rect)
        # aro de acento
        if sel > 0.01:
            r_aro = radio + 5 + 2 * (1 - sel)
            aro = QColor(acento)
            aro.setAlphaF(min(1.0, sel * 1.4))
            p.setPen(QPen(aro, 3.0))
            p.drawEllipse(QPointF(cx, cy), r_aro, r_aro)
            # check en la esquina inferior derecha
            d = 28 * min(1.0, sel)
            ang = math.radians(45)
            bx, by = cx + (LADO_FOTO / 2 + 2) * math.cos(ang), cy + (LADO_FOTO / 2 + 2) * math.sin(ang)
            p.setPen(QPen(QColor(C["panel"]), 3.0))
            p.setBrush(acento)
            p.drawEllipse(QPointF(bx, by), d / 2, d / 2)
            if d > 12:
                ruta = QPainterPath()
                k = d / 28
                ruta.moveTo(bx - 6 * k, by + 0.5 * k)
                ruta.lineTo(bx - 1.5 * k, by + 5 * k)
                ruta.lineTo(bx + 6.5 * k, by - 4.5 * k)
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(C["acento_texto"]), 2.6 * max(0.5, k), Qt.SolidLine, Qt.RoundCap,
                              Qt.RoundJoin))
                p.drawPath(ruta)
        # foco de teclado
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(C["texto"]), 1.5, Qt.DotLine))
            p.drawEllipse(QPointF(cx, cy), radio + 9, radio + 9)
        # nombre
        f = fuente(13, 700 if sel > 0.5 else 600)
        p.setFont(f)
        color = QColor(C["acento_alto"]) if sel > 0.5 else QColor(C["texto"])
        if sel <= 0.5 and self._hover < 0.05:
            color = QColor(C["texto2"])
        p.setPen(color)
        texto = QFontMetrics(f).elidedText(self.dato.get("nombre", ""), Qt.ElideRight, w - 10)
        p.drawText(QRectF(5, cy + LADO_FOTO / 2 + 14, w - 10, 22), Qt.AlignHCenter | Qt.AlignTop, texto)
        p.end()


class PantallaGustos(QDialog):
    """La pantalla. `exec()` devuelve Accepted tanto al continuar como al omitir; el resultado
    queda en `self.accion` ("guardar" u "omitir") y `self.lista` (los artistas elegidos)."""

    def __init__(self, gestor=None, inicial=None, ajustes=False, region="PE", padre=None):
        super().__init__(padre)
        self.gestor = gestor
        self.es_ajustes = bool(ajustes)
        self.region = region
        self.accion = None
        self.lista = []
        self.elegidos = {}              # nombre en minúsculas -> artista (en orden de elección)
        self.tarjetas = {}              # nombre en minúsculas -> tarjeta visible
        self._texto = ""
        self._columnas = 0
        self._mostrando = []            # artistas de la rejilla actual
        self._resolviendo = False
        self._mensaje_t = QTimer(self, singleShot=True, interval=2600)
        self._mensaje_t.timeout.connect(self._actualizar_contador)
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet(hoja(iconos.flechas_qss()) + f"""
QLabel#gt_eyebrow {{ color: {C['acento']}; font-size: 12px; font-weight: 800; letter-spacing: 3px; }}
QLabel#gt_titulo {{ font-size: 36px; font-weight: 900; color: {C['texto']}; }}
QLabel#gt_sub {{ font-size: 15px; color: {C['texto2']}; }}
QLabel#gt_estado {{ color: {C['texto3']}; font-size: 13px; }}
QLineEdit#gt_buscar {{
    background: {C['superficie2']}; border: 2px solid {C['borde']}; border-radius: 24px;
    padding: 10px 18px 10px 6px; font-size: 15px; }}
QLineEdit#gt_buscar:hover {{ border-color: {C['borde_claro']}; }}
QLineEdit#gt_buscar:focus {{ border-color: {C['acento']}; background: {C['superficie3']}; }}
QPushButton#gt_chip {{
    background: {C['superficie2']}; border: 1px solid {C['borde_claro']}; border-radius: 17px;
    padding: 4px 12px 4px 5px; font-size: 12.5px; font-weight: 600; color: {C['texto']}; text-align: left; }}
QPushButton#gt_chip:hover {{ background: {C['superficie3']}; border-color: {C['acento']}; }}
QPushButton#gt_omitir {{ background: transparent; border: none; color: {C['texto2']};
    font-size: 14px; font-weight: 600; padding: 10px 16px; }}
QPushButton#gt_omitir:hover {{ color: {C['texto']}; text-decoration: underline; }}
QPushButton#principal {{ padding: 12px 34px; border-radius: 22px; font-size: 14.5px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 6px 0; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,40); border-radius: 4px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,80); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
""")
        self._construir()
        self.reloj = QTimer(self, singleShot=True, interval=RETRASO_BUSQUEDA_MS)
        self.reloj.timeout.connect(self._buscar)
        self.campo.textEdited.connect(lambda _t: self.reloj.start())
        self.campo.returnPressed.connect(lambda: (self.reloj.stop(), self._buscar()))
        for a in G.limpiar(inicial):
            self.elegidos[_clave(a)] = a
        self._pintar_chips()
        self._mostrar_sugeridos()
        self._actualizar_contador()
        QTimer.singleShot(0, self.campo.setFocus)

    # ------------------------------------------------------------ construcción
    def _construir(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        centro = QWidget()
        centro.setObjectName("gt_centro")
        centro.setMaximumWidth(1060)
        v = QVBoxLayout(centro)
        v.setContentsMargins(40, 26, 40, 0)
        v.setSpacing(0)
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(centro, 100)
        fila.addStretch(1)
        raiz.addLayout(fila, 1)

        eyebrow = QLabel("TU MÚSICA, A TU MEDIDA" if not self.es_ajustes else "MIS ARTISTAS FAVORITOS")
        eyebrow.setObjectName("gt_eyebrow")
        eyebrow.setAlignment(Qt.AlignHCenter)
        v.addWidget(eyebrow)
        v.addSpacing(8)
        titulo = QLabel("¿Qué artistas te gustan?")
        titulo.setObjectName("gt_titulo")
        titulo.setAlignment(Qt.AlignHCenter)
        titulo.setFont(fuente(36, 900, titulo=True))
        v.addWidget(titulo)
        v.addSpacing(6)
        sub = QLabel("Elige tus favoritos y Caudal te recomendará música parecida desde el primer día.")
        sub.setObjectName("gt_sub")
        sub.setAlignment(Qt.AlignHCenter)
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addSpacing(18)

        self.campo = QLineEdit()
        self.campo.setObjectName("gt_buscar")
        self.campo.setPlaceholderText("Busca un artista…")
        self.campo.setClearButtonEnabled(True)
        self.campo.setFixedHeight(48)
        self.campo.setFixedWidth(520)
        self.campo.addAction(iconos.icono("lupa", 18, C["texto3"]), QLineEdit.LeadingPosition)
        self.campo.setAccessibleName("Buscar un artista")
        v.addWidget(self.campo, 0, Qt.AlignHCenter)
        v.addSpacing(14)

        # chips de lo elegido
        self.zona_chips = QScrollArea()
        self.zona_chips.setFrameShape(QFrame.NoFrame)
        self.zona_chips.setWidgetResizable(True)
        self.zona_chips.setFixedHeight(46)
        self.zona_chips.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zona_chips.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zona_chips.viewport().setAutoFillBackground(False)
        interior = QWidget()
        interior.setObjectName("gt_interior")
        interior.setStyleSheet("QWidget#gt_interior{background:transparent;}")
        self.fila_chips = QHBoxLayout(interior)
        self.fila_chips.setContentsMargins(0, 4, 0, 4)
        self.fila_chips.setSpacing(8)
        self.zona_chips.setWidget(interior)
        v.addWidget(self.zona_chips)

        self.estado = QLabel("")
        self.estado.setObjectName("gt_estado")
        self.estado.setAlignment(Qt.AlignHCenter)
        v.addWidget(self.estado)
        v.addSpacing(4)

        self.area = QScrollArea()
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setWidgetResizable(True)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.viewport().setAutoFillBackground(False)
        self.rejilla_w = QWidget()
        self.rejilla_w.setAttribute(Qt.WA_TranslucentBackground, True)
        self.rejilla = QGridLayout(self.rejilla_w)
        self.rejilla.setContentsMargins(0, 6, 0, 18)
        self.rejilla.setHorizontalSpacing(10)
        self.rejilla.setVerticalSpacing(6)
        self.area.setWidget(self.rejilla_w)
        v.addWidget(self.area, 1)

        # barra inferior
        barra = QFrame()
        barra.setObjectName("gt_barra")
        barra.setStyleSheet(f"QFrame#gt_barra{{background:rgba(6,7,10,150);border-top:1px solid {C['borde']};}}")
        h = QHBoxLayout(barra)
        h.setContentsMargins(40, 14, 40, 14)
        h.setSpacing(14)
        cont = QVBoxLayout()
        cont.setSpacing(1)
        self.contador = QLabel("0 elegidos")
        self.contador.setFont(fuente(16, 800))
        self.ayuda = QLabel("")
        self.ayuda.setObjectName("gt_estado")
        cont.addWidget(self.contador)
        cont.addWidget(self.ayuda)
        h.addLayout(cont, 1)
        self.bt_omitir = QPushButton("Cancelar" if self.es_ajustes else "Omitir por ahora")
        self.bt_omitir.setObjectName("gt_omitir")
        self.bt_omitir.setCursor(Qt.PointingHandCursor)
        self.bt_omitir.clicked.connect(self._omitir)
        self.bt_seguir = QPushButton("Guardar" if self.es_ajustes else "Continuar")
        self.bt_seguir.setObjectName("principal")
        self.bt_seguir.setCursor(Qt.PointingHandCursor)
        self.bt_seguir.setDefault(True)
        self.bt_seguir.clicked.connect(self._continuar)
        h.addWidget(self.bt_omitir)
        h.addWidget(self.bt_seguir)
        raiz.addWidget(barra)

    # ------------------------------------------------------------ fondo
    def paintEvent(self, _e):
        p = QPainter(self)
        r = QRectF(self.rect())
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor(C["panel"]))
        g.setColorAt(1, QColor(C["fondo"]))
        p.fillRect(r, g)
        for (fx, fy, rad, color, alfa) in ((0.5, -0.05, 0.75, C["acento"], 46),
                                           (0.95, 1.05, 0.65, C["violeta"], 38),
                                           (0.04, 0.9, 0.5, C["acento_bajo"], 22)):
            cen = QPointF(r.width() * fx, r.height() * fy)
            d = max(r.width(), r.height()) * rad
            rg = QRadialGradient(cen, d)
            c0 = QColor(color)
            c0.setAlpha(alfa)
            c1 = QColor(color)
            c1.setAlpha(0)
            rg.setColorAt(0, c0)
            rg.setColorAt(1, c1)
            p.fillRect(r, rg)
        p.end()

    # ------------------------------------------------------------ rejilla
    def _cols(self):
        ancho = max(1, self.area.viewport().width() - 4)
        return max(2, ancho // (ANCHO_TARJETA + 10))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._columnas and self._cols() != self._columnas:
            QTimer.singleShot(0, self._recolocar)

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._recolocar)

    def _recolocar(self):
        """Cambia las columnas al cambiar el ancho, sin rehacer las tarjetas (se conserva todo)."""
        cols = self._cols()
        if cols == self._columnas:
            return
        tarjetas = list(self.tarjetas.values())
        for t in tarjetas:
            self.rejilla.removeWidget(t)
        self._columnas = cols
        for i, t in enumerate(tarjetas):
            self.rejilla.addWidget(t, i // cols, i % cols)
        for c in range(cols):
            self.rejilla.setColumnStretch(c, 1)
        for c in range(cols, cols + 8):
            self.rejilla.setColumnStretch(c, 0)
        for r in range(len(tarjetas) // cols + 3):
            self.rejilla.setRowStretch(r, 0)
        self.rejilla.setRowStretch(len(tarjetas) // cols + 1, 1)

    def _mostrar_sugeridos(self):
        elegidos = list(self.elegidos.values())
        nombres = {_clave(a) for a in elegidos}
        base = [dict(_RESUELTOS.get(n.lower()) or {"nombre": n, "id": "", "portada": ""})
                for n in G.populares(self.region) if n.lower() not in nombres]
        # los ya elegidos primero: al reabrir desde Ajustes se ven marcados
        self._mostrando = elegidos + base
        self.estado.setText("")
        self._pintar_rejilla(self._mostrando)
        pendientes = [a for a in base if not a.get("id")]
        if pendientes:
            self._resolver(pendientes)

    def _pintar_rejilla(self, artistas):
        while self.rejilla.count():
            it = self.rejilla.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.tarjetas = {}
        self._columnas = self._cols()
        for i, a in enumerate(artistas):
            t = TarjetaArtista(a)
            t.alternar.connect(self._alternar)
            t.poner_marcada(_clave(a) in self.elegidos, animar=False)
            self.rejilla.addWidget(t, i // self._columnas, i % self._columnas)
            self.tarjetas[_clave(a)] = t
        for c in range(self._columnas):
            self.rejilla.setColumnStretch(c, 1)
        for c in range(self._columnas, self._columnas + 6):
            self.rejilla.setColumnStretch(c, 0)
        self.rejilla.setRowStretch(len(artistas) // max(1, self._columnas) + 1, 1)

    def _resolver(self, pendientes):
        """Trae foto e id de los populares del catálogo (cada uno aparte; si falla, se queda el nombre)."""
        for a in pendientes:
            en_segundo_plano(G.resolver_popular, a["nombre"], ok=lambda r, a=a: self._resuelto(a, r),
                             error=lambda _e: None, dueno=self, urgente=False)

    def _resuelto(self, a, r):
        if not isinstance(r, dict) or not r.get("id"):
            return
        a["id"], a["portada"] = r.get("id", ""), r.get("portada", "")
        _RESUELTOS[a["nombre"].lower()] = {"nombre": a["nombre"], "id": a["id"], "portada": a["portada"]}
        t = self.tarjetas.get(_clave(a))
        if t is not None:
            t.dato = a
            t.refrescar_foto()
            t.update()
        elegido = self.elegidos.get(_clave(a))
        if elegido is not None and not elegido.get("id"):
            elegido["id"], elegido["portada"] = a["id"], a["portada"]
            self._pintar_chips()

    # ------------------------------------------------------------ búsqueda
    def _buscar(self):
        from .. import catalogo
        texto = self.campo.text().strip()
        if texto == self._texto:
            return
        self._texto = texto
        if len(texto) < 2:
            if not texto:
                self._mostrar_sugeridos()
            return
        self.estado.setText("Buscando…")
        en_segundo_plano(catalogo.buscar, texto, "artistas", 18,
                         ok=lambda r, t=texto: self._resultados(t, r),
                         error=lambda _e, t=texto: self._fallo(t), dueno=self, urgente=True)

    def _resultados(self, texto, r):
        if texto != self._texto:
            return
        artistas = [G.artista_de_elemento(e) for e in (r or []) if e.get("tipo") == "artista"]
        artistas = [a for a in artistas if a["nombre"]]
        self._mostrando = artistas
        self.estado.setText("" if artistas else f"No encontramos artistas para «{texto}».")
        self._pintar_rejilla(artistas)

    def _fallo(self, texto):
        if texto == self._texto:
            self.estado.setText("No se pudo buscar. Revisa tu conexión e inténtalo de nuevo.")

    # ------------------------------------------------------------ selección
    def _alternar(self, tarjeta):
        a = tarjeta.dato
        k = _clave(a)
        if k in self.elegidos:
            self.elegidos.pop(k)
            tarjeta.poner_marcada(False)
        else:
            if len(self.elegidos) >= G.MAXIMO:
                self._mensaje(f"Máximo {G.MAXIMO}: quita uno para añadir otro.")
                return
            self.elegidos[k] = a
            tarjeta.poner_marcada(True)
        self._pintar_chips()
        self._actualizar_contador()

    def _quitar(self, k):
        self.elegidos.pop(k, None)
        t = self.tarjetas.get(k)
        if t is not None:
            t.poner_marcada(False)
        self._pintar_chips()
        self._actualizar_contador()

    def _pintar_chips(self):
        while self.fila_chips.count():
            it = self.fila_chips.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.zona_chips.setVisible(bool(self.elegidos))
        self.fila_chips.addStretch(1)
        for k, a in self.elegidos.items():
            b = QPushButton(f"{a['nombre']}   ✕")
            b.setObjectName("gt_chip")
            b.setFixedHeight(34)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip("Quitar de mis favoritos")
            b.setAccessibleName(f"Quitar a {a['nombre']}")
            b.setIconSize(QSize(24, 24))
            if a.get("portada"):
                pm = imagenes.pedir(a["portada"], 48, 48, "redonda",
                                    callback=lambda pm, b=b: self._icono_chip(b, pm))
                if pm is not None:
                    b.setIcon(QIcon(pm))
            else:
                b.setIcon(QIcon(self._pm_inicial(a["nombre"])))
            b.clicked.connect(lambda _=False, k=k: self._quitar(k))
            self.fila_chips.addWidget(b)
        self.fila_chips.addStretch(1)

    def _icono_chip(self, b, pm):
        try:
            b.setIcon(QIcon(pm))
        except RuntimeError:
            pass

    @staticmethod
    def _pm_inicial(nombre, lado=48):
        pm = QPixmap(lado, lado)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        a, b = _color_de(nombre)
        g = QLinearGradient(0, 0, lado, lado)
        g.setColorAt(0, a)
        g.setColorAt(1, b)
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, lado, lado)
        p.setPen(QColor(255, 255, 255, 235))
        p.setFont(fuente(lado * 0.4, 800))
        p.drawText(QRectF(0, 0, lado, lado), Qt.AlignCenter, _iniciales(nombre)[:1])
        p.end()
        return pm

    def _actualizar_contador(self):
        n = len(self.elegidos)
        self.contador.setText("Ningún artista elegido" if n == 0 else
                              "1 elegido" if n == 1 else f"{n} elegidos")
        listo = n >= G.SUGERIDO
        self.contador.setStyleSheet(f"color:{C['acento_alto'] if listo else C['texto']};")
        if n == 0:
            self.ayuda.setText(f"Elige al menos {G.SUGERIDO} para mejores recomendaciones · máximo {G.MAXIMO}")
        elif not listo:
            faltan = G.SUGERIDO - n
            self.ayuda.setText(f"Elige {faltan} más para mejores recomendaciones · máximo {G.MAXIMO}")
        else:
            self.ayuda.setText(f"Perfecto. Puedes elegir hasta {G.MAXIMO} y cambiarlos cuando quieras.")
        self.ayuda.setStyleSheet(f"color:{C['texto3']};font-size:13px;")
        self.bt_seguir.setEnabled(n > 0 or self.es_ajustes)

    def _mensaje(self, texto):
        self.ayuda.setText(texto)
        self.ayuda.setStyleSheet(f"color:{C['aviso']};font-size:13px;font-weight:700;")
        self._mensaje_t.start()

    # ------------------------------------------------------------ salida
    def _continuar(self):
        self.accion = "guardar"
        self.lista = G.limpiar(list(self.elegidos.values()))
        self.accept()

    def _omitir(self):
        if self.es_ajustes:
            self.accion = None
            self.reject()
            return
        self.accion = "omitir"
        self.lista = []
        self.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._omitir()
            return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        # cerrar la ventana equivale a omitir (en Ajustes, a cancelar)
        if self.accion is None and not self.es_ajustes:
            self.accion = "omitir"
            self.lista = []
        super().closeEvent(e)


def abrir(gestor, inicial=None, ajustes=False, region="PE", padre=None):
    """Muestra la pantalla a pantalla completa. Devuelve ("guardar"|"omitir"|None, lista)."""
    d = PantallaGustos(gestor, inicial, ajustes, region, padre)
    d.setWindowTitle("Tus artistas favoritos · Caudal")
    d.showMaximized()
    d.exec()
    return d.accion, d.lista


def al_entrar(cuenta, coleccion, region="PE"):
    """Antes de la ventana principal: si la cuenta aún no eligió artistas, muestra la pantalla;
    si hubo cambios pendientes de subir, los reintenta. Nunca lanza errores hacia afuera."""
    sesion = (cuenta or {}).get("sesion")
    if sesion is None or not getattr(sesion, "access", ""):
        return None
    try:
        g = G.Gustos(sesion, coleccion)
        if not g.hace_falta_pantalla():
            from ..hilos import en_segundo_plano
            en_segundo_plano(g.sincronizar, error=lambda _e: None)   # reintenta lo pendiente
            return None
        accion, lista = abrir(g, region=region)
        if accion in ("guardar", "omitir"):
            g.guardar(lista, omitido=(accion == "omitir"))
        return accion
    except Exception:  # noqa: BLE001
        return None
