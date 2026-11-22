# -*- coding: utf-8 -*-
"""Grupos para hablar en Windows (descargador/grupos.py, notas_voz.py y ui/paginas/grupos.py).

Sin internet ni ventanas (Qt offscreen): la sesión de la nube es un doble que contesta como
supabase/grupos.sql y apunta lo que se le pide."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QToolButton  # noqa: E402

from descargador import grupos as G  # noqa: E402
from descargador import nube  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet_para_imagenes(monkeypatch):
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "_leer", lambda url: b"")


def _grupo(gid="g1", nombre="Reggaetón Lima", tipo="abierto", rol="miembro", codigo=None, sin_leer=0, ultimo=None):
    return {"id": gid, "nombre": nombre, "descripcion": "Para hablar", "tipo": tipo, "miembros": 3, "rol": rol,
            "codigo": codigo, "cerrado": False, "ultimo": "2026-11-21T15:00:00Z", "sin_leer": sin_leer,
            "ultimo_mensaje": ultimo}


def _mensaje(mid, autor="ana", mio=False, texto="hola", pista=None, audio=None, seg=None, rol="miembro"):
    return {"id": mid, "texto": texto, "pista": pista, "audio": audio, "audio_seg": seg, "fijado": False,
            "oculto": False, "creado": f"2026-11-21T15:0{mid % 10}:00Z", "mio": mio,
            "autor": {"id": f"id-{autor}", "usuario": autor, "nombre": autor.upper(), "foto_url": None, "rol": rol}}


class SesionFalsa:
    user_id = "yo"
    access = "token"

    def __init__(self):
        self.llamadas = []
        self.subidos = []
        self.mios = []
        self.mensajes = []
        self.ver = _grupo(rol="dueno")

    def rpc(self, nombre, **p):
        self.llamadas.append((nombre, p))
        if nombre == "mis_grupos":
            return self.mios
        if nombre == "grupos_explorar":
            return [_grupo("g9", "Salsa", rol=None)]
        if nombre == "grupo_crear":
            return _grupo("nuevo", p["p_nombre"], p["p_tipo"], "dueno", "ABCD2345" if p["p_tipo"] == "privado" else None)
        if nombre == "grupo_unirse":
            return _grupo(p["p_grupo"], "Salsa")
        if nombre == "grupo_unirse_codigo":
            return _grupo("gp", "Primos", "privado", codigo=p["p_codigo"])
        if nombre == "grupo_mensajes":
            return list(reversed(self.mensajes))
        if nombre in ("grupo_mensajes_desde", "grupo_fijados", "grupo_reportados"):
            return []
        if nombre == "grupo_enviar":
            return _mensaje(90 + len(self.llamadas), "yo", True, p.get("p_texto") or "", p.get("p_pista"),
                            p.get("p_audio"), p.get("p_audio_seg"))
        if nombre == "grupo_ver":
            return self.ver
        if nombre == "grupo_miembros_lista":
            return [{"id": "yo", "usuario": "yo", "nombre": "Yo", "rol": "dueno"},
                    {"id": "id-ana", "usuario": "ana", "nombre": "Ana", "rol": "miembro"}]
        return None

    def pedir(self, metodo, ruta, **kw):
        return self.rpc(ruta[4:], **(kw.get("json") or {}))

    def subir_archivo(self, bucket, ruta, datos, tipo, reemplazar=False, avance=None, tiempo=120):
        self.subidos.append((bucket, ruta, tipo, len(datos)))

    def url_firmada(self, bucket, ruta, segundos=3600):
        return f"https://x/{bucket}/{ruta}?token=t"


class CtxFalso(QObject):
    cambio = Signal()

    def __init__(self, sesion):
        super().__init__()
        self.cuenta = {"usuario": "yo", "nombre": "Yo", "sesion": sesion}
        self.avisos = []
        self.navegaciones = []
        self.reproducidas = []
        self.reproductor = None

    def avisar(self, texto, deshacer=None):
        self.avisos.append(texto)

    def navegar(self, d):
        self.navegaciones.append(d)

    def reproducir_pista(self, p, contexto=None):
        self.reproducidas.append(p)


def esperar(app, cond, que, maximo=8):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


def textos(w):
    return " | ".join(l.text() for l in w.findChildren(QLabel))


# ================================================================ servicio

def test_codigo_y_cancion_limpios():
    assert G.limpiar_codigo(" abcd-2345 ") == "ABCD2345"
    p = G.pista_para_grupo({"video_id": "kJQP7kiw5Fk", "titulo": "Despacito", "duracion": 282.4, "clave": "yt:x",
                            "artistas": [{"nombre": "Luis Fonsi"}, {"nombre": "Daddy Yankee"}], "archivo": "c:/x.mp3",
                            "miniatura": "https://i.ytimg.com/x.jpg"})
    assert p == {"video_id": "kJQP7kiw5Fk", "titulo": "Despacito", "artista": "Luis Fonsi, Daddy Yankee",
                 "miniatura": "https://i.ytimg.com/x.jpg", "duracion": "282"}


def test_vista_previa():
    assert G.vista_previa(_grupo(ultimo={"nombre": "Ana", "texto": "hola"})) == "Ana: hola"
    assert G.vista_previa(_grupo(ultimo={"usuario": "beto", "audio": True})) == "beto: 🎤 Nota de voz"
    assert G.vista_previa(_grupo()) == "3 personas"


def test_mensajes_en_orden_y_nota_de_voz_recortada():
    s = SesionFalsa()
    s.mensajes = [_mensaje(1), _mensaje(2, audio="g1/x/1.m4a", seg=12)]
    api = G.Grupos(s)
    l = api.mensajes("g1")
    assert [m["id"] for m in l] == [1, 2] and l[1]["visible"] == "ANA"
    api.enviar("g1", audio="g1/yo/1.m4a", audio_seg=999)
    assert s.llamadas[-1] == ("grupo_enviar", {"p_grupo": "g1", "p_texto": "", "p_pista": None,
                                               "p_audio": "g1/yo/1.m4a", "p_audio_seg": 180})


def test_subir_nota_a_su_carpeta():
    s = SesionFalsa()
    ruta = G.Grupos(s).subir_audio("g1", b"123", "audio/mp4")
    assert ruta.startswith("g1/yo/") and ruta.endswith(".m4a")
    assert s.subidos == [("audios-grupos", ruta, "audio/mp4", 3)]


def test_errores_en_lenguaje_normal():
    class R:
        status_code = 400
        text = "x"

        def __init__(self, m):
            self.m = m

        def json(self):
            return {"message": self.m, "code": "P0001"}
    assert str(nube._traducir(R("vas muy rápido; espera unos segundos"))) == "Vas muy rápido. Espera unos segundos."
    assert str(nube._traducir(R("esa canción no se puede compartir"))) == "Esa canción no se puede compartir."
    # las frases de antes siguen igual
    assert "Primero deben ser amigos" in str(nube._traducir(R("primero deben ser amigos")))


def test_comprimir_nota_con_ffmpeg():
    from descargador import notas_voz as NV
    import math
    import struct
    pcm = b"".join(struct.pack("<h", int(8000 * math.sin(i / 8))) for i in range(NV.TASA * 2))
    datos, tipo = NV.comprimir(pcm)
    if tipo == "audio/mp4":
        assert len(datos) < len(pcm) / 4          # AAC: mucho más liviano que el WAV
    else:
        assert datos[:4] == b"RIFF"              # sin ffmpeg queda en WAV


# ================================================================ pantalla

def test_pagina_sin_grupos_y_crear(app, monkeypatch):
    from descargador.ui.paginas import grupos as P
    s = SesionFalsa()
    ctx = CtxFalso(s)
    pag = P.PaginaGrupos(ctx)
    pag.resize(1100, 700)
    pag.show()
    esperar(app, lambda: "Aún no estás en ningún grupo" in textos(pag), "lista vacía")
    d = P.DialogoCrearGrupo(ctx, pag.api, pag)
    assert "No se pueden enviar imágenes ni videos" in textos(d)
    d.nombre.setText("Primos")
    d.privado.setChecked(True)
    d._crear()
    esperar(app, lambda: d.grupo is not None, "crear")
    assert ("grupo_crear", {"p_nombre": "Primos", "p_descripcion": "", "p_tipo": "privado"}) in s.llamadas
    pag.close()


def test_conversacion_texto_cancion_y_nota(app):
    from descargador.ui.paginas import grupos as P
    s = SesionFalsa()
    s.mios = [_grupo(sin_leer=150, ultimo={"nombre": "Ana", "texto": "quién va"})]
    s.mensajes = [_mensaje(1, "ana", texto="Hola gente", rol="dueno"), _mensaje(2, "ana", texto="Qué escuchan"),
                  _mensaje(3, "beto", texto="", pista={"video_id": "kJQP7kiw5Fk", "titulo": "Despacito",
                                                        "artista": "Luis Fonsi", "miniatura": ""}),
                  _mensaje(4, "beto", texto="", audio="g1/b/1.m4a", seg=65)]
    ctx = CtxFalso(s)
    pag = P.PaginaGrupos(ctx)
    pag.resize(1100, 700)
    pag.show()
    esperar(app, lambda: "99+" in textos(pag), "lista con sin leer")
    pag.abrir(s.mios[0])
    esperar(app, lambda: "Despacito" in textos(pag), "mensajes")
    t = textos(pag)
    assert t.count("ANA · dueño") == 1                 # el nombre una vez por tanda
    assert "🎤 1:05" in t
    # no hay botones de imágenes ni videos: solo emoji, canción, micrófono y enviar
    herramientas = [b.toolTip() for b in pag.panel.findChildren(QToolButton)]
    assert not any("imagen" in x.lower() or "video" in x.lower() or "foto" in x.lower() for x in herramientas)
    pag.campo.setText("Yo voy")
    pag._enviar()
    esperar(app, lambda: any(n == "grupo_enviar" for n, _p in s.llamadas), "enviar")
    esperar(app, lambda: "Yo voy" in textos(pag) and "Enviando…" not in textos(pag), "confirmado")
    # escuchar la canción compartida
    for b in pag.panel.findChildren(QPushButton):
        if b.toolTip() == "Escuchar":
            b.click()
    assert ctx.reproducidas and ctx.reproducidas[0]["video_id"] == "kJQP7kiw5Fk"
    pag.close()


def test_mandar_nota_de_voz_sube_y_envia(app, monkeypatch):
    from descargador.ui.paginas import grupos as P
    s = SesionFalsa()
    ctx = CtxFalso(s)
    pag = P.PaginaGrupos(ctx)
    pag.show()
    pag.abrir(_grupo())
    esperar(app, lambda: pag.campo.isEnabled(), "abierto")
    pag._mandar(datos=b"x" * 1000, tipo="audio/mp4", seg=7)
    esperar(app, lambda: any(n == "grupo_enviar" for n, _p in s.llamadas), "nota enviada")
    envio = [p for n, p in s.llamadas if n == "grupo_enviar"][-1]
    assert envio["p_audio"].startswith("g1/yo/") and envio["p_audio_seg"] == 7
    assert s.subidos[0][0] == "audios-grupos"
    pag.close()


def test_menu_de_mensaje_segun_rol(app, monkeypatch):
    from descargador.ui.paginas import grupos as P
    vistos = []

    class MenuFalso:
        def __init__(self, *_a):
            self.textos = []

        def addAction(self, t):
            self.textos.append(t)
            return t

        def exec(self, *_a):
            vistos.append(list(self.textos))
            return None
    monkeypatch.setattr(P, "QMenu", MenuFalso)
    s = SesionFalsa()
    pag = P.PaginaGrupos(CtxFalso(s))
    pag.actual = _grupo(rol="miembro")
    pag._opciones(_mensaje(5, "ana", texto="algo"), None)
    pag.actual = _grupo(rol="moderador")
    pag._opciones(_mensaje(5, "ana", texto="algo"), None)
    assert vistos[0] == ["Copiar texto", "Reportar…"]
    assert vistos[1] == ["Copiar texto", "Fijar arriba", "Ocultar", "Reportar…", "Borrar"]


def test_info_privado_codigo_y_gente(app):
    from descargador.ui.paginas import grupos as P
    s = SesionFalsa()
    s.ver = _grupo(tipo="privado", rol="dueno", codigo="ABCD2345")
    d = P.DialogoInfoGrupo(CtxFalso(s), G.Grupos(s), _grupo(tipo="privado", rol="dueno"))
    d.show()
    esperar(app, lambda: "ABCD2345" in textos(d), "código")
    assert "Ana" in textos(d)
    assert d.bt_borrar.isVisible()
    d.close()


def test_pagina_estrecha_lista_o_chat(app):
    from descargador.ui.paginas import grupos as P
    s = SesionFalsa()
    s.mios = [_grupo()]
    pag = P.PaginaGrupos(CtxFalso(s))
    pag.resize(560, 700)
    pag.show()
    app.processEvents()
    assert pag.caja_izq.isVisible() and not pag.panel.isVisible()
    pag.abrir(_grupo())
    app.processEvents()
    assert pag.panel.isVisible() and not pag.caja_izq.isVisible() and pag.bt_volver.isVisible()
    pag._volver()
    app.processEvents()
    assert pag.caja_izq.isVisible()
    pag.close()
