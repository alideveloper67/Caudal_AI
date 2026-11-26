# -*- coding: utf-8 -*-
"""Vincular Spotify, YouTube y SoundCloud: permisos (PKCE), tokens, lectura, y poner al día. Sin red."""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from descargador import config, importacion, listas, servicios_externos as SE, vinculadas as V  # noqa: E402
from descargador.catalogo import nueva_pista  # noqa: E402
from descargador.coleccion import Coleccion  # noqa: E402


class Resp:
    def __init__(self, datos=None, estado=200):
        self._d, self.status_code, self.headers = datos, estado, {}

    def json(self):
        if self._d is None:
            raise ValueError
        return self._d


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def perfil(tmp_path, monkeypatch):
    monkeypatch.setattr(SE, "carpeta_perfil", lambda: tmp_path)
    monkeypatch.setitem(SE._config, "datos", None)
    return tmp_path


@pytest.fixture
def col(tmp_path):
    return Coleccion(tmp_path / "c.db")


def activar(monkeypatch, **datos):
    conf = dict(SE.VACIA, **datos)
    monkeypatch.setattr(SE, "configuracion", lambda forzar=False, pedir=None: conf)
    monkeypatch.setitem(SE._config, "datos", conf)


def sesion(servicio, caduca=9e12, **k):
    SE._guardar_sesion(servicio, {"access": "A", "refresh": "R", "caduca": caduca, "client_id": "cid", **k})


def esperar(app, cond, s=10):
    fin = time.time() + s
    while not cond() and time.time() < fin:
        app.processEvents()
        time.sleep(0.01)
    assert cond()


# ---------------------------------------------------------------- permisos

@pytest.mark.parametrize("servicio,host", [("spotify", "accounts.spotify.com"), ("youtube", "accounts.google.com"),
                                           ("soundcloud", "secure.soundcloud.com")])
def test_direccion_de_permiso(servicio, host):
    v, e = SE.nuevo_verificador(), SE.nuevo_estado(servicio)
    u = urlparse(SE.url_autorizar(servicio, "cid", v, e))
    q = parse_qs(u.query)
    assert u.netloc == host and q["state"] == [e] and e.startswith(f"e-{servicio}-")
    assert q["redirect_uri"] == ["https://caudal-musica.netlify.app/api/vincular"]
    assert q["code_challenge"] == [SE.huella(v)] and q["code_challenge_method"] == ["S256"]
    assert "client_secret" not in q
    if servicio == "youtube":
        assert q["scope"] == ["https://www.googleapis.com/auth/youtube.readonly"]
        assert q["access_type"] == ["offline"] and q["prompt"] == ["consent"]


def navegador(respuestas, puerto):
    """Un «navegador» que vuelve a la PC con lo que devuelvan las funciones de `respuestas`."""
    codigos = []

    def abrir(url):
        q = parse_qs(urlparse(url).query)

        def ir():
            for f in respuestas:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/vincular?{f(q['state'][0])}", timeout=5) as r:
                        codigos.append(r.status)
                except urllib.error.HTTPError as e:
                    codigos.append(e.code)
        threading.Thread(target=ir, daemon=True).start()
        return True
    abrir.codigos = codigos
    return abrir


def puerto_libre():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_vincular_youtube_canjea_en_el_servidor_y_guarda_solo_en_el_perfil(perfil, monkeypatch):
    activar(monkeypatch, youtube_client_id="yt-id")
    pedidos = []

    def publicar(url, json=None, **_k):
        pedidos.append((url, json))
        return Resp({"access": "AC", "refresh": "RE", "caduca_en": 3600})
    p = puerto_libre()
    # una vuelta con otro `state` se ignora y se sigue esperando la buena
    abrir = navegador([lambda e: "servicio=youtube&code=malo&state=e-youtube-otro",
                       lambda e: f"servicio=youtube&code=C0D&state={e}"], p)
    assert SE.vincular("youtube", abrir=abrir, publicar=publicar, puerto=p, espera=20)
    assert abrir.codigos[0] == 400
    assert pedidos[0][0].endswith("/api/vincular")
    assert pedidos[0][1]["servicio"] == "youtube" and pedidos[0][1]["code"] == "C0D"
    assert len(pedidos[0][1]["verificador"]) >= 43
    s = json.loads((perfil / "youtube_sesion.json").read_text("utf-8"))
    assert s["refresh"] == "RE" and SE.vinculada("youtube") and not SE.vinculada("spotify")


def test_vincular_spotify_canjea_directo_con_la_misma_vuelta(perfil, monkeypatch):
    activar(monkeypatch, spotify_client_id="sp-id")
    pedidos = []

    def publicar(url, data=None, **_k):
        pedidos.append((url, data))
        return Resp({"access_token": "a", "refresh_token": "r", "expires_in": 3600})
    p = puerto_libre()
    SE.vincular("spotify", abrir=navegador([lambda e: f"code=X&state={e}"], p), publicar=publicar, puerto=p, espera=20)
    url, d = pedidos[0]
    assert url == "https://accounts.spotify.com/api/token" and d["redirect_uri"] == SE.VUELTA
    assert d["client_id"] == "sp-id" and "client_secret" not in d


def test_cancelar_sin_activar_y_error_del_servidor(perfil, monkeypatch):
    activar(monkeypatch)
    with pytest.raises(SE.ErrorServicio, match="archivo"):
        SE.vincular("youtube")
    activar(monkeypatch, soundcloud_client_id="x")
    p = puerto_libre()
    with pytest.raises(SE.ErrorServicio, match="Cancelaste"):
        SE.vincular("soundcloud", abrir=navegador([lambda e: f"error=access_denied&state={e}"], p), puerto=p, espera=20)
    p = puerto_libre()
    with pytest.raises(SE.ErrorServicio, match="caducó"):
        SE.vincular("soundcloud", abrir=navegador([lambda e: f"code=1&state={e}"], p), puerto=p, espera=20,
                    publicar=lambda *a, **k: Resp({"error": "canje", "mensaje": "El permiso caducó."}))
    with pytest.raises(SE.ErrorServicio):
        SE.vincular("soundcloud", abrir=lambda u: True, cancelado=lambda: True, puerto=puerto_libre())
    assert not SE.vinculada("soundcloud")


def test_el_token_se_renueva_y_el_de_soundcloud_se_cambia(perfil):
    sesion("soundcloud", caduca=0)
    cuerpos = []

    def publicar(url, json=None, **_k):
        cuerpos.append(json)
        return Resp({"access": "A2", "refresh": "R2", "caduca_en": 3600})
    assert SE.token("soundcloud", publicar) == "A2" and cuerpos == [{"servicio": "soundcloud", "refresh": "R"}]
    assert SE.token("soundcloud", lambda *a, **k: pytest.fail("aún vale")) == "A2"
    assert SE._leer_sesion("soundcloud")["refresh"] == "R2"
    sesion("youtube", caduca=0)
    assert SE.token("youtube", lambda *a, **k: Resp({"access": "B", "refresh": "", "caduca_en": 10})) == "B"
    assert SE._leer_sesion("youtube")["refresh"] == "R"         # Google no siempre lo repite
    assert SE.token("spotify") == ""


def test_desvincular_borra_y_en_google_retira_el_permiso(perfil):
    pedidos = []
    sesion("youtube")
    sesion("soundcloud")
    SE.desvincular("youtube", lambda url, data=None, **_k: pedidos.append((url, data)))
    assert pedidos == [("https://oauth2.googleapis.com/revoke", {"token": "R"})]
    SE.desvincular("soundcloud", lambda *a, **k: pytest.fail("solo Google"))
    assert not SE.vinculada("youtube") and not SE.vinculada("soundcloud") and not list(perfil.glob("*_sesion.*"))


# ---------------------------------------------------------------- leer

def video(i, categoria="10", titulo="Suena", canal="Junior H - Topic"):
    return {"id": f"{i:011d}", "snippet": {"categoryId": categoria, "title": titulo, "channelTitle": canal,
                                           "thumbnails": {"high": {"url": "u"}}},
            "contentDetails": {"duration": "PT3M5S"}}


def test_youtube_solo_musica_paginado(perfil, monkeypatch):
    sesion("youtube")
    pedidos = []

    def pedir(metodo, url, params=None, headers=None, **_k):
        pedidos.append(params)
        assert headers["Authorization"] == "Bearer A" and params["myRating"] == "like"
        if "pageToken" not in params:
            return Resp({"items": [video(1), video(2, "20")], "nextPageToken": "P"})
        return Resp({"items": [video(3, titulo="Cidtronyck - Esta Noche", canal="CidtronyckVEVO")]})
    monkeypatch.setattr(listas.requests, "request", pedir)
    r = SE.me_gusta("youtube")
    assert len(pedidos) == 2 and [c["externa"] for c in r["canciones"]] == ["yt:00000000001", "yt:00000000003"]
    assert r["canciones"][0] | {} == {"titulo": "Suena", "artista": "Junior H", "duracion": 185, "miniatura": "u",
                                      "url": "https://www.youtube.com/watch?v=00000000001", "externa": "yt:00000000001"}
    assert (r["canciones"][1]["artista"], r["canciones"][1]["titulo"]) == ("Cidtronyck", "Esta Noche")


@pytest.mark.parametrize("estado,texto", [(401, "Vincula otra vez"), (403, "límite"), (500, "rato")])
def test_youtube_errores_contados_sin_jerga(perfil, monkeypatch, estado, texto):
    sesion("youtube")
    monkeypatch.setattr(listas, "_pedir", lambda *a, **k: Resp({}, estado))
    with pytest.raises(SE.ErrorServicio, match=texto):
        SE.me_gusta("youtube")


def test_soundcloud_solo_sigue_enlaces_de_su_api_y_para_en_lo_conocido(perfil, monkeypatch):
    sesion("soundcloud")
    vistos = []

    def pedir(metodo, url, headers=None, **_k):
        vistos.append(url)
        assert headers["Authorization"] == "OAuth A"
        return Resp({"collection": [{"kind": "track", "id": 5, "title": "A - B", "duration": 1000, "user": {}}],
                     "next_href": "https://malo.example/x"})
    monkeypatch.setattr(listas.requests, "request", pedir)
    r = SE.me_gusta("soundcloud")
    assert vistos == ["https://api.soundcloud.com/me/likes/tracks?limit=200&linked_partitioning=true"]
    assert r["canciones"][0]["externa"] == "sc:5"


def test_al_poner_al_dia_se_para_en_la_primera_pagina_conocida(perfil, monkeypatch):
    sesion("spotify")
    vistos = []

    def pedir(metodo, url, **_k):
        vistos.append(url)
        return Resp({"items": [{"track": {"type": "track", "id": f"t{len(vistos)}", "name": "x", "artists": []}}],
                     "next": f"https://api.spotify.com/v1/me/tracks?offset={len(vistos)}"} if len(vistos) < 9 else {"items": []})
    monkeypatch.setattr(listas.requests, "request", pedir)
    r = SE.me_gusta("spotify", conocidas={"sp:t2", "sp:t3"})
    assert len(vistos) == 2 and [c["externa"] for c in r["canciones"]] == ["sp:t1", "sp:t2"]


# ---------------------------------------------------------------- lo que se recuerda

def test_memoria_de_lo_traido(col):
    assert V.info(col, "spotify") == {"mantener": True, "ultima": 0.0, "cuantas": 0, "completa": False}
    V.anotar_traidas(col, "spotify", ["sp:1"], ["sp:2"])
    assert V.conocidas(col, "spotify") == {"sp:1"}               # una que no salió se vuelve a probar...
    V.anotar_traidas(col, "spotify", [], ["sp:2"])
    V.anotar_traidas(col, "spotify", [], ["sp:2"])
    assert V.conocidas(col, "spotify") == {"sp:1", "sp:2"}       # ...tres veces y no más
    assert V.nuevas([{"externa": "sp:1"}, {"externa": "sp:3"}, {"externa": "sp:3"}, {"titulo": "x"}],
                    V.conocidas(col, "spotify")) == [{"externa": "sp:3"}, {"titulo": "x"}]
    V.anotar(col, "spotify", ultima=time.time() - 3600)
    assert not V.toca_sincronizar(col, "spotify")
    V.anotar(col, "spotify", ultima=time.time() - 13 * 3600)
    assert V.toca_sincronizar(col, "spotify")
    V.anotar(col, "spotify", mantener=False)
    assert not V.toca_sincronizar(col, "spotify")
    V.olvidar(col, "spotify")
    assert not V.conocidas(col, "spotify")


def test_los_tokens_no_van_a_la_copia_ni_a_la_nube(perfil, col, tmp_path, monkeypatch):
    from descargador import copia_seguridad as CS
    subidas = []
    col.sincronizador = SimpleNamespace(anotar=lambda *a: subidas.append(a))
    sesion("youtube", refresh="SECRETISIMO")
    V.anotar(col, "youtube", cuantas=3)
    V.anotar_traidas(col, "youtube", ["yt:aaaaaaaaaaa"])
    assert subidas == []
    assert not any("vinculada" in k for k in CS.ESTADO_COPIABLE)
    assert not any("sesion" in n for n in CS.ARCHIVOS_ESCRITORIO)
    ruta = CS.guardar_copia(tmp_path / "x", CS.crear_copia(col, config.Ajustes(), carpeta=perfil))
    with zipfile.ZipFile(ruta) as z:
        for n in z.namelist():
            datos = z.read(n)
            assert b"SECRETISIMO" not in datos and b"yt:aaaaaaaaaaa" not in datos and "sesion" not in n


# ---------------------------------------------------------------- poner al día solo

class Ctx:
    def __init__(self, col):
        self.coleccion = col
        self.ajustes = config.Ajustes()
        self.ventana = None


def test_mantener_al_dia_trae_solo_lo_nuevo(app, perfil, col, monkeypatch):
    from descargador.ui import dialogo_importacion as DI, vincular_auto as VA
    for s in ("spotify", "youtube"):
        sesion(s)
    V.anotar(col, "youtube", ultima=1, completa=True, cuantas=10)
    V.anotar_traidas(col, "youtube", ["yt:viejo"])
    pedidas, buscadas = [], []

    def me_gusta(servicio, conocidas=None, **_k):
        pedidas.append((servicio, conocidas))
        return {"canciones": [{"externa": f"yt:{n}", "titulo": n, "artista": "a"} for n in ("n1", "n2", "no", "viejo")]}
    monkeypatch.setattr(SE, "me_gusta", me_gusta)

    def buscar(c):
        buscadas.append(c["externa"])
        return None if c["titulo"] == "no" else nueva_pista(c["titulo"].rjust(11, "x"), c["titulo"], [{"nombre": "a"}])
    monkeypatch.setattr(DI, "buscar_pista", buscar)
    s = VA.SincronizadorCuentas(Ctx(col))
    fin = []
    s.termino.connect(lambda *a: fin.append(a))
    # Spotify está vinculado pero aún sin la primera vez (esa la pide la persona)
    assert s.revisar() == ["youtube"]
    esperar(app, lambda: fin)
    assert fin == [("youtube", 2)] and pedidas == [("youtube", {"yt:viejo"})]
    assert sorted(buscadas) == ["yt:n1", "yt:n2", "yt:no"]
    assert [p["titulo"] for p in col.lista_me_gusta()] == ["n1", "n2"]      # la más nueva arriba
    assert V.conocidas(col, "youtube") == {"yt:viejo", "yt:n1", "yt:n2"}
    d = V.info(col, "youtube")
    assert d["cuantas"] == 12 and time.time() - d["ultima"] < 60
    assert s.revisar() == []                       # hasta dentro de 12 horas


def test_no_se_pone_al_dia_con_una_importacion_a_medias_ni_si_falla_la_red(app, perfil, col, monkeypatch):
    from descargador.ui import vincular_auto as VA
    sesion("spotify")
    V.anotar(col, "spotify", completa=True)
    s = VA.SincronizadorCuentas(Ctx(col))
    col.guardar_estado(importacion.CLAVE_PENDIENTE, {"canciones": [1]})
    assert s.revisar() == []
    col.guardar_estado(importacion.CLAVE_PENDIENTE, None)

    def falla(*_a, **_k):
        raise SE.ErrorServicio("sin red")
    monkeypatch.setattr(SE, "me_gusta", falla)
    assert s.revisar() == ["spotify"]
    esperar(app, lambda: not s.ocupado)
    assert V.info(col, "spotify")["ultima"] == 0      # no cuenta como hecha: se vuelve a probar


# ---------------------------------------------------------------- la ventana

def dialogo(col):
    from descargador.ui.dialogo_me_gusta import DialogoMeGusta
    return DialogoMeGusta(Ctx(col))


def textos(d):
    return " ".join([w.text() for w in d.findChildren(QLabel)] + [w.text() for w in d.findChildren(QPushButton)])


def test_sin_nada_activado_sirve_igual_y_sin_jerga(app, perfil, col, monkeypatch):
    activar(monkeypatch)
    d = dialogo(col)
    t = textos(d)
    for x in ("Pedir mis datos a Spotify", "Abrir Google Takeout", "Elegir el archivo", "SoundCloud"):
        assert x in t
    for jerga in ("client", "API", "OAuth", "modo de desarrollo", "credencial", "Vincular Spotify  "):
        assert jerga not in t
    assert not [b for b in d.findChildren(QPushButton) if b.text().strip() in ("Vincular Spotify", "Vincular YouTube")]


def test_activado_y_vinculado(app, perfil, col, monkeypatch):
    activar(monkeypatch, youtube_client_id="1", spotify_client_id="2", soundcloud_client_id="3")
    sesion("youtube")
    V.anotar(col, "youtube", ultima=time.time() - 7300, cuantas=1240)
    t = textos(dialogo(col))
    assert "hace 2 horas" in t and "1 240 canciones" in t and "Desvincular" in t and "Sincronizar ahora" in t
    assert "Vincular Spotify" in t and "Vincular SoundCloud" in t and "Vincular YouTube" not in t.replace(
        "Vincular Spotify, YouTube", "")


def test_sincronizar_emite_solo_lo_nuevo_y_dice_si_no_hay(app, perfil, col, monkeypatch):
    activar(monkeypatch, youtube_client_id="1")
    sesion("youtube")
    V.anotar_traidas(col, "youtube", ["yt:1"])
    canciones = [{"titulo": "a", "externa": "yt:1"}, {"titulo": "b", "externa": "yt:2"}]
    monkeypatch.setattr(SE, "me_gusta", lambda s, **k: {"canciones": list(canciones), "titulo": "T", "plataforma": "YouTube Music"})
    d = dialogo(col)
    salio = []
    d.listo.connect(lambda *a: salio.append(a))
    d._sincronizar("youtube")
    esperar(app, lambda: salio)
    assert salio == [([canciones[1]], "T", "YouTube Music", "youtube:me", "youtube")]
    canciones.pop()
    d2 = dialogo(col)
    d2._sincronizar("youtube")
    esperar(app, lambda: "no hay canciones nuevas" in d2.estado.text())
    assert V.info(col, "youtube")["completa"]
    d2._desvincular("youtube")
    monkeypatch.setattr(SE.requests, "post", lambda *a, **k: None)
    esperar(app, lambda: not SE.vinculada("youtube"))
    esperar(app, lambda: "desvinculada" in d2.estado.text())


def test_archivo_y_texto_pegado_desde_la_ventana(app, perfil, col, monkeypatch, tmp_path):
    activar(monkeypatch)
    f = tmp_path / "l.csv"
    f.write_text("title,artist\nA,B\n", encoding="utf-8")
    d = dialogo(col)
    salio = []
    d.listo.connect(lambda *a: salio.append(a))
    d.traer_archivo(str(f))
    esperar(app, lambda: salio)
    assert salio[0][0][0]["titulo"] == "A" and salio[0][3:] == ("archivo:lista", "")
    d = dialogo(col)
    d.listo.connect(lambda *a: salio.append(a))
    d.campo_texto.setPlainText("Yeyo - Oye Morena")
    d._pegado()
    assert salio[1][0][0]["artista"] == "Yeyo"
    d = dialogo(col)
    d.traer_archivo(str(tmp_path / "no.csv"))
    esperar(app, lambda: "No se pudo abrir" in d.estado.text())


def test_la_importacion_apunta_lo_traido_de_la_cuenta(app, perfil, col, monkeypatch):
    from descargador.ui import dialogo_importacion as DI
    monkeypatch.setattr(DI, "buscar_pista", lambda c: None if c["titulo"] == "no" else
                        nueva_pista(c["titulo"].rjust(11, "y"), c["titulo"], [{"nombre": "z"}]))
    canciones = [{"titulo": t, "artista": "z", "externa": f"sp:{t}"} for t in ("uno", "no", "dos")]
    t = DI.nueva(col, canciones, {"tipo": "me_gusta", "servicio": "Spotify", "enlace": "spotify:me", "titulo": "x",
                                  "cuenta": "spotify"})
    d = DI.DialogoImportacion(Ctx(col), t)
    fin = []
    d.terminado.connect(fin.append)
    d.empezar()
    esperar(app, lambda: fin)
    assert V.conocidas(col, "spotify") == {"sp:uno", "sp:dos"}
    i = V.info(col, "spotify")
    assert i["completa"] and i["cuantas"] == 2 and i["ultima"] > 0


def test_un_id_de_video_suelto_se_resuelve_con_el_catalogo(monkeypatch):
    from descargador import catalogo
    from descargador.ui import dialogo_importacion as DI
    cancion = {"microformat": {"microformatDataRenderer": {"category": "Music"}},
               "videoDetails": {"videoId": "dQw4w9WgXcQ", "title": "Never", "author": "Rick - Topic", "lengthSeconds": "213",
                                "thumbnail": {"thumbnails": []}}}
    monkeypatch.setattr(catalogo, "_yt", lambda: SimpleNamespace(get_song=lambda v: cancion))
    p = DI.buscar_pista({"titulo": "", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert p["titulo"] == "Never" and p["artista"] == "Rick" and p["duracion"] == 213
    cancion["microformat"]["microformatDataRenderer"]["category"] = "Gaming"
    assert catalogo.pista_de_video("dQw4w9WgXcQ") is None
