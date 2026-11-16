# -*- coding: utf-8 -*-
"""Tarjeta vertical (9:16, 1080x1920) con el perfil completo de una persona de Caudal.

Pensada para un estado de WhatsApp o una historia de Instagram. Se dibuja con QPainter en un
QImage (sin widgets) y el contenido se ajusta al espacio: si hay mucho se reducen los tamaños,
si falta algo no se dejan huecos.

    img = generar(perfil, estilo="color", imagenes=traer_imagenes(perfil))   # QImage
    img, info = generar_con_info(...)      # info: escala usada, cajas de texto, bloques (para pruebas)

`perfil` es lo que devuelve Social.ver_perfil (ya limpio). `imagenes` es un diccionario de QImage
con las claves «foto», «banner», «cancion» y «top0».. «top2»; lo que falte se dibuja sin imagen.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPolygonF, QRadialGradient)

from . import social as S

ANCHO, ALTO = 1080, 1920
MARGEN = 84
ANCHO_UTIL = ANCHO - 2 * MARGEN
ZONA_ARRIBA = 96          # donde empieza la cabecera (logo)
CABECERA = 72
ZONA_CUERPO = (212, 1752)  # de dónde a dónde se reparte el contenido
Y_PIE = 1812

ESTILOS = {"color": "Color del perfil", "oscuro": "Oscuro", "claro": "Claro"}
FAMILIAS = ["Segoe UI Variable Display", "Segoe UI", "Arial"]


# ------------------------------------------------------------------ colores y fuentes

def _mezcla(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


def _alfa(c, a):
    c = QColor(c)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


def _luz(c):
    c = QColor(c)
    return (0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()) / 255


def _fuente(px, peso=QFont.Normal, cursiva=False, espacio=0.0):
    f = QFont()
    f.setFamilies(FAMILIAS)
    f.setPixelSize(max(6, int(round(px))))
    f.setWeight(peso)
    f.setItalic(cursiva)
    f.setHintingPreference(QFont.PreferNoHinting)
    if espacio:
        f.setLetterSpacing(QFont.AbsoluteSpacing, espacio)
    return f


def paleta(estilo, color):
    """Colores de cada estilo. `color` es el del perfil (QColor)."""
    if estilo == "claro":
        texto = QColor("#14161B")
        return {
            "claro": True, "texto": texto, "texto2": QColor("#4A5161"), "texto3": QColor("#7A8294"),
            "acento": color, "etiqueta": _mezcla(color, "#000000", 0.38),
            "tarjeta": QColor(255, 255, 255, 190), "borde": QColor(20, 24, 40, 28),
            "chip": _alfa(color, 0.14), "chip_borde": _alfa(_mezcla(color, "#000000", 0.2), 0.45),
            "fondo_arriba": _mezcla("#FFFFFF", color, 0.20), "fondo_abajo": _mezcla("#F6F4F0", color, 0.05),
            "hueco": QColor("#FFFFFF"), "texto_acento": _mezcla(color, "#000000", 0.45),
        }
    base_a, base_b = (QColor("#0A0C11"), QColor("#10131A")) if estilo == "oscuro" else (None, None)
    if estilo == "oscuro":
        fondo_arriba, fondo_abajo = _mezcla(base_a, color, 0.07), base_b
    else:
        fondo_arriba = _mezcla("#0A0C11", color, 0.50)
        fondo_abajo = _mezcla("#0A0C11", color, 0.11)
    return {
        "claro": False, "texto": QColor("#F6F8FB"), "texto2": QColor("#C3CAD6"), "texto3": QColor("#8B94A5"),
        "acento": color, "etiqueta": _mezcla(color, "#FFFFFF", 0.35),
        "tarjeta": QColor(255, 255, 255, 22), "borde": QColor(255, 255, 255, 34),
        "chip": _alfa(color, 0.20), "chip_borde": _alfa(_mezcla(color, "#FFFFFF", 0.25), 0.55),
        "fondo_arriba": fondo_arriba, "fondo_abajo": fondo_abajo,
        "hueco": _mezcla("#0A0C11", color, 0.15), "texto_acento": _mezcla(color, "#FFFFFF", 0.4),
    }


# ------------------------------------------------------------------ texto

def _limpiar(t):
    return " ".join(str(t or "").split())


def envolver(texto, fm, ancho, max_lineas):
    """Parte el texto en líneas que caben en `ancho`; si sobra, la última acaba en «…»."""
    palabras = _limpiar(texto).split(" ")
    if palabras == [""]:
        return []
    ancho = int(ancho)
    lineas, actual, i = [], "", 0
    while i < len(palabras):
        w = palabras[i]
        prueba = f"{actual} {w}" if actual else w
        if fm.horizontalAdvance(prueba) <= ancho:
            actual = prueba
            i += 1
            continue
        if actual:
            lineas.append(actual)
            actual = ""
        else:                       # una palabra más ancha que la línea
            lineas.append(fm.elidedText(w, Qt.ElideRight, ancho))
            i += 1
        if len(lineas) == max_lineas:
            break
    if actual and len(lineas) < max_lineas:
        lineas.append(actual)
    if i < len(palabras) and lineas:
        lineas[-1] = fm.elidedText(lineas[-1] + " " + " ".join(palabras[i:]), Qt.ElideRight, ancho)
    return lineas


class Lienzo:
    """Pinta (o sólo mide) la tarjeta. `k` es la escala del contenido."""

    def __init__(self, p, pal, perfil, imagenes, k, pintor):
        self.pal, self.d, self.imgs, self.k, self.p = pal, perfil, imagenes or {}, k, pintor
        self.dibujar = True
        self.cajas = []          # (x, y, ancho, alto, texto) de cada texto pintado
        self.recortados = []     # textos que hubo que acortar con «…»
        self.color = QColor(perfil.get("color_perfil") or "#22D3EE")
        self.pos = {}

    def s(self, v):
        return int(round(v * self.k))

    # --- primitivas
    def texto(self, x, y, ancho, texto, fuente, color, alinear=Qt.AlignHCenter, sombra=False):
        fm = QFontMetrics(fuente)
        if self.dibujar:
            self.p.setFont(fuente)
            r = QRectF(x, y, ancho, fm.height())
            self.p.setPen(color)
            self.p.drawText(r, int(alinear | Qt.AlignVCenter | Qt.TextSingleLine), texto)
            w = fm.horizontalAdvance(texto)
            if alinear == Qt.AlignHCenter:
                x0 = x + (ancho - w) / 2
            elif alinear == Qt.AlignRight:
                x0 = x + ancho - w
            else:
                x0 = x
            self.cajas.append((x0, y, w, fm.height(), texto))
        return fm.height()

    def parrafo(self, x, y, ancho, texto, fuente, color, max_lineas, alinear=Qt.AlignHCenter, interlinea=1.22):
        fm = QFontMetrics(fuente)
        lineas = envolver(texto, fm, ancho, max_lineas)
        paso = int(fm.height() * interlinea)
        if any(l.endswith("…") for l in lineas) and self.dibujar:
            self.recortados.append(_limpiar(texto))
        for i, l in enumerate(lineas):
            self.texto(x, y + i * paso, ancho, l, fuente, color, alinear)
        return paso * len(lineas) - (paso - fm.height() if lineas else 0), len(lineas)

    def fila_centrada(self, elementos, y, hueco, alto, max_filas=9):
        """elementos: [(ancho, pintar(x, y))]; los reparte en filas centradas. Devuelve el alto."""
        filas, fila, usado = [], [], 0
        for e in elementos:
            if fila and usado + hueco + e[0] > ANCHO_UTIL:
                filas.append(fila)
                fila, usado = [], 0
            fila.append(e)
            usado += e[0] + (hueco if len(fila) > 1 else 0)
        if fila:
            filas.append(fila)
        filas = filas[:max_filas]
        for n, f in enumerate(filas):
            total = sum(e[0] for e in f) + hueco * (len(f) - 1)
            x = (ANCHO - total) / 2
            for e in f:
                if self.dibujar:
                    e[1](x, y + n * (alto + hueco))
                x += e[0] + hueco
        return len(filas) * alto + max(0, len(filas) - 1) * hueco if filas else 0

    def tarjeta(self, x, y, w, h, radio=30):
        if not self.dibujar:
            return
        p = self.p
        r = QRectF(x, y, w, h)
        if self.pal["claro"]:
            sombra = QRectF(x, y + 8, w, h)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(30, 30, 60, 14))
            p.drawRoundedRect(sombra, radio, radio)
        p.setPen(QPen(self.pal["borde"], 1.6))
        p.setBrush(self.pal["tarjeta"])
        p.drawRoundedRect(r, radio, radio)

    def imagen_en(self, img, ruta, x, y, w, h):
        """Pinta `img` recortada para llenar el rectángulo (como object-fit: cover) dentro de `ruta`."""
        p = self.p
        p.save()
        p.setClipPath(ruta)
        esc = img.scaled(int(w), int(h), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawImage(int(x), int(y), esc, (esc.width() - int(w)) // 2, (esc.height() - int(h)) // 2,
                    int(w), int(h))
        p.restore()

    def icono(self, nombre, lado, color, x, y):
        from .ui import iconos
        pm = iconos.pixmap(nombre, int(lado), color.name())
        self.p.drawPixmap(int(x), int(y), pm)

    def etiqueta_seccion(self, y, texto):
        f = _fuente(self.s(23), QFont.Bold, espacio=self.s(4))
        return self.texto(MARGEN, y, ANCHO_UTIL, texto, f, self.pal["etiqueta"])

    # --- bloques (cada uno pinta en y y devuelve su alto; con dibujar=False sólo mide)
    def b_cabecera(self, y):
        from .ui import iconos
        if self.dibujar:
            logo = iconos.icono_app(160).scaled(CABECERA, CABECERA, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.p.drawPixmap(MARGEN, y, logo)
            f = _fuente(44, QFont.Black, espacio=1)
            self.texto(MARGEN + CABECERA + 16, y + (CABECERA - QFontMetrics(f).height()) // 2, 400,
                       "Caudal", f, self.pal["texto"], Qt.AlignLeft)
            n = self.d.get("numero")
            if n:
                f2 = _fuente(28, QFont.Bold)
                txt = f"Usuario N.º {n}"
                w = QFontMetrics(f2).horizontalAdvance(txt) + 48
                h = 54
                x = ANCHO - MARGEN - w
                yy = y + (CABECERA - h) // 2
                self.p.setPen(QPen(self.pal["chip_borde"], 1.8))
                self.p.setBrush(self.pal["chip"])
                self.p.drawRoundedRect(QRectF(x, yy, w, h), h / 2, h / 2)
                self.texto(x, yy + (h - QFontMetrics(f2).height()) // 2, w, txt, f2, self.pal["texto"])
        return CABECERA

    def b_avatar(self, y):
        d = self.s(270)
        if self.dibujar:
            p = self.p
            cx, cy = ANCHO / 2, y + d / 2
            col = self.color
            # resplandor
            g = QRadialGradient(QPointF(cx, cy), d * 0.95)
            g.setColorAt(0.5, _alfa(col, 0.50 if not self.pal["claro"] else 0.32))
            g.setColorAt(1.0, _alfa(col, 0.0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), d * 0.95, d * 0.95)
            # aro del color del perfil
            aro = max(6, self.s(10))
            p.setBrush(col)
            p.drawEllipse(QPointF(cx, cy), d / 2, d / 2)
            sep = max(4, self.s(7))
            p.setBrush(self.pal["hueco"])
            p.drawEllipse(QPointF(cx, cy), d / 2 - aro, d / 2 - aro)
            r = d / 2 - aro - sep
            ruta = QPainterPath()
            ruta.addEllipse(QPointF(cx, cy), r, r)
            foto = self.imgs.get("foto")
            if foto is not None and not foto.isNull():
                self.imagen_en(foto, ruta, cx - r, cy - r, 2 * r, 2 * r)
            else:
                g2 = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
                g2.setColorAt(0, _mezcla(col, "#FFFFFF", 0.22))
                g2.setColorAt(1, _mezcla(col, "#000000", 0.25))
                p.setBrush(g2)
                p.drawEllipse(QPointF(cx, cy), r, r)
                ini = (S.nombre_visible(self.d).strip()[:1] or "?").upper()
                p.setPen("#101114" if _luz(col) > 0.55 else "#FFFFFF")
                p.setFont(_fuente(r * 0.95, QFont.Black))
                p.drawText(QRectF(cx - r, cy - r, 2 * r, 2 * r), int(Qt.AlignCenter), ini)
        return d

    def b_nombre(self, y):
        nombre = S.nombre_visible(self.d)
        f = _fuente(self.s(70), QFont.Black)
        h, n = self.parrafo(MARGEN, y, ANCHO_UTIL, nombre, f, self.pal["texto"], 2, interlinea=1.04)
        f2 = _fuente(self.s(34), QFont.DemiBold)
        usuario = "@" + (self.d.get("usuario") or "")
        gap = self.s(8)
        h2 = self.texto(MARGEN, y + h + gap, ANCHO_UTIL,
                        QFontMetrics(f2).elidedText(usuario, Qt.ElideRight, ANCHO_UTIL), f2, self.pal["texto_acento"])
        return h + gap + h2

    def b_chips(self, y):
        titulos = S.titulos_de(self.d)
        if not titulos:
            return 0
        alto = self.s(52)
        f = _fuente(self.s(25), QFont.Bold, espacio=self.s(1))
        fm = QFontMetrics(f)
        elementos = []
        for clave, txt in titulos:
            txt = txt.replace("★", "").strip()
            txt = txt.upper() if clave in ("fundador_caudal", "rey_de_la_musica", "artista") else txt
            txt = fm.elidedText(txt, Qt.ElideRight, ANCHO_UTIL - self.s(120))
            icono_w = alto * 0.55
            w = fm.horizontalAdvance(txt) + self.s(34) + icono_w + self.s(14)
            elementos.append((w, lambda x, yy, c=clave, t=txt, w=w: self._chip_titulo(x, yy, w, alto, c, t, f)))
        return self.fila_centrada(elementos, y, self.s(14), alto, 3)

    def _chip_titulo(self, x, y, w, h, clave, txt, f):
        p = self.p
        oro = QColor(S.COLOR_ARTISTA)
        cian = QColor("#22D3EE")
        if clave == "fundador_caudal":
            g = QLinearGradient(x, 0, x + w, 0)
            g.setColorAt(0, cian)
            g.setColorAt(1, oro)
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            col_txt = QColor("#101114")
        elif clave == "rey_de_la_musica":
            g = QLinearGradient(x, 0, x + w, 0)
            g.setColorAt(0, QColor("#FFD95E"))
            g.setColorAt(1, QColor("#FF9F1C"))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            col_txt = QColor("#3A2600")
        elif clave == "fundador":
            p.setPen(QPen(_alfa(oro, 0.8), 2))
            p.setBrush(_alfa(oro, 0.14 if not self.pal["claro"] else 0.22))
            col_txt = self.pal["texto"] if not self.pal["claro"] else QColor("#5A4000")
        else:
            g = QLinearGradient(x, y, x + w, y + h)
            g.setColorAt(0, QColor("#FFE27A"))
            g.setColorAt(1, oro)
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            col_txt = QColor("#3A2600")
        p.drawRoundedRect(QRectF(x, y, w, h), h / 2, h / 2)
        ic = h * 0.5
        ix, iy = x + h * 0.36, y + (h - ic) / 2
        p.setPen(Qt.NoPen)
        p.setBrush(col_txt if clave != "fundador" else oro)
        if clave == "rey_de_la_musica":
            e = ic / 14
            p.drawPolygon(QPolygonF([QPointF(ix + 1 * e, iy + 12 * e), QPointF(ix + 1.5 * e, iy + 4 * e),
                                     QPointF(ix + 4.5 * e, iy + 8 * e), QPointF(ix + 7 * e, iy + 3 * e),
                                     QPointF(ix + 9.5 * e, iy + 8 * e), QPointF(ix + 12.5 * e, iy + 4 * e),
                                     QPointF(ix + 13 * e, iy + 12 * e)]))
        elif clave == "fundador_caudal":
            from .ui import iconos
            p.drawPixmap(int(ix - 2), int(iy - 2), iconos.icono_app(int(ic + 6)))
        else:
            self._estrella(ix + ic / 2, iy + ic / 2, ic / 2)
        self.texto(x + h * 0.36 + ic + self.s(14), y + (h - QFontMetrics(f).height()) // 2, w, txt, f, col_txt,
                   Qt.AlignLeft)

    def _estrella(self, cx, cy, r):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append(QPointF(cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        self.p.drawPolygon(QPolygonF(pts))

    def b_frase(self, y):
        frase = _limpiar(self.d.get("frase"))
        if not frase:
            return 0
        f = _fuente(self.s(40), QFont.Medium, cursiva=True)
        h, _n = self.parrafo(MARGEN + self.s(30), y, ANCHO_UTIL - self.s(60), f"“{frase}”", f,
                             self.pal["texto"], 3, interlinea=1.2)
        return h

    def b_bio(self, y):
        bio = _limpiar(self.d.get("bio"))
        if not bio:
            return 0
        f = _fuente(self.s(31), QFont.Normal)
        ancho = ANCHO_UTIL - self.s(30)
        fm = QFontMetrics(f)
        lineas = envolver(bio, fm, ancho - self.s(64), 5)
        paso = int(fm.height() * 1.28)
        alto = len(lineas) * paso - (paso - fm.height()) + self.s(56)
        ancho_t = max(fm.horizontalAdvance(l) for l in lineas) if lineas else 0
        ancho = min(ancho, max(self.s(420), ancho_t + self.s(96)))
        x_card = (ANCHO - ancho) / 2
        self.tarjeta(x_card, y, ancho, alto, self.s(28))
        if any(l.endswith("…") for l in lineas) and self.dibujar:
            self.recortados.append(bio)
        for i, l in enumerate(lineas):
            self.texto(x_card + self.s(32), y + self.s(28) + i * paso, ancho - self.s(64), l, f,
                       self.pal["texto2"])
        return alto

    def b_numeros(self, y):
        d = self.d
        datos = []
        if d.get("likes"):
            datos.append((str(d["likes"]), "me gusta", "corazon_lleno"))
        if d.get("num_subidas"):
            datos.append((str(d["num_subidas"]), "canciones subidas", "musica"))
        if d.get("insignias"):
            datos.append((str(len(d["insignias"])), "insignias", "estrella"))
        if not datos:
            return 0
        alto = self.s(128)
        ancho = min(ANCHO_UTIL, len(datos) * self.s(304))
        x0 = (ANCHO - ancho) / 2
        self.tarjeta(x0, y, ancho, alto, self.s(32))
        col_w = ancho / len(datos)
        fn = _fuente(self.s(54), QFont.Black)
        fl = _fuente(self.s(23), QFont.DemiBold)
        for i, (num, rot, ic) in enumerate(datos):
            x = x0 + i * col_w
            if i and self.dibujar:
                self.p.setPen(QPen(self.pal["borde"], 2))
                self.p.drawLine(QPointF(x, y + alto * 0.22), QPointF(x, y + alto * 0.78))
            self.texto(x, y + self.s(14), col_w, num, fn, self.pal["texto"])
            if self.dibujar:
                fm = QFontMetrics(fl)
                w = fm.horizontalAdvance(rot)
                lado = self.s(22)
                xl = x + (col_w - (w + lado + self.s(8))) / 2
                yl = y + self.s(14) + QFontMetrics(fn).height() - self.s(2)
                self.icono(ic, lado, self.pal["acento"] if not self.pal["claro"] else self.pal["texto_acento"],
                           xl, yl + (fm.height() - lado) / 2)
                self.texto(xl + lado + self.s(8), yl, w + 4, rot, fl, self.pal["texto3"], Qt.AlignLeft)
        return alto

    def b_cancion(self, y):
        c = self.d.get("cancion_fav")
        if not c:
            return 0
        lado = self.s(176)
        pad = self.s(24)
        alto = lado + 2 * pad
        self.tarjeta(MARGEN, y, ANCHO_UTIL, alto, self.s(34))
        if self.dibujar:
            ruta = QPainterPath()
            ruta.addRoundedRect(QRectF(MARGEN + pad, y + pad, lado, lado), self.s(22), self.s(22))
            img = self.imgs.get("cancion")
            if img is not None and not img.isNull():
                self.p.setPen(Qt.NoPen)
                self.imagen_en(img, ruta, MARGEN + pad, y + pad, lado, lado)
            else:
                g = QLinearGradient(MARGEN + pad, y + pad, MARGEN + pad + lado, y + pad + lado)
                g.setColorAt(0, _mezcla(self.color, "#FFFFFF", 0.15))
                g.setColorAt(1, _mezcla(self.color, "#000000", 0.35))
                self.p.setPen(Qt.NoPen)
                self.p.setBrush(g)
                self.p.drawPath(ruta)
                self.icono("musica", lado * 0.42, QColor("#FFFFFF"), MARGEN + pad + lado * 0.29,
                           y + pad + lado * 0.29)
        x = MARGEN + pad + lado + self.s(28)
        w = ANCHO - MARGEN - pad - x
        fe = _fuente(self.s(22), QFont.Bold, espacio=self.s(3))
        ft = _fuente(self.s(40), QFont.Black)
        fa = _fuente(self.s(30), QFont.Medium)
        # el bloque de texto va centrado en vertical respecto a la carátula
        fm_t = QFontMetrics(ft)
        lineas_t = envolver(c["titulo"], fm_t, w, 2)
        paso_t = int(fm_t.height() * 1.08)
        h_texto = QFontMetrics(fe).height() + self.s(8) + len(lineas_t) * paso_t
        if c.get("artista"):
            h_texto += self.s(6) + QFontMetrics(fa).height()
        yy = y + (alto - h_texto) / 2
        yy += self.texto(x, int(yy), w, "MI CANCIÓN FAVORITA", fe, self.pal["etiqueta"], Qt.AlignLeft) + self.s(8)
        if any(l.endswith("…") for l in lineas_t) and self.dibujar:
            self.recortados.append(c["titulo"])
        for l in lineas_t:
            self.texto(x, int(yy), w, l, ft, self.pal["texto"], Qt.AlignLeft)
            yy += paso_t
        if c.get("artista"):
            yy += self.s(6)
            self.texto(x, int(yy), w, QFontMetrics(fa).elidedText(c["artista"], Qt.ElideRight, int(w)), fa,
                       self.pal["texto2"], Qt.AlignLeft)
        return alto

    def b_artista_fav(self, y):
        a = _limpiar(self.d.get("artista_fav"))
        if not a:
            return 0
        fe = _fuente(self.s(27), QFont.Medium)
        fn = _fuente(self.s(32), QFont.Black)
        fm1, fm2 = QFontMetrics(fe), QFontMetrics(fn)
        pref = "Artista favorito  "
        a_txt = fm2.elidedText(a, Qt.ElideRight, ANCHO_UTIL - fm1.horizontalAdvance(pref))
        total = fm1.horizontalAdvance(pref) + fm2.horizontalAdvance(a_txt)
        if a_txt != a and self.dibujar:
            self.recortados.append(a)
        h = max(fm1.height(), fm2.height()) + self.s(6)
        if self.dibujar:
            x = (ANCHO - total) / 2
            self.texto(x, y + (h - fm1.height()) // 2, fm1.horizontalAdvance(pref) + 4, pref, fe,
                       self.pal["texto3"], Qt.AlignLeft)
            self.texto(x + fm1.horizontalAdvance(pref), y + (h - fm2.height()) // 2, fm2.horizontalAdvance(a_txt) + 4,
                       a_txt, fn, self.pal["texto"], Qt.AlignLeft)
        return h

    def b_top(self, y):
        tops = [a for a in (self.d.get("top_artistas") or []) if a.get("nombre")][:3]
        if not tops:
            return 0
        h = self.etiqueta_seccion(y, "LO QUE MÁS ESCUCHO") + self.s(22)
        d = self.s(148)
        col_w = ANCHO_UTIL / 3
        fn = _fuente(self.s(27), QFont.Bold)
        fv = _fuente(self.s(22), QFont.Normal)
        fm = QFontMetrics(fn)
        total_w = col_w * len(tops)
        x_ini = (ANCHO - total_w) / 2
        for i, a in enumerate(tops):
            cx = x_ini + col_w * i + col_w / 2
            if self.dibujar:
                p = self.p
                ruta = QPainterPath()
                ruta.addEllipse(QPointF(cx, y + h + d / 2), d / 2, d / 2)
                p.setPen(Qt.NoPen)
                p.setBrush(_alfa(self.color, 0.9))
                p.drawEllipse(QPointF(cx, y + h + d / 2), d / 2 + 5, d / 2 + 5)
                img = self.imgs.get(f"top{i}")
                if img is not None and not img.isNull():
                    self.imagen_en(img, ruta, cx - d / 2, y + h, d, d)
                else:
                    g = QLinearGradient(cx - d / 2, y + h, cx + d / 2, y + h + d)
                    g.setColorAt(0, _mezcla(self.color, "#FFFFFF", 0.1))
                    g.setColorAt(1, _mezcla(self.color, "#000000", 0.4))
                    p.setBrush(g)
                    p.drawPath(ruta)
                    self.icono("usuario", d * 0.46, QColor("#FFFFFF"), cx - d * 0.23, y + h + d * 0.27)
            nombre = a["nombre"]
            elid = fm.elidedText(nombre, Qt.ElideRight, int(col_w - self.s(16)))
            if elid != nombre and self.dibujar:
                self.recortados.append(nombre)
            self.texto(cx - col_w / 2, y + h + d + self.s(14), col_w, elid, fn, self.pal["texto"])
            veces = a.get("veces")
            if veces:
                self.texto(cx - col_w / 2, y + h + d + self.s(14) + fm.height(), col_w,
                           f"{veces} {'vez' if veces == 1 else 'veces'}", fv, self.pal["texto3"])
        hh = h + d + self.s(14) + fm.height() + (QFontMetrics(fv).height()
                                                  if any(a.get("veces") for a in tops) else 0)
        return hh

    def b_generos(self, y):
        gen = [g for g in (self.d.get("generos") or []) if g][:5]
        if not gen:
            return 0
        alto = self.s(52)
        f = _fuente(self.s(26), QFont.DemiBold)
        fm = QFontMetrics(f)
        el = []
        for g in gen:
            t = fm.elidedText(g, Qt.ElideRight, ANCHO_UTIL - self.s(60))
            w = fm.horizontalAdvance(t) + self.s(44)
            el.append((w, lambda x, yy, t=t, w=w: self._chip_simple(x, yy, w, alto, t, f)))
        return self.fila_centrada(el, y, self.s(14), alto, 2)

    def _chip_simple(self, x, y, w, h, t, f):
        self.p.setPen(QPen(self.pal["chip_borde"], 1.6))
        self.p.setBrush(self.pal["chip"])
        self.p.drawRoundedRect(QRectF(x, y, w, h), h / 2, h / 2)
        self.texto(x, y + (h - QFontMetrics(f).height()) // 2, w, t, f, self.pal["texto"])

    def b_insignias(self, y):
        ins = self.d.get("insignias") or []
        if not ins:
            return 0
        h = self.etiqueta_seccion(y, "INSIGNIAS") + self.s(20)
        alto = self.s(58)
        f = _fuente(self.s(26), QFont.DemiBold)
        fm = QFontMetrics(f)
        el = []
        for i in ins[:6]:
            tit_def, icono, color = S.INSIGNIAS.get(i.get("clave"), (None, "estrella", "#C3CAD6"))
            t = fm.elidedText(i.get("titulo") or tit_def or "Insignia", Qt.ElideRight, ANCHO_UTIL - self.s(140))
            w = fm.horizontalAdvance(t) + self.s(40) + alto * 0.62
            el.append((w, lambda x, yy, t=t, w=w, ic=icono, c=color: self._chip_insignia(x, yy, w, alto, t, ic, c, f)))
        return h + self.fila_centrada(el, y + h, self.s(14), alto, 2)

    def _chip_insignia(self, x, y, w, h, t, icono, color, f):
        c = QColor(color)
        if self.pal["claro"]:
            c = _mezcla(c, "#000000", 0.2)
        self.p.setPen(QPen(_alfa(c, 0.55), 1.8))
        self.p.setBrush(_alfa(c, 0.16))
        self.p.drawRoundedRect(QRectF(x, y, w, h), h / 2, h / 2)
        circ = h * 0.62
        cx, cy = x + h * 0.19 + circ / 2, y + h / 2
        self.p.setPen(Qt.NoPen)
        self.p.setBrush(_alfa(c, 0.30))
        self.p.drawEllipse(QPointF(cx, cy), circ / 2, circ / 2)
        ic = circ * 0.62
        self.icono(icono, ic, c, cx - ic / 2, cy - ic / 2)
        self.texto(x + h * 0.19 + circ + self.s(12), y + (h - QFontMetrics(f).height()) // 2, w, t, f,
                   self.pal["texto"], Qt.AlignLeft)

    def pie(self):
        f = _fuente(34, QFont.DemiBold)
        y = Y_PIE
        if self.dibujar:
            self.p.setPen(QPen(_alfa(self.pal["etiqueta"], 0.8), 3, Qt.SolidLine, Qt.RoundCap))
            self.p.drawLine(QPointF(ANCHO / 2 - 40, y - 26), QPointF(ANCHO / 2 + 40, y - 26))
        self.texto(MARGEN, y, ANCHO_UTIL, "Escucha música gratis en Caudal", f, self.pal["texto"])


# ------------------------------------------------------------------ fondo

def _fondo(p, pal, estilo, color, banner, y_avatar):
    g = QLinearGradient(0, 0, 0, ALTO)
    g.setColorAt(0, pal["fondo_arriba"])
    g.setColorAt(1, pal["fondo_abajo"])
    p.fillRect(0, 0, ANCHO, ALTO, g)
    # imagen de fondo del perfil: tenue y desvanecida hacia abajo
    if banner is not None and not banner.isNull():
        alto = 1000
        capa = QImage(ANCHO, alto, QImage.Format_ARGB32_Premultiplied)
        capa.fill(Qt.transparent)
        q = QPainter(capa)
        q.setRenderHint(QPainter.SmoothPixmapTransform, True)
        esc = banner.scaled(ANCHO, alto, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        q.drawImage(0, 0, esc, (esc.width() - ANCHO) // 2, (esc.height() - alto) // 2, ANCHO, alto)
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        m = QLinearGradient(0, 0, 0, alto)
        tope = 0.60 if pal["claro"] else (0.30 if estilo == "oscuro" else 0.50)
        m.setColorAt(0, QColor(0, 0, 0, int(255 * tope)))
        m.setColorAt(0.55, QColor(0, 0, 0, int(255 * tope * 0.55)))
        m.setColorAt(1, QColor(0, 0, 0, 0))
        q.fillRect(0, 0, ANCHO, alto, m)
        q.end()
        p.drawImage(0, 0, capa)
    # resplandor del color del perfil detrás de la foto
    r = QRadialGradient(QPointF(ANCHO / 2, y_avatar), 760)
    r.setColorAt(0, _alfa(color, 0.34 if not pal["claro"] else 0.22))
    r.setColorAt(1, _alfa(color, 0.0))
    p.fillRect(0, 0, ANCHO, ALTO, r)
    # un destello suave abajo, para que el pie no quede en un fondo plano
    r2 = QRadialGradient(QPointF(ANCHO / 2, ALTO + 60), 640)
    r2.setColorAt(0, _alfa(color, 0.22 if not pal["claro"] else 0.14))
    r2.setColorAt(1, _alfa(color, 0.0))
    p.fillRect(0, 0, ANCHO, ALTO, r2)


# ------------------------------------------------------------------ composición

BLOQUES = ["avatar", "nombre", "chips", "frase", "bio", "numeros", "cancion", "artista_fav", "top",
           "generos", "insignias"]


def _medir(perfil, pal, imagenes, k):
    img = QImage(8, 8, QImage.Format_ARGB32_Premultiplied)
    pt = QPainter(img)
    L = Lienzo(pt, pal, perfil, imagenes, k, pt)
    L.dibujar = False
    hs = [(n, getattr(L, "b_" + n)(0)) for n in BLOQUES]
    pt.end()
    return [(n, h) for n, h in hs if h > 0]


def planificar(perfil, pal, imagenes):
    """Busca la escala más grande a la que todo cabe y reparte el espacio sobrante entre los bloques."""
    ini, fin = ZONA_CUERPO
    disponible = fin - ini
    k = 1.4
    while True:
        bloques = _medir(perfil, pal, imagenes, k)
        hueco = int(34 * k)
        total = sum(h for _n, h in bloques) + hueco * max(0, len(bloques) - 1)
        if total <= disponible or k <= 0.46:
            break
        k = round(k - 0.02, 3)
    n = max(1, len(bloques) - 1)
    extra = max(0, disponible - total)
    hueco_final = hueco + min(extra / n, hueco * 1.1)
    usado = sum(h for _n, h in bloques) + hueco_final * (len(bloques) - 1)
    y = ini + max(0, (disponible - usado) / 2)
    pos = []
    for nombre, h in bloques:
        pos.append((nombre, int(y), h))
        y += h + hueco_final
    return k, pos


def generar_con_info(perfil, estilo="color", imagenes=None):
    estilo = estilo if estilo in ESTILOS else "color"
    perfil = dict(perfil or {})
    color = QColor(perfil.get("color_perfil") or "#22D3EE")
    if not color.isValid():
        color = QColor("#22D3EE")
    perfil["color_perfil"] = color.name()
    imagenes = imagenes or {}
    pal = paleta(estilo, color)
    k, pos = planificar(perfil, pal, imagenes)
    img = QImage(ANCHO, ALTO, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor("#000000"))
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
    L = Lienzo(p, pal, perfil, imagenes, k, p)
    p_av = next((y for n, y, h in pos if n == "avatar"), 560)
    h_av = next((h for n, y, h in pos if n == "avatar"), 270)
    _fondo(p, pal, estilo, color, imagenes.get("banner"), p_av + h_av / 2)
    L.b_cabecera(ZONA_ARRIBA)
    for nombre, y, _h in pos:
        getattr(L, "b_" + nombre)(y)
    L.pie()
    p.end()
    info = {"k": k, "bloques": pos, "cajas": L.cajas, "recortados": L.recortados, "estilo": estilo}
    return img.convertToFormat(QImage.Format_RGB32), info


def generar(perfil, estilo="color", imagenes=None):
    return generar_con_info(perfil, estilo, imagenes)[0]


# ------------------------------------------------------------------ imágenes del perfil

def urls_de(perfil):
    """Qué imágenes necesita la tarjeta: clave -> dirección."""
    u = {}
    if perfil.get("foto_url"):
        u["foto"] = S.url_foto(perfil["foto_url"])
    if perfil.get("banner_url"):
        u["banner"] = S.url_foto(perfil["banner_url"])
    c = perfil.get("cancion_fav") or {}
    mini = c.get("miniatura") or (f"https://i.ytimg.com/vi/{c['video_id']}/hqdefault.jpg" if c.get("video_id") else "")
    if mini:
        u["cancion"] = mini
    for i, a in enumerate([a for a in (perfil.get("top_artistas") or []) if a.get("nombre")][:3]):
        if a.get("portada"):
            u[f"top{i}"] = a["portada"]
    return {k: v for k, v in u.items() if v}


def traer_imagenes(perfil):
    """Baja (o lee de la caché) las imágenes del perfil. Bloquea: usar en segundo plano."""
    from .ui import imagenes as IM
    salida = {}
    for clave, url in urls_de(perfil).items():
        datos = IM._leer(url)
        if not datos:
            continue
        img = QImage()
        if img.loadFromData(datos) and not img.isNull():
            salida[clave] = img
    return salida


def nombre_sugerido(perfil):
    import re
    u = re.sub(r"[^A-Za-z0-9_.-]+", "", str(perfil.get("usuario") or "")) or "perfil"
    return f"caudal_perfil_{u}.png"
