# -*- coding: utf-8 -*-
"""Panel de la derecha: lo que suena, la cola y la letra sincronizada."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import catalogo
from ..hilos import en_segundo_plano
from .componentes import BotonIcono, FilaPista, Portada
from .estilos import C
from .letra_viva import CACHE_LETRAS, LienzoLetra
from .sonando import Continuacion, PortadaInmersiva

_CACHE_LETRAS = CACHE_LETRAS  # compartida con la pagina de la letra
_CACHE_ARTISTAS = {}


class _Tarjeta(QFrame):
    def __init__(self, titulo="", padre=None):
        super().__init__(padre)
        self.setObjectName("caja")
        self.setStyleSheet(f"QFrame#caja{{background:{C['superficie2']};border-radius:10px;}}")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(16, 14, 16, 16)
        self.v.setSpacing(10)
        if titulo:
            t = QLabel(titulo)
            t.setStyleSheet("font-size:15px;font-weight:800;")
            self.v.addWidget(t)


def _redimensionar(portada, ancho, alto):
    portada.ancho, portada.alto = ancho, alto
    portada.setFixedSize(ancho, alto)
    url = portada.url
    portada.url = ""
    portada.pm = None
    portada.set_url(url)


class VistaSonando(QScrollArea):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.setObjectName("lienzo")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interior = QWidget()
        self.v = QVBoxLayout(interior)
        self.v.setContentsMargins(12, 4, 12, 20)
        self.v.setSpacing(16)
        self.setWidget(interior)
        from .componentes import suavizar
        suavizar(self)

        self.portada = PortadaInmersiva(ctx, 22, 720)
        self.portada.setFixedHeight(300)
        self.portada.setCursor(Qt.PointingHandCursor)
        self.portada.setToolTip("Ver el reproductor en grande")
        self.portada.ir_artista.connect(self._ir_artista)
        self.portada.pulsada.connect(self._en_grande)
        self.v.addWidget(self.portada)

        self.continua = Continuacion(ctx, limite=5)
        self.continua.ver_todo.connect(self._ver_cola)
        self.v.addWidget(self.continua)

        self.caja_info = _Tarjeta("Cómo suena")
        self.et_info = QLabel("")
        self.et_info.setObjectName("secundario")
        self.et_info.setWordWrap(True)
        self.caja_info.v.addWidget(self.et_info)

        self.caja_artista = _Tarjeta("Acerca del artista")
        self.foto_artista = Portada(220, 140, "cuadrada", 8, "usuario")
        self.caja_artista.v.addWidget(self.foto_artista, 0, Qt.AlignHCenter)
        self.et_nombre_artista = QPushButton("")
        self.et_nombre_artista.setCursor(Qt.PointingHandCursor)
        self.et_nombre_artista.setStyleSheet(
            "QPushButton{background:transparent;border:none;padding:0;text-align:left;"
            "font-size:16px;font-weight:800;}QPushButton:hover{text-decoration:underline;}")
        self.et_nombre_artista.clicked.connect(self._ir_artista)
        self.caja_artista.v.addWidget(self.et_nombre_artista)
        self.et_oyentes = QLabel("")
        self.et_oyentes.setObjectName("secundario")
        self.caja_artista.v.addWidget(self.et_oyentes)
        self.et_bio = QLabel("")
        self.et_bio.setWordWrap(True)
        self.et_bio.setObjectName("secundario")
        self.caja_artista.v.addWidget(self.et_bio)
        self.caja_artista.hide()
        self.v.addWidget(self.caja_artista)
        self.v.addWidget(self.caja_info)
        self.v.addStretch(1)
        self._artista_id = ""

        r = ctx.reproductor
        r.pista_cambio.connect(self._pista)
        r.calidad_cambio.connect(self._calidad)
        ctx.me_gusta_cambio.connect(self._al_cambiar_gusta)
        self._pista(r.actual)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        lado = max(160, min(self.viewport().width() - 24, 460))
        alto = max(220, min(lado, int(self.viewport().height() * 0.6)))
        if alto != self.portada.height():
            self.portada.setFixedHeight(alto)
        ancho_foto = max(120, lado - 32)
        if ancho_foto != self.foto_artista.ancho:
            _redimensionar(self.foto_artista, ancho_foto, int(ancho_foto * 0.62))

    def _en_grande(self):
        abrir = getattr(self.ctx.ventana, "abrir_sonando", None)
        if abrir is not None and self.ctx.reproductor.actual:
            abrir()

    def _ver_cola(self):
        panel = getattr(self.ctx.ventana, "panel_der", None)
        if panel is not None:
            panel.mostrar("cola")

    def _pista(self, p):
        self.portada.poner(p)
        if not p:
            self.caja_artista.hide()
            self.caja_info.hide()
            return
        artistas = [a for a in p.get("artistas") or [] if a.get("id")]
        if artistas:
            self._cargar_artista(artistas[0]["id"])
        else:
            self._artista_id = ""
            self.caja_artista.hide()

    def _al_cambiar_gusta(self, *_a):
        self.portada.pintar_gusta()

    def _calidad(self, info):
        lineas = []
        if info.get("local"):
            lineas.append("Desde tu disco, sin usar internet.")
        if info.get("alto"):
            fps = int(info.get("fps") or 0)
            lineas.append(f"Video {info['alto']}p a {fps} fps · "
                          f"{(info.get('vcodec') or '').split('.')[0].upper()}"
                          + (" · HDR" if info.get("hdr") else ""))
        if info.get("acodec"):
            codec = (info.get("acodec") or "").split(".")[0].upper()
            codec = {"MP4A": "AAC"}.get(codec, codec)
            lineas.append(f"Audio {codec} a {info.get('abr') or '?'} kbps"
                          + (f" · {int(info['asr']) // 1000} kHz" if info.get("asr") else ""))
        if not info.get("local"):
            lineas.append("Sin anuncios y en segundo plano.")
        aj = self.ctx.ajustes
        extras = []
        if aj["normalizar"]:
            extras.append("volumen normalizado")
        if aj["ecualizador"]:
            extras.append(f"ecualizador «{aj['eq_preset']}»")
        if int(aj["crossfade"] or 0):
            extras.append(f"fundido de {aj['crossfade']} s")
        if extras:
            lineas.append("Con " + ", ".join(extras) + ".")
        self.et_info.setText("\n".join(lineas))
        self.caja_info.setVisible(bool(lineas))

    def _cargar_artista(self, ident):
        if ident == self._artista_id:
            return
        self._artista_id = ident
        if ident in _CACHE_ARTISTAS:
            self._pintar_artista(_CACHE_ARTISTAS[ident])
            return
        self.caja_artista.hide()

        def listo(datos):
            _CACHE_ARTISTAS[ident] = datos
            if self._artista_id == ident:
                self._pintar_artista(datos)
        en_segundo_plano(catalogo.artista, ident, ok=listo, error=lambda _e: None, dueno=self)

    def _pintar_artista(self, a):
        self.foto_artista.set_url(a.get("foto") or "")
        self.et_nombre_artista.setText(a.get("titulo") or "")
        self.et_oyentes.setText(a.get("subtitulo") or "")
        bio = (a.get("descripcion") or "").strip()
        if len(bio) > 320:
            bio = bio[:317].rsplit(" ", 1)[0] + "…"
        self.et_bio.setText(bio)
        self.et_bio.setVisible(bool(bio))
        self.caja_artista.show()

    def _ir_artista(self):
        if self._artista_id:
            self.ctx.navegar({"pagina": "artista", "id": self._artista_id})


class VistaCola(QScrollArea):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.setObjectName("lienzo")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interior = QWidget()
        self.v = QVBoxLayout(interior)
        self.v.setContentsMargins(8, 4, 8, 20)
        self.v.setSpacing(6)
        self.setWidget(interior)
        from .componentes import suavizar
        suavizar(self)
        self.et_ahora = QLabel("Sonando ahora")
        self.et_ahora.setStyleSheet("font-size:15px;font-weight:800;")
        self.et_ahora.setContentsMargins(8, 10, 8, 0)
        self.v.addWidget(self.et_ahora)
        self.fila = None
        self.hueco = QVBoxLayout()
        self.v.addLayout(self.hueco)
        self.v.addSpacing(8)
        self.continua = Continuacion(ctx)
        self.v.addWidget(self.continua)
        self.v.addStretch(1)
        r = ctx.reproductor
        r.pista_cambio.connect(self.pintar)
        self.pintar()

    def showEvent(self, e):
        super().showEvent(e)
        self.pintar()

    def pintar(self, *_a):
        """La fila de lo que suena (lo que sigue se repinta solo)."""
        r = self.ctx.reproductor
        if self.fila is not None:
            if r.actual and self.fila.pista.get("clave") == r.actual.get("clave"):
                self.fila.update()
                return
            self.hueco.removeWidget(self.fila)
            self.fila.deleteLater()
            self.fila = None
        self.et_ahora.setVisible(bool(r.actual))
        if r.actual:
            self.fila = FilaPista(self.ctx, r.actual, 0, mostrar_album=False, mostrar_numero=False,
                                  arrastrable=False, compacto=True)
            self.fila.reproducir.connect(lambda _i: r.alternar())
            self.fila.me_gusta.connect(lambda _i: self.ctx.alternar_me_gusta(self.ctx.reproductor.actual))
            self.fila.menu.connect(lambda _i, pos: self.ctx.menu_pista(self.ctx.reproductor.actual, pos))
            self.hueco.addWidget(self.fila)


class VistaLetras(LienzoLetra):
    """La letra viva en el panel lateral (version compacta de la pagina)."""

    def __init__(self, ctx, padre=None):
        super().__init__(ctx, compacto=True, padre=padre)


class PanelDerecho(QFrame):
    cerrado = Signal()
    cambio = Signal(str)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.setObjectName("panel_der")
        self.setMinimumWidth(300)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 10, 0, 0)
        v.setSpacing(6)
        cab = QHBoxLayout()
        cab.setContentsMargins(16, 0, 10, 0)
        cab.setSpacing(4)
        self.botones = {}
        for clave, texto in (("sonando", "Sonando"), ("cola", "Cola"), ("letras", "Letra")):
            b = QPushButton(texto)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=clave: self.mostrar(c))
            cab.addWidget(b)
            self.botones[clave] = b
        cab.addStretch(1)
        cerrar = BotonIcono("cerrar", 16, "Cerrar el panel", 30)
        cerrar.clicked.connect(self.cerrado.emit)
        cab.addWidget(cerrar)
        v.addLayout(cab)
        from PySide6.QtWidgets import QStackedWidget
        self.pila = QStackedWidget()
        self.vistas = {
            "sonando": VistaSonando(ctx),
            "cola": VistaCola(ctx),
            "letras": VistaLetras(ctx),
        }
        for w in self.vistas.values():
            self.pila.addWidget(w)
        v.addWidget(self.pila, 1)
        self.actual = "sonando"
        self.mostrar("sonando")

    def mostrar(self, nombre):
        if nombre not in self.vistas:
            return
        self.actual = nombre
        for c, b in self.botones.items():
            b.setChecked(c == nombre)
        self.pila.setCurrentWidget(self.vistas[nombre])
        self.cambio.emit(nombre)
