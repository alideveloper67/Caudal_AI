# -*- coding: utf-8 -*-
"""Conejo mago: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/conejo_mago/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'conejo_mago' / 'hoja.png').convert('RGBA')
