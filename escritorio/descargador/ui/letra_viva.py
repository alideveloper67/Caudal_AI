# -*- coding: utf-8 -*-
"""La letra que va con la musica.

Un lienzo pintado a mano (60 cuadros por segundo mientras suena):

- el fondo son los colores de la portada, desenfocados y en movimiento lento,
  con un pulso suave cada vez que entra una linea nueva;
- la linea que se canta se ve grande, con brillo, y se va "llenando" de
  izquierda a derecha al ritmo en que se canta (karaoke);
- las demas lineas se desplazan en cascada, como una ola, y se apagan hacia los
  bordes;
- en los tramos instrumentales aparecen tres puntos que respiran y se llenan
  hasta que vuelve la voz;
- un clic en una linea salta a ese momento; la rueda deja mirar arriba/abajo y
  a los pocos segundos vuelve sola a lo que suena.

`LienzoLetra` sirve para el panel lateral (compacto) y para la pagina completa
(`PaginaLetra`), que ademas trae la cabecera y «Guardar imagen» (una tarjeta
vertical lista para historias).
"""

import bisect
import math
import os
import re
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from .. import catalogo, traductor
from ..hilos import en_segundo_plano
from . import iconos, imagenes

# letras ya pedidas (clave de la pista -> datos de catalogo.letras)
CACHE_LETRAS = {}

ADELANTO_MS = 180        # la linea se enciende un pelin antes: se siente a tiempo
FPS_SONANDO = 16         # ms entre cuadros mientras suena (~60 fps)
RADIO = 12               # esquinas de los paneles de Caudal
FPS_QUIETO = 40          # en pausa solo se mueve el fondo, mas despacio


# ------------------------------------------------------------------ colores

def paleta_de(img):
    """Tres colores vivos de la portada (o unos de reserva)."""
    reserva = [QColor("#6D28D9"), QColor("#DB2777"), QColor("#0EA5E9")]
    if img is None or img.isNull():
        return reserva
    peq = img.scaled(12, 12, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    colores = []
    for x in range(peq.width()):
        for y in range(peq.height()):
            colores.append(QColor(peq.pixel(x, y)))
    # se ordenan por "viveza" y se toman tonos distintos entre si
    colores.sort(key=lambda c: c.hsvSaturationF() * 0.7 + c.valueF() * 0.3, reverse=True)
    elegidos = []
    for c in colores:
        h = c.hsvHueF()
        if all(abs(h - e.hsvHueF()) > 0.08 or h < 0 for e in elegidos):
            elegidos.append(c)
        if len(elegidos) == 3:
            break
    while len(elegidos) < 3:
        base = elegidos[0] if elegidos else reserva[0]
        h, s, v, _a = base.getHsvF()
        elegidos.append(QColor.fromHsvF(((h if h >= 0 else 0.75) + 0.12 * len(elegidos)) % 1.0,
                                        max(0.5, s), max(0.6, v)))
    salida = []
    for c in elegidos:
        h, s, v, _a = c.getHsvF()
        # vivos pero no chillones; nunca grises
        salida.append(QColor.fromHsvF(h if h >= 0 else 0.75, min(0.92, max(0.55, s * 1.25)),
                                      min(0.95, max(0.55, v))))
    return salida


def _mezcla(a, b, t):
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def pintar_fondo(p, ancho, alto, paleta, desenfoque, t, pulso):
    """El fondo vivo en un QPainter de `ancho`x`alto` (se pinta pequeno y se
    estira: asi sale desenfocado y cuesta poco)."""
    c1, c2, c3 = paleta
    base = QColor.fromHsvF(max(0.0, c1.hsvHueF()), min(1.0, c1.hsvSaturationF() * 0.9), 0.16)
    p.fillRect(QRectF(0, 0, ancho, alto), base)
    if desenfoque is not None and not desenfoque.isNull():
        p.save()
        p.setOpacity(0.55)
        zoom = 1.25 + 0.06 * math.sin(t * 0.05)
        w, h = ancho * zoom, max(ancho, alto) * zoom
        cx = ancho / 2 + ancho * 0.05 * math.sin(t * 0.031)
        cy = alto / 2 + alto * 0.05 * math.cos(t * 0.027)
        p.translate(cx, cy)
        p.rotate(6 * math.sin(t * 0.02))
        p.drawImage(QRectF(-w / 2, -h / 2, w, h), desenfoque)
        p.restore()
    radio = max(ancho, alto) * (0.62 + 0.05 * pulso)
    p.setPen(Qt.NoPen)
    for k, (c, fase, vel) in enumerate(((c1, 0.0, 0.11), (c2, 2.1, 0.083), (c3, 4.2, 0.067))):
        cx = ancho * (0.5 + 0.38 * math.sin(t * vel + fase))
        cy = alto * (0.5 + 0.34 * math.cos(t * vel * 1.3 + fase * 0.7))
        g = QRadialGradient(QPointF(cx, cy), radio * (0.85 + 0.12 * k))
        centro = QColor(c)
        centro.setAlphaF(min(1.0, 0.62 + 0.25 * pulso))
        medio = QColor(c)
        medio.setAlphaF(0.22)
        fin = QColor(c)
        fin.setAlphaF(0.0)
        g.setColorAt(0.0, centro)
        g.setColorAt(0.45, medio)
        g.setColorAt(1.0, fin)
        p.setBrush(QBrush(g))
        p.drawRect(QRectF(0, 0, ancho, alto))
    # velo oscuro para que el blanco se lea siempre, y vineta
    p.fillRect(QRectF(0, 0, ancho, alto), QColor(0, 0, 0, 92))
    v = QRadialGradient(QPointF(ancho / 2, alto / 2), max(ancho, alto) * 0.75)
    v.setColorAt(0.55, QColor(0, 0, 0, 0))
    v.setColorAt(1.0, QColor(0, 0, 0, 120))
    p.setBrush(QBrush(v))
    p.drawRect(QRectF(0, 0, ancho, alto))


def desenfocar(img):
    """La portada reducida a una mancha suave de color."""
    if img is None or img.isNull():
        return None
    peq = img.scaled(10, 10, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return peq.scaled(80, 80, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


# ------------------------------------------------------------------- lineas

def preparar_lineas(datos):
    """De catalogo.letras a una lista de lineas con su momento de inicio y fin
    estimado del canto, y los silencios largos convertidos en "interludios"."""
    if datos.get("sincronizada") and datos.get("lineas"):
        crudas = [(int(ms), (texto or "").strip()) for ms, texto in datos["lineas"]]
        crudas.sort(key=lambda x: x[0])
        lineas = []
        if crudas and crudas[0][0] > 4500:
            lineas.append({"ms": 0, "texto": "", "pausa": True, "hasta": crudas[0][0]})
        for i, (ms, texto) in enumerate(crudas):
            siguiente = crudas[i + 1][0] if i + 1 < len(crudas) else ms + 6000
            hueco = max(300, siguiente - ms)
            vacia = not texto or texto in ("♪", "♫", "...", "…")
            if vacia:
                if hueco > 3000:
                    lineas.append({"ms": ms, "texto": "", "pausa": True, "hasta": siguiente})
                continue
            # lo que dura cantarla: segun lo larga que es y el tiempo hasta la
            # siguiente (en una balada se estira), sin pasar nunca del hueco
            n = len(texto)
            canto = min(hueco - 150, max(1100, n * 85, min(hueco * 0.6, n * 160)))
            canto = max(300, canto)
            lineas.append({"ms": ms, "texto": texto, "pausa": False, "canto": canto})
            if hueco - canto > 5500:
                lineas.append({"ms": ms + canto + 700, "texto": "", "pausa": True,
                               "hasta": siguiente})
        return lineas, True
    if datos.get("texto"):
        return [{"ms": None, "texto": t.strip(), "pausa": False}
                for t in datos["texto"].split("\n")], False
    return [], False


def partir(texto, fm, ancho):
    """Reparte el texto en filas que caben en `ancho`."""
    palabras = texto.split()
    if not palabras:
        return [""]
    filas, fila = [], ""
    for p in palabras:
        prueba = (fila + " " + p).strip()
        if fila and fm.horizontalAdvance(prueba) > ancho:
            filas.append(fila)
            fila = p
        else:
            fila = prueba
    filas.append(fila)
    return filas


def _suave(actual, objetivo, dt, rapidez):
    """Acercamiento exponencial independiente de los fps."""
    return actual + (objetivo - actual) * (1 - math.exp(-dt * rapidez))


# ------------------------------------------------------------------- lienzo

class LienzoLetra(QWidget):
    """La letra viva. `compacto` para el panel lateral."""

    def __init__(self, ctx, compacto=False, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.compacto = compacto
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)
        self.margen_arriba = 0       # la pagina completa deja sitio a su cabecera
        self.clave = None
        self.pista = None
        self.datos = None
        self.lineas = []
        self.sincronizada = False
        self.traducciones = []
        self.mensaje = "Pon algo a sonar para ver su letra."
        self.esperando = False
        self.paleta = paleta_de(None)
        self.mancha = None
        self.portada = QImage()
        self._fondo_cache = None
        self._items = []             # filas ya repartidas: [{y, alto, filas, tr, ...}]
        self._ancho_hecho = -1
        self._actual = -1
        self._scroll = 0.0
        self._manual = 0.0
        self._ultimo_toque = 0.0
        self._encima = -1
        self._pulso = 0.0
        self._t0 = time.monotonic()
        self._ultimo_cuadro = time.monotonic()
        self._pos_base = 0.0
        self._pos_reloj = time.monotonic()
        self._rutas = {}             # brillo de la linea actual (caminos de texto)

        self.reloj = QTimer(self)
        self.reloj.setTimerType(Qt.PreciseTimer)
        self.reloj.timeout.connect(self._cuadro)

        r = ctx.reproductor
        r.pista_cambio.connect(self._pista)
        r.posicion_cambio.connect(self._posicion)
        r.estado_cambio.connect(lambda _e: self._ritmo())

    # ----------------------------------------------------------- tiempo
    def _posicion(self, seg):
        self._pos_base = float(seg or 0)
        self._pos_reloj = time.monotonic()

    def ahora_ms(self):
        """La posicion de la musica, interpolada entre avisos del motor."""
        r = self.ctx.reproductor
        pos = self._pos_base
        if getattr(r, "estado", "") == "sonando":
            pasado = min(1.0, time.monotonic() - self._pos_reloj)
            pos += pasado * float(getattr(r, "velocidad", 1.0) or 1.0)
        return pos * 1000

    def _ritmo(self):
        if not self.isVisible():
            self.reloj.stop()
            return
        sonando = getattr(self.ctx.reproductor, "estado", "") == "sonando"
        ms = FPS_SONANDO if sonando else FPS_QUIETO
        if not self.reloj.isActive() or self.reloj.interval() != ms:
            self.reloj.start(ms)

    def showEvent(self, e):
        super().showEvent(e)
        r = self.ctx.reproductor
        self._posicion(getattr(r, "_posicion", 0))
        p = r.actual
        if p and (p.get("clave") or p.get("video_id")) != self.clave:
            self._pista(p)
        elif not p and self.clave is not None:
            self._pista(None)
        self._ritmo()

    def hideEvent(self, e):
        super().hideEvent(e)
        self.reloj.stop()

    # ----------------------------------------------------------- datos
    def _pista(self, p):
        if not p:
            self.clave = self.pista = self.datos = None
            self._poner_lineas([], False, "Pon algo a sonar para ver su letra.")
            return
        clave = p.get("clave") or p.get("video_id")
        if not self.isVisible() or clave == self.clave:
            return
        self.clave = clave
        self.pista = p
        self.traducciones = []
        url = p.get("miniatura") or ""
        if url:
            imagenes.imagen(url, lambda img, c=clave: self.clave == c and self._portada(img))
        else:
            self._portada(QImage())
        if clave in CACHE_LETRAS:
            self._llegaron(clave, CACHE_LETRAS[clave])
            return
        self._poner_lineas([], False, "Buscando la letra", esperando=True)
        en_segundo_plano(catalogo.letras, p, ok=lambda d, c=clave: self._llegaron(c, d),
                         error=lambda _e, c=clave: self.clave == c and self._poner_lineas(
                             [], False, "No se pudo conseguir la letra. Revisa tu internet."),
                         dueno=self)

    def _portada(self, img):
        self.portada = img if img is not None else QImage()
        self.paleta = paleta_de(self.portada)
        self.mancha = desenfocar(self.portada)
        self.update()

    def _llegaron(self, clave, datos):
        CACHE_LETRAS[clave] = datos
        if clave != self.clave:
            return
        self.datos = datos
        lineas, sinc = preparar_lineas(datos)
        if not lineas:
            self._poner_lineas([], False, "No hay letra para esta canción.\nA veces aparece "
                                          "buscándola desde el álbum oficial.")
            return
        self._poner_lineas(lineas, sinc, "")
        self.pedir_traduccion()

    def pedir_traduccion(self):
        self.traducciones = []
        self._ancho_hecho = -1
        self.update()
        if not self.ctx.ajustes["traducir_letra"] or not self.lineas:
            return
        clave = self.clave
        textos = [ln["texto"] for ln in self.lineas]

        def llego(t, c=clave):
            if c == self.clave and isinstance(t, list):
                self.traducciones = t
                self._ancho_hecho = -1
                self.update()
        en_segundo_plano(traductor.traducir, clave, textos, ok=llego, dueno=self)

    def _poner_lineas(self, lineas, sincronizada, mensaje, esperando=False):
        self.lineas = lineas
        self.sincronizada = sincronizada
        self.mensaje = mensaje
        self.esperando = esperando
        self._actual = -1
        self._manual = 0.0
        self._ancho_hecho = -1
        self._rutas = {}
        self._items = []
        self._scroll = 0.0
        self.update()

    # ----------------------------------------------------------- medidas
    def _tam(self):
        if self.compacto:
            return 21
        return max(28, min(46, self.width() / 24))

    def _fuentes(self):
        tam = self._tam()
        f = QFont("Segoe UI")
        f.setPixelSize(int(tam))
        f.setWeight(QFont.ExtraBold)
        f.setLetterSpacing(QFont.PercentageSpacing, 98)
        ft = QFont("Segoe UI")
        ft.setPixelSize(int(tam * (0.68 if self.compacto else 0.56)))
        ft.setWeight(QFont.DemiBold)
        return f, ft

    def _margen_x(self):
        return 22 if self.compacto else max(40, self.width() * 0.09)

    def _repartir(self):
        if self._ancho_hecho == self.width() and self._items:
            return
        f, ft = self._fuentes()
        fm, fmt = QFontMetricsF(f), QFontMetricsF(ft)
        ancho = max(120, self.width() - 2 * self._margen_x())
        alto_fila = fm.height() * 1.04
        alto_tr = fmt.height() * 1.1
        hueco = self._tam() * (0.62 if not self.compacto else 0.55)
        y = 0.0
        self._items = []
        for i, ln in enumerate(self.lineas):
            if ln["pausa"]:
                alto = self._tam() * 1.1
                self._items.append({"y": y, "alto": alto, "filas": [], "anchos": [], "tr": []})
                y += alto + hueco
                continue
            filas = partir(ln["texto"], fm, ancho)
            tr_texto = self.traducciones[i] if i < len(self.traducciones) else ""
            tr = partir(tr_texto, fmt, ancho) if tr_texto else []
            alto = len(filas) * alto_fila + (len(tr) * alto_tr + 6 if tr else 0)
            self._items.append({"y": y, "alto": alto, "filas": filas,
                                "anchos": [fm.horizontalAdvance(x) for x in filas],
                                "tr": tr, "yv": None, "foco": 0.0})
            y += alto + hueco
        for it in self._items:
            it.setdefault("yv", None)
            it.setdefault("foco", 0.0)
        self._alto_total = y
        self._alto_fila = alto_fila
        self._alto_tr = alto_tr
        self._ascenso = fm.ascent()
        self._ascenso_tr = fmt.ascent()
        self._ancho_hecho = self.width()
        self._rutas = {}

    def _indice(self, ms):
        if not self.sincronizada or not self.lineas:
            return -1
        tiempos = [ln["ms"] for ln in self.lineas]
        return bisect.bisect_right(tiempos, ms + ADELANTO_MS) - 1

    # ----------------------------------------------------------- animacion
    def _cuadro(self):
        ahora = time.monotonic()
        dt = min(0.1, ahora - self._ultimo_cuadro)
        self._ultimo_cuadro = ahora
        self._pulso = _suave(self._pulso, 0.0, dt, 2.2)
        if self.lineas:
            self._repartir()
            i = self._indice(self.ahora_ms())
            if i != self._actual:
                if i >= 0 and not self.lineas[i]["pausa"]:
                    self._pulso = 1.0
                self._actual = i
            # el desplazamiento sigue a la linea actual (o a la rueda)
            alto_vista = self.height() - self.margen_arriba
            ancla = self.margen_arriba + alto_vista * (0.30 if not self.compacto else 0.28)
            if self.sincronizada and 0 <= self._actual < len(self._items):
                it = self._items[self._actual]
                objetivo = it["y"] + min(it["alto"], self._alto_fila * 2) / 2 - ancla
            elif self.sincronizada:
                objetivo = -ancla + 0
            else:
                objetivo = -self.margen_arriba - 30
            if time.monotonic() - self._ultimo_toque > 3.5:
                self._manual = _suave(self._manual, 0.0, dt, 4.0)
            self._scroll = _suave(self._scroll, objetivo, dt, 7.0)
            for k, it in enumerate(self._items):
                destino = it["y"] - self._scroll - self._manual
                if it["yv"] is None:
                    it["yv"] = destino
                # ola: cuanto mas lejos de la actual, mas tarda en llegar
                d = abs(k - self._actual) if self._actual >= 0 else 0
                it["yv"] = _suave(it["yv"], destino, dt, max(3.2, 9.5 - d * 1.1))
                it["foco"] = _suave(it["foco"], 1.0 if k == self._actual else 0.0, dt, 9.0)
        self.update()

    # ----------------------------------------------------------- pintura
    def _fondo(self):
        """El fondo se pinta a 1/6 de tamano y se estira (desenfoque gratis)."""
        w, h = max(8, self.width() // 6), max(8, self.height() // 6)
        if self._fondo_cache is None or self._fondo_cache.size().width() != w \
                or self._fondo_cache.size().height() != h:
            self._fondo_cache = QImage(w, h, QImage.Format_RGB32)
        img = self._fondo_cache
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        pintar_fondo(p, w, h, self.paleta, self.mancha, time.monotonic() - self._t0, self._pulso)
        p.end()
        return img

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # las esquinas de abajo, redondas como el resto de paneles de Caudal
        borde = QPainterPath()
        borde.addRoundedRect(QRectF(0, -RADIO, self.width(), self.height() + RADIO), RADIO, RADIO)
        p.setClipPath(borde)
        p.drawImage(QRectF(0, 0, self.width(), self.height()), self._fondo())
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        if not self.lineas:
            self._pintar_mensaje(p)
            p.end()
            return
        self._repartir()
        f, ft = self._fuentes()
        x0 = self._margen_x()
        ms = self.ahora_ms()
        alto = self.height()
        arriba = self.margen_arriba
        for k, it in enumerate(self._items):
            y = it["yv"] if it["yv"] is not None else it["y"] - self._scroll
            if y + it["alto"] < arriba - 40 or y > alto + 40:
                continue
            ln = self.lineas[k]
            # apagado hacia los bordes
            borde = 1.0
            zona = alto * 0.14
            if y < arriba + zona:
                # se apaga antes de llegar a la cabecera
                borde = max(0.0, min(1.0, (y - arriba + 8) / zona))
            elif y + it["alto"] > alto - zona:
                borde = max(0.0, (alto - y - it["alto"] + 30) / (zona + 30))
            foco = it["foco"] if self.sincronizada else 1.0
            if ln["pausa"]:
                self._pintar_puntos(p, x0, y, k, ms, foco, borde)
                continue
            base = 0.34 if self.sincronizada else 0.92
            if k == self._encima and self.sincronizada:
                base += 0.18
            opacidad = (base + (1 - base) * foco) * borde
            if opacidad <= 0.01:
                continue
            escala = 0.955 + 0.045 * foco + 0.018 * self._pulso * (1 if k == self._actual else 0)
            p.save()
            p.translate(x0, y + self._alto_fila / 2)
            p.scale(escala, escala)
            p.translate(0, -self._alto_fila / 2)
            p.setOpacity(opacidad)
            p.setFont(f)
            progreso = self._progreso(k, ms)
            if k == self._actual and self.sincronizada:
                self._pintar_brillo(p, k, it, f, foco)
            for n, fila in enumerate(it["filas"]):
                yy = n * self._alto_fila + self._ascenso
                p.setPen(self._pluma(n, it, progreso, k))
                p.drawText(QPointF(0, yy), fila)
            if it["tr"]:
                p.setFont(ft)
                p.setPen(QColor(255, 255, 255, 190 if k == self._actual else 150))
                yy = len(it["filas"]) * self._alto_fila + 6 + self._ascenso_tr
                for fila in it["tr"]:
                    p.drawText(QPointF(0, yy), fila)
                    yy += self._alto_tr
            p.restore()
        self._pintar_fuente(p)
        p.end()

    def _progreso(self, k, ms):
        """Cuanto de la linea k ya se canto (0..1)."""
        if not self.sincronizada:
            return 1.0
        if k < self._actual:
            return 1.0
        if k > self._actual:
            return 0.0
        ln = self.lineas[k]
        canto = ln.get("canto") or 1500
        return max(0.0, min(1.0, (ms + ADELANTO_MS - ln["ms"]) / canto))

    def _pluma(self, n, it, progreso, k):
        """Blanco hasta donde se canto y apagado despues, con borde suave."""
        if not self.sincronizada or k != self._actual:
            return QColor(255, 255, 255)
        total = sum(len(x) for x in it["filas"]) or 1
        hecho = progreso * total
        antes = sum(len(x) for x in it["filas"][:n])
        local = max(0.0, min(1.0, (hecho - antes) / max(1, len(it["filas"][n]))))
        ancho = it["anchos"][n] or 1
        borde = local * ancho
        pluma = 36
        g = QLinearGradient(borde - pluma, 0, borde + pluma, 0)
        g.setColorAt(0.0, QColor(255, 255, 255, 255))
        g.setColorAt(1.0, QColor(255, 255, 255, 105))
        return QPen(QBrush(g), 1)

    def _pintar_brillo(self, p, k, it, f, foco):
        """Un halo suave alrededor de la linea que suena (se pinta una vez por
        linea y luego solo se dibuja la imagen: cuesta casi nada por cuadro)."""
        cache = self._rutas.get(k)
        if cache is None:
            pad = 16
            ancho = int(max(it["anchos"] or [1]) + 2 * pad)
            alto = int(len(it["filas"]) * self._alto_fila + 2 * pad)
            img = QImage(max(1, ancho), max(1, alto), QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.transparent)
            q = QPainter(img)
            q.setRenderHint(QPainter.Antialiasing)
            ruta = QPainterPath()
            for n, fila in enumerate(it["filas"]):
                ruta.addText(QPointF(pad, pad + n * self._alto_fila + self._ascenso), f, fila)
            q.setBrush(Qt.NoBrush)
            for grosor, alfa in ((14, 10), (8, 18), (4, 26)):
                q.setPen(QPen(QColor(255, 255, 255, alfa), grosor, Qt.SolidLine,
                              Qt.RoundCap, Qt.RoundJoin))
                q.drawPath(ruta)
            q.end()
            cache = (img, pad)
            self._rutas = {k: cache}
        img, pad = cache
        intensidad = (0.5 + 0.5 * self._pulso) * foco
        p.save()
        p.setOpacity(p.opacity() * min(1.0, intensidad))
        p.drawImage(QPointF(-pad, -pad), img)
        p.restore()

    def _pintar_puntos(self, p, x0, y, k, ms, foco, borde):
        ln = self.lineas[k]
        if foco < 0.02 and k != self._actual:
            p.save()
            p.setOpacity(0.25 * borde)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255))
            for n in range(3):
                p.drawEllipse(QPointF(x0 + 6 + n * 16, y + self._tam() * 0.5), 3.2, 3.2)
            p.restore()
            return
        inicio, fin = ln["ms"], ln.get("hasta") or ln["ms"] + 4000
        avance = max(0.0, min(1.0, (ms - inicio) / max(1, fin - inicio)))
        respira = 1.0 + 0.16 * math.sin((time.monotonic() - self._t0) * 3.6)
        # al acabar, los puntos se encogen y dan paso a la voz
        salida = max(0.0, min(1.0, (fin - ms) / 450.0))
        r = self._tam() * 0.2 * respira * (0.5 + 0.5 * foco) * salida
        p.save()
        p.setPen(Qt.NoPen)
        for n in range(3):
            lleno = max(0.0, min(1.0, avance * 3 - n))
            p.setOpacity(borde * (0.35 + 0.65 * lleno) * max(foco, 0.3))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(x0 + r + n * r * 3.1, y + self._tam() * 0.55), r, r)
        p.restore()

    def _pintar_mensaje(self, p):
        p.setPen(QColor(255, 255, 255, 225))
        f = QFont("Segoe UI")
        f.setPixelSize(17 if self.compacto else 24)
        f.setWeight(QFont.Bold)
        p.setFont(f)
        texto = self.mensaje
        if self.esperando:
            texto += "." * (1 + int((time.monotonic() - self._t0) * 2.5) % 3)
        caja = QRectF(24, self.margen_arriba, self.width() - 48, self.height() - self.margen_arriba)
        p.drawText(caja, Qt.AlignCenter | Qt.TextWordWrap, texto)

    def _pintar_fuente(self, p):
        if not self.datos or not self.datos.get("fuente"):
            return
        p.setOpacity(0.5)
        f = QFont("Segoe UI")
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        texto = f"Letra de {self.datos['fuente']}"
        if not self.sincronizada:
            texto = "Letra sin sincronizar · " + texto
        p.drawText(QRectF(0, self.height() - 22, self.width() - 14, 18),
                   Qt.AlignRight | Qt.AlignVCenter, texto)
        p.setOpacity(1.0)

    # ----------------------------------------------------------- raton
    def _item_en(self, y):
        for k, it in enumerate(self._items):
            yv = it["yv"] if it["yv"] is not None else it["y"]
            if yv - 6 <= y <= yv + it["alto"] + 6:
                return k
        return -1

    def mouseMoveEvent(self, e):
        k = self._item_en(e.position().y())
        ok = k >= 0 and self.sincronizada and not self.lineas[k]["pausa"]
        self._encima = k if ok else -1
        self.setCursor(Qt.PointingHandCursor if ok else Qt.ArrowCursor)

    def leaveEvent(self, e):
        self._encima = -1
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self.sincronizada:
            return super().mousePressEvent(e)
        k = self._item_en(e.position().y())
        if k >= 0 and self.lineas[k]["ms"] is not None:
            self._ultimo_toque = 0.0
            self._manual = 0.0
            self.ctx.reproductor.buscar(max(0, self.lineas[k]["ms"]) / 1000)
            self._posicion(max(0, self.lineas[k]["ms"]) / 1000)

    def wheelEvent(self, e):
        self._ultimo_toque = time.monotonic()
        self._manual -= e.angleDelta().y() * 0.9
        alto = getattr(self, "_alto_total", 0)
        self._manual = max(-alto, min(alto, self._manual))
        if not self.reloj.isActive():
            self._ritmo()
        e.accept()

    # ----------------------------------------------------------- tarjeta
    def lineas_para_tarjeta(self, cuantas=3):
        """La linea que suena y las siguientes (para compartir)."""
        if not self.lineas:
            return []
        textos = [ln["texto"] for ln in self.lineas if not ln["pausa"] and ln["texto"]]
        if not textos:
            return []
        if self.sincronizada and self._actual >= 0:
            desde = [ln["texto"] for ln in self.lineas[self._actual:]
                     if not ln["pausa"] and ln["texto"]]
            if desde:
                return desde[:cuantas]
        return textos[:cuantas]


def crear_tarjeta(pista, lineas, portada, paleta):
    """Imagen vertical 1080x1920, lista para una historia."""
    W, H = 1080, 1920
    img = QImage(W, H, QImage.Format_RGB32)
    fondo = QImage(W // 6, H // 6, QImage.Format_RGB32)
    p = QPainter(fondo)
    p.setRenderHint(QPainter.Antialiasing)
    pintar_fondo(p, fondo.width(), fondo.height(), paleta, desenfocar(portada), 7.0, 0.3)
    p.end()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.drawImage(QRectF(0, 0, W, H), fondo)
    margen = 96
    # portada con esquinas redondas y sombra
    lado = 560
    caja = QRectF((W - lado) / 2, 250, lado, lado)
    for n in range(14, 0, -2):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 9))
        p.drawRoundedRect(caja.adjusted(-n, -n + 18, n, n + 18), 40 + n, 40 + n)
    if portada is not None and not portada.isNull():
        ruta = QPainterPath()
        ruta.addRoundedRect(caja, 36, 36)
        p.save()
        p.setClipPath(ruta)
        cuadro = min(portada.width(), portada.height())
        origen = QRectF((portada.width() - cuadro) / 2, (portada.height() - cuadro) / 2,
                        cuadro, cuadro)
        p.drawImage(caja, portada, origen)
        p.restore()
    # titulo y artista
    titulo = (pista or {}).get("titulo") or ""
    artista = ", ".join(a.get("nombre", "") for a in (pista or {}).get("artistas") or []) \
        or (pista or {}).get("artista") or ""
    ft = QFont("Segoe UI")
    ft.setPixelSize(44)
    ft.setWeight(QFont.ExtraBold)
    fa = QFont("Segoe UI")
    fa.setPixelSize(34)
    fa.setWeight(QFont.DemiBold)
    p.setPen(QColor(255, 255, 255))
    p.setFont(ft)
    y = caja.bottom() + 90
    fm = QFontMetricsF(ft)
    p.drawText(QRectF(margen, y, W - 2 * margen, 60), Qt.AlignHCenter | Qt.AlignVCenter,
               fm.elidedText(titulo, Qt.ElideRight, W - 2 * margen))
    p.setFont(fa)
    p.setPen(QColor(255, 255, 255, 185))
    p.drawText(QRectF(margen, y + 62, W - 2 * margen, 50), Qt.AlignHCenter | Qt.AlignVCenter,
               QFontMetricsF(fa).elidedText(artista, Qt.ElideRight, W - 2 * margen))
    # la letra: la primera bien encendida, las demas un poco menos
    fl = QFont("Segoe UI")
    fl.setPixelSize(70)
    fl.setWeight(QFont.ExtraBold)
    fml = QFontMetricsF(fl)
    y = y + 200
    p.setFont(fl)
    for n, texto in enumerate(lineas[:3]):
        for fila in partir(texto, fml, W - 2 * margen):
            if y > H - 220:
                break
            if n == 0:
                ruta = QPainterPath()
                ruta.addText(QPointF(margen, y + fml.ascent()), fl, fila)
                for ancho, alfa in ((18, 10), (10, 18)):
                    p.setPen(QPen(QColor(255, 255, 255, alfa), ancho, Qt.SolidLine,
                                  Qt.RoundCap, Qt.RoundJoin))
                    p.setBrush(Qt.NoBrush)
                    p.drawPath(ruta)
            p.setPen(QColor(255, 255, 255, 255 if n == 0 else 150))
            p.drawText(QPointF(margen, y + fml.ascent()), fila)
            y += fml.height() * 1.05
        y += 26
    # firma
    fc = QFont("Segoe UI")
    fc.setPixelSize(30)
    fc.setWeight(QFont.Bold)
    p.setFont(fc)
    p.setPen(QColor(255, 255, 255, 170))
    p.drawPixmap(QRectF(W / 2 - 112, H - 140, 40, 40).toRect(), iconos.icono_app(80))
    p.drawText(QRectF(W / 2 - 62, H - 140, 200, 40), Qt.AlignLeft | Qt.AlignVCenter, "Caudal")
    p.end()
    return img


def carpeta_imagenes():
    base = os.path.join(os.path.expanduser("~"), "Pictures")
    try:
        from PySide6.QtCore import QStandardPaths
        base = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or base
    except Exception:  # noqa: BLE001
        pass
    ruta = os.path.join(base, "Caudal")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _nombre_archivo(texto):
    limpio = re.sub(r'[\\/:*?"<>|]+', "", texto or "").strip()[:70]
    return limpio or "letra"


# --------------------------------------------------------------- pagina

_BOTON = ("QPushButton{border:none;border-radius:14px;padding:6px 14px;font-size:13px;"
          "font-weight:800;color:#FFFFFF;background:rgba(255,255,255,0.16);}"
          "QPushButton:hover{background:rgba(255,255,255,0.26);}"
          "QPushButton:checked{background:#FFFFFF;color:#06070A;}")


class PaginaLetra(QWidget):
    """La letra a pantalla completa, con cabecera y «Guardar imagen»."""
    volver = Signal()
    titulo = "Letra"

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.lienzo = LienzoLetra(ctx, compacto=False, padre=self)
        self.lienzo.margen_arriba = 92
        self.cabecera = QWidget(self)
        self.cabecera.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(self.cabecera)
        h.setContentsMargins(28, 18, 22, 0)
        h.setSpacing(14)
        self.portada = QLabel()
        self.portada.setFixedSize(56, 56)
        h.addWidget(self.portada)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        self.et_titulo = QLabel("")
        self.et_titulo.setStyleSheet("color:#FFFFFF;font-size:17px;font-weight:800;background:transparent;")
        self.et_artista = QLabel("")
        self.et_artista.setStyleSheet("color:rgba(255,255,255,0.72);font-size:13px;"
                                      "font-weight:600;background:transparent;")
        textos.addStretch(1)
        textos.addWidget(self.et_titulo)
        textos.addWidget(self.et_artista)
        textos.addStretch(1)
        h.addLayout(textos, 1)
        self.bt_traducir = QPushButton("Traducir")
        self.bt_traducir.setCheckable(True)
        self.bt_traducir.setChecked(bool(ctx.ajustes["traducir_letra"]))
        self.bt_traducir.setToolTip("Mostrar la traducción bajo cada línea")
        self.bt_traducir.toggled.connect(self._traducir)
        self.bt_imagen = QPushButton("Guardar imagen")
        self.bt_imagen.setToolTip("Una tarjeta vertical con la portada y estas líneas, "
                                  "lista para tus historias (también queda copiada)")
        self.bt_imagen.clicked.connect(self._tarjeta)
        self.bt_volver = QPushButton("Cerrar")
        self.bt_volver.setToolTip("Volver a donde estabas")
        self.bt_volver.clicked.connect(self.volver.emit)
        for b in (self.bt_traducir, self.bt_imagen, self.bt_volver):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(_BOTON)
            h.addWidget(b, 0, Qt.AlignVCenter)
        r = ctx.reproductor
        r.pista_cambio.connect(self._cabecera)
        self._cabecera(r.actual)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.lienzo.setGeometry(0, 0, self.width(), self.height())
        self.cabecera.setGeometry(0, 0, self.width(), 86)
        self.cabecera.raise_()

    def showEvent(self, e):
        super().showEvent(e)
        self._cabecera(self.ctx.reproductor.actual)

    def _cabecera(self, p):
        if not p:
            self.et_titulo.setText("")
            self.et_artista.setText("")
            self.portada.clear()
            return
        self.et_titulo.setText(p.get("titulo") or "")
        artista = ", ".join(a.get("nombre", "") for a in p.get("artistas") or []) \
            or p.get("artista") or ""
        self.et_artista.setText(artista)
        url = p.get("miniatura") or ""
        self.portada.clear()
        if url:
            pm = imagenes.pedir(url, 56, 56, radio=10,
                                callback=lambda pm, u=url: self._poner_portada(u, pm))
            if pm is not None:
                self.portada.setPixmap(pm)

    def _poner_portada(self, url, pm):
        p = self.ctx.reproductor.actual
        if p and (p.get("miniatura") or "") == url:
            self.portada.setPixmap(pm)

    def _traducir(self, on):
        self.ctx.ajustes["traducir_letra"] = bool(on)
        self.ctx.ajustes.guardar()
        self.lienzo.pedir_traduccion()

    def _tarjeta(self):
        lineas = self.lienzo.lineas_para_tarjeta()
        pista = self.ctx.reproductor.actual
        if not lineas or not pista:
            self.ctx.avisar("Primero pon una canción que tenga letra.")
            return
        img = crear_tarjeta(pista, lineas, self.lienzo.portada, self.lienzo.paleta)
        nombre = _nombre_archivo(f"{pista.get('titulo') or 'Letra'} - {lineas[0][:30]}")
        ruta = os.path.join(carpeta_imagenes(), nombre + ".png")
        n = 2
        while os.path.exists(ruta):
            ruta = os.path.join(carpeta_imagenes(), f"{nombre} ({n}).png")
            n += 1
        img.save(ruta, "PNG")
        try:
            QApplication.clipboard().setImage(img)
        except Exception:  # noqa: BLE001
            pass
        self.ctx.avisar("Imagen guardada en Imágenes › Caudal y copiada: pégala donde quieras")
