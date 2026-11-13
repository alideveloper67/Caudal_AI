# -*- coding: utf-8 -*-
"""Pagina de artista: foto grande, populares y toda su discografia."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ... import catalogo
from ...hilos import en_segundo_plano
from .. import imagenes
from ..componentes import BarraAcciones, EtiquetaTitulo, ListaPistas, Pagina
from ..estilos import C
from .comun import cache, guardar_cache, pintar_secciones


class Banner(QWidget):
    """La foto del artista a todo lo ancho, fundida con la pagina."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setFixedHeight(340)
        self.img = None
        self.color = QColor("#28303D")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(28, 0, 28, 22)
        self.v.addStretch(1)

    def set_imagen(self, img):
        self.img = img if img is not None and not img.isNull() else None
        if self.img is not None:
            self.color = imagenes.color_dominante(self.img)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), self.color)
        if self.img is not None:
            esc = self.img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            # el encuadre de las fotos de artista suele tener la cara arriba
            y = int((esc.height() - h) * 0.25)
            p.drawImage(0, 0, esc, (esc.width() - w) // 2, y, w, h)
        g = QLinearGradient(0, h * 0.35, 0, h)
        g.setColorAt(0, QColor(0, 0, 0, 0))
        g.setColorAt(1, QColor(0, 0, 0, 170))
        p.fillRect(QRect(0, 0, w, h), g)


class PaginaArtista(Pagina):
    def __init__(self, ctx, ident, padre=None):
        super().__init__(ctx, padre, margen=(0, 0, 0, 32))
        self.ident = ident
        self.datos = None
        self.titulo = "Artista"
        datos = cache(("artista", ident), 30)
        if datos is not None:
            self._pintar(datos)
        else:
            self.cargando("Cargando el artista…")
            en_segundo_plano(catalogo.artista, ident, ok=self._llego,
                             error=lambda e: self.error(f"No se pudo abrir el artista.\n{e}",
                                                        lambda: self.ctx.navegar(
                                                            {"pagina": "artista", "id": ident})),
                             dueno=self)

    def _llego(self, datos):
        guardar_cache(("artista", self.ident), datos)
        self._pintar(datos)

    def _pintar(self, a):
        self.vaciar()
        self.datos = a
        self.titulo = a.get("titulo") or "Artista"
        self.titulo_cambio.emit(self.titulo)
        ctx = self.ctx
        banner = Banner()
        et = EtiquetaTitulo(a.get("titulo") or "", maximo=84, minimo=32)
        et.setStyleSheet(et.styleSheet() + "color:#FFFFFF;")
        banner.v.addWidget(et)
        if a.get("subtitulo"):
            s = QLabel(a["subtitulo"])
            s.setStyleSheet("font-size:14px;font-weight:600;color:#FFFFFF;")
            banner.v.addWidget(s)
        self.cuerpo.addWidget(banner)
        if a.get("foto"):
            imagenes.imagen(a["foto"], lambda img: self._foto(banner, img))

        contenido = QWidget()
        cv = QVBoxLayout(contenido)
        cv.setContentsMargins(24, 12, 24, 0)
        cv.setSpacing(28)

        acciones = BarraAcciones()
        acciones.bt_play.clicked.connect(self._reproducir)
        acciones.boton("aleatorio", "Aleatorio", lambda: self._reproducir(True), 26, 40)
        acciones.boton("radio", "Radio del artista", self._radio, 24, 40)
        seguido = ctx.coleccion.guardado("artista", self.ident)
        self.bt_seguir = QPushButton("Siguiendo" if seguido else "Seguir")
        self.bt_seguir.setObjectName("contorno")
        self.bt_seguir.setCheckable(True)
        self.bt_seguir.setChecked(seguido)
        self.bt_seguir.setCursor(Qt.PointingHandCursor)
        self.bt_seguir.clicked.connect(self._seguir)
        acciones.widget(self.bt_seguir)
        acciones.boton("puntos", "Más", lambda: ctx.menu_elemento(
            self._elemento(), acciones.mapToGlobal(acciones.rect().center())), 22, 40)
        acciones.terminar()
        cv.addWidget(acciones)

        secciones = a.get("secciones") or []
        populares = next((s for s in secciones if s["estilo"] == "filas"), None)
        if populares:
            t = QLabel("Populares")
            t.setObjectName("titulo_seccion")
            cv.addWidget(t)
            self.lista = ListaPistas(ctx, mostrar_album=True, mostrar_cabecera=False)
            pistas = populares["elementos"]
            self.populares = pistas
            self.lista.set_pistas(pistas[:5], {"tipo": "artista", "id": self.ident,
                                               "titulo": a.get("titulo")})
            cv.addWidget(self.lista)
            if populares.get("mas") and populares["mas"].get("id"):
                mas = QPushButton("Ver más canciones")
                mas.setObjectName("enlace")
                mas.setCursor(Qt.PointingHandCursor)
                m = populares["mas"]
                mas.clicked.connect(lambda: ctx.navegar({"pagina": "lista", "id": m["id"][2:]
                                                         if m["id"].startswith("VL") else m["id"]}))
                cv.addWidget(mas, 0, Qt.AlignLeft)
        resto = [s for s in secciones if s is not populares]
        pintar_secciones(ctx, cv, resto)
        if a.get("descripcion"):
            caja = QWidget()
            caja.setObjectName("caja")
            caja.setAttribute(Qt.WA_StyledBackground, True)
            caja.setStyleSheet(f"QWidget#caja{{background:{C['superficie2']};border-radius:12px;}}")
            vb = QVBoxLayout(caja)
            vb.setContentsMargins(24, 20, 24, 22)
            t = QLabel("Información")
            t.setObjectName("titulo_seccion")
            vb.addWidget(t)
            d = QLabel(a["descripcion"][:1400])
            d.setWordWrap(True)
            d.setObjectName("secundario")
            d.setStyleSheet("font-size:14px;line-height:150%;")
            vb.addWidget(d)
            cv.addWidget(caja)
        self.cuerpo.addWidget(contenido)
        self.cuerpo.addStretch(1)

    def _foto(self, banner, img):
        try:
            banner.set_imagen(img)
            self.set_color(banner.color)
        except RuntimeError:
            pass

    def _elemento(self):
        a = self.datos or {}
        return {"tipo": "artista", "id": self.ident, "titulo": a.get("titulo") or "",
                "miniatura": a.get("foto") or "", "subtitulo": "Artista"}

    def _reproducir(self, aleatorio=False):
        a = self.datos or {}
        if getattr(self, "populares", None) and not aleatorio:
            self.ctx.reproducir_lista(self.populares, 0, {"tipo": "artista", "id": self.ident,
                                                          "titulo": a.get("titulo")})
            return
        rid = a.get("aleatorio_id") or a.get("radio_id")
        if rid:
            self.ctx.reproductor.reproducir_radio_id(rid, a.get("titulo") or "Artista")
        elif getattr(self, "populares", None):
            self.ctx.reproducir_lista(self.populares, 0, {"tipo": "artista", "id": self.ident,
                                                          "titulo": a.get("titulo")}, True)

    def _radio(self):
        a = self.datos or {}
        rid = a.get("radio_id") or a.get("aleatorio_id")
        if rid:
            self.ctx.reproductor.reproducir_radio_id(rid, f"Radio de {a.get('titulo', '')}")
        elif getattr(self, "populares", None):
            self.ctx.reproductor.iniciar_radio(self.populares[0])

    def _seguir(self):
        self.ctx.alternar_guardado(self._elemento())
        seguido = self.ctx.coleccion.guardado("artista", self.ident)
        self.bt_seguir.setChecked(seguido)
        self.bt_seguir.setText("Siguiendo" if seguido else "Seguir")


def _sin_usar():  # pragma: no cover
    return QHBoxLayout
