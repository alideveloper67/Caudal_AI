# -*- coding: utf-8 -*-
"""Perfiles, amigos, directorio y música de la gente (capa de datos).

Todo habla con las funciones de supabase/social.sql a través de `nube.Sesion`.
Las funciones de este archivo no tocan la interfaz: devuelven diccionarios
limpios (con todos los campos presentes aunque el servidor no los mande) para
que las pantallas no se rompan si falta algo.

La interfaz vive en ui/paginas/perfil*.py, directorio*.py, amigos*.py,
subir_musica*.py y comunidad*.py.
"""

import mimetypes
import os
import re
import time
import uuid
from pathlib import Path

from . import nube
from .config import carpeta_datos
from .premium_datos import efecto_valido, marco_valido
from .nube import ErrorNube, SinConexion  # noqa: F401 - se reexportan para las pantallas

BUCKET_FOTOS = "avatares"
BUCKET_MUSICA = "musica"

LIKES_ARTISTA = 200            # con tantos «me gusta» llega la nota ARTISTA
TOPE_AUDIO = 15 * 1024 * 1024  # el almacén rechaza audio más pesado
TOPE_IMAGEN = 1_900_000        # las fotos deben pesar menos de 2 MB
LADO_FOTO = 512
LADO_PORTADA = 800

# formato -> tipo de archivo que acepta el almacén de música
AUDIOS = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac",
          ".ogg": "audio/ogg", ".wav": "audio/wav", ".webm": "audio/webm"}
IMAGENES = (".jpg", ".jpeg", ".png", ".webp")
FILTRO_AUDIO = "Música (*.mp3 *.m4a *.aac *.flac *.ogg *.wav *.webm)"
FILTRO_IMAGEN = "Imágenes (*.jpg *.jpeg *.png *.webp)"
FILTRO_IMAGEN_PERFIL = "Imágenes (*.jpg *.jpeg *.png *.webp *.gif)"   # foto y fondo del perfil (GIF: donadores)

GENEROS_SUGERIDOS = ["Pop", "Rock", "Reguetón", "Salsa", "Cumbia", "Hip hop", "Trap", "Electrónica",
                     "Indie", "Baladas", "Jazz", "Clásica", "Metal", "K-pop", "R&B", "Folclore",
                     "Lofi", "Vallenato", "Bachata", "Anime", "Alternativo", "Latina"]

# colores que se ofrecen para el perfil (la persona también puede elegir el suyo)
COLORES_PERFIL = ["#FF5C8A", "#FF8A3D", "#F5C542", "#2BD576", "#22D3EE", "#4C8DFF", "#8B6CFF",
                  "#C45CFF", "#F2555A", "#14B8A6", "#A3E635", "#94A3B8"]

# clave -> (titulo por defecto, icono de iconos.py, color)
INSIGNIAS = {
    "veterano": ("Veterano", "reloj", "#B794F6"),
    "fiel": ("Oyente fiel", "corazon_lleno", "#FF7A9E"),
    "explorador": ("Explorador", "brujula", "#5EC8FF"),
    "coleccionista": ("Coleccionista", "album", "#FFB454"),
    "maratonista": ("Maratonista", "velocidad", "#6FE0A0"),
    "creador": ("Creador", "musica", "#FF9CE6"),
}
COLOR_ARTISTA = "#FFC83D"

# --------------------------------------------------------------- direcciones


def url_publica(bucket, ruta, marca=None):
    """Dirección para ver o escuchar un archivo público del almacén."""
    ruta = str(ruta or "").lstrip("/")
    if not ruta:
        return ""
    u = f"{nube.URL}/storage/v1/object/public/{bucket}/{ruta}"
    return f"{u}?v={marca}" if marca else u


_MARCAS_FOTO = {}   # ruta de foto -> marca (lo que cambia al subir una foto nueva)


def marcar_foto(ruta, marca=None):
    """Cada vez que cambia una foto propia se estrena marca para saltarse la caché."""
    _MARCAS_FOTO[ruta] = marca or int(time.time())


def url_foto(foto_url, marca=None):
    """Foto de perfil lista para descargar ('' si la persona no tiene)."""
    if not foto_url:
        return ""
    if str(foto_url).startswith("http"):
        return str(foto_url)
    # para fotos ajenas no hay fecha de cambio: se renueva a diario
    m = marca or _MARCAS_FOTO.get(foto_url) or int(time.time() // 86400)
    return url_publica(BUCKET_FOTOS, foto_url, m)


def url_musica(ruta):
    return url_publica(BUCKET_MUSICA, ruta)


# --------------------------------------------------------------- datos limpios

_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def color_valido(c):
    return str(c) if isinstance(c, str) and _COLOR.match(c) else None


def _texto(v, tope=None):
    t = "" if v is None else str(v)
    return t[:tope] if tope else t


def _entero(v, defecto=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return defecto


def nombre_visible(p):
    return (p.get("nombre") or "").strip() or p.get("usuario") or "Alguien"


def cancion_fav_limpia(c):
    if not isinstance(c, dict):
        return None
    titulo = _texto(c.get("titulo")).strip()
    if not titulo and not c.get("video_id"):
        return None
    return {"video_id": _texto(c.get("video_id")), "titulo": titulo or "Canción",
            "artista": _texto(c.get("artista")), "miniatura": _texto(c.get("miniatura"))}


def subida_limpia(s):
    s = dict(s or {})
    return {"id": _texto(s.get("id")), "user_id": _texto(s.get("user_id")),
            "usuario": _texto(s.get("usuario")), "titulo": _texto(s.get("titulo")) or "Sin título",
            "artista": _texto(s.get("artista")), "album": _texto(s.get("album")),
            "duracion": _entero(s.get("duracion")), "ruta": _texto(s.get("ruta")),
            "portada": _texto(s.get("portada")), "escuchas": _entero(s.get("escuchas")),
            "estado": _texto(s.get("estado")) or "publicada", "creado": _texto(s.get("creado")),
            "es_artista": bool(s.get("es_artista")), "nota": _texto(s.get("nota")),
            "nombre": _texto(s.get("nombre")), "tamano": _entero(s.get("tamano")),
            "reportes": _entero(s.get("reportes")),
            "motivos": [str(m) for m in (s.get("motivos") or []) if m]}


def texto_estado(s):
    """(texto, tono) del estado de una canción propia; tono: 'aviso', 'error' o '' (publicada)."""
    e = (s or {}).get("estado")
    if e == "pendiente":
        return "En revisión", "aviso"
    if e == "revision":
        return "En revisión por reportes", "aviso"
    if e == "retirada":
        nota = (s.get("nota") or "").strip()
        return ("Rechazada: " + nota if nota else "Rechazada"), "error"
    return "", ""


def perfil_limpio(d):
    """Un perfil (de ver_perfil o del directorio) con todos sus campos."""
    d = dict(d or {})
    p = {
        "id": _texto(d.get("id")), "usuario": _texto(d.get("usuario")),
        "nombre": _texto(d.get("nombre")), "foto_url": d.get("foto_url") or None,
        "banner_url": d.get("banner_url") or None,
        "marco": marco_valido(d.get("marco")), "efecto_nombre": efecto_valido(d.get("efecto_nombre")),
        "bio": _texto(d.get("bio"), 300), "frase": _texto(d.get("frase"), 80),
        "cancion_fav": cancion_fav_limpia(d.get("cancion_fav")),
        "artista_fav": _texto(d.get("artista_fav"), 80),
        "generos": [str(g) for g in (d.get("generos") or []) if g][:5],
        "color_perfil": color_valido(d.get("color_perfil")),
        "relacion": _texto(d.get("relacion")) or "ninguna",
        "privado": bool(d.get("privado")), "es_mio": bool(d.get("es_mio")),
        "publico": bool(d.get("publico", d.get("perfil_publico", False))),
        "mostrar_top": bool(d.get("mostrar_top", True)),
        "likes": _entero(d.get("likes")), "di_like": bool(d.get("di_like")),
        "es_artista": bool(d.get("es_artista")) or _entero(d.get("likes")) >= LIKES_ARTISTA,
        "afinidad": d.get("afinidad") if isinstance(d.get("afinidad"), (int, float)) else None,
        "creado": _texto(d.get("creado")),
        "fundador": bool(d.get("fundador")), "fundador_caudal": bool(d.get("fundador_caudal")),
        "numero": _entero(d.get("numero"), 0) or None,
        "titulos": [{"clave": _texto(x.get("clave")), "nombre": _texto(x.get("nombre"))}
                    for x in (d.get("titulos") or []) if isinstance(x, dict) and x.get("clave")],
        "top_artistas": [x for x in (d.get("top_artistas") or []) if isinstance(x, dict) and x.get("nombre")],
        "top_canciones": [x for x in (d.get("top_canciones") or []) if isinstance(x, dict)],
        "insignias": [x for x in (d.get("insignias") or []) if isinstance(x, dict) and x.get("clave")],
        "subidas": [subida_limpia(x) for x in (d.get("subidas") or []) if isinstance(x, dict)],
    }
    p["num_subidas"] = _entero(d.get("num_subidas"), len(p["subidas"]))
    return p


def titulos_de(p):
    """Notas especiales de un perfil, de más a menos distinguida: lista de (clave, texto).
    Primero «Fundador de Caudal», luego los demás títulos que manda la base (con su nombre),
    después «Usuario fundador ★» y por último ARTISTA."""
    t, vistos = [], set()
    nombres = {x["clave"]: x["nombre"] for x in p.get("titulos") or []}
    if p.get("fundador_caudal") or "fundador_caudal" in nombres:
        t.append(("fundador_caudal", nombres.get("fundador_caudal") or "Fundador de Caudal"))
        vistos.add("fundador_caudal")
    for x in p.get("titulos") or []:
        if x["clave"] not in vistos:
            t.append((x["clave"], x["nombre"] or x["clave"].replace("_", " ").capitalize()))
            vistos.add(x["clave"])
    if p.get("fundador"):
        n = p.get("numero")
        t.append(("fundador", "Usuario fundador ★" if not n else f"Fundador n.º {n} ★"))
    if p.get("es_artista"):
        t.append(("artista", "ARTISTA"))
    return t


def tarjeta_limpia(d):
    """Una persona del directorio."""
    p = perfil_limpio(d)
    p["num_subidas"] = _entero((d or {}).get("num_subidas"))
    return p


def persona_limpia(d):
    """Una persona de las listas de amistades (solicitudes, amigos, bloqueados, búsqueda)."""
    d = dict(d or {})
    return {"id": _texto(d.get("id") or d.get("de") or d.get("para")),
            "solicitud": d.get("id") if "de" in d or "para" in d else None,
            "usuario": _texto(d.get("usuario")), "nombre": _texto(d.get("nombre")),
            "foto_url": d.get("foto_url") or None, "relacion": _texto(d.get("relacion")),
            "marco": marco_valido(d.get("marco")), "efecto_nombre": efecto_valido(d.get("efecto_nombre")),
            "creado": _texto(d.get("creado") or d.get("desde"))}


# --------------------------------------------------------------- amistad (texto y acciones)

def accion_amistad(relacion):
    """Qué botón corresponde según la relación: (texto, acción, ayuda).
    Acciones: enviar, cancelar, aceptar, escribir, desbloquear o None."""
    return {
        "ninguna": ("Agregar", "enviar", "Enviarle una solicitud de amistad"),
        "enviada": ("Solicitud enviada", "cancelar", "Toca para cancelar la solicitud"),
        "recibida": ("Aceptar solicitud", "aceptar", "Esta persona quiere ser tu amiga"),
        "amigo": ("Escribir", "escribir", "Abrir la conversación"),
        "bloqueado": ("Desbloquear", "desbloquear", "Dejar de tener bloqueada a esta persona"),
    }.get(relacion or "ninguna", (None, None, ""))


def relacion_tras_envio(respuesta):
    """Lo que devuelve enviar_solicitud -> la relación nueva."""
    return "amigo" if str(respuesta) in ("aceptada", "ya_amigos") else "enviada"


def mensaje_tras_envio(respuesta, nombre=""):
    r = str(respuesta)
    quien = f" con {nombre}" if nombre else ""
    if r == "aceptada":
        return f"¡Ya son amigos{quien}! Ahora pueden escribirse."
    if r == "ya_amigos":
        return "Ya son amigos."
    if r == "ya_enviada":
        return "Ya le habías enviado una solicitud. Esperando su respuesta."
    return "Solicitud enviada. Cuando la acepte podrán escribirse."


def explicar(e, que="hacer eso"):
    """Un error contado para personas, sin jerga."""
    if isinstance(e, SinConexion):
        return "Sin conexión. Revisa tu internet y vuelve a intentarlo."
    if isinstance(e, ErrorNube) and str(e).strip():
        return str(e)
    return f"No se pudo {que}. Vuelve a intentarlo."


def tiempo_corto(segundos):
    s = int(segundos or 0)
    if s <= 0:
        return ""
    m, seg = divmod(s, 60)
    return f"{m}:{seg:02d}"


def mes_anio(texto):
    """'2026-03-04T…' -> 'marzo de 2026' ('' si no se entiende)."""
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
             "octubre", "noviembre", "diciembre"]
    m = re.match(r"(\d{4})-(\d{2})", str(texto or ""))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return ""
    return f"{meses[int(m.group(2)) - 1]} de {m.group(1)}"


# --------------------------------------------------------------- imágenes (con Qt, sin Pillow)

def _cargar_imagen(origen):
    from PySide6.QtGui import QImage
    img = QImage()
    if isinstance(origen, (bytes, bytearray)):
        img.loadFromData(bytes(origen))
    else:
        img.load(str(origen))
    if img.isNull():
        raise ErrorNube("No se pudo abrir esa imagen. Elige un archivo jpg, png o webp.")
    return img


def recortar_cuadrado(img, lado):
    """Recorte cuadrado centrado y reducido a `lado` px (sin agrandar si es más chica)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    w, h = img.width(), img.height()
    t = min(w, h)
    cuadro = img.copy((w - t) // 2, (h - t) // 2, t, t)
    final = min(lado, t)
    if t != final:
        cuadro = cuadro.scaled(final, final, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    # el JPEG no tiene transparencia: se pone sobre blanco
    plano = QImage(final, final, QImage.Format_RGB32)
    plano.fill(QColor("#FFFFFF"))
    p = QPainter(plano)
    p.drawImage(0, 0, cuadro)
    p.end()
    return plano


def comprimir_jpeg(img, tope=TOPE_IMAGEN):
    """JPEG que pesa menos de `tope` bytes (baja la calidad hasta lograrlo)."""
    from PySide6.QtCore import QBuffer, QIODevice
    ultimo = b""
    for calidad in (90, 82, 74, 66, 58, 50, 40):
        b = QBuffer()
        b.open(QIODevice.WriteOnly)
        img.save(b, "JPEG", calidad)
        ultimo = bytes(b.data())
        if len(ultimo) < tope:
            return ultimo
    raise ErrorNube("La imagen sigue pesando demasiado. Elige otra más pequeña.")


def recortar_proporcion(img, ancho, alto):
    """Recorte centrado con la proporción ancho:alto, reducido a ese tamaño si es más grande."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage, QPainter
    w, h = img.width(), img.height()
    if w * alto > h * ancho:                      # demasiado ancha
        nw, nh = int(h * ancho / alto), h
    else:
        nw, nh = w, int(w * alto / ancho)
    corte = img.copy((w - nw) // 2, (h - nh) // 2, nw, nh)
    if nw > ancho:
        corte = corte.scaled(ancho, alto, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    plano = QImage(corte.width(), corte.height(), QImage.Format_RGB32)
    plano.fill(QColor("#FFFFFF"))
    p = QPainter(plano)
    p.drawImage(0, 0, corte)
    p.end()
    return plano


def preparar_banner(origen):
    """Imagen de fondo del perfil: 1280×480 como máximo, en JPEG de menos de 2 MB."""
    return comprimir_jpeg(recortar_proporcion(_cargar_imagen(origen), 1280, 480))


def preparar_foto(origen):
    """Foto de perfil: cuadrada de 512 px y en JPEG (bytes listos para subir)."""
    return comprimir_jpeg(recortar_cuadrado(_cargar_imagen(origen), LADO_FOTO))


def preparar_portada(origen):
    """Carátula de una canción: cuadrada, de 800 px como máximo, en JPEG."""
    return comprimir_jpeg(recortar_cuadrado(_cargar_imagen(origen), LADO_PORTADA))


# --------------------------------------------------------------- audio

def revisar_audio(ruta):
    """(extensión, tipo, tamaño) si el archivo se puede subir; si no, ErrorNube que lo explica."""
    p = Path(str(ruta or ""))
    if not p.is_file():
        raise ErrorNube("No se encontró ese archivo de audio. Elígelo de nuevo.")
    ext = p.suffix.lower()
    if ext not in AUDIOS:
        raise ErrorNube(f"El formato «{p.suffix or 'sin extensión'}» no se puede subir. "
                        "Usa mp3, m4a, aac, flac, ogg, wav o webm.")
    tam = p.stat().st_size
    if tam <= 0:
        raise ErrorNube("Ese archivo de audio está vacío.")
    if tam > TOPE_AUDIO:
        raise ErrorNube(f"Ese audio pesa {tam / 1048576:.1f} MB y el máximo es 15 MB. "
                        "Comprímelo (por ejemplo a mp3) y vuelve a intentarlo.")
    return ext, AUDIOS[ext], tam


def leer_datos_audio(ruta):
    """Título, artista, álbum y duración (lo que se pueda saber; nunca falla)."""
    p = Path(str(ruta))
    titulo, artista, album, duracion = p.stem, "", "", 0
    try:
        import mutagen
        m = mutagen.File(str(p), easy=True)
        if m is not None:
            titulo = (m.get("title") or [titulo])[0] or titulo
            artista = (m.get("artist") or m.get("albumartist") or [""])[0]
            album = (m.get("album") or [""])[0]
            duracion = int(getattr(m.info, "length", 0) or 0)
    except Exception:  # noqa: BLE001 - sin mutagen o archivo raro: se sigue con el nombre
        pass
    if not duracion and p.suffix.lower() == ".wav":
        try:
            import wave
            with wave.open(str(p)) as w:
                duracion = int(w.getnframes() / max(1, w.getframerate()))
        except Exception:  # noqa: BLE001
            pass
    if not artista and " - " in titulo:
        artista, titulo = [x.strip() for x in titulo.split(" - ", 1)]
    return {"titulo": titulo.strip()[:120], "artista": artista.strip()[:120],
            "album": album.strip()[:120], "duracion": max(0, min(7200, duracion))}


# --------------------------------------------------------------- reproducir lo de la comunidad

def carpeta_comunidad():
    c = carpeta_datos() / "comunidad"
    c.mkdir(parents=True, exist_ok=True)
    return c


def archivo_local(s):
    """Dónde se guarda la copia local de una canción de la comunidad."""
    ext = Path(str(s.get("ruta") or "")).suffix.lower()
    if ext not in AUDIOS:
        ext = ".mp3"
    return carpeta_comunidad() / f"{re.sub(r'[^0-9A-Za-z_-]', '', str(s.get('id')))}{ext}"


def descargar_subida(s, avance=None):
    """Baja la canción a la carpeta de datos (una vez) y devuelve su ruta.

    El motor de reproducción lee archivos del disco o direcciones de YouTube; una
    canción subida es un archivo suelto en la nube, así que se trae primero (15 MB
    como máximo) y suena como cualquier archivo local."""
    import requests
    destino = archivo_local(s)
    if destino.exists() and destino.stat().st_size > 0:
        return str(destino)
    url = url_musica(s.get("ruta"))
    if not url:
        raise ErrorNube("Esta canción ya no está disponible.")
    parcial = destino.with_suffix(destino.suffix + ".parte")
    try:
        with requests.get(url, stream=True, timeout=nube.TIEMPO) as r:
            if r.status_code == 404:
                raise ErrorNube("Esta canción ya no está disponible: quizá su dueño la borró.")
            if r.status_code >= 300:
                raise ErrorNube("No se pudo traer la canción. Vuelve a intentarlo.")
            total = int(r.headers.get("Content-Length") or 0)
            hecho = 0
            with open(parcial, "wb") as f:
                for trozo in r.iter_content(64 * 1024):
                    if not trozo:
                        continue
                    f.write(trozo)
                    hecho += len(trozo)
                    if hecho > TOPE_AUDIO * 2:
                        raise ErrorNube("Ese archivo es demasiado grande para reproducirlo.")
                    if avance and total:
                        try:
                            avance(hecho, total)
                        except Exception:  # noqa: BLE001
                            pass
        os.replace(parcial, destino)
    except requests.RequestException as e:
        raise SinConexion("No se pudo traer la canción. Revisa tu internet.") from e
    finally:
        try:
            if parcial.exists():
                parcial.unlink()
        except OSError:
            pass
    return str(destino)


def pista_de_subida(s, archivo):
    """La canción de la comunidad como pista que entiende el reproductor.

    Es una pista de archivo local (`archivo`, `es_audio`) con datos extra: `subida_id`,
    `subida_por` y `comunidad`, para que se pueda contar la escucha y mostrar quién la subió."""
    s = subida_limpia(s)
    artista = s["artista"] or (f"@{s['usuario']}" if s["usuario"] else "Comunidad de Caudal")
    return {
        "tipo": "pista", "clave": f"comunidad:{s['id']}", "video_id": "",
        "titulo": s["titulo"], "artista": artista,
        "artistas": [{"nombre": s["artista"], "id": ""}] if s["artista"] else [],
        "album": {"nombre": s["album"], "id": ""} if s["album"] else {},
        "duracion": s["duracion"], "miniatura": url_musica(s["portada"]),
        "archivo": archivo, "es_audio": True, "es_video": False,
        "subida_id": s["id"], "subida_por": s["usuario"], "comunidad": True,
    }


def pista_de_favorita(c):
    """La canción favorita de un perfil (de YouTube Music) lista para sonar."""
    c = cancion_fav_limpia(c)
    if not c or not c["video_id"]:
        return None
    vid = c["video_id"]
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": c["titulo"],
            "artista": c["artista"],
            "artistas": [{"nombre": c["artista"], "id": ""}] if c["artista"] else [],
            "album": {}, "duracion": 0,
            "miniatura": c["miniatura"] or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}


def pista_de_top(x):
    """Una canción del «top del mes» de un perfil (datos de pista + veces)."""
    vid = _texto(x.get("video_id"))
    if not vid and str(x.get("clave") or "").startswith("yt:"):
        vid = str(x["clave"])[3:]
    if not vid:
        return None
    p = {k: v for k, v in x.items() if k != "veces"}
    p.update(tipo="pista", clave=f"yt:{vid}", video_id=vid)
    if not p.get("miniatura"):
        p["miniatura"] = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    p.setdefault("titulo", "Canción")
    p.setdefault("artista", "")
    return p


def pista_de_item(item):
    """Una canción de una lista de la nube (`{clave, datos}`) lista para reproducir, o None."""
    datos = dict(item.get("datos") or {})
    datos.setdefault("clave", item.get("clave") or "")
    return pista_de_top(datos)


# --------------------------------------------------------------- la sesión

class Social:
    """Todo lo social de una cuenta. Las llamadas bloquean: úsalas con `en_segundo_plano`."""

    def __init__(self, sesion):
        self.sesion = sesion

    @property
    def yo(self):
        return self.sesion.user_id

    # ---- perfil
    def ver_perfil(self, usuario):
        """El perfil de alguien o None (no existe, o hay un bloqueo entre las dos personas)."""
        u = (usuario or "").strip().lstrip("@").lower()
        if not u:
            return None
        d = self.sesion.rpc("ver_perfil", p_usuario=u)
        return perfil_limpio(d) if isinstance(d, dict) else None

    def listas_de_perfil(self, usuario):
        """Las listas que se ven en el perfil de alguien (en el mío, todas, con sus ajustes).
        Sin la función nueva en la nube devuelve [] en vez de romper el perfil."""
        u = (usuario or "").strip().lstrip("@").lower()
        if not u:
            return []
        try:
            d = self.sesion.rpc("listas_de_perfil", p_usuario=u)
        except nube.ErrorNube:
            return []
        return [l for l in d if isinstance(l, dict)] if isinstance(d, list) else []

    def ver_lista_publica(self, lista_id):
        """Una lista pública (o mía) con todas sus canciones; None si no se puede abrir."""
        d = self.sesion.rpc("ver_lista_publica", p_lista=lista_id)
        return d if isinstance(d, dict) else None

    def guardar_perfil(self, campos):
        """Cambia mi perfil. Devuelve lo que quedó guardado (el servidor puede corregir cosas)."""
        filas = self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.yo}", json=campos,
                                  cabeceras={"Prefer": "return=representation"})
        return (filas or [{}])[0]

    def _subir_imagen_perfil(self, nombre, datos_jpeg, que, tipo="image/jpeg"):
        ruta = f"{self.yo}/{nombre}"
        try:
            self.sesion.subir_archivo(BUCKET_FOTOS, ruta, datos_jpeg, tipo, reemplazar=True)
        except SinConexion:
            raise
        except ErrorNube as e:
            raise ErrorNube(f"No se pudo guardar {que}. {e} Si sigue pasando, cierra sesión, "
                            "vuelve a entrar y prueba con otra imagen.") from e
        marcar_foto(ruta)
        return ruta

    def subir_foto(self, datos_jpeg):
        return self._subir_imagen_perfil("avatar.jpg", datos_jpeg, "tu foto")

    def subir_banner(self, datos_jpeg):
        return self._subir_imagen_perfil("banner.jpg", datos_jpeg, "tu imagen de fondo")

    def subir_foto_gif(self, datos_gif):
        """GIF animado como foto (solo donadores; el servidor descarta .gif de quien no puede)."""
        return self._subir_imagen_perfil("avatar.gif", datos_gif, "tu foto", "image/gif")

    def subir_banner_gif(self, datos_gif):
        return self._subir_imagen_perfil("banner.gif", datos_gif, "tu imagen de fondo", "image/gif")

    def borrar_variantes(self, nombres):
        """Borra, sin quejarse, archivos viejos de mi carpeta (p. ej. avatar.jpg al pasar a avatar.gif)."""
        try:
            self.sesion.borrar_archivos(BUCKET_FOTOS, [f"{self.yo}/{n}" for n in nombres])
        except ErrorNube:
            pass

    def quitar_banner(self):
        self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.yo}", json={"banner_url": None})
        try:
            self.sesion.borrar_archivos(BUCKET_FOTOS, [f"{self.yo}/banner.jpg"])
        except ErrorNube:
            pass

    # ---- fondo de la aplicación (solo Donador o Fundador de Caudal)
    def puede_poner_fondo(self):
        return self.sesion.rpc("puede_poner_fondo") is True

    # ---- premium: estado, pase de prueba y personalización
    def mi_premium(self):
        """{premium, tipo, vence} de mi cuenta (donador, fundador o prueba). {} si el servidor no responde algo útil."""
        d = self.sesion.rpc("mi_premium")
        return d if isinstance(d, dict) else {}

    def canjear_pase(self, codigo):
        """Canjea un código de prueba. Devuelve {ok, mensaje, dias, vence}."""
        d = self.sesion.rpc("canjear_pase", p_codigo=str(codigo or "").strip().upper())
        return d if isinstance(d, dict) else {"ok": False, "mensaje": "No se pudo comprobar el código."}

    # --- pases de regalo (solo donadores y fundadores; el servidor lo comprueba: supabase/pases_regalo.sql)
    def crear_pase_regalo(self):
        """Crea un código de regalo. Devuelve {ok, mensaje} o {ok, codigo, dias, caduca}."""
        d = self.sesion.rpc("crear_pase_regalo")
        return d if isinstance(d, dict) else {"ok": False, "mensaje": "No se pudo crear el código."}

    def mis_pases_regalo(self):
        """Mis últimos códigos de regalo: [{codigo, dias, usado, caduca, vigente}], los nuevos primero."""
        d = self.sesion.rpc("mis_pases_regalo")
        return [x for x in d if isinstance(x, dict)] if isinstance(d, list) else []

    def anular_pase_regalo(self, codigo):
        """Borra un código que nadie usó. True si se anuló."""
        return self.sesion.rpc("anular_pase_regalo", p_codigo=str(codigo or "").strip().upper()) is True

    def leer_personalizacion(self):
        """Mi marco, efecto de nombre y tema, tal como están guardados en mi perfil."""
        filas = self.sesion.pedir(
            "GET", f"perfiles?select=marco,efecto_nombre,tema_premium&id=eq.{self.yo}")
        d = (filas or [{}])[0] or {}
        from .premium_datos import tema_valido
        return {"marco": marco_valido(d.get("marco")), "efecto_nombre": efecto_valido(d.get("efecto_nombre")),
                "tema_premium": tema_valido(d.get("tema_premium"))}

    # --- más para donadores (supabase/donadores_extra.sql). Va aparte de leer_personalizacion: si la base
    # todavía no tiene estas columnas, lo de siempre (marco, efecto, tema) sigue funcionando.
    def leer_extra_donador(self):
        """Mi color del nombre y si quiero salir en la pared: {color_nombre, en_pared}."""
        from .premium_datos import color_valido
        filas = self.sesion.pedir("GET", f"perfiles?select=color_nombre,en_pared&id=eq.{self.yo}")
        d = (filas or [{}])[0] or {}
        return {"color_nombre": color_valido(d.get("color_nombre")), "en_pared": d.get("en_pared") is True}

    def guardar_extra_donador(self, campos):
        """Guarda `color_nombre` y/o `en_pared` (y nada más)."""
        limpio = {k: v for k, v in (campos or {}).items() if k in ("color_nombre", "en_pared")}
        if limpio:
            self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.yo}", json=limpio)

    def colores_nombre(self, usuarios):
        """{usuario: '#RRGGBB'} de los que tienen un color vigente (el servidor filtra)."""
        from .premium_datos import color_valido
        lista = sorted({str(u).strip().lower() for u in usuarios or [] if str(u or "").strip()})[:200]
        if not lista:
            return {}
        d = self.sesion.rpc("colores_nombre", p_usuarios=lista)
        salida = {}
        for u, c in (d.items() if isinstance(d, dict) else []):
            c = color_valido(c)
            if c:
                salida[str(u).lower()] = c
        return salida

    def pared_agradecimiento(self):
        from .premium_datos import leer_pared
        return leer_pared(self.sesion.rpc("pared_agradecimiento"))


    def subir_fondo(self, datos_jpeg):
        return self._subir_imagen_perfil("fondo.jpg", datos_jpeg, "tu fondo")

    def leer_fondo(self):
        filas = self.sesion.pedir(
            "GET", f"perfiles?select=fondo_url,fondo_visible,fondo_desenfoque&id=eq.{self.yo}")
        return (filas or [{}])[0] or {}

    def quitar_fondo(self):
        self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.yo}", json={"fondo_url": None})
        try:
            self.sesion.borrar_archivos(BUCKET_FOTOS, [f"{self.yo}/fondo.jpg"])
        except ErrorNube:
            pass

    def quitar_foto(self):
        self.sesion.pedir("PATCH", f"perfiles?id=eq.{self.yo}", json={"foto_url": None})
        try:
            self.sesion.borrar_archivos(BUCKET_FOTOS, [f"{self.yo}/avatar.jpg"])
        except ErrorNube:
            pass

    def dar_like(self, otro):
        return _entero(self.sesion.rpc("dar_like", p_otro=otro))

    def quitar_like(self, otro):
        return _entero(self.sesion.rpc("quitar_like", p_otro=otro))

    # ---- directorio
    def explorar_perfiles(self, busqueda="", limite=24, desde=0):
        filas = self.sesion.rpc("explorar_perfiles", p_busqueda=busqueda or "", p_limite=limite,
                                p_desde=desde) or []
        return [tarjeta_limpia(f) for f in filas if isinstance(f, dict)]

    # ---- amistades
    def enviar_solicitud(self, otro):
        return str(self.sesion.rpc("enviar_solicitud", p_otro=otro)).strip('"')

    def responder_solicitud(self, solicitud, acepta):
        self.sesion.rpc("responder_solicitud", p_id=solicitud, p_acepta=bool(acepta))

    def cancelar_solicitud(self, otro):
        self.sesion.rpc("cancelar_solicitud", p_otro=otro)

    def quitar_amigo(self, otro):
        self.sesion.rpc("quitar_amigo", p_otro=otro)

    def bloquear(self, otro):
        self.sesion.rpc("bloquear", p_otro=otro)

    def desbloquear(self, otro):
        self.sesion.rpc("desbloquear", p_otro=otro)

    def _personas(self, funcion):
        return [persona_limpia(f) for f in (self.sesion.rpc(funcion) or []) if isinstance(f, dict)]

    def mis_solicitudes(self):
        return self._personas("mis_solicitudes")

    def mis_enviadas(self):
        return self._personas("mis_enviadas")

    def mis_amigos(self):
        return self._personas("mis_amigos")

    def mis_bloqueados(self):
        return self._personas("mis_bloqueados")

    def contar_solicitudes(self):
        return len(self.mis_solicitudes())

    def buscar_persona(self, usuario):
        u = (usuario or "").strip().lstrip("@").lower()
        if not u:
            return None
        filas = self.sesion.rpc("buscar_persona", p_usuario=u) or []
        return persona_limpia(filas[0]) if filas else None

    # ---- música de la gente
    def explorar_subidas(self, busqueda="", limite=30, desde=0):
        filas = self.sesion.rpc("explorar_subidas", p_busqueda=busqueda or "", p_limite=limite,
                                p_desde=desde) or []
        return [subida_limpia(f) for f in filas if isinstance(f, dict)]

    # ---- moderación y publicación
    def publica_directo(self):
        """¿Lo que subo se publica sin revisión? Ante la duda, no (se dirá «en revisión»)."""
        try:
            return self.sesion.rpc("publica_directo") is True
        except ErrorNube:
            return False

    def soy_moderador(self):
        try:
            return self.sesion.rpc("soy_moderador") is True
        except ErrorNube:
            return False

    def revision_contar(self):
        try:
            return _entero(self.sesion.rpc("revision_contar"))
        except ErrorNube:
            return 0

    def revision_pendientes(self, limite=60):
        filas = self.sesion.rpc("revision_pendientes", p_limite=limite) or []
        return [subida_limpia(f) for f in filas if isinstance(f, dict)]

    def revision_resolver(self, subida, aprobar, nota=""):
        self.sesion.rpc("revision_resolver", p_id=subida, p_aprobar=bool(aprobar),
                        p_nota=(nota or "").strip()[:300])

    def contar_escucha(self, subida):
        try:
            self.sesion.rpc("contar_escucha_subida", p_id=subida)
        except Exception:  # noqa: BLE001 - contar no debe molestar a quien escucha
            pass

    def reportar(self, subida, motivo=""):
        self.sesion.rpc("reportar_subida", p_id=subida, p_motivo=(motivo or "")[:300])

    def borrar_subida(self, s):
        """Borra la canción y sus archivos."""
        self.sesion.rpc("borrar_subida", p_id=s["id"])
        try:
            self.sesion.borrar_archivos(BUCKET_MUSICA, [s.get("ruta"), s.get("portada")])
        except ErrorNube:
            pass
        try:
            archivo_local(s).unlink()
        except OSError:
            pass

    def subir_cancion(self, ruta_audio, ruta_portada, titulo, artista="", album="", duracion=0,
                      avance=None):
        """Sube audio + carátula y registra la canción. `avance(fraccion, texto)` informa.

        Si algo falla a medias se borra lo que ya se había subido. Devuelve el id nuevo."""
        titulo = (titulo or "").strip()
        if not titulo:
            raise ErrorNube("Escribe el título de la canción.")
        if not ruta_portada:
            raise ErrorNube("Elige la carátula: cada canción necesita una.")
        ext, tipo, tam = revisar_audio(ruta_audio)
        portada = preparar_portada(ruta_portada)

        def informar(f, texto):
            if avance:
                try:
                    avance(max(0.0, min(1.0, f)), texto)
                except Exception:  # noqa: BLE001
                    pass

        nombre = uuid.uuid4().hex
        r_audio = f"{self.yo}/{nombre}{ext}"
        r_portada = f"{self.yo}/{nombre}.jpg"
        subidos = []
        try:
            informar(0.02, "Subiendo la canción…")
            with open(ruta_audio, "rb") as f:
                datos = f.read()
            self.sesion.subir_archivo(BUCKET_MUSICA, r_audio, datos, tipo,
                                      avance=lambda a, t: informar(0.02 + 0.83 * a / max(1, t),
                                                                   "Subiendo la canción…"))
            subidos.append(r_audio)
            informar(0.88, "Subiendo la carátula…")
            self.sesion.subir_archivo(BUCKET_MUSICA, r_portada, portada, "image/jpeg")
            subidos.append(r_portada)
            informar(0.95, "Terminando…")
            nuevo = self.sesion.rpc("registrar_subida", p_titulo=titulo[:120],
                                    p_artista=(artista or "").strip()[:120],
                                    p_album=(album or "").strip()[:120],
                                    p_duracion=int(duracion or 0), p_ruta=r_audio,
                                    p_portada=r_portada, p_tamano=tam)
        except Exception:
            try:
                self.sesion.borrar_archivos(BUCKET_MUSICA, subidos)
            except Exception:  # noqa: BLE001
                pass
            raise
        informar(1.0, "¡Lista!")
        return str(nuevo).strip('"')


def social_de(ctx):
    """El objeto Social de la cuenta con internet, o None si no hay sesión."""
    cuenta = getattr(ctx, "cuenta", None) or {}
    s = cuenta.get("sesion")
    if s is not None and getattr(s, "access", ""):
        return Social(s)
    return None


def tipo_de_archivo(ruta):
    return mimetypes.guess_type(str(ruta))[0] or "application/octet-stream"


def pared_agradecimiento_publica():
    """La pared sin sesión (es pública, como en la web)."""
    from .premium_datos import leer_pared
    r = nube._peticion("POST", "/rest/v1/rpc/pared_agradecimiento", json={})
    if r.status_code >= 300:
        raise nube._traducir(r)
    return leer_pared(r.json() if r.text.strip() else [])
