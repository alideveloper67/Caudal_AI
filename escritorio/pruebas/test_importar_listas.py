# -*- coding: utf-8 -*-
"""Traer listas enormes y me gusta de otras apps (escritorio), sin red.

Paginación sin tope (respuestas simuladas de más de 5000 canciones), Spotify con
sus reglas de 2026, SoundCloud con páginas guardadas, emparejado en lotes que se
puede reanudar, y me gusta fusionados sin duplicados (también en la nube).
"""

import json
import os
import sys
import tempfile
import threading
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import importacion, listas  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402
from descargador.sincronizacion import Sincronizador  # noqa: E402

NADA = lambda *_a, **_k: None  # noqa: E731 - «dormir» de mentira


class Resp:
    def __init__(self, estado=200, datos=None, texto=None, cabeceras=None):
        self.status_code = estado
        self._datos = datos
        self.text = texto if texto is not None else json.dumps(datos)
        self.headers = cabeceras or {}

    def json(self):
        if self._datos is None:
            raise ValueError("no es json")
        return self._datos


# ---------------------------------------------------------------- paginar

def test_paginar_no_tiene_tope_de_canciones():
    paginas = 130                                    # 130 x 50 = 6500 canciones

    def pedir(cursor):
        n = cursor or 0
        elementos = [f"c{n * 50 + i}" for i in range(50)]
        return elementos, (n + 1 if n + 1 < paginas else None)

    todas = listas.paginar(pedir)
    assert len(todas) == 6500 and todas[-1] == "c6499"


def test_paginar_se_corta_si_el_servicio_repite_el_cursor():
    vueltas = []

    def pedir(cursor):
        vueltas.append(cursor)
        return ["x"], "siempre-el-mismo"

    assert len(listas.paginar(pedir)) == 2 and len(vueltas) == 2


def test_pedir_espera_y_reintenta_los_429(monkeypatch):
    respuestas = [Resp(429, {}, cabeceras={"Retry-After": "1"}), Resp(503, {}), Resp(200, {"ok": 1})]
    monkeypatch.setattr(listas.requests, "request", lambda *a, **k: respuestas.pop(0))
    esperas = []
    r = listas._pedir("GET", "https://x", dormir=esperas.append)
    assert r.status_code == 200 and len(esperas) == 2


# ---------------------------------------------------------------- Spotify

def _spotify_falso(n_canciones, por_pagina=50, ruta_items="items", prohibido=()):
    """Una API de Spotify de mentira con una lista de n canciones."""
    pedidos = []

    def request(metodo, url, **_k):
        pedidos.append(url)
        for p in prohibido:
            if p in url:
                return Resp(403, {"error": {"status": 403}})
        if url.endswith("/playlists/L1"):
            return Resp(200, {"name": "Enorme", "owner": {"display_name": "Ana"}, "images": []})
        if f"/playlists/L1/{ruta_items}" in url:
            desde = int(url.split("offset=")[1]) if "offset=" in url else 0
            filas = [{"item" if ruta_items == "items" else "track":
                      {"type": "track", "name": f"Tema {i}", "duration_ms": 200000,
                       "artists": [{"name": "Grupo"}]}}
                     for i in range(desde, min(desde + por_pagina, n_canciones))]
            sig = desde + por_pagina
            base = url.split("?")[0]
            nxt = f"{base}?limit={por_pagina}&offset={sig}" if sig < n_canciones else None
            return Resp(200, {"items": filas, "next": nxt, "total": n_canciones})
        return Resp(404, {})

    return request, pedidos


def test_spotify_lista_de_mas_de_5000_llega_entera(monkeypatch):
    request, _ = _spotify_falso(7321)
    monkeypatch.setattr(listas.requests, "request", request)
    d = listas._spotify_api("playlist", "L1", "tok", dormir=NADA)
    assert len(d["canciones"]) == 7321          # antes se cortaba en 5000
    assert d["canciones"][0] == {"titulo": "Tema 0", "artista": "Grupo", "duracion": 200}


def test_spotify_si_items_esta_prohibido_prueba_la_ruta_de_siempre(monkeypatch):
    request, pedidos = _spotify_falso(250, por_pagina=100, ruta_items="tracks", prohibido=("/items",))
    monkeypatch.setattr(listas.requests, "request", request)
    d = listas._spotify_api("playlist", "L1", "tok", dormir=NADA)
    assert len(d["canciones"]) == 250 and any("/tracks" in p for p in pedidos)


def test_spotify_lista_ajena_cae_a_la_pagina_publica_y_lo_explica(monkeypatch):
    request, _ = _spotify_falso(300, prohibido=("/items", "/tracks"))
    monkeypatch.setattr(listas.requests, "request", request)
    monkeypatch.setattr(listas, "_token_api_spotify", lambda _a: "tok")
    monkeypatch.setattr(listas, "_spotify_pagina", lambda t, i: {
        "titulo": "Enorme", "autor": "", "portada": "",
        "canciones": [{"titulo": f"T{i}", "artista": "A", "duracion": 1} for i in range(50)]})
    d = listas._spotify("https://open.spotify.com/playlist/L1", {}, dormir=NADA)
    assert len(d["canciones"]) == 50 and not d["completa"]
    assert d["aviso"] == listas.AVISO_SPOTIFY_AJENA


def test_spotify_sin_nada_configurado_usa_la_pagina_y_dice_que_falta(monkeypatch):
    monkeypatch.setattr(listas, "_token_api_spotify", lambda _a: "")
    monkeypatch.setattr(listas, "_spotify_por_funcion", MagicMock(side_effect=listas.SinCredenciales()))
    monkeypatch.setattr(listas, "_spotify_pagina", lambda t, i: {
        "titulo": "X", "autor": "", "portada": "",
        "canciones": [{"titulo": f"T{i}", "artista": "A", "duracion": 1} for i in range(50)]})
    d = listas._spotify("https://open.spotify.com/playlist/abc", {}, dormir=NADA)
    assert d["aviso"] == listas.AVISO_SPOTIFY_SIN_CONEXION


def test_spotify_por_la_funcion_de_caudal_sigue_los_trozos(monkeypatch):
    def request(metodo, url, params=None, **_k):
        desde = int(params["desde"])
        canciones = [{"titulo": f"T{i}", "artista": "A", "duracion": 1}
                     for i in range(desde, min(desde + 1000, 5500))]
        return Resp(200, {"titulo": "L", "autor": "A", "portada": "", "canciones": canciones,
                          "siguiente": desde + 1000 if desde + 1000 < 5500 else None})
    monkeypatch.setattr(listas.requests, "request", request)
    d = listas._spotify_por_funcion("playlist", "L1", dormir=NADA)
    assert len(d["canciones"]) == 5500 and d["titulo"] == "L"


def test_la_funcion_sin_publicar_cuenta_como_sin_credenciales(monkeypatch):
    monkeypatch.setattr(listas.requests, "request",
                        lambda *a, **k: Resp(404, None, texto="<html>Page not found</html>"))
    with pytest.raises(listas.SinCredenciales):
        listas._spotify_por_funcion("playlist", "L1", dormir=NADA)


def test_pistas_de_pagina_entiende_albumes_listas_y_me_gusta():
    pagina = {"items": [
        {"name": "De album", "artists": []},
        {"item": {"type": "track", "name": "De lista", "artists": []}},
        {"track": {"name": "De me gusta", "artists": []}, "added_at": "2026"},
        {"item": {"type": "episode", "name": "Un podcast"}},
        None,
    ]}
    assert [p["name"] for p in listas._pistas_de_pagina(pagina)] == ["De album", "De lista", "De me gusta"]


# ---------------------------------------------------------------- SoundCloud

def test_tipos_de_enlace_de_soundcloud():
    t = listas.tipo_soundcloud
    assert t("https://soundcloud.com/ana/sets/verano?si=1")[0] == "lista"
    assert t("https://soundcloud.com/ana/likes") == ("me_gusta", "ana")
    assert t("https://soundcloud.com/ana")[0] == "perfil"
    assert t("https://soundcloud.com/ana/un-tema")[0] == "cancion"
    assert t("https://on.soundcloud.com/AbC12")[0] == "corto"
    assert t("https://soundcloud.com/discover")[0] == ""
    assert listas.detectar_plataforma("https://m.soundcloud.com/ana/sets/x") == "soundcloud"


def test_soundcloud_me_gusta_paginados_sin_tope(monkeypatch):
    total = 5432

    def request(metodo, url, **_k):
        desde = int(url.split("offset=")[1]) if "offset=" in url else 0
        coleccion = [{"kind": "track", "title": f"Grupo - Tema {i}", "duration": 180000,
                      "user": {"username": "subidor"}} for i in range(desde, min(desde + 200, total))]
        sig = desde + 200
        nxt = (f"{listas.API_SOUNDCLOUD}/users/1/likes/tracks?linked_partitioning=true&limit=200"
               f"&offset={sig}") if sig < total else None
        return Resp(200, {"collection": coleccion, "next_href": nxt})

    monkeypatch.setattr(listas.requests, "request", request)
    c = listas.soundcloud_paginado(
        f"{listas.API_SOUNDCLOUD}/users/1/likes/tracks?linked_partitioning=true&limit=200", "tok",
        dormir=NADA)
    assert len(c) == total
    assert c[0] == {"titulo": "Tema 0", "artista": "Grupo", "duracion": 180}


def test_soundcloud_no_sigue_enlaces_fuera_de_su_api(monkeypatch):
    monkeypatch.setattr(listas.requests, "request", lambda *a, **k: Resp(200, {
        "collection": [{"title": "Uno", "user": {"username": "a"}}],
        "next_href": "https://otro-sitio.example/robar"}))
    assert len(listas.soundcloud_paginado(f"{listas.API_SOUNDCLOUD}/x", "t", dormir=NADA)) == 1


PAGINA_SC = ('<html><script>window.__sc_hydration = ' + json.dumps([
    {"hydratable": "apiClient", "data": {"id": "NO-SE-USA"}},
    {"hydratable": "playlist", "data": {
        "title": "Chill", "track_count": 48, "user": {"username": "chillhop"},
        "tracks": [{"id": i, "title": f"Artista {i} - Tema {i}", "duration": 120000,
                    "user": {"username": "chillhop"}} for i in range(5)]
                  + [{"id": 100 + i, "kind": "track"} for i in range(43)]}},
]) + ';</script></html>')


def test_soundcloud_pagina_publica_trae_lo_que_ensena():
    datos, total = listas.leer_soundcloud_pagina(PAGINA_SC)
    assert total == 48 and len(datos["canciones"]) == 5
    assert datos["canciones"][0]["artista"] == "Artista 0"


def test_soundcloud_sin_credenciales_explica_lo_que_falta(monkeypatch):
    monkeypatch.setattr(listas, "_soundcloud_por_funcion", MagicMock(side_effect=listas.SinCredenciales()))
    monkeypatch.setattr(listas.requests, "get", lambda *a, **k: Resp(200, None, texto=PAGINA_SC))
    d = listas.leer("https://soundcloud.com/chillhop/sets/chill", {})
    assert d["total"] == 5 and not d["completa"] and "5 de sus 48" in d["aviso"]
    with pytest.raises(listas.ErrorLista) as e:
        listas.leer("https://soundcloud.com/chillhop/likes", {})
    assert "conexión oficial" in str(e.value)


def test_me_gusta_de_youtube_explica_como_pasarlos():
    with pytest.raises(listas.ErrorLista) as e:
        listas.leer("https://music.youtube.com/playlist?list=LM", {})
    assert "Agregar a playlist" in str(e.value)


# ---------------------------------------------------------------- emparejado en lotes

def _canciones(n):
    return [{"titulo": f"Tema {i}", "artista": "Grupo", "duracion": 200} for i in range(n)]


def test_emparejar_en_lotes_en_orden_y_con_avance():
    lotes, avances = [], []
    activos, maximo = [0], [0]
    cerrojo = threading.Lock()

    def buscar(c):
        with cerrojo:
            activos[0] += 1
            maximo[0] = max(maximo[0], activos[0])
        n = int(c["titulo"].split()[1])
        with cerrojo:
            activos[0] -= 1
        return None if n % 10 == 0 else {"clave": f"yt:{n:011d}", "video_id": f"{n:011d}"}

    r = importacion.emparejar(_canciones(5300), buscar, lote=50, hilos=4,
                              al_lote=lambda fin, p, s: lotes.append((fin, p, s)),
                              al_avanzar=lambda h, t: avances.append((h, t)))
    assert r["hechas"] == 5300 and r["encontradas"] == 4770 and len(r["no_encontradas"]) == 530
    assert len(lotes) == 106 and lotes[-1][0] == 5300
    claves = [p["clave"] for _f, ps, _s in lotes for p in ps]
    assert claves == sorted(claves)                     # el orden de la lista se respeta
    assert avances[-1] == (5300, 5300) and maximo[0] <= 4


def test_emparejar_se_reanuda_donde_quedo_y_se_puede_pausar():
    hechas = []
    parar = {"ya": False}

    def al_lote(fin, p, s):
        hechas.append(fin)
        if fin >= 200:
            parar["ya"] = True

    r = importacion.emparejar(_canciones(1000), lambda c: {"clave": "yt:x", "video_id": "x"},
                              lote=100, al_lote=al_lote, cancelado=lambda: parar["ya"])
    assert r["cancelado"] and hechas == [100, 200]
    resto = []
    r2 = importacion.emparejar(_canciones(1000), lambda c: {"clave": "yt:x", "video_id": "x"},
                               desde=200, lote=100, al_lote=lambda f, p, s: resto.append(f))
    assert not r2["cancelado"] and resto[0] == 300 and resto[-1] == 1000


def test_un_fallo_de_red_se_reintenta_y_no_cuenta_como_no_encontrada():
    intentos = []

    def buscar(q):
        intentos.append(q)
        if len(intentos) < 3:
            raise ConnectionError("sin red")
        return [{"video_id": "abcdefghijk", "duracion": 201}]

    p = importacion.resolver_una({"titulo": "Tema", "artista": "Grupo", "duracion": 200}, buscar,
                                 dormir=NADA)
    assert p["video_id"] == "abcdefghijk" and len(intentos) == 3


def test_elegir_prefiere_la_duracion_parecida():
    c = {"duracion": 200}
    assert importacion.elegir(c, [{"video_id": "a", "duracion": 600},
                                  {"video_id": "b", "duracion": 202}])["video_id"] == "b"
    assert importacion.elegir(c, []) is None


def test_el_avance_se_escribe_como_en_espanol():
    assert importacion.texto_avance(1240, 5300) == "1 240 de 5 300"


# ---------------------------------------------------------------- me gusta sin duplicados

@pytest.fixture(scope="module")
def plantilla(tmp_path_factory):
    ruta = tmp_path_factory.mktemp("plantilla") / "h.db"
    Coleccion(ruta).con.close()
    return ruta


@pytest.fixture
def col(tmp_path, plantilla):
    import shutil
    shutil.copy(str(plantilla), str(tmp_path / "h.db"))
    c = Coleccion(tmp_path / "h.db")
    c.sincronizador = MagicMock()
    return c


def _pista(vid, titulo, artista="Grupo"):
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": titulo,
            "artista": artista, "artistas": [{"nombre": artista, "id": ""}]}


def test_fusion_de_me_gusta_sin_duplicados(col):
    col.alternar_me_gusta(_pista("aaaaaaaaaaa", "Ya me gustaba"))
    col.con.execute("DELETE FROM pendientes")
    traidas = [
        _pista("bbbbbbbbbbb", "Nueva 1"),
        _pista("aaaaaaaaaaa", "Ya me gustaba"),                     # misma clave
        _pista("ccccccccccc", "Ya me gustaba (Official Video)"),    # misma canción, otro video
        _pista("ddddddddddd", "Nueva 2"),
        _pista("bbbbbbbbbbb", "Nueva 1"),                           # repetida en la tanda
    ]
    anadidas, repetidas = col.agregar_me_gusta_varios(traidas)
    assert (anadidas, repetidas) == (2, 3)
    assert col.total_me_gusta() == 3
    orden = [p["titulo"] for p in col.lista_me_gusta()]
    assert orden.index("Nueva 1") < orden.index("Nueva 2")        # se respeta el orden traído
    # volver a sincronizar no añade nada
    assert col.agregar_me_gusta_varios(traidas) == (0, 5)


def test_los_me_gusta_traidos_suben_a_la_nube_de_400_en_400(col):
    pistas = [_pista(f"{i:011d}", f"Tema {i}") for i in range(1000)]
    assert col.agregar_me_gusta_varios(pistas) == (1000, 0)
    ops = [(f["op"], json.loads(f["datos"])) for f in col.con.execute("SELECT op, datos FROM pendientes")]
    assert [op for op, _ in ops] == ["me_gusta_varios"] * 3
    assert [len(d["items"]) for _, d in ops] == [400, 400, 200]


def test_una_lista_enorme_va_a_la_nube_por_trozos(col):
    lid = col.crear_lista("Enorme")
    col.con.execute("DELETE FROM pendientes")
    col.agregar_a_lista(lid, [_pista(f"{i:011d}", f"T{i}") for i in range(5300)])
    tamanos = [len(json.loads(f["datos"])["items"])
               for f in col.con.execute("SELECT datos FROM pendientes WHERE op = 'items_poner'")]
    assert sum(tamanos) == 5300 and max(tamanos) == 400
    assert len(col.pistas_de_lista(lid)) == 5300


class NubeMeGusta:
    """Como PostgREST: nunca más de 1000 filas por respuesta."""

    def __init__(self, n):
        self.filas = [{"clave": f"yt:{i:011d}", "datos": {"titulo": f"T{i}"},
                       "fecha": "2026-01-01T00:00:00+00:00"} for i in range(n)]
        self.subidas = []

    def pedir(self, metodo, ruta, json=None, cabeceras=None, **_k):
        if metodo == "POST":
            self.subidas.append((ruta, json))
            return []
        if ruta.startswith("me_gusta?"):
            import re
            limite = int(re.search(r"limit=(\d+)", ruta).group(1)) if "limit=" in ruta else 1000
            desde = int(re.search(r"offset=(\d+)", ruta).group(1)) if "offset=" in ruta else 0
            return self.filas[desde:desde + min(limite, 1000)]
        return []


def test_traer_mas_de_1000_me_gusta_no_borra_los_de_esta_pc(col):
    nube = NubeMeGusta(3500)
    for f in nube.filas:
        col.con.execute("INSERT INTO me_gusta (clave, fecha) VALUES (?, 1)", (f["clave"],))
    col.con.commit()
    s = Sincronizador(col, {"sesion": nube})
    s._traer(col.con)
    assert col.total_me_gusta() == 3500           # antes quedaban 1000


def test_la_orden_me_gusta_varios_sube_con_su_fecha(col):
    nube = NubeMeGusta(0)
    s = Sincronizador(col, {"sesion": nube})
    s._enviar("me_gusta_varios", {"items": [{"clave": "yt:aaaaaaaaaaa", "datos": {"t": 1},
                                             "fecha": 1700000000}]})
    ruta, filas = nube.subidas[-1]
    assert ruta.startswith("me_gusta?on_conflict=user_id,clave")
    assert filas[0]["clave"] == "yt:aaaaaaaaaaa" and filas[0]["fecha"].startswith("2023-11-14")


def test_fuentes_para_volver_a_sincronizar(col):
    importacion.anotar_fuente(col, "SoundCloud", "https://soundcloud.com/ana/likes", "Me gusta de ana", 10, 2)
    importacion.anotar_fuente(col, "Spotify", "spotify:me", "Me gusta de Spotify", 5, 0)
    importacion.anotar_fuente(col, "SoundCloud", "https://soundcloud.com/ana/likes", "Me gusta de ana", 3, 0)
    f = col.estado(importacion.CLAVE_FUENTES)
    assert [x["enlace"] for x in f] == ["https://soundcloud.com/ana/likes", "spotify:me"]
    assert f[0]["anadidas"] == 3


# ---------------------------------------------------------------- pantallas (Qt sin ventana)

@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _ctx(col):
    from PySide6.QtCore import QObject, Signal

    class Ctx(QObject):
        listas_cambio = Signal()

    c = Ctx()
    c.coleccion = col
    c.ajustes = {}
    return c


def test_el_dialogo_pinta_5000_canciones_y_marca_todas_sin_trabarse(app):
    import time as _t
    from descargador.ui.dialogo_listas import DialogoListas
    d = DialogoListas({})
    datos = {"plataforma": "YouTube", "titulo": "Enorme", "total": 5300, "aviso": "",
             "canciones": [{"titulo": f"T{i}", "artista": "A", "duracion": 200} for i in range(5300)]}
    t0 = _t.perf_counter()
    d._pintar(datos)
    d.casilla_todas.setChecked(False)
    d.casilla_todas.setChecked(True)
    assert _t.perf_counter() - t0 < 10
    assert d._marcadas == 5300 and "5 300" in d.bt_guardar.text()
    from PySide6.QtCore import Qt
    d.canciones.item(0).setCheckState(Qt.Unchecked)
    assert d._marcadas == 5299 and len(d._elegidas()) == 5299
    recibido = []
    d.a_me_gusta.connect(lambda *a: recibido.append(a))
    d._a_me_gusta()
    assert len(recibido[0][0]) == 5299 and recibido[0][2] == "YouTube"


def test_el_dialogo_de_avance_guarda_por_lotes_y_se_puede_reanudar(app, col, monkeypatch):
    from PySide6.QtCore import QCoreApplication
    from descargador.ui import dialogo_importacion as DI
    canciones = [{"titulo": f"Tema {i}", "artista": "Grupo", "duracion": 200} for i in range(230)]

    def falsa(c):
        n = int(c["titulo"].split()[1])
        return None if n % 10 == 7 else _pista(f"{n:011d}", c["titulo"])

    monkeypatch.setattr(DI, "buscar_pista", falsa)
    ctx = _ctx(col)
    trabajo = DI.nueva(col, canciones, {"tipo": "lista", "nombre": "Grande", "plataforma": "Spotify"})
    assert DI.pendiente(col)["hechas"] == 0           # apuntada antes de empezar
    dlg = DI.DialogoImportacion(ctx, trabajo)
    fin = []
    dlg.terminado.connect(fin.append)
    dlg.empezar()
    import time as _t
    limite = _t.time() + 30
    while not fin and _t.time() < limite:
        QCoreApplication.processEvents()
        _t.sleep(0.01)
    assert fin and fin[0]["acabo"]
    lid = trabajo["destino"]["lista_id"]
    assert len(col.pistas_de_lista(lid)) == 207
    assert len(fin[0]["no_encontradas"]) == 23
    assert DI.pendiente(col) is None
    assert "207 canciones" in dlg.resumen() and "23 no se encontraron" in dlg.resumen()


def test_dialogo_me_gusta_explica_lo_que_falta_sin_conexiones(app, col, monkeypatch):
    from PySide6.QtWidgets import QLabel
    from descargador import servicios_externos
    monkeypatch.setattr(servicios_externos, "configuracion", lambda forzar=False: {
        "spotify_client_id": "", "spotify": False, "soundcloud": False})
    from descargador.ui.dialogo_me_gusta import DialogoMeGusta
    d = DialogoMeGusta(_ctx(col))
    textos = " ".join(l.text() for l in d.findChildren(QLabel))
    assert "aún no está activada" in textos           # Spotify
    assert "Agregar a playlist" in textos             # YouTube Music
    assert "SoundCloud aún no está activada" in textos


def test_spotify_pkce_url_sin_secreto():
    from urllib.parse import parse_qs, urlparse
    from descargador import servicios_externos as SE
    v = SE.nuevo_verificador()
    q = parse_qs(urlparse(SE.url_autorizar_spotify("cid", v, "est")).query)
    assert q["code_challenge"][0] == SE.huella(v) and q["code_challenge_method"][0] == "S256"
    assert q["redirect_uri"][0] == "http://127.0.0.1:43821/spotify"
    assert "client_secret" not in q
