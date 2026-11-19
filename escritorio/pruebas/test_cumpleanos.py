# -*- coding: utf-8 -*-
"""«Feliz cumpleaños» en el escritorio: la regla del día (29 de febrero incluido), que la celebración salga una
sola vez al día, el gorrito en avatares, el aviso de amigos con «Escribirle» y que la pantalla de celebración
quepa a 320x568. Qt offscreen, datos en carpeta temporal y una nube falsa (no se toca la base real).

Se corre solo: python -m pytest pruebas/test_cumpleanos.py"""

import os
import sys
from datetime import date, datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget  # noqa: E402

from descargador import cumpleanos as CU  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    CU.ESTADO.reiniciar()
    CU.ESTADO.ahora = date.today
    yield
    CU.ESTADO.reiniciar()
    CU.ESTADO.ahora = date.today


class SesionFalsa:
    user_id = "yo"
    access = "token"

    def __init__(self, perfil=None, ids=None, falla_rpc=False):
        self._perfil = perfil if perfil is not None else []
        self._ids = ids if ids is not None else []
        self.falla_rpc = falla_rpc

    def pedir(self, metodo, ruta, **kw):
        assert metodo == "GET" and ruta.startswith("perfiles")
        return self._perfil

    def rpc(self, nombre, **kw):
        assert nombre == "amigos_cumplen_hoy"
        if self.falla_rpc:
            raise RuntimeError("sin red")
        return self._ids


# ------------------------------------------------------------------ la regla

def test_cumpleanos_normal():
    n = date(1995, 11, 19)
    assert CU.es_cumple(n, date(2026, 11, 19))
    assert not CU.es_cumple(n, date(2026, 11, 18)) and not CU.es_cumple(n, date(2026, 11, 20))
    assert not CU.es_cumple(n, date(2026, 12, 19))
    assert not CU.es_cumple(None, date(2026, 11, 19))
    assert CU.es_cumple(n, datetime(2026, 11, 19, 23, 59))


def test_29_de_febrero():
    n = date(2000, 2, 29)
    assert CU.es_cumple(n, date(2026, 2, 28))                    # año normal: el 28
    assert not CU.es_cumple(n, date(2026, 3, 1))
    assert CU.es_cumple(n, date(2027, 2, 28))
    assert CU.es_cumple(n, date(2028, 2, 29))                    # bisiesto: el 29
    assert not CU.es_cumple(n, date(2028, 2, 28))
    assert CU.es_cumple(n, date(2100, 2, 28))                    # 2100 no es bisiesto
    assert CU.es_cumple(n, date(2000, 2, 29))
    # quien nació el 28 lo celebra siempre el 28
    m = date(1999, 2, 28)
    assert CU.es_cumple(m, date(2026, 2, 28)) and CU.es_cumple(m, date(2028, 2, 28))
    assert not CU.es_cumple(m, date(2028, 2, 29))


def test_bisiestos_y_edad():
    assert [CU.es_bisiesto(a) for a in (1900, 2000, 2024, 2026, 2100)] == [False, True, True, False, False]
    assert CU.edad_que_cumple(date(2000, 2, 29), date(2026, 2, 28)) == 26
    assert CU.edad_que_cumple(date(1995, 11, 19), date(2026, 11, 19)) == 31
    assert CU.edad_que_cumple(None, date(2026, 11, 19)) is None
    assert CU.edad_que_cumple(date(2026, 11, 19), date(2026, 11, 19)) is None       # recién nacido
    assert CU.edad_que_cumple(date(2030, 1, 1), date(2026, 11, 19)) is None          # futura
    assert CU.edad_que_cumple(date(1800, 1, 1), date(2026, 11, 19)) is None          # absurda
    assert CU.clave_dia(date(2026, 3, 5)) == "2026-03-05"


# ------------------------------------------------------------------ una sola vez al día

def test_una_sola_vez_al_dia(app):
    from descargador.config import Ajustes
    aj = Ajustes()
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    e.poner(mi_id="yo", nombre="Ali", nacimiento=date(1995, 11, 19))
    assert e.es_mio_hoy and e.edad == 31
    assert e.toca_celebrar(aj)
    e.marcar_celebrado(aj)
    assert not e.toca_celebrar(aj)                       # ya salió hoy
    assert Ajustes()["cumple_celebrado"] == "2026-11-19"   # y se recuerda aunque se cierre la app
    assert not CU.ESTADO.toca_celebrar(Ajustes())
    e.ahora = lambda: date(2026, 11, 20)
    assert not e.es_mio_hoy and not e.toca_celebrar(Ajustes())
    e.ahora = lambda: date(2027, 11, 19)
    assert e.toca_celebrar(Ajustes())                    # el año siguiente vuelve


def test_dia_que_no_es_el_suyo_no_hay_celebracion():
    from descargador.config import Ajustes
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 18)
    e.poner(mi_id="yo", nacimiento=date(1995, 11, 19))
    assert not e.toca_celebrar(Ajustes())


def test_29_de_febrero_se_celebra_una_vez_el_28():
    from descargador.config import Ajustes
    aj = Ajustes()
    e = CU.ESTADO
    e.ahora = lambda: date(2027, 2, 28)
    e.poner(mi_id="yo", nacimiento=date(2000, 2, 29))
    assert e.toca_celebrar(aj)
    e.marcar_celebrado(aj)
    assert not e.toca_celebrar(aj)
    e.ahora = lambda: date(2027, 3, 1)
    assert not e.es_mio_hoy


# ------------------------------------------------------------------ la nube

def test_lee_mi_fecha_y_los_ids_de_amigos(app):
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    s = SesionFalsa(perfil=[{"fecha_nacimiento": "1995-11-19", "nombre": "Ali Pérez"}],
                    ids=["a1", "a2", "", 7, {"amigos_cumplen_hoy": "a3"}])
    res = e.leer_de_la_nube(s)
    e.aplicar(s, res)
    assert e.mi_id == "yo" and e.nombre == "Ali" and e.es_mio_hoy and e.perfil_leido
    assert e.amigos_hoy == {"a1", "a2", "a3"}
    assert e.es_de("a1") and not e.es_de("zzz") and not e.es_de("") and e.es_de("yo")
    e.ahora = lambda: date(2026, 11, 20)                  # al día siguiente la lista ya no vale
    assert e.amigos_hoy == frozenset() and not e.es_de("a1")


def test_sin_red_no_rompe_y_conserva_lo_que_habia(app):
    e = CU.ESTADO
    e.poner(mi_id="yo", amigos=["x1"])
    s = SesionFalsa(falla_rpc=True)
    s.pedir = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sin red"))
    res = e.leer_de_la_nube(s)
    assert res == (None, None)
    e.aplicar(s, res)
    assert e.amigos_hoy == {"x1"} and e.perfil_leido


def test_mi_id_no_cuenta_como_amigo_y_reiniciar_limpia():
    e = CU.ESTADO
    e.poner(mi_id="yo", nacimiento=date(1990, 1, 1), amigos=["yo", "z"])
    assert e.amigos_hoy == {"z"}
    e.reiniciar()
    assert e.amigos_hoy == frozenset() and e.nacimiento is None and e.mi_id == ""


# ------------------------------------------------------------------ lo que se ve

def _foto(w):
    img = QImage(w.size(), QImage.Format_ARGB32)
    img.fill(0)
    w.render(img)
    return img


def test_gorro_en_el_avatar_solo_de_quien_cumple(app):
    from descargador.ui.paginas import perfil_comun as PC
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    e.poner(mi_id="yo", amigos=["amigo1"])
    con = PC.Avatar(64, "Ana", None, None, persona_id="amigo1")
    sin = PC.Avatar(64, "Ana", None, None, persona_id="otro")
    nada = PC.Avatar(64, "Ana", None, None)
    assert con.size() == sin.size() == nada.size()
    assert _foto(con) != _foto(sin)                      # el gorro cambia lo que se dibuja
    assert _foto(sin) == _foto(nada)
    e.poner(amigos=[])                                   # se quita solo cuando cambia la lista
    assert _foto(con) == _foto(sin)


def test_mi_avatar_lleva_gorro_solo_mi_dia(app):
    from descargador.ui.paginas import perfil_comun as PC
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    e.poner(mi_id="yo", nacimiento=date(1990, 11, 19))
    av = PC.Avatar(64, "Yo", None, None, persona_id="yo")
    base = PC.Avatar(64, "Yo", None, None)
    assert _foto(av) != _foto(base)
    e.ahora = lambda: date(2026, 11, 20)
    assert _foto(av) == _foto(base)


def test_gorro_en_la_mascota_y_en_cualquier_tamano(app):
    from descargador import mascotas
    from descargador.ui.cumpleanos_ui import pintar_gorro
    img = QImage(100, 100, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    pintar_gorro(p, 50, 90, 40)
    pintar_gorro(p, 50, 90, 2)                           # demasiado chico: no dibuja ni rompe
    p.end()
    assert any(img.pixelColor(x, y).alpha() for x in range(100) for y in range(100))
    datos = next((m for m in mascotas.catalogo() if not m.get("arcoiris")), None)
    if datos is not None:
        a = QImage(200, 120, QImage.Format_ARGB32)
        b = QImage(200, 120, QImage.Format_ARGB32)
        for im, gorro in ((a, False), (b, True)):
            im.fill(0)
            q = QPainter(im)
            mascotas.pintar(q, datos, 100, 110, 0, 200, 0, 0, 2, gorro=gorro)
            q.end()
        assert a != b


def _recorre(w):
    for h in w.findChildren(QWidget):
        yield h


@pytest.mark.parametrize("ancho,alto,nombre", [
    (320, 568, "Ali"),
    (320, 568, "Maximiliano Alejandro Fernandez-Sotomayor"),
    (568, 320, "Ali"),
    (940, 600, "Ali"),
])
def test_la_celebracion_cabe_sin_desbordes(app, ancho, alto, nombre):
    from descargador.ui.cumpleanos_ui import PantallaCumple
    padre = QWidget()
    padre.resize(ancho, alto)
    p = PantallaCumple(padre, nombre, 31, ctx=None, quieto=True)
    p.setGeometry(padre.rect())
    padre.show()
    app.processEvents()
    assert p.titulo.text().startswith("¡Feliz cumpleaños")
    assert p.edad.text() == "Hoy cumples 31" and not p.edad.isHidden()
    assert p.boton.text() == "¡Gracias!"
    marco = p.rect()
    for w in (p.titulo, p.edad, p.boton, p.figura):
        assert marco.contains(w.geometry()), (w, w.geometry(), marco)
    # el título entero cabe en su alto (con el texto en varias líneas si hace falta)
    assert p.titulo.heightForWidth(p.titulo.width()) <= p.titulo.height() + 2
    assert p.layout().minimumSize().height() <= alto
    padre.close()


def test_sin_edad_no_se_inventa(app):
    from descargador.ui.cumpleanos_ui import PantallaCumple
    padre = QWidget()
    padre.resize(320, 568)
    p = PantallaCumple(padre, "", None, quieto=True)
    p.setGeometry(padre.rect())
    padre.show()
    app.processEvents()
    assert p.titulo.text() == "¡Feliz cumpleaños!" and p.edad.isHidden()


def test_gracias_cierra_y_avisa(app):
    from descargador.ui.cumpleanos_ui import PantallaCumple
    padre = QWidget()
    padre.resize(400, 500)
    p = PantallaCumple(padre, "Ali", 20, quieto=True)
    p.setGeometry(padre.rect())
    padre.show()
    avisos = []
    p.cerrada.connect(lambda: avisos.append(1))
    p.boton.click()
    assert avisos == [1] and p.isHidden()


def test_el_confeti_solo_corre_mientras_se_ve(app):
    from descargador.ui.cumpleanos_ui import PantallaCumple
    padre = QWidget()
    padre.resize(400, 500)
    p = PantallaCumple(padre, "Ali", 20)
    p.setGeometry(padre.rect())
    assert not p._reloj.isActive()
    padre.show()
    assert p._reloj.isActive()
    p.hide()
    assert not p._reloj.isActive()
    quieto = PantallaCumple(padre, "Ali", 20, quieto=True)
    quieto.show()
    assert not quieto._reloj.isActive()                  # modo ligero: confeti quieto


class CtxFalso:
    def __init__(self):
        self.cuenta = {"nombre": "Ali", "sesion": None}
        self.chat_pendiente = None
        self.navegado = []

    def navegar(self, d):
        self.navegado.append(d)


def test_aviso_de_inicio_banner_y_amigos(app):
    from descargador.ui.cumpleanos_ui import AvisoCumple
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    e.poner(mi_id="yo", nacimiento=date(1990, 11, 19), amigos=["m1", "m2", "m3", "m4", "m5"])
    amigos = [{"id": f"m{i}", "usuario": f"u{i}", "nombre": n, "foto_url": None}
              for i, n in enumerate(["María Fernanda de los Ángeles Quispe", "Beto", "Cami", "Dani", "Eli"], 1)]
    ctx = CtxFalso()
    ancho = QWidget()
    ancho.resize(320, 568)
    aviso = AvisoCumple(ctx, ancho, amigos_de_prueba=amigos)
    aviso.setGeometry(0, 0, 320, 500)
    ancho.show()
    app.processEvents()
    textos = [l.text() for l in aviso.findChildren(QLabel)]
    assert any("Hoy es tu cumple" in t for t in textos)
    assert sum("¡salúdalo!" in t for t in textos) == 3            # se enseñan 3, el resto va resumido
    assert any(t == "y 2 amigos más cumplen hoy" for t in textos)
    botones = [b for b in aviso.findChildren(QPushButton) if b.text() == "Escribirle"]
    assert len(botones) == 3
    botones[0].click()
    assert ctx.chat_pendiente["id"] == "m1" and ctx.navegado == [{"pagina": "mensajes"}]
    assert not aviso.isHidden()


def test_aviso_de_inicio_no_ocupa_nada_sin_cumpleanos(app):
    from descargador.ui.cumpleanos_ui import AvisoCumple
    e = CU.ESTADO
    e.ahora = lambda: date(2026, 11, 19)
    e.poner(mi_id="yo", nacimiento=date(1990, 5, 5), amigos=[])
    aviso = AvisoCumple(CtxFalso(), None, amigos_de_prueba=[])
    assert aviso.isHidden() and aviso.layout().count() == 0
    e.poner(nacimiento=date(1990, 11, 19))                  # llega la fecha: aparece solo
    assert aviso.layout().count() == 1 and not aviso.isHidden()
