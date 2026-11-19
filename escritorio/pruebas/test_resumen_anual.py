# -*- coding: utf-8 -*-
"""«Tu año en Caudal», el ánimo de las canciones y las tarjetas de letra exclusivas.

Lógica pura con datos inventados, más el dibujo real de las imágenes (Qt offscreen) y los cuadros con candado."""

import os
import sys
import time
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import premium as P  # noqa: E402
from descargador import recomendador as R  # noqa: E402
from descargador import resumen_anual as RA  # noqa: E402
from test_premium import CtxFalso, SesionFalsa, esperar  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    yield tmp_path


# ------------------------------------------------------------------ ánimo

@pytest.mark.parametrize("texto,esperado", [
    ("Sin ti - Llorando por dentro", "triste"),
    ("Adiós", "triste"),
    ("Without You", "triste"),
    ("Fiesta en la playa", "fiesta"),
    ("Dance the night away", "fiesta"),
    ("Eres mi amor", "romantica"),
    ("Corazón partío", "romantica"),
    ("Amor y lágrimas", "triste"),             # manda la tristeza
    ("Solomillo con papas", ""),               # «solo» dentro de otra palabra no cuenta
    ("Scrying session", ""),                  # «cry» pegado a letras por delante no cuenta
    ("Nada especial", ""),
    ("", ""),
    (None, ""),
])
def test_animo_por_palabras_con_limite_de_palabra(texto, esperado):
    assert R.animo_de(texto) == esperado


# ------------------------------------------------------------------ cálculo del año

def _e(clave, titulo, artista, fecha, dur=200, aid=""):
    pista = {"clave": clave, "titulo": titulo, "artista": artista, "duracion": dur,
             "artistas": [{"nombre": artista, "id": aid}], "miniatura": ""}
    return {"pista": pista, "fecha": fecha, "contexto": None}


def _historial():
    base = datetime(2026, 3, 1, 20, 0)
    h = []
    for i in range(6):                                    # 6 días seguidos con la misma canción triste
        h.append(_e("yt:a", "Lloro por ti", "Ana", base + timedelta(days=i), 240, "A1"))
    for i in range(3):
        h.append(_e("yt:b", "Fiesta total", "Beto", base + timedelta(days=10, minutes=i), 180, "B1"))
    h.append(_e("yt:c", "Cualquier cosa", "Ana", base + timedelta(days=20), 200, "A1"))
    h.append(_e("yt:d", "Del año pasado", "Zed", datetime(2025, 12, 31, 23, 0), 100, "Z"))     # otro año: no cuenta
    return h


def test_resumen_del_anio_con_datos_conocidos():
    r = RA.calcular(_historial(), 2026, ahora=datetime(2026, 11, 18))
    assert r["escuchas"] == 10 and r["canciones_distintas"] == 3 and r["artistas_distintos"] == 2
    assert r["minutos"] == round((6 * 240 + 3 * 180 + 200) / 60)
    assert r["artista_top"] == {"nombre": "Ana", "veces": 7}
    assert [a["nombre"] for a in r["top_artistas"]] == ["Ana", "Beto"]
    assert r["cancion_top"]["titulo"] == "Lloro por ti" and r["cancion_top"]["veces"] == 6
    assert r["racha"] == 6
    assert r["dia_top"]["escuchas"] == 3 and r["dia_top"]["texto"] == "11 de marzo"
    assert r["mes_top"]["nombre"] == "marzo"
    assert r["hay_datos"]


def test_el_animo_del_anio_es_el_que_mas_sono():
    r = RA.calcular(_historial(), 2026)
    assert r["animo"]["clave"] == "triste" and r["animo"]["nombre"] == "Melancólico"
    assert r["animo"]["porcentaje"] == round(100 * 6 / 9)


def test_poca_musica_no_inventa_resumen():
    r = RA.calcular(_historial()[:3], 2026)
    assert not r["hay_datos"] and r["animo"] is None          # con 3 escuchas el ánimo no se afirma
    vacio = RA.calcular([], 2026)
    assert vacio["escuchas"] == 0 and vacio["artista_top"] is None and vacio["cancion_top"] is None
    assert vacio["racha"] == 0 and vacio["minutos"] == 0


def test_mejor_racha():
    d = datetime(2026, 1, 1).date()
    assert RA.mejor_racha({d, d + timedelta(days=1), d + timedelta(days=2), d + timedelta(days=5)}) == 3
    assert RA.mejor_racha(set()) == 0 and RA.mejor_racha({d}) == 1


def test_texto_de_horas():
    assert RA.texto_horas(45) == "45 min" and RA.texto_horas(180) == "3 h" and RA.texto_horas(1234) == "20 h 34 min"


def test_leer_desde_la_coleccion_real(tmp_path):
    """El mismo cálculo, de punta a punta, sobre la base de datos de verdad (sin red)."""
    from descargador.coleccion import Coleccion
    col = Coleccion()
    ahora = datetime.now()
    for i in range(7):
        col.registrar_escucha({"clave": "yt:xyz", "video_id": "xyz", "titulo": "Lloro por ti", "artista": "Ana",
                               "artistas": [{"nombre": "Ana", "id": "A1"}], "duracion": 210})
    r = RA.leer(col, ahora.year, ahora)
    assert r["escuchas"] == 7 and r["hay_datos"] and r["cancion_top"]["titulo"] == "Lloro por ti"


# ------------------------------------------------------------------ imágenes

def _no_es_plana(img, paso=40):
    colores = {img.pixelColor(x, y).name() for x in range(0, img.width(), paso) for y in range(0, img.height(), paso)}
    return len(colores) > 10


def test_la_imagen_del_anio_es_vertical_1080x1920_y_trae_contenido(app):
    from descargador.ui import anio_caudal as AC
    r = RA.calcular(_historial(), 2026)
    img = AC.crear_imagen_anio(r, "ana")
    assert (img.width(), img.height()) == (1080, 1920) and _no_es_plana(img)
    # un resumen con pocos datos (sin ánimo ni artistas) tampoco rompe el dibujo
    vacio = AC.crear_imagen_anio(RA.calcular([], 2026), "")
    assert (vacio.width(), vacio.height()) == (1080, 1920)
    borrosa = AC.difuminar(img)
    assert (borrosa.width(), borrosa.height()) == (1080, 1920)
    # difuminar de verdad: ya no hay bordes duros entre píxeles vecinos
    saltos = lambda im: sum(abs(im.pixelColor(x, 900).red() - im.pixelColor(x + 1, 900).red()) for x in range(100, 700))  # noqa: E731
    assert saltos(borrosa) < saltos(img)


def _portada():
    img = QImage(400, 400, QImage.Format_RGB32)
    p = QPainter(img)
    p.fillRect(0, 0, 200, 400, QColor("#FF7A59"))
    p.fillRect(200, 0, 200, 400, QColor("#3B82F6"))
    p.end()
    return img


def test_las_tarjetas_de_letra_salen_en_1080x1920_y_cada_estilo_es_distinto(app):
    from descargador.ui import letra_viva as LV
    pista = {"titulo": "Jeremías 17-5", "artistas": [{"nombre": "Canserbero"}]}
    lineas = ["Que tu risita venía con la fecha ya vencia'", "Esta canción no es para nadie", "Que no tenga ganas"]
    portada = _portada()
    paleta = LV.paleta_de(portada)
    assert set(LV.ESTILOS_EXCLUSIVOS) == {"neon", "cristal", "papel", "aurora"}
    huellas = {}
    for estilo in LV.ESTILOS_TARJETA:
        img = LV.crear_tarjeta(pista, lineas, portada, paleta, estilo)
        assert (img.width(), img.height()) == (1080, 1920) and _no_es_plana(img)
        huellas[estilo] = img.pixelColor(540, 60).name() + img.pixelColor(100, 1700).name()
    assert len(set(huellas.values())) == 5                    # cinco aspectos distintos de verdad
    # sin estilo (o uno desconocido) es el clásico de siempre
    assert LV.crear_tarjeta(pista, lineas, portada, paleta).pixelColor(540, 60) == \
        LV.crear_tarjeta(pista, lineas, portada, paleta, "inventado").pixelColor(540, 60)
    # sin portada y con una sola línea tampoco se rompen
    for estilo in LV.ESTILOS_EXCLUSIVOS:
        assert LV.crear_tarjeta({"titulo": "x"}, ["una línea"], None, paleta, estilo).height() == 1920


# ------------------------------------------------------------------ cuadro «Tu año» con candado

def _dialogo(app, premium, monkeypatch, tmp_path):
    from descargador.ui import anio_caudal as AC
    from descargador.premium_datos import EstadoPremium
    monkeypatch.setattr(RA, "leer", lambda col, anio=None, ahora=None: RA.calcular(_historial(), 2026))
    monkeypatch.setattr(AC, "carpeta_imagenes", lambda: str(tmp_path))
    ctx = CtxFalso(SesionFalsa())
    ctx.coleccion = object()
    ctx.premium = P.GestorPremium(ctx)
    ctx.premium.estado = EstadoPremium(premium, "donador" if premium else None, None)
    d = AC.DialogoAnio(ctx)
    d.show()
    esperar(app, lambda: d.imagen is not None, "resumen calculado")
    return d


def test_el_ano_se_ve_borroso_y_con_candado_si_no_eres_donador(app, monkeypatch, tmp_path):
    d = _dialogo(app, False, monkeypatch, tmp_path)
    assert d.aviso.isVisible() and d.bt_donar.isVisible() and d.bt_codigo.isVisible()
    assert not d.bt_guardar.isEnabled() and not d.bt_copiar.isEnabled()
    d._guardar()
    assert list(tmp_path.glob("*.png")) == []                   # nada se guarda sin ser donador
    d.close()


def test_el_donador_ve_guarda_y_copia_su_ano(app, monkeypatch, tmp_path):
    d = _dialogo(app, True, monkeypatch, tmp_path)
    assert not d.aviso.isVisible() and d.bt_guardar.isEnabled() and d.bt_copiar.isEnabled()
    d._guardar()
    d._guardar()                                                # una segunda vez no pisa la primera
    archivos = sorted(p.name for p in tmp_path.glob("*.png"))
    assert len(archivos) == 2 and archivos[0].startswith("Tu-anio-en-Caudal-2026")
    guardada = QImage(str(tmp_path / archivos[0]))
    assert (guardada.width(), guardada.height()) == (1080, 1920)
    d._copiar()
    copiada = QApplication.clipboard().image()
    assert copiada.width() == 1080
    d.close()


def test_el_ano_sin_escuchas_lo_explica(app, monkeypatch, tmp_path):
    from descargador.ui import anio_caudal as AC
    monkeypatch.setattr(RA, "leer", lambda col, anio=None, ahora=None: RA.calcular([], 2026))
    ctx = CtxFalso(SesionFalsa())
    ctx.coleccion = object()
    ctx.premium = P.GestorPremium(ctx)
    d = AC.DialogoAnio(ctx)
    d.show()
    esperar(app, lambda: d.res is not None, "cálculo")
    assert "pocas escuchas" in d.estado.text() and not d.bt_guardar.isEnabled()
    d.close()


def test_el_selector_de_tarjeta_pide_donar_en_los_exclusivos(app, monkeypatch):
    """Elegir «Neón» sin ser donador abre «Donar aquí» y no guarda nada; el clásico sí; el donador elige todo."""
    from PySide6.QtWidgets import QWidget
    from descargador.premium_datos import EstadoPremium
    from descargador.ui import letra_viva as LV
    abiertos = []
    monkeypatch.setattr("descargador.ui.donar.abrir_donar", lambda padre=None: abiertos.append(1))
    visto = {}

    class Pagina(QWidget):
        _es_premium = LV.PaginaLetra._es_premium
        _elegir_estilo_tarjeta = LV.PaginaLetra._elegir_estilo_tarjeta

        def _mostrar_menu(self, menu):                      # en vez de abrir el menú de verdad
            acciones = menu.actions()
            visto["textos"] = [x.text() for x in acciones]
            return acciones[visto["indice"]]

    pg = Pagina()
    pg.ctx = CtxFalso(SesionFalsa())
    pg.ctx.premium = P.GestorPremium(pg.ctx)
    visto["indice"] = 1                                          # «Neón», sin ser donador
    assert pg._elegir_estilo_tarjeta() is None and abiertos == [1]
    assert "🔒" not in visto["textos"][0] and all("🔒" in t for t in visto["textos"][1:])
    visto["indice"] = 0                                          # «Clásico»: de todos
    assert pg._elegir_estilo_tarjeta() == "clasico" and abiertos == [1]
    pg.ctx.premium.estado = EstadoPremium(True, "donador", None)
    visto["indice"] = 3                                          # «Papel», ya como donador
    assert pg._elegir_estilo_tarjeta() == "papel" and abiertos == [1]
    assert not any("🔒" in t for t in visto["textos"])
    pg.close()
