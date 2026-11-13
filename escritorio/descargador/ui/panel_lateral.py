# -*- coding: utf-8 -*-
"""Panel izquierdo: navegacion y 'Tu biblioteca'."""

import json

from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import iconos, imagenes
from .componentes import MIME_PISTAS, BotonIcono, _borrar_layout, fuente
from .estilos import C


class ItemBiblioteca(QWidget):
    pulsado = Signal(dict)
    menu = Signal(dict, object)

    def __init__(self, ctx, el, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.el = el
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._encima = False
        self._soltando = False
        self.pms = []
        self.activo = False
        tipo = el.get("tipo")
        self.setAcceptDrops(tipo in ("mi_lista", "me_gusta"))
        urls = el.get("mosaico") or ([el.get("miniatura")] if el.get("miniatura") else [])
        forma = "redonda" if tipo == "artista" else "cuadrada"
        if len(urls) >= 4:
            self.pms = [None] * 4
            for i, u in enumerate(urls[:4]):
                self._pedir(u, 24, forma, i)
        elif urls:
            self.pms = [None]
            self._pedir(urls[0], 48, forma, 0)

    def _pedir(self, url, lado, forma, i):
        yo = self

        def listo(pm, i=i):
            try:
                yo.pms[i] = pm
                yo.update()
            except (RuntimeError, IndexError):
                pass
        pm = imagenes.pedir(url, lado, lado, forma, 0 if lado == 24 else 4, listo)
        if pm is not None:
            self.pms[i] = pm

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.pulsado.emit(self.el)
        elif e.button() == Qt.RightButton:
            self.menu.emit(self.el, e.globalPosition().toPoint())

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_PISTAS):
            self._soltando = True
            self.update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._soltando = False
        self.update()

    def dropEvent(self, e):
        self._soltando = False
        self.update()
        try:
            pistas = json.loads(bytes(e.mimeData().data(MIME_PISTAS)).decode("utf-8"))
        except ValueError:
            return
        if self.el.get("tipo") == "mi_lista":
            self.ctx.anadir_a_lista(pistas, self.el["id"])
        elif self.el.get("tipo") == "me_gusta":
            for p in pistas:
                if not self.ctx.coleccion.me_gusta(p.get("clave")):
                    self.ctx.alternar_me_gusta(p)
        e.acceptProposedAction()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        if self._soltando:
            p.setPen(QColor(C["acento"]))
            p.setBrush(QColor(34, 211, 238, 30))
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 6, 6)
        elif self.activo:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 26))
            p.drawRoundedRect(QRectF(0, 0, w, h), 6, 6)
        elif self._encima:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 14))
            p.drawRoundedRect(QRectF(0, 0, w, h), 6, 6)
        r = QRect(8, 8, 48, 48)
        tipo = self.el.get("tipo")
        especial = self.el.get("especial")
        if especial:
            ruta = QPainterPath()
            ruta.addRoundedRect(QRectF(r), 4, 4)
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            colores = {"me_gusta": ("#5B3DF5", "#22D3EE"), "musica": ("#0E7490", "#22D3EE"),
                       "videos": ("#7C2D12", "#F97316")}[especial]
            grad.setColorAt(0, QColor(colores[0]))
            grad.setColorAt(1, QColor(colores[1]))
            p.fillPath(ruta, grad)
            icono = {"me_gusta": "corazon_lleno", "musica": "descargado",
                     "videos": "video"}[especial]
            p.drawPixmap(r.x() + 14, r.y() + 14, iconos.pixmap(icono, 20, "#FFFFFF"))
        elif len(self.pms) == 4:
            ruta = QPainterPath()
            ruta.addRoundedRect(QRectF(r), 4, 4)
            p.setClipPath(ruta)
            for i, pm in enumerate(self.pms):
                x = r.x() + (i % 2) * 24
                y = r.y() + (i // 2) * 24
                if pm is not None:
                    p.drawPixmap(x, y, pm)
                else:
                    p.fillRect(x, y, 24, 24, QColor(C["superficie3"]))
            p.setClipping(False)
        elif self.pms and self.pms[0] is not None:
            p.drawPixmap(r.topLeft(), self.pms[0])
        else:
            ruta = QPainterPath()
            if tipo == "artista":
                ruta.addEllipse(QRectF(r))
            else:
                ruta.addRoundedRect(QRectF(r), 4, 4)
            p.fillPath(ruta, QColor(C["superficie3"]))
            icono = {"artista": "usuario", "album": "album"}.get(tipo, "musica")
            p.drawPixmap(r.x() + 14, r.y() + 14, iconos.pixmap(icono, 20, C["texto3"]))
        # textos
        sonando = self._sonando()
        ancho = w - 76 - (26 if sonando else 0)
        f1 = fuente(14.5, QFont.DemiBold)
        p.setFont(f1)
        p.setPen(QColor(C["acento"] if sonando else C["texto"]))
        p.drawText(QRect(66, 11, ancho, 22), Qt.AlignVCenter,
                   QFontMetrics(f1).elidedText(self.el.get("titulo") or "", Qt.ElideRight, ancho))
        x = 66
        if self.el.get("fijada"):
            p.drawPixmap(x, 37, iconos.pixmap("fijar", 13, C["acento"]))
            x += 18
        f2 = fuente(12.5)
        p.setFont(f2)
        p.setPen(QColor(C["texto2"]))
        p.drawText(QRect(x, 34, ancho - (x - 66), 18), Qt.AlignVCenter,
                   QFontMetrics(f2).elidedText(self.el.get("subtitulo") or "", Qt.ElideRight,
                                               ancho - (x - 66)))
        if sonando:
            p.drawPixmap(w - 30, h // 2 - 8, iconos.pixmap("altavoz_fuerte", 16, C["acento"]))

    def _sonando(self):
        ctx = self.ctx.reproductor.contexto or {}
        if self.ctx.reproductor.estado not in ("sonando", "cargando", "pausa"):
            return False
        tipo = self.el.get("tipo")
        if tipo == "me_gusta":
            return ctx.get("tipo") == "me_gusta"
        if tipo in ("mi_lista", "album", "lista"):
            return ctx.get("tipo") == tipo and str(ctx.get("id")) == str(self.el.get("id"))
        return False


class PanelLateral(QWidget):
    ir = Signal(dict)
    traer_lista = Signal()

    NAV = [("inicio", "Inicio", "casa"), ("explorar", "Explorar", "brujula"),
           ("descargas", "Descargas", "descargar"), ("navegador", "Navegador web", "globo"),
           ("telefono", "Conectar el teléfono", "telefono")]

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.setMinimumWidth(286)
        self.setMaximumWidth(420)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        nav = QFrame()
        nav.setObjectName("panel_nav")
        vn = QVBoxLayout(nav)
        vn.setContentsMargins(10, 12, 10, 12)
        vn.setSpacing(2)
        marca = QHBoxLayout()
        marca.setContentsMargins(10, 0, 0, 8)
        marca.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(iconos.icono_app(28))
        marca.addWidget(logo)
        nombre = QLabel("Caudal")
        nombre.setStyleSheet("font-size:19px;font-weight:900;letter-spacing:-0.4px;")
        marca.addWidget(nombre)
        marca.addStretch(1)
        vn.addLayout(marca)
        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botones = {}
        for clave, texto, icono in self.NAV:
            b = QPushButton(f"   {texto}")
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setIcon(iconos.icono_estados(icono, 20, C["texto2"], C["texto"]))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, c=clave: self.ir.emit({"pagina": c}))
            self.grupo.addButton(b)
            self.botones[clave] = b
            vn.addWidget(b)
        v.addWidget(nav)

        bib = QFrame()
        bib.setObjectName("panel_izq")
        vb = QVBoxLayout(bib)
        vb.setContentsMargins(8, 12, 8, 8)
        vb.setSpacing(8)
        cab = QHBoxLayout()
        cab.setContentsMargins(10, 0, 4, 0)
        t = QPushButton("  Tu biblioteca")
        t.setIcon(iconos.icono("biblioteca", 20, C["texto2"]))
        t.setCursor(Qt.PointingHandCursor)
        t.setStyleSheet(f"QPushButton{{background:transparent;border:none;padding:0;"
                        f"font-size:15px;font-weight:800;color:{C['texto2']};text-align:left;}}"
                        f"QPushButton:hover{{color:{C['texto']};}}")
        t.clicked.connect(lambda: self.ir.emit({"pagina": "biblioteca"}))
        cab.addWidget(t)
        cab.addStretch(1)
        mas = BotonIcono("mas", 18, "Crear una lista o traer una de otra app", 32)
        mas.clicked.connect(lambda: self._menu_crear(mas))
        cab.addWidget(mas)
        vb.addLayout(cab)

        chips = QHBoxLayout()
        chips.setContentsMargins(6, 0, 0, 0)
        chips.setSpacing(6)
        self.filtro_tipo = None
        self.chips = {}
        for clave, texto in (("listas", "Listas"), ("albumes", "Álbumes"),
                             ("artistas", "Artistas"), ("disco", "Disco")):
            c = QPushButton(texto)
            c.setObjectName("chip")
            c.setCheckable(True)
            c.setCursor(Qt.PointingHandCursor)
            c.setFocusPolicy(Qt.NoFocus)
            c.setStyleSheet("QPushButton#chip{padding:4px 9px;font-size:12px;border-radius:12px;}")
            from PySide6.QtWidgets import QSizePolicy
            c.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            c.clicked.connect(lambda _=False, k=clave: self._filtrar(k))
            chips.addWidget(c)
            self.chips[clave] = c
        chips.addStretch(1)
        vb.addLayout(chips)

        fila_buscar = QHBoxLayout()
        fila_buscar.setContentsMargins(4, 0, 4, 0)
        self.buscar = QLineEdit()
        self.buscar.setObjectName("filtro_lista")
        self.buscar.setPlaceholderText("Buscar en tu biblioteca")
        self.buscar.setClearButtonEnabled(True)
        self.buscar.addAction(iconos.icono("lupa", 16, C["texto2"]), QLineEdit.LeadingPosition)
        self.buscar.textChanged.connect(lambda _t: self._programar())
        fila_buscar.addWidget(self.buscar)
        vb.addLayout(fila_buscar)

        self.area = QScrollArea()
        self.area.setObjectName("lienzo")
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interior = QWidget()
        self.lista = QVBoxLayout(interior)
        self.lista.setContentsMargins(0, 0, 0, 0)
        self.lista.setSpacing(0)
        self.area.setWidget(interior)
        vb.addWidget(self.area, 1)
        v.addWidget(bib, 1)

        self.items = []
        self._pendiente = False
        self.destino_actual = None
        for senal in (ctx.listas_cambio, ctx.guardados_cambio, ctx.descargas_cambio,
                      ctx.me_gusta_cambio):
            senal.connect(self._programar)
        ctx.reproductor.estado_cambio.connect(lambda *_: [i.update() for i in self.items])
        ctx.reproductor.pista_cambio.connect(lambda *_: [i.update() for i in self.items])
        self.refrescar()

    def _programar(self, *_):
        if not self._pendiente:
            self._pendiente = True
            QTimer.singleShot(80, self.refrescar)

    def _filtrar(self, clave):
        self.filtro_tipo = None if self.filtro_tipo == clave else clave
        for k, c in self.chips.items():
            c.setChecked(k == self.filtro_tipo)
        self.refrescar()

    def _menu_crear(self, boton):
        menu = QMenu(self)
        menu.addAction(iconos.icono("anadir_lista", 16, C["texto2"]), "Crear una lista",
                       self.ctx.crear_lista)
        menu.addAction(iconos.icono("descargar", 16, C["texto2"]),
                       "Traer una lista de Spotify, Apple Music o YouTube…", self.traer_lista.emit)
        menu.exec(boton.mapToGlobal(boton.rect().bottomLeft()))

    def marcar(self, destino):
        self.destino_actual = destino
        pagina = (destino or {}).get("pagina")
        boton = self.botones.get(pagina)
        if boton:
            boton.setChecked(True)
        else:
            self.grupo.setExclusive(False)
            for b in self.botones.values():
                b.setChecked(False)
            self.grupo.setExclusive(True)
        for it in self.items:
            it.activo = self._coincide(it.el, destino)
            it.update()

    def _coincide(self, el, destino):
        if not destino:
            return False
        pag = destino.get("pagina")
        if el.get("tipo") == "me_gusta":
            return pag == "me_gusta"
        if el.get("tipo") == "disco":
            return pag == "disco" and destino.get("solo") == el.get("solo")
        if el.get("tipo") == "mi_lista":
            return pag == "mi_lista" and str(destino.get("id")) == str(el.get("id"))
        if el.get("tipo") in ("album", "lista", "artista"):
            return pag == el["tipo"] and destino.get("id") == el.get("id")
        return False

    def elementos(self):
        col = self.ctx.coleccion
        filtro = self.buscar.text().strip().lower()
        f = self.filtro_tipo
        salida = []
        if f in (None, "listas"):
            n = col.total_me_gusta()
            salida.append({"tipo": "me_gusta", "especial": "me_gusta", "titulo": "Tus me gusta",
                           "subtitulo": f"Lista • {n} {'canción' if n == 1 else 'canciones'}",
                           "fijada": True})
        if f in (None, "disco"):
            musica = len(col.descargadas(True))
            videos = len(col.descargadas(False))
            salida.append({"tipo": "disco", "solo": True, "especial": "musica",
                           "titulo": "Música descargada",
                           "subtitulo": f"En tu disco • {musica} canciones"})
            salida.append({"tipo": "disco", "solo": False, "especial": "videos",
                           "titulo": "Videos descargados",
                           "subtitulo": f"En tu disco • {videos} videos"})
        if f in (None, "listas"):
            for l in col.listas():
                salida.append({"tipo": "mi_lista", "id": l["id"], "titulo": l["nombre"],
                               "subtitulo": f"Lista • {l['n']} {'canción' if l['n'] == 1 else 'canciones'}",
                               "mosaico": col.portadas_de_lista(l["id"]),
                               "fijada": bool(l.get("fijada"))})
            for g in col.guardados("lista"):
                salida.append({**g, "subtitulo": g.get("subtitulo") or "Lista"})
        if f in (None, "albumes"):
            for g in col.guardados("album"):
                salida.append({**g, "subtitulo": g.get("subtitulo") or "Álbum"})
        if f in (None, "artistas"):
            for g in col.guardados("artista"):
                salida.append({**g, "subtitulo": "Artista"})
        if filtro:
            salida = [e for e in salida if filtro in (e.get("titulo") or "").lower()
                      or filtro in (e.get("subtitulo") or "").lower()]
        return salida

    def refrescar(self):
        self._pendiente = False
        _borrar_layout(self.lista)
        self.items = []
        for el in self.elementos():
            it = ItemBiblioteca(self.ctx, el)
            it.pulsado.connect(self._abrir)
            it.menu.connect(self._menu)
            it.activo = self._coincide(el, self.destino_actual)
            self.lista.addWidget(it)
            self.items.append(it)
        if not self.items:
            vacio = QLabel("Nada por aquí con ese filtro.")
            vacio.setObjectName("secundario")
            vacio.setContentsMargins(12, 12, 12, 12)
            self.lista.addWidget(vacio)
        self.lista.addStretch(1)

    def _abrir(self, el):
        tipo = el.get("tipo")
        if tipo == "me_gusta":
            self.ir.emit({"pagina": "me_gusta"})
        elif tipo == "disco":
            self.ir.emit({"pagina": "disco", "solo": el["solo"]})
        elif tipo == "mi_lista":
            self.ir.emit({"pagina": "mi_lista", "id": el["id"]})
        else:
            self.ctx.abrir_elemento(el)

    def _menu(self, el, pos):
        tipo = el.get("tipo")
        if tipo == "mi_lista":
            menu = QMenu(self)
            menu.addAction(iconos.icono("reproducir", 16, C["texto2"]), "Reproducir",
                           lambda: self.ctx.reproducir_elemento(el))
            menu.addAction(iconos.icono("aleatorio", 16, C["texto2"]), "Reproducir en aleatorio",
                           lambda: self.ctx.reproducir_elemento(el, aleatorio=True))
            menu.addSeparator()
            fijada = bool(el.get("fijada"))
            menu.addAction(iconos.icono("fijar", 16, C["texto2"]),
                           "Desfijar" if fijada else "Fijar arriba",
                           lambda: (self.ctx.coleccion.editar_lista(el["id"], fijada=not fijada),
                                    self.ctx.listas_cambio.emit()))
            menu.addAction(iconos.icono("editar", 16, C["texto2"]), "Cambiar nombre y descripción",
                           lambda: self.ir.emit({"pagina": "mi_lista", "id": el["id"],
                                                 "editar": True}))
            self.ctx.menu_descargar(menu, lambda cb: self.ctx.pistas_de(el, cb))
            menu.addSeparator()
            menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Borrar la lista",
                           lambda: self._borrar_lista(el))
            menu.exec(pos)
        elif tipo == "me_gusta":
            menu = QMenu(self)
            menu.addAction("Reproducir", lambda: self.ctx.reproducir_elemento(el))
            menu.addAction("Reproducir en aleatorio",
                           lambda: self.ctx.reproducir_elemento(el, aleatorio=True))
            self.ctx.menu_descargar(menu, lambda cb: self.ctx.pistas_de(el, cb))
            menu.exec(pos)
        elif tipo in ("album", "lista", "artista"):
            self.ctx.menu_elemento(el, pos)

    def _borrar_lista(self, el):
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(self, "Borrar la lista",
                                 f"¿Borrar «{el['titulo']}»? Las canciones no se borran "
                                 "del disco ni de Tus me gusta.")
        if r == QMessageBox.Yes:
            self.ctx.coleccion.borrar_lista(el["id"])
            self.ctx.listas_cambio.emit()
            if (self.destino_actual or {}).get("pagina") == "mi_lista" and \
                    str(self.destino_actual.get("id")) == str(el["id"]):
                self.ir.emit({"pagina": "inicio"})
