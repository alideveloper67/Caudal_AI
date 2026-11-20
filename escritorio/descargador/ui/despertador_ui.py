# -*- coding: utf-8 -*-
"""Despertador con música en Caudal Escritorio.

- `GestorDespertador`: mira cada 15 s si toca una alarma (también al despertar la PC, si no pasó
  media hora), la hace sonar con el reproductor de Caudal subiendo el volumen poco a poco y enseña la
  ventana de «Posponer / Apagar». Se abre desde la bandeja («Despertador…») o con Ctrl+Alt+D.
- `DialogoDespertador`: la lista de alarmas y su editor (hora, días, qué suena, volumen, subida,
  minutos de posponer y «Probar»).

En la computadora Caudal tiene que estar abierto (aunque sea en la bandeja) y la PC despierta.
La lógica (próxima vez, qué suena sin internet, curva del volumen) vive en `despertador.py`.
"""

import random
import time
from datetime import datetime

from PySide6.QtCore import QObject, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QScrollArea, QSlider, QSpinBox, QTimeEdit, QVBoxLayout, QWidget)

from .. import despertador as dsp
from ..hilos import en_segundo_plano
from .estilos import C

CLAVE_TONO = "despertador:tono"


def _hoja():
    return (
        f"QDialog,QWidget#despertador{{background:{C['panel']};color:{C['texto']};}}"
        f"QLabel{{color:{C['texto']};background:transparent;}}"
        f"QLabel[sub='1']{{color:{C['texto2']};font-size:12.5px;}}"
        f"QPushButton{{background:{C['superficie2']};color:{C['texto']};border:none;border-radius:16px;"
        "padding:7px 16px;font-weight:600;}"
        f"QPushButton:hover{{background:{C['superficie3']};}}"
        f"QPushButton[principal='1']{{background:{C['acento']};color:{C['acento_texto']};font-weight:800;}}"
        f"QPushButton[dia='1']{{border-radius:17px;padding:0;min-width:34px;max-width:34px;min-height:34px;"
        "max-height:34px;font-weight:800;}"
        f"QPushButton[dia='1']:checked{{background:{C['acento']};color:{C['acento_texto']};}}"
        f"QComboBox,QSpinBox,QTimeEdit,QLineEdit{{background:{C['superficie2']};color:{C['texto']};"
        f"border:1px solid {C['borde']};border-radius:8px;padding:5px 8px;}}"
        f"QListWidget{{background:{C['superficie']};color:{C['texto']};border:1px solid {C['borde']};"
        "border-radius:8px;}"
        f"QFrame#fila{{background:{C['superficie']};border-radius:12px;}}"
        f"QCheckBox{{color:{C['texto']};}}"
    )


# ============================================================ gestor

class GestorDespertador(QObject):
    """Vigila las alarmas y las hace sonar. Uno por ventana."""

    cambiado = Signal()

    def __init__(self, ctx, ventana):
        super().__init__(ventana)
        self.ctx = ctx
        self.ventana = ventana
        self.r = ctx.reproductor
        self.alarmas = dsp.leer()
        self._ultima = datetime.now()
        self.sonando = None              # la alarma que suena ahora
        self._inicio = 0.0
        self._vol_antes = None
        self._objetivo = 80
        self._tono = False
        self._ventana_sonando = None
        self._winsound = False

        self._reloj = QTimer(self)
        self._reloj.setInterval(15000)
        self._reloj.timeout.connect(self._mirar)
        self._reloj.start()

        self._subida = QTimer(self)
        self._subida.setInterval(250)
        self._subida.timeout.connect(self._paso_volumen)

        self.r.estado_cambio.connect(self._al_estado)
        self.r.pista_cambio.connect(self._al_pista)

        self._enganchar_bandeja()
        atajo = QShortcut(QKeySequence("Ctrl+Alt+D"), ventana)
        atajo.activated.connect(self.abrir_dialogo)

    # ---------------------------------------------------------------- guardado

    def guardar(self):
        dsp.guardar(self.alarmas)
        self.cambiado.emit()

    def poner(self, alarma):
        alarma = dsp.normalizar(alarma)
        for i, a in enumerate(self.alarmas):
            if a["id"] == alarma["id"]:
                self.alarmas[i] = alarma
                break
        else:
            self.alarmas.append(alarma)
        self.guardar()
        return alarma

    def quitar(self, ident):
        self.alarmas = [a for a in self.alarmas if a["id"] != ident]
        self.guardar()

    def proxima(self):
        """(alarma, cuándo) de la próxima que suena, o (None, None)."""
        mejor = (None, None)
        for a in self.alarmas:
            p = dsp.proxima_vez(a)
            if p and (mejor[1] is None or p < mejor[1]):
                mejor = (a, p)
        return mejor

    # ---------------------------------------------------------------- bandeja

    def _enganchar_bandeja(self):
        menu = getattr(self.ventana, "_menu_bandeja", None)
        if menu is None:
            return
        try:
            acciones = menu.actions()
            antes = acciones[-1] if acciones else None    # antes de «Salir»
            from PySide6.QtGui import QAction
            accion = QAction("Despertador…", menu)
            accion.triggered.connect(self.abrir_dialogo)
            menu.insertAction(antes, accion)
        except Exception:  # noqa: BLE001 - sin bandeja el atajo sigue valiendo
            pass

    def abrir_dialogo(self):
        try:
            self.ventana.traer_al_frente()
        except Exception:  # noqa: BLE001
            pass
        DialogoDespertador(self, self.ventana).exec()

    # ---------------------------------------------------------------- vigilar

    def _mirar(self):
        ahora = datetime.now()
        tocan = dsp.tocan(self.alarmas, self._ultima, ahora)
        self._ultima = ahora
        if tocan and self.sonando is None:
            self.sonar(tocan[0])

    # ---------------------------------------------------------------- sonar

    def _candidatas(self, alarma):
        col = self.ctx.coleccion
        f = alarma.get("fuente") or {}
        tipo = f.get("tipo")
        try:
            if tipo == "cancion":
                p = f.get("pista")
                return [p] if isinstance(p, dict) else []
            if tipo == "lista":
                return col.pistas_de_lista(int(f.get("id")))
            if tipo == "mix":
                from .. import mixes
                hoy, _c = mixes.guardados_de_hoy(col)
                for m in hoy or []:
                    if m.get("id") == f.get("id"):
                        return [p for p in (m.get("pistas") or []) if isinstance(p, dict)]
                return []
            if tipo == "me_gusta":
                return col.lista_me_gusta(limite=400)
        except Exception:  # noqa: BLE001 - lista borrada, base ocupada...: suena el respaldo
            return []
        return []

    def _respaldo(self):
        col = self.ctx.coleccion
        try:
            locales = col.descargadas(solo_audio=True)
        except Exception:  # noqa: BLE001
            return []
        gustan = [p for p in locales if col.me_gusta(p.get("clave"))]
        return gustan or locales

    def sonar(self, alarma, prueba=False):
        """Empieza a sonar (primero se mira si hay internet, sin trabar la ventana)."""
        if self.sonando is not None:
            self._parar_sonido()
        self.sonando = dict(alarma, _prueba=prueba)
        en_segundo_plano(dsp.hay_internet, ok=lambda red: self._arrancar(red),
                         error=lambda _e: self._arrancar(False), dueno=self)

    def _arrancar(self, hay_red):
        alarma = self.sonando
        if alarma is None:
            return
        col = self.ctx.coleccion
        tipo, pistas, _motivo = dsp.planear(alarma, hay_red, self._candidatas(alarma),
                                            col.esta_descargada, self._respaldo(), random.Random())
        self._objetivo = int(alarma.get("volumen") or 80)
        if self._vol_antes is None:
            self._vol_antes = self.r.volumen
        self._inicio = time.monotonic()
        self._tono = tipo == "tono"
        titulo = "Sonido suave de Caudal"
        if self.r.disponible:
            self.r.fijar_volumen(max(1, round(self._objetivo * dsp.factor_volumen(0, alarma["subida"]))))
            if self._tono:
                self._tocar_tono()
            else:
                contexto = {"tipo": "seleccion", "id": "despertador",
                            "titulo": alarma.get("etiqueta") or "Despertador"}
                self.r.reproducir_lista(pistas, contexto=contexto, modo="audio")
                titulo = f"{pistas[0].get('titulo', '')} · {pistas[0].get('artista', '')}".strip(" ·")
            self._subida.start()
        else:
            self._tocar_winsound()
        self._mostrar_ventana(alarma, titulo)

    def _pista_tono(self):
        ruta = str(dsp.ruta_tono())
        return {"tipo": "pista", "clave": CLAVE_TONO, "titulo": "Despertador · Amanecer",
                "artista": "Caudal", "artistas": [], "archivo": ruta, "es_audio": True,
                "es_video": False, "duracion": 8, "miniatura": ""}

    def _tocar_tono(self):
        self.r.reproducir_pista(self._pista_tono(), contexto={"tipo": "seleccion", "id": "despertador",
                                                              "titulo": "Despertador"},
                                modo="audio", con_radio=False)

    def _tocar_winsound(self):
        try:
            import winsound
            winsound.PlaySound(str(dsp.ruta_tono()),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
            self._winsound = True
        except Exception:  # noqa: BLE001 - fuera de Windows no hay con qué
            self._winsound = False

    def _al_pista(self, pista):
        # el sonido de la alarma no cuenta como «escuchado» (no entra en tu resumen ni en los mixes)
        if pista and pista.get("clave") == CLAVE_TONO:
            self.r._escucha_registrada = True   # noqa: SLF001 - el reproductor no ofrece otra forma

    def _al_estado(self, estado):
        # el tono dura 8 s: mientras la alarma siga, vuelve a empezar
        if self.sonando is not None and self._tono and estado == "parado":
            QTimer.singleShot(150, lambda: self._tono and self.sonando is not None and self._tocar_tono())

    def _paso_volumen(self):
        a = self.sonando
        if a is None:
            self._subida.stop()
            return
        t = time.monotonic() - self._inicio
        if t >= dsp.MAX_SONANDO_SEG:
            self.apagar()                       # nadie la apagó: se calla sola
            return
        v = max(1, round(self._objetivo * dsp.factor_volumen(t, a["subida"])))
        if v != self.r.volumen:
            self.r.fijar_volumen(v)

    def _parar_sonido(self, seguir=False):
        self._subida.stop()
        tono = self._tono
        self._tono = False
        if self._winsound:
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:  # noqa: BLE001
                pass
            self._winsound = False
        if self.r.disponible and (tono or not seguir):
            self.r.detener()
        if self._vol_antes is not None:
            self.r.fijar_volumen(self._vol_antes)
            self._vol_antes = None

    def _cerrar_ventana(self):
        v = self._ventana_sonando
        self._ventana_sonando = None
        if v is not None:
            v.close()
            v.deleteLater()

    def posponer(self):
        a = self.sonando
        if a is None:
            return
        self._parar_sonido()
        self._cerrar_ventana()
        self.sonando = None
        if not a.get("_prueba"):
            self.poner(dsp.posponer(a))
            try:
                self.ventana.aviso.mostrar(f"Pospuesta {a['posponer']} minutos")
            except Exception:  # noqa: BLE001
                pass

    def apagar(self, seguir=False):
        """Apaga la alarma. Con `seguir`, la música se queda sonando (al volumen de siempre)."""
        a = self.sonando
        if a is None:
            return
        self._parar_sonido(seguir=seguir)
        self._cerrar_ventana()
        self.sonando = None
        if not a.get("_prueba"):
            self.poner(dsp.tras_sonar(a))

    def _mostrar_ventana(self, alarma, titulo):
        self._cerrar_ventana()
        v = VentanaSonando(alarma, titulo, sin_musica=self._tono)
        v.posponer.connect(self.posponer)
        v.apagar.connect(self.apagar)
        self._ventana_sonando = v
        v.show()
        v.raise_()
        v.activateWindow()
        try:
            self.ventana.traer_al_frente()
            v.raise_()
        except Exception:  # noqa: BLE001
            pass


# ============================================================ ventana de «está sonando»

class VentanaSonando(QWidget):
    posponer = Signal()
    apagar = Signal(bool)

    def __init__(self, alarma, titulo, sin_musica=False):
        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setObjectName("despertador")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(_hoja())
        self.setWindowTitle("Despertador · Caudal")
        self.setMinimumSize(420, 340)
        v = QVBoxLayout(self)
        v.setContentsMargins(32, 28, 32, 28)
        v.setSpacing(10)
        self.et_hora = QLabel(datetime.now().strftime("%H:%M"))
        self.et_hora.setAlignment(Qt.AlignCenter)
        self.et_hora.setStyleSheet(f"font-size:64px;font-weight:900;color:{C['texto']};")
        v.addWidget(self.et_hora)
        etiqueta = QLabel(alarma.get("etiqueta") or "Buenos días")
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setStyleSheet(f"font-size:20px;font-weight:800;color:{C['acento']};")
        v.addWidget(etiqueta)
        sub = QLabel(titulo if not sin_musica else "Sonido suave de Caudal")
        sub.setProperty("sub", "1")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addStretch(1)
        bt_pos = QPushButton(f"Posponer {alarma.get('posponer', 9)} min")
        bt_pos.setMinimumHeight(46)
        bt_pos.clicked.connect(self.posponer.emit)
        v.addWidget(bt_pos)
        bt_apagar = QPushButton("Apagar")
        bt_apagar.setProperty("principal", "1")
        bt_apagar.setMinimumHeight(46)
        bt_apagar.clicked.connect(lambda: self.apagar.emit(False))
        v.addWidget(bt_apagar)
        if not sin_musica:
            bt_seguir = QPushButton("Apagar y seguir escuchando")
            bt_seguir.clicked.connect(lambda: self.apagar.emit(True))
            v.addWidget(bt_seguir)
        self._reloj = QTimer(self)
        self._reloj.setInterval(5000)
        self._reloj.timeout.connect(lambda: self.et_hora.setText(datetime.now().strftime("%H:%M")))
        self._reloj.start()

    def closeEvent(self, e):          # cerrar la ventana = posponer (nunca se pierde la alarma)
        if self.isVisible() and getattr(self, "_cerrando", False) is False:
            self._cerrando = True
            self.posponer.emit()
        super().closeEvent(e)

    def close(self):
        self._cerrando = True
        return super().close()


# ============================================================ lista y editor

class DialogoDespertador(QDialog):
    def __init__(self, gestor, padre=None):
        super().__init__(padre)
        self.g = gestor
        self.setWindowTitle("Despertador")
        self.setStyleSheet(_hoja())
        self.setMinimumSize(520, 520)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(10)
        t = QLabel("Despertador")
        t.setStyleSheet("font-size:24px;font-weight:900;")
        v.addWidget(t)
        self.et_proxima = QLabel("")
        self.et_proxima.setProperty("sub", "1")
        v.addWidget(self.et_proxima)
        aviso = QLabel("Suena con Caudal abierto (también en la bandeja) y la computadora despierta.")
        aviso.setProperty("sub", "1")
        aviso.setWordWrap(True)
        v.addWidget(aviso)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.contenido = QWidget()
        self.contenido.setObjectName("despertador")
        self.lista = QVBoxLayout(self.contenido)
        self.lista.setContentsMargins(0, 0, 0, 0)
        self.lista.setSpacing(8)
        self.area.setWidget(self.contenido)
        v.addWidget(self.area, 1)
        fila = QHBoxLayout()
        nueva = QPushButton("Nueva alarma")
        nueva.setProperty("principal", "1")
        nueva.clicked.connect(self._nueva)
        fila.addWidget(nueva)
        fila.addStretch(1)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.accept)
        fila.addWidget(cerrar)
        v.addLayout(fila)
        self._pintar()

    def _pintar(self):
        while self.lista.count():
            it = self.lista.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not self.g.alarmas:
            vacio = QLabel("Aún no tienes alarmas. Crea una y despierta con tu música.")
            vacio.setProperty("sub", "1")
            vacio.setWordWrap(True)
            self.lista.addWidget(vacio)
        for a in sorted(self.g.alarmas, key=lambda x: (x["hora"], x["minuto"])):
            self.lista.addWidget(self._fila(a))
        self.lista.addStretch(1)
        alarma, cuando = self.g.proxima()
        if alarma is None:
            self.et_proxima.setText("Ninguna alarma activa")
        else:
            self.et_proxima.setText(dsp.texto_falta((cuando - datetime.now()).total_seconds()))

    def _fila(self, a):
        f = QFrame()
        f.setObjectName("fila")
        h = QHBoxLayout(f)
        h.setContentsMargins(16, 10, 12, 10)
        col = QVBoxLayout()
        hora = QLabel(dsp.texto_hora(a))
        hora.setStyleSheet(f"font-size:28px;font-weight:900;color:{C['texto'] if a['activa'] else C['texto3']};")
        col.addWidget(hora)
        fuente = a.get("fuente") or {}
        detalle = QLabel(" · ".join(x for x in (a.get("etiqueta"), dsp.texto_dias(a["dias"]),
                                                fuente.get("titulo") or dsp.NOMBRE_TIPO.get(fuente.get("tipo"), ""))
                                    if x))
        detalle.setProperty("sub", "1")
        detalle.setWordWrap(True)
        col.addWidget(detalle)
        h.addLayout(col, 1)
        activa = QCheckBox()
        activa.setChecked(a["activa"])
        activa.setToolTip("Activar o apagar")
        activa.toggled.connect(lambda si, a=a: self._activar(a, si))
        h.addWidget(activa)
        editar = QPushButton("Editar")
        editar.clicked.connect(lambda _=False, a=a: self._editar(a))
        h.addWidget(editar)
        return f

    def _activar(self, a, si):
        a = dict(a, activa=si, pospuesta_hasta=0)
        self.g.poner(a)
        self._pintar()

    def _nueva(self):
        self._editar(dsp.nueva_alarma(), nueva=True)

    def _editar(self, a, nueva=False):
        ed = EditorAlarma(self.g, a, nueva, self)
        if ed.exec() == QDialog.Accepted:
            if ed.borrar:
                self.g.quitar(a["id"])
            else:
                guardada = self.g.poner(ed.resultado())
                p = dsp.proxima_vez(guardada)
                if p:
                    try:
                        self.g.ventana.aviso.mostrar(dsp.texto_falta((p - datetime.now()).total_seconds()))
                    except Exception:  # noqa: BLE001
                        pass
        self._pintar()


class EditorAlarma(QDialog):
    def __init__(self, gestor, alarma, nueva, padre=None):
        super().__init__(padre)
        self.g = gestor
        self.a = dsp.normalizar(alarma)
        self.borrar = False
        self.setWindowTitle("Nueva alarma" if nueva else "Editar alarma")
        self.setStyleSheet(_hoja())
        self.setMinimumWidth(480)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 18)
        v.setSpacing(10)

        self.hora = QTimeEdit(QTime(self.a["hora"], self.a["minuto"]))
        self.hora.setDisplayFormat("HH:mm")
        self.hora.setStyleSheet("font-size:30px;font-weight:900;")
        v.addWidget(self.hora)

        dias = QHBoxLayout()
        self.botones_dia = {}
        for d in dsp.DIAS:
            b = QPushButton(dsp.INICIAL_DIA[d])
            b.setProperty("dia", "1")
            b.setCheckable(True)
            b.setChecked(d in self.a["dias"])
            b.setToolTip(dsp.NOMBRE_DIA[d])
            dias.addWidget(b)
            self.botones_dia[d] = b
        dias.addStretch(1)
        v.addLayout(dias)
        sin = QLabel("Sin días marcados suena una sola vez.")
        sin.setProperty("sub", "1")
        v.addWidget(sin)

        self.etiqueta = QLineEdit(self.a["etiqueta"])
        self.etiqueta.setPlaceholderText("Nombre (opcional): «Trabajo», «Gimnasio»…")
        self.etiqueta.setMaxLength(40)
        v.addWidget(self.etiqueta)

        v.addWidget(QLabel("Qué suena"))
        self.tipo = QComboBox()
        for t in dsp.TIPOS:
            self.tipo.addItem(dsp.NOMBRE_TIPO[t], t)
        self.tipo.setCurrentIndex(max(0, list(dsp.TIPOS).index(self.a["fuente"]["tipo"])))
        v.addWidget(self.tipo)
        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Filtrar…")
        v.addWidget(self.buscar)
        self.opciones = QListWidget()
        self.opciones.setMinimumHeight(150)
        v.addWidget(self.opciones)
        self.tipo.currentIndexChanged.connect(self._cargar_opciones)
        self.buscar.textChanged.connect(self._filtrar)

        fila = QHBoxLayout()
        fila.addWidget(QLabel("Volumen"))
        self.volumen = QSlider(Qt.Horizontal)
        self.volumen.setRange(5, 100)
        self.volumen.setValue(self.a["volumen"])
        fila.addWidget(self.volumen, 1)
        self.et_vol = QLabel(f"{self.a['volumen']} %")
        self.volumen.valueChanged.connect(lambda x: self.et_vol.setText(f"{x} %"))
        fila.addWidget(self.et_vol)
        v.addLayout(fila)

        fila2 = QHBoxLayout()
        fila2.addWidget(QLabel("Llega a ese volumen en"))
        self.subida = QSpinBox()
        self.subida.setRange(0, 600)
        self.subida.setSingleStep(15)
        self.subida.setSuffix(" s")
        self.subida.setValue(self.a["subida"])
        fila2.addWidget(self.subida)
        fila2.addSpacing(16)
        fila2.addWidget(QLabel("Posponer"))
        self.posponer = QSpinBox()
        self.posponer.setRange(1, 60)
        self.posponer.setSuffix(" min")
        self.posponer.setValue(self.a["posponer"])
        fila2.addWidget(self.posponer)
        fila2.addStretch(1)
        v.addLayout(fila2)

        botones = QHBoxLayout()
        if not nueva:
            borrar = QPushButton("Borrar")
            borrar.clicked.connect(self._borrar)
            botones.addWidget(borrar)
        probar = QPushButton("Probar")
        probar.setToolTip("Suena ahora mismo, como sonará")
        probar.clicked.connect(lambda: self.g.sonar(self.resultado(), prueba=True))
        botones.addWidget(probar)
        botones.addStretch(1)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones.addWidget(cancelar)
        guardar = QPushButton("Guardar")
        guardar.setProperty("principal", "1")
        guardar.clicked.connect(self._guardar)
        botones.addWidget(guardar)
        v.addLayout(botones)
        self._cargar_opciones()

    # ------------------------------------------------------------ opciones de «qué suena»

    def _opciones_de(self, tipo):
        """[(texto, fuente)] de lo que se puede elegir para ese tipo."""
        col = self.g.ctx.coleccion
        try:
            if tipo == "cancion":
                vistas, salen = set(), []
                for p in (col.lista_me_gusta(limite=300) + col.descargadas(solo_audio=True)[:300]):
                    c = p.get("clave")
                    if not c or c in vistas:
                        continue
                    vistas.add(c)
                    texto = f"{p.get('titulo', '')} · {p.get('artista', '')}".strip(" ·")
                    salen.append((texto, {"tipo": "cancion", "id": c, "titulo": texto, "pista": _minima(p)}))
                return salen
            if tipo == "lista":
                return [(f"{l.get('nombre', '')}", {"tipo": "lista", "id": str(l.get("id")),
                                                     "titulo": l.get("nombre", "")})
                        for l in col.listas()]
            if tipo == "mix":
                from .. import mixes
                hoy, _c = mixes.guardados_de_hoy(col)
                return [(m.get("titulo", ""), {"tipo": "mix", "id": m.get("id"), "titulo": m.get("titulo", "")})
                        for m in hoy or []]
        except Exception:  # noqa: BLE001
            return []
        if tipo == "me_gusta":
            return [("Al azar de tus «me gusta»", {"tipo": "me_gusta", "id": "me_gusta",
                                                  "titulo": "Tus «me gusta»"})]
        return [("Sonido suave de Caudal (suena siempre, con o sin internet)",
                 {"tipo": "tono", "id": "tono", "titulo": "Sonido suave de Caudal"})]

    def _cargar_opciones(self):
        tipo = self.tipo.currentData()
        self.opciones.clear()
        elegida = self.a["fuente"] if self.a["fuente"].get("tipo") == tipo else None
        opciones = self._opciones_de(tipo)
        if tipo == "mix" and not opciones:
            opciones = []
            self.opciones.addItem(QListWidgetItem("Abre Inicio una vez hoy para que se armen tus mixes."))
        for texto, fuente in opciones:
            it = QListWidgetItem(texto)
            it.setData(Qt.UserRole, fuente)
            self.opciones.addItem(it)
            if elegida and str(elegida.get("id")) == str(fuente.get("id")):
                self.opciones.setCurrentItem(it)
        if self.opciones.currentItem() is None and self.opciones.count() and tipo in ("me_gusta", "tono"):
            self.opciones.setCurrentRow(0)
        self.buscar.setVisible(tipo in ("cancion", "lista"))
        self._filtrar(self.buscar.text())

    def _filtrar(self, texto):
        t = (texto or "").strip().lower()
        for i in range(self.opciones.count()):
            it = self.opciones.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    # ------------------------------------------------------------ resultado

    def resultado(self):
        it = self.opciones.currentItem()
        fuente = it.data(Qt.UserRole) if it is not None else None
        if not isinstance(fuente, dict):
            fuente = self.a["fuente"] if self.a["fuente"].get("tipo") == self.tipo.currentData() else \
                {"tipo": "tono", "id": "tono", "titulo": "Sonido suave de Caudal"}
        t = self.hora.time()
        return dsp.normalizar(dict(
            self.a, hora=t.hour(), minuto=t.minute(),
            dias=[d for d, b in self.botones_dia.items() if b.isChecked()],
            etiqueta=self.etiqueta.text().strip(), fuente=fuente, activa=True, pospuesta_hasta=0,
            volumen=self.volumen.value(), subida=self.subida.value(), posponer=self.posponer.value()))

    def _guardar(self):
        it = self.opciones.currentItem()
        if self.tipo.currentData() in ("cancion", "lista", "mix") and (it is None or not it.data(Qt.UserRole)):
            QMessageBox.information(self, "Despertador", "Elige qué quieres que suene en la lista de abajo.")
            return
        self.accept()

    def _borrar(self):
        self.borrar = True
        self.accept()


def _minima(p):
    """Lo justo de una pista para volver a sonarla (y que el archivo guardado no pese)."""
    claves = ("tipo", "clave", "video_id", "titulo", "artista", "artistas", "album", "duracion",
              "miniatura", "archivo", "es_audio", "es_video", "descarga_id", "url")
    return {k: p[k] for k in claves if k in p}
