# -*- coding: utf-8 -*-
"""Ventana principal de Caudal: paneles, navegacion, busqueda y bandeja."""

import os
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QFrame, QHBoxLayout,
                               QLineEdit, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
                               QStackedWidget, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from .. import catalogo, redes, version
from ..config import APP_NOMBRE
from ..hilos import en_segundo_plano
from . import iconos
from .actualizador import Buscador, DialogoActualizacion
from .barra_reproduccion import BarraReproduccion
from .componentes import Aviso, BotonIcono
from .estilos import C, hoja
from .panel_derecho import PanelDerecho
from .panel_lateral import PanelLateral

EXT_AUDIO = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac", ".wma", ".webm"}
EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts"}

SINGLETONS = ("descargas", "video")


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
        self.setMinimumSize(1060, 660)
        self.resize(1440, 900)
        self.setAcceptDrops(True)
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
        self._conectar()
        self._atajos()
        self._bandeja()

        geo = self.ajustes["geometria"]
        if geo:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
            except Exception:
                pass
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
        if not self.r.disponible:
            QTimer.singleShot(800, lambda: QMessageBox.warning(
                self, APP_NOMBRE, "No se encontró el motor de reproducción (libmpv), así que no "
                                  "se puede reproducir. Las descargas sí funcionan.\n\n"
                                  + (self.r.motivo_no_disponible or "")))
        self.buscador_version = None
        QTimer.singleShot(6000, lambda: self.buscar_version(True))
        QApplication.instance().installEventFilter(_Teclas(self))
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
        menu.addSeparator()
        menu.addAction(iconos.icono("engranaje", 16, C["texto2"]), "Ajustes",
                       lambda: self.navegar({"pagina": "ajustes"}))
        menu.addAction(iconos.icono("candado", 16, C["texto2"]), "Cambiar la contraseña",
                       self._cambiar_contrasena)
        menu.addSeparator()
        menu.addAction(iconos.icono("salir", 16, C["texto2"]), "Cerrar sesión", self._cerrar_sesion)
        menu.exec(self.bt_cuenta.mapToGlobal(self.bt_cuenta.rect().bottomRight())
                  - QPoint(menu.sizeHint().width(), -6))

    def _cambiar_contrasena(self):
        from PySide6.QtWidgets import QInputDialog
        from ..cuentas import Cuentas, ErrorCuenta
        usuario = (getattr(self.ctx, "cuenta", None) or {}).get("usuario", "")
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
            Cuentas().cambiar_contrasena(usuario, actual, nueva)
        except ErrorCuenta as e:
            QMessageBox.warning(self, APP_NOMBRE, str(e))
            return
        self.aviso.mostrar("Contraseña cambiada")

    def _cerrar_sesion(self):
        r = QMessageBox.question(self, APP_NOMBRE, "¿Cerrar la sesión? La próxima vez Caudal "
                                                   "te pedirá entrar.")
        if r != QMessageBox.Yes:
            return
        self._saliendo = True
        self._guardar_estado()
        self.teclas_multimedia.soltar()
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
        elif pag == "biblioteca":
            from .paginas.biblioteca import PaginaBiblioteca
            w = PaginaBiblioteca(self.ctx)
        elif pag == "descargas":
            from .paginas.descargas import PaginaDescargas
            w = PaginaDescargas(self.ctx)
        elif pag == "ajustes":
            from .paginas.ajustes import PaginaAjustes
            w = PaginaAjustes(self.ctx)
        elif pag == "video":
            from .video import VistaVideo
            w = VistaVideo(self.ctx)
            w.volver.connect(self.atras_desde_video)
            w.pidio_mini.connect(self.alternar_mini)
            w.pidio_completa.connect(self.alternar_completa)
        if w is None:
            from .paginas.inicio import PaginaInicio
            w = PaginaInicio(self.ctx)
        if pag in SINGLETONS:
            self.singletons[pag] = w
        self.pila.addWidget(w)
        return w

    def navegar(self, destino, reemplazar=False):
        if self.en_completa and destino.get("pagina") != "video":
            self.alternar_completa()
        # ajustes y paginas unicas: si ya estas ahi, no se duplica
        actual = self.historia[self.indice][0] if 0 <= self.indice < len(self.historia) else None
        if actual and actual == destino and not destino.get("editar"):
            w = self.historia[self.indice][1]
            if destino.get("pagina") in ("inicio",) and w is not None:
                # volver a Inicio refresca lo reciente
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
        cambio = self.pila.currentWidget() is not w
        self.pila.setCurrentWidget(w)
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
        self.bt_descargas.set_activo(pag == "descargas", punto=False)
        self.bt_ajustes.set_activo(pag == "ajustes", punto=False)
        titulo = getattr(w, "titulo", "") or ""
        self.setWindowTitle(f"{titulo} · {APP_NOMBRE}" if titulo and pag != "inicio" else APP_NOMBRE)

    def atras(self):
        if self.indice > 0:
            self._ir(self.indice - 1)

    def adelante(self):
        if self.indice < len(self.historia) - 1:
            self._ir(self.indice + 1)

    def _ir(self, i):
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
        self.barra.pidio_video.connect(self._ver_video)
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
        g.tarea_agregada.connect(lambda _i: self._contar_descargas())
        g.cola_cambio.connect(self._contar_descargas)
        g.tarea_cambio.connect(lambda _i: self._contar_descargas())
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
        atajo("Ctrl+Shift+L", lambda: self.alternar_panel("letras"))
        atajo("Ctrl+Shift+Q", lambda: self.alternar_panel("cola"))
        atajo("Ctrl+M", self.alternar_mini)
        atajo("F11", self.alternar_completa)
        atajo("Escape", lambda: self.en_completa and self.alternar_completa())
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

    def _si_no_escribe(self, accion):
        foco = QApplication.focusWidget()
        if isinstance(foco, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox)):
            return
        accion()

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
        if redes.extraer_urls(texto):
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
        dialogo.exec()

    def _lista_traida(self, canciones):
        """Una lista de Spotify / Apple: se guarda como lista de Caudal, lista para sonar."""
        if not canciones:
            return
        caja = QMessageBox(self)
        caja.setWindowTitle("Traer la lista")
        caja.setText(f"{len(canciones)} canciones. ¿Qué hacemos con ellas?")
        guardar = caja.addButton("Guardarla como lista", QMessageBox.AcceptRole)
        bajar = caja.addButton("Descargarlas en MP3", QMessageBox.ActionRole)
        caja.addButton("Cancelar", QMessageBox.RejectRole)
        caja.exec()
        if caja.clickedButton() is bajar:
            for c in canciones:
                enlace = c.get("url") or ("ytsearch1:" + (c.get("busqueda") or c.get("titulo") or ""))
                nombre = c.get("titulo") or ""
                if c.get("artista"):
                    nombre = f"{c['artista']} - {nombre}"
                self.ctx.gestor.agregar(enlace, tipo="audio", titulo=nombre)
            self.aviso.mostrar(f"{len(canciones)} canciones en la cola de descargas")
            return
        if caja.clickedButton() is not guardar:
            return

        def resolver():
            pistas = []
            for c in canciones:
                vid = catalogo.video_id_de(c.get("url") or "")
                if vid:
                    pistas.append(catalogo.nueva_pista(vid, c.get("titulo") or "",
                                                       [{"nombre": c.get("artista") or "", "id": ""}]))
                    continue
                consulta = c.get("busqueda") or f"{c.get('artista', '')} {c.get('titulo', '')}"
                try:
                    hallado = catalogo.buscar(consulta.strip(), "canciones", 1)
                except Exception:
                    hallado = []
                if hallado:
                    pistas.append(hallado[0])
            return pistas

        def listo(pistas):
            if not pistas:
                self.aviso.mostrar("No se encontró ninguna de esas canciones")
                return
            nombre = self.ctx.coleccion.nombre_libre("Lista traída")
            lista_id = self.ctx.coleccion.crear_lista(nombre)
            self.ctx.coleccion.agregar_a_lista(lista_id, pistas)
            self.ctx.listas_cambio.emit()
            self.navegar({"pagina": "mi_lista", "id": lista_id})
            self.aviso.mostrar(f"Lista guardada: {len(pistas)} de {len(canciones)} canciones")

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
        DialogoActualizacion(novedad, self).exec()

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

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.aviso.isVisible():
            self.aviso.move((self.width() - self.aviso.width()) // 2,
                            self.height() - self.aviso.height() - 120)

    def closeEvent(self, e):
        if self.en_completa:
            self.alternar_completa()
            e.ignore()
            return
        if (not self._saliendo and self.ajustes["segundo_plano"] and self.bandeja
                and (self.r.estado in ("sonando", "cargando") or self.ctx.gestor.hay_actividad())):
            e.ignore()
            self.hide()
            if not self._aviso_bandeja:
                self._aviso_bandeja = True
                self.bandeja.showMessage(
                    "Caudal sigue sonando",
                    "Está junto al reloj. Clic para abrirlo; clic derecho → Salir para cerrarlo.",
                    QSystemTrayIcon.Information, 4000)
            return
        activas = [t for t in self.ctx.gestor.lista() if t.activa]
        if activas and not self._saliendo:
            r = QMessageBox.question(self, APP_NOMBRE,
                                     f"Hay {len(activas)} descarga(s) en marcha. Si sales ahora se "
                                     "detendrán (podrás retomarlas). ¿Salir igualmente?")
            if r != QMessageBox.Yes:
                e.ignore()
                return
        self._guardar_estado()
        self.teclas_multimedia.soltar()
        self.ctx.gestor.cancelar_todo()
        self.r.cerrar()
        if self.mini:
            self.mini.hide()
        if self.bandeja:
            self.bandeja.hide()
        e.accept()
        QApplication.quit()

    def _guardar_estado(self):
        try:
            self.ajustes["geometria"] = bytes(self.saveGeometry().toBase64()).decode()
            self.ctx.coleccion.guardar_estado("divisor",
                                              bytes(self.divisor.saveState().toBase64()).decode())
        except Exception:
            pass
        self.ajustes.guardar()

    def salir(self):
        self._saliendo = True
        self.close()
