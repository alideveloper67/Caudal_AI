# -*- coding: utf-8 -*-
"""Mezcla DJ, Mezclador, «Tu mes pasado», versión a la vista y aviso de novedades
grande. Sin red, sin mpv y sin ventanas visibles (Qt 'offscreen'), con datos
temporales."""

import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(autouse=True)
def _sin_cuadros_modales(monkeypatch):
    # en las pruebas no hay motor de audio: el aviso modal de la ventana colgaría la prueba
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: 0))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _basico(p):
    """Los tres datos de los pasos de la primera versión del Mezclador."""
    return {k: p[k] for k in ("entra", "dur", "graves")}


def _pista(n, dur=200, archivo="", artista="Artista"):
    p = {"tipo": "pista", "clave": f"yt:vid{n:08d}", "video_id": f"vid{n:08d}",
         "titulo": f"Canción {n}", "artista": artista, "duracion": dur, "miniatura": ""}
    if archivo:
        p["archivo"] = archivo
    return p


# ================================================================ lógica de la mezcla

def test_segundos_de_la_mezcla_siempre_entre_4_y_16():
    from descargador import mezcla_dj as md
    assert md.limitar_segundos(1) == 4
    assert md.limitar_segundos(99) == 16
    assert md.limitar_segundos("9") == 9
    assert md.limitar_segundos(None) == md.SEG_DEFECTO
    assert md.limitar_segundos("x") == md.SEG_DEFECTO


def test_paso_valido_el_fundido_no_pasa_de_la_entrada():
    from descargador import mezcla_dj as md
    p = md.normalizar_paso({"entra": 6, "dur": 14, "graves": 0}, 200)
    assert _basico(p) == {"entra": 6, "dur": 6, "graves": False}
    assert p["tipo"] == "fundido" and p["curva"] == "suave" and p["tempo"] is False
    # una canción corta no puede empezar a entrar a 30 s del final
    assert md.normalizar_paso({"entra": 30, "dur": 8}, 30)["entra"] == 15
    # basura
    p = md.normalizar_paso({"entra": "a", "dur": None}, 0)
    assert p["entra"] >= md.DUR_MIN_PASO and p["dur"] <= p["entra"]
    assert md.normalizar_paso(None)["graves"] is True


def test_configuracion_manda_el_paso_luego_la_mezcla_luego_el_fundido():
    from descargador import mezcla_dj as md
    cfg = md.configuracion_fundido
    assert cfg({"entra": 12, "dur": 5, "graves": False}, True, 8, True, 3, 200) == (12, 5, False)
    assert cfg(None, True, 10, True, 3, 200) == (10, 10, True)
    assert cfg(None, True, 99, False, 3, 200) == (16, 16, False)
    assert cfg(None, False, 10, True, 3, 200) == (3, 3, False)
    assert cfg(None, False, 10, True, 0, 200) == (0, 0, False)


def test_filtro_de_graves_se_suma_a_la_cadena_del_usuario():
    from descargador import mezcla_dj as md
    assert md.con_graves("") == "lavfi=[highpass=f=220]"
    assert md.con_graves("lavfi=[volume=2dB,alimiter=limit=0.9]") == \
        "lavfi=[highpass=f=220,volume=2dB,alimiter=limit=0.9]"
    assert md.graves_cortados(0.0) == (False, True)
    assert md.graves_cortados(0.49) == (False, True)
    assert md.graves_cortados(0.5) == (True, False)
    assert md.graves_cortados(1.0) == (True, False)


def test_plan_pasos_y_duracion_del_set():
    from descargador import mezcla_dj as md
    pistas = [_pista(1, 200), _pista(2, 180), _pista(3, 240)]
    pasos = md.pasos_para(pistas, [{"entra": 10, "dur": 10, "graves": False}], 6, True)
    assert len(pasos) == 2
    assert _basico(pasos[0]) == {"entra": 10, "dur": 10, "graves": False}
    assert _basico(pasos[1]) == {"entra": 6, "dur": 6, "graves": True}
    plan = md.plan_de_set(pistas, pasos)
    assert set(plan) == {"yt:vid00000001", "yt:vid00000002"}      # la última no tiene paso
    assert md.duracion_del_set(pistas, pasos) == pytest.approx(620 - 16)
    assert md.inicio_de_prueba(200, pasos[0], antes=10) == 180.0
    assert md.inicio_de_prueba(5, pasos[0]) == 0.0


def test_sets_guardados(app):
    from descargador import mezcla_dj as md
    from descargador.coleccion import Coleccion
    col = Coleccion()
    pistas = [_pista(1), _pista(2, archivo="C:/x.mp3")]
    with pytest.raises(ValueError):
        md.guardar_set(col, "  ", pistas, [])
    with pytest.raises(ValueError):
        md.guardar_set(col, "Una sola", pistas[:1], [])
    s = md.guardar_set(col, "Fiesta", pistas, [{"entra": 9, "dur": 7, "graves": True}])
    assert [_basico(x) for x in s["pasos"]] == [{"entra": 9, "dur": 7, "graves": True}]
    assert "archivo" not in s["pistas"][1]                  # nada de rutas de este equipo
    md.guardar_set(col, "fiesta", pistas, [])                # mismo nombre: reemplaza
    assert [x["nombre"] for x in md.leer_sets(col)] == ["fiesta"]
    assert md.nombre_libre(col) == "Mi mezcla n.º 1"
    md.borrar_set(col, "FIESTA")
    assert md.leer_sets(col) == []


# ================================================================ reproductor

class MotorFalso:
    es_video = False

    def __init__(self):
        self.volumen = None
        self.cargas = []
        self.filtros = []
        self.pausado = False
        self.parado = False
        self.pos = 0.0

    def fijar_volumen(self, v):
        self.volumen = v

    def fijar_velocidad(self, v):
        pass

    def fijar_filtros(self, af):
        self.filtros.append(af)

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


def _reproductor(app, monkeypatch, tmp_path, n=3):
    from descargador import mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    a = Ajustes()
    a["sponsorblock"] = False
    a["autoplay"] = False
    a["crossfade"] = 0
    r = Reproductor(a, Coleccion())
    r.disponible = True
    r.audio = [MotorFalso(), MotorFalso()]
    r.activo = 0
    r.volumen = 80
    pistas = []
    for i in range(1, n + 1):
        f = tmp_path / f"{i}.opus"
        f.write_bytes(b"x")
        pistas.append(_pista(i, archivo=str(f)))
    r.secuencia, r.original = list(pistas), list(pistas)
    r.pos, r.actual = 0, pistas[0]
    r._duracion = 200.0
    r.estado = "sonando"
    return r, pistas


def test_ajustes_nuevos_con_sus_valores_por_defecto():
    from descargador.config import DEFECTOS
    assert DEFECTOS["mezcla_dj"] is False
    assert DEFECTOS["mezcla_dj_seg"] == 8
    assert DEFECTOS["mezcla_dj_graves"] is True
    assert DEFECTOS["version_novedades_vista"] == ""


def test_mezcla_dj_automatica_entra_antes_y_cambia_los_graves(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["mezcla_dj"] = True
    r.ajustes["mezcla_dj_seg"] = 12
    r._bordes["vid00000001"] = (0.0, 190.0)
    saliente, entrante = r.audio
    r._al_posicion(saliente, 170.0)                       # aún faltan 20 s de música
    assert r._fundido is None
    r._al_posicion(saliente, 178.5)                       # 190 - 12 = 178: empieza a entrar
    f = r._fundido
    assert f is not None and f["dur"] == 12.0 and f["graves"] is True
    assert r.actual is pistas[1]
    # la que entra llega sin graves; la que sale los conserva
    assert entrante.filtros[-1].startswith("lavfi=[highpass=f=220")
    # a mitad del fundido los graves cambian de una a otra
    f["inicio"] -= 7.0
    r._paso_fundido()
    assert saliente.filtros[-1].startswith("lavfi=[highpass=f=220")
    assert entrante.filtros[-1] in ("", None) or "highpass" not in entrante.filtros[-1]
    # al acabar, los dos vuelven a su sonido de siempre
    f["inicio"] -= 20.0
    r._paso_fundido()
    assert r._fundido is None and saliente.parado
    assert "highpass" not in (entrante.filtros[-1] or "")
    assert "highpass" not in (saliente.filtros[-1] or "")


def test_mezcla_dj_sin_cambio_de_graves(app, monkeypatch, tmp_path):
    r, _ = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["mezcla_dj"] = True
    r.ajustes["mezcla_dj_graves"] = False
    r.ajustes["mezcla_dj_seg"] = 6
    r._al_posicion(r.audio[0], 195.0)
    assert r._fundido["dur"] == 6.0 and r._fundido["graves"] is False
    assert all("highpass" not in (x or "") for x in r.audio[1].filtros)


def test_sin_mezcla_dj_el_fundido_de_siempre_no_toca_los_graves(app, monkeypatch, tmp_path):
    r, _ = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["crossfade"] = 5
    r._al_posicion(r.audio[0], 196.0)
    assert r._fundido["dur"] == 5.0 and r._fundido["graves"] is False


def test_set_del_mezclador_usa_el_paso_de_cada_cancion(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [{"entra": 20, "dur": 4, "graves": False},
                              {"entra": 9, "dur": 9, "graves": True}], "Mi set")
    assert r.contexto["tipo"] == "mezcla" and r.aleatorio is False
    assert set(r.plan_mezcla) == {"yt:vid00000001", "yt:vid00000002"}
    # el primer paso entra a 20 s del final, con 4 s de fundido y sin graves
    r.actual, r._duracion, r.estado = pistas[0], 200.0, "sonando"
    r._al_posicion(r.audio[r.activo], 170.0)
    assert r._fundido is None
    r._al_posicion(r.audio[r.activo], 181.0)
    f = r._fundido
    assert f is not None and f["dur"] == 4.0 and f["graves"] is False
    assert r.actual is pistas[1]
    # otra lista que se reproduzca después borra el plan
    r._cortar_fundido()
    r.reproducir_lista(pistas)
    assert r.plan_mezcla == {}


def test_probar_un_paso_arranca_poco_antes_de_la_entrada(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.probar_paso(pistas[0], pistas[1], {"entra": 12, "dur": 8, "graves": True})
    assert r.secuencia == [pistas[0], pistas[1]]
    entrada = r.audio[r.activo].cargas[-1][1] if r.audio[r.activo].cargas else None
    assert entrada == 200 - 12 - 10 or r._posicion == 178.0
    assert r.plan_mezcla["yt:vid00000001"]["entra"] == 12
    # al terminar la prueba, se calla
    prueba = r._prueba
    r.estado = "sonando"
    r._fin_de_prueba(prueba)
    assert r.audio[r.activo].pausado and r.plan_mezcla == {}


# ================================================================ tu mes pasado

def _historial(pistas_y_fechas):
    from descargador import mixes
    return [mixes.escucha(p, f) for p, f in pistas_y_fechas]


def test_mes_pasado_es_el_mes_calendario_anterior():
    from descargador import recomendador as rc
    ahora = datetime(2026, 11, 15, 12, 0)
    h = []
    for n in range(1, 8):                       # 7 canciones en octubre; la 1 suena 3 veces
        for veces in range(3 if n == 1 else 1):
            h.append((_pista(n), datetime(2026, 10, 3 + veces, 10)))
    h.append((_pista(50), datetime(2026, 11, 2, 9)))     # de este mes: no cuenta
    h.append((_pista(51), datetime(2026, 9, 30, 23)))    # de septiembre: no cuenta
    m = rc.mes_pasado(_historial(h), ahora)
    assert m["titulo"] == "Tu mes pasado"
    assert m["nombre_lista"] == "Lo más escuchado en octubre"
    claves = [p["clave"] for p in m["pistas"]]
    assert claves[0] == "yt:vid00000001" and len(claves) == 7
    assert "yt:vid00000050" not in claves and "yt:vid00000051" not in claves


def test_mes_pasado_en_enero_mira_diciembre():
    from descargador import recomendador as rc
    h = [(_pista(n), datetime(2025, 12, 10 + n)) for n in range(1, 7)]
    m = rc.mes_pasado(_historial(h), datetime(2026, 1, 5))
    assert m["nombre_lista"] == "Lo más escuchado en diciembre"


def test_mes_pasado_con_pocos_datos_usa_los_ultimos_30_dias():
    from descargador import recomendador as rc
    ahora = datetime(2026, 11, 15, 12, 0)
    h = [(_pista(n), datetime(2026, 11, 1 + n)) for n in range(1, 6)]      # todo este mes
    m = rc.mes_pasado(_historial(h), ahora)
    assert m["titulo"] == "Tu último mes"
    assert m["nombre_lista"] == "Lo más escuchado en los últimos 30 días"
    assert m["total"] == 5
    # casi nada: no se ofrece
    assert rc.mes_pasado(_historial(h[:2]), ahora) is None
    assert rc.mes_pasado([], ahora) is None


def test_guardar_el_mes_pasado_como_lista_real(app):
    from descargador import recomendador as rc
    from descargador.coleccion import Coleccion
    col = Coleccion()
    ahora = datetime(2026, 11, 15)
    h = [(_pista(n), datetime(2026, 10, n)) for n in range(1, 9)]
    m = rc.mes_pasado(_historial(h), ahora)
    lista_id, nombre = rc.guardar_como_lista(col, m)
    assert nombre == "Lo más escuchado en octubre"
    assert [p["clave"] for p in col.pistas_de_lista(lista_id)] == [p["clave"] for p in m["pistas"]]
    # guardarla otra vez no choca con la anterior
    _id2, nombre2 = rc.guardar_como_lista(col, m)
    assert nombre2 == "Lo más escuchado en octubre (2)"
    with pytest.raises(ValueError):
        rc.guardar_como_lista(col, {"pistas": []})


def test_vuelve_en_el_tiempo_trae_primero_el_mes_pasado(app):
    from descargador import recomendador as rc
    from descargador.coleccion import Coleccion
    col = Coleccion()
    ahora = datetime(2026, 11, 15)
    for n in range(1, 8):
        p = _pista(n)
        col.recordar(p)
        col.con.execute("INSERT INTO reproducciones (clave, fecha, contexto, nube_id) VALUES (?,?,?,?)",
                        (p["clave"], datetime(2026, 10, 10).timestamp(), "", None))
    col.con.commit()
    lista = rc.maquina_del_tiempo_de(col, ahora)
    assert lista and lista[0]["id"] == "mes_pasado"
    assert lista[0]["nombre_lista"] == "Lo más escuchado en octubre"


# ================================================================ version y aviso grande

def test_notas_con_marca_grande():
    from descargador import version
    assert version.separar_marca_grande("[grande]\nMucho nuevo") == (True, "Mucho nuevo")
    assert version.separar_marca_grande("  [GRANDE] Hola") == (True, "Hola")
    assert version.separar_marca_grande("Arreglos varios") == (False, "Arreglos varios")
    assert version.separar_marca_grande(None) == (False, "")
    assert version.separar_marca_grande("Algo [grande] en medio")[0] is False


def test_el_aviso_sale_una_sola_vez_por_version():
    from descargador.config import Ajustes
    from descargador.ui import novedades_grandes as ng
    a = Ajustes()
    assert ng.debe_mostrarse(a, "2.3.0")
    ng.marcar_vista(a, "2.3.0")
    assert not ng.debe_mostrarse(a, "2.3.0")
    assert Ajustes()["version_novedades_vista"] == "2.3.0"      # queda guardado en disco
    assert ng.debe_mostrarse(a, "2.4.0")


def test_contenido_del_aviso_segun_el_plan():
    from descargador.ui import novedades_grandes as ng
    assert ng.TITULO == "La actualización más grande de Caudal"
    assert [t[1] for t in ng.TARJETAS] == [
        "Perfiles de verdad", "Amigos con solicitud", "Descubre gente", "Sube tu música",
        "Mezclador", "Tu mes pasado", "Colores al instante", "Logo nuevo"]
    assert all(t[2].endswith(".") for t in ng.TARJETAS)


def _contexto(app):
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None          # nada de motores de audio reales en las pruebas
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import estilos
    from descargador.ui.contexto import Contexto
    ajustes = Ajustes()
    estilos.aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
    historial, coleccion = Historial(), Coleccion()
    gestor = Gestor(ajustes, historial)
    rep = Reproductor(ajustes, coleccion)
    return Contexto(ajustes, historial, coleccion, gestor, rep)


def test_aviso_grande_en_tres_tamanos_y_modo_actualizar(app, datos_aislados):
    from PySide6.QtWidgets import QWidget
    from descargador.ui.novedades_grandes import NovedadesGrandes
    padre = QWidget()
    for ancho, alto, cols in ((1400, 900, 4), (900, 700, 2), (560, 640, 1)):
        padre.resize(ancho, alto)
        d = NovedadesGrandes(padre)
        d.show()
        app.processEvents()
        d.mostrar_todo()
        assert d._cols == cols
        assert d.bt_principal.text() == "Empezar"
        assert d.bt_luego.isHidden() and d.bt_cerrar.accessibleName() == "Cerrar"
        assert len(d._tarjetas) == 8
        assert all(t.accessibleName() and t.accessibleDescription() for t in d._tarjetas)
        d.grab().save(str(datos_aislados / f"aviso_{ancho}.png"))
        d.reject()
        assert not d.isVisible()
    d = NovedadesGrandes(padre, {"version": "2.3.0", "instalador": "https://x/i.exe", "notas": ""})
    assert d.bt_principal.text() == "Actualizar ahora" and not d.bt_luego.isHidden()
    d = NovedadesGrandes(padre, {"version": "2.3.0", "instalador": "", "notas": ""})
    assert not d.bt_principal.isEnabled()


def test_las_tarjetas_aparecen_una_a_una(app):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QWidget
    from descargador.ui.novedades_grandes import NovedadesGrandes
    padre = QWidget()
    padre.resize(1200, 800)
    d = NovedadesGrandes(padre)
    d.show()
    assert all(t.progreso() == 0.0 for t in d._tarjetas)
    fin = datetime.now() + timedelta(seconds=2.2)
    while datetime.now() < fin:
        app.processEvents()
    assert all(t.progreso() == pytest.approx(1.0) for t in d._tarjetas)
    d.reject()


def test_aviso_de_actualizacion_grande_sustituye_al_normal(app, monkeypatch):
    from descargador.ui import actualizador, novedades_grandes
    llamados = []
    from descargador.ui import presentacion_grande
    for clase in (novedades_grandes.NovedadesGrandes, presentacion_grande.PresentacionGrande):
        monkeypatch.setattr(clase, "exec", lambda self: llamados.append("grande") or 0)
    monkeypatch.setattr(actualizador.DialogoActualizacion, "exec",
                        lambda self: llamados.append("normal") or 0)
    base = {"version": "9.9.9", "notas": "x", "instalador": "u", "apk": "", "pagina": ""}
    actualizador.mostrar_aviso({**base, "grande": True})
    actualizador.mostrar_aviso({**base, "grande": False})
    actualizador.mostrar_aviso(base)
    assert llamados == ["grande", "normal", "normal"]


# ================================================================ ventana: versión y Mezclador

def test_version_a_la_vista_y_aviso_sin_cortar_la_musica(app, datos_aislados, monkeypatch):
    from descargador import version
    from descargador.ui import novedades_grandes
    from descargador.ui.ventana import Ventana
    from PySide6.QtWidgets import QMessageBox
    # sin motor de audio en las pruebas: el aviso modal colgaría la prueba esperando un clic
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: 0))
    ctx = _contexto(app)
    v = Ventana(ctx)
    v.resize(1440, 900)
    v.show()
    app.processEvents()
    assert v.et_version.text() == f"Caudal {version.VERSION}"
    assert v.et_version.testAttribute(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.WA_TransparentForMouseEvents)
    # abajo a la izquierda: dentro del panel lateral, por encima de la barra de reproducción
    abajo_izq = v.et_version.mapTo(v, v.et_version.rect().bottomLeft())
    assert abajo_izq.x() < 320 and abajo_izq.y() <= v.barra.mapTo(v, v.barra.rect().topLeft()).y()
    assert v.et_version.isVisible()
    v.grab().save(str(datos_aislados / "ventana_version.png"))
    # en la vista de video la barra se oculta y la versión se queda
    v._ajustar_barra("video")
    assert v.barra.isHidden() and v.et_version.isVisible()
    v._ajustar_barra("inicio")
    # el aviso grande: una vez por versión, sin pausar nada
    pausas = []
    monkeypatch.setattr(ctx.reproductor, "pausar", lambda: pausas.append(1))
    monkeypatch.setattr(ctx.reproductor, "detener", lambda: pausas.append(2))
    v._avisar_novedades()
    from descargador.ui import presentacion_grande
    assert isinstance(v._aviso_grande, (novedades_grandes.NovedadesGrandes,
                                        presentacion_grande.PresentacionGrande))
    assert ctx.ajustes["version_novedades_vista"] == version.VERSION
    v._aviso_grande.reject()
    app.processEvents()
    assert v._aviso_grande is None
    v._avisar_novedades()
    assert v._aviso_grande is None                                  # ya no sale
    assert pausas == []
    v.close()


def test_pagina_mezclador_armar_ordenar_probar_reproducir_y_guardar(app, datos_aislados):
    from descargador import mezcla_dj as md
    from descargador.ui.paginas.mezclador import PaginaMezclador
    ctx = _contexto(app)
    avisos, llamadas = [], []
    ctx.aviso.connect(avisos.append)
    ctx.reproductor.reproducir_set = lambda p, pasos, nombre="", **_: llamadas.append(("set", len(p), pasos, nombre))
    ctx.reproductor.probar_paso = lambda a, b, paso, **_: llamadas.append(("prueba", a["clave"], b["clave"], paso))
    pagina = PaginaMezclador(ctx)
    pagina.resize(900, 900)
    pagina.show()
    app.processEvents()
    assert not pagina.bt_reproducir.isEnabled()                 # mesa vacía
    pistas = [_pista(n, 180 + n) for n in range(1, 5)]
    for p in pistas:
        ctx.coleccion.recordar(p)
    assert pagina.anadir(pistas[:3]) == 3
    assert pagina.anadir(pistas[:3]) == 0                       # sin repetir
    assert pagina.anadir(pistas) == 1
    assert len(pagina.pasos) == 3 and pagina.bt_reproducir.isEnabled()
    # ajustar un paso desde su pantalla
    paso0 = pagina.v_set.itemAt(1).widget()
    paso0.s_dur.setValue(5)
    paso0.s_entra.setValue(12)
    paso0.c_tipo.setCurrentIndex(paso0.c_tipo.findData("fundido"))
    assert _basico(pagina.pasos[0]) == {"entra": 12, "dur": 5, "graves": False}
    # el fundido nunca dura más que la entrada
    paso0.s_entra.setValue(3)
    assert pagina.pasos[0]["dur"] == 3
    paso0.s_entra.setValue(12)
    paso0.s_dur.setValue(5)
    # ordenar: subir la segunda; la unión entre las dos que se cruzan se conserva
    pagina._mover(1, -1)
    assert [p["clave"] for p in pagina.pistas][:2] == [pistas[1]["clave"], pistas[0]["clave"]]
    assert _basico(pagina.pasos[0]) == {"entra": 12, "dur": 5, "graves": False}   # la unión que se conserva
    assert pagina.pasos[1] == md.normalizar_paso(md.paso_por_defecto(8, True), 180)   # la nueva
    pagina._quitar(0)
    assert len(pagina.pistas) == 3 and len(pagina.pasos) == 2
    # probar y reproducir
    pagina.probar(0)
    assert llamadas[-1][0] == "prueba" and llamadas[-1][1] == pagina.pistas[0]["clave"]
    pagina.campo_nombre.setText("Fiesta del viernes")
    pagina.reproducir_set()
    assert llamadas[-1][:2] == ("set", 3) and llamadas[-1][3] == "Fiesta del viernes"
    # guardar y volver a abrir
    assert pagina.guardar() is True
    guardados = md.leer_sets(ctx.coleccion)
    assert guardados[0]["nombre"] == "Fiesta del viernes" and len(guardados[0]["pistas"]) == 3
    pagina.vaciar_mesa()
    assert pagina.pistas == [] and not pagina.bt_guardar.isEnabled()
    pagina.abrir_mezcla(guardados[0])
    assert len(pagina.pistas) == 3 and pagina.campo_nombre.text() == "Fiesta del viernes"
    pagina.grab().save(str(datos_aislados / "mezclador.png"))
    # el borrador sobrevive a que la página se rehaga (cambio de color)
    nueva = PaginaMezclador(ctx)
    assert [p["clave"] for p in nueva.pistas] == [p["clave"] for p in pagina.pistas]
    assert nueva.pasos == pagina.pasos
    assert any("guardada" in a.lower() for a in avisos)
    # guardar con menos de dos canciones se rechaza con una frase clara
    pagina.vaciar_mesa()
    with pytest.raises(ValueError, match="al menos dos"):
        md.guardar_set(ctx.coleccion, "x", [], [])
