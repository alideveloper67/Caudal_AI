# -*- coding: utf-8 -*-
"""«Tu año en Caudal»: el resumen del año como imagen vertical 1080×1920 para estados e historias.

Lo calcula `resumen_anual` con tus escuchas locales. Es una función para donadores: quien no lo es ve la
imagen difuminada con un candado, «Donar aquí» y «Tengo un código de prueba»."""

import os
import re

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout)

from .. import resumen_anual as RA
from ..hilos import en_segundo_plano
from . import iconos
from .letra_viva import _fondo_aurora, carpeta_imagenes

W, H = 1080, 1920


def _fuente(px, peso=QFont.Bold):
    f = QFont("Segoe UI")
    f.setPixelSize(int(px))
    f.setWeight(peso)
    return f


def _texto(p, rect, texto, px, peso, color, alinear=Qt.AlignLeft):
    """Una línea de texto dentro de `rect`, con puntos suspensivos si no cabe."""
    f = _fuente(px, peso)
    p.setFont(f)
    p.setPen(color)
    corto = QFontMetricsF(f).elidedText(str(texto), Qt.ElideRight, rect.width())
    p.drawText(rect, int(alinear) | Qt.AlignVCenter, corto)


def _tarjeta(p, rect):
    p.setPen(QPen(QColor(255, 255, 255, 50), 2))
    p.setBrush(QColor(255, 255, 255, 22))
    p.drawRoundedRect(rect, 44, 44)


def crear_imagen_anio(res, usuario=""):
    """El resumen (de `resumen_anual.calcular`) como QImage 1080×1920."""
    img = QImage(W, H, QImage.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    _fondo_aurora(p, W, H)
    blanco = QColor(255, 255, 255)
    tenue = QColor(255, 255, 255, 185)
    m = 80
    ancho = W - 2 * m

    # cabecera: logo, «Tu año en Caudal» y el año con degradado
    p.drawPixmap(QRectF(m, 92, 54, 54).toRect(), iconos.icono_app(110))
    _texto(p, QRectF(m + 70, 90, 700, 58), "TU AÑO EN CAUDAL", 34, QFont.Bold, tenue)
    f = _fuente(210, QFont.Black)
    ruta = QPainterPath()
    ruta.addText(QPointF(m - 6, 360), f, str(res["anio"]))
    g = QLinearGradient(m, 200, m + 640, 360)
    g.setColorAt(0.0, QColor("#34D399"))
    g.setColorAt(0.5, QColor("#22D3EE"))
    g.setColorAt(1.0, QColor("#F472B6"))
    p.fillPath(ruta, QBrush(g))

    # minutos
    _texto(p, QRectF(m, 410, ancho, 50), "Escuchaste", 40, QFont.DemiBold, tenue)
    _texto(p, QRectF(m, 450, ancho, 190), f"{res['minutos']:,}".replace(",", " "), 170, QFont.Black, blanco)
    sub = "minutos de música"
    if res["minutos"] >= 120:
        sub += f"  ·  {RA.texto_horas(res['minutos'])}"
    _texto(p, QRectF(m, 640, ancho, 54), sub, 38, QFont.DemiBold, tenue)
    _texto(p, QRectF(m, 700, ancho, 50),
           f"{res['escuchas']} canciones sonaron · {res['artistas_distintos']} artistas distintos", 30,
           QFont.Normal, tenue)

    # canción del año
    c = res.get("cancion_top")
    caja = QRectF(m, 790, ancho, 250)
    _tarjeta(p, caja)
    _texto(p, QRectF(m + 40, 812, ancho - 80, 44), "TU CANCIÓN DEL AÑO", 28, QFont.Bold, QColor("#67E8F9"))
    if c:
        _texto(p, QRectF(m + 40, 862, ancho - 80, 76), c["titulo"], 58, QFont.ExtraBold, blanco)
        _texto(p, QRectF(m + 40, 938, ancho - 80, 50), c["artista"], 36, QFont.DemiBold, tenue)
        _texto(p, QRectF(m + 40, 982, ancho - 80, 44), f"La pusiste {c['veces']} veces", 30, QFont.Normal, tenue)

    # artista del año
    a = res.get("artista_top")
    caja = QRectF(m, 1066, ancho, 200)
    _tarjeta(p, caja)
    _texto(p, QRectF(m + 40, 1086, ancho - 80, 44), "TU ARTISTA DEL AÑO", 28, QFont.Bold, QColor("#F9A8D4"))
    if a:
        _texto(p, QRectF(m + 40, 1132, ancho - 80, 76), a["nombre"], 62, QFont.ExtraBold, blanco)
        _texto(p, QRectF(m + 40, 1204, ancho - 80, 44), f"{a['veces']} escuchas", 30, QFont.Normal, tenue)

    # dos tarjetas pequeñas: racha y ánimo (o el día que más escuchaste)
    mitad = (ancho - 24) / 2
    izq, der = QRectF(m, 1292, mitad, 176), QRectF(m + mitad + 24, 1292, mitad, 176)
    _tarjeta(p, izq)
    _tarjeta(p, der)
    _texto(p, QRectF(izq.left() + 30, 1306, mitad - 60, 40), "MEJOR RACHA", 26, QFont.Bold, QColor("#FDE68A"))
    racha = res.get("racha") or 0
    _texto(p, QRectF(izq.left() + 30, 1346, mitad - 60, 76), f"{racha} {'día' if racha == 1 else 'días'}", 60,
           QFont.Black, blanco)
    _texto(p, QRectF(izq.left() + 30, 1420, mitad - 60, 36), "seguidos con música", 26, QFont.Normal, tenue)
    an = res.get("animo")
    if an:
        _texto(p, QRectF(der.left() + 30, 1306, mitad - 60, 40), "TU ÁNIMO", 26, QFont.Bold, QColor("#C4B5FD"))
        _texto(p, QRectF(der.left() + 30, 1346, mitad - 60, 76), an["nombre"], 52, QFont.Black, blanco)
        _texto(p, QRectF(der.left() + 30, 1420, mitad - 60, 36), f"{an['porcentaje']} % de lo que sonó", 26,
               QFont.Normal, tenue)
    else:
        d = res.get("dia_top")
        _texto(p, QRectF(der.left() + 30, 1306, mitad - 60, 40), "TU DÍA MÁS MUSICAL", 26, QFont.Bold,
               QColor("#C4B5FD"))
        _texto(p, QRectF(der.left() + 30, 1346, mitad - 60, 76), d["texto"] if d else "—", 44, QFont.Black, blanco)
        _texto(p, QRectF(der.left() + 30, 1420, mitad - 60, 36), f"{d['escuchas']} canciones" if d else "", 26,
               QFont.Normal, tenue)

    # top 5 de artistas
    _texto(p, QRectF(m, 1500, ancho, 44), "TU TOP 5 DE ARTISTAS", 28, QFont.Bold, tenue)
    for i, x in enumerate(res.get("top_artistas") or []):
        y = 1552 + i * 52
        _texto(p, QRectF(m, y, 60, 48), str(i + 1), 36, QFont.Black, QColor("#34D399"))
        _texto(p, QRectF(m + 64, y, ancho - 64 - 190, 48), x["nombre"], 36, QFont.ExtraBold, blanco)
        _texto(p, QRectF(W - m - 190, y, 190, 48), f"{x['veces']}", 32, QFont.DemiBold, tenue, Qt.AlignRight)

    pie = f"@{usuario} · Caudal" if usuario else "Caudal"
    _texto(p, QRectF(m, H - 84, ancho, 44), pie, 30, QFont.DemiBold, tenue, Qt.AlignHCenter)
    p.end()
    return img


def difuminar(img, factor=22):
    """La imagen borrosa (para la vista previa bloqueada): se reduce y se estira, sin efectos pesados."""
    chica = img.scaled(max(1, img.width() // factor), max(1, img.height() // factor), Qt.IgnoreAspectRatio,
                       Qt.SmoothTransformation)
    return chica.scaled(img.width(), img.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def _nombre_archivo(anio):
    return re.sub(r"[^0-9A-Za-z_-]+", "", f"Tu-anio-en-Caudal-{anio}") or "anio-caudal"


class DialogoAnio(QDialog):
    def __init__(self, ctx, padre=None, anio=None):
        super().__init__(padre)
        self.ctx = ctx
        self.anio = anio
        self.res = None
        self.imagen = None
        self.setWindowTitle("Tu año en Caudal")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)
        t = QLabel("Tu año en Caudal")
        t.setObjectName("titulo_seccion")
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        self.estado = QLabel("Calculando tu año…")
        self.estado.setObjectName("secundario")
        self.estado.setWordWrap(True)
        self.estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.estado)
        self.vista = QLabel()
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setFixedSize(270, 480)
        v.addWidget(self.vista, 0, Qt.AlignHCenter)
        self.aviso = QLabel("🔒 «Tu año en Caudal» es exclusivo para donadores.")
        self.aviso.setObjectName("ayuda")
        self.aviso.setWordWrap(True)
        self.aviso.setAlignment(Qt.AlignCenter)
        v.addWidget(self.aviso)
        self.fila_bloqueo = QHBoxLayout()
        self.fila_bloqueo.addStretch(1)
        from .canje_pase import boton_codigo
        from .donar import boton_donar
        self.bt_donar = boton_donar(texto="Donar aquí")
        self.bt_codigo = boton_codigo(ctx, texto="Tengo un código de prueba")
        self.fila_bloqueo.addWidget(self.bt_donar)
        self.fila_bloqueo.addWidget(self.bt_codigo)
        self.fila_bloqueo.addStretch(1)
        v.addLayout(self.fila_bloqueo)
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_guardar = QPushButton("Guardar imagen")
        self.bt_guardar.clicked.connect(self._guardar)
        self.bt_copiar = QPushButton("Copiar")
        self.bt_copiar.setObjectName("contorno")
        self.bt_copiar.clicked.connect(self._copiar)
        cerrar = QPushButton("Cerrar")
        cerrar.setObjectName("contorno")
        cerrar.clicked.connect(self.accept)
        for b in (self.bt_guardar, self.bt_copiar, cerrar):
            fila.addWidget(b)
        fila.addStretch(1)
        v.addLayout(fila)
        self.msg = QLabel("")
        self.msg.setObjectName("secundario")
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        v.addWidget(self.msg)
        g = getattr(ctx, "premium", None)
        if g is not None:
            g.cambiado.connect(self._pintar)
        self._pintar()
        en_segundo_plano(RA.leer, ctx.coleccion, anio, ok=self._listo, error=self._fallo, dueno=self)

    def _premium(self):
        g = getattr(self.ctx, "premium", None)
        return bool(g is not None and g.premium)

    def _listo(self, res):
        self.res = res
        usuario = (getattr(self.ctx, "cuenta", None) or {}).get("usuario") or ""
        self.imagen = crear_imagen_anio(res, usuario) if res["hay_datos"] else None
        self._pintar()

    def _fallo(self, _e):
        self.estado.setText("No se pudo leer tu historial. Vuelve a intentarlo en un momento.")

    def _pintar(self):
        premium = self._premium()
        hay = self.imagen is not None
        if self.res is not None and not self.res["hay_datos"]:
            self.estado.setText("Todavía hay pocas escuchas este año. Cuando escuches un poco más, aquí verás tu "
                                "resumen.")
        elif hay:
            self.estado.setText("Así quedó tu año. Es una imagen vertical, lista para un estado." if premium
                                else "Tu año ya está listo. Hazte donador para verlo y compartirlo.")
        self.aviso.setVisible(hay and not premium)
        self.bt_donar.setVisible(hay and not premium)
        self.bt_codigo.setVisible(hay and not premium)
        self.bt_guardar.setEnabled(hay and premium)
        self.bt_copiar.setEnabled(hay and premium)
        if hay:
            origen = self.imagen if premium else difuminar(self.imagen)
            self.vista.setPixmap(QPixmap.fromImage(origen).scaled(270, 480, Qt.KeepAspectRatio,
                                                                 Qt.SmoothTransformation))
        else:
            self.vista.clear()

    def _guardar(self):
        if self.imagen is None or not self._premium():
            return
        ruta = os.path.join(carpeta_imagenes(), _nombre_archivo(self.res["anio"]) + ".png")
        n = 2
        while os.path.exists(ruta):
            ruta = os.path.join(carpeta_imagenes(), f"{_nombre_archivo(self.res['anio'])} ({n}).png")
            n += 1
        self.imagen.save(ruta, "PNG")
        self.msg.setText("Guardada en Imágenes › Caudal.")

    def _copiar(self):
        if self.imagen is None or not self._premium():
            return
        QApplication.clipboard().setImage(self.imagen)
        self.msg.setText("Copiada: pégala donde quieras.")


def abrir_anio(ctx, padre=None):
    DialogoAnio(ctx, padre).exec()
