# -*- coding: utf-8 -*-
"""«Compartir perfil»: la tarjeta vertical 9:16 del perfil, sus tres estilos, guardar/copiar y el botón.

Sin internet ni ventanas (Qt offscreen). Las fotos y carátulas son imágenes sintéticas locales.
Genera capturas en pruebas/capturas_perfil/ para mirarlas a ojo.
"""

import os
import sys
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QPushButton  # noqa: E402

from descargador import tarjeta_perfil as T  # noqa: E402
from test_social import CtxFalso, SesionFalsa, esperar  # noqa: E402,F401

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_perfil")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet_para_imagenes(monkeypatch):
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "_leer", lambda url: b"")


def _imagen(c1, c2, w=640, h=640, ruido=0):
    im = QImage(w, h, QImage.Format_RGB32)
    p = QPainter(im)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    p.fillRect(0, 0, w, h, g)
    p.setPen(0)
    p.setBrush(QColor(255, 255, 255, 70))
    for i in range(ruido):
        p.drawEllipse(w * (i * 37 % 100) // 100 - 60, h * (i * 53 % 100) // 100 - 60, 160 + i * 9, 160 + i * 9)
    p.end()
    return im


@pytest.fixture(scope="module")
def imgs(app):
    return {"foto": _imagen("#ff9a8b", "#6a5acd", ruido=3), "banner": _imagen("#1e90ff", "#ff5c8a", 1200, 700, 0),
            "cancion": _imagen("#f5c542", "#c0392b", ruido=4), "top0": _imagen("#22d3ee", "#4c8dff", ruido=2),
            "top1": _imagen("#2bd576", "#14b8a6", ruido=2), "top2": _imagen("#8b6cff", "#ff5c8a", ruido=2)}


COMPLETO = {
    "id": "u2", "usuario": "bea", "nombre": "Bea Luna", "foto_url": "bea/foto.jpg", "banner_url": "bea/banner.jpg",
    "bio": "Amo el indie, las tardes de lluvia con audífonos y descubrir bandas pequeñas que nadie conoce "
           "todavía. Compongo en mis ratos libres y comparto lo que más me mueve.",
    "frase": "Música todo el día, todos los días",
    "cancion_fav": {"video_id": "abc12345678", "titulo": "Canción de las mil y una noches", "artista": "Grupo Y",
                    "miniatura": "http://x/y.jpg"},
    "artista_fav": "Grupo Y", "generos": ["Indie", "Pop", "Reguetón", "Lofi", "Jazz"], "color_perfil": "#FF5C8A",
    "relacion": "ninguna", "es_mio": False, "privado": False, "publico": True, "likes": 212, "num_subidas": 14,
    "es_artista": True, "fundador": True, "numero": 17, "fundador_caudal": True,
    "titulos": [{"clave": "fundador_caudal", "nombre": "Fundador de Caudal"},
                {"clave": "rey_de_la_musica", "nombre": "Rey de la música"}],
    "top_artistas": [{"nombre": "Grupo Y", "portada": "http://x/a.jpg", "veces": 9},
                     {"nombre": "Artista con un nombre larguísimo de verdad", "portada": "http://x/b.jpg", "veces": 5},
                     {"nombre": "Luz", "portada": "", "veces": 1}],
    "top_canciones": [], "subidas": [],
    "insignias": [{"clave": k} for k in ("veterano", "fiel", "explorador", "coleccionista", "maratonista", "creador")],
}

VACIO = {"id": "u9", "usuario": "nuevo", "nombre": "", "foto_url": None, "banner_url": None, "bio": "", "frase": "",
         "cancion_fav": None, "artista_fav": "", "generos": [], "color_perfil": None, "relacion": "ninguna",
         "es_mio": False, "privado": False, "likes": 0, "num_subidas": 0, "insignias": [], "titulos": [],
         "top_artistas": [], "es_artista": False, "fundador": False, "numero": None}


def _revisar(info, vacio=False):
    """Nada fuera del lienzo ni de los márgenes, bloques sin solaparse y sin huecos enormes."""
    for x, y, w, h, t in info["cajas"]:
        assert x >= -1 and x + w <= T.ANCHO + 1 and y >= 0 and y + h <= T.ALTO, ("fuera del lienzo", t)
        if y > 200:     # el cuerpo respeta los márgenes (la cabecera ya va dentro)
            assert x >= T.MARGEN - 8 and x + w <= T.ANCHO - T.MARGEN + 8, ("se sale del margen", t, x, w)
    b = info["bloques"]
    for (n1, y1, h1), (n2, y2, h2) in zip(b, b[1:]):
        assert y1 + h1 <= y2, ("se solapan", n1, n2)
        assert y2 - (y1 + h1) <= 130, ("hueco entre bloques", n1, n2, y2 - (y1 + h1))
    assert b[0][1] >= T.ZONA_CUERPO[0] - 1 and b[-1][1] + b[-1][2] <= T.ZONA_CUERPO[1] + 1
    if not vacio:
        # el contenido llena el espacio: poco margen sobrante arriba y abajo
        assert (b[0][1] - T.ZONA_CUERPO[0]) + (T.ZONA_CUERPO[1] - b[-1][1] - b[-1][2]) < 120


def test_la_imagen_sale_de_1080_por_1920(app, imgs):
    for e in T.ESTILOS:
        img = T.generar(COMPLETO, e, imgs)
        assert (img.width(), img.height()) == (1080, 1920) and not img.isNull()


def test_perfil_completo_sin_huecos_ni_texto_fuera(app, imgs):
    for e in T.ESTILOS:
        img, info = T.generar_con_info(COMPLETO, e, imgs)
        _revisar(info)
        nombres = [n for n, _y, _h in info["bloques"]]
        assert nombres == ["avatar", "nombre", "chips", "frase", "bio", "numeros", "cancion", "artista_fav",
                           "top", "generos", "insignias"]
        textos = " | ".join(c[4] for c in info["cajas"])
        for esperado in ("Bea Luna", "@bea", "Usuario N.º 17", "FUNDADOR DE CAUDAL", "REY DE LA MÚSICA", "ARTISTA",
                         "“Música todo el día, todos los días”", "MI CANCIÓN FAVORITA", "LO QUE MÁS ESCUCHO",
                         "INSIGNIAS", "Escucha música gratis en Caudal", "me gusta", "canciones subidas", "Indie"):
            assert esperado in textos, esperado


def test_perfil_casi_vacio_no_deja_huecos(app):
    img, info = T.generar_con_info(VACIO, "color", {})
    _revisar(info, vacio=True)
    assert [n for n, _y, _h in info["bloques"]] == ["avatar", "nombre"]
    assert info["k"] > 1.2        # lo poco que hay se ve más grande
    solo_bio = dict(VACIO, bio="Hola, soy nueva por aquí.")
    _img, info2 = T.generar_con_info(solo_bio, "claro", {})
    _revisar(info2, vacio=True)
    assert [n for n, _y, _h in info2["bloques"]] == ["avatar", "nombre", "bio"]


def test_los_tres_estilos_son_distintos(app, imgs):
    a, b, c = (T.generar(COMPLETO, e, imgs) for e in ("color", "oscuro", "claro"))
    assert a != b and b != c and a != c
    # el claro es claro y el oscuro es oscuro (muestra en una esquina libre)
    assert QColor(c.pixel(20, 1700)).lightness() > 180 and QColor(b.pixel(20, 1700)).lightness() < 60
    # sin imagen de fondo cambia respecto de con ella
    assert T.generar(COMPLETO, "oscuro", {}) != b


def test_texto_muy_largo_se_recorta_con_puntos_suspensivos(app, imgs):
    largo = dict(COMPLETO, bio=("palabra " * 200).strip(), frase="f" * 79 + " " + "frase larga " * 6,
                 nombre="Nombre " * 30, artista_fav="Artista " * 20,
                 cancion_fav={"video_id": "x", "titulo": "Título larguísimo " * 12, "artista": "A" * 200,
                              "miniatura": ""},
                 generos=["Género larguísimo " * 10], insignias=[{"clave": "veterano", "titulo": "Insignia " * 30}])
    img, info = T.generar_con_info(largo, "color", imgs)
    _revisar(info)
    assert info["recortados"]
    textos = [c[4] for c in info["cajas"]]
    assert any(t.endswith("…") for t in textos)
    # la descripción ocupa como mucho 5 líneas
    from PySide6.QtGui import QFontMetrics
    f = T._fuente(31 * info["k"])
    lineas = T.envolver(largo["bio"], QFontMetrics(f), 800, 5)
    assert len(lineas) == 5 and lineas[-1].endswith("…")
    assert len(T.envolver("una dos tres", QFontMetrics(f), 4000, 5)) == 1


def test_acentos_y_sin_estrella_duplicada(app, imgs):
    _img, info = T.generar_con_info(COMPLETO, "color", imgs)
    t = " | ".join(c[4] for c in info["cajas"])
    assert "Fundador n.º 17" in t and "★" not in t and "Â" not in t and "Ã" not in t


def test_traer_imagenes_usa_el_cargador_de_imagenes(app, monkeypatch, imgs):
    from descargador.ui import imagenes
    buf = QByteArray()
    b = QBuffer(buf)
    b.open(QIODevice.WriteOnly)
    imgs["foto"].save(b, "PNG")
    b.close()
    pedidas = []

    def leer(url):
        pedidas.append(url)
        return bytes(buf) if "foto" in url or "banner" in url else b""
    monkeypatch.setattr(imagenes, "_leer", leer)
    r = T.traer_imagenes(COMPLETO)
    assert set(r) == {"foto", "banner"} and len(pedidas) >= 5
    assert any("a.jpg" in u for u in pedidas) and any("x/y.jpg" in u for u in pedidas)


def test_dialogo_guardar_copiar_y_estilos(app, imgs, tmp_path, monkeypatch):
    from descargador.ui.paginas.perfil_compartir import DialogoCompartirPerfil
    ctx = CtxFalso(SesionFalsa())
    d = DialogoCompartirPerfil(ctx, COMPLETO, None, imagenes=imgs)
    assert d.vista.height() == 560 and d.vista.width() == 315 and d.vista.pixmap() is not None
    assert {b.text() for b in d.botones.values()} == {"Color del perfil", "Oscuro", "Claro"}
    primera = d.imagen
    d.botones["claro"].click()
    assert d.estilo == "claro" and d.imagen != primera
    # guardar: nombre sugerido caudal_perfil_<usuario>.png y PNG válido
    visto = {}

    def fingir(_p, _t, sugerido, filtro):
        visto["sugerido"] = sugerido
        return str(tmp_path / "salida.png"), filtro
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fingir))
    assert d.guardar() is True
    assert os.path.basename(visto["sugerido"]) == "caudal_perfil_bea.png"
    leida = QImage(str(tmp_path / "salida.png"))
    assert (leida.width(), leida.height()) == (1080, 1920)
    assert open(tmp_path / "salida.png", "rb").read(8) == b"\x89PNG\r\n\x1a\n"
    assert "Imagen guardada" in d.estado.text()
    # cancelar el diálogo no guarda nada
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a: ("", "")))
    assert d.guardar() is False
    # una ruta imposible avisa sin romper
    assert d.guardar_en(str(tmp_path / "no_existe" / "x.png")) is False and "No se pudo" in d.estado.text()
    # copiar al portapapeles
    d.copiar()
    cp = QGuiApplication.clipboard().image()
    assert (cp.width(), cp.height()) == (1080, 1920)
    # abrir carpeta (tras guardar, la de la última imagen)
    d.guardar_en(str(tmp_path / "otra.png"))
    abiertas = []
    from PySide6.QtGui import QDesktopServices
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda u: abiertas.append(u.toLocalFile()) or True))
    d.abrir_carpeta()
    assert abiertas and os.path.normcase(abiertas[0]) == os.path.normcase(str(tmp_path))


def test_el_dialogo_baja_las_imagenes_en_segundo_plano(app):
    from descargador.ui.paginas.perfil_compartir import DialogoCompartirPerfil
    d = DialogoCompartirPerfil(CtxFalso(SesionFalsa()), VACIO)
    esperar(app, lambda: d.imagen is not None, "se pinta la tarjeta")
    assert d.bt_guardar.isEnabled() and d.bt_copiar.isEnabled()


def _botones(pag):
    return [b.text().strip() for b in pag.findChildren(QPushButton)]


def test_el_boton_esta_en_perfiles_visibles_y_no_en_privados(app):
    from descargador.ui.paginas.perfil import PaginaPerfil
    ajeno = dict(COMPLETO, afinidad=None, di_like=False, mostrar_top=True)
    pag = PaginaPerfil(CtxFalso(SesionFalsa({"ver_perfil": lambda p: ajeno})), "bea")
    esperar(app, lambda: pag.p is not None, "carga ajeno")
    assert "Compartir perfil" in _botones(pag)
    mio = dict(ajeno, es_mio=True, usuario="ana")
    pag2 = PaginaPerfil(CtxFalso(SesionFalsa({"ver_perfil": lambda p: mio})), "ana")
    esperar(app, lambda: pag2.p is not None, "carga propio")
    assert "Compartir perfil" in _botones(pag2) and "Editar perfil" in _botones(pag2)
    privado = {"id": "u3", "usuario": "cami", "nombre": "Cami", "relacion": "ninguna", "privado": True}
    pag3 = PaginaPerfil(CtxFalso(SesionFalsa({"ver_perfil": lambda p: privado})), "cami")
    esperar(app, lambda: pag3.p is not None, "carga privado")
    assert "Compartir perfil" not in _botones(pag3)
    # al pulsar abre el diálogo con el perfil de esa persona (sin ejecutarlo de verdad)
    abierto = []
    from descargador.ui.paginas import perfil_compartir as PCm
    original = PCm.DialogoCompartirPerfil.exec
    PCm.DialogoCompartirPerfil.exec = lambda self: abierto.append(self.p["usuario"]) or 0
    try:
        pag._compartir()
    finally:
        PCm.DialogoCompartirPerfil.exec = original
    assert abierto == ["bea"]


def test_capturas_para_mirar(app, imgs):
    os.makedirs(CAPTURAS, exist_ok=True)
    for e in T.ESTILOS:
        assert T.generar(COMPLETO, e, imgs).save(os.path.join(CAPTURAS, f"perfil_completo_{e}.png"))
    assert T.generar(VACIO, "color", {}).save(os.path.join(CAPTURAS, "perfil_vacio_color.png"))
    casi = dict(VACIO, usuario="luna", nombre="Luna", bio="Hola, soy nueva por aquí.", color_perfil="#8B6CFF",
                likes=3)
    assert T.generar(casi, "oscuro", {}).save(os.path.join(CAPTURAS, "perfil_casi_vacio_oscuro.png"))
