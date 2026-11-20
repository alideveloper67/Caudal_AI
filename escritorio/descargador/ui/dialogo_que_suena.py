# -*- coding: utf-8 -*-
"""«¿Qué suena?»: escuchar 10 segundos, reconocer la canción y abrirla en Caudal."""

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QVBoxLayout)

from .. import que_suena as Q
from ..hilos import en_segundo_plano
from .componentes import Portada
from .estilos import C, hoja


class DialogoQueSuena(QDialog):
    """`api` (pruebas): dict con disponible, grabar_wav, reconocer, buscar_en_caudal."""

    def __init__(self, ctx, padre=None, api=None, en_fondo=None):
        super().__init__(padre)
        self.ctx = ctx
        self.api = api or {"disponible": Q.disponible, "grabar_wav": Q.grabar_wav,
                           "reconocer": Q.reconocer, "buscar_en_caudal": Q.buscar_en_caudal}
        self._en_fondo = en_fondo or (lambda f, *a, ok=None, error=None:
                                      en_segundo_plano(f, *a, ok=ok, error=error, dueno=self))
        self.resultado = None
        self.pista = None
        self._cancelar = threading.Event()
        self.setWindowTitle("¿Qué suena? · Caudal")
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja())
        self.setMinimumWidth(460)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(12)
        t = QLabel("¿Qué suena?")
        t.setObjectName("titulo_pagina")
        v.addWidget(t)
        self.et_texto = QLabel("Acerca la PC a la música y toca «Escuchar»: en 10 segundos te decimos qué canción es.")
        self.et_texto.setObjectName("secundario")
        self.et_texto.setWordWrap(True)
        v.addWidget(self.et_texto)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(6)
        self.barra.hide()
        v.addWidget(self.barra)

        # tarjeta del resultado
        self.tarjeta = QFrame()
        self.tarjeta.setObjectName("caja")
        ht = QHBoxLayout(self.tarjeta)
        ht.setContentsMargins(14, 12, 14, 12)
        ht.setSpacing(14)
        self.portada = Portada(84, radio=10)
        ht.addWidget(self.portada)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.et_titulo = QLabel("")
        self.et_titulo.setWordWrap(True)
        self.et_titulo.setStyleSheet("font-size:18px;font-weight:900;background:transparent;")
        col.addWidget(self.et_titulo)
        self.et_artista = QLabel("")
        self.et_artista.setWordWrap(True)
        self.et_artista.setStyleSheet(f"color:{C['texto2']};background:transparent;")
        col.addWidget(self.et_artista)
        col.addStretch(1)
        ht.addLayout(col, 1)
        self.tarjeta.hide()
        v.addWidget(self.tarjeta)

        fila = QHBoxLayout()
        self.bt_reproducir = self._boton("Reproducir", "principal", self._reproducir)
        self.bt_cola = self._boton("Añadir a la cola", "contorno", self._a_la_cola)
        self.bt_buscar = self._boton("Buscar en Caudal", "contorno", self._buscar)
        for b in (self.bt_reproducir, self.bt_cola, self.bt_buscar):
            b.hide()
            fila.addWidget(b)
        fila.addStretch(1)
        v.addLayout(fila)

        abajo = QHBoxLayout()
        abajo.addStretch(1)
        self.bt_escuchar = self._boton("Escuchar", "principal", self._escuchar)
        self.bt_escuchar.setEnabled(False)
        abajo.addWidget(self.bt_escuchar)
        v.addLayout(abajo)

        self._reloj = QTimer(self)
        self._reloj.setInterval(100)
        self._reloj.timeout.connect(self._avanzar)
        self._pasos = 0
        self._intentos = 0

        self.et_texto.setText("Comprobando…")
        self._en_fondo(self.api["disponible"], ok=self._al_disponible, error=lambda _e: self._al_disponible(False))

    def _boton(self, texto, nombre, f):
        b = QPushButton(texto)
        b.setObjectName(nombre)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(f)
        return b

    # ------------------------------------------------------------ pasos
    def _al_disponible(self, si):
        if not si:
            self.et_texto.setText(Q.NO_DISPONIBLE)
            self.bt_escuchar.setEnabled(False)
            return
        self.et_texto.setText("Acerca la PC a la música y toca «Escuchar»: en 10 segundos te decimos qué canción es.")
        self.bt_escuchar.setEnabled(True)

    def _escuchar(self):
        self._cancelar.clear()
        self.resultado = self.pista = None
        self.tarjeta.hide()
        for b in (self.bt_reproducir, self.bt_cola, self.bt_buscar):
            b.hide()
        self.bt_escuchar.setEnabled(False)
        self.bt_escuchar.setText("Escuchando…")
        self.et_texto.setText("Escuchando… deja que suene la música.")
        self.barra.setValue(0)
        self.barra.show()
        self._pasos = 0
        self._intentos += 1
        self._reloj.start()
        self._en_fondo(lambda: self.api["grabar_wav"](Q.SEGUNDOS, cancelar=self._cancelar),
                       ok=self._grabado, error=self._fallo)

    def _avanzar(self):
        self._pasos += 1
        self.barra.setValue(min(100, int(self._pasos * 100 / (Q.SEGUNDOS * 10))))

    def _grabado(self, wav):
        self._reloj.stop()
        if not wav:
            return self._listo_para_otra()
        self.barra.setRange(0, 0)          # ocupado, sin porcentaje
        self.et_texto.setText("Reconociendo…")
        self._en_fondo(self.api["reconocer"], wav, ok=self._reconocido, error=self._fallo)

    def _reconocido(self, r):
        self.barra.setRange(0, 100)
        self.barra.hide()
        self._listo_para_otra()
        if not r or not r.get("encontrada"):
            self.et_texto.setText("No la reconocimos. Acércate a la música y prueba otra vez.")
            return
        self.resultado = r
        self.et_texto.setText("¡La encontramos!")
        self.et_titulo.setText(r["titulo"])
        extra = " · ".join(x for x in (r.get("album"), r.get("anio")) if x)
        self.et_artista.setText(r["artista"] + (f"\n{extra}" if extra else ""))
        self.portada.set_url(r.get("portada") or "")
        self.tarjeta.show()
        self.bt_buscar.show()
        self._en_fondo(self.api["buscar_en_caudal"], r, ok=self._con_pista, error=lambda _e: None)

    def _con_pista(self, pista):
        self.pista = pista
        if pista:
            if not (self.resultado or {}).get("portada"):
                self.portada.set_url(pista.get("miniatura") or "")
            self.bt_reproducir.show()
            self.bt_cola.show()

    def _fallo(self, e):
        self._reloj.stop()
        self.barra.setRange(0, 100)
        self.barra.hide()
        self._listo_para_otra()
        self.et_texto.setText(str(e) if isinstance(e, Q.ErrorQueSuena)
                              else "No se pudo reconocer ahora. Vuelve a probar.")

    def _listo_para_otra(self):
        self.bt_escuchar.setEnabled(True)
        self.bt_escuchar.setText("Escuchar otra vez" if self._intentos else "Escuchar")

    # ------------------------------------------------------------ acciones
    def _reproducir(self):
        if self.pista:
            self.ctx.reproductor.reproducir_pista(self.pista)
            self.accept()

    def _a_la_cola(self):
        if self.pista:
            self.ctx.reproductor.agregar_a_cola([self.pista])
            self.bt_cola.setEnabled(False)
            self.bt_cola.setText("En la cola")

    def _buscar(self):
        if self.resultado:
            navegar = getattr(self.ctx, "navegar", None)
            if navegar:
                navegar({"pagina": "buscar", "q": self.resultado["consulta"]})
            self.accept()

    def done(self, r):
        self._cancelar.set()
        self._reloj.stop()
        super().done(r)


def abrir_que_suena(ctx, padre=None):
    d = DialogoQueSuena(ctx, padre or getattr(ctx, "ventana", None))
    d.exec()
    return d
