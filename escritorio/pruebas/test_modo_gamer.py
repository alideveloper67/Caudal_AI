# -*- coding: utf-8 -*-
"""Modo gamer: atajos globales, mini reproductor, ahorro al jugar, presets de sonido, bajar al hablar,
listas por situacion, XP y misiones, «Ahora suena» para OBS, neon y la pantalla.

Qt offscreen, datos en una carpeta temporal, sin audio real y sin internet. Los atajos globales y
los clics que pasan se prueban contra Windows de verdad (RegisterHotKey y una ventana nativa)."""

import os
import sys
import tempfile
import time
from datetime import date, timedelta

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_gamer_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget  # noqa: E402

from descargador import modo_gamer as MG  # noqa: E402

CAPTURAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas_gamer")
os.makedirs(CAPTURAS, exist_ok=True)
WIN = sys.platform == "win32"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def esperar(app, cond, que, maximo=8):
    fin = time.time() + maximo
    while not cond():
        app.processEvents()
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.01)


def pausa(app, s=0.2):
    fin = time.time() + s
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture(scope="module")
def bases():
    """Coleccion e Historial tardan segundos en abrirse en este equipo: se abren una sola vez."""
    from descargador import mpv_carga
    mpv_carga.modulo = lambda: None          # nada de motores de audio reales
    from descargador.coleccion import Coleccion
    from descargador.historial import Historial
    return Coleccion(), Historial()


@pytest.fixture
def ctx(app, bases, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    from descargador import config
    monkeypatch.setitem(config.PERFIL, "carpeta", "")
    from descargador.config import Ajustes
    from descargador.motor import Gestor
    from descargador.reproduccion import Reproductor
    from descargador.ui.contexto import Contexto
    aj = Ajustes()
    col, his = bases
    return Contexto(aj, his, col, Gestor(aj, his), Reproductor(aj, col))


@pytest.fixture
def gestor(ctx):
    from descargador.ui.neon_gamer import reloj_neon
    g = MG.GestorGamer(ctx, None)
    yield g
    g.cerrar()
    reloj_neon().pausar(False)
    reloj_neon().activar(True)


def _pista(n=1, titulo="Canción", artista="Artista"):
    return {"tipo": "pista", "clave": f"yt:{n}", "video_id": f"id{n}", "titulo": f"{titulo} {n}",
            "artista": artista, "miniatura": "", "duracion": 200}


# ------------------------------------------------------------------ atajos (lógica pura)

def test_atajos_por_defecto_validos_y_sin_choques():
    assert set(MG.ATAJOS_DEFECTO) == {a for a, _n in MG.ACCIONES}
    for t in MG.ATAJOS_DEFECTO.values():
        mods, vk = MG.parsear_atajo(t)
        assert mods & MG.MOD_CTRL and mods & MG.MOD_ALT and vk
        assert MG.normalizar_atajo(t) == t
    assert MG.atajos_repetidos(MG.ATAJOS_DEFECTO) == {}


def test_parsear_atajos_y_rechazos():
    assert MG.parsear_atajo("Ctrl+Alt+Space") == (MG.MOD_CTRL | MG.MOD_ALT, 0x20)
    assert MG.parsear_atajo("ctrl + shift + F5") == (MG.MOD_CTRL | MG.MOD_SHIFT, 0x74)
    assert MG.parsear_atajo("Meta+K") == (MG.MOD_WIN, ord("K"))
    assert MG.normalizar_atajo("alt+ctrl+pgdown") == "Ctrl+Alt+PgDown"
    for malo in ("", None, "K", "Shift+K", "Ctrl+", "Ctrl+Alt", "Ctrl+Hola", "Foo+K", "Ctrl+F25", 5):
        assert MG.parsear_atajo(malo) is None, malo


def test_atajos_repetidos_se_detectan():
    d = dict(MG.ATAJOS_DEFECTO, mini="Alt+Ctrl+Space")
    assert MG.atajos_repetidos(d) == {"mini": "play"}


# ------------------------------------------------------------------ ajustes propios

def test_config_guarda_valida_y_se_recupera_de_un_archivo_roto(tmp_path):
    ruta = tmp_path / "g.json"
    c = MG.ConfigGamer(ruta)
    assert c["activo"] is False and c["neon"] is True and c["hablar_nivel"] == 25
    c["activo"] = True
    c["mini_pos"] = [10, 20]
    c.guardar()
    assert MG.ConfigGamer(ruta)["mini_pos"] == [10, 20]
    ruta.write_text('{"mini_opacidad": 9999, "hablar_nivel": "x", "atajos": {"play": "Ctrl+Alt+P", '
                    '"siguiente": "mal"}, "neon": "si"}', encoding="utf-8")
    c2 = MG.ConfigGamer(ruta)
    assert c2["mini_opacidad"] == 100 and c2["hablar_nivel"] == 25
    assert c2["atajos"]["play"] == "Ctrl+Alt+P" and c2["atajos"]["siguiente"] == "Ctrl+Alt+Right"
    assert c2["neon"] is True
    ruta.write_text("{no es json", encoding="utf-8")
    assert MG.ConfigGamer(ruta)["activo"] is False


# ------------------------------------------------------------------ nivel, XP y misiones

def test_curva_de_nivel_suave_y_consistente():
    assert MG.nivel_de_xp(0) == 1 and MG.nivel_de_xp(49) == 1 and MG.nivel_de_xp(50) == 2
    previo = 0
    for xp in range(0, 20000, 7):
        n = MG.nivel_de_xp(xp)
        assert n >= previo and MG.xp_para_nivel(n) <= xp < MG.xp_para_nivel(n + 1)
        previo = n
    largos = [MG.xp_para_nivel(n + 1) - MG.xp_para_nivel(n) for n in range(1, 30)]
    assert all(b - a == 50 for a, b in zip(largos, largos[1:]))      # cada nivel cuesta 50 XP más
    n, dentro, largo, rango = MG.info_nivel(0)
    assert (n, dentro, largo, rango) == (1, 0, 50, "Novato")
    assert MG.info_nivel(MG.xp_para_nivel(6))[3] == "Aprendiz"


def test_el_nivel_se_planta_en_99_y_la_barra_queda_llena():
    assert MG.nivel_de_xp(10**9) == 99
    assert MG.nivel_de_xp(MG.xp_para_nivel(99)) == 99
    assert MG.nivel_de_xp(MG.xp_para_nivel(98)) == 98
    n, dentro, largo, rango = MG.info_nivel(10**9)
    assert n == 99 and largo > 0 and dentro == largo and rango == "Leyenda"


def test_misiones_deterministas_por_fecha():
    d = date(2026, 9, 26)
    a, b = MG.misiones_del_dia(d), MG.misiones_del_dia(d)
    assert a == b and len(a) == 3
    assert len({m["tipo"] for m in a}) == 3 and a[0]["tipo"] == "minutos"
    assert all(m["id"].startswith("2026-09-26:") and m["meta"] > 0 and m["xp"] > 0 for m in a)
    distintas = {tuple(m["id"].split(":")[1] for m in MG.misiones_del_dia(d + timedelta(days=i)))
                 for i in range(30)}
    assert len(distintas) > 3                                       # los días no se repiten todos igual


def test_progreso_un_xp_por_minuto_y_cobro_de_misiones_una_vez(tmp_path):
    hoy = {"d": date(2026, 9, 26)}
    p = MG.Progreso(tmp_path / "p.json", lambda: hoy["d"])
    assert p.xp == 0 and p.racha() == 0
    assert p.sumar_segundos(59) == 0 and p.xp == 0
    assert p.sumar_segundos(1) == 1 and p.xp == 1                   # justo un minuto
    meta = next(m for m in p.misiones() if m["tipo"] == "minutos")["meta"]
    p.sumar_segundos(60 * (meta - 1))
    m = next(m for m in p.misiones() if m["tipo"] == "minutos")
    assert m["hecha"] and p.xp == meta + m["xp"]                    # minutos + bono, una sola vez
    xp = p.xp
    p.sumar_segundos(0)
    assert p.xp == xp
    # lo que se hizo queda guardado (el gestor guarda cada pocos segundos y al cerrar)
    p.guardar()
    assert MG.Progreso(tmp_path / "p.json", lambda: hoy["d"]).xp == xp
    # al día siguiente las misiones vuelven a empezar
    hoy["d"] += timedelta(days=1)
    assert all(not m["hecha"] and m["actual"] == 0 for m in p.misiones())


def test_progreso_eventos_completan_misiones(tmp_path):
    p = MG.Progreso(tmp_path / "p.json", lambda: date(2026, 9, 26))
    for m in p.misiones():
        if m["tipo"] != "minutos":
            ganado = p.evento(m["tipo"], m["meta"])
            assert ganado == m["xp"]
    assert sum(1 for m in p.misiones() if m["hecha"]) == 2


def test_racha_cuenta_dias_seguidos_y_se_corta(tmp_path):
    hoy = {"d": date(2026, 9, 1)}
    p = MG.Progreso(tmp_path / "p.json", lambda: hoy["d"])
    p.sumar_segundos(60 * 5)
    assert p.racha() == 0                                            # 5 min no bastan para el día
    p.sumar_segundos(60 * 5)
    assert p.racha() == 1
    p.sumar_segundos(60 * 30)
    assert p.racha() == 1                                            # el mismo día no suma dos veces
    for _ in range(2):
        hoy["d"] += timedelta(days=1)
        p.sumar_segundos(60 * 12)
    assert p.racha() == 3 and p.d["mejor_racha"] == 3
    hoy["d"] += timedelta(days=1)
    assert p.racha() == 3                                            # ayer cuenta: aún se puede seguir
    hoy["d"] += timedelta(days=1)
    assert p.racha() == 0                                            # un día sin escuchar la corta
    p.sumar_segundos(60 * 12)
    assert p.racha() == 1 and p.d["mejor_racha"] == 3


def test_progreso_tolera_archivo_roto(tmp_path):
    f = tmp_path / "p.json"
    f.write_text('{"xp": "mucho", "racha": [1]}', encoding="utf-8")
    assert MG.Progreso(f).xp == 0
    f.write_text("###", encoding="utf-8")
    assert MG.Progreso(f).xp == 0


# ------------------------------------------------------------------ OBS

def test_ahora_suena_texto_html_y_escape(tmp_path):
    assert MG.texto_ahora_suena(_pista(1, "Tema", "Yo")) == "Tema 1 — Yo"
    assert MG.texto_ahora_suena({"titulo": "Solo"}) == "Solo" and MG.texto_ahora_suena(None) == ""
    h = MG.html_ahora_suena('<b>Tom & "Jerry"</b>')
    assert "&lt;b&gt;Tom &amp; &quot;Jerry&quot;&lt;/b&gt;" in h and 'http-equiv="refresh"' in h
    c = tmp_path / "obs" / "sub"
    assert MG.escribir_ahora_suena(str(c), _pista(1, "Canción ñ", "Ü"), con_html=True)
    assert (c / "ahora_suena.txt").read_text(encoding="utf-8") == "Canción ñ 1 — Ü"
    assert "Canción ñ 1" in (c / "ahora_suena.html").read_text(encoding="utf-8")
    MG.escribir_ahora_suena(str(c), None, con_html=False)
    assert (c / "ahora_suena.txt").read_text(encoding="utf-8") == ""
    assert "YouTube" in MG.AVISO_DERECHOS and "directos" in MG.AVISO_DERECHOS


def test_obs_sigue_la_cancion_y_solo_con_el_modo_activo(gestor, ctx, tmp_path):
    carpeta = tmp_path / "stream"
    gestor.fijar_obs(activo=True, carpeta=str(carpeta), con_html=True)
    ctx.reproductor.pista_cambio.emit(_pista(1))
    assert not (carpeta / "ahora_suena.txt").exists()                # modo gamer apagado: no escribe
    gestor.activar(True)
    ctx.reproductor.actual = _pista(2)
    ctx.reproductor.estado = "sonando"
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    assert (carpeta / "ahora_suena.txt").read_text(encoding="utf-8") == "Canción 2 — Artista"
    assert (carpeta / "ahora_suena.html").exists()
    ctx.reproductor.estado = "parado"
    ctx.reproductor.estado_cambio.emit("parado")
    assert (carpeta / "ahora_suena.txt").read_text(encoding="utf-8") == ""
    gestor.fijar_obs(activo=False)
    ctx.reproductor.estado = "sonando"
    ctx.reproductor.actual = _pista(3)
    ctx.reproductor.pista_cambio.emit(ctx.reproductor.actual)
    assert (carpeta / "ahora_suena.txt").read_text(encoding="utf-8") == ""


# ------------------------------------------------------------------ detección de pantalla completa

def _info(**k):
    base = {"rect": (0, 0, 1920, 1080), "monitor": (0, 0, 1920, 1080), "clase": "UnrealWindow",
            "pid": 4242, "exe": "juego.exe", "estilo": 0x90000000, "visible": True, "minimizada": False}
    base.update(k)
    return base


def test_juzgar_pantalla_completa():
    f = MG.es_juego_pantalla_completa
    assert f(_info(), 1, [])
    assert f(_info(rect=(-8, -8, 1928, 1088)), 1, [])                # un poco más grande que el monitor
    assert not f(None, 1, [])
    assert not f(_info(rect=(0, 0, 1920, 1040)), 1, [])              # no tapa la barra de tareas
    assert not f(_info(estilo=0x16CF0000), 1, [])                    # maximizada normal: tiene barra de título
    assert not f(_info(clase="Progman"), 1, []) and not f(_info(clase="WorkerW"), 1, [])
    assert not f(_info(pid=7), 7, [])                                # la propia Caudal no cuenta
    assert not f(_info(exe="Chrome.exe"), 1, ["chrome.exe"])
    assert not f(_info(visible=False), 1, []) and not f(_info(minimizada=True), 1, [])
    assert f(_info(rect=(1920, 0, 3840, 1080), monitor=(1920, 0, 3840, 1080)), 1, [])   # segundo monitor


@pytest.mark.skipif(not WIN, reason="Windows")
def test_ventana_en_primer_plano_responde_sin_romper():
    info = MG.ventana_en_primer_plano()
    assert info is None or {"rect", "monitor", "clase", "pid", "exe", "estilo"} <= set(info)
    MG.es_juego_pantalla_completa(info, os.getpid(), [])


# ------------------------------------------------------------------ ahorro al jugar

class _Ventana(QWidget):
    """Una ventana con lo que se anima: capa de fondo, personaje y la barra con su reloj de mascota."""

    def __init__(self):
        super().__init__()
        from PySide6.QtCore import QTimer
        self.capa_fondo = QWidget(self)
        self.personaje_fondo = QWidget(self)
        self.barra = QWidget(self)
        self.singletons = {}
        self.t_mascota = QTimer(self.barra)
        self.t_mascota.setInterval(30)
        self.t_logica = QTimer(self.barra)          # uno lento: no es animación, no se toca
        self.t_logica.setInterval(5000)
        self.t_unica = QTimer(self.barra)
        self.t_unica.setSingleShot(True)
        self.t_unica.setInterval(100)
        self.resize(300, 200)


@pytest.mark.skipif(not WIN, reason="prioridad de proceso de Windows")
def test_ahorro_pausa_animaciones_baja_prioridad_y_restaura(app, ctx):
    v = _Ventana()
    v.show()
    g = MG.GestorGamer(ctx, v)
    visto = []
    g.ahorro_cambio.connect(lambda si, n: visto.append((si, n)))
    v.t_mascota.start()
    v.t_logica.start()
    v.t_unica.start()
    prio0 = MG.prioridad_proceso()
    g.entrar_en_ahorro("juego.exe")
    try:
        assert g.ahorrando and visto == [(True, "juego.exe")]
        assert not v.t_mascota.isActive()
        assert v.t_logica.isActive() and v.t_unica.isActive()        # lo que no anima sigue
        assert not v.capa_fondo.isVisible() and not v.personaje_fondo.isVisible()
        assert MG.prioridad_proceso() == MG.PRIORIDAD_BAJA
        from descargador.ui.neon_gamer import reloj_neon
        assert reloj_neon().pausado
    finally:
        g.salir_de_ahorro()
    assert not g.ahorrando and visto[-1] == (False, "")
    assert v.t_mascota.isActive() and v.capa_fondo.isVisible() and v.personaje_fondo.isVisible()
    assert MG.prioridad_proceso() == prio0
    assert not reloj_neon().pausado
    g.salir_de_ahorro()                                              # repetir no rompe nada
    g.cerrar()
    v.close()


@pytest.mark.skipif(not WIN, reason="prioridad de proceso de Windows")
def test_sondeo_entra_al_ver_un_juego_y_sale_tras_dos_sondeos_sin_juego(app, ctx):
    v = _Ventana()
    v.show()
    g = MG.GestorGamer(ctx, v)
    g.cfg["activo"] = True
    estado = {"info": _info(pid=os.getpid() + 1)}
    g.sondeo = lambda: estado["info"]
    prio0 = MG.prioridad_proceso()
    try:
        g._sondear()
        assert g.ahorrando and g.juego == "juego.exe"
        estado["info"] = _info(pid=os.getpid() + 1, rect=(0, 0, 800, 600))   # alt-tab a otra cosa
        g._sondear()
        assert g.ahorrando                                            # un sondeo suelto no apaga el ahorro
        g._sondear()
        assert not g.ahorrando and MG.prioridad_proceso() == prio0
        estado["info"] = _info(pid=os.getpid() + 1)
        g._sondear()
        assert g.ahorrando
        estado["info"] = _info(pid=os.getpid() + 1, rect=(0, 0, 800, 600))
        g._sondear()
        estado["info"] = _info(pid=os.getpid() + 1)
        g._sondear()                                                  # volvió al juego: se reinicia la cuenta
        assert g._negativos == 0 and g.ahorrando
        g.cfg["activo"] = False
        g.fijar_ahorro(False)                                         # apagar el ahorro lo restaura
        assert not g.ahorrando
        g.sondeo = lambda: (_ for _ in ()).throw(RuntimeError("falla"))
        g._sondear()                                                  # un sondeo que falla no molesta
    finally:
        g.cerrar()
        v.close()
    assert MG.prioridad_proceso() == prio0


def test_sondeo_solo_corre_con_modo_y_ahorro_encendidos(gestor):
    assert not gestor._t_sondeo.isActive()
    gestor.activar(True)
    assert gestor._t_sondeo.isActive() and gestor._t_sondeo.interval() == 3000
    gestor.fijar_ahorro(False)
    assert not gestor._t_sondeo.isActive()
    gestor.fijar_ahorro(True)
    assert gestor._t_sondeo.isActive()
    gestor.activar(False)
    assert not gestor._t_sondeo.isActive()


# ------------------------------------------------------------------ atajos globales (Windows real)

@pytest.mark.skipif(not WIN, reason="RegisterHotKey")
def test_atajos_globales_se_registran_disparan_y_se_liberan(app, ctx):
    import ctypes
    u = ctypes.windll.user32
    g = MG.GestorGamer(ctx, None)
    g.cfg["atajos"] = {a: t for a, t in MG.ATAJOS_DEFECTO.items()}
    # atajos poco probables para no chocar con lo que tenga abierta quien pruebe
    g.cfg["atajos"].update(play="Ctrl+Alt+Shift+F13", siguiente="Ctrl+Alt+Shift+F14",
                           anterior="Ctrl+Alt+Shift+F15", vol_mas="Ctrl+Alt+Shift+F16",
                           vol_menos="Ctrl+Alt+Shift+F17", mini="Ctrl+Alt+Shift+F18",
                           clics="Ctrl+Alt+Shift+F19", hablar="Ctrl+Alt+Shift+F20")
    llamadas = []
    r = ctx.reproductor
    r.alternar = lambda: llamadas.append("play")
    r.siguiente = lambda *a, **k: llamadas.append("siguiente")
    r.anterior = lambda: llamadas.append("anterior")
    g.activar(True)
    try:
        assert g.fallidos == {} and len(g._registrados) == 8
        # Windows entrega la pulsación a la cola del hilo: el filtro la recibe y actúa
        hilo = ctypes.windll.kernel32.GetCurrentThreadId()
        for ident, accion in list(g._registrados.items()):
            if accion in ("play", "siguiente", "anterior"):
                assert u.PostThreadMessageW(hilo, MG.WM_HOTKEY, ident, 0)
        pausa(app, 0.3)
        assert llamadas == ["play", "siguiente", "anterior"]
        # el mismo atajo en otro registro no se deja mientras está tomado
        assert not u.RegisterHotKey(None, 0x7F01, MG.MOD_CTRL | MG.MOD_ALT | MG.MOD_SHIFT, 0x7C)
        # un id ajeno no se toca
        assert g._pulso(0x1234) is False
    finally:
        g.cerrar()
    # liberados al cerrar: ahora sí se pueden volver a pedir
    assert g._registrados == {}
    for vk in range(0x7C, 0x84):
        assert u.RegisterHotKey(None, 0x7F02, MG.MOD_CTRL | MG.MOD_ALT | MG.MOD_SHIFT, vk), hex(vk)
        u.UnregisterHotKey(None, 0x7F02)


@pytest.mark.skipif(not WIN, reason="RegisterHotKey")
def test_atajo_ocupado_se_avisa_y_no_rompe_al_resto(app, ctx):
    import ctypes
    u = ctypes.windll.user32
    assert u.RegisterHotKey(None, 0x7F03, MG.MOD_CTRL | MG.MOD_ALT | MG.MOD_SHIFT, 0x7C)   # F13 tomado
    g = MG.GestorGamer(ctx, None)
    try:
        g.cfg["atajos"].update(play="Ctrl+Alt+Shift+F13", siguiente="Ctrl+Alt+Shift+F14")
        g.activar(True)
        assert "play" in g.fallidos and "otra aplicación" in g.fallidos["play"].lower()
        assert "siguiente" not in g.fallidos and len(g._registrados) == 7
    finally:
        g.cerrar()
        u.UnregisterHotKey(None, 0x7F03)


def test_fijar_atajo_valida_repetidos_y_persiste(gestor):
    assert gestor.fijar_atajo("play", "Ctrl+Alt+P") == (True, "Ctrl+Alt+P")
    assert gestor.cfg["atajos"]["play"] == "Ctrl+Alt+P"
    ok, msg = gestor.fijar_atajo("mini", "Ctrl+Alt+P")
    assert not ok and "Reproducir" in msg and gestor.cfg["atajos"]["mini"] == "Ctrl+Alt+M"
    assert not gestor.fijar_atajo("mini", "M")[0]
    assert not gestor.fijar_atajo("nada", "Ctrl+Alt+Q")[0]
    assert MG.ConfigGamer(gestor.cfg.archivo)["atajos"]["play"] == "Ctrl+Alt+P"
    gestor.restaurar_atajos()
    assert gestor.cfg["atajos"] == MG.ATAJOS_DEFECTO


def test_ejecutar_acciones_llaman_al_reproductor(gestor, ctx):
    r = ctx.reproductor
    vistos = []
    r.alternar = lambda: vistos.append("play")
    r.siguiente = lambda *a, **k: vistos.append("sig")
    r.anterior = lambda: vistos.append("ant")
    for a in ("play", "siguiente", "anterior"):
        gestor.ejecutar(a)
    assert vistos == ["play", "sig", "ant"]
    r.volumen = 50
    gestor.ejecutar("vol_mas")
    assert r.volumen == 55
    gestor.ejecutar("vol_menos")
    gestor.ejecutar("vol_menos")
    assert r.volumen == 45 and ctx.ajustes["volumen"] == 45


# ------------------------------------------------------------------ presets de sonido

def test_presets_usan_el_ecualizador_y_se_restauran(gestor, ctx):
    a = ctx.ajustes
    a["ecualizador"], a["eq_bandas"], a["eq_preset"], a["sonido_envolvente"] = True, [1] * 10, "Pop", False
    avisos = []
    ctx.sonido_cambio.connect(lambda: avisos.append(1))
    for clave, p in MG.PRESETS_SONIDO.items():
        assert len(p["bandas"]) == 10
        assert gestor.aplicar_preset(clave)
        assert a["ecualizador"] is True and a["eq_bandas"] == p["bandas"]
        assert a["eq_preset"] == f"Gamer · {p['nombre']}" and a["sonido_envolvente"] == p["envolvente"]
        assert gestor.cfg["sonido_gamer"] == clave
        assert "equalizer=f=" in ctx.reproductor.cadena_filtros() or not any(p["bandas"])
    assert len(avisos) == 4 and not gestor.aplicar_preset("noexiste")
    # el sonido de antes se guarda solo una vez, con el primer preset
    gestor.restaurar_sonido()
    assert a["eq_bandas"] == [1] * 10 and a["eq_preset"] == "Pop" and a["sonido_envolvente"] is False
    assert gestor.cfg["sonido_gamer"] == "" and gestor.cfg["sonido_previo"] is None
    gestor.restaurar_sonido()                                         # sin nada guardado: plano
    assert a["ecualizador"] is False and a["eq_bandas"] == [0] * 10


# ------------------------------------------------------------------ bajar la música al hablar

def test_hablar_baja_al_25_con_rampa_y_restaura_sin_tocar_lo_guardado(app, gestor, ctx):
    r = ctx.reproductor
    r.fijar_volumen(80)
    vistos = []
    gestor.bajar_volumen()
    assert gestor.cfg["hablar_nivel"] == 25
    esperar(app, lambda: not gestor._rampa.isActive(), "rampa de bajada")
    assert r.volumen == 20 and ctx.ajustes["volumen"] == 80           # 25 % de 80; el guardado sigue en 80
    gestor._hablando = None
    gestor.subir_volumen()
    # la subida es una rampa: pasa por valores intermedios
    vistos.append(r.volumen)
    esperar(app, lambda: not gestor._rampa.isActive(), "rampa de subida")
    assert r.volumen == 80 and gestor._vol_base is None and ctx.ajustes["volumen"] == 80


def test_hablar_la_rampa_es_gradual(app, gestor, ctx):
    r = ctx.reproductor
    r.fijar_volumen(100)
    valores = []
    gestor.bajar_volumen()
    while gestor._rampa.isActive():
        valores.append(r.volumen)
        pausa(app, 0.02)
    assert valores[0] > 25 and r.volumen == 25
    assert len(set(valores)) >= 3 and valores == sorted(valores, reverse=True)


@pytest.mark.skipif(not WIN, reason="GetAsyncKeyState")
def test_hablar_mantener_y_soltar_la_tecla(app, gestor, ctx, monkeypatch):
    r = ctx.reproductor
    r.fijar_volumen(60)
    pulsada = {"v": True}
    monkeypatch.setattr(MG, "tecla_pulsada", lambda vk: pulsada["v"])
    gestor.ejecutar("hablar")
    assert gestor._hablando == ord("V")
    esperar(app, lambda: r.volumen == 15, "bajó al 25 %")
    pausa(app, 0.15)
    assert r.volumen == 15                                            # mientras se mantiene, se queda
    pulsada["v"] = False
    esperar(app, lambda: r.volumen == 60, "volvió", 6)
    assert gestor._hablando is None and not gestor._t_tecla.isActive()
    assert ctx.ajustes["volumen"] == 60
    assert gestor.progreso.contador("hablar") == 1


def test_hablar_el_volumen_pedido_mientras_se_habla_se_respeta(app, gestor, ctx):
    r = ctx.reproductor
    r.fijar_volumen(80)
    gestor.bajar_volumen()
    esperar(app, lambda: not gestor._rampa.isActive(), "bajada")
    gestor.cambiar_volumen(-20)                                       # atajo de volumen mientras se habla
    assert gestor._vol_base == 60
    gestor._hablando = None
    gestor.subir_volumen()
    esperar(app, lambda: not gestor._rampa.isActive(), "subida")
    assert r.volumen == 60


def test_cerrar_devuelve_el_volumen_si_se_cierra_hablando(app, ctx):
    g = MG.GestorGamer(ctx, None)
    ctx.reproductor.fijar_volumen(70)
    g.bajar_volumen()
    pausa(app, 0.1)
    g.cerrar()
    assert ctx.reproductor.volumen == 70


# ------------------------------------------------------------------ listas por situación

def test_cada_situacion_busca_en_el_catalogo_y_reproduce(app, gestor, ctx, monkeypatch):
    from descargador import catalogo
    pedidos = []

    def falsa(q, filtro=None, limite=20):
        pedidos.append((q, filtro))
        return [_pista(i) for i in range(1, 6)] + [{"tipo": "album", "id": "x"}]
    monkeypatch.setattr(catalogo, "buscar", falsa)
    puestas = []
    ctx.reproductor.reproducir_lista = lambda pistas, inicio=0, contexto=None, *a, **k: puestas.append((pistas, contexto))
    assert set(MG.SITUACIONES) == {"lobby", "concentracion", "clutch", "victoria", "derrota"}
    for clave in MG.SITUACIONES:
        fin = []
        assert gestor.reproducir_situacion(clave, fin.append)
        esperar(app, lambda: bool(fin), f"lista {clave}")
        assert fin == [True]
    assert len(puestas) == 5 and all(len(p) == 5 and c["titulo"].startswith("Modo gamer") for p, c in puestas)
    assert all(f == "canciones" for _q, f in pedidos)
    assert gestor.progreso.contador("listas") == 5
    assert not gestor.reproducir_situacion("otra")


def test_situacion_prueba_la_segunda_consulta_y_avisa_si_no_hay(app, gestor, ctx, monkeypatch):
    from descargador import catalogo
    consultas = []

    def vacia(q, filtro=None, limite=20):
        consultas.append(q)
        return []
    monkeypatch.setattr(catalogo, "buscar", vacia)
    avisos = []
    ctx.aviso.connect(avisos.append)
    puestas = []
    ctx.reproductor.reproducir_lista = lambda *a, **k: puestas.append(1)
    fin = []
    gestor.reproducir_situacion("lobby", fin.append)
    esperar(app, lambda: bool(fin), "sin resultados")
    assert fin == [False] and not puestas
    assert consultas == MG.SITUACIONES["lobby"]["consultas"]
    assert any("No encontré" in a for a in avisos)
    # y una búsqueda que falla (sin internet) no tira nada
    monkeypatch.setattr(catalogo, "buscar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sin red")))
    fin.clear()
    gestor.reproducir_situacion("derrota", fin.append)
    esperar(app, lambda: bool(fin), "falla")
    assert fin == [False] and any("No se pudo" in a for a in avisos)


# ------------------------------------------------------------------ XP del gestor

def test_el_gestor_cuenta_minutos_solo_si_suena_y_sube_de_nivel(gestor, ctx, monkeypatch):
    reloj = {"t": 1000.0}
    monkeypatch.setattr(MG.time, "monotonic", lambda: reloj["t"])
    gestor._ultimo_tic = reloj["t"]
    niveles = []
    gestor.subio_nivel.connect(niveles.append)
    ctx.reproductor.estado = "pausa"
    reloj["t"] += 25
    gestor._tic_xp()
    assert gestor.progreso.xp == 0
    ctx.reproductor.estado = "sonando"
    for _ in range(12):                                               # 12 × 25 s, y cada tic mide su tramo
        reloj["t"] += 25
        gestor._tic_xp()
    assert gestor.progreso.d["minutos_total"] == 5
    antes = gestor.progreso.xp
    gestor.progreso.d["xp"] = 49
    gestor._nivel_mostrado = 1
    for _ in range(3):
        reloj["t"] += 25
        gestor._tic_xp()
    assert gestor.progreso.xp >= 50 and niveles == [2] and antes >= 5
    # un salto grande de reloj (PC dormida) no regala horas de XP
    xp = gestor.progreso.xp
    reloj["t"] += 86400
    gestor._tic_xp()
    assert gestor.progreso.xp - xp <= 1 + 40
    assert MG.Progreso(gestor.progreso.archivo).xp == gestor.progreso.xp


def test_cambiar_de_pista_cuenta_para_la_mision(gestor, ctx):
    ctx.reproductor.pista_cambio.emit(_pista(1))
    ctx.reproductor.pista_cambio.emit(_pista(2))
    ctx.reproductor.pista_cambio.emit(None)
    assert gestor.progreso.contador("pistas") == 2


# ------------------------------------------------------------------ mini reproductor

def test_mini_flotante_encima_translucido_sin_foco_y_recuerda_su_sitio(app, gestor, ctx):
    gestor.cfg["mini_opacidad"] = 60
    ctx.reproductor.actual = _pista(1, "Una canción larguísima que no cabe", "Banda")
    m = gestor.mini()
    gestor.mostrar_mini(True)
    assert m.isVisible() and gestor.cfg["mini_visible"]
    fl = m.windowFlags()
    assert fl & Qt.FramelessWindowHint and fl & Qt.WindowStaysOnTopHint and fl & Qt.WindowDoesNotAcceptFocus
    assert m.testAttribute(Qt.WA_TranslucentBackground) and m.testAttribute(Qt.WA_ShowWithoutActivating)
    assert abs(m.windowOpacity() - 0.6) < 0.02
    m.poner_pista(ctx.reproductor.actual)
    assert "Banda" in m.et_artista.text() and m.et_titulo.text().startswith("Una canción")
    assert m.et_titulo.text().endswith("…") or m.et_titulo.text().endswith("1")
    m.move(120, 90)
    m.guardar_posicion()
    assert gestor.cfg["mini_pos"] == [120, 90]
    gestor.mostrar_mini(False)
    assert not m.isVisible() and not gestor.cfg["mini_visible"]
    # otra vez: vuelve a su sitio
    m.move(5, 5)
    gestor.mostrar_mini(True)
    assert (m.x(), m.y()) == (120, 90)
    # una posición guardada fuera de toda pantalla se corrige
    gestor.cfg["mini_pos"] = [99999, 99999]
    gestor.mostrar_mini(False)
    gestor.mostrar_mini(True)
    assert m.x() < 5000
    m.poner_opacidad(10)
    assert gestor.cfg["mini_opacidad"] == 35
    gestor.mostrar_mini(False)


def test_mini_controles_reproducen_pasan_y_ajustan_volumen(app, gestor, ctx):
    r = ctx.reproductor
    vistos = []
    r.alternar = lambda: vistos.append("play")
    r.siguiente = lambda *a, **k: vistos.append("sig")
    m = gestor.mini()
    gestor.mostrar_mini(True)
    m.bt_play.click()
    m.bt_sig.click()
    assert vistos == ["play", "sig"]
    m.volumen.movido.emit(0.35)
    assert r.volumen == 35 and ctx.ajustes["volumen"] == 35
    r.volumen = 80
    m.sincronizar_volumen()
    assert abs(m.volumen.valor - 0.8) < 0.01
    r.estado_cambio.emit("sonando")
    gestor.mostrar_mini(False)


def test_mini_dejar_pasar_los_clics_y_quitarlo_con_el_atajo(app, gestor, ctx):
    m = gestor.mini()
    gestor.mostrar_mini(True)
    assert not m.testAttribute(Qt.WA_TransparentForMouseEvents) and m.controles.isVisible()
    gestor.alternar_clics()                                           # lo que hace Ctrl+Alt+K
    assert gestor.cfg["mini_clics"] and m.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert m.controles.isHidden() and m.bt_cerrar.isHidden()
    assert m.et_pasan.isVisible() and "Ctrl+Alt+K" in m.et_pasan.text()
    gestor.ejecutar("clics")
    assert not gestor.cfg["mini_clics"] and not m.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert not m.controles.isHidden() and m.et_pasan.isHidden()
    gestor.mostrar_mini(False)


@pytest.mark.skipif(not WIN, reason="WS_EX_TRANSPARENT")
def test_clics_pasan_pone_y_quita_ws_ex_transparent_en_una_ventana_real():
    import ctypes
    from ctypes import wintypes as w
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, w.HWND, w.HANDLE, w.HANDLE, w.LPVOID]
    u.CreateWindowExW.restype = w.HWND
    hwnd = u.CreateWindowExW(0, "STATIC", "prueba", 0x80000000, 0, 0, 40, 40, None, None, None, None)
    assert hwnd
    try:
        a = MG._win()
        leer = lambda: a["getp"](w.HWND(hwnd), MG.GWL_EXSTYLE)       # noqa: E731
        assert not leer() & MG.WS_EX_TRANSPARENT
        assert MG.fijar_clics_pasan(hwnd, True)
        assert leer() & MG.WS_EX_TRANSPARENT and leer() & MG.WS_EX_LAYERED and leer() & MG.WS_EX_NOACTIVATE
        assert MG.fijar_clics_pasan(hwnd, True)                       # repetir da lo mismo
        assert MG.fijar_clics_pasan(hwnd, False)
        assert not leer() & MG.WS_EX_TRANSPARENT
    finally:
        u.DestroyWindow(hwnd)
    assert MG.fijar_clics_pasan(0, True) is False                     # sin ventana real: no revienta


# ------------------------------------------------------------------ neón

def test_neon_reloj_solo_corre_con_algo_visible_y_se_apaga(app, gestor, ctx):
    from descargador.ui.neon_gamer import MarcoNeon, reloj_neon
    rl = reloj_neon()
    marco = MarcoNeon()
    marco.resize(200, 100)
    assert not rl.activo
    marco.show()
    assert rl.activo and rl._t.interval() == 50                       # 20 cuadros por segundo
    f0 = rl.fase
    pausa(app, 0.25)
    assert rl.fase != f0
    gestor.fijar_neon(False)
    assert not rl.activo and not gestor.cfg["neon"]
    gestor.fijar_neon(True)
    assert rl.activo
    rl.pausar(True)
    assert not rl.activo
    rl.pausar(False)
    marco.hide()
    assert not rl.activo
    marco.deleteLater()


def test_neon_se_pinta_con_y_sin_efecto(app):
    from PySide6.QtGui import QImage
    from descargador.ui.neon_gamer import MarcoNeon, reloj_neon
    marco = MarcoNeon(18, 2.0)
    marco.resize(240, 90)
    marco.show()
    reloj_neon().activar(True)
    a = marco.grab().toImage()
    reloj_neon().activar(False)
    b = marco.grab().toImage()
    reloj_neon().activar(True)
    assert isinstance(a, QImage) and a != b
    marco.close()


# ------------------------------------------------------------------ pantalla y ventana completa

@pytest.fixture
def ventana(app, ctx, monkeypatch):
    from descargador import fondo as F
    from descargador.ui.ventana import Ventana
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: 0)
    monkeypatch.setattr(Ventana, "buscar_version", lambda self, *a, **k: None)
    monkeypatch.setattr(Ventana, "_avisar_novedades", lambda self, *a, **k: None)
    monkeypatch.setattr(F.GestorFondo, "sincronizar", lambda self: None)
    ctx.cuenta = {"usuario": "ana", "nombre": "Ana", "sesion": None}
    v = Ventana(ctx)
    yield v
    try:
        v.gamer.cerrar()
    finally:
        v.hide()
        from descargador.ui.neon_gamer import reloj_neon
        reloj_neon().pausar(False)
        reloj_neon().activar(True)


def test_la_ventana_trae_el_modo_gamer_en_la_navegacion(app, ventana, ctx):
    from descargador.ui.panel_lateral import PanelLateral
    assert any(c == "gamer" for c, _t, _i in PanelLateral.NAV + PanelLateral.NAV_MAS)
    assert ctx.gamer is ventana.gamer
    assert not ventana.gamer.activo and not ventana.gamer._registrados   # apagado de fábrica
    ventana.show()
    ventana.navegar({"pagina": "gamer"})
    pausa(app, 0.2)
    from descargador.ui.paginas.modo_gamer import PaginaModoGamer
    pag = ventana.pila.currentWidget()
    assert isinstance(pag, PaginaModoGamer)
    assert ventana.lateral.botones["gamer"]._activo
    ventana.hide()


def test_pantalla_modo_gamer_muestra_y_cambia_todo(app, ventana, ctx, tmp_path):
    from descargador.ui.paginas.modo_gamer import PaginaModoGamer
    g = ventana.gamer
    ventana.resize(1100, 900)
    ventana.show()
    ventana.navegar({"pagina": "gamer"})
    pag = ventana.pila.currentWidget()
    assert isinstance(pag, PaginaModoGamer)
    pausa(app, 0.2)
    # nivel y misiones
    assert pag.et_nivel.text() == "Nivel 1 · Novato" and len(pag.filas_misiones) == 3
    assert all(tx.text() for tx, _b, _e in pag.filas_misiones)
    g.progreso.evento("sonidos", 1)
    g.progreso.d["xp"] = 160
    g._tras_xp(0, 1)
    assert pag.et_nivel.text().startswith("Nivel 3") and "160 XP" in pag.et_xp.text()
    # interruptor general
    assert not pag.sw_activo.isChecked()
    pag.sw_activo.setChecked(True)
    assert g.activo and pag.et_activo.text().startswith("Atajos")
    # los atajos se ven y se cambian
    assert pag.editores["play"].keySequence().toString() == "Ctrl+Alt+Space"
    pag.editores["play"].setKeySequence(__import__("PySide6.QtGui", fromlist=["QKeySequence"]).QKeySequence("Ctrl+Alt+J"))
    pag._cambiar_atajo("play", pag.editores["play"])
    assert g.cfg["atajos"]["play"] == "Ctrl+Alt+J"
    pag.editores["mini"].setKeySequence(__import__("PySide6.QtGui", fromlist=["QKeySequence"]).QKeySequence("Ctrl+Alt+J"))
    pag._cambiar_atajo("mini", pag.editores["mini"])
    assert "Reproducir" in pag.msg_atajos.text() and g.cfg["atajos"]["mini"] == "Ctrl+Alt+M"
    assert pag.editores["mini"].keySequence().toString() == "Ctrl+Alt+M"
    # mini, clics, opacidad
    pag.bt_mini.click()
    assert g._mini.isVisible() and pag.bt_mini.text() == "Ocultar"
    pag.sw_clics.setChecked(True)
    assert g.cfg["mini_clics"]
    pag.sw_clics.setChecked(False)
    pag.sl_opacidad.setValue(50)
    assert g.cfg["mini_opacidad"] == 50 and abs(g._mini.windowOpacity() - 0.5) < 0.02
    pag.bt_mini.click()
    assert pag.bt_mini.text() == "Mostrar"
    # sonido
    pag.chips_sonido["fps"].click()
    assert ctx.ajustes["eq_preset"] == "Gamer · FPS" and pag.chips_sonido["fps"].isChecked()
    assert "FPS" in pag.et_sonido.text()
    # hablar
    pag.sl_hablar.setValue(40)
    assert g.cfg["hablar_nivel"] == 40 and pag.et_hablar.text() == "40 %"
    # ahorro
    pag.ed_ignorar.setText("Foo.exe, bar.exe")
    pag._guardar_ignorar()
    assert g.cfg["ignorar"] == ["foo.exe", "bar.exe"]
    g.entrar_en_ahorro("juego.exe")
    assert "juego.exe" in pag.et_ahorro.text()
    g.salir_de_ahorro()
    assert "normal" in pag.et_ahorro.text()
    pag.sw_ahorro.setChecked(False)
    assert not g.cfg["ahorro"] and pag.et_ahorro.text() == "Apagado."
    # OBS: aviso de derechos siempre visible
    assert pag.et_derechos.isVisible() and "YouTube" in pag.et_derechos.text()
    pag.sw_obs.setChecked(True)
    pag.sw_html.setChecked(True)
    assert g.cfg["obs"] and g.cfg["obs_html"]
    g.fijar_obs(carpeta=str(tmp_path / "obs_x"))
    assert str(tmp_path / "obs_x") == pag.et_carpeta.text()
    # neón
    pag.sw_neon.setChecked(False)
    assert not g.cfg["neon"]
    pag.sw_neon.setChecked(True)
    # captura para revisar el diseño
    pausa(app, 0.1)
    pag.lienzo.grab().save(os.path.join(CAPTURAS, "pantalla_modo_gamer.png"))
    # con la ventana más chica (mínimo 940) la página pide poco ancho
    ventana.resize(940, 700)
    pausa(app, 0.2)
    assert pag.lienzo.minimumSizeHint().width() <= 360
    pag.lienzo.grab().save(os.path.join(CAPTURAS, "pantalla_modo_gamer_angosta.png"))
    ventana.hide()


def test_pantalla_sobrevive_a_un_modo_apagado_y_a_cerrar(app, ventana, ctx):
    ventana.show()
    ventana.navegar({"pagina": "gamer"})
    pausa(app, 0.1)
    ventana.navegar({"pagina": "inicio"})
    pausa(app, 0.1)
    ventana.gamer.activar(True)
    ventana.gamer.activar(False)
    assert ventana.gamer._registrados == {}
    ventana.hide()


def test_captura_del_mini(app, gestor, ctx):
    ctx.reproductor.actual = _pista(1, "Neon Nights", "Synthwave Club")
    ctx.reproductor.estado = "sonando"
    m = gestor.mini()
    gestor.mostrar_mini(True)
    m.poner_pista(ctx.reproductor.actual)
    pausa(app, 0.1)
    img = m.grab()
    assert not img.isNull() and img.width() == 352
    img.save(os.path.join(CAPTURAS, "mini_gamer.png"))
    gestor.mostrar_mini(False)
