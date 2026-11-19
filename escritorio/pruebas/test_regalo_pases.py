# -*- coding: utf-8 -*-
"""Pases de regalo para donadores: la tarjeta «Regala una prueba a tus amigos» (crear, listar con su estado,
copiar, anular, texto para compartir) y el aviso único. Qt offscreen, datos en carpeta temporal y una nube
falsa que contesta lo que contestarían las funciones de supabase/pases_regalo.sql (la base real no se toca).

Se corre solo: python -m pytest pruebas/test_regalo_pases.py"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget  # noqa: E402

from descargador import nube  # noqa: E402
from descargador import premium as P  # noqa: E402
from descargador import social as S  # noqa: E402
from descargador.ui import aviso_regalo as AR  # noqa: E402
from descargador.ui import personalizar_ajuste as PA  # noqa: E402
from test_premium import CtxFalso, SesionFalsa, esperar, iso  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    yield tmp_path


def _pase(codigo, usado=False, vigente=True):
    return {"codigo": codigo, "dias": 7, "usado": usado, "vigente": vigente and not usado,
            "caduca": iso(datetime.now(timezone.utc) + timedelta(days=20))}


class Servidor:
    """Lo que contestan las tres funciones del servidor, con su lista de códigos viva."""

    def __init__(self, pases=None):
        self.pases = list(pases or [])
        self.creados = 0
        self.rechazo = None            # si hay texto, crear_pase_regalo contesta ok:false con ese mensaje

    def crear(self, _p):
        if self.rechazo:
            return {"ok": False, "mensaje": self.rechazo}
        self.creados += 1
        cod = f"NUEV-{self.creados:04d}".replace("0", "A")
        self.pases.insert(0, _pase(cod))
        return {"ok": True, "codigo": cod, "dias": 7}

    def mis(self, _p):
        return list(self.pases)

    def anular(self, p):
        antes = len(self.pases)
        self.pases = [x for x in self.pases if not (x["codigo"] == p["p_codigo"] and not x["usado"])]
        return len(self.pases) < antes


def _gestor(app, tipo="donador", pases=None, server=None):
    server = server or Servidor(pases)
    vence = datetime.now(timezone.utc) + timedelta(days=6)
    datos = {"mi_premium": {"premium": tipo is not None, "tipo": tipo,
                            "vence": iso(vence) if tipo == "prueba" else None},
             "GET perfiles": [{"marco": "ninguno", "efecto_nombre": "ninguno", "tema_premium": "ninguno"}],
             "PATCH perfiles": [{}],
             "crear_pase_regalo": server.crear, "mis_pases_regalo": server.mis,
             "anular_pase_regalo": server.anular}
    ses = SesionFalsa(datos)
    ctx = CtxFalso(ses)
    g = P.GestorPremium(ctx)
    ctx.premium = g
    g.refrescar()
    esperar(app, lambda: not g._pidiendo, "estado de la cuenta")
    return ctx, g, ses, server


_VIVOS = []


def _tarjeta(ctx):
    """La tarjeta dentro de una ventana ya visible (como en Personalizar): ella decide si se muestra."""
    marco = QWidget()
    lay = QVBoxLayout(marco)
    t = PA.TarjetaRegalo(ctx, marco)
    lay.addWidget(t)
    marco.resize(620, 500)
    marco.show()
    _VIVOS.append(marco)               # si no, Python lo borra al salir de aquí
    return t


def _filas(t):
    """[(código, texto del estado, [botones])] de la lista."""
    out = []
    for i in range(t.lista.count()):
        lay = t.lista.itemAt(i).layout()
        ws = [lay.itemAt(j).widget() for j in range(lay.count())]
        out.append((ws[0].text(), ws[1].text(), [w.text() for w in ws[2:] if isinstance(w, QPushButton)]))
    return out


def _quieta(app, t, n=3):
    for _ in range(n):
        app.processEvents()


# ------------------------------------------------------------------ servidor (social.py)

def test_social_llama_a_las_tres_funciones_del_servidor(app):
    srv = Servidor([_pase("AAAA-BBBB")])
    ses = SesionFalsa({"crear_pase_regalo": srv.crear, "mis_pases_regalo": srv.mis,
                       "anular_pase_regalo": srv.anular})
    s = S.Social(ses)
    assert s.crear_pase_regalo()["ok"]
    assert [p["codigo"] for p in s.mis_pases_regalo()][-1] == "AAAA-BBBB"
    assert s.anular_pase_regalo(" aaaa-bbbb ") is True                  # va en mayúsculas y sin espacios
    assert ses.llamadas[-1] == ("anular_pase_regalo", {"p_codigo": "AAAA-BBBB"})
    assert s.anular_pase_regalo("ZZZZ-ZZZZ") is False


def test_social_aguanta_respuestas_raras(app):
    s = S.Social(SesionFalsa({"crear_pase_regalo": None, "mis_pases_regalo": {"x": 1},
                              "anular_pase_regalo": None}))
    assert s.crear_pase_regalo()["ok"] is False
    assert s.mis_pases_regalo() == []
    assert s.anular_pase_regalo("AAAA-BBBB") is False


# ------------------------------------------------------------------ quién ve la tarjeta

@pytest.mark.parametrize("tipo,visible", [("donador", True), ("fundador", True), ("prueba", False), (None, False)])
def test_solo_donadores_y_fundadores_ven_la_tarjeta(app, tipo, visible):
    ctx, g, ses, _srv = _gestor(app, tipo)
    assert g.puede_regalar is visible
    t = _tarjeta(ctx)
    assert t.isVisible() is visible
    if not visible:                                                      # y ni siquiera pregunta al servidor
        _quieta(app, t)
        assert not any(ll[0] == "mis_pases_regalo" for ll in ses.llamadas)
    t.window().close()


def test_dentro_de_personalizar_sigue_la_misma_regla(app):
    from descargador.ui.personalizar_ajuste import SeccionPersonalizar
    ctx, g, _ses, _srv = _gestor(app, "prueba")
    s = SeccionPersonalizar(ctx)
    s.resize(660, 900)
    s.show()
    assert not s.tarjeta_regalo.isVisible()
    s.close()
    ctx, g, _ses, _srv = _gestor(app, "donador")
    s = SeccionPersonalizar(ctx)
    s.resize(660, 900)
    s.show()
    assert s.tarjeta_regalo.isVisible()
    s.close()


def test_aparece_cuando_se_sabe_que_es_donador(app):
    ctx, g, _ses, _srv = _gestor(app, None)
    t = _tarjeta(ctx)
    assert not t.isVisible()
    from descargador.premium_datos import EstadoPremium
    g._aplicar_remoto(EstadoPremium(True, "donador", None), None)      # llega de la nube
    assert t.isVisible()
    t.window().close()


# ------------------------------------------------------------------ la lista

def test_lista_con_estado_y_botones(app):
    pases = [_pase("AAAA-BBBB"), _pase("CCCC-DDDD", usado=True), _pase("EEEE-FFFF", vigente=False)]
    ctx, g, ses, _srv = _gestor(app, pases=pases)
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 3, "llegan los códigos")
    assert _filas(t) == [("AAAA-BBBB", "Sin usar", ["Copiar", "Anular"]),
                         ("CCCC-DDDD", "Usado", []),
                         ("EEEE-FFFF", "Caducado", ["Anular"])]
    # el texto para compartir lleva el primer código sin usar y la web
    assert t.caja_texto.isVisible()
    assert "AAAA-BBBB" in t.texto.text() and "https://caudal-musica.netlify.app" in t.texto.text()
    t.window().close()


def test_sin_codigos_sin_lista_ni_texto(app):
    ctx, g, _ses, _srv = _gestor(app)
    t = _tarjeta(ctx)
    esperar(app, lambda: t._cargado, "pregunta")
    _quieta(app, t)
    assert _filas(t) == [] and not t.caja_texto.isVisible()
    t.window().close()


def test_si_todos_estan_usados_no_hay_texto_para_compartir(app):
    ctx, g, _ses, _srv = _gestor(app, pases=[_pase("AAAA-BBBB", usado=True)])
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 1, "llegan")
    assert not t.caja_texto.isVisible()
    t.window().close()


def test_estados_y_texto_son_funciones_puras():
    assert PA.estado_de_regalo({"usado": True, "vigente": False}) == "usado"
    assert PA.estado_de_regalo({"usado": False, "vigente": True}) == "sin_usar"
    assert PA.estado_de_regalo({"usado": False, "vigente": False}) == "caducado"
    t = PA.texto_para_compartir("ABCD-2345")
    assert "ABCD-2345" in t and "https://caudal-musica.netlify.app" in t and "Tengo un código" in t


# ------------------------------------------------------------------ crear, copiar, anular

def test_crear_un_codigo_lo_agrega_a_la_lista(app):
    ctx, g, ses, srv = _gestor(app)
    t = _tarjeta(ctx)
    esperar(app, lambda: t._cargado, "pregunta")
    t.bt_crear.click()
    assert not t.bt_crear.isEnabled() and "Creando" in t.msg.text()     # un solo toque a la vez
    esperar(app, lambda: len(t.pases) == 1, "aparece el código nuevo")
    assert srv.creados == 1 and t.pases[0]["codigo"].startswith("NUEV-")
    assert t.bt_crear.isEnabled() and "Listo" in t.msg.text()
    assert t.pases[0]["codigo"] in t.texto.text()
    t.window().close()


def test_si_el_servidor_dice_que_no_se_muestra_su_mensaje(app):
    srv = Servidor()
    srv.rechazo = "Ya tienes 3 códigos sin usar. Cuando un amigo canjee uno, puedes crear otro."
    ctx, g, _ses, _srv = _gestor(app, server=srv)
    t = _tarjeta(ctx)
    t.bt_crear.click()
    esperar(app, lambda: t.msg.text().startswith("Ya tienes 3"), "mensaje del servidor")
    assert t.bt_crear.isEnabled() and t.pases == []
    t.window().close()


def test_sin_red_se_explica_sin_jerga(app):
    ctx, g, ses, _srv = _gestor(app)
    t = _tarjeta(ctx)
    esperar(app, lambda: t._cargado, "pregunta")
    _quieta(app, t)
    ses.sin_red = True
    t.bt_crear.click()
    esperar(app, lambda: "Sin conexión" in t.msg.text(), "aviso de red")
    assert t.bt_crear.isEnabled()
    t.window().close()


def test_copiar_el_codigo_y_el_mensaje(app):
    ctx, g, _ses, _srv = _gestor(app, pases=[_pase("AAAA-BBBB")])
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 1, "llega")
    lay = t.lista.itemAt(0).layout()
    copiar = [lay.itemAt(j).widget() for j in range(lay.count())
              if isinstance(lay.itemAt(j).widget(), QPushButton)][0]
    copiar.click()
    assert QGuiApplication.clipboard().text() == "AAAA-BBBB"
    t.bt_copiar_texto.click()
    portapapeles = QGuiApplication.clipboard().text()
    assert "AAAA-BBBB" in portapapeles and "https://caudal-musica.netlify.app" in portapapeles
    t.window().close()


def test_anular_un_codigo_lo_quita(app):
    ctx, g, ses, srv = _gestor(app, pases=[_pase("AAAA-BBBB"), _pase("CCCC-DDDD")])
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 2, "llegan")
    lay = t.lista.itemAt(0).layout()
    anular = [lay.itemAt(j).widget() for j in range(lay.count())
              if isinstance(lay.itemAt(j).widget(), QPushButton) and lay.itemAt(j).widget().text() == "Anular"][0]
    anular.click()
    esperar(app, lambda: len(t.pases) == 1, "se quita de la lista")
    assert ("anular_pase_regalo", {"p_codigo": "AAAA-BBBB"}) in ses.llamadas
    assert t.pases[0]["codigo"] == "CCCC-DDDD" and "Anulado" in t.msg.text()
    t.window().close()


def test_anular_uno_que_ya_se_uso_avisa(app):
    ctx, g, _ses, srv = _gestor(app, pases=[_pase("AAAA-BBBB")])
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 1, "llega")
    srv.pases[0]["usado"] = True                                         # un amigo lo canjeó justo ahora
    t._anular("AAAA-BBBB")
    esperar(app, lambda: "ya no se puede anular" in t.msg.text(), "aviso")
    esperar(app, lambda: t.pases and t.pases[0]["usado"], "la lista se actualiza")
    t.window().close()


def test_cerrar_la_tarjeta_antes_de_la_respuesta_no_rompe(app):
    ctx, g, _ses, _srv = _gestor(app)
    t = _tarjeta(ctx)
    t.bt_crear.click()
    t.window().close()
    t.deleteLater()
    import time
    fin = time.time() + 0.6
    while time.time() < fin:
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.mark.parametrize("ancho", [560, 660])
def test_la_tarjeta_cabe_en_ventanas_chicas(app, ancho):
    ctx, g, _ses, _srv = _gestor(app, pases=[_pase("AAAA-BBBB")])
    t = _tarjeta(ctx)
    esperar(app, lambda: len(t.pases) == 1, "llega")
    assert t.minimumSizeHint().width() <= ancho - 60
    t.window().close()


# ------------------------------------------------------------------ el aviso único

class VentanaFalsa(QWidget):
    def __init__(self, ctx, g):
        super().__init__()
        self.ajustes = ctx.ajustes
        self.premium = g
        self.fue_al_regalo = 0

    def ir_a_regalo(self):
        self.fue_al_regalo += 1


def test_el_ajuste_nuevo_empieza_sin_ver(app):
    ctx, g, _ses, _srv = _gestor(app)
    assert ctx.ajustes["aviso_regalo_visto"] is False


@pytest.mark.parametrize("tipo,sale", [("donador", True), ("fundador", True), ("prueba", False), (None, False)])
def test_el_aviso_sale_solo_a_donadores_y_fundadores(app, tipo, sale):
    ctx, g, _ses, _srv = _gestor(app, tipo)
    v = VentanaFalsa(ctx, g)
    d = AR.mostrar_si_toca(v)
    assert (d is not None) is sale
    assert ctx.ajustes["aviso_regalo_visto"] is sale                    # solo se anota si se enseñó
    if d is not None:
        d.close()
    v.close()


def test_el_aviso_sale_una_sola_vez(app):
    ctx, g, _ses, _srv = _gestor(app)
    v = VentanaFalsa(ctx, g)
    d = AR.mostrar_si_toca(v)
    assert d is not None and d.isVisible()
    assert any("regalar códigos de prueba a tus amigos" in lb.text() for lb in d.findChildren(QLabel))
    d.close()
    assert AR.mostrar_si_toca(v) is None                                # ya está anotado
    # y queda guardado en disco: otra Ajustes (otro arranque) lo sabe
    from descargador.config import Ajustes
    assert Ajustes()["aviso_regalo_visto"] is True
    v.close()


def test_el_boton_lleva_a_la_tarjeta(app):
    ctx, g, _ses, _srv = _gestor(app)
    v = VentanaFalsa(ctx, g)
    d = AR.mostrar_si_toca(v)
    d.bt_ir.click()
    esperar(app, lambda: v.fue_al_regalo == 1, "navega a la tarjeta")
    v.close()


def test_ahora_no_cierra_y_no_navega(app):
    ctx, g, _ses, _srv = _gestor(app)
    v = VentanaFalsa(ctx, g)
    d = AR.mostrar_si_toca(v)
    d.bt_luego.click()
    for _ in range(5):
        app.processEvents()
    assert v.fue_al_regalo == 0 and ctx.ajustes["aviso_regalo_visto"] is True
    v.close()
