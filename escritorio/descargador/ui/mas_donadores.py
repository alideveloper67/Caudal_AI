# -*- coding: utf-8 -*-
"""Ajustes › «Más para donadores»: letra con efectos, pared de agradecimiento y tu propia mascota.

Igual que «Personalizar», se ve siempre: quien todavía no tiene los beneficios ve cada cosa con candado y, al
tocarla, una explicación corta de cómo conseguirla (donar o, para lo que vale con prueba, canjear un código).

- Letra con efectos: abre la vista grande (letra_escena.py) con lo que suena. Vale con la prueba.
- Pared de agradecimiento: la casilla «Aparecer en la pared» (apagada por defecto). Solo donadores y
  fundadores (la prueba no cuenta) y solo mayores de 18 años (la pared es pública, también en la web).
  «Ver la pared» la abre para cualquiera.
- Tu propia mascota: abre WhatsApp con un mensaje ya escrito; el diseño se aprueba por WhatsApp.
"""

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import social as S
from ..hilos import en_segundo_plano
from ..premium_datos import TEXTO_MASCOTA, url_mascota
from .canje_pase import boton_codigo
from .donar import boton_donar
from .estilos import C

ORO = "#FFC857"
CANDADO_PRUEBA = "🔒 Es para donadores: dona con Yape o canjea un código de prueba para usarla."
CANDADO_DONADOR = ("🔒 Es solo para donadores y fundadores (el código de prueba no cuenta). "
                   "Dona con Yape para tenerlo.")


def abrir_whatsapp_mascota(usuario):
    """Abre WhatsApp (la app o la web) con el mensaje para pedir la mascota. True si se pudo abrir."""
    return bool(QDesktopServices.openUrl(QUrl(url_mascota(usuario))))


class _Fila(QFrame):
    """Una función: título, explicación, un botón y (sin beneficios) el candado con lo que hay que hacer."""

    def __init__(self, titulo, detalle, padre=None):
        super().__init__(padre)
        self.setObjectName("fila_donador")
        self.setStyleSheet(f"QFrame#fila_donador{{background:{C['superficie']};border-radius:14px;}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(6)
        cab = QHBoxLayout()
        cab.setSpacing(8)
        self.et_titulo = QLabel(titulo)
        self.et_titulo.setStyleSheet("font-size:15px;font-weight:800;background:transparent;")
        cab.addWidget(self.et_titulo, 1)
        self.candado = QLabel("🔒")
        self.candado.setToolTip("Exclusivo para donadores")
        self.candado.setStyleSheet(f"color:{ORO};font-size:15px;background:transparent;")
        cab.addWidget(self.candado)
        v.addLayout(cab)
        self.et_detalle = QLabel(detalle)
        self.et_detalle.setObjectName("secundario")
        self.et_detalle.setWordWrap(True)
        v.addWidget(self.et_detalle)
        self.cuerpo = QHBoxLayout()
        self.cuerpo.setSpacing(8)
        v.addLayout(self.cuerpo)
        # lo que sale al tocar algo bloqueado: cómo conseguirlo
        self.caja_explica = QWidget()
        h = QHBoxLayout(self.caja_explica)
        h.setContentsMargins(0, 2, 0, 0)
        h.setSpacing(8)
        self.et_explica = QLabel("")
        self.et_explica.setObjectName("ayuda")
        self.et_explica.setWordWrap(True)
        h.addWidget(self.et_explica, 1)
        self.zona_botones = h
        v.addWidget(self.caja_explica)
        self.caja_explica.hide()

    def explicar(self, texto, ctx, con_codigo):
        self.et_explica.setText(texto)
        if not getattr(self, "_botones_puestos", False):
            self._botones_puestos = True
            self.zona_botones.addWidget(boton_donar(texto="Donar aquí"))
            if con_codigo:
                self.zona_botones.addWidget(boton_codigo(ctx, texto="Tengo un código"))
        self.caja_explica.show()


class SeccionMasDonadores(QFrame):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.gestor = getattr(ctx, "premium", None)
        self.setObjectName("caja")
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(12)
        t = QLabel("Más para donadores")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        v.addWidget(t)
        ayuda = QLabel("Gracias por sostener Caudal. Esto es lo que tienes por apoyarlo.")
        ayuda.setObjectName("secundario")
        ayuda.setWordWrap(True)
        v.addWidget(ayuda)

        # ---- letra con efectos
        self.fila_letra = _Fila("Letra con efectos a pantalla completa",
                                "Solo el verso que suena, enorme, con animaciones al entrar cada línea y un "
                                "resplandor con los colores de la carátula. Cuatro estilos: Resplandor, Ola, "
                                "Neón y Cine. También desde el botón del visualizador o con Ctrl+Shift+Y.")
        self.bt_letra = QPushButton("Abrir con lo que suena")
        self.bt_letra.setCursor(Qt.PointingHandCursor)
        self.bt_letra.clicked.connect(self._abrir_letra)
        self.fila_letra.cuerpo.addWidget(self.bt_letra)
        self.fila_letra.cuerpo.addStretch(1)
        v.addWidget(self.fila_letra)

        # ---- pared de agradecimiento
        self.fila_pared = _Fila("Pared de agradecimiento",
                                "Una lista con los nombres de quienes apoyan Caudal, en la app y en la web. "
                                "Solo sales si lo marcas aquí (y tienes 18 años o más). Puedes quitarte cuando "
                                "quieras.")
        self.casilla_pared = QCheckBox("Aparecer en la pared de agradecimiento")
        self.casilla_pared.setCursor(Qt.PointingHandCursor)
        self.casilla_pared.toggled.connect(self._cambiar_pared)
        self.fila_pared.cuerpo.addWidget(self.casilla_pared)
        self.fila_pared.cuerpo.addStretch(1)
        self.bt_ver_pared = QPushButton("Ver la pared")
        self.bt_ver_pared.setObjectName("contorno")
        self.bt_ver_pared.setCursor(Qt.PointingHandCursor)
        self.bt_ver_pared.clicked.connect(self._ver_pared)
        self.fila_pared.cuerpo.addWidget(self.bt_ver_pared)
        v.addWidget(self.fila_pared)

        # ---- mascota propia
        self.fila_mascota = _Fila("Tu propia mascota",
                                  "Una mascota diseñada para ti, que camina por la barra de la canción. "
                                  + TEXTO_MASCOTA)
        self.bt_mascota = QPushButton("Quiero mi propia mascota")
        self.bt_mascota.setCursor(Qt.PointingHandCursor)
        self.bt_mascota.clicked.connect(self._pedir_mascota)
        self.fila_mascota.cuerpo.addWidget(self.bt_mascota)
        self.fila_mascota.cuerpo.addStretch(1)
        v.addWidget(self.fila_mascota)

        self.msg = QLabel("")
        self.msg.setObjectName("secundario")
        self.msg.setWordWrap(True)
        self.msg.hide()
        v.addWidget(self.msg)

        if self.gestor is not None:
            self.gestor.cambiado.connect(self.refrescar)
        self.refrescar()

    # ------------------------------------------------------------ estado
    @property
    def _premium(self):
        return bool(self.gestor is not None and self.gestor.premium)

    @property
    def _donador(self):
        return bool(self.gestor is not None and self.gestor.donador_de_verdad)

    def refrescar(self):
        premium, donador = self._premium, self._donador
        self.fila_letra.candado.setVisible(not premium)
        self.bt_letra.setText("Abrir con lo que suena" if premium else "🔒 Abrir con lo que suena")
        self.fila_pared.candado.setVisible(not donador)
        self.fila_mascota.candado.setVisible(not donador)
        self.bt_mascota.setText("Quiero mi propia mascota" if donador else "🔒 Quiero mi propia mascota")
        en_pared = bool(self.gestor is not None and self.gestor.en_pared)
        self.casilla_pared.blockSignals(True)
        self.casilla_pared.setChecked(en_pared and donador)
        self.casilla_pared.blockSignals(False)
        # sin beneficios la casilla se puede tocar, pero solo para que explique cómo conseguirlo
        self.casilla_pared.setText("Aparecer en la pared de agradecimiento" if donador
                                   else "🔒 Aparecer en la pared de agradecimiento")
        if premium:
            self.fila_letra.caja_explica.hide()
        if donador:
            self.fila_pared.caja_explica.hide()
            self.fila_mascota.caja_explica.hide()

    def _avisar(self, texto):
        self.msg.setText(texto)
        self.msg.setVisible(bool(texto))

    # ------------------------------------------------------------ acciones
    def _abrir_letra(self):
        if not self._premium:
            self.fila_letra.explicar(CANDADO_PRUEBA, self.ctx, con_codigo=True)
            return
        v = getattr(self.ctx, "ventana", None)
        if v is not None and hasattr(v, "abrir_escena"):
            v.abrir_escena()

    def _cambiar_pared(self, si):
        if not self._donador:
            self.casilla_pared.blockSignals(True)
            self.casilla_pared.setChecked(False)
            self.casilla_pared.blockSignals(False)
            self.fila_pared.explicar(CANDADO_DONADOR, self.ctx, con_codigo=False)
            return
        self.gestor.guardar_en_pared(si, alerta=self._avisar)
        self._avisar("Listo: ya sales en la pared. ¡Gracias!" if si else "Listo: ya no sales en la pared.")

    def _ver_pared(self):
        DialogoPared(self.ctx, self.window()).exec()

    def _pedir_mascota(self):
        if not self._donador:
            self.fila_mascota.explicar(CANDADO_DONADOR, self.ctx, con_codigo=False)
            return
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        if abrir_whatsapp_mascota(cuenta.get("usuario")):
            self._avisar("Abrimos WhatsApp con el mensaje listo: solo envíalo. " + TEXTO_MASCOTA)
        else:
            self._avisar("No se pudo abrir WhatsApp. Escríbenos al +51 902 464 984 diciendo tu usuario y que "
                         "quieres tu mascota personalizada.")


class DialogoPared(QDialog):
    """La pared de agradecimiento: los nombres de quienes apoyan Caudal (fundadores primero)."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        from . import iconos as _i
        from .estilos import hoja
        self.ctx = ctx
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(_i.flechas_qss()))
        self.setWindowTitle("Pared de agradecimiento · Caudal")
        self.setMinimumSize(460, 520)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)
        t = QLabel("Gracias a quienes sostienen Caudal")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        t.setWordWrap(True)
        v.addWidget(t)
        sub = QLabel("Caudal es gratis y sin anuncios gracias a estas personas. Si donaste y quieres salir aquí, "
                     "marca la casilla en Ajustes › Más para donadores.")
        sub.setObjectName("secundario")
        sub.setWordWrap(True)
        v.addWidget(sub)
        self.estado = QLabel("Cargando la pared…")
        self.estado.setObjectName("ayuda")
        self.estado.setWordWrap(True)
        v.addWidget(self.estado)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.contenido = QWidget()
        self.contenido.setObjectName("lienzo")
        self.lista = QVBoxLayout(self.contenido)
        self.lista.setContentsMargins(0, 0, 0, 0)
        self.lista.setSpacing(6)
        self.lista.addStretch(1)
        self.area.setWidget(self.contenido)
        v.addWidget(self.area, 1)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        v.addWidget(cerrar, 0, Qt.AlignRight)
        self.cargar()

    def cargar(self):
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        sesion = cuenta.get("sesion")
        trabajo = (S.Social(sesion).pared_agradecimiento if sesion is not None else S.pared_agradecimiento_publica)
        en_segundo_plano(trabajo, ok=self.pintar, error=self._fallo, dueno=self)

    def _fallo(self, e):
        self.estado.setText(S.explicar(e, "cargar la pared"))
        self.estado.show()

    def pintar(self, filas):
        while self.lista.count() > 1:
            it = self.lista.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        if not filas:
            self.estado.setText("Todavía no hay nadie en la pared. ¡Puedes ser la primera persona!")
            self.estado.show()
            return
        self.estado.hide()
        for i, f in enumerate(filas):
            self.lista.insertWidget(i, self._fila(f))

    def _fila(self, f):
        caja = QFrame()
        caja.setObjectName("fila_pared")
        caja.setStyleSheet(f"QFrame#fila_pared{{background:{C['superficie']};border-radius:12px;}}")
        h = QHBoxLayout(caja)
        h.setContentsMargins(14, 8, 14, 8)
        h.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(0)
        nombre = QLabel(f["nombre"])
        color = f.get("color") or C["texto"]
        nombre.setStyleSheet(f"font-size:15px;font-weight:800;color:{color};background:transparent;")
        col.addWidget(nombre)
        usuario = QLabel("@" + f["usuario"])
        usuario.setStyleSheet(f"color:{C['texto3']};font-size:11.5px;background:transparent;")
        col.addWidget(usuario)
        h.addLayout(col, 1)
        chip = QLabel("Fundador" if f["tipo"] == "fundador" else "Donador")
        fondo = ORO if f["tipo"] == "fundador" else C["superficie3"]
        texto = "#1A1203" if f["tipo"] == "fundador" else C["texto"]
        chip.setStyleSheet(f"background:{fondo};color:{texto};border-radius:9px;padding:2px 9px;"
                           "font-size:11px;font-weight:800;")
        h.addWidget(chip)
        return caja
