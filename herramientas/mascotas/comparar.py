import importlib.util, sys
from pathlib import Path
from PIL import Image, ImageDraw
AQUI = Path('.').resolve()
sys.path.insert(0, str(AQUI))
import pix

def cargar(ruta, nombre):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

claves = sorted(p.stem for p in (AQUI/'anteriores').glob('*.py') if p.stem not in ('pikachu',))
filas = []
for c in claves:
    pares = []
    for etiqueta, ruta in (('antes (perfil)', AQUI/'anteriores'/f'{c}.py'), ('ahora (frente)', AQUI/f'{c}.py')):
        pix.W = 48
        try:
            h = cargar(ruta, f'm_{etiqueta[:2]}_{c}').hojas()
            cw = h.width // 2
            pares.append((etiqueta, h.crop((0, 0, cw, h.height))))
        except Exception as e:
            pares.append((etiqueta, Image.new('RGBA', (48, 44))))
        finally:
            pix.W = 48
    filas.append((c, pares))
E = 4; cw = 60 * E; ch = 44 * E + 16
cols = 4  # 2 personajes por fila (antes/ahora cada uno)
n = len(filas); r = (n + 1) // 2
img = Image.new('RGBA', (cw * 4 + 20, ch * r + 10), (30, 34, 46, 255))
d = ImageDraw.Draw(img)
for i, (c, pares) in enumerate(filas):
    bx = (i % 2) * cw * 2 + 10; by = (i // 2) * ch + 8
    for j, (et, im) in enumerate(pares):
        x = bx + j * cw
        d.text((x, by - 2), f'{c} - {et}', fill=(190, 200, 220))
        img.alpha_composite(im.resize((im.width * E, im.height * E), Image.NEAREST), (x, by + 12))
out = AQUI / 'vista' / 'comparacion.png'; img.save(out); print(out, img.size)
