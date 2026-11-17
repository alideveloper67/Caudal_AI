# -*- coding: utf-8 -*-
"""Ovejita: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/oveja/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'oveja' / 'hoja.png').convert('RGBA')
