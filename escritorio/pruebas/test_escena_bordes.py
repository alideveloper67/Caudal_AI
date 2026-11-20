# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena.bordes import LADOS, BordeBrillo, geometrias_borde


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _reloj(b, t=100.0):
    """Sustituye el reloj de un BordeBrillo por uno falso que controla la prueba."""
    estado = {"t": t}
    b._monotonic = lambda: estado["t"]
    b._t0 = t
    return estado


def _render(b):
    img = QImage(b.width(), b.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    b.render(img)
    return img


def _borde(app, lado, longitud=1920, grosor=60):
    """Franja del tamaño que le daría el marco: horizontal si es arriba/abajo."""
    b = BordeBrillo(lado)
    if lado in ("arriba", "abajo"):
        b.resize(longitud, grosor)
    else:
        b.resize(grosor, longitud)
    return b


def test_geometrias_tamanos_1920x1080():
    g = geometrias_borde(QRect(0, 0, 1920, 1080), 60)
    assert set(g) == {"arriba", "abajo", "izquierda", "derecha"}
    assert g["arriba"] == QRect(0, 0, 1920, 60)
    assert g["abajo"] == QRect(0, 1020, 1920, 60)
    assert g["izquierda"] == QRect(0, 0, 60, 1080)
    assert g["derecha"] == QRect(1860, 0, 60, 1080)


def test_cada_franja_cubre_su_lado_completo():
    r = QRect(0, 0, 1920, 1080)
    g = geometrias_borde(r, 60)
    # arriba y abajo: todo el ancho; izquierda y derecha: todo el alto
    assert (g["arriba"].left(), g["arriba"].right()) == (0, 1919)
    assert (g["abajo"].left(), g["abajo"].right()) == (0, 1919)
    assert (g["izquierda"].top(), g["izquierda"].bottom()) == (0, 1079)
    assert (g["derecha"].top(), g["derecha"].bottom()) == (0, 1079)
    # el interior queda libre y las esquinas se solapan (son translúcidas)
    centro = QPoint(960, 540)
    assert not any(f.contains(centro) for f in g.values())
    assert g["arriba"].intersects(g["izquierda"])


def test_geometrias_respetan_origen_no_nulo():
    g = geometrias_borde(QRect(100, 50, 400, 300), 20)
    assert g["arriba"] == QRect(100, 50, 400, 20)
    assert g["abajo"] == QRect(100, 330, 400, 20)
    assert g["izquierda"] == QRect(100, 50, 20, 300)
    assert g["derecha"] == QRect(480, 50, 20, 300)


def test_lado_invalido_lanza_valueerror(app):
    with pytest.raises(ValueError):
        BordeBrillo("centro")


@pytest.mark.parametrize("lado", LADOS)
def test_render_de_cada_lado_sin_errores(app, lado):
    b = _borde(app, lado)
    _reloj(b)
    img = _render(b)
    assert not img.isNull()
    assert img.width() == b.width() and img.height() == b.height()
    # algo se pinta: hay píxeles con alfa en el borde exterior
    assert _alfa_exterior(img, lado) > 0


def _alfa_exterior(img, lado):
    cx, cy = img.width() // 2, img.height() // 2
    if lado == "arriba":
        return img.pixelColor(cx, 0).alpha()
    if lado == "abajo":
        return img.pixelColor(cx, img.height() - 1).alpha()
    if lado == "izquierda":
        return img.pixelColor(0, cy).alpha()
    return img.pixelColor(img.width() - 1, cy).alpha()


def _alfa_interior(img, lado):
    cx, cy = img.width() // 2, img.height() // 2
    if lado == "arriba":
        return img.pixelColor(cx, img.height() - 1).alpha()
    if lado == "abajo":
        return img.pixelColor(cx, 0).alpha()
    if lado == "izquierda":
        return img.pixelColor(img.width() - 1, cy).alpha()
    return img.pixelColor(0, cy).alpha()


@pytest.mark.parametrize("lado", LADOS)
def test_borde_exterior_tiene_mas_alfa_que_interior(app, lado):
    b = _borde(app, lado, 1920, 60)
    _reloj(b)
    b.fijar_intensidad(1.0)
    img = _render(b)
    # tomamos el píxel junto al borde exterior y otro junto al interior
    cx, cy = img.width() // 2, img.height() // 2
    if lado == "arriba":
        exterior, interior = img.pixelColor(cx, 3).alpha(), img.pixelColor(cx, 55).alpha()
    elif lado == "abajo":
        exterior, interior = img.pixelColor(cx, 56).alpha(), img.pixelColor(cx, 4).alpha()
    elif lado == "izquierda":
        exterior, interior = img.pixelColor(3, cy).alpha(), img.pixelColor(55, cy).alpha()
    else:
        exterior, interior = img.pixelColor(56, cy).alpha(), img.pixelColor(4, cy).alpha()
    assert exterior > interior


@pytest.mark.parametrize("lado", LADOS)
def test_franja_no_oscurece_y_se_desvanece_a_cero(app, lado):
    """Sobre un QImage transparente: el interior queda con alfa <= 3 y el color a mitad
    de franja no es oscuro (no tiñe el fondo de negro)."""
    brillo = QColor(255, 158, 192)
    b = _borde(app, lado, 1920, 60)
    reloj = _reloj(b)
    # todos los colores iguales: así el píxel de medio no depende de la posición del ciclo
    b.poner_colores(brillo, brillo, brillo)
    reloj["t"] += 2 * BordeBrillo.DURACION_TRANSICION
    b.fijar_intensidad(1.0)
    img = _render(b)
    cx, cy = img.width() // 2, img.height() // 2
    if lado == "arriba":
        interior, medio = img.pixelColor(cx, 59), img.pixelColor(cx, 30)
    elif lado == "abajo":
        interior, medio = img.pixelColor(cx, 0), img.pixelColor(cx, 29)
    elif lado == "izquierda":
        interior, medio = img.pixelColor(59, cy), img.pixelColor(30, cy)
    else:
        interior, medio = img.pixelColor(0, cy), img.pixelColor(29, cy)
    assert interior.alpha() <= 3
    assert medio.red() >= 0.5 * brillo.red()
    assert medio.green() >= 0.5 * brillo.green()
    assert medio.blue() >= 0.5 * brillo.blue()


def test_poner_colores_cambia_el_color_pintado_tras_la_transicion(app):
    b = _borde(app, "arriba", 1920, 60)
    reloj = _reloj(b)
    b.fijar_intensidad(1.0)
    antes = _render(b).pixelColor(960, 0)

    verde = QColor(0, 255, 0)
    b.poner_colores(verde, QColor(0, 0, 255), verde)
    # a mitad de la transición el color todavía no es el final
    reloj["t"] += BordeBrillo.DURACION_TRANSICION / 2
    medio = b._colores_actuales(reloj["t"])[2]
    assert medio.green() < 255 or medio.red() > 0

    # tras los 800 ms el brillo pintado es el nuevo (línea caliente en el borde exterior)
    reloj["t"] += BordeBrillo.DURACION_TRANSICION
    from descargador.ui.escena.estilo import acento_legible
    assert b._colores_actuales(reloj["t"])[2].rgb() == acento_legible(verde).rgb()
    despues = _render(b).pixelColor(960, 0)
    assert despues.green() > despues.red() + 80
    assert despues != antes


def test_intensidad_por_defecto_y_limites(app):
    b = _borde(app, "derecha")
    assert b._intensidad == pytest.approx(0.85)
    b.fijar_intensidad(3.0)
    assert b._intensidad == 1.0
    b.fijar_intensidad(-1)
    assert b._intensidad == 0.0


def test_respiracion_queda_entre_085_y_1(app):
    b = _borde(app, "izquierda")
    reloj = _reloj(b)
    valores = []
    for i in range(100):
        reloj["t"] = 100.0 + i * 0.1
        valores.append(b._factor_intensidad(reloj["t"]))
    assert min(valores) >= 0.85 - 1e-9
    assert max(valores) <= 1.0 + 1e-9
    assert max(valores) - min(valores) > 0.1   # de verdad respira


def test_nivel_del_audio_sigue_a_la_intensidad(app):
    b = _borde(app, "abajo")
    reloj = _reloj(b)
    b.fijar_nivel(0.0)
    for _ in range(40):
        reloj["t"] += 0.05
        bajo = b._factor_intensidad(reloj["t"])
    b.fijar_nivel(1.0)
    for _ in range(40):
        reloj["t"] += 0.05
        alto = b._factor_intensidad(reloj["t"])
    assert alto > bajo + 0.5


def test_timer_a_10_fps(app):
    # 10 cuadros bastan para un brillo que recorre el borde en 14 s (y son 4 ventanas)
    b = BordeBrillo("arriba")
    assert b._timer.interval() == 100
