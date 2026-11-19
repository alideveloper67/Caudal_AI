# -*- coding: utf-8 -*-
"""Amigos y solicitudes: buscar por usuario exacto, aceptar o rechazar, quitar, bloquear.

    PanelSolicitudes(ctx, compacto=False)   # recibidas y enviadas
    PanelAmigos(ctx, compacto=False)        # buscador + lista de amigos (+ bloqueados)
    PaginaAmigos(ctx, pestana="solicitudes")  # página con los dos (y «Bloqueados»)

Los paneles se usan dentro de Mensajes (compacto=True, en la columna izquierda) y en
la página completa. Nadie puede escribir a quien no es amigo: «Escribir» solo aparece
con amistad aceptada.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Pagina
from ..estilos import C, hoja
from ..premium_estilos import nombre_efecto
from . import perfil_comun as PC


def ver_perfil(ctx, usuario):
    ctx.navegar({"pagina": "perfil", "usuario": usuario})


def fila_persona(p, compacto=False, acciones=(), al_abrir=None, detalle=""):
    """Una persona: foto, nombre y usuario, y a la derecha sus botones.
    acciones: lista de (icono, ayuda, función, texto, estilo)."""
    f = QFrame()
    f.setObjectName("fila_persona")
    f.setCursor(Qt.PointingHandCursor if al_abrir else Qt.ArrowCursor)
    f.setStyleSheet(f"QFrame#fila_persona{{background:{C['superficie']};border-radius:12px;}}"
                    f"QFrame#fila_persona:hover{{background:{C['superficie2']};}}")
    h = QHBoxLayout(f)
    h.setContentsMargins(10, 8, 10, 8)
    h.setSpacing(10)
    h.addWidget(PC.Avatar(40 if compacto else 46, S.nombre_visible(p), None, p.get("foto_url"),
                          marco=p.get("marco")))
    col = QVBoxLayout()
    col.setSpacing(0)
    n = nombre_efecto(S.nombre_visible(p), "font-size:13.5px;font-weight:700;", p.get("efecto_nombre"), False)
    n.setMinimumWidth(30)
    n.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    col.addWidget(n)
    sub = f"@{p.get('usuario') or ''}" + (f" · {detalle}" if detalle else "")
    u = PC.etiqueta(sub, f"color:{C['texto3']};font-size:11.5px;", False)
    u.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    col.addWidget(u)
    h.addLayout(col, 1)
    for icono, ayuda, funcion, texto, estilo in acciones:
        if compacto or not texto:
            b = PC.boton_redondo(icono, ayuda, funcion, 30,
                                 color=C["acento_texto"] if estilo == "principal" else None,
                                 fondo=C["acento"] if estilo == "principal" else None)
        else:
            b = PC.boton(texto, estilo, icono, ayuda=ayuda, al_pulsar=funcion)
            b.setMinimumHeight(30)
        h.addWidget(b)
    if al_abrir:
        for w in f.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        f.mousePressEvent = lambda e: al_abrir() if e.button() == Qt.LeftButton else None
    return f


class _PanelLista(QWidget):
    """Base: un área con desplazamiento y un mensaje de carga o de error."""

    cambio = Signal()

    def __init__(self, ctx, compacto=False, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.compacto = compacto
        self.social = S.social_de(ctx)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(8)
        self.cabecera = QVBoxLayout()
        self.cabecera.setSpacing(8)
        self.v.addLayout(self.cabecera)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setObjectName("interior_panel")
        self.interior.setStyleSheet("QWidget#interior_panel{background:transparent;}")
        self.lista = QVBoxLayout(self.interior)
        self.lista.setContentsMargins(0, 0, 4, 0)
        self.lista.setSpacing(6)
        self.area.setWidget(self.interior)
        self.v.addWidget(self.area, 1)
        self.cargado = False

    def mensaje(self, texto, error=False):
        PC.limpiar(self.lista)
        self.lista.addWidget(PC.etiqueta(texto, f"color:{C['error'] if error else C['texto2']};"
                                                "font-size:12.5px;"))
        self.lista.addStretch(1)

    def sin_cuenta(self):
        self.mensaje("Los amigos necesitan una cuenta de Caudal con internet. "
                     "Vuelve a abrir Caudal con conexión.")

    def seccion(self, texto):
        et = QLabel(texto.upper())
        et.setObjectName("seccion")
        et.setStyleSheet("background:transparent;margin-top:6px;")
        self.lista.addWidget(et)

    def accion_hecha(self, texto):
        PC.aviso(self.ctx, texto)
        self.cambio.emit()
        self.cargar()

    def hacer(self, funcion, *args, listo=None, que="hacer eso"):
        en_segundo_plano(funcion, *args,
                         ok=listo or (lambda _r: self.cargar()),
                         error=lambda e: PC.aviso(self.ctx, S.explicar(e, que)),
                         dueno=self, urgente=True)

    def cargar(self):
        raise NotImplementedError

    def showEvent(self, e):
        super().showEvent(e)
        if not self.cargado and self.social is not None:
            self.cargar()


# ====================================================================== solicitudes

class PanelSolicitudes(_PanelLista):
    contador = Signal(int)

    def __init__(self, ctx, compacto=False, padre=None):
        super().__init__(ctx, compacto, padre)
        if self.social is None:
            self.sin_cuenta()
        else:
            self.mensaje("Cargando tus solicitudes…")

    def cargar(self):
        if self.social is None:
            return
        self.cargado = True

        def traer():
            return self.social.mis_solicitudes(), self.social.mis_enviadas()
        en_segundo_plano(traer, ok=self._pintar,
                         error=lambda e: self.mensaje(S.explicar(e, "cargar tus solicitudes"), True),
                         dueno=self, urgente=True)

    def _pintar(self, datos):
        recibidas, enviadas = datos
        self.contador.emit(len(recibidas))
        PC.limpiar(self.lista)
        if not recibidas and not enviadas:
            self.lista.addWidget(PC.etiqueta(
                "No tienes solicitudes.\n\nCuando alguien quiera ser tu amigo, aparecerá aquí. "
                "Para agregar a alguien, busca su usuario en la pestaña «Amigos».",
                f"color:{C['texto2']};font-size:12.5px;"))
            self.lista.addStretch(1)
            return
        if recibidas:
            self.seccion(f"Recibidas ({len(recibidas)})")
        for p in recibidas:
            self.lista.addWidget(fila_persona(
                p, self.compacto, [
                    ("listo", "Aceptar", lambda p=p: self._responder(p, True), "Aceptar", "principal"),
                    ("cerrar", "Rechazar", lambda p=p: self._responder(p, False), "Rechazar", "contorno")],
                al_abrir=lambda p=p: ver_perfil(self.ctx, p["usuario"])))
        if enviadas:
            self.seccion(f"Enviadas ({len(enviadas)})")
        for p in enviadas:
            self.lista.addWidget(fila_persona(
                p, self.compacto, [
                    ("cerrar", "Cancelar la solicitud", lambda p=p: self._cancelar(p), "Cancelar", "contorno")],
                al_abrir=lambda p=p: ver_perfil(self.ctx, p["usuario"]), detalle="esperando respuesta"))
        self.lista.addStretch(1)

    def _responder(self, p, acepta):
        nombre = S.nombre_visible(p)
        self.hacer(self.social.responder_solicitud, p["solicitud"], acepta,
                   listo=lambda _r: self.accion_hecha(f"Ahora eres amigo de {nombre}" if acepta
                                                      else "Solicitud rechazada"),
                   que="responder la solicitud")

    def _cancelar(self, p):
        self.hacer(self.social.cancelar_solicitud, p["id"],
                   listo=lambda _r: self.accion_hecha("Solicitud cancelada"), que="cancelar la solicitud")


# ====================================================================== amigos

class DialogoBloqueados(QDialog):
    def __init__(self, ctx, social, padre=None):
        super().__init__(padre)
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle("Personas bloqueadas · Caudal")
        self.setMinimumSize(420, 380)
        self.ctx, self.social = ctx, social
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        t = QLabel("Personas bloqueadas")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        v.addWidget(PC.etiqueta("No pueden verte, escribirte ni enviarte solicitudes.", f"color:{C['texto2']};"))
        self.panel = _Bloqueados(ctx)
        v.addWidget(self.panel, 1)
        c = QPushButton("Cerrar")
        c.setObjectName("contorno")
        c.clicked.connect(self.accept)
        v.addWidget(c, 0, Qt.AlignRight)


class _Bloqueados(_PanelLista):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, False, padre)
        if self.social is None:
            self.sin_cuenta()
        else:
            self.mensaje("Cargando…")
            self.cargar()

    def cargar(self):
        self.cargado = True
        en_segundo_plano(self.social.mis_bloqueados, ok=self._pintar,
                         error=lambda e: self.mensaje(S.explicar(e, "cargar la lista"), True),
                         dueno=self, urgente=True)

    def _pintar(self, lista):
        PC.limpiar(self.lista)
        if not lista:
            self.lista.addWidget(PC.etiqueta("No tienes a nadie bloqueado.", f"color:{C['texto2']};"))
        for p in lista:
            self.lista.addWidget(fila_persona(p, False, [
                ("candado", "Desbloquear", lambda p=p: self._desbloquear(p), "Desbloquear", "contorno")]))
        self.lista.addStretch(1)

    def _desbloquear(self, p):
        self.hacer(self.social.desbloquear, p["id"],
                   listo=lambda _r: self.accion_hecha(f"Desbloqueaste a {S.nombre_visible(p)}"),
                   que="desbloquear")


class PanelAmigos(_PanelLista):
    escribir = Signal(dict)

    def __init__(self, ctx, compacto=False, padre=None):
        super().__init__(ctx, compacto, padre)
        self.amigos = []
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Buscar por usuario exacto")
        self.campo.setMaxLength(40)
        self.campo.returnPressed.connect(self._buscar)
        fila.addWidget(self.campo, 1)
        bt = PC.boton_redondo("lupa", "Buscar a esa persona", self._buscar, 34)
        fila.addWidget(bt)
        self.cabecera.addLayout(fila)
        self.resultado = QVBoxLayout()
        self.resultado.setSpacing(6)
        self.cabecera.addLayout(self.resultado)
        if self.social is None:
            self.sin_cuenta()
        else:
            self.mensaje("Cargando tus amigos…")

    # ------------------------------------------------------------ buscar
    def _buscar(self):
        if self.social is None:
            return
        u = self.campo.text().strip().lstrip("@").lower()
        PC.limpiar(self.resultado)
        if not u:
            return
        yo = ((getattr(self.ctx, "cuenta", None) or {}).get("usuario") or "").lower()
        if u == yo:
            self.resultado.addWidget(PC.etiqueta("Ese es tu propio usuario. Escribe el de otra persona.",
                                                 f"color:{C['texto2']};font-size:12.5px;"))
            return
        self.resultado.addWidget(PC.etiqueta("Buscando…", f"color:{C['texto3']};font-size:12.5px;"))
        en_segundo_plano(self.social.buscar_persona, u, ok=lambda p, u=u: self._resultado(u, p),
                         error=lambda e: self._msg_resultado(S.explicar(e, "buscar")),
                         dueno=self, urgente=True)

    def _msg_resultado(self, texto):
        PC.limpiar(self.resultado)
        self.resultado.addWidget(PC.etiqueta(texto, f"color:{C['texto2']};font-size:12.5px;"))

    def _resultado(self, u, p):
        if u != self.campo.text().strip().lstrip("@").lower():
            return
        PC.limpiar(self.resultado)
        if p is None:
            self._msg_resultado(f"No hay nadie con el usuario «{u}». Revisa que esté bien escrito: "
                                "tiene que ser exacto.")
            return
        texto, accion, ayuda = S.accion_amistad(p["relacion"])
        acciones = []
        if accion:
            icono = {"enviar": "mas", "aceptar": "listo", "escribir": "chat", "cancelar": "cerrar"}.get(accion)
            acciones.append((icono or "mas", ayuda, lambda p=p, a=accion: self._accion_resultado(p, a), texto,
                             "principal" if accion in ("enviar", "aceptar", "escribir") else "contorno"))
        self.resultado.addWidget(fila_persona(p, self.compacto, acciones,
                                              al_abrir=lambda p=p: ver_perfil(self.ctx, p["usuario"])))

    def _accion_resultado(self, p, accion):
        if accion == "escribir":
            self.escribir.emit(p)
            return
        nombre = S.nombre_visible(p)
        if accion == "cancelar":
            self.hacer(self.social.cancelar_solicitud, p["id"],
                       listo=lambda _r: (PC.aviso(self.ctx, "Solicitud cancelada"), self._buscar(),
                                         self.cambio.emit()), que="cancelar la solicitud")
            return

        def listo(r):
            PC.aviso(self.ctx, S.mensaje_tras_envio(r, nombre))
            self._buscar()
            self.cambio.emit()
            self.cargar()
        self.hacer(self.social.enviar_solicitud, p["id"], listo=listo, que="enviar la solicitud")

    # ------------------------------------------------------------ lista
    def cargar(self):
        if self.social is None:
            return
        self.cargado = True
        en_segundo_plano(self.social.mis_amigos, ok=self._pintar,
                         error=lambda e: self.mensaje(S.explicar(e, "cargar tus amigos"), True),
                         dueno=self, urgente=True)

    def _pintar(self, amigos):
        self.amigos = amigos
        PC.limpiar(self.lista)
        if not amigos:
            self.lista.addWidget(PC.etiqueta(
                "Aún no tienes amigos.\n\nBusca el usuario exacto de alguien arriba y envíale una "
                "solicitud. Cuando la acepte podrán escribirse y mezclar sus gustos.",
                f"color:{C['texto2']};font-size:12.5px;"))
        else:
            self.seccion(f"Mis amigos ({len(amigos)})")
        for p in amigos:
            self.lista.addWidget(fila_persona(
                p, self.compacto, [
                    ("chat", "Escribir", lambda p=p: self.escribir.emit(p), "Escribir", "contorno"),
                    ("puntos", "Más opciones", lambda p=p: self._menu(p), "", "contorno")],
                al_abrir=lambda p=p: ver_perfil(self.ctx, p["usuario"])))
        bl = QPushButton("Personas bloqueadas")
        bl.setObjectName("enlace")
        bl.setCursor(Qt.PointingHandCursor)
        bl.clicked.connect(self._bloqueados)
        self.lista.addWidget(bl, 0, Qt.AlignLeft)
        self.lista.addStretch(1)

    def _menu(self, p):
        from PySide6.QtGui import QCursor
        m = QMenu(self)
        m.addAction(iconos.icono("usuario", 16, C["texto2"]), "Ver perfil",
                    lambda: ver_perfil(self.ctx, p["usuario"]))
        m.addAction(iconos.icono("cerrar", 16, C["texto2"]), "Quitar de mis amigos", lambda: self._quitar(p))
        m.addAction(iconos.icono("candado", 16, C["texto2"]), "Bloquear", lambda: self._bloquear(p))
        m.exec(QCursor.pos())

    def _quitar(self, p):
        nombre = S.nombre_visible(p)
        if not PC.confirmar(self, "Quitar amigo", f"¿Quitar a {nombre} de tus amigos? Ya no podrán escribirse.",
                            "Quitar"):
            return
        self.hacer(self.social.quitar_amigo, p["id"],
                   listo=lambda _r: self.accion_hecha(f"{nombre} ya no es tu amigo"), que="quitar al amigo")

    def _bloquear(self, p):
        nombre = S.nombre_visible(p)
        if not PC.confirmar(self, "Bloquear", f"¿Bloquear a {nombre}? Dejarán de ser amigos y no podrán verse "
                            "ni escribirse. Puedes desbloquear cuando quieras.", "Bloquear"):
            return
        self.hacer(self.social.bloquear, p["id"],
                   listo=lambda _r: self.accion_hecha(f"Bloqueaste a {nombre}"), que="bloquear")

    def _bloqueados(self):
        if self.social is not None:
            DialogoBloqueados(self.ctx, self.social, self).exec()


# ====================================================================== página completa

class PaginaAmigos(QWidget):
    """Amigos, solicitudes y bloqueados en una sola página (con las mismas piezas de Mensajes)."""

    def __init__(self, ctx, pestana="solicitudes", padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.titulo = "Amigos"
        self.setObjectName("lienzo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 20, 24, 20)
        fila = QHBoxLayout()
        caja = QWidget()
        caja.setMaximumWidth(760)
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        fila.addStretch(1)
        fila.addWidget(caja, 100)
        fila.addStretch(1)
        raiz.addLayout(fila, 1)
        t = QLabel("Amigos")
        t.setObjectName("titulo_pagina")
        v.addWidget(t)
        v.addWidget(PC.etiqueta("Solo se puede escribir a quien es tu amigo: primero envía una solicitud "
                                "y espera a que la acepte.", f"color:{C['texto2']};"))
        barra = QHBoxLayout()
        barra.setSpacing(0)
        self.botones = {}
        self.pila = []
        self.sol = PanelSolicitudes(ctx)
        self.ami = PanelAmigos(ctx)
        self.ami.escribir.connect(self._escribir)
        self.sol.cambio.connect(self.ami.cargar)
        self.sol.contador.connect(self._contador)
        self.bloq = _Bloqueados(ctx)
        self.paneles = {"solicitudes": self.sol, "amigos": self.ami, "bloqueados": self.bloq}
        for clave, texto in (("solicitudes", "Solicitudes"), ("amigos", "Amigos"), ("bloqueados", "Bloqueados")):
            b = QPushButton(texto)
            b.setObjectName("pestana")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=clave: self.mostrar(k))
            self.botones[clave] = b
            barra.addWidget(b)
        barra.addStretch(1)
        v.addLayout(barra)
        for w in self.paneles.values():
            v.addWidget(w, 1)
        self.mostrar(pestana if pestana in self.paneles else "solicitudes")

    def mostrar(self, clave):
        for k, w in self.paneles.items():
            w.setVisible(k == clave)
            self.botones[k].setChecked(k == clave)
        if clave == "bloqueados" and self.bloq.social is not None:
            self.bloq.cargar()

    def _contador(self, n):
        self.botones["solicitudes"].setText(f"Solicitudes ({n})" if n else "Solicitudes")

    def _escribir(self, p):
        self.ctx.chat_pendiente = {"id": p["id"], "usuario": p["usuario"], "nombre": p["nombre"],
                                   "visible": S.nombre_visible(p)}
        self.ctx.navegar({"pagina": "mensajes"})
