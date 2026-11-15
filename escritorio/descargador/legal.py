# -*- coding: utf-8 -*-
"""Términos, privacidad y datos básicos del perfil (igual que app/lib/nucleo/legal.dart).

Los textos viven en Caudal/legal (fuente única) y se copian aquí con
legal/sincronizar.py. Si cambian de forma importante se sube VERSION y a
todos se les pide aceptarlos de nuevo.
"""

import os
from datetime import date

VERSION = "2026-11-15.2"
EDAD_MINIMA = 14     # sin permiso de la madre, el padre o un tutor (Ley 29733, Perú)

PAISES = {
    "PE": "Perú", "AR": "Argentina", "BO": "Bolivia", "CL": "Chile", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "EC": "Ecuador", "SV": "El Salvador", "ES": "España",
    "US": "Estados Unidos", "GT": "Guatemala", "HN": "Honduras", "MX": "México",
    "NI": "Nicaragua", "PA": "Panamá", "PY": "Paraguay", "PR": "Puerto Rico",
    "DO": "República Dominicana", "UY": "Uruguay", "VE": "Venezuela", "OT": "Otro país",
}
GENEROS = {"mujer": "Mujer", "hombre": "Hombre", "otro": "Otro", "no_decir": "Prefiero no decirlo"}


def texto(nombre):
    """'terminos' o 'privacidad' (Markdown)."""
    import sys
    bases = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "legal")]
    if getattr(sys, "_MEIPASS", None):
        bases.insert(0, os.path.join(sys._MEIPASS, "descargador", "legal"))
    for b in bases:
        ruta = os.path.join(b, f"{nombre}.md")
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                return f.read()
    return "No se encontró el texto. Puedes leerlo en la web de Caudal."


def edad(nacimiento, hoy=None):
    h = hoy or date.today()
    return h.year - nacimiento.year - ((h.month, h.day) < (nacimiento.month, nacimiento.day))


def revisar_perfil(nombre, nacimiento, pais, permiso_tutor=False, hoy=None):
    """None si está bien; si no, lo que hay que corregir (en palabras)."""
    if len((nombre or "").strip()) < 2:
        return "Escribe tu nombre."
    if nacimiento is None:
        return "Elige tu fecha de nacimiento."
    e = edad(nacimiento, hoy)
    if e < 0 or e > 120:
        return "Revisa tu fecha de nacimiento."
    if e < EDAD_MINIMA and not permiso_tutor:
        return (f"Tienes menos de {EDAD_MINIMA} años: tu madre, padre o tutor debe darte permiso "
                "y marcar la casilla de permiso.")
    if not pais:
        return "Elige tu país."
    return None


def extra_registro(nacimiento, pais, genero, comparte, permiso_tutor):
    """Lo que viaja con el registro para que el perfil lo guarde al crearse."""
    d = {"terminos": VERSION, "comparte_datos": bool(comparte),
         "fecha_nacimiento": nacimiento.isoformat(), "pais": pais,
         "permiso_tutor": bool(permiso_tutor)}
    if genero:
        d["genero"] = genero
    return d


# ---------------------------------------------------------------- en la nube

def perfil(sesion):
    filas = sesion.pedir("GET", "perfiles?select=nombre,terminos_version,comparte_datos,"
                                f"fecha_nacimiento,pais,genero&id=eq.{sesion.user_id}") or []
    d = filas[0] if filas else {}
    nac = None
    if d.get("fecha_nacimiento"):
        try:
            nac = date.fromisoformat(d["fecha_nacimiento"])
        except ValueError:
            nac = None
    return {"version": d.get("terminos_version"), "comparte": bool(d.get("comparte_datos")),
            "nacimiento": nac, "pais": d.get("pais"), "genero": d.get("genero"),
            "nombre": d.get("nombre") or ""}


def aceptado(p):
    return p.get("version") == VERSION


def completo(p):
    return p.get("nacimiento") is not None and bool(p.get("pais"))


def aceptar(sesion, comparte):
    sesion.pedir("POST", "rpc/aceptar_terminos", json={"p_version": VERSION, "p_comparte": bool(comparte)})


def compartir(sesion, comparte):
    sesion.pedir("POST", "rpc/compartir_datos", json={"p_comparte": bool(comparte)})


def completar(sesion, nombre, nacimiento, pais, genero=None, permiso_tutor=False):
    sesion.pedir("POST", "rpc/completar_perfil", json={
        "p_nombre": (nombre or "").strip(), "p_nacimiento": nacimiento.isoformat(), "p_pais": pais,
        "p_genero": genero or "", "p_permiso_tutor": bool(permiso_tutor)})


def eliminar_cuenta(sesion):
    sesion.pedir("POST", "rpc/eliminar_mi_cuenta", json={})
