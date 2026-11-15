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

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QSlider, QVBoxLayout, QWidget)

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


# ================================================================ una canción del set

class FilaCancion(QFrame):
    subir = Signal(int)
    bajar = Signal(int)
    quitar = Signal(int)

    def __init__(self, indice, total, pista, padre=None):
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
        a = QLabel(_artista(pista))
        a.setObjectName("secundario")
        v.addWidget(t)
        v.addWidget(a)
        h.addLayout(v, 1)
        d = QLabel(formato_tiempo(pista.get("duracion")))
        d.setObjectName("secundario")
        h.addWidget(d)
        b_arriba = _boton_plano("chevron_arriba", "Subir esta canción", lambda: self.subir.emit(indice))
        b_arriba.setEnabled(indice > 0)
        b_abajo = _boton_plano("chevron_abajo", "Bajar esta canción", lambda: self.bajar.emit(indice))
        b_abajo.setEnabled(indice < total - 1)
        b_quitar = _boton_plano("cerrar", "Quitar del set", lambda: self.quitar.emit(indice))
        for b in (b_arriba, b_abajo, b_quitar):
            h.addWidget(b)


# ================================================================ el paso entre dos canciones

class FilaPaso(QFrame):
    """Cómo entra la canción siguiente: cuándo, cuánto dura y si cambia los graves."""

    cambio = Signal(int, dict)
    probar = Signal(int)

    def __init__(self, indice, paso, duracion, padre=None):
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

        tope = max(md.DUR_MIN_PASO, min(md.ENTRA_MAX, int(duracion * 0.5))) if duracion else md.ENTRA_MAX
        self.s_entra, self.e_entra = self._deslizador(
            v, "Empieza a entrar", md.DUR_MIN_PASO, tope, self.paso["entra"],
            lambda n: f"{n} s antes del final", "Segundos antes del final en que entra la siguiente")
        self.s_dur, self.e_dur = self._deslizador(
            v, "Dura el fundido", md.DUR_MIN_PASO, md.SEG_MAX, self.paso["dur"],
            lambda n: f"{n} s", "Segundos que dura el fundido")
        self.graves = QCheckBox("Cambio de graves")
        self.graves.setToolTip("Los bajos de una canción ceden el sitio a los de la otra, "
                               "para que no se pisen")
        self.graves.setChecked(self.paso["graves"])
        self.graves.setCursor(Qt.PointingHandCursor)
        self.graves.toggled.connect(lambda _v: self._emitir())
        v.addWidget(self.graves)

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
        self.paso = md.normalizar_paso({"entra": self.s_entra.value(), "dur": self.s_dur.value(),
                                        "graves": self.graves.isChecked()}, self.duracion)
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
        self._leer_borrador()
        self._construir()

    # ------------------------------------------------------------ estado

    @property
    def col(self):
        return self.ctx.coleccion

    def _leer_borrador(self):
        b = self.col.estado(CLAVE_BORRADOR, None) or {}
        self.pistas = [p for p in (b.get("pistas") or []) if isinstance(p, dict) and p.get("clave")]
        self.pasos = md.pasos_para(self.pistas, b.get("pasos"))
        self.nombre = str(b.get("nombre") or "")

    def _guardar_borrador(self):
        self.col.guardar_estado(CLAVE_BORRADOR, {
            "nombre": self.campo_nombre.text() if hasattr(self, "campo_nombre") else self.nombre,
            "pistas": [md._pista_minima(p) for p in self.pistas], "pasos": self.pasos})

    # ------------------------------------------------------------ construcción

    def _construir(self):
        t = QLabel("Mezclador")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        self.cuerpo.addWidget(t)
        sub = QLabel("Arma un set con tus canciones y ajusta, paso a paso, cómo se enlaza cada "
                     "una con la siguiente: cuándo entra, cuánto dura el fundido y si cambian los "
                     "graves.")
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
        self.campo_nombre.textChanged.connect(lambda _t: self._guardar_borrador())
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
        self.et_resumen = QLabel("")
        self.et_resumen.setObjectName("secundario")
        self.et_resumen.setWordWrap(True)
        self.cuerpo.addWidget(self.et_resumen)

        self.zona = QWidget()
        self.v_set = QVBoxLayout(self.zona)
        self.v_set.setContentsMargins(0, 0, 0, 0)
        self.v_set.setSpacing(8)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        self._repintar()

    def _repintar(self):
        _borrar_layout(self.v_set)
        n = len(self.pistas)
        self.bt_reproducir.setEnabled(n >= 2)
        self.bt_guardar.setEnabled(n >= 2)
        self.bt_vaciar.setEnabled(n > 0)
        if n == 0:
            self.v_set.addWidget(SinResultados(
                "album", "Tu mesa está vacía",
                "Añade canciones de lo que suena, de Tus me gusta o de tus listas. "
                "Con dos o más ya puedes mezclar."))
            self.et_resumen.setText("")
            return
        total = md.duracion_del_set(self.pistas, self.pasos)
        self.et_resumen.setText(f"{n} {'canción' if n == 1 else 'canciones'} · "
                                f"{formato_tiempo(total)} de música mezclada")
        for i, p in enumerate(self.pistas):
            fila = FilaCancion(i, n, p)
            fila.subir.connect(lambda k: self._mover(k, -1))
            fila.bajar.connect(lambda k: self._mover(k, +1))
            fila.quitar.connect(self._quitar)
            self.v_set.addWidget(fila)
            if i < n - 1:
                paso = FilaPaso(i, self.pasos[i], p.get("duracion") or 0)
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
            del self.pistas[i]
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
            self._guardar_borrador()
            total = md.duracion_del_set(self.pistas, self.pasos)
            self.et_resumen.setText(f"{len(self.pistas)} canciones · "
                                    f"{formato_tiempo(total)} de música mezclada")

    def vaciar_mesa(self):
        self.pistas, self.pasos = [], []
        self.campo_nombre.setText("")
        self._cambio_en_set()

    # ------------------------------------------------------------ de dónde salen las canciones

    def _menu_anadir(self):
        r = self.ctx.reproductor
        menu = QMenu(self)
        menu.addAction(iconos.icono("cola", 16, C["texto2"]), "De lo que suena y la cola",
                       lambda: self._elegir("Lo que suena y la cola", self._de_la_cola()))
        menu.addAction(iconos.icono("corazon", 16, C["texto2"]), "De Tus me gusta",
                       lambda: self._elegir("Tus me gusta", self.col.lista_me_gusta()))
        listas = self.col.listas()
        if listas:
            sub = menu.addMenu(iconos.icono("lista", 16, C["texto2"]), "De una de tus listas")
            for l in listas[:30]:
                sub.addAction(f"{l['nombre']}  ({l['n']})",
                              lambda _=False, l=l: self._elegir(
                                  l["nombre"], self.col.pistas_de_lista(l["id"])))
        else:
            sin = menu.addAction("Aún no tienes listas")
            sin.setEnabled(False)
        del r
        menu.exec(self.bt_anadir.mapToGlobal(self.bt_anadir.rect().bottomLeft()))

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
        self.ctx.reproductor.reproducir_set(self.pistas, self.pasos, nombre)
        self.ctx.aviso.emit(f"Suena «{nombre}»")

    def probar(self, i):
        if not (0 <= i < len(self.pistas) - 1):
            return
        self.ctx.reproductor.probar_paso(self.pistas[i], self.pistas[i + 1], self.pasos[i])
        self.ctx.aviso.emit("Probando el paso: suena el final de una y el principio de la otra")

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
            md.guardar_set(self.col, nombre, self.pistas, self.pasos)
        except ValueError as e:
            self.ctx.aviso.emit(str(e))
            return False
        self.ctx.aviso.emit(f"Mezcla guardada: «{nombre}»")
        return True

    def abrir_mezcla(self, s):
        self.pistas = [dict(p) for p in s.get("pistas") or []]
        self.pasos = md.pasos_para(self.pistas, s.get("pasos"))
        self.campo_nombre.setText(s.get("nombre") or "")
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
