# -*- coding: utf-8 -*-
"""Mapache viajero: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/mapache/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'mapache' / 'hoja.png').convert('RGBA')
