# -*- coding: utf-8 -*-
"""Integra las 22 mascotas nuevas (v4), deja las que la persona quiere conservar y saca las que pidió borrar.

1. Limpia manchitas sueltas (< 6 px) de cada sprite v4 y rehace su hoja de 4 cuadros.
2. Crea los cargadores <clave>.py de las nuevas.
3. Rehace el catálogo (móvil y escritorio): conservadas + nuevas (cuadros: 4, estela tomada de una parecida).
4. Copia la estela de cada nueva y borra hojas/estelas de las eliminadas en las dos carpetas de arte
   (quedan respaldadas en herramientas/mascotas/v3, frente_v2, anteriores y en CaudalRespaldos).
"""
import json
import shutil
import sys
from collections import deque
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent.parent
ARTE = [RAIZ / "app" / "assets" / "mascotas", RAIZ / "escritorio" / "descargador" / "mascotas"]
RESPALDO = Path.home() / "CaudalRespaldos" / "mascotas-antes-v4"
SKILL = Path.home() / ".claude" / "skills" / "pixel-art-exact" / "scripts"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(AQUI))
import spritelib as S  # noqa: E402
import importar_hoja as I  # noqa: E402

CONSERVAR = ["nyan", "nailong", "pikachu", "kirby", "hellokitty", "doraemon", "totoro", "snoopy", "kuromi", "mymelody",
             "cinnamoroll", "purin", "olaf"]
BORRAR = ["stitch", "minion", "pooh", "mickey", "bob", "patrick", "pusheen", "rilakkuma", "toothless"]
# clave: (nombre, estela, de qué mascota se copia la estela por ahora)
NUEVAS = {
    "zorro_aviador": ("Zorro aviador", "estrella", "nailong"),
    "conejo_mago": ("Conejo mago", "estrella", "nailong"),
    "pinguino": ("Pingüino aviador", "copo", "olaf"),
    "robot": ("Robotín", "rayo", "pikachu"),
    "brote": ("Brotecito", "hoja", "totoro"),
    "gatito": ("Gatita del lazo", "corazon", "hellokitty"),
    "dino": ("Dinito", "hoja", "totoro"),
    "panda": ("Panda", "hoja", "totoro"),
    "raton": ("Ratón explorador", "estrella", "nailong"),
    "oveja": ("Ovejita", "nube", "cinnamoroll"),
    "zorrito": ("Zorrito", "hoja", "totoro"),
    "rana": ("Ranita", "gota", "pooh"),
    "mapache": ("Mapache viajero", "hoja", "totoro"),
    "murcielago": ("Murciélago lunar", "estrella", "stitch"),
    "cacatua": ("Cacatúa", "estrella", "nailong"),
    "nutria": ("Nutria", "burbuja", "bob"),
    "ciervo": ("Cervatillo", "flor", "mymelody"),
    "dragon": ("Dragoncito", "llama", "toothless"),
    "muneco_nieve": ("Muñeco de nieve", "copo", "olaf"),
    "gato_mago": ("Gato mago", "estrella", "nailong"),
    "erizo": ("Erizo", "hoja", "totoro"),
    "ajolote": ("Ajolote", "burbuja", "patrick"),
}

# clave: (nombre, origen, estela) — hoja y estela propias en v4/<clave>/ (las arma su <clave>.py)
# estela: "propia" = v4/<clave>/estela.png; si no, la clave cuya estela se reutiliza (o None = la que ya tiene)
IMPORTADAS = {
    "pikachu": ("Pikachu", "Pokémon", "rayo", None),
    "charmander": ("Charmander", "Pokémon", "llama", "propia"),
    "bulbasaur": ("Bulbasaur", "Pokémon", "hoja", "totoro"),
    "squirtle": ("Squirtle", "Pokémon", "burbuja", "propia"),
    "kuromi": ("Kuromi", "Sanrio", "calavera", None),
    "hellokitty": ("Hello Kitty", "Sanrio", "corazon", None),
    "doraemon": ("Doraemon", "Doraemon", "cascabel", None),
    "purin": ("Pompompurin", "Sanrio", "flan", None),
    "cinnamoroll": ("Cinnamoroll", "Sanrio", "nube", None),
    "mymelody": ("My Melody", "Sanrio", "flor", None),
    "snoopy": ("Snoopy", "Peanuts", "hueso", None),
    "totoro": ("Totoro", "Mi vecino Totoro", "hoja", None),
    "nyan": ("Nyan Cat", "Nyan Cat", "arcoiris", None),
    "olaf": ("Olaf", "Frozen", "copo", None),
    "kirby": ("Kirby", "Kirby", "estrella", None),
    "gato_negro": ("Gato negro", "Caudal", "humo", "propia"),
    "capibara": ("Capibara", "Caudal", "mandarina", "propia"),
    "pochacco": ("Pochacco", "Sanrio", "corazon", "hellokitty"),
    "nailong": ("Nailong", "Nailong", "estrella", None),
    "caniche": ("Brawncito", "Exclusiva de cochayuyo", "huella", "propia"),
}

# mascotas exclusivas de unas cuentas [(id de la cuenta en la nube, usuario solo para leerlo)]:
# solo esas cuentas la ven y la pueden elegir, aunque no sean donadoras
SOLO_CUENTAS = {
    "caniche": [("1b489a46-df0e-4601-879c-cff3e3f34ae1", "cochayuyo"),
                ("fe27d3fb-28b3-4894-836c-5b773a228007", "aliceo"),          # fundador
                ("7a7f61d4-b736-4826-bcf2-891ee68ba0f2", "aliceoapp")],      # fundador
}

CARGADOR = '''# -*- coding: utf-8 -*-
"""{nombre}: mascota original (hoja de la persona), pixelizada con la skill pixel-art-exact. Fuente en v4/{clave}/."""
from pathlib import Path

from PIL import Image


def hojas():
    return Image.open(Path(__file__).parent / 'v4' / '{clave}' / 'hoja.png').convert('RGBA')
'''


def limpiar_manchitas(sprite_py, minimo=6 * I.DENSIDAD ** 2):
    sp = S.load(str(sprite_py))
    rows = [list(r) for r in sp["rows"]]
    h, w = len(rows), len(rows[0])
    visto = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if rows[y][x] != sp["bg"] and not visto[y][x]:
                q = deque([(y, x)])
                visto[y][x] = True
                pts = []
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and not visto[ny][nx] and rows[ny][nx] != sp["bg"]:
                                visto[ny][nx] = True
                                q.append((ny, nx))
                comps.append(pts)
    if len(comps) <= 1:
        return 0
    mayor = max(len(c) for c in comps)
    quitados = 0
    for c in comps:
        if len(c) < minimo and len(c) < mayor:
            for y, x in c:
                rows[y][x] = sp["bg"]
                quitados += 1
    if quitados:
        filas = S.crop_rows(["".join(r) for r in rows], sp["bg"])
        S.save(str(sprite_py), filas, sp["palette"], bg=sp["bg"])
    return quitados


def main():
    # 1) limpieza y hojas
    for c in NUEVAS:
        d = AQUI / "v4" / c
        q = limpiar_manchitas(d / "sprite.py")
        I.rebote4(d / "sprite.py", d)
        if q:
            print(f"{c}: {q} píxel(es) sueltos quitados")
    # 2) cargadores
    for c, (nombre, _, _) in NUEVAS.items():
        (AQUI / f"{c}.py").write_text(CARGADOR.format(nombre=nombre, clave=c), encoding="utf-8")
    eliminadas = AQUI / "eliminadas"
    eliminadas.mkdir(exist_ok=True)
    for c in BORRAR:
        p = AQUI / f"{c}.py"
        if p.exists():
            shutil.move(str(p), str(eliminadas / p.name))
    # 3 y 4) catálogo, estelas y borrado, en las dos carpetas de arte
    for arte in ARTE:
        viejo = {m["clave"]: m for m in json.loads((arte / "catalogo.json").read_text(encoding="utf-8"))}
        respaldo = RESPALDO / ("app" if arte == ARTE[0] else "escritorio")
        for m in json.loads((respaldo / "catalogo.json").read_text(encoding="utf-8")):
            viejo.setdefault(m["clave"], m)
        nuevo = [viejo[c] for c in CONSERVAR if c in viejo]
        for c in CONSERVAR:
            for nombre in (f"{c}.png", f"estela_{c}.png"):
                if not (arte / nombre).exists() and (respaldo / nombre).exists():
                    shutil.copy(respaldo / nombre, arte / nombre)
        for c, (nombre, estela, fuente) in NUEVAS.items():
            base = viejo.get(fuente, {})
            nuevo.append({
                "clave": c, "nombre": nombre, "origen": "Caudal", "ancho": 48, "alto": 44, "arcoiris": False,
                "estela": estela, "estela_colores": base.get("estela_colores", []),
                "estela_ancho": base.get("estela_ancho", 11), "estela_alto": base.get("estela_alto", 11), "cuadros": 4,
                "densidad": I.DENSIDAD,
            })
            origen = arte / f"estela_{fuente}.png"
            if not origen.exists():
                origen = respaldo / f"estela_{fuente}.png"
            if origen.exists():
                shutil.copy(origen, arte / f"estela_{c}.png")
            shutil.copy(AQUI / "v4" / c / "hoja.png", arte / f"{c}.png")
        import pokemon_exacto as P
        # las que ya estaban en el catálogo conservan su lugar; las nuevas entran tras Pikachu
        ya = {m["clave"]: i for i, m in enumerate(nuevo)}
        lugar = {c: ya[c] for c in IMPORTADAS if c in ya and c not in ("pikachu",)}
        pos = max(0, next((i for i, m in enumerate(nuevo) if m["clave"] == "pikachu"), 0))
        nuevo = [m if m["clave"] not in lugar else {"clave": "__" + m["clave"]} for m in nuevo]
        nuevo = [m for m in nuevo if m["clave"] not in IMPORTADAS]
        for c, (nombre, origen_, estela, fuente_estela) in IMPORTADAS.items():
            d = AQUI / "v4" / c
            ancho, alto = P.POKEMON[c]["cuadro"]
            entrada = {"clave": c, "nombre": nombre, "origen": origen_, "ancho": ancho, "alto": alto, "arcoiris": estela == "arcoiris",
                       "estela": estela, "estela_colores": [], "estela_ancho": 11, "estela_alto": 11, "cuadros": 4,
                       "densidad": I.DENSIDAD}
            if c in SOLO_CUENTAS:
                entrada["solo_cuentas"] = [i for i, _ in SOLO_CUENTAS[c]]
                entrada["solo_usuarios"] = [u for _, u in SOLO_CUENTAS[c]]
            hueco = next((i for i, m in enumerate(nuevo) if m["clave"] == "__" + c), None)
            if hueco is not None:
                nuevo[hueco] = entrada
            else:
                nuevo.insert(pos, entrada)
                pos += 1
            shutil.copy(d / "hoja.png", arte / f"{c}.png")
            if fuente_estela == "propia":
                shutil.copy(d / "estela.png", arte / f"estela_{c}.png")
            elif fuente_estela:
                shutil.copy(arte / f"estela_{fuente_estela}.png", arte / f"estela_{c}.png")
        for c in BORRAR:
            for f in (arte / f"{c}.png", arte / f"estela_{c}.png"):
                if f.exists():
                    f.unlink()
        (arte / "catalogo.json").write_text(json.dumps(nuevo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(arte, "->", len(nuevo), "mascotas")


if __name__ == "__main__":
    main()
