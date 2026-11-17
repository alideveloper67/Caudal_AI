# -*- coding: utf-8 -*-
"""totoro: de la imagen de la persona (pixel art de IA), pixelizada con la skill; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'totoro' / 'hoja.png').convert('RGBA')

