# -*- coding: utf-8 -*-
"""Estilo y tipo de letra de la letra de las canciones (ajustes «estilo_letra» y «fuente_letra»)."""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
import shiboken6  # noqa: E402
from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtGui import QFont, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from descargador.config import DEFECTOS  # noqa: E402
from descargador.ui import estilo_letra as E  # noqa: E402
from descargador.ui import selector_letra as S  # noqa: E402
from descargador.ui import tipografia_letra as T  # noqa: E402
from descargador.ui.escena import letra as L  # noqa: E402

LINEAS = [
    {"ms": 0, "texto": "cuando la noche cae", "pausa": False, "canto": 1500},
    {"ms": 2000, "texto": "sobre la ciudad entera", "pausa": False, "canto": 1500},
    {"ms": 4000, "texto": "y las luces se encienden", "pausa": False},
]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _restaurar():
    yield
    L.fijar_estilo_letra("clasica")
    T.fijar("predeterminada")


def _letra(estilo):
    w = L.LetraCinetica()
    w.resize(640, 420)
    w.poner_estilo(estilo)
    w.poner_lineas(LINEAS, True)
    w.fijar_traducciones(["when night falls", None, "and the lights"])
    w._sincronizada = True
    w.fijar_ms(2600)               # línea 2: su línea anterior se va, la siguiente se ve abajo
    w._entradas = {k: time.monotonic() - 10.0 for k in w._entradas}   # palabras ya asentadas
    return w


def _render(w):
    img = QImage(w.width(), w.height(), QImage.Format_ARGB32_Premultiplied)
    img.fill(0)
    w.render(img)
    return img


def _pintados(img):
    return sum(1 for y in range(0, img.height(), 2) for x in range(0, img.width(), 2)
               if img.pixelColor(x, y).alpha() > 0)


def test_ajustes_por_defecto():
    assert DEFECTOS["estilo_letra"] == "clasica"
    assert DEFECTOS["fuente_letra"] == "predeterminada"
    assert L.ESTILOS_LETRA == ("clasica", "nitida", "neon", "simple", "degradado", "contorno", "relieve",
                               "marcador", "oro", "vhs")
    assert tuple(T.FUENTES) == (
        "predeterminada", "poppins", "bebas", "anton", "pacifico", "lobster", "righteous", "serif", "bangers",
        "lilita", "titan", "bungee", "russo", "audiowide", "monoton", "abril", "shrikhand", "staatliches",
        "marker", "kaushan", "vibes", "elite", "pixel", "limelight", "caveat", "ops", "courgette")
    assert L.normalizar_estilo("raro") == "clasica"
    assert L.LetraCinetica.__init__ and L.estilo_letra() in L.ESTILOS_LETRA


@pytest.mark.parametrize("estilo", L.ESTILOS_LETRA)
def test_cada_estilo_pinta_sin_error(app, estilo):
    w = _letra(estilo)
    time.sleep(0.05)
    assert w.estilo() == estilo
    assert _pintados(_render(w)) > 200


def test_los_estilos_se_ven_distintos(app):
    imagenes = {e: _render(_letra(e)) for e in L.ESTILOS_LETRA}
    assert imagenes["clasica"] != imagenes["nitida"]
    assert imagenes["clasica"] != imagenes["neon"]
    assert imagenes["clasica"] != imagenes["simple"]
    claves = list(imagenes)
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            assert imagenes[a] != imagenes[b], (a, b)


def test_cambio_de_estilo_en_vivo(app):
    w = _letra("clasica")
    L.fijar_estilo_letra("neon")
    assert w.estilo() == "neon"
    L.fijar_estilo_letra("no-existe")
    assert w.estilo() == "clasica"
    shiboken6.delete(w)
    L.fijar_estilo_letra("simple")          # una letra ya destruida no rompe nada


def test_todas_las_fuentes_cargan(app):
    for clave in T.FUENTES:
        if clave == "predeterminada":
            assert T.familia(clave) is None
        else:
            assert T.familia(clave), clave
    base = QFont("Segoe UI")
    base.setPixelSize(30)
    f = T.adaptar(base, "bebas")
    assert f.family() == T.familia("bebas") and f.pixelSize() == 30 and not f.italic()
    assert T.adaptar(base, "predeterminada") is base
    assert T.normalizar("raro") == "predeterminada"


def test_fuente_que_no_carga_usa_la_predeterminada(app, monkeypatch, tmp_path):
    monkeypatch.setattr(T, "carpeta_fuentes", lambda: tmp_path)
    monkeypatch.setitem(T.FUENTES, "falsa", ("Falsa", ("NoExiste.ttf",), QFont.Normal))
    base = QFont("Segoe UI")
    assert T.familia("falsa") is None
    assert T.adaptar(base, "falsa") is base
    T._familias.pop("falsa", None)


@pytest.mark.parametrize("clave", list(T.FUENTES))
def test_cada_fuente_pinta_la_escena_y_la_letra_viva(app, clave):
    w = _letra("clasica")
    T.fijar(clave)
    assert _pintados(_render(w)) > 200
    # la letra viva usa la fuente elegida al medir
    from descargador.ui.letra_viva import LienzoLetra
    f, _ft = LienzoLetra._fuentes(_FakeLienzo())
    fam = T.familia(clave)
    assert f.family() == (fam or "Segoe UI")


class _FakeLienzo:
    compacto = False

    def _tam(self):
        return 30

    def width(self):
        return 800


def test_aviso_cierre_filtra_luajit():
    from descargador.aviso_errores import limpiar_cierre
    solo_luajit = ("Windows fatal exception: code 0xe24c4a02\n\nCurrent thread 0x1 (most recent call first):\n"
                   "  File \"a.py\", line 3 in f\n\n"
                   "Windows fatal exception: code 0xE24C4A02\n\nThread 0x2:\n  File \"b.py\", line 1 in g\n")
    assert limpiar_cierre(solo_luajit) == ""
    mezcla = solo_luajit + ("Windows fatal exception: access violation\n\nCurrent thread 0x3:\n"
                            "  File \"c.py\", line 9 in h\n")
    queda = limpiar_cierre(mezcla)
    assert queda.startswith("Windows fatal exception: access violation")
    assert "0xe24c4a02" not in queda.lower() and "c.py" in queda
    assert limpiar_cierre("Fatal Python error: Segmentation fault\n  File x") .startswith("Fatal Python error")


def test_aviso_cierre_no_envia_si_solo_hay_luajit(tmp_path, monkeypatch):
    from descargador import aviso_errores as A
    (tmp_path / "cierre_nativo.txt").write_text("Windows fatal exception: code 0xe24c4a02\n\nThread 0x1:\n",
                                                encoding="utf-8")
    monkeypatch.setattr(A, "_ruta", lambda n: str(tmp_path / n))
    monkeypatch.setattr(A, "_leer", lambda n, d: {"limpio": False})
    enviados = []
    monkeypatch.setattr(A, "encolar", lambda inf: enviados.append(inf))
    A._revisar_cierre_anterior()
    assert enviados == []
    (tmp_path / "cierre_nativo.txt").write_text("Windows fatal exception: access violation\n\nThread 0x1:\n",
                                                encoding="utf-8")
    A._revisar_cierre_anterior()
    assert len(enviados) == 1


def test_modo_gamer_ahorro_con_etiqueta_destruida(app):
    from descargador.ui.paginas.modo_gamer import PaginaModoGamer

    class _Falsa(QObject):
        pass

    falsa = _Falsa()
    falsa.et_ahorro = QLabel()
    shiboken6.delete(falsa.et_ahorro)
    PaginaModoGamer._refrescar_ahorro(falsa)      # antes: RuntimeError (QLabel ya destruido)


class _Aj(dict):
    guardados = 0

    def guardar(self):
        self.guardados += 1


class _CtxSel:
    def __init__(self):
        self.ajustes = _Aj(estilo_letra="clasica", fuente_letra="predeterminada")


def test_ajustes_abre_el_disenador_y_dice_lo_puesto(app, tmp_path):
    """La sección «Letra de las canciones» de Ajustes: vista previa, lo que está puesto y «Cambiar diseño»."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    from descargador.ui.paginas import ajustes as AJ

    class _Falsa(QWidget):
        _seccion_letra = AJ.PaginaAjustes._seccion_letra
        _abrir_diseno_letra = AJ.PaginaAjustes._abrir_diseno_letra
        _pintar_diseno_letra = AJ.PaginaAjustes._pintar_diseno_letra
        al_cambiar_tipografia = AJ.PaginaAjustes.al_cambiar_tipografia
        al_cambiar_estilo_letra = AJ.PaginaAjustes.al_cambiar_estilo_letra
        _conectar = AJ.PaginaAjustes._conectar
        _poner = AJ.PaginaAjustes._poner

    pag = _Falsa()
    pag.ctx = _CtxSel()
    pag.a = pag.ctx.ajustes
    pag.a["estilo_letra"] = "oro"               # lo guardado manda al abrir la página
    pag.cuerpo = QVBoxLayout(pag)
    pag._seccion_letra()
    assert E.actual() == "oro" and pag.et_diseno_letra.text() == "Predeterminada · Oro"
    w = _letra("oro")
    d = pag._abrir_diseno_letra()
    assert d.isVisible() and d is S.dialogo_abierto()
    d.selector.muestra_estilo("neon").click()
    assert pag.a["estilo_letra"] == "neon" and w.estilo() == "neon"
    d.selector.muestra_fuente("lobster").click()
    assert pag.a["fuente_letra"] == "lobster" and T.actual() == "lobster"
    assert pag.et_diseno_letra.text() == "Lobster · Neón"
    antes = _render(pag.vista_letra)
    d.selector.muestra_fuente("pixel").click()
    assert _render(pag.vista_letra) != antes       # la vista previa va detrás
    assert pag._abrir_diseno_letra() is d          # no se abre dos veces
    d.close()
    app.processEvents()
    assert S.dialogo_abierto() is None


# ------------------------------------------------------------------ fuentes

TILDES = "áéíóúüñÁÉÍÓÚÜÑ¿¡"


@pytest.mark.parametrize("clave", [k for k in T.FUENTES if k != "predeterminada"])
def test_las_tildes_no_salen_como_cuadros(app, clave):
    from PySide6.QtGui import QRawFont
    for archivo in T.FUENTES[clave][1]:
        cruda = QRawFont(str(T.carpeta_fuentes() / archivo), 40)
        assert cruda.isValid(), archivo
        faltan = [c for c in TILDES if not cruda.supportsCharacter(ord(c))]
        assert not faltan, (clave, faltan)
    # y al pintarlas se usa esa fuente, no una de repuesto
    f = T.adaptar(QFont("Segoe UI", 20), clave)
    from PySide6.QtGui import QFontInfo
    assert QFontInfo(f).family() == T.familia(clave)


def test_cada_fuente_se_ve_distinta(app):
    vistas = {}
    for clave in T.FUENTES:
        T.fijar(clave)
        vistas[clave] = _render(_letra("simple"))
    claves = list(vistas)
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            assert vistas[a] != vistas[b], (a, b)


def test_tamano_relativo_ninguna_diminuta_ni_desbordada(app):
    """Todas las fuentes ocupan un ancho parecido (a la misma medida pedida) y la letra no se sale."""
    from PySide6.QtGui import QFontMetricsF
    base = QFont("Segoe UI")
    base.setPixelSize(40)
    anchos = {k: QFontMetricsF(T.adaptar(base, k)).horizontalAdvance("Cuando la noche cae") for k in T.FUENTES}
    medio = sorted(anchos.values())[len(anchos) // 2]
    for k, w in anchos.items():
        assert 0.62 * medio < w < 1.5 * medio, (k, w, medio)
    f = T.adaptar(base, "pixel")
    assert f.pixelSize() == round(40 * T.FACTORES["pixel"])
    for clave in T.FUENTES:                  # la tinta no toca el borde de la pieza en la escena
        T.fijar(clave)
        img = _render(_letra("simple"))
        w, h = img.width(), img.height()
        assert not any(img.pixelColor(x, y).alpha() for y in range(0, h, 2) for x in (0, 1, w - 2, w - 1)), clave


def test_las_fuentes_van_dentro_del_exe():
    import pathlib
    raiz = pathlib.Path(__file__).resolve().parent.parent
    spec = (raiz / "Caudal Escritorio.spec").read_text(encoding="utf-8")
    assert "('descargador/fuentes_letra', 'descargador/fuentes_letra')" in spec
    for _clave, (_n, archivos, _p) in T.FUENTES.items():
        for a in archivos:
            assert (T.carpeta_fuentes() / a).exists(), a


# ------------------------------------------------------------------ estilos en la canción y el karaoke

LRC = [(0, "cuando la noche cae"), (4000, "¿dónde está mi corazón, niña?"), (9000, "y las luces se encienden")]


def _lienzo(app, monkeypatch, clase=None, **kw):
    from descargador import catalogo
    from descargador.ui import imagenes, letra_viva as V
    from PySide6.QtCore import Signal

    class _R(QObject):
        pista_cambio = Signal(object)
        posicion_cambio = Signal(float)
        estado_cambio = Signal(str)

        def __init__(self):
            super().__init__()
            self.actual = {"clave": "kk", "video_id": "kk", "titulo": "T", "artista": "A", "miniatura": ""}
            self.estado = "pausa"
            self._posicion = 5.0

    class _Ctx:
        def __init__(self):
            self.reproductor = _R()
            self.ajustes = _Aj(traducir_letra=False, letra_sincronia_auto=False)

        def avisar(self, *_a):
            pass

    datos = {"sincronizada": True, "lineas": LRC, "texto": "", "fuente": "LRCLIB"}
    monkeypatch.setattr(catalogo, "letras", lambda p: datos)
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: None)
    V.CACHE_LETRAS.clear()
    V.CACHE_LETRAS["kk"] = datos
    lz = V.LienzoLetra(_Ctx(), **kw)
    lz.resize(700, 420)
    lz._t0 = time.monotonic()
    lz.show()
    for _ in range(400):
        app.processEvents()
        time.sleep(0.004)
        if lz._items and lz._actual == 1 and lz._items[1]["foco"] > 0.99 and not lz._moviendo:
            break
    assert lz._actual == 1
    lz.reloj.stop()
    lz._cuadro = lambda: None
    lz._fondo = lambda: QImage(8, 8, QImage.Format_ARGB32_Premultiplied)     # fondo quieto: solo se compara la letra
    return lz


@pytest.mark.parametrize("compacto", [False, True])
def test_los_estilos_se_ven_en_la_letra_de_la_cancion(app, monkeypatch, compacto):
    lz = _lienzo(app, monkeypatch, compacto=compacto)
    negro = QImage(8, 8, QImage.Format_RGB32)
    negro.fill(0)
    lz._fondo = lambda: negro
    vistas = {}
    for e in L.ESTILOS_LETRA:
        L.fijar_estilo_letra(e)
        lz.reloj.stop()
        vistas[e] = _render(lz)
        assert len(lz._capas) == 0 if e == "clasica" else len(lz._capas) > 0
    claves = list(vistas)
    for i, a in enumerate(claves):
        for b in claves[i + 1:]:
            assert vistas[a] != vistas[b], (a, b)
    # y volver a la clásica deja exactamente lo de antes
    L.fijar_estilo_letra("clasica")
    assert _render(lz) == vistas["clasica"]
    lz.hide()
    lz.deleteLater()


def test_la_clasica_se_pinta_como_siempre(app, monkeypatch):
    """Con «clasica» el camino es el de siempre: texto con su pluma y el halo, sin imágenes de estilos."""
    from descargador.ui import letra_viva as V
    lz = _lienzo(app, monkeypatch)
    usados = []
    monkeypatch.setattr(V.LienzoLetra, "_pintar_con_diseno", lambda *a, **k: usados.append(1))
    halos = []
    real = V.LienzoLetra._pintar_brillo
    monkeypatch.setattr(V.LienzoLetra, "_pintar_brillo", lambda self, *a: (halos.append(1), real(self, *a)))
    _render(lz)
    assert not usados and halos
    L.fijar_estilo_letra("oro")
    halos.clear()
    _render(lz)
    assert usados and not halos
    lz.hide()
    lz.deleteLater()


def test_las_filas_se_pintan_una_vez_y_se_guardan(app, monkeypatch):
    lz = _lienzo(app, monkeypatch)
    L.fijar_estilo_letra("relieve")
    _render(lz)
    creadas = []
    real = E.imagen_capa
    monkeypatch.setattr(E, "imagen_capa", lambda *a, **k: (creadas.append(1), real(*a, **k))[1])
    for _ in range(5):
        _render(lz)
    assert creadas == []                          # nada se vuelve a trazar por cuadro
    T.fijar("lilita")                             # otra fuente: se rehacen
    for _ in range(3):
        _render(lz)
    assert creadas
    lz.hide()
    lz.deleteLater()


def test_los_colores_de_la_caratula_se_asientan_antes_de_repintar(app, monkeypatch):
    from PySide6.QtGui import QColor
    lz = _lienzo(app, monkeypatch)
    L.fijar_estilo_letra("degradado")
    _render(lz)
    antes = lz._col_letra
    for i in range(6):                            # la transición de la paleta: un color por cuadro
        lz.paleta = [QColor(40 * i, 200, 90), QColor("#FF8800"), QColor("#0088FF")]
        lz._colores_letra()
    assert lz._col_letra is antes
    lz._col_desde -= 1.0
    assert lz._colores_letra() is not antes[1]
    lz.hide()
    lz.deleteLater()


def test_cache_de_capas_no_crece_sin_fin():
    c = E.CacheCapas(tope=4 * 100 * 100 * 3)
    for i in range(10):
        c.pedir(i, lambda: (QImage(100, 100, QImage.Format_ARGB32_Premultiplied), None))
    assert len(c) == 3 and 9 in c and 0 not in c


def test_los_colores_siempre_se_leen():
    from PySide6.QtGui import QColor
    for base in ("#000000", "#101060", "#0000FF", "#7A0000", "#FFFFFF", "#333333", "#2E7D32"):
        col = E.Colores(base, base, base)
        for c in (col.a, col.b, col.c):
            assert E.luminancia(c) >= 0.33, base
        # el texto oscuro del marcador sobre su pastilla: contraste de sobra
        pastilla = E.aclarar(col.a, 0.48)
        assert (E.luminancia(pastilla) + 0.05) / (E.luminancia(E.TINTA_MARCADOR) + 0.05) > 7
    assert E.Colores("#E8577E", "#E8577E", "#E8577E").a != E.Colores("#E8577E", "#E8577E", "#E8577E").b
    assert E.aclarar(QColor("#FFFFFF")).name() == "#ffffff"


# ------------------------------------------------------------------ escena: estilos con movimiento

def test_contorno_ensena_hueco_lo_que_viene_y_lo_rellena(app):
    w = _letra("contorno")
    w.fijar_ms(2000)                              # solo entró la primera palabra
    w._t_linea = time.monotonic() - 5
    hueca = _pintados(_render(w))
    assert len(w._entradas) == 1
    assert hueca > 1500                           # también se ven (huecas) las que faltan
    t0 = time.monotonic()
    w._entradas = {0: t0}
    assert w._animando(t0)                        # mientras se rellena, hay que repintar
    w._entradas = {0: t0 - 5}
    w._t_linea = t0 - 5
    w._prev = None
    assert not w._animando(t0)


def test_marcador_no_tapa_las_demas_palabras(app):
    w = _letra("marcador")
    entero = _render(w)
    w._entradas = {k: time.monotonic() - 10.0 for k in w._entradas}
    u, r = w._resaltador(w._disposicion(w._indice).items[0], 10.0)
    assert u == 1.0 and r.width() > 20 and not entero.isNull()


@pytest.mark.parametrize("estilo", E.ESTILOS_CAPAS)
def test_cada_estilo_con_cada_fuente_pinta_a_media_entrada(app, estilo):
    for clave in T.FUENTES:
        T.fijar(clave)
        w = _letra(estilo)
        ahora = time.monotonic()
        w._entradas = {k: ahora - 0.1 for k in w._entradas}
        assert _pintados(_render(w)) > 150, clave
        w.deleteLater()


# ------------------------------------------------------------------ selector

def test_el_selector_guarda_marca_y_cambia_en_vivo(app):
    ctx = _CtxSel()
    sel = S.SelectorLetra(ctx)
    sel.resize(700, 600)
    sel.show()
    app.processEvents()
    assert [m.clave for m in sel.estilos.muestras] == list(L.ESTILOS_LETRA)
    assert [m.clave for m in sel.fuentes.muestras] == list(T.FUENTES)
    assert sel.muestra_estilo("clasica").isChecked() and sel.muestra_fuente("predeterminada").isChecked()
    w = _letra("clasica")
    for e in L.ESTILOS_LETRA:
        sel.muestra_estilo(e).click()
        assert ctx.ajustes["estilo_letra"] == e == E.actual() == w.estilo()
        assert sel.muestra_estilo(e).isChecked()
    for k in T.FUENTES:
        sel.muestra_fuente(k).click()
        assert ctx.ajustes["fuente_letra"] == k == T.actual()
    assert ctx.ajustes.guardados == len(L.ESTILOS_LETRA) + len(T.FUENTES)
    # si se cambia desde otro sitio, el selector lo marca
    L.fijar_estilo_letra("vhs")
    T.fijar("bungee")
    assert sel.muestra_estilo("vhs").isChecked() and sel.muestra_fuente("bungee").isChecked()
    sel.restablecer()
    assert ctx.ajustes["estilo_letra"] == "clasica" and ctx.ajustes["fuente_letra"] == "predeterminada"
    assert sel.muestra_estilo("clasica").isChecked()
    sel.deleteLater()


def test_las_muestras_son_de_verdad(app):
    """Cada estilo se ve distinto en su muestra y cada fuente está escrita en la suya."""
    ctx = _CtxSel()
    sel = S.SelectorLetra(ctx)
    sel.resize(700, 600)
    sel.show()
    app.processEvents()

    def zona(m):
        img = QImage(m.width(), m.height(), QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        m.render(img)
        z = m.zona().toRect()
        return img.copy(z.adjusted(0, 0, -30, 0))

    for muestras in (sel.estilos.muestras, sel.fuentes.muestras):
        vistas = [zona(m) for m in muestras]
        for i, a in enumerate(vistas):
            for j in range(i + 1, len(vistas)):
                assert a != vistas[j], (muestras[i].clave, muestras[j].clave)
    # la muestra del estilo usa la tipografía puesta
    m = sel.muestra_estilo("oro")
    antes = zona(m)
    T.fijar("pacifico")
    assert zona(m) != antes
    # ninguna muestra se desborda de su tarjeta, ni con la ventana estrecha
    for ancho in (380, 700, 1100):
        sel.resize(ancho, 600)
        app.processEvents()
        for m in sel.estilos.muestras + sel.fuentes.muestras:
            assert m.geometry().right() <= m.parentWidget().width(), (ancho, m.clave)
            assert m.width() >= 90
    for clave in T.FUENTES:
        f = S.fuente_que_cabe(clave, T.nombre(clave), 120, 40, 30)
        from PySide6.QtGui import QFontMetricsF
        assert QFontMetricsF(f).horizontalAdvance(T.nombre(clave)) <= 121 and f.pixelSize() >= 5
    sel.deleteLater()


def test_dialogo_se_cierra_con_esc_y_sobrevive_a_su_ventana(app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWidget
    ctx = _CtxSel()
    padre = QWidget()
    padre.show()
    d = S.abrir_selector(ctx, padre, sin_marco=True)
    assert d.parentWidget() is padre and d.isWindow() and not d.isModal()
    QTest.keyClick(d, Qt.Key_Escape)
    app.processEvents()
    assert S.dialogo_abierto() is None
    d = S.abrir_selector(ctx, padre)
    shiboken6.delete(padre)                       # se cerró la ventana de debajo
    assert S.dialogo_abierto() is None
    L.fijar_estilo_letra("oro")                   # y cambiar el estilo no toca nada destruido
    T.fijar("anton")
