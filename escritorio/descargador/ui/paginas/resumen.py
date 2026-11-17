# -*- coding: utf-8 -*-
"""Tu resumen: como el Wrapped de Spotify, pero siempre disponible.

Tarjetas grandes que se pasan con las flechas (o un clic) para la semana, el
mes o el año: minutos, top canciones y artistas, horas del dia, racha y la
cancion del mes. Todo se pinta a mano en un solo widget, con un reloj que
anima la entrada de cada tarjeta y el paso entre ellas; la misma funcion de
pintado sirve para exportar la tarjeta a PNG.
"""

import math
import os

from PySide6.QtCore import QElapsedTimer, QEvent, QPointF, QRectF, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ... import mixes as mx
from ...hilos import en_segundo_plano
from .. import iconos, imagenes
from ..componentes import BotonIcono, Chip, Pagina, SinResultados, a_la_vista, fuente
from ..estilos import C

ANCHO, ALTO = 420, 560          # tamano logico de una tarjeta (3:4)
EXPORTAR_ANCHO = 1080           # el PNG sale a 1080 x 1440

# (degradado de arriba a la izquierda, de abajo a la derecha)
COLORES = {
    "minutos": ("#0F2F7A", "#22D3EE"),
    "canciones": ("#4A1450", "#FF5C8A"),
    "artistas": ("#2A1D7A", "#7C5CFF"),
    "horas": ("#0B3A2B", "#2BD576"),
    "racha": ("#6B260B", "#FFB443"),
    "mes": ("#2A0F3D", "#FF7A45"),
}

NOMBRES = {"minutos": "Minutos", "canciones": "Top canciones", "artistas": "Top artistas",
           "horas": "Horas del día", "racha": "Racha", "mes": "Canción del mes"}


def _miles(n):
    return f"{int(n):,}".replace(",", ".")


def _suave(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _escalon(t, i, paso=0.09, largo=0.5):
    """Progreso del elemento i de una tarjeta: entran uno detras de otro."""
    return _suave((t - i * paso) / largo)


def _plural(n, uno, varios):
    return uno if n == 1 else varios


def tarjetas_de(r):
    """Que tarjetas tiene un resumen (las que tienen algo que contar)."""
    if r.get("vacio"):
        return []
    salida = ["minutos"]
    if r["top_canciones"]:
        salida.append("canciones")
    if r["top_artistas"]:
        salida.append("artistas")
    salida += ["horas", "racha"]
    if r.get("cancion_del_mes"):
        salida.append("mes")
    return salida


class Imagenes:
    """Portadas de las tarjetas: se piden una vez y se guardan recortadas por
    tamano, para no reescalar cada fotograma."""

    def __init__(self, al_llegar):
        self.al_llegar = al_llegar
        self.originales = {}
        self.recortes = {}

    def pedir(self, url):
        if not url or url in self.originales:
            return
        self.originales[url] = None

        def listo(img, url=url):
            self.originales[url] = img if img is not None and not img.isNull() else None
            try:
                self.al_llegar()
            except RuntimeError:
                pass
        imagenes.imagen(url, listo)

    def recorte(self, url, w, h, forma, radio, escala):
        img = self.originales.get(url)
        if img is None:
            return None
        clave = (url, int(w), int(h), forma, radio, round(escala, 2))
        pm = self.recortes.get(clave)
        if pm is None:
            pm = imagenes.formar(img, w * escala, h * escala, forma, radio * escala)
            pm.setDevicePixelRatio(1.0)
            self.recortes[clave] = pm
            if len(self.recortes) > 120:
                self.recortes.pop(next(iter(self.recortes)))
        return pm


# ---------------------------------------------------------------- pintado

class Pintor:
    """Pinta una tarjeta en un rectangulo de ANCHO x ALTO (en logico)."""

    def __init__(self, r, imgs):
        self.r = r
        self.imgs = imgs
        self.escala = 1.0

    # --- piezas

    def _fondo(self, p, tipo, reloj, redondeo):
        a, b = COLORES[tipo]
        if tipo == "mes" and self.r.get("color_mes"):
            a = QColor(self.r["color_mes"]).darker(150).name()
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, ANCHO, ALTO), redondeo, redondeo)
        p.setClipPath(ruta)
        g = QLinearGradient(0, 0, ANCHO, ALTO)
        g.setColorAt(0, QColor(a))
        g.setColorAt(1, QColor(b))
        p.fillRect(QRectF(0, 0, ANCHO, ALTO), g)
        # manchas de luz que flotan despacio
        p.setPen(Qt.NoPen)
        for k, (cx, cy, rad, vel) in enumerate(((0.85, 0.12, 190, 0.35), (0.1, 0.78, 230, 0.27),
                                                (0.6, 1.0, 160, 0.42))):
            x = ANCHO * cx + math.sin(reloj * vel + k * 2.1) * 26
            y = ALTO * cy + math.cos(reloj * vel * 0.8 + k) * 22
            rg = QRadialGradient(QPointF(x, y), rad)
            rg.setColorAt(0, QColor(255, 255, 255, 46))
            rg.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(rg)
            p.drawEllipse(QPointF(x, y), rad, rad)
        # grano de anillos, como un disco
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 14), 1.2))
        giro = reloj * 0.15
        for k in range(5):
            rad = 120 + k * 34
            p.drawArc(QRectF(ANCHO - 70 - rad, -60 - rad + 60, rad * 2, rad * 2),
                      int((200 + math.degrees(giro) + k * 9) * 16), 70 * 16)

    def _texto(self, p, rect, texto, px, peso=QFont.Normal, color="#FFFFFF", alfa=1.0,
               alin=Qt.AlignLeft | Qt.AlignVCenter, titulo=False, elidir=True):
        f = fuente(px, peso, titulo)
        p.setFont(f)
        c = QColor(color)
        c.setAlphaF(max(0.0, min(1.0, c.alphaF() * alfa)))
        p.setPen(c)
        if elidir and not (alin & Qt.TextWordWrap):
            texto = QFontMetrics(f).elidedText(texto, Qt.ElideRight, int(rect.width()))
        p.drawText(rect, int(alin), texto)

    def _cabecera(self, p, t, rotulo):
        a = _escalon(t, 0)
        p.setOpacity(a)
        self._texto(p, QRectF(30, 26 - 8 * (1 - a), ANCHO - 60, 18),
                    f"CAUDAL  ·  {self.r['nombre'].upper()}", 11.5, QFont.Bold, "#FFFFFF", 0.75)
        p.setOpacity(1.0)
        b = _escalon(t, 1)
        p.setOpacity(b)
        self._texto(p, QRectF(30, 48 + 12 * (1 - b), ANCHO - 60, 74), rotulo, 30, QFont.Black,
                    alin=Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, titulo=True)
        p.setOpacity(1.0)

    def _pie(self, p):
        self._texto(p, QRectF(30, ALTO - 40, ANCHO - 60, 20), self.r["rango"].capitalize(),
                    11.5, QFont.DemiBold, "#FFFFFF", 0.65)
        self._texto(p, QRectF(30, ALTO - 40, ANCHO - 60, 20), "Caudal", 13, QFont.Black,
                    "#FFFFFF", 0.8, Qt.AlignRight | Qt.AlignVCenter, titulo=True)

    def _portada(self, p, url, rect, forma="cuadrada", radio=6):
        pm = self.imgs.recorte(url, rect.width(), rect.height(), forma, radio, self.escala)
        if pm is not None:
            p.drawPixmap(rect, pm, QRectF(pm.rect()))
            return
        ruta = QPainterPath()
        if forma == "redonda":
            ruta.addEllipse(rect)
        else:
            ruta.addRoundedRect(rect, radio, radio)
        p.fillPath(ruta, QColor(0, 0, 0, 60))
        lado = int(min(rect.width(), rect.height()) * 0.4)
        p.drawPixmap(int(rect.center().x() - lado / 2), int(rect.center().y() - lado / 2),
                     iconos.pixmap("usuario" if forma == "redonda" else "musica", lado,
                                   "#FFFFFF"))

    # --- tarjetas

    def pintar(self, p, tipo, t, reloj=0.0, redondeo=22):
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self._fondo(p, tipo, reloj, redondeo)
        getattr(self, "_t_" + tipo)(p, t)
        self._pie(p)
        p.restore()

    def _t_minutos(self, p, t):
        r = self.r
        self._cabecera(p, t, f"Esta es {r['nombre']} en música")
        a = _escalon(t, 2, largo=0.8)
        p.setOpacity(_escalon(t, 2))
        n = int(round(r["minutos"] * a))
        self._texto(p, QRectF(26, 150, ANCHO - 52, 120), _miles(n), 96 if r["minutos"] < 10000
                    else 80, QFont.Black, titulo=True)
        self._texto(p, QRectF(30, 262, ANCHO - 60, 26),
                    _plural(r["minutos"], "minuto escuchado", "minutos escuchados"), 19,
                    QFont.Bold, alfa=0.9)
        p.setOpacity(1.0)
        # comparacion con el periodo anterior
        b = _escalon(t, 4)
        p.setOpacity(b)
        cambio = r.get("cambio")
        if cambio is None:
            frase = "Tu primer resumen con Caudal" if r["minutos_antes"] == 0 else ""
        elif cambio == 0:
            frase = "Lo mismo que el periodo anterior"
        elif cambio > 0:
            frase = f"▲ {cambio}% más que el periodo anterior"
        else:
            frase = f"▼ {-cambio}% menos que el periodo anterior"
        if frase:
            f = fuente(13.5, QFont.Bold)
            ancho = QFontMetrics(f).horizontalAdvance(frase) + 28
            caja = QRectF(30, 304, ancho, 32)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(caja, 16, 16)
            self._texto(p, caja, frase, 13.5, QFont.Bold, alin=Qt.AlignCenter)
        p.setOpacity(1.0)
        # tres cifras abajo
        datos = ((r["escuchas"], "reproducciones"), (r["canciones_distintas"], "canciones"),
                 (r["artistas_distintos"], "artistas"))
        ancho = (ANCHO - 60) / 3
        for i, (valor, rotulo) in enumerate(datos):
            c = _escalon(t, 5 + i)
            p.setOpacity(c)
            x = 30 + i * ancho
            y = 384 + 14 * (1 - c)
            self._texto(p, QRectF(x, y, ancho - 8, 44), _miles(round(valor * _suave(t * 1.4))),
                        32, QFont.Black, titulo=True)
            self._texto(p, QRectF(x, y + 44, ancho - 8, 20), rotulo, 13, QFont.DemiBold,
                        alfa=0.8)
        p.setOpacity(1.0)

    def _t_canciones(self, p, t):
        self._cabecera(p, t, "Tus canciones más escuchadas")
        y0 = 140
        for i, c in enumerate(self.r["top_canciones"][:5]):
            a = _escalon(t, 2 + i)
            if a <= 0:
                continue
            p.setOpacity(a)
            dx = 40 * (1 - a)
            alto = 66
            y = y0 + i * (alto + 8)
            if i == 0:
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255, 34))
                p.drawRoundedRect(QRectF(20 + dx, y - 4, ANCHO - 40, alto + 8), 12, 12)
            self._texto(p, QRectF(26 + dx, y, 34, alto), str(i + 1), 26, QFont.Black,
                        alin=Qt.AlignCenter, titulo=True)
            self._portada(p, c["pista"].get("miniatura") or "", QRectF(66 + dx, y + 5, 56, 56))
            ancho_t = ANCHO - 66 - 56 - 14 - 92 - 20
            self._texto(p, QRectF(134 + dx, y + 10, ancho_t, 24), c["pista"].get("titulo") or "",
                        15.5, QFont.Bold)
            self._texto(p, QRectF(134 + dx, y + 34, ancho_t, 20), c["pista"].get("artista") or "",
                        13, alfa=0.75)
            self._texto(p, QRectF(ANCHO - 112 + dx, y, 84, alto),
                        f"{c['veces']} {_plural(c['veces'], 'vez', 'veces')}", 13, QFont.Bold,
                        alfa=0.85, alin=Qt.AlignRight | Qt.AlignVCenter)
        p.setOpacity(1.0)

    def _t_artistas(self, p, t):
        r = self.r
        self._cabecera(p, t, "Tus artistas favoritos")
        arts = r["top_artistas"]
        top = arts[0]
        a = _escalon(t, 2, largo=0.6)
        p.setOpacity(a)
        lado = 150 * (0.85 + 0.15 * a)
        rect = QRectF(ANCHO / 2 - lado / 2, 132 + (150 - lado) / 2, lado, lado)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawEllipse(rect.translated(0, 6))
        self._portada(p, top.get("miniatura") or "", rect, "redonda")
        self._texto(p, QRectF(30, 292, ANCHO - 60, 34), top["nombre"], 26, QFont.Black,
                    alin=Qt.AlignCenter, titulo=True)
        self._texto(p, QRectF(30, 324, ANCHO - 60, 20),
                    f"#1  ·  {_miles(top['minutos'])} min  ·  {top['veces']} "
                    f"{_plural(top['veces'], 'escucha', 'escuchas')}", 13, QFont.DemiBold,
                    alfa=0.85, alin=Qt.AlignCenter)
        p.setOpacity(1.0)
        y = 362
        for i, ar in enumerate(arts[1:5]):
            b = _escalon(t, 4 + i)
            p.setOpacity(b)
            dx = 30 * (1 - b)
            self._texto(p, QRectF(34 + dx, y, 26, 34), str(i + 2), 17, QFont.Black, alfa=0.8,
                        alin=Qt.AlignCenter, titulo=True)
            self._portada(p, ar.get("miniatura") or "", QRectF(66 + dx, y + 1, 32, 32), "redonda")
            self._texto(p, QRectF(108 + dx, y, ANCHO - 210, 34), ar["nombre"], 15, QFont.Bold)
            self._texto(p, QRectF(ANCHO - 120 + dx, y, 90, 34), f"{_miles(ar['minutos'])} min", 13,
                        QFont.DemiBold, alfa=0.8, alin=Qt.AlignRight | Qt.AlignVCenter)
            y += 38
        p.setOpacity(1.0)
        nuevos = r.get("descubrimientos") or []
        if nuevos and len(arts) <= 4:
            c = _escalon(t, 8)
            p.setOpacity(c)
            self._texto(p, QRectF(30, ALTO - 70, ANCHO - 60, 20),
                        "Nuevo para ti: " + ", ".join(n["nombre"] for n in nuevos), 12.5,
                        QFont.DemiBold, alfa=0.85)
            p.setOpacity(1.0)

    def _t_horas(self, p, t):
        r = self.r
        franja = r["franja"]
        frase = {"madrugada": "Eres de madrugada", "mañana": "Eres de mañana",
                 "tarde": "Eres de tarde", "noche": "Eres de noche"}[franja]
        self._cabecera(p, t, frase)
        a = _escalon(t, 2)
        p.setOpacity(a)
        h = r["hora_pico"]
        self._texto(p, QRectF(30, 132, ANCHO - 60, 24),
                    f"Tu hora pico es a las {h:02d}:00, con {_miles(r['por_hora'][h])} min",
                    15, QFont.DemiBold, alfa=0.9)
        p.setOpacity(1.0)
        # barras por hora
        maximo = max(r["por_hora"]) or 1
        area = QRectF(30, 186, ANCHO - 60, 250)
        ancho = area.width() / 24
        p.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.DashLine))
        p.drawLine(QPointF(area.left(), area.bottom()), QPointF(area.right(), area.bottom()))
        p.setPen(Qt.NoPen)
        for i, m in enumerate(r["por_hora"]):
            b = _escalon(t, 2 + i * 0.25, largo=0.45)
            alto = max(3.0, area.height() * (m / maximo)) * b
            barra = QRectF(area.left() + i * ancho + ancho * 0.16, area.bottom() - alto,
                           ancho * 0.68, alto)
            p.setBrush(QColor(255, 255, 255, 245 if i == h else 105))
            p.drawRoundedRect(barra, ancho * 0.3, ancho * 0.3)
        for hora in (0, 6, 12, 18, 23):
            self._texto(p, QRectF(area.left() + hora * ancho - 10, area.bottom() + 8, ancho + 20,
                                  16), f"{hora:02d}", 11, QFont.DemiBold, alfa=0.7,
                        alin=Qt.AlignCenter)
        c = _escalon(t, 9)
        p.setOpacity(c)
        momentos = {"madrugada": "Cuando todos duermen, tú le das al play.",
                    "mañana": "Arrancas el día con música.",
                    "tarde": "Tus tardes tienen banda sonora.",
                    "noche": "La noche es cuando más suena lo tuyo."}
        self._texto(p, QRectF(30, 470, ANCHO - 60, 22), momentos[franja], 14, QFont.DemiBold,
                    alfa=0.9)
        p.setOpacity(1.0)

    def _t_racha(self, p, t):
        r = self.r
        actual, mejor = r["racha_actual"], r["racha_mas_larga"]
        self._cabecera(p, t, "Tu racha" if actual else "Tu constancia")
        a = _escalon(t, 2, largo=0.7)
        p.setOpacity(_escalon(t, 2))
        n = actual if actual else r["dias_con_musica"]
        self._texto(p, QRectF(26, 118, 200, 110), str(int(round(n * a))), 92, QFont.Black,
                    titulo=True)
        self._texto(p, QRectF(30, 220, ANCHO - 60, 24),
                    (_plural(actual, "día seguido con música", "días seguidos con música")
                     if actual else _plural(n, "día con música", "días con música")),
                    18, QFont.Bold, alfa=0.92)
        p.setOpacity(1.0)
        b = _escalon(t, 3)
        p.setOpacity(b)
        dias = len(r["por_dia"])
        self._texto(p, QRectF(30, 250, ANCHO - 60, 20),
                    f"Tu mejor racha: {mejor} {_plural(mejor, 'día', 'días')}  ·  "
                    f"{r['dias_con_musica']} de {dias} días", 13.5, QFont.DemiBold, alfa=0.8)
        p.setOpacity(1.0)
        # calendario: un cuadrito por dia, mas claro cuanto mas escuchaste
        por_dia = r["por_dia"]
        columnas = 7 if dias <= 31 else 53
        filas = math.ceil(dias / columnas)
        area = QRectF(30, 292, ANCHO - 60, 196)
        hueco = 6 if columnas == 7 else 1.6
        lado = min((area.width() - hueco * (columnas - 1)) / columnas,
                   (area.height() - hueco * (filas - 1)) / filas)
        maximo = max(por_dia) or 1
        p.setPen(Qt.NoPen)
        for i, m in enumerate(por_dia):
            if columnas == 7:
                col, fila = i % 7, i // 7
            else:
                col, fila = i // 7, i % 7
            c = _escalon(t, 3 + (i / max(1, dias)) * 4, largo=0.35)
            if c <= 0:
                continue
            x = area.left() + col * (lado + hueco)
            y = area.top() + fila * (lado + hueco)
            alfa = 28 if m == 0 else int(80 + 175 * (m / maximo))
            p.setBrush(QColor(255, 255, 255, int(alfa * c)))
            s = lado * (0.6 + 0.4 * c)
            p.drawRoundedRect(QRectF(x + (lado - s) / 2, y + (lado - s) / 2, s, s),
                              min(6, s * 0.25), min(6, s * 0.25))

    def _t_mes(self, p, t):
        r = self.r
        c = r["cancion_del_mes"]
        pista = c["pista"]
        self._cabecera(p, t, f"Tu canción de {r['nombre_mes']}")
        a = _escalon(t, 2, largo=0.7)
        p.setOpacity(_escalon(t, 2))
        lado = 230
        p.save()
        p.translate(ANCHO / 2, 140 + lado / 2)
        p.rotate(-6 * (1 - a))
        p.scale(0.8 + 0.2 * a, 0.8 + 0.2 * a)
        rect = QRectF(-lado / 2, -lado / 2, lado, lado)
        p.setPen(Qt.NoPen)
        for k in range(3):                    # sombra en capas
            p.setBrush(QColor(0, 0, 0, 30))
            p.drawRoundedRect(rect.adjusted(-k * 3, k * 4, k * 3, k * 6), 10, 10)
        self._portada(p, pista.get("miniatura") or "", rect, radio=10)
        p.restore()
        p.setOpacity(1.0)
        b = _escalon(t, 4)
        p.setOpacity(b)
        self._texto(p, QRectF(30, 394 + 10 * (1 - b), ANCHO - 60, 34), pista.get("titulo") or "",
                    24, QFont.Black, alin=Qt.AlignCenter, titulo=True)
        self._texto(p, QRectF(30, 428 + 10 * (1 - b), ANCHO - 60, 22), pista.get("artista") or "",
                    15, QFont.DemiBold, alfa=0.85, alin=Qt.AlignCenter)
        p.setOpacity(1.0)
        d = _escalon(t, 6)
        p.setOpacity(d)
        frase = (f"La pusiste {c['veces']} {_plural(c['veces'], 'vez', 'veces')}"
                 f"  ·  {_miles(c['minutos'])} min")
        f = fuente(13.5, QFont.Bold)
        ancho = QFontMetrics(f).horizontalAdvance(frase) + 30
        caja = QRectF(ANCHO / 2 - ancho / 2, 466, ancho, 32)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(caja, 16, 16)
        self._texto(p, caja, frase, 13.5, QFont.Bold, alin=Qt.AlignCenter)
        p.setOpacity(1.0)


# ---------------------------------------------------------------- escenario

class Escenario(QWidget):
    """Las tarjetas, una cada vez, con su entrada animada y el paso entre ellas.
    Clic en la mitad izquierda: anterior; en la derecha: siguiente."""

    cambio = Signal(int)
    ENTRADA_MS = 1300
    PASO_MS = 460
    PUNTOS = 30

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setFixedSize(ANCHO, ALTO + self.PUNTOS)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.r = None
        self.tipos = []
        self.i = 0
        self.anterior = None
        self.sentido = 1
        self.imgs = Imagenes(self.update)
        self.pintor = None
        self.reloj = QElapsedTimer()
        self.reloj.start()
        self.t_entrada = 0
        self.t_paso = -10_000
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tic)

    # 60 cuadros/s solo mientras entra una tarjeta o se pasa a otra; quieta, las manchas de luz
    # flotan tan despacio que 20 cuadros/s se ven igual; con la ventana minimizada, nada
    FLUIDO_MS, TRANQUILO_MS, DORMIDO_MS = 16, 50, 500

    def _ritmo(self, ms):
        if self.timer.interval() != ms:
            self.timer.setInterval(ms)

    def _tic(self):
        if not a_la_vista(self):
            self._ritmo(self.DORMIDO_MS)
            return
        entrada, paso, _r = self.progreso()
        self._ritmo(self.FLUIDO_MS if (entrada < 1.0 or paso < 1.0) else self.TRANQUILO_MS)
        self.update()

    def set_resumen(self, r):
        self.r = r
        self.tipos = tarjetas_de(r)
        self.pintor = Pintor(r, self.imgs)
        for c in r["top_canciones"]:
            self.imgs.pedir(c["pista"].get("miniatura"))
        for a in r["top_artistas"]:
            self.imgs.pedir(a.get("miniatura"))
        if r.get("cancion_del_mes"):
            url = r["cancion_del_mes"]["pista"].get("miniatura")
            self.imgs.pedir(url)
            self._color_mes(url)
        self.i = 0
        self.anterior = None
        self.t_entrada = self.reloj.elapsed()
        self.t_paso = -10_000
        self._ritmo(self.FLUIDO_MS)
        self.update()

    def _color_mes(self, url):
        r = self.r

        def listo(img):
            try:
                if img is not None and not img.isNull() and self.r is r:
                    r["color_mes"] = imagenes.color_dominante(img).name()
                    self.update()
            except (RuntimeError, AttributeError):
                pass
        if url:
            imagenes.imagen(url, listo)

    def ir(self, i):
        if not self.tipos:
            return
        i = max(0, min(len(self.tipos) - 1, i))
        if i == self.i:
            return
        self.sentido = 1 if i > self.i else -1
        self.anterior = self.i
        self.i = i
        ahora = self.reloj.elapsed()
        self.t_paso = ahora
        self.t_entrada = ahora
        self._ritmo(self.FLUIDO_MS)
        self.cambio.emit(i)
        self.update()

    def siguiente(self):
        self.ir(self.i + 1)

    def previa(self):
        self.ir(self.i - 1)

    # --- eventos

    def showEvent(self, e):
        super().showEvent(e)
        self.timer.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.timer.stop()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self.tipos:
            return
        pos = e.position()
        if pos.y() > ALTO:
            n = len(self.tipos)
            x0 = ANCHO / 2 - (n * 18) / 2
            k = int((pos.x() - x0) // 18)
            if 0 <= k < n:
                self.ir(k)
            return
        if pos.x() < ANCHO * 0.35:
            self.previa()
        else:
            self.siguiente()

    def event(self, e):
        # las flechas sueltas son atajos de la ventana (avanzar el video): con
        # el foco aqui, pasan las tarjetas
        if (e.type() == QEvent.ShortcutOverride and e.key() in (Qt.Key_Left, Qt.Key_Right)
                and not e.modifiers()):
            e.accept()
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Right:
            self.siguiente()
        elif e.key() == Qt.Key_Left:
            self.previa()
        else:
            super().keyPressEvent(e)

    # --- pintado

    def progreso(self):
        ahora = self.reloj.elapsed()
        entrada = min(1.0, (ahora - self.t_entrada) / self.ENTRADA_MS)
        paso = min(1.0, (ahora - self.t_paso) / self.PASO_MS)
        return entrada, paso, ahora / 1000.0

    def paintEvent(self, _e):
        if not self.tipos or self.pintor is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        entrada, paso, reloj = self.progreso()
        s = _suave(paso)
        if self.anterior is not None and paso < 1.0:
            # la que se va: se corre hacia atras, se achica y se apaga
            p.save()
            p.setOpacity(1 - s)
            p.translate(ANCHO / 2 - self.sentido * ANCHO * 0.22 * s, ALTO / 2)
            esc = 1 - 0.06 * s
            p.scale(esc, esc)
            p.translate(-ANCHO / 2, -ALTO / 2)
            self.pintor.pintar(p, self.tipos[self.anterior], 1.0, reloj)
            p.restore()
        p.save()
        if self.anterior is not None and paso < 1.0:
            p.setOpacity(s)
            p.translate(ANCHO / 2 + self.sentido * ANCHO * 0.3 * (1 - s), ALTO / 2)
            esc = 0.94 + 0.06 * s
            p.scale(esc, esc)
            p.translate(-ANCHO / 2, -ALTO / 2)
        self.pintor.pintar(p, self.tipos[self.i], entrada, reloj)
        p.restore()
        # puntos de abajo (el actual se estira)
        n = len(self.tipos)
        x = ANCHO / 2 - (n * 18) / 2
        p.setPen(Qt.NoPen)
        for k in range(n):
            activo = k == self.i
            w = 8 + (14 * s if activo else (14 * (1 - s) if k == self.anterior and paso < 1
                                            else 0))
            p.setBrush(QColor(C["texto"] if activo else C["superficie3"]))
            p.drawRoundedRect(QRectF(x + 9 - w / 2 + 2, ALTO + 13, w, 8), 4, 4)
            x += 18

    # --- exportar

    def exportar(self, ruta, ancho=EXPORTAR_ANCHO):
        """Guarda la tarjeta actual como PNG (ya entera, sin animacion)."""
        if not self.tipos:
            return False
        escala = ancho / ANCHO
        img = QImage(int(ANCHO * escala), int(ALTO * escala), QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.scale(escala, escala)
        self.pintor.escala = escala
        try:
            self.pintor.pintar(p, self.tipos[self.i], 1.0, 1.2, redondeo=0)
        finally:
            self.pintor.escala = 1.0
            p.end()
        return img.save(ruta, "PNG")


# ---------------------------------------------------------------- pagina

class PaginaResumen(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Tu resumen"
        self.set_color("#2A1D5A")
        self.periodo = "semana"
        self.historial = []
        self._resumenes = {}
        # todo el historial (pueden ser decenas de miles de escuchas) se lee y se resume en segundo
        # plano, con su propia conexión a la base: la página aparece al momento con un esqueleto
        copiar = getattr(ctx.coleccion, "copia_de_lectura", None)
        self._cargando = copiar is not None
        if not self._cargando:
            self.historial = mx.leer_historial(ctx.coleccion)
        self._construir()
        if self._cargando:
            def leer():
                with copiar() as c:
                    h = mx.leer_historial(c)
                return h, {k: mx.calcular_resumen(h, k) for k in mx.PERIODOS}
            en_segundo_plano(leer, ok=self._llego_historial, error=self._fallo_historial, dueno=self)

    def _llego_historial(self, datos):
        self.historial, self._resumenes = datos
        self._fin_carga()

    def _fallo_historial(self, _e):
        self.historial, self._resumenes = mx.leer_historial(self.ctx.coleccion), {}
        self._fin_carga()

    def _fin_carga(self):
        self._cargando = False
        try:
            self.esqueleto.hide()
            self.esqueleto.deleteLater()
        except (AttributeError, RuntimeError):
            pass
        self.elegir(self.periodo)

    def _construir(self):
        cab = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(2)
        t = QLabel("Tu resumen")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        textos.addWidget(t)
        self.et_rango = QLabel("")
        self.et_rango.setObjectName("secundario")
        textos.addWidget(self.et_rango)
        cab.addLayout(textos)
        cab.addStretch(1)
        self.chips = {}
        for clave, (_d, etiqueta, _n, _r) in mx.PERIODOS.items():
            c = Chip(etiqueta)
            c.setChecked(clave == self.periodo)
            c.clicked.connect(lambda _=False, k=clave: self.elegir(k))
            cab.addWidget(c, 0, Qt.AlignBottom)
            self.chips[clave] = c
        self.cuerpo.addLayout(cab)

        self.zona = QWidget()
        self.zv = QVBoxLayout(self.zona)
        self.zv.setContentsMargins(0, 0, 0, 0)
        self.zv.setSpacing(18)
        fila = QHBoxLayout()
        fila.setSpacing(18)
        fila.addStretch(1)
        estilo = (f"QPushButton{{background:{C['superficie2']};border:none;border-radius:22px;}}"
                  f"QPushButton:hover{{background:{C['superficie3']};}}"
                  f"QPushButton:disabled{{background:transparent;}}")
        self.bt_izq = BotonIcono("atras", 20, "Anterior  (←)", 44)
        self.bt_izq.setStyleSheet(estilo)
        self.bt_der = BotonIcono("adelante", 20, "Siguiente  (→)", 44)
        self.bt_der.setStyleSheet(estilo)
        self.escenario = Escenario()
        self.bt_izq.clicked.connect(self.escenario.previa)
        self.bt_der.clicked.connect(self.escenario.siguiente)
        self.escenario.cambio.connect(self._flechas)
        fila.addWidget(self.bt_izq, 0, Qt.AlignVCenter)
        fila.addWidget(self.escenario)
        fila.addWidget(self.bt_der, 0, Qt.AlignVCenter)
        fila.addStretch(1)
        self.zv.addLayout(fila)

        botones = QHBoxLayout()
        botones.setSpacing(12)
        botones.addStretch(1)
        self.bt_guardar = QPushButton("  Guardar imagen")
        self.bt_guardar.setObjectName("principal")
        self.bt_guardar.setIcon(iconos.icono("descargar", 16, C["acento_texto"]))
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.clicked.connect(self.guardar_imagen)
        botones.addWidget(self.bt_guardar)
        self.bt_top = QPushButton("  Escuchar tu top")
        self.bt_top.setObjectName("contorno")
        self.bt_top.setIcon(iconos.icono("reproducir", 16, C["texto"]))
        self.bt_top.setCursor(Qt.PointingHandCursor)
        self.bt_top.clicked.connect(self._escuchar_top)
        botones.addWidget(self.bt_top)
        botones.addStretch(1)
        self.zv.addLayout(botones)
        self.cuerpo.addWidget(self.zona)

        self.vacio = SinResultados(
            "musica", "Aún no hay nada que resumir",
            "Escucha música un rato y aquí verás tus minutos, tus canciones y artistas "
            "favoritos, tus horas y tu racha.")
        self.cuerpo.addWidget(self.vacio)
        if self._cargando:
            from ..componentes import Esqueleto
            self.esqueleto = Esqueleto("tarjetas")
            self.cuerpo.addWidget(self.esqueleto)
        self.cuerpo.addStretch(1)
        self.elegir(self.periodo)

    def elegir(self, periodo):
        self.periodo = periodo
        for k, c in self.chips.items():
            c.setChecked(k == periodo)
        if self._cargando:
            self.zona.setVisible(False)
            self.vacio.setVisible(False)
            return
        # el de la primera carga ya viene hecho del segundo plano (solo vale la primera vez:
        # después se recalcula, por si sonó algo mientras tanto)
        self.r = self._resumenes.pop(periodo, None) or mx.calcular_resumen(self.historial, periodo)
        d = self.r["desde"]
        self.et_rango.setText(f"{self.r['rango'].capitalize()} · desde el {d.day} de "
                              f"{mx.MESES[d.month - 1]}")
        hay = not self.r["vacio"]
        self.zona.setVisible(hay)
        self.vacio.setVisible(not hay)
        if hay:
            self.escenario.set_resumen(self.r)
            self.escenario.setFocus()
        self._flechas(0)

    def _flechas(self, i):
        n = len(self.escenario.tipos)
        self.bt_izq.setEnabled(i > 0)
        self.bt_der.setEnabled(i < n - 1)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Left, Qt.Key_Right):
            self.escenario.keyPressEvent(e)
        else:
            super().keyPressEvent(e)

    def nombre_archivo(self):
        tipo = self.escenario.tipos[self.escenario.i] if self.escenario.tipos else "resumen"
        return f"Caudal - {self.r['etiqueta']} - {NOMBRES.get(tipo, tipo)}.png"

    def guardar_imagen(self):
        if not self.escenario.tipos:
            return
        carpeta = (QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
                   or os.path.expanduser("~"))
        ruta, _f = QFileDialog.getSaveFileName(self, "Guardar imagen",
                                               os.path.join(carpeta, self.nombre_archivo()),
                                               "Imagen PNG (*.png)")
        if not ruta:
            return
        if not ruta.lower().endswith(".png"):
            ruta += ".png"
        if self.escenario.exportar(ruta):
            self.ctx.avisar(f"Imagen guardada: {os.path.basename(ruta)}")
        else:
            self.ctx.avisar("No se pudo guardar la imagen")

    def _escuchar_top(self):
        r = self.r
        pistas = [c["pista"] for c in r["top_canciones"]]
        # el top 5 y, detras, el resto de lo que mas sonaba en el periodo
        vistas = {p.get("clave") for p in pistas}
        for e in reversed(self.historial):
            if e["fecha"] < r["desde"] or len(pistas) >= 50:
                continue
            if e["pista"].get("clave") not in vistas:
                vistas.add(e["pista"].get("clave"))
                pistas.append(e["pista"])
        if pistas:
            self.ctx.reproducir_lista(pistas, 0, {"tipo": "resumen", "id": self.periodo,
                                                  "titulo": f"Tu top de {r['nombre'][3:]}"})

