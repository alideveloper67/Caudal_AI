# -*- coding: utf-8 -*-
"""Cacatúa: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/cacatua/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'cacatua' / 'hoja.png').convert('RGBA')
