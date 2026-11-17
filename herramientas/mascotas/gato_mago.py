# -*- coding: utf-8 -*-
"""Gato mago: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/gato_mago/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'gato_mago' / 'hoja.png').convert('RGBA')
