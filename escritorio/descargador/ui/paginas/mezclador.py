# -*- coding: utf-8 -*-
"""Mezclador: tu propia mesa de DJ.

Se arma un set con canciones de la cola, de Tus me gusta o de tus listas, se
ordena y, entre cada canción y la siguiente, se ajusta:

* cuántos segundos antes del final empieza a entrar la siguiente,
* cuánto dura el fundido,
* si hay cambio de graves.

Se puede probar un paso (suena solo esa unión), reproducir el set entero y
guardarlo con nombre. Lo que no se ha guardado queda como borrador, así que
cambiar de color o de pantalla no lo pierde.

Cómo se abre:  PaginaMezclador(ctx)  (como las demás páginas de ui/paginas/).
"""

import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget)

from ... import mezcla_dj as md
from .. import iconos
from ..componentes import Pagina, Portada, SinResultados, _borrar_layout, formato_tiempo
from ..estilos import C

CLAVE_BORRADOR = "mezclador_borrador"
MAX_CANCIONES = 40


def _titulo(p):
    return p.get("titulo") or "Sin título"


def _artista(p):
    return p.get("artista") or ""


def _boton_plano(icono, ayuda, al_pulsar, lado=34):
    """Botón de icono que se puede alcanzar con el teclado y lo lee un lector de pantalla."""
    b = QPushButton()
    b.setFixedSize(lado, lado)
    b.setCursor(Qt.PointingHandCursor)
    b.setToolTip(ayuda)
    b.setAccessibleName(ayuda)
    b.setIcon(iconos.icono(icono, 18, C["texto2"]))
    b.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:{lado // 2}px;}}"
                    f"QPushButton:hover{{background:{C['hover']};}}"
                    f"QPushButton:focus{{border:2px solid {C['acento']};}}"
                    "QPushButton:disabled{background:transparent;}")
    b.clicked.connect(al_pulsar)
    return b


# ================================================================ elegir canciones

class ElegirCanciones(QDialog):
    """Lista con casillas para escoger qué canciones se añaden al set."""

    def __init__(self, titulo, pistas, padre=None, ya=()):
        super().__init__(padre)
        self.setWindowTitle(titulo)
        self.setMinimumSize(520, 520)
        self.pistas = [p for p in pistas if p.get("clave")]
        self._ya = set(ya)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        t = QLabel(titulo)
        t.setStyleSheet("font-size:19px;font-weight:800;")
        v.addWidget(t)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar en esta lista")
        self.buscar.setClearButtonEnabled(True)
        self.buscar.setAccessibleName("Buscar canciones")
        self.buscar.textChanged.connect(self._filtrar)
        v.addWidget(self.buscar)
        self.lista = QListWidget()
        self.lista.setAccessibleName("Canciones para añadir")
        for p in self.pistas:
            dur = formato_tiempo(p.get("duracion"))
            texto = _titulo(p) + (f" — {_artista(p)}" if _artista(p) else "") + \
                (f"   ({dur})" if dur else "")
            it = QListWidgetItem(texto)
            ya_esta = p["clave"] in self._ya
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            if ya_esta:
                it.setText(texto + "   · ya está en el set")
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, p["clave"])
            self.lista.addItem(it)
        v.addWidget(self.lista, 1)
        self.et = QLabel("")
        self.et.setObjectName("ayuda")
        v.addWidget(self.et)
        fila = QHBoxLayout()
        todo = QPushButton("Marcar todas")
        todo.clicked.connect(lambda: self._marcar(True))
        nada = QPushButton("Quitar marcas")
        nada.clicked.connect(lambda: self._marcar(False))
        fila.addWidget(todo)
        fila.addWidget(nada)
        fila.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        self.bt_anadir = QPushButton("Añadir al set")
        self.bt_anadir.setObjectName("principal")
        self.bt_anadir.setDefault(True)
        self.bt_anadir.clicked.connect(self.accept)
        fila.addWidget(cancelar)
        fila.addWidget(self.bt_anadir)
        v.addLayout(fila)
        self.lista.itemChanged.connect(self._contar)
        self._contar()
        if not self.pistas:
            self.et.setText("No hay canciones aquí todavía.")

    def _filtrar(self, texto):
        q = texto.strip().lower()
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _marcar(self, si):
        for i in range(self.lista.count()):
            it = self.lista.item(i)
            if it.isHidden() or not (it.flags() & Qt.ItemIsEnabled):
                continue
            it.setCheckState(Qt.Checked if si else Qt.Unchecked)

    def _contar(self, *_):
        n = len(self.elegidas())
        if self.pistas:
            self.et.setText(f"{n} {'canción marcada' if n == 1 else 'canciones marcadas'}")
        self.bt_anadir.setEnabled(n > 0)

    def elegidas(self):
        claves = [self.lista.item(i).data(Qt.UserRole) for i in range(self.lista.count())
                  if self.lista.item(i).checkState() == Qt.Checked]
        por_clave = {p["clave"]: p for p in self.pistas}
        return [por_clave[c] for c in claves if c in por_clave]


# ================================================================ ritmo a mano

class DialogoRitmo(QDialog):
    """Escribir el tempo de una canción o «tocarlo» con el dedo al ritmo de la música."""

    def __init__(self, titulo, bpm=0.0, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Ritmo de la canción")
        self.setMinimumWidth(420)
        self._toques = []
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        t = QLabel(f"Ritmo de «{titulo}»")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        t.setWordWrap(True)
        v.addWidget(t)
        ayuda = QLabel("Escríbelo o pulsa el botón grande al compás de la música, varias veces: "
                       "Caudal calcula los pulsos por minuto.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)
        fila = QHBoxLayout()
        self.caja = QDoubleSpinBox()
        self.caja.setRange(40.0, 220.0)
        self.caja.setDecimals(1)
        self.caja.setSingleStep(0.5)
        self.caja.setSuffix(" pulsos por minuto")
        self.caja.setValue(bpm if bpm else 120.0)
        self.caja.setAccessibleName("Pulsos por minuto")
        fila.addWidget(self.caja, 1)
        v.addLayout(fila)
        self.bt_tocar = QPushButton("Tocar el ritmo")
        self.bt_tocar.setObjectName("contorno")
        self.bt_tocar.setMinimumHeight(64)
        self.bt_tocar.setCursor(Qt.PointingHandCursor)
        self.bt_tocar.clicked.connect(lambda: self.registrar_toque(time.time()))
        v.addWidget(self.bt_tocar)
        self.et = QLabel("")
        self.et.setObjectName("ayuda")
        v.addWidget(self.et)
        pie = QHBoxLayout()
        pie.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        ok = QPushButton("Guardar ritmo")
        ok.setObjectName("principal")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        pie.addWidget(cancelar)
        pie.addWidget(ok)
        v.addLayout(pie)

    def registrar_toque(self, t):
        """Un toque en el instante t (segundos). Tras 2,5 s sin tocar, se empieza de nuevo."""
        if self._toques and t - self._toques[-1] > 2.5:
            self._toques = []
        self._toques.append(t)
        self._toques = self._toques[-9:]
        if len(self._toques) >= 3:
            gaps = [b - a for a, b in zip(self._toques, self._toques[1:])]
            bpm = 60.0 / (sum(gaps) / len(gaps))
            if 40.0 <= bpm <= 220.0:
                self.caja.setValue(round(bpm * 2) / 2)
            self.et.setText(f"{len(self._toques)} toques · {self.caja.value():.1f} por minuto")
        else:
            self.et.setText("Sigue tocando…")

    def bpm(self):
        return float(self.caja.value())


# ================================================================ onda de energía

class VistaOnda(QWidget):
    """Barras de energía de la canción con sus puntos de entrada y salida. Un clic
    marca la entrada; con Mayús (o clic derecho), la salida."""

    cambio = Signal(object, object)          # entrada, salida (segundos o None)

    def __init__(self, perfil, duracion, entrada=None, salida=None, beats=None, padre=None):
        super().__init__(padre)
        self.perfil = list(perfil or [])
        self.duracion = float(duracion or 0)
        self.entrada, self.salida = entrada, salida
        self.setFixedHeight(76)
        self.setMinimumWidth(200)
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Onda de energía de la canción. Clic para marcar la entrada; "
                               "con Mayús, la salida")
        self.setToolTip("Clic: marca dónde entra · Mayús + clic: marca dónde sale")

    def poner(self, entrada, salida):
        self.entrada, self.salida = entrada, salida
        self.update()

    def _x(self, seg):
        return seg / self.duracion * self.width() if self.duracion else 0

    def mousePressEvent(self, e):
        if not self.duracion:
            return
        seg = max(0.0, min(self.duracion, e.position().x() / max(1, self.width()) * self.duracion))
        seg = round(seg, 1)
        if e.button() == Qt.RightButton or (e.modifiers() & Qt.ShiftModifier):
            self.salida = seg
        else:
            self.entrada = seg
        self.update()
        self.cambio.emit(self.entrada, self.salida)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie2"]))
        p.drawRoundedRect(0, 0, w, h, 10, 10)
        barras = self.perfil or [0.25] * 64
        n = len(barras)
        ancho = w / n
        a = self._x(self.entrada) if self.entrada is not None else -1
        z = self._x(self.salida) if self.salida is not None else w + 1
        for i, v in enumerate(barras):
            x = i * ancho
            alto = max(3.0, (h - 16) * float(v))
            dentro = a <= x + ancho / 2 <= z
            color = QColor(C["acento"] if dentro else C["texto3"])
            color.setAlpha(235 if dentro else 110)
            p.setBrush(color)
            if not self.perfil:
                color.setAlpha(60)
                p.setBrush(color)
            p.drawRoundedRect(QRectF(x + 1, (h - alto) / 2, max(1.5, ancho - 2), alto), 1.5, 1.5)
        for seg, col in ((self.entrada, C["exito"]), (self.salida, C["error"])):
            if seg is None:
                continue
            x = self._x(seg)
            p.setPen(QPen(QColor(col), 2.5))
            p.drawLine(QPointF(x, 3), QPointF(x, h - 3))
        p.end()


# ================================================================ una canción del set

class FilaCancion(QFrame):
    subir = Signal(int)
    bajar = Signal(int)
    quitar = Signal(int)
    detalle = Signal(int)

    def __init__(self, indice, total, pista, analisis=None, abierta=False, padre=None):
        super().__init__(padre)
        self.setObjectName("caja")
        self.setAccessibleName(f"Canción {indice + 1} de {total}: {_titulo(pista)}")
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 10, 10, 10)
        h.setSpacing(12)
        n = QLabel(str(indice + 1))
        n.setFixedWidth(24)
        n.setAlignment(Qt.AlignCenter)
        n.setStyleSheet(f"color:{C['texto3']};font-size:15px;font-weight:800;")
        h.addWidget(n)
        portada = Portada(46, 46, "cuadrada", 6)
        portada.set_url(pista.get("miniatura") or "")
        h.addWidget(portada)
        v = QVBoxLayout()
        v.setSpacing(1)
        t = QLabel(_titulo(pista))
        t.setStyleSheet("font-size:14px;font-weight:700;")
        bpm = float((analisis or {}).get("bpm") or 0)
        ritmo = (f"{bpm:.0f} pulsos por minuto" if bpm else "ritmo sin analizar")
        self.et_ritmo = QLabel(" · ".join(x for x in (_artista(pista), ritmo) if x))
        self.et_ritmo.setObjectName("secundario")
        v.addWidget(t)
        v.addWidget(self.et_ritmo)
        h.addLayout(v, 1)
        d = QLabel(formato_tiempo(pista.get("duracion")))
        d.setObjectName("secundario")
        h.addWidget(d)
        self.bt_detalle = _boton_plano("chevron_arriba" if abierta else "ecualizador",
                                       "Ocultar los ajustes de la canción" if abierta
                                       else "Ajustes de la canción: ritmo, entrada, salida y sonido",
                                       lambda: self.detalle.emit(indice))
        b_arriba = _boton_plano("chevron_arriba", "Subir esta canción", lambda: self.subir.emit(indice))
        b_arriba.setEnabled(indice > 0)
        b_abajo = _boton_plano("chevron_abajo", "Bajar esta canción", lambda: self.bajar.emit(indice))
        b_abajo.setEnabled(indice < total - 1)
        b_quitar = _boton_plano("cerrar", "Quitar del set", lambda: self.quitar.emit(indice))
        for b in (self.bt_detalle, b_arriba, b_abajo, b_quitar):
            h.addWidget(b)


class PanelCancion(QFrame):
    """Los ajustes de una canción del set: ritmo, onda con entrada y salida, y un
    ecualizador de 3 bandas."""

    marcas_cambio = Signal(str, dict)
    analizar = Signal(int)
    escribir_ritmo = Signal(int)
    probar_tramo = Signal(int, float)

    def __init__(self, indice, pista, analisis, marcas, padre=None):
        super().__init__(padre)
        self.indice, self.pista = indice, pista
        self.clave = str(pista.get("clave") or "")
        dur = int(float(pista.get("duracion") or 0))
        self.dur = dur
        m = md.normalizar_marcas(marcas, dur)
        self.setObjectName("panel_cancion")
        self.setStyleSheet(f"QFrame#panel_cancion{{background:{C['superficie']};"
                           "border-radius:14px;}QFrame#panel_cancion QLabel{background:transparent;}")
        self.setAccessibleName(f"Ajustes de {_titulo(pista)}")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 16, 14)
        v.setSpacing(10)

        # ---- ritmo
        fila = QHBoxLayout()
        bpm = float((analisis or {}).get("bpm") or 0)
        energia = (analisis or {}).get("energia")
        if bpm:
            texto = f"{bpm:.1f} pulsos por minuto" + (
                f" · energía {int(round(energia * 100))} %" if energia is not None else "")
            if (analisis or {}).get("manual"):
                texto += " · escrito a mano"
        else:
            texto = "Ritmo sin analizar"
        self.et_ritmo = QLabel(texto)
        self.et_ritmo.setStyleSheet("font-size:13px;font-weight:700;")
        self.et_ritmo.setToolTip("Para medir el ritmo hace falta la canción en el disco o conexión; "
                                 "también puedes escribirlo o tocarlo a mano")
        fila.addWidget(self.et_ritmo, 1)
        bt_an = QPushButton("Analizar")
        bt_an.setObjectName("contorno")
        bt_an.setCursor(Qt.PointingHandCursor)
        bt_an.setToolTip("Calcula el ritmo y la energía escuchando la canción")
        bt_an.clicked.connect(lambda: self.analizar.emit(indice))
        bt_es = QPushButton("Escribir o tocar…")
        bt_es.setToolTip("Escribe los pulsos por minuto o tócalos con el dedo al ritmo de la música")
        bt_es.setObjectName("contorno")
        bt_es.setCursor(Qt.PointingHandCursor)
        bt_es.clicked.connect(lambda: self.escribir_ritmo.emit(indice))
        fila.addWidget(bt_an)
        fila.addWidget(bt_es)
        v.addLayout(fila)

        # ---- onda y puntos de entrada y salida
        self.onda = VistaOnda((analisis or {}).get("perfil"), dur, m["entrada"], m["salida"])
        self.onda.cambio.connect(self._de_la_onda)
        v.addWidget(self.onda)
        self.s_entrada, self.e_entrada = self._deslizador(
            v, "Entra en", 0, max(1, dur), int(m["entrada"] or 0),
            lambda n: "Desde el principio" if n == 0 else f"Entra en {formato_tiempo(n)}",
            "Segundo en el que entra esta canción")
        self.s_salida, self.e_salida = self._deslizador(
            v, "Sale en", 0, max(1, dur), int(m["salida"]) if m["salida"] else dur,
            lambda n: "Hasta el final" if n >= self.dur else f"Sale en {formato_tiempo(n)}",
            "Segundo en el que sale esta canción")
        pruebas = QHBoxLayout()
        bt_e = QPushButton("  Probar la entrada")
        bt_e.setObjectName("contorno")
        bt_e.setIcon(iconos.icono("reproducir", 14, C["texto"]))
        bt_e.setCursor(Qt.PointingHandCursor)
        bt_e.clicked.connect(lambda: self.probar_tramo.emit(indice, float(self.s_entrada.value())))
        bt_s = QPushButton("  Probar la salida")
        bt_s.setObjectName("contorno")
        bt_s.setIcon(iconos.icono("reproducir", 14, C["texto"]))
        bt_s.setCursor(Qt.PointingHandCursor)
        bt_s.clicked.connect(lambda: self.probar_tramo.emit(
            indice, max(0.0, float(self.s_salida.value()) - 8.0)))
        pruebas.addWidget(bt_e)
        pruebas.addWidget(bt_s)
        pruebas.addStretch(1)
        v.addLayout(pruebas)

        # ---- ecualizador de 3 bandas
        t = QLabel("Sonido de esta canción en la mezcla")
        t.setStyleSheet(f"color:{C['acento_alto']};font-size:12px;font-weight:800;"
                        "letter-spacing:0.6px;")
        v.addWidget(t)
        self.s_eq = []
        for i, nombre in enumerate(("Graves", "Medios", "Agudos")):
            s, _val = self._deslizador(
                v, nombre, -12, 6, int(round(m["eq"][i])),
                lambda n: f"{n:+d} dB" if n else "Normal", f"{nombre} de esta canción en decibelios")
            self.s_eq.append(s)

    def _deslizador(self, v, texto, minimo, maximo, valor, formato, accesible):
        fila = QHBoxLayout()
        fila.setSpacing(12)
        et = QLabel(texto)
        et.setFixedWidth(110)
        et.setStyleSheet("font-size:13px;font-weight:600;")
        s = QSlider(Qt.Horizontal)
        s.setRange(minimo, maximo)
        s.setValue(max(minimo, min(maximo, valor)))
        s.setAccessibleName(accesible)
        val = QLabel(formato(s.value()))
        val.setFixedWidth(150)
        val.setObjectName("secundario")
        s.valueChanged.connect(lambda n, val=val, formato=formato: (val.setText(formato(n)),
                                                                     self._emitir()))
        fila.addWidget(et)
        fila.addWidget(s, 1)
        fila.addWidget(val)
        v.addLayout(fila)
        return s, val

    def _de_la_onda(self, entrada, salida):
        for s, v, fin in ((self.s_entrada, entrada, False), (self.s_salida, salida, True)):
            if v is None:
                continue
            s.blockSignals(True)
            s.setValue(int(round(v)))
            s.blockSignals(False)
        self.e_entrada.setText("Desde el principio" if self.s_entrada.value() == 0
                               else f"Entra en {formato_tiempo(self.s_entrada.value())}")
        self.e_salida.setText("Hasta el final" if self.s_salida.value() >= self.dur
                              else f"Sale en {formato_tiempo(self.s_salida.value())}")
        self._emitir(desde_onda=True)

    def marcas(self):
        entrada = self.s_entrada.value() or None
        salida = self.s_salida.value() if self.s_salida.value() < self.dur else None
        return md.normalizar_marcas({"entrada": entrada, "salida": salida,
                                     "eq": [s.value() for s in self.s_eq]}, self.dur)

    def _emitir(self, desde_onda=False):
        m = self.marcas()
        if not desde_onda:
            self.onda.poner(m["entrada"], m["salida"])
        self.marcas_cambio.emit(self.clave, m)


# ================================================================ el paso entre dos canciones

_COLORES_ENCAJE = {"encaja": "exito", "ajusta": "aviso", "choca": "error", "desconocido": "texto3"}


def texto_compatibilidad(comp, an_a, an_b):
    """Frase para la etiqueta de colores de un paso."""
    nivel = (comp or {}).get("nivel", "desconocido")
    a, b = float((an_a or {}).get("bpm") or 0), float((an_b or {}).get("bpm") or 0)
    if nivel == "encaja":
        return f"Encajan: {a:.0f} y {b:.0f} pulsos por minuto"
    if nivel == "ajusta":
        return f"Se igualan estirando el tiempo: {a:.0f} y {b:.0f} (±{comp['dif'] * 100:.0f} %)"
    if nivel == "choca":
        return f"Chocan en ritmo: {a:.0f} y {b:.0f}; mejor filtro o corte"
    return "Sin analizar el ritmo: mezcla simple"


class FilaPaso(QFrame):
    """Cómo entra la canción siguiente: tipo de transición, curva, a tempo, cuándo
    entra y cuánto dura."""

    cambio = Signal(int, dict)
    probar = Signal(int)

    def __init__(self, indice, paso, duracion, compat=None, texto_compat="", padre=None):
        super().__init__(padre)
        self.indice = indice
        self.duracion = duracion
        self.paso = md.normalizar_paso(paso, duracion)
        self.setObjectName("paso_mezcla")
        self.setStyleSheet(
            f"QFrame#paso_mezcla{{background:{C['superficie']};border-radius:14px;"
            f"border-left:3px solid {C['acento']};}}"
            "QFrame#paso_mezcla QLabel{background:transparent;}")
        self.setAccessibleName(f"Paso {indice + 1}: cómo entra la siguiente canción")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 12, 16, 12)
        v.setSpacing(8)

        cab = QHBoxLayout()
        t = QLabel("Entrada de la siguiente")
        t.setStyleSheet(f"color:{C['acento_alto']};font-size:12px;font-weight:800;"
                        "letter-spacing:0.6px;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.bt_probar = QPushButton("  Probar este paso")
        self.bt_probar.setObjectName("contorno")
        self.bt_probar.setIcon(iconos.icono("reproducir", 14, C["texto"]))
        self.bt_probar.setCursor(Qt.PointingHandCursor)
        self.bt_probar.setToolTip("Suena solo esta unión: el final de una y el principio de la otra")
        self.bt_probar.clicked.connect(lambda: self.probar.emit(self.indice))
        cab.addWidget(self.bt_probar)
        v.addLayout(cab)

        # encaje de tempos, con color
        nivel = (compat or {}).get("nivel", "desconocido")
        self.et_compat = QLabel(texto_compat or "Sin analizar el ritmo: mezcla simple")
        self.et_compat.setAccessibleName("Encaje de tempos")
        self.et_compat.setStyleSheet(
            f"background:{C[_COLORES_ENCAJE[nivel]]};color:{C['acento_texto'] if nivel != 'desconocido' else C['texto']};"
            "border-radius:9px;padding:4px 10px;font-size:12px;font-weight:700;")
        if nivel == "desconocido":
            self.et_compat.setStyleSheet(
                f"background:{C['superficie3']};color:{C['texto2']};border-radius:9px;"
                "padding:4px 10px;font-size:12px;font-weight:600;")
        fila_c = QHBoxLayout()
        fila_c.addWidget(self.et_compat)
        fila_c.addStretch(1)
        v.addLayout(fila_c)

        # tipo y curva
        opciones = QHBoxLayout()
        opciones.setSpacing(10)
        self.c_tipo = QComboBox()
        for clave, nombre in md.TIPOS:
            self.c_tipo.addItem(nombre, clave)
        self.c_tipo.setCurrentIndex(max(0, self.c_tipo.findData(self.paso["tipo"])))
        self.c_tipo.setAccessibleName("Tipo de transición")
        self.c_curva = QComboBox()
        for clave, nombre in md.CURVAS:
            self.c_curva.addItem("Curva " + nombre.lower(), clave)
        self.c_curva.setCurrentIndex(max(0, self.c_curva.findData(self.paso["curva"])))
        self.c_curva.setAccessibleName("Curva del volumen")
        self.k_tempo = QCheckBox("Igualar el tempo")
        self.k_tempo.setToolTip("La canción que entra se acerca (hasta ±8 %) al ritmo de la que sale "
                                "sin cambiar el tono, y entra en un inicio de compás")
        self.k_tempo.setChecked(self.paso["tempo"])
        self.k_tempo.setCursor(Qt.PointingHandCursor)
        opciones.addWidget(self.c_tipo)
        opciones.addWidget(self.c_curva)
        opciones.addWidget(self.k_tempo)
        opciones.addStretch(1)
        v.addLayout(opciones)
        self.c_tipo.currentIndexChanged.connect(lambda _i: self._emitir())
        self.c_curva.currentIndexChanged.connect(lambda _i: self._emitir())
        self.k_tempo.toggled.connect(lambda _v: self._emitir())

        tope = max(md.DUR_MIN_PASO, min(md.ENTRA_MAX, int(duracion * 0.5))) if duracion else md.ENTRA_MAX
        self.s_entra, self.e_entra = self._deslizador(
            v, "Empieza a entrar", md.DUR_MIN_PASO, tope, self.paso["entra"],
            lambda n: f"{n} s antes del final", "Segundos antes del final en que entra la siguiente")
        self.s_dur, self.e_dur = self._deslizador(
            v, "Dura el fundido", md.DUR_MIN_PASO, md.SEG_MAX, self.paso["dur"],
            lambda n: f"{n} s", "Segundos que dura el fundido")

    def _deslizador(self, v, texto, minimo, maximo, valor, formato, accesible):
        fila = QHBoxLayout()
        fila.setSpacing(12)
        et = QLabel(texto)
        et.setFixedWidth(110)
        et.setStyleSheet("font-size:13px;font-weight:600;")
        s = QSlider(Qt.Horizontal)
        s.setRange(minimo, max(minimo, maximo))
        s.setValue(max(minimo, min(maximo, valor)))
        s.setAccessibleName(accesible)
        val = QLabel(formato(s.value()))
        val.setFixedWidth(120)
        val.setObjectName("secundario")
        s.valueChanged.connect(lambda n, val=val, formato=formato: (val.setText(formato(n)),
                                                                     self._alcambiar(s)))
        fila.addWidget(et)
        fila.addWidget(s, 1)
        fila.addWidget(val)
        v.addLayout(fila)
        s._formato, s._val = formato, val
        return s, val

    def _alcambiar(self, quien):
        # el fundido nunca dura más que lo que falta para que acabe la canción
        if quien is self.s_dur and self.s_dur.value() > self.s_entra.value():
            self.s_entra.setValue(min(self.s_dur.value(), self.s_entra.maximum()))
        elif quien is self.s_entra and self.s_dur.value() > self.s_entra.value():
            self.s_dur.setValue(self.s_entra.value())
        self._emitir()

    def _emitir(self):
        self.paso = md.normalizar_paso(
            {"entra": self.s_entra.value(), "dur": self.s_dur.value(),
             "tipo": self.c_tipo.currentData(), "curva": self.c_curva.currentData(),
             "tempo": self.k_tempo.isChecked()}, self.duracion)
        self.cambio.emit(self.indice, self.paso)


# ================================================================ la página

class PaginaMezclador(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Mezclador"
        self.set_color(QColor(C["acento_bajo"]).darker(320).name())
        self.pistas = []
        self.pasos = []
        self.nombre = ""
        self.marcas = {}             # clave -> {"entrada", "salida", "eq"}
        self.analisis = {}           # clave -> análisis de ritmo (de la caché)
        self._abiertas = set()       # canciones con sus ajustes desplegados
        self._cola_analisis = []     # canciones por analizar, una a una en segundo plano
        self._analizando = None
        self._despues_de_analizar = None
        self._guardar_pronto = QTimer(self)
        self._guardar_pronto.setSingleShot(True)
        self._guardar_pronto.setInterval(450)
        self._guardar_pronto.timeout.connect(self._guardar_borrador)
        self._leer_borrador()
        self._construir()

    # ------------------------------------------------------------ estado

    @property
    def col(self):
        return self.ctx.coleccion

    def _clave(self, p):
        return str(p.get("clave") or "")

    def _leer_borrador(self):
        b = self.col.estado(CLAVE_BORRADOR, None) or {}
        self.pistas = [p for p in (b.get("pistas") or []) if isinstance(p, dict) and p.get("clave")]
        self.pasos = md.pasos_para(self.pistas, b.get("pasos"))
        self.nombre = str(b.get("nombre") or "")
        self.marcas = {k: md.normalizar_marcas(v) for k, v in (b.get("marcas") or {}).items()}
        self._cargar_analisis()

    def _cargar_analisis(self):
        from ... import analisis_audio as aa
        self.analisis = {}
        for p in self.pistas:
            a = aa.analisis_guardado(self.col, p)
            if a:
                self.analisis[self._clave(p)] = a

    def _guardar_borrador(self):
        self.col.guardar_estado(CLAVE_BORRADOR, {
            "nombre": self.campo_nombre.text() if hasattr(self, "campo_nombre") else self.nombre,
            "pistas": [md._pista_minima(p) for p in self.pistas], "pasos": self.pasos,
            "marcas": {k: v for k, v in self.marcas.items() if not md.marcas_vacias(v)}})

    def _marcas_activas(self):
        return {k: v for k, v in self.marcas.items() if not md.marcas_vacias(v)}

    # ------------------------------------------------------------ construcción

    def _construir(self):
        t = QLabel("Mezclador")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        self.cuerpo.addWidget(t)
        sub = QLabel("Arma un set con tus canciones y mézclalo como un DJ: Caudal mide el ritmo, "
                     "las ordena para que encajen, igualas el tempo, eliges cómo entra cada una "
                     "y marcas dónde empieza y acaba.")
        sub.setObjectName("secundario")
        sub.setWordWrap(True)
        self.cuerpo.addWidget(sub)

        barra = QHBoxLayout()
        barra.setSpacing(10)
        self.campo_nombre = QLineEdit(self.nombre)
        self.campo_nombre.setPlaceholderText("Nombre de la mezcla")
        self.campo_nombre.setAccessibleName("Nombre de la mezcla")
        self.campo_nombre.setMaxLength(80)
        self.campo_nombre.setMinimumWidth(220)
        self.campo_nombre.textChanged.connect(lambda _t: self._guardar_pronto.start())
        barra.addWidget(self.campo_nombre, 1)
        self.bt_anadir = QPushButton("  Añadir canciones")
        self.bt_anadir.setObjectName("contorno")
        self.bt_anadir.setIcon(iconos.icono("mas", 16, C["texto"]))
        self.bt_anadir.setCursor(Qt.PointingHandCursor)
        self.bt_anadir.clicked.connect(self._menu_anadir)
        barra.addWidget(self.bt_anadir)
        self.bt_mis = QPushButton("  Mis mezclas")
        self.bt_mis.setObjectName("contorno")
        self.bt_mis.setIcon(iconos.icono("biblioteca", 16, C["texto"]))
        self.bt_mis.setCursor(Qt.PointingHandCursor)
        self.bt_mis.clicked.connect(self._menu_mis)
        barra.addWidget(self.bt_mis)
        self.cuerpo.addLayout(barra)

        acciones = QHBoxLayout()
        acciones.setSpacing(10)
        self.bt_reproducir = QPushButton("  Reproducir el set")
        self.bt_reproducir.setObjectName("principal")
        self.bt_reproducir.setIcon(iconos.icono("reproducir", 16, C["acento_texto"]))
        self.bt_reproducir.setCursor(Qt.PointingHandCursor)
        self.bt_reproducir.clicked.connect(self.reproducir_set)
        acciones.addWidget(self.bt_reproducir)
        self.bt_guardar = QPushButton("  Guardar mezcla")
        self.bt_guardar.setObjectName("contorno")
        self.bt_guardar.setIcon(iconos.icono("listo", 16, C["texto"]))
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.clicked.connect(self.guardar)
        acciones.addWidget(self.bt_guardar)
        self.bt_vaciar = QPushButton("Vaciar mesa")
        self.bt_vaciar.setCursor(Qt.PointingHandCursor)
        self.bt_vaciar.clicked.connect(self.vaciar_mesa)
        acciones.addWidget(self.bt_vaciar)
        acciones.addStretch(1)
        self.cuerpo.addLayout(acciones)

        # ---- el DJ: analizar, ordenar y mezclar solo
        dj = QFrame()
        dj.setObjectName("caja")
        vd = QVBoxLayout(dj)
        vd.setContentsMargins(18, 14, 18, 14)
        vd.setSpacing(8)
        td = QLabel("Mezclar como un DJ")
        td.setStyleSheet("font-size:15px;font-weight:800;")
        vd.addWidget(td)
        ayuda = QLabel("Mide el ritmo de cada canción, las ordena para que el paso sea suave y "
                       "deja cada unión lista según el estilo que elijas.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        vd.addWidget(ayuda)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.c_perfil = QComboBox()
        for clave, (nombre, *_r) in md.PERFILES.items():
            self.c_perfil.addItem(nombre, clave)
        self.c_perfil.setAccessibleName("Estilo de mezcla")
        self.c_perfil.setToolTip("Suave: fundidos largos a tempo · Club: cambio de graves · "
                                 "Rápida: cortes en el compás")
        fila.addWidget(self.c_perfil)
        self.bt_dj = QPushButton("  Mezclar como un DJ")
        self.bt_dj.setObjectName("principal")
        self.bt_dj.setIcon(iconos.icono("album", 16, C["acento_texto"]))
        self.bt_dj.setCursor(Qt.PointingHandCursor)
        self.bt_dj.clicked.connect(lambda: self.mezclar_como_dj())
        fila.addWidget(self.bt_dj)
        self.bt_lista = QPushButton("  Mezclar una lista…")
        self.bt_lista.setObjectName("contorno")
        self.bt_lista.setCursor(Qt.PointingHandCursor)
        self.bt_lista.setToolTip("Trae la cola, Tus me gusta o una lista y la mezcla como un DJ")
        self.bt_lista.clicked.connect(self._menu_mezclar_lista)
        fila.addWidget(self.bt_lista)
        fila.addStretch(1)
        vd.addLayout(fila)
        fila2 = QHBoxLayout()
        fila2.setSpacing(10)
        self.bt_analizar = QPushButton("Analizar el ritmo")
        self.bt_analizar.setObjectName("contorno")
        self.bt_analizar.setCursor(Qt.PointingHandCursor)
        self.bt_analizar.clicked.connect(lambda: self.analizar_todas())
        self.bt_ordenar = QPushButton("Ordenar mi set")
        self.bt_ordenar.setObjectName("contorno")
        self.bt_ordenar.setCursor(Qt.PointingHandCursor)
        self.bt_ordenar.setToolTip("Reordena por tempo y energía: de lo más calmado a lo más fuerte")
        self.bt_ordenar.clicked.connect(self.ordenar)
        fila2.addWidget(self.bt_analizar)
        fila2.addWidget(self.bt_ordenar)
        fila2.addStretch(1)
        vd.addLayout(fila2)
        self.cuerpo.addWidget(dj)

        self.et_resumen = QLabel("")
        self.et_resumen.setObjectName("secundario")
        self.et_resumen.setWordWrap(True)
        self.et_resumen.setAccessibleName("Estado de la mezcla")
        self.cuerpo.addWidget(self.et_resumen)

        self.zona = QWidget()
        self.v_set = QVBoxLayout(self.zona)
        self.v_set.setContentsMargins(0, 0, 0, 0)
        self.v_set.setSpacing(8)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        self._repintar()

    def _texto_resumen(self):
        n = len(self.pistas)
        if not n:
            return ""
        total = md.duracion_del_set(self.pistas, self.pasos)
        con = sum(1 for p in self.pistas if (self.analisis.get(self._clave(p)) or {}).get("bpm"))
        t = (f"{n} {'canción' if n == 1 else 'canciones'} · {formato_tiempo(total)} de música "
             f"mezclada · ritmo medido en {con} de {n}")
        if self._analizando is not None:
            t += f" · analizando «{_titulo(self._analizando)}»…"
        return t

    def _repintar(self):
        _borrar_layout(self.v_set)
        n = len(self.pistas)
        self.bt_reproducir.setEnabled(n >= 2)
        self.bt_guardar.setEnabled(n >= 2)
        self.bt_vaciar.setEnabled(n > 0)
        self.bt_dj.setEnabled(n >= 2)
        self.bt_ordenar.setEnabled(n >= 2)
        self.bt_analizar.setEnabled(n >= 1)
        if n == 0:
            self.v_set.addWidget(SinResultados(
                "album", "Tu mesa está vacía",
                "Añade canciones de lo que suena, de Tus me gusta o de tus listas. "
                "Con dos o más ya puedes mezclar."))
            self.et_resumen.setText("")
            return
        self.et_resumen.setText(self._texto_resumen())
        for i, p in enumerate(self.pistas):
            clave = self._clave(p)
            abierta = clave in self._abiertas
            fila = FilaCancion(i, n, p, self.analisis.get(clave), abierta)
            fila.subir.connect(lambda k: self._mover(k, -1))
            fila.bajar.connect(lambda k: self._mover(k, +1))
            fila.quitar.connect(self._quitar)
            fila.detalle.connect(self._alternar_detalle)
            self.v_set.addWidget(fila)
            if abierta:
                panel = PanelCancion(i, p, self.analisis.get(clave), self.marcas.get(clave))
                panel.marcas_cambio.connect(self._marcas_cambiadas)
                panel.analizar.connect(self._analizar_una)
                panel.escribir_ritmo.connect(self._escribir_ritmo)
                panel.probar_tramo.connect(self._probar_tramo)
                self.v_set.addWidget(panel)
            if i < n - 1:
                comp = md.compatibilidad(self.analisis.get(clave), self.analisis.get(
                    self._clave(self.pistas[i + 1])))
                texto = texto_compatibilidad(comp, self.analisis.get(clave), self.analisis.get(
                    self._clave(self.pistas[i + 1])))
                paso = FilaPaso(i, self.pasos[i], p.get("duracion") or 0, comp, texto)
                paso.cambio.connect(self._paso_cambiado)
                paso.probar.connect(self.probar)
                self.v_set.addWidget(paso)
        if n == 1:
            ayuda = QLabel("Añade al menos una canción más para poder mezclar.")
            ayuda.setObjectName("ayuda")
            self.v_set.addWidget(ayuda)

    # ------------------------------------------------------------ editar el set

    def anadir(self, pistas):
        """Añade canciones al final del set (sin repetir). Devuelve cuántas entraron."""
        ya = {p["clave"] for p in self.pistas}
        nuevas = []
        for p in pistas:
            if p.get("clave") and p["clave"] not in ya:
                ya.add(p["clave"])
                nuevas.append(dict(p))
        sitio = MAX_CANCIONES - len(self.pistas)
        nuevas = nuevas[:max(0, sitio)]
        self.pistas.extend(nuevas)
        self.pasos = md.pasos_para(self.pistas, self.pasos, self.ctx.ajustes["mezcla_dj_seg"],
                                   self.ctx.ajustes["mezcla_dj_graves"])
        self._cargar_analisis()
        self._cambio_en_set()
        return len(nuevas)

    def _mover(self, i, d):
        j = i + d
        if not (0 <= i < len(self.pistas) and 0 <= j < len(self.pistas)):
            return
        self.pistas[i], self.pistas[j] = self.pistas[j], self.pistas[i]
        # la unión entre las dos que se cruzan se conserva; las de los lados son nuevas
        antiguos = list(self.pasos)
        menor = min(i, j)
        if menor > 0:
            antiguos[menor - 1] = None
        if menor + 1 < len(antiguos):
            antiguos[menor + 1] = None
        self.pasos = md.pasos_para(self.pistas, antiguos, self.ctx.ajustes["mezcla_dj_seg"],
                                   self.ctx.ajustes["mezcla_dj_graves"])
        self._cambio_en_set()

    def _quitar(self, i):
        if 0 <= i < len(self.pistas):
            quitada = self.pistas.pop(i)
            self.marcas.pop(self._clave(quitada), None)
            self._abiertas.discard(self._clave(quitada))
            # la unión de las dos canciones que quedan juntas es nueva; las demás se conservan
            if i == 0:
                antiguos = self.pasos[1:]
            else:
                antiguos = self.pasos[:i - 1] + [None] + self.pasos[i + 1:]
            self.pasos = md.pasos_para(self.pistas, antiguos, self.ctx.ajustes["mezcla_dj_seg"],
                                       self.ctx.ajustes["mezcla_dj_graves"])
            self._cambio_en_set()

    def _cambio_en_set(self):
        self._guardar_borrador()
        self._repintar()

    def _paso_cambiado(self, i, paso):
        if 0 <= i < len(self.pasos):
            self.pasos[i] = paso
            self._guardar_pronto.start()
            self.et_resumen.setText(self._texto_resumen())

    def _marcas_cambiadas(self, clave, m):
        self.marcas[clave] = m
        self._guardar_pronto.start()

    def _alternar_detalle(self, i):
        if not (0 <= i < len(self.pistas)):
            return
        clave = self._clave(self.pistas[i])
        if clave in self._abiertas:
            self._abiertas.discard(clave)
        else:
            self._abiertas.add(clave)
        self._repintar()

    def vaciar_mesa(self):
        self.pistas, self.pasos, self.marcas, self.analisis = [], [], {}, {}
        self._abiertas.clear()
        self._cola_analisis = []
        self.campo_nombre.setText("")
        self._cambio_en_set()

    # ------------------------------------------------------------ ritmo: analizar, escribir, ordenar

    def _tras_cambio_de_ritmo(self):
        try:
            self.ctx.reproductor.olvidar_analisis()
        except Exception:  # noqa: BLE001
            pass
        self._cargar_analisis()
        self._repintar()

    def analizar_todas(self, despues=None, forzar=False):
        """Mide el ritmo de las canciones que aún no lo tienen, una a una en segundo plano.
        `despues` se llama al terminar."""
        pendientes = [p for p in self.pistas
                      if forzar or not (self.analisis.get(self._clave(p)) or {}).get("bpm")]
        self._despues_de_analizar = despues
        self._cola_analisis = list(pendientes)
        if not pendientes:
            self._terminar_analisis()
            return
        self._siguiente_analisis()

    def _analizar_una(self, i):
        if 0 <= i < len(self.pistas):
            self._despues_de_analizar = None
            self._cola_analisis = [self.pistas[i]]
            self._siguiente_analisis()

    def _siguiente_analisis(self):
        from ... import analisis_audio as aa
        from ...hilos import en_segundo_plano
        if self._analizando is not None:
            return
        if not self._cola_analisis:
            self._terminar_analisis()
            return
        p = self._cola_analisis.pop(0)
        self._analizando = p
        self.et_resumen.setText(self._texto_resumen())
        fuente = aa.fuente_local(self.col, p)         # toca la colección: aquí, no en el hilo
        en_segundo_plano(aa.analizar_en_hilo, fuente, dict(p), self.ctx.ajustes,
                         ok=lambda datos, p=p: self._analisis_listo(p, datos),
                         error=lambda _e, p=p: self._analisis_listo(p, None), dueno=self)

    def _analisis_listo(self, pista, datos):
        from ... import analisis_audio as aa
        try:
            self._analizando = None
            if datos:
                aa.guardar_analisis(self.col, pista, datos)
                self.analisis[self._clave(pista)] = aa.analisis_guardado(self.col, pista)
            else:
                self._sin_ritmo = getattr(self, "_sin_ritmo", 0) + 1
            self._siguiente_analisis()
        except RuntimeError:
            pass

    def _terminar_analisis(self):
        sin = getattr(self, "_sin_ritmo", 0)
        self._sin_ritmo = 0
        self._tras_cambio_de_ritmo()
        if sin:
            self.ctx.aviso.emit(f"No se pudo medir el ritmo de {sin} "
                                f"{'canción' if sin == 1 else 'canciones'}: puedes escribirlo o "
                                "tocarlo a mano, o descargarla para analizarla")
        despues, self._despues_de_analizar = self._despues_de_analizar, None
        if despues:
            despues()

    def _escribir_ritmo(self, i):
        from ... import analisis_audio as aa
        if not (0 <= i < len(self.pistas)):
            return
        p = self.pistas[i]
        d = DialogoRitmo(_titulo(p), float((self.analisis.get(self._clave(p)) or {}).get("bpm") or 0),
                         self.window())
        if d.exec() == QDialog.Accepted:
            aa.corregir_ritmo(self.col, p, d.bpm())
            self._tras_cambio_de_ritmo()

    def ordenar(self):
        """Reordena por tempo y energía. Si falta medir el ritmo, primero lo mide."""
        if any(not (self.analisis.get(self._clave(p)) or {}).get("bpm") for p in self.pistas):
            self.analizar_todas(despues=self._aplicar_orden)
        else:
            self._aplicar_orden()

    def _aplicar_orden(self):
        antes = [self._clave(p) for p in self.pistas]
        self.pistas = md.ordenar_set(self.pistas, self.analisis)
        self.pasos = md.pasos_para(self.pistas, [], self.ctx.ajustes["mezcla_dj_seg"],
                                   self.ctx.ajustes["mezcla_dj_graves"])
        con = sum(1 for p in self.pistas if (self.analisis.get(self._clave(p)) or {}).get("bpm"))
        cambio = antes != [self._clave(p) for p in self.pistas]
        self._cambio_en_set()
        if con < 2:
            self.ctx.aviso.emit("Hace falta el ritmo de al menos dos canciones para ordenarlas")
        else:
            self.ctx.aviso.emit("Set ordenado por tempo y energía" if cambio
                                else "El set ya estaba bien ordenado")

    def mezclar_como_dj(self, perfil=None):
        """Mide el ritmo, ordena y deja cada paso listo según el estilo elegido."""
        if len(self.pistas) < 2:
            self.ctx.aviso.emit("Añade al menos dos canciones para mezclar")
            return
        self._perfil_pendiente = perfil or self.c_perfil.currentData()
        if any(not (self.analisis.get(self._clave(p)) or {}).get("bpm") for p in self.pistas):
            self.analizar_todas(despues=self._aplicar_dj)
        else:
            self._aplicar_dj()

    def _aplicar_dj(self):
        perfil = getattr(self, "_perfil_pendiente", "suave")
        self.pistas = md.ordenar_set(self.pistas, self.analisis)
        self.pasos = md.pasos_automaticos(self.pistas, self.analisis, perfil)
        sin = [p for p in self.pistas if not (self.analisis.get(self._clave(p)) or {}).get("bpm")]
        a_tempo = sum(1 for p in self.pasos if p["tempo"])
        self._cambio_en_set()
        nombre = md.perfil_mezcla(perfil)[0]
        mensaje = f"Listo, estilo {nombre}: {len(self.pistas)} canciones ordenadas, {a_tempo} " \
                  f"{'unión' if a_tempo == 1 else 'uniones'} a tempo"
        if sin:
            mensaje += f"; {len(sin)} sin ritmo medido se mezclan de forma sencilla"
        self.ctx.aviso.emit(mensaje)

    # ------------------------------------------------------------ de dónde salen las canciones

    def _menu_anadir(self):
        menu = QMenu(self)
        self._llenar_fuentes(menu, lambda titulo, pistas: self._elegir(titulo, pistas))
        menu.exec(self.bt_anadir.mapToGlobal(self.bt_anadir.rect().bottomLeft()))

    def _menu_mezclar_lista(self):
        menu = QMenu(self)
        self._llenar_fuentes(menu, self._traer_y_mezclar)
        menu.exec(self.bt_lista.mapToGlobal(self.bt_lista.rect().bottomLeft()))

    def _llenar_fuentes(self, menu, accion):
        menu.addAction(iconos.icono("cola", 16, C["texto2"]), "De lo que suena y la cola",
                       lambda: accion("Lo que suena y la cola", self._de_la_cola()))
        menu.addAction(iconos.icono("corazon", 16, C["texto2"]), "De Tus me gusta",
                       lambda: accion("Tus me gusta", self.col.lista_me_gusta()))
        listas = self.col.listas()
        if listas:
            sub = menu.addMenu(iconos.icono("lista", 16, C["texto2"]), "De una de tus listas")
            for l in listas[:30]:
                sub.addAction(f"{l['nombre']}  ({l['n']})",
                              lambda _=False, l=l: accion(l["nombre"], self.col.pistas_de_lista(l["id"])))
        else:
            sin = menu.addAction("Aún no tienes listas")
            sin.setEnabled(False)

    def _traer_y_mezclar(self, titulo, pistas):
        """Pone una lista entera (hasta 40 canciones) en la mesa y la mezcla como un DJ."""
        pistas = [p for p in pistas if p.get("clave")][:MAX_CANCIONES]
        if len(pistas) < 2:
            self.ctx.aviso.emit("Esa lista necesita al menos dos canciones")
            return
        self.pistas, self.pasos, self.marcas = [dict(p) for p in pistas], [], {}
        self.pasos = md.pasos_para(self.pistas, [], self.ctx.ajustes["mezcla_dj_seg"],
                                   self.ctx.ajustes["mezcla_dj_graves"])
        self._abiertas.clear()
        if not self.campo_nombre.text().strip():
            self.campo_nombre.setText(f"{titulo} (mezcla)"[:80])
        self._cargar_analisis()
        self._cambio_en_set()
        self.mezclar_como_dj()

    def _de_la_cola(self):
        r = self.ctx.reproductor
        salida, vistos = [], set()
        for p in ([r.actual] if r.actual else []) + list(r.proximas) + \
                list(r.siguientes_de_contexto(60)):
            if p and p.get("clave") and p["clave"] not in vistos:
                vistos.add(p["clave"])
                salida.append(p)
        return salida

    def _elegir(self, titulo, pistas):
        d = ElegirCanciones(titulo, pistas, self.window(), ya={p["clave"] for p in self.pistas})
        if d.exec() == QDialog.Accepted:
            n = self.anadir(d.elegidas())
            self.ctx.aviso.emit(f"{n} {'canción añadida' if n == 1 else 'canciones añadidas'} al set"
                                if n else "No se añadió nada")

    # ------------------------------------------------------------ acciones

    def reproducir_set(self):
        if len(self.pistas) < 2:
            self.ctx.aviso.emit("Añade al menos dos canciones para mezclar")
            return
        nombre = self.campo_nombre.text().strip() or "Mi mezcla"
        self.ctx.reproductor.reproducir_set(self.pistas, self.pasos, nombre,
                                            marcas=self._marcas_activas(), analisis=dict(self.analisis))
        self.ctx.aviso.emit(f"Suena «{nombre}»")

    def probar(self, i):
        if not (0 <= i < len(self.pistas) - 1):
            return
        self.ctx.reproductor.probar_paso(self.pistas[i], self.pistas[i + 1], self.pasos[i],
                                         marcas=self._marcas_activas(), analisis=dict(self.analisis))
        self.ctx.aviso.emit("Probando el paso: suena el final de una y el principio de la otra")

    def _probar_tramo(self, i, desde):
        if 0 <= i < len(self.pistas):
            self.ctx.reproductor.probar_tramo(self.pistas[i], desde, 12.0)
            self.ctx.aviso.emit("Probando el tramo: suenan unos segundos")

    def guardar(self):
        nombre = self.campo_nombre.text().strip()
        if not nombre:
            nombre = md.nombre_libre(self.col)
            self.campo_nombre.setText(nombre)
        existe = any(s["nombre"].lower() == nombre.lower() for s in md.leer_sets(self.col))
        if existe:
            r = QMessageBox.question(
                self.window(), "Caudal",
                f"Ya tienes una mezcla llamada «{nombre}». ¿La reemplazo con esta?")
            if r != QMessageBox.Yes:
                return False
        try:
            md.guardar_set(self.col, nombre, self.pistas, self.pasos, self._marcas_activas())
        except ValueError as e:
            self.ctx.aviso.emit(str(e))
            return False
        self.ctx.aviso.emit(f"Mezcla guardada: «{nombre}»")
        return True

    def abrir_mezcla(self, s):
        self.pistas = [dict(p) for p in s.get("pistas") or []]
        self.pasos = md.pasos_para(self.pistas, s.get("pasos"))
        self.marcas = {k: md.normalizar_marcas(v) for k, v in (s.get("marcas") or {}).items()}
        self._abiertas.clear()
        self.campo_nombre.setText(s.get("nombre") or "")
        self._cargar_analisis()
        self._cambio_en_set()

    def _menu_mis(self):
        sets = md.leer_sets(self.col)
        menu = QMenu(self)
        if not sets:
            sin = menu.addAction("Aún no has guardado ninguna mezcla")
            sin.setEnabled(False)
        for s in sets:
            n = len(s.get("pistas") or [])
            menu.addAction(iconos.icono("album", 16, C["texto2"]),
                           f"{s['nombre']}  ({n} canciones)",
                           lambda _=False, s=s: self.abrir_mezcla(s))
        if sets:
            menu.addSeparator()
            borrar = menu.addMenu(iconos.icono("papelera", 16, C["texto2"]), "Borrar una mezcla")
            for s in sets:
                borrar.addAction(s["nombre"], lambda _=False, s=s: self._borrar(s["nombre"]))
        menu.exec(self.bt_mis.mapToGlobal(self.bt_mis.rect().bottomLeft()))

    def _borrar(self, nombre):
        r = QMessageBox.question(self.window(), "Caudal",
                                 f"¿Borrar la mezcla «{nombre}»? Las canciones no se tocan.")
        if r == QMessageBox.Yes:
            md.borrar_set(self.col, nombre)
            self.ctx.aviso.emit(f"Mezcla borrada: «{nombre}»")
