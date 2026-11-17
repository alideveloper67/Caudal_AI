# -*- coding: utf-8 -*-
"""Zorro aviador: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/zorro_aviador/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'zorro_aviador' / 'hoja.png').convert('RGBA')
