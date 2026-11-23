# -*- coding: utf-8 -*-
"""Escenarios con ilustración: sus imágenes existen, «Mi imagen o GIF» reproduce un GIF, el ratón suelta
partículas y los escenarios quedan reservados a donadores (menos videoclip y carátula)."""
import os
import sys
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from descargador.ui.escena import escenarios
from descargador.ui.escena import ventana as V
from descargador.ui.escena.escenarios import imagen_motor, imagenes, propia


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_todas_las_ilustraciones_estan():
    for nombre in dir(imagenes):
        clase = getattr(imagenes, nombre)
        if isinstance(clase, type) and issubclass(clase, imagen_motor.EscenarioImagen) and clase.IMAGEN:
            ruta = os.path.join(imagen_motor.CARPETA, clase.IMAGEN)
            assert os.path.isfile(ruta), ruta
            assert not QImage(ruta).isNull(), ruta


def test_solo_quedan_los_escenarios_pedidos():
    assert set(escenarios.ESCENARIOS) == {"retro", "synthwave", "lofi", "cyberpunk", "samurai", "cinnamoroll",
                                          "pompompurin", "mymelody", "hellokitty", "kuromi", "ippo", "kaneki",
                                          "goku", "propia"}


def test_gif_propio_se_reproduce(app, tmp_path):
    from PIL import Image
    ruta = tmp_path / "anim.gif"
    cuadros = [Image.new("RGB", (64, 36), c) for c in ((200, 30, 30), (30, 200, 30), (30, 30, 200))]
    cuadros[0].save(ruta, save_all=True, append_images=cuadros[1:], duration=50, loop=0)
    propia.fijar_ruta(str(ruta))
    w = escenarios.crear("propia")
    assert w is not None and w._movie is not None
    w.resize(640, 360)
    img = QImage(640, 360, QImage.Format_ARGB32_Premultiplied)
    for _ in range(3):
        w._cuadro()
        w.render(img)
    propia.fijar_ruta("")


def test_clic_suelta_particulas(app):
    w = escenarios.crear("kuromi")
    w.resize(800, 450)
    img = QImage(800, 450, QImage.Format_ARGB32_Premultiplied)
    w.render(img)
    w.soltar(400, 200, 10, 200)
    assert len(w._trazo) == 10
    w._cuadro()
    w.render(img)


def test_los_escenarios_son_de_donadores():
    assert V.FONDOS_LIBRES == ("video", "ambiente")
    avisos = []
    esc = types.SimpleNamespace(ctx=types.SimpleNamespace(avisar=avisos.append, premium=None,
                                                          ajustes={"escena_fondo": "video"}))
    esc._es_donador = lambda: False
    esc._preguntar_donador = lambda pendiente=None: False      # sin gestor premium: no hay a quién preguntar
    esc._avisar_solo_donadores = lambda: avisos.append(V.EscenaEscritorio.AVISO_SOLO_DONADORES)
    puesto = []
    esc.poner_fondo = puesto.append
    esc._ruta_propia_valida = lambda: True
    acc = types.SimpleNamespace(data=lambda: "goku")
    V.EscenaEscritorio._fondo_elegido(esc, acc)
    assert puesto == [] and avisos and "donadores" in avisos[0]
    acc = types.SimpleNamespace(data=lambda: "ambiente")
    V.EscenaEscritorio._fondo_elegido(esc, acc)
    assert puesto == ["ambiente"]
