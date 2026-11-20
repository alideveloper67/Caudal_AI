# -*- coding: utf-8 -*-
"""La ventana real con el visualizador, el karaoke, los colores de la carátula, los sonidos de interfaz, la
insignia de calidad real y los ajustes nuevos. Sin ventanas a la vista (Qt offscreen), sin internet y sin motor
de audio (libmpv apagado: nada suena)."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QPushButton  # noqa: E402

PISTA = {"tipo": "pista", "clave": "yt:1", "video_id": "id1", "titulo": "Medianoche en Lima",
         "artista": "Las Estrellas", "miniatura": "u1", "duracion": 200}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pausa(app, s=0.2):
    fin = time.time() + s
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture(scope="module")
def bases():
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None          # nada de motores de audio reales
    from descargador.coleccion import Coleccion
    from descargador.historial import Historial
    return Coleccion(), Historial()


@pytest.fixture
def ctx(app, bases, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    from descargador.config import Ajustes
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui.contexto import Contexto
    aj = Ajustes()
    col, his = bases
    return Contexto(aj, his, col, Gestor(aj, his), Reproductor(aj, col))


def caratula():
    img = QImage(200, 200, QImage.Format_RGB32)
    p = QPainter(img)
    p.fillRect(0, 0, 100, 200, QColor("#E11D1D"))
    p.fillRect(100, 0, 100, 200, QColor("#E8590C"))
    p.end()
    return img


@pytest.fixture
def ventana(app, ctx, monkeypatch):
    from descargador import fondo as F
    from descargador import paleta_caratula
    from descargador.ui import imagenes
    from descargador.ui.ventana import Ventana
    paleta_caratula.CACHE.clear()
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: 0)
    monkeypatch.setattr(Ventana, "buscar_version", lambda self, *a, **k: None)
    monkeypatch.setattr(Ventana, "_avisar_novedades", lambda self, *a, **k: None)
    monkeypatch.setattr(F.GestorFondo, "sincronizar", lambda self: None)
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(caratula()))
    ctx.cuenta = {"usuario": "ana", "nombre": "Ana", "sesion": None}
    v = Ventana(ctx)
    v.ctx_falso = ctx
    v.resize(1280, 800)
    yield v
    try:
        v.gamer.cerrar()
    finally:
        v.hide()
        v.deleteLater()      # que sus temporizadores no salten en la prueba siguiente
        from descargador.ui.neon_gamer import reloj_neon
        reloj_neon().pausar(False)
        reloj_neon().activar(True)


def hacer_donador(v, si=True):
    from descargador.premium_datos import EstadoPremium
    v.premium.estado = EstadoPremium(si, "donador" if si else None)
    v.premium.cambiado.emit()


def poner_a_sonar(v):
    v.ctx_falso.reproductor.actual = dict(PISTA)
    v.ctx_falso.reproductor.pista_cambio.emit(v.r.actual)
    v.ctx_falso.reproductor._fijar_estado("sonando")


def actual(v):
    return v.historia[v.indice][0].get("pagina")


# ------------------------------------------------------------------ puerta de donadores

def test_sin_donador_se_abre_donar_y_no_la_vista(app, ventana, monkeypatch):
    from descargador.ui import donar
    abiertas = []
    monkeypatch.setattr(donar, "abrir_donar", lambda padre=None: abiertas.append(1))
    poner_a_sonar(ventana)
    ventana.abrir_visualizador("barras")
    ventana.abrir_karaoke()
    assert len(abiertas) == 2
    assert "visualizador" not in ventana.singletons and "karaoke" not in ventana.singletons
    assert actual(ventana) not in ("visualizador", "karaoke")


def test_con_donador_pero_sin_cancion_avisa(app, ventana, monkeypatch):
    avisos = []
    monkeypatch.setattr(ventana.aviso, "mostrar", lambda t, *a, **k: avisos.append(t))
    hacer_donador(ventana)
    ventana.abrir_visualizador()
    ventana.abrir_karaoke()
    assert len(avisos) == 2 and "sonar" in avisos[0] and actual(ventana) not in ("visualizador", "karaoke")


def test_con_donador_se_abre_el_visualizador_y_se_cambia_de_estilo(app, ventana):
    from descargador.ui.visualizador import PaginaVisualizador
    hacer_donador(ventana)
    poner_a_sonar(ventana)
    ventana.show()
    ventana.abrir_visualizador("barras")
    pausa(app, 0.2)
    pag = ventana.pila.currentWidget()
    assert isinstance(pag, PaginaVisualizador) and pag.estilo == "barras"
    assert ventana.ajustes["visualizador_estilo"] == "barras"
    assert ventana.barra.bt_visual._activo
    largo = len(ventana.historia)
    ventana.abrir_visualizador("particulas")                     # ya está abierto: solo cambia de estilo
    assert pag.estilo == "particulas" and len(ventana.historia) == largo
    ventana.cerrar_vista_grande()
    assert actual(ventana) not in ("visualizador", "karaoke") and not ventana.barra.bt_visual._activo
    ventana.abrir_karaoke()
    from descargador.ui.karaoke import PaginaKaraoke
    assert isinstance(ventana.pila.currentWidget(), PaginaKaraoke)
    ventana.abrir_visualizador()                                 # de karaoke a visualizador
    assert isinstance(ventana.pila.currentWidget(), PaginaVisualizador)


def test_pantalla_completa_y_esc(app, ventana):
    hacer_donador(ventana)
    poner_a_sonar(ventana)
    ventana.show()
    ventana.abrir_karaoke()
    pausa(app, 0.1)
    pag = ventana.pila.currentWidget()
    pag.bt_completa.click()
    assert ventana.en_completa and not ventana.barra.isVisible() and not ventana.lateral.isVisible()
    # Esc: sale de la pantalla completa y cierra la vista
    esc = [s for s in ventana.findChildren(QShortcut) if s.key() == QKeySequence("Escape")]
    assert esc
    esc[0].activated.emit()
    assert not ventana.en_completa and ventana.barra.isVisible() and ventana.lateral.isVisible()
    assert actual(ventana) not in ("visualizador", "karaoke")


def test_el_atajo_del_visualizador_y_del_karaoke_existen(app, ventana):
    teclas = {s.key().toString() for s in ventana.findChildren(QShortcut)}
    assert {"Ctrl+Shift+V", "Ctrl+Shift+K"} <= teclas


# ------------------------------------------------------------------ ahorro del modo gamer

def test_el_modo_gamer_en_ahorro_detiene_el_visualizador_y_lo_devuelve(app, ventana):
    hacer_donador(ventana)
    poner_a_sonar(ventana)
    ventana.show()
    ventana.abrir_visualizador()
    pausa(app, 0.2)
    pag = ventana.pila.currentWidget()
    assert pag.reloj.isActive() and pag.reloj.interval() == 33
    ventana.gamer.entrar_en_ahorro("juego.exe")
    assert not pag.reloj.isActive()
    t_modelo = pag.modelo._t                                     # (el tiempo interno solo avanza con el reloj)
    pausa(app, 0.3)
    assert pag.modelo._t == t_modelo
    ventana.gamer.salir_de_ahorro()
    assert pag.reloj.isActive()
    pausa(app, 0.2)
    assert pag.modelo._t > t_modelo


def test_en_ahorro_la_barra_no_anima_los_colores(app, ventana):
    hacer_donador(ventana)
    ventana.gamer.entrar_en_ahorro("juego.exe")
    try:
        poner_a_sonar(ventana)
        g = ventana.barra._colores
        assert not g.animando and g.fuerza == 1.0                   # saltó directo, sin reloj
    finally:
        ventana.gamer.salir_de_ahorro()


# ------------------------------------------------------------------ la barra

def test_el_boton_de_la_barra_ofrece_los_estilos_y_el_karaoke_con_candado(app, ventana, monkeypatch):
    from descargador.ui import barra_reproduccion as BR
    menus = []

    class MenuFalso(QMenu):
        def exec(self, *a, **k):                                  # (no se abre: solo se anota qué ofrece)
            menus.append([x.text() for x in self.actions() if x.text()])
    monkeypatch.setattr(BR, "QMenu", MenuFalso)
    ventana.barra._menu_visual()
    assert all(t.startswith("🔒") for t in menus[0][:4]) and menus[0][-1] == "Exclusivo para donadores"
    hacer_donador(ventana)
    ventana.barra._menu_visual()
    assert menus[1] == ["Visualizador · Ondas", "Visualizador · Partículas", "Visualizador · Barras",
                        "Karaoke a pantalla completa", "Letra con efectos a pantalla completa"]


def test_los_estilos_del_menu_llegan_a_la_ventana(app, ventana, monkeypatch):
    pedidos = []
    monkeypatch.setattr(ventana, "abrir_visualizador", lambda e=None: pedidos.append(e))
    ventana.barra.pidio_visualizador.emit("barras")
    assert pedidos == ["barras"]


def test_la_barra_toma_los_colores_de_la_caratula_con_transicion(app, ventana):
    hacer_donador(ventana)
    barra = ventana.barra
    barra.resize(1200, 88)
    barra.show()
    sin = barra.grab().toImage()
    assert barra.barra.color_relleno is None
    poner_a_sonar(ventana)
    assert barra._colores.animando
    pausa(app, 1.2)
    assert barra._colores.fuerza > 0.95 and barra.barra.color_relleno is not None
    con = barra.grab().toImage()
    assert con != sin
    # el tinte se nota en el extremo izquierdo (rojo de la carátula) sin comerse los controles
    p0, p1 = sin.pixelColor(3, 40), con.pixelColor(3, 40)
    assert p1.red() > p0.red()
    # apagarlo devuelve la barra de siempre
    ventana.ajustes["colores_caratula"] = False
    barra._colores.refrescar()
    pausa(app, 1.2)
    assert barra.barra.color_relleno is None and barra._colores.fuerza == 0


def test_sin_donador_la_barra_no_cambia(app, ventana):
    poner_a_sonar(ventana)
    pausa(app, 0.3)
    assert ventana.barra._colores.fuerza == 0 and ventana.barra.barra.color_relleno is None


def test_insignia_de_calidad_real(app, ventana):
    barra = ventana.barra
    poner_a_sonar(ventana)
    barra._audio_real({"codec": "opus", "bitrate": 160000,
                       "params": {"samplerate": 48000, "format": "fltp", "channels": "stereo"}})
    assert barra.et_calidad.isVisibleTo(barra) and barra.et_calidad.text() == "OPUS 160 kbps"
    assert "48 kHz" in barra.et_calidad.toolTip() and "estéreo" in barra.et_calidad.toolTip()
    barra._audio_real({"codec": "flac", "bitrate": 0, "params": {"samplerate": 44100, "format": "s16"}})
    assert barra.et_calidad.text() == "FLAC 16/44,1"
    # sin datos o en modo video no se toca
    barra._audio_real({})
    assert barra.et_calidad.text() == "FLAC 16/44,1"
    ventana.r.modo = "video"
    barra._audio_real({"codec": "aac", "bitrate": 128000, "params": {"samplerate": 44100}})
    assert barra.et_calidad.text() == "FLAC 16/44,1"
    ventana.r.modo = "audio"


def test_el_reproductor_avisa_del_audio_real_solo_del_motor_actual(app, ctx):
    r = ctx.reproductor
    recibidos = []
    r.audio_real_cambio.connect(recibidos.append)

    class _M:
        _cerrado = False

        def __init__(self, datos):
            self.d = datos

        def info_audio(self):
            return self.d
    activo, otro = _M({"codec": "opus", "params": {"samplerate": 48000}}), _M({"codec": "aac", "params": {}})
    r.audio = [activo, otro]
    r.activo = 0
    r._traspaso = None
    r._al_audio_real(activo)
    r._al_audio_real(otro)                                       # el que no suena no cuenta
    pausa(app, 0.1)                                              # la lectura se hace en el hilo de la interfaz
    assert recibidos == [activo.d]
    r._al_audio_real(_M({"codec": None, "params": None}))
    assert len(recibidos) == 1
    r.audio = []


# ------------------------------------------------------------------ sonidos de interfaz

def test_sonidos_al_dar_me_gusta_solo_con_donador_y_activado(app, ventana, monkeypatch):
    from descargador import sonidos_ui as SU
    sonados = []
    monkeypatch.setattr(SU, "tocar", lambda n: sonados.append(n) or True)
    ctx = ventana.ctx_falso
    assert ctx.sonidos_ui is not None
    ctx.me_gusta_cambio.emit("x", True)
    assert sonados == []                                         # sin donador
    hacer_donador(ventana)
    ctx.me_gusta_cambio.emit("x", True)
    assert sonados == []                                         # apagado de fábrica
    ventana.ajustes["sonidos_ui"] = True
    ventana.ajustes["sonido_ui_tipo"] = "campana"
    ctx.me_gusta_cambio.emit("x", True)
    ctx.me_gusta_cambio.emit("x", False)
    assert sonados == ["campana"]


# ------------------------------------------------------------------ ajustes

def test_ajustes_trae_los_controles_nuevos_y_los_recuerda(app, ventana, monkeypatch):
    from descargador import sonidos_ui as SU
    sonados = []
    monkeypatch.setattr(SU, "tocar", lambda n: sonados.append(n) or True)
    hacer_donador(ventana)
    ventana.show()
    ventana.navegar({"pagina": "ajustes"})
    pag = ventana.pila.currentWidget()
    assert pag.colores_c.isChecked() and not pag.sonidos_ui.isChecked()
    pag.colores_c.setChecked(False)
    assert ventana.ajustes["colores_caratula"] is False
    pag.sonidos_ui.setChecked(True)
    assert ventana.ajustes["sonidos_ui"] is True
    i = pag.sonido_tipo.findData("moneda")
    pag.sonido_tipo.setCurrentIndex(i)
    assert ventana.ajustes["sonido_ui_tipo"] == "moneda" and sonados == ["moneda"]   # se oye al elegirlo
    textos = {b.text() for b in pag.findChildren(QPushButton)}
    assert {"Ver mi semana", "Buscar"} <= textos
    hacer_donador(ventana, False)
    pag.sonido_tipo.setCurrentIndex(pag.sonido_tipo.findData("campana"))
    assert sonados == ["moneda"]                                 # sin donador la prueba no suena


def test_los_ajustes_por_defecto(ctx):
    a = ctx.ajustes
    assert a["visualizador_estilo"] == "ondas" and a["colores_caratula"] is True
    assert a["sonidos_ui"] is False and a["sonido_ui_tipo"] == "burbuja"
