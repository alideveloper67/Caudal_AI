# -*- coding: utf-8 -*-
"""«¿Qué suena?» en Windows (descargador/que_suena.py y ui/dialogo_que_suena.py)
sin red ni micrófono: el servidor y la grabación son falsos. Qt offscreen."""

import io
import math
import os
import struct
import sys
import wave

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import que_suena as Q  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _sin_cache():
    Q.olvidar_disponible()
    yield
    Q.olvidar_disponible()


def tono(segundos=1.0, amplitud=8000):
    n = int(Q.TASA * segundos)
    return struct.pack(f"<{n}h", *(int(amplitud * math.sin(2 * math.pi * 440 * i / Q.TASA)) for i in range(n)))


def test_wav():
    pcm = tono(0.5)
    w = wave.open(io.BytesIO(Q.wav_de_pcm(pcm)))
    assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 8000)
    assert w.readframes(8000) == pcm
    assert Q.pico(pcm) > 7000 and not Q.silencio(pcm)
    assert Q.silencio(bytes(32000)) and Q.pico(b"") == 0


def test_grabar_wav_con_grabador_falso():
    llamadas = []

    def grabador(seg, tasa, cancelar=None, avance=None):
        llamadas.append((seg, tasa))
        return tono(2)
    wav = Q.grabar_wav(10, grabador=grabador)
    assert llamadas == [(10, 16000)] and wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
    with pytest.raises(Q.ErrorQueSuena, match="Privacidad"):
        Q.grabar_wav(10, grabador=lambda *a, **k: bytes(64000))     # silencio: micrófono bloqueado
    with pytest.raises(Q.ErrorQueSuena):
        Q.grabar_wav(10, grabador=lambda *a, **k: b"\x01\x02")      # casi nada


class _Resp:
    def __init__(self, status, datos):
        self.status_code = status
        self._d = datos

    def json(self):
        if isinstance(self._d, Exception):
            raise self._d
        return self._d


class _Sesion:
    def __init__(self, get=None, post=None):
        self._get, self._post = get, post
        self.posts = []
        self.gets = 0

    def get(self, url, timeout=None):
        self.gets += 1
        if isinstance(self._get, Exception):
            raise self._get
        return self._get

    def post(self, url, data=None, headers=None, timeout=None):
        self.posts.append((url, data, headers))
        if isinstance(self._post, Exception):
            raise self._post
        return self._post


def test_disponible_y_cache():
    s = _Sesion(get=_Resp(200, {"disponible": True, "servicio": "audd"}))
    t = [0.0]
    assert Q.disponible(s, ahora=lambda: t[0]) is True
    assert Q.disponible(s, ahora=lambda: t[0]) is True and s.gets == 1      # recordado
    t[0] = 700
    Q.disponible(s, ahora=lambda: t[0])
    assert s.gets == 2
    Q.olvidar_disponible()
    assert Q.disponible(_Sesion(get=_Resp(200, {"disponible": False}))) is False
    Q.olvidar_disponible()
    import requests
    assert Q.disponible(_Sesion(get=requests.ConnectionError("x"))) is False


def test_reconocer():
    s = _Sesion(post=_Resp(200, {"encontrada": True, "titulo": "Zoo", "artista": "Shakira", "anio": "2025",
                                 "portada": "https://i.scdn.co/a", "video_id": "WTRm-Yr5Foo",
                                 "consulta": "Shakira Zoo"}))
    r = Q.reconocer(b"RIFF....", s)
    assert r["encontrada"] and r["titulo"] == "Zoo" and r["video_id"] == "WTRm-Yr5Foo"
    assert s.posts[0][0] == Q.URL and s.posts[0][2]["content-type"] == "audio/wav"
    assert Q.reconocer(b"x", _Sesion(post=_Resp(200, {"encontrada": False}))) == {"encontrada": False}
    r = Q.reconocer(b"x", _Sesion(post=_Resp(200, {"encontrada": True, "titulo": "T", "artista": "A",
                                                   "portada": "javascript:1", "video_id": "malo"})))
    assert r["portada"] == "" and r["video_id"] == "" and r["consulta"] == "A T"
    with pytest.raises(Q.ErrorQueSuena, match="todavía no está disponible"):
        Q.reconocer(b"x", _Sesion(post=_Resp(503, {"disponible": False, "mensaje": "otra"})))
    with pytest.raises(Q.ErrorQueSuena, match="Espera unos minutos"):
        Q.reconocer(b"x", _Sesion(post=_Resp(429, {"mensaje": "Ya probaste muchas veces seguidas. Espera unos minutos."})))
    import requests
    with pytest.raises(Q.ErrorQueSuena, match="internet"):
        Q.reconocer(b"x", _Sesion(post=requests.ConnectionError("x")))


def test_elegir_y_buscar_en_caudal():
    res = {"titulo": "Despacito (feat. Daddy Yankee)", "artista": "Luis Fonsi", "consulta": "Luis Fonsi Despacito", "video_id": ""}
    pistas = [
        {"tipo": "pista", "video_id": "aaaaaaaaaaa", "titulo": "Otra cosa", "artista": "Nadie"},
        {"tipo": "pista", "video_id": "kJQP7kiw5Fk", "titulo": "Despacito", "artista": "Luis Fonsi, Daddy Yankee"},
        {"tipo": "album", "video_id": "", "titulo": "Despacito"},
    ]
    assert Q.elegir(res, pistas)["video_id"] == "kJQP7kiw5Fk"
    assert Q.elegir(res, pistas[:1]) is None
    pedidos = []
    p = Q.buscar_en_caudal(res, buscar=lambda q, f, n: pedidos.append((q, f, n)) or pistas)
    assert pedidos == [("Luis Fonsi Despacito", "canciones", 5)] and p["video_id"] == "kJQP7kiw5Fk"
    # con el video de YouTube que da el servicio no hace falta buscar
    p = Q.buscar_en_caudal({"titulo": "Despacito", "artista": "Luis Fonsi", "video_id": "kJQP7kiw5Fk"},
                           buscar=lambda *a: pytest.fail("no debía buscar"))
    assert p["video_id"] == "kJQP7kiw5Fk" and p["artista"] == "Luis Fonsi" and p["tipo"] == "pista"

    def falla(*_a):
        raise RuntimeError("sin red")
    assert Q.buscar_en_caudal(res, buscar=falla) is None


# ================================================================ diálogo

def en_el_acto(f, *a, ok=None, error=None):
    try:
        r = f(*a)
    except Exception as e:  # noqa: BLE001
        if error:
            error(e)
        return
    if ok:
        ok(r)


class _Repro:
    def __init__(self):
        self.hechos = []

    def reproducir_pista(self, p):
        self.hechos.append(("ya", p["video_id"]))

    def agregar_a_cola(self, ps):
        self.hechos.append(("cola", ps[0]["video_id"]))


class _Ctx:
    def __init__(self):
        self.reproductor = _Repro()
        self.destinos = []

    def navegar(self, d):
        self.destinos.append(d)


def _api(**kw):
    base = {"disponible": lambda: True, "grabar_wav": lambda seg, cancelar=None: b"RIFFwav",
            "reconocer": lambda wav: {"encontrada": True, "titulo": "Zoo", "artista": "Shakira", "album": "Z",
                                      "anio": "2025", "portada": "", "video_id": "", "consulta": "Shakira Zoo"},
            "buscar_en_caudal": lambda r: {"tipo": "pista", "video_id": "WTRm-Yr5Foo", "titulo": "Zoo",
                                           "miniatura": "https://i.ytimg.com/vi/WTRm-Yr5Foo/hq.jpg"}}
    base.update(kw)
    return base


def test_dialogo_sin_clave(app):
    from descargador.ui.dialogo_que_suena import DialogoQueSuena
    d = DialogoQueSuena(_Ctx(), api=_api(disponible=lambda: False), en_fondo=en_el_acto)
    assert d.et_texto.text() == Q.NO_DISPONIBLE
    assert not d.bt_escuchar.isEnabled()


def test_dialogo_reconoce_y_reproduce(app):
    from descargador.ui.dialogo_que_suena import DialogoQueSuena
    ctx = _Ctx()
    d = DialogoQueSuena(ctx, api=_api(), en_fondo=en_el_acto)
    assert d.bt_escuchar.isEnabled()
    d.bt_escuchar.click()
    assert d.et_titulo.text() == "Zoo" and "Shakira" in d.et_artista.text() and "2025" in d.et_artista.text()
    assert not d.tarjeta.isHidden() and not d.bt_reproducir.isHidden() and not d.bt_cola.isHidden()
    assert d.bt_escuchar.text() == "Escuchar otra vez"
    d.bt_cola.click()
    assert ctx.reproductor.hechos == [("cola", "WTRm-Yr5Foo")] and not d.bt_cola.isEnabled()
    d.bt_buscar.click()
    assert ctx.destinos == [{"pagina": "buscar", "q": "Shakira Zoo"}]
    d2 = DialogoQueSuena(ctx, api=_api(), en_fondo=en_el_acto)
    d2.bt_escuchar.click()
    d2.bt_reproducir.click()
    assert ctx.reproductor.hechos[-1] == ("ya", "WTRm-Yr5Foo")


def test_dialogo_no_la_reconoce_y_errores(app):
    from descargador.ui.dialogo_que_suena import DialogoQueSuena
    d = DialogoQueSuena(_Ctx(), api=_api(reconocer=lambda wav: {"encontrada": False}), en_fondo=en_el_acto)
    d.bt_escuchar.click()
    assert "No la reconocimos" in d.et_texto.text() and d.tarjeta.isHidden() and d.bt_escuchar.isEnabled()

    def mic(*_a, **_k):
        raise Q.ErrorQueSuena(Q.PRIVACIDAD)
    d = DialogoQueSuena(_Ctx(), api=_api(grabar_wav=mic), en_fondo=en_el_acto)
    d.bt_escuchar.click()
    assert "Privacidad" in d.et_texto.text() and d.bt_escuchar.isEnabled()
    # se encuentra pero no está en el catálogo: solo «Buscar en Caudal»
    d = DialogoQueSuena(_Ctx(), api=_api(buscar_en_caudal=lambda r: None), en_fondo=en_el_acto)
    d.bt_escuchar.click()
    assert not d.bt_buscar.isHidden() and d.bt_reproducir.isHidden()
