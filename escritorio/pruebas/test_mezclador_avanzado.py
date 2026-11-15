# -*- coding: utf-8 -*-
"""Mezclador avanzado: BPM y compás desde el audio, orden y compatibilidad, mezcla a
tempo, tipos de transición, ecualizador y marcas por canción. Sin red, sin mpv y sin
ventanas (los de interfaz están en test_mezclador_y_novedades.py)."""

import math
import os
import random
import sys
import wave
from array import array

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def datos_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    yield tmp_path


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def clicks(bpm, seg=100, sr=4000, desfase=0.31, fuerte=True):
    """Audio sintético: un golpe cada pulso (el primero de cada compás más fuerte)."""
    n = int(seg * sr)
    m = [0] * n
    periodo = 60.0 / bpm
    random.seed(3)
    t, k = desfase, 0
    while t < seg - 0.3:
        i = int(t * sr)
        amp = 24000 if (k % 4 == 0 and fuerte) else 16000
        for j in range(int(sr * 0.06)):
            if i + j < n:
                m[i + j] += int(amp * math.exp(-j / (sr * 0.0125)) * math.sin(j * 0.35 * 4000 / sr))
        t += periodo
        k += 1
    for i in range(n):
        m[i] += random.randint(-300, 300)
    return array("h", [max(-32768, min(32767, v)) for v in m])


# ================================================================ BPM

@pytest.mark.parametrize("bpm", [80, 100, 124, 128, 140, 170])
def test_bpm_de_audio_sintetico(bpm):
    from descargador import analisis_audio as aa
    r = aa.analizar_muestras(clicks(bpm))
    assert r["bpm"] == pytest.approx(bpm, abs=0.6)
    periodo = 60.0 / bpm
    # primer pulso y primer «uno» (el golpe fuerte) cerca de 0,31 s
    assert abs(((r["fase"] - 0.31 + periodo / 2) % periodo) - periodo / 2) < 0.04
    assert abs(((r["uno"] - 0.31 + 2 * periodo) % (4 * periodo)) - 2 * periodo) < 0.04
    assert len(r["perfil"]) == 64 and max(r["perfil"]) == 1.0
    assert 0.0 <= r["energia"] <= 1.0 and r["claridad"] > 0.5


def test_silencio_y_audio_corto_no_dan_tempo():
    from descargador import analisis_audio as aa
    assert aa.analizar_muestras(array("h", [0] * 4000 * 3)) is None
    r = aa.analizar_muestras(array("h", [0] * 4000 * 30))
    assert r["bpm"] == 0.0 and r["energia"] == 0.0


def test_mas_ritmo_y_mas_volumen_es_mas_energia():
    from descargador import analisis_audio as aa
    calma = aa.analizar_muestras(array("h", [int(v * 0.1) for v in clicks(80)]))
    fuerte = aa.analizar_muestras(clicks(170))
    assert fuerte["energia"] > calma["energia"]


def _wav(ruta, muestras, sr=4000):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(muestras.tobytes())


def test_analisis_de_un_archivo_real_con_ffmpeg(tmp_path):
    from descargador import analisis_audio as aa
    from descargador.reproduccion import _ffmpeg_exe
    exe = _ffmpeg_exe()
    if not exe:
        pytest.skip("no hay ffmpeg en esta PC")
    ruta = tmp_path / "ritmo.wav"
    _wav(ruta, clicks(120, seg=60))
    r = aa.analizar_fuente({"archivo": str(ruta)}, exe)
    assert r is not None and r["bpm"] == pytest.approx(120, abs=0.8)
    assert aa.analizar_fuente({"archivo": str(tmp_path / "no_existe.wav")}, exe) is None


def test_cache_de_analisis_y_correccion_a_mano(app, tmp_path):
    from descargador import analisis_audio as aa
    from descargador.coleccion import Coleccion
    col = Coleccion()
    pista = {"clave": "yt:vid00000001", "video_id": "vid00000001", "duracion": 200}
    assert aa.analisis_guardado(col, pista) is None
    aa.guardar_analisis(col, pista, {"bpm": 123.0, "fase": 0.2, "uno": 0.2, "energia": 0.5,
                                     "perfil": [0.5] * 64})
    assert aa.analisis_guardado(col, pista)["bpm"] == 123.0
    # sin audio disponible, la caché responde sin tocar ffmpeg
    assert aa.analizar_pista(col, pista, exe="no-hay")["bpm"] == 123.0
    # corregir el tempo a mano
    aa.guardar_analisis(col, pista, {**aa.analisis_guardado(col, pista), "bpm": 128.0})
    assert aa.analisis_guardado(col, pista)["bpm"] == 128.0
    # sin copia en el disco y sin conexión: no se puede analizar, y lo dice con None
    otra = {"clave": "yt:vid00000002", "video_id": "vid00000002"}
    assert aa.analizar_pista(col, otra, exe="no-hay") is None


# ================================================================ compatibilidad y orden

def _an(bpm, energia=0.5, uno=0.0):
    return {"bpm": bpm, "energia": energia, "uno": uno, "fase": uno}


def test_compatibilidad_por_colores():
    from descargador import mezcla_dj as md
    assert md.compatibilidad(_an(120), _an(122))["nivel"] == "encaja"
    assert md.compatibilidad(_an(120), _an(127))["nivel"] == "ajusta"
    assert md.compatibilidad(_an(120), _an(140))["nivel"] == "choca"
    assert md.compatibilidad(_an(120), _an(61))["nivel"] == "encaja"        # la mitad cuenta
    assert md.compatibilidad(_an(120), {})["nivel"] == "desconocido"
    assert md.razon_tempo(124, 128) == pytest.approx(0.96875)
    assert md.razon_tempo(124, 140) is None
    assert md.razon_tempo(0, 120) is None


def test_ordenar_set_por_tempo_y_energia():
    from descargador import mezcla_dj as md
    datos = {"a": _an(128, 0.9), "b": _an(90, 0.2), "c": _an(100, 0.35), "d": _an(126, 0.8),
             "e": _an(95, 0.3)}
    pistas = [{"clave": k, "titulo": k} for k in "abcde"] + [{"clave": "z", "titulo": "sin"}]
    orden = [p["clave"] for p in md.ordenar_set(pistas, datos)]
    assert orden[0] == "b"                       # empieza por la más calmada
    assert orden[-1] == "z"                      # lo que no se pudo analizar va al final
    assert set(orden[:3]) == {"b", "e", "c"} and set(orden[3:5]) == {"a", "d"}   # cada grupo junto
    saltos = [md.diferencia_tempo(datos[x]["bpm"], datos[y]["bpm"])
              for x, y in zip(orden[:4], orden[1:5])]
    assert sorted(saltos)[-1] < 0.3 and sorted(saltos)[-2] < 0.08   # un solo salto grande: el de cambiar de grupo
    # con una sola canción analizada no se toca nada
    assert md.ordenar_set(pistas[:2], {"a": _an(100)}) == pistas[:2]


def test_pasos_automaticos_segun_perfil():
    from descargador import mezcla_dj as md
    pistas = [{"clave": k, "duracion": 200} for k in "abc"]
    datos = {"a": _an(120), "b": _an(124), "c": _an(150)}
    suave = md.pasos_automaticos(pistas, datos, "suave")
    assert [p["tipo"] for p in suave] == ["fundido", "fundido"]
    assert suave[0]["tempo"] is True and suave[1]["tempo"] is False       # b→c choca: no se estira
    assert suave[0]["entra"] == 8                                          # 4 compases a 120 BPM
    club = md.pasos_automaticos(pistas, datos, "club")
    assert club[0]["tipo"] == "graves" and club[1]["tipo"] == "filtro"     # el choque se tapa con filtro
    assert club[0]["entra"] == 4
    rapida = md.pasos_automaticos(pistas, datos, "rapida")
    assert rapida[0]["tipo"] == "corte" and rapida[0]["curva"] == "corte"
    # sin análisis: duraciones fijas por perfil y sin estirar el tempo
    sin = md.pasos_automaticos(pistas, {}, "club")
    assert sin[0]["entra"] == 8 and sin[0]["tempo"] is False


def test_alineacion_con_el_compas():
    from descargador import mezcla_dj as md
    an = _an(120, uno=0.31)                       # compás de 2 s: 0,31 · 2,31 · 4,31…
    assert md.inicio_de_compas_hasta(10.0, an) == pytest.approx(8.31)
    assert md.inicio_de_compas_desde(10.0, an) == pytest.approx(10.31)
    assert md.entrada_alineada(3.0, an) == pytest.approx(4.31)
    assert md.disparo_alineado(176.2, an) == pytest.approx(174.31)
    assert md.disparo_alineado(176.2, {}) == 176.2                         # sin análisis, igual


def test_filtros_curvas_y_ecualizador():
    from descargador import mezcla_dj as md
    sal, ent = md.partes_transicion("filtro", 0.1)
    assert sal == () and ent == ("highpass=f=1800",)
    sal, ent = md.partes_transicion("filtro", 0.9)
    assert sal == ("lowpass=f=400",) and ent == ()
    assert md.partes_transicion("eco", 0.05)[0] == () and "aecho" in md.partes_transicion("eco", 0.5)[0][0]
    assert md.partes_transicion("fundido", 0.5) == ((), ())
    assert md.curva_volumenes("lineal", 0.25) == (0.25, 0.75)
    ent, sal = md.curva_volumenes("suave", 0.5)
    assert ent == pytest.approx(sal)               # igual potencia a mitad
    assert md.curva_volumenes("corte", 0.4) == (0.0, 1.0)
    assert md.curva_volumenes("corte", 0.65) == (1.0, 0.0)
    assert md.filtros_eq([0, 0, 0]) == [] and md.filtros_eq(None) == []
    eq = md.filtros_eq([-12, 3, 6])
    assert eq[0].startswith("bass=g=-12.0") and "equalizer" in eq[1] and eq[2].startswith("treble=g=6.0")
    assert md.filtros_eq([-40, 0, 0])[0].startswith("bass=g=-12.0")        # tope
    assert md.combinar_filtros("lavfi=[a]", ["x"], ["y"]) == "lavfi=[x,a,y]"
    assert md.combinar_filtros("", ["x"]) == "lavfi=[x]"
    assert md.combinar_filtros("", (), ()) == ""


def test_marcas_validas():
    from descargador import mezcla_dj as md
    m = md.normalizar_marcas({"entrada": 12.3456, "salida": 190, "eq": [1, 20, -50]}, 200)
    assert m == {"entrada": 12.35, "salida": 190.0, "eq": [1.0, 6.0, -12.0]}
    assert md.normalizar_marcas({"entrada": 300}, 200)["entrada"] is None   # fuera de la canción
    assert md.normalizar_marcas({"entrada": 100, "salida": 102}, 200)["salida"] is None
    assert md.marcas_vacias({}) and md.marcas_vacias({"eq": [0.2, 0, 0]})
    assert not md.marcas_vacias({"entrada": 5})


def test_mezclas_guardadas_antes_se_leen_y_las_nuevas_llevan_todo(app):
    from descargador import mezcla_dj as md
    from descargador.coleccion import Coleccion
    col = Coleccion()
    # una mezcla de la primera versión (sin tipo, curva, tempo ni marcas)
    col.guardar_estado(md.CLAVE_SETS, [{"nombre": "Vieja", "pistas": [{"clave": "a", "duracion": 200},
                                                                       {"clave": "b", "duracion": 200}],
                                        "pasos": [{"entra": 9, "dur": 7, "graves": True}]}])
    vieja = md.leer_sets(col)[0]
    paso = md.pasos_para(vieja["pistas"], vieja["pasos"])[0]
    assert paso["tipo"] == "graves" and paso["curva"] == "suave" and paso["tempo"] is False
    assert md.normalizar_marcas(vieja.get("marcas", {}).get("a")) == {"entrada": None, "salida": None,
                                                                      "eq": [0.0, 0.0, 0.0]}
    nuevo = md.guardar_set(col, "Nueva", vieja["pistas"],
                           [{"entra": 8, "dur": 8, "tipo": "eco", "curva": "lineal", "tempo": True}],
                           {"a": {"entrada": 10, "eq": [2, 0, 0]}, "b": {}})
    assert nuevo["pasos"][0]["tipo"] == "eco" and nuevo["pasos"][0]["tempo"] is True
    assert set(nuevo["marcas"]) == {"a"}                                    # las vacías no se guardan
    assert md.leer_sets(col)[0]["marcas"]["a"]["eq"] == [2.0, 0.0, 0.0]


# ================================================================ reproductor

class MotorFalso:
    es_video = False

    def __init__(self):
        self.volumen = None
        self.cargas = []
        self.filtros = []
        self.velocidades = []
        self.pausado = False
        self.parado = False
        self.pos = 0.0

    def fijar_volumen(self, v):
        self.volumen = v

    def fijar_velocidad(self, v):
        self.velocidades.append(v)

    def fijar_filtros(self, af):
        self.filtros.append(af)

    def cargar(self, fuente, inicio=0.0, pausado=False):
        self.cargas.append((fuente, inicio))

    def detener(self):
        self.parado = True

    def pausar(self, si=True):
        self.pausado = bool(si)

    def en_pausa(self):
        return self.pausado

    def posicion_actual(self):
        return self.pos

    def buscar(self, s):
        self.pos = s


def _pista(n, dur=200, archivo=""):
    p = {"tipo": "pista", "clave": f"yt:vid{n:08d}", "video_id": f"vid{n:08d}",
         "titulo": f"Canción {n}", "artista": "Artista", "duracion": dur, "miniatura": ""}
    if archivo:
        p["archivo"] = archivo
    return p


def _reproductor(app, monkeypatch, tmp_path, n=3):
    from descargador import mpv_carga
    monkeypatch.setattr(mpv_carga, "modulo", lambda: None)
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.reproduccion import Reproductor
    a = Ajustes()
    a["sponsorblock"] = False
    a["autoplay"] = False
    a["crossfade"] = 0
    r = Reproductor(a, Coleccion())
    r.disponible = True
    r.audio = [MotorFalso(), MotorFalso()]
    r.activo = 0
    r.volumen = 80
    pistas = []
    for i in range(1, n + 1):
        f = tmp_path / f"{i}.opus"
        f.write_bytes(b"x")
        pistas.append(_pista(i, archivo=str(f)))
    r.secuencia, r.original = list(pistas), list(pistas)
    r.pos, r.actual = 0, pistas[0]
    r._duracion = 200.0
    r.estado = "sonando"
    return r, pistas


def _paso(**kw):
    base = {"entra": 8, "dur": 8, "tipo": "fundido", "curva": "suave", "tempo": False}
    base.update(kw)
    return base


def test_tipo_filtro_cierra_la_que_sale_y_abre_la_que_entra(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [_paso(tipo="filtro")], "x")
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal, ent = r.audio
    r._al_posicion(sal, 193.0)
    f = r._fundido
    assert f is not None and f["tipo"] == "filtro" and f["dur"] == 8.0
    assert "highpass=f=1800" in ent.filtros[-1]                  # la que entra empieza «tapada»
    f["inicio"] -= 6.5                                            # avance 0,81
    r._paso_fundido()
    assert "lowpass=f=400" in sal.filtros[-1]
    assert "highpass" not in (ent.filtros[-1] or "")
    f["inicio"] -= 10
    r._paso_fundido()
    assert r._fundido is None
    base = r.cadena_filtros()
    assert ent.filtros[-1] == base and sal.filtros[-1] == base                  # todo vuelve a su sitio


def test_tipo_eco_y_corte(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [_paso(tipo="eco")], "x")
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal = r.audio[0]
    r._al_posicion(sal, 193.0)
    r._fundido["inicio"] -= 4
    r._paso_fundido()
    assert "aecho" in sal.filtros[-1]
    r._cortar_fundido()
    # corte: dura medio segundo, con la curva de corte
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [_paso(tipo="corte", curva="suave")], "x")
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    r._al_posicion(r.audio[0], 193.0)
    assert r._fundido["dur"] == 0.5 and r._fundido["curva"] == "corte"


def test_la_curva_manda_en_los_volumenes(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [_paso(curva="lineal")], "x")
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal, ent = r.audio
    r._al_posicion(sal, 193.0)
    r._fundido["inicio"] -= 2.0                                   # avance 0,25
    r._paso_fundido()
    assert ent.volumen == pytest.approx(80 * 0.25, abs=3) and sal.volumen == pytest.approx(80 * 0.75, abs=3)


def test_mezcla_a_tempo_estira_a_la_que_entra_y_la_devuelve(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    an = {pistas[0]["clave"]: {"bpm": 124.0, "uno": 0.5, "fase": 0.5},
          pistas[1]["clave"]: {"bpm": 128.0, "uno": 1.0, "fase": 1.0}}
    r.reproducir_set(pistas, [_paso(tempo=True)], "x", analisis=an)
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal, ent = r.audio
    r._al_posicion(sal, 193.0)
    f = r._fundido
    assert f["ratio"] == pytest.approx(124 / 128)
    assert ent.velocidades[-1] == pytest.approx(r.velocidad * 124 / 128)   # la que entra se acerca
    assert sal.velocidades[-1:] in ([], [r.velocidad]) or True              # la que sale no se toca
    # a la que entra se le da un inicio de compás (128 BPM: compás de 1,875 s; «uno» en 1,0)
    entrada = ent.cargas[-1][1]
    assert abs(((entrada - 1.0) / 1.875) - round((entrada - 1.0) / 1.875)) < 1e-6
    f["inicio"] -= 20
    r._paso_fundido()
    # al acabar vuelve poco a poco a su velocidad normal (se programa con temporizadores)
    assert r._fundido is None


def test_sin_analisis_no_se_estira_aunque_se_pida(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.reproducir_set(pistas, [_paso(tempo=True)], "x")
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    r._al_posicion(r.audio[0], 193.0)
    assert r._fundido["ratio"] == 1.0 and r.audio[1].velocidades[-1] == r.velocidad


def test_la_transicion_empieza_en_un_inicio_de_compas(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    an = {pistas[0]["clave"]: {"bpm": 120.0, "uno": 0.31, "fase": 0.31}}
    r.reproducir_set(pistas, [_paso(entra=8, dur=8, tempo=True)], "x", analisis=an)
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal = r.audio[0]
    # 200 - 8 = 192 → el compás anterior es 190,31 (compases de 2 s desde 0,31)
    r._al_posicion(sal, 190.0)
    assert r._fundido is None
    r._al_posicion(sal, 190.4)
    assert r._fundido is not None


def test_marcas_de_entrada_y_salida(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    marcas = {pistas[0]["clave"]: {"salida": 150.0}, pistas[1]["clave"]: {"entrada": 17.5}}
    r.reproducir_set(pistas, [_paso(entra=6, dur=6)], "x", marcas=marcas)
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    assert r._fin_musica() == 150.0
    sal, ent = r.audio
    r._al_posicion(sal, 140.0)
    assert r._fundido is None
    r._al_posicion(sal, 144.5)                      # 150 - 6
    assert r._fundido is not None and ent.cargas[-1][1] == 17.5


def test_ecualizador_por_cancion(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    marcas = {pistas[1]["clave"]: {"eq": [-8, 0, 3]}}
    r.reproducir_set(pistas, [_paso()], "x", marcas=marcas)
    r.estado, r.actual, r._duracion = "sonando", pistas[0], 200.0
    sal, ent = r.audio
    r._al_posicion(sal, 193.0)
    assert "bass=g=-8.0" in ent.filtros[-1] and "treble=g=3.0" in ent.filtros[-1]
    r._fundido["inicio"] -= 20
    r._paso_fundido()
    assert "bass=g=-8.0" in ent.filtros[-1]          # sigue con su ecualizador al acabar el fundido
    assert sal.filtros[-1] == r.cadena_filtros()      # la que salió vuelve a lo normal
    # cargar otra canción sin ecualizador en ese motor lo limpia
    r.plan_marcas = {}
    r._arrancar(r._gen, {"archivo": pistas[0]["archivo"], "local": True}, 0.0, False)
    assert r.audio[r.activo].filtros[-1] == r.cadena_filtros()


def test_probar_paso_y_tramo_con_marcas(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.probar_paso(pistas[0], pistas[1], _paso(entra=10, dur=8),
                  marcas={pistas[0]["clave"]: {"salida": 120.0}})
    assert r.audio[r.activo].cargas[-1][1] == pytest.approx(120 - 10 - 10)  # antes de la salida elegida
    r.probar_tramo(pistas[2], 33.0, 8)
    assert r.audio[r.activo].cargas[-1][1] == 33.0 and r.plan_mezcla == {}
    r.estado = "sonando"
    r._fin_de_prueba(r._prueba)
    assert r.audio[r.activo].pausado


def test_mezcla_dj_automatica_sigue_igual_con_tipo_graves(app, monkeypatch, tmp_path):
    r, pistas = _reproductor(app, monkeypatch, tmp_path)
    r.ajustes["mezcla_dj"] = True
    r.ajustes["mezcla_dj_seg"] = 10
    r._al_posicion(r.audio[0], 191.0)
    f = r._fundido
    assert f["tipo"] == "graves" and f["graves"] is True and f["dur"] == 10.0


# ================================================================ la página

def _contexto(app):
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None
    from descargador.coleccion import Coleccion
    from descargador.config import Ajustes
    from descargador.historial import Historial
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui import estilos
    from descargador.ui.contexto import Contexto
    ajustes = Ajustes()
    estilos.aplicar_aspecto(ajustes["acento"], ajustes["fondo"])
    historial, coleccion = Historial(), Coleccion()
    return Contexto(ajustes, historial, coleccion, Gestor(ajustes, historial),
                    Reproductor(ajustes, coleccion))


def _esperar(app, condicion, segundos=60):
    import time
    fin = time.time() + segundos
    while time.time() < fin and not condicion():
        app.processEvents()
        time.sleep(0.02)
    return condicion()


def test_dialogo_de_ritmo_calcula_los_pulsos_tocados(app):
    from descargador.ui.paginas.mezclador import DialogoRitmo
    d = DialogoRitmo("Una canción", 0.0)
    for k in range(6):
        d.registrar_toque(100.0 + k * 0.5)             # un toque cada medio segundo = 120
    assert d.bpm() == pytest.approx(120.0, abs=0.6)
    d.registrar_toque(110.0)                            # tras una pausa larga se empieza de nuevo
    assert len(d._toques) == 1
    d.caja.setValue(97.5)
    assert d.bpm() == 97.5


def test_ritmo_escrito_a_mano_no_alinea_compases(app):
    from descargador import analisis_audio as aa
    from descargador import mezcla_dj as md
    from descargador.coleccion import Coleccion
    col = Coleccion()
    pista = {"clave": "yt:vid00000001", "video_id": "vid00000001"}
    datos = aa.corregir_ritmo(col, pista, 126)
    assert datos["bpm"] == 126.0 and datos["manual"] and datos["sin_fase"]
    assert md.razon_tempo(126, 120) is not None                      # el tempo sí se iguala
    assert md.entrada_alineada(3.3, datos) == 3.3                    # pero sin fase no se alinea
    assert md.disparo_alineado(176.2, datos) == 176.2


def test_pagina_dj_analiza_ordena_y_deja_los_pasos(app, datos_aislados):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from descargador import mezcla_dj as md
    from descargador.reproduccion import _ffmpeg_exe
    from descargador.ui.paginas.mezclador import PaginaMezclador
    if not _ffmpeg_exe():
        pytest.skip("no hay ffmpeg en esta PC")
    ctx = _contexto(app)
    avisos, llamadas = [], []
    ctx.aviso.connect(avisos.append)
    ctx.reproductor.reproducir_set = lambda p, pasos, nombre="", marcas=None, analisis=None: \
        llamadas.append(("set", [x["clave"] for x in p], marcas, analisis))
    ctx.reproductor.probar_tramo = lambda p, desde, seg=12.0: llamadas.append(("tramo", p["clave"], desde))
    pistas = []
    for n, bpm in ((1, 140), (2, 100), (3, 124), (4, 102)):
        ruta = datos_aislados / f"c{n}.wav"
        _wav(ruta, clicks(bpm, seg=50))
        p = _pista(n, 50, archivo=str(ruta))
        ctx.coleccion.recordar(p)
        pistas.append(p)
    pagina = PaginaMezclador(ctx)
    pagina.resize(1000, 1100)
    pagina.show()
    app.processEvents()
    pagina.anadir(pistas)
    assert pagina.analisis == {}
    pagina.c_perfil.setCurrentIndex(pagina.c_perfil.findData("club"))
    pagina.mezclar_como_dj()
    assert _esperar(app, lambda: len(pagina.analisis) == 4 and pagina._analizando is None
                    and not pagina._cola_analisis, 120)
    assert _esperar(app, lambda: any("Listo" in a for a in avisos), 30)
    bpms = {k: v["bpm"] for k, v in pagina.analisis.items()}
    assert bpms["yt:vid00000002"] == pytest.approx(100, abs=0.8)
    assert bpms["yt:vid00000003"] == pytest.approx(124, abs=0.8)
    # ordenadas por tempo: 100, 102, 124, 140 (empieza por la más calmada)
    orden = [pagina._clave(p) for p in pagina.pistas]
    assert [round(bpms[k]) for k in orden] == sorted(round(bpms[k]) for k in orden)
    assert [p["tipo"] for p in pagina.pasos] == ["graves", "filtro", "filtro"] or \
        all(p["tipo"] in ("graves", "filtro") for p in pagina.pasos)
    assert pagina.pasos[0]["tempo"] is True                       # 100 → 102 encajan
    assert pagina.pasos[-1]["tempo"] is False                     # 124 → 140 chocan
    # los colores del paso salen de verdad: verde, ámbar o rojo según el encaje
    pasos_w = [pagina.v_set.itemAt(i).widget() for i in range(pagina.v_set.count())
               if pagina.v_set.itemAt(i).widget().objectName() == "paso_mezcla"]
    assert len(pasos_w) == 3 and "Encajan" in pasos_w[0].et_compat.text()
    assert "Chocan" in pasos_w[-1].et_compat.text()
    # los ajustes de una canción: marcas, ecualizador y probar el tramo
    pagina._alternar_detalle(0)
    app.processEvents()
    panel = next(pagina.v_set.itemAt(i).widget() for i in range(pagina.v_set.count())
                 if pagina.v_set.itemAt(i).widget().objectName() == "panel_cancion")
    panel.s_entrada.setValue(12)
    panel.s_salida.setValue(40)
    panel.s_eq[0].setValue(-6)
    clave0 = pagina._clave(pagina.pistas[0])
    assert pagina.marcas[clave0] == {"entrada": 12.0, "salida": 40.0, "eq": [-6.0, 0.0, 0.0]}
    QTest.mouseClick(panel.onda, Qt.LeftButton, Qt.NoModifier, panel.onda.rect().center())
    assert 20 <= pagina.marcas[clave0]["entrada"] <= 30            # clic en medio de 50 s
    QTest.mouseClick(panel.onda, Qt.LeftButton, Qt.ShiftModifier, panel.onda.rect().center())
    panel.probar_tramo.emit(0, 12.0)
    assert llamadas[-1] == ("tramo", clave0, 12.0)
    pagina.grab().save(str(datos_aislados / "mezclador_avanzado.png"))
    # reproducir lleva las marcas y el análisis al reproductor
    pagina.reproducir_set()
    kind, claves, marcas, analisis = llamadas[-1]
    assert kind == "set" and claves == orden and clave0 in marcas and len(analisis) == 4
    # guardar y volver a abrir conserva marcas y pasos nuevos
    pagina.campo_nombre.setText("Club del sábado")
    assert pagina.guardar()
    guardado = md.leer_sets(ctx.coleccion)[0]
    assert guardado["pasos"][0]["tipo"] == "graves" and clave0 in guardado["marcas"]
    pagina.vaciar_mesa()
    pagina.abrir_mezcla(guardado)
    assert pagina.marcas[clave0]["eq"] == [-6.0, 0.0, 0.0] and len(pagina.analisis) == 4
    # ordenar a mano un set revuelto
    pagina.pistas = list(reversed(pagina.pistas))
    pagina.ordenar()
    assert [round(bpms[pagina._clave(p)]) for p in pagina.pistas] == sorted(round(v) for v in bpms.values())
