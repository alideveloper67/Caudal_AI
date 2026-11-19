# -*- coding: utf-8 -*-
"""Ventana principal de Caudal: paneles, navegacion, busqueda y bandeja."""

import os
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QComboBox, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSplitter,
                               QStackedWidget, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from .. import catalogo, redes, version
from ..config import APP_NOMBRE
from ..hilos import en_segundo_plano
from . import iconos
from .actualizador import Buscador, mostrar_aviso
from .barra_reproduccion import BarraReproduccion
from .componentes import Aviso, BotonIcono
from .estilos import C, hoja
from .panel_derecho import PanelDerecho
from .panel_lateral import PanelLateral

EXT_AUDIO = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac", ".wma", ".webm"}
EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts"}

SINGLETONS = ("descargas", "video", "letra", "vinilo")


class _Teclas(QObject):
    """Espacio para reproducir/pausar en toda la app, salvo al escribir."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Space and not ev.modifiers():
            foco = QApplication.focusWidget()
            if not isinstance(foco, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox,
                                     QAbstractSpinBox)):
                if QApplication.activeWindow() in (self.v, self.v.mini):
                    self.v.ctx.reproductor.alternar()
                    return True
        return False


class TeclasMultimedia(QAbstractNativeEventFilter):
    """Las teclas de reproducir/siguiente/anterior del teclado, en todo Windows.

    Se registran solo mientras Caudal tiene algo cargado, para no quitarle
    las teclas a otras apps cuando no se esta usando.
    """

    TECLAS = {1: 0xB3, 2: 0xB0, 3: 0xB1, 4: 0xB2}   # play/pausa, sig., ant., stop
    WM_HOTKEY = 0x0312

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self.activas = set()

    def registrar(self):
        if sys.platform != "win32" or self.activas:
            return
        import ctypes
        hwnd = int(self.v.winId())
        for ident, vk in self.TECLAS.items():
            if ctypes.windll.user32.RegisterHotKey(hwnd, ident, 0x4000, vk):  # MOD_NOREPEAT
                self.activas.add(ident)

    def soltar(self):
        if sys.platform != "win32":
            return
        import ctypes
        hwnd = int(self.v.winId())
        for ident in list(self.activas):
            ctypes.windll.user32.UnregisterHotKey(hwnd, ident)
        self.activas.clear()

    def nativeEventFilter(self, tipo, mensaje):
        if tipo != b"windows_generic_MSG" or not self.activas:
            return False, 0
        import ctypes.wintypes
        msg = ctypes.wintypes.MSG.from_address(int(mensaje))
        if msg.message != self.WM_HOTKEY:
            return False, 0
        r = self.v.r
        ident = int(msg.wParam)
        if ident == 1:
            r.alternar()
        elif ident == 2:
            r.siguiente()
        elif ident == 3:
            r.anterior()
        elif ident == 4:
            r.pausar()
        else:
            return False, 0
        return True, 0


class Ventana(QWidget):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        ctx.ventana = self
        self.ajustes = ctx.ajustes
        self.r = ctx.reproductor
        self.r.pidio_pantalla_completa = self.alternar_completa
        self.setObjectName("raiz")
        self.setWindowTitle(APP_NOMBRE)
        self.setWindowIcon(QIcon(iconos.icono_app(256)))
        self.setMinimumSize(940, 600)         # cabe en portátiles de 1366 × 768
        self.resize(1440, 900)
        self.setAcceptDrops(True)
        # «Fondo de Caudal»: la copia local se ve al instante (la nube la refresca después)
        from ..fondo import GestorFondo
        from . import estilos
        self.fondo = GestorFondo(ctx)
        ctx.fondo = self.fondo
        from ..mascotas import GestorMascota
        ctx.mascota = GestorMascota(ctx)      # la mascotita del reproductor (donadores y fundadores)
        # lo premium (marcos, efectos de nombre, temas, pase de prueba): copia local al instante y la nube
        # se pregunta en segundo plano, sin frenar el arranque
        from ..premium import GestorPremium
        self.premium = GestorPremium(ctx)
        ctx.premium = self.premium
        self.premium.aspecto_cambiado.connect(self.reabrir_con_aspecto)
        self.premium.refrescar()
        estilos.FONDO["activo"] = self.fondo.activo or estilos.patron_actual() is not None
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        self.historia = []          # [(destino, widget o None)]
        self.indice = -1
        self.singletons = {}
        self.en_completa = False
        self._saliendo = False
        self._aviso_bandeja = False
        self._ultimo_portapapeles = ""
        self.mini = None

        self._construir()
        self._montar_fondo()
        self._conectar()
        self._atajos()
        self._bandeja()

        geo = self.ajustes["geometria"]
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
            except Exception:
                pass
        self._dejar_a_la_vista()
        self._t_letra = QTimer(self)
        self._t_letra.setSingleShot(True)
        self._t_letra.setInterval(300)
        self._t_letra.timeout.connect(self._ajustar_letra)
        estado_split = self.ctx.coleccion.estado("divisor")
        if estado_split:
            try:
                self.divisor.restoreState(QByteArray.fromBase64(estado_split.encode()))
            except Exception:
                pass

        self.navegar({"pagina": "inicio"})
        panel = self.ajustes["panel_derecho"]
        if panel == "oculto":
            self.panel_der.hide()
        else:
            self.panel_der.mostrar(panel if panel in ("sonando", "cola", "letras") else "sonando")
        self.barra.marcar_panel(self.panel_der.actual if self.panel_der.isVisible() else "")
        self.r.restaurar_sesion()
        self._seguir_tras_reabrir()
        if not self.r.disponible:
            QTimer.singleShot(800, lambda: QMessageBox.warning(
                self, APP_NOMBRE, "No se encontró el motor de reproducción (libmpv), así que no "
                                  "se puede reproducir. Las descargas sí funcionan.\n\n"
                                  + (self.r.motivo_no_disponible or "")))
        self.buscador_version = None
        self._aviso_grande = None
        self._aviso_mascotas = None
        self._grande_en_sesion = False
        self._novedad_pendiente = None
        QTimer.singleShot(2500, self._avisar_novedades)
        # «ya puedes regalar códigos de prueba»: una vez, a donadores y fundadores (cuando se sepa que lo son)
        self._aviso_regalo = None
        self._t_regalo = QTimer(self)
        self._t_regalo.setSingleShot(True)
        self._t_regalo.timeout.connect(self._avisar_regalo)
        self.premium.cambiado.connect(lambda: self._t_regalo.start(3000))
        self._t_regalo.start(5000)
        QTimer.singleShot(1500, self.fondo.sincronizar)
        QTimer.singleShot(6000, lambda: self.buscar_version(True))
        QTimer.singleShot(9000, self._buscar_avisos)
        QApplication.instance().installEventFilter(_Teclas(self))
        from . import arrastre
        arrastre.instalar()        # arrastrar con el ratón para desplazar, como con el dedo
        self.teclas_multimedia = TeclasMultimedia(self)
        QApplication.instance().installNativeEventFilter(self.teclas_multimedia)
        if self.r.actual is not None and self.ajustes["teclas_multimedia"]:
            self.teclas_multimedia.registrar()

    # ------------------------------------------------------------ estructura

    def _construir(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(8, 8, 8, 0)
        raiz.setSpacing(8)

        self.divisor = QSplitter(Qt.Horizontal)
        self.divisor.setHandleWidth(8)
        self.divisor.setChildrenCollapsible(False)
        self.divisor.setStyleSheet("QSplitter::handle{background:transparent;}")

        self.lateral = PanelLateral(self.ctx)
        self.divisor.addWidget(self.lateral)
        # la versión, siempre a la vista y sin estorbar: abajo del panel izquierdo
        # (se queda en la vista de video; en pantalla completa se esconde con el panel)
        self.et_version = QLabel(f"Caudal {version.VERSION}")
        self.et_version.setObjectName("version_visible")
        self.et_version.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.et_version.setFocusPolicy(Qt.NoFocus)
        self.et_version.setAccessibleName(f"Versión de Caudal {version.VERSION}")
        self.et_version.setStyleSheet(
            f"color:{C['texto3']};background:transparent;font-size:10px;"
            "padding:0 0 3px 14px;")
        self.lateral.layout().addWidget(self.et_version)

        self.centro = QFrame()
        self.centro.setObjectName("panel_centro")
        vc = QVBoxLayout(self.centro)
        vc.setContentsMargins(0, 0, 0, 0)
        vc.setSpacing(0)
        vc.addWidget(self._barra_superior())
        self.pila = QStackedWidget()
        vc.addWidget(self.pila, 1)
        self.divisor.addWidget(self.centro)

        self.panel_der = PanelDerecho(self.ctx)
        self.divisor.addWidget(self.panel_der)
        self.divisor.setStretchFactor(0, 0)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setStretchFactor(2, 0)
        self.divisor.setSizes([300, 900, 340])
        raiz.addWidget(self.divisor, 1)

        self.barra = BarraReproduccion(self.ctx)
        raiz.addWidget(self.barra)
        self.aviso = Aviso(self)

        from .video import MiniReproductor
        self.mini = MiniReproductor(self.ctx)
        self.mini.expandir.connect(self._mini_expandir)
        # Modo gamer: atajos globales, ahorro al jugar, XP... (todo apagado hasta que se active)
        from ..modo_gamer import GestorGamer
        self.gamer = GestorGamer(self.ctx, self)
        self.ctx.gamer = self.gamer

    def _barra_superior(self):
        barra = QFrame()
        barra.setObjectName("barra_superior")
        barra.setFixedHeight(64)
        h = QHBoxLayout(barra)
        h.setContentsMargins(16, 10, 16, 6)
        h.setSpacing(8)
        estilo = (f"QPushButton{{background:{C['fondo']};border:none;border-radius:16px;}}"
                  f"QPushButton:hover{{background:{C['superficie2']};}}")
        self.bt_atras = BotonIcono("atras", 18, "Atrás  (Alt+←)", 32)
        self.bt_atras.setStyleSheet(estilo)
        self.bt_atras.clicked.connect(self.atras)
        self.bt_adelante = BotonIcono("adelante", 18, "Adelante  (Alt+→)", 32)
        self.bt_adelante.setStyleSheet(estilo)
        self.bt_adelante.clicked.connect(self.adelante)
        h.addWidget(self.bt_atras)
        h.addWidget(self.bt_adelante)
        h.addSpacing(8)
        self.campo = QLineEdit()
        self.campo.setObjectName("buscador")
        self.campo.setPlaceholderText("¿Qué quieres escuchar o ver?  ·  o pega un enlace")
        self.campo.setClearButtonEnabled(True)
        self.campo.setMaximumWidth(560)
        self.campo.setMinimumWidth(320)
        self.campo.setFixedHeight(44)
        self.icono_lupa = QAction(iconos.icono("lupa", 20, C["texto2"]), "", self.campo)
        self.campo.addAction(self.icono_lupa, QLineEdit.LeadingPosition)
        h.addWidget(self.campo, 1)
        h.addStretch(1)
        self.bt_perfil = BotonIcono("usuario", 19, "Mi perfil", 36)
        self.bt_perfil.clicked.connect(lambda: self.navegar({"pagina": "perfil"}))
        h.addWidget(self.bt_perfil)
        self.bt_mensajes = BotonIcono("chat", 19, "Mensajes", 36)
        self.bt_mensajes.clicked.connect(lambda: self.navegar({"pagina": "mensajes"}))
        h.addWidget(self.bt_mensajes)
        # cuántos mensajes sin leer (se mira cada minuto)
        self._sin_leer = 0
        self._reloj_mensajes = QTimer(self)
        self._reloj_mensajes.setInterval(60000)
        self._reloj_mensajes.timeout.connect(self._mirar_mensajes)
        self._reloj_mensajes.start()
        QTimer.singleShot(4000, self._mirar_mensajes)
        self.bt_resumen = BotonIcono("ecualizador", 19, "Tu resumen", 36)
        self.bt_resumen.clicked.connect(lambda: self.navegar({"pagina": "resumen"}))
        h.addWidget(self.bt_resumen)
        self.bt_descargas = BotonIcono("descargar", 19, "Descargas", 36)
        self.bt_descargas.clicked.connect(lambda: self.navegar({"pagina": "descargas"}))
        h.addWidget(self.bt_descargas)
        self.bt_ajustes = BotonIcono("engranaje", 19, "Ajustes", 36)
        self.bt_ajustes.clicked.connect(lambda: self.navegar({"pagina": "ajustes"}))
        h.addWidget(self.bt_ajustes)
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        if cuenta:
            nombre = cuenta.get("nombre") or cuenta.get("usuario") or "?"
            self.bt_cuenta = QPushButton(nombre[:1].upper())
            self.bt_cuenta.setFixedSize(34, 34)
            self.bt_cuenta.setCursor(Qt.PointingHandCursor)
            self.bt_cuenta.setToolTip(nombre)
            self.bt_cuenta.setStyleSheet(
                f"QPushButton{{background:{C['acento']};color:{C['acento_texto']};border:3px solid "
                f"{C['superficie2']};border-radius:17px;font-weight:900;font-size:14px;padding:0;}}"
                f"QPushButton:hover{{border-color:{C['superficie3']};}}")
            self.bt_cuenta.clicked.connect(self._menu_cuenta)
            h.addWidget(self.bt_cuenta)

        self._t_buscar = QTimer(self)
        self._t_buscar.setSingleShot(True)
        self._t_buscar.setInterval(380)
        self._t_buscar.timeout.connect(self._buscar_ahora)
        self.campo.textEdited.connect(lambda _t: self._t_buscar.start())
        self.campo.returnPressed.connect(self._buscar_ahora)
        return barra

    def _menu_cuenta(self):
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        menu = QMenu(self)
        cab = menu.addAction(f"{cuenta.get('nombre', '')}  ·  @{cuenta.get('usuario', '')}")
        cab.setEnabled(False)
        sinc = getattr(self.ctx, "sincronizador", None)
        if sinc is not None:
            textos = {"sincronizado": "Biblioteca sincronizada", "pendiente": "Sincronizando…",
                      "sin_conexion": "Sin conexión: se sincroniza al volver",
                      "error": "No se pudo sincronizar ahora", "": "Sincronizando…"}
            estado = menu.addAction(textos.get(sinc.ultimo_estado, "Sincronizando…"))
            estado.setEnabled(False)
            menu.addAction("Sincronizar ahora", sinc.ya)
        menu.addSeparator()
        menu.addAction(iconos.icono("engranaje", 16, C["texto2"]), "Ajustes",
                       lambda: self.navegar({"pagina": "ajustes"}))
        menu.addAction(iconos.icono("candado", 16, C["texto2"]), "Privacidad y tus datos",
                       self._privacidad)
        if not (getattr(self.ctx, "cuenta", None) or {}).get("google"):
            # quien entra con Google no tiene contraseña de Caudal
            menu.addAction(iconos.icono("candado", 16, C["texto2"]), "Cambiar la contraseña",
                           self._cambiar_contrasena)
        menu.addSeparator()
        menu.addAction(iconos.icono("salir", 16, C["texto2"]), "Cerrar sesión", self._cerrar_sesion)
        menu.exec(self.bt_cuenta.mapToGlobal(self.bt_cuenta.rect().bottomRight())
                  - QPoint(menu.sizeHint().width(), -6))

    def _cambiar_contrasena(self):
        from PySide6.QtWidgets import QInputDialog
        from ..cuentas import Cuentas, ErrorCuenta
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        if not cuenta.get("sesion"):
            return
        actual, ok = QInputDialog.getText(self, "Cambiar la contraseña", "Contraseña actual:",
                                          QLineEdit.Password)
        if not ok:
            return
        nueva, ok = QInputDialog.getText(self, "Cambiar la contraseña",
                                         "Contraseña nueva (al menos 6 caracteres):",
                                         QLineEdit.Password)
        if not ok:
            return
        try:
            Cuentas().cambiar_contrasena(cuenta, actual, nueva)
        except ErrorCuenta as e:
            QMessageBox.warning(self, APP_NOMBRE, str(e))
            return
        self.aviso.mostrar("Contraseña cambiada")

    def _privacidad(self):
        from .legal_ui import DialogoPrivacidad
        d = DialogoPrivacidad(self.ctx, self)
        d.cuenta_eliminada.connect(lambda: self._cerrar_sesion(preguntar=False))
        d.exec()

    def _cerrar_sesion(self, preguntar=True):
        if preguntar:
            r = QMessageBox.question(self, APP_NOMBRE, "¿Cerrar la sesión? La próxima vez Caudal "
                                                       "te pedirá entrar.")
            if r != QMessageBox.Yes:
                return
        self._saliendo = True
        self._guardar_estado()
        self.teclas_multimedia.soltar()
        self.gamer.cerrar()
        self.ctx.gestor.cancelar_todo()
        self.r.cerrar()
        if self.mini:
            self.mini.hide()
        if self.bandeja:
            self.bandeja.hide()
        self.hide()
        cerrar = getattr(self.ctx, "cerrar_sesion", None)
        if cerrar:
            cerrar()
        else:
            QApplication.quit()

    # ------------------------------------------------------------ navegacion

    def _fabricar(self, destino):
        pag = destino.get("pagina")
        if pag in SINGLETONS and pag in self.singletons:
            return self.singletons[pag]
        w = None
        if pag == "inicio":
            from .paginas.inicio import PaginaInicio
            w = PaginaInicio(self.ctx)
        elif pag == "buscar":
            from .paginas.buscar import PaginaBuscar
            w = PaginaBuscar(self.ctx, destino.get("q", ""), destino.get("filtro", "todo"))
        elif pag == "explorar":
            from .paginas.explorar import PaginaExplorar
            w = PaginaExplorar(self.ctx)
        elif pag == "genero":
            from .paginas.explorar import PaginaGenero
            w = PaginaGenero(self.ctx, destino["id"], destino.get("params"),
                             destino.get("titulo", ""))
        elif pag == "artista":
            from .paginas.artista import PaginaArtista
            w = PaginaArtista(self.ctx, destino["id"])
        elif pag in ("album", "lista", "mi_lista", "me_gusta", "disco"):
            from .paginas.coleccion import PaginaColeccion
            w = PaginaColeccion(self.ctx, destino)
        elif pag == "lista_compartida":
            from .paginas.lista_compartida import PaginaListaCompartida
            w = PaginaListaCompartida(self.ctx, destino)
        elif pag == "mix":
            from .paginas.inicio import PaginaMix
            w = PaginaMix(self.ctx, destino)
        elif pag == "resumen":
            from .paginas.resumen import PaginaResumen
            w = PaginaResumen(self.ctx)
        elif pag == "biblioteca":
            from .paginas.biblioteca import PaginaBiblioteca
            w = PaginaBiblioteca(self.ctx)
        elif pag == "descargas":
            from .paginas.descargas import PaginaDescargas
            w = PaginaDescargas(self.ctx)
        elif pag == "ajustes":
            from .paginas.ajustes import PaginaAjustes
            w = PaginaAjustes(self.ctx)
        elif pag == "mensajes":
            from .paginas.mensajes import PaginaMensajes
            w = PaginaMensajes(self.ctx)
        elif pag == "letra":
            from .letra_viva import PaginaLetra
            w = PaginaLetra(self.ctx)
            w.volver.connect(self.cerrar_letra)
        elif pag == "vinilo":
            from .vinilo import PaginaVinilo
            w = PaginaVinilo(self.ctx)
            w.volver.connect(self.cerrar_vinilo)
        elif pag == "estudio":
            from .paginas.estudio import PaginaEstudio
            w = PaginaEstudio(self.ctx)
        elif pag == "gamer":
            from .paginas.modo_gamer import PaginaModoGamer
            w = PaginaModoGamer(self.ctx)
        elif pag == "video":
            from .video import VistaVideo
            w = VistaVideo(self.ctx)
            w.volver.connect(self.atras_desde_video)
            w.pidio_mini.connect(self.alternar_mini)
            w.pidio_completa.connect(self.alternar_completa)
        if w is None and pag == "mezclador":
            from .paginas.mezclador import PaginaMezclador
            w = PaginaMezclador(self.ctx)
        if w is None:
            # perfiles, directorio, amigos, subir música y comunidad
            from .paginas.perfil_rutas import fabricar
            w = fabricar(self.ctx, destino)
        if w is None:
            from .paginas.inicio import PaginaInicio
            w = PaginaInicio(self.ctx)
        if pag in SINGLETONS:
            self.singletons[pag] = w
        self.pila.addWidget(w)
        return w

    def navegar(self, destino, reemplazar=False):
        if destino.get("pagina") != "estudio" and self._estudio_en_curso():
            # un bloque de estudio en curso: antes de irse, se pregunta
            self._guardia_estudio(lambda: self.navegar(destino, reemplazar))
            return
        if self.en_completa and destino.get("pagina") != "video":
            self.alternar_completa()
        # ajustes y paginas unicas: si ya estas ahi, no se duplica
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else None
        if actual and actual == destino and not destino.get("editar"):
            w = self.historia[self.indice][1]
            if destino.get("pagina") in ("inicio",) and w is not None:
                # volver a Inicio refresca lo reciente (solo eso: el resto de Inicio no cambió)
                refrescar = getattr(w, "refrescar_recientes", None)
                if refrescar is not None:
                    try:
                        refrescar()
                        self._mostrar(destino, w)
                        return
                    except RuntimeError:
                        pass
                reemplazar = True
            else:
                return
        if reemplazar and 0 <= self.indice < len(self.historia):
            _d, viejo = self.historia[self.indice]
            self._soltar(viejo)
            w = self._fabricar(destino)
            self.historia[self.indice] = (destino, w)
        else:
            for _d, viejo in self.historia[self.indice + 1:]:
                self._soltar(viejo)
            self.historia = self.historia[:self.indice + 1]
            w = self._fabricar(destino)
            self.historia.append((destino, w))
            self.indice = len(self.historia) - 1
            self._podar()
        self._mostrar(destino, w)

    def _soltar(self, w):
        if w is None or w in self.singletons.values():
            return
        if any(x is w for _d, x in self.historia):
            # sigue en otra posicion del historial
            usos = sum(1 for _d, x in self.historia if x is w)
            if usos > 1:
                return
        self.pila.removeWidget(w)
        w.deleteLater()

    def _podar(self):
        """Solo las 12 ultimas paginas se quedan vivas; las demas se rehacen al volver."""
        vivas = [i for i, (_d, w) in enumerate(self.historia)
                 if w is not None and w not in self.singletons.values()]
        for i in vivas[:-12]:
            d, w = self.historia[i]
            self.pila.removeWidget(w)
            w.deleteLater()
            self.historia[i] = (d, None)

    def _mostrar(self, destino, w):
        est = getattr(self.ctx, "estudio", None)
        if est is not None and destino.get("pagina") != "estudio":
            est.salir_del_modo()        # fuera de la pantalla de estudio: todo vuelve a su sitio
        cambio = self.pila.currentWidget() is not w
        self.pila.setCurrentWidget(w)
        self._ajustar_barra(destino.get("pagina"))
        if cambio and destino.get("pagina") != "video":
            from .componentes import aparecer
            aparecer(w)
        self.lateral.marcar(destino)
        pag = destino.get("pagina")
        if pag == "buscar":
            if self.campo.text().strip() != destino.get("q", ""):
                self.campo.setText(destino.get("q", ""))
        elif not self.campo.hasFocus():
            self.campo.clear()
        self.bt_atras.setEnabled(self.indice > 0)
        self.bt_adelante.setEnabled(self.indice < len(self.historia) - 1)
        self.bt_resumen.set_activo(pag == "resumen", punto=False)
        self.bt_perfil.set_activo(pag == "perfil" and not destino.get("usuario"), punto=False)
        self.bt_mensajes.set_activo(pag == "mensajes" or self._sin_leer > 0, punto=self._sin_leer > 0)
        self.bt_descargas.set_activo(pag == "descargas", punto=False)
        self.bt_ajustes.set_activo(pag == "ajustes", punto=False)
        if hasattr(self, "barra") and hasattr(self, "panel_der"):
            self.barra.bt_vinilo.set_activo(pag == "vinilo", punto=False)
            self.barra.bt_letras.set_activo(pag == "letra" or (
                self.panel_der.isVisible() and self.panel_der.actual == "letras"))
        titulo = getattr(w, "titulo", "") or ""
        self.setWindowTitle(f"{titulo} · {APP_NOMBRE}" if titulo and pag != "inicio" else APP_NOMBRE)

    def _ajustar_barra(self, pagina=None):
        """La vista de video trae sus propios controles: la barra de abajo se
        oculta ahi para no mostrar dos reproductores a la vez."""
        if not hasattr(self, "barra"):
            return
        if pagina is None:
            pagina = self.historia[self.indice][0].get("pagina") if 0 <= self.indice < len(self.historia) else ""
        self.barra.setVisible(not getattr(self, "en_completa", False) and pagina != "video")

    def _mirar_mensajes(self):
        from .paginas.mensajes import chat_de
        from ..hilos import en_segundo_plano
        c = chat_de(self.ctx)
        if c is None:
            return

        def listo(n):
            self._sin_leer = int(n or 0)
            en_mensajes = bool(self.historia) and self.historia[self.indice][0].get("pagina") == "mensajes"
            self.bt_mensajes.set_activo(en_mensajes or self._sin_leer > 0, punto=self._sin_leer > 0)
            self.bt_mensajes.setToolTip(f"Mensajes ({self._sin_leer} sin leer)" if self._sin_leer else "Mensajes")

        en_segundo_plano(c.sin_leer, ok=listo, error=lambda _e: None, dueno=self, urgente=True)

    def atras(self):
        if self.indice > 0:
            self._ir(self.indice - 1)

    def adelante(self):
        if self.indice < len(self.historia) - 1:
            self._ir(self.indice + 1)

    def _ir(self, i):
        if self._estudio_en_curso() and 0 <= i < len(self.historia) \
                and self.historia[i][0].get("pagina") != "estudio":
            self._guardia_estudio(lambda: self._ir(i))
            return
        if self.en_completa:
            self.alternar_completa()
        self.indice = i
        d, w = self.historia[i]
        if w is None:
            w = self._fabricar(d)
            self.historia[i] = (d, w)
            self._podar()
        self._mostrar(d, w)

    def atras_desde_video(self):
        if self.en_completa:
            self.alternar_completa()
        if self.indice > 0:
            self.atras()
        else:
            self.navegar({"pagina": "inicio"})

    def mostrar_video(self):
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        if actual.get("pagina") != "video":
            self.navegar({"pagina": "video"})
        if self.mini.isVisible():
            self.mini.close()

    # ------------------------------------------------------------ busqueda

    def _buscar_ahora(self):
        self._t_buscar.stop()
        texto = self.campo.text().strip()
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        destino = {"pagina": "buscar", "q": texto}
        self.navegar(destino, reemplazar=actual.get("pagina") == "buscar")

    def buscar_texto(self, texto):
        self.campo.setText(texto)
        self._buscar_ahora()

    def enfocar_busqueda(self):
        self.campo.setFocus()
        self.campo.selectAll()
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        if actual.get("pagina") != "buscar":
            self.navegar({"pagina": "buscar", "q": self.campo.text().strip()})

    # ------------------------------------------------------------ conexiones

    def _conectar(self):
        self.lateral.ir.connect(self.navegar)
        self.lateral.traer_lista.connect(self._traer_lista)
        self.barra.pidio_panel.connect(self.alternar_panel)
        self.barra.pidio_letra.connect(self.alternar_letra)
        self.barra.pidio_video.connect(self._ver_video)
        self.barra.pidio_vinilo.connect(self.alternar_vinilo)
        self.r.estado_cambio.connect(self._vinilo_auto)
        self.barra.pidio_mini.connect(self.alternar_mini)
        self.barra.pidio_ecualizador.connect(self.abrir_ecualizador)
        self.panel_der.cerrado.connect(lambda: self.alternar_panel(None))
        self.panel_der.cambio.connect(lambda n: self.barra.marcar_panel(n))
        self.ctx.aviso.connect(self.aviso.mostrar)
        self.r.aviso.connect(self.aviso.mostrar)
        self.r.error.connect(lambda t: self.aviso.mostrar(t, 6000))
        self.r.pista_cambio.connect(self._al_cambiar_pista)
        self.r.estado_cambio.connect(lambda _e: self._tooltip_bandeja())
        self.r.modo_cambio.connect(self._al_cambiar_modo)
        g = self.ctx.gestor
        g.tarea_finalizada.connect(self._descarga_terminada)
        # el progreso de cada descarga avisa varias veces por segundo: el conteo del botón se
        # agrupa (un recuento cada 250 ms como mucho)
        self._t_contar = QTimer(self)
        self._t_contar.setSingleShot(True)
        self._t_contar.setInterval(250)
        self._t_contar.timeout.connect(self._contar_descargas)
        g.tarea_agregada.connect(self._programar_conteo)
        g.cola_cambio.connect(self._programar_conteo)
        g.tarea_cambio.connect(self._programar_conteo)
        QGuiApplication.clipboard().dataChanged.connect(self._portapapeles)

    def _atajos(self):
        def atajo(secuencia, accion):
            QShortcut(QKeySequence(secuencia), self, activated=accion)
        atajo("Ctrl+K", self.enfocar_busqueda)
        atajo("Ctrl+L", self.enfocar_busqueda)
        atajo("Ctrl+F", self.enfocar_busqueda)
        atajo("Alt+Left", self.atras)
        atajo("Alt+Right", self.adelante)
        atajo("Ctrl+Right", self.r.siguiente)
        atajo("Ctrl+Left", self.r.anterior)
        atajo("Shift+Right", lambda: self.r.avanzar(10))
        atajo("Shift+Left", lambda: self.r.avanzar(-10))
        atajo("Ctrl+Up", lambda: self.barra.subir_volumen(5))
        atajo("Ctrl+Down", lambda: self.barra.subir_volumen(-5))
        atajo("Ctrl+S", self.barra._aleatorio)
        atajo("Ctrl+R", self.barra._repetir)
        atajo("Ctrl+Q", self.salir)
        atajo("Ctrl+O", lambda: os.path.isdir(self.ajustes["carpeta"])
              and os.startfile(self.ajustes["carpeta"]))
        atajo("Ctrl+D", lambda: self.navegar({"pagina": "descargas"}))
        atajo("Ctrl+,", lambda: self.navegar({"pagina": "ajustes"}))
        atajo("Ctrl+Shift+L", self.alternar_letra)
        atajo("Ctrl+Shift+Q", lambda: self.alternar_panel("cola"))
        atajo("Ctrl+M", self.alternar_mini)
        atajo("F11", self.alternar_completa)
        atajo("Escape", lambda: self.en_completa and self.alternar_completa()
              or self._escape_estudio()
              or self._en_vinilo() and self.cerrar_vinilo())
        atajo("Ctrl+Shift+A", self._anadir_sonando_a_lista)
        atajo("Ctrl+Shift+E", self.abrir_estudio)
        atajo("Ctrl+Shift+N", self._notas_estudio)
        # en la vista de video: F, I, M y flechas como en YouTube
        for tecla, accion in (("F", self._f_video), ("I", self.alternar_mini),
                              ("M", self.barra._silenciar),
                              ("Right", lambda: self._en_video() and self.r.avanzar(5)),
                              ("Left", lambda: self._en_video() and self.r.avanzar(-5)),
                              ("J", lambda: self._en_video() and self.r.avanzar(-10)),
                              ("L", lambda: self._en_video() and self.r.avanzar(10)),
                              ("K", lambda: self._en_video() and self.r.alternar())):
            sc = QShortcut(QKeySequence(tecla), self)
            sc.setContext(Qt.WindowShortcut)
            sc.activated.connect(lambda a=accion: self._si_no_escribe(a))
        sc = QShortcut(QKeySequence("Ctrl+V"), self)
        sc.activated.connect(self._pegar_global)
        # Espacio: reproducir / pausar (no cuando se escribe o hay un botón con el foco, que ya usa Espacio)
        sp = QShortcut(QKeySequence("Space"), self)
        sp.setContext(Qt.WindowShortcut)
        sp.activated.connect(self._espacio)
        bar = QShortcut(QKeySequence("/"), self)
        bar.setContext(Qt.WindowShortcut)
        bar.activated.connect(lambda: self._si_no_escribe(self.enfocar_busqueda))

    def _si_no_escribe(self, accion):
        foco = QApplication.focusWidget()
        if isinstance(foco, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox)):
            return
        accion()

    def _espacio(self):
        foco = QApplication.focusWidget()
        if isinstance(foco, (QAbstractButton, QSlider)):
            return
        self._si_no_escribe(self.r.alternar)

    def _anadir_sonando_a_lista(self):
        p = getattr(self.r, "actual", None)
        if not p:
            self.ctx.aviso.emit("Ahora no suena nada: pon una canción y vuelve a pulsar Ctrl+Mayús+A.")
            return
        self.ctx.elegir_listas([p])

    def _en_video(self):
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        return actual.get("pagina") == "video" and self.r.modo == "video"

    def _f_video(self):
        if self._en_video():
            self.alternar_completa()

    def _pegar_global(self):
        foco = QApplication.focusWidget()
        if isinstance(foco, QLineEdit):
            foco.paste()
            return
        texto = QGuiApplication.clipboard().text().strip()
        from .. import listas_compartidas as LC
        if ("/l/" in texto or "caudal://lista" in texto) and LC.extraer_codigo(texto):
            self.ctx.tengo_un_codigo(texto)         # pegaron un enlace de lista de Caudal
        elif redes.extraer_urls(texto):
            self.buscar_texto(texto)

    # ------------------------------------------------------------ reproduccion

    def _al_cambiar_pista(self, p):
        self._tooltip_bandeja()
        if p is not None and self.ajustes["teclas_multimedia"] and hasattr(self, "teclas_multimedia"):
            self.teclas_multimedia.registrar()
        if p and self.ajustes["letras_auto"] and self.panel_der.isVisible() and self.r.modo == "audio":
            self.panel_der.mostrar("letras")

    def _al_cambiar_modo(self, modo):
        if modo == "audio":
            actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
            if actual.get("pagina") == "video" and not self.en_completa:
                pass

    def _ver_video(self):
        if self.r.modo != "video":
            if self.r.actual is None:
                return
            self.r.cambiar_modo("video")
        self.mostrar_video()

    def alternar_letra(self):
        """La letra a pantalla completa; si ya esta abierta, se vuelve."""
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        if actual.get("pagina") == "letra":
            self.cerrar_letra()
        else:
            self.navegar({"pagina": "letra"})

    def _en_vinilo(self):
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        return actual.get("pagina") == "vinilo"

    def alternar_vinilo(self):
        """El modo vinilo a pantalla completa; si ya esta abierto, se vuelve."""
        if self._en_vinilo():
            self.cerrar_vinilo()
        elif self.r.actual is not None:
            self.navegar({"pagina": "vinilo"})

    def cerrar_vinilo(self):
        if self.indice > 0:
            self.atras()
        else:
            self.navegar({"pagina": "inicio"})

    def _vinilo_auto(self, estado):
        """Con «Mostrar el vinilo al reproducir», se abre al empezar cada cancion."""
        p = self.r.actual
        if estado != "sonando" or not p or not self.ajustes["vinilo_auto"] or self.r.modo != "audio":
            return
        clave = p.get("clave") or p.get("video_id")
        if clave == getattr(self, "_vinilo_clave", None):
            return
        self._vinilo_clave = clave
        if not self._en_vinilo() and not self.en_completa:
            self.navegar({"pagina": "vinilo"})

    def cerrar_letra(self):
        if self.indice > 0:
            self.atras()
        else:
            self.navegar({"pagina": "inicio"})

    def alternar_panel(self, nombre):
        if nombre is None or (self.panel_der.isVisible() and self.panel_der.actual == nombre):
            self.panel_der.hide()
            self.ajustes["panel_derecho"] = "oculto"
            self.barra.marcar_panel("")
        else:
            self.panel_der.show()
            self.panel_der.mostrar(nombre)
            self.ajustes["panel_derecho"] = nombre
        self.ajustes.guardar()

    def alternar_mini(self):
        if self.mini.isVisible():
            self.mini.close()
        else:
            if self.en_completa:
                self.alternar_completa()
            self.mini.abrir()

    def _mini_expandir(self):
        self.mini.close()
        self.traer_al_frente()
        if self.r.modo == "video":
            self.mostrar_video()

    def alternar_completa(self):
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else {}
        if not self.en_completa:
            if self.r.modo != "video":
                return
            if actual.get("pagina") != "video":
                self.mostrar_video()
            self._antes_completa = (self.isMaximized(), self.panel_der.isVisible())
            self.en_completa = True
            for w in (self.lateral, self.panel_der, self.barra,
                      self.centro.layout().itemAt(0).widget()):
                w.hide()
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.centro.setStyleSheet("QFrame#panel_centro{border-radius:0;background:#000;}")
            self.showFullScreen()
            vista = self.singletons.get("video")
            if vista:
                vista.modo_completa(True)
        else:
            self.en_completa = False
            maximizada, panel = getattr(self, "_antes_completa", (False, True))
            for w in (self.lateral, self.barra, self.centro.layout().itemAt(0).widget()):
                w.show()
            self._ajustar_barra()
            if panel:
                self.panel_der.show()
            self.layout().setContentsMargins(8, 8, 8, 0)
            self.centro.setStyleSheet("")
            if maximizada:
                self.showMaximized()
            else:
                self.showNormal()
            vista = self.singletons.get("video")
            if vista:
                vista.modo_completa(False)

    def abrir_ecualizador(self):
        from .ecualizador import DialogoEcualizador
        DialogoEcualizador(self.ctx, self).exec()

    # ------------------------------------------------------------ descargas

    def _programar_conteo(self, *_a):
        if not self._t_contar.isActive():
            self._t_contar.start()

    def _contar_descargas(self):
        activas = sum(1 for t in self.ctx.gestor.lista() if t.activa or t.estado == "en_cola")
        self.bt_descargas.setToolTip(f"Descargas · {activas} en marcha" if activas else "Descargas")
        self.bt_descargas.set_icono("descarga_circulo" if activas else "descargar")
        self.bt_descargas.set_activo(bool(activas), punto=bool(activas))

    def _descarga_terminada(self, ident, ok):
        self.ctx.coleccion.invalidar_indice()
        self.ctx.descargas_cambio.emit()
        t = self.ctx.gestor.tareas.get(ident)
        if ok and t and self.ajustes["notificar_al_terminar"] and self.bandeja:
            self.bandeja.showMessage("Descarga completada", t.titulo[:120],
                                     QSystemTrayIcon.Information, 3500)

    def _traer_lista(self):
        from .dialogo_listas import DialogoListas
        dialogo = DialogoListas(self.ajustes, self)
        dialogo.descargar.connect(self._lista_traida)
        dialogo.guardar.connect(self._guardar_lista_traida)
        dialogo.exec()

    def _lista_traida(self, canciones):
        """«Descargar»: las canciones elegidas van a la cola de descargas en MP3."""
        if not canciones:
            return
        for c in canciones:
            enlace = c.get("url") or ("ytsearch1:" + (c.get("busqueda") or c.get("titulo") or ""))
            nombre = c.get("titulo") or ""
            if c.get("artista"):
                nombre = f"{c['artista']} - {nombre}"
            self.ctx.gestor.agregar(enlace, tipo="audio", titulo=nombre)
        self.aviso.mostrar(f"{len(canciones)} canciones en la cola de descargas")

    def _guardar_lista_traida(self, canciones, titulo):
        """«Guardar como lista»: se busca cada canción y queda como lista tuya
        (sincronizada: también aparece en el teléfono y en la web)."""
        if not canciones:
            return

        def una(c):
            vid = catalogo.video_id_de(c.get("url") or "")
            if vid:
                return catalogo.nueva_pista(vid, c.get("titulo") or "",
                                            [{"nombre": c.get("artista") or "", "id": ""}])
            consulta = c.get("busqueda") or f"{c.get('artista', '')} {c.get('titulo', '')}"
            for _ in range(2):
                try:
                    hallado = catalogo.buscar(consulta.strip(), "canciones", 1)
                    return hallado[0] if hallado else None
                except Exception:  # noqa: BLE001
                    continue
            return None

        def resolver():
            # de cuatro en cuatro: una lista de 50 tarda segundos, no un minuto
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=4) as grupo:
                return [p for p in grupo.map(una, canciones) if p]

        def listo(pistas):
            if not pistas:
                self.aviso.mostrar("No se encontró ninguna de esas canciones")
                return
            col = self.ctx.coleccion
            nombre = (titulo or "Lista traída").strip()[:80]
            if any(l["nombre"] == nombre for l in col.listas()):
                nombre = col.nombre_libre(nombre)
            lista_id = col.crear_lista(nombre)
            col.agregar_a_lista(lista_id, pistas)
            self.ctx.listas_cambio.emit()
            self.navegar({"pagina": "mi_lista", "id": lista_id})
            faltan = len(canciones) - len(pistas)
            self.aviso.mostrar(f"Lista «{nombre}» guardada con {len(pistas)} canciones"
                               + (f" ({faltan} no se encontraron)" if faltan else ""))

        self.aviso.mostrar(f"Buscando {len(canciones)} canciones en YouTube Music…", 8000)
        en_segundo_plano(resolver, ok=listo, error=lambda e: self.aviso.mostrar(str(e)), dueno=self)

    # ------------------------------------------------------------ bandeja

    def _bandeja(self):
        self.bandeja = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.bandeja = QSystemTrayIcon(QIcon(iconos.icono_app(64)), self)
        self.bandeja.setToolTip(APP_NOMBRE)
        menu = QMenu()
        menu.addAction(iconos.icono("reproducir", 16, C["texto2"]), "Reproducir / pausar",
                       self.r.alternar)
        menu.addAction(iconos.icono("siguiente", 16, C["texto2"]), "Siguiente", self.r.siguiente)
        menu.addAction(iconos.icono("anterior", 16, C["texto2"]), "Anterior", self.r.anterior)
        menu.addSeparator()
        menu.addAction(iconos.icono("mini", 16, C["texto2"]), "Mini reproductor", self.alternar_mini)
        menu.addAction("Mostrar Caudal", self.traer_al_frente)
        menu.addSeparator()
        menu.addAction("Salir", self.salir)
        self.bandeja.setContextMenu(menu)
        self._menu_bandeja = menu
        self.bandeja.activated.connect(
            lambda razon: self.traer_al_frente() if razon == QSystemTrayIcon.Trigger else None)
        self.bandeja.show()

    def _tooltip_bandeja(self):
        if not self.bandeja:
            return
        p = self.r.actual
        if p:
            estado = {"sonando": "▶", "pausa": "⏸", "cargando": "…"}.get(self.r.estado, "")
            self.bandeja.setToolTip(f"{estado} {p.get('titulo', '')} — {p.get('artista', '')}"[:120])
        else:
            self.bandeja.setToolTip(APP_NOMBRE)

    def traer_al_frente(self):
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------ portapapeles

    def _portapapeles(self):
        if not self.ajustes["vigilar_portapapeles"]:
            return
        try:
            texto = QGuiApplication.clipboard().text().strip()
        except RuntimeError:
            return
        if not texto or texto == self._ultimo_portapapeles:
            return
        self._ultimo_portapapeles = texto
        urls = redes.extraer_urls(texto)
        if urls and redes.detectar(urls[0]) is not redes.DESCONOCIDA:
            if self.isActiveWindow():
                self.buscar_texto(urls[0])
            elif self.bandeja:
                self.bandeja.showMessage("Enlace detectado",
                                         "Abre Caudal para reproducirlo o descargarlo.",
                                         QSystemTrayIcon.Information, 3000)

    # ------------------------------------------------------------ version

    def buscar_version(self, callado):
        if self.buscador_version and self.buscador_version.isRunning():
            return
        self.buscador_version = Buscador()
        self.buscador_version.resultado.connect(lambda n: self._responder_version(n, callado))
        self.buscador_version.start()
        if not callado:
            self.aviso.mostrar("Buscando actualizaciones…")

    def _responder_version(self, novedad, callado):
        if not novedad:
            if not callado:
                self.aviso.mostrar(f"Tienes la versión {version.VERSION}, la más reciente.")
            return
        abiertos = (self._aviso_grande, getattr(self, "_aviso_mascotas", None))
        if any(a is not None and a.isVisible() for a in abiertos):
            # no se apilan dos avisos: este sale cuando se cierre el de novedades
            self._novedad_pendiente = novedad
            return
        mostrar_aviso(novedad, self)

    def _buscar_avisos(self):
        """Los avisos que se mandan a todas las apps (descargador/avisos.py): cada uno sale una vez."""
        if self.en_completa or self._saliendo:
            QTimer.singleShot(20000, self._buscar_avisos)
            return
        from .. import avisos
        from ..hilos import en_segundo_plano

        def listos(lista):
            if lista and not self._saliendo:
                from .aviso_caudal import mostrar_avisos
                mostrar_avisos(lista, self)

        en_segundo_plano(avisos.pendientes, ok=listos, error=lambda _e: None, dueno=self)

    def _avisar_novedades(self):
        """Una sola vez por versión, y sin tocar la música."""
        if self.en_completa or self._saliendo:
            QTimer.singleShot(20000, self._avisar_novedades)
            return
        from .novedades_grandes import mostrar_si_toca
        try:
            self._aviso_grande = mostrar_si_toca(self)
        except Exception:  # noqa: BLE001 - un aviso nunca debe romper la app
            self._aviso_grande = None
            return
        if self._aviso_grande is not None:
            self._grande_en_sesion = True
            self._aviso_grande.finished.connect(self._tras_novedades)
            return
        # la presentación de la 2.4.2 (mascotitas y fondos): si en este arranque ya salió la
        # de la edición grande, espera al siguiente para que no se encimen
        from . import presentacion_mascotas
        try:
            otra = True if getattr(self, "_grande_en_sesion", False) else None
            self._aviso_mascotas = presentacion_mascotas.mostrar_si_toca(self, otra)
        except Exception:  # noqa: BLE001
            self._aviso_mascotas = None
            return
        if self._aviso_mascotas is not None:
            self._aviso_mascotas.finished.connect(self._tras_novedades)

    def _avisar_regalo(self):
        """El aviso único de los códigos de regalo: espera a que no haya otro aviso abierto."""
        from . import aviso_regalo
        if self._aviso_regalo is not None or not aviso_regalo.debe_mostrarse(self.ajustes, self.premium):
            return
        if (self.en_completa or self._saliendo or self._aviso_grande is not None
                or self._aviso_mascotas is not None):
            self._t_regalo.start(20000)
            return
        try:
            self._aviso_regalo = aviso_regalo.mostrar_si_toca(self)
        except Exception:  # noqa: BLE001 - un aviso nunca debe romper la app
            self._aviso_regalo = None
            return
        if self._aviso_regalo is not None:
            self._aviso_regalo.finished.connect(lambda _r=0: setattr(self, "_aviso_regalo", None))

    def ir_a_regalo(self):
        """Lleva a Ajustes, a la tarjeta «Regala una prueba a tus amigos»."""
        self.navegar({"pagina": "ajustes"})
        QTimer.singleShot(250, self._mostrar_tarjeta_regalo)

    def _mostrar_tarjeta_regalo(self):
        mostrar = getattr(self.pila.currentWidget(), "mostrar_regalo", None)
        if callable(mostrar):
            mostrar()

    def _tras_novedades(self, _resultado=0):
        self._aviso_grande = None
        self._aviso_mascotas = None
        pendiente, self._novedad_pendiente = self._novedad_pendiente, None
        if pendiente:
            QTimer.singleShot(400, lambda: mostrar_aviso(pendiente, self))

    # ------------------------------------------------------------ arrastrar y soltar

    def dragEnterEvent(self, e):
        datos = e.mimeData()
        if datos.hasUrls() or datos.hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        datos = e.mimeData()
        archivos, enlaces = [], []
        if datos.hasUrls():
            for u in datos.urls():
                if u.isLocalFile():
                    archivos.append(u.toLocalFile())
                else:
                    enlaces.append(u.toString())
        elif datos.hasText():
            enlaces = redes.extraer_urls(datos.text())
        medios = [a for a in archivos
                  if os.path.splitext(a)[1].lower() in EXT_AUDIO | EXT_VIDEO]
        if medios:
            pistas = []
            for a in medios:
                ext = os.path.splitext(a)[1].lower()
                es_audio = ext in EXT_AUDIO and ext not in EXT_VIDEO - {".webm"}
                pistas.append({"tipo": "pista", "clave": "archivo:" + a, "archivo": a,
                               "titulo": os.path.splitext(os.path.basename(a))[0],
                               "artistas": [], "artista": "Archivo de tu equipo", "album": {},
                               "duracion": 0, "miniatura": "", "es_audio": es_audio,
                               "es_video": not es_audio})
            self.ctx.reproducir_lista(pistas, 0, {"tipo": "archivos", "id": "archivos",
                                                  "titulo": "Archivos de tu equipo"})
            e.acceptProposedAction()
            return
        enlaces = redes.extraer_urls(" ".join(enlaces))
        if enlaces:
            self.buscar_texto(" ".join(enlaces))
            e.acceptProposedAction()

    # ------------------------------------------------------------ cierre

    # ------------------------------------------------------------ fondo de Caudal

    def _montar_fondo(self):
        from .fondo_capa import CapaFondo
        self._instantanea = None
        self._velo = None
        self.capa_fondo = CapaFondo(self.fondo, self)
        self.capa_fondo.setGeometry(self.rect())
        self.capa_fondo.lower()
        self.capa_fondo.setVisible(self._con_capa())
        # el personaje del fondo elegido, sentado sobre la barra del reproductor
        from .fondo_capa import PersonajeEsquina
        self.personaje_fondo = PersonajeEsquina(self, getattr(self, "barra", None),
                                                getattr(self.ctx, "reproductor", None))
        self.personaje_fondo.colocar()
        self.fondo.antes_de_cambiar.connect(self._fondo_antes)
        self.fondo.cambiado.connect(self._fondo_cambiado)

    def _con_capa(self):
        """La capa de fondo se ve con la imagen de «Fondo de Caudal» o con un fondo con personaje."""
        from . import estilos
        return self.fondo.activo or estilos.patron_actual() is not None

    def _fondo_antes(self):
        # una foto de lo que se ve ahora: se desvanece encima mientras aparece lo nuevo
        self._instantanea = self.grab() if self.isVisible() and not self.en_completa else None

    def _fondo_cambiado(self, encendido_o_apagado):
        from . import estilos
        if encendido_o_apagado:
            estilos.FONDO["activo"] = self._con_capa()
            self.setStyleSheet(hoja(iconos.flechas_qss()))
            self.capa_fondo.setVisible(self._con_capa())
            self.capa_fondo.lower()
        foto, self._instantanea = self._instantanea, None
        if foto is not None:
            self._desvanecer(foto)

    def _desvanecer(self, foto, ms=300):
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation
        from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel
        if self._velo is not None:
            self._velo.deleteLater()
        velo = QLabel(self)
        velo.setPixmap(foto)
        velo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        velo.setGeometry(self.rect())
        efecto = QGraphicsOpacityEffect(velo)
        velo.setGraphicsEffect(efecto)
        velo.show()
        velo.raise_()
        self._velo = velo
        anim = QPropertyAnimation(efecto, b"opacity", velo)
        anim.setDuration(ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        def fin():
            if self._velo is velo:
                self._velo = None
            velo.deleteLater()
        anim.finished.connect(fin)
        anim.start()

    def _dejar_a_la_vista(self):
        """Si el tamaño o la posición recordados quedaron fuera de la pantalla (otro monitor, otra
        resolución), la ventana vuelve a caber y a verse."""
        pantalla = QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()
        if pantalla is None:
            return
        area = pantalla.availableGeometry()
        g = self.frameGeometry()
        if not area.intersects(g) or g.width() > area.width() or g.height() > area.height():
            self.resize(min(self.width(), area.width() - 40), min(self.height(), area.height() - 60))
            self.move(area.x() + (area.width() - self.width()) // 2, area.y() + (area.height() - self.height()) // 2)

    def _ajustar_letra(self):
        """La letra se adapta al ancho: un poco más chica en ventanas estrechas y más grande en pantallas anchas.
        Solo se rehace la hoja de estilos al cruzar un umbral (no en cada pixel que se arrastra)."""
        from . import estilos
        ancho = self.width()
        base = 12.5 if ancho < 1180 else (14 if ancho >= 1900 else 13)
        if base != estilos.ESCALA["base"]:
            estilos.ESCALA["base"] = base
            self.setStyleSheet(hoja(iconos.flechas_qss()))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_t_letra", None) is not None:
            self._t_letra.start()
        if getattr(self, "capa_fondo", None) is not None:
            self.capa_fondo.setGeometry(self.rect())
        if getattr(self, "personaje_fondo", None) is not None:
            self.personaje_fondo.colocar()
        if self.aviso.isVisible():
            self.aviso.move((self.width() - self.aviso.width()) // 2,
                            self.height() - self.aviso.height() - 120)

    # ------------------------------------------------------------ modo estudio

    def _estudio_en_curso(self):
        est = getattr(self.ctx, "estudio", None)
        return est is not None and est.hay_bloque()

    def _guardia_estudio(self, accion):
        """«¿Salir de tu sesión de estudio?» con un bloque en curso: «Salir» termina la
        sesión y sigue con `accion`; «Seguir estudiando» deja todo como está."""
        from .estudio_enfoque import confirmar_salida
        marco = self.vista_enfoque if getattr(self, "vista_enfoque", None) is not None \
            and self.vista_enfoque.isVisible() else self
        confirmar_salida(marco, self.ctx.estudio, accion)

    def abrir_estudio(self):
        self.navegar({"pagina": "estudio"})

    def abrir_enfoque(self):
        """La vista «Cero distracciones» sobre toda la ventana."""
        from .estudio_enfoque import VistaEnfoque
        if getattr(self, "vista_enfoque", None) is None:
            from .. import estudio
            self.vista_enfoque = VistaEnfoque(self.ctx, self, estudio.de(self.ctx))
        self.vista_enfoque.abrir()

    def _vista_enfoque_abierta(self):
        v = getattr(self, "vista_enfoque", None)
        return v is not None and v.isVisible()

    def _escape_estudio(self):
        """Esc en el modo estudio. True si lo atendió."""
        if self._vista_enfoque_abierta():
            return self.vista_enfoque.escape()
        c = getattr(self, "_confirma_estudio", None)
        if c is not None and c.isVisible():
            c.seguir.emit()
            return True
        return False

    def _notas_estudio(self):
        """Ctrl+Mayús+N: la «Captura de ideas», solo dentro del modo estudio."""
        if self._vista_enfoque_abierta():
            self.vista_enfoque.alternar_notas()
            return
        actual = self.historia[self.indice][1] if 0 <= self.indice < len(self.historia) else None
        if actual is not None and hasattr(actual, "alternar_notas"):
            actual.alternar_notas()

    def closeEvent(self, e):
        if not self._saliendo and self._estudio_en_curso():
            e.ignore()
            self._guardia_estudio(self.close)
            return
        if self.en_completa:
            self.alternar_completa()
            e.ignore()
            return
        if self._saliendo:
            e.accept()
            return
        sonando = self.r.estado in ("sonando", "cargando")
        if sonando and self.bandeja:
            eleccion = self.ajustes["al_cerrar"]
            if eleccion not in ("bandeja", "salir"):
                eleccion = self._preguntar_al_cerrar()
                if eleccion is None:
                    e.ignore()
                    return
            if eleccion == "bandeja":
                e.ignore()
                self._a_la_bandeja()
                return
        activas = [t for t in self.ctx.gestor.lista() if t.activa]
        if activas:
            r = QMessageBox.question(self, APP_NOMBRE,
                                     f"Hay {len(activas)} descarga(s) en marcha. Si sales ahora se "
                                     "detienen y podrás retomarlas al volver. ¿Salir igualmente?")
            if r != QMessageBox.Yes:
                e.ignore()
                return
        e.ignore()
        self.salir()

    def _preguntar_al_cerrar(self):
        """Primera vez que se cierra con musica: se pregunta y se puede recordar."""
        from PySide6.QtWidgets import QCheckBox
        caja = QMessageBox(self)
        caja.setWindowTitle(APP_NOMBRE)
        caja.setIcon(QMessageBox.Question)
        caja.setText("¿Qué hacemos con la música?")
        caja.setInformativeText("Caudal puede seguir sonando en segundo plano, junto al reloj de "
                                "Windows, o cerrarse del todo.")
        seguir = caja.addButton("Seguir sonando", QMessageBox.AcceptRole)
        cerrar = caja.addButton("Cerrar Caudal", QMessageBox.DestructiveRole)
        caja.addButton("Cancelar", QMessageBox.RejectRole)
        recordar = QCheckBox("Recordar mi elección (se cambia en Ajustes)")
        caja.setCheckBox(recordar)
        caja.setDefaultButton(seguir)
        caja.exec()
        elegido = caja.clickedButton()
        if elegido is seguir:
            eleccion = "bandeja"
        elif elegido is cerrar:
            eleccion = "salir"
        else:
            return None
        if recordar.isChecked():
            self.ajustes["al_cerrar"] = eleccion
            self.ajustes.guardar()
        return eleccion

    def _a_la_bandeja(self):
        if self.mini and self.mini.isVisible():
            pass
        self.hide()
        if not self._aviso_bandeja:
            self._aviso_bandeja = True
            self.bandeja.showMessage(
                "Caudal sigue sonando",
                "Está junto al reloj. Clic para abrirlo; clic derecho → Salir para cerrarlo.",
                QSystemTrayIcon.Information, 4000)

    def reabrir_con_aspecto(self):
        """«Aplicar ahora» en Ajustes › Aspecto: los colores nuevos se ven al momento,
        sin cerrar Caudal y sin cortar la música. Si algo fallara, se reabre como antes."""
        try:
            self._recolorear_en_vivo()
        except Exception:  # noqa: BLE001
            self._reabrir_por_reinicio()

    def _recolorear_en_vivo(self):
        import re
        from PySide6.QtWidgets import QApplication
        from . import iconos
        from .estilos import C, aplicar_aspecto, hoja
        from . import estilos
        viejo = dict(C)
        aplicar_aspecto(self.ajustes["acento"], self.ajustes["fondo"])
        # el fondo con personaje enciende (o apaga) la capa del mosaico y los paneles translúcidos
        estilos.FONDO["activo"] = self._con_capa()
        if hasattr(self, "capa_fondo"):
            self.capa_fondo.setVisible(self._con_capa())
            self.capa_fondo.lower()
            self.capa_fondo.update()
        if getattr(self, "personaje_fondo", None) is not None:
            self.personaje_fondo.colocar()
        # cada color de la paleta vieja pasa a su color nuevo en todas las hojas de estilo
        mapa = {}
        for k, v in viejo.items():
            n = C.get(k)
            if isinstance(v, str) and isinstance(n, str) and v.startswith("#") \
                    and n.lower() != v.lower():
                mapa.setdefault(v.lower(), n)
        iconos._CACHE.clear()
        self.setStyleSheet(hoja(iconos.flechas_qss()))
        if mapa:
            patron = re.compile("(?:" + "|".join(re.escape(k) for k in mapa) + ")(?![0-9a-fA-F])",
                                re.IGNORECASE)
            for w in QApplication.allWidgets():
                ss = w.styleSheet()
                if ss and w is not self:
                    nuevo = patron.sub(lambda m: mapa[m.group(0).lower()], ss)
                    if nuevo != ss:
                        w.setStyleSheet(nuevo)
        # las paginas se rehacen con la paleta nueva (menos el video, que tiene su ventana nativa)
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else None
        en_video = bool(actual) and actual.get("pagina") == "video"
        conservar = self.singletons.get("video")
        for i, (d, w) in enumerate(self.historia):
            if w is not None and w is not conservar:
                self.pila.removeWidget(w)
                w.deleteLater()
                self.historia[i] = (d, None)
        for nombre, w in list(self.singletons.items()):
            if w is not conservar:
                if self.pila.indexOf(w) >= 0:
                    self.pila.removeWidget(w)
                w.deleteLater()
                self.singletons.pop(nombre, None)
        if actual and not en_video:
            w = self._fabricar(actual)
            self.historia[self.indice] = (actual, w)
            self._mostrar(actual, w)
        for w in QApplication.allWidgets():
            w.update()
        try:
            self.aviso.mostrar("Listo: Caudal ya tiene sus colores nuevos")
        except Exception:  # noqa: BLE001
            pass

    def _reabrir_por_reinicio(self):
        """Plan B: Caudal se reabre con los colores nuevos y la música sigue donde iba."""
        import time as _t
        sonando = self.r.estado == "sonando"
        try:
            self.r.guardar_sesion()
            self.ctx.coleccion.guardar_estado("reabrir", {"cuando": _t.time(), "sonando": sonando,
                                                         "pagina": "ajustes"})
        except Exception:  # noqa: BLE001
            pass
        try:
            self._guardar_estado()
        except Exception:  # noqa: BLE001
            pass
        try:
            cuenta = getattr(self.ctx, "cuenta", None)
            if cuenta and cuenta.get("sesion"):
                from ..cuentas import Cuentas
                Cuentas().actualizar_recordada(cuenta)   # el token renovado, para la nueva
        except Exception:  # noqa: BLE001
            pass
        reiniciar = getattr(self.ctx, "reiniciar", None)
        if reiniciar is None:
            return
        self.hide()
        if self.mini:
            self.mini.hide()
        if self.bandeja:
            self.bandeja.hide()
        try:
            self.r.cerrar()
        except Exception:  # noqa: BLE001
            pass
        reiniciar()

    def _seguir_tras_reabrir(self):
        """Tras «Aplicar ahora»: vuelve a Ajustes y retoma la canción."""
        import time as _t
        try:
            datos = self.ctx.coleccion.estado("reabrir")
        except Exception:  # noqa: BLE001
            return
        if not datos:
            return
        try:
            self.ctx.coleccion.guardar_estado("reabrir", None)
        except Exception:  # noqa: BLE001
            pass
        if _t.time() - float(datos.get("cuando") or 0) > 120:
            return
        if datos.get("pagina"):
            QTimer.singleShot(0, lambda: self.navegar({"pagina": datos["pagina"]}))
        QTimer.singleShot(0, lambda: self.aviso.mostrar("Listo: Caudal ya tiene sus colores nuevos"))
        if datos.get("sonando") and self.r.actual is not None:
            QTimer.singleShot(400, self.r.reanudar)

    def salir(self):
        """La unica salida: guarda, para todo y termina el proceso de verdad."""
        if getattr(self, "_saliendo_ya", False):
            return
        if self._estudio_en_curso():
            self._guardia_estudio(self.salir)
            return
        self._saliendo_ya = True
        est = getattr(self.ctx, "estudio", None)
        if est is not None:
            try:
                est.cerrar()        # guarda lo estudiado y devuelve los ajustes del reproductor
            except Exception:
                pass
        self._saliendo = True
        try:
            self._guardar_estado()
        except Exception:
            pass
        try:
            cuenta = getattr(self.ctx, "cuenta", None)
            if cuenta and cuenta.get("sesion"):
                from ..cuentas import Cuentas
                Cuentas().actualizar_recordada(cuenta)   # el token renovado, para la proxima
        except Exception:
            pass
        # primero desaparece todo de la pantalla: el apagado va detras
        for w in (self.mini, self):
            try:
                if w:
                    w.hide()
            except RuntimeError:
                pass
        if self.bandeja:
            self.bandeja.hide()
        QApplication.processEvents()
        try:
            self.teclas_multimedia.soltar()
        except Exception:
            pass
        try:
            self.gamer.cerrar()
        except Exception:
            pass
        try:
            self.ctx.gestor.cancelar_todo()
        except Exception:
            pass
        try:
            self.r.cerrar()
        except Exception:
            pass
        for w in (self.mini, self):
            try:
                if w:
                    w.hide()
            except RuntimeError:
                pass
        if self.bandeja:
            self.bandeja.hide()
        QApplication.quit()

    def _guardar_estado(self):
        try:
            self.ajustes["geometria"] = bytes(self.saveGeometry().toBase64()).decode()
            self.ctx.coleccion.guardar_estado("divisor",
                                              bytes(self.divisor.saveState().toBase64()).decode())
        except Exception:
            pass
        self.ajustes.guardar()


