# -*- coding: utf-8 -*-
"""«Fondo de Caudal»: una imagen tenue detrás de toda la aplicación (solo Donador o Fundador).

Sin internet ni ventanas (Qt offscreen) y con los datos de la app en una carpeta temporal:
la sesión de la nube es un doble que contesta lo que contestaría la base de datos.
Genera capturas en <carpeta temporal>/caudal_fondo_capturas para mirarlas.
"""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QMimeData, QObject, QPointF, Qt, QUrl, Signal  # noqa: E402
from PySide6.QtGui import QColor, QDropEvent, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from descargador import fondo as F  # noqa: E402
from descargador import nube  # noqa: E402

EJEMPLO = r"C:\Users\USER\Downloads\opacity_quarter.png"
CAPTURAS = os.path.join(tempfile.gettempdir(), "caudal_fondo_capturas")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    monkeypatch.setattr(F, "_descargar", lambda url: (_ for _ in ()).throw(nube.SinConexion("sin red")))
    yield tmp_path


class SesionFalsa:
    user_id = "yo-id"
    access = "token"

    def __init__(self, datos=None, sin_red=False):
        self.datos = datos or {}
        self.sin_red = sin_red
        self.llamadas = []
        self.subidos = []
        self.borrados = []

    def _red(self):
        if self.sin_red:
            raise nube.SinConexion("sin red")

    def rpc(self, nombre, **p):
        self._red()
        self.llamadas.append((nombre, p))
        r = self.datos.get(nombre)
        return r(p) if callable(r) else r

    def pedir(self, metodo, ruta, **kw):
        self._red()
        if ruta.startswith("rpc/"):
            return self.rpc(ruta[4:], **(kw.get("json") or {}))
        self.llamadas.append((metodo, ruta, kw))
        clave = "GET perfiles" if metodo == "GET" else metodo
        r = self.datos.get(clave)
        return r(kw) if callable(r) else r

    def subir_archivo(self, bucket, ruta, datos, tipo, reemplazar=False, avance=None, tiempo=120):
        self._red()
        self.subidos.append((bucket, ruta, tipo, len(datos), reemplazar))

    def borrar_archivos(self, bucket, rutas):
        self._red()
        self.borrados.append((bucket, list(rutas)))


def _ctx(app, sesion, usuario="ana"):
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None          # nada de motores de audio reales en las pruebas
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import estilos
    from descargador.ui.contexto import Contexto
    ajustes = Ajustes()
    estilos.aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
    estilos.FONDO["activo"] = False
    ctx = Contexto(ajustes, Historial(), Coleccion(), Gestor(ajustes, Historial()),
                   Reproductor(ajustes, Coleccion()))
    ctx.cuenta = {"usuario": usuario, "nombre": "Ana", "sesion": sesion}
    return ctx


def esperar(app, cond, que, maximo=10):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


def pausa(app, s=0.4):
    fin = time.time() + s
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.01)


def imagen_de_prueba(ruta, ancho=800, alto=500, color="#FF9AC8", formato="PNG"):
    img = QImage(ancho, alto, QImage.Format_RGB32)
    img.fill(QColor(color))
    p = QPainter(img)
    p.fillRect(ancho // 2, 0, ancho // 2, alto, QColor("#1FC8FF"))
    p.end()
    assert img.save(str(ruta), formato)
    return str(ruta)


def luz(c):
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * canal(c.red()) + 0.7152 * canal(c.green()) + 0.0722 * canal(c.blue())


def contraste(a, b):
    la, lb = luz(QColor(a)), luz(QColor(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def luz_maxima(img, x0, y0, x1, y1):
    mejor = QColor(0, 0, 0)
    for y in range(y0, y1, 3):
        for x in range(x0, x1, 3):
            c = QColor(img.pixel(x, y))
            if luz(c) > luz(mejor):
                mejor = c
    return mejor


@pytest.fixture
def ventana_sin_ruido(monkeypatch):
    from descargador.ui.ventana import Ventana
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: 0)
    monkeypatch.setattr(Ventana, "buscar_version", lambda self, *a, **k: None)
    monkeypatch.setattr(Ventana, "_avisar_novedades", lambda self, *a, **k: None)
    monkeypatch.setattr(F.GestorFondo, "sincronizar", lambda self: None)
    return Ventana


def ventana_con_permiso(app, Ventana, puede=True, titulo=F.TITULO_FUNDADOR, sesion=None):
    sesion = sesion or SesionFalsa({"puede_poner_fondo": puede})
    ctx = _ctx(app, sesion)
    gestor = F.GestorFondo(ctx)
    gestor.puede, gestor.titulo = puede, titulo if puede else ""
    gestor._guardar_local()
    v = Ventana(ctx)
    v.resize(1280, 800)
    v.show()
    pausa(app, 0.3)
    return v, ctx, sesion


# ================================================================ límites y permiso

def test_los_valores_se_limitan_a_sus_rangos():
    assert F.limitar_visible(1) == 5 and F.limitar_visible(500) == 60
    assert F.limitar_visible("30") == 30 and F.limitar_visible(None) == F.VISIBLE_DEF
    assert F.limitar_visible("x") == 22
    assert F.limitar_desenfoque(-4) == 0 and F.limitar_desenfoque(99) == 20
    assert F.limitar_desenfoque(7.4) == 7 and F.limitar_desenfoque("z") == 0


def test_el_gestor_limita_lo_que_le_llega_de_los_deslizadores(app):
    g = F.GestorFondo(_ctx(app, None))
    g.poner_valores(2, 80)
    assert (g.visible, g.desenfoque) == (5, 20)
    g.poner_valores(100, -5)
    assert (g.visible, g.desenfoque) == (60, 0)


def test_la_opcion_solo_aparece_para_quien_puede(app):
    from descargador.ui.paginas.ajustes import PaginaAjustes
    # sin permiso: ni aparece
    ctx = _ctx(app, SesionFalsa({"puede_poner_fondo": False}))
    ctx.fondo = F.GestorFondo(ctx)
    ctx.fondo.aplicar_permiso(ctx.fondo.consultar_permiso())
    pag = PaginaAjustes(ctx)
    pag.resize(900, 700)
    pag.show()
    pausa(app, 0.3)
    assert not ctx.fondo.puede and not pag.seccion_fondo.isVisible()
    # con permiso: sí, y con su título
    ses = SesionFalsa({"puede_poner_fondo": True,
                       "ver_perfil": {"id": "u1", "usuario": "ana", "nombre": "Ana",
                                      "fundador_caudal": True}})
    ctx2 = _ctx(app, ses)
    ctx2.fondo = F.GestorFondo(ctx2)
    ctx2.fondo.aplicar_permiso(ctx2.fondo.consultar_permiso())
    pag2 = PaginaAjustes(ctx2)
    pag2.resize(900, 700)
    pag2.show()
    pausa(app, 0.3)
    assert ctx2.fondo.puede and pag2.seccion_fondo.isVisible()
    assert ctx2.fondo.titulo == F.TITULO_FUNDADOR
    assert pag2.seccion_fondo.insignia.texto == "Fundador de Caudal"
    textos = {b.text() for b in pag2.seccion_fondo.findChildren(type(pag2.seccion_fondo.bt_elegir))}
    assert {"Elegir imagen…", "Quitar fondo"} <= textos
    assert (pag2.seccion_fondo.s_visible.minimum(), pag2.seccion_fondo.s_visible.maximum()) == (5, 60)
    assert (pag2.seccion_fondo.s_desen.minimum(), pag2.seccion_fondo.s_desen.maximum()) == (0, 20)
    # un donador cualquiera
    ses3 = SesionFalsa({"puede_poner_fondo": True, "ver_perfil": {"id": "u", "usuario": "ana",
                                                                  "nombre": "Ana"}})
    g3 = F.GestorFondo(_ctx(app, ses3))
    g3.aplicar_permiso(g3.consultar_permiso())
    assert g3.titulo == F.TITULO_DONADOR


def test_sin_permiso_no_se_puede_poner_aunque_se_intente(app, tmp_path):
    g = F.GestorFondo(_ctx(app, SesionFalsa({"puede_poner_fondo": False})))
    with pytest.raises(nube.ErrorNube):
        g.poner_imagen(imagen_de_prueba(tmp_path / "a.png"))
    assert not g.activo


# ================================================================ la imagen y la nube

def test_la_imagen_se_reduce_y_se_sube_con_el_patron_de_la_foto(app, tmp_path):
    ses = SesionFalsa({"puede_poner_fondo": True})
    g = F.GestorFondo(_ctx(app, ses))
    g.puede = True
    grande = imagen_de_prueba(tmp_path / "grande.png", 3600, 2000)
    datos = g.poner_imagen(grande)
    img = QImage()
    img.loadFromData(datos)
    assert max(img.width(), img.height()) == 1920 and len(datos) < 5 * 1024 * 1024
    esperar(app, lambda: ses.subidos, "la subida")
    assert ses.subidos[0][:3] == ("avatares", "yo-id/fondo.jpg", "image/jpeg")
    assert ses.subidos[0][4] is True                       # reemplaza el anterior
    esperar(app, lambda: any(c[0] == "PATCH" for c in ses.llamadas), "el guardado del perfil")
    parche = [c for c in ses.llamadas if c[0] == "PATCH"][-1]
    assert parche[1] == "perfiles?id=eq.yo-id"
    assert parche[2]["json"]["fondo_url"] == "yo-id/fondo.jpg"
    assert parche[2]["json"]["fondo_visible"] == 22 and parche[2]["json"]["fondo_desenfoque"] == 0
    # una imagen chica no se agranda
    chica = F.preparar_fondo(imagen_de_prueba(tmp_path / "chica.jpg", 640, 360, formato="JPG"))
    ci = QImage()
    ci.loadFromData(chica)
    assert (ci.width(), ci.height()) == (640, 360)


def test_una_imagen_rota_se_explica_sin_jerga(app, tmp_path):
    malo = tmp_path / "roto.png"
    malo.write_bytes(b"no soy una imagen")
    with pytest.raises(nube.ErrorNube) as e:
        F.preparar_fondo(str(malo))
    assert "jpg, png o webp" in str(e.value)


def test_sin_red_se_usa_la_copia_local(app, tmp_path):
    ses = SesionFalsa({"puede_poner_fondo": True})
    g = F.GestorFondo(_ctx(app, ses))
    g.puede, g.titulo = True, F.TITULO_DONADOR
    g.poner_imagen(imagen_de_prueba(tmp_path / "a.png"))
    g.poner_valores(40, 9)
    g.guardar_ajustes()
    esperar(app, lambda: ses.subidos, "la subida")
    pausa(app, 0.2)
    # al abrir otra vez, sin internet: se ve al instante, con sus ajustes
    caida = SesionFalsa(sin_red=True)
    g2 = F.GestorFondo(_ctx(app, caida))
    assert g2.puede and g2.activo and (g2.visible, g2.desenfoque) == (40, 9)
    assert g2.imagen.width() == 800
    g2.aplicar_remoto(g2._traer())                         # sin red: no pierde nada
    assert g2.activo and g2.puede and (g2.visible, g2.desenfoque) == (40, 9)
    g2.verificar_permiso()
    pausa(app, 0.3)
    assert g2.activo and g2.puede


def test_la_nube_manda_al_iniciar_sesion(app, tmp_path, monkeypatch):
    base = imagen_de_prueba(tmp_path / "n.png", 1000, 600)
    datos = F.preparar_fondo(base)
    monkeypatch.setattr(F, "_descargar", lambda url: datos)
    ses = SesionFalsa({"puede_poner_fondo": True,
                       "GET perfiles": [{"fondo_url": "yo-id/fondo.jpg", "fondo_visible": 33,
                                         "fondo_desenfoque": 4}]})
    g = F.GestorFondo(_ctx(app, ses))
    assert not g.activo
    g.aplicar_remoto(g._traer())
    assert g.puede and g.activo and (g.visible, g.desenfoque) == (33, 4)
    # y queda copia local para el próximo arranque
    assert F.GestorFondo(_ctx(app, None)).activo
    # si la cuenta pierde el permiso, el fondo se va
    ses.datos["puede_poner_fondo"] = False
    g.aplicar_remoto(g._traer())
    assert not g.puede and not g.activo
    assert not F.GestorFondo(_ctx(app, None)).activo


# ================================================================ lo que se ve

def test_poner_y_quitar_el_fondo_cambia_y_restaura_lo_pintado(app, ventana_sin_ruido, tmp_path):
    from descargador.ui import estilos
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.navegar({"pagina": "descargas"})
    pausa(app, 0.5)
    antes = v.grab().toImage()
    assert not v.capa_fondo.isVisible() and not estilos.FONDO["activo"]
    # con fondo: otra cosa
    v.fondo.poner_imagen(imagen_de_prueba(tmp_path / "f.png", 1200, 700))
    v.fondo.poner_valores(40, 0)
    pausa(app, 0.7)
    assert v.capa_fondo.isVisible() and estilos.FONDO["activo"]
    con = v.grab().toImage()
    distintos = sum(1 for y in range(0, antes.height(), 7) for x in range(0, antes.width(), 7)
                    if antes.pixel(x, y) != con.pixel(x, y))
    assert distintos > 0.3 * (antes.height() // 7) * (antes.width() // 7)
    # los deslizadores se notan al momento en toda la aplicación
    v.fondo.poner_valores(10, 0)
    pausa(app, 0.1)
    poco = v.grab().toImage()
    assert poco.pixel(640, 790) != con.pixel(640, 790) or poco.pixel(305, 400) != con.pixel(305, 400)
    # quitar: vuelve exactamente al aspecto de siempre
    v.fondo.quitar()
    pausa(app, 0.8)
    assert not v.capa_fondo.isVisible() and not estilos.FONDO["activo"]
    despues = v.grab().toImage()
    iguales = sum(1 for y in range(0, antes.height(), 5) for x in range(0, antes.width(), 5)
                  if antes.pixel(x, y) == despues.pixel(x, y))
    total = len(range(0, antes.height(), 5)) * len(range(0, antes.width(), 5))
    assert iguales == total
    v.deleteLater()


def test_con_fondo_el_texto_sigue_leyendose_en_el_peor_caso(app, ventana_sin_ruido, tmp_path):
    from descargador.ui.estilos import C
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.navegar({"pagina": "descargas"})
    # la imagen más clara posible (blanca) y el máximo permitido (60 %)
    v.fondo.poner_imagen(imagen_de_prueba(tmp_path / "blanca.png", 1200, 700, "#FFFFFF"))
    v.fondo.poner_valores(60, 0)
    pausa(app, 0.8)
    img = v.grab().toImage()
    pag = v.pila.currentWidget()
    esq = pag.mapTo(v, pag.rect().topLeft())
    # sitios sin texto donde sí se escribe: el margen de la página y el panel de la izquierda
    zonas = [(esq.x() + 2, esq.y() + 200, esq.x() + 18, esq.y() + 500), (9, 640, 15, 690)]   # franja entre el borde del panel y las portadas
    for z in zonas:
        peor = luz_maxima(img, *z)
        assert contraste(C["texto"], peor.name()) >= 4.5, (z, peor.name())
    # el texto secundario (gris) en la misma zona de la página
    peor = luz_maxima(img, *zonas[0])
    assert contraste(C["texto2"], peor.name()) >= 3.0
    v.deleteLater()


def test_el_color_de_la_app_se_conserva_al_recolorear_en_vivo(app, ventana_sin_ruido, tmp_path):
    from descargador.ui import estilos
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.fondo.poner_imagen(imagen_de_prueba(tmp_path / "f.png"))
    pausa(app, 0.6)
    v.ajustes["acento"] = "rosa"
    v.ajustes["fondo"] = "noche"
    v._recolorear_en_vivo()
    pausa(app, 0.3)
    assert estilos.FONDO["activo"] and v.capa_fondo.isVisible()
    assert "rgba(" in v.styleSheet() and estilos.C["panel"] == "#0E1426"
    assert "14, 20, 38" in v.styleSheet()                  # el panel nuevo, translúcido
    img = v.grab().toImage()
    assert not img.isNull()
    v.deleteLater()


def test_blur_y_redimension_no_rompen_la_capa(app, ventana_sin_ruido, tmp_path):
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.fondo.poner_imagen(imagen_de_prueba(tmp_path / "f.png", 1600, 900))
    v.fondo.poner_valores(30, 20)
    pausa(app, 0.5)
    v.resize(1100, 700)
    pausa(app, 0.4)
    v.resize(1500, 950)
    pausa(app, 0.4)
    assert v.capa_fondo.size() == v.size()
    assert v.capa_fondo.rend._clave[1:3] == (v.width(), v.height())
    v.deleteLater()


# ================================================================ la pantalla de ajuste

def test_pantalla_de_ajuste_elegir_deslizar_quitar_y_soltar(app, ventana_sin_ruido, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.navegar({"pagina": "ajustes"})
    pausa(app, 0.4)
    pag = v.pila.currentWidget()
    sec = pag.seccion_fondo
    assert sec.isVisible() and not sec.bt_quitar.isEnabled()
    assert not sec.s_visible.isEnabled()
    foto = imagen_de_prueba(tmp_path / "elegida.png")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (foto, ""))
    sec.bt_elegir.click()
    pausa(app, 0.6)
    assert v.fondo.activo and sec.bt_quitar.isEnabled() and sec.s_visible.isEnabled()
    # los deslizadores se ven en vivo y se guardan al soltar
    sec.s_visible.setSliderDown(True)
    sec.s_visible.setValue(48)
    sec.s_desen.setValue(12)
    assert (v.fondo.visible, v.fondo.desenfoque) == (48, 12)
    assert sec.et_visible.text() == "48 %" and sec.et_desen.text() == "12"
    sec.s_visible.setSliderDown(False)
    n = len([c for c in ses.llamadas if c[0] == "PATCH"])
    sec.s_visible.sliderReleased.emit()
    esperar(app, lambda: len([c for c in ses.llamadas if c[0] == "PATCH"]) > n, "el guardado")
    assert ses.llamadas[-1][2]["json"] == {"fondo_visible": 48, "fondo_desenfoque": 12}
    assert F.GestorFondo(_ctx(app, None)).visible == 48
    # quitar
    sec.bt_quitar.click()
    pausa(app, 0.5)
    assert not v.fondo.activo and not sec.bt_quitar.isEnabled()
    esperar(app, lambda: ses.borrados, "el borrado en la nube")
    assert ses.borrados[0] == ("avatares", ["yo-id/fondo.jpg"])
    # arrastrar y soltar una imagen
    otra = imagen_de_prueba(tmp_path / "soltada.jpg", 900, 500, "#8A6CFF", "JPG")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(otra)])
    ev = QDropEvent(QPointF(20, 20), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    sec.dropEvent(ev)
    pausa(app, 0.5)
    assert v.fondo.activo
    # un archivo que no es imagen se ignora
    mime2 = QMimeData()
    mime2.setUrls([QUrl.fromLocalFile(str(tmp_path / "x.txt"))])
    v.fondo.quitar()
    sec.dropEvent(QDropEvent(QPointF(20, 20), Qt.CopyAction, mime2, Qt.LeftButton, Qt.NoModifier))
    assert not v.fondo.activo
    v.deleteLater()


# ================================================================ capturas para mirar

@pytest.mark.skipif(not os.path.exists(EJEMPLO), reason="falta la imagen de ejemplo")
def test_capturas_con_la_imagen_de_ejemplo(app, ventana_sin_ruido):
    os.makedirs(CAPTURAS, exist_ok=True)
    v, ctx, ses = ventana_con_permiso(app, ventana_sin_ruido)
    v.fondo.poner_imagen(EJEMPLO)
    v.fondo.poner_valores(30, 0)
    for nombre, pagina in (("descargas", "descargas"), ("ajustes", "ajustes"), ("inicio", "inicio")):
        v.navegar({"pagina": pagina})
        pausa(app, 0.8)
        assert v.grab().save(os.path.join(CAPTURAS, f"{nombre}_30_0.png"))
    pag = v.pila.currentWidget() if False else None
    v.navegar({"pagina": "ajustes"})
    pausa(app, 0.5)
    pag = v.pila.currentWidget()
    pag.verticalScrollBar().setValue(pag.seccion_fondo.y() - 40)
    v.fondo.poner_valores(25, 6)
    pausa(app, 0.5)
    assert v.grab().save(os.path.join(CAPTURAS, "seccion_fondo_25_6.png"))
    v.deleteLater()
