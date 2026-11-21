# -*- coding: utf-8 -*-
"""Piezas editables de la escena de escritorio: una ventana sin marco que el usuario puede
mover, redimensionar, escalar con la rueda (Ctrl) y ocultar con el ratón.

Hay un modo edición global (`activar_edicion`). Mientras está activo, cada pieza muestra
su botón ✕ (arriba a la derecha) y su asa de redimensionar (abajo a la derecha). Sin modo
edición, arrastrar con Alt pulsado también mueve la pieza.
"""

import math
import weakref

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QToolButton, QWidget

ZONA_ASA = 18          # lado de la zona sensible de la esquina inferior derecha
TAM_ASA = 14           # lado del dibujo del asa
TAM_CERRAR = 22        # lado del botón ✕
ESCALA_MIN = 0.5       # escala mínima respecto al tamaño de creación
ESCALA_MAX = 2.5       # escala máxima respecto al tamaño de creación
PASO_ESCALA = 0.10     # cada muesca de la rueda cambia el tamaño un 10 %

_edicion = False
_piezas = []           # referencias débiles a todas las PiezaEditable vivas


def activar_edicion(si: bool):
    """Activa o desactiva el modo edición para todas las piezas vivas."""
    global _edicion
    _edicion = bool(si)
    _piezas[:] = [r for r in _piezas if r() is not None]
    for r in list(_piezas):
        pieza = r()
        if pieza is not None:
            pieza._refrescar_edicion()


def edicion_activa() -> bool:
    """Devuelve True si el modo edición global está activo."""
    return _edicion


def _pantalla_de(widget):
    """Geometría de la pantalla donde está el widget (o la principal si no hay ninguna)."""
    pantalla = widget.screen()
    if pantalla is None:
        pantalla = QGuiApplication.primaryScreen()
    return pantalla.geometry()


def _fraccion(valor):
    """Limita una fracción al intervalo 0..1 y la redondea."""
    return round(min(1.0, max(0.0, valor)), 6)


UMBRAL_ARRASTRE = 6      # px que hay que arrastrar para que deje de ser un clic


class _Captura(QWidget):
    """Capa invisible (alfa 1) que cubre la pieza: en una ventana translúcida de Windows lo totalmente
    transparente no recibe el ratón, y así la pieza entera se puede arrastrar."""

    def __init__(self, padre):
        super().__init__(padre)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _ev):
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(self)
        try:
            p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        finally:
            p.end()


class _Asa(QWidget):
    """Asa de la esquina: tres rayitas diagonales semitransparentes. No gestiona el ratón;
    el evento no aceptado se propaga a la pieza, que es la que redimensiona."""

    def __init__(self, padre):
        super().__init__(padre)
        self.setFixedSize(TAM_ASA, TAM_ASA)
        self.setCursor(Qt.SizeFDiagCursor)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pluma = QPen(QColor(255, 255, 255, 170))
        pluma.setWidthF(1.5)
        p.setPen(pluma)
        for k in (4, 8, 12):
            p.drawLine(k, TAM_ASA - 1, TAM_ASA - 1, k)
        p.end()


class PiezaEditable(QObject):
    """Engancha un QWidget de nivel superior para que el usuario pueda editarlo.

    `padre` es el QObject dueño de esta pieza; si es None, la pieza cuelga del propio widget
    y se destruye con él. Cada operación tolera un widget ya destruido (RuntimeError).
    """

    cambiado = Signal(str)
    ocultado = Signal(str)     # la persona ocultó la pieza con la ✕ (no se emite al cargar un estado guardado)

    def __init__(self, widget, nombre, minimo=(120, 60), padre=None, libre=False, bloqueo=None):
        super().__init__(padre if padre is not None else widget)
        self._widget = widget
        # libre: arrastrar (más de UMBRAL px) mueve la pieza sin modo edición, y al pasar el ratón
        # aparecen la esquina para agrandar y la ✕. Un clic sin arrastre sigue siendo un clic.
        self._libre = bool(libre)
        self._bloqueo = bloqueo        # f(QPoint local) -> True si ahí no se arrastra (p. ej. la línea de progreso)
        self._pendiente = None         # (pos global, pos del widget) de una pulsación que aún no es arrastre
        self._encima = False
        self._nombre = str(nombre)
        self._minimo = (int(minimo[0]), int(minimo[1]))
        tam = widget.size()
        self._base = (max(1, tam.width()), max(1, tam.height()))
        self._modo = None          # None, "mover" o "redimensionar"
        self._g0 = QPoint()        # posición global al empezar el arrastre
        self._pos0 = QPoint()      # posición del widget al empezar a mover
        self._size0 = QSize()      # tamaño del widget al empezar a redimensionar

        self._boton = QToolButton(widget)
        self._boton.setText("✕")
        self._boton.setFixedSize(TAM_CERRAR, TAM_CERRAR)
        self._boton.setCursor(Qt.PointingHandCursor)
        self._boton.setToolTip("Ocultar")
        self._boton.setStyleSheet(
            "QToolButton { background-color: rgba(0, 0, 0, 160); color: white; border: none;"
            " border-radius: 11px; font-size: 11px; }"
            " QToolButton:hover { background-color: rgba(0, 0, 0, 220); }")
        self._boton.clicked.connect(lambda: self.ocultar())

        self._asa = _Asa(widget)
        # en una ventana translúcida, lo transparente deja pasar el clic al escritorio: una capa
        # invisible (alfa 1) hace que toda la pieza se pueda tocar, también los huecos de la letra
        self._captura = _Captura(widget)
        self._captura.lower()

        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        self._hijos = []
        for h in widget.findChildren(QWidget):
            if h in (self._boton, self._asa, self._captura):
                continue
            h.installEventFilter(self)
            self._hijos.append(h)
        self._boton.setVisible(False)
        self._asa.setVisible(False)
        self._recolocar()
        _piezas.append(weakref.ref(self))
        self._refrescar_edicion()

    # ----- controles y modo edición -----

    def _refrescar_edicion(self):
        """Muestra u oculta los controles según el modo edición global."""
        try:
            on = _edicion or (self._libre and (self._encima or self._modo is not None))
            self._boton.setVisible(on)
            self._asa.setVisible(on)
            if not _edicion and self._modo is None:
                self._modo = None
                self._widget.unsetCursor()
        except RuntimeError:
            pass

    def _recolocar(self):
        """Coloca el ✕ arriba a la derecha y el asa abajo a la derecha."""
        try:
            w, h = self._widget.width(), self._widget.height()
            self._captura.setGeometry(0, 0, w, h)
            self._boton.move(w - TAM_CERRAR - 6, 6)
            self._asa.move(w - TAM_ASA - 2, h - TAM_ASA - 2)
            self._boton.raise_()
            self._asa.raise_()
        except RuntimeError:
            pass

    def _en_zona_asa(self, gpos):
        """True si la posición global cae en la zona de 18x18 de la esquina inferior derecha."""
        local = self._widget.mapFromGlobal(gpos)
        w, h = self._widget.width(), self._widget.height()
        return QRect(w - ZONA_ASA, h - ZONA_ASA, ZONA_ASA, ZONA_ASA).contains(local)

    # ----- eventos del ratón y de la rueda -----

    def eventFilter(self, obj, ev):
        try:
            if obj is not self._widget and obj not in self._hijos:
                return False
            tipo = ev.type()
            if tipo == QEvent.Resize and obj is self._widget:
                self._recolocar()
            elif tipo == QEvent.Enter and obj is self._widget:
                self._encima = True
                self._refrescar_edicion()
            elif tipo == QEvent.Leave and obj is self._widget:
                self._encima = False
                self._refrescar_edicion()
            elif tipo == QEvent.MouseButtonPress:
                return self._presionar(ev)
            elif tipo == QEvent.MouseMove:
                return self._arrastrar(ev)
            elif tipo == QEvent.MouseButtonRelease:
                return self._soltar(ev)
            elif tipo == QEvent.Wheel:
                return self._rueda(ev)
        except RuntimeError:
            return False
        return False

    def _presionar(self, ev):
        """Empieza un arrastre con el botón izquierdo si hay edición o si se pulsa Alt."""
        if ev.button() != Qt.LeftButton:
            return False
        alt = bool(ev.modifiers() & Qt.AltModifier)
        gpos = ev.globalPosition().toPoint()
        if not _edicion and not alt:
            if not self._libre:
                return False
            if self._en_zona_asa(gpos):
                self._g0 = gpos
                self._modo = "redimensionar"
                self._size0 = QSize(self._widget.width(), self._widget.height())
                self._widget.setCursor(Qt.SizeFDiagCursor)
                return True
            local = self._widget.mapFromGlobal(gpos)
            if self._bloqueo is not None:
                try:
                    if self._bloqueo(local):
                        return False
                except Exception:  # noqa: BLE001
                    pass
            # aún no se sabe si es un clic o un arrastre: el clic sigue su curso
            self._pendiente = (gpos, self._widget.pos())
            return False
        self._g0 = gpos
        if self._en_zona_asa(gpos):
            self._modo = "redimensionar"
            self._size0 = QSize(self._widget.width(), self._widget.height())
            self._widget.setCursor(Qt.SizeFDiagCursor)
        else:
            self._modo = "mover"
            self._pos0 = self._widget.pos()
            self._widget.setCursor(Qt.SizeAllCursor)
        return True

    def _arrastrar(self, ev):
        """Mueve o redimensiona mientras se arrastra; sin arrastre, ajusta el cursor."""
        gpos = ev.globalPosition().toPoint()
        if self._modo is None and self._pendiente is not None:
            g0, p0 = self._pendiente
            if not (ev.buttons() & Qt.LeftButton):
                self._pendiente = None
            elif (gpos - g0).manhattanLength() >= UMBRAL_ARRASTRE:
                # ya es un arrastre: desde aquí la pieza se mueve
                self._pendiente = None
                self._g0, self._pos0 = g0, p0
                self._modo = "mover"
                self._widget.setCursor(Qt.SizeAllCursor)
        if self._modo is None:
            if (_edicion or (self._libre and self._encima)) and self._en_zona_asa(gpos):
                self._widget.setCursor(Qt.SizeFDiagCursor)
            else:
                self._widget.unsetCursor()
            return False
        if not (ev.buttons() & Qt.LeftButton):
            # se perdió el botón (soltado fuera de la ventana): terminamos el arrastre
            self._finalizar_arrastre()
            return True
        dx = gpos.x() - self._g0.x()
        dy = gpos.y() - self._g0.y()
        if self._modo == "mover":
            self._widget.move(self._pos0.x() + dx, self._pos0.y() + dy)
        else:
            self._redimensionar(dx, dy)
        self._recolocar()
        return True

    def _redimensionar(self, dx, dy):
        """Nuevo tamaño = tamaño inicial + desplazamiento, con mínimo y tope de pantalla."""
        pantalla = _pantalla_de(self._widget)
        mw, mh = self._minimo
        w = max(mw, min(self._size0.width() + dx, pantalla.width()))
        h = max(mh, min(self._size0.height() + dy, pantalla.height()))
        self._widget.resize(w, h)

    def _soltar(self, ev):
        if self._pendiente is not None:
            self._pendiente = None          # fue un clic: que lo reciba la pieza
            return False
        if self._modo is None or ev.button() != Qt.LeftButton:
            return False
        self._finalizar_arrastre()
        return True

    def _finalizar_arrastre(self):
        self._modo = None
        self._pendiente = None
        self._widget.unsetCursor()
        self._refrescar_edicion()
        self.cambiado.emit(self._nombre)

    def _rueda(self, ev):
        """Ctrl + rueda: escala ±10 % por muesca manteniendo el centro, entre 0.5x y 2.5x."""
        if not (ev.modifiers() & Qt.ControlModifier):
            return False
        dy = ev.angleDelta().y()
        if dy == 0:
            return True
        w, h = self._widget.width(), self._widget.height()
        base_w = self._base[0]
        actual = w / base_w
        nuevo = actual * (1 + PASO_ESCALA if dy > 0 else 1 - PASO_ESCALA)
        nuevo = max(ESCALA_MIN, min(ESCALA_MAX, nuevo))
        nw = max(1, round(base_w * nuevo))
        nh = max(1, round(h * nw / w))
        g = self._widget.geometry()
        cx = g.x() + g.width() / 2
        cy = g.y() + g.height() / 2
        self._widget.resize(nw, nh)
        self._widget.move(round(cx - nw / 2), round(cy - nh / 2))
        self._recolocar()
        self.cambiado.emit(self._nombre)
        return True

    # ----- ocultar, mostrar y estado -----

    def ocultar(self):
        """Oculta la pieza y avisa con `cambiado` y `ocultado`."""
        try:
            self._modo = None
            self._widget.hide()
            self.cambiado.emit(self._nombre)
            self.ocultado.emit(self._nombre)
        except RuntimeError:
            pass

    def mostrar(self):
        """Muestra la pieza y avisa con `cambiado`."""
        try:
            self._widget.show()
            self.cambiado.emit(self._nombre)
        except RuntimeError:
            pass

    def estado(self) -> dict:
        """Posición y tamaño como fracciones (0..1) de la pantalla del widget, y si es visible.

        Devuelve {} si el widget ya fue destruido.
        """
        try:
            g = self._widget.geometry()
            p = _pantalla_de(self._widget)
            if p.width() <= 0 or p.height() <= 0:
                return {}
            return {
                "x": _fraccion((g.x() - p.x()) / p.width()),
                "y": _fraccion((g.y() - p.y()) / p.height()),
                "w": _fraccion(g.width() / p.width()),
                "h": _fraccion(g.height() / p.height()),
                "visible": bool(self._widget.isVisible()),
            }
        except RuntimeError:
            return {}

    def aplicar(self, estado: dict, pantalla: QRect):
        """Coloca el widget según las fracciones de `estado` dentro de `pantalla`.

        Lo recorta para que quede entero dentro de la pantalla y lo muestra u oculta según
        "visible". Si `estado` está vacío o mal formado, no hace nada y no lanza excepciones.
        """
        try:
            if not isinstance(estado, dict) or not estado:
                return
            try:
                fx, fy, fw, fh = (float(estado[k]) for k in ("x", "y", "w", "h"))
            except (KeyError, TypeError, ValueError):
                return
            if not all(math.isfinite(v) for v in (fx, fy, fw, fh)):
                return
            if not isinstance(pantalla, QRect) or pantalla.width() <= 0 or pantalla.height() <= 0:
                return
            fx, fy, fw, fh = (_fraccion(v) for v in (fx, fy, fw, fh))
            pw, ph = pantalla.width(), pantalla.height()
            w = max(1, min(round(fw * pw), pw))
            h = max(1, min(round(fh * ph), ph))
            x = round(pantalla.x() + fx * pw)
            y = round(pantalla.y() + fy * ph)
            x = min(max(x, pantalla.x()), pantalla.x() + pw - w)
            y = min(max(y, pantalla.y()), pantalla.y() + ph - h)
            self._widget.setGeometry(x, y, w, h)
            self._widget.setVisible(bool(estado.get("visible", True)))
            self._recolocar()
        except RuntimeError:
            pass
