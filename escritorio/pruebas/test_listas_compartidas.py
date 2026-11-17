# -*- coding: utf-8 -*-
"""Listas compartidas y colaborativas, rapidez de la sincronización y «Añadir a una lista».

Sin internet y con los datos de la app en una carpeta temporal: la nube es un doble que contesta lo
que contestaría la base (supabase/listas.sql) y cuenta las peticiones.
"""

import json
import os
import re
import sqlite3
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton  # noqa: E402

from descargador import chat as CH  # noqa: E402
from descargador import listas_compartidas as LC  # noqa: E402
from descargador import nube  # noqa: E402
from descargador.coleccion import Coleccion, para_nube  # noqa: E402
from descargador.sincronizacion import Sincronizador  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "docs", "capturas-escritorio")


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    # en modo offscreen no hay tipografías: se carga la de Windows para que las capturas se lean
    from PySide6.QtGui import QFont, QFontDatabase
    for f in ("segoeui.ttf", "segoeuib.ttf", "seguiemj.ttf"):
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/" + f)
    a.setFont(QFont("Segoe UI", 10))
    from descargador.ui import estilos, iconos
    a.setStyleSheet(estilos.hoja(iconos.flechas_qss()))
    return a


@pytest.fixture(autouse=True)
def sin_internet_para_imagenes(monkeypatch):
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "_leer", lambda url: b"")


@pytest.fixture(scope="module")
def base_vacia(tmp_path_factory):
    """Una biblioteca vacía ya creada (crear una desde cero tarda en discos lentos): cada prueba usa una copia."""
    ruta = tmp_path_factory.mktemp("base") / "historial.db"
    c = Coleccion(ruta)
    c.con.close()
    return ruta


@pytest.fixture
def col(tmp_path, base_vacia):
    import shutil
    destino = tmp_path / "historial.db"
    shutil.copy(base_vacia, destino)
    return Coleccion(destino)


def pista(i, **extra):
    p = {"tipo": "pista", "clave": f"yt:v{i:09d}", "video_id": f"v{i:09d}", "titulo": f"Canción {i}",
         "artista": f"Artista {i % 7}", "artistas": [{"nombre": f"Artista {i % 7}", "id": "a1"}],
         "album": {"nombre": "Álbum", "id": "b1"}, "duracion": 200,
         "miniatura": f"https://i.ytimg.com/vi/v{i:09d}/hq.jpg"}
    p.update(extra)
    return p


# ======================================================================= códigos y mensaje

def test_el_codigo_se_muestra_con_guion():
    assert LC.con_guion("K7M2 9qxp") == "K7M2-9QXP"
    assert LC.con_guion("k7m29qxp") == "K7M2-9QXP"


@pytest.mark.parametrize("texto", ["K7M2-9QXP", "k7m2-9qxp", "k7m29qxp", " K7M2 9QXP ", "k7m2 - 9qxp"])
def test_se_acepta_en_minusculas_con_o_sin_guion(texto):
    assert LC.normalizar_codigo(texto) == "K7M29QXP"
    assert LC.extraer_codigo(texto) == "K7M29QXP"


@pytest.mark.parametrize("malo", ["", "K7M2", "K7M2-9QX", "K7M2-9QXPA", "K7M2-9Q0P", "K7M2-9QIP", "K7M2-9QLP", "K7M2-9Q1P"])
def test_codigos_que_no_valen(malo):
    # el alfabeto no tiene I, L, O, 0 ni 1
    assert LC.normalizar_codigo(malo) == ""


def test_se_saca_el_codigo_de_un_enlace_o_de_un_mensaje_pegado():
    assert LC.extraer_codigo("https://caudal-musica.netlify.app/l/K7M2-9QXP") == "K7M29QXP"
    assert LC.extraer_codigo("caudal://lista?codigo=K7M2-9QXP") == "K7M29QXP"
    msg = LC.mensaje_compartir("Gym", "K7M29QXP")
    assert LC.extraer_codigo(msg) == "K7M29QXP"


def test_enlaces():
    assert LC.enlace("k7m29qxp") == "https://caudal-musica.netlify.app/l/K7M2-9QXP"
    assert LC.enlace_app("K7M29QXP") == "caudal://lista?codigo=K7M2-9QXP"


def test_mensaje_para_compartir_es_exacto():
    assert LC.mensaje_compartir("Mi playlist", "K7M29QXP") == (
        "Te paso mi lista «Mi playlist» en Caudal 🎧\n"
        "Ábrela aquí: https://caudal-musica.netlify.app/l/K7M2-9QXP\n"
        "O entra a Caudal › Biblioteca › «Tengo un código» y escribe: K7M2-9QXP")


def test_frases_de_permiso():
    assert "añadir canciones" in LC.frase_permiso("colaborador")
    assert "solo escuchar" in LC.frase_permiso("oyente")
    assert LC.etiqueta_rol("colaborador") == "Colaborativa" and LC.etiqueta_rol("oyente") == "Solo escuchar"
    assert LC.normalizar_rol("cualquiera") == "colaborador"


# ======================================================================= forma exacta de lo que devuelve la base

VISTA_PREVIA = {"nombre": "Gym", "descripcion": "Para entrenar", "total": 3, "rol": "oyente", "miembros": 2,
                "dueno": {"usuario": "ana", "nombre": "Ana", "foto_url": None},
                "canciones": [{"titulo": f"T{i}", "artista": "A", "miniatura": "http://x/y.jpg"} for i in range(6)]}


def test_vista_previa_de_ver_lista_codigo():
    v = LC.vista_previa(VISTA_PREVIA)
    assert v["nombre"] == "Gym" and v["total"] == 3 and v["rol"] == "oyente" and v["miembros"] == 2
    assert v["dueno"]["usuario"] == "ana" and v["dueno"]["foto_url"] == ""
    assert len(v["canciones"]) == 6 and v["canciones"][0]["titulo"] == "T0"


def test_codigo_que_no_existe_es_nulo():
    assert LC.vista_previa(None) is None


def test_resultado_de_unirse():
    r = LC.resultado_unirse({"lista_id": "u1", "nombre": "Gym", "rol": "colaborador", "es_dueno": False})
    assert r == {"lista_id": "u1", "nombre": "Gym", "rol": "colaborador", "es_dueno": False}


def test_lista_compartida_de_mis_listas_compartidas():
    x = LC.lista_compartida({"id": "u1", "nombre": "Gym", "descripcion": "", "rol": "colaborador", "total": 4,
                             "actualizada": "2026-11-16T10:00:00+00:00",
                             "dueno": {"id": "d1", "usuario": "ana", "nombre": "Ana", "foto_url": None}})
    assert x["dueno"]["id"] == "d1" and x["total"] == 4 and x["rol"] == "colaborador"
    assert LC.nombre_persona(x["dueno"]) == "Ana"


def test_miembros_de_miembros_lista():
    m = LC.miembro({"id": "d1", "usuario": "ana", "nombre": "Ana", "foto_url": None, "rol": "colaborador",
                    "desde": "2026-11-16T10:00:00+00:00", "es_dueno": True})
    assert m["es_dueno"] is True and m["usuario"] == "ana"


FILA_PISTA = {"clave": "yt:v000000001", "datos": {k: v for k, v in pista(1).items() if k != "clave"},
              "orden": 1.0, "agregada": "2026-11-16T10:00:00+00:00",
              "agregada_por": {"id": "d1", "usuario": "ana", "nombre": "Ana"}}


def test_pistas_de_lista_quedan_listas_para_sonar_y_dicen_quien_las_anadio():
    p = LC.pista_compartida(FILA_PISTA)
    assert p["clave"] == "yt:v000000001" and p["video_id"] == "v000000001" and p["tipo"] == "pista"
    assert LC.quien_agrego(p) == "Ana"


def test_quien_puede_quitar():
    p = LC.pista_compartida(FILA_PISTA)
    assert LC.puede_quitar("colaborador", True, p, "otro")          # el dueño, cualquiera
    assert LC.puede_quitar("colaborador", False, p, "d1")           # un colaborador, las suyas
    assert not LC.puede_quitar("colaborador", False, p, "otro")     # no las de otros
    assert not LC.puede_quitar("oyente", False, p, "d1")            # quien solo escucha, ninguna


def test_tarjeta_de_lista_para_el_chat():
    t = LC.tarjeta_para_chat("k7m2-9qxp", "Gym", 12, "colaborador", "https://x/y.jpg")
    assert t == {"codigo": "K7M29QXP", "nombre": "Gym", "canciones": 12, "rol": "colaborador",
                 "portada": "https://x/y.jpg"}
    assert "portada" not in LC.tarjeta_para_chat("K7M29QXP", "Gym", 0, "oyente", "")
    assert LC.tarjeta_limpia({"nombre": "sin código"}) is None
    assert LC.tarjeta_limpia({"codigo": "K7M2-9QXP", "nombre": "Gym", "canciones": "5", "rol": "oyente"})["canciones"] == 5


# ======================================================================= errores traducidos

class Respuesta:
    def __init__(self, estado, cuerpo):
        self.status_code = estado
        self._c = cuerpo
        self.text = json.dumps(cuerpo)

    def json(self):
        return self._c


@pytest.mark.parametrize("mensaje", [
    "Ese código no existe o la lista ya no se comparte. Revisa que esté bien escrito.",
    "Esta lista ya tiene 20 personas, que es el máximo. Pídele a su dueño que haga lugar.",
    "No te puedes unir a esta lista.",
    "En esta lista solo puedes escuchar: no puedes añadir canciones.",
    "Solo puedes quitar las canciones que añadiste tú.",
    "Una lista compartida admite hasta 2000 canciones y esta ya tiene 2000.",
])
def test_los_errores_de_listas_llegan_en_espanol(mensaje):
    e = nube._traducir(Respuesta(400, {"code": "P0001", "message": mensaje, "details": None, "hint": None}))
    assert str(e) == mensaje


def test_funcion_aun_no_aplicada_se_explica():
    e = nube._traducir(Respuesta(404, {"code": "PGRST202", "message": "Could not find the function public.unirse_a_lista"}))
    assert "todavía no está activa" in str(e)


# ======================================================================= la nube de mentira

class NubeListas:
    """Contesta las funciones de supabase/listas.sql y cuenta cada llamada."""
    user_id = "yo-id"
    access = "token"

    def __init__(self):
        self.llamadas = []
        self.codigos = {}            # uuid -> (codigo, rol)
        self.cuantos_compartir = 0
        self.fallo = None

    def rpc(self, nombre, **p):
        self.llamadas.append((nombre, p))
        if self.fallo:
            raise nube.ErrorNube(self.fallo)
        if nombre == "compartir_lista":
            self.cuantos_compartir += 1
            u = p["p_lista"]
            cod = self.codigos.get(u, ("ABCD2345", None))[0]
            self.codigos[u] = (cod, p["p_rol"])
            return cod
        if nombre == "ver_lista_codigo":
            for u, (c, r) in self.codigos.items():
                if c == p["p_codigo"]:
                    return dict(VISTA_PREVIA, rol=r)
            return None
        if nombre == "dejar_de_compartir_lista":
            self.codigos.pop(p["p_lista"], None)
            return None
        return None

    def pedir(self, metodo, ruta, **kw):
        if ruta.startswith("rpc/"):
            return self.rpc(ruta[4:], **(kw.get("json") or {}))
        return []


def listas_nube(sesion):
    return LC.ListasCompartidas(sesion)


def test_llamadas_a_la_base_con_los_nombres_y_parametros_del_plan():
    s = NubeListas()
    n = listas_nube(s)
    assert n.compartir("u1", "oyente") == "ABCD2345"
    n.ver_codigo("abcd-2345")
    n.unirse("abcd 2345")
    n.salir("u1")
    n.quitar_miembro("u1", "x")
    n.miembros("u1")
    n.mis_compartidas()
    n.pistas("u1")
    n.quitar("u1", "yt:v1")
    n.dejar_de_compartir("u1")
    assert s.llamadas[0] == ("compartir_lista", {"p_lista": "u1", "p_rol": "oyente"})
    assert s.llamadas[1] == ("ver_lista_codigo", {"p_codigo": "ABCD2345"})
    assert s.llamadas[2] == ("unirse_a_lista", {"p_codigo": "ABCD2345"})
    nombres = [x[0] for x in s.llamadas]
    assert nombres[3:] == ["salir_de_lista", "quitar_miembro", "miembros_lista", "mis_listas_compartidas",
                           "pistas_de_lista", "quitar_de_lista_compartida", "dejar_de_compartir_lista"]


def test_agregar_manda_solo_canciones_de_internet_sin_rutas_de_la_pc():
    s = NubeListas()
    n = listas_nube(s)
    local = {"tipo": "pista", "clave": "local:5", "titulo": "Mi archivo", "archivo": "C:/musica/a.mp3"}
    n.agregar("u1", [pista(1, archivo="C:/x.mp3"), local])
    nombre, p = s.llamadas[-1]
    assert nombre == "agregar_a_lista_compartida" and p["p_lista"] == "u1"
    assert [i["clave"] for i in p["p_items"]] == ["yt:v000000001"]
    assert "archivo" not in p["p_items"][0]["datos"]
    n.agregar("u1", [local])                      # nada que mandar: ni siquiera se llama
    assert s.llamadas[-1][1]["p_items"][0]["clave"] == "yt:v000000001"


# ======================================================================= compartir una lista mía

def lista_con_canciones(col, nombre="Gym", n=3):
    lid = col.crear_lista(nombre)
    col.agregar_a_lista(lid, [pista(i) for i in range(n)])
    col.agregar_a_lista(lid, [{"tipo": "pista", "clave": "local:9", "titulo": "Archivo"}])
    return lid


def test_comparte_una_lista_nueva_con_el_permiso_por_defecto(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    subidas = []
    r = LC.compartir_mi_lista(col, listas_nube(s), lid, antes=lambda: subidas.append(1))
    assert subidas == [1]                          # lo pendiente se sube antes: la lista debe existir en la nube
    assert r["codigo"] == "ABCD2345" and r["rol"] == "colaborador" and r["canciones"] == 3   # el archivo local no cuenta
    u = col.lista(lid)["uuid"]
    assert s.codigos[u] == ("ABCD2345", "colaborador")
    assert LC.codigos_guardados(col)[u] == {"codigo": "ABCD2345", "rol": "colaborador"}


def test_si_ya_esta_compartida_se_reutiliza_el_codigo(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    n = listas_nube(s)
    LC.compartir_mi_lista(col, n, lid)
    r = LC.compartir_mi_lista(col, n, lid)
    assert s.cuantos_compartir == 1 and r["ya"] is True and r["codigo"] == "ABCD2345"


def test_cambiar_el_permiso_llama_a_la_base(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    n = listas_nube(s)
    LC.compartir_mi_lista(col, n, lid, "colaborador")
    r = LC.compartir_mi_lista(col, n, lid, "oyente")
    assert s.cuantos_compartir == 2 and r["rol"] == "oyente" and r["codigo"] == "ABCD2345"


def test_si_dejaron_de_compartir_desde_el_telefono_se_vuelve_a_compartir(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    n = listas_nube(s)
    LC.compartir_mi_lista(col, n, lid)
    s.codigos.clear()                                # desde otro aparato
    assert LC.estado_de_mi_lista(col, n, col.lista(lid)["uuid"]) is None
    assert LC.codigos_guardados(col) == {}


def test_dejar_de_compartir_olvida_el_codigo(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    n = listas_nube(s)
    LC.compartir_mi_lista(col, n, lid)
    LC.dejar_de_compartir_mi_lista(col, n, lid)
    assert LC.codigos_guardados(col) == {} and s.codigos == {}


# ---- «Enviar una lista» desde dentro del chat: elegir lista → compartir si hace falta → armar el mensaje

def test_enviar_lista_no_compartida_la_comparte_sola_como_colaborativa(col):
    s = NubeListas()
    lid = lista_con_canciones(col, "Mi playlist", 5)
    r = LC.preparar_lista_para_chat(col, listas_nube(s), lid)
    assert s.cuantos_compartir == 1
    assert s.llamadas[0][1]["p_rol"] == "colaborador"        # permiso por defecto: pueden añadir canciones
    t = r["tarjeta"]
    assert t["codigo"] == "ABCD2345" and t["nombre"] == "Mi playlist" and t["canciones"] == 5
    assert t["rol"] == "colaborador"
    assert "añadir canciones" in r["frase"] and r["ya_compartida"] is False


def test_enviar_lista_solo_escuchar_comparte_con_ese_permiso(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    r = LC.preparar_lista_para_chat(col, listas_nube(s), lid, "oyente")
    assert s.llamadas[0][1]["p_rol"] == "oyente" and r["tarjeta"]["rol"] == "oyente"
    assert "solo escuchar" in r["frase"]


def test_enviar_lista_ya_compartida_reutiliza_su_codigo_y_permiso(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    n = listas_nube(s)
    LC.compartir_mi_lista(col, n, lid, "oyente")
    r = LC.preparar_lista_para_chat(col, n, lid)             # sin pedir otro permiso
    assert s.cuantos_compartir == 1 and r["ya_compartida"] is True
    assert r["tarjeta"]["codigo"] == "ABCD2345" and r["tarjeta"]["rol"] == "oyente"


def test_enviar_lista_con_la_nube_caida_dice_que_paso(col):
    s = NubeListas()
    s.fallo = "Esa lista no existe o no es tuya."
    lid = lista_con_canciones(col)
    with pytest.raises(nube.ErrorNube) as e:
        LC.preparar_lista_para_chat(col, listas_nube(s), lid)
    assert "no es tuya" in str(e.value)


class SesionChat:
    user_id = "yo-id"
    access = "t"

    def __init__(self, sin_lista=False):
        self.llamadas = []
        self.sin_lista = sin_lista

    def pedir(self, metodo, ruta, **kw):
        self.llamadas.append((metodo, ruta, kw))
        if metodo == "GET" and "lista" in ruta.split("select=")[1].split("&")[0].split(",") and self.sin_lista:
            raise nube.ErrorNube("Esta función todavía no está activa en el servidor de Caudal.")
        if metodo == "POST" and ruta == "mensajes":
            return [{"id": 1, "autor": "yo-id", "texto": "", "pista": None,
                     "lista": kw["json"].get("lista"), "creado": "2026-11-16T10:00:00+00:00"}]
        if metodo == "GET":
            return [{"id": 2, "autor": "otro", "texto": "", "pista": None,
                     "lista": {"codigo": "ABCD2345", "nombre": "Gym", "canciones": 4, "rol": "colaborador"},
                     "creado": "2026-11-16T10:00:00+00:00"}]
        return []


def test_el_mensaje_de_chat_lleva_la_tarjeta_de_lista():
    s = SesionChat()
    t = LC.tarjeta_para_chat("ABCD2345", "Gym", 4, "colaborador")
    m = CH.Chat(s).enviar("chat1", "", None, t)
    cuerpo = s.llamadas[-1][2]["json"]
    assert cuerpo == {"chat": "chat1", "texto": "", "lista": t}
    assert m["lista"]["codigo"] == "ABCD2345"


def test_al_leer_el_chat_se_piden_las_listas():
    s = SesionChat()
    ms = CH.Chat(s).mensajes("chat1")
    assert "lista" in s.llamadas[0][1] and ms[0]["lista"]["nombre"] == "Gym"


def test_si_la_base_aun_no_tiene_listas_en_mensajes_el_chat_sigue_igual():
    CH.Chat._con_lista = True
    try:
        s = SesionChat(sin_lista=True)
        ms = CH.Chat(s).mensajes("chat1")
        assert len(ms) == 1 and CH.Chat._con_lista is False
    finally:
        CH.Chat._con_lista = True


def test_vista_previa_de_la_conversacion_con_lista():
    c = {"ultimo_lista": {"nombre": "Gym"}, "ultimo_autor": "yo", "ultimo_texto": ""}
    assert CH.vista_previa(c, "yo") == "Tú: 📋 Lista «Gym»"


def test_tarjeta_conocida_dice_abrir(col):
    s = NubeListas()
    lid = lista_con_canciones(col)
    LC.compartir_mi_lista(col, listas_nube(s), lid)
    assert LC.lista_de_codigo(col, "abcd-2345") == {"tipo": "mia", "id": lid}
    assert LC.lista_de_codigo(col, "ZZZZ2345") is None
    LC.recordar_union(col, "ZZZZ-2345", "u9")
    assert LC.lista_de_codigo(col, "zzzz2345") == {"tipo": "unida", "id": "u9"}


# ======================================================================= sincronización: rapidez

class NubeSinc:
    """PostgREST de mentira: cuenta peticiones y entrega como mucho 1000 filas por consulta."""
    user_id = "u1"

    def __init__(self, listas=3, canciones=40):
        self.listas = [{"id": f"00000000-0000-0000-0000-{k:012d}", "nombre": f"Lista {k}", "descripcion": "",
                        "fijada": False, "creada": "2026-01-01T00:00:00+00:00", "publica": False,
                        "en_perfil": False} for k in range(listas)]
        self.items = [{"lista_id": l["id"], "clave": f"yt:v{k:03d}{j:05d}", "orden": j + 1,
                       "datos": {k2: v for k2, v in pista(k * 100000 + j).items() if k2 != "clave"}}
                      for k, l in enumerate(self.listas) for j in range(canciones)]
        self.peticiones = []
        self.fila_ajustes = None

    def pedir(self, metodo, ruta, **kw):
        base = ruta.split("?")[0]
        self.peticiones.append((metodo, base, ruta))
        q = ruta.split("?", 1)[1] if "?" in ruta else ""
        if metodo == "POST" and base == "ajustes":
            self.fila_ajustes = {"datos": kw["json"][0]["datos"], "actualizado": "2026-11-16T10:00:00+00:00"}
        if metodo != "GET":
            return None
        if base == "listas":
            return [dict(l) for l in self.listas]
        if base == "lista_items":
            filas = self.items
            m = re.search(r"lista_id=eq\.([^&]+)", q)
            if m:
                filas = [f for f in filas if f["lista_id"] == m.group(1)]
            lim = min(int(re.search(r"limit=(\d+)", q).group(1)) if "limit=" in q else 1000, 1000)
            off = int(re.search(r"offset=(\d+)", q).group(1)) if "offset=" in q else 0
            return [dict(f) for f in filas[off:off + lim]]
        if base == "ajustes":
            return [self.fila_ajustes] if self.fila_ajustes else []
        return []

    def de(self, base):
        return [p for p in self.peticiones if p[1] == base]


def con_cambios(s, **kw):
    """Corre un ciclo y devuelve cuántas filas escribió en la base."""
    total = []

    class Con(sqlite3.Connection):
        def close(self):
            total.append(self.total_changes)
            super().close()
    original = sqlite3.connect
    import descargador.sincronizacion as m
    m.sqlite3.connect = lambda *a, **k: original(*a, factory=Con, **k)
    try:
        r = s._ciclo(**kw)
    finally:
        m.sqlite3.connect = original
    return sum(total), r


def sincronizador(col, nube_):
    return Sincronizador(col, {"sesion": nube_}, ajustes={"region": "PE"})


def test_la_descarga_pide_las_canciones_de_todas_las_listas_en_UNA_peticion(app, col):
    n = NubeSinc(listas=5, canciones=40)            # 200 canciones: caben en una página
    sincronizador(col, n)._ciclo()
    assert len(n.de("lista_items")) == 1            # antes: una petición por lista
    assert "lista_id=eq" not in n.de("lista_items")[0][2]
    assert len(col.listas()) == 5 and all(l["n"] == 40 for l in col.listas())


def test_mas_de_mil_canciones_se_piden_por_paginas(app, col):
    n = NubeSinc(listas=3, canciones=450)           # 1350 canciones
    sincronizador(col, n)._ciclo()
    pedidas = n.de("lista_items")
    assert len(pedidas) == 2 and "offset=0" in pedidas[0][2] and "offset=1000" in pedidas[1][2]
    assert sum(l["n"] for l in col.listas()) == 1350


def test_una_descarga_sin_novedades_no_reescribe_nada(app, col):
    n = NubeSinc()
    s = sincronizador(col, n)
    s._ciclo()
    s._ciclo()                                      # la nube ya tiene los ajustes de esta cuenta
    escrituras, (cambio, _aj) = con_cambios(s)
    assert escrituras == 0 and cambio is False       # antes: tocaba cada canción de cada lista


def test_solo_se_escribe_lo_que_cambio_en_la_nube(app, col):
    n = NubeSinc(listas=2, canciones=10)
    s = sincronizador(col, n)
    s._ciclo()
    s._ciclo()
    n.items.append({"lista_id": n.listas[1]["id"], "clave": "yt:vNUEVA0001", "orden": 11,
                    "datos": {"titulo": "Nueva", "video_id": "vNUEVA0001"}})
    escrituras, (cambio, _aj) = con_cambios(s)
    assert cambio is True and 1 <= escrituras <= 3
    assert "yt:vNUEVA0001" in col.claves_de_lista(col.lista_por_uuid(n.listas[1]["id"])["id"])


def test_lo_que_se_borra_en_la_nube_se_borra_aqui(app, col):
    n = NubeSinc(listas=1, canciones=5)
    s = sincronizador(col, n)
    s._ciclo()
    quitada = n.items.pop(0)["clave"]
    _e, (cambio, _aj) = con_cambios(s)
    lid = col.lista_por_uuid(n.listas[0]["id"])["id"]
    assert cambio and quitada not in col.claves_de_lista(lid) and len(col.claves_de_lista(lid)) == 4


def test_tras_un_cambio_local_solo_se_envia_no_se_vuelve_a_bajar_todo(app, col):
    n = NubeSinc(listas=4, canciones=30)
    s = sincronizador(col, n)
    s._ciclo()
    col.sincronizador = type("X", (), {"pronto": lambda self: None})()
    lid = col.listas()[0]["id"]
    col.agregar_a_lista(lid, [pista(999999)])
    n.peticiones.clear()
    _e, (cambio, _aj) = con_cambios(s, completo=False)        # lo que dispara pronto()
    assert [p[0] for p in n.peticiones] == ["POST"] and n.peticiones[0][1] == "lista_items"
    assert cambio is False and not [p for p in n.peticiones if p[0] == "GET"]


def test_el_ciclo_completo_sigue_trayendo_lo_de_otros_dispositivos(app, col):
    n = NubeSinc(listas=2, canciones=5)
    s = sincronizador(col, n)
    s._ciclo()
    n.peticiones.clear()
    s._ciclo(completo=True)
    assert len(n.de("lista_items")) == 1 and len(n.de("listas")) == 1


def test_refrescar_una_lista_pide_solo_esa_lista(app, col):
    n = NubeSinc(listas=3, canciones=5)
    s = sincronizador(col, n)
    s._ciclo()
    n.items.append({"lista_id": n.listas[2]["id"], "clave": "yt:vOTRA000001", "orden": 6,
                    "datos": {"titulo": "De un colaborador", "video_id": "vOTRA000001"}})
    n.peticiones.clear()
    assert s._traer_una(n.listas[2]["id"]) is True
    assert len(n.peticiones) == 1 and n.listas[2]["id"] in n.peticiones[0][2]
    assert s._traer_una(n.listas[2]["id"]) is False         # ya está al día


def test_enviar_ahora_sube_lo_pendiente(app, col):
    n = NubeSinc(listas=0)
    s = sincronizador(col, n)
    col.sincronizador = type("X", (), {"pronto": lambda self: None})()
    lid = col.crear_lista("Nueva")
    col.agregar_a_lista(lid, [pista(1)])
    s.enviar_ahora()
    assert [p[1] for p in n.peticiones] == ["listas", "lista_items"]
    assert col.con.execute("SELECT COUNT(*) n FROM pendientes").fetchone()["n"] == 0


def test_ciclo_ligero_no_pregunta_por_los_ajustes_si_no_cambiaron(app, col):
    n = NubeSinc(listas=1, canciones=2)
    s = sincronizador(col, n)
    s._ciclo()
    n.peticiones.clear()
    s._ciclo(completo=False)
    assert n.peticiones == []


# ======================================================================= guardar en listas (rapidez y deshacer)

def test_agregar_300_canciones_confirma_una_sola_vez(col):
    lid = col.crear_lista("Grande")
    confirmaciones = []
    real = col.con
    col.con = type("C", (), {"execute": lambda self, *a, **k: real.execute(*a, **k),
                             "commit": lambda self: (confirmaciones.append(1), real.commit()),
                             "__getattr__": lambda self, k: getattr(real, k)})()
    nuevas = col.agregar_a_lista(lid, [pista(i) for i in range(300)])
    assert nuevas == 300 and len(confirmaciones) == 1       # antes: 301 confirmaciones al disco


def test_pistas_se_leen_por_tandas_y_en_orden(col):
    lid = col.crear_lista("L")
    col.agregar_a_lista(lid, [pista(i) for i in range(30)])
    col.recordar({"tipo": "pista", "clave": "yt:v000000100", "titulo": "Suelta"})
    got = col.pistas(["yt:v000000007", "yt:noexiste", "yt:v000000100", "yt:v000000003"])
    assert [p["clave"] for p in got] == ["yt:v000000007", "yt:v000000100", "yt:v000000003"]
    assert len(col.portadas_de_lista(lid, 4)) == 4


class Reproductor(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    modo_cambio = Signal(str)
    actual = None
    contexto = None
    estado = "parado"
    aleatorio = False

    def agregar_a_cola(self, *_a):
        pass


def contexto(col, sesion=None):
    from descargador.ui.contexto import Contexto
    c = Contexto({}, None, col, None, Reproductor())
    c.cuenta = {"usuario": "ana", "nombre": "Ana", "sesion": sesion}
    c.navegaciones = []
    c.navegar = c.navegaciones.append
    c.avisos = []
    c.aviso.connect(c.avisos.append)
    c.deshacer = []
    c.avisar = lambda texto, deshacer=None: (c.avisos.append(texto), c.deshacer.append(deshacer))
    return c


def test_anadir_a_varias_listas_y_deshacer_quita_solo_lo_nuevo(app, col):
    a, b = col.crear_lista("A"), col.crear_lista("B")
    col.agregar_a_lista(b, [pista(1)])                      # ya estaba en B
    c = contexto(col)
    c.anadir_a_listas([pista(1), pista(2)], [a, b])
    assert col.claves_de_lista(a) == {"yt:v000000001", "yt:v000000002"}
    assert col.claves_de_lista(b) == {"yt:v000000001", "yt:v000000002"}
    assert c.avisos[-1] == "Añadido a 2 listas" and c.deshacer[-1] is not None
    assert col.estado("ultima_lista") == a
    c.deshacer[-1]()
    assert col.claves_de_lista(a) == set()
    assert col.claves_de_lista(b) == {"yt:v000000001"}      # lo que ya había se respeta


def test_anadir_algo_que_ya_estaba_avisa_sin_deshacer(app, col):
    a = col.crear_lista("A")
    col.agregar_a_lista(a, [pista(1)])
    c = contexto(col)
    c.anadir_a_listas([pista(1)], [a])
    assert c.avisos[-1] == "Ya estaba en «A»"


def test_anadir_a_una_lista_compartida_va_a_la_nube_y_se_puede_deshacer(app, col):
    s = NubeListas()
    c = contexto(col, s)
    from descargador.hilos import esperar_todo
    c.anadir_a_listas([pista(1)], [], [{"id": "uc1", "nombre": "De Ana"}])
    esperar_todo(3000)
    for _ in range(30):
        app.processEvents()
        time.sleep(0.01)
    assert ("agregar_a_lista_compartida", {"p_lista": "uc1", "p_items": [
        {"clave": "yt:v000000001", "datos": para_nube(pista(1))}]}) in s.llamadas
    assert c.avisos[-1] == "Añadido a «De Ana»"
    c.deshacer[-1]()
    esperar_todo(3000)
    assert any(x[0] == "quitar_de_lista_compartida" for x in s.llamadas)


def esperar(app, cond, que, maximo=25):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.01)


# ======================================================================= pantallas (offscreen) y capturas

def soltar(app):
    """Deja que Qt borre de verdad los widgets que se mandaron borrar (deleteLater)."""
    from PySide6.QtCore import QEvent
    app.processEvents()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def guardar(widget, nombre):
    os.makedirs(CAPTURAS, exist_ok=True)
    widget.grab().save(os.path.join(CAPTURAS, nombre))


def textos(w):
    return " | ".join(x.text() for x in w.findChildren(QLabel))


def botones(w):
    return {b.text().strip(): b for b in w.findChildren(QPushButton)}


def test_dialogo_anadir_a_lista_ultima_arriba_busqueda_y_crear(app, col):
    from descargador.ui.dialogos_listas import DialogoAnadirALista
    for i in range(12):
        col.crear_lista(f"Lista {i:02d}")
    col.agregar_a_lista(col.listas()[0]["id"], [pista(1), pista(2)])
    ultima = col.lista_por_uuid(col.lista(7)["uuid"])["id"]
    col.guardar_estado("ultima_lista", ultima)
    c = contexto(col)
    d = DialogoAnadirALista(c, [pista(50, titulo="Una canción larga")])
    d.resize(460, 620)
    d.show()
    app.processEvents()
    assert d.buscador.isVisible()                            # hay más de 8: aparece la búsqueda
    assert d.listas[0]["id"] == ultima                       # la última usada, arriba
    assert "la última que usaste" in textos(d)
    assert not d.bt_listo.isEnabled()
    guardar(d, "dialogo_anadir_a_lista.png")
    d._alternar(("l", d.listas[0]["id"]))
    d._alternar(("l", d.listas[1]["id"]))
    assert d.bt_listo.isEnabled() and d.bt_listo.text() == "Listo (2)"
    d.buscador.setText("Lista 03")
    soltar(app)
    assert sum(1 for b in d.area.findChildren(QPushButton) if b.isCheckable()) == 1
    d.buscador.setText("")
    d.nombre_nuevo.setText("Gimnasio")
    d._crear()
    assert any(l["nombre"] == "Gimnasio" for l in col.listas()) and len(d._marcadas) == 3
    d._listo()
    assert d.result() == QDialog.Accepted and len(d.ids) == 3


def test_dialogo_anadir_sin_listas_invita_a_crear_la_primera(app, col):
    from descargador.ui.dialogos_listas import DialogoAnadirALista
    d = DialogoAnadirALista(contexto(col), [pista(1)])
    d.show()
    app.processEvents()
    assert not d.buscador.isVisible() and "Todavía no tienes listas" in textos(d)
    d.nombre_nuevo.setText("Primera")
    d._crear()
    assert d.bt_listo.isEnabled()


def test_dialogo_compartir_lista_nueva_y_ya_compartida(app, col):
    from descargador.ui.dialogos_listas import DialogoCompartir
    s = NubeListas()
    lid = lista_con_canciones(col, "Gym", 4)
    c = contexto(col, s)
    d = DialogoCompartir(c, lid)
    d.show()
    esperar(app, lambda: d.bt_empezar.isVisibleTo(d), "aparece «Compartir con un código»")
    assert "privada" in textos(d) and not d.caja_codigo.isVisibleTo(d)
    guardar(d, "dialogo_compartir_privada.png")
    d.bt_empezar.click()
    esperar(app, lambda: d.caja_codigo.isVisibleTo(d), "aparece el código")
    assert d.et_codigo.text() == "ABCD-2345"
    assert d.et_enlace.text() == "https://caudal-musica.netlify.app/l/ABCD-2345"
    assert "podrá escuchar y añadir canciones" in d.et_permiso.text()
    d.bt_copiar_codigo.click()
    assert QApplication.clipboard().text() == "ABCD-2345"
    d.bt_copiar_mensaje.click()
    assert QApplication.clipboard().text() == LC.mensaje_compartir("Gym", "ABCD2345")
    d.bt_oyente.click()
    esperar(app, lambda: s.codigos[col.lista(lid)["uuid"]][1] == "oyente", "cambia el permiso: " + d.estado.text())
    assert "solo escuchar" in d.et_permiso.text()
    guardar(d, "dialogo_compartir_codigo.png")
    d.close()
    # otra vez: ya está compartida, se muestra al instante y no se vuelve a compartir
    veces = s.cuantos_compartir
    d2 = DialogoCompartir(c, lid)
    d2.show()
    assert d2.caja_codigo.isVisibleTo(d2) and d2.et_codigo.text() == "ABCD-2345"
    esperar(app, lambda: any(x[0] == "ver_lista_codigo" for x in s.llamadas[-4:]), "se comprueba con la base")
    assert s.cuantos_compartir == veces
    d2.close()


def test_dialogo_compartir_sin_cuenta_lo_explica(app, col):
    from descargador.ui.dialogos_listas import DialogoCompartir
    lid = lista_con_canciones(col)
    d = DialogoCompartir(contexto(col, None), lid)
    d.show()
    assert "necesita una cuenta" in d.estado.text() and not d.bt_empezar.isVisibleTo(d)


def test_tengo_un_codigo_vista_previa_y_unirme(app, col):
    from descargador.ui.dialogos_listas import DialogoTengoCodigo
    s = NubeListas()
    s.codigos["x"] = ("K7M29QXP", "colaborador")

    def rpc(nombre, **p):
        s.llamadas.append((nombre, p))
        if nombre == "ver_lista_codigo":
            return dict(VISTA_PREVIA, rol="colaborador") if p["p_codigo"] == "K7M29QXP" else None
        if nombre == "unirse_a_lista":
            return {"lista_id": "uu1", "nombre": "Gym", "rol": "colaborador", "es_dueno": False}
    s.rpc = rpc
    c = contexto(col, s)
    d = DialogoTengoCodigo(c)
    d.show()
    d.campo.setText("k7m2-9qxp")
    esperar(app, lambda: d.tarjeta.isVisibleTo(d), "vista previa")
    assert "Gym" in d.t_nombre.text() and "De Ana" in d.t_sub.text()
    assert "podrás añadir canciones" in d.t_permiso.text() and d.bt_unirme.isEnabled()
    guardar(d, "dialogo_tengo_un_codigo.png")
    d.bt_unirme.click()
    esperar(app, lambda: d.resultado is not None, "se une")
    assert d.resultado["lista_id"] == "uu1"
    assert LC.lista_de_codigo(col, "K7M2-9QXP") == {"tipo": "unida", "id": "uu1"}
    assert ("unirse_a_lista", {"p_codigo": "K7M29QXP"}) in s.llamadas


def test_tengo_un_codigo_que_no_existe_y_codigo_mal_escrito(app, col):
    from descargador.ui.dialogos_listas import DialogoTengoCodigo
    s = NubeListas()
    c = contexto(col, s)
    d = DialogoTengoCodigo(c)
    d.show()
    d.campo.setText("ABC")
    assert "8 letras y números" in d.estado.text() and not d.bt_unirme.isEnabled()
    d.campo.setText("ZZZZ-2345")
    esperar(app, lambda: "no existe" in d.estado.text(), "dice que no existe")
    assert not d.bt_unirme.isEnabled()
    guardar(d, "dialogo_tengo_un_codigo_error.png")


def test_dialogo_enviar_lista_desde_el_chat(app, col):
    from descargador.ui.dialogos_listas import DialogoEnviarLista
    s = NubeListas()
    a = lista_con_canciones(col, "Gym", 4)
    b = lista_con_canciones(col, "Viaje", 6)
    LC.compartir_mi_lista(col, listas_nube(s), b, "oyente")
    c = contexto(col, s)
    d = DialogoEnviarLista(c, "Bea")
    d.show()
    app.processEvents()
    assert not d.bt_enviar.isEnabled() and "Compartida · Solo escuchar" in textos(d)
    guardar(d, "dialogo_enviar_lista_chat.png")
    d._elegir(a)                                             # sin compartir: se puede elegir el permiso
    assert d.fila_rol.isEnabled() and "Colaborativa" in d.et_permiso.text()
    d._poner_rol("oyente")
    assert "Solo escuchar" in d.et_permiso.text()
    d._poner_rol("colaborador")
    d.bt_enviar.click()
    esperar(app, lambda: d.tarjeta is not None, "arma la tarjeta")
    assert d.tarjeta["nombre"] == "Gym" and d.tarjeta["rol"] == "colaborador" and d.tarjeta["canciones"] == 4
    assert "añadir canciones" in d.frase
    d2 = DialogoEnviarLista(c, "Bea")
    d2._elegir(b)                                            # ya compartida: se reutiliza
    assert not d2.fila_rol.isEnabled() and "mismo código" in d2.et_permiso.text()


def test_chat_tarjeta_de_lista_y_enviar_una_lista(app, col, monkeypatch):
    from descargador.ui.paginas import mensajes as M
    s = SesionChat()
    c = contexto(col, s)
    s2 = NubeListas()
    pag = M.PaginaMensajes(c)
    pag.resize(900, 600)
    pag.actual = {"id": "chat1", "visible": "Bea", "usuario": "bea", "es_amigo": True}
    pag._activar(True)
    caja, hora = pag._burbuja({"autor": "otro", "texto": "", "pista": None,
                               "lista": {"codigo": "ABCD2345", "nombre": "Gym", "canciones": 4, "rol": "colaborador"},
                               "fecha": CH._fecha("2026-11-16T10:00:00+00:00")})
    assert "Gym" in textos(caja) and "Colaborativa" in textos(caja)
    assert "Unirme" in botones(caja)
    pag.show()
    app.processEvents()
    guardar(pag, "chat_tarjeta_de_lista.png")
    assert pag.bt_lista.isEnabled()
    # «Enviar una lista» desde el chat: sin abrir el diálogo, se envía la tarjeta
    pag._enviar(lista=LC.tarjeta_para_chat("ABCD2345", "Gym", 4, "colaborador"))
    esperar(app, lambda: any(x[0] == "POST" and x[1] == "mensajes" for x in s.llamadas), "se envía el mensaje")
    cuerpo = [x for x in s.llamadas if x[0] == "POST"][-1][2]["json"]
    assert cuerpo["lista"]["codigo"] == "ABCD2345" and cuerpo["texto"] == ""
    _ = s2


def test_pagina_de_lista_compartida_muestra_quien_anadio_y_permisos(app, col):
    from descargador.ui.paginas.lista_compartida import PaginaListaCompartida
    s = NubeListas()
    filas = [dict(FILA_PISTA, clave=f"yt:v{i:09d}", agregada_por={"id": "yo-id" if i % 2 else "d1",
                                                                  "usuario": "yo" if i % 2 else "ana",
                                                                  "nombre": "Yo" if i % 2 else "Ana"},
                  datos={k: v for k, v in pista(i).items() if k != "clave"}, orden=float(i)) for i in range(1, 7)]
    s.rpc = lambda nombre, **p: (s.llamadas.append((nombre, p)) or
                                 (filas if nombre == "pistas_de_lista" else
                                  [{"id": "d1", "usuario": "ana", "nombre": "Ana", "foto_url": None, "rol": "colaborador",
                                    "desde": "", "es_dueno": True}] if nombre == "miembros_lista" else None))
    c = contexto(col, s)
    dest = {"pagina": "lista_compartida", "id": "uu1",
            "el": {"tipo": "lista_compartida", "id": "uu1", "titulo": "Gym", "rol": "colaborador",
                   "dueno": {"id": "d1", "usuario": "ana", "nombre": "Ana"}}}
    p = PaginaListaCompartida(c, dest)
    p.resize(1000, 800)
    p.show()
    esperar(app, lambda: p.cargado, "llegan las canciones")
    app.processEvents()
    assert p.lista is not None and len(p.lista.filas) == 6
    assert "Compartida · Ana" in textos(p) and "Colaborativa" in textos(p)
    vistas = p._a_mostrar()
    assert vistas[0]["album"]["nombre"] == "Añadida por ti" and vistas[1]["album"]["nombre"] == "Añadida por Ana"
    # puede quitar las suyas (i = 1, 3, 5), no las de Ana
    from PySide6.QtWidgets import QMenu
    m1, m2 = QMenu(), QMenu()
    p._menu_extra(m1, 0)
    p._menu_extra(m2, 1)
    assert len(m1.actions()) == 1 and len(m2.actions()) == 0
    assert p._buscador is not None and hasattr(p, "e_buscar")        # colaborador: puede añadir
    guardar(p, "pagina_lista_compartida.png")
    # sin cambios, el refresco no repinta
    firma = p._firma
    p._llegan(list(p.pistas))
    assert p._firma is firma
    p.reloj.stop()


def test_pagina_de_lista_solo_escuchar_no_deja_anadir(app, col):
    from descargador.ui.paginas.lista_compartida import PaginaListaCompartida
    s = NubeListas()
    s.rpc = lambda nombre, **p: [FILA_PISTA] if nombre == "pistas_de_lista" else None
    c = contexto(col, s)
    p = PaginaListaCompartida(c, {"pagina": "lista_compartida", "id": "uu2",
                                  "el": {"titulo": "Solo mirar", "rol": "oyente", "dueno": {"nombre": "Ana"}}})
    p.resize(900, 700)
    p.show()
    esperar(app, lambda: p.cargado, "llegan las canciones")
    assert not hasattr(p, "e_buscar") and "solo escuchar" in textos(p).lower()
    from PySide6.QtWidgets import QMenu
    m = QMenu()
    p._menu_extra(m, 0)
    assert len(m.actions()) == 0
    p.reloj.stop()


def compartidas_en(pagina):
    from descargador.ui.paginas.comun import Rejilla
    return [e for r in pagina.findChildren(Rejilla) for e in r.elementos if e.get("tipo") == "lista_compartida"]


def test_biblioteca_muestra_listas_compartidas_y_el_boton_tengo_un_codigo(app, col):
    from descargador.ui.paginas.biblioteca import PaginaBiblioteca
    s = NubeListas()
    comp = [{"id": "uu1", "nombre": "Fiesta de Ana", "descripcion": "", "rol": "colaborador", "total": 8,
             "actualizada": "", "dueno": {"id": "d1", "usuario": "ana", "nombre": "Ana", "foto_url": ""}}]
    s.rpc = lambda nombre, **p: comp if nombre == "mis_listas_compartidas" else None
    lista_con_canciones(col, "Mi lista", 3)
    c = contexto(col, s)
    LC._CACHE.clear()
    p = PaginaBiblioteca(c)
    p.resize(1100, 700)
    p.show()
    esperar(app, lambda: compartidas_en(p), "aparece la lista compartida")
    el = compartidas_en(p)[0]
    assert el["titulo"] == "Fiesta de Ana" and el["subtitulo"] == "Compartida · Ana" and el["tipo"] == "lista_compartida"
    assert "Listas compartidas" in textos(p)
    assert "Tengo un código" in botones(p)
    guardar(p, "biblioteca_listas_compartidas.png")
    # lo último que se supo queda guardado: la próxima vez sale al instante
    assert LC.compartidas_guardadas(col)[0]["nombre"] == "Fiesta de Ana"
    LC._CACHE.clear()
    s.llamadas.clear()
    s.rpc = lambda nombre, **p: (_ for _ in ()).throw(nube.SinConexion("sin internet"))
    p2 = PaginaBiblioteca(c)
    assert compartidas_en(p2)[0]["titulo"] == "Fiesta de Ana"      # sin conexión también se ve
