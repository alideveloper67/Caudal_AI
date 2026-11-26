# -*- coding: utf-8 -*-
"""Lo que hace falta para que la interfaz no dé tirones, en un solo sitio (lo llama main al abrir).

- Escribir en disco, el reconocedor de voz y las letras guardadas, fuera del hilo que pinta.
- El turno entre hilos de Python pasa de 5 a 1,5 ms: con un hilo de fondo trabajando, el que pinta
  esperaba 5 ms cada vez que quería dibujar (a 60 cuadros por segundo hay 16 ms para todo).
- El recolector de memoria: repasar todos los objetos de la app paraba la interfaz decenas de ms cada
  poco. Lo que hay cargado tras abrir no se vuelve a repasar, y lo nuevo, con menos frecuencia.
- Los módulos de las pantallas se cargan solos en un hilo, para que abrirlas la primera vez no espere
  al disco.
"""

import gc
import importlib
import sys
import threading
import time

TURNO_S = 0.0015
UMBRALES_GC = (20000, 25, 60)

# lo que se abre con un clic, por orden de lo que más se usa
PRECARGA = (
    "descargador.ui.sonando", "descargador.ui.letra_viva", "descargador.ui.paginas.coleccion",
    "descargador.ui.paginas.buscar", "descargador.ui.paginas.biblioteca", "descargador.ui.paginas.explorar",
    "descargador.ui.paginas.artista", "descargador.ui.aspecto", "descargador.ui.fondo_ajuste",
    "descargador.ui.mascotas_ajuste", "descargador.ui.personalizar_ajuste", "descargador.ui.mas_donadores",
    "descargador.ui.paginas.ajustes", "descargador.ui.selector_letra",
    "descargador.ui.escena.ventana", "descargador.ui.escena.escenarios.imagenes",
    "descargador.ui.escena.escenarios.retro", "descargador.ui.escena.escenarios.propia",
    "descargador.ui.escena.fondo_synthwave", "descargador.ui.epica", "descargador.ui.video",
    "descargador.ui.paginas.mensajes", "descargador.ui.paginas.juntos", "descargador.ui.paginas.perfil",
    "descargador.ui.paginas.resumen", "descargador.ui.paginas.modo_gamer", "descargador.ui.paginas.descargas",
    "descargador.ui.visualizador", "descargador.ui.karaoke", "descargador.ui.letra_escena",
    "descargador.ui.vinilo", "descargador.ui.paginas.estudio", "descargador.ui.paginas.mezclador",
    "descargador.recomendador", "descargador.mix_continuo", "descargador.generos",
    # avisos y celebraciones de los primeros segundos
    "descargador.ui.presentacion_100", "descargador.ui.novedades_grandes", "descargador.ui.presentacion_mascotas",
    "descargador.ui.aviso_regalo", "descargador.ui.cumpleanos_ui", "descargador.ui.dialogo_importacion",
    "descargador.ui.ecualizador", "descargador.ui.dialogo_listas", "descargador.ui.paginas.grupos",
    "descargador.ui.paginas.revision",
)

_precargado = threading.Event()
_empezado = False


def preparar(carpeta_datos):
    """Al abrir, antes de construir nada."""
    from . import ayudante, disco, letras_cache
    sys.setswitchinterval(TURNO_S)
    gc.set_threshold(*UMBRALES_GC)
    disco.activar()
    letras_cache.activar(carpeta_datos)
    ayudante.activar()


def _cargar_motor_de_musica():
    """yt-dlp monta sus extractores la primera vez que se usa: con el disco frío, entre 6 y 12 s que se
    sumaban a la primera canción y a la primera búsqueda en SoundCloud."""
    try:
        for nombre in ("yt_dlp", "ytmusicapi", "yt_dlp.extractor.youtube", "yt_dlp.extractor.soundcloud"):
            importlib.import_module(nombre)
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}):
            pass
    except Exception:  # noqa: BLE001 - se cargará al usarlo
        pass


def precargar(espera=1.5, pausa=0.04):
    """Carga los módulos de las pantallas en un hilo, de uno en uno."""
    global _empezado
    _empezado = True

    def trabajo():
        time.sleep(espera)
        _cargar_motor_de_musica()        # primero, lo que hace sonar la música
        for nombre in PRECARGA:
            try:
                if nombre not in sys.modules:
                    importlib.import_module(nombre)
                    time.sleep(pausa)
            except Exception:  # noqa: BLE001 - lo que no cargue se verá al abrirlo
                pass
        try:
            from . import letras_cache
            letras_cache.podar()
        except Exception:  # noqa: BLE001
            pass
        try:
            from .ui import tipografia_letra
            tipografia_letra.leer_todas()
        except Exception:  # noqa: BLE001
            pass
        _precargado.set()
    threading.Thread(target=trabajo, name="precarga", daemon=True).start()


def precargado():
    return _precargado.is_set()


def precargando():
    """Los módulos se están cargando: lo que no corre prisa, mejor que espere. Importar uno en el hilo que
    pinta, recién encendida la PC y con un disco de platos, paraba la ventana entre 8 y 20 segundos."""
    return _empezado and not _precargado.is_set()


def asentar():
    """Cuando la ventana ya está en pie: lo cargado hasta aquí no se vuelve a repasar."""
    gc.collect()
    gc.freeze()
