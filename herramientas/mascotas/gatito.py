# -*- coding: utf-8 -*-
"""Gatita del lazo: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/gatito/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'gatito' / 'hoja.png').convert('RGBA')
