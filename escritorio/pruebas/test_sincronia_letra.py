# -*- coding: utf-8 -*-
"""La letra se pone sola a tiempo (descargador/sincronia_letra.py + ui/sincronia_auto.py).

La lógica de alinear se prueba con «lo oído» simulado; la integración, con un reproductor falso y la
escucha sustituida (no se baja el modelo ni suena nada)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from descargador import sincronia_letra as sl  # noqa: E402

LETRA = [
    (12000, "Sí, sabes que ya llevo un rato mirándote"),
    (16000, "Tengo que bailar contigo hoy"),
    (20000, "Vi que tu mirada ya estaba llamándome"),
    (24000, "Muéstrame el camino que yo voy"),
    (28000, "Tú tú eres el imán y yo soy el metal"),
    (32000, "Me voy acercando y voy armando el plan"),
    (36000, "Solo con pensarlo se acelera el pulso"),
    (40000, "Ya ya me está gustando más de lo normal"),
    (44000, "Todos mis sentidos van pidiendo más"),
    (48000, "Esto hay que tomarlo sin ningún apuro"),
    (52000, "Despacito"),
]


def oido(letra, corrimiento=0.0, quitar=(), ruido=True):
    """Lo que «oiría» el reconocedor: cada palabra de cada verso, desde su tiempo + corrimiento."""
    palabras = []
    for i, (ms, texto) in enumerate(letra):
        if i in quitar:
            continue
        for j, w in enumerate(texto.split()):
            palabras.append((ms / 1000 + corrimiento + j * 0.3, w))
    if ruido:
        palabras += [(5.0, "oh"), (6.0, "yeah"), (60.0, "baby"), (61.0, "uh")]
    palabras.sort()
    return palabras


def test_normalizar_quita_tildes_y_signos():
    assert sl.normalizar("¡Tití me preguntó!") == "titi me pregunto"


def test_idioma_por_las_palabras():
    assert sl.idioma_de([t for _, t in LETRA]) == "es"
    assert sl.idioma_de(["I love you baby and you love me", "you and me in the night all the time",
                         "oh baby it is so", "my love is the one you want"]) == "en"
    assert sl.idioma_de(["la la la"]) is None


def test_letra_a_tiempo_no_se_toca():
    r = sl.alinear(LETRA, oido(LETRA, 0.0), (0, 70))
    assert abs(r["corrimiento"]) < 0.1
    assert sl.decidir(r) == ("bien", 0)


def test_letra_corrida_13_segundos_se_corrige():
    # «La Camisa Negra» en video: la letra de LRCLIB iba 13 s antes de lo que se canta
    r = sl.alinear(LETRA, oido(LETRA, 13.17), (0, 80))
    accion, ms = sl.decidir(r)
    assert accion == "corregir"
    assert abs(ms - 13170) < 100


def test_letra_un_segundo_tarde_se_corrige():
    r = sl.alinear(LETRA, oido(LETRA, -1.1), (0, 70))
    accion, ms = sl.decidir(r)
    assert accion == "corregir" and abs(ms + 1100) < 100


def test_margen_normal_del_reconocedor_no_mueve_nada():
    assert sl.decidir(sl.alinear(LETRA, oido(LETRA, -0.4), (0, 70)))[0] == "bien"


def test_un_coro_repetido_no_engana():
    # el mismo verso suena dos veces: debe ganar el corrimiento en el que coinciden los demás versos
    letra = LETRA + [(56000, "Tengo que bailar contigo hoy")]
    r = sl.alinear(letra, oido(letra, 2.0), (0, 80))
    assert abs(r["corrimiento"] - 2.0) < 0.1


def test_reconocedor_que_falla_algunas_palabras():
    o = oido(LETRA, 3.0, quitar=(2, 5, 7))
    o = [(s, "acerando" if w == "acercando" else w) for s, w in o]
    accion, ms = sl.decidir(sl.alinear(LETRA, o, (0, 70)))
    assert accion == "corregir" and abs(ms - 3000) < 100


def test_letra_de_otra_cancion_pide_otra():
    otra = [(12000 + i * 4000, t) for i, t in enumerate([
        "Tengo la camisa negra", "hoy mi amor está de luto", "hoy tengo en el alma una pena",
        "y es por culpa de tu embrujo", "hoy sé que tú ya no me quieres", "y eso es lo que más me hiere",
        "que tengo la camisa negra", "y una pena que me duele"])]
    r = sl.alinear(LETRA, oido(otra), (0, 70))
    assert sl.decidir(r)[0] == "otra"


def test_casi_nada_oido_no_decide():
    assert sl.decidir(sl.alinear(LETRA, [(1.0, "oh")], (0, 70)))[0] == "nada"
    assert sl.decidir(sl.alinear([(1000, "la"), (2000, "oh")], oido(LETRA), (0, 70)))[0] == "nada"


def test_tramo_empieza_antes_del_primer_verso():
    desde, largo = sl.tramo_a_escuchar(LETRA, 230)
    assert desde == 0.0 and largo == sl.TRAMO_S
    desde, largo = sl.tramo_a_escuchar([(40000, "hola que tal amigo")], 60)
    assert desde == 40 - sl.ANTES_S and largo == 60 - desde


def test_verificar_elige_otra_letra_que_cuadra(monkeypatch):
    buena = [(ms + 5000, t) for ms, t in LETRA]
    mala = [(12000 + i * 4000, t) for i, t in enumerate(["Tengo la camisa negra hoy", "hoy mi amor está de luto",
                                                           "hoy tengo en el alma una pena", "y es por culpa de tu embrujo",
                                                           "hoy sé que tú ya no me quieres", "y eso es lo que más me hiere"])]
    monkeypatch.setattr(sl, "escuchar", lambda *a, **k: oido(buena, 0.5))
    otras = [{"sincronizada": True, "lineas": mala, "etiqueta": "mala"},
             {"sincronizada": True, "lineas": buena, "etiqueta": "buena"}]
    r = sl.verificar(mala, {"archivo": "x"}, 230, alternativas=lambda: otras)
    assert r["accion"] == "cambiar" and r["datos"]["etiqueta"] == "buena"


def test_verificar_sin_audio_no_hace_nada(monkeypatch):
    monkeypatch.setattr(sl, "escuchar", lambda *a, **k: None)
    assert sl.verificar(LETRA, {"archivo": "x"}, 230)["accion"] == "nada"


# ---------------------------------------------------------------- integración con la app

class _Ajustes(dict):
    def __getitem__(self, k):
        return self.get(k, {"letra_sincronia_auto": True, "letra_auto": {}, "letra_desfases": {}}.get(k))

    def guardar(self):
        self.guardado = True


class _Reproductor:
    modo = "audio"
    _duracion = 230.0
    _traspaso = None

    def __init__(self, p):
        self.actual = p

    def fuente_sonando(self):
        return self.modo, {"archivo": "c:/x.m4a"}


class _Ctx:
    def __init__(self, p):
        self.ajustes = _Ajustes()
        self.reproductor = _Reproductor(p)
        self.avisos = []

    def avisar(self, t):
        self.avisos.append(t)


def _esperar(cond, ms=4000):
    from PySide6.QtCore import QCoreApplication
    import time
    fin = time.monotonic() + ms / 1000
    while time.monotonic() < fin and not cond():
        QCoreApplication.processEvents()
        time.sleep(0.01)
    return cond()


def test_coordinador_mide_una_vez_guarda_y_da_el_desfase(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from descargador.ui import sincronia_auto as sa
    p = {"video_id": "abc", "titulo": "Despacito", "duracion": 230}
    ctx = _Ctx(p)
    llamadas = []

    def verificar(lineas, fuente, dur, alternativas):
        llamadas.append(fuente)
        return {"accion": "corregir", "desfase_ms": 13170, "datos": None, "detalle": ""}
    monkeypatch.setattr(sa.sincronia_letra, "verificar", verificar)
    monkeypatch.setattr(sa.sincronia_letra, "disponible", lambda: True)
    s = sa.SincroniaAuto(ctx)
    llegados = []
    s.listo.connect(lambda c, r: llegados.append((c, r)))
    datos = {"sincronizada": True, "lineas": LETRA}
    s.pedir(p, datos)
    s.pedir(p, datos)                         # dos vistas a la vez: se mide una sola vez
    assert _esperar(lambda: llegados)
    assert len(llamadas) == 1 and llamadas[0] == {"archivo": "c:/x.m4a"}
    # la letra va 13 s adelantada: el reloj de la letra se atrasa 13 s
    assert s.desfase(p, LETRA) == -13170
    assert s.medida(p, LETRA)
    # queda guardado: otra sesión no vuelve a escuchar
    assert list(ctx.ajustes["letra_auto"].values()) == [13170]
    s2 = sa.SincroniaAuto(ctx)
    s2.pedir(p, datos)
    _esperar(lambda: False, 300)
    assert len(llamadas) == 1 and s2.desfase(p, LETRA) == -13170
    # en video suena otra versión: se mide aparte
    ctx.reproductor.modo = "video"
    assert s.desfase(p, LETRA) == 0 and not s.medida(p, LETRA)


def test_coordinador_apagado_no_escucha(monkeypatch):
    from descargador.ui import sincronia_auto as sa
    p = {"video_id": "abc"}
    ctx = _Ctx(p)
    ctx.ajustes["letra_sincronia_auto"] = False
    monkeypatch.setattr(sa.sincronia_letra, "verificar", lambda *a: (_ for _ in ()).throw(AssertionError("no")))
    s = sa.SincroniaAuto(ctx)
    s.pedir(p, {"sincronizada": True, "lineas": LETRA})
    assert s.desfase(p, LETRA) == 0


def test_coordinador_otra_letra_queda_medida(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from descargador.ui import sincronia_auto as sa
    p = {"video_id": "zz"}
    ctx = _Ctx(p)
    nueva = {"sincronizada": True, "lineas": [(ms + 5000, t) for ms, t in LETRA]}
    monkeypatch.setattr(sa.sincronia_letra, "verificar",
                        lambda *a: {"accion": "cambiar", "desfase_ms": 500, "datos": nueva, "detalle": ""})
    monkeypatch.setattr(sa.sincronia_letra, "disponible", lambda: True)
    s = sa.SincroniaAuto(ctx)
    llegados = []
    s.listo.connect(lambda c, r: llegados.append(r))
    s.pedir(p, {"sincronizada": True, "lineas": LETRA})
    assert _esperar(lambda: llegados)
    datos, ms = s.letra_nueva(p, LETRA)
    assert datos is nueva and ms == 500
    # la letra nueva ya viene medida: no se vuelve a escuchar, y su corrección se aplica
    assert s.medida(p, nueva["lineas"]) and s.desfase(p, nueva["lineas"]) == -500
    # «cambiar» no se guarda en disco (la letra nueva solo vive en memoria)
    assert ctx.ajustes["letra_auto"] == {}


def test_lienzo_aplica_la_correccion_y_respeta_el_ajuste_a_mano(monkeypatch):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from descargador.ui import letra_viva
    from descargador.ui import sincronia_auto as sa

    class Sinc:
        def __init__(self):
            self.pedidos = []
            from PySide6.QtCore import QObject, Signal

            class _S(QObject):
                listo = Signal(str, object)
            self._s = _S()
            self.listo = self._s.listo

        def desfase(self, p, lineas):
            return -13170

        def pedir(self, p, datos):
            self.pedidos.append(p)

    falso = Sinc()
    monkeypatch.setattr(letra_viva, "sincronia_de", lambda ctx: falso)
    from types import SimpleNamespace
    from PySide6.QtCore import QObject, Signal

    class R(QObject):
        pista_cambio = Signal(object)
        posicion_cambio = Signal(float)
        estado_cambio = Signal(str)
        modo_cambio = Signal(str)
        estado = "pausa"
        velocidad = 1.0
        actual = None
        _posicion = 0.0
    aj = _Ajustes()
    ctx = SimpleNamespace(reproductor=R(), ajustes=aj, avisar=lambda t: None)
    lz = letra_viva.LienzoLetra(ctx)
    lz.pista = {"video_id": "abc"}
    lz.clave = "abc"
    lz._llegaron("abc", {"sincronizada": True, "lineas": LETRA})
    assert falso.pedidos == [{"video_id": "abc"}]
    assert lz._adelanto() == letra_viva.ADELANTO_MS - 13170
    # si la persona ya la movió a mano, manda lo suyo y no se suma lo automático
    aj["letra_desfases"] = {"abc": 500}
    assert lz._adelanto() == letra_viva.ADELANTO_MS + 500
