# -*- coding: utf-8 -*-
"""Lo nuevo de la 2.1 en el escritorio: recomendador, chat y datos del perfil."""

from datetime import date, datetime, timedelta

from descargador import chat as CH
from descargador import legal
from descargador import recomendador as rc

HOY = datetime(2026, 11, 14, 12)


def p(vid, artista):
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": f"T{vid}",
            "artista": artista, "artistas": [{"nombre": artista, "id": f"id_{artista}"}],
            "duracion": 200, "miniatura": f"m{vid}"}


def e(pista, dias):
    return {"pista": pista, "fecha": HOY - timedelta(days=dias), "contexto": None}


def test_combinar_y_diversificar():
    r = rc.combinar([[p("a", "A"), p("b", "B")], [p("c", "C"), p("b", "B")]])
    assert r[0][0]["video_id"] == "b"
    d = rc.diversificar([p(f"a{i}", "A") for i in range(5)] + [p("b0", "B")], 2, 4)
    assert [x["video_id"] for x in d] == ["a0", "a1", "b0", "a2"]


def test_descubre_no_repite_ni_salta():
    historial = [e(p("oida", "Querido"), i) for i in range(6)]
    g = rc.Gusto.desde(historial, {"canciones": {"saltada": 2}, "artistas": {"id:id_Odiado": 5}}, ahora=HOY)
    cand = rc.combinar([[p("oida", "Querido"), p("nueva", "Nuevo"), p("saltada", "X"),
                         p("conocida", "Querido"), p("otra", "Odiado")]])
    ids = [x["video_id"] for x in rc.puntuar_descubre(cand, g)]
    assert "nueva" in ids and "conocida" in ids
    assert not {"oida", "saltada", "otra"} & set(ids)


def test_saltos_se_guardan_y_se_perdonan():
    class Col:
        def __init__(self):
            self.d = {}

        def estado(self, k, defecto=None):
            return self.d.get(k, defecto)

        def guardar_estado(self, k, v):
            self.d[k] = v

    c = Col()
    rc.anotar_salto(c, p("x", "A"))
    rc.anotar_salto(c, p("x", "A"))
    assert c.d["saltos"]["canciones"]["x"] == 2
    rc.perdonar(c, p("x", "A"))
    assert c.d["saltos"]["canciones"]["x"] == 1


def test_maquina_del_tiempo():
    h = [e(p(f"ano{i}", "A"), 366) for i in range(6)] + [e(p("ano0", "A"), 366), e(p("hoy", "B"), 0)]
    m = rc.maquina_del_tiempo(h, ahora=HOY)
    assert len(m) == 1 and m[0]["titulo"] == "Hace un año"
    assert m[0]["pistas"][0]["video_id"] == "ano0" and "2025" in m[0]["subtitulo"]


def test_mezcla_y_vista_previa():
    m = CH.mix_de_mezcla({"afinidad": 53, "comunes": [{"clave": "yt:comun"}],
                          "mezcla": [{"clave": "yt:a1"}, {"clave": "yt:b1"}, {"clave": "yt:comun"}],
                          "artistas_comunes": ["Bad Bunny"]}, "Beto", "c1")
    assert [x["video_id"] for x in m["pistas"]] == ["comun", "a1", "b1"]
    assert "53 %" in m["subtitulo"] and "Bad Bunny" in m["subtitulo"]
    assert CH.vista_previa({"ultimo_pista": {"titulo": "Tema"}, "ultimo_autor": "yo"}, "yo") == "Tú: ♪ Tema"


def test_datos_del_perfil():
    hoy = date(2026, 11, 14)
    assert legal.edad(date(2000, 11, 15), hoy) == 25
    assert legal.revisar_perfil("Ana", None, "PE") == "Elige tu fecha de nacimiento."
    assert "permiso" in legal.revisar_perfil("Ana", date(2015, 1, 1), "PE", hoy=hoy)
    assert legal.revisar_perfil("Ana", date(2015, 1, 1), "PE", permiso_tutor=True, hoy=hoy) is None
    x = legal.extra_registro(date(2000, 5, 3), "PE", None, True, False)
    assert x["terminos"] == legal.VERSION and x["fecha_nacimiento"] == "2000-05-03" and "genero" not in x
    assert "Política de privacidad" in legal.texto("privacidad")
