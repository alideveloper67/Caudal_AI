# -*- coding: utf-8 -*-
"""Pantalla «Modo gamer»: nivel y misiones, mini reproductor, atajos, ahorro al jugar,
sonido por juego, bajar la musica al hablar, listas por situacion y «Ahora suena» para OBS."""

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QKeySequence, QPainter
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QKeySequenceEdit,
                               QLabel, QLineEdit, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget)

from ... import modo_gamer as MG
from .. import iconos
from ..componentes import Pagina
from ..estilos import C
from ..neon_gamer import MarcoNeon, color_neon, reloj_neon


class _Barra(QWidget):
    """Barra fina de progreso; con el neon encendido el relleno cambia de color."""

    def __init__(self, alto=10, padre=None):
        super().__init__(padre)
        self.valor = 0.0
        self.setFixedHeight(alto)

    def poner(self, v):
        self.valor = max(0.0, min(1.0, float(v)))
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())
        rad = r.height() / 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 28))
        p.drawRoundedRect(r, rad, rad)
        if self.valor > 0:
            neon = reloj_neon().encendido
            p.setBrush(color_neon(reloj_neon().fase, 0.0, 0.7, 1.0) if neon else QColor(C["acento"]))
            p.drawRoundedRect(QRectF(r.left(), r.top(), max(r.height(), r.width() * self.valor), r.height()),
                              rad, rad)


class _BarraNeon(_Barra):
    """La barra de XP se anota en el reloj neon para repintarse con el."""

    def showEvent(self, e):
        reloj_neon().registrar(self)
        super().showEvent(e)

    def hideEvent(self, e):
        super().hideEvent(e)
        reloj_neon().refrescar()


def _texto(t, estilo="", envolver=True):
    """Etiqueta que se parte en lineas y no obliga a la pagina a ser ancha."""
    e = QLabel(t)
    e.setStyleSheet("background:transparent;" + estilo)
    if envolver:
        e.setWordWrap(True)
        e.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    return e


class _Seccion(QFrame):
    def __init__(self, titulo, ayuda=""):
        super().__init__()
        self.setObjectName("caja")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(22, 18, 22, 14)
        self.v.setSpacing(8)
        self.v.addWidget(_texto(titulo, "font-size:18px;font-weight:800;"))
        if ayuda:
            a = _texto(ayuda, f"color:{C['texto2']};font-size:12.5px;")
            a.setWordWrap(True)
            self.v.addWidget(a)

    def fila(self, titulo, ayuda, widget):
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(18)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(_texto(titulo, "font-size:14px;font-weight:600;"))
        if ayuda:
            a = _texto(ayuda, f"color:{C['texto3']};font-size:12px;")
            a.setWordWrap(True)
            col.addWidget(a)
            caja.ayuda = a
        h.addLayout(col, 1)
        if widget is not None:
            h.addWidget(widget, 0, Qt.AlignVCenter | Qt.AlignRight)
        self.v.addWidget(caja)
        return caja


def _interruptor(v):
    c = QCheckBox()
    c.setChecked(bool(v))
    c.setCursor(Qt.PointingHandCursor)
    return c


def _chip(texto, ayuda=""):
    b = QPushButton(texto)
    b.setObjectName("chip")
    b.setCheckable(True)
    b.setCursor(Qt.PointingHandCursor)
    b.setToolTip(ayuda)
    return b


class PaginaModoGamer(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre)
        self.titulo = "Modo gamer"
        self.g = ctx.gamer
        self.cfg = self.g.cfg
        self.cuerpo.setSpacing(16)
        self._cargando = True

        self._cabecera()
        self._seccion_nivel()
        self._seccion_mini()
        self._seccion_atajos()
        self._seccion_ahorro()
        self._seccion_sonido()
        self._seccion_hablar()
        self._seccion_listas()
        self._seccion_obs()
        self.cuerpo.addStretch(1)

        self.g.cambio.connect(self._refrescar)
        self.g.progreso_cambio.connect(self._refrescar_nivel)
        self.g.atajos_cambio.connect(self._refrescar_atajos)
        self.g.ahorro_cambio.connect(lambda *_a: self._refrescar_ahorro())
        self._cargando = False
        self._refrescar()
        self._refrescar_nivel()
        self._refrescar_atajos()

    # ------------------------------------------------------------ cabecera

    def _cabecera(self):
        marco = MarcoNeon(22, 2.4)
        v = QVBoxLayout(marco)
        v.setContentsMargins(26, 22, 26, 20)
        v.setSpacing(14)
        h = QHBoxLayout()
        h.setSpacing(18)
        ic = QLabel()
        ic.setStyleSheet("background:transparent;")
        ic.setPixmap(iconos.pixmap("mando", 44, C["acento"]))
        h.addWidget(ic, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        t = _texto("Modo gamer", "font-size:30px;font-weight:900;")
        t.setObjectName("titulo_pagina")
        col.addWidget(t)
        sub = _texto("Música a mano mientras juegas: atajos que funcionan desde el juego, un mini "
                     "reproductor flotante, ahorro de recursos y mucho más.",
                     f"color:{C['texto2']};font-size:13px;")
        sub.setWordWrap(True)
        col.addWidget(sub)
        h.addLayout(col, 1)
        v.addLayout(h)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.sw_activo = _interruptor(self.cfg["activo"])
        self.sw_activo.toggled.connect(lambda si: not self._cargando and self.g.activar(si))
        fila.addWidget(self.sw_activo)
        txt = QVBoxLayout()
        txt.setSpacing(0)
        txt.addWidget(_texto("Modo gamer activado", "font-size:14px;font-weight:700;"))
        self.et_activo = _texto("", f"color:{C['texto3']};font-size:11.5px;")
        txt.addWidget(self.et_activo)
        fila.addLayout(txt, 1)
        self.sw_neon = QCheckBox("Neón RGB")
        self.sw_neon.setChecked(bool(self.cfg["neon"]))
        self.sw_neon.setCursor(Qt.PointingHandCursor)
        self.sw_neon.toggled.connect(lambda si: not self._cargando and self.g.fijar_neon(si))
        fila.addWidget(self.sw_neon, 0, Qt.AlignRight)
        v.addLayout(fila)
        self.cuerpo.addWidget(marco)

    # ------------------------------------------------------------ nivel y misiones

    def _seccion_nivel(self):
        marco = MarcoNeon(22, 1.6)
        v = QVBoxLayout(marco)
        v.setContentsMargins(26, 20, 26, 20)
        v.setSpacing(8)
        fila = QHBoxLayout()
        self.et_nivel = _texto("", "font-size:24px;font-weight:900;", False)
        fila.addWidget(self.et_nivel)
        fila.addStretch(1)
        self.et_racha = _texto("", f"color:{C['texto2']};font-size:13px;font-weight:600;")
        self.et_racha.setWordWrap(True)
        fila.addWidget(self.et_racha, 1)
        self.et_racha.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v.addLayout(fila)
        self.barra_xp = _BarraNeon(12)
        v.addWidget(self.barra_xp)
        self.et_xp = _texto("", f"color:{C['texto3']};font-size:12px;")
        self.et_xp.setWordWrap(True)
        v.addWidget(self.et_xp)
        v.addSpacing(6)
        v.addWidget(_texto("Misiones de hoy", "font-size:15px;font-weight:800;"))
        self.filas_misiones = []
        for _ in range(3):
            caja = QWidget()
            col = QVBoxLayout(caja)
            col.setContentsMargins(0, 4, 0, 4)
            col.setSpacing(4)
            h = QHBoxLayout()
            h.setSpacing(10)
            tx = _texto("", "font-size:13.5px;font-weight:600;")
            h.addWidget(tx, 1)
            est = _texto("", f"color:{C['texto2']};font-size:12px;", False)
            est.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(est)
            col.addLayout(h)
            barra = _Barra(6)
            col.addWidget(barra)
            v.addWidget(caja)
            self.filas_misiones.append((tx, barra, est))
        nota = _texto("1 XP por cada minuto escuchado. Con 10 minutos al día sigues tu racha. "
                      "Se guarda solo en esta PC.", f"color:{C['texto3']};font-size:11.5px;")
        nota.setWordWrap(True)
        v.addWidget(nota)
        self.cuerpo.addWidget(marco)

    def _refrescar_nivel(self):
        pr = self.g.progreso
        n, dentro, largo, rango = MG.info_nivel(pr.xp)
        self.et_nivel.setText(f"Nivel {n} · {rango}")
        self.barra_xp.poner(dentro / largo if largo else 0)
        self.et_xp.setText(f"{dentro} / {largo} XP para el nivel {n + 1}   ·   {pr.xp} XP en total")
        racha = pr.racha()
        self.et_racha.setText(f"Racha: {racha} día{'s' if racha != 1 else ''}"
                              + (f"  ·  récord {pr.d['mejor_racha']}" if pr.d["mejor_racha"] > racha else ""))
        for (tx, barra, est), m in zip(self.filas_misiones, pr.misiones()):
            tx.setText(m["texto"])
            barra.poner(m["actual"] / m["meta"])
            est.setText("Hecha  +%d XP" % m["xp"] if m["hecha"] else f"{m['actual']} / {m['meta']}")
            est.setStyleSheet(f"background:transparent;font-size:12px;color:"
                              f"{C['exito'] if m['hecha'] else C['texto2']};")

    # ------------------------------------------------------------ mini reproductor

    def _seccion_mini(self):
        s = _Seccion("Mini reproductor", "Una ventanita flotante, siempre encima y sin quitarle el foco "
                     "al juego. Se arrastra desde cualquier parte y recuerda su sitio. Se ve sobre "
                     "juegos en ventana o ventana sin bordes (no sobre los de pantalla completa exclusiva).")
        self.bt_mini = QPushButton("Mostrar")
        self.bt_mini.setObjectName("contorno")
        self.bt_mini.setCursor(Qt.PointingHandCursor)
        self.bt_mini.clicked.connect(self.g.alternar_mini)
        s.fila("Mini reproductor", "Carátula, título, reproducir/pausa, siguiente y volumen", self.bt_mini)
        self.sl_opacidad = QSlider(Qt.Horizontal)
        self.sl_opacidad.setRange(35, 100)
        self.sl_opacidad.setFixedWidth(120)
        self.sl_opacidad.setValue(int(self.cfg["mini_opacidad"]))
        self.sl_opacidad.valueChanged.connect(self._opacidad)
        s.fila("Transparencia", "Más a la izquierda, más transparente", self.sl_opacidad)
        self.sw_clics = _interruptor(self.cfg["mini_clics"])
        self.sw_clics.toggled.connect(lambda si: not self._cargando and self.g.fijar_clics(si))
        self.fila_clics = s.fila("Dejar pasar los clics", "La ventanita deja de recibir el ratón", self.sw_clics)
        self.cuerpo.addWidget(s)

    def _opacidad(self, v):
        if self._cargando:
            return
        if self.g._mini is not None:
            self.g._mini.poner_opacidad(v)
        else:
            self.cfg["mini_opacidad"] = int(v)
            self.cfg.guardar()

    # ------------------------------------------------------------ atajos

    def _seccion_atajos(self):
        s = _Seccion("Atajos de teclado", "Funcionan en todo Windows, también dentro de un juego. "
                     "Todos llevan Ctrl, Alt o Win para no chocar con las teclas del juego.")
        self.editores = {}
        self.estados = {}
        for accion, nombre in MG.ACCIONES:
            caja = QWidget()
            h = QHBoxLayout(caja)
            h.setContentsMargins(0, 3, 0, 3)
            h.setSpacing(12)
            izq = QVBoxLayout()
            izq.setSpacing(0)
            nom = _texto(nombre, "font-size:13.5px;font-weight:600;")
            nom.setWordWrap(True)
            nom.setMinimumWidth(80)
            izq.addWidget(nom)
            est = _texto("", f"color:{C['error']};font-size:11.5px;")
            est.setWordWrap(True)
            est.hide()
            izq.addWidget(est)
            h.addLayout(izq, 1)
            ed = QKeySequenceEdit()
            ed.setMaximumSequenceLength(1)
            ed.setFixedWidth(130)
            ed.editingFinished.connect(lambda a=accion, e=ed: self._cambiar_atajo(a, e))
            h.addWidget(ed)
            s.v.addWidget(caja)
            self.editores[accion] = ed
            self.estados[accion] = est
        fila = QHBoxLayout()
        self.msg_atajos = _texto("", f"color:{C['aviso']};font-size:12px;")
        self.msg_atajos.setWordWrap(True)
        fila.addWidget(self.msg_atajos, 1)
        b = QPushButton("Restaurar atajos")
        b.setObjectName("contorno")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(self.g.restaurar_atajos)
        fila.addWidget(b)
        s.v.addLayout(fila)
        self.cuerpo.addWidget(s)

    def _cambiar_atajo(self, accion, editor):
        if self._cargando:
            return
        texto = editor.keySequence().toString(QKeySequence.PortableText)
        ok, msg = self.g.fijar_atajo(accion, texto)
        self.msg_atajos.setText("" if ok else msg)
        if not ok:
            self._refrescar_atajos()

    def _refrescar_atajos(self):
        antes = self._cargando
        self._cargando = True
        for accion, ed in self.editores.items():
            ed.setKeySequence(QKeySequence(self.cfg["atajos"].get(accion, "")))
            motivo = self.g.fallidos.get(accion, "") if self.g.activo else ""
            self.estados[accion].setText(motivo)
            self.estados[accion].setVisible(bool(motivo))
        self._cargando = antes

    # ------------------------------------------------------------ ahorro

    def _seccion_ahorro(self):
        s = _Seccion("Ahorro al jugar", "Si una app está a pantalla completa en primer plano, Caudal "
                     "pausa la mascota, el personaje del fondo y los visualizadores, y baja su "
                     "prioridad para dejarle todo el equipo al juego. Al salir, todo vuelve.")
        self.sw_ahorro = _interruptor(self.cfg["ahorro"])
        self.sw_ahorro.toggled.connect(lambda si: not self._cargando and self.g.fijar_ahorro(si))
        s.fila("Ahorrar recursos al detectar un juego", "Se mira cada 3 segundos; cuesta casi nada",
               self.sw_ahorro)
        self.et_ahorro = _texto("", f"color:{C['texto2']};font-size:12.5px;font-weight:600;")
        s.v.addWidget(self.et_ahorro)
        self.ed_ignorar = QLineEdit()
        self.ed_ignorar.setFixedWidth(200)
        self.ed_ignorar.setPlaceholderText("chrome.exe, vlc.exe")
        self.ed_ignorar.editingFinished.connect(self._guardar_ignorar)
        s.fila("Apps que no cuentan como juego", "Nombres de programa separados por comas (por ejemplo "
               "un navegador en pantalla completa)", self.ed_ignorar)
        self.cuerpo.addWidget(s)

    def _guardar_ignorar(self):
        if self._cargando:
            return
        self.cfg["ignorar"] = [x.strip().lower() for x in self.ed_ignorar.text().split(",") if x.strip()]
        self.cfg.guardar()

    def _refrescar_ahorro(self):
        if self.g.ahorrando:
            n = f" ({self.g.juego})" if self.g.juego else ""
            self.et_ahorro.setText(f"Ahora: jugando{n}. Caudal está en modo ahorro.")
        elif not self.g.activo:
            self.et_ahorro.setText("Activa el Modo gamer arriba para que se vigile.")
        elif not self.cfg["ahorro"]:
            self.et_ahorro.setText("Apagado.")
        else:
            self.et_ahorro.setText("Ahora: normal. Esperando a que abras un juego.")

    # ------------------------------------------------------------ sonido

    def _seccion_sonido(self):
        s = _Seccion("Sonido por tipo de juego", "Usa el ecualizador de Caudal. «Restaurar» devuelve "
                     "tu sonido de antes.")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(8)
        self.chips_sonido = {}
        for i, (clave, p) in enumerate(MG.PRESETS_SONIDO.items()):
            b = _chip(p["nombre"], p["ayuda"])
            b.clicked.connect(lambda _c=False, k=clave: self.g.aplicar_preset(k))
            rejilla.addWidget(b, i // 2, i % 2)
            self.chips_sonido[clave] = b
        s.v.addLayout(rejilla)
        r = QPushButton("Restaurar mi sonido")
        r.setObjectName("contorno")
        r.setCursor(Qt.PointingHandCursor)
        r.clicked.connect(self.g.restaurar_sonido)
        s.v.addWidget(r, 0, Qt.AlignLeft)
        self.et_sonido = _texto("", f"color:{C['texto3']};font-size:12px;")
        self.et_sonido.setWordWrap(True)
        s.v.addWidget(self.et_sonido)
        self.cuerpo.addWidget(s)

    # ------------------------------------------------------------ hablar

    def _seccion_hablar(self):
        s = _Seccion("Bajar la música al hablar", "Mantén el atajo «Hablar» y la música baja con una "
                     "rampa suave; al soltarlo, vuelve a tu volumen. No cambia tu volumen guardado.")
        self.sl_hablar = QSlider(Qt.Horizontal)
        self.sl_hablar.setRange(5, 80)
        self.sl_hablar.setFixedWidth(120)
        self.sl_hablar.setValue(int(self.cfg["hablar_nivel"]))
        self.et_hablar = _texto("", f"color:{C['texto2']};font-size:12.5px;font-weight:600;", False)
        self.et_hablar.setFixedWidth(46)
        self.sl_hablar.valueChanged.connect(self._nivel_hablar)
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.sl_hablar)
        h.addWidget(self.et_hablar)
        s.fila("Volumen mientras hablas", "Porcentaje del volumen actual", caja)
        self.cuerpo.addWidget(s)

    def _nivel_hablar(self, v):
        self.et_hablar.setText(f"{v} %")
        if not self._cargando:
            self.cfg["hablar_nivel"] = int(v)
            self.cfg.guardar()

    # ------------------------------------------------------------ listas

    def _seccion_listas(self):
        s = _Seccion("Listas por situación", "Mezclas buscadas en YouTube Music para cada momento de "
                     "la partida.")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(8)
        self.botones_listas = {}
        for i, (clave, p) in enumerate(MG.SITUACIONES.items()):
            b = QPushButton(p["nombre"])
            b.setObjectName("contorno")
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(p["ayuda"])
            b.clicked.connect(lambda _c=False, k=clave: self._poner_lista(k))
            rejilla.addWidget(b, i // 2, i % 2)
            self.botones_listas[clave] = b
        s.v.addLayout(rejilla)
        self.cuerpo.addWidget(s)

    def _poner_lista(self, clave):
        b = self.botones_listas[clave]
        b.setEnabled(False)

        def fin(_ok):
            try:
                b.setEnabled(True)
            except RuntimeError:
                pass
        self.g.reproducir_situacion(clave, fin)

    # ------------------------------------------------------------ OBS

    def _seccion_obs(self):
        s = _Seccion("«Ahora suena» para OBS")
        aviso = QFrame()
        aviso.setObjectName("aviso_derechos")
        aviso.setStyleSheet(f"QFrame#aviso_derechos{{background:rgba(245,165,36,0.12);"
                            f"border:1px solid {C['aviso']};border-radius:12px;}}")
        ha = QVBoxLayout(aviso)
        ha.setContentsMargins(14, 10, 14, 10)
        self.et_derechos = _texto("Atención: " + MG.AVISO_DERECHOS, f"color:{C['texto']};font-size:12.5px;")
        self.et_derechos.setWordWrap(True)
        ha.addWidget(self.et_derechos)
        s.v.addWidget(aviso)
        self.sw_obs = _interruptor(self.cfg["obs"])
        self.sw_obs.toggled.connect(lambda si: not self._cargando and self.g.fijar_obs(activo=si))
        s.fila("Escribir la canción actual", "Un archivo ahora_suena.txt que OBS lee con una fuente de "
               "texto. Solo escribe con el Modo gamer activado.", self.sw_obs)
        self.sw_html = _interruptor(self.cfg["obs_html"])
        self.sw_html.toggled.connect(lambda si: not self._cargando and self.g.fijar_obs(con_html=si))
        s.fila("También una página HTML", "ahora_suena.html se recarga sola cada 2 segundos "
               "(fuente de navegador local de OBS)", self.sw_html)
        caja = QWidget()
        h = QHBoxLayout(caja)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        b1 = QPushButton("Cambiar…")
        b1.setObjectName("contorno")
        b1.setCursor(Qt.PointingHandCursor)
        b1.clicked.connect(self._elegir_carpeta)
        b2 = QPushButton("Abrir")
        b2.setObjectName("contorno")
        b2.setCursor(Qt.PointingHandCursor)
        b2.clicked.connect(self._abrir_carpeta)
        h.addWidget(b1)
        h.addWidget(b2)
        s.fila("Carpeta", "Dónde se guardan los archivos", caja)
        self.et_carpeta = QLineEdit()           # una ruta larga no se parte en lineas: se desplaza
        self.et_carpeta.setReadOnly(True)
        self.et_carpeta.setToolTip("Carpeta donde se escribe ahora_suena.txt")
        s.v.addWidget(self.et_carpeta)
        self.cuerpo.addWidget(s)

    def _elegir_carpeta(self):
        ruta = QFileDialog.getExistingDirectory(self, "Carpeta para «Ahora suena»", self.g.carpeta_obs())
        if ruta:
            self.g.fijar_obs(carpeta=ruta)

    def _abrir_carpeta(self):
        ruta = self.g.carpeta_obs()
        try:
            os.makedirs(ruta, exist_ok=True)
            os.startfile(ruta)
        except (OSError, AttributeError):
            pass

    # ------------------------------------------------------------ sincronizar con los ajustes

    def _refrescar(self):
        antes = self._cargando
        self._cargando = True
        self.sw_activo.setChecked(bool(self.cfg["activo"]))
        self.et_activo.setText("Atajos y vigilancia en marcha" if self.cfg["activo"] else "Apagado")
        self.sw_neon.setChecked(bool(self.cfg["neon"]))
        visible = self.g._mini is not None and self.g._mini.isVisible()
        self.bt_mini.setText("Ocultar" if visible else "Mostrar")
        self.sw_clics.setChecked(bool(self.cfg["mini_clics"]))
        self.sl_opacidad.setValue(int(self.cfg["mini_opacidad"]))
        self.sw_ahorro.setChecked(bool(self.cfg["ahorro"]))
        self.ed_ignorar.setText(", ".join(self.cfg["ignorar"]))
        self.sl_hablar.setValue(int(self.cfg["hablar_nivel"]))
        self.et_hablar.setText(f"{self.cfg['hablar_nivel']} %")
        self.sw_obs.setChecked(bool(self.cfg["obs"]))
        self.sw_html.setChecked(bool(self.cfg["obs_html"]))
        self.et_carpeta.setText(self.g.carpeta_obs())
        for clave, b in self.chips_sonido.items():
            b.setChecked(self.cfg["sonido_gamer"] == clave)
        self.et_sonido.setText("Sonido puesto: " + MG.PRESETS_SONIDO[self.cfg["sonido_gamer"]]["nombre"]
                               if self.cfg["sonido_gamer"] else "Usando tu sonido de siempre.")
        atajo_clics = self.cfg["atajos"].get("clics", "")
        self.fila_clics.ayuda.setText(
            f"La ventanita deja de recibir el ratón y se maneja con {atajo_clics}")
        self._cargando = antes
        self._refrescar_ahorro()
        self._refrescar_atajos()
