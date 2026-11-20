# -*- coding: utf-8 -*-
"""Ajustes persistentes de la aplicacion."""

import json
import os
import sys
from pathlib import Path


APP_NOMBRE = "Caudal"


def raiz_app() -> Path:
    """Carpeta donde vive la aplicacion (soporta PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def carpeta_datos() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    ruta = Path(base) / "DescargadorVideos"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


# cuenta con la que se entro: su biblioteca y sus ajustes viven en su carpeta
PERFIL = {"carpeta": "", "cuenta": None}


def fijar_perfil(carpeta, cuenta=None):
    PERFIL["carpeta"] = carpeta or ""
    PERFIL["cuenta"] = cuenta


def carpeta_perfil() -> Path:
    """Datos de la cuenta activa (la primera cuenta usa la carpeta de siempre)."""
    ruta = carpeta_datos() / PERFIL["carpeta"] if PERFIL["carpeta"] else carpeta_datos()
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def cuenta_activa():
    return PERFIL["cuenta"] or {}


def carpeta_caratulas() -> Path:
    ruta = carpeta_datos() / "caratulas"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_ffmpeg() -> str:
    """Devuelve la carpeta con ffmpeg.exe, o cadena vacia si no esta."""
    candidatas = [raiz_app() / "bin", raiz_app() / "_internal" / "bin", carpeta_datos() / "bin"]
    for c in candidatas:
        if (c / "ffmpeg.exe").exists() or (c / "ffmpeg").exists():
            return str(c)
    # ffmpeg del sistema
    from shutil import which
    hallado = which("ffmpeg")
    if hallado:
        return str(Path(hallado).parent)
    return ""


def carpeta_descargas_por_defecto() -> str:
    for nombre in ("Downloads", "Descargas"):
        p = Path.home() / nombre
        if p.exists():
            return str(p / "Videos Descargados")
    return str(Path.home() / "Videos Descargados")


DEFECTOS = {
    "carpeta": carpeta_descargas_por_defecto(),
    "calidad": "mejor",
    "tipo_descarga": "completo",   # completo | video | audio
    "modo_musica": False,          # nivela el audio para que suene mas fuerte
    "sesion_token": "",            # sesion guardada del servidor
    "sesion_usuario": "",
    "mantener_sesion": True,
    # opcionales y gratuitos (developer.spotify.com): sin ellos Spotify solo
    # deja leer 50 canciones por lista
    "spotify_id": "",
    "spotify_secreto": "",
    # igual para SoundCloud (soundcloud.com/you/apps). Si se dejan vacios se usan los del
    # sitio de Caudal en Netlify, que son los que pone el dueno
    "soundcloud_id": "",
    "soundcloud_secreto": "",
    "formato_salida": "mp4",
    "formato_audio": "mp3",
    "simultaneas": 2,
    "playlist": False,
    "limite_playlist": 50,
    "subtitulos": False,
    "idioma_subtitulos": "es",
    "incrustar_subtitulos": True,
    "miniatura": True,
    "metadatos": True,
    "navegador_cookies": "ninguno",
    "archivo_cookies": "",
    "plantilla_nombre": "%(title).150B [%(id)s].%(ext)s",
    "subcarpeta_por_red": False,
    "limite_velocidad": 0,          # KB/s, 0 = sin limite
    "reintentos": 6,
    "proxy": "",
    "vigilar_portapapeles": False,
    "notificar_al_terminar": True,
    "abrir_al_terminar": False,
    "geometria": "",
    # --- descargas: calidad fina
    "codec_descarga": "maxima",      # maxima (AV1/VP9, hasta 8K) | compatible (H.264)
    "bitrate_mp3": "320",            # 128 | 192 | 256 | 320 | V0
    # --- reproduccion
    "region": "PE",
    "calidad_audio": "maxima",       # maxima | normal | ahorro
    "calidad_video": "maxima",       # maxima | 4320 | 2160 | 1440 | 1080 | 720 | 480 | 360
    "codec_video": "auto",           # auto | sin_av1 | compatible
    "aceleracion": True,             # decodificar con la tarjeta grafica si se puede
    "calidad_adaptable": True,       # bajar un escalon si el equipo pierde cuadros
    "crossfade": 0,                  # segundos de fundido entre canciones (0 = sin fundido)
    "traducir_letra": True,          # la traduccion bajo cada linea de la letra
    "acento": "cian",                # color de la app (estilos.ACENTOS)
    "fondo": "oscuro",               # fondo de la app (estilos.FONDOS)
    "tamano_personaje": 124,         # alto del personaje del fondo con personaje (se cambia con el ratón)
    "personaje_x": -1,               # dónde está el personaje: fracción 0..1 de la ventana; -1 = su esquina
    "personaje_y": -1,
    "personaje_baila": True,         # el personaje baila mientras suena la música
    "aviso_regalo_visto": False,     # ya se le avisó al donador de que puede regalar códigos de prueba
    "normalizar": True,              # mismo volumen percibido entre canciones
    "modo_noche": False,             # comprime el volumen: nada suena fuerte de golpe (ideal para dormir)
    "sonido_envolvente": False,      # ensancha el sonido en audifonos
    "autoplay": True,                # al acabarse la cola, seguir con canciones parecidas
    "sponsorblock": True,            # saltar lo que no es musica en videos musicales
    "sponsorblock_videos": False,    # y patrocinios / autopromocion en videos normales
    "preferir_descargado": True,     # si ya esta en el disco, sonar desde el disco
    "volumen": 80,
    "velocidad": 1.0,
    "aleatorio": False,
    "repetir": "no",                 # no | todo | una
    "ecualizador": False,
    "eq_bandas": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "eq_preset": "Plano",
    "segundo_plano": True,           # (antiguo) se sustituye por al_cerrar
    "al_cerrar": "preguntar",        # preguntar | bandeja | salir (con musica sonando)
    "escena_fondo": "video",         # fondo de la escena de escritorio: video | ambiente
    "mini_encima": True,             # el mini reproductor queda por encima de todo
    "letras_auto": False,            # abrir las letras al reproducir
    "vinilo_auto": False,            # abrir el modo vinilo al reproducir
    "vinilo_pantalla": True,         # el modo vinilo mantiene la pantalla encendida
    "visualizador_estilo": "ondas",  # ondas | particulas | barras (donadores)
    "colores_caratula": True,        # la barra y las vistas grandes toman los colores de la carátula (donadores)
    "sonidos_ui": False,             # sonidito al dar me gusta y al abrir (donadores)
    "sonido_ui_tipo": "burbuja",     # burbuja | moneda | campana
    "panel_derecho": "sonando",      # sonando | cola | letras | oculto
    "subtitulos_video": False,
    "teclas_multimedia": True,
    "super_volumen": 0,              # (antiguo) 0..4; se sigue escribiendo a juego con volumen_maximo
    # volumen maximo sin distorsion (sonoridad.py): no | normal | alto | maximo
    "volumen_maximo": "alto",
    # ecualizador avanzado (eq_avanzado.py, donadores y fundadores)
    "eq_avanzado": False,
    "eq_av_bandas": [0] * 15,
    "eq_av_preamp": 0.0,
    "eq_av_nombre": "",
    "eq_av_guardados": {},
    "eq_por_salida": {"audifonos": "", "parlante": "", "bluetooth": ""},
    "recordar_sesion": True,
    # --- compartidos con la app movil (mismas claves en los dos lados)
    "descarga_inteligente": False,   # bajar solo tus me gusta y lo mas escuchado
    "descarga_inteligente_gb": 5,    # hasta cuantos GB
    "transicion_dj": True,           # recortar silencios del final y del inicio al pasar
    "apagado_suave": True,           # el temporizador baja el volumen en los ultimos 30 s
    # --- mezcla DJ y aviso de novedades (solo de este equipo)
    "mezcla_dj": False,              # enlazar las canciones como un DJ (entra antes del final)
    "mezcla_dj_seg": 8,              # segundos de mezcla, de 4 a 16
    "mezcla_dj_graves": True,        # cambio de graves: los graves de una cancion ceden a los de la otra
    "version_novedades_vista": "",   # ultima version cuyo aviso de novedades grande ya se vio
    "presentacion_mascotas_vista": "",   # la presentacion de la 2.4.2 (mascotitas y fondos) ya se vio
    "cumple_celebrado": "",          # el dia (aaaa-mm-dd) en que ya salio la pantalla de «Feliz cumpleaños»
}


class Ajustes:
    def __init__(self):
        self.archivo = carpeta_perfil() / "ajustes.json"
        self.datos = dict(DEFECTOS)
        self.cargar()

    def cargar(self):
        try:
            if self.archivo.exists():
                guardado = json.loads(self.archivo.read_text(encoding="utf-8"))
                for k, v in guardado.items():
                    if k in DEFECTOS:
                        self.datos[k] = v
                # quien tenia el super volumen antiguo encendido conserva un nivel parecido
                from .sonoridad import migrar
                migrado = dict(guardado)
                if migrar(migrado):
                    self.datos["volumen_maximo"] = migrado["volumen_maximo"]
        except Exception:
            pass

    def guardar(self):
        try:
            self.archivo.write_text(
                json.dumps(self.datos, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def __getitem__(self, clave):
        return self.datos.get(clave, DEFECTOS.get(clave))

    def __setitem__(self, clave, valor):
        self.datos[clave] = valor

    def __contains__(self, clave):
        return clave in self.datos or clave in DEFECTOS

    def get(self, clave, defecto=None):
        return self.datos.get(clave, defecto if defecto is not None else DEFECTOS.get(clave))
