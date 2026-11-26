# -*- coding: utf-8 -*-
"""Inicio ordenado (rejilla de carátulas por páginas, canciones para ti) y el reproductor en grande
(lo que sigue con fichas y filas que se arrastran). Sin red, sin motor de audio y sin ventanas."""

import os
import random
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, QPoint, QPointF, Qt, Signal  # noqa: E402
from PySide6.QtGui import QImage, QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import catalogo, mix_continuo  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(QImage()))
    monkeypatch.setattr(imagenes, "pedir", lambda *a, **k: None)


def pausa(app, s=0.15):
    fin = time.time() + s
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


def pista(i, **k):
    return dict(catalogo.nueva_pista(f"{i:011d}", f"Canción {i}", [{"nombre": f"Artista {i % 5}", "id": f"UC{i % 5}"}],
                                     duracion=180), **k)


@pytest.fixture
def rep(app, tmp_path, monkeypatch):
    from descargador import mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    r = Reproductor(Ajustes(), Coleccion(tmp_path / "c.db"))
    r.secuencia = [pista(i) for i in range(6)]
    r.original = list(r.secuencia)
    r.pos, r.actual = 1, r.secuencia[1]
    r.contexto = {"tipo": "album", "id": "A", "titulo": "Mi álbum"}
    return r


class Ctx(QObject):
    aviso = Signal(str)
    me_gusta_cambio = Signal(str, bool)

    def __init__(self, r):
        super().__init__()
        self.reproductor, self.coleccion, self.ajustes = r, r.coleccion, r.ajustes
        self.ventana = None
        self.hecho = []

    def __getattr__(self, n):
        if n.startswith("_"):
            raise AttributeError(n)

        def f(*a, **k):
            self.hecho.append((n, a, k))
        return f


# ================================================================ la rejilla

def test_columnas_y_paginas():
    from descargador.ui.paginas import rejilla_portadas as R
    assert [R.columnas_para(w) for w in (330, 616, 896, 1536)] == [3, 4, 5, 9]
    assert R.paginas_para(0, 4) == 0 and R.paginas_para(5, 4) == 1
    assert R.paginas_para(17, 4) == 2 and R.paginas_para(500, 4) == 3


def test_mezclar_no_repite_y_alterna():
    from descargador.ui.paginas.rejilla_portadas import mezclar
    cont = [{"tipo": "album", "id": i, "titulo": f"A{i}"} for i in (1, 1, 2)]
    sal = mezclar(cont, [pista(i) for i in (1, 2, 2, 3)])
    assert [x["titulo"] for x in sal] == ["A1", "Canción 1", "Canción 2", "Canción 3", "A2"]


def test_rejilla_pagina_marca_la_que_suena_y_se_pulsa(app, rep):
    from descargador.ui.paginas.rejilla_portadas import RejillaPortadas
    ctx = Ctx(rep)
    els = [{"tipo": "me_gusta", "especial": "me_gusta", "titulo": "Tus me gusta"},
           {"tipo": "album", "id": "A", "titulo": "Mi álbum"}] + [dict(pista(i), tipo="pista") for i in range(30)]
    w = RejillaPortadas(ctx, els)
    w.resize(700, 400)
    w.show()
    pausa(app)
    assert w.columnas == 4 and w.paginas == 3 and w.puntos.isVisible()
    assert w.es_la_que_suena(els[1]) and w.es_la_que_suena(els[3]) and not w.es_la_que_suena(els[0])
    sal = []
    w.abrir.connect(lambda e: sal.append(("abrir", e["titulo"])))
    w.reproducir.connect(lambda e: sal.append(("tocar", e["titulo"])))
    centro = lambda k: w.lienzo.rect_de(k).center().toPoint()  # noqa: E731
    QTest.mouseClick(w.lienzo, Qt.LeftButton, Qt.NoModifier, centro(1))
    QTest.mouseClick(w.lienzo, Qt.LeftButton, Qt.NoModifier, w.lienzo.rect_play(1).center().toPoint())
    QTest.mouseClick(w.lienzo, Qt.LeftButton, Qt.NoModifier, centro(2))
    assert sal == [("abrir", "Mi álbum"), ("tocar", "Mi álbum"), ("tocar", "Canción 0")]
    w.ir_a(1)
    pausa(app, 0.5)
    assert w.pagina == 1 and w.avance == 1.0
    QTest.mouseClick(w.lienzo, Qt.LeftButton, Qt.NoModifier, centro(0))
    assert sal[-1] == ("tocar", "Canción 6")
    assert not w.grab().isNull()
    w.resize(340, 400)                  # al achicarse cambia las columnas y no se sale
    pausa(app)
    assert w.columnas == 3 and w.lienzo.rect_de(2).right() <= w.lienzo.width() + 1
    w.poner([])
    assert w.isHidden()


def test_rejilla_se_repinta_sola_al_cambiar_de_cancion(app, rep):
    from descargador.ui.paginas.rejilla_portadas import RejillaPortadas
    w = RejillaPortadas(Ctx(rep), [dict(pista(i), tipo="pista") for i in range(8)])
    w.resize(700, 400)
    w.show()
    pausa(app)
    antes = w.grab().toImage()
    rep.actual = rep.secuencia[4]
    rep.pista_cambio.emit(rep.actual)
    pausa(app)
    assert w.grab().toImage() != antes


# ================================================================ Inicio

def test_lo_tuyo_y_volver_a_escuchar_no_repiten(tmp_path):
    from descargador.ui.paginas import inicio as I
    col = Coleccion(tmp_path / "c.db")
    r = random.Random(1)
    for _ in range(120):
        i = r.randrange(40)
        col.registrar_escucha(pista(i), {"tipo": "album", "id": f"a{i % 4}", "titulo": f"Álbum {i % 4}"})
    d = I.lo_tuyo(col)
    claves = [(e.get("tipo"), e.get("clave") or e.get("id")) for e in d["rejilla"]]
    assert len(claves) == len(set(claves)) and d["rejilla"][0]["especial"] == "me_gusta"
    assert {e["titulo"] for e in d["rejilla"] if e["tipo"] == "album"} == {f"Álbum {i}" for i in range(4)}
    assert d["recientes"] and isinstance(d["mixes_artistas"], list)


def test_canciones_para_ti_una_de_cada_mix():
    from descargador.ui.paginas.inicio import canciones_para_ti
    m = [{"pistas": [pista(1), pista(2)]}, {"pistas": [pista(1), pista(3)]}, {}]
    assert [p["titulo"] for p in canciones_para_ti(m)] == ["Canción 1", "Canción 2", "Canción 3"]
    assert canciones_para_ti(None) == []


def test_pagina_inicio_orden_sin_repetir_y_sin_bloquear(app, rep, monkeypatch):
    from descargador.ui.paginas import inicio as I
    col = rep.coleccion
    r = random.Random(2)
    for _ in range(200):
        i = min(79, int(abs(r.gauss(0, 30))))
        col.registrar_escucha(pista(i), {"tipo": "album", "id": f"a{i % 5}", "titulo": f"Álbum {i % 5}"})
    monkeypatch.setattr(catalogo, "inicio", lambda: {"secciones": []})
    monkeypatch.setattr(catalogo, "radio", lambda *a, **k: {"pistas": [pista(i) for i in range(100, 140)]})
    leidas = []
    original = type(col).escuchado_hace_poco

    def espia(self, *a):
        leidas.append(self is col)
        return original(self, *a)
    monkeypatch.setattr(type(col), "escuchado_hace_poco", espia)
    from descargador.ui.paginas.comun import _CACHE
    _CACHE.clear()
    ctx = Ctx(rep)
    ctx.cuenta = {"nombre": "Ana"}
    p = I.PaginaInicio(ctx)
    p.resize(900, 700)
    p.show()
    fin = time.time() + 10
    while time.time() < fin and not (p.caja_para_ti.isVisible() and p.rejilla.isVisible()):
        pausa(app, 0.05)
    assert p.rejilla.isVisible() and p.caja_para_ti.isVisible()
    assert not any(leidas), "la base de la interfaz no se lee para pintar Inicio"
    # el orden: rejilla, canciones para ti, volver a escuchar, mixes... y los accesos pequeños al final
    orden = [p.zv.itemAt(i).widget() for i in range(p.zv.count())]
    pos = [orden.index(w) for w in (p.rejilla, p.caja_para_ti, p.caja_recientes, p.caja_mixes, p.caja_descubre,
                                    p.caja_tiempo, p.caja_artistas, p.caja_extras)]
    assert pos == sorted(pos)
    from descargador.ui.paginas.rejilla_portadas import clave_de
    from descargador.ui.componentes import Tarjeta
    arriba = {clave_de(e) for e in p.rejilla.visibles()}
    assert p.caja_recientes.isVisible()
    abajo = {clave_de(dict(x.el, tipo="pista")) for x in p.caja_recientes.findChildren(Tarjeta)}
    assert abajo
    assert not arriba & abajo
    for ancho in (380, 640, 1000, 1600):
        p.resize(ancho, 700)
        pausa(app, 0.1)
        assert p.lienzo.width() <= p.viewport().width(), f"se desborda a {ancho}"
    p.refrescar_recientes()
    p._filtrar("videos")
    p._filtrar("musica")
    pausa(app, 0.5)
    p._filtrar("disco")
    pausa(app, 0.1)


def test_rejilla_de_canciones_segun_el_ancho(app, rep):
    from descargador.ui.componentes import FilaCompacta, RejillaRapida
    ctx = Ctx(rep)
    w = RejillaRapida(ctx, "Canciones para ti", [pista(i) for i in range(30)], columnas=4)
    w.resize(1300, 400)
    w.show()
    pausa(app)
    visibles = [f for f in w.findChildren(FilaCompacta) if f.isVisible()]
    assert len(visibles) == 16 and w.puntos.total == 2
    w.resize(330, 400)
    pausa(app)
    visibles = [f for f in w.findChildren(FilaCompacta) if f.isVisible()]
    assert len(visibles) == 4 and w.puntos.total == 3 and w.bt_todo.text().strip() == "Todo"
    w.ir_a(1)
    f = next(f for f in w.findChildren(FilaCompacta) if f.isVisible())
    QTest.mouseClick(f, Qt.LeftButton, Qt.NoModifier, QPoint(20, 30))
    assert ctx.hecho[-1][0] == "reproducir_lista" and ctx.hecho[-1][1][1] == 4
    QTest.mouseClick(f, Qt.LeftButton, Qt.NoModifier, f._r_puntos().center())
    assert ctx.hecho[-1][0] == "menu_pista"
    w.bt_todo.click()
    assert ctx.hecho[-1][1][1] == 0


# ================================================================ la cola

def test_mover_en_secuencia(rep):
    r = rep
    r.mover_en_secuencia(2, 5)
    assert [p["titulo"] for p in r.secuencia] == [f"Canción {i}" for i in (0, 1, 3, 4, 5, 2)]
    assert r.original == r.secuencia                  # sin aleatorio el orden nuevo es el de la lista
    antes = list(r.secuencia)
    for o, d in ((1, 3), (0, 2), (2, 1), (2, 9), (3, 3)):      # ni lo que ya sonó ni fuera de la cola
        r.mover_en_secuencia(o, d)
    assert r.secuencia == antes
    r.aleatorio = True
    r.mover_en_secuencia(5, 2)
    assert r.original == antes


def test_arrastrar_por_el_asa_reordena(app, rep):
    from descargador.ui.sonando import ALTO_FILA, ColaReordenable
    ctx = Ctx(rep)
    w = ColaReordenable(ctx)
    w.resize(320, w.height())
    w.show()
    pausa(app)
    assert [f[4]["titulo"] for f in w.filas] == [f"Canción {i}" for i in (2, 3, 4, 5)]

    def raton(tipo, y, boton=Qt.LeftButton, x=300):
        p = QPointF(x, y)
        return QMouseEvent(tipo, p, w.mapToGlobal(p), boton, boton, Qt.NoModifier)
    w.mouseMoveEvent(raton(QMouseEvent.MouseMove, 30, Qt.NoButton))
    assert w.property("sin_arrastre") is True          # en el asa, la lista no se desplaza: se mueve la canción
    w.mousePressEvent(raton(QMouseEvent.MouseButtonPress, 30))
    w.mouseMoveEvent(raton(QMouseEvent.MouseMove, 30 + 2 * ALTO_FILA))
    assert w._arrastre["destino"] == 2 and not w.grab().isNull()
    w.mouseReleaseEvent(raton(QMouseEvent.MouseButtonRelease, 30 + 2 * ALTO_FILA))
    assert [p["titulo"] for p in rep.secuencia[2:]] == [f"Canción {i}" for i in (3, 4, 2, 5)]
    w.rehacer()
    w.mouseMoveEvent(raton(QMouseEvent.MouseMove, 30, Qt.NoButton, 150))
    assert w.property("sin_arrastre") is False
    w._quitar(0)
    assert [p["titulo"] for p in rep.secuencia[2:]] == ["Canción 4", "Canción 2", "Canción 5"]
    ctx.hecho[-1][1][1]()                              # deshacer
    assert rep.secuencia[2]["titulo"] == "Canción 3"


def test_un_clic_en_las_rayas_abre_como_moverla(app, rep, monkeypatch):
    from PySide6.QtWidgets import QMenu
    from descargador.ui.sonando import ALTO_FILA, ColaReordenable
    w = ColaReordenable(Ctx(rep))
    w.resize(320, w.height())
    w.show()
    pausa(app)
    abiertos = []
    monkeypatch.setattr(ColaReordenable, "_menu_mover", lambda self, i, donde: abiertos.append(i))

    def raton(tipo, y, boton=Qt.LeftButton):
        p = QPointF(300, y)
        return QMouseEvent(tipo, p, w.mapToGlobal(p), boton, boton, Qt.NoModifier)
    antes = [p["titulo"] for p in rep.secuencia]
    w.mousePressEvent(raton(QMouseEvent.MouseButtonPress, ALTO_FILA + 30))     # segunda canción, en las rayas
    w.mouseReleaseEvent(raton(QMouseEvent.MouseButtonRelease, ALTO_FILA + 32))
    assert abiertos == [1] and antes == [p["titulo"] for p in rep.secuencia]   # abre el menú, no mueve nada
    m = QMenu()
    w._acciones_mover(m, 1)
    textos = [a.text() for a in m.actions()]
    assert textos[:2] == ["Subir", "Bajar"] and "Ponerla la última" in textos and "Quitar de la cola" in textos
    m.actions()[0].trigger()
    assert rep.secuencia[2]["titulo"] == "Canción 3"


def test_grupos_de_la_cola_y_no_se_mezclan(app, rep):
    from descargador.ui.sonando import ColaReordenable
    rep.proximas = [pista(20), pista(21)]
    rep.secuencia += [pista(30, _auto=True), pista(31, _auto=True)]
    w = ColaReordenable(Ctx(rep))
    assert [f[1] for f in w.filas if f[0] == "titulo"] == ["Siguiente en tu cola", "Siguiente de: Mi álbum",
                                                           "Y después, canciones parecidas"]
    antes = list(rep.secuencia)
    w.mover(1, 4)                  # de «tu cola» al álbum: no
    assert rep.secuencia == antes and rep.proximas[0]["titulo"] == "Canción 20"
    w.mover(1, 2)
    assert rep.proximas[0]["titulo"] == "Canción 21"
    corta = ColaReordenable(Ctx(rep), limite=3)
    assert sum(f[0] == "pista" for f in corta.filas) == 3


# ================================================================ las fichas

def test_populares_intercala_artistas_y_descubrir_quita_lo_oido(tmp_path, monkeypatch):
    col = Coleccion(tmp_path / "c.db")
    col.registrar_escucha(pista(50))
    col.alternar_me_gusta(pista(51))
    monkeypatch.setattr(catalogo, "radio", lambda *a, **k: {"pistas": [pista(i) for i in range(50, 56)]})
    monkeypatch.setattr(catalogo, "artista", lambda i: {"secciones": [
        {"elementos": [dict(pista(100 + 10 * int(i[2:]) + k)) for k in range(4)]}]})
    r = mix_continuo.candidatas(col, pista(1), "populares")["pistas"]
    assert r[0]["titulo"] == "Canción 110" and len({p["video_id"] for p in r}) == len(r) == 20
    from descargador import recomendador
    monkeypatch.setattr(recomendador, "radio_inteligente", lambda c, p: {"pistas": [pista(i) for i in (50, 52)]})
    r = mix_continuo.candidatas(col, pista(1), "descubrir")["pistas"]
    assert [p["titulo"] for p in r] == ["Canción 52", "Canción 53", "Canción 54", "Canción 55"]
    assert mix_continuo.valido("poco conocidas") == "todo"


def test_elegir_ficha_solo_cambia_las_automaticas(app, rep, monkeypatch):
    rep.secuencia += [pista(30, _auto=True)]
    monkeypatch.setattr(mix_continuo, "candidatas",
                        lambda c, p, t: {"pistas": [pista(i) for i in (3, 60, 61)]} if t == "populares" else {"pistas": []})
    avisos = []
    rep.aviso.connect(avisos.append)
    rep.elegir_mix("populares")
    assert rep.mix_cargando
    fin = time.time() + 5
    while rep.mix_cargando and time.time() < fin:
        pausa(app, 0.02)
    assert [p["titulo"] for p in rep.secuencia] == [f"Canción {i}" for i in (0, 1, 2, 3, 4, 5, 60, 61)]
    assert all(p.get("_auto") for p in rep.secuencia[6:]) and rep.tipo_mix == "populares"
    rep.elegir_mix("descubrir")
    while rep.mix_cargando and time.time() < fin:
        pausa(app, 0.02)
    assert rep.tipo_mix == "populares" and avisos and len(rep.secuencia) == 8      # nada que poner: se queda como estaba


# ================================================================ la pantalla

def test_pantalla_sonando(app, rep):
    from descargador.ui.sonando import PaginaSonando
    ctx = Ctx(rep)
    w = PaginaSonando(ctx)
    w.resize(1000, 640)
    w.show()
    pausa(app)
    rep.duracion_cambio.emit(200.0)
    rep.posicion_cambio.emit(50.0)
    assert w.et_total.text() == "3:20" and w.et_pos.text() == "0:50" and abs(w.barra.valor - 0.25) < 0.01
    assert w.portada.titulo == "Canción 1" and w.der.isVisible() and w.bt_play.width() >= 70
    assert w.continua.et_titulo.text() == "Mi álbum"
    for ancho, alto in ((1000, 640), (560, 620), (380, 560), (1500, 900)):
        w.resize(ancho, alto)
        pausa(app, 0.1)
        assert w.lienzo.width() <= w.viewport().width() and w.portada.height() >= 150
        assert not w.grab().isNull()
    salio = []
    w.volver.connect(lambda: salio.append(1))
    w.bt_volver.click()
    QTest.keyClick(w, Qt.Key_Escape)
    assert len(salio) == 2
    rep.actual = None
    rep.pista_cambio.emit(None)
    assert w.portada.titulo == "Nada sonando"


def test_panel_derecho_con_la_cola_dentro(app, rep):
    from descargador.ui.panel_derecho import VistaCola, VistaSonando
    rep.proximas = []
    ctx = Ctx(rep)
    v = VistaSonando(ctx)
    v.resize(320, 700)
    v.show()
    pausa(app)
    assert v.portada.titulo == "Canción 1" and len([f for f in v.continua.cola.filas if f[0] == "pista"]) == 4
    c = VistaCola(ctx)
    c.resize(320, 700)
    c.show()
    pausa(app)
    assert c.fila.pista["titulo"] == "Canción 1"
    rep.pos, rep.actual = 2, rep.secuencia[2]
    rep.pista_cambio.emit(rep.actual)
    rep.cola_cambio.emit()
    pausa(app, 0.2)
    assert c.fila.pista["titulo"] == "Canción 2" and len(c.continua.cola.filas) == 3
