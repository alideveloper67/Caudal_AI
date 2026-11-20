# -*- coding: utf-8 -*-
"""La Fiesta en Windows (descargador/fiesta.py y ui/paginas/fiesta.py), sin red:
una «base» falsa en memoria con las mismas reglas que supabase/fiesta.sql y un
reproductor falso. Qt offscreen: no se abre ninguna ventana."""

import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from descargador import fiesta as F  # noqa: E402
from descargador import nube  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def cancion(i, votos=0, **kw):
    return {"id": i, "video_id": f"vid{i:08d}", "titulo": f"Canción {i}", "artista": "Artista",
            "miniatura": f"https://i.ytimg.com/vi/{i}/hq.jpg", "duracion": 200, "nombre": "Ana",
            "votos": votos, "estado": "cola", **kw}


# ================================================================ sin Qt

def test_leer_fiesta_ordena_y_limpia():
    f = F.leer_fiesta({
        "codigo": "ABC234", "nombre": "Cumple", "abierta": True, "limite": 3, "version": 4, "invitados": 2,
        "sonando": {"video_id": "AAAAAAAAAAA", "titulo": "Suena", "miniatura": "javascript:alert(1)",
                    "fiesta_id": 7, "pausa": True, "nombre": "Beto"},
        "cola": [cancion(5, 1), cancion(3, 1), cancion(9, 4), "basura"],
        "sonadas": [cancion(1, estado="sonando"), cancion(2, estado="sonada")],
    })
    assert [c["id"] for c in f["cola"]] == [9, 3, 5]
    assert f["sonando"]["miniatura"] == "" and f["sonando"]["fiesta_id"] == 7 and f["sonando"]["pausa"]
    assert [c["id"] for c in f["sonadas"]] == [2]
    assert F.leer_fiesta(None) is None and F.leer_fiesta([]) is None
    assert F.leer_fiesta({"abierta": False})["abierta"] is False


def test_codigo_y_enlace():
    assert F.normalizar_codigo(" abc-234 ") == "ABC234"
    assert F.normalizar_codigo("ABC23O") == ""
    assert F.enlace("ABC234") == "https://caudal-musica.netlify.app/fiesta/ABC234"


def test_mensajes_de_error():
    assert F.mensaje_de_error(400, '{"code":"P0001","message":"Esta fiesta ya terminó: el anfitrión la cerró."}') \
        == "Esta fiesta ya terminó: el anfitrión la cerró."
    assert "todavía no está activa" in F.mensaje_de_error(404, {"code": "PGRST202", "message": "x"})
    assert F.mensaje_de_error(400, '{"code":"42501","message":"permission denied"}') == "Algo falló. Vuelve a intentarlo."
    assert "internet" in F.mensaje_de_error(502, "")


class _Resp:
    def __init__(self, status, cuerpo):
        self.status_code = status
        self.text = cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)

    def json(self):
        return json.loads(self.text)


def test_llamar_usa_la_base_y_traduce(monkeypatch):
    vistas = []

    def falso(metodo, ruta, **kw):
        vistas.append((metodo, ruta, kw.get("json")))
        if ruta.endswith("fiesta_crear"):
            return _Resp(200, {"codigo": "ABC234", "clave": "k" * 64})
        if ruta.endswith("fiesta_cerrar"):
            return _Resp(400, {"code": "P0001", "message": "Solo el anfitrión puede hacer eso en esta fiesta."})
        return _Resp(200, "null")
    monkeypatch.setattr(nube, "_peticion", falso)
    assert F.crear("Cumple", 3) == ("ABC234", "k" * 64)
    assert vistas[0] == ("POST", "/rest/v1/rpc/fiesta_crear", {"p_nombre": "Cumple", "p_limite": 3})
    assert F.ver("ABC234") is None
    with pytest.raises(F.ErrorFiesta, match="Solo el anfitrión"):
        F.cerrar("ABC234", "mala")

    def sin_red(*_a, **_k):
        raise nube.SinConexion("No hay conexión con el servidor de cuentas. Revisa tu internet.")
    monkeypatch.setattr(nube, "_peticion", sin_red)
    with pytest.raises(F.ErrorFiesta, match="Revisa tu internet"):
        F.ver("ABC234")


def test_debe_tomar():
    assert F.debe_tomar(False, "parado", None, False)            # no suena nada
    assert F.debe_tomar(True, "parado", 100, False)              # terminó la cola del reproductor
    assert F.debe_tomar(True, "sonando", 25, False)              # quedan 25 s
    assert F.debe_tomar(True, "sonando", 3, False)
    assert not F.debe_tomar(True, "sonando", 26, False)
    assert not F.debe_tomar(True, "sonando", None, False)        # sin duración no se adivina
    assert not F.debe_tomar(True, "pausa", 5, False)             # en pausa no
    assert not F.debe_tomar(False, "parado", None, True)         # ya hay una esperando
    assert not F.debe_tomar(True, "sonando", 5, True)


def test_pistas():
    p = F.pista_de_cancion(cancion(4))
    assert p["video_id"] == "vid00000004" and p["fiesta_id"] == 4 and p["artista"] == "Artista"
    assert p["tipo"] == "pista" and p["fiesta_nombre"] == "Ana"
    s = F.pista_para_sonando(p, 1500, True)
    assert s["fiesta_id"] == 4 and s["pos_ms"] == 1500 and s["pausa"] is True and s["duracion"] == 200
    assert "fiesta_id" not in F.pista_para_sonando({"video_id": "x", "miniatura": "http://inseguro"})
    assert F.pista_para_sonando({"miniatura": "http://inseguro"})["miniatura"] == ""
    assert F.pista_para_sonando(None) is None
    assert F.hay_pendiente([{"video_id": "a"}, p]) and not F.hay_pendiente([{"video_id": "a"}])


# ================================================================ base falsa + reproductor falso

class BaseFalsa:
    """Las reglas de supabase/fiesta.sql que usa el anfitrión, en memoria."""

    def __init__(self):
        self.f = None
        self.cola = []
        self.sonadas = []
        self.llamadas = []

    def _ver(self):
        f = dict(self.f, cola=[dict(c) for c in self.cola], sonadas=[dict(c) for c in self.sonadas])
        f["version"] += 0
        return F.leer_fiesta(f)

    def _tocar(self):
        self.f["version"] += 1

    def crear(self, nombre, limite):
        self.llamadas.append(("crear", nombre, limite))
        self.f = {"codigo": "ABC234", "nombre": nombre or "Fiesta", "abierta": True, "limite": limite,
                  "version": 1, "invitados": 2, "sonando": None}
        self.clave = "c" * 64
        return "ABC234", self.clave

    def ver(self, codigo):
        self.llamadas.append(("ver",))
        return self._ver()

    def _clave(self, clave):
        if clave != self.clave:
            raise F.ErrorFiesta("Solo el anfitrión puede hacer eso en esta fiesta.")

    def quitar(self, codigo, clave, cid):
        self._clave(clave)
        self.llamadas.append(("quitar", cid))
        if not any(c["id"] == cid for c in self.cola):
            raise F.ErrorFiesta("Esa canción ya no está en la cola.")
        self.cola = [c for c in self.cola if c["id"] != cid]
        self._tocar()
        return self._ver()

    def limite(self, codigo, clave, n):
        self._clave(clave)
        self.llamadas.append(("limite", n))
        self.f["limite"] = n
        self._tocar()
        return self._ver()

    def cerrar(self, codigo, clave):
        self._clave(clave)
        self.llamadas.append(("cerrar",))
        self.f["abierta"] = False
        self.f["sonando"] = None
        self._tocar()
        return self._ver()

    def tomar(self, codigo, clave):
        self._clave(clave)
        self.llamadas.append(("tomar",))
        if not self.f["abierta"] or not self.cola:
            return None
        c = F.ordenar_cola([F.leer_cancion(x) for x in self.cola])[0]
        self.cola = [x for x in self.cola if x["id"] != c["id"]]
        self.sonadas.insert(0, dict(c, estado="sonando"))
        self._tocar()
        return c

    def sonando(self, codigo, clave, datos):
        self._clave(clave)
        self.llamadas.append(("sonando", datos))
        self.f["sonando"] = datos
        self._tocar()
        return self._ver()

    def api(self):
        return {k: getattr(self, k) for k in ("crear", "ver", "quitar", "limite", "cerrar", "tomar", "sonando")}


def en_el_acto(f, *a, ok=None, error=None):
    try:
        r = f(*a)
    except Exception as e:  # noqa: BLE001
        if error:
            error(e)
        return
    if ok:
        ok(r)


class ReproductorFalso(QObject):
    pista_cambio = Signal(object)
    estado_cambio = Signal(str)
    posicion_cambio = Signal(float)
    duracion_cambio = Signal(float)

    def __init__(self):
        super().__init__()
        self.actual = None
        self.estado = "parado"
        self.proximas = []
        self.hechos = []

    def reproducir_lista(self, pistas, inicio=0, contexto=None, **_):
        self.hechos.append(("lista", pistas[0]["fiesta_id"]))
        self.actual = pistas[0]
        self.estado = "sonando"
        self.pista_cambio.emit(self.actual)

    def reproducir_despues(self, pistas):
        self.hechos.append(("despues", pistas[0]["fiesta_id"]))
        self.proximas[0:0] = pistas

    def reproducir_pista(self, pista, contexto=None, modo=None, con_radio=True):
        self.hechos.append(("ya", pista.get("fiesta_id"), con_radio))
        self.actual = pista
        self.estado = "sonando"
        self.pista_cambio.emit(pista)

    def agregar_a_cola(self, pistas):
        self.proximas.extend(pistas)


class Ctx(QObject):
    aviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.reproductor = ReproductorFalso()
        self.avisos = []
        self.aviso.connect(self.avisos.append)


@pytest.fixture
def montaje(app, monkeypatch):
    monkeypatch.setattr(F.ControlFiesta, "_abrir_canal", lambda self: None)
    ctx = Ctx()
    base = BaseFalsa()
    c = F.ControlFiesta(ctx, api=base.api(), en_fondo=en_el_acto)
    c.aviso.connect(ctx.aviso.emit)
    return ctx, base, c


def _listo_para_tomar(c):
    c._ultimo_tomar = 0.0


def test_crear_y_tomar_cuando_no_suena_nada(montaje):
    ctx, base, c = montaje
    errores = []
    c.error.connect(errores.append)
    c.crear("Cumple", 3)
    assert c.codigo == "ABC234" and c.abierta and c.enlace.endswith("/fiesta/ABC234")
    assert base.llamadas[0] == ("crear", "Cumple", 3)
    # llega la primera canción: no suena nada → se pone sola
    base.cola = [cancion(1, 0), cancion(2, 3)]
    _listo_para_tomar(c)
    c.refrescar()
    assert ctx.reproductor.hechos[0] == ("lista", 2)             # la más votada
    assert any("De la fiesta" in a and "Ana" in a for a in ctx.avisos)
    # se avisó qué suena con su fiesta_id
    c._mandar_sonando()
    s = [x for x in base.llamadas if x[0] == "sonando"][-1][1]
    assert s["fiesta_id"] == 2 and s["video_id"] == "vid00000002" and s["pausa"] is False
    assert not errores


def test_siguiente_al_final_de_la_cancion(montaje):
    ctx, base, c = montaje
    r = ctx.reproductor
    c.crear("", 0)
    r.actual, r.estado = {"video_id": "AAAAAAAAAAA", "titulo": "Mía", "duracion": 200}, "sonando"
    base.cola = [cancion(5)]
    c._al_duracion(200.0)
    c.refrescar()
    _listo_para_tomar(c)
    c._al_posicion(100.0)
    c.revisar()
    assert r.hechos == []                                        # quedan 100 s: todavía no
    c._al_posicion(180.0)
    c.revisar()
    assert r.hechos == [("despues", 5)]                          # quedan 20 s: a continuación
    base.cola = [cancion(6)]
    _listo_para_tomar(c)
    c.refrescar()
    assert r.hechos == [("despues", 5)]                          # ya hay una esperando: no otra
    # en pausa no se toma
    r.proximas = []
    r.estado = "pausa"
    _listo_para_tomar(c)
    c.revisar()
    assert len(r.hechos) == 1
    # sin modo automático tampoco
    r.estado = "sonando"
    c.poner_auto(False)
    _listo_para_tomar(c)
    c.revisar()
    assert len(r.hechos) == 1
    c.poner_auto(True)
    _listo_para_tomar(c)
    c.revisar()
    assert r.hechos[-1] == ("despues", 6)


def test_quitar_limite_poner_ahora_y_cerrar(montaje, app):
    ctx, base, c = montaje
    c.crear("Fiesta", 5)
    c.poner_auto(False)
    base.cola = [cancion(1), cancion(2, 2)]
    c.refrescar()
    assert [x["id"] for x in c.fiesta["cola"]] == [2, 1]
    c.quitar(1)
    assert ("quitar", 1) in base.llamadas and [x["id"] for x in c.fiesta["cola"]] == [2]
    errores = []
    c.error.connect(errores.append)
    c.quitar(99)
    assert errores == ["Esa canción ya no está en la cola."]
    c.poner_limite(2)
    assert c.fiesta["limite"] == 2
    n = len(base.llamadas)
    c.poner_limite(2)                                           # igual: no se llama
    assert len(base.llamadas) == n
    c.poner_ahora(c.fiesta["cola"][0])
    assert ctx.reproductor.hechos[-1] == ("ya", 2, False)
    c._mandar_sonando()
    assert base.f["sonando"]["fiesta_id"] == 2
    c.cerrar()
    assert c.fiesta["abierta"] is False and not c.abierta
    assert not c._consulta.isActive() and not c._tic.isActive()
    c.olvidar()
    assert c.codigo is None and c.fiesta is None


def test_pausa_se_avisa(montaje):
    ctx, base, c = montaje
    r = ctx.reproductor
    c.crear("", 5)
    r.actual, r.estado = {"video_id": "AAAAAAAAAAA", "titulo": "Mía", "duracion": 200}, "pausa"
    c._al_posicion(42.0)
    c._mandar_sonando()
    s = base.f["sonando"]
    assert s["pausa"] is True and s["pos_ms"] == 42000 and "fiesta_id" not in s
    r.estado = "parado"
    c._mandar_sonando()
    assert base.f["sonando"] is None


def test_respuesta_vieja_no_pisa(montaje):
    _ctx, base, c = montaje
    c.crear("", 5)
    base.f["version"] = 10
    c.refrescar()
    base.f["version"] = 3
    base.cola = [cancion(1)]
    c.refrescar()
    assert c.fiesta["version"] == 10 and c.fiesta["cola"] == []


def test_error_al_crear(app, monkeypatch):
    monkeypatch.setattr(F.ControlFiesta, "_abrir_canal", lambda self: None)
    ctx = Ctx()

    def mal(*_a):
        raise F.ErrorFiesta("Ahora mismo hay demasiadas fiestas nuevas. Prueba de nuevo en unos minutos.")
    c = F.ControlFiesta(ctx, api={"crear": mal}, en_fondo=en_el_acto)
    errores = []
    c.error.connect(errores.append)
    c.crear("x", 5)
    assert errores and "demasiadas fiestas" in errores[0] and c.codigo is None and not c.creando


def test_mensaje_del_tiempo_real_refresca(montaje):
    _ctx, base, c = montaje
    c.crear("", 5)
    n = sum(1 for x in base.llamadas if x[0] == "ver")
    c._al_mensaje("cambio", {"version": 99})
    c._al_mensaje("otro", {"version": 100})
    c._al_mensaje("cambio", {"version": 0})                    # vieja: no
    assert sum(1 for x in base.llamadas if x[0] == "ver") == n + 1


# ================================================================ pantalla

def test_pantalla(montaje, app, monkeypatch):
    from descargador.ui.paginas import fiesta as P
    ctx, base, c = montaje
    c.poner_auto(False)
    p = P.PaginaFiesta(ctx, control=c)
    assert p.pilas.currentIndex() == 0
    p.campo_nombre.setText("Cumple de Lu")
    p.campo_limite.setValue(3)
    p.bt_crear.click()
    assert base.llamadas[0] == ("crear", "Cumple de Lu", 3)
    assert p.pilas.currentIndex() == 1
    assert p.et_codigo.text() == "ABC234"
    assert p.lienzo_qr.texto == c.enlace and len(p.lienzo_qr.matriz) == 33
    assert p.et_nombre.text() == "Cumple de Lu" and "2 personas" in p.et_gente.text()
    assert p.limite_vivo.value() == 3 and "3 canciones" in p.et_limite.text()
    p.lienzo_qr.grab()                                         # se dibuja sin fallar
    # la cola con sus botones
    base.cola = [cancion(1, 0), cancion(2, 4, nombre="Beto")]
    c.refrescar()
    filas = [p.lista.itemAt(i).widget() for i in range(p.lista.count()) if p.lista.itemAt(i).widget()]
    assert len(filas) == 2
    textos = [l.text() for l in filas[0].findChildren(P.QLabel)]
    assert "Canción 2" in textos and any("Beto" in t for t in textos) and "♥ 4" in textos
    botones = {b.text(): b for b in filas[1].findChildren(P.QPushButton)}
    botones["Quitar"].click()
    assert ("quitar", 1) in base.llamadas
    filas = [p.lista.itemAt(i).widget() for i in range(p.lista.count()) if p.lista.itemAt(i).widget()]
    {b.text(): b for b in filas[0].findChildren(P.QPushButton)}["Poner ahora"].click()
    assert ctx.reproductor.hechos[-1][0:2] == ("ya", 2)
    # lo que suena
    base.f["sonando"] = {"titulo": "Suena ya", "artista": "Alguien", "nombre": "Beto", "pausa": False}
    base.f["version"] += 1
    c.refrescar()
    assert p.et_titulo.text() == "Suena ya" and "Beto" in p.et_artista.text()
    # copiar enlace
    p.bt_copiar.click()
    assert QApplication.clipboard().text() == c.enlace and "Enlace de la fiesta copiado" in ctx.avisos
    # límite en vivo
    p.limite_vivo.setValue(0)
    p.limite_vivo.editingFinished.emit()
    assert base.f["limite"] == 0 and "Sin límite" in p.et_limite.text()
    # cerrar (se confirma)
    monkeypatch.setattr(P.QMessageBox, "question", lambda *a, **k: P.QMessageBox.Yes)
    p.bt_cerrar.click()
    assert p.pilas.currentIndex() == 2
    # otra fiesta
    p.pilas.widget(2).findChild(P.QPushButton).click()
    assert p.pilas.currentIndex() == 0


def test_pantalla_error(app, monkeypatch):
    from descargador.ui.paginas import fiesta as P
    monkeypatch.setattr(F.ControlFiesta, "_abrir_canal", lambda self: None)
    ctx = Ctx()

    def mal(*_a):
        raise F.ErrorFiesta("La fiesta todavía no está activa en el servidor de Caudal.")
    c = F.ControlFiesta(ctx, api={"crear": mal}, en_fondo=en_el_acto)
    p = P.PaginaFiesta(ctx, control=c)
    p.bt_crear.click()
    assert not p.et_error.isHidden() and "todavía no está activa" in p.et_error.text()
    assert p.pilas.currentIndex() == 0 and p.bt_crear.isEnabled()
