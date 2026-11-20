# -*- coding: utf-8 -*-
"""Recomendador de canciones parecidas (tarea A) y artistas favoritos (tarea B).

Sin internet: datos falsos, sesión falsa y Qt offscreen."""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QBuffer, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import generos, nube, recomendador as rc  # noqa: E402
from descargador import gustos as G  # noqa: E402
from descargador import mixes  # noqa: E402

AHORA = datetime(2026, 11, 16, 20, 0)
CARPETA_CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_gustos")


def pista(vid, artista, titulo=None, aid=None, album=None):
    vid = vid.ljust(11, "x")[:11]
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": titulo or f"Tema {vid}",
            "artista": artista, "artistas": [{"id": aid or f"UC_{artista}", "nombre": artista}],
            "album": {"nombre": album or "", "id": ""}, "duracion": 200, "miniatura": ""}


def escucha(p, dias=1):
    return {"pista": p, "fecha": AHORA - timedelta(days=dias), "contexto": ""}


CUMBIA = [pista(f"cum{i}", a, f"Cumbia de {a} {i}") for i, a in enumerate(
    ["Grupo 5", "Corazón Serrano", "Agua Marina", "Armonía 10", "Marisol", "Grupo 5", "Agua Marina"])]
ROCK = [pista(f"roc{i}", a, f"Rock {i}") for i, a in enumerate(
    ["Metallica", "Nirvana", "Queen", "Soda Stereo", "AC/DC"])]


def ids(lista):
    return [p["video_id"] for p in lista]


# ====================================================================== A: género e idioma

def test_genero_de_se_deduce_de_los_datos():
    assert generos.genero_de(pista("a", "Grupo 5", "Cómo te extraño")) == "cumbia"
    assert generos.genero_de(pista("b", "Metallica", "One")) == "rock"
    assert generos.genero_de(pista("c", "Bad Bunny", "Tití me preguntó")) == "urbano"
    assert generos.genero_de(pista("d", "Alguien Raro", "Algo", album="Salsa Brava")) == "salsa"
    assert generos.genero_de(pista("e", "Desconocido", "Nada")) is None
    # lo que se sabe del artista completa el título sin pistas
    assert generos.genero_de(pista("f", "Desconocido", "Nada"), {"id:UC_Desconocido": "rock"}) == "rock"


def test_idioma_y_epoca():
    assert generos.idioma_de(pista("a", "x", "Te quiero mucho, mi amor")) == "es"
    assert generos.idioma_de(pista("b", "x", "I love you baby, never go")) == "en"
    assert generos.idioma_de(pista("c", "x", "안녕")) == "ko"
    assert generos.idioma_de(pista("d", "x", "Zzz")) is None
    assert generos.epoca_de(pista("e", "x", "Hits 1998")) == 1998
    assert generos.epoca_de({"anio": 2015}) == 2015
    assert generos.compat_idioma("es", "en") < 1 and generos.compat_epoca(1980, 2020) < 1


# ====================================================================== A: puntuar_cola

def gusto_vacio(**kw):
    return rc.Gusto(**kw)


def test_una_cancion_de_cumbia_no_trae_rock():
    semilla = pista("sem", "Grupo 5", "Cómo te extraño", aid="UC_g5")
    # YouTube Music mete rock arriba: el género lo baja
    fuentes = {"siguientes": ROCK[:3] + CUMBIA[:5], "relacionados": ROCK[3:] + CUMBIA[5:]}
    cola = rc.puntuar_cola(semilla, fuentes, gusto_vacio(), largo=12)
    posiciones_rock = [i for i, p in enumerate(cola) if p in ROCK]
    posiciones_cumbia = [i for i, p in enumerate(cola) if p in CUMBIA]
    assert posiciones_cumbia, "debe traer cumbia"
    assert not posiciones_rock or min(posiciones_rock) > max(posiciones_cumbia)
    assert ids(cola)[:6] and all(p not in ROCK for p in cola[:6])


def test_lo_saltado_hoy_se_excluye_y_lo_oido_sale_al_final_o_no_sale():
    semilla = pista("sem", "Grupo 5", "Hola amor")
    fuentes = {"siguientes": CUMBIA}
    g = gusto_vacio(saltados_hoy={CUMBIA[0]["video_id"]}, ultimas={CUMBIA[1]["video_id"]})
    cola = rc.puntuar_cola(semilla, fuentes, g, largo=10)
    assert CUMBIA[0]["video_id"] not in ids(cola)               # saltada hoy: fuera
    assert CUMBIA[1]["video_id"] not in ids(cola[:-1])          # ya oída: nunca antes del final
    estricta = rc.puntuar_cola(semilla, fuentes, g, largo=10, estricto=True)
    assert CUMBIA[1]["video_id"] not in ids(estricta)           # en estricto, ni al final
    # lo saltado muchas veces antes también queda fuera
    g2 = gusto_vacio(saltos={CUMBIA[2]["video_id"]: 2})
    assert CUMBIA[2]["video_id"] not in ids(rc.puntuar_cola(semilla, fuentes, g2, largo=10))


def test_los_gustos_y_los_me_gusta_suben_el_puntaje():
    semilla = pista("sem", "Grupo 5", "Hola amor")
    a = pista("aaaa", "Artista Uno", "Cumbia uno", aid="UC_a")
    b = pista("bbbb", "Artista Dos", "Cumbia dos", aid="UC_b")
    fuentes = {"siguientes": [a, b]}                 # a gana de salida por posición
    assert ids(rc.puntuar_cola(semilla, fuentes, gusto_vacio()))[0] == "aaaaxxxxxxx"
    g = gusto_vacio(gustos={"id:UC_b": 1.0})
    assert ids(rc.puntuar_cola(semilla, fuentes, g))[0] == "bbbbxxxxxxx"
    g2 = gusto_vacio(gustados={"bbbbxxxxxxx"})
    assert ids(rc.puntuar_cola(semilla, fuentes, g2))[0] == "bbbbxxxxxxx"


def test_gusto_desde_usa_gustos_me_gusta_y_saltos():
    hist = [escucha(pista(f"h{i}", "Grupo 5", "Cumbia"), i) for i in range(1, 6)]
    salto = {"canciones": {}, "artistas": {"id:UC_Grupo 5": 3},
             "hoy": {"dia": mixes.clave_dia(AHORA), "vids": ["zzzzzzzzzzz"]}}
    g = rc.Gusto.desde(hist, salto, ahora=AHORA, gustos=[{"nombre": "Metallica", "id": "UCm", "portada": ""}],
                       me_gusta=[pista("lk", "Queen", "Rock", aid="UCq")])
    assert g.saltados_hoy == {"zzzzzzzzzzz"}
    assert g.bono_gusto(pista("x", "Metallica", aid="UCm")) == 1.0
    assert g.afinidad(pista("x", "Metallica", aid="UCm")) >= 0.6
    assert g.me_gusta(pista("lk", "Queen", aid="UCq")) == 1.0
    assert g.me_gusta(pista("otra", "Queen", aid="UCq")) > 0
    sin = rc.Gusto.desde(hist, {}, ahora=AHORA)
    assert g.artistas["id:UC_Grupo 5"] < sin.artistas["id:UC_Grupo 5"]     # los saltos restan
    assert len(g.ultimas) == 5
    # otro día: lo saltado «hoy» ya no cuenta
    manana = rc.Gusto.desde(hist, salto, ahora=AHORA + timedelta(days=1))
    assert manana.saltados_hoy == set()


def test_diversidad_no_mas_de_dos_seguidas_del_mismo_artista():
    semilla = pista("sem", "Grupo 5", "Hola amor")
    muchas = [pista(f"g5_{i}", "Grupo 5", f"Cumbia {i}", aid="UC_g5") for i in range(6)]
    otras = [pista(f"ot{i}", f"Cumbia Grupo {i}", f"Cumbia {i}") for i in range(6)]
    cola = rc.puntuar_cola(semilla, {"siguientes": muchas + otras}, gusto_vacio(), largo=12)
    arts = [p["artista"] for p in cola]
    for i in range(len(arts) - 2):
        assert not (arts[i] == arts[i + 1] == arts[i + 2]), arts
    assert arts.count("Grupo 5") <= rc.MAX_POR_ARTISTA
    assert len(rc.separar_artistas(muchas)) == len(muchas)       # no pierde canciones


def test_determinista_con_semilla():
    semilla = pista("sem", "Grupo 5", "Hola amor")
    fuentes = {"siguientes": CUMBIA + ROCK, "relacionados": list(reversed(CUMBIA))}
    a = rc.puntuar_cola(semilla, fuentes, gusto_vacio(), largo=10, semilla_rng=7)
    b = rc.puntuar_cola(semilla, fuentes, gusto_vacio(), largo=10, semilla_rng=7)
    assert ids(a) == ids(b)


def test_descubrimiento_artistas_nuevos_afines():
    semilla = pista("sem", "Grupo 5", "Hola amor")
    conocidos = [pista(f"k{i}", f"Conocido {i % 4}", f"Cumbia {i}", aid=f"UCk{i % 4}") for i in range(30)]
    nuevos = [pista(f"n{i}", f"Nuevo {i}", f"Cumbia nueva {i}", aid=f"UCn{i}") for i in range(10)]
    hist = [escucha(p, 2) for p in conocidos]
    g = rc.Gusto.desde(hist, {}, ahora=AHORA)
    g.ultimas = set()
    cola = rc.puntuar_cola(semilla, {"siguientes": conocidos + nuevos}, g, largo=20, semilla_rng=1)
    n_nuevos = sum(1 for p in cola if p["video_id"].startswith("n"))
    assert 3 <= n_nuevos <= 6, n_nuevos       # ~20 %
    # los nuevos de otro género NO se cuelan como «descubrimiento»
    rock_nuevo = [pista(f"r{i}", f"Banda Rock {i}", f"Rock duro {i}") for i in range(10)]
    cola2 = rc.puntuar_cola(semilla, {"siguientes": conocidos[:6] + rock_nuevo}, g, largo=10)
    assert all(not p["video_id"].startswith("r") for p in cola2[:5])


# ====================================================================== A: con red falsa

@pytest.fixture
def col(tmp_path):
    from descargador.coleccion import Coleccion
    c = Coleccion(tmp_path / "h.db")
    yield c
    c.con.close()


def test_radio_inteligente_junta_fuentes_y_respeta_el_genero(col, monkeypatch):
    sem = pista("sem", "Grupo 5", "Hola amor", aid="UC_g5")
    monkeypatch.setattr(rc.catalogo, "radio", lambda v, limite=50: {
        "pistas": ROCK + [sem] + CUMBIA[:4], "letras_id": "L", "relacionados_id": "R"})
    monkeypatch.setattr(rc.catalogo, "relacionados", lambda v: [{"elementos": CUMBIA[3:]}])
    deartista = {"secciones": [{"elementos": [pista("art1", "Grupo 5", "Otra de Grupo 5", aid="UC_g5"),
                                              {"tipo": "artista", "id": "UC_otro", "titulo": "Otro"}]}]}
    monkeypatch.setattr(rc.catalogo, "artista", lambda i: deartista if i == "UC_g5" else {
        "secciones": [{"elementos": [pista("par1", "Los Parecidos", "Cumbia parecida", aid="UC_otro")]}]})
    rc._CACHE_ARTISTA.clear()
    r = rc.radio_inteligente(col, sem)
    assert r["letras_id"] == "L" and r["relacionados_id"] == "R"
    v = ids(r["pistas"])
    assert "semxxxxxxxx" not in v and "art1xxxxxxx" in v and "par1xxxxxxx" in v
    assert all(p not in ROCK for p in r["pistas"][:6])


def test_radio_inteligente_sin_red_extra_sigue_funcionando(col, monkeypatch):
    sem = pista("sem", "Grupo 5", "Hola amor")
    monkeypatch.setattr(rc.catalogo, "radio", lambda v, limite=50: {"pistas": CUMBIA[:5]})
    monkeypatch.setattr(rc.catalogo, "relacionados", lambda v: (_ for _ in ()).throw(RuntimeError("sin red")))
    monkeypatch.setattr(rc.catalogo, "artista", lambda i: (_ for _ in ()).throw(RuntimeError("sin red")))
    rc._CACHE_ARTISTA.clear()
    assert len(rc.radio_inteligente(col, sem)["pistas"]) >= 4


def test_anotar_salto_guarda_lo_de_hoy(col):
    p = pista("sal", "Metallica", "One")
    rc.anotar_salto(col, p)
    g = rc.gusto(col)
    assert p["video_id"] in g.saltados_hoy and g.saltos[p["video_id"]] == 1


def test_gusto_lee_gustos_locales(col):
    col.guardar_estado(rc.CLAVE_GUSTOS, {"lista": [{"nombre": "Metallica", "id": "UCm", "portada": ""}]})
    assert rc.gusto(col).bono_gusto(pista("x", "Metallica", aid="UCm")) == 1.0


def test_sugerencias_de_gustos(col, monkeypatch):
    col.guardar_estado(rc.CLAVE_GUSTOS, {"lista": [{"nombre": "Grupo 5", "id": "UC_g5", "portada": ""},
                                                   {"nombre": "Marisol", "id": "UC_mar", "portada": ""}]})
    monkeypatch.setattr(rc.catalogo, "artista", lambda i: {"secciones": [{"elementos": [
        pista(f"{i[-3:]}{n}", "Grupo 5" if i == "UC_g5" else "Marisol", f"Cumbia {n}", aid=i) for n in range(8)]}]})
    rc._CACHE_ARTISTA.clear()
    m = rc.sugerencias_gustos(col, ahora=AHORA)
    assert m and m["total"] >= 5
    assert rc.sugerencias_gustos(col, ahora=AHORA) == m           # una vez al día (guardado)


# ====================================================================== B: guardado

class SesionFalsa:
    user_id = "yo-id"
    access = "token"

    def __init__(self, nube_gustos=None, elegidos=False):
        self.fila = {"gustos": nube_gustos or [], "gustos_elegidos": elegidos}
        self.llamadas = []
        self.sin_red = False

    def pedir(self, metodo, ruta, **kw):
        self.llamadas.append((metodo, ruta, kw))
        if self.sin_red:
            raise nube.SinConexion("sin red")
        if metodo == "GET":
            return [dict(self.fila)]
        if metodo == "PATCH":
            self.fila.update(kw["json"])
            return None


def test_limpiar_maximo_30_sin_repetidos():
    muchos = [{"nombre": f"Artista {i}", "id": f"UC{i}", "portada": ""} for i in range(45)]
    assert len(G.limpiar(muchos)) == 30
    assert len(G.limpiar([{"nombre": "A", "id": "1"}, {"nombre": "a", "id": ""}, {"nombre": ""}, 5])) == 1


def test_guardar_gustos_con_patch_y_copia_local(col):
    s = SesionFalsa()
    g = G.Gustos(s, col)
    assert g.hace_falta_pantalla() is True            # cuenta nueva: gustos_elegidos = false
    assert g.guardar([{"nombre": "Metallica", "id": "UCm", "portada": "http://x/m.jpg"}]) is True
    metodo, ruta, kw = [c for c in s.llamadas if c[0] == "PATCH"][-1]
    assert ruta == "perfiles?id=eq.yo-id"
    assert kw["json"]["gustos_elegidos"] is True and kw["json"]["gustos"][0]["nombre"] == "Metallica"
    assert g.local()["lista"][0]["id"] == "UCm" and not g.local()["pendiente"]
    assert g.hace_falta_pantalla() is False
    assert rc.gusto(col).bono_gusto(pista("x", "Metallica", aid="UCm")) == 1.0   # alimenta al recomendador


def test_omitir_marca_elegidos_y_sin_red_queda_pendiente_y_se_reintenta(col):
    s = SesionFalsa()
    g = G.Gustos(s, col)
    s.sin_red = True
    assert g.guardar([], omitido=True) is False
    assert g.local()["pendiente"] and g.local()["elegidos"]
    assert g.hace_falta_pantalla() is False           # ya contestó: no se vuelve a preguntar
    s.sin_red = False
    assert g.sincronizar() == []
    assert not g.local()["pendiente"]
    assert s.fila["gustos_elegidos"] is True


def test_sincronizar_trae_los_gustos_de_otro_dispositivo(col):
    s = SesionFalsa([{"nombre": "Queen", "id": "UCq", "portada": ""}], elegidos=True)
    g = G.Gustos(s, col)
    assert g.hace_falta_pantalla() is False
    assert g.local()["lista"][0]["nombre"] == "Queen"


def test_sin_red_al_entrar_no_estorba(col):
    s = SesionFalsa()
    s.sin_red = True
    assert G.Gustos(s, col).hace_falta_pantalla() is False


# ====================================================================== B: pantalla

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _png(i):
    img = QImage(300, 300, QImage.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 300, 300)
    g.setColorAt(0, QColor.fromHsv((i * 37) % 360, 190, 235))
    g.setColorAt(1, QColor.fromHsv((i * 37 + 70) % 360, 220, 90))
    p.fillRect(img.rect(), g)
    p.setBrush(QColor(255, 255, 255, 70))
    p.setPen(Qt.NoPen)
    p.drawEllipse(80, 70, 140, 140)
    p.end()
    b = QBuffer()
    b.open(QBuffer.WriteOnly)
    img.save(b, "PNG")
    return bytes(b.data())


@pytest.fixture
def pantalla_falsa(monkeypatch, app):
    from descargador.ui import imagenes, pantalla_gustos as PG
    monkeypatch.setattr(imagenes, "_leer", lambda url: _png(abs(hash(url)) % 1000) if url else b"")
    PG._RESUELTOS.clear()
    nombres = G.populares("PE")

    def resolver(nombre):
        i = nombres.index(nombre) if nombre in nombres else 0
        return {"nombre": nombre, "id": f"UC{i}", "portada": f"http://img/{i}.jpg"}
    monkeypatch.setattr(G, "resolver_popular", resolver)
    llamadas = []

    def buscar(texto, filtro=None, limite=20):
        llamadas.append((time.time(), texto, filtro))
        return [{"tipo": "artista", "id": f"UCb{i}", "titulo": f"{texto.title()} {i}",
                 "miniatura": f"http://img/b{i}.jpg"} for i in range(6)]
    monkeypatch.setattr("descargador.catalogo.buscar", buscar)
    return PG, llamadas


def esperar(app, cond, que, maximo=8):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


def _abrir(app, PG, **kw):
    d = PG.PantallaGustos(**kw)
    d.resize(1100, 700)
    d.show()
    esperar(app, lambda: len(d.tarjetas) >= 20, "rejilla")
    for _ in range(20):                  # que termine de acomodarse (columnas, resoluciones)
        app.processEvents()
        time.sleep(0.02)
    esperar(app, lambda: all(t._foto is not None for t in d.tarjetas.values() if t.dato.get('portada')), "fotos")
    return d


def _capturar(app, d, nombre):
    os.makedirs(CARPETA_CAPTURAS, exist_ok=True)
    for _ in range(25):
        app.processEvents()
        time.sleep(0.02)
    ruta = os.path.join(CARPETA_CAPTURAS, nombre)
    d.grab().save(ruta)
    return ruta


def test_pantalla_se_ve_y_se_captura(app, pantalla_falsa):
    PG, _ = pantalla_falsa
    d = _abrir(app, PG)
    assert d.contador.text() == "Ningún artista elegido"
    assert not d.bt_seguir.isEnabled() and d.bt_omitir.isVisible()
    _capturar(app, d, "01_vacia.png")
    for t in list(d.tarjetas.values())[:5]:
        t.alternar.emit(t)
    esperar(app, lambda: all(abs(t._sel - 1) < 0.05 for t in list(d.tarjetas.values())[:5]), "animación")
    assert d.contador.text() == "5 elegidos" and d.bt_seguir.isEnabled()
    assert sum(1 for i in range(d.fila_chips.count()) if d.fila_chips.itemAt(i).widget()) == 5
    ruta = _capturar(app, d, "02_con_elegidos.png")
    assert os.path.getsize(ruta) > 20000
    d.close()


def test_omitir_siempre_disponible_y_marca_omitido(app, pantalla_falsa):
    PG, _ = pantalla_falsa
    d = _abrir(app, PG)
    d.bt_omitir.click()
    assert d.accion == "omitir" and d.lista == []
    d2 = _abrir(app, PG)
    t = list(d2.tarjetas.values())[0]
    t.alternar.emit(t)
    d2.bt_omitir.click()                              # aunque haya elegido, omitir omite
    assert d2.accion == "omitir" and d2.lista == []
    d3 = _abrir(app, PG)
    d3.close()
    assert d3.accion == "omitir"                      # cerrar la ventana = omitir


def test_continuar_devuelve_lo_elegido(app, pantalla_falsa):
    PG, _ = pantalla_falsa
    d = _abrir(app, PG)
    for t in list(d.tarjetas.values())[:3]:
        t.alternar.emit(t)
    d.bt_seguir.click()
    assert d.accion == "guardar" and len(d.lista) == 3
    assert all(x["id"].startswith("UC") for x in d.lista)


def test_maximo_30(app, pantalla_falsa):
    PG, llamadas = pantalla_falsa
    d = _abrir(app, PG)
    d.elegidos.update({f"x{i}": {"nombre": f"X{i}", "id": f"X{i}", "portada": ""} for i in range(29)})
    t1, t2 = list(d.tarjetas.values())[:2]
    t1.alternar.emit(t1)
    assert len(d.elegidos) == 30
    t2.alternar.emit(t2)
    assert len(d.elegidos) == 30 and not t2.marcada and "Máximo" in d.ayuda.text()
    t1.alternar.emit(t1)                              # quitar libera un lugar
    assert len(d.elegidos) == 29
    d.close()


def test_busqueda_con_retraso_de_350_ms(app, pantalla_falsa):
    PG, llamadas = pantalla_falsa
    d = _abrir(app, PG)
    t0 = time.time()
    for txt in ("ka", "kar", "karol"):
        d.campo.setText(txt)
        d.campo.textEdited.emit(txt)
        app.processEvents()
        time.sleep(0.1)
    assert llamadas == []                             # escribiendo seguido: nada todavía
    esperar(app, lambda: len(llamadas) == 1, "una sola búsqueda")
    assert llamadas[0][1] == "karol" and llamadas[0][2] == "artistas"
    # 350 ms después de la última tecla (los QTimer de Qt pueden adelantarse hasta un 5 %)
    assert llamadas[0][0] - t0 >= 0.35 * 0.95 + 0.2
    esperar(app, lambda: any(c.dato["nombre"].startswith("Karol") for c in d.tarjetas.values()), "resultados")
    _capturar(app, d, "03_busqueda.png")
    d.campo.setText("")
    d.campo.textEdited.emit("")
    esperar(app, lambda: len(d.tarjetas) >= 20, "vuelven los sugeridos")
    d.close()


def test_ajustes_abre_con_lo_elegido_marcado(app, pantalla_falsa):
    PG, _ = pantalla_falsa
    previos = [{"nombre": "Grupo 5", "id": "UC0", "portada": "http://img/0.jpg"},
               {"nombre": "Artista Propio", "id": "UCp", "portada": ""}]
    d = _abrir(app, PG, inicial=previos, ajustes=True)
    assert d.contador.text() == "2 elegidos"
    assert d.tarjetas["artista propio"].marcada and d.tarjetas["grupo 5"].marcada
    assert d.bt_seguir.text() == "Guardar" and d.bt_omitir.text() == "Cancelar"
    d.bt_omitir.click()
    assert d.accion is None
    d.close()
