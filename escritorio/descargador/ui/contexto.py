# -*- coding: utf-8 -*-
"""Lo que comparten todas las pantallas: reproducir, navegar, me gusta,
listas, descargar y los menus de clic derecho."""

import os
import subprocess
import webbrowser

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox

from .. import catalogo
from ..hilos import en_segundo_plano
from . import iconos
from .estilos import C

# (etiqueta, opciones) — None es un separador
PRESETS_DESCARGA = [
    ("Audio · MP3 320 kbps", {"tipo": "audio", "formato_audio": "mp3", "bitrate_mp3": "320"}),
    ("Audio · M4A / AAC (sin recomprimir)", {"tipo": "audio", "formato_audio": "m4a"}),
    ("Audio · OPUS original (la mejor de YouTube)", {"tipo": "audio", "formato_audio": "opus"}),
    ("Audio · FLAC", {"tipo": "audio", "formato_audio": "flac"}),
    ("Audio · WAV", {"tipo": "audio", "formato_audio": "wav"}),
    None,
    ("Video · Máxima calidad (hasta 8K, HDR)", {"tipo": "completo", "calidad": "mejor",
                                                 "codec_descarga": "maxima"}),
    ("Video · 4K (2160p)", {"tipo": "completo", "calidad": "2160", "codec_descarga": "maxima"}),
    ("Video · 1440p", {"tipo": "completo", "calidad": "1440", "codec_descarga": "maxima"}),
    ("Video · 1080p", {"tipo": "completo", "calidad": "1080", "codec_descarga": "maxima"}),
    ("Video · 1080p compatible con todo (H.264)", {"tipo": "completo", "calidad": "1080",
                                                    "codec_descarga": "compatible"}),
    ("Video · 720p", {"tipo": "completo", "calidad": "720", "codec_descarga": "maxima"}),
    ("Solo video, sin sonido (máxima)", {"tipo": "video", "calidad": "mejor",
                                         "codec_descarga": "maxima"}),
]


def url_de(pista):
    if pista.get("video_id"):
        if pista.get("es_video"):
            return f"https://www.youtube.com/watch?v={pista['video_id']}"
        return f"https://music.youtube.com/watch?v={pista['video_id']}"
    return pista.get("url") or ""


class Contexto(QObject):
    me_gusta_cambio = Signal(str, bool)
    listas_cambio = Signal()
    guardados_cambio = Signal()
    descargas_cambio = Signal()
    sonido_cambio = Signal()
    aviso = Signal(str)

    def __init__(self, ajustes, historial, coleccion, gestor, reproductor, padre=None):
        super().__init__(padre)
        self.ajustes = ajustes
        self.historial = historial
        self.coleccion = coleccion
        self.gestor = gestor
        self.reproductor = reproductor
        self.ventana = None

    # ------------------------------------------------------------ navegar

    def navegar(self, destino):
        if self.ventana:
            self.ventana.navegar(destino)

    def abrir_elemento(self, el):
        tipo = el.get("tipo")
        if tipo == "pista":
            self.reproducir_pista(el)
        elif tipo == "album":
            self.navegar({"pagina": "album", "id": el["id"]})
        elif tipo == "lista":
            self.navegar({"pagina": "lista", "id": el["id"]})
        elif tipo == "artista":
            self.navegar({"pagina": "artista", "id": el["id"]})
        elif tipo == "radio":
            self.reproductor.reproducir_radio_id(el["id"], el.get("titulo") or "Radio")
        elif tipo in ("genero", "pagina"):
            self.navegar({"pagina": "genero", "id": el["id"], "params": el.get("params"),
                          "titulo": el.get("titulo")})
        elif tipo == "mi_lista":
            self.navegar({"pagina": "mi_lista", "id": el["id"]})
        elif tipo == "me_gusta":
            self.navegar({"pagina": "me_gusta"})

    # ------------------------------------------------------------ reproducir

    def _modo_para(self, pista):
        if pista.get("archivo") and not pista.get("es_audio"):
            return "video"
        if pista.get("es_video") and not pista.get("archivo"):
            return "video"
        return "audio"

    def reproducir_lista(self, pistas, inicio=0, contexto=None, aleatorio=None):
        if not pistas:
            return
        inicio = max(0, min(inicio, len(pistas) - 1))
        modo = self._modo_para(pistas[inicio])
        self.reproductor.reproducir_lista(pistas, inicio, contexto, aleatorio, modo)
        if modo == "video" and self.ventana:
            self.ventana.mostrar_video()

    def reproducir_pista(self, pista, contexto=None):
        modo = self._modo_para(pista)
        self.reproductor.reproducir_pista(pista, contexto, modo)
        if modo == "video" and self.ventana:
            self.ventana.mostrar_video()

    def reproducir_elemento(self, el, aleatorio=None):
        """El boton de play de una tarjeta: hay que traer las canciones primero."""
        tipo = el.get("tipo")
        if tipo == "pista":
            self.reproducir_pista(el)
            return
        if tipo == "radio":
            self.reproductor.reproducir_radio_id(el["id"], el.get("titulo") or "Radio")
            return
        if tipo == "mi_lista":
            pistas = self.coleccion.pistas_de_lista(el["id"])
            self.reproducir_lista(pistas, 0, {"tipo": "mi_lista", "id": el["id"],
                                              "titulo": el.get("titulo") or el.get("nombre")},
                                  aleatorio)
            return
        if tipo == "me_gusta":
            self.reproducir_lista(self.coleccion.lista_me_gusta(), 0,
                                  {"tipo": "me_gusta", "id": "me_gusta", "titulo": "Tus me gusta"},
                                  aleatorio)
            return
        if tipo == "artista":
            def listo(datos):
                rid = datos.get("aleatorio_id") or datos.get("radio_id")
                if rid:
                    self.reproductor.reproducir_radio_id(rid, f"Radio de {datos.get('titulo', '')}")
                else:
                    canciones = [e for s in datos.get("secciones", []) for e in s["elementos"]
                                 if e.get("tipo") == "pista"]
                    self.reproducir_lista(canciones, 0, {"tipo": "artista", "id": el["id"],
                                                         "titulo": datos.get("titulo")})
            self.aviso.emit("Preparando…")
            en_segundo_plano(catalogo.artista, el["id"], ok=listo,
                             error=lambda e: self.aviso.emit(f"No se pudo: {e}"), dueno=self)
            return
        if tipo in ("album", "lista"):
            funcion = catalogo.album if tipo == "album" else catalogo.lista

            def listo(datos):
                pistas = datos.get("pistas") or []
                if not pistas:
                    self.aviso.emit("No tiene canciones disponibles.")
                    return
                self.reproducir_lista(pistas, 0, {"tipo": tipo, "id": el["id"],
                                                  "titulo": datos.get("titulo"),
                                                  "miniatura": datos.get("miniatura")},
                                      aleatorio)
            self.aviso.emit("Preparando…")
            en_segundo_plano(funcion, el["id"], ok=listo,
                             error=lambda e: self.aviso.emit(f"No se pudo abrir: {e}"), dueno=self)

    def pistas_de(self, el, al_tener):
        """Trae las canciones de un album / lista / mi lista y se las pasa a al_tener."""
        tipo = el.get("tipo")
        if tipo == "pista":
            al_tener([el])
        elif tipo == "mi_lista":
            al_tener(self.coleccion.pistas_de_lista(el["id"]))
        elif tipo == "me_gusta":
            al_tener(self.coleccion.lista_me_gusta())
        elif tipo in ("album", "lista"):
            funcion = catalogo.album if tipo == "album" else catalogo.lista
            en_segundo_plano(funcion, el["id"], ok=lambda d: al_tener(d.get("pistas") or []),
                             error=lambda e: self.aviso.emit(f"No se pudo: {e}"), dueno=self)
        elif tipo == "radio":
            en_segundo_plano(catalogo.radio, None, el["id"],
                             ok=lambda d: al_tener(d.get("pistas") or []),
                             error=lambda e: self.aviso.emit(f"No se pudo: {e}"), dueno=self)

    # ------------------------------------------------------------ me gusta y listas

    def avisar(self, texto, deshacer=None):
        """Aviso abajo; con `deshacer`, lleva el boton para revertir."""
        if self.ventana is not None:
            self.ventana.aviso.mostrar(texto, 3200, "Deshacer" if deshacer else None, deshacer)
        else:
            self.aviso.emit(texto)

    def alternar_me_gusta(self, pista, avisar=True):
        ahora = self.coleccion.alternar_me_gusta(pista)
        self.me_gusta_cambio.emit(pista.get("clave") or "", ahora)
        if avisar:
            if ahora:
                self.avisar("Añadida a Tus me gusta")
            else:
                self.avisar("Quitada de Tus me gusta",
                            lambda: self.alternar_me_gusta(pista, avisar=False))
        return ahora

    def quitar_de_lista(self, lista_id, pista):
        claves = [p["clave"] for p in self.coleccion.pistas_de_lista(lista_id)]
        posicion = claves.index(pista["clave"]) if pista.get("clave") in claves else None
        self.coleccion.quitar_de_lista(lista_id, pista["clave"])
        self.listas_cambio.emit()

        def deshacer():
            self.coleccion.agregar_a_lista(lista_id, [pista])
            if posicion is not None:
                orden = [c for c in claves]
                self.coleccion.mover_en_lista(lista_id, orden)
            self.listas_cambio.emit()
        self.avisar("Quitada de la lista", deshacer)

    def anadir_a_lista(self, pistas, lista_id=None):
        if isinstance(pistas, dict):
            pistas = [pistas]
        if lista_id is None:
            nombre, ok = QInputDialog.getText(self.ventana, "Nueva lista", "Nombre de la lista:",
                                              text=self.coleccion.nombre_libre())
            if not ok or not nombre.strip():
                return
            try:
                lista_id = self.coleccion.crear_lista(nombre)
            except ValueError as e:
                QMessageBox.warning(self.ventana, "Caudal", str(e))
                return
        nuevas = self.coleccion.agregar_a_lista(lista_id, pistas)
        lista = self.coleccion.lista(lista_id) or {}
        self.listas_cambio.emit()
        if nuevas == 0:
            self.aviso.emit(f"Ya estaba en «{lista.get('nombre', '')}»")
        else:
            self.aviso.emit(f"Añadido a «{lista.get('nombre', '')}»")

    def importar_de_pc(self):
        """Traer canciones que ya tienes en la PC: quedan en «En tu disco» y,
        si quieres, en una lista nueva o en una de las tuyas."""
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from ..coleccion import pista_de_descarga
        rutas, _f = QFileDialog.getOpenFileNames(
            self.ventana, "Elige tus canciones", str(Path.home() / "Music"),
            "Audio (*.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus *.wma *.webm *.aiff);;Todos (*.*)")
        if not rutas:
            return
        pistas = []
        for ruta in rutas:
            titulo, artista, duracion = Path(ruta).stem, "", 0
            try:
                import mutagen
                m = mutagen.File(ruta, easy=True)
                if m is not None:
                    titulo = (m.get("title") or [titulo])[0] or titulo
                    artista = (m.get("artist") or m.get("albumartist") or [""])[0]
                    duracion = int(getattr(m.info, "length", 0) or 0)
            except Exception:  # noqa: BLE001
                pass
            if not artista and " - " in titulo:
                artista, titulo = [x.strip() for x in titulo.split(" - ", 1)]
            ya = self.historial.con.execute(
                "SELECT * FROM descargas WHERE archivo = ? AND estado = 'completada'", (ruta,)).fetchone()
            if ya is None:
                ident = self.historial.agregar(Path(ruta).as_uri(), titulo, "En tu PC", ruta,
                                               tamano=os.path.getsize(ruta), duracion=duracion,
                                               calidad=Path(ruta).suffix.lstrip(".").upper(),
                                               es_audio=True, autor=artista)
                ya = self.historial.con.execute("SELECT * FROM descargas WHERE id = ?", (ident,)).fetchone()
            pistas.append(pista_de_descarga(dict(ya)))
        self.coleccion.invalidar_indice()
        self.descargas_cambio.emit()
        caja = QMessageBox(self.ventana)
        caja.setWindowTitle("Caudal")
        caja.setText(f"{len(pistas)} {'canción importada' if len(pistas) == 1 else 'canciones importadas'}. "
                     "Ya están en «En tu disco». ¿Dónde más las pones?")
        nueva = caja.addButton("En una lista nueva solo con ellas", QMessageBox.AcceptRole)
        existente = caja.addButton("En una de mis listas", QMessageBox.ActionRole)
        caja.addButton("Así está bien", QMessageBox.RejectRole)
        caja.exec()
        if caja.clickedButton() is nueva:
            self.anadir_a_lista(pistas, None)
        elif caja.clickedButton() is existente:
            listas = self.coleccion.listas()
            if not listas:
                self.anadir_a_lista(pistas, None)
                return
            nombres = [l["nombre"] for l in listas]
            elegida, ok = QInputDialog.getItem(self.ventana, "Caudal", "¿En qué lista?", nombres, 0, False)
            if ok:
                self.anadir_a_lista(pistas, listas[nombres.index(elegida)]["id"])

    def crear_lista(self):
        nombre = self.coleccion.nombre_libre()
        try:
            lista_id = self.coleccion.crear_lista(nombre)
        except ValueError as e:
            QMessageBox.warning(self.ventana, "Caudal", str(e))
            return
        self.listas_cambio.emit()
        self.navegar({"pagina": "mi_lista", "id": lista_id})

    def alternar_guardado(self, el):
        if self.coleccion.guardado(el["tipo"], el["id"]):
            self.coleccion.olvidar(el["tipo"], el["id"])
            self.aviso.emit("Quitado de tu biblioteca")
        else:
            self.coleccion.guardar(el)
            self.aviso.emit("Guardado en tu biblioteca")
        self.guardados_cambio.emit()

    # ------------------------------------------------------------ descargar

    def descargar(self, pistas, opciones):
        if isinstance(pistas, dict):
            pistas = [pistas]
        opciones = dict(opciones or {})
        tipo = opciones.pop("tipo", None)
        calidad = opciones.pop("calidad", None)
        n = 0
        for p in pistas:
            url = url_de(p)
            if not url:
                continue
            meta = {"titulo": p.get("titulo"), "artista": p.get("artista"),
                    "duracion": p.get("duracion"),
                    "miniatura": p.get("miniatura") if "://" in (p.get("miniatura") or "") else ""}
            self.gestor.agregar(url, tipo=tipo or "audio", calidad=calidad, opciones=opciones,
                                meta=meta)
            n += 1
        if n:
            self.aviso.emit("Descargando…" if n == 1 else f"{n} descargas en la cola")

    def dialogo_descarga(self, pistas):
        from .dialogo_descarga import DialogoDescarga
        if isinstance(pistas, dict):
            pistas = [pistas]
        d = DialogoDescarga(self.ajustes, pistas, self.ventana)
        if d.exec():
            self.descargar(pistas, d.opciones())

    def menu_descargar(self, padre_menu, pistas_o_funcion):
        """Submenu 'Descargar' con los formatos. Acepta pistas o una funcion
        que las traiga (para albumes y listas que hay que pedir)."""
        sub = padre_menu.addMenu(iconos.icono("descargar", 16, C["texto2"]), "Descargar")

        def hacer(opciones):
            if callable(pistas_o_funcion):
                pistas_o_funcion(lambda ps: self.descargar(ps, opciones))
            else:
                self.descargar(pistas_o_funcion, opciones)

        def mas():
            if callable(pistas_o_funcion):
                pistas_o_funcion(self.dialogo_descarga)
            else:
                self.dialogo_descarga(pistas_o_funcion)

        for item in PRESETS_DESCARGA:
            if item is None:
                sub.addSeparator()
                continue
            etiqueta, opciones = item
            sub.addAction(etiqueta, lambda o=opciones: hacer(dict(o)))
        sub.addSeparator()
        sub.addAction("Más opciones y formatos exactos…", mas)
        return sub

    # ------------------------------------------------------------ menus

    def _submenu_listas(self, menu, pistas):
        sub = menu.addMenu(iconos.icono("anadir_lista", 16, C["texto2"]), "Añadir a una lista")
        sub.addAction(iconos.icono("mas", 16, C["texto2"]), "Nueva lista…",
                      lambda: self.anadir_a_lista(pistas, None))
        listas = self.coleccion.listas()
        if listas:
            sub.addSeparator()
        for l in listas[:40]:
            sub.addAction(l["nombre"], lambda i=l["id"]: self.anadir_a_lista(pistas, i))
        return sub

    def abrir_similares(self, pista):
        from .. import recomendador as rc
        from ..hilos import en_segundo_plano
        self.aviso.emit("Buscando canciones similares…")
        en_segundo_plano(rc.similares, self.coleccion, pista,
                         ok=lambda m: self.navegar({"pagina": "mix", "id": m["id"], "el": m})
                         if m.get("pistas") else self.aviso.emit("No se encontraron canciones parecidas."),
                         error=lambda _e: self.aviso.emit("No se pudo conectar. Revisa tu internet."),
                         dueno=self)

    def enviar_a_chat(self, pista):
        from .paginas.mensajes import enviar_pista_a_chat
        enviar_pista_a_chat(self, pista)

    def menu_pista(self, pista, pos, extra=None):
        menu = QMenu(self.ventana)
        r = self.reproductor
        menu.addAction(iconos.icono("reproducir", 16, C["texto2"]), "Reproducir",
                       lambda: self.reproducir_pista(pista))
        menu.addAction(iconos.icono("cola", 16, C["texto2"]), "Reproducir a continuación",
                       lambda: r.reproducir_despues(pista))
        menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir a la cola",
                       lambda: r.agregar_a_cola(pista))
        if pista.get("video_id"):
            menu.addAction(iconos.icono("radio", 16, C["texto2"]), "Iniciar radio de la canción",
                           lambda: r.iniciar_radio(pista))
            menu.addAction(iconos.icono("estrella", 16, C["texto2"]), "Canciones similares",
                           lambda: self.abrir_similares(pista))
            menu.addAction(iconos.icono("compartir", 16, C["texto2"]), "Enviar en un chat…",
                           lambda: self.enviar_a_chat(pista))
            if not pista.get("es_video") or pista.get("archivo"):
                menu.addAction(iconos.icono("video", 16, C["texto2"]), "Ver el video",
                               lambda: self.ver_video(pista))
            else:
                menu.addAction(iconos.icono("musica", 16, C["texto2"]), "Escuchar solo el audio",
                               lambda: self.reproductor.reproducir_pista(pista, modo="audio"))
        menu.addSeparator()
        gusta = self.coleccion.me_gusta(pista.get("clave"))
        menu.addAction(iconos.icono("corazon_lleno" if gusta else "corazon", 16,
                                    C["acento"] if gusta else C["texto2"]),
                       "Quitar de Tus me gusta" if gusta else "Guardar en Tus me gusta",
                       lambda: self.alternar_me_gusta(pista))
        self._submenu_listas(menu, [pista])
        if pista.get("video_id") or pista.get("url"):
            self.menu_descargar(menu, [pista])
        menu.addSeparator()
        artistas = [a for a in pista.get("artistas") or [] if a.get("id")]
        if len(artistas) == 1:
            menu.addAction(iconos.icono("usuario", 16, C["texto2"]), "Ir al artista",
                           lambda: self.navegar({"pagina": "artista", "id": artistas[0]["id"]}))
        elif artistas:
            sub = menu.addMenu(iconos.icono("usuario", 16, C["texto2"]), "Ir al artista")
            for a in artistas:
                sub.addAction(a["nombre"], lambda i=a["id"]: self.navegar({"pagina": "artista",
                                                                          "id": i}))
        alb = pista.get("album") or {}
        if alb.get("id"):
            menu.addAction(iconos.icono("album", 16, C["texto2"]), "Ir al álbum",
                           lambda: self.navegar({"pagina": "album", "id": alb["id"]}))
        menu.addSeparator()
        url = url_de(pista)
        if url:
            menu.addAction(iconos.icono("enlace", 16, C["texto2"]), "Copiar enlace",
                           lambda: (QGuiApplication.clipboard().setText(url),
                                    self.aviso.emit("Enlace copiado")))
            menu.addAction(iconos.icono("abrir", 16, C["texto2"]), "Abrir en YouTube",
                           lambda: webbrowser.open(url))
        archivo = pista.get("archivo") or ""
        if not archivo and pista.get("video_id"):
            copia = self.coleccion.copia_local(pista["video_id"])
            archivo = copia[0] if copia else ""
        if archivo and os.path.exists(archivo):
            menu.addAction(iconos.icono("carpeta", 16, C["texto2"]), "Mostrar en la carpeta",
                           lambda: subprocess.Popen(["explorer", "/select,",
                                                     os.path.normpath(archivo)]))
            if pista.get("archivo") and pista.get("es_video") is not None \
                    and not pista.get("es_audio"):
                menu.addAction(iconos.icono("musica", 16, C["texto2"]), "Extraer el audio a MP3",
                               lambda: self.extraer_audio(pista))
            if pista.get("descarga_id"):
                menu.addAction(iconos.icono("papelera", 16, C["texto2"]), "Borrar del disco…",
                               lambda: self.borrar_del_disco(pista))
        if extra:
            menu.addSeparator()
            extra(menu)
        menu.exec(pos)

    def menu_elemento(self, el, pos):
        tipo = el.get("tipo")
        if tipo == "pista":
            self.menu_pista(el, pos)
            return
        if tipo == "genero":
            return
        menu = QMenu(self.ventana)
        menu.addAction(iconos.icono("reproducir", 16, C["texto2"]), "Reproducir",
                       lambda: self.reproducir_elemento(el))
        if tipo in ("album", "lista", "mi_lista", "me_gusta"):
            menu.addAction(iconos.icono("aleatorio", 16, C["texto2"]), "Reproducir en aleatorio",
                           lambda: self.reproducir_elemento(el, aleatorio=True))
            menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir a la cola",
                           lambda: self.pistas_de(el, self.reproductor.agregar_a_cola))
            menu.addSeparator()
            if tipo in ("album", "lista"):
                guardado = self.coleccion.guardado(tipo, el["id"])
                menu.addAction(iconos.icono("mas_circulo" if not guardado else "check_circulo", 16,
                                            C["acento"] if guardado else C["texto2"]),
                               "Quitar de tu biblioteca" if guardado else "Guardar en tu biblioteca",
                               lambda: self.alternar_guardado(el))
            sub = menu.addMenu(iconos.icono("anadir_lista", 16, C["texto2"]), "Añadir a una lista")
            sub.addAction("Nueva lista…", lambda: self.pistas_de(
                el, lambda ps: self.anadir_a_lista(ps, None)))
            for l in self.coleccion.listas()[:40]:
                if tipo == "mi_lista" and l["id"] == el["id"]:
                    continue
                sub.addAction(l["nombre"], lambda i=l["id"]: self.pistas_de(
                    el, lambda ps, i=i: self.anadir_a_lista(ps, i)))
            if tipo == "mi_lista":
                from . import dialogo_portada
                dialogo_portada.agregar_al_menu(menu, self, el["id"], self.ventana)
            self.menu_descargar(menu, lambda cb: self.pistas_de(el, cb))
        elif tipo == "artista":
            menu.addAction(iconos.icono("radio", 16, C["texto2"]), "Radio del artista",
                           lambda: self.reproducir_elemento(el))
            seguido = self.coleccion.guardado("artista", el["id"])
            menu.addAction("Dejar de seguir" if seguido else "Seguir",
                           lambda: self.alternar_guardado(el))
        elif tipo == "radio":
            menu.addAction(iconos.icono("lista", 16, C["texto2"]), "Añadir a la cola",
                           lambda: self.pistas_de(el, self.reproductor.agregar_a_cola))
        if tipo in ("album", "lista", "artista"):
            menu.addSeparator()
            enlaces = {"album": "https://music.youtube.com/browse/",
                       "artista": "https://music.youtube.com/channel/",
                       "lista": "https://music.youtube.com/playlist?list="}
            url = enlaces[tipo] + el["id"]
            menu.addAction(iconos.icono("enlace", 16, C["texto2"]), "Copiar enlace",
                           lambda: (QGuiApplication.clipboard().setText(url),
                                    self.aviso.emit("Enlace copiado")))
        menu.exec(pos)

    # ------------------------------------------------------------ varios

    def ver_video(self, pista):
        if self.reproductor.actual is pista or (
                self.reproductor.actual and pista.get("video_id")
                and self.reproductor.actual.get("video_id") == pista.get("video_id")):
            self.reproductor.cambiar_modo("video")
        else:
            self.reproductor.reproducir_pista(pista, modo="video")
        if self.ventana:
            self.ventana.mostrar_video()

    def extraer_audio(self, pista):
        from ..conversion import ErrorConversion, duracion, extraer_audio

        def hacer():
            return extraer_audio(pista["archivo"], formato=self.ajustes["formato_audio"]
                                 if self.ajustes["formato_audio"] != "original" else "mp3",
                                 reforzar=bool(self.ajustes["modo_musica"]))

        def listo(destino):
            self.historial.agregar(
                pista.get("url", ""), pista.get("titulo", ""), pista.get("plataforma", ""),
                destino, os.path.getsize(destino), duracion(destino),
                os.path.splitext(destino)[1].lstrip(".").upper(),
                caratula=pista.get("miniatura", ""), es_audio=True, autor=pista.get("artista", ""))
            self.coleccion.invalidar_indice()
            self.descargas_cambio.emit()
            self.aviso.emit("Audio extraído y guardado en tu música")

        def fallo(e):
            texto = str(e) if isinstance(e, ErrorConversion) else f"No se pudo extraer: {e}"
            QMessageBox.warning(self.ventana, "Caudal", texto)

        self.aviso.emit("Extrayendo el audio…")
        en_segundo_plano(hacer, ok=listo, error=fallo, dueno=self)

    def borrar_del_disco(self, pista):
        r = QMessageBox.question(self.ventana, "Caudal",
                                 f"Se borrará del disco:\n\n{pista.get('titulo', '')}\n\n"
                                 "No se puede deshacer.")
        if r != QMessageBox.Yes:
            return
        archivo = pista.get("archivo") or ""
        actual = self.reproductor.actual
        if actual and actual.get("archivo") == archivo:
            self.reproductor.detener()
        if archivo and os.path.exists(archivo):
            try:
                os.remove(archivo)
            except OSError:
                QMessageBox.warning(self.ventana, "Caudal",
                                    "No se pudo borrar: puede estar abierto en otro programa.")
                return
        self.historial.borrar(pista.get("descarga_id"))
        self.coleccion.invalidar_indice()
        self.descargas_cambio.emit()
        self.aviso.emit("Borrado del disco")
