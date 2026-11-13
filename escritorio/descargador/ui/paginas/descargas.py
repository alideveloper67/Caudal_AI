# -*- coding: utf-8 -*-
"""Gestor de descargas: pegar enlaces, la cola en marcha y el historial."""

import os
import subprocess
import time
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMenu, QMessageBox, QPushButton, QScrollArea,
                               QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget, QFrame)

from ... import motor, redes
from .. import iconos
from ..componentes import SinResultados
from ..dialogo_descarga import AUDIOS, CALIDADES, CONTENEDORES, DialogoDescarga
from ..estilos import C
from ..tarjeta import TarjetaDescarga

TIPOS = [("Video con sonido", "completo"), ("Solo audio", "audio"), ("Solo video", "video")]


def abrir_ruta(ruta):
    if ruta and os.path.exists(ruta):
        try:
            os.startfile(ruta)  # noqa: S606
            return True
        except OSError:
            return False
    return False


def mostrar_en_carpeta(archivo):
    if archivo and os.path.exists(archivo):
        subprocess.Popen(["explorer", "/select,", os.path.normpath(archivo)])
        return True
    return False


def _combo(opciones, valor, ancho):
    c = QComboBox()
    for etiqueta, v in opciones:
        c.addItem(etiqueta, v)
    i = c.findData(valor)
    c.setCurrentIndex(i if i >= 0 else 0)
    c.setFixedWidth(ancho)
    return c


class PaginaDescargas(QWidget):
    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.gestor = ctx.gestor
        self.ajustes = ctx.ajustes
        self.titulo = "Descargas"
        self.tarjetas = {}
        self._sucias = set()

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 14)
        v.setSpacing(14)
        t = QLabel("Descargas")
        t.setObjectName("titulo_pagina")
        t.setStyleSheet("font-size:30px;font-weight:900;")
        v.addWidget(t)

        # --- pegar enlaces
        caja = QFrame()
        caja.setObjectName("caja")
        vc = QVBoxLayout(caja)
        vc.setContentsMargins(16, 16, 16, 14)
        vc.setSpacing(10)
        fila = QHBoxLayout()
        fila.setSpacing(8)
        self.campo = QLineEdit()
        self.campo.setObjectName("url")
        self.campo.setPlaceholderText("Pega uno o varios enlaces de YouTube, TikTok, Instagram, "
                                      "X, Facebook, Telegram… (1800 sitios)")
        self.campo.setClearButtonEnabled(True)
        self.campo.returnPressed.connect(self._encolar)
        fila.addWidget(self.campo, 1)
        bt_pegar = QPushButton()
        bt_pegar.setIcon(iconos.icono("pegar", 18, C["texto"]))
        bt_pegar.setToolTip("Pegar del portapapeles")
        bt_pegar.setFixedSize(44, 44)
        bt_pegar.setCursor(Qt.PointingHandCursor)
        bt_pegar.clicked.connect(self._pegar)
        fila.addWidget(bt_pegar)
        bt = QPushButton("  Descargar")
        bt.setObjectName("principal")
        bt.setIcon(iconos.icono("descargar", 17, C["acento_texto"]))
        bt.setCursor(Qt.PointingHandCursor)
        bt.setFixedHeight(44)
        bt.clicked.connect(self._encolar)
        fila.addWidget(bt)
        vc.addLayout(fila)

        opciones = QHBoxLayout()
        opciones.setSpacing(8)
        a = self.ajustes
        self.c_tipo = _combo(TIPOS, a["tipo_descarga"], 170)
        self.c_calidad = _combo(CALIDADES, a["calidad"], 200)
        self.c_contenedor = _combo(CONTENEDORES, a["formato_salida"], 90)
        self.c_audio = _combo(AUDIOS, a["formato_audio"], 230)
        self.c_codec = _combo([("Máxima calidad", "maxima"), ("Compatible (H.264)", "compatible")],
                              a["codec_descarga"], 170)
        for c in (self.c_tipo, self.c_calidad, self.c_codec, self.c_contenedor, self.c_audio):
            c.currentIndexChanged.connect(self._guardar_rapidos)
            opciones.addWidget(c)
        bt_mas = QPushButton("Más opciones…")
        bt_mas.setObjectName("enlace")
        bt_mas.setCursor(Qt.PointingHandCursor)
        bt_mas.clicked.connect(self._mas_opciones)
        opciones.addWidget(bt_mas)
        opciones.addStretch(1)
        vc.addLayout(opciones)
        self.et_carpeta = QPushButton("")
        self.et_carpeta.setObjectName("enlace")
        self.et_carpeta.setCursor(Qt.PointingHandCursor)
        self.et_carpeta.clicked.connect(lambda: abrir_ruta(self.ajustes["carpeta"]))
        vc.addWidget(self.et_carpeta, 0, Qt.AlignLeft)
        v.addWidget(caja)

        # --- pestanas
        pest = QHBoxLayout()
        pest.setSpacing(0)
        self.bt_curso = QPushButton("En curso")
        self.bt_hist = QPushButton("Historial")
        for i, b in enumerate((self.bt_curso, self.bt_hist)):
            b.setObjectName("pestana")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self._pestana(i))
            pest.addWidget(b)
        pest.addStretch(1)
        self.et_cola = QLabel("")
        self.et_cola.setObjectName("secundario")
        pest.addWidget(self.et_cola)
        pest.addSpacing(12)
        self.bt_pausar = QPushButton("  Pausar todo")
        self.bt_pausar.setIcon(iconos.icono("pausa", 14, C["texto"]))
        self.bt_reanudar = QPushButton("  Reanudar")
        self.bt_reanudar.setIcon(iconos.icono("reproducir", 14, C["texto"]))
        self.bt_limpiar = QPushButton("  Limpiar terminadas")
        self.bt_limpiar.setIcon(iconos.icono("papelera", 14, C["texto"]))
        for b in (self.bt_pausar, self.bt_reanudar, self.bt_limpiar):
            b.setCursor(Qt.PointingHandCursor)
            pest.addWidget(b)
        v.addLayout(pest)

        self.pila = QStackedWidget()
        # en curso
        curso = QWidget()
        vcu = QVBoxLayout(curso)
        vcu.setContentsMargins(0, 0, 0, 0)
        self.area = QScrollArea()
        self.area.setObjectName("lienzo")
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        interior = QWidget()
        self.lista = QVBoxLayout(interior)
        self.lista.setContentsMargins(0, 0, 8, 8)
        self.lista.setSpacing(8)
        self.lista.addStretch(1)
        self.area.setWidget(interior)
        vcu.addWidget(self.area, 1)
        self.vacio = SinResultados("descargar", "No hay descargas en marcha",
                                   "Pega un enlace arriba, o usa «Descargar» en cualquier canción, "
                                   "álbum o lista.\nTambién puedes arrastrar enlaces a la ventana.")
        vcu.addWidget(self.vacio, 1)
        self.pila.addWidget(curso)
        # historial
        hist = QWidget()
        vh = QVBoxLayout(hist)
        vh.setContentsMargins(0, 0, 0, 0)
        fila_h = QHBoxLayout()
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar en el historial…")
        self.buscar.setClearButtonEnabled(True)
        self.buscar.textChanged.connect(self._cargar_historial)
        fila_h.addWidget(self.buscar, 1)
        b_abrir = QPushButton("Abrir")
        b_abrir.clicked.connect(self._abrir_historial)
        b_carpeta = QPushButton("Ver en carpeta")
        b_carpeta.clicked.connect(self._carpeta_historial)
        b_vaciar = QPushButton("Quitar las fallidas")
        b_vaciar.setObjectName("peligro")
        b_vaciar.clicked.connect(self._vaciar_historial)
        for b in (b_abrir, b_carpeta, b_vaciar):
            b.setCursor(Qt.PointingHandCursor)
            fila_h.addWidget(b)
        vh.addLayout(fila_h)
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Título", "Red", "Calidad", "Tamaño", "Fecha",
                                              "Estado"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setShowGrid(False)
        cab = self.tabla.horizontalHeader()
        cab.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cab.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            cab.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tabla.doubleClicked.connect(self._abrir_historial)
        vh.addWidget(self.tabla, 1)
        self.pila.addWidget(hist)
        v.addWidget(self.pila, 1)

        self.bt_pausar.clicked.connect(self._pausar_todo)
        self.bt_reanudar.clicked.connect(self.gestor.reanudar_todo)
        self.bt_limpiar.clicked.connect(self.gestor.limpiar_terminadas)
        self.gestor.tarea_agregada.connect(self._agregar_tarjeta)
        self.gestor.tarea_cambio.connect(self._sucias.add)
        self.gestor.cola_cambio.connect(self._sincronizar)

        for t in self.gestor.lista():
            self._agregar_tarjeta(t.ident)
        self._pestana(0)
        self._guardar_rapidos()
        self.reloj = QTimer(self)
        self.reloj.timeout.connect(self._refrescar)
        self.reloj.start(250)

    # ------------------------------------------------------------ campo

    def _pegar(self):
        texto = QGuiApplication.clipboard().text().strip()
        if texto:
            self.campo.setText(texto)
            self.campo.setFocus()

    def _encolar(self):
        texto = self.campo.text().strip()
        if not texto:
            self.campo.setFocus()
            return
        urls = redes.extraer_urls(texto)
        if not urls:
            QMessageBox.warning(self, "Caudal", "No encontré ningún enlace válido en lo que pegaste.")
            return
        self.gestor.agregar_varias(urls)
        self.campo.clear()
        self._pestana(0)

    def _mas_opciones(self):
        texto = self.campo.text().strip()
        urls = redes.extraer_urls(texto)
        if not urls:
            QMessageBox.information(self, "Caudal", "Pega primero un enlace en el campo de arriba.")
            return
        d = DialogoDescarga(self.ajustes, None, self, url=urls[0])
        if d.exec():
            o = d.opciones()
            tipo = o.pop("tipo", None)
            calidad = o.pop("calidad", None)
            for u in urls:
                self.gestor.agregar(u, tipo=tipo, calidad=calidad, opciones=o)
            self.campo.clear()
            self._pestana(0)

    def _guardar_rapidos(self):
        a = self.ajustes
        a["tipo_descarga"] = self.c_tipo.currentData()
        a["calidad"] = self.c_calidad.currentData()
        a["formato_salida"] = self.c_contenedor.currentData()
        a["formato_audio"] = self.c_audio.currentData()
        a["codec_descarga"] = self.c_codec.currentData()
        a.guardar()
        audio = a["tipo_descarga"] == "audio"
        self.c_calidad.setVisible(not audio)
        self.c_codec.setVisible(not audio)
        self.c_contenedor.setVisible(not audio)
        self.c_audio.setVisible(audio)
        self.et_carpeta.setText(f"Se guarda en  {a['carpeta']}")

    def actualizar_carpeta(self):
        self.et_carpeta.setText(f"Se guarda en  {self.ajustes['carpeta']}")

    # ------------------------------------------------------------ lista

    def _pestana(self, i):
        self.pila.setCurrentIndex(i)
        self.bt_curso.setChecked(i == 0)
        self.bt_hist.setChecked(i == 1)
        for b in (self.bt_pausar, self.bt_reanudar, self.bt_limpiar):
            b.setVisible(i == 0)
        if i == 1:
            self._cargar_historial()

    def _agregar_tarjeta(self, ident):
        t = self.gestor.tareas.get(ident)
        if not t or ident in self.tarjetas:
            return
        tarjeta = TarjetaDescarga(t)
        tarjeta.accion_principal.connect(self._accion_principal)
        tarjeta.accion_abrir.connect(lambda i: mostrar_en_carpeta(
            self.gestor.tareas[i].archivo) if i in self.gestor.tareas else None)
        tarjeta.accion_quitar.connect(self.gestor.quitar)
        tarjeta.accion_menu.connect(self._menu_tarjeta)
        self.tarjetas[ident] = tarjeta
        self.lista.insertWidget(self.lista.count() - 1, tarjeta)
        self._alternar_vacio()

    def _accion_principal(self, ident):
        t = self.gestor.tareas.get(ident)
        if not t:
            return
        if t.estado in (motor.DESCARGANDO, motor.EN_COLA, motor.ANALIZANDO):
            self.gestor.pausar(ident)
        elif t.estado in (motor.PAUSADA, motor.ERROR, motor.CANCELADA):
            self.gestor.reanudar(ident)
        elif t.estado == motor.COMPLETADA:
            self._reproducir_tarea(t)

    def _reproducir_tarea(self, t):
        filas = self.ctx.coleccion.descargadas()
        p = next((x for x in filas if x.get("archivo") == t.archivo), None)
        if p:
            self.ctx.reproducir_pista(p, {"tipo": "disco", "id": "disco", "titulo": "Descargas"})
        else:
            abrir_ruta(t.archivo)

    def _menu_tarjeta(self, ident, pos):
        t = self.gestor.tareas.get(ident)
        if not t:
            return
        menu = QMenu(self)
        if t.estado == motor.COMPLETADA and t.archivo:
            menu.addAction("Reproducir en Caudal", lambda: self._reproducir_tarea(t))
            menu.addAction("Abrir con otra app", lambda: abrir_ruta(t.archivo))
            menu.addAction("Ver en la carpeta", lambda: mostrar_en_carpeta(t.archivo))
            menu.addSeparator()
        if t.estado in (motor.ERROR, motor.CANCELADA, motor.PAUSADA):
            menu.addAction("Reintentar", lambda: self.gestor.reanudar(ident))
        if t.estado in (motor.DESCARGANDO, motor.EN_COLA, motor.ANALIZANDO):
            menu.addAction("Pausar", lambda: self.gestor.pausar(ident))
            menu.addAction("Cancelar", lambda: self.gestor.cancelar(ident))
        menu.addAction("Copiar enlace", lambda: QGuiApplication.clipboard().setText(t.url))
        menu.addAction("Abrir enlace en el navegador", lambda: webbrowser.open(t.url))
        if t.error:
            menu.addSeparator()
            menu.addAction("Ver el detalle del error",
                           lambda: QMessageBox.information(self, "Detalle", t.error))
        menu.addSeparator()
        menu.addAction("Quitar de la lista", lambda: self.gestor.quitar(ident))
        menu.exec(pos)

    def _sincronizar(self):
        for ident in list(self.tarjetas):
            if ident not in self.gestor.tareas:
                tarjeta = self.tarjetas.pop(ident)
                self.lista.removeWidget(tarjeta)
                tarjeta.deleteLater()
        self._alternar_vacio()

    def _alternar_vacio(self):
        hay = bool(self.tarjetas)
        self.area.setVisible(hay)
        self.vacio.setVisible(not hay)

    def _pausar_todo(self):
        for t in self.gestor.lista():
            if t.estado in (motor.DESCARGANDO, motor.EN_COLA, motor.ANALIZANDO):
                self.gestor.pausar(t.ident)

    def _refrescar(self):
        activo = bool(self._sucias) or self.gestor.hay_actividad()
        deseado = 250 if activo else 1200
        if self.reloj.interval() != deseado:
            self.reloj.setInterval(deseado)
        if self._sucias:
            for ident in list(self._sucias):
                tarjeta = self.tarjetas.get(ident)
                tarea = self.gestor.tareas.get(ident)
                if tarjeta and tarea:
                    tarjeta.actualizar(tarea)
            self._sucias.clear()
        tareas = self.gestor.lista()
        activas = [t for t in tareas if t.activa]
        hechas = [t for t in tareas if t.estado == motor.COMPLETADA]
        velocidad = sum(t.velocidad or 0 for t in activas)
        if tareas:
            texto = f"{len(activas)} en marcha · {len(hechas)} listas de {len(tareas)}"
            if velocidad:
                texto += f" · {motor.formato_bytes(velocidad)}/s"
        else:
            texto = ""
        self.et_cola.setText(texto)

    # ------------------------------------------------------------ historial

    def _cargar_historial(self, *_):
        filas = self.ctx.historial.listar(500, self.buscar.text().strip())
        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            fecha = time.strftime("%d/%m/%Y %H:%M", time.localtime(f["fecha"] or 0))
            estado = "Completada" if f["estado"] == "completada" else "Error"
            valores = [f["titulo"] or f["url"], f["plataforma"] or "", f["calidad"] or "",
                       motor.formato_bytes(f["tamano"]) if f["tamano"] else "", fecha, estado]
            for j, val in enumerate(valores):
                celda = QTableWidgetItem(str(val))
                if j == 0:
                    celda.setData(Qt.UserRole, f["archivo"] or "")
                    celda.setToolTip(f["url"])
                if j == 5:
                    from PySide6.QtGui import QColor
                    celda.setForeground(QColor(C["exito"] if f["estado"] == "completada"
                                               else C["error"]))
                self.tabla.setItem(i, j, celda)

    def _archivo_sel(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            return ""
        celda = self.tabla.item(fila, 0)
        return celda.data(Qt.UserRole) if celda else ""

    def _abrir_historial(self, *_):
        archivo = self._archivo_sel()
        if not archivo or not os.path.exists(archivo):
            QMessageBox.information(self, "Caudal", "Ese archivo ya no está en el disco.")
            return
        abrir_ruta(archivo)

    def _carpeta_historial(self):
        archivo = self._archivo_sel()
        if not mostrar_en_carpeta(archivo):
            abrir_ruta(self.ajustes["carpeta"])

    def _vaciar_historial(self):
        # lo completado alimenta tu biblioteca: solo se quitan los intentos fallidos
        h = self.ctx.historial
        h.con.execute("DELETE FROM descargas WHERE estado != 'completada'")
        h.con.commit()
        self._cargar_historial()
        self.ctx.aviso.emit("Quitadas las descargas fallidas del historial")
