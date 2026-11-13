# -*- coding: utf-8 -*-
"""Buscar: todo YouTube Music, y cualquier enlace de ~1800 sitios."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget)

from ... import catalogo, redes
from ...hilos import en_segundo_plano
from .. import iconos, imagenes
from ..componentes import (Carrusel, Chip, ListaPistas, Pagina, Portada, SinResultados,
                           _borrar_layout, fuente)
from ..estilos import C
from .comun import Rejilla, cache, guardar_cache

FILTROS = [("todo", "Todo"), ("canciones", "Canciones"), ("videos", "Videos"),
           ("albumes", "Álbumes"), ("artistas", "Artistas"), ("listas", "Listas")]


class ResultadoPrincipal(QWidget):
    abrir = Signal(dict)
    reproducir = Signal(dict)

    def __init__(self, ctx, el, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.el = el
        self.setFixedHeight(250)
        self.setMinimumWidth(320)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._encima = False
        self.pm = None
        forma = "redonda" if el.get("tipo") == "artista" else "cuadrada"
        url = el.get("miniatura") or ""
        yo = self

        def listo(pm):
            try:
                yo.pm = pm
                yo.update()
            except RuntimeError:
                pass
        if url:
            self.pm = imagenes.pedir(url, 96, 96, forma, 6, listo)

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def _r_play(self):
        return QRectF(self.width() - 76, self.height() - 76, 52, 52)

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.ctx.menu_elemento(self.el, e.globalPosition().toPoint())
        elif e.button() == Qt.LeftButton:
            if self._r_play().contains(e.position()):
                self.reproducir.emit(self.el)
            else:
                self.abrir.emit(self.el)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        ruta = QPainterPath()
        ruta.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 10, 10)
        p.fillPath(ruta, QColor(C["superficie3"] if self._encima else C["superficie2"]))
        if self.pm is not None:
            p.drawPixmap(22, 22, self.pm)
        else:
            r = QRectF(22, 22, 96, 96)
            rr = QPainterPath()
            rr.addRoundedRect(r, 6, 6)
            p.fillPath(rr, QColor(C["superficie3"]))
        f = fuente(30, QFont.Black, True)
        p.setFont(f)
        p.setPen(QColor(C["texto"]))
        ancho = self.width() - 44
        p.drawText(QRectF(22, 132, ancho, 44), Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(self.el.get("titulo") or "", Qt.ElideRight, ancho))
        tipo = {"pista": "Video" if self.el.get("es_video") else "Canción", "album": "Álbum",
                "artista": "Artista", "lista": "Lista"}.get(self.el.get("tipo"), "")
        sub = self.el.get("artista") or ""
        f2 = fuente(13.5)
        p.setFont(f2)
        p.setPen(QColor(C["texto2"]))
        texto = f"{tipo}  •  {sub}" if sub else tipo
        if self.el.get("tipo") == "album":
            texto = self.el.get("subtitulo") or tipo
        p.drawText(QRectF(22, 182, ancho - 80, 24), Qt.AlignVCenter,
                   QFontMetrics(f2).elidedText(texto, Qt.ElideRight, ancho - 80))
        if self._encima:
            r = self._r_play()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 110))
            p.drawEllipse(r.translated(0, 3))
            p.setBrush(QColor(C["acento"]))
            p.drawEllipse(r)
            p.drawPixmap(int(r.center().x() - 10), int(r.center().y() - 11),
                         iconos.pixmap("reproducir", 22, "#06070A"))


class TarjetaEnlace(QWidget):
    """Lo que aparece al pegar un enlace: reproducir, ver o descargar."""

    def __init__(self, ctx, url, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.url = url
        self.datos = None
        self.setObjectName("caja")
        self.setStyleSheet(f"QWidget#caja{{background:{C['superficie2']};border-radius:12px;}}")
        self.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(self)
        h.setContentsMargins(20, 20, 20, 20)
        h.setSpacing(20)
        self.portada = Portada(240, 135, "cuadrada", 8, "video")
        h.addWidget(self.portada)
        v = QVBoxLayout()
        v.setSpacing(6)
        plataforma = redes.detectar(url)
        et_red = QLabel(f"Enlace de {plataforma.nombre}" if plataforma is not redes.DESCONOCIDA
                        else "Enlace")
        et_red.setObjectName("secundario")
        v.addWidget(et_red)
        self.et_titulo = QLabel("Consultando el enlace…")
        self.et_titulo.setWordWrap(True)
        self.et_titulo.setStyleSheet("font-size:20px;font-weight:800;")
        v.addWidget(self.et_titulo)
        self.et_sub = QLabel(url)
        self.et_sub.setObjectName("secundario")
        self.et_sub.setWordWrap(True)
        v.addWidget(self.et_sub)
        v.addStretch(1)
        botones = QHBoxLayout()
        botones.setSpacing(8)
        self.bt_oir = QPushButton("  Escuchar")
        self.bt_oir.setObjectName("principal")
        self.bt_oir.setIcon(iconos.icono("reproducir", 15, C["acento_texto"]))
        self.bt_oir.clicked.connect(lambda: self._reproducir("audio"))
        self.bt_ver = QPushButton("  Ver video")
        self.bt_ver.setObjectName("contorno")
        self.bt_ver.setIcon(iconos.icono("video", 16, C["texto"]))
        self.bt_ver.clicked.connect(lambda: self._reproducir("video"))
        self.bt_bajar = QPushButton("  Descargar")
        self.bt_bajar.setObjectName("contorno")
        self.bt_bajar.setIcon(iconos.icono("descargar", 16, C["texto"]))
        self.bt_bajar.clicked.connect(self._menu_descargar)
        for b in (self.bt_oir, self.bt_ver, self.bt_bajar):
            b.setCursor(Qt.PointingHandCursor)
            botones.addWidget(b)
        botones.addStretch(1)
        v.addLayout(botones)
        h.addLayout(v, 1)
        en_segundo_plano(catalogo.formatos_disponibles, url, ctx.ajustes, ok=self._llego,
                         error=self._fallo, dueno=self)

    def _pista(self):
        d = self.datos or {}
        vid = catalogo.video_id_de(self.url)
        p = catalogo.nueva_pista(vid or "", d.get("titulo") or self.url,
                                 [{"nombre": d.get("autor") or "", "id": ""}] if d.get("autor") else [],
                                 None, d.get("duracion") or 0, d.get("miniatura") or "", True)
        if not vid:
            p["clave"] = "url:" + self.url
            p["url"] = self.url
        else:
            p["url"] = self.url
        return p

    def _llego(self, datos):
        self.datos = datos
        self.et_titulo.setText(datos.get("titulo") or self.url)
        alturas = sorted({f["alto"] for f in datos.get("formatos") or [] if f["alto"]},
                         reverse=True)
        partes = []
        if datos.get("autor"):
            partes.append(datos["autor"])
        if alturas:
            partes.append(f"hasta {alturas[0]}p")
        if datos.get("duracion"):
            from ..componentes import formato_tiempo
            partes.append(formato_tiempo(datos["duracion"]))
        self.et_sub.setText("  •  ".join(partes) or self.url)
        if datos.get("miniatura"):
            self.portada.set_url(datos["miniatura"])
        self.bt_ver.setEnabled(bool(alturas))

    def _fallo(self, e):
        self.et_titulo.setText("No se pudo leer el enlace")
        self.et_sub.setText(str(e)[:240])

    def _reproducir(self, modo):
        p = self._pista()
        self.ctx.reproductor.reproducir_pista(p, {"tipo": "enlace", "id": self.url,
                                                  "titulo": p["titulo"]}, modo,
                                              con_radio=bool(p.get("video_id")))
        if modo == "video":
            self.ctx.ventana.mostrar_video()

    def _menu_descargar(self):
        menu = QMenu(self)
        sub = self.ctx.menu_descargar(menu, [self._pista()])
        sub.exec(self.bt_bajar.mapToGlobal(self.bt_bajar.rect().bottomLeft()))


class PaginaBuscar(Pagina):
    def __init__(self, ctx, consulta="", filtro="todo", padre=None):
        super().__init__(ctx, padre)
        self.consulta = (consulta or "").strip()
        self.filtro = filtro
        self.titulo = f"Buscar: {self.consulta}" if self.consulta else "Buscar"
        self._pintar()

    def _pintar(self):
        self.vaciar()
        if not self.consulta:
            self._vacia()
            return
        urls = redes.extraer_urls(self.consulta)
        if urls and len(self.consulta.split()) <= len(urls):
            self._enlaces(urls)
            return
        fila = QHBoxLayout()
        fila.setSpacing(8)
        for clave, texto in FILTROS:
            c = Chip(texto)
            c.setChecked(clave == self.filtro)
            c.clicked.connect(lambda _=False, k=clave: self._filtrar(k))
            fila.addWidget(c)
        fila.addStretch(1)
        self.cuerpo.addLayout(fila)
        self.zona = QWidget()
        self.zv = QVBoxLayout(self.zona)
        self.zv.setContentsMargins(0, 0, 0, 0)
        self.zv.setSpacing(30)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        self._buscar()

    def _filtrar(self, clave):
        self.filtro = clave
        self._pintar()

    def _buscar(self):
        clave = ("buscar", self.consulta.lower(), self.filtro)
        datos = cache(clave, 10)
        if datos is not None:
            self._resultados(datos)
            return
        from ..componentes import Esqueleto
        self.zv.addWidget(Esqueleto("filas"))
        if self.filtro == "todo":
            funcion, args = catalogo.buscar_todo, (self.consulta,)
        else:
            funcion, args = catalogo.buscar, (self.consulta, self.filtro, 40)

        def listo(d, filtro=self.filtro):
            guardar_cache(("buscar", self.consulta.lower(), filtro), d)
            if filtro == self.filtro:
                self._resultados(d)

        def fallo(e):
            _borrar_layout(self.zv)
            self.zv.addWidget(SinResultados("aviso", "No se pudo buscar",
                                            f"Revisa tu conexión a internet.\n{str(e)[:160]}"))
        en_segundo_plano(funcion, *args, ok=listo, error=fallo, dueno=self)
        self.ctx.coleccion.anotar_busqueda(self.consulta)

    def _resultados(self, datos):
        _borrar_layout(self.zv)
        ctx = self.ctx
        if self.filtro == "todo":
            principal = datos.get("principal")
            secciones = datos.get("secciones") or []
            if not principal and not secciones:
                self._nada()
                return
            canciones = next((s for s in secciones if s["filtro"] == "canciones"), None)
            if principal or canciones:
                arriba = QHBoxLayout()
                arriba.setSpacing(24)
                if principal:
                    caja_p = QVBoxLayout()
                    t = QLabel("Resultado principal")
                    t.setObjectName("titulo_seccion")
                    caja_p.addWidget(t)
                    rp = ResultadoPrincipal(ctx, principal)
                    rp.abrir.connect(ctx.abrir_elemento)
                    rp.reproducir.connect(ctx.reproducir_elemento)
                    caja_p.addWidget(rp)
                    caja_p.addStretch(1)
                    arriba.addLayout(caja_p, 42)
                if canciones:
                    caja_c = QVBoxLayout()
                    fila_t = QHBoxLayout()
                    t = QLabel("Canciones")
                    t.setObjectName("titulo_seccion")
                    fila_t.addWidget(t)
                    fila_t.addStretch(1)
                    mas = QPushButton("Ver todas")
                    mas.setObjectName("enlace")
                    mas.setCursor(Qt.PointingHandCursor)
                    mas.clicked.connect(lambda: self._filtrar("canciones"))
                    fila_t.addWidget(mas)
                    caja_c.addLayout(fila_t)
                    lp = ListaPistas(ctx, mostrar_album=False, mostrar_cabecera=False,
                                     mostrar_numero=False)
                    pistas = canciones["elementos"][:4]
                    lp.set_pistas(pistas)
                    lp.al_reproducir = lambda i, ps=canciones["elementos"]: ctx.reproducir_pista(ps[i])
                    caja_c.addWidget(lp)
                    caja_c.addStretch(1)
                    arriba.addLayout(caja_c, 58)
                self.zv.addLayout(arriba)
            for s in secciones:
                if s["filtro"] == "canciones":
                    continue
                self.zv.addWidget(Carrusel(ctx, s["titulo"], s["elementos"],
                                           mas=lambda f=s["filtro"]: self._filtrar(f)))
            return

        elementos = datos or []
        if not elementos:
            self._nada()
            return
        if self.filtro == "canciones":
            lp = ListaPistas(ctx, mostrar_album=True)
            lp.set_pistas(elementos)
            lp.al_reproducir = lambda i: ctx.reproducir_pista(elementos[i])
            self.zv.addWidget(lp)
        else:
            self.zv.addWidget(Rejilla(ctx, "", elementos))

    def _nada(self):
        self.zv.addWidget(SinResultados(
            "lupa", f"No hay resultados para «{self.consulta}»",
            "Revisa cómo está escrito o prueba con menos palabras."))

    def _enlaces(self, urls):
        t = QLabel("Enlaces" if len(urls) > 1 else "Enlace")
        t.setObjectName("titulo_seccion")
        self.cuerpo.addWidget(t)
        for u in urls[:10]:
            if "list=" in u and ("youtube.com" in u or "youtu.be" in u) and "v=" not in u:
                lista_id = u.split("list=")[1].split("&")[0]
                b = QPushButton(f"  Abrir la lista de YouTube  ({lista_id[:18]}…)")
                b.setObjectName("contorno")
                b.setIcon(iconos.icono("lista", 16, C["texto"]))
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _=False, l=lista_id: self.ctx.navegar(
                    {"pagina": "lista", "id": l}))
                self.cuerpo.addWidget(b, 0, Qt.AlignLeft)
            self.cuerpo.addWidget(TarjetaEnlace(self.ctx, u))
        if len(urls) > 1:
            b = QPushButton(f"  Descargar los {len(urls)} enlaces con mis ajustes")
            b.setObjectName("principal")
            b.setIcon(iconos.icono("descargar", 16, C["acento_texto"]))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda: (self.ctx.gestor.agregar_varias(urls),
                                       self.ctx.aviso.emit(f"{len(urls)} descargas en la cola")))
            self.cuerpo.addWidget(b, 0, Qt.AlignLeft)
        self.cuerpo.addStretch(1)

    def _vacia(self):
        ctx = self.ctx
        recientes = ctx.coleccion.busquedas_recientes(14)
        if recientes:
            fila_t = QHBoxLayout()
            t = QLabel("Búsquedas recientes")
            t.setObjectName("titulo_seccion")
            fila_t.addWidget(t)
            fila_t.addStretch(1)
            borrar = QPushButton("Borrar")
            borrar.setObjectName("enlace")
            borrar.setCursor(Qt.PointingHandCursor)
            borrar.clicked.connect(lambda: (ctx.coleccion.borrar_busquedas(), self._pintar()))
            fila_t.addWidget(borrar)
            self.cuerpo.addLayout(fila_t)
            from PySide6.QtWidgets import QGridLayout
            chips = QWidget()
            flujo = _Flujo(chips)
            for texto in recientes:
                c = Chip(texto, conmutable=False)
                c.clicked.connect(lambda _=False, q=texto: ctx.ventana.buscar_texto(q))
                flujo.addWidget(c)
            self.cuerpo.addWidget(chips)
            _ = QGridLayout
        t = QLabel("Explorar todo")
        t.setObjectName("titulo_seccion")
        self.cuerpo.addWidget(t)
        self.zona_generos = QVBoxLayout()
        self.cuerpo.addLayout(self.zona_generos)
        self.cuerpo.addStretch(1)
        datos = cache("explorar", 60)
        if datos is not None:
            self._generos(datos)
        else:
            en_segundo_plano(catalogo.explorar, ok=self._generos_llegaron, error=lambda _e: None,
                             dueno=self)

    def _generos_llegaron(self, datos):
        guardar_cache("explorar", datos)
        self._generos(datos)

    def _generos(self, datos):
        generos = []
        for s in datos.get("secciones") or []:
            generos += [e for e in s["elementos"] if e.get("tipo") == "genero"]
        if generos:
            self.zona_generos.addWidget(Rejilla(self.ctx, "", generos, ancho=210))


class _Flujo:
    """Coloca chips en filas que se reparten solas (FlowLayout sencillo)."""

    def __init__(self, contenedor):
        from PySide6.QtWidgets import QVBoxLayout
        self.contenedor = contenedor
        self.v = QVBoxLayout(contenedor)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(8)
        self.fila = None
        self.ancho = 0

    def addWidget(self, w):
        tope = 900
        w.adjustSize()
        if self.fila is None or self.ancho + w.sizeHint().width() > tope:
            self.fila = QHBoxLayout()
            self.fila.setSpacing(8)
            self.fila.addStretch(1)
            self.v.addLayout(self.fila)
            self.ancho = 0
        self.fila.insertWidget(self.fila.count() - 1, w)
        self.ancho += w.sizeHint().width() + 8
