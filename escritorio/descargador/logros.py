# -*- coding: utf-8 -*-
"""Logros: insignias por rachas de escucha, horas, canciones descubiertas, listas, escuchar con
amigos... (igual que app/lib/nucleo/logros.dart: mismas claves, mismas metas, mismo guardado).

Todo se cuenta en el equipo (logros.json en la carpeta de la cuenta) y se junta con la nube
(supabase/logros.sql) para que el teléfono y la computadora tengan los mismos. Al juntar nunca se
pierde nada: cada contador se queda con el mayor, los días se suman y cada logro conserva la fecha
más antigua en que se consiguió.

Quien cuenta (ui/logros_ui.py, VigiaLogros) avisa de lo que pasa:
    anotar_segundos(seg)                  tiempo con música sonando
    anotar_cancion(clave, artistas)       empezó a sonar una canción
    anotar_listas(n) / anotar_me_gusta(n) / anotar_descargas(n)   totales de la colección
    anotar_sala(codigo, con_amigos, soy_anfitrion)                «Escuchar juntos»
y `revisar()` devuelve los logros recién conseguidos (para el aviso).
"""

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

PLATAFORMA = "windows"
VITRINA_MAX = 3
DIAS_GUARDADOS = 400
SEGUNDOS_DIA = 60           # un día cuenta para la racha con al menos un minuto de música
MAX_CLAVES = 20000          # canciones distintas que se recuerdan en el equipo (lo demás solo suma)


@dataclass(frozen=True)
class Logro:
    id: str
    nombre: str
    descripcion: str
    categoria: str
    metrica: str
    meta: int


CATEGORIAS = (
    ("rachas", "Rachas"),
    ("horas", "Horas de música"),
    ("descubrir", "Descubrir"),
    ("listas", "Listas y me gusta"),
    ("amigos", "Con amigos"),
    ("especiales", "Especiales"),
)

CATALOGO = (
    Logro("primera_nota", "Primera nota", "Escucha tu primera canción en Caudal.", "descubrir", "canciones", 1),
    Logro("racha_3", "Encendido", "Escucha música 3 días seguidos.", "rachas", "racha", 3),
    Logro("racha_7", "Semana en llamas", "Escucha música 7 días seguidos.", "rachas", "racha", 7),
    Logro("racha_30", "Mes imparable", "Escucha música 30 días seguidos.", "rachas", "racha", 30),
    Logro("racha_100", "Leyenda del ritmo", "Escucha música 100 días seguidos.", "rachas", "racha", 100),
    Logro("horas_1", "Primera hora", "Acumula 1 hora de música.", "horas", "horas", 1),
    Logro("horas_10", "Diez horas", "Acumula 10 horas de música.", "horas", "horas", 10),
    Logro("horas_100", "Cien horas", "Acumula 100 horas de música.", "horas", "horas", 100),
    Logro("horas_500", "Disco de oro", "Acumula 500 horas de música.", "horas", "horas", 500),
    Logro("descubre_50", "Brújula musical", "Escucha 50 canciones distintas.", "descubrir", "canciones", 50),
    Logro("descubre_250", "Oído curioso", "Escucha 250 canciones distintas.", "descubrir", "canciones", 250),
    Logro("descubre_1000", "Planeta música", "Escucha 1000 canciones distintas.", "descubrir", "canciones", 1000),
    Logro("artistas_25", "Abanico de artistas", "Escucha a 25 artistas distintos.", "descubrir", "artistas", 25),
    Logro("lista_1", "Mi primera lista", "Crea tu primera lista.", "listas", "listas", 1),
    Logro("lista_5", "Mixtape", "Crea 5 listas.", "listas", "listas", 5),
    Logro("lista_15", "Cofre de listas", "Crea 15 listas.", "listas", "listas", 15),
    Logro("gusta_25", "Flechazo", "Dale me gusta a 25 canciones.", "listas", "me_gusta", 25),
    Logro("gusta_200", "Corazón grande", "Dale me gusta a 200 canciones.", "listas", "me_gusta", 200),
    Logro("juntos_1", "Mejor en compañía", "Escucha música con amigos en «Escuchar juntos».", "amigos", "juntos", 1),
    Logro("juntos_10", "Alma de la fiesta", "Comparte 10 salas de «Escuchar juntos».", "amigos", "juntos", 10),
    Logro("anfitrion", "La sala es tuya", "Abre una sala de «Escuchar juntos» y que alguien se una.", "amigos",
          "anfitrion", 1),
    Logro("noctambulo", "Búho nocturno", "Escucha 10 canciones entre la medianoche y las 5 a. m.", "especiales",
          "noche", 10),
    Logro("madrugador", "Al alba", "Escucha 10 canciones entre las 5 y las 8 de la mañana.", "especiales",
          "manana", 10),
    Logro("maraton", "Maratón", "Escucha 4 horas de música en un mismo día.", "especiales", "dia_horas", 4),
    Logro("descargas_25", "Sin internet, sin problema", "Guarda 25 canciones o videos para escucharlos sin internet.", "especiales",
          "descargas", 25),
    Logro("dos_mundos", "Dos mundos", "Usa Caudal en la computadora y en el teléfono con tu cuenta.", "especiales",
          "dispositivos", 2),
    Logro("coleccionista", "Vitrina llena", "Consigue 15 logros.", "especiales", "logros", 15),
)

POR_ID = {l.id: l for l in CATALOGO}

# contadores que se guardan (y viajan a la nube); el resto se calcula
CONTADORES = ("segundos", "canciones", "artistas", "listas", "me_gusta", "juntos", "anfitrion", "noche",
              "manana", "descargas", "dia_max", "racha_max")
ESCRITORIO = {"windows", "macos", "linux"}
MOVIL = {"android", "ios"}


def hoy_texto(cuando=None):
    return datetime.fromtimestamp(cuando if cuando is not None else time.time()).strftime("%Y-%m-%d")


def _fecha(texto):
    try:
        return date.fromisoformat(str(texto))
    except ValueError:
        return None


def racha_mas_larga(dias):
    """Días seguidos más largos en una lista de fechas aaaa-mm-dd (en cualquier orden)."""
    fechas = sorted({f for f in (_fecha(d) for d in dias) if f})
    mejor = actual = 0
    anterior = None
    for f in fechas:
        actual = actual + 1 if anterior is not None and f - anterior == timedelta(days=1) else 1
        mejor = max(mejor, actual)
        anterior = f
    return mejor


def racha_en_curso(dias, hoy=None):
    """Días seguidos que terminan hoy (o ayer: la racha sigue viva hasta que acabe el día)."""
    fechas = {f for f in (_fecha(d) for d in dias) if f}
    hoy = _fecha(hoy) if isinstance(hoy, str) else (hoy or date.today())
    dia = hoy if hoy in fechas else hoy - timedelta(days=1)
    n = 0
    while dia in fechas:
        n += 1
        dia -= timedelta(days=1)
    return n


def _artistas_de(pista):
    """Nombres de los artistas de una pista (en minúsculas), como los guarda la colección."""
    nombres = []
    for a in (pista or {}).get("artistas") or []:
        n = a.get("nombre") if isinstance(a, dict) else a
        if n and str(n).strip():
            nombres.append(str(n).strip().lower())
    if not nombres and (pista or {}).get("artista"):
        nombres = [p.strip().lower() for p in str(pista["artista"]).split(",") if p.strip()]
    return nombres


def _entero(v):
    try:
        if isinstance(v, bool):
            return 0
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return 0


class Logros:
    """Estado de los logros de una cuenta en este equipo."""

    def __init__(self, archivo=None, plataforma=PLATAFORMA, reloj=time.time):
        self.archivo = archivo
        self.plataforma = plataforma
        self.reloj = reloj
        self._cerrojo = threading.RLock()
        self.al_cambiar = []            # funciones sin argumentos (la pantalla se repinta)
        self._vaciar()
        self.cargar()
        self.plataformas.add(plataforma)

    def _vaciar(self):
        self.contadores = {k: 0 for k in CONTADORES}
        self.dias = set()
        self.plataformas = set()
        self.claves = set()
        self.artistas_vistos = set()
        self.salas = []                 # salas ya contadas (codigo|id), para no contar dos veces
        self.hoy = {"fecha": "", "segundos": 0}
        self.desbloqueados = {}
        self.vitrina = []
        self.importado = False
        self.pendiente_nube = False

    # ------------------------------------------------------------ disco
    def cargar(self):
        if not self.archivo:
            return
        try:
            with open(self.archivo, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(d, dict):
            return
        with self._cerrojo:
            for k in CONTADORES:
                self.contadores[k] = _entero((d.get("contadores") or {}).get(k))
            self.dias = {x for x in d.get("dias") or [] if _fecha(x)}
            self.plataformas = {str(x) for x in d.get("plataformas") or []}
            self.claves = set(map(str, d.get("claves") or []))
            self.artistas_vistos = set(map(str, d.get("artistas_vistos") or []))
            self.salas = [str(x) for x in d.get("salas") or []][-50:]
            hoy = d.get("hoy") or {}
            self.hoy = {"fecha": str(hoy.get("fecha") or ""), "segundos": _entero(hoy.get("segundos"))}
            self.desbloqueados = {str(k): _entero(v) for k, v in (d.get("desbloqueados") or {}).items()
                                  if str(k) in POR_ID}
            self.vitrina = [x for x in d.get("vitrina") or [] if x in self.desbloqueados][:VITRINA_MAX]
            self.importado = bool(d.get("importado"))
            self.pendiente_nube = bool(d.get("pendiente_nube"))

    def datos(self):
        with self._cerrojo:
            return {
                "version": 1,
                "contadores": dict(self.contadores),
                "dias": sorted(self.dias)[-DIAS_GUARDADOS:],
                "plataformas": sorted(self.plataformas),
                "claves": sorted(self.claves)[:MAX_CLAVES],
                "artistas_vistos": sorted(self.artistas_vistos)[:MAX_CLAVES],
                "salas": self.salas[-50:],
                "hoy": dict(self.hoy),
                "desbloqueados": dict(self.desbloqueados),
                "vitrina": list(self.vitrina),
                "importado": self.importado,
                "pendiente_nube": self.pendiente_nube,
            }

    def guardar(self):
        if not self.archivo:
            return
        try:
            tmp = str(self.archivo) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.datos(), f, ensure_ascii=False)
            os.replace(tmp, self.archivo)
        except OSError:
            pass

    def _avisar(self):
        for f in list(self.al_cambiar):
            try:
                f()
            except Exception:  # noqa: BLE001 - una pantalla cerrada no debe romper el conteo
                pass

    # ------------------------------------------------------------ lo que pasa
    def anotar_segundos(self, segundos, cuando=None):
        segundos = _entero(segundos)
        if segundos <= 0:
            return
        cuando = self.reloj() if cuando is None else cuando
        fecha = hoy_texto(cuando)
        with self._cerrojo:
            self.contadores["segundos"] += segundos
            if self.hoy["fecha"] != fecha:
                self.hoy = {"fecha": fecha, "segundos": 0}
            self.hoy["segundos"] += segundos
            self.contadores["dia_max"] = max(self.contadores["dia_max"], self.hoy["segundos"])
            if self.hoy["segundos"] >= SEGUNDOS_DIA:
                self.dias.add(fecha)
            self.contadores["racha_max"] = max(self.contadores["racha_max"], racha_mas_larga(self.dias))
            self.pendiente_nube = True

    def anotar_cancion(self, clave, artistas=(), cuando=None):
        if not clave:
            return
        cuando = self.reloj() if cuando is None else cuando
        hora = datetime.fromtimestamp(cuando).hour
        with self._cerrojo:
            if clave not in self.claves:
                self.claves.add(clave)
                self.contadores["canciones"] += 1
            for a in artistas or ():
                a = str(a).strip().lower()
                if a and a not in self.artistas_vistos:
                    self.artistas_vistos.add(a)
                    self.contadores["artistas"] += 1
            if hora < 5:
                self.contadores["noche"] += 1
            elif hora < 8:
                self.contadores["manana"] += 1
            self.pendiente_nube = True

    def anotar_pista(self, pista, cuando=None):
        """Atajo: una pista de la app (dict con clave y artistas)."""
        if pista:
            self.anotar_cancion(pista.get("clave"), _artistas_de(pista), cuando)

    def _total(self, clave, n):
        n = _entero(n)
        with self._cerrojo:
            if n > self.contadores[clave]:
                self.contadores[clave] = n
                self.pendiente_nube = True

    def anotar_listas(self, total):
        self._total("listas", total)

    def anotar_me_gusta(self, total):
        self._total("me_gusta", total)

    def anotar_descargas(self, total):
        self._total("descargas", total)

    def anotar_sala(self, ident, con_amigos, soy_anfitrion=False):
        """Una sala de «Escuchar juntos». Cuenta una vez por sala y solo si había alguien más."""
        if not ident or not con_amigos:
            return
        with self._cerrojo:
            if ident in self.salas:
                return
            self.salas = (self.salas + [ident])[-50:]
            self.contadores["juntos"] += 1
            if soy_anfitrion:
                self.contadores["anfitrion"] += 1
            self.pendiente_nube = True

    def importar(self, reproducciones):
        """Lo ya escuchado antes de existir los logros (una sola vez): [(clave, fecha, pista|None)].
        Cuenta canciones, artistas, días y horarios; las horas empiezan a contar desde ahora."""
        with self._cerrojo:
            if self.importado:
                return
            for clave, fecha, pista in reproducciones or ():
                try:
                    fecha = float(fecha)
                except (TypeError, ValueError):
                    continue
                self.anotar_cancion(clave, _artistas_de(pista), fecha)
                self.dias.add(hoy_texto(fecha))
            self.contadores["racha_max"] = max(self.contadores["racha_max"], racha_mas_larga(self.dias))
            self.importado = True
            self.pendiente_nube = True

    # ------------------------------------------------------------ cuentas
    def racha_actual(self, hoy=None):
        return racha_en_curso(self.dias, hoy or date.fromtimestamp(self.reloj()))

    def valor(self, metrica):
        c = self.contadores
        if metrica == "racha":
            return max(c["racha_max"], racha_mas_larga(self.dias))
        if metrica == "horas":
            return c["segundos"] // 3600
        if metrica == "dia_horas":
            return c["dia_max"] // 3600
        if metrica == "dispositivos":
            return int(bool(self.plataformas & ESCRITORIO)) + int(bool(self.plataformas & MOVIL))
        if metrica == "logros":
            return len(self.desbloqueados)
        return c.get(metrica, 0)

    def progreso(self, logro):
        """(valor, meta, fraccion 0..1) de un logro."""
        logro = POR_ID[logro] if isinstance(logro, str) else logro
        v = self.valor(logro.metrica)
        return v, logro.meta, min(1.0, v / logro.meta if logro.meta else 1.0)

    def conseguido(self, ident):
        return ident in self.desbloqueados

    def revisar(self):
        """Desbloquea lo que ya se cumplió y lo devuelve (en el orden del catálogo)."""
        nuevos = []
        ahora = int(self.reloj())
        with self._cerrojo:
            # dos vueltas: «Vitrina llena» depende de cuántos hay
            for _ in range(2):
                for l in CATALOGO:
                    if l.id not in self.desbloqueados and self.valor(l.metrica) >= l.meta:
                        self.desbloqueados[l.id] = ahora
                        nuevos.append(l)
            if nuevos:
                self.pendiente_nube = True
        self.guardar()
        if nuevos:
            self._avisar()
        return nuevos

    def resumen(self):
        return {"conseguidos": len(self.desbloqueados), "total": len(CATALOGO),
                "racha": self.racha_actual(), "horas": self.contadores["segundos"] // 3600}

    # ------------------------------------------------------------ vitrina
    def poner_vitrina(self, ids):
        with self._cerrojo:
            limpio = []
            for i in ids or ():
                if i in self.desbloqueados and i not in limpio:
                    limpio.append(i)
            self.vitrina = limpio[:VITRINA_MAX]
            self.pendiente_nube = True
        self.guardar()
        self._avisar()
        return list(self.vitrina)

    def alternar_vitrina(self, ident):
        """Pone o quita un logro de la vitrina. Devuelve False si no se pudo (no conseguido o llena)."""
        if ident not in self.desbloqueados:
            return False
        if ident in self.vitrina:
            self.poner_vitrina([x for x in self.vitrina if x != ident])
            return True
        if len(self.vitrina) >= VITRINA_MAX:
            return False
        self.poner_vitrina(self.vitrina + [ident])
        return True

    # ------------------------------------------------------------ nube
    def para_nube(self):
        with self._cerrojo:
            return {
                "p_contadores": {k: int(v) for k, v in self.contadores.items()},
                "p_dias": sorted(self.dias)[-DIAS_GUARDADOS:],
                "p_plataformas": sorted(self.plataformas),
                "p_desbloqueados": {k: int(v) for k, v in self.desbloqueados.items()},
                "p_vitrina": list(self.vitrina),
            }

    def mezclar(self, remoto):
        """Junta lo que devolvió la nube (logros_guardar / logros_mios). Nunca baja nada."""
        if not isinstance(remoto, dict):
            return
        with self._cerrojo:
            for k, v in (remoto.get("contadores") or {}).items():
                if k in self.contadores:
                    self.contadores[k] = max(self.contadores[k], _entero(v))
            self.dias |= {d for d in remoto.get("dias") or [] if _fecha(d)}
            self.plataformas |= {str(p) for p in remoto.get("plataformas") or []}
            for k, v in (remoto.get("desbloqueados") or {}).items():
                if k in POR_ID:
                    v = _entero(v)
                    if k not in self.desbloqueados or (v and v < self.desbloqueados[k]):
                        self.desbloqueados[k] = v
            vit = remoto.get("vitrina")
            if isinstance(vit, list):
                self.vitrina = [x for x in vit if x in self.desbloqueados][:VITRINA_MAX]
            self.contadores["racha_max"] = max(self.contadores["racha_max"], racha_mas_larga(self.dias))
        self.guardar()
        self._avisar()


def subir(datos, sesion):
    """Manda `para_nube()` y devuelve lo juntado en la nube (dict), o None sin red / sin la tabla.
    Solo hace red: se puede llamar desde un hilo (luego `mezclar` en el hilo de la interfaz)."""
    if sesion is None or not getattr(sesion, "access", ""):
        return None
    try:
        r = sesion.rpc("logros_guardar", **datos)
    except Exception:  # noqa: BLE001 - sin red o sin la migración: se intenta más tarde
        return None
    return r if isinstance(r, dict) else None


def sincronizar(logros, sesion):
    """Sube y junta de una vez (todo en el mismo hilo). True si se pudo."""
    r = subir(logros.para_nube(), sesion)
    if r is None:
        return False
    with logros._cerrojo:
        logros.pendiente_nube = False
    logros.mezclar(r)
    return True


def vitrina_de(sesion, usuario):
    """{"vitrina": [...], "total": n, "fechas": {...}} de otra persona, o None si no se puede ver."""
    if sesion is None or not usuario:
        return None
    try:
        r = sesion.rpc("logros_de", p_usuario=str(usuario))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(r, dict):
        return None
    return {"vitrina": [x for x in r.get("vitrina") or [] if x in POR_ID][:VITRINA_MAX],
            "total": _entero(r.get("total")), "fechas": r.get("fechas") or {}}


def reproducciones_de(ruta_base, limite=50000):
    """Lee lo escuchado de la base de la colección (en solo lectura, desde cualquier hilo)."""
    import sqlite3
    filas = []
    try:
        con = sqlite3.connect(f"file:{ruta_base}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return filas
    try:
        cur = con.execute(
            "SELECT r.clave, r.fecha, p.datos FROM reproducciones r LEFT JOIN pistas p ON p.clave = r.clave "
            "ORDER BY r.fecha LIMIT ?", (limite,))
        for clave, fecha, datos in cur:
            try:
                pista = json.loads(datos) if datos else None
            except ValueError:
                pista = None
            filas.append((clave, fecha, pista))
    except sqlite3.Error:
        pass
    finally:
        con.close()
    return filas
