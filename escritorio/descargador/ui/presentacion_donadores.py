# -*- coding: utf-8 -*-
"""Presentación «Gracias, donador»: el agradecimiento más emotivo, para quien es donador o fundador
DE VERDAD (la prueba gratuita no cuenta). Sale UNA vez por dispositivo
(ajustes["presentacion_donadores_vista"]), unos 8 s después de arrancar y después de «Somos 100»
si esa se abre. Sigue GUION_DONADORES.md: cinco diapositivas con los mismos textos en Windows y Android.

Estructura y animaciones de presentacion_100 (aurora de fondo, fundido con desplazamiento entre
diapositivas, puntos de progreso, entradas escalonadas, reloj de ~60 FPS solo con la ventana abierta),
con paleta dorada y ámbar. Sin marco y a la medida de la ventana de Caudal.
"""

import math
import random

from PySide6.QtCore import (QElapsedTimer, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation, QRectF,
                            QTimer, Qt, QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication, QDialog

from . import ilustraciones_grandes as I
from .componentes import fuente
from .estilos import C
from .presentacion_100 import Presentacion100, _envolver, _icono, _ruta_corazon
from .presentacion_grande import _Boton

CLAVE_VISTA = "presentacion_donadores_vista"
SITIO = "https://caudal-musica.netlify.app"
URL_MOSTRAR = "caudal-musica.netlify.app"
FIRMA = "— Con todo el cariño, el equipo de Caudal 💛"
COLUMNAS = 3

PALETA_DORADA = dict(acento="#E8AB16", acento_alto="#FFD76A", acento_bajo="#7A5300",
                     acento_texto="#1A1200", fondo="#0C0904", panel="#2A1F08")

# Diez exclusivas del guion (título y una línea), en su orden
EXCLUSIVAS = [
    ("Escenarios vivos", "11 ilustraciones animadas que reaccionan a la música, más Retro y Synthwave."),
    ("Tu imagen o tu GIF", "De fondo en la escena y en el reproductor."),
    ("Marcos animados", "Aurora, Fuego, Oro, Neón, Hielo, Arcoíris y Galaxia alrededor de tu foto."),
    ("Nombre con efecto", "Brillo, Degradado, Arcoíris o Neón, y el color que quieras."),
    ("Estéticas y temas", "Retro, Cyberpunk, Japón samurái, Gótico, Lo-fi, Kuromi, Cinnamoroll y más."),
    ("Sonido a tu medida", "Ecualizador avanzado y un ecualizador que se adapta a cada canción."),
    ("Letras con estilo", "Estilos de letra animada y tarjetas exclusivas para compartir en tus estados."),
    ("Tu perfil, único", "Portada animada, foto en GIF, cápsula del tiempo y dedicatorias."),
    ("Visualizador y escena", "El visualizador a pantalla completa y la escena de escritorio con todos sus fondos."),
    ("Tu lugar en el muro", "El muro de agradecimiento de Caudal y la etiqueta de Donador en tu perfil."),
]


def diapositivas(nombre, fundador=False):
    """Los textos del guion. Sin nombre, el título queda en «Gracias» a secas."""
    titulo_1 = f"Gracias, {nombre}" if nombre else "Gracias"
    return [
        dict(vis="medalla", titulo=titulo_1, texto="Tú hiciste posible lo que Caudal es hoy.", arriba=230),
        dict(vis="sol", titulo="Ayudaste a que Caudal crezca",
             texto="Caudal es gratis para todos gracias a personas como tú. Tu apoyo pagó servidores, horas de "
                   "trabajo y cada mejora que hoy disfrutan cien personas. No fue solo una donación: fue confiar "
                   "en algo que estaba empezando.",
             pie="Este proyecto también es tuyo.", arriba=130),
        dict(vis="demo", demo="mi_perfil", titulo="Tu perfil de donador",
             texto="Así te ven los demás: tu marco animado, tu nombre con efecto y tus insignias."),
        dict(vis="demo", demo="escenarios", titulo="Escenarios vivos, solo para ti",
             texto="11 ilustraciones que reaccionan a la música, más Retro, Synthwave y tu propia imagen o GIF."),
        dict(vis="demo", demo="perfil_premium", titulo="Marcos y nombres que brillan",
             texto="Aurora, Fuego, Oro, Neón, Hielo, Arcoíris y Galaxia; y tu nombre con Brillo, Degradado, "
                   "Arcoíris o Neón."),
        dict(vis="demo", demo="temas", titulo="Estéticas exclusivas",
             texto="Cambia todo Caudal de estilo: Cyberpunk, Japón samurái, Kuromi, Cinnamoroll, Lo-fi, Gótico y más."),
        dict(vis="demo", demo="ecualizador", titulo="Sonido a tu medida",
             texto="El ecualizador avanzado y uno que se adapta solo a cada canción."),
        dict(vis="demo", demo="letra", titulo="Letras con estilo",
             texto="Estilos de letra animada y tarjetas exclusivas para compartir en tus estados."),
        dict(vis="grid", titulo="Todas tus exclusivas", texto="", grid=True),
        dict(vis="horizonte", titulo="Y esto sigue",
             texto="Lo próximo es convertir Caudal en una comunidad para toda la gente que ama la música. Tú vas "
                   "a estar en primera fila: cada nueva exclusiva llegará primero a quienes nos ayudan.",
             pie="Si quieres, invita a tu gente: " + URL_MOSTRAR, arriba=130),
        dict(vis="corazon", titulo="Gracias por creer en Caudal.", texto="", pie=FIRMA, arriba=150, abajo=110,
             botones=True),
    ]


class PaletaDorada(I.Paleta):
    """La paleta de presentacion_100 con el acento dorado; los vecinos, ámbar y crema."""

    def __init__(self):
        super().__init__(PALETA_DORADA)
        self.c2 = QColor("#FFB703")          # ámbar
        self.c3 = QColor("#B45309")          # ámbar oscuro
        self.c4 = QColor("#FFF3C4")          # crema
        self.oro = QColor("#FFE08A")


class PresentacionDonadores(QDialog):
    """Las cinco diapositivas del guion. `navegar` lleva a la personalización premium (Ajustes)."""

    DURACION = 900               # ms de la transición entre diapositivas
    BROTE_MS = 900               # ms del brote de partículas al entrar

    def __init__(self, padre=None, ctx=None, nombre="", fundador=False, navegar=None):
        super().__init__(padre)
        self.ctx = ctx
        self._navegar = navegar
        self.medalla = "Fundador de Caudal" if fundador else "Donador de Caudal"
        self.diap = diapositivas(nombre, fundador)
        self.n = len(self.diap)
        self._cache_demos = {"perfil": self._datos_perfil(ctx, nombre, fundador)}
        self._pedir_foto(ctx)
        self.indice = 0
        self._ant = None
        self._dir = 1
        self._p_trans = 1.0
        self._tg = 0.0
        self._tl = 0.0
        self._tl_ant = 0.0
        self._pos_puntos = 0.0
        self._exploto = False
        self._particulas = []
        self._rueda = 0
        self._ultima_rueda = QElapsedTimer()
        self._ultima_rueda.start()
        self._revelado = False
        self._base = None
        self._fondo_img = None
        self._cache_fuentes = {}
        self._cache_lay = {}
        self._puntos = []
        self._pal = PaletaDorada()
        self._anim_trans = None
        self._anim_puntos = None
        self._anim_op = None
        self._anim_brote = None

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setWindowTitle("Gracias, donador")
        self.setAccessibleName("Gracias, donador")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(760, 520)

        self.bt_ant = self._boton("Atrás", self.anterior, "Diapositiva anterior")
        self.bt_sig = self._boton("Siguiente", self.siguiente, "Diapositiva siguiente", principal=True)
        self.bt_descubrir = self._boton("Descubrir mis exclusivas", self._descubrir,
                                        "Descubrir mis exclusivas", principal=True)
        self.bt_seguir = self._boton("Seguir escuchando", self.accept, "Seguir escuchando")

        self._reloj = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(16)                  # ~60 FPS, solo mientras la ventana está abierta
        self._timer.timeout.connect(self._tick)

        self._ajustar_tamano()
        self._actualizar_botones()
        self._colocar_botones()

    @staticmethod
    def _datos_perfil(ctx, nombre, fundador):
        """Lo que se enseña en «Tu perfil de donador», con lo que ya sabe la app (sin esperar a la red)."""
        prem = getattr(ctx, "premium", None)
        cuenta = getattr(ctx, "cuenta", None) or {}
        return {
            "nombre": nombre or str(cuenta.get("nombre") or ""),
            "usuario": str(cuenta.get("usuario") or ""),
            "tipo": "fundador" if fundador else "donador",
            "marco": getattr(prem, "marco", None) if getattr(prem, "marco", "ninguno") != "ninguno" else None,
            "efecto": getattr(prem, "efecto", None) if getattr(prem, "efecto", "ninguno") != "ninguno" else None,
            "tema": getattr(prem, "tema", None),
            "color": getattr(prem, "color_nombre", None),
            "en_pared": bool(getattr(prem, "en_pared", False)),
            "foto": None,
        }

    def _pedir_foto(self, ctx):
        """La foto real del perfil, en segundo plano; mientras tanto se ve la inicial."""
        cuenta = getattr(ctx, "cuenta", None) or {}
        sesion = cuenta.get("sesion") if isinstance(cuenta, dict) else None
        usuario = cuenta.get("usuario") if isinstance(cuenta, dict) else None
        if sesion is None or not usuario:
            return
        try:
            from .. import social as S
            from ..hilos import en_segundo_plano
            from . import imagenes
        except Exception:  # noqa: BLE001
            return

        def ver():
            perfil = S.Social(sesion).ver_perfil(usuario) or {}
            return S.url_foto(perfil.get("foto_url")) if perfil.get("foto_url") else ""

        def llego_url(url):
            if url:
                imagenes.imagen(url, lambda img: self._cache_demos["perfil"].__setitem__("foto", img))

        en_segundo_plano(ver, ok=llego_url, error=lambda _e: None, dueno=self)

    def _boton(self, texto, accion, nombre, principal=False):
        b = _Boton(texto, self, principal)
        b.colores = PALETA_DORADA                   # botones dorados, no del color de la app
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
        for b in (self.bt_descubrir, self.bt_seguir):
            b.configurar(fs, 0.95)

    def _actualizar_botones(self):
        ultimo = self.indice == self.n - 1
        self.bt_sig.setVisible(not ultimo)
        for b in (self.bt_descubrir, self.bt_seguir):
            b.setVisible(ultimo)
        self.bt_ant.setVisible(self.indice > 0)
        d = self.diap[self.indice]
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
            botones = [self.bt_descubrir, self.bt_seguir]
            gap = 16 * fs
            total = sum(b.width() for b in botones) + gap * (len(botones) - 1)
            x = (w - total) / 2
            for b in botones:
                b.move(round(x), round(L["y_botones"] - b.height() / 2))
                x += b.width() + gap
        for b in (self.bt_ant, self.bt_sig, self.bt_descubrir, self.bt_seguir):
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

    def _descubrir(self):
        """«Descubrir mis exclusivas»: cierra la presentación y lleva a la personalización premium."""
        self.accept()
        if self._navegar is not None:
            destino = {"pagina": "ajustes"}
            QTimer.singleShot(0, lambda: self._navegar(destino))

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
        self._anim_brote = QVariantAnimation(self)
        self._anim_brote.setStartValue(0.0)
        self._anim_brote.setEndValue(1.0)
        self._anim_brote.setDuration(self.BROTE_MS)
        self._anim_brote.finished.connect(self._explotar)
        self._anim_brote.start()

    def hideEvent(self, e):
        self._timer.stop()
        if self._base is not None:
            self._base.removeEventFilter(self)
            self._base = None
        super().hideEvent(e)

    def _explotar(self):
        """Al entrar: un brote de partículas doradas (una sola vez)."""
        if self._exploto:
            return
        self._exploto = True
        fs = self._escala()
        L = self._layout(0)
        cx, cy = L["cx"], L["y0"] + L["arriba"] * 0.42
        pal = self._pal
        colores = [pal.al, pal.oro, pal.ac, QColor("#FFFFFF")]
        for k in range(60):
            ang = 2 * math.pi * k / 60 + random.uniform(-0.12, 0.12)
            v = random.uniform(110, 300) * fs
            self._particulas.append(dict(x=cx, y=cy, vx=math.cos(ang) * v, vy=math.sin(ang) * v,
                                         t0=self._tg, r=random.uniform(1.2, 2.8) * fs,
                                         col=random.choice(colores)))
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
        for a in (self._anim_trans, self._anim_puntos, self._anim_op, self._anim_brote):
            if a is not None and a.state() == a.State.Running:
                a.stop()
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
        d = self.diap[i]
        fs = self._escala()
        es_demo = d.get("vis") == "demo"
        col = (min(w * 0.94, 1100 * fs) if d.get("grid") else min(w * 0.86, 980 * fs) if es_demo
               else min(w * 0.82, 820 * fs))
        f_t = self._f((36 if es_demo else 44) * fs, QFont.Black, True)
        f_b = self._f(19 * fs, QFont.Normal)
        f_p = self._f(17 * fs, QFont.DemiBold)
        fm_t, fm_b, fm_p = QFontMetricsF(f_t), QFontMetricsF(f_b), QFontMetricsF(f_p)
        lin_t = _envolver(d["titulo"], f_t, col)
        lin_b = _envolver(d["texto"], f_b, col * 0.92) if d.get("texto") else []
        lin_p = _envolver(d["pie"], f_p, col * 0.9) if d.get("pie") else []
        lh_t, lh_b, lh_p = fm_t.height() * 0.98, fm_b.height() * 1.36, fm_p.height() * 1.3

        arriba = d.get("arriba", 0) * fs
        abajo = d.get("abajo", 0) * fs
        gap_v, gap_t, gap_b = 26 * fs, 18 * fs, 22 * fs
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
        if es_demo:
            disponible = (h - 100 * fs) - 60 * fs - y - gap_b
            alto_d = max(160 * fs, disponible)
            ancho_d = min(col, alto_d * 16 / 9)
            demo = (ancho_d, ancho_d * 9 / 16)
            abajo = demo[1]
        if d.get("grid"):
            # la rejilla ocupa lo que quede; si no cabe a 1280x720, se reduce el texto (mínimo 11 px)
            disponible = (h - 100 * fs) - 70 * fs - y - gap_b
            px = 13 * fs
            grid = self._grid(col, fs, px)
            while grid["total"] > disponible and px > 11:
                px = max(11.0, px - 0.5)
                grid = self._grid(col, fs, px)
            abajo = grid["total"]
        y_abajo = y + (gap_b if abajo else 0.0)
        alto = y_abajo + abajo
        area_top, area_bot = (40 if es_demo else 70) * fs, h - 100 * fs
        y0 = area_top + max(0.0, (area_bot - area_top - alto) / 2.0)

        L = dict(fs=fs, cx=w / 2.0, col=col, arriba=arriba, y0=y0,
                 f_t=f_t, f_b=f_b, f_p=f_p, lin_t=lin_t, lin_b=lin_b, lin_p=lin_p,
                 lh_t=lh_t, lh_b=lh_b, lh_p=lh_p, grid=grid, demo=demo,
                 y_tit=y0 + y_tit, y_body=y0 + y_body, y_pie=y0 + y_pie, y_abajo=y0 + y_abajo)
        if d.get("botones"):
            L["y_botones"] = y0 + y_abajo + abajo / 2.0
        self._cache_lay[clave] = L
        return L

    def _grid(self, col, fs, px):
        """Rejilla 3 columnas de «Tus exclusivas»: tarjetas con icono, título y una línea."""
        gap_c, row_gap = 14 * fs, 12 * fs
        cw = (col - 2 * gap_c) / float(COLUMNAS)
        f_tt = self._f(15 * fs, QFont.Bold)
        f_td = self._f(px, QFont.Normal)
        fm_tt, fm_td = QFontMetricsF(f_tt), QFontMetricsF(f_td)
        ancho_txt = cw - 84 * fs
        tarjetas = []
        for k, (tit, desc) in enumerate(EXCLUSIVAS):
            lt = _envolver(tit, f_tt, ancho_txt)
            ld = _envolver(desc, f_td, ancho_txt)
            alto = 20 * fs + len(lt) * fm_tt.height() + 2 * fs + len(ld) * fm_td.height() * 1.05 + 18 * fs
            tarjetas.append(dict(lin_t=lt, lin_d=ld, alto=max(80 * fs, alto), icono=k))
        filas = []
        for ini in range(0, len(tarjetas), COLUMNAS):
            filas.append(max(t["alto"] for t in tarjetas[ini:ini + COLUMNAS]))
        for k, t in enumerate(tarjetas):
            fila, c = divmod(k, COLUMNAS)
            en_fila = min(COLUMNAS, len(tarjetas) - fila * COLUMNAS)
            margen = (COLUMNAS - en_fila) * (cw + gap_c) / 2.0      # una fila incompleta queda centrada
            t["x"] = margen + c * (cw + gap_c)
            t["y"] = sum(filas[:fila]) + fila * row_gap
            t["w"] = cw
            t["h"] = filas[fila]
        total = sum(filas) + row_gap * (len(filas) - 1)
        return dict(tarjetas=tarjetas, total=total, f_tt=f_tt, f_td=f_td)

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

    def _pintar_textos(self, p, L, tl, a, dx):
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

    # ================================================================ visuales por diapositiva

    def _vis_medalla(self, p, L, tl, a, dx):
        """La medalla dorada: destello al entrar, gira suavemente y lleva la etiqueta debajo."""
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] * 0.42
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.0, 0.8))
        latido = 0.5 + 0.5 * math.sin(self._tg * 1.6)
        R = 70 * fs
        sx = 0.35 + 0.65 * abs(math.cos(self._tg * 0.7))      # el giro: la medalla se ve de canto y de frente
        p.setOpacity(a * r)
        # rayos dorados que giran despacio detrás
        p.save()
        p.translate(cx, cy)
        p.rotate(self._tg * 6.0)
        largo = 300 * fs
        rg = QRadialGradient(QPointF(0, 0), largo)
        rg.setColorAt(0, I.alfa(pal.oro, 60))
        rg.setColorAt(0.55, I.alfa(pal.ac, 18))
        rg.setColorAt(1, I.alfa(pal.ac, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(rg)
        for k in range(16):
            ang = math.radians(k * 22.5)
            abre = math.radians(4.0 if k % 2 == 0 else 2.0)
            p.drawPolygon(QPolygonF([QPointF(0, 0),
                                     QPointF(math.cos(ang - abre) * largo, math.sin(ang - abre) * largo),
                                     QPointF(math.cos(ang + abre) * largo, math.sin(ang + abre) * largo)]))
        p.restore()
        I.brillo(p, cx, cy, 240 * fs, pal.ac, int(80 + 40 * latido))
        # cintas de la medalla (detrás del disco)
        for lado in (-1, 1):
            cinta = QPolygonF([QPointF(cx + lado * R * 0.18, cy + R * 0.55), QPointF(cx + lado * R * 0.62, cy + R * 0.40),
                               QPointF(cx + lado * R * 0.78, cy + R * 1.55), QPointF(cx + lado * R * 0.50, cy + R * 1.35),
                               QPointF(cx + lado * R * 0.30, cy + R * 1.62)])
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#B45309") if lado < 0 else QColor("#92400E"))
            p.drawPolygon(cinta)
        p.setPen(Qt.NoPen)
        for k in range(8):                                  # motas doradas orbitando
            ang = self._tg * 0.6 + k * math.pi / 4
            x = cx + R * 1.9 * math.cos(ang)
            y = cy + R * 0.9 * math.sin(ang)
            p.setBrush(QColor(255, 230, 150, int(90 + 120 * math.sin(self._tg * 2 + k) ** 2)))
            p.drawEllipse(QPointF(x, y), 2.2 * fs, 2.2 * fs)
        esc = 0.6 + 0.4 * r
        p.save()
        p.translate(cx, cy)
        p.scale(sx * esc, esc)
        g = QLinearGradient(-R, -R, R, R)
        g.setColorAt(0, pal.al)
        g.setColorAt(0.5, pal.ac)
        g.setColorAt(1, pal.ba)
        p.setPen(I.lapiz(pal.al, max(1.4, 2.4 * fs)))
        p.setBrush(g)
        p.drawEllipse(QPointF(0, 0), R, R)
        p.setBrush(Qt.NoBrush)
        p.setPen(I.lapiz(I.alfa(pal.tx, 120), max(1.0, 1.6 * fs)))
        p.drawEllipse(QPointF(0, 0), R * 0.80, R * 0.80)          # canto interior grabado
        p.setPen(Qt.NoPen)
        I.estrella(p, 0, 0, R * 0.52, R * 0.22, QColor(pal.tx))
        # reflejo que barre la medalla
        brillo_x = (math.fmod(self._tg * 0.5, 1.6) - 0.8) * R * 2.2
        rb = QLinearGradient(brillo_x - R * 0.3, -R, brillo_x + R * 0.3, R)
        rb.setColorAt(0, QColor(255, 255, 255, 0))
        rb.setColorAt(0.5, QColor(255, 255, 255, 110))
        rb.setColorAt(1, QColor(255, 255, 255, 0))
        clip = QPainterPath()
        clip.addEllipse(QPointF(0, 0), R, R)
        p.setClipPath(clip)
        p.fillRect(QRectF(-R, -R, 2 * R, 2 * R), rb)
        p.setClipping(False)
        p.restore()
        # etiqueta «Donador de Caudal» o «Fundador de Caudal»
        p.setOpacity(a * r)
        f = self._f(15 * fs, QFont.ExtraBold)
        ancho = QFontMetricsF(f).horizontalAdvance(self.medalla)
        rect = QRectF(cx - (ancho + 44 * fs) / 2, cy + R * 1.75, ancho + 44 * fs, 32 * fs)
        p.setBrush(I.alfa(pal.ac, 60))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        p.setFont(f)
        p.setPen(pal.al)
        p.drawText(rect, int(Qt.AlignHCenter | Qt.AlignVCenter), self.medalla)

    def _vis_sol(self, p, L, tl, a, dx):
        """Diapositiva 2: un destello que respira y cinco estrellas que se encienden en fila."""
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.0, 0.8))
        pulso = 0.5 + 0.5 * math.sin(self._tg * 1.2)
        p.setOpacity(a * r)
        I.brillo(p, cx, cy, 240 * fs, pal.ac, int(60 + 50 * pulso))
        p.setPen(Qt.NoPen)
        I.destello(p, cx, cy, 30 * fs * (1 + 0.12 * pulso) * 1.6, QColor(pal.oro))
        for k in range(5):
            rk = I.eo(I.tramo(tl, 0.3 + 0.1 * k, 0.5))
            p.setOpacity(a * rk)
            x = cx + (k - 2) * 56 * fs
            y = cy + 62 * fs
            I.estrella(p, x, y, 11 * fs * (0.8 + 0.2 * rk), 5 * fs * (0.8 + 0.2 * rk), QColor(pal.oro))
        p.setOpacity(a * r)

    def _vis_horizonte(self, p, L, tl, a, dx):
        """Diapositiva 4: tres destellos que crecen de izquierda a derecha, sobre una línea de luz."""
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.0, 0.6))
        p.setOpacity(a * r)
        p.setPen(I.lapiz(I.alfa(pal.ac, 110), 1.2 * fs))
        p.drawLine(QPointF(cx - 260 * fs, cy + 40 * fs), QPointF(cx + 260 * fs, cy + 40 * fs))
        p.setPen(Qt.NoPen)
        for k, sc in enumerate((0.6, 1.0, 1.5)):
            rk = I.eo(I.tramo(tl, 0.1 + 0.2 * k, 0.7))
            x = cx + (k - 1) * 150 * fs
            tam = 22 * fs * sc * (0.9 + 0.1 * math.sin(self._tg * 1.5 + k))
            p.setOpacity(a * rk)
            I.brillo(p, x, cy, 90 * fs * sc, pal.ac, int(60 * rk))
            I.destello(p, x, cy, tam, QColor(pal.oro))

    def _vis_grid(self, p, L, tl, a, dx):
        """Rejilla de «Tus exclusivas»: tarjetas de cristal dorado que entran escalonadas."""
        fs = L["fs"]
        pal = self._pal
        g = L["grid"]
        x0 = L["cx"] - L["col"] / 2 + dx
        y0 = L["y_abajo"]
        fm_tt, fm_td = QFontMetricsF(g["f_tt"]), QFontMetricsF(g["f_td"])
        cuerpo = I.mezcla(C["texto2"], "#FFFFFF", 0.55)
        for t in g["tarjetas"]:
            k = t["icono"]
            r = I.eo(I.tramo(tl, 0.15 + 0.08 * k, 0.7))
            x = x0 + t["x"]
            y = y0 + t["y"] + (1 - r) * 24 * fs
            p.setOpacity(a * r)
            rect = QRectF(x, y, t["w"], t["h"])
            I.cristal(p, rect, 18 * fs, a_relleno=26, a_borde=60)
            p.setPen(I.lapiz(I.alfa(pal.ac, 150), 1.0))           # filo dorado
            p.setBrush(I.alfa(pal.ac, 16))
            p.drawRoundedRect(rect, 18 * fs, 18 * fs)
            p.setBrush(Qt.NoBrush)
            _icono(p, x + 38 * fs, y + 34 * fs, 13 * fs, k, pal.al)
            tx = x + 70 * fs
            yy = y + 20 * fs
            p.setFont(g["f_tt"])
            p.setPen(QColor("#FFFFFF"))
            for lin in t["lin_t"]:
                p.drawText(QPointF(tx, yy + fm_tt.ascent()), " ".join(lin))
                yy += fm_tt.height()
            yy += 2 * fs
            p.setFont(g["f_td"])
            p.setPen(cuerpo)
            for lin in t["lin_d"]:
                p.drawText(QPointF(tx, yy + fm_td.ascent()), " ".join(lin))
                yy += fm_td.height() * 1.05

    def _vis_corazon(self, p, L, tl, a, dx):
        """Diapositiva 5: un corazón dorado que late."""
        fs = L["fs"]
        cx = L["cx"] + dx
        cy = L["y0"] + L["arriba"] / 2
        pal = self._pal
        r = I.eo(I.tramo(tl, 0.0, 0.7))
        latido = 0.5 + 0.5 * math.sin(self._tg * 2 * math.pi / 1.5)
        s = 84 * fs * (1 + 0.07 * latido) * (0.85 + 0.15 * r)
        p.setOpacity(a * r)
        I.brillo(p, cx, cy, 260 * fs, pal.ac, int(90 * (0.5 + 0.5 * latido)))
        g = QLinearGradient(cx, cy - s, cx, cy + s)
        g.setColorAt(0, I.mezcla(pal.al, "#FFFFFF", 0.25))
        g.setColorAt(1, pal.ac)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(_ruta_corazon(cx, cy, s))

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
        vis = self.diap[i].get("vis")
        if vis == "medalla":
            self._vis_medalla(p, L, tl, a, dx)
        elif vis == "sol":
            self._vis_sol(p, L, tl, a, dx)
        elif vis == "grid":
            self._vis_grid(p, L, tl, a, dx)
        elif vis == "horizonte":
            self._vis_horizonte(p, L, tl, a, dx)
        elif vis == "corazon":
            self._vis_corazon(p, L, tl, a, dx)
        elif vis == "demo":
            from .demos_presentacion import pintar_demo
            fs = L["fs"]
            ancho, alto = L["demo"]
            r = I.eo(I.tramo(tl, 0.15, 0.8))
            esc = 0.94 + 0.06 * r
            rect = QRectF(L["cx"] + dx - ancho * esc / 2, L["y_abajo"] + (1 - r) * 30 * fs, ancho * esc, alto * esc)
            p.save()
            p.setOpacity(a * r)
            pintar_demo(p, self.diap[i]["demo"], rect, tl, fs, self._pal, self._cache_demos)
            p.restore()
        self._pintar_textos(p, L, tl, a, dx)
        p.restore()

    # ================================================================ fondo y pintura

    def _pintar_fondo(self, p):
        """Aurora dorada: degradado ámbar oscuro, luces difusas que respiran y viñeta."""
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
        base.setColorAt(0, I.mezcla(pal.fondo, pal.ac, 0.20))
        base.setColorAt(0.55, I.mezcla(pal.fondo, pal.ac, 0.07))
        base.setColorAt(1, I.mezcla(pal.fondo, "#000000", 0.5))
        q.fillRect(img.rect(), base)
        q.setCompositionMode(QPainter.CompositionMode_Plus)
        matices = (0, -10, -22, -6, -32)          # solo hacia ámbar y naranja: nada de verdes
        for k in range(5):
            fx, fy = 0.07 + 0.03 * k, 0.06 + 0.025 * k
            cx = bw * (0.5 + 0.42 * math.sin(tg * fx * 2.2 + k * 1.9))
            cy = bh * (0.5 + 0.36 * math.cos(tg * fy * 2.4 + k * 2.7))
            resp = 0.5 + 0.5 * math.sin(tg * 0.9 + k * 1.3)          # la luz respira
            rad = max(bw, bh) * (0.38 + 0.10 * resp)
            col = I.tono(pal.ac, matices[k], 0.7, 0.9)
            g = QRadialGradient(QPointF(cx, cy), rad)
            g.setColorAt(0, I.alfa(col, 44 + 32 * resp))
            g.setColorAt(0.55, I.alfa(col, 16 + 12 * resp))
            g.setColorAt(1, I.alfa(col, 0))
            q.setPen(Qt.NoPen)
            q.setBrush(g)
            q.drawEllipse(QPointF(cx, cy), rad, rad)
        q.setCompositionMode(QPainter.CompositionMode_SourceOver)
        vg = QRadialGradient(QPointF(bw / 2, bh * 0.48), max(bw, bh) * 0.8)
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(0.62, QColor(0, 0, 0, 40))
        vg.setColorAt(1.0, QColor(0, 0, 0, 185))
        q.setBrush(vg)
        q.drawRect(img.rect())
        q.end()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(0, 0, w, h), img)
        # polvo dorado que flota despacio
        for k in range(40):
            sp = 6 + 14 * I.azar(k, 1)
            y = h - ((tg * sp + I.azar(k, 2) * h * 1.2) % (h * 1.1)) + h * 0.05
            x = w * I.azar(k, 3) + 12 * math.sin(tg * 0.5 + k)
            tw = 0.5 + 0.5 * math.sin(tg * (1 + I.azar(k, 4)) + k)
            r = (0.8 + 1.8 * I.azar(k, 5)) * fs
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 214, 120, int(80 * tw * (0.4 + I.azar(k, 6)))))
            p.drawEllipse(QPointF(x, y), r, r)

    def _pintar_particulas(self, p):
        fs = self._escala()
        g = 520 * fs
        vivas = []
        for q in self._particulas:
            t = self._tg - q["t0"]
            if t > 1.9:
                continue
            vivas.append(q)
            k = (1 - math.exp(-2.4 * t)) / 2.4
            x = q["x"] + q["vx"] * k
            y = q["y"] + q["vy"] * k + 0.35 * 0.5 * g * t * t
            col = QColor(q["col"])
            col.setAlpha(int(255 * (1 - t / 1.9)))
            p.setPen(Qt.NoPen)
            p.setBrush(col)
            p.drawEllipse(QPointF(x, y), q["r"], q["r"])
        self._particulas = vivas

    def _pintar_marco(self, p):
        """Puntos de progreso dorados."""
        w = self.width()
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
                col = I.mezcla(pal.oro, pal.al, 0.2)
                col.setAlpha(int(70 + 185 * peso))
            else:
                col = QColor(255, 226, 150, 120 if k < self._pos_puntos else 62)
            p.setBrush(col)
            p.drawRoundedRect(r, base_w / 2, base_w / 2)
            x += anchos[k] + sep

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
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


# ================================================================ cuándo sale

def _donador_de_verdad(ctx):
    premium = getattr(ctx, "premium", None)
    return premium is not None and bool(getattr(premium, "donador_de_verdad", False))


def _nombre(ctx):
    cuenta = getattr(ctx, "cuenta", None) or {}
    return str(cuenta.get("nombre") or "").strip()


def _fundador(ctx):
    return getattr(getattr(ctx, "premium", None), "tipo", None) == "fundador"


def _presentacion_100_abierta(ventana):
    """True si «Somos 100» está visible como hija de la ventana (ahora mismo en pantalla)."""
    try:
        return any(d.isVisible() for d in ventana.findChildren(Presentacion100))
    except RuntimeError:
        return False


def _despues(ventana, ms):
    """Vuelve a intentar revisar_donador más tarde (sin romper si la ventana ya no existe)."""
    def _correr():
        try:
            revisar_donador(ventana)
        except RuntimeError:
            pass
    QTimer.singleShot(ms, _correr)


def _abrir(ventana, ctx):
    try:
        dlg = PresentacionDonadores(ventana, ctx=ctx, nombre=_nombre(ctx), fundador=_fundador(ctx),
                                    navegar=getattr(ventana, "navegar", None))
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.open()
        return dlg
    except RuntimeError:          # la ventana ya no existe
        return None


def revisar_donador(ventana):
    """Unos 8 s después de arrancar: si es donador o fundador DE VERDAD y aún no lo vio, lo marca como
    visto y abre la presentación. Si «Somos 100» está en pantalla, espera a que se cierre. Sin
    donación de verdad (prueba gratuita) no hace nada y no marca nada."""
    ajustes = getattr(ventana, "ajustes", None)
    if ajustes is None or ajustes.get(CLAVE_VISTA):
        return None
    ctx = getattr(ventana, "ctx", None)
    if not _donador_de_verdad(ctx):
        return None
    if _presentacion_100_abierta(ventana):
        _despues(ventana, 2000)
        return None
    if getattr(ventana, "en_completa", False) or getattr(ventana, "_saliendo", False):
        _despues(ventana, 20000)
        return None
    ajustes[CLAVE_VISTA] = True
    ajustes.guardar()
    return _abrir(ventana, ctx)
