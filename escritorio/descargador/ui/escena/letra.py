# -*- coding: utf-8 -*-
"""Letra animada tipo póster: la línea que suena en grande, palabra a palabra, con tipografía
cinética. Las palabras entran en su instante exacto; la palabra más larga va en mayúsculas y
con acento de color. Todo se dibuja con QPainter sobre fondo transparente."""

import bisect
import math
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QFontMetricsF, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import QWidget

from .. import epica
from .. import estilo_letra as estilos
from .. import tipografia_letra
from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, SEGUNDO, TEXTO, TEXTO_2, TEXTO_3, acento_legible, fuente,
                     fuente_impacto, preparar_transparente)

ADELANTO_ESCENA_MS = 220      # lo que la escena adelanta la letra (ventana.ADELANTO_LETRA_MS)
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
TAM_TRADUCCION = 0.42         # tamaño de la traducción respecto al de la línea principal
TAM_MIN_TRADUCCION = 13       # px mínimos de la traducción
GAP_TRADUCCION = 0.30         # separación entre el bloque principal y la traducción (fracción)
ALFA_TRADUCCION = 200         # alfa del texto traducido (de 0 a 255)
DURACION_TRADUCCION = 0.35    # s del fundido de la traducción al cambiar de línea
ALTO_LINEA_TRADUCCION = 1.4   # alto de la fila de la traducción, en veces su tamaño de letra

# Estilo con que se pinta la letra (ajuste «estilo_letra», mismas claves que en Android):
#   "clasica": texto relleno, sin borde (la de siempre, por defecto)
#   "nitida":  sombra suave, borde oscuro, brillo y degradado
#   "neon":    relleno blanco y resplandor fuerte del acento en la palabra que suena; las demás tenues
#   "simple":  texto blanco plano; lo que no suena al 45 % de opacidad
#   "degradado", "contorno", "relieve", "marcador", "oro" y "vhs": ver ui/estilo_letra.py (cada palabra se
#   pinta una vez en una imagen y luego solo se copia)
ESTILOS_LETRA = estilos.ESTILOS
OPACIDAD_TENUE_NEON = 0.5     # palabras que no suenan en el estilo neón
OPACIDAD_TENUE_SIMPLE = 0.45  # palabras que no suenan en el estilo simple
OPACIDAD_POR_CANTAR = 0.75    # contorno: las palabras que todavía no llegan, huecas
DURACION_POR_CANTAR = 0.30    # s del fundido de esas palabras al cambiar de línea
RELLENO_MIN, RELLENO_MAX = 0.18, 1.2   # s que tarda una palabra en rellenarse (contorno)
DURACION_MARCADOR = 0.22      # s que tarda en pasar el resaltador por una palabra
DURACION_GLITCH = 0.26        # s del temblor de una palabra al entrar (vhs)
ESPERA_COLORES_MS = 260       # los colores de la carátula cambian en una transición: se espera a que paren
ESTILO_POR_DEFECTO = estilos.POR_DEFECTO


def normalizar_estilo(estilo):
    """El estilo pedido si es válido; si no, el clásico."""
    return estilos.normalizar(estilo)


def estilo_letra():
    """Estilo con que se pintan ahora las letras."""
    return estilos.actual()


def fijar_estilo_letra(estilo):
    """Cambia el estilo de todas las letras (las visibles se repintan al momento)."""
    estilos.fijar(estilo)


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

def _pintar_palabra(p, it, tam, color_fuerte, destello=0.0):
    """Una palabra legible sobre cualquier fondo: sombra suave hacia abajo, borde oscuro fino, resplandor del
    acento en la palabra fuerte (y un destello al entrar) y relleno con un degradado vertical sutil."""
    k = max(0.5, tam / 60.0)
    trazo = it.trazo
    p.setBrush(Qt.NoBrush)
    # sombra difusa (tres pasadas cada vez más finas y oscuras), un poco hacia abajo
    p.save()
    p.translate(0, 2.2 * k)
    for ancho, a in ((16, 22), (9, 40), (4.5, 70)):
        p.setPen(QPen(QColor(0, 0, 0, a), ancho * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(trazo)
    p.restore()
    # resplandor: la palabra fuerte siempre; todas al entrar
    brillo = (0.55 if it.fuerte else 0.0) + 0.6 * destello
    if brillo > 0.02:
        col = QColor(color_fuerte if it.fuerte else QColor(255, 255, 255))
        for ancho, a in ((20, 30), (10, 55)):
            col.setAlpha(int(min(255, a * brillo * 1.6)))
            p.setPen(QPen(col, ancho * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(trazo)
    # borde oscuro fino que recorta la letra del fondo
    p.setPen(QPen(QColor(10, 8, 16, 170), 2.4 * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(trazo)
    # relleno con degradado: blanco arriba y un toque cálido abajo; la fuerte en su color
    r = it.rect
    g = QLinearGradient(0, r.top(), 0, r.bottom())
    if it.fuerte:
        claro = QColor(color_fuerte).lighter(150)
        g.setColorAt(0, claro)
        g.setColorAt(0.55, QColor(color_fuerte))
        g.setColorAt(1, QColor(color_fuerte).darker(115))
    else:
        g.setColorAt(0, QColor(255, 255, 255))
        g.setColorAt(1, QColor(236, 230, 246) if not it.contorno else QColor(255, 255, 255, 215))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawPath(trazo)


def _texto_legible(p, rect, flags, texto, color, tam):
    """Texto corto (traducción, línea siguiente) con sombra suave para que se lea sobre cualquier fondo."""
    k = max(0.6, tam / 22.0)
    for dx, dy, a in ((0, 2 * k, 150), (0, 1 * k, 120), (1 * k, 0, 70), (-1 * k, 0, 70)):
        p.setPen(QColor(0, 0, 0, a))
        p.drawText(rect.translated(dx, dy), flags, texto)
    p.setPen(color)
    p.drawText(rect, flags, texto)


def _pintar_palabra_neon(p, it, tam, color_acento, sonando):
    """Neón: sin borde oscuro; la palabra que suena con un resplandor fuerte del acento."""
    k = max(0.5, tam / 60.0)
    trazo = it.trazo
    if sonando:
        col = QColor(color_acento)
        p.setBrush(Qt.NoBrush)
        for ancho, a in ((26, 40), (15, 75), (7, 130)):
            col.setAlpha(a)
            p.setPen(QPen(col, ancho * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(trazo)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255))
    p.drawPath(trazo)


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
    __slots__ = ("indice", "trazo", "rect", "fuerte", "contorno", "medida", "tam", "capas")

    def __init__(self, indice, trazo, rect, fuerte, contorno, medida=None, tam=0.0):
        self.medida = medida          # alturas reales de su fila (para los estilos de ui/estilo_letra.py)
        self.tam = tam                # tamaño de su letra
        self.capas = {}               # capa -> (imagen, dónde va), ya pintadas
        self.indice = indice
        self.trazo = trazo
        self.rect = rect
        self.fuerte = fuerte
        self.contorno = contorno


class _Disposicion:
    """Disposición de una línea (o trozo) para el tamaño actual; se guarda en caché."""
    __slots__ = ("tipo", "items", "ms_palabras", "puntos", "radio", "tam")

    def __init__(self, tipo, items=(), ms_palabras=(), puntos=(), radio=0.0, tam=0.0):
        self.tipo = tipo              # "palabras", "pausa" o "vacia"
        self.items = list(items)
        self.ms_palabras = list(ms_palabras)
        self.puntos = list(puntos)
        self.radio = radio
        self.tam = tam                # tamaño base de la línea (sin el de la palabra fuerte)


class LetraCinetica(QWidget):
    """Letra de la canción en grande, translúcida, sincronizada con el ms de reproducción.

    Con `con_epica` (la escena), si hay una letra épica elegida la pinta ella (ui/epica): planos montados como
    un edit, movidos por el instante de la canción y el golpe de la música."""

    def __init__(self, parent=None, con_epica=False):
        super().__init__(parent)
        preparar_transparente(self)
        self._con_epica = bool(con_epica)
        self._epica = epica.actual() if con_epica else epica.NINGUNA
        self._montaje = None          # la letra cortada en planos (se hace al pedirla)
        self._energia = self._golpe = 0.0
        self._vivo = False            # en el último cuadro había algo pintado
        self._mascara_borde = None
        self._lienzo_epica = None
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
        self._trad = []               # traducción por línea original (None = sin traducción)
        self._ef = None               # entradas efectivas: líneas partidas en trozos si hace falta
        self._ef_clave = None         # tamaño con el que se construyeron
        self._cache = {}              # índice efectivo -> disposición (válida para _ef_clave)
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(33)     # 30 fps: de sobra para la entrada de las palabras
        self._timer.timeout.connect(self._tic)
        self._estilo = estilos.efectivo()
        self._colores_estilo = None   # colores con que están pintadas las palabras guardadas
        self._t_colores = QTimer(self)
        self._t_colores.setSingleShot(True)
        self._t_colores.setInterval(ESPERA_COLORES_MS)
        self._t_colores.timeout.connect(self._asentar_colores)
        estilos.suscribir(self)
        tipografia_letra.suscribir(self)
        if con_epica:
            epica.suscribir(self)
        self._t_adelanto = QTimer(self)      # prepara el plano que viene, entre cuadro y cuadro
        self._t_adelanto.setSingleShot(True)
        self._t_adelanto.setInterval(0)
        self._t_adelanto.timeout.connect(self._adelantar_epica)

    def sizeHint(self):
        return QSize(620, 420)

    # ----------------------------------------------------------------- API pública

    def poner_lineas(self, lineas, sincronizada):
        """Carga la letra. Si no está sincronizada (o ninguna línea tiene ms), se muestra estática."""
        self._lineas = [dict(linea) for linea in (lineas or [])]
        self._sincronizada = bool(sincronizada) and any(
            linea.get("ms") is not None for linea in self._lineas)
        self._trad = []               # una letra nueva borra las traducciones de la anterior
        self._montaje = None
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
        cambio = self._avanzar(time.monotonic())
        if self._con_planos():
            # todo sale del instante de la canción: cada aviso es un cuadro (y uno más para limpiar al acabar)
            viva = self._montaje_epico().viva(self._t_epica())
            if viva or self._vivo or cambio:
                self.update()
            if not viva and cambio:
                self._arrancar()
            return
        if cambio:
            self._arrancar()
            self.update()

    def fijar_audio(self, energia, golpe):
        """Energía y golpe de la música (0..1): las letras épicas laten con ellos."""
        self._energia, self._golpe = float(energia or 0.0), float(golpe or 0.0)

    def poner_epica(self, clave):
        """Una de epica.NOMBRES, o «» para la letra normal."""
        clave = epica.normalizar(clave)
        if clave == self._epica:
            return
        self._epica = clave
        self._montaje = None
        self._arrancar()
        self.update()

    def epica_puesta(self):
        return self._epica

    def al_cambiar_letra_epica(self):
        self.poner_epica(epica.actual())

    def poner_mensaje(self, texto):
        """Muestra un mensaje centrado en lugar de la letra. Cadena vacía lo quita."""
        self._mensaje = str(texto or "")
        self._arrancar()
        self.update()

    def fijar_traducciones(self, traducciones):
        """Traducción de cada línea, con el mismo índice que las líneas de la letra. None o cadena
        vacía = sin traducción para esa línea. None, lista vacía o de otro largo quitan todas."""
        if not isinstance(traducciones, (list, tuple)) or not traducciones \
                or len(traducciones) != len(self._lineas):
            self._trad = []
        else:
            self._trad = [None if t is None or not str(t).strip() else str(t).strip()
                          for t in traducciones]
        self._cache.clear()           # el tamaño de la línea cambia si ahora lleva traducción
        self._arrancar()
        self.update()

    def poner_estilo(self, estilo):
        """Uno de ESTILOS_LETRA. Se aplica en vivo: la disposición se rehace (el trazo cambia: casi todos
        lo simplifican)."""
        estilo = normalizar_estilo(estilo)
        if estilo == self._estilo:
            return
        self._estilo = estilo
        self._cache.clear()
        self._prev = None
        self._arrancar()
        self.update()

    def estilo(self):
        return self._estilo

    def al_cambiar_estilo_letra(self):
        """Se eligió otro estilo (en el selector o en Ajustes)."""
        self.poner_estilo(estilos.efectivo())

    def al_cambiar_tipografia(self):
        """Otra tipografía mide distinto: se rehace la disposición (y los trozos si cambian)."""
        self._cache.clear()
        if self._montaje is not None:
            self._montaje.olvidar()
        self._prev = None
        if self._sincronizada:
            antes = self._ef
            self._ef = None
            ef = self._efectivas()
            if antes is None or _firma(antes) != _firma(ef):
                self._indice = -1
                self._entradas = {}
                ahora = time.monotonic()
                self._avanzar(ahora)
                # lo que ya se había cantado se queda puesto: cambiar la fuente no lo vuelve a animar
                self._entradas = {k: ahora - 10.0 for k in self._entradas}
                self._prev = None
        else:
            self._ef = None
        self._arrancar()
        self.update()

    def poner_colores(self, dominante, segundo, brillo):
        """Colores de la carátula que suena. El brillo define el acento de la palabra fuerte."""
        self._dominante = QColor(dominante)
        self._segundo = QColor(segundo)
        self._brillo = QColor(brillo)
        # llegan muchos seguidos (la paleta cambia con una transición): las palabras guardadas solo se
        # vuelven a pintar cuando los colores se quedan quietos
        if self._colores_estilo is not None:
            self._t_colores.start()
        self.update()

    def _colores_letra(self):
        if self._colores_estilo is None:
            self._asentar_colores()
        return self._colores_estilo

    def _asentar_colores(self):
        nuevos = estilos.Colores(acento_legible(self._brillo), self._dominante, self._segundo)
        if self._colores_estilo is None or nuevos.clave != self._colores_estilo.clave:
            self._colores_estilo = nuevos
            for disp in self._cache.values():
                for it in disp.items:
                    it.capas.clear()
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
        if self._con_planos():
            # los planos los mueve el reloj de la escena (fijar_ms); aquí solo laten los puntos de una pausa
            return (self._indice >= 0 and self._efectivas()[self._indice]["pausa"]
                    and not self._montaje_epico().viva(self._t_epica()))
        if self._prev is not None and ahora - self._prev[1] < DURACION_CAMBIO:
            return True
        if any(ahora - t0 < DURACION_ENTRADA for t0 in self._entradas.values()):
            return True
        if self._estilo == "contorno" and self._indice >= 0:
            # letras huecas que se rellenan (y las que aún no llegan, que aparecen con un fundido)
            if ahora - self._t_linea < DURACION_POR_CANTAR:
                return True
            disp = self._disposicion(self._indice)
            if any(ahora - t0 < self._relleno_s(disp, j) for j, t0 in self._entradas.items()):
                return True
        if self._indice >= 0 and self._efectivas()[self._indice]["pausa"]:
            return True
        # el fundido de la traducción también necesita repintar mientras dura
        if self._traduccion_actual() is not None and ahora - self._t_linea < DURACION_TRADUCCION:
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
        original = estilos.original()             # la de siempre: su letra propia, no la elegida
        caligrafia = not original and tipografia_letra.actual() in tipografia_letra.SIN_MAYUSCULAS
        for k, palabra in enumerate(palabras):
            es = (k == fuerte)
            f = fuente_impacto(int(round(tam * FACTOR_FUERTE)) if es else int(round(tam)))
            if not original:
                f = tipografia_letra.adaptar(f)
            m = QFontMetricsF(f)
            texto = palabra.upper() if es and not caligrafia else palabra
            if original:
                subida, bajada = m.ascent(), m.descent()
            else:
                subida, bajada = tipografia_letra.subida_bajada(f)
            medidas.append((texto, es, f, subida, bajada, m.horizontalAdvance(texto)))
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

    def _ajustar(self, palabras, con_traduccion=False):
        """(medidas, filas, tamaño, cabe): el mayor tamaño que deja el bloque dentro del 92% del
        ancho y el 70% del alto, con 4 filas como máximo. cabe=False si ni al tamaño mínimo.
        Con con_traduccion se deja sitio debajo para la fila de la traducción."""
        fuerte = palabra_fuerte(palabras)
        area = self._area()
        ancho_max = ANCHO_MAX * self.width()
        alto_max = ALTO_MAX * self.height()
        tam = max(TAM_MIN, min(TAM_MAX, area.height() * 0.42))
        while True:
            medidas = self._medir(palabras, fuerte, tam)
            filas = self._partir_en_filas(medidas, tam, ancho_max)
            bw, bh = self._tamano_bloque(medidas, filas, tam)
            reserva = tam * (GAP_TRADUCCION + TAM_TRADUCCION * ALTO_LINEA_TRADUCCION) \
                if con_traduccion else 0.0
            if len(filas) <= MAX_FILAS and bw <= ancho_max and bh + reserva <= alto_max:
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
        con_trad = self._traduccion_de(entrada["orig"]) is not None
        medidas, filas, tam, _ = self._ajustar(palabras, con_trad)
        bw, bh = self._tamano_bloque(medidas, filas, tam)
        area = self._area()
        separacion = tam * GAP_PALABRAS
        y = area.top() + max(0.0, (area.height() - bh) / 2.0)
        contorno_linea = (entrada["orig"] % 2 == 1)
        marco = QRectF(area.left(), y, bw, bh)
        con_capas = self._estilo in estilos.ESTILOS_CAPAS
        # la clásica con las tipografías de siempre se pinta exactamente igual que siempre
        como_siempre = self._estilo == "clasica" and tipografia_letra.actual() in tipografia_letra.DE_SIEMPRE
        fina = tipografia_letra.actual() in tipografia_letra.FINAS
        enlazada = tipografia_letra.actual() in tipografia_letra.ENLAZADAS
        items = []
        for fila in filas:
            asc = max(medidas[k][3] for k in fila)
            desc = max(medidas[k][4] for k in fila)
            x = area.left()
            for k in fila:
                texto, es, f, _, _, ancho = medidas[k]
                trazo = QPainterPath()
                hueca = contorno_linea and not es and not fina     # (una fuente finísima no tiene hueco que enseñar)
                if not como_siempre:
                    trazo.setFillRule(Qt.WindingFill)    # en las letras enlazadas no quedan huecos donde se pisan
                trazo.addText(QPointF(x, y + asc), f, texto)
                if self._estilo in ("nitida", "neon") or (hueca and enlazada and not con_capas and not como_siempre):
                    trazo = trazo.simplified()    # sin contornos solapados: el borde no raya el interior
                rect = QRectF(x, y, ancho, asc + desc)
                item = _Item(k, trazo, rect, es, hueca, tam=f.pixelSize())
                if con_capas:
                    item.medida = estilos.Medida(marco, y + asc, *estilos.alturas(f), estilos.grosor_borde(f))
                items.append(item)
                x += ancho + separacion
            y += asc + desc + tam * GAP_FILAS
        ms_palabras = []
        if entrada["ms"] is not None:
            ms_palabras = [ms for _, ms in repartir_palabras(entrada["texto"], entrada["ms"],
                                                             entrada["canto"])]
        return _Disposicion("palabras", items, ms_palabras, tam=tam)

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
        estilo = self._estilo
        mov = estilos.movimiento()
        if mov == "latido" and entradas is not None and disp.items:
            # la línea entera late un poco con el golpe de la música (desde su centro)
            caja = disp.items[0].rect
            for it in disp.items[1:]:
                caja = caja.united(it.rect)
            s = 1.0 + 0.022 * min(1.0, self._golpe) + 0.008 * math.sin(ahora * 2.4)
            p.save()
            p.translate(caja.center().x(), caja.center().y() + dy)
            p.scale(s, s)
            p.translate(-caja.center().x(), -caja.center().y() - dy)
            try:
                self._pintar_items_movidos(p, disp, entradas, ahora, dy, opacidad, color_fuerte, estilo, mov)
            finally:
                p.restore()
            return
        self._pintar_items_movidos(p, disp, entradas, ahora, dy, opacidad, color_fuerte, estilo, mov)

    def _pintar_items_movidos(self, p, disp, entradas, ahora, dy, opacidad, color_fuerte, estilo, mov):
        ultima = None                             # la que acaba de entrar (para el brillo)
        if entradas is not None and mov == "brillo":
            llegadas = [(t, i) for i, t in entradas.items() if t is not None]
            if llegadas:
                ultima = max(llegadas)[1]
        # la palabra que suena: la última que ha entrado de la línea actual (neón y simple)
        sonando = None
        if entradas is not None and estilo in ("neon", "simple", "marcador"):
            llegadas = [(entradas[it.indice], it.indice) for it in disp.items
                        if entradas.get(it.indice) is not None]
            if llegadas:
                sonando = max(llegadas)[1]
        self._sonando_ahora = sonando
        if estilo == "marcador" and sonando is not None:
            # el resaltador va detrás de TODAS las palabras: no puede tapar la fila de arriba
            for it in disp.items:
                if it.indice == sonando:
                    self._pintar_resaltador(p, it, ahora - entradas[sonando], dy, opacidad)
        for it in disp.items:
            escala = 1.0
            dx = 0.0
            alfa = 1.0
            if entradas is not None:
                t0 = entradas.get(it.indice)
                if t0 is None:
                    if estilo == "contorno":      # la que viene se ve hueca, esperando su turno
                        espera = OPACIDAD_POR_CANTAR * min(1.0, (ahora - self._t_linea) / DURACION_POR_CANTAR)
                        self._pintar_capa(p, it, "base", 0.0, dy, opacidad * espera)
                    continue                      # aún no ha llegado su instante
                t = (ahora - t0) / DURACION_ENTRADA
                if t < 1.0:
                    e = _ease_out_back(t)
                    escala = 1.25 - 0.25 * e
                    dx = 30.0 * (1.0 - e)
                    alfa = 1.0 - (1.0 - max(0.0, t)) ** 2
                    if estilo == "contorno":      # ya se veía hueca en su sitio: solo un pequeño latido
                        escala, dx, alfa = 1.0 + 0.07 * math.sin(math.pi * max(0.0, t)), 0.0, 1.0
                    elif estilo == "marcador":    # el resaltador llega por la izquierda; la palabra, quieta
                        escala, dx = 1.0, 0.0
            sube = 0.0
            eco = None
            if entradas is not None and entradas.get(it.indice) is not None and estilo not in ("contorno", "marcador"):
                tt = ahora - entradas[it.indice]
                if mov in ("suave", "ola"):
                    dur = 0.42 if mov == "suave" else 0.55
                    e = _ease_out_cubic(tt / dur) if tt < dur else 1.0
                    escala, dx, alfa = 1.0, 0.0, e
                    sube = (1.0 - e) * disp.tam * (0.22 if mov == "suave" else 0.45)
                elif mov == "eco" and tt < 0.7:
                    eco = 1.0 - tt / 0.7
                elif mov in ("brillo", "latido") and tt < DURACION_ENTRADA:
                    e = _ease_out_cubic(tt / DURACION_ENTRADA)        # entra sin el rebote de la clásica
                    escala, dx = 1.08 - 0.08 * e, 14.0 * (1.0 - e)
            if mov == "ola" and entradas is not None:
                sube += math.sin(ahora * 2.0 + it.indice * 0.8) * disp.tam * 0.025
            if alfa <= 0.0:
                continue
            if eco:
                # dos copias que se quedan atrás y se apagan: el eco de la palabra
                for paso in (2, 1):
                    self._pintar_una(p, disp, it, entradas, ahora, escala, dx - paso * disp.tam * 0.16 * eco, dy,
                                     opacidad * alfa * 0.22 * eco * (3 - paso) / 2, color_fuerte, estilo, None)
            if ultima == it.indice:
                self._pintar_halo_palabra(p, it, dy, opacidad * alfa, color_fuerte, ahora - entradas[it.indice])
            self._pintar_una(p, disp, it, entradas, ahora, escala, dx, dy - sube, opacidad * alfa, color_fuerte,
                             estilo, None)

    def _pintar_halo_palabra(self, p, it, dy, opacidad, color, desde):
        """Brillo suave detrás de la palabra que suena: crece al entrar y se queda respirando."""
        k = max(0.5, it.tam / 60.0) if it.tam else 1.0
        fuerza = min(1.0, desde / 0.25) * (0.75 + 0.25 * math.sin(desde * 3.0))
        p.save()
        p.translate(0, dy)
        p.setBrush(Qt.NoBrush)
        col = QColor(color)
        for ancho, a in ((26, 22), (14, 40)):
            col.setAlpha(int(a * fuerza * opacidad))
            p.setPen(QPen(col, ancho * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(it.trazo)
        p.restore()

    def _pintar_una(self, p, disp, it, entradas, ahora, escala, dx, dy, opacidad_total, color_fuerte, estilo, _x):
        """Una palabra con su escala y desplazamiento (lo de siempre de cada estilo)."""
        sonando = getattr(self, "_sonando_ahora", None)
        alfa = 1.0
        opacidad = opacidad_total
        if True:
            # destello al entrar (nítida): la palabra nace con un brillo que se apaga en la transición
            destello = 0.0
            if estilo == "nitida" and entradas is not None:
                t0 = entradas.get(it.indice)
                if t0 is not None:
                    destello = max(0.0, 1.0 - (ahora - t0) / (DURACION_ENTRADA * 1.6))
            es_sonando = it.indice == sonando
            if estilo in estilos.ESTILOS_CAPAS:
                desde = None if entradas is None else ahora - entradas[it.indice]
                self._pintar_con_capas(p, disp, it, es_sonando, desde, escala, dx, dy, opacidad * alfa)
                return
            tenue = 1.0
            if estilo == "neon" and not es_sonando:
                tenue = OPACIDAD_TENUE_NEON
            elif estilo == "simple" and not es_sonando:
                tenue = OPACIDAD_TENUE_SIMPLE
            p.save()
            p.setOpacity(opacidad * alfa * tenue)
            c = it.rect.center()
            p.translate(c.x() + dx, c.y() + dy)
            p.scale(escala, escala)
            p.translate(-c.x(), -c.y())
            if estilo == "nitida":
                if destello > 0.02:
                    _pintar_palabra(p, it, disp.tam, color_fuerte, destello)
                else:
                    self._pintar_guardada(p, it, "nitida", disp.tam, color_fuerte, escala, False)
            elif estilo == "neon":
                self._pintar_guardada(p, it, "neon", disp.tam, color_fuerte, escala, es_sonando)
            elif estilo == "simple":
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 255, 255))
                p.drawPath(it.trazo)
            elif it.contorno:
                p.setPen(QPen(QColor(255, 255, 255), 1.6))
                p.setBrush(Qt.NoBrush)
                p.drawPath(it.trazo)
            else:
                p.setPen(Qt.NoPen)
                p.setBrush(color_fuerte if it.fuerte else TEXTO)
                p.drawPath(it.trazo)
            p.restore()

    def _relleno_s(self, disp, j):
        """Segundos que tarda en rellenarse la palabra j (contorno): hasta que entra la siguiente."""
        ms = disp.ms_palabras
        if j + 1 < len(ms):
            return max(RELLENO_MIN, min(RELLENO_MAX, (ms[j + 1] - ms[j]) / 1000.0))
        return 0.45

    def _capa(self, it, capa):
        """La imagen de una palabra en una capa; se pinta la primera vez que hace falta."""
        capa = estilos.capa_real(self._estilo, capa)
        dpr = self.devicePixelRatioF() or 1.0
        hecha = it.capas.get(capa)
        if hecha is None or hecha[0].devicePixelRatio() != dpr:
            hecha = estilos.imagen_capa(it.trazo, it.tam, self._estilo, capa, self._colores_letra(),
                                        it.medida, dpr)
            it.capas[capa] = hecha
        return hecha

    def _resaltador(self, it, desde):
        """(cuánto avanzó 0..1, la pastilla ahora mismo) del resaltador de una palabra."""
        u = _ease_out_cubic(desde / DURACION_MARCADOR)
        r = estilos.rect_pastilla(it.trazo.boundingRect(), it.medida, it.tam)
        r.setWidth(r.width() * u)
        return u, r

    def _pintar_resaltador(self, p, it, desde, dy, opacidad):
        _u, r = self._resaltador(it, desde)
        antes = p.opacity()
        p.setOpacity(antes * opacidad)
        estilos.pintar_pastilla(p, r.translated(0, round(dy)), self._colores_letra(), it.tam)
        p.setOpacity(antes)

    def _pintar_capa(self, p, it, capa, dx, dy, opacidad, hasta=None, desde_x=None):
        """Copia la imagen de la palabra en su sitio (entera, hasta la x `hasta` o desde la x `desde_x`)."""
        img, en = self._capa(it, capa)
        antes = p.opacity()
        p.setOpacity(antes * opacidad)
        en = QPointF(round(en.x() + dx), round(en.y() + dy))
        if desde_x is not None:
            p.save()
            p.setClipRect(QRectF(desde_x + dx, en.y(), img.width(), img.height()))
            p.drawImage(en, img)
            p.restore()
        elif hasta is None:
            p.drawImage(en, img)
        else:
            estilos.dibujar_hasta(p, img, en, hasta + dx, it.tam * 0.10)
        p.setOpacity(antes)

    def _pintar_con_capas(self, p, disp, it, es_sonando, desde, escala, dx, dy, opacidad):
        """Una palabra de los estilos de ui/estilo_letra.py. `desde`: segundos desde que entró (None = la
        línea que ya se va)."""
        estilo = self._estilo
        p.save()
        if abs(escala - 1.0) > 0.001:
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            c = it.rect.center()
            p.translate(c.x() + dx, c.y() + dy)
            p.scale(escala, escala)
            p.translate(-c.x(), -c.y())
            dx = dy = 0.0
        if estilo == "marcador":
            if es_sonando and desde is not None:
                # el texto se vuelve oscuro por donde ya pasó el resaltador
                u, r = self._resaltador(it, desde)
                if u < 1.0:
                    self._pintar_capa(p, it, "base", dx, dy, opacidad, desde_x=r.right())
                self._pintar_capa(p, it, "viva", dx, dy, opacidad, None if u >= 1 else r.right())
            else:
                self._pintar_capa(p, it, "reposo", dx, dy, opacidad)
        elif estilo == "contorno" and desde is not None:
            u = min(1.0, max(0.0, desde / self._relleno_s(disp, it.indice)))
            if u < 1.0:
                self._pintar_capa(p, it, "base", dx, dy, opacidad)
            caja = it.trazo.boundingRect()
            self._pintar_capa(p, it, "viva", dx, dy, opacidad,
                              None if u >= 1 else caja.left() + caja.width() * u)
        elif estilo == "vhs" and desde is not None and desde < DURACION_GLITCH:
            self._pintar_temblor(p, it, dx, dy, opacidad, 1.0 - max(0.0, desde) / DURACION_GLITCH)
        else:
            self._pintar_capa(p, it, "viva", dx, dy, opacidad)
        p.restore()

    def _pintar_temblor(self, p, it, dx, dy, opacidad, fuerza):
        """VHS: al entrar, la palabra llega cortada en franjas corridas que se van juntando."""
        img, en = self._capa(it, "viva")
        dpr = img.devicePixelRatio()
        w, h = img.width() / dpr, img.height() / dpr
        franjas = 6
        alto = h / franjas
        antes = p.opacity()
        p.setOpacity(antes * opacidad)
        for i in range(franjas):
            corrida = math.sin(i * 2.4 + it.indice * 1.7 + fuerza * 9.0) * it.tam * 0.16 * fuerza
            p.drawImage(QRectF(en.x() + dx + corrida, en.y() + dy + i * alto, w, alto), img,
                        QRectF(0, i * alto * dpr, w * dpr, alto * dpr))
        p.setOpacity(antes)

    def _pintar_guardada(self, p, it, estilo, tam, color, escala, sonando):
        """Nítida y neón: la palabra quieta se pinta una vez en una imagen (sus trazos anchos son caros) y
        luego solo se copia; mientras se agranda o se achica al entrar se pinta al vuelo, nítida."""
        def pintar(q):
            if estilo == "nitida":
                _pintar_palabra(q, it, tam, color)
            else:
                _pintar_palabra_neon(q, it, tam, color, sonando)
        if abs(escala - 1.0) > 0.001:
            pintar(p)
            return
        dpr = self.devicePixelRatioF() or 1.0
        clave = (estilo, color.rgb(), sonando, dpr)
        hecha = it.capas.get(clave)
        if hecha is None:
            margen = math.ceil(16 * max(0.5, tam / 60.0) + 4)
            caja = it.trazo.boundingRect().adjusted(-margen, -margen, margen, margen).toAlignedRect()
            img = QImage(max(1, int(caja.width() * dpr)), max(1, int(caja.height() * dpr)),
                         QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(dpr)
            img.fill(Qt.transparent)
            q = QPainter(img)
            q.setRenderHint(QPainter.Antialiasing, True)
            q.translate(-caja.topLeft())
            pintar(q)
            q.end()
            hecha = (img, QPointF(caja.topLeft()))
            it.capas = {k: v for k, v in it.capas.items() if k[1] == clave[1]}     # otro color: fuera lo viejo
            it.capas[clave] = hecha
        p.drawImage(hecha[1], hecha[0])

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

    def _traduccion_de(self, orig):
        """Traducción de la línea original orig, o None si no tiene."""
        return self._trad[orig] if 0 <= orig < len(self._trad) else None

    def _traduccion_actual(self):
        """Texto traducido de la línea que suena, o None si no hay (o si es una pausa)."""
        if not self._trad or self._indice < 0:
            return None
        entrada = self._efectivas()[self._indice]
        if entrada["pausa"]:
            return None
        return self._traduccion_de(entrada["orig"])

    def _capa_traduccion(self, disp):
        """Qué dibujar de la traducción: (desplazamiento del bloque principal, texto ya recortado,
        fuente, rectángulo). None si no hay traducción o no cabe debajo del bloque."""
        texto = self._traduccion_actual()
        if not texto or not disp.items:
            return None
        area = self._area()
        f = fuente_impacto(max(TAM_MIN_TRADUCCION, int(round(disp.tam * TAM_TRADUCCION))))
        alto_linea = QFontMetricsF(f).height()
        texto = QFontMetrics(f).elidedText(texto, Qt.ElideRight, max(1, int(area.width())))
        bloque_top = min(it.rect.top() for it in disp.items)
        bloque_bottom = max(it.rect.bottom() for it in disp.items)
        separacion = disp.tam * GAP_TRADUCCION
        # el bloque sube solo lo justo para que la traducción quepa en el área
        exceso = bloque_bottom + separacion + alto_linea - area.bottom()
        desplazamiento = -max(0.0, exceso)
        if bloque_top + desplazamiento < 0:
            return None                       # ni subiendo cabe: se omite antes que salirse
        y = bloque_bottom + desplazamiento + separacion
        return desplazamiento, texto, f, QRectF(area.left(), y, area.width(), alto_linea)

    def _pintar_traduccion(self, p, capa, ahora):
        """Texto traducido en blanco translúcido, con fundido al cambiar de línea."""
        _, texto, f, rect = capa
        fundido = min(1.0, max(0.0, (ahora - self._t_linea) / DURACION_TRADUCCION))
        alfa = int(ALFA_TRADUCCION * fundido)
        if alfa <= 0:
            return
        p.save()
        p.setFont(f)
        if self._estilo == "nitida" or self._estilo in estilos.ESTILOS_CAPAS:
            p.setOpacity(alfa / 255.0)
            _texto_legible(p, rect, Qt.AlignLeft | Qt.AlignVCenter, texto, QColor(255, 236, 200),
                           f.pixelSize() or 18)
        else:
            p.setPen(QColor(255, 255, 255, alfa))
            p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, texto)
        p.restore()

    # ----------------------------------------------------------------- letra épica

    def _con_planos(self):
        return bool(self._epica) and self._sincronizada and bool(self._lineas)

    def _t_epica(self):
        """El segundo de la canción con que se montan los planos (la escena adelanta la letra normal para que
        sus transiciones lleguen a tiempo; aquí el golpe es más corto)."""
        return (self._ms - ADELANTO_ESCENA_MS) / 1000.0 + epica.ADELANTO_S

    def _montaje_epico(self):
        if self._montaje is None:
            versos = []
            con_ms = [(i, l) for i, l in enumerate(self._lineas) if l.get("ms") is not None]
            for k, (i, l) in enumerate(con_ms):
                texto = str(l.get("texto") or "").strip()
                if l.get("pausa") or not texto:
                    continue
                sig = con_ms[k + 1][1]["ms"] if k + 1 < len(con_ms) else None
                canto = l.get("canto")
                versos.append((i, texto, int(l["ms"]), canto if canto and canto > 0 else CANTO_POR_DEFECTO, sig))
            self._montaje = epica.Montaje(self._epica, versos, repartir_palabras)
        return self._montaje

    def _lienzo(self):
        alto = self.height() - (34.0 if self._traduccion_actual() else 0.0)
        return epica.Lienzo(self.width(), max(60.0, alto), self.devicePixelRatioF() or 1.0, self._colores_letra(),
                            self._energia, self._golpe)

    def _adelantar_epica(self):
        if self._con_planos() and a_la_vista(self):
            try:
                if self._montaje_epico().adelantar(self._t_epica(), self._lienzo()):
                    self._t_adelanto.start()
            except Exception:  # noqa: BLE001 - un plano raro se verá (o no) a su hora; no tumba la escena
                pass

    def _borde_suave(self, w, h, dpr):
        """Máscara que apaga los bordes: lo que entra enorme no se corta contra el filo de la ventanita."""
        clave = (w, h, dpr)
        if self._mascara_borde is None or self._mascara_borde[0] != clave:
            img = QImage(max(1, int(w * dpr)), max(1, int(h * dpr)), QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(dpr)
            img.fill(QColor(0, 0, 0, 255))
            q = QPainter(img)
            q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            m = max(10.0, min(w, h) * 0.075)
            for a, b, largo in (((0, 0), (w, 0), w), ((0, 0), (0, h), h)):
                g = QLinearGradient(QPointF(*a), QPointF(*b))
                f = min(0.49, m / max(1.0, largo))
                for u, al in ((0.0, 0), (f * 0.5, 120), (f, 255), (1 - f, 255), (1 - f * 0.5, 120), (1.0, 0)):
                    g.setColorAt(u, QColor(0, 0, 0, al))
                q.fillRect(QRectF(0, 0, w, h), QBrush(g))
            q.end()
            self._mascara_borde = (clave, img)
        return self._mascara_borde[1]

    def _pintar_epica(self, p):
        w, h = self.width(), self.height()
        cx = self._lienzo()
        montaje, t = self._montaje_epico(), self._t_epica()
        if not montaje.viva(t):
            if montaje.indice(t) + 1 < len(montaje.planos):
                self._t_adelanto.start()
            return False
        dpr = cx.dpr
        tam = (max(1, int(w * dpr)), max(1, int(h * dpr)))
        if self._lienzo_epica is None or (self._lienzo_epica.width(), self._lienzo_epica.height()) != tam:
            self._lienzo_epica = QImage(tam[0], tam[1], QImage.Format_ARGB32_Premultiplied)
            self._lienzo_epica.setDevicePixelRatio(dpr)
        img = self._lienzo_epica
        img.fill(Qt.transparent)
        q = QPainter(img)
        try:
            q.translate(w / 2.0, cx.h / 2.0)
            algo = montaje.pintar(q, t, cx)
            q.resetTransform()
            q.setOpacity(1.0)
            q.setClipping(False)
            q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            q.drawImage(0, 0, self._borde_suave(w, h, dpr))
        finally:
            q.end()
        p.drawImage(0, 0, img)
        self._t_adelanto.start()
        return algo

    def _pintar_traduccion_epica(self, p, ahora):
        texto = self._traduccion_actual()
        if not texto:
            return
        f = fuente_impacto(max(TAM_MIN_TRADUCCION, min(26, int(self.height() * 0.075))))
        p.save()
        p.setFont(f)
        p.setOpacity(ALFA_TRADUCCION / 255.0 * min(1.0, max(0.0, (ahora - self._t_linea) / DURACION_TRADUCCION)))
        rect = QRectF(PAD, self.height() - 42, max(1.0, self.width() - 2 * PAD), 36)
        texto = QFontMetrics(f).elidedText(texto, Qt.ElideRight, int(rect.width()))
        _texto_legible(p, rect, Qt.AlignCenter, texto, QColor(255, 240, 210), f.pixelSize() or 18)
        p.restore()

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
            if self._con_planos():
                self._vivo = self._pintar_epica(p)
                if self._vivo:
                    self._pintar_traduccion_epica(p, ahora)
                elif 0 <= self._indice < len(ef) and ef[self._indice]["pausa"]:
                    disp = self._disposicion(self._indice)
                    p.translate((self.width() - disp.radio * 7.2) / 2.0 - PAD, 0)
                    self._pintar_pausa(p, disp, ahora, 0.0, 1.0, color_fuerte)
                return

            # línea siguiente, en pequeño; si es pausa o vacía, no se muestra nada
            sig = self._indice + 1
            if 0 <= sig < len(ef) and not ef[sig]["pausa"] and ef[sig]["texto"].strip():
                nitida = self._estilo == "nitida" or self._estilo in estilos.ESTILOS_CAPAS
                f = fuente(16, QFont.DemiBold) if nitida else fuente(15)
                p.setFont(f)
                if not nitida:
                    p.setPen(TEXTO_3)
                ancho = max(1, int(self.width() - 2 * PAD))
                texto = QFontMetrics(f).elidedText(ef[sig]["texto"], Qt.ElideRight, ancho)
                rect_sig = QRectF(PAD, self.height() - PAD - 24, ancho, 24)
                if nitida:
                    _texto_legible(p, rect_sig, Qt.AlignLeft | Qt.AlignVCenter, texto,
                                   QColor(255, 255, 255, 175), 16)
                else:
                    p.drawText(rect_sig, Qt.AlignLeft | Qt.AlignVCenter, texto)

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
                    capa = self._capa_traduccion(disp)
                    desplazamiento = capa[0] if capa else 0.0
                    self._pintar_items(p, disp, self._entradas, ahora, desplazamiento, 1.0,
                                       color_fuerte)
                    if capa:
                        self._pintar_traduccion(p, capa, ahora)
                elif disp.tipo == "pausa":
                    self._pintar_pausa(p, disp, ahora, 0.0, 1.0, color_fuerte)
        finally:
            p.end()
