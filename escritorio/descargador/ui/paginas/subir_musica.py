# -*- coding: utf-8 -*-
"""Subir mi música: audio + carátula (obligatoria) + título, artista y álbum (opcional),
casilla de derechos y barra de progreso. Debajo, mis canciones subidas.

    PaginaSubirMusica(ctx)
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QProgressBar, QVBoxLayout, QWidget)

from ... import social as S
from ...hilos import en_segundo_plano
from ..componentes import Pagina, Portada, SinResultados
from ..estilos import C
from . import perfil_comun as PC

TEXTO_DERECHOS = "Declaro que esta música es mía o tengo permiso para compartirla"


class PaginaSubirMusica(Pagina):
    progreso = Signal(float, str)

    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Subir música"
        self.social = S.social_de(ctx)
        self.ruta_audio = None
        self.ruta_portada = None
        self.subiendo = False
        self.progreso.connect(self._avance)
        col = PC.columna_central(self.cuerpo, 820)
        t = QLabel("Subir mi música")
        t.setObjectName("titulo_pagina")
        col.addWidget(t)
        col.addWidget(PC.etiqueta(
            "Comparte tus canciones con la comunidad de Caudal. Cada canción lleva su carátula y, si hace falta, el "
            "equipo la revisa antes de publicarla. "
            "Puedes subir hasta 30 en total y 10 por día; el audio pesa 15 MB como máximo.",
            f"color:{C['texto2']};"))
        if self.social is None:
            col.addWidget(SinResultados("compartir", "Subir música necesita tu cuenta",
                                        "Abre Caudal con internet e inicia sesión para compartir tu música."))
            self.cuerpo.addStretch(1)
            return
        col.addWidget(self._formulario())
        self.caja_mias = QVBoxLayout()
        self.caja_mias.setSpacing(8)
        col.addLayout(self.caja_mias)
        self.cuerpo.addStretch(1)
        self._cargar_mias()

    # ------------------------------------------------------------ formulario
    def _formulario(self):
        f, v = PC.tarjeta()
        v.setSpacing(12)
        h = QHBoxLayout()
        h.setSpacing(18)
        # carátula
        izq = QVBoxLayout()
        izq.setSpacing(8)
        self.vista_portada = Portada(150, radio=14)
        izq.addWidget(self.vista_portada)
        self.bt_portada = PC.boton("Elegir carátula…", "contorno", "carpeta", al_pulsar=self._elegir_portada)
        izq.addWidget(self.bt_portada)
        self.et_portada = PC.etiqueta("Obligatoria. Se recorta en cuadrado.", f"color:{C['texto3']};font-size:11px;")
        self.et_portada.setMaximumWidth(150)
        izq.addWidget(self.et_portada)
        izq.addStretch(1)
        h.addLayout(izq)
        # datos
        der = QVBoxLayout()
        der.setSpacing(6)
        fila = QHBoxLayout()
        self.bt_audio = PC.boton("Elegir canción…", "principal", "musica", al_pulsar=self._elegir_audio)
        fila.addWidget(self.bt_audio)
        fila.addStretch(1)
        der.addLayout(fila)
        self.et_audio = PC.etiqueta("Formatos: mp3, m4a, aac, flac, ogg, wav o webm.",
                                    f"color:{C['texto3']};font-size:11.5px;")
        der.addWidget(self.et_audio)
        self.titulo_c = self._campo(der, "Título *", "Cómo se llama la canción", 120)
        self.artista = self._campo(der, "Artista", "Quién la canta (opcional)", 120)
        self.album = self._campo(der, "Álbum", "Si es de un álbum, escribe su nombre para agruparlas (opcional)", 120)
        h.addLayout(der, 1)
        v.addLayout(h)
        self.chk = QCheckBox(TEXTO_DERECHOS)
        self.chk.toggled.connect(self._revisar)
        v.addWidget(self.chk)
        self.barra = QProgressBar()
        self.barra.setRange(0, 1000)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(8)
        self.barra.setStyleSheet(f"QProgressBar{{background:{C['superficie3']};border:none;border-radius:4px;}}"
                                 f"QProgressBar::chunk{{background:{C['acento']};border-radius:4px;}}")
        self.barra.hide()
        v.addWidget(self.barra)
        self.estado = PC.etiqueta("", f"color:{C['texto2']};font-size:12.5px;")
        v.addWidget(self.estado)
        fila2 = QHBoxLayout()
        fila2.addStretch(1)
        self.bt_subir = PC.boton("Subir canción", "principal", "compartir", al_pulsar=self._subir)
        self.bt_subir.setEnabled(False)
        fila2.addWidget(self.bt_subir)
        v.addLayout(fila2)
        self.titulo_c.textChanged.connect(self._revisar)
        return f

    def _campo(self, layout, rotulo, ayuda, tope):
        layout.addWidget(PC.etiqueta(rotulo, f"color:{C['texto2']};font-size:12px;font-weight:700;"))
        c = QLineEdit()
        c.setMaxLength(tope)
        c.setPlaceholderText(ayuda)
        layout.addWidget(c)
        return c

    # ------------------------------------------------------------ elegir archivos
    def _elegir_audio(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige tu canción", os.path.expanduser("~/Music"),
                                               S.FILTRO_AUDIO)
        if not ruta:
            return
        try:
            _ext, _tipo, tam = S.revisar_audio(ruta)
        except S.ErrorNube as e:
            self._decir(str(e), error=True)
            return
        self.ruta_audio = ruta
        d = S.leer_datos_audio(ruta)
        if not self.titulo_c.text().strip():
            self.titulo_c.setText(d["titulo"])
        if not self.artista.text().strip():
            self.artista.setText(d["artista"])
        if not self.album.text().strip():
            self.album.setText(d["album"])
        self.duracion = d["duracion"]
        self.et_audio.setText(f"{os.path.basename(ruta)}  ·  {tam / 1048576:.1f} MB"
                              + (f"  ·  {S.tiempo_corto(d['duracion'])}" if d["duracion"] else ""))
        self.et_audio.setStyleSheet(f"background:transparent;color:{C['exito']};font-size:11.5px;font-weight:700;")
        self._decir("")
        self._revisar()

    def _elegir_portada(self):
        ruta, _f = QFileDialog.getOpenFileName(self, "Elige la carátula", "", S.FILTRO_IMAGEN)
        if not ruta:
            return
        try:
            img = S.recortar_cuadrado(S._cargar_imagen(ruta), 300)
        except S.ErrorNube as e:
            self._decir(str(e), error=True)
            return
        from PySide6.QtGui import QPixmap
        from ..imagenes import formar
        self.ruta_portada = ruta
        self.vista_portada.pm = formar(img, 150, 150, "cuadrada", 14)
        self.vista_portada.url = "local"
        self.vista_portada.update()
        self.et_portada.setText(os.path.basename(ruta))
        _ = QPixmap
        self._decir("")
        self._revisar()

    def _revisar(self, *_):
        listo = bool(self.ruta_audio and self.ruta_portada and self.titulo_c.text().strip()
                     and self.chk.isChecked() and not self.subiendo)
        self.bt_subir.setEnabled(listo)
        if not self.subiendo and not self.estado.text():
            faltan = []
            if not self.ruta_audio:
                faltan.append("elegir la canción")
            if not self.ruta_portada:
                faltan.append("elegir la carátula")
            if self.ruta_audio and not self.titulo_c.text().strip():
                faltan.append("escribir el título")
            if not self.chk.isChecked():
                faltan.append("marcar la casilla de derechos")
            self.bt_subir.setToolTip("Falta " + ", ".join(faltan) if faltan else "")

    def _decir(self, texto, error=False):
        self.estado.setText(texto)
        self.estado.setStyleSheet(f"background:transparent;color:{C['error'] if error else C['texto2']};"
                                  "font-size:12.5px;")

    # ------------------------------------------------------------ subir
    def _subir(self):
        if self.subiendo:
            return
        self.subiendo = True
        self.bt_subir.setEnabled(False)
        for w in (self.bt_audio, self.bt_portada, self.chk):
            w.setEnabled(False)
        self.barra.setValue(0)
        self.barra.show()
        self._decir("Preparando…")
        datos = dict(ruta_audio=self.ruta_audio, ruta_portada=self.ruta_portada,
                     titulo=self.titulo_c.text(), artista=self.artista.text(), album=self.album.text(),
                     duracion=getattr(self, "duracion", 0))
        social = self.social
        senal = self.progreso

        def trabajo():
            nuevo = social.subir_cancion(avance=lambda f, t: senal.emit(f, t), **datos)
            return nuevo, social.publica_directo()
        en_segundo_plano(trabajo, ok=self._subida_lista, error=self._subida_fallo, dueno=self, urgente=True)

    def _avance(self, fraccion, texto):
        self.barra.setValue(int(fraccion * 1000))
        self._decir(f"{texto}  {int(fraccion * 100)} %")

    def _terminar(self):
        self.subiendo = False
        for w in (self.bt_audio, self.bt_portada, self.chk):
            w.setEnabled(True)
        self._revisar()

    def _subida_lista(self, resultado):
        _id, directo = resultado
        self._terminar()
        self.barra.hide()
        if directo:
            texto = "Listo: tu canción ya está en la comunidad."
            aviso = "Canción publicada"
        else:
            texto = ("Tu canción quedó en revisión. El equipo de Caudal la revisará y te avisaremos aquí "
                     "si se aprueba.")
            aviso = "Canción enviada a revisión"
        self._decir(texto)
        self.estado.setStyleSheet(f"background:transparent;color:{C['exito'] if directo else C['aviso']};"
                                  "font-size:13px;font-weight:700;")
        PC.aviso(self.ctx, aviso)
        self.ruta_audio = self.ruta_portada = None
        for c in (self.titulo_c, self.artista, self.album):
            c.clear()
        self.chk.setChecked(False)
        self.vista_portada.pm = None
        self.vista_portada.url = ""
        self.vista_portada.update()
        self.et_portada.setText("Obligatoria. Se recorta en cuadrado.")
        self.et_audio.setText("Formatos: mp3, m4a, aac, flac, ogg, wav o webm.")
        self.et_audio.setStyleSheet(f"background:transparent;color:{C['texto3']};font-size:11.5px;")
        self._cargar_mias()

    def _subida_fallo(self, e):
        self._terminar()
        self.barra.hide()
        self._decir(S.explicar(e, "subir la canción") + " No se guardó nada a medias.", error=True)

    # ------------------------------------------------------------ mis canciones
    def _cargar_mias(self):
        mio = ((getattr(self.ctx, "cuenta", None) or {}).get("usuario") or "")
        en_segundo_plano(self.social.ver_perfil, mio, ok=self._pintar_mias, error=lambda _e: None,
                         dueno=self, urgente=True)

    def _pintar_mias(self, p):
        PC.limpiar(self.caja_mias)
        subidas = (p or {}).get("subidas") or []
        self.caja_mias.addWidget(PC.titulo_seccion(f"Mis canciones ({len(subidas)} de 30)"))
        if not subidas:
            self.caja_mias.addWidget(PC.etiqueta("Aún no subiste ninguna. La primera aparecerá aquí.",
                                                 f"color:{C['texto2']};"))
            return
        publicas = [s for s in subidas if s["estado"] == "publicada"]
        for s in subidas:
            t = PC.TarjetaSubida(s, propia=True, mostrar_autor=False)
            t.reproducir.connect(lambda s=s: PC.reproducir_subidas(
                self.ctx, self.social, publicas, publicas.index(s) if s in publicas else 0, self)
                if s in publicas else PC.reproducir_subidas(self.ctx, self.social, [s], 0, self))
            t.borrar.connect(lambda s=s: PC.borrar_subida(self.ctx, self.social, s, self, self._cargar_mias))
            self.caja_mias.addWidget(t)
        if any(s["estado"] != "publicada" for s in subidas):
            self.caja_mias.addWidget(PC.etiqueta(
                "«En revisión»: el equipo de Caudal todavía no la aprobó (o la reportaron varias personas), "
                "así que aún no la ve la comunidad. Si la rechazan, aquí verás el motivo.",
                f"color:{C['texto3']};font-size:11.5px;"))
