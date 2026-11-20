# -*- coding: utf-8 -*-
"""Filas de Ajustes para lo nuevo: la casilla del aviso de errores y el acceso a los logros.

    from ..ajuste_aviso_errores import fila_aviso_errores, fila_logros
    fila_aviso_errores(s)              # s = Seccion("Almacenamiento y privacidad")
    fila_logros(s, ctx, self)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QPushButton

from .. import aviso_errores

TITULO = "Enviar informes de errores"
AYUDA = ("Si Caudal se cierra o falla, manda un informe sin datos personales (versión, sistema, "
         "pantalla y dónde falló) para poder arreglarlo. Va solo a Caudal, sin servicios de terceros.")


def casilla_aviso_errores():
    c = QCheckBox()
    c.setChecked(aviso_errores.activo())
    c.setCursor(Qt.PointingHandCursor)
    c.toggled.connect(aviso_errores.poner_activo)
    return c


def fila_aviso_errores(seccion):
    c = casilla_aviso_errores()
    seccion.fila(TITULO, AYUDA, c)
    return c


def fila_logros(seccion, ctx, padre=None):
    from .logros_ui import abrir_logros, logros_de_ctx
    r = logros_de_ctx(ctx).resumen()
    bt = QPushButton("Ver logros")
    bt.setCursor(Qt.PointingHandCursor)
    bt.clicked.connect(lambda: abrir_logros(ctx, padre))
    seccion.fila("Tus logros", f"{r['conseguidos']} de {r['total']} insignias. Elige cuáles lucir en tu perfil.", bt)
    return bt
