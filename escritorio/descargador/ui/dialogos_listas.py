# -*- coding: utf-8 -*-
"""Ventanas de las listas: «Añadir a una lista» (varias a la vez), «Compartir lista»,
«Tengo un código» y «Enviar una lista» desde un chat.

Son delgadas: la lógica (códigos, permisos, mensajes, pasos de compartir) vive en
`descargador/listas_compartidas.py`. Todo lo que toca internet va en segundo plano.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from .. import listas_compartidas as LC
from ..hilos import en_segundo_plano
from . import iconos
from .componentes import _borrar_layout
from .estilos import C, hoja


def _explicar(e, que="hacer eso"):
    from .contexto import explicar_error
    return explicar_error(e, que)


class _Base(QDialog):
    """Ventana con el aspecto de Caudal (fondo, tipografía y botones del resto de la app)."""

    def __init__(self, titulo, ancho=480, alto=0, padre=None):
        super().__init__(padre)
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle(titulo + " · Caudal")
        self.setMinimumWidth(ancho)
        if alto:
            self.setMinimumHeight(alto)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(26, 22, 26, 20)
        self.v.setSpacing(12)

    def titulo(self, texto, sub=""):
        t = QLabel(texto)
        t.setStyleSheet("font-size:21px;font-weight:900;background:transparent;")
        t.setWordWrap(True)
        self.v.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setObjectName("ayuda")
            s.setWordWrap(True)
            self.v.addWidget(s)

    def aviso_estado(self):
        """La línea de estado (cargando, errores): siempre ocupa su sitio, nada salta."""
        self.estado = QLabel("")
        self.estado.setWordWrap(True)
        self.estado.setObjectName("ayuda")
        self.estado.setMinimumHeight(22)
        self.v.addWidget(self.estado)

    def decir(self, texto, error=False):
        self.estado.setStyleSheet(f"color:{C['error'] if error else C['texto2']};font-size:12.5px;"
                                  "background:transparent;")
        self.estado.setText(texto)


def _boton(texto, objeto="contorno", icono=None, color=None):
    b = QPushButton(("  " + texto) if icono else texto)
    b.setObjectName(objeto)
    b.setCursor(Qt.PointingHandCursor)
    if icono:
        b.setIcon(iconos.icono(icono, 16, color or C["texto"]))
    return b


def _zona_desplazable(minimo=160):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
    area.viewport().setAutoFillBackground(False)
    area.setMinimumHeight(minimo)
    interior = QWidget()
    interior.setObjectName("interior_dialogo")
    interior.setStyleSheet("QWidget#interior_dialogo{background:transparent;}")
    lay = QVBoxLayout(interior)
    lay.setContentsMargins(0, 0, 6, 0)
    lay.setSpacing(4)
    lay.addStretch(1)
    area.setWidget(interior)
    return area, lay


def _fila_estilo(activa=False):
    fondo = C["superficie3"] if activa else "transparent"
    return (f"QPushButton{{text-align:left;border:none;border-radius:12px;padding:0 4px;background:{fondo};}}"
            f"QPushButton:hover{{background:{C['superficie2']};}}"
            f"QPushButton:focus{{border:1px solid {C['acento']};}}")


# ======================================================================= añadir a una lista


class DialogoAnadirALista(_Base):
    """Elegir una o varias listas para guardar canciones. Abre al instante (todo sale de la base de
    esta PC): la última lista usada arriba, buscador cuando hay muchas, crear una nueva sin salir."""

    MUCHAS = 8

    def __init__(self, ctx, pistas, padre=None):
        super().__init__("Añadir a una lista", 460, 520, padre)
        self.ctx = ctx
        self.pistas = pistas
        self.ids = []                  # listas mías elegidas, en el orden en que se eligieron
        self.compartidas = []          # listas compartidas donde puedo añadir
        self._marcadas = {}
        n = len(pistas)
        sub = (pistas[0].get("titulo") or "esta canción") if n == 1 else f"{n} canciones"
        self.titulo("Añadir a una lista", sub)
        col = ctx.coleccion
        self.listas = col.listas()
        ultima = col.estado("ultima_lista")
        self.listas.sort(key=lambda l: l["id"] != ultima)
        self.ultima = ultima
        self.compartibles = self._compartidas_conocidas()

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar una lista")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.addAction(iconos.icono("lupa", 16, C["texto2"]), QLineEdit.LeadingPosition)
        self.buscador.textChanged.connect(self._pintar)
        self.buscador.setVisible(len(self.listas) + len(self.compartibles) > self.MUCHAS)
        self.v.addWidget(self.buscador)

        self.area, self.lay = _zona_desplazable(220)
        self.v.addWidget(self.area, 1)

        nueva = QHBoxLayout()
        nueva.setSpacing(8)
        self.nombre_nuevo = QLineEdit()
        self.nombre_nuevo.setPlaceholderText("O crea una lista nueva aquí")
        self.nombre_nuevo.returnPressed.connect(self._crear)
        nueva.addWidget(self.nombre_nuevo, 1)
        self.bt_crear = _boton("Crear", "contorno", "mas")
        self.bt_crear.clicked.connect(self._crear)
        nueva.addWidget(self.bt_crear)
        self.v.addLayout(nueva)
        self.aviso_estado()

        fila = QHBoxLayout()
        fila.addStretch(1)
        cancelar = _boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        fila.addWidget(cancelar)
        self.bt_listo = _boton("Listo", "principal")
        self.bt_listo.setDefault(True)
        self.bt_listo.clicked.connect(self._listo)
        fila.addWidget(self.bt_listo)
        self.v.addLayout(fila)
        self._pintar()
        self._actualizar_boton()
        if not self.listas and not self.compartibles:
            self.nombre_nuevo.setFocus()
        else:
            self.buscador.setFocus() if self.buscador.isVisible() else self.area.setFocus()
        self._traer_compartidas()

    # ---- listas compartidas donde se puede añadir (las ya conocidas salen al instante)
    def _compartidas_conocidas(self):
        datos = LC.ultima_conocida("mis_compartidas") or LC.compartidas_guardadas(self.ctx.coleccion)
        return [x for x in datos if x.get("rol") == "colaborador"]

    def _traer_compartidas(self):
        from .contexto import nube_de
        nube = nube_de(self.ctx)
        if nube is None or LC.en_cache("mis_compartidas", 30) is not None:
            return

        def listo(filas):
            LC.guardar_cache("mis_compartidas", filas)
            LC.guardar_compartidas(self.ctx.coleccion, filas)
            nuevas = [x for x in filas if x.get("rol") == "colaborador"]
            if [x["id"] for x in nuevas] != [x["id"] for x in self.compartibles]:
                self.compartibles = nuevas
                self._pintar()
        en_segundo_plano(nube.mis_compartidas, ok=listo, error=lambda _e: None, dueno=self)

    def _pintar(self, *_):
        _borrar_layout(self.lay)
        q = self.buscador.text().strip().lower()
        ver = [l for l in self.listas if not q or q in l["nombre"].lower()]
        for l in ver:
            self.lay.addWidget(self._fila(("l", l["id"]), l["nombre"],
                                          f"{l['n']} {'canción' if l['n'] == 1 else 'canciones'}"
                                          + ("  ·  la última que usaste" if l["id"] == self.ultima else ""),
                                          "lista"))
        comp = [c for c in self.compartibles if not q or q in c["nombre"].lower()]
        if comp:
            t = QLabel("Listas compartidas")
            t.setStyleSheet(f"color:{C['texto2']};font-weight:800;font-size:12px;margin-top:8px;"
                            "background:transparent;")
            self.lay.addWidget(t)
            for c in comp:
                self.lay.addWidget(self._fila(("c", c["id"]), c["nombre"],
                                              f"Compartida · {LC.nombre_persona(c['dueno'])}", "compartir", c))
        if not ver and not comp:
            et = QLabel("Todavía no tienes listas. Escribe un nombre abajo y créala."
                        if not self.listas else f"Ninguna lista se llama «{self.buscador.text().strip()}».")
            et.setObjectName("ayuda")
            et.setWordWrap(True)
            self.lay.addWidget(et)
        self.lay.addStretch(1)

    def _fila(self, clave, nombre, detalle, icono, datos=None):
        marcada = clave in self._marcadas
        b = QPushButton()
        b.setCheckable(True)
        b.setChecked(marcada)
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(54)
        b.setStyleSheet(_fila_estilo(marcada))
        h = QHBoxLayout(b)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(iconos.pixmap(icono, 22, C["acento"] if marcada else C["texto2"]))
        h.addWidget(ic)
        col = QVBoxLayout()
        col.setSpacing(0)
        n = QLabel(nombre)
        n.setStyleSheet("font-weight:700;background:transparent;")
        d = QLabel(detalle)
        d.setStyleSheet(f"color:{C['texto3']};font-size:11.5px;background:transparent;")
        col.addWidget(n)
        col.addWidget(d)
        h.addLayout(col, 1)
        marca = QLabel()
        marca.setPixmap(iconos.pixmap("check_circulo" if marcada else "mas_circulo", 22,
                                      C["acento"] if marcada else C["texto3"]))
        h.addWidget(marca)
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False, k=clave, x=datos: self._alternar(k, x))
        return b

    def _alternar(self, clave, datos=None):
        if clave in self._marcadas:
            del self._marcadas[clave]
        else:
            self._marcadas[clave] = datos
        barra = self.area.verticalScrollBar().value()
        self._pintar()
        self.area.verticalScrollBar().setValue(barra)
        self._actualizar_boton()

    def _actualizar_boton(self):
        n = len(self._marcadas)
        self.bt_listo.setEnabled(n > 0)
        self.bt_listo.setText(f"Listo ({n})" if n > 1 else "Listo")

    def _crear(self):
        nombre = self.nombre_nuevo.text().strip()
        if not nombre:
            return
        try:
            lid = self.ctx.coleccion.crear_lista(nombre)
        except ValueError as e:
            self.decir(str(e), True)
            return
        self.listas = self.ctx.coleccion.listas()
        self.listas.sort(key=lambda l: l["id"] != lid)
        self.nombre_nuevo.clear()
        self.buscador.clear()
        self._marcadas[("l", lid)] = None
        self.ctx.listas_cambio.emit()
        self.decir(f"Lista «{nombre}» creada y marcada.")
        self._pintar()
        self._actualizar_boton()

    def _listo(self):
        self.ids = [k[1] for k in self._marcadas if k[0] == "l"]
        self.compartidas = [d for k, d in self._marcadas.items() if k[0] == "c"]
        self.accept()


# ======================================================================= compartir una lista mía


class DialogoCompartir(_Base):
    """Compartir una lista propia: permiso, código con guion, copiar código/mensaje/enlace,
    enviar por el chat, miembros y dejar de compartir."""

    def __init__(self, ctx, lista_id, padre=None):
        super().__init__("Compartir lista", 500, 0, padre)
        from .contexto import nube_de
        self.ctx = ctx
        self.lista_id = lista_id
        self.nube = nube_de(ctx)
        self.col = ctx.coleccion
        self.lista = self.col.lista(lista_id) or {}
        self.codigo = ""
        self.rol = LC.POR_DEFECTO
        self.ocupado = False
        self.titulo(f"Compartir «{self.lista.get('nombre', '')}»",
                    "Quien tenga el código puede abrir tu lista en Caudal. Tú decides si también puede añadir canciones.")
        self.aviso_estado()

        # permiso
        self.fila_permiso = QWidget()
        hp = QHBoxLayout(self.fila_permiso)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.setSpacing(8)
        self.grupo = QButtonGroup(self)
        self.bt_colab = _boton("Pueden añadir canciones")
        self.bt_oyente = _boton("Solo escuchar")
        for b, r in ((self.bt_colab, "colaborador"), (self.bt_oyente, "oyente")):
            b.setCheckable(True)
            b.setProperty("rol", r)
            self.grupo.addButton(b)
            hp.addWidget(b)
            b.clicked.connect(lambda _=False, r=r: self._cambiar_rol(r))
        self.grupo.setExclusive(True)
        self.bt_colab.setChecked(True)
        self.v.addWidget(self.fila_permiso)
        self.et_permiso = QLabel("")
        self.et_permiso.setObjectName("ayuda")
        self.et_permiso.setWordWrap(True)
        self.v.addWidget(self.et_permiso)

        # el código
        self.caja_codigo = QFrame()
        self.caja_codigo.setObjectName("caja_codigo")
        self.caja_codigo.setStyleSheet(f"QFrame#caja_codigo{{background:{C['superficie2']};border-radius:16px;}}")
        vc = QVBoxLayout(self.caja_codigo)
        vc.setContentsMargins(18, 14, 18, 14)
        vc.setSpacing(2)
        et = QLabel("Código de la lista")
        et.setStyleSheet(f"color:{C['texto2']};font-size:12px;background:transparent;")
        vc.addWidget(et)
        self.et_codigo = QLabel("········")
        self.et_codigo.setAlignment(Qt.AlignCenter)
        self.et_codigo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.et_codigo.setStyleSheet(f"font-size:36px;font-weight:900;letter-spacing:5px;color:{C['acento']};"
                                     "background:transparent;")
        vc.addWidget(self.et_codigo)
        self.et_enlace = QLabel("")
        self.et_enlace.setAlignment(Qt.AlignCenter)
        self.et_enlace.setStyleSheet(f"color:{C['texto3']};font-size:11.5px;background:transparent;")
        self.et_enlace.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vc.addWidget(self.et_enlace)
        self.v.addWidget(self.caja_codigo)

        # botones
        f1 = QHBoxLayout()
        f1.setSpacing(8)
        self.bt_copiar_codigo = _boton("Copiar código", "principal", "enlace", C["acento_texto"])
        self.bt_copiar_codigo.clicked.connect(self._copiar_codigo)
        self.bt_copiar_mensaje = _boton("Copiar mensaje", "contorno", "compartir")
        self.bt_copiar_mensaje.clicked.connect(self._copiar_mensaje)
        f1.addWidget(self.bt_copiar_codigo)
        f1.addWidget(self.bt_copiar_mensaje)
        self.v.addLayout(f1)
        f2 = QHBoxLayout()
        f2.setSpacing(8)
        self.bt_copiar_enlace = _boton("Copiar enlace", "contorno", "enlace")
        self.bt_copiar_enlace.clicked.connect(self._copiar_enlace)
        self.bt_chat = _boton("Enviar por el chat", "contorno", "chat")
        self.bt_chat.clicked.connect(self._enviar_por_chat)
        f2.addWidget(self.bt_copiar_enlace)
        f2.addWidget(self.bt_chat)
        self.v.addLayout(f2)

        # compartir por primera vez
        self.bt_empezar = _boton("Compartir con un código", "principal", "compartir", C["acento_texto"])
        self.bt_empezar.clicked.connect(lambda: self._compartir(self.rol))
        self.v.addWidget(self.bt_empezar)

        # miembros
        self.et_miembros = QLabel("Quién está en la lista")
        self.et_miembros.setStyleSheet("font-size:14px;font-weight:800;margin-top:8px;background:transparent;")
        self.v.addWidget(self.et_miembros)
        self.zona_miembros = QVBoxLayout()
        self.zona_miembros.setSpacing(2)
        self.v.addLayout(self.zona_miembros)

        pie = QHBoxLayout()
        self.bt_dejar = _boton("Dejar de compartir", "contorno", "cerrar", C["error"])
        self.bt_dejar.clicked.connect(self._dejar)
        pie.addWidget(self.bt_dejar)
        pie.addStretch(1)
        cerrar = _boton("Cerrar", "principal")
        cerrar.clicked.connect(self.accept)
        pie.addWidget(cerrar)
        self.v.addLayout(pie)

        if self.nube is None:
            self._mostrar("sin_red")
            return
        self._mostrar("cargando")
        u = self.col._uuid_lista(lista_id)
        g = LC.codigos_guardados(self.col).get(u)
        if g:                                  # lo último que se sabía, al instante
            self.rol = g["rol"]
            self.codigo = g["codigo"]
            self._mostrar("compartida")
        en_segundo_plano(self._averiguar, ok=self._llego, error=self._fallo, dueno=self, urgente=True)

    # ---- estados
    def _mostrar(self, estado):
        comp = estado == "compartida"
        for w in (self.caja_codigo, self.bt_copiar_codigo, self.bt_copiar_mensaje, self.bt_copiar_enlace,
                  self.bt_chat, self.bt_dejar, self.et_miembros, self.fila_permiso):
            w.setVisible(comp)
        self.et_permiso.setVisible(estado in ("compartida", "privada"))
        self.bt_empezar.setVisible(estado == "privada")
        self.fila_permiso.setVisible(estado in ("compartida", "privada"))
        if estado == "cargando":
            self.decir("Un momento…")
        elif estado == "sin_red":
            self.decir("Compartir necesita una cuenta de Caudal con internet. Vuelve a abrir Caudal con conexión.", True)
        elif estado == "privada":
            self.decir("Esta lista es privada: solo tú la ves.")
        else:
            self.decir("")
        if comp:
            self.et_codigo.setText(LC.con_guion(self.codigo))
            self.et_enlace.setText(LC.enlace(self.codigo))
        self._marcar_rol()

    def _marcar_rol(self):
        (self.bt_colab if self.rol == "colaborador" else self.bt_oyente).setChecked(True)
        self.et_permiso.setText(LC.frase_permiso(self.rol))

    def _averiguar(self):
        u = self.col._uuid_lista(self.lista_id)
        self._subir_pendientes()
        return LC.estado_de_mi_lista(self.col, self.nube, u)

    def _subir_pendientes(self):
        s = getattr(self.ctx, "sincronizador", None)
        if s is not None:
            s.enviar_ahora()

    def _llego(self, estado):
        if estado:
            self.codigo, self.rol = estado["codigo"], estado["rol"]
            self._mostrar("compartida")
            self._cargar_miembros()
        else:
            self.codigo = ""
            self._mostrar("privada")

    def _fallo(self, e):
        self.ocupado = False
        if self.codigo:
            self.decir(_explicar(e, "comprobar el código"), True)
        else:
            self._mostrar("privada")
            self.decir(_explicar(e, "comprobar la lista"), True)

    # ---- acciones
    def _compartir(self, rol):
        if self.ocupado:
            return
        self.ocupado = True
        self.decir("Compartiendo la lista…")
        en_segundo_plano(LC.compartir_mi_lista, self.col, self.nube, self.lista_id, rol,
                         self._subir_pendientes, ok=self._compartida, error=self._fallo, dueno=self, urgente=True)

    def _compartida(self, r):
        self.ocupado = False
        self.codigo, self.rol = r["codigo"], r["rol"]
        self._mostrar("compartida")
        self.decir("Listo: la lista está compartida.")
        self.ctx.listas_cambio.emit()
        self._cargar_miembros()

    def _cambiar_rol(self, rol):
        if rol == self.rol:
            return
        previo = self.rol
        self.rol = rol
        self.et_permiso.setText(LC.frase_permiso(rol))
        if self.codigo:
            self._compartir(rol)
        else:
            self.rol = rol if previo != rol else previo

    def _copiar(self, texto, aviso):
        QGuiApplication.clipboard().setText(texto)
        self.decir(aviso)
        self.ctx.aviso.emit(aviso)

    def _copiar_codigo(self):
        self._copiar(LC.con_guion(self.codigo), "Código copiado")

    def _copiar_mensaje(self):
        self._copiar(LC.mensaje_compartir(self.lista.get("nombre", ""), self.codigo), "Mensaje copiado: ya puedes pegarlo")

    def _copiar_enlace(self):
        self._copiar(LC.enlace(self.codigo), "Enlace copiado")

    def _enviar_por_chat(self):
        from .paginas.mensajes import enviar_lista_a_chat
        n = sum(1 for p in self.col.pistas_de_lista(self.lista_id) if str(p.get("clave", "")).startswith("yt:"))
        tarjeta = LC.tarjeta_para_chat(self.codigo, self.lista.get("nombre", ""), n, self.rol,
                                       LC._portada_web(self.col, self.lista_id))
        self.hide()
        enviar_lista_a_chat(self.ctx, tarjeta)
        self.accept()

    def _dejar(self):
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(self, "Dejar de compartir",
                                 "El código dejará de servir y las personas que ya estaban dentro saldrán de la lista. "
                                 "Tus canciones no se tocan. ¿Dejar de compartir?")
        if r != QMessageBox.Yes:
            return
        self.decir("Un momento…")
        en_segundo_plano(LC.dejar_de_compartir_mi_lista, self.col, self.nube, self.lista_id,
                         self._subir_pendientes, ok=self._ya_no, error=self._fallo, dueno=self, urgente=True)

    def _ya_no(self, _r):
        self.codigo = ""
        self._mostrar("privada")
        self.decir("Dejaste de compartir la lista.")
        self.ctx.listas_cambio.emit()
        _borrar_layout(self.zona_miembros)

    # ---- miembros
    def _cargar_miembros(self):
        u = self.col._uuid_lista(self.lista_id)
        en_segundo_plano(self.nube.miembros, u, ok=self._pintar_miembros, error=lambda _e: None, dueno=self)

    def _pintar_miembros(self, miembros):
        from .paginas.perfil_comun import Avatar
        _borrar_layout(self.zona_miembros)
        otros = [m for m in miembros if not m["es_dueno"]]
        self.et_miembros.setText(f"Quién está en la lista ({len(miembros)})" if otros
                                 else "Quién está en la lista")
        if not otros:
            et = QLabel("Todavía nadie más: cuando alguien escriba el código aparecerá aquí.")
            et.setObjectName("ayuda")
            et.setWordWrap(True)
            self.zona_miembros.addWidget(et)
        for m in miembros:
            fila = QHBoxLayout()
            fila.setSpacing(10)
            fila.addWidget(Avatar(34, LC.nombre_persona(m), C["acento"], m.get("foto_url"),
                                  marco=m.get("marco")))
            nombre = LC.nombre_persona(m) + ("  ·  tú, dueño" if m["es_dueno"] else "")
            n = QLabel(f"<b>{nombre}</b><br><span style='color:{C['texto3']};font-size:11px'>@{m['usuario']}</span>")
            n.setStyleSheet("background:transparent;")
            fila.addWidget(n, 1)
            if not m["es_dueno"]:
                q = _boton("Quitar", "contorno")
                q.clicked.connect(lambda _=False, m=m: self._quitar(m))
                fila.addWidget(q)
            cont = QWidget()
            cont.setLayout(fila)
            self.zona_miembros.addWidget(cont)

    def _quitar(self, m):
        u = self.col._uuid_lista(self.lista_id)
        en_segundo_plano(self.nube.quitar_miembro, u, m["id"], ok=lambda _r: self._cargar_miembros(),
                         error=lambda e: self.decir(_explicar(e, "quitar a esa persona"), True), dueno=self)


def compartir_lista(ctx, lista_id, padre=None):
    d = DialogoCompartir(ctx, lista_id, padre or getattr(ctx, "ventana", None))
    d.exec()
    return d


# ======================================================================= tengo un código


class DialogoTengoCodigo(_Base):
    """Escribir o pegar un código (o el enlace): vista previa y «Unirme»."""

    def __init__(self, ctx, codigo="", padre=None):
        super().__init__("Tengo un código", 480, 0, padre)
        from .contexto import nube_de
        self.ctx = ctx
        self.nube = nube_de(ctx)
        self.vista = None
        self.codigo = ""
        self.resultado = None
        self.titulo("Tengo un código", "Escribe el código de la lista que te pasaron (o pega el enlace). "
                                       "No importa si lo pones en minúsculas o sin el guion.")
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("K7M2-9QXP")
        self.campo.setStyleSheet("font-size:20px;font-weight:800;letter-spacing:3px;padding:8px 12px;")
        self.campo.textChanged.connect(self._al_escribir)
        self.campo.returnPressed.connect(self._ver)
        fila.addWidget(self.campo, 1)
        pegar = _boton("Pegar", "contorno", "pegar")
        pegar.clicked.connect(lambda: self.campo.setText(QGuiApplication.clipboard().text().strip()))
        fila.addWidget(pegar)
        self.v.addLayout(fila)
        self.aviso_estado()

        self.tarjeta = QFrame()
        self.tarjeta.setObjectName("tarjeta_lista")
        self.tarjeta.setStyleSheet(f"QFrame#tarjeta_lista{{background:{C['superficie2']};border-radius:16px;}}")
        vt = QVBoxLayout(self.tarjeta)
        vt.setContentsMargins(18, 14, 18, 14)
        vt.setSpacing(4)
        self.t_nombre = QLabel("")
        self.t_nombre.setStyleSheet("font-size:18px;font-weight:900;background:transparent;")
        self.t_nombre.setWordWrap(True)
        self.t_sub = QLabel("")
        self.t_sub.setStyleSheet(f"color:{C['texto2']};background:transparent;")
        self.t_sub.setWordWrap(True)
        self.t_canciones = QLabel("")
        self.t_canciones.setStyleSheet(f"color:{C['texto3']};font-size:12px;background:transparent;")
        self.t_canciones.setWordWrap(True)
        self.t_permiso = QLabel("")
        self.t_permiso.setStyleSheet(f"color:{C['acento']};font-weight:700;background:transparent;")
        self.t_permiso.setWordWrap(True)
        for w in (self.t_nombre, self.t_sub, self.t_canciones, self.t_permiso):
            vt.addWidget(w)
        self.tarjeta.hide()
        self.v.addWidget(self.tarjeta)

        pie = QHBoxLayout()
        pie.addStretch(1)
        cancelar = _boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        pie.addWidget(cancelar)
        self.bt_unirme = _boton("Unirme a la lista", "principal", "compartir", C["acento_texto"])
        self.bt_unirme.setEnabled(False)
        self.bt_unirme.clicked.connect(self._unirme)
        pie.addWidget(self.bt_unirme)
        self.v.addLayout(pie)
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(350)
        self._temporizador.timeout.connect(self._ver)
        if self.nube is None:
            self.decir("Las listas compartidas necesitan una cuenta de Caudal con internet.", True)
            self.campo.setEnabled(False)
        elif codigo:
            self.campo.setText(codigo)
        else:
            self.campo.setFocus()

    def _al_escribir(self, texto):
        c = LC.extraer_codigo(texto)
        self.bt_unirme.setEnabled(False)
        self.tarjeta.hide()
        self.vista = None
        if c:
            self.codigo = c
            self._temporizador.start()
        elif texto.strip():
            self.decir("Un código tiene 8 letras y números, como K7M2-9QXP.")
        else:
            self.decir("")

    def _ver(self):
        c = LC.extraer_codigo(self.campo.text())
        if not c or self.nube is None:
            return
        self.codigo = c
        self.decir("Buscando la lista…")
        en_segundo_plano(self.nube.ver_codigo, c, ok=lambda v, c=c: self._vista(c, v),
                         error=lambda e: self.decir(_explicar(e, "buscar la lista"), True),
                         dueno=self, urgente=True)

    def _vista(self, codigo, v):
        if codigo != self.codigo:
            return
        if v is None:
            self.decir("Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.", True)
            return
        self.vista = v
        self.decir("")
        self.t_nombre.setText(v["nombre"])
        quien = LC.nombre_persona(v["dueno"])
        self.t_sub.setText(f"De {quien}  ·  {v['total']} {'canción' if v['total'] == 1 else 'canciones'}"
                           f"  ·  {v['miembros'] + 1} {'persona' if v['miembros'] == 0 else 'personas'}")
        self.t_canciones.setText("\n".join(f"♪ {c['titulo']}" + (f" — {c['artista']}" if c["artista"] else "")
                                           for c in v["canciones"]) or "Todavía no tiene canciones.")
        self.t_permiso.setText(("Colaborativa: " if v["rol"] == "colaborador" else "Solo escuchar: ")
                               + ("podrás añadir canciones." if v["rol"] == "colaborador"
                                  else "podrás escucharla, pero no añadir canciones."))
        self.tarjeta.show()
        self.bt_unirme.setEnabled(True)
        self.bt_unirme.setDefault(True)

    def _unirme(self):
        self.bt_unirme.setEnabled(False)
        self.decir("Uniéndote a la lista…")
        en_segundo_plano(self.nube.unirse, self.codigo, ok=self._unido,
                         error=lambda e: (self.decir(_explicar(e, "unirte a la lista"), True),
                                          self.bt_unirme.setEnabled(True)), dueno=self, urgente=True)

    def _unido(self, r):
        self.resultado = dict(r, codigo=self.codigo, vista=self.vista)
        LC.recordar_union(self.ctx.coleccion, self.codigo, r["lista_id"])
        LC._CACHE.pop("mis_compartidas", None)
        self.accept()


def tengo_un_codigo(ctx, codigo="", padre=None):
    """Abre «Tengo un código»; al unirse, lleva a la lista."""
    d = DialogoTengoCodigo(ctx, codigo, padre or getattr(ctx, "ventana", None))
    if d.exec() and d.resultado:
        abrir_lista_unida(ctx, d.resultado)


def abrir_lista_unida(ctx, r):
    """Tras unirse (o al pulsar «Abrir» en una tarjeta del chat)."""
    ctx.listas_cambio.emit()
    if r.get("es_dueno"):
        mia = ctx.coleccion.lista_por_uuid(r["lista_id"])
        if mia:
            ctx.navegar({"pagina": "mi_lista", "id": mia["id"]})
            return
    v = r.get("vista") or {}
    ctx.aviso.emit(f"Te uniste a «{r['nombre']}»")
    ctx.navegar({"pagina": "lista_compartida", "id": r["lista_id"],
                 "el": {"tipo": "lista_compartida", "id": r["lista_id"], "titulo": r["nombre"],
                        "rol": r["rol"], "dueno": v.get("dueno") or {}}})


# ======================================================================= enviar una lista desde el chat


class DialogoEnviarLista(_Base):
    """«Enviar una lista» dentro de un chat: elige una de tus listas; si aún no está compartida se
    comparte sola (por defecto, «Pueden añadir canciones»). Al aceptar, `tarjeta` trae lo que va en el mensaje."""

    def __init__(self, ctx, destinatario="", padre=None):
        super().__init__("Enviar una lista", 480, 540, padre)
        from .contexto import nube_de
        self.ctx = ctx
        self.col = ctx.coleccion
        self.nube = nube_de(ctx)
        self.tarjeta = None
        self.elegida = None
        self.rol = LC.POR_DEFECTO
        self.titulo("Enviar una lista" + (f" a {destinatario}" if destinatario else ""),
                    "Elige una de tus listas. Se comparte con un código y le llega como una tarjeta con botón «Unirme».")
        self.codigos = LC.codigos_guardados(self.col)
        self.listas = [l for l in self.col.listas() if self._es_enviable(l)]
        self.area, self.lay = _zona_desplazable(200)
        self.v.addWidget(self.area, 1)

        self.fila_rol = QWidget()
        hr = QHBoxLayout(self.fila_rol)
        hr.setContentsMargins(0, 0, 0, 0)
        hr.setSpacing(8)
        self.grupo = QButtonGroup(self)
        self.bt_colab = _boton("Colaborativa")
        self.bt_oyente = _boton("Solo escuchar")
        for b, r in ((self.bt_colab, "colaborador"), (self.bt_oyente, "oyente")):
            b.setCheckable(True)
            self.grupo.addButton(b)
            hr.addWidget(b)
            b.clicked.connect(lambda _=False, r=r: self._poner_rol(r))
        self.bt_colab.setChecked(True)
        self.v.addWidget(self.fila_rol)
        self.et_permiso = QLabel("")
        self.et_permiso.setObjectName("ayuda")
        self.et_permiso.setWordWrap(True)
        self.v.addWidget(self.et_permiso)
        self.aviso_estado()

        pie = QHBoxLayout()
        pie.addStretch(1)
        cancelar = _boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        pie.addWidget(cancelar)
        self.bt_enviar = _boton("Enviar la lista", "principal", "compartir", C["acento_texto"])
        self.bt_enviar.setEnabled(False)
        self.bt_enviar.clicked.connect(self._enviar)
        pie.addWidget(self.bt_enviar)
        self.v.addLayout(pie)
        self._pintar()
        self._actualizar()
        if self.nube is None:
            self.decir("Para enviar una lista hace falta una cuenta de Caudal con internet.", True)
            self.bt_enviar.setEnabled(False)

    def _es_enviable(self, l):
        return True

    def _compartida(self, l):
        u = l.get("uuid")
        return self.codigos.get(u) if u else None

    def _pintar(self):
        _borrar_layout(self.lay)
        for l in self.listas:
            g = self._compartida(l)
            detalle = f"{l['n']} {'canción' if l['n'] == 1 else 'canciones'}"
            if g:
                detalle += f"  ·  Compartida · {LC.etiqueta_rol(g['rol'])}"
            sel = self.elegida == l["id"]
            b = QPushButton()
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(54)
            b.setStyleSheet(_fila_estilo(sel))
            h = QHBoxLayout(b)
            h.setContentsMargins(12, 6, 12, 6)
            h.setSpacing(12)
            ic = QLabel()
            ic.setPixmap(iconos.pixmap("lista", 22, C["acento"] if sel else C["texto2"]))
            h.addWidget(ic)
            col = QVBoxLayout()
            col.setSpacing(0)
            n = QLabel(l["nombre"])
            n.setStyleSheet("font-weight:700;background:transparent;")
            d = QLabel(detalle)
            d.setStyleSheet(f"color:{C['texto3']};font-size:11.5px;background:transparent;")
            col.addWidget(n)
            col.addWidget(d)
            h.addLayout(col, 1)
            if sel:
                m = QLabel()
                m.setPixmap(iconos.pixmap("check_circulo", 22, C["acento"]))
                h.addWidget(m)
            for w in b.findChildren(QLabel):
                w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            b.clicked.connect(lambda _=False, i=l["id"]: self._elegir(i))
            self.lay.addWidget(b)
        if not self.listas:
            et = QLabel("Todavía no tienes listas. Crea una desde «Tu biblioteca» y vuelve.")
            et.setObjectName("ayuda")
            et.setWordWrap(True)
            self.lay.addWidget(et)
        self.lay.addStretch(1)

    def _elegir(self, lista_id):
        self.elegida = lista_id
        l = self.col.lista(lista_id) or {}
        g = self._compartida(l)
        if g:
            self.rol = g["rol"]
        self._pintar()
        self._actualizar()

    def _poner_rol(self, rol):
        self.rol = rol
        self._actualizar()

    def _actualizar(self):
        l = (self.col.lista(self.elegida) or {}) if self.elegida else {}
        g = self._compartida(l) if l else None
        (self.bt_colab if self.rol == "colaborador" else self.bt_oyente).setChecked(True)
        self.fila_rol.setEnabled(not g)
        if not self.elegida:
            self.et_permiso.setText("Elige una lista. Después podrás decidir si se pueden añadir canciones.")
        elif g:
            self.et_permiso.setText(f"Esta lista ya está compartida como «{LC.etiqueta_rol(g['rol'])}»: "
                                    "se usa el mismo código. " + LC.frase_permiso(g["rol"]))
        else:
            self.et_permiso.setText("Se compartirá como «" + LC.etiqueta_rol(self.rol) + "». "
                                    + LC.frase_permiso(self.rol))
        self.bt_enviar.setEnabled(bool(self.elegida) and self.nube is not None)

    def _enviar(self):
        if not self.elegida:
            return
        self.bt_enviar.setEnabled(False)
        self.decir("Preparando la lista…")
        s = getattr(self.ctx, "sincronizador", None)
        l = self.col.lista(self.elegida) or {}
        rol = None if self._compartida(l) else self.rol
        en_segundo_plano(LC.preparar_lista_para_chat, self.col, self.nube, self.elegida, rol,
                         (s.enviar_ahora if s is not None else None),
                         ok=self._listo, error=self._fallo, dueno=self, urgente=True)

    def _listo(self, r):
        self.tarjeta = r["tarjeta"]
        self.frase = r["frase"]
        self.ctx.listas_cambio.emit()
        self.accept()

    def _fallo(self, e):
        self.decir(_explicar(e, "preparar la lista"), True)
        self.bt_enviar.setEnabled(True)
