# -*- coding: utf-8 -*-
"""Ajustes: todo se cambia desde aqui, con una explicacion corta de cada cosa."""

import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout,
                               QWidget)

from ... import catalogo, mpv_carga, version
from ...config import DEFECTOS, carpeta_datos, ruta_ffmpeg
from ...hilos import en_segundo_plano
from ...motor import formato_bytes
from .. import iconos, imagenes
from ..componentes import Pagina
from ..estilos import C

NAVEGADORES = [("No usar cookies", "ninguno"), ("Chrome", "chrome"), ("Edge", "edge"),
               ("Firefox", "firefox"), ("Brave", "brave"), ("Opera", "opera"),
               ("Vivaldi", "vivaldi"), ("Chromium", "chromium")]
REGIONES = [("Perú", "PE"), ("México", "MX"), ("Argentina", "AR"), ("Colombia", "CO"),
            ("Chile", "CL"), ("España", "ES"), ("Estados Unidos", "US"), ("Venezuela", "VE"),
            ("Ecuador", "EC"), ("Bolivia", "BO"), ("Uruguay", "UY"), ("Paraguay", "PY"),
            ("Brasil", "BR"), ("Reino Unido", "GB")]


class Seccion(QFrame):
    def __init__(self, titulo, padre=None):
        super().__init__(padre)
        self.setObjectName("caja")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 18, 22, 10)
        self.v.setSpacing(0)
        t = QLabel(titulo)
        t.setStyleSheet("font-size:18px;font-weight:800;margin-bottom:6px;")
        self.v.addWidget(t)

    def fila(self, titulo, ayuda, widget):
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 10, 0, 10)
        h.setSpacing(18)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        t = QLabel(titulo)
        t.setStyleSheet("font-size:14px;font-weight:600;")
        textos.addWidget(t)
        if ayuda:
            a = QLabel(ayuda)
            a.setObjectName("secundario")
            a.setWordWrap(True)
            textos.addWidget(a)
        h.addLayout(textos, 1)
        if widget is not None:
            h.addWidget(widget, 0, Qt.AlignVCenter | Qt.AlignRight)
        self.v.addWidget(caja)
        return caja


def _combo(opciones, valor, ancho=240):
    c = QComboBox()
    for etiqueta, v in opciones:
        c.addItem(etiqueta, v)
    i = c.findData(valor)
    c.setCurrentIndex(i if i >= 0 else 0)
    c.setFixedWidth(ancho)
    return c


def _interruptor(valor):
    c = QCheckBox()
    c.setChecked(bool(valor))
    c.setCursor(Qt.PointingHandCursor)
    return c


class PaginaAjustes(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Ajustes"
        self.a = ctx.ajustes
        a = self.a
        t = QLabel("Ajustes")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        self.cuerpo.addWidget(t)
        self.cuerpo.setSpacing(16)

        # ---------------- aspecto
        from ..aspecto import SelectorAspecto
        from ..estilos import ACTUAL
        s = Seccion("Aspecto")
        self.selector_aspecto = SelectorAspecto(a, (ACTUAL["acento"], ACTUAL["fondo"]))
        self.selector_aspecto.aplicar.connect(self._aplicar_aspecto)
        s.v.addWidget(self.selector_aspecto)
        self.cuerpo.addWidget(s)

        # ---------------- fondo de Caudal (solo Donador o Fundador de Caudal: si no, ni aparece)
        gestor_fondo = getattr(ctx, "fondo", None)
        self.seccion_fondo = None
        if gestor_fondo is not None:
            from ..fondo_ajuste import SeccionFondo
            self.seccion_fondo = SeccionFondo(gestor_fondo, self.lienzo)
            self.cuerpo.addWidget(self.seccion_fondo)
            gestor_fondo.verificar_permiso()

        # ---------------- reproduccion
        s = Seccion("Reproducción")
        self.calidad_audio = _combo([("Máxima (Opus ~160 kbps, o 256 kbps con Premium)", "maxima"),
                                     ("Normal (~128 kbps)", "normal"),
                                     ("Ahorro de datos (~64 kbps)", "ahorro")],
                                    a["calidad_audio"], 380)
        self._conectar(self.calidad_audio, "calidad_audio")
        s.fila("Calidad del audio", "Lo que suena en streaming. Lo descargado suena siempre "
                                    "con su propia calidad.", self.calidad_audio)
        self.calidad_video = _combo([("Máxima disponible (hasta 8K)", "maxima"), ("8K", "4320"),
                                     ("4K", "2160"), ("1440p", "1440"), ("1080p", "1080"),
                                     ("720p", "720"), ("480p", "480"), ("360p", "360")],
                                    a["calidad_video"], 260)
        self._conectar(self.calidad_video, "calidad_video")
        s.fila("Calidad del video", "Resolución con la que empiezan los videos. Puedes "
                                    "cambiarla mientras ves cada uno.", self.calidad_video)
        self.codec = _combo([("Automático: la mejor imagen (AV1/VP9)", "auto"),
                             ("Evitar AV1 (equipos de hace unos años)", "sin_av1"),
                             ("Solo H.264 (el más ligero, hasta 1080p)", "compatible")],
                            a["codec_video"], 380)
        self._conectar(self.codec, "codec_video")
        s.fila("Códec del video", "AV1 da la mejor imagen pero exige mucho al equipo si la "
                                  "tarjeta gráfica no lo acelera.", self.codec)
        self.adaptable = _interruptor(a["calidad_adaptable"])
        self._conectar(self.adaptable, "calidad_adaptable")
        s.fila("Bajar la calidad si el video se traba",
               "Si tu equipo no llega a mostrar todos los cuadros, baja un escalón y te avisa.",
               self.adaptable)
        self.acel = _interruptor(a["aceleracion"])
        self._conectar(self.acel, "aceleracion", self._aplicar_aceleracion)
        s.fila("Aceleración por hardware", "Usa la tarjeta gráfica para decodificar el video "
                                           "(menos consumo y menos calor).", self.acel)
        self.preferir = _interruptor(a["preferir_descargado"])
        self._conectar(self.preferir, "preferir_descargado")
        s.fila("Usar lo descargado cuando exista", "Si una canción ya está en tu disco suena "
                                                   "desde ahí: al instante y sin internet.",
               self.preferir)
        self.autoplay = _interruptor(a["autoplay"])
        self._conectar(self.autoplay, "autoplay")
        s.fila("Reproducción automática", "Al terminar tu cola siguen canciones parecidas, "
                                          "para que la música no pare.", self.autoplay)
        self.sponsor = _interruptor(a["sponsorblock"])
        self._conectar(self.sponsor, "sponsorblock")
        s.fila("Saltar lo que no es música", "En los videos musicales salta las intros habladas y "
                                             "los finales sin música (base de SponsorBlock).",
               self.sponsor)
        self.sponsor_v = _interruptor(a["sponsorblock_videos"])
        self._conectar(self.sponsor_v, "sponsorblock_videos")
        s.fila("Saltar patrocinios en los videos", "En videos normales salta las menciones "
                                                    "pagadas, autopromoción y '¡suscríbete!'.",
               self.sponsor_v)
        self.letras = _interruptor(a["letras_auto"])
        self._conectar(self.letras, "letras_auto")
        s.fila("Mostrar la letra al reproducir", "Abre la letra en el panel derecho cuando "
                                                 "empieza una canción.", self.letras)
        self.vinilo = _interruptor(a["vinilo_auto"])
        self._conectar(self.vinilo, "vinilo_auto")
        s.fila("Mostrar el vinilo al reproducir", "Cuando empieza una canción se abre el tocadiscos "
                                                  "a pantalla completa, con la carátula girando. "
                                                  "También lo abres con el botón del disco.",
               self.vinilo)
        self.suave = _interruptor(a["apagado_suave"])
        self._conectar(self.suave, "apagado_suave")
        s.fila("Apagar la música poco a poco", "Con el temporizador para dormir, el volumen va "
                                               "bajando durante los últimos 30 segundos en vez "
                                               "de cortarse de golpe.", self.suave)
        self.region = _combo(REGIONES, a["region"], 200)
        self._conectar(self.region, "region", lambda: catalogo.fijar_region(self.a["region"]))
        s.fila("País para las recomendaciones", "Inicio, novedades y tendencias de este país.",
               self.region)
        self.bt_gustos = QPushButton("Elegir artistas")
        self.bt_gustos.setObjectName("contorno")
        self.bt_gustos.setCursor(Qt.PointingHandCursor)
        self.bt_gustos.clicked.connect(self._elegir_gustos)
        s.fila("Mis artistas favoritos", "Los artistas que elegiste al crear tu cuenta. Caudal los "
                                         "usa para recomendarte música parecida.", self.bt_gustos)
        self.cuerpo.addWidget(s)

        # ---------------- sonido
        s = Seccion("Sonido")
        self.normalizar = _interruptor(a["normalizar"])
        self._conectar(self.normalizar, "normalizar", ctx.reproductor.aplicar_sonido)
        s.fila("Igualar el volumen entre canciones", "Las canciones suaves y las fuertes suenan "
                                        "parecido, sin tocar los cambios de volumen de cada una.",
               self.normalizar)
        from ...reproduccion import NOMBRES_SUPER_VOLUMEN
        self.super = _combo([(n, k) for k, n in NOMBRES_SUPER_VOLUMEN.items()],
                            int(a["super_volumen"] or 0), 200)
        self._conectar(self.super, "super_volumen",
                       lambda: (ctx.reproductor.aplicar_sonido(), ctx.sonido_cambio.emit()))
        s.fila("Súper volumen", "Mucho más fuerte sin que se rompa el sonido: un limitador "
                                "evita la saturación. También en el botón del altavoz de abajo.",
               self.super)
        caja_fundido = QWidget()
        hf = QHBoxLayout(caja_fundido)
        hf.setContentsMargins(0, 0, 0, 0)
        self.fundido = QSlider(Qt.Horizontal)
        self.fundido.setRange(0, 12)
        self.fundido.setValue(int(a["crossfade"] or 0))
        self.fundido.setFixedWidth(200)
        self.et_fundido = QLabel()
        self.et_fundido.setFixedWidth(60)
        hf.addWidget(self.fundido)
        hf.addWidget(self.et_fundido)
        self.fundido.valueChanged.connect(self._fundido)
        self._fundido(self.fundido.value(), guardar=False)
        s.fila("Fundido entre canciones", "Una canción se funde con la siguiente, sin silencio "
                                          "entre medias.", caja_fundido)
        self.dj = _interruptor(a["transicion_dj"])
        self._conectar(self.dj, "transicion_dj")
        s.fila("Transiciones como un DJ", "Al pasar de canción se recortan los silencios del "
                                          "final y del principio, para que la siguiente entre "
                                          "justo a tiempo. Funciona con y sin fundido.", self.dj)
        self.mezcla = _interruptor(a["mezcla_dj"])
        self._conectar(self.mezcla, "mezcla_dj", self._mezcla_cambio)
        s.fila("Mezcla DJ", "Las canciones se enlazan solas, como en una cabina: la siguiente "
                            "entra antes de que acabe la que suena. Si la activas, manda sobre "
                            "el fundido de arriba.", self.mezcla)
        caja_mezcla = QWidget()
        hm = QHBoxLayout(caja_mezcla)
        hm.setContentsMargins(0, 0, 0, 0)
        self.mezcla_seg = QSlider(Qt.Horizontal)
        self.mezcla_seg.setRange(4, 16)
        self.mezcla_seg.setValue(max(4, min(16, int(a["mezcla_dj_seg"] or 8))))
        self.mezcla_seg.setFixedWidth(200)
        self.mezcla_seg.setAccessibleName("Segundos de la mezcla DJ")
        self.et_mezcla_seg = QLabel()
        self.et_mezcla_seg.setFixedWidth(60)
        hm.addWidget(self.mezcla_seg)
        hm.addWidget(self.et_mezcla_seg)
        self.mezcla_seg.valueChanged.connect(self._mezcla_segundos)
        self._mezcla_segundos(self.mezcla_seg.value(), guardar=False)
        self.fila_mezcla_seg = s.fila("Duración de la mezcla", "Cuántos segundos dura el "
                                      "enlace entre dos canciones (de 4 a 16).", caja_mezcla)
        self.mezcla_graves = _interruptor(a["mezcla_dj_graves"])
        self._conectar(self.mezcla_graves, "mezcla_dj_graves")
        self.fila_mezcla_graves = s.fila(
            "Cambio de graves", "Mientras entra la nueva se le quitan los graves y, a mitad "
                                "del enlace, pasan de una canción a la otra. Así no se pisan "
                                "los bajos.", self.mezcla_graves)
        self._mezcla_cambio()
        bt_eq = QPushButton("  Abrir el ecualizador")
        bt_eq.setIcon(iconos.icono("ecualizador", 16, C["texto"]))
        bt_eq.setCursor(Qt.PointingHandCursor)
        bt_eq.clicked.connect(lambda: ctx.ventana.abrir_ecualizador())
        s.fila("Ecualizador de 10 bandas", "Con ajustes listos para graves, voces, reguetón, "
                                           "rock… o a tu medida.", bt_eq)
        self.musica_fuerte = _interruptor(a["modo_musica"])
        self._conectar(self.musica_fuerte, "modo_musica")
        s.fila("Descargar el audio más fuerte", "Lo que descargues como audio se nivela para "
                                                "sonar muy fuerte sin romperse (ideal parlantes).",
               self.musica_fuerte)
        self.cuerpo.addWidget(s)

        # ---------------- ventana
        s = Seccion("Ventana y segundo plano")
        self.bandeja = _combo([("Preguntarme", "preguntar"),
                               ("Seguir sonando en segundo plano", "bandeja"),
                               ("Cerrar Caudal del todo", "salir")], a["al_cerrar"], 280)
        self._conectar(self.bandeja, "al_cerrar")
        s.fila("Al cerrar la ventana con música sonando",
               "«Seguir sonando» deja Caudal junto al reloj de Windows; para salir del todo: "
               "clic derecho en su icono → Salir, o Ctrl+Q.", self.bandeja)
        self.mini_encima = _interruptor(a["mini_encima"])
        self._conectar(self.mini_encima, "mini_encima")
        s.fila("Mini reproductor siempre encima", "La ventanita de video o música flota sobre "
                                                  "las demás apps.", self.mini_encima)
        self.teclas = _interruptor(a["teclas_multimedia"])
        self._conectar(self.teclas, "teclas_multimedia", self._teclas)
        s.fila("Teclas multimedia del teclado", "Reproducir, pausar, siguiente y anterior "
                                                "funcionan aunque Caudal esté minimizado.",
               self.teclas)
        self.portapapeles = _interruptor(a["vigilar_portapapeles"])
        self._conectar(self.portapapeles, "vigilar_portapapeles")
        s.fila("Detectar enlaces copiados", "Al copiar un enlace de video te ofrece reproducirlo "
                                            "o descargarlo.", self.portapapeles)
        self.notificar = _interruptor(a["notificar_al_terminar"])
        self._conectar(self.notificar, "notificar_al_terminar")
        s.fila("Avisar al terminar cada descarga", "", self.notificar)
        self.cuerpo.addWidget(s)

        # ---------------- descargas
        s = Seccion("Descargas")
        caja_c = QWidget()
        hc = QHBoxLayout(caja_c)
        hc.setContentsMargins(0, 0, 0, 0)
        self.carpeta = QLineEdit(a["carpeta"])
        self.carpeta.setFixedWidth(330)
        self.carpeta.editingFinished.connect(self._guardar_carpeta)
        bt_ex = QPushButton("Cambiar")
        bt_ex.setCursor(Qt.PointingHandCursor)
        bt_ex.clicked.connect(self._elegir_carpeta)
        hc.addWidget(self.carpeta)
        hc.addWidget(bt_ex)
        s.fila("Carpeta de descargas", "", caja_c)
        self.plantilla = QLineEdit(a["plantilla_nombre"])
        self.plantilla.setFixedWidth(330)
        self.plantilla.editingFinished.connect(
            lambda: self._poner("plantilla_nombre", self.plantilla.text().strip()
                                or DEFECTOS["plantilla_nombre"]))
        s.fila("Nombre de los archivos", "Plantilla de yt-dlp: %(title)s, %(artist)s, %(id)s, "
                                         "%(uploader)s…", self.plantilla)
        self.bitrate = _combo([("320 kbps", "320"), ("256 kbps", "256"), ("192 kbps", "192"),
                               ("128 kbps", "128"), ("VBR máxima (V0)", "V0")], a["bitrate_mp3"], 200)
        self._conectar(self.bitrate, "bitrate_mp3")
        s.fila("Calidad de los MP3", "", self.bitrate)
        self.simultaneas = QSpinBox()
        self.simultaneas.setRange(1, 8)
        self.simultaneas.setValue(int(a["simultaneas"]))
        self.simultaneas.valueChanged.connect(lambda v: (self._poner("simultaneas", v),
                                                         ctx.gestor.actualizar_simultaneas(v)))
        s.fila("Descargas a la vez", "", self.simultaneas)
        self.velocidad = QSpinBox()
        self.velocidad.setRange(0, 200000)
        self.velocidad.setSingleStep(256)
        self.velocidad.setSuffix(" KB/s")
        self.velocidad.setSpecialValueText("Sin límite")
        self.velocidad.setValue(int(a["limite_velocidad"]))
        self.velocidad.valueChanged.connect(lambda v: self._poner("limite_velocidad", v))
        s.fila("Límite de velocidad", "Deja ancho de banda libre para lo demás.", self.velocidad)
        self.playlist = _interruptor(a["playlist"])
        self._conectar(self.playlist, "playlist")
        s.fila("Bajar listas y perfiles completos", "Al pegar el enlace de una lista, baja "
                                                    "todos sus videos.", self.playlist)
        self.tope = QSpinBox()
        self.tope.setRange(1, 5000)
        self.tope.setValue(int(a["limite_playlist"]))
        self.tope.valueChanged.connect(lambda v: self._poner("limite_playlist", v))
        s.fila("Máximo por lista", "", self.tope)
        self.subcarpeta = _interruptor(a["subcarpeta_por_red"])
        self._conectar(self.subcarpeta, "subcarpeta_por_red")
        s.fila("Una subcarpeta por cada red social", "", self.subcarpeta)
        self.miniatura = _interruptor(a["miniatura"])
        self._conectar(self.miniatura, "miniatura")
        s.fila("Poner la portada dentro del archivo", "", self.miniatura)
        self.metadatos = _interruptor(a["metadatos"])
        self._conectar(self.metadatos, "metadatos")
        s.fila("Guardar título, artista y capítulos", "", self.metadatos)
        self.subtitulos = _interruptor(a["subtitulos"])
        self._conectar(self.subtitulos, "subtitulos")
        s.fila("Descargar subtítulos", "", self.subtitulos)
        self.idiomas = QLineEdit(a["idioma_subtitulos"])
        self.idiomas.setFixedWidth(160)
        self.idiomas.editingFinished.connect(
            lambda: self._poner("idioma_subtitulos", self.idiomas.text().strip() or "es"))
        s.fila("Idiomas de los subtítulos", "Códigos separados por comas: es, en, pt", self.idiomas)
        self.cuerpo.addWidget(s)

        # ---------------- descarga inteligente
        s = Seccion("Descarga inteligente")
        self.inteligente = _interruptor(a["descarga_inteligente"])
        self._conectar(self.inteligente, "descarga_inteligente", self._inteligente_cambio)
        s.fila("Bajar sola tu música favorita",
               "Caudal descarga en segundo plano tus me gusta y lo que más escuchas, para que "
               "suene sin internet. Va despacio y se aparta cuando ves un video o cuando algo "
               "está cargando, para no cortar lo que suena.", self.inteligente)
        self.inteligente_gb = QSpinBox()
        self.inteligente_gb.setRange(1, 500)
        self.inteligente_gb.setSuffix(" GB")
        self.inteligente_gb.setValue(max(1, int(a["descarga_inteligente_gb"] or 5)))
        self.inteligente_gb.valueChanged.connect(
            lambda v: (self._poner("descarga_inteligente_gb", int(v)), self._inteligente_cambio()))
        s.fila("Espacio máximo", "Cuando se llena, deja de bajar. Lo ya descargado no se borra.",
               self.inteligente_gb)
        self.et_inteligente = QLabel("")
        self.et_inteligente.setObjectName("secundario")
        self.et_inteligente.setWordWrap(True)
        s.fila("Cómo va", "", self.et_inteligente)
        self.cuerpo.addWidget(s)
        self._preparar_inteligente()

        # ---------------- cuenta
        s = Seccion("Tu cuenta de YouTube (opcional)")
        nota = QLabel("Sin cuenta todo funciona. Con tu sesión de YouTube (si tienes Premium) "
                      "llega el audio de 256 kbps y los videos con restricción de edad. Caudal "
                      "lee la sesión del navegador donde ya la tienes abierta; ciérralo antes "
                      "de reproducir para que Windows deje leerla.")
        nota.setWordWrap(True)
        nota.setObjectName("secundario")
        s.v.addWidget(nota)
        self.navegador = _combo(NAVEGADORES, a["navegador_cookies"], 200)
        self._conectar(self.navegador, "navegador_cookies")
        s.fila("Usar la sesión de", "", self.navegador)
        caja_ck = QWidget()
        hk = QHBoxLayout(caja_ck)
        hk.setContentsMargins(0, 0, 0, 0)
        self.cookies = QLineEdit(a["archivo_cookies"])
        self.cookies.setPlaceholderText("cookies.txt (opcional)")
        self.cookies.setFixedWidth(260)
        self.cookies.editingFinished.connect(
            lambda: self._poner("archivo_cookies", self.cookies.text().strip()))
        bt_ck = QPushButton("Elegir")
        bt_ck.clicked.connect(self._elegir_cookies)
        hk.addWidget(self.cookies)
        hk.addWidget(bt_ck)
        s.fila("O un archivo de cookies", "", caja_ck)
        self.proxy = QLineEdit(a["proxy"])
        self.proxy.setPlaceholderText("socks5://127.0.0.1:1080")
        self.proxy.setFixedWidth(260)
        self.proxy.editingFinished.connect(lambda: self._poner("proxy", self.proxy.text().strip()))
        s.fila("Proxy", "Para contenido bloqueado en tu país.", self.proxy)
        self.cuerpo.addWidget(s)

        # ---------------- almacenamiento
        s = Seccion("Almacenamiento y privacidad")
        self.et_cache = QLabel("")
        self.et_cache.setObjectName("secundario")
        bt_cache = QPushButton("Vaciar")
        bt_cache.clicked.connect(self._vaciar_cache)
        caja_cache = QWidget()
        hca = QHBoxLayout(caja_cache)
        hca.setContentsMargins(0, 0, 0, 0)
        hca.addWidget(self.et_cache)
        hca.addWidget(bt_cache)
        s.fila("Portadas guardadas", "Se guardan para que todo cargue al instante y sin internet.",
               caja_cache)
        bt_escuchas = QPushButton("Borrar")
        bt_escuchas.clicked.connect(self._borrar_escuchas)
        s.fila("Historial de escuchas", "«Volver a escuchar», tus mixes y lo reciente.", bt_escuchas)
        bt_busq = QPushButton("Borrar")
        bt_busq.clicked.connect(lambda: (ctx.coleccion.borrar_busquedas(),
                                         ctx.aviso.emit("Búsquedas recientes borradas")))
        s.fila("Búsquedas recientes", "", bt_busq)
        bt_datos = QPushButton("Abrir")
        bt_datos.clicked.connect(lambda: __import__("os").startfile(str(carpeta_datos())))
        s.fila("Carpeta de datos de Caudal", str(carpeta_datos()), bt_datos)
        self.cuerpo.addWidget(s)

        # ---------------- motor
        s = Seccion("Motor y versión")
        self.et_motor = QLabel("")
        self.et_motor.setObjectName("secundario")
        self.et_motor.setWordWrap(True)
        self.et_motor.setTextInteractionFlags(Qt.TextSelectableByMouse)
        s.v.addWidget(self.et_motor)
        bt_motor = QPushButton("Actualizar yt-dlp")
        bt_motor.clicked.connect(self._actualizar_motor)
        s.fila("Motor de YouTube y otros sitios", "Si un sitio deja de funcionar de golpe, "
                                                  "actualiza: las webs cambian a menudo.", bt_motor)
        self.bt_version = QPushButton("Buscar actualizaciones")
        self.bt_version.clicked.connect(lambda: ctx.ventana.buscar_version(False))
        self.et_version = s.fila(f"Caudal {version.VERSION}", "", self.bt_version)
        bt_defecto = QPushButton("Restaurar")
        bt_defecto.setObjectName("peligro")
        bt_defecto.clicked.connect(self._restaurar)
        s.fila("Volver a los ajustes de fábrica", "Tus listas, me gusta y descargas no se tocan.",
               bt_defecto)
        self.cuerpo.addWidget(s)
        self.cuerpo.addStretch(1)
        self._pintar_motor()
        self._pintar_cache()

    # ------------------------------------------------------------ guardar

    def _poner(self, clave, valor):
        self.a[clave] = valor
        self.a.guardar()

    def _elegir_gustos(self):
        """Reabre «¿Qué artistas te gustan?» con lo elegido, para cambiarlo."""
        from ... import gustos as G
        from .. import pantalla_gustos
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        sesion = cuenta.get("sesion")
        gestor = G.Gustos(sesion, self.ctx.coleccion) if sesion is not None else None
        inicial = []
        if gestor is not None:
            inicial = gestor.local()["lista"]
        accion, lista = pantalla_gustos.abrir(gestor, inicial, ajustes=True,
                                              region=self.a["region"], padre=self.window())
        if accion != "guardar":
            return
        if gestor is None:
            self.ctx.coleccion.guardar_estado(G.CLAVE, {"lista": lista, "elegidos": True,
                                                       "pendiente": False})
            return
        def listo(llego):
            aviso = getattr(self.ctx, "aviso", None)
            if aviso is not None:
                aviso.emit("Tus artistas favoritos se guardaron." if llego else
                           "Se guardaron aquí; se subirán cuando haya conexión.")
        en_segundo_plano(gestor.guardar, lista, ok=listo, error=lambda _e: None, dueno=self)

    def _conectar(self, widget, clave, despues=None):
        if isinstance(widget, QCheckBox):
            widget.toggled.connect(lambda v: (self._poner(clave, bool(v)), despues and despues()))
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(
                lambda _i: (self._poner(clave, widget.currentData()), despues and despues()))

    def _aplicar_aspecto(self):
        ventana = getattr(self.ctx, "ventana", None)
        if ventana is not None and hasattr(ventana, "reabrir_con_aspecto"):
            ventana.reabrir_con_aspecto()
        else:
            getattr(self.ctx, "reiniciar", lambda: None)()

    def _mezcla_cambio(self):
        activa = self.mezcla.isChecked()
        self.fila_mezcla_seg.setEnabled(activa)
        self.fila_mezcla_graves.setEnabled(activa)

    def _mezcla_segundos(self, v, guardar=True):
        self.et_mezcla_seg.setText(f"{v} s")
        if guardar:
            self._poner("mezcla_dj_seg", int(v))

    def _fundido(self, v, guardar=True):
        self.et_fundido.setText(f"{v} s" if v else "Sin fundido")
        if guardar:
            self._poner("crossfade", int(v))

    # ------------------------------------------------------------ descarga inteligente

    def _descarga_inteligente(self):
        return getattr(self.ctx.reproductor, "descarga_inteligente", None)

    def _preparar_inteligente(self):
        self.et_inteligente.setFixedWidth(320)
        self.et_inteligente.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        di = self._descarga_inteligente()
        if di is None:
            self.et_inteligente.setText("No disponible en este equipo.")
            return
        if di.gestor is None:
            di.gestor = self.ctx.gestor          # para no pisar tus descargas
        if not getattr(di, "_avisa_biblioteca", False):
            di._avisa_biblioteca = True
            di.descargada.connect(lambda _p: self.ctx.descargas_cambio.emit())
        di.cambio.connect(self._pintar_inteligente)
        self._pintar_inteligente()

    def _inteligente_cambio(self):
        di = self._descarga_inteligente()
        if di is not None:
            di.ajustes_cambiaron()
        self._pintar_inteligente()

    def _pintar_inteligente(self):
        try:
            di = self._descarga_inteligente()
            if di is None:
                return
            e = di.estado()
            usado = formato_bytes(e["usado"]) if e["usado"] else "0 MB"
            texto = f"Usado {usado} de {e['limite_gb']} GB"
            if not e["activa"]:
                texto += " · apagada"
            elif e["bajando"]:
                texto += f" · bajando «{e['bajando']}»"
            elif e["motivo"]:
                texto += " · " + e["motivo"]
            self.et_inteligente.setText(texto)
        except RuntimeError:
            pass        # la pagina ya se cerro

    def _teclas(self):
        tm = getattr(self.ctx.ventana, "teclas_multimedia", None)
        if tm is None:
            return
        if self.a["teclas_multimedia"] and self.ctx.reproductor.actual is not None:
            tm.registrar()
        else:
            tm.soltar()

    def _aplicar_aceleracion(self):
        for m in self.ctx.reproductor.videos.values():
            m.fijar_aceleracion(self.a["aceleracion"])

    def _guardar_carpeta(self):
        self._poner("carpeta", self.carpeta.text().strip() or DEFECTOS["carpeta"])
        self.ctx.descargas_cambio.emit()

    def _elegir_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de descargas", self.a["carpeta"])
        if carpeta:
            self.carpeta.setText(carpeta)
            self._guardar_carpeta()

    def _elegir_cookies(self):
        archivo, _ = QFileDialog.getOpenFileName(self, "Archivo de cookies", "",
                                                 "Cookies (*.txt);;Todos (*.*)")
        if archivo:
            self.cookies.setText(archivo)
            self._poner("archivo_cookies", archivo)

    def _pintar_cache(self):
        self.et_cache.setText(formato_bytes(imagenes.tamano_cache()))

    def _vaciar_cache(self):
        for f in imagenes.carpeta_cache().glob("*.img"):
            try:
                f.unlink()
            except OSError:
                pass
        self._pintar_cache()
        self.ctx.aviso.emit("Portadas borradas: se volverán a bajar cuando hagan falta")

    def _borrar_escuchas(self):
        r = QMessageBox.question(self, "Caudal", "¿Borrar tu historial de escuchas? Inicio dejará "
                                                 "de mostrar lo reciente y tus mixes.")
        if r == QMessageBox.Yes:
            self.ctx.coleccion.borrar_escuchas()
            self.ctx.aviso.emit("Historial de escuchas borrado")

    def _pintar_motor(self):
        try:
            import yt_dlp
            v_yt = yt_dlp.version.__version__
        except Exception:
            v_yt = "no disponible"
        mod = mpv_carga.modulo()
        if mod is not None:
            try:
                import locale
                locale.setlocale(locale.LC_NUMERIC, "C")
                m = self.ctx.reproductor.audio[0].mpv if self.ctx.reproductor.audio else None
                v_mpv = m.mpv_version if m is not None else "cargado"
            except Exception:
                v_mpv = "cargado"
        else:
            v_mpv = "NO ENCONTRADO: " + (mpv_carga.error() or "")
        ff = ruta_ffmpeg()
        self.et_motor.setText(f"yt-dlp {v_yt}\nReproductor: {v_mpv}\n"
                              f"ffmpeg: {ff or 'NO ENCONTRADO'}")

    def _actualizar_motor(self):
        if getattr(sys, "frozen", False):
            QMessageBox.information(self, "Caudal", "En la versión instalada, el motor se "
                                                    "actualiza con cada versión nueva de Caudal "
                                                    "(Buscar actualizaciones).")
            return
        self.ctx.aviso.emit("Actualizando yt-dlp…")

        def hacer():
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                               capture_output=True, text=True, timeout=300,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return r.returncode == 0, r.stderr

        def listo(res):
            ok, err = res
            if ok:
                QMessageBox.information(self, "Caudal", "Motor actualizado. Reinicia Caudal para "
                                                        "usar la versión nueva.")
            else:
                QMessageBox.warning(self, "Caudal", f"No se pudo actualizar:\n{(err or '')[:400]}")
        en_segundo_plano(hacer, ok=listo, error=lambda e: QMessageBox.warning(self, "Caudal",
                                                                              str(e)), dueno=self)

    def _restaurar(self):
        r = QMessageBox.question(self, "Caudal", "Se restaurarán todos los ajustes. Tus listas, "
                                                 "me gusta y descargas no se tocan. ¿Continuar?")
        if r != QMessageBox.Yes:
            return
        for k, v in DEFECTOS.items():
            if k not in ("geometria", "sesion_token", "sesion_usuario"):
                self.a[k] = list(v) if isinstance(v, list) else v
        self.a.guardar()
        self.ctx.reproductor.aplicar_sonido()
        if self._descarga_inteligente() is not None:
            self._descarga_inteligente().ajustes_cambiaron()
        self.ctx.navegar({"pagina": "ajustes"})
        self.ctx.aviso.emit("Ajustes restaurados")
