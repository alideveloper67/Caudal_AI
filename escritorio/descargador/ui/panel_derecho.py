# -*- coding: utf-8 -*-
"""Panel de la derecha: lo que suena, la cola y la letra sincronizada."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .. import catalogo
from ..hilos import en_segundo_plano
from . import iconos
from .componentes import BotonIcono, FilaPista, Portada, _borrar_layout, fuente
from .estilos import C
from .letra_viva import CACHE_LETRAS, LienzoLetra

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
        self.v.setContentsMargins(16, 4, 16, 20)
        self.v.setSpacing(14)
        self.setWidget(interior)
        from .componentes import suavizar
        suavizar(self)

        self.portada = Portada(220, 220, "cuadrada", 8)
        self.v.addWidget(self.portada, 0, Qt.AlignHCenter)
        fila = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(2)
        self.et_titulo = QLabel("")
        self.et_titulo.setWordWrap(True)
        self.et_titulo.setStyleSheet("font-size:22px;font-weight:800;")
        textos.addWidget(self.et_titulo)
        self.et_artista = QLabel("")
        self.et_artista.setObjectName("secundario")
        self.et_artista.setWordWrap(True)
        self.et_artista.setStyleSheet("font-size:14px;")
        textos.addWidget(self.et_artista)
        fila.addLayout(textos, 1)
        self.bt_gusta = BotonIcono("corazon", 20, "Tus me gusta", 34)
        self.bt_gusta.clicked.connect(self._gusta)
        fila.addWidget(self.bt_gusta, 0, Qt.AlignTop)
        self.bt_mas = BotonIcono("puntos", 20, "Más opciones", 34)
        self.bt_mas.clicked.connect(self._menu)
        fila.addWidget(self.bt_mas, 0, Qt.AlignTop)
        self.v.addLayout(fila)

        self.caja_info = _Tarjeta("Cómo suena")
        self.et_info = QLabel("")
        self.et_info.setObjectName("secundario")
        self.et_info.setWordWrap(True)
        self.caja_info.v.addWidget(self.et_info)
        self.v.addWidget(self.caja_info)

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

        self.caja_siguiente = _Tarjeta("Siguiente en la cola")
        self.fila_siguiente = None
        self.v.addWidget(self.caja_siguiente)
        self.v.addStretch(1)
        self._artista_id = ""

        r = ctx.reproductor
        r.pista_cambio.connect(self._pista)
        r.calidad_cambio.connect(self._calidad)
        r.cola_cambio.connect(self._siguiente)
        ctx.me_gusta_cambio.connect(self._al_cambiar_gusta)
        self._pista(r.actual)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        lado = max(160, min(self.viewport().width() - 32, 420))
        if lado != self.portada.ancho:
            _redimensionar(self.portada, lado, lado)
            ancho_foto = max(120, lado - 32)
            _redimensionar(self.foto_artista, ancho_foto, int(ancho_foto * 0.62))

    def _pista(self, p):
        if not p:
            self.et_titulo.setText("Nada sonando")
            self.et_artista.setText("Elige algo para escuchar")
            self.portada.set_url("")
            self.caja_artista.hide()
            self.caja_info.hide()
            return
        self.portada.set_url(p.get("miniatura") or "")
        self.et_titulo.setText(p.get("titulo") or "")
        self.et_artista.setText(p.get("artista") or "")
        self._pintar_gusta()
        artistas = [a for a in p.get("artistas") or [] if a.get("id")]
        if artistas:
            self._cargar_artista(artistas[0]["id"])
        else:
            self.caja_artista.hide()
        self._siguiente()

    def _al_cambiar_gusta(self, *_a):
        self._pintar_gusta()

    def _pintar_gusta(self):
        p = self.ctx.reproductor.actual
        gusta = bool(p and self.ctx.coleccion.me_gusta(p.get("clave")))
        self.bt_gusta.set_icono("corazon_lleno" if gusta else "corazon")
        self.bt_gusta.set_activo(gusta, punto=False)

    def _gusta(self):
        if self.ctx.reproductor.actual:
            self.ctx.alternar_me_gusta(self.ctx.reproductor.actual)

    def _menu(self):
        p = self.ctx.reproductor.actual
        if p:
            self.ctx.menu_pista(p, self.bt_mas.mapToGlobal(self.bt_mas.rect().bottomLeft()))

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

    def _siguiente(self):
        r = self.ctx.reproductor
        sig = r.proximas[0] if r.proximas else (
            r.secuencia[r.pos + 1] if 0 <= r.pos < len(r.secuencia) - 1 else None)
        if self.fila_siguiente:
            self.fila_siguiente.deleteLater()
            self.fila_siguiente = None
        if not sig:
            self.caja_siguiente.hide()
            return
        self.fila_siguiente = FilaPista(self.ctx, sig, 0, mostrar_album=False, mostrar_numero=False,
                                        arrastrable=False, compacto=True)
        self.fila_siguiente.reproducir.connect(lambda _i: r.siguiente())
        self.caja_siguiente.v.addWidget(self.fila_siguiente)
        self.caja_siguiente.show()


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
        self.v.setSpacing(2)
        self.setWidget(interior)
        from .componentes import suavizar
        suavizar(self)
        self._pendiente = False
        r = ctx.reproductor
        r.cola_cambio.connect(self._programar)
        r.pista_cambio.connect(self._programar)
        self.pintar()

    def _programar(self, *_):
        # varias senales seguidas -> un solo repintado
        if not self._pendiente:
            self._pendiente = True
            QTimer.singleShot(60, self.pintar)

    def showEvent(self, e):
        super().showEvent(e)
        self.pintar()

    def _titulo(self, texto, accion=None, texto_accion=""):
        fila = QHBoxLayout()
        fila.setContentsMargins(8, 14, 8, 4)
        t = QLabel(texto)
        t.setStyleSheet("font-size:15px;font-weight:800;")
        t.setWordWrap(True)
        fila.addWidget(t, 1)
        if accion:
            b = QPushButton(texto_accion)
            b.setObjectName("enlace")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(accion)
            fila.addWidget(b)
        self.v.addLayout(fila)

    def pintar(self):
        self._pendiente = False
        if not self.isVisible():
            return
        _borrar_layout(self.v)
        r = self.ctx.reproductor
        if not r.actual:
            vacio = QLabel("Tu cola está vacía.\nElige algo para escuchar.")
            vacio.setAlignment(Qt.AlignCenter)
            vacio.setObjectName("secundario")
            self.v.addSpacing(40)
            self.v.addWidget(vacio)
            self.v.addStretch(1)
            return
        self._titulo("Sonando ahora")
        f = FilaPista(self.ctx, r.actual, 0, mostrar_album=False, mostrar_numero=False,
                      arrastrable=False, compacto=True)
        f.reproducir.connect(lambda _i: r.alternar())
        self.v.addWidget(f)

        if r.proximas:
            self._titulo("Siguiente en tu cola", r.vaciar_proximas, "Vaciar cola")
            for i, p in enumerate(r.proximas[:100]):
                fila = FilaPista(self.ctx, p, i, mostrar_album=False, mostrar_numero=False,
                                 arrastrable=False, compacto=True)
                fila.reproducir.connect(r.saltar_a_proxima)
                fila.menu.connect(lambda i, pos, p=p: self.ctx.menu_pista(
                    p, pos, extra=lambda m, i=i, p=p: m.addAction(
                        "Quitar de la cola", lambda: self._quitar_proxima(i, p))))
                self.v.addWidget(fila)

        siguientes = r.siguientes_de_contexto(80)
        normales = [(i, p) for i, p in enumerate(siguientes) if not p.get("_auto")]
        automaticas = [(i, p) for i, p in enumerate(siguientes) if p.get("_auto")]
        nombre = (r.contexto or {}).get("titulo") or "la cola"
        if normales:
            self._titulo(f"Siguiente de: {nombre}")
            for i, p in normales:
                self._fila_contexto(r, i, p)
        if automaticas:
            self._titulo("Reproducción automática")
            nota = QLabel("Canciones parecidas para que la música no pare.")
            nota.setObjectName("ayuda")
            nota.setContentsMargins(8, 0, 8, 6)
            self.v.addWidget(nota)
            for i, p in automaticas:
                self._fila_contexto(r, i, p)
        if not siguientes and not r.proximas:
            nota = QLabel("No hay nada más en la cola."
                          + (" Al terminar seguirán canciones parecidas."
                             if self.ctx.ajustes["autoplay"] else ""))
            nota.setObjectName("secundario")
            nota.setWordWrap(True)
            nota.setContentsMargins(8, 16, 8, 0)
            self.v.addWidget(nota)
        self.v.addStretch(1)

    def _quitar_proxima(self, i, p):
        r = self.ctx.reproductor
        r.quitar_proxima(i)

        def deshacer():
            r.proximas.insert(min(i, len(r.proximas)), p)
            r.cola_cambio.emit()
        self.ctx.avisar("Quitada de la cola", deshacer)

    def _fila_contexto(self, r, i, p):
        absoluto = r.pos + 1 + i
        fila = FilaPista(self.ctx, p, i, mostrar_album=False, mostrar_numero=False,
                         arrastrable=False, compacto=True)
        fila.reproducir.connect(lambda _i, a=absoluto: r.saltar_a(a))
        fila.menu.connect(lambda _i, pos, p=p, a=absoluto: self.ctx.menu_pista(
            p, pos, extra=lambda m: m.addAction("Quitar de la cola",
                                                lambda: r.quitar_de_secuencia(a))))
        self.v.addWidget(fila)


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


def _sin_usar():  # pragma: no cover
    return QFont, fuente, iconos
