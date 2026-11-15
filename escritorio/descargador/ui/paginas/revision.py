# -*- coding: utf-8 -*-
"""Revisión de música (solo moderación): las canciones nuevas y las reportadas esperan aquí.
Se escucha antes de decidir; se aprueba, o se rechaza con un motivo que verá quien la subió.

    PaginaRevision(ctx)      # destino: {"pagina": "revision"}
    es_moderador(ctx, al_saber)   # para mostrar u ocultar la entrada del panel lateral
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Pagina, Portada, SinResultados
from ..estilos import C, hoja
from . import perfil_comun as PC

MOTIVOS_RAPIDOS = ["No es tuya", "Mala calidad", "Contenido inadecuado", "Duplicada"]


def es_moderador(ctx, al_saber):
    """Pregunta en segundo plano si esta cuenta modera y llama a `al_saber(bool, pendientes)`.
    Pensado para el panel lateral: la entrada «Revisión de música» solo se muestra si es True."""
    social = S.social_de(ctx)
    if social is None:
        al_saber(False, 0)
        return

    def trabajo():
        if not social.soy_moderador():
            return False, 0
        return True, social.revision_contar()
    en_segundo_plano(trabajo, ok=lambda r: al_saber(*r), error=lambda _e: al_saber(False, 0),
                     urgente=True)


class DialogoRechazo(QDialog):
    """El motivo del rechazo, con motivos rápidos."""

    def __init__(self, s, padre=None):
        super().__init__(padre)
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle("Rechazar canción · Caudal")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(10)
        t = QLabel("Rechazar canción")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        v.addWidget(PC.etiqueta(f"«{s.get('titulo', '')}» no se publicará. Quien la subió verá el motivo en "
                                "Subir música.", f"color:{C['texto2']};"))
        fila = PC.FlujoChips()
        self.campo = QLineEdit()
        self.campo.setMaxLength(300)
        self.campo.setPlaceholderText("Motivo (se muestra a quien la subió)")
        for m in MOTIVOS_RAPIDOS:
            b = QPushButton(m)
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, m=m: self.campo.setText(m))
            fila.agregar(b)
        v.addWidget(fila)
        v.addWidget(self.campo)
        self.aviso = PC.etiqueta("", f"color:{C['error']};font-size:12px;", False)
        v.addWidget(self.aviso)
        pie = QHBoxLayout()
        pie.addStretch(1)
        c = QPushButton("Cancelar")
        c.setObjectName("contorno")
        c.clicked.connect(self.reject)
        pie.addWidget(c)
        ok = QPushButton("Rechazar")
        ok.setObjectName("principal")
        ok.clicked.connect(self._ok)
        pie.addWidget(ok)
        v.addLayout(pie)

    def _ok(self):
        if not self.campo.text().strip():
            self.aviso.setText("Escribe un motivo o elige uno de arriba: así sabrá qué corregir.")
            return
        self.accept()

    def motivo(self):
        return self.campo.text().strip()


class TarjetaRevision(QFrame):
    escuchar = Signal(dict)
    aprobar = Signal(dict)
    rechazar = Signal(dict)
    perfil = Signal(str)

    def __init__(self, s, padre=None):
        super().__init__(padre)
        self.s = s
        self.setObjectName("tarjeta_revision")
        self.setStyleSheet(f"QFrame#tarjeta_revision{{background:{C['panel']};border:1px solid {C['borde']};"
                           "border-radius:16px;}")
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 16, 16, 16)
        h.setSpacing(16)
        por = Portada(112, radio=14)
        por.set_url(S.url_musica(s.get("portada")))
        h.addWidget(por, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(PC.etiqueta(s["titulo"], "font-size:17px;font-weight:800;", False))
        partes = [x for x in (s.get("artista"), s.get("album")) if x]
        col.addWidget(PC.etiqueta(" · ".join(partes) or "Artista sin indicar",
                                  f"color:{C['texto2']};font-size:13px;", False))
        quien = QHBoxLayout()
        quien.setSpacing(6)
        quien.addWidget(PC.etiqueta("Subida por", f"color:{C['texto3']};font-size:12px;", False))
        b = QPushButton(f"@{s['usuario']}" + (f" ({s['nombre']})" if s.get("nombre") else ""))
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"QPushButton{{background:transparent;border:none;padding:0;color:{C['acento']};"
                        "font-size:12px;font-weight:700;}QPushButton:hover{text-decoration:underline;}")
        b.clicked.connect(lambda _=False: self.perfil.emit(s["usuario"]))
        quien.addWidget(b)
        quien.addStretch(1)
        col.addLayout(quien)
        datos = []
        if s.get("duracion"):
            datos.append(S.tiempo_corto(s["duracion"]))
        if s.get("tamano"):
            datos.append(f"{s['tamano'] / 1048576:.1f} MB")
        if s.get("creado"):
            datos.append(s["creado"][:10])
        col.addWidget(PC.etiqueta(" · ".join(datos), f"color:{C['texto3']};font-size:12px;", False))
        if s["estado"] == "revision" or s["reportes"]:
            n = s["reportes"]
            col.addWidget(PC.etiqueta(f"Reportada por {n} {'persona' if n == 1 else 'personas'}",
                                      f"color:{C['aviso']};font-size:12.5px;font-weight:800;", False))
            for m in s["motivos"][:4]:
                col.addWidget(PC.etiqueta(f"• {m}", f"color:{C['texto2']};font-size:12px;"))
        else:
            col.addWidget(PC.etiqueta("Canción nueva, esperando su primera revisión",
                                      f"color:{C['texto2']};font-size:12px;", False))
        col.addStretch(1)
        h.addLayout(col, 1)
        acc = QVBoxLayout()
        acc.setSpacing(8)
        acc.addWidget(PC.boton("Escuchar", "contorno", "reproducir", al_pulsar=lambda: self.escuchar.emit(s)))
        self.bt_ok = PC.boton("Aprobar", "principal", "listo", al_pulsar=lambda: self.aprobar.emit(s))
        acc.addWidget(self.bt_ok)
        self.bt_no = PC.boton("Rechazar", "contorno", "cerrar", C["error"], al_pulsar=lambda: self.rechazar.emit(s))
        acc.addWidget(self.bt_no)
        acc.addStretch(1)
        h.addLayout(acc)

    def ocupado(self, si):
        for b in (self.bt_ok, self.bt_no):
            b.setEnabled(not si)


class PaginaRevision(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Revisión de música"
        self.social = S.social_de(ctx)
        self.tarjetas = {}
        self.col = PC.columna_central(self.cuerpo, 920)
        cab = QHBoxLayout()
        t = QLabel("Revisión de música")
        t.setObjectName("titulo_pagina")
        cab.addWidget(t)
        cab.addStretch(1)
        self.bt_actualizar = PC.boton("Actualizar", "contorno", "reintentar", al_pulsar=self.cargar)
        cab.addWidget(self.bt_actualizar)
        self.col.addLayout(cab)
        self.col.addWidget(PC.etiqueta(
            "Escucha cada canción antes de decidir. Si la rechazas, quien la subió verá tu motivo.",
            f"color:{C['texto2']};"))
        self.contador = PC.etiqueta("", f"color:{C['texto3']};font-size:12.5px;font-weight:700;", False)
        self.col.addWidget(self.contador)
        self.caja = QVBoxLayout()
        self.caja.setSpacing(12)
        self.col.addLayout(self.caja)
        self.cuerpo.addStretch(1)
        if self.social is None:
            self.bt_actualizar.hide()
            self._mensaje("candado", "Necesitas tu cuenta", "Abre Caudal con internet e inicia sesión.")
        else:
            self.cargar()

    def _mensaje(self, icono, titulo, texto):
        PC.limpiar(self.caja)
        self.contador.setText("")
        self.caja.addWidget(SinResultados(icono, titulo, texto))

    def cargar(self):
        if self.social is None:
            return
        self.contador.setText("Cargando…")
        social = self.social

        def trabajo():
            if not social.soy_moderador():
                return None
            return social.revision_pendientes(100)
        en_segundo_plano(trabajo, ok=self._pintar,
                         error=lambda e: self._mensaje("aviso", "No se pudo cargar",
                                                       S.explicar(e, "cargar la revisión")),
                         dueno=self, urgente=True)

    def _pintar(self, lista):
        PC.limpiar(self.caja)
        self.tarjetas = {}
        if lista is None:
            self.bt_actualizar.hide()
            self._mensaje("candado", "Esta pantalla es solo para moderación",
                          "Tu cuenta no tiene permiso para revisar música.")
            return
        self._contar(len(lista))
        if not lista:
            self.caja.addWidget(SinResultados("listo", "No hay nada por revisar",
                                              "Cuando alguien suba música o la reporten, aparecerá aquí."))
            return
        for s in lista:
            t = TarjetaRevision(s)
            t.escuchar.connect(lambda s: PC.reproducir_subidas(self.ctx, self.social, [s], 0, self))
            t.aprobar.connect(self._aprobar)
            t.rechazar.connect(self._rechazar)
            t.perfil.connect(lambda u: self.ctx.navegar({"pagina": "perfil", "usuario": u}))
            self.tarjetas[s["id"]] = t
            self.caja.addWidget(t)

    def _contar(self, n):
        self.contador.setText("Nada pendiente" if not n else
                              f"{n} {'canción pendiente' if n == 1 else 'canciones pendientes'}")

    def _aprobar(self, s):
        self._resolver(s, True, "")

    def _rechazar(self, s):
        d = DialogoRechazo(s, self)
        if d.exec() == QDialog.Accepted:
            self._resolver(s, False, d.motivo())

    def _resolver(self, s, aprobar, nota):
        t = self.tarjetas.get(s["id"])
        if t is not None:
            t.ocupado(True)

        def listo(_r):
            PC.aviso(self.ctx, "Canción aprobada: ya está en la comunidad" if aprobar else "Canción rechazada")
            tj = self.tarjetas.pop(s["id"], None)
            if tj is not None:
                self.caja.removeWidget(tj)
                tj.deleteLater()
            n = len(self.tarjetas)
            self._contar(n)
            if not n:
                self.caja.addWidget(SinResultados("listo", "No hay nada por revisar",
                                                  "Cuando alguien suba música o la reporten, aparecerá aquí."))

        def fallo(e):
            if t is not None:
                try:
                    t.ocupado(False)
                except RuntimeError:
                    pass
            PC.aviso(self.ctx, S.explicar(e, "guardar tu decisión"))
        en_segundo_plano(self.social.revision_resolver, s["id"], aprobar, nota, ok=listo, error=fallo,
                         dueno=self, urgente=True)
