# -*- coding: utf-8 -*-
"""Karaoke y letras a pantalla completa (donadores): letra grande que se llena fila por fila, fondo con los
colores de la carátula y la mascota «cantando». Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

CAPTURAS = os.environ.get("CAUDAL_CAPTURAS", "")
LRC = [(0, ""), (12000, "Cuando la noche cae sobre la ciudad entera"), (16000, "y las luces se encienden"),
       (20500, "te busco entre la gente"), (24000, ""), (40000, "baila conmigo")]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _R(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = {"clave": "k1", "titulo": "Medianoche en Lima", "artista": "Las Estrellas", "miniatura": "u1"}
        self.estado = "sonando"
        self.velocidad = 1.0
        self._posicion = 17.0
        self.saltos = []

    def anterior(self):
        pass

    def siguiente(self):
        pass

    def alternar(self):
        pass

    def buscar(self, s):
        self.saltos.append(s)

    def fijar(self, estado):
        self.estado = estado
        self.estado_cambio.emit(estado)

    def mover(self, seg):
        self._posicion = seg
        self.posicion_cambio.emit(seg)


class _Aj(dict):
    def guardar(self):
        pass


class _Prem(QObject):
    cambiado = Signal()

    def __init__(self):
        super().__init__()
        self.premium = True


class _Gamer:
    ahorrando = False


class _Mascota:
    def __init__(self, datos):
        self._d = datos

    def datos(self):
        return self._d


class _Ctx(QObject):
    def __init__(self):
        super().__init__()
        from descargador import mascotas
        self.reproductor = _R()
        self.ajustes = _Aj(traducir_letra=False, colores_caratula=True)
        self.premium = _Prem()
        self.gamer = _Gamer()
        self.mascota = _Mascota(mascotas.por_clave("capibara") or mascotas.catalogo()[0])
        self.ventana = None
        self.avisos = []

    def avisar(self, texto, deshacer=None):
        self.avisos.append(texto)


def caratula():
    img = QImage(200, 200, QImage.Format_RGB32)
    p = QPainter(img)
    p.fillRect(0, 0, 100, 200, QColor("#0EA5E9"))
    p.fillRect(100, 0, 100, 200, QColor("#14B8A6"))
    p.end()
    return img


def bombear(app, seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture
def pagina(app, monkeypatch):
    from descargador import catalogo, paleta_caratula
    from descargador.ui import imagenes, karaoke as K, letra_viva as L
    paleta_caratula.CACHE.clear()
    L.CACHE_LETRAS.clear()
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": LRC, "texto": "",
                                                       "fuente": "LRCLIB"})
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(caratula()))
    monkeypatch.setattr(imagenes, "pedir", lambda *a, **k: None)
    ctx = _Ctx()
    w = K.PaginaKaraoke(ctx)
    w.resize(1280, 720)
    w.ctx_falso = ctx
    yield w
    w.hide()
    w.deleteLater()


def abrir(app, w, pos=17.0):
    w.r.mover(pos)
    w.show()
    bombear(app, 0.6)


def test_la_letra_es_mas_grande_que_en_la_pagina_de_letra(app, pagina):
    from descargador.ui.letra_viva import LienzoLetra
    w = pagina
    ctx = w.ctx_falso
    normal = LienzoLetra(ctx, compacto=False)
    normal.resize(1280, 720)
    w.show()
    app.processEvents()
    assert w.lienzo.width() == 1280
    assert w.lienzo._tam() > normal._tam() * 1.5
    assert 40 <= w.lienzo._tam() <= 88
    w.resize(500, 400)
    assert w.lienzo._tam() >= 40                              # nunca ilegible
    normal.deleteLater()


def test_va_con_la_musica_y_se_llena_fila_por_fila(app, pagina):
    w = pagina
    abrir(app, w, 12.2)
    lc = w.lienzo
    assert lc.sincronizada and len(lc.lineas) == len(LRC)
    assert lc._actual == 1
    lc._repartir()
    it = lc._items[1]
    assert len(it["filas"]) >= 2, "la línea larga debe partirse en varias filas a este tamaño"
    # al avanzar la voz la línea se va llenando de 0 a 1…
    vistos = []
    for seg in (12.4, 13.2, 14.2, 15.2, 15.9):
        w.r.mover(seg)
        vistos.append(lc._progreso(1, lc.ahora_ms()))
    assert vistos == sorted(vistos) and 0 <= vistos[0] < 0.5 and vistos[-1] > 0.8
    # …y la pluma pinta las filas en orden: una fila completa antes de empezar la siguiente
    w.r.mover(13.9)
    prog = lc._progreso(1, lc.ahora_ms())
    total = sum(len(f) for f in it["filas"])
    hecho = prog * total
    llenas = [min(1.0, max(0.0, (hecho - sum(len(f) for f in it["filas"][:n])) / len(it["filas"][n])))
              for n in range(len(it["filas"]))]
    assert llenas == sorted(llenas, reverse=True)             # primero llenas, luego a medias, luego vacías
    assert llenas[0] > 0 and llenas[-1] < 1
    # lo ya cantado queda lleno y lo que viene, vacío
    assert lc._progreso(0, lc.ahora_ms()) == 1.0 and lc._progreso(3, lc.ahora_ms()) == 0.0


def test_un_clic_en_una_linea_salta_a_ese_momento(app, pagina):
    w = pagina
    abrir(app, w, 17.0)
    lc = w.lienzo
    k = 3
    it = lc._items[k]
    y = int(it["yv"] + 10)
    QTest.mouseClick(lc, Qt.LeftButton, Qt.NoModifier, QPointF_(lc._margen_x() + 20, y))
    assert w.r.saltos and abs(w.r.saltos[-1] - 20.5) < 0.6


def QPointF_(x, y):
    from PySide6.QtCore import QPoint
    return QPoint(int(x), int(y))


def test_el_fondo_toma_los_colores_de_la_caratula_con_transicion(app, pagina):
    w = pagina
    abrir(app, w)
    bombear(app, 1.2)
    assert w.colores.fuerza > 0.9
    esperados = w.colores.hex_actuales()
    assert [c.name() for c in w.lienzo.paleta] == esperados      # el lienzo pinta con la paleta de la carátula
    w.ctx_falso.ajustes["colores_caratula"] = False
    w.colores.refrescar()
    bombear(app, 1.2)
    assert w.colores.fuerza == 0
    assert [c.name() for c in w.lienzo.paleta] != esperados       # apagado: vuelven los colores de siempre


def test_la_mascota_canta_con_voz_tararea_sin_ella_y_descansa_en_pausa(app, pagina):
    w = pagina
    abrir(app, w, 13.0)                                           # hay voz (línea 1)
    m = w.mascota
    assert m.calcular_estado() == "canta" and m.estado == "canta" and m.reloj.isActive()
    c0 = m.cuadro
    bombear(app, 0.6)
    assert m.cuadro > c0 + 2                                      # abre y cierra la boca: cambia de cuadro
    w.r.mover(30.0)                                               # tramo instrumental
    bombear(app, 0.4)
    assert m.calcular_estado() == "tararea"
    c1 = m.cuadro
    bombear(app, 0.5)
    assert m.cuadro == c1                                         # tararea: se mece pero no abre la boca
    w.r.fijar("pausa")
    assert m.estado == "descansa" and not m.reloj.isActive() and m.cuadro == 0
    w.r.fijar("sonando")
    assert m.reloj.isActive()


def test_la_mascota_se_ve_en_la_pantalla(app, pagina):
    w = pagina
    abrir(app, w, 13.0)
    assert w.mascota.isVisible() and w.mascota.datos
    img = w.mascota.grab().toImage()
    pintados = sum(1 for x in range(0, img.width(), 6) for y in range(0, img.height(), 6)
                   if img.pixelColor(x, y).alpha() > 0)
    assert pintados > 40, "la mascota no se dibujó"
    if CAPTURAS:
        os.makedirs(CAPTURAS, exist_ok=True)
        w.grab().save(os.path.join(CAPTURAS, "karaoke.png"))


def test_sin_mascota_elegida_canta_una_por_defecto(app):
    from descargador.ui import karaoke as K
    ctx = _Ctx()
    ctx.mascota = _Mascota(None)
    d = K.mascota_para(ctx)
    assert d and d.get("clave")
    ctx.mascota = None
    assert K.mascota_para(ctx)["clave"] == d["clave"]


def test_con_el_ahorro_del_modo_gamer_nada_se_anima(app, pagina):
    w = pagina
    abrir(app, w, 13.0)
    w.ctx_falso.gamer.ahorrando = True
    # lo que el modo gamer hace: parar los relojes rápidos de la vista
    paradas = [t for t in w.findChildren(QTimer) if t.isActive() and not t.isSingleShot() and t.interval() <= 250]
    assert w.mascota.reloj in paradas and w.lienzo.reloj in paradas
    for t in paradas:
        t.stop()
    w.mascota.reloj.start(140)
    c = w.mascota.cuadro
    w.lienzo.reloj.start(16)
    bombear(app, 0.4)
    assert w.mascota.cuadro == c                                  # aunque algo los despierte, no se mueven
    assert w.lienzo.reloj.interval() == 300                       # y el lienzo se queda en vigilia


def test_traducir_se_recuerda(app, pagina):
    w = pagina
    w.show()
    w.bt_traducir.setChecked(True)
    assert w.ctx_falso.ajustes["traducir_letra"] is True


def test_esc_y_cerrar_y_pantalla_completa(app, pagina):
    w = pagina
    cerrado, completa = [], []
    w.volver.connect(lambda: cerrado.append(1))

    class _V:
        def alternar_completa(self):
            completa.append(1)
    w.ctx_falso.ventana = _V()
    w.show()
    QTest.keyClick(w, Qt.Key_Escape)
    w.bt_cerrar.click()
    w.bt_completa.click()
    assert cerrado == [1, 1] and completa == [1]


def test_pierde_el_donador_y_se_cierra(app, pagina):
    w = pagina
    cerrado = []
    w.volver.connect(lambda: cerrado.append(1))
    w.show()
    w.ctx_falso.premium.premium = False
    w.ctx_falso.premium.cambiado.emit()
    assert cerrado == [1]


def test_al_ocultar_se_detiene_todo(app, pagina):
    w = pagina
    abrir(app, w, 13.0)
    w.hide()
    assert not w.mascota.reloj.isActive() and not w.lienzo.reloj.isActive()


@pytest.mark.parametrize("ancho,alto", [(1280, 720), (900, 600), (1920, 1080)])
def test_la_letra_nunca_pisa_la_franja_de_controles(app, pagina, ancho, alto):
    w = pagina
    w.resize(ancho, alto)
    abrir(app, w, 21.0)                                           # varias filas visibles
    bombear(app, 0.8)
    img = w.lienzo.grab().toImage()
    # sin controles encima: en los últimos 112 px (donde van el título y los botones) no hay letra blanca
    for y in range(alto - 112, alto - 24):
        for x in range(0, ancho, 3):
            c = img.pixelColor(x, y)
            assert min(c.red(), c.green(), c.blue()) < 200, f"letra en la franja de controles ({x},{y}) a {ancho}x{alto}"
    if CAPTURAS:
        os.makedirs(CAPTURAS, exist_ok=True)
        w.grab().save(os.path.join(CAPTURAS, f"karaoke_{ancho}x{alto}.png"))


def test_la_mascota_no_arrastra_estela(app, pagina):
    w = pagina
    abrir(app, w, 13.0)
    assert not w.mascota.datos.get("estela") and not w.mascota.datos.get("arcoiris")


def test_senales_tras_destruir_la_pagina_no_fallan(app, monkeypatch):
    """Informe real: una señal del reproductor llegaba a la PaginaKaraoke ya destruida
    («Internal C++ object (PaginaKaraoke) already deleted»)."""
    import shiboken6
    from descargador.ui import karaoke as K
    errores = []
    monkeypatch.setattr(sys, "excepthook", lambda *a: errores.append(a))
    ctx = _Ctx()
    w = K.PaginaKaraoke(ctx)
    w.resize(800, 500)
    shiboken6.delete(w)
    ctx.reproductor.mover(18.0)
    ctx.reproductor.fijar("pausado")
    app.processEvents()
    assert errores == []
