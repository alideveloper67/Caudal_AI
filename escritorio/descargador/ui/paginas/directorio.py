# -*- coding: utf-8 -*-
"""«Perfiles de Caudal»: rejilla de tarjetas con buscador y carga progresiva.

    PaginaDirectorio(ctx)
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Esqueleto, Portada, SinResultados, suavizar
from ..estilos import C
from . import perfil_comun as PC

LOTE = 24
ANCHO_TARJETA = 250


class TarjetaPerfil(QFrame):
    """Foto sobre una banda con el color de la persona, nombre, descripción corta,
    canción favorita, insignias y los botones de me gusta y amistad."""

    abrir = Signal(str)

    def __init__(self, p, ctx, social, padre=None):
        super().__init__(padre)
        self.p, self.ctx, self.social = p, ctx, social
        color = PC.color_de(p)
        self.setObjectName("tarjeta_perfil")
        self.setFixedWidth(ANCHO_TARJETA)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"QFrame#tarjeta_perfil{{background:{C['panel']};border:1px solid {C['borde']};"
                           "border-radius:16px;}"
                           f"QFrame#tarjeta_perfil:hover{{border-color:{PC.mezclar(C['borde_claro'], color, 0.5)};"
                           f"background:{C['superficie']};}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 14)
        v.setSpacing(0)
        banda = QFrame()
        banda.setFixedHeight(62)
        banda.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {PC.tinte(color, 0.75)},"
                            f"stop:1 {PC.tinte(color, 0.3)});border-top-left-radius:15px;"
                            "border-top-right-radius:15px;border:none;")
        v.addWidget(banda)
        # la foto «sube» sobre la banda
        self.avatar = PC.Avatar(72, S.nombre_visible(p), color, p["foto_url"], anillo=C["panel"], padre=self)
        self.avatar.move(16, 26)
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(16, 0, 16, 0)
        cuerpo.setSpacing(3)
        cuerpo.addSpacing(42)
        notas = PC.notas_de(p, solo_principales=True)
        if notas:
            cuerpo.addWidget(notas[0], 0, Qt.AlignLeft)
        n = PC.etiqueta(S.nombre_visible(p), "font-size:16px;font-weight:800;", False)
        n.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        cuerpo.addWidget(n)
        u = PC.etiqueta(f"@{p['usuario']}", f"color:{C['texto3']};font-size:12px;", False)
        cuerpo.addWidget(u)
        if p["bio"]:
            b = PC.etiqueta(_corto(p["bio"], 110), f"color:{C['texto2']};font-size:12px;")
            b.setMinimumHeight(34)
            cuerpo.addSpacing(4)
            cuerpo.addWidget(b)
        if p["cancion_fav"]:
            cuerpo.addSpacing(6)
            cuerpo.addWidget(self._favorita(p["cancion_fav"]))
        cuerpo.addSpacing(4)
        datos = []
        if p["num_subidas"]:
            datos.append(f"♪ {p['num_subidas']} " + ("canción" if p["num_subidas"] == 1 else "canciones"))
        self.et_likes = PC.etiqueta("", f"color:{C['texto3']};font-size:11.5px;", False)
        cuerpo.addWidget(self.et_likes)
        self._datos_extra = datos
        self._texto_likes()
        cuerpo.addSpacing(6)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.bt_amistad = QPushButton()
        self.bt_amistad.setCursor(Qt.PointingHandCursor)
        self.bt_amistad.setFocusPolicy(Qt.NoFocus)
        self.bt_amistad.clicked.connect(self._amistad)
        fila.addWidget(self.bt_amistad, 1)
        self.bt_like = PC.boton_redondo("corazon", "Me gusta", self._like, 34)
        fila.addWidget(self.bt_like)
        cuerpo.addLayout(fila)
        v.addLayout(cuerpo)
        self._repintar_botones()

    def _favorita(self, c):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:{C['superficie2']};border-radius:10px;}}")
        h = QHBoxLayout(f)
        h.setContentsMargins(6, 6, 10, 6)
        h.setSpacing(8)
        por = Portada(34, radio=6)
        por.set_url(c["miniatura"] or "")
        h.addWidget(por)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = PC.etiqueta(c["titulo"], "font-size:11.5px;font-weight:700;", False)
        t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        a = PC.etiqueta(c["artista"] or "Canción favorita", f"color:{C['texto3']};font-size:10.5px;", False)
        a.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(t)
        col.addWidget(a)
        h.addLayout(col, 1)
        return f

    def _texto_likes(self):
        p = self.p
        partes = [f"♥ {p['likes']}"] + self._datos_extra
        self.et_likes.setText("   ".join(partes))

    def _repintar_botones(self):
        p = self.p
        texto, accion, ayuda = S.accion_amistad(p["relacion"])
        self._accion = accion
        if accion is None:
            self.bt_amistad.hide()
        else:
            self.bt_amistad.show()
            principal = accion in ("enviar", "aceptar", "escribir")
            self.bt_amistad.setText(texto)
            self.bt_amistad.setToolTip(ayuda)
            if principal:
                self.bt_amistad.setStyleSheet(
                    f"QPushButton{{background:{C['acento']};color:{C['acento_texto']};border:none;"
                    "border-radius:17px;padding:8px 10px;font-weight:800;}}"
                    f"QPushButton:hover{{background:{C['acento_alto']};}}")
            else:
                self.bt_amistad.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{C['texto']};border:1px solid {C['borde_claro']};"
                    "border-radius:17px;padding:8px 10px;font-weight:700;}}"
                    f"QPushButton:hover{{border-color:{C['texto']};}}")
        self.bt_like.setIcon(iconos.icono("corazon_lleno" if p["di_like"] else "corazon", 17,
                                          C["acento"] if p["di_like"] else C["texto"]))
        self.bt_like.setToolTip("Quitar me gusta" if p["di_like"] else "Me gusta")

    # ------------------------------------------------------------ acciones
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.abrir.emit(self.p["usuario"])
        super().mousePressEvent(e)

    def _like(self):
        p = self.p
        funcion = self.social.quitar_like if p["di_like"] else self.social.dar_like

        def listo(total):
            p["di_like"] = not p["di_like"]
            p["likes"] = total
            self._texto_likes()
            self._repintar_botones()
        en_segundo_plano(funcion, p["id"], ok=listo,
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "dar me gusta")),
                         dueno=self, urgente=True)

    def _amistad(self):
        p, accion = self.p, self._accion
        nombre = S.nombre_visible(p)
        if accion == "escribir":
            self.ctx.chat_pendiente = {"id": p["id"], "usuario": p["usuario"], "nombre": p["nombre"],
                                       "visible": nombre}
            self.ctx.navegar({"pagina": "mensajes"})
            return
        if accion == "cancelar":
            funcion = self.social.cancelar_solicitud

            def listo(_r):
                p["relacion"] = "ninguna"
                PC.aviso(self.ctx, "Solicitud cancelada")
                self._repintar_botones()
        else:
            funcion = self.social.enviar_solicitud

            def listo(r):
                p["relacion"] = S.relacion_tras_envio(r)
                PC.aviso(self.ctx, S.mensaje_tras_envio(r, nombre))
                self._repintar_botones()
        en_segundo_plano(funcion, p["id"], ok=listo,
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "hacer eso")),
                         dueno=self, urgente=True)


def _corto(t, n):
    t = " ".join(str(t).split())
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


class PaginaDirectorio(QWidget):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Perfiles de Caudal"
        self.social = S.social_de(ctx)
        self.busqueda = ""
        self.tarjetas = []
        self.desde = 0
        self.fin = False
        self.cargando = False
        self._generacion = 0
        self._columnas = 0
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 0)
        raiz.setSpacing(12)
        cab = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Perfiles de Caudal")
        t.setObjectName("titulo_pagina")
        col.addWidget(t)
        col.addWidget(PC.etiqueta("Conoce a otras personas que escuchan música aquí. Dales me gusta y "
                                  "envíales una solicitud de amistad.", f"color:{C['texto2']};"))
        cab.addLayout(col, 1)
        raiz.addLayout(cab)
        self.campo = QLineEdit()
        self.campo.setObjectName("buscador")
        self.campo.setPlaceholderText("Buscar por nombre o usuario")
        self.campo.setMaximumWidth(420)
        self.campo.addAction(iconos.icono("lupa", 16, C["texto3"]), QLineEdit.LeadingPosition)
        self.campo.textChanged.connect(lambda _t: self.reloj.start())
        raiz.addWidget(self.campo, 0, Qt.AlignLeft)
        self.caja_aviso = QVBoxLayout()
        raiz.addLayout(self.caja_aviso)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        suavizar(self.area)
        self.interior = QWidget()
        self.interior.setObjectName("interior_dir")
        self.interior.setStyleSheet("QWidget#interior_dir{background:transparent;}")
        iv = QVBoxLayout(self.interior)
        iv.setContentsMargins(0, 4, 0, 24)
        iv.setSpacing(14)
        self.rejilla = QGridLayout()
        self.rejilla.setSpacing(16)
        self.rejilla.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        iv.addLayout(self.rejilla)
        self.pie = QVBoxLayout()
        iv.addLayout(self.pie)
        iv.addStretch(1)
        self.area.setWidget(self.interior)
        self.area.verticalScrollBar().valueChanged.connect(self._al_desplazar)
        raiz.addWidget(self.area, 1)

        self.reloj = QTimer(self)
        self.reloj.setSingleShot(True)
        self.reloj.setInterval(450)
        self.reloj.timeout.connect(self._nueva_busqueda)
        if self.social is None:
            self._mensaje("usuario", "Los perfiles necesitan tu cuenta",
                          "Abre Caudal con internet e inicia sesión para conocer a otras personas.")
        else:
            self._aviso_mi_perfil()
            self._cargar_mas()

    # ------------------------------------------------------------ avisos
    def _aviso_mi_perfil(self):
        mio = ((getattr(self.ctx, "cuenta", None) or {}).get("usuario") or "")
        if not mio:
            return
        en_segundo_plano(self.social.ver_perfil, mio, ok=self._tras_mi_perfil, error=lambda _e: None,
                         dueno=self, urgente=True)

    def _tras_mi_perfil(self, p):
        if not p or p["publico"]:
            return
        f = QFrame()
        f.setObjectName("aviso_privado")
        f.setStyleSheet(f"QFrame#aviso_privado{{background:{C['superficie']};border:1px solid {C['borde']};"
                        "border-radius:14px;}")
        h = QHBoxLayout(f)
        h.setContentsMargins(16, 10, 12, 10)
        h.addWidget(PC.etiqueta("Tu perfil es privado, así que nadie te ve aquí. Puedes hacerlo público "
                                "al editar tu perfil (solo mayores de 18 años).", f"color:{C['texto2']};"), 1)
        h.addWidget(PC.boton("Ir a mi perfil", "contorno",
                             al_pulsar=lambda: self.ctx.navegar({"pagina": "perfil", "usuario": p["usuario"]})))
        PC.limpiar(self.caja_aviso)
        self.caja_aviso.addWidget(f)

    def _mensaje(self, icono, titulo, texto):
        PC.limpiar(self.pie)
        self.pie.addWidget(SinResultados(icono, titulo, texto))

    # ------------------------------------------------------------ carga
    def _nueva_busqueda(self):
        texto = self.campo.text().strip()
        if texto == self.busqueda and self.tarjetas:
            return
        self.busqueda = texto
        self._reiniciar()
        self._cargar_mas()

    def _reiniciar(self):
        self._generacion += 1
        for t in self.tarjetas:
            self.rejilla.removeWidget(t)
            t.deleteLater()
        self.tarjetas = []
        self.desde = 0
        self.fin = False
        self.cargando = False
        self._columnas = 0
        PC.limpiar(self.pie)

    def _cargar_mas(self):
        if self.social is None or self.cargando or self.fin:
            return
        self.cargando = True
        gen = self._generacion
        PC.limpiar(self.pie)
        if not self.tarjetas:
            self.pie.addWidget(Esqueleto("tarjetas"))
        else:
            self.pie.addWidget(PC.etiqueta("Cargando más personas…", f"color:{C['texto3']};", False))
        en_segundo_plano(self.social.explorar_perfiles, self.busqueda, LOTE, self.desde,
                         ok=lambda r, g=gen: self._llegan(g, r),
                         error=lambda e, g=gen: self._fallo(g, e), dueno=self, urgente=True)

    def _llegan(self, gen, lista):
        if gen != self._generacion:
            return
        self.cargando = False
        PC.limpiar(self.pie)
        self.desde += len(lista)
        self.fin = len(lista) < LOTE
        for p in lista:
            t = TarjetaPerfil(p, self.ctx, self.social)
            t.abrir.connect(lambda u: self.ctx.navegar({"pagina": "perfil", "usuario": u}))
            self.tarjetas.append(t)
        self._ordenar(forzar=True)
        if not self.tarjetas:
            if self.busqueda:
                self._mensaje("lupa", "Sin resultados", f"No hay perfiles públicos que coincidan con «{self.busqueda}».")
            else:
                self._mensaje("usuario", "Aún no hay perfiles públicos",
                              "Cuando alguien haga público su perfil, aparecerá aquí. "
                              "¡Puedes ser tú! Hazlo desde «Mi perfil».")
        elif not self.fin:
            b = PC.boton("Mostrar más personas", "contorno", al_pulsar=self._cargar_mas)
            self.pie.addWidget(b, 0, Qt.AlignCenter)
        QTimer.singleShot(0, self._al_desplazar)

    def _fallo(self, gen, e):
        if gen != self._generacion:
            return
        self.cargando = False
        PC.limpiar(self.pie)
        self.pie.addWidget(PC.etiqueta(S.explicar(e, "cargar los perfiles"), f"color:{C['error']};"))
        self.pie.addWidget(PC.boton("Reintentar", "contorno", al_pulsar=self._cargar_mas), 0, Qt.AlignLeft)

    def _al_desplazar(self, *_):
        b = self.area.verticalScrollBar()
        if self.tarjetas and not self.fin and not self.cargando and b.value() >= b.maximum() - 320:
            self._cargar_mas()

    # ------------------------------------------------------------ rejilla
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ordenar()

    def _ordenar(self, forzar=False):
        if not self.tarjetas:
            return
        ancho = max(ANCHO_TARJETA, self.area.viewport().width())
        columnas = max(1, (ancho + 16) // (ANCHO_TARJETA + 16))
        if columnas == self._columnas and not forzar:
            return
        self._columnas = columnas
        for t in self.tarjetas:
            self.rejilla.removeWidget(t)
        for i, t in enumerate(self.tarjetas):
            self.rejilla.addWidget(t, i // columnas, i % columnas, Qt.AlignTop)
