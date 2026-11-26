# -*- coding: utf-8 -*-
"""Letras épicas de la escena (ui/epica): cómo se cortan los versos en planos, que todos los diseños se pintan
en cualquier instante (adelante, atrás, al irse) sin pasarse de tiempo, y cómo las usa la escena."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_dejar_rastro(app):
    from descargador.ui import epica, tipografia_letra
    antes = epica.actual(), tipografia_letra.actual()
    yield
    epica.fijar(antes[0])
    tipografia_letra.fijar(antes[1])


VERSOS = [(0, "Corazón roto en la ciudad", 1000, 1500, 3600), (1, "No me olvides", 3600, 1200, 6000),
          (2, "(Oh-oh) — sí", 6000, 900, 9000), (3, "Ya", 9000, 400, None)]


def montaje(clave, versos=VERSOS):
    from descargador.ui import epica
    from descargador.ui.escena.letra import repartir_palabras
    return epica.Montaje(clave, versos, repartir_palabras)


def lienzo(w=660, h=330, golpe=0.6):
    from descargador.ui import epica, estilo_letra
    return epica.Lienzo(w, h, 1.0, estilo_letra.Colores("#FF4FD8", "#7C5CFF", "#2EE6F0"), 0.5, golpe)


def pintar(m, t, cx):
    img = QImage(int(cx.w), int(cx.h), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    p.translate(cx.w / 2, cx.h / 2)
    algo = m.pintar(p, t, cx)
    p.end()
    return algo, img


def tinta(img):
    """Píxeles con algo pintado (muestreando)."""
    return sum(1 for y in range(0, img.height(), 6) for x in range(0, img.width(), 6)
               if QColor.fromRgba(img.pixel(x, y)).alpha() > 40)


def _claves():
    from descargador.ui import epica
    return list(epica.NOMBRES)


# ------------------------------------------------------------------ planos

def test_las_palabras_cortas_no_se_quedan_solas():
    from descargador.ui.epica import trocear
    assert trocear(["Corazón", "de", "melón"], 1, 9) == [[0], [1, 2]]
    assert trocear(["vamos", "a", "bailar", "ya"], 3, 18) == [[0, 1, 2, 3]] or trocear(
        ["vamos", "a", "bailar", "ya"], 3, 18)[-1] != [3]
    assert trocear([], 3, 10) == []
    # una palabra larguísima va sola aunque pase del tope
    assert trocear(["supercalifragilístico", "sí"], 2, 8)[0][0] == 0


def test_los_planos_cubren_toda_la_letra_en_orden(app):
    for clave in _claves():
        m = montaje(clave)
        inicios = [pl.t0 for pl in m.planos]
        assert inicios == sorted(inicios), clave
        for a, b in zip(m.planos, m.planos[1:]):
            assert a.t0 < a.t1 <= b.t0 + 1e-6, clave       # nunca dos planos vivos a la vez
        dichas = " ".join(x for pl in m.planos if pl.linea == 0 for x in pl.textos)
        assert dichas == "Corazón roto en la ciudad", clave


def test_los_simbolos_sueltos_no_ocupan_pantalla(app):
    m = montaje("impacto")
    textos = [x for pl in m.planos if pl.linea == 2 for x in pl.textos]
    assert textos == ["Oh-oh", "sí"]


def test_edit_total_el_coro_siempre_igual_y_no_repite_seguido(app):
    coro = "Bailando hasta el amanecer"
    versos = [(i, t, i * 2000, 1500, (i + 1) * 2000) for i, t in enumerate(
        ["Primera frase de la noche", coro, "Otra cosa que contar hoy", "Y nadie sabe nada", coro, "Final"])]
    m = montaje("edit", versos)
    por_linea = {}
    for pl in m.planos:
        por_linea.setdefault(pl.linea, set()).add(pl.estilo)
    assert all(len(s) == 1 for s in por_linea.values())
    assert por_linea[1] == por_linea[4]
    assert len({next(iter(s)) for s in por_linea.values()}) >= 3
    assert next(iter(por_linea[0])) != next(iter(por_linea[1]))


def test_fuera_de_los_planos_no_se_pinta_nada(app):
    m = montaje("viral")
    cx = lienzo()
    assert m.indice(0.2) == -1 and not m.viva(0.2)
    assert pintar(m, 0.2, cx)[0] is False
    assert not m.viva(60.0)
    assert pintar(m, 60.0, cx)[0] is False


# ------------------------------------------------------------------ pintar

@pytest.mark.parametrize("clave", _claves())
def test_cada_diseno_se_pinta_en_cualquier_momento(app, clave):
    m = montaje(clave)
    cx = lienzo()
    visto = 0
    t = 0.9
    while t < 11.0:
        _algo, img = pintar(m, t, cx)
        visto = max(visto, tinta(img))
        t += 0.11
    assert visto > 60, "no se vio nada"
    # hacia atrás y a otro tamaño: igual de válido
    for t, tam in ((2.0, (300, 150)), (1.2, (1200, 500)), (3.7, (200, 400))):
        assert pintar(m, t, lienzo(*tam))[0]


@pytest.mark.parametrize("clave", _claves())
def test_cada_diseno_es_legible_cuando_se_asienta(app, clave):
    m = montaje(clave)
    cx = lienzo(golpe=0.0)
    assert tinta(pintar(m, 1.6, cx)[1]) > 120


@pytest.mark.parametrize("clave", _claves())
def test_cada_diseno_cabe_en_un_cuadro(app, clave):
    """A 60 por segundo hay 16 ms para todo: la letra no puede llevarse más de una parte."""
    m = montaje(clave)
    cx = lienzo()
    for i in range(len(m.planos)):
        m.preparado(i, cx)
    tiempos = []
    t = 1.0
    while t < 6.0:
        a = time.perf_counter()
        pintar(m, t, cx)
        tiempos.append(time.perf_counter() - a)
        t += 1 / 30
    tiempos.sort()
    assert tiempos[len(tiempos) // 2] < 0.012, f"{clave}: {tiempos[len(tiempos) // 2] * 1000:.1f} ms"


def test_lo_caro_se_guarda_y_se_rehace_si_cambia_algo(app):
    from descargador.ui import epica
    m = montaje("cromo")
    cx = lienzo()
    a = m.preparado(0, cx)
    assert m.preparado(0, cx) is a
    assert m.preparado(0, lienzo(500, 250)) is not a
    for i in range(len(m.planos)):
        m.preparado(i, cx)
    assert len(m._prep) <= epica.GUARDADOS


def test_se_adelanta_el_plano_que_viene(app):
    m = montaje("glitch")
    cx = lienzo()
    veces = 0
    while m.adelantar(0.0, cx):
        veces += 1
        assert veces < 10
    assert 1 <= veces <= 4 and 0 in m._prep


def test_el_tipo_de_letra_elegido_manda(app):
    from descargador.ui import tipografia_letra
    from descargador.ui.epica.base import fuente
    assert fuente("anton")[1] == "anton"
    tipografia_letra.fijar("pacifico")
    assert fuente("anton")[1] == "pacifico"


# ------------------------------------------------------------------ la letra de la escena

def lineas():
    return [{"ms": 1000, "texto": "Corazón roto en la ciudad", "canto": 1500}, {"ms": 3600, "texto": "No me olvides",
                                                                               "canto": 1200},
            {"ms": 6000, "texto": "", "pausa": True}, {"ms": 9000, "texto": "Vuelve", "canto": 900}]


def test_la_escena_pinta_la_epica_y_cambia_en_vivo(app):
    from descargador.ui import epica
    from descargador.ui.escena.letra import LetraCinetica
    epica.fijar("eco")
    w = LetraCinetica(con_epica=True)
    w.resize(660, 330)
    w.show()
    w.poner_lineas(lineas(), True)
    assert w.epica_puesta() == "eco"
    w.fijar_audio(0.5, 0.8)
    w.fijar_ms(1800)
    assert w.indice_actual() == 0
    a = w.grab().toImage()
    epica.fijar("eco_espejo")
    assert w.epica_puesta() == "eco_espejo"
    assert w.grab().toImage() != a
    epica.fijar("")                                   # la letra normal
    assert w.epica_puesta() == "" and not w.grab().isNull()
    w.close()


def test_sin_con_epica_la_letra_es_la_de_siempre(app):
    from descargador.ui import epica
    from descargador.ui.escena.letra import LetraCinetica
    epica.fijar("fuego")
    w = LetraCinetica()
    assert w.epica_puesta() == ""
    w.close()


def test_con_traduccion_pausa_y_texto_sin_tiempos(app):
    from descargador.ui import epica
    from descargador.ui.escena.letra import LetraCinetica
    epica.fijar("edit")
    w = LetraCinetica(con_epica=True)
    w.resize(660, 330)
    w.show()
    w.poner_lineas(lineas(), True)
    w.fijar_traducciones(["Broken heart", "Don't forget me", None, "Come back"])
    for ms in (0, 1500, 3700, 7000, 9300, 20000, 1200):
        w.fijar_ms(ms)
        assert not w.grab().isNull()
    w.poner_lineas([{"texto": "sin tiempos"}], False)
    assert not w.grab().isNull()
    w.poner_mensaje("Buscando la letra…")
    assert not w.grab().isNull()
    w.close()


def test_el_borde_se_apaga_para_no_cortar_en_seco(app):
    from descargador.ui.escena.letra import LetraCinetica
    w = LetraCinetica(con_epica=True)
    m = w._borde_suave(400, 200, 1.0)
    assert QColor.fromRgba(m.pixel(0, 100)).alpha() < 10
    assert QColor.fromRgba(m.pixel(200, 100)).alpha() == 255


def test_el_selector_elige_la_epica_y_un_estilo_normal_la_quita(app):
    from descargador.ui import epica, estilo_letra
    from descargador.ui.selector_letra import DialogoLetra

    class Aj(dict):
        def guardar(self):
            pass

    class Ctx:
        ajustes = Aj()
    ctx = Ctx()
    epica.fijar("")
    d = DialogoLetra(ctx, None, sin_marco=True)
    d.resize(600, 600)
    d.show()
    d.selector.elegir_epica("eco_color")
    assert epica.actual() == "eco_color" and ctx.ajustes["letra_epica"] == "eco_color"
    assert d.selector.muestra_epica("eco_color").isChecked()
    assert not d.grab().isNull()
    d.selector.elegir_estilo("oro")                   # en la escena: se quiere ver ese estilo
    assert epica.actual() == "" and estilo_letra.actual() == "oro"
    d.selector.restablecer()
    estilo_letra.fijar(estilo_letra.POR_DEFECTO)
    d.close()
    # fuera de la escena, elegir un estilo no toca la épica
    epica.fijar("eco_frase")
    d = DialogoLetra(ctx, None)
    d.selector.elegir_estilo("neon")
    assert epica.actual() == "eco_frase"
    estilo_letra.fijar(estilo_letra.POR_DEFECTO)
    d.close()


def test_el_fuego_trae_su_textura(app):
    from descargador.ui.epica.base import FUEGO_COL, FUEGO_H, FUEGO_N, FUEGO_W, hoja
    h = hoja("fuego.png")
    assert (h.width(), h.height()) == (FUEGO_W * FUEGO_COL, FUEGO_H * (FUEGO_N // FUEGO_COL))


def test_solo_se_ofrecen_la_clasica_y_el_eco_con_sus_variantes(app):
    from descargador.ui import epica, estilo_letra
    assert epica.OFRECIDAS[0] == "eco" and all(k.startswith("eco") for k in epica.OFRECIDAS)
    assert epica.normalizar("impacto") == "" and epica.normalizar("edit") == "" and epica.POR_DEFECTO == ""
    for k in epica.OFRECIDAS:                         # todas se montan y se pintan
        m = montaje(k)
        assert m.planos
    from types import SimpleNamespace
    from descargador.ui.selector_letra import SelectorLetra

    class Aj(dict):
        def guardar(self):
            pass
    aj = Aj()
    s = SelectorLetra(SimpleNamespace(ajustes=aj), en_escena=True)
    try:
        from descargador.ui import presentacion_letra as P
        claves = [m.pres["clave"] for m in s.epicas.muestras]
        assert claves == [p["clave"] for p in P.lista()] and claves[0] == "original" and len(set(claves)) == len(claves)
        assert claves[-len(epica.OFRECIDAS):] == list(epica.OFRECIDAS)
        ola = next(m for m in s.epicas.muestras if m.pres["clave"] == "tuya_ola")
        s.elegir_presentacion(ola)
        assert epica.actual() == "" and estilo_letra.movimiento() == "ola" and aj["letra_movimiento"] == "ola"
        assert not estilo_letra.original() and aj["letra_original"] is False
        assert s.muestra_epica("").pres["clave"] == "tuya_ola" and s.muestra_epica("").isChecked()
        neon = next(m for m in s.epicas.muestras if m.pres["clave"] == "original_neon")
        s.elegir_presentacion(neon)
        assert estilo_letra.original() and estilo_letra.efectivo() == "neon" and aj["letra_acabado_original"] == "neon"
        assert P.actual()["clave"] == "original_neon"
        s.elegir_presentacion(s.epicas.muestras[-1])
        assert epica.actual() == epica.OFRECIDAS[-1] and aj["letra_epica_elegida"]
        vistas = set()                                     # N recorre todas y vuelve al principio
        p = P.actual()
        for _ in range(len(claves)):
            p = P.siguiente(p)
            vistas.add(p["clave"])
        assert vistas == set(claves)
        for m in s.epicas.muestras:                        # todas las miniaturas se pintan
            m.construir()
    finally:
        epica.fijar("")
        estilo_letra.fijar_movimiento("clasica")
        estilo_letra.fijar_original(False, "clasica")
        s.deleteLater()
