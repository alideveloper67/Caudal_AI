# -*- coding: utf-8 -*-
"""Diseños con efectos: katana, glitch, fuego, electro, cromo, neón escrito, polvo de estrellas y garabato."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF)

from .base import (BLANCO, NEGRO, Diseno, alfa, azar, bloque, borde, claro, diagonal, entre, extrusion, in_cubic,
                   cuadro_fuego, hoja, in_out, lim, mancha, mezcla, muelle, oscuro, out_back, out_cubic, out_expo, out_quint, punto,
                   relleno, sello, sombra, temblor, unir, vertical)


class Katana(Diseno):
    CLAVE = "katana"
    NOMBRE = "Katana"
    DETALLE = "Un corte de espada abre cada frase y otro la parte en dos"
    FUENTE = "bangers"
    PALABRAS = 3
    LETRAS = 16
    SALIDA = 0.32

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.86, cx.h * 0.68, 2, 0.24, 0.14, sesgo=0.10))
        k = cx.k

        def lleno(q, tinta, t):
            sombra(q, tinta, k, 1.3, 4)
            tinta.difusa(q, cx.a, 18 * k, 0.75)
            extrusion(q, tinta, oscuro(cx.a, 0.35), oscuro(cx.a, 0.75), 6 * k, math.radians(55))
            borde(q, t, QColor(8, 5, 12), 5 * k)
            relleno(q, t, vertical(t, (0, BLANCO), (0.60, QColor(252, 250, 255)), (1, claro(cx.a, 0.45))))
        return {"lleno": sello(t, lleno, 34 * k, cx.dpr)}

    @staticmethod
    def _mitad(W, H, ang, arriba):
        """El medio plano por encima o por debajo del corte."""
        dx, dy = math.cos(ang), math.sin(ang)
        nx, ny = (dy, -dx) if arriba else (-dy, dx)
        L = W + H
        p = QPainterPath()
        p.addPolygon(QPolygonF([QPointF(-dx * L, -dy * L), QPointF(dx * L, dy * L),
                                QPointF(dx * L + nx * L, dy * L + ny * L), QPointF(-dx * L + nx * L, -dy * L + ny * L)]))
        p.closeSubpath()
        return p

    def _tajo(self, p, cx, ang, u, brillo, ancho=7.0):
        """La hoja: una lente de luz que cruza la pantalla (u: cuánto avanzó)."""
        if brillo <= 0.01:
            return
        L = cx.w * 0.62
        dx, dy = math.cos(ang), math.sin(ang)
        a, b = -L + 2 * L * lim(u - 0.45) / 0.55, -L + 2 * L * out_cubic(u)
        medio = (a + b) / 2
        for g, color in ((ancho * 3.2, alfa(cx.a, 90 * brillo)), (ancho * 1.5, alfa(claro(cx.a, 0.5), 170 * brillo)),
                         (ancho * 0.6, alfa(BLANCO, 255 * brillo))):
            g *= cx.k
            hoja = QPainterPath(QPointF(dx * a, dy * a))
            hoja.quadTo(QPointF(dx * medio - dy * g, dy * medio + dx * g), QPointF(dx * b, dy * b))
            hoja.quadTo(QPointF(dx * medio + dy * g, dy * medio - dx * g), QPointF(dx * a, dy * a))
            p.fillPath(hoja, color)

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        ang = math.radians(entre(-24, -13, pl.semilla)) * (1 if pl.n % 2 else -1)
        dx, dy = math.cos(ang), math.sin(ang)
        s = (1 + 0.04 * lim(t / max(0.5, pl.dur))) * (1 + 0.045 * cx.golpe)
        sx, sy, _g = temblor(max(0.0, t - 0.07), 9 * cx.k, 10, pl.semilla)
        if u <= 0:
            e = out_expo((t - 0.06) / 0.26)
            op = lim((t - 0.05) / 0.05)
            if e < 0.995:
                d = (1 - e) * cx.w * 0.34
                for arriba, signo in ((True, 1), (False, -1)):
                    p.save()
                    p.setClipPath(self._mitad(cx.w, cx.h, ang, arriba))
                    o["lleno"].pintar(p, sx + dx * d * signo, sy + dy * d * signo, s, op)
                    p.restore()
            else:
                o["lleno"].pintar(p, sx, sy, s, 1.0)
            self._tajo(p, cx, ang, t / 0.16, math.exp(-max(0.0, t - 0.10) * 9))
            if t < 0.6:
                pm = mancha(claro(cx.a, 0.4), 16)
                for i in range(16):
                    v = t - 0.08 - 0.004 * i
                    if v <= 0:
                        continue
                    q = entre(-0.5, 0.5, pl.semilla, i) * cx.w
                    lado = 1 if i % 2 else -1
                    vx = dx * 260 * azar(i, 2) - dy * lado * (60 + 240 * azar(i, 3))
                    vy = dy * 260 * azar(i, 2) + dx * lado * (60 + 240 * azar(i, 3)) + 420 * v
                    punto(p, pm, dx * q + vx * v * cx.k, dy * q + vy * v * cx.k, (2.2 + 4.5 * azar(i, 5)) * cx.k,
                          math.exp(-v * 6))
                p.setOpacity(1)
            return
        # la salida: otro tajo y las dos mitades se deslizan y caen
        ang2 = -ang * 0.9
        dx, dy = math.cos(ang2), math.sin(ang2)
        e = in_out(lim((u - 0.16) / 0.84))
        for arriba, signo in ((True, 1), (False, -1)):
            p.save()
            p.translate(dx * signo * e * cx.w * 0.22, dy * signo * e * cx.w * 0.22 + (e ** 2) * cx.h * (0.02 if arriba else 0.34))
            p.rotate(signo * -7 * e)
            p.setClipPath(self._mitad(cx.w * 1.6, cx.h * 1.6, ang2, arriba))
            o["lleno"].pintar(p, 0, 0, s, (1 - e) ** 1.7)
            p.restore()
        self._tajo(p, cx, ang2, u / 0.22, math.exp(-max(0.0, u - 0.18) * 7), 6.0)


class Glitch(Diseno):
    CLAVE = "glitch"
    NOMBRE = "Glitch"
    DETALLE = "Señal rota: franjas, colores separados y letras que se descifran"
    FUENTE = "ops"
    PALABRAS = 4
    LETRAS = 20
    SALIDA = 0.20

    RAROS = "#@$%&/\\<>=+*0123456789ΞΛØ¥§"

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        k = cx.k

        def caras(ts, completo):
            t = unir(bloque(ts, f, cx.w * 0.82, cx.h * 0.62, 2, 0.28, 0.16))
            m = 26 * k

            def base(q, tinta, t):
                sombra(q, tinta, k, 1.2, 2)
                borde(q, t, QColor(6, 5, 12, 230), 4 * k)
                relleno(q, t, BLANCO)
            s = {"base": sello(t, base, m, cx.dpr)}
            if completo:
                s["cian"] = sello(t, lambda q, ti, t: relleno(q, t, QColor("#00F0FF")), m, cx.dpr)
                s["mag"] = sello(t, lambda q, ti, t: relleno(q, t, QColor("#FF0055")), m, cx.dpr)
            return s
        o = caras(textos, True)
        # dos versiones cifradas: se ven un instante al entrar
        o["cifra"] = []
        for v in range(2):
            raros = ["".join(self.RAROS[int(azar(pl.semilla, v, i, j) * len(self.RAROS))] for j in range(len(x)))
                     for i, x in enumerate(textos)]
            o["cifra"].append(caras(raros, False)["base"])
        return o

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        paso = int(t * 22)
        # de vez en cuando, un fallo suelto
        suelto = 0.45 if azar(pl.semilla, int(t * 2.2), 9) > 0.62 and (t * 2.2) % 1.0 < 0.22 else 0.0
        fz = max(math.exp(-t * 6.0), suelto, max(0.0, cx.golpe - 0.35) * 0.9, u * 1.3)
        op = 1 - in_cubic(u)
        desv = (2.0 + 15 * fz) * cx.k
        temb = (azar(paso, pl.semilla) - 0.5) * 8 * fz * cx.k
        if t < 0.15 and u <= 0:
            quien = o["cifra"][paso % 2]
            quien.pintar(p, temb, 0, 1.0 + 0.08 * azar(paso, 3), 0.95)
            self._bloques(p, pl, cx, paso, fz)
            return
        base = o["base"]
        if fz < 0.07:
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            o["cian"].pintar(p, -desv, 0, 1.0, 0.75 * op)
            o["mag"].pintar(p, desv, 0, 1.0, 0.75 * op)
            base.pintar(p, 0, 0, 1.0, op)
        else:
            n = 11
            alto = base.h / n
            for i in range(n):
                fuerte = azar(paso, i, pl.semilla) > 0.50
                dx = (azar(paso, i, 7) - 0.5) * cx.w * 0.20 * fz if fuerte else 0.0
                dx += temb
                y = i * alto
                p.setOpacity(0.8 * op)
                o["cian"].franja(p, 0, 0, y, alto, dx - desv)
                o["mag"].franja(p, 0, 0, y, alto, dx + desv)
                p.setOpacity(op)
                base.franja(p, 0, 0, y, alto, dx)
            p.setOpacity(1)
        self._bloques(p, pl, cx, paso, fz * op)
        # barra de barrido
        y = -cx.h / 2 + ((t * 0.55 + azar(pl.semilla)) % 1.0) * cx.h
        g = QLinearGradient(0, y - 16, 0, y + 16)
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, int(20 * op)))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(base.x0, y - 16, base.w, 32), QBrush(g))

    def _bloques(self, p, pl, cx, paso, fz):
        if fz < 0.12:
            return
        p.setPen(Qt.NoPen)
        for i in range(int(3 + 7 * min(1.0, fz))):
            if azar(paso, i, 21) > 0.75:
                continue
            w = (0.03 + 0.22 * azar(paso, i, 22)) * cx.w
            h = (0.008 + 0.035 * azar(paso, i, 23)) * cx.h
            x = (azar(paso, i, 24) - 0.5) * cx.w * 0.9
            y = (azar(paso, i, 25) - 0.5) * cx.h * 0.72
            c = (QColor("#00F0FF"), QColor("#FF0055"), BLANCO, cx.a)[int(azar(paso, i, 26) * 4) % 4]
            p.fillRect(QRectF(x, y, w, h), alfa(c, 210 * min(1.0, fz)))


class Fuego(Diseno):
    CLAVE = "fuego"
    NOMBRE = "En llamas"
    DETALLE = "La letra se prende, arde con la música y se consume en brasas"
    FUENTE = "anton"
    PALABRAS = 3
    LETRAS = 15
    SALIDA = 0.45

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.80, cx.h * 0.52, 2, 0.24, 0.14))
        t.translate(0, cx.h * 0.07)
        k = cx.k

        def halo(q, tinta, t):
            tinta.difusa(q, QColor("#FF3A00"), 34 * k, 1.0)
            tinta.difusa(q, QColor("#FF7A00"), 15 * k, 0.9)

        def lleno(q, tinta, t):
            tinta.difusa(q, NEGRO, 7 * k, 1.0, 0, 3 * k)
            borde(q, t, QColor(58, 6, 0), 6 * k)
            relleno(q, t, vertical(t, (0, "#D92B00"), (0.30, "#FF7A00"), (0.62, "#FFC93C"), (1, "#FFF6C8")))
            borde(q, t, QColor(255, 236, 150, 120), 1.3 * k)
        r = t.boundingRect()
        alto = cx.h * 0.46                          # hasta dónde suben las llamas sobre las letras
        zona = QRectF(r.left() - 34 * k, r.top() - alto, r.width() + 68 * k, r.height() + alto + 10 * k)

        def mascara(q, tinta, t):
            # la silueta repetida hacia arriba, cada vez más suave y más tenue: el fuego sale de las letras
            pasos = 9
            for i in range(pasos, 0, -1):
                u = i / pasos
                tinta.difusa(q, BLANCO, (4 + 22 * u) * k, 0.50 * (1 - u * 0.60), 0, -alto * 0.80 * u)
            tinta.difusa(q, BLANCO, 5 * k, 1.0)
        from .base import Sello
        from ..estilo_letra import _Tinta
        pm = QPixmap(max(1, int(zona.width())), max(1, int(zona.height())))
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing)
        q.translate(-zona.left(), -zona.top())
        mascara(q, _Tinta(t, zona.left(), zona.top(), pm.width(), pm.height(), 1.0), t)
        q.end()
        return {"halo": sello(t, halo, 70 * k, cx.dpr), "lleno": sello(t, lleno, 26 * k, cx.dpr), "r": r,
                "mascara": Sello(pm, zona.left(), zona.top(), pm.width(), pm.height()),
                "lienzo": QPixmap(pm.size()), "alto": alto}

    def _llamas(self, o, pl, t, cx, fuerza):
        """El fuego de este instante, recortado a las letras (en su lienzo)."""
        textura = hoja("fuego.png")
        m, lienzo = o["mascara"], o["lienzo"]
        lienzo.fill(Qt.transparent)
        if textura.isNull():
            return lienzo
        q = QPainter(lienzo)
        q.setRenderHint(QPainter.SmoothPixmapTransform)
        origen = cuadro_fuego(t + azar(pl.semilla))
        ancho = max(220.0, cx.h * 1.05)
        # con más fuerza, las llamas llegan más arriba
        alto = o["r"].height() * 0.80 + o["alto"] * (0.42 + 0.62 * fuerza)
        x = -ancho * azar(pl.semilla, 8)
        while x < m.w:
            # la textura casa consigo misma por los lados: no se ve la junta
            q.drawPixmap(QRectF(x, m.h - alto, ancho + 1, alto), textura, origen)
            x += ancho
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        q.drawPixmap(0, 0, m.pm)
        q.end()
        return lienzo

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        r, m = o["r"], o["mascara"]
        prende = out_cubic(t / 0.42)
        frente = r.left() - 20 * cx.k + (r.width() + 40 * cx.k) * prende
        op = 1 - in_out(u)
        parpadeo = 0.86 + 0.14 * math.sin(t * 31 + pl.semilla) * math.sin(t * 17)
        fuerza = lim(0.30 + 0.35 * cx.energia + 0.75 * cx.golpe + 0.6 * math.exp(-t * 3) + 0.5 * u, 0, 1.3)
        p.save()
        p.setClipRect(QRectF(-cx.w, -cx.h, frente + cx.w, 2 * cx.h))
        o["halo"].pintar(p, 0, 0, 1.0 + 0.02 * cx.golpe, op * parpadeo * min(1.0, 0.55 + 0.5 * cx.golpe))
        llamas = self._llamas(o, pl, t, cx, fuerza)
        p.setOpacity(op)
        p.drawPixmap(QPointF(m.x0, m.y0 - u * 26 * cx.k), llamas)
        p.setOpacity(1)
        s = 1 + 0.025 * cx.golpe
        o["lleno"].pintar(p, 0, -u * 14 * cx.k, s, op)
        # y un velo de fuego por delante, para que las letras estén dentro y no pegadas encima
        p.setOpacity(op * (0.26 + 0.22 * cx.golpe + 0.5 * u))
        p.drawPixmap(QPointF(m.x0, m.y0 - u * 26 * cx.k), llamas)
        p.setOpacity(1)
        p.restore()
        brasa = mancha(QColor("#FFB347"), 24)
        if prende < 0.999:
            punto(p, brasa, frente, r.center().y(), r.height() * 0.5, 0.9 * (1 - prende ** 3))
        for i in range(30):
            vel = 0.28 + 0.45 * azar(i, 11)
            v = (t * vel + azar(i, 12)) % 1.0
            x = r.left() + r.width() * azar(i, 13) + math.sin(t * 2.2 + i) * 20 * cx.k
            y = r.bottom() - v * cx.h * (0.85 + 0.3 * u)
            if x < frente:
                punto(p, brasa, x, y, (1.8 + 2.8 * azar(i, 14)) * cx.k, (1 - v) * (1 - u * 0.6) * 0.95)
        p.setOpacity(1)


class Electro(Diseno):
    CLAVE = "electro"
    NOMBRE = "Alto voltaje"
    DETALLE = "Un rayo la enciende y la corriente salta entre las letras con el ritmo"
    FUENTE = "audiowide"
    PALABRAS = 3
    LETRAS = 16
    SALIDA = 0.24

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.82, cx.h * 0.54, 2, 0.28, 0.18))
        k = cx.k
        tono = QColor("#39C6FF") if cx.a.hsvSaturationF() < 0.25 else cx.a

        def apagada(q, tinta, t):
            sombra(q, tinta, k, 1.0, 3)
            relleno(q, t, QColor(20, 24, 38, 225))
            borde(q, t, alfa(tono, 150), 1.8 * k)

        def lleno(q, tinta, t):
            tinta.difusa(q, NEGRO, 9 * k, 0.8, 0, 2 * k)
            for r, fz in ((30, 1.0), (15, 1.1), (6, 1.1)):
                tinta.difusa(q, tono, r * k, fz)
            borde(q, t, claro(tono, 0.25), 3.2 * k)
            relleno(q, t, vertical(t, (0, BLANCO), (0.7, claro(tono, 0.85)), (1, claro(tono, 0.6))))
        n = 60
        pts = [t.pointAtPercent((i + 0.5) / n) for i in range(n)]
        m = 52 * k
        return {"apagada": sello(t, apagada, m, cx.dpr), "lleno": sello(t, lleno, m, cx.dpr), "tono": tono,
                "pts": [(q.x(), q.y()) for q in pts], "r": t.boundingRect()}

    @staticmethod
    def _rayo(x0, y0, x1, y1, semilla, caos, pasos):
        """Un camino quebrado de un punto a otro."""
        dx, dy = x1 - x0, y1 - y0
        largo = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / largo, dx / largo
        c = QPainterPath(QPointF(x0, y0))
        for i in range(1, pasos):
            u = i / pasos
            d = (azar(semilla, i) - 0.5) * caos * largo * math.sin(math.pi * u) ** 0.6
            c.lineTo(x0 + dx * u + nx * d, y0 + dy * u + ny * d)
        c.lineTo(x1, y1)
        return c

    @staticmethod
    def _luz(p, camino, tono, op, k):
        p.setBrush(Qt.NoBrush)
        for ancho, color, a in ((9, tono, 46), (4.2, tono, 120), (1.7, BLANCO, 245)):
            p.setPen(QPen(alfa(color, a * op), ancho * k, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(camino)

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        tono, r, k = o["tono"], o["r"], cx.k
        # enciende parpadeando
        if t < 0.30:
            enc = 1.0 if (t < 0.05 or 0.09 < t < 0.13 or t > 0.18) else 0.15
        else:
            enc = 1.0 if azar(pl.semilla, int(t * 11)) > 0.045 else 0.45
        s = 1 + 0.035 * cx.golpe
        sy = s
        op = 1.0
        if u > 0:                                  # se apaga como un televisor viejo
            sy = s * max(0.02, 1 - out_cubic(u / 0.55))
            s *= 1 + 0.25 * u
            op = 1 - in_cubic(u)
        dx, dy, g = temblor(t, 10 * k, 11, pl.semilla)
        o["apagada"].pintar(p, dx, dy, s, op, g, sy=sy)
        o["lleno"].pintar(p, dx, dy, s, op * enc * (0.90 + 0.10 * cx.golpe), g, sy=sy)
        if u > 0:
            self._luz(p, self._rayo(-cx.w * 0.4 * (1 - u), 0, cx.w * 0.4 * (1 - u), 0, pl.semilla, 0.0, 2), tono, 1 - u, k)
            return
        q = int(t * 26)
        if t < 0.30:
            x1 = entre(r.left(), r.right(), pl.semilla, 1) * 0.8
            c = self._rayo(entre(-0.4, 0.4, pl.semilla, 5) * cx.w, -cx.h * 0.5, x1, r.top() + r.height() * 0.2,
                           pl.semilla + q, 0.34, 11)
            self._luz(p, c, tono, (1 - t / 0.30) * 1.2, k * 1.5)
            rama = self._rayo(x1 * 0.6, -cx.h * 0.2, x1 - entre(-0.3, 0.3, q) * cx.w, r.center().y(), q + 3, 0.4, 7)
            self._luz(p, rama, tono, (1 - t / 0.30) * 0.8, k)
            punto(p, mancha(tono, 48), x1, r.top(), cx.h * 0.55, math.exp(-t * 11) * 0.9)
            p.setOpacity(1)
        arcos = 2 + int(3 * cx.energia + 4 * cx.golpe)
        pts = o["pts"]
        for j in range(arcos):
            clave = int(t * 15) + j * 31
            if azar(clave, j, 2) > 0.70 + 0.25 * cx.golpe:
                continue
            a = pts[int(azar(clave, 4) * len(pts))]
            b = pts[int(azar(clave, 5) * len(pts))]
            if math.hypot(a[0] - b[0], a[1] - b[1]) > cx.w * 0.40:
                continue
            self._luz(p, self._rayo(a[0], a[1], b[0], b[1], clave, 0.42, 7), tono, 0.85, k * 0.85)
            punto(p, mancha(tono, 16), a[0], a[1], 8 * k, 0.9)
            p.setOpacity(1)


class Cromo(Diseno):
    CLAVE = "cromo"
    NOMBRE = "Cromo Y2K"
    DETALLE = "Metal líquido con destellos que lo recorren, como un edit de coches"
    FUENTE = "righteous"
    PALABRAS = 3
    LETRAS = 16
    SALIDA = 0.26

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.86, cx.h * 0.62, 2, 0.26, 0.16, sesgo=0.14))
        k = cx.k
        az = claro(cx.a, 0.62)
        osc = oscuro(cx.a, 0.78)

        def lleno(q, tinta, t):
            tinta.difusa(q, NEGRO, 14 * k, 1.0, 0, 6 * k)
            tinta.difusa(q, cx.a, 24 * k, 0.75)
            extrusion(q, tinta, QColor(120, 126, 150), QColor(16, 16, 30), 8 * k, math.radians(62))
            borde(q, t, QColor(10, 10, 22), 5 * k)
            borde(q, t, QColor(225, 232, 255), 2.2 * k)
            relleno(q, t, vertical(t, (0.0, "#FFFFFF"), (0.16, az), (0.36, "#F4F7FF"), (0.485, oscuro(az, 0.45)),
                                   (0.50, osc), (0.60, oscuro(cx.a, 0.35)), (0.78, az), (0.92, "#FFFFFF"),
                                   (1.0, oscuro(az, 0.25))))
            # filo de luz por dentro
            q.save()
            q.setClipPath(t)
            borde(q, t, QColor(255, 255, 255, 150), 1.8 * k)
            q.restore()
        m = 34 * k
        mascara = sello(t, lambda q, ti, t: relleno(q, t, BLANCO), m, 1.0)
        r = t.boundingRect()
        brillos = []
        for i in range(60):
            q = t.pointAtPercent(azar(pl.semilla, i))
            if q.y() < r.center().y() and all(abs(q.x() - b[0]) > r.width() * 0.16 for b in brillos):
                brillos.append((q.x(), q.y()))
            if len(brillos) >= 5:
                break
        return {"lleno": sello(t, lleno, m, cx.dpr), "mascara": mascara, "brillos": brillos, "r": r, "barrido": None}

    def _barrido(self, p, o, u, op, s, sy):
        """La banda de luz, recortada a las letras."""
        if not 0.0 < u < 1.0 or op <= 0.02:
            return
        m = o["mascara"]
        pm = o["barrido"]
        if pm is None:
            pm = o["barrido"] = QPixmap(m.pm.size())
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        x = -m.w * 0.3 + m.w * 1.6 * u
        g = QLinearGradient(x - m.h * 0.75, 0, x + m.h * 0.75, m.h * 0.6)
        for pos, a in ((0.0, 0), (0.36, 0), (0.47, 225), (0.53, 255), (0.60, 170), (0.70, 0), (1.0, 0)):
            g.setColorAt(pos, QColor(255, 255, 255, a))
        q.fillRect(pm.rect(), QBrush(g))
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        q.drawPixmap(0, 0, m.pm)
        q.end()
        p.save()
        p.setOpacity(op)
        p.scale(s, sy)
        p.drawPixmap(QPointF(m.x0, m.y0), pm)
        p.restore()

    @staticmethod
    def _estrella(p, x, y, r, op):
        if op <= 0.01 or r < 0.6:
            return
        p.setOpacity(op)
        p.setPen(Qt.NoPen)
        c = QPainterPath()
        for giro, rr in ((0.0, r), (math.pi / 4, r * 0.45)):
            pts = QPolygonF()
            for i in range(8):
                a = giro + math.pi / 4 * i
                d = rr if i % 2 == 0 else rr * 0.10
                pts.append(QPointF(x + math.cos(a) * d, y + math.sin(a) * d))
            c.addPolygon(pts)
            c.closeSubpath()
        c.setFillRule(Qt.WindingFill)
        p.fillPath(c, BLANCO)
        p.setOpacity(1)

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        e = out_back(t / 0.38, 1.4)
        s = 1 + 0.03 * cx.golpe + 0.03 * lim(t / max(0.5, pl.dur))
        sy = s * max(0.02, math.sin(lim(e, 0, 1.2) * math.pi / 2))
        op = lim(t / 0.05)
        if u > 0:
            sy = s * max(0.02, math.cos(in_out(u) * math.pi / 2))
            op = 1 - in_cubic(u)
        sesgo = (1 - lim(t / 0.38)) * 0.5 + 0.35 * u
        o["lleno"].pintar(p, 0, 0, s, op, sy=sy, sesgo=-sesgo)
        if t > 0.22 and u <= 0:
            ciclo = ((t - 0.22) / 1.25) % 1.45
            self._barrido(p, o, ciclo, 0.9, s, sy)
            # destello horizontal al entrar
            f = math.exp(-(t - 0.22) * 4.0)
            if f > 0.02:
                pm = mancha(claro(cx.a, 0.5), 48)
                p.setCompositionMode(QPainter.CompositionMode_Screen)
                p.setOpacity(min(1.0, f))
                p.drawPixmap(QRectF(-cx.w * 0.6, -14 * cx.k, cx.w * 1.2, 28 * cx.k), pm, QRectF(pm.rect()))
                p.setOpacity(1)
                p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            for i, (x, y) in enumerate(o["brillos"]):
                f = (t * 0.8 + i * 0.37 + azar(pl.semilla, i)) % 1.0
                b = math.sin(math.pi * lim(f / 0.42)) if f < 0.42 else 0.0
                self._estrella(p, x * s, y * sy, (9 + 13 * azar(i, pl.semilla, 4)) * cx.k * b * (1 + 0.6 * cx.golpe), b)


class Neon(Diseno):
    CLAVE = "letrero"
    NOMBRE = "Neón escrito"
    DETALLE = "Se escribe con luz, parpadea y se enciende como un letrero de noche"
    FUENTE = "pacifico"
    PALABRAS = 4
    LETRAS = 24
    SALIDA = 0.20

    def preparar(self, pl, cx):
        from .base import fuente
        f, _c = fuente(self.FUENTE)
        piezas = bloque(list(pl.textos), f, cx.w * 0.82, cx.h * 0.60, 2, 0.24, 0.20)
        t = unir(piezas)
        k = cx.k
        tono, tono2 = cx.a, cx.b if cx.b != cx.a else cx.c

        def apagado(q, tinta, t):
            tinta.difusa(q, NEGRO, 8 * k, 0.9, 0, 3 * k)
            borde(q, t, alfa(NEGRO, 200), 5 * k)
            borde(q, t, alfa(claro(tono, 0.2), 130), 2 * k)

        def lleno(q, tinta, t):
            tinta.difusa(q, NEGRO, 8 * k, 0.8, 0, 3 * k)
            for r, fz, c in ((40, 0.9, tono2), (22, 1.0, tono), (11, 1.2, tono), (5, 1.1, claro(tono, 0.3))):
                tinta.difusa(q, c, r * k, fz)
            borde(q, t, claro(tono, 0.15), 4.2 * k)
            borde(q, t, claro(tono, 0.6), 1.8 * k)
            relleno(q, t, claro(tono, 0.93))
        m = 64 * k
        filas = {}
        for z in piezas:
            filas.setdefault(z.fila, []).append(z)
        recorrido = []
        for fi in sorted(filas):
            g = filas[fi]
            recorrido.append((min(z.x - z.w / 2 for z in g), max(z.x + z.w / 2 for z in g),
                              min(z.y - z.h / 2 for z in g), max(z.y + z.h / 2 for z in g)))
        return {"apagado": sello(t, apagado, m, cx.dpr), "lleno": sello(t, lleno, m, cx.dpr), "filas": recorrido,
                "tono": tono, "m": m}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        dur = min(0.55, max(0.25, pl.dur * 0.35))
        av = t / dur * len(o["filas"])
        s = 1 + 0.015 * cx.golpe
        if u > 0:
            op = 1.0 if azar(pl.semilla, int(u * 9)) > 0.35 + 0.5 * u else 0.15
            o["lleno"].pintar(p, 0, 0, s, op * (1 - u))
            return
        escrito = av >= len(o["filas"])
        if escrito:
            t2 = t - dur
            luz = 1.0
            if t2 < 0.34:                         # termina de encender: parpadeo
                luz = 1.0 if (t2 < 0.04 or 0.10 < t2 < 0.15 or t2 > 0.22) else 0.25
            elif azar(pl.semilla, int(t * 9)) < 0.03:
                luz = 0.55
            o["apagado"].pintar(p, 0, 0, s, 1.0)
            o["lleno"].pintar(p, 0, 0, s, luz * (0.88 + 0.12 * cx.golpe))
            if t2 < 0.4:
                o["lleno"].pintar(p, 0, 0, s * (1 + 0.10 * t2 / 0.4), 0.45 * (1 - t2 / 0.4) * luz)
            return
        # escribiendo: cada fila se descubre de izquierda a derecha con la punta de luz
        punta = None
        for i, (x0, x1, y0, y1) in enumerate(o["filas"]):
            a = in_out(lim(av - i))
            if a <= 0:
                break
            x = x0 - 10 + (x1 - x0 + 20) * a
            arriba = -cx.h if i == 0 else (o["filas"][i - 1][3] + y0) / 2
            abajo = cx.h if i + 1 == len(o["filas"]) else (y1 + o["filas"][i + 1][2]) / 2
            p.save()
            p.setClipRect(QRectF(-cx.w, arriba, x + cx.w, abajo - arriba))
            o["lleno"].pintar(p, 0, 0, s, 0.95)
            p.restore()
            if a < 1:
                punta = (x, mezcla(y0, y1, 0.5 + 0.32 * math.sin(a * 26)), y1 - y0)
        if punta:
            pm = mancha(o["tono"], 32)
            p.setCompositionMode(QPainter.CompositionMode_Screen)
            punto(p, pm, punta[0], punta[1], punta[2] * 0.42, 1.0)
            for i in range(8):
                v = (t * 5 + azar(i)) % 1.0
                punto(p, pm, punta[0] - v * 34 * cx.k * azar(i, 2), punta[1] + (azar(i, 3) - 0.4) * 60 * v * cx.k,
                      4 * (1 - v) * cx.k, 1 - v)
            p.setOpacity(1)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)


class Estelar(Diseno):
    CLAVE = "estelar"
    NOMBRE = "Polvo de estrellas"
    DETALLE = "Miles de puntos de luz forman la palabra y el viento se la lleva"
    FUENTE = "poppins"
    PALABRAS = 3
    LETRAS = 16
    SALIDA = 0.70
    N = 300

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.80, cx.h * 0.52, 2, 0.28, 0.18))
        k = cx.k

        def lleno(q, tinta, t):
            sombra(q, tinta, k, 0.8, 3)
            for r, fz in ((26, 0.7), (11, 0.7)):
                tinta.difusa(q, cx.a, r * k, fz)
            borde(q, t, alfa(QColor(10, 8, 20), 150), 2.4 * k)
            relleno(q, t, diagonal(t, (0, BLANCO), (0.5, claro(cx.a, 0.55)), (1, claro(cx.b, 0.45))))
        r = t.boundingRect()
        pts = []
        for i in range(self.N):
            q = t.pointAtPercent((i + azar(pl.semilla, i) * 0.9) / self.N)
            pts.append((q.x() + (azar(i, 7) - 0.5) * 7 * k, q.y() + (azar(i, 8) - 0.5) * 7 * k, (q.x() - r.left()) / max(1.0, r.width())))
        return {"lleno": sello(t, lleno, 40 * k, cx.dpr), "pts": pts, "r": r}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        k = cx.k
        pa, pb, pc = mancha(claro(cx.a, 0.5), 16), mancha(claro(cx.b, 0.55), 16), mancha(BLANCO, 16)
        entra = min(0.5, max(0.28, pl.dur * 0.45))
        if u <= 0:
            firme = in_out(lim((t - entra * 0.55) / (entra * 0.55)))
            o["lleno"].pintar(p, 0, 0, 1 + 0.02 * cx.golpe, firme)
            if t < entra * 1.5:
                for i, (x, y, f) in enumerate(o["pts"]):
                    e = out_quint((t - f * entra * 0.35) / (entra * 0.8))
                    ang = azar(i, 1) * 2 * math.pi + (1 - e) * 2.6
                    d = (1 - e) * cx.w * (0.12 + 0.34 * azar(i, 2))
                    punto(p, (pa, pb, pc)[i % 3], x + math.cos(ang) * d, y + math.sin(ang) * d * 0.7,
                          (1.6 + 2.6 * azar(i, 3)) * k * (1 + 0.8 * (1 - e)),
                          lim(t / 0.10) * (1 - lim((t - entra) / (entra * 0.5))))
                p.setOpacity(1)
            # destellos sueltos mientras se ve
            for i in range(10):
                f = (t * 0.6 + azar(pl.semilla, i)) % 1.0
                x, y, _f = o["pts"][int(azar(pl.semilla, i, int(t * 0.6 + azar(pl.semilla, i))) * len(o["pts"]))]
                punto(p, pc, x, y, 7 * k * math.sin(math.pi * f), firme * math.sin(math.pi * f) * (0.5 + 0.5 * cx.golpe))
            p.setOpacity(1)
            return
        # se deshace de izquierda a derecha
        r = o["r"]
        corte = r.left() - 30 * k + (r.width() + 60 * k) * in_out(u / 0.72)
        p.save()
        p.setClipRect(QRectF(corte, -cx.h, cx.w * 2, 2 * cx.h))
        o["lleno"].pintar(p, 0, 0, 1.0, 1 - 0.5 * u)
        p.restore()
        for i, (x, y, _f) in enumerate(o["pts"]):
            if x > corte:
                continue
            v = lim((corte - x) / (r.width() * 0.9) + azar(i, 4) * 0.10)
            x2 = x + (40 + 210 * azar(i, 5)) * v * k + math.sin(v * 7 + i) * 14 * k * v
            y2 = y - (20 + 150 * azar(i, 6)) * v * v * k
            punto(p, (pa, pb, pc)[i % 3], x2, y2, (1.5 + 2.6 * azar(i, 3)) * k * (1 - 0.5 * v), (1 - v) * (1 - u ** 3))
        p.setOpacity(1)


_RUIDO = [azar(i, 3.7) - 0.5 for i in range(1021)]


class Garabato(Diseno):
    CLAVE = "garabato"
    NOMBRE = "Garabato"
    DETALLE = "Dibujada a mano cuadro a cuadro, con rayones, coronas y flechas que tiemblan"
    FUENTE = "marker"
    PALABRAS = 3
    LETRAS = 16
    SALIDA = 0.16

    CUADROS = 3

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        piezas = bloque(textos, f, cx.w * 0.78, cx.h * 0.50, 2, 0.28, 0.20)
        t = unir(piezas)
        k = cx.k
        tono = QColor("#FFE94A") if pl.linea % 2 else claro(cx.a, 0.15)
        fuerte = max(piezas, key=lambda z: len(z.texto))
        caras = []
        for v in range(self.CUADROS):
            tv = self._temblar(t, 1.25 * k, pl.semilla + v * 17)

            def pintor(q, tinta, t, v=v, tv=tv):
                sombra(q, tinta, k, 0.9, 4)
                g = 4.4 * k
                tinta.copia(q, QColor(12, 10, 16), [(math.cos(a * math.pi / 8) * g, math.sin(a * math.pi / 8) * g)
                                                    for a in range(16)])
                relleno(q, tv, BLANCO)
                # sombreado a rayas dentro
                q.save()
                q.setClipPath(tv)
                r = tv.boundingRect()
                q.setPen(QPen(alfa(tono, 235), 3.2 * k, Qt.SolidLine, Qt.RoundCap))
                x = r.left() - r.height()
                i = 0
                while x < r.right():
                    j = (azar(i, v, 3) - 0.5) * 7 * k
                    q.drawLine(QPointF(x + j, r.bottom()), QPointF(x + r.height() * 0.8 + j, r.top() + r.height() * 0.42))
                    x += 10 * k
                    i += 1
                q.restore()
                self._adornos(q, piezas, fuerte, tono, v, k, pl)
            caras.append(sello(tv, pintor, 46 * k, cx.dpr))
        return {"caras": caras}

    @staticmethod
    def _temblar(t, fuerza, semilla):
        s = QPainterPath(t)
        s.setFillRule(Qt.WindingFill)
        f, n, d = 2.0 * fuerza, len(_RUIDO), int(semilla) * 7
        for i in range(s.elementCount()):
            e = s.elementAt(i)
            s.setElementPositionAt(i, e.x + _RUIDO[(d + i * 2) % n] * f, e.y + _RUIDO[(d + i * 2 + 1) % n] * f)
        return s

    @staticmethod
    def _adornos(q, piezas, fuerte, tono, v, k, pl):
        def mano(puntos, color, ancho, semilla):
            c = QPainterPath()
            for i, (x, y) in enumerate(puntos):
                x += (azar(semilla, i, v) - 0.5) * 5 * k
                y += (azar(semilla, i, v, 2) - 0.5) * 5 * k
                c.moveTo(x, y) if i == 0 else c.lineTo(x, y)
            for col, an in ((QColor(12, 10, 16), ancho + 4 * k), (color, ancho)):
                q.setBrush(Qt.NoBrush)
                q.setPen(QPen(col, an, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                q.drawPath(c)
        r = fuerte.rect()
        y = r.bottom() + 9 * k
        # doble subrayado
        mano([(mezcla(r.left(), r.right(), u), y + math.sin(u * 9) * 2 * k) for u in (0, .2, .4, .6, .8, 1)], tono, 4.4 * k, 1)
        mano([(mezcla(r.left() + r.width() * .12, r.right() - r.width() * .05, u), y + 9 * k) for u in (0, .3, .6, 1)], tono, 3.2 * k, 2)
        tipo = (pl.n + pl.linea) % 3
        if tipo == 0:                                       # corona
            b0 = min(piezas, key=lambda z: z.rect().top() + z.rect().left() * 0.2).rect()
            x, y0, a = b0.left() + b0.width() * 0.10, b0.top() - 8 * k, 30 * k
            mano([(x, y0), (x - a * .15, y0 - a), (x + a * .35, y0 - a * .5), (x + a * .6, y0 - a * 1.15),
                  (x + a * .85, y0 - a * .5), (x + a * 1.35, y0 - a), (x + a * 1.2, y0), (x, y0)], QColor("#FFD23F"), 4 * k, 3)
        elif tipo == 1:                                     # rayitos
            x, y0 = r.right() + 6 * k, r.top() - 4 * k
            for i, ang in enumerate((-75, -42, -10)):
                c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                mano([(x + c * 8 * k, y0 + s * 8 * k), (x + c * 30 * k, y0 + s * 30 * k)], QColor("#FFFFFF"), 4.4 * k, 10 + i)
        else:                                               # asteriscos
            for i, (x, y0) in enumerate(((r.left() - 16 * k, r.top() - 6 * k), (r.right() + 14 * k, r.bottom() - 4 * k))):
                for ang in (0, 60, 120):
                    c, s = math.cos(math.radians(ang)) * 12 * k, math.sin(math.radians(ang)) * 12 * k
                    mano([(x - c, y0 - s), (x + c, y0 + s)], tono, 3.6 * k, 20 + i)

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        paso = int(t * 10)                       # a saltos, como hecho a mano
        cara = o["caras"][(paso + pl.semilla) % self.CUADROS]
        tp = paso / 10.0
        s = (0.55, 1.14, 0.96)[paso] if paso < 3 else 1.0
        s *= 1 + 0.05 * cx.golpe
        giro = entre(-3, 3, pl.semilla) + (azar(paso, pl.semilla) - 0.5) * 1.8
        if u > 0:
            s *= 1 - 0.5 * u
            giro += 10 * u
        dy = -4 * cx.k * abs(math.sin(tp * 9))
        cara.pintar(p, 0, dy, s, 1.0 if u < 0.75 else 0.0, giro)


DISENOS = (Katana, Glitch, Fuego, Electro, Cromo, Neon, Estelar, Garabato)
