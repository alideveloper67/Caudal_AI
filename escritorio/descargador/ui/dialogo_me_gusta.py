# -*- coding: utf-8 -*-
"""«Pasar tus me gusta»: los de Spotify, YouTube Music y SoundCloud a los Me gusta de Caudal.

Cada servicio dice en una frase qué se puede hacer y, si algo falta, qué hacer.
Lo traído se busca en YouTube Music (DialogoImportacion) y se añade sin repetir.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from .. import importacion, listas, servicios_externos
from .estilos import C


class _Hilo(QThread):
    listo = Signal(object)
    fallo = Signal(str)

    def __init__(self, funcion):
        super().__init__()
        self.funcion = funcion

    def run(self):
        try:
            self.listo.emit(self.funcion())
        except (listas.ErrorLista, servicios_externos.ErrorServicio) as e:
            self.fallo.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.fallo.emit(f"No se pudo: {str(e)[:100]}")


def _texto(t, ayuda=True):
    l = QLabel(t)
    l.setWordWrap(True)
    if ayuda:
        l.setObjectName("ayuda")
    return l


class DialogoMeGusta(QDialog):
    listo = Signal(list, str, str, str)   # canciones, titulo, servicio, enlace

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.hilo = None
        self.setWindowTitle("Pasar tus me gusta")
        self.setMinimumSize(600, 620)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 20, 22, 18)
        raiz.setSpacing(12)
        titulo = QLabel("Pasar tus me gusta a Caudal")
        titulo.setStyleSheet("font-size:19px;font-weight:700;letter-spacing:-0.3px;")
        raiz.addWidget(titulo)
        raiz.addWidget(_texto("Las canciones que te gustan en otra app se buscan en YouTube Music "
                              "y se añaden a tus Me gusta de Caudal (aquí, en el teléfono y en la "
                              "web). Las que ya tenías no se repiten."))

        self.estado = _texto("", ayuda=False)
        self.estado.setStyleSheet(f"color:{C['texto2']};")
        raiz.addWidget(self.estado)

        cuerpo = QWidget()
        self.col = QVBoxLayout(cuerpo)
        self.col.setContentsMargins(0, 0, 0, 0)
        self.col.setSpacing(12)
        zona = QScrollArea()
        zona.setWidgetResizable(True)
        zona.setFrameShape(QFrame.NoFrame)
        zona.setWidget(cuerpo)
        raiz.addWidget(zona, 1)

        conf = servicios_externos.configuracion()
        self._seccion_spotify(conf)
        self._seccion_youtube()
        self._seccion_soundcloud(conf)
        self._seccion_fuentes()
        self.col.addStretch(1)

        fila = QHBoxLayout()
        fila.addStretch(1)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.reject)
        fila.addWidget(cerrar)
        raiz.addLayout(fila)

    # ------------------------------------------------------------ secciones

    def _tarjeta(self, nombre, color):
        caja = QFrame()
        caja.setObjectName("tarjeta")
        v = QVBoxLayout(caja)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(8)
        t = QLabel(nombre)
        t.setStyleSheet(f"font-size:15px;font-weight:700;color:{color};")
        v.addWidget(t)
        self.col.addWidget(caja)
        return v

    def _seccion_spotify(self, conf):
        v = self._tarjeta("Spotify", "#1DB954")
        if not conf.get("spotify_client_id"):
            v.addWidget(_texto(
                "Tus «Canciones que te gustan» de Spotify son privadas y la conexión con Spotify "
                "aún no está activada en Caudal."))
            v.addWidget(_texto(
                "Mientras tanto: en Spotify selecciona todas tus canciones que te gustan, "
                "añádelas a una lista nueva y pega aquí abajo, en «Desde un enlace», el enlace "
                "de esa lista. Ojo: sin la conexión oficial Spotify solo deja ver 50 canciones."))
            return
        conectado = servicios_externos.spotify_conectado()
        v.addWidget(_texto("Conecta tu cuenta y se traen todas tus canciones que te gustan." if not conectado
                           else "Tu cuenta de Spotify está conectada."))
        fila = QHBoxLayout()
        if conectado:
            traer = QPushButton("  Traer mis me gusta de Spotify")
            traer.setObjectName("principal")
            traer.clicked.connect(lambda: self._correr(
                servicios_externos.me_gusta_spotify, "Spotify", "spotify:me"))
            fila.addWidget(traer)
            salir = QPushButton("Desconectar")
            salir.clicked.connect(self._desconectar_spotify)
            fila.addWidget(salir)
        else:
            con = QPushButton("  Conectar con Spotify")
            con.setObjectName("principal")
            con.clicked.connect(self._conectar_spotify)
            fila.addWidget(con)
        fila.addStretch(1)
        v.addLayout(fila)
        v.addWidget(_texto("Mientras la app de Caudal esté en «modo desarrollo» de Spotify, solo "
                           "pueden conectarse las cuentas que el dueño de Caudal haya añadido."))

    def _seccion_youtube(self):
        v = self._tarjeta("YouTube Music", "#FF3B30")
        v.addWidget(_texto(
            "Caudal entra con Google solo para tu cuenta: no tiene permiso para leer tu YouTube, "
            "y pedirlo exige una revisión de Google. Haz esto: en YouTube Music abre «Música que te "
            "gusta», toca ⋮ › «Agregar a playlist», crea una lista pública o no listada y pega su "
            "enlace aquí abajo."))

    def _seccion_soundcloud(self, conf):
        v = self._tarjeta("SoundCloud", "#FF5500")
        hay = conf.get("soundcloud") or bool(
            listas._ajuste(self.ctx.ajustes, "soundcloud_id"))
        v.addWidget(_texto("Pega el enlace de un perfil (sus me gusta deben ser públicos)." if hay else
                           "La conexión oficial con SoundCloud aún no está activada en Caudal, así que "
                           "todavía no se pueden leer los me gusta de un perfil."))
        if not hay:
            return
        fila = QHBoxLayout()
        self.campo_sc = QLineEdit()
        self.campo_sc.setPlaceholderText("https://soundcloud.com/tu-perfil")
        fila.addWidget(self.campo_sc, 1)
        traer = QPushButton("  Traer sus me gusta")
        traer.setObjectName("principal")
        traer.clicked.connect(self._soundcloud)
        fila.addWidget(traer)
        v.addLayout(fila)

    def _seccion_fuentes(self):
        v = self._tarjeta("Desde un enlace", C["acento"])
        v.addWidget(_texto("Cualquier lista pública de Spotify, YouTube Music o SoundCloud: sus "
                           "canciones pasan a tus Me gusta."))
        fila = QHBoxLayout()
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Enlace de la lista")
        self.campo.returnPressed.connect(self._enlace)
        fila.addWidget(self.campo, 1)
        bt = QPushButton("  Pasar a Me gusta")
        bt.setObjectName("principal")
        bt.clicked.connect(self._enlace)
        fila.addWidget(bt)
        v.addLayout(fila)

        fuentes = self.ctx.coleccion.estado(importacion.CLAVE_FUENTES, []) or []
        if fuentes:
            v.addWidget(_texto("Ya sincronizadas (vuelve a pasar solo lo nuevo):"))
        for f in fuentes[:6]:
            if not isinstance(f, dict):
                continue
            fila = QHBoxLayout()
            fila.addWidget(_texto(f"{f.get('servicio') or ''} · {f.get('titulo') or f.get('enlace')}"
                                  f" · {importacion.miles(f.get('anadidas', 0))} añadidas"), 1)
            otra = QPushButton("Volver a sincronizar")
            otra.setObjectName("contorno")
            otra.clicked.connect(lambda _=False, f=f: self._repetir(f))
            fila.addWidget(otra)
            v.addLayout(fila)

    # ------------------------------------------------------------ acciones

    def _correr(self, funcion, servicio, enlace):
        if self.hilo and self.hilo.isRunning():
            return
        self.estado.setStyleSheet(f"color:{C['texto2']};")
        self.estado.setText("Leyendo tus canciones…")
        self.hilo = _Hilo(funcion)
        self.hilo.listo.connect(lambda d: self._leido(d, servicio, enlace))
        self.hilo.fallo.connect(self._fallo)
        self.hilo.start()

    def _leido(self, datos, servicio, enlace):
        canciones = datos.get("canciones") or []
        if not canciones:
            self._fallo("No llegó ninguna canción.")
            return
        self.listo.emit(canciones, datos.get("titulo") or servicio,
                        datos.get("plataforma") or servicio, enlace)
        self.accept()

    def _fallo(self, texto):
        self.estado.setStyleSheet(f"color:{C['error']};")
        self.estado.setText(texto or "Se canceló.")

    def _enlace(self):
        url = self.campo.text().strip()
        if not url:
            return
        nombres = {"spotify": "Spotify", "youtube": "YouTube Music", "soundcloud": "SoundCloud",
                   "apple": "Apple Music"}
        self._correr(lambda: listas.leer(url, self.ctx.ajustes),
                     nombres.get(listas.detectar_plataforma(url), "Enlace"), url)

    def _soundcloud(self):
        url = self.campo_sc.text().strip()
        if not url:
            return
        if listas.tipo_soundcloud(url)[0] == "perfil":
            url = url.rstrip("/") + "/likes"
        self._correr(lambda: listas.leer(url, self.ctx.ajustes), "SoundCloud", url)

    def _repetir(self, fuente):
        enlace = fuente.get("enlace") or ""
        if enlace == "spotify:me":
            self._correr(servicios_externos.me_gusta_spotify, "Spotify", enlace)
        elif enlace:
            self._correr(lambda: listas.leer(enlace, self.ctx.ajustes),
                         fuente.get("servicio") or "", enlace)

    def _conectar_spotify(self):
        self.estado.setText("Se abrió el navegador: entra en Spotify y acepta.")
        hilo = _Hilo(servicios_externos.conectar_spotify)
        hilo.listo.connect(lambda _ok: self._recargar("Cuenta de Spotify conectada."))
        hilo.fallo.connect(self._fallo)
        self.hilo = hilo
        hilo.start()

    def _desconectar_spotify(self):
        servicios_externos.desconectar_spotify()
        self._recargar("Cuenta de Spotify desconectada.")

    def _recargar(self, texto):
        # se rehace el diálogo para que la tarjeta de Spotify cambie de estado
        padre = self.parent()
        self.accept()
        nuevo = DialogoMeGusta(self.ctx, padre)
        nuevo.listo.connect(lambda *a: self.listo.emit(*a))
        nuevo.estado.setText(texto)
        nuevo.exec()
