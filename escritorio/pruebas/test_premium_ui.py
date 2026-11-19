# -*- coding: utf-8 -*-
"""Lo premium que se ve: marcos animados, nombre con efecto, Personalizar, canje de código y Ajustes sin bloqueo.

Qt offscreen, datos en carpeta temporal y nube falsa (como test_fondo_app.py y test_premium.py)."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from descargador import nube  # noqa: E402
from descargador import premium as P  # noqa: E402
from descargador import premium_datos as D  # noqa: E402
from descargador.ui import premium_estilos as PE  # noqa: E402
from test_premium import CtxFalso, SesionFalsa, esperar, iso  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    # en Qt offscreen la aplicación no siempre cuenta como «activa»: aquí sí, para probar el reloj
    monkeypatch.setattr(QApplication, "applicationState", lambda self: Qt.ApplicationActive)
    yield tmp_path


@pytest.fixture(autouse=True)
def reloj_limpio():
    r = PE.reloj()
    for w in list(r._vivos):
        r.quitar(w)
    yield


def _gestor_premium(app, tipo="donador", extra=None):
    vence = datetime.now(timezone.utc) + timedelta(days=6)
    datos = {"mi_premium": {"premium": True, "tipo": tipo, "vence": iso(vence) if tipo == "prueba" else None},
             "GET perfiles": [{"marco": "ninguno", "efecto_nombre": "ninguno", "tema_premium": "ninguno"}],
             "PATCH perfiles": [{}]}
    datos.update(extra or {})
    ses = SesionFalsa(datos)
    ctx = CtxFalso(ses)
    g = P.GestorPremium(ctx)
    ctx.premium = g
    g.refrescar()
    esperar(app, lambda: g.premium, "estado premium")
    return ctx, g, ses


def _gestor_gratis():
    ctx = CtxFalso(SesionFalsa({"mi_premium": {"premium": False}}))
    ctx.premium = P.GestorPremium(ctx)
    return ctx, ctx.premium


# ------------------------------------------------------------------ avatar con marco

def test_avatar_sin_marco_se_dibuja_como_siempre(app):
    from descargador.ui.paginas import perfil_comun as PC
    assert PC.Avatar(48, "Ana", "#7C5CFF", None)._margen() == 0
    assert PC.Avatar(148, "Ana", "#7C5CFF", None, anillo="#101217")._margen() == 3
    a = PC.Avatar(48, "Ana", "#7C5CFF", None, marco="inventado")        # una clave rara no pinta nada
    assert a.marco == "ninguno"


@pytest.mark.parametrize("marco", [m for m in D.MARCOS if m != "ninguno"])
def test_cada_marco_pinta_un_anillo_y_la_foto_queda_dentro(app, marco):
    from descargador.ui.paginas import perfil_comun as PC
    av = PC.Avatar(96, "Ana", "#7C5CFF", None, anillo="#101217", marco=marco, marco_siempre=True)
    av.show()
    img = av.grab().toImage()
    ancho = PE.ancho_marco(96)
    # a media altura, en el borde izquierdo: ahí está el anillo (opaco y con color del marco)
    anillo = img.pixelColor(int(3 + ancho / 2), 48)
    assert anillo.alpha() == 255 and anillo.name() != "#7c5cff"          # el anillo no es el color del perfil
    # el interior sigue siendo la inicial sobre el color del perfil
    assert img.pixelColor(48, 30).name() == "#7c5cff"
    assert av._margen() == pytest.approx(3 + ancho)
    av.close()


def test_set_marco_cambia_el_margen_y_la_vista(app):
    from descargador.ui.paginas import perfil_comun as PC
    av = PC.Avatar(80, "Ana", "#7C5CFF", None)
    av.show()
    base = av._margen()
    av.set_marco("oro")
    assert av._margen() > base and av.marco == "oro"
    av.set_marco("ninguno")
    assert av._margen() == base
    av.close()


# ------------------------------------------------------------------ el reloj único y ligero

def test_el_reloj_duerme_si_no_hay_nada_que_animar(app):
    from descargador.ui.paginas import perfil_comun as PC
    r = PE.reloj()
    assert not r.activo
    sin = PC.Avatar(48, "Ana", None, None)
    sin.show()
    assert not r.activo                                            # sin marco no hay reloj
    con = PC.Avatar(48, "Ana", None, None, marco="aurora")
    con.show()
    assert r.activo and r.cuantos() == 1
    con.hide()
    assert not r.activo and r.cuantos() == 0                       # al ocultarse se apaga solo
    sin.close()
    con.close()


def test_el_reloj_va_a_30_fps_como_mucho(app):
    assert PE.reloj()._timer.interval() >= 33 and PE.FPS <= 30


def test_con_muchos_avatares_los_marcos_se_quedan_quietos_salvo_el_perfil(app):
    from descargador.ui.paginas import perfil_comun as PC
    r = PE.reloj()
    lista = [PC.Avatar(40, f"P{i}", None, None, marco="neon") for i in range(PE.MAX_ANIMADOS + 3)]
    for a in lista:
        a.show()
    perfil = PC.Avatar(148, "Yo", None, None, marco="oro", marco_siempre=True)
    perfil.show()
    r.t = 12.34
    assert all(not r.se_anima(a) for a in lista) and r.se_anima(perfil)
    assert r.angulo(lista[0], 0.2) == PE.ANGULO_QUIETO               # quietos
    assert r.angulo(perfil, 0.2) != PE.ANGULO_QUIETO                 # el perfil sigue girando
    for a in lista[PE.MAX_ANIMADOS - 3:]:
        a.hide()                                                    # queda una lista corta: vuelven a moverse
    assert all(r.se_anima(a) for a in lista[:PE.MAX_ANIMADOS - 3])
    for a in lista + [perfil]:
        a.close()


def test_el_tic_solo_repinta_lo_visible_y_no_corre_con_la_ventana_minimizada(app, monkeypatch):
    from descargador.ui.paginas import perfil_comun as PC
    r = PE.reloj()
    av = PC.Avatar(60, "Ana", None, None, marco="fuego", marco_siempre=True)
    av.show()
    pintados = []
    monkeypatch.setattr(av, "update", lambda *a: pintados.append(1))
    antes = r.tics
    r.tic()
    assert r.tics == antes + 1 and pintados == [1]
    monkeypatch.setattr(QApplication, "applicationState", lambda self: Qt.ApplicationInactive)
    r.tic()                                                         # otra aplicación al frente: no gasta nada
    assert r.tics == antes + 1 and pintados == [1]
    av.close()


# ------------------------------------------------------------------ nombre con efecto

@pytest.mark.parametrize("efecto", ["brillo", "degradado", "arcoiris", "neon"])
def test_cada_efecto_pinta_el_nombre_con_varios_colores(app, efecto):
    n = PE.NombreEfecto("Ana Lucía", efecto, "font-size:26px;font-weight:900;", siempre=True)
    n.resize(280, 46)
    n.show()
    img = n.grab().toImage()
    colores = {img.pixelColor(x, y).name() for x in range(0, 280, 3) for y in range(8, 38, 3)}
    assert len(colores) > 6
    n.close()


def test_nombre_largo_se_recorta_sin_salirse_de_su_caja(app):
    n = PE.NombreEfecto("Un nombre larguísimo que no cabe en la caja", "degradado", "font-size:20px;font-weight:800;")
    n.setFixedSize(90, 34)
    n.show()
    img = n.grab().toImage()
    assert img.width() == 90 and img.height() == 34
    n.close()


def test_sin_efecto_es_una_etiqueta_normal_y_el_reloj_solo_corre_con_los_animados(app):
    r = PE.reloj()
    normal = PE.nombre_efecto("Ana", "font-size:14px;", "ninguno")
    assert type(normal) is QLabel
    degradado = PE.NombreEfecto("Ana", "degradado")
    degradado.show()
    assert not r.activo                                              # el degradado es fijo: no pide reloj
    brillo = PE.NombreEfecto("Ana", "brillo")
    brillo.show()
    assert r.activo
    brillo.set_efecto("ninguno")
    assert not r.activo
    brillo.set_efecto("arcoiris")
    assert r.activo
    brillo.hide()
    assert not r.activo
    for w in (normal, degradado, brillo):
        w.close()


# ------------------------------------------------------------------ fila de persona (Amigos, Mensajes, etc.)

def test_fila_de_persona_muestra_marco_y_efecto(app):
    from descargador.ui.paginas import amigos
    from descargador.ui.paginas import perfil_comun as PC
    f = amigos.fila_persona({"id": "1", "usuario": "bea", "nombre": "Bea", "foto_url": None,
                             "marco": "galaxia", "efecto_nombre": "arcoiris"})
    f.resize(340, 60)
    f.show()
    av = f.findChildren(PC.Avatar)[0]
    assert av.marco == "galaxia"
    assert f.findChildren(PE.NombreEfecto) and f.findChildren(PE.NombreEfecto)[0].efecto == "arcoiris"
    sin = amigos.fila_persona({"id": "2", "usuario": "cai", "nombre": "Cai", "foto_url": None})
    sin.show()
    assert sin.findChildren(PC.Avatar)[0].marco == "ninguno" and not sin.findChildren(PE.NombreEfecto)
    f.close()
    sin.close()


# ------------------------------------------------------------------ Personalizar

def _seccion(ctx):
    from descargador.ui.personalizar_ajuste import SeccionPersonalizar
    s = SeccionPersonalizar(ctx)
    s.resize(660, 900)
    s.show()
    return s


def test_personalizar_bloqueado_para_quien_no_es_donador(app):
    ctx, g = _gestor_gratis()
    s = _seccion(ctx)
    assert s.caja_bloqueo.isVisible() and s.bt_donar.isVisible() and s.bt_codigo.isVisible()
    assert not s.bt_aplicar.isEnabled() and "Exclusivo" in s.estado.text()
    s.botones["marco"]["fuego"].click()                              # probar sí se puede: vista previa en vivo
    assert s.avatar.marco == "fuego"
    s.botones["efecto"]["neon"].click()
    assert s.nombre.efecto == "neon"
    s._aplicar()                                                     # pero no se guarda
    assert g.marco == "ninguno" and not any(ll[0] == "PATCH" for ll in ctx.cuenta["sesion"].llamadas)
    s.close()


def test_personalizar_donador_aplica_guarda_y_cambia_el_tema(app):
    ctx, g, ses = _gestor_premium(app)
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "azul", "noche"
    llamadas = []

    class V:
        def reabrir_con_aspecto(self):
            llamadas.append(1)
    ctx.ventana = V()
    s = _seccion(ctx)
    assert not s.caja_bloqueo.isVisible() and s.bt_aplicar.isEnabled() and "Donador" in s.estado.text()
    s.botones["marco"]["oro"].click()
    s.botones["efecto"]["degradado"].click()
    s.botones["tema"]["sakura"].click()
    from descargador.ui import estilos as E
    assert s.muestra.fondo == E.fondo_de("premium_sakura")           # la miniatura ya enseña el tema
    s.bt_aplicar.click()
    assert (g.marco, g.efecto, g.tema) == ("oro", "degradado", "sakura")
    assert ctx.ajustes["fondo"] == "premium_sakura" and llamadas == [1]
    esperar(app, lambda: any(ll[0] == "PATCH" for ll in ses.llamadas), "se guarda en el perfil")
    s.close()


def test_personalizar_con_prueba_muestra_cuanto_queda(app):
    ctx, g, _ = _gestor_premium(app, tipo="prueba")
    s = _seccion(ctx)
    assert "prueba" in s.estado.text() and "días" in s.estado.text()
    s.close()


def test_personalizar_quitar_todo(app):
    ctx, g, _ = _gestor_premium(app)
    g.guardar_personalizacion("aurora", "neon", "oceano")
    s = _seccion(ctx)
    assert s.sel == {"marco": "aurora", "efecto": "neon", "tema": "oceano"}
    s.bt_quitar.click()
    assert (g.marco, g.efecto, g.tema) == ("ninguno",) * 3
    s.close()


@pytest.mark.parametrize("ancho", [560, 660, 900])
def test_personalizar_cabe_en_ventanas_chicas(app, ancho):
    ctx, g = _gestor_gratis()
    from descargador.ui.personalizar_ajuste import SeccionPersonalizar
    s = SeccionPersonalizar(ctx)
    assert s.minimumSizeHint().width() <= ancho
    s.resize(ancho, 1000)
    s.show()
    app.processEvents()
    for b in [b for d in s.botones.values() for b in d.values()]:
        assert b.geometry().right() <= s.width()                      # nada se sale por la derecha
    s.close()


# ------------------------------------------------------------------ canje de código

def test_canje_normaliza_el_codigo_y_activa_el_boton_solo_si_esta_completo(app):
    from descargador.ui.canje_pase import DialogoCanje
    ctx, g = _gestor_gratis()
    d = DialogoCanje(ctx)
    d.show()
    d.campo.textEdited.emit("abcd")
    d.campo.setText("abcd")
    d._al_escribir("abcd")
    assert d.campo.text() == "ABCD" and not d.bt_canjear.isEnabled()
    d._al_escribir("abcd12 34")
    assert d.campo.text() == "ABCD-1234" and d.bt_canjear.isEnabled()
    d.close()


def test_canje_exitoso_cierra_con_buen_mensaje(app):
    from descargador.ui.canje_pase import DialogoCanje
    vence = iso(datetime.now(timezone.utc) + timedelta(days=7))
    ses = SesionFalsa({"canjear_pase": {"ok": True, "mensaje": "¡Listo! 7 días de donador.", "dias": 7, "vence": vence},
                       "mi_premium": {"premium": True, "tipo": "prueba", "vence": vence}})
    ctx = CtxFalso(ses)
    ctx.premium = P.GestorPremium(ctx)
    d = DialogoCanje(ctx)
    d.show()
    d._al_escribir("abcd1234")
    d._canjear()
    assert "Comprobando" in d.estado.text() and not d.bt_canjear.isEnabled()
    esperar(app, lambda: d.canjeado, "canje")
    assert "7 días" in d.estado.text() and ctx.premium.premium
    d.close()


def test_canje_con_codigo_usado_explica_y_deja_reintentar(app):
    from descargador.ui.canje_pase import DialogoCanje
    ses = SesionFalsa({"canjear_pase": {"ok": False, "mensaje": "Ese código ya se usó."}})
    ctx = CtxFalso(ses)
    ctx.premium = P.GestorPremium(ctx)
    d = DialogoCanje(ctx)
    d.show()
    d._al_escribir("zzzz0000")
    d._canjear()
    esperar(app, lambda: "ya se usó" in d.estado.text(), "mensaje del servidor")
    assert not d.canjeado and d.bt_canjear.isEnabled() and d.campo.isEnabled()
    d.close()


def test_canje_sin_internet_lo_dice_sin_jerga(app):
    from descargador.ui.canje_pase import DialogoCanje
    ctx = CtxFalso(SesionFalsa(sin_red=True))
    ctx.premium = P.GestorPremium(ctx)
    d = DialogoCanje(ctx)
    d.show()
    d._al_escribir("zzzz0000")
    d._canjear()
    esperar(app, lambda: "Sin conexión" in d.estado.text(), "aviso de red")
    assert d.bt_canjear.isEnabled()
    d.close()


def test_el_cuadro_de_donar_ofrece_el_codigo_solo_con_sesion(app):
    from descargador.ui.donar import DialogoDonar
    from PySide6.QtWidgets import QWidget
    sin = DialogoDonar(None)
    assert not hasattr(sin, "bt_codigo")
    ventana = QWidget()
    ventana.ctx = CtxFalso(SesionFalsa())
    ventana.ctx.premium = P.GestorPremium(ventana.ctx)
    con = DialogoDonar(ventana)
    assert hasattr(con, "bt_codigo") and "código" in con.bt_codigo.text()
    sin.close()
    con.close()


# ------------------------------------------------------------------ Ajustes: sigue abriendo al instante

def test_ajustes_trae_personalizar_y_no_importa_el_motor_en_la_interfaz(app):
    from test_fondo_app import SesionFalsa as SF
    from test_fondo_app import _ctx as ctx_completo
    from descargador import fondo as F
    from descargador.ui.paginas.ajustes import PaginaAjustes
    ctx = ctx_completo(app, SF({"puede_poner_fondo": False}))
    ctx.fondo = F.GestorFondo(ctx)
    ctx.premium = P.GestorPremium(ctx)
    pag = PaginaAjustes(ctx)
    pag.resize(1000, 800)
    pag.show()
    assert pag.seccion_personalizar is not None
    # lo que cuesta (yt-dlp, ffmpeg) se lee aparte: al abrir solo hay un «leyendo»
    assert pag.et_motor.text() == "Leyendo el motor…"
    esperar(app, lambda: pag.et_motor.text().startswith("yt-dlp"), "motor leído en segundo plano", maximo=30)
    pag.close()


def test_elegir_colores_normales_quita_el_tema_premium_elegido(app):
    ctx, g, ses = _gestor_premium(app)
    g.guardar_personalizacion(tema="ambar")
    assert g.tema == "ambar"
    ctx.ajustes["acento"], ctx.ajustes["fondo"] = "verde", "bosque"        # lo que hace Ajustes › Aspecto
    g.aspecto_elegido_a_mano()
    assert g.tema == "ninguno"
    esperar(app, lambda: [ll for ll in ses.llamadas if ll[0] == "PATCH"][-1][2]["json"]["tema_premium"] == "ninguno",
            "se guarda en el perfil")


def test_el_tema_del_perfil_se_pone_tambien_en_otro_equipo(app):
    ctx, g, _ = _gestor_premium(app, extra={"GET perfiles": [{"marco": "hielo", "efecto_nombre": "brillo",
                                                               "tema_premium": "bosque"}]})
    assert (ctx.ajustes["acento"], ctx.ajustes["fondo"]) == ("premium_bosque", "premium_bosque")
