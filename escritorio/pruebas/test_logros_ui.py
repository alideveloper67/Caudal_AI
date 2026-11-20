# -*- coding: utf-8 -*-
"""Logros en la interfaz (ui/logros_ui.py): insignias en pixel art, pantalla de logros con la
vitrina, el aviso al conseguir uno, la vitrina del perfil y el vigía que cuenta lo que suena.
Sin ventanas a la vista (Qt offscreen), sin internet y sin reproducir nada.

Con CAPTURAS_LOGROS=<carpeta> guarda capturas de las pantallas para mirarlas."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from descargador import logros as L  # noqa: E402
from descargador.ui import logros_ui as LU  # noqa: E402

CAPTURAS = os.environ.get("CAPTURAS_LOGROS")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


def _captura(w, nombre):
    if CAPTURAS:
        os.makedirs(CAPTURAS, exist_ok=True)
        w.grab().save(os.path.join(CAPTURAS, nombre + ".png"))


class Repro(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)

    def __init__(self):
        super().__init__()
        self.estado = "parado"


class Col:
    def __init__(self):
        self.n_listas, self.n_gusta, self.n_desc = 0, 0, 0
        self.archivo = ""

    def listas(self):
        return [{}] * self.n_listas

    def total_me_gusta(self):
        return self.n_gusta

    def contar_descargadas(self):
        return {True: self.n_desc, False: 1}       # como la colección: canciones y videos


class Ctx(QObject):
    me_gusta_cambio = Signal(str, bool)
    listas_cambio = Signal()
    descargas_cambio = Signal()
    aviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.reproductor = Repro()
        self.coleccion = Col()
        self.cuenta = {"usuario": "ana", "sesion": None}
        self.ventana = QWidget()
        self.ventana.resize(1000, 700)


def _logros(tmp_path):
    return L.Logros(str(tmp_path / "logros.json"))


# ---------------------------------------------------------------- insignias

def test_insignias_nitidas_y_en_grises(app):
    for l in L.CATALOGO:
        pm = LU.pixmap_insignia(l.id, 72)
        assert pm.width() == 72 and pm.height() == 72
    img = LU.imagen_insignia("gusta_25")
    gris = LU.imagen_insignia("gusta_25", apagado=True)
    c, g = img.pixelColor(12, 10), gris.pixelColor(12, 10)
    assert c.alpha() == 255 and c.red() > c.blue() + 60          # el corazón es rojo
    assert abs(g.red() - g.green()) < 3 and g.alpha() > 0          # apagado: gris
    assert img.pixelColor(0, 0).alpha() == 0                       # fondo transparente
    # ampliada sin suavizar: un pixel lógico son 3x3 iguales
    big = LU.pixmap_insignia("gusta_25", 72).toImage()
    for x in range(0, 72, 3):
        for y in range(0, 72, 3):
            assert big.pixelColor(x, y) == big.pixelColor(x + 2, y + 2)


# ---------------------------------------------------------------- pantalla de logros

def test_pantalla_de_logros_y_vitrina(app, tmp_path):
    lg = _logros(tmp_path)
    lg.anotar_listas(6)
    lg.anotar_me_gusta(30)
    lg.anotar_segundos(4000)
    lg.revisar()
    cambios = []
    d = LU.DialogoLogros(lg, lambda: cambios.append(1))
    d.resize(820, 1400)
    d.show()
    app.processEvents()
    pag = d.pagina
    assert len(pag.tarjetas) == len(L.CATALOGO)
    assert f"{len(lg.desbloqueados)} de {len(L.CATALOGO)}" in pag.resumen.text()
    por_id = {t.logro.id: t for t in pag.tarjetas}
    assert por_id["lista_5"].bt.isVisibleTo(d) and not por_id["racha_30"].bt.isVisibleTo(d)
    assert "1 de 30 días" in por_id["racha_30"].estado.text()        # hoy ya sonó música
    for i in ("lista_1", "lista_5", "gusta_25"):
        por_id[i].bt.click()
    assert lg.vitrina == ["lista_1", "lista_5", "gusta_25"] and len(cambios) == 3
    assert "En tu perfil" in por_id["lista_5"].bt.text()
    por_id["horas_1"].bt.click()                                    # llena: avisa y no entra
    assert "horas_1" not in lg.vitrina and "ya tiene 3" in pag.aviso.text()
    _captura(d, "logros_pantalla")
    d.close()
    assert pag.pintar not in lg.al_cambiar


# ---------------------------------------------------------------- aviso

def test_aviso_baja_y_se_cierra(app):
    v = QWidget()
    v.resize(900, 600)
    v.show()
    cola = LU.ColaAvisos(v)
    cola.poner([L.POR_ID["racha_7"]])
    a = cola.actual
    assert isinstance(a, LU.AvisoLogro) and a.isVisible()
    fin = time.time() + 2
    while time.time() < fin and a.t < 1.0:
        app.processEvents()
    assert a.y() >= 0 and a.x() == (v.width() - a.width()) // 2
    _captura(v, "logros_aviso")
    a.cerrar()
    fin = time.time() + 2
    while time.time() < fin and cola.actual is not None:
        app.processEvents()
    assert cola.actual is None


def test_muchos_de_golpe_salen_en_un_solo_aviso(app):
    v = QWidget()
    cola = LU.ColaAvisos(v)
    cola.poner([L.CATALOGO[i] for i in range(6)])
    assert cola.actual.extra == 5 and cola.pendientes == []


# ---------------------------------------------------------------- vitrina del perfil

def test_vitrina_mia_y_de_otra_persona(app, tmp_path, monkeypatch):
    ctx = Ctx()
    lg = _logros(tmp_path)
    ctx.logros = lg
    v = LU.VitrinaLogros(ctx, "ana", es_mio=True)
    assert v.isVisibleTo(v.parentWidget() or v) or not v.isHidden()
    assert "Elige hasta 3" in v.findChildren(LU.QLabel)[-1].text()
    lg.anotar_listas(1)
    lg.revisar()
    lg.alternar_vitrina("lista_1")
    assert len(v.findChildren(LU.Insignia)) == 1
    v.resize(640, 190)
    v.show()
    app.processEvents()
    _captura(v, "logros_vitrina")

    # otra persona: se pide a la nube en segundo plano
    monkeypatch.setattr(L, "vitrina_de", lambda s, u: {"vitrina": ["racha_7"], "total": 9, "fechas": {}})
    otra = LU.VitrinaLogros(ctx, "luis", es_mio=False)
    from descargador.hilos import esperar_todo
    esperar_todo(3000)
    fin = time.time() + 2
    while time.time() < fin and otra.isHidden():
        app.processEvents()
    assert not otra.isHidden() and "9 de" in otra.total.text()
    monkeypatch.setattr(L, "vitrina_de", lambda s, u: {"vitrina": [], "total": 0, "fechas": {}})
    nadie = LU.VitrinaLogros(ctx, "x", es_mio=False)
    esperar_todo(3000)
    for _ in range(20):
        app.processEvents()
    assert nadie.isHidden()                                        # sin nada que enseñar no ocupa lugar


# ---------------------------------------------------------------- vigía

def test_vigia_cuenta_lo_que_suena_y_avisa(app, tmp_path, monkeypatch):
    ctx = Ctx()
    lg = _logros(tmp_path)
    reloj = {"t": 1000.0}
    monkeypatch.setattr(LU.time, "monotonic", lambda: reloj["t"])
    vigia = LU.VigiaLogros(ctx, lg, tic_ms=5000, importar=False)
    assert ctx.logros is lg and ctx.vigia_logros is vigia
    r = ctx.reproductor
    r.estado = "sonando"
    r.pista_cambio.emit({"clave": "yt:a", "artistas": [{"nombre": "A"}]})
    for _ in range(3):
        reloj["t"] += 5
        vigia._al_tic()
    assert lg.contadores["segundos"] == 15 and lg.contadores["canciones"] == 0
    reloj["t"] += 5
    vigia._al_tic()
    assert lg.contadores["canciones"] == 1 and lg.conseguido("primera_nota")
    assert vigia.avisos.actual is not None and vigia.avisos.actual.logro.id == "primera_nota"
    # en pausa no cuenta, y un salto largo (equipo dormido) no suma de más
    r.estado = "pausa"
    reloj["t"] += 500
    vigia._al_tic()
    r.estado = "sonando"
    reloj["t"] += 3600
    vigia._al_tic()
    assert lg.contadores["segundos"] == 20 + 15


def test_vigia_colecciones_y_salas(app, tmp_path):
    ctx = Ctx()
    lg = _logros(tmp_path)
    vigia = LU.VigiaLogros(ctx, lg, importar=False)
    ctx.coleccion.n_listas, ctx.coleccion.n_gusta, ctx.coleccion.n_desc = 5, 26, 3
    ctx.listas_cambio.emit()
    assert {"lista_1", "lista_5", "gusta_25"} <= set(lg.desbloqueados)
    assert lg.contadores["descargas"] == 4                         # 3 canciones + 1 video

    class Sala:
        codigo, mi_id, soy_anfitrion = "ABC123", "yo", True
        miembros = [1]

    class Gestor:
        sala = Sala()
    vigia._juntos = Gestor()
    vigia._al_juntos()
    assert lg.contadores["juntos"] == 0                            # sola en la sala
    Sala.miembros = [1, 2]
    vigia._al_juntos()
    vigia._al_juntos()
    assert lg.contadores["juntos"] == 1 and {"juntos_1", "anfitrion"} <= set(lg.desbloqueados)


def test_vigia_importa_lo_de_antes_y_sincroniza(app, tmp_path, monkeypatch):
    ctx = Ctx()
    lg = _logros(tmp_path)
    monkeypatch.setattr(L, "reproducciones_de", lambda ruta: [("yt:a", time.time() - 86400 * d, None) for d in range(3)])
    subidas = []

    def subir(datos, sesion):
        subidas.append(datos)
        return {"contadores": {"juntos": 4}, "plataformas": ["android"]}
    monkeypatch.setattr(L, "subir", subir)

    class Sesion:
        access = "token"
    ctx.cuenta["sesion"] = Sesion()
    vigia = LU.VigiaLogros(ctx, lg, importar=False)
    vigia._importar()
    from descargador.hilos import esperar_todo
    for _ in range(3):
        esperar_todo(3000)
        app.processEvents()
    assert lg.importado and lg.conseguido("racha_3")
    assert subidas and subidas[0]["p_plataformas"] == ["windows"]
    assert lg.contadores["juntos"] == 4 and lg.conseguido("dos_mundos")
    assert lg.pendiente_nube            # «Dos mundos» se consiguió al juntar: sale en la próxima subida


def test_fila_de_ajustes_para_logros(app, tmp_path):
    from descargador.ui.ajuste_aviso_errores import fila_logros
    from descargador.ui.paginas.ajustes import Seccion
    ctx = Ctx()
    ctx.logros = _logros(tmp_path)
    s = Seccion("Logros")
    bt = fila_logros(s, ctx)
    assert bt.text() == "Ver logros"
