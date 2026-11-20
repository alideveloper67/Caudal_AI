# -*- coding: utf-8 -*-
"""herramientas/ver_errores.py: la consulta que agrupa por traza, los filtros (sin inyección de
SQL) y el texto que se enseña. La consulta de verdad se ejecuta en supabase/pruebas/errores_app.prueba.mjs."""

import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))

import ver_errores as V  # noqa: E402


def test_consulta_agrupa_por_huella_con_filtros():
    sql = V.sql_agrupados(7, "android", "2.6.1", 10)
    assert "group by huella" in sql and "sum(veces)" in sql and "limit 10" in sql
    assert "interval '7 days'" in sql and "plataforma = 'android'" in sql and "version = '2.6.1'" in sql


def test_filtros_sin_inyeccion():
    sql = V.sql_agrupados(30, version="1'; drop table errores_app; --")
    assert "version = '1''; drop table errores_app; --'" in sql
    with pytest.raises(ValueError):
        V.sql_detalle("abc' or 1=1 --")
    assert "huella like 'abc123%'" in V.sql_detalle("abc123")
    assert "interval '1 days'" in V.sql_agrupados(-5)


def test_texto_de_los_grupos():
    grupos = [{"huella": "a1b2c3d4e5f6a7b8c9d0", "tipo": "ValueError", "mensaje": "boom", "pantalla": "Ventana",
               "origen": "interfaz", "traza": "Traceback\n  File x\nValueError: boom", "veces": 12, "informes": 3,
               "plataformas": ["android", "windows"], "versiones": ["2.6.1", "2.7.2"],
               "primera": "2026-11-01T10:00:00", "ultima": "2026-11-18T22:15:00"}]
    t = V.formatear(grupos, con_traza=True)
    assert "1 errores distintos · 12 veces" in t and "ValueError  ×12  (3 informes)" in t
    assert "android, windows" in t and "2.6.1, 2.7.2" in t and "ValueError: boom" in t
    assert "2026-11-18 22:15" in t and "a1b2c3d4e5f6" in t
    assert "Traceback" not in V.formatear(grupos)
    assert V.formatear([]) == "No hay errores en ese periodo."
    d = V.formatear_detalle([{"creado": "2026-11-18T22:15:00", "plataforma": "ios", "version": "2.6.1",
                              "sistema": "ios 18", "pantalla": "", "veces": 2, "tipo": "X", "mensaje": "m",
                              "traza": "T"}])
    assert "ios 2.6.1" in d and "Última traza (X: m)" in d


def test_sin_token_sale_con_explicacion(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_TOKEN", raising=False)
    monkeypatch.setattr(V.os.path, "expanduser", lambda _p: str(tmp_path))
    with pytest.raises(SystemExit) as e:
        V.main([])
    assert "token" in str(e.value)
