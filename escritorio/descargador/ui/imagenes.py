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
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QRectF, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPainterPath, QPixmap

from ..config import carpeta_datos

_POOL = QThreadPool()
_POOL.setMaxThreadCount(6)
_MEMORIA = OrderedDict()          # (url, w, h, forma, radio) -> QPixmap
_IMAGENES = OrderedDict()         # url -> QImage original
_COLORES = OrderedDict()           # cacheKey de la imagen -> color (con tope, ver color_dominante)
TOPE_COLORES = 600
_esperando = {}                   # url -> [callbacks]
_cerrojo = threading.Lock()
_AGENTE = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36")
_por_hilo = threading.local()


def _sesion_del_hilo():
    """Una requests.Session por hilo de bajada (Session no es segura entre hilos; así cada
    hilo reutiliza su conexión con el servidor de portadas)."""
    s = getattr(_por_hilo, "sesion", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = _AGENTE
        _por_hilo.sesion = s
    return s


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
        r = _sesion_del_hilo().get(url, timeout=15)
        if r.status_code == 200 and r.content and len(r.content) < 12_000_000:
            try:
                ruta.write_bytes(r.content)
            except OSError:
                pass
            return r.content
    except requests.RequestException:
        pass
    return b""


def bytes_de(url):
    """Bytes originales (de disco, cache o internet; bloquea: llamar en segundo plano). Sirve para los
    GIF que se animan: `imagen()`/`pedir()` de un GIF dan SOLO el primer cuadro (para listas y
    tarjetas pequenas), nunca se cachea una animacion como imagen estatica donde deba animarse."""
    return _leer(url)


class _Senales(QObject):
    listo = Signal(str, object, object)      # url, QImage original, {spec: QImage recortada}


_senales = _Senales()

# lado máximo al que se decodifica una original: más que cualquier portada en pantalla
# (la más grande, el vinilo, ronda 400 px × 2 de densidad) y que las tarjetas para compartir.
# Una carátula local de 3000x3000 (36 MB en memoria) queda en 1280x1280 (6,5 MB).
LADO_MAXIMO = 1280


def decodificar(datos):
    """QImage de unos bytes, reducida al decodificar si es enorme (sirve en cualquier hilo)."""
    img = QImage()
    if not datos:
        return img
    # el arreglo de bytes y el búfer tienen que vivir mientras el lector los usa
    arreglo = QByteArray(datos)
    bufer = QBuffer(arreglo)
    bufer.open(QIODevice.ReadOnly)
    try:
        lector = QImageReader(bufer)
        tam = lector.size()
        if tam.isValid() and max(tam.width(), tam.height()) > LADO_MAXIMO:
            lector.setScaledSize(tam.scaled(LADO_MAXIMO, LADO_MAXIMO, Qt.KeepAspectRatio))
        img = lector.read()
        del lector
    finally:
        bufer.close()
    if img.isNull():                 # formatos raros: como antes
        img = QImage()
        img.loadFromData(datos)
    return img


class _Bajada(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        datos = _leer(self.url)
        img = decodificar(datos)
        # las miniaturas de YouTube vienen con franjas negras (4:3 con un 16:9
        # dentro): se recortan para que no parezcan marcos
        if not img.isNull() and "i.ytimg.com" in self.url and img.height() > 0:
            if abs(img.width() / img.height() - 4 / 3) < 0.05:
                alto = int(img.width() * 9 / 16)
                img = img.copy(0, (img.height() - alto) // 2, img.width(), alto)
        # los recortes que ya se pidieron se hacen aquí, fuera del hilo de la interfaz
        # (escalar una original de 1280 px costaba milisegundos por portada al pintar listas)
        with _cerrojo:
            specs = set(_recortes_pedidos.get(self.url, ()))
        hechos = {}
        if not img.isNull():
            for spec in specs:
                try:
                    hechos[spec] = formar_imagen(img, *spec)
                except Exception:  # noqa: BLE001 - se hará en el hilo principal
                    pass
        _senales.listo.emit(self.url, img, hechos)


# las originales se guardan por peso, no por cantidad: una miniatura de
# YouTube a 1280x720 ocupa ~3,7 MB en memoria. Las que salen se vuelven a leer
# del disco (no de internet) si hacen falta.
TOPE_ORIGINALES = 64 * 1024 * 1024
_peso = {"total": 0}
_recortes_pedidos = {}           # url -> {(w_px, h_px, forma, radio_px)} pendientes de bajar


def _guardar_original(url, img):
    viejo = _IMAGENES.pop(url, None)
    if viejo is not None:
        _peso["total"] -= viejo.sizeInBytes()
    _IMAGENES[url] = img
    _peso["total"] += img.sizeInBytes()
    while _peso["total"] > TOPE_ORIGINALES and len(_IMAGENES) > 1:
        _u, sale = _IMAGENES.popitem(last=False)
        _peso["total"] -= sale.sizeInBytes()


def _al_bajar(url, img, hechos=None):
    if not img.isNull():
        _guardar_original(url, img)
    with _cerrojo:
        callbacks = _esperando.pop(url, [])
        _recortes_pedidos.pop(url, None)
    _hechos_ahora.update({"url": url, "hechos": hechos or {}})
    try:
        for cb in callbacks:
            try:
                cb(img)
            except RuntimeError:
                pass
    finally:
        _hechos_ahora.update({"url": None, "hechos": {}})


_hechos_ahora = {"url": None, "hechos": {}}     # recortes hechos en el hilo de bajada, mientras se reparten
_senales.listo.connect(_al_bajar)


def imagen(url, callback):
    """Pide la QImage original (sin recortar)."""
    if not url:
        callback(QImage())
        return
    if url in _IMAGENES:
        _IMAGENES.move_to_end(url)
        callback(_IMAGENES[url])
        return
    with _cerrojo:
        if url in _esperando:
            _esperando[url].append(callback)
            return
        _esperando[url] = [callback]
    _POOL.start(_Bajada(url))


def _escala_pantalla():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is not None:
        try:
            return app.devicePixelRatio()
        except Exception:
            return 1.0
    return 1.0


def _spec(ancho, alto, forma, radio, escala):
    """Lo que hace falta para recortar: el tamaño en píxeles reales (nítido con la densidad
    de la pantalla, nunca menor que lo que se pinta)."""
    return (max(1, int(ancho * escala)), max(1, int(alto * escala)), forma, float(radio) * escala)


def formar_imagen(img, w, h, forma="cuadrada", radio_px=6.0):
    """El recorte (como object-fit: cover) en una QImage de w×h píxeles. Vale en cualquier hilo."""
    destino = QImage(max(1, w), max(1, h), QImage.Format_ARGB32_Premultiplied)
    destino.fill(Qt.transparent)
    p = QPainter(destino)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    ruta = QPainterPath()
    if forma == "redonda":
        ruta.addEllipse(QRectF(0, 0, w, h))
    else:
        ruta.addRoundedRect(QRectF(0, 0, w, h), radio_px, radio_px)
    p.setClipPath(ruta)
    if img is None or img.isNull():
        p.fillRect(0, 0, w, h, QColor("#252A35"))
    else:
        esc = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (esc.width() - w) // 2
        y = (esc.height() - h) // 2
        p.drawImage(0, 0, esc, x, y, w, h)
    p.end()
    return destino


def _a_pixmap(qimg, escala):
    pm = QPixmap.fromImage(qimg)
    pm.setDevicePixelRatio(escala)
    return pm


def formar(img, ancho, alto, forma="cuadrada", radio=6):
    """Recorta la imagen para llenar el hueco (como object-fit: cover)."""
    escala = _escala_pantalla()
    return _a_pixmap(formar_imagen(img, *_spec(ancho, alto, forma, radio, escala)), escala)


TOPE_RECORTES = 64 * 1024 * 1024
_peso_recortes = {"total": 0}


def _bytes(pm):
    return pm.width() * pm.height() * 4


def _guardar_recorte(clave, pm):
    viejo = _MEMORIA.pop(clave, None)
    if viejo is not None:
        _peso_recortes["total"] -= _bytes(viejo)
    _MEMORIA[clave] = pm
    _peso_recortes["total"] += _bytes(pm)
    while (_peso_recortes["total"] > TOPE_RECORTES or len(_MEMORIA) > 1500) and len(_MEMORIA) > 1:
        _c, sale = _MEMORIA.popitem(last=False)
        _peso_recortes["total"] -= _bytes(sale)


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
        _IMAGENES.move_to_end(url)
        if img.isNull():
            return None
        pm = formar(img, ancho, alto, forma, radio)
        _guardar_recorte(clave, pm)
        return pm

    escala = _escala_pantalla()
    spec = _spec(ancho, alto, forma, radio, escala)

    def listo(img):
        if img is None or img.isNull():
            return
        hecho = _hechos_ahora["hechos"].get(spec) if _hechos_ahora["url"] == url else None
        if hecho is not None:
            pm = _a_pixmap(hecho, escala)        # recortada en el hilo de bajada: aquí solo se convierte
        else:
            pm = formar(img, ancho, alto, forma, radio)
        _guardar_recorte(clave, pm)
        if callback:
            callback(pm)

    if url:
        with _cerrojo:
            _recortes_pedidos.setdefault(url, set()).add(spec)
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
    while len(_COLORES) > TOPE_COLORES:
        _COLORES.popitem(last=False)
    return color


def precargar(urls):
    for u in urls:
        if u and u not in _IMAGENES:
            imagen(u, lambda _i: None)


def _uso():  # pragma: no cover - documentacion viva
    return os.path.basename(__file__)
