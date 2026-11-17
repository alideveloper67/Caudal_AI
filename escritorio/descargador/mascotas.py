# -*- coding: utf-8 -*-
"""«Mascotitas» del reproductor: un personajito que camina sobre la barra de progreso.

Exclusivo de las cuentas «Donador de Caudal» y «Fundador de Caudal»: usa el mismo permiso que
el fondo (lo decide el servidor, aquí solo se lee `ctx.fondo.puede`). La elegida se guarda en la
carpeta de la cuenta, para que aparezca al abrir Caudal sin esperar a la red.
"""

import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from .config import carpeta_perfil


def _carpeta_arte():
    base = Path(getattr(sys, "_MEIPASS", "")) / "descargador" if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "mascotas"


ARTE = _carpeta_arte()
_PIXMAPS = {}


def catalogo():
    """Las mascotas disponibles: [{clave, nombre, origen, ancho, alto, arcoiris}]."""
    try:
        datos = json.loads((ARTE / "catalogo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [m for m in datos if isinstance(m, dict) and m.get("clave")]


def cuenta_id(ctx):
    """El id (en la nube) de la cuenta que está dentro, o ''."""
    return str((getattr(ctx, "cuenta", None) or {}).get("id") or "")


def cuenta_usuario(ctx):
    """El usuario de la cuenta que está dentro (en minúsculas), o ''."""
    return str((getattr(ctx, "cuenta", None) or {}).get("usuario") or "").strip().lower()


def es_de(m, ctx):
    """¿Esta mascota es de la cuenta que está dentro? Las de todos, sí; las exclusivas, por id o por usuario."""
    if not es_exclusiva(m):
        return True
    yo, usuario = cuenta_id(ctx), cuenta_usuario(ctx)
    usuarios = [str(u).lower() for u in (m.get("solo_usuarios") or [])]
    return (bool(yo) and yo in cuentas_de(m)) or (bool(usuario) and usuario in usuarios)


def cuentas_de(m):
    """Las cuentas (ids en la nube) dueñas de una mascota exclusiva (campo `solo_cuentas`); [] si es de todos."""
    m = m or {}
    lista = m.get("solo_cuentas") or ([m["solo_cuenta"]] if m.get("solo_cuenta") else [])
    return [str(x) for x in lista if x]


def es_exclusiva(m):
    """Mascota solo de unas cuentas."""
    return bool(cuentas_de(m))


def disponible_para(m, cuenta):
    """Las de todos, y las exclusivas solo para sus cuentas."""
    return bool(m) and (not es_exclusiva(m) or cuenta in cuentas_de(m))


def catalogo_de(ctx):
    """Lo que esta cuenta puede ver: sin las exclusivas de otras cuentas."""
    return [m for m in catalogo() if es_de(m, ctx)]


def por_clave(clave):
    for m in catalogo():
        if m["clave"] == clave:
            return m
    return None


def estela_hoja(clave):
    """QPixmap de la estela (2 variantes de 11x11 lado a lado) o None."""
    k = "estela_" + clave
    if k in _PIXMAPS:
        return _PIXMAPS[k]
    pm = QPixmap(str(ARTE / f"{clave}.png".replace(clave, k)))
    _PIXMAPS[k] = None if pm.isNull() else pm
    return _PIXMAPS[k]


def num_cuadros(datos):
    """Cuántos cuadros de animación trae la hoja de una mascota (campo `cuadros` del catálogo; por defecto 2)."""
    try:
        return max(2, int((datos or {}).get("cuadros", 2)))
    except (TypeError, ValueError):
        return 2


def densidad(datos):
    """Píxeles de la hoja por píxel en pantalla (campo `densidad`; por defecto 1). Con 2 la mascota se ve
    igual de grande pero con el doble de detalle."""
    try:
        return max(1, int((datos or {}).get("densidad", 1)))
    except (TypeError, ValueError):
        return 1


def cuadros(clave):
    """Los cuadros de la animación como QPixmap (2 o más, lado a lado en la hoja), o None si no existe el dibujo."""
    if clave in _PIXMAPS:
        return _PIXMAPS[clave]
    hoja = QPixmap(str(ARTE / f"{clave}.png"))
    if hoja.isNull():
        _PIXMAPS[clave] = None
        return None
    n = num_cuadros(por_clave(clave))
    ancho = hoja.width() // n
    res = tuple(hoja.copy(i * ancho, 0, ancho, hoja.height()) for i in range(n))
    _PIXMAPS[clave] = res
    return res


class GestorMascota(QObject):
    cambiada = Signal()

    def __init__(self, ctx, padre=None):
        super().__init__(padre)
        self.ctx = ctx
        self.clave = ""
        self._cargar()
        fondo = getattr(ctx, "fondo", None)
        if fondo is not None:
            fondo.permiso_cambiado.connect(lambda _p: self.cambiada.emit())

    @staticmethod
    def _archivo():
        return carpeta_perfil() / "mascota.json"

    def _cargar(self):
        try:
            datos = json.loads(self._archivo().read_text(encoding="utf-8"))
            clave = str(datos.get("clave") or "")
        except Exception:  # noqa: BLE001
            clave = ""
        self.clave = clave if por_clave(clave) else ""

    def _guardar(self):
        try:
            self._archivo().write_text(json.dumps({"clave": self.clave}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @property
    def puede(self):
        return bool(getattr(getattr(self.ctx, "fondo", None), "puede", False))

    def puede_elegir(self, clave):
        """Las de siempre: donadores y fundadores. Una exclusiva: solo su cuenta (aunque no sea donadora)."""
        m = por_clave(clave)
        if not m:
            return False
        if es_exclusiva(m):
            return es_de(m, self.ctx)
        return self.puede

    @property
    def tiene_exclusivas(self):
        """Esta cuenta tiene alguna mascota solo suya."""
        return any(es_exclusiva(m) and es_de(m, self.ctx) for m in catalogo())

    @property
    def activa(self):
        return bool(self.clave) and self.puede_elegir(self.clave)

    def elegir(self, clave):
        """Pone la mascota (o la quita con ''). Devuelve False si la cuenta no puede."""
        clave = clave if por_clave(clave) else ""
        if clave and not self.puede_elegir(clave):
            return False
        if clave == self.clave:
            return True
        self.clave = clave
        self._guardar()
        self.cambiada.emit()
        return True

    def datos(self):
        return por_clave(self.clave) if self.activa else None


COLORES_ARCOIRIS = ("#ff0000", "#ff9900", "#ffff00", "#33ff00", "#0099ff", "#6633ff")


def pintar(p, datos, x, y, margen, ancho_total, cuadro, fase, escala=1):
    """Dibuja la mascota con los pies sobre la línea `y`, centrada en `x`.

    La usan la barra del reproductor y la vista previa de Ajustes, para que se vean igual.
    """
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QPainter
    cuadros_ = cuadros(datos["clave"])
    if not cuadros_:
        return
    w, h = datos["ancho"] * escala, datos["alto"] * escala
    izq = max(0.0, min(x - w / 2, ancho_total - w))
    arriba = y - h + 1 * escala
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setRenderHint(QPainter.SmoothPixmapTransform, False)
    if datos.get("arcoiris"):
        # la estela de arcoíris de Nyan Cat: seis franjas con un vaivén suave
        fino = 3 * escala
        base = arriba + h * 0.30
        xi = margen
        fin = izq + w * 0.25
        while xi < fin:
            onda = escala * (1 if int((xi - margen) / (5 * escala) + fase) % 2 else 0)
            for i, col in enumerate(COLORES_ARCOIRIS):
                p.fillRect(QRectF(xi, base + i * fino + onda, min(2 * escala, fin - xi) + 0.5, fino), QColor(col))
            xi += 2 * escala
    elif datos.get("estela"):
        _pintar_estela(p, datos["clave"], x, y, margen, w, h, fase, escala)
    pm = cuadros_[cuadro % len(cuadros_)]
    # hoja con más detalle que la pantalla (densidad 2 en una pantalla al 100 %): se reduce suave para no perder
    # trazos; si la pantalla tiene densidad suficiente se dibuja nítido, píxel a píxel
    reducir = densidad(datos) > 1 and p.device() is not None and p.device().devicePixelRatioF() < densidad(datos)
    if reducir:
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    p.drawPixmap(QRectF(izq, arriba, w, h), pm, QRectF(pm.rect()))
    if reducir:
        p.setRenderHint(QPainter.SmoothPixmapTransform, False)


def _pintar_estela(p, clave, x, y, margen, w, h, fase, escala):
    """El detallito de cada mascota (corazones, estrellas, hojas…) que va quedando atrás y se desvanece.
    No guarda nada: se calcula de la posición, así también se ve bien al saltar a otro punto."""
    import math
    from PySide6.QtCore import QRectF
    hoja = estela_hoja(clave)
    if hoja is None:
        return
    n, paso = 7, 21 * escala
    centro = x - w * 0.32
    for i in range(n):
        px = centro - (i + 1) * paso
        if px < margen:
            break
        vida = 1.0 - i / n
        tam = (18 * escala) * (0.6 + 0.4 * vida)
        vaiven = math.sin(fase * 0.9 + i * 1.3) * 3 * escala
        py = y - h * 0.42 + vaiven - (1 - vida) * 3 * escala
        var = (i + int(fase)) % 2
        p.setOpacity(0.25 + 0.75 * vida)
        p.drawPixmap(QRectF(px - tam / 2, py - tam / 2, tam, tam), hoja, QRectF(var * 11, 0, 11, 11))
    p.setOpacity(1.0)
