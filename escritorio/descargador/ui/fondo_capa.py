# -*- coding: utf-8 -*-
"""La capa de «Fondo de Caudal»: se pinta detrás de todo el contenido de la ventana.

Color base de la app + la imagen «cubriendo» todo el espacio con poca opacidad (y, si se
pide, desenfocada) + una viñeta que oscurece los bordes y la parte de abajo + un toque
muy suave del color de acento. La imagen ya escalada y desenfocada se guarda en una caché:
al pintar solo se compone, y al cambiar el tamaño se re-escala una vez, con una pausa.
"""

import math
import time

from PySide6.QtCore import QElapsedTimer, QEvent, QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget)

from .estilos import C

_PATRONES = {}


def pixmap_patron(ruta):
    """El dibujo del personaje del fondo (descargador/fondos/<clave>.png). Se carga una vez."""
    if ruta is None:
        return None
    clave = str(ruta)
    if clave not in _PATRONES:
        pm = QPixmap(clave)
        _PATRONES[clave] = None if pm.isNull() else pm
    return _PATRONES[clave]


def _con_alfa(color, alfa):
    c = QColor(color)
    c.setAlpha(max(0, min(255, int(alfa))))
    return c


def escena_cubierta(img, tam, desenfoque):
    """La imagen «cubriendo» `tam` (recorte centrado) y, si se pide, desenfocada (0–20).
    El desenfoque se hace sobre una copia a mitad de tamaño y luego se agranda: barato."""
    w, h = max(1, tam.width()), max(1, tam.height())
    if desenfoque <= 0:
        c = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return QPixmap.fromImage(c.copy((c.width() - w) // 2, (c.height() - h) // 2, w, h))
    hw, hh = max(2, w // 2), max(2, h // 2)
    radio = desenfoque * 1.1
    margen = int(radio * 2) + 2
    c = img.scaled(hw, hh, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    c = c.copy((c.width() - hw) // 2, (c.height() - hh) // 2, hw, hh)
    # se estira un poco hacia los bordes para que el desenfoque no deje orillas claras
    grande = c.scaled(hw + 2 * margen, hh + 2 * margen, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    escena = QGraphicsScene()
    item = QGraphicsPixmapItem(QPixmap.fromImage(grande))
    efecto = QGraphicsBlurEffect()
    efecto.setBlurRadius(radio)
    efecto.setBlurHints(QGraphicsBlurEffect.QualityHint)
    item.setGraphicsEffect(efecto)
    escena.addItem(item)
    salida = QImage(grande.size(), QImage.Format_ARGB32_Premultiplied)
    salida.fill(Qt.transparent)
    p = QPainter(salida)
    escena.render(p, QRectF(salida.rect()), QRectF(salida.rect()))
    p.end()
    corte = salida.copy(margen, margen, hw, hh).scaled(w, h, Qt.IgnoreAspectRatio,
                                                       Qt.SmoothTransformation)
    return QPixmap.fromImage(corte)


class Renderizador:
    """Pinta el fondo en cualquier rectángulo (la ventana o la vista previa)."""

    def __init__(self):
        self._pm = None
        self._clave = None
        self._compuesto = None
        self._clave_compuesto = None

    def compuesto(self, ancho, alto, dpr, img, serie, visible, desenfoque):
        """El fondo entero (color + imagen + velos + viñeta + acento) ya compuesto en un QPixmap.
        Se rehace solo si cambia el tamaño, la imagen, sus ajustes o los colores: la capa de la
        ventana se repinta cada vez que algo translúcido se mueve encima, y así cada repintado
        es copiar un trozo de imagen en vez de seis degradados."""
        hay = img is not None and not img.isNull()
        clave = (int(ancho), int(alto), float(dpr), serie if hay else None, visible, desenfoque,
                 C["fondo"], C["panel"], C["acento"])
        if clave != self._clave_compuesto or self._compuesto is None:
            pm = QPixmap(max(1, int(ancho * dpr)), max(1, int(alto * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.transparent)
            q = QPainter(pm)
            self.pintar(q, QRectF(0, 0, ancho, alto), img, serie, visible, desenfoque)
            q.end()
            self._compuesto, self._clave_compuesto = pm, clave
        return self._compuesto

    def _escena(self, img, serie, rect, desenfoque, estirar):
        tam = QSize(max(1, int(rect.width())), max(1, int(rect.height())))
        clave = (serie, tam.width(), tam.height(), desenfoque)
        if clave != self._clave:
            if estirar and self._pm is not None:
                return self._pm                 # mientras se arrastra el borde: se estira la anterior
            self._pm = escena_cubierta(img, tam, desenfoque)
            self._clave = clave
        return self._pm

    def pintar(self, p, rect, img, serie, visible, desenfoque, estirar=False, patron=None):
        """`visible` es el porcentaje (5–60) de imagen que se deja ver. `patron` (QPixmap): el personaje del
        fondo elegido; se ve chico, a un costado, y si además hay imagen de «Fondo de Caudal» va encima de
        ella en su esquina (la imagen no se tapa)."""
        rect = QRectF(rect)
        w, h = rect.width(), rect.height()
        base = QColor(C["fondo"])
        p.save()
        p.setClipRect(rect, Qt.IntersectClip)
        p.translate(rect.topLeft())
        r = QRectF(0, 0, w, h)
        # el color de la app, con un cambio de tono casi imperceptible de arriba abajo
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(C["panel"]))
        g.setColorAt(1, base)
        p.fillRect(r, g)
        v = max(0.0, min(1.0, visible / 100.0))
        hay_imagen = img is not None and not img.isNull()
        if not hay_imagen:
            v = 0.0
        if hay_imagen:
            pm = self._escena(img, serie, rect, desenfoque, estirar)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.setOpacity(v)
            p.drawPixmap(r.toRect(), pm)
            p.setOpacity(1.0)
        # un velo que crece con la imagen: cuanto más se ve, más se cuida el texto
        p.fillRect(r, _con_alfa(base, 255 * min(0.3, v * 0.30)))
        # viñeta: oscurece hacia los bordes y hacia abajo (profundidad y lectura)
        d = max(w, h)
        rad = QRadialGradient(w * 0.5, h * 0.42, d * 0.80)
        rad.setColorAt(0.0, _con_alfa(base, 0))
        rad.setColorAt(0.55, _con_alfa(base, 0))
        rad.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, rad)
        baja = QLinearGradient(0, h * 0.50, 0, h)
        baja.setColorAt(0.0, _con_alfa(base, 0))
        baja.setColorAt(1.0, _con_alfa(base, 150))
        p.fillRect(r, baja)
        # un soplo del color de acento desde la esquina de arriba
        ac = QColor(C["acento"])
        brillo = QRadialGradient(w * 0.88, -h * 0.05, d * 0.70)
        brillo.setColorAt(0.0, _con_alfa(ac, 30))
        brillo.setColorAt(1.0, _con_alfa(ac, 0))
        p.fillRect(r, brillo)
        lado = QLinearGradient(0, 0, w, h)
        lado.setColorAt(0.0, _con_alfa(ac, 12))
        lado.setColorAt(0.6, _con_alfa(ac, 0))
        p.fillRect(r, lado)
        p.restore()


class PersonajeEsquina(QWidget):
    """El personaje del fondo elegido, sentado sobre el borde de arriba de la barra del reproductor, en
    la esquina derecha. Siempre se ve entero (los paneles no lo tapan) y sigue a la barra (tamaño de la
    ventana, pantalla completa). Convive con la imagen de fondo.

    Con el ratón, sin ir a ningún ajuste: la rueda encima de él cambia su tamaño; arrastrarlo con el
    botón izquierdo lo lleva a cualquier parte de la ventana (nunca se sale); doble clic lo devuelve a
    su esquina. Tamaño y lugar se recuerdan en los ajustes (el lugar como fracción 0..1 de lo que cabe
    en la ventana, así se respeta al cambiar el tamaño de la ventana).

    Mientras suena la música baila: rebote, vaivén y un poco de squash/stretch con los pies fijos. El
    reloj solo corre mientras suena; en pausa queda quieto."""

    ALTO = 124         # tamaño de partida (el dibujo mide 96 px: se agranda sin suavizar, nítido)
    MINIMO, MAXIMO = 64, 280
    MARGEN = 22        # espacio para el halo
    CLAVE = "tamano_personaje"
    CLAVE_X, CLAVE_Y = "personaje_x", "personaje_y"
    CLAVE_BAILE = "personaje_baila"
    UMBRAL_ARRASTRE = 2        # px que hay que mover antes de que un clic cuente como arrastre
    CUADRO_MS = 33             # ~30 cuadros por segundo
    FUNDIDO_S = 0.35           # lo que tarda en entrar y salir del baile (nunca corta de golpe)
    # baile suave, como las mascotas del reproductor (todo en fracciones del alto del personaje)
    SALTO = 0.028              # lo que sube entre tiempo y tiempo
    MECE = 0.012               # desplazamiento lateral
    GIRO = 1.7                 # grados, como mucho
    ESTIRA = 0.012             # estiramiento casi imperceptible
    BPM_BASE = 96.0            # si la canción aún no tiene su ritmo analizado
    BPM_MAXIMO = 130.0         # por encima se baila a la mitad

    def __init__(self, padre, barra=None, reproductor=None):
        super().__init__(padre)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Arrástralo para moverlo, gira la rueda para cambiar su tamaño; "
                        "doble clic lo devuelve a su esquina")
        self.barra = barra
        self.pm = None
        self._arrastre = None            # (punto global de inicio, posición al empezar, ¿ya se movió?)
        self._frac = (-1.0, -1.0)        # lugar elegido como fracción 0..1; -1 = su esquina de siempre
        self._amp = 0.0                  # 0..1: cuánto está bailando (sube y baja con el fundido)
        self._sonando = False
        self._quiere = False
        self._ref = (time.monotonic(), 0.0)   # (reloj, posición de la canción) para interpolar el tiempo
        self._ritmo = (self.BPM_BASE, 0.0)    # (bpm, segundo del primer tiempo) de la canción que suena
        self._reloj = QElapsedTimer()
        self._t_baile = QTimer(self)
        self._t_baile.setInterval(self.CUADRO_MS)
        self._t_baile.timeout.connect(self._paso_baile)
        self._t_colocar = QTimer(self)
        self._t_colocar.setSingleShot(True)
        self._t_colocar.setInterval(0)
        self._t_colocar.timeout.connect(self.colocar)
        self._t_guardar = QTimer(self)
        self._t_guardar.setSingleShot(True)
        self._t_guardar.setInterval(500)
        self._t_guardar.timeout.connect(self._guardar)
        if barra is not None:
            barra.installEventFilter(self)
        self.alto = self._leer_alto()
        self._frac = self._leer_frac()
        self.reproductor = reproductor
        if reproductor is not None:
            reproductor.estado_cambio.connect(self._al_estado)
            for nombre, ranura in (("posicion_cambio", self._al_posicion), ("pista_cambio", self._al_pista)):
                senal = getattr(reproductor, nombre, None)
                if senal is not None:
                    senal.connect(ranura)
            self._sonando = getattr(reproductor, "estado", "") == "sonando"
            self._tomar_posicion()
            self._leer_ritmo()
        from ..cumpleanos import ESTADO as _cumple
        _cumple.cambiado.connect(self.update)      # el gorrito de cumpleaños aparece / se va solo
        self.hide()

    # ---------------------------------------------------------------- ajustes
    def _ajustes(self):
        return getattr(self.parentWidget(), "ajustes", None)

    def _leer_alto(self):
        try:
            v = int((self._ajustes() or {})[self.CLAVE] or self.ALTO)
        except (TypeError, ValueError, KeyError):
            v = self.ALTO
        return max(self.MINIMO, min(self.MAXIMO, v))

    def _leer_frac(self):
        a = self._ajustes() or {}
        try:
            fx, fy = float(a[self.CLAVE_X]), float(a[self.CLAVE_Y])
        except (TypeError, ValueError, KeyError):
            return (-1.0, -1.0)
        if not (0.0 <= fx <= 1.0 and 0.0 <= fy <= 1.0):       # -1 (o basura) = en su esquina
            return (-1.0, -1.0)
        return (fx, fy)

    @property
    def en_la_esquina(self):
        return self._frac[0] < 0

    def _guardar(self):
        a = self._ajustes()
        if a is not None:
            a[self.CLAVE] = self.alto
            a[self.CLAVE_X], a[self.CLAVE_Y] = self._frac
            try:
                a.guardar()
            except Exception:  # noqa: BLE001
                pass

    def baile_permitido(self):
        try:
            return bool((self._ajustes() or {})[self.CLAVE_BAILE])
        except (TypeError, KeyError):
            return True

    # ---------------------------------------------------------------- medidas
    def _margenes(self, alto=None):
        """(lateral, arriba, abajo): dejan sitio al halo y a lo que se sale del dibujo al bailar."""
        h, m = alto or self.alto, self.MARGEN
        return m + int(h * 0.05), m + int(h * 0.08), 6

    def _tamano(self, alto=None):
        h = alto or self.alto
        lado, arriba, abajo = self._margenes(h)
        w = int(self.pm.width() * h / max(1, self.pm.height()))
        return w + 2 * lado, h + arriba + abajo

    def _acotar(self, x, y, ancho, alto):
        padre = self.parentWidget()
        return (max(0, min(int(x), max(0, padre.width() - ancho))),
                max(0, min(int(y), max(0, padre.height() - alto))))

    def _frac_de(self, x, y, ancho, alto):
        padre = self.parentWidget()
        libre_x, libre_y = padre.width() - ancho, padre.height() - alto
        return (max(0.0, min(1.0, x / libre_x)) if libre_x > 0 else 0.0,
                max(0.0, min(1.0, y / libre_y)) if libre_y > 0 else 0.0)

    # ---------------------------------------------------------------- tamaño
    def poner_alto(self, alto):
        alto = max(self.MINIMO, min(self.MAXIMO, int(alto)))
        if alto == self.alto:
            return
        if not self.en_la_esquina and self.pm is not None and self.parentWidget() is not None:
            # en su sitio elegido, crece o se achica con la esquina de abajo a la derecha quieta
            g = self.geometry()
            ancho, alto_w = self._tamano(alto)
            x, y = self._acotar(g.right() + 1 - ancho, g.bottom() + 1 - alto_w, ancho, alto_w)
            self._frac = self._frac_de(x, y, ancho, alto_w)
        self.alto = alto
        self.colocar()
        self._t_guardar.start()

    def wheelEvent(self, e):
        paso = 1 if e.angleDelta().y() > 0 else -1
        self.poner_alto(self.alto + paso * 10)
        e.accept()

    # ---------------------------------------------------------------- mover con el ratón
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = [e.globalPosition(), self.pos(), False]
            e.accept()

    def mouseMoveEvent(self, e):
        if self._arrastre is None:
            return
        inicio, pos0, movido = self._arrastre
        d = e.globalPosition() - inicio
        if not movido:
            if abs(d.x()) < self.UMBRAL_ARRASTRE and abs(d.y()) < self.UMBRAL_ARRASTRE:
                return
            self._arrastre[2] = True
            self.setCursor(Qt.ClosedHandCursor)
        x, y = self._acotar(pos0.x() + d.x(), pos0.y() + d.y(), self.width(), self.height())
        self._frac = self._frac_de(x, y, self.width(), self.height())
        self.move(x, y)
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._arrastre is not None:
            movido = self._arrastre[2]
            self._arrastre = None
            self.setCursor(Qt.OpenHandCursor)
            if movido:
                self._guardar()
            e.accept()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = None
            self.volver_a_la_esquina()
            e.accept()

    def volver_a_la_esquina(self):
        """Lo devuelve a su esquina de siempre, sobre la barra (y lo recuerda)."""
        self._frac = (-1.0, -1.0)
        self.colocar()
        self._guardar()

    def eventFilter(self, obj, e):
        if obj is self.barra and e.type() in (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide):
            self._t_colocar.start()      # un reloj propio: si el personaje se destruye, no queda nada pendiente
        return False

    def colocar(self):
        from .estilos import patron_actual
        self.pm = pixmap_patron(patron_actual())
        padre = self.parentWidget()
        barra = self.barra
        if self.pm is None or padre is None or barra is None or not barra.isVisible():
            self.hide()
            self._actualizar_baile()
            return
        h = self.alto
        ancho, alto_w = self._tamano()
        self.resize(ancho, alto_w)
        lado, arriba, _abajo = self._margenes()
        if self.en_la_esquina:
            borde = barra.mapTo(padre, QPoint(0, 0)).y()
            # los pies apoyados en el borde de arriba de la barra, en la esquina derecha
            x = min(padre.width() - ancho, padre.width() - ancho - 8 + (lado - self.MARGEN))
            y = borde - h - arriba + 4
        else:
            fx, fy = self._frac
            x = fx * max(0, padre.width() - ancho)
            y = fy * max(0, padre.height() - alto_w)
            x, y = self._acotar(x, y, ancho, alto_w)
        self.move(int(x), int(y))
        self.show()
        self.raise_()
        self.update()
        self._actualizar_baile()

    # ---------------------------------------------------------------- baile
    def _al_estado(self, estado):
        self._tomar_posicion()
        self._sonando = estado == "sonando"
        if self._sonando:
            self._leer_ritmo()
        self._actualizar_baile()

    def _al_posicion(self, segundos):
        self._ref = (time.monotonic(), float(segundos))

    def _al_pista(self, *_a):
        self._leer_ritmo()

    def _tomar_posicion(self):
        pos = getattr(self.reproductor, "_posicion", None)
        if isinstance(pos, (int, float)):
            self._ref = (time.monotonic(), float(pos))

    def _leer_ritmo(self):
        """El tempo y el primer tiempo salen del análisis que la app ya guardó para la canción (el del
        mezclador DJ): aquí NO se analiza audio. Sin él, 96 bpm."""
        bpm, fase = self.BPM_BASE, 0.0
        r = self.reproductor
        try:
            an = r._analisis_de(r.actual) if r is not None and r.actual is not None else None
            if an and float(an.get("bpm") or 0) > 0:
                bpm, fase = float(an["bpm"]), float(an.get("fase") or 0.0)
        except Exception:  # noqa: BLE001 - sin análisis, el ritmo de siempre
            pass
        self._ritmo = (bpm, fase)

    def _posicion_cancion(self):
        """Dónde va la canción ahora, interpolando entre aviso y aviso del reproductor (y quieta si no suena)."""
        t0, p0 = self._ref
        if not self._sonando:
            return p0
        vel = float(getattr(self.reproductor, "velocidad", 1.0) or 1.0)
        return p0 + (time.monotonic() - t0) * vel

    def _periodo(self):
        """Segundos por tiempo bailado: un tempo mayor de 130 bpm se baila a la mitad."""
        bpm = self._ritmo[0]
        while bpm > self.BPM_MAXIMO:
            bpm /= 2
        return 60.0 / max(1.0, bpm)

    def _actualizar_baile(self):
        """El reloj corre mientras suena la música, está permitido y el personaje se ve; y un rato más
        mientras el fundido de salida lo deja quieto."""
        debe = self._sonando and self.baile_permitido() and self.isVisible()
        self._quiere = debe
        if debe or self._amp > 0:
            if not self._t_baile.isActive():
                self._reloj.start()
                self._t_baile.start()
        elif self._t_baile.isActive():
            self._t_baile.stop()

    def actualizar_baile(self):
        """Para cuando cambia el ajuste «personaje_baila»."""
        self._actualizar_baile()

    def _paso_baile(self):
        dt = self._reloj.restart() / 1000.0
        paso = dt / self.FUNDIDO_S
        self._amp = min(1.0, self._amp + paso) if self._quiere else max(0.0, self._amp - paso)
        if self._amp <= 0 and not self._quiere:
            self._t_baile.stop()
        self.update()

    def pose(self):
        """(subida 0..1, desplazamiento en fracción del alto, giro en grados, escala_x, escala_y).

        Cae en los tiempos de la canción: abajo justo EN el tiempo y arriba entre tiempos (sube = sin(pi·f)
        con f la fracción del tiempo); se mece de lado cada 2 tiempos. Todo se multiplica por el fundido."""
        if self._amp <= 0:
            return 0.0, 0.0, 0.0, 1.0, 1.0
        a = self._amp * self._amp * (3 - 2 * self._amp)             # fundido suave (smoothstep)
        bpm, fase = self._ritmo
        periodo = self._periodo()
        tiempos = (self._posicion_cancion() - fase) / periodo
        f = tiempos % 1.0
        subida = math.sin(math.pi * f)
        lado = math.sin(math.pi * (tiempos % 2.0))                  # un vaivén completo cada 2 tiempos
        k = subida * 2 - 1
        return (subida * a, self.MECE * lado * a, self.GIRO * lado * a,
                1 - 0.5 * self.ESTIRA * k * a, 1 + self.ESTIRA * k * a)

    def paintEvent(self, _e):
        if self.pm is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        h = self.alto
        lado, y, _abajo = self._margenes()
        w = self.width() - 2 * lado
        x = lado
        subida, desp, giro, sx, sy = self.pose()
        p.setPen(Qt.NoPen)
        # halo suave del color del tema detrás: se nota sobre cualquier fondo, también sobre una foto
        ac = QColor(C["acento"])
        cx, cy = self.width() / 2, y + h * 0.58
        radio = min(self.width() / 2, self.height() - cy, cy) - 1    # se apaga antes de tocar el borde
        halo = QRadialGradient(cx, cy, radio)
        halo.setColorAt(0.0, _con_alfa(ac, 80))
        halo.setColorAt(0.5, _con_alfa(ac, 30))
        halo.setColorAt(1.0, _con_alfa(ac, 0))
        p.setBrush(halo)
        p.drawEllipse(QRectF(cx - radio, cy - radio, radio * 2, radio * 2))
        # sombra bajo los pies: lo «posa» sobre la barra (se encoge un poco cuando salta)
        enc = 1 - 0.08 * subida
        sombra = QRadialGradient(x + w / 2, y + h - 1, w * 0.48 * enc)
        sombra.setColorAt(0.0, _con_alfa("#000000", int(150 - 20 * subida)))
        sombra.setColorAt(1.0, _con_alfa("#000000", 0))
        p.setBrush(sombra)
        p.drawEllipse(QRectF(x + w * (0.5 - 0.46 * enc), y + h - 8, w * 0.92 * enc, 15))
        # el dibujo baila desde los pies (el punto de apoyo no se mueve de la barra, salvo el salto)
        p.save()
        p.translate(x + w / 2 + desp * h, y + h - subida * h * self.SALTO)
        p.rotate(giro)
        p.scale(sx, sy)
        p.translate(-(x + w / 2), -(y + h))
        # agrandar pixel art: sin suavizado (nítido); se suaviza si hay que achicarlo o si gira
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.pm.height() > h or self._amp > 0)
        p.drawPixmap(QRectF(x, y, w, h), self.pm, QRectF(self.pm.rect()))
        from ..cumpleanos import ESTADO as _cumple
        if _cumple.es_mio_hoy:
            # cumpleaños: gorrito de fiesta sobre el personaje (baila con él)
            from .cumpleanos_ui import pintar_gorro
            pintar_gorro(p, x + w * 0.52, y + h * 0.1, w * 0.3)
        p.restore()
        p.end()


class CapaFondo(QWidget):
    """Hija de la ventana, siempre al fondo; no recibe clics."""

    def __init__(self, gestor, padre):
        super().__init__(padre)
        self.gestor = gestor
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.rend = Renderizador()
        self._redimensionando = False
        self._t = QTimer(self)
        self._t.setSingleShot(True)
        self._t.setInterval(140)
        self._t.timeout.connect(self._fin_redimension)
        gestor.cambiado.connect(self._al_cambiar)

    def _al_cambiar(self, _a=None):
        self.update()

    def _fin_redimension(self):
        self._redimensionando = False
        self.update()

    def resizeEvent(self, e):
        self._redimensionando = True
        self._t.start()
        super().resizeEvent(e)

    def paintEvent(self, e):
        g = self.gestor
        p = QPainter(self)
        if self._redimensionando:
            # mientras se arrastra el borde: se pinta directo (componer en cada paso sería peor)
            self.rend.pintar(p, QRectF(self.rect()), g.imagen, g.serie, g.visible, g.desenfoque,
                             estirar=True)
        else:
            dpr = self.devicePixelRatioF()
            pm = self.rend.compuesto(self.width(), self.height(), dpr, g.imagen, g.serie,
                                     g.visible, g.desenfoque)
            # el pintor ya viene recortado a la zona que se repinta: solo se copia ese trozo
            p.drawPixmap(0, 0, pm)
        p.end()
