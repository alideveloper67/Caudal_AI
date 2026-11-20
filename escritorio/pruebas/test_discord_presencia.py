# -*- coding: utf-8 -*-
"""Discord Rich Presence con un Discord de mentira (sin abrir la tubería real): conecta, actualiza,
pausa, se limpia, Discord ausente no rompe, reconecta, ID vacío = apagado, ID inválido no insiste."""

import os
import sys
import tempfile
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="caudal_pruebas_discord_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from descargador import discord_presencia as D  # noqa: E402


class DiscordFalso:
    """Lo que haría la app de Discord al otro lado de la tubería."""

    def __init__(self):
        self.abierto = False
        self.id_valido = True
        self.rechaza_tipo = False
        self.actividades = []        # cada SET_ACTIVITY recibido (None = quitar)
        self.conexiones = 0
        self.intentos = 0
        self.saludos = []
        self.vivas = []

    def fabrica(self):
        return ConexionFalsa(self)

    def cortar(self):
        """Se cierra Discord con Caudal conectado."""
        self.abierto = False
        for c in self.vivas:
            c.rota = True


class ConexionFalsa:
    def __init__(self, servidor):
        self.s = servidor
        self.cola = []
        self.rota = False

    def conectar(self):
        self.s.intentos += 1
        if not self.s.abierto:
            raise D.ErrorIPC("Discord no está abierto.")
        self.s.conexiones += 1
        self.s.vivas.append(self)

    def enviar(self, op, carga):
        if self.rota:
            raise D.ErrorIPC("tubería rota")
        if op == D.OP_SALUDO:
            self.s.saludos.append(carga)
            if not self.s.id_valido:
                self.cola.append((D.OP_CIERRE, {"code": 4000, "message": "Invalid Client ID"}))
            else:
                self.cola.append((D.OP_MARCO, {"cmd": "DISPATCH", "evt": "READY", "data": {"v": 1}}))
            return
        if op == D.OP_PONG:
            self.s.pongs = getattr(self.s, "pongs", 0) + 1
            return
        act = carga["args"].get("activity")
        if self.s.rechaza_tipo and act and "type" in act:
            self.cola.append((D.OP_MARCO, {"cmd": "SET_ACTIVITY", "evt": "ERROR", "nonce": carga["nonce"],
                                           "data": {"code": 4000, "message": "type is not allowed"}}))
            return
        self.s.actividades.append(act)
        # a veces Discord pide un ping en medio: el cliente debe contestar y seguir
        self.cola.append((D.OP_PING, {"hola": 1}))
        self.cola.append((D.OP_MARCO, {"cmd": "SET_ACTIVITY", "evt": None, "nonce": carga["nonce"], "data": act}))

    def recibir(self):
        if self.rota or not self.cola:
            raise D.ErrorIPC("sin respuesta")
        return self.cola.pop(0)

    def cerrar(self):
        if self in self.s.vivas:
            self.s.vivas.remove(self)


def esperar(cond, segundos=3.0):
    fin = time.time() + segundos
    while time.time() < fin:
        if cond():
            return True
        time.sleep(0.01)
    return cond()


PISTA = {"clave": "yt:abc", "video_id": "abc", "titulo": "Despacio", "artista": "Ana",
         "album": {"nombre": "Disco Uno"}, "duracion": 200,
         "miniatura": "https://i.ytimg.com/vi/abc/hqdefault.jpg"}


@pytest.fixture
def discord():
    return DiscordFalso()


def presencia(discord, **k):
    k.setdefault("reintento", 0.05)
    k.setdefault("entre_envios", 0)
    return D.PresenciaDiscord("1234567890", fabrica=discord.fabrica, **k)


def test_id_vacio_queda_apagado_sin_errores(discord):
    discord.abierto = True
    p = D.PresenciaDiscord("", fabrica=discord.fabrica)
    assert not p.disponible
    p.actualizar(PISTA, "sonando", 10, 200)
    p.poner_activa(True)
    p.limpiar()
    p.detener()
    assert discord.intentos == 0 and p._hilo is None
    # y el ID de verdad sigue vacío hasta que el dueño lo pegue
    assert D.ID_APLICACION_DISCORD == "" or D.ID_APLICACION_DISCORD.isdigit()


def test_conecta_y_muestra_la_cancion(discord):
    discord.abierto = True
    p = presencia(discord)
    antes = time.time()
    p.actualizar(PISTA, "sonando", 30, 200)
    assert esperar(lambda: discord.actividades)
    assert discord.saludos[0] == {"v": 1, "client_id": "1234567890"}
    a = discord.actividades[-1]
    assert a["type"] == D.TIPO_ESCUCHANDO
    assert a["details"] == "Despacio" and a["state"] == "Ana"
    assert a["assets"]["large_image"] == PISTA["miniatura"] and a["assets"]["large_text"] == "Disco Uno"
    assert a["assets"]["small_image"] == "logo"
    assert a["buttons"] == [{"label": "Escuchar en Caudal", "url": "https://caudal-musica.netlify.app"}]
    t = a["timestamps"]
    assert t["end"] - t["start"] == 200_000
    assert abs(t["start"] / 1000 - (antes - 30)) < 2
    p.detener()


def test_pausa_y_parar(discord):
    discord.abierto = True
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 5, 200)
    assert esperar(lambda: len(discord.actividades) == 1)
    p.actualizar(PISTA, "pausa", 40, 200)
    assert esperar(lambda: len(discord.actividades) == 2)
    a = discord.actividades[-1]
    assert a["state"] == "En pausa · Ana" and "timestamps" not in a
    p.actualizar(PISTA, "parado")
    assert esperar(lambda: len(discord.actividades) == 3)
    assert discord.actividades[-1] is None
    p.detener()


def test_pausa_larga_se_quita(discord):
    discord.abierto = True
    ahora = [1000.0]
    p = presencia(discord, reloj=lambda: ahora[0])
    p.actualizar(PISTA, "pausa", 40, 200)
    assert esperar(lambda: discord.actividades and discord.actividades[-1] is not None)
    ahora[0] += D.PAUSA_MAX_S + 5
    assert esperar(lambda: discord.actividades[-1] is None)
    p.detener()


def test_mismo_estado_no_se_reenvia(discord):
    discord.abierto = True
    p = presencia(discord)
    for _ in range(5):
        p.actualizar(PISTA, "sonando", 30, 200)
    assert esperar(lambda: discord.actividades)
    time.sleep(0.2)
    assert len(discord.actividades) == 1
    p.detener()


def test_discord_ausente_no_rompe_y_aparece_al_abrirlo(discord):
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 0, 200)          # Discord cerrado: ni error ni actividad
    assert esperar(lambda: discord.intentos >= 2)
    assert discord.actividades == []
    discord.abierto = True                          # se abre Discord después
    assert esperar(lambda: discord.actividades)
    assert discord.actividades[-1]["details"] == "Despacio"
    p.detener()


def test_discord_se_cierra_y_vuelve(discord):
    discord.abierto = True
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 0, 200)
    assert esperar(lambda: len(discord.actividades) == 1)
    discord.cortar()
    p.actualizar(dict(PISTA, titulo="Otra"), "sonando", 0, 180)
    assert esperar(lambda: discord.intentos >= 3)       # reintenta en silencio
    assert not p.conectada
    discord.abierto = True
    assert esperar(lambda: discord.actividades[-1] and discord.actividades[-1]["details"] == "Otra")
    p.detener()


def test_id_invalido_no_insiste(discord):
    discord.abierto = True
    discord.id_valido = False
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 0, 200)
    assert esperar(lambda: p.id_invalido)
    time.sleep(0.3)
    assert discord.intentos == 1
    p.actualizar(PISTA, "pausa", 3, 200)
    time.sleep(0.2)
    assert discord.intentos == 1
    p.detener()


def test_discord_viejo_sin_tipo_escuchando(discord):
    discord.abierto = True
    discord.rechaza_tipo = True
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 0, 200)
    assert esperar(lambda: discord.actividades)
    assert "type" not in discord.actividades[-1]
    assert discord.actividades[-1]["details"] == "Despacio"
    p.detener()


def test_desactivar_y_cerrar_limpian(discord):
    discord.abierto = True
    p = presencia(discord)
    p.actualizar(PISTA, "sonando", 0, 200)
    assert esperar(lambda: len(discord.actividades) == 1)
    p.poner_activa(False)
    assert esperar(lambda: discord.actividades[-1] is None)
    p.poner_activa(True)
    assert esperar(lambda: discord.actividades[-1] is not None)
    p.detener()
    assert discord.actividades[-1] is None            # al cerrar Caudal se quita del perfil
    assert not p._hilo.is_alive()


def test_sin_boton(discord):
    discord.abierto = True
    p = presencia(discord)
    p.poner_boton(False)
    p.actualizar(PISTA, "sonando", 0, 200)
    assert esperar(lambda: discord.actividades)
    assert "buttons" not in discord.actividades[-1]
    p.detener()


def test_actividad_textos_y_caratulas():
    larga = "x" * 300
    a = D.actividad_de({"titulo": larga, "artistas": [{"nombre": "Uno"}, {"nombre": "Dos"}],
                        "miniatura": "C:/caratulas/local.jpg"}, "sonando", 0, 0, ahora=100)
    assert len(a["details"]) == 128 and a["details"].endswith("…")
    assert a["state"] == "Uno, Dos"
    assert a["assets"]["large_image"] == "logo" and "small_image" not in a["assets"]
    assert "end" not in a["timestamps"]            # sin duración: solo «transcurrido»
    corta = D.actividad_de({"titulo": "Y", "artista": ""}, "sonando", 0, 60, ahora=100)
    assert len(corta["details"]) >= 2 and corta["state"] == "Caudal"
    assert D.actividad_de(PISTA, "parado") is None and D.actividad_de(None, "sonando") is None


def test_ajuste_guardado(tmp_path):
    assert D.leer_ajuste(tmp_path) == {"activo": True, "boton": True}      # activado por defecto
    D.guardar_ajuste({"activo": False, "boton": True}, tmp_path)
    assert D.leer_ajuste(tmp_path) == {"activo": False, "boton": True}


def test_enganche_con_el_reproductor(discord, tmp_path):
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])

    class ReproductorFalso(QObject):
        pista_cambio = Signal(object)
        estado_cambio = Signal(str)
        posicion_cambio = Signal(float)
        duracion_cambio = Signal(float)

        def __init__(self):
            super().__init__()
            self.actual, self.estado, self._posicion, self._duracion = None, "parado", 0.0, 0.0

    r = ReproductorFalso()
    discord.abierto = True
    e = D.enganchar(r, presencia(discord), carpeta=tmp_path)
    r.actual, r.estado, r._duracion = PISTA, "sonando", 200.0
    r.pista_cambio.emit(PISTA)
    assert esperar(lambda: discord.actividades and discord.actividades[-1])
    n = len(discord.actividades)
    r._posicion = 120.0
    r.posicion_cambio.emit(120.0)                  # adelantar: cambian los tiempos
    assert esperar(lambda: len(discord.actividades) > n)
    t = discord.actividades[-1]["timestamps"]
    assert abs((t["end"] / 1000 - time.time()) - 80) < 3
    e.poner_activa(False)
    assert esperar(lambda: discord.actividades[-1] is None)
    assert D.leer_ajuste(tmp_path)["activo"] is False
    e.p.detener()

    # sin ID: el enganche ni escucha al reproductor
    vacio = D.enganchar(ReproductorFalso(), D.PresenciaDiscord(""), carpeta=tmp_path)
    assert not vacio.disponible
