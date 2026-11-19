# -*- coding: utf-8 -*-
"""Modo gamer (Windows): atajos globales, ahorro al jugar, presets de sonido, bajar la musica
al hablar, listas por situacion, nivel con XP y misiones, y «Ahora suena» para OBS.

Todo lo que no es Qt (analizar atajos, juzgar si hay un juego a pantalla completa, la curva de
nivel, las misiones del dia, el texto para OBS) son funciones puras y se prueban sin ventana.
El `GestorGamer` las junta; la ventana principal lo crea una vez (ctx.gamer) y lo cierra al salir.

Los ajustes y el progreso viven en archivos propios dentro de la carpeta del perfil
(modo_gamer.json y modo_gamer_progreso.json): nada sale de esta PC.
"""

import html
import json
import math
import os
import random
import sys
import time
from datetime import date, datetime, timedelta

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, Signal

from . import catalogo
from .config import carpeta_perfil
from .hilos import en_segundo_plano

# ===================================================================== atajos

MOD_ALT, MOD_CTRL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
WM_HOTKEY = 0x0312

ACCIONES = [
    ("play", "Reproducir / pausar"),
    ("siguiente", "Siguiente canción"),
    ("anterior", "Canción anterior"),
    ("vol_mas", "Subir volumen"),
    ("vol_menos", "Bajar volumen"),
    ("mini", "Mostrar / ocultar el mini reproductor"),
    ("clics", "Dejar pasar los clics (quitar y poner)"),
    ("hablar", "Hablar: bajar la música mientras se mantiene"),
]
NOMBRES_ACCION = dict(ACCIONES)

# Ctrl+Alt+... : casi nunca los usa un juego ni otra app
ATAJOS_DEFECTO = {
    "play": "Ctrl+Alt+Space",
    "siguiente": "Ctrl+Alt+Right",
    "anterior": "Ctrl+Alt+Left",
    "vol_mas": "Ctrl+Alt+Up",
    "vol_menos": "Ctrl+Alt+Down",
    "mini": "Ctrl+Alt+M",
    "clics": "Ctrl+Alt+K",
    "hablar": "Ctrl+Alt+V",
}

_VK_NOMBRES = {
    "SPACE": 0x20, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "PGUP": 0x21, "PGDOWN": 0x22, "END": 0x23, "HOME": 0x24, "INS": 0x2D, "DEL": 0x2E,
    "RETURN": 0x0D, "ENTER": 0x0D, "TAB": 0x09, "ESC": 0x1B, "BACKSPACE": 0x08,
    ",": 0xBC, ".": 0xBE, "-": 0xBD, "=": 0xBB, ";": 0xBA, "/": 0xBF, "`": 0xC0,
    "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
# nombre canonico (como lo escribe Qt) de cada tecla especial
_CANON = {0x20: "Space", 0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down", 0x21: "PgUp",
          0x22: "PgDown", 0x23: "End", 0x24: "Home", 0x2D: "Ins", 0x2E: "Del", 0x0D: "Return",
          0x09: "Tab", 0x1B: "Esc", 0x08: "Backspace"}
_MODS = {"CTRL": MOD_CTRL, "CONTROL": MOD_CTRL, "ALT": MOD_ALT, "SHIFT": MOD_SHIFT,
         "META": MOD_WIN, "WIN": MOD_WIN}


def parsear_atajo(texto):
    """«Ctrl+Alt+Space» -> (modificadores, codigo de tecla virtual). None si no sirve.
    Un atajo global necesita una tecla y al menos Ctrl, Alt o Win (con Mayus solo molestaria
    al escribir)."""
    if not texto or not isinstance(texto, str):
        return None
    partes = [p.strip() for p in texto.replace(" ", "").split("+")]
    if len(partes) < 2 or not partes[-1]:
        return None
    mods = 0
    for m in partes[:-1]:
        v = _MODS.get(m.upper())
        if v is None:
            return None
        mods |= v
    if not mods & (MOD_CTRL | MOD_ALT | MOD_WIN):
        return None
    t = partes[-1].upper()
    if t in _VK_NOMBRES:
        vk = _VK_NOMBRES[t]
    elif len(t) == 1 and ("A" <= t <= "Z" or "0" <= t <= "9"):
        vk = ord(t)
    elif t.startswith("F") and t[1:].isdigit() and 1 <= int(t[1:]) <= 24:
        vk = 0x70 + int(t[1:]) - 1
    else:
        return None
    return mods, vk


def formato_atajo(mods, vk):
    """El mismo atajo escrito de forma canonica (Ctrl+Alt+Shift+Win+tecla)."""
    partes = []
    if mods & MOD_CTRL:
        partes.append("Ctrl")
    if mods & MOD_ALT:
        partes.append("Alt")
    if mods & MOD_SHIFT:
        partes.append("Shift")
    if mods & MOD_WIN:
        partes.append("Win")
    if vk in _CANON:
        tecla = _CANON[vk]
    elif 0x70 <= vk <= 0x87:
        tecla = f"F{vk - 0x70 + 1}"
    elif 0x30 <= vk <= 0x5A:
        tecla = chr(vk)
    else:
        tecla = next((n for n, c in _VK_NOMBRES.items() if c == vk and len(n) == 1), f"0x{vk:02X}")
    return "+".join(partes + [tecla])


def normalizar_atajo(texto):
    p = parsear_atajo(texto)
    return formato_atajo(*p) if p else None


def atajos_repetidos(atajos):
    """Las acciones cuyo atajo ya usa otra: {accion: otra_accion}."""
    vistos, dup = {}, {}
    for accion, t in atajos.items():
        n = normalizar_atajo(t)
        if not n:
            continue
        if n in vistos:
            dup[accion] = vistos[n]
        else:
            vistos[n] = accion
    return dup


# ===================================================================== ajustes propios

PRESETS_SONIDO = {
    "fps": {"nombre": "FPS", "ayuda": "Pasos y voces claros: menos graves, más presencia",
            "bandas": [-6, -4, -2, 0, 0, 2, 4, 5, 3, 1], "envolvente": False},
    "rpg": {"nombre": "RPG épico", "ayuda": "Graves con cuerpo y agudos brillantes, sonido amplio",
            "bandas": [5, 4, 2, 0, -1, 0, 2, 3, 4, 4], "envolvente": True},
    "carreras": {"nombre": "Carreras", "ayuda": "Motor y energía: graves firmes y ritmo adelante",
                 "bandas": [6, 5, 3, 1, 0, 0, 1, 2, 3, 2], "envolvente": False},
    "chill": {"nombre": "Chill", "ayuda": "Cálido y suave, sin agudos que cansen",
              "bandas": [1, 1, 0, 0, 0, -1, -1, -2, -3, -3], "envolvente": False},
}

SITUACIONES = {
    "lobby": {"nombre": "Lobby", "ayuda": "Mientras esperas la partida",
              "consultas": ["gaming lobby chill music", "chill electronic gaming mix"]},
    "concentracion": {"nombre": "Concentración", "ayuda": "Para estar en la zona",
                      "consultas": ["lofi focus gaming music", "ambient electronic focus"]},
    "clutch": {"nombre": "Clutch", "ayuda": "Adrenalina para el último round",
               "consultas": ["epic intense gaming music", "drum and bass gaming mix"]},
    "victoria": {"nombre": "Victoria", "ayuda": "Para celebrar",
                 "consultas": ["victory celebration hype songs", "epic victory music"]},
    "derrota": {"nombre": "Derrota", "ayuda": "Para respirar y volver a intentarlo",
                "consultas": ["calm comforting songs after a loss", "chill relaxing songs"]},
}

IGNORAR_DEFECTO = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
                   "vivaldi.exe", "explorer.exe", "applicationframehost.exe", "powerpnt.exe",
                   "vlc.exe", "mpv.exe"]

DEFECTOS_GAMER = {
    "activo": False,             # atajos globales + detector de juegos + «Ahora suena»
    "atajos": dict(ATAJOS_DEFECTO),
    "mini_visible": False,
    "mini_opacidad": 88,         # 35..100
    "mini_clics": False,         # dejar pasar los clics
    "mini_pos": None,            # [x, y]
    "neon": True,
    "ahorro": True,
    "ignorar": list(IGNORAR_DEFECTO),
    "hablar_nivel": 25,          # % del volumen mientras se habla
    "obs": False,
    "obs_carpeta": "",
    "obs_html": False,
    "sonido_gamer": "",          # clave del preset puesto
    "sonido_previo": None,       # el sonido de antes, para devolverlo
}


def _entero(v, defecto, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return defecto


class ConfigGamer:
    def __init__(self, archivo=None):
        self.archivo = archivo or (carpeta_perfil() / "modo_gamer.json")
        self.datos = json.loads(json.dumps(DEFECTOS_GAMER))
        self.cargar()

    def cargar(self):
        try:
            if os.path.exists(self.archivo):
                with open(self.archivo, encoding="utf-8") as f:
                    g = json.load(f)
                if isinstance(g, dict):
                    self._mezclar(g)
        except (OSError, ValueError):
            pass

    def _mezclar(self, g):
        d = self.datos
        for k in ("activo", "mini_visible", "mini_clics", "neon", "ahorro", "obs", "obs_html"):
            if isinstance(g.get(k), bool):
                d[k] = g[k]
        d["mini_opacidad"] = _entero(g.get("mini_opacidad"), d["mini_opacidad"], 35, 100)
        d["hablar_nivel"] = _entero(g.get("hablar_nivel"), d["hablar_nivel"], 5, 80)
        pos = g.get("mini_pos")
        if isinstance(pos, (list, tuple)) and len(pos) == 2 and all(isinstance(n, (int, float)) for n in pos):
            d["mini_pos"] = [int(pos[0]), int(pos[1])]
        if isinstance(g.get("obs_carpeta"), str):
            d["obs_carpeta"] = g["obs_carpeta"]
        if isinstance(g.get("atajos"), dict):
            for a in ATAJOS_DEFECTO:
                n = normalizar_atajo(g["atajos"].get(a))
                if n:
                    d["atajos"][a] = n
        if isinstance(g.get("ignorar"), list):
            d["ignorar"] = [str(x).lower() for x in g["ignorar"] if str(x).strip()]
        if g.get("sonido_gamer") in PRESETS_SONIDO or g.get("sonido_gamer") == "":
            d["sonido_gamer"] = g.get("sonido_gamer", "")
        if isinstance(g.get("sonido_previo"), dict):
            d["sonido_previo"] = g["sonido_previo"]

    def guardar(self):
        try:
            tmp = f"{self.archivo}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.datos, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.archivo)
        except OSError:
            pass

    def __getitem__(self, k):
        return self.datos[k]

    def __setitem__(self, k, v):
        self.datos[k] = v


# ===================================================================== nivel, XP y misiones

XP_POR_MINUTO = 1
MINUTOS_DIA_ACTIVO = 10          # con tanto escuchado el dia cuenta para la racha

RANGOS = ["Novato", "Aprendiz", "Jugador", "Veterano", "Élite", "Maestro", "Leyenda"]


def xp_para_nivel(n):
    """XP total que hace falta para llegar al nivel n (el 1 es el de partida)."""
    n = max(1, int(n))
    return 25 * (n - 1) * n


def nivel_de_xp(xp):
    xp = max(0, int(xp))
    n = int((1 + math.sqrt(1 + 4 * xp / 25.0)) / 2)
    while xp_para_nivel(n + 1) <= xp:
        n += 1
    while n > 1 and xp_para_nivel(n) > xp:
        n -= 1
    return n


def info_nivel(xp):
    """(nivel, xp dentro del nivel, xp que dura el nivel, rango)."""
    n = nivel_de_xp(xp)
    base = xp_para_nivel(n)
    return n, int(xp) - base, xp_para_nivel(n + 1) - base, RANGOS[min(len(RANGOS) - 1, (n - 1) // 5)]


_PLANTILLAS = {
    "minutos": ("Escucha {meta} minutos", "minutos"),
    "pistas": ("Pasa por {meta} canciones", "pistas"),
    "listas": ("Pon una lista por situación", "listas"),
    "sonidos": ("Prueba un preset de sonido", "sonidos"),
    "mini": ("Abre el mini reproductor", "mini"),
    "hablar": ("Usa «bajar la música al hablar»", "hablar"),
}
_METAS = {"minutos": (15, 20, 30, 45), "pistas": (5, 8, 12), "listas": (1,), "sonidos": (1,),
          "mini": (1,), "hablar": (1,)}
_RECOMPENSA = {"minutos": 30, "pistas": 20, "listas": 15, "sonidos": 15, "mini": 10, "hablar": 10}


def misiones_del_dia(fecha):
    """3 misiones que dependen solo de la fecha: la misma fecha siempre da las mismas.
    Siempre una de minutos y dos de otro tipo."""
    rng = random.Random(f"caudal-gamer-{fecha.isoformat()}")
    meta_min = rng.choice(_METAS["minutos"])
    otras = rng.sample([t for t in _PLANTILLAS if t != "minutos"], 2)
    salida = []
    for tipo in ["minutos"] + otras:
        meta = meta_min if tipo == "minutos" else rng.choice(_METAS[tipo])
        salida.append({"id": f"{fecha.isoformat()}:{tipo}", "tipo": tipo, "meta": meta,
                       "texto": _PLANTILLAS[tipo][0].format(meta=meta), "xp": _RECOMPENSA[tipo]})
    return salida


class Progreso:
    """XP, racha y avance de las misiones del dia. Se guarda en este equipo."""

    def __init__(self, archivo=None, hoy=None):
        self.archivo = archivo or (carpeta_perfil() / "modo_gamer_progreso.json")
        self._hoy = hoy or date.today
        self.d = {"xp": 0, "racha": 0, "mejor_racha": 0, "ultimo_activo": "", "dia": "",
                  "cont": {}, "cobradas": [], "resto": 0.0, "minutos_total": 0}
        self._cargar()
        self._girar_dia()

    def _cargar(self):
        try:
            with open(self.archivo, encoding="utf-8") as f:
                g = json.load(f)
            if isinstance(g, dict):
                for k in self.d:
                    if k in g and isinstance(g[k], type(self.d[k])):
                        self.d[k] = g[k]
        except (OSError, ValueError):
            pass
        self.d["xp"] = max(0, int(self.d["xp"]))

    def guardar(self):
        try:
            tmp = f"{self.archivo}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
            os.replace(tmp, self.archivo)
        except OSError:
            pass

    def _girar_dia(self):
        hoy = self._hoy().isoformat()
        if self.d["dia"] != hoy:
            self.d["dia"] = hoy
            self.d["cont"] = {}
            self.d["cobradas"] = []

    # --- lectura
    @property
    def xp(self):
        return self.d["xp"]

    def racha(self):
        """Dias seguidos activos; se corta si ayer no se escucho lo suficiente."""
        ult = self.d["ultimo_activo"]
        if not ult:
            return 0
        hoy = self._hoy()
        if ult in (hoy.isoformat(), (hoy - timedelta(days=1)).isoformat()):
            return self.d["racha"]
        return 0

    def contador(self, nombre):
        self._girar_dia()
        return int(self.d["cont"].get(nombre, 0))

    def misiones(self):
        self._girar_dia()
        res = []
        for m in misiones_del_dia(self._hoy()):
            actual = self.contador(m["tipo"])
            res.append({**m, "actual": min(actual, m["meta"]), "hecha": m["id"] in self.d["cobradas"]})
        return res

    # --- escritura
    def _sumar_xp(self, n):
        self.d["xp"] += int(n)

    def sumar_segundos(self, seg):
        """Escuchar da 1 XP por minuto completo. Devuelve los XP ganados ahora."""
        self._girar_dia()
        total = self.d["resto"] + max(0.0, float(seg))
        minutos = int(total // 60)
        self.d["resto"] = total - minutos * 60
        if minutos:
            self.d["cont"]["minutos"] = self.contador("minutos") + minutos
            self.d["minutos_total"] += minutos
            self._sumar_xp(minutos * XP_POR_MINUTO)
            self._revisar_racha()
        return minutos * XP_POR_MINUTO + self._cobrar()

    def evento(self, nombre, n=1):
        """Cuenta algo que hizo la persona (pistas, listas, sonidos, mini, hablar). Devuelve XP de misiones."""
        self._girar_dia()
        self.d["cont"][nombre] = self.contador(nombre) + n
        return self._cobrar()

    def _revisar_racha(self):
        if self.contador("minutos") < MINUTOS_DIA_ACTIVO:
            return
        hoy = self._hoy()
        if self.d["ultimo_activo"] == hoy.isoformat():
            return
        ayer = (hoy - timedelta(days=1)).isoformat()
        self.d["racha"] = self.d["racha"] + 1 if self.d["ultimo_activo"] == ayer else 1
        self.d["ultimo_activo"] = hoy.isoformat()
        self.d["mejor_racha"] = max(self.d["mejor_racha"], self.d["racha"])

    def _cobrar(self):
        ganado = 0
        for m in self.misiones():
            if m["actual"] >= m["meta"] and not m["hecha"]:
                self.d["cobradas"].append(m["id"])
                self._sumar_xp(m["xp"])
                ganado += m["xp"]
        return ganado


# ===================================================================== «Ahora suena» (OBS)

def texto_ahora_suena(pista):
    if not pista:
        return ""
    titulo = (pista.get("titulo") or "").strip()
    artista = (pista.get("artista") or "").strip()
    return f"{titulo} — {artista}" if titulo and artista else titulo or artista


def html_ahora_suena(texto):
    cuerpo = html.escape(texto) if texto else "&nbsp;"
    return ("<!doctype html><html><head><meta charset=\"utf-8\">"
            "<meta http-equiv=\"refresh\" content=\"2\"><title>Ahora suena</title><style>"
            "html,body{margin:0;background:transparent}"
            "p{font:700 28px 'Segoe UI',Arial,sans-serif;color:#fff;margin:8px 14px;"
            "text-shadow:0 0 6px #000,0 0 12px #000}</style></head><body>"
            f"<p>{cuerpo}</p></body></html>")


def _escribir_atomico(ruta, contenido):
    tmp = f"{ruta}.tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(contenido)
    os.replace(tmp, ruta)


def escribir_ahora_suena(carpeta, pista, con_html=False):
    """Escribe ahora_suena.txt (y .html si se pide). Devuelve True si pudo."""
    try:
        os.makedirs(carpeta, exist_ok=True)
        texto = texto_ahora_suena(pista)
        _escribir_atomico(os.path.join(carpeta, "ahora_suena.txt"), texto)
        if con_html:
            _escribir_atomico(os.path.join(carpeta, "ahora_suena.html"), html_ahora_suena(texto))
        return True
    except OSError:
        return False


AVISO_DERECHOS = ("La música de YouTube no se puede usar en directos ni en videos grabados "
                  "(VOD): tiene derechos de autor y tu canal puede recibir un strike o silenciarse. "
                  "Usa «Ahora suena» solo con música propia, libre o con licencia para stream.")


# ===================================================================== Windows (ctypes)

_API = {}


def _win():
    """Las funciones de Windows con sus tipos bien puestos (64 bits). None fuera de Windows."""
    if sys.platform != "win32":
        return None
    if _API:
        return _API
    import ctypes
    from ctypes import wintypes as w

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", w.DWORD), ("rcMonitor", w.RECT), ("rcWork", w.RECT),
                    ("dwFlags", w.DWORD)]

    u = ctypes.WinDLL("user32", use_last_error=True)
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    u.GetForegroundWindow.restype = w.HWND
    u.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
    u.MonitorFromWindow.argtypes = [w.HWND, w.DWORD]
    u.MonitorFromWindow.restype = w.HANDLE
    u.GetMonitorInfoW.argtypes = [w.HANDLE, ctypes.POINTER(MONITORINFO)]
    u.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    u.GetWindowLongW.argtypes = [w.HWND, ctypes.c_int]
    u.GetWindowLongW.restype = ctypes.c_long
    u.IsWindowVisible.argtypes = [w.HWND]
    u.IsIconic.argtypes = [w.HWND]
    u.RegisterHotKey.argtypes = [w.HWND, ctypes.c_int, w.UINT, w.UINT]
    u.UnregisterHotKey.argtypes = [w.HWND, ctypes.c_int]
    u.GetAsyncKeyState.argtypes = [ctypes.c_int]
    u.GetAsyncKeyState.restype = ctypes.c_short
    ptr = "GetWindowLongPtrW" if ctypes.sizeof(ctypes.c_void_p) == 8 else "GetWindowLongW"
    getp = getattr(u, ptr)
    getp.argtypes = [w.HWND, ctypes.c_int]
    getp.restype = ctypes.c_ssize_t
    setp = getattr(u, ptr.replace("Get", "Set"))
    setp.argtypes = [w.HWND, ctypes.c_int, ctypes.c_ssize_t]
    setp.restype = ctypes.c_ssize_t
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
    k.CloseHandle.argtypes = [w.HANDLE]
    k.GetCurrentProcess.restype = w.HANDLE
    k.SetPriorityClass.argtypes = [w.HANDLE, w.DWORD]
    k.GetPriorityClass.argtypes = [w.HANDLE]
    k.GetPriorityClass.restype = w.DWORD
    _API.update(u=u, k=k, ct=ctypes, w=w, MONITORINFO=MONITORINFO, getp=getp, setp=setp)
    return _API


GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_CAPTION, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_NOACTIVATE = 0x00C00000, 0x80000, 0x20, 0x08000000
CLASES_ESCRITORIO = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                     "XamlExplorerHostIslandWindow", "Windows.UI.Core.CoreWindow"}


def _exe_de_pid(pid):
    a = _win()
    if not a:
        return ""
    h = a["k"].OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = a["ct"].create_unicode_buffer(520)
        n = a["w"].DWORD(520)
        if a["k"].QueryFullProcessImageNameW(h, 0, buf, a["ct"].byref(n)):
            return os.path.basename(buf.value).lower()
    finally:
        a["k"].CloseHandle(h)
    return ""


def ventana_en_primer_plano():
    """Lo que hace falta saber de la ventana activa (o None). Unas pocas llamadas, baratas."""
    a = _win()
    if not a:
        return None
    u, ct, w = a["u"], a["ct"], a["w"]
    hwnd = u.GetForegroundWindow()
    if not hwnd:
        return None
    rect = w.RECT()
    if not u.GetWindowRect(hwnd, ct.byref(rect)):
        return None
    mon = u.MonitorFromWindow(hwnd, 2)               # MONITOR_DEFAULTTONEAREST
    mi = a["MONITORINFO"]()
    mi.cbSize = ct.sizeof(mi)
    if not mon or not u.GetMonitorInfoW(mon, ct.byref(mi)):
        return None
    clase = ct.create_unicode_buffer(128)
    u.GetClassNameW(hwnd, clase, 128)
    pid = w.DWORD(0)
    u.GetWindowThreadProcessId(hwnd, ct.byref(pid))
    m = mi.rcMonitor
    return {"rect": (rect.left, rect.top, rect.right, rect.bottom),
            "monitor": (m.left, m.top, m.right, m.bottom),
            "clase": clase.value, "pid": int(pid.value), "exe": _exe_de_pid(int(pid.value)),
            "estilo": u.GetWindowLongW(hwnd, GWL_STYLE) & 0xFFFFFFFF,
            "visible": bool(u.IsWindowVisible(hwnd)), "minimizada": bool(u.IsIconic(hwnd))}


def es_juego_pantalla_completa(info, mi_pid, ignorar=()):
    """¿La ventana activa es una app a pantalla completa (juego, sin bordes ni barra de titulo)?
    Una ventana maximizada normal tiene barra de titulo, asi que no cuenta."""
    if not info or not info.get("visible") or info.get("minimizada"):
        return False
    if info.get("pid") == mi_pid or info.get("clase") in CLASES_ESCRITORIO:
        return False
    if (info.get("exe") or "").lower() in {str(x).lower() for x in ignorar}:
        return False
    l, t, r, b = info["rect"]
    ml, mt, mr, mb = info["monitor"]
    if not (l <= ml and t <= mt and r >= mr and b >= mb):
        return False
    if info.get("estilo", 0) & WS_CAPTION == WS_CAPTION:
        return False
    return True


def fijar_clics_pasan(hwnd, si):
    """WS_EX_TRANSPARENT: el raton atraviesa la ventana (y WS_EX_NOACTIVATE: no roba el foco)."""
    a = _win()
    if not a or not hwnd:
        return False
    try:
        h = a["w"].HWND(hwnd)
        est = a["getp"](h, GWL_EXSTYLE)
        nuevo = est | WS_EX_LAYERED | WS_EX_NOACTIVATE
        nuevo = nuevo | WS_EX_TRANSPARENT if si else nuevo & ~WS_EX_TRANSPARENT
        if nuevo != est:
            a["setp"](h, GWL_EXSTYLE, nuevo)
        return bool(a["getp"](h, GWL_EXSTYLE) & WS_EX_TRANSPARENT) == bool(si)
    except Exception:  # noqa: BLE001 - una ventana que no es de Windows (offscreen)
        return False


def tecla_pulsada(vk):
    a = _win()
    return bool(a and a["u"].GetAsyncKeyState(int(vk)) & 0x8000)


def prioridad_proceso():
    a = _win()
    return int(a["k"].GetPriorityClass(a["k"].GetCurrentProcess())) if a else 0


def poner_prioridad_proceso(clase):
    a = _win()
    return bool(a and a["k"].SetPriorityClass(a["k"].GetCurrentProcess(), int(clase)))


PRIORIDAD_BAJA, PRIORIDAD_NORMAL = 0x00004000, 0x00000020


class _FiltroHotkey(QAbstractNativeEventFilter):
    def __init__(self, alpulsar):
        super().__init__()
        self.alpulsar = alpulsar

    def nativeEventFilter(self, tipo, mensaje):
        if sys.platform != "win32" or tipo != b"windows_generic_MSG":
            return False, 0
        try:
            import ctypes.wintypes as w
            msg = w.MSG.from_address(int(mensaje))
            if msg.message == WM_HOTKEY and self.alpulsar(int(msg.wParam)):
                return True, 0
        except Exception:  # noqa: BLE001
            pass
        return False, 0


# ===================================================================== el gestor

ID_BASE = 0x6A01
PASO_RAMPA_MS = 30


class GestorGamer(QObject):
    cambio = Signal()                  # algo de los ajustes cambio: las pantallas se refrescan
    ahorro_cambio = Signal(bool, str)  # (ahorrando, nombre del juego)
    atajos_cambio = Signal()
    progreso_cambio = Signal()
    subio_nivel = Signal(int)

    def __init__(self, ctx, ventana=None, cfg=None, progreso=None):
        super().__init__(ventana)
        self.ctx = ctx
        self.v = ventana
        self.r = ctx.reproductor
        self.cfg = cfg or ConfigGamer()
        self.progreso = progreso or Progreso()
        self.fallidos = {}             # accion -> motivo, de los atajos que Windows no dejo registrar
        self._registrados = {}         # id -> accion
        self._filtro = None
        self._mini = None
        # ahorro
        self.ahorrando = False
        self.juego = ""
        self._negativos = 0
        self._timers_parados = []
        self._ocultos = []
        self._prioridad_previa = None
        self.sondeo = ventana_en_primer_plano      # se puede sustituir en pruebas
        self._t_sondeo = QTimer(self)
        self._t_sondeo.setInterval(3000)
        self._t_sondeo.timeout.connect(self._sondear)
        # bajar al hablar
        self._hablando = None          # (vk) mientras se mantiene
        self._rampa = QTimer(self)
        self._rampa.setInterval(PASO_RAMPA_MS)
        self._rampa.timeout.connect(self._paso_rampa)
        self._vol_base = None          # volumen antes de bajar
        self._vol_meta = None
        self._ajuste_vol0 = 0
        self._paso_ms = 300
        self._t_tecla = QTimer(self)
        self._t_tecla.setInterval(40)
        self._t_tecla.timeout.connect(self._vigilar_tecla)
        # XP
        self._t_xp = QTimer(self)
        self._t_xp.setInterval(5000)
        self._t_xp.timeout.connect(self._tic_xp)
        self._ultimo_tic = time.monotonic()
        self._nivel_mostrado = nivel_de_xp(self.progreso.xp)
        self._t_xp.start()
        # OBS
        if self.r is not None:
            self.r.pista_cambio.connect(self._al_pista)
            self.r.estado_cambio.connect(self._al_estado)
        from .ui.neon_gamer import reloj_neon
        reloj_neon().activar(self.cfg["neon"])
        if self.cfg["activo"]:
            self._encender()
        if self.cfg["mini_visible"]:
            QTimer.singleShot(0, lambda: self.mostrar_mini(True))

    # ------------------------------------------------------------ interruptor general

    @property
    def activo(self):
        return bool(self.cfg["activo"])

    def activar(self, si):
        si = bool(si)
        if si == self.activo:
            return
        self.cfg["activo"] = si
        self.cfg.guardar()
        self._encender() if si else self._apagar()
        self.cambio.emit()

    def _encender(self):
        self.registrar_atajos()
        self._reiniciar_sondeo()
        self._escribir_obs()

    def _apagar(self):
        self.soltar_atajos()
        self._t_sondeo.stop()
        self.salir_de_ahorro()

    # ------------------------------------------------------------ atajos globales

    def registrar_atajos(self):
        self.soltar_atajos()
        self.fallidos = {}
        a = _win()
        if not a:
            self.fallidos = {k: "Solo funciona en Windows" for k in ATAJOS_DEFECTO}
            self.atajos_cambio.emit()
            return
        if self._filtro is None:
            from PySide6.QtWidgets import QApplication
            self._filtro = _FiltroHotkey(self._pulso)
            QApplication.instance().installNativeEventFilter(self._filtro)
        for i, (accion, _n) in enumerate(ACCIONES):
            p = parsear_atajo(self.cfg["atajos"].get(accion))
            if not p:
                self.fallidos[accion] = "Atajo no válido"
                continue
            ident = ID_BASE + i
            if a["u"].RegisterHotKey(None, ident, p[0] | MOD_NOREPEAT, p[1]):
                self._registrados[ident] = accion
            else:
                self.fallidos[accion] = "Otra aplicación ya usa este atajo"
        for acc, otra in atajos_repetidos(self.cfg["atajos"]).items():
            self.fallidos.setdefault(acc, f"Igual que «{NOMBRES_ACCION[otra]}»")
        self.atajos_cambio.emit()

    def soltar_atajos(self):
        a = _win()
        if a:
            for ident in list(self._registrados):
                a["u"].UnregisterHotKey(None, ident)
        self._registrados.clear()

    def _pulso(self, ident):
        accion = self._registrados.get(ident)
        if not accion:
            return False
        self.ejecutar(accion)
        return True

    def fijar_atajo(self, accion, texto):
        """Cambia un atajo. Devuelve (ok, mensaje)."""
        if accion not in ATAJOS_DEFECTO:
            return False, "Acción desconocida"
        n = normalizar_atajo(texto)
        if not n:
            return False, "Usa una tecla con Ctrl, Alt o Win (por ejemplo Ctrl+Alt+P)"
        otras = {k: v for k, v in self.cfg["atajos"].items() if k != accion}
        for k, v in otras.items():
            if normalizar_atajo(v) == n:
                return False, f"Ya lo usa «{NOMBRES_ACCION[k]}»"
        self.cfg["atajos"][accion] = n
        self.cfg.guardar()
        if self.activo:
            self.registrar_atajos()
        self.cambio.emit()
        return True, n

    def restaurar_atajos(self):
        self.cfg["atajos"] = dict(ATAJOS_DEFECTO)
        self.cfg.guardar()
        if self.activo:
            self.registrar_atajos()
        self.cambio.emit()

    def ejecutar(self, accion):
        r = self.r
        if accion == "play":
            r.alternar()
        elif accion == "siguiente":
            r.siguiente()
        elif accion == "anterior":
            r.anterior()
        elif accion == "vol_mas":
            self.cambiar_volumen(5)
        elif accion == "vol_menos":
            self.cambiar_volumen(-5)
        elif accion == "mini":
            self.alternar_mini()
        elif accion == "clics":
            self.alternar_clics()
        elif accion == "hablar":
            self._hablar_inicio(parsear_atajo(self.cfg["atajos"].get("hablar")))

    def cambiar_volumen(self, delta):
        if self._vol_base is not None:          # mientras se habla: cambia el volumen al que se vuelve
            self._vol_base = max(0, min(100, self._vol_base + delta))
            self._vol_meta = self._nivel_bajo()
            return
        barra = getattr(self.v, "barra", None)
        if barra is not None and hasattr(barra, "subir_volumen"):
            barra.subir_volumen(delta)
        else:
            self.r.fijar_volumen(self.r.volumen + delta)
        self.cambio.emit()

    # ------------------------------------------------------------ mini reproductor

    def mini(self):
        if self._mini is None:
            from .ui.mini_gamer import MiniGamer
            self._mini = MiniGamer(self.ctx, self)
        return self._mini

    def mostrar_mini(self, si):
        m = self.mini()
        if si:
            m.abrir()
            self.cfg["mini_visible"] = True
            self._evento("mini")
        else:
            m.hide()
            self.cfg["mini_visible"] = False
        self.cfg.guardar()
        self.cambio.emit()

    def alternar_mini(self):
        visible = self._mini is not None and self._mini.isVisible()
        self.mostrar_mini(not visible)

    def fijar_clics(self, si):
        self.cfg["mini_clics"] = bool(si)
        self.cfg.guardar()
        if self._mini is not None:
            self._mini.aplicar_clics()
        self.cambio.emit()

    def alternar_clics(self):
        self.fijar_clics(not self.cfg["mini_clics"])

    def fijar_neon(self, si):
        self.cfg["neon"] = bool(si)
        self.cfg.guardar()
        from .ui.neon_gamer import reloj_neon
        reloj_neon().activar(self.cfg["neon"])
        self.cambio.emit()

    # ------------------------------------------------------------ ahorro al jugar

    def fijar_ahorro(self, si):
        self.cfg["ahorro"] = bool(si)
        self.cfg.guardar()
        if not si:
            self.salir_de_ahorro()
        self._reiniciar_sondeo()
        self.cambio.emit()

    def _reiniciar_sondeo(self):
        if self.activo and self.cfg["ahorro"]:
            if not self._t_sondeo.isActive():
                self._t_sondeo.start()
        else:
            self._t_sondeo.stop()

    def _sondear(self):
        try:
            info = self.sondeo()
        except Exception:  # noqa: BLE001 - un sondeo que falla no debe molestar
            return
        hay = es_juego_pantalla_completa(info, os.getpid(), self.cfg["ignorar"])
        if hay:
            self._negativos = 0
            if not self.ahorrando:
                self.entrar_en_ahorro((info or {}).get("exe", ""))
        elif self.ahorrando:
            # dos sondeos seguidos sin juego: un alt-tab rapido no apaga el ahorro
            self._negativos += 1
            if self._negativos >= 2:
                self.salir_de_ahorro()

    def _objetos_animados(self):
        v = self.v
        objs = []
        if v is not None:
            for nombre in ("capa_fondo", "personaje_fondo", "barra", "panel_der"):
                o = getattr(v, nombre, None)
                if o is not None:
                    objs.append(o)
            objs.extend(getattr(v, "singletons", {}).values())
        if self._mini is not None:
            objs.append(self._mini)
        objs.append(self)
        return objs

    def entrar_en_ahorro(self, nombre=""):
        """Quita lo que se mueve (mascota, personaje, visualizadores, neon) y baja la prioridad."""
        if self.ahorrando:
            return
        from PySide6.QtCore import QTimer as _T
        from PySide6.QtWidgets import QWidget
        self.ahorrando = True
        self.juego = nombre
        self._negativos = 0
        self._timers_parados = []
        self._ocultos = []
        vistos = set()
        for o in self._objetos_animados():
            if o is self:
                continue
            for t in ([o] if isinstance(o, _T) else []) + o.findChildren(_T):
                # solo los de animacion: rapidos y que se repiten
                if id(t) not in vistos and t.isActive() and not t.isSingleShot() and t.interval() <= 250:
                    vistos.add(id(t))
                    self._timers_parados.append((t, t.interval()))
                    t.stop()
        for nombre_o in ("capa_fondo", "personaje_fondo"):
            o = getattr(self.v, nombre_o, None) if self.v is not None else None
            if isinstance(o, QWidget) and o.isVisible():
                o.hide()
                self._ocultos.append(o)
        from .ui.neon_gamer import reloj_neon
        reloj_neon().pausar(True)
        self._prioridad_previa = prioridad_proceso() or PRIORIDAD_NORMAL
        poner_prioridad_proceso(PRIORIDAD_BAJA)
        self.ahorro_cambio.emit(True, nombre)

    def salir_de_ahorro(self):
        if not self.ahorrando:
            return
        self.ahorrando = False
        for o in self._ocultos:
            try:
                o.show()
            except RuntimeError:
                pass
        for t, ms in self._timers_parados:
            try:
                if not t.isActive():
                    t.start(ms)
            except RuntimeError:
                pass
        self._ocultos, self._timers_parados = [], []
        poner_prioridad_proceso(self._prioridad_previa or PRIORIDAD_NORMAL)
        self._prioridad_previa = None
        from .ui.neon_gamer import reloj_neon
        reloj_neon().pausar(False)
        self.ahorro_cambio.emit(False, "")

    # ------------------------------------------------------------ presets de sonido

    def aplicar_preset(self, clave):
        p = PRESETS_SONIDO.get(clave)
        if not p:
            return False
        a = self.ctx.ajustes
        if not self.cfg["sonido_gamer"]:      # primera vez: guardar el sonido de antes
            self.cfg["sonido_previo"] = {k: (list(a[k]) if isinstance(a[k], list) else a[k])
                                         for k in ("ecualizador", "eq_bandas", "eq_preset",
                                                   "sonido_envolvente")}
        a["ecualizador"] = True
        a["eq_bandas"] = list(p["bandas"])
        a["eq_preset"] = f"Gamer · {p['nombre']}"
        a["sonido_envolvente"] = bool(p["envolvente"])
        self._sonido_aplicado()
        self.cfg["sonido_gamer"] = clave
        self.cfg.guardar()
        self._evento("sonidos")
        self.cambio.emit()
        return True

    def restaurar_sonido(self):
        prev = self.cfg["sonido_previo"]
        a = self.ctx.ajustes
        if prev:
            for k, v in prev.items():
                a[k] = v
        else:
            a["ecualizador"], a["eq_bandas"], a["eq_preset"] = False, [0] * 10, "Plano"
        self._sonido_aplicado()
        self.cfg["sonido_gamer"] = ""
        self.cfg["sonido_previo"] = None
        self.cfg.guardar()
        self.cambio.emit()

    def _sonido_aplicado(self):
        self.ctx.ajustes.guardar()
        try:
            self.r.aplicar_sonido()
        except Exception:  # noqa: BLE001 - sin motor de audio no hay nada que aplicar
            pass
        senal = getattr(self.ctx, "sonido_cambio", None)
        if senal is not None:
            senal.emit()

    # ------------------------------------------------------------ bajar la musica al hablar

    def _nivel_bajo(self):
        return int(round((self._vol_base or 0) * self.cfg["hablar_nivel"] / 100.0))

    def _hablar_inicio(self, p):
        if not p or self._hablando is not None:
            return
        self._hablando = p[1]
        self._evento("hablar")
        self.bajar_volumen()
        self._t_tecla.start()

    def _vigilar_tecla(self):
        if self._hablando is None or not tecla_pulsada(self._hablando):
            self._t_tecla.stop()
            self._hablando = None
            self.subir_volumen()

    def bajar_volumen(self):
        """Baja al nivel de hablar con una rampa corta. No toca el volumen guardado."""
        if self._vol_base is None:
            self._vol_base = int(self.r.volumen)
            self._ajuste_vol0 = int(self.ctx.ajustes["volumen"])
        self._vol_meta = self._nivel_bajo()
        self._paso_ms = 220
        self._rampa.start()

    def subir_volumen(self):
        if self._vol_base is None:
            return
        # si la persona cambio el volumen a mano mientras tanto, se vuelve a ese
        guardado = int(self.ctx.ajustes["volumen"])
        if guardado != self._ajuste_vol0:
            self._vol_base = guardado
        self._vol_meta = self._vol_base
        self._paso_ms = 600
        self._rampa.start()

    def _paso_rampa(self):
        if self._vol_meta is None:
            self._rampa.stop()
            return
        actual = float(self.r.volumen)
        paso = max(1.0, abs(self._vol_base - self._nivel_bajo()) * PASO_RAMPA_MS / self._paso_ms)
        if abs(actual - self._vol_meta) <= paso:
            nuevo = self._vol_meta
        else:
            nuevo = actual + paso if actual < self._vol_meta else actual - paso
        self._poner_volumen(nuevo)
        if int(round(nuevo)) == int(self._vol_meta):
            self._rampa.stop()
            if self._hablando is None and self._vol_meta == self._vol_base:
                self._vol_base = None
                self._vol_meta = None
                self._refrescar_barra()

    def _poner_volumen(self, v):
        r = self.r
        r.volumen = max(0, min(100, int(round(v))))    # sin tocar ajustes: el guardado sigue siendo el de la persona
        try:
            r._aplicar_volumen()
        except Exception:  # noqa: BLE001
            pass
        self._refrescar_barra()

    def _refrescar_barra(self):
        barra = getattr(self.v, "barra", None)
        if barra is not None and hasattr(barra, "_pintar_volumen"):
            try:
                barra._pintar_volumen()
            except Exception:  # noqa: BLE001
                pass
        if self._mini is not None:
            self._mini.sincronizar_volumen()

    # ------------------------------------------------------------ listas por situacion

    def reproducir_situacion(self, clave, alterminar=None):
        s = SITUACIONES.get(clave)
        if not s:
            return False
        consultas = list(s["consultas"])

        def buscar():
            for q in consultas:
                pistas = [p for p in catalogo.buscar(q, "canciones", 40)
                          if p.get("tipo") == "pista" and p.get("video_id")]
                if len(pistas) >= 3:
                    return pistas
            return []

        def listo(pistas):
            if not pistas:
                self.ctx.aviso.emit("No encontré canciones para esa lista ahora mismo.")
            else:
                self.r.reproducir_lista(pistas, 0, {"tipo": "busqueda", "id": f"gamer-{clave}",
                                                    "titulo": f"Modo gamer · {s['nombre']}"})
                self._evento("listas")
            if alterminar:
                alterminar(bool(pistas))

        def fallo(e):
            self.ctx.aviso.emit(f"No se pudo cargar la lista: {e}")
            if alterminar:
                alterminar(False)

        self.ctx.aviso.emit(f"Preparando «{s['nombre']}»…")
        en_segundo_plano(buscar, ok=listo, error=fallo, dueno=self)
        return True

    # ------------------------------------------------------------ XP

    def _evento(self, nombre, n=1):
        ganado = self.progreso.evento(nombre, n)
        self._tras_xp(ganado)

    def _tic_xp(self):
        ahora = time.monotonic()
        dt = min(ahora - self._ultimo_tic, 30.0)
        self._ultimo_tic = ahora
        if self.r is not None and self.r.estado == "sonando":
            self._tras_xp(self.progreso.sumar_segundos(dt), dt)

    def _tras_xp(self, ganado, escuchado=0):
        antes = self._nivel_mostrado
        nivel = nivel_de_xp(self.progreso.xp)
        self._nivel_mostrado = nivel
        if ganado or escuchado:
            self.progreso.guardar()
        if nivel > antes:
            self.subio_nivel.emit(nivel)
            try:
                self.ctx.aviso.emit(f"¡Subiste al nivel {nivel}!")
            except Exception:  # noqa: BLE001
                pass
        self.progreso_cambio.emit()

    # ------------------------------------------------------------ OBS

    def carpeta_obs(self):
        c = self.cfg["obs_carpeta"]
        return c or str(carpeta_perfil() / "obs")

    def fijar_obs(self, activo=None, carpeta=None, con_html=None):
        if activo is not None:
            self.cfg["obs"] = bool(activo)
        if carpeta is not None:
            self.cfg["obs_carpeta"] = carpeta
        if con_html is not None:
            self.cfg["obs_html"] = bool(con_html)
        self.cfg.guardar()
        self._escribir_obs()
        self.cambio.emit()

    def _al_pista(self, p=None):
        if p:
            self._evento("pistas")
        self._escribir_obs()
        if self._mini is not None:
            self._mini.poner_pista(self.r.actual)

    def _al_estado(self, estado):
        if estado == "parado":
            self._escribir_obs()

    def _escribir_obs(self):
        if not (self.activo and self.cfg["obs"]):
            return False
        pista = self.r.actual if self.r is not None and self.r.estado != "parado" else None
        return escribir_ahora_suena(self.carpeta_obs(), pista, self.cfg["obs_html"])

    # ------------------------------------------------------------ cierre

    def cerrar(self):
        """Libera los atajos, devuelve el volumen y la prioridad, y guarda."""
        self._t_xp.stop()
        self._t_sondeo.stop()
        self._t_tecla.stop()
        self._rampa.stop()
        if self._vol_base is not None:
            self._poner_volumen(self._vol_base)
            self._vol_base = None
        self.soltar_atajos()
        if self._filtro is not None:
            try:
                from PySide6.QtWidgets import QApplication
                QApplication.instance().removeNativeEventFilter(self._filtro)
            except Exception:  # noqa: BLE001
                pass
            self._filtro = None
        self.salir_de_ahorro()
        if self.r is not None and self.activo and self.cfg["obs"]:
            escribir_ahora_suena(self.carpeta_obs(), None, self.cfg["obs_html"])
        if self._mini is not None:
            self._mini.guardar_posicion()
            self._mini.hide()
        self.cfg.guardar()
        self.progreso.guardar()
