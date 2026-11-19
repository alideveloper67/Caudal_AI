# -*- coding: utf-8 -*-
"""Una lista compartida (de otra persona, donde soy miembro): quién añadió cada canción,
añadir o quitar según el permiso, miembros y salir. Se vuelve a traer cada ~20 s mientras está abierta."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton, QVBoxLayout, QWidget

from ... import catalogo
from ... import listas_compartidas as LC
from ...hilos import en_segundo_plano
from .. import iconos
from ..componentes import (BarraAcciones, Cabecera, FilaPista, ListaPistas, Pagina, SinResultados,
                           _borrar_layout, formato_duracion_larga)
from ..contexto import explicar_error, nube_de
from ..estilos import C


class PaginaListaCompartida(Pagina):
    """destino: {"pagina": "lista_compartida", "id": id de la lista, "el": {titulo, rol, dueno}}"""

    def __init__(self, ctx, destino, padre=None):
        super().__init__(ctx, padre, margen=(24, 0, 24, 32))
        self.destino = destino
        self.ident = destino["id"]
        el = destino.get("el") or {}
        self.nombre = el.get("titulo") or el.get("nombre") or "Lista compartida"
        self.rol = LC.normalizar_rol(el.get("rol"))
        self.dueno = el.get("dueno") or {}
        self.titulo = self.nombre
        self.nube = nube_de(ctx)
        self.pistas = []
        self.lista = None
        self.filtro = ""
        self.cargado = False
        self._firma = None
        self._trayendo = False
        self._contenido()
        if self.nube is None:
            self.error("Las listas compartidas necesitan una cuenta de Caudal con internet.")
            return
        previas = LC.ultima_conocida(("pistas", self.ident))
        if previas is not None:             # lo último que se vio, al instante; luego se actualiza
            self._llegan(previas)
        self._traer()
        self.reloj = QTimer(self)
        self.reloj.setInterval(LC.CADA_REFRESCO * 1000)
        self.reloj.timeout.connect(self._tic)
        self.reloj.start()

    # ------------------------------------------------------------ datos
    def _tic(self):
        if self.isVisible() and not self._trayendo:
            self._traer()

    def _traer(self):
        self._trayendo = True
        en_segundo_plano(self.nube.pistas, self.ident, ok=self._llegan_nube, error=self._fallo, dueno=self)

    def _llegan_nube(self, pistas):
        self._trayendo = False
        LC.guardar_cache(("pistas", self.ident), pistas)
        self._llegan(pistas)

    def _llegan(self, pistas):
        firma = [p.get("clave") for p in pistas]
        if self.cargado and firma == self._firma:
            return                           # nada cambió: no se repinta
        self._firma = firma
        self.pistas = pistas
        self.cargado = True
        self._contenido()

    def _fallo(self, e):
        self._trayendo = False
        texto = explicar_error(e, "abrir la lista")
        if not self.cargado:
            self.error(texto, self._reintentar)
        else:
            self.ctx.aviso.emit(texto)
            if "acceso" in texto or "no estás" in texto.lower():
                self.reloj.stop()

    def _reintentar(self):
        self.vaciar()
        self.cargando(tipo="filas")
        self._traer()

    # ------------------------------------------------------------ pintado
    def _yo(self):
        return self.nube.yo if self.nube else ""

    def _contenido(self):
        self.vaciar()
        ctx = self.ctx
        cab = Cabecera(ctx, "Lista compartida", self.nombre, "", lado=212)
        cab.set_portada(next((p.get("miniatura") for p in self.pistas if p.get("miniatura")), ""))
        cab.color_listo.connect(self.set_color)
        self.set_color("#2C3442")
        if self.dueno:
            cab.add_dato("Compartida · " + LC.nombre_persona(self.dueno), negrita=True)
        cab.add_dato(LC.etiqueta_rol(self.rol))
        n = len(self.pistas)
        dur = formato_duracion_larga(sum(p.get("duracion") or 0 for p in self.pistas))
        cab.add_dato(f"{n} {'canción' if n == 1 else 'canciones'}" + (f", {dur}" if dur else ""))
        cab.terminar()
        self.cuerpo.addWidget(cab)

        acciones = BarraAcciones()
        acciones.bt_play.clicked.connect(lambda: self._reproducir(False))
        acciones.bt_play.setEnabled(bool(self.pistas))
        acciones.boton("aleatorio", "Reproducir en aleatorio", lambda: self._reproducir(True), 26, 40)
        acciones.boton("usuario", "Quién está en la lista", self._miembros, 24, 40)
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
        self.cuerpo.addWidget(acciones)

        if not self.cargado:
            self.cargando(tipo="filas")
            return
        if not self.pistas:
            texto = ("Añade la primera canción con el buscador de abajo." if self.rol == "colaborador"
                     else "Esta lista todavía no tiene canciones.")
            self.cuerpo.addWidget(SinResultados("lista", "La lista está vacía", texto))
        else:
            self.lista = ListaPistas(ctx, mostrar_album=True)
            self.lista.al_menu_extra = self._menu_extra
            self.cuerpo.addWidget(self.lista)
            self._aplicar()
        if self.rol == "colaborador":
            self._buscador()
        else:
            nota = QLabel("Esta lista es de solo escuchar: no se pueden añadir ni quitar canciones.")
            nota.setObjectName("secundario")
            nota.setWordWrap(True)
            self.cuerpo.addWidget(nota)
        self.cuerpo.addStretch(1)

    def _a_mostrar(self):
        """Cada canción con «Añadida por …» en la columna del álbum (la original queda en `self.pistas`)."""
        f = self.filtro.strip().lower()
        salida = []
        for p in self.pistas:
            if f and f not in (p.get("titulo") or "").lower() and f not in (p.get("artista") or "").lower():
                continue
            quien = LC.quien_agrego(p)
            vista = dict(p)
            vista["album"] = {"nombre": "Añadida por " + ("ti" if str((p.get("_agregada_por") or {}).get("id"))
                                                            == str(self._yo()) else quien)}
            salida.append(vista)
        return salida

    def _aplicar(self):
        if self.lista is not None:
            self.lista.set_pistas(self._a_mostrar(), None)

    def _filtrar(self, texto):
        self.filtro = texto
        self._aplicar()

    def _reproducir(self, aleatorio):
        pistas = self._a_mostrar()
        if pistas:
            self.ctx.reproducir_lista(pistas, 0, None, aleatorio=aleatorio or None)

    # ------------------------------------------------------------ menús
    def _original(self, i):
        vistas = self._a_mostrar()
        if not (0 <= i < len(vistas)):
            return None
        clave = vistas[i].get("clave")
        return next((p for p in self.pistas if p.get("clave") == clave), None)

    def _menu_extra(self, menu, i):
        p = self._original(i)
        if p is None:
            return
        if LC.puede_quitar(self.rol, False, p, self._yo()):
            menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Quitar de esta lista",
                           lambda: self._quitar(p))

    def _menu_mas(self):
        menu = QMenu(self)
        menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir todo a la cola",
                       lambda: self.ctx.reproductor.agregar_a_cola(self._a_mostrar()))
        menu.addAction(iconos.icono("anadir_lista", 16, C["texto2"]), "Guardar todo en una de mis listas…",
                       lambda: self.ctx.elegir_listas(self._a_mostrar()))
        menu.addAction(iconos.icono("usuario", 16, C["texto2"]), "Quién está en la lista", self._miembros)
        menu.addSeparator()
        menu.addAction(iconos.icono("salir", 16, C["texto2"]), "Salir de la lista", self._salir)
        menu.exec(self.bt_mas.mapToGlobal(self.bt_mas.rect().bottomLeft()))

    def _quitar(self, p):
        def listo(_r):
            self.pistas = [x for x in self.pistas if x.get("clave") != p.get("clave")]
            LC.guardar_cache(("pistas", self.ident), self.pistas)
            self._firma = None
            self._llegan(self.pistas)

            def deshacer():
                en_segundo_plano(self.nube.agregar, self.ident, [p], ok=lambda _n: self._traer(),
                                 error=lambda e: self.ctx.aviso.emit(explicar_error(e)), dueno=self)
            self.ctx.avisar("Quitada de la lista", deshacer)
        en_segundo_plano(self.nube.quitar, self.ident, p["clave"], ok=listo,
                         error=lambda e: self.ctx.aviso.emit(explicar_error(e, "quitar la canción")), dueno=self)

    def _miembros(self):
        from ..dialogos_listas import _Base, _boton
        d = _Base("Quién está en la lista", 420, 0, self)
        d.titulo("Quién está en la lista", self.nombre)
        zona = QVBoxLayout()
        d.v.addLayout(zona)
        cargando = QLabel("Cargando…")
        cargando.setObjectName("ayuda")
        zona.addWidget(cargando)

        def pintar(miembros):
            from .perfil_comun import Avatar
            _borrar_layout(zona)
            for m in miembros:
                fila = QHBoxLayout()
                fila.addWidget(Avatar(34, LC.nombre_persona(m), C["acento"], m.get("foto_url"),
                                      marco=m.get("marco")))
                quien = LC.nombre_persona(m) + ("  ·  dueño" if m["es_dueno"] else "")
                et = QLabel(f"<b>{quien}</b><br><span style='color:{C['texto3']};font-size:11px'>@{m['usuario']}</span>")
                fila.addWidget(et, 1)
                caja = QWidget()
                caja.setLayout(fila)
                zona.addWidget(caja)
        en_segundo_plano(self.nube.miembros, self.ident, ok=pintar,
                         error=lambda e: cargando.setText(explicar_error(e, "ver quién está")), dueno=d)
        cerrar = _boton("Cerrar", "principal")
        cerrar.clicked.connect(d.accept)
        d.v.addWidget(cerrar, 0, Qt.AlignRight)
        d.exec()

    def _salir(self):
        r = QMessageBox.question(self, "Salir de la lista",
                                 f"¿Salir de «{self.nombre}»? Dejarás de verla en tu biblioteca; "
                                 "las canciones que añadiste se quedan en la lista.")
        if r != QMessageBox.Yes:
            return

        def listo(_r):
            LC._CACHE.pop("mis_compartidas", None)
            self.ctx.listas_cambio.emit()
            self.ctx.aviso.emit(f"Saliste de «{self.nombre}»")
            self.ctx.navegar({"pagina": "biblioteca"})
        en_segundo_plano(self.nube.salir, self.ident, ok=listo,
                         error=lambda e: self.ctx.aviso.emit(explicar_error(e, "salir de la lista")), dueno=self)

    # ------------------------------------------------------------ añadir canciones
    def _buscador(self):
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 18, 0, 0)
        v.setSpacing(10)
        t = QLabel("Añade música a esta lista")
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
        self._t_buscar.timeout.connect(self._buscar)
        self.e_buscar.textChanged.connect(lambda _t: self._t_buscar.start())

    def _buscar(self):
        texto = self.e_buscar.text().strip()
        if not texto:
            _borrar_layout(self.zona_res)
            return
        en_segundo_plano(catalogo.buscar, texto, "canciones", 12, ok=self._resultados,
                         error=lambda _e: None, dueno=self)

    def _resultados(self, pistas):
        _borrar_layout(self.zona_res)
        ya = {p.get("clave") for p in self.pistas}
        for i, p in enumerate([p for p in pistas if p.get("clave") not in ya][:10]):
            fila = QHBoxLayout()
            fp = FilaPista(self.ctx, p, i, mostrar_album=True, mostrar_numero=False)
            fp.reproducir.connect(lambda _i, p=p: self.ctx.reproducir_pista(p))
            fp.menu.connect(lambda _i, pos, p=p: self.ctx.menu_pista(p, pos))
            fila.addWidget(fp, 1)
            b = QPushButton("Añadir")
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, p=p, b=b: self._anadir(p, b))
            fila.addWidget(b)
            self.zona_res.addLayout(fila)

    def _anadir(self, p, boton):
        boton.setEnabled(False)
        boton.setText("Añadiendo…")

        def listo(n):
            try:
                boton.setText("Añadida ✓" if n else "Ya estaba")
            except RuntimeError:
                pass
            self.ctx.avisar(f"Añadida a «{self.nombre}»" if n else "Ya estaba en la lista",
                            (lambda: en_segundo_plano(self.nube.quitar, self.ident, p["clave"],
                                                      ok=lambda _r: self._traer(), error=lambda _e: None, dueno=self))
                            if n else None)
            self._traer()

        def fallo(e):
            try:
                boton.setEnabled(True)
                boton.setText("Añadir")
            except RuntimeError:
                pass
            self.ctx.aviso.emit(explicar_error(e, "añadir la canción"))
        en_segundo_plano(self.nube.agregar, self.ident, [p], ok=listo, error=fallo, dueno=self)
