# -*- coding: utf-8 -*-
"""Mira cada pocos segundos por dónde sale el sonido (audífonos, parlante, bluetooth) y, si cambió y
esa salida tiene un ajuste del ecualizador avanzado asignado, lo pone solo (donadores y fundadores)."""

from PySide6.QtCore import QObject, QTimer, Signal

from .. import eq_avanzado, salida_audio


class VigiaSalida(QObject):
    cambio = Signal(str)          # tipo de salida nuevo

    CADA_MS = 3000

    def __init__(self, ctx, leer=None, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self._leer = leer or salida_audio.salida_actual
        self.tipo = None
        self.nombre = ""
        self._reloj = QTimer(self)
        self._reloj.setInterval(self.CADA_MS)
        self._reloj.timeout.connect(self.mirar)

    def iniciar(self):
        self.mirar()
        self._reloj.start()

    def _premium(self):
        g = getattr(self.ctx, "premium", None)
        return bool(g is not None and g.premium)

    def mirar(self):
        datos = self._leer()
        if not datos:
            return
        antes, ahora = self.tipo, datos.get("tipo")
        self.nombre = datos.get("nombre") or ""
        if ahora == antes:
            return
        self.tipo = ahora
        self.cambio.emit(ahora or "")
        puesto = eq_avanzado.al_cambiar_salida(self.ctx.ajustes, self._premium(), antes, ahora)
        if puesto:
            self.ctx.ajustes.guardar()
            self.ctx.reproductor.aplicar_sonido()
            self.ctx.sonido_cambio.emit()
            self.ctx.aviso.emit(f"Suena por {salida_audio.NOMBRES_TIPO.get(ahora, ahora).lower()}: "
                                f"ecualizador «{puesto}»")
