# -*- coding: utf-8 -*-
"""Letra a pantalla completa con efectos (donadores): solo el verso que se canta, enorme y en el centro.

Parte de lo que ya hay: la letra viva (`letra_viva.LienzoLetra`: letra, tiempos, traducción) y el karaoke
(`karaoke.LienzoKaraoke`: los colores que siguen a la carátula). Aquí cambia cómo se ve:

- el verso actual, grande y centrado; el anterior se va hacia arriba y se apaga; el siguiente espera abajo,
  pequeño;
- cada verso ENTRA con una animación según el estilo elegido:
    · Resplandor: sube y se enciende con un halo de los colores de la carátula;
    · Ola: las palabras entran una a una, con un pequeño rebote;
    · Neón: parpadea como un letrero al encenderse y queda brillando;
    · Cine: aparece letra a letra, con letra de cine y mucho aire;
    · Zoom: llega de golpe, enorme, y se clava en su sitio;
    · Máquina: se escribe tecla a tecla, con su cursor;
    · Lluvia: las letras caen y rebotan;
    · Giro: cada palabra entra girando;
- con el tipo de letra elegido en «Diseño de letra» (la predeterminada deja a cada estilo la suya);
- detrás del verso, un resplandor que respira con los colores de la carátula (y late al entrar cada verso);
- lo ya cantado se tiñe poco a poco (como el karaoke).

Gasta poco: el reloj de la letra viva (60 cuadros por segundo solo mientras algo entra o sale, ~20 entre
versos y casi nada en pausa), sin desenfoques por cuadro (el halo de cada verso se pinta una vez y se guarda),
y en modo gamer con ahorro no anima nada. Sin animaciones del sistema no cambia nada de esto: es una vista
que se abre a propósito.
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QMenu, QPushButton, QWidget

from ..paleta_caratula import colores_de
from ..premium_datos import DETALLE_ESCENA, ESTILOS_ESCENA, NOMBRES_ESCENA, estilo_escena_valido
from . import tipografia_letra
from .componentes import a_la_vista
from .karaoke import LienzoKaraoke
from .letra_viva import FPS_DORMIDO, FPS_SONANDO, partir
from .vista_grande import BOTON, VistaGrande, ahorrando

AJUSTE_ESTILO = "letra_escena_estilo"
# lo que tarda en entrar un verso (s) según el estilo; la salida del anterior es igual para todos
DURACION = {"resplandor": 0.6, "ola": 0.5, "neon": 0.75, "cine": 0.4, "zoom": 0.5, "maquina": 0.03,
            "lluvia": 0.75, "giro": 0.55}
SALIDA = 0.45
PASO_OLA = 0.075        # retraso entre palabras
PASO_CINE_MAX = 0.045   # retraso máximo entre letras (las líneas largas van más deprisa)
CINE_TOTAL = 1.3        # una línea de cine termina de aparecer, como mucho, en este tiempo
PASO_MAQUINA_MAX = 0.055   # segundos entre teclas
MAQUINA_TOTAL = 1.4
PASO_LLUVIA_MAX = 0.035
LLUVIA_TOTAL = 1.5
PASO_GIRO = 0.085
GRADOS_GIRO = 75.0
ESCALA_ZOOM = 2.3
POR_PALABRAS = ("ola", "giro")
POR_LETRAS = ("cine", "maquina", "lluvia")


# ------------------------------------------------------------------ cuentas (sin Qt, se prueban solas)

def _lim(x):
    return max(0.0, min(1.0, x))


def suave(x):
    """Salida cúbica: rápido al principio y se posa despacio."""
    x = _lim(x)
    return 1 - (1 - x) ** 3


def rebote(x):
    """Como `suave` pero se pasa un poquito y vuelve (las palabras de la ola)."""
    x = _lim(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def parpadeo_neon(t):
    """Lo encendido que está un letrero de neón `t` segundos después de darle a la llave (0..1)."""
    tramos = ((0.08, 0.0), (0.14, 0.9), (0.22, 0.15), (0.30, 1.0), (0.36, 0.3), (0.42, 0.85))
    for fin, valor in tramos:
        if t < fin:
            return valor
    return 0.85 + 0.15 * _lim((t - 0.42) / 0.3)


def bote(x):
    """Cae y rebota cada vez menos hasta quedarse quieto (0 arriba, 1 en el suelo)."""
    x = _lim(x)
    n, d = 7.5625, 2.75
    if x < 1 / d:
        return n * x * x
    if x < 2 / d:
        x -= 1.5 / d
        return n * x * x + 0.75
    if x < 2.5 / d:
        x -= 2.25 / d
        return n * x * x + 0.9375
    x -= 2.625 / d
    return n * x * x + 0.984375


def golpe(x):
    """La escala del zoom: enorme, se clava un poco de más y vuelve a su tamaño."""
    x = _lim(x)
    if x < 0.36:
        u = x / 0.36
        return ESCALA_ZOOM + (0.93 - ESCALA_ZOOM) * (u * u * (3 - 2 * u))
    u = (x - 0.36) / 0.64
    return 1.0 - 0.07 * math.cos(u * math.pi * 1.5) * (1 - u)


def paso_de(estilo, n):
    """Segundos entre una pieza y la siguiente."""
    n = max(1, int(n))
    if estilo == "ola":
        return PASO_OLA
    if estilo == "giro":
        return PASO_GIRO
    if estilo == "cine":
        return min(PASO_CINE_MAX, max(0.0, CINE_TOTAL - DURACION["cine"]) / n)
    if estilo == "maquina":
        return min(PASO_MAQUINA_MAX, MAQUINA_TOTAL / n)
    if estilo == "lluvia":
        return min(PASO_LLUVIA_MAX, (LLUVIA_TOTAL - DURACION["lluvia"]) / n)
    return 0.0


def giro_de(estilo, t, i):
    """Grados que le faltan a la pieza `i` para quedar derecha (solo en «Giro»)."""
    if estilo != "giro":
        return 0.0
    x = (t - i * PASO_GIRO) / DURACION["giro"]
    return (1 - rebote(x)) * GRADOS_GIRO * (-1 if i % 2 == 0 else 1)


def letras_escritas(t, n):
    """Cuántas letras lleva escritas la máquina a los `t` segundos."""
    paso = paso_de("maquina", n)
    return max(0, min(n, int(t / paso) + 1)) if t > 0 and paso > 0 else 0


def unidades_de(estilo, texto):
    """En qué piezas entra un verso: palabras (ola, giro), letras (cine, máquina, lluvia) o el verso entero."""
    estilo = estilo_escena_valido(estilo)
    if estilo in POR_PALABRAS:
        return texto.split()
    if estilo in POR_LETRAS:
        return [c for c in texto if not c.isspace()]
    return [texto]


def entrada(estilo, t, n):
    """Cómo va entrando cada una de las `n` piezas de un verso, `t` segundos después de empezar.
    Devuelve [(alfa 0..1, subida en «alturas de letra», escala)]."""
    estilo = estilo_escena_valido(estilo)
    n = max(1, int(n))
    if estilo == "ola":
        salida = []
        for i in range(n):
            x = (t - i * PASO_OLA) / DURACION["ola"]
            salida.append((suave(x * 1.6), (1 - rebote(x)) * 0.7, 1.0))
        return salida
    if estilo == "cine":
        paso = min(PASO_CINE_MAX, max(0.0, CINE_TOTAL - DURACION["cine"]) / n)
        return [(suave((t - i * paso) / DURACION["cine"]), (1 - suave((t - i * paso) / DURACION["cine"])) * 0.12,
                 1.0) for i in range(n)]
    if estilo == "neon":
        return [(parpadeo_neon(t), 0.0, 0.97 + 0.03 * suave(t / DURACION["neon"]))]
    if estilo == "zoom":
        x = t / DURACION["zoom"]
        return [(_lim(x * 3.2), 0.0, golpe(x))]
    if estilo == "maquina":
        paso = paso_de(estilo, n)
        return [(_lim((t - i * paso) / DURACION["maquina"]), 0.0, 1.0) for i in range(n)]
    if estilo == "lluvia":
        paso = paso_de(estilo, n)
        salida = []
        for i in range(n):
            # no caen en fila: cada letra se adelanta o se atrasa un poco
            x = (t - i * paso - ((i * 37) % 11) * 0.012) / DURACION["lluvia"]
            salida.append((suave(x * 2.4), (1 - bote(x)) * 1.5, 1.0))
        return salida
    if estilo == "giro":
        salida = []
        for i in range(n):
            x = (t - i * PASO_GIRO) / DURACION["giro"]
            salida.append((suave(x * 1.8), (1 - suave(x)) * 0.25, 0.55 + 0.45 * suave(x)))
        return salida
    a = suave(t / DURACION["resplandor"])
    return [(a, (1 - a) * 0.45, 0.9 + 0.1 * a)]


def termino_entrada(estilo, t, n):
    """¿Ya entró todo el verso? (para dejar de pedir cuadros fluidos)."""
    estilo = estilo_escena_valido(estilo)
    n = max(1, int(n))
    if estilo in POR_PALABRAS or estilo in POR_LETRAS:
        extra = 0.12 if estilo == "lluvia" else 0.0        # lo que se atrasa cada gota
        return t >= (n - 1) * paso_de(estilo, n) + DURACION[estilo] + extra
    if estilo == "zoom":
        return t >= DURACION["zoom"]
    if estilo == "neon":
        return t >= 0.75
    return t >= DURACION["resplandor"]


def salida_de(t):
    """El verso anterior al irse: (alfa, cuánto sube)."""
    a = suave(t / SALIDA)
    return 1 - a, a


# ------------------------------------------------------------------ lienzo

class LienzoEscena(LienzoKaraoke):
    """El verso que suena, en grande y con su entrada animada."""

    def __init__(self, ctx, colores, estilo="resplandor", padre=None):
        self.estilo = estilo_escena_valido(estilo)
        self._anterior = -1
        self._t_cambio = 0.0
        self._halos = {}             # (k, estilo, tamaño) -> (imagen, margen)
        super().__init__(ctx, colores, padre=padre)
        self.setMouseTracking(True)

    def poner_estilo(self, estilo):
        self.estilo = estilo_escena_valido(estilo)
        self._halos = {}
        self._t_cambio = time.monotonic()      # el verso de ahora vuelve a entrar con el estilo nuevo
        self._despertar()
        self.update()

    def al_cambiar_tipografia(self):
        self._halos = {}
        super().al_cambiar_tipografia()

    def _poner_lineas(self, lineas, sincronizada, mensaje, esperando=False):
        super()._poner_lineas(lineas, sincronizada, mensaje, esperando)
        self._anterior = -1
        self._halos = {}

    # ----------------------------------------------------------- medidas
    def _tam_verso(self):
        return max(34.0, min(108.0, self.width() / 12.5))

    def _fuente(self, tam):
        if self.estilo == "cine":
            f = QFont("Georgia")
            f.setPixelSize(int(tam * 0.86))
            f.setWeight(QFont.Normal)
            f.setLetterSpacing(QFont.PercentageSpacing, 112)
        else:
            maquina = self.estilo == "maquina"
            f = QFont("Consolas" if maquina else "Segoe UI")
            f.setPixelSize(int(tam * (0.92 if maquina else 1.0)))
            f.setWeight(QFont.Bold if self.estilo in ("neon", "maquina") else QFont.Black)
            f.setLetterSpacing(QFont.PercentageSpacing, {"neon": 104, "maquina": 100}.get(self.estilo, 97))
        return tipografia_letra.adaptar(f)      # la tipografía elegida (o la de cada estilo, si es la de siempre)

    # ----------------------------------------------------------- animación
    def _cuadro(self):
        ahora = time.monotonic()
        if ahorrando(self.ctx) or not a_la_vista(self):
            self._ultimo_cuadro = ahora
            if self.reloj.interval() != FPS_DORMIDO:
                self.reloj.start(FPS_DORMIDO)
            return
        dt = min(0.1, ahora - self._ultimo_cuadro)
        self._ultimo_cuadro = ahora
        self._pulso = max(0.0, self._pulso - dt * 1.6)
        if self.lineas and self.sincronizada:
            i = self._indice(self.ahora_ms())
            if i != self._actual:
                self._anterior = self._actual
                self._actual = i
                self._t_cambio = ahora
                if 0 <= i < len(self.lineas) and not self.lineas[i]["pausa"]:
                    self._pulso = 1.0
        t = ahora - self._t_cambio
        n = len(unidades_de(self.estilo, self._texto(self._actual)))
        self._moviendo = (not termino_entrada(self.estilo, t, n)) or t < SALIDA or self._pulso > 0.3
        ms = FPS_SONANDO if self._moviendo else self._ms_objetivo()
        if self.reloj.interval() != ms:
            self.reloj.start(ms)
        self.update()

    def _texto(self, k):
        if 0 <= k < len(self.lineas) and not self.lineas[k]["pausa"]:
            return self.lineas[k]["texto"] or ""
        return ""

    def _siguiente_con_texto(self, k):
        for j in range(max(0, k + 1), len(self.lineas)):
            if self._texto(j):
                return j
        return -1

    # ----------------------------------------------------------- pintura
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(QRectF(0, 0, self.width(), self.height()), self._fondo())
        p.setRenderHint(QPainter.TextAntialiasing)
        if not self.lineas:
            self._pintar_mensaje(p)
            p.end()
            return
        if not self.sincronizada:
            self.mensaje = ("Esta letra no trae tiempos, así que aquí no puede avanzar sola.\n"
                            "En el karaoke puedes leerla entera.")
            self._pintar_mensaje(p)
            p.end()
            return
        ahora = time.monotonic()
        t = ahora - self._t_cambio
        alto_util = self.height() - self.margen_arriba - self.margen_abajo
        centro_y = self.margen_arriba + alto_util * 0.46
        tam = self._tam_verso()
        self._pintar_resplandor(p, centro_y, tam, ahora)
        # el anterior se va hacia arriba
        if self._anterior >= 0 and t < SALIDA and self._texto(self._anterior):
            alfa, sube = salida_de(t)
            self._pintar_verso(p, self._anterior, centro_y - sube * tam * 1.6, tam, alfa * 0.8, None)
        # el siguiente espera abajo, pequeño
        sig = self._siguiente_con_texto(self._actual)
        if sig >= 0:
            self._pintar_pequeno(p, self._texto(sig), self.margen_arriba + alto_util * 0.86, tam * 0.36, 0.42)
        if 0 <= self._actual < len(self.lineas) and self.lineas[self._actual]["pausa"]:
            self._pintar_pausa(p, centro_y, tam, ahora)
        elif self._texto(self._actual):
            self._pintar_verso(p, self._actual, centro_y, tam, 1.0, t)
            tr = self.traducciones[self._actual] if self._actual < len(self.traducciones) else ""
            if tr:
                filas = len(self._filas(self._actual, tam))
                y_tr = centro_y + filas * QFontMetricsF(self._fuente(tam)).height() * 0.55 + tam * 0.55
                self._pintar_pequeno(p, tr, y_tr, tam * 0.34, 0.75 * suave(t / 0.6))
        elif self._actual < 0:
            # antes del primer verso
            primero = self._siguiente_con_texto(-1)
            if primero >= 0:
                self._pintar_pequeno(p, "♪", centro_y, tam, 0.5)
        self._pintar_fuente(p)
        p.end()

    def _filas(self, k, tam):
        f = self._fuente(tam)
        ancho = max(120.0, self.width() * 0.84)
        return partir(self._texto(k), QFontMetricsF(f), ancho)

    def _colores(self):
        c1, c2, c3 = (QColor(c) for c in self.paleta[:3])
        return c1, c2, c3

    def _pintar_resplandor(self, p, cy, tam, ahora):
        """El resplandor de detrás: dos manchas de los colores de la carátula que respiran y laten."""
        c1, c2, _c3 = self._colores()
        respira = 0.5 + 0.5 * math.sin((ahora - self._t0) * 1.3)
        fuerza = 0.42 + 0.18 * respira + 0.35 * self._pulso
        w, h = self.width(), self.height()
        for c, dx, radio in ((c1, -0.12, 0.55), (c2, 0.14, 0.45)):
            g = QRadialGradient(QPointF(w * (0.5 + dx), cy), max(w, h) * radio * (0.9 + 0.12 * self._pulso))
            centro = QColor(c)
            centro.setAlphaF(_lim(0.55 * fuerza))
            fin = QColor(c)
            fin.setAlphaF(0.0)
            g.setColorAt(0.0, centro)
            g.setColorAt(1.0, fin)
            p.fillRect(QRectF(0, 0, w, h), QBrush(g))

    def _halo(self, k, filas, f, fm, color):
        """El brillo alrededor de un verso: se pinta una vez (caminos de texto con trazos gruesos) y se guarda."""
        clave = (k, self.estilo, f.family(), f.pixelSize(), self.width(), color.name())
        hecho = self._halos.get(clave)
        if hecho is not None:
            return hecho
        margen = int(f.pixelSize() * 0.5)
        alto_fila = fm.height()
        ancho = int(max(fm.horizontalAdvance(x) for x in filas) + 2 * margen)
        alto = int(len(filas) * alto_fila + 2 * margen)
        img = QImage(max(1, ancho), max(1, alto), QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        q = QPainter(img)
        q.setRenderHint(QPainter.Antialiasing)
        ruta = QPainterPath()
        ruta.setFillRule(Qt.WindingFill)
        for n, fila in enumerate(filas):
            x = (ancho - fm.horizontalAdvance(fila)) / 2
            ruta.addText(QPointF(x, margen + n * alto_fila + fm.ascent()), f, fila)
        q.setBrush(Qt.NoBrush)
        capas = ((22, 14), (14, 26), (8, 44), (4, 70)) if self.estilo == "neon" else ((18, 12), (10, 24), (5, 38))
        for grosor, alfa in capas:
            c = QColor(color)
            c.setAlpha(alfa)
            q.setPen(QPen(c, grosor * f.pixelSize() / 80.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            q.drawPath(ruta)
        q.end()
        self._halos = {k2: v for k2, v in self._halos.items() if k2[0] in (self._actual, self._anterior)}
        self._halos[clave] = (img, margen)
        return img, margen

    def _pintar_verso(self, p, k, cy, tam, alfa_total, t):
        """Un verso centrado en `cy`. Con `t` (segundos desde que entró) se anima su entrada."""
        f = self._fuente(tam)
        fm = QFontMetricsF(f)
        filas = self._filas(k, tam)
        alto_fila = fm.height()
        y0 = cy - len(filas) * alto_fila / 2
        c1, c2, _c3 = self._colores()
        color_halo = c1.lighter(150) if self.estilo == "neon" else c2.lighter(130)
        neon = self.estilo == "neon"
        # el halo: entra con el verso (en neón, parpadea con él)
        if t is not None:
            n_total = len(unidades_de(self.estilo, self._texto(k)))
            fases = entrada(self.estilo, t, n_total)
            if self.estilo in ("neon", "resplandor", "zoom"):
                brillo = fases[0][0]
            elif self.estilo in ("maquina", "lluvia", "giro"):
                # el halo se enciende cuando ya están casi todas: antes dejaría ver el verso que aún no llega
                dura = (n_total - 1) * paso_de(self.estilo, n_total) + DURACION[self.estilo]
                brillo = suave((t - 0.65 * dura) / max(0.25, 0.6 * dura))
            else:
                brillo = suave(t / 0.6)
        else:
            fases, brillo = None, 1.0
        p.save()
        if self.estilo == "zoom" and fases is not None and fases[0][2] != 1.0:
            # todo el verso (sus filas y su halo) crece a la vez, desde el centro
            p.translate(self.width() / 2, cy)
            p.scale(fases[0][2], fases[0][2])
            p.translate(-self.width() / 2, -cy)
            fases = [(fases[0][0], 0.0, 1.0)]
        img, margen = self._halo(k, filas, f, fm, color_halo)
        p.save()
        p.setOpacity(_lim(alfa_total * brillo * (0.75 + 0.25 * self._pulso)))
        p.drawImage(QPointF((self.width() - img.width()) / 2, y0 - margen), img)
        p.restore()
        p.setFont(f)
        progreso = self._progreso(k, self.ahora_ms()) if t is not None else 1.0
        total = sum(len(x) for x in filas) or 1
        hecho = progreso * total
        cantado = QColor(c1).lighter(170) if not neon else QColor(255, 255, 255)
        base = QColor(255, 255, 255, 235) if not neon else QColor(c1).lighter(185)
        indice = 0            # índice de pieza (palabra o letra) a lo largo del verso
        antes = 0             # letras ya pintadas en filas anteriores
        for n, fila in enumerate(filas):
            ancho_fila = fm.horizontalAdvance(fila)
            x0 = (self.width() - ancho_fila) / 2
            y = y0 + n * alto_fila + fm.ascent()
            piezas = self._piezas(fila, fm, x0)
            for texto, x, letras_antes in piezas:
                if fases is not None:
                    a, sube, esc = fases[min(indice, len(fases) - 1)]
                    giro = giro_de(self.estilo, t, indice)
                else:
                    a, sube, esc, giro = 1.0, 0.0, 1.0, 0.0
                indice += 1
                if a <= 0.01:
                    continue
                # lo cantado se tiñe (de izquierda a derecha, como el karaoke)
                local = _lim((hecho - antes - letras_antes) / max(1, len(texto)))
                color = QColor(cantado) if local >= 1 else QColor(base)
                if 0 < local < 1:
                    g = QLinearGradient(x, 0, x + fm.horizontalAdvance(texto), 0)
                    g.setColorAt(max(0.0, local - 0.08), cantado)
                    g.setColorAt(min(1.0, local + 0.08), base)
                    pluma = QPen(QBrush(g), 1)
                else:
                    pluma = QPen(color)
                p.save()
                p.setOpacity(_lim(a * alfa_total))
                ancho_pieza = fm.horizontalAdvance(texto)
                p.translate(x + ancho_pieza / 2, y - sube * tam)
                if giro:
                    centro = fm.ascent() * 0.36          # gira sobre el centro de la palabra, no sobre su pie
                    p.translate(0, -centro)
                    p.rotate(giro)
                    p.translate(0, centro)
                p.scale(esc, esc)
                p.translate(-ancho_pieza / 2, 0)
                p.setPen(pluma)
                p.drawText(QPointF(0, 0), texto)
                p.restore()
            antes += len(fila) + 1
        if self.estilo == "maquina" and t is not None:
            self._pintar_cursor(p, filas, fm, y0, alto_fila, t, alfa_total)
        p.restore()

    def _pintar_cursor(self, p, filas, fm, y0, alto_fila, t, alfa):
        """El cursor de la máquina: detrás de la última letra escrita; al acabar, parpadea."""
        n = sum(1 for fila in filas for c in fila if not c.isspace())
        escritas = letras_escritas(t, n)
        if escritas >= n and int(t / 0.45) % 2:
            return
        fila_n, x = 0, 0.0
        quedan = escritas
        for fila_n, fila in enumerate(filas):
            hay = sum(1 for c in fila if not c.isspace())
            if quedan <= hay or fila_n == len(filas) - 1:
                hasta = 0
                while hasta < len(fila) and quedan > 0:
                    quedan -= 0 if fila[hasta].isspace() else 1
                    hasta += 1
                x = (self.width() - fm.horizontalAdvance(fila)) / 2 + fm.horizontalAdvance(fila[:hasta])
                break
            quedan -= hay
        alto = fm.ascent() * 0.86
        pie = y0 + fila_n * alto_fila + fm.ascent()
        p.save()
        p.setOpacity(_lim(alfa * 0.9))
        p.fillRect(QRectF(x + alto * 0.07, pie - alto * 0.92, max(3.0, alto * 0.09), alto * 1.04),
                   self._colores()[0].lighter(170))
        p.restore()

    def _piezas(self, fila, fm, x0):
        """[(texto, x, letras antes en la fila)] para pintar la fila pieza a pieza según el estilo."""
        if self.estilo in POR_PALABRAS:
            salida, pos = [], 0
            for palabra in fila.split(" "):
                if palabra:
                    salida.append((palabra, x0 + fm.horizontalAdvance(fila[:pos]), pos))
                pos += len(palabra) + 1
            return salida
        if self.estilo in POR_LETRAS:
            return [(c, x0 + fm.horizontalAdvance(fila[:i]), i) for i, c in enumerate(fila) if c != " "]
        return [(fila, x0, 0)]

    def _pintar_pequeno(self, p, texto, cy, tam, alfa):
        if not texto or alfa <= 0.01:
            return
        f = QFont("Georgia" if self.estilo == "cine" else "Segoe UI")
        f.setPixelSize(int(max(13, tam)))
        f.setWeight(QFont.DemiBold)
        fm = QFontMetricsF(f)
        filas = partir(texto, fm, max(120.0, self.width() * 0.8))[:2]
        p.save()
        p.setFont(f)
        p.setOpacity(_lim(alfa))
        p.setPen(QColor(255, 255, 255))
        y = cy - len(filas) * fm.height() / 2 + fm.ascent()
        for fila in filas:
            p.drawText(QPointF((self.width() - fm.horizontalAdvance(fila)) / 2, y), fila)
            y += fm.height()
        p.restore()

    def _pintar_pausa(self, p, cy, tam, ahora):
        """Un tramo instrumental: tres puntos de los colores de la carátula que respiran."""
        c1, c2, c3 = self._colores()
        r = tam * 0.16 * (1.0 + 0.18 * math.sin((ahora - self._t0) * 3.4))
        p.save()
        p.setPen(Qt.NoPen)
        for n, c in enumerate((c1, c2, c3)):
            p.setOpacity(0.55 + 0.45 * _lim(math.sin((ahora - self._t0) * 2.2 - n * 0.7) * 0.5 + 0.5))
            p.setBrush(QColor(c).lighter(140))
            p.drawEllipse(QPointF(self.width() / 2 + (n - 1) * r * 3.4, cy), r, r)
        p.restore()

    # ----------------------------------------------------------- ratón: aquí no se salta ni se desplaza
    def mouseMoveEvent(self, e):
        QWidget.mouseMoveEvent(self, e)

    def mousePressEvent(self, e):
        QWidget.mousePressEvent(self, e)

    def wheelEvent(self, e):
        e.ignore()


class PaginaLetraEscena(VistaGrande):
    """La vista grande: el lienzo de la escena, «Estilo» y «Traducir» en la cabecera."""

    titulo = "Letra con efectos"

    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.colores = colores_de(ctx)
        estilo = estilo_escena_valido(ctx.ajustes[AJUSTE_ESTILO])
        self.lienzo = LienzoEscena(ctx, self.colores, estilo, self)
        self.lienzo.margen_arriba = 64
        self.lienzo.margen_abajo = 120
        self.lienzo.installEventFilter(self)
        self.lienzo.lower()
        self.bt_estilo = QPushButton()
        self.bt_estilo.setCursor(Qt.PointingHandCursor)
        self.bt_estilo.setStyleSheet(BOTON)
        self.bt_estilo.setFocusPolicy(Qt.NoFocus)
        self.bt_estilo.clicked.connect(self._menu_estilos)
        self.fila_cab.insertWidget(1, self.bt_estilo, 0, Qt.AlignVCenter)
        self.bt_traducir = QPushButton("Traducir")
        self.bt_traducir.setCheckable(True)
        self.bt_traducir.setChecked(bool(ctx.ajustes["traducir_letra"]))
        self.bt_traducir.setToolTip("Mostrar la traducción bajo el verso")
        self.bt_traducir.setCursor(Qt.PointingHandCursor)
        self.bt_traducir.setStyleSheet(BOTON)
        self.bt_traducir.setFocusPolicy(Qt.NoFocus)
        self.bt_traducir.toggled.connect(self._traducir)
        self.fila_cab.insertWidget(2, self.bt_traducir, 0, Qt.AlignVCenter)
        self._pintar_boton_estilo()

    def _pintar_boton_estilo(self):
        e = self.lienzo.estilo
        self.bt_estilo.setText(f"Estilo: {NOMBRES_ESCENA[e]}  ▾")
        self.bt_estilo.setToolTip(DETALLE_ESCENA[e])

    def _menu_estilos(self):
        menu = QMenu(self)
        for clave in ESTILOS_ESCENA:
            a = menu.addAction(f"{NOMBRES_ESCENA[clave]} — {DETALLE_ESCENA[clave]}",
                               lambda k=clave: self.elegir_estilo(k))
            a.setCheckable(True)
            a.setChecked(clave == self.lienzo.estilo)
        menu.exec(self.bt_estilo.mapToGlobal(self.bt_estilo.rect().bottomLeft()))

    def elegir_estilo(self, estilo):
        estilo = estilo_escena_valido(estilo)
        self.ctx.ajustes[AJUSTE_ESTILO] = estilo
        try:
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        self.lienzo.poner_estilo(estilo)
        self._pintar_boton_estilo()

    def keyPressEvent(self, e):
        # 1-8 cambian de estilo sin abrir el menú
        if Qt.Key_1 <= e.key() < Qt.Key_1 + len(ESTILOS_ESCENA):
            self.elegir_estilo(ESTILOS_ESCENA[e.key() - Qt.Key_1])
            return
        super().keyPressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.lienzo.setGeometry(0, 0, self.width(), self.height())
        self.lienzo.lower()
        self.cabecera.raise_()
        self.pie.raise_()

    def _traducir(self, on):
        self.ctx.ajustes["traducir_letra"] = bool(on)
        try:
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        self.lienzo.pedir_traduccion()
