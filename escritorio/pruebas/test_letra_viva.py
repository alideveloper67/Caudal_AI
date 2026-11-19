# -*- coding: utf-8 -*-
"""La letra viva: va con la musica, se puede tocar y se comparte como imagen.
Sin ventanas a la vista (Qt offscreen) y sin internet."""

import os
import sys
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, QPoint, Qt, Signal  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

LRC = [(0, ""), (12000, "Cuando la noche cae"), (16000, "y las luces se encienden"),
       (20500, "te busco entre la gente"), (24000, ""), (40000, "baila conmigo")]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _R(QObject):
    pista_cambio = Signal(object)
    posicion_cambio = Signal(float)
    estado_cambio = Signal(str)

    def __init__(self):
        super().__init__()
        self.actual = None
        self.estado = "sonando"
        self.velocidad = 1.0
        self._posicion = 0.0
        self.saltos = []

    def buscar(self, s):
        self.saltos.append(s)
        self._posicion = s
        self.posicion_cambio.emit(s)


class _Aj(dict):
    def guardar(self):
        pass


class _Ctx:
    def __init__(self):
        self.reproductor = _R()
        self.ajustes = _Aj(traducir_letra=False)
        self.avisos = []

    def avisar(self, texto, deshacer=None):
        self.avisos.append(texto)


def bombear(app, seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture
def pagina(app, monkeypatch, tmp_path):
    from descargador import catalogo
    from descargador.ui import imagenes, letra_viva as L
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": True, "lineas": LRC,
                                                       "texto": "", "fuente": "LRCLIB"})
    por = QImage(40, 40, QImage.Format_RGB32)
    por.fill(QColor("#DB2777"))
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(por))
    monkeypatch.setattr(imagenes, "pedir", lambda *a, **k: None)
    monkeypatch.setattr(L, "carpeta_imagenes", lambda: str(tmp_path))
    L.CACHE_LETRAS.clear()
    ctx = _Ctx()
    pag = L.PaginaLetra(ctx)
    pag.resize(1100, 680)
    pag.show()
    pista = {"clave": "yt:abc", "video_id": "abc", "titulo": "Noche", "artista": "Luna",
             "miniatura": "u"}
    ctx.reproductor.actual = pista
    ctx.reproductor.pista_cambio.emit(pista)
    bombear(app, 0.4)
    yield pag, ctx, tmp_path
    pag.close()
    pag.deleteLater()


def test_silencios_largos_se_vuelven_puntos():
    from descargador.ui.letra_viva import preparar_lineas
    lineas, sinc = preparar_lineas({"sincronizada": True, "lineas": LRC})
    assert sinc
    # intro de 12 s, el hueco vacio de 16 s y la linea suelta: puntos
    pausas = [ln for ln in lineas if ln["pausa"]]
    assert pausas[0]["ms"] == 0 and pausas[0]["hasta"] == 12000
    assert any(p["ms"] == 24000 and p["hasta"] == 40000 for p in pausas)
    cantadas = [ln["texto"] for ln in lineas if not ln["pausa"]]
    assert cantadas == ["Cuando la noche cae", "y las luces se encienden",
                        "te busco entre la gente", "baila conmigo"]
    # lo que dura cantar una linea nunca pasa del hueco hasta la siguiente
    assert all(ln["canto"] <= 4500 for ln in lineas if not ln["pausa"])
    # sin sincronizar: todas las lineas, sin tiempos
    lineas, sinc = preparar_lineas({"sincronizada": False, "texto": "a\nb"})
    assert not sinc and [ln["ms"] for ln in lineas] == [None, None]


def test_la_linea_que_suena_sigue_a_la_musica(app, pagina):
    pag, ctx, _ = pagina
    lz = pag.lienzo
    assert lz.lineas, "la letra tenia que llegar"
    ctx.reproductor.posicion_cambio.emit(13.0)
    bombear(app, 0.2)
    assert lz.lineas[lz._actual]["texto"] == "Cuando la noche cae"
    # a mitad de la linea se ha cantado una parte, ni toda ni nada
    assert 0.2 < lz._progreso(lz._actual, 13500) < 1.0
    ctx.reproductor.posicion_cambio.emit(21.0)
    bombear(app, 0.2)
    assert lz.lineas[lz._actual]["texto"] == "te busco entre la gente"
    # el tiempo avanza solo entre avisos del motor (fluido aunque lleguen pocos)
    antes = lz.ahora_ms()
    bombear(app, 0.25)
    assert lz.ahora_ms() - antes >= 200
    # en pausa no avanza
    ctx.reproductor.estado = "pausa"
    ctx.reproductor.posicion_cambio.emit(21.0)
    a = lz.ahora_ms()
    bombear(app, 0.2)
    assert lz.ahora_ms() == a
    # el instrumental: puntos
    ctx.reproductor.estado = "sonando"
    ctx.reproductor.posicion_cambio.emit(30.0)
    bombear(app, 0.2)
    assert lz.lineas[lz._actual]["pausa"]


def test_un_clic_en_una_linea_salta_a_ese_momento(app, pagina):
    pag, ctx, _ = pagina
    lz = pag.lienzo
    ctx.reproductor.posicion_cambio.emit(13.0)
    bombear(app, 1.2)  # que la animacion se asiente
    k = next(i for i, ln in enumerate(lz.lineas) if ln["texto"] == "te busco entre la gente")
    it = lz._items[k]
    QTest.mouseClick(lz, Qt.LeftButton, Qt.NoModifier,
                     QPoint(int(lz._margen_x()) + 20, int(it["yv"] + 10)))
    assert ctx.reproductor.saltos == [20.5]


def test_guardar_imagen_para_historias(app, pagina):
    pag, ctx, carpeta = pagina
    ctx.reproductor.posicion_cambio.emit(16.5)
    bombear(app, 0.2)
    pag.bt_imagen.click()
    pngs = [f for f in os.listdir(carpeta) if f.endswith(".png")]
    assert len(pngs) == 1
    img = QImage(os.path.join(carpeta, pngs[0]))
    assert (img.width(), img.height()) == (1080, 1920)
    assert "Imágenes" in ctx.avisos[-1]
    assert pag.lienzo.lineas_para_tarjeta()[0] == "y las luces se encienden"


def test_sin_letra_lo_explica(app, monkeypatch):
    from descargador import catalogo
    from descargador.ui import imagenes, letra_viva as L
    monkeypatch.setattr(catalogo, "letras", lambda p: {"sincronizada": False, "lineas": [],
                                                       "texto": "", "fuente": ""})
    monkeypatch.setattr(imagenes, "imagen", lambda url, cb: cb(QImage()))
    L.CACHE_LETRAS.clear()
    ctx = _Ctx()
    lz = L.LienzoLetra(ctx, compacto=True)
    lz.resize(320, 500)
    lz.show()
    p = {"clave": "yt:zz", "titulo": "X"}
    ctx.reproductor.actual = p
    ctx.reproductor.pista_cambio.emit(p)
    bombear(app, 0.3)
    assert "No hay letra" in lz.mensaje
    lz.grab()  # pintar el mensaje no falla
    lz.close()


# ------------------------------------------------- estabilidad (2.2.3)

def test_las_portadas_en_memoria_tienen_tope(app):
    from descargador.ui import imagenes as I
    I._IMAGENES.clear()
    I._peso["total"] = 0
    grande = QImage(1280, 720, QImage.Format_RGB32)
    for n in range(120):  # ~440 MB si no hubiera tope
        I._guardar_original(f"u{n}", grande)
    assert I._peso["total"] <= I.TOPE_ORIGINALES
    assert "u119" in I._IMAGENES and "u0" not in I._IMAGENES
    I._IMAGENES.clear()
    I._peso["total"] = 0


def test_los_errores_quedan_en_fallos_log(tmp_path):
    import threading
    from descargador import registro_fallos as R
    antes_hook, antes_hilo = sys.excepthook, threading.excepthook
    try:
        R.activar(tmp_path)
        try:
            raise ValueError("boton roto")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        h = threading.Thread(target=lambda: 1 / 0, name="prueba")
        h.start()
        h.join()
        texto = (tmp_path / "fallos.log").read_text(encoding="utf-8")
        assert "boton roto" in texto and "Error en la interfaz" in texto
        assert "ZeroDivisionError" in texto and "prueba" in texto
    finally:
        sys.excepthook, threading.excepthook = antes_hook, antes_hilo


def test_estilo_exclusivo_de_la_tarjeta_pide_donar_y_luego_se_usa_al_guardar(app, pagina, monkeypatch):
    from descargador.ui import letra_viva as L
    pag, ctx, carpeta = pagina
    ctx.reproductor.posicion_cambio.emit(16.5)
    bombear(app, 0.2)
    abiertos = []
    monkeypatch.setattr("descargador.ui.donar.abrir_donar", lambda padre=None: abiertos.append(1))
    eleccion = {"i": 1}                                   # «Neón»
    monkeypatch.setattr(L.PaginaLetra, "_mostrar_menu", lambda self, menu: menu.actions()[eleccion["i"]])
    # sin ser donador: se abre «Donar aquí» y el estilo no cambia; guardar sigue siendo el clásico, de un clic
    pag.bt_estilo.click()
    assert abiertos == [1] and pag.estilo_tarjeta == "clasico"
    # con beneficios: el estilo queda elegido, el botón lo dice y la imagen sale en ese estilo
    class _Premium:
        premium = True
    ctx.premium = _Premium()
    pag.bt_estilo.click()
    assert pag.estilo_tarjeta == "neon" and "Neón" in pag.bt_estilo.text()
    vistos = []
    real = L.crear_tarjeta
    monkeypatch.setattr(L, "crear_tarjeta", lambda *a, **k: (vistos.append(a[-1]), real(*a, **k))[1])
    pag.bt_imagen.click()
    assert vistos == ["neon"]
    assert len([f for f in os.listdir(carpeta) if f.endswith(".png")]) == 1
    # si se acaba la prueba, vuelve el clásico solo
    ctx.premium.premium = False
    pag.bt_imagen.click()
    assert vistos == ["neon", "clasico"]
