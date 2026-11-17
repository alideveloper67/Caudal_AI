# -*- coding: utf-8 -*-
"""Squirtle: extraído exacto de la imagen de la persona; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'squirtle' / 'hoja.png').convert('RGBA')
