# -*- coding: utf-8 -*-
"""Modo estudio: perfiles de música, temporizador de enfoque, constancia y notas.

Todo lo de este archivo es lógica: no dibuja nada y se puede probar sin ventanas.
Lo que se elige se guarda en la carpeta de la cuenta, en ficheros propios (los ajustes
generales de Caudal se comparten con la app del teléfono y esto es solo de este equipo).

* `PERFILES` y `cola_del_perfil`: qué se busca en el catálogo y cómo se quitan las
  canciones con voz cuando hay alternativas.
* `Temporizador`: Pomodoro / trabajo profundo con la HORA DE FIN (no cuenta tics),
  rondas y descanso largo opcional. El reloj es inyectable para probarlo.
* `Estadisticas`: tiempo estudiado por día, últimos 7 días y racha, sin presión.
* `Notas`: «Captura de ideas», con fecha, locales.
* `Configuracion`: lo elegido, con valores seguros.
* `ControladorEstudio`: lo une con el reproductor y con los sonidos ambientales.
"""

import json
import os
import time
import uuid
from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from . import config, disco

# ---------------------------------------------------------------------- perfiles

CAPAS_ORDEN = ("lluvia", "cafeteria", "bosque", "chimenea", "blanco", "rosa", "marron")

# clave -> datos del perfil. `mezcla`: volumen sugerido (0-100) de cada capa; las que no
# aparecen quedan apagadas. `colores`: los dos tonos de su tarjeta.
PERFILES = {
    "leer": {
        "nombre": "Leer / Escribir",
        "lema": "Sin letra, muy calmado",
        "detalle": "Lo-fi, ambient y piano",
        "icono": "libro",
        "colores": ("#2B4C5C", "#5C4A66"),
        "consultas": ["lofi piano instrumental para estudiar",
                      "ambient piano relaxing instrumental",
                      "lofi beats to study and relax no lyrics",
                      "peaceful piano music for focus"],
        "mezcla": {"lluvia": 32, "chimenea": 14},
    },
    "programar": {
        "nombre": "Programar / Analizar",
        "lema": "Ritmo constante, sin sorpresas",
        "detalle": "Electrónica instrumental y synthwave suave",
        "icono": "codigo",
        "colores": ("#24407A", "#2F6D74"),
        "consultas": ["deep focus electronic instrumental",
                      "chill synthwave instrumental focus",
                      "coding music instrumental electronic study",
                      "ambient electronic music for concentration"],
        "mezcla": {"rosa": 22, "cafeteria": 12},
    },
    "repasar": {
        "nombre": "Repasar / Memorizar",
        "lema": "Estable y sin distracciones",
        "detalle": "Clásica, baroque y ambient instrumental",
        "icono": "tarjetas",
        "colores": ("#5A4A2A", "#2F5A4A"),
        "consultas": ["baroque classical music for studying",
                      "bach instrumental focus music",
                      "classical piano music for concentration",
                      "ambient instrumental music for memorizing"],
        "mezcla": {"bosque": 26, "marron": 10},
    },
    "relajarme": {
        "nombre": "Relajarme",
        "lema": "Para bajar el ritmo",
        "detalle": "Ambient suave, piano y lo-fi tranquilo",
        "icono": "hoja",
        "colores": ("#4F3A5E", "#2D5C6A"),
        "consultas": ["relaxing ambient music instrumental",
                      "calm piano music to relax",
                      "peaceful instrumental ambient music",
                      "chill lofi beats relaxing no lyrics"],
        "mezcla": {"lluvia": 40, "chimenea": 24, "bosque": 12},
    },
}
PERFIL_INICIAL = "leer"

# palabras que anuncian música sin voz
_BUENAS = ("instrumental", "lofi", "lo-fi", "lo fi", "ambient", "piano", "study", "focus",
           "sin letra", "no lyrics", "concentra", "estudio", "estudiar", "baroque", "bach",
           "classical", "clásica", "clasica", "synthwave", "calm", "relax", "peaceful",
           "meditation", "chillhop", "chill", "soft", "deep focus", "sleep", "concentration")
# y palabras que casi siempre significan canción con letra o videoclip
_MALAS = ("official video", "official music video", "music video", "video oficial", "ft.",
          "feat.", "feat ", "featuring", "lyrics", "lyric video", "letra", "karaoke", "(live",
          "en vivo")


def puntaje_instrumental(pista):
    """Cuánto parece de música sin voz: mayor es mejor; negativo = parece canción con letra."""
    texto = " ".join(str(pista.get(k) or "") for k in ("titulo", "artista")) + " " + \
        str((pista.get("album") or {}).get("nombre") or "")
    t = texto.lower()
    puntos = min(6, sum(2 for w in _BUENAS if w in t))
    if any(w in t for w in _MALAS):
        puntos -= 6
    if pista.get("explicito"):
        puntos -= 3
    dur = int(pista.get("duracion") or 0)
    if 0 < dur < 80:
        puntos -= 2
    elif dur > 1800:
        puntos += 1
    return puntos


def filtrar_pistas(pistas, minimo=8):
    """Quita las repetidas y deja primero lo que parece sin voz. Lo que parece canción con
    letra solo se usa si, sin ello, quedarían menos de `minimo` canciones."""
    vistas, limpias = set(), []
    for p in pistas or []:
        if not isinstance(p, dict) or p.get("tipo", "pista") != "pista":
            continue
        clave = p.get("video_id") or p.get("clave") or p.get("archivo")
        if not clave or clave in vistas:
            continue
        vistas.add(clave)
        limpias.append(p)
    buenas = [p for p in limpias if puntaje_instrumental(p) > 0]
    neutras = [p for p in limpias if puntaje_instrumental(p) == 0]
    malas = [p for p in limpias if puntaje_instrumental(p) < 0]
    salida = buenas + neutras
    if len(salida) < minimo:
        salida += sorted(malas, key=puntaje_instrumental, reverse=True)
    return salida


def cola_del_perfil(clave, buscar, por_consulta=14, minimo=8):
    """La cola de un perfil: sus consultas al catálogo, mezcladas por turnos para que el
    estilo cambie despacio, y sin canciones con voz si hay otras. `buscar(texto)` devuelve
    elementos del catálogo; una consulta que falla no impide las demás."""
    perfil = PERFILES.get(clave) or PERFILES[PERFIL_INICIAL]
    listas = []
    for consulta in perfil["consultas"]:
        try:
            r = buscar(consulta) or []
        except Exception:  # noqa: BLE001 - sin red una consulta no debe romper las demás
            r = []
        listas.append([p for p in r if isinstance(p, dict) and p.get("tipo", "pista") == "pista"
                       ][:por_consulta])
    turnos = []
    for i in range(max((len(x) for x in listas), default=0)):
        for x in listas:
            if i < len(x):
                turnos.append(x[i])
    return filtrar_pistas(turnos, minimo)


# ---------------------------------------------------------------------- temporizador

PRESETS_POMODORO = {"25/5": (25, 5), "50/10": (50, 10), "90/15": (90, 15)}
FASES_ACTIVAS = ("enfoque", "descanso", "descanso_largo")
NOMBRE_FASE = {"enfoque": "Enfoque", "descanso": "Descanso", "descanso_largo": "Descanso largo",
               "inactivo": "", "completo": "Sesión completa"}


class Temporizador:
    """Bloques de enfoque y descanso con la hora de fin. Pausar guarda lo que falta y
    reanudar calcula una hora de fin nueva; el reloj puede ser cualquier función."""

    def __init__(self, reloj=time.time):
        self.reloj = reloj
        self.enfoque = 25.0
        self.descanso = 5.0
        self.largo = 0.0
        self.rondas = 4
        self.cada = 4
        self.reiniciar()

    def reiniciar(self):
        self.fase = "inactivo"
        self.ronda = 0
        self.duracion = 0.0
        self._fin = 0.0
        self._pausa = None
        self._enfocado = 0.0

    def configurar(self, enfoque, descanso, rondas=4, largo=0, cada=4):
        self.enfoque = max(0.01, float(enfoque))
        self.descanso = max(0.0, float(descanso))
        self.rondas = max(1, int(rondas))
        self.largo = max(0.0, float(largo))
        self.cada = max(1, int(cada))

    # ---- estado
    def activo(self):
        return self.fase in FASES_ACTIVAS

    def en_pausa(self):
        return self._pausa is not None

    def restante(self):
        if not self.activo():
            return 0.0
        if self._pausa is not None:
            return self._pausa
        return max(0.0, self._fin - self.reloj())

    def progreso(self):
        if not self.activo() or self.duracion <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.restante() / self.duracion))

    def enfocado_total(self):
        """Segundos de enfoque de verdad de toda la sesión (sin pausas ni descansos)."""
        parcial = (self.duracion - self.restante()) if self.fase == "enfoque" else 0.0
        return self._enfocado + max(0.0, parcial)

    # ---- acciones
    def _entrar(self, fase):
        minutos = {"enfoque": self.enfoque, "descanso": self.descanso,
                   "descanso_largo": self.largo}[fase]
        self.fase = fase
        self.duracion = minutos * 60.0
        self._fin = self.reloj() + self.duracion
        self._pausa = None

    def iniciar(self):
        self.reiniciar()
        self.ronda = 1
        self._entrar("enfoque")

    def pausar(self):
        if self.activo() and self._pausa is None:
            self._pausa = self.restante()

    def reanudar(self):
        if self.activo() and self._pausa is not None:
            self._fin = self.reloj() + self._pausa
            self._pausa = None

    def terminar(self):
        """Termina la sesión; devuelve los segundos de enfoque que llevaba."""
        total = self.enfocado_total()
        self.reiniciar()
        return total

    def saltar(self):
        """Pasa a la fase siguiente sin esperar. Devuelve los eventos, como `revisar`."""
        if not self.activo():
            return []
        return [self._cerrar(saltando=True)]

    def revisar(self):
        """Avanza las fases cuya hora ya llegó. Si el equipo estuvo dormido, solo se pasa
        a la fase siguiente (que empieza ahora): nada de disparar varias campanas de golpe."""
        if self.activo() and self._pausa is None and self.reloj() >= self._fin:
            return [self._cerrar(saltando=False)]
        return []

    def _cerrar(self, saltando):
        if self.fase == "enfoque":
            hecho = (self.duracion - self.restante()) if saltando else self.duracion
            self._enfocado += max(0.0, hecho)
            ev = {"tipo": "fin_enfoque", "ronda": self.ronda, "segundos": hecho,
                  "rondas": self.rondas, "completa": self.ronda >= self.rondas}
            if ev["completa"]:
                self.fase = "completo"
                self.duracion, self._fin, self._pausa = 0.0, 0.0, None
                ev["siguiente"] = "completo"
            else:
                largo = self.largo > 0 and self.ronda % self.cada == 0
                sig = "descanso_largo" if largo else "descanso"
                if (self.largo if largo else self.descanso) <= 0:
                    # sin descanso configurado: se sigue con la ronda siguiente
                    self.ronda += 1
                    sig = "enfoque"
                self._entrar(sig)
                ev["siguiente"] = sig
            return ev
        # fin de un descanso
        self.ronda += 1
        self._entrar("enfoque")
        return {"tipo": "fin_descanso", "ronda": self.ronda, "segundos": 0.0,
                "rondas": self.rondas, "completa": False, "siguiente": "enfoque"}


def formato_reloj(segundos):
    """mm:ss (o h:mm:ss) para el temporizador grande; sube al segundo siguiente
    para que «0:00» solo se vea al terminar."""
    s = int(max(0.0, segundos) + 0.999)
    h, r = divmod(s, 3600)
    m, seg = divmod(r, 60)
    return f"{h}:{m:02d}:{seg:02d}" if h else f"{m:02d}:{seg:02d}"


def formato_duracion(segundos):
    """«1 h 25 min», «40 min», «Menos de 1 min»."""
    s = int(segundos or 0)
    if s < 60:
        return "0 min" if s <= 0 else "Menos de 1 min"
    h, m = divmod(s // 60, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


# ---------------------------------------------------------------------- guardado

def _carpeta():
    return config.carpeta_perfil()


def _leer_json(ruta, defecto):
    try:
        disco.vaciar(ruta)
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def _escribir_json(ruta, datos):
    """Lo escribe un hilo aparte y de una vez (disco.py): un corte de luz no deja el archivo a medias."""
    try:
        disco.escribir(ruta, json.dumps(datos, ensure_ascii=False, indent=1))
    except (OSError, TypeError, ValueError):
        pass


# ---------------------------------------------------------------------- constancia

MINUTOS_DE_RACHA = 5     # un día cuenta para la racha desde 5 minutos de enfoque


class Estadisticas:
    """Tiempo estudiado por día (historial local). Sin metas ni reproches."""

    def __init__(self, ruta=None, reloj=time.time):
        self.ruta = ruta or (_carpeta() / "estudio_historial.json")
        self.reloj = reloj
        datos = _leer_json(self.ruta, {})
        self.dias = {str(k): int(v) for k, v in (datos.get("dias") or {}).items()
                     if isinstance(v, (int, float))}
        self.sesiones = list(datos.get("sesiones") or [])[-200:]

    def hoy_fecha(self):
        return datetime.fromtimestamp(self.reloj()).date()

    def guardar(self):
        _escribir_json(self.ruta, {"dias": self.dias, "sesiones": self.sesiones[-200:]})

    def sumar(self, segundos, dia=None):
        segundos = int(round(segundos or 0))
        if segundos <= 0:
            return
        k = (dia or self.hoy_fecha()).isoformat()
        self.dias[k] = self.dias.get(k, 0) + segundos
        self.guardar()

    def anotar_sesion(self, segundos, perfil="", bloques=0):
        if int(segundos or 0) < 60:
            return
        self.sesiones.append({"fecha": datetime.fromtimestamp(self.reloj()).isoformat(
            timespec="seconds"), "segundos": int(segundos), "perfil": perfil,
            "bloques": int(bloques)})
        self.sesiones = self.sesiones[-200:]
        self.guardar()

    def de_dia(self, dia=None):
        return self.dias.get((dia or self.hoy_fecha()).isoformat(), 0)

    def hoy(self):
        return self.de_dia()

    def ultimos_dias(self, n=7):
        """[(fecha, segundos)] de los últimos n días, el de hoy al final."""
        hoy = self.hoy_fecha()
        return [(hoy - timedelta(days=i), self.de_dia(hoy - timedelta(days=i)))
                for i in range(n - 1, -1, -1)]

    def semana(self):
        return sum(s for _d, s in self.ultimos_dias(7))

    def racha(self):
        """Días seguidos con estudio. Si hoy aún no estudiaste, la racha de ayer sigue
        viva hasta que termine el día: no se rompe antes de tiempo."""
        minimo = MINUTOS_DE_RACHA * 60
        dia = self.hoy_fecha()
        if self.de_dia(dia) < minimo:
            dia -= timedelta(days=1)
        n = 0
        while self.de_dia(dia) >= minimo:
            n += 1
            dia -= timedelta(days=1)
        return n

    def mejor_racha(self):
        minimo = MINUTOS_DE_RACHA * 60
        fechas = sorted(date.fromisoformat(k) for k, v in self.dias.items() if v >= minimo)
        mejor = actual = 0
        previa = None
        for f in fechas:
            actual = actual + 1 if previa is not None and f - previa == timedelta(days=1) else 1
            mejor = max(mejor, actual)
            previa = f
        return mejor

    def frase(self):
        """Un texto amable sobre cómo vas; nunca un regaño."""
        hoy, racha = self.hoy(), self.racha()
        if hoy <= 0 and racha <= 0 and not self.dias:
            return "Cuando quieras empezar, aquí te acompañamos."
        if hoy <= 0:
            if racha > 0:
                return f"Llevas {racha} {'día' if racha == 1 else 'días'} seguidos. Hoy puedes seguir con calma."
            return "Hoy es un buen día para volver, a tu ritmo."
        if racha >= 7:
            return f"{racha} días seguidos. Qué constancia tan bonita."
        if racha >= 2:
            return f"{racha} días seguidos. Vas por buen camino."
        return "Buen comienzo. Cada rato cuenta."


# ---------------------------------------------------------------------- notas

class Notas:
    """«Captura de ideas»: notas cortas con fecha, en este equipo."""

    MAXIMO = 500

    def __init__(self, ruta=None, reloj=time.time):
        self.ruta = ruta or (_carpeta() / "estudio_notas.json")
        self.reloj = reloj
        datos = _leer_json(self.ruta, [])
        self.lista = [n for n in datos if isinstance(n, dict) and n.get("texto")] \
            if isinstance(datos, list) else []

    def todas(self):
        return list(self.lista)

    def anadir(self, texto):
        texto = (texto or "").strip()
        if not texto:
            return None
        nota = {"id": uuid.uuid4().hex[:12], "texto": texto[:4000],
                "fecha": datetime.fromtimestamp(self.reloj()).isoformat(timespec="seconds")}
        self.lista.insert(0, nota)
        del self.lista[self.MAXIMO:]
        _escribir_json(self.ruta, self.lista)
        return nota

    def borrar(self, ident):
        n = len(self.lista)
        self.lista = [x for x in self.lista if x.get("id") != ident]
        if len(self.lista) != n:
            _escribir_json(self.ruta, self.lista)
            return True
        return False

    def deshacer_borrado(self, nota):
        """Vuelve a poner una nota borrada por error (en su orden por fecha)."""
        if nota and not any(x.get("id") == nota.get("id") for x in self.lista):
            self.lista.append(nota)
            self.lista.sort(key=lambda x: x.get("fecha", ""), reverse=True)
            _escribir_json(self.ruta, self.lista)


MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def fecha_amable(iso, ahora=None):
    """«Hoy, 14:32» · «Ayer, 9:05» · «12 nov, 18:20»."""
    try:
        f = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    ahora = ahora or datetime.now()
    hora = f"{f.hour}:{f.minute:02d}"
    if f.date() == ahora.date():
        return f"Hoy, {hora}"
    if f.date() == ahora.date() - timedelta(days=1):
        return f"Ayer, {hora}"
    return f"{f.day} {MESES[f.month - 1]}, {hora}"


# ---------------------------------------------------------------------- configuración

DEFECTOS = {
    "perfil": PERFIL_INICIAL,
    "pomodoro": "25/5",          # 25/5 | 50/10 | 90/15 | personalizado
    "enfoque_min": 25,
    "descanso_min": 5,
    "rondas": 4,
    "descanso_largo_min": 0,     # 0 = sin descanso largo (tras cada 4 rondas)
    "al_descansar": "bajar",     # bajar | pausar | seguir (la música base)
    "atenuar": True,             # bajar ~35 % la música base mientras dura el enfoque
    "campana": True,
    "mezcla_del_perfil": True,   # al elegir un perfil, se pone su mezcla sugerida
    "capas": {},                 # capa -> {"on": bool, "vol": 0-100}
    "calido": False,             # modo oscuro cálido
    "brillo": 55,                # «Brillo cálido» 0-100
    "despierto": False,          # mantener el equipo despierto
    "candado": False,            # mantener pulsado 2 s para salir
}
ATENUACION_ENFOQUE = 0.65        # factor de volumen de la música base durante el enfoque
FACTOR_DESCANSO_BAJO = 0.30      # y durante el descanso con «Bajar»
CAPA_VOL_INICIAL = 45


class Configuracion:
    def __init__(self, ruta=None):
        self.ruta = ruta or (_carpeta() / "estudio.json")
        self.datos = dict(DEFECTOS)
        self.datos["capas"] = {}
        guardado = _leer_json(self.ruta, {})
        if isinstance(guardado, dict):
            for k, v in guardado.items():
                if k in DEFECTOS:
                    self.datos[k] = v
        self.validar()

    def validar(self):
        d = self.datos
        if d["perfil"] not in PERFILES:
            d["perfil"] = PERFIL_INICIAL
        if d["pomodoro"] not in list(PRESETS_POMODORO) + ["personalizado"]:
            d["pomodoro"] = "25/5"
        if d["pomodoro"] in PRESETS_POMODORO:
            d["enfoque_min"], d["descanso_min"] = PRESETS_POMODORO[d["pomodoro"]]

        def entero(k, lo, hi):
            try:
                d[k] = max(lo, min(hi, int(d[k])))
            except (TypeError, ValueError):
                d[k] = DEFECTOS[k]
        entero("enfoque_min", 1, 240)
        entero("descanso_min", 0, 60)
        entero("rondas", 1, 12)
        entero("descanso_largo_min", 0, 60)
        entero("brillo", 0, 100)
        if d["al_descansar"] not in ("bajar", "pausar", "seguir"):
            d["al_descansar"] = "bajar"
        for k in ("atenuar", "campana", "mezcla_del_perfil", "calido", "despierto", "candado"):
            d[k] = bool(d[k])
        capas = {}
        for c, v in (d["capas"] if isinstance(d["capas"], dict) else {}).items():
            if c in CAPAS_ORDEN and isinstance(v, dict):
                try:
                    capas[c] = {"on": bool(v.get("on")), "vol": max(0, min(100, int(v.get("vol", 45))))}
                except (TypeError, ValueError):
                    pass
        d["capas"] = capas

    def __getitem__(self, k):
        return self.datos[k]

    def __setitem__(self, k, v):
        self.datos[k] = v

    def guardar(self):
        self.validar()
        _escribir_json(self.ruta, self.datos)


# ---------------------------------------------------------------------- mantener despierto

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


class MantenerDespierto:
    """Evita que Windows apague la pantalla o duerma mientras se estudia. La llamada
    al sistema es inyectable para probarlo."""

    def __init__(self, llamada=None):
        if llamada is None:
            llamada = self._windows
        self._llamada = llamada
        self.activo = False

    @staticmethod
    def _windows(banderas):
        import sys
        if sys.platform != "win32":
            return 0
        import ctypes
        return ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(banderas))

    def poner(self, si):
        si = bool(si)
        if si == self.activo:
            return
        try:
            if si:
                self._llamada(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
            else:
                self._llamada(ES_CONTINUOUS)
        except Exception:  # noqa: BLE001 - no es vital
            return
        self.activo = si


# ---------------------------------------------------------------------- controlador

class ControladorEstudio(QObject):
    """El modo estudio en marcha: une el temporizador con la música base y los sonidos."""

    cambio = Signal()                  # algo cambió (la pantalla se repinta)
    tic = Signal()                     # cada segundo mientras corre un bloque
    bloque_terminado = Signal(dict)    # el evento de `Temporizador.revisar`
    aviso = Signal(str)                # texto calmado para mostrar en pantalla
    pasos_fundido = 24

    def __init__(self, ctx, carpeta=None, reloj=time.time, mezclador=None, buscar=None,
                 despierto=None, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.reloj = reloj
        carpeta = carpeta or _carpeta()
        self.cfg = Configuracion(carpeta / "estudio.json")
        self.est = Estadisticas(carpeta / "estudio_historial.json", reloj)
        self.notas = Notas(carpeta / "estudio_notas.json", reloj)
        self.temporizador = Temporizador(reloj)
        if mezclador is None:
            from .sonidos_ambiente import Mezclador
            mezclador = Mezclador(getattr(ctx, "ajustes", None), padre=self)
        self.mezclador = mezclador
        self.mezclador.cargar_estado(self.cfg["capas"])
        self.mezclador.cambio.connect(self._capas_cambiaron)
        self._buscar = buscar
        self.despierto = MantenerDespierto(despierto)
        self.activo = False            # el modo estudio está en marcha
        self.vista_abierta = False     # la vista «Cero distracciones» está a la vista
        self.cargando_cola = False
        self.tiene_musica = False
        self._guardado = {}            # ajustes del reproductor antes de entrar al modo
        self._contado = 0.0            # segundos de enfoque ya sumados a las estadísticas
        self._pausamos_musica = False
        self._factor = 1.0
        self._pasos = []
        self._fundido = QTimer(self)
        self._fundido.setInterval(60)
        self._fundido.timeout.connect(self._paso_fundido)
        self._reloj = QTimer(self)
        self._reloj.setInterval(500)
        self._reloj.timeout.connect(self.revisar)
        self.aplicar_configuracion()

    # ---- ayudas
    @property
    def r(self):
        return getattr(self.ctx, "reproductor", None)

    def hay_bloque(self):
        """Hay un bloque de enfoque o de descanso en curso (aunque esté en pausa)."""
        return self.temporizador.activo()

    def fase(self):
        return self.temporizador.fase

    def guardar(self):
        self.cfg["capas"] = self.mezclador.exportar_estado()
        self.cfg.guardar()

    def _capas_cambiaron(self):
        self.cfg["capas"] = self.mezclador.exportar_estado()
        self.cfg.guardar()
        self.cambio.emit()

    # ---- configuración
    def aplicar_configuracion(self):
        c = self.cfg
        self.temporizador.configurar(c["enfoque_min"], c["descanso_min"], c["rondas"],
                                     c["descanso_largo_min"])

    def poner(self, **cambios):
        for k, v in cambios.items():
            if k in DEFECTOS:
                self.cfg[k] = v
        if "pomodoro" in cambios and cambios["pomodoro"] != "personalizado":
            self.cfg.validar()
        elif "enfoque_min" in cambios or "descanso_min" in cambios:
            self.cfg["pomodoro"] = "personalizado"
        self.cfg.guardar()
        if not self.hay_bloque():
            self.aplicar_configuracion()
        self._mantener_despierto()
        self.cambio.emit()

    def elegir_perfil(self, clave):
        if clave not in PERFILES:
            return
        self.cfg["perfil"] = clave
        if self.cfg["mezcla_del_perfil"]:
            self.aplicar_mezcla_del_perfil()
        self.cfg.guardar()
        self.cambio.emit()

    def aplicar_mezcla_del_perfil(self, clave=None):
        sugerida = PERFILES[clave or self.cfg["perfil"]]["mezcla"]
        self.mezclador.aplicar_mezcla({c: sugerida.get(c, 0) for c in CAPAS_ORDEN})

    # ---- entrar y salir del modo
    def activar(self):
        """Entra al modo: la cola sale solo del perfil (sin radio de relleno), con fundido
        suave entre canciones y sin mezcla DJ."""
        if self.activo:
            return
        self.activo = True
        r, aj = self.r, getattr(self.ctx, "ajustes", None)
        if aj is not None:
            self._guardado = {k: aj[k] for k in ("crossfade", "mezcla_dj", "autoplay",
                                                 "repetir", "aleatorio")}
            aj["crossfade"] = 5
            aj["mezcla_dj"] = False
            aj["autoplay"] = False
            aj["repetir"] = "todo"
            aj["aleatorio"] = False
        if r is not None:
            self._guardado["_r_repetir"] = getattr(r, "repetir", "no")
            self._guardado["_r_aleatorio"] = getattr(r, "aleatorio", False)
            r.repetir = "todo"
            r.aleatorio = False
        self.cambio.emit()

    def desactivar(self):
        """Sale del modo: los ajustes del reproductor vuelven a como estaban y se apagan los
        sonidos ambientales. La música que suena sigue sonando."""
        if not self.activo:
            return
        self._cerrar_sesion(guardar_sesion=True)
        self.activo = False
        self.vista_abierta = False
        r, aj = self.r, getattr(self.ctx, "ajustes", None)
        g, self._guardado = self._guardado, {}
        if aj is not None:
            for k in ("crossfade", "mezcla_dj", "autoplay", "repetir", "aleatorio"):
                if k in g:
                    aj[k] = g[k]
        if r is not None:
            if "_r_repetir" in g:
                r.repetir = g["_r_repetir"]
            if "_r_aleatorio" in g:
                r.aleatorio = g["_r_aleatorio"]
        self._poner_volumen_base(1.0, suave=False)
        self.mezclador.apagar_todo(guardar=False)
        self._mantener_despierto()
        self.cambio.emit()

    def salir_del_modo(self):
        """Al irse de la pantalla del modo estudio sin un bloque en curso."""
        if self.activo and not self.hay_bloque() and not self.vista_abierta:
            self.desactivar()

    # ---- música del perfil
    def reproducir_perfil(self, clave=None):
        """Busca la cola del perfil (en segundo plano) y la pone a sonar como cola propia."""
        self.activar()
        clave = clave or self.cfg["perfil"]
        if self.cargando_cola:
            return
        self.cargando_cola = True
        self.cambio.emit()
        from .hilos import en_segundo_plano
        en_segundo_plano(self._buscar_cola, clave, ok=lambda p, c=clave: self._cola_lista(c, p),
                         error=lambda e: self._cola_fallo(e), dueno=self)

    def _buscar_cola(self, clave):
        buscar = self._buscar
        if buscar is None:
            from . import catalogo
            buscar = lambda texto: catalogo.buscar(texto, "canciones", 20)  # noqa: E731
        return cola_del_perfil(clave, buscar)

    def _cola_lista(self, clave, pistas):
        self.cargando_cola = False
        r = self.r
        if not pistas or r is None:
            self.aviso.emit("No pudimos traer música ahora. Revisa tu conexión y vuelve a intentarlo.")
            self.cambio.emit()
            return
        ctx_cola = {"tipo": "estudio", "id": clave,
                    "titulo": "Modo estudio · " + PERFILES[clave]["nombre"]}
        self.tiene_musica = True
        r.reproducir_lista(pistas, 0, ctx_cola, aleatorio=False, modo="audio")
        self._aplicar_musica()
        self.cambio.emit()

    def _cola_fallo(self, _e):
        self.cargando_cola = False
        self.aviso.emit("No pudimos traer música ahora. Revisa tu conexión y vuelve a intentarlo.")
        self.cambio.emit()

    # ---- sesión
    def empezar(self, solo_musica=False):
        """Empieza a estudiar: temporizador (salvo «Solo música»), mezcla del perfil y cola."""
        self.activar()
        if self.cfg["mezcla_del_perfil"] and not self.mezclador.hay_algo_encendido():
            self.aplicar_mezcla_del_perfil()
        if not solo_musica:
            self.aplicar_configuracion()
            self.temporizador.iniciar()
            self._contado = 0.0
            self._reloj.start()
            self._mantener_despierto()
        self.reproducir_perfil()
        self.cambio.emit()

    def terminar(self):
        """El usuario termina su sesión: se guarda lo estudiado y todo vuelve a su sitio."""
        self._cerrar_sesion(guardar_sesion=True)
        self.desactivar()

    def _cerrar_sesion(self, guardar_sesion):
        if self.temporizador.fase == "inactivo":
            self._reloj.stop()
            return
        completa = self.temporizador.fase == "completo"      # ya se anotó al terminar
        total = self.temporizador.terminar()
        nuevo = total - self._contado
        if nuevo > 0:
            self.est.sumar(nuevo)
        if guardar_sesion and not completa:
            self.est.anotar_sesion(total, self.cfg["perfil"], 0)
        self._contado = 0.0
        self._reloj.stop()
        self._restaurar_musica()
        self._mantener_despierto()
        self.cambio.emit()

    def pausar_o_reanudar(self):
        t = self.temporizador
        if not t.activo():
            return
        if t.en_pausa():
            t.reanudar()
        else:
            t.pausar()
        self.cambio.emit()

    def saltar_fase(self):
        for ev in self.temporizador.saltar():
            self._manejar(ev)

    # ---- el reloj
    def revisar(self):
        """Se llama cada medio segundo: mira la hora de fin y guarda lo estudiado."""
        t = self.temporizador
        for ev in t.revisar():
            self._manejar(ev)
        if t.activo() or t.fase == "completo":
            self._guardar_avance()
            self.tic.emit()

    def _guardar_avance(self, minimo=30.0):
        pendiente = self.temporizador.enfocado_total() - self._contado
        if pendiente >= minimo:
            self.est.sumar(pendiente)
            self._contado += pendiente

    def _manejar(self, ev):
        """Un bloque terminó: se cuenta, suena la campana, la música se acomoda y se
        avisa con un texto tranquilo."""
        t = self.temporizador
        # lo estudiado hasta el final de este bloque
        pendiente = t.enfocado_total() - self._contado
        if pendiente > 0:
            self.est.sumar(pendiente)
            self._contado += pendiente
        if ev["tipo"] == "fin_enfoque":
            if ev.get("completa"):
                total = t.enfocado_total()
                self.est.anotar_sesion(total, self.cfg["perfil"], ev.get("rondas", 0))
                self._reloj.stop()
                self._restaurar_musica()
                self._mantener_despierto()
                self.aviso.emit(f"Terminaste tus {ev['rondas']} "
                                f"{'ronda' if ev['rondas'] == 1 else 'rondas'}. Bien hecho, "
                                "te mereces un buen descanso.")
            elif ev.get("siguiente") == "enfoque":
                self._aplicar_musica()
                self.aviso.emit(f"Ronda {ev['ronda']} lista. Seguimos con la siguiente.")
            else:
                self._musica_de_descanso()
                largo = ev["siguiente"] == "descanso_largo"
                minutos = self.cfg["descanso_largo_min"] if largo else self.cfg["descanso_min"]
                self.aviso.emit(("Buen trabajo. Tómate un descanso largo de " if largo
                                 else "Buen trabajo. Descansa unos ") + f"{minutos} min.")
            self._campana(0.9)
        elif ev["tipo"] == "fin_descanso":
            self._aplicar_musica()
            self.aviso.emit(f"Descanso terminado. Ronda {ev['ronda']} de {ev['rondas']}: "
                            "cuando quieras.")
            self._campana(0.6)
        self.bloque_terminado.emit(ev)
        self.cambio.emit()

    def _campana(self, fuerza):
        if self.cfg["campana"]:
            try:
                self.mezclador.tocar_campana(fuerza)
            except Exception:  # noqa: BLE001 - la campana no es vital
                pass

    # ---- volumen de la música base
    def factor_enfoque(self):
        return ATENUACION_ENFOQUE if self.cfg["atenuar"] else 1.0

    def _aplicar_musica(self):
        """Durante el enfoque: la música base, atenuada si así se eligió; y si se había
        pausado en el descanso, vuelve a sonar."""
        self._reanudar_si_pausamos()
        self._poner_volumen_base(self.factor_enfoque())

    def _musica_de_descanso(self):
        accion = self.cfg["al_descansar"]
        if accion == "pausar":
            r = self.r
            if r is not None and r.estado == "sonando":
                r.pausar()
                self._pausamos_musica = True
        elif accion == "bajar":
            self._poner_volumen_base(min(self.factor_enfoque(), FACTOR_DESCANSO_BAJO))
        else:
            self._poner_volumen_base(self.factor_enfoque())

    def _restaurar_musica(self):
        self._reanudar_si_pausamos()
        self._poner_volumen_base(1.0)

    def _reanudar_si_pausamos(self):
        if self._pausamos_musica:
            self._pausamos_musica = False
            r = self.r
            if r is not None and r.estado == "pausa":
                r.reanudar()

    def _poner_volumen_base(self, objetivo, suave=True):
        objetivo = max(0.0, min(1.0, float(objetivo)))
        if not suave or abs(objetivo - self._factor) < 0.005:
            self._fundido.stop()
            self._pasos = []
            self._fijar_factor(objetivo)
            return
        n = self.pasos_fundido
        self._pasos = [self._factor + (objetivo - self._factor) * (i + 1) / n for i in range(n)]
        self._fundido.start()

    def _paso_fundido(self):
        if not self._pasos:
            self._fundido.stop()
            return
        self._fijar_factor(self._pasos.pop(0))
        if not self._pasos:
            self._fundido.stop()

    def _fijar_factor(self, f):
        self._factor = f
        r = self.r
        poner = getattr(r, "_poner_factor_suave", None)
        if poner is not None:
            try:
                poner(f)
            except Exception:  # noqa: BLE001
                pass

    def _mantener_despierto(self):
        quiere = bool(self.cfg["despierto"]) and (self.hay_bloque() or self.vista_abierta)
        self.despierto.poner(quiere)

    def vista_cambio(self, abierta):
        self.vista_abierta = bool(abierta)
        self._mantener_despierto()
        self.cambio.emit()

    # ---- cierre
    def cerrar(self):
        """Al cerrar Caudal: se guarda lo estudiado y se apagan los sonidos."""
        try:
            self._cerrar_sesion(guardar_sesion=True)
            if self.activo:
                self.desactivar()
        finally:
            self.despierto.poner(False)
            self.mezclador.cerrar()

    # ---- textos para las pantallas
    def titulo_fase(self):
        t = self.temporizador
        if t.fase == "inactivo":
            return ""
        if t.fase == "completo":
            return "Sesión completa"
        base = NOMBRE_FASE[t.fase]
        if t.fase == "enfoque" or t.rondas > 1:
            base += f" · ronda {t.ronda} de {t.rondas}"
        return base + (" · en pausa" if t.en_pausa() else "")



def de(ctx):
    """El controlador del modo estudio de este contexto (se crea la primera vez)."""
    c = getattr(ctx, "estudio", None)
    if c is None:
        c = ControladorEstudio(ctx)
        try:
            ctx.estudio = c
        except AttributeError:
            pass
    return c
