# -*- coding: utf-8 -*-
"""Presentación de la versión 2.4.2: «Mascotitas y fondos con personaje».

Cinco diapositivas a pantalla completa con el mismo fondo de aurora y la misma mecánica que la
presentación de la edición grande (flechas, Enter, rueda, clic, puntos de progreso y «Saltar»
siempre a la vista). Las mascotas se dibujan con `descargador/mascotas.py`, igual que en la barra
del reproductor, y siempre nítidas: se pintan en una capa a su tamaño real y se agrandan por
enteros, sin suavizado. Los fondos con personaje salen de `estilos.TEMAS` y de
`descargador/fondos/<clave>.png`.

Sale una sola vez a quien abre Caudal con la 2.4.2 o una posterior (se anota al abrirse). Si en
ese arranque ya sale la presentación de la edición grande, esta espera al siguiente. La música no
se toca.
"""

import math

from PySide6.QtCore import (QElapsedTimer, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRectF, QTimer,
                            Qt, QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QApplication, QDialog

from .. import mascotas as M
from .. import version as _version
from . import ilustraciones_grandes as I
from .componentes import fuente
from .estilos import C, TEMAS, ruta_patron
from .presentacion_grande import _Boton

VERSION_PRESENTACION = "2.4.2"
CLAVE_AJUSTE = "presentacion_mascotas_vista"

DIAPOSITIVAS = [
    dict(clave="portada", etiqueta="LO NUEVO DE CAUDAL", titulo="Mascotitas y fondos con personaje",
         texto="Un amiguito que camina sobre tu música y fondos nuevos para vestir Caudal a tu gusto.",
         centrada=True, tono=0),
    dict(clave="mascotas", etiqueta="MASCOTITAS", titulo="Un amiguito en tu barra",
         texto="Mientras suena la canción, un personaje en pixel art camina sobre la barra de progreso y va "
               "dejando su estela: corazones, estrellas, llamitas…",
         nota="Exclusivo de Donador de Caudal y Fundador de Caudal", tono=24),
    dict(clave="fondos", etiqueta="PARA TODOS", titulo="Fondos con personaje",
         texto="En Ajustes › Aspecto, sección «Con personajes». Cada fondo tiñe Caudal con sus colores y "
               "sienta a su personaje en la esquina del reproductor.",
         nota="Si tienes tu propia imagen de fondo, se sigue viendo", tono=-30),
    dict(clave="juntos", etiqueta="VAN JUNTOS", titulo="Tu fondo y tu personaje",
         texto="Al elegir un fondo con personaje, su mascotita también se pone a caminar por la barra. "
               "Uno te acompaña sentado y el otro camina contigo.",
         nota="La mascotita sale si tu cuenta tiene mascotas", tono=40),
    dict(clave="final", etiqueta="GRACIAS", titulo="Gracias por ser parte de Caudal",
         texto="Elige tu personaje favorito y disfruta lo nuevo.", centrada=True, tono=8),
]

# los que desfilan en la portada y en el cierre (de izquierda a derecha)
DESFILE = ("kuromi", "bulbasaur", "nyan", "pikachu", "cinnamoroll", "hellokitty", "squirtle", "totoro",
           "charmander", "kirby", "mymelody", "dragon")
DESFILE_FINAL = ("capibara", "purin", "olaf", "gato_negro", "pochacco", "conejo_mago", "doraemon", "snoopy",
                 "ajolote", "kirby")
# el orden de la rejilla de la diapositiva de mascotitas: primero las más conocidas
PRIMERAS = ("pikachu", "hellokitty", "nyan", "kirby", "charmander", "totoro", "cinnamoroll", "dragon",
            "ajolote", "kuromi", "squirtle", "snoopy")
# el orden en que rotan los fondos con personaje
ORDEN_TEMAS = ("hellokitty", "pikachu", "kuromi", "totoro", "nyan", "cinnamoroll", "charmander", "mymelody",
               "squirtle", "kirby", "doraemon", "snoopy", "bulbasaur", "purin", "olaf", "capibara", "pochacco",
               "gato_negro")

PASO_CUADRO = 0.17        # s por cuadro de animación, como en la barra del reproductor
VELOCIDAD = 30.0          # unidades de la barra por segundo al caminar
PERIODO_FONDO = 2.2       # s que se ve cada fondo en la diapositiva de fondos
PERIODO_JUNTOS = 3.6      # s por fondo en la diapositiva «van juntos»


# ================================================================ cuándo sale

def debe_mostrarse(ajustes, version_actual=None):
    """True si la versión instalada ya trae esta presentación y aún no se vio."""
    actual = version_actual or _version.VERSION
    if _version.hay_novedad(actual, VERSION_PRESENTACION):          # la instalada es anterior a la 2.4.2
        return False
    vista = str(ajustes[CLAVE_AJUSTE] or "")
    return not vista or _version.hay_novedad(vista, VERSION_PRESENTACION)


def marcar_vista(ajustes):
    ajustes[CLAVE_AJUSTE] = VERSION_PRESENTACION
    ajustes.guardar()


def abrir(ventana):
    """Abre la presentación sobre la ventana (también a mano, p. ej. desde Ajustes). No bloquea."""
    d = PresentacionMascotas(ventana, ctx=getattr(ventana, "ctx", None))
    d.setAttribute(Qt.WA_DeleteOnClose, True)
    navegar = getattr(ventana, "navegar", None)
    if callable(navegar):
        d.ir_a_aspecto.connect(lambda: QTimer.singleShot(0, lambda: navegar({"pagina": "ajustes"})))
    d.open()
    return d


def mostrar_si_toca(ventana, otra=None):
    """Al abrir la app: la enseña si toca. `otra` es el aviso que ya salió en este arranque (la
    presentación de la edición grande): si lo hay, esta espera al siguiente arranque para que no se
    encimen. Se anota al abrirse, no al cerrarse. Devuelve el diálogo o None."""
    if otra is not None:
        return None
    ajustes = ventana.ajustes
    if not debe_mostrarse(ajustes):
        return None
    marcar_vista(ajustes)
    return abrir(ventana)


# ================================================================ mascotas

def disponibles(claves=None):
    """Las mascotas que se pueden enseñar: con dibujo y nunca las exclusivas de una cuenta."""
    if claves is None:
        lista = M.catalogo()
    else:
        lista = [M.por_clave(c) for c in claves]
    return [m for m in lista if m and not M.es_exclusiva(m) and M.cuadros(m["clave"])]


def orden_rejilla():
    """Todas las de la rejilla: primero las de PRIMERAS y luego el resto del catálogo."""
    primeras = disponibles(PRIMERAS)
    vistas = {m["clave"] for m in primeras}
    return primeras + [m for m in disponibles() if m["clave"] not in vistas]


HOLGURA = 40              # unidades a cada lado de la capa: así una mascota puede entrar y salir


def capa_mascotas(ancho_u, alto_u, piezas, holgura=HOLGURA):
    """Una capa transparente de `ancho_u` × `alto_u` unidades de la barra (2 píxeles de la hoja por
    unidad, así las hojas de densidad 2 se ven píxel a píxel). `piezas`: [(datos, x, y, margen, t)],
    con los pies sobre `y` y la estela cortada en `margen`. Se dibuja con `mascotas.pintar`, como la
    barra del reproductor. La capa lleva `holgura` unidades de más a cada lado (la x 0 cae en
    `holgura`): `dibujar_capa` lo descuenta."""
    total = ancho_u + 2 * holgura
    img = QImage(max(2, int(math.ceil(total * 2))), max(2, int(math.ceil(alto_u * 2))),
                 QImage.Format_ARGB32_Premultiplied)
    img.setDevicePixelRatio(2.0)
    img.fill(0)
    q = QPainter(img)
    for datos, x, y, margen, t in piezas:
        n = int(max(0.0, t) / PASO_CUADRO)
        M.pintar(q, datos, round(x + holgura), round(y), max(0.0, margen + holgura), total,
                 n % M.num_cuadros(datos), n * 0.9, 1)
        q.setOpacity(1.0)
    q.end()
    img.setText("holgura", str(holgura))
    return img


def dibujar_capa(p, img, x, y, k):
    """La capa en (x, y) agrandada `k` veces por enteros, sin suavizado (x es donde cae la x 0)."""
    holgura = float(img.text("holgura") or 0)
    x -= holgura * 2 * k
    p.save()
    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    p.drawImage(QRectF(round(x), round(y), img.width() * k, img.height() * k), img,
                QRectF(0, 0, img.width(), img.height()))
    p.restore()


def desvanecer_bordes(img, izq, der):
    """Funde a transparente los extremos de la capa (`izq`/`der` en fracción del ancho)."""
    q = QPainter(img)
    q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    w = img.width() / img.devicePixelRatio()
    g = QLinearGradient(0, 0, w, 0)
    g.setColorAt(0.0, QColor(0, 0, 0, 0))
    g.setColorAt(izq, QColor(0, 0, 0, 255))
    g.setColorAt(1.0 - der, QColor(0, 0, 0, 255))
    g.setColorAt(1.0, QColor(0, 0, 0, 0))
    q.fillRect(QRectF(0, 0, w, img.height() / img.devicePixelRatio()), g)
    q.end()


def _pixmap_personaje(clave):
    from .fondo_capa import pixmap_patron
    return pixmap_patron(ruta_patron(clave))


def _tema(clave):
    """dict con los colores de un fondo con personaje."""
    v = TEMAS[clave]
    return dict(nombre=v[0], acento=QColor(v[1]), fondo=QColor(v[2]), panel=QColor(v[3]), sup=QColor(v[4]),
                sup2=QColor(v[5]), sup3=QColor(v[6]), hover=QColor(v[7]), borde=QColor(v[8]))


def temas_en_orden():
    return [k for k in ORDEN_TEMAS if k in TEMAS] + [k for k in TEMAS if k not in ORDEN_TEMAS]


# ================================================================ el diálogo

class PresentacionMascotas(QDialog):
    ir_a_aspecto = Signal()

    DURACION = 900               # ms de la transición entre diapositivas

    def __init__(self, padre=None, ctx=None):
        super().__init__(padre)
        self.ctx = ctx
        self.n = len(DIAPOSITIVAS)
        self.indice = 0
        self.destino = ""
        self._ant = None
        self._dir = 1
        self._p_trans = 1.0
        self._tg = 0.0
        self._tl = 0.0
        self._tl_ant = 0.0
        self._pos_puntos = 0.0
        self._revelado = False
        self._rueda = 0
        self._ultima_rueda = QElapsedTimer()
        self._ultima_rueda.start()
        self._cache_fuentes = {}
        self._cache_rutas = {}
        self._puntos = []
        self._fondo_img = None
        self._logo_cache = {}
        self._base = None
        self._anim_trans = None
        self._anim_puntos = None
        self._anim_op = None
        self._pal = I.Paleta(C)
        self._rejilla = orden_rejilla()
        self._desfile = disponibles(DESFILE)
        self._desfile_final = disponibles(DESFILE_FINAL)
        self._temas = temas_en_orden()

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle("Novedades de Caudal")
        self.setAccessibleName("Novedades de Caudal: mascotitas y fondos con personaje")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(900, 600)

        def boton(texto, nombre, principal=False):
            b = _Boton(texto, self, principal)
            b.setAccessibleName(nombre)
            b.setCursor(Qt.PointingHandCursor)
            b.setAutoDefault(False)
            b.setFocusPolicy(Qt.TabFocus)
            return b

        self.bt_saltar = boton("Saltar", "Saltar la presentación")
        self.bt_saltar.clicked.connect(self.reject)
        self.bt_ant = boton("‹  Atrás", "Diapositiva anterior")
        self.bt_ant.clicked.connect(self.anterior)
        self.bt_sig = boton("Siguiente  ›", "Diapositiva siguiente", True)
        self.bt_sig.clicked.connect(self._principal)
        self.bt_aspecto = boton("Elegir mi fondo", "Abrir Ajustes, en Aspecto")
        self.bt_aspecto.clicked.connect(self._ir_aspecto)

        self._reloj = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

        self._ajustar_tamano()
        self._actualizar_textos()
        self._colocar_botones()

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
        self.setGeometry(esq.x(), esq.y(), max(900, ancho), max(600, alto))

    def eventFilter(self, obj, e):
        if obj is self._base and e.type() in (QEvent.Resize, QEvent.Move):
            self._ajustar_tamano()
        return super().eventFilter(obj, e)

    def _escala(self):
        return max(0.82, min(1.5, min(self.width() / 1280.0, self.height() / 800.0)))

    def _k(self):
        """Cuántos píxeles de pantalla ocupa cada píxel de la hoja de una mascota (siempre entero)."""
        return 2 if self._escala() >= 1.6 else 1

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fondo_img = None
        self._cache_rutas.pop("lay", None)
        self._estilos()
        self._colocar_botones()

    # ================================================================ botones

    def _estilos(self):
        fs = self._escala()
        ultimo = self.indice == self.n - 1
        self.bt_saltar.configurar(fs)
        self.bt_ant.configurar(fs)
        self.bt_sig.configurar(fs, 1.14 if ultimo else 1.0)
        self.bt_aspecto.configurar(fs, 1.14)

    def _actualizar_textos(self):
        ultimo = self.indice == self.n - 1
        self.bt_sig.setText("Empezar" if ultimo else "Siguiente  ›")
        self.bt_sig.setAccessibleName("Empezar" if ultimo else "Diapositiva siguiente")
        self.bt_ant.setVisible(self.indice > 0)
        self.bt_aspecto.setVisible(ultimo)
        d = DIAPOSITIVAS[self.indice]
        self.setAccessibleDescription(f"Diapositiva {self.indice + 1} de {self.n}. {d['titulo']}. {d['texto']}")
        self._estilos()

    def _y_puntos(self):
        return self.height() - round(46 * self._escala())

    def _colocar_botones(self):
        fs = self._escala()
        w = self.width()
        self.bt_saltar.move(round(w - 48 * fs - self.bt_saltar.width()), round(30 * fs))
        self.bt_ant.move(round(56 * fs), round(self._y_puntos() - self.bt_ant.height() / 2))
        if self.indice == self.n - 1:
            L = self._layout(self.indice)
            sep = 14 * fs
            total = self.bt_aspecto.width() + sep + self.bt_sig.width()
            x = (w - total) / 2
            y = L["y_botones"]
            self.bt_aspecto.move(round(x), round(y))
            self.bt_sig.move(round(x + self.bt_aspecto.width() + sep), round(y))
        else:
            self.bt_sig.move(round(w - 56 * fs - self.bt_sig.width()),
                             round(self._y_puntos() - self.bt_sig.height() / 2))
        for b in (self.bt_saltar, self.bt_sig, self.bt_aspecto):
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
        self._actualizar_textos()
        self._colocar_botones()
        for a in (self._anim_trans, self._anim_puntos):
            if a is not None:
                a.stop()
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
        else:
            self.accept()

    def _ir_aspecto(self):
        self.destino = "aspecto"
        self.ir_a_aspecto.emit()
        self.accept()

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
        self._colocar_botones()
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
        """Adelanta los relojes y termina las transiciones (pruebas y capturas)."""
        self._tg += segundos
        self._tl += segundos
        self._tl_ant += segundos
        for a in (self._anim_trans, self._anim_puntos, self._anim_op):
            if a is not None and a.state() == a.State.Running:
                a.setCurrentTime(a.duration())
                a.stop()
        self._p_trans = 1.0
        self._ant = None
        self._pos_puntos = float(self.indice)
        self.setWindowOpacity(1.0)
        self._colocar_botones()
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

    def _alto_desfile(self):
        return 62 * 2 * self._k() + 18 * self._escala()

    def _layout(self, i):
        w, h = self.width(), self.height()
        cache = self._cache_rutas.setdefault("lay", {})
        if (i, w, h) in cache:
            return cache[(i, w, h)]
        d = DIAPOSITIVAS[i]
        fs = self._escala()
        centrada = d.get("centrada", False)
        ancho_split = w / float(h) >= 1.15
        margen = max(52 * fs, w * 0.065)
        top_ui, bot_ui = 92 * fs, 96 * fs
        if centrada:
            col = min(w * 0.84, 1040 * max(fs, 1.0))
            tpx = (60 if i == 0 else 52) * fs
            alin = Qt.AlignHCenter
        elif ancho_split:
            col = min(max(w * 0.36, 320), 540 * max(fs, 1.0))
            tpx = 44 * fs
            alin = Qt.AlignLeft
        else:
            col = min(w - 2 * margen, 640 * max(fs, 1.0))
            tpx = 38 * fs
            alin = Qt.AlignHCenter
        f_k = self._f(13 * fs, QFont.DemiBold, False, 2.4 * fs)
        f_t = self._f(tpx, QFont.Black, True)
        f_b = self._f((19.5 if centrada else 18) * fs, QFont.Normal)
        f_n = self._f(14 * fs, QFont.DemiBold)
        lin_t = self._equilibrar(d["titulo"], f_t, col)
        if len(lin_t) > 2:
            f_t = self._f(tpx * 0.84, QFont.Black, True)
            lin_t = self._equilibrar(d["titulo"], f_t, col)
        lin_b = self._envolver(d["texto"], f_b, col * (0.84 if centrada else 1.0))
        fm_t, fm_b, fm_k, fm_n = QFontMetricsF(f_t), QFontMetricsF(f_b), QFontMetricsF(f_k), QFontMetricsF(f_n)
        lh_t, lh_b = fm_t.height() * 0.98, fm_b.height() * 1.34
        gap1, gap2 = 14 * fs, 18 * fs
        logo = (92 if i == 0 else 78) * fs if centrada else 0
        gap0 = 22 * fs if logo else 0
        nota_h = (fm_n.height() + 16 * fs) if d.get("nota") else 0
        gap3 = 22 * fs if nota_h else 0
        alto = logo + gap0 + fm_k.height() + gap1 + lh_t * len(lin_t) + gap2 + lh_b * len(lin_b) + gap3 + nota_h
        y_botones = 0.0
        desfile = None
        if centrada:
            x0 = (w - col) / 2
            ilus = QRectF(0, 0, w, h)
            alto_d = self._alto_desfile()
            if i == self.n - 1:
                alto_bt = self.bt_sig.sizeHint().height() * 1.0
                bloque = alto + 30 * fs + alto_bt + 26 * fs + alto_d
            else:
                bloque = alto + 34 * fs + alto_d
            y0 = top_ui + max(0.0, (h - top_ui - bot_ui - bloque) / 2)
            y_fin = y0 + alto
            if i == self.n - 1:
                y_botones = y_fin + 30 * fs
                y_desf = y_botones + alto_bt + 26 * fs
            else:
                y_desf = y_fin + 34 * fs
            desfile = QRectF(margen * 0.6, y_desf, w - margen * 1.2, alto_d)
        elif ancho_split:
            x0 = margen
            ix0 = margen + col + w * 0.035
            ilus = QRectF(ix0, top_ui, max(220, w - margen * 0.7 - ix0), h - top_ui - bot_ui)
            y0 = (top_ui + (h - bot_ui)) / 2 - alto / 2
        else:
            ilus_h = (h - top_ui - bot_ui) * 0.56
            ilus = QRectF(margen, top_ui, w - 2 * margen, ilus_h)
            x0 = (w - col) / 2
            y0 = top_ui + ilus_h + 14 * fs
        L = dict(fs=fs, col=col, x0=x0, y0=y0, alin=alin, f_k=f_k, f_t=f_t, f_b=f_b, f_n=f_n, lin_t=lin_t,
                 lin_b=lin_b, lh_t=lh_t, lh_b=lh_b, gap0=gap0, gap1=gap1, gap2=gap2, gap3=gap3, nota_h=nota_h,
                 logo=logo, ilus=ilus, alto=alto, y_fin=y0 + alto, centrada=centrada, h_k=fm_k.height(),
                 y_botones=y_botones, desfile=desfile)
        cache[(i, w, h)] = L
        return L

    def _ruta_palabra(self, palabra, f):
        clave = (palabra, f.pixelSize(), f.weight(), f.family())
        r = self._cache_rutas.get(clave)
        if r is None:
            r = QPainterPath()
            r.addText(0, QFontMetricsF(f).ascent(), f, palabra)
            self._cache_rutas[clave] = r
        return r

    def _pintar_texto(self, p, i, tl, alfa_, dx):
        L = self._layout(i)
        pal = self._pal
        fs = L["fs"]
        x0, y = L["x0"] + dx, L["y0"]
        col = L["col"]
        d = DIAPOSITIVAS[i]
        centro = L["alin"] == Qt.AlignHCenter

        def alinear(ancho_linea):
            return x0 + (col - ancho_linea) / 2 if centro else x0

        if L["logo"]:
            r = I.eo(I.tramo(tl, 0.0, 1.0))
            self._pintar_logo(p, x0 + col / 2, y + L["logo"] / 2 + (1 - r) * 18, L["logo"], alfa_ * r)
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
        xk = alinear(wk)
        p.drawText(QPointF(xk, y + fm.ascent() + (1 - r) * 12), et)
        if not centro:
            p.setPen(QPen(I.alfa(pal.al, 150), 2 * fs, Qt.SolidLine, Qt.RoundCap))
            ls = I.eo(I.tramo(tl, 0.3, 0.8))
            yl = y + L["h_k"] * 0.55
            p.drawLine(QPointF(xk + wk + 14 * fs, yl), QPointF(xk + wk + 14 * fs + 46 * fs * ls, yl))
        y += L["h_k"] + L["gap1"]

        # título, palabra por palabra, con una banda de luz que lo cruza
        f_t = L["f_t"]
        fm_t = QFontMetricsF(f_t)
        espacio = fm_t.horizontalAdvance(" ")
        n_pal = 0
        fuerte = i in (0, self.n - 1)
        for lin in L["lin_t"]:
            ancho_lin = sum(fm_t.horizontalAdvance(w_) for w_ in lin) + espacio * (len(lin) - 1)
            xl = alinear(ancho_lin)
            xx = xl
            for w_ in lin:
                r = I.eo(I.tramo(tl, 0.38 + 0.085 * n_pal, 0.85))
                n_pal += 1
                ww = fm_t.horizontalAdvance(w_)
                if r > 0:
                    ruta = self._ruta_palabra(w_, f_t)
                    p.save()
                    p.setOpacity(alfa_ * r)
                    p.translate(xx, y + (1 - r) * 30 * fs)
                    base = QLinearGradient(0, 0, 0, fm_t.height())
                    base.setColorAt(0, QColor("#FFFFFF"))
                    base.setColorAt(1, I.mezcla("#FFFFFF", pal.al, 0.30 if fuerte else 0.18))
                    p.setPen(Qt.NoPen)
                    p.setBrush(base)
                    p.drawPath(ruta)
                    ft_ = ((self._tg - 0.9) % 4.8) / 2.2 if fuerte else ((self._tg + i * 0.7) % 7.0) / 2.6
                    if ft_ < 1.0:
                        ancho_blq = max(col, ancho_lin)
                        cx = (xl - xx) + ancho_blq * (-0.15 + 1.3 * ft_)
                        g = QLinearGradient(cx - 0.12 * ancho_blq, 0, cx + 0.12 * ancho_blq, fm_t.height() * 0.3)
                        g.setColorAt(0, I.alfa(pal.al, 0))
                        g.setColorAt(0.5, I.alfa(I.mezcla(pal.al, "#FFFFFF", 0.65), 255 if fuerte else 150))
                        g.setColorAt(1, I.alfa(pal.al, 0))
                        p.setBrush(g)
                        p.drawPath(ruta)
                    p.restore()
                xx += ww + espacio
            y += L["lh_t"]
        y += L["gap2"] - (L["lh_t"] - fm_t.height() * 0.98)

        # cuerpo
        f_b = L["f_b"]
        fm_b = QFontMetricsF(f_b)
        p.setFont(f_b)
        cuerpo = I.mezcla(C["texto2"], "#FFFFFF", 0.58)
        for k, lin in enumerate(L["lin_b"]):
            r = I.eo(I.tramo(tl, 0.9 + 0.11 * k, 0.8))
            p.setOpacity(alfa_ * r)
            p.setPen(cuerpo)
            txt = " ".join(lin)
            p.drawText(QPointF(alinear(fm_b.horizontalAdvance(txt)), y + fm_b.ascent() + (1 - r) * 16), txt)
            y += L["lh_b"]

        # nota en una píldora
        if L["nota_h"]:
            y += L["gap3"]
            r = I.eo(I.tramo(tl, 1.25 + 0.11 * len(L["lin_b"]), 0.8))
            p.setOpacity(alfa_ * r)
            f_n = L["f_n"]
            fm_n = QFontMetricsF(f_n)
            txt = d["nota"]
            lado = fm_n.height() * 0.62
            ancho = fm_n.horizontalAdvance(txt) + lado + 40 * fs
            ancho = min(ancho, col)
            rect = QRectF(alinear(ancho), y + (1 - r) * 10, ancho, L["nota_h"])
            p.setPen(QPen(I.alfa(pal.al, 120), 1.2))
            p.setBrush(I.alfa(pal.ac, 40))
            p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
            # una estrellita delante
            I.estrella(p, rect.left() + 16 * fs + lado / 2, rect.center().y(), lado * 0.62, lado * 0.27,
                       QColor(pal.al))
            p.setFont(f_n)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(rect.left() + 22 * fs + lado, rect.top(), rect.width() - 30 * fs - lado,
                              rect.height()), int(Qt.AlignVCenter | Qt.AlignLeft), txt)
        p.setOpacity(1.0)

    # ================================================================ logo

    def _pintar_logo(self, p, cx, cy, tam, a):
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
        g = QRadialGradient(QPointF(cx, cy), tam)
        g.setColorAt(0, I.alfa(pal.al, 80 + 40 * pulso))
        g.setColorAt(1, I.alfa(pal.al, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QPointF(cx, cy), tam, tam)
        dpr = pm.devicePixelRatio()
        p.drawPixmap(QPointF(cx - pm.width() / 2 / dpr, cy - pm.height() / 2 / dpr), pm)
        p.restore()

    # ================================================================ fondo de aurora

    def _pintar_fondo(self, p, tono_grados):
        w, h = self.width(), self.height()
        bw, bh = max(2, w // 3), max(2, h // 3)
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
            g.setColorAt(0, I.alfa(col, 74))
            g.setColorAt(0.55, I.alfa(col, 24))
            g.setColorAt(1, I.alfa(col, 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(cx, cy), rad, rad)
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
            g.setColorAt(0.75, I.alfa(col, 36))
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
        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(0, 0, w, h), img)
        p.restore()
        # polvo de luz
        fs = self._escala()
        p.setPen(Qt.NoPen)
        for k in range(42):
            sp = 6 + 14 * I.azar(k, 1)
            y = h - ((tg * sp + I.azar(k, 2) * h * 1.2) % (h * 1.1)) + h * 0.05
            x = w * I.azar(k, 3) + 12 * math.sin(tg * 0.5 + k)
            tw = 0.5 + 0.5 * math.sin(tg * (1 + I.azar(k, 4)) + k)
            r = (0.8 + 1.8 * I.azar(k, 5)) * fs
            p.setBrush(QColor(255, 255, 255, int(70 * tw * (0.4 + I.azar(k, 6)))))
            p.drawEllipse(QPointF(x, y), r, r)

    # ================================================================ piezas de dibujo

    def _pista(self, p, x0, x1, y, fs, relleno_hasta=None, color=None, grosor=None):
        """La barra de progreso como en el reproductor: pista tenue y relleno claro."""
        g = grosor or max(3.0, 4 * fs)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 46))
        p.drawRoundedRect(QRectF(x0, y - g / 2, x1 - x0, g), g / 2, g / 2)
        if relleno_hasta is not None and relleno_hasta > x0:
            p.setBrush(QColor(color) if color is not None else QColor(C["texto"]))
            p.drawRoundedRect(QRectF(x0, y - g / 2, min(x1, relleno_hasta) - x0, g), g / 2, g / 2)

    def _desfile_en(self, p, rect, lista, t, alfa_):
        """Varias mascotas caminando juntas sobre una barra, entrando por la izquierda y saliendo por la
        derecha, cada una con su estela."""
        if not lista or rect is None:
            return
        fs = self._escala()
        k = self._k()
        U = 2 * k                                   # px de pantalla por unidad de la barra
        y_linea = rect.bottom() - 10 * fs
        x0, x1 = rect.left(), rect.right()
        p.save()
        p.setOpacity(alfa_)
        # la barra con una luz que sigue a cada mascota
        g = max(3.0, 4 * fs)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 34))
        p.drawRoundedRect(QRectF(x0, y_linea - g / 2, x1 - x0, g), g / 2, g / 2)
        ancho_u = (x1 - x0) / U
        alto_u = max(m["alto"] for m in lista) + 12
        hueco = 118.0
        largo = max(ancho_u + 80, hueco * len(lista))
        desp = (t * VELOCIDAD) % largo
        piezas = []
        for j, m in enumerate(lista):
            x = (j * hueco + desp) % largo - 40          # entra por la izquierda, fuera de la vista
            piezas.append((x, m))
        piezas.sort(key=lambda e: e[0])
        capa = []
        anterior = -1e9
        for x, m in piezas:
            if x < -m["ancho"] or x > ancho_u + m["ancho"]:
                anterior = x + m["ancho"] / 2
                continue
            margen = max(0.0, anterior + 6)
            capa.append((m, x, alto_u - 1, margen, t + x * 0.013))
            anterior = x + m["ancho"] / 2
            # luz bajo la mascota, en la barra
            xs = x0 + x * U
            luz = QLinearGradient(xs - 150 * fs, 0, xs, 0)
            luz.setColorAt(0, I.alfa(self._pal.al, 0))
            luz.setColorAt(1, I.alfa(I.mezcla(self._pal.al, "#FFFFFF", 0.5), 230))
            p.setBrush(luz)
            p.drawRoundedRect(QRectF(max(x0, xs - 150 * fs), y_linea - g / 2, min(xs, x1) - max(x0, xs - 150 * fs), g),
                              g / 2, g / 2)
        holgura = 80
        img = capa_mascotas(ancho_u, alto_u, capa, holgura)
        total = ancho_u + 2 * holgura
        borde = (holgura + min(60.0, ancho_u * 0.08)) / total
        desvanecer_bordes(img, borde, borde)
        dibujar_capa(p, img, x0, y_linea - (alto_u - 1) * U, k)
        p.restore()

    # ---------------------------------------------------------------- rejilla de mascotitas

    def _ilus_mascotas(self, p, L, tl, alfa_, dx):
        r = QRectF(L["ilus"]).translated(dx, 0)
        fs = L["fs"]
        k = self._k()
        U = 2 * k
        alto_masc = 52 * U
        sep = 14 * fs
        filas = 3 if (r.height() - 2 * sep) / 3 >= alto_masc + 54 * fs else 2
        cols = 3 if r.width() >= 3 * (alto_masc * 1.9) else 2
        ch = min((r.height() - (filas - 1) * sep) / filas, alto_masc + 96 * fs)
        cw = (r.width() - (cols - 1) * sep) / cols
        alto_total = filas * ch + (filas - 1) * sep
        y_ini = r.top() + (r.height() - alto_total) / 2
        por_pagina = filas * cols
        lista = self._rejilla
        if not lista:
            return
        f_nom = self._f(14 * fs, QFont.Bold)
        f_ori = self._f(11.5 * fs, QFont.Normal)
        periodo = 6.5
        for j in range(por_pagina):
            fila, columna = divmod(j, cols)
            cx = r.left() + columna * (cw + sep)
            cy = y_ini + fila * (ch + sep)
            entrada = I.eo(I.tramo(tl, 0.35 + 0.07 * j, 0.7))
            if entrada <= 0:
                continue
            # cada tarjeta cambia de mascota en su turno (un poco escalonado)
            tj = max(0.0, tl - 0.07 * j)
            pagina = int(tj / periodo)
            fase = tj - pagina * periodo
            m = lista[(pagina * por_pagina + j) % len(lista)]
            cambio = 1.0
            if pagina > 0 and fase < 0.45:
                cambio = I.eo(fase / 0.45)
            elif fase > periodo - 0.35:
                cambio = 1 - I.clamp((fase - (periodo - 0.35)) / 0.35)
            a = alfa_ * entrada
            tarjeta = QRectF(cx, cy + (1 - entrada) * 26 * fs, cw, ch)
            p.save()
            p.setOpacity(a)
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
            gr = QLinearGradient(tarjeta.topLeft(), tarjeta.bottomRight())
            gr.setColorAt(0, QColor(255, 255, 255, 26))
            gr.setColorAt(1, QColor(255, 255, 255, 10))
            p.setBrush(gr)
            p.drawRoundedRect(tarjeta, 16 * fs, 16 * fs)
            pad = 14 * fs
            p.setOpacity(a * cambio)
            p.setFont(f_nom)
            p.setPen(QColor("#FFFFFF"))
            fm = QFontMetricsF(f_nom)
            p.drawText(QPointF(tarjeta.left() + pad, tarjeta.top() + pad + fm.ascent()),
                       fm.elidedText(m["nombre"], Qt.ElideRight, tarjeta.width() - 2 * pad))
            if m.get("origen") and m["origen"] != m["nombre"]:
                p.setFont(f_ori)
                p.setPen(I.mezcla(C["texto2"], "#FFFFFF", 0.3))
                fo = QFontMetricsF(f_ori)
                p.drawText(QPointF(tarjeta.left() + pad, tarjeta.top() + pad + fm.height() + fo.ascent()),
                           fo.elidedText(m["origen"], Qt.ElideRight, tarjeta.width() - 2 * pad))
            # la barra de la tarjeta y la mascota caminando por ella
            tx0, tx1 = tarjeta.left() + pad, tarjeta.right() - pad
            ty = tarjeta.bottom() - pad - 4 * fs
            ancho_u = (tx1 - tx0) / U
            # camina de punta a punta de la pista; en los extremos aparece y se desvanece
            media = m["ancho"] / 2
            ini, fin = media * 0.6, max(media * 0.6 + 1, ancho_u - media * 0.6)
            recorrido = fin - ini
            pos = ini + (tj * VELOCIDAD * 0.85 + 23 * j) % recorrido
            borde = I.liso(pos, ini, ini + 14) * (1 - I.liso(pos, fin - 14, fin))
            self._pista(p, tx0, tx1, ty, fs, tx0 + pos * U)
            alto_u = m["alto"] + 4
            img = capa_mascotas(ancho_u, alto_u, [(m, pos, alto_u - 1, 0.0, tj)])
            recorte = QPainterPath()
            recorte.addRoundedRect(tarjeta, 16 * fs, 16 * fs)
            p.setClipPath(recorte, Qt.IntersectClip)
            p.setOpacity(a * cambio * borde)
            dibujar_capa(p, img, tx0, ty - (alto_u - 1) * U, k)
            p.restore()
        # cuántas hay
        n = len(lista)
        f = self._f(13 * fs, QFont.DemiBold)
        p.save()
        p.setOpacity(alfa_ * I.eo(I.tramo(tl, 1.2, 0.8)))
        p.setFont(f)
        p.setPen(I.mezcla(C["texto2"], "#FFFFFF", 0.5))
        p.drawText(QRectF(r.left(), y_ini + alto_total + 8 * fs, r.width(), 24 * fs),
                   int(Qt.AlignRight | Qt.AlignVCenter), f"{n} mascotitas para elegir")
        p.restore()

    # ---------------------------------------------------------------- mini Caudal

    def _mini_caudal(self, p, R, clave, fs, t, mascota=None, pos_masc=0.0):
        """Una Caudal pequeñita pintada con los colores de un fondo con personaje, con su personaje
        sentado sobre la barra del reproductor. Devuelve el rectángulo de la barra de progreso."""
        T = _tema(clave)
        ac = T["acento"]
        rad = 16 * fs
        ruta = QPainterPath()
        ruta.addRoundedRect(R, rad, rad)
        p.save()
        p.setClipPath(ruta)
        g = QLinearGradient(R.topLeft(), R.bottomLeft())
        g.setColorAt(0, T["panel"])
        g.setColorAt(1, T["fondo"])
        p.fillRect(R, g)
        brillo = QRadialGradient(QPointF(R.right() - R.width() * 0.1, R.top()), R.width() * 0.7)
        brillo.setColorAt(0, I.alfa(ac, 46))
        brillo.setColorAt(1, I.alfa(ac, 0))
        p.fillRect(R, brillo)
        w, h = R.width(), R.height()
        alto_barra = max(46 * fs, h * 0.15)
        barra = QRectF(R.left(), R.bottom() - alto_barra, w, alto_barra)
        lateral = QRectF(R.left(), R.top(), w * 0.22, h - alto_barra)
        p.setPen(Qt.NoPen)
        # barra lateral
        p.setBrush(I.alfa(T["panel"], 235))
        p.drawRect(lateral)
        u = min(w, h) / 100.0
        lx = lateral.left() + 4 * u
        ly = lateral.top() + 5 * u
        p.setBrush(ac)
        p.drawEllipse(QRectF(lx, ly, 4.4 * u, 4.4 * u))
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawRoundedRect(QRectF(lx + 6 * u, ly + 1.3 * u, lateral.width() * 0.42, 1.8 * u), 0.9 * u, 0.9 * u)
        ly += 11 * u
        for j in range(5):
            fila = QRectF(lateral.left() + 2.4 * u, ly, lateral.width() - 4.8 * u, 6 * u)
            if j == 0:
                p.setBrush(T["sup3"])
                p.drawRoundedRect(fila, 1.6 * u, 1.6 * u)
            p.setBrush(ac if j == 0 else QColor(255, 255, 255, 120))
            p.drawEllipse(QRectF(fila.left() + 1.8 * u, fila.center().y() - 1.2 * u, 2.4 * u, 2.4 * u))
            p.setBrush(QColor(255, 255, 255, 200 if j == 0 else 90))
            p.drawRoundedRect(QRectF(fila.left() + 5.6 * u, fila.center().y() - 0.7 * u,
                                     fila.width() * (0.55 - 0.05 * (j % 3)), 1.4 * u), 0.7 * u, 0.7 * u)
            ly += 7.4 * u
        ly += 3 * u
        for j in range(4):
            p.setBrush(T["sup2"])
            p.drawRoundedRect(QRectF(lateral.left() + 3 * u, ly, 4.6 * u, 4.6 * u), 1 * u, 1 * u)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawRoundedRect(QRectF(lateral.left() + 9 * u, ly + 1.6 * u, lateral.width() * 0.4, 1.3 * u),
                              0.6 * u, 0.6 * u)
            ly += 6.6 * u
        # contenido
        cx0 = lateral.right() + 4 * u
        cw = R.right() - 4 * u - cx0
        cy = R.top() + 4 * u
        p.setBrush(T["sup2"])
        p.drawRoundedRect(QRectF(cx0, cy, cw * 0.44, 5 * u), 2.5 * u, 2.5 * u)
        p.setBrush(QColor(255, 255, 255, 60))
        p.drawEllipse(QRectF(cx0 + cw - 5 * u, cy, 5 * u, 5 * u))
        cy += 10 * u
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawRoundedRect(QRectF(cx0, cy, cw * 0.32, 3 * u), 1.5 * u, 1.5 * u)
        cy += 6.5 * u
        n_tar = 4
        sepc = 3 * u
        lado = (cw - sepc * (n_tar - 1)) / n_tar
        lado = min(lado, (h - alto_barra) * 0.34)
        for j in range(n_tar):
            rr = QRectF(cx0 + j * (lado + sepc), cy, lado, lado)
            gg = QLinearGradient(rr.topLeft(), rr.bottomRight())
            gg.setColorAt(0, I.tono(ac, j * 34 - 20, 0.45, 0.75))
            gg.setColorAt(1, I.mezcla(I.tono(ac, j * 34 + 20, 0.4, 0.5), T["fondo"], 0.45))
            p.setBrush(gg)
            p.drawRoundedRect(rr, 2.2 * u, 2.2 * u)
            p.setBrush(QColor(255, 255, 255, 150))
            p.drawRoundedRect(QRectF(rr.left(), rr.bottom() + 2 * u, lado * 0.8, 1.6 * u), 0.8 * u, 0.8 * u)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawRoundedRect(QRectF(rr.left(), rr.bottom() + 4.6 * u, lado * 0.5, 1.4 * u), 0.7 * u, 0.7 * u)
        cy += lado + 10 * u
        fila_h = 7.2 * u
        j = 0
        while cy + fila_h < barra.top() - 2 * u and j < 6:
            fr = QRectF(cx0, cy, cw, fila_h - 1.4 * u)
            p.setBrush(I.alfa(T["sup"], 220) if j % 2 == 0 else I.alfa(T["sup"], 110))
            p.drawRoundedRect(fr, 1.6 * u, 1.6 * u)
            p.setBrush(I.tono(ac, j * 50, 0.4, 0.6))
            p.drawRoundedRect(QRectF(fr.left() + 1.2 * u, fr.top() + 0.9 * u, fr.height() - 1.8 * u,
                                     fr.height() - 1.8 * u), 1 * u, 1 * u)
            p.setBrush(QColor(255, 255, 255, 190))
            p.drawRoundedRect(QRectF(fr.left() + fr.height() + 1.5 * u, fr.center().y() - 0.8 * u, cw * 0.28, 1.6 * u),
                              0.8 * u, 0.8 * u)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawRoundedRect(QRectF(fr.right() - cw * 0.12, fr.center().y() - 0.7 * u, cw * 0.08, 1.4 * u),
                              0.7 * u, 0.7 * u)
            cy += fila_h
            j += 1
        # barra del reproductor
        p.setBrush(I.alfa(T["sup"], 250))
        p.drawRect(barra)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRect(QRectF(barra.left(), barra.top(), barra.width(), max(1.0, fs)))
        bu = barra.height() / 10.0
        tapa = QRectF(barra.left() + 2.2 * bu, barra.top() + 2 * bu, 6 * bu, 6 * bu)
        gg = QLinearGradient(tapa.topLeft(), tapa.bottomRight())
        gg.setColorAt(0, ac)
        gg.setColorAt(1, I.tono(ac, 40, 0.4, 0.5))
        p.setBrush(gg)
        p.drawRoundedRect(tapa, bu, bu)
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawRoundedRect(QRectF(tapa.right() + 1.6 * bu, tapa.top() + 1.2 * bu, w * 0.12, 1.2 * bu), 0.6 * bu, 0.6 * bu)
        p.setBrush(QColor(255, 255, 255, 90))
        p.drawRoundedRect(QRectF(tapa.right() + 1.6 * bu, tapa.top() + 3.6 * bu, w * 0.08, 1.0 * bu), 0.5 * bu, 0.5 * bu)
        mx = R.left() + w / 2
        boton = 3.6 * bu
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(QPointF(mx, barra.top() + 3.4 * bu), boton / 2, boton / 2)
        tri = QPainterPath()
        tri.moveTo(mx - 0.45 * bu, barra.top() + 2.7 * bu)
        tri.lineTo(mx - 0.45 * bu, barra.top() + 4.1 * bu)
        tri.lineTo(mx + 0.75 * bu, barra.top() + 3.4 * bu)
        tri.closeSubpath()
        p.setBrush(T["sup"])
        p.drawPath(tri)
        p.setBrush(QColor(255, 255, 255, 150))
        for s in (-1, 1):
            p.drawEllipse(QPointF(mx + s * 4 * bu, barra.top() + 3.4 * bu), 0.9 * bu, 0.9 * bu)
        px0, px1 = R.left() + w * 0.3, R.left() + w * 0.7
        py = barra.top() + 7.2 * bu
        relleno = px0 + (px1 - px0) * (0.25 + 0.5 * ((t * 0.06) % 1.0)) if mascota is None else None
        if mascota is not None:
            relleno = px0 + max(0.0, pos_masc) * 2 * self._k()
        self._pista(p, px0, px1, py, fs, relleno, grosor=max(2.5, 3 * fs))
        p.setBrush(QColor(255, 255, 255, 90))
        p.drawRoundedRect(QRectF(R.right() - w * 0.13, py - 0.6 * bu, w * 0.08, 1.2 * bu), 0.6 * bu, 0.6 * bu)
        p.restore()
        # el personaje sentado sobre la barra, en la esquina derecha (fuera del recorte: asoma por arriba)
        pm = _pixmap_personaje(clave)
        if pm is not None:
            k = self._k()
            pw, ph = pm.width() * k, pm.height() * k
            x = round(R.right() - pw - 16 * fs)
            y = round(barra.top() - ph + 3 * k)
            sombra = QRadialGradient(QPointF(x + pw / 2, barra.top() + 1), pw * 0.5)
            sombra.setColorAt(0, QColor(0, 0, 0, 130))
            sombra.setColorAt(1, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(sombra)
            p.drawEllipse(QRectF(x + pw * 0.06, barra.top() - 5, pw * 0.88, 11))
            p.save()
            p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            p.drawPixmap(QRectF(x, y, pw, ph), pm, QRectF(pm.rect()))
            p.restore()
        # borde fino de la ventana
        p.setPen(QPen(QColor(255, 255, 255, 50), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(R.adjusted(0.5, 0.5, -0.5, -0.5), rad, rad)
        return QRectF(px0, py, px1 - px0, 0)

    def _ilus_fondos(self, p, L, tl, alfa_, dx):
        r = QRectF(L["ilus"]).translated(dx, 0)
        fs = L["fs"]
        temas = self._temas
        if not temas:
            return
        entrada = I.eo(I.tramo(tl, 0.3, 0.9))
        alto_pie = 64 * fs
        alto_max = r.height() - alto_pie - 30 * fs           # 30: lo que asoma el personaje por arriba
        ancho = min(r.width(), alto_max / 0.66)
        alto = ancho * 0.66
        R = QRectF(r.left() + (r.width() - ancho) / 2, r.top() + 30 * fs + (alto_max - alto) / 2 + (1 - entrada) * 30 * fs,
                   ancho, alto)
        tt = max(0.0, tl - 0.3)
        idx = int(tt / PERIODO_FONDO)
        fase = tt - idx * PERIODO_FONDO
        actual = temas[idx % len(temas)]
        previo = temas[(idx - 1) % len(temas)] if idx > 0 else None
        mezcla_ = I.eio(I.clamp(fase / 0.5)) if previo else 1.0
        # un halo con el color del fondo que se ve
        T = _tema(actual)
        halo = QRadialGradient(R.center(), R.width() * 0.75)
        halo.setColorAt(0, I.alfa(T["acento"], int(70 * entrada)))
        halo.setColorAt(1, I.alfa(T["acento"], 0))
        p.save()
        p.setOpacity(alfa_)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(R.center(), R.width() * 0.75, R.height() * 0.85)
        # sombra de la ventanita
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(R.translated(0, 10 * fs).adjusted(6 * fs, 6 * fs, -6 * fs, 4 * fs), 18 * fs, 18 * fs)
        if previo and mezcla_ < 1.0:
            p.setOpacity(alfa_ * entrada)
            self._mini_caudal(p, R, previo, fs, tl)
        p.setOpacity(alfa_ * entrada * mezcla_)
        self._mini_caudal(p, R, actual, fs, tl)
        # el nombre del fondo y los puntitos de todos
        p.setOpacity(alfa_ * entrada)
        f = self._f(16 * fs, QFont.ExtraBold)
        fm = QFontMetricsF(f)
        nombre = T["nombre"]
        y_pie = R.bottom() + 20 * fs
        chip_w = fm.horizontalAdvance(nombre) + 46 * fs
        chip = QRectF(R.center().x() - chip_w / 2, y_pie, chip_w, fm.height() + 12 * fs)
        p.setBrush(I.alfa(T["acento"], 230))
        p.drawRoundedRect(chip, chip.height() / 2, chip.height() / 2)
        p.setBrush(QColor(255, 255, 255, 230))
        p.drawEllipse(QPointF(chip.left() + 16 * fs, chip.center().y()), 4 * fs, 4 * fs)
        p.setFont(f)
        oscuro = T["acento"].lightnessF() > 0.55
        p.setPen(I.mezcla(T["acento"], "#000000", 0.82) if oscuro else QColor("#FFFFFF"))
        p.drawText(QRectF(chip.left() + 26 * fs, chip.top(), chip.width() - 34 * fs, chip.height()),
                   int(Qt.AlignVCenter | Qt.AlignLeft), nombre)
        n = len(temas)
        paso = 13 * fs
        x = R.center().x() - (n - 1) * paso / 2
        yd = chip.bottom() + 16 * fs
        for j, c in enumerate(temas):
            col = QColor(TEMAS[c][1])
            activo = c == actual
            rr = (4.6 if activo else 3.2) * fs
            if activo:
                p.setBrush(QColor(255, 255, 255, 230))
                p.drawEllipse(QPointF(x + j * paso, yd), rr + 1.6 * fs, rr + 1.6 * fs)
            p.setBrush(col)
            p.drawEllipse(QPointF(x + j * paso, yd), rr, rr)
        p.restore()

    # ---------------------------------------------------------------- fondo + mascota juntos

    def _ilus_juntos(self, p, L, tl, alfa_, dx):
        r = QRectF(L["ilus"]).translated(dx, 0)
        fs = L["fs"]
        temas = self._temas
        if not temas:
            return
        k = self._k()
        U = 2 * k
        entrada = I.eo(I.tramo(tl, 0.3, 0.9))
        tt = max(0.0, tl - 0.3)
        idx = int(tt / PERIODO_JUNTOS)
        fase = tt - idx * PERIODO_JUNTOS
        actual = temas[idx % len(temas)]
        previo = temas[(idx - 1) % len(temas)] if idx > 0 else None
        clic = 0.55                                  # cuándo «se hace clic» en el fondo nuevo
        # -------- arriba: los fondos con personaje, como en Ajustes › Aspecto
        cols = 6
        filas = math.ceil(len(temas) / cols)
        sep = 8 * fs
        alto_b = 16 * fs + 54 * fs + 10 * fs + 52 * U + 20 * fs
        asoma = 48 * k * 2 * 0.95                     # lo que asoma el personaje sentado por arriba
        alto_barra_zona = alto_b + asoma
        alto_rej = min(r.height() - alto_barra_zona - 24 * fs, filas * 48 * fs + (filas - 1) * sep)
        th = (alto_rej - (filas - 1) * sep) / filas
        tw = (r.width() - (cols - 1) * sep) / cols
        y_rej = r.top() + max(0.0, (r.height() - alto_rej - 24 * fs - alto_barra_zona) / 2) + (1 - entrada) * 20 * fs
        f_tile = self._f(min(12.5 * fs, th * 0.3), QFont.Bold)
        fm_t = QFontMetricsF(f_tile)
        elegido = actual if (fase >= clic or previo is None) else previo
        rect_elegido = None
        rect_actual = None
        p.save()
        p.setOpacity(alfa_ * entrada)
        for j, c in enumerate(temas):
            fi, co = divmod(j, cols)
            rr = QRectF(r.left() + co * (tw + sep), y_rej + fi * (th + sep), tw, th)
            T = _tema(c)
            g = QLinearGradient(rr.topLeft(), rr.bottomRight())
            g.setColorAt(0, T["sup2"])
            g.setColorAt(1, T["fondo"])
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(rr, 10 * fs, 10 * fs)
            p.setBrush(T["acento"])
            p.drawEllipse(QPointF(rr.left() + 12 * fs, rr.center().y()), 5 * fs, 5 * fs)
            p.setFont(f_tile)
            p.setPen(QColor(255, 255, 255, 235))
            p.drawText(QRectF(rr.left() + 22 * fs, rr.top(), rr.width() - 26 * fs, rr.height()),
                       int(Qt.AlignVCenter | Qt.AlignLeft), fm_t.elidedText(T["nombre"], Qt.ElideRight,
                                                                           rr.width() - 26 * fs))
            if c == elegido:
                rect_elegido = rr
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(T["acento"], 2.4 * fs))
                p.drawRoundedRect(rr.adjusted(1, 1, -1, -1), 10 * fs, 10 * fs)
            if c == actual:
                rect_actual = rr
        # el puntero va al fondo nuevo y hace clic
        if rect_actual is not None:
            if previo is not None and rect_elegido is not None and fase < clic:
                src = self._rect_tema(previo, r, y_rej, tw, th, sep, cols)
                m = I.eio(I.clamp(fase / (clic * 0.85)))
                cx = src.center().x() + (rect_actual.center().x() - src.center().x()) * m
                cy = src.center().y() + (rect_actual.center().y() - src.center().y()) * m
            else:
                cx, cy = rect_actual.center().x(), rect_actual.center().y()
            pulso = 1.0 - 0.18 * math.sin(math.pi * I.clamp((fase - clic + 0.12) / 0.24))
            if fase >= clic and fase < clic + 0.5:
                onda = (fase - clic) / 0.5
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, int(200 * (1 - onda))), 2 * fs))
                p.drawEllipse(QPointF(cx + 2 * fs, cy + 2 * fs), 8 * fs + 22 * fs * onda, 8 * fs + 22 * fs * onda)
            I.cursor(p, cx + 6 * fs, cy + 4 * fs, 2.2 * fs * pulso)
        p.restore()

        # -------- abajo: la barra del reproductor de cerca
        y_b = y_rej + alto_rej + 24 * fs + asoma + (1 - entrada) * 30 * fs
        barra = QRectF(r.left(), y_b, r.width(), alto_b)
        mezcla_ = I.eio(I.clamp((fase - clic) / 0.45)) if (previo is not None) else 1.0
        if previo is not None and fase < clic:
            mezcla_ = 0.0
        p.save()
        if previo is not None and mezcla_ < 1.0:
            p.setOpacity(alfa_ * entrada)
            self._barra_cerca(p, barra, previo, fs, PERIODO_JUNTOS + fase, 1.0)
        p.setOpacity(alfa_ * entrada * mezcla_)
        self._barra_cerca(p, barra, actual, fs, max(0.0, fase - clic), mezcla_)
        p.restore()

    def _rect_tema(self, clave, r, y_rej, tw, th, sep, cols):
        j = self._temas.index(clave)
        fi, co = divmod(j, cols)
        return QRectF(r.left() + co * (tw + sep), y_rej + fi * (th + sep), tw, th)

    def _barra_cerca(self, p, barra, clave, fs, t, a_masc):
        """La barra del reproductor de cerca: el personaje sentado en la esquina y su mascota caminando."""
        T = _tema(clave)
        k = self._k()
        U = 2 * k
        rad = 16 * fs
        g = QLinearGradient(barra.topLeft(), barra.bottomLeft())
        g.setColorAt(0, T["sup2"])
        g.setColorAt(1, T["sup"])
        p.setPen(QPen(I.alfa(T["acento"], 90), 1.2))
        p.setBrush(g)
        p.drawRoundedRect(barra, rad, rad)
        brillo = QRadialGradient(QPointF(barra.right() - barra.width() * 0.2, barra.top()), barra.width() * 0.5)
        brillo.setColorAt(0, I.alfa(T["acento"], 50))
        brillo.setColorAt(1, I.alfa(T["acento"], 0))
        p.setPen(Qt.NoPen)
        p.setBrush(brillo)
        p.drawRoundedRect(barra, rad, rad)
        tapa = QRectF(barra.left() + 18 * fs, barra.top() + 16 * fs, 54 * fs, 54 * fs)
        gg = QLinearGradient(tapa.topLeft(), tapa.bottomRight())
        gg.setColorAt(0, T["acento"])
        gg.setColorAt(1, I.tono(T["acento"], 40, 0.4, 0.45))
        p.setBrush(gg)
        p.drawRoundedRect(tapa, 8 * fs, 8 * fs)
        I.nota(p, tapa.center().x() - 4 * fs, tapa.center().y() - 2 * fs, tapa.height() * 0.42, QColor(255, 255, 255, 230), 0)
        f1 = self._f(15 * fs, QFont.Bold)
        f2 = self._f(12.5 * fs, QFont.Normal)
        p.setFont(f1)
        p.setPen(QColor("#FFFFFF"))
        xt = tapa.right() + 14 * fs
        p.drawText(QPointF(xt, tapa.top() + QFontMetricsF(f1).ascent() + 2 * fs), "Tu canción favorita")
        p.setFont(f2)
        p.setPen(I.mezcla(C["texto2"], "#FFFFFF", 0.35))
        p.drawText(QPointF(xt, tapa.top() + QFontMetricsF(f1).height() + QFontMetricsF(f2).ascent() + 5 * fs),
                   f"Fondo {T['nombre']}")
        # la pista de progreso, abajo a lo ancho, y la mascota caminando por ella
        px0 = barra.left() + 22 * fs
        px1 = barra.right() - 22 * fs
        py = barra.bottom() - 20 * fs
        m = M.por_clave(clave)
        if m is not None and (M.es_exclusiva(m) or not M.cuadros(clave)):
            m = None
        ancho_u = (px1 - px0) / U
        pos = 6 + t * VELOCIDAD * 0.9
        pos = min(pos, ancho_u * 0.62)
        self._pista(p, px0, px1, py, fs, px0 + pos * U, color=T["acento"])
        if m is not None:
            alto_u = m["alto"] + 4
            img = capa_mascotas(ancho_u, alto_u, [(m, pos, alto_u - 1, 0.0, t)])
            p.save()
            p.setOpacity(p.opacity())
            dibujar_capa(p, img, px0, py - (alto_u - 1) * U, k)
            p.restore()
        # el personaje del fondo, sentado sobre el borde de arriba, a la derecha
        pm = _pixmap_personaje(clave)
        if pm is not None:
            pw, ph = pm.width() * k, pm.height() * k
            x = round(barra.right() - pw - 24 * fs)
            y = round(barra.top() - ph + 4 * k)
            sombra = QRadialGradient(QPointF(x + pw / 2, barra.top() + 1), pw * 0.5)
            sombra.setColorAt(0, QColor(0, 0, 0, 120))
            sombra.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(sombra)
            p.drawEllipse(QRectF(x + pw * 0.06, barra.top() - 5, pw * 0.88, 11))
            p.save()
            p.setRenderHint(QPainter.SmoothPixmapTransform, False)
            p.drawPixmap(QRectF(x, y, pw, ph), pm, QRectF(pm.rect()))
            p.restore()

    # ================================================================ pintura

    def _pintar_diap(self, p, i, tl, alfa_, off):
        w, h = self.width(), self.height()
        L = self._layout(i)
        clave = DIAPOSITIVAS[i]["clave"]
        dxi, dxt = off * 0.10 * w, off * 0.06 * w
        p.save()
        p.setClipRect(QRectF(0, 0, w, h))
        if clave == "mascotas":
            self._ilus_mascotas(p, L, tl, alfa_, dxi)
        elif clave == "fondos":
            self._ilus_fondos(p, L, tl, alfa_, dxi)
        elif clave == "juntos":
            self._ilus_juntos(p, L, tl, alfa_, dxi)
        p.restore()
        p.save()
        self._pintar_texto(p, i, tl, alfa_, dxt)
        p.restore()
        if L["desfile"] is not None:
            lista = self._desfile if clave == "portada" else self._desfile_final
            a = I.eo(I.tramo(tl, 0.9, 1.0))
            p.save()
            self._desfile_en(p, QRectF(L["desfile"]).translated(dxt, 0), lista, tl + 4.0, alfa_ * a)
            p.restore()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        self._pal = I.Paleta(C)
        e = self._p_trans
        t_nuevo = DIAPOSITIVAS[self.indice]["tono"]
        t_viejo = DIAPOSITIVAS[self._ant]["tono"] if self._ant is not None else t_nuevo
        self._pintar_fondo(p, t_viejo + (t_nuevo - t_viejo) * e)
        if self._ant is not None and e < 1.0:
            self._pintar_diap(p, self._ant, self._tl_ant, I.clamp(1 - e * 1.7), -self._dir * e)
            self._pintar_diap(p, self.indice, self._tl, I.clamp((e - 0.15) / 0.85), self._dir * (1 - e))
        else:
            self._pintar_diap(p, self.indice, self._tl, 1.0, 0.0)
        p.setOpacity(1.0)
        self._pintar_marco(p)

    def _pintar_marco(self, p):
        w = self.width()
        fs = self._escala()
        pal = self._pal
        if self.indice > 0 and self.indice < self.n - 1:
            from .iconos import icono_app
            lado = round(30 * fs)
            pm = self._logo_cache.get(("m", lado)) or icono_app(lado)
            self._logo_cache[("m", lado)] = pm
            a = I.clamp(self._tl / 0.8) if self._ant in (0, self.n - 1) else 1.0
            p.setOpacity(a)
            p.drawPixmap(round(56 * fs), round(30 * fs), pm)
            p.setPen(QColor("#FFFFFF"))
            p.setFont(self._f(17 * fs, QFont.Black, True))
            p.drawText(QPointF(56 * fs + lado / pm.devicePixelRatio() + 10 * fs, 30 * fs + lado * 0.72), "Caudal")
            p.setOpacity(1.0)
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
