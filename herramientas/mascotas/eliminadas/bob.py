from pathlib import Path
from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v3' / 'bob' / 'hoja.png').convert('RGBA')
