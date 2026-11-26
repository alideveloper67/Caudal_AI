# -*- coding: utf-8 -*-
"""Diseños de golpe: los que se clavan en la pantalla (impacto, viral, póster, eco, túnel, phonk)."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

from .base import (BLANCO, NEGRO, Diseno, alfa, anillo, azar, bloque, borde, claro, diagonal, entre, escalar, extrusion,
                   fuente, in_cubic, lim, mancha, mayusculas, mezcla, mover, muelle, oscuro, out_back, out_cubic,
                   out_expo, out_quint, punto, rayos, relleno, sello, sombra, temblor, trazo, unir, vaciar, vertical)


class Impacto(Diseno):
    CLAVE = "impacto"
    NOMBRE = "Impacto"
    DETALLE = "Cada palabra se estrella contra la pantalla: destello, onda y sacudida"
    FUENTE = "anton"
    PALABRAS = 2
    LETRAS = 9
    SALIDA = 0.16

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        piezas = bloque(textos, f, cx.w * 0.80, cx.h * 0.66, 2, 0.22, 0.10)
        t = unir(piezas)
        k = cx.k
        tipo = (pl.n + pl.linea) % 3
        cara = [(0, BLANCO), (0.62, QColor(255, 255, 255)), (1, claro(cx.a, 0.55))]
        if tipo == 1:
            cara = [(0, claro(cx.a, 0.55)), (0.5, cx.a), (1, oscuro(cx.a, 0.12))]

        def lleno(q, tinta, t):
            sombra(q, tinta, k, 1.1, 5)
            if tipo == 2:
                extrusion(q, tinta, cx.a, oscuro(cx.a, 0.55), 9 * k, math.radians(52))
            else:
                extrusion(q, tinta, QColor(18, 14, 26), QColor(4, 3, 8), 6 * k, math.radians(60))
            borde(q, t, QColor(10, 8, 16), 5.0 * k)
            relleno(q, t, vertical(t, *cara))

        m = 34 * k
        return {"lleno": sello(t, lleno, m, cx.dpr),
                "blanco": sello(t, lambda q, ti, t: (ti.difusa(q, BLANCO, 12 * k, 1.2), relleno(q, t, BLANCO)), m, cx.dpr),
                "hueco": sello(t, lambda q, ti, t: borde(q, t, alfa(cx.a, 150), 2.2 * k), m, cx.dpr)}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        e = out_expo(t / 0.15)
        s = 2.0 - 1.0 * e
        s *= 1.0 + 0.055 * lim(t / max(0.4, pl.dur)) + 0.05 * cx.golpe
        dx, dy, g = temblor(max(0.0, t - 0.03), 13 * cx.k, 8.5, pl.semilla)
        op = lim(t / 0.04) * (1 - u)
        s *= 1 + 0.45 * in_cubic(u)
        g += entre(-2.2, 2.2, pl.semilla)
        if u < 1 and t < 0.6:
            rayos(p, cx.w, cx.h, pl.semilla, claro(cx.a, 0.6), math.exp(-t * 5.2) * (1 - u), 30)
            anillo(p, (t - 0.05) / 0.42, cx.w * 0.56, claro(cx.a, 0.35), 9 * cx.k)
        o["hueco"].pintar(p, dx * 0.4, dy * 0.4, s * (1.34 + 0.12 * lim(t)), op * 0.55 * lim((t - 0.08) / 0.2), g * 1.6)
        if t < 0.13:
            o["lleno"].pintar(p, dx, dy, s * 1.45, op * 0.16, g)
            o["lleno"].pintar(p, dx, dy, s * 1.20, op * 0.26, g)
        o["lleno"].pintar(p, dx, dy, s, op, g)
        o["blanco"].pintar(p, dx, dy, s, op * math.exp(-t * 13), g)


class Viral(Diseno):
    CLAVE = "viral"
    NOMBRE = "Viral"
    DETALLE = "Los subtítulos de los videos que se hacen virales: saltan palabra a palabra"
    FUENTE = "poppins"
    PALABRAS = 4
    LETRAS = 22
    SALIDA = 0.12

    TONOS = ("#FFE600", "#39FF6A", "#FF4D6D", "#3DE7FF")

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        piezas = bloque(textos, f, cx.w * 0.84, cx.h * 0.60, 2, 0.30, 0.24, tope=cx.h * 0.26)
        k = cx.k
        con_caja = pl.linea % 3 == 2
        tono = QColor(self.TONOS[pl.linea % len(self.TONOS)])
        grosor = 13 * k

        def pintor(color):
            def hacer(q, tinta, t):
                tinta.difusa(q, NEGRO, 10 * k, 0.9, 0, 7 * k)
                tinta_neg = mover(t, 0, 5 * k)
                borde(q, tinta_neg, NEGRO, grosor)
                borde(q, t, NEGRO, grosor)
                relleno(q, t, vertical(t, (0, claro(color, 0.35)), (0.45, color), (1, color)))
            return hacer
        m = 26 * k
        viva = BLANCO if con_caja else tono
        return {"piezas": piezas, "caja": con_caja, "tono": tono,
                "normal": [sello(z.trazo, pintor(BLANCO), m, cx.dpr) for z in piezas],
                "viva": [sello(z.trazo, pintor(viva), m, cx.dpr) for z in piezas]}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        n = pl.cantadas(t)
        if n <= 0:
            return
        piezas = o["piezas"]
        k = cx.k
        p.save()
        p.rotate(entre(-3.0, 3.0, pl.semilla, pl.linea))
        s0 = (0.80 + 0.20 * muelle(t, 2.6, 9)) * (1 - 0.18 * u) * (1 + 0.02 * cx.golpe)
        p.scale(s0, s0)
        act = min(n, len(piezas)) - 1
        ta = t - (pl.tiempos[act] - pl.t0)
        op = 1 - u
        if o["caja"]:
            r = piezas[act].rect()
            if act > 0 and ta < 0.16:
                a = piezas[act - 1].rect()
                e = out_back(ta / 0.16, 1.2)
                r = QRectF(mezcla(a.x(), r.x(), e), mezcla(a.y(), r.y(), e), mezcla(a.width(), r.width(), e),
                           mezcla(a.height(), r.height(), e))
            r = r.adjusted(-16 * k, -13 * k, 16 * k, 15 * k)
            p.setOpacity(op)
            p.setPen(Qt.NoPen)
            p.setBrush(alfa(NEGRO, 120))
            p.drawRoundedRect(r.translated(0, 6 * k), 16 * k, 16 * k)
            p.setBrush(vivo_caja(o["tono"]))
            p.drawRoundedRect(r, 16 * k, 16 * k)
            p.setOpacity(1)
        for z in piezas:
            if z.i > act:
                continue
            tz = t - (pl.tiempos[z.i] - pl.t0)
            m = muelle(tz, 3.4, 10)
            s = 0.35 + 0.65 * m
            giro = (1 - min(1.0, m)) * entre(-14, 14, pl.semilla, z.i)
            if z.i == act:
                s *= 1.09 + 0.05 * cx.golpe
                o["viva"][z.i].pintar(p, z.x, z.y - 3 * k * math.exp(-tz * 6), s, op * lim(tz / 0.05), giro)
            else:
                o["normal"][z.i].pintar(p, z.x, z.y, 1.0, op, 0)
        p.restore()


def vivo_caja(c):
    """El color de la caja: oscurecido lo justo para que el texto blanco con borde mande."""
    return QColor(int(c.red() * 0.82), int(c.green() * 0.74), int(c.blue() * 0.86))


class Poster(Diseno):
    CLAVE = "poster"
    NOMBRE = "Póster cinético"
    DETALLE = "El verso se arma en filas enormes que entran chocando, como un cartel vivo"
    FUENTE = "bebas"
    PALABRAS = 8
    LETRAS = 40
    SALIDA = 0.26

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        n = len(textos)
        letras = sum(len(x) for x in textos)
        filas = 1 if n == 1 else 2 if letras <= 13 or n == 2 else 3 if letras <= 28 else 4
        filas = min(filas, n)
        anchos = [max(1.0, trazo(x, f).boundingRect().width()) + 24 for x in textos]
        from .base import _particiones
        grupos = _particiones(anchos, filas)
        W, H = cx.w * 0.88, cx.h * 0.80
        hueco = 12 * cx.k
        crudos = []
        for g in grupos:
            t = trazo(" ".join(textos[i] for i in g), f)
            r = t.boundingRect()
            crudos.append((g, t, r.width(), r.height()))
        # cada fila, del mismo ancho: las cortas salen enormes (con un tope para que no aplasten al resto)
        altos = [min(h * W / w, H * (0.56 if len(crudos) > 1 else 0.8)) for _g, _t, w, h in crudos]
        total = sum(altos) + hueco * (len(crudos) - 1)
        f_alto = min(1.0, H / total)
        altos = [a * f_alto for a in altos]
        total = sum(altos) + hueco * (len(crudos) - 1)
        y = -total / 2
        modos = [("lleno", "acento", "hueco", "caja"), ("caja", "lleno", "acento", "hueco"),
                 ("acento", "caja", "lleno", "hueco")][pl.linea % 3]
        if len(crudos) == 1:
            modos = ("lleno",)
        k = cx.k
        filas_o = []
        for j, ((g, t, w, h), alto) in enumerate(zip(crudos, altos)):
            s = alto / h
            sx = min(W / w, s * 1.5)                 # se estira a lo ancho, como en los carteles, pero no sin fin
            t2 = escalar(t, sx, s)
            modo = modos[j % len(modos)]

            def pintor(q, tinta, t, modo=modo):
                if modo == "caja":
                    r = t.boundingRect().adjusted(-10 * k, -6 * k, 10 * k, 6 * k)
                    q.setPen(Qt.NoPen)
                    q.setBrush(alfa(NEGRO, 90))
                    q.drawRect(r.translated(5 * k, 6 * k))
                    q.setBrush(cx.a)
                    q.drawRect(r)
                    relleno(q, t, QColor(14, 10, 20))
                    return
                sombra(q, tinta, k, 1.0, 4)
                if modo == "hueco":
                    borde(q, t, QColor(8, 6, 14), 8 * k)
                    borde(q, t, BLANCO, 4.4 * k)
                    vaciar(q, t, 46)
                else:
                    borde(q, t, QColor(8, 6, 14), 3.4 * k)
                    relleno(q, t, BLANCO if modo == "lleno" else
                            diagonal(t, (0, claro(cx.a, 0.25)), (0.5, cx.a), (1, cx.b)))
            cy = y + alto / 2
            filas_o.append({"sello": sello(t2, pintor, 22 * k, cx.dpr), "y": cy, "alto": alto,
                            "t": pl.tiempos[g[0]] - pl.t0, "w": w * sx, "modo": modo,
                            "blanco": sello(t2, lambda q, ti, t: relleno(q, t, BLANCO), 8 * k, cx.dpr)})
            y += alto + hueco
        return {"filas": filas_o}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        av = lim(t / max(0.6, pl.dur))
        lado = 1 if pl.linea % 2 else -1
        p.save()
        p.rotate(lado * mezcla(3.4, 1.2, out_cubic(av)))
        z = (1.0 + 0.05 * av) * (1 + 0.018 * cx.golpe) * (1 + 0.15 * in_cubic(u))
        p.scale(z, z)
        for j, fila in enumerate(o["filas"]):
            # la primera fila entra con el plano; las demás, cuando se canta su primera palabra
            tz = t - fila["t"]
            if tz < 0:
                continue
            d = 1 if (j + pl.linea) % 2 else -1
            e = out_expo(tz / 0.34)
            dx = d * (1 - e) * cx.w * 0.75 - d * in_cubic(u) * cx.w * 0.9
            s = 1.0 + 0.22 * (1 - e)
            dy = 0.0
            for j2 in range(j + 1, len(o["filas"])):      # cuando cae la de abajo, las de arriba dan un brinco
                t2 = t - o["filas"][j2]["t"]
                if 0 < t2 < 0.3:
                    dy -= 5 * cx.k * math.exp(-t2 * 14) * math.cos(t2 * 40)
            op = (1 - u) * lim(tz / 0.06)
            if tz < 0.12:
                fila["sello"].pintar(p, dx + d * cx.w * 0.10, fila["y"] + dy, s, op * 0.22, sy=1.0)
            fila["sello"].pintar(p, dx, fila["y"] + dy, s, op, sy=1.0)
            if fila["modo"] != "caja":
                fila["blanco"].pintar(p, dx, fila["y"] + dy, s, op * 0.8 * math.exp(-tz * 11), sy=1.0)
        p.restore()


class Eco(Diseno):
    CLAVE = "eco"
    NOMBRE = "Eco fluido"
    DETALLE = "La palabra se repite en contornos que se deslizan despacio a los lados"
    FUENTE = "anton"
    PALABRAS = 2
    LETRAS = 11
    SALIDA = 0.12

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = trazo(" ".join(textos), f)
        r = t.boundingRect()
        s = min(cx.w * 0.80 / r.width(), cx.h * 0.36 / r.height())
        t = escalar(t, s)
        k = cx.k
        r = t.boundingRect()

        def lleno(q, tinta, t):
            sombra(q, tinta, k, 1.2, 4)
            tinta.difusa(q, cx.a, 16 * k, 0.6)
            borde(q, t, QColor(8, 6, 14), 5 * k)
            relleno(q, t, diagonal(t, (0, BLANCO), (0.55, claro(cx.a, 0.35)), (1, cx.a)))
        return {"lleno": sello(t, lleno, 30 * k, cx.dpr),
                "hueco": sello(t, lambda q, ti, t: (borde(q, t, alfa(NEGRO, 150), 6.5 * k), borde(q, t, BLANCO, 3.6 * k),
                                                    vaciar(q, t, 26)), 6 * k, cx.dpr),
                "color": sello(t, lambda q, ti, t: (borde(q, t, alfa(NEGRO, 150), 6.5 * k), borde(q, t, cx.a, 3.8 * k),
                                                    vaciar(q, t, 26)), 6 * k, cx.dpr),
                "blanco": sello(t, lambda q, ti, t: relleno(q, t, BLANCO), 6 * k, cx.dpr),
                "w": r.width(), "h": r.height()}

    FILAS = 2                       # ecos a cada lado (arriba y abajo)
    OPACIDADES = (0.55, 0.24)
    VELOCIDAD = 1.0
    ESPEJO = False                  # solo debajo y del revés, como un reflejo
    SOLO_COLOR = False              # todos los ecos del color de la carátula

    def pintar(self, p, pl, o, t, cx):
        # fluido: los ecos se abren despacio y se deslizan en calma; la palabra entra sin golpe
        u = self._salida(pl, t)
        abre = out_cubic(t / 0.55) * (1 - in_cubic(u))
        paso = o["h"] * 1.18
        ancho = o["w"] + 40 * cx.k
        medio = int(cx.h / 2 / paso) + 1
        n = min(self.FILAS, medio)
        filas = range(1, n + 1) if self.ESPEJO else [k for k in range(-n, n + 1) if k]
        for k in filas:
            d = 1 if k % 2 else -1
            y = k * paso * abre * (1 + 0.025 * cx.golpe)
            op = self.OPACIDADES[min(abs(k), len(self.OPACIDADES)) - 1] * (1 - u) * lim(t / 0.3)
            quien = o["color"] if self.SOLO_COLOR or (k + pl.n) % 2 else o["hueco"]
            vel = (26 + 34 * math.exp(-t * 2.5) + 10 * cx.energia) * cx.k * self.VELOCIDAD
            if self.ESPEJO:
                d = 0                                        # el reflejo no corre: se mece
            x = -cx.w / 2 + (d * t * vel + pl.semilla * 13) % ancho - ancho / 2 if d else 0.0
            ola = math.sin(t * 1.6 + k) * 3 * cx.k
            if self.ESPEJO:
                quien.pintar(p, x + ola, y, 1.0, op, sy=-1.0)
                continue
            while x < cx.w / 2 + ancho / 2:
                quien.pintar(p, x, y + ola, 1.0, op)
                x += ancho
        e = out_cubic(t / 0.38)
        s = (1.12 - 0.12 * e) * (1 + 0.02 * cx.golpe) * (1 - 0.12 * u)
        dx, dy, g = temblor(max(0.0, t - 0.04), 2.5 * cx.k, 10, pl.semilla)
        # entra cuando la anterior ya se fue: nunca dos palabras grandes una encima de otra
        llega = lim((t - 0.10) / 0.18)
        o["lleno"].pintar(p, dx, dy - (1 - e) * 10 * cx.k, s, (1 - u) * llega, g)
        o["blanco"].pintar(p, dx, dy, s, 0.6 * (1 - u) * llega * math.exp(-t * 9), g)


class EcoSuave(Eco):
    CLAVE = "eco_suave"
    NOMBRE = "Eco suave"
    DETALLE = "Un solo eco a cada lado, muy tenue: acompaña sin distraer"
    FILAS = 1
    OPACIDADES = (0.30,)
    VELOCIDAD = 0.6


class EcoEspejo(Eco):
    CLAVE = "eco_espejo"
    NOMBRE = "Eco espejo"
    DETALLE = "La palabra se refleja debajo, como en agua, y se mece despacio"
    FILAS = 2
    OPACIDADES = (0.40, 0.16)
    ESPEJO = True


class EcoColor(Eco):
    CLAVE = "eco_color"
    NOMBRE = "Eco de color"
    DETALLE = "Los ecos toman el color de la carátula y corren en calma"
    FILAS = 2
    OPACIDADES = (0.50, 0.26)
    SOLO_COLOR = True
    VELOCIDAD = 0.8


class EcoFrase(Eco):
    CLAVE = "eco_frase"
    NOMBRE = "Eco de frase"
    DETALLE = "Como el Eco fluido, con más palabras a la vez: se lee la frase entera"
    PALABRAS = 4
    LETRAS = 20
    FILAS = 1
    OPACIDADES = (0.38,)
    VELOCIDAD = 0.7


class Tunel(Diseno):
    CLAVE = "tunel"
    NOMBRE = "Hiperespacio"
    DETALLE = "Las palabras llegan volando desde el fondo y te atraviesan"
    FUENTE = "russo"
    PALABRAS = 2
    LETRAS = 12
    SALIDA = 0.30

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.76, cx.h * 0.56, 2, 0.26, 0.14))
        k = cx.k

        def lleno(q, tinta, t):
            sombra(q, tinta, k, 0.9, 3)
            for r, fz in ((26, 0.9), (13, 0.9), (6, 0.8)):
                tinta.difusa(q, cx.a, r * k, fz)
            borde(q, t, oscuro(cx.a, 0.75), 4 * k)
            relleno(q, t, vertical(t, (0, BLANCO), (0.5, claro(cx.b, 0.7)), (1, claro(cx.a, 0.25))))
        return {"lleno": sello(t, lleno, 40 * k, cx.dpr)}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        R = math.hypot(cx.w, cx.h) * 0.55
        vel = 0.30 + 1.9 * math.exp(-t * 4.5) + 0.7 * cx.golpe + 1.6 * u
        op_l = (1 - u) * lim(t / 0.1)
        # estrellas que pasan: dos tandas de trazos, cada una de un grosor
        for tanda, (grosor, color) in enumerate(((1.2, BLANCO), (2.2, claro(cx.a, 0.4)))):
            camino = QPainterPath()
            for i in range(22):
                ang = azar(i, tanda, 3) * 2 * math.pi
                z = (azar(i, tanda, 5) + t * (0.55 + 0.5 * azar(i, tanda, 7))) % 1.0
                r0 = R * (0.10 + 0.95 * z * z)
                r1 = r0 + R * 0.05 * (0.3 + 2.4 * z) * (0.5 + vel)
                c, s = math.cos(ang), math.sin(ang) * 0.72
                camino.moveTo(c * r0, s * r0)
                camino.lineTo(c * r1, s * r1)
            p.setPen(QPen(alfa(color, 150 * op_l), grosor * cx.k, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawPath(camino)
        e = out_quint(t / 0.42)
        z = (1 - e) * 13.0
        s = 1.0 / (1.0 + z)
        s *= (1 + 0.12 * lim(t / max(0.5, pl.dur))) * (1 + 0.04 * cx.golpe)
        giro = (1 - e) * entre(-40, 40, pl.semilla)
        x0, y0 = entre(-0.25, 0.25, pl.semilla, 2) * cx.w * (1 - e), entre(-0.3, 0.3, pl.semilla, 3) * cx.h * (1 - e)
        if u > 0:
            s *= 1 + 5.5 * u * u
            o["lleno"].pintar(p, 0, 0, s * 0.86, (1 - u) ** 2 * 0.35, 0)
            o["lleno"].pintar(p, 0, 0, s, (1 - u) ** 1.6, 0)
            return
        if t < 0.30:
            for j in (3, 2, 1):
                tj = max(0.0, t - 0.028 * j)
                ej = out_quint(tj / 0.42)
                sj = 1.0 / (1.0 + (1 - ej) * 13.0)
                o["lleno"].pintar(p, x0, y0, sj, 0.13 * lim(tj / 0.05), giro)
        o["lleno"].pintar(p, x0, y0, s, lim(t / 0.07), giro)


class Phonk(Diseno):
    CLAVE = "phonk"
    NOMBRE = "Phonk"
    DETALLE = "Derrape rojo y negro: entra de lado, deja humo y tiembla con cada bajo"
    FUENTE = "shrikhand"
    PALABRAS = 3
    LETRAS = 15
    SALIDA = 0.18

    ROJO = QColor("#FF1E3C")

    def preparar(self, pl, cx):
        textos, f = self._textos(pl)
        t = unir(bloque(textos, f, cx.w * 0.82, cx.h * 0.60, 2, 0.22, 0.12, sesgo=0.16))
        k = cx.k
        rojo = self.ROJO

        def lleno(q, tinta, t):
            tinta.difusa(q, NEGRO, 16 * k, 1.2, 0, 4 * k)
            tinta.difusa(q, rojo, 22 * k, 0.8)
            extrusion(q, tinta, rojo, QColor(60, 0, 12), 10 * k, math.radians(38))
            borde(q, t, NEGRO, 6 * k)
            relleno(q, t, vertical(t, (0, BLANCO), (0.48, QColor(235, 232, 240)), (0.52, QColor(150, 146, 162)),
                                   (1, QColor(245, 240, 250))))
            # arañazos
            q.save()
            q.setClipPath(t)
            r = t.boundingRect()
            q.setPen(QPen(QColor(10, 6, 12, 190), 1.6 * k))
            for i in range(16):
                y = r.top() + r.height() * azar(pl.semilla, i)
                x = r.left() + r.width() * azar(pl.semilla, i, 2)
                lg = r.width() * (0.05 + 0.16 * azar(pl.semilla, i, 3))
                q.drawLine(QPointF(x, y), QPointF(x + lg, y - lg * 0.30))
            q.restore()
        m = 36 * k
        return {"lleno": sello(t, lleno, m, cx.dpr),
                "rojo": sello(t, lambda q, ti, t: relleno(q, t, rojo), m, cx.dpr),
                "negro": sello(t, lambda q, ti, t: relleno(q, t, QColor(0, 0, 0)), m, cx.dpr),
                "bajo": t.boundingRect().bottom()}

    def pintar(self, p, pl, o, t, cx):
        u = self._salida(pl, t)
        d = 1 if pl.n % 2 else -1
        e = out_expo(t / 0.26)
        x = d * (1 - e) * cx.w * 0.95 - d * in_cubic(u) * cx.w * 1.1
        sesgo = -d * 0.75 * (1 - e) + d * 0.5 * u
        golpe = cx.golpe
        paso = int(t * 24)
        tx = (azar(paso, pl.semilla) - 0.5) * (3 + 22 * golpe) * cx.k
        ty = (azar(paso, pl.semilla, 2) - 0.5) * (2 + 15 * golpe) * cx.k
        g = (azar(paso, pl.semilla, 3) - 0.5) * 3.5 * golpe - d * 3 * (1 - e)
        s = 1 + 0.075 * golpe + 0.03 * lim(t)
        op = (1 - u) * lim(t / 0.04)
        # resplandor rojo que late detrás
        punto(p, mancha(self.ROJO, 48), 0, 0, cx.w * 0.55, op * (0.20 + 0.40 * golpe))
        p.setOpacity(1)
        # humo del derrape
        humo = mancha(QColor(210, 205, 215), 32)
        for i in range(14):
            v = (t * 0.9 + azar(i, pl.semilla)) % 1.0
            px_ = x + d * (0.1 + 0.42 * v + 0.2 * azar(i, 4)) * cx.w * 0.75
            py_ = o["bajo"] - 6 * cx.k - v * 46 * cx.k * azar(i, 6)
            punto(p, humo, px_, py_, (14 + 46 * v) * cx.k, op * 0.20 * (1 - v) * (0.35 + math.exp(-t * 1.6)))
        p.setOpacity(1)
        if t < 0.3:
            for j in (4, 3, 2, 1):
                o["rojo" if j % 2 else "negro"].pintar(p, x + d * j * 26 * cx.k * (1 - e) * 6, ty, s, op * 0.17, g, sesgo=sesgo)
        desv = (3 + 13 * golpe) * cx.k
        o["rojo"].pintar(p, x + tx - desv, ty + desv * 0.3, s, op * 0.75, g, sesgo=sesgo)
        o["lleno"].pintar(p, x + tx, ty, s, op, g, sesgo=sesgo)


DISENOS = (Impacto, Viral, Poster, Eco, Tunel, Phonk)
