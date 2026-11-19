# -*- coding: utf-8 -*-
"""La tarjeta de tu semana: una imagen vertical 1080×1920 para estados e historias (donadores).

Hermana de «Tu año en Caudal» (`anio_caudal`): mismo estilo y mismo cuadro con candado para quien no es donador.
El cálculo está en `resumen_semanal`."""

import os
import re

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .. import resumen_semanal as RS
from ..hilos import en_segundo_plano
from . import iconos
from .anio_caudal import _fuente, _tarjeta, _texto, difuminar
from .letra_viva import _fondo_aurora, carpeta_imagenes

W, H = 1080, 1920
FRANJAS = {"madrugada": "la madrugada", "mañana": "la mañana", "tarde": "la tarde", "noche": "la noche"}


def _miles(n):
    return f"{int(n):,}".replace(",", " ")


def crear_imagen_semana(res, usuario=""):
    """La tarjeta (de `resumen_semanal.calcular`) como QImage 1080×1920."""
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

    # cabecera: logo, título y el rango de fechas con degradado
    p.drawPixmap(QRectF(m, 92, 54, 54).toRect(), iconos.icono_app(110))
    _texto(p, QRectF(m + 70, 90, 800, 58), "MI SEMANA EN CAUDAL", 34, QFont.Bold, tenue)
    f = _fuente(150, QFont.Black)
    ruta = QPainterPath()
    ruta.addText(QPointF(m - 4, 330), f, res["rango"])
    g = QLinearGradient(m, 200, m + 760, 330)
    g.setColorAt(0.0, QColor("#34D399"))
    g.setColorAt(0.5, QColor("#22D3EE"))
    g.setColorAt(1.0, QColor("#F472B6"))
    p.fillPath(ruta, QBrush(g))

    # minutos
    _texto(p, QRectF(m, 380, ancho, 50), "Escuchaste", 40, QFont.DemiBold, tenue)
    _texto(p, QRectF(m, 420, ancho, 190), _miles(res["minutos"]), 170, QFont.Black, blanco)
    sub = "minutos de música"
    if res["minutos"] >= 120:
        sub += f"  ·  {_horas(res['minutos'])}"
    _texto(p, QRectF(m, 610, ancho, 54), sub, 38, QFont.DemiBold, tenue)
    _texto(p, QRectF(m, 668, ancho, 50),
           f"{res['escuchas']} canciones sonaron · {res['artistas_distintos']} artistas distintos", 30,
           QFont.Normal, tenue)
    cambio = RS.frase_cambio(res.get("cambio"))
    if cambio:
        subio = (res.get("cambio") or 0) >= 0
        _texto(p, QRectF(m, 716, ancho, 46), cambio, 30, QFont.Bold, QColor("#34D399" if subio else "#FCA5A5"))

    # los siete días: barras
    caja = QRectF(m, 790, ancho, 320)
    _tarjeta(p, caja)
    _texto(p, QRectF(m + 40, 806, ancho - 80, 44), "TUS DÍAS", 28, QFont.Bold, QColor("#67E8F9"))
    dias = res["dias"]
    mayor = max([d["minutos"] for d in dias] + [1])
    base_y, alto_max = 1050, 150
    hueco = (ancho - 80) / max(1, len(dias))
    p.setPen(Qt.NoPen)
    for i, d in enumerate(dias):
        x = m + 40 + i * hueco + hueco * 0.18
        w = hueco * 0.64
        alto = max(10.0, alto_max * d["minutos"] / mayor) if d["minutos"] else 10.0
        mejor = res.get("mejor_dia") and d["fecha"] == res["mejor_dia"]["fecha"]
        gr = QLinearGradient(0, base_y - alto, 0, base_y)
        if d["minutos"]:
            gr.setColorAt(0.0, QColor("#F9A8D4") if mejor else QColor("#67E8F9"))
            gr.setColorAt(1.0, QColor("#F472B6") if mejor else QColor("#34D399"))
        else:
            gr.setColorAt(0.0, QColor(255, 255, 255, 45))
            gr.setColorAt(1.0, QColor(255, 255, 255, 45))
        p.setBrush(QBrush(gr))
        p.drawRoundedRect(QRectF(x, base_y - alto, w, alto), 14, 14)
        _texto(p, QRectF(x - 10, base_y + 6, w + 20, 40), d["letra"], 30, QFont.Bold, tenue, Qt.AlignHCenter)

    # canción de la semana
    c = res.get("cancion_top")
    caja = QRectF(m, 1140, ancho, 230)
    _tarjeta(p, caja)
    _texto(p, QRectF(m + 40, 1158, ancho - 80, 44), "LA CANCIÓN DE TU SEMANA", 28, QFont.Bold, QColor("#67E8F9"))
    if c:
        _texto(p, QRectF(m + 40, 1206, ancho - 80, 76), c["titulo"], 56, QFont.ExtraBold, blanco)
        _texto(p, QRectF(m + 40, 1282, ancho - 80, 48), c["artista"], 34, QFont.DemiBold, tenue)
        _texto(p, QRectF(m + 40, 1324, ancho - 80, 40), f"La pusiste {c['veces']} {'vez' if c['veces'] == 1 else 'veces'}",
               28, QFont.Normal, tenue)

    # top 3 de artistas
    _texto(p, QRectF(m, 1400, ancho, 44), "TUS ARTISTAS", 28, QFont.Bold, tenue)
    for i, a in enumerate(res.get("top_artistas") or []):
        y = 1450 + i * 54
        _texto(p, QRectF(m, y, 60, 50), str(i + 1), 36, QFont.Black, QColor("#34D399"))
        _texto(p, QRectF(m + 64, y, ancho - 64 - 190, 50), a["nombre"], 36, QFont.ExtraBold, blanco)
        _texto(p, QRectF(W - m - 190, y, 190, 50), f"{a['veces']}", 32, QFont.DemiBold, tenue, Qt.AlignRight)

    # dos tarjetas pequeñas: días con música y la franja del día
    mitad = (ancho - 24) / 2
    izq, der = QRectF(m, 1640, mitad, 160), QRectF(m + mitad + 24, 1640, mitad, 160)
    _tarjeta(p, izq)
    _tarjeta(p, der)
    _texto(p, QRectF(izq.left() + 30, 1654, mitad - 60, 40), "DÍAS CON MÚSICA", 26, QFont.Bold, QColor("#FDE68A"))
    _texto(p, QRectF(izq.left() + 30, 1696, mitad - 60, 76), f"{res['dias_con_musica']} de 7", 58, QFont.Black, blanco)
    _texto(p, QRectF(der.left() + 30, 1654, mitad - 60, 40), "TU MOMENTO", 26, QFont.Bold, QColor("#C4B5FD"))
    _texto(p, QRectF(der.left() + 30, 1696, mitad - 60, 76), FRANJAS.get(res["franja"], res["franja"]), 46,
           QFont.Black, blanco)

    pie = f"@{usuario} · Caudal" if usuario else "Caudal"
    _texto(p, QRectF(m, H - 84, ancho, 44), pie, 30, QFont.DemiBold, tenue, Qt.AlignHCenter)
    p.end()
    return img


def _horas(minutos):
    from ..resumen_anual import texto_horas
    return texto_horas(minutos)


def _nombre_archivo(res):
    return re.sub(r"[^0-9A-Za-z_-]+", "", f"Mi-semana-en-Caudal-{res['hasta']:%Y-%m-%d}") or "semana-caudal"


class DialogoSemana(QDialog):
    def __init__(self, ctx, padre=None, ahora=None):
        super().__init__(padre)
        self.ctx = ctx
        self.ahora = ahora
        self.res = None
        self.imagen = None
        self.setWindowTitle("Mi semana en Caudal")
        self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)
        t = QLabel("Mi semana en Caudal")
        t.setObjectName("titulo_seccion")
        t.setAlignment(Qt.AlignCenter)
        v.addWidget(t)
        self.estado = QLabel("Calculando tu semana…")
        self.estado.setObjectName("secundario")
        self.estado.setWordWrap(True)
        self.estado.setAlignment(Qt.AlignCenter)
        v.addWidget(self.estado)
        self.vista = QLabel()
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setFixedSize(270, 480)
        v.addWidget(self.vista, 0, Qt.AlignHCenter)
        self.aviso = QLabel("🔒 La tarjeta de tu semana es exclusiva para donadores.")
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
        en_segundo_plano(self._leer, ok=self._listo, error=self._fallo, dueno=self)

    def _leer(self):
        copiar = getattr(self.ctx.coleccion, "copia_de_lectura", None)
        if copiar is None:
            return RS.leer(self.ctx.coleccion, self.ahora)
        with copiar() as c:
            return RS.leer(c, self.ahora)

    def _premium(self):
        g = getattr(self.ctx, "premium", None)
        return bool(g is not None and g.premium)

    def _listo(self, res):
        self.res = res
        usuario = (getattr(self.ctx, "cuenta", None) or {}).get("usuario") or ""
        self.imagen = crear_imagen_semana(res, usuario) if res["hay_datos"] else None
        self._pintar()

    def _fallo(self, _e):
        self.estado.setText("No se pudo leer tu historial. Vuelve a intentarlo en un momento.")

    def _pintar(self):
        premium = self._premium()
        hay = self.imagen is not None
        if self.res is not None and not self.res["hay_datos"]:
            self.estado.setText("Esta semana hay pocas escuchas. Escucha un poco más y aquí verás tu tarjeta.")
        elif hay:
            self.estado.setText("Así quedó tu semana. Es una imagen vertical, lista para un estado." if premium
                                else "Tu semana ya está lista. Hazte donador para verla y compartirla.")
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
        base = _nombre_archivo(self.res)
        ruta = os.path.join(carpeta_imagenes(), base + ".png")
        n = 2
        while os.path.exists(ruta):
            ruta = os.path.join(carpeta_imagenes(), f"{base} ({n}).png")
            n += 1
        self.imagen.save(ruta, "PNG")
        self.msg.setText("Guardada en Imágenes › Caudal.")

    def _copiar(self):
        if self.imagen is None or not self._premium():
            return
        QApplication.clipboard().setImage(self.imagen)
        self.msg.setText("Copiada: pégala donde quieras.")


def abrir_semana(ctx, padre=None):
    DialogoSemana(ctx, padre).exec()

