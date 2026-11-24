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

# Las mismas claves que PREMIUM_TEMAS de ui/estilos.py (sin el prefijo «premium_»). Si se añade un tema
# allí, añadirlo también aquí: tema_valido() lo devolvería a «ninguno» al leerlo del servidor.
TEMAS = ("ninguno", "atardecer", "bosque", "sakura", "oceano", "medianoche", "ambar",
         "retro", "cyberpunk", "samurai", "boxeo", "gym", "fan_kitty", "gotico", "lofi",
         "est_kuromi", "est_cinnamoroll", "est_pompompurin", "est_hellokitty", "est_mymelody")
NOMBRES_TEMA = {"ninguno": "Tema normal", "atardecer": "Atardecer", "bosque": "Bosque profundo",
                "sakura": "Sakura", "oceano": "Océano", "medianoche": "Medianoche", "ambar": "Ámbar",
                "retro": "Retro", "cyberpunk": "Cyberpunk", "samurai": "Japón samurái", "boxeo": "Boxeo",
                "gym": "Gym", "fan_kitty": "Fan de Hello Kitty", "gotico": "Gótico", "lofi": "Lo-fi",
                "est_kuromi": "Estética Kuromi", "est_cinnamoroll": "Estética Cinnamoroll",
                "est_pompompurin": "Estética Pompompurin", "est_hellokitty": "Estética Hello Kitty",
                "est_mymelody": "Estética My Melody"}

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


# ================================================================ más para donadores
# Color del nombre, pared de agradecimiento, mascota propia y la letra con efectos. Las claves son las
# mismas que usa la app del teléfono y la base (supabase/donadores_extra.sql).

# la paleta del color del nombre (en este orden en las dos apps); además se puede elegir uno propio
PALETA_NOMBRE = (("Rosa", "#FF5C8A"), ("Coral", "#FF7A45"), ("Oro", "#FFC857"), ("Menta", "#7CFFB2"),
                 ("Cian", "#22D3EE"), ("Azul", "#4DA8FF"), ("Lila", "#A78BFA"), ("Fucsia", "#FF4DD2"),
                 ("Nieve", "#F5F5F5"))


def color_valido(v):
    """Un color «#RRGGBB» en mayúsculas, o None si no hay o está mal escrito («#abc» se estira a «#AABBCC»)."""
    t = str(v or "").strip().upper()
    if not t:
        return None
    if not t.startswith("#"):
        t = "#" + t
    if len(t) == 4 and all(c in "0123456789ABCDEF" for c in t[1:]):
        t = "#" + "".join(c * 2 for c in t[1:])
    if len(t) == 7 and all(c in "0123456789ABCDEF" for c in t[1:]):
        return t
    return None


def nombre_de_color(color):
    """«Rosa», «Oro»... para un color de la paleta; «Personalizado» para otro; «Sin color» si no hay."""
    c = color_valido(color)
    if c is None:
        return "Sin color"
    for nombre, hexa in PALETA_NOMBRE:
        if hexa == c:
            return nombre
    return "Personalizado"


def es_donador_de_verdad(estado):
    """Donador o fundador vigente (la prueba no cuenta): la pared y la mascota propia son solo para ellos."""
    return bool(estado is not None and estado.vigente() and estado.tipo in ("donador", "fundador"))


NUMERO_WHATSAPP = "51902464984"
TEXTO_MASCOTA = ("Te escribimos por WhatsApp para diseñarla juntos: el diseño se aprueba por WhatsApp antes de "
                 "añadirlo a tu cuenta.")


def mensaje_mascota(usuario):
    """El mensaje ya escrito que se manda por WhatsApp para pedir la mascota personalizada."""
    u = str(usuario or "").strip().lstrip("@")
    quien = f"Hola, soy @{u} en Caudal." if u else "Hola, soy donador de Caudal."
    return f"{quien} Quiero mi mascota personalizada."


def url_mascota(usuario):
    from urllib.parse import quote
    return f"https://wa.me/{NUMERO_WHATSAPP}?text={quote(mensaje_mascota(usuario), safe='')}"


def leer_pared(datos):
    """Lo que devuelve `pared_agradecimiento()` → [{usuario, nombre, tipo, color, desde}] limpio (fundadores
    primero, como lo manda el servidor). Lo que venga roto se descarta."""
    salida = []
    for d in datos if isinstance(datos, list) else []:
        if not isinstance(d, dict):
            continue
        usuario = str(d.get("usuario") or "").strip()
        tipo = str(d.get("tipo") or "").strip().lower()
        if not usuario or tipo not in ("donador", "fundador"):
            continue
        nombre = str(d.get("nombre") or "").strip() or usuario
        salida.append({"usuario": usuario, "nombre": nombre[:40], "tipo": tipo,
                       "color": color_valido(d.get("color")), "desde": d.get("desde")})
    return salida


# la letra a pantalla completa con efectos: estilos (las mismas claves que en el teléfono)
ESTILOS_ESCENA = ("resplandor", "ola", "neon", "cine", "zoom", "maquina", "lluvia", "giro")
NOMBRES_ESCENA = {"resplandor": "Resplandor", "ola": "Ola", "neon": "Neón", "cine": "Cine", "zoom": "Zoom",
                  "maquina": "Máquina", "lluvia": "Lluvia", "giro": "Giro"}
DETALLE_ESCENA = {"resplandor": "Cada verso sube con un brillo de los colores de la carátula",
                  "ola": "Las palabras entran una a una, como una ola",
                  "neon": "El verso se enciende como un letrero de neón",
                  "cine": "Letra a letra, como los créditos de una película",
                  "zoom": "El verso llega de golpe, enorme, y se queda en su sitio",
                  "maquina": "Se escribe tecla a tecla, con su cursor",
                  "lluvia": "Las letras caen y rebotan hasta quedarse quietas",
                  "giro": "Cada palabra entra girando"}
_NUMEROS = {4: "Cuatro", 5: "Cinco", 6: "Seis", 7: "Siete", 8: "Ocho", 9: "Nueve", 10: "Diez"}


def texto_estilos_escena():
    """«Ocho estilos: Resplandor, Ola, … y Giro»: los que hay de verdad."""
    nombres = [NOMBRES_ESCENA[k] for k in ESTILOS_ESCENA]
    cuantos = _NUMEROS.get(len(nombres), str(len(nombres)))
    return f"{cuantos} estilos: {', '.join(nombres[:-1])} y {nombres[-1]}"


def estilo_escena_valido(v):
    v = str(v or "").strip().lower()
    return v if v in ESTILOS_ESCENA else ESTILOS_ESCENA[0]
