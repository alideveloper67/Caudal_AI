# -*- coding: utf-8 -*-
"""Lo premium de la cuenta activa: estado (donador, fundador o prueba), pase de prueba, y la
personalización (marco, efecto del nombre y tema de colores).

Igual que el fondo de Caudal: se guarda una copia local (para que al abrir se vea al instante, sin
esperar a la red) y se refresca desde el servidor en segundo plano. NADA de esto bloquea la ventana:
todas las llamadas a la nube van por `en_segundo_plano`. El servidor decide quién tiene beneficios;
aquí solo se pregunta y se aplica."""

import json
import time

from PySide6.QtCore import QObject, Signal

from . import nube
from . import social as S
from .config import carpeta_perfil
from .hilos import en_segundo_plano
from .premium_datos import (NINGUNO, EstadoPremium, efecto_valido, marco_valido, tema_valido,
                            texto_vencimiento)

PREFIJO_TEMA = "premium_"
ASPECTO_NORMAL = ("cian", "oscuro")


def aspecto_de_tema(clave):
    """(acento, fondo) que se guardan en los ajustes para un tema premium; None si es «ninguno»."""
    clave = tema_valido(clave)
    return None if clave == NINGUNO else (PREFIJO_TEMA + clave, PREFIJO_TEMA + clave)


def es_aspecto_premium(acento, fondo):
    return str(acento or "").startswith(PREFIJO_TEMA) or str(fondo or "").startswith(PREFIJO_TEMA)


def _archivo():
    return carpeta_perfil() / "premium.json"


def leer_copia_local():
    try:
        return json.loads(_archivo().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def revertir_aspecto_si_hace_falta(ajustes):
    """Se llama al arrancar, ANTES de pintar nada: si los ajustes llevan un tema premium y la cuenta ya
    no tiene beneficios (según la copia local), vuelven los colores de antes (o los de siempre).
    Devuelve True si cambió algo. Solo lee un archivo pequeño: no toca la red."""
    try:
        if not es_aspecto_premium(ajustes["acento"], ajustes["fondo"]):
            return False
        copia = leer_copia_local()
        estado = EstadoPremium(copia.get("premium"), copia.get("tipo"), copia.get("vence"))
        if estado.vigente():
            return False
        previo = copia.get("aspecto_previo") or list(ASPECTO_NORMAL)
        if es_aspecto_premium(*previo):
            previo = list(ASPECTO_NORMAL)
        ajustes["acento"], ajustes["fondo"] = previo[0], previo[1]
        ajustes.guardar()
        return True
    except Exception:  # noqa: BLE001
        return False


class GestorPremium(QObject):
    """El estado y la personalización de la cuenta activa."""

    cambiado = Signal()           # el estado o la personalización cambiaron (para repintar)
    aspecto_cambiado = Signal()   # el tema premium se puso o se quitó (prueba vencida, otro equipo...): reaplicar colores

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.estado = EstadoPremium()
        self.marco = NINGUNO
        self.efecto = NINGUNO
        self.tema = NINGUNO
        self.aspecto_previo = list(ASPECTO_NORMAL)
        self._aviso_dia = ""
        self._pidiendo = False
        self._cargar_local()

    # ------------------------------------------------------------ copia local
    def _cargar_local(self):
        d = leer_copia_local()
        self.estado = EstadoPremium(d.get("premium"), d.get("tipo"), d.get("vence"))
        self.marco = marco_valido(d.get("marco"))
        self.efecto = efecto_valido(d.get("efecto"))
        self.tema = tema_valido(d.get("tema"))
        previo = d.get("aspecto_previo")
        if isinstance(previo, list) and len(previo) == 2:
            self.aspecto_previo = [str(previo[0]), str(previo[1])]
        self._aviso_dia = str(d.get("aviso_dia") or "")

    def _guardar_local(self):
        try:
            d = self.estado.a_dict()
            d.update(marco=self.marco, efecto=self.efecto, tema=self.tema,
                     aspecto_previo=self.aspecto_previo, aviso_dia=self._aviso_dia)
            _archivo().write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------ lectura
    @property
    def premium(self):
        return self.estado.vigente()

    @property
    def tipo(self):
        return self.estado.tipo if self.premium else None

    def dias_de_prueba(self):
        return self.estado.dias_restantes()

    def marco_efectivo(self):
        """Lo que se pinta: sin beneficios no se ve nada, aunque quede algo guardado."""
        return self.marco if self.premium else NINGUNO

    def efecto_efectivo(self):
        return self.efecto if self.premium else NINGUNO

    def tema_efectivo(self):
        return self.tema if self.premium else NINGUNO

    def _social(self):
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        sesion = cuenta.get("sesion")
        return S.Social(sesion) if sesion is not None else None

    # ------------------------------------------------------------ nube (siempre en segundo plano)
    def refrescar(self):
        """Pregunta al servidor el estado y la personalización. No bloquea."""
        social = self._social()
        if social is None or self._pidiendo:
            return
        self._pidiendo = True

        def trabajo():
            estado = EstadoPremium.desde_servidor(social.mi_premium())
            try:
                pers = social.leer_personalizacion()
            except nube.ErrorNube:
                pers = None
            return estado, pers

        def listo(res):
            self._pidiendo = False
            self._aplicar_remoto(*res)

        def fallo(_e):
            self._pidiendo = False      # sin red: se queda lo que ya se sabía
        en_segundo_plano(trabajo, ok=listo, error=fallo)

    def _aplicar_remoto(self, estado, pers):
        antes = self.estado
        tenia_tema = self.tema_efectivo() != NINGUNO
        self.estado = estado
        if pers:
            self.marco = marco_valido(pers.get("marco"))
            self.efecto = efecto_valido(pers.get("efecto_nombre"))
            self.tema = tema_valido(pers.get("tema_premium"))
        self._guardar_local()
        self.cambiado.emit()
        if estado != antes:
            self._refrescar_permisos()
        if not self.premium and (tenia_tema or self._ajustes_con_tema()):
            self._volver_al_aspecto_normal()
        elif self.premium:
            self._alinear_aspecto_con_el_perfil()
            if estado != antes:
                self._avisar_vencimiento()

    def _ajustes_con_tema(self):
        a = getattr(self.ctx, "ajustes", None)
        return a is not None and es_aspecto_premium(a["acento"], a["fondo"])

    def _refrescar_permisos(self):
        """El fondo de Caudal y la mascotita (que cuelga de su permiso) se desbloquean o se bloquean al momento,
        sin reiniciar. Va en segundo plano."""
        fondo = getattr(self.ctx, "fondo", None)
        if fondo is not None and hasattr(fondo, "verificar_permiso"):
            fondo.verificar_permiso()

    def _alinear_aspecto_con_el_perfil(self):
        """El tema que dice el perfil manda también en este equipo (lo elegiste en otro): se pone, o se quita."""
        a = getattr(self.ctx, "ajustes", None)
        if a is None:
            return
        actual = (str(a["acento"]), str(a["fondo"]))
        deseado = aspecto_de_tema(self.tema)
        if deseado is not None and actual != deseado:
            if not es_aspecto_premium(*actual):
                self.aspecto_previo = [actual[0], actual[1]]
                self._guardar_local()
            a["acento"], a["fondo"] = deseado
            a.guardar()
            self.aspecto_cambiado.emit()
        elif deseado is None and es_aspecto_premium(*actual):
            self._volver_al_aspecto_normal()

    def aspecto_elegido_a_mano(self):
        """Ajustes › Aspecto aplicó colores normales: el tema premium deja de ser el elegido (y así se guarda)."""
        a = getattr(self.ctx, "ajustes", None)
        if a is None or es_aspecto_premium(a["acento"], a["fondo"]) or self.tema == NINGUNO:
            return
        self.tema = NINGUNO
        self._guardar_local()
        self.cambiado.emit()
        self._subir()

    def _volver_al_aspecto_normal(self):
        a = getattr(self.ctx, "ajustes", None)
        if a is None or not self._ajustes_con_tema():
            return
        previo = self.aspecto_previo
        if es_aspecto_premium(*previo):
            previo = list(ASPECTO_NORMAL)
        a["acento"], a["fondo"] = previo[0], previo[1]
        a.guardar()
        self.aspecto_cambiado.emit()

    def _avisar_vencimiento(self):
        """Un aviso discreto, una vez al día, cuando a la prueba le quedan pocos días."""
        dias = self.estado.dias_restantes()
        if dias is None or dias > 3:
            return
        hoy = time.strftime("%Y-%m-%d")
        if self._aviso_dia == hoy:
            return
        self._aviso_dia = hoy
        self._guardar_local()
        aviso = getattr(self.ctx, "aviso", None)
        if aviso is not None:
            aviso.emit(texto_vencimiento(dias))

    def canjear(self, codigo, ok=None, error=None):
        """Canjea un código de prueba en segundo plano. `ok(resultado)` recibe {ok, mensaje, dias, vence}."""
        social = self._social()
        if social is None:
            if error:
                error(nube.ErrorNube("Inicia sesión para canjear un código."))
            return

        def trabajo():
            res = social.canjear_pase(codigo)
            if res.get("ok"):
                estado = EstadoPremium.desde_servidor(social.mi_premium())
                return res, estado
            return res, None

        def listo(par):
            res, estado = par
            if res.get("ok") and estado is not None:
                self.estado = estado
                self._guardar_local()
                self.cambiado.emit()
                self._refrescar_permisos()
            if ok:
                ok(res)
        en_segundo_plano(trabajo, ok=listo, error=error or (lambda _e: None))

    # ------------------------------------------------------------ pases de regalo (donadores y fundadores)
    @property
    def puede_regalar(self):
        """Solo quien dona de verdad: la prueba no puede regalar pruebas."""
        return self.premium and self.estado.tipo in ("donador", "fundador")

    def _regalo(self, trabajo, ok, error, dueno):
        social = self._social()
        if social is None:
            if error:
                error(nube.ErrorNube("Inicia sesión para regalar códigos."))
            return
        en_segundo_plano(lambda: trabajo(social), ok=ok, error=error or (lambda _e: None), dueno=dueno)

    def crear_regalo(self, ok=None, error=None, dueno=None):
        """Crea un código de regalo en segundo plano. `ok(resultado)` recibe {ok, codigo, dias, caduca, mensaje}."""
        self._regalo(lambda s: s.crear_pase_regalo(), ok, error, dueno)

    def mis_regalos(self, ok=None, error=None, dueno=None):
        """Los códigos que creé, en segundo plano. `ok(lista)`."""
        self._regalo(lambda s: s.mis_pases_regalo(), ok, error, dueno)

    def anular_regalo(self, codigo, ok=None, error=None, dueno=None):
        """Anula un código que nadie usó. `ok(True/False)`."""
        self._regalo(lambda s: s.anular_pase_regalo(codigo), ok, error, dueno)

    def guardar_personalizacion(self, marco=None, efecto=None, tema=None, alerta=None):
        """Aplica y guarda lo elegido: local al instante y en la nube en segundo plano.
        Devuelve True si el tema cambió (hay que reaplicar los colores). Sin beneficios no hace nada."""
        if not self.premium:
            return False
        cambia_tema = False
        if marco is not None:
            self.marco = marco_valido(marco)
        if efecto is not None:
            self.efecto = efecto_valido(efecto)
        if tema is not None:
            nuevo = tema_valido(tema)
            cambia_tema = nuevo != self.tema
            if cambia_tema:
                a = getattr(self.ctx, "ajustes", None)
                if a is not None and not es_aspecto_premium(a["acento"], a["fondo"]):
                    self.aspecto_previo = [str(a["acento"]), str(a["fondo"])]
                self.tema = nuevo
                self._poner_aspecto()
        self._guardar_local()
        self.cambiado.emit()
        self._subir(alerta)
        return cambia_tema

    def _poner_aspecto(self):
        a = getattr(self.ctx, "ajustes", None)
        if a is None:
            return
        destino = aspecto_de_tema(self.tema)
        if destino is None:
            previo = self.aspecto_previo
            destino = tuple(ASPECTO_NORMAL if es_aspecto_premium(*previo) else previo)
        a["acento"], a["fondo"] = destino[0], destino[1]
        a.guardar()

    def _subir(self, alerta=None):
        social = self._social()
        if social is None:
            return
        campos = {"marco": self.marco, "efecto_nombre": self.efecto, "tema_premium": self.tema}

        def fallo(e):
            if alerta is not None:
                alerta("Se ve aquí, pero no se pudo guardar en tu cuenta. " + S.explicar(e, "guardarlo"))
        en_segundo_plano(social.guardar_perfil, campos, error=fallo)
