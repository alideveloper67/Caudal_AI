# -*- coding: utf-8 -*-
"""Paleta y hoja de estilos de Caudal.

Oscuro y profundo, con un solo acento (el cian del icono) y superficies que se
separan por luz, no por bordes. Los nombres de color antiguos se conservan
porque los usan el navegador, el panel del telefono y el actualizador.
"""

C = {
    "fondo":       "#06070A",   # entre paneles
    "panel":       "#101217",   # paneles principales
    "superficie":  "#14171D",
    "superficie2": "#1B1F27",
    "superficie3": "#252A35",
    "hover":       "#1F232C",
    "borde":       "#222731",
    "borde_claro": "#363D4B",
    "texto":       "#F3F5F9",
    "texto2":      "#A9B1C0",
    "texto3":      "#8993A6",   # antes #6F788A: con 4,4:1 de contraste cansaba la vista; ahora 6:1
    "acento":      "#22D3EE",
    "acento_alto": "#67E8F9",
    "acento_bajo": "#0EA5C6",
    "acento_texto": "#03222B",
    "violeta":     "#7C5CFF",
    "exito":       "#2BD576",
    "error":       "#F2555A",
    "aviso":       "#F5A524",
    "cian":        "#6366F1",
}

# Los colores y fondos que se pueden elegir (los mismos que en el teléfono).
# nombre -> (etiqueta, acento, alto, bajo, texto sobre el acento)
ACENTOS = {
    "cian": ("Cian", "#22D3EE", "#67E8F9", "#0EA5C6", "#03222B"),
    "violeta": ("Violeta", "#8B6CFF", "#B4A1FF", "#6D4FE6", "#14093D"),
    "rosa": ("Rosa", "#FF5C8A", "#FF93B1", "#E63E6E", "#3D0716"),
    "verde": ("Verde", "#2BD576", "#6EE7A3", "#1FAF5E", "#032412"),
    "naranja": ("Naranja", "#FF8A3D", "#FFB27F", "#E56F20", "#3A1600"),
    "rojo": ("Rojo", "#F2555A", "#F78A8D", "#D63A40", "#3B0608"),
    "azul": ("Azul", "#4C8DFF", "#8DB5FF", "#2F6FE0", "#051A40"),
    "dorado": ("Dorado", "#F5C542", "#F9DB85", "#D9A91E", "#332400"),
}
# nombre -> (etiqueta, fondo, panel, superficie, superficie2, superficie3, hover, borde)
FONDOS = {
    "oscuro": ("Oscuro", "#06070A", "#101217", "#14171D", "#1B1F27", "#252A35", "#1F232C", "#222731"),
    "negro": ("Negro puro", "#000000", "#0A0A0A", "#101010", "#171717", "#222222", "#1A1A1A", "#1C1C1C"),
    "noche": ("Azul noche", "#070B18", "#0E1426", "#131A30", "#1A2340", "#243052", "#1C2644", "#1F2946"),
    "uva": ("Morado", "#0D0716", "#160E24", "#1C122E", "#251A3B", "#32244E", "#281C40", "#2B2042"),
    "bosque": ("Bosque", "#050D0A", "#0C1813", "#111F19", "#172A22", "#20372D", "#1A2D25", "#1C3027"),
    "grafito": ("Grafito", "#121316", "#1A1C20", "#202227", "#282B31", "#33373E", "#2B2E34", "#2E3138"),
}

# Fondos con personaje: la paleta teñida con sus colores, su acento (se pone al elegirlo) y un mosaico
# tenue con su dibujito detrás de toda la app (descargador/fondos/<clave>.png, densidad 2).
# Las capas las calcula herramientas/mascotas/fondos_tematicos.py (las mismas que el teléfono).
TEMAS = {
    "hellokitty": ("Hello Kitty", "#FF4D6D", "#1C0A10", "#241318", "#2A191E", "#302026", "#3C2C31", "#35252A", "#37272D"),
    "kuromi": ("Kuromi", "#FF77B7", "#120A1C", "#1A1324", "#20192A", "#272030", "#332C3C", "#2C2535", "#2E2737"),
    "pikachu": ("Pikachu", "#F5D142", "#17130A", "#1F1B13", "#252119", "#2C2820", "#37342C", "#312D25", "#332F27"),
    "charmander": ("Charmander", "#FF8A3D", "#1A0D07", "#221510", "#281C16", "#2F231D", "#3A2F2A", "#332822", "#352A25"),
    "squirtle": ("Squirtle", "#5EC8E5", "#071420", "#101C28", "#16222D", "#1D2934", "#2A353F", "#222E39", "#25303B"),
    "bulbasaur": ("Bulbasaur", "#5FD3A0", "#061712", "#0F1F1A", "#152520", "#1C2C27", "#293733", "#21312C", "#24332E"),
    "snoopy": ("Snoopy", "#E8403F", "#111215", "#191A1D", "#1F2023", "#26272A", "#323336", "#2B2C2F", "#2E2E31"),
    "totoro": ("Totoro", "#8CCB6E", "#0E1210", "#161A18", "#1C201E", "#242726", "#303331", "#292C2A", "#2B2E2D"),
    "mymelody": ("My Melody", "#FF6FA5", "#1C0A16", "#24131E", "#2A1924", "#30202B", "#3C2C37", "#352530", "#372732"),
    "purin": ("Pompompurin", "#F7C948", "#181306", "#201B0F", "#262115", "#2D281C", "#383429", "#312D21", "#342F24"),
    "cinnamoroll": ("Cinnamoroll", "#7FB8FF", "#0A1324", "#131B2C", "#192131", "#202838", "#2C3443", "#252D3C", "#272F3E"),
    "kirby": ("Kirby", "#FF8FB8", "#1C0B16", "#24141E", "#2A1A24", "#30212B", "#3C2D37", "#352630", "#372832"),
    "doraemon": ("Doraemon", "#2E8BFF", "#06111F", "#0F1927", "#151F2C", "#1C2633", "#29323E", "#212B38", "#242E3A"),
    "olaf": ("Olaf", "#8ECDF5", "#0A1520", "#131D28", "#19232D", "#202A34", "#2C363F", "#252F39", "#27313B"),
    "nyan": ("Nyan Cat", "#FF7AC8", "#0B0E2C", "#141633", "#1A1C39", "#21243F", "#2D304A", "#262943", "#282B45"),
    "capibara": ("Capibara", "#FFA53D", "#1A1008", "#221811", "#281E17", "#2F261E", "#3A312B", "#332A23", "#352D26"),
    "pochacco": ("Pochacco", "#FF3D86", "#1A0A12", "#22131A", "#281920", "#2F2027", "#3A2C33", "#33252C", "#35272E"),
    "nailong": ("Nailong", "#FFD23F", "#181406", "#201C0F", "#262215", "#2D291C", "#383529", "#312E21", "#343024"),
    "gato_negro": ("Gato negro", "#7BD88F", "#0F0F12", "#17171A", "#1D1D20", "#252527", "#313133", "#29292C", "#2C2C2E"),
}
FONDOS.update({k: (v[0],) + v[2:] for k, v in TEMAS.items()})


def es_tema(valor):
    return valor in TEMAS


def acento_de_tema(valor):
    """El acento que acompaña a un fondo con personaje ("" si no es uno de ellos)."""
    return TEMAS[valor][1] if valor in TEMAS else ""


def ruta_patron(valor):
    """El mosaico del fondo con personaje (o None)."""
    if valor not in TEMAS:
        return None
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "fondos" / f"{valor}.png"
    return p if p.exists() else None


def patron_actual():
    return ruta_patron(ACTUAL.get("fondo"))


# tamaño base de la letra: la ventana lo adapta (más chica en pantallas pequeñas, más grande en las enormes)
ESCALA = {"base": 13}


# lo que se está viendo ahora mismo (lo que se aplicó al arrancar)
ACTUAL = {"acento": "cian", "fondo": "oscuro"}


def _rgb(hexa):
    h = str(hexa or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(c))) for c in rgb)


def _mezcla(a, b, t):
    """De a hacia b (t = 0 → a, t = 1 → b)."""
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _luz(rgb):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def es_color(valor):
    """True si es un color propio (#RRGGBB) y no uno de la lista."""
    return str(valor or "").startswith("#") and _rgb(valor) is not None


def acento_de(valor):
    """(etiqueta, acento, alto, bajo, texto) de un acento de la lista o de un color propio."""
    if valor in ACENTOS:
        return ACENTOS[valor]
    rgb = _rgb(valor) if es_color(valor) else None
    if rgb is None:
        return ACENTOS["cian"]
    # un acento demasiado oscuro no se ve sobre el fondo: se aclara lo justo
    while _luz(rgb) < 0.10:
        rgb = _mezcla(rgb, (255, 255, 255), 0.12)
    alto = _mezcla(rgb, (255, 255, 255), 0.35)
    bajo = _mezcla(rgb, (0, 0, 0), 0.18)
    # texto encima del acento: oscuro teñido del mismo color, o blanco si el acento es oscuro
    texto = _mezcla(rgb, (0, 0, 0), 0.85) if _luz(rgb) > 0.22 else (255, 255, 255)
    return ("Tu color", _hex(rgb), _hex(alto), _hex(bajo), _hex(texto))


def fondo_de(valor):
    """(etiqueta, fondo, panel, superficie, superficie2, superficie3, hover, borde)."""
    if valor in FONDOS:
        return FONDOS[valor]
    rgb = _rgb(valor) if es_color(valor) else None
    if rgb is None:
        return FONDOS["oscuro"]
    # el fondo siempre oscuro (el texto es claro): se baja la luz si hace falta
    while _luz(rgb) > 0.035:
        rgb = _mezcla(rgb, (0, 0, 0), 0.15)
    blanco = (255, 255, 255)
    capas = [_mezcla(rgb, blanco, t) for t in (0.0, 0.035, 0.06, 0.09, 0.14, 0.11, 0.12)]
    return ("Tu fondo",) + tuple(_hex(c) for c in capas)


def aplicar_aspecto(acento, fondo):
    """Cambia la paleta. Se llama al arrancar, antes de construir la ventana.
    Acepta los nombres de la lista (los mismos del teléfono) o un color propio #RRGGBB."""
    ACTUAL["acento"], ACTUAL["fondo"] = acento, fondo
    a = acento_de(acento)
    C.update(acento=a[1], acento_alto=a[2], acento_bajo=a[3], acento_texto=a[4])
    f = fondo_de(fondo)
    C.update(fondo=f[1], panel=f[2], superficie=f[3], superficie2=f[4], superficie3=f[5],
             hover=f[6], borde=f[7])


# «Fondo de Caudal»: mientras haya una imagen de fondo, paneles y tarjetas se vuelven
# translúcidos (cuánto, aquí). Sin fondo, la hoja de estilos no cambia nada.
FONDO = {"activo": False}
ALFA_PANEL = 0.34        # barra lateral, centro y panel derecho
ALFA_BARRA = 0.66        # barra del reproductor
ALFA_TARJETA = 0.86      # tarjetas y filas: siguen leyéndose bien


def rgba(hexa, alfa):
    r, g, b = _rgb(hexa) or (0, 0, 0)
    return f"rgba({r}, {g}, {b}, {alfa})"


def hoja_fondo():
    """Lo que cambia en la hoja cuando hay fondo (va al final para ganar a lo anterior)."""
    return f"""
QFrame#panel_izq, QFrame#panel_centro, QFrame#panel_der, QFrame#panel_nav {{
    background: {rgba(C['panel'], ALFA_PANEL)};
}}
QFrame#reproductor {{
    background: {rgba(C['fondo'], ALFA_BARRA)};
}}
QFrame#tarjeta, QFrame#panel, QFrame#caja, QFrame#tarjeta_album, QFrame#cabecera {{
    background: {rgba(C['superficie'], ALFA_TARJETA)};
}}
QFrame#tarjeta:hover {{
    background: {rgba(C['superficie2'], 0.92)};
}}
QFrame#cabecera_nav {{
    background: {rgba(C['panel'], ALFA_PANEL)};
}}
QLineEdit#buscador {{
    background: {rgba(C['superficie2'], 0.78)};
}}
QLineEdit#buscador:hover, QLineEdit#buscador:focus {{
    background: {rgba(C['superficie3'], 0.92)};
}}
QPushButton#chip, QPushButton#filtro, QPushButton#redondo {{
    background: {rgba(C['superficie2'], 0.82)};
}}
QPushButton#chip:checked, QPushButton#filtro:checked {{
    background: {C['texto']};
}}
"""


FUENTE = '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'
FUENTE_TITULO = '"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'


def hoja(flechas=None):
    flechas = flechas or {}
    fl_abajo = flechas.get("abajo", "")
    fl_arriba = flechas.get("arriba", "")
    img_abajo = f"image: url({fl_abajo});" if fl_abajo else "image: none;"
    img_arriba = f"image: url({fl_arriba});" if fl_arriba else "image: none;"
    return f"""
* {{
    font-family: {FUENTE};
    outline: none;
}}
QWidget#raiz {{
    background: {C['fondo']};
}}
QWidget {{
    color: {C['texto']};
    font-size: {ESCALA['base']}px;
}}
QToolTip {{
    background: {C['superficie3']};
    color: {C['texto']};
    border: 1px solid {C['borde_claro']};
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
}}

/* ---------- marcos principales ---------- */
QFrame#panel_izq, QFrame#panel_centro, QFrame#panel_der, QFrame#panel_nav {{
    background: {C['panel']};
    border: none;
    border-radius: 10px;
}}
QFrame#barra_superior {{
    background: transparent;
}}
QFrame#reproductor {{
    background: {C['fondo']};
    border: none;
}}

/* ---------- campos ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {C['superficie2']};
    border: 1px solid {C['borde']};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {C['acento']};
    selection-color: {C['acento_texto']};
}}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {C['borde_claro']};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border: 1px solid {C['acento']};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {C['texto3']};
    background: {C['superficie']};
}}
QLineEdit#buscador {{
    background: {C['superficie2']};
    border: 2px solid transparent;
    border-radius: 20px;
    padding: 8px 16px 8px 6px;
    font-size: 14px;
}}
QLineEdit#buscador:hover {{
    background: {C['superficie3']};
    border-color: {C['borde_claro']};
}}
QLineEdit#buscador:focus {{
    background: {C['superficie3']};
    border: 2px solid {C['texto']};
}}
QLineEdit#url {{
    background: {C['superficie2']};
    border: 1px solid {C['borde']};
    border-radius: 11px;
    padding: 11px 14px;
    font-size: 14px;
}}
QLineEdit#url:focus {{
    border: 1px solid {C['acento']};
    background: {C['superficie3']};
}}
QLineEdit#filtro_lista {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 8px 6px 30px;
}}
QLineEdit#filtro_lista:focus, QLineEdit#filtro_lista:hover {{
    background: {C['superficie2']};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    {img_abajo}
    width: 18px;
    height: 18px;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {C['superficie2']};
    border: 1px solid {C['borde_claro']};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {C['superficie3']};
    selection-color: {C['texto']};
    outline: none;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    height: 15px;
    background: transparent;
    border: none;
    {img_arriba}
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    height: 15px;
    background: transparent;
    border: none;
    {img_abajo}
}}

/* ---------- botones ---------- */
QPushButton {{
    background: {C['superficie2']};
    border: 1px solid {C['borde']};
    border-radius: 9px;
    padding: 8px 14px;
    color: {C['texto']};
    font-weight: 600;
}}
QPushButton:hover {{
    background: {C['superficie3']};
    border-color: {C['borde_claro']};
}}
QPushButton:pressed {{
    background: {C['superficie']};
}}
QPushButton:disabled {{
    color: {C['texto3']};
    background: {C['superficie']};
    border-color: {C['borde']};
}}
QPushButton#principal {{
    background: {C['acento']};
    border: 1px solid {C['acento']};
    color: {C['acento_texto']};
    font-weight: 700;
    padding: 10px 22px;
    border-radius: 18px;
    font-size: 13.5px;
}}
QPushButton#principal:hover {{
    background: {C['acento_alto']};
    border-color: {C['acento_alto']};
}}
QPushButton#principal:pressed {{
    background: {C['acento_bajo']};
}}
QPushButton#principal:disabled {{
    background: {C['superficie3']};
    border-color: {C['borde']};
    color: {C['texto3']};
}}
QPushButton#contorno {{
    background: transparent;
    border: 1px solid {C['borde_claro']};
    border-radius: 15px;
    padding: 6px 16px;
    font-weight: 700;
}}
QPushButton#contorno:hover {{
    border-color: {C['texto']};
    background: transparent;
}}
QPushButton#contorno:checked {{
    border-color: {C['acento']};
    color: {C['acento']};
}}
QPushButton#icono {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px;
}}
QPushButton#icono:hover {{
    background: {C['superficie3']};
}}
QPushButton#redondo {{
    background: {C['superficie2']};
    border: none;
    border-radius: 16px;
    padding: 0;
}}
QPushButton#redondo:hover {{
    background: {C['superficie3']};
}}
QPushButton#redondo:disabled {{
    background: {C['superficie']};
}}
QPushButton#peligro:hover {{
    background: rgba(242, 85, 90, 0.16);
    border-color: {C['error']};
}}
QPushButton#enlace {{
    background: transparent;
    border: none;
    color: {C['texto2']};
    padding: 4px 6px;
    text-align: left;
    font-weight: 700;
}}
QPushButton#enlace:hover {{
    color: {C['texto']};
    text-decoration: underline;
}}
QPushButton#chip {{
    background: {C['superficie2']};
    border: none;
    border-radius: 13px;
    padding: 5px 13px;
    color: {C['texto']};
    font-weight: 600;
    font-size: 12.5px;
}}
QPushButton#chip:hover {{
    background: {C['superficie3']};
}}
QPushButton#chip:checked {{
    background: {C['texto']};
    color: #0A0B0E;
}}
QPushButton#filtro {{
    background: {C['superficie2']};
    border: none;
    border-radius: 13px;
    padding: 5px 13px;
    color: {C['texto']};
    font-size: 12.5px;
    font-weight: 600;
}}
QPushButton#filtro:hover {{
    background: {C['superficie3']};
}}
QPushButton#filtro:checked {{
    background: {C['texto']};
    color: #0A0B0E;
}}
QPushButton#nav {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    color: {C['texto2']};
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#nav:hover {{
    color: {C['texto']};
}}
QPushButton#nav:checked {{
    color: {C['texto']};
    background: {C['superficie2']};
}}
QPushButton#seccion_lateral {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    color: {C['texto2']};
    font-size: 13.5px;
    font-weight: 600;
}}
QPushButton#seccion_lateral:hover {{
    color: {C['texto']};
}}
QPushButton#seccion_lateral:checked {{
    color: {C['texto']};
    background: {C['superficie2']};
}}
QPushButton#pestana {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 8px 4px;
    margin-right: 14px;
    color: {C['texto2']};
    font-weight: 700;
    font-size: 13px;
}}
QPushButton#pestana:hover {{
    color: {C['texto']};
}}
QPushButton#pestana:checked {{
    color: {C['texto']};
    border-bottom: 2px solid {C['acento']};
}}

/* ---------- textos ---------- */
QLabel#titulo_pagina {{
    font-family: {FUENTE_TITULO};
    font-size: 26px;
    font-weight: 800;
}}
QLabel#titulo_seccion {{
    font-family: {FUENTE_TITULO};
    font-size: 21px;
    font-weight: 800;
}}
QLabel#seccion {{
    font-size: 12px;
    font-weight: 700;
    color: {C['texto2']};
    letter-spacing: 0.6px;
}}
QLabel#ayuda {{
    color: {C['texto3']};
    font-size: 11.5px;
}}
QLabel#secundario {{
    color: {C['texto2']};
    font-size: 12.5px;
}}
QLabel#insignia {{
    color: {C['acento']};
    background: rgba(34, 211, 238, 0.10);
    border: 1px solid rgba(34, 211, 238, 0.35);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.4px;
}}
QLabel#estadistica {{
    color: {C['texto2']};
    font-size: 11.5px;
}}

/* ---------- tarjetas y paneles heredados ---------- */
QFrame#tarjeta {{
    background: {C['superficie']};
    border: 1px solid {C['borde']};
    border-radius: 12px;
}}
QFrame#tarjeta:hover {{
    background: {C['superficie2']};
    border-color: {C['borde_claro']};
}}
QLabel#titulo_tarjeta {{
    font-size: 13.5px;
    font-weight: 600;
}}
QLabel#meta {{
    color: {C['texto2']};
    font-size: 11.5px;
}}
QLabel#estado_err {{
    color: {C['error']};
    font-size: 11.5px;
}}
QLabel#estado_ok {{
    color: {C['exito']};
    font-size: 11.5px;
    font-weight: 600;
}}
QFrame#panel {{
    background: {C['superficie']};
    border: 1px solid {C['borde']};
    border-radius: 12px;
}}
QFrame#caja {{
    background: {C['superficie']};
    border: none;
    border-radius: 12px;
}}
QFrame#separador {{
    background: {C['borde']};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame#cabecera {{
    background: {C['superficie']};
    border-bottom: 1px solid {C['borde']};
}}

/* ---------- progreso ---------- */
QProgressBar {{
    background: {C['superficie3']};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {C['acento']};
    border-radius: 3px;
}}

/* ---------- desplazamiento ---------- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea#lienzo, QScrollArea#lienzo > QWidget, QScrollArea#lienzo > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 0;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.30);
}}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    height: 0;
    width: 0;
    background: none;
    border: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.16);
    min-width: 40px;
}}

/* ---------- tablas ---------- */
QTableWidget {{
    background: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: {C['superficie3']};
    selection-color: {C['texto']};
}}
QTableWidget::item {{
    padding: 8px 8px;
    border-bottom: 1px solid {C['borde']};
}}
QTableWidget::item:selected {{
    background: {C['superficie3']};
}}
QHeaderView::section {{
    background: transparent;
    color: {C['texto2']};
    padding: 8px 8px;
    border: none;
    border-bottom: 1px solid {C['borde']};
    font-weight: 600;
    font-size: 11.5px;
}}
QTableCornerButton::section {{
    background: transparent;
    border: none;
}}

/* ---------- casillas ---------- */
QCheckBox {{
    spacing: 10px;
    padding: 4px 0;
}}
QCheckBox::indicator {{
    width: 36px;
    height: 20px;
    border-radius: 10px;
    border: none;
    background: {C['superficie3']};
    image: url({flechas.get('interruptor_off', '')});
}}
QCheckBox::indicator:checked {{
    background: {C['acento']};
    image: url({flechas.get('interruptor_on', '')});
}}
QCheckBox:disabled {{
    color: {C['texto3']};
}}
QRadioButton {{
    spacing: 9px;
    padding: 4px 0;
}}

/* ---------- menus ---------- */
QMenu {{
    background: {C['superficie3']};
    border: 1px solid {C['borde_claro']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 9px 26px 9px 12px;
    border-radius: 4px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background: rgba(255, 255, 255, 0.10);
}}
QMenu::item:disabled {{
    color: {C['texto3']};
}}
QMenu::separator {{
    height: 1px;
    background: {C['borde_claro']};
    margin: 4px 6px;
}}
QMenu::icon {{
    padding-left: 8px;
}}
QMenu::right-arrow {{
    width: 10px;
    height: 10px;
}}

/* ---------- pestanas heredadas ---------- */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar {{
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: transparent;
    color: {C['texto2']};
    padding: 9px 18px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {C['texto']};
    border-bottom: 2px solid {C['acento']};
}}

/* ---------- navegador ---------- */
QFrame#cabecera_nav {{
    background: {C['panel']};
    border-bottom: 1px solid {C['borde']};
}}
QFrame#cabecera_nav QLineEdit {{
    border-radius: 16px;
    padding: 8px 16px;
    background: {C['superficie2']};
}}
QPushButton#acceso_web {{
    background: {C['superficie']};
    border: 1px solid {C['borde']};
    border-radius: 12px;
    padding: 16px 12px;
    color: {C['texto2']};
    font-size: 12.5px;
    font-weight: 600;
    text-align: center;
}}
QPushButton#acceso_web:hover {{
    background: {C['superficie2']};
    border-color: {C['acento']};
    color: {C['texto']};
}}
QFrame#barra_descarga {{
    background: {C['superficie2']};
    border-top: 1px solid {C['acento']};
}}
QFrame#tarjeta_album {{
    background: {C['superficie']};
    border: 1px solid {C['borde']};
    border-radius: 12px;
}}

/* ---------- dialogos ---------- */
QDialog {{
    background: {C['panel']};
}}
QMessageBox {{
    background: {C['panel']};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {C['superficie3']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {C['acento']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C['texto']};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::groove:vertical {{
    width: 4px;
    background: {C['superficie3']};
    border-radius: 2px;
}}
QSlider::add-page:vertical {{
    background: {C['acento']};
    border-radius: 2px;
}}
QSlider::handle:vertical {{
    background: {C['texto']};
    width: 14px;
    height: 14px;
    margin: 0 -5px;
    border-radius: 7px;
}}
""" + (hoja_fondo() if FONDO["activo"] else "")
