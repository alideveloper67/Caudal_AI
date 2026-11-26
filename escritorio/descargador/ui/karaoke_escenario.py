# -*- coding: utf-8 -*-
"""El escenario del karaoke: el verso que toca, enorme, palabra por palabra, con la bola que marca la voz, luces que
se mueven con la música, cuenta atrás antes de entrar y, con el micrófono, el puntaje.

Los datos (letra, tiempos, sincronía, traducción) son los de `karaoke.LienzoKaraoke`; aquí cambia cómo se ve. Con
`modo = "lista"` se ve la letra entera, como antes.

Cómo va fluido sin tarjeta gráfica: cada verso se pinta UNA vez (apagado y encendido) en dos imágenes; en cada cuadro
solo se copian los trozos de cada palabra. Las luces y el viñeteado también están pintados de antemano.
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF, QRadialGradient)

from ..karaoke_audio import Microfono, Puntaje
from . import tipografia_letra
from .componentes import a_la_vista
from .epica.base import alfa, claro, lim, out_back, out_cubic, vivo
from .escena.letra import repartir_palabras
from .karaoke import LienzoKaraoke
from .letra_viva import FPS_DORMIDO, FPS_QUIETO, FPS_SONANDO, partir
from .vista_grande import ahorrando

ENTRADA_S = 0.34                # lo que tarda un verso en subir a su sitio
SALIDA_S = 0.30
AVISO_S = 1.1                   # «¡Perfecto!»
RESULTADO_S = 9.0
CUENTA_S = 3.0                  # 3, 2, 1 antes de entrar
HUECO_CUENTA_S = 3.6            # silencio mínimo para que haya cuenta atrás
LUCES = 5
VERSOS_GUARDADOS = 6


class _Verso:
    """Un verso pintado: dos imágenes (apagado y encendido) y dónde está cada palabra."""
    __slots__ = ("apagado", "encendido", "halo", "palabras", "w", "h", "margen", "filas")


class LienzoEscenario(LienzoKaraoke):

    def __init__(self, ctx, colores, padre=None, modo="escenario"):
        self.modo = modo
        self._versos = {}
        self._luces_px = {}
        self._luz_hecha_en = -1
        self._n_cuadro = 0
        self._vineta = None
        self._haciendo = None                 # [clave, pasos, verso] que se está pintando a trozos
        self._margenes = None                 # (arriba, abajo) que se ven ahora: van suaves a los de los mandos
        self.mandos_a_la_vista = True
        self._anterior = -1
        self._t_cambio = 0.0
        self._avisos = []                     # [(texto, puntos, cuándo)]
        self._ultimo_oir = 0.0
        self._resultado = None                # (estrellas, puntos, porcentaje, cuándo)
        self._energia = 0.0
        self._golpe = 0.0
        self.micro = Microfono()
        self.puntaje = Puntaje()
        super().__init__(ctx, colores, padre=padre)

    # ------------------------------------------------------------ qué se ve

    def en_escenario(self):
        """Sin tiempos no hay escenario que valga: se ve la letra entera."""
        return self.modo == "escenario" and (not self.lineas or self.sincronizada)

    def poner_modo(self, modo):
        self.modo = modo if modo in ("escenario", "lista") else "escenario"
        self._ancho_hecho = -1
        self._t_cambio = time.monotonic()
        self._despertar()
        self.update()

    def _olvidar_dibujos(self):
        self._versos = {}
        self._haciendo = None
        self._luces_px = {}

    def al_cambiar_tipografia(self):
        self._olvidar_dibujos()
        super().al_cambiar_tipografia()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._versos = {}
        self._haciendo = None
        self._vineta = None

    def _poner_lineas(self, lineas, sincronizada, mensaje, esperando=False):
        self._versos = {}
        self._haciendo = None
        self._anterior = -1
        super()._poner_lineas(lineas, sincronizada, mensaje, esperando)

    def _pista(self, p):
        # canción nueva con el micrófono encendido: cómo te fue en la que acaba
        self._terminar_puntaje()
        super()._pista(p)

    # ------------------------------------------------------------ micrófono y puntaje

    def poner_micro(self, si):
        if si:
            self.puntaje.empezar()
            self._avisos = []
            self._resultado = None
            self.micro.encender()
        else:
            self.micro.apagar()
        self._despertar()
        self.update()

    def _terminar_puntaje(self):
        if self.micro.encendido and self.puntaje.versos >= 4:
            self._resultado = (self.puntaje.estrellas(), self.puntaje.puntos, self.puntaje.porcentaje(),
                               time.monotonic())
        self.puntaje.empezar()

    def _oir(self, ahora):
        if not self.micro.encendido:
            self._ultimo_oir = 0.0
            return
        dt = min(0.2, ahora - self._ultimo_oir) if self._ultimo_oir else 0.0
        self._ultimo_oir = ahora
        if getattr(self.ctx.reproductor, "estado", "") != "sonando" or dt <= 0:
            return
        k, toca = None, False
        if self._hay_verso(self._actual):
            p = self._progreso(self._actual, self.ahora_ms())
            k, toca = self._actual, 0.0 < p < 1.0
        r = self.puntaje.oir(self.micro.nivel_ahora, k, toca, dt)
        if r and r[0]:
            self._avisos = self._avisos[-2:] + [(r[0], r[1], ahora)]

    # ------------------------------------------------------------ tiempo

    def _hay_verso(self, k):
        return 0 <= k < len(self.lineas) and not self.lineas[k]["pausa"] and bool(self.lineas[k]["texto"])

    def _siguiente(self, k):
        for j in range(max(0, k + 1), len(self.lineas)):
            if self._hay_verso(j):
                return j
        return -1

    def falta_para_cantar(self):
        """Segundos hasta el próximo verso si ahora hay silencio, o None."""
        k = self._actual
        ms = self.ahora_ms() + self._adelanto()
        if self._hay_verso(k):
            return None
        j = self._siguiente(k)
        return max(0.0, (self.lineas[j]["ms"] - ms) / 1000.0) if j >= 0 else None

    def _hueco_antes(self, j):
        """Cuánto silencio hay antes del verso `j` (s)."""
        fin = 0.0
        for i in range(j - 1, -1, -1):
            if self._hay_verso(i):
                fin = self.lineas[i]["ms"] + (self.lineas[i].get("canto") or 1500)
                break
        return (self.lineas[j]["ms"] - fin) / 1000.0

    def _cuadro(self):
        if not self.en_escenario():
            super()._cuadro()
            return
        ahora = time.monotonic()
        if ahorrando(self.ctx) or not a_la_vista(self):
            self._ultimo_cuadro = ahora
            if self.reloj.interval() != FPS_DORMIDO:
                self.reloj.start(FPS_DORMIDO)
            return
        dt = min(0.1, ahora - self._ultimo_cuadro)
        self._ultimo_cuadro = ahora
        if self.lineas and self.sincronizada:
            i = self._indice(self.ahora_ms())
            if i != self._actual:
                self._anterior, self._actual = self._actual, i
                self._t_cambio = ahora
                if self._hay_verso(i):
                    self._pulso = 1.0
        self._pulso = max(0.0, self._pulso - dt * 1.8)
        meta = (self.margen_arriba, self.margen_abajo) if self.mandos_a_la_vista else (18, 34)
        if self._margenes is None:
            self._margenes = meta
        u = 1.0 - math.exp(-dt * 7.0)
        self._margenes = tuple(x + (y - x) * u for x, y in zip(self._margenes, meta))
        self._oir_musica(dt)
        self._oir(ahora)
        if self.lineas and self.sincronizada and ahora - self._t_cambio > ENTRADA_S:
            self._adelantar_versos()
        sonando = getattr(self.ctx.reproductor, "estado", "") == "sonando"
        vivo_ = sonando or ahora - self._t_cambio < 0.6 or self._avisos or self._resultado
        ms = FPS_SONANDO if vivo_ else FPS_QUIETO
        if self.reloj.interval() != ms:
            self.reloj.start(ms)
        self.update()

    def _oir_musica(self, dt):
        """El nivel real de lo que suena mueve las luces."""
        f = getattr(self.ctx.reproductor, "nivel_audio", None)
        n = None
        if f is not None:
            try:
                n = f()
            except Exception:  # noqa: BLE001
                n = None
        meta = lim((n[0] + 34.0) / 26.0) if n else 0.35 + 0.15 * math.sin(time.monotonic() * 2.1)
        self._golpe = max(self._golpe - dt * 3.2, lim((meta - self._energia) * 4.0))
        self._energia += (meta - self._energia) * min(1.0, dt * 5.0)

    # ------------------------------------------------------------ verso pintado

    def _tam_verso(self):
        return max(34.0, min(118.0, self.width() / 12.0, self.height() / 6.2))

    def _fuente_de(self, tam):
        f = QFont("Segoe UI")
        f.setPixelSize(int(tam))
        f.setWeight(QFont.Black)
        f.setLetterSpacing(QFont.PercentageSpacing, 98)
        return tipografia_letra.adaptar(f)

    def _colores_verso(self):
        c = self._colores_letra()
        return vivo(c.a), vivo(c.b)

    def _clave_verso(self, k):
        a, b = self._colores_verso()
        return (k, self.width(), self.height(), a.rgb(), b.rgb(), self.devicePixelRatioF() or 1.0)

    def _verso(self, k):
        """El verso pintado; si aún no estaba (o estaba a medias), se termina ahora."""
        clave = self._clave_verso(k)
        v = self._versos.get(clave)
        if v is None:
            hecho = self._haciendo
            pasos = hecho[1] if hecho is not None and hecho[0] == clave else self._pasos_verso(k)
            for v in pasos:
                pass
            if hecho is not None and hecho[0] == clave:
                self._haciendo = None
            v = v if v is not None else hecho[2]
            self._guardar_verso(clave, v)
        return v

    def _guardar_verso(self, clave, v):
        self._versos[clave] = v
        while len(self._versos) > VERSOS_GUARDADOS:
            self._versos.pop(next(iter(self._versos)))

    def _adelantar_versos(self):
        """Los dos siguientes se van pintando a trozos (un paso por cuadro): al entrar ya están hechos."""
        if self._haciendo is None:
            k = self._actual
            for _ in range(2):
                k = self._siguiente(k)
                if k < 0:
                    return
                clave = self._clave_verso(k)
                if clave not in self._versos:
                    self._haciendo = [clave, self._pasos_verso(k), None]
                    break
            else:
                return
        hecho = self._haciendo
        try:
            hecho[2] = next(hecho[1])
        except StopIteration:
            self._haciendo = None
            if hecho[2] is not None and hecho[0] == self._clave_verso(hecho[0][0]):
                self._guardar_verso(hecho[0], hecho[2])

    def _pasos_verso(self, k):
        """Pinta un verso en cuatro pasos (cada `yield`, un cuadro)."""
        a, b = self._colores_verso()
        dpr = self.devicePixelRatioF() or 1.0
        texto = self.lineas[k]["texto"]
        ancho = max(160.0, self.width() * 0.88)
        tam = self._tam_verso()
        while True:
            f = self._fuente_de(tam)
            fm = QFontMetricsF(f)
            filas = partir(texto, fm, ancho)
            if tam <= 30 or (len(filas) <= 2 and max(fm.horizontalAdvance(x) for x in filas) <= ancho):
                break
            tam *= 0.93
        v = _Verso()
        v.margen = m = math.ceil(tam * 0.34)
        paso = fm.height() * 1.13
        anchos = [fm.horizontalAdvance(x) for x in filas]
        v.w = math.ceil(max(anchos) + 2 * m)
        v.h = math.ceil(paso * len(filas) + 2 * m)
        v.filas = len(filas)
        tiempos = repartir_palabras(texto, self.lineas[k]["ms"], self.lineas[k].get("canto"))
        fin = self.lineas[k]["ms"] + (self.lineas[k].get("canto") or 1500)
        v.palabras = []
        ruta = QPainterPath()
        ruta.setFillRule(Qt.WindingFill)
        aire = fm.horizontalAdvance(" ") / 2.0
        sobra = fm.height() * 0.05
        n = 0
        for j, fila in enumerate(filas):
            x0 = (v.w - anchos[j]) / 2.0
            y = m + j * paso
            ruta.addText(QPointF(x0, y + fm.ascent()), f, fila)
            x = x0
            for w in fila.split():
                pos = x - x0
                aw = fm.horizontalAdvance(w)
                t0 = tiempos[n][1] if n < len(tiempos) else fin
                t1 = tiempos[n + 1][1] if n + 1 < len(tiempos) else fin
                # cada fila se queda con su franja: la de abajo no tapa los rabos (g, q) de la de arriba
                arriba = 0.0 if j == 0 else y - sobra
                abajo = float(v.h) if j + 1 == len(filas) else y + paso - sobra
                v.palabras.append((QRectF(x0 + pos - aire, arriba, aw + 2 * aire, abajo - arriba), t0,
                                   max(t0 + 60, t1), j))
                x += aw + fm.horizontalAdvance(" ")
                n += 1

        yield v

        def lienzo():
            pm = QPixmap(max(1, int(v.w * dpr)), max(1, int(v.h * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            q.setRenderHint(QPainter.Antialiasing)
            return pm, q
        borde = QPen(QColor(6, 7, 14, 215), tam * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        v.apagado, q = lienzo()
        q.strokePath(ruta, borde)
        q.fillPath(ruta, QColor(255, 255, 255, 236))
        q.end()
        yield v
        v.encendido, q = lienzo()
        q.strokePath(ruta, QPen(QColor(255, 255, 255, 245), tam * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        g = QLinearGradient(0, m, 0, v.h - m)
        g.setColorAt(0.0, claro(a, 0.12))
        g.setColorAt(1.0, claro(b, 0.10))
        q.fillPath(ruta, QBrush(g))
        q.end()
        yield v
        # el brillo de detrás, a un cuarto de tamaño (al estirarlo queda difuminado gratis)
        esc = 0.25
        v.halo = QPixmap(max(1, int(v.w * esc)), max(1, int(v.h * esc)))
        v.halo.fill(Qt.transparent)
        q = QPainter(v.halo)
        q.setRenderHint(QPainter.Antialiasing)
        q.scale(esc, esc)
        for grosor, al in ((0.60, 20), (0.42, 30), (0.24, 46)):
            q.strokePath(ruta, QPen(alfa(a, al), tam * grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        q.end()
        yield v

    # ------------------------------------------------------------ pintura

    def paintEvent(self, e):
        if not self.en_escenario():
            super().paintEvent(e)
            return
        ahora = time.monotonic()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        p.drawImage(QRectF(0, 0, w, h), self._fondo())
        self._pintar_luces(p, w, h, ahora)
        p.setRenderHint(QPainter.TextAntialiasing)
        if not self.lineas:
            self._pintar_mensaje(p)
            p.end()
            return
        arriba, abajo = self._margenes or (self.margen_arriba, self.margen_abajo)
        alto = h - arriba - abajo
        cy = arriba + alto * 0.36
        t = ahora - self._t_cambio
        k = self._actual
        traduccion = self._traduccion(k)
        fin = cy + self._tam_verso() * 1.3                      # dónde acaba lo de ahora
        if self._hay_verso(self._anterior) and t < SALIDA_S:
            u = out_cubic(t / SALIDA_S)
            self._poner_verso(p, self._anterior, cy - u * alto * 0.20,
                              self._cabe(self._anterior, alto) * (1.0 - 0.16 * u), 1.0 - u, None)
        if self._hay_verso(k):
            u = lim(t / ENTRADA_S)
            s = self._cabe(k, alto)
            v = self._verso(k)
            fin = cy + (v.h / 2.0 - v.margen * 0.5) * s + (self._tam_verso() * 0.62 if traduccion else 0.0)
            y = cy + (1 - out_cubic(u)) * alto * 0.30
            self._poner_verso(p, k, y, s * (0.62 + 0.38 * out_back(u, 1.2)) * (1 + 0.012 * self._golpe), lim(u * 2.2),
                              self.ahora_ms() + self._adelanto(), traduccion)
        else:
            self._pintar_espera(p, w, cy, alto, ahora)
        j = self._siguiente(k)
        if j >= 0:
            v = self._verso(j)
            entra = lim(t / 0.4)
            sitio = max(40.0, arriba + alto - fin)              # el siguiente se queda debajo, sin encimarse
            s = min(0.52, (w * 0.72) / v.w, sitio / max(1.0, v.h - v.margen))
            p.setOpacity(0.62 * entra)
            y = fin + min(sitio * 0.5, v.h * s * 0.5 + alto * 0.07) + (1 - out_cubic(entra)) * 26
            p.drawPixmap(QRectF(w / 2 - v.w * s / 2, y - v.h * s / 2, v.w * s, v.h * s), v.apagado,
                         QRectF(v.apagado.rect()))
            p.setOpacity(1.0)
        self._pintar_puntaje(p, w, h, arriba, alto, ahora)
        self._pintar_fuente(p)
        p.end()

    def _cabe(self, k, alto):
        """Con los mandos a la vista hay menos alto: el verso encoge lo justo."""
        v = self._verso(k)
        return min(1.0, alto * 0.62 / max(1.0, v.h - v.margen))

    def _traduccion(self, k):
        return self.traducciones[k] if 0 <= k < len(self.traducciones) else ""

    def _poner_verso(self, p, k, cy, escala, opacidad, ms, traduccion=""):
        """`ms` None: entero encendido (el que se va)."""
        v = self._verso(k)
        dpr = v.apagado.devicePixelRatio()
        p.save()
        p.translate(self.width() / 2.0, cy)
        p.scale(escala, escala)
        p.translate(-v.w / 2.0, -v.h / 2.0)
        p.setOpacity(opacidad * (0.50 + 0.40 * self._energia + 0.30 * self._golpe))
        p.drawPixmap(QRectF(0, 0, v.w, v.h), v.halo, QRectF(v.halo.rect()))
        p.setOpacity(opacidad)

        def copiar(pm, r):
            p.drawPixmap(r, pm, QRectF(r.x() * dpr, r.y() * dpr, r.width() * dpr, r.height() * dpr))
        bola = None
        for n, (r, t0, t1, fila) in enumerate(v.palabras):
            u = 1.0 if ms is None else lim((ms - t0) / (t1 - t0))
            if u <= 0.0:
                copiar(v.apagado, r)
                if bola is None and n == 0 and ms is not None:
                    bola = (r, None, lim(1 + (ms - t0) / 450.0))
                continue
            cantando = ms is not None and u < 1.0
            if cantando:
                # la palabra que suena: crece un poco y se va llenando
                z = 1.0 + 0.07 * math.sin(math.pi * min(1.0, u * 1.15))
                p.save()
                p.translate(r.center())
                p.scale(z, z)
                p.translate(-r.center())
                copiar(v.apagado, r)
                copiar(v.encendido, QRectF(r.x(), r.y(), r.width() * u, r.height()))
                p.restore()
                bola = (r, v.palabras[n - 1][0] if n and v.palabras[n - 1][3] == fila else None, u)
            else:
                copiar(v.encendido, r)
        if bola is not None:
            self._pintar_bola(p, v, *bola)
        p.restore()
        if traduccion:
            f = QFont("Segoe UI")
            f.setPixelSize(int(max(16, self._tam_verso() * 0.28)))
            f.setWeight(QFont.DemiBold)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255, 205))
            p.setOpacity(opacidad)
            y = cy + v.h * escala / 2 - v.margen * 0.4
            p.drawText(QRectF(self.width() * 0.08, y, self.width() * 0.84, f.pixelSize() * 2.6),
                       Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, traduccion)
            p.setOpacity(1.0)

    def _pintar_bola(self, p, v, r, antes, u):
        """La bola que salta de palabra en palabra."""
        x1 = r.center().x()
        x0 = antes.center().x() if antes is not None else r.left()
        v_ = lim(u * 2.2)                                   # llega pronto y bota en el sitio
        x = x0 + (x1 - x0) * v_ if antes is not None else x1
        alto = v.margen * 0.95
        bote = math.sin(math.pi * v_) * alto if v_ < 1 else abs(math.sin(math.pi * (u - 0.4545) * 1.9)) * alto * 0.25
        radio = v.margen * 0.24
        y = r.top() + v.margen * 0.46 - bote
        g = QRadialGradient(QPointF(x - radio * 0.3, y - radio * 0.35), radio * 1.3)
        g.setColorAt(0.0, QColor(255, 255, 255))
        g.setColorAt(1.0, self._colores_verso()[0])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawEllipse(QPointF(x, y + radio * 0.25), radio * 1.12, radio * 1.12)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(x, y), radio, radio)

    def _pintar_espera(self, p, w, cy, alto, ahora):
        """Silencio: cuánto falta, y 3-2-1 antes de entrar."""
        falta = self.falta_para_cantar()
        tam = self._tam_verso()
        if falta is None:
            p.setFont(self._fuente_de(tam * 0.6))
            p.setPen(QColor(255, 255, 255, 210))
            p.drawText(QRectF(0, cy - tam, w, tam * 2), Qt.AlignCenter, "♪")
            return
        a, b = self._colores_verso()
        centro = QPointF(w / 2.0, cy)
        if falta <= CUENTA_S and self._hueco_antes(self._siguiente(self._actual)) >= HUECO_CUENTA_S:
            n = max(1, math.ceil(falta))
            u = 1.0 - (falta - (n - 1))                      # 0 al aparecer el número, 1 al irse
            z = 1.0 + 0.55 * (1 - out_cubic(lim(u * 2.4)))
            p.save()
            p.translate(centro)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(255, 255, 255, 46), tam * 0.10))
            p.drawEllipse(QPointF(0, 0), tam * 1.05, tam * 1.05)
            p.setPen(QPen(a, tam * 0.10, Qt.SolidLine, Qt.RoundCap))
            d = tam * 1.05
            p.drawArc(QRectF(-d, -d, 2 * d, 2 * d), 90 * 16, int(-360 * 16 * falta / CUENTA_S))
            p.scale(z, z)
            p.setOpacity(lim(1.25 - u * 0.6))
            f = self._fuente_de(tam * 1.15)
            ruta = QPainterPath()
            fm = QFontMetricsF(f)
            s = str(n)
            caja = fm.tightBoundingRect(s)
            ruta.addText(QPointF(-caja.center().x(), -caja.center().y()), f, s)
            p.strokePath(ruta, QPen(QColor(6, 7, 14, 200), tam * 0.12, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.fillPath(ruta, QColor(255, 255, 255))
            p.restore()
            return
        f = QFont("Segoe UI")
        f.setPixelSize(int(max(18, tam * 0.36)))
        f.setWeight(QFont.Bold)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 225))
        texto = f"Entras en {math.ceil(falta)} s" if self._actual <= 0 else f"Instrumental · vuelves en {math.ceil(falta)} s"
        p.drawText(QRectF(0, cy - tam * 0.2, w, tam * 0.9), Qt.AlignCenter, texto)
        # tres notas que respiran encima
        f.setPixelSize(int(tam * 0.62))
        p.setFont(f)
        for i, s in enumerate(("♪", "♫", "♪")):
            y = cy - tam * 0.75 + math.sin(ahora * 2.4 + i * 1.1) * tam * 0.12
            p.setPen(claro(a if i != 1 else b, 0.25))
            p.drawText(QRectF(w / 2 + (i - 1) * tam * 0.95 - tam / 2, y - tam * 0.5, tam, tam), Qt.AlignCenter, s)

    # ------------------------------------------------------------ luces

    def _luz(self, color, largo):
        clave = (color.rgb(), int(largo))
        pm = self._luces_px.get(clave)
        if pm is None:
            if self._luz_hecha_en == self._n_cuadro:
                return None                   # una luz nueva por cuadro: al abrir no se paran todas a la vez
            self._luz_hecha_en = self._n_cuadro
            an, al = max(8, int(largo * 0.30)), max(8, int(largo * 0.5))      # a media resolución: es luz
            pm = QPixmap(an, al)
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            q.setRenderHint(QPainter.Antialiasing)
            for parte, al_ in ((1.0, 34), (0.66, 40), (0.34, 52)):
                g = QLinearGradient(0, 0, 0, al)
                g.setColorAt(0.0, alfa(claro(color, 0.35), al_ * 2.1))
                g.setColorAt(0.35, alfa(color, al_))
                g.setColorAt(1.0, alfa(color, 0))
                q.setPen(Qt.NoPen)
                q.setBrush(QBrush(g))
                q.drawPolygon(QPolygonF([QPointF(an * 0.47, 0), QPointF(an * 0.53, 0),
                                         QPointF(an * (0.5 + 0.5 * parte), al), QPointF(an * (0.5 - 0.5 * parte), al)]))
            q.end()
            if len(self._luces_px) > 12:
                self._luces_px = {}
            self._luces_px[clave] = pm
        return pm

    def _pintar_luces(self, p, w, h, ahora):
        a, b = self._colores_verso()
        t = ahora - self._t0
        largo = h * 1.25
        self._n_cuadro += 1
        for i in range(LUCES):
            pm = self._luz(a if i % 2 == 0 else b, largo)
            if pm is None:
                continue
            x = w * (0.08 + 0.84 * i / (LUCES - 1))
            giro = 24 * math.sin(t * (0.42 + 0.07 * i) + i * 1.7) + (0.5 - i / (LUCES - 1)) * 22
            p.save()
            p.translate(x, -h * 0.06)
            p.rotate(giro)
            p.setOpacity(lim(0.26 + 0.50 * self._energia + 0.45 * self._golpe * (0.6 + 0.4 * math.sin(i * 2.3 + t))))
            an = pm.width() * 2.0
            p.drawPixmap(QRectF(-an / 2, 0, an, largo), pm, QRectF(pm.rect()))
            p.restore()
        # motas de luz que suben
        p.setPen(Qt.NoPen)
        for i in range(22):
            vida = (t * (0.035 + 0.012 * (i % 5)) + i * 0.137) % 1.0
            x = (0.5 + 0.5 * math.sin(i * 12.9898 + vida * 1.7)) * w
            y = h * (1.02 - vida * 1.05)
            r = 1.2 + (i % 4) * 0.9
            p.setOpacity(math.sin(math.pi * vida) * (0.22 + 0.5 * self._energia))
            p.setBrush(QColor(255, 255, 255) if i % 3 else a)
            p.drawEllipse(QPointF(x, y), r, r)
        p.setOpacity(1.0)
        if self._vineta is None or self._vineta.size().width() != max(1, w // 3):
            pm = QPixmap(max(1, w // 3), max(1, h // 3))
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            g = QRadialGradient(QPointF(pm.width() / 2, pm.height() * 0.45), max(pm.width(), pm.height()) * 0.72)
            g.setColorAt(0.0, QColor(0, 0, 0, 70))
            g.setColorAt(0.55, QColor(0, 0, 0, 96))
            g.setColorAt(1.0, QColor(0, 0, 0, 190))
            q.fillRect(pm.rect(), QBrush(g))
            q.end()
            self._vineta = pm
        p.drawPixmap(QRectF(0, 0, w, h), self._vineta, QRectF(self._vineta.rect()))

    # ------------------------------------------------------------ puntaje

    def _pintar_puntaje(self, p, w, h, arriba, alto, ahora):
        a, _b = self._colores_verso()
        if self.micro.encendido:
            # abajo a la izquierda, lejos de la letra
            caja = QRectF(26, h - (self._margenes or (0, self.margen_abajo))[1] - 82, 236, 70)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(8, 9, 16, 165))
            p.drawRoundedRect(caja, 18, 18)
            f = QFont("Segoe UI")
            f.setPixelSize(30)
            f.setWeight(QFont.Black)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255))
            cifra = f"{self.puntaje.puntos}"
            p.drawText(caja.adjusted(18, 4, -14, -20), Qt.AlignLeft | Qt.AlignVCenter, cifra)
            x = QFontMetricsF(f).horizontalAdvance(cifra)
            f.setPixelSize(13)
            f.setWeight(QFont.Bold)
            p.setFont(f)
            p.setPen(QColor(255, 255, 255, 190))
            p.drawText(caja.adjusted(26 + x, 12, -14, -20), Qt.AlignLeft | Qt.AlignVCenter, "puntos")
            if self.puntaje.combo >= 2:
                p.setPen(claro(a, 0.25))
                p.drawText(caja.adjusted(18, 12, -16, -20), Qt.AlignRight | Qt.AlignVCenter, f"racha ×{self.puntaje.combo}")
            barra = QRectF(caja.left() + 18, caja.bottom() - 17, caja.width() - 36, 7)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(barra, 3.5, 3.5)
            nivel = lim(self.micro.nivel_ahora * 9.0)
            p.setBrush(a if self.puntaje.cantando else QColor(255, 255, 255, 130))
            p.drawRoundedRect(QRectF(barra.x(), barra.y(), max(7.0, barra.width() * nivel), barra.height()), 3.5, 3.5)
        elif self.micro.error:
            f = QFont("Segoe UI")
            f.setPixelSize(14)
            p.setFont(f)
            p.setPen(QColor(255, 214, 214))
            p.drawText(QRectF(28, arriba + 8, w - 56, 26), Qt.AlignLeft | Qt.AlignVCenter, self.micro.error)
        self._avisos = [x for x in self._avisos if ahora - x[2] < AVISO_S]
        for texto, puntos, cuando in self._avisos:
            t = ahora - cuando
            u = t / AVISO_S
            tam = self._tam_verso() * 0.52
            f = self._fuente_de(tam)
            ruta = QPainterPath()
            s = f"{texto}  +{puntos}"
            ancho = QFontMetricsF(f).horizontalAdvance(s)
            ruta.addText(QPointF(-ancho / 2, 0), f, s)
            p.save()
            p.translate(w / 2, arriba + alto * 0.10 - u * 26)
            z = 0.6 + 0.4 * out_back(lim(t / 0.25), 2.2)
            p.scale(z, z)
            p.setOpacity(lim((1 - u) * 2.4))
            p.strokePath(ruta, QPen(QColor(6, 7, 14, 210), tam * 0.16, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.fillPath(ruta, QColor("#FFD84A") if puntos >= 100 else claro(a, 0.3))
            p.restore()
        if self._resultado:
            self._pintar_resultado(p, w, h, ahora)

    def _pintar_resultado(self, p, w, h, ahora):
        estrellas, puntos, parte, cuando = self._resultado
        t = ahora - cuando
        if t > RESULTADO_S:
            self._resultado = None
            return
        op = lim(t / 0.3) * lim((RESULTADO_S - t) / 0.6)
        caja = QRectF(w / 2 - 230, h * 0.5 - 130, 460, 236)
        p.setOpacity(op)
        p.setPen(QPen(QColor(255, 255, 255, 46), 1.5))
        p.setBrush(QColor(10, 11, 20, 232))
        p.drawRoundedRect(caja, 26, 26)
        for i in range(5):
            u = out_back(lim((t - 0.25 - i * 0.16) / 0.35), 2.0)
            c = QPointF(caja.center().x() + (i - 2) * 74, caja.top() + 66)
            r = 29 * (u if i < estrellas else 1.0)
            pts = QPolygonF([QPointF(c.x() + (r if n % 2 == 0 else r * 0.45) * math.sin(math.pi * n / 5),
                                     c.y() - (r if n % 2 == 0 else r * 0.45) * math.cos(math.pi * n / 5)) for n in range(10)])
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FFD84A") if i < estrellas else QColor(255, 255, 255, 36))
            p.drawPolygon(pts)
        f = QFont("Segoe UI")
        f.setPixelSize(44)
        f.setWeight(QFont.Black)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(caja.x(), caja.top() + 108, caja.width(), 58), Qt.AlignCenter, f"{puntos} puntos")
        f.setPixelSize(16)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 190))
        p.drawText(QRectF(caja.x(), caja.top() + 168, caja.width(), 40), Qt.AlignCenter,
                   f"Cantaste el {parte} % de lo que tocaba")
        p.setOpacity(1.0)

    # ------------------------------------------------------------ ratón

    def mousePressEvent(self, e):
        if not self.en_escenario():
            super().mousePressEvent(e)
        elif self._resultado:
            self._resultado = None
            self.update()

    def wheelEvent(self, e):
        if not self.en_escenario():
            super().wheelEvent(e)

    def mouseMoveEvent(self, e):
        if not self.en_escenario():
            super().mouseMoveEvent(e)
