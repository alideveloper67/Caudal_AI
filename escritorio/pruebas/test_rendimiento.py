# -*- coding: utf-8 -*-
"""Rendimiento del escritorio: frenos de avisos, cachés con tope, páginas que no se rehacen
ocultas, conteos en SQL, conexiones que se sueltan solas y la sincronización sin bloquear la base.
Qt offscreen, sin red ni audio, datos en una carpeta temporal."""

import json
import os
import sqlite3
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.coleccion import Coleccion  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def plantilla(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("plantilla") / "h.db"
    Coleccion(ruta).con.close()
    return ruta


@pytest.fixture
def col(tmp_path, plantilla):
    import shutil
    shutil.copy(str(plantilla), str(tmp_path / "h.db"))
    return Coleccion(tmp_path / "h.db")


def pista(i, **extra):
    return dict({"tipo": "pista", "clave": f"yt:{i:011d}", "video_id": f"{i:011d}",
                 "titulo": f"Canción {i}", "artista": f"Artista {i % 3}",
                 "artistas": [{"nombre": f"Artista {i % 3}", "id": f"UC{i % 3}"}],
                 "duracion": 200, "miniatura": ""}, **extra)


# ---------------------------------------------------------------- freno de la posición

def _reproductor_minimo():
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    QObject.__init__(r)
    r._posicion = 0.0
    r.velocidad = 1.0
    return r


def test_la_posicion_llega_a_la_interfaz_a_5_por_segundo_como_mucho(app, monkeypatch):
    from descargador import reproduccion as R
    r = _reproductor_minimo()
    avisos = []
    r.posicion_cambio.connect(avisos.append)
    reloj = [100.0]
    monkeypatch.setattr(R.time, "monotonic", lambda: reloj[0])
    # mpv avisa 50 veces por segundo durante 2 s
    for i in range(100):
        reloj[0] = 100.0 + i * 0.02
        r._posicion = i * 0.02
        r._emitir_posicion()
    assert 8 <= len(avisos) <= 11              # ~5 por segundo (antes: 100)
    assert avisos == sorted(avisos)


def test_un_salto_o_forzar_pasan_siempre(app, monkeypatch):
    from descargador import reproduccion as R
    r = _reproductor_minimo()
    avisos = []
    r.posicion_cambio.connect(avisos.append)
    reloj = [50.0]
    monkeypatch.setattr(R.time, "monotonic", lambda: reloj[0])
    r._posicion = 10.0
    r._emitir_posicion()
    reloj[0] += 0.02
    r._posicion = 90.0                          # buscar(): salto de 80 s
    r._emitir_posicion()
    reloj[0] += 0.02
    r._posicion = 90.02
    r._emitir_posicion(forzar=True)
    assert avisos == [10.0, 90.0, 90.02]


def test_al_pausar_se_avisa_la_posicion_exacta(app, monkeypatch):
    from descargador import reproduccion as R
    r = _reproductor_minimo()
    r.estado = "sonando"
    r._guardar_sesion_pronto = lambda: None
    avisos = []
    r.posicion_cambio.connect(avisos.append)
    reloj = [10.0]
    monkeypatch.setattr(R.time, "monotonic", lambda: reloj[0])
    r._posicion = 5.0
    r._emitir_posicion()
    reloj[0] += 0.05
    r._posicion = 5.05
    r._emitir_posicion()                        # frenado
    r._fijar_estado("pausa")
    assert avisos[-1] == 5.05


def test_el_deslizador_solo_repinta_si_cambia_un_pixel(app):
    from descargador.ui.componentes import Deslizador
    d = Deslizador()
    d.resize(312, 16)
    pintadas = []
    d.update = lambda *a: pintadas.append(1)
    d.set_valor(0.5)
    n = len(pintadas)
    d.set_valor(0.5 + 1e-5)                     # menos de medio píxel: nada
    assert len(pintadas) == n
    d.set_valor(0.6)
    assert len(pintadas) == n + 1


# ---------------------------------------------------------------- freno del progreso

def test_el_progreso_de_descarga_avisa_4_veces_por_segundo_como_mucho(monkeypatch):
    from descargador import motor as M

    class Trabajo:                              # solo el freno, sin crear la descarga
        INTERVALO_PROGRESO = M.TrabajoDescarga.INTERVALO_PROGRESO
        _toca_avisar = M.TrabajoDescarga._toca_avisar
    trabajo = Trabajo()
    reloj = [0.0]
    monkeypatch.setattr(M.time, "monotonic", lambda: 1000.0 + reloj[0])
    pasaron = 0
    for i in range(200):                       # yt-dlp: un aviso por bloque, 200 en 2 s
        reloj[0] = i * 0.01
        pasaron += trabajo._toca_avisar(False)
    assert 7 <= pasaron <= 9
    assert trabajo._toca_avisar(True)           # el 100 % pasa siempre


# ---------------------------------------------------------------- mascotas

def test_el_catalogo_de_mascotas_se_lee_una_vez(tmp_path, monkeypatch):
    from descargador import mascotas as M
    (tmp_path / "catalogo.json").write_text(json.dumps(
        [{"clave": "a", "nombre": "A", "ancho": 10, "alto": 10}]), encoding="utf-8")
    monkeypatch.setattr(M, "ARTE", tmp_path)
    M.olvidar_catalogo()
    lecturas = []
    original = type(tmp_path).read_text

    def contar(self, *a, **k):
        lecturas.append(str(self))
        return original(self, *a, **k)
    monkeypatch.setattr(type(tmp_path), "read_text", contar)
    for _ in range(500):
        assert M.por_clave("a")["nombre"] == "A"
        M.catalogo()
    assert len(lecturas) == 1
    # si el archivo cambia (otra fecha), se vuelve a leer
    (tmp_path / "catalogo.json").write_text(json.dumps(
        [{"clave": "a", "nombre": "Otra", "ancho": 10, "alto": 10},
         {"clave": "b", "nombre": "B", "ancho": 10, "alto": 10}]), encoding="utf-8")
    t = time.time() + 5
    os.utime(tmp_path / "catalogo.json", (t, t))
    monkeypatch.setattr(M, "MIRAR_CADA", 0.0)
    assert M.por_clave("a")["nombre"] == "Otra" and M.por_clave("b")
    M.olvidar_catalogo()


def test_la_mascota_activa_se_recuerda_pero_sigue_al_permiso(tmp_path, monkeypatch):
    from descargador import mascotas as M
    (tmp_path / "catalogo.json").write_text(json.dumps(
        [{"clave": "a", "nombre": "A", "ancho": 10, "alto": 10}]), encoding="utf-8")
    monkeypatch.setattr(M, "ARTE", tmp_path)
    M.olvidar_catalogo()

    class Fondo(QObject):
        permiso_cambiado = Signal(bool)

        def __init__(self):
            super().__init__()
            self.puede = True

    class Ctx:
        fondo = Fondo()
        cuenta = {"id": "1", "usuario": "ana"}
    g = M.GestorMascota.__new__(M.GestorMascota)
    QObject.__init__(g)
    g.ctx, g.clave = Ctx(), "a"
    assert g.datos()["nombre"] == "A"
    Ctx.fondo.puede = False
    assert g.datos() is None                    # la caché no se salta el permiso
    Ctx.fondo.puede = True
    assert g.datos()["nombre"] == "A"
    M.olvidar_catalogo()


# ---------------------------------------------------------------- caché con tope

def test_diccionario_limitado_suelta_lo_menos_usado():
    from descargador.memoria import DiccionarioLimitado
    d = DiccionarioLimitado(3)
    for k in "abc":
        d[k] = k.upper()
    assert d["a"] == "A"                        # usar «a» la hace reciente
    d["d"] = "D"
    assert list(d) == ["c", "a", "d"] and "b" not in d
    assert d.get("zz") is None and d.get("c") == "C"


def test_las_caches_de_letras_traducciones_y_catalogo_tienen_tope():
    from descargador import traductor
    from descargador.ui import letra_viva
    from descargador.ui.paginas import comun
    for i in range(1000):
        letra_viva.CACHE_LETRAS[f"k{i}"] = {}
        traductor._CACHE[f"k{i}"] = []
        comun.guardar_cache(("x", i), i)
    assert len(letra_viva.CACHE_LETRAS) <= 300 and len(traductor._CACHE) <= 300
    assert len(comun._CACHE) <= comun.TOPE_CACHE
    assert comun.cache(("x", 999)) == 999
    letra_viva.CACHE_LETRAS.clear()
    traductor._CACHE.clear()
    comun._CACHE.clear()


def test_la_cache_del_catalogo_tira_lo_caducado():
    from descargador.ui.paginas import comun
    comun._CACHE.clear()
    for i in range(comun.TOPE_CACHE // 2):
        comun._CACHE[("viejo", i)] = (time.time() - 2 * comun.CADUCA_SEG, i)
    comun.guardar_cache("nuevo", 1)
    assert len(comun._CACHE) == 1 and comun.cache("nuevo") == 1
    comun._CACHE.clear()


# ---------------------------------------------------------------- base: conteos y límites

def test_conteo_de_descargas_en_sql(col):
    for i in range(7):
        col.con.execute("INSERT INTO descargas (url, titulo, archivo, estado, fecha, es_audio) "
                        "VALUES (?,?,?,?,?,?)", (f"u{i}", "t", f"C:/x/{i}", "completada", i, i % 2))
    col.con.execute("INSERT INTO descargas (url, archivo, estado, es_audio) VALUES ('f','', 'error', 1)")
    col.con.commit()
    assert col.contar_descargadas() == {True: 3, False: 4}


def test_me_gusta_con_limite_lee_solo_los_primeros(col):
    for i in range(30):
        col.alternar_me_gusta(pista(i))
    todos = col.lista_me_gusta()
    assert [p["clave"] for p in col.lista_me_gusta(limite=5)] == [p["clave"] for p in todos[:5]]
    assert len(col.lista_me_gusta("Canción 2", limite=5)) == len(col.lista_me_gusta("Canción 2"))


def test_copia_de_lectura_con_su_propia_conexion(col):
    col.alternar_me_gusta(pista(1))
    with col.copia_de_lectura() as c:
        assert c.con is not col.con
        assert c.total_me_gusta() == 1 and c.sincronizador is None
    with pytest.raises(sqlite3.ProgrammingError):
        c.con.execute("SELECT 1")               # quedó cerrada


def test_maquina_del_tiempo_se_calcula_una_vez_al_dia(col, monkeypatch):
    from datetime import datetime, timedelta
    from descargador import mixes, recomendador as rc
    hoy = datetime(2026, 11, 16, 12, 0)
    for i in range(12):
        col.registrar_escucha(pista(i))
    col.con.execute("UPDATE reproducciones SET fecha = ?", ((hoy - timedelta(days=40)).timestamp(),))
    col.con.commit()
    rc._CACHE_TIEMPO.clear()
    lecturas = []
    leer = mixes.leer_historial
    monkeypatch.setattr(mixes, "leer_historial", lambda *a, **k: lecturas.append(1) or leer(*a, **k))
    primera = rc.maquina_del_tiempo_de(col, ahora=hoy)
    assert primera and rc.maquina_del_tiempo_en_memoria(col, ahora=hoy) == primera
    assert rc.maquina_del_tiempo_de(col, ahora=hoy) == primera
    assert len(lecturas) == 1
    rc.maquina_del_tiempo_de(col, ahora=hoy + timedelta(days=1))     # otro día: se rehace
    assert len(lecturas) == 2
    rc._CACHE_TIEMPO.clear()


# ---------------------------------------------------------------- señales que se sueltan solas

class _RepFalso(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = None
        self.estado = "parado"
        self._posicion = 0.0


def test_las_filas_destruidas_no_fallan_al_cambiar_de_cancion(app):
    from shiboken6 import delete
    from descargador.ui.componentes import FilaCompacta

    class Ctx:
        reproductor = _RepFalso()
    fallos = []
    antes = sys.excepthook
    sys.excepthook = lambda *a: fallos.append(a)
    try:
        filas = [FilaCompacta(Ctx, pista(i), lambda p: None) for i in range(20)]
        for f in filas:
            delete(f)
        app.processEvents()
        Ctx.reproductor.pista_cambio.emit(pista(99))
        app.processEvents()
    finally:
        sys.excepthook = antes
    assert not fallos                           # antes: 20 RuntimeError «already deleted»


def test_el_mismo_fallo_en_rafaga_se_escribe_una_vez(tmp_path):
    import threading
    from descargador import registro_fallos as R
    antes_hook, antes_hilo = sys.excepthook, threading.excepthook
    try:
        R.activar(tmp_path)
        R._ultimo.update(clave=None, cuando=0.0, repetido=0)
        for _ in range(113):
            R.anotar("Error en la interfaz", "RuntimeError: already deleted")
        R.anotar("Otro", "distinto")
        texto = (tmp_path / "fallos.log").read_text(encoding="utf-8")
        assert texto.count("already deleted") == 1
        assert "se repitió 112 veces" in texto and "distinto" in texto
    finally:
        sys.excepthook, threading.excepthook = antes_hook, antes_hilo
        R._ultimo.update(clave=None, cuando=0.0, repetido=0)


# ---------------------------------------------------------------- páginas ocultas

class _CtxPagina(QObject):
    me_gusta_cambio = Signal(str, bool)
    listas_cambio = Signal()
    descargas_cambio = Signal()
    guardados_cambio = Signal()
    aviso = Signal(str)

    def __init__(self, col):
        super().__init__()
        from unittest.mock import MagicMock
        self.coleccion = col
        self.ajustes = {"carpeta": ""}
        self.reproductor = MagicMock()
        self.ventana = None

    def navegar(self, d):
        pass


def test_una_pagina_oculta_no_se_rehace_hasta_volver_a_verse(app, col):
    from descargador.ui.paginas.coleccion import PaginaColeccion
    ctx = _CtxPagina(col)
    col.alternar_me_gusta(pista(1))
    from PySide6.QtWidgets import QStackedWidget, QWidget
    pila = QStackedWidget()                     # como en la ventana: otra página encima
    pag = PaginaColeccion(ctx, {"pagina": "me_gusta"})
    otra = QWidget()
    pila.addWidget(pag)
    pila.addWidget(otra)
    pila.setCurrentWidget(otra)
    pila.show()
    app.processEvents()
    rehechas = []
    original = pag._pintar
    pag._pintar = lambda d: (rehechas.append(1), original(d))
    for i in range(2, 12):                      # diez «me gusta» con la página escondida
        col.alternar_me_gusta(pista(i))
        ctx.me_gusta_cambio.emit(f"yt:{i}", True)
    assert not rehechas and pag._pendiente_recargar
    pila.setCurrentWidget(pag)
    for _ in range(5):
        app.processEvents()
    assert len(rehechas) == 1 and not pag._pendiente_recargar
    assert len(pag.pistas) == 11
    # a la vista, cada cambio se ve al momento (como siempre)
    col.alternar_me_gusta(pista(20))
    ctx.me_gusta_cambio.emit("yt:20", True)
    assert len(rehechas) == 2
    pila.close()


# ---------------------------------------------------------------- sincronización

class _NubeVigilada:
    """Nube de mentira que mira, en cada petición, si la base está bloqueada esperándola."""

    def __init__(self):
        self.user_id = "u1"
        self.con = None
        self.bloqueada_en = []

    def pedir(self, metodo, ruta, json=None, cabeceras=None):
        if self.con is not None and self.con.in_transaction:
            self.bloqueada_en.append(ruta)
        if ruta.startswith("me_gusta"):
            return [{"clave": "yt:00000000001", "datos": pista(1), "fecha": "2026-11-16T10:00:00+00:00"}]
        if ruta.startswith("listas"):
            return [{"id": "L1", "nombre": "Nube", "descripcion": "", "fijada": False,
                     "creada": "2026-11-01T10:00:00+00:00", "publica": False, "en_perfil": False}]
        if ruta.startswith("lista_items"):
            return [{"lista_id": "L1", "clave": "yt:00000000002", "datos": pista(2), "orden": 1}]
        if ruta.startswith("escuchas"):
            return [{"id": 7, "clave": "yt:00000000003", "datos": pista(3), "contexto": None,
                     "fecha": "2026-11-16T09:00:00+00:00"}]
        return []


def test_traer_no_espera_a_la_red_con_la_base_bloqueada(col):
    from descargador.sincronizacion import Sincronizador
    # algo local que borrar: así la escritura empieza pronto (antes, con la base ya bloqueada,
    # se pedían las listas, sus canciones, los guardados y las escuchas)
    col.con.execute("INSERT INTO me_gusta (clave, fecha) VALUES ('yt:viejo', 1)")
    col.con.commit()
    nube = _NubeVigilada()
    s = Sincronizador(col, {"sesion": nube})
    con = sqlite3.connect(str(col.archivo))
    con.row_factory = sqlite3.Row
    nube.con = con
    try:
        assert s._traer(con) is True
        assert not con.in_transaction            # confirmado al terminar
    finally:
        con.close()
    assert nube.bloqueada_en == []
    assert col.me_gusta("yt:00000000001") and not col.me_gusta("yt:viejo")
    assert [l["nombre"] for l in col.listas()] == ["Nube"]
    assert col.con.execute("SELECT COUNT(*) FROM reproducciones WHERE nube_id = 7").fetchone()[0] == 1


def test_al_volver_a_la_ventana_sincroniza_si_hace_mas_de_un_minuto(app, col):
    from descargador import sincronizacion as SM
    s = SM.Sincronizador(col, {"sesion": _NubeVigilada()})
    llamadas = []
    s.ya = lambda completo=True: llamadas.append(completo)
    s._reloj.start()
    s.completa()
    s.al_volver()                               # recién hecho: nada
    assert llamadas == [True]
    s._ultima_completa -= SM.AL_VOLVER + 1
    s.al_volver()
    assert llamadas == [True, True]
    assert SM.CADA == 10 * 60 * 1000
    s._reloj.stop()


# ---------------------------------------------------------------- sesión del reproductor

def test_guardar_la_sesion_de_rutina_no_usa_la_conexion_de_la_interfaz(app, col):
    from descargador.reproduccion import Reproductor
    r = Reproductor.__new__(Reproductor)
    QObject.__init__(r)
    r.coleccion = col
    r.secuencia = [pista(1), pista(2)]
    r.pos, r.proximas, r.contexto, r._posicion, r.modo = 1, [], None, 42.0, "audio"
    r.actual = r.secuencia[1]

    class ConVigilada:
        def __getattr__(self, nombre):
            raise AssertionError("la interfaz no debe escribir la sesión de rutina")
    principal, col.con = col.con, ConVigilada()
    try:
        r._guardar_sesion_pronto()
        fin = time.time() + 10
        estado = r._estado_sesion()
        while estado.escrita < estado.gen and time.time() < fin:
            time.sleep(0.02)
    finally:
        col.con = principal
    assert col.estado("sesion")["posicion"] == 42.0
    r._posicion = 50.0
    r.guardar_sesion()                          # la de cerrar: al momento
    assert col.estado("sesion")["posicion"] == 50.0


# ---------------------------------------------------------------- portadas

def _png(w, h):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor("#3366cc"))
    arreglo = QByteArray()
    b = QBuffer(arreglo)
    b.open(QIODevice.WriteOnly)
    img.save(b, "PNG")
    b.close()
    return bytes(arreglo)


def test_las_portadas_enormes_se_decodifican_reducidas_y_en_cualquier_hilo(app):
    import threading
    from descargador.ui import imagenes as I
    grande = I.decodificar(_png(3000, 2000))
    assert (grande.width(), grande.height()) == (1280, 853)
    chica = I.decodificar(_png(544, 544))
    assert (chica.width(), chica.height()) == (544, 544)        # lo normal no se toca
    assert I.decodificar(b"").isNull() and I.decodificar(b"no es imagen").isNull()
    datos = _png(1600, 1600)
    malos = []

    def trabajar():
        for _ in range(15):
            img = I.decodificar(datos)
            rec = I.formar_imagen(img, 96, 96, "redonda", 0)
            if img.width() != 1280 or rec.width() != 96:
                malos.append(1)
    hilos = [threading.Thread(target=trabajar) for _ in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert not malos


def test_el_recorte_sale_nitido_para_la_densidad_de_la_pantalla(app):
    from descargador.ui import imagenes as I
    img = I.decodificar(_png(544, 544))
    pm = I.formar(img, 48, 48, "cuadrada", 4)
    escala = app.devicePixelRatio()
    assert pm.width() == int(48 * escala) and pm.devicePixelRatio() == escala
    assert I.TOPE_ORIGINALES == 64 * 1024 * 1024 and I.TOPE_RECORTES == 64 * 1024 * 1024


# ---------------------------------------------------------------- Inicio en la ventana de verdad

def _ventana_real():
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None            # sin motores de audio reales
    from descargador.coleccion import Coleccion as Col
    from descargador.config import Ajustes
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import estilos
    from descargador.ui.contexto import Contexto
    from descargador.ui.ventana import Ventana
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.warning = staticmethod(lambda *a, **k: 0)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
    Ventana.buscar_version = lambda self, callado=False: None
    Ventana._avisar_novedades = lambda self: None
    ajustes = Ajustes()
    estilos.aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
    historial, coleccion = Historial(), Col()
    ctx = Contexto(ajustes, historial, coleccion, Gestor(ajustes, historial),
                   Reproductor(ajustes, coleccion))
    ctx.estudio = None
    return ctx, Ventana(ctx)


def _esperar(app, cond, seg=10):
    fin = time.time() + seg
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.01)
    return cond()


def test_pulsar_inicio_estando_en_inicio_solo_pone_al_dia_lo_reciente(app):
    from datetime import datetime, timedelta
    from descargador import recomendador as rc
    from descargador.ui.paginas import comun
    comun.guardar_cache("inicio", {"secciones": []})   # sin red
    col = Coleccion()                                   # la misma base que usará la ventana
    hace_un_mes = (datetime.now() - timedelta(days=31)).timestamp()
    for i in range(8):
        col.registrar_escucha(pista(i))
    col.con.execute("UPDATE reproducciones SET fecha = ?", (hace_un_mes,))
    col.con.commit()
    col.con.close()
    rc._CACHE_TIEMPO.clear()
    ctx, v = _ventana_real()
    col = ctx.coleccion
    v.resize(1200, 800)
    v.show()
    v.navegar({"pagina": "inicio"})
    pag = v.historia[v.indice][1]
    # la máquina del tiempo se calcula en segundo plano y aparece en su sitio
    assert _esperar(app, lambda: pag.caja_tiempo.isVisible())
    caja_tiempo = pag.caja_tiempo
    col.registrar_escucha(pista(50, titulo="Recién escuchada"))
    v.navegar({"pagina": "inicio"})
    assert v.historia[v.indice][1] is pag          # la misma página, no una nueva
    assert pag.caja_tiempo is caja_tiempo          # la máquina del tiempo no se rehízo
    from PySide6.QtCore import QEvent
    from descargador.ui.componentes import Carrusel, Tarjeta
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    carruseles = pag.caja_recientes.findChildren(Carrusel)
    assert len(carruseles) == 1
    titulos = [t.el.get("titulo") for t in carruseles[0].findChildren(Tarjeta)]
    assert titulos and titulos[0] == "Recién escuchada"
    v.hide()
