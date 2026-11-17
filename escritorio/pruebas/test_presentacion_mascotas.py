# -*- coding: utf-8 -*-
"""Presentación de la 2.4.2 («Mascotitas y fondos con personaje»): cuándo sale, que no se encima
con la de la edición grande, que se recorre entera y que no enseña mascotas exclusivas. Sin
ventanas a la vista (Qt offscreen) y sin red."""

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def padre(app):
    from descargador.config import Ajustes
    w = QWidget()
    w.resize(1360, 760)
    w.ajustes = Ajustes()
    w.destinos = []
    w.navegar = w.destinos.append
    w.show()
    app.processEvents()
    yield w
    w.close()


def _nueva(padre, app):
    from descargador.ui.presentacion_mascotas import PresentacionMascotas
    d = PresentacionMascotas(padre)
    d.show()
    app.processEvents()
    d.avanzar(1)
    return d


# ================================================================ cuándo sale

def test_clave_de_ajustes_y_version():
    from descargador.config import DEFECTOS
    from descargador.ui import presentacion_mascotas as pm
    assert pm.VERSION_PRESENTACION == "2.4.2"
    assert DEFECTOS[pm.CLAVE_AJUSTE] == ""


def test_sale_una_sola_vez_desde_la_242(datos_aislados):
    from descargador.config import Ajustes
    from descargador.ui import presentacion_mascotas as pm
    a = Ajustes()
    assert not pm.debe_mostrarse(a, "2.4.1")                # versión menor: no sale
    assert not pm.debe_mostrarse(a, "2.3.9")
    assert pm.debe_mostrarse(a, "2.4.2")
    assert pm.debe_mostrarse(a, "2.4.5") and pm.debe_mostrarse(a, "3.0.0")   # quien salta de versión también
    pm.marcar_vista(a)
    assert Ajustes()[pm.CLAVE_AJUSTE] == "2.4.2"               # queda guardado en disco
    assert not pm.debe_mostrarse(a, "2.4.2")
    assert not pm.debe_mostrarse(Ajustes(), "2.4.3")           # ni con los parches siguientes


def test_mostrar_si_toca_abre_anota_y_no_repite(app, monkeypatch, padre):
    from descargador import version
    from descargador.config import Ajustes
    from descargador.ui import presentacion_mascotas as pm
    monkeypatch.setattr(version, "VERSION", "2.4.2")
    d = pm.mostrar_si_toca(padre)
    assert isinstance(d, pm.PresentacionMascotas) and d.isVisible()
    assert Ajustes()[pm.CLAVE_AJUSTE] == "2.4.2"               # anotada al abrirse, no al cerrarse
    d.reject()
    app.processEvents()
    assert pm.mostrar_si_toca(padre) is None


def test_no_sale_con_version_anterior(app, monkeypatch, padre):
    from descargador import version
    from descargador.ui import presentacion_mascotas as pm
    monkeypatch.setattr(version, "VERSION", "2.4.1")
    assert pm.mostrar_si_toca(padre) is None
    assert padre.ajustes[pm.CLAVE_AJUSTE] == ""


def test_si_ya_sale_la_grande_espera_al_siguiente_arranque(app, monkeypatch, padre):
    from descargador import version
    from descargador.ui import presentacion_mascotas as pm
    monkeypatch.setattr(version, "VERSION", "2.4.2")
    otra = QWidget()
    assert pm.mostrar_si_toca(padre, otra) is None
    assert padre.ajustes[pm.CLAVE_AJUSTE] == ""                # no se gastó: sale la próxima vez
    d = pm.mostrar_si_toca(padre)
    assert d is not None
    d.reject()


def test_ventana_no_encima_las_dos_presentaciones(app, monkeypatch, padre):
    """La ventana real: con la grande pendiente sale solo la grande; en el arranque siguiente, la nuestra."""
    from descargador import version
    from descargador.ui import novedades_grandes as ng
    from descargador.ui import presentacion_mascotas as pm
    from descargador.ui.presentacion_grande import PresentacionGrande
    from descargador.ui.ventana import Ventana
    monkeypatch.setattr(version, "VERSION", "2.4.2")

    class Falsa(QWidget):                                  # lo mínimo de Ventana que usa _avisar_novedades
        def __init__(self, w):
            super().__init__()
            self.resize(1360, 760)
            self.en_completa = False
            self._saliendo = False
            self._aviso_grande = None
            self._aviso_mascotas = None
            self._grande_en_sesion = False
            self._novedad_pendiente = None
            self.ajustes = w.ajustes
            self.navegar = w.navegar

    for nombre in ("_avisar_novedades", "_tras_novedades"):
        setattr(Falsa, nombre, getattr(Ventana, nombre))
    monkeypatch.setattr(ng, "crear_aviso", lambda v, novedad=None: PresentacionGrande(v))
    # primer arranque: la grande pendiente (nunca vista)
    v = Falsa(padre)
    v._avisar_novedades()
    assert isinstance(v._aviso_grande, PresentacionGrande) and v._aviso_mascotas is None
    v._aviso_grande.reject()
    app.processEvents()
    v._avisar_novedades()                                  # en la misma sesión tampoco se encima
    assert v._aviso_mascotas is None and v._aviso_grande is None
    # siguiente arranque: ahora sí sale la nuestra
    v2 = Falsa(padre)
    v2._avisar_novedades()
    assert v2._aviso_grande is None and isinstance(v2._aviso_mascotas, pm.PresentacionMascotas)
    v2._aviso_mascotas.reject()
    app.processEvents()
    assert v2._aviso_mascotas is None
    # y ya no vuelve
    v3 = Falsa(padre)
    v3._avisar_novedades()
    assert v3._aviso_grande is None and v3._aviso_mascotas is None


# ================================================================ qué enseña

def test_nunca_muestra_mascotas_exclusivas():
    from descargador import mascotas as M
    from descargador.ui import presentacion_mascotas as pm
    exclusivas = {m["clave"] for m in M.catalogo() if M.es_exclusiva(m)}
    assert exclusivas, "el catálogo debería tener al menos una exclusiva para que la prueba sirva"
    todas = pm.orden_rejilla() + pm.disponibles(pm.DESFILE) + pm.disponibles(pm.DESFILE_FINAL)
    assert todas and not exclusivas & {m["clave"] for m in todas}
    # aunque alguien la pida a mano
    assert pm.disponibles(sorted(exclusivas)) == []
    # la rejilla las recorre todas (menos las exclusivas), sin repetir
    claves = [m["clave"] for m in pm.orden_rejilla()]
    assert len(claves) == len(set(claves))
    assert set(claves) == {m["clave"] for m in M.catalogo() if not M.es_exclusiva(m)}


def test_los_fondos_con_personaje_tienen_dibujo_y_mascota():
    from descargador.ui import presentacion_mascotas as pm
    from descargador.ui.estilos import TEMAS
    temas = pm.temas_en_orden()
    assert sorted(temas) == sorted(TEMAS) and len(temas) == len(TEMAS) >= 18
    for k in temas:
        assert pm._pixmap_personaje(k) is not None, k
        assert pm.disponibles([k]), k


def test_capa_de_mascotas_nitida_y_sin_suavizado(app):
    """La mascota se pinta píxel a píxel: con densidad 2, un píxel de la hoja es un píxel de la capa."""
    from descargador import mascotas as M
    from descargador.ui import presentacion_mascotas as pm
    m = M.por_clave("pikachu")
    img = pm.capa_mascotas(120, m["alto"] + 4, [(m, 60, m["alto"] + 3, 0.0, 0.0)], holgura=0)
    assert img.width() == 240
    hoja = M.cuadros("pikachu")[0].toImage()
    assert hoja.width() == m["ancho"] * M.densidad(m)
    izq, arriba = (60 - m["ancho"] // 2) * 2, (m["alto"] + 3 - m["alto"] + 1) * 2
    iguales = sum(1 for y in range(0, hoja.height(), 3) for x in range(0, hoja.width(), 3)
                  if hoja.pixelColor(x, y).alpha() == 255
                  and img.pixelColor(izq + x, arriba + y).rgb() == hoja.pixelColor(x, y).rgb())
    opacos = sum(1 for y in range(0, hoja.height(), 3) for x in range(0, hoja.width(), 3)
                 if hoja.pixelColor(x, y).alpha() == 255)
    assert opacos and iguales / opacos > 0.97


# ================================================================ el diálogo

def test_se_construye_y_recorre_todas(app, padre):
    from descargador.ui import presentacion_mascotas as pm
    d = _nueva(padre, app)
    assert d.n == len(pm.DIAPOSITIVAS) == 5
    assert d.geometry().size() == padre.window().size()
    assert d.bt_saltar.isVisible() and not d.bt_ant.isVisible() and not d.bt_aspecto.isVisible()
    for i in range(d.n):
        assert d.indice == i
        d.avanzar(2.5)
        img = d.grab().toImage()
        assert not img.isNull() and img.width() == d.width()
        assert d.bt_saltar.isVisible()
        # a media transición también se pinta sin errores
        if i < d.n - 1:
            d.siguiente()
            d._p_trans = 0.5
            d.grab()
            d.avanzar(0.01)
    assert d.indice == d.n - 1
    assert d.bt_sig.text() == "Empezar" and d.bt_aspecto.isVisible()
    d.siguiente()                                          # no pasa de la última
    assert d.indice == d.n - 1
    d.reject()


def test_teclado_rueda_clic_y_puntos(app, padre):
    d = _nueva(padre, app)
    QTest.keyClick(d, Qt.Key_Right)
    d.avanzar(1)
    assert d.indice == 1
    QTest.keyClick(d, Qt.Key_Return)
    d.avanzar(1)
    assert d.indice == 2
    QTest.keyClick(d, Qt.Key_Left)
    d.avanzar(1)
    assert d.indice == 1
    QTest.keyClick(d, Qt.Key_End)
    d.avanzar(1)
    assert d.indice == d.n - 1
    QTest.keyClick(d, Qt.Key_Home)
    d.avanzar(1)
    assert d.indice == 0
    # un giro fuerte de la rueda hacia abajo pasa a la siguiente (uno suave y seguido se ignora)
    rueda = QWheelEvent(QPointF(200, 200), QPointF(200, 200), QPoint(0, 0), QPoint(0, -480),
                        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(d, rueda)
    d.avanzar(1)
    assert d.indice == 1
    d.ir_a(0, animar=False)
    d.avanzar(1)
    QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, QPoint(300, 300))
    d.avanzar(1)
    assert d.indice == 1
    d.grab()                                               # para que existan los puntos
    punto = d._puntos[3].center().toPoint()
    QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, punto)
    d.avanzar(1)
    assert d.indice == 3
    d.reject()


def test_saltar_cierra_y_escape_tambien(app, padre):
    d = _nueva(padre, app)
    d.siguiente()
    d.avanzar(1)
    d.bt_saltar.click()
    app.processEvents()
    assert not d.isVisible() and d.result() == 0
    d2 = _nueva(padre, app)
    QTest.keyClick(d2, Qt.Key_Escape)
    app.processEvents()
    assert not d2.isVisible()


def test_empezar_y_elegir_mi_fondo(app, padre):
    from descargador.ui import presentacion_mascotas as pm
    d = _nueva(padre, app)
    d.ir_a(d.n - 1, animar=False)
    d.avanzar(1)
    d.bt_sig.click()
    app.processEvents()
    assert not d.isVisible() and d.result() == 1 and d.destino == ""
    # «Elegir mi fondo» lleva a Ajustes (Aspecto es lo primero)
    d2 = pm.abrir(padre)
    d2.ir_a(d2.n - 1, animar=False)
    d2.avanzar(1)
    d2.bt_aspecto.click()
    for _ in range(5):
        app.processEvents()
    assert padre.destinos == [{"pagina": "ajustes"}]


def test_no_toca_la_musica(app, padre, monkeypatch):
    """La presentación no llama al reproductor para nada (no lo conoce)."""
    from descargador.ui import presentacion_mascotas as pm
    import inspect
    fuente = inspect.getsource(pm)
    for llamada in (".reproductor", "pausar(", "detener(", "volumen"):
        assert llamada not in fuente, llamada


def test_se_ve_bien_a_varios_tamanos(app, padre):
    """Se pinta a 900x600, 1360x760 y 1920x1080 sin errores y los botones caben en pantalla."""
    for w, h in ((900, 600), (1360, 760), (1920, 1080)):
        padre.resize(w, h)
        app.processEvents()
        d = _nueva(padre, app)
        d.resize(w, h)
        for i in range(d.n):
            d.ir_a(i, animar=False)
            d.avanzar(3)
            d.grab()
            for b in (d.bt_saltar, d.bt_sig) + ((d.bt_aspecto, d.bt_ant) if i == d.n - 1 else ()):
                g = b.geometry()
                assert g.left() >= 0 and g.top() >= 0 and g.right() <= d.width() and g.bottom() <= d.height(), (w, h, i)
        # el texto no se sale del lado izquierdo ni invade la ilustración
        for i in (1, 2, 3):
            L = d._layout(i)
            assert L["x0"] + L["col"] <= L["ilus"].left() + 1
            assert L["y0"] >= 0 and L["y_fin"] <= d.height()
        d.reject()
