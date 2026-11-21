# -*- coding: utf-8 -*-
"""Aviso de errores: los cierres y errores que nadie atrapó se mandan a la nube de Caudal
(tabla `errores_app`, supabase/errores_app.sql), sin servicios de terceros y sin datos personales.

Igual que app/lib/nucleo/aviso_errores.dart. Cada informe lleva: plataforma, versión, sistema,
la pantalla que estaba abierta, el tipo de error, el mensaje y la traza. Antes de salir del equipo
se borran las rutas de la carpeta del usuario, correos, enlaces con datos y cosas que parecen claves.
No va el usuario ni el id de la cuenta.

- Se apaga desde Ajustes (casilla «Enviar informes de errores»); apagado no se guarda ni se manda nada.
- Sin red, los informes esperan en una cola en el disco y salen en otro arranque.
- Freno: el mismo error se junta (se cuenta cuántas veces pasó) y sale como mucho una vez cada
  6 horas; como mucho 20 informes al día y 30 errores distintos en cola. Un cierre de verdad
  (Python que se cae del todo) queda escrito con faulthandler y se manda al abrir la siguiente vez.

Se engancha en main.py, después de registro_fallos.activar (que deja su fallos.log como siempre):
    aviso_errores.activar(carpeta_datos())
"""

import faulthandler
import hashlib
import json
import os
import platform
import re
import sys
import threading
import time
import traceback

PLATAFORMA = "windows" if sys.platform == "win32" else ("macos" if sys.platform == "darwin" else "linux")
TABLA = "/rest/v1/errores_app"
ESPERA_MISMO = 6 * 3600       # el mismo error sale como mucho una vez cada 6 horas
TOPE_DIA = 20                 # informes por día
TOPE_COLA = 30                # errores distintos esperando
TOPE_SESION = 60              # capturas por sesión (luego se ignora todo: algo va muy mal)
PAUSA_SIN_TABLA = 24 * 3600   # el servidor aún no tiene la tabla: se vuelve a probar al día siguiente

_estado = {"carpeta": None, "pantalla": "", "capturas": 0, "temporizador": None, "cierre": None,
           "enviar": None, "version": None}
_cerrojo = threading.RLock()


# ---------------------------------------------------------------- limpiar datos personales

_PATRONES = (
    # carpeta del usuario (Windows, macOS, Linux), con \ o /
    # (el nombre puede llevar espacios: «C:\Users\María José\...»)
    (re.compile(r"(?i)([a-z]:[\\/]+(?:users|usuarios|documents and settings)[\\/]+)[^\\/\"'<>|:,\r\n]+"),
     r"\1~"),
    (re.compile(r"(/(?:home|Users)/)[^/\s\"']+"), r"\1~"),
    # correos (también los usuario@usuarios.caudal.app de las cuentas)
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<correo>"),
    # tokens JWT
    (re.compile(r"eyJ[\w-]{6,}\.[\w-]{6,}\.[\w-]*"), "<token>"),
    # enlaces: se queda el sitio y la ruta, sin lo que va después de ? o #
    (re.compile(r"(https?://[^\s\"'<>?#]+)[?#][^\s\"'<>]*"), r"\1?…"),
    # cadenas largas que parecen claves o códigos
    (re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"), "<clave>"),
)


def limpiar(texto):
    """Quita lo personal de un texto (rutas de usuario, correos, tokens, datos de enlaces)."""
    t = str(texto or "")
    for patron, cambio in _PATRONES:
        t = patron.sub(cambio, t)
    return t


# ---------------------------------------------------------------- informe

def huella(tipo, marcos):
    """Igual error = igual huella: tipo + archivo:función de cada marco (sin números de línea,
    para que el mismo fallo se agrupe aunque cambie la versión)."""
    base = tipo + "|" + "|".join(marcos)
    return hashlib.sha256(base.encode("utf-8", "replace")).hexdigest()[:20]


def informe_de(tipo_exc, valor, tb, origen="interfaz", pantalla="", version=None, sistema=None,
               plataforma=PLATAFORMA):
    """El informe (dict con las columnas de la tabla) de una excepción."""
    if version is None:
        try:
            from .version import VERSION as version
        except Exception:  # noqa: BLE001
            version = "?"
    tipo = getattr(tipo_exc, "__qualname__", None) or getattr(tipo_exc, "__name__", None) or str(tipo_exc)
    modulo = getattr(tipo_exc, "__module__", "") or ""
    if modulo and modulo not in ("builtins", "__main__"):
        tipo = f"{modulo}.{tipo}"
    marcos = []
    for m in traceback.extract_tb(tb) if tb is not None else []:
        marcos.append(f"{os.path.basename(m.filename)}:{m.name}")
    traza = "".join(traceback.format_exception(tipo_exc, valor, tb)) if tb is not None else \
        "".join(traceback.format_exception_only(tipo_exc, valor))
    return _armar(tipo, str(valor), traza, huella(tipo, marcos), origen, pantalla, version, sistema, plataforma)


def informe_texto(tipo, mensaje, traza, origen="", pantalla="", version=None, sistema=None,
                  plataforma=PLATAFORMA):
    """Un informe a partir de texto (p. ej. el volcado de un cierre de Python)."""
    if version is None:
        try:
            from .version import VERSION as version
        except Exception:  # noqa: BLE001
            version = "?"
    sin_lineas = re.sub(r"line \d+", "", re.sub(r"0x[0-9a-fA-F]+", "", str(traza)))
    marcos = re.findall(r'File "([^"]+)"', sin_lineas)
    return _armar(tipo, mensaje, traza, huella(tipo, [os.path.basename(m) for m in marcos] or [sin_lineas[:200]]),
                  origen, pantalla, version, sistema, plataforma)


def _armar(tipo, mensaje, traza, hue, origen, pantalla, version, sistema, plataforma):
    ahora = time.time()
    return {
        "plataforma": plataforma,
        "version": str(version)[:24] or "?",
        "sistema": (sistema if sistema is not None else sistema_actual())[:120],
        "pantalla": limpiar(pantalla)[:80],
        "origen": str(origen)[:40],
        "tipo": limpiar(tipo)[:160] or "Error",
        "mensaje": limpiar(mensaje)[:600],
        # lo último de la traza es lo que más dice: si es larga se recorta por delante
        "traza": _recortar_inicio(limpiar(traza), 8000),
        "huella": hue,
        "veces": 1,
        "primera_vez": ahora,
        "ultima_vez": ahora,
    }


def _recortar_inicio(t, n):
    return t if len(t) <= n else "…" + t[-(n - 1):]


_SISTEMA = []


def sistema_actual():
    """«Windows 10 (AMD64) · Python 3.12.10». Se calcula una vez: en Windows preguntar la versión
    puede tardar segundos (WMI) y no debe pasar justo cuando algo falla."""
    if not _SISTEMA:
        try:
            _SISTEMA.append(f"{platform.system()} {platform.release()} ({platform.machine()}) · "
                            f"Python {platform.python_version()}")
        except Exception:  # noqa: BLE001
            _SISTEMA.append(sys.platform)
    return _SISTEMA[0]


# ---------------------------------------------------------------- ajuste y cola

def _ruta(nombre):
    c = _estado["carpeta"]
    if not c:
        # aún sin activar (p. ej. la casilla de Ajustes): la carpeta de datos de siempre
        try:
            from .config import carpeta_datos
            c = str(carpeta_datos())
        except Exception:  # noqa: BLE001
            return None
    return os.path.join(str(c), nombre)


def _leer(nombre, defecto):
    ruta = _ruta(nombre)
    if not ruta:
        return defecto
    try:
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def _escribir(nombre, datos):
    ruta = _ruta(nombre)
    if not ruta:
        return
    try:
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        os.replace(tmp, ruta)
    except OSError:
        pass


def activo():
    """¿Se mandan los informes? (casilla de Ajustes; encendida si nunca se tocó)."""
    return bool(_leer("aviso_errores.json", {}).get("activo", True))


def poner_activo(si):
    with _cerrojo:
        _escribir("aviso_errores.json", {"activo": bool(si)})
        if not si:
            _escribir("errores_pendientes.json", [])     # apagado: lo que esperaba tampoco sale


def cola():
    return [x for x in _leer("errores_pendientes.json", []) if isinstance(x, dict) and x.get("huella")]


def encolar(informe):
    """Guarda el informe en la cola del disco (junta los repetidos). False si no se guardó."""
    if not activo():
        return False
    with _cerrojo:
        c = cola()
        for x in c:
            if x["huella"] == informe["huella"]:
                x["veces"] = min(100000, int(x.get("veces") or 1) + int(informe.get("veces") or 1))
                x["ultima_vez"] = informe.get("ultima_vez") or time.time()
                for k in ("version", "pantalla", "mensaje", "traza", "sistema"):
                    x[k] = informe.get(k, x.get(k))
                break
        else:
            c.append(dict(informe))
        # cola llena: se van los más viejos
        c = sorted(c, key=lambda x: x.get("ultima_vez") or 0)[-TOPE_COLA:]
        _escribir("errores_pendientes.json", c)
        return True


def _envios():
    e = _leer("errores_enviados.json", {})
    hoy = time.strftime("%Y-%m-%d")
    if e.get("dia") != hoy:
        e = {"dia": hoy, "n": 0, "huellas": e.get("huellas") or {}, "pausa_hasta": e.get("pausa_hasta") or 0}
    e.setdefault("huellas", {})
    e.setdefault("pausa_hasta", 0)
    # se olvidan las huellas viejas (más de 2 días)
    limite = time.time() - 2 * 86400
    e["huellas"] = {k: v for k, v in e["huellas"].items() if isinstance(v, (int, float)) and v > limite}
    return e


def _fecha_iso(t):
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(t)))
    except (TypeError, ValueError):
        return None


def para_enviar(ahora=None):
    """Los informes de la cola que pueden salir ya (respetando los frenos)."""
    ahora = time.time() if ahora is None else ahora
    e = _envios()
    if e["pausa_hasta"] > ahora:
        return []
    libres = max(0, TOPE_DIA - int(e.get("n") or 0))
    listos = [x for x in cola() if ahora - e["huellas"].get(x["huella"], 0) >= ESPERA_MISMO]
    return listos[:libres]


def _post_por_defecto(fila):
    """Manda una fila; devuelve el código HTTP (0 si no hubo red)."""
    import requests
    from . import nube
    try:
        r = requests.post(nube.URL + TABLA, json=fila, timeout=15, headers={
            "apikey": nube.CLAVE_PUBLICA, "Authorization": f"Bearer {nube.CLAVE_PUBLICA}",
            "Content-Type": "application/json", "Prefer": "return=minimal"})
        return r.status_code
    except Exception:  # noqa: BLE001 - sin red: sigue en la cola
        return 0


def enviar_pendientes(enviar=None, ahora=None):
    """Manda lo que se pueda de la cola. Devuelve cuántos salieron. Se llama desde un hilo."""
    if not activo():
        return 0
    enviar = enviar or _estado["enviar"] or _post_por_defecto
    ahora = time.time() if ahora is None else ahora
    salieron = 0
    for inf in para_enviar(ahora):
        fila = {k: inf.get(k) for k in ("plataforma", "version", "sistema", "pantalla", "origen", "tipo",
                                        "mensaje", "traza", "huella", "veces")}
        fila["primera_vez"] = _fecha_iso(inf.get("primera_vez"))
        fila["ultima_vez"] = _fecha_iso(inf.get("ultima_vez"))
        codigo = enviar(fila)
        with _cerrojo:
            e = _envios()
            if 200 <= codigo < 300 or codigo in (400, 409, 413, 422):
                # salió (o el servidor no lo quiere nunca): fuera de la cola
                _escribir("errores_pendientes.json", [x for x in cola() if x["huella"] != inf["huella"]])
                if 200 <= codigo < 300:
                    e["huellas"][inf["huella"]] = ahora
                    e["n"] = int(e.get("n") or 0) + 1
                    salieron += 1
                _escribir("errores_enviados.json", e)
            elif codigo == 404:
                # el servidor aún no tiene la tabla (migración sin aplicar): mañana se prueba
                e["pausa_hasta"] = ahora + PAUSA_SIN_TABLA
                _escribir("errores_enviados.json", e)
                break
            else:
                break       # sin red o servidor caído: se intenta en otro momento
    return salieron


def _programar_envio(segundos=5.0):
    with _cerrojo:
        t = _estado.get("temporizador")
        if t is not None and t.is_alive():
            return
        t = threading.Timer(segundos, _enviar_en_hilo)
        t.daemon = True
        _estado["temporizador"] = t
        t.start()


def _enviar_en_hilo():
    try:
        enviar_pendientes()
    except Exception:  # noqa: BLE001 - el aviso de errores nunca debe dar otro error
        pass


# ---------------------------------------------------------------- captura

def fijar_pantalla(nombre):
    """La pantalla abierta (la ventana la puede ir diciendo; si no, se mira la ventana activa)."""
    _estado["pantalla"] = str(nombre or "")[:80]


def _pantalla_actual():
    if _estado["pantalla"]:
        return _estado["pantalla"]
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return ""
        partes = []
        v = app.activeWindow() or app.activeModalWidget()
        if v is not None:
            partes.append(type(v).__name__)
            # la página visible de la ventana principal, si tiene una pila de páginas
            for nombre in ("pila", "paginas", "stack"):
                pila = getattr(v, nombre, None)
                actual = getattr(pila, "currentWidget", None)
                if callable(actual) and actual() is not None:
                    partes.append(type(actual()).__name__)
                    break
        return " > ".join(partes)
    except Exception:  # noqa: BLE001
        return ""


def capturar(tipo, valor, tb, origen="interfaz"):
    """Anota un error no controlado. Nunca lanza."""
    try:
        if _estado["carpeta"] is None or tipo is None or issubclass(tipo, (KeyboardInterrupt, SystemExit)):
            return
        with _cerrojo:
            _estado["capturas"] += 1
            if _estado["capturas"] > TOPE_SESION:
                return
        inf = informe_de(tipo, valor, tb, origen=origen, pantalla=_pantalla_actual(), version=_estado["version"])
        if encolar(inf):
            _programar_envio()
    except Exception:  # noqa: BLE001
        pass


# Excepciones SEH que una librería nativa lanza y atrapa ella misma: faulthandler las escribe
# («Windows fatal exception: code 0x...») aunque la app siga viva. 0xe24c4a02 es el error de LuaJIT
# (dentro de libmpv), que mpv atrapa solo. No son cierres: se quitan del informe.
EXCEPCIONES_INOFENSIVAS = ("0xe24c4a02",)
_CABECERA_FALLO = re.compile(r"^(Windows fatal exception:|Fatal Python error:)", re.IGNORECASE)


def limpiar_cierre(texto):
    """Quita del texto de faulthandler los bloques de excepciones inofensivas (ver arriba).
    Cada bloque empieza en «Windows fatal exception:» o «Fatal Python error:» y llega hasta el
    siguiente. Devuelve el texto que queda, sin espacios sobrantes ("" si no queda nada)."""
    bloques, actual = [], []
    for linea in (texto or "").splitlines():
        if _CABECERA_FALLO.match(linea.strip()) and actual:
            bloques.append(actual)
            actual = []
        actual.append(linea)
    if actual:
        bloques.append(actual)
    quedan = []
    for bloque in bloques:
        cabecera = bloque[0].strip().lower()
        if cabecera.startswith("windows fatal exception:") and \
                any(c in cabecera for c in EXCEPCIONES_INOFENSIVAS):
            continue
        quedan.append("\n".join(bloque))
    return "\n".join(quedan).strip()


def _revisar_cierre_anterior():
    """Si la vez anterior Python se cayó del todo (faulthandler escribió algo), se manda."""
    ruta = _ruta("cierre_nativo.txt")
    if not ruta or not os.path.exists(ruta):
        return
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            texto = f.read().strip()
    except OSError:
        return
    texto = limpiar_cierre(texto)      # sin las excepciones que la librería atrapa sola
    # si la sesión anterior terminó bien, lo escrito fue un aviso que no la tumbó: no se manda
    if texto and not _leer("aviso_errores_sesion.json", {}).get("limpio", True):
        primera = texto.splitlines()[0][:150]
        inf = informe_texto("Cierre inesperado", primera, texto[-8000:], origen="cierre", version=_estado["version"])
        encolar(inf)


def activar(carpeta, version=None, enviar=None, demora=20.0):
    """Instala los ganchos (excepciones de la interfaz y de los hilos, y cierres de Python).
    `enviar(fila) -> código HTTP` es para las pruebas."""
    _estado.update(carpeta=str(carpeta), version=version, enviar=enviar, capturas=0)
    # lo que usan los hilos de este módulo se importa AQUÍ, en el hilo principal: si un hilo
    # importa `requests` mientras la app lo está importando, los dos se esperan para siempre
    # (bloqueo de importación) y Caudal no llega a abrir la ventana
    import requests  # noqa: F401
    from . import nube  # noqa: F401
    try:
        import winreg  # noqa: F401  (platform lo pide al mirar la versión de Windows)
    except ImportError:
        pass
    threading.Thread(target=sistema_actual, name="sistema", daemon=True).start()   # se calcula ya, aparte
    _revisar_cierre_anterior()

    anterior = sys.excepthook

    def gancho(tipo, valor, tb):
        capturar(tipo, valor, tb, "interfaz")
        try:
            anterior(tipo, valor, tb)
        except Exception:  # noqa: BLE001
            pass

    sys.excepthook = gancho

    anterior_hilo = threading.excepthook

    def gancho_hilo(args):
        if args.exc_type is not SystemExit:
            nombre = getattr(args.thread, "name", "") or "hilo"
            capturar(args.exc_type, args.exc_value, args.exc_traceback, "hilo:" + re.sub(r"\d+", "", nombre)[:30])
        try:
            anterior_hilo(args)
        except Exception:  # noqa: BLE001
            pass

    threading.excepthook = gancho_hilo

    # un cierre de verdad (fallo de memoria en una librería nativa...) no pasa por los ganchos:
    # faulthandler deja la traza en un archivo que se manda al abrir la próxima vez
    try:
        ruta = _ruta("cierre_nativo.txt")
        viejo = _estado.get("cierre")
        if viejo is not None:
            try:
                faulthandler.disable()
                viejo.close()
            except Exception:  # noqa: BLE001
                pass
        f = open(ruta, "w", encoding="utf-8")
        faulthandler.enable(file=f, all_threads=False)
        _estado["cierre"] = f
    except Exception:  # noqa: BLE001
        pass

    # la sesión queda «abierta» hasta que Qt sale bien (aboutToQuit)
    _escribir("aviso_errores_sesion.json", {"limpio": False})
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(marcar_salida_limpia)
    except Exception:  # noqa: BLE001
        pass

    if demora is not None and cola():
        _programar_envio(demora)


def marcar_salida_limpia():
    """Caudal se cerró bien: lo que haya en cierre_nativo.txt no fue un cierre."""
    _escribir("aviso_errores_sesion.json", {"limpio": True})
