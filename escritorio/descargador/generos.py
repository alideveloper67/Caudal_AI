# -*- coding: utf-8 -*-
"""Género, idioma y época de una canción, deducidos de los datos que ya trae
(artista, título, álbum): sin llamadas extra a internet. Lógica pura y testeable."""

import re
import unicodedata

from . import mixes


def plano(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


GENEROS = {
    "cumbia": ["cumbia", "chicha", "grupo 5", "corazon serrano", "agua marina", "armonia 10", "chacalon",
               "juaneco", "papillon", "pintura roja", "grupo aliado", "los angeles azules", "sonora dinamita",
               "la sonora", "amar azul", "alma serrana", "hermanos yaipen", "tropicalisimo apache", "los mirlos",
               "bareto", "los palmeras", "damas gratis", "kumbia kings", "selena", "marisol", "armonia"],
    "salsa": ["salsa", "marc anthony", "celia cruz", "willie colon", "hector lavoe", "gran combo", "grupo niche",
              "victor manuelle", "oscar d'leon", "ruben blades", "fania", "la india", "tito puente",
              "eddie palmieri", "son cubano", "buena vista"],
    "bachata": ["bachata", "romeo santos", "aventura", "prince royce", "grupo extra", "juan luis guerra",
                "merengue", "elvis crespo", "olga tanon", "toby love", "zacarias ferreira", "anthony santos"],
    "urbano": ["reggaeton", "reguet", "perreo", "bad bunny", "karol g", "daddy yankee", "feid", "j balvin",
               "ozuna", "anuel", "maluma", "rauw alejandro", "myke towers", "wisin", "yandel", "don omar",
               "nicky jam", "farruko", "sech", "arcangel", "de la ghetto", "becky g", "jhay cortez",
               "eladio carrion", "tito el bambino", "zion", "lunay", "bryant myers", "nio garcia"],
    "hiphop": ["rap", "hip hop", "hip-hop", "trap", "drill", "eminem", "kendrick", "drake", "travis scott",
               "21 savage", "snoop", "tupac", "2pac", "50 cent", "kanye", "j cole", "jay-z", "jay z",
               "post malone", "migos", "cardi b", "nicki minaj", "bizarrap", "duki", "paulo londra",
               "trueno", "nicki nicole", "cazzu", "khea", "residente", "calle 13"],
    "rock": ["rock", "metal", "punk", "grunge", "alternativ", "soda stereo", "cerati", "metallica", "queen",
             "nirvana", "ac/dc", "acdc", "guns n", "led zeppelin", "pink floyd", "linkin park", "green day",
             "foo fighters", "heroes del silencio", "enanitos verdes", "caifanes", "la renga", "beatles",
             "rolling stones", "red hot", "radiohead", "pearl jam", "bon jovi", "iron maiden", "megadeth",
             "slipknot", "system of a down", "my chemical", "oasis", "the killers", "arctic monkeys",
             "sepultura", "mago de oz", "hombres g", "los prisioneros", "charly garcia", "fito paez",
             "los fabulosos", "pappo", "rata blanca", "la ley", "mana", "cafe tacvba", "molotov", "libido",
             "mar de copas", "pedro suarez vertiz", "kiss", "scorpions", "black sabbath", "deep purple",
             "evanescence", "paramore", "avril"],
    "pop": ["pop", "taylor swift", "dua lipa", "ed sheeran", "shakira", "ariana grande", "justin bieber",
            "billie eilish", "the weeknd", "coldplay", "imagine dragons", "harry styles", "bruno mars",
            "adele", "katy perry", "maroon 5", "olivia rodrigo", "lady gaga", "rihanna", "beyonce",
            "selena gomez", "miley cyrus", "sabrina carpenter", "camila cabello", "shawn mendes",
            "one direction", "demi lovato", "lana del rey", "doja cat", "sam smith", "lewis capaldi",
            "rosalia", "aitana", "tini", "morat", "sebastian yatra", "camilo", "reik", "cnco",
            "jesse & joy", "natalia lafourcade", "pablo alboran", "david bisbal", "enrique iglesias",
            "ricky martin", "thalia", "paulina rubio", "belinda", "rbd"],
    "balada": ["balada", "luis miguel", "ricardo arjona", "juan gabriel", "franco de vita", "sin bandera",
               "chayanne", "alejandro sanz", "manzanero", "jose jose", "jose luis perales", "camilo sesto",
               "ricardo montaner", "marco antonio solis", "emmanuel", "cristian castro", "myriam hernandez",
               "gloria trevi", "pimpinela", "roberto carlos", "julio iglesias", "bolero", "los panchos"],
    "regional": ["corrido", "banda ", "norteno", "regional mexican", "peso pluma", "grupo frontera",
                 "fuerza regida", "junior h", "natanael cano", "luis r conriquez", "eslabon armado",
                 "los tigres", "vicente fernandez", "ramon ayala", "intocable", "banda ms", "calibre 50",
                 "mariachi", "ranchera", "alejandro fernandez", "pedro infante", "christian nodal",
                 "ariel camacho", "carin leon", "grupo firme", "el fantasma"],
    "electronica": ["edm", "electronic", "house", "techno", "trance", "dubstep", "avicii", "david guetta",
                    "calvin harris", "martin garrix", "tiesto", "marshmello", "alan walker", "skrillex",
                    "daft punk", "deadmau5", "kygo", "zedd", "swedish house", "the chainsmokers", "diplo",
                    "major lazer", "afrojack", "hardwell", "armin van buuren", "alok", "steve aoki"],
    "folclore": ["huayno", "folclor", "folklor", "andin", "vals criollo", "criolla", "marinera", "los kjarkas",
                 "savia andina", "dina paucar", "sonia morales", "eva ayllon", "chabuca granda",
                 "lucha reyes", "cecilia barraza", "los morochucos", "inti-illimani", "violeta parra",
                 "mercedes sosa", "atahualpa yupanqui", "yma sumac", "zampona", "charango",
                 "picaflor de los andes", "flor pucarina"],
    "clasica": ["jazz", "classical", "clasica", "sinfonia", "symphony", "concerto", "orchestra", "sonata",
                "chopin", "mozart", "beethoven", "bach", "vivaldi", "debussy", "louis armstrong", "miles davis",
                "frank sinatra", "ella fitzgerald", "norah jones", "john coltrane", "ludovico einaudi",
                "piano solo", "lofi", "lo-fi", "instrumental", "tchaikovsky", "paganini"],
    "kpop": ["k-pop", "kpop", "bts", "blackpink", "twice", "stray kids", "newjeans", "exo", "seventeen",
             "itzy", "(g)i-dle", "aespa", "le sserafim", "red velvet", "enhypen", "ateez", "psy", "nct",
             "jungkook", "jimin", "j-pop", "anime opening", "yoasobi"],
    "vallenato": ["vallenato", "carlos vives", "diomedes", "silvestre dangond", "binomio de oro",
                  "jorge celedon", "los diablitos", "kaleth morales", "fonseca", "peter manjarres",
                  "farid ortiz", "rafael orozco"],
}

# qué tan compatibles son dos géneros (1 = el mismo). Lo que no figura vale MIN_GENERO.
_C = {
    ("cumbia", "salsa"): 0.7, ("cumbia", "vallenato"): 0.7, ("cumbia", "bachata"): 0.55,
    ("cumbia", "regional"): 0.5, ("cumbia", "folclore"): 0.55, ("cumbia", "balada"): 0.4,
    ("cumbia", "urbano"): 0.4, ("salsa", "bachata"): 0.75, ("salsa", "vallenato"): 0.55,
    ("salsa", "balada"): 0.4, ("bachata", "balada"): 0.55, ("bachata", "urbano"): 0.5,
    ("bachata", "vallenato"): 0.5, ("bachata", "pop"): 0.45, ("urbano", "hiphop"): 0.8,
    ("urbano", "pop"): 0.6, ("urbano", "electronica"): 0.5, ("urbano", "regional"): 0.4,
    ("pop", "rock"): 0.6, ("pop", "balada"): 0.7, ("pop", "electronica"): 0.65, ("pop", "hiphop"): 0.5,
    ("pop", "kpop"): 0.6, ("pop", "regional"): 0.35, ("rock", "electronica"): 0.35,
    ("rock", "balada"): 0.4, ("rock", "hiphop"): 0.35, ("regional", "balada"): 0.55,
    ("regional", "folclore"): 0.5, ("folclore", "balada"): 0.45, ("clasica", "folclore"): 0.4,
    ("electronica", "kpop"): 0.45, ("hiphop", "kpop"): 0.4,
}
COMPAT = {frozenset(k): v for k, v in _C.items()}
MIN_GENERO = 0.25


def compatibilidad(a, b):
    """0..1 entre dos géneros; si se desconoce alguno es neutro (1.0)."""
    if not a or not b or a == b:
        return 1.0
    return COMPAT.get(frozenset([a, b]), MIN_GENERO)


def _texto_pista(p):
    alb = (p or {}).get("album") or {}
    nombre_album = alb.get("nombre") if isinstance(alb, dict) else str(alb or "")
    return plano(" | ".join(str(x or "") for x in (
        (p or {}).get("artista"), (p or {}).get("titulo"), nombre_album, (p or {}).get("subtitulo"),
        (p or {}).get("genero"))))


def _tiene(clave, texto):
    # una palabra corta solo cuenta entera; una larga, donde aparezca
    if len(clave) <= 5:
        return re.search(r"(?<![a-z0-9])" + re.escape(clave.strip()) + r"(?![a-z0-9])", texto) is not None
    return clave in texto


def genero_de(p, conocidos=None):
    """El género de una canción (cumbia, salsa, rock…) o None si no se puede deducir.

    Mira el texto (artista, título, álbum, campo `genero`); si nada coincide, lo que ya
    se sabe de ese artista (`conocidos`: {clave de artista: género})."""
    texto = _texto_pista(p)
    artista = plano((p or {}).get("artista"))
    mejor, puntos = None, 0
    for g, claves in GENEROS.items():
        n = 0
        for c in claves:
            if _tiene(c, texto):
                n += 2 if (c.strip() in artista or len(c) > 5) else 1
        if n > puntos:
            mejor, puntos = g, n
    if mejor:
        return mejor
    if conocidos:
        for c, _n in mixes.artistas_de(p):
            if conocidos.get(c):
                return conocidos[c]
    return None


_ES = set("el la los las de del que y en un una es por con para tu mi te me se lo su al no si mas amor corazon "
          "vida noche dia besos quiero eres soy este esta como pero sin sobre tengo siempre nunca todo nada "
          "cuando donde baila bailame fiesta cancion mujer hombre dime ven vuelve vamos mundo cielo luna sol".split())
_EN = set("the you and of to in my your love me it is on with for this that baby night we all be are just like "
          "when what feel heart girl boy dont im never want need time live come back one more way down "
          "world dance life remix feat song".split())
_PT = set("voce nao coracao amor eu uma com para meu minha ele ela sao tudo porque obrigado saudade".split())


def idioma_de(p):
    """'es', 'en', 'pt', 'ko', 'ja' o None si no se sabe."""
    t = str((p or {}).get("titulo") or "")
    if re.search("[가-힯]", t):
        return "ko"
    if re.search("[぀-ヿ]", t):
        return "ja"
    palabras = re.findall(r"[a-z]+", plano(t).replace("'", ""))
    es = sum(1 for w in palabras if w in _ES)
    en = sum(1 for w in palabras if w in _EN)
    pt = sum(1 for w in palabras if w in _PT)
    if re.search("[ñ¿¡]", t.lower()):
        es += 2
    if re.search("ção|ões|ã", t.lower()):
        pt += 2
    cuentas = sorted([(es, "es"), (en, "en"), (pt, "pt")], reverse=True)
    if cuentas[0][0] == 0 or cuentas[0][0] == cuentas[1][0]:
        return None
    return cuentas[0][1]


def compat_idioma(a, b):
    if not a or not b or a == b:
        return 1.0
    if {a, b} == {"es", "pt"}:
        return 0.8
    return 0.65


def epoca_de(p):
    """El año de la canción si viene en los datos (campo `anio`/`year`, o 4 cifras en título/álbum)."""
    for k in ("anio", "year"):
        try:
            v = int((p or {}).get(k))
            if 1900 < v < 2100:
                return v
        except (TypeError, ValueError):
            pass
    alb = (p or {}).get("album") or {}
    texto = f"{(p or {}).get('titulo') or ''} {alb.get('nombre') if isinstance(alb, dict) else alb or ''}"
    m = re.findall(r"(?<!\d)(19[5-9]\d|20[0-3]\d)(?!\d)", texto)
    return int(m[-1]) if m else None


def compat_epoca(a, b):
    if not a or not b:
        return 1.0
    d = abs(a - b)
    return 1.0 if d <= 6 else 0.92 if d <= 15 else 0.82
