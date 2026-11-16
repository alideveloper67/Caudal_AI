# -*- coding: utf-8 -*-
"""«Fondo de Caudal»: una imagen tenue detrás de toda la aplicación.

Solo la pueden poner las cuentas con título «Donador de Caudal» o «Fundador de Caudal»
(lo decide el servidor con `puede_poner_fondo()`; aquí solo se pregunta). La imagen y sus
dos ajustes (cuánto se ve y cuánto se desenfoca) se guardan en la nube y en una copia local
de la carpeta de la cuenta, para que al abrir Caudal se vea al instante, sin esperar a la red.
"""

import json
import time

from PySide6.QtCore import QBuffer, QIODevice, QObject, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter

from . import nube
from . import social as S
from .config import carpeta_perfil
from .hilos import en_segundo_plano

VISIBLE_MIN, VISIBLE_MAX, VISIBLE_DEF = 5, 60, 22
DESENFOQUE_MIN, DESENFOQUE_MAX, DESENFOQUE_DEF = 0, 20, 0
LADO_MAX = 1920                 # lado largo, en píxeles
TOPE_BYTES = 5 * 1024 * 1024    # lo que acepta el almacén
EXT_IMAGEN = (".jpg", ".jpeg", ".png", ".webp")
TITULO_DONADOR = "Donador de Caudal"
TITULO_FUNDADOR = "Fundador de Caudal"


def limitar_visible(v):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        v = VISIBLE_DEF
    return max(VISIBLE_MIN, min(VISIBLE_MAX, v))


def limitar_desenfoque(v):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError):
        v = DESENFOQUE_DEF
    return max(DESENFOQUE_MIN, min(DESENFOQUE_MAX, v))


def es_imagen(ruta):
    return str(ruta or "").lower().endswith(EXT_IMAGEN)


def preparar_fondo(origen):
    """Imagen elegida (ruta o bytes) → JPEG de lado largo ≤ 1920 px y menos de 5 MB."""
    img = S._cargar_imagen(origen)
    w, h = img.width(), img.height()
    if max(w, h) > LADO_MAX:
        img = img.scaled(LADO_MAX, LADO_MAX, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    plano = QImage(img.width(), img.height(), QImage.Format_RGB32)
    plano.fill(QColor("#000000"))          # lo transparente queda oscuro, como la aplicación
    p = QPainter(plano)
    p.drawImage(0, 0, img)
    p.end()
    ultimo = b""
    for calidad in (85, 78, 70, 60, 50, 40):
        b = QBuffer()
        b.open(QIODevice.WriteOnly)
        plano.save(b, "JPEG", calidad)
        ultimo = bytes(b.data())
        if len(ultimo) < TOPE_BYTES:
            return ultimo
    raise nube.ErrorNube("La imagen sigue pesando demasiado. Elige otra más pequeña.")


def _descargar(url):
    import requests
    r = requests.get(url, timeout=25)
    if r.status_code != 200 or not r.content:
        raise nube.ErrorNube("No se pudo bajar tu fondo.")
    return r.content


class GestorFondo(QObject):
    """El fondo de la cuenta activa: imagen, ajustes, copia local y nube."""

    antes_de_cambiar = Signal()       # justo antes de poner o quitar la imagen (para el fundido)
    cambiado = Signal(bool)           # algo se ve distinto; True si se encendió o se apagó
    permiso_cambiado = Signal(bool)

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.imagen = None            # QImage o None
        self.serie = 0                # sube con cada imagen nueva (para las cachés)
        self.visible = VISIBLE_DEF
        self.desenfoque = DESENFOQUE_DEF
        self.puede = False
        self.titulo = ""
        self.pendiente = False        # hay cambios locales que aún no llegaron a la nube
        self._cargar_local()

    # ------------------------------------------------------------ copia local
    @staticmethod
    def _archivos():
        c = carpeta_perfil()
        return c / "fondo_app.jpg", c / "fondo_app.json"

    def _cargar_local(self):
        jpg, js = self._archivos()
        datos = {}
        try:
            datos = json.loads(js.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
        self.puede = bool(datos.get("puede"))
        self.titulo = str(datos.get("titulo") or "")
        self.visible = limitar_visible(datos.get("visible", VISIBLE_DEF))
        self.desenfoque = limitar_desenfoque(datos.get("desenfoque", DESENFOQUE_DEF))
        self.pendiente = bool(datos.get("pendiente"))
        if self.puede and datos.get("tiene") and jpg.exists():
            img = QImage(str(jpg))
            if not img.isNull():
                self.imagen = img
                self.serie += 1

    def _guardar_local(self):
        jpg, js = self._archivos()
        try:
            js.write_text(json.dumps({
                "puede": self.puede, "titulo": self.titulo, "visible": self.visible,
                "desenfoque": self.desenfoque, "tiene": self.imagen is not None,
                "pendiente": self.pendiente}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def _escribir_imagen(self, datos_jpeg):
        jpg, _ = self._archivos()
        try:
            if datos_jpeg:
                jpg.write_bytes(datos_jpeg)
            elif jpg.exists():
                jpg.unlink()
        except OSError:
            pass

    @property
    def activo(self):
        return self.imagen is not None

    def _sesion(self):
        cuenta = getattr(self.ctx, "cuenta", None) or {}
        return cuenta.get("sesion")

    def _social(self):
        sesion = self._sesion()
        return S.Social(sesion) if sesion is not None else None

    # ------------------------------------------------------------ cambios en pantalla
    def _poner_imagen_memoria(self, img):
        """Cambia la imagen mostrada (None la quita). Avisa para el fundido."""
        encendia = (img is not None) != (self.imagen is not None)
        self.antes_de_cambiar.emit()
        self.imagen = img
        self.serie += 1
        self.cambiado.emit(encendia)

    def poner_valores(self, visible=None, desenfoque=None):
        """Mientras se mueven los deslizadores: se ve al momento, aún sin guardar."""
        if visible is not None:
            self.visible = limitar_visible(visible)
        if desenfoque is not None:
            self.desenfoque = limitar_desenfoque(desenfoque)
        self.cambiado.emit(False)

    def poner_imagen(self, origen):
        """Pone una imagen elegida por la persona (ruta o bytes). Guarda local y sube a la nube.
        Devuelve los bytes JPEG que se guardaron."""
        if not self.puede:
            raise nube.ErrorNube("Tu cuenta no puede poner un fondo.")
        datos = preparar_fondo(origen)
        img = QImage()
        img.loadFromData(datos)
        self._escribir_imagen(datos)
        self.pendiente = True
        self._poner_imagen_memoria(img)
        self._guardar_local()
        self._subir_async(datos)
        return datos

    def quitar(self):
        self._escribir_imagen(None)
        self.pendiente = True
        self._poner_imagen_memoria(None)
        self._guardar_local()
        self._quitar_async()

    def guardar_ajustes(self):
        """Al soltar un deslizador: copia local y nube."""
        self._guardar_local()
        social = self._social()
        if social is None or not self.puede:
            return
        campos = {"fondo_visible": self.visible, "fondo_desenfoque": self.desenfoque}
        en_segundo_plano(social.guardar_perfil, campos, error=lambda _e: None)

    # ------------------------------------------------------------ nube
    def _subir_async(self, datos):
        social = self._social()
        if social is None:
            return
        campos = {"fondo_visible": self.visible, "fondo_desenfoque": self.desenfoque}

        def trabajo():
            campos["fondo_url"] = social.subir_fondo(datos)
            social.guardar_perfil(campos)
            return True

        def listo(_):
            self.pendiente = False
            self._guardar_local()

        def fallo(e):
            aviso = getattr(self.ctx, "aviso", None)
            if aviso is not None:
                aviso.emit("Tu fondo se ve aquí, pero no se pudo guardar en tu cuenta. "
                           + S.explicar(e, "guardarlo"))
        en_segundo_plano(trabajo, ok=listo, error=fallo)

    def _quitar_async(self):
        social = self._social()
        if social is None:
            return

        def listo(_):
            self.pendiente = False
            self._guardar_local()
        en_segundo_plano(social.quitar_fondo, ok=listo, error=lambda _e: None)

    # ------------------------------------------------------------ permiso y sincronización
    def consultar_permiso(self):
        """Pregunta al servidor (bloquea). Sin red conserva lo que ya se sabía."""
        social = self._social()
        if social is None:
            return self.puede
        try:
            puede = bool(social.puede_poner_fondo())
        except nube.SinConexion:
            return self.puede
        except nube.ErrorNube:
            return self.puede
        titulo = self.titulo
        if puede:
            titulo = self._titulo_de(social) or titulo or TITULO_DONADOR
        return puede, titulo

    def _titulo_de(self, social):
        usuario = (getattr(self.ctx, "cuenta", None) or {}).get("usuario") or ""
        try:
            p = social.ver_perfil(usuario)
        except nube.ErrorNube:
            return ""
        if not p:
            return ""
        claves = {t.get("clave") for t in p.get("titulos") or []}
        if p.get("fundador_caudal") or "fundador_caudal" in claves:
            return TITULO_FUNDADOR
        return TITULO_DONADOR

    def aplicar_permiso(self, res):
        if isinstance(res, bool) or res is None:
            return
        puede, titulo = res
        cambio = puede != self.puede
        self.puede, self.titulo = puede, (titulo if puede else "")
        if not puede and self.imagen is not None:
            self._escribir_imagen(None)
            self._poner_imagen_memoria(None)
        self._guardar_local()
        if cambio:
            self.permiso_cambiado.emit(puede)

    def verificar_permiso(self):
        """Lo mismo, sin bloquear la ventana."""
        if self._sesion() is None:
            return
        en_segundo_plano(self.consultar_permiso, ok=self.aplicar_permiso, error=lambda _e: None)

    def _traer(self):
        """(Bloquea) Todo lo de la nube: permiso, ajustes y la imagen. None si no hay red."""
        social = self._social()
        if social is None:
            return None
        try:
            permiso = self.consultar_permiso()
            if isinstance(permiso, bool):
                return None
            res = {"permiso": permiso}
            if permiso[0]:
                fila = social.leer_fondo()
                res["fila"] = fila
                ruta = fila.get("fondo_url")
                if ruta:
                    res["datos"] = _descargar(S.url_publica(S.BUCKET_FOTOS, ruta, int(time.time())))
            return res
        except nube.ErrorNube:
            return None
        except Exception:  # noqa: BLE001
            return None

    def aplicar_remoto(self, res):
        if not res:
            return
        self.aplicar_permiso(res["permiso"])
        if not res["permiso"][0] or self.pendiente:
            return
        fila = res.get("fila") or {}
        visible = limitar_visible(fila.get("fondo_visible") or VISIBLE_DEF)
        desen = limitar_desenfoque(fila.get("fondo_desenfoque") or 0)
        datos = res.get("datos")
        if datos:
            img = QImage()
            img.loadFromData(datos)
            if not img.isNull():
                self._escribir_imagen(datos)
                self.visible, self.desenfoque = visible, desen
                self._poner_imagen_memoria(img)
                self._guardar_local()
                return
        elif self.imagen is not None and not fila.get("fondo_url"):
            self._escribir_imagen(None)
            self._poner_imagen_memoria(None)
        if (visible, desen) != (self.visible, self.desenfoque):
            self.visible, self.desenfoque = visible, desen
            self.cambiado.emit(False)
        self._guardar_local()

    def sincronizar(self):
        """Al iniciar sesión: la nube manda sobre la copia local (sin bloquear la ventana)."""
        if self._sesion() is None:
            return
        en_segundo_plano(self._traer, ok=self.aplicar_remoto, error=lambda _e: None)
