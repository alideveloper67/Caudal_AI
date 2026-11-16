# -*- coding: utf-8 -*-
"""Perfil de una persona (el tuyo o el de otra): portada teñida con su color, notas,
insignias, top del mes, afinidad, me gusta, amistad y su música subida.

    PaginaPerfil(ctx, usuario=None)    # usuario=None -> mi perfil
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Pagina, Portada, SinResultados
from ..estilos import C
from . import perfil_comun as PC


class PaginaPerfil(Pagina):
    def __init__(self, ctx, usuario=None, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Mi perfil" if not usuario else "Perfil"
        mio = ((getattr(ctx, "cuenta", None) or {}).get("usuario") or "").lower()
        self.usuario = (usuario or mio or "").strip().lstrip("@").lower()
        self.social = S.social_de(ctx)
        self.p = None
        self._ocupado = False
        self.lienzo.alto_degradado = 380
        if self.social is None or not self.usuario:
            self._sin_cuenta()
        else:
            self.cargar()

    # ------------------------------------------------------------ carga
    def _sin_cuenta(self):
        self.vaciar()
        self.cuerpo.addWidget(SinResultados(
            "usuario", "Los perfiles necesitan tu cuenta",
            "Abre Caudal con internet e inicia sesión para ver tu perfil y el de otras personas."))
        self.cuerpo.addStretch(1)

    def cargar(self):
        self.vaciar()
        self.cargando("", "filas")
        en_segundo_plano(self.social.ver_perfil, self.usuario, ok=self._pintar,
                         error=self._fallo, dueno=self, urgente=True)

    def _fallo(self, e):
        self.error(S.explicar(e, "cargar este perfil"), self.cargar)

    # ------------------------------------------------------------ pintar
    def _pintar(self, p):
        self.vaciar()
        if p is None:
            self.cuerpo.addWidget(SinResultados(
                "usuario", "No encontramos este perfil",
                "Puede que la persona ya no exista o que no puedas verla."))
            self.cuerpo.addStretch(1)
            return
        self.p = p
        self.titulo = "Mi perfil" if p["es_mio"] else S.nombre_visible(p)
        color = PC.color_de(p)
        self.set_color(PC.tinte(color, 0.30))
        col = PC.columna_central(self.cuerpo, 920)
        col.addWidget(self._hero(p, color))
        if p["privado"]:
            col.addWidget(self._aviso_privado(p))
            self.cuerpo.addStretch(1)
            return
        tarjetas = []

        def poner(w):
            col.addWidget(w)
            tarjetas.append(w)
        est = self._estadisticas(p, color)
        poner(est)
        if p["afinidad"] is not None:
            poner(self._afinidad(p, color))
        if p["bio"] or p["artista_fav"] or p["generos"]:
            poner(self._sobre(p, color))
        elif p["es_mio"]:
            poner(self._invitar_a_completar())
        if p["cancion_fav"]:
            poner(self._favorita(p, color))
        if p["insignias"]:
            poner(self._insignias(p))
        if p["top_artistas"] or p["top_canciones"]:
            poner(self._top(p, color))
        poner(self._subidas(p))
        self.cuerpo.addStretch(1)
        PC.entrada(tarjetas)

    def _hero(self, p, color):
        """Imagen de fondo a todo el ancho, un panel de cristal con el nombre encima y la foto
        grande solapada con el borde del fondo."""
        alto_fondo = 270
        cont = QWidget()
        cont.setMinimumHeight(alto_fondo + 92)
        v = QVBoxLayout(cont)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.fondo = PC.FondoPerfil(alto_fondo, 20, False, 0.82, color, p.get("banner_url"), animar=True)
        fl = QVBoxLayout(self.fondo)
        fl.setContentsMargins(186, 0, 18, 16)
        fl.addStretch(1)
        cristal = QFrame()
        cristal.setObjectName("cristal")
        cristal.setStyleSheet("QFrame#cristal{background:rgba(8, 10, 14, 0.58);"
                              "border:1px solid rgba(255, 255, 255, 0.12);border-radius:16px;}")
        cv = QVBoxLayout(cristal)
        cv.setContentsMargins(18, 12, 18, 12)
        cv.setSpacing(4)
        notas = PC.notas_de(p)
        if notas:
            fila = QHBoxLayout()
            fila.setSpacing(6)
            for n in notas:
                fila.addWidget(n)
            fila.addStretch(1)
            cv.addLayout(fila)
        nombre = QLabel(S.nombre_visible(p))
        nombre.setStyleSheet(f"background:transparent;color:{C['texto']};font-size:32px;font-weight:900;")
        nombre.setWordWrap(True)
        cv.addWidget(nombre)
        datos = [f"@{p['usuario']}"]
        if p["creado"] and S.mes_anio(p["creado"]):
            datos.append("en Caudal desde " + S.mes_anio(p["creado"]))
        cv.addWidget(PC.etiqueta("  ·  ".join(datos), f"color:{C['texto2']};font-size:13px;font-weight:600;"))
        if p["frase"]:
            cv.addWidget(PC.etiqueta(f"“{p['frase']}”", f"color:{C['texto']};font-size:14px;font-style:italic;"))
        fl.addWidget(cristal)
        v.addWidget(self.fondo)
        fila_acc = QHBoxLayout()
        fila_acc.setContentsMargins(186, 12, 0, 12)
        fila_acc.addLayout(self._acciones(p))
        v.addLayout(fila_acc)
        v.addStretch(1)
        av = PC.Avatar(148, S.nombre_visible(p), color, p["foto_url"], anillo=C["panel"], padre=cont,
                       animar=True)
        av.move(26, alto_fondo - 78)
        av.raise_()
        return cont

    def _estadisticas(self, p, color):
        fila = QHBoxLayout()
        fila.setSpacing(12)
        datos = [(str(p["likes"]), "me gusta", "corazon_lleno"),
                 (str(p["num_subidas"]), "canciones subidas", "musica"),
                 (str(len(p["insignias"])), "insignias", "estrella")]
        if p["afinidad"] is not None:
            datos.append((f"{int(p['afinidad'])} %", "de afinidad contigo", "usuario"))
        tarjetas = []
        for valor, rotulo, icono in datos:
            f, v = PC.tarjeta()
            v.setContentsMargins(16, 12, 16, 12)
            v.setSpacing(0)
            h = QHBoxLayout()
            ic = QLabel()
            ic.setPixmap(iconos.pixmap(icono, 18, color))
            ic.setStyleSheet("background:transparent;")
            h.addWidget(ic)
            h.addWidget(PC.etiqueta(valor, "font-size:22px;font-weight:900;", False))
            h.addStretch(1)
            v.addLayout(h)
            v.addWidget(PC.etiqueta(rotulo, f"color:{C['texto3']};font-size:11.5px;", False))
            fila.addWidget(f, 1)
            tarjetas.append(f)
        caja = QWidget()
        caja.setLayout(fila)
        caja._tarjetas = tarjetas
        return caja

    # ------------------------------------------------------------ acciones
    def _acciones(self, p):
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.fila_acciones = fila
        if p["es_mio"]:
            fila.addWidget(PC.boton("Editar perfil", "principal", "editar", al_pulsar=self._editar))
            fila.addWidget(PC.boton("Subir música", "contorno", "compartir",
                                    al_pulsar=lambda: self.ctx.navegar({"pagina": "subir_musica"})))
            if not p["privado"]:
                self.bt_compartir = self._boton_compartir()
                fila.addWidget(self.bt_compartir)
            estado = "Público" if p["publico"] else "Privado"
            ayuda = ("Cualquier persona mayor de 18 años puede verlo en Perfiles de Caudal." if p["publico"]
                     else "Solo tus amigos lo ven. Puedes hacerlo público al editar.")
            fila.addWidget(self._etiqueta_estado(f"Tu perfil es {estado.lower()}", ayuda))
            if p["likes"]:
                fila.addWidget(self._etiqueta_estado(f"♥ {p['likes']}", "Me gusta que te dieron"))
            fila.addStretch(1)
            return fila
        self._boton_amistad(p, fila)
        if not p["privado"]:
            self.bt_like = PC.boton(self._texto_like(p), "contorno", "corazon_lleno" if p["di_like"] else "corazon",
                                    C["acento"] if p["di_like"] else C["texto"], "Dar o quitar me gusta",
                                    self._like)
            fila.addWidget(self.bt_like)
            self.bt_compartir = self._boton_compartir()
            fila.addWidget(self.bt_compartir)
        mas = PC.boton_redondo("puntos", "Más opciones", self._menu_mas)
        fila.addWidget(mas)
        fila.addStretch(1)
        return fila

    def _boton_compartir(self):
        return PC.boton("Compartir perfil", "contorno", "compartir",
                        ayuda="Crea una imagen vertical de este perfil para un estado o una historia",
                        al_pulsar=self._compartir)

    def _compartir(self):
        from .perfil_compartir import DialogoCompartirPerfil
        DialogoCompartirPerfil(self.ctx, self.p, self).exec()

    def _etiqueta_estado(self, texto, ayuda=""):
        et = QLabel(texto)
        et.setToolTip(ayuda)
        et.setStyleSheet(f"background:{PC.rgba('#000000', 0.25)};color:{C['texto']};border-radius:13px;"
                         "padding:5px 12px;font-size:12px;font-weight:700;")
        return et

    def _texto_like(self, p):
        return f"{p['likes']}" if p["likes"] else "Me gusta"

    def _boton_amistad(self, p, fila):
        texto, accion, ayuda = S.accion_amistad(p["relacion"])
        if accion is None:
            return
        if accion == "escribir":
            fila.addWidget(PC.boton("Escribir", "principal", "chat", ayuda=ayuda, al_pulsar=self._escribir))
            fila.addWidget(self._etiqueta_estado("✓ Amigos"))
            return
        nombre = "contorno" if accion in ("cancelar", "desbloquear") else "principal"
        fila.addWidget(PC.boton(texto, nombre, "mas" if accion in ("enviar", "aceptar") else None,
                                ayuda=ayuda, al_pulsar=lambda a=accion: self._amistad(a)))

    def _amistad(self, accion):
        p = self.p
        nombre = S.nombre_visible(p)
        if accion == "cancelar":
            if not PC.confirmar(self, "Cancelar solicitud", f"¿Cancelar la solicitud que le enviaste a {nombre}?",
                                "Cancelar solicitud"):
                return
            funcion, args = self.social.cancelar_solicitud, (p["id"],)
            nueva = lambda _r: "ninguna"   # noqa: E731
        elif accion == "desbloquear":
            funcion, args = self.social.desbloquear, (p["id"],)
            nueva = lambda _r: "ninguna"   # noqa: E731
        else:
            funcion, args = self.social.enviar_solicitud, (p["id"],)
            nueva = S.relacion_tras_envio

        def listo(r):
            if accion in ("enviar", "aceptar"):
                PC.aviso(self.ctx, S.mensaje_tras_envio(r, nombre))
            elif accion == "cancelar":
                PC.aviso(self.ctx, "Solicitud cancelada")
            else:
                PC.aviso(self.ctx, f"Desbloqueaste a {nombre}")
            self.cargar()
        en_segundo_plano(funcion, *args, ok=listo,
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "hacer eso")),
                         dueno=self, urgente=True)

    def _escribir(self):
        p = self.p
        self.ctx.chat_pendiente = {"id": p["id"], "usuario": p["usuario"], "nombre": p["nombre"],
                                   "visible": S.nombre_visible(p)}
        self.ctx.navegar({"pagina": "mensajes"})

    def _like(self):
        p = self.p
        funcion = self.social.quitar_like if p["di_like"] else self.social.dar_like

        def listo(total):
            p["di_like"] = not p["di_like"]
            p["likes"] = total
            self._pintar(p)
        en_segundo_plano(funcion, p["id"], ok=listo,
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "dar me gusta")),
                         dueno=self, urgente=True)

    def _menu_mas(self):
        from PySide6.QtGui import QCursor
        p = self.p
        m = QMenu(self)
        if p["relacion"] == "amigo":
            m.addAction(iconos.icono("cerrar", 16, C["texto2"]), "Quitar de mis amigos", self._quitar_amigo)
        m.addAction(iconos.icono("candado", 16, C["texto2"]), "Bloquear", self._bloquear)
        m.exec(QCursor.pos())

    def _quitar_amigo(self):
        p = self.p
        if not PC.confirmar(self, "Quitar amigo", f"¿Quitar a {S.nombre_visible(p)} de tus amigos? "
                            "Ya no podrán escribirse.", "Quitar"):
            return
        en_segundo_plano(self.social.quitar_amigo, p["id"],
                         ok=lambda _r: (PC.aviso(self.ctx, "Ya no son amigos"), self.cargar()),
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "quitar al amigo")),
                         dueno=self, urgente=True)

    def _bloquear(self):
        p = self.p
        if not PC.confirmar(self, "Bloquear", f"¿Bloquear a {S.nombre_visible(p)}? No podrán verse, "
                            "escribirse ni enviarse solicitudes. Puedes desbloquear cuando quieras en "
                            "Mensajes → Amigos.", "Bloquear"):
            return

        def listo(_r):
            PC.aviso(self.ctx, f"Bloqueaste a {S.nombre_visible(p)}")
            self.cargar()
        en_segundo_plano(self.social.bloquear, p["id"], ok=listo,
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, "bloquear")),
                         dueno=self, urgente=True)

    def _editar(self):
        from .perfil_editar import DialogoEditarPerfil
        d = DialogoEditarPerfil(self.ctx, self.social, self.p, self)
        if d.exec() == QDialog.Accepted:
            self.cargar()

    # ------------------------------------------------------------ secciones
    def _aviso_privado(self, p):
        f, v = PC.tarjeta()
        v.addWidget(PC.etiqueta("Este perfil es privado", "font-size:17px;font-weight:800;"))
        v.addWidget(PC.etiqueta("Solo sus amigos pueden ver su descripción, su música y sus gustos. "
                                "Envíale una solicitud de amistad para conocerle mejor.",
                                f"color:{C['texto2']};"))
        return f

    def _invitar_a_completar(self):
        f, v = PC.tarjeta()
        v.addWidget(PC.etiqueta("Cuéntale al mundo quién eres", "font-size:17px;font-weight:800;"))
        v.addWidget(PC.etiqueta("Añade una foto, una descripción, tu canción favorita y un color. "
                                "Pulsa «Editar perfil» para empezar.", f"color:{C['texto2']};"))
        return f

    def _afinidad(self, p, color):
        f, v = PC.tarjeta()
        a = int(p["afinidad"])
        v.addWidget(PC.etiqueta(f"Os parecéis un {a} %", "font-size:17px;font-weight:800;"))
        v.addWidget(PC.BarraAfinidad(a, color))
        v.addWidget(PC.etiqueta("Lo calculamos con los artistas que los dos han escuchado en los últimos meses.",
                                f"color:{C['texto3']};font-size:11.5px;"))
        return f

    def _sobre(self, p, color):
        f, v = PC.tarjeta()
        if p["bio"]:
            v.addWidget(PC.etiqueta(p["bio"], "font-size:14px;"))
        if p["artista_fav"]:
            v.addWidget(PC.etiqueta(f"Artista favorito: <b>{_h(p['artista_fav'])}</b>", f"color:{C['texto2']};"))
        if p["generos"]:
            flujo = PC.FlujoChips()
            for g in p["generos"]:
                flujo.agregar(PC.chip_texto(g))
            v.addWidget(flujo)
        return f

    def _favorita(self, p, color):
        c = p["cancion_fav"]
        f, v = PC.tarjeta(PC.mezclar(C["borde"], color, 0.6))
        f.setStyleSheet(f"QFrame#tarjeta_social{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                        f"stop:0 {PC.tinte(color, 0.32)},stop:0.6 {C['panel']});border:1px solid "
                        f"{PC.mezclar(C['borde'], color, 0.6)};border-radius:16px;}}")
        v.addWidget(PC.etiqueta("CANCIÓN FAVORITA", f"color:{C['texto3']};font-size:11px;font-weight:800;"
                                                    "letter-spacing:1px;"))
        h = QHBoxLayout()
        h.setSpacing(18)
        por = Portada(148, radio=16)
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        brillo = QGraphicsDropShadowEffect(por)
        brillo.setBlurRadius(46)
        brillo.setOffset(0, 8)
        brillo.setColor(QColor(color))
        por.setGraphicsEffect(brillo)
        por.set_url(c["miniatura"] or (f"https://i.ytimg.com/vi/{c['video_id']}/hqdefault.jpg"
                                       if c["video_id"] else ""))
        h.addWidget(por)
        col = QVBoxLayout()
        col.addStretch(1)
        col.addWidget(PC.etiqueta(c["titulo"], "font-size:20px;font-weight:800;"))
        if c["artista"]:
            col.addWidget(PC.etiqueta(c["artista"], f"color:{C['texto2']};font-size:14px;"))
        pista = S.pista_de_favorita(c)
        if pista:
            fila = QHBoxLayout()
            fila.addWidget(PC.boton("Escuchar", "principal", "reproducir",
                                    al_pulsar=lambda: self.ctx.reproducir_pista(pista)))
            fila.addStretch(1)
            col.addSpacing(6)
            col.addLayout(fila)
        col.addStretch(1)
        h.addLayout(col, 1)
        v.addLayout(h)
        return f

    def _insignias(self, p):
        f, v = PC.tarjeta()
        v.addWidget(PC.titulo_seccion("Insignias"))
        flujo = PC.FlujoChips()
        for i in p["insignias"]:
            flujo.agregar(PC.chip_insignia(i))
        v.addWidget(flujo)
        return f

    def _top(self, p, color):
        f, v = PC.tarjeta()
        v.addWidget(PC.titulo_seccion("Lo más escuchado este mes"))
        if p["top_artistas"]:
            fila = QHBoxLayout()
            fila.setSpacing(14)
            for a in p["top_artistas"][:5]:
                caja = QVBoxLayout()
                caja.setSpacing(4)
                por = Portada(76, forma="redonda", icono="usuario")
                por.set_url(a.get("portada") or "")
                caja.addWidget(por, 0, Qt.AlignHCenter)
                n = PC.etiqueta(a["nombre"], "font-size:12px;font-weight:700;")
                n.setAlignment(Qt.AlignHCenter)
                n.setMaximumWidth(92)
                caja.addWidget(n)
                caja.addWidget(PC.etiqueta(f"{a.get('veces', 0)} veces",
                                           f"color:{C['texto3']};font-size:11px;"))
                fila.addLayout(caja)
            fila.addStretch(1)
            v.addLayout(fila)
        for x in p["top_canciones"][:5]:
            pista = S.pista_de_top(x)
            if pista:
                v.addWidget(self._fila_top(pista, x.get("veces", 0)))
        return f

    def _fila_top(self, pista, veces):
        b = QPushButton()
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedHeight(54)
        b.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:10px;text-align:left;}}"
                        f"QPushButton:hover{{background:{C['superficie']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(6, 4, 10, 4)
        por = Portada(42, radio=6)
        por.set_url(pista.get("miniatura") or "")
        h.addWidget(por)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(PC.etiqueta(pista["titulo"], "font-size:13px;font-weight:700;", False))
        col.addWidget(PC.etiqueta(pista["artista"], f"color:{C['texto2']};font-size:11.5px;", False))
        h.addLayout(col, 1)
        h.addWidget(PC.etiqueta(f"{veces} veces", f"color:{C['texto3']};font-size:11.5px;", False))
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False: self.ctx.reproducir_pista(pista))
        return b

    def _subidas(self, p):
        f, v = PC.tarjeta()
        v.addWidget(PC.titulo_seccion("Música subida" if not p["es_mio"] else "Mi música",
                                      "Canciones que compartió con la comunidad." if not p["es_mio"] else
                                      "Lo que subiste. Las puede escuchar toda la comunidad."))
        subidas = p["subidas"]
        if not subidas:
            v.addWidget(PC.etiqueta("Todavía no subió música." if not p["es_mio"] else
                                    "Aún no subiste nada. Pulsa «Subir música» para compartir tu primera canción.",
                                    f"color:{C['texto2']};"))
            return f
        publicas = [s for s in subidas if s["estado"] == "publicada"]
        if publicas:
            v.addWidget(PC.boton("Reproducir todo", "contorno", "reproducir",
                                 al_pulsar=lambda: PC.reproducir_subidas(self.ctx, self.social, publicas, 0, self)))
        for i, s in enumerate(subidas):
            t = PC.TarjetaSubida(s, propia=p["es_mio"], mostrar_autor=False)
            t.reproducir.connect(lambda s=s: self._tocar(s, subidas))
            t.reportar.connect(lambda s=s: PC.reportar_subida(self.ctx, self.social, s, self))
            t.borrar.connect(lambda s=s: PC.borrar_subida(self.ctx, self.social, s, self, self.cargar))
            v.addWidget(t)
        return f


    def _tocar(self, s, subidas):
        pub = [x for x in subidas if x["estado"] == "publicada"]
        if s in pub:
            PC.reproducir_subidas(self.ctx, self.social, pub, pub.index(s), self)
        else:
            PC.reproducir_subidas(self.ctx, self.social, [s], 0, self)


def _h(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
