# -*- coding: utf-8 -*-
"""Modo estudio: elegir en qué vas a trabajar, mezclar sonidos y empezar a concentrarte."""

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QSpinBox, QToolTip, QVBoxLayout, QWidget)

from ... import estudio as E
from .. import iconos
from ..componentes import Pagina, fuente
from ..estilos import C
from ..estudio_piezas import (PanelMezcla, PanelNotas, Segmentado, TarjetaPerfil, con_alfa,
                              icono_estudio)

DIAS = ("L", "M", "M", "J", "V", "S", "D")
NOMBRES_DIA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def _etiqueta(texto, estilo=""):
    e = QLabel(texto)
    e.setStyleSheet("background:transparent;" + estilo)
    return e


def _caja(radio=18):
    f = QFrame()
    f.setObjectName("caja")
    f.setStyleSheet(f"QFrame#caja{{border-radius:{radio}px;}}")
    return f


class BarraFina(QWidget):
    """Una línea suave de progreso."""

    def __init__(self, alto=6, padre=None):
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
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        if self.valor > 0:
            p.setBrush(QColor(C["acento"]))
            p.drawRoundedRect(QRectF(r.left(), r.top(), max(r.height(), r.width() * self.valor),
                                     r.height()), r.height() / 2, r.height() / 2)


class GraficoSemana(QWidget):
    """Los últimos 7 días como barras suaves; hoy se ilumina. Sin metas ni rayas rojas."""

    def __init__(self, padre=None):
        super().__init__(padre)
        self.datos = []
        self.setFixedHeight(112)
        self.setMouseTracking(True)
        self.setMinimumWidth(200)

    def poner(self, datos):
        self.datos = list(datos)
        self.update()

    def _geometria(self):
        n = max(1, len(self.datos))
        paso = self.width() / n
        ancho = min(34.0, paso * 0.5)
        return n, paso, ancho

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        n, paso, ancho = self._geometria()
        tope = max(3600, max((s for _d, s in self.datos), default=0))
        base = self.height() - 22
        alto_max = base - 6
        f = fuente(11.5, QFont.DemiBold)
        p.setFont(f)
        for i, (dia, seg) in enumerate(self.datos):
            cx = paso * (i + 0.5)
            hoy = i == n - 1
            h = max(6.0, alto_max * seg / tope) if seg > 0 else 6.0
            r = QRectF(cx - ancho / 2, base - h, ancho, h)
            p.setPen(Qt.NoPen)
            if seg <= 0:
                p.setBrush(QColor(255, 255, 255, 18))
            elif hoy:
                g = QLinearGradient(r.topLeft(), r.bottomLeft())
                g.setColorAt(0, QColor(C["acento_alto"]))
                g.setColorAt(1, QColor(C["acento"]))
                p.setBrush(g)
            else:
                p.setBrush(con_alfa(C["acento"], 120))
            p.drawRoundedRect(r, min(8.0, ancho / 2), min(8.0, ancho / 2))
            p.setPen(QColor(C["texto"] if hoy else C["texto3"]))
            p.drawText(QRectF(cx - 20, base + 4, 40, 16), Qt.AlignCenter, DIAS[dia.weekday()])

    def mouseMoveEvent(self, e):
        n, paso, _a = self._geometria()
        i = int(e.position().x() // paso)
        if 0 <= i < len(self.datos):
            dia, seg = self.datos[i]
            QToolTip.showText(e.globalPosition().toPoint(),
                              f"{NOMBRES_DIA[dia.weekday()].capitalize()} {dia.day}: "
                              f"{E.formato_duracion(seg) if seg else 'sin estudio'}", self)


class Dato(QWidget):
    """Una cifra tranquila con su rótulo."""

    def __init__(self, rotulo, padre=None):
        super().__init__(padre)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        self.valor = _etiqueta("", "font-size:26px;font-weight:800;")
        v.addWidget(self.valor)
        self.rotulo = _etiqueta(rotulo, f"font-size:12.5px;color:{C['texto2']};")
        v.addWidget(self.rotulo)

    def poner(self, valor):
        self.valor.setText(valor)


class BannerSesion(QFrame):
    """Lo que ves mientras estudias: el bloque, lo que falta y los botones de siempre."""

    pausar = Signal()
    enfoque = Signal()
    saltar = Signal()
    terminar = Signal()
    otra = Signal()

    def __init__(self, padre=None):
        super().__init__(padre)
        self.setObjectName("caja")
        self.setStyleSheet("QFrame#caja{border-radius:20px;}")
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(10)
        fila = QHBoxLayout()
        fila.setSpacing(24)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.fase = _etiqueta("", f"font-size:12px;font-weight:700;color:{C['acento']};"
                                  "letter-spacing:1px;")
        col.addWidget(self.fase)
        self.tiempo = _etiqueta("25:00", "font-size:54px;font-weight:300;")
        self.tiempo.setFont(fuente(54, QFont.Light, True))
        col.addWidget(self.tiempo)
        fila.addLayout(col)
        fila.addStretch(1)
        self.botones = QHBoxLayout()
        self.botones.setSpacing(10)
        self.bt_pausa = QPushButton("Pausar")
        self.bt_enfoque = QPushButton("  Sin distracciones")
        self.bt_enfoque.setIcon(iconos.icono("pantalla_completa", 18, C["acento_texto"]))
        self.bt_enfoque.setObjectName("principal")
        self.bt_saltar = QPushButton("Saltar descanso")
        self.bt_terminar = QPushButton("Terminar")
        self.bt_otra = QPushButton("Empezar otra sesión")
        self.bt_otra.setObjectName("principal")
        for b, s in ((self.bt_pausa, self.pausar), (self.bt_enfoque, self.enfoque),
                     (self.bt_saltar, self.saltar), (self.bt_terminar, self.terminar),
                     (self.bt_otra, self.otra)):
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(40)
            b.clicked.connect(lambda _=False, s=s: s.emit())
            self.botones.addWidget(b)
        for b in (self.bt_pausa, self.bt_saltar, self.bt_terminar):
            b.setObjectName("contorno")
        fila.addLayout(self.botones)
        v.addLayout(fila)
        self.barra = BarraFina(6)
        v.addWidget(self.barra)
        self.mensaje = _etiqueta("", f"font-size:13.5px;color:{C['texto2']};")
        self.mensaje.setWordWrap(True)
        v.addWidget(self.mensaje)

    def actualizar(self, ctrl):
        t = ctrl.temporizador
        completo = t.fase == "completo"
        self.fase.setText(ctrl.titulo_fase().upper())
        self.tiempo.setText("¡Listo!" if completo else E.formato_reloj(t.restante()))
        self.barra.poner(1.0 if completo else t.progreso())
        self.bt_pausa.setText("Reanudar" if t.en_pausa() else "Pausar")
        self.bt_pausa.setVisible(t.activo())
        self.bt_enfoque.setVisible(t.activo())
        self.bt_terminar.setVisible(t.activo())
        self.bt_saltar.setVisible(t.activo() and t.fase != "enfoque")
        self.bt_otra.setVisible(completo)
        self.barra.setVisible(t.activo() or completo)
        self.mensaje.setVisible(bool(self.mensaje.text()))


class TarjetaEstudioInicio(QWidget):
    """La entrada elegante al modo estudio desde Inicio."""

    clicked = Signal()

    def __init__(self, ctrl_o_texto="", padre=None):
        super().__init__(padre)
        self.texto_datos = ctrl_o_texto
        self.setFixedHeight(112)
        self.setCursor(Qt.PointingHandCursor)
        self._encima = 0.0
        self._objetivo = 0.0
        self.setAccessibleName("Modo estudio")
        self._t = QTimer(self)
        self._t.setInterval(16)
        self._t.timeout.connect(self._paso)

    def compacta(self):
        """Más baja y discreta (en Inicio va al lado de «Tu resumen»)."""
        self.setFixedHeight(84)
        self.update()

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
        ruta.addRoundedRect(r, 16, 16)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor("#1E3A4C"))
        g.setColorAt(0.6, QColor("#33405F"))
        g.setColorAt(1, QColor("#4A3F63"))
        p.fillPath(ruta, g)
        if self._encima > 0.01:
            p.fillPath(ruta, QColor(255, 255, 255, int(16 * self._encima)))
        p.save()
        p.setClipPath(ruta)
        p.setPen(Qt.NoPen)
        dx = 8 * self._encima
        for cx, cy, rad, a in ((r.right() - 70 - dx, 8, 64, 20), (r.right() - 14, 84, 44, 26),
                               (r.right() - 160 - dx * 2, 100, 30, 16)):
            p.setBrush(QColor(255, 255, 255, a))
            p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))
        p.restore()
        # icono en círculo
        p.setBrush(QColor(255, 255, 255, 34))
        chica = self.height() < 100
        p.setPen(Qt.NoPen)
        arriba, mitad = (10, 26) if chica else (20, 28)      # dónde empieza el texto y radio del círculo
        p.drawEllipse(QRectF(18 if chica else 26, r.center().y() - (22 if chica else 28), mitad * 2 - (8 if chica else 0),
                             mitad * 2 - (8 if chica else 0)))
        p.drawPixmap(int(18 + 10 if chica else 26 + 14), int(r.center().y() - (12 if chica else 14)),
                     iconos.pixmap("graduado", 24 if chica else 28, "#FFFFFF"))
        x = 78 if chica else 104
        p.setPen(QColor(255, 255, 255, 190))
        p.setFont(fuente(11.5, QFont.Bold))
        p.drawText(QRectF(x, arriba, r.width() - x - 60, 16), Qt.AlignLeft | Qt.AlignVCenter,
                   "MODO ESTUDIO")
        p.setPen(QColor("#FFFFFF"))
        p.setFont(fuente(18 if chica else 22, QFont.Bold, True))
        p.drawText(QRectF(x, arriba + 16, r.width() - x - 60, 26 if chica else 30), Qt.AlignLeft | Qt.AlignVCenter,
                   "Concéntrate con calma")
        f = fuente(13)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 210))
        texto = self.texto_datos or "Música sin letra, sonidos que relajan y descansos a tu ritmo"
        ancho = int(r.width() - x - 60)
        p.drawText(QRectF(x, arriba + (42 if chica else 48), ancho, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(texto, Qt.ElideRight, ancho))
        lado = 22
        px = r.right() - 28 - lado + 4 * self._encima
        p.drawPixmap(int(px), int(r.center().y() - lado / 2), iconos.pixmap("adelante", lado, "#FFFFFF"))


class PaginaEstudio(Pagina):
    def __init__(self, ctx, padre=None):
        super().__init__(ctx, padre, margen=(36, 30, 36, 44))
        self.titulo = "Modo estudio"
        self.ctrl = E.de(ctx)
        self.cuerpo.setSpacing(30)
        self._columnas = 0
        self._cargando = False
        self.panel_notas = None
        self._construir()
        self.ctrl.cambio.connect(self._refrescar)
        self.ctrl.tic.connect(self._tic)
        self.ctrl.aviso.connect(self._aviso)
        self.ctrl.bloque_terminado.connect(self._al_terminar_bloque)
        self._refrescar()

    # ---------------------------------------------------------------- construcción
    def _construir(self):
        ctrl = self.ctrl
        cab = QVBoxLayout()
        cab.setSpacing(6)
        cab.addWidget(_etiqueta("MODO ESTUDIO", f"font-size:12px;font-weight:700;color:{C['acento']};"
                                                "letter-spacing:1.4px;"))
        cab.addWidget(_etiqueta("Tu espacio para concentrarte", "font-size:34px;font-weight:900;"))
        sub = _etiqueta("Elige en qué vas a trabajar y deja que Caudal cuide la música, los "
                        "sonidos y los descansos.", f"font-size:15px;color:{C['texto2']};")
        sub.setWordWrap(True)
        cab.addWidget(sub)
        self.cuerpo.addLayout(cab)

        self.banner = BannerSesion()
        self.banner.pausar.connect(ctrl.pausar_o_reanudar)
        self.banner.enfoque.connect(self._abrir_enfoque)
        self.banner.saltar.connect(ctrl.saltar_fase)
        self.banner.terminar.connect(self._terminar)
        self.banner.otra.connect(lambda: ctrl.empezar())
        self.cuerpo.addWidget(self.banner)

        self.cuerpo.addWidget(_etiqueta("¿En qué vas a trabajar?", "font-size:21px;font-weight:800;"))
        self.rejilla = QGridLayout()
        self.rejilla.setHorizontalSpacing(16)
        self.rejilla.setVerticalSpacing(16)
        self.tarjetas = {}
        for clave in E.PERFILES:
            t = TarjetaPerfil(clave)
            t.elegido.connect(self._elegir)
            self.tarjetas[clave] = t
        self.cuerpo.addLayout(self.rejilla)

        self.fila2 = QGridLayout()
        self.fila2.setHorizontalSpacing(18)
        self.fila2.setVerticalSpacing(18)
        self.caja_sesion = self._construir_sesion()
        self.caja_mezcla = self._construir_mezcla()
        self.cuerpo.addLayout(self.fila2)

        self.fila3 = QGridLayout()
        self.fila3.setHorizontalSpacing(18)
        self.fila3.setVerticalSpacing(18)
        self.caja_constancia = self._construir_constancia()
        self.caja_notas = self._construir_notas()
        self.cuerpo.addLayout(self.fila3)
        self.cuerpo.addStretch(1)
        self._reordenar(force=True)

    def _construir_sesion(self):
        c = _caja()
        v = QVBoxLayout(c)
        v.setContentsMargins(28, 26, 28, 26)
        v.setSpacing(12)
        v.addWidget(_etiqueta("Tu sesión", "font-size:19px;font-weight:800;"))
        v.addWidget(_etiqueta("Bloques de enfoque con descansos, como te funcione mejor.",
                              f"font-size:13px;color:{C['texto2']};"))
        v.addSpacing(6)
        v.addWidget(_etiqueta("RITMO", f"font-size:11.5px;font-weight:700;color:{C['texto3']};"
                                       "letter-spacing:1px;"))
        self.seg_ritmo = Segmentado([("25/5", "25 · 5"), ("50/10", "50 · 10"), ("90/15", "90 · 15"),
                                     ("personalizado", "A mi manera")], self.ctrl.cfg["pomodoro"])
        self.seg_ritmo.cambiado.connect(lambda k: self.ctrl.poner(pomodoro=k))
        v.addWidget(self.seg_ritmo)
        g = QGridLayout()
        g.setHorizontalSpacing(18)
        g.setVerticalSpacing(8)
        self.sp = {}
        campos = (("enfoque_min", "Enfoque", 1, 240, " min", 0, 0),
                  ("descanso_min", "Descanso", 0, 60, " min", 0, 1),
                  ("rondas", "Rondas", 1, 12, "", 1, 0),
                  ("descanso_largo_min", "Descanso largo", 0, 60, " min", 1, 1))
        for clave, texto, lo, hi, suf, fila, col in campos:
            caja = QVBoxLayout()
            caja.setSpacing(4)
            caja.addWidget(_etiqueta(texto, f"font-size:12.5px;color:{C['texto2']};"))
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setSuffix(suf)
            s.setMinimumHeight(38)
            if clave == "descanso_largo_min":
                s.setSpecialValueText("Ninguno")
            s.valueChanged.connect(lambda val, k=clave: self._cambio_numero(k, val))
            caja.addWidget(s)
            self.sp[clave] = s
            g.addLayout(caja, fila, col)
        v.addLayout(g)
        v.addWidget(_etiqueta("El descanso largo llega después de cada 4 rondas.",
                              f"font-size:12px;color:{C['texto3']};"))
        v.addSpacing(6)
        v.addWidget(_etiqueta("AL TERMINAR UN BLOQUE, LA MÚSICA", f"font-size:11.5px;font-weight:700;"
                                                                f"color:{C['texto3']};letter-spacing:1px;"))
        self.seg_musica = Segmentado([("bajar", "Baja"), ("pausar", "Se pausa"),
                                      ("seguir", "Sigue igual")], self.ctrl.cfg["al_descansar"])
        self.seg_musica.cambiado.connect(lambda k: self.ctrl.poner(al_descansar=k))
        v.addWidget(self.seg_musica)
        v.addSpacing(6)
        self.opciones = {}
        for clave, texto in (("campana", "Campana suave al cambiar de bloque"),
                             ("atenuar", "Bajar un poco la música mientras te concentras"),
                             ("despierto", "Mantener el equipo despierto"),
                             ("candado", "Candado: mantener pulsado 2 s para salir")):
            cb = QCheckBox(texto)
            cb.setCursor(Qt.PointingHandCursor)
            cb.toggled.connect(lambda si, k=clave: self.ctrl.poner(**{k: bool(si)}))
            self.opciones[clave] = cb
            v.addWidget(cb)
        v.addSpacing(10)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.bt_empezar = QPushButton("Empezar a estudiar")
        self.bt_empezar.setObjectName("principal")
        self.bt_empezar.setMinimumHeight(46)
        self.bt_empezar.setStyleSheet("QPushButton#principal{padding:10px 26px;font-size:14px;}")
        self.bt_empezar.setCursor(Qt.PointingHandCursor)
        self.bt_empezar.clicked.connect(self._empezar)
        fila.addWidget(self.bt_empezar)
        self.bt_enfoque = QPushButton("  Sin distracciones")
        self.bt_enfoque.setIcon(iconos.icono("pantalla_completa", 18, C["texto"]))
        self.bt_enfoque.setObjectName("contorno")
        self.bt_enfoque.setMinimumHeight(46)
        self.bt_enfoque.setCursor(Qt.PointingHandCursor)
        self.bt_enfoque.clicked.connect(lambda: self._empezar(abrir=True))
        fila.addWidget(self.bt_enfoque)
        fila.addStretch(1)
        v.addLayout(fila)
        self.bt_solo = QPushButton("Solo la música, sin temporizador")
        self.bt_solo.setObjectName("enlace")
        self.bt_solo.setCursor(Qt.PointingHandCursor)
        self.bt_solo.clicked.connect(lambda: self.ctrl.empezar(solo_musica=True))
        v.addWidget(self.bt_solo, 0, Qt.AlignLeft)
        self.et_estado = _etiqueta("", f"font-size:12.5px;color:{C['texto2']};")
        self.et_estado.setWordWrap(True)
        v.addWidget(self.et_estado)
        return c

    def _construir_mezcla(self):
        c = _caja()
        v = QVBoxLayout(c)
        v.setContentsMargins(28, 26, 28, 24)
        v.setSpacing(10)
        v.addWidget(_etiqueta("Sonidos y música", "font-size:19px;font-weight:800;"))
        d = _etiqueta("Mezcla a tu gusto: cada capa tiene su propio volumen.",
                      f"font-size:13px;color:{C['texto2']};")
        d.setWordWrap(True)
        v.addWidget(d)
        v.addSpacing(6)
        self.mezcla = PanelMezcla(self.ctrl)
        v.addWidget(self.mezcla)
        v.addSpacing(6)
        self.bt_sugerida = QPushButton("")
        self.bt_sugerida.setObjectName("enlace")
        self.bt_sugerida.setCursor(Qt.PointingHandCursor)
        self.bt_sugerida.clicked.connect(lambda: self.ctrl.aplicar_mezcla_del_perfil())
        v.addWidget(self.bt_sugerida, 0, Qt.AlignLeft)
        self.cb_auto_mezcla = QCheckBox("Poner la mezcla sugerida al elegir un perfil")
        self.cb_auto_mezcla.toggled.connect(lambda si: self.ctrl.poner(mezcla_del_perfil=bool(si)))
        v.addWidget(self.cb_auto_mezcla)
        v.addStretch(1)
        return c

    def _construir_constancia(self):
        c = _caja()
        v = QVBoxLayout(c)
        v.setContentsMargins(28, 26, 28, 24)
        v.setSpacing(14)
        v.addWidget(_etiqueta("Tu constancia", "font-size:19px;font-weight:800;"))
        fila = QHBoxLayout()
        fila.setSpacing(34)
        self.d_hoy = Dato("hoy")
        self.d_semana = Dato("últimos 7 días")
        self.d_racha = Dato("de racha")
        for d in (self.d_hoy, self.d_semana, self.d_racha):
            fila.addWidget(d)
        fila.addStretch(1)
        v.addLayout(fila)
        self.grafico = GraficoSemana()
        v.addWidget(self.grafico)
        self.et_frase = _etiqueta("", f"font-size:13.5px;color:{C['texto2']};")
        self.et_frase.setWordWrap(True)
        v.addWidget(self.et_frase)
        return c

    def _construir_notas(self):
        c = _caja()
        v = QVBoxLayout(c)
        v.setContentsMargins(28, 26, 28, 24)
        v.setSpacing(10)
        fila = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(icono_estudio("idea", 22, C["acento"]))
        ic.setStyleSheet("background:transparent;")
        fila.addWidget(ic)
        fila.addWidget(_etiqueta("Captura de ideas", "font-size:19px;font-weight:800;"))
        fila.addStretch(1)
        v.addLayout(fila)
        d = _etiqueta("Anota lo que se te ocurra sin salir de lo que haces y vuelve a tu tarea "
                      "sin perder el hilo.", f"font-size:13px;color:{C['texto2']};")
        d.setWordWrap(True)
        v.addWidget(d)
        self.et_nota = _etiqueta("", f"font-size:13.5px;color:{C['texto']};padding:12px 14px;"
                                     "border-radius:12px;background:rgba(255,255,255,12);")
        self.et_nota.setWordWrap(True)
        v.addWidget(self.et_nota)
        fila2 = QHBoxLayout()
        self.bt_notas = QPushButton("Abrir las notas")
        self.bt_notas.setObjectName("contorno")
        self.bt_notas.setMinimumHeight(40)
        self.bt_notas.setCursor(Qt.PointingHandCursor)
        self.bt_notas.clicked.connect(self.alternar_notas)
        fila2.addWidget(self.bt_notas)
        fila2.addWidget(_etiqueta("Ctrl + Shift + N", f"font-size:12px;color:{C['texto3']};"))
        fila2.addStretch(1)
        v.addLayout(fila2)
        v.addStretch(1)
        return c

    # ---------------------------------------------------------------- reflujo
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reordenar()

    def _reordenar(self, force=False):
        ancho = self.viewport().width()
        ancho = ancho if ancho > 50 else self.width()
        cols = 4 if ancho >= 980 else 2
        ancha = ancho >= 920
        clave = (cols, ancha)
        if clave == self._columnas and not force:
            return
        self._columnas = clave
        for t in self.tarjetas.values():
            self.rejilla.removeWidget(t)
        for i, t in enumerate(self.tarjetas.values()):
            self.rejilla.addWidget(t, i // cols, i % cols)
        for lay, a, b in ((self.fila2, self.caja_sesion, self.caja_mezcla),
                          (self.fila3, self.caja_constancia, self.caja_notas)):
            lay.removeWidget(a)
            lay.removeWidget(b)
            if ancha:
                lay.addWidget(a, 0, 0)
                lay.addWidget(b, 0, 1)
                lay.setColumnStretch(0, 11)
                lay.setColumnStretch(1, 10)
            else:
                lay.addWidget(a, 0, 0)
                lay.addWidget(b, 1, 0)
                lay.setColumnStretch(0, 1)
                lay.setColumnStretch(1, 0)

    # ---------------------------------------------------------------- acciones
    def _elegir(self, clave):
        self.ctrl.elegir_perfil(clave)

    def _cambio_numero(self, clave, valor):
        if self._cargando:
            return
        if clave in ("enfoque_min", "descanso_min"):
            self.ctrl.poner(**{clave: int(valor), "pomodoro": "personalizado"})
        else:
            self.ctrl.poner(**{clave: int(valor)})

    def _empezar(self, _=False, abrir=False):
        self.ctrl.empezar()
        if abrir:
            self._abrir_enfoque()

    def _abrir_enfoque(self):
        v = getattr(self.ctx, "ventana", None)
        if v is not None and hasattr(v, "abrir_enfoque"):
            v.abrir_enfoque()

    def _terminar(self):
        self.ctrl.terminar()

    def alternar_notas(self):
        if self.panel_notas is None:
            marco = self.window() if self.window() is not self else self
            self.panel_notas = PanelNotas(self.ctrl, marco)
            self.panel_notas.cerrado.connect(self._refrescar)
        self.panel_notas.alternar()

    def _aviso(self, texto):
        self.banner.mensaje.setText(texto)
        self.banner.mensaje.setVisible(bool(texto))

    # ---------------------------------------------------------------- repintado
    def _tic(self):
        self.banner.actualizar(self.ctrl)

    def _al_terminar_bloque(self, _e=None):
        self._refrescar()

    def _refrescar(self):
        ctrl, cfg = self.ctrl, self.ctrl.cfg
        self._cargando = True
        try:
            perfil = E.PERFILES[cfg["perfil"]]
            for k, t in self.tarjetas.items():
                t.poner_seleccion(k == cfg["perfil"])
            self.set_color(perfil["colores"][0])
            self.seg_ritmo.poner(cfg["pomodoro"])
            self.seg_musica.poner(cfg["al_descansar"])
            for k, s in self.sp.items():
                s.blockSignals(True)
                s.setValue(int(cfg[k]))
                s.blockSignals(False)
            for k, cb in self.opciones.items():
                cb.blockSignals(True)
                cb.setChecked(bool(cfg[k]))
                cb.blockSignals(False)
            self.cb_auto_mezcla.blockSignals(True)
            self.cb_auto_mezcla.setChecked(bool(cfg["mezcla_del_perfil"]))
            self.cb_auto_mezcla.blockSignals(False)
            self.bt_sugerida.setText(f"Usar la mezcla sugerida para «{perfil['nombre']}»")
            en_curso = ctrl.hay_bloque()
            if not en_curso and ctrl.temporizador.fase != "completo":
                self.banner.mensaje.clear()
            self.banner.setVisible(en_curso or ctrl.temporizador.fase == "completo")
            self.banner.actualizar(ctrl)
            for s in self.sp.values():
                s.setEnabled(not en_curso)
            self.seg_ritmo.setEnabled(not en_curso)
            self.bt_empezar.setVisible(not en_curso)
            self.bt_enfoque.setVisible(not en_curso)
            self.bt_solo.setVisible(not en_curso)
            if ctrl.cargando_cola:
                self.et_estado.setText("Buscando tu música…")
            elif en_curso:
                self.et_estado.setText("Tu sesión sigue en marcha mientras estés en esta pantalla.")
            else:
                self.et_estado.setText("")
            self.et_estado.setVisible(bool(self.et_estado.text()))
            est = ctrl.est
            self.d_hoy.poner(E.formato_duracion(est.hoy()) if est.hoy() else "—")
            self.d_semana.poner(E.formato_duracion(est.semana()) if est.semana() else "—")
            r = est.racha()
            self.d_racha.poner(f"{r} {'día' if r == 1 else 'días'}" if r else "—")
            self.grafico.poner(est.ultimos_dias(7))
            self.et_frase.setText(est.frase())
            notas = ctrl.notas.todas()
            if notas:
                t = notas[0]["texto"]
                t = t if len(t) <= 140 else t[:137].rsplit(" ", 1)[0] + "…"
                self.et_nota.setText(f"{t}\n{E.fecha_amable(notas[0]['fecha'])}"
                                     f"  ·  {len(notas)} {'idea' if len(notas) == 1 else 'ideas'}")
            else:
                self.et_nota.setText("Aún no hay ideas guardadas.")
        finally:
            self._cargando = False
