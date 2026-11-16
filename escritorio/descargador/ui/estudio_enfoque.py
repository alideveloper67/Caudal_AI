# -*- coding: utf-8 -*-
"""«Cero distracciones»: la vista minimalista del modo estudio.

Cubre toda la ventana con lo justo: el temporizador grande, reproducir/pausar, siguiente,
volumen, el mezclador de sonidos y las notas. Sin portadas llamativas, letras ni feeds.
Con el «modo cálido» baja el brillo y tiñe todo de ámbar suave, con poco contraste.
"""

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QRadialGradient
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from .. import estudio as E
from . import iconos
from .componentes import Deslizador, fuente
from .estilos import FUENTE_TITULO, C
from .estudio_piezas import (BotonRedondo, ConfirmaSalida, PanelMezcla, PanelNotas, con_alfa,
                             icono_estudio, mezclar)
from .paginas.estudio import BarraFina

AMBAR = "#E8D3B0"          # el tono del texto en modo cálido
AMBAR_2 = "#B09874"
AMBAR_3 = "#7D6B52"
FONDO_CALIDO = "#17100A"
LUZ_CALIDA = "#2A1C10"


def confirmar_salida(padre, ctrl, accion):
    """Muestra «¿Salir de tu sesión de estudio?» sobre `padre`. «Salir» termina la sesión
    (se guarda lo estudiado) y luego hace `accion`; «Seguir estudiando» no cambia nada."""
    previo = getattr(padre, "_confirma_estudio", None)
    if previo is not None:
        try:
            if previo.isVisible():
                return previo
        except RuntimeError:
            pass
    estudiado = E.formato_duracion(ctrl.temporizador.enfocado_total())
    resumen = ("Llevas " + estudiado + " de enfoque. Si sales ahora, se guarda lo que ya "
               "estudiaste." if ctrl.temporizador.enfocado_total() >= 60 else
               "Tienes un bloque en curso. Si sales ahora, termina tu sesión.")
    c = ConfirmaSalida(padre, candado=ctrl.cfg["candado"], resumen=resumen)
    padre._confirma_estudio = c

    def soltar():
        padre._confirma_estudio = None
        c.cerrar()

    def salir():
        soltar()
        ctrl.terminar()
        if accion:
            accion()
    c.seguir.connect(soltar)
    c.salir.connect(salir)
    c.setFocus()
    return c


class Velo(QWidget):
    """Tinte ámbar encima de todo: multiplica los colores (baja brillo y contraste)."""

    def __init__(self, padre):
        super().__init__(padre)
        self.t = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

    def poner(self, t):
        self.t = max(0.0, min(1.0, float(t)))
        self.setVisible(self.t > 0.001)
        self.update()

    def paintEvent(self, _e):
        if self.t <= 0.001:
            return
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode_Multiply)
        base = mezclar("#FFFFFF", "#FFC890", self.t)
        oscuro = 1.0 - 0.34 * self.t
        base = QColor(round(base.red() * oscuro), round(base.green() * oscuro),
                      round(base.blue() * oscuro))
        p.fillRect(self.rect(), base)


class VistaEnfoque(QWidget):
    def __init__(self, ctx, padre, ctrl=None):
        super().__init__(padre)
        self.ctx = ctx
        self.ctrl = ctrl or E.de(ctx)
        self.r = self.ctrl.r
        self.setObjectName("enfoque")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAutoFillBackground(False)
        self._pantalla_antes = None
        self._popover = None
        self._construir()
        self.panel_notas = PanelNotas(self.ctrl, self)
        self.panel_notas.cerrado.connect(lambda: self.bt_notas.set_activo(False))
        self.velo = Velo(self)
        self.velo.hide()
        c = self.ctrl
        c.cambio.connect(self._refrescar)
        c.tic.connect(self._refrescar_reloj)
        c.aviso.connect(self._aviso)
        if self.r is not None:
            self.r.estado_cambio.connect(self._estado_musica)
            self.r.pista_cambio.connect(self._pista)
        self._reloj = QTimer(self)
        self._reloj.setInterval(1000)
        self._reloj.timeout.connect(self._refrescar_reloj)
        padre.installEventFilter(self)
        self.hide()

    # ---------------------------------------------------------------- construcción
    def _construir(self):
        v = QVBoxLayout(self)
        v.setContentsMargins(40, 30, 40, 34)
        v.setSpacing(0)
        # ---- arriba
        top = QHBoxLayout()
        top.setSpacing(10)
        self.ic_marca = QLabel()
        self.ic_marca.setFixedSize(22, 22)
        top.addWidget(self.ic_marca)
        self.et_sesion = QLabel("")
        self.et_sesion.setObjectName("e_sesion")
        top.addWidget(self.et_sesion)
        top.addStretch(1)
        self.bt_calido = BotonRedondo("luna", 40, 19, "Modo cálido: menos brillo, tono ámbar")
        self.bt_calido.clicked.connect(self._alternar_calido)
        top.addWidget(self.bt_calido)
        self.brillo = Deslizador(18)
        self.brillo.setFixedWidth(120)
        self.brillo.setToolTip("Brillo cálido")
        self.brillo.setAccessibleName("Brillo cálido")
        self.brillo.movido.connect(self._brillo)
        self.brillo.soltado.connect(self._brillo)
        top.addWidget(self.brillo)
        self.et_brillo = QLabel("Brillo cálido")
        self.et_brillo.setObjectName("e_ayuda")
        top.addWidget(self.et_brillo)
        top.addSpacing(8)
        self.bt_despierto = BotonRedondo("ojo", 40, 19, "Mantener el equipo despierto")
        self.bt_despierto.clicked.connect(self._alternar_despierto)
        top.addWidget(self.bt_despierto)
        self.bt_pantalla = BotonRedondo("pantalla", 40, 19, "Pantalla completa")
        self.bt_pantalla.clicked.connect(self.alternar_pantalla)
        top.addWidget(self.bt_pantalla)
        self.bt_cerrar = BotonRedondo("cerrar", 40, 18, "Salir de esta vista (Esc)")
        self.bt_cerrar.clicked.connect(self.pedir_salida)
        top.addWidget(self.bt_cerrar)
        v.addLayout(top)
        v.addStretch(5)
        # ---- el temporizador
        centro = QVBoxLayout()
        centro.setSpacing(0)
        centro.setAlignment(Qt.AlignHCenter)
        self.et_fase = QLabel("")
        self.et_fase.setObjectName("e_fase")
        self.et_fase.setAlignment(Qt.AlignCenter)
        centro.addWidget(self.et_fase)
        centro.addSpacing(6)
        self.et_tiempo = QLabel("25:00")
        self.et_tiempo.setObjectName("e_tiempo")
        self.et_tiempo.setAlignment(Qt.AlignCenter)
        self.et_tiempo.setFont(fuente(150, QFont.Light, True))
        centro.addWidget(self.et_tiempo)
        centro.addSpacing(10)
        self.barra = BarraFina(4)
        self.barra.setFixedWidth(380)
        centro.addWidget(self.barra, 0, Qt.AlignHCenter)
        centro.addSpacing(26)
        enlaces = QHBoxLayout()
        enlaces.setAlignment(Qt.AlignHCenter)
        enlaces.setSpacing(6)
        self.bt_pausa = self._enlace("Pausar el bloque", self.ctrl.pausar_o_reanudar)
        self.bt_saltar = self._enlace("Saltar el descanso", self.ctrl.saltar_fase)
        self.bt_iniciar = self._enlace("Empezar un bloque", lambda: self.ctrl.empezar())
        for b in (self.bt_pausa, self.bt_saltar, self.bt_iniciar):
            enlaces.addWidget(b)
        centro.addLayout(enlaces)
        centro.addSpacing(18)
        self.et_aviso = QLabel("")
        self.et_aviso.setObjectName("e_aviso")
        self.et_aviso.setAlignment(Qt.AlignCenter)
        self.et_aviso.setWordWrap(True)
        self.et_aviso.setFixedWidth(560)
        self.et_aviso.setMinimumHeight(46)
        self.efecto_aviso = QGraphicsOpacityEffect(self.et_aviso)
        self.efecto_aviso.setOpacity(0.0)
        self.et_aviso.setGraphicsEffect(self.efecto_aviso)
        centro.addWidget(self.et_aviso, 0, Qt.AlignHCenter)
        v.addLayout(centro)
        v.addStretch(6)
        # ---- controles
        ctl = QHBoxLayout()
        ctl.setSpacing(14)
        ctl.setAlignment(Qt.AlignHCenter)
        self.bt_play = BotonRedondo("reproducir", 66, 26, "Reproducir o pausar la música", relleno=True)
        self.bt_play.clicked.connect(self._play)
        self.bt_sig = BotonRedondo("siguiente", 48, 20, "Siguiente canción")
        self.bt_sig.clicked.connect(self._siguiente)
        ctl.addWidget(self.bt_play)
        ctl.addWidget(self.bt_sig)
        ctl.addSpacing(22)
        self.ic_vol = QLabel()
        self.ic_vol.setFixedSize(22, 22)
        ctl.addWidget(self.ic_vol)
        self.vol = Deslizador(20)
        self.vol.setFixedWidth(150)
        self.vol.setToolTip("Volumen de la música")
        self.vol.setAccessibleName("Volumen de la música")
        self.vol.movido.connect(self._volumen)
        self.vol.soltado.connect(self._volumen)
        ctl.addWidget(self.vol)
        ctl.addSpacing(22)
        self.bt_mezcla = BotonRedondo("lluvia", 48, 22, "Mezclador de sonidos")
        self.bt_mezcla.clicked.connect(self.alternar_mezcla)
        self.bt_notas = BotonRedondo("idea", 48, 22, "Captura de ideas (Ctrl+Shift+N)")
        self.bt_notas.clicked.connect(self.alternar_notas)
        ctl.addWidget(self.bt_mezcla)
        ctl.addWidget(self.bt_notas)
        v.addLayout(ctl)
        v.addSpacing(20)
        self.et_ahora = QLabel("")
        self.et_ahora.setObjectName("e_ahora")
        self.et_ahora.setAlignment(Qt.AlignCenter)
        v.addWidget(self.et_ahora)
        # ---- el mezclador, como panel emergente
        self.caja_mezcla = QFrame(self)
        self.caja_mezcla.setObjectName("e_mezcla")
        self.caja_mezcla.setFixedWidth(430)
        lm = QVBoxLayout(self.caja_mezcla)
        lm.setContentsMargins(24, 20, 24, 18)
        lm.setSpacing(10)
        cab = QHBoxLayout()
        t = QLabel("Sonidos y música")
        t.setStyleSheet("font-size:16px;font-weight:800;background:transparent;")
        cab.addWidget(t)
        cab.addStretch(1)
        lm.addLayout(cab)
        self.mezcla = PanelMezcla(self.ctrl, compacto=True)
        lm.addWidget(self.mezcla)
        self.caja_mezcla.hide()

    def _enlace(self, texto, accion):
        b = QPushButton(texto)
        b.setObjectName("e_enlace")
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        b.clicked.connect(lambda _=False: accion())
        return b

    # ---------------------------------------------------------------- aspecto
    def tinte(self):
        cfg = self.ctrl.cfg
        return (cfg["brillo"] / 100.0) if cfg["calido"] else 0.0

    def _aplicar_aspecto(self):
        t = self.tinte()
        texto = mezclar(C["texto"], AMBAR, t * 0.9).name()
        texto2 = mezclar(C["texto2"], AMBAR_2, t).name()
        texto3 = mezclar(C["texto3"], AMBAR_3, t).name()
        acento = mezclar(C["acento"], "#F2B979", t).name()
        self.setStyleSheet(
            f"QLabel#e_sesion{{color:{texto2};font-size:13.5px;font-weight:600;background:transparent;}}"
            f"QLabel#e_fase{{color:{acento};font-size:13px;font-weight:700;letter-spacing:2px;"
            "background:transparent;}"
            f"QLabel#e_tiempo{{color:{texto};background:transparent;font-size:150px;font-weight:200;"
            f"font-family:{FUENTE_TITULO};}}"
            f"QLabel#e_ayuda{{color:{texto3};font-size:12px;background:transparent;}}"
            f"QLabel#e_ahora{{color:{texto3};font-size:13.5px;background:transparent;}}"
            f"QLabel#e_aviso{{color:{texto};font-size:14px;background:rgba(255,255,255,16);"
            "border-radius:22px;padding:11px 24px;}"
            f"QPushButton#e_enlace{{background:transparent;border:none;color:{texto2};font-size:13.5px;"
            "font-weight:600;padding:6px 14px;border-radius:14px;}"
            f"QPushButton#e_enlace:hover{{color:{texto};background:rgba(255,255,255,14);}}"
            f"QFrame#e_mezcla{{background:{C['panel']};border:1px solid {C['borde_claro']};"
            "border-radius:22px;}")
        self.ic_marca.setPixmap(icono_estudio("hoja", 20, acento))
        self.ic_vol.setPixmap(iconos.pixmap("altavoz_fuerte", 20, texto2))
        self.velo.poner(t)
        for b in (self.bt_calido, self.bt_despierto, self.bt_mezcla, self.bt_notas):
            b.color_activo = acento
        self.bt_calido.set_activo(self.ctrl.cfg["calido"])
        self.bt_despierto.set_activo(self.ctrl.cfg["despierto"])
        self.brillo.setVisible(bool(self.ctrl.cfg["calido"]))
        self.et_brillo.setVisible(bool(self.ctrl.cfg["calido"]))
        self.brillo.set_valor(self.ctrl.cfg["brillo"] / 100.0)
        self.update()

    def paintEvent(self, _e):
        t = self.tinte()
        p = QPainter(self)
        base = mezclar(C["fondo"], FONDO_CALIDO, t)
        p.fillRect(self.rect(), base)
        g = QRadialGradient(QPointF(self.width() / 2, self.height() * 0.40), max(self.width(), 600) * 0.62)
        g.setColorAt(0, con_alfa(mezclar(C["panel"], LUZ_CALIDA, t), 255))
        g.setColorAt(1, con_alfa(base, 255))
        p.fillRect(self.rect(), g)

    # ---------------------------------------------------------------- ciclo de vida
    def abrir(self):
        padre = self.parentWidget()
        self.setGeometry(padre.rect())
        self._aplicar_aspecto()
        self._refrescar()
        self.show()
        self.raise_()
        self.velo.setGeometry(self.rect())
        self.velo.raise_()
        self.setFocus()
        self._reloj.start()
        self.ctrl.vista_cambio(True)

    def cerrar_vista(self):
        self._reloj.stop()
        self._cerrar_popover()
        self.panel_notas.hide()
        if self.window().isFullScreen() and self._pantalla_antes is not None:
            self.alternar_pantalla()
        self.hide()
        self.ctrl.vista_cambio(False)

    def esta_abierta(self):
        return self.isVisible()

    def eventFilter(self, obj, ev):
        if obj is self.parentWidget() and ev.type() == QEvent.Resize and self.isVisible():
            self.setGeometry(obj.rect())
        return False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.velo.setGeometry(self.rect())
        self._colocar_popover()
        if self.panel_notas.isVisible():
            self.panel_notas.colocar()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.escape()
        elif e.key() == Qt.Key_Space and not e.modifiers():
            self._play()
        else:
            super().keyPressEvent(e)

    def escape(self):
        """Esc: primero cierra lo emergente; si no hay nada, pide salir."""
        c = getattr(self, "_confirma_estudio", None)
        if c is not None and c.isVisible():
            c.seguir.emit()
            return True
        if self.panel_notas.isVisible():
            self.panel_notas.cerrar()
            return True
        if self._popover is not None:
            self._cerrar_popover()
            return True
        self.pedir_salida()
        return True

    def pedir_salida(self):
        """Salir de la vista: con un bloque en curso, antes se pregunta."""
        if not self.ctrl.hay_bloque():
            self.cerrar_vista()
            return
        confirmar_salida(self, self.ctrl, self.cerrar_vista)
        self.velo.raise_()

    # ---------------------------------------------------------------- repintado
    def _refrescar(self):
        c, t = self.ctrl, self.ctrl.temporizador
        perfil = E.PERFILES[c.cfg["perfil"]]["nombre"]
        self.et_sesion.setText(f"Sesión de estudio · {perfil}")
        self._aplicar_aspecto()
        self._refrescar_reloj()
        self.bt_pausa.setVisible(t.activo())
        self.bt_pausa.setText("Reanudar el bloque" if t.en_pausa() else "Pausar el bloque")
        self.bt_saltar.setVisible(t.activo() and t.fase != "enfoque")
        self.bt_iniciar.setVisible(not t.activo())
        self.bt_iniciar.setText("Empezar otra sesión" if t.fase == "completo" else "Empezar un bloque")
        self._estado_musica()
        self._pista()
        self._volumen_actual()

    def _refrescar_reloj(self):
        c, t = self.ctrl, self.ctrl.temporizador
        if t.activo():
            self.et_tiempo.setText(E.formato_reloj(t.restante()))
            self.et_fase.setText(c.titulo_fase().upper())
            self.barra.poner(t.progreso())
            self.barra.setVisible(True)
        elif t.fase == "completo":
            self.et_tiempo.setText("¡Listo!")
            self.et_fase.setText("SESIÓN COMPLETA")
            self.barra.poner(1.0)
            self.barra.setVisible(True)
        else:
            from datetime import datetime
            self.et_tiempo.setText(datetime.fromtimestamp(c.reloj()).strftime("%H:%M"))
            self.et_fase.setText("SIN TEMPORIZADOR")
            self.barra.setVisible(False)

    def _estado_musica(self, *_a):
        r = self.r
        sonando = r is not None and r.estado in ("sonando", "cargando")
        self.bt_play.set_icono("pausa" if sonando else "reproducir")

    def _pista(self, *_a):
        r = self.r
        p = getattr(r, "actual", None) if r is not None else None
        if p:
            t = (p.get("titulo") or "") + (f" · {p['artista']}" if p.get("artista") else "")
            ancho = max(200, self.width() - 200)
            self.et_ahora.setText(QFontMetrics(self.et_ahora.font()).elidedText(t, Qt.ElideRight, ancho))
        else:
            self.et_ahora.setText("Sin música todavía: pulsa reproducir para empezar con tu perfil")

    def _volumen_actual(self):
        r = self.r
        if r is not None:
            self.vol.set_valor(int(getattr(r, "volumen", 80)) / 100.0)

    def _aviso(self, texto):
        """Un mensaje calmado: aparece suave y se va solo."""
        self.et_aviso.setText(texto)
        a = QPropertyAnimation(self.efecto_aviso, b"opacity", self)
        a.setDuration(600)
        a.setStartValue(self.efecto_aviso.opacity())
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.start(QPropertyAnimation.DeleteWhenStopped)
        QTimer.singleShot(10000, self._ocultar_aviso)

    def _ocultar_aviso(self):
        try:
            a = QPropertyAnimation(self.efecto_aviso, b"opacity", self)
        except RuntimeError:
            return
        a.setDuration(900)
        a.setStartValue(self.efecto_aviso.opacity())
        a.setEndValue(0.0)
        a.start(QPropertyAnimation.DeleteWhenStopped)

    # ---------------------------------------------------------------- acciones
    def _play(self):
        r = self.r
        if r is None:
            return
        if r.actual is None and not self.ctrl.cargando_cola:
            self.ctrl.reproducir_perfil()
        else:
            r.alternar()

    def _siguiente(self):
        if self.r is not None and self.r.actual is not None:
            self.r.siguiente()

    def _volumen(self, x):
        if self.r is not None:
            self.r.fijar_volumen(round(x * 100))

    def _alternar_calido(self):
        self.ctrl.poner(calido=not self.ctrl.cfg["calido"])
        self._aplicar_aspecto()

    def _brillo(self, x):
        self.ctrl.cfg["brillo"] = round(x * 100)
        self._aplicar_aspecto()
        if not self.brillo.arrastrando:
            self.ctrl.cfg.guardar()

    def _alternar_despierto(self):
        self.ctrl.poner(despierto=not self.ctrl.cfg["despierto"])
        self._aplicar_aspecto()

    def alternar_pantalla(self):
        w = self.window()
        if w.isFullScreen():
            maximizada = bool((self._pantalla_antes or (False,))[0])
            self._pantalla_antes = None
            w.showMaximized() if maximizada else w.showNormal()
        else:
            self._pantalla_antes = (w.isMaximized(),)
            w.showFullScreen()

    # ---- emergentes
    def alternar_mezcla(self):
        if self._popover is self.caja_mezcla:
            self._cerrar_popover()
            return
        self.panel_notas.hide()
        self._popover = self.caja_mezcla
        self.mezcla.refrescar()
        self.caja_mezcla.adjustSize()
        self.caja_mezcla.show()
        self.caja_mezcla.raise_()
        self._colocar_popover()
        self.velo.raise_()
        self.bt_mezcla.set_activo(True)

    def _cerrar_popover(self):
        if self._popover is not None:
            self._popover.hide()
            self._popover = None
        self.bt_mezcla.set_activo(False)

    def _colocar_popover(self):
        if self._popover is None:
            return
        self._popover.adjustSize()
        x = self.width() - self._popover.width() - 40
        y = self.bt_mezcla.mapTo(self, self.bt_mezcla.rect().topLeft()).y() - self._popover.height() - 16
        self._popover.move(max(12, x), max(70, y))

    def alternar_notas(self):
        self._cerrar_popover()
        self.panel_notas.limite_inferior =             self.bt_notas.mapTo(self, self.bt_notas.rect().topLeft()).y() - 16
        self.panel_notas.alternar()
        self.bt_notas.set_activo(self.panel_notas.isVisible())
        self.velo.raise_()
