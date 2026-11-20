# -*- coding: utf-8 -*-
"""El color del nombre de los demás (donadores): se pide al servidor en tandas y se recuerda.

Cada etiqueta de nombre (perfil, chats, «Juntos») pregunta `color_de(usuario)`. Si no se sabe todavía, el
usuario se apunta y, un instante después, se piden todos los apuntados en UNA sola llamada
(`colores_nombre`, supabase/donadores_extra.sql) en segundo plano. Al llegar se avisa con `cambiado` y las
etiquetas se repintan solas. Lo que no tiene color también se recuerda (no se vuelve a preguntar).

El propio color no se pide: sale del gestor premium (se ve al instante al elegirlo). Si la base todavía no
tiene la función, no pasa nada: los nombres se ven como siempre."""

import time

from PySide6.QtCore import QObject, QTimer, Signal

from . import social as S
from .hilos import en_segundo_plano
from .premium_datos import color_valido

ESPERA_MS = 60
OLVIDAR_S = 15 * 60          # pasado este rato se vuelve a preguntar (alguien pudo cambiar su color)


class GestorColores(QObject):
    cambiado = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self._cache = {}          # usuario -> (color o None, cuándo se supo)
        self._pendientes = set()
        self._pidiendo = False
        self._cuenta = None
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(ESPERA_MS)
        self._t.timeout.connect(self._pedir)
        premium = getattr(ctx, "premium", None)
        if premium is not None:
            premium.cambiado.connect(self.cambiado.emit)      # mi propio color cambió

    def _mi_cuenta(self):
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        return cuenta

    def _revisar_cuenta(self):
        """Otra cuenta (o sin sesión): se olvida todo lo sabido."""
        c = self._mi_cuenta()
        clave = (str(c.get("usuario") or "").lower(), id(c.get("sesion")))
        if clave != self._cuenta:
            self._cuenta = clave
            self._cache.clear()
            self._pendientes.clear()

    def color_de(self, usuario):
        """El color vigente de `usuario` ('#RRGGBB') o None. Si no se sabe, se pide (y llega con `cambiado`)."""
        u = str(usuario or "").strip().lstrip("@").lower()
        if not u:
            return None
        self._revisar_cuenta()
        if u == self._cuenta[0]:
            premium = getattr(self.ctx, "premium", None)
            return premium.color_efectivo() if premium is not None else None
        dato = self._cache.get(u)
        if dato is not None and time.monotonic() - dato[1] < OLVIDAR_S:
            return dato[0]
        if self._mi_cuenta().get("sesion") is not None:
            self._pendientes.add(u)
            if not self._t.isActive() and not self._pidiendo:
                self._t.start()
        return dato[0] if dato is not None else None

    def _pedir(self):
        sesion = self._mi_cuenta().get("sesion")
        if sesion is None or not self._pendientes or self._pidiendo:
            return
        lote = sorted(self._pendientes)[:200]
        self._pendientes.difference_update(lote)
        try:
            social = S.Social(sesion)
        except Exception:  # noqa: BLE001 - una sesión rara: los nombres se ven como siempre
            return
        self._pidiendo = True
        cuenta = self._cuenta

        def listo(colores):
            self._pidiendo = False
            if cuenta != self._cuenta:
                return
            ahora = time.monotonic()
            for u in lote:
                self._cache[u] = (color_valido((colores or {}).get(u)), ahora)
            if self._pendientes:
                self._t.start()
            if any(self._cache[u][0] for u in lote):
                self.cambiado.emit()

        def fallo(_e):
            # sin red o sin la función en la base: se recuerda «sin color» un rato, sin insistir
            self._pidiendo = False
            ahora = time.monotonic()
            for u in lote:
                self._cache.setdefault(u, (None, ahora))
            if self._pendientes:
                self._t.start()
        en_segundo_plano(social.colores_nombre, lote, ok=listo, error=fallo, dueno=self)

    def olvidar(self):
        self._cache.clear()
        self._pendientes.clear()


def gestor(ctx):
    """El gestor de colores de esta ventana (se crea la primera vez que se pide)."""
    g = getattr(ctx, "_colores_nombre", None)
    if g is None:
        g = GestorColores(ctx)
        try:
            ctx._colores_nombre = g
        except Exception:  # noqa: BLE001
            pass
    return g
