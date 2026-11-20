# -*- coding: utf-8 -*-
"""Lo premium de la cuenta (estado con vencimientos, pase de prueba, personalización y temas de colores).

Sin internet ni ventanas (Qt offscreen), con los datos de la app en una carpeta temporal y una sesión de la
nube falsa que contesta lo que contestaría la base de datos."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import nube  # noqa: E402
from descargador import premium as P  # noqa: E402
from descargador import premium_datos as D  # noqa: E402
from descargador import social as S  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    yield tmp_path


def esperar(app, cond, que, maximo=10):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class SesionFalsa:
    user_id = "yo-id"
    access = "token"

    def __init__(self, datos=None, sin_red=False):
        self.datos = datos or {}
        self.sin_red = sin_red
        self.llamadas = []

    def rpc(self, nombre, **p):
        if self.sin_red:
            raise nube.SinConexion("sin red")
        self.llamadas.append((nombre, p))
        r = self.datos.get(nombre)
        return r(p) if callable(r) else r

    def pedir(self, metodo, ruta, **kw):
        if self.sin_red:
            raise nube.SinConexion("sin red")
        self.llamadas.append((metodo, ruta, kw))
        r = self.datos.get(f"{metodo} perfiles")
        return r(kw) if callable(r) else r


class CtxFalso(QObject):
    aviso = Signal(str)

    def __init__(self, sesion):
        super().__init__()
        from descargador.config import Ajustes
        self.ajustes = Ajustes()
        self.cuenta = {"usuario": "ana", "nombre": "Ana", "sesion": sesion}
        self.ventana = None


def _ctx(sesion):
    return CtxFalso(sesion)


# ------------------------------------------------------------------ datos puros

def test_validadores_aceptan_lo_conocido_y_nada_mas():
    assert D.marco_valido("AURORA") == "aurora"
    assert D.marco_valido("hackeado") == "ninguno" and D.marco_valido(None) == "ninguno"
    assert D.efecto_valido(" Neon ") == "neon" and D.efecto_valido("x") == "ninguno"
    assert D.tema_valido("oceano") == "oceano" and D.tema_valido("rosa") == "ninguno"
    assert len(D.MARCOS) == 8 and len(D.EFECTOS) == 5 and len(D.TEMAS) == 20   # «ninguno» + 19 temas


def test_estado_prueba_vigente_y_vencida():
    ahora = 1_800_000_000.0
    en_3 = EstadoDe(ahora + 3 * 86400 - 100)
    assert en_3.vigente(ahora) and en_3.dias_restantes(ahora) == 3
    assert EstadoDe(ahora + 60).dias_restantes(ahora) == 1            # menos de un día: «1 día»
    vencida = EstadoDe(ahora - 1)
    assert not vencida.vigente(ahora) and vencida.dias_restantes(ahora) is None


def EstadoDe(vence):
    return D.EstadoPremium(True, "prueba", vence)


def test_donador_y_fundador_no_vencen():
    for tipo in ("donador", "fundador"):
        e = D.EstadoPremium(True, tipo, None)
        assert e.vigente(time.time() + 10 ** 9) and e.dias_restantes() is None
    assert not D.EstadoPremium(False, None, None).vigente()


def test_estado_desde_servidor_lee_iso_y_tolera_basura():
    vence = datetime.now(timezone.utc) + timedelta(days=5)
    e = D.EstadoPremium.desde_servidor({"premium": True, "tipo": "prueba", "vence": iso(vence)})
    assert e.vigente() and e.dias_restantes() in (5, 6)
    assert not D.EstadoPremium.desde_servidor(None).premium
    raro = D.EstadoPremium.desde_servidor({"premium": True, "tipo": "mago", "vence": "ayer"})
    assert raro.tipo is None and raro.vence is None and raro.vigente()


def test_codigo_se_normaliza_solo():
    assert D.limpiar_codigo("ab12 cd34") == "AB12-CD34"
    assert D.limpiar_codigo("ab1") == "AB1"
    assert D.limpiar_codigo("  ") == ""
    assert D.limpiar_codigo("abcd-efgh-extra") == "ABCD-EFGH"
    assert D.codigo_completo("abcd1234") and not D.codigo_completo("abc")


def test_texto_de_vencimiento():
    assert "mañana" in D.texto_vencimiento(1)
    assert D.texto_vencimiento(4) == "Tu prueba de donador vence en 4 días"
    assert D.texto_vencimiento(None) == ""


# ------------------------------------------------------------------ social: lo que llega de la nube

def test_perfil_y_personas_traen_marco_y_efecto_ya_validados():
    p = S.perfil_limpio({"id": "x", "usuario": "ana", "marco": "oro", "efecto_nombre": "arcoiris"})
    assert (p["marco"], p["efecto_nombre"]) == ("oro", "arcoiris")
    assert S.perfil_limpio({"id": "x"})["marco"] == "ninguno"                    # falta → ninguno
    assert S.perfil_limpio({"marco": "<script>"})["marco"] == "ninguno"          # basura → ninguno
    per = S.persona_limpia({"id": "u", "usuario": "bea", "marco": "fuego", "efecto_nombre": "neon"})
    assert (per["marco"], per["efecto_nombre"]) == ("fuego", "neon")
    from descargador import listas_compartidas as LC
    assert LC._persona({"id": "u", "marco": "hielo"})["marco"] == "hielo"


# ------------------------------------------------------------------ temas de colores

def _ratio(a, b):
    from descargador.ui import estilos as E
    la, lb = sorted((E._luz(E._rgb(a)), E._luz(E._rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("tema", [t for t in D.TEMAS if t != "ninguno"])
def test_temas_premium_cumplen_contraste_AA(tema):
    from descargador.ui import estilos as E
    clave = "premium_" + tema
    assert E.es_premium(clave)
    f, a = E.fondo_de(clave), E.acento_de(clave)
    capas = f[1:]
    assert len(capas) == 7
    for capa in capas[:5]:                         # fondo, panel y las tres superficies
        assert _ratio(E.C["texto"], capa) >= 4.5
        assert _ratio(E.C["texto2"], capa) >= 4.5
        assert _ratio(E.C["texto3"], capa) >= 4.5
        assert _ratio(a[1], capa) >= 4.5           # el acento como texto o icono sobre cada superficie
    assert _ratio(a[4], a[1]) >= 4.5               # lo que se escribe sobre un botón de acento
    assert _ratio(a[4], a[3]) >= 3.0


def test_los_temas_premium_no_se_cuelan_en_el_selector_normal():
    from descargador.ui import estilos as E
    assert not any(k.startswith("premium_") for k in E.ACENTOS) and not any(k.startswith("premium_") for k in E.FONDOS)
    assert E.es_premium("premium_ambar") and not E.es_premium("premium_inventado") and not E.es_premium("cian")


def test_aplicar_aspecto_con_un_tema_premium_y_volver():
    from descargador.ui import estilos as E
    original = dict(E.C), dict(E.ACTUAL)
    try:
        E.aplicar_aspecto("premium_sakura", "premium_sakura")
        assert E.C["acento"].upper() == "#F472B6" and E.C["fondo"].upper() == "#160B12"
        E.aplicar_aspecto("cian", "oscuro")
        assert E.C["fondo"].upper() == "#06070A"
        E.aplicar_aspecto("premium_nunca", "premium_nunca")      # una clave rara no rompe nada
        assert E.C["acento"] == E.acento_de("cian")[1]
    finally:
        E.C.update(original[0])
        E.ACTUAL.update(original[1])


# ------------------------------------------------------------------ gestor (nube falsa, siempre en segundo plano)

def _sesion_prueba(dias=5, tipo="prueba"):
    vence = datetime.now(timezone.utc) + timedelta(days=dias)
    return SesionFalsa({
        "mi_premium": {"premium": True, "tipo": tipo, "vence": iso(vence) if tipo == "prueba" else None},
        "GET perfiles": [{"marco": "aurora", "efecto_nombre": "brillo", "tema_premium": "oceano"}],
        "PATCH perfiles": [{}],
    })


def test_refrescar_trae_estado_y_personalizacion_sin_bloquear(app):
    ctx = _ctx(_sesion_prueba())
    g = P.GestorPremium(ctx)
    assert not g.premium                              # arranca sin saber nada (copia local vacía)
    g.refrescar()
    esperar(app, lambda: g.premium, "estado premium")
    assert g.tipo == "prueba" and g.dias_de_prueba() in (4, 5)
    assert (g.marco, g.efecto, g.tema) == ("aurora", "brillo", "oceano")
    assert (g.marco_efectivo(), g.efecto_efectivo(), g.tema_efectivo()) == ("aurora", "brillo", "oceano")


def test_la_copia_local_se_ve_al_instante_en_el_siguiente_arranque(app):
    g = P.GestorPremium(_ctx(_sesion_prueba(tipo="donador")))
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    g2 = P.GestorPremium(_ctx(SesionFalsa(sin_red=True)))      # sin red: lo que ya se sabía
    assert g2.premium and g2.marco == "aurora" and g2.tipo == "donador"


def test_sin_red_no_rompe_ni_borra_lo_guardado(app):
    g = P.GestorPremium(_ctx(_sesion_prueba(tipo="donador")))
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    g.ctx.cuenta["sesion"] = SesionFalsa(sin_red=True)
    g.refrescar()
    for _ in range(30):
        app.processEvents()
        time.sleep(0.01)
    assert g.premium and g.marco == "aurora"


def test_si_falla_al_abrir_se_reintenta_solo_hasta_traer_los_beneficios(app, monkeypatch):
    # al abrir hay mucho tráfico: si la primera pregunta falla, un fundador no puede quedarse sin nada
    monkeypatch.setattr(P.GestorPremium, "ESPERAS_REINTENTO_S", (0, 0, 0))
    ses = _sesion_prueba(tipo="fundador")
    ses.sin_red = True
    g = P.GestorPremium(_ctx(ses))
    g.refrescar()
    esperar(app, lambda: g._fallos_seguidos >= 1, "primer fallo")
    assert not g.premium
    ses.sin_red = False                                  # vuelve la red: el reintento lo trae solo
    esperar(app, lambda: g.premium, "estado tras reintento")
    assert g.tipo == "fundador" and g._fallos_seguidos == 0
    assert g._periodico.isActive()                       # y se sigue preguntando de vez en cuando


def test_una_prueba_vencida_no_pinta_nada_aunque_quede_guardado(app):
    g = P.GestorPremium(_ctx(SesionFalsa()))
    g.estado = D.EstadoPremium(True, "prueba", time.time() - 10)
    g.marco, g.efecto, g.tema = "oro", "neon", "ambar"
    assert not g.premium
    assert (g.marco_efectivo(), g.efecto_efectivo(), g.tema_efectivo()) == ("ninguno",) * 3


def test_guardar_personalizacion_aplica_el_tema_y_sube_a_la_nube(app):
    ses = _sesion_prueba(tipo="donador")
    ctx = _ctx(ses)
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "rosa", "noche"
    g = P.GestorPremium(ctx)
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    assert g.guardar_personalizacion("galaxia", "neon", "medianoche") is True
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("premium_medianoche", "premium_medianoche")
    assert g.aspecto_previo == ["rosa", "noche"]                # lo de antes se recuerda
    esperar(app, lambda: any(ll[0] == "PATCH" for ll in ses.llamadas), "se sube al perfil")
    cuerpo = [ll for ll in ses.llamadas if ll[0] == "PATCH"][-1][2]["json"]
    assert cuerpo == {"marco": "galaxia", "efecto_nombre": "neon", "tema_premium": "medianoche"}
    # quitar el tema devuelve lo que tenía
    assert g.guardar_personalizacion(tema="ninguno") is True
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("rosa", "noche")


def test_sin_beneficios_no_se_guarda_nada(app):
    ses = SesionFalsa({"mi_premium": {"premium": False}})
    g = P.GestorPremium(_ctx(ses))
    assert g.guardar_personalizacion("oro", "neon", "ambar") is False
    assert g.marco == "ninguno" and not any(ll[0] == "PATCH" for ll in ses.llamadas)


def test_al_perder_los_beneficios_el_tema_vuelve_a_lo_normal(app):
    ctx = _ctx(_sesion_prueba(tipo="donador"))
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "verde", "bosque"
    g = P.GestorPremium(ctx)
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    g.guardar_personalizacion(tema="atardecer")
    assert ctx.ajustes["fondo"] == "premium_atardecer"
    perdidos = []
    g.aspecto_cambiado.connect(lambda: perdidos.append(1))
    g._aplicar_remoto(D.EstadoPremium(False), {"marco": "ninguno", "efecto_nombre": "ninguno",
                                               "tema_premium": "ninguno"})
    assert perdidos == [1]
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("verde", "bosque")


def test_revertir_en_el_arranque_con_la_copia_local(app):
    ctx = _ctx(SesionFalsa())
    g = P.GestorPremium(ctx)
    g.estado = D.EstadoPremium(True, "prueba", time.time() + 86400)
    g.tema, g.aspecto_previo = "sakura", ["azul", "grafito"]
    g._guardar_local()
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "premium_sakura", "premium_sakura"
    assert P.revertir_aspecto_si_hace_falta(ctx.ajustes) is False        # sigue vigente: se queda
    g.estado = D.EstadoPremium(True, "prueba", time.time() - 5)           # venció mientras estaba cerrada
    g._guardar_local()
    assert P.revertir_aspecto_si_hace_falta(ctx.ajustes) is True
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("azul", "grafito")
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "rosa", "noche"
    assert P.revertir_aspecto_si_hace_falta(ctx.ajustes) is False        # un aspecto normal no se toca


def test_canjear_ok_actualiza_el_estado(app):
    ses = SesionFalsa({
        "canjear_pase": lambda p: {"ok": True, "mensaje": "¡Listo!", "dias": 7,
                                   "vence": iso(datetime.now(timezone.utc) + timedelta(days=7))},
        "mi_premium": {"premium": True, "tipo": "prueba",
                       "vence": iso(datetime.now(timezone.utc) + timedelta(days=7))},
    })
    g = P.GestorPremium(_ctx(ses))
    res = []
    g.canjear("ABCD-1234", ok=res.append)
    esperar(app, lambda: res, "respuesta del canje")
    assert res[0]["ok"] and g.premium and g.tipo == "prueba"
    assert ("canjear_pase", {"p_codigo": "ABCD-1234"}) in ses.llamadas


def test_canjear_con_codigo_malo_no_cambia_nada(app):
    ses = SesionFalsa({"canjear_pase": {"ok": False, "mensaje": "Ese código ya se usó."}})
    g = P.GestorPremium(_ctx(ses))
    res = []
    g.canjear("ZZZZ-0000", ok=res.append)
    esperar(app, lambda: res, "respuesta")
    assert not res[0]["ok"] and res[0]["mensaje"] == "Ese código ya se usó." and not g.premium


def test_canjear_sin_red_avisa(app):
    g = P.GestorPremium(_ctx(SesionFalsa(sin_red=True)))
    fallos = []
    g.canjear("ZZZZ-0000", error=fallos.append)
    esperar(app, lambda: fallos, "error")
    assert isinstance(fallos[0], nube.SinConexion)


def test_aviso_discreto_de_vencimiento_una_vez_al_dia(app):
    ctx = _ctx(_sesion_prueba(dias=2))
    avisos = []
    ctx.aviso.connect(avisos.append)
    g = P.GestorPremium(ctx)
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    app.processEvents()
    assert len(avisos) == 1 and "vence" in avisos[0]
    g._aplicar_remoto(D.EstadoPremium(True, "prueba", time.time() + 86400), None)   # otro cambio el mismo día
    assert len(avisos) == 1


def test_al_canjear_se_desbloquean_el_fondo_y_la_mascotita(app):
    class FondoFalso:
        llamadas = 0

        def verificar_permiso(self):
            FondoFalso.llamadas += 1
    ses = SesionFalsa({"canjear_pase": {"ok": True, "mensaje": "ok", "dias": 7},
                       "mi_premium": {"premium": True, "tipo": "prueba",
                                      "vence": iso(datetime.now(timezone.utc) + timedelta(days=7))}})
    ctx = _ctx(ses)
    ctx.fondo = FondoFalso()
    g = P.GestorPremium(ctx)
    res = []
    g.canjear("ABCD-1234", ok=res.append)
    esperar(app, lambda: res, "canje")
    assert FondoFalso.llamadas == 1                           # el permiso del fondo (y el de la mascota) se vuelve a mirar


def test_elegir_colores_normales_a_mano_deja_de_aplicar_el_tema(app):
    ses = _sesion_prueba(tipo="donador")
    ctx = _ctx(ses)
    g = P.GestorPremium(ctx)
    g.refrescar()
    esperar(app, lambda: g.premium, "estado")
    assert ctx.ajustes["fondo"] == "premium_oceano"           # el tema guardado en el perfil se puso solo
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "rosa", "negro"
    g.aspecto_elegido_a_mano()
    assert g.tema == "ninguno"
    g._aplicar_remoto(g.estado, {"marco": "aurora", "efecto_nombre": "brillo", "tema_premium": "ninguno"})
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("rosa", "negro")      # y ya no se vuelve a pisar
