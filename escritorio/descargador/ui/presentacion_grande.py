# -*- coding: utf-8 -*-
"""La tercera «Actualización grande de Caudal»: una presentación a pantalla completa.

Nueve diapositivas con fondo de aurora animado, una ilustración propia por
diapositiva (todo dibujado con QPainter, sin imágenes) y una transición de
fundido con desplazamiento en capas (parallax). Se maneja con las flechas, Enter,
la rueda, el clic o los puntos de progreso; «Saltar» está siempre a la vista.

La pinta una sola ventana sin marco que cubre la de Caudal; la música no se toca.
"""

import math

from PySide6.QtCore import (QElapsedTimer, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRectF, QTimer,
                            Qt, QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from .. import version as _version
from . import ilustraciones_grandes as I
from . import ilustraciones_v4  # noqa: F401  (registra las ilustraciones de esta edición)
from .componentes import fuente
from .estilos import C

TITULO = "ACTUALIZACIÓN GRANDE DE CAUDAL"

# clave de la ilustración, etiqueta, título, texto
DIAPOSITIVAS = [
    dict(clave="portada", etiqueta="EDICIÓN 2.5", titulo=TITULO,
         texto="Más estilo, más herramientas y una app que va más suave. Esto es lo nuevo.", centrada=True, tono=0),
    dict(clave="marcos", etiqueta="TU PERFIL", titulo="Lúcete en tu perfil",
         texto="Marcos animados para tu foto y nombres con brillo, degradado o arcoíris. Se ven en tu perfil, tus "
               "chats y tus amigos.", tono=30),
    dict(clave="temas", etiqueta="DONADORES", titulo="Temas exclusivos",
         texto="Seis paletas completas (Atardecer, Bosque, Sakura, Océano, Medianoche y Ámbar) que cambian el color "
               "de toda la app.", tono=-20),
    dict(clave="pase", etiqueta="PASE DE PRUEBA", titulo="Pase de prueba",
         texto="Canjea un código y usa todos los beneficios de donador durante 7 días. Pídelo a quien te invitó a "
               "Caudal.", tono=46),
    dict(clave="letras", etiqueta="COMPARTE", titulo="Letras para presumir",
         texto="Tarjetas con la carátula difuminada y estilos nuevos para donadores, listas para tus estados e "
               "historias.", tono=18),
    dict(clave="anio", etiqueta="TU AÑO", titulo="Tu año en Caudal",
         texto="Tus minutos, tu canción y tus artistas del año en una imagen lista para compartir. Exclusivo de "
               "donadores.", tono=-40),
    dict(clave="musica", etiqueta="REPRODUCCIÓN", titulo="La música no se corta",
         texto="Si la conexión se cae, Caudal la retoma solo y sigue justo donde iba, sin saltar de canción.",
         tono=10),
    dict(clave="fluido", etiqueta="RENDIMIENTO", titulo="Más fluida",
         texto="Ajustes abre al instante, sin congelar la ventana, y la app trabaja en segundo plano para ir suave.",
         tono=-14),
    dict(clave="final", etiqueta="GRACIAS", titulo="Gracias por ser parte de Caudal",
         texto="Todo esto es para ti. Disfruta lo nuevo.", centrada=True, tono=8),
]


class _Boton(QPushButton):
    """Botón en forma de píldora pintado a mano (el redondeo de las hojas de estilo falla
    sin borde en algunas versiones de Qt)."""

    def __init__(self, texto, padre, principal=False):
        super().__init__(texto, padre)
        self.principal = principal
        self._px, self._mas = 14, 1.0
        self._encima = False
        self._fs = 1.0
        self.setMouseTracking(True)

    def configurar(self, fs, mas=1.0):
        self._fs, self._mas = fs, mas
        self._px = max(12, round(14 * fs)) * (1.06 if self.principal else 1.0) * mas
        self.adjustSize()

    def _fuente(self):
        return fuente(self._px, QFont.ExtraBold if self.principal else QFont.Bold)

    def sizeHint(self):
        fm = QFontMetricsF(self._fuente())
        px = (32 if self.principal else 22) * self._fs * self._mas
        py = (10 if self.principal else 9) * self._fs * self._mas
        from PySide6.QtCore import QSize
        return QSize(round(fm.horizontalAdvance(self.text()) + 2 * px), round(fm.height() + 2 * py))

    def enterEvent(self, e):
        self._encima = True
        self.update()

    def leaveEvent(self, e):
        self._encima = False
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if not self.isEnabled():
            fondo, texto = QColor(255, 255, 255, 34), QColor(255, 255, 255, 130)
        elif self.principal:
            fondo = QColor(C["acento_bajo"] if self.isDown() else C["acento_alto"] if self._encima else C["acento"])
            texto = QColor(C["acento_texto"])
        else:
            fondo = QColor(255, 255, 255, 56 if self._encima else 26)
            texto = QColor(255, 255, 255, 240)
        p.setPen(Qt.NoPen)
        p.setBrush(fondo)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        if self.hasFocus() and self.focusPolicy() != Qt.NoFocus:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor("#FFFFFF") if self.principal else QColor(C["acento_alto"]), 2))
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), r.height() / 2, r.height() / 2)
        p.setFont(self._fuente())
        p.setPen(texto)
        p.drawText(self.rect(), int(Qt.AlignCenter), self.text())


class PresentacionGrande(QDialog):
    """`novedad` (de `version.buscar_actualizacion`) la convierte en el aviso previo a
    actualizar, con el botón final «Actualizar ahora»."""

    DURACION = 950               # ms de la transición entre diapositivas

    def __init__(self, padre=None, novedad=None, version_actual=None):
        super().__init__(padre)
        self.novedad = novedad
        self.descarga = None
        self.n = len(DIAPOSITIVAS)
        self.indice = 0
        self._ant = None                    # diapositiva que se va
        self._dir = 1
        self._p_trans = 1.0
        self._tg = 0.0
        self._tl = 0.0                      # reloj de la diapositiva actual
        self._tl_ant = 0.0
        self._pos_puntos = 0.0
        self._estado = ""
        self._prog = 0.0
        self._revelado = False
        self._rueda = 0
        self._ultima_rueda = QElapsedTimer()
        self._ultima_rueda.start()
        self._cache_fuentes = {}
        self._cache_rutas = {}
        self._puntos = []                   # rectángulos de los puntos, para el clic
        self._fondo_img = None
        self._logo_cache = {}
        self._base = None
        self._anim_trans = None
        self._anim_puntos = None
        self._anim_sig = None
        self._anim_op = None
        self._version_actual = version_actual or _version.VERSION

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle("Novedades de Caudal")
        self.setAccessibleName("Novedades de Caudal")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(900, 600)

        self.bt_saltar = _Boton("Saltar" if not novedad else "Más tarde", self)
        self.bt_saltar.setAccessibleName("Saltar la presentación")
        self.bt_saltar.setCursor(Qt.PointingHandCursor)
        self.bt_saltar.setAutoDefault(False)
        self.bt_saltar.setFocusPolicy(Qt.TabFocus)
        self.bt_saltar.clicked.connect(self.reject)
        self.bt_ant = _Boton("‹  Atrás", self)
        self.bt_ant.setCursor(Qt.PointingHandCursor)
        self.bt_ant.setAutoDefault(False)
        self.bt_ant.setFocusPolicy(Qt.TabFocus)
        self.bt_ant.setAccessibleName("Diapositiva anterior")
        self.bt_ant.clicked.connect(self.anterior)
        self.bt_sig = _Boton("Siguiente  ›", self, True)
        self.bt_sig.setCursor(Qt.PointingHandCursor)
        self.bt_sig.setAutoDefault(False)
        self.bt_sig.setFocusPolicy(Qt.TabFocus)
        self.bt_sig.setAccessibleName("Diapositiva siguiente")
        self.bt_sig.clicked.connect(self._principal)

        self._reloj = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._ajustar_tamano()
        self._actualizar_textos()
        self._estilos()
        self._colocar_botones(animar=False)

    # ================================================================ tamaño y capa

    def _base_ventana(self):
        padre = self.parentWidget()
        return padre.window() if padre is not None else None

    def _ajustar_tamano(self):
        base = self._base_ventana()
        if base is not None:
            esq = base.mapToGlobal(QPoint(0, 0))
            ancho, alto = base.width(), base.height()
        else:
            pant = QApplication.primaryScreen()
            geo = pant.availableGeometry() if pant is not None else None
            ancho, alto = (geo.width(), geo.height()) if geo else (1280, 800)
            esq = geo.topLeft() if geo else QPoint(0, 0)
        ancho, alto = max(900, ancho), max(600, alto)
        self.setGeometry(esq.x(), esq.y(), ancho, alto)

    def eventFilter(self, obj, e):
        if obj is self._base and e.type() in (QEvent.Resize, QEvent.Move):
            self._ajustar_tamano()
        return super().eventFilter(obj, e)

    def _escala(self):
        return max(0.82, min(1.5, min(self.width() / 1280.0, self.height() / 800.0)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fondo_img = None
        self._estilos()
        self._colocar_botones(animar=False)

    # ================================================================ botones

    def _estilos(self):
        fs = self._escala()
        ultimo = self.indice == self.n - 1
        self.bt_saltar.configurar(fs)
        self.bt_ant.configurar(fs)
        self.bt_sig.configurar(fs, 1.18 if ultimo else 1.0)

    def _texto_boton_final(self):
        return "Actualizar ahora" if self.novedad else "Empezar"

    def _actualizar_textos(self):
        ultimo = self.indice == self.n - 1
        self.bt_sig.setText(self._texto_boton_final() if ultimo else "Siguiente  ›")
        self.bt_sig.setAccessibleName(self._texto_boton_final() if ultimo else "Diapositiva siguiente")
        if self.novedad and ultimo and not self.novedad.get("instalador"):
            self.bt_sig.setEnabled(False)
            self._estado = "Esta versión no trae el instalador adjunto. Bájala desde la página del proyecto."
        d = DIAPOSITIVAS[self.indice]
        self.setAccessibleDescription(f"Diapositiva {self.indice + 1} de {self.n}. {d['titulo']}. {d['texto']}")
        self.bt_ant.setVisible(self.indice > 0)
        self._estilos()

    def _y_puntos(self):
        return self.height() - round(46 * self._escala())

    def _destino_sig(self, i):
        """Dónde va el botón principal: abajo a la derecha, y en la última diapositiva
        centrado bajo el texto."""
        fs = self._escala()
        w, h = self.width(), self.height()
        bw, bh = self.bt_sig.width(), self.bt_sig.height()
        if i == self.n - 1:
            L = self._layout(i)
            y = min(L["y_fin"] + 30 * fs, h - 120 * fs)
            return QPoint(round((w - bw) / 2), round(y))
        return QPoint(round(w - 56 * fs - bw), round(self._y_puntos() - bh / 2))

    def _colocar_botones(self, animar=True):
        fs = self._escala()
        w = self.width()
        self.bt_saltar.move(round(w - 48 * fs - self.bt_saltar.width()), round(30 * fs))
        self.bt_ant.move(round(56 * fs), round(self._y_puntos() - self.bt_ant.height() / 2))
        destino = self._destino_sig(self.indice)
        if self._anim_sig is not None:
            self._anim_sig.stop()
        if animar and self.isVisible() and self.bt_sig.pos() != destino:
            self._anim_sig = QPropertyAnimation(self.bt_sig, b"pos", self)
            self._anim_sig.setDuration(700)
            self._anim_sig.setStartValue(self.bt_sig.pos())
            self._anim_sig.setEndValue(destino)
            self._anim_sig.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim_sig.start()
        else:
            self.bt_sig.move(destino)
        self.bt_saltar.raise_()
        self.bt_sig.raise_()

    # ================================================================ navegación

    def ir_a(self, i, animar=True):
        i = max(0, min(self.n - 1, int(i)))
        if i == self.indice:
            return
        if self.descarga is not None and self.descarga.isRunning():
            return
        self._dir = 1 if i > self.indice else -1
        self._ant = self.indice
        self._tl_ant = self._tl
        self.indice = i
        self._tl = 0.0
        self._actualizar_textos()
        self._colocar_botones(animar=animar)
        if self._anim_trans is not None:
            self._anim_trans.stop()
        self._anim_puntos = QVariantAnimation(self)
        self._anim_puntos.setStartValue(float(self._pos_puntos))
        self._anim_puntos.setEndValue(float(i))
        self._anim_puntos.setDuration(520 if animar else 1)
        self._anim_puntos.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_puntos.valueChanged.connect(self._poner_puntos)
        self._anim_puntos.start()
        self._anim_trans = QVariantAnimation(self)
        self._anim_trans.setStartValue(0.0)
        self._anim_trans.setEndValue(1.0)
        self._anim_trans.setDuration(self.DURACION if animar else 1)
        self._anim_trans.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim_trans.valueChanged.connect(self._poner_trans)
        self._anim_trans.finished.connect(self._fin_trans)
        self._p_trans = 0.0
        self._anim_trans.start()
        self.update()

    def _poner_trans(self, v):
        self._p_trans = float(v)

    def _poner_puntos(self, v):
        self._pos_puntos = float(v)

    def _fin_trans(self):
        self._p_trans = 1.0
        self._ant = None

    def siguiente(self):
        if self.indice < self.n - 1:
            self.ir_a(self.indice + 1)

    def anterior(self):
        if self.indice > 0:
            self.ir_a(self.indice - 1)

    def _principal(self):
        if self.indice < self.n - 1:
            self.siguiente()
            return
        if not self.novedad:
            self.accept()
            return
        from .actualizador import Descarga
        self.bt_sig.setEnabled(False)
        self.bt_saltar.setEnabled(False)
        self.bt_ant.setEnabled(False)
        self._estado = "Bajando la actualización…"
        self._prog = 0.0
        self.descarga = Descarga(self.novedad["instalador"])
        self.descarga.progreso.connect(self._poner_prog)
        self.descarga.listo.connect(self._lanzar)
        self.descarga.fallo.connect(self._fallo)
        self.descarga.start()

    def _poner_prog(self, v):
        self._prog = max(0.0, min(1.0, float(v) / 100.0))

    def _lanzar(self, ruta):
        self._estado = "Instalando. Caudal se cerrará un momento…"
        self._prog = 1.0
        _version.instalar_y_salir(ruta)

    def _fallo(self, mensaje):
        self._estado = f"{mensaje} Puedes intentarlo otra vez."
        self._prog = 0.0
        self.bt_sig.setEnabled(True)
        self.bt_saltar.setEnabled(True)
        self.bt_ant.setEnabled(True)

    def reject(self):
        # con la descarga en marcha no se cierra a medias
        if self.descarga is not None and self.descarga.isRunning():
            return
        super().reject()

    # ================================================================ entrada

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Space):
            if self.indice == self.n - 1 and k == Qt.Key_Space:
                self._principal()
            else:
                self.siguiente()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self._principal()
        elif k in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_Backspace):
            self.anterior()
        elif k == Qt.Key_Home:
            self.ir_a(0)
        elif k == Qt.Key_End:
            self.ir_a(self.n - 1)
        elif k == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)

    def _punto_en(self, pos):
        for i, r in enumerate(self._puntos):
            if r.adjusted(-6, -12, 6, 12).contains(QPointF(pos)):
                return i
        return None

    def mouseMoveEvent(self, e):
        self.setCursor(Qt.PointingHandCursor if self._punto_en(e.position().toPoint()) is not None
                       else Qt.ArrowCursor)
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        i = self._punto_en(e.position().toPoint())
        if i is not None:
            self.ir_a(i)
        else:
            self.siguiente()

    def wheelEvent(self, e):
        self._rueda += e.angleDelta().y()
        if self._ultima_rueda.elapsed() < 750 and abs(self._rueda) < 480:
            return
        if abs(self._rueda) >= 120:
            if self._rueda < 0:
                self.siguiente()
            else:
                self.anterior()
            self._rueda = 0
            self._ultima_rueda.restart()
        e.accept()

    # ================================================================ vida

    def showEvent(self, e):
        super().showEvent(e)
        self._ajustar_tamano()
        self._base = self._base_ventana()
        if self._base is not None:
            self._base.installEventFilter(self)
        self.setFocus()
        self._reloj.start()
        self._timer.start()
        if self._revelado:
            return
        self._revelado = True
        self._colocar_botones(animar=False)
        self.setWindowOpacity(0.0)
        self._anim_op = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_op.setDuration(520)
        self._anim_op.setStartValue(0.0)
        self._anim_op.setEndValue(1.0)
        self._anim_op.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_op.start()

    def hideEvent(self, e):
        self._timer.stop()
        if self._base is not None:
            self._base.removeEventFilter(self)
            self._base = None
        super().hideEvent(e)

    def _tick(self):
        dt = min(0.05, self._reloj.restart() / 1000.0)
        self._tg += dt
        self._tl += dt
        self._tl_ant += dt
        self.update()

    def avanzar(self, segundos):
        """Adelanta todos los relojes y termina las transiciones (pruebas y capturas)."""
        self._tg += segundos
        self._tl += segundos
        self._tl_ant += segundos
        for a in (self._anim_trans, self._anim_puntos, self._anim_sig, self._anim_op):
            if a is not None and a.state() == a.State.Running:
                a.setCurrentTime(a.duration())
                a.stop()
        self._p_trans = 1.0
        self._ant = None
        self._pos_puntos = float(self.indice)
        self.setWindowOpacity(1.0)
        self._colocar_botones(animar=False)
        self.update()

    # ================================================================ texto

    def _f(self, px, peso, titulo=False, tracking=0.0):
        clave = (round(px, 1), int(peso), titulo, round(tracking, 2))
        f = self._cache_fuentes.get(clave)
        if f is None:
            f = fuente(px, peso, titulo)
            if tracking:
                f.setLetterSpacing(QFont.AbsoluteSpacing, tracking)
            self._cache_fuentes[clave] = f
        return f

    @staticmethod
    def _envolver(texto, f, ancho):
        fm = QFontMetricsF(f)
        lineas, actual = [], []
        for pal in texto.split():
            if actual and fm.horizontalAdvance(" ".join(actual + [pal])) > ancho:
                lineas.append(actual)
                actual = [pal]
            else:
                actual.append(pal)
        if actual:
            lineas.append(actual)
        return lineas

    def _equilibrar(self, texto, f, ancho):
        """Reparte el título en líneas parecidas, sin dejar una palabra suelta abajo."""
        base = self._envolver(texto, f, ancho)
        n = len(base)
        if n < 2:
            return base
        lo, hi = ancho * 0.35, ancho
        for _ in range(14):
            medio = (lo + hi) / 2
            if len(self._envolver(texto, f, medio)) <= n:
                hi = medio
            else:
                lo = medio
        return self._envolver(texto, f, hi)

    def _layout(self, i):
        """Dónde va cada cosa en la diapositiva i, para el tamaño actual."""
        w, h = self.width(), self.height()
        clave = (i, w, h)
        if clave in self._cache_rutas.get("lay", {}):
            return self._cache_rutas["lay"][clave]
        d = DIAPOSITIVAS[i]
        fs = self._escala()
        centrada = d.get("centrada", False)
        ancho_split = w / float(h) >= 1.15
        margen = max(52 * fs, w * 0.065)
        top_ui, bot_ui = 92 * fs, 104 * fs
        if centrada:
            col = min(w * 0.86, 1100 * max(fs, 1.0))
            tpx = (66 if i == 0 else 56) * fs
            alin = Qt.AlignHCenter
        elif ancho_split:
            col = min(max(w * 0.38, 300), 560 * max(fs, 1.0))
            tpx = 46 * fs
            alin = Qt.AlignLeft
        else:
            col = min(w - 2 * margen, 640 * max(fs, 1.0))
            tpx = 40 * fs
            alin = Qt.AlignHCenter
        f_k = self._f(13 * fs, QFont.DemiBold, False, 2.4 * fs)
        f_t = self._f(tpx, QFont.Black, True)
        f_b = self._f((20 if centrada else 18.5) * fs, QFont.Normal)
        lin_t = self._equilibrar(d["titulo"], f_t, col)
        if i == 0 and len(lin_t) > 2:                      # el título de portada siempre en dos líneas como mucho
            lin_t = self._equilibrar(d["titulo"], self._f(tpx * 0.82, QFont.Black, True), col)
            f_t = self._f(tpx * 0.82, QFont.Black, True)
        lin_b = self._envolver(d["texto"], f_b, col * (0.86 if centrada else 1.0))
        fm_t, fm_b, fm_k = QFontMetricsF(f_t), QFontMetricsF(f_b), QFontMetricsF(f_k)
        lh_t, lh_b = fm_t.height() * 0.98, fm_b.height() * 1.34
        gap1, gap2 = 14 * fs, 20 * fs
        logo = (118 if i == 0 else 84) * fs if centrada else 0
        gap0 = 26 * fs if logo else 0
        alto = logo + gap0 + fm_k.height() + gap1 + lh_t * len(lin_t) + gap2 + lh_b * len(lin_b)
        if centrada:
            extra = (56 * fs + 40 * fs) if i == self.n - 1 else 0     # sitio para el botón final
            centro_y = (top_ui + (h - bot_ui)) / 2 - (extra / 2 if extra else 0) + (-18 * fs if i == 0 else 0)
            x0 = (w - col) / 2
            ilus = QRectF(0, 0, w, h)
        elif ancho_split:
            centro_y = (top_ui + (h - bot_ui)) / 2
            x0 = margen
            ix0 = margen + col + w * 0.03
            ilus = QRectF(ix0, top_ui, max(200, w - margen * 0.6 - ix0), h - top_ui - bot_ui)
        else:
            ilus_h = (h - top_ui - bot_ui) * 0.56
            ilus = QRectF(margen, top_ui, w - 2 * margen, ilus_h)
            x0 = (w - col) / 2
            centro_y = top_ui + ilus_h + 14 * fs + alto / 2
        y0 = centro_y - alto / 2
        L = dict(fs=fs, col=col, x0=x0, y0=y0, alin=alin, f_k=f_k, f_t=f_t, f_b=f_b, lin_t=lin_t, lin_b=lin_b,
                 lh_t=lh_t, lh_b=lh_b, gap0=gap0, gap1=gap1, gap2=gap2, logo=logo, ilus=ilus, alto=alto,
                 y_fin=y0 + alto, centrada=centrada, h_k=fm_k.height())
        self._cache_rutas.setdefault("lay", {})[clave] = L
        return L

    def _ruta_palabra(self, palabra, f):
        clave = (palabra, f.pixelSize(), f.weight(), f.family())
        r = self._cache_rutas.get(clave)
        if r is None:
            r = QPainterPath()
            fm = QFontMetricsF(f)
            r.addText(0, fm.ascent(), f, palabra)
            self._cache_rutas[clave] = r
        return r

    def _pintar_texto(self, p, i, tl, alfa_, dx):
        L = self._layout(i)
        pal = self._pal
        fs = L["fs"]
        x0, y = L["x0"] + dx, L["y0"]
        col = L["col"]
        d = DIAPOSITIVAS[i]

        def alinear(ancho_linea):
            if L["alin"] == Qt.AlignHCenter:
                return x0 + (col - ancho_linea) / 2
            return x0

        if L["logo"]:
            r = I.eo(I.tramo(tl, 0.0, 1.0))
            self._pintar_logo(p, x0 + col / 2, y + L["logo"] / 2 + (1 - r) * 18, L["logo"], alfa_ * r, 0.5 if i == 0 else 0.9)
            y += L["logo"] + L["gap0"]

        # etiqueta
        r = I.eo(I.tramo(tl, 0.25, 0.7))
        p.setOpacity(alfa_ * r)
        f_k = L["f_k"]
        fm = QFontMetricsF(f_k)
        et = f"{i:02d}   ·   {d['etiqueta']}" if 0 < i < self.n - 1 else d["etiqueta"]
        wk = fm.horizontalAdvance(et)
        p.setFont(f_k)
        p.setPen(QColor(pal.al))
        if L["alin"] == Qt.AlignHCenter:
            xk = x0 + (col - wk) / 2
        else:
            xk = x0
        p.drawText(QPointF(xk, y + fm.ascent() + (1 - r) * 12), et)
        if L["alin"] != Qt.AlignHCenter:
            p.setPen(QPen(I.alfa(pal.al, 150), 2 * fs, Qt.SolidLine, Qt.RoundCap))
            ls = I.eo(I.tramo(tl, 0.3, 0.8))
            p.drawLine(QPointF(xk + wk + 14 * fs, y + L["h_k"] * 0.55), QPointF(xk + wk + 14 * fs + 46 * fs * ls, y + L["h_k"] * 0.55))
        y += L["h_k"] + L["gap1"]

        # título, palabra por palabra, con brillo que lo recorre
        f_t = L["f_t"]
        fm_t = QFontMetricsF(f_t)
        espacio = fm_t.horizontalAdvance(" ")
        n_pal = 0
        brillo_fuerte = (i in (0, self.n - 1))
        for lin in L["lin_t"]:
            ancho_lin = sum(fm_t.horizontalAdvance(w_) for w_ in lin) + espacio * (len(lin) - 1)
            xl = alinear(ancho_lin)
            xx = xl
            for w_ in lin:
                ini = 0.38 + 0.085 * n_pal
                r = I.eo(I.tramo(tl, ini, 0.85))
                n_pal += 1
                ww = fm_t.horizontalAdvance(w_)
                if r > 0:
                    ruta = self._ruta_palabra(w_, f_t)
                    p.save()
                    p.setOpacity(alfa_ * r)
                    p.translate(xx, y + (1 - r) * 30 * fs)
                    base = QLinearGradient(0, 0, 0, fm_t.height())
                    base.setColorAt(0, QColor("#FFFFFF"))
                    base.setColorAt(1, I.mezcla("#FFFFFF", pal.al, 0.30 if brillo_fuerte else 0.18))
                    p.setPen(Qt.NoPen)
                    p.setBrush(base)
                    p.drawPath(ruta)
                    if brillo_fuerte or True:
                        # banda de luz que cruza el título cada pocos segundos
                        ciclo = 4.8
                        ft_ = ((self._tg - 0.9) % ciclo) / 2.2 if i in (0, self.n - 1) else ((self._tg + i * 0.7) % 7.0) / 2.6
                        if ft_ < 1.0:
                            ancho_blq = max(col, ancho_lin)
                            cx = (xl - xx) + ancho_blq * (-0.15 + 1.3 * ft_)
                            g = QLinearGradient(cx - 0.12 * ancho_blq, 0, cx + 0.12 * ancho_blq, fm_t.height() * 0.3)
                            fuerza = 255 if brillo_fuerte else 150
                            g.setColorAt(0, I.alfa(pal.al, 0))
                            g.setColorAt(0.5, I.alfa(I.mezcla(pal.al, "#FFFFFF", 0.65), fuerza))
                            g.setColorAt(1, I.alfa(pal.al, 0))
                            p.setBrush(g)
                            p.drawPath(ruta)
                    p.restore()
                xx += ww + espacio
            y += L["lh_t"]
        y += L["gap2"] - (L["lh_t"] - fm_t.height() * 0.98)

        # cuerpo, línea por línea
        f_b = L["f_b"]
        fm_b = QFontMetricsF(f_b)
        p.setFont(f_b)
        cuerpo = I.mezcla(C["texto2"], "#FFFFFF", 0.55)
        for k, lin in enumerate(L["lin_b"]):
            r = I.eo(I.tramo(tl, 0.9 + 0.11 * k, 0.8))
            p.setOpacity(alfa_ * r)
            p.setPen(cuerpo)
            txt = " ".join(lin)
            wl = fm_b.horizontalAdvance(txt)
            if L["alin"] == Qt.AlignHCenter:
                xl = x0 + (col - wl) / 2
            else:
                xl = x0
            p.drawText(QPointF(xl, y + fm_b.ascent() + (1 - r) * 16), txt)
            y += L["lh_b"]
        p.setOpacity(1.0)

    # ================================================================ logo

    def _pintar_logo(self, p, cx, cy, tam, a, fuerza):
        """El logo con un brillo (shimmer) que lo cruza en diagonal, cada pocos segundos."""
        from .iconos import icono_app
        lado = int(tam)
        pm = self._logo_cache.get(lado)
        if pm is None:
            pm = icono_app(lado)
            self._logo_cache[lado] = pm
        pal = self._pal
        p.save()
        p.setOpacity(a)
        pulso = 0.5 + 0.5 * math.sin(self._tg * 1.6)
        g = QRadialGradient(QPointF(cx, cy), tam * 1.0)
        g.setColorAt(0, I.alfa(pal.al, 90 + 40 * pulso))
        g.setColorAt(1, I.alfa(pal.al, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), tam * 1.0, tam * 1.0)
        p.drawPixmap(QPointF(cx - pm.width() / 2 / pm.devicePixelRatio(), cy - pm.height() / 2 / pm.devicePixelRatio()), pm)
        # brillo recortado a la silueta del logo
        ft = ((self._tg - 0.6) % 4.2) / 1.6
        if ft < 1.0:
            img = QImage(pm.size(), QImage.Format_ARGB32_Premultiplied)
            img.setDevicePixelRatio(pm.devicePixelRatio())
            img.fill(0)
            q = QPainter(img)
            q.drawPixmap(0, 0, pm)
            q.setCompositionMode(QPainter.CompositionMode_SourceAtop)
            ancho = pm.width() / pm.devicePixelRatio()
            x = -ancho * 0.3 + ancho * 1.6 * ft
            gg = QLinearGradient(x - ancho * 0.12, 0, x + ancho * 0.12, ancho * 0.28)
            gg.setColorAt(0, QColor(255, 255, 255, 0))
            gg.setColorAt(0.5, QColor(255, 255, 255, int(235 * fuerza + 20)))
            gg.setColorAt(1, QColor(255, 255, 255, 0))
            q.fillRect(QRectF(0, 0, ancho, ancho), gg)
            q.end()
            p.drawImage(QPointF(cx - ancho / 2, cy - ancho / 2), img)
        p.restore()

    # ================================================================ fondo

    def _pintar_fondo(self, p, tono_grados):
        w, h = self.width(), self.height()
        esc = 3
        bw, bh = max(2, w // esc), max(2, h // esc)
        if self._fondo_img is None or self._fondo_img.width() != bw or self._fondo_img.height() != bh:
            self._fondo_img = QImage(bw, bh, QImage.Format_RGB32)
        img = self._fondo_img
        q = QPainter(img)
        q.setRenderHint(QPainter.Antialiasing, True)
        pal, tg = self._pal, self._tg
        base = QLinearGradient(0, 0, 0, bh)
        base.setColorAt(0, I.mezcla(pal.fondo, pal.ac, 0.09))
        base.setColorAt(0.6, I.mezcla(pal.fondo, pal.panel, 0.7))
        base.setColorAt(1, I.mezcla(pal.fondo, "#000000", 0.45))
        q.fillRect(img.rect(), base)
        q.setCompositionMode(QPainter.CompositionMode_Plus)
        matices = (0, 38, -46, 84, -12)
        for k in range(5):
            fx, fy = 0.07 + 0.03 * k, 0.06 + 0.025 * k
            cx = bw * (0.5 + 0.42 * math.sin(tg * fx * 2.2 + k * 1.9))
            cy = bh * (0.5 + 0.36 * math.cos(tg * fy * 2.4 + k * 2.7))
            rad = max(bw, bh) * (0.42 + 0.08 * math.sin(tg * 0.2 + k))
            col = I.tono(pal.ac, matices[k] + tono_grados, 0.6, 0.95)
            g = QRadialGradient(QPointF(cx, cy), rad)
            g.setColorAt(0, I.alfa(col, 78))
            g.setColorAt(0.55, I.alfa(col, 26))
            g.setColorAt(1, I.alfa(col, 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(cx, cy), rad, rad)
        # cortinas de aurora
        for k in range(3):
            col = I.tono(pal.ac, matices[(k + 1) % 5] + tono_grados + 20, 0.55, 0.95)
            ruta = QPainterPath()
            base_y = bh * (0.22 + 0.14 * k)
            ruta.moveTo(0, 0)
            for s in range(0, 41):
                x = bw * s / 40
                y = base_y + bh * 0.09 * math.sin(s * 0.33 + tg * (0.28 + 0.1 * k) + k * 2) \
                    + bh * 0.05 * math.sin(s * 0.8 - tg * 0.4 + k)
                ruta.lineTo(x, y)
            ruta.lineTo(bw, 0)
            ruta.closeSubpath()
            g = QLinearGradient(0, 0, 0, base_y + bh * 0.2)
            g.setColorAt(0, I.alfa(col, 0))
            g.setColorAt(0.75, I.alfa(col, 38))
            g.setColorAt(1, I.alfa(col, 0))
            q.setBrush(g)
            q.drawPath(ruta)
        q.setCompositionMode(QPainter.CompositionMode_SourceOver)
        vg = QRadialGradient(QPointF(bw / 2, bh * 0.48), max(bw, bh) * 0.78)
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(0.62, QColor(0, 0, 0, 40))
        vg.setColorAt(1.0, QColor(0, 0, 0, 175))
        q.setBrush(vg)
        q.drawRect(img.rect())
        q.end()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(0, 0, w, h), img)
        # polvo de luz que sube despacio
        for k in range(46):
            sp = 6 + 14 * I.azar(k, 1)
            y = h - ((tg * sp + I.azar(k, 2) * h * 1.2) % (h * 1.1)) + h * 0.05
            x = w * I.azar(k, 3) + 12 * math.sin(tg * 0.5 + k)
            tw = 0.5 + 0.5 * math.sin(tg * (1 + I.azar(k, 4)) + k)
            r = (0.8 + 1.8 * I.azar(k, 5)) * self._escala()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(70 * tw * (0.4 + I.azar(k, 6)))))
            p.drawEllipse(QPointF(x, y), r, r)

    # ================================================================ pintura

    def _pintar_diap(self, p, i, tl, alfa_, off):
        """`off`: -1..1, desplazamiento relativo (negativo: se va hacia la izquierda)."""
        w, h = self.width(), self.height()
        L = self._layout(i)
        d = DIAPOSITIVAS[i]
        dxi, dxt = off * 0.11 * w, off * 0.06 * w
        r = L["ilus"]
        u = min(r.width(), r.height()) / 100.0
        esc = 1.0 - 0.06 * abs(off)
        p.save()
        p.setClipRect(QRectF(0, 0, w, h))
        p.translate(r.center().x() + dxi * (0.5 if L["centrada"] else 1.0), r.center().y())
        p.scale(u * esc, u * esc)
        X = I.Ctx(self._pal, tl, self._tg, r.width() / 2 / (u * esc), r.height() / 2 / (u * esc), alfa_)
        p.setOpacity(alfa_)
        I.ILUSTRACIONES[d["clave"]](p, X)
        p.restore()
        p.save()
        self._pintar_texto(p, i, tl, alfa_, dxt)
        p.restore()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        from .estilos import C as _C
        self._pal = I.Paleta(_C)
        w, h = self.width(), self.height()
        e = self._p_trans
        # el tono del fondo pasa suavemente de una diapositiva a la siguiente
        t_nuevo = DIAPOSITIVAS[self.indice]["tono"]
        t_viejo = DIAPOSITIVAS[self._ant]["tono"] if self._ant is not None else t_nuevo
        self._pintar_fondo(p, t_viejo + (t_nuevo - t_viejo) * e)
        if self._ant is not None and e < 1.0:
            ee = I.eio(e) if False else e
            self._pintar_diap(p, self._ant, self._tl_ant, I.clamp(1 - ee * 1.7), -self._dir * ee)
            self._pintar_diap(p, self.indice, self._tl, I.clamp((ee - 0.15) / 0.85), self._dir * (1 - ee))
        else:
            self._pintar_diap(p, self.indice, self._tl, 1.0, 0.0)
        p.setOpacity(1.0)
        self._pintar_marco(p)

    def _pintar_marco(self, p):
        """Marca arriba, puntos de progreso, estado de la descarga."""
        w, h = self.width(), self.height()
        fs = self._escala()
        pal = self._pal
        # marca arriba a la izquierda (la portada ya lleva el logo grande)
        if self.indice > 0:
            from .iconos import icono_app
            lado = round(30 * fs)
            pm = self._logo_cache.get(("m", lado)) or icono_app(lado)
            self._logo_cache[("m", lado)] = pm
            a = I.clamp(self._tl / 0.8) if self._ant == 0 or self._ant is None else 1.0
            p.setOpacity(a)
            p.drawPixmap(round(56 * fs), round(30 * fs), pm)
            p.setPen(QColor("#FFFFFF"))
            p.setFont(self._f(17 * fs, QFont.Black, True))
            p.drawText(QPointF(56 * fs + lado / pm.devicePixelRatio() + 10 * fs, 30 * fs + lado * 0.72), "Caudal")
            p.setOpacity(1.0)
        # puntos de progreso
        n = self.n
        base_w, pill = 8 * fs, 30 * fs
        sep = 9 * fs
        anchos = [base_w + (pill - base_w) * max(0.0, 1 - abs(self._pos_puntos - k)) for k in range(n)]
        total = sum(anchos) + sep * (n - 1)
        x = (w - total) / 2
        y = self._y_puntos()
        self._puntos = []
        p.setPen(Qt.NoPen)
        for k in range(n):
            r = QRectF(x, y - base_w / 2, anchos[k], base_w)
            self._puntos.append(r)
            peso = max(0.0, 1 - abs(self._pos_puntos - k))
            if peso > 0:
                col = I.mezcla("#FFFFFF", pal.al, 0.4 * (1 - peso) + 0.0)
                col.setAlpha(int(70 + 185 * peso))
            else:
                col = QColor(255, 255, 255, 120 if k < self._pos_puntos else 62)
            p.setBrush(col)
            p.drawRoundedRect(r, base_w / 2, base_w / 2)
            x += anchos[k] + sep
        # descarga
        if self._estado:
            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(self._f(14 * fs, QFont.DemiBold))
            p.drawText(QRectF(w * 0.15, h - 140 * fs, w * 0.7, 26 * fs), int(Qt.AlignHCenter | Qt.AlignVCenter), self._estado)
        if self._prog > 0:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRect(QRectF(0, h - 5, w, 5))
            p.setBrush(QColor(pal.al))
            p.drawRect(QRectF(0, h - 5, w * self._prog, 5))


def hay_presentacion(version_publicada):
    """True si la actualización publicada es de la edición que lleva esta presentación."""
    return _version.es_de_la_edicion(version_publicada) and not _version.alcanza_edicion(_version.VERSION)
