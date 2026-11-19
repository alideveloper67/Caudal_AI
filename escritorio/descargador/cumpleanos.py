# -*- coding: utf-8 -*-
"""«Feliz cumpleaños»: las reglas (puras, sin red) y lo que la app sabe hoy. Igual que app/lib/nucleo/cumpleanos.dart.

- El día se mira con la fecha LOCAL. Quien nació un 29 de febrero lo celebra el 28 en los años no bisiestos.
- La celebración sale UNA sola vez al día (se anota antes de enseñarla: si la cierran, no vuelve a salir).
- De los amigos solo se sabe QUIÉN cumple hoy (supabase/cumpleanos.sql, función `amigos_cumplen_hoy`):
  nunca su fecha de nacimiento.
"""

from datetime import date, datetime

from PySide6.QtCore import QObject, Signal

CLAVE_AJUSTE = "cumple_celebrado"


def es_bisiesto(anio):
    return (anio % 4 == 0 and anio % 100 != 0) or anio % 400 == 0


def _dia(d):
    return d.date() if isinstance(d, datetime) else d


def es_cumple(nacimiento, hoy):
    """¿`hoy` es el día de cumpleaños de quien nació el `nacimiento`?"""
    if nacimiento is None:
        return False
    nac, hoy = _dia(nacimiento), _dia(hoy)
    dia = nac.day
    if nac.month == 2 and dia == 29 and not es_bisiesto(hoy.year):
        dia = 28
    return hoy.month == nac.month and hoy.day == dia


def edad_que_cumple(nacimiento, hoy):
    """La edad que cumple hoy; None si la fecha no tiene sentido (futura, de hoy mismo o de más de 120 años)."""
    if nacimiento is None:
        return None
    e = _dia(hoy).year - _dia(nacimiento).year
    return e if 1 <= e <= 120 else None


def clave_dia(d):
    d = _dia(d)
    return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"


def _ids(respuesta):
    """Los ids de la respuesta de la nube (texto suelto o filas de un solo campo)."""
    salida = []
    for x in respuesta if isinstance(respuesta, list) else []:
        if isinstance(x, dict) and x:
            x = next(iter(x.values()))
        if isinstance(x, str) and x:
            salida.append(x)
    return salida


class EstadoCumple(QObject):
    cambiado = Signal()

    def __init__(self):
        super().__init__()
        self.ahora = date.today          # el reloj (las pruebas lo cambian)
        self.mi_id = ""
        self.nombre = ""
        self.nacimiento = None
        self.perfil_leido = False
        self._amigos = set()
        self._dia_amigos = ""

    # ---- lo que se sabe
    @property
    def es_mio_hoy(self):
        return es_cumple(self.nacimiento, self.ahora())

    @property
    def edad(self):
        return edad_que_cumple(self.nacimiento, self.ahora())

    @property
    def amigos_hoy(self):
        return frozenset(self._amigos) if self._dia_amigos == clave_dia(self.ahora()) else frozenset()

    def es_de(self, persona_id):
        """¿Esta persona (yo o un amigo) cumple hoy? Sin id, no."""
        if not persona_id:
            return False
        if persona_id == self.mi_id:
            return self.es_mio_hoy
        return persona_id in self.amigos_hoy

    # ---- ponerlo a mano (la app al leer el perfil y las pruebas)
    def poner(self, mi_id=None, nombre=None, nacimiento=None, amigos=None):
        if mi_id is not None:
            self.mi_id = mi_id
        if nombre is not None:
            self.nombre = nombre
        if nacimiento is not None:
            self.nacimiento = nacimiento
        if amigos is not None:
            self._amigos = {a for a in amigos if a and a != self.mi_id}
            self._dia_amigos = clave_dia(self.ahora())
        self.cambiado.emit()

    def reiniciar(self):
        self.mi_id = ""
        self.nombre = ""
        self.nacimiento = None
        self.perfil_leido = False
        self._amigos = set()
        self._dia_amigos = ""
        self.cambiado.emit()

    # ---- la nube (bloquea: usar en segundo plano)
    def leer_de_la_nube(self, sesion):
        """Mi fecha y los amigos que cumplen hoy. Devuelve (perfil, ids); un fallo de red deja None / None."""
        perfil = ids = None
        try:
            from . import legal
            perfil = legal.perfil(sesion)
        except Exception:  # noqa: BLE001 - sin red no pasa nada
            perfil = None
        try:
            ids = _ids(sesion.rpc("amigos_cumplen_hoy"))
        except Exception:  # noqa: BLE001
            ids = None
        return perfil, ids

    def aplicar(self, sesion, resultado):
        """Guarda lo que trajo `leer_de_la_nube` (en el hilo de la ventana)."""
        perfil, ids = resultado
        self.mi_id = getattr(sesion, "user_id", "") or self.mi_id
        if perfil:
            self.nacimiento = perfil.get("nacimiento")
            primero = (perfil.get("nombre") or "").strip().split(" ")[0]
            if primero:
                self.nombre = primero
        self.perfil_leido = True
        self.poner(amigos=ids)          # con None conserva lo que había

    # ---- una sola vez al día
    def toca_celebrar(self, ajustes):
        return self.es_mio_hoy and ajustes[CLAVE_AJUSTE] != clave_dia(self.ahora())

    def marcar_celebrado(self, ajustes):
        ajustes[CLAVE_AJUSTE] = clave_dia(self.ahora())
        ajustes.guardar()


ESTADO = EstadoCumple()
