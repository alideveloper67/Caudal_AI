# -*- coding: utf-8 -*-
"""Ajustes → «Copia de seguridad»: guardar todo en un archivo .caudal y recuperarlo (aquí, en otra
PC o en el teléfono). La lógica está en descargador/copia_seguridad.py."""

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget)

from .. import copia_seguridad as CS
from ..config import carpeta_perfil
from ..hilos import en_segundo_plano
from .paginas.ajustes import Seccion

QUE_LLEVA = ("Tus me gusta, listas (con sus portadas), historial de escuchas, álbumes y artistas "
             "guardados, el registro de descargas, ajustes, ecualizador, mascota, fondo, artistas "
             "favoritos y las notas del modo estudio. Sirve para pasarlo todo a otra PC o al teléfono, "
             "aunque no uses cuenta. No lleva tu sesión ni contraseñas, ni los audios descargados.")


def _fecha(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M") if ts else "todavía ninguna"


class DialogoRestaurar(QDialog):
    """Vista previa de la copia y cómo traerla: juntar o reemplazar."""

    def __init__(self, copia, padre=None):
        super().__init__(padre)
        self.copia = copia
        self.setWindowTitle("Restaurar una copia")
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(10)
        t = QLabel("Esto trae la copia")
        t.setStyleSheet("font-size:18px;font-weight:800;")
        v.addWidget(t)
        d = QLabel(copia.descripcion())
        d.setObjectName("secundario")
        v.addWidget(d)
        r = QLabel(copia.texto_resumen().replace(" · ", "\n• ").join(("• ", "")))
        r.setWordWrap(True)
        r.setStyleSheet("font-size:14px;line-height:150%;")
        v.addWidget(r)
        v.addSpacing(6)
        self.juntar = QRadioButton("Juntar con lo que tengo")
        self.juntar.setChecked(True)
        ayuda_j = QLabel("Añade lo que falta y no repite nada de lo que ya tienes.")
        ayuda_j.setObjectName("secundario")
        self.reemplazar = QRadioButton("Reemplazar todo")
        ayuda_r = QLabel("Borra tus me gusta, listas, historial y guardados de ahora y deja solo los de la "
                         "copia. Tus archivos descargados no se borran.")
        ayuda_r.setObjectName("secundario")
        ayuda_r.setWordWrap(True)
        grupo = QButtonGroup(self)
        for w in (self.juntar, self.reemplazar):
            grupo.addButton(w)
            w.setCursor(Qt.PointingHandCursor)
        for w in (self.juntar, ayuda_j, self.reemplazar, ayuda_r):
            v.addWidget(w)
        self.con_ajustes = QCheckBox("Usar también los ajustes de la copia (aspecto, ecualizador, mascota…)")
        self.con_ajustes.setChecked(True)
        v.addSpacing(4)
        v.addWidget(self.con_ajustes)
        if copia.origen == "movil":
            nota = QLabel("Viene del teléfono: de sus ajustes se usan solo los que también existen en la PC.")
            nota.setObjectName("secundario")
            nota.setWordWrap(True)
            v.addWidget(nota)
        botones = QHBoxLayout()
        botones.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        ok = QPushButton("Restaurar")
        ok.setObjectName("primario")
        ok.setDefault(True)
        ok.clicked.connect(self._aceptar)
        botones.addWidget(cancelar)
        botones.addWidget(ok)
        v.addSpacing(8)
        v.addLayout(botones)

    @property
    def modo(self):
        return "reemplazar" if self.reemplazar.isChecked() else "juntar"

    def _aceptar(self):
        if self.modo == "reemplazar":
            con_cuenta = getattr(self.parent(), "con_cuenta", False)
            texto = ("Se borrarán tus me gusta, listas, historial de escuchas y guardados de este equipo, "
                     "y quedarán solo los de la copia.")
            if con_cuenta:
                texto += " Como entras con tu cuenta, el cambio también llega a tus otros dispositivos."
            texto += "\n\nTus archivos descargados no se tocan. ¿Reemplazar todo?"
            caja = QMessageBox(QMessageBox.Warning, "Reemplazar todo", texto, parent=self)
            si = caja.addButton("Sí, reemplazar todo", QMessageBox.DestructiveRole)
            caja.addButton("Cancelar", QMessageBox.RejectRole)
            caja.exec()
            if caja.clickedButton() is not si:
                return
        self.accept()


class SeccionCopia(Seccion):
    """La tarjeta de Ajustes."""

    def __init__(self, ctx, padre=None):
        super().__init__("Copia de seguridad", padre)
        self.ctx = ctx
        self.carpeta = carpeta_perfil()
        self.con_cuenta = (getattr(ctx, "cuenta", None) or {}).get("sesion") is not None
        nota = QLabel(QUE_LLEVA)
        nota.setWordWrap(True)
        nota.setObjectName("secundario")
        self.v.addWidget(nota)

        self.bt_guardar = QPushButton("Guardar copia…")
        self.bt_guardar.setCursor(Qt.PointingHandCursor)
        self.bt_guardar.clicked.connect(self._guardar)
        self.fila("Guardar una copia", "Crea un archivo .caudal donde tú elijas.", self.bt_guardar)

        self.bt_restaurar = QPushButton("Abrir copia…")
        self.bt_restaurar.setCursor(Qt.PointingHandCursor)
        self.bt_restaurar.clicked.connect(self._elegir)
        self.fila("Restaurar una copia", "Antes de cambiar nada verás qué trae y podrás elegir "
                                         "entre juntarla con lo tuyo o reemplazarlo todo.", self.bt_restaurar)

        cfg = CS.leer_config(self.carpeta)
        self.auto = QCheckBox()
        self.auto.setCursor(Qt.PointingHandCursor)
        self.auto.setChecked(bool(cfg.get("automatica")))
        self.auto.toggled.connect(self._auto)
        self.et_auto = self.fila("Copia automática cada semana", "", self.auto)
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 0, 0, 0)
        bt_carpeta = QPushButton("Cambiar")
        bt_carpeta.clicked.connect(self._cambiar_carpeta)
        bt_abrir = QPushButton("Abrir")
        bt_abrir.clicked.connect(self._abrir_carpeta)
        h.addWidget(bt_carpeta)
        h.addWidget(bt_abrir)
        self.et_carpeta = self.fila("Carpeta de las copias automáticas", "", caja)
        self._pintar()

    # ---------------------------------------------------------------- pintar
    def _carpeta_auto(self):
        return CS.leer_config(self.carpeta).get("carpeta") or CS.carpeta_por_defecto()

    def _pintar(self):
        cfg = CS.leer_config(self.carpeta)
        ayuda = ("Una vez por semana, en segundo plano, se guarda una copia en la carpeta de abajo. "
                 f"Se quedan las {cfg.get('conservar', 5)} más nuevas. Última: {_fecha(cfg.get('ultima'))}.")
        self._poner_ayuda(self.et_auto, ayuda)
        self._poner_ayuda(self.et_carpeta, self._carpeta_auto())

    @staticmethod
    def _poner_ayuda(fila, texto):
        etiquetas = fila.findChildren(QLabel)
        if len(etiquetas) >= 2:
            etiquetas[1].setText(texto)
        else:
            a = QLabel(texto)
            a.setObjectName("secundario")
            a.setWordWrap(True)
            fila.layout().itemAt(0).layout().addWidget(a)

    def _aviso(self, texto):
        aviso = getattr(self.ctx, "aviso", None)
        if aviso is not None:
            aviso.emit(texto)

    # ---------------------------------------------------------------- guardar
    def _extras(self):
        return CS.extras_de(self.ctx)

    def _guardar(self):
        inicio = str(Path.home() / "Documents" / CS.nombre_sugerido())
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar la copia de Caudal", inicio,
                                              "Copia de Caudal (*.caudal)")
        if not ruta:
            return
        self.bt_guardar.setEnabled(False)
        self.bt_guardar.setText("Guardando…")
        extras = self._extras()
        ctx = self.ctx

        def trabajo():
            with ctx.coleccion.copia_de_lectura() as c:
                contenido = CS.crear_copia(c, ctx.ajustes, self.carpeta, **extras)
            return CS.guardar_copia(ruta, contenido), CS.abrir_copia(contenido).texto_resumen()

        def listo(res):
            self._listo_boton()
            destino, resumen = res
            QMessageBox.information(self, "Copia guardada",
                                    f"Se guardó en:\n{destino}\n\nLleva: {resumen}\n\nPara pasarla al teléfono, "
                                    "envíatela (por ejemplo por WhatsApp o un cable) y ábrela desde Ajustes → "
                                    "Copia de seguridad.")

        en_segundo_plano(trabajo, ok=listo, error=self._fallo, dueno=self)

    def _listo_boton(self):
        self.bt_guardar.setEnabled(True)
        self.bt_guardar.setText("Guardar copia…")
        self.bt_restaurar.setEnabled(True)
        self.bt_restaurar.setText("Abrir copia…")

    def _fallo(self, e):
        self._listo_boton()
        texto = str(e) if isinstance(e, CS.ErrorCopia) else (
            "Algo salió mal y no se cambió nada. Vuelve a intentarlo; si sigue pasando, "
            "prueba con otra copia.")
        QMessageBox.warning(self, "Copia de seguridad", texto)

    # ---------------------------------------------------------------- restaurar
    def _elegir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Elegir una copia de Caudal", str(Path.home()),
                                              "Copia de Caudal (*.caudal);;Todos los archivos (*)")
        if not ruta:
            return
        self.bt_restaurar.setEnabled(False)
        self.bt_restaurar.setText("Leyendo…")
        en_segundo_plano(CS.abrir_copia, ruta, ok=self._vista_previa, error=self._fallo, dueno=self)

    def _vista_previa(self, copia):
        self._listo_boton()
        dlg = DialogoRestaurar(copia, self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._restaurar(copia, dlg.modo, dlg.con_ajustes.isChecked())

    def _restaurar(self, copia, modo, con_ajustes):
        self.bt_restaurar.setEnabled(False)
        self.bt_restaurar.setText("Restaurando…")
        ctx = self.ctx
        anotar = getattr(ctx.coleccion, "sincronizador", None) is not None

        def trabajo():
            # en otro hilo con su propia conexión: la ventana sigue respondiendo
            with ctx.coleccion.copia_de_lectura() as c:
                return CS.restaurar_coleccion(c, copia, modo, anotar=anotar)

        def listo(cuenta):
            self._listo_boton()
            col = ctx.coleccion
            try:
                col.olvidar_memoria()
                col.invalidar_indice()
            except Exception:  # noqa: BLE001
                pass
            sinc = getattr(ctx, "sincronizador", None)
            if anotar and sinc is not None:
                sinc.pronto()
            hecho = CS.restaurar_extras(copia, modo, ajustes=ctx.ajustes, carpeta=self.carpeta, col=col,
                                        ctx=ctx, con_ajustes=con_ajustes)
            for senal in ("listas_cambio", "guardados_cambio", "descargas_cambio", "sonido_cambio"):
                s = getattr(ctx, senal, None)
                if s is not None:
                    s.emit()
            if getattr(ctx, "me_gusta_cambio", None) is not None:
                ctx.me_gusta_cambio.emit("", True)
            self._terminado(cuenta, hecho, modo)

        en_segundo_plano(trabajo, ok=listo, error=self._fallo, dueno=self)

    def _terminado(self, cuenta, hecho, modo):
        partes = []
        nombres = (("me_gusta", "me gusta"), ("listas", "listas"), ("canciones_en_listas", "canciones en listas"),
                   ("escuchas", "escuchas"), ("guardados", "guardados"), ("descargas", "descargas registradas"))
        for k, n in nombres:
            if cuenta.get(k):
                partes.append(f"{cuenta[k]} {n}")
        que = ("Entraron: " + ", ".join(partes) + ".") if partes else (
            "No había nada nuevo: ya tenías todo lo de la copia." if modo == "juntar" else "")
        if "ajustes" in hecho or "estudio" in hecho or "mascota" in hecho:
            que += "\n\nPara ver del todo los ajustes, el aspecto y el modo estudio, reinicia Caudal."
        caja = QMessageBox(QMessageBox.Information, "Copia restaurada", que.strip() or "Listo.", parent=self)
        reiniciar = None
        if getattr(self.ctx, "reiniciar", None) is not None and "ajustes" in hecho:
            reiniciar = caja.addButton("Reiniciar ahora", QMessageBox.AcceptRole)
        caja.addButton("Listo", QMessageBox.RejectRole)
        caja.exec()
        if reiniciar is not None and caja.clickedButton() is reiniciar:
            self.ctx.reiniciar()

    # ---------------------------------------------------------------- automática
    def _auto(self, si):
        cfg = CS.leer_config(self.carpeta)
        cfg["automatica"] = bool(si)
        CS.guardar_config(cfg, self.carpeta)
        self._pintar()
        if si:
            self._aviso("Copia automática activada: la primera se hace en un momento")
            ctx = self.ctx
            extras = self._extras()

            def trabajo():
                with ctx.coleccion.copia_de_lectura() as c:
                    return CS.hacer_automatica(c, ctx.ajustes, self.carpeta, **extras)
            en_segundo_plano(trabajo, ok=lambda _r: self._pintar(), error=lambda _e: None, dueno=self)

    def _cambiar_carpeta(self):
        ruta = QFileDialog.getExistingDirectory(self, "Carpeta para las copias automáticas", self._carpeta_auto())
        if not ruta:
            return
        cfg = CS.leer_config(self.carpeta)
        cfg["carpeta"] = ruta
        CS.guardar_config(cfg, self.carpeta)
        self._pintar()

    def _abrir_carpeta(self):
        ruta = self._carpeta_auto()
        os.makedirs(ruta, exist_ok=True)
        try:
            os.startfile(ruta)  # noqa: S606 - abrir la carpeta en el Explorador
        except (OSError, AttributeError):
            self._aviso(ruta)
