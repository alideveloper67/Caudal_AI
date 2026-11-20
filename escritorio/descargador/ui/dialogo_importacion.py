# -*- coding: utf-8 -*-
"""Buscar en YouTube Music las canciones traídas de otra app, con progreso a la vista.

Sirve para guardar una lista nueva o para pasar canciones a «Me gusta». Va de
lote en lote en otro hilo (la ventana no se congela), guarda lo encontrado
después de cada lote y apunta por dónde va: si se cierra Caudal o se pausa,
la próxima vez se sigue desde ahí.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar,
                               QPushButton, QVBoxLayout)

from .. import catalogo, importacion
from .estilos import C


def buscar_pista(cancion):
    """La pista de YouTube Music para una canción traída (con sus reintentos)."""
    vid = catalogo.video_id_de(cancion.get("url") or "")
    if vid:
        return catalogo.nueva_pista(vid, cancion.get("titulo") or "",
                                    [{"nombre": cancion.get("artista") or "", "id": ""}],
                                    duracion=cancion.get("duracion") or 0,
                                    miniatura=cancion.get("miniatura") or "")
    return importacion.resolver_una(cancion, lambda q: catalogo.buscar(q, "canciones", 3))


class _Trabajo(QThread):
    avance = Signal(int, int)
    lote = Signal(int, list, list)
    termino = Signal(dict)

    def __init__(self, canciones, desde):
        super().__init__()
        self.canciones = canciones
        self.desde = desde
        self.parar = False

    def run(self):
        try:
            r = importacion.emparejar(
                self.canciones, buscar_pista, desde=self.desde,
                al_avanzar=lambda h, t: self.avance.emit(h, t),
                al_lote=lambda fin, p, s: self.lote.emit(fin, p, s),
                cancelado=lambda: self.parar)
        except Exception as e:  # noqa: BLE001
            r = {"cancelado": True, "error": str(e)[:120]}
        self.termino.emit(r)


def pendiente(col):
    """La importación que quedó a medias, o None."""
    p = col.estado(importacion.CLAVE_PENDIENTE)
    if not isinstance(p, dict) or not p.get("canciones"):
        return None
    if p.get("hechas", 0) >= len(p["canciones"]):
        return None
    return p


def nueva(col, canciones, destino):
    """Prepara una importación y la deja apuntada. `destino`:
    {'tipo': 'lista', 'nombre', 'plataforma'} o {'tipo': 'me_gusta', 'servicio', 'enlace', 'titulo'}."""
    trabajo = {"destino": dict(destino), "canciones": canciones, "hechas": 0,
               "encontradas": 0, "anadidas": 0, "repetidas": 0, "no_encontradas": []}
    if destino.get("tipo") == "lista":
        nombre = (destino.get("nombre") or "Lista traída").strip()[:80]
        if any(l["nombre"] == nombre for l in col.listas()):
            nombre = col.nombre_libre(nombre)
        trabajo["destino"]["nombre"] = nombre
        trabajo["destino"]["lista_id"] = col.crear_lista(
            nombre, f"Traída de {destino.get('plataforma') or 'otra app'}")
    col.guardar_estado(importacion.CLAVE_PENDIENTE, trabajo)
    return trabajo


class DialogoImportacion(QDialog):
    """Se puede esconder («Seguir en segundo plano») y la búsqueda continúa."""

    terminado = Signal(dict)

    def __init__(self, ctx, trabajo, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.col = ctx.coleccion
        self.trabajo = trabajo
        self.hilo = None
        destino = trabajo["destino"]
        self.es_me_gusta = destino.get("tipo") == "me_gusta"

        self.setWindowTitle("Buscando canciones")
        self.setMinimumWidth(520)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 20, 22, 18)
        raiz.setSpacing(12)

        destino_txt = ("tus Me gusta" if self.es_me_gusta
                       else f"la lista «{destino.get('nombre', '')}»")
        self.titulo = QLabel(f"Pasando canciones a {destino_txt}")
        self.titulo.setStyleSheet("font-size:17px;font-weight:700;")
        self.titulo.setWordWrap(True)
        raiz.addWidget(self.titulo)

        ayuda = QLabel("Caudal busca cada canción en YouTube Music. Lo encontrado se guarda "
                       "por tandas: si cierras Caudal, la próxima vez sigue desde aquí.")
        ayuda.setObjectName("ayuda")
        ayuda.setWordWrap(True)
        raiz.addWidget(ayuda)

        self.barra = QProgressBar()
        self.barra.setRange(0, max(1, len(trabajo["canciones"])))
        self.barra.setValue(trabajo.get("hechas", 0))
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(8)
        raiz.addWidget(self.barra)

        self.cuenta = QLabel("")
        self.cuenta.setStyleSheet("font-weight:600;")
        raiz.addWidget(self.cuenta)

        self.faltan = QPlainTextEdit()
        self.faltan.setReadOnly(True)
        self.faltan.setMaximumHeight(140)
        self.faltan.hide()
        raiz.addWidget(self.faltan)

        fila = QHBoxLayout()
        fila.addStretch(1)
        self.bt_pausar = QPushButton("Pausar")
        self.bt_pausar.setToolTip("Se queda guardado lo encontrado; luego puedes seguir")
        self.bt_pausar.clicked.connect(self._pausar)
        fila.addWidget(self.bt_pausar)
        self.bt_fondo = QPushButton("Seguir en segundo plano")
        self.bt_fondo.setObjectName("principal")
        self.bt_fondo.setCursor(Qt.PointingHandCursor)
        self.bt_fondo.clicked.connect(self.hide)
        fila.addWidget(self.bt_fondo)
        raiz.addLayout(fila)
        self._pintar_cuenta(trabajo.get("hechas", 0), len(trabajo["canciones"]))

    # ------------------------------------------------------------ marcha

    def empezar(self):
        self.hilo = _Trabajo(self.trabajo["canciones"], self.trabajo.get("hechas", 0))
        self.hilo.avance.connect(self._pintar_cuenta)
        self.hilo.lote.connect(self._guardar_lote)
        self.hilo.termino.connect(self._fin)
        self.hilo.start()

    def _pintar_cuenta(self, hechas, total):
        self.barra.setValue(hechas)
        t = self.trabajo
        self.cuenta.setText(f"{importacion.texto_avance(hechas, total)} canciones  ·  "
                            f"{importacion.miles(t.get('encontradas', 0))} encontradas")

    def _guardar_lote(self, fin, pistas, sin):
        t = self.trabajo
        destino = t["destino"]
        if pistas:
            if self.es_me_gusta:
                anadidas, repetidas = self.col.agregar_me_gusta_varios(pistas)
                t["anadidas"] = t.get("anadidas", 0) + anadidas
                t["repetidas"] = t.get("repetidas", 0) + repetidas
            else:
                t["anadidas"] = t.get("anadidas", 0) + self.col.agregar_a_lista(
                    destino["lista_id"], pistas)
        t["encontradas"] = t.get("encontradas", 0) + len(pistas)
        t["no_encontradas"] = t.get("no_encontradas", []) + list(sin)
        t["hechas"] = fin
        self.col.guardar_estado(importacion.CLAVE_PENDIENTE, t)
        if not self.es_me_gusta and pistas:
            self.ctx.listas_cambio.emit()

    def _pausar(self):
        if self.hilo and self.hilo.isRunning():
            self.hilo.parar = True
            self.bt_pausar.setEnabled(False)
            self.cuenta.setText("Pausando después de esta tanda…")

    def _fin(self, r):
        t = self.trabajo
        total = len(t["canciones"])
        acabo = not r.get("cancelado") and t.get("hechas", 0) >= total
        if acabo:
            self.col.guardar_estado(importacion.CLAVE_PENDIENTE, None)
            if self.es_me_gusta:
                d = t["destino"]
                importacion.anotar_fuente(self.col, d.get("servicio", ""), d.get("enlace", ""),
                                          d.get("titulo", ""), t.get("anadidas", 0),
                                          len(t.get("no_encontradas", [])))
        self.titulo.setText(self.resumen() if acabo else
                            "En pausa. Lo encontrado ya está guardado; sigue cuando quieras "
                            "desde «Traer una lista».")
        faltan = t.get("no_encontradas", [])
        if acabo and faltan:
            self.faltan.setPlainText("No se encontraron en YouTube Music:\n" + "\n".join(faltan))
            self.faltan.show()
        self.bt_pausar.hide()
        self.bt_fondo.setText("Listo")
        try:
            self.bt_fondo.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.bt_fondo.clicked.connect(self.accept)
        if r.get("error"):
            self.cuenta.setText(f"Se detuvo: {r['error']}")
            self.cuenta.setStyleSheet(f"color:{C['error']};")
        if acabo and not self.es_me_gusta:
            self.ctx.listas_cambio.emit()
        self.terminado.emit(dict(t, acabo=acabo))
        if self.isHidden():
            self.show()

    def resumen(self):
        t = self.trabajo
        faltan = len(t.get("no_encontradas", []))
        if self.es_me_gusta:
            txt = f"Se añadieron {importacion.miles(t.get('anadidas', 0))} canciones a tus Me gusta"
            if t.get("repetidas"):
                txt += f" ({importacion.miles(t['repetidas'])} ya estaban)"
        else:
            txt = (f"Lista «{t['destino'].get('nombre', '')}» guardada con "
                   f"{importacion.miles(t.get('anadidas', 0))} canciones")
        if faltan:
            txt += f". {importacion.miles(faltan)} no se encontraron."
        return txt + ("" if faltan else ".")

    def closeEvent(self, e):  # noqa: N802
        # cerrar la ventana no detiene la búsqueda: sigue en segundo plano
        if self.hilo and self.hilo.isRunning():
            e.ignore()
            self.hide()
            return
        super().closeEvent(e)
