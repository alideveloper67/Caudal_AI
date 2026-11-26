# -*- coding: utf-8 -*-
"""Inicio: lo tuyo arriba, y lo que propone YouTube Music debajo."""

import time
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout,
                               QWidget)

from ... import catalogo
from ...hilos import en_segundo_plano
from .. import iconos, imagenes
from ..componentes import (BarraAcciones, Cabecera, Carrusel, Chip, FilaDesplazable, ListaPistas,
                           Pagina, RejillaRapida, Tarjeta, formato_duracion_larga, fuente)
from ..estilos import C
from .comun import cache, guardar_cache, pintar_secciones
from .rejilla_portadas import (FILAS, RejillaPortadas, clave_de, columnas_para, mezclar,
                               paginas_para)

_INTENTO_MIXES = {}


_INTENTO_DESCUBRE = {}
_INTENTO_GUSTOS = {}
_INTENTO_PARECIDOS = {}


def _con_copia(col, funcion):
    """Corre `funcion(col)` en un hilo con una conexión propia a la base (la de la interfaz no se
    comparte entre hilos); las colecciones de prueba sin copia se usan tal cual."""
    copiar = getattr(col, "copia_de_lectura", None)
    if copiar is None:
        return funcion(col)
    with copiar() as c:
        return funcion(c)


def _armar_mixes_hoy(c):
    """(lista, completos, historial): lo guardado de hoy, o el armado sin radio si aún no hay.
    Corre en segundo plano con la copia de la base; el historial sale solo si hace falta."""
    from ... import mixes as mx
    guardados, completos = mx.guardados_de_hoy(c)
    historial = None
    if not (guardados and completos):
        historial = mx.historial_para_mixes(c)
    lista = guardados if guardados else mx.construir(historial, radio=None)
    return lista, completos, historial


_TIPOS_ATAJO = ("album", "lista", "mi_lista", "radio", "artista")


def atajos_de(c):
    """Lo que abres a menudo: tus me gusta, lo último que pusiste y tus listas."""
    elementos = [{"tipo": "me_gusta", "especial": "me_gusta", "titulo": "Tus me gusta"}]
    vistos = set()
    recientes = None
    for x in c.contextos_recientes(16):
        clave = (x.get("tipo"), str(x.get("id")))
        if clave in vistos or x.get("tipo") not in _TIPOS_ATAJO or not x.get("titulo"):
            continue
        vistos.add(clave)
        el = {"tipo": x["tipo"], "id": x["id"], "titulo": x["titulo"], "miniatura": x.get("miniatura") or ""}
        if x["tipo"] == "mi_lista":
            portadas = c.portadas_de_lista(x["id"], 1)
            el["miniatura"] = portadas[0] if portadas else ""
        elif x["tipo"] == "radio" and not el["miniatura"]:
            recientes = recientes if recientes is not None else c.escuchado_hace_poco(60)
            el["miniatura"] = next((p.get("miniatura") or "" for p in recientes
                                    if p.get("video_id") == x.get("id")), "")
        elementos.append(el)
    for l in c.listas()[:8]:
        clave = ("mi_lista", str(l["id"]))
        if clave not in vistos:
            vistos.add(clave)
            portadas = c.portadas_de_lista(l["id"], 1)
            elementos.append({"tipo": "mi_lista", "id": l["id"], "titulo": l["nombre"],
                              "miniatura": portadas[0] if portadas else ""})
    return elementos


def lo_tuyo(c, solo_musica=False):
    """Todo lo de arriba de Inicio de una vez (va en segundo plano, con la copia de la base):
    {"rejilla", "recientes", "mixes_artistas"}."""
    recientes = c.escuchado_hace_poco(90)
    usadas = c.mas_escuchadas(24, 30)
    if solo_musica:
        recientes = [p for p in recientes if not p.get("es_video")]
        usadas = [p for p in usadas if not p.get("es_video")]
    # lo que más repites estos días, alternado con lo último que sonó
    canciones, vistas = [], set()
    for i in range(max(len(usadas), len(recientes[:40]))):
        for lista in (usadas, recientes[:40]):
            if i < len(lista) and lista[i].get("clave") not in vistas:
                vistas.add(lista[i].get("clave"))
                canciones.append(lista[i])
    return {"rejilla": mezclar(atajos_de(c), canciones), "recientes": recientes,
            "mixes_artistas": mixes_de_artistas(c)}


def mixes_de_artistas(c):
    salida = []
    historial = c.escuchado_hace_poco(150) + c.lista_me_gusta(limite=100)
    vistos = set()
    for a in c.artistas_frecuentes(14):
        # el mismo artista con dos fichas salía dos veces
        if a["nombre"].strip().lower() in vistos or len(salida) >= 8:
            continue
        vistos.add(a["nombre"].strip().lower())
        portada = next((p.get("miniatura") for p in historial
                        if any(x.get("id") == a["id"] for x in p.get("artistas") or [])), "")
        salida.append({"tipo": "artista", "id": a["id"], "titulo": f"Mix de {a['nombre']}",
                       "subtitulo": f"{a['nombre']} y artistas parecidos", "miniatura": portada})
    return salida


def canciones_para_ti(mixes, tope=48):
    """Una canción de cada mix por vuelta, sin repetir: «Canciones para ti»."""
    salida, vistas = [], set()
    largos = [m.get("pistas") or [] for m in mixes or []]
    for i in range(max((len(x) for x in largos), default=0)):
        for lista in largos:
            if i < len(lista) and len(salida) < tope:
                k = lista[i].get("video_id") or lista[i].get("clave")
                if k and k not in vistas:
                    vistas.add(k)
                    salida.append(lista[i])
    return salida


def saludo():
    h = time.localtime().tm_hour
    if 5 <= h < 12:
        return "Buenos días"
    if 12 <= h < 19:
        return "Buenas tardes"
    return "Buenas noches"


class PaginaInicio(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Inicio"
        self.set_color("#16324A")
        self.filtro = "todo"
        self._construir()

    def _construir(self):
        ctx = self.ctx
        cuenta = getattr(ctx, "cuenta", None) or {}
        nombre = (cuenta.get("nombre") or "").split(" ")[0]
        t = QLabel(f"{saludo()}, {nombre}" if nombre else saludo())
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:26px;font-weight:900;")
        t.setMinimumWidth(10)
        self.cuerpo.setSpacing(16)
        self.cuerpo.addWidget(t)
        from ..cumpleanos_ui import AvisoCumple      # «Hoy es tu cumple» y los amigos que cumplen hoy
        self.cuerpo.addWidget(AvisoCumple(ctx))

        chips = FilaDesplazable()
        self.chips = {}
        for clave, texto in (("todo", "Todo"), ("musica", "Música"), ("videos", "Videos"),
                             ("disco", "En tu disco")):
            c = Chip(texto)
            c.setChecked(clave == self.filtro)
            c.clicked.connect(lambda _=False, k=clave: self._filtrar(k))
            chips.agregar(c)
            self.chips[clave] = c
        self.cuerpo.addWidget(chips)

        self.zona = QWidget()
        self.zv = QVBoxLayout(self.zona)
        self.zv.setContentsMargins(0, 0, 0, 0)
        self.zv.setSpacing(30)
        self.cuerpo.addWidget(self.zona)
        self.cuerpo.addStretch(1)
        self._pintar()

    def _filtrar(self, clave):
        self.filtro = clave
        for k, c in self.chips.items():
            c.setChecked(k == clave)
        self._pintar()

    def _limpiar(self):
        from ..componentes import _borrar_layout
        _borrar_layout(self.zv)

    def _pintar(self):
        self._limpiar()
        ctx = self.ctx
        col = ctx.coleccion
        if self.filtro in ("todo", "musica"):
            self.rejilla = RejillaPortadas(ctx)
            self.rejilla.abrir.connect(self._abrir_atajo)
            self.rejilla.reproducir.connect(self._reproducir_atajo)
            self.rejilla.hide()
            self.zv.addWidget(self.rejilla)
            self.caja_para_ti, self.v_para_ti = self._caja()
            self.caja_recientes, self.v_recientes = self._caja()
            self._mixes_diarios()
            self._artistas_parecidos()
            self._gustos_inicio()
            self._descubre()
            self._maquina_del_tiempo()
            self.caja_artistas, self.v_artistas = self._caja()
            self._extras()
            self._pedir_lo_tuyo()
        if self.filtro == "disco":
            musica = col.descargadas(True)
            videos = col.descargadas(False)
            if musica:
                self.zv.addWidget(Carrusel(ctx, "Tu música descargada", musica[:40],
                                           mas=lambda: ctx.navegar({"pagina": "disco", "solo": True})))
            if videos:
                self.zv.addWidget(Carrusel(ctx, "Tus videos descargados", videos[:40],
                                           mas=lambda: ctx.navegar({"pagina": "disco", "solo": False})))
            if not musica and not videos:
                from ..componentes import SinResultados
                self.zv.addWidget(SinResultados(
                    "descargar", "Aún no hay nada en tu disco",
                    "Descarga canciones o videos y aparecerán aquí para escucharlos sin internet."))
            return

        if self.filtro == "videos":
            recientes_v = [p for p in col.escuchado_hace_poco(30) if p.get("es_video")]
            if recientes_v:
                self.zv.addWidget(Carrusel(ctx, "Videos que viste", recientes_v))

        datos = cache("inicio")
        if datos is not None:
            self._con_catalogo(datos)
        else:
            from ..componentes import Esqueleto
            self.et_cargando = Esqueleto("tarjetas")
            self.zv.addWidget(self.et_cargando)
            en_segundo_plano(catalogo.inicio, ok=self._llego, error=self._sin_red, dueno=self)

    def _caja(self):
        """Un hueco en su sitio para algo que llega después; sin nada no ocupa."""
        caja = QWidget()
        v = QVBoxLayout(caja)
        v.setContentsMargins(0, 0, 0, 0)
        caja.hide()
        self.zv.addWidget(caja)
        return caja, v

    def _pedir_lo_tuyo(self, solo_arriba=False):
        """Lee lo tuyo en segundo plano (la interfaz no espera a la base) y lo pinta al llegar."""
        self._pedido = getattr(self, "_pedido", 0) + 1
        n, musica = self._pedido, self.filtro == "musica"
        en_segundo_plano(_con_copia, self.ctx.coleccion, lambda c: lo_tuyo(c, musica),
                         ok=lambda r: self._lo_tuyo_listo(n, r, solo_arriba),
                         error=lambda _e: None, dueno=self)

    def _lo_tuyo_listo(self, n, r, solo_arriba):
        from ..componentes import _borrar_layout
        if n != self._pedido or self.filtro not in ("todo", "musica"):
            return                       # entretanto se cambió de ficha
        try:
            self.rejilla.poner(r["rejilla"] if len(r["rejilla"]) > 1 else [])
            self._recientes = r["recientes"]
            self._pintar_recientes()
            if solo_arriba:
                return
            _borrar_layout(self.v_artistas)
            self.caja_artistas.setVisible(bool(r["mixes_artistas"]))
            if r["mixes_artistas"]:
                self.v_artistas.addWidget(Carrusel(self.ctx, "Mixes de tus artistas", r["mixes_artistas"],
                                                   subtitulo="sus radios, con artistas parecidos"))
        except RuntimeError:
            pass                         # la página se rehizo mientras llegaban

    def _pintar_recientes(self):
        """«Volver a escuchar»: lo último que sonó y que no está ya en la rejilla de arriba."""
        from ..componentes import _borrar_layout
        _borrar_layout(self.v_recientes)
        columnas = columnas_para(max(300, self.viewport().width() - 48))
        ya = {clave_de(el) for el in self.rejilla.elementos[:paginas_para(
            len(self.rejilla.elementos), columnas) * columnas * FILAS]}
        quedan = [p for p in getattr(self, "_recientes", []) if clave_de(dict(p, tipo="pista")) not in ya][:24]
        self.caja_recientes.setVisible(len(quedan) >= 4)
        if len(quedan) >= 4:
            self.v_recientes.addWidget(Carrusel(self.ctx, "Volver a escuchar", quedan))

    def _pintar_para_ti(self, pistas):
        from ..componentes import _borrar_layout
        _borrar_layout(self.v_para_ti)
        self.caja_para_ti.setVisible(len(pistas) >= 4)
        if len(pistas) >= 4:
            self.v_para_ti.addWidget(RejillaRapida(self.ctx, "Canciones para ti", pistas, columnas=4))

    def refrescar_recientes(self):
        """Pulsar «Inicio» estando en Inicio: se pone al día lo de arriba y se sube, sin rehacer
        toda la página (mixes, máquina del tiempo...)."""
        if self.filtro not in ("todo", "musica") or getattr(self, "rejilla", None) is None:
            self._pintar()
        else:
            self._pedir_lo_tuyo(solo_arriba=True)
        self.verticalScrollBar().setValue(0)

    def _llego(self, datos):
        guardar_cache("inicio", datos)
        if getattr(self, "et_cargando", None) is not None:
            try:
                self.et_cargando.deleteLater()
            except RuntimeError:
                pass
            self.et_cargando = None
        self._con_catalogo(datos)

    def _con_catalogo(self, datos):
        secciones = datos.get("secciones") or []
        if self.filtro == "videos":
            secciones = [dict(s, elementos=[e for e in s["elementos"]
                                            if e.get("tipo") == "pista" and e.get("es_video")])
                         for s in secciones]
            secciones = [s for s in secciones if len(s["elementos"]) >= 3]
            for s in secciones:
                s["estilo"] = "carrusel"
        elif self.filtro == "musica":
            secciones = [s for s in secciones
                         if not all(e.get("tipo") == "pista" and e.get("es_video")
                                    for e in s["elementos"])]
        if self.filtro in ("todo", "musica") and not self._hay_para_ti:
            # sin historial todavía: «Canciones para ti» sale de la selección del catálogo
            primera = next((s for s in secciones if s.get("estilo") == "filas" and s.get("elementos")
                            and all(e.get("tipo") == "pista" for e in s["elementos"])), None)
            if primera is not None:
                self._del_catalogo = list(primera["elementos"])
                if self._mixes_vistos:
                    self._pintar_para_ti(self._del_catalogo)

        pintar_secciones(self.ctx, self.zv, secciones)

    def _sin_red(self, _e):
        if getattr(self, "et_cargando", None) is not None:
            try:
                self.et_cargando.deleteLater()
                self.et_cargando = None
                from ..componentes import SinResultados
                self.zv.addWidget(SinResultados(
                    "globo", "Sin conexión con YouTube Music",
                    "Mientras vuelve, tienes lo descargado en «En tu disco»."))
            except RuntimeError:
                pass

    def _abrir_atajo(self, el):
        if el.get("tipo") == "radio":
            if el.get("id") and len(str(el["id"])) == 11:
                p = next((x for x in self.ctx.coleccion.escuchado_hace_poco(60)
                          if x.get("video_id") == el["id"]), None)
                if p:
                    self.ctx.reproductor.iniciar_radio(p)
                    return
            self.ctx.reproductor.reproducir_radio_id(el["id"], el.get("titulo") or "Radio")
        else:
            self.ctx.abrir_elemento(el)

    def _reproducir_atajo(self, el):
        if el.get("tipo") == "pista":
            r = self.ctx.reproductor
            if self.rejilla.es_la_que_suena(el):
                r.alternar()
            else:
                self.ctx.reproducir_elemento(el)
        elif el.get("tipo") == "radio":
            self._abrir_atajo(el)
        elif self.rejilla.es_la_que_suena(el):
            self.ctx.reproductor.alternar()
        else:
            self.ctx.reproducir_elemento(el)

    # ------------------------------------------------------------ mixes diarios

    def _mixes_diarios(self):
        """Tus mixes diarios: salen al momento con lo tuyo y, cuando llega la
        radio de YouTube Music, se completan (una vez al dia)."""
        col = self.ctx.coleccion
        self._hay_para_ti = False
        self._mixes_vistos = False
        self._del_catalogo = []
        self.caja_mixes, self.v_mixes = self._caja()
        # leer la base y armar los mixes va en segundo plano: aparecen al llegar
        en_segundo_plano(_con_copia, col, _armar_mixes_hoy, ok=self._mixes_hoy_listos,
                         error=lambda _e: None, dueno=self)

    def _mixes_hoy_listos(self, r):
        from ... import mixes as mx
        lista, completos, historial = r
        try:
            self._pintar_mixes(lista)
            if completos or not self.v_mixes.count():
                return
            dia = mx.clave_dia(datetime.now())
            if _INTENTO_MIXES.get("dia") == dia and time.time() - _INTENTO_MIXES.get("t", 0) < 600:
                return            # sin red hace un momento: no se insiste en cada vuelta a Inicio
            if historial is None:
                return
            _INTENTO_MIXES.update(dia=dia, t=time.time())
            en_segundo_plano(mx.construir, historial, mx.radio_catalogo,
                             ok=self._mixes_listos, error=lambda _e: None, dueno=self)
        except RuntimeError:
            pass              # la página se rehizo mientras llegaban los mixes

    # ------------------------------------------------------------ hecho para ti

    def _descubre(self):
        """«Descubre para ti»: canciones nuevas elegidas por lo que escuchas."""
        from ... import recomendador as rc
        self.caja_descubre, self.v_descubre = self._caja()
        guardado = self.ctx.coleccion.estado(rc.CLAVE_DESCUBRE, None) or {}
        from ... import mixes as mx
        if guardado.get("dia") == mx.clave_dia(datetime.now()) and guardado.get("mix"):
            self._pintar_descubre(guardado["mix"])
            return
        if time.time() - _INTENTO_DESCUBRE.get("t", 0) < 600:
            return
        _INTENTO_DESCUBRE["t"] = time.time()
        en_segundo_plano(_con_copia, self.ctx.coleccion, rc.descubrir, ok=self._pintar_descubre,
                         error=lambda _e: None, dueno=self)

    def _gustos_inicio(self):
        """«Porque te gustan tus artistas»: sugerencias de los artistas favoritos elegidos."""
        from ... import recomendador as rc
        if not rc.leer_gustos(self.ctx.coleccion):
            return
        self.caja_gustos, self.v_gustos = self._caja()
        guardado = self.ctx.coleccion.estado(rc.CLAVE_PARA_TI, None) or {}
        from ... import mixes as mx
        if guardado.get("dia") == mx.clave_dia(datetime.now()) and guardado.get("mix"):
            self._pintar_gustos(guardado["mix"])
            return
        if time.time() - _INTENTO_GUSTOS.get("t", 0) < 600:
            return
        _INTENTO_GUSTOS["t"] = time.time()
        en_segundo_plano(_con_copia, self.ctx.coleccion, rc.sugerencias_gustos,
                         ok=self._pintar_gustos, error=lambda _e: None, dueno=self)

    def _artistas_parecidos(self):
        """«Artistas parecidos a los que escuchas»: gente nueva para ti, y a quién se parece cada uno."""
        from ... import recomendador as rc
        self.caja_parecidos, self.v_parecidos = self._caja()
        if time.time() - _INTENTO_PARECIDOS.get("t", 0) < 600 and _INTENTO_PARECIDOS.get("vacio"):
            return                   # hace un momento no había red (o historial): no se insiste en cada vuelta
        en_segundo_plano(_con_copia, self.ctx.coleccion, rc.artistas_parecidos, ok=self._pintar_parecidos,
                         error=lambda _e: None, dueno=self)

    def _pintar_parecidos(self, lista):
        from ..componentes import _borrar_layout
        _INTENTO_PARECIDOS.update(t=time.time(), vacio=len(lista or []) < 4)
        try:
            if len(lista or []) < 4:
                return
            _borrar_layout(self.v_parecidos)
            self.v_parecidos.addWidget(Carrusel(self.ctx, "Artistas parecidos a los que escuchas", lista,
                                                subtitulo="gente nueva para ti"))
            self.caja_parecidos.show()
        except RuntimeError:
            pass

    def _pintar_gustos(self, mix):
        if not mix:
            return
        try:
            self._carrusel_de_mixes(self.v_gustos, "Porque te gustan tus artistas",
                                    "música de tus favoritos y de otros parecidos", [mix])
        except RuntimeError:
            pass

    def _pintar_descubre(self, mix):
        if not mix:
            return
        try:
            self._carrusel_de_mixes(self.v_descubre, "Hecho para ti",
                                    "canciones que aún no has oído · se renueva cada día", [mix])
        except RuntimeError:
            pass

    def _maquina_del_tiempo(self):
        """Lee hasta un año de escuchas: si hoy ya se calculó sale al momento; si no, se calcula
        en segundo plano (con su propia conexión a la base) y aparece en su sitio al terminar."""
        from ... import recomendador as rc
        col = self.ctx.coleccion
        caja, v = self._caja()
        self.caja_tiempo, self.v_tiempo = caja, v
        lista = rc.maquina_del_tiempo_en_memoria(col)
        if lista is not None:
            self._pintar_maquina(lista)
            return
        caja.hide()
        copiar = getattr(col, "copia_de_lectura", None)
        if copiar is None:                       # colecciones de prueba: como antes
            self._pintar_maquina(rc.maquina_del_tiempo_de(col))
            return

        def calcular():
            with copiar() as c:
                return rc.maquina_del_tiempo_de(c)
        en_segundo_plano(calcular, ok=self._pintar_maquina, error=lambda _e: None, dueno=self)

    def _pintar_maquina(self, lista):
        try:
            if not lista:
                self.caja_tiempo.hide()
                return
            self.caja_tiempo.show()
            self._carrusel_de_mixes(self.v_tiempo, "Vuelve en el tiempo",
                                    "tu mes pasado y lo que escuchabas antes", lista)
        except RuntimeError:
            pass

    def _carrusel_de_mixes(self, v, titulo, subtitulo, lista):
        from ..componentes import _borrar_layout
        _borrar_layout(v)
        car = Carrusel(self.ctx, titulo, [], subtitulo=subtitulo)
        fila = car.area.widget().layout()
        alto = 0
        for i, el in enumerate(lista):
            tj = TarjetaMix(self.ctx, el)
            tj.abrir.connect(lambda e: self.ctx.navegar({"pagina": "mix", "id": e["id"], "el": e}))
            tj.reproducir.connect(lambda e: reproducir_mix(self.ctx, e))
            tj.menu.connect(lambda e, pos: menu_mix(self.ctx, e, pos))
            fila.insertWidget(i, tj)
            alto = max(alto, tj.height())
        car.area.setFixedHeight(alto + 2)
        v.addWidget(car)
        v.parentWidget().show()

    def _mixes_listos(self, nuevos):
        from ... import mixes as mx
        if not nuevos:
            return
        mx.guardar(self.ctx.coleccion, nuevos)
        guardados, _c = mx.guardados_de_hoy(self.ctx.coleccion)
        try:
            self._pintar_mixes(guardados or nuevos)
        except RuntimeError:
            pass

    def _pintar_mixes(self, lista):
        from ..componentes import _borrar_layout
        _borrar_layout(self.v_mixes)
        self._mixes_vistos = True
        para_ti = canciones_para_ti(lista)
        self._hay_para_ti = len(para_ti) >= 8
        self._pintar_para_ti(para_ti if self._hay_para_ti else (self._del_catalogo or para_ti))
        if not lista:
            self.caja_mixes.hide()
            return
        car = Carrusel(self.ctx, "Tus mixes diarios", [],
                       subtitulo="hechos para ti · se renuevan cada día")
        fila = car.area.widget().layout()
        alto = 0
        for i, el in enumerate(lista):
            tj = TarjetaMix(self.ctx, el)
            tj.abrir.connect(lambda e: self.ctx.navegar({"pagina": "mix", "id": e["id"]}))
            tj.reproducir.connect(lambda e: reproducir_mix(self.ctx, e))
            tj.menu.connect(lambda e, pos: menu_mix(self.ctx, e, pos))
            fila.insertWidget(i, tj)
            alto = max(alto, tj.height())
        car.area.setFixedHeight(alto + 2)
        self.v_mixes.addWidget(car)
        self.caja_mixes.show()

    def _extras(self):
        """Modo estudio y tu resumen: dos accesos pequeños, uno al lado del otro."""
        self.caja_extras = _DosColumnas()
        self.zv.addWidget(self.caja_extras)
        self._tarjeta_estudio()
        self._banner_resumen()

    def _tarjeta_estudio(self):
        """La entrada calmada al Modo estudio, con lo que llevas hoy si ya estudiaste."""
        try:
            from ... import estudio as E
            from .estudio import TarjetaEstudioInicio
            est = E.Estadisticas()
            texto = ""
            if est.hoy() > 0:
                texto = f"Hoy llevas {E.formato_duracion(est.hoy())} de enfoque"
                if est.racha() > 1:
                    texto += f"  ·  {est.racha()} días seguidos"
            t = TarjetaEstudioInicio(texto)
            t.compacta()
            t.clicked.connect(lambda: self.ctx.navegar({"pagina": "estudio"}))
            self.caja_extras.agregar(t)
        except Exception:  # noqa: BLE001 - una tarjeta nunca debe romper Inicio
            pass

    def _banner_resumen(self):
        """El resumen de la semana se calcula en segundo plano; el banner aparece al llegar."""
        from ... import mixes as mx

        def calcular(c):
            return mx.calcular_resumen(mx.leer_historial(
                c, desde=datetime.now() - timedelta(days=8)), "semana")

        caja = self.caja_extras

        def listo(r):
            if r["vacio"]:
                return
            try:
                b = BannerResumen(r)
                b.setFixedHeight(84)
                b.clicked.connect(lambda: self.ctx.navegar({"pagina": "resumen"}))
                caja.agregar(b)
            except RuntimeError:
                pass
        en_segundo_plano(_con_copia, self.ctx.coleccion, calcular, ok=listo,
                         error=lambda _e: None, dueno=self)


class _DosColumnas(QWidget):
    """Dos tarjetas en fila; si no caben, una debajo de la otra."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.h = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.h.setContentsMargins(0, 0, 0, 0)
        self.h.setSpacing(12)

    def agregar(self, w):
        w.setMinimumWidth(10)
        self.h.addWidget(w, 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.h.setDirection(QBoxLayout.LeftToRight if self.width() >= 640 else QBoxLayout.TopToBottom)


# ---------------------------------------------------------------- mixes

def contexto_mix(el):
    return {"tipo": "mix", "id": el.get("id"), "titulo": el.get("titulo"),
            "miniatura": el.get("miniatura") or ""}


def reproducir_mix(ctx, el, aleatorio=None):
    pistas = el.get("pistas") or []
    if pistas:
        ctx.reproducir_lista(pistas, 0, contexto_mix(el), aleatorio)


def menu_mix(ctx, el, pos):
    pistas = el.get("pistas") or []
    menu = QMenu(ctx.ventana)
    menu.addAction(iconos.icono("reproducir", 16, C["texto2"]), "Reproducir",
                   lambda: reproducir_mix(ctx, el))
    menu.addAction(iconos.icono("aleatorio", 16, C["texto2"]), "Reproducir en aleatorio",
                   lambda: reproducir_mix(ctx, el, True))
    menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir a la cola",
                   lambda: ctx.reproductor.agregar_a_cola(pistas))
    menu.addSeparator()
    if el.get("nombre_lista"):
        menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Guardar como lista",
                       lambda: guardar_mix_como_lista(ctx, el))
    ctx._submenu_listas(menu, pistas)
    ctx.menu_descargar(menu, pistas)
    menu.exec(pos)


def guardar_mix_como_lista(ctx, el):
    """«Tu mes pasado» (y parecidos) pasa a ser una lista tuya de verdad."""
    from ... import recomendador as rc
    try:
        _id, nombre = rc.guardar_como_lista(ctx.coleccion, el)
    except ValueError as e:
        ctx.aviso.emit(str(e))
        return None
    ctx.listas_cambio.emit()
    ctx.aviso.emit(f"Guardada como lista: «{nombre}»")
    return nombre


def dibujar_cubriendo(p, img, celda):
    """drawImage con recorte tipo «cover»."""
    w, h = img.width(), img.height()
    if w <= 0 or h <= 0 or celda.height() <= 0:
        return
    proporcion = celda.width() / celda.height()
    if w / h > proporcion:
        nw = h * proporcion
        origen = QRectF((w - nw) / 2, 0, nw, h)
    else:
        nh = w / proporcion
        origen = QRectF(0, (h - nh) / 2, w, nh)
    p.drawImage(celda, img, origen)


def pintar_mosaico(p, r, imgs, color, radio=6):
    """Portada de mix: 2x2 con cuatro portadas (o una sola), con el color del mix
    como franja abajo, como los mixes diarios de Spotify."""
    ruta = QPainterPath()
    ruta.addRoundedRect(r, radio, radio)
    p.save()
    p.setClipPath(ruta)
    base = QColor(color)
    grad = QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0, base.darker(130))
    grad.setColorAt(1, base.darker(320))
    p.fillRect(r, grad)
    imgs = [i for i in imgs if i is not None and not i.isNull()]
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    if len(imgs) >= 4:
        mitad = r.width() / 2
        for k, img in enumerate(imgs[:4]):
            celda = QRectF(r.x() + (k % 2) * mitad, r.y() + (k // 2) * mitad, mitad, mitad)
            dibujar_cubriendo(p, img, celda)
    elif imgs:
        dibujar_cubriendo(p, imgs[0], r)
    else:
        lado = int(r.width() * 0.3)
        p.drawPixmap(int(r.center().x() - lado / 2), int(r.center().y() - lado / 2),
                     iconos.pixmap("musica", lado, "#FFFFFF"))
    velo = QLinearGradient(r.left(), r.bottom() - r.height() * 0.5, r.left(), r.bottom())
    velo.setColorAt(0, QColor(0, 0, 0, 0))
    velo.setColorAt(1, QColor(0, 0, 0, 170))
    p.fillRect(r, velo)
    alto = max(3.0, r.height() * 0.035)
    p.fillRect(QRectF(r.left(), r.bottom() - alto, r.width(), alto), base)
    p.restore()


class Mosaico(QObject):
    """Baja las portadas de un mix y avisa con el pixmap compuesto."""

    listo = Signal(QPixmap)

    def __init__(self, el, lado, rotulo=True, padre=None):
        super().__init__(padre)
        self.el = el
        self.lado = lado
        self.rotulo = rotulo
        self.urls = list(el.get("miniaturas") or ([el["miniatura"]] if el.get("miniatura") else []))
        self.imgs = {}
        for u in self.urls:
            imagenes.imagen(u, lambda img, u=u: self._llego(u, img))

    def _llego(self, url, img):
        try:
            self.imgs[url] = img
            self.listo.emit(self.pixmap())
        except RuntimeError:
            pass

    def pixmap(self):
        app = QApplication.instance()
        escala = app.devicePixelRatio() if app is not None else 1.0
        lado = self.lado
        pm = QPixmap(int(lado * escala), int(lado * escala))
        pm.setDevicePixelRatio(escala)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(0, 0, lado, lado)
        pintar_mosaico(p, r, [self.imgs.get(u) for u in self.urls],
                       self.el.get("color") or C["acento"], 6 if lado < 300 else 8)
        if self.rotulo:
            # «Mix diario 3» escrito sobre la portada
            f = fuente(max(11, lado * 0.105), QFont.Black, True)
            p.setFont(f)
            p.setPen(QColor("#FFFFFF"))
            margen = lado * 0.08
            p.drawText(QRectF(margen, lado * 0.5, lado - 2 * margen, lado * 0.42),
                       Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap,
                       self.el.get("titulo") or "Mix")
        p.end()
        return pm


class TarjetaMix(Tarjeta):
    """Tarjeta de un mix diario, con la portada en mosaico."""

    def __init__(self, ctx, el, ancho=176, padre=None):
        super().__init__(ctx, dict(el, miniatura=""), ancho, padre)
        self.el = el
        self._mosaico = Mosaico(el, self.lado_img, padre=self)
        self._pm = self._mosaico.pixmap()
        self._mosaico.listo.connect(self._con_mosaico)

    def _con_mosaico(self, pm):
        self._pm = pm
        self.update()


class PaginaMix(Pagina):
    """Un mix diario: cabecera con el mosaico y sus canciones."""

    def __init__(self, ctx, destino, padre=None):
        super().__init__(ctx, padre, margen=(24, 0, 24, 32))
        from ... import mixes as mx
        self.destino = destino
        # «Descubre», «Similares», la máquina del tiempo o una mezcla traen ya sus canciones
        self.el = destino.get("el")
        if self.el is None:
            guardados, _c = mx.guardados_de_hoy(ctx.coleccion)
            if not guardados:
                guardados = mx.construir(mx.historial_para_mixes(ctx.coleccion), radio=None)
            self.el = next((m for m in guardados or [] if m.get("id") == destino.get("id")), None)
        if self.el is None:
            self.titulo = "Mix diario"
            self.error("Este mix ya no está: los mixes se renuevan cada día.",
                       lambda: ctx.navegar({"pagina": "inicio"}))
            return
        self._pintar()

    def _pintar(self):
        ctx, el = self.ctx, self.el
        self.titulo = el.get("titulo") or "Mix diario"
        pistas = el.get("pistas") or []
        self.set_color(QColor(el.get("color") or C["acento"]).darker(230).name())
        guardable = bool(el.get("nombre_lista"))
        cab = Cabecera(ctx, "Tu mes pasado" if guardable else "Mix diario", self.titulo, "",
                       lado=212)
        self._mosaico = Mosaico(el, 212, rotulo=False, padre=self)
        portada = cab.portada
        portada.pm = self._mosaico.pixmap()

        def nuevo(pm):
            try:
                portada.pm = pm
                portada.update()
            except RuntimeError:
                pass
        self._mosaico.listo.connect(nuevo)
        if guardable:
            cab.set_descripcion(f"{el.get('subtitulo') or ''}. Guárdala como lista para "
                                "no perderla cuando pase el tiempo.")
        else:
            cab.set_descripcion("Lo que más escuchas mezclado con canciones parecidas. "
                                "Se renueva cada día.")
        nombres = el.get("artistas") or []
        if nombres:
            cab.add_dato(", ".join(nombres[:4]) + (" y más" if len(nombres) > 4 else ""),
                         negrita=True)
        n = len(pistas)
        dur = formato_duracion_larga(sum(p.get("duracion") or 0 for p in pistas))
        cab.add_dato(f"{n} {'canción' if n == 1 else 'canciones'}" + (f", {dur}" if dur else ""))
        cab.terminar()
        self.cuerpo.addWidget(cab)

        acciones = BarraAcciones()
        acciones.bt_play.clicked.connect(lambda: reproducir_mix(ctx, el))
        acciones.bt_play.setEnabled(bool(pistas))
        acciones.boton("aleatorio", "Reproducir en aleatorio",
                       lambda: reproducir_mix(ctx, el, True), 26, 40)
        acciones.boton("cola", "Añadir a la cola",
                       lambda: ctx.reproductor.agregar_a_cola(pistas), 24, 40)
        if guardable:
            self.bt_guardar = QPushButton("  Guardar como lista")
            self.bt_guardar.setObjectName("contorno")
            self.bt_guardar.setIcon(iconos.icono("lista", 16, C["texto"]))
            self.bt_guardar.setCursor(Qt.PointingHandCursor)
            self.bt_guardar.setToolTip(f"Crea la lista «{el['nombre_lista']}» con estas canciones")
            self.bt_guardar.clicked.connect(self._guardar_lista)
            acciones.widget(self.bt_guardar)
        self.bt_mas = acciones.boton("puntos", "Más opciones", self._menu, 24, 40)
        acciones.terminar()
        self.cuerpo.addWidget(acciones)

        self.lista = ListaPistas(ctx)
        self.lista.set_pistas(pistas, contexto_mix(el))
        self.cuerpo.addWidget(self.lista)
        self.cuerpo.addStretch(1)

    def _guardar_lista(self):
        nombre = guardar_mix_como_lista(self.ctx, self.el)
        if nombre:
            self.bt_guardar.setText("  Guardada en tus listas")
            self.bt_guardar.setEnabled(False)

    def _menu(self):
        menu_mix(self.ctx, self.el, self.bt_mas.mapToGlobal(self.bt_mas.rect().bottomLeft()))


# ---------------------------------------------------------------- resumen

class BannerResumen(QWidget):
    """Entrada a «Tu resumen» desde Inicio: una franja con tus minutos de la semana."""

    clicked = Signal()

    def __init__(self, r, padre=None):
        super().__init__(padre)
        self.r = r
        self.setFixedHeight(96)
        self.setCursor(Qt.PointingHandCursor)
        self._encima = 0.0
        self._objetivo = 0.0
        self._t = QTimer(self)
        self._t.setInterval(16)
        self._t.timeout.connect(self._paso)

    def _paso(self):
        self._encima += (self._objetivo - self._encima) * 0.25
        if abs(self._encima - self._objetivo) < 0.01:
            self._encima = self._objetivo
            self._t.stop()
        self.update()

    def enterEvent(self, _e):
        self._objetivo = 1.0
        self._t.start()

    def leaveEvent(self, _e):
        self._objetivo = 0.0
        self._t.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0, 0, -1, -1)
        ruta = QPainterPath()
        ruta.addRoundedRect(r, 12, 12)
        grad = QLinearGradient(r.topLeft(), r.topRight())
        grad.setColorAt(0, QColor("#123A8C"))
        grad.setColorAt(0.55, QColor("#5B1E5E"))
        grad.setColorAt(1, QColor("#FF5C8A"))
        p.fillPath(ruta, grad)
        if self._encima > 0.01:
            p.fillPath(ruta, QColor(255, 255, 255, int(18 * self._encima)))
        p.save()
        p.setClipPath(ruta)
        p.setPen(Qt.NoPen)
        dx = 10 * self._encima
        for cx, cy, rad, a in ((r.right() - 80 - dx, 10, 70, 40), (r.right() - 20, 80, 46, 55),
                               (r.right() - 170 - dx * 2, 92, 34, 30)):
            p.setBrush(QColor(255, 255, 255, a))
            p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))
        p.restore()
        datos = self.r
        dy = (self.height() - 96) / 2
        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(fuente(11.5, QFont.Bold))
        p.drawText(QRectF(24, 16 + dy, r.width() - 48, 18), Qt.AlignLeft | Qt.AlignVCenter,
                   "TU RESUMEN")
        p.setPen(QColor("#FFFFFF"))
        f = fuente(24 if dy >= 0 else 20, QFont.Black, True)
        p.setFont(f)
        minutos = f"{datos['minutos']:,}".replace(",", ".")
        p.drawText(QRectF(24, 34 + dy, r.width() - 90, 32), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(
                       f"{minutos} {'minuto' if datos['minutos'] == 1 else 'minutos'} esta semana",
                       Qt.ElideRight, int(r.width() - 90)))
        top = datos["top_artistas"][0]["nombre"] if datos["top_artistas"] else ""
        p.setPen(QColor(255, 255, 255, 215))
        p.setFont(fuente(13))
        texto = (f"Tu artista: {top}  ·  " if top else "") + "Mira tu semana, tu mes o tu año"
        p.drawText(QRectF(24, 66 + dy, r.width() - 120, 20), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(fuente(13)).elidedText(texto, Qt.ElideRight, int(r.width() - 120)))
        lado = 22
        x = r.right() - 24 - lado + 4 * self._encima
        p.drawPixmap(int(x), int(r.center().y() - lado / 2),
                     iconos.pixmap("adelante", lado, "#FFFFFF"))
