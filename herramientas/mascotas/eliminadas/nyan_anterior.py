from pathlib import Path
from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v3' / 'nyan' / 'hoja.png').convert('RGBA')
