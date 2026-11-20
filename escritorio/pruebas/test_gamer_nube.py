# -*- coding: utf-8 -*-
"""Modo gamer en la nube: el progreso (XP, minutos y racha) se reparte entre los equipos de una
cuenta. Sin red: la sesión es falsa y registra las llamadas a `pedir`."""

import os
import sys
import tempfile
import uuid
from datetime import date, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="caudal_gamer_nube_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import modo_gamer as MG  # noqa: E402


class SesionFalsa:
    """Imita a la sesión de la cuenta: `pedir` guarda la llamada y devuelve lo preparado."""

    def __init__(self, user_id="user-1", filas=None):
        self.user_id = user_id
        self.filas = filas if filas is not None else []
        self.llamadas = []

    def pedir(self, metodo, ruta, **kw):
        self.llamadas.append((metodo, ruta, kw))
        if metodo == "GET":
            return self.filas
        return None


def progreso_en(tmp_path, hoy):
    return MG.Progreso(tmp_path / "progreso.json", hoy=lambda: hoy)


# ------------------------------------------------------------------ XP entre equipos

def test_xp_suma_la_propia_y_la_de_otros(tmp_path):
    p = progreso_en(tmp_path, date(2026, 11, 20))
    p.d["xp"] = 10
    p.aplicar_otros([
        {"dispositivo": "otro-1", "xp": 5, "minutos": 3, "dias": []},
        {"dispositivo": "otro-2", "xp": 7, "minutos": 1, "dias": []},
    ], "mi-equipo")
    assert p.xp == 22
    assert p.nube_xp == 12 and p.nube_minutos == 4


def test_aplicar_otros_ignora_la_fila_propia_y_las_rotas(tmp_path):
    p = progreso_en(tmp_path, date(2026, 11, 20))
    p.aplicar_otros([
        None,                                                       # no es un dict
        "basura",                                                   # tampoco
        {"dispositivo": "yo", "xp": 999, "minutos": 999, "dias": ["2026-11-20"]},   # la mía
        {"dispositivo": "rota", "xp": "mucho", "minutos": 4},       # xp no numérico
        {"dispositivo": "d", "xp": 4, "minutos": 2, "dias": "2026-01-01"},  # dias no es lista
        {"dispositivo": "e", "xp": 1, "minutos": None, "dias": ["2026-11-19", 5]},
    ], "yo")
    assert p.nube_xp == 5
    assert p.nube_minutos == 2
    assert p.nube_dias == {"2026-11-19"}
    assert p.xp == 5


def test_aplicar_otros_reemplaza_la_foto_anterior(tmp_path):
    p = progreso_en(tmp_path, date(2026, 11, 20))
    p.aplicar_otros([{"dispositivo": "b", "xp": 40, "minutos": 0, "dias": []}], "a")
    p.aplicar_otros([{"dispositivo": "b", "xp": 45, "minutos": 0, "dias": []}], "a")
    assert p.nube_xp == 45                                          # no se suma dos veces


# ------------------------------------------------------------------ racha con dos equipos

def test_racha_une_los_dias_de_dos_equipos(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d["dias"] = [hoy.isoformat()]                                 # hoy en este equipo
    p.aplicar_otros([{"dispositivo": "otro", "xp": 0, "minutos": 0,
                      "dias": [(hoy - timedelta(days=1)).isoformat(),
                               (hoy - timedelta(days=2)).isoformat()]}], "yo")
    assert p.racha() == 3
    assert p.d["mejor_racha"] == 3


def test_racha_se_corta_si_falta_un_dia_en_la_union(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d["dias"] = [hoy.isoformat()]
    p.aplicar_otros([{"dispositivo": "otro", "xp": 0, "minutos": 0,
                      "dias": [(hoy - timedelta(days=2)).isoformat()]}], "yo")
    assert p.racha() == 1                                           # ayer no está: solo hoy


def test_racha_sin_dias_usa_la_logica_de_antes(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d.update(racha=4, ultimo_activo=(hoy - timedelta(days=1)).isoformat(), dias=[])
    assert p.racha() == 4


def test_revisar_racha_anota_el_dia_una_sola_vez(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.sumar_segundos(60 * 12)                                       # supera el mínimo del día
    p.sumar_segundos(60 * 12)
    assert p.d["dias"] == [hoy.isoformat()]


def test_dias_se_limitan_a_120_las_mas_recientes(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d["dias"] = [(hoy - timedelta(days=n)).isoformat() for n in range(130, 0, -1)]
    p.sumar_segundos(60 * 12)
    assert len(p.d["dias"]) == 120
    assert p.d["dias"][-1] == hoy.isoformat()


# ------------------------------------------------------------------ lo que se sube

def test_aporte_no_incluye_lo_de_otros(tmp_path):
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d.update(xp=10, minutos_total=6, dias=[hoy.isoformat()])
    p.aplicar_otros([{"dispositivo": "otro", "xp": 50, "minutos": 30,
                      "dias": ["2026-11-01"]}], "yo")
    assert p.aporte() == {"xp": 10, "minutos": 6, "dias": [hoy.isoformat()]}


# ------------------------------------------------------------------ identificador del equipo

def test_dispositivo_id_es_estable(tmp_path, monkeypatch):
    monkeypatch.setattr(MG, "carpeta_perfil", lambda: tmp_path)
    primero = MG.dispositivo_id()
    segundo = MG.dispositivo_id()
    assert primero == segundo
    assert uuid.UUID(primero).version == 4
    assert (tmp_path / "dispositivo.txt").read_text(encoding="utf-8").strip() == primero


def test_dispositivo_id_reusa_el_archivo_existente(tmp_path, monkeypatch):
    monkeypatch.setattr(MG, "carpeta_perfil", lambda: tmp_path)
    (tmp_path / "dispositivo.txt").write_text("equipo-fijo\n", encoding="utf-8")
    assert MG.dispositivo_id() == "equipo-fijo"


# ------------------------------------------------------------------ sincronización

def test_sincronizar_hace_el_post_con_on_conflict_y_el_get_filtrado(tmp_path, monkeypatch):
    monkeypatch.setattr(MG, "carpeta_perfil", lambda: tmp_path)
    hoy = date(2026, 11, 20)
    p = progreso_en(tmp_path, hoy)
    p.d.update(xp=12, minutos_total=8, dias=[hoy.isoformat()])
    filas_nube = [{"dispositivo": "otro", "xp": 3, "minutos": 1, "dias": []}]
    sesion = SesionFalsa(user_id="user-42", filas=filas_nube)

    devueltas = MG.sincronizar(sesion, p)

    assert devueltas == filas_nube
    (m1, r1, kw1), (m2, r2, kw2) = sesion.llamadas
    assert m1 == "POST"
    assert r1 == "gamer_aportes?on_conflict=user_id,dispositivo"
    assert kw1["json"] == {"user_id": "user-42", "dispositivo": MG.dispositivo_id(),
                           "xp": 12, "minutos": 8, "dias": [hoy.isoformat()]}
    assert kw1["cabeceras"] == {"Prefer": "resolution=merge-duplicates,return=minimal"}
    assert m2 == "GET"
    assert r2 == "gamer_aportes?select=dispositivo,xp,minutos,dias&user_id=eq.user-42"


def test_sincronizar_sin_sesion_no_hace_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(MG, "carpeta_perfil", lambda: tmp_path)
    p = progreso_en(tmp_path, date(2026, 11, 20))
    assert MG.sincronizar(None, p) == []


def test_sincronizar_y_aplicar_dejan_el_xp_de_la_cuenta(tmp_path, monkeypatch):
    monkeypatch.setattr(MG, "carpeta_perfil", lambda: tmp_path)
    p = progreso_en(tmp_path, date(2026, 11, 20))
    p.d["xp"] = 20
    mi_id = MG.dispositivo_id()
    sesion = SesionFalsa(filas=[
        {"dispositivo": mi_id, "xp": 20, "minutos": 0, "dias": []},         # mi fila: ignorada
        {"dispositivo": "portatil", "xp": 30, "minutos": 5, "dias": []},
    ])
    p.aplicar_otros(MG.sincronizar(sesion, p), mi_id)
    assert p.xp == 50
