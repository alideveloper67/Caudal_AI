# -*- coding: utf-8 -*-
"""«Vincular Spotify, YouTube y SoundCloud»: sus me gusta pasan a los Me gusta de Caudal.

Con la cuenta vinculada se traen solos; y sin vincular nada, desde el archivo con tus datos que da
cada servicio, desde cualquier tabla de canciones o pegando los nombres. Lo traído se busca en
YouTube Music (DialogoImportacion) y se añade sin repetir.
"""

import time

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from .. import archivo_me_gusta, importacion, listas, servicios_externos, vinculadas
from ..hilos import en_segundo_plano
from .estilos import C

COLORES = {"spotify": "#1DB954", "youtube": "#FF4E45", "soundcloud": "#FF7733"}
_VIVOS = set()          # un hilo que espera al navegador no se destruye aunque se cierre la ventana


class _Hilo(QThread):
    listo = Signal(object)
    fallo = Signal(str)

    def __init__(self, funcion):
        super().__init__()
        self.funcion = funcion
        self.cancelar = False
        _VIVOS.add(self)
        self.finished.connect(self._soltar)

    def _soltar(self):
        _VIVOS.discard(self)

    def run(self):
        try:
            self.listo.emit(self.funcion())
        except (listas.ErrorLista, servicios_externos.ErrorServicio,
                archivo_me_gusta.ErrorArchivo) as e:
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
    # canciones, titulo, servicio, enlace, cuenta ('spotify'|'youtube'|'soundcloud' o '')
    listo = Signal(list, str, str, str, str)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.hilo = None
        self.campo_sc = None
        self.setWindowTitle("Vincular Spotify, YouTube y SoundCloud")
        self.setMinimumSize(620, 660)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 20, 22, 18)
        raiz.setSpacing(12)
        titulo = QLabel("Vincular Spotify, YouTube y SoundCloud")
        titulo.setStyleSheet("font-size:19px;font-weight:700;letter-spacing:-0.3px;")
        raiz.addWidget(titulo)
        raiz.addWidget(_texto("Las canciones que te gustan allí pasan a tus Me gusta de Caudal (aquí, en el "
                              "teléfono y en la web). Las que ya tenías no se repiten."))

        self.estado = _texto("", ayuda=False)
        self.estado.setStyleSheet(f"color:{C['texto2']};")
        self.estado.hide()
        raiz.addWidget(self.estado)

        zona = QScrollArea()
        zona.setObjectName("lienzo")
        zona.setWidgetResizable(True)
        zona.setFrameShape(QFrame.NoFrame)
        zona.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zona = zona
        raiz.addWidget(zona, 1)

        fila = QHBoxLayout()
        fila.addStretch(1)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.reject)
        fila.addWidget(cerrar)
        raiz.addLayout(fila)

        self.conf = servicios_externos.configuracion_en_memoria() or dict(servicios_externos.VACIA)
        self._pintar()
        # qué está activado se pregunta aparte: la ventana se abre al instante
        en_segundo_plano(servicios_externos.configuracion, ok=self._llego_conf,
                         error=lambda _e: None, dueno=self)

    # ------------------------------------------------------------ pintado

    def _llego_conf(self, conf):
        if conf and dict(conf) != dict(self.conf):
            self.conf = dict(conf)
            self._pintar()

    def _pintar(self):
        escrito = getattr(self, "campo_texto", None)
        texto = escrito.toPlainText() if escrito is not None else ""
        enlace = self.campo.text() if getattr(self, "campo", None) is not None else ""
        cuerpo = QWidget()
        self.col = QVBoxLayout(cuerpo)
        self.col.setContentsMargins(0, 0, 6, 0)
        self.col.setSpacing(12)
        self.campo_sc = None
        self._seccion_servicio("spotify", "Spotify", [
            "1. Entra en tu cuenta de Spotify y pide «Descargar tus datos» (los datos de la cuenta).",
            "2. Cuando llegue el correo, baja el .zip.",
            "3. Elígelo aquí, sin abrirlo."], "Pedir mis datos a Spotify",
            "https://www.spotify.com/account/privacy/")
        self._seccion_servicio("youtube", "YouTube y YouTube Music", [
            "1. En Google Takeout marca solo «YouTube y YouTube Music» y crea la exportación.",
            "2. Cuando llegue el correo, baja el .zip.",
            "3. Elígelo aquí, sin abrirlo."], "Abrir Google Takeout", "https://takeout.google.com/")
        self._seccion_servicio("soundcloud", "SoundCloud", [], "", "")
        self._seccion_archivo(texto)
        self._seccion_enlace(enlace)
        self._seccion_fuentes()
        self.col.addStretch(1)
        barra = self.zona.verticalScrollBar().value()
        self.zona.setWidget(cuerpo)
        self.zona.verticalScrollBar().setValue(barra)

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

    def _boton(self, texto, accion, principal=False):
        b = QPushButton(texto)
        b.setObjectName("principal" if principal else "contorno")
        b.setCursor(Qt.PointingHandCursor)
        b.setAutoDefault(False)
        b.clicked.connect(lambda _=False: accion())
        return b

    def _fila(self, v, *botones):
        fila = QHBoxLayout()
        fila.setSpacing(8)
        for b in botones:
            fila.addWidget(b)
        fila.addStretch(1)
        v.addLayout(fila)

    def _seccion_servicio(self, servicio, nombre, pasos, texto_enlace, enlace):
        v = self._tarjeta(nombre, COLORES[servicio])
        corto = servicios_externos.NOMBRES[servicio]
        activado = bool(servicios_externos.client_id(self.conf, servicio))
        if servicios_externos.vinculada(servicio):
            self._vinculada(v, servicio, corto)
            return
        if activado:
            v.addWidget(_texto(f"Vincula tu cuenta de {corto}: se traen todos tus me gusta y Caudal los "
                               "mantiene al día."))
            self._fila(v, self._boton(f"  Vincular {corto}", lambda: self._vincular(servicio), True))
            if servicio == "spotify":
                v.addWidget(_texto("Spotify solo deja vincular unas pocas cuentas. Si no acepta la tuya, usa "
                                   "el archivo con tus datos."))
        if servicio == "soundcloud":
            self._soundcloud_sin_vincular(v, activado)
            return
        if not activado:
            v.addWidget(_texto(f"Trae tus me gusta con el archivo que te da {corto}:", ayuda=False))
        for p in pasos:
            v.addWidget(_texto(p))
        self._fila(v, self._boton(texto_enlace, lambda: QDesktopServices.openUrl(QUrl(enlace))),
                   self._boton("Elegir el archivo", self._elegir_archivo, not activado))

    def _soundcloud_sin_vincular(self, v, activado):
        hay = self.conf.get("soundcloud") or bool(listas._ajuste(self.ctx.ajustes, "soundcloud_id"))
        if hay:
            v.addWidget(_texto("O pega el enlace de tu perfil (tus me gusta tienen que ser públicos)."))
            fila = QHBoxLayout()
            self.campo_sc = QLineEdit()
            self.campo_sc.setPlaceholderText("https://soundcloud.com/tu-perfil")
            self.campo_sc.returnPressed.connect(self._soundcloud)
            fila.addWidget(self.campo_sc, 1)
            fila.addWidget(self._boton("Traer sus me gusta", self._soundcloud))
            v.addLayout(fila)
        elif not activado:
            v.addWidget(_texto("Copia los nombres de tus canciones de SoundCloud y pégalos más abajo, en "
                               "«Desde un archivo o un texto». Si los tienes en una tabla (.csv), elígela allí."))

    def _vinculada(self, v, servicio, corto):
        d = vinculadas.info(self.ctx.coleccion, servicio)
        n = d["cuantas"]
        detalle = f"Cuenta vinculada · {vinculadas.hace_cuanto(d['ultima'])}"
        if d["ultima"]:
            detalle += f" · {importacion.miles(n)} {'canción traída' if n == 1 else 'canciones traídas'}"
        v.addWidget(_texto(detalle, ayuda=False))
        caja = QCheckBox("Mantener al día (al abrir Caudal, como mucho cada 12 horas)")
        caja.setChecked(d["mantener"])
        caja.toggled.connect(lambda si: vinculadas.anotar(self.ctx.coleccion, servicio, mantener=bool(si)))
        v.addWidget(caja)
        self._fila(v, self._boton("  Sincronizar ahora", lambda: self._sincronizar(servicio), True),
                   self._boton("Desvincular", lambda: self._desvincular(servicio)))
        v.addWidget(_texto(f"Tu sesión de {corto} se queda en esta PC. Al desvincular se borra; las canciones "
                           "que ya trajiste se quedan."))

    def _seccion_archivo(self, texto=""):
        v = self._tarjeta("Desde un archivo o un texto", C["acento"])
        v.addWidget(_texto("Sirve el .zip de Spotify o de Google Takeout, cualquier tabla .csv con título y "
                           "artista (Exportify, TuneMyMusic, Soundiiz…) o un .txt."))
        self._fila(v, self._boton("Elegir un archivo", self._elegir_archivo))
        v.addWidget(_texto("O pega tus canciones, una por línea:"))
        self.campo_texto = QPlainTextEdit(texto)
        self.campo_texto.setPlaceholderText("Artista - Título\nArtista - Título")
        self.campo_texto.setTabChangesFocus(True)
        self.campo_texto.setFixedHeight(84)
        v.addWidget(self.campo_texto)
        self._fila(v, self._boton("Pasar a Me gusta", self._pegado))

    def _seccion_enlace(self, texto=""):
        v = self._tarjeta("Desde un enlace", C["acento"])
        v.addWidget(_texto("Cualquier lista pública de Spotify, YouTube Music o SoundCloud."))
        fila = QHBoxLayout()
        self.campo = QLineEdit(texto)
        self.campo.setPlaceholderText("Enlace de la lista")
        self.campo.returnPressed.connect(self._enlace)
        fila.addWidget(self.campo, 1)
        fila.addWidget(self._boton("Pasar a Me gusta", self._enlace))
        v.addLayout(fila)

    def _seccion_fuentes(self):
        fuentes = [f for f in (self.ctx.coleccion.estado(importacion.CLAVE_FUENTES, []) or [])
                   if isinstance(f, dict) and str(f.get("enlace") or "").startswith("http")]
        if not fuentes:
            return
        v = self._tarjeta("Ya traídas", C["texto"])
        for f in fuentes[:6]:
            fila = QHBoxLayout()
            fila.addWidget(_texto(f"{f.get('servicio') or ''} · {f.get('titulo') or f.get('enlace')}"
                                  f" · {importacion.miles(f.get('anadidas', 0))} añadidas"), 1)
            fila.addWidget(self._boton("Volver a traer", lambda f=f: self._repetir(f)))
            v.addLayout(fila)

    # ------------------------------------------------------------ acciones

    def _decir(self, texto, error=False):
        self.estado.setStyleSheet(f"color:{C['error'] if error else C['texto2']};")
        self.estado.setText(texto)
        self.estado.setVisible(bool(texto))

    def _ocupado(self):
        return self.hilo is not None and self.hilo.isRunning()

    def _lanzar(self, funcion, al_terminar):
        self.hilo = _Hilo(funcion)
        self.hilo.listo.connect(al_terminar)
        self.hilo.fallo.connect(self._fallo)
        self.hilo.start()

    def _correr(self, funcion, servicio, enlace, cuenta=""):
        if self._ocupado():
            return self._decir("Espera: todavía se está leyendo lo anterior.")
        self._decir("Leyendo tus canciones…")
        self._lanzar(funcion, lambda d: self._leido(d, servicio, enlace, cuenta))

    def _leido(self, datos, servicio, enlace, cuenta=""):
        canciones = datos.get("canciones") or []
        if enlace.endswith(":me"):
            # de una cuenta vinculada solo se busca lo que aún no se trajo
            col = self.ctx.coleccion
            canciones = vinculadas.nuevas(canciones, vinculadas.conocidas(col, cuenta))
            if not canciones:
                vinculadas.anotar(col, cuenta, ultima=time.time(), completa=True)
                self._pintar()
                return self._decir("Ya lo tienes todo: no hay canciones nuevas.")
        if not canciones:
            return self._fallo("No llegó ninguna canción.")
        self.listo.emit(canciones, datos.get("titulo") or servicio,
                        datos.get("plataforma") or servicio, enlace, cuenta)
        self.accept()

    def _fallo(self, texto):
        self._decir(texto or "Se canceló.", error=True)

    def _enlace(self):
        url = self.campo.text().strip()
        if not url:
            return
        nombres = {"spotify": "Spotify", "youtube": "YouTube Music", "soundcloud": "SoundCloud",
                   "apple": "Apple Music"}
        self._correr(lambda: listas.leer(url, self.ctx.ajustes),
                     nombres.get(listas.detectar_plataforma(url), "Enlace"), url)

    def _soundcloud(self):
        url = self.campo_sc.text().strip() if self.campo_sc is not None else ""
        if not url:
            return
        if listas.tipo_soundcloud(url)[0] == "perfil":
            url = url.rstrip("/") + "/likes"
        self._correr(lambda: listas.leer(url, self.ctx.ajustes), "SoundCloud", url)

    def _repetir(self, fuente):
        enlace = fuente.get("enlace") or ""
        self._correr(lambda: listas.leer(enlace, self.ctx.ajustes), fuente.get("servicio") or "", enlace)

    def _elegir_archivo(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige el archivo con tus canciones", "",
                                               archivo_me_gusta.FILTRO_DIALOGO)
        if ruta:
            self.traer_archivo(ruta)

    def traer_archivo(self, ruta):
        if self._ocupado():
            return self._decir("Espera: todavía se está leyendo lo anterior.")
        self._decir("Leyendo el archivo…")
        self._lanzar(lambda: archivo_me_gusta.desde_archivo(ruta), self._leido_archivo)

    def _leido_archivo(self, datos):
        servicio = datos.get("servicio") or ""
        self._leido(datos, datos.get("plataforma") or "", f"archivo:{servicio or 'lista'}", servicio)

    def _pegado(self):
        try:
            datos = archivo_me_gusta.desde_texto(self.campo_texto.toPlainText())
        except archivo_me_gusta.ErrorArchivo as e:
            return self._fallo(str(e))
        self._leido(datos, "Tu lista", "archivo:texto")

    def _vincular(self, servicio):
        if self._ocupado():
            return
        nombre = servicios_externos.NOMBRES[servicio]
        self._decir(f"Se abrió el navegador: entra en {nombre} y acepta.")
        hilo = _Hilo(None)
        hilo.funcion = lambda: servicios_externos.vincular(servicio, cancelado=lambda: hilo.cancelar)
        hilo.listo.connect(lambda _ok: self._recien_vinculada(servicio))
        hilo.fallo.connect(self._fallo)
        self.hilo = hilo
        hilo.start()

    def _recien_vinculada(self, servicio):
        self._pintar()
        self._decir("Cuenta vinculada. Leyendo tus me gusta…")
        self.hilo.wait(2000)          # el hilo del navegador ya acabó: se puede empezar a leer
        self._sincronizar(servicio)

    def _sincronizar(self, servicio):
        nombre = "YouTube Music" if servicio == "youtube" else servicios_externos.NOMBRES[servicio]
        self._correr(lambda: servicios_externos.me_gusta(servicio), nombre, f"{servicio}:me", servicio)

    def _desvincular(self, servicio):
        if self._ocupado():
            return self._decir("Espera: todavía se está leyendo lo anterior.")
        vinculadas.olvidar(self.ctx.coleccion, servicio)
        nombre = servicios_externos.NOMBRES[servicio]

        def hecho(_r):
            self._pintar()
            self._decir(f"Cuenta de {nombre} desvinculada.")
        # retirar el permiso en Google toca la red: aparte
        self._lanzar(lambda: servicios_externos.desvincular(servicio), hecho)

    def done(self, r):
        # si se cierra mientras espera al navegador, se deja de esperar
        if self.hilo is not None:
            self.hilo.cancelar = True
            for s in (self.hilo.listo, self.hilo.fallo):
                try:
                    s.disconnect()
                except (RuntimeError, TypeError):
                    pass
        super().done(r)
