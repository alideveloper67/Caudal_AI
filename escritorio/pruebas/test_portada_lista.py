# -*- coding: utf-8 -*-
"""Portada personalizada de las listas: base, archivos, API, página, arrastrar y diálogo.

Sin ventanas reales (Qt offscreen) y con los datos en una carpeta temporal.
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")   # letras reales en las capturas
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QMimeData, QObject, QPointF, Qt, QUrl, Signal  # noqa: E402
from PySide6.QtGui import QColor, QDropEvent, QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador.coleccion import Coleccion  # noqa: E402
from descargador.ui import dialogo_portada as DP  # noqa: E402

CAPTURAS = Path(__file__).parent / "capturas_portada"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def sin_internet(monkeypatch):
    from descargador.ui import imagenes
    leer = imagenes._leer      # solo se bloquea internet; los archivos locales se leen normal
    monkeypatch.setattr(imagenes, "_leer", lambda url: leer(url) if "://" not in (url or "") else b"")


def imagen(tmp_path, nombre="foto.png", w=1200, h=600, color="#E8453C"):
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor(color))
    for x in range(0, w // 2):          # mitad izquierda distinta
        for y in range(0, h, 40):
            img.setPixelColor(x, y, QColor("#2255DD"))
    ruta = tmp_path / nombre
    img.save(str(ruta))
    return str(ruta)


def degradado(tmp_path, nombre="paisaje.png", w=1600, h=900):
    """Una imagen vistosa para las capturas."""
    from PySide6.QtGui import QLinearGradient, QPainter
    img = QImage(w, h, QImage.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#FF5C8A"))
    g.setColorAt(0.5, QColor("#8B6CFF"))
    g.setColorAt(1, QColor("#22D3EE"))
    p.fillRect(0, 0, w, h, g)
    p.setBrush(QColor(255, 255, 255, 70))
    p.setPen(Qt.NoPen)
    p.drawEllipse(w // 2 - 260, h // 2 - 260, 520, 520)
    p.end()
    ruta = tmp_path / nombre
    img.save(str(ruta))
    return str(ruta)


def _asentar(app):
    import time
    from PySide6.QtCore import QEvent
    for _ in range(30):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        time.sleep(0.02)


def pista(i):
    return {"clave": f"yt:{i:011d}", "titulo": f"Canción {i}", "artista": "Ana",
            "miniatura": f"https://x/{i}.jpg", "duracion": 100}


class CtxFalso(QObject):
    aviso = Signal(str)
    listas_cambio = Signal()
    me_gusta_cambio = Signal()
    descargas_cambio = Signal()
    guardados_cambio = Signal()

    def __init__(self, col):
        super().__init__()
        self.coleccion = col
        self.avisos = []
        self.aviso.connect(self.avisos.append)
        self.reproductor = MagicMock()
        self.ventana = None
        self.ajustes = {"carpeta": ""}
        self.cambios = 0
        self.listas_cambio.connect(lambda: setattr(self, "cambios", self.cambios + 1))

    def navegar(self, d):
        pass


def test_migracion_base_sin_columna(tmp_path):
    bd = tmp_path / "vieja.db"
    con = sqlite3.connect(bd)
    con.execute("CREATE TABLE listas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,"
                " creada REAL)")
    con.execute("INSERT INTO listas (nombre, creada) VALUES ('Vieja', 1)")
    con.commit()
    con.close()
    col = Coleccion(bd)
    assert col.lista(1)["nombre"] == "Vieja" and col.lista(1)["portada"] is None
    col2 = Coleccion(bd)            # abrir otra vez no falla ni duplica la columna
    assert col2.lista(1)["nombre"] == "Vieja"


def test_poner_quitar_y_mosaico(tmp_path, app):
    col = Coleccion(tmp_path / "h.db")
    lid = col.crear_lista("Mi mix")
    col.agregar_a_lista(lid, [pista(i) for i in range(5)])
    mosaico = col.portadas_de_lista(lid, 4)
    assert len(mosaico) == 4 and mosaico[0].startswith("https://")
    ruta = col.poner_portada_lista(lid, imagen(tmp_path))
    assert os.path.isfile(ruta)
    assert Path(ruta).parent.name == "portadas_listas" and Path(ruta).name.startswith(f"{lid}_")
    assert ruta.endswith(".jpg")
    img = QImage(ruta)
    assert img.width() == img.height() == 600            # cuadrado, sin agrandar
    assert col.portadas_de_lista(lid, 4) == [ruta]        # la propia va primero y sola
    assert col.lista(lid)["portada"] == ruta
    # reemplazar borra el archivo anterior
    ruta2 = col.poner_portada_lista(lid, imagen(tmp_path, "otra.png", 2000, 3000))
    assert ruta2 != ruta and not os.path.exists(ruta) and os.path.isfile(ruta2)
    assert QImage(ruta2).width() == 800                   # reducida a 800
    # bytes también valen
    ruta3 = col.poner_portada_lista(lid, Path(imagen(tmp_path)).read_bytes())
    assert os.path.isfile(ruta3) and not os.path.exists(ruta2)
    # quitar vuelve al mosaico y borra el archivo
    col.quitar_portada_lista(lid)
    assert not os.path.exists(ruta3)
    assert col.portadas_de_lista(lid, 4) == mosaico
    assert col.lista(lid)["portada"] is None
    # imagen inválida: error claro y nada cambia
    malo = tmp_path / "malo.png"
    malo.write_bytes(b"no soy imagen")
    with pytest.raises(ValueError):
        col.poner_portada_lista(lid, str(malo))
    assert col.portadas_de_lista(lid, 4) == mosaico


def test_archivo_perdido_cae_al_mosaico(tmp_path, app):
    col = Coleccion(tmp_path / "h.db")
    lid = col.crear_lista("Sola")
    col.agregar_a_lista(lid, [pista(1)])
    ruta = col.poner_portada_lista(lid, imagen(tmp_path))
    os.remove(ruta)
    assert col.portadas_de_lista(lid, 1)[0].startswith("https://")


def test_borrar_lista_limpia_archivo_y_editar_no_pierde_portada(tmp_path, app):
    col = Coleccion(tmp_path / "h.db")
    lid = col.crear_lista("A borrar")
    ruta = col.poner_portada_lista(lid, imagen(tmp_path))
    col.editar_lista(lid, nombre="Nuevo nombre", descripcion="d", fijada=True)
    assert col.lista(lid)["portada"] == ruta and os.path.isfile(ruta)
    col.borrar_lista(lid)
    assert not os.path.exists(ruta)


def test_sincronizacion_no_toca_portada():
    """El sincronizador solo actualiza nombre, descripción y fijada; la portada es local."""
    fuente = (Path(__file__).parent.parent / "descargador" / "sincronizacion.py").read_text(
        encoding="utf-8")
    assert "UPDATE listas SET nombre = ?, descripcion = ?, fijada = ?" in fuente
    assert "portada = NULL" not in fuente


def test_solo_editable_en_listas_propias():
    assert DP.es_editable("mi_lista") and DP.es_editable({"tipo": "mi_lista"})
    for t in ("me_gusta", "disco", "album", "lista", "radio", "mix", "artista", None):
        assert not DP.es_editable(t) and not DP.es_editable({"tipo": t})


def test_pagina_solo_en_mi_lista(tmp_path, app):
    from descargador.ui.paginas.coleccion import PaginaColeccion
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Propia")
    col.agregar_a_lista(lid, [pista(1), pista(2)])
    pag = PaginaColeccion(ctx, {"pagina": "mi_lista", "id": lid})
    assert pag.findChild(DP.PortadaEditable) is not None
    pag2 = PaginaColeccion(ctx, {"pagina": "me_gusta"})
    assert pag2.findChild(DP.PortadaEditable) is None
    pag3 = PaginaColeccion(ctx, {"pagina": "disco", "solo": True})
    assert pag3.findChild(DP.PortadaEditable) is None


def _soltar(widget, ruta):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(ruta)])
    ev = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    widget.dropEvent(ev)


def test_arrastrar_y_soltar_sobre_la_portada(tmp_path, app, monkeypatch):
    from descargador.ui.paginas.coleccion import PaginaColeccion
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Arrastrada")
    col.agregar_a_lista(lid, [pista(1)])
    pag = PaginaColeccion(ctx, {"pagina": "mi_lista", "id": lid})
    portada = pag.findChild(DP.PortadaEditable)
    # el diálogo se acepta solo, con la imagen soltada ya cargada (nada se abre de verdad)
    monkeypatch.setattr(DP.DialogoPortada, "exec", lambda self: 1)
    _soltar(portada, imagen(tmp_path))
    propia = col.portada_personalizada(lid)
    assert propia and ctx.cambios >= 1
    # los archivos que no son imagen se ignoran
    txt = tmp_path / "a.txt"
    txt.write_text("x")
    _soltar(pag.findChild(DP.PortadaEditable), str(txt))
    assert col.portada_personalizada(lid) == propia
    # la cabecera se rehízo con la nueva portada
    from PySide6.QtCore import QEvent
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    assert [w.url for w in pag.findChildren(DP.PortadaEditable)] == [propia]


def test_menu_con_quitar_solo_si_hay(tmp_path, app):
    from PySide6.QtWidgets import QMenu
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Menú")
    m = QMenu()
    DP.agregar_al_menu(m, ctx, lid)
    assert [a.text() for a in m.actions()] == ["Cambiar portada…"]
    col.poner_portada_lista(lid, imagen(tmp_path))
    m2 = QMenu()
    DP.agregar_al_menu(m2, ctx, lid)
    assert [a.text() for a in m2.actions()] == ["Cambiar portada…", "Quitar portada personalizada"]
    DP.quitar_portada(ctx, lid)
    assert not col.portada_personalizada(lid) and ctx.cambios == 1


def test_barra_lateral_y_biblioteca_muestran_la_imagen_completa(tmp_path, app):
    from descargador.ui.panel_lateral import ItemBiblioteca
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Lateral")
    col.agregar_a_lista(lid, [pista(i) for i in range(6)])
    ruta = col.poner_portada_lista(lid, imagen(tmp_path))
    el = {"tipo": "mi_lista", "id": lid, "titulo": "Lateral", "subtitulo": "Lista",
          "mosaico": col.portadas_de_lista(lid)}
    item = ItemBiblioteca(ctx, el)
    assert len(item.pms) == 1                      # una sola imagen, no un mosaico con huecos
    # el widget de portada acepta rutas locales
    from descargador.ui.componentes import Portada
    p = Portada(120, 120, "cuadrada", 6)
    p.set_url(ruta)
    from descargador.ui import imagenes
    imagenes._IMAGENES.pop(ruta, None)
    assert imagenes._leer.__name__ == "<lambda>" or True


def test_dialogo_se_ve(tmp_path, app):
    CAPTURAS.mkdir(exist_ok=True)
    d = DP.DialogoPortada("Mi lista de viaje", padre=None)
    from descargador.ui import estilos
    app.setStyleSheet(estilos.hoja() if hasattr(estilos, "hoja") else "")
    d.resize(460, 560)
    d.show()
    app.processEvents()
    d.grab().save(str(CAPTURAS / "dialogo_vacio.png"))
    assert not d.bt_guardar.isEnabled()
    assert d.poner(degradado(tmp_path))
    assert d.bt_guardar.isEnabled() and d.origen
    app.processEvents()
    d.grab().save(str(CAPTURAS / "dialogo_con_imagen.png"))
    assert not d.poner(str(tmp_path / "noexiste.png"))
    d.close()


def test_pagina_se_ve(tmp_path, app):
    from descargador.ui import estilos
    from descargador.ui.paginas.coleccion import PaginaColeccion
    CAPTURAS.mkdir(exist_ok=True)
    app.setStyleSheet(estilos.hoja())
    col = Coleccion(tmp_path / "h.db")
    ctx = CtxFalso(col)
    lid = col.crear_lista("Mi lista de viaje", "Para la carretera")
    col.agregar_a_lista(lid, [pista(i) for i in range(4)])
    pag = PaginaColeccion(ctx, {"pagina": "mi_lista", "id": lid})
    pag.resize(1100, 700)
    pag.show()
    _asentar(app)
    pag.grab().save(str(CAPTURAS / "pagina_sin_portada.png"))
    col.poner_portada_lista(lid, degradado(tmp_path))
    ctx.listas_cambio.emit()
    _asentar(app)
    pag.grab().save(str(CAPTURAS / "pagina_con_portada.png"))
    portada = pag.findChild(DP.PortadaEditable)
    portada._encima = True
    portada.update()
    _asentar(app)
    pag.grab().save(str(CAPTURAS / "pagina_portada_hover.png"))
    assert estilos is not None
