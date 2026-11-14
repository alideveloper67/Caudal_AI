# -*- coding: utf-8 -*-
"""«Escuchar juntos»: piezas sueltas y una sala REAL en Supabase Realtime con
dos clientes Python (mismo protocolo que la app movil, supabase/JUNTOS.md).

La prueba de red se salta solo si no hay internet hasta Supabase.
"""

import os
import socket
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import juntos as J  # noqa: E402


class ReproductorFalso(J.Control):
    """Reproductor de mentira cuyo tiempo avanza con el reloj de verdad."""

    def __init__(self, demora_carga=0.3):
        self.pista = None
        self._sonando = False
        self._base = 0
        self._desde = 0
        self._cargando_hasta = 0
        self.demora = demora_carga
        self.cargas = 0
        self.saltos = 0
        self._cerrojo = threading.Lock()

    @staticmethod
    def _ahora():
        return J.ahora_ms()

    @property
    def cargando(self):
        return self._ahora() < self._cargando_hasta

    @property
    def posicion_ms(self):
        with self._cerrojo:
            if self.cargando:
                return self._base
            corre = self._sonando and self._desde
            return self._base + (self._ahora() - max(self._desde, self._cargando_hasta)
                                 if corre else 0)

    @property
    def sonando(self):
        return self._sonando and not self.cargando

    def cargar(self, pista, inicio_ms=0, pausado=False):
        with self._cerrojo:
            self.cargas += 1
            self.pista = dict(pista)
            self._base = int(inicio_ms)
            self._cargando_hasta = self._ahora() + int(self.demora * 1000)
            self._desde = self._cargando_hasta
            self._sonando = not pausado

    def buscar(self, ms):
        with self._cerrojo:
            self.saltos += 1
            self._base = int(ms)
            self._desde = self._ahora()

    def pausar(self):
        b = self.posicion_ms
        with self._cerrojo:
            self._base = b
            self._sonando = False

    def reanudar(self):
        with self._cerrojo:
            self._desde = self._ahora()
            self._sonando = True

    def poner(self, pista, en_ms):
        """Lo que haria el usuario del anfitrion."""
        with self._cerrojo:
            self.pista = dict(pista)
            self._base = int(en_ms)
            self._desde = self._ahora()
            self._cargando_hasta = 0
            self._sonando = True


def hasta_que(condicion, que, maximo=20):
    fin = time.time() + maximo
    while not condicion():
        if time.time() > fin:
            pytest.fail(f"No pasó a tiempo: {que}")
        time.sleep(0.1)


# ---------------------------------------------------------------- piezas

def test_codigo_y_enlace():
    c = J.nuevo_codigo()
    assert len(c) == 6 and all(x in J.ALFABETO for x in c)
    assert J.codigo_de_texto(c) == c
    assert J.codigo_de_texto(J.enlace_sala(c)) == c
    assert J.codigo_de_texto(" ab-c 234 ") == "ABC234"
    assert J.codigo_de_texto("https://caudal.app/juntos?sala=XYZ789") == "XYZ789"
    assert J.codigo_de_texto("hola") is None
    assert J.codigo_de_texto("ABCDEF0") is None
    assert J.codigo_de_texto("ABCDE0") is None     # el 0 no existe en el alfabeto


def test_posicion_esperada_con_reloj_del_anfitrion():
    # el anfitrion va 10 s adelantado y mando "30 s" hace 2 s (de su reloj)
    assert J.posicion_esperada(30000, True, 1000000 + 8000, 10000, ahora_local=1000000) == 32000
    assert J.posicion_esperada(30000, False, 0, 0) == 30000


def test_pista_compartida_sin_rutas_locales():
    p = J.pista_para_compartir({"video_id": "a", "titulo": "t", "archivo": "/x.m4a",
                                "raro": [1], "album": {}, "duracion": 200, "nada": None})
    assert p == {"video_id": "a", "titulo": "t", "duracion": 200}
    assert J.clave_pista({"video_id": "abc", "clave": "yt:abc"}) == "v:abc"
    assert J.clave_pista(None) == ""


class _CanalFalso:
    """Canal sin red: guarda lo que se difunde."""

    def __init__(self):
        self.presentes = {}
        self.enviado = []

    def difundir(self, ev, d):
        self.enviado.append((ev, d))

    def presentarme(self, _d):
        pass

    def abrir(self):
        pass

    def cerrar(self):
        pass


def _sala_sin_red(anfitrion, control):
    s = J.SalaJuntos("ABC234", control, "Yo", anfitrion=anfitrion)
    s.canal = _CanalFalso()
    s.abrir()
    s._al_abierto(None)
    return s


def test_invitado_corrige_deriva_de_mas_de_1500_ms():
    c = ReproductorFalso(demora_carga=0)
    s = _sala_sin_red(False, c)
    pista = {"video_id": "dQw4w9WgXcQ", "titulo": "Prueba"}
    t = J.ahora_ms()
    s._al_mensaje("estado", {"de": "HOST", "rango": 1, "seq": 1, "pista": pista,
                             "pos": 30000, "sonando": True, "t": t})
    assert c.pista["video_id"] == "dQw4w9WgXcQ" and c.cargas == 1
    assert s.anfitrion_id == "HOST"
    # dentro del margen: no salta
    c.buscar(c.posicion_ms + 1000)
    c.saltos = 0
    s._seguir()
    assert c.saltos == 0
    # fuera del margen: salta a la posicion del anfitrion
    c.buscar(c.posicion_ms + 5000)
    c.saltos = 0
    s._ultimo_salto = 0
    s._seguir()
    assert c.saltos == 1
    assert abs(c.posicion_ms - J.posicion_esperada(30000, True, t, 0)) < 400
    # pausa del anfitrion
    s._al_mensaje("estado", {"de": "HOST", "rango": 1, "seq": 2, "pista": pista,
                             "pos": 31000, "sonando": False, "t": J.ahora_ms()})
    assert not c.sonando


def test_invitado_avisa_si_la_pista_es_un_archivo_local():
    c = ReproductorFalso(demora_carga=0)
    s = _sala_sin_red(False, c)
    s._al_mensaje("estado", {"de": "HOST", "rango": 1, "seq": 1,
                             "pista": {"titulo": "Mi demo", "clave": "local:3"},
                             "pos": 0, "sonando": True, "t": J.ahora_ms()})
    assert c.cargas == 0 and "archivo" in (s.aviso or "")


def test_dos_anfitriones_gana_el_mas_antiguo():
    a = _sala_sin_red(True, ReproductorFalso())
    a._rango_anfitrion = 2000
    a._al_mensaje("estado", {"de": "VIEJO", "rango": 1000, "pista": None, "pos": 0,
                             "sonando": False, "t": J.ahora_ms()})
    assert a.anfitrion_id == "VIEJO" and not a.soy_anfitrion
    b = _sala_sin_red(True, ReproductorFalso())
    b._rango_anfitrion = 1000
    b.canal.enviado.clear()
    b._al_mensaje("estado", {"de": "NUEVO", "rango": 2000, "pista": None, "pos": 0,
                             "sonando": False, "t": J.ahora_ms()})
    assert b.soy_anfitrion and b.canal.enviado[-1][0] == "estado"


def test_anfitrion_responde_ping_y_hola():
    s = _sala_sin_red(True, ReproductorFalso())
    s.canal.enviado.clear()
    s._al_mensaje("ping", {"de": "INV", "a": s.mi_id, "t0": 123})
    ev, d = s.canal.enviado[-1]
    assert ev == "pong" and d["para"] == "INV" and d["t0"] == 123 and isinstance(d["th"], int)
    s._al_mensaje("ping", {"de": "INV", "a": "OTRO", "t0": 1})
    assert len(s.canal.enviado) == 1


def test_eleccion_de_anfitrion_por_antiguedad():
    s = _sala_sin_red(False, ReproductorFalso())
    s.canal.presentes = {"ZZZ": {"nombre": "A", "entro": 100}, "AAA": {"nombre": "B", "entro": 100},
                         "MMM": {"nombre": "C", "entro": 50}, s.mi_id: {"entro": s._entro}}
    s.anfitrion_id = "MMM"
    del s.canal.presentes["MMM"]
    s._al_presencia()
    assert s.anfitrion_id == "AAA"   # mismo "entro": desempata el id


# ---------------------------------------------------------------- sala real

def _hay_red():
    try:
        socket.create_connection(("nztirmwqykbxadidpzzt.supabase.co", 443), timeout=8).close()
        return True
    except OSError:
        return False


def _abrir(bucle, sala):
    resultado = {}
    listo = threading.Event()

    def al_abierta(error):
        resultado["e"] = error
        listo.set()

    sala.al_abierta = al_abierta
    bucle.salas.append(sala)
    bucle.llamar(sala.abrir)
    assert listo.wait(30), "la sala no abrió"
    if resultado["e"] is not None:
        pytest.fail(f"Realtime no disponible: {resultado['e']}")


@pytest.mark.skipif(not _hay_red(), reason="sin internet hasta Supabase")
def test_sala_real_dos_clientes_python():
    bucle_a, bucle_b = J.BucleSimple(), J.BucleSimple()
    a, b = ReproductorFalso(), ReproductorFalso()
    cancion = {"video_id": "dQw4w9WgXcQ", "titulo": "Prueba", "artista": "Caudal",
               "duracion": 213, "archivo": "C:/no/se/manda.m4a"}
    a.poner(cancion, 30000)
    reacciones_a = []
    anf = J.SalaJuntos(J.nuevo_codigo(), a, "Ana", "ana", anfitrion=True,
                       despachar=bucle_a.despachar,
                       al_reaccion=lambda e, n, mio: reacciones_a.append((e, n, mio)))
    inv = J.SalaJuntos(J.codigo_de_texto(anf.enlace), b, "Beto", "beto",
                       despachar=bucle_b.despachar)
    try:
        _abrir(bucle_a, anf)
        assert anf.soy_anfitrion
        _abrir(bucle_b, inv)
        hasta_que(lambda: len(anf.miembros) == 2 and len(inv.miembros) == 2, "los dos en la lista")
        assert {m.nombre for m in inv.miembros} == {"Ana", "Beto"}

        hasta_que(lambda: (b.pista or {}).get("video_id") == "dQw4w9WgXcQ", "el invitado carga")
        assert "archivo" not in b.pista
        assert inv.anfitrion_id == anf.mi_id and not inv.soy_anfitrion
        hasta_que(lambda: b.sonando and abs(b.posicion_ms - a.posicion_ms) < 1500, "van a la par")

        # pausa
        bucle_a.llamar(lambda: (a.pausar(), anf.al_cambiar_reproductor()))
        hasta_que(lambda: not b.sonando, "la pausa llega")
        hasta_que(lambda: abs(b.posicion_ms - a.posicion_ms) < 1500, "pausados en el mismo punto")

        # seguir y saltar (el anfitrion nota el salto solo)
        bucle_a.llamar(lambda: (a.reanudar(), a.buscar(120000), anf.al_cambiar_reproductor()))
        hasta_que(lambda: b.sonando and abs(b.posicion_ms - a.posicion_ms) < 1500, "el salto llega")
        assert b.posicion_ms >= 119000

        # deriva del invitado (p. ej. tocó la barra): se corrige solo
        b.buscar(b.posicion_ms + 9000)
        hasta_que(lambda: abs(b.posicion_ms - a.posicion_ms) < 1500, "corrige la deriva")

        # otra cancion
        bucle_a.llamar(lambda: (a.poner({"video_id": "kJQP7kiw5Fk", "titulo": "Otra",
                                          "duracion": 280}, 5000), anf.al_cambiar_reproductor()))
        hasta_que(lambda: (b.pista or {}).get("video_id") == "kJQP7kiw5Fk", "cambia la canción")
        hasta_que(lambda: abs(b.posicion_ms - a.posicion_ms) < 1500, "a la par otra vez")

        # reacciones
        bucle_b.llamar(lambda: inv.reaccionar("🔥"))
        hasta_que(lambda: ("🔥", "Beto", False) in reacciones_a, "la reacción llega")

        # el anfitrion se va: el invitado pasa a serlo
        bucle_a.llamar(anf.salir)
        hasta_que(lambda: inv.soy_anfitrion, "pasa el mando", maximo=40)
        hasta_que(lambda: len(inv.miembros) == 1, "queda uno")
    finally:
        bucle_a.llamar(anf.salir)
        bucle_b.llamar(inv.salir)
        bucle_a.parar()
        bucle_b.parar()


def test_chat_de_la_sala():
    vistos = []
    s = _sala_sin_red(True, ReproductorFalso())
    s.al_chat = vistos.append
    s.canal.enviado.clear()
    assert s.enviar_chat("  hola a todos 🎉  ")
    ev, d = s.canal.enviado[-1]
    assert ev == "chat" and d["texto"] == "hola a todos 🎉" and d["nombre"] == "Yo"
    assert not s.enviar_chat("   ")
    # llega uno de otro (y uno roto que se ignora)
    s._al_mensaje("chat", {"de": "OTRO", "nombre": "Ana", "texto": "x" * 900, "t": 5})
    s._al_mensaje("chat", {"de": "OTRO", "texto": ""})
    assert [m["texto"][:5] for m in vistos] == ["hola ", "xxxxx"]
    assert len(vistos[-1]["texto"]) == J.LARGO_CHAT
    # quien entra recibe lo ultimo del chat
    s.canal.enviado.clear()
    s._al_mensaje("hola", {"de": "NUEVO"})
    ev, d = [x for x in s.canal.enviado if x[0] == "chat_historial"][0]
    assert d["para"] == "NUEVO" and len(d["mensajes"]) == 2
    nuevo = _sala_sin_red(False, ReproductorFalso())
    llegados = []
    nuevo.al_chat = llegados.append
    nuevo._al_mensaje("chat_historial", {"para": nuevo.mi_id, "mensajes": d["mensajes"]})
    assert len(llegados) == 2 and len(nuevo.chat) == 2
