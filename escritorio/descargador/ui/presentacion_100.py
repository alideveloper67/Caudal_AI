# -*- coding: utf-8 -*-
"""Presentación «Somos 100»: el agradecimiento cuando Caudal llega a 100 personas.

Sale UNA vez por dispositivo (ajustes["presentacion_100_vista"]) y solo cuando el total de
usuarios que devuelve Supabase (RPC total_usuarios) llega a 100. Sigue el guion
GUION_100.md: cinco diapositivas con los mismos textos en Windows y en Android.

Estilo y mecánica de presentacion_grande: aurora de fondo que respira, fundido con
desplazamiento entre diapositivas, puntos de progreso, entradas escalonadas y un reloj
de QTimer a ~60 FPS que solo corre mientras la ventana está abierta. Sin marco y a la
medida de la ventana de Caudal; la música no se toca.
"""

import json
import math
import random
import urllib.request

from PySide6.QtCore import (QElapsedTimer, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRectF,
                            QTimer, QUrl, Qt, QVariantAnimation)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication, QDialog

from . import ilustraciones_grandes as I
from .componentes import fuente
from .estilos import C
from .presentacion_grande import _Boton

SUPABASE_TOTAL = "https://nztirmwqykbxadidpzzt.supabase.co/rest/v1/rpc/total_usuarios"
CLAVE_PUBLICA = "sb_publishable_ga4gKRk0czj044G-xPptSQ_BZ_sTZLl"
META = 100
CLAVE_VISTA = "presentacion_100_vista"
SITIO = "https://caudal-musica.netlify.app"
URL_MOSTRAR = "caudal-musica.netlify.app"
TEXTO_COMPARTIR = "Escucho mi música con Caudal 🎵 Únete: https://caudal-musica.netlify.app"
FIRMA = "— Con cariño, el equipo de Caudal 💜"

# Tarjetas de la diapositiva 3: título y una línea (texto exacto del guion)
NOVEDADES = [
    ("Escenarios vivos", "11 ilustraciones animadas que reaccionan a la música: Cyberpunk, Japón antiguo, Goku, "
                         "Hajime no Ippo, Kaneki, Kuromi, Cinnamoroll y más."),
    ("Interactivos", "mueve el ratón o el dedo y suelta partículas; en Goku e Ippo, los graves sacuden la pantalla."),
    ("Tu imagen o tu GIF", "pon de fondo lo que quieras."),
    ("Letra que resalta", "más legible sobre cualquier fondo, a tiempo con la música y con traducción."),
    ("Escena a tu gusto", "mueve, agranda u oculta cada pieza; Restablecer lo devuelve todo."),
    ("Para tus estados", "comparte tu escenario con la canción que suena."),
    ("Avisos en Android", "mensajes, solicitudes de amistad y novedades aunque la app esté cerrada."),
    ("Progreso gamer en todos tus equipos", "tu nivel se suma entre el celular y la PC."),
    ("Más fluido", "Caudal abre y responde más rápido."),
]

# Seis bloques de la diapositiva 3 (texto exacto del guion): título y puntos (chips)
BLOQUES = [
    ("Escucha", ["Música sin límites y videoclips", "Descargas MP3, M4A y FLAC", "Sube tu propia música",
                 "Letras traducidas y karaoke", "Ecualizador, DJ y temporizador"]),
    ("Descubre", ["«Descubre para ti» cada día", "Música que aprende de ti", "Modos de escucha",
                  "Similares y radios", "¿Qué suena?", "Máquina del tiempo", "Resumen semanal y anual"]),
    ("Juntos", ["Escuchar juntos con chat", "Fiestas por QR", "Mezcla de compatibilidad",
                "Listas con 50 amigos", "Amigos, mensajes y dedicatorias", "Directorio", "Tu cumpleaños"]),
    ("Hazlo tuyo", ["Mascotas", "Temas, fondos y tu imagen", "Vinilo, Casete o Neón",
                    "Perfil con portada y GIF", "Escenarios vivos y escena"]),
    ("Vive tu música", ["Modo gamer", "Modo estudio y Pomodoro", "Logros", "Visualizador", "Despertador",
                        "Modo coche", "Chromecast"]),
    ("Comparte y cuida lo tuyo", ["Tarjetas para tus estados", "Importa de Spotify, Apple y YouTube",
                                  "Copia de seguridad", "Sincronizado en todos tus equipos"]),
]
# icono de cada bloque (índice de _icono)
ICONOS_BLOQUE = [5, 8, 1, 2, 7, 3]

# arriba: alto del dibujo sobre el título; abajo: alto del bloque bajo el texto (tarjetas o enlace y botones)
DIAPOSITIVAS = [
    dict(tipo="contador", titulo="Somos 100",
         texto="100 personas eligieron Caudal para acompañar su música. Gracias por estar aquí.", arriba=170),
    dict(tipo="corazon", titulo="Gracias por confiar en Caudal",
         texto="Caudal empezó como un proyecto pequeño, hecho con cariño. Hoy suena en cien vidas. Cada canción "
               "que pusiste, cada lista que armaste y cada mensaje que nos mandaste lo hizo crecer.", arriba=150),
    # recorrido con demostraciones de verdad: cada una se ve funcionando dentro de una pantalla
    dict(tipo="demo", demo="escenarios", titulo="Escenarios vivos",
         texto="11 ilustraciones que se mueven con tu música. Pasa el ratón y suelta partículas; en Goku e Ippo, "
               "los graves sacuden la pantalla."),
    dict(tipo="demo", demo="letra", titulo="Letras que se cantan contigo",
         texto="La letra entra palabra a palabra, a tiempo con la canción, legible sobre cualquier fondo y con "
               "traducción."),
    dict(tipo="demo", demo="escena", titulo="La escena de escritorio",
         texto="Tu música a pantalla completa: mueve, agranda u oculta cada pieza a tu gusto."),
    dict(tipo="demo", demo="juntos", titulo="Escuchen juntos",
         texto="La misma canción al mismo segundo, con chat y reacciones. Arma listas con hasta 50 amigos."),
    dict(tipo="demo", demo="descubre", titulo="Música que te conoce",
         texto="«Descubre para ti» cada día, radios, canciones similares y tu máquina del tiempo."),
    dict(tipo="demo", demo="mascotas", titulo="Tus mascotas",
         texto="Más de 60 compañeros que caminan por tu reproductor, celebran contigo y hasta tu cumpleaños."),
    dict(tipo="demo", demo="gamer", titulo="Modo gamer",
         texto="Niveles, misiones y rachas que se suman entre tu celular y tu PC."),
    dict(tipo="demo", demo="estudio", titulo="Modo estudio",
         texto="Pomodoro, sonidos de ambiente y una vista sin distracciones para concentrarte."),
    dict(tipo="rejilla", titulo="Todo lo que Caudal te ofrece",
         texto="Gratis, para siempre, en Android, Windows y el navegador, con tu cuenta sincronizada.", grid=True),
    dict(tipo="tarjetas", titulo="Lo nuevo que vas a disfrutar", texto="", abajo=436),
    dict(tipo="logo", titulo="Lo que viene: la comunidad de Caudal",
         texto="En la próxima actualización, Caudal se convierte en una comunidad para toda la gente que disfruta "
               "la música: un lugar para descubrir, compartir y conocer a quienes sienten las canciones como tú.",
         pie="Seguiremos creciendo y mejorando. Esto recién empieza.", arriba=130),
    dict(tipo="enlace", titulo="Comparte Caudal con el mundo",
         texto="Si Caudal te acompaña, invita a tus amigos y a tu familia. Cada persona que llega hace la "
               "comunidad más grande.", abajo=190),
]


def _envolver(texto, f, ancho):
    """Parte el texto en líneas (listas de palabras) que quepan en `ancho`."""
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


def _icono(p, cx, cy, r, k, color):
    """Icono sencillo de cada tarjeta (k = posición de la tarjeta), dibujado con QPainter."""
    p.save()
    p.setPen(I.lapiz(color, max(1.6, r * 0.16)))
    p.setBrush(Qt.NoBrush)
    tipo = k % 9
    if tipo == 0:                                   # escenario: montañas
        ruta = QPainterPath()
        ruta.moveTo(cx - r, cy + r * 0.6)
        ruta.lineTo(cx - r * 0.2, cy - r * 0.6)
        ruta.lineTo(cx + r * 0.2, cy + r * 0.1)
        ruta.lineTo(cx + r * 0.45, cy - r * 0.3)
        ruta.lineTo(cx + r, cy + r * 0.6)
        p.drawPath(ruta)
    elif tipo == 1:                                 # interactivo: aro con partículas
        p.drawEllipse(QPointF(cx, cy), r * 0.7, r * 0.7)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for dx, dy in ((-r * 0.95, -r * 0.6), (r * 0.9, -r * 0.8), (r * 0.2, r * 0.95)):
            p.drawEllipse(QPointF(cx + dx, cy + dy), r * 0.16, r * 0.16)
    elif tipo == 2:                                 # imagen: marco con sol y montaña
        p.drawRoundedRect(QRectF(cx - r, cy - r * 0.8, r * 2, r * 1.6), r * 0.2, r * 0.2)
        p.drawEllipse(QPointF(cx + r * 0.4, cy - r * 0.3), r * 0.18, r * 0.18)
        p.drawLine(QPointF(cx - r * 0.8, cy + r * 0.5), QPointF(cx - r * 0.1, cy - r * 0.1))
    elif tipo == 3:                                 # letra: líneas de texto
        for j, anc in enumerate((1.0, 0.8, 0.6)):
            y = cy - r * 0.6 + j * r * 0.6
            p.drawLine(QPointF(cx - r * anc, y), QPointF(cx + r * anc, y))
    elif tipo == 4:                                 # escena: dos controles deslizantes
        for j, pos in enumerate((-0.4, 0.3)):
            y = cy - r * 0.45 + j * r * 0.9
            p.drawLine(QPointF(cx - r, y), QPointF(cx + r, y))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(cx + pos * r, y), r * 0.18, r * 0.18)
            p.setPen(I.lapiz(color, max(1.6, r * 0.16)))
            p.setBrush(Qt.NoBrush)
    elif tipo == 5:                                 # estados: círculo con triángulo de reproducción
        p.drawEllipse(QPointF(cx, cy), r, r)
        ruta = QPainterPath()
        ruta.moveTo(cx - r * 0.3, cy - r * 0.45)
        ruta.lineTo(cx + r * 0.5, cy)
        ruta.lineTo(cx - r * 0.3, cy + r * 0.45)
        ruta.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawPath(ruta)
    elif tipo == 6:                                 # avisos: campana
        p.drawArc(QRectF(cx - r * 0.7, cy - r * 0.8, r * 1.4, r * 1.4), 0, 180 * 16)
        p.drawLine(QPointF(cx - r * 0.7, cy + r * 0.1), QPointF(cx - r * 0.7, cy + r * 0.45))
        p.drawLine(QPointF(cx + r * 0.7, cy + r * 0.1), QPointF(cx + r * 0.7, cy + r * 0.45))
        p.drawLine(QPointF(cx - r, cy + r * 0.45), QPointF(cx + r, cy + r * 0.45))
    elif tipo == 7:                                 # progreso gamer: estrella
        p.setPen(Qt.NoPen)
        I.estrella(p, cx, cy, r, r * 0.45, QColor(color))
    else:                                           # más fluido: destello
        p.setPen(Qt.NoPen)
        I.destello(p, cx, cy, r, QColor(color))
    p.restore()


def _ruta_corazon(cx, cy, s):
    ruta = QPainterPath()
    ruta.moveTo(cx, cy + s * 0.55)
    ruta.cubicTo(cx + s * 0.95, cy + s * 0.05, cx + s * 0.6, cy - s * 0.75, cx, cy - s * 0.3)
    ruta.cubicTo(cx - s * 0.6, cy - s * 0.75, cx - s * 0.95, cy + s * 0.05, cx, cy + s * 0.55)
    ruta.closeSubpath()
    return ruta


class Presentacion100(QDialog):
    """Las cinco diapositivas del guion. `ctx` (opcional) pone el aviso «Enlace copiado»."""

    DURACION = 900               # ms de la transición entre diapositivas
    CONTEO_MS = 2200             # el contador sube de 0 a 100 en ~2,2 s

    def __init__(self, padre=None, ctx=None):
        super().__init__(padre)
        self.ctx = ctx
        self.n = len(DIAPOSITIVAS)
        self.indice = 0
        self._ant = None
        self._dir = 1
        self._p_trans = 1.0
        self._tg = 0.0
        self._tl = 0.0
        self._tl_ant = 0.0
        self._pos_puntos = 0.0
        self._cont = 0.0
        self._exploto = False
        self._cache_demos = {}
        self._t_explosion = 0.0
        self._particulas = []
        self._msg = ""
        self._msg_t0 = -99.0
        self._rueda = 0
        self._ultima_rueda = QElapsedTimer()
        self._ultima_rueda.start()
        self._revelado = False
        self._base = None
        self._fondo_img = None
        self._cache_fuentes = {}
        self._cache_lay = {}
        self._logo_cache = {}
        self._puntos = []
        self._pal = I.Paleta(C)
        self._anim_trans = None
        self._anim_puntos = None
        self._anim_op = None
        self._anim_cont = None

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle("Somos 100")
        self.setAccessibleName("Somos 100")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(760, 520)

        self.bt_ant = self._boton("Atrás", self.anterior, "Diapositiva anterior")
        self.bt_sig = self._boton("Siguiente", self.siguiente, "Diapositiva siguiente", principal=True)
        self.bt_copiar = self._boton("Copiar enlace", self._copiar, "Copiar enlace")
        self.bt_compartir = self._boton("Compartir Caudal", self._compartir, "Compartir Caudal")
        self.bt_seguir = self._boton("Seguir escuchando", self.accept, "Seguir escuchando", principal=True)

        self._reloj = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(16)                  # ~60 FPS, solo mientras la ventana está abierta
        self._timer.timeout.connect(self._tick)

        self._ajustar_tamano()
        self._actualizar_botones()
        self._colocar_botones()

    def _boton(self, texto, accion, nombre, principal=False):
        b = _Boton(texto, self, principal)
        b.setCursor(Qt.PointingHandCursor)
        b.setAutoDefault(False)
        b.setFocusPolicy(Qt.TabFocus)
        b.setAccessibleName(nombre)
        b.clicked.connect(accion)
        return b

    # ================================================================ tamaño

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
        self.setGeometry(esq.x(), esq.y(), max(760, ancho), max(520, alto))

    def eventFilter(self, obj, e):
        if obj is self._base and e.type() in (QEvent.Resize, QEvent.Move):
            self._ajustar_tamano()
        return super().eventFilter(obj, e)

    def _escala(self):
        return max(0.72, min(1.45, min(self.width() / 1200.0, self.height() / 720.0)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._cache_lay.clear()
        self._estilos()
        self._colocar_botones()

    # ================================================================ botones

    def _estilos(self):
        fs = self._escala()
        self.bt_ant.configurar(fs)
        self.bt_sig.configurar(fs)
        for b in (self.bt_copiar, self.bt_compartir, self.bt_seguir):
            b.configurar(fs, 0.9)

    def _actualizar_botones(self):
        ultimo = self.indice == self.n - 1
        self.bt_sig.setVisible(not ultimo)
        for b in (self.bt_copiar, self.bt_compartir, self.bt_seguir):
            b.setVisible(ultimo)
        self.bt_ant.setVisible(self.indice > 0)
        d = DIAPOSITIVAS[self.indice]
        self.setAccessibleDescription(f"Diapositiva {self.indice + 1} de {self.n}. {d['titulo']}.")
        self._estilos()

    def _y_puntos(self):
        return self.height() - round(46 * self._escala())

    def _colocar_botones(self):
        fs = self._escala()
        w = self.width()
        y_pie = self._y_puntos()
        self.bt_ant.move(round(56 * fs), round(y_pie - self.bt_ant.height() / 2))
        self.bt_sig.move(round(w - 56 * fs - self.bt_sig.width()), round(y_pie - self.bt_sig.height() / 2))
        if self.indice == self.n - 1:
            L = self._layout(self.indice)
            botones = [self.bt_copiar, self.bt_compartir, self.bt_seguir]
            gap = 14 * fs
            total = sum(b.width() for b in botones) + gap * (len(botones) - 1)
            x = (w - total) / 2
            for b in botones:
                b.move(round(x), round(L["y_botones"] - b.height() / 2))
                x += b.width() + gap
        for b in (self.bt_ant, self.bt_sig, self.bt_copiar, self.bt_compartir, self.bt_seguir):
            b.raise_()

    # ================================================================ navegación

    def ir_a(self, i, animar=True):
        i = max(0, min(self.n - 1, int(i)))
        if i == self.indice:
            return
        self._dir = 1 if i > self.indice else -1
        self._ant = self.indice
        self._tl_ant = self._tl
        self.indice = i
        self._tl = 0.0
        self._actualizar_botones()
        self._colocar_botones()
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

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Right, Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Space):
            self.siguiente()
        elif k in (Qt.Key_Left, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_Backspace):
            self.anterior()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            if self.indice == self.n - 1:
                self.accept()
            else:
                self.siguiente()
        elif k == Qt.Key_Home:
            self.ir_a(0)
        elif k == Qt.Key_End:
            self.ir_a(self.n - 1)
        else:
            super().keyPressEvent(e)

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

    # ================================================================ botones de la última diapositiva

    def _avisar(self, texto):
        self._msg, self._msg_t0 = texto, self._tg
        if self.ctx is not None and hasattr(self.ctx, "avisar"):
            try:
                self.ctx.avisar(texto)
            except Exception:  # noqa: BLE001 - un aviso nunca debe romper la presentación
                pass
        self.update()

    def _copiar(self):
        QApplication.clipboard().setText(SITIO)
        self._avisar("Enlace copiado")

    def _compartir(self):
        QApplication.clipboard().setText(TEXTO_COMPARTIR)
        QDesktopServices.openUrl(QUrl(SITIO))
        self._avisar("Texto para compartir copiado")

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
        self._colocar_botones()
        self.setWindowOpacity(0.0)
        self._anim_op = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_op.setDuration(520)
        self._anim_op.setStartValue(0.0)
        self._anim_op.setEndValue(1.0)
        self._anim_op.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_op.start()
        self._iniciar_conteo()

    def hideEvent(self, e):
        self._timer.stop()
        if self._base is not None:
            self._base.removeEventFilter(self)
            self._base = None
        super().hideEvent(e)

    def _iniciar_conteo(self):
        self._anim_cont = QVariantAnimation(self)
        self._anim_cont.setStartValue(0.0)
        self._anim_cont.setEndValue(float(META))
        self._anim_cont.setDuration(self.CONTEO_MS)
        self._anim_cont.setEasingCurve(QEasingCurve.InOutSine)
        self._anim_cont.valueChanged.connect(self._poner_cont)
        self._anim_cont.finished.connect(self._explotar)
        self._anim_cont.start()

    def _poner_cont(self, v):
        self._cont = float(v)

    def _explotar(self):
        """Al llegar a 100: una pequeña explosión de partículas de luz (una sola vez)."""
        if self._exploto:
            return
        self._exploto = True
        self._t_explosion = self._tg
        self._cont = float(META)
        fs = self._escala()
        L = self._layout(0)
        cx, cy = L["cx"], L["y0"] + L["arriba"] / 2
        pal = self._pal
        colores = [pal.al, pal.c2, QColor("#FFFFFF"), QColor(pal.oro)]
        for k in range(70):
            ang = 2 * math.pi * k / 70 + random.uniform(-0.12, 0.12)
            v = random.uniform(120, 340) * fs
            self._particulas.append(dict(x=cx, y=cy, vx=math.cos(ang) * v, vy=math.sin(ang) * v,
                                         t0=self._tg, r=random.uniform(1.2, 3.0) * fs,
                                         col=random.choice(colores)))
        # confeti: papelitos de colores que suben, giran y caen despacio
        for k in range(60):
            ang = random.uniform(-math.pi * 0.95, -math.pi * 0.05)
            v = random.uniform(220, 520) * fs
            self._particulas.append(dict(x=cx, y=cy, vx=math.cos(ang) * v, vy=math.sin(ang) * v, t0=self._tg,
                                         r=random.uniform(3.0, 5.5) * fs, col=random.choice(colores),
                                         confeti=True, giro=random.uniform(-9, 9), fase=random.uniform(0, 6.28)))
        self.update()

    def _tick(self):
        dt = min(0.05, self._reloj.restart() / 1000.0)
        self._tg += dt
        self._tl += dt
        self._tl_ant += dt
        self.update()

    def avanzar(self, segundos):
        """Adelanta los relojes y termina las transiciones (pruebas y capturas)."""
        self._tg += segundos
        self._tl += segundos
        self._tl_ant += segundos
        for a in (self._anim_trans, self._anim_puntos, self._anim_op, self._anim_cont):
            if a is not None and a.state() == a.State.Running:
                a.stop()
        if self._anim_cont is not None:
            self._explotar()
        self._p_trans = 1.0
        self._ant = None
        self._pos_puntos = float(self.indice)
        self.setWindowOpacity(1.0)
        self._colocar_botones()
        self.update()

    # ================================================================ texto y disposición

    def _f(self, px, peso, titulo=False):
        clave = (round(px, 1), int(peso), titulo)
        f = self._cache_fuentes.get(clave)
        if f is None:
            f = fuente(px, peso, titulo)
            self._cache_fuentes[clave] = f
        return f

    def _layout(self, i):
        """Dónde va cada cosa en la diapositiva i, para el tamaño actual (coordenadas absolutas)."""
        w, h = self.width(), self.height()
        clave = (i, w, h)
        L = self._cache_lay.get(clave)
        if L is not None:
            return L
        d = DIAPOSITIVAS[i]
        tipo = d["tipo"]
        fs = self._escala()
        if tipo == "rejilla":
            col = min(w * 0.94, 1100 * fs)
        elif tipo == "demo":
            col = min(w * 0.86, 980 * fs)
        elif tipo == "tarjetas":
            col = min(w * 0.9, 1040 * fs)
        else:
            col = min(w * 0.82, 820 * fs)
        f_t = self._f((36 if tipo == "demo" else 44) * fs, QFont.Black, True)
        f_b = self._f(19 * fs, QFont.Normal)
        f_p = self._f(15 * fs, QFont.Normal)
        fm_t, fm_b, fm_p = QFontMetricsF(f_t), QFontMetricsF(f_b), QFontMetricsF(f_p)
        lin_t = _envolver(d["titulo"], f_t, col)
        lin_b = _envolver(d["texto"], f_b, col * 0.92) if d.get("texto") else []
        lin_p = _envolver(d["pie"], f_p, col * 0.9) if d.get("pie") else []
        lh_t, lh_b, lh_p = fm_t.height() * 0.98, fm_b.height() * 1.36, fm_p.height() * 1.3

        tarjetas = []
        if tipo == "tarjetas":
            cw = (col - 2 * 14 * fs) / 3
            f_tt, f_td = self._f(15 * fs, QFont.Bold), self._f(13 * fs, QFont.Normal)
            for tit, desc in NOVEDADES:
                tarjetas.append((_envolver(tit, f_tt, cw - 84 * fs), _envolver(desc, f_td, cw - 84 * fs)))

        arriba = d.get("arriba", 0) * fs
        abajo = d.get("abajo", 0) * fs
        gap_v, gap_t, gap_b = 26 * fs, 18 * fs, 22 * fs
        # bloque de texto, relativo a su borde superior
        y = arriba + (gap_v if arriba else 0.0)
        y_tit = y
        y += len(lin_t) * lh_t
        y_body = y + gap_t
        if lin_b:
            y = y_body + len(lin_b) * lh_b
        y_pie = y + gap_b
        if lin_p:
            y = y_pie + len(lin_p) * lh_p
        grid = None
        demo = None
        if tipo == "demo":
            # la pantalla de la demo ocupa lo que quede (16:9), centrada bajo el texto
            disponible = (h - 100 * fs) - 60 * fs - y - gap_b
            alto_d = max(160 * fs, disponible)
            ancho_d = min(col, alto_d * 16 / 9)
            alto_d = ancho_d * 9 / 16
            demo = (ancho_d, alto_d)
            abajo = alto_d
        if tipo == "rejilla":
            # la rejilla ocupa lo que quede; si no cabe a 1280x720, se reduce el texto de los chips (mínimo 12 px)
            disponible = (h - 100 * fs) - 70 * fs - y - gap_b
            px = 14 * fs
            grid = self._grid(col, fs, px)
            while grid["total"] > disponible and px > 12:
                px = max(12.0, px - 0.5)
                grid = self._grid(col, fs, px)
            abajo = grid["total"]
        y_abajo = y + (gap_b if abajo else 0.0)
        alto = y_abajo + abajo
        area_top, area_bot = (40 if tipo == "demo" else 70) * fs, h - 100 * fs
        y0 = area_top + max(0.0, (area_bot - area_top - alto) / 2.0)

        L = dict(fs=fs, cx=w / 2.0, col=col, arriba=arriba, y0=y0,
                 f_t=f_t, f_b=f_b, f_p=f_p, lin_t=lin_t, lin_b=lin_b, lin_p=lin_p,
                 lh_t=lh_t, lh_b=lh_b, lh_p=lh_p, tarjetas=tarjetas, grid=grid, demo=demo,
                 y_tit=y0 + y_tit, y_body=y0 + y_body, y_pie=y0 + y_pie, y_abajo=y0 + y_abajo)
        if tipo == "enlace":
            L["y_link"] = y0 + y_abajo + 30 * fs
            L["y_botones"] = y0 + y_abajo + 100 * fs
            L["y_firma"] = y0 + y_abajo + 160 * fs
        self._cache_lay[clave] = L
        return L

    def _lineas(self, p, lineas, font, y, lh, tl, retardo, color, a, cx, fs):
        """Líneas centradas con fundido y un pequeño ascenso al entrar, una tras otra."""
        p.setFont(font)
        p.setPen(QColor(color))
        fm = QFontMetricsF(font)
        for k, lin in enumerate(lineas):
            r = I.eo(I.tramo(tl, retardo + 0.07 * k, 0.7))
            txt = " ".join(lin)
            p.setOpacity(a * r)
            p.drawText(QPointF(cx - fm.horizontalAdvance(txt) / 2.0, y + k * lh + fm.ascent() + (1 - r) * 14 * fs),
                       txt)

    def _pintar_textos(self, p, i, L, tl, a, dx):
        fs = L["fs"]
        cx = L["cx"] + dx
        pal = self._pal
        cuerpo = I.mezcla(C["texto2"], "#FFFFFF", 0.55)
        self._lineas(p, L["lin_t"], L["f_t"], L["y_tit"], L["lh_t"], tl, 0.1, "#FFFFFF", a, cx, fs)
        if L["lin_b"]:
            self._lineas(p, L["lin_b"], L["f_b"], L["y_body"], L["lh_b"], tl, 0.35, cuerpo, a, cx, fs)
        if L["lin_p"]:
            self._lineas(p, L["lin_p"], L["f_p"], L["y_pie"], L["lh_p"], tl, 0.6,
                         I.mezcla(pal.al, "#FFFFFF", 0.3), a, cx, fs)
        if DIAPOSITIVAS[i]["tipo"] == "enlace":
            self._lineas(p, [FIRMA.split()], L["f_p"], L["y_firma"], L["lh_p"], tl, 0.85, cuerpo, a, cx, fs)

    # ================================================================ visuales por diapositiva

    def _vis_contador(self, p, L, tl, a, dx):
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        r = I.eo(I.tramo(tl, 0.0, 0.8))
        latido = 0.5 + 0.5 * math.sin(self._tg * 1.4)
        pal = self._pal
        llegado = self._cont / float(META)
        p.setOpacity(a * r)
        # rayos de luz que giran despacio detrás del número (crecen a medida que cuenta)
        p.save()
        p.translate(cx, cy)
        p.rotate(self._tg * 7.0)
        largo = (160 + 220 * llegado) * fs
        rg = QRadialGradient(QPointF(0, 0), largo)
        rg.setColorAt(0, I.alfa(I.mezcla(pal.al, "#FFFFFF", 0.4), int(42 * llegado)))
        rg.setColorAt(0.6, I.alfa(pal.al, int(14 * llegado)))
        rg.setColorAt(1, I.alfa(pal.al, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(rg)
        for k in range(14):
            ang = math.radians(k * 360 / 14)
            abre = math.radians(4.5 if k % 2 == 0 else 2.5)
            p.drawPolygon(QPolygonF([QPointF(0, 0),
                                     QPointF(math.cos(ang - abre) * largo, math.sin(ang - abre) * largo),
                                     QPointF(math.cos(ang + abre) * largo, math.sin(ang + abre) * largo)]))
        p.restore()
        I.brillo(p, cx, cy, 280 * fs, pal.ac, int(90 * (0.6 + 0.4 * latido)))
        # ondas expansivas al llegar a 100
        if self._exploto:
            t = self._tg - self._t_explosion
            p.setBrush(Qt.NoBrush)
            for j in range(3):
                u = (t - j * 0.22) / 1.5
                if 0 < u < 1:
                    radio = (70 + 420 * (1 - (1 - u) ** 3)) * fs
                    p.setPen(QPen(I.alfa(I.mezcla(pal.al, "#FFFFFF", 0.5), int(150 * (1 - u))), (3.0 - 2.0 * u) * fs))
                    p.drawEllipse(QPointF(cx, cy), radio, radio * 0.92)
        # el número como trazo: halo del acento, borde fino y relleno con degradado (blanco → acento → oro)
        f = self._f(150 * fs, QFont.Black, True)
        texto = str(int(round(self._cont)))
        ruta = QPainterPath()
        ruta.addText(QPointF(0, 0), f, texto)
        caja = ruta.boundingRect()
        sube = (1 - r) * 20 * fs
        escala = 1.0 + (0.08 * max(0.0, 1 - (self._tg - self._t_explosion) / 0.5) if self._exploto else 0.0)
        p.save()
        p.translate(cx, cy + sube)
        p.scale(escala, escala)
        p.translate(-caja.center().x(), -caja.center().y())
        p.setBrush(Qt.NoBrush)
        for ancho, al in ((34, 26), (18, 46), (8, 80)):
            p.setPen(QPen(I.alfa(pal.al, int(al * (0.7 + 0.3 * latido))), ancho * fs, Qt.SolidLine, Qt.RoundCap,
                          Qt.RoundJoin))
            p.drawPath(ruta)
        g = QLinearGradient(0, caja.top(), 0, caja.bottom())
        g.setColorAt(0.0, QColor("#FFFFFF"))
        g.setColorAt(0.45, I.mezcla("#FFFFFF", pal.al, 0.35))
        g.setColorAt(1.0, I.mezcla(pal.al, pal.oro, 0.55))
        p.setPen(QPen(QColor(255, 255, 255, 200), 1.4 * fs))
        p.setBrush(g)
        p.drawPath(ruta)
        p.restore()

    def _vis_corazon(self, p, L, tl, a, dx):
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.0, 0.7))
        latido = 0.5 + 0.5 * math.sin(self._tg * 2 * math.pi / 1.5)
        s = 58 * fs * (1 + 0.07 * latido) * (0.85 + 0.15 * r)
        p.setOpacity(a * r)
        I.brillo(p, cx, cy, 190 * fs, pal.ac, int(70 * (0.5 + 0.5 * latido)))
        g = QLinearGradient(cx, cy - s, cx, cy + s)
        g.setColorAt(0, I.mezcla(pal.al, "#FFFFFF", 0.25))
        g.setColorAt(1, pal.ac)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(_ruta_corazon(cx, cy, s))

    def _grid(self, col, fs, px):
        """Rejilla 3×2 de «Todo lo que Caudal te ofrece»: por bloque, icono, título y chips por punto."""
        gap_c, pad_x, pad_y = 14 * fs, 10 * fs, 5 * fs
        chip_gap, row_gap, cab = 7 * fs, 12 * fs, 46 * fs
        m = 14 * fs                                    # margen interior del bloque (los chips no tocan el borde)
        bw = (col - 2 * gap_c) / 3.0
        ancho_util = bw - 2 * m
        f_bt = self._f(20 * fs, QFont.Black)
        f_ch = self._f(px, QFont.DemiBold)
        fm_ch = QFontMetricsF(f_ch)
        lh = fm_ch.height() * 1.05
        bloques = []
        for k, (titulo, puntos) in enumerate(BLOQUES):
            chips = []
            x = y = row_h = 0.0
            for pt in puntos:
                lin = _envolver(pt, f_ch, ancho_util - 2 * pad_x)
                ancho = max(fm_ch.horizontalAdvance(" ".join(ln)) for ln in lin)
                cw = min(ancho_util, ancho + 2 * pad_x)
                ch = len(lin) * lh + 2 * pad_y
                if x > 0 and x + cw > ancho_util:
                    x, y, row_h = 0.0, y + row_h + chip_gap, 0.0
                chips.append((m + x, cab + y, cw, ch, lin))
                x += cw + chip_gap
                row_h = max(row_h, ch)
            bloques.append(dict(titulo=titulo, icono=ICONOS_BLOQUE[k], chips=chips, alto=cab + y + row_h + m))
        alturas = [max(b["alto"] for b in bloques[:3]), max(b["alto"] for b in bloques[3:])]
        for idx, b in enumerate(bloques):
            fila = idx // 3
            b["x"] = (idx % 3) * (bw + gap_c)
            b["y"] = 0.0 if fila == 0 else alturas[0] + row_gap
            b["w"] = bw
            b["h"] = alturas[fila]
        total = alturas[0] + row_gap + alturas[1]
        return dict(bloques=bloques, total=total, f_bt=f_bt, f_ch=f_ch, lh=lh, pad_y=pad_y)

    def _vis_rejilla(self, p, L, tl, a, dx):
        fs = L["fs"]
        pal = self._pal
        g = L["grid"]
        x0 = L["cx"] - L["col"] / 2 + dx
        y0 = L["y_abajo"]
        fm_bt = QFontMetricsF(g["f_bt"])
        for k, bl in enumerate(g["bloques"]):
            r = I.eo(I.tramo(tl, 0.15 + 0.12 * k, 0.7))           # entran escalonados, ~120 ms entre bloques
            x = x0 + bl["x"]
            y = y0 + bl["y"] + (1 - r) * 24 * fs
            p.setOpacity(a * r)
            I.cristal(p, QRectF(x, y, bl["w"], bl["h"]), 16 * fs, a_relleno=24, a_borde=56)
            _icono(p, x + 30 * fs, y + 24 * fs, 12 * fs, bl["icono"], pal.al)
            p.setFont(g["f_bt"])
            p.setPen(QColor("#FFFFFF"))
            base = y + 24 * fs + (fm_bt.ascent() - fm_bt.descent()) / 2
            p.drawText(QPointF(x + 54 * fs, base), bl["titulo"])
            p.setFont(g["f_ch"])
            for cx_, cy_, cw, ch, lin in bl["chips"]:
                rect = QRectF(x + cx_, y + cy_, cw, ch)
                I.cristal(p, rect, ch / 2, a_relleno=34, a_borde=70)
                p.setPen(QColor(255, 255, 255, 235))
                for j, ln in enumerate(lin):
                    p.drawText(QRectF(rect.x(), rect.y() + g["pad_y"] + j * g["lh"], cw, g["lh"]),
                               int(Qt.AlignHCenter | Qt.AlignVCenter), " ".join(ln))

    def _vis_tarjetas(self, p, L, tl, a, dx):
        fs = L["fs"]
        col = L["col"]
        gap = 14 * fs
        cw = (col - 2 * gap) / 3
        ch = 136 * fs
        pal = self._pal
        x_ini = L["cx"] - col / 2 + dx
        f_tt, f_td = self._f(15 * fs, QFont.Bold), self._f(13 * fs, QFont.Normal)
        fm_tt, fm_td = QFontMetricsF(f_tt), QFontMetricsF(f_td)
        for k, (lin_tit, lin_desc) in enumerate(L["tarjetas"]):
            fila, c = divmod(k, 3)
            r = I.eo(I.tramo(tl, 0.2 + 0.12 * k, 0.75))
            x = x_ini + c * (cw + gap)
            y = L["y_abajo"] + fila * (ch + gap) + (1 - r) * 30 * fs
            p.setOpacity(a * r)
            rect = QRectF(x, y, cw, ch)
            I.cristal(p, rect, 18 * fs, a_relleno=26, a_borde=60)
            _icono(p, x + 38 * fs, y + 34 * fs, 13 * fs, k, pal.al)
            tx = x + 70 * fs
            yy = y + 20 * fs
            p.setFont(f_tt)
            p.setPen(QColor("#FFFFFF"))
            for lin in lin_tit:
                p.drawText(QPointF(tx, yy + fm_tt.ascent()), " ".join(lin))
                yy += fm_tt.height()
            yy += 2 * fs
            p.setFont(f_td)
            p.setPen(I.mezcla(C["texto2"], "#FFFFFF", 0.55))
            for lin in lin_desc:
                p.drawText(QPointF(tx, yy + fm_td.ascent()), " ".join(lin))
                yy += fm_td.height() * 1.05

    def _pintar_logo(self, p, cx, cy, tam, a, fs):
        """El logo con un halo que respira y motas de luz girando a su alrededor."""
        from .iconos import icono_app
        lado = int(tam)
        pm = self._logo_cache.get(lado)
        if pm is None:
            pm = icono_app(lado)
            self._logo_cache[lado] = pm
        pulso = 0.5 + 0.5 * math.sin(self._tg * 1.6)
        p.setOpacity(a)
        I.brillo(p, cx, cy, tam * 1.3, self._pal.ac, int(60 + 50 * pulso))
        dpr = pm.devicePixelRatio()
        p.drawPixmap(QPointF(cx - pm.width() / 2 / dpr, cy - pm.height() / 2 / dpr), pm)
        p.setPen(Qt.NoPen)
        for k in range(6):
            ang = self._tg * 0.5 + k * math.pi / 3
            x = cx + tam * 0.78 * math.cos(ang)
            y = cy + tam * 0.5 * math.sin(ang)
            p.setBrush(QColor(255, 255, 255, int(120 + 100 * math.sin(self._tg * 2 + k))))
            p.drawEllipse(QPointF(x, y), 2.2 * fs, 2.2 * fs)

    def _vis_demo(self, p, i, L, tl, a, dx):
        """La demostración de la diapositiva: entra subiendo con un leve zoom y luego vive sola."""
        from .demos_presentacion import pintar_demo
        fs = L["fs"]
        ancho, alto = L["demo"]
        r = I.eo(I.tramo(tl, 0.15, 0.8))
        esc = 0.94 + 0.06 * r
        rect = QRectF(L["cx"] + dx - ancho * esc / 2, L["y_abajo"] + (1 - r) * 30 * fs, ancho * esc, alto * esc)
        p.save()
        p.setOpacity(a * r)
        pintar_demo(p, DIAPOSITIVAS[i]["demo"], rect, tl, fs, self._pal, self._cache_demos)
        p.restore()

    def _vis_logo(self, p, L, tl, a, dx):
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        r = I.eo(I.tramo(tl, 0.0, 0.8))
        self._pintar_logo(p, cx, cy, 56 * fs * (0.9 + 0.1 * r), a * r, fs)

    def _vis_enlace(self, p, L, tl, a, dx):
        fs = L["fs"]
        cx = L["cx"] + dx
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.35, 0.7))
        f = self._f(30 * fs, QFont.ExtraBold)
        ancho = QFontMetricsF(f).horizontalAdvance(URL_MOSTRAR)
        rect = QRectF(cx - (ancho + 60 * fs) / 2, L["y_link"] - 30 * fs, ancho + 60 * fs, 60 * fs)
        p.setOpacity(a * r)
        I.brillo(p, cx, L["y_link"], ancho * 0.8, pal.ac, 50)
        I.cristal(p, rect, 30 * fs, a_relleno=34, a_borde=90)
        p.setFont(f)
        p.setPen(pal.al)
        p.drawText(rect, int(Qt.AlignHCenter | Qt.AlignVCenter), URL_MOSTRAR)

    def _pintar_diap(self, p, i, tl, a, off):
        """`off`: -1..1, desplazamiento relativo (negativo: se va hacia la izquierda)."""
        if a <= 0.01:
            return
        w, h = self.width(), self.height()
        L = self._layout(i)
        dx = off * 0.12 * w
        p.save()
        p.setClipRect(QRectF(0, 0, w, h))
        p.setOpacity(a)
        tipo = DIAPOSITIVAS[i]["tipo"]
        if tipo == "contador":
            self._vis_contador(p, L, tl, a, dx)
        elif tipo == "corazon":
            self._vis_corazon(p, L, tl, a, dx)
        elif tipo == "rejilla":
            self._vis_rejilla(p, L, tl, a, dx)
        elif tipo == "tarjetas":
            self._vis_tarjetas(p, L, tl, a, dx)
        elif tipo == "logo":
            self._vis_logo(p, L, tl, a, dx)
        elif tipo == "enlace":
            self._vis_enlace(p, L, tl, a, dx)
        elif tipo == "demo":
            self._vis_demo(p, i, L, tl, a, dx)
        self._pintar_textos(p, i, L, tl, a, dx)
        p.restore()

    # ================================================================ fondo y pintura

    def _pintar_fondo(self, p):
        """Aurora de fondo: degradado del acento de la app, luces difusas que respiran y viñeta."""
        w, h = self.width(), self.height()
        fs = self._escala()
        esc = 3
        bw, bh = max(2, w // esc), max(2, h // esc)
        if self._fondo_img is None or self._fondo_img.width() != bw or self._fondo_img.height() != bh:
            self._fondo_img = QImage(bw, bh, QImage.Format_RGB32)
        img = self._fondo_img
        q = QPainter(img)
        q.setRenderHint(QPainter.Antialiasing, True)
        pal, tg = self._pal, self._tg
        base = QLinearGradient(0, 0, 0, bh)
        base.setColorAt(0, I.mezcla(pal.fondo, pal.ac, 0.16))
        base.setColorAt(0.55, I.mezcla(pal.fondo, pal.ac, 0.05))
        base.setColorAt(1, I.mezcla(pal.fondo, "#000000", 0.6))
        q.fillRect(img.rect(), base)
        q.setCompositionMode(QPainter.CompositionMode_Plus)
        matices = (0, 40, -40, 80, -20)
        for k in range(5):
            fx, fy = 0.07 + 0.03 * k, 0.06 + 0.025 * k
            cx = bw * (0.5 + 0.42 * math.sin(tg * fx * 2.2 + k * 1.9))
            cy = bh * (0.5 + 0.36 * math.cos(tg * fy * 2.4 + k * 2.7))
            resp = 0.5 + 0.5 * math.sin(tg * 0.9 + k * 1.3)          # la luz respira
            rad = max(bw, bh) * (0.38 + 0.10 * resp)
            col = I.tono(pal.ac, matices[k], 0.6, 0.9)
            g = QRadialGradient(QPointF(cx, cy), rad)
            g.setColorAt(0, I.alfa(col, 60 + 40 * resp))
            g.setColorAt(0.55, I.alfa(col, 22 + 14 * resp))
            g.setColorAt(1, I.alfa(col, 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(cx, cy), rad, rad)
        q.setCompositionMode(QPainter.CompositionMode_SourceOver)
        vg = QRadialGradient(QPointF(bw / 2, bh * 0.48), max(bw, bh) * 0.8)
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(0.62, QColor(0, 0, 0, 40))
        vg.setColorAt(1.0, QColor(0, 0, 0, 175))
        q.setBrush(vg)
        q.drawRect(img.rect())
        q.end()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(0, 0, w, h), img)
        # polvo de luz que sube despacio
        for k in range(40):
            sp = 6 + 14 * I.azar(k, 1)
            y = h - ((tg * sp + I.azar(k, 2) * h * 1.2) % (h * 1.1)) + h * 0.05
            x = w * I.azar(k, 3) + 12 * math.sin(tg * 0.5 + k)
            tw = 0.5 + 0.5 * math.sin(tg * (1 + I.azar(k, 4)) + k)
            r = (0.8 + 1.8 * I.azar(k, 5)) * fs
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, int(70 * tw * (0.4 + I.azar(k, 6)))))
            p.drawEllipse(QPointF(x, y), r, r)

    def _pintar_particulas(self, p):
        fs = self._escala()
        g = 520 * fs
        vivas = []
        for q in self._particulas:
            t = self._tg - q["t0"]
            vida = 3.2 if q.get("confeti") else 1.9
            if t > vida:
                continue
            vivas.append(q)
            k = (1 - math.exp(-2.4 * t)) / 2.4
            x = q["x"] + q["vx"] * k
            y = q["y"] + q["vy"] * k + 0.35 * 0.5 * g * t * t
            col = QColor(q["col"])
            col.setAlpha(int(255 * (1 - t / vida)))
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            if q.get("confeti"):
                x += math.sin(t * 5 + q["fase"]) * 14 * fs          # se mece al caer
                p.save()
                p.translate(x, y)
                p.rotate(math.degrees(q["giro"] * t + q["fase"]))
                p.scale(1.0, max(0.15, abs(math.cos(t * 7 + q["fase"]))))   # se voltea
                p.drawRect(QRectF(-q["r"], -q["r"] * 0.5, 2 * q["r"], q["r"]))
                p.restore()
            else:
                p.drawEllipse(QPointF(x, y), q["r"], q["r"])
        self._particulas = vivas

    def _pintar_marco(self, p):
        """Puntos de progreso, mensaje breve de los botones de enlace."""
        w, h = self.width(), self.height()
        fs = self._escala()
        pal = self._pal
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
                col = I.mezcla("#FFFFFF", pal.al, 0.4 * (1 - peso))
                col.setAlpha(int(70 + 185 * peso))
            else:
                col = QColor(255, 255, 255, 120 if k < self._pos_puntos else 62)
            p.setBrush(col)
            p.drawRoundedRect(r, base_w / 2, base_w / 2)
            x += anchos[k] + sep
        edad = self._tg - self._msg_t0
        if self._msg and edad < 2.6:
            p.setOpacity(min(1.0, (2.6 - edad) / 0.6))
            p.setFont(self._f(14 * fs, QFont.DemiBold))
            p.setPen(QColor(255, 255, 255, 230))
            p.drawText(QRectF(w * 0.15, h - 84 * fs, w * 0.7, 26 * fs),
                       int(Qt.AlignHCenter | Qt.AlignVCenter), self._msg)
            p.setOpacity(1.0)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        e = self._p_trans
        self._pintar_fondo(p)
        if self._ant is not None and e < 1.0:
            self._pintar_diap(p, self._ant, self._tl_ant, I.clamp(1 - e * 1.7), -self._dir * e)
            self._pintar_diap(p, self.indice, self._tl, I.clamp((e - 0.15) / 0.85), self._dir * (1 - e))
        else:
            self._pintar_diap(p, self.indice, self._tl, 1.0, 0.0)
        p.setOpacity(1.0)
        self._pintar_particulas(p)
        self._pintar_marco(p)
        p.end()


def pedir_total(timeout=8):
    """Cuántas personas usan Caudal (RPC total_usuarios de Supabase). Petición vacía, sin datos personales."""
    cabeceras = {"apikey": CLAVE_PUBLICA, "Authorization": "Bearer " + CLAVE_PUBLICA,
                 "Content-Type": "application/json"}
    peticion = urllib.request.Request(SUPABASE_TOTAL, data=b"{}", method="POST", headers=cabeceras)
    with urllib.request.urlopen(peticion, timeout=timeout) as resp:
        valor = json.loads(resp.read().decode("utf-8"))
    if isinstance(valor, list) and valor:
        valor = valor[0]
    return int(valor)


def _abrir(ventana, despues=None):
    """Abre la presentación en el hilo de la interfaz. Si hay otra cosa a pantalla completa o la app
    se está cerrando, espera un poco y lo vuelve a intentar (sin pedir la cifra otra vez). `despues` se llama
    al cerrarla (o si no se pudo abrir)."""
    try:
        ocupada = bool(getattr(ventana, "en_completa", False) or getattr(ventana, "_saliendo", False))
        if ocupada:
            QTimer.singleShot(20000, lambda: _abrir(ventana, despues))
            return None
        dlg = Presentacion100(ventana, getattr(ventana, "ctx", None))
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        if despues is not None:
            dlg.finished.connect(lambda _r: despues())
        dlg.open()
        return dlg
    except RuntimeError:          # la ventana ya no existe
        return None


def revisar_hito_100(ventana, despues=None):
    """Al arrancar: si aún no se vio y el total llega a 100, marca la presentación como vista y la abre.
    Sin red o con error no hace nada. `despues` (opcional) se llama una sola vez cuando ya no hay nada que
    enseñar: al cerrar la presentación, o enseguida si no tocaba (así lo demás espera su turno)."""
    hecho = [False]

    def seguir():
        if despues is not None and not hecho[0]:
            hecho[0] = True
            try:
                despues()
            except RuntimeError:
                pass

    ajustes = getattr(ventana, "ajustes", None)
    if ajustes is None or ajustes.get(CLAVE_VISTA):
        seguir()
        return
    from descargador.hilos import en_segundo_plano

    def listo(total):
        if total is None or int(total) < META or ajustes.get(CLAVE_VISTA):
            seguir()
            return
        ajustes[CLAVE_VISTA] = True
        ajustes.guardar()
        if _abrir(ventana, seguir) is None and not (getattr(ventana, "en_completa", False)
                                                    or getattr(ventana, "_saliendo", False)):
            seguir()

    en_segundo_plano(pedir_total, ok=listo, error=lambda _e: seguir(), dueno=ventana)
