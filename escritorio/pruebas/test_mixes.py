# -*- coding: utf-8 -*-
"""Pruebas de Tus mixes diarios y Tu resumen (sin red ni ventanas)."""

import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AHORA = datetime(2026, 11, 13, 21, 30)


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


def pista(vid, artista, aid=None, titulo=None, duracion=200):
    vid = vid.ljust(11, "x")[:11]
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid,
            "titulo": titulo or f"Canción {vid}", "artista": artista,
            "artistas": [{"id": aid or f"UC{artista}", "nombre": artista}],
            "duracion": duracion, "miniatura": f"https://img/{vid}.jpg"}


def historial_de_dos_estilos():
    """Reguetón por la noche, rock por la mañana: dos mundos que no se mezclan."""
    from descargador.mixes import escucha
    reggaeton = [pista(f"reg{i}", a) for i, a in enumerate(["Bad Bunny", "Feid", "Karol G"] * 3)]
    rock = [pista(f"roc{i}", a) for i, a in enumerate(["Soda Stereo", "Cerati", "Enanitos"] * 3)]
    salida = []
    for d in range(20):
        dia = AHORA - timedelta(days=d)
        for j, p in enumerate(reggaeton):
            salida.append(escucha(p, dia.replace(hour=22, minute=j * 4)))
        for j, p in enumerate(rock):
            salida.append(escucha(p, dia.replace(hour=8, minute=j * 4)))
    return salida


# ---------------------------------------------------------------- mixes

def test_los_artistas_de_una_sesion_van_al_mismo_mix():
    from descargador.mixes import agrupar
    grupos = agrupar(historial_de_dos_estilos(), ahora=AHORA)
    assert len(grupos) >= 2
    juntos = {}
    for i, g in enumerate(grupos):
        for a in g.artistas:
            juntos[g.nombres[a]] = i
    reg = {juntos[n] for n in ("Bad Bunny", "Feid", "Karol G")}
    roc = {juntos[n] for n in ("Soda Stereo", "Cerati", "Enanitos")}
    # (se puede partir un grupo para llegar a tres mixes, pero nunca mezclar mundos)
    assert not reg & roc
    assert len(reg) + len(roc) <= 3


def test_con_poco_historial_salen_al_menos_tres_mixes():
    from descargador.mixes import agrupar, escucha
    h = [escucha(pista(f"a{i}", n), AHORA - timedelta(minutes=10 * i))
         for i, n in enumerate(["Uno", "Dos", "Tres", "Cuatro"])]
    assert len(agrupar(h, ahora=AHORA)) >= 3


def test_construir_mezcla_tus_canciones_con_la_radio_sin_repetir():
    from descargador.mixes import construir
    pedidas = []

    def radio(vid):
        pedidas.append(vid)
        return [pista(f"r{vid[:4]}{i}", "Nuevo") for i in range(30)]

    mixes = construir(historial_de_dos_estilos(), radio=radio, ahora=AHORA, largo=30)
    assert 2 <= len(mixes) <= 6
    assert pedidas and len(pedidas) == len(set(pedidas))
    vistos = set()
    for i, m in enumerate(mixes):
        assert m["tipo"] == "mix" and m["con_radio"]
        assert m["titulo"] == f"Mix diario {i + 1}"
        assert m["subtitulo"].endswith("y más")
        assert 1 <= len(m["miniaturas"]) <= 4
        ids = [p["video_id"] for p in m["pistas"]]
        assert len(ids) == len(set(ids))
        assert not vistos & set(ids), "una cancion de radio no se repite entre mixes"
        vistos.update(ids)
        assert any(p["artista"] == "Nuevo" for p in m["pistas"])
        assert m["pistas"][0]["artista"] != "Nuevo", "empieza con una tuya"


def test_sin_red_el_mix_sale_con_lo_tuyo():
    from descargador.mixes import construir

    def radio(_vid):
        raise OSError("sin red")

    mixes = construir(historial_de_dos_estilos(), radio=radio, ahora=AHORA)
    assert mixes and not any(m["con_radio"] for m in mixes)
    assert all(p["artista"] != "Nuevo" for m in mixes for p in m["pistas"])


def test_el_mix_del_dia_no_cambia_en_el_dia():
    from descargador.mixes import construir
    a = construir(historial_de_dos_estilos(), radio=None, ahora=AHORA)
    b = construir(historial_de_dos_estilos(), radio=None, ahora=AHORA.replace(hour=23))
    assert [p["clave"] for p in a[0]["pistas"]] == [p["clave"] for p in b[0]["pistas"]]


def test_el_estilo_sale_del_genero_desde_el_que_sonaron():
    from descargador.mixes import construir, escucha
    h = [escucha(pista(f"s{i}", "Romeo"), AHORA - timedelta(minutes=5 * i),
                 {"tipo": "genero", "id": "g1", "titulo": "Bachata"}) for i in range(6)]
    mixes = construir(h, radio=None, ahora=AHORA)
    assert mixes[0]["titulo"] == "Mix de Bachata"


def test_mixes_del_dia_se_guardan_un_dia_y_se_reintentan_sin_radio():
    from descargador import mixes as mx
    from descargador.coleccion import Coleccion
    col = Coleccion(":memory:")  # en memoria: el disco de esta PC va lento
    for e in historial_de_dos_estilos()[:120]:
        col.registrar_escucha(e["pista"])
        col.con.execute("UPDATE reproducciones SET fecha=? WHERE id=(SELECT MAX(id) FROM "
                        "reproducciones)", (e["fecha"].timestamp(),))
    col.con.commit()
    llamadas = []

    def sin_red(vid):
        llamadas.append(vid)
        raise OSError("sin red")

    primeros = mx.del_dia(col, radio=sin_red, ahora=AHORA)
    assert primeros and llamadas
    n = len(llamadas)

    def con_red(vid):
        llamadas.append(vid)
        return [pista(f"n{vid[:5]}{i}", "Nuevo") for i in range(10)]

    segundos = mx.del_dia(col, radio=con_red, ahora=AHORA)       # se reintenta
    assert len(llamadas) > n and all(m["con_radio"] for m in segundos)
    n = len(llamadas)
    terceros = mx.del_dia(col, radio=con_red, ahora=AHORA)       # ya completo: cache
    assert len(llamadas) == n and terceros == segundos
    # un armado sin radio no pisa el bueno de hoy
    mx.guardar(col, mx.construir(mx.historial_para_mixes(col, AHORA), None, AHORA), AHORA)
    assert mx.guardados_de_hoy(col, AHORA)[1] is True
    # al dia siguiente se rehacen
    mx.del_dia(col, radio=con_red, ahora=AHORA + timedelta(days=1))
    assert len(llamadas) > n


def test_leer_historial_en_orden_y_con_contexto():
    from descargador import mixes as mx
    from descargador.coleccion import Coleccion
    col = Coleccion(":memory:")  # en memoria: el disco de esta PC va lento
    col.registrar_escucha(pista("uno", "A"), {"tipo": "album", "id": "x", "titulo": "Disco"})
    col.registrar_escucha(pista("dos", "B"))
    h = mx.leer_historial(col)
    assert [e["pista"]["video_id"][:3] for e in h] == ["uno", "dos"]
    assert h[0]["contexto"]["titulo"] == "Disco" and h[1]["contexto"] is None


def test_artistas_sin_id_se_parten_por_comas():
    from descargador.mixes import artistas_de
    p = {"artista": "Shakira, Bizarrap & Ozuna"}
    assert [n for _c, n in artistas_de(p)] == ["Shakira", "Bizarrap", "Ozuna"]


# ---------------------------------------------------------------- resumen

def test_resumen_de_la_semana():
    from descargador.mixes import calcular_resumen, escucha
    h = []
    favorita = pista("fav", "Bad Bunny", duracion=180)
    otra = pista("otra", "Feid", duracion=240)
    for d in range(5):                       # 5 dias seguidos hasta hoy
        dia = AHORA - timedelta(days=d)
        h += [escucha(favorita, dia.replace(hour=22)), escucha(favorita, dia.replace(hour=23)),
              escucha(otra, dia.replace(hour=9))]
    h.insert(0, escucha(pista("vieja", "Viejo"), AHORA - timedelta(days=10)))
    r = calcular_resumen(h, "semana", ahora=AHORA.replace(hour=23, minute=59))
    assert r["escuchas"] == 15
    assert r["minutos"] == round((10 * 180 + 5 * 240) / 60)
    assert r["top_canciones"][0]["pista"]["video_id"].startswith("fav")
    assert r["top_canciones"][0]["veces"] == 10
    assert r["top_artistas"][0]["nombre"] == "Bad Bunny"
    assert r["hora_pico"] == 9 and r["franja"] == "mañana"   # 20 min a las 9 frente a 15
    assert r["racha_actual"] == 5 and r["racha_mas_larga"] == 5
    assert r["dias_con_musica"] == 5 and len(r["por_dia"]) == 7
    assert r["cancion_del_mes"]["pista"]["video_id"].startswith("fav")
    assert r["nombre_mes"] == "noviembre"
    assert r["minutos_antes"] == round(200 / 60) and r["cambio"] is not None
    assert [a["nombre"] for a in r["descubrimientos"]] == ["Bad Bunny", "Feid"]


def test_resumen_vacio_y_racha_hasta_ayer():
    from descargador.mixes import calcular_resumen, escucha
    assert calcular_resumen([], "anio", ahora=AHORA)["vacio"]
    h = [escucha(pista("x", "A"), AHORA - timedelta(days=d)) for d in (1, 2, 3)]
    r = calcular_resumen(h, "mes", ahora=AHORA)
    assert r["racha_actual"] == 3 and not r["vacio"] and len(r["por_dia"]) == 30


def test_videos_largos_no_inflan_los_minutos():
    from descargador.mixes import calcular_resumen, escucha
    r = calcular_resumen([escucha(pista("live", "DJ", duracion=7200), AHORA)], "semana",
                         ahora=AHORA)
    assert r["minutos"] == 15
