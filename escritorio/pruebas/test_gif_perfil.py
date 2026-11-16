# -*- coding: utf-8 -*-
"""GIF animados en la foto y el fondo del perfil (solo donadores): detección, reducción, permisos,
buscador con cliente falso, avisos y que el avatar y el fondo se animen de verdad.

Sin internet ni ventanas (Qt offscreen). Capturas en pruebas/capturas_gif/ para mirarlas a ojo.
"""

import io
import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog  # noqa: E402

from descargador import gif_perfil as G  # noqa: E402
from descargador import nube  # noqa: E402
from descargador import social as S  # noqa: E402
from test_social import CtxFalso, SesionFalsa, esperar  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_gif")
os.makedirs(CAPTURAS, exist_ok=True)

COLORES = [(255, 90, 90), (90, 200, 120), (90, 140, 255), (255, 210, 70)]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet_para_imagenes(monkeypatch):
    from descargador.ui import imagenes
    monkeypatch.setattr(imagenes, "_leer", lambda url: b"")


def gif_de_colores(ancho=120, alto=120, cuadros=4, dur=120):
    """GIF pequeño cuyos cuadros son de colores muy distintos (para ver que anima)."""
    fr = []
    for i in range(cuadros):
        im = Image.new("RGB", (ancho, alto), COLORES[i % len(COLORES)])
        for k in range(0, ancho, 20):
            im.paste((255, 255, 255), (k, 0, k + 8, alto))
        fr.append(im.quantize(64))
    b = io.BytesIO()
    fr[0].save(b, "GIF", save_all=True, append_images=fr[1:], duration=dur, loop=0)
    return b.getvalue()


def gif_pesado(ancho, alto, cuadros, dur=70):
    """Ruido: casi no se comprime, así que pasa de 4,5 MB."""
    fr = []
    for i in range(cuadros):
        im = Image.frombytes("RGB", (ancho, alto), os.urandom(ancho * alto * 3))
        fr.append(im.quantize(256, dither=Image.NONE))
    b = io.BytesIO()
    fr[0].save(b, "GIF", save_all=True, append_images=fr[1:], duration=[dur + 10 * i for i in range(cuadros)],
               loop=0)
    return b.getvalue()


# ------------------------------------------------------------------ detección y reducción
def test_deteccion_de_gif(tmp_path):
    g = gif_de_colores()
    assert G.es_gif(g) and G.es_gif(b"GIF87a....")
    assert not G.es_gif(b"\xff\xd8\xff") and not G.es_gif(b"") and not G.es_gif(None)
    f = tmp_path / "foto.png"          # extensión mentirosa: manda la cabecera
    f.write_bytes(g)
    assert G.es_gif_ruta(str(f))
    j = tmp_path / "x.gif"
    j.write_bytes(b"\xff\xd8\xff\xe0")
    assert not G.es_gif_ruta(str(j))
    assert not G.es_gif_ruta(str(tmp_path / "no_existe.gif"))
    assert G.url_es_gif("https://x/storage/v1/object/public/avatares/u/avatar.gif?v=123")
    assert G.url_es_gif("u/banner.gif") and not G.url_es_gif("u/avatar.jpg") and not G.url_es_gif(None)


def test_gif_liviano_se_sube_tal_cual():
    g = gif_de_colores()
    assert G.preparar_gif(g, G.RAZON_FOTO) == g


@pytest.mark.parametrize("modo,tamano", [(G.RAZON_FOTO, (480, 480)), (G.RAZON_FONDO, (960, 360))])
def test_reduccion_con_pillow(modo, tamano):
    ancho, alto = (900, 700) if modo == G.RAZON_FOTO else (1200, 800)
    g = gif_pesado(ancho, alto, 14 if modo == G.RAZON_FOTO else 12)
    assert len(g) > G.TOPE_SUBIDA
    antes = Image.open(io.BytesIO(g))
    suma_antes = sum(max(20, f.info.get("duration", 100)) for f in
                     __import__("PIL.ImageSequence", fromlist=["x"]).Iterator(antes))
    out = G.preparar_gif(g, modo, usar_pillow=True)
    assert G.es_gif(out) and len(out) <= G.TOPE_SUBIDA
    im = Image.open(io.BytesIO(out))
    assert im.n_frames > 1
    assert im.size[0] <= tamano[0] and im.size[1] <= tamano[1]
    if modo == G.RAZON_FOTO:
        assert im.size[0] == im.size[1]
    else:
        assert abs(im.size[0] / im.size[1] - 8 / 3) < 0.03
    suma_despues = sum(f.info.get("duration", 100) for f in
                       __import__("PIL.ImageSequence", fromlist=["x"]).Iterator(im))
    assert abs(suma_despues - suma_antes) <= 0.05 * suma_antes + 40, (suma_antes, suma_despues)


def test_reduccion_sin_pillow_escritor_propio(app):
    """El respaldo con Qt: el GIF que escribe se lee bien (con Pillow) y conserva los cuadros y colores."""
    g = gif_de_colores(300, 200, 6, 90)
    out = G.preparar_gif(g, G.RAZON_FOTO, tope=1000, usar_pillow=False) if False else None
    # tope pequeño para forzar la reducción de un GIF chico
    for tope in (len(g) - 1,):
        out = G.preparar_gif(g, G.RAZON_FOTO, tope=tope, usar_pillow=False)
        assert G.es_gif(out)
        im = Image.open(io.BytesIO(out))
        assert im.n_frames in (6, 3, 2) and im.size[0] == im.size[1]
        im.seek(0)
        c0 = im.convert("RGB").getpixel((im.size[0] - 10, im.size[1] // 2))
        assert max(abs(a - b) for a, b in zip(c0, COLORES[0])) < 30
        if im.n_frames > 1:
            im.seek(1)
            c1 = im.convert("RGB").getpixel((im.size[0] - 10, im.size[1] // 2))
            assert max(abs(a - b) for a, b in zip(c1, COLORES[1] if im.n_frames == 6 else COLORES[2])) < 30


def test_reduccion_sin_pillow_pesado(app):
    g = gif_pesado(700, 520, 10)
    assert len(g) > G.TOPE_SUBIDA
    t = time.time()
    out = G.preparar_gif(g, G.RAZON_FONDO, usar_pillow=False)
    assert len(out) <= G.TOPE_SUBIDA
    im = Image.open(io.BytesIO(out))
    assert im.n_frames > 1 and abs(im.size[0] / im.size[1] - 8 / 3) < 0.03
    assert time.time() - t < 90


def test_demasiado_pesado_avisa():
    g = gif_pesado(400, 400, 8)
    with pytest.raises(nube.ErrorNube) as e:
        G.preparar_gif(g, G.RAZON_FOTO, tope=2000)
    assert str(e.value) == "Ese GIF pesa demasiado. Prueba con uno más corto"
    with pytest.raises(nube.ErrorNube):
        G.preparar_gif(b"no soy un gif", G.RAZON_FOTO)


# ------------------------------------------------------------------ editor: permiso y subida
def _editor(app, puede, tmp_path):
    from descargador.ui.paginas.perfil_editar import DialogoEditarPerfil
    ses = SesionFalsa({"puede_poner_fondo": puede})
    ctx = CtxFalso(ses)
    perfil = S.perfil_limpio({"id": "yo-id", "usuario": "ana", "nombre": "Ana", "foto_url": None,
                              "color_perfil": "#FF5C8A", "perfil_publico": True})
    d = DialogoEditarPerfil(ctx, S.Social(ses), perfil)
    d.show()
    esperar(app, lambda: ("puede_poner_fondo", {}) in ses.llamadas, "preguntar el permiso")
    for _ in range(20):
        app.processEvents()
        time.sleep(0.01)
    return d, ses


def _elegir(monkeypatch, ruta):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (ruta, "")))


def test_sin_permiso_mensaje_y_primer_cuadro(app, tmp_path, monkeypatch):
    d, ses = _editor(app, False, tmp_path)
    assert not d.bt_gif_foto.isVisible() and not d.bt_gif_banner.isVisible()
    f = tmp_path / "anim.gif"
    f.write_bytes(gif_de_colores(200, 200))
    _elegir(monkeypatch, str(f))
    d._elegir_foto()
    assert "exclusivos de los donadores de Caudal" in d.estado.text()
    assert d.foto_gif is None and d.foto_ruta == str(f) and d.av.gif is None and d.av.pm is not None
    d._elegir_banner()
    assert "exclusivos de los donadores" in d.estado.text() and d.banner_gif is None
    d.nombre.setText("Ana")
    d._guardar()
    esperar(app, lambda: ses.subidos, "la subida")
    esperar(app, lambda: len(ses.subidos) >= 2, "la subida del fondo")
    assert [s[2] for s in ses.subidos] == ["image/jpeg", "image/jpeg"]       # como hoy, JPEG con el primer cuadro
    assert [s[1].rsplit("/", 1)[1] for s in ses.subidos] == ["avatar.jpg", "banner.jpg"]


def test_con_permiso_conserva_la_animacion(app, tmp_path, monkeypatch):
    d, ses = _editor(app, True, tmp_path)
    assert d.bt_gif_foto.isVisible() and d.bt_gif_banner.isVisible()
    f = tmp_path / "anim.gif"
    f.write_bytes(gif_de_colores(200, 200))
    _elegir(monkeypatch, str(f))
    d._elegir_foto()
    esperar(app, lambda: d.foto_gif is not None, "preparar el GIF")
    assert d.av.gif is not None and d.av.gif.animado and d.foto_ruta is None
    d._elegir_banner()
    esperar(app, lambda: d.banner_gif is not None, "preparar el GIF de fondo")
    d.nombre.setText("Ana")
    d._guardar()
    esperar(app, lambda: len(ses.subidos) >= 2, "las subidas")
    assert ses.subidos[0][1] == "yo-id/avatar.gif" and ses.subidos[0][2] == "image/gif"
    assert ses.subidos[1][1] == "yo-id/banner.gif" and ses.subidos[1][2] == "image/gif"
    patch = [x for x in ses.llamadas if isinstance(x, tuple) and x[0] == "PATCH" and "perfiles" in x[1]]
    cuerpo = patch[-1][2]["json"]
    assert cuerpo["foto_url"].endswith(".gif") and cuerpo["banner_url"].endswith(".gif")


def test_boton_con_insignia(app, tmp_path):
    d, _ses = _editor(app, True, tmp_path)
    d.resize(640, 740)
    app.processEvents()
    d.grab().save(os.path.join(CAPTURAS, "editor_botones.png"))
    assert "GIF" in d.bt_gif_foto.toolTip() or "donadores" in d.bt_gif_foto.toolTip()


# ------------------------------------------------------------------ buscador (cliente falso)
class ClienteFalso:
    def __init__(self, paginas=None, error=None, aviso=""):
        self.paginas = paginas or []
        self.error = error
        self.aviso = aviso
        self.consultas = []
        self.vistas = []
        self.bajadas = []

    def buscar(self, q="", pos=""):
        self.consultas.append((q, pos))
        if self.error:
            return {"items": [], "siguiente": "", "error": self.error, "aviso": ""}
        if q == "nada":
            return {"items": [], "siguiente": "", "aviso": self.aviso, "error": ""}
        n = int(pos or 0)
        lote = self.paginas[n] if n < len(self.paginas) else []
        sig = str(n + 1) if n + 1 < len(self.paginas) else ""
        return {"items": lote, "siguiente": sig, "aviso": self.aviso, "error": ""}

    def vista(self, url):
        self.vistas.append(url)
        return gif_de_colores(90, 90, 3, 100)

    def bajar(self, url):
        self.bajadas.append(url)
        return gif_de_colores(240, 240, 4, 100)


def _items(n, desde=0):
    return [{"id": str(desde + i), "titulo": f"GIF {desde + i}", "vista": f"https://x/v{desde + i}.gif",
             "gif": f"https://x/g{desde + i}.gif", "ancho": 240, "alto": 240, "peso": 1000} for i in range(n)]


def _dialogo(app, cliente, modo=G.RAZON_FOTO, ancho=1100, alto=700):
    from descargador.ui.paginas.perfil_gif import DialogoBuscarGif
    d = DialogoBuscarGif(CtxFalso(SesionFalsa()), modo, None, cliente=cliente)
    d.resize(ancho, alto)
    d.show()
    return d


def test_buscador_rejilla_animada_y_captura(app):
    cli = ClienteFalso([_items(12), _items(12, 12), _items(6, 24)])
    d = _dialogo(app, cli)
    esperar(app, lambda: len(d._vistas) == 12, "los GIF del momento")
    assert cli.consultas[0] == ("", "")                       # sin texto: los del momento
    esperar(app, lambda: any(v.gif is not None for v in d._vistas), "las vistas")
    esperar(app, lambda: sum(v.gif is not None for v in d._vistas) >= 6, "más vistas")
    assert d.columnas == 4                                   # 1100 px: cuatro columnas
    # solo se animan unas pocas a la vez
    esperar(app, lambda: any(v.gif is not None and v.gif.corriendo for v in d._vistas), "alguna animándose")
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    corriendo = sum(1 for v in d._vistas if v.gif is not None and v.gif.corriendo)
    assert 1 <= corriendo <= 6
    d.grab().save(os.path.join(CAPTURAS, "buscador_1100x700.png"))
    # el cuadro de una vista cambia con el tiempo
    vis = next(v for v in d._vistas if v.gif is not None and v.gif.corriendo)
    a = vis.grab().toImage()
    esperar(app, lambda: vis.grab().toImage() != a, "que el cuadro cambie", 5)
    d.close()


def test_buscador_paginacion_y_carga_perezosa(app):
    cli = ClienteFalso([_items(24), _items(12, 24), _items(6, 36)])
    d = _dialogo(app, cli, ancho=700, alto=600)
    esperar(app, lambda: len(d._vistas) == 24, "primera página")
    assert d.columnas == 3
    esperar(app, lambda: len(cli.vistas) >= 3, "descargar las vistas visibles")
    time.sleep(0.2)
    app.processEvents()
    assert len(cli.vistas) < 24                              # las de abajo aún no se pidieron (perezosa)
    b = d.area.verticalScrollBar()
    b.setValue(b.maximum())
    esperar(app, lambda: len(d._vistas) == 36, "la segunda página al llegar abajo")
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    b.setValue(b.maximum())
    esperar(app, lambda: len(d._vistas) == 42, "la tercera página")
    assert [c[1] for c in cli.consultas] == ["", "1", "2"]
    d.close()


def test_buscador_texto_con_retraso_y_vacio(app):
    cli = ClienteFalso([_items(4)])
    d = _dialogo(app, cli, ancho=700, alto=620)
    esperar(app, lambda: len(d._vistas) == 4, "inicio")
    n = len(cli.consultas)
    d.campo.setText("nada")
    d.campo.textEdited.emit("nada")
    time.sleep(0.1)
    app.processEvents()
    assert len(cli.consultas) == n                          # aún dentro del retraso de 350 ms
    esperar(app, lambda: ("nada", "") in cli.consultas, "la búsqueda con retraso")
    esperar(app, lambda: d.paginas.currentIndex() == 1, "estado vacío")
    assert "No encontramos GIF para «nada»" in d.vacio_texto.text()
    d.grab().save(os.path.join(CAPTURAS, "buscador_vacio.png"))
    d.close()


def test_buscador_aviso_nunca_se_ignora(app):
    cli = ClienteFalso([_items(4)], aviso="Mostrando solo contenido apto para todo público")
    d = _dialogo(app, cli, ancho=700, alto=620)
    esperar(app, lambda: len(d._vistas) == 4, "inicio")
    assert "contenido apto" in d.estado.text()
    d.grab().save(os.path.join(CAPTURAS, "buscador_aviso.png"))
    d.close()


def test_buscador_sin_clave(app):
    d = _dialogo(app, ClienteFalso(error="sin_clave"), ancho=700, alto=620)
    esperar(app, lambda: d.paginas.currentIndex() == 1, "mensaje de búsqueda no activada")
    assert d.vacio_texto.text() == ("La búsqueda de GIF llegará muy pronto. "
                                    "Mientras, puedes subir un GIF desde tu equipo.")
    d.grab().save(os.path.join(CAPTURAS, "buscador_sin_clave.png"))
    d.close()


@pytest.mark.parametrize("modo", [G.RAZON_FOTO, G.RAZON_FONDO])
def test_buscador_elegir_previa_y_usar(app, modo):
    cli = ClienteFalso([_items(8)])
    d = _dialogo(app, cli, modo, 760, 680)
    esperar(app, lambda: len(d._vistas) == 8, "inicio")
    d._elegir(d._vistas[2].item)
    assert d.paginas.currentIndex() == 2
    esperar(app, lambda: d.bt_usar.isEnabled(), "descargar el elegido")
    assert cli.bajadas == ["https://x/g2.gif"]               # solo se baja el campo gif, por el servicio
    for _ in range(10):
        app.processEvents()
        time.sleep(0.02)
    d.grab().save(os.path.join(CAPTURAS, f"previa_{modo}.png"))
    d._elegir_otro()
    assert d.paginas.currentIndex() == 0
    d._elegir(d._vistas[2].item)
    esperar(app, lambda: d.bt_usar.isEnabled(), "descargar otra vez")
    d._usar()
    assert d.result() == QDialog.Accepted and G.es_gif(d.datos)


def test_editor_usa_gif_del_buscador(app, tmp_path, monkeypatch):
    from descargador.ui.paginas import perfil_gif
    d, ses = _editor(app, True, tmp_path)
    d.cliente_gifs = ClienteFalso([_items(3)])
    monkeypatch.setattr(perfil_gif.DialogoBuscarGif, "exec", lambda self: (self._elegir(self._vistas[0].item)
                                                                         if self._vistas else None) or None)

    def exec_falso(self):
        esperar(app, lambda: len(self._vistas) == 3, "vistas")
        self._elegir(self._vistas[1].item)
        esperar(app, lambda: self.bt_usar.isEnabled(), "descarga")
        self._usar()
        return QDialog.Accepted
    monkeypatch.setattr(perfil_gif.DialogoBuscarGif, "exec", exec_falso)
    d._buscar_gif(G.RAZON_FOTO)
    esperar(app, lambda: d.foto_gif is not None, "preparar el GIF del buscador")
    assert d.av.gif is not None


# ------------------------------------------------------------------ mostrarlos animados
def _distintos(app, widget, veces=40):
    base = widget.grab().toImage()
    for _ in range(veces):
        app.processEvents()
        time.sleep(0.03)
        if widget.grab().toImage() != base:
            return True
    return False


def test_avatar_se_anima(app):
    from descargador.ui.paginas import perfil_comun as PC
    av = PC.Avatar(150, "Ana", None, None, anillo="#222222", animar=True)
    av.poner_gif(gif_de_colores(160, 160, 4, 100))
    av.show()
    a = av.grab().toImage()
    assert _distintos(app, av), "el cuadro del avatar no cambió"
    av.grab().save(os.path.join(CAPTURAS, "avatar_animado.png"))
    # redondo: la esquina queda transparente/sin foto
    assert a.pixelColor(2, 2) != a.pixelColor(75, 75)
    # al ocultarse se detiene
    av.hide()
    app.processEvents()
    assert not av.gif.corriendo
    av.show()
    app.processEvents()
    assert av.gif.corriendo
    av.close()


def test_pausa_al_minimizar(app):
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    from descargador.ui.paginas import perfil_comun as PC
    ventana = QWidget()
    ly = QVBoxLayout(ventana)
    av = PC.Avatar(100, "Ana", None, None, animar=True)
    ly.addWidget(av)
    av.poner_gif(gif_de_colores(100, 100, 4, 100))
    ventana.show()
    app.processEvents()
    assert av.gif.corriendo
    ventana.showMinimized()
    for _ in range(5):
        app.processEvents()
    if ventana.isMinimized():                                 # el modo offscreen puede no minimizar
        assert not av.gif.corriendo
        ventana.showNormal()
        for _ in range(5):
            app.processEvents()
        assert av.gif.corriendo
    ventana.close()


def test_fondo_se_anima_y_url_gif(app, monkeypatch):
    from descargador.ui import imagenes
    from descargador.ui.paginas import perfil_comun as PC
    g = gif_de_colores(320, 120, 4, 100)
    monkeypatch.setattr(imagenes, "_leer", lambda url: g)
    f = PC.FondoPerfil(120, 14, False, 0.3, "#FF5C8A", "u2/banner.gif", animar=True)
    f.setFixedWidth(480)
    f.show()
    esperar(app, lambda: f.gif is not None, "bajar el GIF del fondo")
    assert _distintos(app, f), "el fondo no se animó"
    f.grab().save(os.path.join(CAPTURAS, "fondo_animado.png"))
    # en el directorio (animar=False) se queda el primer cuadro, sin QMovie
    quieto = PC.FondoPerfil(84, 15, True, 0.5, "#FF5C8A", "u2/banner.gif")
    quieto.show()
    esperar(app, lambda: quieto.img is not None, "primer cuadro")
    assert quieto.gif is None
    f.close()
    quieto.close()


def test_avatar_url_gif_animar_o_primer_cuadro(app, monkeypatch):
    from descargador.ui import imagenes
    from descargador.ui.paginas import perfil_comun as PC
    g = gif_de_colores(150, 150, 4, 100)
    monkeypatch.setattr(imagenes, "_leer", lambda url: g)
    animado = PC.Avatar(100, "Ana", None, "u2/avatar.gif", animar=True)
    animado.show()
    esperar(app, lambda: animado.gif is not None, "avatar animado")
    pequeno = PC.Avatar(40, "Ana", None, "u2/avatar.gif")        # lista / tarjeta pequeña
    pequeno.show()
    esperar(app, lambda: pequeno.pm is not None, "primer cuadro")
    assert pequeno.gif is None
    # la caché de pixmaps guarda el primer cuadro del GIF, no una animación
    assert isinstance(pequeno.pm, type(animado.grab()))
    animado.close()
    pequeno.close()


def test_perfil_ajeno_anima_foto_y_fondo(app, monkeypatch):
    """La página de perfil crea el avatar y el fondo con animación."""
    from descargador.ui import imagenes
    from descargador.ui.paginas.perfil import PaginaPerfil
    g = gif_de_colores(200, 200, 4, 100)
    monkeypatch.setattr(imagenes, "_leer", lambda url: g)
    from test_social import PERFIL
    ses = SesionFalsa({"ver_perfil": lambda p: dict(PERFIL, foto_url="u2/avatar.gif",
                                                    banner_url="u2/banner.gif")})
    ctx = CtxFalso(ses)
    pag = PaginaPerfil(ctx, "bea")
    pag.resize(1100, 700)
    pag.show()
    esperar(app, lambda: pag.p is not None, "el perfil")
    from descargador.ui.paginas.perfil_comun import Avatar
    av = [a for a in pag.findChildren(Avatar) if a.lado == 148][0]
    esperar(app, lambda: av.gif is not None, "el avatar animado")
    esperar(app, lambda: pag.fondo.gif is not None, "el fondo animado")
    pag.grab().save(os.path.join(CAPTURAS, "perfil_animado.png"))
    pag.close()

