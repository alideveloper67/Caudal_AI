# -*- coding: utf-8 -*-
"""Transiciones DJ, apagado suave del temporizador, descarga inteligente y
modo ambiente. Sin red, sin mpv y sin ventanas visibles (Qt 'offscreen')."""

import os
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------- ajustes

def test_claves_compartidas_con_el_movil():
    from descargador.config import DEFECTOS
    assert DEFECTOS["descarga_inteligente"] is False
    assert DEFECTOS["descarga_inteligente_gb"] == 5
    assert DEFECTOS["transicion_dj"] is True
    assert DEFECTOS["apagado_suave"] is True


# ---------------------------------------------------------------- silencios

SALIDA_INICIO = """
[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 2.48 | silence_duration: 2.48
[silencedetect @ 0x1] silence_start: 9.1
[silencedetect @ 0x1] silence_end: 9.6 | silence_duration: 0.5
"""

SALIDA_FINAL = """
[silencedetect @ 0x1] silence_start: 21.25
"""


def test_silencedetect_relativo_y_abierto():
    from descargador.reproduccion import analizar_silencedetect
    assert analizar_silencedetect(SALIDA_INICIO) == [(0.0, 2.48), (9.1, 9.6)]
    # tramo del final, empezado en el segundo 172: se suma; sin fin = hasta el final
    assert analizar_silencedetect(SALIDA_FINAL, 172.0, 30.0) == [(193.25, None)]
    # si ffmpeg ya dio tiempos absolutos no se suman dos veces
    assert analizar_silencedetect("silence_start: 193.25", 172.0, 30.0) == [(193.25, None)]


def test_bordes_con_silencios_y_sponsorblock():
    from descargador.reproduccion import bordes_de_musica
    # sin datos: no se recorta nada
    assert bordes_de_musica(200) == (0.0, 200)
    # silencio al principio y al final
    assert bordes_de_musica(200, (), [(0.0, 2.48)], [(193.25, None)]) == (2.48, 193.25)
    # SponsorBlock manda (intro hablada y final sin musica)
    sb = [(0.0, 11.0, "music_offtopic"), (185.0, 200.0, "music_offtopic")]
    assert bordes_de_musica(200, sb) == (11.0, 185.0)
    # un patrocinio en medio no es un borde
    assert bordes_de_musica(200, [(60.0, 80.0, "sponsor")]) == (0.0, 200)
    # nunca se salta mas de 15 s al entrar
    assert bordes_de_musica(200, [(0.0, 40.0, "music_offtopic")])[0] == 15.0
    # recortes ridiculos (< 0,4 s) no cuentan
    assert bordes_de_musica(200, (), [(0.0, 0.2)], [(199.8, None)]) == (0.0, 200)
    # si quedaria casi nada, mejor no tocar
    assert bordes_de_musica(60, (), [(0.0, 20.0)], [(35.0, None)]) == (0.0, 60)


# ---------------------------------------------------------------- reproductor

class MotorFalso:
    es_video = False

    def __init__(self):
        self.volumen = None
        self.cargas = []
        self.pausado = False
        self.parado = False
        self.pos = 0.0

    def fijar_volumen(self, v):
        self.volumen = v

    def fijar_velocidad(self, v):
        pass

    def fijar_filtros(self, af):
        pass

    def cargar(self, fuente, inicio=0.0, pausado=False):
        self.cargas.append((fuente, inicio))

    def detener(self):
        self.parado = True

    def pausar(self, si=True):
        self.pausado = bool(si)

    def en_pausa(self):
        return self.pausado

    def posicion_actual(self):
        return self.pos

    def buscar(self, s):
        self.pos = s


def _pista(n, dur=200, archivo=""):
    p = {"tipo": "pista", "clave": f"yt:vid{n:08d}", "video_id": f"vid{n:08d}",
         "titulo": f"Canción {n}", "artista": "Artista", "duracion": dur, "miniatura": ""}
    if archivo:
        p["archivo"] = archivo
    return p


def _reproductor(app, monkeypatch, tmp_path):
    from descargador import mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    a = Ajustes()
    a["sponsorblock"] = False          # nada de red en las pruebas
    a["autoplay"] = False
    r = Reproductor(a, Coleccion())
    r.disponible = True
    r.audio = [MotorFalso(), MotorFalso()]
    r.activo = 0
    r.volumen = 80
    sonando = tmp_path / "a.opus"
    siguiente = tmp_path / "b.opus"
    sonando.write_bytes(b"x")
    siguiente.write_bytes(b"x")
    pistas = [_pista(1, archivo=str(sonando)), _pista(2, archivo=str(siguiente))]
    r.secuencia, r.original = list(pistas), list(pistas)
    r.pos, r.actual = 0, pistas[0]
    r._duracion = 200.0
    r.estado = "sonando"
    return r, pistas


def test_temporizador_baja_el_volumen_en_los_ultimos_30_s(app, monkeypatch, tmp_path):
    r, _ = _reproductor(app, monkeypatch, tmp_path)
    m = r.audio[0]
    r._apagar_en = time.time() + 60
    r._tic_temporizador()
    assert r._factor_suave == 1.0                     # aun falta: volumen normal
    r._apagar_en = time.time() + 15
    r._tic_temporizador()
    assert 0.45 < r._factor_suave < 0.55
    assert 36 < m.volumen < 44                        # 80 * ~0,5
    assert r._temporizador.interval() == 200          # pasos finos al final
    r.fijar_volumen(60)                               # mover el volumen no rompe el fundido
    assert m.volumen < 35
    r._apagar_en = time.time() - 0.1
    r._tic_temporizador()
    assert m.pausado is True                          # se pauso...
    assert r._factor_suave == 1.0 and m.volumen == 60  # ...y el volumen vuelve a su sitio


def test_temporizador_sin_apagado_suave_corta_de_golpe(app, monkeypatch, tmp_path):
    r, _ = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["apagado_suave"] = False
    r._apagar_en = time.time() + 10
    r._tic_temporizador()
    assert r._factor_suave == 1.0 and r.audio[0].volumen in (None, 80)


def test_transicion_dj_salta_el_silencio_final_y_entra_en_la_musica(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["crossfade"] = 0
    r._bordes["vid00000001"] = (0.0, 190.0)
    r._bordes["vid00000002"] = (3.5, 180.0)
    saliente, entrante = r.audio
    r._al_posicion(saliente, 185.0)
    assert r._fundido is None                         # aun suena musica
    r._al_posicion(saliente, 190.4)                   # empieza el silencio final
    assert r._fundido is not None and r._fundido["dur"] == pytest.approx(1.2)
    assert r.actual is pistas[1]
    assert entrante.cargas[-1][1] == 3.5              # la siguiente entra en su musica


def test_transicion_dj_adelanta_el_fundido(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["crossfade"] = 6
    r._bordes["vid00000001"] = (0.0, 190.0)
    r._al_posicion(r.audio[0], 183.0)
    assert r._fundido is None
    r._al_posicion(r.audio[0], 184.5)                 # 190 - 6: el fundido acaba con la musica
    assert r._fundido is not None and r._fundido["dur"] == 6.0


def test_sin_transicion_dj_todo_sigue_como_antes(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["transicion_dj"] = False
    r.ajustes["crossfade"] = 0
    r._bordes["vid00000001"] = (0.0, 190.0)
    r._al_posicion(r.audio[0], 195.0)
    assert r._fundido is None and r.actual is pistas[0]
    assert r._inicio_dj(pistas[1]) == 0.0


def test_al_terminar_esta_cancion_para_donde_acaba_la_musica(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r._bordes["vid00000001"] = (0.0, 190.0)
    r.programar_apagado(None, al_terminar=True)
    r._al_posicion(r.audio[0], 175.0)                 # quedan 15 s de musica: a media voz
    assert 0.45 < r._factor_suave < 0.55
    r._al_posicion(r.audio[0], 190.2)
    assert r.estado == "parado" and r._fundido is None
    assert r._factor_suave == 1.0 and r._apagar_al_final is False


# ---------------------------------------------------------------- descarga inteligente

def test_candidatos_mezclan_me_gusta_y_lo_mas_escuchado():
    from descargador.descarga_inteligente import ordenar_candidatos
    g = [_pista(1), _pista(2), _pista(3)]
    e = [_pista(2), _pista(9), {"titulo": "sin id"}, _pista(8, dur=3600)]
    orden = ordenar_candidatos(g, e, ya_descargada=lambda p: p["video_id"] == "vid00000003",
                               descartadas={"vid00000009"})
    assert [p["video_id"] for p in orden] == ["vid00000001", "vid00000002"]


def test_tope_de_espacio_y_uso_en_disco(tmp_path):
    from descargador.descarga_inteligente import GB, cabe, tamano_estimado, uso_en_disco
    assert tamano_estimado({"duracion": 200}) == 4_000_000
    assert cabe(0, 5, 4_000_000)
    assert not cabe(5 * GB - 1000, 5, 4_000_000)
    assert not cabe(0, 0, 1)
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.opus").write_bytes(b"x" * 100)
    (tmp_path / "sub" / "b.m4a").write_bytes(b"x" * 50)
    assert uso_en_disco(str(tmp_path)) == 150
    assert uso_en_disco(str(tmp_path / "no-existe")) == 0


def test_ajustes_suaves_no_tocan_los_del_usuario():
    from descargador.config import Ajustes
    from descargador.descarga_inteligente import LIMITE_KBS, _AjustesSuaves
    a = Ajustes()
    a["formato_audio"] = "mp3"
    s = _AjustesSuaves(a, "C:/x/Descarga inteligente")
    assert s["formato_audio"] == "original" and s["tipo_descarga"] == "audio"
    assert s["limite_velocidad"] == LIMITE_KBS and s["carpeta"].endswith("inteligente")
    assert s["plantilla_nombre"] == a["plantilla_nombre"]
    assert a["formato_audio"] == "mp3"
    a["limite_velocidad"] = 200
    assert _AjustesSuaves(a, "x")["limite_velocidad"] == 200


class _ColeccionFalsa:
    def __init__(self, gusta, escuchadas=()):
        self.gusta, self.escuchadas = list(gusta), list(escuchadas)
        self.invalidada = 0

    def lista_me_gusta(self):
        return self.gusta

    def mas_escuchadas(self, n=25, dias=60):
        return self.escuchadas

    def copia_local(self, vid, querer_video=False):
        return None

    def invalidar_indice(self):
        self.invalidada += 1


def test_descarga_inteligente_espera_y_no_molesta(app, monkeypatch, tmp_path):
    from descargador import config
    from descargador.config import Ajustes
    from descargador.descarga_inteligente import DescargaInteligente
    monkeypatch.setattr(config, "ruta_ffmpeg", lambda: str(tmp_path))
    a = Ajustes()
    a["carpeta"] = str(tmp_path / "Descargas")
    col = _ColeccionFalsa([_pista(1)])
    rep = SimpleNamespace(modo="audio", estado="sonando", actual=None, _fuente=None)
    di = DescargaInteligente(a, col, rep)
    lanzadas = []
    monkeypatch.setattr(di, "_lanzar", lambda p: lanzadas.append(p))
    di.revisar()
    assert lanzadas == []                              # apagada por defecto
    a["descarga_inteligente"] = True
    rep.modo, rep.estado = "video", "sonando"          # viendo un video por internet
    di.revisar()
    assert lanzadas == [] and "video" in di.estado()["motivo"]
    rep.modo = "audio"
    di.gestor = SimpleNamespace(hay_actividad=lambda: True, lista=lambda: [])
    di.revisar()
    assert lanzadas == [] and "descargas" in di.estado()["motivo"]
    di.gestor = None
    di.revisar()
    assert [p["video_id"] for p in lanzadas] == ["vid00000001"]
    a["descarga_inteligente_gb"] = 0                   # sin espacio: no baja nada
    lanzadas.clear()
    di.revisar()
    assert lanzadas == [] and "Lleno" in di.estado()["motivo"]


def test_descarga_inteligente_pausa_la_suya_si_algo_carga(app, monkeypatch, tmp_path):
    from descargador.config import Ajustes
    from descargador.descarga_inteligente import DescargaInteligente
    a = Ajustes()
    a["descarga_inteligente"] = True
    rep = SimpleNamespace(modo="audio", estado="cargando", actual=_pista(5), _fuente={})
    di = DescargaInteligente(a, _ColeccionFalsa([]), rep)
    di._tarea = SimpleNamespace(pausar=False, cancelar=False)
    di.revisar()
    assert di._tarea.pausar is True


def test_lo_bajado_entra_al_historial(app, monkeypatch, tmp_path):
    from descargador.config import Ajustes
    from descargador.descarga_inteligente import DescargaInteligente
    archivo = tmp_path / "cancion.opus"
    archivo.write_bytes(b"x" * 10)
    apuntes = []
    historial = SimpleNamespace(agregar=lambda *a, **k: apuntes.append((a, k)))
    col = _ColeccionFalsa([])
    di = DescargaInteligente(Ajustes(), col, None, historial=historial)
    llegadas = []
    di.descargada.connect(llegadas.append)
    di._tarea = SimpleNamespace(url="https://music.youtube.com/watch?v=vid00000001",
                                titulo="T", calidad="OPUS", duracion=200, autor="A",
                                plataforma=SimpleNamespace(nombre="YouTube"))
    di._pista = _pista(1)
    di._terminada("x", True, str(archivo), "")
    assert apuntes and apuntes[0][1]["es_audio"] is True
    assert apuntes[0][0][3] == str(archivo)
    assert col.invalidada == 1 and llegadas and di.estado()["hechas"] == 1


# ---------------------------------------------------------------- modo ambiente

def test_modo_ambiente_se_mueve_despacio_y_pinta(app):
    from PySide6.QtGui import QColor, QImage
    from descargador.ui.video import ModoAmbiente, fondo_desenfocado
    img = QImage(64, 64, QImage.Format_RGB32)
    img.fill(QColor("#E04020"))
    fondo = fondo_desenfocado(img, 300, 200)
    assert (fondo.width(), fondo.height()) == (300, 200)
    w = ModoAmbiente()
    w.resize(640, 360)
    w.poner({"titulo": "Tusa", "artista": "KAROL G", "miniatura": ""})
    w.img = img
    captura = w.grab().toImage()
    assert w.cuadros >= 1
    esquina = QColor(captura.pixel(30, 30))
    assert esquina.red() > esquina.blue()             # el fondo lleva el color de la portada
    # el vaiven es lento y no se sale del margen
    xs = [w.desplazamiento(t)[0] for t in range(0, 48)]
    assert max(abs(x) for x in xs) <= 640 * w.MARGEN
    pasos = [abs(a - b) for a, b in zip(xs, xs[1:])]
    assert max(pasos) <= 5                            # pocos pixeles por segundo


def test_vista_grande_muestra_ambiente_con_audio_y_video_con_video(app, monkeypatch, tmp_path):
    from PySide6.QtCore import QObject, Signal
    r, pistas = _reproductor(app, monkeypatch, tmp_path)

    class Ctx(QObject):
        aviso = Signal(str)
    ctx = Ctx()
    ctx.reproductor, ctx.ajustes, ctx.ventana = r, r.ajustes, None
    from descargador.ui.video import VistaVideo
    v = VistaVideo(ctx)
    r.pista_cambio.emit(pistas[0])
    assert v.escena.currentWidget() is v.ambiente
    assert v.ambiente.titulo == "Canción 1"
    assert "Ver el video" in v.bt_audio.text()
    r.modo = "video"
    r.modo_cambio.emit("video")
    assert v.escena.currentWidget() is v.pantalla
    r.destino_video = "mini"                          # el video se fue a la ventanita
    v._vigilar()
    assert v.escena.currentWidget() is v.ambiente
