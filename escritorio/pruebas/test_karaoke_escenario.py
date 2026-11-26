# -*- coding: utf-8 -*-
"""El karaoke nuevo: voz y tono, puntaje, escenario palabra por palabra y mandos. Sin red, sin audio y sin micrófono."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import test_karaoke as base  # noqa: E402
from test_karaoke import app  # noqa: E402,F401
from descargador import karaoke_audio as KA  # noqa: E402


# ------------------------------------------------------------------ sonido

def test_filtros_de_voz_y_tono():
    assert KA.partes() == [] and KA.partes("no existe", "x") == []
    sin = ",".join(KA.partes("sin"))
    assert "stereotools=mlev=0.016" in sin and "lowpass=f=150" in sin and "amix=inputs=2" in sin
    assert sin.count("[") == sin.count("]")
    medio = float(",".join(KA.partes("baja")).split("mlev=")[1].split("[")[0])
    assert 0.1 < medio < 0.5
    assert KA.partes("original", 12) == [f"rubberband=pitch={2 ** 0.5:.6f}"]         # tope: 6 semitonos
    assert float(KA.partes("original", -3)[0].split("=")[-1]) < 1


def test_el_reproductor_mete_y_quita_los_filtros(monkeypatch):
    from descargador import sonoridad
    from descargador.reproduccion import Reproductor
    monkeypatch.setattr(sonoridad, "nivel_efectivo", lambda a: None)

    class R:
        ajustes = {"modo_noche": False, "sonido_envolvente": False}
        veces = 0
        fijar_karaoke = Reproductor.fijar_karaoke
        cadena_filtros = Reproductor.cadena_filtros

        def _previa(self):
            return 0.0, []

        def aplicar_sonido(self):
            self.veces += 1
    r = R()
    normal = r.cadena_filtros()
    r.fijar_karaoke("sin", 2)
    con = r.cadena_filtros()
    assert "stereotools" in con and "rubberband" in con and con.startswith("lavfi=[") and r.veces == 1
    r.fijar_karaoke("sin", 2)
    assert r.veces == 1                                       # lo mismo no rehace el sonido
    r.fijar_karaoke()
    assert r.cadena_filtros() == normal and r.veces == 2


# ------------------------------------------------------------------ puntaje

def test_nivel_del_microfono():
    import array
    assert KA.nivel(b"") == 0.0 and KA.nivel(array.array("h", [0] * 800).tobytes()) == 0.0
    fuerte = array.array("h", [16000 if i // 20 % 2 else -16000 for i in range(800)]).tobytes()
    assert 0.4 < KA.nivel(fuerte) < 0.6


def test_puntaje_premia_cantar_cuando_toca():
    p = KA.Puntaje()
    for _ in range(40):
        p.oir(0.01, None, False, 0.05)                            # la música que se cuela
    avisos = []
    for verso in range(4):
        for _ in range(30):
            avisos.append(p.oir(0.2, verso, True, 0.05))
    avisos.append(p.oir(0.0, None, False, 0.05))
    buenos = [a for a in avisos if a]
    assert len(buenos) == 4 and buenos[0] == ("¡Perfecto!", 100)
    assert p.combo == 4 and p.puntos > 400 and p.porcentaje() == 100 and p.estrellas() == 5
    for _ in range(30):
        p.oir(0.005, 9, True, 0.05)                               # callado
    assert p.oir(0.0, None, False, 0.05) == ("", 0) and p.combo == 0
    q = KA.Puntaje()
    for _ in range(200):
        q.oir(0.10, None, False, 0.05)                            # un micrófono que lo oye todo fuerte
    for _ in range(30):
        q.oir(0.11, 1, True, 0.05)
    assert q.oir(0.0, None, False, 0.05) == ("", 0)               # el ruido de siempre no es cantar


# ------------------------------------------------------------------ escenario

@pytest.fixture
def pagina(app, monkeypatch):                                     # noqa: F811
    from descargador import catalogo, paleta_caratula
    from descargador.ui import imagenes, karaoke as K, letra_viva as L
    paleta_caratula.CACHE.clear()
    L.CACHE_LETRAS.clear()
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": base.LRC, "texto": "",
                                                       "fuente": "Source: Musixmatch"})
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(base.caratula()))
    monkeypatch.setattr(imagenes, "pedir", lambda *a, **k: None)
    ctx = base._Ctx()
    ctx.ajustes["karaoke_vista"] = "escenario"
    ctx.reproductor.llamadas = []
    ctx.reproductor.fijar_karaoke = lambda voz="original", tono=0: ctx.reproductor.llamadas.append((voz, tono))
    ctx.reproductor.fijar_velocidad = lambda v, guardar=True: setattr(ctx.reproductor, "velocidad", v)
    w = K.PaginaKaraoke(ctx)
    w.resize(1280, 720)
    w.ctx_falso = ctx
    yield w
    w.hide()
    w.deleteLater()


def foto(w):
    img = QImage(w.lienzo.size(), QImage.Format_RGB32)
    w.lienzo.render(img)
    return img


def test_cada_palabra_se_enciende_a_su_hora(app, pagina):         # noqa: F811
    w = pagina
    base.abrir(app, w, 12.1)
    lc = w.lienzo
    assert lc.en_escenario() and lc._hay_verso(lc._actual)
    v = lc._verso(lc._actual)
    assert len(v.palabras) == len(base.LRC[1][1].split())
    t0 = [p[1] for p in v.palabras]
    assert t0 == sorted(t0) and t0[0] == 12000 and all(a[2] >= a[1] + 60 for a in v.palabras)
    for (r1, _a, _b, f1), (r2, _c, _d, f2) in zip(v.palabras, v.palabras[1:]):
        if f1 == f2:
            assert r1.right() <= r2.left() + 0.5                  # las palabras no se pisan
        else:
            assert r1.bottom() <= r2.top() + 0.5                  # ni las filas
    pronto = foto(w)
    w.r.mover(15.0)
    base.bombear(app, 0.1)
    assert foto(w) != pronto
    assert v.w <= w.width() and v.filas <= 3


def test_cuenta_atras_y_silencios(app, pagina):                   # noqa: F811
    w = pagina
    base.abrir(app, w, 6.0)
    lc = w.lienzo
    w.r.mover(6.0)
    base.bombear(app, 0.1)
    assert 5.0 < lc.falta_para_cantar() < 6.2
    foto(w)
    w.r.mover(10.5)                                               # 3, 2, 1
    base.bombear(app, 0.1)
    assert 0.5 < lc.falta_para_cantar() < 1.8
    foto(w)
    w.r.mover(13.0)
    base.bombear(app, 0.1)
    assert lc.falta_para_cantar() is None
    w.r.mover(60.0)                                               # después del último verso
    base.bombear(app, 0.1)
    foto(w)


def test_los_versos_que_vienen_se_preparan_a_trozos(app, pagina):  # noqa: F811
    w = pagina
    base.abrir(app, w, 12.5)
    lc = w.lienzo
    tope = time.monotonic() + 5
    sig = lc._siguiente(lc._actual)
    while lc._clave_verso(lc._siguiente(sig)) not in lc._versos and time.monotonic() < tope:
        w.r.mover(13.0)
        base.bombear(app, 0.05)
    assert lc._clave_verso(sig) in lc._versos and lc._clave_verso(lc._siguiente(sig)) in lc._versos
    lc._olvidar_dibujos()                                         # a medias y pedido de golpe: se termina bien
    lc._adelantar_versos()
    assert lc._haciendo is not None
    v = lc._verso(lc._haciendo[0][0])
    assert not v.apagado.isNull() and not v.encendido.isNull() and not v.halo.isNull() and lc._haciendo is None


def test_mandos_de_voz_tono_velocidad_y_vista(app, pagina):       # noqa: F811
    w = pagina
    base.abrir(app, w, 13.0)
    r, aj = w.r, w.ctx_falso.ajustes
    w.bt_voces["sin"].click()
    QTest.keyClick(w, Qt.Key_Up)
    QTest.keyClick(w, Qt.Key_Up)
    QTest.keyClick(w, Qt.Key_Down)
    base.bombear(app, 0.4)
    assert aj["karaoke_voz"] == "sin" and w.tono == 1 and r.llamadas[-1] == ("sin", 1)
    assert w.et_tono.text() == "Tono +1" and w.bt_voces["sin"].isChecked() and not w.bt_voces["original"].isChecked()
    w.poner_velocidad(-0.05)
    assert abs(r.velocidad - 0.95) < 1e-6 and w.et_vel.text() == "0,95×"
    QTest.keyClick(w, Qt.Key_L)
    assert aj["karaoke_vista"] == "lista" and not w.lienzo.en_escenario()
    foto(w)
    QTest.keyClick(w, Qt.Key_L)
    assert w.lienzo.en_escenario()
    QTest.keyClick(w, Qt.Key_V)
    assert aj["karaoke_voz"] == "original"
    w.hide()                                                      # al salir todo suena como siempre
    assert r.llamadas[-1] == ("original", 0) and r.velocidad == 1.0 and w.tono == 0
    assert not w.lienzo.micro.encendido


def test_puntaje_a_la_vista_y_resultado_al_cambiar_de_cancion(app, pagina, monkeypatch):  # noqa: F811
    w = pagina
    lc = w.lienzo
    monkeypatch.setattr(type(lc.micro), "encender", lambda s: setattr(s, "_puesto", True))
    monkeypatch.setattr(type(lc.micro), "apagar", lambda s: setattr(s, "_puesto", False))
    monkeypatch.setattr(type(lc.micro), "encendido", property(lambda s: getattr(s, "_puesto", False)))
    base.abrir(app, w, 12.1)
    QTest.keyClick(w, Qt.Key_M)
    assert w.bt_micro.isChecked()
    lc.micro.nivel_ahora = 0.3
    for k in range(12):
        w.r.mover(12.3 + k * 0.2)
        base.bombear(app, 0.06)
    assert lc.puntaje.cantando
    foto(w)
    lc.puntaje.versos, lc.puntaje.suma, lc.puntaje.puntos = 6, 5.4, 720
    lc._pista(dict(w.r.actual, clave="k2"))
    assert lc._resultado[:3] == (5, 720, 90) and lc.puntaje.puntos == 0
    foto(w)
    QTest.mouseClick(lc, Qt.LeftButton)
    assert lc._resultado is None


def test_los_mandos_no_se_salen(app, pagina):                     # noqa: F811
    w = pagina
    base.abrir(app, w, 13.0)
    for ancho, alto in ((1280, 720), (900, 560), (700, 420)):
        w.resize(ancho, alto)
        base.bombear(app, 0.1)
        foto(w)
        assert w.mandos.geometry().bottom() < w.height() and w.mandos.width() == w.width()
        assert w.mandos.sizeHint().width() <= max(640, ancho)
