# -*- coding: utf-8 -*-
"""Opciones completas de una descarga, con la lista de formatos exactos."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox, QDialog,
                               QDialogButtonBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .. import catalogo
from ..hilos import en_segundo_plano
from ..motor import formato_bytes
from .contexto import url_de
from .estilos import C

CALIDADES = [
    ("Máxima (hasta 8K)", "mejor"), ("8K · 4320p", "4320"), ("4K · 2160p", "2160"),
    ("2K · 1440p", "1440"), ("Full HD · 1080p", "1080"), ("HD · 720p", "720"),
    ("480p", "480"), ("360p", "360"),
]
CODECS = [("Máxima calidad (AV1 / VP9, HDR)", "maxima"),
          ("Compatible con todo (H.264, hasta 1080p)", "compatible")]
CONTENEDORES = [("MP4", "mp4"), ("MKV", "mkv"), ("WEBM", "webm")]
AUDIOS = [("MP3", "mp3"), ("M4A / AAC (sin recomprimir)", "m4a"),
          ("OPUS (original de YouTube)", "opus"), ("FLAC", "flac"), ("WAV", "wav"),
          ("Original, tal cual llega", "original")]
BITRATES = [("320 kbps", "320"), ("256 kbps", "256"), ("192 kbps", "192"), ("128 kbps", "128"),
            ("VBR máxima (V0)", "V0")]


def _combo(opciones, valor):
    c = QComboBox()
    for etiqueta, v in opciones:
        c.addItem(etiqueta, v)
    i = c.findData(valor)
    c.setCurrentIndex(i if i >= 0 else 0)
    return c


class DialogoDescarga(QDialog):
    def __init__(self, ajustes, pistas=None, padre=None, url=""):
        super().__init__(padre)
        self.ajustes = ajustes
        self.pistas = pistas or []
        self.url = url or (url_de(self.pistas[0]) if len(self.pistas) == 1 else "")
        self.formato_exacto = ""
        self.setWindowTitle("Opciones de descarga")
        self.setMinimumWidth(620)

        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        titulo = QLabel("Descargar")
        titulo.setObjectName("titulo_seccion")
        v.addWidget(titulo)
        if len(self.pistas) == 1:
            sub = QLabel(f"{self.pistas[0].get('titulo', '')}  ·  {self.pistas[0].get('artista', '')}")
        elif self.pistas:
            sub = QLabel(f"{len(self.pistas)} elementos")
        else:
            sub = QLabel(self.url)
        sub.setObjectName("secundario")
        sub.setWordWrap(True)
        v.addWidget(sub)

        # que se baja
        fila_tipo = QHBoxLayout()
        self.grupo = QButtonGroup(self)
        for i, (texto, valor) in enumerate((("Video con sonido", "completo"),
                                            ("Solo audio", "audio"),
                                            ("Solo video", "video"))):
            b = QPushButton(texto)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("valor", valor)
            self.grupo.addButton(b, i)
            fila_tipo.addWidget(b)
        fila_tipo.addStretch(1)
        v.addLayout(fila_tipo)
        tipo_inicial = ajustes["tipo_descarga"]
        for b in self.grupo.buttons():
            b.setChecked(b.property("valor") == tipo_inicial)
        self.grupo.buttonClicked.connect(lambda _b: self._refrescar())

        rej = QGridLayout()
        rej.setHorizontalSpacing(14)
        rej.setVerticalSpacing(10)
        rej.setColumnStretch(1, 1)
        self.c_calidad = _combo(CALIDADES, ajustes["calidad"])
        self.c_codec = _combo(CODECS, ajustes["codec_descarga"])
        self.c_contenedor = _combo(CONTENEDORES, ajustes["formato_salida"])
        self.c_audio = _combo(AUDIOS, ajustes["formato_audio"])
        self.c_bitrate = _combo(BITRATES, ajustes["bitrate_mp3"])
        self.e_subcarpeta = QLineEdit()
        self.e_subcarpeta.setPlaceholderText("Opcional: guardar dentro de una subcarpeta")
        filas = [("Calidad de imagen", self.c_calidad), ("Códec", self.c_codec),
                 ("Contenedor", self.c_contenedor), ("Formato de audio", self.c_audio),
                 ("Calidad del MP3", self.c_bitrate), ("Subcarpeta", self.e_subcarpeta)]
        self.etiquetas = {}
        for i, (texto, w) in enumerate(filas):
            et = QLabel(texto)
            et.setObjectName("secundario")
            self.etiquetas[w] = et
            rej.addWidget(et, i, 0)
            rej.addWidget(w, i, 1)
        v.addLayout(rej)
        self.c_audio.currentIndexChanged.connect(self._refrescar)

        self.nota = QLabel("")
        self.nota.setObjectName("ayuda")
        self.nota.setWordWrap(True)
        v.addWidget(self.nota)

        # formatos exactos
        self.bt_formatos = QPushButton("Ver todos los formatos de este enlace")
        self.bt_formatos.setCursor(Qt.PointingHandCursor)
        self.bt_formatos.clicked.connect(self._cargar_formatos)
        self.bt_formatos.setVisible(bool(self.url))
        v.addWidget(self.bt_formatos, 0, Qt.AlignLeft)
        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(["ID", "Tipo", "Resolución", "Códec", "Bitrate",
                                              "Tamaño", "Notas"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setShowGrid(False)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setMinimumHeight(240)
        self.tabla.hide()
        self.tabla.itemSelectionChanged.connect(self._elegir_formato)
        v.addWidget(self.tabla, 1)

        botones = QDialogButtonBox()
        ok = botones.addButton("Descargar", QDialogButtonBox.AcceptRole)
        ok.setObjectName("principal")
        botones.addButton("Cancelar", QDialogButtonBox.RejectRole)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        v.addWidget(botones)
        self._refrescar()

    def _tipo(self):
        b = self.grupo.checkedButton()
        return b.property("valor") if b else "completo"

    def _refrescar(self):
        tipo = self._tipo()
        audio = tipo == "audio"
        for w in (self.c_calidad, self.c_codec, self.c_contenedor):
            w.setVisible(not audio)
            self.etiquetas[w].setVisible(not audio)
        self.c_audio.setVisible(audio)
        self.etiquetas[self.c_audio].setVisible(audio)
        mp3 = audio and self.c_audio.currentData() == "mp3"
        self.c_bitrate.setVisible(mp3)
        self.etiquetas[self.c_bitrate].setVisible(mp3)
        if audio:
            notas = {
                "mp3": "MP3 lo abre todo. A 320 kbps no se nota la diferencia con el original.",
                "m4a": "Se guarda el AAC que sirve YouTube sin volver a comprimirlo.",
                "opus": "El Opus original de YouTube (~160 kbps): la mejor calidad posible.",
                "flac": "Contenedor sin pérdida. Ojo: la fuente de YouTube ya viene comprimida.",
                "wav": "Sin compresión: archivos grandes, máxima compatibilidad para editar.",
                "original": "El archivo de audio exactamente como llega, sin convertir.",
            }
            self.nota.setText(notas.get(self.c_audio.currentData(), ""))
        else:
            self.nota.setText("«Máxima calidad» baja la mejor imagen que exista (AV1/VP9, hasta "
                              "8K y HDR). Para pasarlo a un televisor o móvil antiguo, elige "
                              "«Compatible con todo».")

    def _cargar_formatos(self):
        self.bt_formatos.setEnabled(False)
        self.bt_formatos.setText("Consultando formatos…")
        en_segundo_plano(catalogo.formatos_disponibles, self.url, self.ajustes,
                         ok=self._pintar_formatos, error=self._fallo_formatos, dueno=self)

    def _fallo_formatos(self, e):
        self.bt_formatos.setEnabled(True)
        self.bt_formatos.setText(f"No se pudo consultar ({str(e)[:80]}). Reintentar")

    def _pintar_formatos(self, datos):
        self.bt_formatos.setText("Elige un formato concreto (o deja la selección automática)")
        formatos = sorted(datos.get("formatos") or [],
                          key=lambda f: (bool(f["vcodec"]), f["alto"], f["tbr"]), reverse=True)
        self.tabla.setRowCount(len(formatos))
        for i, f in enumerate(formatos):
            if f["vcodec"] and f["acodec"]:
                tipo = "Video+audio"
            elif f["vcodec"]:
                tipo = "Video"
            else:
                tipo = "Audio"
            res = f"{f['alto']}p{int(f['fps']) if f['fps'] and f['fps'] > 30 else ''}" if f["alto"] else ""
            codec = " + ".join(x.split(".")[0] for x in (f["vcodec"], f["acodec"]) if x)
            bitrate = f"{f['abr']} kbps" if f["abr"] and not f["vcodec"] else (
                f"{f['tbr']} kbps" if f["tbr"] else "")
            notas = " ".join(x for x in ("HDR" if f["hdr"] else "", f["nota"], f["idioma"]) if x)
            valores = [f["id"], tipo, res, codec, bitrate,
                       formato_bytes(f["tamano"]) if f["tamano"] else "", notas]
            for j, val in enumerate(valores):
                celda = QTableWidgetItem(str(val))
                if j == 0:
                    celda.setData(Qt.UserRole, (f["id"], tipo))
                self.tabla.setItem(i, j, celda)
        self.tabla.show()
        self.adjustSize()

    def _elegir_formato(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            self.formato_exacto = ""
            return
        ident, tipo = self.tabla.item(fila, 0).data(Qt.UserRole)
        self.formato_exacto = ident
        # elegir un formato de solo audio pasa el tipo a audio, etc.
        destino = {"Audio": "audio", "Video": "completo", "Video+audio": "completo"}[tipo]
        for b in self.grupo.buttons():
            if b.property("valor") == destino and self._tipo() != "video":
                b.setChecked(True)
        self._refrescar()
        self.nota.setText(f"Formato elegido: {ident}"
                          + ("  (se le unirá el mejor sonido)" if tipo == "Video" else ""))

    def opciones(self):
        tipo = self._tipo()
        o = {"tipo": tipo}
        if tipo == "audio":
            o["formato_audio"] = self.c_audio.currentData()
            o["bitrate_mp3"] = self.c_bitrate.currentData()
        else:
            o["calidad"] = self.c_calidad.currentData()
            o["codec_descarga"] = self.c_codec.currentData()
            o["formato_salida"] = self.c_contenedor.currentData()
        if self.formato_exacto:
            o["formato_exacto"] = self.formato_exacto
        if self.e_subcarpeta.text().strip():
            o["subcarpeta"] = self.e_subcarpeta.text().strip()
        return o


def _ignorar(_w: QWidget):  # pragma: no cover
    return C
