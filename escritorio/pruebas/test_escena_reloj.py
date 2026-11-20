# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.ui.escena.estilo import acento_legible  # noqa: E402
from descargador.ui.escena.reloj import RelojGigante, texto_fecha, texto_hora  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _reloj(ancho, alto, hora):
    w = RelojGigante()
    w.resize(ancho, alto)
    w.fijar_ahora(lambda: hora)
    w.fijar_24h(True)
    return w


def _pintar_en_imagen(w):
    img = QImage(w.width(), w.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    w.render(p, QPoint(0, 0))
    p.end()
    return img


def test_texto_hora_24h(app):
    assert texto_hora(datetime(2026, 11, 20, 7, 5), True) == "7:05"
    assert texto_hora(datetime(2026, 11, 20, 19, 5), True) == "19:05"
    assert texto_hora(datetime(2026, 11, 20, 0, 30), True) == "0:30"
    assert texto_hora(datetime(2026, 11, 20, 19, 5)) == "19:05"  # por defecto 24h


def test_texto_hora_12h(app):
    assert texto_hora(datetime(2026, 11, 20, 19, 5), False) == "7:05"
    assert texto_hora(datetime(2026, 11, 20, 0, 30), False) == "12:30"
    assert texto_hora(datetime(2026, 11, 20, 12, 0), False) == "12:00"
    assert texto_hora(datetime(2026, 11, 20, 7, 5), False) == "7:05"


def test_texto_fecha(app):
    assert texto_fecha(datetime(2026, 11, 20)) == "vie 20 nov"
    assert texto_fecha(datetime(2026, 1, 1)) == "jue 1 ene"


def test_sizehint_560x320(app):
    w = RelojGigante()
    assert w.sizeHint().width() == 560 and w.sizeHint().height() == 320


def test_pintar_560x320_no_falla(app):
    w = _reloj(560, 320, datetime(2026, 11, 20, 19, 5))
    img = _pintar_en_imagen(w)
    assert img.width() == 560 and img.height() == 320
    # algo se ha pintado (hay píxeles con alfa)
    assert any(img.pixelColor(x, y).alpha() > 0 for x in range(0, 560, 8) for y in range(0, 320, 8))


def test_pintar_200x100_no_falla(app):
    w = _reloj(200, 100, datetime(2026, 11, 20, 19, 5))
    img = _pintar_en_imagen(w)
    assert img.width() == 200 and img.height() == 100
    assert any(img.pixelColor(x, y).alpha() > 0 for x in range(0, 200, 4) for y in range(0, 100, 4))


def _caja_dibujada(w, m):
    caja = QRectF()
    for i in range(len(m.texto)):
        caja = caja.united(w._camino(m, i).boundingRect())
    return caja


def test_digito_suelto_ocupa_86_por_ciento_y_va_a_la_derecha(app):
    # un solo carácter nunca llega al tope de ancho, así que manda la altura (86 %)
    w = _reloj(560, 320, datetime(2026, 11, 20, 19, 5))
    m = w._maquetar("0")
    caja = _caja_dibujada(w, m)
    assert abs(caja.height() - 0.88 * 320) <= 0.01 * 320
    assert abs(caja.right() - 560 * (1 - 0.035)) <= 1.5


def test_hora_respeta_altura_o_tope_de_ancho(app):
    # la regla: alto 86 %, pero si la hora no cabe en el ancho se reduce (no se corta)
    w = _reloj(200, 100, datetime(2026, 11, 20, 19, 5))
    m = w._maquetar("19:05")
    caja = _caja_dibujada(w, m)
    assert caja.width() <= 200 * 0.965 + 0.5
    assert caja.left() >= -0.5
    assert abs(caja.right() - 200 * (1 - 0.035)) <= 1.5
    esperado = min(0.88 * 100, 0.96 * 200 * caja.height() / caja.width())
    assert abs(caja.height() - esperado) <= 0.5


def test_transicion_al_cambiar_minuto_y_termina(app):
    w = RelojGigante()
    w.resize(560, 320)
    w.show()
    hora = [datetime(2026, 11, 20, 19, 5)]
    w.fijar_ahora(lambda: hora[0])
    reloj_falso = [100.0]
    w._monotonic = lambda: reloj_falso[0]
    assert w._texto == "19:05" and w._trans_dig is None   # fijar_ahora muestra en el acto
    hora[0] = datetime(2026, 11, 20, 19, 6)               # el reloj avanza un minuto
    w._comprobar()
    assert w._trans_dig is not None
    assert w._anim.isActive()
    reloj_falso[0] = 100.3                       # a mitad de la transición de 650 ms
    w._tick_animacion()
    assert w._trans_dig is not None
    reloj_falso[0] = 100.7                       # ya pasaron los 650 ms
    w._tick_animacion()
    assert w._trans_dig is None
    assert not w._anim.isActive()
    w.hide()


def test_solo_animan_los_digitos_que_cambian(app):
    hora = [datetime(2026, 11, 20, 19, 5)]
    w = RelojGigante()
    w.resize(560, 320)
    w.show()
    w.fijar_ahora(lambda: hora[0])
    hora[0] = datetime(2026, 11, 20, 19, 6)
    w._comprobar()
    assert [ii for ii, _ in w._trans_dig["pares"]] == [4]
    w.hide()
    hora2 = [datetime(2026, 11, 20, 19, 59)]
    w2 = RelojGigante()
    w2.resize(560, 320)
    w2.show()
    w2.fijar_ahora(lambda: hora2[0])
    hora2[0] = datetime(2026, 11, 20, 20, 0)
    w2._comprobar()
    # 19:59 -> 20:00: los cuatro dígitos cambian; los ':' (índice 2) no se animan
    assert sorted(ii for ii, _ in w2._trans_dig["pares"]) == [0, 1, 3, 4]
    w2.hide()


def test_sin_cambio_de_minuto_no_hay_transicion(app):
    w = _reloj(560, 320, datetime(2026, 11, 20, 19, 5))
    w.show()
    w.fijar_ahora(lambda: datetime(2026, 11, 20, 19, 5))
    w._comprobar()
    assert w._trans_dig is None
    w.hide()


def test_transicion_de_colores_700_ms(app):
    w = _reloj(560, 320, datetime(2026, 11, 20, 19, 5))
    w.show()
    reloj_falso = [0.0]
    w._monotonic = lambda: reloj_falso[0]
    inicial = w._acento_actual()
    destino = acento_legible(QColor("#00AAFF"))
    w.poner_colores(QColor("#00FF00"), QColor("#000000"), QColor("#00AAFF"))
    reloj_falso[0] = 0.35
    medio = w._acento_actual()
    assert medio != inicial and medio != destino
    reloj_falso[0] = 0.8
    w._tick_animacion()
    assert w._trans_col is None
    assert w._acento_actual() == destino
    w.hide()


def test_fijar_ahora_muestra_la_hora_en_el_acto(app):
    w = RelojGigante()
    w.resize(560, 320)
    w.fijar_ahora(lambda: datetime(2026, 11, 20, 7, 5))
    assert w._texto == "7:05"
    assert w._fecha == "vie 20 nov"
    assert w._trans_dig is None


def test_fijar_24h_cambia_el_formato(app):
    w = _reloj(560, 320, datetime(2026, 11, 20, 19, 5))
    assert w._texto == "19:05"
    w.fijar_24h(False)
    assert w._texto == "7:05"
    w.fijar_24h(True)
    assert w._texto == "19:05"
