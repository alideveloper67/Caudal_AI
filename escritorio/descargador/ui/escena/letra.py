# -*- coding: utf-8 -*-
"""Letra animada tipo póster: la línea que suena en grande, palabra a palabra, con tipografía
cinética. Las palabras entran en su instante exacto; la palabra más larga va en mayúsculas y
con acento de color. Todo se dibuja con QPainter sobre fondo transparente."""

import bisect
import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, TEXTO, TEXTO_2, TEXTO_3, acento_legible, fuente,
                     fuente_impacto, preparar_transparente)

CANTO_POR_DEFECTO = 1800      # ms que dura cantar una línea si no lo dice
DURACION_ENTRADA = 0.28       # s que tarda una palabra en asentarse
DURACION_CAMBIO = 0.42        # s de la transición entre líneas
SUBIDA_CAMBIO = 50.0          # px que sube el bloque anterior al salir
FACTOR_FUERTE = 1.55          # tamaño de la palabra fuerte respecto al base
MAX_FILAS = 4
ANCHO_MAX = 0.92              # fracción del ancho del widget que puede ocupar el bloque
ALTO_MAX = 0.70               # fracción del alto del widget que puede ocupar el bloque
TAM_MIN = 14.0
TAM_MAX = 150.0
GAP_PALABRAS = 0.28           # separación entre palabras, en fracción del tamaño base
GAP_FILAS = 0.10              # separación entre filas, en fracción del tamaño base
PAD = 28.0                    # margen del widget
RESERVA = 44.0                # alto que se deja abajo para la línea siguiente
PERIODO_PUNTOS = 1.1          # s de un latido completo de los puntos de pausa


# --------------------------------------------------------------------------- funciones puras

def indice_en(lineas, ms):
    """Índice de la última línea con ms <= ms_actual; -1 si no hay ninguna o no hay sincronía."""
    if ms is None:
        return -1
    indice = -1
    for i, linea in enumerate(lineas or []):
        inicio = linea.get("ms")
        if inicio is not None and inicio <= ms:
            indice = i
    return indice


def repartir_palabras(texto, inicio_ms, canto_ms=None):
    """Cada palabra con el ms en que aparece. La primera entra en inicio_ms y el resto se reparte
    canto_ms (1800 si falta) en proporción a las letras de las palabras anteriores."""
    palabras = str(texto or "").split()
    if not palabras:
        return []
    canto = canto_ms if (canto_ms is not None and canto_ms > 0) else CANTO_POR_DEFECTO
    pesos = [_peso_palabra(w) for w in palabras]
    total = sum(pesos)
    resultado = []
    acumulado = 0
    for palabra, peso in zip(palabras, pesos):
        # floor (int) garantiza que la última quede estrictamente por debajo de inicio+canto
        resultado.append((palabra, int(inicio_ms + canto * acumulado / total)))
        acumulado += peso
    return resultado


def palabra_fuerte(palabras):
    """Índice de la palabra a destacar: la más larga; si empatan, la última. -1 si no hay."""
    mejor = -1
    mejor_len = -1
    for i, palabra in enumerate(palabras or []):
        texto = palabra[0] if isinstance(palabra, tuple) else palabra
        n = len(str(texto))
        if n >= mejor_len:
            mejor, mejor_len = i, n
    return mejor


def _firma(ef):
    """Identidad del reparto en trozos: si no cambia, los índices siguen valiendo."""
    return [(e["orig"], e["texto"], e["ms"], e["pausa"]) for e in ef]


def _peso_palabra(palabra):
    """Peso para repartir el tiempo: letras de la palabra, mínimo 1."""
    return max(1, sum(1 for c in palabra if c.isalpha()))


# --------------------------------------------------------------------------- utilidades de dibujo

def _ease_out_back(t):
    t = min(1.0, max(0.0, t))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def _ease_out_cubic(t):
    t = min(1.0, max(0.0, t))
    return 1.0 - (1.0 - t) ** 3


class _Item:
    """Una palabra ya colocada: su trazo (en coordenadas del widget), su caja y su estilo."""
    __slots__ = ("indice", "trazo", "rect", "fuerte", "contorno")

    def __init__(self, indice, trazo, rect, fuerte, contorno):
        self.indice = indice
        self.trazo = trazo
        self.rect = rect
        self.fuerte = fuerte
        self.contorno = contorno


class _Disposicion:
    """Disposición de una línea (o trozo) para el tamaño actual; se guarda en caché."""
    __slots__ = ("tipo", "items", "ms_palabras", "puntos", "radio")

    def __init__(self, tipo, items=(), ms_palabras=(), puntos=(), radio=0.0):
        self.tipo = tipo              # "palabras", "pausa" o "vacia"
        self.items = list(items)
        self.ms_palabras = list(ms_palabras)
        self.puntos = list(puntos)
        self.radio = radio


class LetraCinetica(QWidget):
    """Letra de la canción en grande, translúcida, sincronizada con el ms de reproducción."""

    def __init__(self, parent=None):
        super().__init__(parent)
        preparar_transparente(self)
        self._lineas = []
        self._sincronizada = False
        self._ms = 0
        self._indice = -1             # índice dentro de las entradas efectivas (trozos)
        self._t_linea = time.monotonic()
        self._entradas = {}           # índice de palabra -> instante (monotonic) en que entró
        self._prev = None             # (disposición anterior, instante del cambio)
        self._mensaje = ""
        self._dominante = QColor(DOMINANTE)
        self._segundo = QColor(SEGUNDO)
        self._brillo = QColor(BRILLO)
        self._ef = None               # entradas efectivas: líneas partidas en trozos si hace falta
        self._ef_clave = None         # tamaño con el que se construyeron
        self._cache = {}              # índice efectivo -> disposición (válida para _ef_clave)
        self._timer = QTimer(self)
        self._timer.setInterval(33)     # 30 fps: de sobra para la entrada de las palabras
        self._timer.timeout.connect(self._tic)

    def sizeHint(self):
        return QSize(620, 420)

    # ----------------------------------------------------------------- API pública

    def poner_lineas(self, lineas, sincronizada):
        """Carga la letra. Si no está sincronizada (o ninguna línea tiene ms), se muestra estática."""
        self._lineas = [dict(linea) for linea in (lineas or [])]
        self._sincronizada = bool(sincronizada) and any(
            linea.get("ms") is not None for linea in self._lineas)
        self._ef = None
        self._cache.clear()
        self._indice = -1
        self._prev = None
        self._entradas = {}
        self._t_linea = time.monotonic()
        if self._sincronizada:
            self._avanzar(time.monotonic())
        self._arrancar()
        self.update()

    def fijar_ms(self, ms):
        """Posición de reproducción actual (en ms). Se llama unas 30 veces por segundo."""
        if ms is None:
            return
        self._ms = int(ms)
        if not self._sincronizada:
            return
        if self._avanzar(time.monotonic()):
            self._arrancar()
            self.update()

    def poner_mensaje(self, texto):
        """Muestra un mensaje centrado en lugar de la letra. Cadena vacía lo quita."""
        self._mensaje = str(texto or "")
        self._arrancar()
        self.update()

    def poner_colores(self, dominante, segundo, brillo):
        """Colores de la carátula que suena. El brillo define el acento de la palabra fuerte."""
        self._dominante = QColor(dominante)
        self._segundo = QColor(segundo)
        self._brillo = QColor(brillo)
        self.update()

    def indice_actual(self):
        """Índice (en la lista original) de la línea que suena; -1 si no hay o no hay sincronía."""
        if not self._sincronizada or self._indice < 0:
            return -1
        return self._efectivas()[self._indice]["orig"]

    # ----------------------------------------------------------------- estado y animación

    def _avanzar(self, ahora):
        """Pone al día trozo actual y palabras visibles. True si algo visible cambió."""
        ef = self._efectivas()
        if not (0 <= self._indice < len(ef)):
            self._indice = -1
            self._entradas = {}
        nuevo = indice_en(ef, self._ms)
        cambio = False
        if nuevo != self._indice:
            if self._indice >= 0:
                self._prev = (self._disposicion(self._indice), ahora)
            self._indice = nuevo
            self._t_linea = ahora
            self._entradas = {}
            cambio = True
        if self._indice >= 0 and not ef[self._indice]["pausa"]:
            disp = self._disposicion(self._indice)
            visibles = bisect.bisect_right(disp.ms_palabras, self._ms)
            for j in list(self._entradas):
                if j >= visibles:
                    del self._entradas[j]
                    cambio = True
            for j in range(visibles):
                if j not in self._entradas:
                    self._entradas[j] = ahora
                    cambio = True
        return cambio

    def _animando(self, ahora):
        """True mientras haya algo que mover: palabras entrando, transición o puntos latiendo."""
        if self._mensaje or not self._sincronizada:
            return False
        if self._prev is not None and ahora - self._prev[1] < DURACION_CAMBIO:
            return True
        if any(ahora - t0 < DURACION_ENTRADA for t0 in self._entradas.values()):
            return True
        if self._indice >= 0 and self._efectivas()[self._indice]["pausa"]:
            return True
        return False

    def _arrancar(self):
        if self._timer.isActive():
            return
        if a_la_vista(self) and self._animando(time.monotonic()):
            self._timer.start()

    def _tic(self):
        if not a_la_vista(self):
            self._timer.stop()
            return
        ahora = time.monotonic()
        self.update()
        if not self._animando(ahora):
            self._timer.stop()

    def showEvent(self, evento):
        super().showEvent(evento)
        self._arrancar()

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        # el reparto en trozos depende del tamaño: si cambia, se recalcula el estado; si no,
        # las palabras ya dichas siguen como estaban (no se vuelve a animar nada)
        if not self._sincronizada:
            return
        antes = self._ef
        self._ef = None
        ef = self._efectivas()
        if antes is not None and _firma(antes) == _firma(ef):
            return
        self._prev = None
        self._indice = -1
        self._entradas = {}
        self._avanzar(time.monotonic())
        self._arrancar()

    # ----------------------------------------------------------------- disposición

    def _area(self):
        ancho = self.width()
        alto = self.height()
        return QRectF(PAD, PAD, max(1.0, ancho - 2 * PAD), max(1.0, alto - 2 * PAD - RESERVA))

    def _efectivas(self):
        """Lista de entradas que se muestran en orden: cada línea, o sus trozos si no caben
        en 4 filas al tamaño mínimo. Se reconstruye solo si cambia el tamaño del widget."""
        clave = (self.width(), self.height())
        if self._ef is None or self._ef_clave != clave:
            self._ef = self._construir_efectivas()
            self._ef_clave = clave
            self._cache.clear()
        return self._ef

    def _construir_efectivas(self):
        ef = []
        for i, linea in enumerate(self._lineas):
            texto = str(linea.get("texto", "") or "")
            palabras = texto.split()
            if linea.get("pausa") or not palabras or linea.get("ms") is None:
                ef.append({"orig": i, "texto": texto, "ms": linea.get("ms"),
                           "canto": linea.get("canto"), "pausa": bool(linea.get("pausa"))})
            else:
                ef.extend(self._trozos_de(i, palabras, linea))
        return ef

    def _trozos_de(self, i, palabras, linea):
        """Parte una línea en trozos que quepan en 4 filas y reparte su canto entre ellos."""
        trozos = self._trozos_palabras(palabras)
        canto = linea.get("canto")
        canto = canto if (canto is not None and canto > 0) else CANTO_POR_DEFECTO
        inicio = int(linea["ms"])
        if len(trozos) == 1:
            return [{"orig": i, "texto": " ".join(palabras), "ms": inicio, "canto": canto,
                     "pausa": False}]
        pesos = [sum(_peso_palabra(w) for w in trozo) for trozo in trozos]
        total = sum(pesos)
        resultado = []
        acumulado = 0
        for trozo, peso in zip(trozos, pesos):
            resultado.append({"orig": i, "texto": " ".join(trozo),
                              "ms": int(inicio + canto * acumulado / total),
                              "canto": max(1, int(canto * peso / total)), "pausa": False})
            acumulado += peso
        return resultado

    def _trozos_palabras(self, palabras):
        """Trozos consecutivos, cada uno con el mayor número de palabras que cabe en 4 filas."""
        if self._ajustar(palabras)[3]:
            return [palabras]
        trozos = []
        a = 0
        n = len(palabras)
        while a < n:
            mejor = a + 1                     # una sola palabra siempre se acepta
            lo, hi = a + 2, n
            while lo <= hi:
                medio = (lo + hi) // 2
                if self._ajustar(palabras[a:medio])[3]:
                    mejor = medio
                    lo = medio + 1
                else:
                    hi = medio - 1
            trozos.append(palabras[a:mejor])
            a = mejor
        return trozos

    def _medir(self, palabras, fuerte, tam):
        """(texto mostrado, es_fuerte, fuente, ascenso, descenso, ancho) de cada palabra."""
        medidas = []
        for k, palabra in enumerate(palabras):
            es = (k == fuerte)
            f = fuente_impacto(int(round(tam * FACTOR_FUERTE)) if es else int(round(tam)))
            m = QFontMetricsF(f)
            texto = palabra.upper() if es else palabra
            medidas.append((texto, es, f, m.ascent(), m.descent(), m.horizontalAdvance(texto)))
        return medidas

    @staticmethod
    def _partir_en_filas(medidas, tam, ancho_max):
        """Reparte las palabras en filas que quepan en ancho_max; nunca deja una sola fila si hay
        dos o más palabras."""
        separacion = tam * GAP_PALABRAS
        filas = []
        fila = []
        ancho = 0.0
        for k, m in enumerate(medidas):
            w = m[5]
            if fila and ancho + separacion + w > ancho_max:
                filas.append(fila)
                fila = [k]
                ancho = w
            else:
                ancho += (separacion + w) if fila else w
                fila.append(k)
        if fila:
            filas.append(fila)
        if len(filas) == 1 and len(medidas) >= 2:
            mitad = (len(medidas) + 1) // 2
            filas = [list(range(mitad)), list(range(mitad, len(medidas)))]
        return filas

    @staticmethod
    def _tamano_bloque(medidas, filas, tam):
        """Ancho y alto del bloque de palabras (alineado a la izquierda)."""
        separacion = tam * GAP_PALABRAS
        anchos = []
        altos = []
        for fila in filas:
            anchos.append(sum(medidas[k][5] for k in fila) + separacion * (len(fila) - 1))
            altos.append(max(medidas[k][3] for k in fila) + max(medidas[k][4] for k in fila))
        return max(anchos), sum(altos) + tam * GAP_FILAS * (len(filas) - 1)

    def _ajustar(self, palabras):
        """(medidas, filas, tamaño, cabe): el mayor tamaño que deja el bloque dentro del 92% del
        ancho y el 70% del alto, con 4 filas como máximo. cabe=False si ni al tamaño mínimo."""
        fuerte = palabra_fuerte(palabras)
        area = self._area()
        ancho_max = ANCHO_MAX * self.width()
        alto_max = ALTO_MAX * self.height()
        tam = max(TAM_MIN, min(TAM_MAX, area.height() * 0.42))
        while True:
            medidas = self._medir(palabras, fuerte, tam)
            filas = self._partir_en_filas(medidas, tam, ancho_max)
            bw, bh = self._tamano_bloque(medidas, filas, tam)
            if len(filas) <= MAX_FILAS and bw <= ancho_max and bh <= alto_max:
                return medidas, filas, tam, True
            if tam <= TAM_MIN:
                return medidas, filas, tam, False
            tam = max(TAM_MIN, tam * 0.94)

    def _disposicion(self, idx):
        """Disposición de la entrada idx para el tamaño actual; se calcula una vez y se guarda."""
        guardada = self._cache.get(idx)
        if guardada is not None:
            return guardada
        entrada = self._efectivas()[idx]
        if entrada["pausa"]:
            disp = self._disponer_pausa()
        elif entrada["texto"].split():
            disp = self._disponer_palabras(entrada)
        else:
            disp = _Disposicion("vacia")
        self._cache[idx] = disp
        return disp

    def _disponer_palabras(self, entrada):
        palabras = entrada["texto"].split()
        medidas, filas, tam, _ = self._ajustar(palabras)
        bw, bh = self._tamano_bloque(medidas, filas, tam)
        area = self._area()
        separacion = tam * GAP_PALABRAS
        y = area.top() + max(0.0, (area.height() - bh) / 2.0)
        contorno_linea = (entrada["orig"] % 2 == 1)
        items = []
        for fila in filas:
            asc = max(medidas[k][3] for k in fila)
            desc = max(medidas[k][4] for k in fila)
            x = area.left()
            for k in fila:
                texto, es, f, _, _, ancho = medidas[k]
                trazo = QPainterPath()
                trazo.addText(QPointF(x, y + asc), f, texto)
                rect = QRectF(x, y, ancho, asc + desc)
                items.append(_Item(k, trazo, rect, es, contorno_linea and not es))
                x += ancho + separacion
            y += asc + desc + tam * GAP_FILAS
        ms_palabras = []
        if entrada["ms"] is not None:
            ms_palabras = [ms for _, ms in repartir_palabras(entrada["texto"], entrada["ms"],
                                                             entrada["canto"])]
        return _Disposicion("palabras", items, ms_palabras)

    def _disponer_pausa(self):
        area = self._area()
        radio = max(10.0, min(30.0, min(self.width(), self.height()) * 0.06))
        separacion = radio * 2.6
        cy = area.top() + area.height() / 2.0
        x = area.left() + radio
        puntos = [QPointF(x + i * separacion, cy) for i in range(3)]
        return _Disposicion("pausa", puntos=puntos, radio=radio)

    # ----------------------------------------------------------------- pintado

    def _pintar_items(self, p, disp, entradas, ahora, dy, opacidad, color_fuerte):
        """Dibuja las palabras de una línea. entradas=None significa línea ya completa."""
        for it in disp.items:
            escala = 1.0
            dx = 0.0
            alfa = 1.0
            if entradas is not None:
                t0 = entradas.get(it.indice)
                if t0 is None:
                    continue                      # aún no ha llegado su instante
                t = (ahora - t0) / DURACION_ENTRADA
                if t < 1.0:
                    e = _ease_out_back(t)
                    escala = 1.25 - 0.25 * e
                    dx = 30.0 * (1.0 - e)
                    alfa = 1.0 - (1.0 - max(0.0, t)) ** 2
            if alfa <= 0.0:
                continue
            p.save()
            p.setOpacity(opacidad * alfa)
            c = it.rect.center()
            p.translate(c.x() + dx, c.y() + dy)
            p.scale(escala, escala)
            p.translate(-c.x(), -c.y())
            if it.contorno:
                p.setPen(QPen(QColor(255, 255, 255), 1.6))
                p.setBrush(Qt.NoBrush)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(color_fuerte if it.fuerte else TEXTO)
            p.drawPath(it.trazo)
            p.restore()

    def _pintar_pausa(self, p, disp, ahora, dy, opacidad, color):
        """Tres puntos que laten en secuencia."""
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        for i, c in enumerate(disp.puntos):
            fase = 2.0 * math.pi * (ahora - self._t_linea) / PERIODO_PUNTOS - i * 0.9
            s = 0.5 + 0.5 * math.sin(fase)
            r = disp.radio * (0.72 + 0.28 * s)
            p.setOpacity(opacidad * (0.45 + 0.55 * s))
            p.drawEllipse(QPointF(c.x(), c.y() + dy), r, r)
        p.setOpacity(opacidad)

    def _pintar_mensaje(self, p):
        p.setFont(fuente(16))
        p.setPen(TEXTO_2)
        rect = QRectF(PAD, PAD, max(1.0, self.width() - 2 * PAD), max(1.0, self.height() - 2 * PAD))
        p.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self._mensaje)

    def _pintar_sin_sincronizar(self, p):
        p.setFont(fuente(13))
        p.setPen(TEXTO_3)
        p.drawText(QRectF(PAD, PAD, max(1.0, self.width() - 2 * PAD), 20),
                   Qt.AlignLeft | Qt.AlignTop, "Letra sin sincronizar")
        textos = [str(linea.get("texto", "")) for linea in self._lineas[:6]]
        if not textos:
            return
        p.setFont(fuente(18, QFont.DemiBold))
        p.setPen(TEXTO_2)
        rect = QRectF(PAD, PAD + 30, max(1.0, self.width() - 2 * PAD),
                      max(1.0, self.height() - 2 * PAD - 30))
        p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, "\n".join(textos))

    def paintEvent(self, evento):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.TextAntialiasing, True)
            if self._mensaje:
                self._pintar_mensaje(p)
                return
            if not self._lineas:          # sin letra no se pinta nada
                return
            if not self._sincronizada:
                self._pintar_sin_sincronizar(p)
                return
            ahora = time.monotonic()
            color_fuerte = acento_legible(self._brillo)
            ef = self._efectivas()

            # línea siguiente, en pequeño; si es pausa o vacía, no se muestra nada
            sig = self._indice + 1
            if 0 <= sig < len(ef) and not ef[sig]["pausa"] and ef[sig]["texto"].strip():
                f = fuente(15)
                p.setFont(f)
                p.setPen(TEXTO_3)
                ancho = max(1, int(self.width() - 2 * PAD))
                texto = QFontMetrics(f).elidedText(ef[sig]["texto"], Qt.ElideRight, ancho)
                p.drawText(QRectF(PAD, self.height() - PAD - 24, ancho, 24),
                           Qt.AlignLeft | Qt.AlignVCenter, texto)

            # bloque anterior que sube y se desvanece
            if self._prev is not None:
                disp_prev, t0 = self._prev
                u = (ahora - t0) / DURACION_CAMBIO
                if u < 1.0:
                    e = _ease_out_cubic(u)
                    if disp_prev.tipo == "palabras":
                        self._pintar_items(p, disp_prev, None, ahora, -SUBIDA_CAMBIO * e, 1.0 - e,
                                           color_fuerte)
                    elif disp_prev.tipo == "pausa":
                        self._pintar_pausa(p, disp_prev, ahora, -SUBIDA_CAMBIO * e, 1.0 - e,
                                           color_fuerte)

            # trozo actual
            if self._indice >= 0:
                disp = self._disposicion(self._indice)
                if disp.tipo == "palabras":
                    self._pintar_items(p, disp, self._entradas, ahora, 0.0, 1.0, color_fuerte)
                elif disp.tipo == "pausa":
                    self._pintar_pausa(p, disp, ahora, 0.0, 1.0, color_fuerte)
        finally:
            p.end()
