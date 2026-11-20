# -*- coding: utf-8 -*-
"""Enviar la música a Chromecast desde la PC: el control con una tele de mentira
y el servidor de la PC (archivos con Range y repetidor de streams)."""

import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import cast  # noqa: E402

APP = QApplication.instance() or QApplication([])

SALA = cast.Dispositivo("tv1", "Tele de la sala", "Chromecast")
COCINA = cast.Dispositivo("al1", "Cocina", "Google Nest Audio")


class TeleFalsa:
    """Contesta al momento, en el mismo hilo."""

    def __init__(self):
        self.al_dispositivos = self.al_sesion = self.al_medio = self.al_volumen = None
        self.ordenes = []
        self.cargados = []
        self.buscando = False
        self.aceptar = True
        self.disponible = True

    def buscar(self):
        self.buscando = True

    def dejar_de_buscar(self):
        self.buscando = False

    def conectar(self, d):
        self.ordenes.append(f"conectar {d.nombre}")
        if not self.aceptar:
            return False
        self.al_sesion(d)
        self.al_volumen(0.4)
        return True

    def desconectar(self):
        self.ordenes.append("desconectar")
        self.al_sesion(None)

    def cargar(self, medio, desde=0.0, sonar=True):
        self.cargados.append((medio, desde, sonar))
        self.ordenes.append("cargar")

    def sonar(self):
        self.ordenes.append("sonar")

    def pausar(self):
        self.ordenes.append("pausar")

    def ir_a(self, s):
        self.ordenes.append(f"ir_a {int(s)}")

    def fijar_volumen(self, v):
        self.ordenes.append(f"volumen {v}")

    def parar(self):
        self.ordenes.append("parar")

    def cerrar(self):
        pass

    def dice(self, estado, posicion=None, duracion=None, url=None):
        url = url or (self.cargados[-1][0]["url"] if self.cargados else None)
        self.al_medio(estado, duracion, url, posicion)


class ServidorFalso:
    def __init__(self):
        self.archivos, self.remotos, self.sin_red = [], [], False

    def publicar_archivo(self, ruta, tipo=None):
        if self.sin_red:
            return None
        self.archivos.append(ruta)
        return f"http://192.168.1.20:5000/a/{len(self.archivos)}"

    def publicar_remoto(self, url, tipo=None, cabeceras=None):
        self.remotos.append(url)
        return f"http://192.168.1.20:5000/p/{len(self.remotos)}"

    def cerrar(self):
        pass


class ReproFalso:
    def __init__(self):
        self.actual = None
        self.fuente = None
        self.estado = "parado"
        self.pos = 0.0
        self.dur = 180.0
        self.callado = 0
        self.vueltas = []
        self.avisos = []
        self.siguientes = 0
        self.cola = []
        self.cast = None

    def anfitrion(self):
        def siguiente():
            self.siguientes += 1
            if self.cola:
                self.actual = self.cola.pop(0)
                self.fuente = {"url": f"https://rr.googlevideo.com/v?mime=audio%2Fwebm&id={self.actual['video_id']}"}
                if self.cast.activo:
                    self.cast.enviar(self.actual, self.fuente)

        def volver(seg, sonar):
            self.vueltas.append((seg, sonar))

        return cast.AnfitrionCast(
            pista=lambda: self.actual, fuente=lambda: self.fuente,
            posicion=lambda: self.pos, poner_posicion=lambda s: setattr(self, "pos", s),
            duracion=lambda: self.dur, poner_duracion=lambda s: setattr(self, "dur", s),
            sonando_local=lambda: self.estado in ("sonando", "cargando"),
            fijar_estado=lambda e: setattr(self, "estado", e),
            callar_local=lambda: setattr(self, "callado", self.callado + 1),
            volver_local=volver, siguiente=siguiente, aviso=self.avisos.append)


def cancion(i):
    return {"video_id": i, "titulo": f"Canción {i}", "artista": "Artista", "album": {"nombre": "Disco"},
            "miniatura": "https://lh3.googleusercontent.com/x=w120-h120-l90-rj"}


@pytest.fixture
def todo():
    tele, srv, r = TeleFalsa(), ServidorFalso(), ReproFalso()
    c = cast.ControlCast(r.anfitrion(), puente=tele, servidor=srv)
    c.despues = lambda _ms, fn: fn()
    r.cast = c
    yield tele, srv, r, c
    c.cerrar()


def sonando(r, i="a", url=None):
    r.actual = cancion(i)
    r.fuente = {"url": url or "https://rr.googlevideo.com/v?mime=audio%2Fwebm&ip=1.2.3.4",
                "cabeceras": {"User-Agent": "x"}}
    r.estado = "sonando"


def test_lista_lo_que_encuentra(todo):
    tele, _s, _r, c = todo
    assert c.soportado
    c.buscar_dispositivos()
    assert tele.buscando
    tele.al_dispositivos([SALA, COCINA])
    assert [d.nombre for d in c.dispositivos] == ["Tele de la sala", "Cocina"]
    assert COCINA.es_altavoz and not SALA.es_altavoz
    c.dejar_de_buscar()
    assert not tele.buscando


def test_conectar_pasa_lo_que_suena_al_mismo_punto(todo):
    tele, _s, r, c = todo
    sonando(r)
    r.pos = 42.0
    c.conectar(SALA)
    assert c.activo and c.dispositivo == SALA
    assert c.volumen == 0.4
    assert r.callado == 1
    medio, desde, sonar = tele.cargados[0]
    assert medio["url"].startswith("https://rr.googlevideo.com/")
    assert medio["tipo"] == "audio/webm"
    assert (medio["titulo"], medio["artista"], medio["album"]) == ("Canción a", "Artista", "Disco")
    assert "=w720-h720" in medio["caratula"]
    assert desde == 42.0 and sonar
    assert r.estado == "cargando"
    tele.dice(cast.SONANDO, posicion=42.0)
    assert r.estado == "sonando"


def test_pausar_seguir_barra_y_volumen(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO, posicion=10)
    c.pausar()
    assert tele.ordenes[-1] == "pausar" and r.estado == "pausa"
    tele.dice(cast.PAUSA, posicion=10)
    c.reanudar()
    assert tele.ordenes[-1] == "sonar" and r.estado == "sonando"
    c.ir_a(95)
    assert tele.ordenes[-1] == "ir_a 95" and r.pos == 95
    c.fijar_volumen(0.8)
    assert tele.ordenes[-1] == "volumen 0.8"
    c.alternar()
    assert tele.ordenes[-1] == "pausar"


def test_al_terminar_pasa_a_la_siguiente(todo):
    tele, _s, r, c = todo
    sonando(r)
    r.cola = [cancion("b")]
    c.conectar(SALA)
    tele.dice(cast.SONANDO)
    tele.dice(cast.TERMINADO)
    assert r.siguientes == 1
    assert tele.cargados[-1][0]["titulo"] == "Canción b"
    assert tele.cargados[-1][1] == 0


def test_terminado_de_lo_anterior_no_salta(todo):
    tele, _s, r, c = todo
    sonando(r, url="https://rr.googlevideo.com/v?mime=audio%2Fwebm&a")
    c.conectar(SALA)
    tele.dice(cast.SONANDO)
    viejo = tele.cargados[-1][0]["url"]
    sonando(r, "b", url="https://rr.googlevideo.com/v?mime=audio%2Fwebm&b")
    c.enviar(r.actual, r.fuente)
    tele.dice(cast.TERMINADO, url=viejo)
    tele.dice(cast.TERMINADO)  # la nueva aún no empezó
    assert r.siguientes == 0


def test_si_la_tele_no_abre_el_enlace_va_por_la_pc(todo):
    tele, srv, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.ERROR)
    assert srv.remotos == ["https://rr.googlevideo.com/v?mime=audio%2Fwebm&ip=1.2.3.4"]
    assert tele.cargados[-1][0]["url"].startswith("http://192.168.1.20:5000/p/")
    tele.dice(cast.ERROR)
    assert "no pudo reproducir" in r.avisos[-1]
    assert r.siguientes == 1


def test_descargas_las_sirve_la_pc(todo):
    tele, srv, r, c = todo
    r.actual = {**cancion("a"), "miniatura": r"C:\caratulas\a.jpg"}
    r.fuente = {"archivo": r"C:\Musica\Canción a.m4a", "local": True}
    r.estado = "sonando"
    c.conectar(SALA)
    assert srv.archivos == [r"C:\Musica\Canción a.m4a", r"C:\caratulas\a.jpg"]
    m = tele.cargados[0][0]
    assert m["url"] == "http://192.168.1.20:5000/a/1" and m["tipo"] == "audio/mp4"
    assert m["caratula"] == "http://192.168.1.20:5000/a/2"


def test_descargas_sin_red_se_explica(todo):
    tele, srv, r, c = todo
    srv.sin_red = True
    r.actual = cancion("a")
    r.fuente = {"archivo": r"C:\Musica\a.mp3"}
    r.estado = "sonando"
    c.conectar(SALA)
    assert not tele.cargados
    assert "misma red" in r.avisos[-1]
    assert r.estado == "parado"


def test_desconectar_vuelve_a_la_pc_en_el_mismo_punto(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO, posicion=77)
    c.desconectar()
    assert not c.activo and c.dispositivo is None
    assert "desconectar" in tele.ordenes
    seg, sonar = r.vueltas[0]
    assert 77 <= seg < 78 and sonar is True


def test_desconectar_en_pausa_vuelve_en_pausa(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO, posicion=30)
    c.pausar()
    c.desconectar()
    seg, sonar = r.vueltas[0]
    assert int(seg) == 30 and sonar is False


def test_se_corta_la_red_y_sigue_en_la_pc(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO, posicion=50)
    tele.al_sesion(None)
    assert not c.activo
    assert int(r.vueltas[0][0]) == 50
    assert "Sigue sonando en la PC" in r.avisos[-1]


def test_si_no_acepta_la_conexion_se_dice(todo):
    tele, _s, r, c = todo
    tele.aceptar = False
    c.conectar(SALA)
    assert c.conexion == cast.DESCONECTADO
    assert "misma red" in r.avisos[-1]


def test_misma_cancion_no_corta(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO, posicion=12)
    c.enviar(r.actual, {"url": "https://rr.googlevideo.com/video", "audio_url": r.fuente["url"]}, 12)
    assert len(tele.cargados) == 1


def test_parar_y_seguir_vuelve_a_mandar(todo):
    tele, _s, r, c = todo
    sonando(r)
    c.conectar(SALA)
    tele.dice(cast.SONANDO)
    c.parar()
    assert tele.ordenes[-1] == "parar"
    c.reanudar()
    assert len(tele.cargados) == 2


def test_tipos_y_caratulas():
    assert cast.tipo_de_fuente({"url": "https://a/v?mime=audio%2Fmp4"}) == "audio/mp4"
    assert cast.tipo_de_fuente({"archivo": "x.MP3"}) == "audio/mpeg"
    assert cast.tipo_de_fuente({"archivo": "x.flac"}) == "audio/flac"
    assert cast.tipo_de_fuente({"url": "https://a/v", "info": {"ext": "webm"}}) == "audio/webm"
    assert cast.caratula_grande("https://i.ytimg.com/vi/a/mqdefault.jpg") == "https://i.ytimg.com/vi/a/hqdefault.jpg"
    assert cast.direccion_de({"url": "https://v", "audio_url": "https://a"}) == "https://a"
    assert cast.direccion_de({"url": "yt:abc"}) is None


def test_rango_pedido():
    rp = cast.rango_pedido
    assert rp(None, 100) == (0, 99)
    assert rp("bytes=10-20", 100) == (10, 20)
    assert rp("bytes=90-500", 100) == (90, 99)
    assert rp("bytes=-10", 100) == (90, 99)
    assert rp("bytes=100-", 100) is None
    assert rp("bytes=20-10", 100) is None
    assert rp("bytes=-", 100) is None


def test_es_privada():
    assert cast.es_privada("192.168.0.4") and cast.es_privada("10.1.2.3")
    assert not cast.es_privada("8.8.8.8") and not cast.es_privada("127.0.0.1")


# ------------------------------------------------------------------ servidor de verdad

DATOS = bytes(i % 251 for i in range(10000))


def pedir(url, rango=None, metodo="GET"):
    req = urllib.request.Request(url, method=metodo, headers={"Range": rango} if rango else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


@pytest.fixture
def servidor():
    s = cast.ServidorCast(ip="127.0.0.1")
    carpeta = tempfile.mkdtemp(prefix="cast_")
    ruta = os.path.join(carpeta, "canción.m4a")
    with open(ruta, "wb") as f:
        f.write(DATOS)
    yield s, ruta
    s.cerrar()


def test_servidor_archivo_entero_y_a_trozos(servidor):
    s, ruta = servidor
    url = s.publicar_archivo(ruta)
    assert url.startswith("http://127.0.0.1:") and url.endswith(".m4a")
    st, cab, cuerpo = pedir(url)
    assert st == 200 and cuerpo == DATOS
    assert cab["Content-Type"] == "audio/mp4" and cab["Accept-Ranges"] == "bytes"
    st, cab, cuerpo = pedir(url, "bytes=100-199")
    assert st == 206 and cab["Content-Range"] == "bytes 100-199/10000" and cuerpo == DATOS[100:200]
    st, _c, cuerpo = pedir(url, "bytes=9000-")
    assert st == 206 and cuerpo == DATOS[9000:]
    st, _c, cuerpo = pedir(url, "bytes=-500")
    assert cuerpo == DATOS[-500:]
    st, cab, _ = pedir(url, "bytes=20000-")
    assert st == 416 and cab["Content-Range"] == "bytes */10000"
    st, cab, cuerpo = pedir(url, metodo="HEAD")
    assert st == 200 and cab["Content-Length"] == "10000" and cuerpo == b""


def test_servidor_no_deja_leer_otra_cosa(servidor):
    s, ruta = servidor
    url = s.publicar_archivo(ruta)
    base = url[:url.index("/a/")]
    assert pedir(base + "/a/1234")[0] == 404
    assert pedir(base + "/a/..%2F..%2Fwindows")[0] == 404
    assert pedir(base + "/etc/passwd")[0] == 404
    assert s.publicar_archivo(ruta + ".no") is None
    assert s.publicar_archivo(ruta) == url


def test_servidor_repite_stream_con_range(servidor):
    s, _ = servidor

    class Origen(BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_GET(self):
            a, b = cast.rango_pedido(self.headers.get("Range"), len(DATOS))
            self.send_response(206 if self.headers.get("Range") else 200)
            self.send_header("Content-Type", "audio/webm")
            self.send_header("Content-Range", f"bytes {a}-{b}/{len(DATOS)}")
            self.send_header("Content-Length", str(b - a + 1))
            self.send_header("X-Agente", self.headers.get("User-Agent", ""))
            self.end_headers()
            self.wfile.write(DATOS[a:b + 1])

    origen = ThreadingHTTPServer(("127.0.0.1", 0), Origen)
    threading.Thread(target=origen.serve_forever, daemon=True).start()
    try:
        url = s.publicar_remoto(f"http://127.0.0.1:{origen.server_address[1]}/videoplayback?x=1",
                                cabeceras={"User-Agent": "CaudalPrueba"})
        st, cab, cuerpo = pedir(url, "bytes=10-19")
        assert st == 206 and cuerpo == DATOS[10:20]
        assert cab["Content-Range"] == "bytes 10-19/10000"
        assert cab["Content-Type"] == "audio/webm"
    finally:
        origen.shutdown()
        origen.server_close()


def test_boton_oculto_sin_cast_y_hoja_explica_la_red(todo):
    from descargador.ui import cast_boton
    tele, _s, _r, c = todo
    b = cast_boton.BotonCast(c)
    b.show()
    assert b.isVisible()
    tele.disponible = False
    c.cambio.emit()
    assert not b.isVisible()
    tele.disponible = True
    c.cambio.emit()
    hoja = cast_boton.HojaCast(c)
    textos = lambda: " ".join(w.text() for w in hoja.findChildren(cast_boton.QLabel))  # noqa: E731
    assert "Buscando" in textos()
    hoja._ya_esperado()
    assert "misma red" in textos()
    tele.al_dispositivos([SALA])
    botones = [w for w in hoja.findChildren(cast_boton.QPushButton) if w.objectName() == "aparato"]
    assert botones and "Tele de la sala" in botones[-1].text()
    hoja.close()
    assert not tele.buscando
    time.sleep(0)
