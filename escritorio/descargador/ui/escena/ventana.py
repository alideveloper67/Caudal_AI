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

import os
import time

from PySide6.QtCore import QEvent, QObject, QPropertyAnimation, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from .. import imagenes
from ..video import PantallaNativa
from .barra import ALTO as ALTO_BARRA, ANCHO as ANCHO_BARRA, BarraMini
from .bordes import BordeBrillo, geometrias_borde
from .buscador import PanelBusqueda
from . import editable
from .estilo import BRILLO, DOMINANTE, SEGUNDO
from .fondo import FondoAmbiente
from . import escenarios
from .letra import LetraCinetica
from .lista_reciente import ListaSeguir
from .reloj import RelojGigante
from .tarjeta import TarjetaCancion
from ..sincronia_auto import sincronia_de

# La línea entra con una transición de ~0,4 s y cada palabra en ~0,3 s: se adelanta la animación para que
# llegue a su sitio justo cuando se canta (si no, se siente tarde aunque el tiempo sea exacto).
ADELANTO_LETRA_MS = 220
FONDOS_LIBRES = ("video", "ambiente")    # el resto (escenarios, imagen o GIF propios) es de donadores
MAX_EXTRAPOLAR_S = 0.9         # sin avisos de posición más tiempo que esto, la letra espera
SALTO_LETRA_MS = 1500          # desajuste a partir del cual la letra salta (búsqueda, cambio de modo)
PASO_DESFASE_MS = 250       # Ctrl+← / Ctrl+→ en la escena: letra antes / después

# piezas que la persona puede mover, agrandar y ocultar, con su tamaño mínimo (px)
MINIMOS_PIEZA = {"reloj": (220, 90), "tarjeta": (180, 240), "letra": (260, 120), "lista": (220, 200),
                 "barra": (560, 92)}

DURACION_AVISO_MS = 4000    # cuánto se queda el aviso de pieza oculta
DURACION_FADE_MS = 200      # aparición y desvanecido del aviso

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
    barra_w, barra_h = ANCHO_BARRA, ALTO_BARRA
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

    doble_clic = None      # f(): la escena lo pone para volver a mostrar la barra oculta

    def mouseDoubleClickEvent(self, ev):
        if self.doble_clic is not None and ev.button() == Qt.LeftButton:
            self.doble_clic()
        ev.accept()

    def __init__(self):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Caudal · Escena")
        self.setStyleSheet("background:#000000;")
        self.pila = QStackedLayout(self)
        self.pila.setContentsMargins(0, 0, 0, 0)
        self.ambiente = FondoAmbiente()
        self.pantalla = PantallaNativa()
        self.escenario = None             # el escenario animado elegido (se crea al elegirlo)
        self.clave_escenario = None
        self.pila.addWidget(self.ambiente)
        self.pila.addWidget(self.pantalla)

    def ver_video(self, si):
        self.pila.setCurrentIndex(1 if si else 0)

    def ver_escenario(self, clave, forzar=False):
        """Pone el escenario `clave` (synthwave, cyberpunk…). False si no se pudo cargar.
        Con `forzar`, lo vuelve a crear aunque sea la misma clave (p. ej. «Mi imagen» con imagen nueva)."""
        if forzar or self.clave_escenario != clave or self.escenario is None:
            nuevo = escenarios.crear(clave)
            if nuevo is None:
                return False
            if self.escenario is not None:
                self.pila.removeWidget(self.escenario)
                self.escenario.deleteLater()
            self.escenario, self.clave_escenario = nuevo, clave
            self.pila.addWidget(nuevo)
        self.pila.setCurrentWidget(self.escenario)
        return True


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
        self._editables = {}
        self._aviso = None             # QLabel del aviso de pieza oculta (uno a la vez)
        self._anim_aviso = None
        self._timer_aviso = None
        self._forzar_propia = False    # «Mi imagen» con imagen nueva: recrear el escenario
        self._escenario_negado = False # el fondo guardado es un escenario y se puso la carátula (sin donador)
        self._fondo_pendiente = None   # el fondo de donador que se tocó mientras se pregunta al servidor
        self._esperando_donador = False
        self._dur_letra = 0.0
        self._ms_mostrado = None       # último instante de letra mostrado (reloj suave)
        self._lineas_actuales = []
        self._traducciones = None
        self._traduciendo = False
        self._recom_clave = None
        self._modelo_audio = None
        self._t_ondas = None
        self._reloj_letra = QTimer(self)
        self._reloj_letra.setInterval(33)
        self._reloj_letra.timeout.connect(self._tic_letra)
        self._pos = 0.0
        self._pos_t = time.monotonic()
        self._dur = 0.0

    # ------------------------------------------------------------ abrir / cerrar

    def pantalla_destino(self, util=False):
        """El monitor donde está Caudal. Con `util`, solo su área útil (sin la barra de tareas)."""
        v = getattr(self.ctx, "ventana", None)
        scr = v.screen() if v is not None else None
        scr = scr or QGuiApplication.primaryScreen()
        return scr.availableGeometry() if util else scr.geometry()

    def abrir(self, solo_ver=False):
        if self.abierta:
            self.cerrar()
        self.solo_ver = bool(solo_ver)
        # como fondo de pantalla ocupa el monitor entero; abierta, el área útil: la barra de
        # tareas queda a la vista y las notificaciones de Windows siguen saliendo
        geo = self.pantalla_destino(util=not self.solo_ver)
        self._crear(geo)
        self.abierta = True
        self._conectar(True)
        self._colores_caratula()
        self._pista(self.r.actual)
        self._estado(self.r.estado)
        # primero se ve la escena; el video (decodificar y presentar 720p) entra un instante después,
        # para que abrir no sea un único tirón con las once ventanas y el video a la vez
        QTimer.singleShot(280, self._preparar_video)
        QTimer.singleShot(0, self._recientes)
        # quien acaba de donar no tiene que esperar al refresco periódico (20 min): se pregunta ya
        self._preguntar_donador()
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
        if not self.solo_ver:
            self.ctx.avisar("Arrastra cualquier pieza para moverla y agrándala desde su esquina (o Ctrl+rueda). "
                            "El botón de fondo de la barra elige videoclip, carátula o uno de los escenarios.")
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
            if busc is not None and busc.isVisible():
                QTimer.singleShot(0, self.cerrar_buscador)
                return True
            QTimer.singleShot(0, self.cerrar)
            return True
        if (tecla in (Qt.Key_Left, Qt.Key_Right) and ev.modifiers() & Qt.ControlModifier
                and not en_buscador):
            self.mover_letra(PASO_DESFASE_MS if tecla == Qt.Key_Right else -PASO_DESFASE_MS)
            return True
        if tecla == Qt.Key_E and not en_buscador and not ev.modifiers():
            self.alternar_edicion()
            return True
        if tecla == Qt.Key_R and not en_buscador and not ev.modifiers():
            self.restablecer_piezas()
            return True
        if tecla == Qt.Key_Space and not en_buscador:
            self.r.alternar()
            return True
        return False

    def _crear(self, geo):
        self._fondo = _FondoVentana()
        self._fondo.doble_clic = self._mostrar_barra_si_falta
        if self.solo_ver:
            self._fondo.setGeometry(geo)
            self._fondo.show()
        else:
            # NO showFullScreen: una ventana que tapa el monitor entero hace que Windows la tome
            # por «app a pantalla completa» y silencie las notificaciones (WhatsApp, correo…).
            # Ocupa el área útil; si la barra de tareas se oculta sola (área útil = monitor),
            # un píxel menos basta para que los avisos sigan saliendo
            # (SHQueryUserNotificationState pasa de 2 «ocupado» a 5 «acepta notificaciones»).
            monitor = self.pantalla_destino()
            self._fondo.setGeometry(geo.adjusted(0, 0, 0, -1) if geo == monitor else geo)
            self._fondo.show()
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
            if not self.solo_ver and nombre in MINIMOS_PIEZA:
                bloqueo = None
                if nombre == "barra":
                    # sobre la línea de progreso arrastrar es adelantar la canción, no mover la barra
                    bloqueo = (lambda p, b=w: b.rect_progreso().adjusted(-6, -10, 6, 10).contains(p.toPointF()))
                e = editable.PiezaEditable(w, nombre, minimo=MINIMOS_PIEZA[nombre], libre=True, bloqueo=bloqueo)
                e.cambiado.connect(self._guardar_pieza)
                e.ocultado.connect(self._aviso_oculta)
                self._editables[nombre] = e
                guardado = self._estados_guardados().get(nombre)
                if guardado:
                    e.aplicar(guardado, geo)
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
            barra.pidio_buscar.connect(self.alternar_buscador)
            barra.pidio_restablecer.connect(self.restablecer_piezas)
            self._colocar_buscador()
        t = self._piezas["tarjeta"]
        t.pidio_me_gusta.connect(self._me_gusta)
        t.pidio_otra_letra.connect(self._otra_letra)
        if hasattr(t, "pidio_traducir"):
            t.pidio_traducir.connect(self.alternar_traduccion)
        self._piezas["lista"].elegida.connect(self._elegir)
        for lado, rect in g["bordes"].items():
            b = BordeBrillo(lado)
            colocar(b, rect, Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus)
            self._bordes[lado] = b

    def _mostrar_piezas(self):
        for b in self._bordes.values():
            b.show()
        guardados = self._estados_guardados()
        for nombre, w in self._piezas.items():
            if nombre == "buscador":
                continue                      # lo abre la lupa de la barra
            if guardados.get(nombre, {}).get("visible") is False:
                continue                      # la persona la ocultó
            w.show()
            w.raise_()

    # ------------------------------------------------------------ piezas a gusto

    def _estados_guardados(self):
        try:
            return dict(self.ctx.ajustes["escena_piezas"] or {})
        except Exception:  # noqa: BLE001
            return {}

    def _guardar_pieza(self, nombre):
        e = self._editables.get(nombre)
        if e is None:
            return
        estado = e.estado()
        if not estado:
            return
        tabla = self._estados_guardados()
        tabla[nombre] = estado
        try:
            self.ctx.ajustes["escena_piezas"] = tabla
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass

    def alternar_edicion(self):
        """Tecla E: entrar o salir del modo para mover, agrandar y ocultar piezas."""
        si = not editable.edicion_activa()
        editable.activar_edicion(si)
        if si:
            self.ctx.avisar("Modo edición: arrastra las piezas, agrándalas desde la esquina (o Ctrl+rueda) "
                            "y ocúltalas con ✕. E para terminar, R para volver a empezar.")
        else:
            self.ctx.avisar("Listo: la escena queda así.")

    def restablecer_piezas(self):
        """Todo vuelve a su sitio y se ve otra vez. Lo piden el botón Restablecer de la barra y la
        tecla R (en modo edición); no depende del modo edición."""
        try:
            self.ctx.ajustes["escena_piezas"] = {}
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        if not self.abierta:
            return
        self._quitar_aviso_ya()
        g = disposicion(self.pantalla_destino(util=not self.solo_ver), self.solo_ver)
        for nombre, w in self._piezas.items():
            if nombre in g and nombre != "buscador":
                w.setGeometry(g[nombre])
                w.show()
                w.raise_()
        self.ctx.avisar("La escena volvió a como venía.")

    # ------------------------------------------------------------ aviso de pieza oculta

    def _mostrar_aviso(self, texto):
        """Aviso discreto centrado sobre la barra: aparece con fundido, dura 4 s y se desvanece.
        Solo hay un aviso a la vez: uno nuevo sustituye al que esté en pantalla."""
        if not self.abierta or self._fondo is None:
            return
        if self._aviso is None:
            flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus
            self._aviso = QLabel(texto, self._fondo, flags)
            self._aviso.setAttribute(Qt.WA_TranslucentBackground, True)
            self._aviso.setStyleSheet(
                "QLabel{background-color:rgba(20,20,24,210);color:#FFFFFF;padding:12px;"
                "border-radius:12px;font-size:12px;}")
            self._anim_aviso = QPropertyAnimation(self._aviso, b"windowOpacity", self._aviso)
            self._anim_aviso.setDuration(DURACION_FADE_MS)
            self._anim_aviso.finished.connect(self._fin_fade_aviso)
            self._timer_aviso = QTimer(self)
            self._timer_aviso.setSingleShot(True)
            self._timer_aviso.timeout.connect(self._quitar_aviso)
        self._timer_aviso.stop()
        self._anim_aviso.stop()
        self._aviso.setText(texto)
        self._aviso.adjustSize()
        b = self._piezas.get("barra")
        if b is not None and b.isVisible():
            ref = b.geometry()
            x = ref.center().x() - self._aviso.width() // 2
            y = ref.top() - self._aviso.height() - 10
        else:
            # sin barra a la vista: abajo al centro, a 48 px del borde útil de la pantalla
            area = self.pantalla_destino(util=not self.solo_ver)
            x = area.center().x() - self._aviso.width() // 2
            y = area.bottom() - 48 - self._aviso.height()
        self._aviso.move(x, y)
        self._aviso.setWindowOpacity(0.0)
        self._aviso.show()
        self._aviso.raise_()
        self._animar_aviso(1.0)
        self._timer_aviso.start(DURACION_AVISO_MS)

    def _aviso_oculta(self, nombre):
        """Texto del aviso según la pieza que la persona ocultó con la ✕."""
        if nombre == "barra":
            texto = "Barra oculta · pulsa R para recuperarla"
        else:
            texto = "Pieza oculta · pulsa Restablecer en la barra o la tecla R"
        self._mostrar_aviso(texto)

    def _mostrar_barra_si_falta(self):
        """Doble clic en el fondo: si la barra está oculta, vuelve en su posición guardada."""
        b = self._piezas.get("barra")
        if b is None or b.isVisible() or not self.abierta:
            return
        e = self._editables.get("barra")
        if e is not None:
            e.mostrar()              # muestra y guarda el estado
        else:
            b.show()
        b.raise_()

    def _animar_aviso(self, destino):
        self._anim_aviso.stop()
        self._anim_aviso.setStartValue(float(self._aviso.windowOpacity()))
        self._anim_aviso.setEndValue(float(destino))
        self._anim_aviso.start()

    def _quitar_aviso(self):
        """Desvanece el aviso y lo oculta al terminar."""
        if self._aviso is None or not self._aviso.isVisible():
            return
        self._animar_aviso(0.0)

    def _fin_fade_aviso(self):
        if self._aviso is not None and self._aviso.windowOpacity() <= 0.01:
            self._aviso.hide()

    def _quitar_aviso_ya(self):
        """Corta el aviso en seco (al cerrar la escena o al restablecer)."""
        if self._timer_aviso is not None:
            self._timer_aviso.stop()
        if self._anim_aviso is not None:
            self._anim_aviso.stop()
        if self._aviso is not None:
            self._aviso.hide()

    # ------------------------------------------------------------ «Mi imagen»

    def _ruta_propia(self):
        return str(self.ctx.ajustes.get("escena_imagen_propia", "") or "")

    def _ruta_propia_valida(self):
        ruta = self._ruta_propia()
        return bool(ruta) and os.path.isfile(ruta)

    def _fijar_ruta_propia(self):
        """Pasa la imagen elegida al escenario «Mi imagen» antes de crearlo."""
        try:
            from .escenarios import propia
        except ImportError:
            return
        propia.fijar_ruta(self._ruta_propia())

    def _elegir_imagen_propia(self):
        """Selector de imagen (png/jpg/webp). Cancelar no cambia nada."""
        if not self.abierta:
            return
        from PySide6.QtWidgets import QFileDialog
        ruta, _ = QFileDialog.getOpenFileName(self._fondo, "Elige una imagen o un GIF para tu escena", "",
                                              "Imágenes y GIF (*.png *.jpg *.jpeg *.webp *.gif)")
        if not ruta or not self.abierta:
            return
        self.ctx.ajustes["escena_imagen_propia"] = ruta
        self.ctx.ajustes.guardar()
        self._forzar_propia = True
        self.poner_fondo("propia")

    def cerrar(self):
        if not self.abierta:
            return
        self.abierta = False
        self._soltar_espera_donador()
        self._fondo_pendiente = None
        self._reloj_letra.stop()
        self._quitar_aviso_ya()
        self._aviso = None                 # el QLabel muere con la ventana de fondo
        self._anim_aviso = None
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
        editable.activar_edicion(False)
        self._editables.clear()
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
                 (self.r.modo_cambio, self._modo),
                 (sincronia_de(self.ctx).listo, self._sincronia_lista)]
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
        if clave != getattr(self, "_clave_reloj", None):
            # canción nueva: nada de la anterior (posición, duración, desfase del video) debe mover su letra
            self._clave_reloj = clave
            self._pos, self._pos_t, self._dur = 0.0, time.monotonic(), 0.0
            self._dur_letra = 0.0
            self._datos_letra = {}
            self._ms_mostrado = None
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
        self._recomendar(p)
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
        datos = getattr(self, "_datos_letra", None) or {}
        if self.abierta and datos.get("sincronizada") and not self._desfase_letra():
            # el videoclip puede ser otra versión que el audio: se mide también en este modo
            sincronia_de(self.ctx).pedir(self.r.actual, datos)
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
        try:
            if self._fondo.escenario is not None:
                self._fondo.escenario.poner_acento(QColor(b))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ fondo de video

    def _preparar_video(self):
        """El videoclip de fondo si se puede; si no, la carátula viva."""
        if not self.abierta:
            return
        modo = self.ctx.ajustes.get("escena_fondo", "video")
        self._escenario_negado = False
        if modo in escenarios.ESCENARIOS and not self._es_donador():
            self._escenario_negado = True
            modo = "ambiente"                   # los escenarios son de donadores: la carátula viva
        if modo in escenarios.ESCENARIOS:
            if modo == "propia":
                self._fijar_ruta_propia()       # antes de crear el escenario
            forzar = modo == "propia" and self._forzar_propia
            if self._fondo.ver_escenario(modo, forzar=forzar):
                if modo == "propia":
                    self._forzar_propia = False
                self.r.activar_espectro(True)
                return
            modo = "ambiente"                   # no se pudo cargar: la carátula viva
        if modo != "video" or not self.r.disponible:
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
        """El botón de fondo de la barra: un menú con videoclip, carátula y los escenarios."""
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QMenu
        actual = self.ctx.ajustes.get("escena_fondo", "video")
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#16141C;color:#F2F0F7;border:1px solid #2E2A38;border-radius:10px;padding:6px;}"
            "QMenu::item{padding:7px 22px 7px 14px;border-radius:6px;}"
            "QMenu::item:selected{background:#2E2A38;}"
            "QMenu::separator{height:1px;background:#2E2A38;margin:5px 8px;}")
        opciones = [("video", "Videoclip"), ("ambiente", "Carátula viva"), None]
        opciones += [(k, v[0]) for k, v in escenarios.ESCENARIOS.items()]
        opciones += [None, ("elegir_propia", "Elegir mi imagen o GIF…")]
        donador = self._es_donador()
        for op in opciones:
            if op is None:
                menu.addSeparator()
                continue
            clave, nombre = op
            libre = clave in FONDOS_LIBRES
            marca = "✓  " if clave == actual else ("🔒 " if not (libre or donador) else "     ")
            acc = menu.addAction(marca + nombre)
            acc.setData(clave)
        # sin bloquear: la escena (letra, video, ondas) sigue viva con el menú abierto
        menu.triggered.connect(self._fondo_elegido)
        self._menu_fondo = menu
        menu.popup(QCursor.pos())

    def _es_donador(self):
        """Los escenarios (y la imagen o GIF propios) son exclusivos de donadores; videoclip y carátula, no."""
        try:
            from ..ecualizador_avanzado import es_premium
            return es_premium(self.ctx)
        except Exception:  # noqa: BLE001
            return False

    def _fondo_elegido(self, acc):
        clave = acc.data()
        if not clave:
            return
        if clave not in FONDOS_LIBRES and not self._es_donador():
            # lo guardado en este equipo puede ir atrasado (una donación de hace un rato): se pregunta
            # al servidor y, si ya es donador, el fondo se pone solo
            if self._preguntar_donador(pendiente=clave):
                return
            self._avisar_solo_donadores()
            return
        if clave == "elegir_propia" or (clave == "propia" and not self._ruta_propia_valida()):
            # el selector se abre cuando el menú ya se cerró, no dentro de su evento
            QTimer.singleShot(0, self._elegir_imagen_propia)
            return
        self.poner_fondo(clave)

    AVISO_SOLO_DONADORES = ("Los escenarios son exclusivos para donadores. Desbloquéalos apoyando a Caudal "
                            "(Más → Donar) o con un código de prueba.")
    ESPERA_DONADOR_MS = 10000

    def _avisar_solo_donadores(self):
        self.ctx.avisar(self.AVISO_SOLO_DONADORES)

    def _preguntar_donador(self, pendiente=None):
        """Pide al servidor el estado de donador (en segundo plano). Devuelve False si no se puede preguntar."""
        g = getattr(self.ctx, "premium", None)
        if g is None or not hasattr(g, "refrescar") or not hasattr(g, "cambiado"):
            return False
        if ((getattr(self.ctx, "cuenta", None) or {}).get("sesion")) is None:
            return False                        # sin sesión no hay a quién preguntar
        if pendiente is not None:
            self._fondo_pendiente = pendiente
        if not self._esperando_donador:
            self._esperando_donador = True
            g.cambiado.connect(self._estado_donador_llego)
            QTimer.singleShot(self.ESPERA_DONADOR_MS, self._sin_respuesta_donador)
        g.refrescar()
        return True

    def _soltar_espera_donador(self):
        if not self._esperando_donador:
            return
        self._esperando_donador = False
        try:
            self.ctx.premium.cambiado.disconnect(self._estado_donador_llego)
        except (RuntimeError, TypeError, AttributeError):
            pass

    def _estado_donador_llego(self):
        self._soltar_espera_donador()
        pendiente, self._fondo_pendiente = self._fondo_pendiente, None
        if not self.abierta:
            return
        if not self._es_donador():
            if pendiente is not None:
                self._avisar_solo_donadores()
            return
        if pendiente is not None:
            if pendiente == "elegir_propia" or (pendiente == "propia" and not self._ruta_propia_valida()):
                QTimer.singleShot(0, self._elegir_imagen_propia)
            else:
                self.poner_fondo(pendiente)
        elif self._escenario_negado:
            self._preparar_video()              # el escenario guardado ya se puede ver

    def _sin_respuesta_donador(self):
        """Sin red o el servidor no contestó: lo de siempre."""
        if not self._esperando_donador:
            return
        self._soltar_espera_donador()
        pendiente, self._fondo_pendiente = self._fondo_pendiente, None
        if pendiente is not None and self.abierta:
            self._avisar_solo_donadores()

    def poner_fondo(self, nuevo):
        self.ctx.ajustes["escena_fondo"] = nuevo
        self.ctx.ajustes.guardar()
        if nuevo != "video":
            self.r.tope_video = None
            if self.r.destino_video == NOMBRE_VIDEO:
                self.r.mover_video("principal")
            if self._modo_previo is not None and self._modo_previo != self.r.modo:
                self.r.cambiar_modo(self._modo_previo)
            self._modo_previo = None
            if nuevo in escenarios.ESCENARIOS:
                self._preparar_video()          # pone el escenario y el medidor del audio
            else:
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
        self._dur_letra = float((datos or {}).get("duracion") or 0)
        self._datos_letra = datos or {}
        if sinc and not self._desfase_letra():
            # Caudal escucha un tramo y la pone a tiempo (o cambia por la que cuadra): ui/sincronia_auto.py
            sincronia_de(self.ctx).pedir(self.r.actual, datos)
        self._lineas_actuales = [str((l or {}).get("texto") or "") if isinstance(l, dict) else str(l)
                                 for l in lineas]
        self._traducciones = None
        if self._traduciendo:
            self._traducir_letra()

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

    # ------------------------------------------------------------ traducción de la letra

    def alternar_traduccion(self):
        """La píldora «Traducir» de la tarjeta: la letra lleva debajo su traducción al español (o se quita)."""
        self._traduciendo = not self._traduciendo
        t = self._piezas.get("tarjeta")
        if t is not None and hasattr(t, "fijar_traduccion"):
            t.fijar_traduccion(self._traduciendo)
        if self._traduciendo:
            self._traducir_letra()
        else:
            self._poner_traducciones(None)

    def _traducir_letra(self):
        lineas = list(self._lineas_actuales)
        if not any(x.strip() for x in lineas):
            return
        from ... import traductor
        from ...hilos import en_segundo_plano
        clave = self._lineas_clave

        def llego(trad, c=clave, n=len(lineas)):
            if not self.abierta or c != self._lineas_clave or not self._traduciendo:
                return
            if isinstance(trad, str):             # traductor.MISMO_IDIOMA
                self.ctx.avisar("Esta letra ya está en español.")
                return
            if not trad or len(trad) != n:
                self.ctx.avisar("No se pudo traducir esta letra.")
                return
            self._poner_traducciones([str(x or "") for x in trad])

        self.ctx.avisar("Traduciendo la letra…")
        en_segundo_plano(traductor.traducir, clave or "", lineas, "es", ok=llego,
                         error=lambda _e: self.abierta and self.ctx.avisar("No se pudo traducir (¿sin internet?)."),
                         dueno=self)

    def _poner_traducciones(self, lista):
        self._traducciones = lista
        letra = self._piezas.get("letra")
        if letra is not None and hasattr(letra, "fijar_traducciones"):
            letra.fijar_traducciones(lista)

    # ------------------------------------------------------------ recomendadas según lo que suena

    def _recomendar(self, p):
        """«Seguir escuchando» suma canciones parecidas a la que suena (la radio de YouTube Music)."""
        lista = self._piezas.get("lista")
        vid = (p or {}).get("video_id")
        if lista is None or not hasattr(lista, "poner_recomendadas") or not vid or vid == self._recom_clave:
            return
        self._recom_clave = vid
        if hasattr(lista, "fijar_cargando_recomendadas"):
            lista.fijar_cargando_recomendadas(True)
        from ... import catalogo
        from ...hilos import en_segundo_plano

        def llego(datos, v=vid):
            if not self.abierta or v != self._recom_clave:
                return
            ya = {clave_de(self.r.actual)}
            pistas = [x for x in (datos or {}).get("pistas") or [] if clave_de(x) not in ya][:12]
            lista.poner_recomendadas(pistas)
            if hasattr(lista, "fijar_cargando_recomendadas"):
                lista.fijar_cargando_recomendadas(False)

        def fallo(_e, v=vid):
            if self.abierta and v == self._recom_clave and hasattr(lista, "fijar_cargando_recomendadas"):
                lista.fijar_cargando_recomendadas(False)

        en_segundo_plano(catalogo.radio, vid, None, 20, ok=llego, error=fallo, dueno=self)

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
        self._tic_ondas()
        self._piezas["letra"].fijar_ms(self._ms_letra(time.monotonic()))

    def _ms_letra(self, ahora):
        """Reloj de la letra: avanza solo entre avisos de posición, pero sin enloquecer.
        - No extrapola más de MAX_EXTRAPOLAR_S sin un aviso nuevo (si el audio se atasca o carga,
          la letra espera en vez de adelantarse y luego saltar hacia atrás).
        - Nunca retrocede por un desajuste pequeño (los avisos llegan con retraso variable): espera a que
          la música lo alcance. Solo salta hacia atrás si la diferencia es grande (la persona buscó)."""
        pos = self._pos
        if self.r.estado == "sonando":
            velocidad = float(getattr(self.r, "velocidad", 1.0) or 1.0)
            pos += min(MAX_EXTRAPOLAR_S, max(0.0, ahora - self._pos_t)) * velocidad
        objetivo = round(pos * 1000) + ADELANTO_LETRA_MS + self._correccion_letra()
        antes = self._ms_mostrado
        if antes is None or abs(objetivo - antes) > SALTO_LETRA_MS or objetivo >= antes:
            self._ms_mostrado = objetivo
        return self._ms_mostrado

    def _tic_ondas(self):
        """Con un escenario a la vista, sus ondas se mueven con el audio que suena."""
        sw = getattr(self._fondo, "escenario", None)
        if sw is None or not sw.isVisible():
            return
        from ... import espectro
        if self._modelo_audio is None:
            self._modelo_audio = espectro.ModeloAudio(32)
        ahora = time.monotonic()
        dt = min(0.25, ahora - (self._t_ondas or ahora))
        self._t_ondas = ahora
        sonando = self.r.estado == "sonando"
        nivel = None
        if sonando:
            try:
                nivel = self.r.nivel_audio()
            except Exception:  # noqa: BLE001
                nivel = None
        self._modelo_audio.avanzar(dt, nivel, sonando, self._pos)
        sw.fijar_espectro(list(self._modelo_audio.bandas) if sonando else [])

    def _correccion_letra(self):
        """Lo que se corre la letra: el ajuste de la persona manda; si no lo hay, lo que midió la sincronía
        automática escuchando el audio; y si todavía no midió, la estimación por la duración del video."""
        propio = self._desfase_letra()
        if propio:
            return propio
        datos = getattr(self, "_datos_letra", None) or {}
        sinc = sincronia_de(self.ctx)
        if datos.get("lineas") and sinc.activa() and sinc.medida(self.r.actual, datos["lineas"]):
            return sinc.desfase(self.r.actual, datos["lineas"])
        return self._desfase_video()

    def _sincronia_lista(self, clave, res):
        if not self.abierta or clave != clave_de(self.r.actual):
            return
        datos = getattr(self, "_datos_letra", None) or {}
        accion = (res or {}).get("accion")
        if accion == "cambiar":
            nueva = sincronia_de(self.ctx).letra_nueva(self.r.actual, datos.get("lineas"))
            if nueva:
                self._llego_letra(self._lineas_clave, nueva[0])
            return
        if accion == "corregir":
            self._ms_mostrado = None          # que salte ya al sitio bueno, sin esperar

    def _desfase_video(self):
        """Un videoclip suele durar más que la canción (intro, escena hablada): la letra sincronizada es
        de la canción, así que se corre lo que el video tiene de más al principio. Solo con el videoclip
        sonando y una diferencia creíble (de 2,5 s a 2 min); con audio solo, no se toca."""
        if self.r.modo != "video" or not self._dur_letra or not self._dur:
            return 0
        extra = float(self._dur) - float(self._dur_letra)
        if not 2.5 <= extra <= 120:
            return 0
        # se decide una sola vez por canción y modo: si la duración llega tarde o cambia, la letra no salta
        clave = (getattr(self, "_clave_reloj", None), round(float(self._dur_letra)))
        fijo = getattr(self, "_desfase_video_fijo", None)
        if fijo is None or fijo[0] != clave:
            self._desfase_video_fijo = (clave, -int(extra * 1000))
        return self._desfase_video_fijo[1]

    def _desfase_letra(self):
        """El ajuste fino que la persona le dio a la letra de esta canción (ms)."""
        try:
            return int((self.ctx.ajustes["letra_desfases"] or {}).get(clave_de(self.r.actual) or "", 0))
        except Exception:  # noqa: BLE001
            return 0

    def mover_letra(self, ms):
        """Adelanta (+) o atrasa (−) la letra de la canción que suena y lo recuerda."""
        clave = clave_de(self.r.actual)
        if not clave:
            return
        try:
            tabla = dict(self.ctx.ajustes["letra_desfases"] or {})
        except Exception:  # noqa: BLE001
            tabla = {}
        nuevo = max(-10000, min(10000, int(tabla.get(clave, 0)) + int(ms)))
        if nuevo:
            tabla[clave] = nuevo
        else:
            tabla.pop(clave, None)
        if len(tabla) > 500:                        # que no crezca sin fin
            for k in list(tabla)[:len(tabla) - 500]:
                tabla.pop(k, None)
        try:
            self.ctx.ajustes["letra_desfases"] = tabla
            self.ctx.ajustes.guardar()
        except Exception:  # noqa: BLE001
            pass
        seg = nuevo / 1000
        self.ctx.avisar("Letra a tiempo" if not nuevo else
                        f"Letra {'adelantada' if nuevo > 0 else 'atrasada'} {abs(seg):.2f} s".replace(".", ","))

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
            self.cerrar_buscador()

    def alternar_buscador(self):
        """La lupa de la barra: abre el buscador (con el cursor listo para escribir) o lo cierra."""
        b = self._piezas.get("buscador")
        if b is None:
            return
        if b.isVisible():
            self.cerrar_buscador()
            return
        self._colocar_buscador()
        b.show()
        b.raise_()
        b.activateWindow()
        b.enfocar()

    def cerrar_buscador(self):
        b = self._piezas.get("buscador")
        if b is not None and b.isVisible():
            b.limpiar()
            b.hide()

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
