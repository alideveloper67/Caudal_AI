# -*- coding: utf-8 -*-
"""Goku Ultra Instinto: de la imagen de la persona (pixel art de IA sin transparencia), recortada con personajes_nov.py y
pixelizada con la skill; se arma con pokemon_exacto.py."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / 'goku_ultra' / 'hoja.png').convert('RGBA')
