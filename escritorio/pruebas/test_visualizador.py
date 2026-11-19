# -*- coding: utf-8 -*-
"""El visualizador a pantalla completa (donadores): la energía sale del nivel medido o del ritmo, los tres estilos
se pintan, gasta poco (reloj que descansa, se detiene con el ahorro del modo gamer) y se cierra con Esc.
Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, QPoint, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import espectro as E  # noqa: E402

CAPTURAS = os.environ.get("CAUDAL_CAPTURAS", "")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ el modelo (sin Qt)

def correr(modelo, seg, nivel=None, sonando=True, **k):
    for i in range(int(seg * 30)):
        modelo.avanzar(1 / 30, nivel, sonando, pos=i / 30, **k)
    return modelo


def test_db_a_unidad_esta_acotado_y_crece():
    assert E.db_a_unidad(-90) == 0 and E.db_a_unidad(0) == 1 and E.db_a_unidad(float("nan")) == 0
    assert E.db_a_unidad("x") == 0
    xs = [E.db_a_unidad(d) for d in range(-60, 0, 4)]
    assert xs == sorted(xs)


def test_silencio_no_mueve_nada():
    m = correr(E.ModeloAudio(), 1.0, nivel=(-80.0, -70.0))
    assert m.energia < 0.01 and max(m.bandas) < 0.01 and m.quieto()


def test_mas_volumen_mas_energia_y_mas_barras():
    suave = correr(E.ModeloAudio(), 1.5, nivel=(-38.0, -30.0))
    fuerte = correr(E.ModeloAudio(), 1.5, nivel=(-14.0, -6.0))
    assert fuerte.energia > suave.energia + 0.2
    assert max(fuerte.bandas) > max(suave.bandas)
    assert all(0.0 <= b <= 1.0 for b in fuerte.bandas) and fuerte.fuente == "medida"


def test_un_pico_sobre_el_nivel_medio_da_golpe():
    m = correr(E.ModeloAudio(), 2.0, nivel=(-30.0, -24.0))            # nivel estable: sin golpe
    base = m.golpe
    for _ in range(3):
        m.avanzar(1 / 30, (-18.0, -4.0), True)                      # entra el bombo
    assert m.golpe > base + 0.25


def test_los_graves_se_llevan_mas_que_los_agudos():
    m = correr(E.ModeloAudio(), 3.0, nivel=(-20.0, -10.0))
    n = m.n
    assert sum(m.bandas[: n // 3]) > sum(m.bandas[-n // 3:])


def test_al_pausar_todo_baja_y_el_modelo_descansa():
    m = correr(E.ModeloAudio(), 1.5, nivel=(-14.0, -6.0))
    assert not m.quieto()
    correr(m, 5.0, nivel=None, sonando=False)
    assert m.quieto()


def test_sin_medidor_sigue_el_ritmo_conocido():
    m = E.ModeloAudio()
    for pos in (0.0, 0.3, 0.6):                                      # 100 bpm: un pulso cada 0.6 s
        m.avanzar(0.0, None, True, pos=pos, bpm=100.0, fase=0.0)
    assert m.fuente == "ritmo"
    assert E.pulso_de_ritmo(0.0, 100.0) == 1.0                       # justo en el pulso: a tope
    assert E.pulso_de_ritmo(0.3, 100.0) < 0.2                        # a media espera: casi nada
    assert E.pulso_de_ritmo(0.6, 100.0) == pytest.approx(1.0, abs=1e-6)
    assert E.pulso_de_ritmo(0.0, 120.0, fase=0.25) < 1.0             # la fase mueve el primer pulso
    assert E.pulso_de_ritmo(0.1, 0) == E.pulso_de_ritmo(0.1, E.BPM_POR_DEFECTO)   # sin tempo: el de siempre


def test_el_ritmo_late_la_energia_sube_y_baja():
    m = E.ModeloAudio()
    valores = []
    for i in range(90):
        m.avanzar(1 / 30, None, True, pos=i / 30, bpm=120.0)
        valores.append(m.energia)
    assert max(valores[30:]) - min(valores[30:]) > 0.1               # late: no es una cifra fija
    assert max(valores) < 1.0


# ------------------------------------------------------------------ la página

class _R(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = {"clave": "a", "titulo": "Medianoche en Lima", "artista": "Las Estrellas",
                       "miniatura": "u1"}
        self.estado = "sonando"
        self.velocidad = 1.0
        self._posicion = 10.0
        self.nivel = (-18.0, -8.0)
        self.espectro = []
        self.llamadas = []

    def anterior(self):
        self.llamadas.append("anterior")

    def siguiente(self):
        self.llamadas.append("siguiente")

    def alternar(self):
        self.llamadas.append("alternar")

    def activar_espectro(self, si):
        self.espectro.append(bool(si))

    def nivel_audio(self):
        return self.nivel if self.estado == "sonando" else None

    def _analisis_de(self, pista):
        return {"bpm": 110.0, "fase": 0.2}

    def fijar(self, estado):
        self.estado = estado
        self.estado_cambio.emit(estado)


class _Aj(dict):
    guardados = 0

    def guardar(self):
        self.guardados += 1


class _Prem(QObject):
    cambiado = Signal()

    def __init__(self):
        super().__init__()
        self.premium = True


class _Gamer:
    ahorrando = False


class _Ctx(QObject):
    def __init__(self):
        super().__init__()
        self.reproductor = _R()
        self.ajustes = _Aj(visualizador_estilo="ondas", colores_caratula=True, traducir_letra=False)
        self.premium = _Prem()
        self.gamer = _Gamer()
        self.ventana = None


def caratula():
    img = QImage(200, 200, QImage.Format_RGB32)
    p = QPainter(img)
    p.fillRect(0, 0, 100, 200, QColor("#E8590C"))
    p.fillRect(100, 0, 100, 200, QColor("#7A1BFF"))
    p.end()
    return img


@pytest.fixture
def pagina(app, monkeypatch):
    from descargador import paleta_caratula
    from descargador.ui import imagenes, visualizador as V
    paleta_caratula.CACHE.clear()
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(caratula()))
    ctx = _Ctx()
    w = V.PaginaVisualizador(ctx)
    w.resize(1280, 720)
    w.ctx_falso = ctx
    yield w
    w.hide()
    w.deleteLater()


def bombear(app, seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


def imagen_de(w):
    return w.grab().toImage()


def variedad(img):
    """Cuántos colores distintos hay en una rejilla de puntos (una pantalla lisa da 1)."""
    return len({img.pixel(x, y) for x in range(0, img.width(), 40) for y in range(0, img.height(), 30)})


def test_se_abre_y_se_cierra_con_el_medidor_solo_mientras_se_ve(pagina):
    w = pagina
    assert w.r.espectro == []                                  # cerrada: el motor no mide nada
    w.show()
    assert w.r.espectro == [True] and w.reloj.isActive()
    w.hide()
    assert w.r.espectro == [True, False] and not w.reloj.isActive()


@pytest.mark.parametrize("estilo", ["ondas", "particulas", "barras"])
def test_los_tres_estilos_se_pintan_y_se_mueven(app, pagina, estilo):
    w = pagina
    w.elegir_estilo(estilo)
    w.show()
    bombear(app, 0.7)
    a = imagen_de(w)
    assert variedad(a) > 12, "la pantalla salió casi lisa"
    cuadros = w.cuadros
    bombear(app, 0.5)
    assert w.cuadros > cuadros + 5                             # se anima (~30 cuadros por segundo)
    b = imagen_de(w)
    assert a != b                                              # y de un cuadro a otro cambia
    if CAPTURAS:
        os.makedirs(CAPTURAS, exist_ok=True)
        b.save(os.path.join(CAPTURAS, f"visualizador_{estilo}.png"))


def test_cada_estilo_se_ve_distinto(app, pagina):
    w = pagina
    w.show()
    imgs = {}
    for estilo in ("ondas", "particulas", "barras"):
        w.elegir_estilo(estilo)
        bombear(app, 0.3)
        imgs[estilo] = imagen_de(w)
    assert imgs["ondas"] != imgs["barras"] != imgs["particulas"]


def test_elegir_estilo_se_recuerda_y_uno_raro_cae_en_ondas(pagina):
    w = pagina
    w.elegir_estilo("barras")
    assert w.ctx_falso.ajustes["visualizador_estilo"] == "barras" and w.ctx_falso.ajustes.guardados >= 1
    assert w.botones_estilo["barras"].isChecked() and not w.botones_estilo["ondas"].isChecked()
    w.elegir_estilo("disco")
    assert w.estilo == "ondas"


def test_con_el_nivel_del_motor_las_barras_se_mueven_con_el_volumen(app, pagina):
    w = pagina
    w.elegir_estilo("barras")
    w.show()
    w.r.nivel = (-40.0, -30.0)
    bombear(app, 0.8)
    bajo = w.modelo.energia
    w.r.nivel = (-12.0, -4.0)
    bombear(app, 0.8)
    assert w.modelo.fuente == "medida" and w.modelo.energia > bajo + 0.2


def test_si_el_motor_no_mide_sigue_el_ritmo(app, pagina):
    w = pagina
    w.r.nivel_audio = lambda: None
    w.show()
    bombear(app, 0.6)
    assert w.modelo.fuente == "ritmo" and w._bpm == 110.0 and w.modelo.energia > 0.1


def test_gasta_poco_sonando_a_30_cuadros_y_en_pausa_se_duerme(app, pagina):
    w = pagina
    w.show()
    assert w.reloj.interval() == 33
    w.r.fijar("pausa")
    bombear(app, 0.2)
    assert w.reloj.interval() >= 200                           # en pausa baja a ~4 por segundo
    bombear(app, 4.0)                                          # las barras terminan de bajar…
    assert not w.reloj.isActive()                              # …y el reloj se apaga solo
    cuadros = w.cuadros
    bombear(app, 0.5)
    assert w.cuadros == cuadros                                # sin trabajo mientras nada se mueve
    w.r.fijar("sonando")                                       # y al dar play despierta
    assert w.reloj.isActive() and w.reloj.interval() == 33


def test_con_el_ahorro_del_modo_gamer_no_anima_nada(app, pagina):
    w = pagina
    w.ctx_falso.gamer.ahorrando = True
    w.show()
    assert not w.reloj.isActive()                              # ni arranca
    bombear(app, 0.1)                                          # (al mostrarse se pinta una vez)
    cuadros = w.cuadros
    bombear(app, 0.3)
    assert w.cuadros == cuadros
    w.reloj.start(33)                                          # si algo lo despierta, el cuadro se salta
    bombear(app, 0.2)
    assert w.modelo.energia == 0 and w.cuadros == cuadros
    w.reloj.stop()
    w.ctx_falso.gamer.ahorrando = False
    w.r.fijar("sonando")                                       # al salir del ahorro, el siguiente cambio lo reanima
    assert w.reloj.isActive()


def test_el_modo_gamer_puede_parar_y_reanudar_sus_relojes(app, pagina):
    """El modo gamer detiene los QTimer hijos que van a ≤ 250 ms: el reloj de la vista lo es."""
    from PySide6.QtCore import QTimer
    w = pagina
    w.show()
    hijos = [t for t in w.findChildren(QTimer) if t.isActive() and not t.isSingleShot() and t.interval() <= 250]
    assert w.reloj in hijos


def test_cada_cuadro_cuesta_poco(app, pagina):
    w = pagina
    w.resize(1920, 1080)
    w.show()
    app.processEvents()
    for estilo in ("ondas", "particulas", "barras"):
        w.elegir_estilo(estilo)
        for _ in range(3):
            w.grab()
        t = time.perf_counter()
        for _ in range(10):
            w.grab()
        ms = (time.perf_counter() - t) * 100
        assert ms < 60, f"{estilo}: {ms:.1f} ms por cuadro a 1920×1080 (sin GPU)"


def test_esc_cierra_y_f_pide_pantalla_completa(app, pagina):
    w = pagina
    cerrado, completa = [], []
    w.volver.connect(lambda: cerrado.append(1))

    class _V:
        def alternar_completa(self):
            completa.append(1)
    w.ctx_falso.ventana = _V()
    w.show()
    QTest.keyClick(w, Qt.Key_Escape)
    assert cerrado == [1]
    QTest.keyClick(w, Qt.Key_F)
    assert completa == [1]
    w.bt_completa.click()
    assert len(completa) == 2


def test_los_controles_se_esconden_solos_y_vuelven_con_el_raton(app, pagina):
    w = pagina
    w.show()
    assert w.cabecera.isVisible() and w.pie.isVisible()
    w._esconder()
    assert not w.cabecera.isVisible() and not w.pie.isVisible()
    assert w.cursor().shape() == Qt.BlankCursor
    QTest.mouseMove(w, QPoint(300, 300))
    w.mostrar_controles()
    assert w.cabecera.isVisible() and w.pie.isVisible() and w.cursor().shape() != Qt.BlankCursor


def test_los_botones_del_pie_mandan_al_reproductor(app, pagina):
    w = pagina
    w.show()
    w.bt_anterior.click()
    w.bt_play.click()
    w.bt_siguiente.click()
    assert w.r.llamadas == ["anterior", "alternar", "siguiente"]
    assert w.et_titulo.text().startswith("Medianoche") and w.et_artista.text() == "Las Estrellas"


def test_si_la_cuenta_deja_de_ser_donadora_se_cierra_sola(app, pagina):
    w = pagina
    cerrado = []
    w.volver.connect(lambda: cerrado.append(1))
    w.show()
    w.ctx_falso.premium.premium = False
    w.ctx_falso.premium.cambiado.emit()
    assert cerrado == [1]


def test_los_colores_de_la_caratula_tiñen_el_fondo(app, pagina):
    w = pagina
    w.show()
    bombear(app, 1.2)
    assert w.colores.fuerza > 0.9
    con = imagen_de(w)
    w.ctx_falso.ajustes["colores_caratula"] = False
    w.colores.refrescar()
    bombear(app, 1.2)
    sin = imagen_de(w)
    assert w.colores.fuerza == 0 and con != sin
