# -*- coding: utf-8 -*-
"""Logros (descargador/logros.py): rachas, horas, canciones y artistas descubiertos, listas, me gusta,
salas con amigos, horarios, vitrina, guardado en el disco, mezcla con la nube, lo escuchado antes y
que el catálogo y los dibujos sean los mismos que en la app del teléfono."""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import logros as L  # noqa: E402
from descargador.logros_dibujos import DIBUJOS, LADO  # noqa: E402

APP = Path(__file__).resolve().parents[2] / "app" / "lib" / "nucleo"


def _t(texto):
    """Segundos desde 1970 de una fecha y hora local «aaaa-mm-dd hh:mm»."""
    return datetime.strptime(texto, "%Y-%m-%d %H:%M").timestamp()


class Reloj:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def nuevo(tmp_path, t="2026-11-10 12:00"):
    return L.Logros(str(tmp_path / "logros.json"), reloj=Reloj(_t(t)))


# ---------------------------------------------------------------- catálogo y dibujos

def test_al_menos_20_logros_cada_uno_con_su_dibujo():
    assert len(L.CATALOGO) >= 20
    ids = [l.id for l in L.CATALOGO]
    assert len(ids) == len(set(ids))
    cats = {c for c, _ in L.CATEGORIAS}
    for l in L.CATALOGO:
        assert l.categoria in cats and l.meta > 0 and l.nombre and l.descripcion
        paleta, filas = DIBUJOS[l.id]
        assert len(filas) == LADO and all(len(f) == LADO for f in filas)
        usados = {c for f in filas for c in f} - {"."}
        assert usados <= set(paleta) and len(usados) >= 4, l.id
        assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in paleta.values())
        # que no sea un garabato: ocupa buena parte del cuadro
        assert sum(c != "." for f in filas for c in f) > 120, l.id


def test_dibujos_iguales_en_el_telefono():
    dart = (APP / "logros_dibujos.dart").read_text(encoding="utf-8")
    bloques = re.findall(r"  '(\w+)': \(\n    \{(.*?)\},\n    \[\n(.*?)    \],\n  \),", dart, re.S)
    assert len(bloques) == len(DIBUJOS)
    for clave, pal, filas in bloques:
        paleta = {s: "#" + h.lower() for s, h in re.findall(r"'(.)': 0xFF([0-9A-F]{6})", pal)}
        filas = re.findall(r"'([^']*)',", filas)
        assert (paleta, tuple(filas)) == (DIBUJOS[clave][0], DIBUJOS[clave][1]), clave


def test_catalogo_igual_en_el_telefono():
    dart = (APP / "logros.dart").read_text(encoding="utf-8")
    del_movil = re.findall(r"Logro\('(\w+)',\s*'([^']*)',\s*'([^']*)',\s*'(\w+)',\s*'(\w+)',\s*(\d+)\)", dart)
    assert [(i, n, d, c, m, int(v)) for i, n, d, c, m, v in del_movil] == \
        [(l.id, l.nombre, l.descripcion, l.categoria, l.metrica, l.meta) for l in L.CATALOGO]


# ---------------------------------------------------------------- rachas

def test_rachas():
    assert L.racha_mas_larga(["2026-01-01", "2026-01-02", "2026-01-04", "2026-01-05", "2026-01-06", "x"]) == 3
    assert L.racha_mas_larga([]) == 0
    dias = ["2026-11-08", "2026-11-09", "2026-11-10"]
    assert L.racha_en_curso(dias, "2026-11-10") == 3
    assert L.racha_en_curso(dias, "2026-11-11") == 3       # hoy aún no escuchó: la racha sigue viva
    assert L.racha_en_curso(dias, "2026-11-12") == 0


def test_un_dia_cuenta_con_un_minuto_de_musica(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_segundos(30, _t("2026-11-10 10:00"))
    assert "2026-11-10" not in lg.dias
    lg.anotar_segundos(30, _t("2026-11-10 10:01"))
    assert "2026-11-10" in lg.dias


def test_racha_de_7_dias_desbloquea_las_de_3_y_7(tmp_path):
    lg = nuevo(tmp_path)
    for d in range(1, 8):
        lg.anotar_segundos(120, _t(f"2026-11-{d:02d} 20:00"))
    nuevos = {l.id for l in lg.revisar()}
    assert {"racha_3", "racha_7"} <= nuevos and "racha_30" not in nuevos
    assert lg.contadores["racha_max"] == 7


# ---------------------------------------------------------------- horas, canciones, horarios

def test_horas_y_maraton(tmp_path):
    lg = nuevo(tmp_path)
    for _ in range(4 * 60):
        lg.anotar_segundos(60, _t("2026-11-10 15:00"))
    ids = {l.id for l in lg.revisar()}
    assert {"horas_1", "maraton"} <= ids and "horas_10" not in ids
    assert lg.valor("horas") == 4 and lg.valor("dia_horas") == 4
    assert lg.progreso("horas_10")[:2] == (4, 10)


def test_horas_de_dias_distintos_no_hacen_maraton(tmp_path):
    lg = nuevo(tmp_path)
    for d in range(1, 5):
        lg.anotar_segundos(3600, _t(f"2026-11-{d:02d} 15:00"))
    assert lg.valor("horas") == 4 and lg.valor("dia_horas") == 1


def test_canciones_y_artistas_distintos(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_pista({"clave": "yt:a", "artistas": [{"id": "1", "nombre": "Bad Bunny"}]})
    lg.anotar_pista({"clave": "yt:a", "artistas": [{"id": "1", "nombre": "Bad Bunny"}]})
    lg.anotar_pista({"clave": "yt:b", "artista": "Karol G, BAD BUNNY"})
    assert lg.contadores["canciones"] == 2 and lg.contadores["artistas"] == 2
    assert [l.id for l in lg.revisar()] == ["primera_nota"]


def test_noche_y_madrugada(tmp_path):
    lg = nuevo(tmp_path)
    for i in range(10):
        lg.anotar_cancion(f"n{i}", (), _t("2026-11-10 02:30"))
        lg.anotar_cancion(f"m{i}", (), _t("2026-11-10 06:15"))
        lg.anotar_cancion(f"d{i}", (), _t("2026-11-10 13:00"))
    ids = {l.id for l in lg.revisar()}
    assert {"noctambulo", "madrugador"} <= ids
    assert lg.contadores["noche"] == 10 and lg.contadores["manana"] == 10


# ---------------------------------------------------------------- colección y amigos

def test_totales_nunca_bajan(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_listas(5)
    lg.anotar_listas(2)              # borró listas: lo conseguido no se pierde
    lg.anotar_me_gusta(30)
    lg.anotar_descargas(25)
    ids = {l.id for l in lg.revisar()}
    assert {"lista_1", "lista_5", "gusta_25", "descargas_25"} <= ids and "lista_15" not in ids
    assert lg.contadores["listas"] == 5


def test_salas_con_amigos_cuentan_una_vez(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_sala("ABC123|yo", con_amigos=False)
    assert lg.contadores["juntos"] == 0
    lg.anotar_sala("ABC123|yo", con_amigos=True, soy_anfitrion=True)
    lg.anotar_sala("ABC123|yo", con_amigos=True, soy_anfitrion=True)
    assert lg.contadores["juntos"] == 1 and lg.contadores["anfitrion"] == 1
    for i in range(9):
        lg.anotar_sala(f"S{i}|yo", True)
    ids = {l.id for l in lg.revisar()}
    assert {"juntos_1", "juntos_10", "anfitrion"} <= ids


def test_dos_mundos_y_coleccionista(tmp_path):
    lg = nuevo(tmp_path)
    assert lg.valor("dispositivos") == 1
    lg.mezclar({"plataformas": ["android"]})
    assert lg.valor("dispositivos") == 2
    lg.mezclar({"plataformas": ["web"]})
    assert lg.valor("dispositivos") == 2
    lg.anotar_listas(20)
    lg.anotar_me_gusta(250)
    lg.anotar_descargas(30)
    for i in range(1100):
        lg.anotar_cancion(f"c{i}", (f"a{i}",), _t("2026-11-10 03:00"))
    lg.anotar_sala("X|1", True, True)
    nuevos = {l.id for l in lg.revisar()}
    assert "coleccionista" in nuevos and len(lg.desbloqueados) >= 15


# ---------------------------------------------------------------- vitrina

def test_vitrina_solo_conseguidos_y_hasta_3(tmp_path):
    lg = nuevo(tmp_path)
    assert lg.alternar_vitrina("racha_7") is False        # aún no
    lg.anotar_listas(20)
    lg.anotar_me_gusta(250)
    lg.revisar()
    for i in ("lista_1", "lista_5", "lista_15"):
        assert lg.alternar_vitrina(i)
    assert lg.alternar_vitrina("gusta_25") is False       # llena
    assert lg.alternar_vitrina("lista_5") and lg.vitrina == ["lista_1", "lista_15"]
    assert lg.poner_vitrina(["gusta_25", "gusta_25", "no_existe", "lista_1", "lista_5"]) == \
        ["gusta_25", "lista_1", "lista_5"]


# ---------------------------------------------------------------- disco y nube

def test_se_guarda_y_se_recupera(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_segundos(4000, _t("2026-11-10 12:00"))
    lg.anotar_pista({"clave": "yt:a", "artista": "X"})
    lg.revisar()
    lg.alternar_vitrina("horas_1")
    otro = nuevo(tmp_path)
    assert otro.contadores["segundos"] == 4000 and "yt:a" in otro.claves
    assert otro.conseguido("horas_1") and otro.vitrina == ["horas_1"]
    otro.anotar_pista({"clave": "yt:a"})
    assert otro.contadores["canciones"] == 1               # ya la conocía


def test_archivo_roto_no_rompe(tmp_path):
    (tmp_path / "logros.json").write_text("{esto no es json", encoding="utf-8")
    lg = nuevo(tmp_path)
    assert lg.contadores["segundos"] == 0
    (tmp_path / "logros.json").write_text(json.dumps({"contadores": {"segundos": "mucho"},
                                                      "desbloqueados": {"inventado": 1}}), encoding="utf-8")
    lg = nuevo(tmp_path)
    assert lg.contadores["segundos"] == 0 and lg.desbloqueados == {}


def test_para_nube_y_mezclar_nunca_baja(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_segundos(7200, _t("2026-11-10 12:00"))
    lg.revisar()
    d = lg.para_nube()
    assert set(d) == {"p_contadores", "p_dias", "p_plataformas", "p_desbloqueados", "p_vitrina"}
    assert d["p_plataformas"] == ["windows"] and d["p_contadores"]["segundos"] == 7200
    assert "claves" not in json.dumps(d)                  # las canciones escuchadas no viajan
    fecha_local = lg.desbloqueados["horas_1"]
    lg.mezclar({"contadores": {"segundos": 100, "canciones": 300}, "dias": ["2026-11-09"],
                "plataformas": ["android"], "desbloqueados": {"horas_1": fecha_local - 50, "racha_3": 5},
                "vitrina": ["racha_3", "inventado"]})
    assert lg.contadores["segundos"] == 7200 and lg.contadores["canciones"] == 300
    assert lg.desbloqueados["horas_1"] == fecha_local - 50 and "racha_3" in lg.desbloqueados
    assert lg.vitrina == ["racha_3"] and "2026-11-09" in lg.dias


class Sesion:
    access = "x"

    def __init__(self, respuesta=None, falla=False):
        self.respuesta, self.falla, self.llamadas = respuesta, falla, []

    def rpc(self, nombre, **p):
        self.llamadas.append((nombre, p))
        if self.falla:
            raise ConnectionError("sin red")
        return self.respuesta


def test_sincronizar(tmp_path):
    lg = nuevo(tmp_path)
    lg.anotar_listas(1)
    assert L.sincronizar(lg, None) is False
    assert L.sincronizar(lg, Sesion(falla=True)) is False and lg.pendiente_nube
    s = Sesion({"contadores": {"juntos": 3}, "desbloqueados": {}, "dias": [], "plataformas": ["ios"]})
    assert L.sincronizar(lg, s) is True and not lg.pendiente_nube
    assert s.llamadas[0][0] == "logros_guardar" and lg.contadores["juntos"] == 3


def test_vitrina_de_otra_persona():
    s = Sesion({"vitrina": ["racha_7", "inventado"], "total": "4", "fechas": {"racha_7": 1}})
    assert L.vitrina_de(s, "ana") == {"vitrina": ["racha_7"], "total": 4, "fechas": {"racha_7": 1}}
    assert s.llamadas == [("logros_de", {"p_usuario": "ana"})]
    assert L.vitrina_de(Sesion(None), "ana") is None
    assert L.vitrina_de(Sesion(falla=True), "ana") is None


def test_importar_lo_escuchado_antes(tmp_path):
    base = tmp_path / "historial.db"
    con = sqlite3.connect(base)
    con.execute("CREATE TABLE pistas (clave TEXT PRIMARY KEY, datos TEXT NOT NULL, actualizada REAL)")
    con.execute("CREATE TABLE reproducciones (id INTEGER PRIMARY KEY AUTOINCREMENT, clave TEXT NOT NULL, "
                "fecha REAL, contexto TEXT DEFAULT '', nube_id INTEGER)")
    con.execute("INSERT INTO pistas VALUES ('yt:a', ?, 0)", (json.dumps({"clave": "yt:a", "artistas": [{"nombre": "A"}]}),))
    for d in (1, 2, 3):
        con.execute("INSERT INTO reproducciones (clave, fecha) VALUES ('yt:a', ?)", (_t(f"2026-11-0{d} 02:00"),))
    con.execute("INSERT INTO reproducciones (clave, fecha) VALUES ('yt:b', ?)", (_t("2026-11-03 12:00"),))
    con.commit()
    con.close()
    filas = L.reproducciones_de(str(base))
    assert len(filas) == 4 and filas[0][2]["artistas"][0]["nombre"] == "A"
    lg = nuevo(tmp_path)
    lg.importar(filas)
    assert lg.contadores["canciones"] == 2 and lg.contadores["artistas"] == 1 and lg.contadores["noche"] == 3
    assert lg.contadores["racha_max"] == 3 and lg.contadores["segundos"] == 0
    lg.importar(filas)                                    # una sola vez
    assert lg.contadores["noche"] == 3
    assert {"primera_nota", "racha_3"} <= {l.id for l in lg.revisar()}
    assert L.reproducciones_de(str(tmp_path / "no_existe.db")) == []


def test_aviso_de_cambios(tmp_path):
    lg = nuevo(tmp_path)
    vistos = []
    lg.al_cambiar.append(lambda: vistos.append(1))
    lg.al_cambiar.append(lambda: 1 / 0)                   # una pantalla rota no rompe nada
    lg.anotar_listas(1)
    lg.revisar()
    assert vistos == [1]
    lg.revisar()                                          # nada nuevo: nadie se entera
    assert vistos == [1]
