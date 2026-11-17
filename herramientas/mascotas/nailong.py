# -*- coding: utf-8 -*-
"""Nailong: de la imagen de la persona (pixel art de IA, fondo negro), pixelizada con la skill; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'nailong' / 'hoja.png').convert('RGBA')

