# -*- coding: utf-8 -*-
"""Datos puros de lo «premium» de Caudal (sin Qt, para probarlos sin ventanas).

Lo que ve la gente de las cuentas con beneficios: un marco animado alrededor de la foto, un efecto
en el nombre y un tema de colores propio. Las claves son las mismas que guarda el servidor en la tabla
de perfiles (`marco`, `efecto_nombre`, `tema_premium`) y las mismas que usa la app del teléfono.

El servidor manda: si alguien deja de ser donador, sus marcos y efectos dejan de salir en las consultas
públicas. Aquí solo se valida lo que llega y se calcula cuánto le queda a una prueba."""

import time
from datetime import datetime, timezone

NINGUNO = "ninguno"

MARCOS = ("ninguno", "aurora", "fuego", "oro", "neon", "hielo", "arcoiris", "galaxia")
NOMBRES_MARCO = {"ninguno": "Sin marco", "aurora": "Aurora", "fuego": "Fuego", "oro": "Oro",
                 "neon": "Neón", "hielo": "Hielo", "arcoiris": "Arcoíris", "galaxia": "Galaxia"}

EFECTOS = ("ninguno", "brillo", "degradado", "arcoiris", "neon")
NOMBRES_EFECTO = {"ninguno": "Normal", "brillo": "Brillo", "degradado": "Degradado",
                  "arcoiris": "Arcoíris", "neon": "Neón"}

TEMAS = ("ninguno", "atardecer", "bosque", "sakura", "oceano", "medianoche", "ambar")
NOMBRES_TEMA = {"ninguno": "Tema normal", "atardecer": "Atardecer", "bosque": "Bosque profundo",
                "sakura": "Sakura", "oceano": "Océano", "medianoche": "Medianoche", "ambar": "Ámbar"}

TIPOS = ("donador", "fundador", "prueba")


def marco_valido(v):
    v = str(v or "").strip().lower()
    return v if v in MARCOS else NINGUNO


def efecto_valido(v):
    v = str(v or "").strip().lower()
    return v if v in EFECTOS else NINGUNO


def tema_valido(v):
    v = str(v or "").strip().lower()
    return v if v in TEMAS else NINGUNO


def _epoch(v):
    """Una fecha del servidor (ISO 8601, o ya un número) a segundos desde 1970. None si no hay."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.timestamp()


class EstadoPremium:
    """Lo que dice `mi_premium()`: si hay beneficios, de qué tipo y cuándo vencen (solo la prueba)."""

    def __init__(self, premium=False, tipo=None, vence=None):
        self.premium = bool(premium)
        self.tipo = tipo if tipo in TIPOS else None
        self.vence = _epoch(vence)

    @classmethod
    def desde_servidor(cls, d):
        d = d if isinstance(d, dict) else {}
        return cls(d.get("premium"), d.get("tipo"), d.get("vence"))

    def vigente(self, ahora=None):
        """¿Tiene beneficios ahora mismo? Una prueba vencida ya no cuenta, aunque el aviso del servidor
        llegue tarde (o falte la red): el reloj local manda sobre lo guardado."""
        if not self.premium:
            return False
        if self.tipo == "prueba" and self.vence is not None:
            return (ahora if ahora is not None else time.time()) < self.vence
        return True

    def dias_restantes(self, ahora=None):
        """Días enteros que le quedan a una prueba (redondeando hacia arriba); None si no es una prueba."""
        if self.tipo != "prueba" or self.vence is None or not self.vigente(ahora):
            return None
        resto = self.vence - (ahora if ahora is not None else time.time())
        return max(1, int(-(-resto // 86400)))

    def a_dict(self):
        return {"premium": self.premium, "tipo": self.tipo, "vence": self.vence}

    def __eq__(self, otro):
        return isinstance(otro, EstadoPremium) and self.a_dict() == otro.a_dict()

    def __repr__(self):
        return f"EstadoPremium({self.a_dict()})"


def texto_vencimiento(dias):
    """«Tu prueba vence mañana» / «Tu prueba vence en 3 días» (sin jerga)."""
    if dias is None:
        return ""
    if dias <= 1:
        return "Tu prueba de donador vence hoy o mañana"
    return f"Tu prueba de donador vence en {dias} días"


def limpiar_codigo(texto):
    """Lo que se escribió → «XXXX-XXXX» en mayúsculas, sin espacios ni caracteres raros.
    Devuelve '' si no hay nada que canjear."""
    letras = "".join(c for c in str(texto or "").upper() if c.isalnum())[:8]
    if not letras:
        return ""
    return letras if len(letras) <= 4 else letras[:4] + "-" + letras[4:]


def codigo_completo(texto):
    return len(limpiar_codigo(texto).replace("-", "")) == 8
