# -*- coding: utf-8 -*-
"""Más para donadores: color del nombre, pared de agradecimiento, mascota propia y letra con efectos.

Qt offscreen, datos en carpeta temporal y nube falsa (como test_premium.py / test_karaoke.py). Nada abre
ventanas a la vista ni sale a internet."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from descargador import nube  # noqa: E402
from descargador import premium as P  # noqa: E402
from descargador import premium_datos as D  # noqa: E402
from test_premium import CtxFalso, SesionFalsa, esperar, iso  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    monkeypatch.setattr(QApplication, "applicationState", lambda self: Qt.ApplicationActive)
    yield tmp_path


def _premium(app, tipo="donador", perfil=None, extra=None):
    vence = datetime.now(timezone.utc) + timedelta(days=6)
    fila = {"marco": "ninguno", "efecto_nombre": "ninguno", "tema_premium": "ninguno"}
    fila.update(perfil or {})
    datos = {"mi_premium": {"premium": True, "tipo": tipo, "vence": iso(vence) if tipo == "prueba" else None},
             "GET perfiles": [fila], "PATCH perfiles": [{}]}
    datos.update(extra or {})
    ses = SesionFalsa(datos)
    ctx = CtxFalso(ses)
    g = P.GestorPremium(ctx)
    ctx.premium = g
    g.refrescar()
    esperar(app, lambda: g.premium and g.tipo == tipo and not g._pidiendo, "estado premium")
    return ctx, g, ses


def _gratis():
    ctx = CtxFalso(SesionFalsa({"mi_premium": {"premium": False}, "GET perfiles": [{}]}))
    ctx.premium = P.GestorPremium(ctx)
    return ctx, ctx.premium


def _patches(ses):
    return [c[2]["json"] for c in ses.llamadas if c[0] == "PATCH"]


# ================================================================== datos puros

def test_color_valido_normaliza_y_rechaza_lo_raro():
    assert D.color_valido("#ff5c8a") == "#FF5C8A"
    assert D.color_valido(" 22d3ee ") == "#22D3EE"
    assert D.color_valido("#abc") == "#AABBCC"
    for malo in (None, "", "rojo", "#12345", "#GGGGGG", "#1234567", 12):
        assert D.color_valido(malo) is None
    assert len(D.PALETA_NOMBRE) == 9 and all(D.color_valido(h) == h for _n, h in D.PALETA_NOMBRE)
    assert D.nombre_de_color("#ffc857") == "Oro"
    assert D.nombre_de_color("#123456") == "Personalizado"
    assert D.nombre_de_color(None) == "Sin color"


def test_la_pared_y_la_mascota_son_de_donadores_de_verdad():
    futuro = time.time() + 86400
    assert D.es_donador_de_verdad(D.EstadoPremium(True, "donador"))
    assert D.es_donador_de_verdad(D.EstadoPremium(True, "fundador"))
    assert not D.es_donador_de_verdad(D.EstadoPremium(True, "prueba", futuro))   # la prueba no cuenta
    assert not D.es_donador_de_verdad(D.EstadoPremium(False, None))
    assert not D.es_donador_de_verdad(None)


def test_mensaje_de_whatsapp_para_la_mascota():
    assert D.mensaje_mascota("@ana_01") == "Hola, soy @ana_01 en Caudal. Quiero mi mascota personalizada."
    assert "mascota personalizada" in D.mensaje_mascota("")
    u = urlparse(D.url_mascota("ana"))
    assert u.scheme == "https" and u.netloc == "wa.me" and u.path == "/51902464984"
    assert parse_qs(u.query)["text"][0] == D.mensaje_mascota("ana")
    assert "%20" in u.query and " " not in D.url_mascota("ana")          # bien codificado
    assert "aprueba por WhatsApp" in D.TEXTO_MASCOTA
    assert unquote(D.url_mascota("x&y=1")).endswith("Quiero mi mascota personalizada.")


def test_leer_pared_limpia_lo_que_llega():
    filas = D.leer_pared([
        {"usuario": "funda", "nombre": "Fundadora", "tipo": "fundador", "color": "#ffc857", "desde": "2026-01-01"},
        {"usuario": "dona", "nombre": "", "tipo": "donador", "color": "azul"},
        {"usuario": "", "nombre": "sin usuario", "tipo": "donador"},
        {"usuario": "prueba", "tipo": "prueba"},
        "basura", None,
    ])
    assert [f["usuario"] for f in filas] == ["funda", "dona"]
    assert filas[0]["color"] == "#FFC857" and filas[1]["color"] is None
    assert filas[1]["nombre"] == "dona"                      # sin nombre, el usuario
    assert D.leer_pared(None) == [] and D.leer_pared({"x": 1}) == []


def test_estilos_de_la_letra_con_efectos():
    assert D.ESTILOS_ESCENA == ("resplandor", "ola", "neon", "cine", "zoom", "maquina", "lluvia", "giro")
    assert D.texto_estilos_escena() == ("Ocho estilos: Resplandor, Ola, Neón, Cine, Zoom, Máquina, Lluvia y Giro")
    assert all(k in D.NOMBRES_ESCENA and k in D.DETALLE_ESCENA for k in D.ESTILOS_ESCENA)
    assert D.estilo_escena_valido(" NEON ") == "neon"
    assert D.estilo_escena_valido("inventado") == "resplandor" and D.estilo_escena_valido(None) == "resplandor"


# ================================================================== gestor premium

def test_el_color_y_la_pared_llegan_del_perfil_y_se_recuerdan(app):
    ctx, g, ses = _premium(app, perfil={"color_nombre": "#ff4dd2", "en_pared": True})
    esperar(app, lambda: g.color_nombre == "#FF4DD2", "el color del perfil")
    assert g.color_efectivo() == "#FF4DD2" and g.en_pared is True
    rutas = [c[1] for c in ses.llamadas if c[0] == "GET"]
    assert any("select=marco,efecto_nombre,tema_premium" in r for r in rutas)
    assert any("select=color_nombre,en_pared" in r for r in rutas)    # en otra petición (ver abajo)
    # al reabrir sale de la copia local, sin red
    g2 = P.GestorPremium(CtxFalso(SesionFalsa(sin_red=True)))
    assert g2.color_nombre == "#FF4DD2" and g2.en_pared is True


def test_si_la_base_no_tiene_las_columnas_nuevas_lo_de_siempre_sigue(app):
    class SesionSinColumnas(SesionFalsa):
        def pedir(self, metodo, ruta, **kw):
            if "color_nombre" in ruta:
                raise nube.ErrorNube("column perfiles.color_nombre does not exist")
            return super().pedir(metodo, ruta, **kw)

    ses = SesionSinColumnas({"mi_premium": {"premium": True, "tipo": "donador"},
                             "GET perfiles": [{"marco": "oro", "efecto_nombre": "neon", "tema_premium": "ninguno"}]})
    ctx = CtxFalso(ses)
    g = P.GestorPremium(ctx)
    ctx.premium = g
    g.refrescar()
    esperar(app, lambda: g.marco == "oro", "el marco de siempre")
    assert g.efecto == "neon" and g.color_nombre is None and g.en_pared is False


def test_sin_beneficios_el_color_no_se_ve_ni_se_guarda(app):
    ctx, g = _gratis()
    g.color_nombre = "#FF5C8A"                     # quedó de cuando donaba
    assert g.color_efectivo() is None
    assert g.guardar_color_nombre("#22D3EE") is False
    assert g.color_nombre == "#FF5C8A"
    assert g.guardar_en_pared(True) is False and g.en_pared is False


def test_guardar_el_color_solo_manda_el_color(app):
    ctx, g, ses = _premium(app)
    avisado = []
    g.cambiado.connect(lambda: avisado.append(1))
    assert g.guardar_color_nombre("#7cffb2") is True
    assert g.color_nombre == "#7CFFB2" and avisado
    esperar(app, lambda: {"color_nombre": "#7CFFB2"} in _patches(ses), "el guardado del color")
    g.guardar_color_nombre(None)                   # «Sin color»
    esperar(app, lambda: {"color_nombre": None} in _patches(ses), "quitar el color")
    assert g.color_efectivo() is None
    # el guardado de siempre (marco/efecto/tema) no lleva las columnas nuevas
    g.guardar_personalizacion("oro", "brillo", None)
    esperar(app, lambda: any("marco" in x for x in _patches(ses)), "el guardado de siempre")
    assert all("color_nombre" not in x for x in _patches(ses) if "marco" in x)


def test_la_pared_es_de_donadores_y_fundadores_no_de_la_prueba(app):
    ctx, g, ses = _premium(app, tipo="prueba")
    assert g.premium and not g.donador_de_verdad
    assert g.guardar_en_pared(True) is False and g.en_pared is False
    assert g.guardar_en_pared(False) is True          # quitarse se puede siempre
    ctx, g, ses = _premium(app, tipo="fundador")
    assert g.donador_de_verdad and g.guardar_en_pared(True) is True
    esperar(app, lambda: {"en_pared": True} in _patches(ses), "guardar la casilla")


def test_social_lee_colores_y_pared():
    from descargador import social as S
    ses = SesionFalsa({"colores_nombre": {"ana": "#ff5c8a", "beto": "rojo"},
                       "pared_agradecimiento": [{"usuario": "ana", "nombre": "Ana", "tipo": "donador"}]})
    s = S.Social(ses)
    assert s.colores_nombre(["Ana", " beto ", "", None, "ana"]) == {"ana": "#FF5C8A"}
    nombre, params = [c for c in ses.llamadas if c[0] == "colores_nombre"][0]
    assert params == {"p_usuarios": ["ana", "beto"]}           # sin repetidos, en minúsculas
    assert s.colores_nombre([]) == {}
    assert [f["usuario"] for f in s.pared_agradecimiento()] == ["ana"]
    s.guardar_extra_donador({"color_nombre": "#FF5C8A", "marco": "oro"})
    assert ses.llamadas[-1][2]["json"] == {"color_nombre": "#FF5C8A"}       # nada que no sea suyo


# ================================================================== colores de los demás

class _SesionColores(SesionFalsa):
    def __init__(self, colores, falla=False):
        super().__init__({"mi_premium": {"premium": False}, "GET perfiles": [{}]})
        self.colores = colores
        self.falla = falla
        self.pedidos = []

    def rpc(self, nombre, **p):
        if nombre == "colores_nombre":
            self.pedidos.append(list(p["p_usuarios"]))
            if self.falla:
                raise nube.ErrorNube("Could not find the function public.colores_nombre")
            return {u: self.colores[u] for u in p["p_usuarios"] if u in self.colores}
        return super().rpc(nombre, **p)


def test_los_colores_se_piden_en_una_sola_tanda_y_se_recuerdan(app):
    from descargador import colores_nombre as CN
    ses = _SesionColores({"beto": "#22D3EE"})
    ctx = CtxFalso(ses)
    ctx.premium = P.GestorPremium(ctx)
    g = CN.gestor(ctx)
    assert CN.gestor(ctx) is g
    llegadas = []
    g.cambiado.connect(lambda: llegadas.append(1))
    assert g.color_de("beto") is None and g.color_de("@Carla") is None and g.color_de("beto") is None
    esperar(app, lambda: llegadas, "los colores")
    assert ses.pedidos == [["beto", "carla"]]                 # una sola llamada para los dos
    assert g.color_de("beto") == "#22D3EE" and g.color_de("carla") is None
    app.processEvents()
    assert len(ses.pedidos) == 1                             # lo sabido (con o sin color) no se vuelve a pedir


def test_mi_color_sale_del_gestor_premium_al_instante(app):
    from descargador import colores_nombre as CN
    ctx, gp, ses = _premium(app, perfil={"color_nombre": "#A78BFA"})
    esperar(app, lambda: gp.color_nombre == "#A78BFA", "mi color")
    g = CN.gestor(ctx)
    assert g.color_de("ana") == "#A78BFA"                     # «ana» es la cuenta de CtxFalso
    assert not [c for c in ses.llamadas if c[0] == "colores_nombre"]


def test_sin_la_funcion_en_la_base_los_nombres_se_ven_como_siempre(app):
    from descargador import colores_nombre as CN
    ses = _SesionColores({}, falla=True)
    ctx = CtxFalso(ses)
    ctx.premium = P.GestorPremium(ctx)
    g = CN.gestor(ctx)
    assert g.color_de("beto") is None
    esperar(app, lambda: ses.pedidos, "la pregunta")
    esperar(app, lambda: "beto" in g._cache, "recordar el fallo")
    assert g.color_de("beto") is None and len(ses.pedidos) == 1


def test_la_etiqueta_del_nombre_se_tine_sola_al_llegar_el_color(app):
    from descargador import colores_nombre as CN
    from descargador.ui import premium_estilos as PE
    ses = _SesionColores({"beto": "#FF7A45"})
    ctx = CtxFalso(ses)
    ctx.premium = P.GestorPremium(ctx)
    n = PE.nombre_efecto("Beto", "font-weight:700;", None, False, ctx=ctx, usuario="beto")
    assert isinstance(n, PE.NombreEfecto) and n.color is None
    esperar(app, lambda: n.color == "#FF7A45", "el color en la etiqueta")
    assert "color:#FF7A45" in n.styleSheet()
    # sin ctx ni color sigue siendo un QLabel de siempre
    simple = PE.nombre_efecto("Ana", "font-weight:700;")
    assert type(simple) is QLabel
    # con «brillo» el destello pasa sobre su color
    b = PE.NombreEfecto("Ana", "brillo", "", color="#22D3EE")
    g = PE._gradiente_texto("brillo", 0, 100, 0, False, b.color)
    assert QColor(g.stops()[0][1]).name().upper() == "#22D3EE"
    n.deleteLater()
    app.processEvents()
    g2 = CN.gestor(ctx)
    g2.cambiado.emit()                                       # una etiqueta borrada no rompe nada


# ================================================================== Personalizar › color del nombre

def test_personalizar_elige_y_guarda_el_color(app):
    from descargador.ui.personalizar_ajuste import SeccionPersonalizar
    ctx, g, ses = _premium(app)
    s = SeccionPersonalizar(ctx)
    assert set(s.botones_color) == {None} | {h for _n, h in D.PALETA_NOMBRE}
    assert s.botones_color[None].isChecked()                  # sin color al principio
    s.botones_color["#FFC857"].click()
    assert s.nombre.color == "#FFC857" and s.botones_color["#FFC857"].isChecked()
    assert g.color_nombre is None                             # todavía es la vista previa
    s.bt_aplicar.click()
    assert g.color_nombre == "#FFC857"
    esperar(app, lambda: {"color_nombre": "#FFC857"} in _patches(ses), "guardar el color")
    # un color propio (el diálogo de color se simula)
    from PySide6.QtWidgets import QColorDialog
    original = QColorDialog.getColor
    QColorDialog.getColor = staticmethod(lambda *a, **k: QColor("#123abc"))
    try:
        s.bt_color_propio.click()
    finally:
        QColorDialog.getColor = original
    assert s.sel_color == "#123ABC" and s.bt_color_propio.isChecked()
    assert not any(b.isChecked() for b in s.botones_color.values())
    s._quitar_todo()
    assert g.color_nombre is None and s.botones_color[None].isChecked()
    s.deleteLater()


def test_personalizar_sin_beneficios_deja_probar_el_color_pero_no_aplicarlo(app):
    from descargador.ui.personalizar_ajuste import SeccionPersonalizar
    ctx, g = _gratis()
    s = SeccionPersonalizar(ctx)
    s.botones_color["#FF5C8A"].click()
    assert s.nombre.color == "#FF5C8A"                         # se ve en la vista previa
    assert not s.bt_aplicar.isEnabled() and not s.caja_bloqueo.isHidden()
    assert g.color_nombre is None
    s.deleteLater()


# ================================================================== Más para donadores

def test_mas_donadores_con_candado_explica_como_conseguirlo(app):
    from descargador.ui.mas_donadores import CANDADO_DONADOR, CANDADO_PRUEBA, SeccionMasDonadores
    ctx, g = _gratis()
    s = SeccionMasDonadores(ctx)
    for fila in (s.fila_letra, s.fila_pared, s.fila_mascota):
        assert not fila.candado.isHidden() and fila.caja_explica.isHidden()
    assert s.bt_mascota.text().startswith("🔒") and s.casilla_pared.text().startswith("🔒")
    s.bt_letra.click()
    assert not s.fila_letra.caja_explica.isHidden() and s.fila_letra.et_explica.text() == CANDADO_PRUEBA
    s.casilla_pared.click()
    assert not s.casilla_pared.isChecked() and s.fila_pared.et_explica.text() == CANDADO_DONADOR
    s.bt_mascota.click()
    assert s.fila_mascota.et_explica.text() == CANDADO_DONADOR
    assert g.en_pared is False
    s.deleteLater()


def test_con_la_prueba_la_letra_se_abre_pero_la_pared_y_la_mascota_no(app):
    from descargador.ui.mas_donadores import SeccionMasDonadores
    ctx, g, ses = _premium(app, tipo="prueba")
    abiertas = []

    class _Ventana:
        def abrir_escena(self):
            abiertas.append(1)
    ctx.ventana = _Ventana()
    s = SeccionMasDonadores(ctx)
    assert s.fila_letra.candado.isHidden() and not s.fila_pared.candado.isHidden()
    s.bt_letra.click()
    assert abiertas == [1]
    s.casilla_pared.click()
    assert not s.casilla_pared.isChecked() and not s.fila_pared.caja_explica.isHidden()
    s.deleteLater()


def test_un_donador_marca_la_pared_y_pide_su_mascota_por_whatsapp(app, monkeypatch):
    from descargador.ui import mas_donadores as M
    ctx, g, ses = _premium(app)
    abiertas = []
    monkeypatch.setattr(M.QDesktopServices, "openUrl", staticmethod(lambda url: abiertas.append(url.toString()) or True))
    s = M.SeccionMasDonadores(ctx)
    assert s.fila_pared.candado.isHidden() and s.fila_mascota.candado.isHidden()
    assert not s.casilla_pared.isChecked()                  # apagada por defecto
    s.casilla_pared.click()
    assert g.en_pared is True
    esperar(app, lambda: {"en_pared": True} in _patches(ses), "guardar la casilla")
    s.casilla_pared.click()
    assert g.en_pared is False
    s.bt_mascota.click()
    assert len(abiertas) == 1
    u = urlparse(abiertas[0])
    assert u.netloc == "wa.me" and u.path == "/51902464984"
    assert parse_qs(u.query)["text"][0] == "Hola, soy @ana en Caudal. Quiero mi mascota personalizada."
    assert "aprueba por WhatsApp" in s.msg.text()
    s.deleteLater()


def test_la_tarjeta_de_la_pared_pregunta_una_sola_vez(app):
    from descargador.ui import mas_donadores as M

    class _Aj(dict):
        def guardar(self):
            pass
    ctx, g, ses = _premium(app)
    ctx.ajustes = _Aj()
    s = M.SeccionMasDonadores(ctx)
    assert not s.tarjeta_pared.isHidden() and s.bt_aparecer.objectName() == "principal"
    s.bt_ahora_no.click()
    assert s.tarjeta_pared.isHidden() and ctx.ajustes["pared_preguntado"] is True and g.en_pared is False
    s2 = M.SeccionMasDonadores(ctx)
    assert s2.tarjeta_pared.isHidden()                       # ya respondió: no vuelve a salir
    s2.deleteLater()
    s.deleteLater()
    ctx.ajustes = _Aj()
    s3 = M.SeccionMasDonadores(ctx)
    s3.bt_aparecer.click()
    assert s3.tarjeta_pared.isHidden() and ctx.ajustes["pared_preguntado"] is True
    esperar(app, lambda: {"en_pared": True} in _patches(ses), "guardar la pared desde la tarjeta")
    assert g.en_pared is True and s3.casilla_pared.isChecked()
    s3.deleteLater()


def test_la_pared_se_pinta_con_fundadores_colores_y_estado_vacio(app, monkeypatch):
    from descargador.ui import mas_donadores as M
    ses = SesionFalsa({"pared_agradecimiento": [
        {"usuario": "funda", "nombre": "Fundadora", "tipo": "fundador", "color": "#FFC857"},
        {"usuario": "dona", "nombre": "Dona", "tipo": "donador", "color": None}]})
    ctx = CtxFalso(ses)
    d = M.DialogoPared(ctx)
    esperar(app, lambda: d.lista.count() == 3, "la pared")
    textos = [lb.text() for lb in d.contenido.findChildren(QLabel)]
    assert "Fundadora" in textos and "Dona" in textos and "Fundador" in textos and "@dona" in textos
    fund = [lb for lb in d.contenido.findChildren(QLabel) if lb.text() == "Fundadora"][0]
    assert "#FFC857" in fund.styleSheet()
    d.pintar([])
    assert "Todavía no hay nadie" in d.estado.text() and d.lista.count() == 1
    d._fallo(nube.SinConexion("sin red"))
    assert d.estado.text()
    d.deleteLater()
    # sin sesión, la pared se lee igual (es pública)
    llamadas = []
    monkeypatch.setattr(M.S, "pared_agradecimiento_publica", lambda: llamadas.append(1) or [])
    sin = CtxFalso(None)
    sin.cuenta = {}
    d2 = M.DialogoPared(sin)
    esperar(app, lambda: llamadas, "la pared pública")
    d2.deleteLater()


# ================================================================== letra con efectos

def test_las_entradas_de_cada_estilo_empiezan_apagadas_y_terminan_puestas():
    from descargador.ui import letra_escena as E
    for estilo in D.ESTILOS_ESCENA:
        n = len(E.unidades_de(estilo, "Cuando la noche cae sobre la ciudad"))
        inicio = E.entrada(estilo, 0.0, n)
        fin = E.entrada(estilo, 5.0, n)
        por_piezas = E.POR_PALABRAS + E.POR_LETRAS
        assert len(inicio) == len(fin) == (n if estilo in por_piezas else 1)
        assert all(abs(E.giro_de(estilo, 5.0, i)) < 0.01 for i in range(n)), estilo
        assert all(abs(e - 1.0) < 0.01 for _a, _s, e in fin), estilo
        assert max(a for a, _s, _e in inicio) < 0.3, estilo          # al entrar todavía no se ve
        assert all(a > 0.95 and abs(s) < 0.01 for a, s, _e in fin), estilo
        assert not E.termino_entrada(estilo, 0.0, n) and E.termino_entrada(estilo, 5.0, n)
    assert E.unidades_de("ola", "uno dos  tres") == ["uno", "dos", "tres"]
    assert E.unidades_de("cine", "a b") == ["a", "b"]
    assert E.unidades_de("resplandor", "a b") == ["a b"] == E.unidades_de("zoom", "a b")
    assert E.unidades_de("giro", "uno dos") == ["uno", "dos"]
    assert E.unidades_de("maquina", "a b") == ["a", "b"] == E.unidades_de("lluvia", "a b")


def test_los_efectos_nuevos_entran_como_dicen():
    from descargador.ui import letra_escena as E
    # zoom: de enorme a su tamaño, pasándose un poco de pequeño (el golpe)
    escalas = [E.entrada("zoom", t / 100, 1)[0][2] for t in range(0, 60)]
    assert escalas[0] > 2 and min(escalas) < 0.98 and abs(escalas[-1] - 1) < 0.01
    # máquina: tecla a tecla, en orden, y nunca tarda más de lo previsto
    assert E.letras_escritas(0.0, 30) == 0 and E.letras_escritas(9.0, 30) == 30
    escritas = [E.letras_escritas(t / 100, 30) for t in range(0, 200, 5)]
    assert escritas == sorted(escritas)
    a = [x[0] for x in E.entrada("maquina", 0.3, 30)]
    assert a[0] == 1.0 and a[-1] == 0.0
    assert E.termino_entrada("maquina", E.MAQUINA_TOTAL + 0.05, 300)
    # lluvia: cae desde arriba y rebota (la altura sube y baja más de una vez)
    alturas = [E.entrada("lluvia", t / 100, 1)[0][1] for t in range(0, 90)]
    assert alturas[0] > 1.2 and abs(alturas[-1]) < 0.01
    rebotes = sum(1 for x, y in zip(alturas, alturas[1:]) if y > x + 0.001)
    assert rebotes > 3
    assert E.termino_entrada("lluvia", E.LLUVIA_TOTAL + 0.2, 200)
    # giro: entra torcida, cada palabra hacia un lado, y acaba derecha
    assert abs(E.giro_de("giro", 0.0, 0)) > 45 and E.giro_de("giro", 0.0, 0) * E.giro_de("giro", 0.085, 1) < 0
    assert E.giro_de("ola", 0.0, 0) == 0.0


def test_la_ola_entra_palabra_por_palabra_y_el_neon_parpadea():
    from descargador.ui import letra_escena as E
    a = E.entrada("ola", 0.15, 4)
    assert a[0][0] > a[1][0] > a[3][0]                 # la primera palabra va por delante
    vistos = [E.parpadeo_neon(t / 100) for t in range(0, 45)]
    subidas = sum(1 for x, y in zip(vistos, vistos[1:]) if y > x + 0.3)
    assert subidas >= 2                                # se enciende, se apaga y se vuelve a encender
    assert E.parpadeo_neon(2.0) == 1.0
    assert E.salida_de(0.0) == (1.0, 0.0) and E.salida_de(5.0)[0] == 0.0
    # cine: una línea larga no tarda más de lo previsto
    n = 80
    assert E.termino_entrada("cine", E.CINE_TOTAL + 0.01, n)


class _R(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = {"clave": "k1", "titulo": "Medianoche", "artista": "Las Estrellas", "miniatura": "u1"}
        self.estado = "sonando"
        self.velocidad = 1.0
        self._posicion = 12.2

    def anterior(self):
        pass

    def siguiente(self):
        pass

    def alternar(self):
        pass

    def buscar(self, s):
        pass

    def mover(self, seg):
        self._posicion = seg
        self.posicion_cambio.emit(seg)


class _Aj(dict):
    def guardar(self):
        self.guardado = True

    def __getitem__(self, k):
        return self.get(k)


class _Prem(QObject):
    cambiado = Signal()

    def __init__(self):
        super().__init__()
        self.premium = True


class _Gamer:
    ahorrando = False


class _CtxLetra(QObject):
    def __init__(self):
        super().__init__()
        self.reproductor = _R()
        self.ajustes = _Aj(traducir_letra=False, colores_caratula=True)
        self.premium = _Prem()
        self.gamer = _Gamer()
        self.ventana = None


LRC = [(0, ""), (12000, "Cuando la noche cae sobre la ciudad entera"), (16000, "y las luces se encienden"),
       (20500, "te busco entre la gente"), (24000, ""), (40000, "baila conmigo")]


def _caratula():
    img = QImage(200, 200, QImage.Format_RGB32)
    p = QPainter(img)
    p.fillRect(0, 0, 100, 200, QColor("#E11D48"))
    p.fillRect(100, 0, 100, 200, QColor("#7C3AED"))
    p.end()
    return img


def _bombear(app, seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture
def escena(app, monkeypatch):
    from descargador import catalogo, paleta_caratula
    from descargador.ui import imagenes, letra_escena as E, letra_viva as L
    paleta_caratula.CACHE.clear()
    L.CACHE_LETRAS.clear()
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": LRC, "texto": "",
                                                       "fuente": "LRCLIB"})
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(_caratula()))
    monkeypatch.setattr(imagenes, "pedir", lambda *a, **k: None)
    ctx = _CtxLetra()
    w = E.PaginaLetraEscena(ctx)
    w.resize(1280, 720)
    w.ctx_falso = ctx
    yield w
    w.hide()
    w.deleteLater()


def _pintar(w):
    img = QImage(w.lienzo.size(), QImage.Format_ARGB32)
    img.fill(0)
    w.lienzo.render(img)
    return img


def test_el_verso_actual_entra_animado_y_cambia_con_la_musica(app, escena):
    w = escena
    w.r.mover(12.2)
    w.show()
    lc = w.lienzo
    esperar(app, lambda: lc.sincronizada and lc._actual == 1, "el primer verso")
    assert lc._tam_verso() >= 34 and lc._tam_verso() > 80          # grande a 1280 px
    w.r.mover(16.1)
    esperar(app, lambda: lc._actual == 2, "el verso siguiente")
    assert lc._anterior == 1                                        # el anterior se va, el nuevo entra
    assert lc._moviendo                                             # mientras entra, cuadros fluidos
    esperar(app, lambda: not lc._moviendo, "que termine de entrar")  # luego, el ritmo tranquilo
    img = _pintar(w)
    assert not img.isNull()


def test_se_puede_elegir_estilo_y_se_guarda(app, escena):
    w = escena
    w.r.mover(12.2)
    w.show()
    esperar(app, lambda: w.lienzo._actual == 1, "el primer verso")
    assert w.lienzo.estilo == "resplandor" and "Resplandor" in w.bt_estilo.text()
    for clave in D.ESTILOS_ESCENA:
        w.elegir_estilo(clave)
        assert w.lienzo.estilo == clave and w.ctx_falso.ajustes["letra_escena_estilo"] == clave
        assert D.NOMBRES_ESCENA[clave] in w.bt_estilo.text()
        _bombear(app, 0.05)
        assert not _pintar(w).isNull()                              # cada estilo se pinta sin errores
    from PySide6.QtTest import QTest
    QTest.keyClick(w, Qt.Key_2)
    assert w.lienzo.estilo == "ola"
    QTest.keyClick(w, Qt.Key_8)
    assert w.lienzo.estilo == "giro"
    QTest.keyClick(w, Qt.Key_9)                                     # no hay noveno: no pasa nada
    assert w.lienzo.estilo == "giro"
    # cada efecto se pinta a media entrada, con el verso ya puesto y con otro tipo de letra
    import time
    from descargador.ui import tipografia_letra as T
    try:
        for fuente in ("predeterminada", "marker"):
            T.fijar(fuente)
            for clave in D.ESTILOS_ESCENA:
                w.elegir_estilo(clave)
                for hace in (0.05, 0.3, 3.0):
                    w.lienzo._t_cambio = time.monotonic() - hace
                    assert not _pintar(w).isNull()
    finally:
        T.fijar("predeterminada")


def test_el_resplandor_usa_los_colores_de_la_caratula(app, escena):
    w = escena
    w.r.mover(12.2)
    w.show()
    esperar(app, lambda: w.colores.fuerza > 0.9 and not w.colores.animando and w.lienzo._actual == 1,
            "los colores de la carátula")
    # el lienzo pinta con la paleta de la carátula (a lo sumo unos tonos de diferencia por la transición)
    for c, h in zip(w.lienzo.paleta, w.colores.hex_actuales()):
        e = QColor(h)
        assert max(abs(c.red() - e.red()), abs(c.green() - e.green()), abs(c.blue() - e.blue())) <= 24, (c.name(), h)
    img = _pintar(w)
    # el centro, detrás del verso, lleva color (no es gris ni negro)
    c = QColor(img.pixel(int(img.width() * 0.2), int(img.height() * 0.46)))
    assert c.hsvSaturationF() > 0.2


def test_tramo_instrumental_y_letra_sin_tiempos(app, escena, monkeypatch):
    w = escena
    w.r.mover(30.0)
    w.show()
    lc = w.lienzo
    esperar(app, lambda: lc._actual >= 0, "el tramo instrumental")
    assert lc.lineas[lc._actual]["pausa"]
    assert not _pintar(w).isNull()
    lc._poner_lineas([{"ms": None, "texto": "hola", "pausa": False}], False, "")
    _pintar(w)
    assert "no trae tiempos" in lc.mensaje


def test_sin_beneficios_la_vista_se_cierra_sola(app, escena):
    w = escena
    w.show()
    cerrada = []
    w.volver.connect(lambda: cerrada.append(1))
    w.ctx_falso.premium.premium = False
    w.ctx_falso.premium.cambiado.emit()
    assert cerrada == [1]
