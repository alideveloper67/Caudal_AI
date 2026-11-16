# -*- coding: utf-8 -*-
"""Modo estudio: perfiles, temporizador, constancia, notas, sonidos fabricados, salida
protegida y las dos pantallas. Sin ventanas a la vista (Qt offscreen), sin internet y sin
audio real: los motores de mpv son dobles y los datos van a una carpeta temporal."""

import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QObject, Qt, Signal  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget  # noqa: E402

from descargador import estudio as E  # noqa: E402
from descargador import sonidos_ambiente as SA  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_estudio")
os.makedirs(CAPTURAS, exist_ok=True)

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class Reloj:
    """Un reloj que avanza solo cuando se le dice."""

    def __init__(self, inicio=None):
        self.t = inicio or datetime(2026, 11, 16, 10, 0, 0).timestamp()

    def __call__(self):
        return self.t

    def pasar(self, segundos):
        self.t += segundos


# ====================================================================== dobles

class RFalso(QObject):
    estado_cambio = Signal(str)
    pista_cambio = Signal(object)

    def __init__(self):
        super().__init__()
        self.estado = "parado"
        self.actual = None
        self.volumen = 80
        self.repetir = "no"
        self.aleatorio = False
        self.factores = []
        self.llamadas = []
        self.listas = []

    def _poner_factor_suave(self, f):
        self.factores.append(round(f, 3))

    def reproducir_lista(self, pistas, inicio=0, contexto=None, aleatorio=None, modo=None, **kw):
        self.listas.append((list(pistas), contexto, aleatorio))
        self.actual = pistas[0]
        self.estado = "sonando"
        self.estado_cambio.emit("sonando")

    def pausar(self):
        self.estado = "pausa"
        self.llamadas.append("pausar")
        self.estado_cambio.emit("pausa")

    def reanudar(self):
        self.estado = "sonando"
        self.llamadas.append("reanudar")
        self.estado_cambio.emit("sonando")

    def alternar(self):
        self.llamadas.append("alternar")
        (self.pausar if self.estado == "sonando" else self.reanudar)()

    def siguiente(self):
        self.llamadas.append("siguiente")

    def fijar_volumen(self, v):
        self.volumen = int(v)
        self.llamadas.append(("volumen", int(v)))


class Aj(dict):
    def __missing__(self, k):
        return {"crossfade": 0, "mezcla_dj": True, "autoplay": True, "repetir": "no",
                "aleatorio": False, "volumen": 80}.get(k)

    def guardar(self):
        pass


class CtxFalso(QObject):
    aviso = Signal(str)

    def __init__(self):
        super().__init__()
        self.reproductor = RFalso()
        self.ajustes = Aj()
        self.ventana = None
        self.estudio = None
        self.navegaciones = []

    def navegar(self, d):
        self.navegaciones.append(d)


class MotorFalso:
    def __init__(self, nombre):
        self.nombre = nombre
        self.llamadas = []
        self.cerrado = False

    def reproducir(self, ruta, volumen, bucle=True):
        self.llamadas.append(("reproducir", os.path.basename(ruta), round(volumen, 2), bucle))

    def fijar_volumen(self, v):
        self.llamadas.append(("volumen", round(v, 2)))

    def detener(self):
        self.llamadas.append(("detener",))

    def cerrar(self):
        self.cerrado = True


def esperar(app, cond, que, maximo=15):
    import time
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.02)


@pytest.fixture
def datos(tmp_path):
    return tmp_path


def hacer(app, datos, reloj=None, segundos_sonido=3, buscar=None):
    """Un controlador con reloj propio, motores falsos y sonidos cortos."""
    reloj = reloj or Reloj()
    ctx = CtxFalso()
    motores = {}

    def fabrica(nombre):
        motores[nombre] = MotorFalso(nombre)
        return motores[nombre]
    mez = SA.Mezclador(None, fabrica, SA.Generador(datos / "amb", segundos=segundos_sonido, empalme=1.0))
    llamadas = []
    ctrl = E.ControladorEstudio(ctx, carpeta=datos, reloj=reloj, mezclador=mez, buscar=buscar,
                                despierto=lambda b: llamadas.append(b))
    ctx.estudio = ctrl
    ctrl._motores = motores
    ctrl._despierto_llamadas = llamadas
    return ctx, ctrl, reloj


# ====================================================================== perfiles y catálogo

def pista(vid, titulo, artista="Alguien", dur=200, **kw):
    return {"tipo": "pista", "clave": f"yt:{vid}", "video_id": vid, "titulo": titulo,
            "artista": artista, "duracion": dur, **kw}


def test_perfiles_estan_completos():
    assert list(E.PERFILES) == ["leer", "programar", "repasar", "relajarme"]
    assert E.PERFILES["leer"]["nombre"] == "Leer / Escribir"
    assert E.PERFILES["programar"]["nombre"] == "Programar / Analizar"
    assert E.PERFILES["repasar"]["nombre"] == "Repasar / Memorizar"
    assert E.PERFILES["relajarme"]["nombre"] == "Relajarme"
    for p in E.PERFILES.values():
        assert len(p["consultas"]) >= 3 and p["lema"] and p["detalle"]
        assert set(p["mezcla"]) <= set(E.CAPAS_ORDEN)
    assert "lofi" in " ".join(E.PERFILES["leer"]["consultas"]).lower()
    assert "synthwave" in " ".join(E.PERFILES["programar"]["consultas"]).lower()
    assert "baroque" in " ".join(E.PERFILES["repasar"]["consultas"]).lower()


def test_filtro_anti_vocales_prefiere_instrumental_y_excluye_con_alternativas():
    buenas = [pista(f"b{i}", f"Lofi piano instrumental {i}") for i in range(9)]
    malas = [pista("m1", "Canción (Official Video)"), pista("m2", "Tema feat. Otro"),
             pista("m3", "Letra de mi canción"), pista("m4", "Hit ft. Alguien"),
             pista("m5", "Song lyrics")]
    neutras = [pista("n1", "Ocean Drive")]
    sal = E.filtrar_pistas(malas[:2] + neutras + buenas + malas[2:])
    ids = [p["video_id"] for p in sal]
    assert not any(i.startswith("m") for i in ids)           # hay alternativas: ninguna con voz
    assert ids.index("n1") > ids.index("b8")                 # lo neutro va detrás de lo instrumental
    assert E.puntaje_instrumental(malas[0]) < 0 < E.puntaje_instrumental(buenas[0])


def test_filtro_usa_lo_con_voz_solo_si_no_hay_mas():
    buenas = [pista("b1", "Piano study"), pista("b2", "Ambient focus")]
    malas = [pista("m1", "Algo (Official Video)"), pista("m2", "Otro ft. X")]
    sal = E.filtrar_pistas(buenas + malas, minimo=4)
    assert [p["video_id"] for p in sal][:2] == ["b1", "b2"] and len(sal) == 4
    sal = E.filtrar_pistas(buenas + malas, minimo=2)
    assert [p["video_id"] for p in sal] == ["b1", "b2"]


def test_cola_del_perfil_mezcla_consultas_sin_repetir_y_tolera_fallos():
    pedidas = []

    def buscar(texto):
        pedidas.append(texto)
        if len(pedidas) == 2:
            raise OSError("sin red")
        k = len(pedidas)
        return [pista(f"q{k}_{i}", f"Ambient piano {k}-{i}") for i in range(5)] + [pista("rep", "Piano study")]
    cola = E.cola_del_perfil("leer", buscar)
    assert pedidas == E.PERFILES["leer"]["consultas"]
    ids = [p["video_id"] for p in cola]
    assert len(ids) == len(set(ids)) and "rep" in ids
    assert ids[0].startswith("q1_") and ids[1].startswith("q3_")   # por turnos entre consultas
    assert E.cola_del_perfil("desconocido", lambda t: [pista("x", "Piano")])   # no rompe


# ====================================================================== temporizador

def test_temporizador_usa_la_hora_de_fin_y_hace_rondas():
    reloj = Reloj()
    t = E.Temporizador(reloj)
    t.configurar(25, 5, rondas=3, largo=15, cada=2)
    t.iniciar()
    assert t.fase == "enfoque" and t.ronda == 1 and t.restante() == 25 * 60
    reloj.pasar(25 * 60 - 1)
    assert t.revisar() == [] and 0.9 < t.restante() < 1.1
    reloj.pasar(1)
    (ev,) = t.revisar()
    assert ev["tipo"] == "fin_enfoque" and ev["siguiente"] == "descanso" and ev["ronda"] == 1
    assert t.fase == "descanso" and t.restante() == 5 * 60
    reloj.pasar(5 * 60)
    (ev,) = t.revisar()
    assert ev["tipo"] == "fin_descanso" and t.fase == "enfoque" and t.ronda == 2
    reloj.pasar(25 * 60)
    (ev,) = t.revisar()
    assert ev["siguiente"] == "descanso_largo" and t.restante() == 15 * 60   # tras la ronda 2 (cada 2)
    reloj.pasar(15 * 60)
    t.revisar()
    assert t.fase == "enfoque" and t.ronda == 3
    reloj.pasar(25 * 60)
    (ev,) = t.revisar()
    assert ev["completa"] and t.fase == "completo" and not t.activo()
    assert t.enfocado_total() == pytest.approx(75 * 60)


def test_temporizador_pausa_no_gasta_tiempo_y_el_sueno_no_dispara_varias_campanas():
    reloj = Reloj()
    t = E.Temporizador(reloj)
    t.configurar(50, 10, rondas=4)
    t.iniciar()
    reloj.pasar(600)
    t.pausar()
    reloj.pasar(3600)                  # una hora en pausa
    assert t.revisar() == [] and t.restante() == pytest.approx(40 * 60)
    t.reanudar()
    reloj.pasar(40 * 60)
    assert len(t.revisar()) == 1
    # el equipo se duerme tres horas durante el descanso: un solo cambio, no cuatro
    reloj.pasar(3 * 3600)
    evs = t.revisar()
    assert len(evs) == 1 and evs[0]["tipo"] == "fin_descanso"
    assert t.fase == "enfoque" and t.restante() == pytest.approx(50 * 60)
    assert t.revisar() == []


def test_temporizador_saltar_y_terminar_cuentan_lo_enfocado():
    reloj = Reloj()
    t = E.Temporizador(reloj)
    t.configurar(25, 5, rondas=2)
    t.iniciar()
    reloj.pasar(10 * 60)
    (ev,) = t.saltar()
    assert ev["segundos"] == pytest.approx(600) and t.fase == "descanso"
    assert t.enfocado_total() == pytest.approx(600)
    t.saltar()                       # el descanso se salta: empieza la ronda 2
    assert t.fase == "enfoque" and t.ronda == 2 and t.enfocado_total() == pytest.approx(600)
    reloj.pasar(5 * 60)
    assert t.enfocado_total() == pytest.approx(900)
    assert t.terminar() == pytest.approx(900) and t.fase == "inactivo"


def test_formatos_de_tiempo():
    assert E.formato_reloj(1500) == "25:00" and E.formato_reloj(0.2) == "00:01"
    assert E.formato_reloj(0) == "00:00" and E.formato_reloj(5400) == "1:30:00"
    assert E.formato_duracion(0) == "0 min" and E.formato_duracion(30) == "Menos de 1 min"
    assert E.formato_duracion(2700) == "45 min" and E.formato_duracion(5100) == "1 h 25 min"


# ====================================================================== constancia y notas

def test_estadisticas_dias_semana_y_racha(datos):
    reloj = Reloj()
    est = E.Estadisticas(datos / "h.json", reloj)
    hoy = est.hoy_fecha()
    assert est.racha() == 0 and "Cuando quieras" in est.frase()
    for atras in (3, 2, 1):          # tres días seguidos antes de hoy
        est.sumar(30 * 60, hoy - timedelta(days=atras))
    assert est.hoy() == 0
    assert est.racha() == 3                       # hoy aún no estudiaste: la racha de ayer sigue viva
    assert "3 días seguidos" in est.frase() and "calma" in est.frase()
    est.sumar(1200)                               # hoy 20 min
    assert est.racha() == 4 and est.hoy() == 1200 and est.semana() == 3 * 1800 + 1200
    est.sumar(3 * 60, hoy - timedelta(days=5))    # menos de 5 min no cuenta como día
    est.sumar(3 * 60, hoy - timedelta(days=4))
    assert est.racha() == 4
    est.sumar(10 * 60, hoy - timedelta(days=4))   # ahora sí: 13 min
    assert est.racha() == 5
    assert est.mejor_racha() == 5
    ultimos = est.ultimos_dias(7)
    assert len(ultimos) == 7 and ultimos[-1] == (hoy, 1200)
    # un hueco rompe la racha cuando pasa el día completo
    reloj.pasar(2 * 86400)
    assert est.racha() == 0
    # se guarda y se recupera
    otra = E.Estadisticas(datos / "h.json", reloj)
    assert otra.dias == est.dias


def test_estadisticas_nunca_regaña(datos):
    est = E.Estadisticas(datos / "h2.json", Reloj())
    prohibidas = ("debes", "meta", "fallaste", "perdiste", "no has", "tienes que", "deberías", "culpa")
    textos = [est.frase()]
    est.sumar(40 * 60)
    textos.append(est.frase())
    for dias in (2, 8):
        for i in range(1, dias):
            est.sumar(1800, est.hoy_fecha() - timedelta(days=i))
        textos.append(est.frase())
    for t in textos:
        assert t and not any(p in t.lower() for p in prohibidas), t


def test_notas_con_fecha_copiar_y_borrar(datos):
    reloj = Reloj()
    n = E.Notas(datos / "n.json", reloj)
    assert n.anadir("   ") is None
    a = n.anadir("Llamar al banco")
    reloj.pasar(60)
    b = n.anadir("Revisar capítulo 3")
    assert [x["texto"] for x in n.todas()] == ["Revisar capítulo 3", "Llamar al banco"]
    assert a["fecha"] < b["fecha"] and E.fecha_amable(b["fecha"], datetime.fromtimestamp(reloj())) == "Hoy, 10:01"
    assert E.fecha_amable(a["fecha"], datetime.fromtimestamp(reloj()) + timedelta(days=1)).startswith("Ayer")
    assert E.fecha_amable("2026-03-05T18:20:00", datetime(2026, 11, 16)) == "5 mar, 18:20"
    assert E.Notas(datos / "n.json").todas() == n.todas()                    # local y persistente
    assert n.borrar(a["id"]) and not n.borrar("no-existe")
    assert [x["texto"] for x in n.todas()] == ["Revisar capítulo 3"]
    n.deshacer_borrado(a)
    assert [x["texto"] for x in n.todas()] == ["Revisar capítulo 3", "Llamar al banco"]


def test_configuracion_valida_y_guarda(datos):
    c = E.Configuracion(datos / "c.json")
    assert c["pomodoro"] == "25/5" and c["enfoque_min"] == 25 and c["al_descansar"] == "bajar"
    c["pomodoro"] = "90/15"
    c["rondas"] = 99
    c["al_descansar"] = "nada"
    c["capas"] = {"lluvia": {"on": True, "vol": 140}, "xyz": {"on": True}}
    c.guardar()
    d = E.Configuracion(datos / "c.json")
    assert (d["enfoque_min"], d["descanso_min"], d["rondas"]) == (90, 15, 12)
    assert d["al_descansar"] == "bajar" and d["capas"] == {"lluvia": {"on": True, "vol": 100}}


# ====================================================================== síntesis

@pytest.fixture(scope="module")
def sonidos():
    """Los siete sonidos, fabricados una sola vez para todas las pruebas."""
    return {c: SA.fabricar(c) for c, _n, _d in SA.CAPAS}


def _pendiente(x, f1=100, f2=8000):
    a = np.array(x, dtype=float)
    f = np.fft.rfftfreq(len(a), 1 / SA.FRECUENCIA)
    pot = np.abs(np.fft.rfft(a * np.hanning(len(a)))) ** 2
    m = (f > f1) & (f < f2)
    return float(np.polyfit(np.log10(f[m]), np.log10(pot[m]), 1)[0])


@pytest.mark.parametrize("capa", [c for c, _n, _d in SA.CAPAS])
def test_sonido_longitud_sin_recortes_y_bucle_sin_clic(sonidos, capa, tmp_path):
    x = sonidos[capa]
    assert len(x) == int(SA.DURACION * SA.FRECUENCIA) and 20 <= SA.DURACION <= 30
    ruta = tmp_path / f"{capa}.wav"
    SA.guardar_wav(ruta, x)
    leido, frec, canales, bits = SA.leer_wav(ruta)
    assert (frec, canales, bits) == (22050, 1, 16) and list(leido[:50]) == list(x[:50])
    assert max(abs(v) for v in x) < 0.9 * 32767                 # sin recortes
    assert sum(1 for v in x if abs(v) >= 32767) == 0
    media = sum(x) / len(x)
    assert abs(media) < 0.01 * 32767                            # sin desplazamiento
    # bucle: del final al principio no hay un salto mayor que los de dentro del sonido
    a = [float(v) for v in x]
    difs = [abs(a[i + 1] - a[i]) for i in range(len(a) - 1)]
    sd = (sum(d * d for d in difs) / len(difs)) ** 0.5
    union = abs(a[0] - a[-1])
    assert union <= 4.5 * sd, (capa, union, sd)
    cola_y_cabeza = a[-6:] + a[:6]
    assert max(abs(cola_y_cabeza[i + 1] - cola_y_cabeza[i]) for i in range(len(cola_y_cabeza) - 1)) <= 5.5 * sd
    # y suena a algo: nivel razonable
    rms = (sum(v * v for v in a) / len(a)) ** 0.5 / 32767
    assert 0.08 < rms < 0.25


@pytest.mark.skipif(np is None, reason="hace falta numpy para medir el espectro")
def test_pendiente_espectral_del_blanco_rosa_y_marron(sonidos):
    blanco, rosa, marron = (_pendiente(sonidos[c]) for c in ("blanco", "rosa", "marron"))
    assert abs(blanco) < 0.2                 # plano
    assert -1.35 < rosa < -0.75              # -3 dB por octava ≈ -1 en potencia
    assert -2.3 < marron < -1.6              # -6 dB por octava ≈ -2
    assert blanco > rosa > marron
    # la lluvia es más aguda que la chimenea y el bosque tiene más graves que la lluvia
    assert _pendiente(sonidos["lluvia"]) > _pendiente(sonidos["chimenea"])
    assert _pendiente(sonidos["bosque"]) < _pendiente(sonidos["lluvia"])


def test_los_sonidos_con_eventos_tienen_eventos(sonidos):
    for capa in ("lluvia", "chimenea", "cafeteria", "bosque"):
        a = np.array(sonidos[capa], dtype=float) if np is not None else None
        if a is None:
            continue
        bloques = a[: len(a) // 22050 * 22050].reshape(-1, 22050)
        energia = (bloques ** 2).mean(axis=1)
        assert energia.max() / energia.min() > 1.04, capa      # no es un ruido plano


def test_campana_suave_y_sin_clic():
    x = SA.campana()
    assert 3 <= len(x) / SA.FRECUENCIA <= 5
    assert abs(x[0]) < 400 and abs(x[-1]) < 20                  # entra y sale sin golpe
    assert max(abs(v) for v in x) < 0.7 * 32767
    assert max(abs(v) for v in x[:200]) < max(abs(v) for v in x)


def test_generador_guarda_en_cache_y_la_reutiliza(datos):
    g = SA.Generador(datos / "c", segundos=2, empalme=0.5)
    r1 = g.asegurar("rosa")
    t1 = os.path.getmtime(r1)
    assert g.asegurar("rosa") == r1 and os.path.getmtime(r1) == t1
    muestras, frec, canales, bits = SA.leer_wav(r1)
    assert len(muestras) == 2 * 22050 and (frec, canales, bits) == (22050, 1, 16)


# ====================================================================== mezclador

def test_mezclador_capas_independientes_y_bucle(app, datos):
    ctx, ctrl, _ = hacer(app, datos)
    m = ctrl.mezclador
    m.encender("lluvia", True)
    m.encender("rosa", True)
    esperar(app, lambda: {"lluvia", "rosa"} <= set(ctrl._motores), "se prepararon dos sonidos")
    m.volumen("lluvia", 80)
    m.volumen("rosa", 20)
    rep = [x for x in ctrl._motores["lluvia"].llamadas if x[0] == "reproducir"]
    assert rep and rep[0][3] is True and rep[0][1].startswith("lluvia")        # en bucle
    assert ctrl._motores["lluvia"] is not ctrl._motores["rosa"]               # un motor por sonido
    assert ctrl._motores["lluvia"].llamadas[-1][0] == "volumen"
    v1, v2 = ctrl._motores["lluvia"].llamadas[-1][1], ctrl._motores["rosa"].llamadas[-1][1]
    assert v1 > v2 > 0                                                          # volumen propio
    m.encender("lluvia", False)
    assert ctrl._motores["lluvia"].llamadas[-1] == ("detener",)
    assert m.activas() == ["rosa"]
    m.aplicar_mezcla({"bosque": 30, "chimenea": 15})
    assert sorted(m.activas()) == ["bosque", "chimenea"]
    assert ctrl._motores["rosa"].llamadas[-1] == ("detener",)
    m.apagar_todo()
    assert m.activas() == []
    m.tocar_campana(0.8)
    assert "campana" in ctrl._motores and ctrl._motores["campana"] is not ctrl._motores.get("lluvia")
    c = [x for x in ctrl._motores["campana"].llamadas if x[0] == "reproducir"][0]
    assert c[3] is False                                                        # la campana no se repite


def test_lo_elegido_se_guarda(app, datos):
    ctx, ctrl, _ = hacer(app, datos)
    ctrl.mezclador.volumen("bosque", 33)
    ctrl.poner(al_descansar="pausar", candado=True, brillo=70)
    ctrl.elegir_perfil("programar")
    ctx2, ctrl2, _ = hacer(app, datos)
    assert ctrl2.cfg["al_descansar"] == "pausar" and ctrl2.cfg["candado"] and ctrl2.cfg["perfil"] == "programar"
    assert ctrl2.mezclador.estado["bosque"]["vol"] == 33
    assert not ctrl2.mezclador.hay_algo_encendido()          # los sonidos no arrancan solos


def test_perfil_pone_su_mezcla_sugerida(app, datos):
    ctx, ctrl, _ = hacer(app, datos)
    ctrl.elegir_perfil("relajarme")
    assert set(ctrl.mezclador.activas()) == {"lluvia", "chimenea", "bosque"}
    assert ctrl.mezclador.estado["lluvia"]["vol"] == E.PERFILES["relajarme"]["mezcla"]["lluvia"]
    ctrl.poner(mezcla_del_perfil=False)
    ctrl.mezclador.apagar_todo()
    ctrl.elegir_perfil("leer")
    assert ctrl.mezclador.activas() == []


# ====================================================================== sesión completa

def _pistas(n=12):
    return [pista(f"v{i}", f"Piano focus {i}") for i in range(n)]


def _con_musica(app, datos, **kw):
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(5), **kw)
    ctrl.empezar()
    esperar(app, lambda: ctx.reproductor.listas, "se puso a sonar la cola del perfil")
    return ctx, ctrl, reloj


def test_empezar_pone_cola_propia_sin_radio_ni_mezcla_dj_y_restaura(app, datos):
    ctx, ctrl, reloj = _con_musica(app, datos)
    pistas, contexto, aleatorio = ctx.reproductor.listas[0]
    assert contexto["tipo"] == "estudio" and contexto["id"] == "leer" and aleatorio is False
    assert ctx.ajustes["crossfade"] == 5 and ctx.ajustes["mezcla_dj"] is False   # fundido suave, sin DJ
    assert ctx.ajustes["autoplay"] is False and ctx.ajustes["repetir"] == "todo"  # sin radio de relleno
    assert ctx.reproductor.repetir == "todo" and ctx.reproductor.aleatorio is False
    assert all("Official" not in p["titulo"] for p in pistas)
    assert ctrl.mezclador.hay_algo_encendido()                                   # la mezcla del perfil
    assert ctrl.hay_bloque() and ctrl.fase() == "enfoque"
    assert ctrl._despierto_llamadas == []                                        # no pedido: no se pide
    ctrl.terminar()
    assert ctx.ajustes["crossfade"] == 0 and ctx.ajustes["mezcla_dj"] is True
    assert ctx.ajustes["autoplay"] is True and ctx.ajustes["repetir"] == "no"
    assert ctx.reproductor.repetir == "no" and not ctrl.mezclador.hay_algo_encendido()
    assert ctx.reproductor.factores[-1] == 1.0 and not ctrl.hay_bloque()


@pytest.mark.parametrize("accion", ["bajar", "pausar", "seguir"])
def test_fin_de_bloque_campana_aviso_y_musica(app, datos, accion):
    ctx, ctrl, reloj = _con_musica(app, datos)
    ctrl.poner(al_descansar=accion, atenuar=True)
    avisos, eventos = [], []
    ctrl.aviso.connect(avisos.append)
    ctrl.bloque_terminado.connect(eventos.append)
    ctrl._pasos, ctrl.pasos_fundido = [], 2
    ctrl.temporizador.configurar(25, 5, rondas=3)
    ctrl.temporizador.iniciar()
    ctrl._aplicar_musica()
    while ctrl._pasos:
        ctrl._paso_fundido()
    assert ctx.reproductor.factores[-1] == pytest.approx(0.65)                  # atenuada en el enfoque
    reloj.pasar(25 * 60)
    ctrl.revisar()
    while ctrl._pasos:
        ctrl._paso_fundido()
    assert [e["tipo"] for e in eventos] == ["fin_enfoque"] and ctrl.fase() == "descanso"
    assert "campana" in ctrl._motores and any(x[0] == "reproducir" for x in ctrl._motores["campana"].llamadas)
    assert avisos and "descans" in avisos[-1].lower() and "5 min" in avisos[-1]
    if accion == "bajar":
        assert ctx.reproductor.factores[-1] == pytest.approx(0.30)
    elif accion == "pausar":
        assert ctx.reproductor.estado == "pausa" and ctx.reproductor.llamadas.count("pausar") == 1
    else:
        assert ctx.reproductor.factores[-1] == pytest.approx(0.65) and ctx.reproductor.estado == "sonando"
    # el descanso acaba: vuelve el volumen (y la música, si se había pausado)
    reloj.pasar(5 * 60)
    ctrl.revisar()
    while ctrl._pasos:
        ctrl._paso_fundido()
    assert ctrl.fase() == "enfoque" and ctx.reproductor.estado == "sonando"
    assert ctx.reproductor.factores[-1] == pytest.approx(0.65)
    assert "ronda 2" in avisos[-1].lower()
    ctrl.terminar()
    assert ctx.reproductor.factores[-1] == 1.0


def test_sin_atenuar_el_enfoque_deja_el_volumen_entero(app, datos):
    ctx, ctrl, reloj = _con_musica(app, datos)
    ctrl.poner(atenuar=False)
    ctrl._pasos, ctrl.pasos_fundido = [], 1
    ctrl._aplicar_musica()
    while ctrl._pasos:
        ctrl._paso_fundido()
    assert ctrl.factor_enfoque() == 1.0 and ctx.reproductor.factores[-1] == 1.0


def test_sin_campana_no_suena_y_la_sesion_completa_se_anota(app, datos):
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))
    ctrl.poner(campana=False, enfoque_min=25, descanso_min=5, rondas=2)
    ctrl.empezar(solo_musica=False)
    esperar(app, lambda: ctx.reproductor.listas, "cola")
    avisos = []
    ctrl.aviso.connect(avisos.append)
    for _ in range(3):                         # enfoque, descanso, enfoque
        reloj.pasar(30 * 60)
        ctrl.revisar()
    assert "campana" not in ctrl._motores
    assert ctrl.temporizador.fase == "completo" and "2 rondas" in avisos[-1]
    assert ctrl.est.hoy() == 50 * 60
    assert len(ctrl.est.sesiones) == 1 and ctrl.est.sesiones[0]["segundos"] == 50 * 60
    ctrl.terminar()                            # terminar después de completar no duplica nada
    assert ctrl.est.hoy() == 50 * 60 and len(ctrl.est.sesiones) == 1


def test_lo_estudiado_se_guarda_mientras_pasa_y_al_terminar(app, datos):
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))
    ctrl.empezar()
    reloj.pasar(10 * 60)
    ctrl.revisar()
    assert ctrl.est.hoy() == 10 * 60                      # no espera al final del bloque
    ctrl.pausar_o_reanudar()
    reloj.pasar(30 * 60)
    ctrl.revisar()
    assert ctrl.est.hoy() == 10 * 60                      # en pausa no suma
    ctrl.pausar_o_reanudar()
    reloj.pasar(5 * 60)
    ctrl.terminar()
    assert ctrl.est.hoy() == 15 * 60 and ctrl.est.racha() == 1
    assert E.Estadisticas(datos / "estudio_historial.json", reloj).hoy() == 15 * 60


def test_mantener_despierto_solo_cuando_se_pide_y_se_suelta(app, datos):
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))
    ctrl.poner(despierto=True)
    assert ctrl._despierto_llamadas == []                 # sin sesión no hace falta
    ctrl.empezar()
    assert ctrl._despierto_llamadas[-1] & E.ES_DISPLAY_REQUIRED
    ctrl.terminar()
    assert ctrl._despierto_llamadas[-1] == E.ES_CONTINUOUS
    ctrl.vista_cambio(True)
    assert ctrl._despierto_llamadas[-1] & E.ES_SYSTEM_REQUIRED
    ctrl.vista_cambio(False)
    assert ctrl._despierto_llamadas[-1] == E.ES_CONTINUOUS


def test_sin_resultados_avisa_con_amabilidad(app, datos):
    ctx, ctrl, _ = hacer(app, datos, buscar=lambda t: [])
    avisos = []
    ctrl.aviso.connect(avisos.append)
    ctrl.reproducir_perfil()
    esperar(app, lambda: avisos, "aviso de sin música")
    assert "conexión" in avisos[0] and not ctx.reproductor.listas and not ctrl.cargando_cola


# ====================================================================== salida protegida

_MARCOS = []


def _marco(app):
    w = QWidget()
    w.resize(1000, 700)
    w.show()
    app.processEvents()
    _MARCOS.append(w)
    return w


@pytest.fixture(autouse=True)
def limpiar_ventanas(app):
    """Cada prueba deja sus ventanas bien cerradas y sin borrados pendientes: así lo que
    una prueba deja a medias no se desploma dentro de la siguiente."""
    yield
    from PySide6.QtCore import QCoreApplication, QEvent
    for w in list(_MARCOS):
        try:
            w.close()
            w.deleteLater()
        except RuntimeError:
            pass
    _MARCOS.clear()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def test_confirmar_salida_seguir_y_salir(app, datos):
    from descargador.ui.estudio_enfoque import confirmar_salida
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))
    ctrl.empezar()
    marco = _marco(app)
    hechas = []
    c = confirmar_salida(marco, ctrl, lambda: hechas.append("fuera"))
    app.processEvents()
    textos = " | ".join(l.text() for l in c.findChildren(QLabel))
    assert "¿Salir de tu sesión de estudio?" in textos
    botones = {b.text(): b for b in c.findChildren(QPushButton)}
    assert set(botones) == {"Seguir estudiando", "Salir"}
    assert confirmar_salida(marco, ctrl, None) is c                       # no se duplica
    botones["Seguir estudiando"].click()
    app.processEvents()
    assert ctrl.hay_bloque() and hechas == []
    c2 = confirmar_salida(marco, ctrl, lambda: hechas.append("fuera"))
    {b.text(): b for b in c2.findChildren(QPushButton)}["Salir"].click()
    app.processEvents()
    assert not ctrl.hay_bloque() and hechas == ["fuera"] and not ctrl.activo


def test_confirmar_salida_con_candado_hay_que_mantener(app, datos):
    from descargador.ui.estudio_piezas import ConfirmaSalida
    marco = _marco(app)
    t = Reloj(1000.0)
    hechos = []
    c = ConfirmaSalida(marco, candado=True, resumen="x", segundos=2.0, reloj=t)
    c.salir.connect(lambda: hechos.append("salir"))
    b = c.bt_salir
    assert "Mantén pulsado" in b.text()
    b.comenzar()
    t.pasar(1.0)
    b._paso()
    assert 0.45 < b.progreso < 0.55 and hechos == []
    b.soltar()                      # soltar antes de tiempo no sale
    t.pasar(5)
    b._paso()
    assert hechos == [] and b.progreso == 0
    b.comenzar()
    t.pasar(2.05)
    b._paso()
    assert hechos == ["salir"]


def test_esc_de_la_vista_cierra_primero_lo_emergente_y_luego_pide_salir(app, datos):
    from descargador.ui.estudio_enfoque import VistaEnfoque
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))
    marco = _marco(app)
    v = VistaEnfoque(ctx, marco, ctrl)
    v.abrir()
    app.processEvents()
    assert v.isVisible() and ctrl.vista_abierta
    # sin bloque en curso se sale sin preguntar
    v.pedir_salida()
    assert not v.isVisible() and not ctrl.vista_abierta
    ctrl.empezar()
    v.abrir()
    v.alternar_notas()
    assert v.panel_notas.isVisible()
    v.escape()
    assert not v.panel_notas.isVisible() and v.isVisible()
    v.alternar_mezcla()
    assert v.caja_mezcla.isVisible()
    v.escape()
    assert not v.caja_mezcla.isVisible() and v.isVisible()
    v.escape()                                                  # ahora sí: pregunta
    app.processEvents()
    c = v._confirma_estudio
    assert c.isVisible() and v.isVisible() and ctrl.hay_bloque()
    v.escape()                                                  # Esc en el aviso = seguir estudiando
    app.processEvents()
    assert v._confirma_estudio is None and ctrl.hay_bloque() and v.isVisible()
    v.bt_cerrar.click()
    app.processEvents()
    {b.text(): b for b in v._confirma_estudio.findChildren(QPushButton)}["Salir"].click()
    app.processEvents()
    assert not v.isVisible() and not ctrl.hay_bloque()


def test_notas_del_panel_guardan_copian_y_borran(app, datos):
    from descargador.ui.estudio_piezas import PanelNotas
    ctx, ctrl, _ = hacer(app, datos)
    marco = _marco(app)
    p = PanelNotas(ctrl, marco)
    p.abrir()
    app.processEvents()
    assert "Aún no hay ideas" in " ".join(l.text() for l in p.findChildren(QLabel))
    p.campo.setPlainText("Preguntar por la beca")
    QTest.keyClick(p.campo, Qt.Key_Return, Qt.ControlModifier)               # Ctrl+Intro
    app.processEvents()
    assert [n["texto"] for n in ctrl.notas.todas()] == ["Preguntar por la beca"]
    assert p.campo.toPlainText() == ""
    tarjetas = p.findChildren(QWidget, "nota_estudio")
    assert len(tarjetas) == 1
    tarjetas[0].bt_copiar.click()
    assert QApplication.clipboard().text() == "Preguntar por la beca"
    tarjetas[0].bt_borrar.click()
    app.processEvents()
    assert ctrl.notas.todas() == [] and "Deshacer" in p.deshacer.text()
    p.deshacer.click()
    assert len(ctrl.notas.todas()) == 1
    p.cerrar()
    assert not p.isVisible()


# ====================================================================== capturas

def _ctrl_demo(app, datos):
    ctx, ctrl, reloj = hacer(app, datos, buscar=lambda t: _pistas(4))     # sin red
    ctx.reproductor.actual = pista("d1", "Moonlight Drive (piano)", "Lofi Lab")
    ctx.reproductor.estado = "sonando"
    est = ctrl.est
    hoy = est.hoy_fecha()
    for atras, m in ((6, 25), (5, 50), (3, 40), (2, 75), (1, 55)):
        est.sumar(m * 60, hoy - timedelta(days=atras))
    est.sumar(42 * 60)
    ctrl.notas.anadir("Revisar la bibliografía del capítulo 4")
    ctrl.notas.anadir("Preguntar a la profesora por la fecha de entrega")
    return ctx, ctrl, reloj


def _pagina(app, datos, ancho, alto, nombre, sesion=False, fondo=False):
    from descargador.ui import estilos
    from descargador.ui.paginas.estudio import PaginaEstudio
    estilos.aplicar_aspecto("cian", "oscuro")
    estilos.FONDO["activo"] = fondo
    ctx, ctrl, reloj = _ctrl_demo(app, datos)
    ctrl.mezclador.aplicar_mezcla({"lluvia": 40, "chimenea": 20})
    esperar(app, lambda: not ctrl.mezclador.esta_preparando(), "sonidos listos", 20)
    marco = QWidget()
    marco.setObjectName("raiz")
    marco.setStyleSheet(estilos.hoja({}))
    marco.resize(ancho, alto)
    from PySide6.QtWidgets import QVBoxLayout
    lay = QVBoxLayout(marco)
    lay.setContentsMargins(0, 0, 0, 0)
    pag = PaginaEstudio(ctx)
    lay.addWidget(pag)
    ctx.ventana = None
    if sesion:
        ctrl.empezar()
        reloj.pasar(7 * 60 + 12)
        ctrl.revisar()
    marco.show()
    app.processEvents()
    app.processEvents()
    marco.grab().save(os.path.join(CAPTURAS, nombre))
    estilos.FONDO["activo"] = False
    return ctx, ctrl, pag, marco


def test_captura_pagina_de_seleccion(app, datos):
    ctx, ctrl, pag, marco = _pagina(app, datos, 1280, 800, "pagina_1280x800.png")
    assert sum(1 for t in pag.tarjetas.values() if t.seleccionada) == 1
    assert pag.tarjetas["leer"].seleccionada
    ctrl.elegir_perfil("repasar")
    assert pag.tarjetas["repasar"].seleccionada and not pag.tarjetas["leer"].seleccionada
    assert not pag.banner.isVisible()
    pag.bt_empezar.click()
    assert ctrl.hay_bloque() and pag.banner.isVisible()
    for sp in pag.sp.values():
        assert not sp.isEnabled()
    marco.close()


def test_captura_pagina_estrecha_y_con_sesion(app, datos):
    ctx, ctrl, pag, marco = _pagina(app, datos, 720, 900, "pagina_720.png", sesion=True)
    assert pag.banner.isVisible() and "ENFOQUE" in pag.banner.fase.text()
    assert pag.banner.tiempo.text() == "17:48"
    assert pag.bt_empezar.isHidden()
    pag.banner.bt_pausa.click()
    assert ctrl.temporizador.en_pausa() and pag.banner.bt_pausa.text() == "Reanudar"
    marco.close()
    ctx, ctrl, pag, marco = _pagina(app, datos, 1280, 800, "pagina_con_sesion_1280.png", sesion=True)
    marco.close()


def test_captura_pagina_completa_alta(app, datos):
    ctx, ctrl, pag, marco = _pagina(app, datos, 1280, 1500, "pagina_completa_1280.png")
    marco.close()


def test_captura_pagina_con_fondo_de_caudal_translucido(app, datos):
    ctx, ctrl, pag, marco = _pagina(app, datos, 1280, 800, "pagina_con_fondo.png", fondo=True)
    marco.close()


def test_captura_vista_cero_distracciones(app, datos):
    from descargador.ui import estilos
    from descargador.ui.estudio_enfoque import VistaEnfoque
    estilos.aplicar_aspecto("cian", "oscuro")
    ctx, ctrl, reloj = _ctrl_demo(app, datos)
    ctrl.empezar()
    reloj.pasar(7 * 60 + 12)
    ctrl.revisar()
    marco = QWidget()
    marco.setObjectName("raiz")
    marco.setStyleSheet(estilos.hoja({}))
    marco.resize(1280, 800)
    marco.show()
    v = VistaEnfoque(ctx, marco, ctrl)
    v.abrir()
    esperar(app, lambda: ctx.reproductor.listas, "cola del perfil")
    ctx.reproductor.actual = pista("d1", "Moonlight Drive (piano)", "Lofi Lab")
    v._pista()
    app.processEvents()
    assert v.et_tiempo.text() == "17:48" and "ENFOQUE" in v.et_fase.text()
    assert v.et_ahora.text().startswith("Moonlight Drive")
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_1280x800.png"))
    # el mezclador y las notas como paneles emergentes
    v.alternar_mezcla()
    app.processEvents()
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_mezclador.png"))
    v.alternar_notas()
    app.processEvents()
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_notas.png"))
    v.panel_notas.cerrar()
    # modo cálido y bajo brillo
    ctrl.poner(calido=True, brillo=70)
    app.processEvents()
    assert v.velo.isVisible() and v.brillo.isVisible()
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_calido.png"))
    # un descanso con su aviso calmado
    reloj.pasar(25 * 60)
    ctrl.revisar()
    app.processEvents()
    for _ in range(40):
        app.processEvents()
        QTest.qWait(20)
    assert "DESCANSO" in v.et_fase.text() and v.bt_saltar.isVisible() is True
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_descanso_calido.png"))
    # el aviso de salida
    ctrl.poner(calido=False, candado=True)
    v.pedir_salida()
    app.processEvents()
    marco.grab().save(os.path.join(CAPTURAS, "enfoque_salir_candado.png"))
    v._confirma_estudio.seguir.emit()
    marco.close()


def test_captura_tarjeta_en_inicio(app, datos):
    from descargador.ui import estilos
    from descargador.ui.paginas.estudio import TarjetaEstudioInicio
    estilos.aplicar_aspecto("cian", "oscuro")
    w = QWidget()
    w.setStyleSheet(estilos.hoja({}))
    w.resize(900, 180)
    from PySide6.QtWidgets import QVBoxLayout
    v = QVBoxLayout(w)
    v.setContentsMargins(30, 30, 30, 30)
    v.addWidget(TarjetaEstudioInicio("Hoy llevas 1 h 17 min de enfoque  ·  3 días seguidos"))
    w.show()
    app.processEvents()
    w.grab().save(os.path.join(CAPTURAS, "inicio_tarjeta.png"))
    w.close()


# ====================================================================== la ventana de verdad

def _ventana(app, datos):
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None            # sin motores de audio reales
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import estilos
    from descargador.ui.contexto import Contexto
    from descargador.ui import ventana as modulo_ventana
    from descargador.ui.ventana import Ventana
    from PySide6.QtWidgets import QMessageBox
    # nada de cuadros modales ni de red: colgarían la prueba
    QMessageBox.warning = staticmethod(lambda *a, **k: 0)
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
    Ventana.buscar_version = lambda self, callado=False: None
    Ventana._avisar_novedades = lambda self: None
    ajustes = Ajustes()
    estilos.aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
    historial, coleccion = Historial(), Coleccion()
    gestor = Gestor(ajustes, historial)
    rep = Reproductor(ajustes, coleccion)
    ctx = Contexto(ajustes, historial, coleccion, gestor, rep)
    ctx.estudio = None
    v = Ventana(ctx)
    return ctx, v


def test_ventana_entrada_en_la_barra_atajos_y_proteccion_al_cambiar_de_pagina(app, datos):
    from descargador.ui.paginas.estudio import PaginaEstudio
    ctx, v = _ventana(app, datos)
    v.resize(1280, 800)
    v.show()
    app.processEvents()
    # entrada en la barra lateral y en Inicio
    assert "estudio" in v.lateral.botones and "Modo estudio" in v.lateral.botones["estudio"].text()
    assert any(type(w).__name__ == "TarjetaEstudioInicio" for w in v.findChildren(QWidget))
    # atajo Ctrl+Shift+E
    QTest.keyClick(v, Qt.Key_E, Qt.ControlModifier | Qt.ShiftModifier)
    app.processEvents()
    pag = v.historia[v.indice][1]
    assert isinstance(pag, PaginaEstudio) and v.lateral.botones["estudio"].isChecked()
    ctrl = ctx.estudio
    ctrl.mezclador._fabrica = lambda n: MotorFalso(n)
    ctrl.mezclador.generador = SA.Generador(datos / "amb2", segundos=2, empalme=0.5)
    ctrl._buscar = lambda t: _pistas(4)
    ctrl.empezar()
    app.processEvents()
    # con un bloque en curso, cambiar de página pregunta y no cambia nada hasta confirmar
    v.navegar({"pagina": "ajustes"})
    app.processEvents()
    assert v.historia[v.indice][0]["pagina"] == "estudio" and ctrl.hay_bloque()
    c = v._confirma_estudio
    assert c.isVisible()
    {b.text(): b for b in c.findChildren(QPushButton)}["Seguir estudiando"].click()
    app.processEvents()
    assert v.historia[v.indice][0]["pagina"] == "estudio" and ctrl.hay_bloque()
    # cerrar la ventana también pregunta
    v.close()
    app.processEvents()
    assert v.isVisible() and v._confirma_estudio.isVisible() and ctrl.hay_bloque()
    v._escape_estudio()                                            # Esc = seguir estudiando
    app.processEvents()
    assert v._confirma_estudio is None and ctrl.hay_bloque()
    # Salir: termina la sesión y sí cambia de página
    v.navegar({"pagina": "ajustes"})
    {b.text(): b for b in v._confirma_estudio.findChildren(QPushButton)}["Salir"].click()
    app.processEvents()
    assert v.historia[v.indice][0]["pagina"] == "ajustes" and not ctrl.hay_bloque()
    assert not ctrl.activo and ctx.ajustes["crossfade"] == 0
    # en un reproductor normal no se quedó nada del modo estudio
    assert ctx.reproductor.repetir in ("no", "todo", "una")
    # abrir la vista, Ctrl+Mayús+N solo dentro del modo estudio
    v.navegar({"pagina": "estudio"})
    v.abrir_enfoque()
    app.processEvents()
    assert v.vista_enfoque.isVisible()
    QTest.keyClick(v, Qt.Key_N, Qt.ControlModifier | Qt.ShiftModifier)
    app.processEvents()
    assert v.vista_enfoque.panel_notas.isVisible()
    v._escape_estudio()
    assert not v.vista_enfoque.panel_notas.isVisible()
    v._escape_estudio()                                             # sin bloque: se cierra directo
    assert not v.vista_enfoque.isVisible()
    v._saliendo = True
    v.close()
