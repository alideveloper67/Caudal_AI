# -*- coding: utf-8 -*-
"""Ajustes › «Personalizar»: marco animado para tu foto, efecto para tu nombre y tema de colores.

Arriba una vista previa en vivo (tu foto con el marco, tu nombre con el efecto y una Caudal en miniatura
con el tema); debajo, tres rejillas para elegir. Es exclusivo de donadores y fundadores (o de quien tenga un
pase de prueba): para el resto se puede probar cómo queda, pero «Aplicar» está bloqueado y salen los botones
«Donar aquí» y «Tengo un código de prueba». Igual que la app del teléfono."""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from ..premium_datos import (EFECTOS, MARCOS, NINGUNO, NOMBRES_EFECTO, NOMBRES_MARCO, NOMBRES_TEMA, PALETA_NOMBRE,
                             TEMAS, color_valido, nombre_de_color, texto_vencimiento)
from .. import social as S
from .aspecto import Muestra
from .canje_pase import boton_codigo
from .donar import boton_donar
from .estilos import ACTUAL, C, acento_de, fondo_de
from .paginas import perfil_comun as PC
from .premium_estilos import NombreEfecto, pintar_marco

COLUMNAS = 4
WEB_CAUDAL = "https://caudal-musica.netlify.app"


def texto_para_compartir(codigo):
    """El mensaje que el donador le manda a su amigo, con el código y la web."""
    return (f"Te regalo una prueba de Caudal, mi app de música: 7 días con todos los beneficios de donador.\n"
            f"1) Descárgala en {WEB_CAUDAL}\n"
            f"2) Abre Ajustes › Personalizar › «Tengo un código de prueba»\n"
            f"3) Escribe este código: {codigo}\n"
            f"Sirve una sola vez.")


def estado_de_regalo(pase):
    """'sin_usar' | 'usado' | 'caducado' para un código de mis_pases_regalo()."""
    if pase.get("usado"):
        return "usado"
    return "sin_usar" if pase.get("vigente") else "caducado"


ETIQUETA_REGALO = {"sin_usar": "Sin usar", "usado": "Usado", "caducado": "Caducado"}


def icono_marco(marco, lado=44):
    """Una muestra quieta del marco (la rejilla no anima nada: solo la vista previa)."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    if marco == NINGUNO:
        p.setPen(QPen(QColor(C["texto3"]), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(3, 3, lado - 6, lado - 6))
    else:
        pintar_marco(p, QRectF(1, 1, lado - 2, lado - 2), marco, ancho=6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"]))
        p.drawEllipse(QRectF(9, 9, lado - 18, lado - 18))
    p.end()
    return pm


def icono_color(color, lado=26):
    """Un círculo del color del nombre (o con una raya si es «Sin color»)."""
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    r = QRectF(2, 2, lado - 4, lado - 4)
    if color:
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(QColor(color))
        p.drawEllipse(r)
    else:
        p.setPen(QPen(QColor(C["texto3"]), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(r)
        p.drawLine(int(r.left() + 4), int(r.bottom() - 4), int(r.right() - 4), int(r.top() + 4))
    p.end()
    return pm


def icono_tema(tema, ancho=64, alto=40):
    """Tres franjas con los colores del tema: fondo, panel y acento."""
    pm = QPixmap(ancho, alto)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    if tema == NINGUNO:
        f, ac = fondo_de("oscuro"), acento_de("cian")
    else:
        f, ac = fondo_de("premium_" + tema), acento_de("premium_" + tema)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(f[1]))
    p.drawRoundedRect(QRectF(0, 0, ancho, alto), 8, 8)
    p.setBrush(QColor(f[2]))
    p.drawRoundedRect(QRectF(5, 5, ancho * 0.42, alto - 10), 5, 5)
    p.setBrush(QColor(f[4]))
    p.drawRoundedRect(QRectF(ancho * 0.42 + 10, 5, ancho * 0.58 - 15, alto * 0.42), 5, 5)
    p.setBrush(QColor(ac[1]))
    p.drawRoundedRect(QRectF(ancho * 0.42 + 10, alto * 0.42 + 10, ancho * 0.3, alto * 0.22), 4, 4)
    p.end()
    return pm


class TarjetaRegalo(QFrame):
    """«Regala una prueba a tus amigos»: crea códigos de un solo uso (7 días de beneficios), los lista con su
    estado y deja copiarlos, anularlos o compartirlos con un texto listo. Solo se ve para donadores y
    fundadores (quien solo tiene una prueba no puede regalar). Todo va en segundo plano."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.gestor = getattr(ctx, "premium", None)
        self.pases = []
        self._cargado = False
        self._ocupado = False
        # va dentro de la tarjeta Personalizar: un fondo suave (como la vista previa), sin otra caja con borde
        self.setObjectName("tarjeta_regalo")
        self.setStyleSheet(f"QFrame#tarjeta_regalo{{background:{C['superficie']};border-radius:14px;}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(10)
        t = QLabel("Regala una prueba a tus amigos")
        t.setStyleSheet("font-size:16px;font-weight:800;background:transparent;")
        v.addWidget(t)
        ayuda = QLabel("Crea un código y pásaselo a un amigo: tendrá 7 días de beneficios de donador. Cada código "
                       "sirve una sola vez y vale 30 días para canjearlo. Puedes tener 3 sin usar a la vez.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)
        fila = QHBoxLayout()
        self.bt_crear = QPushButton("Crear un código")
        self.bt_crear.setCursor(Qt.PointingHandCursor)
        self.bt_crear.clicked.connect(self._crear)
        fila.addWidget(self.bt_crear)
        self.msg = QLabel("")
        self.msg.setObjectName("secundario")
        self.msg.setWordWrap(True)
        fila.addWidget(self.msg, 1)
        v.addLayout(fila)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(6)
        v.addLayout(self.lista)
        # el texto para compartir (del último código sin usar), listo para copiar
        self.caja_texto = QWidget()
        c = QVBoxLayout(self.caja_texto)
        c.setContentsMargins(0, 4, 0, 0)
        c.setSpacing(6)
        et = QLabel("Para mandárselo a tu amigo")
        et.setStyleSheet("font-size:13px;font-weight:800;")
        c.addWidget(et)
        self.texto = QLabel("")
        self.texto.setWordWrap(True)
        self.texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.texto.setStyleSheet(f"background:{C['superficie2']};border-radius:10px;padding:10px 12px;")
        c.addWidget(self.texto)
        self.bt_copiar_texto = QPushButton("Copiar el mensaje")
        self.bt_copiar_texto.setObjectName("contorno")
        self.bt_copiar_texto.setCursor(Qt.PointingHandCursor)
        self.bt_copiar_texto.clicked.connect(self._copiar_texto)
        c.addWidget(self.bt_copiar_texto, 0, Qt.AlignLeft)
        v.addWidget(self.caja_texto)
        if self.gestor is not None:
            self.gestor.cambiado.connect(self.refrescar)
        self.refrescar()

    # ------------------------------------------------------------ quién la ve
    def refrescar(self):
        puede = bool(self.gestor is not None and self.gestor.puede_regalar)
        self.setVisible(puede)
        if puede and not self._cargado:
            self._cargado = True
            self.recargar()
        self._pintar()

    def recargar(self):
        if self.gestor is None:
            return
        self.gestor.mis_regalos(ok=self._llegaron, error=self._fallo_lista, dueno=self)

    def _llegaron(self, lista):
        self.pases = [p for p in (lista or []) if isinstance(p, dict) and p.get("codigo")]
        self._pintar()

    def _fallo_lista(self, e):
        self._cargado = False                    # se vuelve a intentar la próxima vez que se muestre
        self.msg.setText(S.explicar(e, "leer tus códigos"))

    # ------------------------------------------------------------ pintar
    def _pintar(self):
        while self.lista.count():
            it = self.lista.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
            elif it.layout() is not None:
                self._borrar_fila(it.layout())
        sin_usar = None
        for p in self.pases:
            self.lista.addLayout(self._fila(p))
            if sin_usar is None and estado_de_regalo(p) == "sin_usar":
                sin_usar = p["codigo"]
        self.caja_texto.setVisible(sin_usar is not None)
        self.texto.setText(texto_para_compartir(sin_usar) if sin_usar else "")
        self.bt_crear.setEnabled(not self._ocupado)

    @staticmethod
    def _borrar_fila(lay):
        while lay.count():
            it = lay.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()

    def _fila(self, pase):
        codigo, estado = pase["codigo"], estado_de_regalo(pase)
        h = QHBoxLayout()
        h.setSpacing(10)
        c = QLabel(codigo)
        c.setStyleSheet("font-size:16px;font-weight:800;letter-spacing:1px;")
        c.setTextInteractionFlags(Qt.TextSelectableByMouse)
        c.setMinimumWidth(110)
        h.addWidget(c)
        e = QLabel(ETIQUETA_REGALO[estado])
        e.setObjectName("secundario")
        if estado == "sin_usar":
            e.setStyleSheet(f"color:{C['acento']};font-weight:700;")
        h.addWidget(e, 1)
        if estado != "usado":
            if estado == "sin_usar":
                b = QPushButton("Copiar")
                b.setObjectName("contorno")
                b.setCursor(Qt.PointingHandCursor)
                b.setAccessibleName(f"Copiar el código {codigo}")
                b.clicked.connect(lambda _=False, cod=codigo: self._copiar(cod))
                h.addWidget(b)
            a = QPushButton("Anular")
            a.setObjectName("contorno")
            a.setCursor(Qt.PointingHandCursor)
            a.setAccessibleName(f"Anular el código {codigo}")
            a.clicked.connect(lambda _=False, cod=codigo: self._anular(cod))
            h.addWidget(a)
        return h

    # ------------------------------------------------------------ acciones
    def _copiar(self, codigo):
        QGuiApplication.clipboard().setText(codigo)
        self.msg.setText(f"Copiado: {codigo}")

    def _copiar_texto(self):
        QGuiApplication.clipboard().setText(self.texto.text())
        self.msg.setText("Mensaje copiado. Pégalo donde le escribas a tu amigo.")

    def _crear(self):
        if self.gestor is None or self._ocupado:
            return
        self._ocupado = True
        self.bt_crear.setEnabled(False)
        self.msg.setText("Creando tu código…")
        self.gestor.crear_regalo(ok=self._creado, error=self._fallo_accion, dueno=self)

    def _creado(self, res):
        self._ocupado = False
        if res.get("ok") and res.get("codigo"):
            self.msg.setText(f"Listo: {res['codigo']}. Ya puedes mandárselo a tu amigo.")
            self._cargado = True
            self.recargar()
        else:
            self.msg.setText(res.get("mensaje") or "No se pudo crear el código. Vuelve a intentarlo.")
        self._pintar()

    def _anular(self, codigo):
        if self.gestor is None or self._ocupado:
            return
        self._ocupado = True
        self.msg.setText("Anulando…")
        self.gestor.anular_regalo(codigo, ok=lambda hecho, c=codigo: self._anulado(c, hecho),
                                  error=self._fallo_accion, dueno=self)

    def _anulado(self, codigo, hecho):
        self._ocupado = False
        self.msg.setText(f"Anulado: {codigo}" if hecho else "Ese código ya no se puede anular (alguien lo usó).")
        self.recargar()
        self._pintar()

    def _fallo_accion(self, e):
        self._ocupado = False
        self.msg.setText(S.explicar(e, "hacerlo"))
        self._pintar()


class SeccionPersonalizar(QFrame):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.gestor = getattr(ctx, "premium", None)
        self.setObjectName("caja")
        g = self.gestor
        self.sel = {"marco": g.marco if g else NINGUNO, "efecto": g.efecto if g else NINGUNO,
                    "tema": g.tema if g else NINGUNO}
        self.sel_color = g.color_nombre if g else None      # el color del nombre (aparte: no es una clave del marco)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(12)

        cab = QHBoxLayout()
        t = QLabel("Personalizar")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        cab.addWidget(t)
        cab.addStretch(1)
        self.estado = QLabel("")
        self.estado.setObjectName("secundario")
        cab.addWidget(self.estado)
        v.addLayout(cab)
        ayuda = QLabel("Un marco animado para tu foto, un efecto y un color para tu nombre y un tema de colores "
                       "propio. Lo ven también tus amigos.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)

        # bloqueo amable para quien aún no es donador
        self.caja_bloqueo = QWidget()
        h = QHBoxLayout(self.caja_bloqueo)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.aviso = QLabel("🔒 Exclusivo para donadores. Puedes probar cómo queda; para aplicarlo, apoya a "
                            "Caudal o canjea un código de prueba.")
        self.aviso.setObjectName("ayuda")
        self.aviso.setWordWrap(True)
        h.addWidget(self.aviso, 1)
        self.bt_donar = boton_donar(texto="Donar aquí")
        h.addWidget(self.bt_donar)
        self.bt_codigo = boton_codigo(ctx, texto="Tengo un código de prueba")
        h.addWidget(self.bt_codigo)
        v.addWidget(self.caja_bloqueo)

        # vista previa en vivo
        prev = QFrame()
        prev.setStyleSheet(f"QFrame{{background:{C['superficie']};border-radius:14px;}}")
        ph = QHBoxLayout(prev)
        ph.setContentsMargins(16, 14, 16, 14)
        ph.setSpacing(16)
        cuenta = getattr(ctx, "cuenta", None) or {}
        nombre = (cuenta.get("nombre") or cuenta.get("usuario") or "Tu nombre")
        self.avatar = PC.Avatar(88, nombre, None, None, marco=self.sel["marco"], marco_siempre=True)
        ph.addWidget(self.avatar, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.nombre = NombreEfecto(nombre, self.sel["efecto"], "font-size:24px;font-weight:900;", siempre=True)
        col.addStretch(1)
        col.addWidget(self.nombre)
        usuario = QLabel("@" + str(cuenta.get("usuario") or "tu_usuario"))
        usuario.setObjectName("secundario")
        usuario.setStyleSheet("background:transparent;")
        col.addWidget(usuario)
        col.addStretch(1)
        ph.addLayout(col, 1)
        self.muestra = Muestra()
        self.muestra.setMinimumSize(190, 118)
        self.muestra.setMaximumSize(230, 140)
        ph.addWidget(self.muestra, 0, Qt.AlignVCenter)
        v.addWidget(prev)

        self.botones = {"marco": {}, "efecto": {}, "tema": {}}
        self._rejilla(v, "Marco de la foto", "marco", MARCOS, NOMBRES_MARCO, lambda k: QIcon(icono_marco(k)),
                      QSize(44, 44))
        self._rejilla(v, "Efecto del nombre", "efecto", EFECTOS, NOMBRES_EFECTO, None, QSize(1, 1))
        self._fila_colores(v)
        self._rejilla(v, "Tema de colores", "tema", TEMAS, NOMBRES_TEMA, lambda k: QIcon(icono_tema(k)),
                      QSize(64, 40))

        fila = QHBoxLayout()
        self.bt_aplicar = QPushButton("Aplicar")
        self.bt_aplicar.clicked.connect(self._aplicar)
        fila.addWidget(self.bt_aplicar)
        self.bt_quitar = QPushButton("Quitar todo")
        self.bt_quitar.setObjectName("contorno")
        self.bt_quitar.clicked.connect(self._quitar_todo)
        fila.addWidget(self.bt_quitar)
        self.msg = QLabel("")
        self.msg.setObjectName("secundario")
        self.msg.setWordWrap(True)
        fila.addWidget(self.msg, 1)
        v.addLayout(fila)

        # regalar pruebas: solo se ve para donadores y fundadores
        self.tarjeta_regalo = TarjetaRegalo(ctx)
        v.addWidget(self.tarjeta_regalo)

        if g is not None:
            g.cambiado.connect(self.refrescar)
        self._marcar()
        self.refrescar()

    # ------------------------------------------------------------ rejillas
    def _rejilla(self, v, titulo, clave, valores, nombres, icono, tam):
        et = QLabel(titulo)
        et.setStyleSheet("font-size:13px;font-weight:800;")
        v.addWidget(et)
        rej = QGridLayout()
        rej.setSpacing(8)
        for i, valor in enumerate(valores):
            b = QToolButton()
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon if icono else Qt.ToolButtonTextOnly)
            b.setText(nombres[valor])
            b.setToolTip(nombres[valor])
            b.setAccessibleName(f"{titulo}: {nombres[valor]}")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setMinimumSize(96, 78 if icono else 40)
            if icono is not None:
                b.setIcon(icono(valor))
                b.setIconSize(tam)
            b.setStyleSheet(
                f"QToolButton{{background:rgba(255,255,255,0.05);border:2px solid transparent;border-radius:12px;"
                f"color:{C['texto']};font-size:11.5px;padding:4px 2px;}}"
                f"QToolButton:hover{{background:rgba(255,255,255,0.10);}}"
                f"QToolButton:checked{{border:2px solid {C['acento']};background:rgba(255,255,255,0.12);}}")
            b.clicked.connect(lambda _=False, c=clave, val=valor: self._elegir(c, val))
            self.botones[clave][valor] = b
            rej.addWidget(b, i // COLUMNAS, i % COLUMNAS)
        for c in range(COLUMNAS):
            rej.setColumnStretch(c, 1)
        v.addLayout(rej)

    def _fila_colores(self, v):
        """«Color del nombre»: la paleta, «Sin color» y «Personalizado…» (un color cualquiera)."""
        et = QLabel("Color del nombre")
        et.setStyleSheet("font-size:13px;font-weight:800;")
        v.addWidget(et)
        sub = QLabel("Se ve en tu perfil, en los chats y en «Juntos». Con «Brillo» el destello pasa sobre tu color.")
        sub.setObjectName("secundario")
        sub.setWordWrap(True)
        v.addWidget(sub)
        fila = QGridLayout()
        fila.setSpacing(6)
        por_fila = 5                     # en dos filas: cabe en ventanas chicas
        self.botones_color = {}
        estilo = (f"QToolButton{{background:rgba(255,255,255,0.05);border:2px solid transparent;border-radius:12px;"
                  f"color:{C['texto']};font-size:11px;padding:4px 6px;}}"
                  f"QToolButton:hover{{background:rgba(255,255,255,0.10);}}"
                  f"QToolButton:checked{{border:2px solid {C['acento']};background:rgba(255,255,255,0.12);}}")
        opciones = [("Sin color", None)] + list(PALETA_NOMBRE)
        for nombre, hexa in opciones:
            b = QToolButton()
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(QIcon(icono_color(hexa)))
            b.setIconSize(QSize(26, 26))
            b.setToolTip(nombre)
            b.setAccessibleName(f"Color del nombre: {nombre}")
            b.setStyleSheet(estilo)
            b.clicked.connect(lambda _=False, c=hexa: self._elegir_color(c))
            self.botones_color[hexa] = b
            i = len(self.botones_color) - 1
            fila.addWidget(b, i // por_fila, i % por_fila)
        self.bt_color_propio = QToolButton()
        self.bt_color_propio.setCheckable(True)
        self.bt_color_propio.setCursor(Qt.PointingHandCursor)
        self.bt_color_propio.setText("Personalizado…")
        self.bt_color_propio.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.bt_color_propio.setIconSize(QSize(20, 20))
        self.bt_color_propio.setAccessibleName("Color del nombre: elegir uno personalizado")
        self.bt_color_propio.setStyleSheet(estilo)
        self.bt_color_propio.clicked.connect(self._color_propio)
        fila.addWidget(self.bt_color_propio, 2, 0, 1, por_fila, Qt.AlignLeft)
        fila.setColumnStretch(por_fila, 1)
        v.addLayout(fila)

    def _color_propio(self):
        actual = QColor(self.sel_color or C["acento"])
        c = QColorDialog.getColor(actual, self, "Color de tu nombre")
        if c.isValid():
            self._elegir_color(c.name().upper())
        else:
            self._marcar()

    def _elegir_color(self, color):
        self.sel_color = color_valido(color)
        self.msg.setText("")
        self._marcar()

    def _elegir(self, clave, valor):
        self.sel[clave] = valor
        self.msg.setText("")
        self._marcar()

    def _marcar(self):
        """Pinta lo elegido: marca los botones y mueve la vista previa."""
        for clave, d in self.botones.items():
            for valor, b in d.items():
                b.setChecked(valor == self.sel[clave])
        self.avatar.set_marco(self.sel["marco"])
        self.nombre.set_efecto(self.sel["efecto"])
        color = color_valido(self.sel_color)
        for hexa, b in self.botones_color.items():
            b.setChecked(hexa == color)
        propio = color is not None and color not in self.botones_color
        self.bt_color_propio.setChecked(propio)
        self.bt_color_propio.setIcon(QIcon(icono_color(color, 20)) if propio else QIcon())
        self.bt_color_propio.setToolTip(f"Personalizado: {color}" if propio else "Elegir cualquier color")
        self.nombre.set_color(color)
        self.nombre.setAccessibleDescription(f"Color: {nombre_de_color(color)}")
        t = self.sel["tema"]
        if t == NINGUNO:
            self.muestra.poner(ACTUAL.get("acento", "cian") if not str(ACTUAL.get("acento", "")).startswith("premium_")
                               else "cian",
                               ACTUAL.get("fondo", "oscuro") if not str(ACTUAL.get("fondo", "")).startswith("premium_")
                               else "oscuro")
        else:
            self.muestra.poner("premium_" + t, "premium_" + t)

    # ------------------------------------------------------------ estado
    def refrescar(self):
        g = self.gestor
        premium = bool(g and g.premium)
        self.caja_bloqueo.setVisible(not premium)
        self.bt_aplicar.setEnabled(premium)
        self.bt_quitar.setEnabled(premium)
        if not premium:
            self.estado.setText("🔒 Exclusivo")
        elif g.tipo == "prueba":
            self.estado.setText(texto_vencimiento(g.dias_de_prueba()))
        else:
            self.estado.setText("Fundador de Caudal" if g.tipo == "fundador" else "Donador de Caudal")

    def _aplicar(self):
        g = self.gestor
        if g is None or not g.premium:
            return
        cambia_tema = g.guardar_personalizacion(self.sel["marco"], self.sel["efecto"], self.sel["tema"],
                                                alerta=self._alerta)
        color = color_valido(self.sel_color)
        if color != g.color_nombre:
            g.guardar_color_nombre(color, alerta=self._alerta)
        self.msg.setText("Guardado. Así te ve la gente.")
        if cambia_tema:
            ventana = self.ctx.ventana if getattr(self.ctx, "ventana", None) is not None else None
            if ventana is not None and hasattr(ventana, "reabrir_con_aspecto"):
                ventana.reabrir_con_aspecto()

    def _alerta(self, texto):
        self.msg.setText(texto)

    def _quitar_todo(self):
        self.sel = {"marco": NINGUNO, "efecto": NINGUNO, "tema": NINGUNO}
        self.sel_color = None
        self._marcar()
        self._aplicar()
