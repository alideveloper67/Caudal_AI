# -*- coding: utf-8 -*-
"""La escena de escritorio: junta todas las piezas a pantalla completa.

Por qué tantas ventanas: mpv pinta el videoclip en una ventana nativa y Qt no puede dibujar
encima de ella. Así que el fondo (video o carátula viva) es una ventana a pantalla completa
y cada pieza (reloj, tarjeta, letra, lista, buscador, barra y los cuatro bordes) es una
ventanita translúcida propia, «hija» del fondo para quedar siempre encima. Además, cada
ventanita solo ocupa su rincón: componer una capa translúcida de 1920×1080 en cada cuadro
costaría demasiado en un PC modesto.

Dos maneras de abrirla:
- **Pantalla completa** (la normal): todo se puede tocar; Esc sale.
- **Fondo de escritorio**: la escena se pone detrás de los iconos de Windows, como un fondo
  de pantalla vivo. Ahí Windows no deja tocarla, así que solo se ve (sin buscador ni barra)
  y se maneja desde Caudal o con las teclas multimedia.
"""

import time

from PySide6.QtCore import QEvent, QObject, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtWidgets import QStackedLayout, QWidget

from .. import imagenes
from ..video import PantallaNativa
from .barra import BarraMini
from .bordes import BordeBrillo, geometrias_borde
from .buscador import PanelBusqueda
from .estilo import BRILLO, DOMINANTE, SEGUNDO
from .fondo import FondoAmbiente
from .letra import LetraCinetica
from .lista_reciente import ListaSeguir
from .reloj import RelojGigante
from .tarjeta import TarjetaCancion

NOMBRE_VIDEO = "escena"
FUENTE_TEXTO = {
    "auto": "Sonando en Caudal", "ytmusic": "Desde YouTube Music", "youtube": "Desde YouTube",
    "megusta": "Desde tus me gusta", "descargas": "Desde tus descargas",
}


def clave_de(p):
    return (p or {}).get("clave") or (p or {}).get("video_id")


def disposicion(pantalla, solo_ver=False):
    """Dónde va cada pieza en una pantalla (QRect en coordenadas globales).

    Proporcional al alto (diseñado a 1080 px) y con límites para que nada se pise en
    pantallas pequeñas ni quede diminuto en las grandes."""
    x0, y0, W, H = pantalla.x(), pantalla.y(), pantalla.width(), pantalla.height()
    s = max(0.7, min(1.6, H / 1080))
    g = {}
    # lista, barra y buscador tienen medidas internas fijas: van a su tamaño natural
    lista_w, lista_h = 290, min(int(H * 0.62), 620)
    g["lista"] = QRect(x0 + int(26 * s), y0 + int(H * 0.14), lista_w, lista_h)
    reloj_w, reloj_h = int(W * 0.33), int(H * 0.30)
    g["reloj"] = QRect(x0 + W - reloj_w - int(W * 0.04), y0 + int(H * 0.05), reloj_w, reloj_h)
    tar_w, tar_h = int(360 * s), int(520 * s)
    tar_x = x0 + max(lista_w + int(60 * s), int(W * 0.30))
    tar_y = y0 + int(H * 0.27)
    g["tarjeta"] = QRect(tar_x, tar_y, tar_w, tar_h)
    letra_x = tar_x + tar_w + int(10 * s)
    g["letra"] = QRect(letra_x, y0 + int(H * 0.36), max(200, x0 + W - letra_x - int(W * 0.04)),
                       int(H * 0.42))
    barra_w, barra_h = 660, 92
    g["barra"] = QRect(x0 + (W - barra_w) // 2, y0 + H - barra_h - int(12 * s), barra_w, barra_h)
    busc_w = 640
    g["buscador_abajo"] = QRect(x0 + (W - busc_w) // 2, g["barra"].top() - int(4 * s), busc_w, 0)
    # la tarjeta nunca baja hasta el buscador plegado (su campo mide 68 px)
    tope = g["buscador_abajo"].y() - 68 - int(16 * s)
    if g["tarjeta"].bottom() >= tope:
        alto = max(200, tope - g["tarjeta"].top())
        g["tarjeta"].setSize(QSize(int(alto * 360 / 520), alto))
        nuevo_x = g["tarjeta"].right() + int(10 * s)
        g["letra"].setLeft(nuevo_x)
    if solo_ver:
        # sin barra ni buscador: la tarjeta y la letra bajan un poco
        g["tarjeta"].translate(0, int(H * 0.04))
        g["letra"].translate(0, int(H * 0.04))
    g["bordes"] = geometrias_borde(pantalla, int(64 * s))
    return g


class _FondoVentana(QWidget):
    """La ventana de fondo: el videoclip (mpv) o la carátula viva, a pantalla completa."""

    def __init__(self):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Caudal · Escena")
        self.setStyleSheet("background:#000000;")
        self.pila = QStackedLayout(self)
        self.pila.setContentsMargins(0, 0, 0, 0)
        self.ambiente = FondoAmbiente()
        self.pantalla = PantallaNativa()
        self.pila.addWidget(self.ambiente)
        self.pila.addWidget(self.pantalla)

    def ver_video(self, si):
        self.pila.setCurrentIndex(1 if si else 0)


class EscenaEscritorio(QObject):
    """Abre, maneja y cierra la escena. Uno por aplicación (`escena_de(ctx)`)."""

    cerrada = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.r = ctx.reproductor
        self.abierta = False
        self.solo_ver = False
        self.fuente_busqueda = "auto"
        self._modo_previo = None
        self._motor = None
        self._fondo = None
        self._piezas = {}
        self._bordes = {}
        self._colores = (QColor(DOMINANTE), QColor(SEGUNDO), QColor(BRILLO))
        self._lineas_clave = None
        self._alternativas = []
        self._alt_indice = 0
        self._busqueda_gen = 0
        self._reloj_letra = QTimer(self)
        self._reloj_letra.setInterval(33)
        self._reloj_letra.timeout.connect(self._tic_letra)
        self._pos = 0.0
        self._pos_t = time.monotonic()
        self._dur = 0.0

    # ------------------------------------------------------------ abrir / cerrar

    def pantalla_destino(self):
        v = getattr(self.ctx, "ventana", None)
        scr = v.screen() if v is not None else None
        return (scr or QGuiApplication.primaryScreen()).geometry()

    def abrir(self, solo_ver=False):
        if self.abierta:
            self.cerrar()
        self.solo_ver = bool(solo_ver)
        geo = self.pantalla_destino()
        self._crear(geo)
        self.abierta = True
        self._conectar(True)
        self._colores_caratula()
        self._pista(self.r.actual)
        self._estado(self.r.estado)
        self._preparar_video()
        self._recientes()
        self._reloj_letra.start()
        if self.solo_ver:
            from . import escritorio_win
            hwnd = int(self._fondo.winId())
            if not escritorio_win.incrustar_como_fondo(hwnd):
                self.cerrar()
                self.ctx.avisar("Windows no dejó poner la escena como fondo; se abrió a pantalla completa.")
                self.abrir(solo_ver=False)
                return
        self._mostrar_piezas()
        # solo en las ventanas de la escena (y el campo del buscador, que tiene el foco al escribir)
        for w in self._ventanas():
            w.installEventFilter(self)
        if "buscador" in self._piezas:
            self._piezas["buscador"]._campo.installEventFilter(self)

    def _ventanas(self):
        return [self._fondo] + list(self._piezas.values()) + list(self._bordes.values())

    def eventFilter(self, obj, ev):
        """Esc y Espacio valen en cualquiera de las ventanitas de la escena (los atajos de Qt solo
        actúan en la ventana activa, y aquí son once). En el buscador, Esc primero limpia lo que
        haya (texto, resultados o el menú) y Espacio escribe."""
        if ev.type() != QEvent.KeyPress or not self.abierta or self.solo_ver:
            return False
        if not isinstance(obj, QWidget) or obj.window() not in self._ventanas():
            return False
        tecla = ev.key()
        busc = self._piezas.get("buscador")
        en_buscador = busc is not None and obj.window() is busc
        if tecla == Qt.Key_Escape:
            if en_buscador and (busc._campo.text() or busc.altura_deseada() > 80):
                return False
            QTimer.singleShot(0, self.cerrar)
            return True
        if tecla == Qt.Key_Space and not en_buscador:
            self.r.alternar()
            return True
        return False

    def _crear(self, geo):
        self._fondo = _FondoVentana()
        self._fondo.setGeometry(geo)
        if self.solo_ver:
            self._fondo.show()
        else:
            self._fondo.showFullScreen()
        g = disposicion(geo, self.solo_ver)
        banderas = Qt.Tool | Qt.FramelessWindowHint
        origen = geo.topLeft()

        def colocar(w, rect, extra=Qt.WindowType(0)):
            if self.solo_ver:
                # detrás de los iconos todo va en UNA ventana opaca (la del fondo): unas ventanas
                # propias quedarían flotando encima de las demás apps, no detrás
                w.setParent(self._fondo)
                w.setGeometry(rect.translated(-origen))
            else:
                w.setParent(self._fondo, banderas | extra)
                w.setGeometry(rect)

        def pieza(nombre, w, rect):
            colocar(w, rect)
            self._piezas[nombre] = w
            return w

        pieza("reloj", RelojGigante(), g["reloj"])
        pieza("tarjeta", TarjetaCancion(), g["tarjeta"])
        pieza("letra", LetraCinetica(), g["letra"])
        pieza("lista", ListaSeguir(), g["lista"])
        if not self.solo_ver:
            barra = pieza("barra", BarraMini(), g["barra"])
            busc = pieza("buscador", PanelBusqueda(), QRect(g["buscador_abajo"]))
            self._abajo_buscador = g["buscador_abajo"]
            busc.fijar_fuente(self.fuente_busqueda)
            busc.cambio_tamano.connect(self._colocar_buscador)
            busc.buscar.connect(self._buscar)
            busc.elegida.connect(self._elegir)
            busc.artista.connect(self._artista)
            busc.fuente_cambiada.connect(self._fuente_cambiada)
            barra.anterior.connect(self.r.anterior)
            barra.alternar.connect(self.r.alternar)
            barra.siguiente.connect(self.r.siguiente)
            barra.aleatorio.connect(self.r.alternar_aleatorio)
            barra.repetir.connect(self._alternar_repetir)
            barra.buscar_pos.connect(lambda f: self._dur and self.r.buscar(f * self._dur))
            barra.cambiar_fondo.connect(self._alternar_fondo)
            barra.abrir_caudal.connect(self._abrir_caudal)
            barra.salir.connect(self.cerrar)
            self._colocar_buscador()
        t = self._piezas["tarjeta"]
        t.pidio_me_gusta.connect(self._me_gusta)
        t.pidio_otra_letra.connect(self._otra_letra)
        self._piezas["lista"].elegida.connect(self._elegir)
        for lado, rect in g["bordes"].items():
            b = BordeBrillo(lado)
            colocar(b, rect, Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
            self._bordes[lado] = b

    def _mostrar_piezas(self):
        for b in self._bordes.values():
            b.show()
        for w in self._piezas.values():
            w.show()
            w.raise_()
        if "buscador" in self._piezas:
            self._piezas["buscador"].raise_()

    def cerrar(self):
        if not self.abierta:
            return
        self.abierta = False
        self._reloj_letra.stop()
        self._conectar(False)
        # el video vuelve a la vista de Caudal (o al modo canción si lo pusimos nosotros)
        self.r.tope_video = None
        if self.r.destino_video == NOMBRE_VIDEO:
            self.r.mover_video("principal")
        if self._modo_previo is not None and self._modo_previo != self.r.modo:
            self.r.cambiar_modo(self._modo_previo)
        self._modo_previo = None
        if self._motor is not None:
            self.r.soltar_video(NOMBRE_VIDEO)
            self._motor = None
        if self.solo_ver and self._fondo is not None:
            from . import escritorio_win
            escritorio_win.soltar_de_fondo(int(self._fondo.winId()))
        for w in list(self._piezas.values()) + list(self._bordes.values()):
            w.close()
            w.deleteLater()
        self._piezas.clear()
        self._bordes.clear()
        if self._fondo is not None:
            self._fondo.close()
            self._fondo.deleteLater()
            self._fondo = None
        self.cerrada.emit()

    # ------------------------------------------------------------ señales del reproductor

    def _conectar(self, si):
        pares = [(self.r.pista_cambio, self._pista), (self.r.estado_cambio, self._estado),
                 (self.r.posicion_cambio, self._posicion), (self.r.duracion_cambio, self._duracion),
                 (self.r.modo_cambio, self._modo)]
        cc = getattr(self.ctx, "colores_caratula", None)
        if cc is not None:
            pares.append((cc.cambio, self._colores_caratula))
        mg = getattr(self.ctx, "me_gusta_cambio", None)
        if mg is not None:
            pares.append((mg, self._me_gusta_cambio))
        for senal, slot in pares:
            try:
                senal.connect(slot) if si else senal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def _pista(self, p):
        if not self.abierta:
            return
        clave = clave_de(p)
        datos = dict(p or {})
        if p:
            datos["fuente_texto"] = FUENTE_TEXTO.get(self.fuente_busqueda, FUENTE_TEXTO["auto"])
        self._piezas["tarjeta"].poner(datos if p else None)
        self._piezas["tarjeta"].fijar_me_gusta(bool(clave) and self.ctx.coleccion.me_gusta(clave))
        if "barra" in self._piezas:
            self._piezas["barra"].poner(p)
        self._piezas["lista"].marcar_actual(clave)
        url = (p or {}).get("miniatura") or ""
        if url:
            imagenes.imagen(url, lambda img, c=clave: self._portada(c, img))
        else:
            self._portada(clave, QImage())
        self._pedir_letra(p)
        self._recientes()
        self._preparar_video()

    def _portada(self, clave, img):
        if not self.abierta or clave != clave_de(self.r.actual):
            return
        self._piezas["tarjeta"].poner_portada(img)
        if "barra" in self._piezas:
            self._piezas["barra"].poner_portada(img)
        self._fondo.ambiente.poner_portada(img)

    def _estado(self, e):
        if not self.abierta:
            return
        if "barra" in self._piezas:
            self._piezas["barra"].fijar_estado(e)
            self._piezas["barra"].fijar_aleatorio(bool(self.r.aleatorio))
            self._piezas["barra"].fijar_repetir(self.r.repetir or "no")
        self._pos_t = time.monotonic()

    def _posicion(self, s):
        self._pos = float(s or 0)
        self._pos_t = time.monotonic()
        if not self.abierta:
            return
        if "barra" in self._piezas:
            self._piezas["barra"].fijar_progreso(self._pos, self._dur)
        if self._dur:
            self._piezas["tarjeta"].fijar_progreso(self._pos / self._dur)

    def _duracion(self, d):
        self._dur = float(d or 0)

    def _modo(self, _m):
        if self.abierta:
            self._fondo.ver_video(self.r.modo == "video" and self.r.destino_video == NOMBRE_VIDEO)
            if "barra" in self._piezas:
                self._piezas["barra"].fijar_fondo("video" if self.r.modo == "video" else "ambiente")

    def _colores_caratula(self):
        if not self.abierta:
            return
        cc = getattr(self.ctx, "colores_caratula", None)
        if cc is None:
            from ...paleta_caratula import colores_de
            cc = colores_de(self.ctx)
            try:
                cc.cambio.connect(self._colores_caratula)
            except (RuntimeError, TypeError):
                pass
        # con beneficios: los colores de la carátula; sin ellos, los de Caudal (mezcla que hace el gestor)
        try:
            colores = cc.colores()
        except Exception:  # noqa: BLE001
            colores = list(self._colores)
        d, s, b = (QColor(c) for c in colores[:3])
        self._colores = (d, s, b)
        for w in list(self._piezas.values()) + list(self._bordes.values()) + [self._fondo.ambiente]:
            w.poner_colores(d, s, b)

    # ------------------------------------------------------------ fondo de video

    def _preparar_video(self):
        """El videoclip de fondo si se puede; si no, la carátula viva."""
        if not self.abierta:
            return
        if self.ctx.ajustes.get("escena_fondo", "video") != "video" or not self.r.disponible:
            self._fondo.ver_video(False)
            return
        p = self.r.actual
        if not p or not p.get("video_id") or (p.get("archivo") and p.get("es_audio")):
            self._fondo.ver_video(False)
            return
        # el videoclip es solo el fondo (con todo encima): 720p basta y ahorra mucho procesador
        self.r.tope_video = 720
        if self._motor is None:
            self._motor = self.r.registrar_video(NOMBRE_VIDEO, int(self._fondo.pantalla.winId()))
        if self.r.modo != "video":
            if self._modo_previo is None:
                self._modo_previo = self.r.modo
            self.r.destino_video = NOMBRE_VIDEO
            self.r.cambiar_modo("video")
        elif self.r.destino_video != NOMBRE_VIDEO:
            if self._modo_previo is None:
                self._modo_previo = "video"
            self.r.mover_video(NOMBRE_VIDEO)
        self._fondo.ver_video(True)

    def _alternar_fondo(self):
        actual = self.ctx.ajustes.get("escena_fondo", "video")
        nuevo = "ambiente" if actual == "video" else "video"
        self.ctx.ajustes["escena_fondo"] = nuevo
        self.ctx.ajustes.guardar()
        if nuevo == "ambiente":
            self.r.tope_video = None
            if self.r.destino_video == NOMBRE_VIDEO:
                self.r.mover_video("principal")
            if self._modo_previo is not None and self._modo_previo != self.r.modo:
                self.r.cambiar_modo(self._modo_previo)
            self._modo_previo = None
            self._fondo.ver_video(False)
        else:
            self._preparar_video()
        if "barra" in self._piezas:
            self._piezas["barra"].fijar_fondo(nuevo)

    # ------------------------------------------------------------ letra

    def _pedir_letra(self, p):
        from ...catalogo import letras
        from ...hilos import en_segundo_plano
        letra = self._piezas["letra"]
        clave = clave_de(p)
        self._lineas_clave = clave
        self._alternativas, self._alt_indice = [], 0
        if not p:
            letra.poner_lineas([], False)
            letra.poner_mensaje("Pon algo a sonar para ver su letra.")
            return
        letra.poner_lineas([], False)
        letra.poner_mensaje("Buscando la letra…")
        en_segundo_plano(letras, p, ok=lambda d, c=clave: self._llego_letra(c, d),
                         error=lambda _e, c=clave: self._sin_letra(c, "No se pudo conseguir la letra."),
                         dueno=self)

    def _llego_letra(self, clave, datos):
        if not self.abierta or clave != self._lineas_clave:
            return
        from ..letra_viva import preparar_lineas
        lineas, sinc = preparar_lineas(datos or {})
        letra = self._piezas["letra"]
        if not lineas:
            self._sin_letra(clave, "No hay letra para esta canción.")
            return
        letra.poner_mensaje("")
        letra.poner_lineas(lineas, sinc)

    def _sin_letra(self, clave, texto):
        if self.abierta and clave == self._lineas_clave:
            self._piezas["letra"].poner_lineas([], False)
            self._piezas["letra"].poner_mensaje(texto)

    def _otra_letra(self):
        """Pasa a la siguiente letra que encuentre LRCLIB para esta canción."""
        p = self.r.actual
        if not p:
            return
        if self._alternativas:
            self._alt_indice = (self._alt_indice + 1) % len(self._alternativas)
            self._poner_alternativa()
            return
        from ...catalogo import letras_alternativas
        from ...hilos import en_segundo_plano
        clave = clave_de(p)
        self._piezas["letra"].poner_mensaje("Buscando otras letras…")

        def llegaron(lista, c=clave):
            if not self.abierta or c != self._lineas_clave:
                return
            if not lista:
                self._piezas["letra"].poner_mensaje("")
                self.ctx.avisar("No encontré otra letra para esta canción.")
                return
            self._alternativas, self._alt_indice = lista, 0
            self._poner_alternativa()

        en_segundo_plano(letras_alternativas, p, ok=llegaron,
                         error=lambda _e: self.abierta and self._piezas["letra"].poner_mensaje(""),
                         dueno=self)

    def _poner_alternativa(self):
        datos = self._alternativas[self._alt_indice]
        self._llego_letra(self._lineas_clave, datos)
        total = len(self._alternativas)
        self.ctx.avisar(f"Letra {self._alt_indice + 1} de {total}: {datos.get('etiqueta', '')}".strip())

    def _tic_letra(self):
        """La letra avanza con un reloj propio entre aviso y aviso de posición (llegan cada
        ~250 ms), para que las palabras entren justo a tiempo."""
        if not self.abierta or "letra" not in self._piezas:
            return
        pos = self._pos
        if self.r.estado == "sonando":
            pos += time.monotonic() - self._pos_t
        self._piezas["letra"].fijar_ms(int(pos * 1000))

    # ------------------------------------------------------------ lista, búsqueda y acciones

    def _recientes(self):
        if not self.abierta:
            return
        try:
            pistas = self.ctx.coleccion.escuchado_hace_poco(30)
        except Exception:  # noqa: BLE001
            pistas = []
        self._piezas["lista"].poner(pistas)
        self._piezas["lista"].marcar_actual(clave_de(self.r.actual))

    def _colocar_buscador(self):
        b = self._piezas.get("buscador")
        if b is None:
            return
        alto = max(60, int(b.altura_deseada()))
        abajo = self._abajo_buscador
        b.setGeometry(abajo.x(), abajo.y() - alto, abajo.width(), alto)   # crece hacia arriba

    def _fuente_cambiada(self, clave):
        self.fuente_busqueda = clave

    def _buscar(self, texto, fuente):
        from ...hilos import en_segundo_plano
        self.fuente_busqueda = fuente
        self._busqueda_gen += 1
        gen = self._busqueda_gen
        try:
            self.ctx.coleccion.anotar_busqueda(texto)
        except Exception:  # noqa: BLE001
            pass
        en_segundo_plano(buscar_en_fuente, self.ctx.coleccion, texto, fuente,
                         ok=lambda res, g=gen: self._resultados(g, res),
                         error=lambda e, g=gen: self._error_busqueda(g, e), dueno=self)

    def _resultados(self, gen, res):
        if self.abierta and gen == self._busqueda_gen and "buscador" in self._piezas:
            canciones, artistas = res
            self._piezas["buscador"].mostrar_resultados(canciones, artistas)
            if not canciones and not artistas:
                self._piezas["buscador"].mostrar_error("No encontré nada con eso.")

    def _error_busqueda(self, gen, _e):
        if self.abierta and gen == self._busqueda_gen and "buscador" in self._piezas:
            self._piezas["buscador"].mostrar_error("No se pudo buscar. Revisa tu internet.")

    def _elegir(self, pista):
        if pista:
            self.ctx.reproducir_pista(pista)

    def _artista(self, artista):
        """Suena la radio del artista sin salir de la escena."""
        from ...catalogo import buscar
        from ...hilos import en_segundo_plano
        nombre = artista.get("titulo") or artista.get("nombre") or ""
        if not nombre:
            return
        en_segundo_plano(buscar, nombre, "canciones", 25,
                         ok=lambda pistas: pistas and self.ctx.reproducir_lista(
                             pistas, 0, {"tipo": "artista", "id": artista.get("id") or nombre,
                                         "titulo": nombre, "miniatura": artista.get("miniatura") or ""}),
                         dueno=self)

    def _me_gusta(self):
        p = self.r.actual
        if p:
            self.ctx.alternar_me_gusta(p)

    def _me_gusta_cambio(self, clave, si):
        if self.abierta and clave == clave_de(self.r.actual):
            self._piezas["tarjeta"].fijar_me_gusta(bool(si))

    def _alternar_repetir(self):
        f = getattr(self.r, "alternar_repetir", None) or getattr(self.r, "ciclar_repetir", None)
        if f is not None:
            f()
        if "barra" in self._piezas:
            self._piezas["barra"].fijar_repetir(self.r.repetir or "no")

    def _abrir_caudal(self):
        self.cerrar()
        v = getattr(self.ctx, "ventana", None)
        if v is not None:
            v.showNormal() if v.isMinimized() else v.show()
            v.raise_()
            v.activateWindow()


def buscar_en_fuente(coleccion, texto, fuente):
    """(canciones, artistas) para el buscador de la escena, según la fuente elegida.

    Todo lo que suena en Caudal sale de YouTube; «Automático» y «YouTube Music» buscan
    canciones del catálogo de YouTube Music, «Videos de YouTube» busca videos, y las dos
    últimas buscan solo en lo tuyo (sin internet)."""
    from ... import catalogo
    texto = (texto or "").strip()
    if not texto:
        return [], []
    if fuente in ("megusta", "descargas"):
        t = texto.lower()
        if fuente == "megusta":
            pistas = coleccion.lista_me_gusta(filtro=texto) or [
                p for p in coleccion.lista_me_gusta() if t in (p.get("titulo", "") + " " + p.get("artista", "")).lower()]
        else:
            pistas = []
            for d in coleccion.biblioteca(filtro=texto) if hasattr(coleccion, "biblioteca") else []:
                pistas.append(d)
        return list(pistas)[:8], []
    filtro = "videos" if fuente == "youtube" else "canciones"
    canciones = catalogo.buscar(texto, filtro, 8)
    artistas = [] if fuente == "youtube" else catalogo.buscar(texto, "artistas", 5)
    return canciones, artistas


_ESCENAS = {}


def escena_de(ctx):
    e = getattr(ctx, "escena_escritorio", None)
    if e is None:
        e = EscenaEscritorio(ctx, ctx)
        ctx.escena_escritorio = e
    return e
