# -*- coding: utf-8 -*-
"""Piezas que comparten las pantallas sociales: avatar, notas e insignias, tarjeta de
canción de la comunidad, reportar y reproducir lo que sube la gente.

Los estilos se construyen siempre con C[...] (los colores del tema cambian en vivo y
las páginas se rehacen al cambiar de tema): aquí no se guarda ningún widget entre páginas.
"""

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos, imagenes
from ..componentes import Portada
from ..estilos import C, _hex, _luz, _mezcla, _rgb

# ------------------------------------------------------------------ colores


def mezclar(a, b, t):
    """Color entre a y b (t=0 -> a, t=1 -> b), como #RRGGBB."""
    ra, rb = _rgb(a), _rgb(b)
    if ra is None or rb is None:
        return a if ra is not None else b
    return _hex(_mezcla(ra, rb, t))


def rgba(color, alfa):
    r = _rgb(color) or (255, 255, 255)
    return f"rgba({r[0]}, {r[1]}, {r[2]}, {alfa})"


def texto_sobre(color):
    """Texto oscuro o blanco, el que se lea mejor sobre ese color."""
    r = _rgb(color)
    return "#101114" if r is not None and _luz(r) > 0.30 else "#FFFFFF"


def color_de(p):
    """El color del perfil, o el de acento de Caudal si no eligió uno."""
    return (p or {}).get("color_perfil") or C["acento"]


def tinte(color, t=0.28):
    """El color del perfil mezclado con el fondo de los paneles (para la portada)."""
    return mezclar(C["panel"], color, t)


def fuente_px(px, peso=QFont.Normal):
    f = QFont()
    f.setPixelSize(int(px))
    f.setWeight(peso)
    return f


def etiqueta(texto="", estilo="", ajustar=True, nombre=None):
    et = QLabel(texto)
    if nombre:
        et.setObjectName(nombre)
    et.setWordWrap(ajustar)
    et.setStyleSheet("background:transparent;" + estilo)
    return et


def limpiar(layout):
    from ..componentes import _borrar_layout
    _borrar_layout(layout)


def columna_central(padre_layout, ancho=900):
    """Una columna centrada de ancho máximo dentro de una página. Devuelve su layout."""
    fila = QHBoxLayout()
    fila.setContentsMargins(0, 0, 0, 0)
    caja = QWidget()
    caja.setMaximumWidth(ancho)
    caja.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    v = QVBoxLayout(caja)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(18)
    fila.addStretch(1)
    fila.addWidget(caja, 100)
    fila.addStretch(1)
    padre_layout.addLayout(fila)
    return v


# ------------------------------------------------------------------ fondo del perfil (banner)

class FondoPerfil(QWidget):
    """Imagen de fondo de un perfil a todo el ancho, con un degradado oscuro encima.
    Sin imagen, un degradado con el color del perfil. Sigue el tema: los colores salen de C."""

    def __init__(self, alto=240, radio=18, solo_arriba=False, oscuridad=0.78, color=None, banner_url=None,
                 padre=None):
        super().__init__(padre)
        self.radio = radio
        self.solo_arriba = solo_arriba
        self.oscuridad = oscuridad
        self.color = color or C["acento"]
        self.img = None
        self.url = ""
        self.setFixedHeight(alto)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.set_banner(banner_url)

    def set_banner(self, banner_url):
        url = S.url_foto(banner_url) if banner_url else ""
        if url == self.url and (self.img is not None or not url):
            return
        self.url, self.img = url, None
        if url:
            yo, objetivo = self, url

            def listo(img):
                try:
                    if yo.url == objetivo and img is not None and not img.isNull():
                        yo.img = img
                        yo.update()
                except RuntimeError:
                    pass
            imagenes.imagen(url, listo)
        self.update()

    def set_imagen(self, img):
        """Una imagen local (vista previa al elegirla)."""
        self.url, self.img = "local", img
        self.update()

    def quitar(self):
        self.url, self.img = "", None
        self.update()

    def set_color(self, color):
        self.color = color or C["acento"]
        self.update()

    def paintEvent(self, _e):
        from PySide6.QtGui import QLinearGradient
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        w, h = self.width(), self.height()
        ruta = QPainterPath()
        r = self.radio
        ruta.addRoundedRect(QRectF(0, 0, w, h), r, r)
        if self.solo_arriba:                       # las esquinas de abajo, rectas
            ruta.addRect(QRectF(0, h - r, w, r))
            ruta = ruta.simplified()
        p.setClipPath(ruta)
        if self.img is not None and not self.img.isNull():
            esc = self.img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawImage(0, 0, esc, (esc.width() - w) // 2, (esc.height() - h) // 2, w, h)
        else:
            g = QLinearGradient(0, 0, w, h)
            g.setColorAt(0, QColor(tinte(self.color, 0.85)))
            g.setColorAt(1, QColor(tinte(self.color, 0.28)))
            p.fillRect(0, 0, w, h, g)
        sombra = QLinearGradient(0, 0, 0, h)
        arriba = QColor(C["panel"])
        arriba.setAlphaF(0.0)
        abajo = QColor(C["panel"])
        abajo.setAlphaF(self.oscuridad)
        sombra.setColorAt(0.25, arriba)
        sombra.setColorAt(1, abajo)
        p.fillRect(0, 0, w, h, sombra)


def entrada(widgets, paso=70, ms=260):
    """Los widgets aparecen uno tras otro con un fundido suave (tarjetas que «entran»)."""
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
    from PySide6.QtWidgets import QGraphicsOpacityEffect
    for i, w in enumerate(widgets):
        ef = QGraphicsOpacityEffect(w)
        ef.setOpacity(0.0)
        w.setGraphicsEffect(ef)

        def arrancar(w=w, ef=ef):
            try:
                anim = QPropertyAnimation(ef, b"opacity", w)
                anim.setDuration(ms)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.OutCubic)
                anim.finished.connect(lambda: w.setGraphicsEffect(None))
                anim.start(QPropertyAnimation.DeleteWhenStopped)
            except RuntimeError:
                pass
        QTimer.singleShot(i * paso, arrancar)


# ------------------------------------------------------------------ avatar

class Avatar(QWidget):
    """Foto redonda de una persona; sin foto, su inicial sobre el color del perfil."""

    def __init__(self, lado=48, nombre="", color=None, foto_url=None, anillo=None, padre=None):
        super().__init__(padre)
        self.lado = lado
        self.nombre = nombre or ""
        self.color = color or C["acento"]
        self.anillo = anillo
        self.url = ""
        self.pm = None
        self.setFixedSize(lado, lado)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.set_foto(foto_url)

    def set_foto(self, foto_url):
        url = S.url_foto(foto_url) if foto_url else ""
        if url == self.url and (self.pm is not None or not url):
            return
        self.url = url
        self.pm = None
        interior = self.lado - (6 if self.anillo else 0)
        if url:
            yo, objetivo = self, url

            def listo(pm):
                try:
                    if yo.url == objetivo:
                        yo.pm = pm
                        yo.update()
                except RuntimeError:
                    pass
            self.pm = imagenes.pedir(url, interior, interior, "redonda", 0, listo)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        margen = 3 if self.anillo else 0
        if self.anillo:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.anillo))
            p.drawEllipse(QRectF(0, 0, self.lado, self.lado))
        r = QRectF(margen, margen, self.lado - 2 * margen, self.lado - 2 * margen)
        if self.pm is not None:
            p.drawPixmap(int(margen), int(margen), self.pm)
            return
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.color))
        p.drawEllipse(r)
        ini = (self.nombre.strip()[:1] or "?").upper()
        p.setPen(QColor(texto_sobre(self.color)))
        p.setFont(fuente_px(self.lado * 0.42, QFont.Black))
        p.drawText(r, Qt.AlignCenter, ini)


# ------------------------------------------------------------------ notas, títulos e insignias

def _corona(lado, color):
    from PySide6.QtGui import QPixmap, QPolygonF
    from PySide6.QtCore import QPointF
    pm = QPixmap(lado, lado)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    e = lado / 14
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawPolygon(QPolygonF([QPointF(1 * e, 11 * e), QPointF(1.5 * e, 4 * e), QPointF(4.5 * e, 7.5 * e),
                             QPointF(7 * e, 3 * e), QPointF(9.5 * e, 7.5 * e), QPointF(12.5 * e, 4 * e),
                             QPointF(13 * e, 11 * e)]))
    p.end()
    return pm


class Nota(QFrame):
    """Una nota con icono y texto: insignia, ARTISTA, fundador…"""

    def __init__(self, texto, icono, fondo_css, color_texto, color_icono=None, detalle="",
                 tam=11, padre=None):
        super().__init__(padre)
        self.setObjectName("nota_social")
        self.setStyleSheet(f"QFrame#nota_social{{{fondo_css}}}")
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 3, 10, 3)
        h.setSpacing(5)
        if icono:
            ic = QLabel()
            if icono == "@logo":
                ic.setPixmap(iconos.icono_app(16))
            elif icono == "@corona":
                ic.setPixmap(_corona(14, color_texto))
            else:
                ic.setPixmap(iconos.pixmap(icono, 14, color_icono or color_texto))
            ic.setStyleSheet("background:transparent;")
            h.addWidget(ic)
        et = QLabel(texto)
        et.setStyleSheet(f"background:transparent;color:{color_texto};font-size:{tam}px;"
                         "font-weight:800;letter-spacing:0.3px;")
        h.addWidget(et)
        if detalle:
            self.setToolTip(detalle)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)


def nota_titulo(clave, texto):
    """«Fundador de Caudal» (cian a dorado), «Usuario fundador ★» y «ARTISTA» (dorada)."""
    if clave == "fundador_caudal":
        fondo = (f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {C['acento']},"
                 f"stop:1 {S.COLOR_ARTISTA});border-radius:11px;")
        return Nota(texto.upper(), "@logo", fondo, "#101114",
                    detalle="Título especial: quien creó Caudal", tam=11)
    if clave == "rey_de_la_musica":
        fondo = (f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FFD95E,stop:1 #FF9F1C);"
                 "border:1px solid #FFB830;border-radius:11px;")
        return Nota(texto.upper(), "@corona", fondo, "#3A2600", detalle="Título especial", tam=11)
    if clave == "fundador":
        fondo = (f"background:{rgba(S.COLOR_ARTISTA, 0.12)};border:1px solid {rgba(S.COLOR_ARTISTA, 0.55)};"
                 "border-radius:11px;")
        return Nota(texto, "estrella", fondo, S.COLOR_ARTISTA,
                    detalle="Una de las 100 primeras personas en llegar a Caudal")
    fondo = (f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FFE27A,stop:1 {S.COLOR_ARTISTA});"
             f"border:1px solid {S.COLOR_ARTISTA};border-radius:11px;")
    return Nota(texto, "estrella", fondo, "#3A2600",
                detalle=f"Llegó a {S.LIKES_ARTISTA} me gusta" if clave == "artista" else "Título especial")


def notas_de(p, solo_principales=False):
    """Widgets de las notas especiales de un perfil (puede devolver una lista vacía)."""
    claves = S.titulos_de(p)
    if solo_principales:
        claves = claves[:1]
    return [nota_titulo(k, t) for k, t in claves]


def chip_insignia(ins):
    titulo_def, icono, color = S.INSIGNIAS.get(ins.get("clave"), (None, "estrella", C["texto2"]))
    titulo = ins.get("titulo") or titulo_def or "Insignia"
    fondo = f"background:{rgba(color, 0.14)};border:1px solid {rgba(color, 0.45)};border-radius:12px;"
    return Nota(titulo, icono, fondo, C["texto"], color_icono=color, detalle=ins.get("detalle") or "",
                tam=12)


def chip_texto(texto, destacado=False):
    et = QLabel(texto)
    et.setStyleSheet(
        f"background:{C['acento'] if destacado else C['superficie2']};"
        f"color:{C['acento_texto'] if destacado else C['texto']};"
        "border-radius:12px;padding:4px 12px;font-size:12px;font-weight:700;")
    et.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return et


class FlujoChips(QWidget):
    """Chips que pasan a la línea siguiente cuando no caben."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.items = []
        self.espacio = 6

    def agregar(self, w):
        w.setParent(self)
        w.show()
        self.items.append(w)
        self._acomodar()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._acomodar()

    def _acomodar(self):
        ancho = max(60, self.width())
        x = y = alto_fila = 0
        for w in self.items:
            s = w.sizeHint()
            if x and x + s.width() > ancho:
                x, y, alto_fila = 0, y + alto_fila + self.espacio, 0
            w.setGeometry(x, y, s.width(), s.height())
            x += s.width() + self.espacio
            alto_fila = max(alto_fila, s.height())
        total = y + alto_fila
        if self.minimumHeight() != total:
            self.setMinimumHeight(total)
            self.updateGeometry()

    def sizeHint(self):
        return QSize(200, self.minimumHeight())


class BarraAfinidad(QWidget):
    """«Os parecéis un 78 %»: una barra fina que se llena con el color del perfil."""

    def __init__(self, porcentaje, color, padre=None):
        super().__init__(padre)
        self.porcentaje = max(0, min(100, int(porcentaje)))
        self.color = color
        self.setFixedHeight(8)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["superficie3"]))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 8), 4, 4)
        p.setBrush(QColor(self.color))
        p.drawRoundedRect(QRectF(0, 0, self.width() * self.porcentaje / 100, 8), 4, 4)


def titulo_seccion(texto, detalle=""):
    caja = QWidget()
    v = QVBoxLayout(caja)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)
    t = QLabel(texto)
    t.setObjectName("titulo_seccion")
    t.setStyleSheet("background:transparent;")
    v.addWidget(t)
    if detalle:
        d = QLabel(detalle)
        d.setObjectName("ayuda")
        d.setWordWrap(True)
        d.setStyleSheet("background:transparent;")
        v.addWidget(d)
    return caja


def tarjeta(color_borde=None):
    """Un recuadro redondeado del tema; devuelve (marco, layout vertical)."""
    f = QFrame()
    f.setObjectName("tarjeta_social")
    f.setStyleSheet(f"QFrame#tarjeta_social{{background:{C['panel']};border:1px solid "
                    f"{color_borde or C['borde']};border-radius:16px;}}")
    v = QVBoxLayout(f)
    v.setContentsMargins(20, 18, 20, 18)
    v.setSpacing(10)
    return f, v


def boton(texto, nombre="contorno", icono=None, color_icono=None, ayuda="", al_pulsar=None):
    b = QPushButton(("  " if icono else "") + texto)
    b.setObjectName(nombre)
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.NoFocus)
    if icono:
        b.setIcon(iconos.icono(icono, 16, color_icono or (C["acento_texto"] if nombre == "principal"
                                                          else C["texto"])))
    if ayuda:
        b.setToolTip(ayuda)
    if al_pulsar:
        b.clicked.connect(lambda _=False: al_pulsar())
    return b


def boton_redondo(icono, ayuda, al_pulsar, lado=34, color=None, fondo=None):
    b = QPushButton()
    b.setIcon(iconos.icono(icono, 17, color or C["texto"]))
    b.setIconSize(QSize(17, 17))
    b.setFixedSize(lado, lado)
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.NoFocus)
    b.setToolTip(ayuda)
    b.setStyleSheet(f"QPushButton{{background:{fondo or C['superficie2']};border:none;"
                    f"border-radius:{lado // 2}px;padding:0;}}"
                    f"QPushButton:hover{{background:{C['superficie3']};}}")
    b.clicked.connect(lambda _=False: al_pulsar())
    return b


def aviso(ctx, texto):
    try:
        ctx.aviso.emit(texto)
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------ canciones de la comunidad

ESTADOS = {"revision": ("En revisión", "aviso"), "retirada": ("Retirada", "error")}


class TarjetaSubida(QFrame):
    """Una canción subida por la gente: carátula, datos y botones de escuchar / reportar / borrar."""

    reproducir = Signal(dict)
    reportar = Signal(dict)
    borrar = Signal(dict)
    abrir_perfil = Signal(str)

    def __init__(self, s, propia=False, mostrar_autor=True, padre=None):
        super().__init__(padre)
        self.s = s
        self.setObjectName("fila_subida")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"QFrame#fila_subida{{background:{C['superficie']};border:1px solid "
                           f"transparent;border-radius:14px;}}"
                           f"QFrame#fila_subida:hover{{background:{C['superficie2']};}}")
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 8, 12, 8)
        h.setSpacing(12)
        self.portada = Portada(60, radio=10)
        self.portada.set_url(S.url_musica(s.get("portada")))
        h.addWidget(self.portada)
        col = QVBoxLayout()
        col.setSpacing(1)
        t = etiqueta(s.get("titulo") or "Sin título", "font-size:14px;font-weight:700;", False)
        t.setMinimumWidth(40)
        t.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(t)
        partes = [x for x in (s.get("artista"), s.get("album")) if x]
        sub = etiqueta(" · ".join(partes) or "Artista sin indicar",
                       f"color:{C['texto2']};font-size:12px;", False)
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(sub)
        extra = QHBoxLayout()
        extra.setSpacing(6)
        if mostrar_autor and s.get("usuario"):
            por = QPushButton(f"@{s['usuario']}")
            por.setCursor(Qt.PointingHandCursor)
            por.setStyleSheet(f"QPushButton{{background:transparent;border:none;padding:0;"
                              f"color:{C['acento']};font-size:11.5px;font-weight:700;}}"
                              "QPushButton:hover{text-decoration:underline;}")
            por.clicked.connect(lambda _=False: self.abrir_perfil.emit(s["usuario"]))
            extra.addWidget(por)
            if s.get("es_artista"):
                extra.addWidget(nota_titulo("artista", "ARTISTA"))
        datos = []
        if s.get("duracion"):
            datos.append(S.tiempo_corto(s["duracion"]))
        n = int(s.get("escuchas") or 0)
        datos.append(f"{n} escucha" + ("" if n == 1 else "s"))
        extra.addWidget(etiqueta(" · ".join(datos), f"color:{C['texto3']};font-size:11.5px;", False))
        texto_e, tono = S.texto_estado(s)
        if texto_e:
            extra.addWidget(etiqueta(texto_e, f"color:{C[tono]};font-size:11.5px;font-weight:800;", False))
        extra.addStretch(1)
        col.addLayout(extra)
        h.addLayout(col, 1)
        play = QPushButton()
        play.setIcon(iconos.icono("reproducir", 18, C["acento_texto"]))
        play.setFixedSize(38, 38)
        play.setCursor(Qt.PointingHandCursor)
        play.setToolTip("Escuchar")
        play.setStyleSheet(f"QPushButton{{background:{C['acento']};border:none;border-radius:19px;}}"
                           f"QPushButton:hover{{background:{C['acento_alto']};}}")
        play.clicked.connect(lambda _=False: self.reproducir.emit(s))
        h.addWidget(play)
        if propia:
            h.addWidget(boton_redondo("papelera", "Borrar mi canción", lambda: self.borrar.emit(s),
                                      color=C["error"]))
        else:
            h.addWidget(boton_redondo("aviso", "Reportar esta canción", lambda: self.reportar.emit(s),
                                      color=C["texto2"]))

    def mouseDoubleClickEvent(self, e):
        self.reproducir.emit(self.s)
        super().mouseDoubleClickEvent(e)


# ------------------------------------------------------------------ reportar

MOTIVOS = ["No es de quien la subió (derechos de autor)", "Contenido ofensivo o inapropiado",
           "Es spam o no es música", "Otro motivo"]


class DialogoReportar(QDialog):
    def __init__(self, s, padre=None):
        super().__init__(padre)
        from ..estilos import hoja
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.setWindowTitle("Reportar canción · Caudal")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(10)
        t = QLabel("Reportar canción")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        v.addWidget(etiqueta(f"«{s.get('titulo', '')}» se ocultará mientras la revisamos si tres personas "
                             "distintas la reportan.", f"color:{C['texto2']};"))
        self.motivo = QComboBox()
        self.motivo.addItems(MOTIVOS)
        v.addWidget(self.motivo)
        self.detalle = QLineEdit()
        self.detalle.setMaxLength(200)
        self.detalle.setPlaceholderText("Si quieres, cuéntanos más (opcional)")
        v.addWidget(self.detalle)
        fila = QHBoxLayout()
        fila.addStretch(1)
        c = QPushButton("Cancelar")
        c.setObjectName("contorno")
        c.clicked.connect(self.reject)
        fila.addWidget(c)
        ok = QPushButton("Enviar reporte")
        ok.setObjectName("principal")
        ok.clicked.connect(self.accept)
        fila.addWidget(ok)
        v.addLayout(fila)

    def texto(self):
        base = self.motivo.currentText()
        extra = self.detalle.text().strip()
        return f"{base}. {extra}" if extra else base


def reportar_subida(ctx, social, s, padre=None, al_terminar=None):
    d = DialogoReportar(s, padre)
    if d.exec() != QDialog.Accepted:
        return
    motivo = d.texto()

    def listo(_r):
        aviso(ctx, "Gracias. Revisaremos esa canción.")
        if al_terminar:
            al_terminar()
    en_segundo_plano(social.reportar, s["id"], motivo, ok=listo,
                     error=lambda e: aviso(ctx, S.explicar(e, "enviar el reporte")),
                     dueno=padre, urgente=True)


def confirmar(padre, titulo, texto, si="Aceptar", peligro=False):
    """Pregunta sí/no con el estilo de Caudal."""
    from PySide6.QtWidgets import QMessageBox
    caja = QMessageBox(padre)
    caja.setWindowTitle(titulo + " · Caudal")
    caja.setText(texto)
    b_si = caja.addButton(si, QMessageBox.AcceptRole)
    caja.addButton("Cancelar", QMessageBox.RejectRole)
    caja.exec()
    return caja.clickedButton() is b_si


def borrar_subida(ctx, social, s, padre=None, al_terminar=None):
    if not confirmar(padre, "Borrar canción",
                     f"Se borrará «{s.get('titulo', '')}» para todos, con su carátula. "
                     "No se puede deshacer.", "Borrar"):
        return

    def listo(_r):
        aviso(ctx, "Canción borrada")
        if al_terminar:
            al_terminar()
    en_segundo_plano(social.borrar_subida, s, ok=listo,
                     error=lambda e: aviso(ctx, S.explicar(e, "borrar la canción")),
                     dueno=padre, urgente=True)


# ------------------------------------------------------------------ reproducir

def _vigilar_escuchas(ctx):
    """Cuenta una escucha cada vez que EMPIEZA a sonar una canción de la comunidad
    (venga de donde venga: botón, cola o siguiente). Devuelve True si quedó vigilando."""
    if getattr(ctx, "_social_escuchas", False):
        return True
    r = getattr(ctx, "reproductor", None)
    senal = getattr(r, "pista_cambio", None)
    if senal is None:
        return False

    def al_cambiar(p):
        sid = (p or {}).get("subida_id") if isinstance(p, dict) else None
        sc = social_de_ctx(ctx)
        if sid and sc is not None:
            en_segundo_plano(sc.contar_escucha, sid, urgente=True)
    senal.connect(al_cambiar)
    ctx._social_escuchas = True
    return True


def social_de_ctx(ctx):
    return S.social_de(ctx)


def reproducir_subidas(ctx, social, lista, inicio=0, dueno=None):
    """Toca la canción elegida y, en segundo plano, trae las siguientes y las pone en la cola."""
    lista = [x for x in lista if x.get("id") and x.get("ruta")]
    if not lista:
        return
    inicio = max(0, min(inicio, len(lista) - 1))
    vigilando = _vigilar_escuchas(ctx)
    primera = lista[inicio]
    aviso(ctx, f"Preparando «{primera['titulo']}»…")

    def lista_la_primera(ruta):
        pista = S.pista_de_subida(primera, ruta)
        ctx.reproducir_pista(pista, {"tipo": "comunidad", "id": "comunidad", "titulo": "Comunidad de Caudal"})
        if not vigilando:
            en_segundo_plano(social.contar_escucha, primera["id"], urgente=True)
        resto = lista[inicio + 1:inicio + 8]
        if resto:
            _encolar(ctx, resto, dueno)

    en_segundo_plano(S.descargar_subida, primera, ok=lista_la_primera,
                     error=lambda e: aviso(ctx, S.explicar(e, "reproducir la canción")),
                     dueno=dueno, urgente=True)


def _encolar(ctx, resto, dueno):
    r = getattr(ctx, "reproductor", None)
    if r is None or not hasattr(r, "agregar_a_cola"):
        return
    pendientes = list(resto)

    def siguiente(_=None):
        if not pendientes:
            return
        s = pendientes.pop(0)

        def listo(ruta):
            try:
                r.agregar_a_cola(S.pista_de_subida(s, ruta))
            except Exception:  # noqa: BLE001
                return
            siguiente()
        en_segundo_plano(S.descargar_subida, s, ok=listo, error=siguiente)
    siguiente()
