# -*- coding: utf-8 -*-
"""Bulbasaur: extraído exacto de la imagen de la persona; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'bulbasaur' / 'hoja.png').convert('RGBA')
