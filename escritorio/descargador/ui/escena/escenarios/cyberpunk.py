# -*- coding: utf-8 -*-
"""Escenario «Cyberpunk»: ciudad nocturna bajo lluvia fina, con perspectiva atmosférica.

Lo fijo (cielo, luna tras la bruma, dirigible, cuatro planos de edificios con sus ventanas, letreros pegados a
las fachadas, calle mojada, grano y viñeta) se pinta una sola vez y queda en caché. Lo que se mueve (lluvia en
paralaje, salpicaduras, letreros que parpadean, coches voladores, reflejos en el suelo y ondas de la música)
usa sprites y datos ya preparados, así que cada cuadro cuesta poco.
"""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap, QPolygonF, QRadialGradient)

from .base import EscenarioBase, con_alfa, mezclar

SUELO = 0.66                                  # fracción del alto donde empieza la calle (la acera queda limpia)
BRUMA = QColor("#2A1840")
ROSA = QColor("#FF2A6D")
MORADO = QColor("#3A1F6B")
ROJO = QColor(255, 40, 70)
AZUL = QColor(40, 140, 255)
LLUVIA = QColor("#BFE6FF")
BLANCO = QColor("#FFFFFF")
OSCURO = QColor("#0A0712")
VENTANA_APAGADA = QColor("#1A1426")
COLOR_VENTANA = {"calida": QColor("#FFC46B"), "fria": QColor("#6BE4FF"), "rosa": QColor("#FF5FA2")}
COLOR_LETRERO = {"magenta": QColor("#FF2A6D"), "ambar": QColor("#FFB000")}     # "cian" usa el acento

# Planos de edificios, del más lejano al más cercano:
# (color base, mezcla con la bruma, ancho, alto, paso x, paso y, ancho de ventana, alto de ventana)
# Anchos, altos, pasos y ventanas son fracciones de w y h; los altos se miden desde la calle.
# Lejanos: ventanas de 2-3 px. Cercanos: ventanas de 0.004w x 0.009h con separación 0.003w.
PLANOS = (
    ("#1A1030", 0.70, (0.035, 0.065), (0.25, 0.70), 0.0030, 0.0060, 0.0014, 0.0028),
    ("#120B22", 0.45, (0.05, 0.09), (0.18, 0.55), 0.0040, 0.0080, 0.0015, 0.0031),
    ("#0B0614", 0.20, (0.07, 0.13), (0.12, 0.40), 0.0070, 0.0120, 0.0040, 0.0090),
    ("#050309", 0.00, (0.12, 0.20), (0.08, 0.26), 0.0070, 0.0120, 0.0040, 0.0090),
)
ESCALA_PLANO = {0: 0.5, 1: 0.6, 2: 0.8, 3: 1.0}
# Altura (fracción de h) de la base de los letreros de cada plano.
ALTURA_LETREROS = {1: 0.50, 2: 0.56, 3: 0.58}

# Bandas de niebla entre planos: (y inicial, y final, color). Las bajas son magenta, las altas moradas.
BANDAS_NIEBLA = {
    0: (0.28, 0.46, mezclar(MORADO, ROSA, 0.5)),
    1: (0.44, 0.62, mezclar(MORADO, ROSA, 0.25)),
    2: (0.58, 0.78, ROSA),
}

# Letreros: (plano, x fraccionario objetivo, tipo, texto, color, modo).
# Modo: "fijo" se pinta en lo estático; "pulso", "parpadeo" y "apagado" se animan.
# Cada uno se pega a una fachada concreta; si no cabe sin solapar, no se pone.
LETREROS = (
    (1, 0.20, "barra", "酒", "cian", "fijo"),
    (1, 0.36, "barra", "夜", "cian", "fijo"),
    (1, 0.56, "caja", "OPEN", "ambar", "fijo"),
    (1, 0.86, "caja", "ラーメン", "magenta", "fijo"),
    (2, 0.06, "caja", "HOTEL", "magenta", "fijo"),
    (2, 0.34, "barra", "夜", "ambar", "fijo"),
    (2, 0.48, "caja", "OPEN", "magenta", "fijo"),
    (2, 0.64, "caja", "ラーメン", "cian", "fijo"),
    (2, 0.92, "barra", "酒", "magenta", "fijo"),
    (3, 0.12, "barra", "酒", "cian", "pulso"),
    (3, 0.42, "caja", "HOTEL", "magenta", "parpadeo"),
    (3, 0.70, "caja", "OPEN", "ambar", "apagado"),
    (3, 0.90, "barra", "夜", "cian", "parpadeo"),
)


def _azar(k, i, j):
    """Número en 0..1 fijo para (k, i, j): las salpicaduras no dependen del generador aleatorio."""
    x = math.sin(k * 12.9898 + i * 78.233 + j * 37.719) * 43758.5453
    return x - math.floor(x)


def _solapa(a, b, hx=0.0, vy=0.0):
    """Si dos rectángulos (x0, y0, x1, y1) se solapan, dejando un hueco hx (horizontal) y vy (vertical)."""
    return a[0] < b[2] + hx and a[2] + hx > b[0] and a[1] < b[3] + vy and a[3] + vy > b[1]


def _resplandor(pp, trazo, cc):
    """Neón de un trazo: halo ancho, halo medio y núcleo blanco-cian. Halo con aberración cromática leve."""
    pp.setBrush(Qt.NoBrush)
    for dx, col in ((-1, ROJO), (1, AZUL)):
        pp.save()
        pp.translate(dx, 0)
        pp.setPen(QPen(con_alfa(col, 30), 14, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        pp.drawPath(trazo)
        pp.restore()
    pp.setPen(QPen(con_alfa(cc, 35), 14, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pp.drawPath(trazo)
    pp.setPen(QPen(con_alfa(cc, 90), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pp.drawPath(trazo)
    pp.setPen(QPen(con_alfa(mezclar(cc, QColor("white"), 0.6), 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    pp.drawPath(trazo)


class EscenarioCyberpunk(EscenarioBase):
    NOMBRE = "Cyberpunk"
    ACENTO = "#00F0FF"

    def preparar(self):
        # Todo lo aleatorio se genera en pintar_estatico con random.Random(23), así el dibujo es idéntico siempre.
        self._letreros = []     # dicts de cada letrero (sprite, posición, modo)
        self._geo = []          # por plano: lista de (x, y_techo, ancho) de cada edificio, en píxeles
        self._lluvia = []       # (x0, y0, velocidad, largo, alfa) en fracciones de h
        self._coches = []       # (fase, velocidad, y, sentido)

    # ------------------------------------------------------------ fijo (caché)

    def pintar_estatico(self, p, w, h):
        rnd = random.Random(23)
        acento = self.acento()
        self._letreros = []
        self._cielo(p, w, h, rnd)
        ultimo = len(PLANOS) - 1
        self._geo = [[] for _ in PLANOS]
        for idx, cfg in enumerate(PLANOS):
            self._edificios(p, w, h, rnd, idx, cfg, acento)
            if idx < ultimo:
                self._niebla(p, w, h, idx)
            if idx == 0:
                self._dirigible(p, w, h)     # detrás de los planos cercanos, delante de los lejanos
        self._colocar_letreros(p, w, h, rnd, acento)
        self._calle(p, w, h, rnd)

        # Lluvia y coches: fracciones, así que no dependen del tamaño.
        self._lluvia = []
        for _ in range(260):
            fac = 0.6 + 0.8 * rnd.random()          # las gotas cercanas son más rápidas y largas
            self._lluvia.append((rnd.random(), rnd.random(), rnd.uniform(900, 1400) / 1080 * fac,
                                 rnd.uniform(14, 30) / 1080 * fac, rnd.randint(30, 80)))
        self._coches = [
            {"fase": rnd.random(), "vel": rnd.uniform(0.008, 0.014), "y": rnd.uniform(0.10, 0.24),
             "dir": rnd.choice((-1, 1))}
            for _ in range(3)
        ]

        # Grano fino y viñeta.
        ruido = QPolygonF([QPointF(rnd.random() * w, rnd.random() * h) for _ in range(6000)])
        p.setPen(QPen(QColor(255, 255, 255, 8), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPoints(ruido)
        vineta = QRadialGradient(QPointF(w / 2, h / 2), math.hypot(w / 2, h / 2))
        vineta.setColorAt(0.0, QColor(0, 0, 0, 0))
        vineta.setColorAt(0.6, QColor(0, 0, 0, 0))
        vineta.setColorAt(1.0, QColor(0, 0, 0, 130))
        p.setPen(Qt.NoPen)
        p.fillRect(QRectF(0, 0, w, h), QBrush(vineta))

    def _cielo(self, p, w, h, rnd):
        suelo = SUELO * h
        cielo = QLinearGradient(0, 0, 0, suelo)
        cielo.setColorAt(0.0, QColor("#05030C"))
        cielo.setColorAt(0.4, QColor("#1B0B2E"))
        cielo.setColorAt(1.0, QColor("#3A1450"))
        p.fillRect(QRectF(0, 0, w, h), QBrush(cielo))

        for _ in range(140):
            x, y = rnd.random() * w, rnd.random() * 0.5 * h
            p.fillRect(QRectF(x, y, 1.2, 1.2), con_alfa(QColor("#E8DDFF"), rnd.randint(30, 120)))

        # Luna enorme, arriba a la derecha: degradado radial con la luz arriba-izquierda y cráteres tenues.
        cx, cy, r = 0.80 * w, 0.16 * h, 0.12 * h
        self.brillo(p, cx, cy, 0.45 * h, QColor("#D9C7FF"), 22)
        disco = QRadialGradient(QPointF(cx, cy), r, QPointF(cx - 0.35 * r, cy - 0.35 * r))
        disco.setColorAt(0.0, con_alfa(QColor("#F4EEFF"), 95))
        disco.setColorAt(0.7, con_alfa(QColor("#D9C7FF"), 70))
        disco.setColorAt(1.0, con_alfa(QColor("#B9A6E0"), 40))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(disco))
        p.drawEllipse(QPointF(cx, cy), r, r)
        for _ in range(6):
            ang = rnd.uniform(0.0, 2 * math.pi)
            dist = r * 0.75 * math.sqrt(rnd.random())
            rr = r * rnd.uniform(0.05, 0.14)
            p.setBrush(QBrush(con_alfa(QColor("#7D6AA3"), 35)))
            p.drawEllipse(QPointF(cx + dist * math.cos(ang), cy + dist * math.sin(ang)), rr, rr)

        # Franja de bruma delante de la parte baja de la luna.
        velo_bruma = QLinearGradient(0, 0.18 * h, 0, 0.40 * h)
        velo_bruma.setColorAt(0.0, con_alfa(BRUMA, 0))
        velo_bruma.setColorAt(0.5, con_alfa(BRUMA, 150))
        velo_bruma.setColorAt(1.0, con_alfa(BRUMA, 0))
        p.fillRect(QRectF(0, 0.18 * h, w, 0.22 * h), QBrush(velo_bruma))

    def _dirigible(self, p, w, h):
        """Dirigible lejano con una pantalla luminosa rosa."""
        ax, ay = 0.62 * w, 0.30 * h
        L, A = 0.075 * w, 0.022 * h
        cuerpo = QPainterPath()
        cuerpo.addEllipse(QRectF(ax - L / 2, ay - A / 2, L, A))
        aleta = QPolygonF([QPointF(ax + L * 0.38, ay), QPointF(ax + L * 0.52, ay - A * 0.9),
                           QPointF(ax + L * 0.52, ay + A * 0.2)])
        casco = mezclar(QColor("#2A2046"), BRUMA, 0.4)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(con_alfa(casco, 235)))
        p.drawPath(cuerpo)
        p.drawPolygon(aleta)
        p.fillRect(QRectF(ax - L * 0.12, ay + A * 0.35, L * 0.24, A * 0.45), QColor("#120A1E"))
        p.fillRect(QRectF(ax - L * 0.08, ay + A * 0.45, L * 0.16, A * 0.22), con_alfa(ROSA, 220))
        self.brillo(p, ax, ay + A * 0.56, L * 0.45, ROSA, 60)

    def _edificios(self, p, w, h, rnd, idx, cfg, acento):
        """Un plano de edificios: azotea escalonada, antenas, tanques, cornisas, rejilla de ventanas
        (con persianas) y bordes de neón en los planos cercanos. Guarda la geometría para colocar letreros."""
        color, bruma, (aw0, aw1), (ah0, ah1), pas_x, pas_y, ven_w, ven_h = cfg
        base = mezclar(QColor(color), BRUMA, bruma)
        suelo = SUELO * h
        arista = con_alfa(acento, 90)
        apagada = mezclar(VENTANA_APAGADA, BRUMA, bruma)
        tonos = [mezclar(COLOR_VENTANA[k], BRUMA, bruma * 0.5) for k in ("calida", "fria", "rosa")]
        paso_x, paso_y = pas_x * w, pas_y * h
        vw, vh = ven_w * w, ven_h * h
        cercano = idx >= 2
        x = -0.02
        while x < 1.02:
            fw = aw0 + (aw1 - aw0) * rnd.random()
            fh = ah0 + (ah1 - ah0) * rnd.random()
            X, W = x * w, fw * w
            cx = X + W / 2
            top = suelo - fh * h
            self._geo[idx].append((X, top, W))
            p.fillRect(QRectF(X, top, W, suelo - top), base)
            p.fillRect(QRectF(X, top, W, max(1.0, 0.004 * h)), mezclar(base, BLANCO, 0.10))

            # Azotea escalonada: de 1 a 3 retranqueos, cada uno con su cornisa clara.
            ancho_t, y_t = W, top
            for _ in range(rnd.randint(1, 3)):
                ancho_t *= rnd.uniform(0.70, 0.88)
                th = h * rnd.uniform(0.012, 0.04)
                tramo = QRectF(cx - ancho_t / 2, y_t - th, ancho_t, th)
                p.fillRect(tramo, mezclar(base, BLANCO, 0.03))
                p.fillRect(QRectF(tramo.left(), tramo.top(), tramo.width(), max(1.0, 0.004 * h)),
                           mezclar(base, BLANCO, 0.18))
                y_t -= th

            # Tanque de agua sobre la azotea.
            if rnd.random() < 0.3:
                tw = max(6.0, W * 0.10)
                tx = X + W * rnd.uniform(0.15, 0.70)
                th_t = max(8.0, h * 0.02)
                p.fillRect(QRectF(tx, top - th_t, tw, th_t), mezclar(base, QColor("#000000"), 0.35))
                p.fillRect(QRectF(tx, top - th_t, tw, max(1.0, 0.004 * h)), mezclar(base, BLANCO, 0.15))

            # Antena fina, a veces con una luz roja en la punta.
            if rnd.random() < 0.35:
                largo = h * rnd.uniform(0.02, 0.09)
                p.setPen(QPen(mezclar(base, BLANCO, 0.35), 1))
                p.drawLine(QPointF(cx, y_t), QPointF(cx, y_t - largo))
                if rnd.random() < 0.5:
                    p.setPen(Qt.NoPen)
                    p.setBrush(con_alfa(ROSA, 230))
                    p.drawEllipse(QPointF(cx, y_t - largo), 2.2, 2.2)
                    p.setBrush(Qt.NoBrush)

            # Rejilla de ventanas: 30 % encendidas en tres tonos (degradado en los cercanos), el resto apagadas.
            fila = top + paso_y * 0.8
            while fila <= suelo - paso_y * 0.6:
                col = X + paso_x * 0.6
                while col + vw <= X + W - paso_x * 0.4:
                    if rnd.random() < 0.30:
                        r = rnd.random()
                        c = tonos[0] if r < 0.45 else (tonos[1] if r < 0.8 else tonos[2])
                        alfa = int(rnd.randint(120, 255) * (1.0 - 0.35 * bruma))
                        if cercano:
                            deg = QLinearGradient(0, fila, 0, fila + vh)
                            deg.setColorAt(0.0, con_alfa(mezclar(c, BLANCO, 0.45), alfa))
                            deg.setColorAt(1.0, con_alfa(c, alfa))
                            p.fillRect(QRectF(col, fila, vw, vh), QBrush(deg))
                        else:
                            p.fillRect(QRectF(col, fila, vw, vh), con_alfa(c, alfa))
                    else:
                        p.fillRect(QRectF(col, fila, vw, vh), apagada)
                    if rnd.random() < 0.10:      # persiana bajada: dos líneas horizontales oscuras
                        for frac in (0.30, 0.62):
                            p.fillRect(QRectF(col, fila + vh * frac, vw, max(1.0, vh * 0.12)), con_alfa(OSCURO, 170))
                    col += paso_x
                fila += paso_y

            # Bordes iluminados por el neón (solo los planos cercanos).
            if cercano and rnd.random() < 0.5:
                borde = X if rnd.random() < 0.5 else X + W
                p.setPen(QPen(arista, 1))
                p.drawLine(QPointF(borde, top), QPointF(borde, suelo))
                p.setPen(Qt.NoPen)

            x += fw * (0.6 + 0.5 * rnd.random())

    def _niebla(self, p, w, h, idx):
        y0, y1, color = BANDAS_NIEBLA[idx]
        g = QLinearGradient(0, y0 * h, 0, y1 * h)
        g.setColorAt(0.0, con_alfa(color, 0))
        g.setColorAt(0.5, con_alfa(color, 110))
        g.setColorAt(1.0, con_alfa(color, 0))
        p.fillRect(QRectF(0, y0 * h, w, (y1 - y0) * h), QBrush(g))

    def _colocar_letreros(self, p, w, h, rnd, acento):
        """Pega cada letrero a una fachada de su plano (dentro de su ancho), con 0.03*w de hueco a los demás.
        No se pone si no cabe, si se sale de la pantalla o si lo taparía un plano más cercano."""
        suelo = SUELO * h
        ocupados = []
        for plano, xf, tipo, texto, color, modo in LETREROS:
            e = ESCALA_PLANO[plano]
            if tipo == "barra":
                rw, rh = 0.022 * w * e, 0.16 * h * e
            else:
                rw, rh = (0.035 + 0.02 * len(texto)) * w * e, 0.055 * h * e
            fase = rnd.uniform(0.0, 6.28)
            periodo = rnd.uniform(4.0, 7.0)
            objetivo_x = xf * w
            objetivo_y = (ALTURA_LETREROS[plano] - 0.2 * rnd.random()) * h
            hueco, margen = 0.03 * w, 0.012 * w
            colocado = None
            candidatos = sorted(self._geo[plano], key=lambda b: abs(b[0] + b[2] / 2 - objetivo_x))
            for bx, btop, bw in candidatos:
                lo_x, hi_x = bx + margen, bx + bw - margen - rw
                lo_y, hi_y = btop + rh + 0.01 * h, suelo - 0.04 * h
                if hi_x < lo_x or hi_y < lo_y:
                    continue
                x0 = min(max(objetivo_x - rw / 2, lo_x), hi_x)
                y1 = min(max(objetivo_y, lo_y), hi_y)
                rect = (x0, y1 - rh, x0 + rw, y1)
                if rect[0] < 0.01 * w or rect[2] > 0.99 * w:
                    continue
                if any(_solapa(rect, o, hueco, 0.01 * h) for o in ocupados):
                    continue
                tapado = any(
                    _solapa(rect, (bx2, bt2, bx2 + bw2, suelo))
                    for q in range(plano + 1, len(PLANOS))
                    for bx2, bt2, bw2 in self._geo[q]
                )
                if tapado:
                    continue
                colocado = rect
                break
            if colocado is None:
                continue
            ocupados.append(colocado)
            cc = QColor(acento) if color == "cian" else QColor(COLOR_LETRERO[color])
            m = int(max(20, 0.02 * h))
            pix = self._sprite_letrero(rw, rh, texto, cc, tipo, m)
            s = {"pix": pix, "x": colocado[0] - m, "y": colocado[1] - m, "cx": colocado[0] + rw / 2,
                 "ancho": rw, "color": cc, "modo": modo, "fase": fase, "periodo": periodo}
            self._letreros.append(s)
            if modo == "fijo":
                p.drawPixmap(int(s["x"]), int(s["y"]), pix)

    def _sprite_letrero(self, rw, rh, texto, cc, tipo, m):
        pix = QPixmap(int(rw + 2 * m) + 1, int(rh + 2 * m) + 1)
        pix.fill(Qt.transparent)
        pp = QPainter(pix)
        try:
            pp.setRenderHint(QPainter.Antialiasing, True)
            pp.translate(m, m)
            marco = QPainterPath()
            radio = rw / 2 if tipo == "barra" else min(8.0, rh / 2)
            marco.addRoundedRect(QRectF(0, 0, rw, rh), radio, radio)
            fuente = QFont("Segoe UI")
            # Respaldo para los kanji: Segoe UI no los trae.
            fuente.setFamilies(["Segoe UI", "Yu Gothic UI", "Meiryo", "Microsoft YaHei UI", "MS Gothic"])
            fuente.setBold(True)
            fuente.setPixelSize(max(8, int(rw * 0.7 if tipo == "barra" else rh * 0.55)))
            caja = QFontMetricsF(fuente).tightBoundingRect(texto)
            letra = QPainterPath()
            letra.addText(QPointF((rw - caja.width()) / 2 - caja.left(),
                                  (rh - caja.height()) / 2 - caja.top()), fuente, texto)
            pp.fillPath(marco, con_alfa(cc, 26))
            _resplandor(pp, marco, cc)
            pp.fillPath(letra, con_alfa(cc, 50))
            _resplandor(pp, letra, cc)
        finally:
            pp.end()
        return pix

    def _calle(self, p, w, h, rnd):
        suelo = SUELO * h
        asfalto = QLinearGradient(0, suelo, 0, h)
        asfalto.setColorAt(0.0, QColor("#0E0816"))
        asfalto.setColorAt(1.0, QColor("#0A0710"))
        p.fillRect(QRectF(0, suelo, w, h - suelo), QBrush(asfalto))

        # Resplandor magenta del horizonte sobre el asfalto.
        resplandor = QLinearGradient(0, suelo, 0, suelo + 0.08 * h)
        resplandor.setColorAt(0.0, con_alfa(ROSA, 30))
        resplandor.setColorAt(1.0, con_alfa(ROSA, 0))
        p.fillRect(QRectF(0, suelo, w, 0.08 * h), QBrush(resplandor))

        # Seis charcos sin borde: cielo reflejado en capas de transparencia y una mancha vertical de neón.
        p.setPen(Qt.NoPen)
        for _ in range(6):
            frac = 0.10 + 0.8 * rnd.random()
            yy = suelo + (h - suelo) * frac
            xx = rnd.random() * w
            rx = w * (0.03 + 0.06 * frac)
            ry = h * (0.008 + 0.02 * frac)
            for escala, alfa in ((1.0, 30), (0.7, 40), (0.4, 50)):
                p.setBrush(QBrush(con_alfa(QColor("#3A1450"), alfa)))
                p.drawEllipse(QPointF(xx, yy), rx * escala, ry * escala)
            neon = (ROSA, self.acento(), COLOR_LETRERO["ambar"])[int(rnd.random() * 3)]
            for escala, alfa in ((1.0, 14), (0.6, 26), (0.3, 40)):
                p.fillRect(QRectF(xx - rx * 0.2 * escala, yy, rx * 0.4 * escala, ry * 3), con_alfa(neon, alfa))

        p.setPen(QPen(con_alfa(self.acento(), 60), 1))
        p.drawLine(QPointF(0, suelo), QPointF(w, suelo))

    # ------------------------------------------------------------ animado (cada cuadro)

    @staticmethod
    def _factor(s, t, e):
        """Brillo de un letrero en este instante (0..1). `e` es la energía de la música."""
        modo = s["modo"]
        if modo == "parpadeo":
            n = 0.5 + 0.5 * (0.6 * math.sin(t * 1.7 + s["fase"]) + 0.4 * math.sin(t * 4.3 + s["fase"] * 1.9))
            return (0.6 + 0.4 * n) * (0.9 + 0.1 * e)
        if modo == "apagado":
            if (t + s["fase"]) % s["periodo"] < 0.08:
                return 0.0
            return 0.9 + 0.1 * e
        if modo == "pulso":
            return 0.85 + 0.15 * e
        return 0.9 + 0.1 * e

    def pintar_animado(self, p, w, h, t):
        if not self._letreros:
            return
        suelo = SUELO * h
        acento = self.acento()
        e = self.energia()

        # Reflejos verticales de cada letrero en el suelo mojado.
        for s in self._letreros:
            f = self._factor(s, t, e)
            if f <= 0.0:
                continue
            # Dos franjas: una ancha y muy tenue, y otra estrecha y más viva en el centro.
            for ancho, alfa in ((max(10.0, s["ancho"] * 0.9), 20), (max(6.0, s["ancho"] * 0.35), 60)):
                g = QLinearGradient(0, suelo, 0, suelo + 0.16 * h)
                g.setColorAt(0.0, con_alfa(s["color"], alfa * f))
                g.setColorAt(1.0, con_alfa(s["color"], 0))
                p.fillRect(QRectF(s["cx"] - ancho / 2, suelo, ancho, 0.16 * h), QBrush(g))

        # Letreros que parpadean o pulsan.
        for s in self._letreros:
            if s["modo"] == "fijo":
                continue
            f = self._factor(s, t, e)
            if f <= 0.0:
                continue
            p.save()
            p.setOpacity(min(1.0, f))
            p.drawPixmap(int(s["x"]), int(s["y"]), s["pix"])
            p.restore()

        # Coches voladores lejanos: dos luces con estela.
        for c in self._coches:
            u = (c["fase"] + c["vel"] * t) % 1.0
            x = (-0.1 + 1.2 * u) * w
            d = c["dir"]
            if d < 0:
                x = w - x
            y = c["y"] * h
            calido = QColor("#FFE7B0")
            cola = QLinearGradient(QPointF(x - d * 0.06 * w, y), QPointF(x, y))
            cola.setColorAt(0.0, con_alfa(calido, 0))
            cola.setColorAt(1.0, con_alfa(calido, 150))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QBrush(cola), 2))
            p.drawLine(QPointF(x - d * 0.06 * w, y), QPointF(x, y))
            self.brillo(p, x + d * 6, y, 0.02 * h, calido, 200)
            self.brillo(p, x - d * 2, y, 0.012 * h, ROSA, 160)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(BLANCO))
            p.drawEllipse(QPointF(x + d * 6, y), 1.8, 1.8)
            p.setBrush(Qt.NoBrush)

        # Salpicaduras: 20 elipses que crecen y se desvanecen en 0,3 s.
        sc = h / 1080.0
        for i in range(20):
            tt = t + i * 0.037
            a = (tt % 0.3) / 0.3
            k = int(tt / 0.3)
            x = _azar(k, i, 0) * w
            y = suelo + 0.02 * h + _azar(k, i, 1) * (h - suelo) * 0.9
            r = (4.0 + 10.0 * _azar(k, i, 2)) * sc * (0.3 + 0.7 * a)
            p.setPen(QPen(con_alfa(acento, 170 * (1.0 - a)), 1))
            p.drawEllipse(QPointF(x, y), r, r * 0.35)

        # Ondas de la música sobre la acera (quedan sobre el asfalto, sin edificios detrás).
        self.ondas(p, base_y=0.76 * h, ancho=w, alto_max=0.10 * h, color=acento)

        # Lluvia fina y diagonal (100°), con paralaje: las gotas cercanas son más rápidas y largas.
        p.setBrush(Qt.NoBrush)
        for x0, y0, vel, largo, alfa in self._lluvia:
            y = ((y0 + vel * t) % 1.0) * (h + 80) - 40
            x = ((x0 * (w + 200) - 0.179 * (y + 40)) % (w + 200)) - 100
            L = largo * h
            p.setPen(QPen(con_alfa(LLUVIA, alfa), 1))
            p.drawLine(QPointF(x, y), QPointF(x - 0.174 * L, y + 0.985 * L))
