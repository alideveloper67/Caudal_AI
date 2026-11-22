# -*- coding: utf-8 -*-
"""Albumes, listas de YouTube, tus listas, Tus me gusta y lo descargado."""

import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget)

from ... import catalogo
from ...hilos import en_segundo_plano
from .. import dialogo_portada, iconos
from ..componentes import (BarraAcciones, BotonIcono, Cabecera, FilaPista, ListaPistas, Pagina,
                           SinResultados, _borrar_layout, formato_duracion_larga)
from ..estilos import C
from .comun import cache, guardar_cache

ORDENES = [("personalizado", "Orden original"), ("titulo", "Título"), ("artista", "Artista"),
           ("album", "Álbum"), ("duracion", "Duración"), ("reciente", "Agregadas recientemente")]


class DialogoEditarLista(QDialog):
    def __init__(self, lista, padre=None):
        super().__init__(padre)
        self.setWindowTitle("Editar la lista")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        t = QLabel("Editar los datos")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        self.nombre = QLineEdit(lista.get("nombre") or "")
        self.nombre.setPlaceholderText("Nombre")
        v.addWidget(self.nombre)
        self.desc = QPlainTextEdit(lista.get("descripcion") or "")
        self.desc.setPlaceholderText("Añade una descripción (opcional)")
        self.desc.setFixedHeight(110)
        v.addWidget(self.desc)
        v.addSpacing(6)
        self.publica = QCheckBox("Lista pública")
        self.publica.setChecked(bool(lista.get("publica")))
        v.addWidget(self.publica)
        ayuda_pub = QLabel("Cualquier persona de Caudal puede abrirla y escucharla. "
                           "Si la dejas privada, solo tú la ves.")
        ayuda_pub.setObjectName("ayuda")
        ayuda_pub.setWordWrap(True)
        v.addWidget(ayuda_pub)
        self.en_perfil = QCheckBox("Mostrar en mi perfil")
        self.en_perfil.setChecked(bool(lista.get("publica")) and bool(lista.get("en_perfil")))
        v.addWidget(self.en_perfil)
        self.ayuda_perfil = QLabel("")
        self.ayuda_perfil.setObjectName("ayuda")
        self.ayuda_perfil.setWordWrap(True)
        v.addWidget(self.ayuda_perfil)
        self.publica.toggled.connect(self._ajustar_perfil)
        self._ajustar_perfil()
        b = QDialogButtonBox()
        ok = b.addButton("Guardar", QDialogButtonBox.AcceptRole)
        ok.setObjectName("principal")
        b.addButton("Cancelar", QDialogButtonBox.RejectRole)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        v.addWidget(b)

    def _ajustar_perfil(self):
        """«Mostrar en mi perfil» solo tiene sentido en una lista pública."""
        publica = self.publica.isChecked()
        self.en_perfil.setEnabled(publica)
        if not publica:
            self.en_perfil.setChecked(False)
        self.ayuda_perfil.setText(
            "Tus amistades y quien visite tu perfil la verán junto a tus datos." if publica
            else "Para mostrarla en tu perfil, primero hazla pública.")


class PaginaColeccion(Pagina):
    """destino: {"pagina": album|lista|mi_lista|me_gusta|disco, "id", "solo"}"""

    def __init__(self, ctx, destino, padre=None):
        super().__init__(ctx, padre, margen=(24, 0, 24, 32))
        self.destino = destino
        self.tipo = destino["pagina"]
        self.ident = destino.get("id")
        self.datos = {}
        self.pistas = []
        self.orden = "personalizado"
        self.filtro = ""
        self.titulo = ""
        self.lista = None
        if self.tipo in ("album", "lista"):
            clave = (self.tipo, self.ident)
            datos = cache(clave, 30)
            if datos is not None:
                self._pintar(datos)
            else:
                self.cargando(tipo="filas")
                funcion = catalogo.album if self.tipo == "album" else catalogo.lista
                en_segundo_plano(funcion, self.ident, ok=lambda d: self._llego(clave, d),
                                 error=lambda e: self.error(f"No se pudo abrir.\n{str(e)[:200]}",
                                                            lambda: ctx.navegar(dict(destino))),
                                 dueno=self)
        else:
            self._pintar(self._datos_locales())
            if self.tipo == "mi_lista":
                ctx.listas_cambio.connect(self._recargar_local)
                # una lista compartida la editan otras personas: mientras está abierta se vuelve a traer
                self._reloj_compartida = QTimer(self)
                self._reloj_compartida.setInterval(20000)
                self._reloj_compartida.timeout.connect(self._refrescar_compartida)
                self._reloj_compartida.start()
            elif self.tipo == "me_gusta":
                ctx.me_gusta_cambio.connect(self._recargar_local)
            elif self.tipo == "disco":
                ctx.descargas_cambio.connect(self._recargar_local)
            if destino.get("editar"):
                QTimer.singleShot(150, self._editar)

    # ------------------------------------------------------------ datos

    def _llego(self, clave, datos):
        guardar_cache(clave, datos)
        self._pintar(datos)

    def _datos_locales(self):
        col = self.ctx.coleccion
        if self.tipo == "me_gusta":
            pistas = col.lista_me_gusta()
            return {"titulo": "Tus me gusta", "pistas": pistas, "especial": "me_gusta",
                    "duracion": sum(p.get("duracion") or 0 for p in pistas)}
        if self.tipo == "disco":
            solo = self.destino.get("solo", True)
            pistas = col.descargadas(solo)
            return {"titulo": "Música descargada" if solo else "Videos descargados",
                    "pistas": pistas, "especial": "musica" if solo else "videos",
                    "duracion": sum(p.get("duracion") or 0 for p in pistas),
                    "tamano": sum(p.get("tamano") or 0 for p in pistas)}
        lista = col.lista(self.ident) or {}
        pistas = col.pistas_de_lista(self.ident)
        portadas = col.portadas_de_lista(self.ident, 1)
        return {"titulo": lista.get("nombre") or "Lista", "pistas": pistas,
                "descripcion": lista.get("descripcion") or "", "lista": lista,
                "miniatura": portadas[0] if portadas else "",
                "duracion": sum(p.get("duracion") or 0 for p in pistas)}

    def _recargar_local(self, *_):
        # una página que no se ve (otra encima, en el historial) no se rehace con cada «me gusta»
        # o descarga: se marca pendiente y se rehace al volver a verse
        if not self.isVisible() and self.window() is not self:
            self._pendiente_recargar = True
            return
        self._pendiente_recargar = False
        barra = self.verticalScrollBar().value()
        datos = self._datos_locales()
        if self._al_dia_sin_repintar(datos):
            return
        self._pintar(datos)

        def volver_al_sitio():
            try:
                self.verticalScrollBar().setValue(barra)
            except RuntimeError:          # la página ya se cerró
                pass
        QTimer.singleShot(0, volver_al_sitio)

    def showEvent(self, e):
        super().showEvent(e)
        if getattr(self, "_pendiente_recargar", False):
            def recargar():
                try:
                    self._recargar_local()
                except RuntimeError:      # la página se cerró antes
                    pass
            QTimer.singleShot(0, recargar)

    def contexto(self):
        tipo = {"album": "album", "lista": "lista", "mi_lista": "mi_lista",
                "me_gusta": "me_gusta", "disco": "disco"}[self.tipo]
        return {"tipo": tipo, "id": self.ident if self.ident is not None else tipo,
                "titulo": self.datos.get("titulo"), "miniatura": self.datos.get("miniatura", "")}

    # ------------------------------------------------------------ pintado

    def _texto_cuenta(self, datos):
        n = len(datos.get("pistas") or [])
        texto_n = f"{n} {'canción' if n == 1 else 'canciones'}"
        if self.tipo == "disco" and not self.destino.get("solo", True):
            texto_n = f"{n} {'video' if n == 1 else 'videos'}"
        dur = formato_duracion_larga(datos.get("duracion"))
        return texto_n + (f", {dur}" if dur else "")

    def _al_dia_sin_repintar(self, datos):
        """Si en una lista mía solo cambiaron las canciones (añadir, quitar, deshacer, mover), se
        ponen al día las filas y la cuenta SIN rehacer la página: no se pierde el buscador ni lo
        que ya buscaste, no se vuelven a pedir las recomendadas y la vista no salta. Una canción
        añadida aparece al final como una fila nueva. Devuelve False si hace falta repintar."""
        if self.tipo != "mi_lista" or not self.datos:
            return False
        antes, ahora = self.datos.get("lista") or {}, datos.get("lista") or {}
        if (datos.get("titulo") != self.datos.get("titulo")
                or datos.get("descripcion") != self.datos.get("descripcion")
                or datos.get("miniatura") != self.datos.get("miniatura")
                or {k: v for k, v in antes.items() if k != "tocada"}
                != {k: v for k, v in ahora.items() if k != "tocada"}):
            return False
        nuevas = list(datos.get("pistas") or [])
        if not nuevas:
            return False                          # quedó vacía: se enseña el aviso de lista vacía
        viejas = [p.get("clave") for p in self.pistas]
        claves = [p.get("clave") for p in nuevas]
        try:
            if self.lista is None:
                # era la lista vacía: la primera canción entra en el sitio del aviso
                vacia = getattr(self, "_w_vacia", None)
                if vacia is None:
                    return False
                self.lista = ListaPistas(self.ctx, mostrar_album=True)
                self.lista.al_menu_extra = self._menu_extra_mi_lista
                self.cuerpo.insertWidget(self.cuerpo.indexOf(vacia), self.lista)
                vacia.setParent(None)
                vacia.deleteLater()
                self._w_vacia = None
                self.pistas = nuevas
                self._aplicar_orden()
            elif (claves[:len(viejas)] == viejas and len(claves) > len(viejas)
                  and self.orden == "personalizado" and not self.filtro.strip()):
                self.pistas = nuevas
                self.lista.agregar_pistas(nuevas[len(viejas):])
            elif claves != viejas:
                self.pistas = nuevas
                self._aplicar_orden()
            self.datos = datos
            self._et_cuenta.setText(self._texto_cuenta(datos))
            self.bt_play.setEnabled(True)
        except RuntimeError:                      # algún trozo de la página ya se cerró
            return False
        self._marcar_sugeridas()
        return True

    def _pintar(self, datos):
        self.vaciar()
        self.lista = None
        self._w_vacia = None
        self._botones_sug = {}
        self.datos = datos
        self.titulo = datos.get("titulo") or ""
        self.titulo_cambio.emit(self.titulo)
        ctx = self.ctx
        self.pistas = list(datos.get("pistas") or [])

        nombre_tipo = {"album": datos.get("tipo_album") or "Álbum", "lista": "Lista",
                       "mi_lista": "Lista", "me_gusta": "Lista",
                       "disco": "En tu disco"}[self.tipo]
        cab = Cabecera(ctx, nombre_tipo, self.titulo, "", lado=212,
                       editable=dialogo_portada.es_editable(self.tipo))
        if dialogo_portada.es_editable(self.tipo):
            cab.portada.pedir_cambio.connect(self._cambiar_portada)
            cab.portada.imagen_soltada.connect(self._cambiar_portada)
        cab.color_listo.connect(self.set_color)
        if datos.get("especial"):
            colores = {"me_gusta": "#3F2CB8", "musica": "#0E5E73", "videos": "#7A3413"}
            self.set_color(colores[datos["especial"]])
            _portada_especial(cab.portada, datos["especial"])
        elif datos.get("miniatura"):
            cab.set_portada(datos["miniatura"])
        else:
            self.set_color("#2C3442")
        cab.set_descripcion(datos.get("descripcion") or "")
        if self.tipo == "album":
            for a in datos.get("artistas") or []:
                if a.get("id"):
                    cab.add_dato(a["nombre"], al_pulsar=lambda i=a["id"]: ctx.navegar(
                        {"pagina": "artista", "id": i}))
                else:
                    cab.add_dato(a["nombre"], negrita=True)
            if datos.get("anio"):
                cab.add_dato(str(datos["anio"]))
        elif self.tipo == "lista" and datos.get("autor"):
            cab.add_dato(datos["autor"], negrita=True)
        cab.add_dato(self._texto_cuenta(datos))
        self._et_cuenta = cab.linea.itemAt(cab.linea.count() - 1).widget()
        if datos.get("tamano"):
            from ...motor import formato_bytes
            cab.add_dato(formato_bytes(datos["tamano"]))
        cab.terminar()
        self.cuerpo.addWidget(cab)

        # --- acciones
        acciones = BarraAcciones()
        acciones.bt_play.clicked.connect(lambda: self._reproducir(False))
        acciones.bt_play.setEnabled(bool(self.pistas))
        self.bt_play = acciones.bt_play
        self.bt_aleatorio = acciones.boton("aleatorio", "Reproducir en aleatorio",
                                           lambda: self._reproducir(True), 26, 40)
        if self.tipo in ("album", "lista"):
            el = self._elemento()
            guardado = ctx.coleccion.guardado(self.tipo, self.ident)
            self.bt_guardar = acciones.boton("check_circulo" if guardado else "mas_circulo",
                                             "Quitar de tu biblioteca" if guardado
                                             else "Guardar en tu biblioteca",
                                             lambda: self._guardar(el), 28, 40)
            self.bt_guardar.set_activo(guardado, punto=False)
        self.bt_bajar = acciones.boton("descarga_circulo", "Descargar todo", self._menu_bajar,
                                       28, 40)
        if self.pistas and all(ctx.coleccion.esta_descargada(p) for p in self.pistas[:200]):
            self.bt_bajar.set_icono("descargado")
            self.bt_bajar.set_activo(True, punto=False)
            self.bt_bajar.setToolTip("Todo descargado: suena sin internet")
        if self.tipo == "mi_lista":
            acciones.boton("compartir", "Compartir esta lista con un código", self._compartir, 24, 40)
            acciones.boton("editar", "Editar nombre y descripción", self._editar, 22, 40)
        self.bt_mas = acciones.boton("puntos", "Más opciones", self._menu_mas, 24, 40)
        acciones.h.addStretch(1)
        self.e_filtro = QLineEdit()
        self.e_filtro.setObjectName("filtro_lista")
        self.e_filtro.setPlaceholderText("Buscar en la lista")
        self.e_filtro.setFixedWidth(220)
        self.e_filtro.setClearButtonEnabled(True)
        self.e_filtro.addAction(iconos.icono("lupa", 16, C["texto2"]), QLineEdit.LeadingPosition)
        self.e_filtro.setText(self.filtro)
        self.e_filtro.textChanged.connect(self._filtrar)
        acciones.widget(self.e_filtro)
        self.bt_orden = QPushButton(dict(ORDENES)[self.orden] + "  ")
        self.bt_orden.setObjectName("enlace")
        self.bt_orden.setCursor(Qt.PointingHandCursor)
        self.bt_orden.setIcon(iconos.icono("lista", 15, C["texto2"]))
        self.bt_orden.setLayoutDirection(Qt.RightToLeft)
        self.bt_orden.clicked.connect(self._menu_orden)
        acciones.widget(self.bt_orden)
        self.cuerpo.addWidget(acciones)

        # --- canciones
        if not self.pistas:
            self._vacia()
        else:
            self.lista = ListaPistas(ctx, mostrar_album=self.tipo != "album")
            if self.tipo == "mi_lista":
                self.lista.al_menu_extra = self._menu_extra_mi_lista
            self.cuerpo.addWidget(self.lista)
            self._aplicar_orden()
            if self.tipo == "album" and datos.get("anio"):
                pie = QLabel(f"{datos.get('anio')}  ·  {datos.get('tipo_album', 'Álbum')}")
                pie.setObjectName("secundario")
                self.cuerpo.addWidget(pie)
        if self.tipo == "mi_lista":
            self._buscador_para_lista()
        self.cuerpo.addStretch(1)

    def _vacia(self):
        textos = {
            "me_gusta": ("corazon", "Las canciones que te gustan aparecen aquí",
                         "Guárdalas pulsando el corazón."),
            "disco": ("descargar", "Aún no hay nada descargado",
                      "Descarga canciones, álbumes o videos y suenan sin internet."),
            "mi_lista": ("lista", "Tu lista está vacía",
                         "Busca canciones abajo, o arrastra cualquier canción hasta esta lista."),
        }
        icono, t, s = textos.get(self.tipo, ("musica", "No hay canciones", ""))
        self._w_vacia = SinResultados(icono, t, s)
        self.cuerpo.addWidget(self._w_vacia)

    def _ordenadas(self):
        pistas = list(self.pistas)
        o = self.orden
        if o == "titulo":
            pistas.sort(key=lambda p: (p.get("titulo") or "").lower())
        elif o == "artista":
            pistas.sort(key=lambda p: (p.get("artista") or "").lower())
        elif o == "album":
            pistas.sort(key=lambda p: ((p.get("album") or {}).get("nombre") or "").lower())
        elif o == "duracion":
            pistas.sort(key=lambda p: p.get("duracion") or 0)
        elif o == "reciente":
            pistas.reverse()
        f = self.filtro.strip().lower()
        if f:
            pistas = [p for p in pistas if f in (p.get("titulo") or "").lower()
                      or f in (p.get("artista") or "").lower()
                      or f in ((p.get("album") or {}).get("nombre") or "").lower()]
        return pistas

    def _aplicar_orden(self):
        if self.lista is not None:
            self.lista.set_pistas(self._ordenadas(), self.contexto())

    def _filtrar(self, texto):
        self.filtro = texto
        self._aplicar_orden()

    def _menu_orden(self):
        menu = QMenu(self)
        for clave, texto in ORDENES:
            a = menu.addAction(texto, lambda c=clave: self._ordenar(c))
            a.setCheckable(True)
            a.setChecked(clave == self.orden)
        menu.exec(self.bt_orden.mapToGlobal(self.bt_orden.rect().bottomLeft()))

    def _ordenar(self, clave):
        self.orden = clave
        self.bt_orden.setText(dict(ORDENES)[clave] + "  ")
        self._aplicar_orden()

    # ------------------------------------------------------------ acciones

    def _elemento(self):
        d = self.datos
        return {"tipo": self.tipo, "id": self.ident, "titulo": d.get("titulo") or "",
                "subtitulo": (d.get("tipo_album") or "Lista") + (
                    " • " + ", ".join(a["nombre"] for a in d.get("artistas") or [])
                    if d.get("artistas") else (f" • {d['autor']}" if d.get("autor") else "")),
                "miniatura": d.get("miniatura") or ""}

    def _reproducir(self, aleatorio):
        pistas = self._ordenadas()
        if pistas:
            self.ctx.reproducir_lista(pistas, 0, self.contexto(), aleatorio=aleatorio or None)
            if aleatorio is False and self.ctx.reproductor.aleatorio:
                pass

    def _guardar(self, el):
        self.ctx.alternar_guardado(el)
        guardado = self.ctx.coleccion.guardado(self.tipo, self.ident)
        self.bt_guardar.set_icono("check_circulo" if guardado else "mas_circulo")
        self.bt_guardar.set_activo(guardado, punto=False)

    def _menu_bajar(self):
        menu = QMenu(self)
        faltan = [p for p in self.pistas if not self.ctx.coleccion.esta_descargada(p)]
        if not faltan and self.pistas:
            a = menu.addAction("Ya está todo descargado")
            a.setEnabled(False)
            menu.addSeparator()
        objetivo = faltan or self.pistas
        sub = self.ctx.menu_descargar(menu, objetivo)
        sub.setTitle(f"Descargar {len(objetivo)} {'canción' if len(objetivo) == 1 else 'canciones'}")
        menu.exec(self.bt_bajar.mapToGlobal(self.bt_bajar.rect().bottomLeft()))

    def _menu_mas(self):
        menu = QMenu(self)
        ctx = self.ctx
        menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir todo a la cola",
                       lambda: ctx.reproductor.agregar_a_cola(self._ordenadas()))
        if self.tipo != "mi_lista":
            sub = menu.addMenu(iconos.icono("anadir_lista", 16, C["texto2"]), "Añadir a una lista")
            sub.addAction("Nueva lista…", lambda: ctx.anadir_a_lista(self.pistas, None))
            for l in ctx.coleccion.listas()[:40]:
                sub.addAction(l["nombre"], lambda i=l["id"]: ctx.anadir_a_lista(self.pistas, i))
        if self.tipo in ("album", "lista"):
            from PySide6.QtGui import QGuiApplication
            url = ("https://music.youtube.com/browse/" + self.ident if self.tipo == "album"
                   else "https://music.youtube.com/playlist?list=" + self.ident)
            menu.addAction(iconos.icono("enlace", 16, C["texto2"]), "Copiar enlace",
                           lambda: (QGuiApplication.clipboard().setText(url),
                                    ctx.aviso.emit("Enlace copiado")))
            if self.datos.get("lista_id") and self.tipo == "album":
                menu.addAction(iconos.icono("radio", 16, C["texto2"]), "Radio del álbum",
                               lambda: ctx.reproductor.reproducir_radio_id(
                                   "RDAMPL" + self.datos["lista_id"], f"Radio de {self.titulo}"))
        if self.tipo == "disco":
            carpeta = ctx.ajustes["carpeta"]
            menu.addAction(iconos.icono("carpeta", 16, C["texto2"]), "Abrir la carpeta de descargas",
                           lambda: os.path.isdir(carpeta) and os.startfile(carpeta))
        if self.tipo == "mi_lista":
            menu.addSeparator()
            menu.addAction(iconos.icono("compartir", 16, C["texto2"]), "Compartir lista…", self._compartir)
            dialogo_portada.agregar_al_menu(menu, ctx, self.ident, self)
            menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Borrar la lista",
                           self._borrar_lista)
        menu.exec(self.bt_mas.mapToGlobal(self.bt_mas.rect().bottomLeft()))

    def _menu_extra_mi_lista(self, menu, i):
        pistas = self.lista.pistas if self.lista else []
        if not (0 <= i < len(pistas)):
            return
        p = pistas[i]
        menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Quitar de esta lista",
                       lambda: self.ctx.quitar_de_lista(self.ident, p))
        if self.orden == "personalizado" and not self.filtro:
            if i > 0:
                menu.addAction("Subir", lambda: self._mover(i, i - 1))
            if i < len(pistas) - 1:
                menu.addAction("Bajar", lambda: self._mover(i, i + 1))

    def _mover(self, origen, destino):
        claves = [p["clave"] for p in self.pistas]
        c = claves.pop(origen)
        claves.insert(destino, c)
        self.ctx.coleccion.mover_en_lista(self.ident, claves)
        self.ctx.listas_cambio.emit()

    def _editar(self):
        lista = self.ctx.coleccion.lista(self.ident)
        if not lista:
            return
        d = DialogoEditarLista(lista, self)
        if d.exec():
            try:
                self.ctx.coleccion.editar_lista(self.ident, d.nombre.text(),
                                                d.desc.toPlainText().strip(),
                                                publica=d.publica.isChecked(),
                                                en_perfil=d.en_perfil.isChecked())
            except ValueError as e:
                QMessageBox.warning(self, "Caudal", str(e))
                return
            self.ctx.listas_cambio.emit()

    def _compartir(self):
        self.ctx.compartir_lista(self.ident)
        self._recargar_local()

    def _refrescar_compartida(self):
        """Solo si esta lista está compartida y la pantalla está a la vista: se trae esa lista (una petición)."""
        from ... import listas_compartidas as LC
        sinc = getattr(self.ctx, "sincronizador", None)
        if sinc is None or not self.isVisible():
            return
        u = (self.ctx.coleccion.lista(self.ident) or {}).get("uuid")
        if u and u in LC.codigos_guardados(self.ctx.coleccion):
            sinc.refrescar_lista(u)

    def _cambiar_portada(self, ruta=None):
        if self.tipo == "mi_lista":
            dialogo_portada.cambiar_portada(self.ctx, self.ident, self, ruta or None)

    def contextMenuEvent(self, e):
        """Clic derecho sobre la portada grande: cambiar o quitar la portada."""
        if self.tipo == "mi_lista":
            cab = self.findChild(dialogo_portada.PortadaEditable)
            if cab is not None and cab.rect().contains(cab.mapFromGlobal(e.globalPos())):
                menu = QMenu(self)
                dialogo_portada.agregar_al_menu(menu, self.ctx, self.ident, self)
                menu.exec(e.globalPos())
                return
        super().contextMenuEvent(e)

    def _borrar_lista(self):
        r = QMessageBox.question(self, "Borrar la lista",
                                 f"¿Borrar «{self.titulo}»? Las canciones no se borran del disco.")
        if r == QMessageBox.Yes:
            self.ctx.coleccion.borrar_lista(self.ident)
            self.ctx.listas_cambio.emit()
            self.ctx.navegar({"pagina": "inicio"})

    # ------------------------------------------------------------ anadir canciones

    def _buscador_para_lista(self):
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 18, 0, 0)
        v.setSpacing(10)
        t = QLabel("Busca algo para tu lista")
        t.setObjectName("titulo_seccion")
        v.addWidget(t)
        self.e_buscar = QLineEdit()
        self.e_buscar.setPlaceholderText("Busca canciones para añadir")
        self.e_buscar.setFixedWidth(380)
        self.e_buscar.addAction(iconos.icono("lupa", 16, C["texto2"]), QLineEdit.LeadingPosition)
        self.e_buscar.setClearButtonEnabled(True)
        v.addWidget(self.e_buscar)
        self.zona_res = QVBoxLayout()
        self.zona_res.setSpacing(0)
        v.addLayout(self.zona_res)
        self.cuerpo.addWidget(caja)
        self._t_buscar = QTimer(self)
        self._t_buscar.setSingleShot(True)
        self._t_buscar.setInterval(450)
        self._t_buscar.timeout.connect(self._buscar_para_lista)
        self.e_buscar.textChanged.connect(lambda _t: self._t_buscar.start())
        # recomendaciones a partir de la ultima cancion de la lista
        semilla = next((p for p in reversed(self.pistas) if p.get("video_id")), None)
        if semilla:
            en_segundo_plano(catalogo.radio, semilla["video_id"], limite=12,
                             ok=lambda d: self._mostrar_sugeridas(d.get("pistas") or [],
                                                                  "Recomendadas"),
                             error=lambda _e: None, dueno=self)

    def _buscar_para_lista(self):
        texto = self.e_buscar.text().strip()
        if not texto:
            _borrar_layout(self.zona_res)
            return
        en_segundo_plano(catalogo.buscar, texto, "canciones", 12,
                         ok=lambda ps: self._mostrar_sugeridas(ps, ""), error=lambda _e: None,
                         dueno=self)

    def _marcar_sugeridas(self):
        """Los botones del buscador dicen si esa canción ya está en la lista (y vuelven a
        «Añadir» si se deshace)."""
        ya = {p.get("clave") for p in self.pistas}
        for clave, b in list(getattr(self, "_botones_sug", {}).items()):
            try:
                dentro = clave in ya
                b.setText("Añadida" if dentro else "Añadir")
                b.setEnabled(not dentro)
            except RuntimeError:
                self._botones_sug.pop(clave, None)

    def _mostrar_sugeridas(self, pistas, titulo):
        _borrar_layout(self.zona_res)
        self._botones_sug = {}
        ya = {p.get("video_id") for p in self.pistas}
        if titulo:
            t = QLabel(titulo)
            t.setStyleSheet("font-size:16px;font-weight:800;margin-top:6px;")
            self.zona_res.addWidget(t)
            s = QLabel("Según lo que hay en esta lista")
            s.setObjectName("secundario")
            self.zona_res.addWidget(s)
        for i, p in enumerate([p for p in pistas if p.get("video_id") not in ya][:10]):
            fila = QHBoxLayout()
            fp = FilaPista(self.ctx, p, i, mostrar_album=True, mostrar_numero=False)
            fp.reproducir.connect(lambda _i, p=p: self.ctx.reproducir_pista(p))
            fp.menu.connect(lambda _i, pos, p=p: self.ctx.menu_pista(p, pos))
            fila.addWidget(fp, 1)
            b = QPushButton("Añadir")
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, p=p: self.ctx.anadir_a_lista([p], self.ident))
            if p.get("clave"):
                self._botones_sug[p["clave"]] = b
            fila.addWidget(b)
            self.zona_res.addLayout(fila)


def _portada_especial(widget, especial):
    """Portada de degradado con icono para Tus me gusta y lo descargado."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath

    colores = {"me_gusta": ("#5B3DF5", "#22D3EE"), "musica": ("#0E7490", "#22D3EE"),
               "videos": ("#7C2D12", "#F97316")}[especial]
    icono = {"me_gusta": "corazon_lleno", "musica": "descargado", "videos": "video"}[especial]

    def pintar(_e):
        p = QPainter(widget)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(0, 0, widget.width(), widget.height())
        ruta = QPainterPath()
        ruta.addRoundedRect(r, 6, 6)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(colores[0]))
        g.setColorAt(1, QColor(colores[1]))
        p.fillPath(ruta, g)
        lado = int(widget.width() * 0.34)
        p.drawPixmap(int((widget.width() - lado) / 2), int((widget.height() - lado) / 2),
                     iconos.pixmap(icono, lado, "#FFFFFF"))
    widget.paintEvent = pintar
    widget.update()


def _sin_usar():  # pragma: no cover
    return BotonIcono
