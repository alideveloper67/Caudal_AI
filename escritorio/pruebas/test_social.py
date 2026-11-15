# -*- coding: utf-8 -*-
"""Perfiles, amigos, directorio, música de la comunidad y Mensajes con amistad.

Sin internet ni ventanas (Qt offscreen) y con los datos de la app en una carpeta temporal:
la sesión de la nube es un doble que contesta lo que contestaría la base de datos.
"""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QPushButton  # noqa: E402

from descargador import nube  # noqa: E402
from descargador import social as S  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet_para_imagenes(monkeypatch):
    """Las fotos y carátulas no se bajan de internet en las pruebas."""
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "_leer", lambda url: b"")


class SesionFalsa:
    user_id = "yo-id"
    access = "token"

    def __init__(self, datos=None):
        self.datos = datos or {}
        self.llamadas = []
        self.subidos = []
        self.borrados = []
        self.fallar_registro = False

    def rpc(self, nombre, **p):
        self.llamadas.append((nombre, p))
        r = self.datos.get(nombre)
        return r(p) if callable(r) else r

    def pedir(self, metodo, ruta, **kw):
        if ruta.startswith("rpc/"):
            return self.rpc(ruta[4:], **(kw.get("json") or {}))
        self.llamadas.append((metodo, ruta, kw))
        r = self.datos.get(ruta)
        return r(kw) if callable(r) else r

    def subir_archivo(self, bucket, ruta, datos, tipo, reemplazar=False, avance=None, tiempo=120):
        if avance:
            avance(len(datos), len(datos))
        self.subidos.append((bucket, ruta, tipo, len(datos)))

    def borrar_archivos(self, bucket, rutas):
        self.borrados.append((bucket, list(rutas)))


class CtxFalso(QObject):
    aviso = Signal(str)

    def __init__(self, sesion, usuario="ana"):
        super().__init__()
        self.cuenta = {"usuario": usuario, "nombre": "Ana", "sesion": sesion}
        self.avisos = []
        self.aviso.connect(self.avisos.append)
        self.navegaciones = []
        self.reproducidas = []
        self.reproductor = None
        self.ventana = None

    def navegar(self, d):
        self.navegaciones.append(d)

    def reproducir_pista(self, p, contexto=None):
        self.reproducidas.append(p)


def esperar(app, cond, que, maximo=10):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


def textos(widget):
    return " | ".join(l.text() for l in widget.findChildren(QLabel))


def notas(widget):
    return [" ".join(l.text() for l in f.findChildren(QLabel)).strip()
            for f in widget.findChildren(QFrame) if f.objectName() == "nota_social"]


PERFIL = {"id": "u2", "usuario": "bea", "nombre": "Bea Luna", "foto_url": None, "bio": "Amo el indie",
          "frase": "Música todo el día", "cancion_fav": {"video_id": "abc12345678", "titulo": "Canción X",
                                                          "artista": "Grupo Y", "miniatura": "http://x/y.jpg"},
          "artista_fav": "Grupo Y", "generos": ["Indie", "Pop"], "color_perfil": "#FF5C8A",
          "creado": "2026-03-04T10:00:00Z", "relacion": "ninguna", "es_mio": False, "publico": True,
          "mostrar_top": True, "top_artistas": [{"nombre": "Grupo Y", "portada": "", "veces": 9}],
          "top_canciones": [{"video_id": "abc12345678", "titulo": "Canción X", "artista": "Grupo Y", "veces": 4}],
          "insignias": [{"clave": "veterano", "titulo": "Veterano", "detalle": "Más de 3 meses"},
                        {"clave": "creador", "titulo": "Creador", "detalle": "Sube música"}],
          "afinidad": 78, "likes": 12, "es_artista": False, "di_like": False, "fundador": True, "numero": 17,
          "fundador_caudal": True,
          "titulos": [{"clave": "fundador_caudal", "nombre": "Fundador de Caudal"},
                      {"clave": "rey_de_la_musica", "nombre": "Rey de la música"}],
          "subidas": [{"id": "s1", "titulo": "Mi tema", "artista": "Bea", "album": "Primero", "duracion": 200,
                       "ruta": "u2/a.mp3", "portada": "u2/a.jpg", "escuchas": 3, "estado": "publicada",
                       "creado": "2026-05-01T00:00:00Z"}],
          "num_subidas": 1}


# ====================================================================== nube y datos

class RespuestaFalsa:
    def __init__(self, cuerpo, estado=400):
        self._c, self.status_code, self.text = cuerpo, estado, "x"

    def json(self):
        return self._c


def test_errores_de_la_base_se_cuentan_para_personas():
    t = lambda msg, est=400: str(nube._traducir(RespuestaFalsa({"message": msg, "code": "P0001"}, est)))  # noqa: E731
    assert "amigos" in t("primero deben ser amigos")
    assert "30 días" in t("espera unos dias para volver a enviarla")
    assert "demasiadas solicitudes" in t("tienes demasiadas solicitudes pendientes")
    assert "carátula" in t("la cancion necesita una portada")
    assert "15 MB" in t("The object exceeded the maximum allowed size", 413)
    assert "formato" in t("mime type audio/x is not supported").lower()
    # los de siempre siguen igual
    assert "Usuario o contraseña" in t("Invalid login credentials")
    assert "Ese usuario ya existe" in t("User already registered")
    assert "respondió un error" in t("algo raro", 418)


def test_perfil_tolera_campos_que_faltan():
    p = S.perfil_limpio({"id": "x", "usuario": "ana"})
    assert p["bio"] == "" and p["generos"] == [] and p["cancion_fav"] is None
    assert p["subidas"] == [] and p["insignias"] == [] and p["afinidad"] is None
    assert p["mostrar_top"] is True and p["fundador"] is False and p["titulos"] == []
    assert S.perfil_limpio(None)["usuario"] == ""
    assert S.perfil_limpio({"color_perfil": "rojo"})["color_perfil"] is None
    assert S.perfil_limpio({"likes": 250})["es_artista"] is True


def test_titulos_fundador_y_especiales():
    p = S.perfil_limpio(PERFIL)
    assert [k for k, _t in S.titulos_de(p)] == ["fundador_caudal", "rey_de_la_musica", "fundador"]
    assert S.titulos_de(p)[2][1] == "Fundador n.º 17 ★"
    solo = S.perfil_limpio({"fundador": True})
    assert S.titulos_de(solo) == [("fundador", "Usuario fundador ★")]
    # un título que la app no conoce se dibuja igual, con el nombre que llega
    raro = S.perfil_limpio({"titulos": [{"clave": "nuevo_titulo", "nombre": "Un título nuevo"}]})
    assert S.titulos_de(raro) == [("nuevo_titulo", "Un título nuevo")]
    # con el bool suelto (contrato anterior) también sale
    assert S.titulos_de(S.perfil_limpio({"fundador_caudal": True}))[0][1] == "Fundador de Caudal"
    assert S.titulos_de(S.perfil_limpio({"likes": 200}))[-1] == ("artista", "ARTISTA")
    assert S.titulos_de(S.perfil_limpio({})) == []


def test_amistad_texto_y_acciones():
    assert S.accion_amistad("ninguna")[:2] == ("Agregar", "enviar")
    assert S.accion_amistad("enviada")[:2] == ("Solicitud enviada", "cancelar")
    assert S.accion_amistad("recibida")[:2] == ("Aceptar solicitud", "aceptar")
    assert S.accion_amistad("amigo")[:2] == ("Escribir", "escribir")
    assert S.accion_amistad("yo")[1] is None and S.accion_amistad("bloqueado")[1] == "desbloquear"
    assert S.relacion_tras_envio("aceptada") == "amigo" and S.relacion_tras_envio("enviada") == "enviada"
    assert "amigos" in S.mensaje_tras_envio("aceptada", "Bea").lower()


def test_direcciones_de_fotos_y_musica():
    u = S.url_foto("u2/avatar.jpg")
    assert u.startswith(nube.URL + "/storage/v1/object/public/avatares/u2/avatar.jpg?v=")
    S.marcar_foto("u2/avatar.jpg", 123)
    assert S.url_foto("u2/avatar.jpg").endswith("?v=123")
    assert S.url_foto(None) == ""
    assert S.url_musica("u2/a.mp3") == nube.URL + "/storage/v1/object/public/musica/u2/a.mp3"


def _imagen_prueba(ruta, ancho, alto, alfa=False):
    img = QImage(ancho, alto, QImage.Format_ARGB32 if alfa else QImage.Format_RGB32)
    img.fill(QColor("#336699"))
    assert img.save(str(ruta))


def test_foto_se_recorta_cuadrada_y_pesa_poco(app, tmp_path):
    for nombre, (w, h) in {"ancha.png": (1600, 900), "alta.png": (700, 2000), "chica.png": (200, 120)}.items():
        _imagen_prueba(tmp_path / nombre, w, h, alfa=True)
        datos = S.preparar_foto(tmp_path / nombre)
        img = QImage()
        img.loadFromData(datos)
        assert datos[:2] == b"\xff\xd8"                       # JPEG
        assert img.width() == img.height() == min(512, min(w, h))
        assert len(datos) < S.TOPE_IMAGEN
    _imagen_prueba(tmp_path / "grande.jpg", 3000, 3000)
    c = QImage()
    c.loadFromData(S.preparar_portada(tmp_path / "grande.jpg"))
    assert c.width() == c.height() == 800
    with pytest.raises(S.ErrorNube) as e:
        S.preparar_foto(tmp_path / "no_existe.png")
    assert "No se pudo abrir" in str(e.value)


def test_audio_se_revisa_con_frases_claras(tmp_path):
    ok = tmp_path / "a.mp3"
    ok.write_bytes(b"x" * 1000)
    assert S.revisar_audio(ok) == (".mp3", "audio/mpeg", 1000)
    mal = tmp_path / "b.wma"
    mal.write_bytes(b"x")
    with pytest.raises(S.ErrorNube, match="no se puede subir"):
        S.revisar_audio(mal)
    grande = tmp_path / "c.wav"
    grande.write_bytes(b"x" * (S.TOPE_AUDIO + 1))
    with pytest.raises(S.ErrorNube, match="15 MB"):
        S.revisar_audio(grande)
    with pytest.raises(S.ErrorNube, match="No se encontró"):
        S.revisar_audio(tmp_path / "nada.mp3")
    d = S.leer_datos_audio(tmp_path / "Grupo - Tema.mp3")
    assert d["artista"] == "Grupo" and d["titulo"] == "Tema"


def test_pista_de_la_comunidad_es_pista_local_con_datos_extra():
    s = S.subida_limpia({"id": "s1", "titulo": "Tema", "artista": "Bea", "album": "Disco", "duracion": 100,
                         "ruta": "u2/a.mp3", "portada": "u2/a.jpg", "usuario": "bea"})
    p = S.pista_de_subida(s, "C:/x/s1.mp3")
    assert p["tipo"] == "pista" and p["archivo"] == "C:/x/s1.mp3" and p["es_audio"] is True
    assert p["clave"] == "comunidad:s1" and p["subida_id"] == "s1" and p["subida_por"] == "bea"
    assert p["album"]["nombre"] == "Disco" and p["miniatura"].endswith("/musica/u2/a.jpg")
    assert S.pista_de_favorita({"video_id": "abc", "titulo": "T"})["clave"] == "yt:abc"
    assert S.pista_de_favorita({"titulo": "sin id"}) is None


def test_descargar_subida_guarda_una_vez(monkeypatch, tmp_path):
    import requests
    s = S.subida_limpia({"id": "s9", "ruta": "u2/a.mp3", "titulo": "T"})
    llamadas = []

    class R:
        status_code = 200
        headers = {"Content-Length": "6"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def iter_content(self, n):
            yield b"abc"
            yield b"def"

    monkeypatch.setattr(requests, "get", lambda *a, **k: llamadas.append(a) or R())
    ruta = S.descargar_subida(s)
    assert open(ruta, "rb").read() == b"abcdef"
    S.descargar_subida(s)
    assert len(llamadas) == 1                                  # la segunda sale del disco
    os.remove(ruta)


def test_subir_cancion_registra_y_limpia_si_falla(app, tmp_path):
    _imagen_prueba(tmp_path / "c.png", 600, 400)
    audio = tmp_path / "t.mp3"
    audio.write_bytes(b"x" * 5000)
    ses = SesionFalsa({"registrar_subida": "nuevo-id"})
    pasos = []
    nuevo = S.Social(ses).subir_cancion(audio, tmp_path / "c.png", "Tema", "Bea", "Disco", 100,
                                        avance=lambda f, t: pasos.append(f))
    assert nuevo == "nuevo-id" and pasos[-1] == 1.0 and pasos == sorted(pasos)
    assert [x[0] for x in ses.subidos] == ["musica", "musica"]
    assert ses.subidos[0][1].startswith("yo-id/") and ses.subidos[0][1].endswith(".mp3")
    assert ses.subidos[1][1].endswith(".jpg") and ses.borrados == []
    nombre, p = ses.llamadas[-1]
    assert nombre == "registrar_subida" and p["p_album"] == "Disco" and p["p_tamano"] == 5000
    assert p["p_ruta"].startswith("yo-id/") and p["p_portada"].startswith("yo-id/")

    # si el registro falla, lo subido se borra
    def falla(_p):
        raise nube.ErrorNube("hoy ya subiste 10 canciones")
    ses2 = SesionFalsa({"registrar_subida": falla})
    with pytest.raises(nube.ErrorNube):
        S.Social(ses2).subir_cancion(audio, tmp_path / "c.png", "Tema")
    assert len(ses2.borrados) == 1 and len(ses2.borrados[0][1]) == 2
    # sin carátula o sin título ni se intenta
    with pytest.raises(nube.ErrorNube, match="carátula"):
        S.Social(SesionFalsa()).subir_cancion(audio, None, "Tema")
    with pytest.raises(nube.ErrorNube, match="título"):
        S.Social(SesionFalsa()).subir_cancion(audio, tmp_path / "c.png", "  ")


# ====================================================================== pantallas

def test_perfil_ajeno_muestra_todo_y_el_boton_cambia_con_la_relacion(app):
    ses = SesionFalsa({"ver_perfil": lambda p: PERFIL, "enviar_solicitud": "enviada",
                       "dar_like": 13})
    ctx = CtxFalso(ses)
    from descargador.ui.paginas.perfil import PaginaPerfil
    pag = PaginaPerfil(ctx, "bea")
    pag.resize(1000, 900)
    pag.show()
    esperar(app, lambda: pag.p is not None, "carga el perfil")
    t = textos(pag)
    for esperado in ("Bea Luna", "@bea", "marzo de 2026", "Os parecéis un 78 %", "Amo el indie", "Canción X",
                     "Veterano", "Creador", "Lo más escuchado este mes", "Mi tema", "Indie"):
        assert esperado in t, esperado
    # notas: «Fundador de Caudal» primero, luego el otro título y «Fundador n.º 17»
    n = notas(pag)
    assert n[0].startswith("FUNDADOR DE CAUDAL") and "REY DE LA MÚSICA" in n[1] and "Fundador n.º 17 ★" in n[2]
    botones = [b.text().strip() for b in pag.findChildren(QPushButton)]
    assert "Agregar" in botones and "Editar perfil" not in botones
    assert "Escribir" not in botones
    # la portada se tiñe con el color del perfil
    assert pag.lienzo.color.name().upper() != QColor(S.COLORES_PERFIL[4]).name().upper()
    pag.grab()
    # enviar la solicitud
    pag._amistad("enviar")
    esperar(app, lambda: PERFIL and any(c[0] == "enviar_solicitud" for c in ses.llamadas), "se envía")
    assert ses.llamadas[[c[0] for c in ses.llamadas].index("enviar_solicitud")][1] == {"p_otro": "u2"}


def test_perfil_de_amigo_tiene_escribir_y_el_privado_no_enseña_nada(app):
    amigo = dict(PERFIL, relacion="amigo")
    ctx = CtxFalso(SesionFalsa({"ver_perfil": lambda p: amigo}))
    from descargador.ui.paginas.perfil import PaginaPerfil
    pag = PaginaPerfil(ctx, "bea")
    esperar(app, lambda: pag.p is not None, "carga")
    botones = [b.text().strip() for b in pag.findChildren(QPushButton)]
    assert "Escribir" in botones and "Agregar" not in botones
    pag._escribir()
    assert ctx.chat_pendiente["id"] == "u2" and ctx.navegaciones[-1] == {"pagina": "mensajes"}

    privado = {"id": "u3", "usuario": "cami", "nombre": "Cami", "relacion": "ninguna", "privado": True,
               "fundador": True, "numero": 5}
    ctx2 = CtxFalso(SesionFalsa({"ver_perfil": lambda p: privado}))
    pag2 = PaginaPerfil(ctx2, "cami")
    esperar(app, lambda: pag2.p is not None, "carga privado")
    t = textos(pag2)
    assert "Este perfil es privado" in t and "Os parecéis" not in t and "Música subida" not in t
    assert "Fundador n.º 5 ★" in " ".join(notas(pag2))
    assert not any(b.text().strip() == "Me gusta" for b in pag2.findChildren(QPushButton))


def test_perfil_no_existe_o_sin_cuenta(app):
    from descargador.ui.paginas.perfil import PaginaPerfil
    ctx = CtxFalso(SesionFalsa({"ver_perfil": lambda p: None}))
    pag = PaginaPerfil(ctx, "nadie")
    esperar(app, lambda: "No encontramos este perfil" in textos(pag), "mensaje amable")
    ctx2 = CtxFalso(None)
    ctx2.cuenta["sesion"] = None
    pag2 = PaginaPerfil(ctx2)
    assert "necesitan tu cuenta" in textos(pag2)


def test_mi_perfil_edita_y_sube_musica(app):
    mio = dict(PERFIL, es_mio=True, relacion="yo", afinidad=None, usuario="ana", nombre="Ana", publico=False)
    ctx = CtxFalso(SesionFalsa({"ver_perfil": lambda p: mio}))
    from descargador.ui.paginas.perfil import PaginaPerfil
    pag = PaginaPerfil(ctx)
    esperar(app, lambda: pag.p is not None, "carga mi perfil")
    botones = [b.text().strip() for b in pag.findChildren(QPushButton)]
    assert "Editar perfil" in botones and "Subir música" in botones
    assert "Tu perfil es privado" in textos(pag) and "Os parecéis" not in textos(pag)


def test_editar_perfil_guarda_lo_que_se_ve(app, tmp_path):
    from descargador.ui.paginas.perfil_editar import DialogoEditarPerfil
    ses = SesionFalsa({"perfiles?id=eq.yo-id": lambda kw: [dict(kw["json"], perfil_publico=False)]})
    mio = S.perfil_limpio(dict(PERFIL, es_mio=True))
    d = DialogoEditarPerfil(CtxFalso(ses), S.Social(ses), mio)
    d.nombre.setText("Ana María")
    d.frase.setText("Hola")
    d.bio.setPlainText("x" * 400)
    assert len(d.bio.toPlainText()) == 300
    d._poner_color("#2BD576")
    d.botones_generos["Rock"].click()
    d.botones_generos["Jazz"].click()
    d.botones_generos["Metal"].click()          # ya hay Indie, Pop, Rock, Jazz: el quinto cabe
    d.botones_generos["Salsa"].click()          # el sexto no
    assert len(d.generos) == 5 and not d.botones_generos["Salsa"].isChecked()
    assert "hasta 5" in d.aviso_generos.text()
    d.chk_publico.setChecked(True)
    _imagen_prueba(tmp_path / "f.png", 800, 500)
    d.foto_ruta = str(tmp_path / "f.png")
    d.estado.setText("")
    d._guardar()
    esperar(app, lambda: d.result() == QDialog.Accepted or d.estado.text(), "guarda")
    assert d.result() == QDialog.Accepted
    patch = [c for c in ses.llamadas if c[0] == "PATCH"][0][2]["json"]
    assert patch["nombre"] == "Ana María" and patch["color_perfil"] == "#2BD576"
    assert patch["foto_url"] == "yo-id/avatar.jpg" and patch["perfil_publico"] is True
    assert patch["cancion_fav"]["video_id"] == "abc12345678" and len(patch["generos"]) == 5
    assert ses.subidos[0][:3] == ("avatares", "yo-id/avatar.jpg", "image/jpeg")
    # con nombre vacío no guarda
    d2 = DialogoEditarPerfil(CtxFalso(ses), S.Social(ses), mio)
    d2.nombre.setText("")
    d2._guardar()
    assert "nombre" in d2.estado.text().lower()


def test_directorio_tarjetas_pagina_y_acciones(app):
    def fila(i, **extra):
        d = {"id": f"p{i}", "usuario": f"user{i}", "nombre": f"Persona {i}", "foto_url": None,
             "bio": "Me gusta la música", "cancion_fav": PERFIL["cancion_fav"], "color_perfil": "#4C8DFF",
             "relacion": "ninguna", "likes": i, "di_like": False, "num_subidas": 2, "es_artista": i == 1}
        d.update(extra)
        return d
    pedidos = []

    def explorar(p):
        pedidos.append(p)
        base = p["p_desde"]
        if p["p_busqueda"] == "zzz":
            return []
        n = 24 if base == 0 else 5
        return [fila(base + i + 1, fundador=(base + i == 0), numero=3 if base + i == 0 else None)
                for i in range(n)]
    ses = SesionFalsa({"explorar_perfiles": explorar, "enviar_solicitud": "enviada", "dar_like": 8,
                       "ver_perfil": lambda p: dict(PERFIL, publico=False, es_mio=True, usuario="ana")})
    ctx = CtxFalso(ses)
    from descargador.ui.paginas.directorio import PaginaDirectorio, TarjetaPerfil
    pag = PaginaDirectorio(ctx)
    pag.resize(1100, 700)
    pag.show()
    esperar(app, lambda: len(pag.tarjetas) == 24, "primer lote")
    assert pag.fin is False and pedidos[0]["p_limite"] == 24
    pag.grab()
    t0 = pag.tarjetas[0]
    assert "Persona 1" in textos(t0) and "Canción X" in textos(t0) and "♪ 2 canciones" in textos(t0)
    assert any("Fundador n.º 3" in n for n in notas(t0))
    assert "Tu perfil es privado" in " ".join(textos(pag) for _ in [0]) or True
    esperar(app, lambda: "Tu perfil es privado" in textos(pag), "aviso de perfil privado")
    # el segundo lote llega al pedirlo (al llegar al final)
    pag._cargar_mas()
    esperar(app, lambda: len(pag.tarjetas) == 29, "segundo lote")
    assert pedidos[1]["p_desde"] == 24 and pag.fin is True
    # me gusta y solicitud desde la tarjeta
    t0._like()
    esperar(app, lambda: t0.p["di_like"], "me gusta")
    assert t0.p["likes"] == 8
    t0._amistad()
    esperar(app, lambda: t0.p["relacion"] == "enviada", "solicitud")
    assert t0.bt_amistad.text() == "Solicitud enviada"
    # buscar sin resultados
    pag.campo.setText("zzz")
    pag._nueva_busqueda()
    esperar(app, lambda: "Sin resultados" in textos(pag), "sin resultados")
    assert pedidos[-1]["p_busqueda"] == "zzz" and not pag.tarjetas
    # abrir un perfil desde la tarjeta
    t = TarjetaPerfil(S.tarjeta_limpia(fila(7)), ctx, S.Social(ses))
    t.abrir.emit("user7")


def test_amigos_solicitudes_y_busqueda_exacta(app):
    estado = {"solicitudes": [{"id": 5, "de": "u9", "usuario": "zoe", "nombre": "Zoe", "foto_url": None,
                               "creado": "2026-01-01T00:00:00Z"}],
              "amigos": [{"id": "u2", "usuario": "bea", "nombre": "Bea", "foto_url": None}]}
    ses = SesionFalsa({
        "mis_solicitudes": lambda p: estado["solicitudes"],
        "mis_enviadas": [{"id": 6, "para": "u7", "usuario": "leo", "nombre": "Leo", "foto_url": None}],
        "mis_amigos": lambda p: estado["amigos"],
        "buscar_persona": lambda p: [{"id": "u5", "usuario": p["p_usuario"], "nombre": "Nuevo",
                                     "foto_url": None, "relacion": "ninguna"}] if p["p_usuario"] == "nuevo" else [],
        "responder_solicitud": lambda p: estado["solicitudes"].clear(),
        "enviar_solicitud": "enviada",
    })
    ctx = CtxFalso(ses)
    from descargador.ui.paginas.amigos import PaginaAmigos, PanelAmigos, PanelSolicitudes
    sol = PanelSolicitudes(ctx, compacto=True)
    cuentas = []
    sol.contador.connect(cuentas.append)
    sol.show()
    esperar(app, lambda: cuentas == [1], "una solicitud nueva")
    t = textos(sol)
    assert "Zoe" in t and "Leo" in t and "esperando respuesta" in t
    sol._responder(S.persona_limpia(estado["solicitudes"][0]), True)
    esperar(app, lambda: cuentas[-1] == 0, "se acepta y el contador baja")
    assert ses.llamadas[[c[0] for c in ses.llamadas].index("responder_solicitud")][1] == {"p_id": 5,
                                                                                         "p_acepta": True}
    ami = PanelAmigos(ctx)
    ami.show()
    esperar(app, lambda: "MIS AMIGOS (1)" in textos(ami), "lista de amigos")
    escritos = []
    ami.escribir.connect(escritos.append)
    botones = [b for b in ami.findChildren(QPushButton) if b.text().strip() == "Escribir"]
    assert len(botones) == 1                                    # solo el amigo tiene botón de chat
    botones[0].click()
    assert escritos[0]["usuario"] == "bea"
    # buscar por usuario exacto: quien no es amigo no tiene «Escribir», tiene «Agregar»
    ami.campo.setText("nuevo")
    ami._buscar()
    esperar(app, lambda: "Nuevo" in textos(ami) and any(b.text().strip() == "Agregar"
                                                         for b in ami.findChildren(QPushButton)), "resultado")
    assert len([b for b in ami.findChildren(QPushButton) if b.text().strip() == "Escribir"]) == 1
    ami.campo.setText("nadie")
    ami._buscar()
    esperar(app, lambda: "No hay nadie con el usuario «nadie»" in textos(ami), "no existe")
    pag = PaginaAmigos(ctx, "amigos")
    pag.resize(900, 700)
    pag.show()
    esperar(app, lambda: "MIS AMIGOS" in textos(pag), "página de amigos")
    assert pag.botones["amigos"].isChecked() and not pag.sol.isVisibleTo(pag)
    pag.grab()


def _chats():
    return [{"id": "c1", "otro": "u2", "usuario": "bea", "nombre": "Bea", "ultimo": "2026-05-01T10:00:00Z",
             "ultimo_texto": "hola", "ultimo_pista": None, "ultimo_autor": "u2", "sin_leer": 1,
             "foto_url": None},
            {"id": "c2", "otro": "u3", "usuario": "cami", "nombre": "Cami", "ultimo": "2026-04-01T10:00:00Z",
             "ultimo_texto": "adiós", "ultimo_pista": None, "ultimo_autor": "u3", "sin_leer": 0,
             "foto_url": None}]


def test_mensajes_pestanas_y_solo_amigos(app):
    ses = SesionFalsa({"mis_chats": _chats(), "mis_amigos": [{"id": "u2", "usuario": "bea", "nombre": "Bea"}],
                       "mis_solicitudes": [{"id": 5, "de": "u9", "usuario": "zoe", "nombre": "Zoe"}],
                       "mis_enviadas": [], "abrir_chat": "c-nuevo", "marcar_leido": None})
    ctx = CtxFalso(ses)
    from descargador.ui.paginas.mensajes import PaginaMensajes
    pag = PaginaMensajes(ctx)
    pag.resize(1000, 640)
    pag.show()
    esperar(app, lambda: pag._lista_cargada, "lista de chats")
    assert pag.tabs["solicitudes"].text() == "Solicitudes (1)"
    assert pag.tabs["chats"].isChecked() and set(pag.tabs) == {"chats", "solicitudes", "amigos"}
    chats, _n = pag.chat.panorama()
    assert [c["es_amigo"] for c in chats] == [True, False]
    # con un amigo se puede escribir
    pag._abrir(chats[0])
    assert pag.campo.isEnabled() and not pag.aviso_no_amigo.isVisibleTo(pag)
    # con quien dejó de ser amigo, no: se explica y no hay botón de enviar
    pag._abrir(chats[1])
    assert not pag.campo.isEnabled() and pag.aviso_no_amigo.isVisibleTo(pag)
    pag.campo.setText("hola")
    assert not pag.bt_enviar.isEnabled()
    pag._pestana("amigos")
    assert pag.panel_ami.isVisibleTo(pag) and not pag.scroll_lista.isVisibleTo(pag)
    pag._pestana("solicitudes")
    assert pag.panel_sol.isVisibleTo(pag)
    pag.grab()
    # abrir un chat pedido desde fuera (perfil o amigos)
    ctx.chat_pendiente = {"id": "u2", "usuario": "bea", "nombre": "Bea", "visible": "Bea"}
    pag2 = PaginaMensajes(ctx)
    esperar(app, lambda: pag2.actual is not None, "abre el chat pendiente")
    assert pag2.actual["id"] == "c-nuevo" and ctx.chat_pendiente is None


def test_nuevo_chat_pide_solicitud_si_no_son_amigos(app):
    ses = SesionFalsa({"enviar_solicitud": "enviada"})
    ctx = CtxFalso(ses)
    from descargador import chat as CH
    from descargador.ui.paginas.mensajes import DialogoNuevoChat
    d = DialogoNuevoChat(ctx, CH.Chat(ses))
    d.persona = {"id": "u5", "usuario": "nuevo", "nombre": "Nuevo", "relacion": "ninguna"}
    d._mostrar_persona()
    assert d.bt.text() == "Enviar solicitud" and d.bt.isEnabled()
    d._accion()
    esperar(app, lambda: d.persona["relacion"] == "enviada", "solicitud enviada")
    assert d.bt.text() == "Solicitud enviada" and not d.bt.isEnabled()
    d.persona["relacion"] = "amigo"
    d._mostrar_persona()
    assert d.bt.text() == "Escribir" and d.bt.isEnabled()
    d.persona["relacion"] = "recibida"
    d._mostrar_persona()
    assert d.bt.text() == "Aceptar solicitud"


def test_comunidad_lista_busca_reproduce_y_reporta(app, monkeypatch, tmp_path):
    def subida(i, usuario="otra", uid="u2"):
        return {"id": f"s{i}", "user_id": uid, "usuario": usuario, "titulo": f"Tema {i}", "artista": "Bea",
                "album": "Disco", "duracion": 180, "ruta": f"{uid}/{i}.mp3", "portada": f"{uid}/{i}.jpg",
                "escuchas": i, "creado": "2026-05-01T00:00:00Z", "es_artista": i == 1}
    ses = SesionFalsa({"explorar_subidas": lambda p: [subida(1), subida(2, "ana", "yo-id")] if not p["p_busqueda"]
                       else [], "contar_escucha_subida": None, "reportar_subida": None, "borrar_subida": None})
    ctx = CtxFalso(ses)

    class R(QObject):
        pista_cambio = Signal(object)
        colas = []

        def agregar_a_cola(self, p):
            self.colas.append(p)
    ctx.reproductor = R()
    bajadas = []
    monkeypatch.setattr(S, "descargar_subida", lambda s, avance=None: bajadas.append(s["id"]) or str(tmp_path / f"{s['id']}.mp3"))
    from descargador.ui.paginas import perfil_comun as PC
    from descargador.ui.paginas.comunidad import PaginaComunidad
    pag = PaginaComunidad(ctx)
    pag.resize(900, 700)
    pag.show()
    esperar(app, lambda: len(pag.subidas) == 2, "catálogo")
    t = textos(pag)
    assert "Tema 1" in t and "ARTISTA" in t and "Disco" in t
    assert "@otra" in [b.text() for b in pag.findChildren(QPushButton)]
    pag.grab()
    # una propia lleva borrar; una ajena, reportar
    ayudas = [b.toolTip() for b in pag.findChildren(QPushButton)]
    assert "Reportar esta canción" in ayudas and "Borrar mi canción" in ayudas
    # escuchar: se baja, suena como pista de archivo y la siguiente va a la cola
    pag._tocar(pag.subidas[0])
    esperar(app, lambda: ctx.reproducidas and ctx.reproductor.colas, "suena y encola")
    p = ctx.reproducidas[0]
    assert p["archivo"].endswith("s1.mp3") and p["subida_id"] == "s1" and p["es_audio"]
    assert ctx.reproductor.colas[0]["subida_id"] == "s2"
    # la escucha se cuenta al EMPEZAR a sonar (señal del reproductor), una vez por canción que empieza
    ctx.reproductor.pista_cambio.emit(p)
    esperar(app, lambda: any(c[0] == "contar_escucha_subida" for c in ses.llamadas), "escucha contada")
    assert [c[1] for c in ses.llamadas if c[0] == "contar_escucha_subida"] == [{"p_id": "s1"}]
    # reportar
    monkeypatch.setattr(PC.DialogoReportar, "exec", lambda self: PC.QDialog.Accepted)
    PC.reportar_subida(ctx, S.Social(ses), pag.subidas[0], pag)
    esperar(app, lambda: any(c[0] == "reportar_subida" for c in ses.llamadas), "reporte")
    rep = [c[1] for c in ses.llamadas if c[0] == "reportar_subida"][0]
    assert rep["p_id"] == "s1" and "derechos" in rep["p_motivo"]
    # buscar sin resultados
    pag.campo.setText("nada")
    pag._nueva_busqueda()
    esperar(app, lambda: "Sin resultados" in textos(pag), "sin resultados")


def test_subir_musica_exige_caratula_y_derechos(app, tmp_path):
    ses = SesionFalsa({"ver_perfil": lambda p: dict(PERFIL, es_mio=True, subidas=[]),
                       "registrar_subida": "nuevo"})
    ctx = CtxFalso(ses)
    from descargador.ui.paginas.subir_musica import PaginaSubirMusica
    pag = PaginaSubirMusica(ctx)
    pag.resize(900, 800)
    pag.show()
    assert not pag.bt_subir.isEnabled()
    audio = tmp_path / "Grupo - Tema.mp3"
    audio.write_bytes(b"x" * 2000)
    pag.ruta_audio = str(audio)
    pag.titulo_c.setText("Tema")
    pag.chk.setChecked(True)
    assert not pag.bt_subir.isEnabled()               # falta la carátula
    assert "carátula" in pag.bt_subir.toolTip()
    _imagen_prueba(tmp_path / "c.png", 500, 500)
    pag.ruta_portada = str(tmp_path / "c.png")
    pag._revisar()
    assert pag.bt_subir.isEnabled()
    pag.chk.setChecked(False)
    assert not pag.bt_subir.isEnabled()               # sin la casilla de derechos no se sube
    pag.chk.setChecked(True)
    pag._subir()
    assert not pag.bt_subir.isEnabled()
    esperar(app, lambda: "ya está en la comunidad" in pag.estado.text(), "sube")
    assert [s[1].rsplit(".", 1)[1] for s in ses.subidos] == ["mp3", "jpg"]
    assert pag.titulo_c.text() == "" and not pag.chk.isChecked()
    pag.grab()


def test_cambiar_el_tema_no_deja_colores_viejos_en_las_hojas(app):
    """Las hojas de estilo usan C[...]: con otro acento, el acento viejo no aparece."""
    from descargador.ui import estilos
    from descargador.ui.paginas import perfil_comun as PC
    from descargador.ui.paginas.directorio import TarjetaPerfil
    try:
        estilos.aplicar_aspecto("rosa", "noche")
        t = TarjetaPerfil(S.tarjeta_limpia({"id": "a", "usuario": "a", "nombre": "A", "color_perfil": None}),
                          CtxFalso(SesionFalsa()), S.Social(SesionFalsa()))
        hojas = " ".join(w.styleSheet() for w in [t] + t.findChildren(QPushButton)).lower()
        assert estilos.ACENTOS["rosa"][1].lower() in hojas
        assert estilos.ACENTOS["cian"][1].lower() not in hojas
        assert PC.color_de({}) == estilos.C["acento"]
    finally:
        estilos.aplicar_aspecto("cian", "oscuro")
