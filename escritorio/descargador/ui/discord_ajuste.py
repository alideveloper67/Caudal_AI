# -*- coding: utf-8 -*-
"""Ajustes → «Discord»: mostrar o no «Escuchando en Caudal» en tu perfil.

La sección existe siempre que Caudal tenga el ID de su aplicación de Discord
(discord_presencia.ID_APLICACION_DISCORD); si no lo tiene, no se muestra nada."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel

from .paginas.ajustes import Seccion


def _interruptor(valor):
    c = QCheckBox()
    c.setChecked(bool(valor))
    c.setCursor(Qt.PointingHandCursor)
    return c


def seccion_discord(ctx):
    """La tarjeta para Ajustes, o None si la función no está disponible en esta versión."""
    enganche = getattr(ctx, "discord", None)
    if enganche is None or not getattr(enganche, "disponible", False):
        return None
    s = Seccion("Discord")
    nota = QLabel("Si tienes Discord abierto en esta PC, tu perfil muestra «Escuchando en Caudal» con la "
                  "canción, el artista, la carátula y el tiempo. Al pausar se ve «En pausa» y al cerrar "
                  "Caudal se quita. Si no usas Discord, no pasa nada.")
    nota.setWordWrap(True)
    nota.setObjectName("secundario")
    s.v.addWidget(nota)
    activo = _interruptor(enganche.activa)
    activo.toggled.connect(enganche.poner_activa)
    s.fila("Mostrar lo que escucho en Discord", "Lo ven tus amigos y los servidores donde estás.", activo)
    boton = _interruptor(enganche.con_boton)
    boton.toggled.connect(enganche.poner_boton)
    s.fila("Botón «Escuchar en Caudal»", "Un botón en tu perfil que lleva a la web de Caudal.", boton)
    return s
