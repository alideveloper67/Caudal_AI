# -*- coding: utf-8 -*-
"""Las presentaciones de la letra en la Escena: una lista única que usan el selector («Aa») y la tecla N.

Tres familias, cada una con sus variantes:
- **Original**: la de siempre de la escena, con su letra propia (estrecha y en cursiva) y la palabra fuerte en
  grande. Es la predeterminada. Variantes: cómo entran las palabras y su acabado (neón, se rellena, nítida).
- **Tu tipo de letra**: la misma, con el tipo de letra y el estilo que elegiste más abajo.
- **Eco fluido** y sus derivaciones (ui/epica).

Una presentación es un diccionario: {"clave", "nombre", "detalle", "epica", "mov", "original", "acabado"}.
"""

from . import epica, estilo_letra

ACABADOS = {
    "clasica": ("", "Contorno y la palabra fuerte en grande, rellena"),
    "neon": ("Neón", "El contorno brilla con el color de la carátula"),
    "contorno": ("Se rellena", "Las palabras esperan huecas y se rellenan al cantarse"),
    "nitida": ("Nítida", "Rellenas, con borde y sombra: se lee sobre cualquier fondo"),
}
POR_DEFECTO = "original"


def _nombre(base, mov, acabado=""):
    partes = [base]
    if acabado:
        partes.append(acabado)
    if mov != "clasica":
        partes.append(estilo_letra.MOVIMIENTOS[mov][0])
    return " · ".join(partes)


def lista():
    salida = []
    for mov, (_n, detalle) in estilo_letra.MOVIMIENTOS.items():
        salida.append({"clave": "original" if mov == "clasica" else f"original_{mov}", "epica": "", "mov": mov,
                       "original": True, "acabado": "clasica", "nombre": _nombre("Original", mov),
                       "detalle": "La de siempre de la escena. " + detalle})
    for acabado in ("neon", "contorno", "nitida"):
        nombre, detalle = ACABADOS[acabado]
        salida.append({"clave": f"original_{acabado}", "epica": "", "mov": "clasica", "original": True,
                       "acabado": acabado, "nombre": _nombre("Original", "clasica", nombre), "detalle": detalle})
    for mov, (_n, detalle) in estilo_letra.MOVIMIENTOS.items():
        salida.append({"clave": "tuya" if mov == "clasica" else f"tuya_{mov}", "epica": "", "mov": mov,
                       "original": False, "acabado": None, "nombre": _nombre("Tu tipo de letra", mov),
                       "detalle": "Con el tipo de letra y el estilo que elegiste más abajo. " + detalle})
    for k in epica.OFRECIDAS:
        salida.append({"clave": k, "epica": k, "mov": None, "original": False, "acabado": None,
                       "nombre": epica.NOMBRES[k][0], "detalle": epica.NOMBRES[k][1]})
    return salida


def por_clave(clave):
    return next((p for p in lista() if p["clave"] == clave), None)


def actual():
    """La presentación puesta ahora."""
    if epica.actual():
        return por_clave(epica.actual()) or por_clave(POR_DEFECTO)
    mov = estilo_letra.movimiento()
    if estilo_letra.original():
        acabado = estilo_letra.acabado_original()
        if acabado != "clasica":
            return por_clave(f"original_{acabado}") or por_clave(POR_DEFECTO)
        return por_clave("original" if mov == "clasica" else f"original_{mov}")
    return por_clave("tuya" if mov == "clasica" else f"tuya_{mov}")


def aplicar(pres, ajustes=None):
    """La pone (y la guarda si se dan los ajustes)."""
    if ajustes is not None:
        ajustes["letra_epica"] = pres["epica"]
        ajustes["letra_epica_elegida"] = True
        if not pres["epica"]:
            ajustes["letra_movimiento"] = pres["mov"]
            ajustes["letra_original"] = pres["original"]
            if pres["original"]:
                ajustes["letra_acabado_original"] = pres["acabado"]
        try:
            ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
    if not pres["epica"]:
        estilo_letra.fijar_movimiento(pres["mov"])
        estilo_letra.fijar_original(pres["original"], pres["acabado"] if pres["original"] else None)
    epica.fijar(pres["epica"])


def siguiente(pres=None):
    todas = lista()
    pres = pres or actual()
    i = next((k for k, p in enumerate(todas) if p["clave"] == (pres or {}).get("clave")), -1)
    return todas[(i + 1) % len(todas)]
