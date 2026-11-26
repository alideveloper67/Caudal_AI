# -*- coding: utf-8 -*-
"""La tarjeta del resumen semanal y «¿Qué canción era?» (donadores): cálculo con datos inventados, el dibujo
real de la imagen y los cuadros con candado. Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Qt, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import mixes  # noqa: E402
from descargador import quecancion as Q  # noqa: E402
from descargador import resumen_semanal as RS  # noqa: E402

CAPTURAS = os.environ.get("CAUDAL_CAPTURAS", "")
AHORA = datetime(2026, 11, 19, 12, 0)             # jueves


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def pista(n, titulo, artista, dur=200, album=""):
    p = {"clave": f"yt:{n}", "video_id": f"id{n}", "titulo": titulo, "artista": artista, "duracion": dur,
         "miniatura": "", "artistas": [{"id": f"UC{artista}", "nombre": artista}]}
    if album:
        p["album"] = {"id": "al", "titulo": album}
    return p


LUNA = pista(1, "La Luna de Lima", "Las Estrellas", album="Noches")
SOL = pista(2, "Sol de Mañana", "Los del Sur")
MAR = pista(3, "Canción del Mar", "Las Estrellas")
BAILA = pista(4, "Baila Conmigo", "Los del Sur", dur=240)


def esc(p, dias_atras, hora=20, minuto=0):
    d = AHORA - timedelta(days=dias_atras)
    return mixes.escucha(p, datetime(d.year, d.month, d.day, hora, minuto))


def historial():
    return [
        esc(LUNA, 40), esc(SOL, 30),                                       # viejo
        esc(MAR, 9, 8), esc(MAR, 8, 9),                                    # semana anterior
        esc(LUNA, 6, 21), esc(LUNA, 5, 21), esc(LUNA, 4, 22), esc(SOL, 4, 22, 10),
        esc(MAR, 3, 9), esc(BAILA, 1, 18), esc(BAILA, 0, 8), esc(LUNA, 0, 9, 30),
    ]


# ------------------------------------------------------------------ cálculo de la semana

def test_la_semana_cuenta_lo_de_los_ultimos_7_dias():
    r = RS.calcular(historial(), AHORA)
    assert r["hay_datos"] and r["escuchas"] == 8
    assert r["minutos"] == 28                                          # 4×200 + 200 + 200 + 2×240 s
    assert r["canciones_distintas"] == 4 and r["artistas_distintos"] == 2
    assert r["cancion_top"]["titulo"] == "La Luna de Lima" and r["cancion_top"]["veces"] == 4
    assert r["artista_top"]["nombre"] == "Las Estrellas"
    assert len(r["dias"]) == 7 and [d["letra"] for d in r["dias"]] == ["V", "S", "D", "L", "M", "X", "J"]
    assert r["dias"][-1]["fecha"] == AHORA.date()
    assert r["dias_con_musica"] == 6 and r["rango"] == "13 – 19 nov"
    assert r["mejor_dia"]["minutos"] == max(d["minutos"] for d in r["dias"])
    assert r["franja"] in ("madrugada", "mañana", "tarde", "noche")


def test_compara_con_la_semana_anterior():
    r = RS.calcular(historial(), AHORA)
    assert isinstance(r["cambio"], int) and r["cambio"] > 0           # esta semana escuchó más que la anterior
    assert RS.frase_cambio(40) == "+40 % que la semana pasada"
    assert RS.frase_cambio(-12) == "−12 % que la semana pasada"
    assert RS.frase_cambio(0) == "igual que la semana pasada" and RS.frase_cambio(None) == ""


def test_pocas_escuchas_no_alcanzan_para_la_tarjeta():
    r = RS.calcular([esc(LUNA, 1), esc(SOL, 2)], AHORA)
    assert not r["hay_datos"]
    vacio = RS.calcular([], AHORA)
    assert not vacio["hay_datos"] and vacio["cancion_top"] is None and vacio["mejor_dia"] is None


def test_rango_que_cruza_de_mes():
    assert RS.texto_rango(datetime(2026, 10, 28), datetime(2026, 11, 3)) == "28 oct – 3 nov"


# ------------------------------------------------------------------ la imagen

def test_la_imagen_es_vertical_1080x1920_y_tiene_contenido(app):
    from descargador.ui import tarjeta_semanal as T
    img = T.crear_imagen_semana(RS.calcular(historial(), AHORA), "ana")
    assert (img.width(), img.height()) == (1080, 1920)
    colores = {img.pixel(x, y) for x in range(0, 1080, 36) for y in range(0, 1920, 48)}
    assert len(colores) > 40
    if CAPTURAS:
        os.makedirs(CAPTURAS, exist_ok=True)
        img.save(os.path.join(CAPTURAS, "tarjeta_semana.png"))


def test_la_imagen_aguanta_una_semana_con_un_solo_dia_y_textos_largos(app):
    from descargador.ui import tarjeta_semanal as T
    larga = pista(9, "Una canción con un título larguísimo que no cabe en la tarjeta de ninguna manera",
                  "Un artista con un nombre igual de largo que tampoco cabe aquí")
    r = RS.calcular([esc(larga, 0, 8), esc(larga, 0, 9), esc(larga, 0, 10)], AHORA)
    assert r["hay_datos"] and r["dias_con_musica"] == 1
    img = T.crear_imagen_semana(r, "")
    assert img.width() == 1080 and img.height() == 1920


# ------------------------------------------------------------------ cuadros (donador / candado)

class _Prem(QObject):
    cambiado = Signal()

    def __init__(self, si):
        super().__init__()
        self.premium = si


class _Ctx(QObject):
    me_gusta_cambio = Signal(str, bool)

    def __init__(self, premium=True):
        super().__init__()
        self.premium = _Prem(premium)
        self.cuenta = {"usuario": "ana"}
        self.coleccion = None
        self.sonando, self.gustos = [], []

    def reproducir_pista(self, p):
        self.sonando.append(p)

    def alternar_me_gusta(self, p):
        self.gustos.append(p)


def esperar(app, cond, maximo=8.0):
    fin = time.time() + maximo
    while not cond() and time.time() < fin:
        app.processEvents()
        time.sleep(0.01)
    return cond()


def test_cuadro_de_la_semana_con_candado_para_quien_no_es_donador(app, monkeypatch, tmp_path):
    from descargador.ui import tarjeta_semanal as T
    monkeypatch.setattr(RS, "leer", lambda col, ahora=None: RS.calcular(historial(), AHORA))
    monkeypatch.setattr(T, "carpeta_imagenes", lambda: str(tmp_path))
    ctx = _Ctx(premium=False)
    d = T.DialogoSemana(ctx)
    assert esperar(app, lambda: d.imagen is not None)
    assert not d.bt_guardar.isEnabled() and not d.bt_copiar.isEnabled()
    assert not d.aviso.isHidden() and not d.bt_donar.isHidden() and not d.bt_codigo.isHidden()
    d._guardar()
    assert list(tmp_path.iterdir()) == []                           # sin donador no guarda nada
    # al hacerse donador (prueba, regalo…) el cuadro se abre solo
    ctx.premium.premium = True
    ctx.premium.cambiado.emit()
    assert d.bt_guardar.isEnabled() and d.aviso.isHidden() and d.bt_donar.isHidden()
    d._guardar()
    d._guardar()
    nombres = sorted(p.name for p in tmp_path.iterdir())
    assert nombres == ["Mi-semana-en-Caudal-2026-11-19 (2).png", "Mi-semana-en-Caudal-2026-11-19.png"]
    d._copiar()
    assert QApplication.clipboard().image().width() == 1080
    d.deleteLater()


def test_cuadro_de_la_semana_sin_escuchas_lo_explica(app, monkeypatch):
    from descargador.ui import tarjeta_semanal as T
    monkeypatch.setattr(RS, "leer", lambda col, ahora=None: RS.calcular([], AHORA))
    d = T.DialogoSemana(_Ctx())
    assert esperar(app, lambda: d.res is not None)
    assert d.imagen is None and "pocas escuchas" in d.estado.text() and not d.bt_guardar.isEnabled()
    d.deleteLater()


# ------------------------------------------------------------------ ¿Qué canción era? (lógica)

def test_texto_sin_tildes_ni_mayusculas_y_todas_las_palabras():
    h = historial()
    assert [r["pista"]["clave"] for r in Q.buscar(h, "LUNA")] == ["yt:1"]
    assert [r["pista"]["clave"] for r in Q.buscar(h, "mañana")] == ["yt:2"]
    assert [r["pista"]["clave"] for r in Q.buscar(h, "manana")] == ["yt:2"]         # sin tilde también
    assert Q.buscar(h, "luna sol") == []                                          # todas las palabras a la vez
    assert {r["pista"]["clave"] for r in Q.buscar(h, "estrellas")} == {"yt:1", "yt:3"}      # por artista
    assert [r["pista"]["clave"] for r in Q.buscar(h, "noches")] == ["yt:1"]       # por álbum


def test_resultados_de_lo_mas_nuevo_a_lo_mas_viejo_con_sus_veces():
    r = Q.buscar(historial(), "luna")[0]
    assert r["veces"] == 5 and r["fecha"].date() == AHORA.date()                  # su escucha más reciente
    todo = Q.buscar(historial(), "estrellas")
    assert [x["fecha"] for x in todo] == sorted((x["fecha"] for x in todo), reverse=True)


def test_filtro_por_fechas_explicito():
    h = historial()
    r = Q.buscar(h, "", desde=date(2026, 11, 14), hasta=date(2026, 11, 15), entender_fechas=False)
    assert {x["pista"]["clave"] for x in r} == {"yt:1", "yt:2"}
    assert Q.buscar(h, "baila", desde=date(2026, 11, 1), hasta=date(2026, 11, 10)) == []


@pytest.mark.parametrize("texto,desde,hasta,resto", [
    ("ayer", date(2026, 11, 18), date(2026, 11, 18), ""),
    ("hoy", date(2026, 11, 19), date(2026, 11, 19), ""),
    ("anteayer luna", date(2026, 11, 17), date(2026, 11, 17), "luna"),
    ("semana pasada", date(2026, 11, 9), date(2026, 11, 15), ""),
    ("esta semana", date(2026, 11, 16), date(2026, 11, 19), ""),
    ("mes pasado", date(2026, 10, 1), date(2026, 10, 31), ""),
    ("15/11 luna", date(2026, 11, 15), date(2026, 11, 15), "luna"),
    ("12/12", date(2025, 12, 12), date(2025, 12, 12), ""),            # diciembre aún no llegó: es el del año pasado
    ("el lunes", date(2026, 11, 16), date(2026, 11, 16), ""),
    ("el jueves", date(2026, 11, 12), date(2026, 11, 12), ""),        # hoy es jueves: el de hace una semana
    ("la canción de marzo", date(2026, 3, 1), date(2026, 3, 31), ""),
    ("noviembre", date(2026, 11, 1), date(2026, 11, 30), ""),
    ("diciembre", date(2025, 12, 1), date(2025, 12, 31), ""),
])
def test_entiende_fechas_escritas_a_mano(texto, desde, hasta, resto):
    assert Q.interpretar_consulta(texto, AHORA) == (resto, desde, hasta)


def test_sin_fecha_el_texto_queda_intacto():
    assert Q.interpretar_consulta("Baila Conmigo", AHORA) == ("baila conmigo", None, None)
    assert Q.interpretar_consulta("", AHORA) == ("", None, None)
    assert Q.interpretar_consulta("31/02", AHORA)[1] is None          # fecha imposible: no se inventa


def test_busca_texto_y_fecha_juntos():
    h = historial()
    r = Q.buscar(h, "luna ayer", ahora=AHORA)
    assert r == []                                                    # ayer no escuchó la luna
    r = Q.buscar(h, "baila ayer", ahora=AHORA)
    assert [x["pista"]["clave"] for x in r] == ["yt:4"]
    r = Q.buscar(h, "luna semana pasada", ahora=AHORA)                # 9–15 nov: la escuchó el 13, 14 y 15
    assert len(r) == 1 and r[0]["veces"] == 3


def test_el_limite_corta_la_lista():
    h = [esc(pista(100 + i, f"Tema {i}", "X"), 0, 1, i % 60) for i in range(50)]
    assert len(Q.buscar(h, "tema", limite=10)) == 10


def test_texto_de_fecha_legible():
    assert Q.texto_fecha(datetime(2026, 11, 19, 21, 40), AHORA) == "hoy 21:40"
    assert Q.texto_fecha(datetime(2026, 11, 18, 9, 5), AHORA) == "ayer 09:05"
    assert Q.texto_fecha(datetime(2026, 11, 12, 21, 40), AHORA) == "jue 12 nov, 21:40"
    assert Q.texto_fecha(datetime(2025, 3, 3, 7, 0), AHORA) == "lun 3 mar 2025, 07:00"


# ------------------------------------------------------------------ ¿Qué canción era? (cuadro)

def test_cuadro_busca_y_reproduce(app):
    from descargador.ui import dialogo_que_cancion as D
    ctx = _Ctx()
    d = D.DialogoQueCancion(ctx, historial=historial())
    assert d.lista.count() == 0 and "Escribe algo" in d.estado.text()
    d.campo.setText("estrellas")
    d.buscar()
    assert d.lista.count() == 2 and "2 canciones" in d.estado.text()
    assert d.bt_escuchar.isEnabled()
    d.lista.setCurrentRow(1)
    d._escuchar()
    assert [p["clave"] for p in ctx.sonando] == [d.resultados[1]["pista"]["clave"]]
    d._gusta()
    assert len(ctx.gustos) == 1
    d.campo.setText("nada que ver")
    d.buscar()
    assert d.lista.count() == 0 and "No encontré" in d.estado.text() and not d.bt_escuchar.isEnabled()
    d.deleteLater()


def test_cuadro_filtra_por_calendario_y_por_palabras_de_fecha(app, monkeypatch):
    from PySide6.QtCore import QDate
    from descargador.ui import dialogo_que_cancion as D
    class Reloj(datetime):
        @classmethod
        def now(cls, tz=None):
            return AHORA                                           # «ayer» es el de estas escuchas
    monkeypatch.setattr(D, "datetime", Reloj)
    buscar = D.Q.buscar
    monkeypatch.setattr(D.Q, "buscar", lambda *a: buscar(*a, ahora=AHORA))
    ctx = _Ctx()
    d = D.DialogoQueCancion(ctx, historial=historial())
    d.usar_fechas.setChecked(True)
    d.desde.setDate(QDate(2026, 11, 14))
    d.hasta.setDate(QDate(2026, 11, 15))
    d.buscar()
    assert d.lista.count() == 2                                       # la luna y el sol de esos días
    d.usar_fechas.setChecked(False)
    d.campo.setText("baila ayer")
    d.buscar()
    assert d.lista.count() == 1 and "ayer" in d.lista.item(0).text()
    d.deleteLater()


def test_cuadro_con_candado_para_quien_no_es_donador(app):
    from descargador.ui import dialogo_que_cancion as D
    ctx = _Ctx(premium=False)
    d = D.DialogoQueCancion(ctx, historial=historial())
    assert not d.campo.isEnabled() and not d.aviso.isHidden() and not d.bt_donar.isHidden()
    d.campo.setText("luna")
    d.buscar()
    assert d.lista.count() == 0 and "donador" in d.estado.text()
    d._escuchar()
    assert ctx.sonando == []
    ctx.premium.premium = True
    ctx.premium.cambiado.emit()
    assert d.campo.isEnabled() and d.aviso.isHidden()
    d.buscar()
    assert d.lista.count() == 1
    d.deleteLater()


def test_cuadro_lee_el_historial_en_segundo_plano(app, monkeypatch):
    from descargador.ui import dialogo_que_cancion as D
    monkeypatch.setattr(mixes, "leer_historial", lambda col, desde=None, limite=0: historial())
    d = D.DialogoQueCancion(_Ctx())
    assert d.historial is None and "Leyendo" in d.estado.text()
    assert esperar(app, lambda: d.historial is not None)
    d.campo.setText("luna")
    d.buscar()
    assert d.lista.count() == 1
    d.deleteLater()
