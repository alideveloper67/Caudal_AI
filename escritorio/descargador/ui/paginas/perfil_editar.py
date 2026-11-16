# -*- coding: utf-8 -*-
"""Editar mi perfil: foto, nombre, descripción, frase, canción favorita, artista favorito,
géneros, color y qué se muestra. La foto se recorta cuadrada (512 px) y se comprime a JPEG."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ... import gif_perfil as G
from ... import legal
from ... import social as S
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import Portada
from ..estilos import C, hoja
from . import perfil_comun as PC
from .perfil_gif import BotonGif


def _dialogo_base(dialogo, titulo, ancho=560):
    dialogo.setObjectName("raiz")
    dialogo.setAttribute(Qt.WA_StyledBackground, True)
    dialogo.setStyleSheet(hoja(iconos.flechas_qss()))
    dialogo.setWindowTitle(titulo + " · Caudal")
    dialogo.setMinimumWidth(ancho)


class DialogoElegirCancion(QDialog):
    """Busca en el catálogo y elige una canción (con su carátula) como favorita."""

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        _dialogo_base(self, "Canción favorita", 520)
        self.ctx = ctx
        self.elegida = None
        self._buscando = ""
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)
        t = QLabel("Elige tu canción favorita")
        t.setStyleSheet("font-size:20px;font-weight:900;")
        v.addWidget(t)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Busca por título o artista")
        self.campo.returnPressed.connect(self._buscar)
        self.campo.textEdited.connect(lambda _t: self.reloj.start())
        v.addWidget(self.campo)
        r = getattr(ctx, "reproductor", None)
        actual = getattr(r, "actual", None) or {}
        if actual.get("video_id"):
            b = PC.boton("Usar lo que está sonando", "contorno", "musica",
                         al_pulsar=lambda: self._elegir(actual))
            v.addWidget(b, 0, Qt.AlignLeft)
        self.estado = PC.etiqueta("Escribe el nombre de la canción y pulsa Intro.", f"color:{C['texto3']};")
        v.addWidget(self.estado)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setMinimumHeight(300)
        self.area.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.area.viewport().setAutoFillBackground(False)
        self.interior = QWidget()
        self.interior.setStyleSheet("background:transparent;")
        self.lista = QVBoxLayout(self.interior)
        self.lista.setContentsMargins(0, 0, 6, 0)
        self.lista.setSpacing(2)
        self.lista.addStretch(1)
        self.area.setWidget(self.interior)
        v.addWidget(self.area, 1)
        c = QPushButton("Cancelar")
        c.setObjectName("contorno")
        c.clicked.connect(self.reject)
        v.addWidget(c, 0, Qt.AlignRight)
        self.reloj = QTimer(self)
        self.reloj.setSingleShot(True)
        self.reloj.setInterval(600)
        self.reloj.timeout.connect(self._buscar)

    def _buscar(self):
        from ... import catalogo
        texto = self.campo.text().strip()
        if len(texto) < 2 or texto == self._buscando:
            return
        self._buscando = texto
        self.estado.setText("Buscando…")
        en_segundo_plano(catalogo.buscar, texto, "canciones", 12, ok=lambda r, t=texto: self._pintar(t, r),
                         error=lambda _e: self.estado.setText("No se pudo buscar. Revisa tu internet."),
                         dueno=self, urgente=True)

    def _pintar(self, texto, resultados):
        if texto != self._buscando:
            return
        PC.limpiar(self.lista)
        pistas = [r for r in resultados if r.get("tipo") == "pista" and r.get("video_id")]
        self.estado.setText("" if pistas else f"No encontramos canciones para «{texto}».")
        self.estado.setVisible(not pistas)
        for p in pistas:
            self.lista.addWidget(self._fila(p))
        self.lista.addStretch(1)

    def _fila(self, p):
        b = QPushButton()
        b.setFixedHeight(58)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:10px;}}"
                        f"QPushButton:hover{{background:{C['superficie2']};}}")
        h = QHBoxLayout(b)
        h.setContentsMargins(8, 4, 8, 4)
        por = Portada(46, radio=6)
        por.set_url(p.get("miniatura") or "")
        h.addWidget(por)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(PC.etiqueta(p.get("titulo") or "", "font-size:13px;font-weight:700;", False))
        col.addWidget(PC.etiqueta(p.get("artista") or "", f"color:{C['texto2']};font-size:11.5px;", False))
        h.addLayout(col, 1)
        for w in b.findChildren(QLabel):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        b.clicked.connect(lambda _=False, p=p: self._elegir(p))
        return b

    def _elegir(self, p):
        vid = p.get("video_id") or ""
        self.elegida = {"video_id": vid, "titulo": (p.get("titulo") or "")[:120],
                        "artista": (p.get("artista") or "")[:120],
                        "miniatura": p.get("miniatura") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}
        self.accept()


class DialogoEditarPerfil(QDialog):
    def __init__(self, ctx, social, perfil, padre=None):
        super().__init__(padre)
        _dialogo_base(self, "Editar perfil", 600)
        self.resize(640, 740)
        self.ctx = ctx
        self.social = social
        self.p = perfil
        self.foto_ruta = None          # foto elegida en este diálogo (aún sin subir)
        self.quitar_foto = False
        self.banner_ruta = None        # imagen de fondo elegida en este diálogo (aún sin subir)
        self.foto_gif = None           # GIF ya preparado para subir como foto (solo donadores)
        self.banner_gif = None         # ídem, como fondo
        self.puede_gif = bool(getattr(getattr(ctx, "fondo", None), "puede", False))   # permiso en caché
        self.quitar_banner = False
        self.color = perfil.get("color_perfil")
        self.cancion = perfil.get("cancion_fav")
        self.generos = list(perfil.get("generos") or [])
        self.menor = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuerpo = QWidget()
        cuerpo.setObjectName("cuerpo_edicion")
        cuerpo.setStyleSheet("QWidget#cuerpo_edicion{background:transparent;}")
        c = QVBoxLayout(cuerpo)
        c.setContentsMargins(26, 22, 26, 12)
        c.setSpacing(14)
        area.setWidget(cuerpo)
        v.addWidget(area, 1)

        t = QLabel("Editar perfil")
        t.setStyleSheet("font-size:22px;font-weight:900;")
        c.addWidget(t)
        c.addWidget(self._vista_previa())

        # ---- foto
        c.addWidget(self._seccion("Foto"))
        fila = QHBoxLayout()
        fila.setSpacing(8)
        fila.addWidget(PC.boton("Elegir foto…", "contorno", "carpeta", al_pulsar=self._elegir_foto))
        self.bt_gif_foto = BotonGif("Buscar GIF", "lupa", lambda: self._buscar_gif(G.RAZON_FOTO))
        fila.addWidget(self.bt_gif_foto)
        self.bt_quitar = PC.boton("Quitar foto", "contorno", "papelera", al_pulsar=self._quitar)
        self.bt_quitar.setVisible(bool(perfil.get("foto_url")))
        fila.addWidget(self.bt_quitar)
        fila.addStretch(1)
        c.addLayout(fila)
        c.addWidget(PC.etiqueta("La foto se recorta en cuadrado y se reduce sola para que pese poco. Donadores y fundadores pueden usar un GIF animado.",
                                f"color:{C['texto3']};font-size:11.5px;"))

        # ---- imagen de fondo
        c.addWidget(self._seccion("Imagen de fondo"))
        self.fondo = PC.FondoPerfil(120, 14, False, 0.55, PC.color_de(perfil), perfil.get("banner_url"),
                                 animar=True)
        c.addWidget(self.fondo)
        fila_b = QHBoxLayout()
        fila_b.setSpacing(8)
        fila_b.addWidget(PC.boton("Elegir imagen de fondo…", "contorno", "carpeta", al_pulsar=self._elegir_banner))
        self.bt_gif_banner = BotonGif("Buscar GIF", "lupa", lambda: self._buscar_gif(G.RAZON_FONDO))
        fila_b.addWidget(self.bt_gif_banner)
        self.bt_quitar_banner = PC.boton("Quitar imagen", "contorno", "papelera", al_pulsar=self._quitar_fondo)
        self.bt_quitar_banner.setVisible(bool(perfil.get("banner_url")))
        fila_b.addWidget(self.bt_quitar_banner)
        fila_b.addStretch(1)
        c.addLayout(fila_b)
        c.addWidget(PC.etiqueta("Se recorta a 1280×480 y se comprime sola. Sin imagen, se usa el color de tu perfil.",
                                f"color:{C['texto3']};font-size:11.5px;"))

        # ---- datos
        c.addWidget(self._seccion("Sobre ti"))
        self.nombre = self._campo(perfil.get("nombre") or "", 60, "Tu nombre")
        c.addWidget(PC.etiqueta("Nombre", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        c.addWidget(self.nombre)
        self.frase = self._campo(perfil.get("frase") or "", 80, "Una frase corta, como un estado")
        c.addWidget(PC.etiqueta("Frase", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        c.addWidget(self.frase)
        self.cuenta_frase = PC.etiqueta("", f"color:{C['texto3']};font-size:11px;", False)
        c.addWidget(self.cuenta_frase)
        self.frase.textChanged.connect(lambda: self._contar(self.frase, self.cuenta_frase, 80))
        c.addWidget(PC.etiqueta("Descripción", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        self.bio = QPlainTextEdit()
        self.bio.setPlainText(perfil.get("bio") or "")
        self.bio.setPlaceholderText("Cuenta qué música te gusta, qué haces… (hasta 300 letras)")
        self.bio.setFixedHeight(96)
        c.addWidget(self.bio)
        self.cuenta_bio = PC.etiqueta("", f"color:{C['texto3']};font-size:11px;", False)
        c.addWidget(self.cuenta_bio)
        self.bio.textChanged.connect(self._limitar_bio)

        # ---- música
        c.addWidget(self._seccion("Tu música"))
        c.addWidget(PC.etiqueta("Canción favorita", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        self.caja_cancion = QHBoxLayout()
        self.caja_cancion.setSpacing(10)
        c.addLayout(self.caja_cancion)
        self._pintar_cancion()
        self.artista = self._campo(perfil.get("artista_fav") or "", 80, "Tu artista favorito")
        c.addWidget(PC.etiqueta("Artista favorito", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        c.addWidget(self.artista)
        c.addWidget(PC.etiqueta("Géneros (hasta 5)", f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        self.flujo_generos = PC.FlujoChips()
        self.botones_generos = {}
        for g in list(dict.fromkeys(self.generos + S.GENEROS_SUGERIDOS)):
            b = QPushButton(g)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(g in self.generos)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda marcado, g=g, b=b: self._genero(g, marcado, b))
            self.botones_generos[g] = b
            self.flujo_generos.agregar(b)
        c.addWidget(self.flujo_generos)
        self.aviso_generos = PC.etiqueta("", f"color:{C['aviso']};font-size:11.5px;", False)
        c.addWidget(self.aviso_generos)

        # ---- color
        c.addWidget(self._seccion("Color del perfil"))
        c.addWidget(PC.etiqueta("Tiñe la portada de tu perfil y tu tarjeta.",
                                f"color:{C['texto3']};font-size:11.5px;"))
        self.flujo_colores = PC.FlujoChips()
        self.botones_color = []
        for col in [None] + S.COLORES_PERFIL:
            b = QPushButton()
            b.setFixedSize(30, 30)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip("El color de Caudal" if col is None else col)
            b.clicked.connect(lambda _=False, col=col: self._poner_color(col))
            self.botones_color.append((col, b))
            self.flujo_colores.agregar(b)
        otro = PC.boton("Otro color…", "contorno", al_pulsar=self._otro_color)
        self.flujo_colores.agregar(otro)
        c.addWidget(self.flujo_colores)
        self._repintar_colores()

        # ---- privacidad
        c.addWidget(self._seccion("Privacidad"))
        self.chk_publico = QCheckBox("Perfil público en «Perfiles de Caudal»")
        self.chk_publico.setChecked(bool(perfil.get("publico")))
        c.addWidget(self.chk_publico)
        self.nota_publico = PC.etiqueta(
            "Si lo haces público, cualquier persona mayor de 18 años podrá verlo y darte me gusta. "
            "Si es privado, solo lo ven tus amigos.", f"color:{C['texto3']};font-size:11.5px;")
        c.addWidget(self.nota_publico)
        self.chk_top = QCheckBox("Mostrar mis estadísticas (artistas del mes e insignias)")
        self.chk_top.setChecked(bool(perfil.get("mostrar_top", True)))
        c.addWidget(self.chk_top)
        c.addStretch(1)

        # ---- pie
        pie = QFrame()
        pie.setStyleSheet(f"QFrame{{background:{C['panel']};border-top:1px solid {C['borde']};}}")
        h = QHBoxLayout(pie)
        h.setContentsMargins(26, 12, 26, 12)
        self.estado = PC.etiqueta("", f"color:{C['error']};font-size:12px;", True)
        h.addWidget(self.estado, 1)
        cancelar = QPushButton("Cancelar")
        cancelar.setObjectName("contorno")
        cancelar.clicked.connect(self.reject)
        h.addWidget(cancelar)
        self.bt_guardar = QPushButton("Guardar cambios")
        self.bt_guardar.setObjectName("principal")
        self.bt_guardar.clicked.connect(self._guardar)
        h.addWidget(self.bt_guardar)
        v.addWidget(pie)

        self._contar(self.frase, self.cuenta_frase, 80)
        self._limitar_bio()
        self.nombre.textChanged.connect(self._actualizar_vista)
        self.frase.textChanged.connect(self._actualizar_vista)
        self._actualizar_vista()
        self._aplicar_permiso_gif(self.puede_gif)
        en_segundo_plano(legal.perfil, social.sesion, ok=self._edad, error=lambda _e: None,
                         dueno=self, urgente=True)
        en_segundo_plano(social.puede_poner_fondo, ok=self._aplicar_permiso_gif, error=lambda _e: None,
                         dueno=self)

    # ------------------------------------------------------------ piezas
    def _seccion(self, texto):
        et = QLabel(texto.upper())
        et.setObjectName("seccion")
        et.setStyleSheet("background:transparent;margin-top:8px;")
        return et

    def _campo(self, texto, tope, ayuda):
        c = QLineEdit(texto)
        c.setMaxLength(tope)
        c.setPlaceholderText(ayuda)
        return c

    def _contar(self, campo, etiqueta, tope):
        etiqueta.setText(f"{len(campo.text())} de {tope}")

    def _limitar_bio(self):
        t = self.bio.toPlainText()
        if len(t) > 300:
            self.bio.setPlainText(t[:300])
            self.bio.moveCursor(QTextCursor.End)
        self.cuenta_bio.setText(f"{len(self.bio.toPlainText())} de 300")

    def _vista_previa(self):
        self.previa = QFrame()
        self.previa.setObjectName("previa")
        h = QHBoxLayout(self.previa)
        h.setContentsMargins(18, 16, 18, 16)
        h.setSpacing(14)
        self.av = PC.Avatar(72, self.p.get("nombre") or "", PC.color_de(self.p), self.p.get("foto_url"),
                            animar=True)
        h.addWidget(self.av)
        col = QVBoxLayout()
        col.setSpacing(2)
        self.pv_nombre = PC.etiqueta("", "font-size:18px;font-weight:900;", False)
        self.pv_frase = PC.etiqueta("", f"color:{C['texto2']};font-size:12.5px;font-style:italic;", False)
        col.addStretch(1)
        col.addWidget(self.pv_nombre)
        col.addWidget(self.pv_frase)
        col.addStretch(1)
        h.addLayout(col, 1)
        return self.previa

    def _actualizar_vista(self):
        color = self.color or C["acento"]
        self.previa.setStyleSheet(f"QFrame#previa{{background:{PC.tinte(color, 0.45)};border:1px solid "
                                  f"{PC.mezclar(C['borde'], color, 0.5)};border-radius:16px;}}")
        self.av.color = color
        self.av.nombre = self.nombre.text() if hasattr(self, "nombre") else ""
        self.av.update()
        self.pv_nombre.setText(self.nombre.text().strip() or self.p.get("usuario") or "Tu nombre")
        self.pv_frase.setText(f"“{self.frase.text().strip()}”" if self.frase.text().strip() else "")

    # ------------------------------------------------------------ foto
    def _elegir_foto(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige tu foto", "", S.FILTRO_IMAGEN_PERFIL)
        if not ruta:
            return
        if G.es_gif_ruta(ruta):
            if self.puede_gif:
                self._tomar_gif(ruta, G.RAZON_FOTO)
                return
            self._nota(G.MSG_EXCLUSIVO + ". Usamos el primer cuadro.")
        try:
            img = S.recortar_cuadrado(S._cargar_imagen(ruta), 256)
        except S.ErrorNube as e:
            self._nota(str(e), True)
            return
        from PySide6.QtGui import QPixmap
        self.foto_ruta = ruta
        self.foto_gif = None
        self.quitar_foto = False
        if not G.es_gif_ruta(ruta):
            self.estado.setText("")
        self._foto_previa(QPixmap.fromImage(img))
        self.bt_quitar.setVisible(True)

    def _foto_previa(self, pm):
        from ..imagenes import formar
        self.av._quitar_gif()
        self.av.pm = formar(pm.toImage(), 72, 72, "redonda")
        self.av.url = "local"
        self.av.update()

    def _quitar(self):
        self.foto_ruta = None
        self.foto_gif = None
        self.quitar_foto = True
        self.av._quitar_gif()
        self.av.pm = None
        self.av.url = ""
        self.av.update()
        self.bt_quitar.setVisible(False)

    # ------------------------------------------------------------ imagen de fondo
    def _elegir_banner(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige tu imagen de fondo", "", S.FILTRO_IMAGEN_PERFIL)
        if not ruta:
            return
        if G.es_gif_ruta(ruta):
            if self.puede_gif:
                self._tomar_gif(ruta, G.RAZON_FONDO)
                return
            self._nota(G.MSG_EXCLUSIVO + ". Usamos el primer cuadro.")
        try:
            img = S.recortar_proporcion(S._cargar_imagen(ruta), 640, 240)
        except S.ErrorNube as e:
            self._nota(str(e), True)
            return
        self.banner_ruta = ruta
        self.banner_gif = None
        self.quitar_banner = False
        if not G.es_gif_ruta(ruta):
            self.estado.setText("")
        self.fondo.set_imagen(img)
        self.bt_quitar_banner.setVisible(True)

    def _quitar_fondo(self):
        self.banner_ruta = None
        self.banner_gif = None
        self.quitar_banner = True
        self.fondo.quitar()
        self.bt_quitar_banner.setVisible(False)

    # ------------------------------------------------------------ GIF animados (donadores)
    def _aplicar_permiso_gif(self, puede):
        if isinstance(puede, tuple):
            puede = puede[0]
        self.puede_gif = bool(puede)
        self.bt_gif_foto.setVisible(self.puede_gif)
        self.bt_gif_banner.setVisible(self.puede_gif)

    def _nota(self, texto, error=False):
        """Mensaje en el pie: rojo si es un error, tono de aviso si solo informa."""
        color = C["error"] if error else C["aviso"]
        self.estado.setStyleSheet(f"color:{color};font-size:12px;")
        self.estado.setText(texto)

    cliente_gifs = None            # las pruebas ponen aquí un doble del servicio de GIF

    def _buscar_gif(self, modo):
        if not self.puede_gif:
            self._nota(G.MSG_EXCLUSIVO)
            return
        from .perfil_gif import DialogoBuscarGif
        d = DialogoBuscarGif(self.ctx, modo, self, cliente=self.cliente_gifs)
        if d.exec() == QDialog.Accepted and d.datos:
            self._tomar_gif(d.datos, modo)

    def _tomar_gif(self, origen, modo):
        """Deja el GIF listo (reduce si pesa mucho) sin congelar la ventana y lo muestra animado."""
        self._nota("Preparando tu GIF…")
        en_segundo_plano(G.preparar_gif, origen, modo, ok=lambda datos: self._gif_listo(datos, modo),
                         error=lambda e: self._nota(str(e) or G.MSG_NO_ABRE, error=True),
                         dueno=self, urgente=True)

    def _gif_listo(self, datos, modo):
        self.estado.setText("")
        if modo == G.RAZON_FOTO:
            self.foto_gif, self.foto_ruta, self.quitar_foto = datos, None, False
            self.av.poner_gif(datos)
            self.bt_quitar.setVisible(True)
        else:
            self.banner_gif, self.banner_ruta, self.quitar_banner = datos, None, False
            self.fondo.poner_gif(datos)
            self.bt_quitar_banner.setVisible(True)

    # ------------------------------------------------------------ canción favorita
    def _pintar_cancion(self):
        PC.limpiar(self.caja_cancion)
        if self.cancion:
            por = Portada(54, radio=8)
            por.set_url(self.cancion.get("miniatura") or "")
            self.caja_cancion.addWidget(por)
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(PC.etiqueta(self.cancion["titulo"], "font-size:13px;font-weight:700;", False))
            col.addWidget(PC.etiqueta(self.cancion.get("artista") or "", f"color:{C['texto2']};font-size:12px;",
                                      False))
            self.caja_cancion.addLayout(col, 1)
            self.caja_cancion.addWidget(PC.boton("Cambiar", "contorno", al_pulsar=self._elegir_cancion))
            self.caja_cancion.addWidget(PC.boton_redondo("cerrar", "Quitar", self._quitar_cancion, 32))
        else:
            self.caja_cancion.addWidget(PC.boton("Elegir del catálogo…", "contorno", "lupa",
                                                 al_pulsar=self._elegir_cancion))
            self.caja_cancion.addStretch(1)

    def _elegir_cancion(self):
        d = DialogoElegirCancion(self.ctx, self)
        if d.exec() == QDialog.Accepted and d.elegida:
            self.cancion = d.elegida
            self._pintar_cancion()

    def _quitar_cancion(self):
        self.cancion = None
        self._pintar_cancion()

    # ------------------------------------------------------------ géneros y color
    def _genero(self, g, marcado, boton):
        if marcado:
            if len(self.generos) >= 5:
                boton.setChecked(False)
                self.aviso_generos.setText("Puedes elegir hasta 5 géneros. Quita uno para poner otro.")
                return
            self.generos.append(g)
        elif g in self.generos:
            self.generos.remove(g)
        self.aviso_generos.setText("")

    def _poner_color(self, col):
        self.color = col
        self.fondo.set_color(col)
        self._repintar_colores()
        self._actualizar_vista()

    def _otro_color(self):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self.color or C["acento"]), self, "Elige el color de tu perfil")
        if c.isValid():
            self._poner_color(c.name().upper())

    def _repintar_colores(self):
        for col, b in self.botones_color:
            elegido = (col or None) == (self.color or None)
            if col is None:
                fondo = f"background:{C['superficie3']};"
                texto = "∅"
            else:
                fondo = f"background:{col};"
                texto = ""
            b.setText(texto)
            borde = f"3px solid {C['texto']}" if elegido else f"2px solid {C['panel']}"
            b.setStyleSheet(f"QPushButton{{{fondo}border:{borde};border-radius:15px;padding:0;"
                            f"color:{C['texto2']};font-size:13px;font-weight:800;}}")

    # ------------------------------------------------------------ edad y guardado
    def _edad(self, d):
        nac = (d or {}).get("nacimiento")
        if nac is not None and legal.edad(nac) < 18:
            self.menor = True
            self.chk_publico.setChecked(False)
            self.chk_publico.setEnabled(False)
            self.nota_publico.setText(
                "Como eres menor de 18 años, tu perfil se queda privado: solo lo ven tus amigos. "
                "Lo hacemos para cuidarte; cuando cumplas 18 podrás hacerlo público.")

    def _guardar(self):
        nombre = self.nombre.text().strip()
        if len(nombre) < 2:
            self._nota("Escribe tu nombre (al menos 2 letras).", True)
            return
        campos = {"nombre": nombre, "frase": self.frase.text().strip(),
                  "bio": self.bio.toPlainText().strip()[:300], "artista_fav": self.artista.text().strip(),
                  "generos": self.generos[:5], "color_perfil": self.color, "cancion_fav": self.cancion,
                  "perfil_publico": bool(self.chk_publico.isChecked() and not self.menor),
                  "mostrar_top": self.chk_top.isChecked()}
        foto, quitar = self.foto_ruta, self.quitar_foto
        banner, quitar_b = self.banner_ruta, self.quitar_banner
        foto_gif, banner_gif = self.foto_gif, self.banner_gif
        era_gif_foto = G.url_es_gif(self.p.get("foto_url"))
        era_gif_banner = G.url_es_gif(self.p.get("banner_url"))
        quiere_publico = campos["perfil_publico"]
        social = self.social
        self.bt_guardar.setEnabled(False)
        self.bt_guardar.setText("Guardando…")
        self.estado.setText("")

        def trabajo():
            if foto_gif:
                campos["foto_url"] = social.subir_foto_gif(foto_gif)
                social.borrar_variantes(["avatar.jpg"])
            elif foto:
                campos["foto_url"] = social.subir_foto(S.preparar_foto(foto))
                if era_gif_foto:
                    social.borrar_variantes(["avatar.gif"])
            elif quitar:
                social.quitar_foto()
                if era_gif_foto:
                    social.borrar_variantes(["avatar.gif"])
            if banner_gif:
                campos["banner_url"] = social.subir_banner_gif(banner_gif)
                social.borrar_variantes(["banner.jpg"])
            elif banner:
                campos["banner_url"] = social.subir_banner(S.preparar_banner(banner))
                if era_gif_banner:
                    social.borrar_variantes(["banner.gif"])
            elif quitar_b:
                social.quitar_banner()
                if era_gif_banner:
                    social.borrar_variantes(["banner.gif"])
            return social.guardar_perfil(campos)

        def listo(res):
            if quiere_publico and isinstance(res, dict) and res.get("perfil_publico") is False:
                PC.aviso(self.ctx, "Guardado. Tu perfil sigue privado: solo las personas mayores de 18 años "
                                   "pueden hacerlo público.")
            else:
                PC.aviso(self.ctx, "Perfil guardado")
            self.accept()

        def fallo(e):
            self.bt_guardar.setEnabled(True)
            self.bt_guardar.setText("Guardar cambios")
            self._nota(S.explicar(e, "guardar tu perfil"), True)
        en_segundo_plano(trabajo, ok=listo, error=fallo, dueno=self, urgente=True)
