# -*- coding: utf-8 -*-
"""Buscador de la escena: píldora de vidrio con el campo, el selector de fuente y, encima
de ella, los resultados (canciones y artistas) o el estado de carga.

Todo se pinta con QPainter y se ancla al borde inferior: el alto lo pide `altura_deseada()`
y cada cambio se avisa con `cambio_tamano`.
"""

import time

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPalette, QPen)
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from .. import iconos, imagenes
from ..componentes import a_la_vista
from .estilo import (BRILLO, DOMINANTE, RADIO, SEGUNDO, TEXTO, TEXTO_2, TEXTO_3, acento_legible,
                     con_alfa, fuente, pintar_sombra, pintar_vidrio, preparar_transparente)

FUENTES = [("auto", "Automático"), ("ytmusic", "YouTube Music"), ("youtube", "Videos de YouTube"),
           ("megusta", "Mis me gusta"), ("descargas", "Mis descargas")]
_NOMBRES = dict(FUENTES)
_ICONOS_FUENTE = {"auto": "disco", "ytmusic": "musica", "youtube": "video",
                  "megusta": "corazon", "descargas": "descargado"}

# geometría (píxeles)
W = 640
MARGEN_X = 24            # hueco a izquierda y derecha (deja respirar la sombra)
BORDE_INF = 24           # hueco bajo la píldora
PILL_H = 44
RADIO_PILL = 22.0
GAP = 10                 # separación entre la píldora y lo que tiene encima
MARGEN_SUP = 16          # hueco sobre el panel para que su sombra no se corte
PAD_H = 18               # relleno horizontal interior de los paneles
PAD_V = 16               # relleno vertical interior de los paneles
ANCHO_PANEL = W - 2 * MARGEN_X
ANCHO_INTERIOR = ANCHO_PANEL - 2 * PAD_H
X_INTERIOR = MARGEN_X + PAD_H
ALTO_TITULO = 20
N_CARTAS = 4
CARTA_W = 130
CARTA_GAP = 12
CARATULA = 104
CARTA_H = 164            # carátula + título + subtítulo con su aire
N_AVATARES = 5
AVATAR = 68
AVATAR_H = 90            # avatar + nombre debajo
ALTO_ERROR = 76
MENU_W = 230
FILA_H = 36
MENU_PAD = 8
MENU_H = 2 * MENU_PAD + len(FUENTES) * FILA_H
PERIODO = 1.6            # segundos que tarda el brillo en cruzar el widget
TIC_MS = 33


def _icono(p, nombre, tam, color_hex, x, y, alfa=1.0):
    """Dibuja un icono de `iconos` (color en hex) con la opacidad indicada."""
    pm = iconos.pixmap(nombre, tam, color_hex)
    p.save()
    p.setOpacity(alfa)
    p.drawPixmap(int(x), int(y), pm)
    p.restore()


def _camino(rect, radio):
    """Ruta redondeada de un rectángulo."""
    camino = QPainterPath()
    camino.addRoundedRect(QRectF(rect), radio, radio)
    return camino


class _CampoBusqueda(QLineEdit):
    """Campo sin marco que avisa de Enter y de Esc para que el buscador decida qué hacer."""

    enviado = Signal()
    escape = Signal()

    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.enviado.emit()
            ev.accept()
            return
        if ev.key() == Qt.Key_Escape:
            self.escape.emit()
            ev.accept()
            return
        super().keyPressEvent(ev)


class PanelBusqueda(QWidget):
    """Buscador translúcido de la escena: campo, selector de fuente y resultados."""

    buscar = Signal(str, str)          # (texto, clave de fuente)
    elegida = Signal(dict)             # canción pulsada
    artista = Signal(dict)             # artista pulsado
    fuente_cambiada = Signal(str)      # clave de la nueva fuente
    cambio_tamano = Signal()           # cambió altura_deseada()

    def __init__(self, padre=None):
        super().__init__(padre)
        preparar_transparente(self)
        self.setFixedWidth(W)
        self.setMouseTracking(True)

        self._dominante = QColor(DOMINANTE)
        self._segundo = QColor(SEGUNDO)
        self._brillo = QColor(BRILLO)
        self._acento = acento_legible(self._dominante)
        self._fuente_clave = "auto"
        self._modo = "reposo"              # reposo | cargando | resultados | error
        self._canciones = []
        self._artistas = []
        self._error = ""
        self._menu_abierto = False
        self._hover = None                 # ("boton",None) | ("opcion",i) | ("cancion",i) | ("artista",i)
        self._ultima_consulta = ""         # último texto enviado con Enter
        self._imgs = {}                    # url -> QImage (None mientras llega o si falla)
        self._escalas = {}                 # (url, w, h) -> recorte ya escalado
        self._cargador = imagenes.imagen
        self._t0 = time.monotonic()

        self._f_campo = fuente(14)
        self._f_titulo = fuente(13, QFont.DemiBold)
        self._f_normal = fuente(13)
        self._f_carta = fuente(12, QFont.DemiBold)
        self._f_pequena = fuente(11)
        self._f_boton = fuente(12, QFont.DemiBold)

        self._campo = _CampoBusqueda(self)
        self._campo.setFrame(False)
        self._campo.setFont(self._f_campo)
        self._campo.setPlaceholderText("Busca una canción, artista o video…")
        self._campo.setStyleSheet("background:transparent;border:none;")
        pal = self._campo.palette()
        pal.setColor(QPalette.Base, QColor(0, 0, 0, 0))
        pal.setColor(QPalette.Text, QColor(255, 255, 255))
        pal.setColor(QPalette.PlaceholderText, TEXTO_3)
        self._campo.setPalette(pal)
        self._campo.enviado.connect(self._enviar)
        self._campo.escape.connect(self._escape)

        self._timer = QTimer(self)
        self._timer.setInterval(TIC_MS)
        self._timer.timeout.connect(self._tic)

        self._recolocar()
        self.setFixedHeight(self.altura_deseada())

    # ------------------------------------------------------------------ API pública

    def mostrar_resultados(self, canciones, artistas):
        """Muestra hasta 4 canciones y 5 artistas. Sin ninguno, muestra el aviso de sin resultados."""
        self._canciones = list(canciones or [])[:N_CARTAS]
        self._artistas = list(artistas or [])[:N_AVATARES]
        self._parar()
        self._error = ""
        if self._canciones or self._artistas:
            self._modo = "resultados"
        else:
            consulta = self._ultima_consulta or self._campo.text().strip()
            self._modo = "error"
            self._error = f"Sin resultados para «{consulta}»"
        for c in self._canciones:
            self._pedir(c.get("miniatura"))
        for a in self._artistas:
            self._pedir(a.get("miniatura"))
        self._actualizar_altura()

    def mostrar_cargando(self):
        """Huecos con el brillo que pasa mientras llega la respuesta."""
        self._modo = "cargando"
        self._canciones = []
        self._artistas = []
        self._error = ""
        self._t0 = time.monotonic()
        self._actualizar_altura()
        self._arrancar()

    def mostrar_error(self, texto):
        """Muestra el texto de error dentro del panel."""
        self._modo = "error"
        self._error = str(texto)
        self._canciones = []
        self._artistas = []
        self._parar()
        self._actualizar_altura()

    def limpiar(self):
        """Vacía el texto y oculta los resultados."""
        self._campo.clear()
        self._cerrar_menu()
        self._modo = "reposo"
        self._canciones = []
        self._artistas = []
        self._error = ""
        self._parar()
        self._actualizar_altura()

    def fijar_fuente(self, clave):
        """Cambia la fuente sin emitir `fuente_cambiada` (es un cambio de programa)."""
        if clave not in _NOMBRES:
            return
        self._fuente_clave = clave
        self._recolocar()
        self.update()

    def fuente_actual(self):
        return self._fuente_clave

    def fijar_cargador(self, funcion):
        """Función `funcion(url, callback(QImage))` que trae las carátulas."""
        self._cargador = funcion

    def poner_colores(self, dominante, segundo, brillo):
        self._dominante = QColor(dominante)
        self._segundo = QColor(segundo)
        self._brillo = QColor(brillo)
        self._acento = acento_legible(self._dominante)
        self.update()

    def enfocar(self):
        self._campo.setFocus()

    def altura_deseada(self):
        """Alto que necesita el widget: la píldora más lo que hay encima (panel o menú)."""
        alto_panel, _ = self._maquetar()
        arriba = max(alto_panel, MENU_H if self._menu_abierto else 0)
        total = BORDE_INF + PILL_H
        if arriba:
            total += GAP + arriba + MARGEN_SUP
        return int(total)

    def rect_cancion(self, i):
        d = self._disposicion()
        return QRectF(d["cartas"][i]) if 0 <= i < len(d["cartas"]) else QRectF()

    def rect_artista(self, i):
        d = self._disposicion()
        return QRectF(d["avatares"][i]) if 0 <= i < len(d["avatares"]) else QRectF()

    def rect_boton_fuente(self):
        return QRectF(self._rect_boton())

    def rect_opcion_fuente(self, i):
        """Rectángulo de la opción i del menú (solo tiene sentido con el menú abierto)."""
        filas = self._disposicion()["filas"]
        return QRectF(filas[i]) if 0 <= i < len(filas) else QRectF()

    # ------------------------------------------------------------------ geometría

    def _pill(self):
        return QRectF(MARGEN_X, self.height() - BORDE_INF - PILL_H, W - 2 * MARGEN_X, PILL_H)

    def _rect_boton(self):
        """Botón de la fuente: píldora pequeña a la derecha de la píldora principal."""
        pill = self._pill()
        tw = QFontMetrics(self._f_boton).horizontalAdvance(_NOMBRES[self._fuente_clave])
        bw = 12 + tw + 8 + 14 + 12
        return QRectF(pill.right() - 8 - bw, pill.top() + 6, bw, 32)

    def _maquetar(self):
        """Alto del panel de resultados y sus rectángulos relativos a su borde superior.
        Devuelve (0, None) sin panel, (ALTO_ERROR, {}) en error."""
        if self._modo == "reposo":
            return 0, None
        if self._modo == "error":
            return ALTO_ERROR, {}
        cargando = self._modo == "cargando"
        n_c = N_CARTAS if cargando else len(self._canciones)
        n_a = N_AVATARES if cargando else len(self._artistas)
        rel = {"titulo": QRectF(X_INTERIOR, PAD_V, ANCHO_INTERIOR, ALTO_TITULO),
               "cartas": [], "etiqueta": None, "avatares": []}
        y = PAD_V + ALTO_TITULO
        if n_c:
            y += 12
            rel["cartas"] = [QRectF(X_INTERIOR + i * (CARTA_W + CARTA_GAP), y, CARTA_W, CARTA_H)
                             for i in range(n_c)]
            y += CARTA_H
        if n_a:
            y += 16 if n_c else 12
            rel["etiqueta"] = QRectF(X_INTERIOR, y, ANCHO_INTERIOR, 18)
            y += 18 + 10
            celda = ANCHO_INTERIOR / N_AVATARES
            rel["avatares"] = [QRectF(X_INTERIOR + i * celda, y, celda, AVATAR_H) for i in range(n_a)]
            y += AVATAR_H
        return y + PAD_V, rel

    def _disposicion(self):
        """Todos los rectángulos en coordenadas del widget."""
        pill = self._pill()
        menu = QRectF(pill.right() - MENU_W, pill.top() - GAP - MENU_H, MENU_W, MENU_H)
        filas = [QRectF(menu.x() + MENU_PAD, menu.y() + MENU_PAD + i * FILA_H,
                        menu.width() - 2 * MENU_PAD, FILA_H) for i in range(len(FUENTES))]
        d = {"pill": pill, "boton": self._rect_boton(), "menu": menu, "filas": filas,
             "panel": None, "titulo": None, "cartas": [], "etiqueta": None, "avatares": []}
        alto, rel = self._maquetar()
        if rel is None:
            return d
        top = pill.top() - GAP - alto
        d["panel"] = QRectF(MARGEN_X, top, ANCHO_PANEL, alto)
        if rel:
            d["titulo"] = rel["titulo"].translated(0, top)
            d["cartas"] = [r.translated(0, top) for r in rel["cartas"]]
            d["avatares"] = [r.translated(0, top) for r in rel["avatares"]]
            if rel["etiqueta"] is not None:
                d["etiqueta"] = rel["etiqueta"].translated(0, top)
        return d

    def _recolocar(self):
        """Pone el campo en la píldora, entre la lupa y el botón de fuente."""
        pill = self._pill()
        x = pill.x() + 46
        fin = self._rect_boton().x() - 8
        self._campo.setGeometry(QRect(int(x), int(pill.y() + 7), max(40, int(fin - x)), 30))

    def _actualizar_altura(self):
        nueva = self.altura_deseada()
        if nueva != self.height():
            self.setFixedHeight(nueva)
            self.cambio_tamano.emit()
        self._recolocar()
        self.update()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._recolocar()

    # ------------------------------------------------------------------ carátulas

    def _pedir(self, url):
        if not url or url in self._imgs:
            return
        self._imgs[url] = None
        self._cargador(url, lambda img, u=url: self._llego(u, img))

    def _llego(self, url, img):
        try:
            self._imgs[url] = img if (img is not None and not img.isNull()) else None
            self._escalas = {k: v for k, v in self._escalas.items() if k[0] != url}
            self.update()
        except RuntimeError:          # el widget ya no existe
            pass

    def _recorte(self, url, img, w, h):
        """Carátula escalada para cubrir w x h y recortada al centro (se guarda en caché)."""
        clave = (url, w, h)
        if clave not in self._escalas:
            esc = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x0 = (esc.width() - w) // 2
            y0 = (esc.height() - h) // 2
            self._escalas[clave] = esc.copy(x0, y0, w, h)
        return self._escalas[clave]

    # ------------------------------------------------------------------ animación

    def _xc_brillo(self):
        """Posición horizontal del brillo que pasa, según el tiempo real transcurrido."""
        fase = ((time.monotonic() - self._t0) / PERIODO) % 1.0
        return -90 + fase * (W + 180)

    def _arrancar(self):
        if self._modo == "cargando" and a_la_vista(self) and not self._timer.isActive():
            self._timer.start()

    def _parar(self):
        self._timer.stop()

    def _tic(self):
        if self._modo != "cargando" or not a_la_vista(self):
            self._timer.stop()
            return
        self.update()

    # ------------------------------------------------------------------ menú y acciones

    def _abrir_menu(self):
        if self._menu_abierto:
            return
        self._menu_abierto = True
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)     # para cerrar con un clic fuera
        self._actualizar_altura()

    def _cerrar_menu(self):
        if not self._menu_abierto:
            return
        self._menu_abierto = False
        self._hover = None
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._actualizar_altura()

    def _elegir_fuente(self, clave):
        self._fuente_clave = clave
        self._cerrar_menu()
        self._recolocar()
        self.update()
        self.fuente_cambiada.emit(clave)

    def _enviar(self):
        texto = self._campo.text().strip()
        if not texto:
            return
        self._cerrar_menu()
        self._ultima_consulta = texto
        self.mostrar_cargando()            # antes de emitir: si la respuesta llega ya, manda ella
        self.buscar.emit(texto, self._fuente_clave)

    def _escape(self):
        if self._menu_abierto:
            self._cerrar_menu()
        else:
            self.limpiar()

    def eventFilter(self, obj, ev):
        """Con el menú abierto, un clic fuera del menu y del botón lo cierra."""
        if self._menu_abierto and ev.type() == QEvent.MouseButtonPress:
            try:
                local = QPointF(self.mapFromGlobal(ev.globalPosition().toPoint()))
                d = self._disposicion()
                if not d["menu"].contains(local) and not d["boton"].contains(local):
                    self._cerrar_menu()
            except RuntimeError:
                pass
        return False

    def _objetivo(self, pos):
        """Qué hay bajo el puntero: ("boton",None), ("opcion",i), ("cancion",i), ("artista",i) o None."""
        d = self._disposicion()
        if self._menu_abierto:
            for i, fila in enumerate(d["filas"]):
                if fila.contains(pos):
                    return ("opcion", i)
            if d["menu"].contains(pos):
                return None
        if d["boton"].contains(pos):
            return ("boton", None)
        if self._modo == "resultados":
            for i, r in enumerate(d["cartas"]):
                if r.contains(pos):
                    return ("cancion", i)
            for i, r in enumerate(d["avatares"]):
                if r.contains(pos):
                    return ("artista", i)
        return None

    # ------------------------------------------------------------------ eventos

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            super().mousePressEvent(ev)
            return
        obj = self._objetivo(ev.position())
        if obj is None:
            self._cerrar_menu()
            return
        tipo, i = obj
        if tipo == "boton":
            if self._menu_abierto:
                self._cerrar_menu()
            else:
                self._abrir_menu()
        elif tipo == "opcion":
            self._elegir_fuente(FUENTES[i][0])
        elif tipo == "cancion":
            self.elegida.emit(self._canciones[i])
        elif tipo == "artista":
            self.artista.emit(self._artistas[i])

    def mouseMoveEvent(self, ev):
        obj = self._objetivo(ev.position())
        if obj != self._hover:
            self._hover = obj
            self.setCursor(Qt.PointingHandCursor if obj is not None else Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(ev)

    def leaveEvent(self, ev):
        self._hover = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(ev)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self._escape()
            ev.accept()
            return
        super().keyPressEvent(ev)

    def showEvent(self, ev):
        super().showEvent(ev)
        self._arrancar()

    def hideEvent(self, ev):
        self._cerrar_menu()
        self._parar()
        super().hideEvent(ev)

    # ------------------------------------------------------------------ pintura

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        d = self._disposicion()
        if d["panel"] is not None:
            self._pintar_panel(p, d)
        pill = d["pill"]
        pintar_vidrio(p, pill, radio=RADIO_PILL, acento=self._dominante, fuerza=1.0)
        p.setPen(Qt.NoPen)
        _icono(p, "lupa", 18, "#FFFFFF", pill.x() + 18, pill.center().y() - 9, 0.65)
        self._pintar_boton(p, d["boton"], self._hover == ("boton", None))
        if self._menu_abierto:
            self._pintar_menu(p, d)
        p.end()

    def _pintar_boton(self, p, boton, hover):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 42 if hover else 24))
        p.drawRoundedRect(boton, 16, 16)
        p.setFont(self._f_boton)
        p.setPen(TEXTO)
        p.drawText(QRectF(boton.x() + 12, boton.y(), boton.width() - 40, boton.height()),
                   Qt.AlignLeft | Qt.AlignVCenter, _NOMBRES[self._fuente_clave])
        _icono(p, "chevron_abajo", 14, "#FFFFFF", boton.right() - 12 - 14, boton.center().y() - 7, 0.65)

    def _pintar_menu(self, p, d):
        # base casi opaca: el menú se tapa a lo que hay detrás para que se lea
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 14, 26, 215))
        p.drawRoundedRect(d["menu"], 16, 16)
        pintar_vidrio(p, d["menu"], radio=16, acento=self._dominante, fuerza=1.0)
        for i, (clave, nombre) in enumerate(FUENTES):
            fila = d["filas"][i]
            p.setPen(Qt.NoPen)
            if self._hover == ("opcion", i):
                p.setBrush(QColor(255, 255, 255, 26))
                p.drawRoundedRect(fila, 10, 10)
            circ = QRectF(fila.x() + 10, fila.center().y() - 11, 22, 22)
            p.setBrush(self._acento)
            p.drawEllipse(circ)
            _icono(p, _ICONOS_FUENTE[clave], 14, "#12091C", circ.center().x() - 7, circ.center().y() - 7)
            p.setFont(self._f_normal)
            p.setPen(TEXTO)
            p.drawText(QRectF(fila.x() + 42, fila.y(), fila.width() - 76, fila.height()),
                       Qt.AlignLeft | Qt.AlignVCenter, nombre)
            if clave == self._fuente_clave:
                _icono(p, "listo", 16, self._acento.name(), fila.right() - 26, fila.center().y() - 8)

    def _pintar_panel(self, p, d):
        panel = d["panel"]
        # base casi opaca, como el menú: lo de detrás (tarjeta, letra) no debe leerse a través
        pintar_sombra(p, panel, RADIO, 1.0)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 14, 26, 225))
        p.drawRoundedRect(panel, RADIO, RADIO)
        pintar_vidrio(p, panel, radio=RADIO, acento=self._segundo, fuerza=1.0, sombra=False)
        if self._modo == "error":
            p.setFont(self._f_normal)
            p.setPen(TEXTO_2)
            p.drawText(panel.adjusted(PAD_H, 10, -PAD_H, -10),
                       Qt.AlignCenter | Qt.TextWordWrap, self._error)
            return
        cargando = self._modo == "cargando"
        xc = self._xc_brillo()
        p.setFont(self._f_titulo)
        p.setPen(TEXTO)
        p.drawText(d["titulo"], Qt.AlignLeft | Qt.AlignVCenter, "Mejores resultados")
        for i, r in enumerate(d["cartas"]):
            if cargando:
                self._pintar_hueco_carta(p, r, xc)
            else:
                self._pintar_carta(p, r, self._canciones[i], self._hover == ("cancion", i))
        if d["etiqueta"] is not None:
            p.setFont(self._f_titulo)
            p.setPen(TEXTO)
            p.drawText(d["etiqueta"], Qt.AlignLeft | Qt.AlignVCenter, "Artistas")
        for i, r in enumerate(d["avatares"]):
            if cargando:
                self._pintar_hueco_avatar(p, r, xc)
            else:
                self._pintar_avatar(p, r, self._artistas[i], self._hover == ("artista", i))

    def _pintar_imagen(self, p, rect, url, radio):
        img = self._imgs.get(url) if url else None
        camino = _camino(rect, radio)
        if img is None or img.isNull():
            p.setPen(Qt.NoPen)
            p.fillPath(camino, QColor(255, 255, 255, 22))
            _icono(p, "musica", 24, "#FFFFFF", rect.center().x() - 12, rect.center().y() - 12, 0.41)
            return
        recorte = self._recorte(url, img, int(round(rect.width())), int(round(rect.height())))
        p.save()
        p.setClipPath(camino)
        p.drawImage(rect, recorte)
        p.restore()

    def _pintar_carta(self, p, base, cancion, hover):
        r = base.translated(0, -3 if hover else 0)
        camino = _camino(r, 14)
        p.setPen(Qt.NoPen)
        p.fillPath(camino, QColor(255, 255, 255, 34 if hover else 16))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self._acento if hover else QColor(255, 255, 255, 40), 1.6 if hover else 1.0))
        p.drawPath(camino)
        caratula = QRectF(r.x() + (r.width() - CARATULA) / 2, r.y() + 10, CARATULA, CARATULA)
        self._pintar_imagen(p, caratula, cancion.get("miniatura"), 12)
        titulo = QFontMetrics(self._f_carta).elidedText(str(cancion.get("titulo", "")),
                                                        Qt.ElideRight, CARATULA)
        p.setFont(self._f_carta)
        p.setPen(TEXTO)
        p.drawText(QRectF(caratula.x(), r.y() + 120, CARATULA, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   titulo)
        sub = "Canción · " + str(cancion.get("artista", ""))
        sub = QFontMetrics(self._f_pequena).elidedText(sub, Qt.ElideRight, CARATULA)
        p.setFont(self._f_pequena)
        p.setPen(TEXTO_2)
        p.drawText(QRectF(caratula.x(), r.y() + 138, CARATULA, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   sub)

    def _pintar_avatar(self, p, cell, artista, hover):
        circ = QRectF(cell.x() + (cell.width() - AVATAR) / 2, cell.y(), AVATAR, AVATAR)
        self._pintar_imagen(p, circ, artista.get("miniatura"), AVATAR / 2)
        if hover:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(self._acento, 2.0))
            p.drawEllipse(circ.adjusted(1, 1, -1, -1))
        nombre = QFontMetrics(self._f_pequena).elidedText(str(artista.get("titulo", "")),
                                                          Qt.ElideRight, int(cell.width()))
        p.setFont(self._f_pequena)
        p.setPen(TEXTO)
        p.drawText(QRectF(cell.x(), cell.y() + 74, cell.width(), 16),
                   Qt.AlignHCenter | Qt.AlignVCenter, nombre)

    def _pintar_hueco(self, p, rect, radio, xc):
        """Hueco de carga: relleno tenue con el brillo que pasa por encima."""
        camino = _camino(rect, radio)
        p.setPen(Qt.NoPen)
        p.fillPath(camino, QColor(255, 255, 255, 22))
        g = QLinearGradient(QPointF(xc - 70, 0), QPointF(xc + 70, 0))
        banda = con_alfa(self._brillo, 80)
        g.setColorAt(0.0, con_alfa(banda, 0))
        g.setColorAt(0.5, banda)
        g.setColorAt(1.0, con_alfa(banda, 0))
        p.fillPath(camino, g)

    def _pintar_hueco_carta(self, p, base, xc):
        x = base.x() + (base.width() - CARATULA) / 2
        y = base.y()
        self._pintar_hueco(p, QRectF(x, y + 10, CARATULA, CARATULA), 12, xc)
        self._pintar_hueco(p, QRectF(x, y + 123, 84, 12), 6, xc)
        self._pintar_hueco(p, QRectF(x, y + 141, 60, 10), 5, xc)

    def _pintar_hueco_avatar(self, p, cell, xc):
        circ = QRectF(cell.x() + (cell.width() - AVATAR) / 2, cell.y(), AVATAR, AVATAR)
        self._pintar_hueco(p, circ, AVATAR / 2, xc)
        self._pintar_hueco(p, QRectF(cell.center().x() - 28, cell.y() + 76, 56, 10), 5, xc)
