# -*- coding: utf-8 -*-
"""Portadas: se bajan en segundo plano, se guardan en disco y se recortan.

    imagenes.pedir(url, ancho, alto, forma, radio, callback)

`callback(QPixmap)` se llama en el hilo principal. La misma imagen pedida dos
veces se baja una sola vez. Acepta tambien rutas de archivos locales (las
caratulas de lo descargado).
"""

import hashlib
import os
import threading
from collections import OrderedDict

import requests
from PySide6.QtCore import QObject, QRectF, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPixmap

from ..config import carpeta_datos

_POOL = QThreadPool()
_POOL.setMaxThreadCount(6)
_MEMORIA = OrderedDict()          # (url, w, h, forma, radio) -> QPixmap
_IMAGENES = OrderedDict()         # url -> QImage original
_COLORES = {}
_esperando = {}                   # url -> [callbacks]
_cerrojo = threading.Lock()
_sesion = requests.Session()
_sesion.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36")


def carpeta_cache():
    c = carpeta_datos() / "cache_imagenes"
    c.mkdir(parents=True, exist_ok=True)
    return c


def _ruta_cache(url):
    return carpeta_cache() / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".img")


def limpiar_cache(tope_mb=400):
    """Borra lo mas viejo si la cache pasa del tope."""
    try:
        archivos = sorted(carpeta_cache().glob("*.img"), key=lambda f: f.stat().st_atime)
        total = sum(f.stat().st_size for f in archivos)
        tope = tope_mb * 1024 * 1024
        for f in archivos:
            if total <= tope:
                break
            total -= f.stat().st_size
            f.unlink(missing_ok=True)
    except OSError:
        pass


def tamano_cache():
    try:
        return sum(f.stat().st_size for f in carpeta_cache().glob("*.img"))
    except OSError:
        return 0


def _leer(url):
    """Bytes de la imagen: de disco, de la cache o de internet."""
    if not url:
        return b""
    if "://" not in url:
        try:
            with open(url, "rb") as f:
                return f.read()
        except OSError:
            return b""
    ruta = _ruta_cache(url)
    if ruta.exists():
        try:
            return ruta.read_bytes()
        except OSError:
            pass
    try:
        r = _sesion.get(url, timeout=15)
        if r.status_code == 200 and r.content and len(r.content) < 12_000_000:
            try:
                ruta.write_bytes(r.content)
            except OSError:
                pass
            return r.content
    except requests.RequestException:
        pass
    return b""


class _Senales(QObject):
    listo = Signal(str, object)


_senales = _Senales()


class _Bajada(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        datos = _leer(self.url)
        img = QImage()
        if datos:
            img.loadFromData(datos)
        # las miniaturas de YouTube vienen con franjas negras (4:3 con un 16:9
        # dentro): se recortan para que no parezcan marcos
        if not img.isNull() and "i.ytimg.com" in self.url and img.height() > 0:
            if abs(img.width() / img.height() - 4 / 3) < 0.05:
                alto = int(img.width() * 9 / 16)
                img = img.copy(0, (img.height() - alto) // 2, img.width(), alto)
        _senales.listo.emit(self.url, img)


def _al_bajar(url, img):
    if not img.isNull():
        _IMAGENES[url] = img
        while len(_IMAGENES) > 260:
            _IMAGENES.popitem(last=False)
    with _cerrojo:
        callbacks = _esperando.pop(url, [])
    for cb in callbacks:
        try:
            cb(img)
        except RuntimeError:
            pass


_senales.listo.connect(_al_bajar)


def imagen(url, callback):
    """Pide la QImage original (sin recortar)."""
    if not url:
        callback(QImage())
        return
    if url in _IMAGENES:
        callback(_IMAGENES[url])
        return
    with _cerrojo:
        if url in _esperando:
            _esperando[url].append(callback)
            return
        _esperando[url] = [callback]
    _POOL.start(_Bajada(url))


def formar(img, ancho, alto, forma="cuadrada", radio=6):
    """Recorta la imagen para llenar el hueco (como object-fit: cover)."""
    from PySide6.QtWidgets import QApplication
    escala = 1.0
    app = QApplication.instance()
    if app is not None:
        try:
            escala = app.devicePixelRatio()
        except Exception:
            escala = 1.0
    w, h = int(ancho * escala), int(alto * escala)
    destino = QPixmap(max(1, w), max(1, h))
    destino.fill(Qt.transparent)
    p = QPainter(destino)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    ruta = QPainterPath()
    if forma == "redonda":
        ruta.addEllipse(QRectF(0, 0, w, h))
    else:
        ruta.addRoundedRect(QRectF(0, 0, w, h), radio * escala, radio * escala)
    p.setClipPath(ruta)
    if img is None or img.isNull():
        p.fillRect(0, 0, w, h, QColor("#252A35"))
    else:
        esc = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (esc.width() - w) // 2
        y = (esc.height() - h) // 2
        p.drawImage(0, 0, esc, x, y, w, h)
    p.end()
    destino.setDevicePixelRatio(escala)
    return destino


def pedir(url, ancho, alto, forma="cuadrada", radio=6, callback=None):
    """Devuelve el QPixmap si ya esta en memoria; si no, llama a callback luego."""
    clave = (url, ancho, alto, forma, radio)
    if clave in _MEMORIA:
        _MEMORIA.move_to_end(clave)
        return _MEMORIA[clave]
    if url in _IMAGENES:
        # ya bajada: se recorta ahora y se devuelve (sin callback, que llegaria
        # antes de que quien llama guarde el resultado y lo pisaria)
        img = _IMAGENES[url]
        if img.isNull():
            return None
        pm = formar(img, ancho, alto, forma, radio)
        _MEMORIA[clave] = pm
        return pm

    def listo(img):
        if img is None or img.isNull():
            return
        pm = formar(img, ancho, alto, forma, radio)
        _MEMORIA[clave] = pm
        while len(_MEMORIA) > 900:
            _MEMORIA.popitem(last=False)
        if callback:
            callback(pm)

    if url:
        imagen(url, listo)
    return None


def color_dominante(img):
    """Un color de la portada, oscurecido, para el degradado de la cabecera."""
    if img is None or img.isNull():
        return QColor("#2A3240")
    clave = img.cacheKey()
    if clave in _COLORES:
        return _COLORES[clave]
    pequena = img.scaled(24, 24, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    # se agrupan los pixeles por tono y saturacion; gana el grupo con mas peso,
    # premiando los colores vivos sobre los grises
    cubetas = {}
    for x in range(pequena.width()):
        for y in range(pequena.height()):
            c = QColor(pequena.pixel(x, y))
            h, s, v, _a = c.getHsv()
            if v < 40:
                continue
            grupo = (h // 24 if h >= 0 else -1, s // 64)
            peso = 1 + s / 255 * 2 + v / 255
            b = cubetas.setdefault(grupo, [0, 0, 0, 0, 0.0])
            b[0] += c.red()
            b[1] += c.green()
            b[2] += c.blue()
            b[3] += 1
            b[4] += peso
    if not cubetas:
        color = QColor("#2A3240")
    else:
        b = max(cubetas.values(), key=lambda x: x[4])
        color = QColor(b[0] // b[3], b[1] // b[3], b[2] // b[3])
        h, s, v, _a = color.getHsv()
        color.setHsv(max(0, h), min(255, int(s * 1.05)), min(150, max(70, int(v * 0.62))))
    _COLORES[clave] = color
    return color


def precargar(urls):
    for u in urls:
        if u and u not in _IMAGENES:
            imagen(u, lambda _i: None)


def _uso():  # pragma: no cover - documentacion viva
    return os.path.basename(__file__)
