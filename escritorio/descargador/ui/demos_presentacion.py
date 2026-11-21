# -*- coding: utf-8 -*-
"""Demostraciones animadas para las presentaciones («Somos 100» y «Gracias, donador»): en vez de describir
lo que trae Caudal, se ve funcionando dentro de una «pantalla» con marco.

Cada demo es una función `demo_x(p, rect, t, fs, pal, cache)` que pinta dentro de `rect` (ya recortado con
esquinas redondas) en el instante `t` (segundos desde que se abrió la diapositiva). `cache` es un dict propio
de la presentación para guardar lo caro (escenarios creados, imágenes reducidas, la letra…).

Las demos vivas usan las piezas reales de la app: los escenarios con su motor, la letra cinética de la escena
y las mascotas con su dibujo; lo demás son maquetas animadas (gamer, escuchar juntos, descubre, marcos…).
"""
import math
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QFontMetricsF, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)

from . import ilustraciones_grandes as I
from .componentes import fuente

CARPETA_IMG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "escenarios_img")
ESCENARIOS_DEMO = (("cyberpunk", "Cyberpunk"), ("samurai", "Japón antiguo"), ("goku", "Goku"),
                   ("kuromi", "Kuromi"), ("ippo", "Hajime no Ippo"), ("cinnamoroll", "Cinnamoroll"),
                   ("kaneki", "Kaneki"), ("hellokitty", "Hello Kitty"), ("lofi", "Lo-fi"))
SEG_ESCENARIO = 4.0


# ---------------------------------------------------------------- marco de pantalla

def marco(p, rect, fs, pal, contenido):
    """Una «pantalla» con bisel, sombra, brillo del acento y reflejo; `contenido(p, interior)` pinta dentro."""
    radio = 18 * fs
    # sombra y halo
    for k, a in ((26, 30), (14, 50), (6, 70)):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, a))
        p.drawRoundedRect(rect.adjusted(-k * fs * 0.3, -k * fs * 0.1 + 8 * fs, k * fs * 0.3, k * fs * 0.6), radio + k,
                          radio + k)
    I.brillo(p, rect.center().x(), rect.bottom(), rect.width() * 0.55, pal.ac, 50)
    p.setBrush(QColor(14, 14, 20))
    p.setPen(QPen(QColor(255, 255, 255, 40), 1.2 * fs))
    p.drawRoundedRect(rect, radio, radio)
    interior = rect.adjusted(7 * fs, 7 * fs, -7 * fs, -7 * fs)
    camino = QPainterPath()
    camino.addRoundedRect(interior, radio - 6 * fs, radio - 6 * fs)
    p.save()
    p.setClipPath(camino)
    p.fillRect(interior, QColor(8, 8, 12))
    contenido(p, interior)
    # reflejo diagonal del cristal
    g = QLinearGradient(interior.topLeft(), interior.bottomRight())
    g.setColorAt(0.0, QColor(255, 255, 255, 22))
    g.setColorAt(0.35, QColor(255, 255, 255, 0))
    p.fillRect(interior, g)
    p.restore()


def _chip(p, x, y, texto, fs, fondo=QColor(0, 0, 0, 150), color=QColor("#FFFFFF"), px=13):
    f = fuente(px * fs, QFont.Bold)
    p.setFont(f)
    fm = QFontMetricsF(f)
    r = QRectF(x, y, fm.horizontalAdvance(texto) + 22 * fs, fm.height() + 10 * fs)
    p.setPen(Qt.NoPen)
    p.setBrush(fondo)
    p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
    p.setPen(color)
    p.drawText(r, int(Qt.AlignCenter), texto)
    return r


def _imagen(cache, nombre, ancho):
    """Una ilustración de escenarios_img reducida (con caché) a `ancho` px."""
    clave = ("img", nombre, int(ancho))
    img = cache.get(clave)
    if img is None:
        ruta = os.path.join(CARPETA_IMG, nombre)
        img = QImage(ruta)
        if not img.isNull():
            img = img.scaledToWidth(max(8, int(ancho)), Qt.SmoothTransformation)
        cache[clave] = img
    return img


def _escenario_vivo(cache, clave, w, h, t, bandas):
    """Un cuadro del escenario real (motor de la escena) a w×h. Se guarda el widget por clave y tamaño."""
    from .escena import escenarios
    k = ("esc", clave)
    esc = cache.get(k)
    if esc is None:
        esc = escenarios.crear(clave)
        cache[k] = esc
    if esc is None:
        return None
    w, h = max(16, int(w)), max(16, int(h))
    if esc.width() != w or esc.height() != h:
        esc.resize(w, h)
    esc.fijar_espectro(bandas)
    esc._cuadro()
    esc._ahora = esc._t0 + 3.0 + t
    img = cache.get(("lienzo", w, h))
    if img is None:
        img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        cache[("lienzo", w, h)] = img
    img.fill(0)
    esc.render(img)
    return img


def _bandas(t):
    """Un espectro de música simulado: graves que laten a ~120 BPM y agudos que bailan."""
    golpe = max(0.0, math.cos(t * math.pi * 4)) ** 6
    return [min(1.0, 0.35 + 0.6 * golpe * (1 - i / 10)) if i < 6 else
            0.25 + 0.25 * (0.5 + 0.5 * math.sin(t * 3.1 + i * 0.7)) for i in range(32)]


# ---------------------------------------------------------------- demos de la comunidad («Somos 100»)

def demo_escenarios(p, r, t, fs, pal, cache):
    """Los escenarios reales, uno tras otro con fundido, moviéndose con una música simulada."""
    n = len(ESCENARIOS_DEMO)
    pos = t / SEG_ESCENARIO
    k = int(pos) % n
    u = pos - int(pos)
    esc_w, esc_h = min(960, r.width()), min(960, r.width()) * r.height() / r.width()
    bandas = _bandas(t)
    actual = _escenario_vivo(cache, ESCENARIOS_DEMO[k][0], esc_w, esc_h, t, bandas)
    if actual is not None:
        p.drawImage(r, actual)
    if u > 0.85:                                          # fundido al siguiente
        sig = _escenario_vivo(cache, ESCENARIOS_DEMO[(k + 1) % n][0], esc_w, esc_h, t, bandas)
        if sig is not None:
            p.setOpacity((u - 0.85) / 0.15)
            p.drawImage(r, sig)
            p.setOpacity(1.0)
    nombre = ESCENARIOS_DEMO[(k + 1) % n][1] if u > 0.93 else ESCENARIOS_DEMO[k][1]
    _chip(p, r.left() + 14 * fs, r.bottom() - 44 * fs, nombre, fs, QColor(0, 0, 0, 160))
    # partículas del «ratón» que pasa por encima
    cx = r.left() + r.width() * (0.5 + 0.32 * math.sin(t * 0.9))
    cy = r.top() + r.height() * (0.45 + 0.2 * math.sin(t * 1.7))
    for j in range(10):
        e = (t * 1.3 + j * 0.1) % 1.0
        a = math.radians(j * 36 + t * 60)
        x = cx - math.cos(a) * 26 * fs * e
        y = cy - math.sin(a) * 26 * fs * e + 18 * fs * e * e
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, int(200 * (1 - e))))
        p.drawEllipse(QPointF(x, y), 2.4 * fs * (1 - e) + 0.6, 2.4 * fs * (1 - e) + 0.6)
    _cursor(p, cx, cy, fs)


def _cursor(p, x, y, fs):
    flecha = QPainterPath(QPointF(x, y))
    for dx, dy in ((0, 17), (4.5, 13), (8, 20), (11, 18.5), (7.5, 11.5), (13, 11.5)):
        flecha.lineTo(QPointF(x + dx * fs, y + dy * fs))
    flecha.closeSubpath()
    p.setPen(QPen(QColor(0, 0, 0, 200), 1.2 * fs))
    p.setBrush(QColor(255, 255, 255))
    p.drawPath(flecha)


LETRA_DEMO = [(0, "Esta noche suena distinto"), (3200, "cada latido va a tu ritmo"),
              (6400, "y no quiero que termine"), (9600, "nuestra canción")]
CICLO_LETRA = 12800


def demo_letra(p, r, t, fs, pal, cache):
    """La letra cinética real de la escena, cantándose sobre un escenario vivo."""
    fondo = _escenario_vivo(cache, "samurai", min(960, r.width()), min(960, r.width()) * r.height() / r.width(),
                            t, _bandas(t))
    if fondo is not None:
        p.drawImage(r, fondo)
    from .escena.letra import LetraCinetica
    w, h = int(r.width() * 0.84), int(r.height() * 0.62)
    letra = cache.get(("letra", w, h))
    if letra is None:
        letra = LetraCinetica()
        letra.resize(w, h)
        letra.poner_colores("#FF7AA8", "#FFD08A", "#FF7AA8")
        letra.poner_lineas([{"ms": ms, "texto": tx} for ms, tx in LETRA_DEMO], True)
        cache[("letra", w, h)] = letra
        cache["letra_vuelta"] = -1
    ms = int(t * 1000) % CICLO_LETRA
    vuelta = int(t * 1000) // CICLO_LETRA
    if vuelta != cache.get("letra_vuelta"):
        letra.poner_lineas([{"ms": ms0, "texto": tx} for ms0, tx in LETRA_DEMO], True)
        cache["letra_vuelta"] = vuelta
    letra.fijar_ms(ms)
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    letra.render(img)
    p.drawImage(QPointF(r.left() + (r.width() - w) / 2, r.top() + (r.height() - h) / 2), img)
    _chip(p, r.left() + 14 * fs, r.top() + 14 * fs, "♪ A tiempo con la música · con traducción", fs,
          QColor(0, 0, 0, 150), px=12)


def demo_mascotas(p, r, t, fs, pal, cache):
    """Mascotas reales caminando por un prado al atardecer."""
    from .. import mascotas as M
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0, QColor("#2A1B4D"))
    g.setColorAt(0.55, QColor("#7A3E6E"))
    g.setColorAt(0.75, QColor("#E8885A"))
    g.setColorAt(0.76, QColor("#3E6B3A"))
    g.setColorAt(1, QColor("#22401F"))
    p.fillRect(r, g)
    I.brillo(p, r.center().x(), r.top() + r.height() * 0.70, r.width() * 0.25, QColor("#FFD08A"), 120)
    suelo = r.top() + r.height() * 0.86
    claves = cache.get("mascotas")
    if claves is None:
        try:
            catalogo = [m for m in M.catalogo() if not m.get("exclusiva") and M.cuadros(m["clave"])]
        except Exception:  # noqa: BLE001
            catalogo = []
        elegidas = [m for m in catalogo if m["clave"] in ("nyan", "capibara", "bulbasaur", "charmander", "ajolote",
                                                          "caniche", "ciervo", "cacatua")] or catalogo[:6]
        claves = elegidas[:7]
        cache["mascotas"] = claves
    for k, datos in enumerate(claves):
        vel = 0.06 + 0.015 * (k % 3)
        u = (t * vel + k / max(1, len(claves))) % 1.0
        x = r.left() - 60 * fs + u * (r.width() + 120 * fs)
        escala = 2.2 * fs
        salto = abs(math.sin(t * 6 + k)) * 3 * fs
        cuadro = int(t * 6 + k) % 8
        p.save()
        try:
            M.pintar(p, datos, x, suelo - salto, r.left(), r.right() + 400 * fs, cuadro, t * 6, escala=escala)
        except Exception:  # noqa: BLE001
            pass
        p.restore()
    _chip(p, r.left() + 14 * fs, r.top() + 14 * fs, "Más de 60 mascotas te acompañan", fs, QColor(0, 0, 0, 140))


def _avatar(p, c, radio, letra, color, fs):
    g = QLinearGradient(c.x() - radio, c.y() - radio, c.x() + radio, c.y() + radio)
    g.setColorAt(0, QColor(color).lighter(140))
    g.setColorAt(1, QColor(color))
    p.setPen(QPen(QColor(255, 255, 255, 200), 2 * fs))
    p.setBrush(g)
    p.drawEllipse(c, radio, radio)
    p.setFont(fuente(radio * 0.9, QFont.Black))
    p.setPen(QColor("#FFFFFF"))
    p.drawText(QRectF(c.x() - radio, c.y() - radio, 2 * radio, 2 * radio), int(Qt.AlignCenter), letra)


def demo_juntos(p, r, t, fs, pal, cache):
    """Escuchar juntos: dos personas, la misma canción al mismo segundo, chat y reacciones que flotan."""
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#141428"))
    g.setColorAt(1, QColor("#2B1038"))
    p.fillRect(r, g)
    cy = r.top() + r.height() * 0.34
    a1, a2 = QPointF(r.left() + r.width() * 0.16, cy), QPointF(r.right() - r.width() * 0.16, cy)
    _avatar(p, a1, 34 * fs, "A", "#7C4DFF", fs)
    _avatar(p, a2, 34 * fs, "M", "#FF4F8B", fs)
    # ondas sincronizadas entre los dos
    for k in range(3):
        u = (t * 0.7 + k / 3) % 1.0
        p.setPen(QPen(I.alfa(pal.al, int(180 * (1 - u))), 2 * fs))
        p.setBrush(Qt.NoBrush)
        for c in (a1, a2):
            p.drawEllipse(c, (36 + 40 * u) * fs, (36 + 40 * u) * fs)
    # tarjeta de la canción en común
    tarjeta = QRectF(r.center().x() - r.width() * 0.22, cy - 34 * fs, r.width() * 0.44, 68 * fs)
    I.cristal(p, tarjeta, 14 * fs, a_relleno=40, a_borde=80)
    portada = QRectF(tarjeta.left() + 10 * fs, tarjeta.top() + 10 * fs, 48 * fs, 48 * fs)
    img = _imagen(cache, "cyberpunk.jpg", 160)
    if not img.isNull():
        p.save()
        cam = QPainterPath()
        cam.addRoundedRect(portada, 8 * fs, 8 * fs)
        p.setClipPath(cam, Qt.IntersectClip)
        p.drawImage(portada, img, QRectF((img.width() - img.height()) / 2, 0, img.height(), img.height()))
        p.restore()
    p.setPen(QColor("#FFFFFF"))
    p.setFont(fuente(14 * fs, QFont.Bold))
    p.drawText(QPointF(portada.right() + 10 * fs, tarjeta.top() + 28 * fs), "Al mismo segundo")
    p.setPen(QColor(255, 255, 255, 170))
    p.setFont(fuente(12 * fs, QFont.Normal))
    p.drawText(QPointF(portada.right() + 10 * fs, tarjeta.top() + 46 * fs), "Sala de Ana · 2 escuchando")
    prog = (t * 0.06) % 1.0
    barra = QRectF(portada.right() + 10 * fs, tarjeta.bottom() - 14 * fs, tarjeta.right() - portada.right() - 22 * fs,
                   4 * fs)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 50))
    p.drawRoundedRect(barra, 2 * fs, 2 * fs)
    p.setBrush(pal.al)
    p.drawRoundedRect(QRectF(barra.left(), barra.top(), barra.width() * prog, barra.height()), 2 * fs, 2 * fs)
    # chat que va apareciendo
    mensajes = [(0, "¡Esta canción es lo máximo! 🔥"), (1, "La pongo en nuestra lista 💜"), (0, "Escucha el coro 🎶"),
                (1, "Jajaja la estoy cantando")]
    ciclo = 10.0
    tt = t % ciclo
    y = r.top() + r.height() * 0.60
    for k, (quien, texto) in enumerate(mensajes):
        aparece = 1.0 + k * 1.8
        if tt < aparece:
            break
        e = I.eo(I.clamp((tt - aparece) / 0.4))
        f = fuente(13 * fs, QFont.DemiBold)
        fm = QFontMetricsF(f)
        bw = fm.horizontalAdvance(texto) + 26 * fs
        x = r.left() + r.width() * 0.10 if quien == 0 else r.right() - r.width() * 0.10 - bw
        burbuja = QRectF(x, y + (1 - e) * 10 * fs, bw, 30 * fs)
        p.setOpacity(e)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#7C4DFF") if quien == 0 else QColor("#FF4F8B"))
        p.drawRoundedRect(burbuja, 15 * fs, 15 * fs)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(burbuja, int(Qt.AlignCenter), texto)
        p.setOpacity(1.0)
        y += 38 * fs
    # reacciones que flotan
    p.setFont(fuente(20 * fs, QFont.Normal))
    for k, emoji in enumerate(("❤️", "🔥", "😍", "🎉", "💜")):
        u = (t * 0.35 + k * 0.2) % 1.0
        x = r.center().x() + math.sin(u * 6 + k) * 40 * fs + (k - 2) * 26 * fs
        y = r.bottom() - u * r.height() * 0.55
        p.setOpacity(math.sin(math.pi * u))
        p.drawText(QPointF(x, y), emoji)
    p.setOpacity(1.0)


def demo_gamer(p, r, t, fs, pal, cache):
    """Modo gamer: la barra de experiencia se llena, sube de nivel con un destello y las misiones se tachan."""
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#0B0F1E"))
    g.setColorAt(1, QColor("#1B0B2E"))
    p.fillRect(r, g)
    ciclo = 7.0
    tt = t % ciclo
    llenado = I.eo(I.clamp(tt / 3.2))
    subio = tt > 3.2
    nivel = 12 if subio else 11
    # borde RGB animado
    caja = r.adjusted(r.width() * 0.08, r.height() * 0.10, -r.width() * 0.08, -r.height() * 0.10)
    cg = QConicalGradient(caja.center(), (t * 90) % 360)
    for k, c in enumerate(("#FF3D8B", "#FFC14D", "#3DFFB0", "#3D9BFF", "#B14AED", "#FF3D8B")):
        cg.setColorAt(k / 5, QColor(c))
    p.setPen(QPen(QBrush(cg), 3 * fs))
    p.setBrush(QColor(255, 255, 255, 10))
    p.drawRoundedRect(caja, 16 * fs, 16 * fs)
    p.setPen(QColor("#FFFFFF"))
    p.setFont(fuente(26 * fs, QFont.Black))
    p.drawText(QPointF(caja.left() + 26 * fs, caja.top() + 50 * fs), f"Nivel {nivel} · Veterano")
    p.setFont(fuente(13 * fs, QFont.Normal))
    p.setPen(QColor(255, 255, 255, 170))
    p.drawText(QPointF(caja.left() + 26 * fs, caja.top() + 74 * fs), "Racha de 9 días · se suma en tu PC y tu celular")
    barra = QRectF(caja.left() + 26 * fs, caja.top() + 90 * fs, caja.width() - 52 * fs, 14 * fs)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 30))
    p.drawRoundedRect(barra, 7 * fs, 7 * fs)
    bg = QLinearGradient(barra.topLeft(), barra.topRight())
    bg.setColorAt(0, QColor("#FF3D8B"))
    bg.setColorAt(1, QColor("#FFC14D"))
    p.setBrush(bg)
    p.drawRoundedRect(QRectF(barra.left(), barra.top(), barra.width() * (0.05 if subio else llenado), barra.height()),
                      7 * fs, 7 * fs)
    misiones = ("Escucha 30 minutos", "Prueba un preset de sonido", "Descubre 3 canciones nuevas")
    for k, m in enumerate(misiones):
        y = caja.top() + 140 * fs + k * 34 * fs
        hecha = tt > 0.9 + k * 0.9
        p.setPen(QPen(QColor("#3DFFB0") if hecha else QColor(255, 255, 255, 120), 2 * fs))
        p.setBrush(QColor(61, 255, 176, 60) if hecha else Qt.NoBrush)
        p.drawRoundedRect(QRectF(caja.left() + 26 * fs, y - 12 * fs, 18 * fs, 18 * fs), 5 * fs, 5 * fs)
        if hecha:
            p.drawPolyline([QPointF(caja.left() + 30 * fs, y - 3 * fs), QPointF(caja.left() + 34 * fs, y + 1 * fs),
                            QPointF(caja.left() + 40 * fs, y - 7 * fs)])
        p.setPen(QColor(255, 255, 255, 230 if hecha else 170))
        p.setFont(fuente(14 * fs, QFont.DemiBold))
        p.drawText(QPointF(caja.left() + 56 * fs, y + 2 * fs), m)
        p.setPen(QColor("#FFC14D"))
        p.drawText(QPointF(caja.right() - 90 * fs, y + 2 * fs), "+15 XP")
    if subio:
        e = I.clamp((tt - 3.2) / 0.6)
        esc = 0.6 + 0.4 * I.eo(e) + 0.05 * math.sin((tt - 3.2) * 8) * (1 - e)
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(10, 8, 20, int(200 * I.eo(e))))
        p.drawRoundedRect(caja.adjusted(3 * fs, 3 * fs, -3 * fs, -3 * fs), 14 * fs, 14 * fs)
        p.translate(caja.center().x(), caja.center().y() - 10 * fs)
        p.scale(esc, esc)
        I.brillo(p, 0, 0, 160 * fs, QColor("#FFC14D"), int(160 * (1 - 0.5 * e)))
        p.setFont(fuente(40 * fs, QFont.Black))
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(-300 * fs, -40 * fs, 600 * fs, 80 * fs), int(Qt.AlignCenter), "¡Subiste al nivel 12!")
        p.restore()


def demo_descubre(p, r, t, fs, pal, cache):
    """«Descubre para ti»: carrusel de mezclas que pasa solo, con la carátula que se agranda al centro."""
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0, QColor("#101321"))
    g.setColorAt(1, QColor("#1A1030"))
    p.fillRect(r, g)
    p.setPen(QColor("#FFFFFF"))
    p.setFont(fuente(22 * fs, QFont.Black))
    p.drawText(QPointF(r.left() + 24 * fs, r.top() + 44 * fs), "Descubre para ti")
    p.setPen(QColor(255, 255, 255, 160))
    p.setFont(fuente(13 * fs, QFont.Normal))
    p.drawText(QPointF(r.left() + 24 * fs, r.top() + 66 * fs), "Canciones nuevas cada día, elegidas por lo que escuchas")
    portadas = ("japon.jpg", "cyberpunk.jpg", "lofi.jpg", "kuromi.jpg", "goku.jpg", "cinnamoroll.jpg", "kaneki.jpg",
                "pompompurin.jpg")
    nombres = ("Atardeceres", "Neón nocturno", "Lo-fi para estudiar", "Dark pop", "Energía pura", "Suave y dulce",
               "Melancolía", "Café de la mañana")
    lado = r.height() * 0.48
    paso = lado * 0.78
    desplaz = (t * 0.35) % len(portadas)
    cy = r.top() + r.height() * 0.60
    orden = []
    for k in range(len(portadas)):
        d = ((k - desplaz + len(portadas) / 2) % len(portadas)) - len(portadas) / 2
        orden.append((abs(d), d, k))
    for _ad, d, k in sorted(orden, reverse=True):
        x = r.center().x() + d * paso
        if x < r.left() - lado or x > r.right() + lado:
            continue
        esc = 1.0 - min(0.35, abs(d) * 0.16)
        s = lado * esc
        rect = QRectF(x - s / 2, cy - s / 2, s, s)
        img = _imagen(cache, portadas[k], 360)
        p.save()
        cam = QPainterPath()
        cam.addRoundedRect(rect, 12 * fs, 12 * fs)
        p.setClipPath(cam, Qt.IntersectClip)
        if not img.isNull():
            p.drawImage(rect, img, QRectF((img.width() - img.height()) / 2, 0, img.height(), img.height()))
        sombra = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        sombra.setColorAt(0.5, QColor(0, 0, 0, 0))
        sombra.setColorAt(1, QColor(0, 0, 0, 190))
        p.fillRect(rect, sombra)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(fuente(13 * fs * esc, QFont.Bold))
        p.drawText(QRectF(rect.left() + 10 * fs, rect.bottom() - 30 * fs, rect.width() - 20 * fs, 24 * fs),
                   int(Qt.AlignLeft | Qt.AlignVCenter), nombres[k])
        p.restore()
        p.setOpacity(1.0)


def demo_captura(nombre):
    """Una captura real de la app (en escenarios_img/capturas) con un paneo lento tipo «Ken Burns»."""
    def demo(p, r, t, fs, pal, cache):
        img = cache.get(("cap", nombre))
        if img is None:
            img = QImage(os.path.join(CARPETA_IMG, "capturas", nombre))
            cache[("cap", nombre)] = img
        if img.isNull():
            p.fillRect(r, QColor("#111"))
            return
        zoom = 1.06 + 0.06 * (0.5 + 0.5 * math.sin(t * 0.25))
        s = max(r.width() / img.width(), r.height() / img.height()) * zoom
        w, h = img.width() * s, img.height() * s
        dx = (w - r.width()) * (0.5 + 0.5 * math.sin(t * 0.18))
        dy = (h - r.height()) * (0.5 + 0.5 * math.cos(t * 0.15))
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawImage(QRectF(r.left() - dx, r.top() - dy, w, h), img)
    return demo


# ---------------------------------------------------------------- demos de donadores

MARCOS_DEMO = (("Aurora", ("#3DFFB0", "#3D9BFF", "#B14AED", "#3DFFB0")),
               ("Fuego", ("#FF3D00", "#FFB300", "#FF6D00", "#FF3D00")),
               ("Oro", ("#FFE08A", "#B8860B", "#FFF3C4", "#FFE08A")),
               ("Neón", ("#FF2A6D", "#05D9E8", "#FF2A6D", "#05D9E8")),
               ("Galaxia", ("#7C4DFF", "#FF4F8B", "#1A237E", "#7C4DFF")))
EFECTOS_DEMO = ("Brillo", "Degradado", "Arcoíris", "Neón")


def demo_perfil_premium(p, r, t, fs, pal, cache):
    """Marcos animados alrededor de la foto y el nombre con efecto, cambiando cada 2 s."""
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#120E1C"))
    g.setColorAt(1, QColor("#1E1206"))
    p.fillRect(r, g)
    k = int(t / 2.2) % len(MARCOS_DEMO)
    nombre_marco, colores = MARCOS_DEMO[k]
    c = QPointF(r.left() + r.width() * 0.30, r.center().y())
    radio = r.height() * 0.24
    I.brillo(p, c.x(), c.y(), radio * 2.0, QColor(colores[0]), 110)
    from .premium_estilos import pintar_marco
    clave_marco = {"Aurora": "aurora", "Fuego": "fuego", "Oro": "oro", "Neón": "neon", "Galaxia": "galaxia"}[nombre_marco]
    pintar_marco(p, QRectF(c.x() - radio - 9 * fs, c.y() - radio - 9 * fs, 2 * radio + 18 * fs, 2 * radio + 18 * fs),
                 clave_marco, angulo=(t * 120) % 360, ancho=max(6.0, 10 * fs))
    img = _imagen(cache, "kuromi.jpg", 420)
    if not img.isNull():
        p.save()
        cam = QPainterPath()
        cam.addEllipse(c, radio, radio)
        p.setClipPath(cam, Qt.IntersectClip)
        lado = img.height() * 0.6
        p.drawImage(QRectF(c.x() - radio, c.y() - radio, 2 * radio, 2 * radio), img,
                    QRectF(img.width() * 0.5 - lado / 2, img.height() * 0.12, lado, lado))
        p.restore()
    _chip(p, c.x() - 60 * fs, c.y() + radio + 22 * fs, f"Marco {nombre_marco}", fs, QColor(255, 255, 255, 30))
    # nombre con efecto
    efecto = EFECTOS_DEMO[int(t / 2.2) % len(EFECTOS_DEMO)]
    f = fuente(46 * fs, QFont.Black)
    texto = "Aligeri"
    camino = QPainterPath()
    camino.addText(QPointF(0, 0), f, texto)
    caja = camino.boundingRect()
    x0 = r.left() + r.width() * 0.56
    y0 = r.center().y() - 6 * fs
    p.save()
    p.translate(x0 - caja.left(), y0 - caja.center().y())
    if efecto == "Arcoíris":
        gg = QLinearGradient(caja.left() - (t * 120) % caja.width(), 0, caja.right() + caja.width(), 0)
        for j, col in enumerate(("#FF3D3D", "#FFB13D", "#FFF03D", "#3DFF7A", "#3DB8FF", "#B14AED", "#FF3D3D")):
            gg.setColorAt(j / 6, QColor(col))
        gg.setSpread(QLinearGradient.RepeatSpread)
        relleno = QBrush(gg)
    elif efecto == "Degradado":
        gg = QLinearGradient(caja.topLeft(), caja.bottomRight())
        gg.setColorAt(0, QColor("#FFD76A"))
        gg.setColorAt(1, QColor("#FF4F8B"))
        relleno = QBrush(gg)
    else:
        relleno = QBrush(QColor("#FFFFFF"))
    if efecto == "Neón":
        for ancho, a in ((18, 30), (9, 70)):
            p.setPen(QPen(QColor(5, 217, 232, a), ancho * fs, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(camino)
    p.setPen(Qt.NoPen)
    p.setBrush(relleno)
    p.drawPath(camino)
    if efecto == "Brillo":
        bx = caja.left() + ((t * 0.8) % 1.4 - 0.2) * caja.width()
        bg = QLinearGradient(bx - 30 * fs, 0, bx + 30 * fs, 0)
        bg.setColorAt(0, QColor(255, 236, 160, 0))
        bg.setColorAt(0.5, QColor(255, 236, 160, 230))
        bg.setColorAt(1, QColor(255, 236, 160, 0))
        p.setClipPath(camino, Qt.IntersectClip)
        p.fillRect(caja.adjusted(-10, -10, 10, 10), bg)
    p.restore()
    _chip(p, x0, y0 + 40 * fs, f"Nombre con efecto · {efecto}", fs, QColor(255, 255, 255, 30))
    _chip(p, x0, y0 + 80 * fs, "★ Donador de Caudal", fs, QColor(232, 171, 22, 70), QColor("#FFD76A"))


TEMAS_DEMO = (("Cyberpunk", "#0B0A1A", "#FF2A6D", "#05D9E8"), ("Japón samurái", "#1A1020", "#EA5863", "#F5CFA8"),
              ("Kuromi", "#17121F", "#B57BFF", "#FF9AD8"), ("Cinnamoroll", "#EAF4FF", "#7FB6F2", "#FFFFFF"),
              ("Lo-fi", "#1E1612", "#FFB86B", "#E8D5B5"), ("Gótico", "#0E0A10", "#CD5E74", "#9A8AA8"))


def demo_temas(p, r, t, fs, pal, cache):
    """Una maqueta de Caudal cambiando de estética: barra lateral, carátula y tarjetas en cada tema."""
    k = int(t / 2.0) % len(TEMAS_DEMO)
    u = (t / 2.0) % 1.0
    nombre, fondo, acento, segundo = TEMAS_DEMO[k]
    sig = TEMAS_DEMO[(k + 1) % len(TEMAS_DEMO)]
    mezcla = I.clamp((u - 0.8) / 0.2)
    fondo_c = I.mezcla(fondo, sig[1], mezcla)
    acento_c = I.mezcla(acento, sig[2], mezcla)
    segundo_c = I.mezcla(segundo, sig[3], mezcla)
    p.fillRect(r, fondo_c)
    claro = fondo_c.lightness() > 150
    tinta = QColor(20, 20, 30) if claro else QColor(255, 255, 255)
    lateral = QRectF(r.left(), r.top(), r.width() * 0.20, r.height())
    p.fillRect(lateral, I.alfa(acento_c, 40))
    for j in range(5):
        p.setPen(Qt.NoPen)
        p.setBrush(I.alfa(tinta, 150 if j == 1 else 60))
        p.drawRoundedRect(QRectF(lateral.left() + 14 * fs, lateral.top() + (30 + j * 30) * fs, lateral.width() * 0.7,
                                 10 * fs), 5 * fs, 5 * fs)
    portada = QRectF(lateral.right() + 24 * fs, r.top() + 26 * fs, r.height() * 0.42, r.height() * 0.42)
    gg = QLinearGradient(portada.topLeft(), portada.bottomRight())
    gg.setColorAt(0, acento_c)
    gg.setColorAt(1, segundo_c)
    p.setBrush(gg)
    p.drawRoundedRect(portada, 12 * fs, 12 * fs)
    p.setPen(tinta)
    p.setFont(fuente(24 * fs, QFont.Black))
    p.drawText(QPointF(portada.right() + 20 * fs, portada.top() + 40 * fs), nombre)
    p.setFont(fuente(13 * fs, QFont.Normal))
    p.setPen(I.alfa(tinta, 170))
    p.drawText(QPointF(portada.right() + 20 * fs, portada.top() + 64 * fs), "Estética exclusiva para donadores")
    p.setPen(Qt.NoPen)
    p.setBrush(acento_c)
    p.drawRoundedRect(QRectF(portada.right() + 20 * fs, portada.top() + 84 * fs, 120 * fs, 34 * fs), 17 * fs, 17 * fs)
    p.setPen(QColor(20, 20, 30) if acento_c.lightness() > 140 else QColor(255, 255, 255))
    p.setFont(fuente(13 * fs, QFont.Bold))
    p.drawText(QRectF(portada.right() + 20 * fs, portada.top() + 84 * fs, 120 * fs, 34 * fs), int(Qt.AlignCenter),
               "▶  Reproducir")
    for j in range(3):
        tarjeta = QRectF(lateral.right() + 24 * fs + j * (r.width() * 0.245), portada.bottom() + 22 * fs,
                         r.width() * 0.225, r.height() * 0.30)
        p.setPen(Qt.NoPen)
        p.setBrush(I.alfa(tinta, 22))
        p.drawRoundedRect(tarjeta, 12 * fs, 12 * fs)
        p.setBrush(I.alfa(acento_c if j != 1 else segundo_c, 160))
        p.drawRoundedRect(QRectF(tarjeta.left() + 10 * fs, tarjeta.top() + 10 * fs, tarjeta.height() - 20 * fs,
                                 tarjeta.height() - 20 * fs), 8 * fs, 8 * fs)
    # barra de reproducción
    barra = QRectF(lateral.right(), r.bottom() - 34 * fs, r.width() - lateral.width(), 34 * fs)
    p.fillRect(barra, I.alfa(tinta, 18))
    prog = (t * 0.1) % 1.0
    p.setBrush(acento_c)
    p.drawRoundedRect(QRectF(barra.left() + 20 * fs, barra.center().y() - 2 * fs,
                             (barra.width() - 40 * fs) * prog, 4 * fs), 2 * fs, 2 * fs)


def demo_ecualizador(p, r, t, fs, pal, cache):
    """El ecualizador avanzado: diez bandas que se mueven solas y la curva suave que las une."""
    g = QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0, QColor("#0E0A06"))
    g.setColorAt(1, QColor("#22170A"))
    p.fillRect(r, g)
    bandas = ("32", "64", "125", "250", "500", "1k", "2k", "4k", "8k", "16k")
    n = len(bandas)
    area = r.adjusted(r.width() * 0.08, r.height() * 0.18, -r.width() * 0.08, -r.height() * 0.20)
    puntos = []
    for k in range(n):
        v = math.sin(t * 0.9 + k * 0.8) * 0.5 + math.sin(t * 0.37 + k * 1.9) * 0.3
        x = area.left() + area.width() * k / (n - 1)
        y = area.center().y() - v * area.height() * 0.42
        puntos.append(QPointF(x, y))
        p.setPen(QPen(QColor(255, 255, 255, 40), 3 * fs, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()))
        p.setPen(QColor(255, 236, 200, 170))
        p.setFont(fuente(11 * fs, QFont.DemiBold))
        p.drawText(QRectF(x - 20 * fs, area.bottom() + 8 * fs, 40 * fs, 16 * fs), int(Qt.AlignCenter), bandas[k])
    curva = QPainterPath(puntos[0])
    for a, b in zip(puntos, puntos[1:]):
        m = (a.x() + b.x()) / 2
        curva.cubicTo(QPointF(m, a.y()), QPointF(m, b.y()), b)
    relleno = QPainterPath(curva)
    relleno.lineTo(QPointF(area.right(), area.bottom()))
    relleno.lineTo(QPointF(area.left(), area.bottom()))
    relleno.closeSubpath()
    gg = QLinearGradient(0, area.top(), 0, area.bottom())
    gg.setColorAt(0, QColor(255, 183, 3, 110))
    gg.setColorAt(1, QColor(255, 183, 3, 0))
    p.fillPath(relleno, gg)
    p.setPen(QPen(QColor(255, 183, 3, 90), 9 * fs, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(curva)
    p.setPen(QPen(QColor("#FFE08A"), 3 * fs, Qt.SolidLine, Qt.RoundCap))
    p.drawPath(curva)
    for q in puntos:
        p.setPen(QPen(QColor("#FFFFFF"), 2 * fs))
        p.setBrush(QColor("#FFB703"))
        p.drawEllipse(q, 7 * fs, 7 * fs)
    _chip(p, r.left() + 14 * fs, r.top() + 14 * fs, "Se adapta a cada canción", fs, QColor(0, 0, 0, 120),
          QColor("#FFD76A"))


def demo_mi_perfil(p, r, t, fs, pal, cache):
    """El perfil REAL del donador: su foto, su marco animado, su nombre con su efecto y sus insignias."""
    from .premium_estilos import NombreEfecto, pintar_marco
    from ..premium_datos import NOMBRES_EFECTO, NOMBRES_MARCO, NOMBRES_TEMA
    datos = cache.get("perfil") or {}
    nombre = datos.get("nombre") or "Tú"
    marco_k = datos.get("marco") or "oro"
    efecto_k = datos.get("efecto") or "brillo"
    # portada dorada con luces
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#2A1C08"))
    g.setColorAt(1, QColor("#120C05"))
    p.fillRect(r, g)
    portada = QRectF(r.left(), r.top(), r.width(), r.height() * 0.36)
    pg = QLinearGradient(portada.topLeft(), portada.topRight())
    pg.setColorAt(0, QColor("#B45309"))
    pg.setColorAt(0.5, QColor("#E8AB16"))
    pg.setColorAt(1, QColor("#7A3E0E"))
    p.fillRect(portada, pg)
    for k in range(18):
        x = portada.left() + portada.width() * I.azar(k, 1)
        y = portada.top() + portada.height() * I.azar(k, 2)
        tw = 0.5 + 0.5 * math.sin(t * 2 + k)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 240, 200, int(140 * tw)))
        p.drawEllipse(QPointF(x, y), 2.2 * fs, 2.2 * fs)
    # foto con su marco animado
    lado = r.height() * 0.40
    c = QPointF(r.left() + r.width() * 0.17, portada.bottom())
    foto = QRectF(c.x() - lado / 2, c.y() - lado / 2, lado, lado)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#120C05"))
    p.drawEllipse(foto.adjusted(-6 * fs, -6 * fs, 6 * fs, 6 * fs))
    img = datos.get("foto")
    p.save()
    cam = QPainterPath()
    cam.addEllipse(foto)
    p.setClipPath(cam, Qt.IntersectClip)
    if img is not None and not img.isNull():
        lado_i = min(img.width(), img.height())
        p.drawImage(foto, img, QRectF((img.width() - lado_i) / 2, (img.height() - lado_i) / 2, lado_i, lado_i))
    else:
        gg = QLinearGradient(foto.topLeft(), foto.bottomRight())
        gg.setColorAt(0, QColor("#FFD76A"))
        gg.setColorAt(1, QColor("#B45309"))
        p.fillRect(foto, gg)
        p.setPen(QColor("#1A1200"))
        p.setFont(fuente(lado * 0.45, QFont.Black))
        p.drawText(foto, int(Qt.AlignCenter), nombre[:1].upper())
    p.restore()
    pintar_marco(p, foto.adjusted(-7 * fs, -7 * fs, 7 * fs, 7 * fs), marco_k, angulo=(t * 90) % 360,
                 ancho=max(5.0, 8 * fs))
    # nombre con su efecto (el mismo dibujo de la app)
    px = int(48 * fs)
    clave = ("nombre", nombre, efecto_k, px, datos.get("color"))
    et = cache.get(clave)
    if et is None:
        et = NombreEfecto(nombre, efecto_k, f"font-size:{px}px;font-weight:900;color:#FFFFFF;", siempre=True,
                          color=datos.get("color"))
        f_nombre = fuente(px, QFont.Black)
        et.setFont(f_nombre)
        et.ensurePolished()
        et.adjustSize()
        cache[clave] = et
    img_n = QImage(et.size(), QImage.Format_ARGB32_Premultiplied)
    img_n.fill(0)
    et.render(img_n)
    x_txt = foto.right() + 26 * fs
    p.drawImage(QPointF(x_txt, portada.bottom() + 8 * fs), img_n)
    p.setPen(QColor(255, 236, 200, 170))
    p.setFont(fuente(14 * fs, QFont.Normal))
    usuario = datos.get("usuario")
    p.drawText(QPointF(x_txt, portada.bottom() + 8 * fs + img_n.height() + 18 * fs), f"@{usuario}" if usuario else "")
    # insignias
    insignias = [("★ " + ("Fundador de Caudal" if datos.get("tipo") == "fundador" else "Donador de Caudal"),
                  QColor(232, 171, 22, 90), QColor("#FFD76A"))]
    insignias.append((f"Marco {NOMBRES_MARCO.get(marco_k, marco_k)}", QColor(255, 255, 255, 30), QColor("#FFFFFF")))
    insignias.append((f"Nombre {NOMBRES_EFECTO.get(efecto_k, efecto_k)}", QColor(255, 255, 255, 30),
                      QColor("#FFFFFF")))
    if datos.get("tema") and datos.get("tema") != "ninguno":
        insignias.append((NOMBRES_TEMA.get(datos["tema"], datos["tema"]), QColor(255, 255, 255, 30),
                          QColor("#FFFFFF")))
    if datos.get("en_pared"):
        insignias.append(("En el muro de agradecimiento", QColor(255, 255, 255, 30), QColor("#FFFFFF")))
    x, y = r.left() + r.width() * 0.06, r.bottom() - r.height() * 0.30
    for k, (texto, fondo, color) in enumerate(insignias):
        e = I.eo(I.clamp((t - 0.6 - k * 0.25) / 0.4))
        if e <= 0:
            continue
        ancho = QFontMetricsF(fuente(14 * fs, QFont.Bold)).horizontalAdvance(texto) + 22 * fs
        if x + ancho > r.right() - 16 * fs:                  # no cabe: a la fila siguiente
            x, y = r.left() + r.width() * 0.06, y + 38 * fs
        p.setOpacity(e)
        rr = _chip(p, x, y + (1 - e) * 8 * fs, texto, fs, fondo, color, px=14)
        x = rr.right() + 10 * fs
        p.setOpacity(1.0)


DEMOS = {
    "escenarios": demo_escenarios, "letra": demo_letra, "mascotas": demo_mascotas, "juntos": demo_juntos,
    "gamer": demo_gamer, "descubre": demo_descubre, "escena": demo_captura("escena.png"),
    "estudio": demo_captura("estudio.png"), "perfil_premium": demo_perfil_premium, "temas": demo_temas,
    "ecualizador": demo_ecualizador, "mi_perfil": demo_mi_perfil,
}


def pintar_demo(p, clave, rect, t, fs, pal, cache):
    """Pinta la demo `clave` dentro de una pantalla con marco. Si algo falla, la pantalla queda en negro."""
    fn = DEMOS.get(clave)

    def contenido(q, interior):
        if fn is None:
            return
        q.save()
        try:
            fn(q, interior, t, fs, pal, cache)
        except Exception:  # noqa: BLE001 - una demo nunca debe romper la presentación
            pass
        q.restore()
    marco(p, rect, fs, pal, contenido)
