# -*- coding: utf-8 -*-
"""Que la interfaz no espere a nadie: disco, mpv, reconocedor de voz, base de datos y arrastre."""

import json
import os
import sys
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ------------------------------------------------------------------ disco

@pytest.fixture
def disco():
    from descargador import disco as d
    yield d
    d.desactivar()


def test_sin_activar_se_escribe_al_momento(disco, tmp_path):
    r = tmp_path / "a.json"
    disco.escribir(r, "hola")
    assert r.read_text(encoding="utf-8") == "hola"


def test_activado_no_espera_y_solo_escribe_lo_ultimo(disco, tmp_path, monkeypatch):
    escritos = []

    def lento(ruta, texto):
        time.sleep(0.15)
        escritos.append(texto)
        return True
    monkeypatch.setattr(disco, "_escribir_ya", lento)
    disco.activar()
    t = time.perf_counter()
    for i in range(20):
        disco.escribir(tmp_path / "a.json", str(i))
    assert time.perf_counter() - t < 0.08
    assert disco.vaciar(segundos=3)
    assert escritos[-1] == "19" and len(escritos) <= 3


def test_vaciar_espera_al_archivo_pedido(disco, tmp_path):
    disco.activar()
    r = tmp_path / "b.json"
    disco.escribir(r, "x" * 1000)
    assert disco.vaciar(r) and r.read_text(encoding="utf-8") == "x" * 1000
    assert not list(tmp_path.glob("*.tmp"))


def test_los_ajustes_se_leen_aunque_vayan_de_camino(disco, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador.config import Ajustes
    disco.activar()
    a = Ajustes()
    a["volumen"] = 37
    a.guardar()
    assert Ajustes()["volumen"] == 37


# ------------------------------------------------------------------ mpv

def test_las_ordenes_no_esperan_van_en_orden_y_juntan_las_repetidas():
    from descargador.reproduccion import _Ordenes
    o = _Ordenes("prueba")
    hechas, puerta = [], threading.Event()
    o.dar(lambda: puerta.wait(2))
    t = time.perf_counter()
    o.dar(lambda: hechas.append("cargar"))
    for i in range(30):
        o.dar(lambda i=i: hechas.append(i), "volumen")
    o.dar(lambda: hechas.append("seguir"))
    assert time.perf_counter() - t < 0.05
    puerta.set()
    assert o.esperar()
    assert hechas == ["cargar", 29, "seguir"]


def test_una_orden_que_falla_no_para_las_demas():
    from descargador.reproduccion import _Ordenes
    o = _Ordenes("prueba")
    hechas = []
    o.dar(lambda: 1 / 0)
    o.dar(lambda: hechas.append(1))
    assert o.esperar() and hechas == [1]


def test_acabar_tira_lo_pendiente():
    from descargador.reproduccion import _Ordenes
    o = _Ordenes("prueba")
    hechas, puerta, fin = [], threading.Event(), threading.Event()
    o.dar(lambda: puerta.wait(2))
    time.sleep(0.05)
    o.dar(lambda: hechas.append("no"))
    o.acabar(fin.set)
    o.dar(lambda: hechas.append("tampoco"))
    puerta.set()
    assert fin.wait(2) and hechas == []


class _MpvLento:
    """Un mpv ocupado: cada cosa que se le pide tarda."""
    def __init__(self, **_k):
        self.puesto = []
        self.mirando = {}

    def observe_property(self, n, f):
        self.mirando[n] = f

    def unobserve_property(self, n, f):
        pass

    def event_callback(self, _n):
        return lambda f: self.mirando.setdefault("ev:" + _n, f)

    def register_key_binding(self, *_a):
        time.sleep(0.02)

    def command(self, *a):
        time.sleep(0.2)
        self.puesto.append(a)

    def loadfile(self, *a, **k):
        time.sleep(0.2)
        self.puesto.append(("load", a[0]))

    def __setitem__(self, k, v):
        time.sleep(0.2)
        self.puesto.append((k, v))

    def __setattr__(self, k, v):
        if k in ("puesto", "mirando"):
            object.__setattr__(self, k, v)
        else:
            time.sleep(0.2)
            self.puesto.append((k, v))

    def terminate(self):
        self.puesto.append("fin")


@pytest.fixture
def motor(app, monkeypatch):
    from descargador import reproduccion

    class Mod:
        MPV = _MpvLento
    monkeypatch.setattr(reproduccion.mpv_carga, "modulo", lambda: Mod)
    m = reproduccion.Motor({"aceleracion": False}, None, "prueba")
    yield m
    m.cerrar(esperar=False)


def test_el_motor_nunca_hace_esperar_a_la_interfaz(motor):
    t = time.perf_counter()
    motor.fijar_volumen(40)
    motor.cargar({"archivo": "a.mp3", "titulo": "A"}, inicio=12)
    motor.pausar(True)
    motor.buscar(30)
    motor.fijar_filtros("lavfi=[volume=-3dB]")
    assert motor.en_pausa() is True
    motor.posicion_actual(), motor.duracion_actual(), motor.info_audio()
    assert time.perf_counter() - t < 0.06
    assert motor.esperar_ordenes(8)
    claves = [x[0] for x in motor.mpv.puesto]
    assert claves.index("volume") < claves.index("load") < claves.index("af")


def test_lo_que_avisa_mpv_de_lo_anterior_se_descarta(motor):
    avisos = []
    motor.posicion.connect(avisos.append)
    motor.esperar_ordenes(3)
    motor.cargar({"archivo": "b.mp3", "titulo": "B"})
    motor.mpv.mirando["time-pos"]("time-pos", 150.0)        # aún suena la de antes
    assert motor.posicion_actual() == 0.0
    assert motor.esperar_ordenes(5)
    motor.mpv.mirando["time-pos"]("time-pos", 1.5)
    assert 1.5 <= motor.posicion_actual() < 2.2


def test_al_saltar_no_vuelve_la_posicion_vieja(motor):
    motor.esperar_ordenes(3)
    motor.mpv.mirando["time-pos"]("time-pos", 10.0)
    motor.buscar(90)
    motor.mpv.mirando["time-pos"]("time-pos", 10.2)          # llegó antes de que mpv saltara
    assert motor.posicion_actual() >= 90.0


def test_cargas_seguidas_solo_abren_la_ultima(motor):
    motor.esperar_ordenes(3)
    for n in ("a", "b", "c"):
        motor.cargar({"archivo": f"{n}.mp3", "titulo": n})
    assert motor.esperar_ordenes(8)
    assert [x[1] for x in motor.mpv.puesto if x[0] == "load"][-1] == "c.mp3"
    assert len([x for x in motor.mpv.puesto if x[0] == "load"]) <= 2


def test_cerrar_sin_esperar_avisa_al_terminar(motor):
    fin = threading.Event()
    t = time.perf_counter()
    motor.cerrar(al_terminar=fin.set, esperar=False)
    assert time.perf_counter() - t < 0.05
    assert fin.wait(3) and "fin" in motor.mpv.puesto


# ------------------------------------------------------------------ reconocedor de voz aparte

def test_saber_si_hay_reconocedor_no_lo_carga():
    import subprocess
    codigo = ("import sys; from descargador import sincronia_letra as s; s.disponible(); "
              "print('faster_whisper' in sys.modules)")
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, timeout=60,
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert r.stdout.strip() == "False"


def test_el_ayudante_contesta_y_sobrevive_a_un_error():
    from descargador import ayudante
    try:
        assert ayudante.pedir("hola", {}, 40) == {"hola": True}
        with pytest.raises(ayudante.ErrorAyudante):
            ayudante.pedir("esto no existe", {}, 40)
        assert ayudante.pedir("hola", {}, 40) == {"hola": True}
        ayudante._proc.kill()                     # murió: se abre otro solo
        ayudante._proc.wait(5)
        assert ayudante.pedir("hola", {}, 40) == {"hola": True}
    finally:
        ayudante.cerrar()


def test_sin_activar_el_ayudante_no_se_usa():
    from descargador import ayudante
    assert ayudante.disponible() is False


# ------------------------------------------------------------------ base de datos

def test_los_hilos_leen_por_su_conexion_y_no_bloquean(tmp_path):
    from descargador.coleccion import Coleccion
    c = Coleccion(tmp_path / "h.db")
    c.con.execute("INSERT INTO pistas (clave, datos, actualizada) VALUES ('a','{}',1)")
    c.con.commit()
    salida = {}

    def leer():
        salida["n"] = c.con.execute("SELECT COUNT(*) n FROM pistas").fetchone()["n"]
        salida["propia"] = getattr(c.con._propias, "con", None) is not None
    h = threading.Thread(target=leer)
    with c.con._cerrojo:                          # la interfaz tiene la base ocupada
        h.start()
        h.join(3)
        assert not h.is_alive(), "el hilo se quedó esperando a la interfaz"
    assert salida == {"n": 1, "propia": True}
    c.con.close()


def test_el_repaso_del_diario_va_en_otro_hilo(tmp_path, monkeypatch):
    from descargador.coleccion import Coleccion
    c = Coleccion(tmp_path / "h.db")
    assert c.con.execute("PRAGMA wal_autocheckpoint").fetchone()[0] == 0
    for i in range(60):
        c.con.execute("INSERT OR REPLACE INTO pistas (clave, datos, actualizada) VALUES (?,?,1)", (str(i), "{}"))
        c.con.commit()
    time.sleep(0.3)
    assert c.con._repaso[1] < 40
    c.con.close()


def test_el_repaso_estrena_el_diario_y_espera_a_un_momento_quieto(tmp_path):
    """El primer guardado tras el repaso espera al disco: lo hace el hilo, nunca la interfaz."""
    from descargador.coleccion import Coleccion
    c = Coleccion(tmp_path / "h.db")
    c.guardar_estado("x", 1)
    c.con._repasar_ahora(quieto=0)
    diario = open(str(tmp_path / "h.db-wal"), "rb").read(32)
    sal_antes = diario[16:24]                     # cambia cada vez que el diario se estrena
    c.guardar_estado("x", 2)                      # la interfaz: sigue el diario que ya estrenó el hilo
    assert open(str(tmp_path / "h.db-wal"), "rb").read(32)[16:24] == sal_antes
    assert c.estado("x") == 2 and c.estado("_repaso") == 1
    # con guardados seguidos, espera
    c.guardar_estado("x", 3)
    a = time.monotonic()
    c.con._repasar_ahora(quieto=0.5)
    assert time.monotonic() - a >= 0.4
    c.con.close()


# ------------------------------------------------------------------ interfaz

def test_el_arrastre_no_filtra_toda_la_aplicacion(app, monkeypatch):
    from PySide6.QtWidgets import QApplication
    from descargador.ui import arrastre
    puestos = []
    monkeypatch.setattr(arrastre, "_instancia", None)
    monkeypatch.setattr(QApplication, "installEventFilter", lambda self, f: puestos.append(f))
    arrastre.instalar(app)
    assert puestos == []


def test_arrastrar_sigue_desplazando(app):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QLabel, QScrollArea
    from descargador.ui.arrastre import ArrastreRaton
    area = QScrollArea()
    dentro = QLabel("x")
    dentro.setFixedSize(200, 2000)
    area.setWidget(dentro)
    area.resize(220, 300)
    area.show()
    app.processEvents()
    a = ArrastreRaton()
    a._vigilar(dentro)

    def ev(tipo, y, botones):
        from PySide6.QtWidgets import QApplication
        g = QPointF(50, y)
        QApplication.sendEvent(dentro, QMouseEvent(tipo, g, g, Qt.LeftButton if tipo != QEvent.MouseMove else
                                                   Qt.NoButton, botones, Qt.NoModifier))
    ev(QEvent.MouseButtonPress, 250, Qt.LeftButton)
    for y in (240, 200, 120):
        ev(QEvent.MouseMove, y, Qt.LeftButton)
    assert area.verticalScrollBar().value() > 60
    ev(QEvent.MouseButtonRelease, 120, Qt.NoButton)
    assert a._vigilados == []
    area.close()


def test_el_ritmo_baja_a_30_si_pintar_cuesta_y_vuelve_a_60(app, monkeypatch):
    from PySide6.QtCore import QTimer
    from descargador.ui.escena.escenarios import base
    reloj = QTimer()
    reloj.setInterval(33)
    ahora, gasto = [100.0], [0.002]
    monkeypatch.setattr(base.time, "monotonic", lambda: ahora[0])
    r = base.Ritmo(reloj)
    perf = [0.0]
    monkeypatch.setattr(base.time, "perf_counter", lambda: perf[0])

    def cuadros(n):
        for _ in range(n):
            r.antes()
            perf[0] += gasto[0]
            ahora[0] += 0.033
            r.despues()
    cuadros(150)
    assert reloj.interval() == 16
    gasto[0] = 0.015
    cuadros(200)
    assert reloj.interval() == 33


def test_letras_guardadas(tmp_path, monkeypatch):
    from descargador import letras_cache as L
    monkeypatch.setattr(L, "_carpeta", None)
    p = {"video_id": "abc", "titulo": "Luna", "artista": "Ana"}
    L.guardar(p, {"sincronizada": True, "lineas": [(0, "a")]})
    assert L.leer(p) is None                          # sin activar no guarda nada
    L.activar(tmp_path)
    buena = {"sincronizada": True, "lineas": [(0, "a"), (10, "b")], "texto": "a\nb"}
    L.guardar(p, buena)
    assert L.leer(p)["lineas"] == [(0, "a"), (10, "b")]
    ruta = L._ruta(p)
    g = json.loads(ruta.read_text(encoding="utf-8"))
    g["cuando"] = time.time() - 400 * 86400
    ruta.write_text(json.dumps(g), encoding="utf-8")
    assert L.leer(p) is None and L.leer(p, caducada=True) is not None
    L.olvidar(p)
    assert L.leer(p, caducada=True) is None
    monkeypatch.setattr(L, "_carpeta", None)


# ------------------------------------------------------------------ cambiar de escenario sin tirones

def test_la_ilustracion_se_decodifica_en_un_hilo_y_lo_de_antes_se_sigue_viendo(app):
    import time
    from descargador.ui.escena import escenarios
    from descargador.ui.escena.ventana import _FondoVentana
    f = _FondoVentana()
    f.resize(640, 360)
    f.show()
    app.processEvents()
    antes = f.pila.currentWidget()
    assert f.ver_escenario("lofi") is True
    assert f.pila.currentWidget() is antes and f._esperado == "lofi"      # todavía no: se está decodificando
    tope = time.monotonic() + 8
    while f.clave_escenario != "lofi" and time.monotonic() < tope:
        app.processEvents()
        time.sleep(0.005)
    assert f.clave_escenario == "lofi" and f.pila.currentWidget() is f.escenario and f._esperado is None
    assert not f.escenario._img.isNull()
    # arrepentirse a mitad: gana lo último que se pidió
    f.ver_escenario("goku")
    f.ver_video(False)
    tope = time.monotonic() + 1.5
    while time.monotonic() < tope:
        app.processEvents()
        time.sleep(0.01)
    assert f.pila.currentWidget() is f.ambiente and f.clave_escenario == "lofi"
    # volver a uno ya hecho, y los que se dibujan solos, van en el momento
    assert f.ver_escenario("lofi") and f.pila.currentWidget() is f.escenario
    assert f.ver_escenario("synthwave") and f.clave_escenario == "synthwave"
    assert escenarios.preparacion("synthwave") is None and escenarios.preparacion("no-existe") is None
    f.close()
    f.deleteLater()


def test_las_mascotas_de_ajustes_se_pintan_por_tandas(app):
    import time
    from PySide6.QtCore import QObject, Signal
    from descargador import mascotas as M
    from descargador.ui.mascotas_ajuste import SeccionMascotas

    class Gestor(QObject):
        cambiada = Signal()
        ctx, clave, puede, tiene_exclusivas = None, "", True, False

        def puede_elegir(self, _c):
            return True

    s = SeccionMascotas(Gestor())
    tope = time.monotonic() + 8
    while s._sin_dibujo and time.monotonic() < tope:
        app.processEvents()
    con_dibujo = [m["clave"] for m in M.catalogo_de(None) if M.cuadros(m["clave"])]
    assert con_dibujo and all(not s.botones[c].icon().isNull() for c in con_dibujo)
    s.deleteLater()


# ------------------------------------------------------------------ cookies del navegador: la música no espera

@pytest.fixture
def cookies_limpias(tmp_path, monkeypatch):
    from descargador import cookies_navegador as CN
    monkeypatch.setattr(CN, "_archivo", lambda: tmp_path / "ck.json")
    monkeypatch.setattr(CN, "_sabido", {})
    monkeypatch.setattr(CN, "_en_curso", {})
    monkeypatch.setattr(CN, "_leido", False)
    return CN


def test_las_cookies_se_prueban_una_vez_aunque_pregunten_muchos(cookies_limpias, monkeypatch):
    CN = cookies_limpias
    veces = []

    def lento(nav):
        veces.append(nav)
        time.sleep(0.4)
        raise RuntimeError("Failed to decrypt with DPAPI")
    monkeypatch.setattr(CN, "_leer", lento)
    a = time.monotonic()
    hilos = [threading.Thread(target=CN.usable, args=("chrome",)) for _ in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert veces == ["chrome"] and time.monotonic() - a < 1.5
    assert CN.usable("chrome") is None and CN.usable("ninguno") is None and CN.usable("") is None
    # otra sesión: ya se sabe, sin volver a probar
    CN._sabido.clear()
    CN._leido = False
    assert CN.usable("chrome") is None and veces == ["chrome"]
    CN.olvidar()
    monkeypatch.setattr(CN, "_leer", lambda nav: veces.append("ok"))
    assert CN.usable("chrome") == "chrome" and veces[-1] == "ok"


def test_si_las_cookies_tardan_la_cancion_sigue_sin_ellas(cookies_limpias, monkeypatch):
    CN = cookies_limpias
    soltar = threading.Event()
    monkeypatch.setattr(CN, "_leer", lambda nav: soltar.wait(5))
    a = time.monotonic()
    assert CN.usable("edge", espera=0.2) is None
    assert time.monotonic() - a < 1
    soltar.set()
    tope = time.monotonic() + 3
    while CN.usable("edge", espera=0.1) is None and time.monotonic() < tope:
        pass
    assert CN.usable("edge") == "edge"                # cuando se supo, se usan


def test_las_cookies_se_buscan_solo_donde_estan(tmp_path):
    from descargador.cookies_navegador import buscar_rapido
    (tmp_path / "Default" / "Network").mkdir(parents=True)
    (tmp_path / "Profile 2").mkdir()
    (tmp_path / "Default" / "Cache" / "x" / "y").mkdir(parents=True)
    for r in ("Default/Network/Cookies", "Profile 2/Cookies", "Default/Cache/x/y/Cookies"):
        (tmp_path / r).write_text("x")
    assert sorted(os.path.relpath(x, tmp_path).replace("\\", "/") for x in buscar_rapido(str(tmp_path), "Cookies")) \
        == ["Default/Network/Cookies", "Profile 2/Cookies"]
    (tmp_path / "Profiles" / "abc.default").mkdir(parents=True)
    (tmp_path / "Profiles" / "abc.default" / "cookies.sqlite").write_text("x")
    assert len(list(buscar_rapido(str(tmp_path), "cookies.sqlite"))) == 1
    assert list(buscar_rapido(str(tmp_path / "no"), "Cookies")) == []


def test_ytdlp_usa_la_busqueda_rapida():
    from descargador import cookies_navegador as CN
    from yt_dlp import cookies
    CN.aligerar_ytdlp()
    assert cookies._find_files is CN.buscar_rapido


def test_resolver_lo_mismo_a_la_vez_solo_se_hace_una_vez(monkeypatch):
    from descargador import catalogo
    hechos, cache = [], {}

    def lento(objetivo, *a):
        if objetivo in cache:
            return cache[objetivo]
        hechos.append(objetivo)
        time.sleep(0.3)
        cache[objetivo] = {"url": objetivo}
        return cache[objetivo]
    monkeypatch.setattr(catalogo, "_resolver", lento)
    sal = []
    hilos = [threading.Thread(target=lambda: sal.append(catalogo.resolver("abc"))) for _ in range(4)]
    otro = threading.Thread(target=lambda: sal.append(catalogo.resolver("xyz")))
    a = time.monotonic()
    [h.start() for h in hilos + [otro]]
    [h.join() for h in hilos + [otro]]
    assert sorted(hechos) == ["abc", "xyz"] and len(sal) == 5 and time.monotonic() - a < 0.6
    assert catalogo._en_vuelo == {}


def test_al_abrir_se_adelanta_la_cancion_donde_te_quedaste(monkeypatch):
    from types import SimpleNamespace
    from descargador import reproduccion as RP
    pedidos = []
    monkeypatch.setattr(RP, "en_segundo_plano", lambda f, *a, **k: pedidos.append(a[0]))
    r = SimpleNamespace(actual={"video_id": "v1"}, estado="parado", modo="audio", disponible=True,
                        ajustes={"preferir_descargado": True, "calidad_audio": "maxima", "codec_video": "auto"},
                        coleccion=SimpleNamespace(copia_local=lambda v, x: None))
    f = RP.Reproductor.adelantar_actual
    assert f(r) is True and pedidos == ["v1"]
    r.estado = "sonando"
    assert f(r) is False
    r.estado, r.coleccion.copia_local = "parado", lambda v, x: ("c.m4a",)
    assert f(r) is False                              # está descargada: no hace falta
    r.actual = None
    assert f(r) is False and pedidos == ["v1"]
